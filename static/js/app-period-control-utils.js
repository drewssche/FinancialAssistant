(() => {
  function parseIsoDate(value) {
    const raw = String(value || "").trim();
    if (!raw) {
      return null;
    }
    const date = new Date(`${raw}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function toIsoDate(date) {
    return date instanceof Date && !Number.isNaN(date.getTime()) ? date.toISOString().slice(0, 10) : "";
  }

  function addDaysIso(value, deltaDays) {
    const parsed = parseIsoDate(value);
    if (!parsed) {
      return "";
    }
    parsed.setUTCDate(parsed.getUTCDate() + deltaDays);
    return toIsoDate(parsed);
  }

  function shiftPeriodBounds({ period, direction = 1, currentBounds = null, getPeriodBounds }) {
    const current = currentBounds || getPeriodBounds?.(period) || null;
    if (!current?.dateFrom || !current?.dateTo) {
      return current;
    }
    const step = direction < 0 ? -1 : 1;
    if (period === "day") {
      const dateFrom = addDaysIso(current.dateFrom, step);
      return { dateFrom, dateTo: dateFrom };
    }
    if (period === "week") {
      return {
        dateFrom: addDaysIso(current.dateFrom, step * 7),
        dateTo: addDaysIso(current.dateTo, step * 7),
      };
    }
    if (period === "month") {
      const currentStart = parseIsoDate(current.dateFrom);
      if (!currentStart) {
        return current;
      }
      const shiftedMonthStart = new Date(Date.UTC(
        currentStart.getUTCFullYear(),
        currentStart.getUTCMonth() + step,
        1,
      ));
      const shiftedMonthEnd = new Date(Date.UTC(
        currentStart.getUTCFullYear(),
        currentStart.getUTCMonth() + step + 1,
        0,
      ));
      return {
        dateFrom: toIsoDate(shiftedMonthStart),
        dateTo: toIsoDate(shiftedMonthEnd),
      };
    }
    if (period === "year") {
      const currentStart = parseIsoDate(current.dateFrom);
      if (!currentStart) {
        return current;
      }
      const shiftedYear = currentStart.getUTCFullYear() + step;
      return {
        dateFrom: `${shiftedYear}-01-01`,
        dateTo: `${shiftedYear}-12-31`,
      };
    }
    return current;
  }

  window.App.registerRuntimeModule?.("period-control-utils", {
    shiftPeriodBounds,
  });
})();
