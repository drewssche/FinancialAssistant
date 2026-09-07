(() => {
  const bindings = new WeakMap();
  const collator = new Intl.Collator("ru", { numeric: true, sensitivity: "base" });
  const storageKey = (key) => `table-sort:${window.App.state.currentUserId || "guest"}:${key}`;
  const session = new Map();

  function get(key, fallback = null) {
    const id = storageKey(key);
    if (!session.has(id)) {
      try { session.set(id, JSON.parse(localStorage.getItem(id)) || null); } catch { session.set(id, null); }
    }
    const value = session.get(id);
    return value && typeof value.by === "string" && ["asc", "desc"].includes(value.dir) ? value : fallback;
  }

  function set(key, value) {
    session.set(storageKey(key), value);
    try { localStorage.setItem(storageKey(key), JSON.stringify(value)); } catch { /* Session-only sorting. */ }
  }

  function compare(left, right, type = "text", direction = "asc") {
    const normalize = (value) => {
      if (value == null || value === "") return null;
      if (type === "number") return Number.isFinite(Number(value)) ? Number(value) : null;
      if (type === "date") return Number.isFinite(Date.parse(value)) ? Date.parse(value) : null;
      return String(value);
    };
    const a = normalize(left), b = normalize(right);
    // Missing prices/dates always stay last, including descending order.
    if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1;
    const result = type === "text" ? collator.compare(a, b) : a - b;
    return direction === "desc" ? -result : result;
  }

  function sort(items, key, columns, fallback = null) {
    const choice = get(key, fallback);
    const column = columns.find((item) => item?.key === choice?.by);
    if (!column) return items.slice();
    const value = column.value || ((item) => item[column.key]);
    return items.slice().sort((a, b) => compare(value(a), value(b), column.type, choice.dir));
  }

  function bind(table, options) {
    if (!table) return;
    let binding = bindings.get(table);
    if (!binding) {
      binding = {};
      bindings.set(table, binding);
      table.addEventListener("click", (event) => {
        const header = event.target.closest("th[data-sort-key]");
        if (!header || header.closest("table") !== table || event.target.closest(".catalog-column-resizer, input, select")) return;
        if (event.target.closest("button:not(.table-sort-button), a")) return;
        const { key, columns, fallback, onChange } = binding.options;
        const previous = get(key, fallback);
        const next = { by: header.dataset.sortKey, dir: previous?.by === header.dataset.sortKey && previous.dir === "asc" ? "desc" : "asc" };
        set(key, next);
        draw(table, key, columns, fallback);
        Promise.resolve().then(() => onChange(next)).catch((error) => window.App.core.setStatus(String(error)));
      });
    }
    binding.options = options;
    draw(table, options.key, options.columns, options.fallback);
  }

  function draw(table, key, columns, fallback) {
    const choice = get(key, fallback);
    Array.from(table.tHead?.rows[0]?.cells || []).forEach((header, index) => {
      const column = columns[index];
      if (!column) return;
      let button = header.querySelector(".table-sort-button");
      if (!button) {
        button = document.createElement("button");
        button.type = "button";
        button.className = "table-sort-button";
        const label = document.createElement("span");
        // Keep existing resize grips (and their event handlers) outside the button.
        Array.from(header.childNodes).filter((node) => !node.classList?.contains("catalog-column-resizer")).forEach((node) => label.append(node));
        const arrow = document.createElement("span");
        arrow.className = "table-sort-arrow";
        arrow.setAttribute("aria-hidden", "true");
        button.append(label, arrow);
        header.prepend(button);
      }
      header.dataset.sortKey = column.key;
      const active = choice?.by === column.key;
      header.setAttribute("aria-sort", active ? (choice.dir === "asc" ? "ascending" : "descending") : "none");
      button.querySelector(".table-sort-arrow").textContent = active ? (choice.dir === "asc" ? "↑" : "↓") : "↕";
      const next = active && choice.dir === "asc" ? "убыванию" : "возрастанию";
      button.title = `Сортировать по ${next}${column.hint ? `. ${column.hint}` : ""}`;
      button.setAttribute("aria-label", `${button.firstElementChild.textContent.trim()}: ${button.title.toLowerCase()}`);
    });
  }

  window.App.registerRuntimeModule?.("table-sort", { bind, sort, compare, get, set });
})();
