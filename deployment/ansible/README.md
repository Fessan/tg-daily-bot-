# Ansible Deployment для Telegram Daily Bot

## Быстрый старт

### 1. Установка зависимостей

```bash
# Установка Ansible коллекций
ansible-galaxy collection install -r requirements.yml
```

### 2. Настройка

Отредактируйте файлы:

- `inventory.ini` - адрес вашего сервера
- `group_vars/all.yml` - основные настройки
- `group_vars/vault.yml` - секреты (создайте через ansible-vault)

```bash
# Создание зашифрованного файла с секретами
ansible-vault create group_vars/vault.yml
```

Добавьте в vault.yml:

```yaml
vault_bot_token: "YOUR_BOT_TOKEN_HERE"
```

### 3. Проверка подключения

```bash
ansible all -i inventory.ini -m ping
```

### 4. Деплой

```bash
# Первый деплой
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass

# Обновление
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass
```

## Доступные playbook'и

| Playbook | Описание | Команда |
|----------|----------|---------|
| `deploy.yml` | Полный деплой бота | `ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass` |
| `start.yml` | Запуск бота | `ansible-playbook -i inventory.ini start.yml` |
| `stop.yml` | Остановка бота | `ansible-playbook -i inventory.ini stop.yml` |
| `restart.yml` | Перезапуск бота | `ansible-playbook -i inventory.ini restart.yml` |
| `logs.yml` | Просмотр логов | `ansible-playbook -i inventory.ini logs.yml` |
| `backup.yml` | Создание бэкапа | `ansible-playbook -i inventory.ini backup.yml` |

## Структура файлов

```
ansible/
├── ansible.cfg              # Конфигурация Ansible
├── inventory.ini            # Список серверов
├── requirements.yml         # Необходимые коллекции
├── deploy.yml              # Основной playbook для деплоя
├── start.yml               # Запуск бота
├── stop.yml                # Остановка бота
├── restart.yml             # Перезапуск бота
├── logs.yml                # Просмотр логов
├── backup.yml              # Создание бэкапа
├── group_vars/
│   ├── all.yml             # Общие переменные
│   ├── production.yml      # Production переменные
│   └── vault.yml           # Зашифрованные секреты (создайте сами)
└── templates/
    └── env.j2              # Шаблон .env файла
```

## Переменные

### Основные переменные (group_vars/all.yml)

```yaml
project_name: tg-daily-bot
project_path: /opt/tg-daily-bot
project_user: deploy
bot_token: "{{ vault_bot_token }}"  # Из vault
```

### Секретные переменные (group_vars/vault.yml)

Создайте файл через:

```bash
ansible-vault create group_vars/vault.yml
```

Содержимое:

```yaml
vault_bot_token: "YOUR_REAL_BOT_TOKEN"
```

### Редактирование vault файла

```bash
# Редактировать
ansible-vault edit group_vars/vault.yml

# Просмотреть
ansible-vault view group_vars/vault.yml

# Изменить пароль
ansible-vault rekey group_vars/vault.yml
```

## Примеры использования

### Деплой с verbose выводом

```bash
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass -vvv
```

### Деплой на конкретный хост

```bash
ansible-playbook -i inventory.ini deploy.yml --limit prod-server --ask-vault-pass
```

### Dry-run (проверка без изменений)

```bash
ansible-playbook -i inventory.ini deploy.yml --check --ask-vault-pass
```

### Использование файла с паролем vault

Создайте файл `.vault_pass` (добавлен в .gitignore):

```bash
echo "your_vault_password" > .vault_pass
chmod 600 .vault_pass
```

Используйте:

```bash
ansible-playbook -i inventory.ini deploy.yml --vault-password-file .vault_pass
```

## Устранение проблем

### Ошибка подключения SSH

```bash
# Проверьте подключение
ssh deploy@your-server-ip

# Проверьте с verbose
ansible all -i inventory.ini -m ping -vvv
```

### Ошибка прав доступа

```bash
# Проверьте права на ключ
chmod 600 ~/.ssh/id_rsa

# Проверьте пользователя
ansible all -i inventory.ini -m shell -a "whoami"
```

### Ошибка Docker коллекции

```bash
# Переустановите коллекцию
ansible-galaxy collection install community.docker --force
```

## Полезные команды

```bash
# Список всех хостов
ansible-inventory -i inventory.ini --list

# Проверка синтаксиса
ansible-playbook --syntax-check deploy.yml

# Список задач в playbook
ansible-playbook deploy.yml --list-tasks

# Список тегов
ansible-playbook deploy.yml --list-tags

# Выполнение ad-hoc команды
ansible all -i inventory.ini -m shell -a "docker ps"
```

## Безопасность

1. ✅ Используйте Ansible Vault для секретов
2. ✅ Не коммитьте `.vault_pass` в git
3. ✅ Используйте SSH ключи вместо паролей
4. ✅ Ограничьте SSH доступ на сервере
5. ✅ Регулярно обновляйте пароли vault

## Поддержка

См. подробную документацию в [DEPLOYMENT.md](../../DEPLOYMENT.md)

