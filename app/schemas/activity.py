from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ActivityChangeOut(BaseModel):
    field: str
    label: str
    old: Any | None = None
    new: Any | None = None
    old_display: str | None = None
    new_display: str | None = None


class ActivityEventOut(BaseModel):
    id: int
    user_id: int
    actor_user_id: int | None = None
    entity_type: str
    entity_id: int
    event_type: str
    title: str
    changes: list[ActivityChangeOut] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    metadata_display: list[str] = Field(default_factory=list)
    entity_label: str = ""
    entity_summary: str = ""
    entity_exists: bool = False
    available_actions: list[str] = Field(default_factory=list)
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityEventListOut(BaseModel):
    items: list[ActivityEventOut]
    total: int
