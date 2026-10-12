(() => {
  const units = { pieces: "шт. товара", packs: "упак.", mass_kg: "кг", volume_l: "л", content_pieces: "шт. внутри" };
  const metrics = ["purchases", ...Object.keys(units), "amount"];
  const number = (value) => new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 9 }).format(Number(value || 0));
  const normalizeMetric = (value) => metrics.includes(value) ? value : "purchases";
  function summary(item) {
    const totals = item?.quantity_totals;
    if (!totals) return "Единицы не указаны";
    const parts = Object.entries(units).filter(([key]) => Number(totals[key]) > 0)
      .map(([key, label]) => `${number(totals[key])} ${label}`);
    if (Number(totals.unknown_rows_count) > 0) parts.push(`Без единиц: ${totals.unknown_rows_count} стр.`);
    if (Number(totals.unmeasured_package_rows_count) > 0) parts.push(`Без фасовки: ${totals.unmeasured_package_rows_count} стр.`);
    return parts.join(" · ") || "Нет покупок";
  }
  function amounts(item) {
    return Object.entries(item?.amount_totals || {}).sort(([a], [b]) => a.localeCompare(b))
      .map(([currency, value]) => window.App.core.formatMoney(value, {currency})).join(" · ") || "—";
  }
  window.App = window.App || {};
  window.App.purchaseMetrics = {units, metrics, number, normalizeMetric, summary, amounts};
})();
