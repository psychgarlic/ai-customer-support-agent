"""Pydantic-модели для структурированного анализа обращений."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Категория обращения клиента."""

    DELIVERY = "delivery"
    PAYMENT = "payment"
    REFUND = "refund"
    PRODUCT = "product"
    TECHNICAL_ISSUE = "technical_issue"
    OTHER = "other"


class Priority(str, Enum):
    """Приоритет обработки обращения."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Sentiment(str, Enum):
    """Тональность обращения клиента."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class TicketAnalysis(BaseModel):
    """Структурированный результат анализа обращения."""

    category: Category = Field(description="Категория обращения")
    priority: Priority = Field(description="Приоритет обработки")
    sentiment: Sentiment = Field(description="Тональность обращения")
    requires_human: bool = Field(
        default=False,
        description="Необходимость передачи обращения живому оператору",
    )
    reason: str = Field(
        description="Обоснование принятого решения: почему выбрана категория, приоритет и т.д.",
        min_length=10,
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Список недостающей информации, которую нужно уточнить у клиента",
    )


class ToolUsage(BaseModel):
    """Информация об использованном инструменте."""

    name: str = Field(description="Название вызванного инструмента")
    query: str = Field(description="Аргументы / запрос, переданный инструменту")
    result_summary: str = Field(description="Краткий результат работы инструмента")


class AgentResponse(BaseModel):
    """Полный ответ агента — результат обработки обращения."""

    analysis: TicketAnalysis = Field(description="Результат анализа обращения")
    reply: str = Field(
        description="Готовый ответ клиенту на языке обращения",
        min_length=10,
    )
    tools_used: List[ToolUsage] = Field(
        default_factory=list,
        description="Список вызванных инструментов",
    )
    escalate_note: str = Field(
        default="",
        description="Комментарий при эскалации: почему нужен оператор",
    )
