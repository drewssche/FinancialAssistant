import re
import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock, _login, _ensure_categories_loaded, _expand_receipt_row
from tests.e2e.test_receipt_scan_e2e import start, stub, upload


def check_footer(page, picker, width):
    create=picker.locator('.picker-create-footer .chip-btn-create')
    expect(create).to_be_visible()
    body=picker.locator('.picker-scroll-options')
    assert body.evaluate('n=>n.scrollHeight>n.clientHeight+10')
    body.hover()
    page.wait_for_timeout(350)
    bounds=create.bounding_box()
    assert bounds['x']>=0 and bounds['x']+bounds['width']<=width+1
    assert picker.evaluate('n=>n.scrollHeight<=n.clientHeight+1 && n.scrollWidth<=n.clientWidth+1')
    body.hover()
    page.mouse.wheel(0,600)
    page.wait_for_timeout(200)
    assert body.evaluate('n=>n.scrollTop>0')
    assert abs(create.bounding_box()['y']-bounds['y'])<1
    assert create.evaluate('n=>{let r=n.getBoundingClientRect();return n.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}')
    return create


@pytest.mark.e2e
@pytest.mark.parametrize('width,height',[(320,640),(390,400),(1440,1000)])
def test_scan_source_footer_keyboard(static_server_url,page_with_receipt_api_mock,width,height):
    p=page_with_receipt_api_mock;start(p,static_server_url,width);stub(p);upload(p);p.click('#scanRun')
    expect(p.locator('#scanShop')).to_be_visible()
    p.set_viewport_size({'width':width,'height':height})
    p.evaluate("window.App.state.itemSources=Array.from({length:30},(_,i)=>({id:500+i,name:'Магазин '+i}))")
    field=p.locator('#scanShop');field.fill('Магазин')
    picker=p.locator('#scanReceiptStoreOptions');create=check_footer(p,picker,width)
    field.press('ArrowUp');expect(create).to_have_class(re.compile('is-focused'))
    field.press('Enter');expect(picker).to_be_hidden();expect(field).to_have_value('Магазин')


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
@pytest.mark.parametrize('kind',['category','row_category','row_source'])
def test_category_and_source_footers(static_server_url,page_with_receipt_api_mock,width,kind):
    p=page_with_receipt_api_mock;p.set_viewport_size({'width':width,'height':844})
    p.route('**/api/v1/operations/item-sources*',lambda r:r.fulfill(json={'items':[{'id':600+i,'name':'Магазин '+str(i)+' с длинным названием','is_archived':False} for i in range(70)],'total':70,'page':1,'page_size':500}))
    p.goto(static_server_url+'/static/index.html');_login(p);_ensure_categories_loaded(p)
    p.evaluate("""()=>{window.App.state.categories=Array.from({length:70},(_,i)=>({id:500+i,kind:'expense',name:'Продукты '+i+' с длинным названием',icon:'🥗'}));
    window.App.state.itemSources=Array.from({length:70},(_,i)=>({id:600+i,name:'Магазин '+i+' с длинным названием'}));} """)
    p.click('#addOperationCta')
    if kind=='category':
        field=p.locator('#opCategorySearch');picker=p.locator('#createCategoryPickerBlock');query='Продукты'
    else:
        p.click('#createOperationModeSwitch [data-operation-mode=receipt]')
        row=p.locator('.receipt-item-row').first;_expand_receipt_row(row)
        field=row.locator('[data-receipt-field="'+('category_search' if kind=='row_category' else 'shop_name')+'"]')
        picker=row.locator('.receipt-category-picker' if kind=='row_category' else '.receipt-shop-picker')
        query='Продукты' if kind=='row_category' else 'Магазин'
    field.fill(query);field.evaluate("n=>n.scrollIntoView({block:'start'})")
    create=check_footer(p,picker,width)
    p.screenshot(path=f'/tmp/fa-{kind}-footer-{width}.png')
    create.click()
    if kind=='row_source': expect(field).to_have_value(query)
    else: expect(p.locator('#createCategoryModal')).to_be_visible()


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_catalog_source_footer(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;p.set_viewport_size({'width':width,'height':844})
    p.route('**/api/v1/operations/item-sources*',lambda r:r.fulfill(json={'items':[{'id':600+i,'name':'Магазин '+str(i)+' с длинным названием','is_archived':False} for i in range(70)],'total':70,'page':1,'page_size':500}))
    p.goto(static_server_url+'/static/index.html');_login(p)
    p.evaluate("window.App.getRuntimeModule('item-catalog').openItemTemplateModal()")
    p.evaluate("()=>{window.App.state.itemSources=Array.from({length:70},(_,i)=>({id:600+i,name:'Магазин '+i}));window.App.state.itemSourcesLoaded=true;}")
    field=p.locator('#itemTemplateSourceSearch');field.fill('Магазин')
    create=check_footer(p,p.locator('#itemTemplateSourcePickerBlock'),width)
    create.click()
    expect(field).to_have_value('Магазин')
    expect(p.locator('#itemTemplateSourcePickerBlock')).to_be_hidden()
