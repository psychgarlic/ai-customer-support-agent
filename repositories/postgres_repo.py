"""PostgreSQL-репозитории для работы с базой данных.

Заменяют InMemory-репозитории при подключении PostgreSQL.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from repositories.interfaces import Customer, CustomerRepo, Order, OrderRepo, SupportTicket, TicketRepo

logger = logging.getLogger(__name__)


class PostgreSQLCustomerRepo(CustomerRepo):
    """Реализация CustomerRepo для PostgreSQL."""

    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.conn = conn

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, phone, name FROM customers WHERE id = %s",
                (customer_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Customer(
                id=row["id"],
                email=row["email"],
                phone=row["phone"],
                name=row["name"],
            )

    def get_by_email(self, email: str) -> Optional[Customer]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, email, phone, name FROM customers WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Customer(
                id=row["id"],
                email=row["email"],
                phone=row["phone"],
                name=row["name"],
            )


class PostgreSQLOrderRepo(OrderRepo):
    """Реализация OrderRepo для PostgreSQL."""

    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.conn = conn

    def get_by_id(self, order_id: int) -> Optional[Order]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, customer_id, status, total_amount, created_at FROM orders WHERE id = %s",
                (order_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Order(
                id=row["id"],
                customer_id=row["customer_id"],
                status=row["status"],
                total_amount=float(row["total_amount"]),
                created_at=str(row["created_at"]),
            )

    def get_by_customer_id(self, customer_id: int) -> List[Order]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, customer_id, status, total_amount, created_at FROM orders WHERE customer_id = %s ORDER BY created_at DESC",
                (customer_id,),
            )
            rows = cur.fetchall()
            return [
                Order(
                    id=r["id"],
                    customer_id=r["customer_id"],
                    status=r["status"],
                    total_amount=float(r["total_amount"]),
                    created_at=str(r["created_at"]),
                )
                for r in rows
            ]

    def get_status(self, order_id: int) -> Optional[str]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT status FROM orders WHERE id = %s",
                (order_id,),
            )
            row = cur.fetchone()
            return row["status"] if row else None


class PostgreSQLTicketRepo(TicketRepo):
    """Реализация TicketRepo для PostgreSQL."""

    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self.conn = conn

    def create(self, ticket: SupportTicket) -> SupportTicket:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO support_tickets (customer_id, category, priority, status, message)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (
                    ticket.customer_id,
                    ticket.category,
                    ticket.priority,
                    ticket.status,
                    ticket.message,
                ),
            )
            ticket.id = cur.fetchone()["id"]
            self.conn.commit()
            return ticket

    def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM support_tickets WHERE id = %s",
                (ticket_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return SupportTicket(
                id=row["id"],
                customer_id=row["customer_id"],
                category=row["category"],
                priority=row["priority"],
                status=row["status"],
                message=row["message"],
                created_at=str(row["created_at"]),
            )

    def get_by_customer_id(self, customer_id: int) -> List[SupportTicket]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM support_tickets WHERE customer_id = %s ORDER BY created_at DESC",
                (customer_id,),
            )
            rows = cur.fetchall()
            return [
                SupportTicket(
                    id=r["id"],
                    customer_id=r["customer_id"],
                    category=r["category"],
                    priority=r["priority"],
                    status=r["status"],
                    message=r["message"],
                    created_at=str(r["created_at"]),
                )
                for r in rows
            ]
