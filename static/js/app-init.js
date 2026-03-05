(() => {
  const initCore = window.App.initCore;
  const initFeatures = window.App.initFeatures;
  const initStartup = window.App.initStartup;

  initCore.bindCoreInit();
  initFeatures.bindFeatureInit();
  initStartup.startApp();
})();
