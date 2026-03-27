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
    db_pool_size: int = Field(default=3, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=2, alias="DB_MAX_OVERFLOW")
    db_pool_timeout_seconds: int = Field(default=15, alias="DB_POOL_TIMEOUT_SECONDS")
    db_pool_recycle_seconds: int = Field(default=1800, alias="DB_POOL_RECYCLE_SECONDS")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    telegram_bot_token: str = Field(default="change_me", alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(default="", alias="TELEGRAM_BOT_USERNAME")
    telegram_auth_max_age_seconds: int = Field(default=3600, alias="TELEGRAM_AUTH_MAX_AGE_SECONDS")
    telegram_bot_poll_timeout_seconds: int = Field(default=25, alias="TELEGRAM_BOT_POLL_TIMEOUT_SECONDS")
    telegram_bot_retry_delay_seconds: int = Field(default=2, alias="TELEGRAM_BOT_RETRY_DELAY_SECONDS")
    telegram_plan_reminder_scan_interval_seconds: int = Field(
        default=60,
        alias="TELEGRAM_PLAN_REMINDER_SCAN_INTERVAL_SECONDS",
    )
    currency_rate_provider_url: str = Field(
        default="https://api.nbrb.by/exrates/rates/{code}?parammode=2",
        alias="CURRENCY_RATE_PROVIDER_URL",
    )
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

    @property
    def normalized_telegram_bot_username(self) -> str:
        return self.telegram_bot_username.strip()

    @property
    def browser_telegram_login_enabled(self) -> bool:
        return bool(self.normalized_telegram_bot_username)

    def production_config_errors(self) -> list[str]:
        if not self.is_production:
            return []

        errors: list[str] = []
        if not self.app_secret_key.strip() or self.app_secret_key.strip() == "change_me":
            errors.append("APP_SECRET_KEY must be set to a non-default value in production")
        if not self.telegram_bot_token.strip() or self.telegram_bot_token.strip() == "change_me":
            errors.append("TELEGRAM_BOT_TOKEN must be set to a non-default value in production")
        if not self.admin_telegram_id_set:
            errors.append("ADMIN_TELEGRAM_IDS must include at least one admin Telegram ID in production")
        return errors

    def validate_runtime_requirements(self) -> None:
        errors = self.production_config_errors()
        if not errors:
            return
        joined = "; ".join(errors)
        raise RuntimeError(f"Invalid production configuration: {joined}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
