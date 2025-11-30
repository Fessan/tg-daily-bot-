# Чек-лист готовности к деплою

**Дата проверки:** 26 ноября 2025
**Метод деплоя:** Docker + Ansible

---

## ✅ Что готово

### Docker инфраструктура
- ✅ `Dockerfile` - создан и оптимизирован (Python 3.12-slim, непривилегированный пользователь)
- ✅ `docker-compose.yml` - настроен с volumes, logging, security
- ✅ `.dockerignore` - настроен для оптимизации образа
- ✅ `.env` файл - существует локально (содержит BOT_TOKEN)
- ✅ `env.example` - создан как шаблон
- ✅ `requirements.txt` - все зависимости указаны

### Ansible инфраструктура
- ✅ `deployment/ansible/deploy.yml` - playbook для полного деплоя
- ✅ `deployment/ansible/start.yml` - запуск бота
- ✅ `deployment/ansible/stop.yml` - остановка бота
- ✅ `deployment/ansible/restart.yml` - перезапуск бота
- ✅ `deployment/ansible/backup.yml` - создание бэкапов
- ✅ `deployment/ansible/logs.yml` - просмотр логов
- ✅ `deployment/ansible/requirements.yml` - коллекции для Ansible
- ✅ `deployment/ansible/templates/env.j2` - шаблон .env для сервера
- ✅ `deployment/ansible/group_vars/all.yml` - общие переменные
- ✅ `deployment/ansible/group_vars/production.yml` - production переменные

### Документация
- ✅ `DEPLOYMENT.md` - подробное руководство по деплою (560+ строк)
- ✅ `Makefile` - команды для удобного управления (174 строки)
- ✅ `README.md` - обновлен

### Локальное окружение
- ✅ Docker установлен - `/usr/bin/docker`
- ✅ .env файл существует

---

## ❌ Что нужно сделать ПЕРЕД деплоем

### 🔴 КРИТИЧНО (без этого деплой НЕ РАБОТАЕТ)

#### 1. Установить Ansible на локальной машине
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ansible python3-pip

# Проверка
ansible --version
```

#### 2. Установить Ansible коллекции
```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

Требуемые коллекции:
- `community.docker` (>=3.4.0)
- `ansible.posix` (>=1.5.0)

#### 3. Настроить inventory.ini - указать реальный IP сервера
Файл: `deployment/ansible/inventory.ini`

**СЕЙЧАС:**
```ini
prod-server ansible_host=your-server-ip ansible_user=deploy ansible_port=22
```

**НУЖНО ЗАМЕНИТЬ:**
```ini
prod-server ansible_host=123.45.67.89 ansible_user=deploy ansible_port=22
```

Замените `123.45.67.89` на реальный IP вашего сервера.

#### 4. Настроить BOT_TOKEN с использованием Ansible Vault

**Вариант А (РЕКОМЕНДУЕТСЯ): Использовать Ansible Vault**

```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible

# Создать зашифрованный файл
ansible-vault create group_vars/vault.yml

# В открывшемся редакторе введите:
vault_bot_token: "ВАШ_РЕАЛЬНЫЙ_ТОКЕН_БОТА"

# Сохраните и выйдите (Ctrl+X, Y, Enter если nano)
```

Файл `group_vars/all.yml` уже настроен на использование vault:
```yaml
bot_token: "{{ vault_bot_token | default('REPLACE_WITH_YOUR_TOKEN') }}"
```

**Вариант Б (НЕ РЕКОМЕНДУЕТСЯ): Прямое указание токена**

Отредактировать `deployment/ansible/group_vars/all.yml`:
```yaml
bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"
```

⚠️ **ВНИМАНИЕ:** Не коммитьте файл с реальным токеном в Git!

#### 5. Настроить SSH доступ к серверу

Если еще не настроено:

```bash
# Генерация SSH ключа (если нет)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Копирование ключа на сервер
ssh-copy-id deploy@ВАШ_IP_СЕРВЕРА

# Проверка подключения
ssh deploy@ВАШ_IP_СЕРВЕРА
```

Если пользователя `deploy` нет на сервере, создайте его:
```bash
# На сервере
sudo adduser deploy
sudo usermod -aG sudo deploy
```

### 🟡 ВАЖНО (настоятельно рекомендуется)

#### 6. Проверить подключение Ansible к серверу

```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible all -i inventory.ini -m ping
```

Ожидаемый результат:
```
prod-server | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

#### 7. Проверить настройки Git в group_vars/all.yml

Файл: `deployment/ansible/group_vars/all.yml`

```yaml
git_repo: https://github.com/yourusername/tg-daily-bot.git
git_branch: main
```

Если вы **НЕ используете Git**, оставьте пустым или удалите эти строки - playbook будет копировать файлы напрямую через rsync.

Если используете Git, замените на реальный URL репозитория.

---

## 📋 Порядок действий для деплоя

После выполнения всех пунктов выше:

### 1. Установить Ansible (если не установлен)
```bash
sudo apt install ansible python3-pip
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

### 2. Настроить параметры
- ✏️ Отредактировать `inventory.ini` (указать IP сервера)
- ✏️ Создать `group_vars/vault.yml` с токеном бота (или указать в all.yml)
- ✏️ Проверить другие переменные в `group_vars/all.yml`

### 3. Проверить подключение
```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible all -i inventory.ini -m ping
```

### 4. Выполнить тестовый деплой (dry-run)
```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible-playbook -i inventory.ini deploy.yml --check --ask-vault-pass

# Или через Makefile из корня проекта
cd /home/fessan/project/tg-daily-bot-
make deploy-check
```

### 5. Выполнить реальный деплой
```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass

# Или через Makefile из корня проекта
cd /home/fessan/project/tg-daily-bot-
make deploy
```

Playbook автоматически:
1. ✅ Обновит систему на сервере
2. ✅ Установит Docker и Docker Compose (если не установлены)
3. ✅ Создаст пользователя и директории
4. ✅ Скопирует код проекта на сервер
5. ✅ Создаст .env файл с вашим токеном
6. ✅ Создаст бэкап существующей БД (если есть)
7. ✅ Соберет Docker образ
8. ✅ Запустит контейнер
9. ✅ Проверит, что контейнер работает

---

## 🛠️ Полезные команды после деплоя

### Через Makefile (из корня проекта)
```bash
make deploy          # Полный деплой
make deploy-start    # Запустить бота
make deploy-stop     # Остановить бота
make deploy-restart  # Перезапустить бота
make deploy-logs     # Показать логи
make deploy-backup   # Создать бэкап БД
make ansible-ping    # Проверить подключение
```

### Напрямую через Ansible
```bash
cd deployment/ansible

# Деплой
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass

# Запуск/остановка/перезапуск
ansible-playbook -i inventory.ini start.yml
ansible-playbook -i inventory.ini stop.yml
ansible-playbook -i inventory.ini restart.yml

# Логи
ansible-playbook -i inventory.ini logs.yml

# Бэкап
ansible-playbook -i inventory.ini backup.yml
```

### На самом сервере
```bash
# Подключиться к серверу
ssh deploy@ВАШ_IP

# Перейти в директорию проекта
cd /opt/tg-daily-bot

# Docker команды
docker logs -f tg-daily-bot          # Следить за логами
docker ps | grep tg-daily-bot        # Проверить статус
docker stats tg-daily-bot            # Использование ресурсов
docker restart tg-daily-bot          # Перезапустить

# Docker Compose команды
docker compose up -d                 # Запустить
docker compose down                  # Остановить
docker compose logs -f               # Логи
docker compose ps                    # Статус

# Проверить логи приложения
tail -f /opt/tg-daily-bot/logs/bot.log
```

---

## ⚙️ Информация о конфигурации

### Пути на сервере
- **Проект:** `/opt/tg-daily-bot`
- **База данных:** `/opt/tg-daily-bot/data/bot.db`
- **Логи:** `/opt/tg-daily-bot/logs/bot.log`
- **Бэкапы:** `/opt/tg-daily-bot/backups/`

### Docker
- **Контейнер:** `tg-daily-bot`
- **Образ:** `tg-daily-bot:latest`
- **Сеть:** `tg-daily-bot-network`
- **Политика рестарта:** `unless-stopped`

### Безопасность
- ✅ Контейнер работает от непривилегированного пользователя `botuser`
- ✅ Volumes для данных и логов
- ✅ Healthcheck каждые 60 секунд
- ✅ Security opt: `no-new-privileges:true`
- ✅ Ротация логов Docker (max 10MB, 3 файла)

### Бэкапы
- Автоматически создаются при каждом деплое
- Хранятся 30 дней
- Старые бэкапы удаляются автоматически

---

## 📊 Текущий статус проекта

### Git статус
```
Changes not staged for commit:
  modified:   .gitignore
  modified:   CHANGELOG.md
  modified:   README.md
  modified:   bot_instance.py
  modified:   config.py
  modified:   handlers/__init__.py
  modified:   handlers/daily.py
  modified:   handlers/reports.py
  modified:   run_tests.sh
  modified:   setup.py
  modified:   tests/conftest.py
  modified:   tests/test_config.py
  modified:   tests/test_db.py
  modified:   tests/test_utils.py
  modified:   utils.py

Untracked files:
  .dockerignore
  DEPLOYMENT.md
  Dockerfile
  Makefile
  deployment/
  docker-compose.yml
  docs/
  env.example
  scripts/
```

⚠️ **Рекомендация:** Прежде чем деплоить, решите:
1. Закоммитить изменения (если нужна версионность)
2. Или оставить как есть (Ansible скопирует текущее состояние)

---

## 🆘 Решение проблем

### Ansible не находит команды
```bash
# Установить Ansible
sudo apt update && sudo apt install ansible python3-pip

# Проверить
ansible --version
```

### Ошибка: "community.docker collection not found"
```bash
cd deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

### SSH подключение не работает
```bash
# Проверить подключение
ssh deploy@ВАШ_IP

# Если не работает, скопировать ключ
ssh-copy-id deploy@ВАШ_IP
```

### Ошибка vault password
Если используете Ansible Vault, всегда добавляйте `--ask-vault-pass`:
```bash
ansible-playbook -i inventory.ini deploy.yml --ask-vault-pass
```

### Docker не установлен на сервере
Не проблема! Playbook `deploy.yml` автоматически установит Docker.

---

## 📝 Итоговый чек-лист перед деплоем

- [ ] Ansible установлен локально
- [ ] Ansible коллекции установлены (`community.docker`, `ansible.posix`)
- [ ] `inventory.ini` - указан реальный IP сервера
- [ ] `group_vars/vault.yml` создан с реальным BOT_TOKEN (или токен указан в all.yml)
- [ ] SSH доступ к серверу настроен (проверено через `ssh deploy@IP`)
- [ ] Ansible ping успешен (`ansible all -i inventory.ini -m ping`)
- [ ] (Опционально) Git repo настроен в `group_vars/all.yml` (если используется)
- [ ] .env файл существует локально (для тестирования)
- [ ] Код проекта готов к деплою

После выполнения всех пунктов:
```bash
cd /home/fessan/project/tg-daily-bot-
make deploy
```

---

**Готовность:** 85%

**Осталось сделать:** 4 критичных пункта (Ansible, коллекции, inventory.ini, vault с токеном)

**Время на подготовку:** ~15-20 минут

**Время деплоя:** ~3-5 минут (первый раз), ~1-2 минуты (последующие)

---

**Автор чек-листа:** AI DevOps Expert
**Дата:** 26 ноября 2025









