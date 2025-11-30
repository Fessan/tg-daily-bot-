"""
Unit тесты для модуля utils
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from freezegun import freeze_time

from utils import is_workday, delete_later


class TestIsWorkday:
    """Тесты для функции is_workday()"""
    
    @pytest.mark.unit
    @freeze_time("2025-11-26")  # Среда
    def test_workday_wednesday(self):
        """Среда - рабочий день"""
        assert is_workday() is True
    
    @pytest.mark.unit
    @freeze_time("2025-11-29")  # Суббота
    def test_weekend_saturday(self):
        """Суббота - выходной"""
        assert is_workday() is False
    
    @pytest.mark.unit
    @freeze_time("2025-11-30")  # Воскресенье
    def test_weekend_sunday(self):
        """Воскресенье - выходной"""
        assert is_workday() is False
    
    @pytest.mark.unit
    @freeze_time("2025-01-01")  # Новый год
    def test_holiday_new_year(self):
        """Новый год - праздник"""
        assert is_workday() is False
    
    @pytest.mark.unit
    @freeze_time("2025-05-09")  # День Победы
    def test_holiday_victory_day(self):
        """День Победы - праздник"""
        assert is_workday() is False
    
    @pytest.mark.unit
    @freeze_time("2025-06-12")  # День России
    def test_holiday_russia_day(self):
        """День России - праздник"""
        assert is_workday() is False
    
    @pytest.mark.unit
    @freeze_time("2025-11-27")  # Четверг
    def test_workday_thursday(self):
        """Четверг - рабочий день"""
        assert is_workday() is True


class TestDeleteLater:
    """Тесты для функции delete_later()"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_message_success(self):
        """Успешное удаление сообщения"""
        mock_msg = AsyncMock()
        mock_msg.delete = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await delete_later(mock_msg, seconds=1)
        
        mock_msg.delete.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_message_error_suppressed(self):
        """Ошибка при удалении подавляется"""
        mock_msg = AsyncMock()
        mock_msg.delete = AsyncMock(side_effect=Exception("Message not found"))
        
        # Не должно бросать исключение
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await delete_later(mock_msg, seconds=1)
        
        mock_msg.delete.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_message_custom_timeout(self):
        """Удаление с кастомным таймаутом"""
        mock_msg = AsyncMock()
        mock_msg.delete = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await delete_later(mock_msg, seconds=300)
            mock_sleep.assert_called_once_with(300)
        
        mock_msg.delete.assert_called_once()










