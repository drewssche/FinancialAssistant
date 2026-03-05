(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const operationModal = window.App.operationModal;

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
    state.period = ["day", "week", "month", "year", "custom"].includes(savedPeriod) ? savedPeriod : "day";
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
          active_section: state.activeSection,
          timezone: el.timezoneSelect ? el.timezoneSelect.value : state.preferences.data?.ui?.timezone || "auto",
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
    if (window.App.actions.renderTodayLabel) {
      window.App.actions.renderTodayLabel();
    }
  }

  function logout(showMessage = true) {
    localStorage.removeItem("access_token");
    state.token = "";
    state.preferences = null;
    state.page = 1;
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
    core.setStatus("Готово");
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
    core.setStatus("Авторизация успешна", true);
    await bootstrapApp();
  }

  window.App.featureSession = {
    loadMe,
    loadPreferences,
    savePreferences,
    saveSettings,
    logout,
    bootstrapApp,
    devLogin,
  };
})();
