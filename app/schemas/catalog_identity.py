from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator
from app.schemas.operation import MeasurementFields


class VariantInput(MeasurementFields):
    name: str = Field(min_length=1, max_length=160)
    codes: list[str] = Field(default_factory=list, max_length=30)
    is_archived: bool = False


class OfferIdentityInput(BaseModel):
    internal_codes: list[str] | None = Field(default=None, max_length=100)
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


class LookupCodeInput(BaseModel):
    kind: Literal['barcode', 'retailer', 'internal', 'unknown'] = 'unknown'
    code: str = Field(min_length=1, max_length=160)


class ReceiptCodeLookupInput(BaseModel):
    codes: list[LookupCodeInput] = Field(min_length=1, max_length=10)
    shop_name: str = Field(default='', max_length=160)
    source_id: int | None = Field(default=None, gt=0)


class ReceiptSiteLookupInput(ReceiptCodeLookupInput):
    template_id: int | None = Field(default=None, gt=0)
    other_sources: bool = False
    refresh: bool = False
    refresh_selection: str | None = Field(default=None, max_length=16384)


class ReceiptThumbnailInput(BaseModel):
    token: str = Field(min_length=1, max_length=8192)
