# Быстрый старт для деплоя

## 🚀 За 5 минут на боевой сервер

### 1. Подготовка (на вашем компьютере)

```bash
# Установите Ansible
sudo apt install ansible  # Ubuntu/Debian
# или
brew install ansible       # macOS

# Перейдите в директорию проекта
cd tg-daily-bot

# Установите Ansible зависимости
cd deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

### 2. Настройка сервера

Отредактируйте `deployment/ansible/inventory.ini`:

```ini
[production]
prod-server ansible_host=YOUR_SERVER_IP ansible_user=deploy
```

Замените `YOUR_SERVER_IP` на IP вашего сервера.

### 3. Настройка токена бота

Создайте зашифрованный файл с токеном:

```bash
ansible-vault create group_vars/vault.yml
```

Введите пароль и добавьте:

```yaml
vault_bot_token: "YOUR_BOT_TOKEN_FROM_BOTFATHER"
```

### 4. Проверка подключения

```bash
ansible all -i inventory.ini -m ping
```

Должны увидеть `SUCCESS`.

### 5. Деплой! 🎉

```bash
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass
```

Введите пароль vault и ждите завершения.

### 6. Проверка

```bash
# Просмотр логов
ansible-playbook -i inventory.ini logs.yml

# Или на сервере напрямую
ssh deploy@YOUR_SERVER_IP
docker logs tg-daily-bot
```

## Управление ботом

```bash
# Перезапуск
ansible-playbook -i inventory.ini restart.yml

# Остановка
ansible-playbook -i inventory.ini stop.yml

# Запуск
ansible-playbook -i inventory.ini start.yml

# Бэкап
ansible-playbook -i inventory.ini backup.yml
```

## Использование Makefile (еще проще!)

```bash
# Проверка подключения
make ansible-ping

# Деплой
make deploy

# Перезапуск
make deploy-restart

# Логи
make deploy-logs

# Бэкап
make deploy-backup
```

## Что еще?

Полная документация: [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Важно**: Убедитесь, что на сервере:
- ✅ Есть пользователь `deploy` с правами sudo
- ✅ Настроен SSH доступ по ключу
- ✅ Открыт порт 22 для SSH

Если нужна помощь с настройкой сервера - см. раздел "Подготовка удаленного сервера" в [DEPLOYMENT.md](DEPLOYMENT.md)

