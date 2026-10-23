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
      return { label: "Разница", tone: "positive", cardClass: "positive", amount: balance };
    }
    if (balance < 0) {
      return { label: "Разница", tone: "negative", cardClass: "negative", amount: balance };
    }
    return { label: "Разница", tone: "neutral", cardClass: "neutral", amount: 0 };
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

    const incoming = Number(data.cashflow_income_total ?? data.income_total ?? 0);
    const outgoing = Number(data.cashflow_expense_total ?? data.expense_total ?? 0);
    const previousIn = Number(data.prev_cashflow_income_total ?? data.prev_income_total ?? 0);
    const previousOut = Number(data.prev_cashflow_expense_total ?? data.prev_expense_total ?? 0);
    const result = Number(data.cashflow_total ?? incoming - outgoing);
    const previousResult = Number(data.prev_cashflow_total ?? previousIn - previousOut);
    const compare = data.period !== "all_time";
    const signed = value => `${value > 0 ? "+" : ""}${core.formatMoney(value)}`;
    const rows = [
      ["Пришло", incoming, previousIn, "income"],
      ["Ушло", outgoing, previousOut, "expense"],
      ["Разница", result, previousResult, metricTone(result)],
    ];
    if (primaryContainer) {
      primaryContainer.innerHTML = rows.map(([label, value, previous, tone], index) => {
        const pct = previous > 0 && index < 2 ? ` · ${formatPct((value - previous) / previous * 100)}` : "";
        const parts = index === 2 && (Number(data.debt_cashflow_total) || Number(data.fx_cashflow_total))
          ? `<div class="period-result-parts"><span class="meta-chip meta-chip-neutral">Операции <b>${escapeHtml(signed(Number(data.balance || 0)))}</b></span>${Number(data.debt_cashflow_total) ? `<span class="meta-chip meta-chip-neutral">Долги <b>${escapeHtml(signed(Number(data.debt_cashflow_total)))}</b></span>` : ""}${Number(data.fx_cashflow_total) ? `<span class="meta-chip meta-chip-neutral">Обмен валют <b>${escapeHtml(signed(Number(data.fx_cashflow_total)))}</b></span>` : ""}</div>` : "";
        return `<article class="analytics-kpi-card analytics-kpi-${tone}"><div class="muted-small">${label}</div><strong>${escapeHtml(core.formatMoney(value))}</strong>${compare ? `<span class="muted-small">К прошлому периоду: ${escapeHtml(signed(value - previous) + pct)}</span>` : ""}${parts}</article>`;
      }).join("");
    }
    if (secondaryContainer) {
      const comparison = compare && data.comparison_date_from
        ? ` · Сравнение: ${core.formatDateRu(data.comparison_date_from)} — ${core.formatDateRu(data.comparison_date_to)}` : "";
      const changes = compare ? (data.category_breakdown || []).filter(c => Number(c.change_amount) && c.category_kind === "expense")
        .sort((a,b) => Math.abs(Number(b.change_amount)) - Math.abs(Number(a.change_amount))).slice(0,3) : [];
      secondaryContainer.innerHTML = `<div class="muted-small period-summary-meta">${Number(data.cashflow_events_count ?? data.operations_count ?? 0)} операций · Расходы в день: ${escapeHtml(core.formatMoney(data.avg_daily_expense || 0))}${escapeHtml(comparison)}</div>${changes.length ? `<div class="period-category-changes"><span class="muted-small">Изменение расходов</span>${changes.map(c => `<span class="meta-chip meta-chip-neutral">${escapeHtml(c.category_name)} <b>${escapeHtml(signed(Number(c.change_amount)))}</b></span>`).join("")}</div>` : ""}`;
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
    if (level === "brand") {
      return "брендам";
    }
    return level === "group" ? "группам" : "категориям";
  }

  function breakdownEntityCountLabel(level) {
    if (level === "brand") {
      return "бр.";
    }
    return level === "group" ? "гр." : "кат.";
  }

  function breakdownTitle(level) {
    if (level === "brand") {
      return "Структура по брендам";
    }
    return level === "group" ? "Структура по группам" : "Структура по категориям";
  }

  function breakdownItemKey(level, item, selectedKind = "expense") {
    if (level === "brand") {
      const brandKey = item.brand_id !== null && item.brand_id !== undefined ? `brand:${item.brand_id}` : "brand:none";
      return selectedKind === "all" ? `${brandKey}:${item.category_kind || "expense"}` : brandKey;
    }
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
