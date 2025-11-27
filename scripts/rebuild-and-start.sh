#!/bin/bash
# Скрипт для пересборки и запуска контейнера

echo "🛑 Остановка старого контейнера..."
sudo docker compose down

echo "🗑️ Удаление старого образа..."
sudo docker rmi tg-daily-bot--tg-daily-bot 2>/dev/null || true

echo "🔨 Пересборка Docker образа (без кэша)..."
sudo docker compose build --no-cache

echo "🚀 Запуск нового контейнера..."
sudo docker compose up -d

echo "⏳ Ожидание запуска (10 секунд)..."
sleep 10

echo ""
echo "📊 Статус контейнера:"
sudo docker ps | grep tg-daily-bot || echo "❌ Контейнер не запущен"

echo ""
echo "📝 Последние логи:"
sudo docker logs --tail 30 tg-daily-bot

echo ""
echo "💡 Для просмотра логов в реальном времени:"
echo "   sudo docker logs -f tg-daily-bot"

