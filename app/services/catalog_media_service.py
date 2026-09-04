from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select, update

from app.core.cache import (
    invalidate_dashboard_analytics_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    invalidate_plans_cache,
)
from app.db.models import CatalogProduct, ItemBrand, ItemSource, OperationItemTemplate
from app.repositories.catalog_media_repo import CatalogMediaRepository
from app.services.activity_service import ActivityService


class CatalogMediaValidationError(ValueError):
    pass


class CatalogMediaTooLargeError(CatalogMediaValidationError):
    pass


@dataclass(frozen=True)
class ProcessedCatalogImage:
    thumb_bytes: bytes
    thumb_width: int
    thumb_height: int
    detail_bytes: bytes
    detail_width: int
    detail_height: int
    checksum: str


class CatalogMediaService:
    MAX_UPLOAD_BYTES = 8 * 1024 * 1024
    MAX_PIXELS = 20_000_000
    MAX_USER_BYTES = 100 * 1024 * 1024
    THUMB_SIZE = (160, 160)
    DETAIL_SIZE = (1024, 1024)
    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
    ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
    FORMAT_CONTENT_TYPES = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }
    OWNER_MODELS = {
        "brand": ItemBrand,
        "product": CatalogProduct,
        "source": ItemSource,
        "template": OperationItemTemplate,
    }
    OWNER_ENTITY_TYPES = {
        "brand": "item_brand",
        "product": "catalog_product",
        "source": "item_source",
        "template": "item_template",
    }

    def __init__(self, db):
        self.db = db
        self.repo = CatalogMediaRepository(db)
        self.activity = ActivityService(db)

    def get_owner(
        self,
        *,
        user_id: int,
        owner_kind: str,
        owner_id: int,
        include_archived: bool = False,
    ):
        model = self.OWNER_MODELS[owner_kind]
        conditions = [model.user_id == user_id, model.id == owner_id]
        if not include_archived:
            conditions.append(model.is_archived.is_(False))
        return self.db.scalar(select(model).where(*conditions))

    def _resolve_owner(
        self,
        *,
        user_id: int,
        owner_kind: str,
        owner_id: int,
        include_archived: bool = False,
    ) -> tuple[str, object | None]:
        owner = self.get_owner(
            user_id=user_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            include_archived=include_archived,
        )
        if (
            owner_kind == "template"
            and owner is not None
            and owner.product_id is not None
        ):
            product = self.get_owner(
                user_id=user_id,
                owner_kind="product",
                owner_id=int(owner.product_id),
                include_archived=include_archived,
            )
            if product is not None:
                return "product", product
        return owner_kind, owner

    def upload(
        self,
        *,
        user_id: int,
        owner_kind: str,
        owner_id: int,
        content_type: str | None,
        raw: bytes,
    ):
        resolved_kind, owner = self._resolve_owner(
            user_id=user_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
        )
        if owner is None:
            raise LookupError("Catalog entity not found")
        processed = self.process_image(raw=raw, content_type=content_type)
        old_asset = (
            self.repo.get(user_id=user_id, asset_id=int(owner.image_id))
            if owner.image_id
            else None
        )
        old_size = int(old_asset.byte_size or 0) if old_asset is not None else 0
        reclaimable_old_size = (
            old_size
            if old_asset is not None
            and not self._asset_is_externally_referenced(
                asset_id=int(old_asset.id),
                owner_kind=resolved_kind,
                owner_id=int(owner.id),
            )
            else 0
        )
        next_total = self.repo.total_bytes(user_id=user_id) - reclaimable_old_size
        next_total += len(processed.thumb_bytes) + len(processed.detail_bytes)
        if next_total > self.MAX_USER_BYTES:
            raise CatalogMediaTooLargeError("Catalog image storage limit exceeded")

        before_id = owner.image_id
        asset = self.repo.create(user_id=user_id, processed=processed)
        owner.image_id = int(asset.id)
        self.db.flush()
        if resolved_kind == "product":
            self._sync_product_offer_images(
                user_id=user_id,
                product_id=int(owner.id),
                image_id=int(asset.id),
            )
        if old_asset is not None and not self._asset_is_referenced(
            asset_id=int(old_asset.id)
        ):
            self.repo.delete(old_asset)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type=self.OWNER_ENTITY_TYPES[resolved_kind],
            entity_id=int(owner.id),
            event_type="image_updated",
            title="Изображение обновлено",
            metadata={"previous_image_id": before_id, "image_id": int(asset.id)},
        )
        self.db.commit()
        self._invalidate(user_id)
        return owner

    def delete(self, *, user_id: int, owner_kind: str, owner_id: int):
        resolved_kind, owner = self._resolve_owner(
            user_id=user_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
        )
        if owner is None:
            raise LookupError("Catalog entity not found")
        asset = (
            self.repo.get(user_id=user_id, asset_id=int(owner.image_id))
            if owner.image_id
            else None
        )
        previous_id = owner.image_id
        owner.image_id = None
        self.db.flush()
        if resolved_kind == "product":
            self._sync_product_offer_images(
                user_id=user_id,
                product_id=int(owner.id),
                image_id=None,
            )
        if asset is not None and not self._asset_is_referenced(asset_id=int(asset.id)):
            self.repo.delete(asset)
        if previous_id is not None:
            self.activity.record(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type=self.OWNER_ENTITY_TYPES[resolved_kind],
                entity_id=int(owner.id),
                event_type="image_deleted",
                title="Изображение удалено",
                metadata={"previous_image_id": previous_id},
            )
        self.db.commit()
        self._invalidate(user_id)
        return owner

    def get_variant(
        self, *, user_id: int, asset_id: int, variant: str
    ) -> tuple[bytes, str]:
        if variant not in {"thumb", "detail"}:
            raise LookupError("Image variant not found")
        asset = self.repo.get(user_id=user_id, asset_id=asset_id)
        if asset is None:
            raise LookupError("Image not found")
        payload = asset.thumb_bytes if variant == "thumb" else asset.detail_bytes
        return payload, asset.checksum

    def _sync_product_offer_images(
        self,
        *,
        user_id: int,
        product_id: int,
        image_id: int | None,
    ) -> None:
        self.db.execute(
            update(OperationItemTemplate)
            .where(
                OperationItemTemplate.user_id == user_id,
                OperationItemTemplate.product_id == product_id,
            )
            .values(image_id=image_id)
        )
        self.db.flush()

    def _asset_is_referenced(self, *, asset_id: int) -> bool:
        for model in (CatalogProduct, ItemBrand, ItemSource, OperationItemTemplate):
            if self.db.scalar(
                select(model.id).where(model.image_id == asset_id).limit(1)
            ) is not None:
                return True
        return False

    def _asset_is_externally_referenced(
        self,
        *,
        asset_id: int,
        owner_kind: str,
        owner_id: int,
    ) -> bool:
        for kind, model in self.OWNER_MODELS.items():
            conditions = [model.image_id == asset_id]
            if kind == owner_kind:
                conditions.append(model.id != owner_id)
            if kind == "template" and owner_kind == "product":
                conditions.append(
                    (model.product_id.is_(None)) | (model.product_id != owner_id)
                )
            if self.db.scalar(select(model.id).where(*conditions).limit(1)) is not None:
                return True
        return False

    @classmethod
    def process_image(
        cls, *, raw: bytes, content_type: str | None
    ) -> ProcessedCatalogImage:
        if not raw:
            raise CatalogMediaValidationError("Image file is empty")
        if len(raw) > cls.MAX_UPLOAD_BYTES:
            raise CatalogMediaTooLargeError("Image file must be at most 8 MiB")
        normalized_content_type = (
            str(content_type or "").split(";", 1)[0].strip().lower()
        )
        if normalized_content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise CatalogMediaValidationError(
                "Only JPEG, PNG and WebP images are supported"
            )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as opened:
                    image_format = str(opened.format or "").upper()
                    if image_format not in cls.ALLOWED_FORMATS:
                        raise CatalogMediaValidationError(
                            "Only JPEG, PNG and WebP images are supported"
                        )
                    if (
                        cls.FORMAT_CONTENT_TYPES[image_format]
                        != normalized_content_type
                    ):
                        raise CatalogMediaValidationError(
                            "Image content type does not match file contents"
                        )
                    width, height = opened.size
                    if width <= 0 or height <= 0 or width * height > cls.MAX_PIXELS:
                        raise CatalogMediaTooLargeError(
                            "Image must be at most 20 megapixels"
                        )
                    if (
                        bool(getattr(opened, "is_animated", False))
                        or int(getattr(opened, "n_frames", 1) or 1) != 1
                    ):
                        raise CatalogMediaValidationError(
                            "Animated images are not supported"
                        )
                    opened.load()
                    image = ImageOps.exif_transpose(opened)
                    if image.mode not in {"RGB", "RGBA"}:
                        image = image.convert(
                            "RGBA" if "transparency" in image.info else "RGB"
                        )
                    else:
                        image = image.copy()
        except CatalogMediaValidationError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise CatalogMediaTooLargeError(
                "Image must be at most 20 megapixels"
            ) from exc
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise CatalogMediaValidationError(
                "Image file is corrupt or unsupported"
            ) from exc

        detail = cls._resized(image, cls.DETAIL_SIZE)
        thumb = cls._resized(image, cls.THUMB_SIZE)
        detail_bytes = cls._encode_webp(detail)
        thumb_bytes = cls._encode_webp(thumb)
        digest = sha256(thumb_bytes + detail_bytes).hexdigest()
        return ProcessedCatalogImage(
            thumb_bytes=thumb_bytes,
            thumb_width=thumb.width,
            thumb_height=thumb.height,
            detail_bytes=detail_bytes,
            detail_width=detail.width,
            detail_height=detail.height,
            checksum=digest,
        )

    @staticmethod
    def _resized(image: Image.Image, bounds: tuple[int, int]) -> Image.Image:
        result = image.copy()
        result.thumbnail(bounds, Image.Resampling.LANCZOS)
        return result

    @staticmethod
    def _encode_webp(image: Image.Image) -> bytes:
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=85, method=4, exact=True)
        return buffer.getvalue()

    @staticmethod
    def _invalidate(user_id: int) -> None:
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
