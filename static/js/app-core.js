(() => {
  const state = window.App.createAppState ? window.App.createAppState() : {};
  const el = window.App.createAppElements ? window.App.createAppElements() : {};

  function normalizeStatusMessage(message) {
    const raw = String(message || "").trim();
    return raw.replace(/^Error:\s*/i, "");
  }

  function inferStatusType(message) {
    const normalized = normalizeStatusMessage(message).toLowerCase();
    if (/(ошибк|сессия|истек|не удалось|неверн|invalid|denied|forbidden|unauthorized)/.test(normalized)) {
      return "error";
    }
    if (/(успеш|сохран|готов|добавл|обновл|удален|восстанов)/.test(normalized)) {
      return "success";
    }
    return "info";
  }

  function hideLoginAlert() {
    if (!el.loginAlert) {
      return;
    }
    el.loginAlert.textContent = "";
    el.loginAlert.classList.add("hidden");
    el.loginAlert.classList.remove("is-error", "is-success", "is-info");
  }

  function showLoginAlert(message, type = "error") {
    if (!el.loginAlert) {
      return;
    }
    el.loginAlert.textContent = normalizeStatusMessage(message);
    el.loginAlert.classList.remove("hidden", "is-error", "is-success", "is-info");
    el.loginAlert.classList.add(`is-${type}`);
  }

  function setStatus(message, forLogin = false) {
    const normalized = normalizeStatusMessage(message);
    if (!normalized) {
      return;
    }
    const type = inferStatusType(normalized);
    if (forLogin) {
      showLoginAlert(normalized, type);
      return;
    }
    if (window.App?.core?.notify) {
      window.App.core.notify(normalized, { type });
    }
  }

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${state.token}`,
    };
  }

  function showLogin(message = "", options = {}) {
    const preserveAlert = options?.preserveAlert === true;
    setMobileNavOpen(false);
    el.loginScreen.classList.remove("hidden");
    el.appShell.classList.add("hidden");
    if (message) {
      setStatus(message, true);
      return;
    }
    if (preserveAlert) {
      return;
    }
    if (el.loginAlert && !el.loginAlert.classList.contains("hidden") && String(el.loginAlert.textContent || "").trim()) {
      return;
    }
    hideLoginAlert();
  }

  function showApp() {
    el.loginScreen.classList.add("hidden");
    el.appShell.classList.remove("hidden");
    setMobileNavOpen(false);
    hideLoginAlert();
    startCurrencyIconObserver(el.appShell);
    decorateCurrencyIcons(el.appShell);
  }

  function closeAllMenus() {
    // user dropdown is intentionally removed; keep API for backward compatibility
    setMobileNavOpen(false);
  }

  function isMobileViewport() {
    return window.matchMedia("(max-width: 900px)").matches;
  }

  function setMobileNavOpen(isOpen) {
    const next = Boolean(isOpen) && isMobileViewport();
    state.mobileNavOpen = next;
    document.body.classList.toggle("nav-open", next);
    el.appShell?.classList.toggle("mobile-nav-open", next);
    if (el.mobileNavOverlay) {
      el.mobileNavOverlay.classList.toggle("hidden", !next);
    }
    if (el.mobileNavToggleBtn) {
      el.mobileNavToggleBtn.setAttribute("aria-expanded", next ? "true" : "false");
    }
  }

  function toggleMobileNav() {
    setMobileNavOpen(!state.mobileNavOpen);
  }

  function closeMobileNav() {
    setMobileNavOpen(false);
  }

  function syncSegmentedActive(container, attr, value) {
    if (!container) {
      return;
    }
    const buttons = container.querySelectorAll(`button[data-${attr}]`);
    const dataAttr = `data-${attr}`;
    for (const btn of buttons) {
      btn.classList.toggle("active", btn.getAttribute(dataAttr) === value);
    }
  }

  function syncAllPeriodTabs(value) {
    for (const container of el.periodTabGroups) {
      syncSegmentedActive(container, "period", value);
    }
  }

  function getCoreUtils() {
    return window.App?.coreUtils;
  }

  function formatAmount(value) {
    return getCoreUtils().formatAmount(value);
  }

  function formatRateAmount(value, digits = 6) {
    return getCoreUtils().formatRateAmount(value, digits);
  }

  function getUiSettings() {
    const base = getCoreUtils().getUiSettings(state);
    const next = { ...base };

    if (el.currencySelect?.value) {
      next.currency = normalizeCurrencyCode(el.currencySelect.value || "BYN");
    }
    if (el.currencyPositionSelect?.value) {
      next.currencyPosition = el.currencyPositionSelect.value === "prefix" ? "prefix" : "suffix";
    }
    if (el.showDashboardAnalyticsToggle) {
      next.showDashboardAnalytics = Boolean(el.showDashboardAnalyticsToggle.checked);
    }
    if (el.showDashboardOperationsToggle) {
      next.showDashboardOperations = Boolean(el.showDashboardOperationsToggle.checked);
    }
    if (el.showDashboardDebtsToggle) {
      next.showDashboardDebts = Boolean(el.showDashboardDebtsToggle.checked);
    }
    if (el.dashboardOperationsLimitSelect?.value) {
      const opsLimit = Number(el.dashboardOperationsLimitSelect.value || 8);
      next.dashboardOperationsLimit = [5, 8, 12].includes(opsLimit) ? opsLimit : 8;
    }
    if (el.uiScaleRange?.value) {
      const scale = Number(el.uiScaleRange.value || 100);
      next.scalePercent = Number.isFinite(scale) ? Math.max(85, Math.min(115, Math.round(scale))) : 100;
    }

    return next;
  }

  function resolveCurrencyConfig(currencyCode, positionValue) {
    return getCoreUtils().resolveCurrencyConfig(currencyCode, positionValue);
  }

  function normalizeCurrencyCode(value, fallback = "BYN") {
    return getCoreUtils().normalizeCurrencyCode(value, fallback);
  }

  function getCurrencyConfig() {
    const ui = getUiSettings();
    return resolveCurrencyConfig(ui.currency, ui.currencyPosition);
  }

  function getTrackedCurrencies() {
    return getCoreUtils().getTrackedCurrencies(state);
  }

  function getSelectableCurrencies(options = {}) {
    return getCoreUtils().getSelectableCurrencies(state, options);
  }

  function formatCurrencyLabel(currencyCode, options = {}) {
    return getCoreUtils().formatCurrencyLabel(currencyCode, options);
  }

  function formatCurrencySymbol(currencyCode) {
    return getCoreUtils().formatCurrencySymbol(currencyCode);
  }

  function formatMoney(value, options = {}) {
    return getCoreUtils().formatMoney(state, value, options);
  }

  function evaluateMathExpression(value) {
    return getCoreUtils().evaluateMathExpression(value);
  }

  function resolveMoneyInput(value, fallback = 0) {
    return getCoreUtils().resolveMoneyInput(value, fallback);
  }

  function resolveRateInput(value, fallback = 0, digits = 6) {
    return getCoreUtils().resolveRateInput(value, fallback, digits);
  }

  function applyUiScale(scalePercent) {
    getCoreUtils().applyUiScale(el, scalePercent);
  }

  function applyMoneyInputs(config = null) {
    getCoreUtils().applyMoneyInputs(el, state, config);
  }

  function decorateCurrencyIcons(root = null) {
    return getCoreUtils().decorateCurrencyIcons(root || document.body);
  }

  function startCurrencyIconObserver(root = null) {
    return getCoreUtils().startCurrencyIconObserver(root || document.body);
  }

  function isDashboardDebtsVisible() {
    return getUiSettings().showDashboardDebts;
  }

  function formatDateRu(value) {
    return getCoreUtils().formatDateRu(value);
  }

  function parseDateInputValue(value) {
    return getCoreUtils().parseDateInputValue(value);
  }

  function normalizeDateInputValue(value) {
    return getCoreUtils().normalizeDateInputValue(value);
  }

  function normalizeDateFieldValue(value, inputType = "text") {
    return getCoreUtils().normalizeDateFieldValue(value, inputType);
  }

  function syncDateFieldValue(node, value) {
    return getCoreUtils().syncDateFieldValue(node, value);
  }

  function getTodayIso() {
    return getCoreUtils().getTodayIso();
  }

  function kindLabel(kind) {
    return getCoreUtils().kindLabel(kind);
  }

  function formatPeriodLabel(dateFrom, dateTo) {
    return getCoreUtils().formatPeriodLabel(dateFrom, dateTo);
  }

  function getPreferenceTimeZone() {
    return getCoreUtils().getPreferenceTimeZone(state);
  }

  function getPeriodBounds(period) {
    return getCoreUtils().getPeriodBounds(state, period);
  }

  window.App = {
    state,
    el,
    core: {
      setStatus,
      authHeaders,
      showLogin,
      showApp,
    closeAllMenus,
    setMobileNavOpen,
    toggleMobileNav,
    closeMobileNav,
    isMobileViewport,
    isTelegramWebApp() {
      return state.telegramWebAppAvailable === true;
    },
    syncSegmentedActive,
      syncAllPeriodTabs,
      formatAmount,
      formatRateAmount,
      formatMoney,
      formatCurrencyLabel,
      formatCurrencySymbol,
      evaluateMathExpression,
      resolveMoneyInput,
      resolveRateInput,
      formatDateRu,
      parseDateInputValue,
      normalizeDateInputValue,
      normalizeDateFieldValue,
      syncDateFieldValue,
      getTodayIso,
      kindLabel,
      formatPeriodLabel,
      getPreferenceTimeZone,
      getCurrencyConfig,
      getTrackedCurrencies,
      getSelectableCurrencies,
      normalizeCurrencyCode,
      resolveCurrencyConfig,
      getUiSettings,
      applyUiScale,
      applyMoneyInputs,
      decorateCurrencyIcons,
      startCurrencyIconObserver,
      isDashboardDebtsVisible,
      getPeriodBounds,
      hideLoginAlert,
      showLoginAlert,
      inferStatusType,
    },
    actions: {},
  };
})();
