(() => {
  const { state, el, core } = window.App;
  const ADMIN_CACHE_TTL_MS = 15000;
  const escapeHtml = core.escapeHtml || ((value) => String(value ?? ""));

  function formatDateTimeRu(value) {
    if (!value) {
      return "—";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "—";
    }
    return date.toLocaleString("ru-RU");
  }

  function statusLabel(status) {
    if (status === "approved" || status === "active") {
      return "Одобрен";
    }
    if (status === "rejected") {
      return "Отклонен";
    }
    return "Ожидает";
  }

  function statusBadgeClass(status) {
    if (status === "approved" || status === "active") {
      return "debt-status-paid";
    }
    if (status === "rejected") {
      return "debt-status-overdue";
    }
    return "debt-status-active";
  }

  function renderAdminUsers(data) {
    if (!el.adminUsersBody) {
      return;
    }
    const items = Array.isArray(data?.items) ? data.items : [];
    if (!items.length) {
      el.adminUsersBody.innerHTML = "<tr><td colspan='7'>Нет пользователей по выбранному фильтру</td></tr>";
      return;
    }
    el.adminUsersBody.innerHTML = items
      .map((user) => {
        const status = user.status || "pending";
        const canApprove = status !== "approved" && status !== "active";
        const canReject = status !== "rejected";
        return `
          <tr>
            <td data-label="ID">${user.id}</td>
            <td data-label="Пользователь">${escapeHtml(user.display_name || "Без имени")}<div class="muted-small">@${escapeHtml(user.username || "—")}</div></td>
            <td data-label="Telegram">${escapeHtml(user.telegram_id || "—")}</td>
            <td data-label="Статус"><span class="debt-status ${statusBadgeClass(status)}">${statusLabel(status)}</span></td>
            <td data-label="Создан">${formatDateTimeRu(user.created_at)}</td>
            <td data-label="Последний вход">${formatDateTimeRu(user.last_login_at)}</td>
            <td class="mobile-actions-cell" data-label="Действия">
              <div class="actions row-actions admin-row-actions">
                ${canApprove ? `<button class="btn btn-secondary btn-xs" data-admin-approve-id="${user.id}" type="button">Approve</button>` : ""}
                ${canReject ? `<button class="btn btn-secondary btn-xs" data-admin-reject-id="${user.id}" type="button">Reject</button>` : ""}
                <button class="btn btn-danger btn-xs" data-admin-delete-id="${user.id}" type="button">Удалить</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadAdminUsers(options = {}) {
    const force = options.force === true;
    const filter = state.adminUserStatusFilter || "pending";
    const cacheKey = `admin:users:status=${filter}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, ADMIN_CACHE_TTL_MS);
      if (cached) {
        renderAdminUsers(cached);
        return cached;
      }
    }
    const data = await core.requestJson(`/api/v1/admin/users?status_filter=${encodeURIComponent(filter)}`, {
      headers: core.authHeaders(),
    });
    core.setUiRequestCache(cacheKey, data);
    renderAdminUsers(data);
    return data;
  }

  async function setAdminUserStatusFilter(filter) {
    const allowed = new Set(["pending", "approved", "rejected", "all"]);
    state.adminUserStatusFilter = allowed.has(filter) ? filter : "pending";
    core.syncSegmentedActive(el.adminUserStatusTabs, "admin-user-status", state.adminUserStatusFilter);
    await loadAdminUsers({ force: true });
    if (window.App.actions.savePreferences) {
      await window.App.actions.savePreferences();
    }
  }

  async function updateAdminUserStatus(userId, status) {
    await core.requestJson(`/api/v1/admin/users/${userId}/status`, {
      method: "PATCH",
      headers: core.authHeaders(),
      body: JSON.stringify({ status }),
    });
    core.invalidateUiRequestCache("admin:users:");
    await loadAdminUsers({ force: true });
  }

  async function approveAdminUser(userId) {
    await updateAdminUserStatus(userId, "approved");
  }

  async function rejectAdminUser(userId) {
    await updateAdminUserStatus(userId, "rejected");
  }

  async function deleteAdminUser(userId) {
    await core.requestJson(`/api/v1/admin/users/${userId}`, {
      method: "DELETE",
      headers: core.authHeaders(),
    });
    core.invalidateUiRequestCache("admin:users:");
    await loadAdminUsers({ force: true });
  }

  window.App.featureAdmin = {
    loadAdminUsers,
    setAdminUserStatusFilter,
    approveAdminUser,
    rejectAdminUser,
    deleteAdminUser,
  };
})();
