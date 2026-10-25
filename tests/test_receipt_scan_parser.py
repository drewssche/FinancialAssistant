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
    assert result['draft']['rows'][0]['price'] is None and result['errors']


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


def test_euroopt_repeated_items_codes_and_punctuated_date():
    text = '000 "ЕВРОТОРГ", Магазин "Euroopt PRIME"\n№ ДОК\n2186323 Пельмени Бульварские\nслив. масл. 430г 4811040140757\n5.99 x1.000 5.99\n'
    text += ('1751767 Сырок Ясь Белоус\nфундук-какао 16% 45г 4810729017151\n1.10 x1.000 1.10\n' * 4)
    text += 'ИТОГО К. ОПЛАТЕ 10.39\n15,10,2026 21:23:00\n15.10.2026 22:48'
    result=run(text);d=result['draft']
    assert result['errors']==[] and d['date']=='2026-10-15' and d['shop']=='Евроопт'
    assert len(d['rows'])==5 and all(r['price']==110 for r in d['rows'][1:])
    assert all('1751767' not in r['name'] and '4810729017151' not in r['name'] for r in d['rows'])
    assert '4810729017151' in d['rows'][1]['source']


def test_green_discounts_and_spaced_decimal_separators():
    result=run("""* 000 "ГРИНРОЗНИЦА" *
№ ДОК
Чипсы Lay's Нежный сыр с луком 105г
4690388122492 4.99 x1 ,000 4.99
Сыр Камамбер DANKE 50%
4620018341313 10.29 x1.000 10.29
Пельмени Бульварские по-пекински 430г
4811040142935 7.11 x1.000 7.11
Скидка -0.71
Багет Венский молочный
4816413204784 1.99 x1.000 1.99
Скидка -0.60
ИТОГО К ОПЛАТЕ 23.07
ИТОГО СКИДКА -1.31
14.10.2026 22:12:21
Ваши скидки
Купоны 0.60""")
    d=result['draft'];assert result['errors']==[] and d['shop']=='Green'
    assert [r['total'] for r in d['rows']]==[499,1029,640,139]
    assert [r['discount'] for r in d['rows']]==[0,0,71,60]


def test_discount_after_unreadable_item_never_attaches_to_previous():
    result=run('ООО Тест\n№ ДОК\nМолоко\n3.00 x1.000 3.00\nХлеб\n1.99 х!.000 1.99\nСкидка -0.60\nИТОГО К ОПЛАТЕ 4.39\n14.10.2026 10:20:30')
    rows=result['draft']['rows']
    assert len(rows)==2 and rows[0]['discount']==0 and rows[0]['total']==300
    assert rows[1]['price'] is None and rows[1]['discount']==60 and rows[1]['total']==139
    assert result['errors']


def test_discount_after_missing_money_row_is_kept_for_review():
    result=run('ООО Тест\n№ ДОК\nМолоко\n3.00 x1.000 3.00\nХлеб\nнечитаемая строка\nСкидка -0.60\nИТОГО К ОПЛАТЕ 4.39\n14.10.2026 10:20:30')
    rows=result['draft']['rows']
    assert rows[0]['discount']==0 and rows[1]['price'] is None and rows[1]['total'] is None
    assert rows[1]['discount']==60 and result['errors']


def test_weighted_green_purchase_keeps_weight_and_rounding():
    result=run('000 "ГРИНРОЗНИЦА"\n№ ДОК\nКетчуп Помидюр 270 г\n3.59 x1.000 3.59\nБатон 0,45 кг\n2.07 x1.000 2.07\nКолбаса Рубленая\n22318602229407 18.69 x0.530 9.91\nИТОГО К ОПЛАТЕ 15.57\n13.10.2026 15:07:01')
    rows=result['draft']['rows'];assert result['errors']==[]
    assert rows[1]['quantity']==1 and rows[2]['quantity']==.530 and rows[2]['total']==991


def test_storefront_and_promotion_dates_are_not_payment_dates():
    result=run('Общество с ограниченной ответственностью\nЛибретик\nМагазин "Соседи"\n№ ДОК\nПицца 200г\n4.99 *1.000 4.99\nИТОГО К ОПЛАТЕ 4.99\n13.10.2026 22:53:51\nДата начала действия 2026-09-01\nДата окончания действия 2026-12-31\n15.10.2026 22:50')
    assert result['errors']==[] and result['draft']['shop']=='Соседи' and result['draft']['date']=='2026-10-13'


def test_malformed_money_cannot_be_matched_from_its_suffix():
    for price in ['З3.00','3.000','1.3.00']:
        d=run('ООО Тест\n№ ДОК\nМолоко\n'+price+' x1.000 3.00\nИТОГО К ОПЛАТЕ 3.00\n14.10.2026 10:20:30')
        assert d['errors'] and (not d['draft']['rows'] or d['draft']['rows'][0]['price'] is None)


def test_unreadable_weight_line_is_visible_without_inferred_quantity():
    d=run('ООО Тест\n№ ДОК\nКолбаса Рубленая\n2231860229401 18 69 : Han 82 9.91\nИТОГО К ОПЛАТЕ 9.91\n13.10.2026 15:07:01')
    r=d['draft']['rows'][0]
    assert r['name']=='Колбаса Рубленая' and r['price'] is None and r['quantity'] is None and r['total']==991
    assert d['errors']


def test_unreadable_discount_is_unknown_not_zero():
    d=run('ООО Тест\n№ ДОК\nХлеб\n1.99 x1.000 1.99\nСкидка -0.7\nИТОГО К ОПЛАТЕ 1.99\n14.10.2026 12:00:00')
    assert d['draft']['rows'][0]['discount'] is None and d['draft']['rows'][0]['total'] is None
    assert d['errors']


def test_item_codes_preserve_zeroes_and_exclude_receipt_metadata():
    parsed=run('''ООО ГРИНРОЗНИЦА
УНП 191634233
№ ДОК 123456789
0012345 Пельмени 430г
04006381333931 7.11 x1.000 7.11
Скидка -0.71
Молоко
арт. AB-0042
4006381333931
3.00 x1.000 3.00
ИТОГО К ОПЛАТЕ 9.40
13.10.2026 18:24:04
Карта 1234567890123''')['draft']
    first,second=parsed['rows']
    assert first['code_entries']==[{'kind':'unknown','code':'0012345'},{'kind':'unknown','code':'04006381333931'}]
    assert {e['code'] for e in second['code_entries']}=={'AB-0042','4006381333931'}
    assert second['code_entries'][0]['kind']=='retailer'
    assert second['name']=='Молоко'
    assert first['price']==711 and first['total']==640


def test_edit_recalculates_money_in_both_directions_without_changing_source():
    script='global.window={App:{}};'+PARSER+r'''
    const calc=window.App.receiptScanParser.recalculateRow;
    const row={price:1459,quantity:.32,discount:0,total:229,printed_total:229};
    const results=[];
    for(const [field,value] of [['quantity',.32],['quantity',.324],['discount',73],['total',399],['quantity',.32],['price',1500],['total',480],['total',500]]){
      row[field]=value;results.push({changed:calc(row,field),...row});
    }
    console.log(JSON.stringify(results));'''
    rows=json.loads(subprocess.check_output(['node','-e',script],text=True))
    assert [r['total'] for r in rows]==[467,473,400,399,393,406,480,500]
    assert [r['discount'] for r in rows]==[0,0,73,74,74,74,0,0]
    assert all(r['printed_total']==229 for r in rows)
    assert rows[-1]['changed']==[]  # Above-subtotal payments never invent a negative discount.


def test_edit_rounding_unknown_values_and_no_invented_price_or_quantity():
    script='global.window={App:{}};'+PARSER+r'''
    const calc=window.App.receiptScanParser.recalculateRow;
    const half={price:1,quantity:.5,discount:0,total:99};calc(half,'quantity');
    const unknown={price:null,quantity:1,discount:0,total:99};calc(unknown,'total');
    const incomplete={price:711,quantity:1,discount:null,total:640};calc(incomplete,'price');
    const overdiscount={price:100,quantity:1,discount:101,total:100};calc(overdiscount,'discount');
    const unrelated={price:100,quantity:1,discount:0,total:99};calc(unrelated,'name');
    console.log(JSON.stringify({half,unknown,incomplete,overdiscount,unrelated}));'''
    data=json.loads(subprocess.check_output(['node','-e',script],text=True))
    assert data['half']['total']==1
    assert data['unknown']=={'price':None,'quantity':1,'discount':0,'total':99}
    assert data['incomplete']['total'] is None
    assert data['overdiscount']['total']==-1
    assert data['unrelated']['total']==99


def test_selected_catalog_size_fallback_is_conservative():
    items=[
        {'name':'Укроп 40г','sale_unit':'pack'},
        {'name':'Сок 0,75 л','sale_unit':'piece'},
        {'name':'Яйцо перепелиное 20шт','sale_unit':'pack'},
        {'name':'Лук 1кг','sale_unit':'kg'},
        {'name':'Кофе 2 x 40г','sale_unit':'pack'},
        {'name':'Набор 40г + 20г','sale_unit':'pack'},
        {'name':'Укроп 40г','sale_unit':'pack','package_quantity':50,'package_unit':'g'},
        {'name':'Название 40г','sale_unit':'pack','variant_snapshot':{'name':'Фасовка 30г'}},
    ]
    script='global.window={App:{}};'+PARSER+'\nconsole.log(JSON.stringify('+json.dumps(items,ensure_ascii=False)+'.map(window.App.receiptScanParser.catalogMeasurement)));'
    rows=json.loads(subprocess.check_output(['node','-e',script],text=True))
    assert [(r['package_quantity'],r['package_unit']) for r in rows[:3]]==[(40,'g'),(.75,'l'),(20,'piece')]
    assert all(rows[i]['package_quantity'] is None for i in [3,4,5])
    assert rows[6]['package_quantity']==50 and not rows[6].get('catalog_size_from_name')
    assert rows[7]['package_quantity']==30


def test_euroopt_article_without_barcode_and_article_before_amount():
    for item in ['2229644 Пицца Микс 170г\n3.99 x1.000 3.99', 'Пицца Микс 170г\n2229644 3.99 x1.000 3.99']:
        data=run('ООО Евроторг\n№ ДОК 123\n'+item+'\nИТОГО К ОПЛАТЕ 3.99\n23.10.2026 12:00:00')['draft']
        assert data['shop']=='Евроопт'
        assert data['rows'][0]['code_entries']==[{'kind':'unknown','code':'2229644'}]
        assert data['rows'][0]['total']==399
