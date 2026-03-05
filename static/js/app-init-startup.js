(() => {
  const { state, el, core, actions } = window.App;

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

  function startApp() {
    if (actions.setupCategoryIconPickers) {
      actions.setupCategoryIconPickers();
    }
    bindColorSyncHandlers();

    if (window.App.actions.renderTodayLabel) {
      window.App.actions.renderTodayLabel();
    }

    if (state.token) {
      actions.bootstrapApp().catch((err) => {
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

    core.showLogin();
  }

  window.App.initStartup = {
    startApp,
  };
})();
