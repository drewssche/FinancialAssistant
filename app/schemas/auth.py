from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    init_data: str


class DevAuthRequest(BaseModel):
    telegram_id: int = 100001
    first_name: str = "Dev"
    username: str = "dev_user"
    avatar_url: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
