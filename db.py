import aiosqlite
import logging
from aiogram import Bot

logger = logging.getLogger(__name__)

DB_PATH = "bot.db"
DB_VERSION = 1  # Версия схемы базы данных

async def init_db():
    """Инициализация базы данных с версионированием и индексами"""
    async with aiosqlite.connect(DB_PATH) as db:
        logger.info("Инициализация базы данных...")
        
        # Создаем таблицу версий схемы
        await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Всегда создаем таблицы (IF NOT EXISTS безопасен)
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
        
        # Создаем индексы для оптимизации запросов
        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_reports_date 
        ON daily_reports(chat_id, date)
        """)
        
        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_participants_active 
        ON participants(chat_id, active)
        """)
        
        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_participants_username 
        ON participants(chat_id, username)
        """)
        
        # Проверяем/обновляем версию схемы
        cursor = await db.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = await cursor.fetchone()
        current_version = row[0] if row else 0
        
        if current_version < DB_VERSION:
            logger.info(f"Обновление схемы БД с версии {current_version} до {DB_VERSION}")
            if current_version == 0:
                await db.execute("INSERT INTO schema_version (version) VALUES (?)", (DB_VERSION,))
            else:
                await db.execute("INSERT INTO schema_version (version) VALUES (?)", (DB_VERSION,))
            logger.info(f"✅ База данных успешно инициализирована (версия {DB_VERSION})")
        else:
            logger.info(f"База данных актуальна (версия {current_version})")
        
        await db.commit()

async def ensure_admins_in_db(bot: Bot, chat_id):
    """Убедиться что все админы чата есть в базе participants"""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        async with aiosqlite.connect(DB_PATH) as db:
            added = 0
            updated = 0
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
                    updated += 1
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
                    added += 1
            await db.commit()
            if added > 0 or updated > 0:
                logger.info(f"Синхронизация админов для чата {chat_id}: добавлено {added}, обновлено {updated}")
    except Exception as e:
        logger.error(f"Ошибка при синхронизации админов для чата {chat_id}: {e}") 