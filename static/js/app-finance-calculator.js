(() => {
  const FIELD_CONFIG = {
    discount: [
      { id: "price", label: "Цена до скидки", placeholder: "129.90" },
      { id: "discount", label: "Скидка, %", placeholder: "15" },
    ],
    change: [
      { id: "oldPrice", label: "Старая цена", placeholder: "129.90" },
      { id: "newPrice", label: "Новая цена", placeholder: "99.90" },
    ],
    unit: [
      { id: "total", label: "Сумма", placeholder: "12.80" },
      { id: "quantity", label: "Количество / вес / объем", placeholder: "0.45" },
    ],
    split: [
      { id: "total", label: "Сумма чека", placeholder: "84.60" },
      { id: "people", label: "Количество людей", placeholder: "3" },
      { id: "tip", label: "Чаевые / комиссия, %", placeholder: "0" },
    ],
  };

  const MODE_LABELS = {
    discount: "Скидка",
    change: "Изменение",
    unit: "Цена за единицу",
    split: "Разделить чек",
  };

  let bound = false;
  let mode = "discount";

  function getCore() {
    return window.App.core || {};
  }

  function getNode(id) {
    return document.getElementById(id);
  }

  function parseNumber(value) {
    const normalized = String(value || "").trim().replace(/\s+/g, "").replace(",", ".");
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatNumber(value, options = {}) {
    const maximumFractionDigits = options.maximumFractionDigits ?? 2;
    return Number(value || 0).toLocaleString("ru-RU", {
      minimumFractionDigits: options.minimumFractionDigits ?? 2,
      maximumFractionDigits,
    });
  }

  function formatMoney(value) {
    return getCore().formatMoney?.(value) || formatNumber(value);
  }

  function renderRows(rows) {
    const result = getNode("financeCalculatorResult");
    if (!result) {
      return;
    }
    result.innerHTML = rows.map((row) => `
      <div class="finance-calculator-result-row">
        <span>${row.label}</span>
        <strong>${row.value}</strong>
      </div>
    `).join("");
  }

  function calculateDiscount(values) {
    const price = Math.max(0, parseNumber(values.price));
    const discount = Math.min(100, Math.max(0, parseNumber(values.discount)));
    const saved = price * discount / 100;
    const finalPrice = price - saved;
    return [
      { label: "Итоговая цена", value: formatMoney(finalPrice) },
      { label: "Экономия", value: formatMoney(saved) },
      { label: "Скидка", value: `${formatNumber(discount, { maximumFractionDigits: 2 })}%` },
    ];
  }

  function calculateChange(values) {
    const oldPrice = Math.max(0, parseNumber(values.oldPrice));
    const newPrice = Math.max(0, parseNumber(values.newPrice));
    const diff = newPrice - oldPrice;
    const pct = oldPrice > 0 ? diff / oldPrice * 100 : 0;
    return [
      { label: diff >= 0 ? "Подорожание" : "Снижение", value: formatMoney(Math.abs(diff)) },
      { label: "Изменение", value: `${diff >= 0 ? "+" : "-"}${formatNumber(Math.abs(pct), { maximumFractionDigits: 2 })}%` },
      { label: "Новая цена", value: formatMoney(newPrice) },
    ];
  }

  function calculateUnit(values) {
    const total = Math.max(0, parseNumber(values.total));
    const quantity = Math.max(0, parseNumber(values.quantity));
    const unit = quantity > 0 ? total / quantity : 0;
    return [
      { label: "Цена за единицу", value: formatMoney(unit) },
      { label: "Сумма", value: formatMoney(total) },
      { label: "Количество", value: formatNumber(quantity, { maximumFractionDigits: 3 }) },
    ];
  }

  function calculateSplit(values) {
    const total = Math.max(0, parseNumber(values.total));
    const people = Math.max(1, Math.round(parseNumber(values.people) || 1));
    const tip = Math.max(0, parseNumber(values.tip));
    const extra = total * tip / 100;
    const finalTotal = total + extra;
    return [
      { label: "Итого с надбавкой", value: formatMoney(finalTotal) },
      { label: "На человека", value: formatMoney(finalTotal / people) },
      { label: "Надбавка", value: formatMoney(extra) },
    ];
  }

  function readValues() {
    return Object.fromEntries((FIELD_CONFIG[mode] || []).map((field) => [
      field.id,
      getNode(`financeCalculatorInput-${field.id}`)?.value || "",
    ]));
  }

  function recalculate() {
    const values = readValues();
    const rows = {
      discount: calculateDiscount,
      change: calculateChange,
      unit: calculateUnit,
      split: calculateSplit,
    }[mode](values);
    renderRows(rows);
  }

  function renderFields() {
    const fields = getNode("financeCalculatorFields");
    if (!fields) {
      return;
    }
    fields.innerHTML = (FIELD_CONFIG[mode] || []).map((field) => `
      <div class="finance-calculator-field">
        <label for="financeCalculatorInput-${field.id}">${field.label}</label>
        <input id="financeCalculatorInput-${field.id}" inputmode="decimal" autocomplete="off" placeholder="${field.placeholder}" data-calculator-input="${field.id}" />
      </div>
    `).join("");
    fields.querySelectorAll("[data-calculator-input]").forEach((input) => {
      input.addEventListener("input", recalculate);
    });
    recalculate();
    fields.querySelector("input")?.focus();
  }

  function setMode(nextMode) {
    mode = FIELD_CONFIG[nextMode] ? nextMode : "discount";
    getCore().syncSegmentedActive?.(getNode("financeCalculatorTabs"), "calculator-mode", mode);
    getNode("financeCalculatorDrawer")?.setAttribute("aria-label", `Финансовый калькулятор: ${MODE_LABELS[mode]}`);
    renderFields();
  }

  function setOpen(open) {
    const drawer = getNode("financeCalculatorDrawer");
    const overlay = getNode("financeCalculatorOverlay");
    const toggle = getNode("financeCalculatorToggle");
    drawer?.classList.toggle("hidden", !open);
    overlay?.classList.toggle("hidden", !open);
    drawer?.setAttribute("aria-hidden", open ? "false" : "true");
    overlay?.setAttribute("aria-hidden", open ? "false" : "true");
    toggle?.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("finance-calculator-open", open);
    if (open) {
      renderFields();
    } else {
      toggle?.focus();
    }
  }

  function toggle() {
    setOpen(getNode("financeCalculatorDrawer")?.classList.contains("hidden") ?? true);
  }

  function bind() {
    if (bound) {
      return;
    }
    bound = true;
    getNode("financeCalculatorToggle")?.addEventListener("click", toggle);
    getNode("financeCalculatorClose")?.addEventListener("click", () => setOpen(false));
    getNode("financeCalculatorOverlay")?.addEventListener("click", () => setOpen(false));
    getNode("financeCalculatorTabs")?.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-calculator-mode]");
      if (!button) {
        return;
      }
      setMode(String(button.dataset.calculatorMode || "discount"));
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !getNode("financeCalculatorDrawer")?.classList.contains("hidden")) {
        setOpen(false);
      }
    });
    setMode(mode);
  }

  const api = {
    bind,
    calculateDiscount,
    calculateChange,
    calculateUnit,
    calculateSplit,
  };

  window.App.registerRuntimeModule?.("finance-calculator", api);
})();
