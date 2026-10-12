(() => {
  const {core} = window.App, node = id => document.getElementById(id), esc = value => core.escapeHtml(String(value ?? ''));
  const number = value => Number(value).toLocaleString('ru-RU', {maximumFractionDigits:4});
  const pct = value => value == null ? 'нет базы для %' : `${Number(value)>0?'+':''}${number(value)}%`;
  const unit = value => ({kg:'кг',l:'л',piece:'шт.'}[value] || value);
  let product = null, data = null, generation = 0, controller = null, bound = false, dirty = false, saving = false;
  const url = () => `/api/v1/operations/catalog-products/${product.id}/package-replacements`;
  function render() {
    const variants = data?.variants || [];
    for (const id of ['catalogReplacementOld','catalogReplacementNew']) {
      const selected = node(id).value;
      node(id).innerHTML = '<option value="">Выберите фасовку</option>'+variants.map(v => `<option value="${Number(v.id)}">${esc(v.name)} · ${esc(window.App.measurements.summary(v))}${v.is_archived?' · архив':''}</option>`).join('');
      node(id).value = selected;
    }
    node('catalogReplacementsList').innerHTML = (data.items || []).map(r => `<article class="catalog-replacement-card">
      <strong>${esc(r.old_snapshot.name)} → ${esc(r.new_snapshot.name)}</strong>
      <small>${esc(core.formatDateRu(r.effective_date))} · ${esc(r.note || 'Подтверждено вами')}</small>
      <p>${esc(number(r.old_volume))} → ${esc(number(r.new_volume))} ${esc(unit(r.unit))}: <strong>${esc(pct(r.volume_change_percent))}</strong>.</p>
      <p class="muted-small">При прежней цене упаковки цена за ${esc(unit(r.unit))} изменилась бы на ${esc(pct(r.constant_package_price_change_percent))}. Это расчёт, а не наблюдение цены.</p>
      ${(r.comparisons || []).map(c => `<div class="catalog-replacement-comparison"><strong>${esc(c.shop_name || 'Без магазина')} · ${esc(c.currency)}</strong>
        <p>Оплачено за упаковку: ${esc(number(c.old.price))} → ${esc(number(c.new.price))} (${esc(pct(c.package_price_change_percent))}).<br>За ${esc(unit(r.unit))}: ${esc(number(c.old.normalized_price))} → ${esc(number(c.new.normalized_price))} <strong>(${esc(pct(c.normalized_price_change_percent))})</strong>.</p>
        <small>Скидки учтены${c.old.is_discounted?' · старая со скидкой':''}${c.new.is_discounted?' · новая со скидкой':''}. Обычная цена за ${esc(unit(r.unit))}: ${c.regular_normalized_change_percent == null ? 'нет данных для сравнения' : esc(pct(c.regular_normalized_change_percent))}.</small>
        <div class="row"><button type="button" class="btn btn-secondary btn-xs" data-product-purchase-id="${Number(c.old.operation_id)}">Старый чек · ${esc(core.formatDateRu(c.old.recorded_at))}</button><button type="button" class="btn btn-secondary btn-xs" data-product-purchase-id="${Number(c.new.operation_id)}">Новый чек · ${esc(core.formatDateRu(c.new.recorded_at))}</button></div>
      </div>`).join('') || '<p class="muted-small">Нет пары сопоставимых покупок. В чеках должны быть явно выбраны эти фасовки с теми же размерами, магазином и валютой.</p>'}
      <button type="button" class="btn btn-secondary btn-xs" data-replacement-remove="${Number(r.id)}">Отменить подтверждение</button>
    </article>`).join('') || '<p class="muted-small">Подтверждённых замен пока нет. Фасовки можно добавить в блоке ниже.</p>';
  }
  async function load() {
    if (!product || saving) return;
    controller?.abort(); controller = new AbortController(); const token = ++generation;
    node('catalogReplacementsStatus').textContent = 'Загрузка…';
    node('catalogReplacementsBody').classList.add('hidden');
    try {
      const response = await core.requestJson(url(), {headers:core.authHeaders(),signal:controller.signal});
      if (token !== generation) return;
      data = response; render(); node('catalogReplacementsBody').querySelectorAll('button,input,select').forEach(b => b.disabled = false); node('catalogReplacementConfirmed').checked = false;
      node('catalogReplacementsStatus').textContent = 'Размеры подтверждённых замен сохранены на момент подтверждения. Цены читаются из актуальных чеков.';
      node('catalogReplacementsBody').classList.remove('hidden');
    } catch (error) {if (token === generation && error.name !== 'AbortError') node('catalogReplacementsStatus').textContent = `Не удалось загрузить: ${error.message}. Нажмите «Обновить данные».`;}
  }
  async function mutate(path, options) {
    if (saving) return;
    const token = generation; saving = true;
    node('catalogReplacementsBody').querySelectorAll('button,input,select').forEach(b => b.disabled = true);
    try {
      const response = await core.requestJson(path, {...options,headers:core.authHeaders()});
      window.App.getRuntimeModule('catalog-products').invalidate();
      if (token !== generation) return;
      data = response; dirty = false; node('catalogReplacementForm').reset(); node('catalogReplacementDate').value = core.getTodayIso(); render();
      node('catalogReplacementsStatus').textContent = 'Сохранено. Чеки и фасовки каталога не изменены.';
    } catch (error) {if (token === generation) node('catalogReplacementsStatus').textContent = `Не удалось сохранить: ${error.message}`;}
    finally {if (token === generation) {saving = false; node('catalogReplacementsBody').querySelectorAll('button,input,select').forEach(b => b.disabled = false);}}
  }
  function bind() {
    if (bound) return; bound = true;
    document.addEventListener('app:activity-changed', event => {
      const {method,path} = event.detail || {};
      if (!product || saving || !['POST','PUT','PATCH','DELETE'].includes(method)) return;
      if (!/^\/api\/v1\/operations(?:\/\d+)?$/.test(path || '') && !String(path).startsWith(`/api/v1/operations/catalog-products/${product.id}/variants`)) return;
      generation++; controller?.abort(); data = null;
      node('catalogReplacementsList').innerHTML = '<p class="muted-small">Данные изменились — обновите сравнение.</p>';
      node('catalogReplacementsStatus').textContent = 'Чеки или фасовки изменились. Нажмите «Обновить данные», черновик останется.';
    });
    node('catalogReplacementsDetails').addEventListener('toggle', () => {if (node('catalogReplacementsDetails').open && product && !data) load();});
    node('catalogReplacementsRefresh').addEventListener('click', load);
    node('catalogReplacementForm').addEventListener('input', event => {dirty = true; if (['catalogReplacementOld','catalogReplacementNew','catalogReplacementDate'].includes(event.target.id)) node('catalogReplacementConfirmed').checked = false;});
    node('catalogReplacementForm').addEventListener('submit', event => {
      event.preventDefault(); if (!data || !product) return;
      const old = data.variants.find(v => v.id === Number(node('catalogReplacementOld').value));
      const next = data.variants.find(v => v.id === Number(node('catalogReplacementNew').value));
      if (!old || !next || !node('catalogReplacementConfirmed').checked) return;
      mutate(url(), {method:'POST',body:JSON.stringify({old_variant_id:old.id,new_variant_id:next.id,
        effective_date:node('catalogReplacementDate').value,note:node('catalogReplacementNote').value || null,
        confirmed:true,expected_old:old,expected_new:next})});
    });
    node('catalogReplacementsList').addEventListener('click', event => {
      const button = event.target.closest('[data-replacement-remove]');
      if (!button || !product) return;
      if (button.dataset.confirm !== 'yes') {button.dataset.confirm='yes';button.textContent='Отменить эту связь? Чеки сохранятся';return;}
      mutate(`${url()}/${Number(button.dataset.replacementRemove)}`, {method:'DELETE'});
    });
  }
  function close() {generation++; controller?.abort(); product=null;data=null;dirty=false;saving=false;}
  window.App.registerRuntimeModule('catalog-replacements', {
    open(value) {close();bind();product=value;node('catalogReplacementsDetails').open=false;node('catalogReplacementsDetails').classList.toggle('hidden',!value);node('catalogReplacementsBody').querySelectorAll('button,input,select').forEach(b => b.disabled = false);node('catalogReplacementForm').reset();node('catalogReplacementDate').value=core.getTodayIso();node('catalogReplacementsBody').classList.add('hidden');},
    refresh(value) {product=value;if (dirty || saving) return;data=null;if(node('catalogReplacementsDetails').open) load();},
    close, cleanup:close,
  });
})();
