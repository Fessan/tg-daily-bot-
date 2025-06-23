import asyncio
import os
import holidays
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import aiosqlite
from datetime import datetime
from aiogram.filters import CommandObject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import timedelta
from pytz import timezone


def is_workday():
    today = datetime.now(timezone("Europe/Moscow")).date()
    ru_holidays = holidays.RU(years=today.year)
    # Суббота (5) или воскресенье (6) — выходные, а также праздники РФ
    if today.weekday() >= 5 or today in ru_holidays:
        return False
    return True

async def delete_later(msg, seconds=1800):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        pass
async def ensure_admins_in_db(chat_id):
    admins = await bot.get_chat_administrators(chat_id)
    async with aiosqlite.connect(DB_PATH) as db:
        for admin in admins:
            user = admin.user
            # Проверяем — есть ли уже в БД
            cursor = await db.execute(
                "SELECT active FROM participants WHERE chat_id = ? AND user_id = ?",
                (chat_id, user.id)
            )
            row = await cursor.fetchone()
            if row is not None:
                # Уже есть — НЕ меняем active, просто обновляем username/is_admin
                await db.execute(
                    "UPDATE participants SET username = ?, is_admin = True WHERE chat_id = ? AND user_id = ?",
                    (user.username or user.full_name, chat_id, user.id)
                )
            else:
                # Нет в participants — добавляем с active=False (не получит дейлик!)
                await db.execute(
                    "INSERT INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (
                        chat_id,
                        user.id,
                        user.username or user.full_name,
                        False,  # неактивен по умолчанию
                        True
                    )
                )
        await db.commit()

scheduler = AsyncIOScheduler()
DB_PATH = "bot.db"  # Имя файла базы данных
loop = None



async def schedule_all_dailies():
    scheduler.remove_all_jobs()
    moscow_tz = timezone("Europe/Moscow")
    now_msk = datetime.now(moscow_tz)
    print(f"[DEBUG] Сейчас в Москве: {now_msk.strftime('%Y-%m-%d %H:%M:%S')}")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT chat_id, daily_time FROM chats WHERE daily_time IS NOT NULL")
        chats = await cursor.fetchall()
    for chat_id, daily_time in chats:
        hour, minute = map(int, daily_time.split(":"))
        print(f"Добавляю задачу для чата {chat_id}: {daily_time} (hour={hour}, minute={minute})")

        def make_job(chat_id_inner):
            def job():
                now_msk = datetime.now(timezone("Europe/Moscow"))
                print(f"[DEBUG] Сработала задача для чата {chat_id_inner} — сейчас в МСК {now_msk.strftime('%Y-%m-%d %H:%M:%S')}")
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
    print("Расписания дэйликов добавлены для всех чатов.")

async def send_scheduled_daily(chat_id):
    if not is_workday():
        print("Сегодня выходной или праздник — дэйлик не отправляется.")
        return  # Не слать дэйлик
    print(f"[DEBUG] send_scheduled_daily запускается для {chat_id}")

    print(f"[DEBUG] send_scheduled_daily запускается для {chat_id}")
    daily_text = (
        "Текстовый дейлик:\n"
        "1. Что делали?\n"
        "2. Какие были проблемы?\n"
        "3. Что планируете делать?"
    )
    sent = await bot.send_message(chat_id, daily_text)
    last_daily_message_id = sent.message_id
    date_today = datetime.now(timezone("Europe/Moscow")).strftime("%Y-%m-%d")
    scheduler.add_job(
        check_daily_reports,
        "date",
        run_date=datetime.now(timezone("Europe/Moscow")) + timedelta(hours=2),  
        args=[chat_id, last_daily_message_id, date_today]
    )
    print(f"Дэйлик отправлен по расписанию в чат {chat_id}")



async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица чатов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            daily_time TEXT
        );
        """)

        # Таблица участников
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

        # Таблица дэйликов
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

        await db.commit()  # Применяем все изменения


# Загружаем переменные окружения из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("mychats"))
async def cmd_mychats(message: Message):
    # Обрабатываем только в ЛС
    if message.chat.type != "private":
        await message.answer("Эта команда работает только в личке.")
        return

    user_id = message.from_user.id
    # Находим все чаты, где пользователь есть среди админов
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT chats.chat_id, chats.chat_title
            FROM chats
            JOIN participants ON chats.chat_id = participants.chat_id
            WHERE participants.user_id = ? AND participants.active = True
        """, (user_id,))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Не найдено чатов, где вы были замечены как админ или активный участник.")
        return

    text = "Ваши чаты:\n"
    for chat_id, chat_title in rows:
        text += f"— {chat_title or 'Без названия'}: `{chat_id}`\n"

    text += "\nДля отчёта за сегодня: `/report <chat_id>`\nДля другой даты: `/report <chat_id> YYYY-MM-DD`"
    await message.answer(text, parse_mode="Markdown")




@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Проверяем, что команда написана в групповом чате
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в групповых чатах.")
        return

    # Получаем список админов чата
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]

    # Проверяем, что пользователь — админ чата
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ чата может запускать бота.")
        return
    
        # Добавляем чат в базу (если ещё не добавлен)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO chats (chat_id, chat_title, daily_time) VALUES (?, ?, ?)",
            (message.chat.id, message.chat.title, None)
        )
        await db.commit()
        # Получаем чат из базы для проверки и выводим в консоль
        async with db.execute("SELECT * FROM chats WHERE chat_id = ?", (message.chat.id,)) as cursor:
            row = await cursor.fetchone()
            print("Чат из базы:", row)
        
        # Добавляем всех админов как участников (active=True, is_admin=True)
        added = 0
        async with aiosqlite.connect(DB_PATH) as db:
            for admin in admins:
                await db.execute(
                    "INSERT OR IGNORE INTO participants (chat_id, user_id, username, active, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (message.chat.id, admin.user.id, admin.user.username or admin.user.full_name, True, True)
                )
                added += 1
            await db.commit()
        print(f"Добавлено админов: {added}")

    await message.answer("Бот успешно активирован! (пока только тест)")

@dp.message(Command("settime"))
async def cmd_settime(message: Message, command: CommandObject):
    # Проверка: только для группы
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только для админа
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может менять время рассылки.")
        return

    # Проверяем аргумент (время)
    if not command.args:
        await message.answer("Укажи время в формате HH:MM, например: /settime 10:00")
        return

    time_str = command.args.strip()
    # Простейшая валидация формата времени
    try:
        hour, minute = map(int, time_str.split(":"))
        assert 0 <= hour < 24 and 0 <= minute < 60
    except Exception:
        await message.answer("Некорректный формат. Используй: /settime 10:00")
        return

    # Сохраняем в базу
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE chats SET daily_time = ? WHERE chat_id = ?",
            (time_str, message.chat.id)
        )
        await db.commit()
    await message.answer(f"Время ежедневной рассылки установлено на {time_str}.")
    await schedule_all_dailies()

    print(f"Чат {message.chat.id}: daily_time обновлено на {time_str}")


@dp.message(Command("testdaily"))
async def cmd_testdaily(message: Message):
    # Проверяем, что команда написана в групповом чате
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в групповых чатах.")
        return

    # Получаем список админов чата
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]

    # Проверяем, что пользователь — админ чата
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ чата может отправлять дэйлик.")
        return

    # Текст дэйлика
    daily_text = (
        "Текстовый дейлик:\n"
        "1. Что делали?\n"
        "2. Какие были проблемы?\n"
        "3. Что планируете делать?"
    )

    sent = await message.answer(daily_text)
    # Сохраняем данные для напоминания
    last_daily_message_id = sent.message_id
    chat_id = message.chat.id
    date_today = datetime.now().strftime("%Y-%m-%d")

    # Планируем проверку через 1 минуту (для теста)
    scheduler.add_job(
        check_daily_reports,
        "date",
        run_date=datetime.now() + timedelta(minutes=1),
        args=[chat_id, last_daily_message_id, date_today]
    )


from datetime import timedelta

async def check_daily_reports(chat_id, daily_message_id, date_today):
    print(f"Запущена проверка отчетов за {date_today} в чате {chat_id}")
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
    print("Неотчитались:", not_reported)
    if not_reported:
        mentions = []
        for user_id, username in not_reported:
            if username:
                mentions.append(f"@{username}")
            else:
                mentions.append(f"[id{user_id}](tg://user?id={user_id})")
        mention_text = " ".join(mentions)
        text = f"{mention_text}\nЖду Текстовый Дейлик!"
        # Отправляем напоминание в чат
        await bot.send_message(chat_id, text, parse_mode="Markdown")
    else:
        print("Все сдали отчеты!")




@dp.message(Command("exclude"))
async def cmd_exclude(message: Message, command: CommandObject):
        # Сначала добавим всех админов в participants
    await ensure_admins_in_db(message.chat.id)
    # Проверка: только в группе
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только админ может использовать
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может исключать участников.")
        return

    # Получаем аргумент команды
    if not command.args:
        await message.answer("Укажи username или user_id (например: /exclude @username или /exclude 123456789).")
        return

    arg = command.args.strip()
    user_id = None

    # Проверяем, это user_id или username
    if arg.isdigit():
        user_id = int(arg)
    else:
        username = arg.lstrip("@")
        # Ищем user_id по username
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT user_id FROM participants WHERE chat_id = ? AND username = ?",
                (message.chat.id, username)
            )
            row = await cursor.fetchone()
            if row:
                user_id = row[0]

    if not user_id:
        await message.answer("Пользователь не найден в базе.")
        return

    # Делаем active = False (исключаем из списка)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE participants SET active = False WHERE chat_id = ? AND user_id = ?",
            (message.chat.id, user_id)
        )
        await db.commit()

    await message.answer(f"Пользователь с user_id {user_id} больше не будет получать напоминания о дэйлике.")



@dp.message(Command("list_active"))
async def cmd_list_active(message: Message):
        # Сначала добавим всех админов в participants
    await ensure_admins_in_db(message.chat.id)
    # Проверка: только для группы
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только для админа
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может просматривать список.")
        return

    # Получаем всех активных участников
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, username FROM participants WHERE chat_id = ? AND active = True",
            (message.chat.id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Список активных участников пуст.")
        return

    # Формируем текст ответа
    text = "Активные участники:\n"
    for user_id, username in rows:
        if username:
            text += f"— @{username} ({user_id})\n"
        else:
            text += f"— user_id: {user_id}\n"

    # В чате — отправляем только “Результат отправил вам в личку!” и удаляем через 30 мин
    if message.chat.type in ("group", "supergroup"):
        msg = await message.answer("Результат отправил вам в личку!")
        asyncio.create_task(delete_later(msg, seconds=1800))
        await bot.send_message(message.from_user.id, text)
    else:
        await message.answer(text)

@dp.message(Command("list_all"))
async def cmd_list_all(message: Message):
    # Сначала добавим всех админов в participants
    await ensure_admins_in_db(message.chat.id)

    # Проверка: только для группы
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только для админа
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может просматривать список.")
        return

    # Получаем всех участников чата (active и неактивных)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, username, active FROM participants WHERE chat_id = ?",
            (message.chat.id,)
        )
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Участников пока нет в базе.")
        return

    # Формируем текст ответа
    text = "Все участники:\n"
    for user_id, username, active in rows:
        active_status = "✅" if active else "❌"
        if username:
            text += f"{active_status} @{username} ({user_id})\n"
        else:
            text += f"{active_status} user_id: {user_id}\n"

    # В чате — только уведомление, сам отчёт шлём в ЛС
    msg = await message.answer("Отправил список участников вам в личку!")
    asyncio.create_task(delete_later(msg, seconds=1800))
    try:
        await bot.send_message(message.from_user.id, text)
    except Exception:
        await message.answer(
            "Не удалось отправить список участников в личку. Напишите боту в ЛС (например, /start), чтобы получать личные сообщения."
        )


@dp.message(Command("include"))
async def cmd_include(message: Message, command: CommandObject):
        # Сначала добавим всех админов в participants
    await ensure_admins_in_db(message.chat.id)
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может возвращать участников.")
        return

    if not command.args:
        await message.answer("Укажи username или user_id (например: /include @username или /include 123456789).")
        return

    arg = command.args.strip()
    user_id = None
    username = None

    if arg.isdigit():
        user_id = int(arg)
    else:
        username = arg.lstrip("@")

    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Пытаемся найти в базе
        if user_id:
            cursor = await db.execute(
                "SELECT user_id, username FROM participants WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, user_id)
            )
        else:
            cursor = await db.execute(
                "SELECT user_id, username FROM participants WHERE chat_id = ? AND username = ?",
                (message.chat.id, username)
            )
        row = await cursor.fetchone()

        if row:
            await db.execute(
                "UPDATE participants SET active = True WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, row[0])
            )
            await db.commit()
            await message.answer(f"Пользователь с user_id {row[0]} теперь снова в списке активных.")
        else:
            # 2. Пытаемся найти участника через get_chat_member
            try:
                member = None
                if user_id:
                    member = await bot.get_chat_member(message.chat.id, user_id)
                elif username:
                    try:
                        # get_chat_member работает и по username, если тот уникальный в чате
                        member = await bot.get_chat_member(message.chat.id, username)
                    except Exception:
                        # Если вдруг username не сработал — пробуем собрать всех, у кого username совпадает (если бот увидел в чате)
                        chat_adms = await bot.get_chat_administrators(message.chat.id)
                        for m in chat_adms:
                            if m.user.username and m.user.username.lower() == username.lower():
                                member = m
                                break

                if member:
                    user_id_to_add = member.user.id
                    username_to_add = member.user.username
                    await db.execute(
                        "INSERT OR REPLACE INTO participants (chat_id, user_id, username, active) VALUES (?, ?, ?, ?)",
                        (message.chat.id, user_id_to_add, username_to_add, True)
                    )
                    await db.commit()
                    await message.answer(f"Пользователь @{username_to_add or user_id_to_add} добавлен в список активных и теперь должен сдавать отчёты.")
                else:
                    await message.answer(
                        "Не удалось найти пользователя в чате.\n"
                        "Проверь корректность user_id или username и убедись, что пользователь писал в чат.\n"
                        "Лайфхак: пусть участник просто ответит реплаем на дэйлик, чтобы бот 100% его увидел."
                    )
            except Exception as e:
                await message.answer(f"Ошибка при добавлении: {e}")


@dp.message(Command("report"))
async def cmd_report(message: Message, command: CommandObject):
        # Сначала добавим всех админов в participants
    await ensure_admins_in_db(message.chat.id)
    import re
    from datetime import datetime

    # Проверка, что только админ может вызвать команду
    if message.chat.type == "private":
        # В ЛС: admin может получить отчёт только по чатам, где он админ
        args = (command.args or "").strip().split()
        if not args:
            await message.answer("Используй: /report <chat_id> [дата в формате YYYY-MM-DD]")
            return
        chat_id = args[0]
        # Проверяем, админ ли пользователь в этом чате
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT 1 FROM participants
                WHERE chat_id = ? AND user_id = ? AND active = True AND is_admin = True
            """, (chat_id, message.from_user.id))
            is_admin = await cursor.fetchone()
        if not is_admin:
            await message.answer("Команда /report доступна только администраторам указанного чата.")
            return
        date_str = datetime.now(timezone("Europe/Moscow")).strftime("%Y-%m-%d")
        if len(args) > 1:
            date_str = args[1]
    else:
        # В группе: admin — это тот, кто сейчас админ через Telegram API
        chat_id = str(message.chat.id)
        args = (command.args or "").strip().split()
        if args:
            date_str = args[0]
        else:
            date_str = datetime.now(timezone("Europe/Moscow")).strftime("%Y-%m-%d")

        admins = await bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]
        if message.from_user.id not in admin_ids:
            await message.answer("Команда /report доступна только администраторам этого чата.")
            return

    # Проверка даты
    if not re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        await message.answer("Дата в формате YYYY-MM-DD, например: 2024-06-12")
        return

    # Собираем все отчёты
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT participants.username, participants.user_id, daily_reports.text
            FROM daily_reports
            JOIN participants ON
                daily_reports.chat_id = participants.chat_id AND daily_reports.user_id = participants.user_id
            WHERE daily_reports.chat_id = ? AND daily_reports.date = ?
            ORDER BY participants.username, participants.user_id
        """, (chat_id, date_str))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Нет отчётов за эту дату.")
        return

    text = f"Отчёты за {date_str}:\n\n"
    for username, user_id, report in rows:
        user_ref = f"@{username}" if username else f"user_id: {user_id}"
        text += f"{user_ref}:\n{report}\n\n"

    # Если команда из ЛС — просто выводим текст. Если в чате — лучше отправить только админу
    if message.chat.type == "private":
        await message.answer(text)
    else:
        await message.answer("Отправил вам отчёты в личку.")
        await bot.send_message(message.from_user.id, text)



@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "<b>Как работать с Дейлик-Ботом?</b>\n\n"
        "Дейлик-Бот помогает собирать ежедневные отчёты в чатах, напоминать о них, и сохранять в базе для просмотра.\n\n"
        "<b>Главные команды для админа (только из чата):</b>\n"
        "• /start — добавить бота в чат и инициализировать базу\n"
        "• /settime HH:MM — установить время отправки дэйлика (по МСК)\n"
        "• /testdaily — отправить тестовый дэйлик сейчас\n"
        "• /exclude @username или /exclude user_id — исключить участника из списка напоминаний\n"
        "• /include @username или /include user_id — вернуть участника в список\n"
        "• /list_active — список всех активных участников\n"
        "• /list_all — полный список всех участников с user_id и статусом\n"
        "• /report [дата] — получить отчёты за дату (или сегодня, если дату не указали)\n\n"
        "<b>Главные команды для админа (в ЛС):</b>\n"
        "• /mychats — посмотреть список ваших чатов (название и chat_id)\n"
        "• /report chat_id [дата] — получить отчёты за дату из нужного чата в личку\n\n"
        "<b>Общие команды для участников:</b>\n"
        "• Чтобы попасть в список для отчётов — просто один раз ответьте реплаем на сообщение дэйлика.\n"
        "• Если вас исключили, можно снова попасть в список через /include или ответив на дэйлик.\n\n"
        "<b>Особенности:</b>\n"
        "• Все отчёты сохраняются в базе.\n"
        "• Напоминания приходят только активным участникам, если не сдали дэйлик в течение 2 часов.\n"
        "• Время указывается по Москве.\n"
        "• Дейлик присылается каждый день автоматически.\n"
        "• Данные о чатах и отчётах доступны только администраторам.\n\n"
        "<b>Для связи с разработчиком/поддержкой: @Fessan</b>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message()
async def handle_reply(message: Message):
    if not message.reply_to_message or message.reply_to_message.from_user.id != bot.id:
        return
        # Новый кусок: разрешаем только reply на дейлик или напоминание!
    parent_text = message.reply_to_message.text or ""
    if not (
        parent_text.startswith("Текстовый дейлик:") or
        "Жду Текстовый Дейлик" in parent_text
    ):
        return  # Игнорируем любые другие reply на сообщения бота
    # Открываем соединение один раз на всё
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM participants WHERE chat_id = ? AND user_id = ?",
            (message.chat.id, message.from_user.id)
        )
        user = await cursor.fetchone()
        if not user:
            await db.execute(
                "INSERT INTO participants (chat_id, user_id, username, active) VALUES (?, ?, ?, ?)",
                (message.chat.id, message.from_user.id, message.from_user.username or message.from_user.full_name, True)
            )
            await db.commit()
            print(f"Добавлен новый участник: {message.from_user.username or message.from_user.full_name}")
        elif user and not user[3]:  # user[3] — это поле active
            await db.execute(
                "UPDATE participants SET active = True WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, message.from_user.id)
            )
            await db.commit()
            print(f"Участник снова стал активным: {message.from_user.username or message.from_user.full_name}")

        # Сохраняем или обновляем отчет в daily_reports
        today = datetime.now().strftime("%Y-%m-%d")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        await db.execute(
            """
            INSERT INTO daily_reports
                (chat_id, user_id, date, reply_to_message_id, message_id, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id, date) DO UPDATE SET
                reply_to_message_id=excluded.reply_to_message_id,
                message_id=excluded.message_id,
                text=excluded.text,
                created_at=excluded.created_at
            """,
            (
                message.chat.id,
                message.from_user.id,
                today,
                message.reply_to_message.message_id,
                message.message_id,
                message.text,
                created_at
            )
        )
        await db.commit()
        print(f"Сохранён отчет от {message.from_user.username or message.from_user.full_name} за {today}")
    # Добавляем реакцию к сообщению пользователя (если всё успешно)
      # await message.reply("✅")

async def main():
    global loop
    await init_db()
    scheduler.start()
    await schedule_all_dailies()
    loop = asyncio.get_event_loop()
    print("Scheduler запущен, жду рассылки...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
