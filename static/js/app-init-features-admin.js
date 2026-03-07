(() => {
  const { state, el, core, actions } = window.App;
  let bound = false;

  function bindAdminFeatureHandlers() {
    if (bound) {
      return;
    }
    bound = true;

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
            errorPrefix: "Ошибка апрува",
            action: async () => {
              await actions.approveAdminUser(Number(approveBtn.dataset.adminApproveId));
            },
          });
          return;
        }
        const rejectBtn = event.target.closest("button[data-admin-reject-id]");
        if (rejectBtn && actions.rejectAdminUser) {
          core.runAction({
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
  }

  window.App.initFeatureAdmin = {
    bindAdminFeatureHandlers,
  };
})();
