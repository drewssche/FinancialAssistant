(() => {
  const fields = ["sale_unit", "package_quantity", "package_unit"];
  const units = { piece: "шт.", pack: "упак.", kg: "кг", g: "г", l: "л", ml: "мл" };
  function snapshot(value = {}) {
    return Object.fromEntries(fields.map((key) => [key, value[key] === "" || value[key] == null ? null : value[key]]));
  }
  function options(selected, content = false) {
    return '<option value="">Не указана</option>' + Object.entries(units)
      .filter(([key]) => !content || key !== "pack")
      .map(([key, label]) => `<option value="${key}" ${key === selected ? "selected" : ""}>${label}</option>`).join("");
  }
  function summary(value) {
    const sale = units[value.sale_unit] || "Единицы и фасовка";
    return value.package_quantity && units[value.package_unit]
      ? `${sale} · ${value.package_quantity} ${units[value.package_unit]}` : sale;
  }
  window.App = window.App || {};
  window.App.measurements = { fields, units, snapshot, options, summary };
})();
