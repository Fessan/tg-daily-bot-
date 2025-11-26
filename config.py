"""
Конфигурация бота - константы и настройки
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден в .env файле! "
        "Создайте .env файл с BOT_TOKEN=ваш_токен"
    )

# Путь к базе данных
DB_PATH = "bot.db"

# Временная зона
TIMEZONE = "Europe/Moscow"

# Интервалы времени (в секундах/часах)
DAILY_CHECK_INTERVAL_HOURS = 2      # Через сколько часов проверять отчеты
CLEANUP_MESSAGE_SECONDS = 1800      # Через сколько секунд удалять служебные сообщения (30 мин)

# Лимиты
MAX_MENTIONS_PER_MESSAGE = 50       # Максимум упоминаний в одном сообщении (rate limiting)

# Текст сообщений
DAILY_TEXT = (
    "Текстовый дейлик:\n"
    "1. Что делали?\n"
    "2. Какие были проблемы?\n"
    "3. Что планируете делать?"
)

# Логирование
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

