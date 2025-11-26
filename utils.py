"""
Вспомогательные функции
"""
import asyncio
from datetime import datetime
import holidays
from pytz import timezone as pytz_timezone
from config import TIMEZONE


def is_workday():
    """
    Проверяет, является ли сегодня рабочим днем
    
    Returns:
        bool: True если рабочий день, False если выходной/праздник
    """
    today = datetime.now(pytz_timezone(TIMEZONE)).date()
    ru_holidays = holidays.RU(years=today.year)
    # Суббота (5) или воскресенье (6) — выходные, а также праздники РФ
    if today.weekday() >= 5 or today in ru_holidays:
        return False
    return True


async def delete_later(msg, seconds=1800):
    """
    Удаляет сообщение через указанное количество секунд
    
    Args:
        msg: Сообщение Telegram для удаления
        seconds: Через сколько секунд удалить (по умолчанию 1800 = 30 мин)
    """
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        # Сообщение уже могло быть удалено или права отозваны
        pass

