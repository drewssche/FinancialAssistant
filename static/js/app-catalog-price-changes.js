(() => {
  const {core} = window.App;
  const node = (id) => document.getElementById(id), esc = (v) => core.escapeHtml(String(v ?? ""));
  const units = window.App.measurements.units;
  const number = (v) => Number(v).toLocaleString("ru-RU", {maximumFractionDigits: 4});
  const pct = (v) => v == null ? "нет базы для %" : `${Number(v) > 0 ? "+" : ""}${number(v)}%`;
  let bound = false, controller = null, generation = 0, page = 0, rows = [], total = 0, params = null;
  let dirty = false;
  const form = () => node("catalogPriceChangesForm");
  function render() {
    node("catalogPriceChangesList").innerHTML = rows.map((r, index) => {
      const packageLabel = r.package_quantity ? ` · ${number(r.package_quantity)} ${units[r.package_unit] || r.package_unit}` : "";
      const kind = params.get("price_kind") === "regular" ? "Обычная цена" : "Оплаченная цена";
      const missing = !r.unit || (r.unit === "pack" && !r.package_quantity);
      return `<article class="catalog-price-change">
        <div><strong>${esc(r.product_name)}</strong><small>${esc(r.shop_name || "Магазин не указан")} · ${esc(r.offer_name)}</small>
        <small>${esc(kind)} · ${esc(r.currency)}/${esc(units[r.unit] || "ед. (не указана)")}${esc(packageLabel)}</small></div>
        <div><strong>${esc(number(r.reference_price))} → ${esc(number(r.latest_price))} ${esc(r.currency)}</strong>
        <strong class="catalog-price-change-percent">${r.direction > 0 ? "↑" : r.direction < 0 ? "↓" : "="} ${esc(pct(r.change_percent))}</strong>
        <small>${esc(core.formatDateRu(r.reference_date))} → ${esc(core.formatDateRu(r.latest_date))}</small></div>
        <p>За период: ${esc(pct(r.period_change_percent))} · последний шаг: ${esc(pct(r.last_change_percent))}<br>
        Повышений: ${Number(r.increases)} · снижений: ${Number(r.decreases)} · позиций чека: ${Number(r.observations_count)}</p>
        <p>Последний купленный объём по прежней → последней цене:<br><strong>${esc(number(r.baseline_cost))} → ${esc(number(r.latest_cost))} ${esc(r.currency)}</strong>
        · разница ${Number(r.cost_difference) > 0 ? "+" : ""}${esc(number(r.cost_difference))} ${esc(r.currency)}</p>
        ${r.reference_is_discounted || r.latest_is_discounted ? '<small>В сравнении есть покупка со скидкой.</small>' : ""}
        ${r.package_changed ? '<small>В периоде менялась фасовка или единица. Замена упаковки не подтверждена.</small>' : ""}
        ${missing ? '<small>Единицы или содержимое упаковки неизвестны — сопоставимость требует проверки.</small>' : ""}
        <button type="button" class="btn btn-secondary btn-xs" data-open-price-change="${index}">График и чеки</button>
      </article>`;
    }).join("") || '<p class="empty">Нет сравнений с двумя сопоставимыми покупками по этим условиям.</p>';
    node("catalogPriceChangesMore").hidden = dirty || rows.length >= total;
  }
  async function load(more = false) {
    if (!node("catalogPriceChanges").open) return;
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
      if (token !== generation || !node("catalogPriceChanges").open) return;
      rows.push(...result.items); total = result.total; page = result.page;
      render();
      node("catalogPriceChangesStatus").textContent = `Сравнение ${params.get("comparison") === "previous" ? "с предыдущей покупкой" : "за выбранный период"}. Сначала последние покупки. Сравнений: ${total}. Недостаточно покупок: ${result.insufficient_series_count}. Позиций без нужных данных: ${result.excluded_count}.`;
    } catch (error) {
      if (token === generation && error.name !== "AbortError") node("catalogPriceChangesStatus").textContent = `Не удалось загрузить: ${error.message}. Нажмите «Показать» для повтора.`;
    } finally { if (token === generation) node("catalogPriceChangesMore").disabled = false; }
  }
  function invalidate() {
    generation++; controller?.abort(); dirty = true;
    if (node("catalogPriceChanges")?.open) {
      node("catalogPriceChangesStatus").textContent = "Данные или условия изменились. Нажмите «Показать», чтобы обновить сводку.";
      node("catalogPriceChangesMore").hidden = true;
    }
  }
  function bind() {
    if (bound) return; bound = true;
    node("catalogPriceChanges").addEventListener("toggle", () => {
      if (node("catalogPriceChanges").open) load(); else { generation++; controller?.abort(); }
    });
    form().addEventListener("submit", (event) => { event.preventDefault(); load(); });
    form().addEventListener("input", invalidate);
    node("catalogPriceChangesMore").addEventListener("click", () => load(true));
    node("catalogPriceChangesList").addEventListener("click", (event) => {
      const button = event.target.closest("[data-open-price-change]");
      if (!button) return;
      const row = rows[Number(button.dataset.openPriceChange)];
      core.runAction({errorPrefix: "Не удалось открыть историю", action: () => window.App.getRuntimeModule("catalog-products").openEditor(row.product_id, {
        tab: "prices", offerId: row.template_id,
        priceFilters: Object.fromEntries(params),
        priceSeries: {currency: row.currency, shop_name: row.shop_name, unit: row.unit, package_quantity: row.package_quantity, package_unit: row.package_unit},
      })});
    });
  }
  function cleanup() {
    generation++; controller?.abort(); rows = []; params = null; page = 0; total = 0; dirty = false;
    if (node("catalogPriceChanges")) { node("catalogPriceChanges").open = false; form().reset(); node("catalogPriceChangesList").innerHTML = ""; node("catalogPriceChangesStatus").textContent = ""; }
  }
  window.App.registerRuntimeModule("catalog-price-changes", {bind, invalidate, cleanup});
})();
