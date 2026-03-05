(() => {
  const state = {
    token: localStorage.getItem("access_token") || "",
    preferences: null,
    page: 1,
    pageSize: 10,
    total: 0,
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
    createModalCategoryExpanded: false,
    pendingCreateCategoryFromOperation: "",
    pendingConfirm: null,
    toasts: new Map(),
  };

  const el = {
    loginScreen: document.getElementById("loginScreen"),
    appShell: document.getElementById("appShell"),
    loginOutput: document.getElementById("loginOutput"),
    appOutput: document.getElementById("appOutput"),
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
    operationsBody: document.getElementById("operationsBody"),
    dashboardOperationsBody: document.getElementById("dashboardOperationsBody"),
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
    incomeTotal: document.getElementById("incomeTotal"),
    expenseTotal: document.getElementById("expenseTotal"),
    balanceTotal: document.getElementById("balanceTotal"),
    userAvatar: document.getElementById("userAvatar"),
    userName: document.getElementById("userName"),
    userHandle: document.getElementById("userHandle"),
    userMenuToggle: document.getElementById("userMenuToggle"),
    userMenu: document.getElementById("userMenu"),
    openSettingsBtn: document.getElementById("openSettingsBtn"),
    logoutBtn: document.getElementById("logoutBtn"),
    dashboardSection: document.getElementById("dashboardSection"),
    operationsSection: document.getElementById("operationsSection"),
    categoriesSection: document.getElementById("categoriesSection"),
    settingsSection: document.getElementById("settingsSection"),
    settingsForm: document.getElementById("settingsForm"),
    timezoneSelect: document.getElementById("timezoneSelect"),
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
    editCategoryKindSwitch: document.getElementById("editCategoryKindSwitch"),
    editCategoryKind: document.getElementById("editCategoryKind"),
    createModal: document.getElementById("createModal"),
    closeCreateModalBtn: document.getElementById("closeCreateModalBtn"),
    createForm: document.getElementById("createOperationForm"),
    createKindSwitch: document.getElementById("createKindSwitch"),
    createPreviewBody: document.getElementById("createPreviewBody"),
    opKind: document.getElementById("opKind"),
    opCategory: document.getElementById("opCategory"),
    opCategorySearch: document.getElementById("opCategorySearch"),
    opCategoryQuick: document.getElementById("opCategoryQuick"),
    opCategoryAll: document.getElementById("opCategoryAll"),
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
    toastArea: document.getElementById("toastArea"),
  };

  function setStatus(message, forLogin = false) {
    if (forLogin) {
      el.loginOutput.textContent = message;
      return;
    }
    el.appOutput.textContent = message;
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
    }
  }

  function showApp() {
    el.loginScreen.classList.add("hidden");
    el.appShell.classList.remove("hidden");
  }

  function closeAllMenus() {
    el.userMenu.classList.add("hidden");
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
      formatDateRu,
      kindLabel,
      formatPeriodLabel,
      getPreferenceTimeZone,
      getPeriodBounds,
    },
    actions: {},
  };
})();
