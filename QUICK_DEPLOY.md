# Быстрый деплой - 4 шага

## Перед началом

У вас должны быть:
- IP адрес сервера
- SSH доступ к серверу (пользователь `deploy` или другой с sudo)
- Токен Telegram бота от @BotFather

---

## Шаг 1: Установить Ansible (5 минут)

```bash
# Установить Ansible
sudo apt update
sudo apt install ansible python3-pip

# Проверить
ansible --version

# Установить коллекции
cd /home/fessan/project/tg-daily-bot-/deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

---

## Шаг 2: Настроить inventory.ini (2 минуты)

Отредактировать файл `deployment/ansible/inventory.ini`:

```bash
nano deployment/ansible/inventory.ini
```

Заменить `your-server-ip` на реальный IP:
```ini
prod-server ansible_host=123.45.67.89 ansible_user=deploy ansible_port=22
```

Сохранить (Ctrl+O, Enter, Ctrl+X)

---

## Шаг 3: Создать Ansible Vault с токеном (3 минуты)

```bash
cd /home/fessan/project/tg-daily-bot-/deployment/ansible

# Создать зашифрованный файл
ansible-vault create group_vars/vault.yml
```

В редакторе ввести:
```yaml
vault_bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

Замените на ваш реальный токен от @BotFather.

Сохранить и выйти.

---

## Шаг 4: Задеплоить! (3-5 минут)

```bash
cd /home/fessan/project/tg-daily-bot-

# Проверить подключение
make ansible-ping

# Деплой
make deploy
```

При запросе пароля vault введите тот же пароль, что использовали при создании.

---

## Готово! 🎉

Бот запущен на сервере.

### Проверить статус:
```bash
make deploy-logs
```

### Или на сервере:
```bash
ssh deploy@ВАШ_IP
docker logs -f tg-daily-bot
```

---

## Быстрые команды

```bash
make deploy          # Полный деплой
make deploy-restart  # Перезапустить
make deploy-logs     # Логи
make deploy-backup   # Бэкап БД
```

---

## Если что-то пошло не так

**Ansible не найден:**
```bash
sudo apt install ansible
```

**SSH не работает:**
```bash
ssh-copy-id deploy@ВАШ_IP
```

**Docker на сервере нет:**
Не беспокойтесь, Ansible установит автоматически.

**Ошибка "collection not found":**
```bash
cd deployment/ansible
ansible-galaxy collection install -r requirements.yml
```

---

**Подробная документация:** `DEPLOYMENT.md` и `DEPLOYMENT_CHECKLIST.md`









