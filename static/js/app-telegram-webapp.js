(() => {
  window.App = window.App || {};

  let backButtonHandler = null;
  let mainButtonHandler = null;
  let observer = null;

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

  function getVisibleModalAction() {
    const { el, actions } = window.App;
    const modalClosers = [
      [el?.createModal, actions?.closeCreateModal],
      [el?.editModal, actions?.closeEditModal],
      [el?.batchCreateModal, actions?.closeBatchCreateModal],
      [el?.bulkEditOperationsModal, actions?.closeBulkEditOperationsModal],
      [el?.createCategoryModal, actions?.closeCreateCategoryModal],
      [el?.createGroupModal, actions?.closeCreateGroupModal],
      [el?.editCategoryModal, actions?.closeEditCategoryModal],
      [el?.editGroupModal, actions?.closeEditGroupModal],
      [el?.periodCustomModal, actions?.closePeriodCustomModal],
      [el?.debtRepaymentModal, actions?.closeDebtRepaymentModal],
      [el?.debtHistoryModal, actions?.closeDebtHistoryModal],
      [el?.operationReceiptModal, actions?.closeOperationReceiptModal],
      [el?.itemTemplateModal, actions?.closeItemTemplateModal],
      [el?.sourceGroupModal, actions?.closeSourceGroupModal],
      [el?.itemTemplateHistoryModal, actions?.closeItemTemplateHistoryModal],
      [el?.confirmModal, actions?.closeConfirmModal],
    ];
    return modalClosers.find(([node, close]) => node && !node.classList.contains("hidden") && typeof close === "function") || null;
  }

  function getMainButtonTarget() {
    if (getVisibleModalAction()) {
      return null;
    }
    return null;
  }

  function syncBackButton() {
    const webApp = getWebApp();
    if (!webApp?.BackButton) {
      return;
    }
    const { core, state } = window.App;
    const hasModal = Boolean(getVisibleModalAction());
    const shouldShow = Boolean(state?.mobileNavOpen) || hasModal || state?.activeSection !== "dashboard";
    if (shouldShow) {
      webApp.BackButton.show();
    } else {
      webApp.BackButton.hide();
    }
    if (backButtonHandler) {
      webApp.BackButton.offClick(backButtonHandler);
    }
    backButtonHandler = async () => {
      if (core?.closeMobileNav && state?.mobileNavOpen) {
        core.closeMobileNav();
        syncBackButton();
        return;
      }
      const modalAction = getVisibleModalAction();
      if (modalAction) {
        modalAction[1]();
        syncBackButton();
        syncMainButton();
        return;
      }
      if (state?.activeSection && state.activeSection !== "dashboard" && window.App.actions?.switchSection) {
        await window.App.actions.switchSection("dashboard");
        syncBackButton();
      }
    };
    webApp.BackButton.onClick(backButtonHandler);
  }

  function syncMainButton() {
    const webApp = getWebApp();
    if (!webApp?.MainButton) {
      return;
    }
    const target = getMainButtonTarget();
    if (mainButtonHandler) {
      webApp.MainButton.offClick(mainButtonHandler);
      mainButtonHandler = null;
    }
    if (!target || !window.App.core?.isMobileViewport()) {
      webApp.MainButton.hide();
      return;
    }
    webApp.MainButton.setParams({
      is_visible: true,
      text: String(target.textContent || "Сохранить").trim(),
      color: "#ff8f34",
      text_color: "#1e1304",
      is_active: !target.disabled,
    });
    mainButtonHandler = () => target.click();
    webApp.MainButton.onClick(mainButtonHandler);
    webApp.MainButton.show();
  }

  function bindObservers() {
    if (observer || !window.App.el?.appShell) {
      return;
    }
    observer = new MutationObserver(() => {
      syncBackButton();
      syncMainButton();
    });
    observer.observe(window.App.el.appShell, { attributes: true, attributeFilter: ["class"] });
    const modalIds = [
      "createModal",
      "editModal",
      "batchCreateModal",
      "bulkEditOperationsModal",
      "createCategoryModal",
      "createGroupModal",
      "editCategoryModal",
      "editGroupModal",
      "periodCustomModal",
      "debtRepaymentModal",
      "debtHistoryModal",
      "operationReceiptModal",
      "itemTemplateModal",
      "sourceGroupModal",
      "itemTemplateHistoryModal",
      "confirmModal",
      "dashboardSection",
      "analyticsSection",
      "operationsSection",
      "debtsSection",
      "categoriesSection",
      "itemCatalogSection",
      "settingsSection",
      "adminSection",
    ];
    for (const id of modalIds) {
      const node = document.getElementById(id);
      if (node) {
        observer.observe(node, { attributes: true, attributeFilter: ["class"] });
      }
    }
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
      syncBackButton();
      syncMainButton();
    });
    bindObservers();
    syncBackButton();
    syncMainButton();
    return true;
  }

  window.addEventListener("resize", () => {
    const webApp = getWebApp();
    setViewportVars(webApp);
    syncMainButton();
  });

  window.App.telegramWebApp = {
    init,
    syncBackButton,
    syncMainButton,
    setViewportVars,
  };
})();
