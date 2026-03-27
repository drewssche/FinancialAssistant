(() => {
  function begin(panel, label = "Обновляется") {
    if (!panel) {
      return;
    }
    const current = Number(panel.dataset.inlineRefreshCount || 0);
    panel.dataset.inlineRefreshCount = String(current + 1);
    panel.dataset.inlineRefreshLabel = String(label || "Обновляется");
    panel.classList.add("panel-inline-refresh");
  }

  function end(panel) {
    if (!panel) {
      return;
    }
    const current = Number(panel.dataset.inlineRefreshCount || 0);
    const next = Math.max(0, current - 1);
    if (next > 0) {
      panel.dataset.inlineRefreshCount = String(next);
      return;
    }
    delete panel.dataset.inlineRefreshCount;
    delete panel.dataset.inlineRefreshLabel;
    panel.classList.remove("panel-inline-refresh");
  }

  async function withRefresh(panel, task, label = "Обновляется") {
    begin(panel, label);
    try {
      return await task();
    } finally {
      end(panel);
    }
  }

  const api = {
    begin,
    end,
    withRefresh,
  };

  window.App.registerRuntimeModule?.("inline-refresh-state", api);
})();
