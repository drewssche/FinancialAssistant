(() => {
  window.App = window.App || {};

  function getWebApp() {
    return window.Telegram?.WebApp || null;
  }

  function getWebAppVersionParts(webApp) {
    const raw = String(webApp?.version || "").trim();
    const match = raw.match(/^(\d+)(?:\.(\d+))?/);
    if (!match) {
      return null;
    }
    return {
      major: Number(match[1] || 0),
      minor: Number(match[2] || 0),
    };
  }

  function isVersionAtLeast(webApp, major, minor = 0) {
    const parts = getWebAppVersionParts(webApp);
    if (!parts) {
      return false;
    }
    if (parts.major !== major) {
      return parts.major > major;
    }
    return parts.minor >= minor;
  }

  function canUseThemeColorApi(webApp) {
    return Boolean(
      webApp
      && typeof webApp.setHeaderColor === "function"
      && typeof webApp.setBackgroundColor === "function"
      && isVersionAtLeast(webApp, 6, 1),
    );
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
      if (canUseThemeColorApi(webApp)) {
        webApp.setHeaderColor("#0a0f18");
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
