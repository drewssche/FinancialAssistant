(() => {
  const { state, el, core } = window.App;

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getActions() {
    return window.App.actions || {};
  }

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function getTelegramWebApp() {
    return window.App.telegramWebApp;
  }

  function bindColorSyncHandlers() {
    el.groupAccentColor.addEventListener("input", () => {
      el.groupAccentColorHex.value = el.groupAccentColor.value;
    });
    el.groupAccentColorHex.addEventListener("input", () => {
      if (/^#[0-9a-fA-F]{6}$/.test(el.groupAccentColorHex.value)) {
        el.groupAccentColor.value = el.groupAccentColorHex.value;
      }
    });
    el.editGroupAccentColor.addEventListener("input", () => {
      el.editGroupAccentColorHex.value = el.editGroupAccentColor.value;
    });
    el.editGroupAccentColorHex.addEventListener("input", () => {
      if (/^#[0-9a-fA-F]{6}$/.test(el.editGroupAccentColorHex.value)) {
        el.editGroupAccentColor.value = el.editGroupAccentColorHex.value;
      }
    });
  }

  async function startApp() {
    if (getTelegramWebApp()?.init) {
      getTelegramWebApp().init();
    }

    if (getCategoryActions().setupCategoryIconPickers) {
      getCategoryActions().setupCategoryIconPickers();
    }
    bindColorSyncHandlers();

    if (getActions().renderTodayLabel) {
      getActions().renderTodayLabel();
    }

    if (getSessionFeature().loadTelegramLoginConfig) {
      await getSessionFeature().loadTelegramLoginConfig();
    }

    if (state.token) {
      core.showApp();
      getSessionFeature().bootstrapApp?.().catch((err) => {
        if (!state.token) {
          core.showLogin(String(err));
          return;
        }
        const message = err instanceof Error ? err.message : String(err);
        core.showApp();
        core.setStatus(`Ошибка загрузки: ${message}`);
      });
      return;
    }

    if (getSessionFeature().tryAutoTelegramLogin) {
      try {
        const loggedIn = await getSessionFeature().tryAutoTelegramLogin();
        if (loggedIn) {
          return;
        }
      } catch (err) {
        core.showLogin(err instanceof Error ? err.message : String(err));
        return;
      }
    }

    core.showLogin();
  }

  const api = {
    startApp,
  };

  window.App.initStartup = api;
  window.App.registerBootstrapModule?.("startup", api);
})();
