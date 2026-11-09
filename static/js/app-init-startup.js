(() => {
  const { state, el, core } = window.App;

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getNavigationActions() {
    return window.App.getRuntimeModule?.("navigation") || {};
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
    core.showSessionChecking?.();
    getTelegramWebApp()?.init?.();
    document.getElementById("telegramSdk")?.addEventListener("load", () => {
      getTelegramWebApp()?.init?.();
      getSessionFeature().refreshTelegramLoginUi?.();
      if (!state.token && !el.loginContent?.classList.contains("hidden")) {
        getSessionFeature().tryAutoTelegramLogin?.().catch((err) => core.showLogin(err.message));
      }
    }, { once: true });

    if (getCategoryActions().setupCategoryIconPickers) {
      getCategoryActions().setupCategoryIconPickers();
    }
    bindColorSyncHandlers();

    if (getNavigationActions().renderTodayLabel) {
      getNavigationActions().renderTodayLabel();
    }

    if (getSessionFeature().loadTelegramLoginConfig) {
      await getSessionFeature().loadTelegramLoginConfig();
    }

    if (state.token) {
      getSessionFeature().bootstrapApp?.().catch((err) => {
        const message = err instanceof Error ? err.message : String(err);
        if (!state.currentUserId || !state.token) {
          if (err.status === 401 && state.token) getSessionFeature().logout(false);
          core.showLogin(message);
          return;
        }
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
