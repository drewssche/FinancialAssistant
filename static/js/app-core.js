(() => {
  const state = {
    token: localStorage.getItem("access_token") || "",
    preferences: null,
    page: 1,
    pageSize: 20,
    total: 0,
    operationsHasMore: true,
    operationsLoading: false,
    firstOperationDate: "",
    allTimeAnchorResolved: false,
    categoryPage: 1,
    categoryPageSize: 20,
    categoryTotal: 0,
    categoriesHasMore: true,
    categoriesLoading: false,
    categoryTableItems: [],
    debtStatusFilter: "active",
    debtCardsCache: [],
    editDebtCreateId: null,
    editOperationId: null,
    editCategoryId: null,
    period: "day",
    customDateFrom: "",
    customDateTo: "",
    filterKind: "",
    activeSection: "dashboard",
    categoryFilterKind: "all",
    categories: [],
    categoryGroups: [],
    selectedOperationIds: new Set(),
    selectedCategoryIds: new Set(),
    selectedGroupIds: new Set(),
    pendingCreateCategoryFromOperation: "",
    pendingConfirm: null,
    toasts: new Map(),
    lastErrorToast: { message: "", ts: 0 },
  };

  const el = {
    loginScreen: document.getElementById("loginScreen"),
    appShell: document.getElementById("appShell"),
    loginAlert: document.getElementById("loginAlert"),
    devLoginBtn: document.getElementById("devLoginBtn"),
    mainNav: document.getElementById("mainNav"),
    sectionTitle: document.getElementById("sectionTitle"),
    sectionSubtitle: document.getElementById("sectionSubtitle"),
    todayWeekday: document.getElementById("todayWeekday"),
    todayDate: document.getElementById("todayDate"),
    topActions: document.querySelector(".top-actions"),
    periodTabGroups: document.querySelectorAll("[data-period-tabs]"),
    periodCustomModal: document.getElementById("periodCustomModal"),
    periodCustomForm: document.getElementById("periodCustomForm"),
    closePeriodCustomModalBtn: document.getElementById("closePeriodCustomModalBtn"),
    customDateFrom: document.getElementById("customDateFrom"),
    customDateTo: document.getElementById("customDateTo"),
    kindFilters: document.getElementById("kindFilters"),
    filterQ: document.getElementById("filterQ"),
    addOperationCta: document.getElementById("addOperationCta"),
    batchOperationCta: document.getElementById("batchOperationCta"),
    openOperationsTabBtn: document.getElementById("openOperationsTabBtn"),
    openDebtsTabBtn: document.getElementById("openDebtsTabBtn"),
    operationsBody: document.getElementById("operationsBody"),
    dashboardOperationsBody: document.getElementById("dashboardOperationsBody"),
    dashboardDebtsPanel: document.getElementById("dashboardDebtsPanel"),
    dashboardDebtsList: document.getElementById("dashboardDebtsList"),
    operationsSelectAll: document.getElementById("operationsSelectAll"),
    dashboardPeriodLabel: document.getElementById("dashboardPeriodLabel"),
    operationsPeriodLabel: document.getElementById("operationsPeriodLabel"),
    operationsBulkBar: document.getElementById("operationsBulkBar"),
    operationsSelectedCount: document.getElementById("operationsSelectedCount"),
    bulkEditOperationsBtn: document.getElementById("bulkEditOperationsBtn"),
    bulkDeleteOperationsBtn: document.getElementById("bulkDeleteOperationsBtn"),
    deleteAllOperationsBtn: document.getElementById("deleteAllOperationsBtn"),
    pageInfo: document.getElementById("pageInfo"),
    prevPageBtn: document.getElementById("prevPageBtn"),
    nextPageBtn: document.getElementById("nextPageBtn"),
    operationsInfiniteSentinel: document.getElementById("operationsInfiniteSentinel"),
    categoriesInfiniteSentinel: document.getElementById("categoriesInfiniteSentinel"),
    incomeTotal: document.getElementById("incomeTotal"),
    expenseTotal: document.getElementById("expenseTotal"),
    balanceTotal: document.getElementById("balanceTotal"),
    debtLendTotal: document.getElementById("debtLendTotal"),
    debtBorrowTotal: document.getElementById("debtBorrowTotal"),
    debtNetTotal: document.getElementById("debtNetTotal"),
    userAvatar: document.getElementById("userAvatar"),
    userName: document.getElementById("userName"),
    userHandle: document.getElementById("userHandle"),
    sidebarLogoutBtn: document.getElementById("sidebarLogoutBtn"),
    dashboardSection: document.getElementById("dashboardSection"),
    operationsSection: document.getElementById("operationsSection"),
    debtsSection: document.getElementById("debtsSection"),
    categoriesSection: document.getElementById("categoriesSection"),
    settingsSection: document.getElementById("settingsSection"),
    settingsForm: document.getElementById("settingsForm"),
    timezoneSelect: document.getElementById("timezoneSelect"),
    currencySelect: document.getElementById("currencySelect"),
    currencyPositionSelect: document.getElementById("currencyPositionSelect"),
    currencyPreview: document.getElementById("currencyPreview"),
    showDashboardDebtsToggle: document.getElementById("showDashboardDebtsToggle"),
    uiScaleRange: document.getElementById("uiScaleRange"),
    uiScaleValue: document.getElementById("uiScaleValue"),
    resetUiScaleBtn: document.getElementById("resetUiScaleBtn"),
    deleteMePhrase: document.getElementById("deleteMePhrase"),
    deleteMeBtn: document.getElementById("deleteMeBtn"),
    saveSettingsBtn: document.getElementById("saveSettingsBtn"),
    categoriesBody: document.getElementById("categoriesBody"),
    categoryKindTabs: document.getElementById("categoryKindTabs"),
    categorySearchQ: document.getElementById("categorySearchQ"),
    categoriesSelectAll: document.getElementById("categoriesSelectAll"),
    categoriesBulkBar: document.getElementById("categoriesBulkBar"),
    categoriesSelectedCount: document.getElementById("categoriesSelectedCount"),
    bulkEditCategoriesBtn: document.getElementById("bulkEditCategoriesBtn"),
    bulkDeleteCategoriesBtn: document.getElementById("bulkDeleteCategoriesBtn"),
    deleteAllCategoriesBtn: document.getElementById("deleteAllCategoriesBtn"),
    addGroupCta: document.getElementById("addGroupCta"),
    addCategoryCta: document.getElementById("addCategoryCta"),
    addDebtCta: document.getElementById("addDebtCta"),
    debtSearchQ: document.getElementById("debtSearchQ"),
    debtStatusTabs: document.getElementById("debtStatusTabs"),
    debtsCards: document.getElementById("debtsCards"),
    createCategoryModal: document.getElementById("createCategoryModal"),
    closeCreateCategoryModalBtn: document.getElementById("closeCreateCategoryModalBtn"),
    categoryModalForm: document.getElementById("categoryModalForm"),
    createCategoryKind: document.getElementById("createCategoryKind"),
    categoryKind: document.getElementById("categoryKind"),
    categoryName: document.getElementById("categoryName"),
    categoryIcon: document.getElementById("categoryIcon"),
    categoryIconToggle: document.getElementById("categoryIconToggle"),
    categoryIconPopover: document.getElementById("categoryIconPopover"),
    categoryGroup: document.getElementById("categoryGroup"),
    createCategoryGroupField: document.getElementById("createCategoryGroupField"),
    categoryGroupSearch: document.getElementById("categoryGroupSearch"),
    createCategoryGroupPickerBlock: document.getElementById("createCategoryGroupPickerBlock"),
    categoryGroupAll: document.getElementById("categoryGroupAll"),
    createGroupModal: document.getElementById("createGroupModal"),
    closeCreateGroupModalBtn: document.getElementById("closeCreateGroupModalBtn"),
    groupModalForm: document.getElementById("groupModalForm"),
    groupName: document.getElementById("groupName"),
    groupAccentColor: document.getElementById("groupAccentColor"),
    groupAccentColorHex: document.getElementById("groupAccentColorHex"),
    createGroupKind: document.getElementById("createGroupKind"),
    groupKind: document.getElementById("groupKind"),
    editGroupModal: document.getElementById("editGroupModal"),
    closeEditGroupModalBtn: document.getElementById("closeEditGroupModalBtn"),
    editGroupForm: document.getElementById("editGroupForm"),
    editGroupId: document.getElementById("editGroupId"),
    editGroupName: document.getElementById("editGroupName"),
    editGroupAccentColor: document.getElementById("editGroupAccentColor"),
    editGroupAccentColorHex: document.getElementById("editGroupAccentColorHex"),
    editCategoryModal: document.getElementById("editCategoryModal"),
    closeEditCategoryModalBtn: document.getElementById("closeEditCategoryModalBtn"),
    editCategoryForm: document.getElementById("editCategoryForm"),
    editCategoryName: document.getElementById("editCategoryName"),
    editCategoryIcon: document.getElementById("editCategoryIcon"),
    editCategoryIconToggle: document.getElementById("editCategoryIconToggle"),
    editCategoryIconPopover: document.getElementById("editCategoryIconPopover"),
    editCategoryGroup: document.getElementById("editCategoryGroup"),
    editCategoryGroupField: document.getElementById("editCategoryGroupField"),
    editCategoryGroupSearch: document.getElementById("editCategoryGroupSearch"),
    editCategoryGroupPickerBlock: document.getElementById("editCategoryGroupPickerBlock"),
    editCategoryGroupAll: document.getElementById("editCategoryGroupAll"),
    editCategoryKindSwitch: document.getElementById("editCategoryKindSwitch"),
    editCategoryKind: document.getElementById("editCategoryKind"),
    createModal: document.getElementById("createModal"),
    closeCreateModalBtn: document.getElementById("closeCreateModalBtn"),
    createForm: document.getElementById("createOperationForm"),
    createEntryModeSwitch: document.getElementById("createEntryModeSwitch"),
    opEntryMode: document.getElementById("opEntryMode"),
    createKindSwitch: document.getElementById("createKindSwitch"),
    createPreviewHeadOperation: document.getElementById("createPreviewHeadOperation"),
    createPreviewHeadDebt: document.getElementById("createPreviewHeadDebt"),
    createPreviewBody: document.getElementById("createPreviewBody"),
    opKind: document.getElementById("opKind"),
    opCategory: document.getElementById("opCategory"),
    opCategorySearch: document.getElementById("opCategorySearch"),
    createCategoryField: document.getElementById("createCategoryField"),
    opCategoryAll: document.getElementById("opCategoryAll"),
    createCategoryPickerBlock: document.getElementById("createCategoryPickerBlock"),
    createDebtFields: document.getElementById("createDebtFields"),
    createDebtDirectionSwitch: document.getElementById("createDebtDirectionSwitch"),
    debtCounterparty: document.getElementById("debtCounterparty"),
    debtDirection: document.getElementById("debtDirection"),
    debtPrincipal: document.getElementById("debtPrincipal"),
    debtStartDate: document.getElementById("debtStartDate"),
    debtDueDate: document.getElementById("debtDueDate"),
    debtDueHint: document.getElementById("debtDueHint"),
    debtNote: document.getElementById("debtNote"),
    editModal: document.getElementById("editModal"),
    closeEditModalBtn: document.getElementById("closeEditModalBtn"),
    editForm: document.getElementById("editOperationForm"),
    editKindSwitch: document.getElementById("editKindSwitch"),
    editKind: document.getElementById("editKind"),
    editCategory: document.getElementById("editCategory"),
    editPreviewBody: document.getElementById("editPreviewBody"),
    batchCreateModal: document.getElementById("batchCreateModal"),
    closeBatchCreateModalBtn: document.getElementById("closeBatchCreateModalBtn"),
    batchCreateForm: document.getElementById("batchCreateForm"),
    batchCreateInput: document.getElementById("batchCreateInput"),
    bulkEditOperationsModal: document.getElementById("bulkEditOperationsModal"),
    closeBulkEditOperationsModalBtn: document.getElementById("closeBulkEditOperationsModalBtn"),
    bulkEditOperationsForm: document.getElementById("bulkEditOperationsForm"),
    bulkOpKind: document.getElementById("bulkOpKind"),
    bulkOpCategory: document.getElementById("bulkOpCategory"),
    bulkOpDate: document.getElementById("bulkOpDate"),
    bulkEditCategoriesModal: document.getElementById("bulkEditCategoriesModal"),
    closeBulkEditCategoriesModalBtn: document.getElementById("closeBulkEditCategoriesModalBtn"),
    bulkEditCategoriesForm: document.getElementById("bulkEditCategoriesForm"),
    bulkCategoryGroup: document.getElementById("bulkCategoryGroup"),
    confirmModal: document.getElementById("confirmModal"),
    confirmText: document.getElementById("confirmText"),
    confirmCancelBtn: document.getElementById("confirmCancelBtn"),
    confirmDeleteBtn: document.getElementById("confirmDeleteBtn"),
    debtRepaymentModal: document.getElementById("debtRepaymentModal"),
    closeDebtRepaymentModalBtn: document.getElementById("closeDebtRepaymentModalBtn"),
    debtRepaymentForm: document.getElementById("debtRepaymentForm"),
    repaymentDebtId: document.getElementById("repaymentDebtId"),
    repaymentDirection: document.getElementById("repaymentDirection"),
    repaymentCounterparty: document.getElementById("repaymentCounterparty"),
    repaymentOutstanding: document.getElementById("repaymentOutstanding"),
    repaymentProgressBar: document.getElementById("repaymentProgressBar"),
    repaymentPresetRow: document.getElementById("repaymentPresetRow"),
    repaymentAmount: document.getElementById("repaymentAmount"),
    repaymentBeforeValue: document.getElementById("repaymentBeforeValue"),
    repaymentAfterValue: document.getElementById("repaymentAfterValue"),
    repaymentCarryRow: document.getElementById("repaymentCarryRow"),
    repaymentCarryValue: document.getElementById("repaymentCarryValue"),
    repaymentDate: document.getElementById("repaymentDate"),
    repaymentNote: document.getElementById("repaymentNote"),
    submitDebtRepaymentBtn: document.getElementById("submitDebtRepaymentBtn"),
    editDebtModal: document.getElementById("editDebtModal"),
    closeEditDebtModalBtn: document.getElementById("closeEditDebtModalBtn"),
    editDebtForm: document.getElementById("editDebtForm"),
    editDebtId: document.getElementById("editDebtId"),
    editDebtCounterparty: document.getElementById("editDebtCounterparty"),
    editDebtDirection: document.getElementById("editDebtDirection"),
    editDebtPrincipal: document.getElementById("editDebtPrincipal"),
    editDebtStartDate: document.getElementById("editDebtStartDate"),
    editDebtDueDate: document.getElementById("editDebtDueDate"),
    editDebtNote: document.getElementById("editDebtNote"),
    submitEditDebtBtn: document.getElementById("submitEditDebtBtn"),
    debtHistoryModal: document.getElementById("debtHistoryModal"),
    closeDebtHistoryModalBtn: document.getElementById("closeDebtHistoryModalBtn"),
    debtHistoryCounterparty: document.getElementById("debtHistoryCounterparty"),
    debtHistoryDirection: document.getElementById("debtHistoryDirection"),
    debtHistoryOutstanding: document.getElementById("debtHistoryOutstanding"),
    debtHistoryList: document.getElementById("debtHistoryList"),
    toastArea: document.getElementById("toastArea"),
  };

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

  function showLogin(message = "") {
    el.loginScreen.classList.remove("hidden");
    el.appShell.classList.add("hidden");
    if (message) {
      setStatus(message, true);
      return;
    }
    hideLoginAlert();
  }

  function showApp() {
    el.loginScreen.classList.add("hidden");
    el.appShell.classList.remove("hidden");
    hideLoginAlert();
  }

  function closeAllMenus() {
    // user dropdown is intentionally removed; keep API for backward compatibility
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

  function formatAmount(value) {
    const num = Number(value);
    if (Number.isNaN(num)) {
      return "0.00";
    }
    return num.toFixed(2);
  }

  const CURRENCY_META = {
    BYN: { symbol: "Br" },
    RUB: { symbol: "₽" },
    USD: { symbol: "$" },
    EUR: { symbol: "€" },
    GBP: { symbol: "£" },
  };

  function getUiSettings() {
    const ui = state.preferences?.data?.ui || {};
    const scale = Number(ui.scale_percent || 100);
    return {
      currency: String(ui.currency || "BYN").toUpperCase(),
      currencyPosition: ui.currency_position === "prefix" ? "prefix" : "suffix",
      showDashboardDebts: ui.show_dashboard_debts !== false,
      scalePercent: Number.isFinite(scale) ? Math.max(90, Math.min(115, Math.round(scale / 5) * 5)) : 100,
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

  function getCurrencyConfig() {
    const ui = getUiSettings();
    return resolveCurrencyConfig(ui.currency, ui.currencyPosition);
  }

  function formatMoney(value, options = {}) {
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
      : getCurrencyConfig();
    return cfg.position === "prefix" ? `${cfg.symbol} ${formatted}` : `${formatted} ${cfg.symbol}`;
  }

  function applyUiScale(scalePercent) {
    const normalized = Math.max(90, Math.min(115, Number(scalePercent || 100)));
    document.documentElement.style.setProperty("--ui-scale", String(normalized / 100));
    document.body.style.zoom = `${normalized}%`;
    if (el.uiScaleRange) {
      el.uiScaleRange.value = String(normalized);
    }
    if (el.uiScaleValue) {
      el.uiScaleValue.textContent = `${normalized}%`;
    }
  }

  function applyMoneyInputs(config = null) {
    const cfg = config || getCurrencyConfig();
    document.querySelectorAll("[data-money-input-wrap]").forEach((node) => {
      node.dataset.currencySymbol = cfg.symbol;
      node.classList.toggle("currency-prefix", cfg.position === "prefix");
      node.classList.toggle("currency-suffix", cfg.position !== "prefix");
    });
    if (el.currencyPreview) {
      el.currencyPreview.textContent = `Пример: ${formatMoney(1234.56, { currency: cfg.code, position: cfg.position })}`;
    }
  }

  function isDashboardDebtsVisible() {
    return getUiSettings().showDashboardDebts;
  }

  function formatDateRu(value) {
    if (!value) {
      return "";
    }
    const [year, month, day] = String(value).split("-");
    if (!year || !month || !day) {
      return String(value);
    }
    return `${day}.${month}.${year}`;
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

  function formatIsoDateLocal(value) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
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

  function getPreferenceTimeZone() {
    const saved = state.preferences?.data?.ui?.timezone;
    if (!saved || saved === "auto") {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    }
    return saved;
  }

  function getPeriodBounds(period) {
    const now = new Date();
    const timeZone = getPreferenceTimeZone();
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

  window.App = {
    state,
    el,
    core: {
      setStatus,
      authHeaders,
      showLogin,
      showApp,
      closeAllMenus,
      syncSegmentedActive,
      syncAllPeriodTabs,
      formatAmount,
      formatMoney,
      formatDateRu,
      kindLabel,
      formatPeriodLabel,
      getPreferenceTimeZone,
      getCurrencyConfig,
      resolveCurrencyConfig,
      getUiSettings,
      applyUiScale,
      applyMoneyInputs,
      isDashboardDebtsVisible,
      getPeriodBounds,
      hideLoginAlert,
      showLoginAlert,
      inferStatusType,
    },
    actions: {},
  };
})();
