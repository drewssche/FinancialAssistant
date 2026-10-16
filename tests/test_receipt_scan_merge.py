"""Automatic grouping and reversal preserve every cent and identifier."""
import json
import subprocess
from pathlib import Path


def merge(rows):
    code='global.window={App:{core:{}}};'+Path('static/js/app-receipt-codes.js').read_text()+Path('static/js/app-receipt-scan-parser.js').read_text()
    code+='const rows='+json.dumps(rows)+';const before=JSON.stringify(rows);const result=window.App.receiptScanParser.mergeDuplicates(rows,window.App.receiptCodes.validBarcode);console.log(JSON.stringify({result,unchanged:before===JSON.stringify(rows)}));'
    result=json.loads(subprocess.check_output(['node','-e',code],text=True))
    assert result['unchanged']
    return result['result']


def row():
    return dict(name='Сырок Ясь Белоус 45г',price=110,quantity=1,total=110,discount=0,source='Сырок 1.10 x1.000 1.10',code_entries=[{'kind':'unknown','code':'4810729017151'},{'kind':'unknown','code':'1751767'}])


def test_four_repeats_and_another_item_keep_order_and_totals():
    other={**row(),'name':'Пельмени','price':599,'total':599,'code_entries':[{'kind':'barcode','code':'4811040140757'}]}
    rows=[other,row(),{**row(),'name':'Сырок Ясь Белоус (фундук-какао)'},row(),row()]
    result=merge(rows)
    assert len(result)==2 and result[0]==other
    assert result[1]['quantity']==4 and result[1]['price']==110 and result[1]['total']==440
    assert result[1]['merged_count']==4 and result[1]['code_entries']==rows[1]['code_entries']
    assert sum(r['total'] for r in result)==1039


def test_discount_amounts_add_only_with_same_price_and_discount_rate():
    a={**row(),'price':150,'discount':40,'total':110,'discount_type':'coupon'}
    b={**a,'quantity':2,'discount':80,'total':220}
    combined=merge([a,b])[0]
    assert combined['quantity']==3 and combined['discount']==120 and combined['total']==330
    for changed in [dict(price=160,total=120),dict(discount=30,total=120),dict(discount_type='promo')]:
        assert len(merge([a,{**a,**changed}]))==2


def test_ambiguous_codes_sizes_catalog_and_invalid_math_are_not_merged():
    a=row()
    for changes in [dict(code_entries=[]),dict(code_entries=[{'kind':'barcode','code':'4810729017152'}]),dict(code_entries=[{'kind':'retailer','code':'4810729017151'}]),dict(code_entries=[{'kind':'barcode','code':'4810729017151'},{'kind':'retailer','code':'other'}]),dict(package_quantity=200,package_unit='g'),dict(total=111),dict(discount=None),dict(issue='Проверьте строку'),dict(category_id=42),dict(catalog={'product_id':2})]:
        b={**a,**changes}
        assert len(merge([a,b]))==2



def test_canonical_gtin_and_rounding_and_variable_weight_codes():
    a=row();b={**a,'code_entries':[{'kind':'barcode','code':'04810729017151'},{'kind':'unknown','code':'1751767'}]}
    assert len(merge([a,b]))==1
    # Each row rounds to 0.05, but grouped multiplication would round to 0.09.
    fractional={**a,'quantity':.333,'price':14,'total':5}
    assert len(merge([fractional,fractional]))==2
    prefix='223186022940'
    code=prefix+str((10-sum(int(n)*(3 if i%2==0 else 1) for i,n in enumerate(reversed(prefix)))%10)%10)
    variable={**a,'code_entries':[{'kind':'barcode','code':code}]}
    assert len(merge([variable,variable]))==2
    assert len(merge([a]*151))==151


def test_split_restores_original_money_and_keeps_independent_catalog_edits():
    code='global.window={App:{core:{}}};'+Path('static/js/app-receipt-codes.js').read_text()+Path('static/js/app-receipt-scan-parser.js').read_text()
    code+=r"""
    const parser=window.App.receiptScanParser;
    const original=parser.parse('ООО Тест\n№ ДОК\nСырок\n4810729017151 1.10 x1.000 1.10\nСырок другой текст\n4810729017151 1.10 x2.000 2.20\nИТОГО К ОПЛАТЕ 3.30\n15.10.2026 21:23:00').rows;
    const merged=parser.mergeDuplicates(original,window.App.receiptCodes.validBarcode)[0];
    const before=JSON.stringify(merged);
    const initialChanged=parser.mergedMoneyChanged(merged);
    merged.catalog={product_id:42};merged.category_id=101;
    const metadataChanged=parser.mergedMoneyChanged(merged);
    merged.quantity=5;const moneyChanged=parser.mergedMoneyChanged(merged);
    const split=parser.splitMergedRow(merged);
    const money=split.map(r=>[r.quantity,r.price,r.total,r.source,r.name]);
    split[0].code_entries[0].code='changed';split[0].catalog.product_id=99;
    console.log(JSON.stringify({initialChanged,metadataChanged,moneyChanged,money,independent:split[1].code_entries[0].code==='4810729017151'&&split[1].catalog.product_id===42,category:split[1].category_id,codes:window.App.receiptCodes.payload(split[1]),original}));
    """
    result=json.loads(subprocess.check_output(['node','-e',code],text=True))
    assert not result['initialChanged'] and not result['metadataChanged'] and result['moneyChanged']
    assert result['money']==[[r['quantity'],r['price'],r['total'],r['source'],r['name']] for r in result['original']]
    assert result['independent'] and result['category']==101 and result['codes']==[{'kind':'barcode','code':'4810729017151'}]
