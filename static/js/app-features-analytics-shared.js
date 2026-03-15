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
      return { label: "Профицит", tone: "positive", amount: balance };
    }
    if (balance < 0) {
      return { label: "Дефицит", tone: "negative", amount: Math.abs(balance) };
    }
    return { label: "Нулевой баланс", tone: "neutral", amount: 0 };
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
      const primary = [
        {
          label: "Доход",
          value: core.formatMoney(data.income_total),
          delta: formatPct(data.income_change_pct),
          previous: core.formatMoney(data.prev_income_total || 0),
          tone: "income",
        },
        {
          label: "Расход",
          value: core.formatMoney(data.expense_total),
          delta: formatPct(data.expense_change_pct),
          previous: core.formatMoney(data.prev_expense_total || 0),
          tone: "expense",
        },
        {
          label: "Баланс",
          value: core.formatMoney(data.balance),
          delta: formatPct(data.balance_change_pct),
          previous: core.formatMoney(data.prev_balance || 0),
          tone: "balance",
        },
        {
          label: "Операций за период",
          value: String(data.operations_count || 0),
          delta: formatPct(data.operations_change_pct),
          previous: String(data.prev_operations_count || 0),
          tone: "neutral",
        },
      ];
      primaryContainer.innerHTML = primary
        .map((item) => `
          <article class="analytics-kpi-card analytics-kpi-${item.tone}">
            <div class="muted-small">${escapeHtml(item.label)}</div>
            <strong>${escapeHtml(item.value)}</strong>
            <span class="analytics-kpi-delta">К прошлому периоду: ${escapeHtml(item.delta)}</span>
            <span class="muted-small">Было: ${escapeHtml(item.previous)}</span>
          </article>
        `)
        .join("");
    }

    if (secondaryContainer) {
      const result = describeResult(data.balance);
      const chips = [
        { text: `${result.label}: ${core.formatMoney(result.amount)}`, tone: result.tone },
        { text: `Средний расход/день: ${core.formatMoney(data.avg_daily_expense || 0)}`, tone: "neutral" },
        {
          text: data.max_expense_day_date
            ? `Самый затратный день: ${core.formatDateRu(data.max_expense_day_date)} · ${core.formatMoney(data.max_expense_day_total)}`
            : "Самый затратный день: нет данных",
          tone: "neutral",
        },
      ];
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
