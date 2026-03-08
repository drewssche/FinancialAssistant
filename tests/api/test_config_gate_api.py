from app.core.config import Settings


def test_production_config_errors_are_empty_for_valid_runtime():
    settings = Settings(
        APP_ENV="production",
        APP_SECRET_KEY="super-secret-key",
        TELEGRAM_BOT_TOKEN="telegram-token",
        ADMIN_TELEGRAM_IDS="100001,100002",
    )

    assert settings.production_config_errors() == []
    settings.validate_runtime_requirements()


def test_production_config_errors_report_missing_critical_values():
    settings = Settings(
        APP_ENV="production",
        APP_SECRET_KEY="change_me",
        TELEGRAM_BOT_TOKEN="change_me",
        ADMIN_TELEGRAM_IDS="",
    )

    errors = settings.production_config_errors()

    assert "APP_SECRET_KEY must be set to a non-default value in production" in errors
    assert "TELEGRAM_BOT_TOKEN must be set to a non-default value in production" in errors
    assert "ADMIN_TELEGRAM_IDS must include at least one admin Telegram ID in production" in errors


def test_production_runtime_validation_raises_with_all_errors():
    settings = Settings(
        APP_ENV="production",
        APP_SECRET_KEY="change_me",
        TELEGRAM_BOT_TOKEN="change_me",
        ADMIN_TELEGRAM_IDS="",
    )

    try:
        settings.validate_runtime_requirements()
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected production config validation to raise")

    assert "Invalid production configuration:" in message
    assert "APP_SECRET_KEY must be set to a non-default value in production" in message
    assert "TELEGRAM_BOT_TOKEN must be set to a non-default value in production" in message
    assert "ADMIN_TELEGRAM_IDS must include at least one admin Telegram ID in production" in message


def test_development_runtime_allows_placeholder_values():
    settings = Settings(
        APP_ENV="development",
        APP_SECRET_KEY="change_me",
        TELEGRAM_BOT_TOKEN="change_me",
        ADMIN_TELEGRAM_IDS="",
    )

    assert settings.production_config_errors() == []
    settings.validate_runtime_requirements()
