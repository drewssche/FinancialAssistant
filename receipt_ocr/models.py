import hashlib
import os
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get('OCR_MODEL_DIR', '/models'))
BASE = 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/'
FILES = {
    'ch_PP-OCRv5_det_mobile.onnx': ('PP-OCRv5/det/', '4d97c44a20d30a81aad087d6a396b08f786c4635742afc391f6621f5c6ae78ae'),
    'ch_ppocr_mobile_v2.0_cls_mobile.onnx': ('PP-OCRv4/cls/', 'e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c'),
    'eslav_PP-OCRv5_rec_mobile.onnx': ('PP-OCRv5/rec/', '08705d6721849b1347d26187f15a5e362c431963a2a62bfff4feac578c489aab'),
}


def valid():
    return all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
               for name, (_, digest) in FILES.items())


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, (folder, digest) in FILES.items():
        with urllib.request.urlopen(BASE + folder + name, timeout=60) as response:
            data = response.read(20 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError('OCR model checksum mismatch')
        (ROOT / name).write_bytes(data)
    assert valid()
