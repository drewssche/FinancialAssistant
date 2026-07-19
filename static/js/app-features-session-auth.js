(() => {
  const { state, el, core } = window.App;
  const operationModal = window.App.getRuntimeModule?.("operation-modal");
  const sessionPreferences = window.App.getRuntimeModule?.("session-preferences") || {};
  const AUTO_REFRESH_WINDOW_MS = 5 * 60 * 1000;
  const SESSION_TICK_MS = 30 * 1000;
  const TELEGRAM_READY_TIMEOUT_MS = 5000;
  let telegramAuthPromise = null;
  let autoTelegramLoginPromise = null;
  let sessionRefreshPromise = null;
  let bootstrapPromise = null;
  let sessionTimerId = null;
  let sessionLifecycleBound = false;

  function parseTokenPayload(token) {
    try {
      const payload = String(token || "").split(".")[1] || "";
      const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
      const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
      return JSON.parse(atob(padded));
    } catch {
      return {};
    }
  }

  function tokenTimestampIso(rawValue) {
    const seconds = Number(rawValue || 0);
    return Number.isFinite(seconds) && seconds > 0 ? new Date(seconds * 1000).toISOString() : "";
  }

  function storeAccessToken(data, options = {}) {
    const token = String(data?.access_token || "").trim();
    if (!token) throw new Error("Сервер не вернул токен доступа");
    const claims = parseTokenPayload(token);
    state.token = token;
    state.sessionExpiresAt = data?.expires_at || (claims.exp ? new Date(Number(claims.exp) * 1000).toISOString() : "");
    state.sessionStartedAt = tokenTimestampIso(claims.session_started_at || claims.iat);
    const issuedAt = tokenTimestampIso(claims.iat);
    state.sessionLastRenewedAt = options.renewed === true
      || (claims.session_started_at && Number(claims.iat || 0) > Number(claims.session_started_at || 0) + 1)
      ? issuedAt
      : "";
    localStorage.setItem("access_token", token);
    updateSessionStatus();
    return token;
  }

  function hydrateStoredTokenMetadata() {
    if (!state.token) return;
    const claims = parseTokenPayload(state.token);
    state.sessionExpiresAt = claims.exp ? new Date(Number(claims.exp) * 1000).toISOString() : "";
    state.sessionStartedAt = tokenTimestampIso(claims.session_started_at || claims.iat);
    state.sessionLastRenewedAt = claims.session_started_at && Number(claims.iat || 0) > Number(claims.session_started_at || 0) + 1
      ? tokenTimestampIso(claims.iat)
      : "";
  }

  function sessionRemainingMs() {
    const expiresAt = Date.parse(state.sessionExpiresAt || "");
    return Number.isFinite(expiresAt) ? expiresAt - Date.now() : 0;
  }

  function formatRemainingTime(remainingMs) {
    if (remainingMs <= 0) return "Истекла";
    const minutes = Math.max(1, Math.ceil(remainingMs / 60000));
    if (minutes >= 60) return `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`;
    return `${minutes} мин`;
  }

  function formatSessionTime(value) {
    const parsed = new Date(value || "");
    if (Number.isNaN(parsed.getTime())) return "";
    return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(parsed);
  }

  function updateSessionStatus() {
    if (!el.sessionStatusRow || !el.sessionRemainingLabel) return;
    const remainingMs = sessionRemainingMs();
    const visible = Boolean(state.token && state.sessionExpiresAt);
    el.sessionStatusRow.classList.toggle("hidden", !visible);
    if (!visible) return;
    el.sessionRemainingLabel.textContent = remainingMs > 0
      ? `Осталось ${formatRemainingTime(remainingMs)}`
      : "Сессия истекла";
    const startedAt = formatSessionTime(state.sessionStartedAt);
    const expiresAt = formatSessionTime(state.sessionExpiresAt);
    const renewedAt = formatSessionTime(state.sessionLastRenewedAt);
    if (el.sessionStartedLabel) {
      el.sessionStartedLabel.textContent = startedAt ? `Начата ${startedAt}` : "Сессия";
    }
    if (el.sessionExpiresLabel) {
      el.sessionExpiresLabel.textContent = expiresAt ? `Завершится ${expiresAt}` : "";
      el.sessionExpiresLabel.classList.toggle("hidden", !expiresAt);
    }
    if (el.sessionRenewedLabel) {
      el.sessionRenewedLabel.textContent = renewedAt ? `Обновлена ${renewedAt}` : "";
      el.sessionRenewedLabel.classList.toggle("hidden", !renewedAt);
    }
    el.sessionStatusRow.classList.toggle("is-warning", remainingMs > 0 && remainingMs <= AUTO_REFRESH_WINDOW_MS);
    el.sessionStatusRow.classList.toggle("is-expired", remainingMs <= 0);
    [el.sessionRefreshBtn, el.createSessionRefreshBtn, el.editSessionRefreshBtn].forEach((button) => {
      if (button) button.disabled = state.sessionRefreshPending === true;
    });
  }

  function telegramInitData() {
    return String(window.Telegram?.WebApp?.initData || "").trim();
  }

  function hasTelegramLaunchContext() {
    if (telegramInitData()) return true;
    const platform = String(window.Telegram?.WebApp?.platform || "").toLowerCase();
    const launchParams = `${window.location.search || ""}${window.location.hash || ""}`;
    return (platform && platform !== "unknown") || /tgWebApp(?:Data|Platform|Version)/i.test(launchParams);
  }

  async function waitForTelegramInitData(timeoutMs = TELEGRAM_READY_TIMEOUT_MS) {
    const immediate = telegramInitData();
    if (immediate) return immediate;
    if (!hasTelegramLaunchContext()) return "";
    const deadline = Date.now() + Math.max(0, timeoutMs);
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      const value = telegramInitData();
      if (value) return value;
    }
    return "";
  }

  function showSessionRecovery(message = "Данные формы сохранены. Обновите авторизацию, чтобы продолжить.") {
    state.sessionRecoveryVisible = true;
    if (el.sessionRecoveryMessage) el.sessionRecoveryMessage.textContent = message;
    el.sessionRecoveryOverlay?.classList.remove("hidden");
  }

  function hideSessionRecovery() {
    state.sessionRecoveryVisible = false;
    el.sessionRecoveryOverlay?.classList.add("hidden");
  }

  async function requestFreshAccessToken() {
    const response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: core.authHeaders(),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "Не удалось продлить сессию";
      throw new Error(detail);
    }
    return data;
  }

  async function refreshSession(options = {}) {
    const manual = options.manual === true;
    if (!state.token) throw new Error("Нет активной сессии");
    if (sessionRefreshPromise) return sessionRefreshPromise;
    state.sessionRefreshPending = true;
    updateSessionStatus();
    sessionRefreshPromise = requestFreshAccessToken()
      .then((data) => {
        storeAccessToken(data, { renewed: true });
        hideSessionRecovery();
        if (manual) core.notify?.("Сессия продлена", { type: "success" });
        return true;
      })
      .finally(() => {
        state.sessionRefreshPending = false;
        sessionRefreshPromise = null;
        updateSessionStatus();
      });
    return sessionRefreshPromise;
  }

  function authenticateTelegramInPlace(options = {}) {
    if (telegramAuthPromise) return telegramAuthPromise;
    telegramAuthPromise = (async () => {
      const initData = options.initData || await waitForTelegramInitData();
      if (!initData) throw new Error("Telegram не передал данные авторизации. Закройте и снова откройте Mini App.");
      const data = await core.requestJson("/api/v1/auth/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: initData }),
        skipAuthRecovery: true,
      });
      storeAccessToken(data);
      hideSessionRecovery();
      return true;
    })().finally(() => {
      telegramAuthPromise = null;
    });
    return telegramAuthPromise;
  }

  async function recoverUnauthorized() {
    try {
      await refreshSession();
      return true;
    } catch {}
    try {
      await authenticateTelegramInPlace();
      return true;
    } catch (err) {
      showSessionRecovery(err instanceof Error ? err.message : String(err));
      return false;
    }
  }

  async function renewSessionManually() {
    try {
      if (sessionRemainingMs() > 0) {
        try {
          await refreshSession({ manual: true });
          return true;
        } catch {}
      }
      await authenticateTelegramInPlace();
      core.notify?.("Сессия восстановлена", { type: "success" });
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (!hasTelegramLaunchContext()) {
        hideSessionRecovery();
        applyTelegramLoginUi();
        core.showLogin(message);
        return false;
      }
      showSessionRecovery(message);
      core.notify?.(message, { type: "error" });
      return false;
    }
  }

  async function maybeRefreshSession() {
    if (document.visibilityState === "hidden") return false;
    if (!state.token || !state.sessionExpiresAt) {
      updateSessionStatus();
      return false;
    }
    const remainingMs = sessionRemainingMs();
    updateSessionStatus();
    if (remainingMs > AUTO_REFRESH_WINDOW_MS) return false;
    if (remainingMs <= 0) return recoverUnauthorized();
    try {
      await refreshSession();
      return true;
    } catch {
      return recoverUnauthorized();
    }
  }

  function bindSessionLifecycle() {
    if (sessionLifecycleBound) return;
    sessionLifecycleBound = true;
    const resume = () => {
      if (document.visibilityState === "hidden") return;
      if (state.token) {
        maybeRefreshSession().catch(() => {});
        return;
      }
      tryAutoTelegramLogin({ waitForReady: true, bootstrap: true }).catch(() => {});
    };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("pageshow", resume);
  }

  function startSessionMonitor() {
    if (sessionTimerId) clearInterval(sessionTimerId);
    bindSessionLifecycle();
    updateSessionStatus();
    sessionTimerId = setInterval(() => {
      maybeRefreshSession().catch(() => {});
    }, SESSION_TICK_MS);
  }

  function stopSessionMonitor() {
    if (sessionTimerId) clearInterval(sessionTimerId);
    sessionTimerId = null;
    state.sessionExpiresAt = "";
    state.sessionStartedAt = "";
    state.sessionLastRenewedAt = "";
    updateSessionStatus();
  }

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getNavigationActions() {
    return window.App.getRuntimeModule?.("navigation") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

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
    storeAccessToken(data);
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
    script.addEventListener("error", () => {
      state.browserTelegramLoginReady = false;
      if (el.loginTelegramHint) {
        el.loginTelegramHint.textContent = "Кнопка входа Telegram не загрузилась. Откройте Mini App по ссылке выше.";
      }
    }, { once: true });
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
    if (el.telegramMiniAppLink) {
      const username = String(state.telegramBotUsername || "").replace(/^@/, "");
      el.telegramMiniAppLink.href = username ? `https://t.me/${username}?startapp=reauth` : "#";
      el.telegramMiniAppLink.classList.toggle("hidden", !username || hasInitData);
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

  function renderUserAvatar(name, avatarUrl) {
    if (!el.userAvatar) {
      return;
    }
    const initial = String(name || "Пользователь").trim()[0]?.toUpperCase() || "П";
    const safeAvatarUrl = String(avatarUrl || "").trim();
    if (!safeAvatarUrl) {
      el.userAvatar.classList.remove("avatar-image");
      el.userAvatar.innerHTML = initial;
      return;
    }
    const img = document.createElement("img");
    img.className = "avatar-photo";
    img.alt = "";
    img.src = safeAvatarUrl;
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    img.addEventListener("error", () => {
      el.userAvatar.classList.remove("avatar-image");
      el.userAvatar.innerHTML = initial;
    }, { once: true });
    el.userAvatar.classList.add("avatar-image");
    el.userAvatar.replaceChildren(img);
  }

  async function loadMe() {
    const me = await core.requestJson("/api/v1/users/me", { headers: core.authHeaders() });
    state.currentUserId = Number(me.id || 0) || null;
    state.isAdmin = me.is_admin === true;
    state.accessStatus = me.status || "pending";
    const name = me.display_name || "Пользователь";
    const username = String(me.username || "").trim();
    const telegramId = String(me.telegram_id || "").trim();
    el.userName.textContent = name;
    el.userHandle.textContent = username ? `@${username}` : (telegramId ? `ID ${telegramId}` : "Telegram");
    const activityFeature = window.App.getRuntimeModule?.("activity") || {};
    activityFeature.configureActivityButton?.(el.dashboardCurrencyActivityBtn, "currency_portfolio", state.currentUserId);
    activityFeature.configureActivityButton?.(el.currencyPortfolioActivityBtn, "currency_portfolio", state.currentUserId);
    renderUserAvatar(name, me.avatar_url);
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
    sessionPreferences.cancelDebouncedPreferencesSave?.();
    localStorage.removeItem("access_token");
    state.token = "";
    stopSessionMonitor();
    hideSessionRecovery();
    state.preferences = null;
    state.page = 1;
    state.operationsHasMore = true;
    state.operationsLoading = false;
    state.firstOperationDate = "";
    state.allTimeAnchorResolved = false;
    state.dashboardDebtSummaryLoaded = false;
    state.dashboardSummaryHydrated = false;
    state.dashboardCurrencyHydrated = false;
    state.dashboardAnalyticsHydrated = false;
    state.dashboardDebtsHydrated = false;
    state.dashboardPlansHydrated = false;
    state.plansSectionHydrated = false;
    state.debtsSectionHydrated = false;
    state.operationsSectionHydrated = false;
    state.currencySectionHydrated = false;
    state.currencyFilter = "all";
    state.analyticsStructureHydrated = false;
    state.analyticsCalendarHydrated = false;
    state.analyticsTrendHydrated = false;
    state.analyticsCurrencyHydrated = false;
    state.total = 0;
    state.uiRequestCache.clear();
    renderUserAvatar("Пользователь", "");
    operationModal.closeCreateModal();
    operationModal.closeEditModal();
    if (getCategoryActions().closeCreateCategoryModal) {
      getCategoryActions().closeCreateCategoryModal();
    }
    if (getCategoryActions().closeEditCategoryModal) {
      getCategoryActions().closeEditCategoryModal();
    }
    const navigation = getNavigationActions();
    operationModal.closePeriodCustomModal();
    window.App.getRuntimeModule?.("activity")?.closeActivityCenter?.();
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
    if (bootstrapPromise) return bootstrapPromise;
    bootstrapPromise = (async () => {
      await loadMe();
      await sessionPreferences.loadPreferences?.();
      const navigation = getNavigationActions();
      if (navigation.applySectionUi) {
        navigation.applySectionUi();
      }
      core.showApp();
      startSessionMonitor();
      if (navigation.switchSection) {
        await navigation.switchSection(state.activeSection || "dashboard", { preserveBackStack: true });
        return;
      }
      const operationsFeature = getOperationsFeature();
      if (operationsFeature.refreshAll) {
        await operationsFeature.refreshAll();
      }
    })().finally(() => {
      bootstrapPromise = null;
    });
    return bootstrapPromise;
  }

  async function telegramLogin() {
    core.showSessionChecking?.("Входим через Telegram...");
    await authenticateTelegramInPlace();
    await bootstrapApp();
  }

  function tryAutoTelegramLogin(options = {}) {
    if (state.token) {
      return Promise.resolve(false);
    }
    if (autoTelegramLoginPromise) return autoTelegramLoginPromise;
    autoTelegramLoginPromise = (async () => {
      const initData = options.waitForReady === false
        ? telegramInitData()
        : await waitForTelegramInitData();
      if (!initData) {
        return false;
      }
      core.showSessionChecking?.("Входим через Telegram...");
      await authenticateTelegramInPlace({ initData });
      if (options.bootstrap !== false) await bootstrapApp();
      return true;
    })().finally(() => {
      autoTelegramLoginPromise = null;
    });
    return autoTelegramLoginPromise;
  }

  hydrateStoredTokenMetadata();
  applyTelegramLoginUi();
  bindSessionLifecycle();

  const api = {
    loadTelegramLoginConfig,
    telegramBrowserLogin,
    refreshTelegramLoginUi,
    loadMe,
    logout,
    bootstrapApp,
    telegramLogin,
    tryAutoTelegramLogin,
    refreshSession,
    renewSessionManually,
    recoverUnauthorized,
    updateSessionStatus,
    showSessionRecovery,
    hideSessionRecovery,
  };

  window.App.registerRuntimeModule?.("session-auth", api);
})();
