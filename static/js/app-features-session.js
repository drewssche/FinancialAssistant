(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const operationModal = window.App.operationModal;
  const DEFAULT_UI_PREFS = {
    timezone: "auto",
    currency: "BYN",
    currency_position: "suffix",
    show_dashboard_debts: true,
    scale_percent: 100,
  };

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
    core.applyUiScale(ui.scale_percent || 100);
    core.applyMoneyInputs(core.resolveCurrencyConfig(ui.currency, ui.currency_position));
    if (el.dashboardDebtsPanel) {
      el.dashboardDebtsPanel.classList.toggle("hidden", ui.show_dashboard_debts === false);
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
  }

  async function loadMe() {
    const me = await core.requestJson("/api/v1/users/me", { headers: core.authHeaders() });
    const name = me.display_name || "Пользователь";
    el.userName.textContent = name;
    el.userHandle.textContent = `@${name.toLowerCase().replace(/\s+/g, "_")}`;
    el.userAvatar.textContent = name[0]?.toUpperCase() || "П";
  }

  async function loadPreferences() {
    const prefs = await core.requestJson("/api/v1/preferences", { headers: core.authHeaders() });
    state.preferences = prefs;

    const savedPeriod = prefs.data?.dashboard?.period || "day";
    state.period = ["day", "week", "month", "year", "all_time", "custom"].includes(savedPeriod) ? savedPeriod : "day";
    state.customDateFrom = prefs.data?.dashboard?.custom_date_from || "";
    state.customDateTo = prefs.data?.dashboard?.custom_date_to || "";
    if (state.period === "custom" && (!state.customDateFrom || !state.customDateTo)) {
      state.period = "day";
    }
    state.filterKind = prefs.data?.operations?.filters?.kind || "";
    el.filterQ.value = prefs.data?.operations?.filters?.q || "";
    state.activeSection = prefs.data?.ui?.active_section || "dashboard";

    core.syncAllPeriodTabs(state.period);
    core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
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
          filters: {
            kind: state.filterKind,
            q: el.filterQ.value.trim(),
          },
        },
        ui: {
          ...(state.preferences.data?.ui || {}),
          ...DEFAULT_UI_PREFS,
          active_section: state.activeSection,
          timezone: el.timezoneSelect ? el.timezoneSelect.value : getMergedUiPrefs().timezone,
          currency: el.currencySelect ? el.currencySelect.value : getMergedUiPrefs().currency,
          currency_position: el.currencyPositionSelect ? el.currencyPositionSelect.value : getMergedUiPrefs().currency_position,
          show_dashboard_debts: el.showDashboardDebtsToggle ? el.showDashboardDebtsToggle.checked : getMergedUiPrefs().show_dashboard_debts,
          scale_percent: el.uiScaleRange ? Number(el.uiScaleRange.value || 100) : getMergedUiPrefs().scale_percent,
        },
      },
    };

    state.preferences = await core.requestJson("/api/v1/preferences", {
      method: "PUT",
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    });
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
    localStorage.removeItem("access_token");
    state.token = "";
    state.preferences = null;
    state.page = 1;
    state.operationsHasMore = true;
    state.operationsLoading = false;
    state.firstOperationDate = "";
    state.allTimeAnchorResolved = false;
    state.total = 0;
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

  async function devLogin() {
    const firstName = document.getElementById("firstName").value || "Dev";
    const username = document.getElementById("username").value || "dev_user";

    const data = await core.requestJson("/api/v1/auth/dev", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telegram_id: 100001, first_name: firstName, username }),
    });

    state.token = data.access_token;
    localStorage.setItem("access_token", data.access_token);
    await bootstrapApp();
  }

  window.App.featureSession = {
    loadMe,
    loadPreferences,
    savePreferences,
    saveSettings,
    applyInterfaceSettingsUi,
    previewInterfaceSettingsUi,
    deleteMe,
    logout,
    bootstrapApp,
    devLogin,
  };
})();
