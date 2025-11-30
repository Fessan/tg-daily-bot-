"""
Unit тесты для модуля config
"""
import pytest
import os


class TestConfig:
    """Тесты для модуля конфигурации"""
    
    @pytest.mark.unit
    def test_bot_token_loaded(self):
        """BOT_TOKEN загружен из окружения"""
        import config
        assert config.BOT_TOKEN is not None
        assert len(config.BOT_TOKEN) > 0
    
    @pytest.mark.unit
    def test_db_path_defined(self):
        """Путь к БД определен"""
        import config
        assert config.DB_PATH == "bot.db"
    
    @pytest.mark.unit
    def test_timezone_configured(self):
        """Часовой пояс настроен"""
        import config
        assert config.TIMEZONE == "Europe/Moscow"
    
    @pytest.mark.unit
    def test_daily_check_interval(self):
        """Интервал проверки дэйликов"""
        import config
        assert config.DAILY_CHECK_INTERVAL_HOURS == 2
        assert isinstance(config.DAILY_CHECK_INTERVAL_HOURS, int)
    
    @pytest.mark.unit
    def test_cleanup_message_seconds(self):
        """Время удаления сообщений"""
        import config
        assert config.CLEANUP_MESSAGE_SECONDS == 1800
        assert isinstance(config.CLEANUP_MESSAGE_SECONDS, int)
    
    @pytest.mark.unit
    def test_max_mentions_per_message(self):
        """Максимум упоминаний в сообщении"""
        import config
        assert config.MAX_MENTIONS_PER_MESSAGE == 50
        assert isinstance(config.MAX_MENTIONS_PER_MESSAGE, int)
    
    @pytest.mark.unit
    def test_daily_text_defined(self):
        """Текст дэйлика определен"""
        import config
        assert config.DAILY_TEXT is not None
        assert "Текстовый дейлик" in config.DAILY_TEXT
        assert "Что делали?" in config.DAILY_TEXT
        assert "Какие были проблемы?" in config.DAILY_TEXT
        assert "Что планируете делать?" in config.DAILY_TEXT
    
    @pytest.mark.unit
    def test_log_file_defined(self):
        """Файл логов определен"""
        import config
        assert config.LOG_FILE == "bot.log"
    
    @pytest.mark.unit
    def test_log_level_defined(self):
        """Уровень логирования определен"""
        import config
        assert config.LOG_LEVEL == "INFO"
    
    @pytest.mark.unit
    def test_log_format_defined(self):
        """Формат логирования определен"""
        import config
        assert config.LOG_FORMAT is not None
        assert "%(asctime)s" in config.LOG_FORMAT
        assert "%(levelname)s" in config.LOG_FORMAT


class TestConfigValidation:
    """Тесты валидации конфигурации"""
    
    @pytest.mark.unit
    def test_bot_token_not_empty_after_load(self):
        """BOT_TOKEN не пустой после загрузки"""
        import config
        # Токен должен быть установлен в conftest.py
        assert config.BOT_TOKEN
        assert len(config.BOT_TOKEN.strip()) > 0










