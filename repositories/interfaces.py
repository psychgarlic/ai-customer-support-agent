"""Интерфейсы репозиториев для будущей интеграции PostgreSQL (v2.0)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Customer:
    """Сущность клиента."""

    id: int
    email: str
    phone: Optional[str] = None
    name: Optional[str] = None


@dataclass
class Order:
    """Сущность заказа."""

    id: int
    customer_id: int
    status: str
    total_amount: float
    created_at: str
    items: List[str] = None  # type: ignore


@dataclass
class SupportTicket:
    """Сущность обращения в поддержку."""

    id: int
    customer_id: int
    category: str
    priority: str
    status: str
    message: str
    created_at: str


class CustomerRepo(ABC):
    """Интерфейс для работы с клиентами."""

    @abstractmethod
    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """Получить клиента по ID."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Customer]:
        """Получить клиента по email."""


class OrderRepo(ABC):
    """Интерфейс для работы с заказами."""

    @abstractmethod
    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Получить заказ по ID."""

    @abstractmethod
    def get_by_customer_id(self, customer_id: int) -> List[Order]:
        """Получить все заказы клиента."""

    @abstractmethod
    def get_status(self, order_id: int) -> Optional[str]:
        """Получить статус заказа по ID."""


class TicketRepo(ABC):
    """Интерфейс для работы с обращениями в поддержку."""

    @abstractmethod
    def create(self, ticket: SupportTicket) -> SupportTicket:
        """Создать новое обращение."""

    @abstractmethod
    def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        """Получить обращение по ID."""

    @abstractmethod
    def get_by_customer_id(self, customer_id: int) -> List[SupportTicket]:
        """Получить историю обращений клиента."""


class InMemoryCustomerRepo(CustomerRepo):
    """Демо-реализация CustomerRepo (в памяти, для v1.0)."""

    def __init__(self) -> None:
        self._customers: dict[int, Customer] = {
            1: Customer(id=1, email="test@example.com", phone="+79001234567", name="Тестовый Клиент"),
        }

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        return self._customers.get(customer_id)

    def get_by_email(self, email: str) -> Optional[Customer]:
        for c in self._customers.values():
            if c.email == email:
                return c
        return None


class InMemoryOrderRepo(OrderRepo):
    """Демо-реализация OrderRepo (в памяти, для v1.0)."""

    def __init__(self) -> None:
        self._orders: dict[int, Order] = {
            1: Order(
                id=1, customer_id=1, status="shipped", total_amount=15000.0,
                created_at="2026-11-01T10:00:00", items=["Ноутбук", "Чехол"],
            ),
        }

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return self._orders.get(order_id)

    def get_by_customer_id(self, customer_id: int) -> List[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]

    def get_status(self, order_id: int) -> Optional[str]:
        order = self._orders.get(order_id)
        return order.status if order else None


class InMemoryTicketRepo(TicketRepo):
    """Демо-реализация TicketRepo (в памяти, для v1.0)."""

    def __init__(self) -> None:
        self._tickets: dict[int, SupportTicket] = {}
        self._next_id: int = 1

    def create(self, ticket: SupportTicket) -> SupportTicket:
        ticket.id = self._next_id
        self._tickets[self._next_id] = ticket
        self._next_id += 1
        return ticket

    def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        return self._tickets.get(ticket_id)

    def get_by_customer_id(self, customer_id: int) -> List[SupportTicket]:
        return [t for t in self._tickets.values() if t.customer_id == customer_id]
