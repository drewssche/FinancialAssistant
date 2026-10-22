(() => {
  const { state, el, core } = window.App;
  const dashboardData = window.App.getRuntimeModule?.("dashboard-data") || {};
  const operationModal = window.App.getRuntimeModule?.("operation-modal") || {};

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function getItemCatalogFeature() {
    return window.App.getRuntimeModule?.("item-catalog") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getAnalyticsFeature() {
    return window.App.getRuntimeModule?.("analytics") || {};
  }

  function getPickerUtils() {
    return window.App.getRuntimeModule?.("picker-utils") || {};
  }

  function getLoadingSkeletons() {
    return window.App.getRuntimeModule?.("loading-skeletons") || {};
  }
  const createPlansRecurrenceFeature = window.App.getRuntimeModule?.("plans-recurrence");
  const plansRecurrence = createPlansRecurrenceFeature
    ? createPlansRecurrenceFeature({ el, core })
    : {};
  const syncPlanRecurrenceUi = plansRecurrence.syncPlanRecurrenceUi || (() => {});
  const togglePlanWeekday = plansRecurrence.togglePlanWeekday || (() => {});
  let plansRender = {};
  let plansDashboard = {};

  function getPlansCacheKey() {
    return "plans:list";
  }

  function getPlanItems() {
    return Array.isArray(state.plansItems) ? state.plansItems : [];
  }

  function getPlanHistoryItems() {
    return Array.isArray(state.plansHistoryItems) ? state.plansHistoryItems : [];
  }

  function getCategoryMetaById(categoryId) {
    const id = Number(categoryId || 0);
    if (!id) {
      return null;
    }
    const category = (state.categories || []).find((item) => Number(item.id) === id);
    if (!category) {
      return null;
    }
    return {
      id: category.id,
      name: category.name,
      icon: category.icon || category.group_icon || null,
      accent_color: category.group_accent_color || null,
      kind: category.kind,
      group_name: category.group_name || "",
    };
  }

  function getPlanBaseAmountValue(item) {
    const live = Number(item?.current_base_amount ?? NaN);
    if (Number.isFinite(live)) {
      return live;
    }
    return Number(item?.amount || 0);
  }

  const createPlansRenderFeature = window.App.getRuntimeModule?.("plans-render");
  plansRender = createPlansRenderFeature
    ? createPlansRenderFeature({
      state,
      core,
      getCategoryMetaById,
      getPlanBaseAmountValue,
    })
    : {};
  const renderPlanCard = plansRender.renderPlanCard || (() => "");
  const renderHistoryCard = plansRender.renderHistoryCard || (() => "");

  const createPlansDashboardFeature = window.App.getRuntimeModule?.("plans-dashboard");
  plansDashboard = createPlansDashboardFeature
    ? createPlansDashboardFeature({
      state,
      el,
      core,
      getPickerUtils,
      getPlanItems,
      getSessionFeature,
      summarizePlans,
      renderPlanCard,
      loadPlans,
    })
    : {};
  const renderDashboardPlans = plansDashboard.renderDashboardPlans || (() => {});
  const setDashboardPlansPeriod = plansDashboard.setDashboardPlansPeriod || (async () => {});
  const openDashboardPlansPeriodPopover = plansDashboard.openDashboardPlansPeriodPopover || (() => {});

  function getFilteredPlans() {
    const query = String(el.plansSearchQ?.value || "").trim().toLowerCase();
    const activeTab = state.plansTab || "due";
    const activeKind = state.plansKindFilter || "all";
    const activeStatus = state.plansStatusFilter || "all";
    return getPlanItems().filter((item) => {
      const kindOk = activeKind === "all" || item.kind === activeKind;
      const statusOk = activeStatus === "all" || item.status === activeStatus;
      const tabOk = activeTab === "history"
        ? item.status === "confirmed" || item.status === "skipped"
        : activeTab === "oneoff"
          ? item.recurrence_enabled !== true && item.status !== "confirmed" && item.status !== "skipped"
          : activeTab === "recurring"
            ? item.recurrence_enabled === true && item.status !== "confirmed" && item.status !== "skipped"
            : item.status === "due" || item.status === "overdue" || item.status === "upcoming";
      if (!kindOk || !tabOk || !statusOk) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = [
        item.category_name || "",
        item.note || "",
        item.title || "",
      ].join(" ").toLowerCase();
      return window.App.search.matches(haystack, query);
    }).sort((a, b) => window.App.search.compare(query,
      [a.category_name, a.note, a.title, a.event_type], [b.category_name, b.note, b.title, b.event_type]));
  }

  function getFilteredHistoryItems() {
    const query = String(el.plansSearchQ?.value || "").trim().toLowerCase();
    const activeKind = state.plansKindFilter || "all";
    const activeEventType = state.plansHistoryEventFilter || "all";
    return getPlanHistoryItems().filter((item) => {
      if (activeKind !== "all" && item.kind !== activeKind) {
        return false;
      }
      if (activeEventType !== "all" && item.event_type !== activeEventType) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = [
        item.category_name || "",
        item.note || "",
        item.event_type || "",
      ].join(" ").toLowerCase();
      return window.App.search.matches(haystack, query);
    }).sort((a, b) => window.App.search.compare(query,
      [a.category_name, a.note, a.title, a.event_type], [b.category_name, b.note, b.title, b.event_type]));
  }

  function summarizePlans(items) {
    return items.reduce((acc, item) => {
      const amount = getPlanBaseAmountValue(item);
      acc.activeCount += 1;
      if (item.status === "due" || item.status === "overdue") {
        acc.dueCount += 1;
      }
      if (item.status === "due") {
        acc.todayCount += 1;
      }
      if (item.status === "overdue") {
        acc.overdueCount += 1;
      }
      if (item.status === "upcoming") {
        acc.upcomingCount += 1;
      }
      if (item.kind === "income") {
        acc.potentialIncome += amount;
      } else {
        acc.potentialExpense += amount;
      }
      acc.netPlanned += item.kind === "income" ? amount : -amount;
      return acc;
    }, {
      activeCount: 0,
      dueCount: 0,
      todayCount: 0,
      overdueCount: 0,
      upcomingCount: 0,
      potentialExpense: 0,
      potentialIncome: 0,
      netPlanned: 0,
    });
  }

  let forecastDays = 30;
  let forecastGeneration = 0;
  async function renderForecast() {
    const host = document.getElementById("plansForecast");
    if (!host) return;
    const token = ++forecastGeneration, owner = state.token;
    host.textContent = "Загружаю планы…";
    try {
      const data = await core.requestJson(`/api/v1/plans/forecast?days=${forecastDays}`, { headers: core.authHeaders() });
      if (token !== forecastGeneration || owner !== state.token) return;
      if (data.income_total == null) { host.textContent = "Нет данных прогноза"; return; }
      const netTotal = Number(data.income_total) - Number(data.expense_total);
      const netClass = netTotal > 0 ? "amount-income" : netTotal < 0 ? "amount-expense" : "";
      host.innerHTML = `<article class="analytics-kpi-card analytics-kpi-income"><span class="muted-small">Ожидается получить</span><strong class="amount-income">${core.formatMoney(data.income_total)}</strong></article><article class="analytics-kpi-card analytics-kpi-expense"><span class="muted-small">Ожидается заплатить</span><strong class="amount-expense">${core.formatMoney(data.expense_total)}</strong></article><article class="analytics-kpi-card" data-plans-net title="Ожидается получить минус ожидается заплатить за выбранный период"><span class="muted-small">Итог планов</span><strong class="${netClass}">${core.formatMoney(netTotal)}</strong></article><p class="muted-small">${core.formatDateRu(data.date_from)} — ${core.formatDateRu(data.date_to)} · ${Number(data.occurrences_count)} платежей${data.unpriced_count ? ` · Без курса: ${Number(data.unpriced_count)}, не включены в суммы` : ""}${data.overdue_count ? ` · Просрочено планов: ${Number(data.overdue_count)}` : ""}</p>`;
    } catch (error) {
      if (token === forecastGeneration && owner === state.token) host.textContent = "Не удалось загрузить прогноз";
    }
  }
  document.addEventListener("click", event => {
    const button = event.target.closest("[data-plans-horizon]");
    if (!button) return;
    forecastDays = Number(button.dataset.plansHorizon);
    for (const node of document.querySelectorAll("[data-plans-horizon]")) node.classList.toggle("active", node === button);
    void renderForecast();
  });

  async function renderPlansSection() {
    const isHistoryTab = (state.plansTab || "due") === "history";
    const items = isHistoryTab ? getFilteredHistoryItems() : getFilteredPlans();
    const summary = summarizePlans(getPlanItems().filter(item => !["confirmed", "skipped"].includes(item.status)));
    const labels = { all: `Все сроки · ${summary.activeCount}`, overdue: `Просрочено${summary.overdueCount ? ` · ${summary.overdueCount}` : ""}`, due: `Сегодня${summary.todayCount ? ` · ${summary.todayCount}` : ""}`, upcoming: `Впереди · ${summary.upcomingCount}` };
    el.plansStatusTabs?.querySelectorAll("[data-plan-status]").forEach(button => { button.textContent = labels[button.dataset.planStatus]; });
    document.getElementById("plansKpiGrid")?.classList.toggle("hidden", isHistoryTab);
    if (!isHistoryTab) void renderForecast();
    if (!el.plansList) {
      return;
    }
    el.plansStatusTabs?.classList.toggle("hidden", isHistoryTab);
    el.plansHistoryEventTabs?.classList.toggle("hidden", !isHistoryTab);
    el.plansList.innerHTML = items.length
      ? items.map(isHistoryTab ? renderHistoryCard : renderPlanCard).join("")
      : `<div class='panel muted-small'>${isHistoryTab ? "История по выбранному фильтру пока пуста" : "Планов для выбранного фильтра пока нет"}</div>`;
  }

  const editor = window.App.getRuntimeModule("plans-editor")({ state, el, core, operationModal, plansRecurrence });
  const { fillPlanModal, hydrateCreateReceiptItems, getValidatedPlanPayload } = editor;

  async function refreshAfterPlanMutation({ confirmed = false } = {}) {
    const itemCatalogFeature = getItemCatalogFeature();
    if (itemCatalogFeature.invalidateItemCatalogDependentCaches) {
      itemCatalogFeature.invalidateItemCatalogDependentCaches();
    } else {
      core.invalidateUiRequestCache?.("plans");
      core.invalidateUiRequestCache?.("item-catalog");
      core.invalidateUiRequestCache?.("item-brands");
      core.invalidateUiRequestCache?.("analytics");
      core.invalidateUiRequestCache?.("dashboard:highlights");
      core.invalidateUiRequestCache?.("op:receipt:templates");
      state.receiptTemplateHints = [];
      state.itemBrandsLoaded = false;
    }
    if (confirmed) {

      dashboardData.invalidateSummaryCache?.();
    }
    await loadPlans({ force: true });
    await window.App.getRuntimeModule?.("item-brands")?.loadItemBrands?.({ force: true });
    if (itemCatalogFeature.loadItemCatalog) {
      await itemCatalogFeature.loadItemCatalog({ force: true });
    }
    if (!confirmed) {
      return;
    }
    const jobs = [];
    const operationsFeature = getOperationsFeature();
    const dashboardFeature = getDashboardFeature();
    const analyticsFeature = getAnalyticsFeature();
    if (operationsFeature.loadOperations) {
      jobs.push({ label: "Операции", run: () => operationsFeature.loadOperations({ reset: true }) });
    }
    if (dashboardFeature.loadDashboard) {
      jobs.push({ label: "Дашборд", run: () => dashboardFeature.loadDashboard() });
    }
    if (dashboardFeature.loadDashboardOperations) {
      jobs.push({ label: "Планы на дашборде", run: () => dashboardFeature.loadDashboardOperations() });
    }
    if (analyticsFeature.loadAnalyticsSection) {
      jobs.push({ label: "Аналитика", run: () => analyticsFeature.loadAnalyticsSection({ force: true }) });
    }
    const results = await Promise.allSettled(jobs.map((job) => job.run()));
    const failed = [];
    for (let idx = 0; idx < results.length; idx += 1) {
      if (results[idx].status !== "rejected") {
        continue;
      }
      failed.push(jobs[idx].label);
    }
    if (failed.length > 0) {
      console.warn("Plan confirm post-refresh partial failure", failed);
    }
  }

  async function loadPlans(options = {}) {
    const { force = false } = options;
    const { signal = null } = options;
    if (!force) {
      const cached = core.getUiRequestCache?.(getPlansCacheKey(), 30_000);
      if (cached?.plans?.items) {
        state.plansItems = Array.isArray(cached.plans.items) ? cached.plans.items : [];
        state.plansHistoryItems = Array.isArray(cached.history?.items) ? cached.history.items : [];
        await renderPlansSection();
        renderDashboardPlans();
        state.dashboardPlansHydrated = true;
        state.plansSectionHydrated = true;
        return;
      }
    }
    if (!state.plansSectionHydrated && state.activeSection === "plans") {
      getLoadingSkeletons().renderPlansSectionSkeleton?.();
    }
    if (!state.dashboardPlansHydrated && state.activeSection === "dashboard") {
      getLoadingSkeletons().renderDashboardPlansSkeleton?.();
    }
    let plansData;
    let historyData;
    try {
      [plansData, historyData] = await Promise.all([
        core.requestJson("/api/v1/plans", {
          headers: core.authHeaders(),
          signal,
        }),
        core.requestJson("/api/v1/plans/history", {
          headers: core.authHeaders(),
          signal,
        }),
      ]);
    } catch (err) {
      if (core.isAbortError?.(err)) return;
      if (state.activeSection === "plans" && el.plansList) {
        el.plansList.innerHTML = `<div class="panel-load-state panel-load-state-error" role="alert">
          <span>Не удалось загрузить планы</span>
          <button class="btn btn-secondary btn-xs btn-icon" type="button" data-plans-retry title="Повторить" aria-label="Повторить">${window.App.icons.svg("refresh")}</button>
        </div>`;
      }
      throw err;
    }
    if (signal?.aborted) {
      return;
    }
    state.plansItems = Array.isArray(plansData.items) ? plansData.items : [];
    state.plansHistoryItems = Array.isArray(historyData.items) ? historyData.items : [];
    core.setUiRequestCache?.(getPlansCacheKey(), { plans: plansData, history: historyData });
    await renderPlansSection();
    renderDashboardPlans();
    state.dashboardPlansHydrated = true;
    state.plansSectionHydrated = true;
  }

  async function setPlansTab(value) {
    state.plansTab = value || "due";
    core.syncSegmentedActive(el.plansTabTabs, "plan-tab", state.plansTab);
    await renderPlansSection();
  }

  async function setPlansKindFilter(value) {
    state.plansKindFilter = value || "all";
    core.syncSegmentedActive(el.plansKindTabs, "plan-kind", state.plansKindFilter);
    await renderPlansSection();
  }

  async function setPlansStatusFilter(value) {
    state.plansStatusFilter = value || "all";
    core.syncSegmentedActive(el.plansStatusTabs, "plan-status", state.plansStatusFilter);
    await renderPlansSection();
    getSessionFeature().savePreferencesDebounced?.(250);
  }

  async function setPlansHistoryEventFilter(value) {
    state.plansHistoryEventFilter = value || "all";
    core.syncSegmentedActive(el.plansHistoryEventTabs, "plan-history-event", state.plansHistoryEventFilter);
    await renderPlansSection();
    getSessionFeature().savePreferencesDebounced?.(250);
  }

  function applyPlansSearch() {
    renderPlansSection().catch((err) => core.setStatus(String(err)));
  }

  async function openCreatePlan() {
    await operationModal.openCreateModal();
    await fillPlanModal(null);
    operationModal.setCreateModalActivity?.(null, null);
  }

  async function openCreatePlanWithReceiptItem(item = {}) {
    await openCreatePlan();
    hydrateCreateReceiptItems([{
      template_id: item.template_id || item.id || null,
      category_id: item.category_id || null,
      brand_id: item.brand_id || null,
      brand_name: item.brand_name || "",
      brand_accent_color: item.brand_accent_color || "",
      brand_is_archived: Boolean(item.brand_is_archived),
      shop_name: item.shop_name || "",
      name: item.name || "",
      quantity: item.base_quantity || item.quantity || 1,
      unit_price: item.latest_unit_price || item.unit_price || 0,
    }]);
    operationModal.setCreateOperationMode("receipt");
    const scheduledDate = item.effective_date || item.next_date || core.getTodayIso();
    core.syncDateFieldValue(document.getElementById("opDate"), scheduledDate < core.getTodayIso() ? core.getTodayIso() : scheduledDate);
    operationModal.renderReceiptItems?.("create");
    operationModal.renderReceiptSummary?.("create");
    operationModal.updateCreatePreview?.();
  }

  let planOpenGeneration = 0;
  async function openPlanEdit(planId) {
    const generation = ++planOpenGeneration;
    const item = await core.requestJson(`/api/v1/plans/${Number(planId)}`, {
      headers: core.authHeaders(),
    });
    if (generation !== planOpenGeneration) return;
    await operationModal.openCreateModal();
    if (generation !== planOpenGeneration) return;
    await fillPlanModal(item);
    operationModal.setCreateModalActivity?.("plan", item.id);
  }

  async function submitPlanForm(event) {
    event.preventDefault();
    const payload = getValidatedPlanPayload();
    const editorVersion = editor.getContextVersion();
    const planId = Number(state.editPlanId || 0);
    const method = planId > 0 ? "PATCH" : "POST";
    const url = planId > 0 ? `/api/v1/plans/${planId}` : "/api/v1/plans";
    const saved = await window.App.receiptCodes.saveRequest(url, {
      method,
      headers: core.authHeaders(),
      body: JSON.stringify(payload),
    }, "create", payload.receipt_items);
    if (editor.getContextVersion() === editorVersion) {
      if (planId <= 0) {
        operationModal.closeCreateModal();
      } else {
        await fillPlanModal(saved);
        operationModal.setCreateModalActivity?.("plan", saved.id);
      }
    }
    await refreshAfterPlanMutation();
  }

  function findPlanById(planId) {
    return getPlanItems().find((item) => Number(item.id) === Number(planId)) || null;
  }

  async function handlePlanAction(action, planId) {
    const item = findPlanById(planId);
    if (!item) {
      throw new Error("План не найден");
    }
    if (action === "edit") {
      await operationModal.openCreateModal();
      await fillPlanModal(item);
      operationModal.setCreateModalActivity?.("plan", item.id);
      return;
    }
    if (action === "confirm") {
      await core.requestJson(`/api/v1/plans/${planId}/confirm`, {
        method: "POST",
        headers: core.authHeaders(),
      });
      await refreshAfterPlanMutation({ confirmed: true });
      return;
    }
    if (action === "skip") {
      await core.requestJson(`/api/v1/plans/${planId}/skip`, {
        method: "POST",
        headers: core.authHeaders(),
      });
      await refreshAfterPlanMutation();
      return;
    }
    if (action === "delete") {
      core.runDestructiveAction({
        confirmMessage: "Удалить план?",
        doDelete: async () => {
          await core.requestJson(`/api/v1/plans/${planId}`, {
            method: "DELETE",
            headers: core.authHeaders(),
          });
        },
        onAfterDelete: async () => {
          await refreshAfterPlanMutation();
        },
        onDeleteError: "Не удалось удалить план",
      });
    }
  }

  function handlePlanActionClick(event) {
    if (event.__planActionHandled) {
      return;
    }
    const menuTrigger = event.target.closest("button[data-plan-menu-trigger]");
    if (menuTrigger) {
      const planId = String(menuTrigger.dataset.planMenuTrigger || "");
      const menu = document.querySelector(`.plan-card-actions-popover[data-plan-menu="${planId}"]`);
      const card = menuTrigger.closest(".plan-card");
      const pickerUtils = getPickerUtils();
      if (menu && pickerUtils?.setPopoverOpen) {
        const owners = [menuTrigger, menuTrigger.parentElement].filter(Boolean);
        const clearOpenState = () => {
          card?.classList.remove("plan-card-menu-open");
        };
        const shouldOpen = menu.classList.contains("hidden");
        document.querySelectorAll(".plan-card.plan-card-menu-open").forEach((node) => {
          if (node !== card) {
            node.classList.remove("plan-card-menu-open");
          }
        });
        document.querySelectorAll(".plan-card-actions-popover:not(.hidden)").forEach((node) => {
          if (node !== menu) {
            pickerUtils.setPopoverOpen(node, false, {
              owners: Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : [],
            });
            (Array.isArray(node.__appPopoverOwners) ? node.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
          }
        });
        pickerUtils.setPopoverOpen(menu, shouldOpen, { owners, onClose: clearOpenState });
        if (card) {
          card.classList.toggle("plan-card-menu-open", shouldOpen);
        }
        if (!shouldOpen) {
          clearOpenState();
          menuTrigger.blur?.();
        }
      }
      return;
    }
    const receiptBtn = event.target.closest("button[data-plan-receipt-view-id]");
    if (receiptBtn) {
      const item = findPlanById(Number(receiptBtn.dataset.planReceiptViewId || 0));
      const operationsFeature = getOperationsFeature();
      if (item?.id && operationsFeature.openOperationReceiptModal) {
        operationsFeature.openOperationReceiptModal({
          ...item,
          operation_date: item.due_date || item.operation_date || core.getTodayIso(),
        });
      }
      return;
    }
    const openPlanBtn = event.target.closest("button[data-open-plan-id]");
    if (openPlanBtn) {
      openPlanEdit(Number(openPlanBtn.dataset.openPlanId)).catch((err) => core.setStatus(String(err)));
      return;
    }
    const historyOperationBtn = event.target.closest("button[data-plan-history-operation-id]");
    if (historyOperationBtn) {
      getOperationsFeature().openMoneyFlowSource?.({
        sourceKind: "operation",
        sourceId: Number(historyOperationBtn.dataset.planHistoryOperationId || 0),
      }).catch((err) => core.setStatus(String(err)));
      return;
    }
    const btn = event.target.closest("button[data-plan-action]");
    if (!btn) {
      const card = event.target.closest("article[data-plan-card-edit-id]");
      if (!card) {
        return;
      }
      const clickedInteractive = event.target.closest("button, a, input, select, textarea, label, .app-popover");
      if (clickedInteractive) {
        return;
      }
      const planId = Number(card.dataset.planCardEditId || 0);
      if (planId) {
        handlePlanAction("edit", planId).catch((err) => core.setStatus(String(err)));
      }
      return;
    }
    const menu = btn.closest(".plan-card-actions-popover");
    const pickerUtils = getPickerUtils();
    if (menu && pickerUtils?.setPopoverOpen) {
      const onClose = typeof menu.__appPopoverOnClose === "function" ? menu.__appPopoverOnClose : null;
      pickerUtils.setPopoverOpen(menu, false, {
        owners: Array.isArray(menu.__appPopoverOwners) ? menu.__appPopoverOwners : [],
      });
      (Array.isArray(menu.__appPopoverOwners) ? menu.__appPopoverOwners : []).forEach((owner) => owner?.blur?.());
      if (onClose) {
        onClose();
      } else {
        menu.closest(".plan-card")?.classList.remove("plan-card-menu-open");
      }
    }
    const action = btn.dataset.planAction || "";
    const planId = Number(btn.dataset.planId || 0);
    if (!planId || !action) {
      return;
    }
    event.__planActionHandled = true;
    const meta = {
      confirm: { pendingText: "Подтверждение...", successMessage: "План подтвержден" },
      skip: { pendingText: "Обновление...", successMessage: "План обновлен" },
    }[action];
    if (!meta) {
      handlePlanAction(action, planId).catch((err) => core.setStatus(String(err)));
      return;
    }
    core.runAction({
      button: btn,
      pendingText: meta.pendingText,
      successMessage: meta.successMessage,
      errorPrefix: "Ошибка работы с планом",
      action: () => handlePlanAction(action, planId),
    });
  }

  plansDashboard.bindDashboardPlansPeriodOptions?.();

  const api = {
    loadPlans,
    renderPlansSection,
    renderDashboardPlans,
    renderPlanCardMarkup: renderPlanCard,
    setPlansTab,
    setPlansKindFilter,
    setPlansStatusFilter,
    setPlansHistoryEventFilter,
    setDashboardPlansPeriod,
    openDashboardPlansPeriodPopover,
    applyPlansSearch,
    openCreatePlan,
    openCreatePlanWithReceiptItem,
    openPlanEdit,
    resetEditorContext: editor.clearContext,
    isResumingPlan: editor.isResuming,
    submitPlanForm,
    handlePlanActionClick,
    syncPlanRecurrenceUi,
    togglePlanWeekday,
  };

  window.App.registerRuntimeModule?.("plans", api);

  document.addEventListener("keydown", (event) => {
    const card = event.target.closest?.("article[data-plan-card-edit-id]");
    if (!card) {
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    const planId = Number(card.dataset.planCardEditId || 0);
    if (planId) {
      handlePlanAction("edit", planId).catch((err) => core.setStatus(String(err)));
    }
  });

  document.addEventListener("click", (event) => {
    const btn = event.target.closest?.(".plan-card-actions-popover button[data-plan-action]");
    if (!btn) {
      return;
    }
    handlePlanActionClick(event);
  });
})();
