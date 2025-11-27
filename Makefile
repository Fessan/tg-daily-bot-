# Makefile для Telegram Daily Bot
# Удобные команды для локальной разработки и деплоя

.PHONY: help install run test clean docker-build docker-run docker-stop deploy deploy-check

# Цвета для вывода
GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m # No Color

help: ## Показать эту справку
	@echo "$(GREEN)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================================
# ЛОКАЛЬНАЯ РАЗРАБОТКА
# ============================================================

install: ## Установить зависимости в виртуальное окружение
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r requirements-dev.txt
	@echo "$(GREEN)✓ Зависимости установлены$(NC)"

run: ## Запустить бота локально
	./venv/bin/python main.py

test: ## Запустить тесты
	./venv/bin/pytest tests/ -v

lint: ## Проверить код линтерами
	./venv/bin/flake8 .
	./venv/bin/mypy .

format: ## Форматировать код
	./venv/bin/black .
	./venv/bin/isort .

clean: ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	@echo "$(GREEN)✓ Очистка завершена$(NC)"

# ============================================================
# DOCKER
# ============================================================

docker-build: ## Собрать Docker образ
	docker build -t tg-daily-bot:latest .
	@echo "$(GREEN)✓ Docker образ собран$(NC)"

docker-run: ## Запустить контейнер
	docker compose up -d
	@echo "$(GREEN)✓ Контейнер запущен$(NC)"
	@echo "Просмотр логов: docker logs -f tg-daily-bot"

docker-stop: ## Остановить контейнер
	docker compose down
	@echo "$(GREEN)✓ Контейнер остановлен$(NC)"

docker-logs: ## Показать логи контейнера
	docker logs -f tg-daily-bot

docker-restart: ## Перезапустить контейнер
	docker compose restart
	@echo "$(GREEN)✓ Контейнер перезапущен$(NC)"

docker-shell: ## Открыть shell в контейнере
	docker exec -it tg-daily-bot bash

docker-clean: ## Очистить Docker образы и контейнеры
	docker compose down -v
	docker system prune -f
	@echo "$(GREEN)✓ Docker очищен$(NC)"

# ============================================================
# ANSIBLE ДЕПЛОЙ
# ============================================================

ansible-setup: ## Установить Ansible зависимости
	cd deployment/ansible && ansible-galaxy collection install -r requirements.yml
	@echo "$(GREEN)✓ Ansible зависимости установлены$(NC)"

ansible-ping: ## Проверить подключение к серверу
	cd deployment/ansible && ansible all -i inventory.ini -m ping

deploy-check: ## Проверить деплой без изменений (dry-run)
	cd deployment/ansible && ansible-playbook -i inventory.ini deploy.yml --check --ask-vault-pass

deploy: ## Задеплоить бота на сервер
	cd deployment/ansible && ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass
	@echo "$(GREEN)✓ Деплой завершен$(NC)"

deploy-start: ## Запустить бота на сервере
	cd deployment/ansible && ansible-playbook -i inventory.ini start.yml

deploy-stop: ## Остановить бота на сервере
	cd deployment/ansible && ansible-playbook -i inventory.ini stop.yml

deploy-restart: ## Перезапустить бота на сервере
	cd deployment/ansible && ansible-playbook -i inventory.ini restart.yml

deploy-logs: ## Показать логи с сервера
	cd deployment/ansible && ansible-playbook -i inventory.ini logs.yml

deploy-backup: ## Создать бэкап на сервере
	cd deployment/ansible && ansible-playbook -i inventory.ini backup.yml
	@echo "$(GREEN)✓ Бэкап создан$(NC)"

# ============================================================
# РАЗНОЕ
# ============================================================

setup-env: ## Создать .env файл из примера
	@if [ ! -f .env ]; then \
		echo "BOT_TOKEN=YOUR_TOKEN_HERE" > .env; \
		echo "$(YELLOW)! Создан .env файл. Не забудьте добавить ваш BOT_TOKEN$(NC)"; \
	else \
		echo "$(YELLOW)! Файл .env уже существует$(NC)"; \
	fi

backup-local: ## Создать локальный бэкап базы данных
	@mkdir -p backups
	@if [ -f bot.db ]; then \
		cp bot.db backups/bot.db.$$(date +%Y%m%d_%H%M%S); \
		echo "$(GREEN)✓ Бэкап создан в backups/$(NC)"; \
	else \
		echo "$(YELLOW)! База данных bot.db не найдена$(NC)"; \
	fi

restore-local: ## Восстановить последний локальный бэкап
	@if [ -f $$(ls -t backups/bot.db.* 2>/dev/null | head -1) ]; then \
		cp $$(ls -t backups/bot.db.* | head -1) bot.db; \
		echo "$(GREEN)✓ База данных восстановлена$(NC)"; \
	else \
		echo "$(YELLOW)! Бэкапы не найдены$(NC)"; \
	fi

# ============================================================
# ИНФОРМАЦИЯ
# ============================================================

info: ## Показать информацию о проекте
	@echo "$(GREEN)Telegram Daily Bot$(NC)"
	@echo ""
	@echo "Python версия: $$(python3 --version 2>/dev/null || echo 'не установлен')"
	@echo "Docker версия: $$(docker --version 2>/dev/null || echo 'не установлен')"
	@echo "Ansible версия: $$(ansible --version 2>/dev/null | head -1 || echo 'не установлен')"
	@echo ""
	@if [ -f .env ]; then \
		echo "$(GREEN)✓$(NC) .env файл существует"; \
	else \
		echo "$(YELLOW)✗$(NC) .env файл не найден (используйте: make setup-env)"; \
	fi
	@if [ -d venv ]; then \
		echo "$(GREEN)✓$(NC) Виртуальное окружение создано"; \
	else \
		echo "$(YELLOW)✗$(NC) Виртуальное окружение не найдено (используйте: make install)"; \
	fi
	@if [ -f bot.db ]; then \
		echo "$(GREEN)✓$(NC) База данных существует"; \
	else \
		echo "$(YELLOW)✗$(NC) База данных не найдена"; \
	fi
	@echo ""
	@echo "$(GREEN)Документация:$(NC)"
	@echo "  docs/                           - Вся документация"
	@echo "  docs/deployment/               - Руководства по деплою"
	@echo "  docs/testing/                  - Руководства по тестированию"

