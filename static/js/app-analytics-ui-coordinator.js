(() => {
  window.App = window.App || {};

  function getCore() {
    return window.App.core;
  }

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function runPersistedAction({ errorPrefix, action }) {
    return getCore().runAction({
      errorPrefix,
      action: async () => {
        await action();
        await getSessionFeature().savePreferences?.();
      },
    });
  }

  function applySegmentedSelection({
    currentValue,
    nextValue,
    assignValue,
    syncContainer,
    syncAttr,
    errorPrefix,
    action,
  }) {
    if (currentValue === nextValue) {
      return;
    }
    assignValue(nextValue);
    if (syncContainer && syncAttr) {
      getCore().syncSegmentedActive(syncContainer, syncAttr, nextValue);
    }
    runPersistedAction({
      errorPrefix,
      action,
    });
  }

  const api = {
    runPersistedAction,
    applySegmentedSelection,
  };

  window.App.registerRuntimeModule?.("analytics-ui-coordinator", api);
})();
