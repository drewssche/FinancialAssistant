from pydantic import BaseModel, Field, HttpUrl, field_validator
from app.schemas.operation import MeasurementFields


class VariantInput(MeasurementFields):
    name: str = Field(min_length=1, max_length=160)
    codes: list[str] = Field(default_factory=list, max_length=30)
    is_archived: bool = False


class OfferIdentityInput(BaseModel):
    variant_id: int | None = Field(default=None, gt=0)
    retailer_code: str | None = Field(default=None, max_length=160)
    external_name: str | None = Field(default=None, max_length=320)
    product_url: HttpUrl | None = None

    @field_validator('product_url')
    @classmethod
    def public_link(cls, value):
        if value and (value.username or value.password or len(str(value)) > 2048):
            raise ValueError('Ссылка не должна содержать логин/пароль и должна быть короче 2048 символов')
        return value
