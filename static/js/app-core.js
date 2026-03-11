(() => {
  const state = {
    token: localStorage.getItem("access_token") || "",
    mobileNavOpen: false,
    sectionBackStack: [],
    telegramBotUsername: "",
    browserTelegramLoginAvailable: false,
    telegramWebAppReady: false,
    telegramWebAppAvailable: false,
    browserTelegramLoginReady: false,
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
    debtSortPreset: "priority",
    debtCardsCache: [],
    debtCardsPageSize: 20,
    debtCardsVisibleLimit: 20,
    debtCardsVisibleTotal: 0,
    debtCardsHasMore: false,
    debtHistoryPageSize: 20,
    debtHistoryVisibleLimit: 20,
    debtHistoryEvents: [],
    debtHistoryMeta: null,
    debtHistoryHasMore: false,
    editDebtCreateId: null,
    editOperationId: null,
    editCategoryId: null,
    period: "day",
    customDateFrom: "",
    customDateTo: "",
    filterKind: "",
    operationsQuickView: "all",
    operationsCategoryFilterId: null,
    operationsCategoryFilterName: "",
    operationSortPreset: "date",
    activeSection: "dashboard",
    categoryFilterKind: "all",
    categories: [],
    categoryGroups: [],
    selectedOperationIds: new Set(),
    pendingCreateCategoryFromOperation: "",
    pendingConfirm: null,
    toasts: new Map(),
    lastErrorToast: { message: "", ts: 0 },
    uiRequestCache: new Map(),
    createReceiptItems: [],
    createReceiptSeq: 0,
    editReceiptItems: [],
    editReceiptSeq: 0,
    itemCatalogItems: [],
    itemCatalogSortPreset: "usage",
    editItemTemplateId: null,
    editItemSourceName: "",
    analyticsMonthAnchor: "",
    analyticsTab: "overview",
    analyticsCalendarView: "month",
    analyticsGlobalPeriod: "month",
    analyticsGlobalDateFrom: "",
    analyticsGlobalDateTo: "",
    analyticsGlobalPendingCustom: false,
    analyticsCategoryKind: "expense",
    analyticsGranularity: "day",
    analyticsTopOperationsLimit: 5,
    analyticsTopPositionsLimit: 10,
    dashboardAnalyticsPeriod: "month",
    isAdmin: false,
    accessStatus: "pending",
    adminUserStatusFilter: "pending",
    batchOperationPlan: null,
    batchCategoryPlan: null,
    batchItemTemplatePlan: null,
  };

  const el = {
    loginScreen: document.getElementById("loginScreen"),
    appShell: document.getElementById("appShell"),
    loginAlert: document.getElementById("loginAlert"),
    loginTelegramHint: document.getElementById("loginTelegramHint"),
    telegramBrowserLoginWrap: document.getElementById("telegramBrowserLoginWrap"),
    telegramBrowserLogin: document.getElementById("telegramBrowserLogin"),
    mobileNavToggleBtn: document.getElementById("mobileNavToggleBtn"),
    sectionBackBtn: document.getElementById("sectionBackBtn"),
    sectionBackLabel: document.getElementById("sectionBackLabel"),
    mobileNavCloseBtn: document.getElementById("mobileNavCloseBtn"),
    mobileNavOverlay: document.getElementById("mobileNavOverlay"),
    sidebarNav: document.getElementById("sidebarNav"),
    telegramLoginBtn: document.getElementById("telegramLoginBtn"),
    mainNav: document.getElementById("mainNav"),
    adminNavBtn: document.getElementById("adminNavBtn"),
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
    operationsQuickViewTabs: document.getElementById("operationsQuickViewTabs"),
    operationsSortTabs: document.getElementById("operationsSortTabs"),
    filterQ: document.getElementById("filterQ"),
    addOperationCta: document.getElementById("addOperationCta"),
    batchOperationCta: document.getElementById("batchOperationCta"),
    openOperationsTabBtn: document.getElementById("openOperationsTabBtn"),
    openDebtsTabBtn: document.getElementById("openDebtsTabBtn"),
    openAnalyticsTabBtn: document.getElementById("openAnalyticsTabBtn"),
    operationsBody: document.getElementById("operationsBody"),
    dashboardOperationsBody: document.getElementById("dashboardOperationsBody"),
    dashboardDebtsPanel: document.getElementById("dashboardDebtsPanel"),
    dashboardDebtsList: document.getElementById("dashboardDebtsList"),
    dashboardAnalyticsPanel: document.getElementById("dashboardAnalyticsPanel"),
    dashboardOperationsPanel: document.getElementById("dashboardOperationsPanel"),
    dashboardAnalyticsChartWrap: document.getElementById("dashboardAnalyticsChartWrap"),
    dashboardAnalyticsSparkline: document.getElementById("dashboardAnalyticsSparkline"),
    dashboardAnalyticsEmpty: document.getElementById("dashboardAnalyticsEmpty"),
    dashboardAnalyticsPeriodTabs: document.getElementById("dashboardAnalyticsPeriodTabs"),
    dashboardAnalyticsPeriodLabel: document.getElementById("dashboardAnalyticsPeriodLabel"),
    dashboardAnalyticsIncomeDelta: document.getElementById("dashboardAnalyticsIncomeDelta"),
    dashboardAnalyticsIncomeMeta: document.getElementById("dashboardAnalyticsIncomeMeta"),
    dashboardAnalyticsExpenseDelta: document.getElementById("dashboardAnalyticsExpenseDelta"),
    dashboardAnalyticsExpenseMeta: document.getElementById("dashboardAnalyticsExpenseMeta"),
    dashboardAnalyticsBalanceDelta: document.getElementById("dashboardAnalyticsBalanceDelta"),
    dashboardAnalyticsBalanceMeta: document.getElementById("dashboardAnalyticsBalanceMeta"),
    operationsSelectAll: document.getElementById("operationsSelectAll"),
    dashboardPeriodLabel: document.getElementById("dashboardPeriodLabel"),
    operationsPeriodLabel: document.getElementById("operationsPeriodLabel"),
    operationsSummaryGrid: document.getElementById("operationsSummaryGrid"),
    operationsIncomeTotal: document.getElementById("operationsIncomeTotal"),
    operationsExpenseTotal: document.getElementById("operationsExpenseTotal"),
    operationsBalanceTotal: document.getElementById("operationsBalanceTotal"),
    operationsTotalCount: document.getElementById("operationsTotalCount"),
    selectVisibleOperationsBtn: document.getElementById("selectVisibleOperationsBtn"),
    clearVisibleOperationsSelectionBtn: document.getElementById("clearVisibleOperationsSelectionBtn"),
    quickFilterExpenseBtn: document.getElementById("quickFilterExpenseBtn"),
    quickFilterIncomeBtn: document.getElementById("quickFilterIncomeBtn"),
    quickCustomRangeBtn: document.getElementById("quickCustomRangeBtn"),
    operationsBulkBar: document.getElementById("operationsBulkBar"),
    resetOperationsFiltersBtn: document.getElementById("resetOperationsFiltersBtn"),
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
    dashboardDebtKpiGrid: document.getElementById("dashboardDebtKpiGrid"),
    userAvatar: document.getElementById("userAvatar"),
    userName: document.getElementById("userName"),
    userHandle: document.getElementById("userHandle"),
    sidebarLogoutBtn: document.getElementById("sidebarLogoutBtn"),
    dashboardSection: document.getElementById("dashboardSection"),
    analyticsSection: document.getElementById("analyticsSection"),
    operationsSection: document.getElementById("operationsSection"),
    debtsSection: document.getElementById("debtsSection"),
    categoriesSection: document.getElementById("categoriesSection"),
    itemCatalogSection: document.getElementById("itemCatalogSection"),
    settingsSection: document.getElementById("settingsSection"),
    adminSection: document.getElementById("adminSection"),
    settingsForm: document.getElementById("settingsForm"),
    timezoneSelect: document.getElementById("timezoneSelect"),
    currencySelect: document.getElementById("currencySelect"),
    currencyPositionSelect: document.getElementById("currencyPositionSelect"),
    currencyPreview: document.getElementById("currencyPreview"),
    showDashboardAnalyticsToggle: document.getElementById("showDashboardAnalyticsToggle"),
    showDashboardOperationsToggle: document.getElementById("showDashboardOperationsToggle"),
    showDashboardDebtsToggle: document.getElementById("showDashboardDebtsToggle"),
    dashboardOperationsLimitSelect: document.getElementById("dashboardOperationsLimitSelect"),
    analyticsTopOperationsLimitSelect: document.getElementById("analyticsTopOperationsLimitSelect"),
    analyticsTopPositionsLimitSelect: document.getElementById("analyticsTopPositionsLimitSelect"),
    uiScaleRange: document.getElementById("uiScaleRange"),
    uiScaleValue: document.getElementById("uiScaleValue"),
    resetUiScaleBtn: document.getElementById("resetUiScaleBtn"),
    deleteMePhrase: document.getElementById("deleteMePhrase"),
    deleteMeBtn: document.getElementById("deleteMeBtn"),
    saveSettingsBtn: document.getElementById("saveSettingsBtn"),
    categoriesBody: document.getElementById("categoriesBody"),
    categoryKindTabs: document.getElementById("categoryKindTabs"),
    categorySearchQ: document.getElementById("categorySearchQ"),
    categoriesCollapseAllBtn: document.getElementById("categoriesCollapseAllBtn"),
    categoriesExpandAllBtn: document.getElementById("categoriesExpandAllBtn"),
    deleteAllCategoriesBtn: document.getElementById("deleteAllCategoriesBtn"),
    addGroupCta: document.getElementById("addGroupCta"),
    addCategoryCta: document.getElementById("addCategoryCta"),
    batchCategoryCta: document.getElementById("batchCategoryCta"),
    addDebtCta: document.getElementById("addDebtCta"),
    addItemTemplateCta: document.getElementById("addItemTemplateCta"),
    addItemSourceCta: document.getElementById("addItemSourceCta"),
    batchItemCatalogCta: document.getElementById("batchItemCatalogCta"),
    debtSearchQ: document.getElementById("debtSearchQ"),
    itemCatalogSearchQ: document.getElementById("itemCatalogSearchQ"),
    itemCatalogSortTabs: document.getElementById("itemCatalogSortTabs"),
    itemCatalogCollapseAllBtn: document.getElementById("itemCatalogCollapseAllBtn"),
    itemCatalogExpandAllBtn: document.getElementById("itemCatalogExpandAllBtn"),
    deleteAllItemTemplatesBtn: document.getElementById("deleteAllItemTemplatesBtn"),
    itemCatalogBody: document.getElementById("itemCatalogBody"),
    debtStatusTabs: document.getElementById("debtStatusTabs"),
    debtSortTabs: document.getElementById("debtSortTabs"),
    debtsCards: document.getElementById("debtsCards"),
    debtsInfiniteSentinel: document.getElementById("debtsInfiniteSentinel"),
    analyticsMonthLabel: document.getElementById("analyticsMonthLabel"),
    analyticsCalendarViewTabs: document.getElementById("analyticsCalendarViewTabs"),
    analyticsPrevGridBtn: document.getElementById("analyticsPrevGridBtn"),
    analyticsTodayGridBtn: document.getElementById("analyticsTodayGridBtn"),
    analyticsNextGridBtn: document.getElementById("analyticsNextGridBtn"),
    analyticsViewTabs: document.getElementById("analyticsViewTabs"),
    analyticsGlobalScopePanel: document.getElementById("analyticsGlobalScopePanel"),
    analyticsGlobalRangeLabel: document.getElementById("analyticsGlobalRangeLabel"),
    analyticsGlobalPeriodTabs: document.getElementById("analyticsGlobalPeriodTabs"),
    analyticsOverviewPanel: document.getElementById("analyticsOverviewPanel"),
    analyticsStructurePanel: document.getElementById("analyticsStructurePanel"),
    analyticsCalendarPanel: document.getElementById("analyticsCalendarPanel"),
    analyticsOperationsPanel: document.getElementById("analyticsOperationsPanel"),
    analyticsTrendsPanel: document.getElementById("analyticsTrendsPanel"),
    analyticsSummaryRangeLabel: document.getElementById("analyticsSummaryRangeLabel"),
    analyticsKpiPrimary: document.getElementById("analyticsKpiPrimary"),
    analyticsKpiSecondary: document.getElementById("analyticsKpiSecondary"),
    analyticsCategoryKindTabs: document.getElementById("analyticsCategoryKindTabs"),
    analyticsCategoryBreakdownLabel: document.getElementById("analyticsCategoryBreakdownLabel"),
    analyticsCategoryBreakdownChart: document.getElementById("analyticsCategoryBreakdownChart"),
    analyticsCategoryBreakdownSvg: document.getElementById("analyticsCategoryBreakdownSvg"),
    analyticsCategoryBreakdownChartTitle: document.getElementById("analyticsCategoryBreakdownChartTitle"),
    analyticsCategoryBreakdownChartValue: document.getElementById("analyticsCategoryBreakdownChartValue"),
    analyticsCategoryBreakdownChartMeta: document.getElementById("analyticsCategoryBreakdownChartMeta"),
    analyticsCategoryBreakdownList: document.getElementById("analyticsCategoryBreakdownList"),
    analyticsCalendarTotalsTitle: document.getElementById("analyticsCalendarTotalsTitle"),
    analyticsCalendarTotalsRangeLabel: document.getElementById("analyticsCalendarTotalsRangeLabel"),
    analyticsCalendarTotals: document.getElementById("analyticsCalendarTotals"),
    analyticsCalendarTotalsSecondary: document.getElementById("analyticsCalendarTotalsSecondary"),
    analyticsTopOperationsList: document.getElementById("analyticsTopOperationsList"),
    analyticsTopCategoriesTitle: document.getElementById("analyticsTopCategoriesTitle"),
    analyticsTopCategoriesSubtitle: document.getElementById("analyticsTopCategoriesSubtitle"),
    analyticsTopCategoriesList: document.getElementById("analyticsTopCategoriesList"),
    analyticsAnomaliesList: document.getElementById("analyticsAnomaliesList"),
    analyticsTopPositionsList: document.getElementById("analyticsTopPositionsList"),
    analyticsPriceIncreasesList: document.getElementById("analyticsPriceIncreasesList"),
    operationsActiveFilters: document.getElementById("operationsActiveFilters"),
    operationsKindFilterChip: document.getElementById("operationsKindFilterChip"),
    operationsQuickViewChip: document.getElementById("operationsQuickViewChip"),
    operationsCategoryFilterChip: document.getElementById("operationsCategoryFilterChip"),
    clearOperationsCategoryFilterBtn: document.getElementById("clearOperationsCategoryFilterBtn"),
    analyticsCalendarBody: document.getElementById("analyticsCalendarBody"),
    analyticsCalendarScrollWrap: document.getElementById("analyticsCalendarScrollWrap"),
    analyticsMonthGridWrap: document.getElementById("analyticsMonthGridWrap"),
    analyticsYearGridWrap: document.getElementById("analyticsYearGridWrap"),
    analyticsYearGrid: document.getElementById("analyticsYearGrid"),
    analyticsGridMonthPickerWrap: document.getElementById("analyticsGridMonthPickerWrap"),
    analyticsGridMonthPicker: document.getElementById("analyticsGridMonthPicker"),
    analyticsGridYearPicker: document.getElementById("analyticsGridYearPicker"),
    analyticsGranularityTabs: document.getElementById("analyticsGranularityTabs"),
    analyticsTrendRangeLabel: document.getElementById("analyticsTrendRangeLabel"),
    analyticsTrendChart: document.getElementById("analyticsTrendChart"),
    analyticsIncomeDelta: document.getElementById("analyticsIncomeDelta"),
    analyticsExpenseDelta: document.getElementById("analyticsExpenseDelta"),
    analyticsBalanceDelta: document.getElementById("analyticsBalanceDelta"),
    analyticsOpsDelta: document.getElementById("analyticsOpsDelta"),
    adminUserStatusTabs: document.getElementById("adminUserStatusTabs"),
    adminUsersBody: document.getElementById("adminUsersBody"),
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
    opReceiptBlock: document.getElementById("opReceiptBlock"),
    opReceiptEnabled: document.getElementById("opReceiptEnabled"),
    opReceiptFields: document.getElementById("opReceiptFields"),
    receiptItemsList: document.getElementById("receiptItemsList"),
    receiptTotalValue: document.getElementById("receiptTotalValue"),
    receiptDiffValue: document.getElementById("receiptDiffValue"),
    pullReceiptTotalBtn: document.getElementById("pullReceiptTotalBtn"),
    editReceiptBlock: document.getElementById("editReceiptBlock"),
    editReceiptEnabled: document.getElementById("editReceiptEnabled"),
    editReceiptFields: document.getElementById("editReceiptFields"),
    editReceiptItemsList: document.getElementById("editReceiptItemsList"),
    editReceiptTotalValue: document.getElementById("editReceiptTotalValue"),
    editReceiptDiffValue: document.getElementById("editReceiptDiffValue"),
    editPullReceiptTotalBtn: document.getElementById("editPullReceiptTotalBtn"),
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
    editCategoryField: document.getElementById("editCategoryField"),
    editCategorySearch: document.getElementById("editCategorySearch"),
    editCategoryPickerBlock: document.getElementById("editCategoryPickerBlock"),
    editCategoryAll: document.getElementById("editCategoryAll"),
    editPreviewBody: document.getElementById("editPreviewBody"),
    batchCreateModal: document.getElementById("batchCreateModal"),
    closeBatchCreateModalBtn: document.getElementById("closeBatchCreateModalBtn"),
    batchCreateForm: document.getElementById("batchCreateForm"),
    batchCreateInput: document.getElementById("batchCreateInput"),
    batchCreateHint: document.getElementById("batchCreateHint"),
    batchCreateFeedback: document.getElementById("batchCreateFeedback"),
    batchCreatePreview: document.getElementById("batchCreatePreview"),
    batchCreatePreviewBody: document.getElementById("batchCreatePreviewBody"),
    previewBatchCreateBtn: document.getElementById("previewBatchCreateBtn"),
    confirmBatchCreateBtn: document.getElementById("confirmBatchCreateBtn"),
    bulkEditOperationsModal: document.getElementById("bulkEditOperationsModal"),
    closeBulkEditOperationsModalBtn: document.getElementById("closeBulkEditOperationsModalBtn"),
    bulkEditOperationsForm: document.getElementById("bulkEditOperationsForm"),
    bulkOpKind: document.getElementById("bulkOpKind"),
    bulkOpCategory: document.getElementById("bulkOpCategory"),
    bulkOpDate: document.getElementById("bulkOpDate"),
    batchCategoryModal: document.getElementById("batchCategoryModal"),
    closeBatchCategoryModalBtn: document.getElementById("closeBatchCategoryModalBtn"),
    batchCategoryForm: document.getElementById("batchCategoryForm"),
    batchCategoryModeTabs: document.getElementById("batchCategoryModeTabs"),
    batchCategoryMode: document.getElementById("batchCategoryMode"),
    batchCategoryHint: document.getElementById("batchCategoryHint"),
    batchCategoryInput: document.getElementById("batchCategoryInput"),
    batchCategoryFeedback: document.getElementById("batchCategoryFeedback"),
    batchCategoryPreview: document.getElementById("batchCategoryPreview"),
    batchCategoryPreviewBody: document.getElementById("batchCategoryPreviewBody"),
    previewBatchCategoryBtn: document.getElementById("previewBatchCategoryBtn"),
    confirmBatchCategoryBtn: document.getElementById("confirmBatchCategoryBtn"),
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
    debtHistoryModal: document.getElementById("debtHistoryModal"),
    closeDebtHistoryModalBtn: document.getElementById("closeDebtHistoryModalBtn"),
    debtHistoryCounterparty: document.getElementById("debtHistoryCounterparty"),
    debtHistoryDirection: document.getElementById("debtHistoryDirection"),
    debtHistoryOutstanding: document.getElementById("debtHistoryOutstanding"),
    debtHistoryList: document.getElementById("debtHistoryList"),
    debtHistoryItems: document.getElementById("debtHistoryItems"),
    debtHistoryInfiniteSentinel: document.getElementById("debtHistoryInfiniteSentinel"),
    operationReceiptModal: document.getElementById("operationReceiptModal"),
    closeOperationReceiptModalBtn: document.getElementById("closeOperationReceiptModalBtn"),
    operationReceiptMeta: document.getElementById("operationReceiptMeta"),
    operationReceiptItems: document.getElementById("operationReceiptItems"),
    itemTemplateModal: document.getElementById("itemTemplateModal"),
    closeItemTemplateModalBtn: document.getElementById("closeItemTemplateModalBtn"),
    itemTemplateForm: document.getElementById("itemTemplateForm"),
    itemTemplateModalTitle: document.getElementById("itemTemplateModalTitle"),
    itemTemplateSource: document.getElementById("itemTemplateSource"),
    itemTemplateSourceField: document.getElementById("itemTemplateSourceField"),
    itemTemplateSourceSearch: document.getElementById("itemTemplateSourceSearch"),
    itemTemplateSourcePickerBlock: document.getElementById("itemTemplateSourcePickerBlock"),
    itemTemplateSourceAll: document.getElementById("itemTemplateSourceAll"),
    itemTemplateName: document.getElementById("itemTemplateName"),
    itemTemplatePrice: document.getElementById("itemTemplatePrice"),
    itemTemplatePriceDate: document.getElementById("itemTemplatePriceDate"),
    itemTemplatePreviewBody: document.getElementById("itemTemplatePreviewBody"),
    sourceGroupModal: document.getElementById("sourceGroupModal"),
    closeSourceGroupModalBtn: document.getElementById("closeSourceGroupModalBtn"),
    sourceGroupForm: document.getElementById("sourceGroupForm"),
    sourceGroupName: document.getElementById("sourceGroupName"),
    sourceGroupPreviewBody: document.getElementById("sourceGroupPreviewBody"),
    itemTemplateHistoryModal: document.getElementById("itemTemplateHistoryModal"),
    closeItemTemplateHistoryModalBtn: document.getElementById("closeItemTemplateHistoryModalBtn"),
    itemTemplateHistoryTitle: document.getElementById("itemTemplateHistoryTitle"),
    itemTemplateHistoryMeta: document.getElementById("itemTemplateHistoryMeta"),
    itemTemplateHistoryBody: document.getElementById("itemTemplateHistoryBody"),
    sourceGroupTitle: document.getElementById("sourceGroupTitle"),
    sourceGroupOriginalName: document.getElementById("sourceGroupOriginalName"),
    submitSourceGroupBtn: document.getElementById("submitSourceGroupBtn"),
    batchItemTemplateModal: document.getElementById("batchItemTemplateModal"),
    closeBatchItemTemplateModalBtn: document.getElementById("closeBatchItemTemplateModalBtn"),
    batchItemTemplateForm: document.getElementById("batchItemTemplateForm"),
    batchItemTemplateInput: document.getElementById("batchItemTemplateInput"),
    batchItemTemplateFeedback: document.getElementById("batchItemTemplateFeedback"),
    batchItemTemplatePreview: document.getElementById("batchItemTemplatePreview"),
    batchItemTemplatePreviewBody: document.getElementById("batchItemTemplatePreviewBody"),
    previewBatchItemTemplateBtn: document.getElementById("previewBatchItemTemplateBtn"),
    confirmBatchItemTemplateBtn: document.getElementById("confirmBatchItemTemplateBtn"),
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
    setMobileNavOpen(false);
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
    setMobileNavOpen(false);
    hideLoginAlert();
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

  function getUiSettings() {
    const base = getCoreUtils().getUiSettings(state);
    const next = { ...base };

    if (el.currencySelect?.value) {
      next.currency = String(el.currencySelect.value || "BYN").toUpperCase();
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

  function getCurrencyConfig() {
    const ui = getUiSettings();
    return resolveCurrencyConfig(ui.currency, ui.currencyPosition);
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

  function applyUiScale(scalePercent) {
    getCoreUtils().applyUiScale(el, scalePercent);
  }

  function applyMoneyInputs(config = null) {
    getCoreUtils().applyMoneyInputs(el, state, config);
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
      formatMoney,
      evaluateMathExpression,
      resolveMoneyInput,
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
