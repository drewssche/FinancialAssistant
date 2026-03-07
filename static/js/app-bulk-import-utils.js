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

  function splitStrict(line, minParts, maxParts) {
    const parts = String(line || "").split(";").map((part) => normalizeCell(part));
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
    splitStrict,
    keyify,
  };
})();
