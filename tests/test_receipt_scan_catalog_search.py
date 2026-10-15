"""OCR keywords rank candidates; they never assign a product automatically."""
import json
import subprocess
from pathlib import Path


def rank(query, products, shop='Green'):
    setup = '''global.window={App:{}};
window.App.getRuntimeModule=()=>({});
window.App.registerRuntimeModule=(name,f)=>{global.factory=f;};
'''
    script=setup+Path('static/js/app-search-utils.js').read_text()+Path('static/js/app-features-operation-modal-receipt-pickers.js').read_text()
    script+='\nconst state={receiptProductHints:'+json.dumps(products,ensure_ascii=False)+',receiptTemplateHints:[]};'
    script+='\nconst picker=factory({state,core:{},receiptUiState:{},normalizeReceiptName:v=>String(v||"").trim()});'
    script+='\nconsole.log(JSON.stringify(picker.getReceiptScanSuggestions('+json.dumps(query,ensure_ascii=False)+','+json.dumps(shop)+',8)));'
    return json.loads(subprocess.check_output(['node','-e',script],text=True))

PRODUCTS=[{'id':i+1,'name':name,'offers':[]} for i,name in enumerate([
    'Кетчуп Помидюр Томатный 270г','Кетчуп Помидюр Барбекю 270г','Кетчуп Классический 250г',
    'Батон Традиционный новый 225г','Батон Традиционный новый 450г','Батон Аппетитный 240г',
    'Батончик Bounty 78г','Колбаса Краковская 1кг','Колбаски охотничьи с перцем варено-копченые 560г',
    'Чипсы охотничьи колбаски 100г'])]


def test_long_receipt_name_uses_individual_keywords_and_ocr_typo():
    rows=rank('Кетчуп Помидор Томатный категория Первая 270 г дой-пак с дозатором',PRODUCTS)
    assert rows[0]['name']=='Кетчуп Помидюр Томатный 270г'
    assert set(rows[0]['scan_match']['words'])=={'кетчуп','помидор','томатный'}
    assert len(rows)>=3 and not rows[0]['scan_match']['exact']


def test_package_size_ranks_but_never_assigns_or_hides_alternative():
    rows=rank('Батон Традиционный новый сдоб в/с нар 0,45 кг пак х/з Автомат',PRODUCTS)
    assert rows[0]['name']=='Батон Традиционный новый 450г'
    assert rows[1]['name']=='Батон Традиционный новый 225г'
    assert rows[1]['scan_match']['sizeConflict']
    assert all('package_quantity' not in row for row in rows)
    assert not any(row['name'].startswith('Батончик') for row in rows)


def test_generic_keyword_is_labelled_as_candidate_not_exact_identity():
    rows=rank('Колбаса Рубленая варено-копченая в/с',PRODUCTS)
    assert rows[0]['name']=='Колбаса Краковская 1кг'
    assert rows[0]['scan_match']['words']==['колбаса']
    assert all(not row['scan_match']['exact'] for row in rows)


def test_no_matches_from_just_weight_processing_or_noise():
    for query in ['270 г 560г 1кг','варено-копченая в/с уп 560г','Абрикос джем']:
        assert rank(query,PRODUCTS)==[]


def test_offer_alias_and_wrong_layout_are_searchable():
    products=[{'id':1,'name':'Томатный соус','offers':[{'id':10,'name':'Кетчуп Помидюр','shop_name':'Green'}]},
              {'id':2,'name':'Томатный соус','offers':[{'id':20,'name':'Кетчуп Помидюр','shop_name':'Соседи'}]}]
    rows=rank('rtnxeg',products)
    assert rows[0]['id']==1 and rows[0]['selected_offer']['id']==10
    assert rows[1]['selected_offer'] is None
