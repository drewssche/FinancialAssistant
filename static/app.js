import { createTableController } from "/static/table_pattern.js";

const categoryMap = window.bootstrapData?.categoryMap || { income: [], expense: [] };
const categoryMeta = { income: {}, expense: {} };
const groupedCategories = { income: [], expense: [] };
const today = window.bootstrapData?.today || "";
let summaryState = window.bootstrapData?.summary || {
  period: "day",
  selected_date: today,
  totals: { income: 0, expense: 0, balance: 0 },
  income_rows: [],
  expense_rows: [],
};

const modal = document.getElementById("tx-modal");
const modalShell = modal?.querySelector(".modal-shell");
const modalTitle = document.getElementById("modal-title");
const openModalBtn = document.getElementById("open-modal");
const closeModalBtn = document.getElementById("close-modal");

const txForm = document.getElementById("tx-form");
const saveBtn = document.getElementById("save-btn");
const deleteBtn = document.getElementById("delete-btn");

const kindInput = document.getElementById("kind");
const kindSwitch = document.getElementById("kind-switch");

const subcategoryInput = document.getElementById("subcategory");
const subcategorySearch = document.getElementById("subcategory-search");
const subcategoryQuick = document.getElementById("subcategory-quick");
const subcategoryAll = document.getElementById("subcategory-all");
const subcategoryPopover = document.getElementById("subcategory-popover");
const createCategoryBtn = document.getElementById("create-category-btn");

const openCategoryManagerBtn = document.getElementById("open-category-manager");
const closeCategoryManagerBtn = document.getElementById("close-category-manager");
const addCategoryGroupBtn = document.getElementById("add-category-group");
const categoryManagerPanel = document.getElementById("category-manager-panel");
const categoryGroupsEl = document.getElementById("category-groups");
const managerEditor = document.getElementById("manager-editor");
const managerEditorTitle = document.getElementById("manager-editor-title");
const managerEditorCloseBtn = document.getElementById("manager-editor-close");
const editorNameInput = document.getElementById("editor-name");
const editorColorWrap = document.getElementById("editor-color-wrap");
const editorColorInput = document.getElementById("editor-color");
const editorIconWrap = document.getElementById("editor-icon-wrap");
const editorIconGrid = document.getElementById("editor-icon-grid");
const editorMoveWrap = document.getElementById("editor-move-wrap");
const editorGroupSelect = document.getElementById("editor-group-select");
const editorArchiveBtn = document.getElementById("editor-archive");
const editorDeleteBtn = document.getElementById("editor-delete");
const editorSaveBtn = document.getElementById("editor-save");

const accountInput = document.getElementById("account");
const accountChips = document.getElementById("account-chips");

const amountInput = document.getElementById("amount");
const occurredOnInput = document.getElementById("occurred_on");
const occurredOnText = document.getElementById("occurred_on_text");
const dateStrip = document.getElementById("date-strip");
const commentInput = document.getElementById("comment");
const txPreview = document.getElementById("tx-preview");
const previewKind = document.getElementById("preview-kind");
const previewSubcategory = document.getElementById("preview-subcategory");
const previewAmount = document.getElementById("preview-amount");
const previewAccount = document.getElementById("preview-account");
const previewDate = document.getElementById("preview-date");
const previewComment = document.getElementById("preview-comment");

const periodSwitch = document.getElementById("period-switch");
const selectedDateInput = document.getElementById("selected-date");
const periodLabel = document.getElementById("period-label");

const kpiIncome = document.getElementById("kpi-income");
const kpiExpense = document.getElementById("kpi-expense");
const kpiBalance = document.getElementById("kpi-balance");

const tableConfigs = {
  expense: {
    rowsEl: document.getElementById("expense-rows"),
    searchEl: document.getElementById("expense-search"),
    minEl: document.getElementById("expense-min"),
    sortEl: document.getElementById("expense-sort"),
    emptyText: "Нет расходов за выбранный период",
  },
  income: {
    rowsEl: document.getElementById("income-rows"),
    searchEl: document.getElementById("income-search"),
    minEl: document.getElementById("income-min"),
    sortEl: document.getElementById("income-sort"),
    emptyText: "Нет доходов за выбранный период",
  },
};

const tableControllers = {};
const GROUP_ICONS = ["📁", "🏠", "🍽️", "💊", "🛍️", "🎉", "🎁", "💼", "✨", "🚗", "🏋️", "📚", "🧾", "💡", "📱", "🧰", "🧴", "☕", "✈️", "🎮", "💸", "🧘", "🩺", "🛒"];

let currentPeriod = summaryState.period || "day";
let editOperationId = null;
let draggingCategoryId = null;
let draggingFromGroupId = null;
let draggingGroupId = null;
let iconPersistInFlight = false;
let managerEditorState = null;
let moreAnchorBtn = null;

const chipMeasure = document.createElement("span");
chipMeasure.className = "btn btn--chip";
chipMeasure.style.position = "absolute";
chipMeasure.style.visibility = "hidden";
chipMeasure.style.pointerEvents = "none";
chipMeasure.style.whiteSpace = "nowrap";
document.body.appendChild(chipMeasure);

function fmt(value) {
  return Number(value).toFixed(2);
}

function setButtonLoading(btn, loading, loadingText = "") {
  if (!btn) return;
  if (!btn.dataset.defaultText) btn.dataset.defaultText = btn.textContent || "";
  btn.disabled = loading;
  btn.classList.toggle("is-loading", loading);
  if (loading && loadingText) btn.textContent = loadingText;
  if (!loading) btn.textContent = btn.dataset.defaultText;
}

function formatDate(isoDate) {
  const d = new Date(`${isoDate}T00:00:00`);
  return d.toLocaleDateString("ru-RU");
}

function formatShortDate(isoDate) {
  const d = new Date(`${isoDate}T00:00:00`);
  const weekday = d.toLocaleDateString("ru-RU", { weekday: "short" });
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${weekday}. ${day}.${month}`;
}

function measureTextChipWidth(label) {
  chipMeasure.innerHTML = `<span>${escapeHtml(label)}</span>`;
  return Math.ceil(chipMeasure.getBoundingClientRect().width) + 8;
}

function toIsoLocal(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function minskTodayIso() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Europe/Minsk",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const y = parts.find((p) => p.type === "year")?.value || "1970";
  const m = parts.find((p) => p.type === "month")?.value || "01";
  const d = parts.find((p) => p.type === "day")?.value || "01";
  return `${y}-${m}-${d}`;
}

function addDaysIso(isoDate, offset) {
  const base = new Date(`${isoDate}T00:00:00`);
  base.setDate(base.getDate() + offset);
  return toIsoLocal(base);
}

function renderDateStrip() {
  if (!dateStrip) return;
  dateStrip.innerHTML = "";

  const selected = occurredOnInput.value || today;
  const todayMinsk = minskTodayIso();
  const available = Math.max(180, dateStrip.clientWidth - 4);
  const gap = 8;
  const pickOffsets = (count) => {
    const half = Math.floor(count / 2);
    const arr = [];
    for (let i = -half; i <= half; i += 1) arr.push(i);
    return arr;
  };
  const canFit = (offsets) => {
    let total = 0;
    offsets.forEach((offset, idx) => {
      const iso = addDaysIso(selected, offset);
      const label = iso === todayMinsk ? "Сегодня" : formatShortDate(iso);
      total += measureTextChipWidth(label);
      if (idx > 0) total += gap;
    });
    return total <= available;
  };

  let offsets = pickOffsets(7);
  if (!canFit(offsets)) offsets = pickOffsets(5);
  if (!canFit(offsets)) offsets = pickOffsets(3);

  offsets.forEach((offset) => {
    const iso = addDaysIso(selected, offset);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn--chip date-strip-chip";
    btn.dataset.date = iso;
    btn.classList.toggle("active", iso === selected);
    btn.classList.toggle("today", iso === todayMinsk);
    btn.textContent = iso === todayMinsk ? "Сегодня" : formatShortDate(iso);
    btn.addEventListener("click", () => setOccurredDate(iso));
    dateStrip.appendChild(btn);
  });
}

function weekRange(isoDate) {
  const day = new Date(`${isoDate}T00:00:00`);
  const weekday = (day.getDay() + 6) % 7;
  const start = new Date(day);
  start.setDate(day.getDate() - weekday);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return {
    start: toIsoLocal(start),
    end: toIsoLocal(end),
  };
}

function updatePeriodLabel() {
  if (currentPeriod === "day") {
    periodLabel.textContent = `День: ${formatDate(selectedDateInput.value)}`;
    return;
  }
  const r = weekRange(selectedDateInput.value);
  periodLabel.textContent = `Неделя (Пн-Вс): ${formatDate(r.start)} - ${formatDate(r.end)}`;
}

function showModal(el, show) {
  el.classList.toggle("open", show);
  el.setAttribute("aria-hidden", show ? "false" : "true");
  if (show) {
    setCategoryManagerOpen(false);
    closeManagerEditor();
    closeSubcategoryPopover();
  }
  if (!show) {
    setCategoryManagerOpen(false);
    closeManagerEditor();
    closeSubcategoryPopover();
  }
}

function setOccurredDate(isoDate) {
  occurredOnInput.value = isoDate;
  if (occurredOnText) {
    const todayMinsk = minskTodayIso();
    occurredOnText.textContent = isoDate === todayMinsk ? `${formatDate(isoDate)} · Сегодня` : formatDate(isoDate);
    occurredOnText.classList.toggle("is-today", isoDate === todayMinsk);
  }
  renderDateStrip();
  updatePreview();
}

function setCategoryManagerOpen(open) {
  categoryManagerPanel.hidden = !open;
  if (open) {
    modalShell?.classList.add("manager-open");
  } else {
    modalShell?.classList.remove("manager-open");
  }
}

function usageKey(kind) {
  return `fa_category_usage_${kind}`;
}

function getUsage(kind) {
  try {
    return JSON.parse(localStorage.getItem(usageKey(kind)) || "{}");
  } catch {
    return {};
  }
}

function bumpUsage(kind, name) {
  const usage = getUsage(kind);
  usage[name] = (usage[name] || 0) + 1;
  localStorage.setItem(usageKey(kind), JSON.stringify(usage));
}

function sortByUsage(kind, list) {
  const usage = getUsage(kind);
  return [...list].sort((a, b) => {
    const aScore = usage[a] || 0;
    const bScore = usage[b] || 0;
    if (aScore !== bScore) return bScore - aScore;
    const metaA = categoryMeta[kind]?.[a] || {};
    const metaB = categoryMeta[kind]?.[b] || {};
    const groupOrderA = Number(metaA.group_sort ?? 9999);
    const groupOrderB = Number(metaB.group_sort ?? 9999);
    if (groupOrderA !== groupOrderB) return groupOrderA - groupOrderB;
    const categoryOrderA = Number(metaA.category_sort ?? 9999);
    const categoryOrderB = Number(metaB.category_sort ?? 9999);
    if (categoryOrderA !== categoryOrderB) return categoryOrderA - categoryOrderB;
    return a.localeCompare(b, "ru");
  });
}

function sortByGroupCluster(kind, list) {
  return [...list].sort((a, b) => {
    const metaA = categoryMeta[kind]?.[a] || {};
    const metaB = categoryMeta[kind]?.[b] || {};
    const groupOrderA = Number(metaA.group_sort ?? 9999);
    const groupOrderB = Number(metaB.group_sort ?? 9999);
    if (groupOrderA !== groupOrderB) return groupOrderA - groupOrderB;

    const categoryOrderA = Number(metaA.category_sort ?? 9999);
    const categoryOrderB = Number(metaB.category_sort ?? 9999);
    if (categoryOrderA !== categoryOrderB) return categoryOrderA - categoryOrderB;

    return a.localeCompare(b, "ru");
  });
}

function updateKpi() {
  kpiIncome.textContent = fmt(summaryState.totals?.income || 0);
  kpiExpense.textContent = fmt(summaryState.totals?.expense || 0);
  kpiBalance.textContent = fmt(summaryState.totals?.balance || 0);
}

function accountIconSvg(account, iconClass = "op-chip-icon") {
  if (account === "Карта") {
    return `<svg class="${iconClass}" viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="6" width="17" height="12" rx="2.5" ry="2.5" fill="none" stroke="currentColor" stroke-width="1.8"></rect><line x1="4.5" y1="10" x2="19.5" y2="10" stroke="currentColor" stroke-width="1.8"></line></svg>`;
  }
  return `<svg class="${iconClass}" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7.2" fill="none" stroke="currentColor" stroke-width="1.8"></circle><line x1="12" y1="8.3" x2="12" y2="15.7" stroke="currentColor" stroke-width="1.8"></line><line x1="9.3" y1="10.2" x2="14.6" y2="10.2" stroke="currentColor" stroke-width="1.8"></line><line x1="9.3" y1="13.8" x2="14.6" y2="13.8" stroke="currentColor" stroke-width="1.8"></line></svg>`;
}

function kindIcon(kind) {
  return kind === "income" ? "↗" : "↘";
}

function kindChipHtml(kind) {
  const kindClass = kind === "income" ? "income" : "expense";
  const label = kind === "income" ? "Доход" : "Расход";
  return `<span class="op-chip op-chip--kind ${kindClass}"><span class="op-chip-kind-icon">${kindIcon(kind)}</span><span>${label}</span></span>`;
}

function accountChipHtml(account) {
  return `<span class="op-chip op-chip--account">${accountIconSvg(account)}<span>${escapeHtml(account)}</span></span>`;
}

function amountChipHtml(amount) {
  return `<span class="op-chip op-chip--amount"><span class="op-chip-icon">💰</span><span>${escapeHtml(amount)}</span></span>`;
}

function dateChipHtml(isoDate) {
  return `<span class="op-chip op-chip--date"><span class="op-chip-icon">📅</span><span>${escapeHtml(formatDate(isoDate))}</span></span>`;
}

function categoryIcon(kind, subcategory) {
  const meta = categoryMeta[kind]?.[subcategory];
  return meta?.icon || "";
}

function categoryChipHtml(kind, subcategory) {
  const raw = subcategory || "—";
  const icon = categoryIcon(kind, raw);
  const iconHtml = icon ? `<span class="op-chip-icon">${escapeHtml(icon)}</span>` : "";
  return `<span class="op-chip op-chip--category" data-kind="${escapeAttr(kind)}" data-subcategory="${escapeAttr(raw)}">${iconHtml}<span>${escapeHtml(raw)}</span></span>`;
}

function applyCategoryAccentToElement(el) {
  if (!el) return;
  const kind = el.dataset.kind || kindInput.value;
  const subcategory = el.dataset.subcategory || "";
  const meta = categoryMeta[kind]?.[subcategory];
  if (meta?.color) {
    el.style.setProperty("--chip-accent", meta.color);
  } else {
    el.style.removeProperty("--chip-accent");
  }
}

function decorateRecentOperationChips() {
  document.querySelectorAll(".op-chip--category[data-subcategory]").forEach((el) => {
    const kind = el.dataset.kind || "expense";
    const subcategory = el.dataset.subcategory || "";
    const icon = categoryIcon(kind, subcategory);
    if (icon) {
      el.innerHTML = `<span class="op-chip-icon">${escapeHtml(icon)}</span><span>${escapeHtml(subcategory)}</span>`;
    } else {
      el.innerHTML = `<span>${escapeHtml(subcategory)}</span>`;
    }
    applyCategoryAccentToElement(el);
  });
}

function updatePreview() {
  if (!previewKind) return;
  const kind = kindInput.value;
  const subcategory = subcategoryInput.value || "—";
  const amount = amountInput.value ? fmt(amountInput.value) : "0.00";
  const account = accountInput.value || "—";
  const dateValue = occurredOnInput.value || today;
  const comment = commentInput.value?.trim() || "";

  previewKind.innerHTML = kindChipHtml(kind);
  previewSubcategory.innerHTML = categoryChipHtml(kind, subcategory);
  applyCategoryAccentToElement(previewSubcategory.querySelector(".op-chip--category"));
  previewAmount.innerHTML = amountChipHtml(amount);
  previewAccount.innerHTML = accountChipHtml(account);
  previewDate.innerHTML = dateChipHtml(dateValue);
  previewComment.hidden = !comment;
  txPreview?.classList.toggle("kind-income", kind === "income");
  txPreview?.classList.toggle("kind-expense", kind === "expense");
  if (comment) {
    previewComment.textContent = truncateText(comment, 42);
    previewComment.title = comment;
  } else {
    previewComment.textContent = "";
    previewComment.removeAttribute("title");
  }
}

async function loadSummary() {
  const params = new URLSearchParams({
    period: currentPeriod,
    selected_date: selectedDateInput.value,
  });

  const resp = await fetch(`/api/summary?${params.toString()}`);
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert("Не удалось загрузить сводку");
    return;
  }

  summaryState = payload.data;
  updateKpi();
  updatePeriodLabel();
  Object.values(tableControllers).forEach((c) => c.render());
}

function setKind(kind) {
  kindInput.value = kind;
  kindSwitch.querySelectorAll("button[data-kind]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.kind === kind);
  });
  renderCategoryPicker();
  updatePreview();
}

function setAccount(account) {
  accountInput.value = account;
  accountChips.querySelectorAll("button[data-account]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.account === account);
  });
  updatePreview();
}

function measureChipWidth(label, kind = kindInput.value) {
  if (label.startsWith("Еще")) {
    chipMeasure.textContent = label;
  } else {
    const meta = categoryMeta[kind]?.[label];
    const icon = meta?.icon ? `<span class="chip-icon">${escapeHtml(meta.icon)}</span>` : "";
    chipMeasure.innerHTML = `${icon}<span>${escapeHtml(label)}</span>`;
  }
  return Math.ceil(chipMeasure.getBoundingClientRect().width) + 8;
}

function preferredGroupId(kind) {
  const selected = categoryMeta[kind]?.[subcategoryInput.value];
  if (selected?.group_id !== undefined) return selected.group_id;
  const firstReal = (groupedCategories[kind] || []).find((g) => !g.is_virtual);
  return firstReal?.id || null;
}

function normalizeGroupId(groupId) {
  if (!groupId || groupId === "__ungrouped__" || groupId === "null") return null;
  return groupId;
}

function positionSubcategoryPopover(anchorBtn = null) {
  const field = subcategoryQuick?.closest(".field");
  if (!field || !subcategoryPopover) return;
  const fieldRect = field.getBoundingClientRect();
  const anchorRect = (anchorBtn || moreAnchorBtn)?.getBoundingClientRect();
  const defaultLeft = 0;
  const anchorLeft = anchorRect ? Math.max(0, anchorRect.left - fieldRect.left) : defaultLeft;
  const anchorRight = anchorRect ? Math.max(0, anchorRect.right - fieldRect.left) : null;
  const anchorRightGap = anchorRect ? Math.max(0, fieldRect.right - anchorRect.right) : 0;
  const maxWidth = Math.min(760, window.innerWidth - 40, fieldRect.width);
  const desiredWidth = Math.max(520, Math.min(maxWidth, fieldRect.width + 180));
  const maxLeft = Math.max(0, fieldRect.width - desiredWidth);
  const fallbackLeft = Math.min(anchorLeft, maxLeft);

  const topBelow = (subcategoryQuick?.offsetTop || 0) + (subcategoryQuick?.offsetHeight || 0) + 8;
  const absoluteTopBelow = fieldRect.top + topBelow;
  const minBodyHeight = 220;
  const maxBodyHeight = 460;
  const belowSpace = window.innerHeight - absoluteTopBelow - 20;

  let bodyHeight = Math.max(minBodyHeight, Math.min(maxBodyHeight, belowSpace));
  let top = topBelow;

  if (belowSpace < minBodyHeight) {
    const aboveSpace = fieldRect.top + (subcategoryQuick?.offsetTop || 0) - 16;
    bodyHeight = Math.max(minBodyHeight, Math.min(maxBodyHeight, aboveSpace));
    top = Math.max(8, (subcategoryQuick?.offsetTop || 0) - bodyHeight - 56);
  }

  subcategoryPopover.style.width = `${desiredWidth}px`;
  if (anchorRight != null) {
    // Pin right edge to More-chip right edge and let popover expand left.
    subcategoryPopover.style.left = "auto";
    subcategoryPopover.style.right = `${anchorRightGap}px`;
  } else {
    subcategoryPopover.style.right = "auto";
    subcategoryPopover.style.left = `${fallbackLeft}px`;
  }
  subcategoryPopover.style.top = `${top}px`;
  subcategoryAll.style.maxHeight = `${bodyHeight}px`;
}

function closeSubcategoryPopover() {
  subcategoryPopover.hidden = true;
  moreAnchorBtn?.classList.remove("active");
  moreAnchorBtn = null;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function truncateText(text, maxLen) {
  const value = String(text || "");
  if (value.length <= maxLen) return value;
  return `${value.slice(0, maxLen - 1)}…`;
}

function withHighlight(text, query) {
  const q = (query || "").trim().toLowerCase();
  const src = text || "";
  if (!q) return escapeHtml(src);
  const idx = src.toLowerCase().indexOf(q);
  if (idx < 0) return escapeHtml(src);
  const before = escapeHtml(src.slice(0, idx));
  const hit = escapeHtml(src.slice(idx, idx + q.length));
  const after = escapeHtml(src.slice(idx + q.length));
  return `${before}<mark>${hit}</mark>${after}`;
}

function makeCategoryChip(name, opts = {}) {
  const { soft = false, more = false, query = "" } = opts;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `btn btn--chip${soft ? " chip-soft" : ""}${more ? " chip-more" : ""}`;
  if (!more) btn.dataset.subcategory = name;

  const kind = kindInput.value;
  const meta = categoryMeta[kind]?.[name];
  const icon = meta?.icon ? `<span class="chip-icon">${escapeHtml(meta.icon)}</span>` : "";
  btn.innerHTML = `${icon}<span>${withHighlight(name, query)}</span>`;
  if (meta?.color) {
    btn.style.setProperty("--chip-accent", meta.color);
    btn.classList.add("chip-accent");
  }

  if (more) {
    btn.dataset.more = "1";
    btn.addEventListener("click", () => {
      const willOpen = subcategoryPopover.hidden || moreAnchorBtn !== btn;
      moreAnchorBtn?.classList.remove("active");
      moreAnchorBtn = btn;
      btn.classList.toggle("active", willOpen);
      subcategoryPopover.hidden = !willOpen;
      if (!subcategoryPopover.hidden) {
        positionSubcategoryPopover(btn);
      } else {
        moreAnchorBtn = null;
      }
    });
  } else {
    btn.classList.toggle("active", subcategoryInput.value === name);
    btn.addEventListener("click", () => {
      subcategoryInput.value = name;
      closeSubcategoryPopover();
      renderCategoryPicker();
      updatePreview();
    });
  }
  return btn;
}

function renderCategoryPicker() {
  const kind = kindInput.value;
  const query = subcategorySearch.value.trim().toLowerCase();
  const list = categoryMap[kind] || [];
  const sorted = sortByUsage(kind, list);
  const filtered = sorted.filter((name) => name.toLowerCase().includes(query));

  if (!subcategoryInput.value || !list.includes(subcategoryInput.value)) {
    subcategoryInput.value = filtered[0] || sorted[0] || "";
  }
  updatePreview();

  subcategoryQuick.innerHTML = "";
  subcategoryAll.innerHTML = "";

  const available = Math.max(140, subcategoryQuick.clientWidth - 4);
  const moreWidth = measureChipWidth("Еще (99)") + 32;
  let used = 0;
  const quick = [];
  const more = [];

  filtered.forEach((name, idx) => {
    const chipW = measureChipWidth(name, kind) + 8;
    const remainingAfter = filtered.length - (idx + 1);
    const needMore = more.length > 0 || remainingAfter > 0;
    const cap = needMore ? available - moreWidth : available;

    if (used + chipW <= cap) {
      quick.push(name);
      used += chipW;
    } else {
      more.push(name);
    }
  });

  const renderQuickRow = () => {
    subcategoryQuick.innerHTML = "";
    quick.forEach((name) => subcategoryQuick.appendChild(makeCategoryChip(name, { query })));
    if (more.length > 0) {
      subcategoryQuick.appendChild(makeCategoryChip(`Еще (${more.length})`, { more: true }));
    } else {
      closeSubcategoryPopover();
    }
  };

  renderQuickRow();

  while (more.length > 0 && quick.length > 0 && subcategoryQuick.scrollWidth > subcategoryQuick.clientWidth) {
    more.unshift(quick.pop());
    renderQuickRow();
  }

  const clusteredMore = sortByGroupCluster(kind, more);
  clusteredMore.forEach((name) => subcategoryAll.appendChild(makeCategoryChip(name, { soft: true, query })));
  if (!subcategoryPopover.hidden) {
    positionSubcategoryPopover();
  }

  const rawQuery = subcategorySearch.value.trim();
  const canCreate = Boolean(rawQuery && filtered.length === 0);
  createCategoryBtn.hidden = !canCreate;
  createCategoryBtn.textContent = `Создать "${rawQuery}"`;
  if (canCreate) {
    subcategoryQuick.appendChild(createCategoryBtn);
  }
}

async function refreshCategories(kind) {
  const resp = await fetch(`/api/category-groups?kind=${kind}`);
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось загрузить категории");
    return false;
  }

  groupedCategories[kind] = payload.data;
  categoryMap[kind] = [];
  categoryMeta[kind] = {};

  payload.data.forEach((group, groupIdx) => {
    (group.categories || []).forEach((item, categoryIdx) => {
      categoryMap[kind].push(item.name);
      categoryMeta[kind][item.name] = {
        id: item.id,
        group_id: item.group_id,
        color: group.color,
        icon: item.icon || "",
        group_name: group.name,
        group_sort: Number(group.sort_order ?? groupIdx),
        category_sort: Number(item.sort_order ?? categoryIdx),
      };
    });
  });

  decorateRecentOperationChips();
  return true;
}

async function createCategoryFromSearch() {
  const name = subcategorySearch.value.trim();
  if (!name) return;

  const resp = await fetch("/api/categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind: kindInput.value, name, group_id: preferredGroupId(kindInput.value) }),
  });
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось создать категорию");
    return;
  }

  await refreshCategories(kindInput.value);
  subcategoryInput.value = payload.data.name;
  subcategorySearch.value = "";
  renderCategoryPicker();
  updatePreview();
  if (!categoryManagerPanel.hidden) renderCategoryManager();
}

function groupActionChip(icon, title) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn--ghost action-chip";
  btn.textContent = icon;
  btn.title = title;
  btn.setAttribute("aria-label", title);
  return btn;
}

function closeManagerEditor() {
  managerEditorState = null;
  managerEditor.hidden = true;
}

async function persistEditorIcon(icon) {
  if (!managerEditorState || managerEditorState.mode !== "edit" || !managerEditorState.item || iconPersistInFlight) {
    return true;
  }
  const isGroup = managerEditorState.type === "group";
  iconPersistInFlight = true;
  editorIconGrid?.classList.add("is-loading");
  try {
    const resp = await fetch(
      isGroup ? `/api/category-groups/${managerEditorState.item.id}` : `/api/categories/${managerEditorState.item.id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isGroup ? { icon: icon || "📁" } : { icon }),
      },
    );
    const payload = await resp.json();
    if (!resp.ok || !payload.ok) {
      alert(payload.detail || "Не удалось обновить иконку");
      return false;
    }
    managerEditorState.item.icon = payload.data?.icon ?? (isGroup ? (icon || "📁") : icon);
    await refreshCategories(kindInput.value);
    renderCategoryManager();
    renderCategoryPicker();
    updatePreview();
    return true;
  } finally {
    iconPersistInFlight = false;
    editorIconGrid?.classList.remove("is-loading");
  }
}

function renderIconPicker(selectedIcon = "", allowEmpty = false, onSelect = null) {
  if (!editorIconGrid) return;
  editorIconGrid.innerHTML = "";
  const icons = allowEmpty ? ["", ...GROUP_ICONS] : GROUP_ICONS;
  let activeIcon = selectedIcon;

  const applyActive = () => {
    editorIconGrid.querySelectorAll(".icon-option").forEach((node) => {
      node.classList.toggle("active", node.dataset.icon === activeIcon);
    });
  };

  icons.forEach((icon) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn--chip icon-option";
    btn.textContent = icon || "∅";
    btn.dataset.icon = icon;
    btn.classList.toggle("active", activeIcon === icon);
    btn.title = icon || "Без иконки";
    btn.addEventListener("click", async () => {
      if (iconPersistInFlight || activeIcon === icon) return;
      const prevIcon = activeIcon;
      activeIcon = icon;
      applyActive();
      if (!onSelect) return;
      const ok = await onSelect(icon, prevIcon);
      if (!ok) {
        activeIcon = prevIcon;
        applyActive();
      }
    });
    editorIconGrid.appendChild(btn);
  });
}

function selectedIcon() {
  return editorIconGrid?.querySelector(".icon-option.active")?.dataset.icon || "";
}

function openGroupEditor(group = null) {
  managerEditorState = {
    type: "group",
    mode: group ? "edit" : "create",
    item: group,
  };
  managerEditorTitle.textContent = group ? `Группа: ${group.name}` : "Новая группа";
  editorNameInput.value = group?.name || "";
  editorColorInput.value = group?.color || "#7aa7ff";
  editorColorWrap.hidden = false;
  editorIconWrap.hidden = false;
  renderIconPicker(group?.icon || "📁", false, persistEditorIcon);
  editorMoveWrap.hidden = true;
  editorDeleteBtn.hidden = !group;
  editorArchiveBtn.hidden = !group;
  editorArchiveBtn.textContent = "Архивировать";
  editorSaveBtn.textContent = group ? "Сохранить" : "Создать";
  managerEditor.hidden = false;
  editorNameInput.focus();
}

function openCategoryEditor(category, group) {
  managerEditorState = {
    type: "category",
    mode: "edit",
    item: category,
  };
  managerEditorTitle.textContent = `Категория: ${category.name}`;
  editorNameInput.value = category.name;
  editorColorWrap.hidden = true;
  editorIconWrap.hidden = false;
  renderIconPicker(category?.icon || "", true, persistEditorIcon);
  editorMoveWrap.hidden = false;
  editorDeleteBtn.hidden = false;
  editorArchiveBtn.hidden = false;
  editorArchiveBtn.textContent = "Архивировать";
  editorSaveBtn.textContent = "Сохранить";
  managerEditor.hidden = false;

  editorGroupSelect.innerHTML = "";
  const ungroupedOption = document.createElement("option");
  ungroupedOption.value = "";
  ungroupedOption.textContent = "Без группы";
  editorGroupSelect.appendChild(ungroupedOption);
  const groups = groupedCategories[kindInput.value] || [];
  groups.filter((g) => !g.is_virtual).forEach((g) => {
    const option = document.createElement("option");
    option.value = g.id;
    option.textContent = g.name;
    editorGroupSelect.appendChild(option);
  });
  editorGroupSelect.value = normalizeGroupId(category.group_id) || normalizeGroupId(group?.id) || "";
  editorNameInput.focus();
}

function openCreateCategoryEditor(group) {
  managerEditorState = {
    type: "category",
    mode: "create",
    item: null,
    targetGroupId: group?.id || null,
  };
  managerEditorTitle.textContent = "Новая категория";
  editorNameInput.value = "";
  editorColorWrap.hidden = true;
  editorIconWrap.hidden = false;
  renderIconPicker("", true);
  editorMoveWrap.hidden = false;
  editorDeleteBtn.hidden = true;
  editorArchiveBtn.hidden = true;
  editorSaveBtn.textContent = "Создать";
  managerEditor.hidden = false;

  editorGroupSelect.innerHTML = "";
  const ungroupedOption = document.createElement("option");
  ungroupedOption.value = "";
  ungroupedOption.textContent = "Без группы";
  editorGroupSelect.appendChild(ungroupedOption);
  const groups = groupedCategories[kindInput.value] || [];
  groups.filter((g) => !g.is_virtual).forEach((g) => {
    const option = document.createElement("option");
    option.value = g.id;
    option.textContent = g.name;
    editorGroupSelect.appendChild(option);
  });
  editorGroupSelect.value = normalizeGroupId(group?.id) || "";
  editorNameInput.focus();
}

async function saveManagerEditor() {
  if (!managerEditorState) return;
  const name = editorNameInput.value.trim();
  if (!name || name.length < 2) {
    alert("Название должно быть не короче 2 символов");
    return;
  }

  setButtonLoading(editorSaveBtn, true, managerEditorState.mode === "create" ? "Создание..." : "Сохранение...");
  let resp;
  if (managerEditorState.type === "group") {
    const payload = { name, color: editorColorInput.value || "#7aa7ff", icon: selectedIcon() || "📁" };
    resp = managerEditorState.mode === "create"
      ? await fetch("/api/category-groups", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind: kindInput.value, ...payload }),
        })
      : await fetch(`/api/category-groups/${managerEditorState.item.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
  } else {
    const groupId = normalizeGroupId(editorGroupSelect.value);
    resp = managerEditorState.mode === "create"
      ? await fetch("/api/categories", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind: kindInput.value, name, group_id: groupId, icon: selectedIcon() }),
        })
      : await fetch(`/api/categories/${managerEditorState.item.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, group_id: groupId, icon: selectedIcon() }),
        });
  }

  const payload = await resp.json();
  setButtonLoading(editorSaveBtn, false);
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось сохранить");
    return;
  }

  await refreshCategories(kindInput.value);
  renderCategoryManager();
  renderCategoryPicker();
  closeManagerEditor();
}

async function deleteFromManagerEditor() {
  if (!managerEditorState || managerEditorState.mode !== "edit") return;
  const isGroup = managerEditorState.type === "group";
  const item = managerEditorState.item;
  if (!window.confirm(`Удалить ${isGroup ? "группу" : "категорию"} "${item.name}"?`)) return;

  setButtonLoading(editorDeleteBtn, true, "Удаление...");
  const resp = isGroup
    ? await fetch(`/api/category-groups/${item.id}`, { method: "DELETE" })
    : await fetch(`/api/categories/${item.id}`, { method: "DELETE" });
  const payload = await resp.json();
  setButtonLoading(editorDeleteBtn, false);

  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось удалить");
    return;
  }

  await refreshCategories(kindInput.value);
  renderCategoryManager();
  renderCategoryPicker();
  closeManagerEditor();
}

async function archiveFromManagerEditor() {
  if (!managerEditorState || managerEditorState.mode !== "edit") return;
  const isGroup = managerEditorState.type === "group";
  const item = managerEditorState.item;
  if (!window.confirm(`Архивировать ${isGroup ? "группу" : "категорию"} "${item.name}"?`)) return;

  setButtonLoading(editorArchiveBtn, true, "...");
  const resp = isGroup
    ? await fetch(`/api/category-groups/${item.id}/archive`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_archived: true }),
      })
    : await fetch(`/api/categories/${item.id}/archive`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_archived: true }),
      });
  const payload = await resp.json();
  setButtonLoading(editorArchiveBtn, false);
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось архивировать");
    return;
  }

  await refreshCategories(kindInput.value);
  renderCategoryManager();
  renderCategoryPicker();
  closeManagerEditor();
}

async function persistGroupOrder() {
  const ids = (groupedCategories[kindInput.value] || [])
    .filter((g) => !g.is_virtual)
    .map((g) => g.id);
  const resp = await fetch("/api/category-groups/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind: kindInput.value, group_ids: ids }),
  });
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось сохранить порядок групп");
    await refreshCategories(kindInput.value);
  }
}

async function persistCategoriesOrderFor(groupIds) {
  const groups = groupedCategories[kindInput.value] || [];
  const items = [];
  groups.forEach((group) => {
    if (!groupIds.includes(group.id)) return;
    (group.categories || []).forEach((item, idx) => {
      items.push({ id: item.id, group_id: normalizeGroupId(group.id), sort_order: idx });
    });
  });

  if (items.length === 0) return;
  const resp = await fetch("/api/categories/reorder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind: kindInput.value, items }),
  });
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось сохранить порядок категорий");
    await refreshCategories(kindInput.value);
  }
}

function moveLocalCategory(categoryId, fromGroupId, toGroupId, toIndex = null) {
  const groups = groupedCategories[kindInput.value] || [];
  const fromGroup = groups.find((g) => g.id === fromGroupId);
  const toGroup = groups.find((g) => g.id === toGroupId);
  if (!fromGroup || !toGroup) return false;

  const fromList = fromGroup.categories || [];
  const fromIdx = fromList.findIndex((c) => c.id === categoryId);
  if (fromIdx < 0) return false;
  const [moved] = fromList.splice(fromIdx, 1);
  moved.group_id = normalizeGroupId(toGroupId);

  const targetList = toGroup.categories || [];
  const insertAt = toIndex == null ? targetList.length : Math.max(0, Math.min(toIndex, targetList.length));
  targetList.splice(insertAt, 0, moved);
  return true;
}

async function moveCategory(categoryId, groupId) {
  const resp = await fetch(`/api/categories/${categoryId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group_id: groupId }),
  });
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось перенести категорию");
    return;
  }

  await refreshCategories(kindInput.value);
  renderCategoryManager();
  renderCategoryPicker();
}

function renderCategoryManager() {
  const groups = groupedCategories[kindInput.value] || [];
  categoryGroupsEl.innerHTML = "";

  groups.forEach((group) => {
    const isVirtual = Boolean(group.is_virtual);
    const card = document.createElement("section");
    card.className = "group-card";
    card.style.setProperty("--group-color", group.color || "#7aa7ff");
    card.draggable = !isVirtual;
    card.dataset.groupId = group.id;

    card.addEventListener("dragstart", () => {
      if (isVirtual) return;
      draggingGroupId = group.id;
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => {
      draggingGroupId = null;
      card.classList.remove("dragging");
    });
    card.addEventListener("dragover", (e) => {
      if (!draggingGroupId) return;
      if (isVirtual) return;
      e.preventDefault();
      card.classList.add("drop-target");
    });
    card.addEventListener("dragleave", () => card.classList.remove("drop-target"));
    card.addEventListener("drop", async (e) => {
      if (!draggingGroupId) return;
      if (isVirtual) return;
      e.preventDefault();
      card.classList.remove("drop-target");
      const fromIdx = groups.findIndex((g) => g.id === draggingGroupId);
      const toIdx = groups.findIndex((g) => g.id === group.id);
      if (fromIdx < 0 || toIdx < 0 || fromIdx === toIdx) return;
      const [moved] = groups.splice(fromIdx, 1);
      groups.splice(toIdx, 0, moved);
      renderCategoryManager();
      await persistGroupOrder();
      await refreshCategories(kindInput.value);
      renderCategoryManager();
      renderCategoryPicker();
    });

    const head = document.createElement("button");
    head.type = "button";
    head.className = "group-head";

    const title = document.createElement("span");
    title.className = "group-title";
    title.innerHTML = `<span class="group-icon">${escapeHtml(group.icon || "📁")}</span><span>${escapeHtml(group.name)} (${(group.categories || []).length})</span>`;

    const actions = document.createElement("div");
    actions.className = "group-actions";

    const editBtn = groupActionChip("✎", "Редактировать группу");
    editBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openGroupEditor(group);
    });

    const addBtn = groupActionChip("+", "Добавить категорию");
    addBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openCreateCategoryEditor(group);
    });

    const archiveBtn = groupActionChip("🗑", "Удалить группу");
    archiveBtn.classList.add("danger");
    archiveBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openGroupEditor(group);
      requestAnimationFrame(() => deleteFromManagerEditor());
    });

    if (!isVirtual) {
      actions.appendChild(editBtn);
      actions.appendChild(addBtn);
      actions.appendChild(archiveBtn);
    } else {
      const addUngrouped = groupActionChip("+", "Добавить без группы");
      addUngrouped.addEventListener("click", (e) => {
        e.stopPropagation();
        openCreateCategoryEditor({ id: "__ungrouped__" });
      });
      actions.appendChild(addUngrouped);
    }

    head.appendChild(title);
    head.appendChild(actions);

    const body = document.createElement("div");
    body.className = "group-body";
    body.dataset.groupId = group.id;

    body.addEventListener("dragover", (e) => {
      e.preventDefault();
      body.classList.add("drop-target");
    });
    body.addEventListener("dragleave", () => body.classList.remove("drop-target"));
    body.addEventListener("drop", async (e) => {
      e.preventDefault();
      body.classList.remove("drop-target");
      if (!draggingCategoryId || !body.dataset.groupId) return;
      const changed = moveLocalCategory(draggingCategoryId, draggingFromGroupId, body.dataset.groupId, null);
      if (!changed) return;
      const affected = [draggingFromGroupId, body.dataset.groupId].filter((x) => x !== undefined && x !== null);
      renderCategoryManager();
      await persistCategoriesOrderFor(affected);
      await refreshCategories(kindInput.value);
      renderCategoryManager();
      renderCategoryPicker();
      draggingCategoryId = null;
      draggingFromGroupId = null;
    });

    (group.categories || []).forEach((item) => {
      const row = document.createElement("div");
      row.className = "manager-category";
      row.draggable = true;
      row.dataset.categoryId = item.id;

      row.addEventListener("dragstart", () => {
        draggingCategoryId = item.id;
        draggingFromGroupId = group.id;
        row.classList.add("dragging");
      });
      row.addEventListener("dragend", () => {
        draggingCategoryId = null;
        draggingFromGroupId = null;
        row.classList.remove("dragging");
      });
      row.addEventListener("dragover", (e) => {
        e.preventDefault();
        row.classList.add("drop-target");
      });
      row.addEventListener("dragleave", () => row.classList.remove("drop-target"));
      row.addEventListener("drop", async (e) => {
        e.preventDefault();
        row.classList.remove("drop-target");
        if (!draggingCategoryId) return;
        const targetIndex = (group.categories || []).findIndex((x) => x.id === item.id);
        const changed = moveLocalCategory(draggingCategoryId, draggingFromGroupId, group.id, targetIndex);
        if (!changed) return;
        const affected = [draggingFromGroupId, group.id].filter((x) => x !== undefined && x !== null);
        renderCategoryManager();
        await persistCategoriesOrderFor(affected);
        await refreshCategories(kindInput.value);
        renderCategoryManager();
        renderCategoryPicker();
        draggingCategoryId = null;
        draggingFromGroupId = null;
      });

      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "btn btn--chip manager-chip";
      const itemIcon = item.icon ? `<span class="chip-icon">${escapeHtml(item.icon)}</span>` : "";
      chip.innerHTML = `${itemIcon}<span>${escapeHtml(item.name)}</span>`;
      chip.style.setProperty("--chip-accent", group.color || "#7aa7ff");
      chip.classList.add("chip-accent");
      chip.addEventListener("click", () => {
        subcategoryInput.value = item.name;
        subcategorySearch.value = "";
        renderCategoryPicker();
        updatePreview();
      });

      const catActions = document.createElement("div");
      catActions.className = "manager-category-actions";

      const renameBtn = groupActionChip("✎", "Переименовать");
      renameBtn.addEventListener("click", async () => openCategoryEditor(item, group));

      const deleteBtn = groupActionChip("🗑", "Удалить");
      deleteBtn.classList.add("danger");
      deleteBtn.addEventListener("click", async () => {
        openCategoryEditor(item, group);
        await deleteFromManagerEditor();
      });

      catActions.appendChild(renameBtn);
      catActions.appendChild(deleteBtn);

      row.appendChild(chip);
      row.appendChild(catActions);
      body.appendChild(row);
    });

    head.addEventListener("click", () => {
      body.hidden = !body.hidden;
      card.classList.toggle("collapsed", body.hidden);
    });

    card.appendChild(head);
    card.appendChild(body);
    categoryGroupsEl.appendChild(card);
  });
}

async function openCategoryManager() {
  if (!modal.classList.contains("open")) return;
  const ok = await refreshCategories(kindInput.value);
  if (!ok) return;

  renderCategoryManager();
  setCategoryManagerOpen(true);
  requestAnimationFrame(renderCategoryPicker);
}

function closeCategoryManager() {
  setCategoryManagerOpen(false);
  closeManagerEditor();
  requestAnimationFrame(renderCategoryPicker);
}

async function createGroup() {
  openGroupEditor(null);
}

function resetModalToCreate() {
  editOperationId = null;
  modalTitle.textContent = "Новая операция";
  saveBtn.textContent = "Сохранить";
  deleteBtn.hidden = true;

  txForm.reset();
  setOccurredDate(today);
  subcategorySearch.value = "";
  closeSubcategoryPopover();
  closeCategoryManager();

  setKind("expense");
  setAccount(accountChips.querySelector("button[data-account]")?.dataset.account || "Карта");
  updatePreview();
}

async function openEditModal(operationId) {
  const resp = await fetch(`/api/operations/${operationId}`);
  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(payload.detail || "Не удалось загрузить операцию");
    return;
  }

  const item = payload.data;
  editOperationId = item.id;
  modalTitle.textContent = "Редактирование операции";
  saveBtn.textContent = "Сохранить изменения";
  deleteBtn.hidden = false;

  await refreshCategories(item.kind);
  setKind(item.kind);
  subcategoryInput.value = item.subcategory;
  subcategorySearch.value = "";
  renderCategoryPicker();

  amountInput.value = item.amount;
  setOccurredDate(item.occurred_on);
  setAccount(item.account);
  commentInput.value = item.comment || "";
  updatePreview();

  showModal(modal, true);
  requestAnimationFrame(renderCategoryPicker);
}

async function submitOperation(e) {
  e.preventDefault();

  if (!subcategoryInput.value) {
    alert("Выберите подкатегорию");
    return;
  }

  if (!accountInput.value) {
    alert("Выберите счет");
    return;
  }

  const fd = new FormData(txForm);
  const url = editOperationId ? `/api/operations/${editOperationId}` : "/api/operations";
  const method = editOperationId ? "PUT" : "POST";

  setButtonLoading(saveBtn, true, "Сохранение...");
  const resp = await fetch(url, { method, body: fd });
  setButtonLoading(saveBtn, false);

  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(`Не удалось сохранить: ${payload.detail || "unknown"}`);
    return;
  }

  bumpUsage(kindInput.value, subcategoryInput.value);
  window.location.reload();
}

async function removeOperation() {
  if (!editOperationId) return;
  const confirmed = window.confirm("Удалить эту операцию?");
  if (!confirmed) return;

  setButtonLoading(deleteBtn, true, "Удаление...");
  const resp = await fetch(`/api/operations/${editOperationId}`, { method: "DELETE" });
  setButtonLoading(deleteBtn, false);

  const payload = await resp.json();
  if (!resp.ok || !payload.ok) {
    alert(`Не удалось удалить: ${payload.detail || "unknown"}`);
    return;
  }

  window.location.reload();
}

openModalBtn?.addEventListener("click", async () => {
  resetModalToCreate();
  await refreshCategories(kindInput.value);
  showModal(modal, true);
  requestAnimationFrame(renderCategoryPicker);
});

closeModalBtn?.addEventListener("click", () => showModal(modal, false));
modal?.addEventListener("click", (e) => {
  if (e.target === modal) showModal(modal, false);
});

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!modal.classList.contains("open")) return;
  if (!subcategoryPopover.hidden) {
    closeSubcategoryPopover();
    return;
  }
  if (!categoryManagerPanel.hidden) {
    closeCategoryManager();
    return;
  }
  showModal(modal, false);
});

kindSwitch?.querySelectorAll("button[data-kind]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    await refreshCategories(btn.dataset.kind);
    setKind(btn.dataset.kind);
    if (!categoryManagerPanel.hidden) renderCategoryManager();
  });
});

accountChips?.querySelectorAll("button[data-account]").forEach((btn) => {
  btn.addEventListener("click", () => setAccount(btn.dataset.account));
});

subcategorySearch?.addEventListener("input", () => {
  closeSubcategoryPopover();
  renderCategoryPicker();
});

amountInput?.addEventListener("input", updatePreview);
occurredOnInput?.addEventListener("change", () => {
  renderDateStrip();
  updatePreview();
});
commentInput?.addEventListener("input", updatePreview);

createCategoryBtn?.addEventListener("click", createCategoryFromSearch);
openCategoryManagerBtn?.addEventListener("click", openCategoryManager);
closeCategoryManagerBtn?.addEventListener("click", closeCategoryManager);
addCategoryGroupBtn?.addEventListener("click", createGroup);
managerEditorCloseBtn?.addEventListener("click", closeManagerEditor);
editorSaveBtn?.addEventListener("click", saveManagerEditor);
editorArchiveBtn?.addEventListener("click", archiveFromManagerEditor);
editorDeleteBtn?.addEventListener("click", deleteFromManagerEditor);

deleteBtn?.addEventListener("click", removeOperation);
txForm?.addEventListener("submit", submitOperation);

periodSwitch?.querySelectorAll("button[data-period]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    currentPeriod = btn.dataset.period;
    periodSwitch.querySelectorAll("button[data-period]").forEach((x) => {
      x.classList.toggle("active", x.dataset.period === currentPeriod);
    });
    await loadSummary();
  });
});

selectedDateInput?.addEventListener("change", loadSummary);

Object.entries(tableConfigs).forEach(([kind, cfg]) => {
  tableControllers[kind] = createTableController({
    ...cfg,
    getRows: () => summaryState[`${kind}_rows`] || [],
    getTotal: () => summaryState.totals?.[kind] || 0,
    formatAmount: fmt,
  });
  tableControllers[kind].bind();
});

document.querySelectorAll(".edit-op").forEach((btn) => {
  btn.addEventListener("click", () => openEditModal(btn.dataset.id));
});

document.addEventListener("click", (e) => {
  if (!subcategoryPopover.hidden && !subcategoryPopover.contains(e.target) && !e.target.closest("[data-more='1']")) {
    if (!e.target.closest(".chips-row")) {
      closeSubcategoryPopover();
    }
  }
});

window.addEventListener("resize", () => {
  if (modal.classList.contains("open")) {
    renderCategoryPicker();
    renderDateStrip();
    if (!subcategoryPopover.hidden) positionSubcategoryPopover();
  }
});

updateKpi();
updatePeriodLabel();
Object.values(tableControllers).forEach((c) => c.render());
resetModalToCreate();
refreshCategories("expense").then(() => renderCategoryPicker());
updatePreview();
