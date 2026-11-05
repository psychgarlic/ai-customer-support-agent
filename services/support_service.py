"""Сервис поддержки — бизнес-логика приложения.

Оркестрирует работу AI-ассистента и репозиториев.
Не зависит от конкретной реализации БД или LLM.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.assistant import SupportAssistant
from agent.schemas import AgentResponse
from config import settings
from integrations.gigachat import GigaChatService
from repositories.interfaces import (
    CustomerRepo,
    InMemoryCustomerRepo,
    InMemoryOrderRepo,
    InMemoryTicketRepo,
    OrderRepo,
    TicketRepo,
)
from repositories.postgres_repo import (
    PostgreSQLCustomerRepo,
    PostgreSQLOrderRepo,
    PostgreSQLTicketRepo,
)
from tools.knowledge_tools import init_db_connection

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class SupportService:
    """
    Сервис обработки обращений в поддержку.

    Это центральный компонент приложения:
    - Получает текст обращения от UI
    - Передаёт его AI-ассистенту
    - Возвращает структурированный ответ

    Не знает про Streamlit, GigaChat SDK или базу данных напрямую —
    использует абстракции (Assistant, Repository).
    """

    def __init__(
        self,
        assistant: Optional[SupportAssistant] = None,
        customer_repo: Optional[CustomerRepo] = None,
        order_repo: Optional[OrderRepo] = None,
        ticket_repo: Optional[TicketRepo] = None,
    ) -> None:
        self._assistant = assistant
        self._customer_repo = customer_repo or InMemoryCustomerRepo()
        self._order_repo = order_repo or InMemoryOrderRepo()
        self._ticket_repo = ticket_repo or InMemoryTicketRepo()

    @classmethod
    def create(cls) -> "SupportService":
        """
        Фабричный метод для создания сервиса с GigaChat.

        Использует настройки из .env.
        """
        settings.validate()

        service = GigaChatService()
        assistant = SupportAssistant(service)
        return cls(assistant=assistant)

    @classmethod
    def create_with_postgres(
        cls,
        db_url: str,
    ) -> "SupportService":
        """
        Фабричный метод для создания сервиса с PostgreSQL.

        Args:
            db_url: URL подключения к PostgreSQL.
                    Пример: "postgresql://postgres:password@localhost:5432/agentai"

        Returns:
            SupportService с PostgreSQL-репозиториями.
        """
        import psycopg2

        settings.validate()

        # Подключаемся к PostgreSQL
        conn = psycopg2.connect(db_url)

        # Инициализируем подключение для инструментов
        init_db_connection(conn)

        # Создаём PostgreSQL-репозитории
        customer_repo = PostgreSQLCustomerRepo(conn)
        order_repo = PostgreSQLOrderRepo(conn)
        ticket_repo = PostgreSQLTicketRepo(conn)

        # Создаём GigaChat-сервис
        service = GigaChatService()
        assistant = SupportAssistant(service)

        logger.info("Подключено к PostgreSQL: %s", db_url)

        return cls(
            assistant=assistant,
            customer_repo=customer_repo,
            order_repo=order_repo,
            ticket_repo=ticket_repo,
        )

    def process_ticket(self, message: str) -> AgentResponse:
        """
        Обрабатывает обращение клиента.

        Args:
            message: Текст обращения.

        Returns:
            Структурированный ответ агента.

        Raises:
            ValueError: Если сообщение пустое.
            RuntimeError: Если сервис не настроен.
        """
        if not message or not message.strip():
            raise ValueError("Сообщение не может быть пустым")

        if self._assistant is None:
            raise RuntimeError(
                "AI-ассистент не инициализирован. "
                "Используйте SupportService.create() или передайте assistant."
            )

        logger.info("Обработка обращения: %s", message[:100])

        try:
            response = self._assistant.process(message)
        except Exception as e:
            logger.error("Ошибка обработки обращения: %s", e, exc_info=True)
            raise RuntimeError(f"Ошибка обработки обращения: {e}") from e

        return response

    def get_customer(self, email: str) -> Optional[dict]:
        """Получает информацию о клиенте по email (для будущей интеграции)."""
        customer = self._customer_repo.get_by_email(email)
        if not customer:
            return None
        return {
            "id": customer.id,
            "email": customer.email,
            "phone": customer.phone,
            "name": customer.name,
        }

    def get_order_status(self, order_id: int, customer_id: int) -> Optional[dict]:
        """
        Получает статус заказа с проверкой принадлежности клиенту.

        Нельзя предоставлять информацию о чужих заказах!
        """
        order = self._order_repo.get_by_id(order_id)
        if not order:
            return None
        if order.customer_id != customer_id:
            logger.warning(
                "Попытка доступа к чужому заказу: order=%d, customer=%d",
                order_id, customer_id,
            )
            return None  # Не раскрываем информацию о чужих заказах
        return {
            "id": order.id,
            "status": order.status,
            "total_amount": order.total_amount,
            "items": order.items,
        }
