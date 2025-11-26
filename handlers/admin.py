"""
Обработчики команд для администраторов
"""
import asyncio
import logging
import aiosqlite
from aiogram.types import Message
from aiogram.filters import Command, CommandObject

from config import DB_PATH, DAILY_TEXT, CLEANUP_MESSAGE_SECONDS
from bot_instance import bot, dp
from db import ensure_admins_in_db
from scheduler_tasks import schedule_all_dailies
from utils import delete_later

logger = logging.getLogger(__name__)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Инициализация бота в группе - добавление чата и админов в БД"""
    # Проверяем, что команда написана в групповом чате
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в групповых чатах.")
        return

    # Получаем список админов чата
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]

    # Проверяем, что пользователь — админ чата
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ чата может запускать бота.")
        return
    
    # Добавляем чат в базу (если ещё не добавлен)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO chats (chat_id, chat_title, daily_time) VALUES (?, ?, ?)",
            (message.chat.id, message.chat.title, None)
        )
        await db.commit()
        # Получаем чат из базы для проверки и выводим в лог
        async with db.execute("SELECT * FROM chats WHERE chat_id = ?", (message.chat.id,)) as cursor:
            row = await cursor.fetchone()
            logger.info(f"Чат из базы: {row}")
        
        # Добавляем всех админов как участников (active=True, is_admin=True)
        added = 0
        async with aiosqlite.connect(DB_PATH) as db:
            for admin in admins:
                await db.execute(
                    "INSERT OR IGNORE INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (message.chat.id, admin.user.id, admin.user.username or admin.user.full_name, True, True)
                )
                added += 1
            await db.commit()
        logger.info(f"Добавлено админов в чат {message.chat.id}: {added}")

    await message.answer("Бот успешно активирован! (пока только тест)")


@dp.message(Command("settime"))
async def cmd_settime(message: Message, command: CommandObject):
    """Установка времени ежедневной рассылки дэйликов"""
    # Проверка: только для группы
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только для админа
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может менять время рассылки.")
        return

    # Проверяем аргумент (время)
    if not command.args:
        await message.answer("Укажи время в формате HH:MM, например: /settime 10:00")
        return

    time_str = command.args.strip()
    # Простейшая валидация формата времени
    try:
        hour, minute = map(int, time_str.split(":"))
        assert 0 <= hour < 24 and 0 <= minute < 60
    except Exception:
        await message.answer("Некорректный формат. Используй: /settime 10:00")
        return

    # Сохраняем в базу
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE chats SET daily_time = ? WHERE chat_id = ?",
            (time_str, message.chat.id)
        )
        await db.commit()
    
    await message.answer(f"Время ежедневной рассылки установлено на {time_str}.")
    await schedule_all_dailies()

    logger.info(f"Чат {message.chat.id}: daily_time обновлено на {time_str}")


@dp.message(Command("testdaily"))
async def cmd_testdaily(message: Message):
    """Тестовая отправка дэйлика немедленно"""
    # Проверяем, что команда написана в групповом чате
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в групповых чатах.")
        return

    # Получаем список админов чата
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]

    # Проверяем, что пользователь — админ чата
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ чата может отправлять дэйлик.")
        return

    # Отправляем дэйлик
    sent = await message.answer(DAILY_TEXT)
    logger.info(f"Тестовый дэйлик отправлен в чат {message.chat.id}")


@dp.message(Command("exclude"))
async def cmd_exclude(message: Message, command: CommandObject):
    """Исключить участника из списка напоминаний о дэйлике"""
    # Сначала добавим всех админов в participants
    await ensure_admins_in_db(bot, message.chat.id)
    
    # Проверка: только в группе
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только админ может использовать
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может исключать участников.")
        return

    # Получаем аргумент команды
    if not command.args:
        await message.answer("Укажи username или user_id (например: /exclude @username или /exclude 123456789).")
        return

    arg = command.args.strip()
    user_id = None

    # Проверяем, это user_id или username
    if arg.isdigit():
        user_id = int(arg)
    else:
        username = arg.lstrip("@")
        # Ищем user_id по username
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT user_id FROM participants WHERE chat_id = ? AND username = ?",
                (message.chat.id, username)
            )
            row = await cursor.fetchone()
            if row:
                user_id = row[0]

    if not user_id:
        await message.answer("Пользователь не найден в базе.")
        return

    # Делаем active = False (исключаем из списка)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE participants SET active = False WHERE chat_id = ? AND user_id = ?",
            (message.chat.id, user_id)
        )
        await db.commit()

    await message.answer(f"Пользователь с user_id {user_id} больше не будет получать напоминания о дэйлике.")
    logger.info(f"Пользователь {user_id} исключен из активных в чате {message.chat.id}")


@dp.message(Command("include"))
async def cmd_include(message: Message, command: CommandObject):
    """Вернуть участника в список напоминаний о дэйлике"""
    # Сначала добавим всех админов в participants
    await ensure_admins_in_db(bot, message.chat.id)
    
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может возвращать участников.")
        return

    if not command.args:
        await message.answer("Укажи username или user_id (например: /include @username или /include 123456789).")
        return

    arg = command.args.strip()
    user_id = None
    username = None

    if arg.isdigit():
        user_id = int(arg)
    else:
        username = arg.lstrip("@")

    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Пытаемся найти в базе
        if user_id:
            cursor = await db.execute(
                "SELECT user_id, username FROM participants WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, user_id)
            )
        else:
            cursor = await db.execute(
                "SELECT user_id, username FROM participants WHERE chat_id = ? AND username = ?",
                (message.chat.id, username)
            )
        row = await cursor.fetchone()

        if row:
            await db.execute(
                "UPDATE participants SET active = True WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, row[0])
            )
            await db.commit()
            await message.answer(f"Пользователь с user_id {row[0]} теперь снова в списке активных.")
            logger.info(f"Пользователь {row[0]} возвращен в активные в чате {message.chat.id}")
        else:
            # 2. Пытаемся найти участника через get_chat_member
            try:
                member = None
                if user_id:
                    member = await bot.get_chat_member(message.chat.id, user_id)
                elif username:
                    try:
                        # get_chat_member работает и по username, если тот уникальный в чате
                        member = await bot.get_chat_member(message.chat.id, username)
                    except Exception:
                        # Если вдруг username не сработал — пробуем собрать всех, у кого username совпадает
                        chat_adms = await bot.get_chat_administrators(message.chat.id)
                        for m in chat_adms:
                            if m.user.username and m.user.username.lower() == username.lower():
                                member = m
                                break

                if member:
                    user_id_to_add = member.user.id
                    username_to_add = member.user.username
                    await db.execute(
                        "INSERT OR REPLACE INTO participants (chat_id, user_id, username, active) VALUES (?, ?, ?, ?)",
                        (message.chat.id, user_id_to_add, username_to_add, True)
                    )
                    await db.commit()
                    await message.answer(f"Пользователь @{username_to_add or user_id_to_add} добавлен в список активных и теперь должен сдавать отчёты.")
                    logger.info(f"Пользователь {user_id_to_add} добавлен в активные в чате {message.chat.id}")
                else:
                    await message.answer(
                        "Не удалось найти пользователя в чате.\n"
                        "Проверь корректность user_id или username и убедись, что пользователь писал в чат.\n"
                        "Лайфхак: пусть участник просто ответит реплаем на дэйлик, чтобы бот 100% его увидел."
                    )
            except Exception as e:
                logger.error(f"Ошибка при добавлении пользователя в чате {message.chat.id}: {e}")
                await message.answer(f"Ошибка при добавлении: {e}")


@dp.message(Command("list_active"))
async def cmd_list_active(message: Message):
    """Показать список активных участников (получающих напоминания)"""
    # Сначала добавим всех админов в participants
    await ensure_admins_in_db(bot, message.chat.id)
    
    # Проверка: только для группы
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только для админа
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может просматривать список.")
        return

    # Получаем всех активных участников
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, username FROM participants WHERE chat_id = ? AND active = True",
            (message.chat.id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Список активных участников пуст.")
        return

    # Формируем текст ответа
    text = "Активные участники:\n"
    for user_id, username in rows:
        if username:
            text += f"— @{username} ({user_id})\n"
        else:
            text += f"— user_id: {user_id}\n"

    # В чате — отправляем только "Результат отправил вам в личку!" и удаляем через 30 мин
    if message.chat.type in ("group", "supergroup"):
        msg = await message.answer("Результат отправил вам в личку!")
        asyncio.create_task(delete_later(msg, seconds=CLEANUP_MESSAGE_SECONDS))
        await bot.send_message(message.from_user.id, text)
    else:
        await message.answer(text)


@dp.message(Command("list_all"))
async def cmd_list_all(message: Message):
    """Показать полный список участников со статусами"""
    # Сначала добавим всех админов в participants
    await ensure_admins_in_db(bot, message.chat.id)

    # Проверка: только для группы
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только для админа
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может просматривать список.")
        return

    # Получаем всех участников чата (active и неактивных)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, username, active FROM participants WHERE chat_id = ?",
            (message.chat.id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Участников пока нет в базе.")
        return

    # Формируем текст ответа
    text = "Все участники:\n"
    for user_id, username, active in rows:
        active_status = "✅" if active else "❌"
        if username:
            text += f"{active_status} @{username} ({user_id})\n"
        else:
            text += f"{active_status} user_id: {user_id}\n"

    # В чате — только уведомление, сам отчёт шлём в ЛС
    msg = await message.answer("Отправил список участников вам в личку!")
    asyncio.create_task(delete_later(msg, seconds=CLEANUP_MESSAGE_SECONDS))
    try:
        await bot.send_message(message.from_user.id, text)
    except Exception as e:
        logger.error(f"Не удалось отправить список в ЛС пользователю {message.from_user.id}: {e}")
        await message.answer(
            "Не удалось отправить список участников в личку. Напишите боту в ЛС (например, /start), чтобы получать личные сообщения."
        )

