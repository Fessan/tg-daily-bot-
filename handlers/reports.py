"""
Обработчики команд для работы с отчетами
"""
import re
import logging
import aiosqlite
from datetime import datetime
from pytz import timezone as pytz_timezone
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

from config import DB_PATH, TIMEZONE
from bot_instance import bot, dp
from db import ensure_admins_in_db

logger = logging.getLogger(__name__)


@dp.message(Command("mychats"))
async def cmd_mychats(message: Message):
    """Показать список чатов, где пользователь является участником"""
    # Обрабатываем только в ЛС
    if message.chat.type != "private":
        await message.answer("Эта команда работает только в личке.")
        return

    user_id = message.from_user.id
    # Находим все чаты, где пользователь есть среди админов
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT chats.chat_id, chats.chat_title
            FROM chats
            JOIN participants ON chats.chat_id = participants.chat_id
            WHERE participants.user_id = ? AND participants.active = True
        """, (user_id,))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Не найдено чатов, где вы были замечены как админ или активный участник.")
        return

    text = "Ваши чаты:\n"
    for chat_id, chat_title in rows:
        text += f"— {chat_title or 'Без названия'}: `{chat_id}`\n"

    text += "\nДля отчёта за сегодня: `/report <chat_id>`\nДля другой даты: `/report <chat_id> YYYY-MM-DD`"
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("report"))
async def cmd_report(message: Message, command: CommandObject):
    """Получить отчеты за указанную дату"""
    # Сначала добавим всех админов в participants
    await ensure_admins_in_db(bot, message.chat.id)

    # Проверка, что только админ может вызвать команду
    if message.chat.type == "private":
        # В ЛС: admin может получить отчёт только по чатам, где он админ
        args = (command.args or "").strip().split()
        if not args:
            await message.answer("Используй: /report <chat_id> [дата в формате YYYY-MM-DD]")
            return
        chat_id = args[0]
        # Проверяем, админ ли пользователь в этом чате
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT 1 FROM participants
                WHERE chat_id = ? AND user_id = ? AND active = True AND is_admin = True
            """, (chat_id, message.from_user.id))
            is_admin = await cursor.fetchone()
        if not is_admin:
            await message.answer("Команда /report доступна только администраторам указанного чата.")
            return
        date_str = datetime.now(pytz_timezone(TIMEZONE)).strftime("%Y-%m-%d")
        if len(args) > 1:
            date_str = args[1]
    else:
        # В группе: admin — это тот, кто сейчас админ через Telegram API
        chat_id = str(message.chat.id)
        args = (command.args or "").strip().split()
        if args:
            date_str = args[0]
        else:
            date_str = datetime.now(pytz_timezone(TIMEZONE)).strftime("%Y-%m-%d")

        admins = await bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]
        if message.from_user.id not in admin_ids:
            await message.answer("Команда /report доступна только администраторам этого чата.")
            return

    # Проверка даты
    if not re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        await message.answer("Дата в формате YYYY-MM-DD, например: 2024-06-12")
        return

    # Собираем все отчёты
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT participants.username, participants.user_id, daily_reports.text
            FROM daily_reports
            JOIN participants ON
                daily_reports.chat_id = participants.chat_id AND daily_reports.user_id = participants.user_id
            WHERE daily_reports.chat_id = ? AND daily_reports.date = ?
            ORDER BY participants.username, participants.user_id
        """, (chat_id, date_str))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Нет отчётов за эту дату.")
        return

    text = f"Отчёты за {date_str}:\n\n"
    for username, user_id, report in rows:
        user_ref = f"@{username}" if username else f"user_id: {user_id}"
        text += f"{user_ref}:\n{report}\n\n"

    # Если команда из ЛС — просто выводим текст. Если в чате — лучше отправить только админу
    if message.chat.type == "private":
        await message.answer(text)
    else:
        await message.answer("Отправил вам отчёты в личку.")
        await bot.send_message(message.from_user.id, text)
    
    logger.info(f"Отчеты за {date_str} отправлены пользователю {message.from_user.id} для чата {chat_id}")

