"""Private Docker-network endpoint. No persistence, queues, secrets or external calls."""
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from receipt_ocr.models import valid
from receipt_ocr.worker import MAX_BYTES

SLOT = threading.Lock()
TIMEOUT = 90


def recognize(raw):
    try:
        result = subprocess.run([sys.executable, '-m', 'receipt_ocr.worker'], input=raw,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 504, {'detail': 'Распознавание превысило лимит времени. Попробуйте Tesseract.'}
    if result.returncode:
        return 503, {'detail': 'Движок не смог обработать фото. Попробуйте Tesseract.'}
    try:
        data = json.loads(result.stdout)
        if data.get('error') == 'invalid_image':
            return 400, {'detail': 'Нужно одно фото JPG, PNG или WebP до 4 мегапикселей.'}
        if not isinstance(data.get('text'), str) or len(data['text']) > 80000:
            raise ValueError()
        return 200, data
    except (ValueError, TypeError, AttributeError):
        return 503, {'detail': 'Не удалось прочитать результат распознавания.'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never log receipt contents or URLs from OCR text.

    def reply(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.reply(200 if self.path == '/ready' else 404, {'ready': self.path == '/ready'})

    def do_POST(self):
        if self.path != '/recognize':
            return self.reply(404, {})
        if not SLOT.acquire(blocking=False):
            return self.reply(429, {'detail': 'Распознавание занято. Повторите немного позже или выберите Tesseract.'})
        try:
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                size = 0
            if not 0 < size <= MAX_BYTES:
                return self.reply(413, {'detail': 'Фото превышает допустимый размер.'})
            self.connection.settimeout(10)
            raw = self.rfile.read(size)
            if len(raw) != size:
                return self.reply(400, {'detail': 'Фото загружено не полностью.'})
            self.reply(*recognize(raw))
        except (TimeoutError, ConnectionError):
            self.reply(408, {'detail': 'Не удалось загрузить фото.'})
        finally:
            SLOT.release()


if __name__ == '__main__':
    if not valid():
        raise RuntimeError('Missing or invalid OCR models')
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
