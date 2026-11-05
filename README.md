# 🤖 AI Customer Support Agent v2.0

Интеллектуальный агент первой линии поддержки интернет-магазина на основе GigaChat LLM с поддержкой PostgreSQL.

## 📋 Описание

Проект реализует AI-агента, который:
- Анализирует обращения клиентов (категория, приоритет, тональность)
- Использует инструменты (function calling) для поиска в базе знаний
- Проверяет статусы заказов в PostgreSQL
- Генерирует вежливые и полезные ответы
- Определяет необходимость передачи обращения оператору (эскалация)
- Обеспечивает безопасность данных (не запрашивает чувствительную информацию)

## 🛠 Технологии

| Технология | Назначение |
|------------|------------|
| **Python 3.11** | Язык программирования |
| **GigaChat API** | LLM для анализа и генерации текста |
| **Streamlit** | Веб-интерфейс |
| **Pydantic** | Валидация структурированных данных |
| **pytest** | Тестирование |
| **python-dotenv** | Конфигурация |

## 📁 Структура проекта

```
agentai/
│
├── app.py                          # Streamlit-приложение
│
├── agent/                          # AI-агент
│   ├── __init__.py
│   ├── assistant.py                # SupportAssistant — оркестрация LLM
│   ├── prompts.py                  # Системные промпты
│   └── schemas.py                  # Pydantic-модели
│
├── services/                       # Бизнес-логика
│   ├── __init__.py
│   └── support_service.py          # SupportService — центральный сервис
│
├── integrations/                   # Внешние сервисы
│   ├── __init__.py
│   └── gigachat.py                 # GigaChatService — обёртка над API
│
├── tools/                          # Инструменты (function calling)
│   ├── __init__.py
│   └── knowledge_tools.py          # search_support_knowledge, get_support_policy, get_order_status
│
├── repositories/                   # Репозитории (PostgreSQL + InMemory)
│   ├── __init__.py
│   ├── interfaces.py               # ABC-интерфейсы + InMemory-реализации
│   ├── postgres_repo.py            # PostgreSQL-репозитории
│   └── README.md                   # Документация репозиториев
│
├── config/                         # Конфигурация
│   ├── __init__.py
│   └── settings.py                 # Settings — загрузка из .env
│
├── knowledge_base/                 # База знаний (Markdown)
│   ├── faq.md                      # Общие вопросы
│   ├── delivery.md                 # Условия доставки
│   ├── payments.md                 # Способы оплаты
│   └── refunds.md                  # Правила возврата
│
├── tests/                          # Тесты
│   ├── conftest.py
│   ├── test_schemas.py             # Тесты Pydantic-моделей
│   ├── test_tools.py               # Тесты инструментов
│   ├── test_support_service.py     # Тесты бизнес-логики
│   └── test_gigachat_integration.py # Smoke-тест API (опционально)
│
├── .env.example                    # Шаблон конфигурации
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Установка

### 1. Требования

- Python 3.11 или новее
- Доступ к GigaChat API (ключ авторизации)

### 2. Клонирование репозитория

```bash
git clone <repository-url>
cd agentai
```

### 3. Виртуальное окружение

```bash
# Создание окружения
python -m venv .venv

# Активация
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Windows (CMD):
.venv\Scripts\activate.bat

# Установка зависимостей
pip install -r requirements.txt
```

### 4. Настройка PostgreSQL

Проект поддерживает PostgreSQL для хранения клиентов, заказов и обращений.

**1. Установите PostgreSQL** (https://www.postgresql.org/download/windows/)

**2. Создайте базу данных:**

Выполните следующий SQL-скрипт в pgAdmin или через psql:

```sql
-- Создаём базу данных
CREATE DATABASE agentai;

-- Подключаемся к базе данных
\c agentai;

-- Таблица клиентов
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица заказов
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица обращений в поддержку
CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**3. Добавьте DATABASE_URL в `.env`:**

```env
DATABASE_URL=postgresql://postgres:ваш_пароль@localhost:5432/agentai
```

**4. Заполните тестовыми данными:**

Существует два способа создать тестовые данные:

**Способ 1: SQL-скрипт (рекомендуется)**

```powershell
# Запустите SQL-скрипт
psql -U postgres -d agentai -f scripts\test_data.sql
```

**Способ 2: Python-генератор (500 клиентов, 2000 заказов, 500 обращений)**

```powershell
# Убедитесь, что DATABASE_URL настроен в .env
.venv\Scripts\Activate.ps1
python generate_data.py
```

> ⚠️ **Примечание:** `generate_data.py` создаёт большое количество случайных данных. Для быстрого тестирования используйте SQL-скрипт.

> **Примечание:** Для работы с SSL-сертификатами может потребоваться загрузка российского корневого CA-сертификата с [gosuslugi.ru/crt](https://www.gosuslugi.ru/crt).

### 5. Настройка .env (без PostgreSQL)

## 💻 Запуск приложения

```bash
# Активация виртуального окружения (если не активировано)
.venv\Scripts\Activate.ps1

# Запуск Streamlit
streamlit run app.py
```

Приложение откроется в браузере по адресу `http://localhost:8501`.

## 🧪 Тестирование

### Запуск всех тестов

```bash
pytest tests/ -v
```

### Запуск с покрытием

```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Smoke-тесты API (требуют GIGACHAT_CREDENTIALS)

```bash
pytest tests/ -v -m smoke
```

## 📝 Примеры обращений

### 1. Вопрос о доставке

**Ввод:**
> Здравствуйте! Мой заказ №12345 должен был прийти вчера, но я его не получил. Что делать?

**Ожидаемое поведение:**
- Категория: `delivery`
- Приоритет: `high` (просрочка)
- Тональность: `negative`
- Инструменты: `search_support_knowledge("заказ задержка трекинг")`
- Эскалация: возможно, если заказ потерян

### 2. Запрос на возврат

**Ввод:**
> Купил наушники неделю назад, они не работают. Как вернуть деньги?

**Ожидаемое поведение:**
- Категория: `refund`
- Приоритет: `normal`
- Тональность: `neutral`
- Инструменты: `search_support_knowledge("возврат наушники брак")`, `get_support_policy("refund")`
- Эскалация: нет

### 3. Техническая проблема

**Ввод:**
> Не могу войти в личный кабинет, пишет "Неверный пароль", хотя я его не менял.

**Ожидаемое поведение:**
- Категория: `technical_issue`
- Приоритет: `normal`
- Тональность: `negative`
- Инструменты: `get_support_policy("technical_issue")`
- Эскалация: нет

### 4. Критическое обращение (эскалация)

**Ввод:**
> С меня списали деньги дважды за один заказ! Требую вернуть деньги немедленно! Иначе подам в суд!

**Ожидаемое поведение:**
- Категория: `payment`
- Приоритет: `critical` (юридическая угроза)
- Тональность: `negative`
- Эскалация: **да** (требуется оператор)

---

## 🗂️ Настройка базы знаний

База знаний находится в директории `knowledge_base/` и содержит Markdown-файлы:

- `faq.md` — общие вопросы о магазине
- `delivery.md` — условия доставки
- `payments.md` — способы оплаты
- `refunds.md` — правила возврата

> ⚠️ **ВАЖНО:** Текущие данные — это **демо-примеры**. Замените их на реальные условия вашей компании:
> 1. Отредактируйте Markdown-файлы в `knowledge_base/`
> 2. Добавьте новые файлы для ваших категорий
> 3. Удалите ненужные
> 
> AI-агент автоматически использует актуальные данные при запуске.

## 🔧 Инструменты

### search_support_knowledge(query)

Поиск информации в локальной базе знаний (Markdown-файлы).

**Аргументы:**
- `query` (str): Поисковый запрос на русском языке

**Пример:**
```
search_support_knowledge("доставка по Москве сроки")
```

**Результат:**
Фрагменты текста из файлов базы знаний, содержащие искомую информацию.

### get_support_policy(category)

Получение правил обработки обращений определённой категории.

**Аргументы:**
- `category` (str): Категория (`delivery`, `payment`, `refund`, `product`, `technical_issue`, `other`)

**Пример:**
```
get_support_policy("refund")
```

**Результат:**
Текст с правилами обработки возвратов.

### get_order_status(order_id)

Проверка статуса заказа в PostgreSQL базе данных.

**Аргументы:**
- `order_id` (str): Номер заказа

**Пример:**
```
get_order_status("12345")
```

**Результат:**
```
Заказ №12345
Статус: Заказ в пути
Сумма: 15 000,00 руб.
```

> **Примечание:** Инструмент доступен только при подключённой PostgreSQL базе данных.

## 🔒 Безопасность

- API-ключи хранятся только в `.env` и не попадают в Git
- Инструменты выполняются **на стороне сервера** (в Python), не в браузере
- Модель только решает, *какой* инструмент вызвать, но не выполняет произвольный код
- Проверка принадлежности заказа клиенту перед предоставлением информации

## 📊 Архитектура v2.0

```
┌─────────────────────────────────────────────────────────┐
│  Streamlit UI (app.py)                                  │
│  — Ввод обращения, отображение результатов               │
└────────────────────┬────────────────────────────────────┘
                     │ вызывает
┌────────────────────▼────────────────────────────────────┐
│  SupportService (services/support_service.py)           │
│  — Оркестрация: анализ → инструменты → ответ            │
│  — Поддерживает InMemory и PostgreSQL                   │
└────┬──────────────┬──────────────┬──────────────────────┘
     │              │              │
     ▼              ▼              ▼
┌──────────┐ ┌─────────────┐ ┌──────────────┐
│ GigaChat │ │ Knowledge   │ │ PostgreSQL   │
│ Service  │ │ Repository  │ │ Repositories │
│(integrations)│(tools/    │ │(repositories/ │
│          │ │ knowledge_  │ │ postgres_    │
│          │ │ tools.py)   │ │ repo.py)     │
└──────────┘ └─────────────┘ └──────────────┘
```

### Слои ответственности

1. **UI Layer** — Streamlit-интерфейс, отображение результатов
2. **Service Layer** — бизнес-логика, оркестрация
3. **Agent Layer** — работа с LLM, function calling, structured output
4. **Tool Layer** — инструменты (поиск по БЗ, политики, статусы заказов)
5. **Repository Layer** — PostgreSQL для хранения клиентов, заказов и тикетов

## ✅ Возможности версии 2.0

- ✅ Полная интеграция с PostgreSQL (клиенты, заказы, тикеты)
- ✅ Проверка статуса заказов в реальном времени
- ✅ Хранение истории обращений в БД
- ✅ Безопасность: проверка принадлежности заказа клиенту
- ✅ Автоматическая эскалация критических случаев
- ✅ Защита от запросов чувствительных данных (карты, CVV, PIN)
- ✅ База знаний — реальные Markdown-файлы
- ✅ Function calling с GigaChat
- ✅ Structured output через Pydantic
- ✅ Полное покрытие тестами

