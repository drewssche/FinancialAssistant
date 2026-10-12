from decimal import Decimal
from sqlalchemy import event
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.main import app
from tests.api.test_catalog_product_linkage_api import client, _source
from tests.api.test_product_price_history_api import setup_product, buy


def hint(client, p, offer, **fields):
    payload = dict(template_id=offer, as_of='2026-10-10', currency='BYN', shop_name='Магазин', sale_unit='piece')
    payload.update(fields)
    return client.post(f'/api/v1/operations/catalog-products/{p}/price-hint', json=payload)


def test_previous_purchase_dates_edits_and_discount_are_exact(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1,row={'sale_unit':'kg','quantity':'0.242'})
    b=buy(client,p,s,10,2,row={'sale_unit':'kg','quantity':'0.242','regular_unit_price':'10','is_discounted':True,'discount_mode':'final','discount_value':'2.29'})
    c=buy(client,p,s,5,2,row={'sale_unit':'kg'})
    offer=a['receipt_items'][0]['template_id']
    found=hint(client,p,offer,sale_unit='kg',exclude_operation_id=c['id']).json()['previous']
    assert found['operation_id']==b['id'] and found['line_total']=='2.29'
    assert abs(Decimal(found['price'])-Decimal('2.29')/Decimal('.242')) < Decimal('0.0000001')
    assert found['is_discounted'] is True
    assert hint(client,p,offer,sale_unit='kg',as_of='2026-10-02',exclude_operation_id=b['id']).json()['previous']['operation_id']==a['id']
    assert hint(client,p,offer,sale_unit='kg',as_of='2026-10-01',exclude_operation_id=a['id']).json()['status']=='no_history'
    assert hint(client,p,offer,sale_unit='kg',as_of='2026-09-30').json()['status']=='no_history'
    assert hint(client,p,offer,sale_unit='kg').json()['previous']['operation_id']==c['id']


def test_shop_currency_measurements_and_variants_never_mix(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1,row={'sale_unit':'pack','package_quantity':'900','package_unit':'ml'})
    offer=a['receipt_items'][0]['template_id']
    fields=dict(sale_unit='pack',package_quantity='900',package_unit='ml')
    assert hint(client,p,offer,**fields,shop_name='  мАГАЗИН  ').json()['status']=='found'
    for kw in [{'shop_name':'Иной'},{'currency':'USD'},{'package_quantity':'1000'}, {'package_unit':'g'}, {'variant_id':91}]:
        assert hint(client,p,offer,**(fields|kw)).json()['status']=='no_history'
    gen=app.dependency_overrides[get_db]();db=next(gen)
    try:
        from app.db.models import OperationReceiptItem
        db.get(OperationReceiptItem,a['receipt_items'][0]['id']).variant_snapshot={'variant_id':91,'name':'Пакет','codes':[]}
        db.commit()
    finally: gen.close()
    assert hint(client,p,offer,**fields).json()['status']=='no_history'
    assert hint(client,p,offer,**fields,variant_id=91).json()['status']=='found'
    for kw in [{'sale_unit':None},{'sale_unit':'pack'},{'package_quantity':'900'}]:
        assert hint(client,p,offer,**kw).json()['status']=='unknown_measurements'


def test_ownership_validation_read_only_and_deleted_receipts(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1,row={'sale_unit':'piece'})
    offer=a['receipt_items'][0]['template_id']
    gen=app.dependency_overrides[get_db]();db=next(gen);engine=db.get_bind();statements=[]
    def track(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
    try:
        event.listen(engine,'before_cursor_execute',track)
        data=hint(client,p,offer).json()
        event.remove(engine,'before_cursor_execute',track)
        assert len(statements)==2 and all(s.lstrip().upper().startswith('SELECT') for s in statements)
    finally: gen.close()
    assert hint(client,p,offer).json()==data
    assert hint(client,p,offer,exclude_operation_id=999999).status_code==404
    for fields in [{'currency':'byn'},{'as_of':'bad'},{'template_id':0},{'sale_unit':'invalid'},{'package_quantity':'-1'},{'variant_id':0}]:
        assert hint(client,p,offer,**fields).status_code==422
    assert hint(client,p+100,offer).status_code==404
    assert client.delete(f"/api/v1/operations/{a['id']}").status_code==204
    assert hint(client,p,offer).json()['status']=='no_history'
    assert client.post(f"/api/v1/operations/{a['id']}/restore").status_code==200
    assert hint(client,p,offer).json()['status']=='found'
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert hint(client,p,offer).status_code==404


def test_plans_and_unknown_currency_are_not_purchase_history(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1,row={'sale_unit':'piece'})
    offer=a['receipt_items'][0]['template_id']
    res=client.post('/api/v1/plans',json={'kind':'expense','scheduled_date':'2026-10-02','receipt_items':[{'name':'Молоко','product_id':p,'source_id':s,'quantity':'1','unit_price':'100','sale_unit':'piece'}]})
    assert res.status_code==201,res.text
    assert hint(client,p,offer).json()['previous']['operation_id']==a['id']
    assert hint(client,p,offer,currency='USD').json()['status']=='no_history'
