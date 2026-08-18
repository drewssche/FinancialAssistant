(() => {
  const { el, core } = window.App;
  const preferences = window.App.getRuntimeModule?.("session-preferences") || {};
  const auth = window.App.getRuntimeModule?.("session-auth") || {};

  function getNavigationActions() {
    return window.App.getRuntimeModule?.("navigation") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  async function saveSettings(event) {
    event.preventDefault();
    await preferences.savePreferences?.();
    preferences.applyInterfaceSettingsUi?.();
    if (getNavigationActions().renderTodayLabel) {
      getNavigationActions().renderTodayLabel();
    }
    const operationsFeature = getOperationsFeature();
    if (operationsFeature.refreshAll) {
      await operationsFeature.refreshAll();
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
    auth.logout?.(false);
    core.setStatus("Аккаунт удален", true);
  }

  const api = {
    loadMe: auth.loadMe,
    loadPreferences: preferences.loadPreferences,
    savePreferences: preferences.savePreferences,
    savePreferencesDebounced: preferences.savePreferencesDebounced,
    cancelDebouncedPreferencesSave: preferences.cancelDebouncedPreferencesSave,
    saveSettings,
    applyInterfaceSettingsUi: preferences.applyInterfaceSettingsUi,
    previewInterfaceSettingsUi: preferences.previewInterfaceSettingsUi,
    syncSettingsPickerButtons: preferences.syncSettingsPickerButtons,
    openSettingsPickerModal: preferences.openSettingsPickerModal,
    closeSettingsPickerModal: preferences.closeSettingsPickerModal,
    applySettingsPickerValue: preferences.applySettingsPickerValue,
    addBankCurrencyAlertRule: preferences.addBankCurrencyAlertRule,
    removeBankCurrencyAlertRule: preferences.removeBankCurrencyAlertRule,
    deleteMe,
    logout: auth.logout,
    bootstrapApp: auth.bootstrapApp,
    telegramLogin: auth.telegramLogin,
    telegramBrowserLogin: auth.telegramBrowserLogin,
    loadTelegramLoginConfig: auth.loadTelegramLoginConfig,
    refreshTelegramLoginUi: auth.refreshTelegramLoginUi,
    tryAutoTelegramLogin: auth.tryAutoTelegramLogin,
    refreshSession: auth.refreshSession,
    renewSessionManually: auth.renewSessionManually,
    recoverUnauthorized: auth.recoverUnauthorized,
    updateSessionStatus: auth.updateSessionStatus,
    showSessionRecovery: auth.showSessionRecovery,
    hideSessionRecovery: auth.hideSessionRecovery,
  };

  window.App.registerRuntimeModule?.("session", api);
})();
