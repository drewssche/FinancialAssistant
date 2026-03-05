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

    el.userMenuToggle.addEventListener("click", () => {
      el.userMenu.classList.toggle("hidden");
    });

    el.openSettingsBtn.addEventListener("click", () => {
      core.closeAllMenus();
      actions.switchSection("settings").catch((err) => core.setStatus(String(err)));
    });

    el.logoutBtn.addEventListener("click", () => actions.logout(true));

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".icon-select") && !event.target.closest(".color-select") && actions.closeIconPopovers) {
        actions.closeIconPopovers();
      }
      if (!event.target.closest(".user-area")) {
        core.closeAllMenus();
      }
    });
  }

  function bindModalHandlers() {
    el.addOperationCta.addEventListener("click", actions.openCreateModal);
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

    el.settingsForm.addEventListener("submit", (event) => {
      core.runAction({
        button: el.saveSettingsBtn,
        pendingText: "Сохранение...",
        successMessage: "Настройки сохранены",
        errorPrefix: "Ошибка сохранения настроек",
        action: () => actions.saveSettings(event),
      });
    });

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
