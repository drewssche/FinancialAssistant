(() => {
  const { el, core } = window.App;
  const preferences = window.App.featureSessionPreferences || {};
  const auth = window.App.featureSessionAuth || {};

  async function saveSettings(event) {
    event.preventDefault();
    await preferences.savePreferences?.();
    preferences.applyInterfaceSettingsUi?.();
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
    auth.logout?.(false);
    core.setStatus("Аккаунт удален", true);
  }

  window.App.featureSession = {
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
    deleteMe,
    logout: auth.logout,
    bootstrapApp: auth.bootstrapApp,
    telegramLogin: auth.telegramLogin,
    telegramBrowserLogin: auth.telegramBrowserLogin,
    loadTelegramLoginConfig: auth.loadTelegramLoginConfig,
    refreshTelegramLoginUi: auth.refreshTelegramLoginUi,
    tryAutoTelegramLogin: auth.tryAutoTelegramLogin,
  };
})();
