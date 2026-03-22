(() => {
  const initCore = window.App.getBootstrapModule?.("core") || window.App.initCore;
  const initFeatures = window.App.getBootstrapModule?.("features") || window.App.initFeatures;
  const initStartup = window.App.getBootstrapModule?.("startup") || window.App.initStartup;

  initCore.bindCoreInit();
  initFeatures.bindFeatureInit();
  initStartup.startApp();
})();
