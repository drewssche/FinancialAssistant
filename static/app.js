const state = {
  token: localStorage.getItem("access_token") || "",
  preferences: null,
  page: 1,
  pageSize: 10,
  total: 0,
  editOperationId: null,
  period: "30d",
  filterKind: "",
};

const el = {
  loginScreen: document.getElementById("loginScreen"),
  appShell: document.getElementById("appShell"),
  loginOutput: document.getElementById("loginOutput"),
  appOutput: document.getElementById("appOutput"),
  devLoginBtn: document.getElementById("devLoginBtn"),
  periodTabs: document.getElementById("periodTabs"),
  kindFilters: document.getElementById("kindFilters"),
  refreshBtn: document.getElementById("refreshBtn"),
  applyFiltersBtn: document.getElementById("applyFilters"),
  filterQ: document.getElementById("filterQ"),
  addOperationCta: document.getElementById("addOperationCta"),
  batchOperationCta: document.getElementById("batchOperationCta"),
  operationsBody: document.getElementById("operationsBody"),
  pageInfo: document.getElementById("pageInfo"),
  prevPageBtn: document.getElementById("prevPageBtn"),
  nextPageBtn: document.getElementById("nextPageBtn"),
  incomeTotal: document.getElementById("incomeTotal"),
  expenseTotal: document.getElementById("expenseTotal"),
  balanceTotal: document.getElementById("balanceTotal"),
  userAvatar: document.getElementById("userAvatar"),
  userName: document.getElementById("userName"),
  userHandle: document.getElementById("userHandle"),
  userMenuToggle: document.getElementById("userMenuToggle"),
  userMenu: document.getElementById("userMenu"),
  openSettingsBtn: document.getElementById("openSettingsBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  createModal: document.getElementById("createModal"),
  closeCreateModalBtn: document.getElementById("closeCreateModalBtn"),
  createForm: document.getElementById("createOperationForm"),
  createKindSwitch: document.getElementById("createKindSwitch"),
  createPreviewBody: document.getElementById("createPreviewBody"),
  opKind: document.getElementById("opKind"),
  editModal: document.getElementById("editModal"),
  closeEditModalBtn: document.getElementById("closeEditModalBtn"),
  editForm: document.getElementById("editOperationForm"),
  editKindSwitch: document.getElementById("editKindSwitch"),
  editKind: document.getElementById("editKind"),
};

function setStatus(message, forLogin = false) {
  if (forLogin) {
    el.loginOutput.textContent = message;
    return;
  }
  el.appOutput.textContent = message;
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${state.token}`,
  };
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

function setDefaultDate() {
  const input = document.getElementById("opDate");
  if (!input.value) {
    input.value = new Date().toISOString().slice(0, 10);
  }
}

function closeAllMenus() {
  el.userMenu.classList.add("hidden");
}

function openCreateModal() {
  setDefaultDate();
  updateCreatePreview();
  el.createModal.classList.remove("hidden");
}

function closeCreateModal() {
  el.createModal.classList.add("hidden");
}

function openEditModal(item) {
  state.editOperationId = item.id;
  el.editKind.value = item.kind;
  document.getElementById("editAmount").value = item.amount;
  document.getElementById("editDate").value = item.operation_date;
  document.getElementById("editNote").value = item.note || "";
  syncSegmentedActive(el.editKindSwitch, "kind", item.kind);
  el.editModal.classList.remove("hidden");
}

function closeEditModal() {
  state.editOperationId = null;
  el.editModal.classList.add("hidden");
}

function syncSegmentedActive(container, attr, value) {
  if (!container) {
    return;
  }
  const buttons = container.querySelectorAll(`button[data-${attr}]`);
  for (const btn of buttons) {
    btn.classList.toggle("active", btn.dataset[attr] === value);
  }
}

function formatAmount(value) {
  const num = Number(value);
  if (Number.isNaN(num)) {
    return "0.00";
  }
  return num.toFixed(2);
}

function formatDateRu(value) {
  if (!value) {
    return "";
  }
  const [year, month, day] = String(value).split("-");
  if (!year || !month || !day) {
    return String(value);
  }
  return `${day}.${month}.${year}`;
}

function kindLabel(kind) {
  return kind === "income" ? "Доход" : "Расход";
}

function createOperationRow(item, options = {}) {
  const preview = options.preview === true;
  const kindClass = item.kind === "income" ? "income" : "expense";
  const row = document.createElement("tr");
  row.classList.add(`kind-row-${kindClass}`);
  row.innerHTML = `
    <td>${formatDateRu(item.operation_date)}</td>
    <td><span class="kind-pill kind-pill-${kindClass}">${kindLabel(item.kind)}</span></td>
    <td><span class="amount-${kindClass}">${item.amount}</span></td>
    <td>${item.note || ""}</td>
    <td>
      <div class="actions">
        <button class="btn btn-secondary" data-edit-id="${preview ? "" : item.id}" ${preview ? "disabled" : ""}>Редактировать</button>
        <button class="btn btn-danger" data-delete-id="${preview ? "" : item.id}" ${preview ? "disabled" : ""}>Удалить</button>
      </div>
    </td>
  `;
  if (preview) {
    row.classList.add("preview-row");
  } else {
    row.dataset.item = JSON.stringify(item);
  }
  return row;
}

function getCreateFormPreviewItem() {
  return {
    id: 0,
    operation_date: document.getElementById("opDate").value || new Date().toISOString().slice(0, 10),
    kind: el.opKind.value || "expense",
    amount: formatAmount(document.getElementById("opAmount").value),
    note: document.getElementById("opNote").value || "",
  };
}

function updateCreatePreview() {
  if (!el.createPreviewBody) {
    return;
  }
  el.createPreviewBody.innerHTML = "";
  el.createPreviewBody.appendChild(createOperationRow(getCreateFormPreviewItem(), { preview: true }));
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));

  if (response.status === 401) {
    logout(false);
    throw new Error("Сессия истекла, авторизуйся снова");
  }

  if (!response.ok) {
    throw new Error(data.detail || "Ошибка запроса");
  }

  return data;
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
  localStorage.setItem("access_token", data.access_token);
  setStatus("Авторизация успешна", true);
  await bootstrapApp();
}

async function loadMe() {
  const me = await requestJson("/api/v1/users/me", { headers: authHeaders() });
  const name = me.display_name || "Пользователь";
  el.userName.textContent = name;
  el.userHandle.textContent = `@${name.toLowerCase().replace(/\s+/g, "_")}`;
  el.userAvatar.textContent = name[0]?.toUpperCase() || "П";
}

async function loadPreferences() {
  const prefs = await requestJson("/api/v1/preferences", { headers: authHeaders() });
  state.preferences = prefs;

  state.period = prefs.data?.dashboard?.period || "30d";
  state.filterKind = prefs.data?.operations?.filters?.kind || "";
  el.filterQ.value = prefs.data?.operations?.filters?.q || "";

  syncSegmentedActive(el.periodTabs, "period", state.period);
  syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
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
        period: state.period,
      },
      operations: {
        ...(state.preferences.data?.operations || {}),
        filters: {
          kind: state.filterKind,
          q: el.filterQ.value.trim(),
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
  const data = await requestJson(`/api/v1/dashboard/summary?period=${encodeURIComponent(state.period)}`, {
    headers: authHeaders(),
  });
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

  if (state.filterKind) {
    params.set("kind", state.filterKind);
  }

  const q = el.filterQ.value.trim();
  if (q) {
    params.set("q", q);
  }

  return params;
}

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  el.pageInfo.textContent = `Страница ${state.page} из ${totalPages} (${state.total})`;
  el.prevPageBtn.disabled = state.page <= 1;
  el.nextPageBtn.disabled = state.page >= totalPages;
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
    const row = createOperationRow(item);
    el.operationsBody.appendChild(row);
  }
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
    kind: el.opKind.value,
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
  updateCreatePreview();
  state.page = 1;

  closeCreateModal();
  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus("Операция добавлена");
}

async function updateOperation(event) {
  event.preventDefault();
  if (!state.editOperationId) {
    return;
  }

  const payload = {
    kind: el.editKind.value,
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
  closeCreateModal();
  closeEditModal();
  closeAllMenus();
  showLogin(showMessage ? "Вы вышли" : "");
}

async function bootstrapApp() {
  showApp();
  await loadMe();
  await loadPreferences();
  await Promise.all([loadDashboard(), loadOperations()]);
  setStatus("Готово");
}

el.devLoginBtn.addEventListener("click", () => {
  devLogin().catch((err) => setStatus(String(err), true));
});

el.addOperationCta.addEventListener("click", openCreateModal);
el.batchOperationCta.addEventListener("click", () => {
  setStatus("Массовое добавление будет следующим шагом");
});

el.closeCreateModalBtn.addEventListener("click", closeCreateModal);
el.createModal.addEventListener("click", (event) => {
  if (event.target === el.createModal) {
    closeCreateModal();
  }
});

el.closeEditModalBtn.addEventListener("click", closeEditModal);
el.editModal.addEventListener("click", (event) => {
  if (event.target === el.editModal) {
    closeEditModal();
  }
});

el.createForm.addEventListener("submit", (event) => {
  createOperation(event).catch((err) => setStatus(String(err)));
});

el.editForm.addEventListener("submit", (event) => {
  updateOperation(event).catch((err) => setStatus(String(err)));
});

el.refreshBtn.addEventListener("click", () => {
  refreshAll().catch((err) => setStatus(String(err)));
});

el.applyFiltersBtn.addEventListener("click", () => {
  applyFilters().catch((err) => setStatus(String(err)));
});

el.periodTabs.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-period]");
  if (!btn) {
    return;
  }

  state.period = btn.dataset.period;
  syncSegmentedActive(el.periodTabs, "period", state.period);

  savePreferences()
    .then(loadDashboard)
    .then(() => setStatus("Период сохранен"))
    .catch((err) => setStatus(String(err)));
});

el.kindFilters.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-kind]");
  if (!btn) {
    return;
  }

  state.filterKind = btn.dataset.kind;
  syncSegmentedActive(el.kindFilters, "kind", state.filterKind);
});

el.createKindSwitch.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-kind]");
  if (!btn) {
    return;
  }

  el.opKind.value = btn.dataset.kind;
  syncSegmentedActive(el.createKindSwitch, "kind", el.opKind.value);
  updateCreatePreview();
});

el.editKindSwitch.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-kind]");
  if (!btn) {
    return;
  }

  el.editKind.value = btn.dataset.kind;
  syncSegmentedActive(el.editKindSwitch, "kind", el.editKind.value);
});

el.operationsBody.addEventListener("click", (event) => {
  const deleteBtn = event.target.closest("button[data-delete-id]");
  if (deleteBtn) {
    deleteOperation(deleteBtn.dataset.deleteId).catch((err) => setStatus(String(err)));
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
    loadOperations().catch((err) => setStatus(String(err)));
  }
});

el.nextPageBtn.addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  if (state.page < totalPages) {
    state.page += 1;
    loadOperations().catch((err) => setStatus(String(err)));
  }
});

el.userMenuToggle.addEventListener("click", () => {
  el.userMenu.classList.toggle("hidden");
});

el.openSettingsBtn.addEventListener("click", () => {
  closeAllMenus();
  setStatus("Раздел настроек будет следующим шагом");
});

el.logoutBtn.addEventListener("click", () => logout(true));

document.addEventListener("click", (event) => {
  if (!event.target.closest(".user-area")) {
    closeAllMenus();
  }
});

for (const id of ["opAmount", "opDate", "opNote"]) {
  const node = document.getElementById(id);
  if (node) {
    node.addEventListener("input", updateCreatePreview);
    node.addEventListener("change", updateCreatePreview);
  }
}

if (state.token) {
  bootstrapApp().catch((err) => showLogin(String(err)));
} else {
  showLogin();
}
