"""Инструменты (tools) для AI-агента.

Реализует function calling:
- search_support_knowledge(query) — поиск по базе знаний
- get_support_policy(category) — получение правил обработки категории
- get_order_status(order_id) — проверка статуса заказа из БД
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Глобальное подключение к PostgreSQL (заполняется при инициализации)
_db_connection: Optional[Any] = None

# Путь к базе знаний (относительно корня проекта)
_KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"

# Кэш содержимого файлов базы знаний
_kb_cache: Dict[str, str] = {}


def _load_knowledge_base() -> None:
    """Загружает все MD-файлы базы знаний в кэш."""
    global _kb_cache
    if _kb_cache:
        return  # Уже загружено

    if not _KB_DIR.exists():
        logger.warning("Директория базы знаний не найдена: %s", _KB_DIR)
        return

    for md_file in _KB_DIR.glob("*.md"):
        _kb_cache[md_file.stem] = md_file.read_text(encoding="utf-8")

    logger.info("База знаний загружена: %d файлов", len(_kb_cache))


def _search_in_content(content: str, query: str, top_n: int = 3) -> List[str]:
    """Простой текстовый поиск по содержимому файла."""
    query_lower = query.lower()
    sentences = content.split("\n")
    scored: List[tuple[int, str]] = []

    for i, sentence in enumerate(sentences):
        score = sum(1 for word in query_lower.split() if word in sentence.lower())
        if score > 0:
            scored.append((score, sentence.strip()))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_n]]


def search_support_knowledge(query: str) -> str:
    """
    Ищет информацию в локальной базе знаний.

    Args:
        query: Запрос на русском языке (3-5 ключевых слов).

    Returns:
        Найденные фрагменты текста или сообщение об отсутствии информации.
    """
    _load_knowledge_base()

    if not query or not query.strip():
        return "Ошибка: запрос не может быть пустым."

    results: List[str] = []
    for source_name, content in _kb_cache.items():
        matches = _search_in_content(content, query)
        for match in matches:
            results.append(f"[{source_name}]: {match}")

    if not results:
        return (
            f"В базе знаний не найдено информации по запросу «{query}». "
            "Рекомендую дать общий ответ, основываясь на общих правилах обслуживания клиентов."
        )

    return "\n\n".join(results)


def get_support_policy(category: str) -> str:
    """
    Возвращает правила обработки обращений определённой категории.

    Args:
        category: Категория обращения (delivery, payment, refund, product,
                  technical_issue, other).

    Returns:
        Правила обработки или сообщение о неизвестной категории.
    """
    _load_knowledge_base()

    policies: Dict[str, str] = {
        "delivery": textwrap.dedent("""\
            ПРАВИЛА ОБРАБОТКИ КАТЕГОРИИ «ДОСТАВКА»:
            1. Проверьте трек-номер и статус отправки.
            2. Сообщите клиенту ориентировочные сроки.
            3. Если доставка задержана — извинитесь и предложите компенсацию (скидка 5%).
            4. Изменение адреса — только до передачи курьеру.
            5. Не гарантируйте точное время доставки.
            6. Эскалировать, если доставка потеряна или просрочена более чем на 7 дней.
        """),
        "payment": textwrap.dedent("""\
            ПРАВИЛА ОБРАБОТКИ КАТЕГОРИИ «ОПЛАТА»:
            1. Не храните и не запрашивайте данные карт клиента.
            2. Если списание есть, а заказа нет — предложите написать в поддержку.
            3. Не подтверждайте оплату вручную — проверяйте через систему.
            4. Возврат денег — 3-10 рабочих дней на карту.
            5. Эскалировать при подозрении на мошенничество с картой.
        """),
        "refund": textwrap.dedent("""\
            ПРАВИЛА ОБРАБОТКИ КАТЕГОРИИ «ВОЗВРАТ»:
            1. Товар надлежащего качества — 14 дней.
            2. Ненадлежащего — гарантийный срок или 1 год.
            3. Не принимайте возвраты без номера заказа.
            4. Не гарантируйте возврат денег — только после проверки товара.
            5. Запрещённые к возврату товары: бельё, парфюмерия, электронные товары.
            6. Эскалировать, если клиент требует немедленного возврата без проверки.
        """),
        "product": textwrap.dedent("""\
            ПРАВИЛА ОБРАБОТКИ КАТЕГОРИИ «ТОВАР»:
            1. Не гарантируйте наличие товара — проверяйте в системе.
            2. Не называйте цены, если нет точных данных.
            3. Предлагайте аналоги, если товар недоступен.
            4. Характеристики — только из каталога.
            5. Эскалировать, если клиент запрашивает информацию, которой нет в каталоге.
        """),
        "technical_issue": textwrap.dedent("""\
            ПРАВИЛА ОБРАБОТКИ КАТЕГОРИИ «ТЕХНИЧЕСКАЯ ПРОБЛЕМА»:
            1. Попросите скриншот ошибки и описание действий.
            2. Не обещайте исправлений — передайте разработчикам.
            3. Предложите временное решение (очистить кэш, другой браузер).
            4. Не меняйте данные аккаунта клиента.
            5. Эскалировать при массовых проблемах или потере данных.
        """),
        "other": textwrap.dedent("""\
            ПРАВИЛА ОБРАБОТКИ КАТЕГОРИИ «ДРУГОЕ»:
            1. Постарайтесь определить реальную категорию.
            2. Дайте общий вежливый ответ.
            3. Если не можете помочь — предложите оператора.
        """),
    }

    category_lower = category.lower()
    if category_lower in policies:
        return policies[category_lower]

    return f"Неизвестная категория: «{category}». Обратитесь к старшему оператору."


def init_db_connection(conn: Any) -> None:
    """Инициализирует подключение к PostgreSQL для инструментов."""
    global _db_connection
    _db_connection = conn


def get_order_status(order_id: str) -> str:
    """
    Проверяет статус заказа в базе данных.

    Args:
        order_id: Номер заказа (строка, будет преобразована в int).

    Returns:
        Статус заказа или сообщение об отсутствии.
    """
    if _db_connection is None:
        return "База данных не подключена."

    import psycopg2

    try:
        order_id_int = int(order_id)
    except ValueError:
        return f"Некорректный номер заказа: «{order_id}». Введите число."

    with _db_connection.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, customer_id, status, total_amount FROM orders WHERE id = %s",
            (order_id_int,),
        )
        row = cur.fetchone()

    if not row:
        return f"Заказ №{order_id_int} не найден в системе."

    status_labels = {
        "processing": "Заказ обрабатывается",
        "shipped": "Заказ в пути",
        "delivered": "Заказ доставлен",
        "cancelled": "Заказ отменён",
    }

    status_text = status_labels.get(row["status"], row["status"])
    total = float(row["total_amount"])

    return (
        f"Заказ №{row['id']}\n"
        f"Статус: {status_text}\n"
        f"Сумма: {total:,.2f} руб."
    )
