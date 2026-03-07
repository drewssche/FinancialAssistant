from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="FinancialAssistant", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_cors_origins: str = Field(default="http://localhost:5173", alias="APP_CORS_ORIGINS")
    app_secret_key: str = Field(default="change_me", alias="APP_SECRET_KEY")
    app_access_token_expire_minutes: int = Field(default=30, alias="APP_ACCESS_TOKEN_EXPIRE_MINUTES")

    postgres_user: str = Field(default="fin_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="fin_pass", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="financial_assistant", alias="POSTGRES_DB")
    postgres_host: str = Field(default="db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    telegram_bot_token: str = Field(default="change_me", alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(default="", alias="TELEGRAM_BOT_USERNAME")
    telegram_auth_max_age_seconds: int = Field(default=3600, alias="TELEGRAM_AUTH_MAX_AGE_SECONDS")
    telegram_bot_poll_timeout_seconds: int = Field(default=25, alias="TELEGRAM_BOT_POLL_TIMEOUT_SECONDS")
    admin_telegram_ids: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def admin_telegram_id_set(self) -> set[str]:
        return {
            item.strip()
            for item in self.admin_telegram_ids.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
