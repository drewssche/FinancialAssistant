(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const operationModal = window.App.operationModal;
  let preferencesSaveDebounceId = null;
  const DEFAULT_UI_PREFS = {
    timezone: "auto",
    currency: "BYN",
    currency_position: "suffix",
    show_dashboard_analytics: true,
    show_dashboard_operations: true,
    show_dashboard_debts: true,
    dashboard_operations_limit: 8,
    scale_percent: 100,
  };

  async function loadTelegramLoginConfig() {
    try {
      const data = await core.requestJson("/api/v1/auth/public-config");
      state.telegramBotUsername = String(data.telegram_bot_username || "").trim();
      state.browserTelegramLoginAvailable = data.browser_login_available === true;
    } catch {
      state.telegramBotUsername = "";
      state.browserTelegramLoginAvailable = false;
    }
    applyTelegramLoginUi();
    return state.telegramBotUsername;
  }

  async function telegramBrowserLogin(authData) {
    const data = await core.requestJson("/api/v1/auth/telegram/browser", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(authData),
    });
    state.token = data.access_token;
    localStorage.setItem("access_token", data.access_token);
    await bootstrapApp();
  }

  function ensureBrowserTelegramWidget() {
    if (
      !el.telegramBrowserLogin
      || state.browserTelegramLoginReady
      || !state.telegramBotUsername
      || state.browserTelegramLoginAvailable !== true
    ) {
      return;
    }
    window.onTelegramAuth = (user) => {
      telegramBrowserLogin(user).catch((err) => {
        const message = err instanceof Error ? err.message : String(err);
        core.showLogin(message || "Ошибка входа через Telegram");
      });
    };
    el.telegramBrowserLogin.innerHTML = "";
    const script = document.createElement("script");
    script.async = true;
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", state.telegramBotUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "12");
    script.setAttribute("data-userpic", "false");
    script.setAttribute("data-request-access", "write");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    el.telegramBrowserLogin.appendChild(script);
    state.browserTelegramLoginReady = true;
  }

  function applyTelegramLoginUi() {
    if (el.loginTelegramHint) {
      const hasInitData = Boolean(window.Telegram?.WebApp?.initData);
      if (el.telegramLoginBtn) {
        el.telegramLoginBtn.textContent = hasInitData
          ? "Войти через Telegram Mini App"
          : "Войти через Telegram";
        el.telegramLoginBtn.classList.toggle("hidden", !hasInitData);
      }
      if (el.telegramBrowserLoginWrap) {
        const showBrowserWidget = (
          !hasInitData
          && Boolean(state.telegramBotUsername)
          && state.browserTelegramLoginAvailable === true
        );
        el.telegramBrowserLoginWrap.classList.toggle("hidden", !showBrowserWidget);
        if (showBrowserWidget) {
          ensureBrowserTelegramWidget();
        }
      }
      el.loginTelegramHint.classList.remove("hidden");
      el.loginTelegramHint.textContent = hasInitData
        ? "Обнаружен Telegram Mini App. Нажмите «Войти через Telegram Mini App» или дождитесь авто-входа."
        : state.browserTelegramLoginAvailable === true
          ? "В браузере доступен вход через Telegram. Используйте виджет выше."
          : "Вход без Telegram Mini App сейчас недоступен. Откройте приложение внутри Telegram или настройте TELEGRAM_BOT_USERNAME для browser login.";
    }
  }

  function refreshTelegramLoginUi() {
    applyTelegramLoginUi();
  }

  function getMergedUiPrefs() {
    return {
      ...DEFAULT_UI_PREFS,
      ...(state.preferences?.data?.ui || {}),
    };
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
    if (el.showDashboardAnalyticsToggle) {
      el.showDashboardAnalyticsToggle.checked = ui.show_dashboard_analytics !== false;
    }
    if (el.showDashboardOperationsToggle) {
      el.showDashboardOperationsToggle.checked = ui.show_dashboard_operations !== false;
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
    if (el.dashboardOperationsPanel) {
      el.dashboardOperationsPanel.classList.toggle("hidden", ui.show_dashboard_operations === false);
    }
    if (el.dashboardDebtsPanel) {
      el.dashboardDebtsPanel.classList.toggle("hidden", ui.show_dashboard_debts === false);
    }
    if (el.analyticsTopOperationsLimitSelect) {
      el.analyticsTopOperationsLimitSelect.value = String(state.analyticsTopOperationsLimit || 5);
    }
    if (el.analyticsTopPositionsLimitSelect) {
      el.analyticsTopPositionsLimitSelect.value = String(state.analyticsTopPositionsLimit || 10);
    }
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
    if (el.dashboardAnalyticsPanel && el.showDashboardAnalyticsToggle) {
      el.dashboardAnalyticsPanel.classList.toggle("hidden", !el.showDashboardAnalyticsToggle.checked);
    }
    if (el.dashboardOperationsPanel && el.showDashboardOperationsToggle) {
      el.dashboardOperationsPanel.classList.toggle("hidden", !el.showDashboardOperationsToggle.checked);
    }
  }

  async function loadMe() {
    const me = await core.requestJson("/api/v1/users/me", { headers: core.authHeaders() });
    state.isAdmin = me.is_admin === true;
    state.accessStatus = me.status || "pending";
    const name = me.display_name || "Пользователь";
    const username = String(me.username || "").trim();
    const telegramId = String(me.telegram_id || "").trim();
    el.userName.textContent = name;
    el.userHandle.textContent = username ? `@${username}` : (telegramId ? `ID ${telegramId}` : "Telegram");
    el.userAvatar.textContent = name[0]?.toUpperCase() || "П";
    if (!state.isAdmin && state.accessStatus !== "approved" && state.accessStatus !== "active") {
      const reason = state.accessStatus === "rejected"
        ? "Доступ отклонен администратором"
        : "Заявка отправлена. Ожидайте одобрения администратора";
      logout(false);
      throw new Error(reason);
    }
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
    state.operationSortPreset = prefs.data?.operations?.sort_preset || "date";
    state.debtSortPreset = prefs.data?.debts?.sort_preset || "priority";
    state.itemCatalogSortPreset = prefs.data?.ui?.item_catalog_sort_preset || "usage";
    state.analyticsMonthAnchor = prefs.data?.analytics?.month_anchor || "";
    state.analyticsTab = prefs.data?.analytics?.tab || "overview";
    if (state.analyticsTab === "positions") {
      state.analyticsTab = "operations";
    }
    if (!["overview", "calendar", "operations", "trends"].includes(state.analyticsTab)) {
      state.analyticsTab = "overview";
    }
    state.analyticsCalendarView = prefs.data?.analytics?.calendar_view || "month";
    state.analyticsSummaryPeriod = prefs.data?.analytics?.summary_period || "month";
    state.analyticsSummaryDateFrom = prefs.data?.analytics?.summary_date_from || "";
    state.analyticsSummaryDateTo = prefs.data?.analytics?.summary_date_to || "";
    state.analyticsPeriod = prefs.data?.analytics?.period || "month";
    state.analyticsGranularity = prefs.data?.analytics?.granularity || "day";
    state.analyticsTopOperationsLimit = [3, 5, 10].includes(Number(prefs.data?.analytics?.top_operations_limit))
      ? Number(prefs.data?.analytics?.top_operations_limit)
      : 5;
    state.analyticsTopPositionsLimit = [5, 10, 20].includes(Number(prefs.data?.analytics?.top_positions_limit))
      ? Number(prefs.data?.analytics?.top_positions_limit)
      : 10;
    state.adminUserStatusFilter = prefs.data?.admin?.user_status_filter || "pending";
    el.filterQ.value = prefs.data?.operations?.filters?.q || "";
    state.activeSection = prefs.data?.ui?.active_section || "dashboard";

    core.syncAllPeriodTabs(state.period);
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    core.syncSegmentedActive(el.operationsSortTabs, "op-sort", state.operationSortPreset);
    core.syncSegmentedActive(el.debtSortTabs, "debt-sort", state.debtSortPreset);
    core.syncSegmentedActive(el.itemCatalogSortTabs, "item-sort", state.itemCatalogSortPreset);
    core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", state.analyticsTab);
    core.syncSegmentedActive(el.analyticsCalendarViewTabs, "analytics-calendar-view", state.analyticsCalendarView);
    core.syncSegmentedActive(el.analyticsSummaryPeriodTabs, "analytics-summary-period", state.analyticsSummaryPeriod);
    core.syncSegmentedActive(el.analyticsPeriodTabs, "analytics-period", state.analyticsPeriod);
    core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
    core.syncSegmentedActive(el.adminUserStatusTabs, "admin-user-status", state.adminUserStatusFilter);
    if (window.App.actions.applyAnalyticsTabUi) {
      window.App.actions.applyAnalyticsTabUi();
    }
    applyInterfaceSettingsUi();
    operationModal.applySettingsUi();
    if (window.App.actions.renderTodayLabel) {
      window.App.actions.renderTodayLabel();
    }
  }

  async function savePreferences() {
    if (!state.preferences) {
      return;
    }

    const payload = {
      preferences_version: state.preferences.preferences_version || 1,
      data: {
        ...state.preferences.data,
        dashboard: {
          ...(state.preferences.data?.dashboard || {}),
          period: state.period,
          custom_date_from: state.customDateFrom || "",
          custom_date_to: state.customDateTo || "",
        },
        operations: {
          ...(state.preferences.data?.operations || {}),
          sort_preset: state.operationSortPreset || "date",
          filters: {
            kind: state.filterKind,
            q: el.filterQ.value.trim(),
          },
        },
        debts: {
          ...(state.preferences.data?.debts || {}),
          sort_preset: state.debtSortPreset || "priority",
        },
        analytics: {
          ...(state.preferences.data?.analytics || {}),
          month_anchor: state.analyticsMonthAnchor || "",
          tab: state.analyticsTab || "overview",
          calendar_view: state.analyticsCalendarView || "month",
          summary_period: state.analyticsSummaryPeriod || "month",
          summary_date_from: state.analyticsSummaryDateFrom || "",
          summary_date_to: state.analyticsSummaryDateTo || "",
          period: state.analyticsPeriod || "month",
          granularity: state.analyticsGranularity || "day",
          top_operations_limit: state.analyticsTopOperationsLimit || 5,
          top_positions_limit: state.analyticsTopPositionsLimit || 10,
        },
        admin: {
          ...(state.preferences.data?.admin || {}),
          user_status_filter: state.adminUserStatusFilter || "pending",
        },
        ui: {
          ...(state.preferences.data?.ui || {}),
          ...DEFAULT_UI_PREFS,
          active_section: state.activeSection,
          timezone: el.timezoneSelect ? el.timezoneSelect.value : getMergedUiPrefs().timezone,
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

    state.preferences = await core.requestJson("/api/v1/preferences", {
      method: "PUT",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
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

  async function saveSettings(event) {
    event.preventDefault();
    await savePreferences();
    applyInterfaceSettingsUi();
    if (window.App.actions.renderTodayLabel) {
      window.App.actions.renderTodayLabel();
    }
    if (window.App.actions.refreshAll) {
      await window.App.actions.refreshAll();
    }
  }

  async function deleteMe() {
    const phrase = String(el.deleteMePhrase?.value || "").trim();
    if (phrase !== "УДАЛИТЬ") {
      core.setStatus("Введите УДАЛИТЬ для подтверждения удаления аккаунта");
      return;
    }
    await core.requestJson("/api/v1/users/me", {
      method: "DELETE",
      headers: core.authHeaders(),
    });
    logout(false);
    core.setStatus("Аккаунт удален", true);
  }

  function logout(showMessage = true) {
    cancelDebouncedPreferencesSave();
    localStorage.removeItem("access_token");
    state.token = "";
    state.preferences = null;
    state.page = 1;
    state.operationsHasMore = true;
    state.operationsLoading = false;
    state.firstOperationDate = "";
    state.allTimeAnchorResolved = false;
    state.total = 0;
    state.uiRequestCache.clear();
    operationModal.closeCreateModal();
    operationModal.closeEditModal();
    if (categoryActions.closeCreateCategoryModal) {
      categoryActions.closeCreateCategoryModal();
    }
    if (window.App.actions.closeEditCategoryModal) {
      window.App.actions.closeEditCategoryModal();
    }
    operationModal.closePeriodCustomModal();
    core.closeConfirm();
    core.closeAllMenus();

    el.toastArea.innerHTML = "";
    for (const [, toast] of state.toasts) {
      clearTimeout(toast.timeoutId);
    }
    state.toasts.clear();
    core.applyUiScale(100);
    core.applyMoneyInputs(core.resolveCurrencyConfig("BYN", "suffix"));

    core.showLogin(showMessage ? "Вы вышли" : "");
  }

  async function bootstrapApp() {
    core.showApp();
    await loadMe();
    await loadPreferences();
    if (window.App.actions.applySectionUi) {
      window.App.actions.applySectionUi();
    }
    if (window.App.actions.refreshAll) {
      await window.App.actions.refreshAll();
    }
  }

  async function telegramLogin() {
    const initData = String(window.Telegram?.WebApp?.initData || "").trim();
    if (!initData) {
      throw new Error("Нет Telegram initData. Откройте приложение внутри Telegram.");
    }
    const data = await core.requestJson("/api/v1/auth/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ init_data: initData }),
    });
    state.token = data.access_token;
    localStorage.setItem("access_token", data.access_token);
    await bootstrapApp();
  }

  async function tryAutoTelegramLogin() {
    if (state.token) {
      return false;
    }
    const initData = String(window.Telegram?.WebApp?.initData || "").trim();
    if (!initData) {
      return false;
    }
    await telegramLogin();
    return true;
  }

  applyTelegramLoginUi();

  window.App.featureSession = {
    loadMe,
    loadPreferences,
    savePreferences,
    savePreferencesDebounced,
    cancelDebouncedPreferencesSave,
    saveSettings,
    applyInterfaceSettingsUi,
    previewInterfaceSettingsUi,
    deleteMe,
    logout,
    bootstrapApp,
    telegramLogin,
    telegramBrowserLogin,
    loadTelegramLoginConfig,
    refreshTelegramLoginUi,
    tryAutoTelegramLogin,
  };
})();
