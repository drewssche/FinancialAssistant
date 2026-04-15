(() => {
  const { state, el, core } = window.App;

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function isAbortError(err) {
    if (!err) {
      return false;
    }
    if (err.name === "AbortError") {
      return true;
    }
    return String(err).toLowerCase().includes("abort");
  }

  function errorMessage(err, fallback = "Неизвестная ошибка") {
    if (err instanceof Error) {
      return String(err.message || fallback).trim() || fallback;
    }
    if (typeof err === "string") {
      const trimmed = err.trim();
      return trimmed || fallback;
    }
    try {
      const serialized = JSON.stringify(err);
      return serialized && serialized !== "{}" ? serialized : fallback;
    } catch {
      return fallback;
    }
  }

  function dismissToast(toastId) {
    const item = state.toasts.get(toastId);
    if (!item) {
      return;
    }
    clearTimeout(item.timeoutId);
    item.toast.remove();
    state.toasts.delete(toastId);
  }

  function showToast(message, options = {}) {
    const type = options.type || "info";
    const durationMs = options.durationMs ?? (type === "error" ? 6000 : 3200);
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-header">
        <div class="toast-text">${message}</div>
        <button class="toast-close" type="button" data-toast-close="${id}" aria-label="Закрыть">×</button>
      </div>
      <div class="toast-progress"><div class="toast-progress-bar" style="animation-duration:${durationMs}ms"></div></div>
    `;

    el.toastArea.appendChild(toast);
    const timeoutId = setTimeout(() => dismissToast(id), durationMs);
    state.toasts.set(id, { toast, timeoutId, onUndo: null });
    return id;
  }

  function notify(message, options = {}) {
    const text = String(message || "").trim();
    if (!text) {
      return null;
    }
    const type = options.type || core.inferStatusType(text);
    if (type === "error") {
      const now = Date.now();
      const prev = state.lastErrorToast || { message: "", ts: 0 };
      if (prev.message === text && now - prev.ts < 3000) {
        return null;
      }
      state.lastErrorToast = { message: text, ts: now };
    }
    return showToast(text, { ...options, type });
  }

  async function requestJson(url, options = {}) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      if (isAbortError(err)) {
        throw err;
      }
      const path = (() => {
        try {
          return new URL(url, window.location.origin).pathname;
        } catch {
          return url;
        }
      })();
      const raw = errorMessage(err, "Сетевой запрос не выполнен");
      const normalized = raw.toLowerCase();
      if (
        normalized.includes("failed to fetch")
        || normalized.includes("networkerror")
        || normalized.includes("err_address_unreachable")
        || normalized.includes("load failed")
      ) {
        throw new Error(`Сеть недоступна: ${path}. Проверь домен, DNS и доступность сервера`);
      }
      throw new Error(`Сбой запроса: ${path}. ${raw}`);
    }
    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      getSessionFeature().logout?.(false);
      throw new Error("Сессия истекла, авторизуйся снова");
    }

    if (!response.ok) {
      const path = (() => {
        try {
          return new URL(url, window.location.origin).pathname;
        } catch {
          return url;
        }
      })();
      const detail = typeof data.detail === "string" ? data.detail.trim() : "";
      if (detail) {
        throw new Error(`Ошибка запроса [${response.status}] ${path}: ${detail}`);
      }
      throw new Error(`Ошибка запроса [${response.status}] ${path}`);
    }

    return data;
  }

  function getUiRequestCache(cacheKey, maxAgeMs) {
    const key = String(cacheKey || "").trim();
    if (!key) {
      return null;
    }
    const item = state.uiRequestCache.get(key);
    if (!item) {
      return null;
    }
    const ttl = Number(maxAgeMs || 0);
    if (!Number.isFinite(ttl) || ttl <= 0) {
      state.uiRequestCache.delete(key);
      return null;
    }
    const age = Date.now() - Number(item.ts || 0);
    if (age < 0 || age > ttl) {
      state.uiRequestCache.delete(key);
      return null;
    }
    return item.payload;
  }

  function setUiRequestCache(cacheKey, payload) {
    const key = String(cacheKey || "").trim();
    if (!key) {
      return;
    }
    state.uiRequestCache.set(key, {
      ts: Date.now(),
      payload,
    });
    const maxEntries = 80;
    if (state.uiRequestCache.size > maxEntries) {
      const oldestKey = state.uiRequestCache.keys().next().value;
      if (oldestKey) {
        state.uiRequestCache.delete(oldestKey);
      }
    }
  }

  function invalidateUiRequestCache(prefix = "") {
    const normalized = String(prefix || "").trim();
    if (!normalized) {
      state.uiRequestCache.clear();
      return;
    }
    for (const key of Array.from(state.uiRequestCache.keys())) {
      if (key.startsWith(`${normalized}:`)) {
        state.uiRequestCache.delete(key);
      }
    }
  }

  function showConfirm(message, onConfirm, options = {}) {
    const {
      title = "Подтверждение удаления",
      confirmLabel = "Удалить",
      cancelLabel = "Отмена",
      confirmTone = "danger",
    } = options;
    if (el.confirmTitle) {
      el.confirmTitle.textContent = title;
    }
    el.confirmText.textContent = message;
    if (el.confirmDeleteBtn) {
      el.confirmDeleteBtn.textContent = confirmLabel;
      el.confirmDeleteBtn.classList.remove("btn-danger", "btn-primary", "btn-secondary");
      el.confirmDeleteBtn.classList.add(confirmTone === "primary" ? "btn-primary" : confirmTone === "secondary" ? "btn-secondary" : "btn-danger");
    }
    if (el.confirmCancelBtn) {
      el.confirmCancelBtn.textContent = cancelLabel;
    }
    state.pendingConfirm = onConfirm;
    el.confirmModal.classList.remove("hidden");
  }

  function closeConfirm() {
    state.pendingConfirm = null;
    if (el.confirmTitle) {
      el.confirmTitle.textContent = "Подтверждение удаления";
    }
    if (el.confirmText) {
      el.confirmText.textContent = "Вы уверены, что хотите удалить объект?";
    }
    if (el.confirmDeleteBtn) {
      el.confirmDeleteBtn.textContent = "Удалить";
      el.confirmDeleteBtn.classList.remove("btn-primary", "btn-secondary");
      el.confirmDeleteBtn.classList.add("btn-danger");
    }
    if (el.confirmCancelBtn) {
      el.confirmCancelBtn.textContent = "Отмена";
    }
    el.confirmModal.classList.add("hidden");
  }

  function showUndoToast(message, onUndo, durationMs = 6000) {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const toast = document.createElement("div");
    toast.className = "toast toast-info";
    toast.innerHTML = `
      <div class="toast-header">
        <div class="toast-text">${message}</div>
        <button class="btn btn-secondary" data-toast-undo="${id}">Отменить</button>
      </div>
      <div class="toast-progress"><div class="toast-progress-bar" style="animation-duration:${durationMs}ms"></div></div>
    `;

    el.toastArea.appendChild(toast);
    const timeoutId = setTimeout(() => {
      state.toasts.delete(id);
      toast.remove();
    }, durationMs);

    state.toasts.set(id, { toast, timeoutId, onUndo });
  }

  function handleUndoClick(toastId) {
    const item = state.toasts.get(toastId);
    if (!item) {
      return;
    }

    dismissToast(toastId);

    item.onUndo()
      .then((message) => core.setStatus(message || "Изменение отменено"))
      .catch((err) => core.setStatus(`Не удалось отменить: ${err}`));
  }

  function runDestructiveAction(config) {
    const {
      confirmMessage,
      doDelete,
      onAfterDelete,
      toastMessage,
      undoAction,
      onDeleteError = "Не удалось выполнить удаление",
      confirmTitle,
      confirmLabel,
      cancelLabel,
      confirmTone,
    } = config;

    showConfirm(confirmMessage, async () => {
      try {
        await doDelete();
        if (onAfterDelete) {
          await onAfterDelete();
        }
      } catch (err) {
        core.setStatus(`${onDeleteError}: ${err}`);
        return;
      }

      if (toastMessage && undoAction) {
        showUndoToast(toastMessage, undoAction);
      }
    }, {
      title: confirmTitle,
      confirmLabel,
      cancelLabel,
      confirmTone,
    });
  }

  function setButtonLoading(button, isLoading, pendingText = "Сохранение...") {
    if (!button) {
      return true;
    }

    if (isLoading) {
      if (button.dataset.loading === "1") {
        return false;
      }
      button.dataset.loading = "1";
      button.dataset.originalText = button.textContent || "";
      button.textContent = pendingText;
      button.disabled = true;
      button.classList.add("is-loading");
      return true;
    }

    button.disabled = false;
    button.classList.remove("is-loading");
    if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
    delete button.dataset.loading;
    delete button.dataset.originalText;
    return true;
  }

  async function runAction(config) {
    const {
      action,
      button = null,
      pendingText = "Сохранение...",
      successMessage = "",
      errorPrefix = "",
      shouldPrefixError = null,
      forLogin = false,
      rethrow = false,
    } = config;

    const canRun = setButtonLoading(button, true, pendingText);
    if (!canRun) {
      return null;
    }

    try {
      const result = await action();
      if (successMessage) {
        core.setStatus(successMessage, forLogin);
      }
      return result;
    } catch (err) {
      if (isAbortError(err)) {
        return null;
      }
      const message = errorMessage(err);
      const prefixAllowed = typeof shouldPrefixError === "function"
        ? shouldPrefixError(message, err) !== false
        : true;
      if (forLogin && typeof core.showLogin === "function") {
        core.showLogin(errorPrefix && prefixAllowed ? `${errorPrefix}: ${message}` : message);
      } else {
        core.setStatus(errorPrefix && prefixAllowed ? `${errorPrefix}: ${message}` : message, forLogin);
      }
      if (rethrow) {
        throw err;
      }
      return null;
    } finally {
      setButtonLoading(button, false);
    }
  }

  Object.assign(core, {
    isAbortError,
    errorMessage,
    dismissToast,
    notify,
    requestJson,
    getUiRequestCache,
    setUiRequestCache,
    invalidateUiRequestCache,
    showConfirm,
    closeConfirm,
    showUndoToast,
    handleUndoClick,
    runDestructiveAction,
    runAction,
  });
})();
