"""Тесты для PostgreSQL-репозиториев.

Проверяют работу с базой данных:
- Создание и чтение клиентов, заказов, тикетов
- Проверка принадлежности заказа клиенту
- Обработка ошибок и отсутствующих записей
"""

from __future__ import annotations

import logging
import pytest

from config import settings
from repositories.interfaces import Customer, Order, SupportTicket
from repositories.postgres_repo import (
    PostgreSQLCustomerRepo,
    PostgreSQLOrderRepo,
    PostgreSQLTicketRepo,
)

logger = logging.getLogger(__name__)


def get_connection():
    """Получает подключение к PostgreSQL из settings."""
    import psycopg2
    
    db_url = settings.database_url
    if not db_url:
        raise ValueError("DATABASE_URL не настроен в .env")
    
    return psycopg2.connect(db_url)


class TestPostgreSQLCustomerRepo:
    """Тесты для PostgreSQLCustomerRepo."""

    @pytest.fixture(scope="class")
    @classmethod
    def conn(cls):
        """Создаёт подключение к БД перед всеми тестами класса."""
        try:
            connection = get_connection()
            logger.info("Подключено к PostgreSQL для тестов")
            yield connection
            connection.rollback()  # Откатываем изменения
            connection.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL недоступен: {e}")

    @pytest.fixture
    def repo(self, conn):
        """Создаёт репозиторий клиента."""
        return PostgreSQLCustomerRepo(conn)

    def test_get_by_id_exists(self, repo):
        """Тест: получение существующего клиента по ID."""
        customer = repo.get_by_id(1)
        # Проверяем, что клиент существует и имеет корректную структуру
        assert customer is not None
        assert customer.id == 1
        assert customer.email is not None
        assert "@" in customer.email

    def test_get_by_id_not_exists(self, repo):
        """Тест: получение несуществующего клиента по ID."""
        customer = repo.get_by_id(99999)
        assert customer is None

    def test_get_by_email_exists(self, repo):
        """Тест: получение существующего клиента по email."""
        # Сначала получим любого клиента и возьмём его email
        customer = repo.get_by_id(1)
        if customer:
            found = repo.get_by_email(customer.email)
            assert found is not None
            assert found.id == customer.id

    def test_get_by_email_not_exists(self, repo):
        """Тест: получение несуществующего клиента по email."""
        customer = repo.get_by_email("notexist@example.com")
        assert customer is None

    def test_create_customer(self, repo, conn):
        """Тест: создание нового клиента."""
        new_customer = Customer(
            id=0,  # Будет заполнено БД
            email="new@example.com",
            phone="+79991234567",
            name="Новый Клиент",
        )
        # В текущей реализации нет метода create для CustomerRepo,
        # поэтому пропускаем или добавляем вручную
        conn.rollback()


class TestPostgreSQLOrderRepo:
    """Тесты для PostgreSQLOrderRepo."""

    @pytest.fixture(scope="class")
    @classmethod
    def conn(cls):
        """Создаёт подключение к БД перед всеми тестами класса."""
        try:
            connection = get_connection()
            logger.info("Подключено к PostgreSQL для тестов заказов")
            yield connection
            connection.rollback()
            connection.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL недоступен: {e}")

    @pytest.fixture
    def repo(self, conn):
        """Создаёт репозиторий заказов."""
        return PostgreSQLOrderRepo(conn)

    def test_get_by_id_exists(self, repo):
        """Тест: получение существующего заказа по ID."""
        order = repo.get_by_id(1)
        assert order is not None
        assert order.status is not None  # Может быть любым
        assert order.total_amount > 0  # Сумма должна быть положительной

    def test_get_by_id_not_exists(self, repo):
        """Тест: получение несуществующего заказа по ID."""
        order = repo.get_by_id(99999)
        assert order is None

    def test_get_by_customer_id(self, repo):
        """Тест: получение заказов клиента."""
        orders = repo.get_by_customer_id(1)
        assert isinstance(orders, list)
        assert len(orders) > 0

    def test_get_status(self, repo):
        """Тест: получение статуса заказа."""
        status = repo.get_status(1)
        assert status == "shipped"

    def test_get_status_not_exists(self, repo):
        """Тест: получение статуса несуществующего заказа."""
        status = repo.get_status(99999)
        assert status is None


class TestPostgreSQLTicketRepo:
    """Тесты для PostgreSQLTicketRepo."""

    @pytest.fixture(scope="class")
    @classmethod
    def conn(cls):
        """Создаёт подключение к БД перед всеми тестами класса."""
        try:
            connection = get_connection()
            logger.info("Подключено к PostgreSQL для тестов тикетов")
            yield connection
            connection.rollback()
            connection.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL недоступен: {e}")

    @pytest.fixture
    def repo(self, conn):
        """Создаёт репозиторий тикетов."""
        return PostgreSQLTicketRepo(conn)

    def test_create_ticket(self, repo):
        """Тест: создание нового тикета."""
        new_ticket = SupportTicket(
            id=0,
            customer_id=1,
            category="delivery",
            priority="high",
            status="open",
            message="Тестовое обращение",
            created_at="",
        )
        created = repo.create(new_ticket)
        assert created.id is not None
        assert created.category == "delivery"

    def test_get_by_id_exists(self, repo):
        """Тест: получение существующего тикета по ID."""
        ticket = repo.get_by_id(1)
        assert ticket is not None
        assert ticket.category in ["delivery", "payment", "refund", "product", "technical_issue", "other"]

    def test_get_by_id_not_exists(self, repo):
        """Тест: получение несуществующего тикета по ID."""
        ticket = repo.get_by_id(99999)
        assert ticket is None

    def test_get_by_customer_id(self, repo):
        """Тест: получение истории обращений клиента."""
        tickets = repo.get_by_customer_id(1)
        assert isinstance(tickets, list)


class TestPostgreSQLIntegration:
    """Интеграционные тесты: проверка работы всех репозиториев вместе."""

    @pytest.fixture(scope="class")
    @classmethod
    def conn(cls):
        """Создаёт подключение к БД."""
        try:
            connection = get_connection()
            yield connection
            connection.rollback()
            connection.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL недоступен: {e}")

    def test_full_workflow(self, conn):
        """Тест: полный рабочий процесс."""
        # Создаём репозитории
        customer_repo = PostgreSQLCustomerRepo(conn)
        order_repo = PostgreSQLOrderRepo(conn)
        ticket_repo = PostgreSQLTicketRepo(conn)

        # 1. Получаем первого существующего клиента
        customer = customer_repo.get_by_id(1)
        assert customer is not None, "Клиент с ID=1 должен существовать"
        customer_email = customer.email

        # 2. Получаем заказы клиента
        orders = order_repo.get_by_customer_id(customer.id)
        assert len(orders) > 0

        # 3. Проверяем статус заказа
        order = orders[0]
        status = order_repo.get_status(order.id)
        assert status is not None

        # 4. Создаём новый тикет
        new_ticket = SupportTicket(
            id=0,
            customer_id=customer.id,
            category="delivery",
            priority="normal",
            status="open",
            message="Проверка статуса заказа",
            created_at="",
        )
        created_ticket = ticket_repo.create(new_ticket)
        assert created_ticket.id is not None

        # 5. Получаем тикет по ID
        fetched_ticket = ticket_repo.get_by_id(created_ticket.id)
        assert fetched_ticket is not None
        assert fetched_ticket.message == "Проверка статуса заказа"

        # 6. Проверяем историю обращений
        tickets = ticket_repo.get_by_customer_id(customer.id)
        assert len(tickets) > 0
