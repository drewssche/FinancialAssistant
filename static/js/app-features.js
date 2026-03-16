(() => {
  const categoryActions = window.App.actions;
  const dashboardFeatures = window.App.featureDashboard;
  const analyticsFeatures = window.App.featureAnalytics;
  const adminFeatures = window.App.featureAdmin;
  const debtFeatures = window.App.featureDebts;
  const sessionFeatures = window.App.featureSession;
  const itemCatalogFeatures = window.App.featureItemCatalog;
  const operationsFeatures = window.App.featureOperations;
  const operationModal = window.App.operationModal;

  const getCreateFormPreviewItem = operationModal.getCreateFormPreviewItem;
  const updateCreatePreview = operationModal.updateCreatePreview;
  const updateDebtDueHint = operationModal.updateDebtDueHint;
  const updateEditPreview = operationModal.updateEditPreview;
  const renderCreateCategoryPicker = operationModal.renderCreateCategoryPicker;
  const renderEditCategoryPicker = operationModal.renderEditCategoryPicker;
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
  const setReceiptEnabled = operationModal.setReceiptEnabled;
  const renderReceiptSummary = operationModal.renderReceiptSummary;
  const onCategoryCreated = operationModal.onCategoryCreated;
  const selectCreateCategory = operationModal.selectCreateCategory;
  const handleCreatePreviewClick = operationModal.handleCreatePreviewClick;
  const setOperationKind = operationModal.setOperationKind;
  const setCreateOperationMode = operationModal.setCreateOperationMode;
  const setEditOperationMode = operationModal.setEditOperationMode;
  const setDebtDirection = operationModal.setDebtDirection;
  const setCreateEntryMode = operationModal.setCreateEntryMode;
  const openCreateModal = operationModal.openCreateModal;
  const openCreateModalForDebtEdit = operationModal.openCreateModalForDebtEdit;
  const closeCreateModal = operationModal.closeCreateModal;
  const openEditModal = operationModal.openEditModal;
  const closeEditModal = operationModal.closeEditModal;
  const openPeriodCustomModal = operationModal.openPeriodCustomModal;
  const closePeriodCustomModal = operationModal.closePeriodCustomModal;

  const loadMe = sessionFeatures.loadMe;
  const loadPreferences = sessionFeatures.loadPreferences;
  const savePreferences = sessionFeatures.savePreferences;
  const savePreferencesDebounced = sessionFeatures.savePreferencesDebounced;
  const cancelDebouncedPreferencesSave = sessionFeatures.cancelDebouncedPreferencesSave;
  const saveSettings = sessionFeatures.saveSettings;
  const applyInterfaceSettingsUi = sessionFeatures.applyInterfaceSettingsUi;
  const previewInterfaceSettingsUi = sessionFeatures.previewInterfaceSettingsUi;
  const deleteMe = sessionFeatures.deleteMe;
  const logout = sessionFeatures.logout;
  const bootstrapApp = sessionFeatures.bootstrapApp;
  const telegramLogin = sessionFeatures.telegramLogin;
  const telegramBrowserLogin = sessionFeatures.telegramBrowserLogin;
  const loadTelegramLoginConfig = sessionFeatures.loadTelegramLoginConfig;
  const tryAutoTelegramLogin = sessionFeatures.tryAutoTelegramLogin;

  const loadDashboard = dashboardFeatures.loadDashboard;
  const loadDashboardOperations = dashboardFeatures.loadDashboardOperations;
  const loadAnalyticsCalendar = analyticsFeatures.loadAnalyticsCalendar;
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
  const openDebtRepaymentModal = debtFeatures.openDebtRepaymentModal;
  const closeDebtRepaymentModal = debtFeatures.closeDebtRepaymentModal;
  const submitDebtRepayment = debtFeatures.submitDebtRepayment;
  const updateRepaymentDeltaHint = debtFeatures.updateRepaymentDeltaHint;
  const openDebtHistoryModal = debtFeatures.openDebtHistoryModal;
  const closeDebtHistoryModal = debtFeatures.closeDebtHistoryModal;
  const setDebtStatusFilter = debtFeatures.setDebtStatusFilter;
  const setDebtSortPreset = debtFeatures.setDebtSortPreset;
  const applyDebtSearch = debtFeatures.applyDebtSearch;
  const loadMoreDebtCards = debtFeatures.loadMoreDebtCards;
  const loadMoreDebtHistoryEvents = debtFeatures.loadMoreDebtHistoryEvents;
  const openEditDebtModal = debtFeatures.openEditDebtModal;
  const deleteDebtFlow = debtFeatures.deleteDebtFlow;

  const loadItemCatalog = itemCatalogFeatures.loadItemCatalog;
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
  const updateSourceGroupPreview = itemCatalogFeatures.updateSourceGroupPreview;
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
  const setOperationsQuickView = operationsFeatures.setOperationsQuickView;
  const selectVisibleOperations = operationsFeatures.selectVisibleOperations;
  const clearVisibleOperationsSelection = operationsFeatures.clearVisibleOperationsSelection;
  const setOperationsKindFilter = operationsFeatures.setOperationsKindFilter;
  const loadOperationsSummary = operationsFeatures.loadOperationsSummary;
  const openOperationReceiptModal = operationsFeatures.openOperationReceiptModal;
  const closeOperationReceiptModal = operationsFeatures.closeOperationReceiptModal;
  const cleanupOperationsRuntime = operationsFeatures.cleanupOperationsRuntime;

  function logoutWithCatalogCleanup(showMessage = true) {
    cleanupOperationsRuntime();
    cleanupItemCatalogRuntime();
    logout(showMessage);
  }

  const previousActions = window.App.actions;

  window.App.actions = {
    ...previousActions,
    getCreateFormPreviewItem,
    updateCreatePreview,
    updateDebtDueHint,
    updateEditPreview,
    renderCreateCategoryPicker,
    renderEditCategoryPicker,
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
    setReceiptEnabled,
    renderReceiptSummary,
    onCategoryCreated,
    selectCreateCategory,
    handleCreatePreviewClick,
    setOperationKind,
    setCreateOperationMode,
    setEditOperationMode,
    setDebtDirection,
    setCreateEntryMode,
    openCreateModal,
    openCreateModalForDebtEdit,
    closeCreateModal,
    openEditModal,
    closeEditModal,
    openOperationReceiptModal,
    closeOperationReceiptModal,
    openCreateCategoryModal: categoryActions.openCreateCategoryModal,
    closeCreateCategoryModal: categoryActions.closeCreateCategoryModal,
    openPeriodCustomModal,
    closePeriodCustomModal,
    loadMe,
    loadPreferences,
    savePreferences,
    savePreferencesDebounced,
    cancelDebouncedPreferencesSave,
    saveSettings,
    applyInterfaceSettingsUi,
    previewInterfaceSettingsUi,
    deleteMe,
    applySectionUi: previousActions.applySectionUi,
    switchSection: previousActions.switchSection,
    renderTodayLabel: previousActions.renderTodayLabel,
    loadDashboard,
    loadDashboardOperations,
    loadAnalyticsCalendar,
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
    openDebtRepaymentModal,
    closeDebtRepaymentModal,
    submitDebtRepayment,
    updateRepaymentDeltaHint,
    openDebtHistoryModal,
    closeDebtHistoryModal,
    setDebtStatusFilter,
    setDebtSortPreset,
    applyDebtSearch,
    loadMoreDebtCards,
    loadMoreDebtHistoryEvents,
    openEditDebtModal,
    deleteDebtFlow,
    ensureAllTimeBounds,
    invalidateAllTimeAnchor,
    loadOperations,
    loadMoreOperations,
    loadItemCatalog,
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
    updateSourceGroupPreview,
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
    setOperationsQuickView,
    selectVisibleOperations,
    clearVisibleOperationsSelection,
    setOperationsKindFilter,
    loadOperationsSummary,
    fillGroupSelect: categoryActions.fillGroupSelect,
    setCategoryKind: categoryActions.setCategoryKind,
    renderCreateGroupPicker: categoryActions.renderCreateGroupPicker,
    renderEditGroupPicker: categoryActions.renderEditGroupPicker,
    handleCreateGroupSearchFocus: categoryActions.handleCreateGroupSearchFocus,
    handleCreateGroupSearchInput: categoryActions.handleCreateGroupSearchInput,
    handleCreateGroupSearchBlur: categoryActions.handleCreateGroupSearchBlur,
    handleCreateGroupSearchKeydown: categoryActions.handleCreateGroupSearchKeydown,
    handleEditGroupSearchFocus: categoryActions.handleEditGroupSearchFocus,
    handleEditGroupSearchInput: categoryActions.handleEditGroupSearchInput,
    handleEditGroupSearchBlur: categoryActions.handleEditGroupSearchBlur,
    handleEditGroupSearchKeydown: categoryActions.handleEditGroupSearchKeydown,
    handleCreateGroupPickerClick: categoryActions.handleCreateGroupPickerClick,
    handleEditGroupPickerClick: categoryActions.handleEditGroupPickerClick,
    handleCreateGroupOutsidePointer: categoryActions.handleCreateGroupOutsidePointer,
    selectCreateGroup: categoryActions.selectCreateGroup,
    renderCategories: categoryActions.renderCategories,
    updateCategoriesBulkUi: categoryActions.updateCategoriesBulkUi,
    handleCategoriesGroupToggleClick: categoryActions.handleCategoriesGroupToggleClick,
    collapseAllCategoryGroups: categoryActions.collapseAllCategoryGroups,
    expandAllCategoryGroups: categoryActions.expandAllCategoryGroups,
    loadCategories: categoryActions.loadCategories,
    createCategory: categoryActions.createCategory,
    createGroup: categoryActions.createGroup,
    openEditGroupModal: categoryActions.openEditGroupModal,
    closeEditGroupModal: categoryActions.closeEditGroupModal,
    updateGroup: categoryActions.updateGroup,
    deleteGroupFlow: categoryActions.deleteGroupFlow,
    openEditCategoryModal: categoryActions.openEditCategoryModal,
    closeEditCategoryModal: categoryActions.closeEditCategoryModal,
    updateCategory: categoryActions.updateCategory,
    groupCategoryIds: categoryActions.groupCategoryIds,
    bulkDeleteCategories: categoryActions.bulkDeleteCategories,
    bulkDeleteGroups: categoryActions.bulkDeleteGroups,
    deleteCategoryFlow: categoryActions.deleteCategoryFlow,
    createOperation,
    updateOperation,
    deleteOperationFlow,
    applyFilters,
    setOperationsSortPreset,
    applyRealtimeSearch,
    refreshAll,
    logout: logoutWithCatalogCleanup,
    telegramLogin,
    telegramBrowserLogin,
    loadTelegramLoginConfig,
    tryAutoTelegramLogin,
    bootstrapApp,
  };
})();
