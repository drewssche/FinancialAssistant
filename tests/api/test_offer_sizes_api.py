from tests.api.test_catalog_product_linkage_api import client
from tests.api.test_product_primary_codes_api import create
from tests.api.test_catalog_identity_api import get, CODE
from tests.api.test_receipt_codes_api import lookup


def setup(client):
    p=create(client,codes={'barcodes':[{'codes':[CODE]}],'retailers':[{'shop_name':'Green','retailer_code':'001'},{'shop_name':'Соседи','retailer_code':'002'}]}).json()
    return p['id'],{o['source_name']:o['id'] for o in p['offers']}


def save(client,p,edits,**fields):
    return client.patch(f'/api/v1/operations/catalog-products/{p}',json={'codes':{'offer_sizes':edits},**fields})


def test_override_inheritance_reset_and_source_sku(client):
    p,offers=setup(client);a,b=offers['Green'],offers['Соседи']
    own={'template_id':a,'use_product_size':False,'sale_unit':'pack','package_quantity':'500','package_unit':'ml','codes':['5901234123457']}
    r=save(client,p,[own]);assert r.status_code==200,r.text
    byid={o['id']:o for o in r.json()['offers']}
    assert float(byid[a]['package_quantity'])==500 and byid[a]['variant_id']
    assert float(byid[b]['package_quantity'])==900 and byid[b]['variant_id'] is None
    result=lookup(client,[{'kind':'retailer','code':'001'}])['items'][0]
    assert float(result['package_quantity'])==500 and result['variant_snapshot']['codes']==['5901234123457']
    r=save(client,p,[],package_quantity='1000');assert r.status_code==200,r.text
    byid={o['id']:o for o in r.json()['offers']}
    assert float(byid[a]['package_quantity'])==500 and float(byid[b]['package_quantity'])==1000
    hint=client.get(f'/api/v1/operations/item-templates/{a}').json()
    assert float(hint['package_quantity'])==500 and hint['measurement_source']=='offer'
    reset=save(client,p,[{'template_id':a,'use_product_size':True}]);assert reset.status_code==200,reset.text
    byid={o['id']:o for o in reset.json()['offers']}
    assert float(byid[a]['package_quantity'])==1000 and byid[a]['variant_id'] is None
    identity=get(client,p)
    assert {code for v in identity['variants'] for code in v['codes']}=={CODE,'5901234123457'}
    assert next(o for o in identity['offers'] if o['template_id']==a)['retailer_code']=='001'


def test_invalid_offer_size_and_barcode_roll_back_product(client):
    p,offers=setup(client);a=offers['Green']
    for edit in [dict(template_id=a,use_product_size=False,sale_unit='pack',package_quantity='200'),dict(template_id=a,use_product_size=False,sale_unit='pack',package_quantity='200',package_unit='ml',codes=[CODE]),dict(template_id=99999,use_product_size=True)]:
        r=save(client,p,[edit],name='Не сохранять');assert r.status_code==400,r.text
        assert client.get(f'/api/v1/operations/catalog-products/{p}').json()['name']=='Молоко'
    assert len(get(client,p)['variants'])==1


def test_saving_same_size_shares_variant_and_old_variants_are_immutable(client):
    p,offers=setup(client);a,b=offers.values()
    size=dict(use_product_size=False,sale_unit='piece',package_quantity='200',package_unit='ml')
    assert save(client,p,[dict(template_id=a,**size),dict(template_id=b,**size)]).status_code==200
    identity=get(client,p);old=next(v for v in identity['variants'] if float(v['package_quantity'])==200)
    assert {o['variant_id'] for o in identity['offers']}=={old['id']}
    assert save(client,p,[dict(template_id=a,**{**size,'package_quantity':'300'})]).status_code==200
    identity=get(client,p)
    assert float(next(v for v in identity['variants'] if v['id']==old['id'])['package_quantity'])==200
    assert next(o for o in identity['offers'] if o['template_id']==b)['variant_id']==old['id']


def test_duplicate_sizes_require_explicit_variant_and_reject_mismatched_size(client):
    from tests.api.test_catalog_identity_api import variant
    p,offers=setup(client);a=offers['Green']
    duplicate=variant(client,p,codes=[]);assert duplicate.status_code==201
    records=get(client,p)['variants'];chosen=records[-1]['id']
    size=dict(template_id=a,use_product_size=False,sale_unit='pack',package_quantity='900',package_unit='ml')
    assert save(client,p,[size]).status_code==400
    assert save(client,p,[dict(size,variant_id=chosen,package_quantity='200')]).status_code==400
    assert save(client,p,[dict(size,variant_id=chosen)]).status_code==200
    assert next(o for o in get(client,p)['offers'] if o['template_id']==a)['variant_id']==chosen
