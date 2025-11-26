"""
Задачи планировщика - отправка дэйликов и проверка отчетов
"""
import asyncio
import logging
import html
from datetime import datetime, timedelta
import aiosqlite
from pytz import timezone as pytz_timezone

from config import (
    DB_PATH,
    TIMEZONE,
    DAILY_TEXT,
    DAILY_CHECK_INTERVAL_HOURS,
    MAX_MENTIONS_PER_MESSAGE
)
from bot_instance import bot, scheduler, loop
from utils import is_workday

logger = logging.getLogger(__name__)


async def schedule_all_dailies():
    """
    Планирует отправку дэйликов для всех чатов согласно их расписанию
    Вызывается при запуске бота и после изменения времени рассылки
    """
    scheduler.remove_all_jobs()
    moscow_tz = pytz_timezone(TIMEZONE)
    now_msk = datetime.now(moscow_tz)
    logger.info(f"Сейчас в Москве: {now_msk.strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT chat_id, daily_time FROM chats WHERE daily_time IS NOT NULL"
        )
        chats = await cursor.fetchall()
    
    for chat_id, daily_time in chats:
        hour, minute = map(int, daily_time.split(":"))
        logger.info(f"Добавляю задачу для чата {chat_id}: {daily_time} (hour={hour}, minute={minute})")

        def make_job(chat_id_inner):
            """Фабрика для создания job с правильным замыканием chat_id"""
            def job():
                now_msk = datetime.now(pytz_timezone(TIMEZONE))
                logger.info(
                    f"Сработала задача для чата {chat_id_inner} — "
                    f"сейчас в МСК {now_msk.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                # Используем только глобальный loop!
                asyncio.run_coroutine_threadsafe(send_scheduled_daily(chat_id_inner), loop)
            return job
        
        scheduler.add_job(
            make_job(chat_id),
            "cron",
            hour=hour,
            minute=minute,
            timezone=moscow_tz
        )
    
    logger.info("Расписания дэйликов добавлены для всех чатов.")


async def send_scheduled_daily(chat_id):
    """
    Отправляет дэйлик в указанный чат и планирует проверку отчетов
    
    Args:
        chat_id: ID чата для отправки дэйлика
    """
    if not is_workday():
        logger.info("Сегодня выходной или праздник — дэйлик не отправляется.")
        return
    
    logger.info(f"send_scheduled_daily запускается для {chat_id}")
    sent = await bot.send_message(chat_id, DAILY_TEXT)
    last_daily_message_id = sent.message_id
    date_today = datetime.now(pytz_timezone(TIMEZONE)).strftime("%Y-%m-%d")
    
    # Планируем проверку отчетов через N часов
    scheduler.add_job(
        check_daily_reports,
        "date",
        run_date=datetime.now(pytz_timezone(TIMEZONE)) + timedelta(hours=DAILY_CHECK_INTERVAL_HOURS),
        args=[chat_id, last_daily_message_id, date_today]
    )
    logger.info(f"Дэйлик отправлен по расписанию в чат {chat_id}")


async def check_daily_reports(chat_id, daily_message_id, date_today):
    """
    Проверяет кто не сдал отчет и отправляет напоминания
    
    Args:
        chat_id: ID чата
        daily_message_id: ID сообщения с дэйликом
        date_today: Дата в формате YYYY-MM-DD
    """
    logger.info(f"Запущена проверка отчетов за {date_today} в чате {chat_id}")
    
    # Получаем всех активных участников
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, username FROM participants WHERE chat_id = ? AND active = True",
            (chat_id,)
        )
        users = await cursor.fetchall()

        # Получаем тех, кто уже сдал отчет
        cursor = await db.execute(
            "SELECT user_id FROM daily_reports WHERE chat_id = ? AND date = ?",
            (chat_id, date_today)
        )
        reporters = {row[0] for row in await cursor.fetchall()}

    # Находим неотчитавшихся
    not_reported = [(u_id, uname) for u_id, uname in users if u_id not in reporters]
    logger.info(f"Неотчитались ({len(not_reported)} человек): {not_reported}")
    
    if not_reported:
        # Rate limiting: отправляем по частям, если слишком много упоминаний
        for i in range(0, len(not_reported), MAX_MENTIONS_PER_MESSAGE):
            batch = not_reported[i:i + MAX_MENTIONS_PER_MESSAGE]
            mentions = []
            
            for user_id, username in batch:
                # Пытаемся получить красивое имя пользователя
                try:
                    if username:
                        display_name = html.escape(username)
                    else:
                        # Пробуем получить имя через API
                        try:
                            member = await bot.get_chat_member(chat_id, user_id)
                            display_name = html.escape(member.user.first_name or f"User {user_id}")
                        except Exception:
                            display_name = f"User {user_id}"
                    
                    mention = f'<a href="tg://user?id={user_id}">{display_name}</a>'
                    mentions.append(mention)
                except Exception as e:
                    logger.error(f"Ошибка при создании упоминания для user_id={user_id}: {e}")
            
            if mentions:
                mention_text = " ".join(mentions)
                text = f"{mention_text}\nЖду Текстовый Дейлик!"
                try:
                    await bot.send_message(chat_id, text, parse_mode="HTML")
                    # Защита от rate limit между батчами
                    if i + MAX_MENTIONS_PER_MESSAGE < len(not_reported):
                        await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")

