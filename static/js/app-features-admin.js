(() => {
  const { state, el, core } = window.App;
  let usersRequestSequence = 0;
  let diagnosticsRequestSequence = 0;
  let adminView = "users";
  const ADMIN_CACHE_TTL_MS = 15000;
  const escapeHtml = core.escapeHtml || ((value) => String(value ?? ""));

  function getSessionFeature() {
    return window.App.getRuntimeModule?.("session") || {};
  }

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
            <td data-label="Пользователь"><div class="admin-user-identity">${escapeHtml(user.display_name || "Без имени")}<div class="muted-small">@${escapeHtml(user.username || "—")}</div></div></td>
            <td data-label="Telegram">${escapeHtml(user.telegram_id || "—")}</td>
            <td data-label="Статус"><span class="debt-status ${statusBadgeClass(status)}">${statusLabel(status)}</span></td>
            <td data-label="Создан">${formatDateTimeRu(user.created_at)}</td>
            <td data-label="Последний вход">${formatDateTimeRu(user.last_login_at)}</td>
            <td class="mobile-actions-cell" data-label="Действия">
              <div class="actions row-actions admin-row-actions">
                ${canApprove ? `<button class="btn btn-secondary btn-xs btn-icon" data-admin-approve-id="${user.id}" type="button" aria-label="Разрешить доступ" title="Разрешить доступ">${window.App.icons.svg("save")}</button>` : ""}
                ${canReject ? `<button class="btn btn-secondary btn-xs btn-icon" data-admin-reject-id="${user.id}" type="button" aria-label="Отклонить доступ" title="Отклонить доступ">${window.App.icons.svg("close")}</button>` : ""}
                <button class="btn btn-danger btn-xs btn-icon" data-admin-delete-id="${user.id}" type="button" aria-label="Удалить пользователя" title="Удалить пользователя">${window.App.icons.svg("trash")}</button>
              </div>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function formatRate(value) {
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    const numeric = Number(value);
    return Number.isFinite(numeric) ? core.formatRateDisplay?.(numeric, 4, 6) : escapeHtml(String(value));
  }

  function renderAdminCurrencyDiagnostics(data) {
    if (el.adminCurrencyDiagnosticsKpi) {
      el.adminCurrencyDiagnosticsKpi.innerHTML = `
        <article class="kpi-card">
          <span class="kpi-label">Пользователи</span>
          <strong class="kpi-value">${Number(data?.tracked_users || 0)}</strong>
          <span class="kpi-meta">${Number(data?.tracked_currency_slots || 0)} подписок на валюты</span>
        </article>
        <article class="kpi-card">
          <span class="kpi-label">Рассылка</span>
          <strong class="kpi-value">${Number(data?.digest_enabled_users || 0)}</strong>
          <span class="kpi-meta">пользователей</span>
        </article>
        <article class="kpi-card">
          <span class="kpi-label">Пороги курса</span>
          <strong class="kpi-value">${Number(data?.alert_rules_count || 0)}</strong>
          <span class="kpi-meta">активных порогов</span>
        </article>
        <article class="kpi-card">
          <span class="kpi-label">Устарели / отсутствуют</span>
          <strong class="kpi-value">${Number(data?.stale_slots || 0)} / ${Number(data?.missing_slots || 0)}</strong>
          <span class="kpi-meta">Последний курс: ${escapeHtml(data?.freshest_rate_date || "—")}</span>
        </article>
      `;
    }
    if (!el.adminCurrencyDiagnosticsBody) {
      return;
    }
    const items = Array.isArray(data?.items) ? data.items : [];
    if (!items.length) {
      el.adminCurrencyDiagnosticsBody.innerHTML = "<tr><td colspan='7'>Нет валютных настроек для диагностики</td></tr>";
      return;
    }
    el.adminCurrencyDiagnosticsBody.innerHTML = items.map((item) => `
      <tr>
        <td data-label="Валюта"><strong>${escapeHtml(item.currency || "—")}</strong></td>
        <td data-label="Пользователей">${Number(item.tracked_users || 0)}</td>
        <td data-label="Рассылка">${Number(item.digest_users || 0)}</td>
        <td data-label="Пороги">${Number(item.alert_rules || 0)}</td>
        <td data-label="Последний курс">${formatRate(item.latest_rate)}<div class="muted-small">${escapeHtml(item.latest_rate_date || "—")}</div></td>
        <td data-label="Устарели">${Number(item.stale_users || 0)}</td>
        <td data-label="Нет курса">${Number(item.missing_users || 0)}</td>
      </tr>
    `).join("");
  }

  async function loadAdminUsers(options = {}) {
    const force = options.force === true;
    const sequence = ++usersRequestSequence;
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
    if (sequence === usersRequestSequence) {
      core.setUiRequestCache(cacheKey, data);
      renderAdminUsers(data);
    }
    return data;
  }

  async function loadAdminCurrencyDiagnostics(options = {}) {
    const force = options.force === true;
    const sequence = ++diagnosticsRequestSequence;
    const cacheKey = "admin:currency-diagnostics";
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, ADMIN_CACHE_TTL_MS);
      if (cached) {
        renderAdminCurrencyDiagnostics(cached);
        return cached;
      }
    }
    const data = await core.requestJson("/api/v1/admin/currency-diagnostics", {
      headers: core.authHeaders(),
    });
    if (sequence === diagnosticsRequestSequence) {
      core.setUiRequestCache(cacheKey, data);
      renderAdminCurrencyDiagnostics(data);
    }
    return data;
  }

  async function setAdminUserStatusFilter(filter) {
    const allowed = new Set(["pending", "approved", "rejected", "all"]);
    state.adminUserStatusFilter = allowed.has(filter) ? filter : "pending";
    core.syncSegmentedActive(el.adminUserStatusTabs, "admin-user-status", state.adminUserStatusFilter);
    await loadAdminUsers({ force: true });
    const sessionFeature = getSessionFeature();
    if (sessionFeature.savePreferences) {
      await sessionFeature.savePreferences();
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

  async function setAdminView(view = adminView, options = {}) {
    adminView = view === "diagnostics" ? "diagnostics" : "users";
    document.getElementById("adminUsersPanel").classList.toggle("hidden", adminView !== "users");
    document.getElementById("adminDiagnosticsPanel").classList.toggle("hidden", adminView !== "diagnostics");
    document.querySelectorAll("[data-admin-view]").forEach(button => {
      const selected = button.dataset.adminView === adminView;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    return adminView === "users" ? loadAdminUsers(options) : loadAdminCurrencyDiagnostics(options);
  }

  const api = {
    setAdminView,
    loadAdminUsers,
    loadAdminCurrencyDiagnostics,
    setAdminUserStatusFilter,
    approveAdminUser,
    rejectAdminUser,
    deleteAdminUser,
  };

  window.App.featureAdmin = api;
  window.App.registerRuntimeModule?.("admin", api);
})();
