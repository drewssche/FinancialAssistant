(() => {
  const { state, el } = window.App;
  let todayTimerId = null;

  function applySectionUi() {
    const sections = [
      { id: "dashboard", node: el.dashboardSection, title: "Дашборд", subtitle: "Доходы, расходы и операции за выбранный период" },
      { id: "operations", node: el.operationsSection, title: "Операции", subtitle: "Полный список операций" },
      { id: "debts", node: el.debtsSection, title: "Долги", subtitle: "Карточки задолженностей и погашения" },
      { id: "categories", node: el.categoriesSection, title: "Категории", subtitle: "Управление категориями доходов и расходов" },
      { id: "item_catalog", node: el.itemCatalogSection, title: "Каталог позиций", subtitle: "Справочник позиций чеков по источникам" },
      { id: "settings", node: el.settingsSection, title: "Настройки", subtitle: "Параметры интерфейса и безопасности" },
    ];

    for (const section of sections) {
      section.node.classList.toggle("hidden", section.id !== state.activeSection);
      const navBtn = el.mainNav.querySelector(`[data-section="${section.id}"]`);
      if (navBtn) {
        navBtn.classList.toggle("active", section.id === state.activeSection);
      }
      if (section.id === state.activeSection) {
        el.sectionTitle.textContent = section.title;
        el.sectionSubtitle.textContent = section.subtitle;
      }
    }

    const showTopActions =
      state.activeSection === "dashboard" ||
      state.activeSection === "operations" ||
      state.activeSection === "debts" ||
      state.activeSection === "categories" ||
      state.activeSection === "item_catalog";
    el.topActions.classList.toggle("hidden", !showTopActions);
    if (
      el.addOperationCta
      && el.batchOperationCta
      && el.addDebtCta
      && el.addCategoryCta
      && el.addGroupCta
      && el.addItemTemplateCta
      && el.addItemSourceCta
    ) {
      const showOps = state.activeSection === "dashboard" || state.activeSection === "operations";
      const showDebts = state.activeSection === "debts";
      const showCategories = state.activeSection === "categories";
      const showItemCatalog = state.activeSection === "item_catalog";
      el.addOperationCta.classList.toggle("hidden", !showOps);
      el.batchOperationCta.classList.toggle("hidden", !showOps);
      el.addDebtCta.classList.toggle("hidden", !showDebts);
      el.addCategoryCta.classList.toggle("hidden", !showCategories);
      el.addGroupCta.classList.toggle("hidden", !showCategories);
      el.addItemTemplateCta.classList.toggle("hidden", !showItemCatalog);
      el.addItemSourceCta.classList.toggle("hidden", !showItemCatalog);
    }
  }

  function renderTodayLabel() {
    const now = new Date();
    const fallbackTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    let timeZone = fallbackTz;

    try {
      timeZone = window.App.core.getPreferenceTimeZone();
      new Intl.DateTimeFormat("ru-RU", { timeZone }).format(now);
    } catch {
      timeZone = fallbackTz;
    }

    try {
      const weekdayFormatter = new Intl.DateTimeFormat("ru-RU", {
        weekday: "long",
        timeZone,
      });
      const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone,
      });
      const weekday = weekdayFormatter.format(now);
      el.todayWeekday.textContent = weekday.charAt(0).toUpperCase() + weekday.slice(1);
      el.todayDate.textContent = dateFormatter.format(now);
    } catch {
      el.todayWeekday.textContent = "Сегодня";
      el.todayDate.textContent = now.toLocaleDateString("ru-RU");
    }

    if (todayTimerId) {
      clearTimeout(todayTimerId);
    }
    const tomorrow = new Date(now);
    tomorrow.setHours(24, 0, 0, 0);
    todayTimerId = setTimeout(renderTodayLabel, Math.max(1000, tomorrow.getTime() - now.getTime()));
  }

  async function switchSection(sectionId) {
    state.activeSection = sectionId;
    applySectionUi();
    if (sectionId === "debts" && window.App.actions.loadDebtsCards) {
      window.App.actions.loadDebtsCards().catch((err) => {
        const message = window.App.core.errorMessage ? window.App.core.errorMessage(err) : String(err);
        window.App.core.setStatus(`Не удалось открыть раздел «Долги»: ${message}`);
      });
    }
    if (sectionId === "item_catalog" && window.App.actions.loadItemCatalog) {
      window.App.actions.loadItemCatalog().catch((err) => {
        const message = window.App.core.errorMessage ? window.App.core.errorMessage(err) : String(err);
        window.App.core.setStatus(`Не удалось открыть раздел «Каталог позиций»: ${message}`);
      });
    }
    await window.App.actions.savePreferences();
  }

  Object.assign(window.App.actions, {
    applySectionUi,
    renderTodayLabel,
    switchSection,
  });
})();
