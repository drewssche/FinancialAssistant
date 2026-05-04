(() => {
  const { core } = window.App;

  function escapeHtml(value) {
    if (typeof core.escapeHtml === "function") {
      return core.escapeHtml(value);
    }
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function describeResult(balanceRaw) {
    const balance = Number(balanceRaw || 0);
    if (balance > 0) {
      return { label: "Профицит", tone: "positive", cardClass: "positive", amount: balance };
    }
    if (balance < 0) {
      return { label: "Дефицит", tone: "negative", cardClass: "negative", amount: Math.abs(balance) };
    }
    return { label: "Ноль", tone: "neutral", cardClass: "neutral", amount: 0 };
  }

  function metricTone(valueRaw) {
    const value = Number(valueRaw || 0);
    if (value > 0) {
      return "income";
    }
    if (value < 0) {
      return "expense";
    }
    return "neutral";
  }

  function describeFxCashflow(valueRaw) {
    const value = Number(valueRaw || 0);
    if (value > 0) {
      return {
        text: `С учетом валютных сделок: +${core.formatMoney(value)}`,
        tone: "positive",
      };
    }
    if (value < 0) {
      return {
        text: `С учетом валютных сделок: ${core.formatMoney(value)}`,
        tone: "negative",
      };
    }
    return null;
  }

  function describeDebtCashflow(valueRaw) {
    const value = Number(valueRaw || 0);
    if (value > 0) {
      return {
        text: `С учетом долгов: +${core.formatMoney(value)}`,
        tone: "positive",
      };
    }
    if (value < 0) {
      return {
        text: `С учетом долгов: ${core.formatMoney(value)}`,
        tone: "negative",
      };
    }
    return null;
  }

  function resolveResultMetric(data) {
    const value = Number(data?.cashflow_total ?? data?.balance ?? 0);
    const previous = Number(data?.prev_cashflow_total ?? data?.prev_balance ?? 0);
    const delta = data?.cashflow_change_pct ?? data?.balance_change_pct ?? null;
    return { value, previous, delta };
  }

  function renderInsightList(container, items, renderItem, emptyText) {
    if (!container) {
      return;
    }
    if (!Array.isArray(items) || items.length === 0) {
      container.innerHTML = `<div class="muted-small">${emptyText}</div>`;
      return;
    }
    container.innerHTML = items.map(renderItem).join("");
  }

  function renderPeriodKpiBlocks(primaryContainer, secondaryContainer, rangeLabelEl, data, formatPct) {
    if (rangeLabelEl) {
      const periodLabelMap = { day: "Сегодня", week: "Эта неделя", month: "Этот месяц", year: "Этот год", all_time: "Все время", custom: "Период" };
      const label = periodLabelMap[data.period] || "Период";
      rangeLabelEl.textContent = `${label}: ${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }

    if (primaryContainer) {
      const operatingValue = Number(data?.balance ?? 0);
      const operatingPrevious = Number(data?.prev_balance ?? 0);
      const operatingDelta = data?.balance_change_pct ?? null;
      const cashflowMetric = resolveResultMetric(data);
      const primary = [
        {
          label: "Доход",
          value: core.formatMoney(data.income_total),
          delta: formatPct(data.income_change_pct),
          previous: core.formatMoney(data.prev_income_total || 0),
          cardClass: "income",
        },
        {
          label: "Расход",
          value: core.formatMoney(data.expense_total),
          delta: formatPct(data.expense_change_pct),
          previous: core.formatMoney(data.prev_expense_total || 0),
          cardClass: "expense",
        },
        {
          label: "Сэкономлено на акциях",
          value: core.formatMoney(data.discount_savings_total || 0),
          delta: String(data.discount_items_count || 0),
          previous: data.discount_savings_rate_pct === null || data.discount_savings_rate_pct === undefined
            ? "нет расходов"
            : formatPct(data.discount_savings_rate_pct),
          deltaLabel: "Акционных позиций",
          previousLabel: "К расходам",
          cardClass: "income",
        },
        {
          label: "Операционный результат",
          value: core.formatMoney(operatingValue),
          delta: formatPct(operatingDelta),
          previous: core.formatMoney(operatingPrevious),
          cardClass: metricTone(operatingValue),
        },
        {
          label: "Денежный поток",
          value: core.formatMoney(cashflowMetric.value),
          delta: formatPct(cashflowMetric.delta),
          previous: core.formatMoney(cashflowMetric.previous || 0),
          cardClass: metricTone(cashflowMetric.value),
        },
        {
          label: "Операций за период",
          value: String(data.operations_count || 0),
          delta: formatPct(data.operations_change_pct),
          previous: String(data.prev_operations_count || 0),
          cardClass: "neutral",
        },
      ];
      primaryContainer.innerHTML = primary
        .map((item) => {
          const deltaLabel = item.deltaLabel || "К прошлому периоду";
          const previousLabel = item.previousLabel || "Было";
          return `
          <article class="analytics-kpi-card analytics-kpi-${item.cardClass}">
            <div class="muted-small">${escapeHtml(item.label)}</div>
            <strong>${escapeHtml(item.value)}</strong>
            <span class="analytics-kpi-delta">${escapeHtml(deltaLabel)}: ${escapeHtml(item.delta)}</span>
            <span class="muted-small">${escapeHtml(previousLabel)}: ${escapeHtml(item.previous)}</span>
          </article>
        `;
        })
        .join("");
    }

    if (secondaryContainer) {
      const chips = [
        { text: `Средний расход/день: ${core.formatMoney(data.avg_daily_expense || 0)}`, tone: "neutral" },
        {
          text: data.max_expense_day_date
            ? `Самый затратный день: ${core.formatDateRu(data.max_expense_day_date)} · ${core.formatMoney(data.max_expense_day_total)}`
            : "Самый затратный день: нет данных",
          tone: "neutral",
        },
      ];
      const debtCashflowChip = describeDebtCashflow(data.debt_cashflow_total);
      if (debtCashflowChip) {
        debtCashflowChip.text = debtCashflowChip.text.replace("С учетом долгов", "Долги в потоке");
        chips.push(debtCashflowChip);
      }
      const fxCashflowChip = describeFxCashflow(data.fx_cashflow_total);
      if (fxCashflowChip) {
        fxCashflowChip.text = fxCashflowChip.text.replace("С учетом валютных сделок", "Валюта в потоке");
        chips.push(fxCashflowChip);
      }
      secondaryContainer.innerHTML = chips
        .map((item) => `<span class="analytics-kpi-chip analytics-kpi-chip-${item.tone}">${escapeHtml(item.text)}</span>`)
        .join("");
    }
  }

  function categoryKindLabel(kind) {
    if (kind === "income") {
      return "доходов";
    }
    if (kind === "all") {
      return "всех операций";
    }
    return "расходов";
  }

  function categoryKindShort(kind) {
    return kind === "income" ? "Доход" : kind === "all" ? "Все" : "Расход";
  }

  function breakdownEntityLabel(level) {
    return level === "group" ? "группам" : "категориям";
  }

  function breakdownEntityCountLabel(level) {
    return level === "group" ? "гр." : "кат.";
  }

  function breakdownTitle(level) {
    return level === "group" ? "Структура по группам" : "Структура по категориям";
  }

  function breakdownItemKey(level, item) {
    if (level === "group") {
      return item.group_id !== null && item.group_id !== undefined ? `group:${item.group_id}` : "group:none";
    }
    return item.category_id !== null && item.category_id !== undefined ? `category:${item.category_id}` : "category:none";
  }

  function polarToCartesian(cx, cy, radius, angleDeg) {
    const angle = (angleDeg - 90) * (Math.PI / 180);
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  }

  function buildDonutSegmentPath(cx, cy, outerRadius, innerRadius, startAngle, endAngle) {
    if (endAngle - startAngle >= 359.99) {
      const rightOuter = cx + outerRadius;
      const rightInner = cx + innerRadius;
      const leftOuter = cx - outerRadius;
      const leftInner = cx - innerRadius;
      return [
        `M ${rightOuter} ${cy}`,
        `A ${outerRadius} ${outerRadius} 0 1 1 ${leftOuter} ${cy}`,
        `A ${outerRadius} ${outerRadius} 0 1 1 ${rightOuter} ${cy}`,
        `L ${rightInner} ${cy}`,
        `A ${innerRadius} ${innerRadius} 0 1 0 ${leftInner} ${cy}`,
        `A ${innerRadius} ${innerRadius} 0 1 0 ${rightInner} ${cy}`,
        "Z",
      ].join(" ");
    }
    const outerStart = polarToCartesian(cx, cy, outerRadius, startAngle);
    const outerEnd = polarToCartesian(cx, cy, outerRadius, endAngle);
    const innerEnd = polarToCartesian(cx, cy, innerRadius, endAngle);
    const innerStart = polarToCartesian(cx, cy, innerRadius, startAngle);
    const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;
    return [
      `M ${outerStart.x} ${outerStart.y}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEnd.x} ${outerEnd.y}`,
      `L ${innerEnd.x} ${innerEnd.y}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStart.x} ${innerStart.y}`,
      "Z",
    ].join(" ");
  }

  function formatPct(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "нет базы";
    }
    const num = Number(value);
    const sign = num > 0 ? "+" : "";
    return `${sign}${num.toFixed(1)}%`;
  }

  window.App.analyticsShared = {
    escapeHtml,
    describeResult,
    describeDebtCashflow,
    describeFxCashflow,
    resolveResultMetric,
    metricTone,
    renderInsightList,
    renderPeriodKpiBlocks,
    formatPct,
    categoryKindLabel,
    categoryKindShort,
    breakdownEntityLabel,
    breakdownEntityCountLabel,
    breakdownTitle,
    breakdownItemKey,
    buildDonutSegmentPath,
  };
})();
