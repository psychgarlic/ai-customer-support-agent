"""Тесты Pydantic-схем агента."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.schemas import (
    AgentResponse,
    Category,
    Priority,
    Sentiment,
    TicketAnalysis,
    ToolUsage,
)


class TestTicketAnalysis:
    """Тесты модели TicketAnalysis."""

    def test_create_valid_analysis(self) -> None:
        """Создание валидного анализа."""
        analysis = TicketAnalysis(
            category=Category.DELIVERY,
            priority=Priority.NORMAL,
            sentiment=Sentiment.NEUTRAL,
            reason="Клиент спрашивает о статусе доставки, стандартный запрос.",
        )
        assert analysis.category == Category.DELIVERY
        assert analysis.requires_human is False

    def test_requires_human_default(self) -> None:
        """requires_human по умолчанию False."""
        analysis = TicketAnalysis(
            category=Category.OTHER,
            priority=Priority.LOW,
            sentiment=Sentiment.POSITIVE,
            reason="Простой вопрос.",
        )
        assert analysis.requires_human is False

    def test_missing_information_list(self) -> None:
        """missing_information — список строк."""
        analysis = TicketAnalysis(
            category=Category.PAYMENT,
            priority=Priority.HIGH,
            sentiment=Sentiment.NEGATIVE,
            reason="Проблема с оплатой.",
            missing_information=["Номер заказа", "Сумма списания"],
        )
        assert len(analysis.missing_information) == 2

    def test_reason_min_length(self) -> None:
        """reason должен быть не короче 10 символов."""
        with pytest.raises(ValidationError, match="string_too_short"):
            TicketAnalysis(
                category=Category.OTHER,
                priority=Priority.LOW,
                sentiment=Sentiment.NEUTRAL,
                reason="Кратко",  # Too short
            )

    def test_enum_values(self) -> None:
        """Проверка допустимых значений перечислений."""
        # Все категории
        for cat in Category:
            analysis = TicketAnalysis(
                category=cat,
                priority=Priority.NORMAL,
                sentiment=Sentiment.NEUTRAL,
                reason="Это тестовый анализ для проверки.",
            )
            assert analysis.category == cat

        # Все приоритеты
        for pri in Priority:
            analysis = TicketAnalysis(
                category=Category.OTHER,
                priority=pri,
                sentiment=Sentiment.NEUTRAL,
                reason="Это тестовый анализ для проверки.",
            )
            assert analysis.priority == pri

        # Все тональности
        for sen in Sentiment:
            analysis = TicketAnalysis(
                category=Category.OTHER,
                priority=Priority.NORMAL,
                sentiment=sen,
                reason="Это тестовый анализ для проверки.",
            )
            assert analysis.sentiment == sen


class TestToolUsage:
    """Тесты модели ToolUsage."""

    def test_create_tool_usage(self) -> None:
        """Создание записи об использовании инструмента."""
        tool = ToolUsage(
            name="search_support_knowledge",
            query="доставка сроки москва",
            result_summary="Доставка по Москве: 1-2 рабочих дня.",
        )
        assert tool.name == "search_support_knowledge"
        assert len(tool.result_summary) > 0


class TestAgentResponse:
    """Тесты модели AgentResponse."""

    def test_create_full_response(self) -> None:
        """Создание полного ответа агента."""
        response = AgentResponse(
            analysis=TicketAnalysis(
                category=Category.DELIVERY,
                priority=Priority.HIGH,
                sentiment=Sentiment.NEGATIVE,
                reason="Задержка доставки.",
            ),
            reply="Спасибо за обращение. Мы проверим статус вашего заказа.",
            tools_used=[
                ToolUsage(
                    name="search_support_knowledge",
                    query="доставка задержка",
                    result_summary="Информация о задержках.",
                ),
            ],
            escalate_note="",
        )
        assert response.analysis.category == Category.DELIVERY
        assert len(response.reply) > 10
        assert len(response.tools_used) == 1

    def test_response_without_tools(self) -> None:
        """Ответ без использования инструментов."""
        response = AgentResponse(
            analysis=TicketAnalysis(
                category=Category.OTHER,
                priority=Priority.LOW,
                sentiment=Sentiment.POSITIVE,
                reason="Простой вопрос.",
            ),
            reply="Спасибо за ваш вопрос!",
        )
        assert response.tools_used == []
        assert response.escalate_note == ""

    def test_response_with_escalation(self) -> None:
        """Ответ с эскалацией."""
        response = AgentResponse(
            analysis=TicketAnalysis(
                category=Category.TECHNICAL_ISSUE,
                priority=Priority.CRITICAL,
                sentiment=Sentiment.NEGATIVE,
                reason="Подозрение на мошенничество.",
                requires_human=True,
            ),
            reply="Передаём ваш вопрос специалисту.",
            escalate_note="Требуется передача оператору. Причина: подозрение на мошенничество.",
        )
        assert response.analysis.requires_human is True
        assert "оператору" in response.escalate_note.lower()
