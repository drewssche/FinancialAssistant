(() => {
  // Move the existing controls, retaining their listeners, IDs and financial contracts.
  const layouts = new Map();
  const byId = id => document.getElementById(id);
  const desktop = window.matchMedia('(min-width: 900px)');
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
    const extra = disclosure('Комментарий и дополнительные параметры', 'operation-extra');
    form.append(extra);
    extra.append(byId(`${prefix}Note`), byId(`${prefix}FxSettlementBlock`));
    const preview = modal.querySelector(':scope > .operation-modal-card > .preview-panel');
    const previewDetails = disclosure('Предпросмотр', 'operation-preview');
    if (preview) { preview.before(previewDetails); previewDetails.append(preview); }
    const previewButton = document.createElement('button');
    previewButton.type = 'button';
    previewButton.className = 'btn btn-secondary modal-head-icon-btn operation-preview-action';
    previewButton.title = 'Предпросмотр';
    previewButton.setAttribute('aria-label', 'Предпросмотр');
    previewButton.innerHTML = '<svg class="modal-action-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
    previewDetails.id = `${mode}OperationPreview`;
    previewButton.setAttribute('aria-controls', previewDetails.id);
    previewButton.setAttribute('aria-expanded', 'false');
    previewButton.addEventListener('click', () => {
      previewDetails.open = !previewDetails.open;
      if (previewDetails.open) previewDetails.scrollIntoView({block: 'nearest'});
    });
    previewDetails.addEventListener('toggle', () => previewButton.setAttribute('aria-expanded', String(previewDetails.open)));
    header.prepend(previewButton);
    const entry = create ? disclosure('Другие операции: валюта, долг', 'operation-entry') : null;
    if (entry) { form.append(entry); entry.append(byId('createEntryModeSwitch')); }
    const check = disclosure('Сверить сумму чека', 'operation-receipt-check');
    check.querySelector('summary').addEventListener('click', event => {
      if (desktop.matches) event.preventDefault();
    });
    const amount = byId(`${prefix}AmountCompound`), amountAnchor = document.createComment('operation amount');
    amount.before(amountAnchor);
    const category = byId(create ? 'createCategoryField' : 'editCategoryField');
    const categoryAnchor = document.createComment('operation category');
    category.before(categoryAnchor);
    const receipt = byId(`${prefix}ReceiptFields`);
    receipt.append(check);
    const store = document.createElement('label');
    store.className = 'receipt-store';
    store.innerHTML = `<span>Магазин</span><input data-receipt-store="${mode}" aria-label="Магазин чека" placeholder="Выбрать или ввести магазин" autocomplete="off">`;
    receipt.prepend(store);
    window.App.getRuntimeModule('operation-store-picker').bind(store, mode);
    const currency = byId(`${prefix}Currency`), currencyAnchor = document.createComment('operation currency');
    currency.before(currencyAnchor);
    const receiptCurrency = document.createElement('label');
    receiptCurrency.className = 'receipt-currency';
    receiptCurrency.innerHTML = '<span>Валюта</span>';
    store.after(receiptCurrency);
    byId(`${prefix}Amount`).setAttribute('inputmode', 'decimal');
    const sidebar = document.createElement('aside');
    sidebar.className = 'operation-summary-column';
    sidebar.setAttribute('aria-label', 'Сумма и комментарий');
    const noteLabel = document.createElement('label');
    noteLabel.className = 'operation-note-label';
    noteLabel.innerHTML = `<span>Комментарий</span>`;
    sidebar.append(noteLabel);
    const receiptSummary = receipt.querySelector('.receipt-summary');
    const layout = {modal, form, extra, entry, check, amount, amountAnchor, category, categoryAnchor, currency, currencyAnchor, receiptCurrency, prefix, sidebar, noteLabel, receipt, receiptSummary, previewDetails};
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
    check.querySelector('summary').textContent = desktop.matches ? 'Оплачено по чеку' : 'Сверить сумму чека';
    check.querySelector('summary').tabIndex = desktop.matches ? -1 : 0;
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
    byId(`${prefix}Amount`).placeholder = receipt ? (desktop.matches ? 'Необязательно' : 'Сумма в бумажном чеке (необязательно)') : 'Сумма';
    if (reset) {
      modal.querySelectorAll('.operation-disclosure').forEach(node => { node.open = false; });
      extra.open = Boolean((!desktop.matches && byId(`${prefix}Note`).value) || byId(mode === 'create' ? 'opUseFxSettlement' : 'editUseFxSettlement')?.checked);
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
    // The same fields stay in the form across viewport changes; no draft is copied.
    if (desktop.matches) {
      if (entry) { view.form.prepend(entry); entry.open = true; }
      view.form.insertBefore(view.sidebar, extra);
      view.noteLabel.append(note);
      view.sidebar.classList.toggle('hidden', !operation);
      if (receipt) {
        view.sidebar.prepend(view.receiptSummary, check);
        check.open = true;
      } else {
        view.receipt.append(view.receiptSummary, check);
      }
      extra.querySelector('summary').textContent = 'Дополнительные параметры';
    } else {
      if (entry) view.form.append(entry);
      view.receipt.append(view.receiptSummary, check);
      view.sidebar.remove();
      if (plan) extra.before(note); else extra.prepend(note);
    }
  }
  desktop.addEventListener('change', () => {
    for (const [mode, view] of layouts) {
      if (!desktop.matches) {
        view.check.open = Boolean(byId(mode === 'create' ? 'receiptDiffValue' : 'editReceiptDiffValue')?.classList.contains('receipt-diff-warn'));
        if (view.entry) view.entry.open = byId('opEntryMode').value !== 'operation';
      }
      sync(mode);
    }
  });
  window.App.registerRuntimeModule('operation-layout', {sync});
})();
