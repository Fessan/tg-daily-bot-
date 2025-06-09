import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import aiosqlite
from datetime import datetime
from aiogram.filters import CommandObject


DB_PATH = "bot.db"  # Имя файла базы данных

async def migrate_participants_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("ALTER TABLE participants ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;")
        await db.commit()
    print("Миграция завершена: поле is_admin добавлено.")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица чатов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            daily_time TEXT
        );
        """)

        # Таблица участников
        await db.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (chat_id, user_id)
        );
        """)

        # Таблица дэйликов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            chat_id INTEGER,
            user_id INTEGER,
            date TEXT,
            reply_to_message_id INTEGER,
            message_id INTEGER,
            text TEXT,
            created_at TEXT,
            PRIMARY KEY (chat_id, user_id, date)
        );
        """)

        await db.commit()  # Применяем все изменения


# Загружаем переменные окружения из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
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
        # Получаем чат из базы для проверки и выводим в консоль
        async with db.execute("SELECT * FROM chats WHERE chat_id = ?", (message.chat.id,)) as cursor:
            row = await cursor.fetchone()
            print("Чат из базы:", row)
        
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
        print(f"Добавлено админов: {added}")

    await message.answer("Бот успешно активирован! (пока только тест)")



@dp.message(Command("testdaily"))
async def cmd_testdaily(message: Message):
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

    # Текст дэйлика
    daily_text = (
        "Текстовый дейлик:\n"
        "1. Что делали?\n"
        "2. Какие были проблемы?\n"
        "3. Что планируете делать?"
    )
    await message.answer(daily_text)
@dp.message(Command("exclude"))
async def cmd_exclude(message: Message, command: CommandObject):
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


@dp.message()
async def handle_reply(message: Message):
    # Проверяем, что это reply на сообщение бота (то есть, человек отвечает на дэйлик)
    if not message.reply_to_message or message.reply_to_message.from_user.id != bot.id:
        return  # Не reply на сообщение бота — игнорируем

    # Проверяем, есть ли уже этот пользователь в базе
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM participants WHERE chat_id = ? AND user_id = ?",
            (message.chat.id, message.from_user.id)
        )
        user = await cursor.fetchone()
        if not user:
            # Добавляем пользователя в базу с active=True
            await db.execute(
                "INSERT INTO participants (chat_id, user_id, username, active) VALUES (?, ?, ?, ?)",
                (message.chat.id, message.from_user.id, message.from_user.username or message.from_user.full_name, True)
            )
            await db.commit()
            print(f"Добавлен новый участник: {message.from_user.username or message.from_user.full_name}")
 # Сохраняем или обновляем отчет в daily_reports
    today = datetime.now().strftime("%Y-%m-%d")  # Дата отчета
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Точное время

    async with aiosqlite.connect(DB_PATH) as db:
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
    print(f"Сохранён отчет от {message.from_user.username or message.from_user.full_name} за {today}")
 


async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
