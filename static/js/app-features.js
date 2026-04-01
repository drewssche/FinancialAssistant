(() => {
  function getRuntimeModule(name) {
    return window.App.getRuntimeModule?.(name) || {};
  }

  const dashboardFeatures = getRuntimeModule("dashboard");
  const analyticsFeatures = getRuntimeModule("analytics");
  const adminFeatures = getRuntimeModule("admin");
  const debtFeatures = getRuntimeModule("debts");
  const plansFeatures = getRuntimeModule("plans");
  const sessionFeatures = getRuntimeModule("session");
  const itemCatalogFeatures = getRuntimeModule("item-catalog");
  const operationsFeatures = getRuntimeModule("operations");
  const operationModal = getRuntimeModule("operation-modal");

  const updateCreatePreview = operationModal.updateCreatePreview;
  const updateDebtDueHint = operationModal.updateDebtDueHint;
  const updateEditPreview = operationModal.updateEditPreview;
  const renderCreateCategoryPicker = operationModal.renderCreateCategoryPicker;
  const handleCreateCategoryPickerClick = operationModal.handleCreateCategoryPickerClick;
  const handleDebtCounterpartyPickerClick = operationModal.handleDebtCounterpartyPickerClick;
  const handleEditCategoryPickerClick = operationModal.handleEditCategoryPickerClick;
  const handleCreateCategorySearchFocus = operationModal.handleCreateCategorySearchFocus;
  const handleCreateCategorySearchInput = operationModal.handleCreateCategorySearchInput;
  const handleCreateCategorySearchKeydown = operationModal.handleCreateCategorySearchKeydown;
  const handleDebtCounterpartySearchFocus = operationModal.handleDebtCounterpartySearchFocus;
  const handleDebtCounterpartySearchInput = operationModal.handleDebtCounterpartySearchInput;
  const handleDebtCounterpartySearchKeydown = operationModal.handleDebtCounterpartySearchKeydown;
  const handleEditCategorySearchFocus = operationModal.handleEditCategorySearchFocus;
  const handleEditCategorySearchInput = operationModal.handleEditCategorySearchInput;
  const handleEditCategorySearchKeydown = operationModal.handleEditCategorySearchKeydown;
  const handleCreateCategoryOutsidePointer = operationModal.handleCreateCategoryOutsidePointer;
  const handleDebtCounterpartyOutsidePointer = operationModal.handleDebtCounterpartyOutsidePointer;
  const handleEditCategoryOutsidePointer = operationModal.handleEditCategoryOutsidePointer;
  const handleReceiptOutsidePointer = operationModal.handleReceiptOutsidePointer;
  const handleReceiptItemsListInput = operationModal.handleReceiptItemsListInput;
  const handleReceiptItemsListFocusIn = operationModal.handleReceiptItemsListFocusIn;
  const handleReceiptItemsListKeydown = operationModal.handleReceiptItemsListKeydown;
  const handleReceiptItemsListClick = operationModal.handleReceiptItemsListClick;
  const handlePullReceiptTotal = operationModal.handlePullReceiptTotal;
  const renderReceiptSummary = operationModal.renderReceiptSummary;
  const onCategoryCreated = operationModal.onCategoryCreated;
  const handleCreatePreviewClick = operationModal.handleCreatePreviewClick;
  const setOperationKind = operationModal.setOperationKind;
  const setCreateOperationMode = operationModal.setCreateOperationMode;
  const setEditOperationMode = operationModal.setEditOperationMode;
  const setDebtDirection = operationModal.setDebtDirection;
  const setCurrencySide = operationModal.setCurrencySide;
  const setCreateEntryMode = operationModal.setCreateEntryMode;
  const openCreateModal = operationModal.openCreateModal;
  const openCreateModalForDebtEdit = operationModal.openCreateModalForDebtEdit;
  const closeCreateModal = operationModal.closeCreateModal;
  const openEditModal = operationModal.openEditModal;
  const closeEditModal = operationModal.closeEditModal;
  const openPeriodCustomModal = operationModal.openPeriodCustomModal;
  const closePeriodCustomModal = operationModal.closePeriodCustomModal;
  const syncOperationCurrencyFields = operationModal.syncOperationCurrencyFields;
  const syncSuggestedOperationFxRate = operationModal.syncSuggestedOperationFxRate;
  const markCreateOperationFxRateManual = operationModal.markCreateOperationFxRateManual;
  const markEditOperationFxRateManual = operationModal.markEditOperationFxRateManual;
  const resetCreateOperationFxRateAutofill = operationModal.resetCreateOperationFxRateAutofill;
  const resetEditOperationFxRateAutofill = operationModal.resetEditOperationFxRateAutofill;
  const renderReceiptItems = operationModal.renderReceiptItems;
  const syncCurrencyTradeFieldUi = operationModal.syncCurrencyTradeFieldUi;
  const syncSuggestedCurrencyRate = operationModal.syncSuggestedCurrencyRate;
  const markCurrencyRateManual = operationModal.markCurrencyRateManual;
  const markCurrencyQuantitySource = operationModal.markCurrencyQuantitySource;
  const markCurrencyQuoteSource = operationModal.markCurrencyQuoteSource;
  const resetCurrencyRateAutofill = operationModal.resetCurrencyRateAutofill;
  const applyDebtCurrencyUi = operationModal.applyDebtCurrencyUi;

  const savePreferences = sessionFeatures.savePreferences;
  const savePreferencesDebounced = sessionFeatures.savePreferencesDebounced;
  const saveSettings = sessionFeatures.saveSettings;
  const previewInterfaceSettingsUi = sessionFeatures.previewInterfaceSettingsUi;
  const syncSettingsPickerButtons = sessionFeatures.syncSettingsPickerButtons;
  const openSettingsPickerModal = sessionFeatures.openSettingsPickerModal;
  const closeSettingsPickerModal = sessionFeatures.closeSettingsPickerModal;
  const applySettingsPickerValue = sessionFeatures.applySettingsPickerValue;
  const deleteMe = sessionFeatures.deleteMe;
  const logout = sessionFeatures.logout;
  const bootstrapApp = sessionFeatures.bootstrapApp;
  const telegramLogin = sessionFeatures.telegramLogin;
  const loadTelegramLoginConfig = sessionFeatures.loadTelegramLoginConfig;
  const tryAutoTelegramLogin = sessionFeatures.tryAutoTelegramLogin;

  const loadDashboard = dashboardFeatures.loadDashboard;
  const loadDashboardOperations = dashboardFeatures.loadDashboardOperations;
  const loadAnalyticsTrend = analyticsFeatures.loadAnalyticsTrend;
  const loadDashboardAnalyticsPreview = analyticsFeatures.loadDashboardAnalyticsPreview;
  const loadAnalyticsSection = analyticsFeatures.loadAnalyticsSection;
  const loadAnalyticsHighlights = analyticsFeatures.loadAnalyticsHighlights;
  const shiftAnalyticsMonth = analyticsFeatures.shiftAnalyticsMonth;
  const resetAnalyticsMonth = analyticsFeatures.resetAnalyticsMonth;
  const applyAnalyticsTabUi = analyticsFeatures.applyAnalyticsTabUi;
  const setAnalyticsTab = analyticsFeatures.setAnalyticsTab;
  const setAnalyticsCalendarView = analyticsFeatures.setAnalyticsCalendarView;
  const setAnalyticsGridMonthAnchor = analyticsFeatures.setAnalyticsGridMonthAnchor;
  const setAnalyticsGridYearAnchor = analyticsFeatures.setAnalyticsGridYearAnchor;
  const openAnalyticsMonth = analyticsFeatures.openAnalyticsMonth;
  const openOperationsForAnalyticsDate = analyticsFeatures.openOperationsForAnalyticsDate;
  const openOperationsForAnalyticsRange = analyticsFeatures.openOperationsForAnalyticsRange;
  const openOperationsForAnalyticsCategory = analyticsFeatures.openOperationsForAnalyticsCategory;
  const toggleCategoryBreakdownVisibility = analyticsFeatures.toggleCategoryBreakdownVisibility;
  const showAllCategoryBreakdownItems = analyticsFeatures.showAllCategoryBreakdownItems;
  const loadAdminUsers = adminFeatures.loadAdminUsers;
  const setAdminUserStatusFilter = adminFeatures.setAdminUserStatusFilter;
  const approveAdminUser = adminFeatures.approveAdminUser;
  const rejectAdminUser = adminFeatures.rejectAdminUser;
  const deleteAdminUser = adminFeatures.deleteAdminUser;

  const loadDebtsCards = debtFeatures.loadDebtsCards;
  const renderDebtCards = debtFeatures.renderDebtCards;
  const openDebtRepaymentModal = debtFeatures.openDebtRepaymentModal;
  const closeDebtRepaymentModal = debtFeatures.closeDebtRepaymentModal;
  const submitDebtRepayment = debtFeatures.submitDebtRepayment;
  const forgiveDebtFromRepaymentFlow = debtFeatures.forgiveDebtFromRepaymentFlow;
  const updateRepaymentDeltaHint = debtFeatures.updateRepaymentDeltaHint;
  const openDebtForgivenessModal = debtFeatures.openDebtForgivenessModal;
  const closeDebtForgivenessModal = debtFeatures.closeDebtForgivenessModal;
  const submitDebtForgiveness = debtFeatures.submitDebtForgiveness;
  const openDebtHistoryModal = debtFeatures.openDebtHistoryModal;
  const closeDebtHistoryModal = debtFeatures.closeDebtHistoryModal;
  const setDebtStatusFilter = debtFeatures.setDebtStatusFilter;
  const setDebtSortPreset = debtFeatures.setDebtSortPreset;
  const applyDebtSearch = debtFeatures.applyDebtSearch;
  const loadMoreDebtCards = debtFeatures.loadMoreDebtCards;
  const loadMoreDebtHistoryEvents = debtFeatures.loadMoreDebtHistoryEvents;
  const openEditDebtModal = debtFeatures.openEditDebtModal;
  const deleteDebtFlow = debtFeatures.deleteDebtFlow;

  const loadPlans = plansFeatures.loadPlans;
  const renderPlansSection = plansFeatures.renderPlansSection;
  const renderDashboardPlans = plansFeatures.renderDashboardPlans;
  const setDashboardPlansPeriod = plansFeatures.setDashboardPlansPeriod;
  const setPlansTab = plansFeatures.setPlansTab;
  const setPlansKindFilter = plansFeatures.setPlansKindFilter;
  const setPlansStatusFilter = plansFeatures.setPlansStatusFilter;
  const setPlansHistoryEventFilter = plansFeatures.setPlansHistoryEventFilter;
  const applyPlansSearch = plansFeatures.applyPlansSearch;
  const openCreatePlan = plansFeatures.openCreatePlan;
  const submitPlanForm = plansFeatures.submitPlanForm;
  const handlePlanActionClick = plansFeatures.handlePlanActionClick;
  const syncPlanRecurrenceUi = plansFeatures.syncPlanRecurrenceUi;
  const togglePlanWeekday = plansFeatures.togglePlanWeekday;

  const loadItemCatalog = itemCatalogFeatures.loadItemCatalog;
  const refreshItemCatalogView = itemCatalogFeatures.refreshItemCatalogView;
  const setItemCatalogSortPreset = itemCatalogFeatures.setItemCatalogSortPreset;
  const collapseAllItemCatalogGroups = itemCatalogFeatures.collapseAllItemCatalogGroups;
  const expandAllItemCatalogGroups = itemCatalogFeatures.expandAllItemCatalogGroups;
  const handleItemCatalogBodyClick = itemCatalogFeatures.handleItemCatalogBodyClick;
  const openItemTemplateModal = itemCatalogFeatures.openItemTemplateModal;
  const closeItemTemplateModal = itemCatalogFeatures.closeItemTemplateModal;
  const submitItemTemplateForm = itemCatalogFeatures.submitItemTemplateForm;
  const deleteItemTemplateFlow = itemCatalogFeatures.deleteItemTemplateFlow;
  const deleteAllItemTemplatesFlow = itemCatalogFeatures.deleteAllItemTemplatesFlow;
  const openSourceGroupModal = itemCatalogFeatures.openSourceGroupModal;
  const openEditSourceGroupModal = itemCatalogFeatures.openEditSourceGroupModal;
  const closeSourceGroupModal = itemCatalogFeatures.closeSourceGroupModal;
  const submitSourceGroupForm = itemCatalogFeatures.submitSourceGroupForm;
  const deleteItemSourceFlow = itemCatalogFeatures.deleteItemSourceFlow;
  const updateItemTemplatePreview = itemCatalogFeatures.updateItemTemplatePreview;
  const handleItemTemplateSourceSearchFocus = itemCatalogFeatures.handleItemTemplateSourceSearchFocus;
  const handleItemTemplateSourceSearchInput = itemCatalogFeatures.handleItemTemplateSourceSearchInput;
  const handleItemTemplateSourceSearchKeydown = itemCatalogFeatures.handleItemTemplateSourceSearchKeydown;
  const handleItemTemplateSourcePickerClick = itemCatalogFeatures.handleItemTemplateSourcePickerClick;
  const handleItemTemplateSourceOutsidePointer = itemCatalogFeatures.handleItemTemplateSourceOutsidePointer;
  const handleItemTemplateSourceSearchFocusOut = itemCatalogFeatures.handleItemTemplateSourceSearchFocusOut;
  const openItemTemplateHistoryModal = itemCatalogFeatures.openItemTemplateHistoryModal;
  const closeItemTemplateHistoryModal = itemCatalogFeatures.closeItemTemplateHistoryModal;
  const cleanupItemCatalogRuntime = itemCatalogFeatures.cleanupItemCatalogRuntime;

  const ensureAllTimeBounds = operationsFeatures.ensureAllTimeBounds;
  const invalidateAllTimeAnchor = operationsFeatures.invalidateAllTimeAnchor;
  const loadOperations = operationsFeatures.loadOperations;
  const loadMoreOperations = operationsFeatures.loadMoreOperations;
  const createOperation = operationsFeatures.createOperation;
  const updateOperation = operationsFeatures.updateOperation;
  const deleteOperationFlow = operationsFeatures.deleteOperationFlow;
  const applyFilters = operationsFeatures.applyFilters;
  const applyRealtimeSearch = operationsFeatures.applyRealtimeSearch;
  const setOperationsSortPreset = operationsFeatures.setOperationsSortPreset;
  const refreshAll = operationsFeatures.refreshAll;
  const refreshOperationsView = operationsFeatures.refreshOperationsView;
  const getCurrentOperationItems = operationsFeatures.getCurrentOperationItems;
  const clearOperationsCategoryFilter = operationsFeatures.clearOperationsCategoryFilter;
  const resetOperationsFilters = operationsFeatures.resetOperationsFilters;
  const setOperationsMode = operationsFeatures.setOperationsMode;
  const setOperationsSourceFilter = operationsFeatures.setOperationsSourceFilter;
  const setOperationsQuickView = operationsFeatures.setOperationsQuickView;
  const selectVisibleOperations = operationsFeatures.selectVisibleOperations;
  const clearVisibleOperationsSelection = operationsFeatures.clearVisibleOperationsSelection;
  const setOperationsKindFilter = operationsFeatures.setOperationsKindFilter;
  const openMoneyFlowSource = operationsFeatures.openMoneyFlowSource;
  const openOperationReceiptModal = operationsFeatures.openOperationReceiptModal;
  const closeOperationReceiptModal = operationsFeatures.closeOperationReceiptModal;
  const cleanupOperationsRuntime = operationsFeatures.cleanupOperationsRuntime;

  function logoutWithCatalogCleanup(showMessage = true) {
    cleanupOperationsRuntime();
    cleanupItemCatalogRuntime();
    logout(showMessage);
  }

  const previousActions = window.App.actions;
  // Public actions facade is intentionally narrow now:
  // navigation/back-stack helpers stay here as cross-section orchestration,
  // category/debt/batch glue still stays here while it spans multiple modules,
  // everything else should prefer direct runtime-module access.
  const publicActionFacade = {
    updateCreatePreview,
    updateDebtDueHint,
    updateEditPreview,
    renderCreateCategoryPicker,
    handleCreateCategorySearchFocus,
    handleCreateCategorySearchInput,
    handleCreateCategorySearchKeydown,
    handleDebtCounterpartySearchFocus,
    handleDebtCounterpartySearchInput,
    handleDebtCounterpartySearchKeydown,
    handleEditCategorySearchFocus,
    handleEditCategorySearchInput,
    handleEditCategorySearchKeydown,
    handleCreateCategoryOutsidePointer,
    handleDebtCounterpartyOutsidePointer,
    handleEditCategoryOutsidePointer,
    handleReceiptOutsidePointer,
    handleReceiptItemsListInput,
    handleReceiptItemsListFocusIn,
    handleReceiptItemsListKeydown,
    handleReceiptItemsListClick,
    handlePullReceiptTotal,
    handleCreateCategoryPickerClick,
    handleDebtCounterpartyPickerClick,
    handleEditCategoryPickerClick,
    renderReceiptSummary,
    onCategoryCreated,
    handleCreatePreviewClick,
    setOperationKind,
    setCreateOperationMode,
    setEditOperationMode,
    setDebtDirection,
    setCurrencySide,
    setCreateEntryMode,
    openCreateModal,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    openOperationReceiptModal,
    closeOperationReceiptModal,
    openPeriodCustomModal,
    closePeriodCustomModal,
    syncOperationCurrencyFields,
    syncSuggestedOperationFxRate,
    markCreateOperationFxRateManual,
    markEditOperationFxRateManual,
    resetCreateOperationFxRateAutofill,
    resetEditOperationFxRateAutofill,
    renderReceiptItems,
    syncCurrencyTradeFieldUi,
    syncSuggestedCurrencyRate,
    markCurrencyRateManual,
    markCurrencyQuantitySource,
    markCurrencyQuoteSource,
    resetCurrencyRateAutofill,
    applyDebtCurrencyUi,
    savePreferences,
    savePreferencesDebounced,
    saveSettings,
    previewInterfaceSettingsUi,
    syncSettingsPickerButtons,
    openSettingsPickerModal,
    closeSettingsPickerModal,
    applySettingsPickerValue,
    deleteMe,
    applySectionUi: previousActions.applySectionUi,
    switchSection: previousActions.switchSection,
    renderTodayLabel: previousActions.renderTodayLabel,
    loadDashboard,
    loadDashboardOperations,
    loadAnalyticsTrend,
    loadAnalyticsHighlights,
    loadDashboardAnalyticsPreview,
    loadAnalyticsSection,
    shiftAnalyticsMonth,
    resetAnalyticsMonth,
    applyAnalyticsTabUi,
    setAnalyticsTab,
    setAnalyticsCalendarView,
    setAnalyticsGridMonthAnchor,
    setAnalyticsGridYearAnchor,
    openAnalyticsMonth,
    openOperationsForAnalyticsDate,
    openOperationsForAnalyticsRange,
    openOperationsForAnalyticsCategory,
    toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems,
    loadAdminUsers,
    setAdminUserStatusFilter,
    approveAdminUser,
    rejectAdminUser,
    deleteAdminUser,
    loadDebtsCards,
    renderDebtCards,
    loadPlans,
    openDebtRepaymentModal,
    closeDebtRepaymentModal,
    submitDebtRepayment,
    forgiveDebtFromRepaymentFlow,
    updateRepaymentDeltaHint,
    openDebtForgivenessModal,
    closeDebtForgivenessModal,
    submitDebtForgiveness,
    openDebtHistoryModal,
    closeDebtHistoryModal,
    setDebtStatusFilter,
    setDebtSortPreset,
    applyDebtSearch,
    loadMoreDebtCards,
    loadMoreDebtHistoryEvents,
    openEditDebtModal,
    deleteDebtFlow,
    renderPlansSection,
    renderDashboardPlans,
    setDashboardPlansPeriod,
    setPlansTab,
    setPlansKindFilter,
    setPlansStatusFilter,
    setPlansHistoryEventFilter,
    applyPlansSearch,
    openCreatePlan,
    submitPlanForm,
    handlePlanActionClick,
    syncPlanRecurrenceUi,
    togglePlanWeekday,
    ensureAllTimeBounds,
    invalidateAllTimeAnchor,
    loadOperations,
    loadMoreOperations,
    loadItemCatalog,
    refreshItemCatalogView,
    setItemCatalogSortPreset,
    collapseAllItemCatalogGroups,
    expandAllItemCatalogGroups,
    handleItemCatalogBodyClick,
    openItemTemplateModal,
    closeItemTemplateModal,
    submitItemTemplateForm,
    deleteItemTemplateFlow,
    deleteAllItemTemplatesFlow,
    openSourceGroupModal,
    openEditSourceGroupModal,
    closeSourceGroupModal,
    submitSourceGroupForm,
    deleteItemSourceFlow,
    updateItemTemplatePreview,
    handleItemTemplateSourceSearchFocus,
    handleItemTemplateSourceSearchInput,
    handleItemTemplateSourceSearchKeydown,
    handleItemTemplateSourcePickerClick,
    handleItemTemplateSourceOutsidePointer,
    handleItemTemplateSourceSearchFocusOut,
    openItemTemplateHistoryModal,
    closeItemTemplateHistoryModal,
    refreshOperationsView,
    getCurrentOperationItems,
    clearOperationsCategoryFilter,
    resetOperationsFilters,
    setOperationsMode,
    setOperationsSourceFilter,
    setOperationsQuickView,
    selectVisibleOperations,
    clearVisibleOperationsSelection,
    setOperationsKindFilter,
    openMoneyFlowSource,
    createOperation,
    updateOperation,
    deleteOperationFlow,
    applyFilters,
    setOperationsSortPreset,
    applyRealtimeSearch,
    refreshAll,
    logout: logoutWithCatalogCleanup,
    telegramLogin,
    loadTelegramLoginConfig,
    tryAutoTelegramLogin,
    bootstrapApp,
  };

  window.App.actions = {
    ...previousActions,
    ...publicActionFacade,
  };

  const publicActionFacadeContract = Object.freeze({
    navigation: Object.freeze([
      "applySectionUi",
      "switchSection",
      "renderTodayLabel",
      "pushSectionBackContext",
      "navigateSectionBack",
      "updateSectionBackUi",
    ]),
    debt_batch_orchestration: Object.freeze([
      "renderDebtCards",
      "openDebtRepaymentModal",
      "closeDebtRepaymentModal",
      "submitDebtRepayment",
      "forgiveDebtFromRepaymentFlow",
      "updateRepaymentDeltaHint",
      "openDebtForgivenessModal",
      "closeDebtForgivenessModal",
      "submitDebtForgiveness",
      "openDebtHistoryModal",
      "closeDebtHistoryModal",
      "openEditDebtModal",
      "deleteDebtFlow",
      "openBatchCreateModal",
      "openBatchCategoryModal",
      "openBatchItemTemplateModal",
    ]),
  });

  window.App.publicActionFacadeContract = publicActionFacadeContract;
})();
