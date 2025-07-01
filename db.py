import aiosqlite
from aiogram import Bot

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            daily_time TEXT
        );
        """)
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
        await db.commit()

async def ensure_admins_in_db(bot: Bot, chat_id):
    admins = await bot.get_chat_administrators(chat_id)
    async with aiosqlite.connect(DB_PATH) as db:
        for admin in admins:
            user = admin.user
            cursor = await db.execute(
                "SELECT active FROM participants WHERE chat_id = ? AND user_id = ?",
                (chat_id, user.id)
            )
            row = await cursor.fetchone()
            if row is not None:
                await db.execute(
                    "UPDATE participants SET username = ?, is_admin = True WHERE chat_id = ? AND user_id = ?",
                    (user.username or user.full_name, chat_id, user.id)
                )
            else:
                await db.execute(
                    "INSERT INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (
                        chat_id,
                        user.id,
                        user.username or user.full_name,
                        False,
                        True
                    )
                )
        await db.commit() 