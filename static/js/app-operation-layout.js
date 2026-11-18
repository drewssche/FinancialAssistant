(() => {
  // Move the existing controls, retaining their listeners, IDs and financial contracts.
  const layouts = new Map();
  const byId = id => document.getElementById(id);
  const desktop = window.matchMedia('(min-width: 900px)');
  function panel(label, className = '') {
    const node = document.createElement('section');
    node.className = `operation-panel ${className}`;
    const heading = document.createElement('div');
    heading.className = 'operation-panel-label';
    heading.textContent = label;
    node.append(heading);
    return node;
  }
  function setupSimpleForm(mode, prefix, form) {
    const fields = document.createElement('div');
    fields.className = 'operation-basic-fields';
    fields.innerHTML = `<div class="basic-amount"><label for="${prefix}Amount">Сумма</label></div>
      <div class="basic-kind"></div>
      <div class="basic-category"><label for="${prefix}CategorySearch">Категория</label></div>
      <div class="basic-date"><label for="${prefix}Date">Дата</label><div class="basic-date-controls">
        <button type="button" class="btn btn-secondary btn-icon" data-date-step-target="${prefix}Date" data-date-step="today" title="Сегодня" aria-label="Сегодня">${window.App.icons.svg('calendarToday')}</button>
      </div></div>`;
    form.prepend(fields);
    const actions = document.createElement('div');
    actions.className = 'operation-item-actions';
    const details = document.createElement('details');
    details.className = 'operation-note-details';
    details.innerHTML = '<summary>Комментарий и теги</summary>';
    form.append(actions, details);
    const kind = byId(mode + 'KindSwitch'), date = byId(prefix + 'DateField'), format = byId(mode + 'OperationModeSwitch');
    const slots = [kind, date, format].map(control => {
      const anchor = document.createComment(control.id);
      control.before(anchor);
      return {control, anchor};
    });
    const addItem = format.querySelector('[data-operation-mode="receipt"]');
    const exchange = form.querySelector('[data-entry-mode="currency"]');
    return (simple, view, reset) => {
      fields.hidden = actions.hidden = details.hidden = !simple;
      const scan = mode === 'create' && byId('openReceiptScan');
      addItem.textContent = simple ? 'Добавить товар' : 'Чек с товарами';
      if (exchange) exchange.textContent = simple ? 'Обмен валюты' : 'Валюта';
      if (!simple) {
        for (const {control, anchor} of slots) anchor.after(control);
        if (scan && actions.contains(scan)) form.before(scan);
        return;
      }
      fields.querySelector('.basic-amount').append(view.amount);
      fields.querySelector('.basic-kind').append(kind);
      fields.querySelector('.basic-category').append(view.category);
      fields.querySelector('.basic-date-controls').prepend(date);
      for (const option of view.currency.options) option.label = option.value;
      actions.append(format);
      if (scan) actions.append(scan);
      view.extra.before(actions, details);
      view.noteLabel.append(byId(prefix + 'Note'));
      details.append(view.noteLabel, byId(prefix + 'TagsField'));
      if (reset) details.open = Boolean(byId(prefix + 'Note').value.trim() || byId(prefix + 'Tags').value.trim());
      if (view.entry) view.extra.after(view.entry);
      view.sidebar.remove();
    };
  }
  function setup(mode) {
    const create = mode === 'create', prefix = create ? 'op' : 'edit';
    const modal = byId(`${mode}Modal`), form = byId(`${mode}OperationForm`);
    if (!modal || !form) return null;
    modal.classList.add('operation-editor');
    const header = modal.querySelector('.modal-head-actions');
    const extra = panel('Комментарий и дополнительные параметры', 'operation-extra');
    form.append(extra);
    extra.append(byId(`${prefix}Note`));
    const preview = modal.querySelector(':scope > .operation-modal-card > .preview-panel');
    const previewDetails = panel('Предпросмотр', 'operation-preview');
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
      previewDetails.hidden = !previewDetails.hidden;
      syncPreview();
      if (!previewDetails.hidden) previewDetails.scrollIntoView({block: 'nearest'});
    });
    const syncPreview = () => {
      const on = !previewDetails.hidden;
      previewButton.setAttribute('aria-expanded', String(on));
      previewButton.setAttribute('aria-pressed', String(on));
      previewButton.classList.toggle('is-active', on);
      previewButton.title = on ? 'Скрыть предпросмотр' : 'Показать предпросмотр';
      previewButton.setAttribute('aria-label', previewButton.title);
    };
    previewDetails.hidden = true; syncPreview();
    header.prepend(previewButton);
    const entry = create ? panel('Другие операции: валюта, долг', 'operation-entry') : null;
    if (entry) { form.append(entry); entry.append(byId('createEntryModeSwitch')); }
    const check = panel('Сверить сумму чека', 'operation-receipt-check');
    const amount = byId(`${prefix}AmountCompound`), amountAnchor = document.createComment('operation amount');
    amount.before(amountAnchor);
    const category = byId(create ? 'createCategoryField' : 'editCategoryField');
    const categoryAnchor = document.createComment('operation category');
    category.before(categoryAnchor);
    const receipt = byId(`${prefix}ReceiptFields`);
    receipt.append(check);
    const store = document.createElement('div');
    store.className = 'receipt-store';
    store.innerHTML = `<span>Магазин</span><input data-receipt-store="${mode}" aria-label="Магазин чека" placeholder="Выбрать или ввести магазин" autocomplete="off">`;
    const storeInput = store.querySelector('input');
    const storeRow = document.createElement('div'); storeRow.className = 'receipt-store-input-row';
    store.append(storeRow); storeRow.append(storeInput);
    receipt.prepend(store);
    window.App.getRuntimeModule('operation-store-picker').bind(store, mode);
    const currency = byId(`${prefix}Currency`), currencyAnchor = document.createComment('operation currency');
    currency.before(currencyAnchor);
    const receiptCurrency = document.createElement('span');
    receiptCurrency.className = 'receipt-currency-fallback';
    storeRow.append(receiptCurrency);
    byId(`${prefix}Amount`).setAttribute('inputmode', 'decimal');
    const sidebar = document.createElement('aside');
    sidebar.className = 'operation-summary-column';
    sidebar.setAttribute('aria-label', 'Сумма и комментарий');
    const noteLabel = document.createElement('label');
    noteLabel.className = 'operation-note-label';
    noteLabel.innerHTML = `<span>Комментарий</span>`;
    sidebar.append(noteLabel);
    const receiptSummary = receipt.querySelector('.receipt-summary');
    const simpleForm = setupSimpleForm(mode, prefix, form);
    const layout = {modal, form, extra, entry, check, amount, amountAnchor, category, categoryAnchor, currency, currencyAnchor, receiptCurrency, prefix, sidebar, noteLabel, receipt, receiptSummary, previewDetails, syncPreview, simpleForm};
    layouts.set(mode, layout);
    return layout;
  }
  function placeReceiptCurrency(mode) {
    const view = layouts.get(mode);
    if (!view?.modal.classList.contains('is-receipt-editor')) return;
    const first = view.receipt.querySelector('.receipt-item-row');
    const slot = first?.matches('.receipt-item-empty.is-compact') ? null : first?.querySelector('[data-receipt-currency-slot]');
    const host = slot || view.receiptCurrency;
    for (const option of view.currency.options) option.label = option.value;
    const receiptCurrency = mode === 'edit' && window.App.state.editReceiptCurrency;
    if (receiptCurrency) {
      if (slot) slot.textContent = receiptCurrency;
      view.currencyAnchor.after(view.currency);
      view.currency.setAttribute('aria-label', 'Валюта оплаты');
      view.currency.title = 'Валюта оплаты';
      return;
    }
    if (view.currency.parentElement !== host) host.append(view.currency);
    view.currency.setAttribute('aria-label', 'Валюта всего чека');
    view.currency.title = 'Валюта всего чека';
  }
  function sync(mode = 'create', reset = false) {
    const view = layouts.get(mode) || setup(mode);
    if (!view) return;
    const {modal, extra, entry, check, amount, amountAnchor, category, categoryAnchor, currency, currencyAnchor, prefix} = view;
    const operation = mode === 'edit' || byId('opEntryMode').value === 'operation';
    const store = modal.querySelector('[data-receipt-store]');
    if (store && document.activeElement !== store) store.value = window.App.state[mode === 'create' ? 'createReceiptItems' : 'editReceiptItems']?.[0]?.shop_name || '';
    const receipt = operation && !modal.classList.contains('editing-debt-movement') && byId(`${prefix}OperationMode`).value === 'receipt';
    check.querySelector('.operation-panel-label').textContent = desktop.matches ? 'Оплачено по чеку' : 'Сверить сумму чека';
    check.querySelector('.operation-panel-label').tabIndex = -1;
    modal.classList.toggle('is-receipt-editor', receipt);
    modal.classList.toggle('is-other-entry', !operation);
    if (receipt) {
      check.append(amount);
      placeReceiptCurrency(mode);
      extra.prepend(category);
    } else {
      amountAnchor.after(amount);
      currencyAnchor.after(currency);
      for (const option of currency.options) option.removeAttribute('label');
      currency.setAttribute('aria-label', 'Валюта суммы');
      if (currency.title === 'Валюта всего чека') currency.title = '';
      categoryAnchor.after(category);
    }
    byId(`${prefix}Amount`).placeholder = receipt ? (desktop.matches ? 'Необязательно' : 'Сумма в бумажном чеке (необязательно)') : 'Сумма';
    if (reset) { view.previewDetails.hidden = true; view.syncPreview(); }
    const plan = mode === 'create' && window.App.state.createFlowMode === 'plan';
    const simple = operation && !receipt && !plan && !modal.classList.contains('editing-debt-movement');
    modal.classList.toggle('is-simple-operation', simple);
    if (mode === 'create' && byId('openReceiptScan')) byId('openReceiptScan').hidden = !operation || plan;
    const tagsField = byId(`${prefix}TagsField`);
    tagsField.hidden = !operation || modal.classList.contains("editing-debt-movement");
    const note = byId(`${prefix}Note`);
    if (plan && note.parentElement !== view.form) extra.before(note);
    if (!plan && note.parentElement !== extra) extra.prepend(note);
    extra.querySelector('.operation-panel-label').textContent = plan ? 'Дополнительные параметры' : 'Комментарий и дополнительные параметры';
    extra.classList.toggle('hidden', !operation);
    if (entry) {
      entry.classList.toggle('hidden', byId('createEntryModeSwitch').classList.contains('hidden'));
    }
    // The same fields stay in the form across viewport changes; no draft is copied.
    if (desktop.matches) {
      if (entry) view.form.prepend(entry);
      view.form.insertBefore(view.sidebar, extra);
      view.noteLabel.append(note);
      view.sidebar.append(view.noteLabel, tagsField);
      view.sidebar.classList.toggle('hidden', !operation);
      if (receipt) {
        view.sidebar.prepend(view.receiptSummary, check);
      } else {
        view.receipt.append(view.receiptSummary, check);
      }
      extra.querySelector('.operation-panel-label').textContent = 'Дополнительные параметры';
    } else {
      if (entry) view.form.prepend(entry);
      view.receipt.append(view.receiptSummary, check);
      view.sidebar.remove();
      if (plan) extra.before(note, tagsField); else extra.prepend(note, tagsField);
    }
    view.simpleForm(simple, view, reset);
  }
  desktop.addEventListener('change', () => {
    for (const mode of layouts.keys()) {
      sync(mode);
    }
  });
  window.App.registerRuntimeModule('operation-layout', {sync, placeReceiptCurrency});
})();
