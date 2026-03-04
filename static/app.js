const state = {
  token: localStorage.getItem("access_token") || "",
  preferences: null,
};

const loginScreen = document.getElementById("loginScreen");
const appShell = document.getElementById("appShell");
const loginOutput = document.getElementById("loginOutput");
const appOutput = document.getElementById("appOutput");

const devLoginBtn = document.getElementById("devLoginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const refreshBtn = document.getElementById("refreshBtn");
const dashboardPeriod = document.getElementById("dashboardPeriod");
const createOperationForm = document.getElementById("createOperationForm");
const applyFiltersBtn = document.getElementById("applyFilters");

const incomeTotal = document.getElementById("incomeTotal");
const expenseTotal = document.getElementById("expenseTotal");
const balanceTotal = document.getElementById("balanceTotal");
const operationsBody = document.getElementById("operationsBody");

const userAvatar = document.getElementById("userAvatar");
const userName = document.getElementById("userName");
const userHandle = document.getElementById("userHandle");

function setDefaultDate() {
  const el = document.getElementById("opDate");
  if (!el.value) {
    const now = new Date();
    el.value = now.toISOString().slice(0, 10);
  }
}

function showLogin(message) {
  loginScreen.classList.remove("hidden");
  appShell.classList.add("hidden");
  if (message) {
    loginOutput.textContent = message;
  }
}

function showApp() {
  loginScreen.classList.add("hidden");
  appShell.classList.remove("hidden");
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${state.token}`,
  };
}

async function requestJson(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    state.token = "";
    showLogin("Сессия истекла. Войди снова.");
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    throw new Error(data.detail || JSON.stringify(data));
  }

  return data;
}

async function devLogin() {
  const firstName = document.getElementById("firstName").value || "Dev";
  const username = document.getElementById("username").value || "dev_user";

  const data = await requestJson("/api/v1/auth/dev", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      first_name: firstName,
      username,
      telegram_id: 100001,
    }),
  });

  state.token = data.access_token;
  localStorage.setItem("access_token", state.token);
  loginOutput.textContent = "Авторизация успешна";
  await bootstrapApp();
}

async function loadMe() {
  const me = await requestJson("/api/v1/users/me", {
    headers: authHeaders(),
  });

  const name = me.display_name || "User";
  userName.textContent = name;
  userHandle.textContent = `@${name.toLowerCase().replace(/\s+/g, "_")}`;
  userAvatar.textContent = name.slice(0, 1).toUpperCase();
}

async function loadPreferences() {
  const prefs = await requestJson("/api/v1/preferences", {
    headers: authHeaders(),
  });
  state.preferences = prefs;

  const period = prefs.data?.dashboard?.period || "30d";
  dashboardPeriod.value = period;

  const opFilters = prefs.data?.operations?.filters || {};
  document.getElementById("filterKind").value = opFilters.kind || "";
  document.getElementById("filterQ").value = opFilters.q || "";
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
        period: dashboardPeriod.value,
      },
      operations: {
        ...(state.preferences.data?.operations || {}),
        filters: {
          kind: document.getElementById("filterKind").value || "",
          q: document.getElementById("filterQ").value || "",
        },
      },
    },
  };

  const saved = await requestJson("/api/v1/preferences", {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  state.preferences = saved;
}

async function loadDashboard() {
  const period = dashboardPeriod.value;
  const data = await requestJson(`/api/v1/dashboard/summary?period=${encodeURIComponent(period)}`, {
    headers: authHeaders(),
  });

  incomeTotal.textContent = data.income_total;
  expenseTotal.textContent = data.expense_total;
  balanceTotal.textContent = data.balance;
}

async function loadOperations() {
  const params = new URLSearchParams();
  params.set("page", "1");
  params.set("page_size", "20");
  params.set("sort_by", "operation_date");
  params.set("sort_dir", "desc");

  const kind = document.getElementById("filterKind").value;
  const q = document.getElementById("filterQ").value.trim();
  if (kind) {
    params.set("kind", kind);
  }
  if (q) {
    params.set("q", q);
  }

  const data = await requestJson(`/api/v1/operations?${params.toString()}`, {
    headers: authHeaders(),
  });

  operationsBody.innerHTML = "";
  if (!data.items.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="5">Нет операций</td>';
    operationsBody.appendChild(tr);
    return;
  }

  for (const item of data.items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.operation_date}</td>
      <td>${item.kind}</td>
      <td>${item.amount}</td>
      <td>${item.note || ""}</td>
      <td><button class="danger" data-delete-id="${item.id}">Удалить</button></td>
    `;
    operationsBody.appendChild(tr);
  }
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

  await Promise.all([loadDashboard(), loadOperations()]);
  appOutput.textContent = "Операция добавлена";
}

async function handleDeleteClick(event) {
  const btn = event.target.closest("button[data-delete-id]");
  if (!btn) {
    return;
  }

  const id = btn.getAttribute("data-delete-id");
  await fetch(`/api/v1/operations/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${state.token}` },
  });

  await Promise.all([loadDashboard(), loadOperations()]);
  appOutput.textContent = `Операция ${id} удалена`;
}

async function refreshAll() {
  try {
    await Promise.all([loadDashboard(), loadOperations()]);
    appOutput.textContent = "Данные обновлены";
  } catch (err) {
    appOutput.textContent = String(err);
  }
}

async function applyFilters() {
  try {
    await savePreferences();
    await loadOperations();
    appOutput.textContent = "Фильтры применены";
  } catch (err) {
    appOutput.textContent = String(err);
  }
}

async function onPeriodChange() {
  try {
    await savePreferences();
    await loadDashboard();
    appOutput.textContent = "Период сохранен";
  } catch (err) {
    appOutput.textContent = String(err);
  }
}

async function bootstrapApp() {
  try {
    showApp();
    setDefaultDate();
    await loadMe();
    await loadPreferences();
    await Promise.all([loadDashboard(), loadOperations()]);
    appOutput.textContent = "Готово";
  } catch (err) {
    showLogin(String(err));
  }
}

function logout() {
  localStorage.removeItem("access_token");
  state.token = "";
  showLogin("Вы вышли из аккаунта");
}

devLoginBtn.addEventListener("click", () => {
  devLogin().catch((err) => {
    loginOutput.textContent = String(err);
  });
});

logoutBtn.addEventListener("click", logout);
refreshBtn.addEventListener("click", () => {
  refreshAll();
});
createOperationForm.addEventListener("submit", (event) => {
  createOperation(event).catch((err) => {
    appOutput.textContent = String(err);
  });
});
applyFiltersBtn.addEventListener("click", () => {
  applyFilters();
});
dashboardPeriod.addEventListener("change", () => {
  onPeriodChange();
});
operationsBody.addEventListener("click", (event) => {
  handleDeleteClick(event).catch((err) => {
    appOutput.textContent = String(err);
  });
});

if (state.token) {
  bootstrapApp();
} else {
  showLogin();
}
