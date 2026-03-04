export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function highlight(text, query) {
  if (!query) return escapeHtml(text);
  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  const idx = lower.indexOf(q);
  if (idx === -1) return escapeHtml(text);
  const a = escapeHtml(text.slice(0, idx));
  const b = escapeHtml(text.slice(idx, idx + query.length));
  const c = escapeHtml(text.slice(idx + query.length));
  return `${a}<mark>${b}</mark>${c}`;
}

function sortRows(rows, mode) {
  const list = [...rows];
  switch (mode) {
    case "amount_asc":
      return list.sort((a, b) => a.amount - b.amount);
    case "name_asc":
      return list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
    case "name_desc":
      return list.sort((a, b) => b.name.localeCompare(a.name, "ru"));
    case "amount_desc":
    default:
      return list.sort((a, b) => b.amount - a.amount);
  }
}

export function createTableController(config) {
  const {
    rowsEl,
    searchEl,
    minEl,
    sortEl,
    emptyText,
    getRows,
    getTotal,
    formatAmount,
  } = config;

  function render() {
    const total = Number(getTotal() || 0);
    const query = searchEl.value.trim();
    const minVal = Number(minEl.value || 0);
    const sortMode = sortEl.value;

    let rows = getRows() || [];
    if (query) {
      rows = rows.filter((r) => r.name.toLowerCase().includes(query.toLowerCase()));
    }
    rows = rows.filter((r) => Number(r.amount) >= minVal);
    rows = sortRows(rows, sortMode);

    rowsEl.innerHTML = "";
    if (rows.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 3;
      td.className = "muted";
      td.textContent = emptyText;
      tr.appendChild(td);
      rowsEl.appendChild(tr);
      return;
    }

    rows.forEach((row) => {
      const share = total > 0 ? `${((Number(row.amount) / total) * 100).toFixed(1)}%` : "0.0%";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${highlight(row.name, query)}</td>
        <td>${formatAmount(row.amount)}</td>
        <td>${share}</td>
      `;
      rowsEl.appendChild(tr);
    });
  }

  function bind() {
    searchEl.addEventListener("input", render);
    minEl.addEventListener("input", render);
    sortEl.addEventListener("change", render);
  }

  return { render, bind };
}
