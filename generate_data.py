"""Генератор фейковых данных для базы данных."""

import random
import psycopg2

from config import settings

# Параметры генерации
NUM_CUSTOMERS = 500
NUM_ORDERS = 2000
NUM_TICKETS = 500

# Данные для генерации
FIRST_NAMES = [
    "Иван", "Мария", "Алексей", "Елена", "Дмитрий", "Анна", "Сергей",
    "Ольга", "Андрей", "Наталья", "Михаил", "Татьяна", "Николай",
    "Екатерина", "Владимир", "Ирина", "Павел", "Светлана", "Артём",
    "Юлия", "Максим", "Виктория", "Егор", "Полина", "Тимур",
]

LAST_NAMES = [
    "Петров", "Сидорова", "Козлов", "Новиков", "Морозов", "Волков",
    "Соколов", "Лебедев", "Кузнецов", "Попов", "Фёдоров", "Михайлов",
    "Борисов", "Иванов", "Семёнов", "Егоров", "Павлов", "Козмина",
    "Степанов", "Николаева",
]

DOMAINS = ["example.com", "mail.ru", "yandex.ru", "gmail.com"]

STATUSES = ["processing", "shipped", "delivered", "cancelled"]
STATUS_WEIGHTS = [0.15, 0.30, 0.45, 0.10]

PRIORITIES = ["low", "normal", "high", "critical"]
PRIORITY_WEIGHTS = [0.30, 0.40, 0.20, 0.10]

# Сообщения привязаны к статусам заказов
TICKET_MESSAGES = {
    "shipped": [
        "Где мой заказ? Уже прошла неделя",
        "Курьер не пришёл, хотя я ждал весь день",
        "Не могу отследить статус заказа по трек-номеру",
        "Заказ должен был прийти вчера, но я его не получил",
        "Когда будет доставлен мой заказ?",
    ],
    "processing": [
        "Оплата не проходит, карта рабочая",
        "Деньги списали, но заказ не подтверждён",
        "Не могу оплатить через СБП",
        "С меня списали деньги дважды за один заказ",
    ],
    "delivered": [
        "Купил наушники неделю назад, не работают, как вернуть?",
        "Товар пришёл с браком, хочу вернуть",
        "Возврат денег не приходит уже 2 недели",
        "Могу ли вернуть товар без чека?",
        "Заполняю заявку на возврат, но система выдаёт ошибку",
    ],
    "cancelled": [
        "Заказ отменили без предупреждения, верните деньги",
        "Деньги за отменённый заказ не вернули",
        "Почему мой заказ отменили?",
    ],
}


def generate_email() -> str:
    """Генерирует email на английском."""
    first = random.choice(["alex", "anna", "boris", "cat", "dmitry", "elena",
                           "fedor", "grigory", "helen", "igor", "julia", "kate",
                           "leo", "maria", "nick", "olga", "pavel", "queen",
                           "roman", "sarah", "tom", "ulya", "victor", "wendy",
                           "ivan", "maria", "alexey", "elena", "dmitry", "anna",
                           "sergey", "olga", "andrey", "natalia", "mikhail",
                           "tatyana", "nikolay", "ekaterina", "vladimir", "irina",
                           "pavel", "svetlana", "artem", "yulia", "maxim",
                           "victoria", "egor", "polina", "timur"])
    last = random.choice(["petrov", "sidorov", "kozlov", "novikov", "morozov",
                          "volkov", "sokolov", "lebedev", "kuznetsov", "popov",
                          "fedorov", "mikhailov", "borisov", "ivanov", "semenov",
                          "egorov", "pavlov", "kozmina", "stepanov", "nikolaeva"])
    suffix = random.randint(1, 999)
    return f"{first}.{last}{suffix}@{random.choice(DOMAINS)}"


def generate_name() -> str:
    """Генерирует случайное имя."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_orders(conn: psycopg2.extensions.connection, num_orders: int) -> list:
    """Генерирует заказы и возвращает список (customer_id, status, order_id)."""
    orders = []
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM customers")
        customer_ids = [r[0] for r in cur.fetchall()]

        for _ in range(num_orders):
            customer_id = random.choice(customer_ids)
            status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
            total = round(random.uniform(500, 50000), 2)
            orders.append((customer_id, status, total))

        cur.executemany(
            "INSERT INTO orders (customer_id, status, total_amount) VALUES (%s, %s, %s)",
            orders,
        )
        conn.commit()

    # Возвращаем список (customer_id, status, order_id) для создания обращений
    with conn.cursor() as cur:
        cur.execute("SELECT id, customer_id, status FROM orders")
        order_list = [(row[0], row[1], row[2]) for row in cur.fetchall()]
    return order_list


def generate_tickets(conn: psycopg2.extensions.connection, num_tickets: int, order_list: list) -> list:
    """Генерирует обращения, привязанные к конкретным заказам."""
    tickets = []
    used_order_ids = set()

    for _ in range(num_tickets):
        # Выбираем случайный заказ
        order_id, customer_id, order_status = random.choice(order_list)

        # Каждое обращение привязано к одному заказу
        if order_id in used_order_ids:
            continue  # Пропускаем дубликаты
        used_order_ids.add(order_id)

        # Категория обращения зависит от статуса заказа
        if order_status == "shipped":
            category = "delivery"
            priority = random.choices(PRIORITIES, weights=[0.20, 0.30, 0.35, 0.15], k=1)[0]
        elif order_status == "processing":
            category = "payment"
            priority = random.choices(PRIORITIES, weights=[0.25, 0.35, 0.30, 0.10], k=1)[0]
        elif order_status == "delivered":
            category = "refund"
            priority = random.choices(PRIORITIES, weights=[0.30, 0.40, 0.20, 0.10], k=1)[0]
        elif order_status == "cancelled":
            category = "payment"
            priority = random.choices(PRIORITIES, weights=[0.15, 0.25, 0.40, 0.20], k=1)[0]
        else:
            category = "other"
            priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS, k=1)[0]

        status = random.choice(["open", "open", "open", "closed"])
        message = random.choice(TICKET_MESSAGES[order_status])
        tickets.append((customer_id, category, priority, status, message, order_id))

    # Добавляем несколько обращений без привязки к заказу
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM customers")
        customer_ids = [r[0] for r in cur.fetchall()]

        remaining = num_tickets - len(tickets)
        for _ in range(remaining):
            customer_id = random.choice(customer_ids)
            category = random.choice(["product", "technical_issue", "other"])
            priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS, k=1)[0]
            status = random.choice(["open", "open", "closed"])
            messages = {
                "product": ["Есть ли этот товар в наличии в розовом цвете?",
                           "Какой размер у этой модели?",
                           "Есть ли гарантия на этот товар?"],
                "technical_issue": ["Не могу войти в личный кабинет",
                                   "Сайт не загружается",
                                   "Корзина не работает"],
                "other": ["Когда будет распродажа?",
                         "Есть ли скидки для студентов?"],
            }
            message = random.choice(messages[category])
            tickets.append((customer_id, category, priority, status, message, None))

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO support_tickets (customer_id, category, priority, status, message, order_id) VALUES (%s, %s, %s, %s, %s, %s)",
            tickets,
        )
        conn.commit()
    return tickets


def main():
    """Основная функция."""
    # Используем DATABASE_URL из .env
    db_url = settings.database_url
    if not db_url:
        print("Ошибка: DATABASE_URL не настроен в .env")
        print("Скопируйте .env.example в .env и укажите параметры подключения")
        return

    print(f"Подключение к PostgreSQL...")
    conn = psycopg2.connect(db_url)

    # Очищаем существующие данные
    print("Очистка таблиц...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE customers, orders, support_tickets RESTART IDENTITY")
        conn.commit()

    # Генерируем клиентов
    print(f"Генерация {NUM_CUSTOMERS} клиентов...")
    with conn.cursor() as cur:
        customers = []
        for _ in range(NUM_CUSTOMERS):
            name = generate_name()
            email = generate_email()
            phone = f"+79{random.randint(100000000, 999999999)}"
            customers.append((email, phone, name))

        cur.executemany(
            "INSERT INTO customers (email, phone, name) VALUES (%s, %s, %s)",
            customers,
        )
        conn.commit()
    print(f"Создано {NUM_CUSTOMERS} клиентов")

    # Генерируем заказы
    print(f"Генерация {NUM_ORDERS} заказов...")
    order_list = generate_orders(conn, NUM_ORDERS)
    print(f"Создано {len(order_list)} заказов")

    # Генерируем обращения (привязаны к заказам)
    print(f"Генерация {NUM_TICKETS} обращений...")
    tickets = generate_tickets(conn, NUM_TICKETS, order_list)
    print(f"Создано {len(tickets)} обращений")

    # Проверка
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM customers")
        print(f"Всего клиентов: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM orders")
        print(f"Всего заказов: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM support_tickets")
        print(f"Всего обращений: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM support_tickets WHERE order_id IS NOT NULL")
        print(f"Обращений с привязкой к заказу: {cur.fetchone()[0]}")

    conn.close()
    print("Готово!")


if __name__ == "__main__":
    main()
