from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CatalogMediaAsset


class CatalogMediaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, *, user_id: int, asset_id: int) -> CatalogMediaAsset | None:
        return self.db.scalar(
            select(CatalogMediaAsset).where(
                CatalogMediaAsset.user_id == user_id,
                CatalogMediaAsset.id == asset_id,
            )
        )

    def total_bytes(self, *, user_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.coalesce(func.sum(CatalogMediaAsset.byte_size), 0)).where(
                    CatalogMediaAsset.user_id == user_id
                )
            )
            or 0
        )

    def create(self, *, user_id: int, processed) -> CatalogMediaAsset:
        asset = CatalogMediaAsset(
            user_id=user_id,
            content_type="image/webp",
            checksum=processed.checksum,
            byte_size=len(processed.thumb_bytes) + len(processed.detail_bytes),
            thumb_bytes=processed.thumb_bytes,
            thumb_width=processed.thumb_width,
            thumb_height=processed.thumb_height,
            detail_bytes=processed.detail_bytes,
            detail_width=processed.detail_width,
            detail_height=processed.detail_height,
        )
        self.db.add(asset)
        self.db.flush()
        return asset

    def delete(self, asset: CatalogMediaAsset) -> None:
        self.db.delete(asset)
        self.db.flush()
