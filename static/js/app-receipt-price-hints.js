(() => {
  function createReceiptPriceHints(deps) {
    const {state, core, getReceiptItems, getReceiptContext, getReceiptCurrency, getReceiptOperationKind} = deps;
    const records = new WeakMap();
    function context(item, mode) {
      const resuming = mode === 'create' && state.createFlowMode === 'plan' && document.getElementById('planResumeEnabled')?.checked && !document.getElementById('planResumeFields')?.classList.contains('hidden');
      const dateId = mode === 'edit' ? 'editDate' : resuming ? 'planResumeDate' : 'opDate';
      const payload = {
        template_id: Number(item.template_id) || null,
        currency: getReceiptCurrency(mode),
        as_of: core.parseDateInputValue(document.getElementById(dateId)?.value || ''),
        shop_name: item.shop_name || null,
        ...window.App.measurements.snapshot(item),
        variant_id: Number(item.variant_id || item.variant_snapshot?.variant_id) || null,
        exclude_operation_id: mode === 'edit' ? Number(state.editOperationId) || null : null,
      };
      const product = Number(item.product_id) || null;
      const enabled = Boolean(product && payload.template_id && payload.as_of && getReceiptOperationKind(mode) === 'expense');
      return {payload, product, enabled, key: JSON.stringify([product, payload, getReceiptOperationKind(mode), state.token])};
    }
    function invalidate(item, ctx) {
      const old = records.get(item);
      if (old && old.key !== ctx.key) {
        old.controller?.abort();
        records.delete(item);
      }
      return records.get(item);
    }
    function message(item, record, mode) {
      if (!record) return '';
      if (record.loading) return 'Ищем прошлую покупку…';
      if (record.error) return 'Не удалось сравнить цену. Можно повторить.';
      if (record.data?.status === 'unknown_measurements') return 'Укажите единицу продажи и размер упаковки для сопоставления.';
      const old = record.data?.previous;
      if (!old) return 'Прошлой покупки с тем же магазином, валютой и фасовкой нет.';
      const labels = {piece:'шт.', pack:'уп.', kg:'кг', g:'г', l:'л', ml:'мл'};
      const money = value => `${Number(value).toLocaleString('ru-RU', {maximumFractionDigits:4})} ${getReceiptCurrency(mode)}`;
      const basis = labels[item.sale_unit] || 'ед.';
      let result = `${core.formatDateRu(old.recorded_at)}: ${money(old.price)}/${basis}${old.is_discounted ? ' (со скидкой)' : ''}. `;
      const diff = window.App.receiptPricing.compare(item, old);
      if (!diff) return result + 'Введите количество и проверьте сумму позиции.';
      const percent = diff.percent == null ? 'процент не рассчитывается от нулевой цены' : `${diff.percent > 0 ? '+' : ''}${diff.percent.toLocaleString('ru-RU', {maximumFractionDigits:2})}%`;
      result += `Сейчас ${money(diff.currentPrice)}/${basis}: ${diff.direction > 0 ? 'дороже' : diff.direction < 0 ? 'дешевле' : 'без изменения'} (${percent}). `;
      result += `На текущее количество: ${diff.difference > 0 ? '+' : ''}${money(diff.difference)} к стоимости по прошлой цене. `;
      return result + 'Сравнение после скидок; в один день — по порядку записей.';
    }
    function refresh(mode) {
      const list = getReceiptContext(mode).listNode;
      if (!list) return;
      for (const item of getReceiptItems(mode)) {
        const row = list.querySelector(`[data-receipt-item-id="${item.draft_id}"]`);
        if (!row) continue;
        let host = row.querySelector('.receipt-price-hint');
        if (!host) {
          host = document.createElement('div');
          host.className = 'receipt-price-hint';
          host.innerHTML = '<button type="button" class="btn btn-secondary btn-xs" data-receipt-price-hint>Сравнить с прошлой покупкой</button><small role="status" aria-live="polite"></small>';
          row.append(host);
        }
        const ctx = context(item, mode), record = invalidate(item, ctx);
        host.hidden = !ctx.enabled;
        const button = host.querySelector('button');
        button.disabled = Boolean(record?.loading);
        button.textContent = record?.loading ? 'Сравниваем…' : record ? 'Обновить сравнение' : 'Сравнить с прошлой покупкой';
        host.querySelector('small').textContent = message(item, record, mode);
      }
    }
    async function load(button) {
      const row = button.closest('[data-receipt-item-id]'), mode = row.dataset.receiptMode;
      const item = getReceiptItems(mode).find(entry => Number(entry.draft_id) === Number(row.dataset.receiptItemId));
      if (!item) return;
      const ctx = context(item, mode);
      if (!ctx.enabled || invalidate(item, ctx)?.loading) return;
      const record = {key:ctx.key, loading:true, controller:new AbortController()};
      records.set(item, record);
      refresh(mode);
      const current = () => getReceiptItems(mode).includes(item) && context(item, mode).key === ctx.key && records.get(item) === record;
      try {
        const data = await core.requestJson(`/api/v1/operations/catalog-products/${ctx.product}/price-hint`, {
          method:'POST', headers:core.authHeaders(), body:JSON.stringify(ctx.payload), signal:record.controller.signal,
        });
        if (current()) record.data = data;
      } catch (error) {
        if (current() && error.name !== 'AbortError') record.error = true;
      } finally {
        record.loading = false;
        if (current()) refresh(mode);
      }
    }
    // Date/currency controls are outside receipt rows. Clear old comparisons on
    // their native events too; never re-fetch while the user is typing.
    const changed = event => {
      if (['opDate','editDate','opCurrency','editCurrency','planResumeDate','planResumeEnabled','planScheduleMode','opKind','editKind'].includes(event.target.id)) {
        queueMicrotask(() => { refresh('create'); refresh('edit'); });
      }
    };
    document.addEventListener('input', changed);
    document.addEventListener('change', changed);
    return {refresh, load};
  }
  window.App.registerRuntimeModule?.('receipt-price-hints-factory', createReceiptPriceHints);
})();
