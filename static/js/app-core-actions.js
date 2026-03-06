(() => {
  const { state, el, core } = window.App;

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
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      if (window.App?.actions?.logout) {
        window.App.actions.logout(false);
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

    return data;
  }

  function showConfirm(message, onConfirm) {
    el.confirmText.textContent = message;
    state.pendingConfirm = onConfirm;
    el.confirmModal.classList.remove("hidden");
  }

  function closeConfirm() {
    state.pendingConfirm = null;
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
      const message = err instanceof Error ? err.message : String(err);
      core.setStatus(errorPrefix ? `${errorPrefix}: ${message}` : message, forLogin);
      if (rethrow) {
        throw err;
      }
      return null;
    } finally {
      setButtonLoading(button, false);
    }
  }

  Object.assign(core, {
    dismissToast,
    notify,
    requestJson,
    showConfirm,
    closeConfirm,
    showUndoToast,
    handleUndoClick,
    runDestructiveAction,
    runAction,
  });
})();
