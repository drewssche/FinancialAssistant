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
    const header = document.createElement("div");
    header.className = "toast-header";
    const textNode = document.createElement("div");
    textNode.className = "toast-text";
    textNode.textContent = String(message ?? "");
    const closeButton = document.createElement("button");
    closeButton.className = "toast-close";
    closeButton.type = "button";
    closeButton.dataset.toastClose = id;
    closeButton.setAttribute("aria-label", "Закрыть");
    closeButton.textContent = "×";
    header.appendChild(textNode);
    if (type === "success" && Date.now() - Number(state.lastActivityMutationAt || 0) < 2500) {
      const activityButton = document.createElement("button");
      activityButton.className = "toast-activity-btn";
      activityButton.type = "button";
      activityButton.dataset.toastActivity = id;
      activityButton.setAttribute("aria-label", "Открыть последние действия");
      activityButton.title = "Последние действия";
      activityButton.textContent = "◷";
      header.appendChild(activityButton);
    }
    header.appendChild(closeButton);
    const progress = document.createElement("div");
    progress.className = "toast-progress";
    const progressBar = document.createElement("div");
    progressBar.className = "toast-progress-bar";
    progressBar.style.animationDuration = `${durationMs}ms`;
    progress.appendChild(progressBar);
    toast.append(header, progress);

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
    const { skipAuthRecovery = false, timeoutMs = 20000, ...fetchOptions } = options;
    const upstreamSignal = fetchOptions.signal;
    const requestController = new AbortController();
    let timedOut = false;
    const abortFromUpstream = () => requestController.abort(upstreamSignal?.reason);
    if (upstreamSignal?.aborted) {
      abortFromUpstream();
    } else {
      upstreamSignal?.addEventListener?.("abort", abortFromUpstream, { once: true });
    }
    fetchOptions.signal = requestController.signal;
    const normalizedTimeoutMs = Number(timeoutMs);
    const timeoutId = Number.isFinite(normalizedTimeoutMs) && normalizedTimeoutMs > 0
      ? setTimeout(() => {
          timedOut = true;
          requestController.abort();
        }, normalizedTimeoutMs)
      : null;
    let response;
    try {
      response = await fetch(url, fetchOptions);
    } catch (err) {
      if (timedOut) {
        throw new Error(`Сервер не ответил за ${Math.ceil(normalizedTimeoutMs / 1000)} сек.`);
      }
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
    } finally {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
      upstreamSignal?.removeEventListener?.("abort", abortFromUpstream);
    }
    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      if (!skipAuthRecovery && state.token) {
        const recovered = await getSessionFeature().recoverUnauthorized?.();
        if (recovered) {
          return requestJson(url, {
            ...fetchOptions,
            headers: {
              ...(fetchOptions.headers || {}),
              Authorization: `Bearer ${state.token}`,
            },
            skipAuthRecovery: true,
          });
        }
      }
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

    const method = String(fetchOptions.method || "GET").toUpperCase();
    let mutationPath = "";
    try {
      mutationPath = new URL(url, window.location.origin).pathname;
    } catch {
      mutationPath = String(url || "");
    }
    if (
      !["GET", "HEAD", "OPTIONS"].includes(method)
      && /^\/api\/v1\/(operations|categories|plans|debts|currency)(?:\/|$)/.test(mutationPath)
    ) {
      state.lastActivityMutationAt = Date.now();
      document.dispatchEvent(new CustomEvent("app:activity-changed", {
        detail: { method, path: mutationPath },
      }));
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
    const header = document.createElement("div");
    header.className = "toast-header";
    const textNode = document.createElement("div");
    textNode.className = "toast-text";
    textNode.textContent = String(message ?? "");
    const undoButton = document.createElement("button");
    undoButton.className = "btn btn-secondary";
    undoButton.type = "button";
    undoButton.dataset.toastUndo = id;
    undoButton.textContent = "Отменить";
    header.append(textNode, undoButton);
    const progress = document.createElement("div");
    progress.className = "toast-progress";
    const progressBar = document.createElement("div");
    progressBar.className = "toast-progress-bar";
    progressBar.style.animationDuration = `${durationMs}ms`;
    progress.appendChild(progressBar);
    toast.append(header, progress);

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
