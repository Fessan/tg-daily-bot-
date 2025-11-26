"""
Обработчик ответов на дэйлики
"""
import logging
import aiosqlite
from datetime import datetime
from pytz import timezone as pytz_timezone
from aiogram.types import Message

from config import DB_PATH, TIMEZONE
from bot_instance import bot, dp

logger = logging.getLogger(__name__)


@dp.message()
async def handle_reply(message: Message):
    """
    Обрабатывает ответы пользователей на дэйлики
    Сохраняет отчеты в базу данных и управляет статусом участников
    """
    # Проверяем, что это reply на сообщение бота
    if not message.reply_to_message or message.reply_to_message.from_user.id != bot.id:
        return
    
    # Разрешаем только reply на дейлик или напоминание
    parent_text = message.reply_to_message.text or ""
    if not (
        parent_text.startswith("Текстовый дейлик:") or
        "Жду Текстовый Дейлик" in parent_text
    ):
        return  # Игнорируем любые другие reply на сообщения бота
    
    # Открываем соединение один раз на всё
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM participants WHERE chat_id = ? AND user_id = ?",
            (message.chat.id, message.from_user.id)
        )
        user = await cursor.fetchone()
        
        if not user:
            # Новый участник - добавляем в базу
            await db.execute(
                "INSERT INTO participants (chat_id, user_id, username, active) VALUES (?, ?, ?, ?)",
                (message.chat.id, message.from_user.id, 
                 message.from_user.username or message.from_user.full_name, True)
            )
            await db.commit()
            logger.info(
                f"Добавлен новый участник: {message.from_user.username or message.from_user.full_name} "
                f"(user_id: {message.from_user.id})"
            )
        elif user and not user[3]:  # user[3] — это поле active
            # Участник был неактивен - возвращаем его в активные
            await db.execute(
                "UPDATE participants SET active = True WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, message.from_user.id)
            )
            await db.commit()
            logger.info(
                f"Участник снова стал активным: {message.from_user.username or message.from_user.full_name} "
                f"(user_id: {message.from_user.id})"
            )

        # Сохраняем или обновляем отчет в daily_reports
        moscow_tz = pytz_timezone(TIMEZONE)
        today = datetime.now(moscow_tz).strftime("%Y-%m-%d")
        created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")

        await db.execute(
            """
            INSERT INTO daily_reports
                (chat_id, user_id, date, reply_to_message_id, message_id, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id, date) DO UPDATE SET
                reply_to_message_id=excluded.reply_to_message_id,
                message_id=excluded.message_id,
                text=excluded.text,
                created_at=excluded.created_at
            """,
            (
                message.chat.id,
                message.from_user.id,
                today,
                message.reply_to_message.message_id,
                message.message_id,
                message.text,
                created_at
            )
        )
        await db.commit()
        logger.info(
            f"Сохранён отчет от {message.from_user.username or message.from_user.full_name} "
            f"(user_id: {message.from_user.id}) за {today}"
        )
    
    # Можно добавить реакцию к сообщению пользователя (если всё успешно)
    # await message.reply("✅")

