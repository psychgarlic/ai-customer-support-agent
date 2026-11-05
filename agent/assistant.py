"""AI-ассистент поддержки.

Оркестрирует взаимодействие между GigaChat, инструментами и схемами.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from gigachat.models import (
    ChatCompletionRequest,
    ChatFunctionSpecification,
    ChatMessage,
    ChatTool,
    ChatFunctionsTool,
)
from pydantic import BaseModel

from agent.prompts import SYSTEM_PROMPT, TOOL_INSTRUCTIONS
from agent.schemas import AgentResponse, ToolUsage
from integrations.gigachat import GigaChatService
from tools.knowledge_tools import get_support_policy, get_order_status, search_support_knowledge

logger = logging.getLogger(__name__)


def _extract_text(content: Any) -> str:
    """Извлекает текстовый ответ из content (может быть списком ChatContentPart или строкой)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(item.text or "")
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content)


# Шаблоны опасных запросов, которые агент НИКОГДА не должен задавать
DANGEROUS_PATTERNS = [
    "номер карты", "cvv", "pin-код", "pin код",
    "реквизиты", "для перевода", "банковские реквизиты",
    "номер банковской", "cvv-код", "секретный код",
    "номер счета", "расчетный счет", "получатель перевода",
    "номер транзакции", "номер операции", "номер платежа",
    "номер карты или", "карты или транзакции", "номер транзакции",
]


def _check_safety(reply: str) -> str:
    """
    Проверяет ответ агента на безопасность.
    Если ответ содержит запрос чувствительных данных — заменяет на безопасный.
    """
    reply_lower = reply.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in reply_lower:
            logger.warning("Безопасность: ответ содержит запрос чувствительных данных, заменяем")
            return (
                "Спасибо за обращение. Мы передали ваш вопрос специалисту. "
                "Мы никогда не запрашиваем номера карт, CVV-коды или банковские реквизиты. "
                "Оператор свяжется с вами в ближайшее время."
            )

    # Дополнительная проверка: если ответ запрашивает номера транзакций, дат списаний и т.д.
    if any(phrase in reply_lower for phrase in [
        "укажите номер", "сообщите номер", "номер транзакции", "номер операции",
        "дата списания", "дата платежа", "реквизиты перевода",
    ]):
        logger.warning("Безопасность: ответ содержит запрос дополнительных данных, заменяем")
        return (
            "Спасибо за обращение. Мы передали ваш вопрос специалисту. "
            "Мы никогда не запрашиваем номера карт, CVV-коды или банковские реквизиты. "
            "Оператор свяжется с вами в ближайшее время."
        )

    return reply


class SupportAssistant:
    """
    AI-ассистент первой линии поддержки.

    Работает по схеме:
    1. Определяет категорию обращения
    2. Вызывает инструменты (база знаний, политики)
    3. Генерирует ответ с учётом контекста
    4. Решает, нужен ли оператор
    """

    def __init__(self, service: GigaChatService) -> None:
        self._service = service

    def process(self, customer_message: str) -> AgentResponse:
        """
        Обрабатывает обращение клиента.

        Args:
            customer_message: Текст обращения.

        Returns:
            Полный ответ агента (AgentResponse).

        Raises:
            ValueError: Если сообщение пустое.
            RuntimeError: Если ошибка API.
        """
        if not customer_message or not customer_message.strip():
            raise ValueError("Сообщение клиента не может быть пустым")

        # Шаг 1: Определяем инструменты, которые нужно предложить модели
        tools = self._build_tools()

        # Шаг 2: Анализируем обращение с вызовом инструментов
        analysis_result = self._analyze_with_tools(customer_message, tools)

        # Шаг 3: Формируем итоговый ответ
        return self._build_response(customer_message, analysis_result)

    def _build_tools(self) -> List[ChatTool]:
        """Создаёт список инструментов для function calling."""
        search_func = ChatFunctionSpecification(
            name="search_support_knowledge",
            description=(
                "Поиск информации в локальной базе знаний интернет-магазина. "
                "Используйте для поиска условий доставки, возврата, оплаты и т.д."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Краткий поисковый запрос на русском языке (3-5 слов)",
                    },
                },
                "required": ["query"],
            },
        )

        policy_func = ChatFunctionSpecification(
            name="get_support_policy",
            description=(
                "Получение правил обработки определённой категории обращений. "
                "Используйте, чтобы узнать, как правильно обрабатывать обращение."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "delivery", "payment", "refund",
                            "product", "technical_issue", "other",
                        ],
                        "description": "Категория обращения",
                    },
                },
                "required": ["category"],
            },
        )

        order_func = ChatFunctionSpecification(
            name="get_order_status",
            description=(
                "Проверка статуса заказа в базе данных. "
                "Используйте, когда клиент спрашивает о статусе своего заказа. "
                "Введите номер заказа."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Номер заказа (число)",
                    },
                },
                "required": ["order_id"],
            },
        )

        return [
            ChatTool(functions=ChatFunctionsTool(specifications=[search_func])),
            ChatTool(functions=ChatFunctionsTool(specifications=[policy_func])),
            ChatTool(functions=ChatFunctionsTool(specifications=[order_func])),
        ]

    def _analyze_with_tools(
        self,
        message: str,
        tools: List[ChatTool],
    ) -> Dict[str, Any]:
        """
        Анализирует обращение, вызывая инструменты.

        Использует structured output (Pydantic) для парсинга ответа модели.
        """
        assert self._service is not None

        # Сначала проверяем на критические случаи
        is_critical = self._is_critical_case(message)
        if is_critical:
            logger.info("Обнаружен критический случай, эскалируем")
            from agent.schemas import TicketAnalysis
            return {
                "analysis": TicketAnalysis(
                    category=self._detect_category(message.lower()) or "other",
                    priority="critical",
                    sentiment="negative",
                    reason="Критический случай — требуется эскалация.",
                    requires_human=True,
                    missing_information=[],
                ),
                "tools_used": [],
            }

        # Fallback: если инструменты не вызваны, определяем по ключевым словам
        # Проверяем на критичность до отправки к LLM
        category = self._detect_category(message.lower())
        if category == "payment" and any(kw in message.lower() for kw in ["списали дважды", "двойное", "дважды"]):
            logger.info("Критический случай: двойное списание, эскалируем")
            from agent.schemas import TicketAnalysis
            return {
                "analysis": TicketAnalysis(
                    category="payment",
                    priority="critical",
                    sentiment="negative",
                    reason="Двойное списание — требуется эскалация.",
                    requires_human=True,
                    missing_information=[],
                ),
                "tools_used": [],
            }

        # Формируем контекст с инструкциями по инструментам
        system_content = SYSTEM_PROMPT + "\n\n" + TOOL_INSTRUCTIONS

        messages = [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="user", content=message),
        ]

        # Отправляем запрос с инструментами
        response = self._service.chat.create(
            messages=messages,
            tools=tools,
        )

        # Собираем результаты вызова инструментов
        tool_usages: List[ToolUsage] = []
        context_parts: List[str] = [message]

        # Проверяем, были ли вызваны инструменты
        has_function_calls = False
        if hasattr(response, "messages") and response.messages:
            for msg in response.messages:
                if hasattr(msg, "function_call") and msg.function_call:
                    has_function_calls = True
                    fc = msg.function_call
                    tool_name = fc.name
                    tool_args = fc.arguments or {}

                    # Выполняем инструмент на стороне сервера
                    result = self._execute_tool(tool_name, tool_args)

                    tool_usages.append(ToolUsage(
                        name=tool_name,
                        query=str(tool_args),
                        result_summary=result[:500],
                    ))
                    context_parts.append(f"Инструмент {tool_name} вернул: {result}")

        # Fallback: если инструменты не вызваны, определяем по ключевым словам
        if not has_function_calls:
            logger.info("GigaChat не вызвал инструменты, используем fallback")
            tool_usages = self._fallback_tool_detection(message, context_parts)
            if tool_usages:
                for tu in tool_usages:
                    context_parts.append(f"Инструмент {tu.name} вернул: {tu.result_summary}")
                    # Добавляем статус заказа в контекст явно
                    if tu.name == "get_order_status":
                        context_parts.append(f"СТАТУС ЗАКАЗА: {tu.result_summary}")

        # Формируем финальный запрос для структурированного анализа
        full_context = "\n".join(context_parts)

        # Парсим через Pydantic
        from agent.schemas import TicketAnalysis
        try:
            analysis, parsed = self._service.chat.parse(
                f"На основе контекста проанализируй обращение клиента:\n\n{full_context}",
                response_format=TicketAnalysis,
                strict=True,
            )
            return {
                "analysis": parsed,
                "tools_used": tool_usages,
            }
        except Exception as e:
            logger.warning("Structured parse failed, falling back: %s", e)
            return self._fallback_analysis(full_context, tool_usages)

    def _fallback_tool_detection(
        self,
        message: str,
        context_parts: List[str],
    ) -> List[ToolUsage]:
        """
        Fallback-определение инструментов по ключевым словам.
        Используется, если GigaChat не вызвал инструменты автоматически.
        """
        tool_usages: List[ToolUsage] = []
        message_lower = message.lower()

        # Проверяем, упоминает ли клиент номер заказа
        if any(keyword in message_lower for keyword in ["заказ", "номер", "№"]):
            order_id = self._extract_order_id(message)
            if order_id:
                result = get_order_status(order_id)
                tool_usages.append(ToolUsage(
                    name="get_order_status",
                    query=f"order_id={order_id}",
                    result_summary=result[:500],
                ))
                # Добавляем статус заказа в контекст явно
                tool_usages[-1].result_summary = result[:500]

        # Определяем категорию обращения (обязательно для всех обращений)
        category = self._detect_category(message_lower)
        if category:
            result = get_support_policy(category)
            tool_usages.append(ToolUsage(
                name="get_support_policy",
                query=f"category={category}",
                result_summary=result[:500],
            ))

        # Для payment и refund всегда ищем в базе знаний
        if category in ["payment", "refund"]:
            search_keywords = self._detect_search_keywords(message_lower)
            if search_keywords:
                result = search_support_knowledge(search_keywords)
                tool_usages.append(ToolUsage(
                    name="search_support_knowledge",
                    query=search_keywords,
                    result_summary=result[:500],
                ))

        return tool_usages

    def _extract_order_id(self, message: str) -> Optional[str]:
        """Извлекает номер заказа из текста."""
        patterns = [
            r"№\s*(\d+)",
            r"заказ\s+([\d]+)",
            r"order\s+([\d]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _detect_category(self, message_lower: str) -> Optional[str]:
        """Определяет категорию обращения по ключевым словам."""
        # Сначала проверяем критические случаи
        if any(kw in message_lower for kw in ["списали дважды", "списали 2", "двойное списание"]):
            return "payment"

        # Затем проверяем остальные категории
        categories = {
            "delivery": ["доставк", "привез", "курьер", "трек", "отправ"],
            "payment": ["оплат", "карт", "списал", "платеж", "деньг", "банк"],
            "refund": ["верн", "возврат", "бракован", "не работ"],
            "product": ["товар", "характеристик", "наличие", "аналог"],
            "technical_issue": ["войти", "пароль", "ошибк", "сайт", "приложен"],
        }
        for category, keywords in categories.items():
            if any(kw in message_lower for kw in keywords):
                return category
        return None

    def _detect_search_keywords(self, message_lower: str) -> Optional[str]:
        """Извлекает ключевые слова для поиска в базе знаний."""
        stop_words = {
            "здравствуйте", "привет", "помогите", "подскажите", "где", "как",
            "почему", "что", "когда", "который", "уже", "мне", "мой", "мои",
            "меня", "требую", "хочу", "надо", "нужно", "спасибо", "благодарю",
            "списали", "дважды", "два", "двойн", "немедленно", "требую",
        }
        # Убираем пунктуацию
        clean = re.sub(r"[^\w\s]", "", message_lower)
        words = clean.split()
        meaningful = [w for w in words if w not in stop_words and len(w) > 3]
        if meaningful:
            return " ".join(meaningful[:4])
        return None

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Безопасно выполняет инструмент по названию."""
        safe_tools: Dict[str, Any] = {
            "search_support_knowledge": search_support_knowledge,
            "get_support_policy": get_support_policy,
            "get_order_status": get_order_status,
        }

        tool_func = safe_tools.get(name)
        if not tool_func:
            return f"Ошибка: неизвестный инструмент «{name}»."

        try:
            return tool_func(**args)
        except Exception as e:
            logger.error("Ошибка выполнения инструмента %s: %s", name, e)
            return f"Ошибка выполнения инструмента {name}: {e}"

    def _fallback_analysis(
        self,
        context: str,
        tools_used: List[ToolUsage],
    ) -> Dict[str, Any]:
        """
        Fallback-анализ, если structured output не сработал.
        Генерирует ответ через обычный chat.
        """
        from agent.schemas import TicketAnalysis

        # Проверяем на критические случаи
        is_critical = self._is_critical_case(context)

        fallback_analysis = TicketAnalysis(
            category="other",
            priority="critical" if is_critical else "normal",
            sentiment="negative",
            reason="Не удалось выполнить структурированный анализ. Требуется ручная проверка." +
                   (" Критический случай — требуется эскалация." if is_critical else ""),
            requires_human=is_critical,
            missing_information=[],
        )

        # Для критических случаев — безопасный ответ без запросов
        if is_critical:
            fallback_analysis.reply = (
                "Спасибо за обращение. Мы передали ваш вопрос специалисту. "
                "Мы никогда не запрашиваем номера карт, CVV-коды или банковские реквизиты. "
                "Оператор свяжется с вами в ближайшее время."
            )
            return {
                "analysis": fallback_analysis,
                "tools_used": tools_used,
            }

        # Генерируем ответ
        reply = self._service.chat.create(
            messages=[
                ChatMessage(
                    role="system",
                    content="Ты агент поддержки. Сгенерируй вежливый ответ клиенту. "
                            "НИКОГДА не запрашивай номера карт, CVV-коды, PIN-коды или банковские реквизиты. "
                            "НЕ галлюцинируй — отвечай только на основе предоставленного контекста.",
                ),
                ChatMessage(role="user", content=context),
            ],
        )

        reply_text = ""
        if hasattr(reply, "messages") and reply.messages:
            reply_text = _extract_text(reply.messages[0].content)

        fallback_analysis.reply = reply_text

        return {
            "analysis": fallback_analysis,
            "tools_used": tools_used,
        }

    def _is_critical_case(self, context: str) -> bool:
        """Проверяет, является ли обращение критическим."""
        context_lower = context.lower()

        # Критические ключевые слова
        critical_keywords = [
            "суд", "подам в суд", "жалоба", "прокуратура", "рпн",
            "мошенничество", "полиция", "угрозы",
            "требую немедленно", "немедленно верните", "возврат денег немедленно",
            "списали дважды", "двойное списание", "кража",
            "третий раз", "уже писал", "уже обращался", "ничего не делаете",
            "требую соединения", "соединения с менеджером", "связаться с оператором",
        ]

        for keyword in critical_keywords:
            if keyword in context_lower:
                return True

        return False

    def _build_response(
        self,
        message: str,
        analysis_result: Dict[str, Any],
    ) -> AgentResponse:
        """Формирует итоговый ответ агента."""
        from agent.schemas import AgentResponse, TicketAnalysis

        analysis = analysis_result.get("analysis")
        if isinstance(analysis, BaseModel):
            ticket_analysis: TicketAnalysis = analysis
        elif isinstance(analysis, dict):
            ticket_analysis = TicketAnalysis(**analysis)
        else:
            ticket_analysis = TicketAnalysis(
                category="other",
                priority="normal",
                sentiment="neutral",
                reason="Анализ выполнен в fallback-режиме.",
            )

        tools_used: List[ToolUsage] = analysis_result.get("tools_used", [])

        # Генерируем ответ клиенту
        reply = self._generate_reply(message, ticket_analysis, tools_used)

        # Безопасность: проверяем ответ
        reply = _check_safety(reply)

        # Определяем заметку об эскалации
        escalate_note = ""
        if ticket_analysis.requires_human:
            escalate_note = (
                f"Требуется передача оператору. Причина: {ticket_analysis.reason}"
            )

        return AgentResponse(
            analysis=ticket_analysis,
            reply=reply,
            tools_used=tools_used,
            escalate_note=escalate_note,
        )

    def _generate_reply(
        self,
        message: str,
        analysis: TicketAnalysis,
        tools_used: List[ToolUsage],
    ) -> str:
        """Генерирует ответ клиенту с учётом анализа и инструментов."""
        # Извлекаем статус заказа из результатов инструментов
        order_status_info = ""
        for tu in tools_used:
            if tu.name == "get_order_status":
                order_status_info = tu.result_summary
                break

        # Формируем контекст для генерации ответа
        context_lines = [
            f"Категория: {analysis.category.value}",
            f"Приоритет: {analysis.priority.value}",
            f"Тональность: {analysis.sentiment.value}",
        ]

        if order_status_info:
            status_ru = ""
            if "Статус:" in order_status_info:
                status_ru = order_status_info.split("Статус:")[1].split("\n")[0].strip()

            # Маппим русский статус на английский
            if "обрабатыв" in status_ru.lower():
                order_status_en = "processing"
            elif "в пути" in status_ru.lower():
                order_status_en = "shipped"
            elif "доставлен" in status_ru.lower():
                order_status_en = "delivered"
            elif "отменён" in status_ru.lower():
                order_status_en = "cancelled"
            else:
                order_status_en = "unknown"

            context_lines.append(f"СТАТУС ЗАКАЗА (RU): {status_ru}")
            context_lines.append(f"СТАТУС ЗАКАЗА (EN): {order_status_en}")

            if order_status_en == "processing":
                context_lines.append(
                    "⚠️⚠️⚠️ КРИТИЧЕСКАЯ ИНФОРМАЦИЯ: Заказ ещё НЕ ДОСТАВЛЕН (статус: processing). "
                    "Клиент говорит про дефект, но товар ещё не пришёл! "
                    "ЗАПРЕЩЕНО говорить про возврат, дефект, чек, упаковку! "
                    "ЕДИНСТВЕННО правильный ответ: "
                    "\"Ваш заказ №4 ещё обрабатывается и не был доставлен. "
                    "Пожалуйста, подождите подтверждения доставки.\" "
                    "⚠️⚠️⚠️"
                )
            elif order_status_en == "shipped":
                context_lines.append(
                    "Заказ в пути. Клиент может жаловаться на задержку. "
                    "Предложи проверить трек-номер."
                )
            elif order_status_en == "delivered":
                context_lines.append(
                    "Заказ уже доставлен. Клиент может жаловаться на дефект или просить возврат."
                )

        if tools_used:
            context_lines.append("\nРезультаты инструментов:")
            for tu in tools_used:
                context_lines.append(f"- {tu.name}: {tu.result_summary}")

        if analysis.missing_information:
            context_lines.append("\nНужно уточнить:")
            for info in analysis.missing_information:
                context_lines.append(f"- {info}")

        context = "\n".join(context_lines)

        reply_prompt = (
            f"Сформируй вежливый ответ клиенту на основе анализа.\n\n"
            f"Контекст анализа:\n{context}\n\n"
            f"Сообщение клиента:\n{message}\n\n"
            f"Требования:\n"
            f"- Отвечай на языке клиента\n"
            f"- Будь конкретным и полезным\n"
            f"- НЕ галлюцинируй — отвечай только на основе предоставленного контекста\n"
            f"- Если статус заказа 'processing' — ЕДИНСТВЕННЫЙ ответ: 'Ваш заказ ещё обрабатывается и не был доставлен. Пожалуйста, подождите.'\n"
            f"- НЕ упоминай возврат, дефект, чек, упаковку если статус 'processing'\n"
            f"- Если нужно уточнить — задай вопросы\n"
            f"- Если нужен оператор — скажи об этом\n"
            f"- НИКОГДА не запрашивай номера карт, CVV-коды, PIN-коды, банковские реквизиты\n"
        )

        try:
            response = self._service.chat.create(
                messages=[
                    ChatMessage(role="system", content=SYSTEM_PROMPT),
                    ChatMessage(role="user", content=reply_prompt),
                ],
            )
            if hasattr(response, "messages") and response.messages:
                return _extract_text(response.messages[0].content) or "Ответ сгенерирован, но текст пуст."
            return str(response)
        except Exception as e:
            logger.error("Ошибка генерации ответа: %s", e)
            return (
                "Спасибо за обращение. Мы рассмотрим ваш вопрос и ответим в ближайшее время. "
                "Приносим извинения за временные технические трудности."
            )