"""
Модуль обработчиков команд бота
Импортирует и регистрирует все handlers
"""

# Импортируем все модули с обработчиками
# Это автоматически регистрирует их через декоратор @dp.message()
from . import admin
from . import reports
from . import common
from . import daily

__all__ = ['admin', 'reports', 'common', 'daily']










