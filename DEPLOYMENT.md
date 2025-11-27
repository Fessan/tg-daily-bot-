# Руководство по развертыванию Telegram Daily Bot

## Содержание

1. [Общая информация](#общая-информация)
2. [Требования](#требования)
3. [Подготовка локальной машины](#подготовка-локальной-машины)
4. [Подготовка удаленного сервера](#подготовка-удаленного-сервера)
5. [Настройка Ansible](#настройка-ansible)
6. [Деплой приложения](#деплой-приложения)
7. [Управление ботом](#управление-ботом)
8. [Мониторинг и логи](#мониторинг-и-логи)
9. [Бэкапы](#бэкапы)
10. [Решение проблем](#решение-проблем)

---

## Общая информация

Проект настроен для деплоя в Docker контейнере с использованием Ansible для автоматизации. Это позволяет:

- ✅ Изолировать бота от других проектов на сервере
- ✅ Легко управлять версиями и откатываться
- ✅ Автоматизировать процесс развертывания
- ✅ Сохранять данные между обновлениями
- ✅ Быстро разворачивать на новых серверах

## Требования

### Локальная машина (откуда деплоим)

- Python 3.8+
- Ansible 2.10+
- SSH доступ к удаленному серверу
- Git (опционально, если используете репозиторий)

### Удаленный сервер

- Ubuntu 20.04+ / Debian 11+ (или другой Linux с поддержкой Docker)
- Минимум 1GB RAM
- Минимум 10GB свободного места
- SSH доступ с правами sudo
- Открытый порт 22 для SSH

## Подготовка локальной машины

### 1. Установка Ansible

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ansible python3-pip
```

**macOS:**
```bash
brew install ansible
```

**Проверка установки:**
```bash
ansible --version
```

### 2. Установка необходимых коллекций Ansible

```bash
cd deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

### 3. Настройка SSH ключей

Если у вас еще нет SSH ключа:

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

Скопируйте публичный ключ на сервер:

```bash
ssh-copy-id deploy@your-server-ip
```

Проверьте подключение:

```bash
ssh deploy@your-server-ip
```

## Подготовка удаленного сервера

### 1. Создание пользователя для деплоя

Подключитесь к серверу и выполните:

```bash
# Создание пользователя
sudo adduser deploy
sudo usermod -aG sudo deploy

# Настройка SSH для нового пользователя
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

### 2. Настройка sudo без пароля (опционально)

```bash
echo "deploy ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/deploy
```

### 3. Настройка firewall (опционально, но рекомендуется)

```bash
sudo apt install ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Настройка Ansible

### 1. Настройка inventory

Отредактируйте `deployment/ansible/inventory.ini`:

```ini
[production]
prod-server ansible_host=YOUR_SERVER_IP ansible_user=deploy ansible_port=22

[all:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_private_key_file=~/.ssh/id_rsa

project_path=/opt/tg-daily-bot
project_name=tg-daily-bot
```

Замените:
- `YOUR_SERVER_IP` на IP адрес вашего сервера
- `deploy` на имя вашего пользователя (если отличается)

### 2. Настройка переменных

Отредактируйте `deployment/ansible/group_vars/all.yml`:

```yaml
# Telegram Bot токен
bot_token: "YOUR_BOT_TOKEN_HERE"

# Или используйте Ansible Vault для безопасности
```

### 3. Использование Ansible Vault для хранения секретов (рекомендуется)

Создайте зашифрованный файл для токена:

```bash
cd deployment/ansible
ansible-vault create group_vars/vault.yml
```

Введите пароль и добавьте в файл:

```yaml
vault_bot_token: "YOUR_BOT_TOKEN_HERE"
```

Сохраните и закройте редактор.

Теперь в `group_vars/all.yml` токен будет браться из vault:

```yaml
bot_token: "{{ vault_bot_token }}"
```

### 4. Проверка подключения

```bash
cd deployment/ansible
ansible all -i inventory.ini -m ping
```

Ожидаемый результат:
```
prod-server | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

## Деплой приложения

### 1. Первый деплой

Перейдите в директорию Ansible:

```bash
cd deployment/ansible
```

Запустите playbook:

```bash
# Без Ansible Vault
ansible-playbook -i inventory.ini deploy.yml

# С Ansible Vault (если используете)
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass
```

Playbook выполнит следующие шаги:

1. ✅ Обновит систему
2. ✅ Установит Docker и Docker Compose
3. ✅ Создаст пользователя и директории
4. ✅ Скопирует код проекта
5. ✅ Создаст .env файл с настройками
6. ✅ Создаст бэкап существующей БД (если есть)
7. ✅ Соберет Docker образ
8. ✅ Запустит контейнер
9. ✅ Проверит состояние

### 2. Последующие обновления

Для обновления бота после изменений в коде:

```bash
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass
```

Ansible автоматически:
- Создаст бэкап базы данных
- Остановит старый контейнер
- Обновит код
- Пересоберет образ
- Запустит новый контейнер

## Управление ботом

### Остановка бота

```bash
ansible-playbook -i inventory.ini stop.yml
```

### Запуск бота

```bash
ansible-playbook -i inventory.ini start.yml
```

### Перезапуск бота

```bash
ansible-playbook -i inventory.ini restart.yml
```

### Просмотр логов

```bash
# Через Ansible (последние 50 строк)
ansible-playbook -i inventory.ini logs.yml

# Напрямую на сервере
ssh deploy@your-server-ip
docker logs tg-daily-bot

# Следить за логами в реальном времени
docker logs -f tg-daily-bot
```

## Мониторинг и логи

### 1. Проверка статуса контейнера

```bash
ssh deploy@your-server-ip
docker ps | grep tg-daily-bot
```

### 2. Просмотр логов приложения

Логи хранятся в `/opt/tg-daily-bot/logs/bot.log`:

```bash
ssh deploy@your-server-ip
tail -f /opt/tg-daily-bot/logs/bot.log
```

### 3. Проверка использования ресурсов

```bash
ssh deploy@your-server-ip
docker stats tg-daily-bot
```

### 4. Healthcheck

Контейнер имеет встроенный healthcheck, проверяющий существование базы данных:

```bash
docker inspect --format='{{.State.Health.Status}}' tg-daily-bot
```

## Бэкапы

### Автоматические бэкапы

При каждом деплое автоматически создается бэкап базы данных в `/opt/tg-daily-bot/backups/`.

Старые бэкапы (старше 30 дней) удаляются автоматически.

### Ручное создание бэкапа

```bash
ansible-playbook -i inventory.ini backup.yml
```

### Восстановление из бэкапа

```bash
# Подключитесь к серверу
ssh deploy@your-server-ip

# Остановите контейнер
cd /opt/tg-daily-bot
docker-compose down

# Восстановите базу данных
cp backups/bot.db.YYYYMMDDTHHMMSS data/bot.db

# Запустите контейнер
docker-compose up -d
```

### Скачивание бэкапа на локальную машину

```bash
scp deploy@your-server-ip:/opt/tg-daily-bot/backups/bot.db.* ./
```

## Решение проблем

### Контейнер не запускается

1. Проверьте логи:
   ```bash
   docker logs tg-daily-bot
   ```

2. Проверьте .env файл:
   ```bash
   cat /opt/tg-daily-bot/.env
   ```

3. Проверьте права на файлы:
   ```bash
   ls -la /opt/tg-daily-bot/data
   ls -la /opt/tg-daily-bot/logs
   ```

### Бот не отвечает в Telegram

1. Проверьте, что контейнер запущен:
   ```bash
   docker ps | grep tg-daily-bot
   ```

2. Проверьте логи на ошибки:
   ```bash
   docker logs tg-daily-bot | grep ERROR
   ```

3. Проверьте токен бота:
   ```bash
   docker exec tg-daily-bot env | grep BOT_TOKEN
   ```

### База данных заблокирована

SQLite может блокироваться при одновременном доступе. Решение:

```bash
# Остановите контейнер
docker-compose down

# Подождите 5 секунд

# Запустите снова
docker-compose up -d
```

### Недостаточно места на диске

Очистите старые Docker образы:

```bash
docker system prune -a --volumes
```

Очистите старые бэкапы:

```bash
find /opt/tg-daily-bot/backups -name "bot.db.*" -mtime +30 -delete
```

### Ansible не может подключиться

1. Проверьте SSH подключение:
   ```bash
   ssh deploy@your-server-ip
   ```

2. Проверьте inventory файл:
   ```bash
   ansible-inventory -i inventory.ini --list
   ```

3. Проверьте с verbose выводом:
   ```bash
   ansible-playbook -i inventory.ini deploy.yml -vvv
   ```

## Полезные команды

### Docker

```bash
# Просмотр всех контейнеров
docker ps -a

# Просмотр логов
docker logs tg-daily-bot

# Следить за логами
docker logs -f tg-daily-bot

# Выполнить команду в контейнере
docker exec -it tg-daily-bot bash

# Перезапустить контейнер
docker restart tg-daily-bot

# Просмотр использования ресурсов
docker stats tg-daily-bot

# Очистка
docker system prune -a
```

### Docker Compose

```bash
cd /opt/tg-daily-bot

# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Пересборка образа
docker-compose build --no-cache

# Просмотр статуса
docker-compose ps
```

### Ansible

```bash
# Проверка синтаксиса playbook
ansible-playbook --syntax-check deploy.yml

# Dry-run (проверка без изменений)
ansible-playbook -i inventory.ini deploy.yml --check

# Verbose вывод
ansible-playbook -i inventory.ini deploy.yml -vvv

# Запуск конкретной задачи
ansible-playbook -i inventory.ini deploy.yml --tags "backup"
```

## Дополнительные рекомендации

### Безопасность

1. **Используйте Ansible Vault** для хранения секретов
2. **Настройте firewall** на сервере
3. **Регулярно обновляйте** систему и Docker
4. **Ограничьте SSH доступ** (только по ключам, отключите root login)
5. **Настройте fail2ban** для защиты от брутфорса

### Производительность

1. Ограничьте ресурсы контейнера в `docker-compose.yml`
2. Настройте ротацию логов Docker
3. Регулярно очищайте старые Docker образы
4. Мониторьте использование диска

### Мониторинг

Рекомендуется настроить мониторинг:

1. **Uptime мониторинг** (например, UptimeRobot)
2. **Логирование** (например, в Grafana Loki)
3. **Алерты** при падении бота
4. **Мониторинг ресурсов** сервера

### CI/CD

Для автоматического деплоя при push в репозиторий, настройте GitHub Actions или GitLab CI:

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install Ansible
        run: sudo apt install ansible
      
      - name: Deploy
        run: |
          cd deployment/ansible
          ansible-playbook -i inventory.ini deploy.yml
        env:
          ANSIBLE_VAULT_PASSWORD: ${{ secrets.VAULT_PASSWORD }}
```

## Поддержка

При возникновении проблем:

1. Проверьте логи (контейнера и приложения)
2. Изучите [README.md](README.md) проекта
3. Проверьте открытые issues в репозитории
4. Обратитесь к разработчику: [@Fessan](https://t.me/Fessan)

---

**Автор**: @Fessan  
**Версия документа**: 1.0  
**Дата**: 2025-11-26

