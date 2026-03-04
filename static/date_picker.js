function toIsoLocal(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function parseIso(iso, fallbackIso) {
  const src = iso || fallbackIso;
  const d = new Date(`${src}T00:00:00`);
  if (Number.isNaN(d.getTime())) {
    return new Date(`${fallbackIso}T00:00:00`);
  }
  return d;
}

function formatDateRu(iso) {
  const d = parseIso(iso, iso);
  return d.toLocaleDateString("ru-RU");
}

function formatMonthYearRu(date) {
  return date.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
}

export function createInlineDatePicker(config) {
  const {
    inputEl,
    textEl,
    monthEl,
    gridEl,
    prevBtn,
    nextBtn,
    fallbackIso,
    onChange,
  } = config;

  let cursor = null;

  function setValue(iso) {
    inputEl.value = iso;
    textEl.textContent = formatDateRu(iso);
  }

  function getValue() {
    return inputEl.value || fallbackIso;
  }

  function render() {
    const selected = parseIso(getValue(), fallbackIso);
    const currentCursor = cursor || new Date(selected.getFullYear(), selected.getMonth(), 1);
    cursor = currentCursor;
    monthEl.textContent = formatMonthYearRu(currentCursor);

    const first = new Date(currentCursor.getFullYear(), currentCursor.getMonth(), 1);
    const shift = (first.getDay() + 6) % 7;
    const start = new Date(first);
    start.setDate(first.getDate() - shift);

    gridEl.innerHTML = "";
    for (let i = 0; i < 42; i += 1) {
      const cellDate = new Date(start);
      cellDate.setDate(start.getDate() + i);
      const iso = toIsoLocal(cellDate);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cal-day";
      if (cellDate.getMonth() !== currentCursor.getMonth()) btn.classList.add("other");
      if (iso === getValue()) btn.classList.add("active");
      btn.textContent = String(cellDate.getDate());
      btn.addEventListener("click", () => {
        setValue(iso);
        render();
        onChange?.(iso);
      });
      gridEl.appendChild(btn);
    }
  }

  prevBtn?.addEventListener("click", () => {
    if (!cursor) {
      const selected = parseIso(getValue(), fallbackIso);
      cursor = new Date(selected.getFullYear(), selected.getMonth(), 1);
    }
    cursor.setMonth(cursor.getMonth() - 1);
    render();
  });

  nextBtn?.addEventListener("click", () => {
    if (!cursor) {
      const selected = parseIso(getValue(), fallbackIso);
      cursor = new Date(selected.getFullYear(), selected.getMonth(), 1);
    }
    cursor.setMonth(cursor.getMonth() + 1);
    render();
  });

  return {
    getValue,
    setValue(iso) {
      const d = parseIso(iso, fallbackIso);
      setValue(toIsoLocal(d));
      cursor = new Date(d.getFullYear(), d.getMonth(), 1);
    },
    render,
    toIsoLocal,
  };
}
