from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramBrowserAuthRequest(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AuthPublicConfig(BaseModel):
    telegram_bot_username: str | None = None
    browser_login_available: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
