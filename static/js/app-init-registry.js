(() => {
  window.App = window.App || {};

  const bootstrapModules = new Map();
  const featureInitModules = new Map();

  function registerBootstrapModule(name, api) {
    if (!name || !api) {
      return api;
    }
    bootstrapModules.set(name, api);
    return api;
  }

  function getBootstrapModule(name) {
    return bootstrapModules.get(name) || null;
  }

  function registerFeatureInitModule(name, api) {
    if (!name || !api) {
      return api;
    }
    featureInitModules.set(name, api);
    return api;
  }

  function getFeatureInitModule(name) {
    return featureInitModules.get(name) || null;
  }

  window.App.registerBootstrapModule = registerBootstrapModule;
  window.App.getBootstrapModule = getBootstrapModule;
  window.App.registerFeatureInitModule = registerFeatureInitModule;
  window.App.getFeatureInitModule = getFeatureInitModule;
})();
