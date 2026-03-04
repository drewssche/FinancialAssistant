from __future__ import annotations

import os


def _database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.getenv("DB_USER", "financial")
    password = os.getenv("DB_PASSWORD", "financial")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "financial_assistant")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


class Settings:
    app_name: str = os.getenv("APP_NAME", "Financial Assistant")
    database_url: str = _database_url()


settings = Settings()
