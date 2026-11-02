"""Authenticated bridge to the optional, resource-limited OCR container."""
import asyncio
import threading
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.requests import ClientDisconnect

from app.api.deps import get_current_user_id
from app.core.config import get_settings

router = APIRouter(prefix='/receipt-ocr', tags=['receipt-ocr'])
SLOT = threading.Lock()
LAST_REQUEST: dict[int, float] = {}
MAX_BYTES = 8 * 1024 * 1024


def base_url():
    url = get_settings().receipt_ocr_url.rstrip('/')
    if not url:
        raise HTTPException(503, 'Экспериментальный режим недоступен. Выберите Tesseract.')
    return url


@router.get('/status')
async def status(response: Response, user_id: int = Depends(get_current_user_id)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
            result = await client.get(base_url() + '/ready')
        return {'available': result.status_code == 200}
    except (httpx.HTTPError, HTTPException):
        return {'available': False}


@router.post('/recognize')
async def recognize(request: Request, response: Response, user_id: int = Depends(get_current_user_id)):
    url = base_url()
    response.headers['Cache-Control'] = 'no-store'
    if request.headers.get('content-type', '').split(';')[0] not in {'image/jpeg', 'image/png', 'image/webp'}:
        raise HTTPException(415, 'Нужно фото JPG, PNG или WebP.')
    if not SLOT.acquire(blocking=False):
        raise HTTPException(429, 'Распознавание занято. Повторите позже или выберите Tesseract.')
    try:
        now = time.monotonic()
        if now - LAST_REQUEST.get(user_id, -100) < 10:
            raise HTTPException(429, 'Подождите несколько секунд перед повторным распознаванием.')
        if len(LAST_REQUEST) > 1000:
            LAST_REQUEST.clear()
        LAST_REQUEST[user_id] = now
        body = bytearray()
        try:
            async with asyncio.timeout(10):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise HTTPException(413, 'Фото превышает допустимый размер.')
                    body.extend(chunk)
        except TimeoutError:
            raise HTTPException(408, 'Загрузка фото заняла слишком много времени.') from None
        except ClientDisconnect:
            raise HTTPException(400, 'Загрузка фото отменена.') from None
        if not body:
            raise HTTPException(400, 'Фото не загружено.')
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(98, connect=3), trust_env=False) as client:
                result = await client.post(url + '/recognize', content=bytes(body), headers={'Content-Type': request.headers['content-type']})
            data = result.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, 'Экспериментальный режим не ответил. Можно повторить с Tesseract.') from None
        if result.status_code != 200:
            messages = {400: 'Не удалось прочитать фото. Проверьте формат и размер.',
                        413: 'Фото превышает допустимый размер.',
                        429: 'Распознавание занято. Повторите позже или выберите Tesseract.',
                        504: 'Распознавание превысило лимит времени. Попробуйте Tesseract.'}
            raise HTTPException(result.status_code if result.status_code in messages else 503,
                                messages.get(result.status_code, 'Не удалось распознать фото. Попробуйте Tesseract.'))
        if not isinstance(data, dict) or not isinstance(data.get('text'), str) or len(data['text']) > 80000:
            raise HTTPException(503, 'Некорректный ответ распознавания.')
        return {'text': data['text'], 'blocks': [], 'engine': 'rapidocr-v5-eslav'}
    finally:
        SLOT.release()
