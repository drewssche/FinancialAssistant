(() => {
  function createPlansEditor({ state, el, core, operationModal, plansRecurrence }) {
    const { isWorkdaysOnlyEnabled, isMonthEndModeEnabled, setMonthEndMode, setWorkdaysOnlyMode,
      syncPlanRecurrenceUi, getSelectedPlanWeekdays, setSelectedPlanWeekdays } = plansRecurrence;
    function resetPlanModalState() {
      state.createFlowMode = "plan";
      state.editPlanId = null;
      el.createEntryModeSwitch?.classList.add("hidden");
      el.planRecurrenceBlock?.classList.remove("hidden");
      if (el.opCurrency) {
        el.opCurrency.value = core.getCurrencyConfig?.().code || "BYN";
        el.opCurrency.disabled = false;
        el.opCurrency.title = "";
      }
      if (el.opFxRate) {
        el.opFxRate.value = "1";
      }
      operationModal.resetOperationFxPolicy?.("create");
    }

    function hydrateCreateReceiptItems(items) {
      operationModal.clearReceiptItems?.("create");
      if (typeof operationModal.createReceiptDraft !== "function") {
        state.createReceiptItems = [];
        return;
      }
      state.createReceiptItems = (Array.isArray(items) ? items : []).map((row) => operationModal.createReceiptDraft({
        template_id: row.template_id || null,
        product_id: row.product_id || null,
        product_name: row.product_name || "",
        product_image_id: row.product_image_id || null,
        item_image_id: row.item_image_id || null,
        source_id: row.source_id || null,
        source_image_id: row.source_image_id || null,
        category_id: row.category_id || null,
        brand_id: row.brand_id || null,
        brand_name: row.brand_name || "",
        brand_accent_color: row.brand_accent_color || "",
        brand_image_id: row.brand_image_id || null,
        brand_is_archived: Boolean(row.brand_is_archived),
        shop_name: row.shop_name || "",
        name: row.name || "",
        quantity: row.quantity || 0,
        unit_price: row.unit_price || 0,
        is_discounted: Boolean(row.is_discounted),
        regular_unit_price: row.regular_unit_price || 0,
        note: row.note || "",
      }, "create"));
    }

    async function fillPlanModal(plan = null) {
      clearContext();
      resetPlanModalState();
      const createTitle = document.getElementById("createTitle");
      const submitBtn = document.getElementById("submitCreateOperationBtn");
      if (createTitle) {
        createTitle.textContent = plan?.id ? "Редактировать план" : "Новый план";
      }
      if (submitBtn) {
        setSubmitLabel(plan?.id ? "Сохранить план" : "Создать план");
      }
      core.syncDateFieldValue(document.getElementById("opDate"), plan?.scheduled_date || core.getTodayIso());
      document.getElementById("opAmount").value = plan?.original_amount || plan?.amount || "";
      document.getElementById("opNote").value = plan?.note || "";
      if (el.opCurrency) {
        el.opCurrency.value = plan?.currency || (core.getCurrencyConfig?.().code || "BYN");
      }
      operationModal.setOperationKind("create", plan?.kind || "expense");
      if (plan) {
        operationModal.hydrateOperationFxPolicy?.("create", plan, {
          isPlan: true,
          preserveSnapshot: false,
          applyCurrent: true,
        });
      }
      operationModal.selectCreateCategory?.(plan?.category_id ? Number(plan.category_id) : null);
      hydrateCreateReceiptItems(plan?.receipt_items || []);
      operationModal.setCreateOperationMode(state.createReceiptItems.length ? "receipt" : "common");
      await operationModal.syncOperationCurrencyFields?.("create");
      operationModal.renderReceiptItems?.("create");
      operationModal.renderReceiptSummary?.("create");
      state.editPlanId = plan?.id ? Number(plan.id) : null;
      if (el.planScheduleMode) {
        el.planScheduleMode.value = plan?.recurrence_enabled ? "recurring" : "oneoff";
      }
      if (el.planScheduleModeSwitch) {
        core.syncSegmentedActive(el.planScheduleModeSwitch, "plan-schedule-mode", el.planScheduleMode?.value || "oneoff");
      }
      if (el.planRecurrenceFrequency) {
        el.planRecurrenceFrequency.value = plan?.recurrence_frequency || "monthly";
      }
      if (el.planRecurrenceInterval) {
        el.planRecurrenceInterval.value = String(plan?.recurrence_interval || 1);
      }
      setWorkdaysOnlyMode(Boolean(plan?.recurrence_workdays_only));
      setMonthEndMode(Boolean(plan?.recurrence_month_end));
      setSelectedPlanWeekdays(plan?.recurrence_weekdays || []);
      if (el.planRecurrenceEndDate) {
        core.syncDateFieldValue(el.planRecurrenceEndDate, plan?.recurrence_end_date || "");
      }
      syncPlanRecurrenceUi();
      operationModal.updateCreatePreview?.();
      setContext(plan);
    }

    function getValidatedPlanPayload() {
      if (resumePending) throw new Error("Подождите расчёта следующего платежа");
      if (isResuming() && resumeError) throw new Error(resumeError);
      const scheduledDate = core.parseDateInputValue(document.getElementById(isResuming() ? "planResumeDate" : "opDate").value);
      if (!scheduledDate) {
        throw new Error("Проверь дату плана");
      }
      const receiptItems = operationModal.getCreateReceiptPayload ? operationModal.getCreateReceiptPayload() : [];
      const amount = core.resolveMoneyInput(document.getElementById("opAmount").value);
      const hasReceiptItems = receiptItems.length > 0;
      const canDeriveAmountFromReceipt = hasReceiptItems && amount.empty;
      if (!canDeriveAmountFromReceipt && (!amount.valid || amount.value <= 0)) {
        throw new Error("Проверь сумму плана");
      }
      const recurrenceEnabled = (el.planScheduleMode?.value || "oneoff") === "recurring";
      const recurrenceEndDate = core.parseDateInputValue(el.planRecurrenceEndDate?.value || "");
      return {
        kind: el.opKind.value,
        category_id: el.opCategory.value ? Number(el.opCategory.value) : null,
        amount: canDeriveAmountFromReceipt ? null : amount.formatted,
        currency: String(el.opCurrency?.value || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase(),
        scheduled_date: scheduledDate,
        ...(isResuming() ? { resume: true } : {}),
        note: String(document.getElementById("opNote").value || "").trim() || null,
        receipt_items: receiptItems,
        recurrence_enabled: recurrenceEnabled,
        recurrence_frequency: recurrenceEnabled ? (el.planRecurrenceFrequency?.value || "monthly") : null,
        recurrence_interval: recurrenceEnabled ? Math.max(1, Number(el.planRecurrenceInterval?.value || 1)) : 1,
        recurrence_weekdays: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "weekly" ? getSelectedPlanWeekdays() : [],
        recurrence_workdays_only: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "daily" ? isWorkdaysOnlyEnabled() : false,
        recurrence_month_end: recurrenceEnabled && (el.planRecurrenceFrequency?.value || "monthly") === "monthly" ? isMonthEndModeEnabled() : false,
        recurrence_end_date: recurrenceEnabled ? (recurrenceEndDate || null) : null,
        ...operationModal.getOperationFxPolicyPayload?.("create", { isPlan: true }),
      };
    }

    let contextVersion = 0;
    let loadedPlan = null;
    let previousMode = "oneoff";
    let resumePending = false;
    let resumeError = "";
    let previewController = null;
    let previewGeneration = 0;
    const field = (id) => document.getElementById(id);
    const isCompleted = () => ["confirmed", "skipped"].includes(loadedPlan?.status);
    const isResuming = () => isCompleted() && el.planScheduleMode?.value === "recurring" && field("planResumeEnabled").checked;

    function setSubmitLabel(label) {
      const button = field("submitCreateOperationBtn");
      if (button.dataset.loading === "1") button.dataset.originalText = label;
      else button.textContent = label;
    }

    function clearContext() {
      const hadPlanContext = loadedPlan || resumePending || state.createFlowMode === "plan";
      contextVersion += 1;
      previewGeneration += 1;
      previewController?.abort();
      loadedPlan = null;
      resumePending = false;
      resumeError = "";
      field("planEditorContext")?.classList.add("hidden");
      field("planResumeControls")?.classList.add("hidden");
      field("planResumeEnabled").checked = false;
      field("opDateField")?.classList.remove("hidden");
      if (hadPlanContext) {
        const button = field("submitCreateOperationBtn");
        button.disabled = button.dataset.loading === "1";
        delete button.dataset.originalText;
      }
    }

    function setContext(plan) {
      loadedPlan = plan;
      previousMode = el.planScheduleMode?.value || "oneoff";
      field("planEditorContext").classList.toggle("hidden", !plan?.id);
      if (!plan?.id) return;
      const status = { confirmed: "Завершён", skipped: "Пропущен", overdue: "Просрочен", due: "К подтверждению", upcoming: "Активен" };
      field("planEditorStatus").textContent = `План #${plan.id} · ${status[plan.status] || "Активен"}`;
      field("planCompletedHint").classList.toggle("hidden", !isCompleted());
      field("planLinkedOperation").classList.toggle("hidden", !plan.confirmed_operation_id);
      field("planLinkedOperation").textContent = `Операция #${Number(plan.confirmed_operation_id || 0)}`;
      updateResumeUi();
    }

    function updateResumeUi() {
      const recurring = el.planScheduleMode?.value === "recurring";
      field("planResumeControls").classList.toggle("hidden", !isCompleted() || !recurring);
      field("planResumeFields").classList.toggle("hidden", !isResuming());
      field("opDateField")?.classList.toggle("hidden", isResuming());
      if (loadedPlan?.id) {
        setSubmitLabel(isResuming() ? "Сохранить и возобновить" : "Сохранить план");
      }
    }

    function recurrencePayload() {
      return {
        recurrence_frequency: el.planRecurrenceFrequency.value,
        recurrence_interval: Math.max(1, Number(el.planRecurrenceInterval.value || 1)),
        recurrence_weekdays: getSelectedPlanWeekdays(),
        recurrence_workdays_only: isWorkdaysOnlyEnabled(),
        recurrence_month_end: isMonthEndModeEnabled(),
        recurrence_end_date: core.parseDateInputValue(el.planRecurrenceEndDate.value) || null,
      };
    }

    async function refreshResumeDate({ manual = false } = {}) {
      const generation = ++previewGeneration;
      previewController?.abort();
      resumePending = false;
      resumeError = "";
      field("submitCreateOperationBtn").disabled = false;
      if (!isResuming()) return;
      const payload = recurrencePayload();
      if (manual) {
        payload.scheduled_date = core.parseDateInputValue(field("planResumeDate").value);
        if (!payload.scheduled_date) {
          resumeError = "Укажите дату следующего платежа";
          field("planResumeHint").textContent = resumeError;
          return;
        }
      }
      previewController = new AbortController();
      resumePending = true;
      field("submitCreateOperationBtn").disabled = true;
      field("planResumeHint").textContent = "Проверяем следующую дату…";
      try {
        const result = await core.requestJson(`/api/v1/plans/${loadedPlan.id}/resume-preview`, {
          method: "POST", headers: core.authHeaders(), body: JSON.stringify(payload), signal: previewController.signal,
        });
        if (generation !== previewGeneration || !isResuming()) return;
        core.syncDateFieldValue(field("planResumeDate"), result.scheduled_date);
        field("planResumeHint").textContent = `План вернётся в регулярные после сохранения. Следующий платёж: ${core.formatDateRu(result.scheduled_date)}.`;
      } catch (err) {
        if (generation !== previewGeneration) return;
        resumeError = String(err?.message || err);
        field("planResumeHint").textContent = resumeError;
      } finally {
        if (generation === previewGeneration) {
          resumePending = false;
          field("submitCreateOperationBtn").disabled = false;
        }
      }
    }

    function scheduleChanged() {
      if (!isCompleted()) return;
      const mode = el.planScheduleMode.value;
      if (mode !== previousMode) {
        field("planResumeEnabled").checked = mode === "recurring";
        previousMode = mode;
      }
      core.syncDateFieldValue(field("opDate"), loadedPlan.scheduled_date);
      updateResumeUi();
      void refreshResumeDate();
    }

    el.planRecurrenceBlock.addEventListener("click", (event) => {
      if (event.target.closest("[data-plan-schedule-mode], [data-plan-workdays-only], [data-plan-month-end], [data-plan-weekday]")) scheduleChanged();
    });
    el.planRecurrenceBlock.addEventListener("change", (event) => {
      if (["planRecurrenceFrequency", "planRecurrenceEndDate", "planResumeEnabled"].includes(event.target.id)) scheduleChanged();
    });
    el.planRecurrenceInterval.addEventListener("input", scheduleChanged);
    field("planResumeDate").addEventListener("change", () => { void refreshResumeDate({ manual: true }); });
    field("planLinkedOperation").addEventListener("click", () => {
      const id = loadedPlan?.confirmed_operation_id;
      if (!id) return;
      core.runAction({ errorPrefix: "Ошибка открытия операции", action: () => window.App.getRuntimeModule("operations").openMoneyFlowSource({ sourceKind: "operation", sourceId: id }) });
    });
    field("planShowInList").addEventListener("click", () => {
      const plan = loadedPlan;
      if (!plan) return;
      core.runAction({ errorPrefix: "Ошибка открытия планов", action: async () => {
        const plans = window.App.getRuntimeModule("plans");
        const navigation = window.App.getRuntimeModule("navigation");
        const tab = isCompleted() ? "history" : plan.recurrence_enabled ? "recurring" : "oneoff";
        operationModal.closeCreateModal();
        if (el.plansSearchQ) el.plansSearchQ.value = "";
        await plans.setPlansKindFilter("all");
        await plans.setPlansStatusFilter("all");
        await plans.setPlansHistoryEventFilter("all");
        await plans.setPlansTab(tab);
        await navigation.switchSection("plans");
      } });
    });

    return { fillPlanModal, hydrateCreateReceiptItems, getValidatedPlanPayload, clearContext, isResuming, getContextVersion: () => contextVersion };
  }
  window.App.registerRuntimeModule("plans-editor", createPlansEditor);
})();
