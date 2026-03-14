from pydantic import BaseModel
from pydantic import Field


class CategoryCreate(BaseModel):
    name: str
    kind: str
    group_id: int | None = None
    icon: str | None = None
    include_in_statistics: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    group_id: int | None = None
    icon: str | None = None
    include_in_statistics: bool | None = None


class CategoryGroupCreate(BaseModel):
    name: str
    kind: str
    accent_color: str | None = None

class CategoryGroupUpdate(BaseModel):
    name: str | None = None
    accent_color: str | None = None


class CategoryGroupOut(BaseModel):
    id: int
    name: str
    kind: str
    accent_color: str | None

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str | None = None
    kind: str
    include_in_statistics: bool = True
    group_id: int | None
    group_name: str | None = None
    group_icon: str | None = None
    group_accent_color: str | None = None
    is_system: bool

    model_config = {"from_attributes": True}


class CategoryListOut(BaseModel):
    items: list[CategoryOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
