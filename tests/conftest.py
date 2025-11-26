"""
Общие фикстуры для тестов
"""
import os
import tempfile
import pytest
import aiosqlite
from unittest.mock import AsyncMock, MagicMock

# Устанавливаем тестовые переменные окружения перед импортом модулей
os.environ['BOT_TOKEN'] = 'TEST_TOKEN_1234567890:ABCdefGHIjklMNOpqrsTUVwxyz'


@pytest.fixture
def temp_db():
    """Временная база данных для тестов"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def test_db(temp_db):
    """Инициализированная тестовая база данных"""
    from db import init_db
    import config
    
    # Подменяем путь к БД
    original_db_path = config.DB_PATH
    config.DB_PATH = temp_db
    
    # Инициализируем БД
    await init_db()
    
    yield temp_db
    
    # Восстанавливаем оригинальный путь
    config.DB_PATH = original_db_path


@pytest.fixture
def mock_bot():
    """Mock объект бота"""
    bot = AsyncMock()
    bot.id = 123456789
    bot.username = "test_bot"
    bot.send_message = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.get_chat_administrators = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Mock объект сообщения Telegram"""
    message = MagicMock()
    message.chat.id = -1001234567890
    message.chat.type = "supergroup"
    message.chat.title = "Test Chat"
    message.from_user.id = 987654321
    message.from_user.username = "testuser"
    message.from_user.full_name = "Test User"
    message.text = "Test message"
    message.message_id = 12345
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_admin_user():
    """Mock объект администратора"""
    admin = MagicMock()
    admin.user.id = 111111111
    admin.user.username = "admin_user"
    admin.user.full_name = "Admin User"
    return admin


@pytest.fixture
def mock_regular_user():
    """Mock объект обычного пользователя"""
    user = MagicMock()
    user.id = 222222222
    user.username = "regular_user"
    user.full_name = "Regular User"
    return user


@pytest.fixture
async def populated_db(test_db):
    """База данных с тестовыми данными"""
    async with aiosqlite.connect(test_db) as db:
        # Добавляем тестовый чат
        await db.execute(
            "INSERT INTO chats (chat_id, chat_title, daily_time) VALUES (?, ?, ?)",
            (-1001234567890, "Test Chat", "10:00")
        )
        
        # Добавляем участников
        await db.execute(
            "INSERT INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
            (-1001234567890, 111111111, "admin_user", True, True)
        )
        await db.execute(
            "INSERT INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
            (-1001234567890, 222222222, "regular_user", True, False)
        )
        await db.execute(
            "INSERT INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
            (-1001234567890, 333333333, "inactive_user", False, False)
        )
        
        # Добавляем тестовый отчет
        await db.execute(
            """INSERT INTO daily_reports 
               (chat_id, user_id, date, reply_to_message_id, message_id, text, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (-1001234567890, 111111111, "2025-11-26", 10001, 10002, 
             "1. Сделал рефакторинг\n2. Нет проблем\n3. Буду писать тесты", 
             "2025-11-26 10:30:00")
        )
        
        await db.commit()
    
    yield test_db


@pytest.fixture
def mock_scheduler():
    """Mock объект планировщика"""
    scheduler = MagicMock()
    scheduler.add_job = MagicMock()
    scheduler.remove_all_jobs = MagicMock()
    scheduler.start = MagicMock()
    scheduler.shutdown = MagicMock()
    return scheduler

