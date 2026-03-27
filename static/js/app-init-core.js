(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let compactViewportQuery = null;

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

  function getCategoryActions() {
    return window.App.getRuntimeModule?.("category-actions") || {};
  }

  function getDashboardFeature() {
    return window.App.getRuntimeModule?.("dashboard") || {};
  }

  function getAnalyticsFeature() {
    return window.App.getRuntimeModule?.("analytics") || {};
  }

  function getOperationsFeature() {
    return window.App.getRuntimeModule?.("operations") || {};
  }

  function getPlansFeature() {
    return window.App.getRuntimeModule?.("plans") || {};
  }

  function getItemCatalogFeature() {
    return window.App.getRuntimeModule?.("item-catalog") || {};
  }

  function getOperationModal() {
    return window.App.getRuntimeModule?.("operation-modal") || {};
  }

  function getPickerUtils() {
    return window.App.getRuntimeModule?.("picker-utils");
  }

  function isCompactMobileViewport() {
    return window.matchMedia("(max-width: 640px)").matches;
  }

  function rerenderActiveSectionForViewportMode() {
    switch (state.activeSection) {
      case "operations":
        getOperationsFeature().refreshOperationsView?.();
        break;
      case "categories":
        getCategoryActions().renderCategories?.();
        break;
      case "item_catalog":
        getItemCatalogFeature().refreshItemCatalogView?.();
        break;
      case "debts":
        actions.renderDebtCards?.(state.debtCardsCache || []);
        break;
      default:
        break;
    }
  }

  function handleCompactViewportModeChange() {
    const nextValue = isCompactMobileViewport();
    if (state.isCompactMobileViewport === nextValue) {
      return;
    }
    state.isCompactMobileViewport = nextValue;
    rerenderActiveSectionForViewportMode();
  }

  function bindCoreHandlers() {
    if (el.mobileNavToggleBtn) {
      el.mobileNavToggleBtn.addEventListener("click", () => core.toggleMobileNav());
    }
    if (el.mobileNavCloseBtn) {
      el.mobileNavCloseBtn.addEventListener("click", () => core.closeMobileNav());
    }
    if (el.mobileNavOverlay) {
      el.mobileNavOverlay.addEventListener("click", () => core.closeMobileNav());
    }
    if (el.sectionBackBtn && actions.navigateSectionBack) {
      el.sectionBackBtn.addEventListener("click", () => {
        actions.navigateSectionBack().catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.telegramLoginBtn && getSessionFeature().telegramLogin) {
      el.telegramLoginBtn.addEventListener("click", () => {
        const sessionFeature = getSessionFeature();
        core.runAction({
          button: el.telegramLoginBtn,
          pendingText: "Вход...",
          errorPrefix: "Ошибка входа",
          shouldPrefixError: (message) => !(
            message === "Заявка отправлена. Ожидайте одобрения администратора"
            || message === "Доступ отклонен администратором"
          ),
          forLogin: true,
          action: () => sessionFeature.telegramLogin?.(),
        });
      });
    }

    el.mainNav.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-section]");
      if (!btn) {
        return;
      }
      core.closeMobileNav();
      actions.switchSection(btn.dataset.section).catch((err) => core.setStatus(String(err)));
    });

    if (el.openOperationsTabBtn) {
      el.openOperationsTabBtn.addEventListener("click", () => {
        actions.switchSection("operations").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.openPlansTabBtn) {
      el.openPlansTabBtn.addEventListener("click", () => {
        actions.switchSection("plans").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.openDebtsTabBtn) {
      el.openDebtsTabBtn.addEventListener("click", () => {
        actions.switchSection("debts").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.openAnalyticsTabBtn) {
      el.openAnalyticsTabBtn.addEventListener("click", () => {
        getAnalyticsFeature().setAnalyticsTab?.("structure");
        actions.switchSection("analytics").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.openCurrencyTabBtn) {
      el.openCurrencyTabBtn.addEventListener("click", () => {
        actions.switchSection("currency").catch((err) => core.setStatus(String(err)));
      });
    }

    if (el.sidebarLogoutBtn) {
      el.sidebarLogoutBtn.addEventListener("click", () => getSessionFeature().logout?.(true));
    }

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".icon-select") && !event.target.closest(".color-select") && getCategoryActions().closeIconPopovers) {
        getCategoryActions().closeIconPopovers();
      }
      const pickerUtils = getPickerUtils();
      if (pickerUtils?.closeOpenPopoversOnOutside) {
        pickerUtils.closeOpenPopoversOnOutside(event);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        core.closeMobileNav();
      }
    });

    window.addEventListener("resize", () => {
      if (!core.isMobileViewport()) {
        core.closeMobileNav();
      }
    });

    compactViewportQuery = window.matchMedia("(max-width: 640px)");
    state.isCompactMobileViewport = compactViewportQuery.matches;
    compactViewportQuery.addEventListener("change", handleCompactViewportModeChange);
  }

  function bindModalHandlers() {
    el.addOperationCta.addEventListener("click", () => getOperationModal().openCreateModal?.());
    if (el.addPlanCta && getPlansFeature().openCreatePlan) {
      el.addPlanCta.addEventListener("click", () => getPlansFeature().openCreatePlan?.());
    }
    if (el.addDebtCta) {
      el.addDebtCta.addEventListener("click", () => {
        const operationModal = getOperationModal();
        operationModal.openCreateModal?.();
        operationModal.setCreateEntryMode?.("debt");
      });
    }
    if (el.addItemTemplateCta && getItemCatalogFeature().openItemTemplateModal) {
      el.addItemTemplateCta.addEventListener("click", () => {
        getItemCatalogFeature().openItemTemplateModal?.();
      });
    }
    if (el.addItemSourceCta && getItemCatalogFeature().openSourceGroupModal) {
      el.addItemSourceCta.addEventListener("click", () => {
        getItemCatalogFeature().openSourceGroupModal?.();
      });
    }
    el.batchOperationCta.addEventListener("click", () => {
      if (actions.openBatchCreateModal) {
        actions.openBatchCreateModal();
      }
    });
    if (el.batchCategoryCta && actions.openBatchCategoryModal) {
      el.batchCategoryCta.addEventListener("click", () => {
        actions.openBatchCategoryModal();
      });
    }
    if (el.batchItemCatalogCta && actions.openBatchItemTemplateModal) {
      el.batchItemCatalogCta.addEventListener("click", () => {
        actions.openBatchItemTemplateModal();
      });
    }

    el.closeCreateModalBtn.addEventListener("click", () => getOperationModal().closeCreateModal?.());
    el.createModal.addEventListener("click", (event) => {
      if (event.target === el.createModal) {
        getOperationModal().closeCreateModal?.();
      }
    });

    el.closeEditModalBtn.addEventListener("click", () => getOperationModal().closeEditModal?.());
    el.editModal.addEventListener("click", (event) => {
      if (event.target === el.editModal) {
        getOperationModal().closeEditModal?.();
      }
    });

    el.addCategoryCta.addEventListener("click", () => getCategoryActions().openCreateCategoryModal?.());
    el.addGroupCta.addEventListener("click", () => {
      if (actions.openCreateGroupModal) {
        actions.openCreateGroupModal();
      }
    });
    el.closeCreateCategoryModalBtn.addEventListener("click", () => getCategoryActions().closeCreateCategoryModal?.());
    el.createCategoryModal.addEventListener("click", (event) => {
      if (event.target === el.createCategoryModal) {
        getCategoryActions().closeCreateCategoryModal?.();
      }
    });
    el.categoryIconToggle.addEventListener("click", () => {
      el.categoryIconPopover.classList.toggle("hidden");
      el.editCategoryIconPopover.classList.add("hidden");
    });

    el.closeEditCategoryModalBtn.addEventListener("click", () => getCategoryActions().closeEditCategoryModal?.());
    el.editCategoryModal.addEventListener("click", (event) => {
      if (event.target === el.editCategoryModal) {
        getCategoryActions().closeEditCategoryModal?.();
      }
    });
    el.editCategoryIconToggle.addEventListener("click", () => {
      el.editCategoryIconPopover.classList.toggle("hidden");
      el.categoryIconPopover.classList.add("hidden");
    });

    el.closeEditGroupModalBtn.addEventListener("click", () => {
      if (getCategoryActions().closeEditGroupModal) {
        getCategoryActions().closeEditGroupModal();
      }
    });
    el.editGroupModal.addEventListener("click", (event) => {
      if (event.target === el.editGroupModal && getCategoryActions().closeEditGroupModal) {
        getCategoryActions().closeEditGroupModal();
      }
    });

    el.closePeriodCustomModalBtn.addEventListener("click", () => {
      state.analyticsGlobalPendingCustom = false;
      state.dashboardAnalyticsPendingCustom = false;
      getOperationModal().closePeriodCustomModal?.();
    });
    el.periodCustomModal.addEventListener("click", (event) => {
      if (event.target === el.periodCustomModal) {
        state.analyticsGlobalPendingCustom = false;
        state.dashboardAnalyticsPendingCustom = false;
        getOperationModal().closePeriodCustomModal?.();
      }
    });

    if (el.closeDebtRepaymentModalBtn && actions.closeDebtRepaymentModal) {
      el.closeDebtRepaymentModalBtn.addEventListener("click", actions.closeDebtRepaymentModal);
    }
    if (el.debtRepaymentModal && actions.closeDebtRepaymentModal) {
      el.debtRepaymentModal.addEventListener("click", (event) => {
        if (event.target === el.debtRepaymentModal) {
          actions.closeDebtRepaymentModal();
        }
      });
    }
    if (el.closeDebtHistoryModalBtn && actions.closeDebtHistoryModal) {
      el.closeDebtHistoryModalBtn.addEventListener("click", actions.closeDebtHistoryModal);
    }
    if (el.debtHistoryModal && actions.closeDebtHistoryModal) {
      el.debtHistoryModal.addEventListener("click", (event) => {
        if (event.target === el.debtHistoryModal) {
          actions.closeDebtHistoryModal();
        }
      });
    }
    if (el.closeOperationReceiptModalBtn && getOperationsFeature().closeOperationReceiptModal) {
      el.closeOperationReceiptModalBtn.addEventListener("click", () => getOperationsFeature().closeOperationReceiptModal?.());
    }
    if (el.operationReceiptModal && getOperationsFeature().closeOperationReceiptModal) {
      el.operationReceiptModal.addEventListener("click", (event) => {
        if (event.target === el.operationReceiptModal) {
          getOperationsFeature().closeOperationReceiptModal?.();
        }
      });
    }
    if (el.closeItemTemplateModalBtn && getItemCatalogFeature().closeItemTemplateModal) {
      el.closeItemTemplateModalBtn.addEventListener("click", () => getItemCatalogFeature().closeItemTemplateModal?.());
    }
    if (el.itemTemplateModal && getItemCatalogFeature().closeItemTemplateModal) {
      el.itemTemplateModal.addEventListener("click", (event) => {
        if (event.target === el.itemTemplateModal) {
          getItemCatalogFeature().closeItemTemplateModal?.();
        }
      });
    }
    if (el.closeSourceGroupModalBtn && getItemCatalogFeature().closeSourceGroupModal) {
      el.closeSourceGroupModalBtn.addEventListener("click", () => getItemCatalogFeature().closeSourceGroupModal?.());
    }
    if (el.sourceGroupModal && getItemCatalogFeature().closeSourceGroupModal) {
      el.sourceGroupModal.addEventListener("click", (event) => {
        if (event.target === el.sourceGroupModal) {
          getItemCatalogFeature().closeSourceGroupModal?.();
        }
      });
    }
    if (el.closeItemTemplateHistoryModalBtn && getItemCatalogFeature().closeItemTemplateHistoryModal) {
      el.closeItemTemplateHistoryModalBtn.addEventListener("click", () => getItemCatalogFeature().closeItemTemplateHistoryModal?.());
    }
    if (el.itemTemplateHistoryModal && getItemCatalogFeature().closeItemTemplateHistoryModal) {
      el.itemTemplateHistoryModal.addEventListener("click", (event) => {
        if (event.target === el.itemTemplateHistoryModal) {
          getItemCatalogFeature().closeItemTemplateHistoryModal?.();
        }
      });
    }
    if (el.closeSettingsPickerModalBtn && getSessionFeature().closeSettingsPickerModal) {
      el.closeSettingsPickerModalBtn.addEventListener("click", () => getSessionFeature().closeSettingsPickerModal?.());
    }
    if (el.settingsPickerModal && getSessionFeature().closeSettingsPickerModal) {
      el.settingsPickerModal.addEventListener("click", (event) => {
        if (event.target === el.settingsPickerModal) {
          getSessionFeature().closeSettingsPickerModal?.();
        }
      });
    }
    if (el.settingsPickerOptions && getSessionFeature().applySettingsPickerValue) {
      el.settingsPickerOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-settings-picker-value]");
        if (!btn) {
          return;
        }
        getSessionFeature().applySettingsPickerValue?.(btn.dataset.settingsPickerValue || "");
      });
    }
    const pickerButtons = [
      [el.timezonePickerBtn, "timezone"],
      [el.currencyPickerBtn, "currency"],
      [el.currencyPositionPickerBtn, "currency_position"],
      [el.dashboardOperationsLimitPickerBtn, "dashboard_operations_limit"],
    ];
    for (const [buttonNode, pickerKey] of pickerButtons) {
      if (buttonNode && getSessionFeature().openSettingsPickerModal) {
        buttonNode.addEventListener("click", () => getSessionFeature().openSettingsPickerModal?.(pickerKey));
      }
    }

    el.settingsForm.addEventListener("submit", (event) => {
      const sessionFeature = getSessionFeature();
      core.runAction({
        button: el.saveSettingsBtn,
        pendingText: "Сохранение...",
        errorPrefix: "Ошибка сохранения настроек",
        action: () => sessionFeature.saveSettings?.(event),
      });
    });
    if (el.currencySelect) {
      el.currencySelect.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(350);
      });
    }
    if (el.currencyPositionSelect) {
      el.currencyPositionSelect.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(350);
      });
    }
    if (el.showDashboardDebtsToggle) {
      el.showDashboardDebtsToggle.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        const dashboardFeature = getDashboardFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
        if (state.activeSection === "dashboard" && dashboardFeature.loadDashboard) {
          dashboardFeature.loadDashboard().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.showDashboardCurrencyToggle) {
      el.showDashboardCurrencyToggle.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        const dashboardFeature = getDashboardFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
        if (state.activeSection === "dashboard" && dashboardFeature.loadDashboard) {
          dashboardFeature.loadDashboard().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.trackedCurrencyInputs?.length) {
      Array.from(el.trackedCurrencyInputs).forEach((input) => {
        input.addEventListener("change", () => {
          const sessionFeature = getSessionFeature();
          const dashboardFeature = getDashboardFeature();
          sessionFeature.savePreferencesDebounced?.(300);
          if (state.activeSection === "dashboard" && dashboardFeature.loadDashboard) {
            dashboardFeature.loadDashboard().catch((err) => core.setStatus(String(err)));
          }
        });
      });
    }
    if (el.currencyDigestToggle) {
      el.currencyDigestToggle.addEventListener("change", () => {
        getSessionFeature().savePreferencesDebounced?.(300);
      });
    }
    if (el.showDashboardAnalyticsToggle) {
      el.showDashboardAnalyticsToggle.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        const analyticsFeature = getAnalyticsFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
        if (state.activeSection === "dashboard" && analyticsFeature.loadDashboardAnalyticsPreview) {
          analyticsFeature.loadDashboardAnalyticsPreview({ force: true }).catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.showDashboardOperationsToggle) {
      el.showDashboardOperationsToggle.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        const dashboardFeature = getDashboardFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
        if (state.activeSection === "dashboard" && dashboardFeature.loadDashboardOperations) {
          dashboardFeature.loadDashboardOperations().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.plansRemindersToggle) {
      el.plansRemindersToggle.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
      });
    }
    if (el.plansReminderTimeInput) {
      el.plansReminderTimeInput.addEventListener("change", () => {
        getSessionFeature().savePreferencesDebounced?.(300);
      });
    }
    if (el.dashboardOperationsLimitSelect) {
      el.dashboardOperationsLimitSelect.addEventListener("change", () => {
        const sessionFeature = getSessionFeature();
        const dashboardFeature = getDashboardFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
        if (state.activeSection === "dashboard" && dashboardFeature.loadDashboardOperations) {
          dashboardFeature.loadDashboardOperations().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.uiScaleRange) {
      el.uiScaleRange.addEventListener("input", () => {
        const sessionFeature = getSessionFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(600);
      });
    }
    if (el.resetUiScaleBtn) {
      el.resetUiScaleBtn.addEventListener("click", () => {
        if (el.uiScaleRange) {
          el.uiScaleRange.value = "100";
        }
        const sessionFeature = getSessionFeature();
        sessionFeature.previewInterfaceSettingsUi?.();
        sessionFeature.savePreferencesDebounced?.(300);
      });
    }
    window.addEventListener("resize", () => {
      const sessionFeature = getSessionFeature();
      sessionFeature.syncSettingsPickerButtons?.();
      if (!core.isMobileViewport() && sessionFeature.closeSettingsPickerModal) {
        sessionFeature.closeSettingsPickerModal();
      }
    });
    if (el.deleteMeBtn) {
      el.deleteMeBtn.addEventListener("click", () => {
        const sessionFeature = getSessionFeature();
        core.runAction({
          button: el.deleteMeBtn,
          pendingText: "Удаление...",
          errorPrefix: "Ошибка удаления аккаунта",
          action: () => sessionFeature.deleteMe?.(),
        });
      });
    }

    el.confirmCancelBtn.addEventListener("click", core.closeConfirm);
    el.confirmDeleteBtn.addEventListener("click", () => {
      const action = state.pendingConfirm;
      core.closeConfirm();
      if (action) {
        action().catch((err) => core.setStatus(String(err)));
      }
    });
    el.confirmModal.addEventListener("click", (event) => {
      if (event.target === el.confirmModal) {
        core.closeConfirm();
      }
    });

    if (el.plansTabTabs && getPlansFeature().setPlansTab) {
      el.plansTabTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-tab]");
        if (!btn) {
          return;
        }
        getPlansFeature().setPlansTab?.(btn.dataset.planTab || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansKindTabs && getPlansFeature().setPlansKindFilter) {
      el.plansKindTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-kind]");
        if (!btn) {
          return;
        }
        getPlansFeature().setPlansKindFilter?.(btn.dataset.planKind || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansStatusTabs && getPlansFeature().setPlansStatusFilter) {
      el.plansStatusTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-status]");
        if (!btn) {
          return;
        }
        getPlansFeature().setPlansStatusFilter?.(btn.dataset.planStatus || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansHistoryEventTabs && getPlansFeature().setPlansHistoryEventFilter) {
      el.plansHistoryEventTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-history-event]");
        if (!btn) {
          return;
        }
        getPlansFeature().setPlansHistoryEventFilter?.(btn.dataset.planHistoryEvent || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansSearchQ && getPlansFeature().applyPlansSearch) {
      el.plansSearchQ.addEventListener("input", () => {
        getPlansFeature().applyPlansSearch?.();
      });
    }
    if (el.plansList && getPlansFeature().handlePlanActionClick) {
      el.plansList.addEventListener("click", (event) => {
        getPlansFeature().handlePlanActionClick?.(event);
      });
    }
    if (el.dashboardPlansList && getPlansFeature().handlePlanActionClick) {
      el.dashboardPlansList.addEventListener("click", (event) => {
        getPlansFeature().handlePlanActionClick?.(event);
      });
    }
    if (el.dashboardPlansPeriodTabs && getPlansFeature().setDashboardPlansPeriod) {
      el.dashboardPlansPeriodTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-dashboard-plans-period]");
        if (!btn) {
          return;
        }
        getPlansFeature().setDashboardPlansPeriod?.(btn.dataset.dashboardPlansPeriod || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.planScheduleModeSwitch && getPlansFeature().syncPlanRecurrenceUi) {
      el.planScheduleModeSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-schedule-mode]");
        if (!btn) {
          return;
        }
        if (el.planScheduleMode) {
          el.planScheduleMode.value = btn.dataset.planScheduleMode || "oneoff";
        }
        core.syncSegmentedActive(el.planScheduleModeSwitch, "plan-schedule-mode", el.planScheduleMode?.value || "oneoff");
        const plansFeature = getPlansFeature();
        const operationModal = getOperationModal();
        plansFeature.syncPlanRecurrenceUi?.();
        operationModal.updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceFrequency && getPlansFeature().syncPlanRecurrenceUi) {
      el.planRecurrenceFrequency.addEventListener("change", () => {
        const plansFeature = getPlansFeature();
        const operationModal = getOperationModal();
        plansFeature.syncPlanRecurrenceUi?.();
        operationModal.updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceInterval) {
      el.planRecurrenceInterval.addEventListener("input", () => {
        getOperationModal().updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceEndDate) {
      el.planRecurrenceEndDate.addEventListener("change", () => {
        getOperationModal().updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceWorkdaysOnly && el.planRecurrenceWorkdaysSwitch) {
      el.planRecurrenceWorkdaysSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-workdays-only]");
        if (!btn) {
          return;
        }
        el.planRecurrenceWorkdaysOnly.value = (btn.dataset.planWorkdaysOnly || "off") === "on" ? "on" : "off";
        core.syncSegmentedActive(el.planRecurrenceWorkdaysSwitch, "plan-workdays-only", el.planRecurrenceWorkdaysOnly.value);
        getOperationModal().updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceMonthEnd) {
      const syncMonthEndMode = (value) => {
        if (el.planRecurrenceMonthEnd) {
          el.planRecurrenceMonthEnd.value = value ? "on" : "off";
        }
        if (el.planRecurrenceMonthEndSwitch) {
          core.syncSegmentedActive(el.planRecurrenceMonthEndSwitch, "plan-month-end", value ? "on" : "off");
        }
        const plansFeature = getPlansFeature();
        const operationModal = getOperationModal();
        plansFeature.syncPlanRecurrenceUi?.();
        operationModal.updateCreatePreview?.();
      };
      if (el.planRecurrenceMonthEndSwitch) {
        el.planRecurrenceMonthEndSwitch.addEventListener("click", (event) => {
          const btn = event.target.closest("button[data-plan-month-end]");
          if (!btn) {
            return;
          }
          syncMonthEndMode((btn.dataset.planMonthEnd || "off") === "on");
        });
      }
    }
    if (el.planRecurrenceWeekdays && getPlansFeature().togglePlanWeekday) {
      el.planRecurrenceWeekdays.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-weekday]");
        if (!btn) {
          return;
        }
        const plansFeature = getPlansFeature();
        const operationModal = getOperationModal();
        plansFeature.togglePlanWeekday?.(Number(btn.dataset.planWeekday || 0));
        operationModal.updateCreatePreview?.();
      });
    }
  }

  function bindCoreInit() {
    if (bound) {
      return;
    }
    bound = true;
    bindCoreHandlers();
    bindModalHandlers();
  }

  const api = {
    bindCoreInit,
  };

  window.App.initCore = api;
  window.App.registerBootstrapModule?.("core", api);
})();
