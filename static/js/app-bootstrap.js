(() => {
  const manifest = Array.isArray(window.__APP_SCRIPT_MANIFEST__) ? window.__APP_SCRIPT_MANIFEST__ : [];
  const assetVersion = "20260907a";

  function showBootstrapError(message) {
    const text = String(message || "Не удалось загрузить приложение.");
    document.getElementById("loginLoading")?.classList.add("hidden");
    document.getElementById("loginContent")?.classList.remove("hidden");
    const loginAlert = document.getElementById("loginAlert");
    if (loginAlert) {
      loginAlert.textContent = text;
      loginAlert.classList.remove("hidden", "is-success", "is-info");
      loginAlert.classList.add("is-error");
      return;
    }
    throw new Error(text);
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `${src}${src.includes("?") ? "&" : "?"}v=${assetVersion}`;
      script.async = false;
      script.onload = resolve;
      script.onerror = () => reject(new Error(`Не удалось загрузить скрипт: ${src}`));
      document.body.appendChild(script);
    });
  }

  async function bootstrapApp() {
    if (!manifest.length) {
      showBootstrapError("Не найден manifest фронтенд-скриптов.");
      return;
    }

    await Promise.all(manifest.map((src) => loadScript(src)));
  }

  bootstrapApp().catch((error) => {
    console.error(error);
    showBootstrapError(error instanceof Error ? error.message : String(error));
  });
})();
