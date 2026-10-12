(() => {
  const {core} = window.App;
  const esc = (s) => core.escapeHtml(String(s ?? ""));
  const units = {pack: "уп.", piece: "шт.", kg: "кг", g: "г", l: "л", ml: "мл"};
  const number = (v) => Number(v).toLocaleString("ru-RU", {maximumFractionDigits: 4});
  const pct = (v) => v == null ? "нет базы для %" : `${Number(v) > 0 ? "+" : ""}${number(v)}%`;
  const pack = (r) => r.package_quantity && r.package_unit ? `${number(r.package_quantity)} ${units[r.package_unit] || r.package_unit}` : "";
  let payload = null, selected = 0, count = 50;
  function graph(rows, label) {
    const values = rows.map((r) => Number(r.price)), low = values.reduce((a,b) => Math.min(a,b), Infinity), high = values.reduce((a,b) => Math.max(a,b), -Infinity);
    const x = (i) => 40 + (rows.length > 1 ? i / (rows.length - 1) : 0.5) * 620;
    const y = (v) => 135 - (high === low ? 0.5 : (v - low) / (high - low)) * 95;
    const path = rows.map((r, i) => `${i ? "H" : "M"}${x(i).toFixed(2)} ${i ? "V" : ""}${y(Number(r.price)).toFixed(2)}`).join(" ");
    return `<svg class="product-price-chart" viewBox="0 0 700 170" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title><text x="8" y="16">${esc(number(high))}</text><path d="${path}" fill="none" stroke="currentColor" stroke-width="2"/>${rows.map((r,i) => `<circle cx="${x(i)}" cy="${y(Number(r.price))}" r="3" fill="currentColor"><title>${esc(core.formatDateRu(r.recorded_at))}: ${esc(number(r.price))} · ${esc(pct(r.change_percent))}</title></circle>`).join("")}<text x="40" y="160">${esc(core.formatDateRu(rows[0].recorded_at))}</text><text x="660" y="160" text-anchor="end">${esc(core.formatDateRu(rows.at(-1).recorded_at))}</text></svg>`;
  }
  function render() {
    const target = document.getElementById("catalogProductPricesList");
    const series = payload?.series || [];
    if (!series.length) { target.innerHTML = `<p class="empty">Нет покупок с данными для выбранного расчёта.</p>${excluded()}`; return; }
    selected = Math.min(selected, series.length - 1);
    const group = series[selected], rows = group.observations;
    const label = (s) => `${s.currency} · ${s.shop_name || "Магазин не указан"} · за ${units[s.unit] || "ед. (не указана)"}${pack(s) ? ` · ${pack(s)}` : ""}`;
    const title = `${payload.price_kind === "paid" ? "Оплаченная" : "Обычная"} цена: ${label(group)}`;
    target.innerHTML = `<label class="field"><span>Сопоставимые покупки</span><select id="catalogProductPriceSeries">${series.map((s,i) => `<option value="${i}" ${i === selected ? "selected" : ""}>${esc(label(s))}</option>`).join("")}</select></label>
      <p class="product-price-summary"><strong>${esc(pct(group.change_percent))}</strong> от первой до последней покупки · повышений: ${group.increases} · снижений: ${group.decreases}</p>
      ${graph(rows, title)}<p class="muted-small">${esc(title)}. Шаг графика — позиция чека по порядку покупок. Дата — первое наблюдение, а не дата изменения магазином.</p>
      <div class="product-price-events">${[...rows].reverse().slice(0, count).map((r) => `<button type="button" class="catalog-product-purchase-row" data-product-purchase-id="${Number(r.operation_id)}"><span><strong>${esc(core.formatDateRu(r.recorded_at))}</strong><small>${esc(pack(r) || units[r.sale_unit] || "Единица не указана")}${r.is_discounted ? " · со скидкой" : ""}${r.package_changed ? " · другая фасовка/единица" : ""}</small><small>Открыть чек</small></span><span><strong>${esc(number(r.price))} ${esc(group.currency)}/${esc(units[group.unit] || "ед.")}</strong><small>${r.direction > 0 ? "↑ " : r.direction < 0 ? "↓ " : ""}${r.change_percent == null ? "—" : esc(pct(r.change_percent))}</small></span></button>`).join("")}</div>
      ${rows.length > count ? '<button type="button" class="btn btn-secondary" data-price-history-more>Показать ещё</button>' : ""}${excluded()}`;
    target.querySelector("#catalogProductPriceSeries").addEventListener("change", (event) => {selected = Number(event.target.value); count = 50; render(); document.getElementById("catalogProductPriceSeries").focus();});
    target.querySelector("[data-price-history-more]")?.addEventListener("click", () => {count += 50; render(); target.querySelector("[data-price-history-more]")?.focus();});
  }
  function excluded() { return payload?.excluded_count ? `<p class="muted-small">Не показано позиций: ${Number(payload.excluded_count)} — нет нужных единиц, обычной цены или положительного количества.</p>` : ""; }
  window.App.registerRuntimeModule("catalog-price-history", {
    render(value, preserve = false) {
      const key = (s) => s ? JSON.stringify([s.currency, s.shop_name, s.unit, s.package_quantity, s.package_unit]) : "";
      const previous = key(payload?.series?.[selected]);
      payload = value;
      selected = preserve ? Math.max(0, (payload?.series || []).findIndex((s) => key(s) === previous)) : 0;
      if (!preserve) count = 50;
      render();
    },
    cleanup() {payload = null; selected = 0; count = 50;},
  });
})();
