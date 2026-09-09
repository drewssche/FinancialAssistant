(() => {
  function createWorkSummaryUi(deps) {
    const {
      getSnapshot, escape, formatMoney, formatHours, formatDate,
      paymentOperationId, paymentOperationDate, paymentOperationAmount, paymentOperationCurrency,
      paymentOperationBaseAmount, paymentOperationBaseCurrency, paymentSourceLabel,
    } = deps;
    function groupedMoney(rows, amountOf, currencyOf) {
      const totals = new Map();
      rows.forEach((row) => {
        const rawAmount = amountOf(row);
        if (rawAmount == null || rawAmount === "") return;
        const amount = Number(rawAmount);
        if (!Number.isFinite(amount)) return;
        const currency = String(currencyOf(row) || "BYN").toUpperCase();
        totals.set(currency, (totals.get(currency) || 0) + amount);
      });
      return totals;
    }

    function renderMoneyValues(group) {
      const entries = [...group.entries()].sort(([left], [right]) => {
        if (left === "BYN") return -1;
        if (right === "BYN") return 1;
        return left.localeCompare(right);
      });
      if (!entries.length) return '<strong class="work-money-empty">—</strong>';
      return entries.map(([currency, amount]) => `<strong>${escape(formatMoney(amount, currency))}</strong>`).join("");
    }

    function moneyGroupFromTotals(rows, amountKey = "amount", { includeZero = true } = {}) {
      const totals = new Map();
      (Array.isArray(rows) ? rows : []).forEach((row) => {
        const amount = Number(row?.[amountKey]);
        if (!Number.isFinite(amount) || (!includeZero && Math.abs(amount) < 0.005)) return;
        const currency = String(row?.currency || "BYN").toUpperCase();
        totals.set(currency, (totals.get(currency) || 0) + amount);
      });
      return totals;
    }

    function inlineMoneyValues(group) {
      const entries = [...group.entries()].sort(([left], [right]) => {
        if (left === "BYN") return -1;
        if (right === "BYN") return 1;
        return left.localeCompare(right);
      });
      if (!entries.length) return "—";
      return entries.map(([currency, amount]) => escape(formatMoney(amount, currency))).join(" · ");
    }

    function salaryCycleComponentActuals(component) {
      const explicit = moneyGroupFromTotals(component?.actual_totals);
      return explicit.size
        ? explicit
        : groupedMoney(activeSalaryCycleOperations(component), paymentOperationBaseAmount, paymentOperationBaseCurrency);
    }

    function activeSalaryCycleOperations(component) {
      return (Array.isArray(component?.actual_operations) ? component.actual_operations : []).filter((row) => !row?.is_deleted);
    }

    function salaryCycleComponentForecast(component) {
      const amount = component?.forecast_base_amount ?? component?.forecast_amount;
      if (amount == null || amount === "") return new Map();
      const hasBaseAmount = component?.forecast_base_amount != null;
      return groupedMoney(
        [component],
        (row) => row.forecast_base_amount ?? row.forecast_amount,
        (row) => hasBaseAmount
          ? row.forecast_base_currency || row.forecast_currency || "BYN"
          : row.forecast_currency || "BYN",
      );
    }

    function renderSalaryCycleComponent(component) {
      const role = String(component?.role || "extras");
      const label = component?.label || (role === "advance" ? "Аванс" : role === "salary" ? "Основная часть" : "Доплаты");
      const activeOperations = activeSalaryCycleOperations(component);
      const actuals = role === "extras"
        ? groupedMoney(activeOperations, paymentOperationBaseAmount, paymentOperationBaseCurrency)
        : salaryCycleComponentActuals(component);
      const forecast = role === "extras" ? new Map() : salaryCycleComponentForecast(component);
      const date = component?.effective_date ? formatDate(component.effective_date) : "";
      const nominalDate = component?.nominal_date ? formatDate(component.nominal_date) : "";
      const dateLabel = date
        ? component?.shifted && nominalDate
          ? `${date} · перенесено с ${nominalDate}`
          : date
        : "";
      const states = [];
      if (!activeOperations.length && actuals.size) {
        states.push(`<strong>${inlineMoneyValues(actuals)}</strong>`);
      }
      if (forecast.size) {
        states.push(`<span class="work-salary-cycle-state is-forecast">Прогноз · ${inlineMoneyValues(forecast)}</span>`);
      }
      if (!actuals.size && !forecast.size && !activeOperations.length) {
        states.push('<span class="muted-small">Выплата не найдена</span>');
      }
      const operationDateLabel = (row) => paymentOperationDate(row) === component?.effective_date
        ? "" : `${escape(formatDate(paymentOperationDate(row)))} · `;
      const operationLinks = activeOperations.map((row) => {
        const id = paymentOperationId(row);
        if (!(id > 0)) return "";
        const title = `Получено ${formatDate(paymentOperationDate(row))} · ${paymentSourceLabel(row.source)}${row.note ? ` · ${row.note}` : ""} · открыть операцию`;
        return `<button type="button" class="work-payment-actual-link" data-work-operation-id="${id}" title="${escape(title)}">${operationDateLabel(row)}${escape(formatMoney(paymentOperationAmount(row), paymentOperationCurrency(row)))}</button>`;
      }).join("");
      const planId = getSnapshot()?.profile?.[role === "advance" ? "advance_plan_id" : "salary_plan_id"];
      const planLink = role === "extras" ? "" : `<button type="button" class="work-payment-plan-link" data-work-open-plan-picker="${escape(role)}">${planId ? `План #${Number(planId)} · изменить` : "Выбрать план"}</button>`;
      return `
        <div class="work-salary-cycle-component work-salary-cycle-component-${escape(role)}">
          <div class="work-salary-cycle-component-head">
            <strong>${escape(label)}</strong>
            ${dateLabel ? `<span>${escape(dateLabel)}</span>` : ""}
          </div>
          ${states.length ? `<div class="work-salary-cycle-component-values">${states.join("")}</div>` : ""}
          ${operationLinks ? `<div class="work-salary-cycle-operation-links">${operationLinks}</div>` : ""}
          ${planLink}
        </div>`;
    }

    function renderSalaryCycleCard() {
      const cycle = getSnapshot()?.salary_cycle;
      if (!cycle || !Array.isArray(cycle.totals)) return "";
      const actual = moneyGroupFromTotals(cycle.totals, "actual_amount", { includeZero: false });
      const forecast = moneyGroupFromTotals(cycle.totals, "forecast_amount", { includeZero: false });
      const expected = moneyGroupFromTotals(cycle.totals, "expected_amount");
      const incomplete = ["advance", "salary"].some((role) => {
        const component = (cycle.components || []).find((item) => item.role === role);
        return !component || component.status === "missing"
          || (component.status === "forecast" && !salaryCycleComponentForecast(component).size);
      });
      const hasActual = actual.size > 0;
      if (!actual.size) actual.set("BYN", 0);
      const cards = [["Получено за период", actual, "Аванс, основная часть и доплаты", "work-money-kpi-actual"]];
      if (forecast.size || incomplete) {
        cards.push(["Ещё ожидается", forecast, incomplete ? "Не все выплаты найдены — остаток неизвестен" : "По планам зарплатного цикла", "work-money-kpi-forecast"]);
      }
      if (hasActual && forecast.size) {
        cards.push(["Итого с прогнозом", expected, incomplete ? "Неполный итог · не все выплаты найдены" : "Получено + ожидаемые выплаты", ""]);
      }
      const windowLabel = cycle.window_from_exclusive && cycle.window_to_inclusive
        ? `Выплаты после ${formatDate(cycle.window_from_exclusive)} и по ${formatDate(cycle.window_to_inclusive)} включительно`
        : "Аванс прошлого месяца и основная часть текущего";
      return `
        <div class="work-salary-cycle-head"><div class="work-salary-cycle-title">
          <span class="muted-small">Зарплатный цикл</span>
          <strong>${escape(cycle.label || "Зарплата за предыдущий месяц")}</strong>
          <span class="muted-small">${escape(windowLabel)}</span>
        </div></div>
        <div class="work-money-summary-grid">${cards.map(([label, values, meta, className]) => `
          <article class="analytics-kpi-card work-money-kpi-card ${className}">
            <div class="muted-small">${escape(label)}</div>
            <div class="work-money-kpi-values">${renderMoneyValues(values)}</div>
            <div class="muted-small">${escape(meta)}</div>
          </article>`).join("")}</div>`;
    }

    function renderEarningsRate(key, label) {
      const cycle = getSnapshot()?.salary_cycle;
      const estimate = cycle?.earnings_estimate;
      const available = estimate && estimate.status !== "unavailable" && estimate[key] != null;
      const reasons = {
        missing_payment: "Не хватает выплаты или суммы прогноза",
        unresolved_currency: "Нет пересчёта всей зарплаты в BYN",
        missing_work_norm: "Не задана норма рабочих дней или часов",
      };
      const month = cycle?.reference_year && cycle?.reference_month
        ? new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" }).format(new Date(cycle.reference_year, cycle.reference_month - 1, 1))
        : "месяц зарплаты";
      const note = available
        ? `${estimate.status === "forecast" ? "С учётом прогноза" : "По фактической зарплате"} · без разовых доплат · норма: ${estimate.planned_days} дн. / ${formatHours(estimate.planned_hours)} ч`
        : reasons[estimate?.reason] || "Недостаточно данных";
      return `<div class="work-time-kpi-rate" title="${escape(note)}">
        <div class="muted-small">${escape(label)}</div>
        <strong>${available ? `≈ ${escape(formatMoney(estimate[key], estimate.currency))}` : "—"}</strong>
        <div class="muted-small">${available ? `За ${escape(month)} · ${estimate.status === "forecast" ? "прогноз" : "факт"}` : escape(note)}</div>
      </div>`;
    }

    return { renderSalaryCycleCard, renderSalaryCycleComponent, renderEarningsRate, moneyGroupFromTotals, renderMoneyValues };
  }
  window.App.registerRuntimeModule("work-summary-ui", { createWorkSummaryUi });
})();
