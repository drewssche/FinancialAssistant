(() => {
  // Move the existing controls, retaining their listeners, IDs and financial contracts.
  const layouts = new Map();
  const byId = id => document.getElementById(id);
  function disclosure(label, className = '') {
    const node = document.createElement('details');
    node.className = `operation-disclosure ${className}`;
    const summary = document.createElement('summary');
    summary.textContent = label;
    node.append(summary);
    return node;
  }
  function setup(mode) {
    const create = mode === 'create', prefix = create ? 'op' : 'edit';
    const modal = byId(`${mode}Modal`), form = byId(`${mode}OperationForm`);
    if (!modal || !form) return null;
    modal.classList.add('operation-editor');
    const header = modal.querySelector('.modal-head-actions');
    const tools = disclosure('Ещё', 'operation-tools');
    header.prepend(tools);
    const toolMenu = document.createElement("div");
    toolMenu.className = "operation-tools-menu"; tools.append(toolMenu);
    for (const id of [`${mode}ModalReceiptBtn`, `${mode}ModalActivityBtn`, `${mode}SessionRefreshBtn`]) {
      const node = byId(id);
      if (node) toolMenu.append(node);
    }
    const extra = disclosure('Комментарий и дополнительные параметры', 'operation-extra');
    form.append(extra);
    extra.append(byId(`${prefix}Note`), byId(`${prefix}FxSettlementBlock`));
    const preview = modal.querySelector(':scope > .operation-modal-card > .preview-panel');
    const previewDetails = disclosure('Предпросмотр', 'operation-preview');
    if (preview) { preview.before(previewDetails); previewDetails.append(preview); }
    const entry = create ? disclosure('Другие операции: валюта, долг', 'operation-entry') : null;
    if (entry) { form.append(entry); entry.append(byId('createEntryModeSwitch')); }
    const check = disclosure('Сверить сумму чека', 'operation-receipt-check');
    const amount = byId(`${prefix}AmountCompound`), amountAnchor = document.createComment('operation amount');
    amount.before(amountAnchor);
    const category = byId(create ? 'createCategoryField' : 'editCategoryField');
    const categoryAnchor = document.createComment('operation category');
    category.before(categoryAnchor);
    const receipt = byId(`${prefix}ReceiptFields`);
    receipt.append(check);
    const store = document.createElement('label');
    store.className = 'receipt-store';
    store.innerHTML = `<span>Магазин</span><input data-receipt-store="${mode}" aria-label="Магазин чека" placeholder="Выбрать или ввести магазин" list="${mode}ReceiptStores" autocomplete="off"><datalist id="${mode}ReceiptStores"></datalist>`;
    receipt.prepend(store);
    const currency = byId(`${prefix}Currency`), currencyAnchor = document.createComment('operation currency');
    currency.before(currencyAnchor);
    const receiptCurrency = document.createElement('label');
    receiptCurrency.className = 'receipt-currency';
    receiptCurrency.innerHTML = '<span>Валюта</span>';
    store.after(receiptCurrency);
    byId(`${prefix}Amount`).setAttribute('inputmode', 'decimal');
    const layout = {modal, form, extra, entry, check, amount, amountAnchor, category, categoryAnchor, currency, currencyAnchor, receiptCurrency, prefix};
    layouts.set(mode, layout);
    return layout;
  }
  function sync(mode = 'create', reset = false) {
    const view = layouts.get(mode) || setup(mode);
    if (!view) return;
    const {modal, extra, entry, check, amount, amountAnchor, category, categoryAnchor, currency, currencyAnchor, receiptCurrency, prefix} = view;
    const operation = mode === 'edit' || byId('opEntryMode').value === 'operation';
    const store = modal.querySelector('[data-receipt-store]');
    if (store && document.activeElement !== store) store.value = window.App.state[mode === 'create' ? 'createReceiptItems' : 'editReceiptItems']?.[0]?.shop_name || '';
    const receipt = operation && !modal.classList.contains('editing-debt-movement') && byId(`${prefix}OperationMode`).value === 'receipt';
    modal.classList.toggle('is-receipt-editor', receipt);
    modal.classList.toggle('is-other-entry', !operation);
    if (receipt) {
      check.append(amount);
      receiptCurrency.append(currency);
      extra.prepend(category);
    } else {
      amountAnchor.after(amount);
      currencyAnchor.after(currency);
      categoryAnchor.after(category);
    }
    byId(`${prefix}Amount`).placeholder = receipt ? 'Сумма в бумажном чеке (необязательно)' : 'Сумма';
    if (reset) {
      modal.querySelectorAll('.operation-disclosure').forEach(node => { node.open = false; });
      extra.open = Boolean(byId(`${prefix}Note`).value || byId(mode === 'create' ? 'opUseFxSettlement' : 'editUseFxSettlement')?.checked);
      check.open = Boolean(byId(mode === 'create' ? 'receiptDiffValue' : 'editReceiptDiffValue')?.classList.contains('receipt-diff-warn'));
    }
    const plan = mode === 'create' && window.App.state.createFlowMode === 'plan';
    const note = byId(`${prefix}Note`);
    if (plan && note.parentElement !== view.form) extra.before(note);
    if (!plan && note.parentElement !== extra) extra.prepend(note);
    if (plan) modal.querySelector('.operation-preview').open = true;
    extra.querySelector('summary').textContent = plan ? 'Дополнительные параметры' : 'Комментарий и дополнительные параметры';
    extra.classList.toggle('hidden', !operation);
    if (entry) {
      entry.classList.toggle('hidden', byId('createEntryModeSwitch').classList.contains('hidden'));
      if (!operation) entry.open = true;
    }
  }
  window.App.registerRuntimeModule('operation-layout', {sync});
})();
