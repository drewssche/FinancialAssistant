(() => {
  const { state, el, core } = window.App;
  const operationModal = window.App.getRuntimeModule?.("operation-modal");
  let preferencesSaveDebounceId = null;
  const DEFAULT_UI_PREFS = {
    timezone: "auto",
    browser_timezone: "",
    currency: "BYN",
    currency_position: "suffix",
    show_dashboard_analytics: true,
    show_dashboard_operations: true,
    show_dashboard_debts: true,
    dashboard_operations_limit: 8,
    scale_percent: 100,
  };
  const DEFAULT_CURRENCY_PREFS = {
    tracked_currencies: ["USD", "EUR"],
    show_dashboard_kpi: true,
    telegram_digest_enabled: false,
  };
  let activeSettingsPickerKey = "";

  function getAnalyticsFeature() {
    return window.App.getRuntimeModule?.("analytics") || {};
  }

  function getCategoryActions() {
    return window.App.actions || {};
  }

  const SETTINGS_PICKER_CONFIGS = {
    timezone: {
      title: "Таймзона",
      select: () => el.timezoneSelect,
      button: () => el.timezonePickerBtn,
    },
    currency: {
      title: "Валюта",
      select: () => el.currencySelect,
      button: () => el.currencyPickerBtn,
    },
    currency_position: {
      title: "Позиция символа",
      select: () => el.currencyPositionSelect,
      button: () => el.currencyPositionPickerBtn,
    },
    dashboard_operations_limit: {
      title: "Строк планов на дашборде",
      select: () => el.dashboardOperationsLimitSelect,
      button: () => el.dashboardOperationsLimitPickerBtn,
    },
  };

  function normalizeStructureHidden(raw) {
    const normalized = {
      category: { expense: [], income: [], all: [] },
      group: { expense: [], income: [], all: [] },
    };
    for (const level of ["category", "group"]) {
      const sourceLevel = raw && typeof raw === "object" ? raw[level] : null;
      for (const kind of ["expense", "income", "all"]) {
        const source = sourceLevel && Array.isArray(sourceLevel[kind]) ? sourceLevel[kind] : [];
        normalized[level][kind] = source.map((item) => String(item)).filter(Boolean);
      }
    }
    return normalized;
  }

  function getMergedUiPrefs() {
    return {
      ...DEFAULT_UI_PREFS,
      ...(state.preferences?.data?.ui || {}),
    };
  }

  function getMergedCurrencyPrefs() {
    return {
      ...DEFAULT_CURRENCY_PREFS,
      ...(state.preferences?.data?.currency || {}),
    };
  }

  function getSelectButtonLabel(selectNode) {
    if (!selectNode) {
      return "";
    }
    const option = selectNode.options?.[selectNode.selectedIndex] || null;
    return option ? String(option.textContent || option.label || option.value || "").trim() : "";
  }

  function syncSettingsPickerButtons() {
    for (const config of Object.values(SETTINGS_PICKER_CONFIGS)) {
      const selectNode = config.select();
      const buttonNode = config.button();
      if (!selectNode || !buttonNode) {
        continue;
      }
      buttonNode.textContent = getSelectButtonLabel(selectNode);
      buttonNode.classList.toggle("hidden", !core.isMobileViewport());
      buttonNode.setAttribute("aria-label", `${config.title}: ${buttonNode.textContent}`);
    }
  }

  function closeSettingsPickerModal() {
    activeSettingsPickerKey = "";
    if (el.settingsPickerOptions) {
      el.settingsPickerOptions.innerHTML = "";
    }
    if (el.settingsPickerModal) {
      el.settingsPickerModal.classList.add("hidden");
    }
  }

  function openSettingsPickerModal(key) {
    if (!core.isMobileViewport()) {
      return;
    }
    const config = SETTINGS_PICKER_CONFIGS[key];
    const selectNode = config?.select?.();
    if (!config || !selectNode || !el.settingsPickerModal || !el.settingsPickerOptions) {
      return;
    }
    activeSettingsPickerKey = key;
    if (el.settingsPickerTitle) {
      el.settingsPickerTitle.textContent = config.title;
    }
    el.settingsPickerOptions.innerHTML = Array.from(selectNode.options || []).map((option) => {
      const value = String(option.value || "");
      const label = String(option.textContent || option.label || value).trim();
      const active = value === String(selectNode.value || "");
      return `
        <button
          class="btn btn-secondary settings-picker-option ${active ? "active" : ""}"
          type="button"
          data-settings-picker-value="${core.escapeHtml ? core.escapeHtml(value) : value}"
        >${core.escapeHtml ? core.escapeHtml(label) : label}</button>
      `;
    }).join("");
    el.settingsPickerModal.classList.remove("hidden");
  }

  function applySettingsPickerValue(value) {
    const config = SETTINGS_PICKER_CONFIGS[activeSettingsPickerKey];
    const selectNode = config?.select?.();
    if (!config || !selectNode) {
      closeSettingsPickerModal();
      return;
    }
    const nextValue = String(value || "");
    const hasOption = Array.from(selectNode.options || []).some((option) => String(option.value || "") === nextValue);
    if (!hasOption) {
      closeSettingsPickerModal();
      return;
    }
    selectNode.value = nextValue;
    selectNode.dispatchEvent(new Event("change", { bubbles: true }));
    syncSettingsPickerButtons();
    closeSettingsPickerModal();
  }

  function applyInterfaceSettingsUi() {
    const ui = getMergedUiPrefs();
    if (el.timezoneSelect) {
      const hasOption = Array.from(el.timezoneSelect.options).some((opt) => opt.value === ui.timezone);
      el.timezoneSelect.value = hasOption ? ui.timezone : "auto";
    }
    if (el.currencySelect) {
      const hasCurrency = Array.from(el.currencySelect.options).some((opt) => opt.value === ui.currency);
      el.currencySelect.value = hasCurrency ? ui.currency : "BYN";
    }
    if (el.currencyPositionSelect) {
      el.currencyPositionSelect.value = ui.currency_position === "prefix" ? "prefix" : "suffix";
    }
    if (el.showDashboardDebtsToggle) {
      el.showDashboardDebtsToggle.checked = ui.show_dashboard_debts !== false;
    }
    if (el.showDashboardCurrencyToggle) {
      el.showDashboardCurrencyToggle.checked = getMergedCurrencyPrefs().show_dashboard_kpi !== false;
    }
    if (el.trackedCurrencyInputs?.length) {
      const tracked = new Set((getMergedCurrencyPrefs().tracked_currencies || []).map((item) => String(item || "").toUpperCase()));
      Array.from(el.trackedCurrencyInputs).forEach((input) => {
        input.checked = tracked.has(String(input.value || "").toUpperCase());
      });
    }
    if (el.currencyDigestToggle) {
      el.currencyDigestToggle.checked = getMergedCurrencyPrefs().telegram_digest_enabled === true;
    }
    if (el.showDashboardAnalyticsToggle) {
      el.showDashboardAnalyticsToggle.checked = ui.show_dashboard_analytics !== false;
    }
    if (el.showDashboardOperationsToggle) {
      el.showDashboardOperationsToggle.checked = ui.show_dashboard_operations !== false;
    }
    if (el.plansRemindersToggle) {
      el.plansRemindersToggle.checked = (state.preferences?.data?.plans?.reminders_enabled) !== false;
    }
    if (el.plansReminderTimeInput) {
      el.plansReminderTimeInput.value = String(state.preferences?.data?.plans?.reminder_time || "09:00");
      el.plansReminderTimeInput.disabled = el.plansRemindersToggle ? !el.plansRemindersToggle.checked : false;
    }
    if (el.dashboardOperationsLimitSelect) {
      const value = [5, 8, 12].includes(Number(ui.dashboard_operations_limit)) ? String(ui.dashboard_operations_limit) : "8";
      el.dashboardOperationsLimitSelect.value = value;
    }
    core.applyUiScale(ui.scale_percent || 100);
    core.applyMoneyInputs(core.resolveCurrencyConfig(ui.currency, ui.currency_position));
    if (el.dashboardAnalyticsPanel) {
      el.dashboardAnalyticsPanel.classList.toggle("hidden", ui.show_dashboard_analytics === false);
    }
    if (el.dashboardStructurePanel) {
      el.dashboardStructurePanel.classList.toggle("hidden", ui.show_dashboard_analytics === false);
    }
    if (el.dashboardPlansPanel) {
      el.dashboardPlansPanel.classList.toggle("hidden", ui.show_dashboard_operations === false);
    }
    if (el.dashboardPlansPeriodTabs) {
      core.syncSegmentedActive(el.dashboardPlansPeriodTabs, "dashboard-plans-period", state.dashboardPlansPeriod || "month");
    }
    if (el.dashboardDebtsPanel) {
      el.dashboardDebtsPanel.classList.toggle("hidden", ui.show_dashboard_debts === false);
    }
    syncSettingsPickerButtons();
  }

  function previewInterfaceSettingsUi() {
    const currency = el.currencySelect ? el.currencySelect.value : getMergedUiPrefs().currency;
    const position = el.currencyPositionSelect ? el.currencyPositionSelect.value : getMergedUiPrefs().currency_position;
    const scale = el.uiScaleRange ? Number(el.uiScaleRange.value || 100) : getMergedUiPrefs().scale_percent;
    core.applyUiScale(scale);
    core.applyMoneyInputs(core.resolveCurrencyConfig(currency, position));
    if (el.currencyPreview) {
      el.currencyPreview.textContent = `Пример: ${core.formatMoney(1234.56, { currency, position })}`;
    }
    if (el.dashboardDebtsPanel && el.showDashboardDebtsToggle) {
      el.dashboardDebtsPanel.classList.toggle("hidden", !el.showDashboardDebtsToggle.checked);
    }
    if (el.dashboardCurrencyPanel && el.showDashboardCurrencyToggle) {
      el.dashboardCurrencyPanel.classList.toggle("hidden", !el.showDashboardCurrencyToggle.checked);
    }
    if (el.dashboardAnalyticsPanel && el.showDashboardAnalyticsToggle) {
      el.dashboardAnalyticsPanel.classList.toggle("hidden", !el.showDashboardAnalyticsToggle.checked);
    }
    if (el.dashboardStructurePanel && el.showDashboardAnalyticsToggle) {
      el.dashboardStructurePanel.classList.toggle("hidden", !el.showDashboardAnalyticsToggle.checked);
    }
    if (el.dashboardPlansPanel && el.showDashboardOperationsToggle) {
      el.dashboardPlansPanel.classList.toggle("hidden", !el.showDashboardOperationsToggle.checked);
    }
    if (el.plansReminderTimeInput && el.plansRemindersToggle) {
      el.plansReminderTimeInput.disabled = !el.plansRemindersToggle.checked;
    }
    syncSettingsPickerButtons();
  }

  async function loadPreferences() {
    const prefs = await core.requestJson("/api/v1/preferences", { headers: core.authHeaders() });
    state.preferences = prefs;
    core.invalidateUiRequestCache();

    const savedPeriod = prefs.data?.dashboard?.period || "day";
    state.period = ["day", "week", "month", "year", "all_time", "custom"].includes(savedPeriod) ? savedPeriod : "day";
    state.customDateFrom = prefs.data?.dashboard?.custom_date_from || "";
    state.customDateTo = prefs.data?.dashboard?.custom_date_to || "";
    if (state.period === "custom" && (!state.customDateFrom || !state.customDateTo)) {
      state.period = "day";
    }
    state.filterKind = prefs.data?.operations?.filters?.kind || "";
    state.operationsQuickView = prefs.data?.operations?.filters?.quick_view || "all";
    state.operationsCategoryFilterId = prefs.data?.operations?.filters?.category_id ?? null;
    state.operationsCategoryFilterName = prefs.data?.operations?.filters?.category_name || "";
    state.operationSortPreset = prefs.data?.operations?.sort_preset || localStorage.getItem("operations_sort_preset") || "date";
    localStorage.setItem("operations_sort_preset", state.operationSortPreset);
    state.debtSortPreset = prefs.data?.debts?.sort_preset || "priority";
    state.itemCatalogSortPreset = prefs.data?.ui?.item_catalog_sort_preset || "usage";
    state.analyticsMonthAnchor = prefs.data?.analytics?.month_anchor || "";
    state.analyticsTab = prefs.data?.analytics?.tab || "calendar";
    if (state.analyticsTab === "positions" || state.analyticsTab === "operations" || state.analyticsTab === "overview") {
      state.analyticsTab = "calendar";
    }
    if (!["structure", "calendar", "trends", "currency"].includes(state.analyticsTab)) {
      state.analyticsTab = "calendar";
    }
    state.analyticsCurrencyFilter = prefs.data?.analytics?.currency_filter || "all";
    state.analyticsCalendarView = prefs.data?.analytics?.calendar_view || "month";
    state.analyticsGlobalPeriod = prefs.data?.analytics?.global_period || prefs.data?.analytics?.summary_period || prefs.data?.analytics?.period || "month";
    state.analyticsGlobalDateFrom = prefs.data?.analytics?.global_date_from || prefs.data?.analytics?.summary_date_from || "";
    state.analyticsGlobalDateTo = prefs.data?.analytics?.global_date_to || prefs.data?.analytics?.summary_date_to || "";
    state.analyticsCategoryKind = prefs.data?.analytics?.category_kind || "expense";
    state.analyticsBreakdownLevel = ["category", "group"].includes(prefs.data?.analytics?.breakdown_level)
      ? prefs.data.analytics.breakdown_level
      : "category";
    state.analyticsStructureHidden = normalizeStructureHidden(prefs.data?.analytics?.structure_hidden);
    state.analyticsGranularity = prefs.data?.analytics?.granularity || "day";
    if ((state.analyticsGlobalPeriod === "year" || state.analyticsGlobalPeriod === "all_time") && state.analyticsGranularity === "day") {
      state.analyticsGranularity = "week";
    }
    state.dashboardAnalyticsPeriod = prefs.data?.dashboard?.analytics_period || "month";
    state.dashboardAnalyticsDateFrom = prefs.data?.dashboard?.analytics_date_from || "";
    state.dashboardAnalyticsDateTo = prefs.data?.dashboard?.analytics_date_to || "";
    if (state.dashboardAnalyticsPeriod === "custom" && (!state.dashboardAnalyticsDateFrom || !state.dashboardAnalyticsDateTo)) {
      state.dashboardAnalyticsPeriod = "month";
    }
    state.dashboardPlansPeriod = ["week", "month", "all_time"].includes(prefs.data?.plans?.dashboard_period)
      ? prefs.data.plans.dashboard_period
      : "month";
    state.dashboardBreakdownLevel = ["category", "group"].includes(prefs.data?.dashboard?.breakdown_level)
      ? prefs.data.dashboard.breakdown_level
      : "category";
    state.dashboardCategoryKind = ["expense", "income", "all"].includes(prefs.data?.dashboard?.category_kind)
      ? prefs.data.dashboard.category_kind
      : "expense";
    state.adminUserStatusFilter = prefs.data?.admin?.user_status_filter || "pending";
    state.plansStatusFilter = prefs.data?.plans?.status_filter || "all";
    state.plansHistoryEventFilter = prefs.data?.plans?.history_event_filter || "all";
    el.filterQ.value = prefs.data?.operations?.filters?.q || "";
    state.activeSection = prefs.data?.ui?.active_section || "dashboard";

    core.syncAllPeriodTabs(state.period);
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    core.syncSegmentedActive(el.operationsSortTabs, "op-sort", state.operationSortPreset);
    core.syncSegmentedActive(el.debtSortTabs, "debt-sort", state.debtSortPreset);
    core.syncSegmentedActive(el.itemCatalogSortTabs, "item-sort", state.itemCatalogSortPreset);
    core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", state.analyticsTab);
    core.syncSegmentedActive(el.analyticsCalendarViewTabs, "analytics-calendar-view", state.analyticsCalendarView);
    core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", state.analyticsGlobalPeriod);
    core.syncSegmentedActive(el.analyticsBreakdownLevelTabs, "analytics-breakdown-level", state.analyticsBreakdownLevel);
    core.syncSegmentedActive(el.analyticsCategoryKindTabs, "analytics-category-kind", state.analyticsCategoryKind);
    core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
    core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", state.dashboardAnalyticsPeriod);
    core.syncSegmentedActive(el.dashboardPlansPeriodTabs, "dashboard-plans-period", state.dashboardPlansPeriod);
    core.syncSegmentedActive(el.dashboardBreakdownLevelTabs, "dashboard-breakdown-level", state.dashboardBreakdownLevel);
    core.syncSegmentedActive(el.dashboardCategoryKindTabs, "dashboard-category-kind", state.dashboardCategoryKind);
    core.syncSegmentedActive(el.adminUserStatusTabs, "admin-user-status", state.adminUserStatusFilter);
    core.syncSegmentedActive(el.plansStatusTabs, "plan-status", state.plansStatusFilter);
    core.syncSegmentedActive(el.plansHistoryEventTabs, "plan-history-event", state.plansHistoryEventFilter);
    const analyticsFeature = getAnalyticsFeature();
    if (analyticsFeature.applyAnalyticsTabUi) {
      analyticsFeature.applyAnalyticsTabUi();
    }
    applyInterfaceSettingsUi();
    operationModal.applySettingsUi();
    if (getCategoryActions().renderTodayLabel) {
      getCategoryActions().renderTodayLabel();
    }
  }

  function buildPreferencesPayload() {
    const analyticsPrefs = { ...(state.preferences?.data?.analytics || {}) };
    delete analyticsPrefs.top_operations_limit;
    delete analyticsPrefs.top_positions_limit;
    const trackedCurrencies = el.trackedCurrencyInputs?.length
      ? Array.from(el.trackedCurrencyInputs)
        .filter((input) => input.checked)
        .map((input) => String(input.value || "").toUpperCase())
      : (getMergedCurrencyPrefs().tracked_currencies || []);
    return {
      preferences_version: state.preferences?.preferences_version || 1,
      data: {
        ...state.preferences?.data,
        dashboard: {
          ...(state.preferences?.data?.dashboard || {}),
          period: state.period,
          custom_date_from: state.customDateFrom || "",
          custom_date_to: state.customDateTo || "",
          analytics_period: state.dashboardAnalyticsPeriod || "month",
          analytics_date_from: state.dashboardAnalyticsDateFrom || "",
          analytics_date_to: state.dashboardAnalyticsDateTo || "",
          breakdown_level: state.dashboardBreakdownLevel || "category",
          category_kind: state.dashboardCategoryKind || "expense",
        },
        operations: {
          ...(state.preferences?.data?.operations || {}),
          sort_preset: state.operationSortPreset || "date",
          filters: {
            kind: state.filterKind,
            quick_view: state.operationsQuickView || "all",
            category_id: state.operationsCategoryFilterId,
            category_name: state.operationsCategoryFilterName || "",
            q: el.filterQ.value.trim(),
          },
        },
        debts: {
          ...(state.preferences?.data?.debts || {}),
          sort_preset: state.debtSortPreset || "priority",
        },
        analytics: {
          ...analyticsPrefs,
          month_anchor: state.analyticsMonthAnchor || "",
          tab: state.analyticsTab || "calendar",
          calendar_view: state.analyticsCalendarView || "month",
          global_period: state.analyticsGlobalPeriod || "month",
          global_date_from: state.analyticsGlobalDateFrom || "",
          global_date_to: state.analyticsGlobalDateTo || "",
          breakdown_level: state.analyticsBreakdownLevel || "category",
          structure_hidden: normalizeStructureHidden(state.analyticsStructureHidden),
          category_kind: state.analyticsCategoryKind || "expense",
          granularity: state.analyticsGranularity || "day",
          currency_filter: state.analyticsCurrencyFilter || "all",
        },
        admin: {
          ...(state.preferences?.data?.admin || {}),
          user_status_filter: state.adminUserStatusFilter || "pending",
        },
        plans: {
          ...(state.preferences?.data?.plans || {}),
          status_filter: state.plansStatusFilter || "all",
          history_event_filter: state.plansHistoryEventFilter || "all",
          dashboard_period: state.dashboardPlansPeriod || "month",
          reminders_enabled: el.plansRemindersToggle ? el.plansRemindersToggle.checked : (state.preferences?.data?.plans?.reminders_enabled !== false),
          reminder_time: el.plansReminderTimeInput ? String(el.plansReminderTimeInput.value || "09:00") : String(state.preferences?.data?.plans?.reminder_time || "09:00"),
        },
        currency: {
          ...(state.preferences?.data?.currency || {}),
          ...DEFAULT_CURRENCY_PREFS,
          tracked_currencies: trackedCurrencies.length ? trackedCurrencies : [...DEFAULT_CURRENCY_PREFS.tracked_currencies],
          show_dashboard_kpi: el.showDashboardCurrencyToggle ? el.showDashboardCurrencyToggle.checked : getMergedCurrencyPrefs().show_dashboard_kpi,
          telegram_digest_enabled: el.currencyDigestToggle ? el.currencyDigestToggle.checked : getMergedCurrencyPrefs().telegram_digest_enabled,
        },
        ui: {
          ...(state.preferences?.data?.ui || {}),
          ...DEFAULT_UI_PREFS,
          active_section: state.activeSection,
          timezone: el.timezoneSelect ? el.timezoneSelect.value : getMergedUiPrefs().timezone,
          browser_timezone: (() => {
            try {
              return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
            } catch {
              return "";
            }
          })(),
          currency: el.currencySelect ? el.currencySelect.value : getMergedUiPrefs().currency,
          currency_position: el.currencyPositionSelect ? el.currencyPositionSelect.value : getMergedUiPrefs().currency_position,
          show_dashboard_analytics: el.showDashboardAnalyticsToggle ? el.showDashboardAnalyticsToggle.checked : getMergedUiPrefs().show_dashboard_analytics,
          show_dashboard_operations: el.showDashboardOperationsToggle ? el.showDashboardOperationsToggle.checked : getMergedUiPrefs().show_dashboard_operations,
          show_dashboard_debts: el.showDashboardDebtsToggle ? el.showDashboardDebtsToggle.checked : getMergedUiPrefs().show_dashboard_debts,
          dashboard_operations_limit: el.dashboardOperationsLimitSelect
            ? Number(el.dashboardOperationsLimitSelect.value || 8)
            : getMergedUiPrefs().dashboard_operations_limit,
          scale_percent: el.uiScaleRange ? Number(el.uiScaleRange.value || 100) : getMergedUiPrefs().scale_percent,
          item_catalog_sort_preset: state.itemCatalogSortPreset || "usage",
        },
      },
    };
  }

  async function savePreferences() {
    if (!state.preferences) {
      return;
    }
    state.preferences = await core.requestJson("/api/v1/preferences", {
      method: "PUT",
      headers: core.authHeaders(),
      body: JSON.stringify(buildPreferencesPayload()),
    });
    core.invalidateUiRequestCache();
  }

  function savePreferencesDebounced(delayMs = 450) {
    const delay = Number(delayMs || 0);
    const normalizedDelay = Number.isFinite(delay) && delay > 0 ? delay : 450;
    if (preferencesSaveDebounceId) {
      clearTimeout(preferencesSaveDebounceId);
    }
    preferencesSaveDebounceId = setTimeout(() => {
      preferencesSaveDebounceId = null;
      savePreferences().catch(() => {});
    }, normalizedDelay);
  }

  function cancelDebouncedPreferencesSave() {
    if (!preferencesSaveDebounceId) {
      return;
    }
    clearTimeout(preferencesSaveDebounceId);
    preferencesSaveDebounceId = null;
  }

  const api = {
    DEFAULT_UI_PREFS,
    DEFAULT_CURRENCY_PREFS,
    normalizeStructureHidden,
    getMergedUiPrefs,
    getMergedCurrencyPrefs,
    applyInterfaceSettingsUi,
    previewInterfaceSettingsUi,
    syncSettingsPickerButtons,
    openSettingsPickerModal,
    closeSettingsPickerModal,
    applySettingsPickerValue,
    loadPreferences,
    savePreferences,
    savePreferencesDebounced,
    cancelDebouncedPreferencesSave,
  };

  window.App.registerRuntimeModule?.("session-preferences", api);
})();
