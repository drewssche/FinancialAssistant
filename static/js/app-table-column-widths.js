(() => {
  const bindings = new WeakMap();

  function bind(table, { defaults, minimums, storageKey, resetButton } = {}) {
    if (!table) return null;
    if (bindings.has(table)) return bindings.get(table);
    const columns = Array.from(table.querySelectorAll("colgroup > col"));
    const headers = Array.from(table.querySelectorAll("thead th"));
    let widths = [...defaults];
    let loadedKey = null;
    let drag = null;
    const handles = [];
    const key = () => `${storageKey}:${window.App.state.currentUserId || "guest"}`;

    function draw() {
      columns.forEach((column, index) => { column.style.width = `${widths[index]}%`; });
      const tableWidth = table.getBoundingClientRect().width;
      handles.forEach(({ handle, index }) => {
        handle.setAttribute("aria-valuemin", "0");
        handle.setAttribute("aria-valuemax", String(Math.round(tableWidth * (widths[index] + widths[index + 1]) / 100)));
        handle.setAttribute("aria-valuenow", String(Math.round(tableWidth * widths[index] / 100)));
        handle.setAttribute("aria-valuetext", `${Math.round(tableWidth * widths[index] / 100)} пикселей`);
      });
    }

    function apply() {
      if (loadedKey !== key()) {
        loadedKey = key();
        widths = [...defaults];
        try {
          const saved = JSON.parse(localStorage.getItem(loadedKey));
          if (Array.isArray(saved) && saved.length === defaults.length
            && saved.every((value) => Number.isFinite(value) && value > 0)
            && Math.abs(saved.reduce((sum, value) => sum + value, 0) - 100) < .1) widths = saved;
        } catch { /* Unavailable storage or an old/corrupt setting uses defaults. */ }
      }
      draw();
    }

    function save() {
      try { localStorage.setItem(key(), JSON.stringify(widths)); } catch { /* Session-only resizing still works. */ }
    }

    function resizePair(index, delta, initial, tableWidth) {
      if (!(tableWidth > 0)) return;
      const pair = initial[index] + initial[index + 1];
      // A smaller viewport may already be below the preferred minimum. Do not
      // jump wider as soon as dragging begins; just prevent further shrinking.
      const leftMin = Math.min(minimums[index] / tableWidth * 100, initial[index]);
      const rightMin = Math.min(minimums[index + 1] / tableWidth * 100, initial[index + 1]);
      widths[index] = Math.max(leftMin, Math.min(pair - rightMin, initial[index] + delta / tableWidth * 100));
      widths[index + 1] = pair - widths[index];
      draw();
    }

    function finish(cancel = false) {
      if (!drag) return;
      const active = drag;
      drag = null;
      if (cancel) widths = active.initial;
      else save();
      if (active.handle.hasPointerCapture(active.pointerId)) active.handle.releasePointerCapture(active.pointerId);
      document.documentElement.classList.remove("is-resizing-table-columns");
      draw();
    }

    function reset() {
      finish(true);
      widths = [...defaults];
      loadedKey = key();
      try { localStorage.removeItem(loadedKey); } catch { /* No persistent storage. */ }
      draw();
    }

    // The checkbox column stays fixed; each grip shares space with its neighbour.
    // Total width stays 100%, so dragging never pushes actions off the screen.
    headers.slice(1, -1).forEach((header, offset) => {
      const index = offset + 1;
      header.title = header.textContent.trim();
      const handle = document.createElement("span");
      handle.className = "catalog-column-resizer";
      handle.tabIndex = 0;
      handle.setAttribute("role", "separator");
      handle.setAttribute("aria-orientation", "vertical");
      handle.setAttribute("aria-label", `Ширина колонки «${header.textContent.trim()}»`);
      handle.title = "Перетащите для изменения ширины. Двойной клик — сброс. С клавиатуры: ← / →";
      header.append(handle);
      handles.push({ handle, index });
      handle.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || !event.isPrimary) return;
        event.preventDefault();
        event.stopPropagation();
        apply();
        drag = { handle, index, pointerId: event.pointerId, startX: event.clientX, initial: [...widths], tableWidth: table.getBoundingClientRect().width };
        handle.setPointerCapture(event.pointerId);
        document.documentElement.classList.add("is-resizing-table-columns");
        handle.focus({ preventScroll: true });
      });
      handle.addEventListener("pointermove", (event) => {
        if (drag?.pointerId === event.pointerId) resizePair(index, event.clientX - drag.startX, drag.initial, drag.tableWidth);
      });
      handle.addEventListener("pointerup", () => finish());
      handle.addEventListener("pointercancel", () => finish(true));
      handle.addEventListener("lostpointercapture", () => finish(true));
      handle.addEventListener("dblclick", reset);
      handle.addEventListener("click", (event) => event.stopPropagation());
      handle.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && drag) {
          event.preventDefault();
          finish(true);
        } else if (["ArrowLeft", "ArrowRight"].includes(event.key)) {
          event.preventDefault();
          resizePair(index, (event.key === "ArrowLeft" ? -1 : 1) * (event.shiftKey ? 30 : 10), [...widths], table.getBoundingClientRect().width);
          save();
        }
      });
    });
    resetButton?.addEventListener("click", reset);
    const observer = new ResizeObserver(() => { if (!drag) draw(); });
    observer.observe(table);
    const api = { apply, cancel: () => finish(true) };
    bindings.set(table, api);
    apply();
    return api;
  }

  window.App.registerRuntimeModule?.("table-column-widths", { bind });
})();
