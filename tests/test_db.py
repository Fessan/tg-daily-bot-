"""
Unit и Integration тесты для модуля db
"""
import pytest
import aiosqlite


class TestDatabaseInit:
    """Тесты инициализации базы данных"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, test_db):
        """init_db создает все необходимые таблицы"""
        async with aiosqlite.connect(test_db) as db:
            # Проверяем наличие таблиц
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            assert 'chats' in tables
            assert 'participants' in tables
            assert 'daily_reports' in tables
            assert 'schema_version' in tables
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_init_db_creates_indexes(self, test_db):
        """init_db создает индексы"""
        async with aiosqlite.connect(test_db) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = [row[0] for row in await cursor.fetchall()]
            
            assert 'idx_daily_reports_date' in indexes
            assert 'idx_participants_active' in indexes
            assert 'idx_participants_username' in indexes
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_schema_version_set(self, test_db):
        """Версия схемы установлена корректно"""
        async with aiosqlite.connect(test_db) as db:
            cursor = await db.execute("SELECT version FROM schema_version")
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[0] == 1  # Текущая версия


class TestChatsTable:
    """Тесты таблицы chats"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_insert_chat(self, test_db):
        """Добавление чата в БД"""
        async with aiosqlite.connect(test_db) as db:
            await db.execute(
                "INSERT INTO chats (chat_id, chat_title, daily_time) VALUES (?, ?, ?)",
                (-100123, "Test Chat", "10:00")
            )
            await db.commit()
            
            cursor = await db.execute("SELECT * FROM chats WHERE chat_id = ?", (-100123,))
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[0] == -100123
            assert row[1] == "Test Chat"
            assert row[2] == "10:00"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_chat_daily_time(self, test_db):
        """Обновление времени рассылки"""
        async with aiosqlite.connect(test_db) as db:
            await db.execute(
                "INSERT INTO chats (chat_id, chat_title, daily_time) VALUES (?, ?, ?)",
                (-100124, "Test Chat 2", "10:00")
            )
            await db.commit()
            
            await db.execute(
                "UPDATE chats SET daily_time = ? WHERE chat_id = ?",
                ("14:30", -100124)
            )
            await db.commit()
            
            cursor = await db.execute("SELECT daily_time FROM chats WHERE chat_id = ?", (-100124,))
            row = await cursor.fetchone()
            
            assert row[0] == "14:30"


class TestParticipantsTable:
    """Тесты таблицы participants"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_insert_participant(self, populated_db):
        """Добавление участника"""
        async with aiosqlite.connect(populated_db) as db:
            await db.execute(
                "INSERT INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
                (-1001234567890, 444444444, "new_user", True, False)
            )
            await db.commit()
            
            cursor = await db.execute(
                "SELECT * FROM participants WHERE user_id = ?", (444444444,)
            )
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[1] == 444444444
            assert row[2] == "new_user"
            assert row[3] == 1  # active = True
            assert row[4] == 0  # is_admin = False
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_active_participants(self, populated_db):
        """Получение активных участников"""
        async with aiosqlite.connect(populated_db) as db:
            cursor = await db.execute(
                "SELECT user_id FROM participants WHERE chat_id = ? AND active = True",
                (-1001234567890,)
            )
            users = await cursor.fetchall()
            
            # Должно быть 2 активных (admin_user и regular_user)
            assert len(users) == 2
            user_ids = [row[0] for row in users]
            assert 111111111 in user_ids
            assert 222222222 in user_ids
            assert 333333333 not in user_ids  # inactive


class TestDailyReportsTable:
    """Тесты таблицы daily_reports"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_insert_report(self, populated_db):
        """Добавление отчета"""
        async with aiosqlite.connect(populated_db) as db:
            await db.execute(
                """INSERT INTO daily_reports 
                   (chat_id, user_id, date, reply_to_message_id, message_id, text, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (-1001234567890, 222222222, "2025-11-26", 20001, 20002,
                 "Test report", "2025-11-26 11:00:00")
            )
            await db.commit()
            
            cursor = await db.execute(
                "SELECT * FROM daily_reports WHERE user_id = ? AND date = ?",
                (222222222, "2025-11-26")
            )
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[2] == "2025-11-26"
            assert row[5] == "Test report"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_report_on_conflict(self, populated_db):
        """Обновление отчета при повторной отправке (ON CONFLICT)"""
        async with aiosqlite.connect(populated_db) as db:
            # Первый отчет
            await db.execute(
                """INSERT INTO daily_reports 
                   (chat_id, user_id, date, reply_to_message_id, message_id, text, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(chat_id, user_id, date) DO UPDATE SET
                       text=excluded.text,
                       created_at=excluded.created_at""",
                (-1001234567890, 222222222, "2025-11-27", 30001, 30002,
                 "First version", "2025-11-27 10:00:00")
            )
            await db.commit()
            
            # Обновленный отчет
            await db.execute(
                """INSERT INTO daily_reports 
                   (chat_id, user_id, date, reply_to_message_id, message_id, text, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(chat_id, user_id, date) DO UPDATE SET
                       text=excluded.text,
                       created_at=excluded.created_at""",
                (-1001234567890, 222222222, "2025-11-27", 30001, 30003,
                 "Updated version", "2025-11-27 11:00:00")
            )
            await db.commit()
            
            # Проверяем что отчет обновился
            cursor = await db.execute(
                "SELECT text, created_at FROM daily_reports WHERE user_id = ? AND date = ?",
                (222222222, "2025-11-27")
            )
            row = await cursor.fetchone()
            
            assert row[0] == "Updated version"
            assert row[1] == "2025-11-27 11:00:00"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_reports_by_date(self, populated_db):
        """Получение отчетов за дату"""
        async with aiosqlite.connect(populated_db) as db:
            cursor = await db.execute(
                """SELECT participants.username, daily_reports.text
                   FROM daily_reports
                   JOIN participants ON 
                       daily_reports.chat_id = participants.chat_id AND 
                       daily_reports.user_id = participants.user_id
                   WHERE daily_reports.chat_id = ? AND daily_reports.date = ?""",
                (-1001234567890, "2025-11-26")
            )
            reports = await cursor.fetchall()
            
            assert len(reports) == 1
            assert reports[0][0] == "admin_user"
            assert "рефакторинг" in reports[0][1]


class TestEnsureAdminsInDb:
    """Тесты функции ensure_admins_in_db"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ensure_admins_adds_new_admin(self, test_db, mock_bot, mock_admin_user):
        """Функция добавляет нового админа"""
        from db import ensure_admins_in_db
        import config
        
        # Подменяем путь к БД
        original = config.DB_PATH
        config.DB_PATH = test_db
        
        # Добавляем чат
        async with aiosqlite.connect(test_db) as db:
            await db.execute(
                "INSERT INTO chats (chat_id, chat_title) VALUES (?, ?)",
                (-100125, "Test Chat")
            )
            await db.commit()
        
        # Mock для get_chat_administrators
        mock_bot.get_chat_administrators.return_value = [mock_admin_user]
        
        # Вызываем функцию
        await ensure_admins_in_db(mock_bot, -100125)
        
        # Проверяем что админ добавлен
        async with aiosqlite.connect(test_db) as db:
            cursor = await db.execute(
                "SELECT * FROM participants WHERE chat_id = ? AND user_id = ?",
                (-100125, 111111111)
            )
            row = await cursor.fetchone()
            
            assert row is not None
            assert row[4] == 1  # is_admin = True
        
        # Восстанавливаем
        config.DB_PATH = original

