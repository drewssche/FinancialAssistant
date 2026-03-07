from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    display_name: str | None
    avatar_url: str | None
    username: str | None = None
    telegram_id: str | None = None
    status: str
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}
