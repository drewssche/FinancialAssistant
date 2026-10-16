"""Product size drives barcode selection; there is no separate packages workspace."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_product_primary_codes_e2e import setup, CODE, barcode
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock


@pytest.mark.e2e
@pytest.mark.parametrize('width',[320,390,1440])
def test_size_edit_is_main_form_only_and_keeps_original_barcode(static_server_url,page_with_receipt_api_mock,width):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,width,many=True)
    expect(barcode(p)).to_have_value(CODE)
    expect(p.locator('[data-product-tab=packages]')).to_have_count(0)
    expect(p.locator('.package-tasks')).to_have_count(0)
    expect(p.locator('#catalogProductTabs button')).to_have_count(4)
    size=p.locator('.catalog-product-measurements .measurement-editor input')
    size.fill('800')
    expect(barcode(p)).to_have_value('')
    expect(p.locator('#catalogProductSizeNote')).to_contain_text('Размер изменён')
    p.locator('[data-product-tab=offers]').click()
    barcode(p).fill('5901234123457')
    p.locator('[data-product-tab=offers]').click();p.locator('[data-product-tab=product]').click()
    expect(size).to_have_value('800')
    expect(barcode(p)).to_have_value('5901234123457')
    assert writes==[]
    p.locator('.catalog-product-measurements').scroll_into_view_if_needed()
    p.screenshot(path=f'/tmp/fa-simple-size-{width}.png')
    p.locator('#submitCatalogProductBtn').click()
    expect(p.locator('#catalogProductModal')).to_be_hidden()
    assert writes[-1]['package_quantity']=='800'
    assert writes[-1]['codes']['barcodes']==[{'variant_id':None,'codes':['5901234123457']}]
