"""Сервис для работы с GigaChat API.

Инициализирует клиент GigaChat с настройками из .env и предоставляет
единый интерфейс для чат-запросов.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple, Type, TypeVar

from gigachat import GigaChat
from gigachat.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatTool,
)
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GigaChatChatAPI:
    """
    Вложенный API для чат-запросов.
    Позволяет вызывать service.chat.create() и service.chat.parse().
    """

    def __init__(self, service: "GigaChatService") -> None:
        self._service = service

    def create(
        self,
        messages: List[Any],
        tools: Optional[List[ChatTool]] = None,
        **kwargs: Any,
    ) -> ChatCompletionResponse:
        """
        Отправляет запрос к GigaChat API.

        Args:
            messages: Список ChatMessage.
            tools: Список инструментов для function calling.
            **kwargs: Дополнительные параметры.

        Returns:
            Ответ от GigaChat API.
        """
        # Преобразуем все сообщения в ChatMessage
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                formatted_messages.append(msg)
            elif isinstance(msg, dict):
                formatted_messages.append(ChatMessage(**msg))
            else:
                formatted_messages.append(
                    ChatMessage(
                        role=msg.role,
                        content=msg.content,
                        function_call=msg.function_call if hasattr(msg, "function_call") else None,
                    )
                )

        # Формируем ChatCompletionRequest для SDK
        request_data = ChatCompletionRequest(
            messages=formatted_messages,
            tools=tools,
            **kwargs,
        )
        return self._service.client.chat.create(request_data)

    def parse(
        self,
        message: str,
        response_format: Type[T],
        **kwargs: Any,
    ) -> Tuple[ChatCompletionResponse, T]:
        """Отправляет запрос и парсит ответ в Pydantic-модель."""
        return self._service.client.chat_parse(
            message,
            response_format=response_format,
            **kwargs,
        )


class GigaChatService:
    """
    Обёртка над GigaChat SDK.

    Предоставляет:
    - Инициализацию клиента с настройками из .env
    - Метод chat.create() для обычных запросов
    - Метод chat.parse() для структурированного вывода (Pydantic)
    - Обработку SSL-сертификатов
    """

    def __init__(self) -> None:
        self._client: Optional[GigaChat] = None
        self.chat = GigaChatChatAPI(self)  # Вложенный API для чат-запросов

    @property
    def client(self) -> GigaChat:
        """Ленивая инициализация клиента GigaChat."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> GigaChat:
        """Создаёт и настраивает клиент GigaChat."""
        kwargs: dict[str, Any] = {
            "credentials": settings.credentials,
            "scope": settings.scope,
            "model": settings.model if settings.model else None,
        }

        # Настраиваем базовый URL
        if settings.base_url:
            kwargs["base_url"] = settings.base_url

        # Настраиваем SSL
        if settings.ca_bundle_file:
            ca_path = Path(settings.ca_bundle_file)
            if ca_path.exists():
                kwargs["ca_bundle_file"] = str(ca_path)
            else:
                logger.warning(
                    "CA-файл не найден: %s. SSL-проверка может не работать.",
                    settings.ca_bundle_file,
                )

        if not settings.verify_ssl:
            kwargs["verify_ssl_certs"] = False

        logger.info("Инициализация GigaChat: model=%s, url=%s", settings.model, settings.base_url)
        return GigaChat(**kwargs)

    def close(self) -> None:
        """Закрывает соединение с GigaChat."""
        if self._client:
            self._client.close()
            self._client = None
