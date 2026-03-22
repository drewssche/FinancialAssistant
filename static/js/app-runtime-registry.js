(() => {
  window.App = window.App || {};

  const runtimeModules = new Map();

  function registerRuntimeModule(name, api) {
    if (!name || !api) {
      return api;
    }
    runtimeModules.set(name, api);
    return api;
  }

  function getRuntimeModule(name) {
    return runtimeModules.get(name) || null;
  }

  window.App.registerRuntimeModule = registerRuntimeModule;
  window.App.getRuntimeModule = getRuntimeModule;
})();
