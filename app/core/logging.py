import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_api_request_completion(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str,
) -> None:
    logging.getLogger("financial_assistant.api").info(
        "api_request_completed method=%s path=%s status_code=%s duration_ms=%.3f request_id=%s",
        method.upper(),
        path,
        status_code,
        round(max(duration_ms, 0.0), 3),
        request_id,
    )


def log_telegram_bot_event(event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    message = f"telegram_bot_event event={event}"
    if rendered_fields:
        message = f"{message} {rendered_fields}"
    logging.getLogger("financial_assistant_admin_bot").info(message)


def log_auth_event(event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    message = f"auth_event event={event}"
    if rendered_fields:
        message = f"{message} {rendered_fields}"
    logging.getLogger("financial_assistant.auth").info(message)


def log_background_job_event(component: str, event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    message = f"background_job_event component={component} event={event}"
    if rendered_fields:
        message = f"{message} {rendered_fields}"
    logging.getLogger("financial_assistant.jobs").info(message)


def log_admin_notification_event(event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    message = f"admin_notification_event event={event}"
    if rendered_fields:
        message = f"{message} {rendered_fields}"
    logging.getLogger("financial_assistant.admin_notifier").info(message)


def log_telegram_plan_event(event: str, **fields: object) -> None:
    rendered_fields = " ".join(f"{key}={value}" for key, value in sorted(fields.items()))
    message = f"telegram_plan_event event={event}"
    if rendered_fields:
        message = f"{message} {rendered_fields}"
    logging.getLogger("financial_assistant.telegram_plan").info(message)
