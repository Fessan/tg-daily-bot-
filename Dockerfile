# Базовый образ
FROM python:3.12-slim

# Установка переменных окружения для Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создание непривилегированного пользователя для безопасности
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Создание рабочей директории и директорий для данных
WORKDIR /app
RUN mkdir -p /app/data /app/logs && \
    chown -R botuser:botuser /app

# Копирование файла зависимостей
COPY requirements.txt .

# Установка зависимостей глобально (доступны для всех пользователей)
RUN pip install --no-warn-script-location -r requirements.txt

# Копирование кода приложения
COPY --chown=botuser:botuser . .

# Переключение на непривилегированного пользователя
USER botuser

# Volumes для постоянного хранения данных
VOLUME ["/app/data", "/app/logs"]

# Health check для мониторинга
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/data/bot.db') else 1)"

# Запуск приложения
CMD ["python", "-u", "main.py"]

