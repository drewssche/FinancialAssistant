from pydantic import BaseModel, Field


class PreferencesPayload(BaseModel):
    preferences_version: int = 1
    data: dict = Field(default_factory=dict)


class PreferencesOut(BaseModel):
    preferences_version: int
    data: dict

    model_config = {"from_attributes": True}
