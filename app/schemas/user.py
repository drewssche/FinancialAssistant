from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    display_name: str | None
    avatar_url: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
