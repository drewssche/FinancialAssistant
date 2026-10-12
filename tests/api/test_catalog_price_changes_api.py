from decimal import Decimal
from sqlalchemy import event
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.main import app
from tests.api.test_catalog_product_linkage_api import client, _source
from tests.api.test_product_price_history_api import setup_product, buy, history


def changes(client, **params):
    response = client.get('/api/v1/operations/catalog-products/price-changes', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_period_last_step_return_and_previous_cost(client):
    p, s = setup_product(client)
    ops = [buy(client, p, s, price, day, row={'sale_unit':'piece', 'quantity':'2'}) for day, price in enumerate([3,4,3],1)]
    data = changes(client)
    row = data['items'][0]
    assert data['total'] == 1 and row['observations_count'] == 3
    assert row['increases'] == row['decreases'] == 1
    assert row['period_change_percent'] == row['change_percent'] == '0.00'
    assert row['last_change_percent'] == '-25.00'
    assert row['baseline_cost'] == row['latest_cost'] == '6.00'
    previous = changes(client, comparison='previous')['items'][0]
    assert previous['baseline_cost'] == '8.00' and previous['cost_difference'] == '-2.00'
    assert changes(client, direction='up')['total'] == 0
    assert changes(client, direction='same')['total'] == 1
    assert changes(client, comparison='previous', direction='down')['total'] == 1
    period = changes(client, date_from='2026-10-02', date_to='2026-10-03')['items'][0]
    assert period['change_percent'] == '-25.00' and period['observations_count'] == 2
    one = changes(client, date_from='2026-10-03')
    assert one['total'] == 0 and one['insufficient_series_count'] == 1
    assert changes(client, q='vjkjrj')['total'] == 1
    assert changes(client, q='Не существует')['total'] == 0
    assert row['latest_operation_id'] == ops[-1]['id']


def test_normalized_packages_dimensions_and_exact_discount(client):
    p, s = setup_product(client)
    first = buy(client, p, s, 3, 1, row={'sale_unit':'pack','package_quantity':'1000','package_unit':'ml'})
    buy(client, p, s, 3, 2, row={'quantity':'2','sale_unit':'pack','package_quantity':'900','package_unit':'ml'})
    buy(client, p, s, 9, 3)
    assert changes(client)['total'] == 0
    normalized = changes(client, basis='normalized')
    row = normalized['items'][0]
    assert normalized['excluded_count'] == 1
    assert row['unit'] == 'l' and row['package_changed'] is True
    assert row['change_percent'] == '11.11'
    assert row['baseline_cost'] == '5.40' and row['latest_cost'] == '6.00' and row['cost_difference'] == '0.60'
    h = history(client, p, first['receipt_items'][0]['template_id'], basis='normalized')['series'][0]
    assert row['change_percent'] == h['change_percent'] and row['observations_count'] == len(h['observations'])
    buy(client,p,s,10,4,row={'quantity':'0.242','sale_unit':'kg','regular_unit_price':'10','is_discounted':True,'discount_mode':'final','discount_value':'2.29'})
    buy(client,p,s,12,5,row={'quantity':'0.242','sale_unit':'kg','regular_unit_price':'12','is_discounted':True,'discount_mode':'final','discount_value':'2.65'})
    paid = next(r for r in changes(client,basis='normalized')['items'] if r['unit']=='kg')
    assert paid['latest_cost'] == '2.65' and paid['baseline_cost'] == '2.29'
    regular = changes(client,basis='normalized',price_kind='regular')['items'][0]
    assert regular['change_percent'] == '20.00' and regular['latest_cost'] == '2.90'
    assert regular['baseline_cost'] == '2.42'


def test_shops_currencies_ownership_and_plans_are_separate(client):
    p, s = setup_product(client)
    for day, price in [(1,3),(2,4)]: buy(client,p,s,price,day,row={'sale_unit':'piece'})
    other_shop = _source(client,'Другой магазин')
    for day, price in [(3,1),(4,2)]: buy(client,p,other_shop,price,day,row={'sale_unit':'piece'})
    for day, price in [(5,2),(6,3)]: buy(client,p,s,price,day,currency='USD',fx_rate='3',row={'sale_unit':'piece'})
    plan=client.post('/api/v1/plans',json={'kind':'expense','scheduled_date':'2026-10-08','receipt_items':[{'name':'Молоко','product_id':p,'source_id':s,'quantity':'1','unit_price':'100','sale_unit':'piece'}]})
    assert plan.status_code==201,plan.text
    rows = changes(client)['items']
    assert len(rows)==3
    assert all(r['observations_count']==2 for r in rows)
    assert {(r['shop_name'],r['currency'],r['change_percent']) for r in rows} == {('Магазин','BYN','33.33'),('Другой магазин','BYN','100.00'),('Магазин','USD','50.00')}
    a=changes(client,page_size=1);b=changes(client,page_size=1,page=2)
    assert a['total']==b['total']==3 and a['items'][0]['latest_receipt_item_id']!=b['items'][0]['latest_receipt_item_id']
    app.dependency_overrides[get_current_user_id]=lambda:2
    assert changes(client)['total']==0


def test_edits_delete_restore_and_archive_refresh_without_writes(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1);b=buy(client,p,s,4,2)
    baseline=changes(client)
    assert baseline==changes(client)
    assert client.delete(f"/api/v1/operations/{b['id']}").status_code==204
    assert changes(client)['total']==0
    assert client.post(f"/api/v1/operations/{b['id']}/restore").status_code==200
    assert changes(client)==baseline
    assert client.patch(f"/api/v1/operations/{a['id']}",json={'operation_date':'2026-10-03'}).status_code==200
    assert changes(client)['items'][0]['change_percent']=='-25.00'
    assert client.delete(f'/api/v1/operations/catalog-products/{p}').status_code==204
    assert changes(client)['total']==0


def test_single_query_and_zero_baseline(client):
    p,s=setup_product(client)
    a=buy(client,p,s,3,1);buy(client,p,s,4,2)
    from app.db.models import OperationReceiptItem
    gen=app.dependency_overrides[get_db]();db=next(gen)
    engine=db.get_bind()
    try:
        db.get(OperationReceiptItem,a['receipt_items'][0]['id']).line_total=0
        db.commit()
        statements=[]
        def track(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
        event.listen(engine,'before_cursor_execute',track)
        try: data=changes(client)
        finally: event.remove(engine,'before_cursor_execute',track)
        assert len(statements)==1 and statements[0].lstrip().upper().startswith('SELECT')
        assert data['items'][0]['change_percent'] is None and data['items'][0]['direction']==1
        assert data['items'][0]['baseline_cost']=='0.00'
    finally: gen.close()


def test_validation(client):
    endpoint='/api/v1/operations/catalog-products/price-changes'
    for params in [{'basis':'invalid'},{'direction':'invalid'},{'comparison':'invalid'},{'page':0},{'page_size':101},{'date_from':'2026-10-02','date_to':'2026-10-01'}]:
        assert client.get(endpoint,params=params).status_code==422
