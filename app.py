"""Streamlit-интерфейс AI Customer Support Agent.

Пользователь вводит обращение → сервис обрабатывает → отображаются результаты.
"""

from __future__ import annotations

import logging
from datetime import datetime

import streamlit as st

from agent.schemas import AgentResponse
from config import settings
from services.support_service import SupportService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_service() -> SupportService | None:
    """Инициализирует SupportService. Возвращает None, если API не настроен."""
    try:
        # Если есть DATABASE_URL — используем PostgreSQL
        if settings.database_url:
            logger.info("Используем PostgreSQL: %s", settings.database_url)
            return SupportService.create_with_postgres(settings.database_url)
        
        # Иначе — in-memory (для разработки без БД)
        return SupportService.create()
    except ValueError as e:
        st.error(f"⚠️ GigaChat не настроен: {e}")
        st.info(
            "Создайте файл `.env` в корне проекта и укажите `GIGACHAT_CREDENTIALS`. "
            "См. `.env.example` и `README.md`."
        )
        return None
    except Exception as e:
        st.error(f"⚠️ Ошибка инициализации сервиса: {e}")
        logger.error("Ошибка инициализации: %s", e, exc_info=True)
        return None


def display_analysis(analysis: dict) -> None:
    """Отображает блок анализа обращения."""
    st.subheader("📊 Анализ обращения")

    col1, col2, col3 = st.columns(3)

    with col1:
        category = analysis.get("category", "unknown")
        category_labels = {
            "delivery": "🚚 Доставка",
            "payment": "💳 Оплата",
            "refund": "💰 Возврат",
            "product": "📦 Товар",
            "technical_issue": "🔧 Тех. проблема",
            "other": "❓ Другое",
        }
        st.metric("Категория", category_labels.get(category, category))

    with col2:
        priority = analysis.get("priority", "normal")
        priority_emojis = {
            "low": "🟢 Низкий",
            "normal": "🔵 Обычный",
            "high": "🟠 Высокий",
            "critical": "🔴 Критический",
        }
        st.metric("Приоритет", priority_emojis.get(priority, priority))

    with col3:
        sentiment = analysis.get("sentiment", "neutral")
        sentiment_emojis = {
            "positive": "😊 Позитив",
            "neutral": "😐 Нейтрально",
            "negative": "😠 Негатив",
        }
        st.metric("Тональность", sentiment_emojis.get(sentiment, sentiment))

    # Обоснование
    if "reason" in analysis:
        st.info(f"**Обоснование:** {analysis['reason']}")

    # Недостающая информация
    missing = analysis.get("missing_information", [])
    if missing:
        st.warning("**Нужно уточнить:**\n" + "\n".join(f"• {item}" for item in missing))


def display_tools(tools_used: list[dict]) -> None:
    """Отображает блок использованных инструментов."""
    if not tools_used:
        return

    st.subheader("🔧 Использованные инструменты")
    for tool in tools_used:
        with st.expander(f"📌 {tool.get('name', 'unknown')}"):
            st.write(f"**Запрос:** {tool.get('query', 'N/A')}")
            st.write(f"**Результат:** {tool.get('result_summary', 'N/A')}")


def display_reply(reply: str) -> None:
    """Отображает блок готового ответа."""
    st.subheader("💬 Ответ клиенту")
    st.info(reply)


def display_escalation(escalate_note: str) -> None:
    """Отображает блок эскалации."""
    if not escalate_note:
        return

    st.error(f"⚠️ **Требуется передача оператору:**\n{escalate_note}")


def main() -> None:
    """Основная функция Streamlit-приложения."""
    st.set_page_config(
        page_title="AI Customer Support Agent",
        page_icon="🤖",
        layout="wide",
    )

    st.title("🤖 AI Customer Support Agent")
    st.markdown(
        "Интеллектуальный агент первой линии поддержки интернет-магазина. "
        "Введите обращение клиента, и агент проанализирует его, определит категорию, "
        "приоритет и сформирует ответ."
    )

    # Инициализация сервиса
    if "service" not in st.session_state:
        st.session_state.service = init_service()

    service = st.session_state.service

    # Боковая панель
    with st.sidebar:
        st.header("ℹ️ О проекте")
        st.markdown(
            "**AI Customer Support Agent** — интеллектуальный агент поддержки, "
            "использующий GigaChat LLM для анализа обращений и генерации ответов."
        )
        st.markdown("**Технологии:** Python, GigaChat API, Streamlit, Pydantic")

        if service is None:
            st.warning("⚠️ API не настроен. См. README.md для инструкций.")
        else:
            st.success("✅ GigaChat подключён")

    # Поле ввода обращения
    st.header("📝 Введите обращение клиента")
    customer_message = st.text_area(
        "Текст обращения:",
        height=150,
        placeholder=(
            "Пример: 'Здравствуйте! Мой заказ №12345 должен был прийти вчера, "
            "но я его не получил. Что делать?'"
        ),
    )

    # Кнопка обработки
    if st.button("🚀 Обработать обращение", type="primary", disabled=service is None):
        if not customer_message.strip():
            st.warning("⚠️ Пожалуйста, введите текст обращения.")
        else:
            with st.spinner("⏳ Агент обрабатывает обращение..."):
                try:
                    response: AgentResponse = service.process_ticket(customer_message)

                    # Отображаем результаты
                    display_analysis(response.analysis.model_dump())
                    display_tools([t.model_dump() for t in response.tools_used])
                    display_reply(response.reply)
                    display_escalation(response.escalate_note)

                except ValueError as e:
                    st.error(f"⚠️ Ошибка ввода: {e}")
                except RuntimeError as e:
                    st.error(f"⚠️ Ошибка обработки: {e}")
                except Exception as e:
                    st.error(f"⚠️ Неожиданная ошибка: {e}")
                    logger.error("Неожиданная ошибка: %s", e, exc_info=True)

    # Примеры обращений
    with st.expander("💡 Примеры обращений"):
        st.markdown(
            """
            **1. Вопрос о доставке:**
            > Здравствуйте! Мой заказ №12345 должен был прийти вчера, но я его не получил. Что делать?

            **2. Запрос на возврат:**
            > Купил наушники неделю назад, они не работают. Как вернуть деньги?

            **3. Техническая проблема:**
            > Не могу войти в личный кабинет, пишет "Неверный пароль", хотя я его не менял.

            **4. Критическое обращение (эскалация):**
            > С меня списали деньги дважды за один заказ! Требую вернуть деньги немедленно!
            """
        )


if __name__ == "__main__":
    main()
