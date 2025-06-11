import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import aiosqlite
from datetime import datetime
from aiogram.filters import CommandObject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import timedelta






scheduler = AsyncIOScheduler()
DB_PATH = "bot.db"  # Имя файла базы данных

async def migrate_participants_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("ALTER TABLE participants ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;")
        await db.commit()
    print("Миграция завершена: поле is_admin добавлено.")


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

    await message.answer(text)


@dp.message(Command("list_all"))
async def cmd_list_all(message: Message):
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

    await message.answer(text)



@dp.message(Command("include"))
async def cmd_include(message: Message, command: CommandObject):
    # Проверка: только в группе
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда только для групп.")
        return

    # Проверка: только админ может использовать
    admins = await bot.get_chat_administrators(message.chat.id)
    admin_ids = [admin.user.id for admin in admins]
    if message.from_user.id not in admin_ids:
        await message.answer("Только админ может возвращать участников.")
        return

    # Получаем аргумент команды
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

    # Проверяем, есть ли пользователь в базе
    async with aiosqlite.connect(DB_PATH) as db:
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
            # Если есть — просто делаем active = True
            await db.execute(
                "UPDATE participants SET active = True WHERE chat_id = ? AND user_id = ?",
                (message.chat.id, row[0])
            )
            await db.commit()
            await message.answer(f"Пользователь с user_id {row[0]} теперь снова в списке активных.")
        else:
            # Если нет — пытаемся добавить (запросим через Telegram API)
            # Нужно получить объект пользователя по username или user_id
            tg_user = None
            try:
                if user_id:
                    tg_user = await bot.get_chat_member(message.chat.id, user_id)
                elif username:
                    # Получаем список участников чата (только для малых групп, иначе только через админа вручную)
                    members = await bot.get_chat_administrators(message.chat.id)
                    for m in members:
                        if m.user.username and m.user.username.lower() == username.lower():
                            tg_user = m
                            user_id = m.user.id
                            break
                if tg_user:
                    await db.execute(
                        "INSERT INTO participants (chat_id, user_id, username, active) VALUES (?, ?, ?, ?)",
                        (
                            message.chat.id,
                            user_id,
                            username if username else (tg_user.user.username if hasattr(tg_user, 'user') else tg_user.username),
                            True
                        )
                    )
                    await db.commit()
                    await message.answer(f"Пользователь {user_id} добавлен в список активных и теперь должен сдавать отчёты.")
                else:
                    await message.answer("Не удалось найти пользователя в чате. Проверьте корректность user_id или username.")
            except Exception as e:
                await message.answer(f"Ошибка при добавлении: {e}")


@dp.message()
async def handle_reply(message: Message):
    if not message.reply_to_message or message.reply_to_message.from_user.id != bot.id:
        return

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



async def main():
    await init_db()
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
