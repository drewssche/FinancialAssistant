(() => {
  function hiddenBreakdownKeys({ state, level, kind }) {
    const hidden = state.analyticsStructureHidden?.[level]?.[kind];
    return new Set(Array.isArray(hidden) ? hidden.map((item) => String(item)) : []);
  }

  function writeHiddenBreakdownKeys({ state, level, kind, keys }) {
    state.analyticsStructureHidden = state.analyticsStructureHidden || {
      category: { expense: [], income: [], all: [] },
      group: { expense: [], income: [], all: [] },
    };
    state.analyticsStructureHidden[level] = state.analyticsStructureHidden[level] || { expense: [], income: [], all: [] };
    state.analyticsStructureHidden[level][kind] = Array.from(keys);
  }

  function toggleCategoryBreakdownVisibility({
    key,
    activeBreakdown,
    state,
    renderCategoryBreakdown,
    savePreferencesDebounced,
  }) {
    const level = activeBreakdown.level || "category";
    const kind = activeBreakdown.kind || "expense";
    const next = hiddenBreakdownKeys({ state, level, kind });
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    writeHiddenBreakdownKeys({ state, level, kind, keys: next });
    if (activeBreakdown.payload) {
      renderCategoryBreakdown(activeBreakdown.payload, activeBreakdown.formatPct);
    }
    savePreferencesDebounced?.();
  }

  function showAllCategoryBreakdownItems({
    activeBreakdown,
    state,
    renderCategoryBreakdown,
    savePreferencesDebounced,
  }) {
    const level = activeBreakdown.level || state.analyticsBreakdownLevel || "category";
    const kind = activeBreakdown.kind || state.analyticsCategoryKind || "expense";
    writeHiddenBreakdownKeys({ state, level, kind, keys: new Set() });
    if (activeBreakdown.payload) {
      renderCategoryBreakdown(activeBreakdown.payload, activeBreakdown.formatPct);
    }
    savePreferencesDebounced?.();
  }

  const api = {
    hiddenBreakdownKeys,
    writeHiddenBreakdownKeys,
    toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems,
  };

  window.App.registerRuntimeModule?.("analytics-breakdown-visibility-coordinator", api);
})();
