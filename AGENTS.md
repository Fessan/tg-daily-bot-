# Repository Guidelines

## Структура проекта и модули
Точка входа — `main.py` (логирование, загрузка конфигурации, регистрация хендлеров). Логика разделена по ролям: `handlers/` (админские, отчётные, help и daily-команды), `scheduler_tasks.py` (ежедневные рассылки и напоминания), `db.py` (схема SQLite, миграции, запросы), `utils.py` (проверка рабочих дней, отложенное удаление), `config.py` (окружение и константы), `bot_instance.py` (общие объекты bot/dispatcher/scheduler). Тесты — в `tests/` с фикстурами в `conftest.py`; документация — в `docs/` (архитектура, деплой, тестирование); Ansible и сопутствующее — в `deployment/`; Docker-файлы — в корне. Генерируемые артефакты (`bot.db`, `bot.log`, `backups/`) не коммитим.

## Сборка, тесты и разработка
Зависимости в venv: `make install`. Запуск бота: `make run` (нужен `.env` с `BOT_TOKEN`); черновой `.env` — `make setup-env`. Линт/типы: `make lint`; автоформат: `make format`. Тесты: `make test` или `./run_tests.sh` (`unit|integration|e2e|fast|coverage|specific`). Покрытие: `pytest --cov --cov-report=html`. Docker: `make docker-build`, затем `make docker-run`/`make docker-stop` (`make docker-logs` — логи). Ansible: `make ansible-*`, `make deploy*` в `deployment/ansible`.

## Стиль кода и именование
Python 3.11+, отступы 4 пробела; `snake_case` для модулей/функций/переменных, `PascalCase` для классов, `UPPER_SNAKE_CASE` для констант. Форматируем `black` + `isort`, группируем импорты (stdlib, сторонние, локальные). Линт — `flake8`; типы проверяем `mypy`, новые функции аннотируем. Хендлеры держим тонкими, общую логику выносим в scheduler/db/utils.

## Руководство по тестам
Pytest настроен в `pytest.ini` (`test_*.py`, классы `Test*`, маркеры `unit`, `integration`, `e2e`, `slow`; verbose и strict markers). Быстрый прогон: `pytest -m "not slow"` или `./run_tests.sh fast`. Цель покрытия ≥70% (предпочтительно 80%); HTML — `pytest --cov --cov-report=html` (`htmlcov/index.html`). Для изменений в scheduler или БД добавляйте интеграционные тесты по асинхронным потокам и записи в SQLite; фикстуры делайте лёгкими, чтобы избежать утечек состояния.

## Коммиты и Pull Request
Стиль логов: краткие императивные заголовки на английском (например, `Add scheduler retry guard`), тело по необходимости. Один коммит — одна задача; при необходимости фиксируйте запущенные тесты. В PR описывайте изменения, тесты, возможные миграции конфигов/данных; при наличии привязывайте issue. Для пользовательских или операционных изменений прикладывайте скриншоты/логи и обновляйте документацию (`docs/`, README, DEPLOYMENT) при смене поведения или команд.

## Безопасность и конфигурация
Секреты не коммитим: собирайте `.env` из `env.example`, задайте `BOT_TOKEN`; исключайте `bot.db`. При утечке токена — ротация. Для бэкапов SQLite используйте `make backup-local`/`make restore-local` в процессе разработки. В Docker/Ansible защищайте тома БД/логов и выдавайте боту права админа только в нужных чатах.
