(() => {
  const { state, el } = window.App;
  let todayTimerId = null;

  function cloneNavigationState() {
    return {
      activeSection: state.activeSection,
      period: state.period,
      customDateFrom: state.customDateFrom,
      customDateTo: state.customDateTo,
      filterKind: state.filterKind,
      operationsQuickView: state.operationsQuickView,
      operationsCategoryFilterId: state.operationsCategoryFilterId,
      operationsCategoryFilterName: state.operationsCategoryFilterName,
      analyticsTab: state.analyticsTab,
      analyticsCalendarView: state.analyticsCalendarView,
      analyticsGlobalPeriod: state.analyticsGlobalPeriod,
      analyticsGlobalDateFrom: state.analyticsGlobalDateFrom,
      analyticsGlobalDateTo: state.analyticsGlobalDateTo,
      analyticsCategoryKind: state.analyticsCategoryKind,
      analyticsGranularity: state.analyticsGranularity,
      analyticsMonthAnchor: state.analyticsMonthAnchor,
      dashboardAnalyticsPeriod: state.dashboardAnalyticsPeriod,
      dashboardAnalyticsDateFrom: state.dashboardAnalyticsDateFrom,
      dashboardAnalyticsDateTo: state.dashboardAnalyticsDateTo,
      dashboardBreakdownLevel: state.dashboardBreakdownLevel,
      dashboardCategoryKind: state.dashboardCategoryKind,
      filterQ: String(el.filterQ?.value || ""),
    };
  }

  function restoreNavigationState(snapshot) {
    if (!snapshot) {
      return;
    }
    state.period = snapshot.period || "day";
    state.customDateFrom = snapshot.customDateFrom || "";
    state.customDateTo = snapshot.customDateTo || "";
    state.filterKind = snapshot.filterKind || "";
    state.operationsQuickView = snapshot.operationsQuickView || "all";
    state.operationsCategoryFilterId = snapshot.operationsCategoryFilterId ?? null;
    state.operationsCategoryFilterName = snapshot.operationsCategoryFilterName || "";
    state.analyticsTab = snapshot.analyticsTab || "calendar";
    state.analyticsCalendarView = snapshot.analyticsCalendarView || "month";
    state.analyticsGlobalPeriod = snapshot.analyticsGlobalPeriod || "month";
    state.analyticsGlobalDateFrom = snapshot.analyticsGlobalDateFrom || "";
    state.analyticsGlobalDateTo = snapshot.analyticsGlobalDateTo || "";
    state.analyticsCategoryKind = snapshot.analyticsCategoryKind || "expense";
    state.analyticsGranularity = snapshot.analyticsGranularity || "day";
    state.analyticsMonthAnchor = snapshot.analyticsMonthAnchor || "";
    state.dashboardAnalyticsPeriod = snapshot.dashboardAnalyticsPeriod || "month";
    state.dashboardAnalyticsDateFrom = snapshot.dashboardAnalyticsDateFrom || "";
    state.dashboardAnalyticsDateTo = snapshot.dashboardAnalyticsDateTo || "";
    state.dashboardBreakdownLevel = snapshot.dashboardBreakdownLevel || "category";
    state.dashboardCategoryKind = snapshot.dashboardCategoryKind || "expense";
    if (el.filterQ) {
      el.filterQ.value = snapshot.filterQ || "";
    }
    window.App.core.syncAllPeriodTabs(state.period);
    window.App.core.syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
    window.App.core.syncSegmentedActive(el.operationsQuickViewTabs, "operations-quick-view", state.operationsQuickView);
    window.App.core.syncSegmentedActive(el.analyticsViewTabs, "analytics-tab", state.analyticsTab);
    window.App.core.syncSegmentedActive(el.analyticsCalendarViewTabs, "analytics-calendar-view", state.analyticsCalendarView);
    window.App.core.syncSegmentedActive(el.analyticsGlobalPeriodTabs, "analytics-global-period", state.analyticsGlobalPeriod);
    window.App.core.syncSegmentedActive(el.analyticsCategoryKindTabs, "analytics-category-kind", state.analyticsCategoryKind);
    window.App.core.syncSegmentedActive(el.analyticsGranularityTabs, "analytics-granularity", state.analyticsGranularity);
    window.App.core.syncSegmentedActive(el.dashboardAnalyticsPeriodTabs, "dashboard-analytics-period", state.dashboardAnalyticsPeriod);
    window.App.core.syncSegmentedActive(el.dashboardBreakdownLevelTabs, "dashboard-breakdown-level", state.dashboardBreakdownLevel);
    window.App.core.syncSegmentedActive(el.dashboardCategoryKindTabs, "dashboard-category-kind", state.dashboardCategoryKind);
  }

  function updateSectionBackUi() {
    if (!el.sectionBackBtn) {
      return;
    }
    const stack = Array.isArray(state.sectionBackStack) ? state.sectionBackStack : [];
    const last = stack[stack.length - 1] || null;
    const isVisible = Boolean(last);
    el.sectionBackBtn.classList.toggle("hidden", !isVisible);
    if (el.sectionBackLabel) {
      const sectionLabelMap = {
        dashboard: "к Дашборду",
        analytics: last?.analyticsTab === "calendar"
          ? "к Календарю"
          : last?.analyticsTab === "structure"
              ? "к Структуре"
              : last?.analyticsTab === "trends"
                  ? "к Трендам"
                  : "к Аналитике",
        operations: "к Операциям",
        plans: "к Планам",
        debts: "к Долгам",
        categories: "к Категориям",
        item_catalog: "к Каталогу",
        settings: "к Настройкам",
        admin: "к Админу",
      };
      el.sectionBackLabel.textContent = isVisible ? (sectionLabelMap[last.activeSection] || "Назад") : "Назад";
    }
  }

  function pushSectionBackContext() {
    state.sectionBackStack = Array.isArray(state.sectionBackStack) ? state.sectionBackStack : [];
    state.sectionBackStack.push(cloneNavigationState());
    if (state.sectionBackStack.length > 12) {
      state.sectionBackStack = state.sectionBackStack.slice(-12);
    }
    updateSectionBackUi();
  }

  async function navigateSectionBack() {
    if (!Array.isArray(state.sectionBackStack) || !state.sectionBackStack.length) {
      return;
    }
    const snapshot = state.sectionBackStack.pop();
    restoreNavigationState(snapshot);
    updateSectionBackUi();
    await switchSection(snapshot.activeSection || "dashboard", { preserveBackStack: true });
  }

  function applySectionUi() {
    const sections = [
      { id: "dashboard", node: el.dashboardSection, title: "Дашборд", subtitle: "Доходы, расходы и операции за выбранный период" },
      { id: "analytics", node: el.analyticsSection, title: "Аналитика", subtitle: "Календарь, тренды и динамика расходов/доходов" },
      { id: "operations", node: el.operationsSection, title: "Операции", subtitle: "Рабочий список операций, фильтры и массовые действия" },
      { id: "plans", node: el.plansSection, title: "Планы", subtitle: "Будущие операции и регулярные обязательства до подтверждения" },
      { id: "debts", node: el.debtsSection, title: "Долги", subtitle: "Карточки задолженностей и погашения" },
      { id: "categories", node: el.categoriesSection, title: "Категории", subtitle: "Управление категориями доходов и расходов" },
      { id: "item_catalog", node: el.itemCatalogSection, title: "Каталог позиций", subtitle: "Справочник позиций чеков по источникам" },
      { id: "admin", node: el.adminSection, title: "Админ", subtitle: "Контроль доступа пользователей" },
      { id: "settings", node: el.settingsSection, title: "Настройки", subtitle: "Параметры интерфейса и безопасности" },
    ];

    if (el.adminNavBtn) {
      el.adminNavBtn.classList.toggle("hidden", !state.isAdmin);
    }
    if (!state.isAdmin && state.activeSection === "admin") {
      state.activeSection = "dashboard";
    }

    for (const section of sections) {
      if (!section.node) {
        continue;
      }
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
    updateSectionBackUi();

    const showTopActions =
      state.activeSection === "dashboard" ||
      state.activeSection === "operations" ||
      state.activeSection === "plans" ||
      state.activeSection === "debts" ||
      state.activeSection === "categories" ||
      state.activeSection === "item_catalog";
    el.topActions.classList.toggle("hidden", !showTopActions);
    if (
      el.addOperationCta
      && el.batchOperationCta
      && el.addPlanCta
      && el.addDebtCta
      && el.addCategoryCta
      && el.addGroupCta
      && el.batchCategoryCta
      && el.addItemTemplateCta
      && el.addItemSourceCta
      && el.batchItemCatalogCta
    ) {
      const showOps = state.activeSection === "dashboard" || state.activeSection === "operations";
      const showPlans = state.activeSection === "plans";
      const showDebts = state.activeSection === "debts";
      const showCategories = state.activeSection === "categories";
      const showItemCatalog = state.activeSection === "item_catalog";
      el.addOperationCta.classList.toggle("hidden", !showOps);
      el.batchOperationCta.classList.toggle("hidden", !showOps);
      el.addPlanCta.classList.toggle("hidden", !showPlans);
      el.addDebtCta.classList.toggle("hidden", !showDebts);
      el.addCategoryCta.classList.toggle("hidden", !showCategories);
      el.addGroupCta.classList.toggle("hidden", !showCategories);
      el.batchCategoryCta.classList.toggle("hidden", !showCategories);
      el.addItemTemplateCta.classList.toggle("hidden", !showItemCatalog);
      el.addItemSourceCta.classList.toggle("hidden", !showItemCatalog);
      el.batchItemCatalogCta.classList.toggle("hidden", !showItemCatalog);
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

  async function switchSection(sectionId, options = {}) {
    const preserveBackStack = options.preserveBackStack === true;
    if (sectionId === "admin" && !state.isAdmin) {
      return;
    }
    if (window.App.core?.closeMobileNav) {
      window.App.core.closeMobileNav();
    }
    if (!preserveBackStack && state.activeSection !== sectionId) {
      state.sectionBackStack = [];
    }
    state.activeSection = sectionId;
    applySectionUi();
    if (sectionId === "dashboard") {
      const jobs = [];
      if (window.App.actions.loadDashboard) {
        jobs.push(window.App.actions.loadDashboard());
      }
      if (window.App.actions.loadDashboardOperations) {
        jobs.push(window.App.actions.loadDashboardOperations());
      }
      if (window.App.actions.loadDashboardAnalyticsPreview) {
        jobs.push(window.App.actions.loadDashboardAnalyticsPreview({ force: true }));
      }
      if (jobs.length) {
        const results = await Promise.allSettled(jobs);
        const hasFailure = results.some((item) => item.status === "rejected");
        if (hasFailure) {
          window.App.core.setStatus("Не удалось полностью обновить дашборд");
        }
      }
    }
    if (sectionId === "operations" && window.App.actions.loadOperations) {
      await window.App.actions.loadOperations({ reset: true });
    }
    if (sectionId === "plans" && window.App.actions.loadPlans) {
      await window.App.actions.loadPlans();
    }
    if (sectionId === "categories" && window.App.actions.loadCategories) {
      window.App.actions.loadCategories().catch((err) => {
        const message = window.App.core.errorMessage ? window.App.core.errorMessage(err) : String(err);
        window.App.core.setStatus(`Не удалось открыть раздел «Категории»: ${message}`);
      });
    }
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
    if (sectionId === "analytics" && window.App.actions.loadAnalyticsSection) {
      window.App.actions.loadAnalyticsSection({ force: true }).catch((err) => {
        const message = window.App.core.errorMessage ? window.App.core.errorMessage(err) : String(err);
        window.App.core.setStatus(`Не удалось открыть раздел «Аналитика»: ${message}`);
      });
    }
    if (sectionId === "admin" && window.App.actions.loadAdminUsers) {
      window.App.actions.loadAdminUsers({ force: true }).catch((err) => {
        const message = window.App.core.errorMessage ? window.App.core.errorMessage(err) : String(err);
        window.App.core.setStatus(`Не удалось открыть раздел «Админ»: ${message}`);
      });
    }
    await window.App.actions.savePreferences();
  }

  Object.assign(window.App.actions, {
    applySectionUi,
    renderTodayLabel,
    switchSection,
    pushSectionBackContext,
    navigateSectionBack,
    updateSectionBackUi,
  });
})();
