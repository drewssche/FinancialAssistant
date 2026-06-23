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
  let openSource = "global";
  let activeModal = null;
  let returnFocusNode = null;

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

  function clearModalPosition() {
    const drawer = getNode("financeCalculatorDrawer");
    if (!drawer) {
      return;
    }
    drawer.style.removeProperty("--finance-calculator-modal-top");
    drawer.style.removeProperty("--finance-calculator-modal-left");
    drawer.style.removeProperty("--finance-calculator-modal-height");
  }

  function positionModalDrawer() {
    const drawer = getNode("financeCalculatorDrawer");
    if (!drawer || openSource !== "modal" || !activeModal || activeModal.classList.contains("hidden")) {
      return;
    }
    const card = activeModal.querySelector(".modal-card");
    if (!card) {
      return;
    }
    const margin = 12;
    const gap = 8;
    const rect = card.getBoundingClientRect();
    const headRect = card.querySelector(".panel-head")?.getBoundingClientRect();
    const top = Math.max(margin, (headRect?.bottom || rect.top) + gap);
    const width = Math.min(360, Math.max(280, window.innerWidth - margin * 2));
    const preferredLeft = rect.right + gap;
    const left = preferredLeft + width <= window.innerWidth - margin
      ? preferredLeft
      : Math.max(margin, Math.min(window.innerWidth - width - margin, rect.right - width));
    drawer.style.setProperty("--finance-calculator-modal-top", `${top}px`);
    drawer.style.setProperty("--finance-calculator-modal-left", `${left}px`);
    drawer.style.setProperty("--finance-calculator-modal-height", `${Math.min(Math.max(260, rect.bottom - top), window.innerHeight - top - margin)}px`);
  }

  function syncModalToggleState(open) {
    ["financeCalculatorToggle", "createFinanceCalculatorToggle", "editFinanceCalculatorToggle"].forEach((id) => {
      getNode(id)?.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  function setOpen(open, options = {}) {
    const drawer = getNode("financeCalculatorDrawer");
    const overlay = getNode("financeCalculatorOverlay");
    if (open && options.source === "modal") {
      openSource = "modal";
      activeModal = options.modal || null;
      returnFocusNode = options.returnFocus || null;
    } else if (open) {
      openSource = "global";
      activeModal = null;
      returnFocusNode = options.returnFocus || getNode("financeCalculatorToggle");
    }
    drawer?.classList.toggle("hidden", !open);
    drawer?.classList.toggle("modal-attached", open && openSource === "modal");
    overlay?.classList.toggle("hidden", !open || openSource === "modal");
    drawer?.setAttribute("aria-hidden", open ? "false" : "true");
    overlay?.setAttribute("aria-hidden", open && openSource !== "modal" ? "false" : "true");
    syncModalToggleState(open);
    document.body.classList.toggle("finance-calculator-open", open && openSource !== "modal");
    if (open) {
      positionModalDrawer();
      renderFields();
    } else {
      drawer?.classList.remove("modal-attached");
      clearModalPosition();
      document.body.classList.remove("finance-calculator-open");
      const focusTarget = returnFocusNode || getNode("financeCalculatorToggle");
      openSource = "global";
      activeModal = null;
      returnFocusNode = null;
      focusTarget?.focus?.();
    }
  }

  function toggle() {
    setOpen(getNode("financeCalculatorDrawer")?.classList.contains("hidden") ?? true, {
      source: "global",
      returnFocus: getNode("financeCalculatorToggle"),
    });
  }

  function toggleFromModal(modalId, trigger) {
    const drawer = getNode("financeCalculatorDrawer");
    const modal = getNode(modalId);
    const shouldOpen = drawer?.classList.contains("hidden") || openSource !== "modal" || activeModal !== modal;
    setOpen(shouldOpen, { source: "modal", modal, returnFocus: trigger });
  }

  function closeIfAttachedToModal(modal) {
    if (openSource === "modal" && (!modal || modal === activeModal)) {
      setOpen(false);
    }
  }

  function bind() {
    if (bound) {
      return;
    }
    bound = true;
    getNode("financeCalculatorToggle")?.addEventListener("click", toggle);
    getNode("createFinanceCalculatorToggle")?.addEventListener("click", (event) => {
      toggleFromModal("createModal", event.currentTarget);
    });
    getNode("editFinanceCalculatorToggle")?.addEventListener("click", (event) => {
      toggleFromModal("editModal", event.currentTarget);
    });
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
    window.addEventListener("resize", positionModalDrawer);
    document.addEventListener("scroll", positionModalDrawer, true);
    setMode(mode);
  }

  const api = {
    bind,
    closeIfAttachedToModal,
    calculateDiscount,
    calculateChange,
    calculateUnit,
    calculateSplit,
  };

  window.App.registerRuntimeModule?.("finance-calculator", api);
})();
