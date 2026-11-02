"""One disposable process per image: a native crash cannot kill the API server."""
import io
import json
import sys
import warnings

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 4_000_000


def validate_image(raw):
    from PIL import Image
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('invalid_image')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in {'PNG', 'JPEG', 'WEBP'} or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('invalid_image')
            if min(image.size) < 60 or max(image.size) > 3600 or image.width * image.height > MAX_PIXELS:
                raise ValueError('invalid_image')
            image.verify()


def assemble_lines(boxes, texts):
    words = []
    for box, text in zip(boxes, texts):
        ys, xs = [p[1] for p in box], [p[0] for p in box]
        words.append({'x': min(xs), 'y': sum(ys) / 4, 'h': max(ys) - min(ys), 'text': text})
    groups = []
    for word in sorted(words, key=lambda w: w['y']):
        candidates = [g for g in groups if abs(g['y'] - word['y']) < .5 * min(g['h'], word['h'])]
        if candidates:
            group = min(candidates, key=lambda g: abs(g['y'] - word['y']))
            group['words'].append(word)
            group['y'] = sum(w['y'] for w in group['words']) / len(group['words'])
        else:
            groups.append({'y': word['y'], 'h': word['h'], 'words': [word]})
    return '\n'.join(' '.join(w['text'] for w in sorted(g['words'], key=lambda w: w['x']))
                     for g in sorted(groups, key=lambda g: g['y']))[:80000]


def make_engine():
    import cv2
    from rapidocr import RapidOCR, OCRVersion, ModelType, LangRec
    from receipt_ocr.models import ROOT
    cv2.setNumThreads(1)
    engine = RapidOCR(params={
        'Det.limit_type': 'max', 'Det.limit_side_len': 1280,
        'Det.ocr_version': OCRVersion.PPOCRV5, 'Det.model_type': ModelType.MOBILE,
        'Rec.ocr_version': OCRVersion.PPOCRV5, 'Rec.model_type': ModelType.MOBILE,
        'Rec.lang_type': LangRec.ESLAV, 'Global.model_root_dir': str(ROOT),
        'EngineConfig.onnxruntime.intra_op_num_threads': 1,
        'EngineConfig.onnxruntime.inter_op_num_threads': 1,
        'Global.log_level': 'error',
    })
    return engine


def main():
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    try:
        validate_image(raw)
    except Exception:
        print(json.dumps({'error': 'invalid_image'}))
        return
    result = make_engine()(raw)
    text = assemble_lines(result.boxes, result.txts) if result.txts is not None else ''
    print(json.dumps({'text': text, 'engine': 'rapidocr-v5-eslav', 'blocks': []}, ensure_ascii=False))


if __name__ == '__main__':
    main()
