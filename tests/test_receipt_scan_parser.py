"""OCR output is untrusted; arithmetic approval is distinct from text recognition."""
import json
import subprocess
from pathlib import Path

PARSER = Path('static/js/app-receipt-scan-parser.js').read_text()

def run(text):
    script='global.window={App:{}};'+PARSER+'\nconst d=window.App.receiptScanParser.parse('+json.dumps(text)+'); console.log(JSON.stringify({draft:d,errors:window.App.receiptScanParser.validate(d)}));'
    return json.loads(subprocess.check_output(['node','-e',script],text=True))

def test_weight_discount_repeats_and_camera_date():
    result=run('''ООО ГРИНРОЗНИЦА
№ ДОК. 123
Сыр вес
22339202200143 15.64 x0.242 3.79
Скидка -0.13
Сырок 45г
4810290117151 1.10 x1.000 1.10
Сырок 45г
4810290117151 1.10 x1.000 1.10
ИТОГО К ОПЛАТЕ 5.86
12.10.2026 18:24:04
REDMI NOTE 12 PRO
14.10.2026 20:02''')
    assert result['draft']['date']=='2026-10-12'
    rows=result['draft']['rows']
    assert len(rows)==3 and rows[0]['quantity']==.242 and rows[0]['total']==366
    assert rows[1]['name']==rows[2]['name']=='Сырок 45г'
    # The photographed cheese line rounds differently from price × weight; require review.
    assert result['errors']==['Проверьте цену, количество и скидку позиции 1']

def test_loyalty_separate_line_and_no_dosage_inference():
    result=run('''ООО Аптека
№ ДОК 123
Парацетамол 500 мг №10x2
4810201008226 2.55 x1.000 2.55
Скидка Оплата бонусами
-0.16
ИТОГО К ОПЛАТЕ
2.39
12.10.2026 18:26:59''')
    row=result['draft']['rows'][0]
    assert row['discount_type']=='loyalty_points' and row['total']==239
    assert '500 мг' in row['name'] and 'package_quantity' not in row
    assert result['errors']==[]

def test_inconsistent_arithmetic_and_missing_fields_block():
    result=run('Товар\n7.06 x1.000 1.06\nИТОГО К ОПЛАТЕ 1.06')
    assert result['draft']['rows'][0]['issue']
    assert len(result['errors'])>=3

def test_ambiguous_date_total_never_selects_arbitrarily():
    result=run('01.10.2026 10:00:00\n02.10.2026 11:00:00\nИТОГО К ОПЛАТЕ 1.00\nИТОГО К ОПЛАТЕ 2.00')
    assert result['draft']['date']=='' and result['draft']['total'] is None

def test_no_execution_or_digit_repair():
    result=run('<script>alert(1)</script>\nМолоко\nЗ.00 x1.000 3.00')
    assert result['draft']['rows']==[] and result['errors']


def test_bad_date_and_large_scan_are_not_silently_truncated():
    result=run('ООО Тест\n№ ДОК\n'+('Молоко\n1.00 x1.000 1.00\n'*200)+'ИТОГО К ОПЛАТЕ 200.00\n30.02.2026 12:00:00')
    assert result['draft']['date']=='' and len(result['draft']['rows'])==151
    assert 'В чеке должно быть от 1 до 150 позиций' in result['errors']


def test_ocr_assets_match_pinned_manifest():
    import hashlib
    root=Path('static/vendor/receipt-ocr/v7')
    manifest=json.loads((root/'manifest.json').read_text())
    assert manifest['packages']['tesseract.js']=='7.0.0'
    for name,digest in manifest['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name


def test_returns_and_negative_rows_cannot_become_positive_expenses():
    for line in ['Возврат\nТовар\n5.00 x1.000 5.00','Товар\n-5.00 x1.000 5.00']:
        result=run('ООО Тест\n№ ДОК\n'+line+'\nИТОГО К ОПЛАТЕ 5.00\n12.10.2026 12:00:00')
        assert result['draft']['unsupported'] and any('ручной ввод' in e for e in result['errors'])
