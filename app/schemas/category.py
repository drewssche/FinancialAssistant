from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    kind: str


class CategoryOut(BaseModel):
    id: int
    name: str
    kind: str
    is_system: bool

    model_config = {"from_attributes": True}
