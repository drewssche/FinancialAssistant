(() => {
  const { state, el, core } = window.App;
  let bound = false;

  function bindAdminFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;
    const actions = window.App.getRuntimeModule("admin");
    window.App.icons.apply(el.refreshAdminCurrencyDiagnosticsBtn, "refresh", "Обновить диагностику курсов");
    document.getElementById("adminViewTabs").addEventListener("click", event => {
      const button = event.target.closest("[data-admin-view]");
      if (button) core.runAction({
        errorPrefix: "Ошибка загрузки раздела",
        action: () => window.App.getRuntimeModule("admin").setAdminView(button.dataset.adminView),
      });
    });

    if (el.adminUserStatusTabs && actions.setAdminUserStatusFilter) {
      el.adminUserStatusTabs.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-admin-user-status]");
        if (!btn) {
          return;
        }
        if (state.adminUserStatusFilter === btn.dataset.adminUserStatus) {
          return;
        }
        core.runAction({
          errorPrefix: "Ошибка загрузки пользователей",
          action: () => actions.setAdminUserStatusFilter(btn.dataset.adminUserStatus),
        });
      });
    }

    if (el.adminUsersBody) {
      el.adminUsersBody.addEventListener("click", (event) => {
        const approveBtn = event.target.closest("button[data-admin-approve-id]");
        if (approveBtn && actions.approveAdminUser) {
          core.runAction({
            button: approveBtn,
            errorPrefix: "Не удалось разрешить доступ",
            action: async () => {
              await actions.approveAdminUser(Number(approveBtn.dataset.adminApproveId));
            },
          });
          return;
        }
        const rejectBtn = event.target.closest("button[data-admin-reject-id]");
        if (rejectBtn && actions.rejectAdminUser) {
          core.runAction({
            button: rejectBtn,
            errorPrefix: "Ошибка отклонения",
            action: async () => {
              await actions.rejectAdminUser(Number(rejectBtn.dataset.adminRejectId));
            },
          });
          return;
        }
        const deleteBtn = event.target.closest("button[data-admin-delete-id]");
        if (deleteBtn && actions.deleteAdminUser) {
          core.runDestructiveAction({
            confirmMessage: "Удалить пользователя со всеми данными?",
            doDelete: () => actions.deleteAdminUser(Number(deleteBtn.dataset.adminDeleteId)),
            toastMessage: "Пользователь удален",
            onDeleteError: "Не удалось удалить пользователя",
          });
        }
      });
    }
    if (el.refreshAdminCurrencyDiagnosticsBtn && actions.loadAdminCurrencyDiagnostics) {
      el.refreshAdminCurrencyDiagnosticsBtn.addEventListener("click", () => {
        core.runAction({
          button: el.refreshAdminCurrencyDiagnosticsBtn,
          errorPrefix: "Ошибка обновления диагностики валют",
          action: async () => {
            await actions.loadAdminCurrencyDiagnostics({ force: true });
          },
        });
      });
    }
  }

  const api = {
    bindAdminFeatureHandlers,
  };

  window.App.initFeatureAdmin = api;
  window.App.registerFeatureInitModule?.("admin", api);
})();
