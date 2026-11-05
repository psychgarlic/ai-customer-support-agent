"""Конфигурация pytest."""

from __future__ import annotations

from typing import Any


def pytest_configure(config: Any) -> None:
    """Регистрирует кастомные маркеры pytest."""
    config.addinivalue_line("markers", "smoke:mark test as smoke test (requires API key)")
