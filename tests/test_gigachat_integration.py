"""Smoke-тест интеграции с GigaChat API.

Запускается ТОЛЬКО при наличии GIGACHAT_CREDENTIALS в окружении.
Для ручного тестирования реального API.

Запуск:
    pytest tests/test_gigachat_integration.py -v -m smoke
"""

from __future__ import annotations

import os

import pytest

from agent.schemas import TicketAnalysis
from integrations.gigachat import GigaChatService


@pytest.mark.smoke
@pytest.mark.skipif(
    not os.environ.get("GIGACHAT_CREDENTIALS"),
    reason="GIGACHAT_CREDENTIALS не установлен",
)
class TestGigaChatIntegration:
    """Smoke-тесты реального API GigaChat."""

    @pytest.fixture
    def service(self) -> GigaChatService:
        """Создаёт сервис для тестов."""
        return GigaChatService()

    def test_basic_chat(self, service: GigaChatService) -> None:
        """Базовый запрос к API."""
        response = service.chat.create(
            messages=[
                MagicMock(role="user", content="Ответь 'OK' одним словом."),
            ],
        )
        assert response is not None

    def test_structured_output(self, service: GigaChatService) -> None:
        """Запрос со структурированным выводом."""
        completion, parsed = service.chat.parse(
            "Категория: доставка. Приоритет: нормальный. Тональность: нейтральная. Причина: стандартный запрос.",
            response_format=TicketAnalysis,
            strict=True,
        )
        assert parsed.category is not None
        assert parsed.priority is not None


from unittest.mock import MagicMock
