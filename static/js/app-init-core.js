(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;

  function bindCoreHandlers() {
    el.devLoginBtn.addEventListener("click", () => {
      core.runAction({
        button: el.devLoginBtn,
        pendingText: "Вход...",
        errorPrefix: "Ошибка входа",
        forLogin: true,
        action: () => actions.devLogin(),
      });
    });

    el.mainNav.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-section]");
      if (!btn) {
        return;
      }
      actions.switchSection(btn.dataset.section).catch((err) => core.setStatus(String(err)));
    });

    el.openOperationsTabBtn.addEventListener("click", () => {
      actions.switchSection("operations").catch((err) => core.setStatus(String(err)));
    });
    if (el.openDebtsTabBtn) {
      el.openDebtsTabBtn.addEventListener("click", () => {
        actions.switchSection("debts").catch((err) => core.setStatus(String(err)));
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
  }

  function bindModalHandlers() {
    el.addOperationCta.addEventListener("click", actions.openCreateModal);
    if (el.addDebtCta) {
      el.addDebtCta.addEventListener("click", () => {
        actions.openCreateModal();
        if (actions.setCreateEntryMode) {
          actions.setCreateEntryMode("debt");
        }
      });
    }
    el.batchOperationCta.addEventListener("click", () => {
      if (actions.openBatchCreateModal) {
        actions.openBatchCreateModal();
      }
    });

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

    el.closePeriodCustomModalBtn.addEventListener("click", actions.closePeriodCustomModal);
    el.periodCustomModal.addEventListener("click", (event) => {
      if (event.target === el.periodCustomModal) {
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
      });
    }
    if (el.currencyPositionSelect) {
      el.currencyPositionSelect.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
      });
    }
    if (el.showDashboardDebtsToggle) {
      el.showDashboardDebtsToggle.addEventListener("change", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
        }
      });
    }
    if (el.uiScaleRange) {
      el.uiScaleRange.addEventListener("input", () => {
        if (actions.previewInterfaceSettingsUi) {
          actions.previewInterfaceSettingsUi();
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
      });
    }
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
