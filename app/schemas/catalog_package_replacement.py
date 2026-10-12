from datetime import date
from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.catalog_identity import VariantInput


class PackageReplacementInput(BaseModel):
    old_variant_id: int = Field(gt=0)
    new_variant_id: int = Field(gt=0)
    effective_date: date
    note: str | None = Field(default=None, max_length=300)
    confirmed: Literal[True]
    expected_old: VariantInput
    expected_new: VariantInput
