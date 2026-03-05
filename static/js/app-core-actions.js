(() => {
  const { state, el, core } = window.App;

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
      throw new Error(data.detail || "Ошибка запроса");
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
    toast.className = "toast";
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

    clearTimeout(item.timeoutId);
    item.toast.remove();
    state.toasts.delete(toastId);

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
    requestJson,
    showConfirm,
    closeConfirm,
    showUndoToast,
    handleUndoClick,
    runDestructiveAction,
    runAction,
  });
})();
