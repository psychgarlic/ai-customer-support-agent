"""Тесты бизнес-логики SupportService (без обращения к GigaChat API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.assistant import SupportAssistant
from agent.schemas import AgentResponse, TicketAnalysis
from services.support_service import SupportService


class TestSupportService:
    """Тесты SupportService с мокированным ассистентом."""

    def test_process_ticket_with_mock(self) -> None:
        """Обработка обращения с мокированным ассистентом."""
        mock_assistant = MagicMock()
        mock_assistant.process.return_value = AgentResponse(
            analysis=TicketAnalysis(
                category="delivery",
                priority="normal",
                sentiment="neutral",
                reason="Стандартный запрос о доставке.",
            ),
            reply="Ваш заказ в пути. Ожидайте доставку в течение 1-2 дней.",
        )

        service = SupportService(assistant=mock_assistant)
        response = service.process_ticket("Где мой заказ?")

        assert response.analysis.category == "delivery"
        assert "в пути" in response.reply.lower()

    def test_process_ticket_empty_message(self) -> None:
        """Пустое сообщение вызывает ValueError."""
        service = SupportService()
        with pytest.raises(ValueError, match="пуст"):
            service.process_ticket("")

    def test_process_ticket_whitespace_only(self) -> None:
        """Сообщение из пробелов вызывает ValueError."""
        service = SupportService()
        with pytest.raises(ValueError, match="пуст"):
            service.process_ticket("   \n\t  ")

    def test_process_ticket_without_assistant(self) -> None:
        """Вызов без инициализированного ассистента."""
        service = SupportService(assistant=None)
        with pytest.raises(RuntimeError, match="ассистент"):
            service.process_ticket("Тестовое сообщение")

    def test_get_customer_not_found(self) -> None:
        """Поиск несуществующего клиента."""
        service = SupportService()
        result = service.get_customer("nonexistent@example.com")
        assert result is None

    def test_get_order_status_access_control(self) -> None:
        """Проверка: нельзя получить чужой заказ."""
        service = SupportService()
        # Заказ №1 принадлежит клиенту №1
        result = service.get_order_status(order_id=1, customer_id=999)
        assert result is None  # Чужой заказ — доступ запрещён


class TestSupportServiceCreate:
    """Тесты фабричного метода create()."""

    @patch("services.support_service.settings")
    @patch("services.support_service.GigaChatService")
    def test_create_with_gigachat(self, mock_gigachat_class, mock_settings) -> None:
        """Создание сервиса с GigaChat (мокированным)."""
        mock_settings.validate = MagicMock()
        mock_instance = MagicMock()
        mock_gigachat_class.return_value = mock_instance

        service = SupportService.create()
        assert service._assistant is not None
        mock_gigachat_class.assert_called_once()


class TestSupportAssistant:
    """Тесты SupportAssistant с мокированным GigaChatService."""

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Создаёт мокированный GigaChatService."""
        service = MagicMock()
        # Настраиваем parse() для возврата TicketAnalysis
        mock_response = MagicMock()
        mock_response.messages = [
            MagicMock(content="Тестовый ответ.")
        ]
        service.chat.create.return_value = mock_response
        service.chat.parse.return_value = (
            mock_response,
            TicketAnalysis(
                category="delivery",
                priority="normal",
                sentiment="neutral",
                reason="Тестовый анализ.",
            ),
        )
        return service

    def test_process_calls_gigachat(self, mock_service: MagicMock) -> None:
        """Проверка, что process вызывает GigaChat."""
        # Настраиваем mock для function_call
        mock_function_call = MagicMock()
        mock_function_call.name = "search_support_knowledge"
        mock_function_call.arguments = {"query": "доставка"}

        mock_message = MagicMock()
        mock_message.content = "Тестовый ответ."
        mock_message.function_call = None  # Нет function call в этом сообщении

        mock_response = MagicMock()
        mock_response.messages = [mock_message]
        mock_service.chat.create.return_value = mock_response

        mock_parsed = TicketAnalysis(
            category="delivery",
            priority="normal",
            sentiment="neutral",
            reason="Тестовый анализ.",
        )
        mock_service.chat.parse.return_value = (mock_response, mock_parsed)

        assistant = SupportAssistant(mock_service)
        response = assistant.process("Где мой заказ?")

        assert response.analysis.category == "delivery"
        mock_service.chat.create.assert_called()

    def test_process_empty_message(self, mock_service: MagicMock) -> None:
        """Пустое сообщение вызывает ValueError."""
        assistant = SupportAssistant(mock_service)
        with pytest.raises(ValueError, match="пуст"):
            assistant.process("")
