"""
Глобальные объекты бота
Вынесены в отдельный модуль для избежания циклических импортов
"""
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN

# Глобальные объекты
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Event loop (инициализируется в main)
loop = None


def set_event_loop(event_loop):
    """Устанавливает event loop (вызывается из main.py)"""
    global loop
    loop = event_loop

