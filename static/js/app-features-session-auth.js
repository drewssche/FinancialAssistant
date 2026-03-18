(() => {
  const { state, el, core } = window.App;
  const categoryActions = window.App.actions;
  const operationModal = window.App.operationModal;

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
    core.showApp();
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
    if (!el.loginTelegramHint) {
      return;
    }
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

  function refreshTelegramLoginUi() {
    applyTelegramLoginUi();
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
      logout(false, { preserveLoginAlert: true });
      throw new Error(reason);
    }
  }

  function logout(showMessage = true, options = {}) {
    const preserveLoginAlert = options?.preserveLoginAlert === true;
    window.App.featureSessionPreferences?.cancelDebouncedPreferencesSave?.();
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
    if (preserveLoginAlert) {
      core.showLogin("", { preserveAlert: true });
      return;
    }
    core.showLogin(showMessage ? "Вы вышли" : "");
  }

  async function bootstrapApp() {
    core.showApp();
    await loadMe();
    await window.App.featureSessionPreferences?.loadPreferences?.();
    if (window.App.actions.applySectionUi) {
      window.App.actions.applySectionUi();
    }
    if (window.App.actions.switchSection) {
      await window.App.actions.switchSection(state.activeSection || "dashboard", { preserveBackStack: true });
      return;
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
    core.showApp();
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

  window.App.featureSessionAuth = {
    loadTelegramLoginConfig,
    telegramBrowserLogin,
    refreshTelegramLoginUi,
    loadMe,
    logout,
    bootstrapApp,
    telegramLogin,
    tryAutoTelegramLogin,
  };
})();
