import json

import pytest
from playwright.sync_api import expect
from tests.e2e.test_receipt_scan_e2e import start, stub, upload, TEXT
from tests.e2e.test_receipt_picker_store_scope_e2e import static_server_url, page_with_receipt_api_mock


def reviewed(page):
    stub(page);upload(page);page.click('#scanRun')
    expect(page.locator('#scanReview')).to_be_visible()


@pytest.mark.e2e
def test_new_form_resets_and_closed_review_resumes(static_server_url, page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    start(page, static_server_url);reviewed(page)
    page.locator('#scanRows [data-scan-field=name]').first.fill('Исправленное молоко')
    page.click('#scanClose')
    page.evaluate("window.App.getRuntimeModule('operation-modal').closeCreateModal()")
    page.evaluate("document.getElementById('opAmount').value='999';document.getElementById('opDate').value='2026-11-05';document.getElementById('opNote').value='Старый комментарий'")
    page.click('#addOperationCta')
    expect(page.locator('#opAmount')).to_have_value('')
    expect(page.locator('#opNote')).to_have_value('')
    expect(page.locator('#opDate')).to_have_value(page.evaluate('window.App.core.getTodayIso()'))
    assert page.locator('#openReceiptScan').bounding_box()['width'] < 300
    page.screenshot(path='/tmp/fa-compact-scan.png')
    page.click('#openReceiptScan')
    expect(page.locator('#scanRows [data-scan-field=name]').first).to_have_value('Исправленное молоко')
    page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    expect(page.locator('#opAmount')).to_have_value('7.50')
    attachment=page.evaluate("window.App.getRuntimeModule('receipt-scan').payload('create')")
    assert attachment['image'] and attachment['original_text']==TEXT
    assert attachment['review']['rows'][0]['name']=='Исправленное молоко'


@pytest.mark.e2e
@pytest.mark.parametrize('has_photo',[True,False])
def test_saved_receipt_reopens_with_current_operation_and_placeholder(static_server_url,page_with_receipt_api_mock,has_photo):
    page=page_with_receipt_api_mock
    start(page,static_server_url);reviewed(page)
    page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    attachment=page.evaluate("window.App.getRuntimeModule('receipt-scan').payload('create')")
    items=page.evaluate("window.App.getRuntimeModule('operation-modal').getCreateReceiptPayload()")
    if not has_photo:attachment['image']=None
    page.route('**/api/v1/operations/77/receipt-scan',lambda route:route.fulfill(json=attachment))
    page.evaluate("window.App.getRuntimeModule('receipt-scan').saved('create');window.App.getRuntimeModule('operation-modal').closeCreateModal()")
    # Reopened saved form has current amount/date, not stale OCR values.
    page.evaluate("item=>window.App.getRuntimeModule('operation-modal').openEditModal(item)",{
        'id':77,'kind':'expense','amount':'7.50','original_amount':'7.50','currency':'BYN','operation_date':'2026-10-16','note':'Мой комментарий',
        'has_receipt_scan':True,'receipt_items':items})
    page.click('#openSavedReceiptScan')
    expect(page.locator('#scanDate')).to_have_value('2026-10-16')
    expect(page.locator('#scanRows .scan-row')).to_have_count(2)
    expect(page.locator('#scanNoPhoto')).to_be_hidden() if has_photo else expect(page.locator('#scanNoPhoto')).to_be_visible()
    page.click('#scanShowText');expect(page.locator('#scanText')).to_have_value(TEXT);page.click('#scanTextClose')
    page.locator('#scanConfirmed').check();page.click('#scanTransfer');page.click('#scanReplaceYes')
    expect(page.locator('#editAmount')).to_have_value('7.50')
    expect(page.locator('#editNote')).to_have_value('Мой комментарий')
    updated=page.evaluate("window.App.getRuntimeModule('receipt-scan').payload('edit')")
    assert bool(updated['image'])==has_photo
    assert updated['original_text']==TEXT
    page.click('#openSavedReceiptScan');page.click('#scanClose')
    expect(page.locator('#editModal')).to_be_visible()

@pytest.mark.e2e
def test_failed_save_keeps_attachment_and_retry_sends_it_atomically(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock
    start(page,static_server_url);reviewed(page)
    page.locator('#scanConfirmed').check();page.click('#scanTransfer')
    requests=[]
    def save(route):
        if route.request.method!='POST':return route.fallback()
        requests.append(route.request.post_data_json)
        route.fulfill(status=400 if len(requests)==1 else 201,json={'detail':'Проверочная ошибка'} if len(requests)==1 else {'id':77})
    page.route('**/api/v1/operations',save)
    page.evaluate("window.App.state.createReceiptItems[0].code_entries=[]")
    page.click('#submitCreateOperationBtn')
    expect(page.locator('#createModal')).to_be_visible()
    expect(page.locator('#submitCreateOperationBtn')).to_be_enabled()
    assert requests[0]['receipt_scan']['original_text']==TEXT
    assert requests[0]['receipt_scan']['review']['rows'][0]['code_entries']==[]
    page.click('#openReceiptScan');expect(page.locator('#scanReview')).to_be_visible();page.click('#scanClose')
    page.click('#submitCreateOperationBtn')
    expect(page.locator('#createModal')).to_be_hidden()
    assert requests[0]['receipt_scan']==requests[1]['receipt_scan']
    assert page.evaluate("window.App.getRuntimeModule('receipt-scan').payload('create')") is None


@pytest.mark.e2e
def test_settings_photo_stats_and_confirmed_deletion(static_server_url,page_with_receipt_api_mock):
    page=page_with_receipt_api_mock;deleted=[]
    def storage(route):
        if route.request.method=='DELETE':deleted.append(True);route.fulfill(json={'deleted':2,'freed_bytes':204800})
        else:route.fulfill(json={'count':0 if deleted else 2,'bytes':0 if deleted else 204800})
    page.route('**/api/v1/operations/receipt-photos/storage',storage)
    start(page,static_server_url);page.click('#scanClose')
    page.evaluate("window.App.getRuntimeModule('operation-modal').closeCreateModal()")
    page.click('[data-section=settings]');page.click('[data-settings-view=data]')
    expect(page.locator('#receiptPhotoStorage')).to_have_text('2 фото · 200 КБ')
    page.click('#deleteReceiptPhotos')
    expect(page.locator('#confirmText')).to_contain_text('Операции, позиции и распознанный текст останутся')
    assert not deleted
    page.click('#confirmDeleteBtn');expect(page.locator('#receiptPhotoStorage')).to_have_text('Нет сохранённых фото')
    expect(page.locator('#deleteReceiptPhotos')).to_be_disabled()
    assert len(deleted)==1
