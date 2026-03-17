(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;
  let compactViewportQuery = null;

  function isCompactMobileViewport() {
    return window.matchMedia("(max-width: 640px)").matches;
  }

  function rerenderActiveSectionForViewportMode() {
    switch (state.activeSection) {
      case "operations":
        actions.refreshOperationsView?.();
        break;
      case "categories":
        actions.renderCategories?.();
        break;
      case "item_catalog":
        actions.refreshItemCatalogView?.();
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
    if (el.telegramLoginBtn && actions.telegramLogin) {
      el.telegramLoginBtn.addEventListener("click", () => {
        core.runAction({
          button: el.telegramLoginBtn,
          pendingText: "Вход...",
          errorPrefix: "Ошибка входа",
          shouldPrefixError: (message) => !(
            message === "Заявка отправлена. Ожидайте одобрения администратора"
            || message === "Доступ отклонен администратором"
          ),
          forLogin: true,
          action: () => actions.telegramLogin(),
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
        if (actions.setAnalyticsTab) {
          actions.setAnalyticsTab("structure");
        }
        actions.switchSection("analytics").catch((err) => core.setStatus(String(err)));
      });
    }

    if (el.sidebarLogoutBtn) {
      el.sidebarLogoutBtn.addEventListener("click", () => actions.logout(true));
    }

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".icon-select") && !event.target.closest(".color-select") && actions.closeIconPopovers) {
        actions.closeIconPopovers();
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
    el.addOperationCta.addEventListener("click", actions.openCreateModal);
    if (el.addPlanCta && actions.openCreatePlan) {
      el.addPlanCta.addEventListener("click", actions.openCreatePlan);
    }
    if (el.addDebtCta) {
      el.addDebtCta.addEventListener("click", () => {
        actions.openCreateModal();
        if (actions.setCreateEntryMode) {
          actions.setCreateEntryMode("debt");
        }
      });
    }
    if (el.addItemTemplateCta && actions.openItemTemplateModal) {
      el.addItemTemplateCta.addEventListener("click", () => {
        actions.openItemTemplateModal();
      });
    }
    if (el.addItemSourceCta && actions.openSourceGroupModal) {
      el.addItemSourceCta.addEventListener("click", () => {
        actions.openSourceGroupModal();
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

    el.closeCreateModalBtn.addEventListener("click", actions.closeCreateModal);
    el.createModal.addEventListener("click", (event) => {
      if (event.target === el.createModal) {
        actions.closeCreateModal();
      }
    });

    el.closeEditModalBtn.addEventListener("click", actions.closeEditModal);
    el.editModal.addEventListener("click", (event) => {
      if (event.target === el.editModal) {
        actions.closeEditModal();
      }
    });

    el.addCategoryCta.addEventListener("click", actions.openCreateCategoryModal);
    el.addGroupCta.addEventListener("click", () => {
      if (actions.openCreateGroupModal) {
        actions.openCreateGroupModal();
      }
    });
    el.closeCreateCategoryModalBtn.addEventListener("click", actions.closeCreateCategoryModal);
    el.createCategoryModal.addEventListener("click", (event) => {
      if (event.target === el.createCategoryModal) {
        actions.closeCreateCategoryModal();
      }
    });
    el.categoryIconToggle.addEventListener("click", () => {
      el.categoryIconPopover.classList.toggle("hidden");
      el.editCategoryIconPopover.classList.add("hidden");
    });

    el.closeEditCategoryModalBtn.addEventListener("click", actions.closeEditCategoryModal);
    el.editCategoryModal.addEventListener("click", (event) => {
      if (event.target === el.editCategoryModal) {
        actions.closeEditCategoryModal();
      }
    });
    el.editCategoryIconToggle.addEventListener("click", () => {
      el.editCategoryIconPopover.classList.toggle("hidden");
      el.categoryIconPopover.classList.add("hidden");
    });

    el.closeEditGroupModalBtn.addEventListener("click", () => {
      if (actions.closeEditGroupModal) {
        actions.closeEditGroupModal();
      }
    });
    el.editGroupModal.addEventListener("click", (event) => {
      if (event.target === el.editGroupModal && actions.closeEditGroupModal) {
        actions.closeEditGroupModal();
      }
    });

    el.closePeriodCustomModalBtn.addEventListener("click", () => {
      state.analyticsGlobalPendingCustom = false;
      state.dashboardAnalyticsPendingCustom = false;
      actions.closePeriodCustomModal();
    });
    el.periodCustomModal.addEventListener("click", (event) => {
      if (event.target === el.periodCustomModal) {
        state.analyticsGlobalPendingCustom = false;
        state.dashboardAnalyticsPendingCustom = false;
        actions.closePeriodCustomModal();
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
    if (el.closeOperationReceiptModalBtn && actions.closeOperationReceiptModal) {
      el.closeOperationReceiptModalBtn.addEventListener("click", actions.closeOperationReceiptModal);
    }
    if (el.operationReceiptModal && actions.closeOperationReceiptModal) {
      el.operationReceiptModal.addEventListener("click", (event) => {
        if (event.target === el.operationReceiptModal) {
          actions.closeOperationReceiptModal();
        }
      });
    }
    if (el.closeItemTemplateModalBtn && actions.closeItemTemplateModal) {
      el.closeItemTemplateModalBtn.addEventListener("click", actions.closeItemTemplateModal);
    }
    if (el.itemTemplateModal && actions.closeItemTemplateModal) {
      el.itemTemplateModal.addEventListener("click", (event) => {
        if (event.target === el.itemTemplateModal) {
          actions.closeItemTemplateModal();
        }
      });
    }
    if (el.closeSourceGroupModalBtn && actions.closeSourceGroupModal) {
      el.closeSourceGroupModalBtn.addEventListener("click", actions.closeSourceGroupModal);
    }
    if (el.sourceGroupModal && actions.closeSourceGroupModal) {
      el.sourceGroupModal.addEventListener("click", (event) => {
        if (event.target === el.sourceGroupModal) {
          actions.closeSourceGroupModal();
        }
      });
    }
    if (el.closeItemTemplateHistoryModalBtn && actions.closeItemTemplateHistoryModal) {
      el.closeItemTemplateHistoryModalBtn.addEventListener("click", actions.closeItemTemplateHistoryModal);
    }
    if (el.itemTemplateHistoryModal && actions.closeItemTemplateHistoryModal) {
      el.itemTemplateHistoryModal.addEventListener("click", (event) => {
        if (event.target === el.itemTemplateHistoryModal) {
          actions.closeItemTemplateHistoryModal();
        }
      });
    }
    if (el.closeSettingsPickerModalBtn && actions.closeSettingsPickerModal) {
      el.closeSettingsPickerModalBtn.addEventListener("click", actions.closeSettingsPickerModal);
    }
    if (el.settingsPickerModal && actions.closeSettingsPickerModal) {
      el.settingsPickerModal.addEventListener("click", (event) => {
        if (event.target === el.settingsPickerModal) {
          actions.closeSettingsPickerModal();
        }
      });
    }
    if (el.settingsPickerOptions && actions.applySettingsPickerValue) {
      el.settingsPickerOptions.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-settings-picker-value]");
        if (!btn) {
          return;
        }
        actions.applySettingsPickerValue(btn.dataset.settingsPickerValue || "");
      });
    }
    const pickerButtons = [
      [el.timezonePickerBtn, "timezone"],
      [el.currencyPickerBtn, "currency"],
      [el.currencyPositionPickerBtn, "currency_position"],
      [el.dashboardOperationsLimitPickerBtn, "dashboard_operations_limit"],
    ];
    for (const [buttonNode, pickerKey] of pickerButtons) {
      if (buttonNode && actions.openSettingsPickerModal) {
        buttonNode.addEventListener("click", () => actions.openSettingsPickerModal(pickerKey));
      }
    }

    el.settingsForm.addEventListener("submit", (event) => {
      core.runAction({
        button: el.saveSettingsBtn,
        pendingText: "Сохранение...",
        errorPrefix: "Ошибка сохранения настроек",
        action: () => actions.saveSettings(event),
      });
    });
    if (el.currencySelect) {
      el.currencySelect.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(350);
        }
      });
    }
    if (el.currencyPositionSelect) {
      el.currencyPositionSelect.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(350);
        }
      });
    }
    if (el.showDashboardDebtsToggle) {
      el.showDashboardDebtsToggle.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
        if (state.activeSection === "dashboard" && actions.loadDashboard) {
          actions.loadDashboard().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.showDashboardAnalyticsToggle) {
      el.showDashboardAnalyticsToggle.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
        if (state.activeSection === "dashboard" && actions.loadDashboardAnalyticsPreview) {
          actions.loadDashboardAnalyticsPreview({ force: true }).catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.showDashboardOperationsToggle) {
      el.showDashboardOperationsToggle.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
        if (state.activeSection === "dashboard" && actions.loadDashboardOperations) {
          actions.loadDashboardOperations().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.plansRemindersToggle) {
      el.plansRemindersToggle.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
      });
    }
    if (el.plansReminderTimeInput) {
      el.plansReminderTimeInput.addEventListener("change", () => {
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
      });
    }
    if (el.dashboardOperationsLimitSelect) {
      el.dashboardOperationsLimitSelect.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
        if (state.activeSection === "dashboard" && actions.loadDashboardOperations) {
          actions.loadDashboardOperations().catch((err) => core.setStatus(String(err)));
        }
      });
    }
    if (el.uiScaleRange) {
      el.uiScaleRange.addEventListener("input", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(600);
        }
      });
    }
    if (el.resetUiScaleBtn) {
      el.resetUiScaleBtn.addEventListener("click", () => {
        if (el.uiScaleRange) {
          el.uiScaleRange.value = "100";
        }
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
        if (actions.savePreferencesDebounced) {
          actions.savePreferencesDebounced(300);
        }
      });
    }
    window.addEventListener("resize", () => {
      if (actions.syncSettingsPickerButtons) {
        actions.syncSettingsPickerButtons();
      }
      if (!core.isMobileViewport() && actions.closeSettingsPickerModal) {
        actions.closeSettingsPickerModal();
      }
    });
    if (el.deleteMeBtn) {
      el.deleteMeBtn.addEventListener("click", () => {
        core.runAction({
          button: el.deleteMeBtn,
          pendingText: "Удаление...",
          errorPrefix: "Ошибка удаления аккаунта",
          action: () => actions.deleteMe(),
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

    if (el.plansTabTabs && actions.setPlansTab) {
      el.plansTabTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-tab]");
        if (!btn) {
          return;
        }
        actions.setPlansTab(btn.dataset.planTab || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansKindTabs && actions.setPlansKindFilter) {
      el.plansKindTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-kind]");
        if (!btn) {
          return;
        }
        actions.setPlansKindFilter(btn.dataset.planKind || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansStatusTabs && actions.setPlansStatusFilter) {
      el.plansStatusTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-status]");
        if (!btn) {
          return;
        }
        actions.setPlansStatusFilter(btn.dataset.planStatus || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansHistoryEventTabs && actions.setPlansHistoryEventFilter) {
      el.plansHistoryEventTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-history-event]");
        if (!btn) {
          return;
        }
        actions.setPlansHistoryEventFilter(btn.dataset.planHistoryEvent || "").catch((err) => core.setStatus(String(err)));
      });
    }
    if (el.plansSearchQ && actions.applyPlansSearch) {
      el.plansSearchQ.addEventListener("input", () => {
        actions.applyPlansSearch();
      });
    }
    if (el.plansList && actions.handlePlanActionClick) {
      el.plansList.addEventListener("click", (event) => {
        actions.handlePlanActionClick(event);
      });
    }
    if (el.dashboardPlansList && actions.handlePlanActionClick) {
      el.dashboardPlansList.addEventListener("click", (event) => {
        actions.handlePlanActionClick(event);
      });
    }
    if (el.planScheduleModeSwitch && actions.syncPlanRecurrenceUi) {
      el.planScheduleModeSwitch.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-schedule-mode]");
        if (!btn) {
          return;
        }
        if (el.planScheduleMode) {
          el.planScheduleMode.value = btn.dataset.planScheduleMode || "oneoff";
        }
        core.syncSegmentedActive(el.planScheduleModeSwitch, "plan-schedule-mode", el.planScheduleMode?.value || "oneoff");
        actions.syncPlanRecurrenceUi();
        actions.updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceFrequency && actions.syncPlanRecurrenceUi) {
      el.planRecurrenceFrequency.addEventListener("change", () => {
        actions.syncPlanRecurrenceUi();
        actions.updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceInterval) {
      el.planRecurrenceInterval.addEventListener("input", () => {
        actions.updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceEndDate) {
      el.planRecurrenceEndDate.addEventListener("change", () => {
        actions.updateCreatePreview?.();
      });
    }
    if (el.planRecurrenceWorkdaysOnly) {
      el.planRecurrenceWorkdaysOnly.addEventListener("change", () => {
        actions.updateCreatePreview?.();
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
        actions.syncPlanRecurrenceUi?.();
        actions.updateCreatePreview?.();
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
    if (el.planRecurrenceWeekdays && actions.togglePlanWeekday) {
      el.planRecurrenceWeekdays.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-plan-weekday]");
        if (!btn) {
          return;
        }
        actions.togglePlanWeekday(Number(btn.dataset.planWeekday || 0));
        actions.updateCreatePreview?.();
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

  window.App.initCore = {
    bindCoreInit,
  };
})();
