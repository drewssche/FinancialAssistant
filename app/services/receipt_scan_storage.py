"""Private, bounded receipt attachments. Financial rows never depend on the photo."""
import base64
import binascii
import io
import json

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select, update

from app.db.models.operation import Operation


def prepare_scan(payload, existing_image=None):
    if payload is None:
        return None
    data = {key: payload.get(key, default) for key, default in
            (("original_text", ""), ("text", ""), ("review", {}))}
    rows = data["review"].get("rows", [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Некорректные позиции чека")
    if (len(data["original_text"]) > 80000 or len(data["text"]) > 80000
            or len(json.dumps(data, ensure_ascii=False).encode()) > 600000
            or len(data["review"].get("rows", [])) > 150):
        raise ValueError("Слишком большой черновик чека")
    image = None
    if payload.get("image"):
        try:
            raw = base64.b64decode(payload["image"], validate=True)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError("Фото чека превышает 4 МБ")
            with Image.open(io.BytesIO(raw)) as opened:
                if opened.format not in {"JPEG", "PNG", "WEBP"} or opened.width * opened.height > 24000000:
                    raise ValueError("Неподдерживаемое фото чека")
                photo = ImageOps.exif_transpose(opened).convert("RGB")
                photo.thumbnail((2800, 2800), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                photo.save(output, format="WEBP", quality=88, method=5)
                image = raw if raw == existing_image else output.getvalue()
                data["width"], data["height"] = photo.size
        except (binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Не удалось прочитать фото чека") from exc
    return data, image


def attach_scan(operation, prepared):
    if prepared is not None:
        operation.receipt_scan_data, operation.receipt_scan_image = prepared
        operation.has_receipt_scan = True


def read_scan(db, user_id, operation_id):
    operation = db.scalar(select(Operation).where(Operation.user_id == user_id, Operation.id == operation_id))
    if operation is None or not operation.has_receipt_scan:
        return None
    photo = operation.receipt_scan_image
    return {**(operation.receipt_scan_data or {}),
            "image": base64.b64encode(photo).decode() if photo else None,
            "image_bytes": len(photo) if photo else 0}


def photo_stats(db, user_id):
    count, size = db.execute(select(func.count(Operation.id), func.coalesce(func.sum(func.length(Operation.receipt_scan_image)), 0))
                            .where(Operation.user_id == user_id, Operation.receipt_scan_image.is_not(None))).one()
    return {"count": count, "bytes": size}


def delete_photos(db, user_id):
    result = photo_stats(db, user_id)
    db.execute(update(Operation).where(Operation.user_id == user_id, Operation.receipt_scan_image.is_not(None))
               .values(receipt_scan_image=None))
    db.commit()
    return {"deleted": result["count"], "freed_bytes": result["bytes"]}
