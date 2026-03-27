(() => {
  const CURRENCY_META = {
    BYN: { symbol: "руб." },
    RUB: { symbol: "₽" },
    USD: { symbol: "$" },
    EUR: { symbol: "€" },
    GBP: { symbol: "£" },
    CNY: { symbol: "¥" },
    PLN: { symbol: "zł" },
  };
  function decorateCurrencyIcons() {}

  function startCurrencyIconObserver() {}

  function formatAmount(value) {
    const num = Number(value);
    if (Number.isNaN(num)) {
      return "0.00";
    }
    return num.toFixed(2);
  }

  function evaluateMathExpression(value) {
    const raw = String(value || "").trim();
    if (!raw) {
      return { ok: false, value: 0, expression: "", reason: "empty" };
    }
    const expression = raw
      .replace(/\s+/g, "")
      .replace(/,/g, ".");
    if (!expression) {
      return { ok: false, value: 0, expression: "", reason: "empty" };
    }
    if (/[^0-9+\-*/().]/.test(expression)) {
      return { ok: false, value: 0, expression, reason: "invalid_char" };
    }

    let index = 0;

    function skipUnary() {
      while (expression[index] === "+") {
        index += 1;
      }
    }

    function parseNumber() {
      const start = index;
      let sawDigit = false;
      let sawDot = false;
      while (index < expression.length) {
        const ch = expression[index];
        if (ch >= "0" && ch <= "9") {
          sawDigit = true;
          index += 1;
          continue;
        }
        if (ch === "." && !sawDot) {
          sawDot = true;
          index += 1;
          continue;
        }
        break;
      }
      if (!sawDigit) {
        throw new Error("Expected number");
      }
      const token = expression.slice(start, index);
      const num = Number(token);
      if (!Number.isFinite(num)) {
        throw new Error("Invalid number");
      }
      return num;
    }

    function parseFactor() {
      skipUnary();
      if (expression[index] === "-") {
        index += 1;
        return -parseFactor();
      }
      if (expression[index] === "(") {
        index += 1;
        const nested = parseExpression();
        if (expression[index] !== ")") {
          throw new Error("Unclosed parenthesis");
        }
        index += 1;
        return nested;
      }
      return parseNumber();
    }

    function parseTerm() {
      let left = parseFactor();
      while (index < expression.length) {
        const op = expression[index];
        if (op !== "*" && op !== "/") {
          break;
        }
        index += 1;
        const right = parseFactor();
        if (op === "*") {
          left *= right;
        } else {
          if (Math.abs(right) < Number.EPSILON) {
            throw new Error("Division by zero");
          }
          left /= right;
        }
      }
      return left;
    }

    function parseExpression() {
      let left = parseTerm();
      while (index < expression.length) {
        const op = expression[index];
        if (op !== "+" && op !== "-") {
          break;
        }
        index += 1;
        const right = parseTerm();
        if (op === "+") {
          left += right;
        } else {
          left -= right;
        }
      }
      return left;
    }

    try {
      const result = parseExpression();
      if (index !== expression.length) {
        return { ok: false, value: 0, expression, reason: "trailing_token" };
      }
      const rounded = Math.round(result * 100) / 100;
      if (!Number.isFinite(rounded)) {
        return { ok: false, value: 0, expression, reason: "non_finite" };
      }
      return { ok: true, value: rounded, expression, reason: "" };
    } catch {
      return { ok: false, value: 0, expression, reason: "parse_error" };
    }
  }

  function resolveMoneyInput(value, fallback = 0) {
    const raw = String(value || "").trim();
    const fallbackValue = Number(fallback) || 0;
    if (!raw) {
      return {
        raw,
        empty: true,
        valid: false,
        value: fallbackValue,
        previewValue: fallbackValue,
        formatted: formatAmount(fallbackValue),
        previewFormatted: formatAmount(fallbackValue),
      };
    }
    const evaluated = evaluateMathExpression(raw);
    if (evaluated.ok) {
      return {
        raw,
        empty: false,
        valid: true,
        value: evaluated.value,
        previewValue: evaluated.value,
        formatted: formatAmount(evaluated.value),
        previewFormatted: formatAmount(evaluated.value),
      };
    }

    let previewValue = fallbackValue;
    for (let i = raw.length - 1; i > 0; i -= 1) {
      const candidate = raw.slice(0, i).trim();
      if (!candidate) {
        continue;
      }
      const partial = evaluateMathExpression(candidate);
      if (partial.ok) {
        previewValue = partial.value;
        break;
      }
    }

    return {
      raw,
      empty: false,
      valid: false,
      value: fallbackValue,
      previewValue,
      formatted: formatAmount(fallbackValue),
      previewFormatted: formatAmount(previewValue),
    };
  }

  function getUiSettings(state) {
    const ui = state.preferences?.data?.ui || {};
    const scale = Number(ui.scale_percent || 100);
    const dashboardOpsLimit = Number(ui.dashboard_operations_limit || 8);
    return {
      currency: String(ui.currency || "BYN").toUpperCase(),
      currencyPosition: ui.currency_position === "prefix" ? "prefix" : "suffix",
      showDashboardAnalytics: ui.show_dashboard_analytics !== false,
      showDashboardOperations: ui.show_dashboard_operations !== false,
      showDashboardDebts: ui.show_dashboard_debts !== false,
      dashboardOperationsLimit: [5, 8, 12].includes(dashboardOpsLimit) ? dashboardOpsLimit : 8,
      scalePercent: Number.isFinite(scale) ? Math.max(85, Math.min(115, Math.round(scale))) : 100,
    };
  }

  function resolveCurrencyConfig(currencyCode, positionValue) {
    const code = String(currencyCode || "BYN").toUpperCase();
    const position = positionValue === "prefix" ? "prefix" : "suffix";
    const symbol = CURRENCY_META[code]?.symbol || code;
    return {
      code,
      symbol,
      position,
    };
  }

  function formatCurrencyLabel(currencyCode, options = {}) {
    const cfg = resolveCurrencyConfig(currencyCode);
    if (options.withSymbol === false || cfg.symbol === cfg.code) {
      return cfg.code;
    }
    return `${cfg.code} (${cfg.symbol})`;
  }

  function getCurrencyConfig(state) {
    const ui = getUiSettings(state);
    return resolveCurrencyConfig(ui.currency, ui.currencyPosition);
  }

  function formatMoney(state, value, options = {}) {
    const amount = Number(value || 0);
    const safe = Number.isFinite(amount) ? amount : 0;
    const formatted = new Intl.NumberFormat("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(safe);
    if (options.withCurrency === false) {
      return formatted;
    }
    const cfg = options.currency || options.position
      ? resolveCurrencyConfig(options.currency, options.position)
      : getCurrencyConfig(state);
    return cfg.position === "prefix" ? `${cfg.symbol} ${formatted}` : `${formatted} ${cfg.symbol}`;
  }

  function applyUiScale(el, scalePercent) {
    const normalized = Math.max(85, Math.min(115, Number(scalePercent || 100)));
    document.documentElement.style.setProperty("--ui-scale", String(normalized / 100));
    if (el.uiScaleRange) {
      el.uiScaleRange.value = String(normalized);
    }
    if (el.uiScaleValue) {
      el.uiScaleValue.textContent = `${normalized}%`;
    }
  }

  function applyMoneyInputs(el, state, config = null) {
    const cfg = config || getCurrencyConfig(state);
    document.querySelectorAll("[data-money-input-wrap]").forEach((node) => {
      node.dataset.currencySymbol = cfg.symbol;
      node.classList.toggle("currency-byn", cfg.code === "BYN");
      node.classList.toggle("currency-prefix", cfg.position === "prefix");
      node.classList.toggle("currency-suffix", cfg.position !== "prefix");
    });
    if (el.currencyPreview) {
      el.currencyPreview.textContent = `Пример: ${formatMoney(state, 1234.56, { currency: cfg.code, position: cfg.position })}`;
    }
    decorateCurrencyIcons(document.body);
  }

  function isDashboardDebtsVisible(state) {
    return getUiSettings(state).showDashboardDebts;
  }

  function isIsoDate(value) {
    const raw = String(value || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      return false;
    }
    const date = new Date(`${raw}T00:00:00Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === raw;
  }

  function formatDateRu(value) {
    if (!value) {
      return "";
    }
    const raw = String(value).trim();
    if (/^\d{2}\.\d{2}\.\d{4}$/.test(raw)) {
      return raw;
    }
    const [year, month, day] = raw.split("-");
    if (!year || !month || !day) {
      return raw;
    }
    return `${day}.${month}.${year}`;
  }

  function isValidDisplayDateValue(value) {
    if (!/^\d{2}\.\d{2}\.\d{4}$/.test(value)) {
      return false;
    }
    const [day, month, year] = value.split(".");
    const iso = `${year}-${month}-${day}`;
    return isIsoDate(iso);
  }

  function isDisplayDate(value) {
    const raw = normalizeDateInputValue(value);
    return isValidDisplayDateValue(raw);
  }

  function parseDateInputValue(value) {
    const raw = String(value || "").trim();
    if (!raw) {
      return "";
    }
    if (isIsoDate(raw)) {
      return raw;
    }
    const normalized = normalizeDateInputValue(raw);
    if (!/^\d{2}\.\d{2}\.\d{4}$/.test(normalized)) {
      return "";
    }
    const [day, month, year] = normalized.split(".");
    const iso = `${year}-${month}-${day}`;
    return isIsoDate(iso) ? iso : "";
  }

  function normalizeDateInputValue(value) {
    const raw = String(value || "").trim();
    if (!raw) {
      return "";
    }
    if (isIsoDate(raw)) {
      return formatDateRu(raw);
    }
    const digitsOnly = raw.replace(/[^\d]/g, "");
    if (digitsOnly.length === 8) {
      const day = digitsOnly.slice(0, 2);
      const month = digitsOnly.slice(2, 4);
      const year = digitsOnly.slice(4, 8);
      const normalized = `${day}.${month}.${year}`;
      return isValidDisplayDateValue(normalized) ? normalized : raw;
    }
    const dotted = raw.replace(/[-/]/g, ".");
    if (/^\d{1,2}\.\d{1,2}\.\d{4}$/.test(dotted)) {
      const [dayRaw, monthRaw, year] = dotted.split(".");
      const normalized = `${dayRaw.padStart(2, "0")}.${monthRaw.padStart(2, "0")}.${year}`;
      return isValidDisplayDateValue(normalized) ? normalized : raw;
    }
    return raw;
  }

  function normalizeDateFieldValue(value, inputType = "text") {
    const type = String(inputType || "text").toLowerCase();
    const iso = parseDateInputValue(value);
    if (type === "date") {
      return iso || "";
    }
    return iso ? formatDateRu(iso) : normalizeDateInputValue(value);
  }

  function syncDateFieldValue(node, value) {
    if (!node) {
      return "";
    }
    const normalized = normalizeDateFieldValue(value, node.type || "text");
    node.value = normalized;
    return normalized;
  }

  function getTodayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function kindLabel(kind) {
    return kind === "income" ? "Доход" : "Расход";
  }

  function formatPeriodLabel(dateFrom, dateTo) {
    if (!dateFrom || !dateTo) {
      return "";
    }
    if (dateFrom === dateTo) {
      return formatDateRu(dateFrom);
    }
    return `${formatDateRu(dateFrom)} - ${formatDateRu(dateTo)}`;
  }

  function extractZonedDateParts(date, timeZone) {
    const dtf = new Intl.DateTimeFormat("en-US", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "short",
    });
    const parts = dtf.formatToParts(date);
    const get = (type) => parts.find((item) => item.type === type)?.value || "";
    const weekdayMap = {
      Sun: 0,
      Mon: 1,
      Tue: 2,
      Wed: 3,
      Thu: 4,
      Fri: 5,
      Sat: 6,
    };
    return {
      year: Number(get("year")),
      month: Number(get("month")),
      day: Number(get("day")),
      weekday: weekdayMap[get("weekday")] ?? 0,
    };
  }

  function formatIsoUtcDate(value) {
    const year = value.getUTCFullYear();
    const month = String(value.getUTCMonth() + 1).padStart(2, "0");
    const day = String(value.getUTCDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function getPreferenceTimeZone(state) {
    const saved = state.preferences?.data?.ui?.timezone;
    const browserTimeZone = state.preferences?.data?.ui?.browser_timezone;
    if (!saved || saved === "auto") {
      if (browserTimeZone) {
        return browserTimeZone;
      }
      return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    }
    return saved;
  }

  function getPeriodBounds(state, period) {
    const now = new Date();
    const timeZone = getPreferenceTimeZone(state);
    let zonedParts;
    try {
      zonedParts = extractZonedDateParts(now, timeZone);
    } catch {
      zonedParts = extractZonedDateParts(now, "UTC");
    }
    let start = new Date(Date.UTC(zonedParts.year, zonedParts.month - 1, zonedParts.day));
    let end = new Date(start);

    if (period === "day") {
      end = new Date(start);
    } else if (period === "week") {
      const mondayOffset = zonedParts.weekday === 0 ? 6 : zonedParts.weekday - 1;
      start = new Date(Date.UTC(zonedParts.year, zonedParts.month - 1, zonedParts.day));
      start.setUTCDate(start.getUTCDate() - mondayOffset);
      end = new Date(start);
      end.setUTCDate(start.getUTCDate() + 6);
    } else if (period === "month") {
      start = new Date(Date.UTC(zonedParts.year, zonedParts.month - 1, 1));
      end = new Date(Date.UTC(zonedParts.year, zonedParts.month, 0));
    } else if (period === "year") {
      start = new Date(Date.UTC(zonedParts.year, 0, 1));
      end = new Date(Date.UTC(zonedParts.year, 11, 31));
    } else if (period === "all_time") {
      const fallbackToday = formatIsoUtcDate(start);
      const first = String(state.firstOperationDate || "").trim();
      return { dateFrom: first || fallbackToday, dateTo: formatIsoUtcDate(end) };
    } else if (period === "custom" && state.customDateFrom && state.customDateTo) {
      return { dateFrom: state.customDateFrom, dateTo: state.customDateTo };
    } else {
      start = new Date(Date.UTC(zonedParts.year, zonedParts.month - 1, zonedParts.day));
      end = new Date(start);
    }

    return { dateFrom: formatIsoUtcDate(start), dateTo: formatIsoUtcDate(end) };
  }

  window.App.coreUtils = {
    formatAmount,
    evaluateMathExpression,
    resolveMoneyInput,
    getUiSettings,
    resolveCurrencyConfig,
    formatCurrencyLabel,
    getCurrencyConfig,
    formatMoney,
    applyUiScale,
    applyMoneyInputs,
    isDashboardDebtsVisible,
    formatDateRu,
    isDisplayDate,
    parseDateInputValue,
    normalizeDateInputValue,
    normalizeDateFieldValue,
    syncDateFieldValue,
    getTodayIso,
    kindLabel,
    formatPeriodLabel,
    getPreferenceTimeZone,
    getPeriodBounds,
    decorateCurrencyIcons,
    startCurrencyIconObserver,
  };
})();
