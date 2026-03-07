(() => {
  function normalizeCell(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalizeKind(value) {
    const raw = normalizeCell(value).toLowerCase();
    if (!raw) {
      return "";
    }
    if (["expense", "расход"].includes(raw)) {
      return "expense";
    }
    if (["income", "доход"].includes(raw)) {
      return "income";
    }
    return "";
  }

  function normalizeAmount(value) {
    const raw = normalizeCell(value).replace(",", ".");
    if (!raw) {
      return { valid: false, value: "", number: 0 };
    }
    const amount = Number(raw);
    if (!Number.isFinite(amount) || amount <= 0) {
      return { valid: false, value: raw, number: 0 };
    }
    return {
      valid: true,
      value: amount.toFixed(2),
      number: amount,
    };
  }

  function isIsoDate(value) {
    const raw = normalizeCell(value);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
      return false;
    }
    const date = new Date(`${raw}T00:00:00Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === raw;
  }

  function normalizeDisplayDate(value) {
    const raw = normalizeCell(value).replace(/[-/]/g, ".");
    if (!raw) {
      return "";
    }
    if (/^\d{8}$/.test(raw)) {
      return `${raw.slice(0, 2)}.${raw.slice(2, 4)}.${raw.slice(4, 8)}`;
    }
    const parts = raw.split(".");
    if (parts.length !== 3) {
      return raw;
    }
    const [day, month, year] = parts;
    if (!year || year.length !== 4) {
      return raw;
    }
    return `${day.padStart(2, "0")}.${month.padStart(2, "0")}.${year}`;
  }

  function parseFlexibleDate(value) {
    const raw = normalizeCell(value);
    if (!raw) {
      return "";
    }
    if (isIsoDate(raw)) {
      return raw;
    }
    const normalized = normalizeDisplayDate(raw);
    if (!/^\d{2}\.\d{2}\.\d{4}$/.test(normalized)) {
      return "";
    }
    const [day, month, year] = normalized.split(".");
    const iso = `${year}-${month}-${day}`;
    return isIsoDate(iso) ? iso : "";
  }

  function splitStrict(line, minParts, maxParts) {
    const parts = String(line || "").split(";").map((part) => normalizeCell(part));
    while (parts.length > minParts && parts[parts.length - 1] === "") {
      parts.pop();
    }
    if (parts.length < minParts || parts.length > maxParts) {
      return null;
    }
    return parts;
  }

  function keyify(...parts) {
    return parts.map((part) => normalizeCell(part).toLowerCase()).join("::");
  }

  window.App = window.App || {};
  window.App.bulkImportUtils = {
    normalizeCell,
    normalizeKind,
    normalizeAmount,
    isIsoDate,
    normalizeDisplayDate,
    parseFlexibleDate,
    splitStrict,
    keyify,
  };
})();
