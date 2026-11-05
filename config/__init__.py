"""Конфигурация приложения. Загружает параметры из .env файла."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

from config.settings import *  # noqa: F401, F403
