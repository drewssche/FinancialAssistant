(() => {
  window.App = window.App || {};

  function getWebApp() {
    return window.Telegram?.WebApp || null;
  }

  function setViewportVars(webApp) {
    const root = document.documentElement;
    const viewportHeight = Number(webApp?.viewportHeight || window.innerHeight || 0);
    const stableHeight = Number(webApp?.viewportStableHeight || viewportHeight || 0);
    root.style.setProperty("--tg-viewport-height", `${viewportHeight}px`);
    root.style.setProperty("--tg-viewport-stable-height", `${stableHeight}px`);
    root.style.setProperty("--tg-safe-top", "env(safe-area-inset-top)");
    root.style.setProperty("--tg-safe-bottom", "env(safe-area-inset-bottom)");
    document.body.classList.toggle("tg-webapp", Boolean(webApp));
  }

  function init() {
    const webApp = getWebApp();
    if (!webApp || window.App.state?.telegramWebAppReady) {
      setViewportVars(webApp);
      return Boolean(webApp);
    }
    window.App.state.telegramWebAppAvailable = true;
    window.App.state.telegramWebAppReady = true;
    setViewportVars(webApp);
    try {
      webApp.ready();
      webApp.expand();
      if (webApp.setHeaderColor) {
        webApp.setHeaderColor("#0a0f18");
      }
      if (webApp.setBackgroundColor) {
        webApp.setBackgroundColor("#080b12");
      }
    } catch {}
    webApp.onEvent?.("viewportChanged", () => {
      setViewportVars(webApp);
    });
    return true;
  }

  window.addEventListener("resize", () => {
    setViewportVars(getWebApp());
  });

  window.App.telegramWebApp = {
    init,
    setViewportVars,
  };
})();
