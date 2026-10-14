(() => {
  const {core} = window.App;
  const node = (id) => document.getElementById(id), esc = (v) => core.escapeHtml(String(v ?? ""));
  const units = window.App.measurements.units;
  const number = (v) => Number(v).toLocaleString("ru-RU", {maximumFractionDigits: 4});
  const pct = (v) => v == null ? "нет базы для %" : `${Number(v) > 0 ? "+" : ""}${number(v)}%`;
  let bound = false, controller = null, generation = 0, page = 0, rows = [], total = 0, params = null;
  let dirty = false;
  const form = () => node("catalogPriceChangesForm");
  let active = false;
  function warnings(r) {
    return [r.reference_is_discounted || r.latest_is_discounted ? "Есть скидка" : "",
      r.package_changed ? "Фасовка менялась" : "",
      !units[r.unit] || (r.unit === "pack" && !r.package_quantity) ? "Единица / фасовка неизвестна" : ""].filter(Boolean);
  }
  function comparisonDetails(r) {
    return `<p><strong>${esc(r.product_name)}</strong> · ${esc(r.shop_name || "Магазин не указан")} · ${esc(r.offer_name)}<br>${esc(core.formatDateRu(r.reference_date))} → ${esc(core.formatDateRu(r.latest_date))}</p>
      <p>За период: ${esc(pct(r.period_change_percent))} · последний шаг: ${esc(pct(r.last_change_percent))}<br>Повышений: ${Number(r.increases)} · снижений: ${Number(r.decreases)} · позиций чека: ${Number(r.observations_count)}</p>
      <p>Последний купленный объём по прежней → последней цене:<br><strong>${esc(number(r.baseline_cost))} → ${esc(number(r.latest_cost))} ${esc(r.currency)}</strong> · разница ${Number(r.cost_difference) > 0 ? "+" : ""}${esc(number(r.cost_difference))} ${esc(r.currency)}</p>
      ${warnings(r).length ? `<p class="catalog-price-caution">${esc(warnings(r).join(" · "))}. ${r.package_changed ? "Замена упаковки не подтверждена. " : ""}Сопоставимость требует проверки.</p>` : ""}`;
  }
  function render() {
    const offers = new Map();
    const key = r => JSON.stringify([r.product_id, r.shop_name]);
    for (const r of rows) { if (!offers.has(key(r))) offers.set(key(r), new Set()); offers.get(key(r)).add(r.template_id); }
    node("catalogPriceChangesList").innerHTML = rows.map((r, index) => {
      const packageLabel = r.package_quantity ? `${number(r.package_quantity)} ${units[r.package_unit] || r.package_unit}` : "";
      return `<article class="catalog-price-change">
        <div class="catalog-price-change-name"><strong>${esc(r.product_name)}</strong><small>${esc(r.shop_name || "Магазин не указан")}${packageLabel ? ` · ${esc(packageLabel)}` : ""}</small>
          ${offers.get(key(r)).size > 1 ? `<small>${esc(r.offer_name)}</small>` : ""}
          ${warnings(r).length ? `<div class="catalog-price-flags">${warnings(r).map(label => `<span>${esc(label)}</span>`).join("")}</div>` : ""}</div>
        <div class="catalog-price-change-value"><strong>${esc(number(r.reference_price))} → ${esc(number(r.latest_price))} ${esc(r.currency)}</strong><small>за ${esc(units[r.unit] || "ед. (не указана)")}</small></div>
        <strong class="catalog-price-change-percent ${r.direction > 0 ? "is-up" : r.direction < 0 ? "is-down" : ""}">${r.direction > 0 ? "↑" : r.direction < 0 ? "↓" : "="} ${esc(pct(r.change_percent))}</strong>
        <button type="button" class="btn btn-secondary btn-icon" data-open-price-change="${index}" title="График и чеки" aria-label="График и чеки: ${esc(r.product_name)}">${window.App.icons.svg("chart")}</button>
      </article>`;
    }).join("") || '<p class="empty">Нет сравнений с двумя сопоставимыми покупками по этим условиям.</p>';
    node("catalogPriceChangesMore").hidden = dirty || rows.length >= total;
  }
  function setActive(value) {
    active = value;
    node("catalogPriceChanges")?.classList.toggle("hidden", !active);
    if (active) { bind(); load(); } else { generation++; controller?.abort(); }
  }
  async function load(more = false) {
    if (!active) return;
    controller?.abort(); controller = new AbortController(); const token = ++generation;
    if (!more) {
      params = new URLSearchParams(new FormData(form()));
      for (const [key, value] of [...params]) if (!value) params.delete(key);
      params.set("page_size", "20"); page = 0; rows = []; total = 0; dirty = false;
      node("catalogPriceChangesList").innerHTML = "";
    }
    const requestParams = new URLSearchParams(params); requestParams.set("page", String(page + 1));
    node("catalogPriceChangesStatus").textContent = "Загрузка…";
    node("catalogPriceChangesMore").disabled = true;
    try {
      const result = await core.requestJson(`/api/v1/operations/catalog-products/price-changes?${requestParams}`, {headers: core.authHeaders(), signal: controller.signal});
      if (token !== generation || !active) return;
      rows.push(...result.items); total = result.total; page = result.page;
      render();
      const period = [params.get("date_from"), params.get("date_to")].filter(Boolean).map(core.formatDateRu).join(" — ") || "За всё время";
      node("catalogPriceChangesStatus").textContent = `${params.get("price_kind") === "regular" ? "Обычная" : "Оплаченная"} цена · ${params.get("basis") === "normalized" ? "за кг / л / шт. содержимого" : "за единицу продажи"} · ${period} · ${total} сравнений`;
      if (result.insufficient_series_count) node("catalogPriceChangesStatus").textContent += ` · без пары покупок: ${Number(result.insufficient_series_count)}`;
      if (result.excluded_count) node("catalogPriceChangesStatus").textContent += ` · пропущено строк: ${Number(result.excluded_count)}`;

    } catch (error) {
      if (token === generation && error.name !== "AbortError") node("catalogPriceChangesStatus").textContent = `Не удалось загрузить: ${error.message}. Нажмите «Обновить сравнение» для повтора.`;
    } finally { if (token === generation) node("catalogPriceChangesMore").disabled = false; }
  }
  function invalidate() {
    generation++; controller?.abort(); dirty = true;
    if (active) {
      node("catalogPriceChangesStatus").textContent = "Данные или условия изменились. Нажмите «Обновить сравнение», чтобы обновить сводку.";
      node("catalogPriceChangesMore").hidden = true;
    }
  }
  function bind() {
    if (bound) return; bound = true;
    const conditions = window.App.taskDialogs.attach(form().querySelector('.catalog-price-changes-advanced'), 'Условия сравнения', form().querySelector('.catalog-price-changes-options'));
    conditions.id = 'catalogPriceConditionsDialog';
    conditions.trigger.id = 'catalogPriceConditionsButton';
    const apply = document.createElement('button'); apply.type='button'; apply.className='btn btn-primary btn-icon';
    apply.title='Применить условия'; apply.setAttribute('aria-label',apply.title); apply.innerHTML=window.App.icons.svg('save');
    apply.addEventListener('click', () => {if(form().reportValidity()) {conditions.close(); form().requestSubmit();}});
    const footer=document.createElement('footer'); footer.className='row'; footer.append(apply); conditions.append(footer);
    form().addEventListener("submit", (event) => { event.preventDefault(); load(); });
    form().addEventListener("input", invalidate);
    node("catalogPriceChangesMore").addEventListener("click", () => load(true));
    node("catalogPriceChangesList").addEventListener("click", (event) => {
      const button = event.target.closest("[data-open-price-change]");
      if (!button) return;
      const row = rows[Number(button.dataset.openPriceChange)];
      core.runAction({errorPrefix: "Не удалось открыть историю", action: () => window.App.getRuntimeModule("catalog-products").openEditor(row.product_id, {
        tab: "prices", offerId: row.template_id, comparisonHtml: comparisonDetails(row),
        priceFilters: Object.fromEntries(params),
        priceSeries: {currency: row.currency, shop_name: row.shop_name, unit: row.unit, package_quantity: row.package_quantity, package_unit: row.package_unit},
      })});
    });
  }
  function cleanup() {
    generation++; controller?.abort(); rows = []; params = null; page = 0; total = 0; dirty = false;
    if (node("catalogPriceChanges")) { active = false; node("catalogPriceChanges").classList.add("hidden"); form().reset(); node("catalogPriceChangesList").innerHTML = ""; node("catalogPriceChangesStatus").textContent = ""; }
  }
  window.App.registerRuntimeModule("catalog-price-changes", {bind, invalidate, cleanup, setActive});
})();
