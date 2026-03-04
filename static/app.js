const state = {
  token: localStorage.getItem("access_token") || "",
  preferences: null,
  page: 1,
  pageSize: 10,
  total: 0,
  editOperationId: null,
};

const el = {
  loginScreen: document.getElementById("loginScreen"),
  appShell: document.getElementById("appShell"),
  loginOutput: document.getElementById("loginOutput"),
  appOutput: document.getElementById("appOutput"),
  devLoginBtn: document.getElementById("devLoginBtn"),
  dashboardPeriod: document.getElementById("dashboardPeriod"),
  refreshBtn: document.getElementById("refreshBtn"),
  createForm: document.getElementById("createOperationForm"),
  applyFiltersBtn: document.getElementById("applyFilters"),
  operationsBody: document.getElementById("operationsBody"),
  pageInfo: document.getElementById("pageInfo"),
  prevPageBtn: document.getElementById("prevPageBtn"),
  nextPageBtn: document.getElementById("nextPageBtn"),
  filterKind: document.getElementById("filterKind"),
  filterQ: document.getElementById("filterQ"),
  incomeTotal: document.getElementById("incomeTotal"),
  expenseTotal: document.getElementById("expenseTotal"),
  balanceTotal: document.getElementById("balanceTotal"),
  userAvatar: document.getElementById("userAvatar"),
  userName: document.getElementById("userName"),
  userHandle: document.getElementById("userHandle"),
  userMenuToggle: document.getElementById("userMenuToggle"),
  userMenu: document.getElementById("userMenu"),
  logoutBtn: document.getElementById("logoutBtn"),
  openSettingsBtn: document.getElementById("openSettingsBtn"),
  editModal: document.getElementById("editModal"),
  closeEditModalBtn: document.getElementById("closeEditModalBtn"),
  editOperationForm: document.getElementById("editOperationForm"),
};

function setStatus(message, isLogin = false) {
  if (isLogin) {
    el.loginOutput.textContent = message;
  } else {
    el.appOutput.textContent = message;
  }
}

function setDefaultDate() {
  const dateInput = document.getElementById("opDate");
  if (!dateInput.value) {
    dateInput.value = new Date().toISOString().slice(0, 10);
  }
}

function showLogin(message = "") {
  el.loginScreen.classList.remove("hidden");
  el.appShell.classList.add("hidden");
  if (message) {
    setStatus(message, true);
  }
}

function showApp() {
  el.loginScreen.classList.add("hidden");
  el.appShell.classList.remove("hidden");
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${state.token}`,
  };
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    logout(false);
    throw new Error("Сессия истекла, авторизуйся снова");
  }

  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }

  return data;
}

function toggleUserMenu(forceOpen) {
  const open = typeof forceOpen === "boolean" ? forceOpen : !el.userMenu.classList.contains("hidden");
  if (open) {
    el.userMenu.classList.add("hidden");
  } else {
    el.userMenu.classList.remove("hidden");
  }
}

function openEditModal(item) {
  state.editOperationId = item.id;
  document.getElementById("editKind").value = item.kind;
  document.getElementById("editAmount").value = item.amount;
  document.getElementById("editDate").value = item.operation_date;
  document.getElementById("editNote").value = item.note || "";
  el.editModal.classList.remove("hidden");
}

function closeEditModal() {
  state.editOperationId = null;
  el.editModal.classList.add("hidden");
}

async function devLogin() {
  const firstName = document.getElementById("firstName").value || "Dev";
  const username = document.getElementById("username").value || "dev_user";

  const data = await requestJson("/api/v1/auth/dev", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telegram_id: 100001, first_name: firstName, username }),
  });

  state.token = data.access_token;
  localStorage.setItem("access_token", state.token);
  setStatus("Авторизация успешна", true);
  await bootstrapApp();
}

async function loadMe() {
  const me = await requestJson("/api/v1/users/me", { headers: authHeaders() });
  const name = me.display_name || "User";
  el.userName.textContent = name;
  el.userHandle.textContent = `@${name.toLowerCase().replace(/\s+/g, "_")}`;
  el.userAvatar.textContent = name[0]?.toUpperCase() || "U";
}

async function loadPreferences() {
  const prefs = await requestJson("/api/v1/preferences", { headers: authHeaders() });
  state.preferences = prefs;

  const period = prefs.data?.dashboard?.period || "30d";
  el.dashboardPeriod.value = period;

  const opFilters = prefs.data?.operations?.filters || {};
  el.filterKind.value = opFilters.kind || "";
  el.filterQ.value = opFilters.q || "";
}

async function savePreferences() {
  if (!state.preferences) {
    return;
  }

  const payload = {
    preferences_version: state.preferences.preferences_version || 1,
    data: {
      ...state.preferences.data,
      dashboard: {
        ...(state.preferences.data?.dashboard || {}),
        period: el.dashboardPeriod.value,
      },
      operations: {
        ...(state.preferences.data?.operations || {}),
        filters: {
          kind: el.filterKind.value || "",
          q: el.filterQ.value.trim() || "",
        },
      },
    },
  };

  state.preferences = await requestJson("/api/v1/preferences", {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
}

async function loadDashboard() {
  const period = encodeURIComponent(el.dashboardPeriod.value);
  const data = await requestJson(`/api/v1/dashboard/summary?period=${period}`, { headers: authHeaders() });
  el.incomeTotal.textContent = data.income_total;
  el.expenseTotal.textContent = data.expense_total;
  el.balanceTotal.textContent = data.balance;
}

function buildOperationsQuery() {
  const params = new URLSearchParams();
  params.set("page", String(state.page));
  params.set("page_size", String(state.pageSize));
  params.set("sort_by", "operation_date");
  params.set("sort_dir", "desc");

  if (el.filterKind.value) {
    params.set("kind", el.filterKind.value);
  }
  const q = el.filterQ.value.trim();
  if (q) {
    params.set("q", q);
  }
  return params;
}

function renderOperations(items) {
  el.operationsBody.innerHTML = "";

  if (!items.length) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="5">Нет операций</td>';
    el.operationsBody.appendChild(row);
    return;
  }

  for (const item of items) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.operation_date}</td>
      <td>${item.kind}</td>
      <td>${item.amount}</td>
      <td>${item.note || ""}</td>
      <td>
        <div class="actions">
          <button class="btn btn-secondary" data-edit-id="${item.id}">Редактировать</button>
          <button class="btn btn-danger" data-delete-id="${item.id}">Удалить</button>
        </div>
      </td>
    `;
    row.dataset.item = JSON.stringify(item);
    el.operationsBody.appendChild(row);
  }
}

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  el.pageInfo.textContent = `Страница ${state.page} из ${totalPages} (${state.total})`;
  el.prevPageBtn.disabled = state.page <= 1;
  el.nextPageBtn.disabled = state.page >= totalPages;
}

async function loadOperations() {
  const data = await requestJson(`/api/v1/operations?${buildOperationsQuery().toString()}`, {
    headers: authHeaders(),
  });

  state.total = data.total;
  renderOperations(data.items);
  renderPagination();
}

async function createOperation(event) {
  event.preventDefault();

  const payload = {
    kind: document.getElementById("opKind").value,
    amount: document.getElementById("opAmount").value,
    operation_date: document.getElementById("opDate").value,
    note: document.getElementById("opNote").value,
  };

  await requestJson("/api/v1/operations", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });

  document.getElementById("opAmount").value = "";
  document.getElementById("opNote").value = "";

  state.page = 1;
  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus("Операция добавлена");
}

async function updateOperation(event) {
  event.preventDefault();
  if (!state.editOperationId) {
    return;
  }

  const payload = {
    kind: document.getElementById("editKind").value,
    amount: document.getElementById("editAmount").value,
    operation_date: document.getElementById("editDate").value,
    note: document.getElementById("editNote").value,
  };

  await requestJson(`/api/v1/operations/${state.editOperationId}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });

  closeEditModal();
  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus("Операция обновлена");
}

async function deleteOperation(id) {
  const response = await fetch(`/api/v1/operations/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${state.token}` },
  });

  if (!response.ok) {
    setStatus("Не удалось удалить операцию");
    return;
  }

  const totalPages = Math.max(1, Math.ceil((state.total - 1) / state.pageSize));
  if (state.page > totalPages) {
    state.page = totalPages;
  }

  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus(`Операция ${id} удалена`);
}

async function applyFilters() {
  state.page = 1;
  await savePreferences();
  await loadOperations();
  setStatus("Фильтры применены");
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus("Данные обновлены");
}

function logout(showMessage = true) {
  localStorage.removeItem("access_token");
  state.token = "";
  state.preferences = null;
  state.page = 1;
  state.total = 0;
  closeEditModal();
  toggleUserMenu(true);
  showLogin(showMessage ? "Вы вышли" : "");
}

async function bootstrapApp() {
  showApp();
  setDefaultDate();
  await loadMe();
  await loadPreferences();
  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus("Готово");
}

el.devLoginBtn.addEventListener("click", () => {
  devLogin().catch((error) => setStatus(String(error), true));
});

el.refreshBtn.addEventListener("click", () => {
  refreshAll().catch((error) => setStatus(String(error)));
});

el.dashboardPeriod.addEventListener("change", () => {
  savePreferences()
    .then(loadDashboard)
    .then(() => setStatus("Период сохранен"))
    .catch((error) => setStatus(String(error)));
});

el.applyFiltersBtn.addEventListener("click", () => {
  applyFilters().catch((error) => setStatus(String(error)));
});

el.createForm.addEventListener("submit", (event) => {
  createOperation(event).catch((error) => setStatus(String(error)));
});

el.operationsBody.addEventListener("click", (event) => {
  const deleteBtn = event.target.closest("button[data-delete-id]");
  if (deleteBtn) {
    deleteOperation(deleteBtn.dataset.deleteId).catch((error) => setStatus(String(error)));
    return;
  }

  const editBtn = event.target.closest("button[data-edit-id]");
  if (!editBtn) {
    return;
  }

  const row = editBtn.closest("tr");
  const item = row ? JSON.parse(row.dataset.item || "{}") : null;
  if (item?.id) {
    openEditModal(item);
  }
});

el.prevPageBtn.addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    loadOperations().catch((error) => setStatus(String(error)));
  }
});

el.nextPageBtn.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  if (state.page < totalPages) {
    state.page += 1;
    loadOperations().catch((error) => setStatus(String(error)));
  }
});

el.userMenuToggle.addEventListener("click", () => toggleUserMenu());
el.logoutBtn.addEventListener("click", () => logout(true));
el.openSettingsBtn.addEventListener("click", () => {
  toggleUserMenu(true);
  setStatus("Раздел настроек будет добавлен следующим шагом");
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".user-area")) {
    toggleUserMenu(true);
  }
});

el.closeEditModalBtn.addEventListener("click", closeEditModal);
el.editOperationForm.addEventListener("submit", (event) => {
  updateOperation(event).catch((error) => setStatus(String(error)));
});
el.editModal.addEventListener("click", (event) => {
  if (event.target === el.editModal) {
    closeEditModal();
  }
});

if (state.token) {
  bootstrapApp().catch((error) => showLogin(String(error)));
} else {
  showLogin();
}
