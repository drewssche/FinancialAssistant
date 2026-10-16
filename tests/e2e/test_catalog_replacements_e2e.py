"""Changing size replaces the retired manual replacement wizard."""
import pytest
from playwright.sync_api import expect
from tests.e2e.test_product_primary_codes_e2e import setup, CODE
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock


@pytest.mark.e2e
def test_cancel_size_change_and_legacy_tab_fallback(static_server_url,page_with_receipt_api_mock):
    p=page_with_receipt_api_mock;writes=setup(p,static_server_url,390)
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    calls=[]
    p.on('request',lambda r:calls.append(r.url) if '/package-replacements' in r.url else None)
    p.locator('.catalog-product-measurements .measurement-editor input').fill('800')
    p.locator('#closeCatalogProductModalBtn').click()
    p.evaluate("window.App.getRuntimeModule('catalog-products').openEditor(401,{tab:'packages'})")
    expect(p.locator('#catalogProductForm')).to_be_visible()
    expect(p.locator('.catalog-product-measurements .measurement-editor input')).to_have_value('900')
    expect(p.locator('#catalogProductBarcode')).to_have_value(CODE)
    assert writes==[] and calls==[]
