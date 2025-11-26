"""
Telegram Daily Bot - главный файл запуска

Telegram-бот для автоматизированного сбора ежедневных отчетов (дэйликов) 
в групповых чатах с расписанием по МСК, уведомлениями неотчитавшихся, 
управлением участниками и хранением в SQLite.

Автор: @Fessan
"""

import asyncio
import logging

from config import LOG_FILE, LOG_LEVEL, LOG_FORMAT
from bot_instance import bot, dp, scheduler, set_event_loop
from db import init_db
from scheduler_tasks import schedule_all_dailies

# Импортируем все обработчики (они автоматически регистрируются через декоратор @dp.message)
import handlers  # noqa: F401

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """
    Главная функция запуска бота
    
    Выполняет:
    1. Инициализацию базы данных
    2. Настройку event loop
    3. Запуск планировщика задач
    4. Планирование всех дэйликов
    5. Запуск polling бота
    """
    try:
        # Инициализируем базу данных
        await init_db()
        
        # Устанавливаем event loop для scheduler
        event_loop = asyncio.get_event_loop()
        set_event_loop(event_loop)
        
        # Запускаем планировщик
        scheduler.start()
        
        # Планируем все дэйлики из БД
        await schedule_all_dailies()
        
        logger.info("✅ Бот успешно запущен! Scheduler работает, жду рассылки...")
        
        # Запускаем polling
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise
    finally:
        logger.info("Завершение работы бота...")
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
