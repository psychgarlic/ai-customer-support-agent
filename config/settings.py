"""Настройки приложения, загружаемые из переменных окружения (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get_env(key: str, default: str = "") -> str:
    """Получает переменную окружения по ключу."""
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    """Конфигурация GigaChat и приложения."""

    # Обязательные параметры
    credentials: str = field(default_factory=lambda: _get_env("GIGACHAT_CREDENTIALS"))
    scope: str = field(default_factory=lambda: _get_env("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"))
    model: str = field(default_factory=lambda: _get_env("GIGACHAT_MODEL", "GigaChat"))
    base_url: str = field(default_factory=lambda: _get_env("GIGACHAT_BASE_URL", "https://api.giga.chat/v1"))

    # SSL-настройки
    ca_bundle_file: str = field(default_factory=lambda: _get_env("GIGACHAT_CA_BUNDLE_FILE", ""))
    verify_ssl: bool = field(default_factory=lambda: _get_env("GIGACHAT_VERIFY_SSL_CERTS", "true").lower() == "true")

    # PostgreSQL
    database_url: str = field(default_factory=lambda: _get_env("DATABASE_URL", ""))

    def is_configured(self) -> bool:
        """Проверяет, заполнены ли обязательные параметры."""
        return bool(self.credentials.strip())

    def validate(self) -> None:
        """
        Проверяет обязательные параметры.
        Вызывает ValueError, если что-то отсутствует.
        """
        if not self.is_configured():
            raise ValueError(
                "GigaChat не настроен. Создайте файл .env и укажите GIGACHAT_CREDENTIALS. "
                "См. .env.example и README.md для инструкций."
            )


# Глобальный экземпляр настроек
settings = Settings()
