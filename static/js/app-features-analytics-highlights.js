(() => {
  const { state, el, core } = window.App;
  const HIGHLIGHTS_CACHE_TTL_MS = 20000;
  const BREAKDOWN_PALETTE = ["#ff8f6b", "#5fd3bc", "#7aa8ff", "#ffd166", "#c084fc", "#5eead4", "#fb7185", "#93c5fd", "#a3e635"];
  const DONUT_CENTER = 130;
  const DONUT_OUTER_RADIUS = 118;
  const DONUT_INNER_RADIUS = 62;
  let activeBreakdown = {
    items: [],
    listItems: [],
    kind: "expense",
    level: "category",
    total: 0,
    totalOps: 0,
    defaultIndex: null,
    hoveredIndex: null,
  };

  function escapeHtml(value) {
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

  function hiddenBreakdownKeys(level, kind) {
    const hidden = state.analyticsStructureHidden?.[level]?.[kind];
    return new Set(Array.isArray(hidden) ? hidden.map((item) => String(item)) : []);
  }

  function writeHiddenBreakdownKeys(level, kind, keys) {
    state.analyticsStructureHidden = state.analyticsStructureHidden || {
      category: { expense: [], income: [], all: [] },
      group: { expense: [], income: [], all: [] },
    };
    state.analyticsStructureHidden[level] = state.analyticsStructureHidden[level] || { expense: [], income: [], all: [] };
    state.analyticsStructureHidden[level][kind] = Array.from(keys);
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

  function applyCategoryBreakdownHover(index = null) {
    activeBreakdown.hoveredIndex = Number.isInteger(index) ? index : null;
    const resolvedIndex = activeBreakdown.hoveredIndex ?? activeBreakdown.defaultIndex;
    const hasHover = activeBreakdown.hoveredIndex !== null;
    const hasDefault = !hasHover && activeBreakdown.defaultIndex !== null;
    const resolvedColor = Number.isInteger(resolvedIndex)
      ? BREAKDOWN_PALETTE[resolvedIndex % BREAKDOWN_PALETTE.length]
      : "";
    if (el.analyticsCategoryBreakdownChart) {
      el.analyticsCategoryBreakdownChart.classList.toggle("analytics-category-donut-has-hover", hasHover);
      el.analyticsCategoryBreakdownChart.classList.toggle("analytics-category-donut-has-default", hasDefault);
      if (resolvedColor) {
        el.analyticsCategoryBreakdownChart.style.setProperty("--active-slice-color", resolvedColor);
      } else {
        el.analyticsCategoryBreakdownChart.style.removeProperty("--active-slice-color");
      }
    }
    document.querySelectorAll("[data-analytics-category-index]").forEach((node) => {
      const nodeIndex = Number(node.dataset.analyticsCategoryIndex);
      const isActive = hasHover && nodeIndex === resolvedIndex;
      const isInactive = hasHover && nodeIndex !== resolvedIndex;
      const isDefault = hasDefault && nodeIndex === resolvedIndex;
      node.classList.toggle("is-active", isActive);
      node.classList.toggle("is-inactive", isInactive);
      node.classList.toggle("is-default", isDefault);
    });

    const hoveredItem = hasHover ? activeBreakdown.items[resolvedIndex] : null;
    if (el.analyticsCategoryBreakdownChartTitle) {
      el.analyticsCategoryBreakdownChartTitle.textContent = hoveredItem
        ? String(hoveredItem.category_name || "Без категории")
        : "Итог периода";
    }
    if (el.analyticsCategoryBreakdownChartValue) {
      el.analyticsCategoryBreakdownChartValue.textContent = hoveredItem
        ? core.formatMoney(hoveredItem.total_amount || 0)
        : core.formatMoney(activeBreakdown.total);
    }
    if (el.analyticsCategoryBreakdownChartMeta) {
      el.analyticsCategoryBreakdownChartMeta.textContent = hoveredItem
        ? `${Number(hoveredItem.share_pct || 0).toFixed(1)}% · ${Number(hoveredItem.operations_count || 0)} опер.`
        : activeBreakdown.items.length
          ? `${activeBreakdown.items.length} ${breakdownEntityCountLabel(activeBreakdown.level)} · ${activeBreakdown.totalOps} опер.`
          : "Нет данных за период";
    }
  }

  function setCategoryBreakdownHover(indexValue) {
    const index = Number(indexValue);
    if (!Number.isInteger(index) || index < 0 || index >= activeBreakdown.items.length) {
      applyCategoryBreakdownHover(null);
      return;
    }
    applyCategoryBreakdownHover(index);
  }

  function clearCategoryBreakdownHover() {
    applyCategoryBreakdownHover(null);
  }

  function toggleCategoryBreakdownVisibility(key) {
    const level = activeBreakdown.level || "category";
    const kind = activeBreakdown.kind || "expense";
    const next = hiddenBreakdownKeys(level, kind);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    writeHiddenBreakdownKeys(level, kind, next);
    if (activeBreakdown.payload) {
      renderCategoryBreakdown(activeBreakdown.payload, activeBreakdown.formatPct);
    }
    window.App.actions?.savePreferencesDebounced?.();
  }

  function showAllCategoryBreakdownItems() {
    const level = activeBreakdown.level || state.analyticsBreakdownLevel || "category";
    const kind = activeBreakdown.kind || state.analyticsCategoryKind || "expense";
    writeHiddenBreakdownKeys(level, kind, new Set());
    if (activeBreakdown.payload) {
      renderCategoryBreakdown(activeBreakdown.payload, activeBreakdown.formatPct);
    }
    window.App.actions?.savePreferencesDebounced?.();
  }

  function focusDefaultCategoryBreakdown() {
    applyCategoryBreakdownHover(null);
  }

  function bindCategoryBreakdownChartHover() {
    if (!el.analyticsCategoryBreakdownSvg) {
      return;
    }
    el.analyticsCategoryBreakdownSvg.querySelectorAll(".analytics-category-slice").forEach((node) => {
      node.addEventListener("pointerenter", () => {
        setCategoryBreakdownHover(node.dataset.analyticsCategoryIndex);
      });
      node.addEventListener("focus", () => {
        setCategoryBreakdownHover(node.dataset.analyticsCategoryIndex);
      });
    });
    el.analyticsCategoryBreakdownSvg.addEventListener("pointerleave", clearCategoryBreakdownHover);
    el.analyticsCategoryBreakdownSvg.addEventListener("focusout", (event) => {
      if (el.analyticsCategoryBreakdownSvg.contains(event.relatedTarget)) {
        return;
      }
      clearCategoryBreakdownHover();
    });
  }

  function renderCategoryBreakdown(data, formatPct) {
    const items = Array.isArray(data.category_breakdown) ? data.category_breakdown : [];
    const selectedKind = data.category_breakdown_kind || state.analyticsCategoryKind || "expense";
    const selectedLevel = data.category_breakdown_level || state.analyticsBreakdownLevel || "category";
    const hiddenKeys = hiddenBreakdownKeys(selectedLevel, selectedKind);
    let chartIndex = 0;
    const listItems = items.map((item, idx) => {
      const key = breakdownItemKey(selectedLevel, item);
      const isVisible = !hiddenKeys.has(key);
      return {
        ...item,
        palette_index: idx,
        breakdown_key: key,
        is_visible_in_chart: isVisible,
        chart_index: isVisible ? chartIndex++ : null,
      };
    });
    const visibleItems = listItems.filter((item) => item.is_visible_in_chart);
    const chartTotal = visibleItems.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
    const totalOps = visibleItems.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
    activeBreakdown = {
      payload: data,
      formatPct,
      items: visibleItems,
      listItems,
      kind: selectedKind,
      level: selectedLevel,
      total: chartTotal,
      totalOps,
      defaultIndex: visibleItems.length ? 0 : null,
      hoveredIndex: null,
    };

    if (el.analyticsCategoryBreakdownLabel) {
      el.analyticsCategoryBreakdownLabel.textContent = `Доли по сумме для ${categoryKindLabel(selectedKind)} по ${breakdownEntityLabel(selectedLevel)} в выбранном периоде`;
    }
    if (el.analyticsBreakdownShowAllBtn) {
      el.analyticsBreakdownShowAllBtn.disabled = visibleItems.length === listItems.length;
    }
    if (el.analyticsStructurePanel) {
      const title = el.analyticsStructurePanel.querySelector("h3");
      if (title) {
        title.textContent = breakdownTitle(selectedLevel);
      }
    }
    if (el.analyticsTopCategoriesSubtitle) {
      el.analyticsTopCategoriesSubtitle.textContent = `Топ-5 категорий ${categoryKindLabel(selectedKind)}`;
    }
    if (el.analyticsTopCategoriesTitle) {
      el.analyticsTopCategoriesTitle.textContent = selectedKind === "income"
        ? "Категории доходов"
        : selectedKind === "all"
          ? "Категории периода"
          : "Категории расходов";
    }
    core.syncSegmentedActive(el.analyticsBreakdownLevelTabs, "analytics-breakdown-level", selectedLevel);
    core.syncSegmentedActive(el.analyticsCategoryKindTabs, "analytics-category-kind", selectedKind);

    if (el.analyticsCategoryBreakdownSvg) {
      if (visibleItems.length) {
        let accAngle = 0;
        el.analyticsCategoryBreakdownSvg.innerHTML = visibleItems.map((item, idx) => {
          const share = Math.max(0, Number(item.share_pct || 0));
          const startAngle = accAngle;
          const endAngle = Math.min(360, accAngle + (share / 100) * 360);
          const midAngle = startAngle + ((endAngle - startAngle) / 2);
          const shiftX = Math.cos((midAngle - 90) * (Math.PI / 180)) * 10;
          const shiftY = Math.sin((midAngle - 90) * (Math.PI / 180)) * 10;
          accAngle = endAngle;
          return `
            <path
              class="analytics-category-slice"
              d="${buildDonutSegmentPath(DONUT_CENTER, DONUT_CENTER, DONUT_OUTER_RADIUS, DONUT_INNER_RADIUS, startAngle, endAngle)}"
              fill="${BREAKDOWN_PALETTE[idx % BREAKDOWN_PALETTE.length]}"
              style="--slice-shift-x:${shiftX.toFixed(2)}px; --slice-shift-y:${shiftY.toFixed(2)}px;"
              data-analytics-category-index="${idx}"
              data-analytics-category-id="${item.category_id ?? ""}"
              data-analytics-category-name="${escapeHtml(item.category_name || "Без категории")}"
              data-analytics-category-kind="${item.category_kind || selectedKind}"
              data-analytics-breakdown-level="${selectedLevel}"
            ></path>
          `;
        }).join("");
        bindCategoryBreakdownChartHover();
        el.analyticsCategoryBreakdownChart.classList.remove("analytics-category-donut-empty");
      } else {
        el.analyticsCategoryBreakdownSvg.innerHTML = "";
        el.analyticsCategoryBreakdownChart.classList.add("analytics-category-donut-empty");
      }
    }
    if (el.analyticsCategoryBreakdownChart) {
      el.analyticsCategoryBreakdownChart.style.background = visibleItems.length ? "transparent" : "rgba(116, 136, 173, 0.18)";
      el.analyticsCategoryBreakdownChart.classList.remove("analytics-category-donut-has-hover");
      el.analyticsCategoryBreakdownChart.classList.toggle("analytics-category-donut-has-data", visibleItems.length > 0);
    }

    renderInsightList(
      el.analyticsCategoryBreakdownList,
      listItems,
      (item, idx) => {
        const canDrilldown = selectedLevel === "category" && item.category_id !== null && item.category_id !== undefined;
        const itemName = escapeHtml(item.category_name || "Без категории");
        const itemClasses = [
          "analytics-insight-item",
          "analytics-category-breakdown-item",
          item.is_visible_in_chart ? "" : "is-muted",
        ].filter(Boolean).join(" ");
        return `
        <article class="${itemClasses}" data-analytics-category-index="${item.is_visible_in_chart ? item.chart_index : ""}" data-analytics-category-id="${canDrilldown ? item.category_id : ""}" data-analytics-category-name="${itemName}" data-analytics-category-kind="${item.category_kind || selectedKind}" data-analytics-breakdown-level="${selectedLevel}">
          <div class="analytics-insight-head">
            <div class="analytics-category-row-title">
              <span class="analytics-category-color" style="background:${BREAKDOWN_PALETTE[(item.is_visible_in_chart ? item.chart_index : item.palette_index) % BREAKDOWN_PALETTE.length]}"></span>
              <strong>${itemName}</strong>
            </div>
            <span class="muted-small">${core.formatMoney(item.total_amount || 0)}</span>
          </div>
          <div class="muted-small">
            Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}
            ${selectedKind === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}
          </div>
          <div class="muted-small">Изм. к прошлому: ${formatPct(item.change_pct)}</div>
          <div class="analytics-insight-actions">
            <button class="btn btn-secondary" type="button" data-analytics-breakdown-toggle="${item.breakdown_key}">${item.is_visible_in_chart ? "Выкл" : "Вкл"}</button>
            <span class="muted-small">${canDrilldown ? "Перейти к операциям этой категории" : "Агрегация по группе без drilldown"}</span>
            ${canDrilldown ? '<button class="btn btn-secondary" type="button">Открыть операции</button>' : ""}
          </div>
        </article>
      `;
      },
      selectedLevel === "group" ? "Нет групп за выбранный период" : "Нет категорий за выбранный период",
    );
    focusDefaultCategoryBreakdown();
  }

  function renderAnalyticsHighlights(data) {
    const trendModule = window.App.featureAnalyticsModules?.trend;
    const formatPct = trendModule?.formatPct || ((v) => String(v ?? "нет базы"));

    if (el.analyticsGlobalRangeLabel) {
      el.analyticsGlobalRangeLabel.textContent = `${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }
    renderCategoryBreakdown(data, formatPct);
  }

  function renderDashboardBreakdown(data) {
    const items = Array.isArray(data.category_breakdown) ? data.category_breakdown : [];
    const visibleItems = items.slice(0, 8);
    const total = items.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
    const totalOps = items.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
    const selectedKind = data.category_breakdown_kind || state.dashboardCategoryKind || "expense";
    const selectedLevel = data.category_breakdown_level || state.dashboardBreakdownLevel || "category";

    if (el.dashboardStructurePeriodLabel) {
      el.dashboardStructurePeriodLabel.textContent = `Структура ${categoryKindLabel(selectedKind)} по ${breakdownEntityLabel(selectedLevel)}: ${core.formatDateRu(data.date_from)} - ${core.formatDateRu(data.date_to)}`;
    }
    core.syncSegmentedActive(el.dashboardBreakdownLevelTabs, "dashboard-breakdown-level", selectedLevel);
    core.syncSegmentedActive(el.dashboardCategoryKindTabs, "dashboard-category-kind", selectedKind);
    if (el.dashboardCategoryBreakdownChartTitle) {
      el.dashboardCategoryBreakdownChartTitle.textContent = "Итог периода";
    }
    if (el.dashboardCategoryBreakdownChartValue) {
      el.dashboardCategoryBreakdownChartValue.textContent = core.formatMoney(total);
    }
    if (el.dashboardCategoryBreakdownChartMeta) {
      el.dashboardCategoryBreakdownChartMeta.textContent = visibleItems.length
        ? `${items.length} ${breakdownEntityCountLabel(selectedLevel)} · ${totalOps} опер.`
        : "Нет расходов за период";
    }
    if (el.dashboardCategoryBreakdownSvg) {
      if (visibleItems.length) {
        let accAngle = 0;
        el.dashboardCategoryBreakdownSvg.innerHTML = visibleItems.map((item, idx) => {
          const share = Math.max(0, Number(item.share_pct || 0));
          const startAngle = accAngle;
          const endAngle = Math.min(360, accAngle + (share / 100) * 360);
          accAngle = endAngle;
          return `
            <path
              class="analytics-category-slice"
              d="${buildDonutSegmentPath(DONUT_CENTER, DONUT_CENTER, DONUT_OUTER_RADIUS, DONUT_INNER_RADIUS, startAngle, endAngle)}"
              fill="${BREAKDOWN_PALETTE[idx % BREAKDOWN_PALETTE.length]}"
            ></path>
          `;
        }).join("");
        el.dashboardCategoryBreakdownChart?.classList.remove("analytics-category-donut-empty");
      } else {
        el.dashboardCategoryBreakdownSvg.innerHTML = "";
        el.dashboardCategoryBreakdownChart?.classList.add("analytics-category-donut-empty");
      }
    }
    renderInsightList(
      el.dashboardCategoryBreakdownList,
      items.slice(0, 5),
      (item, idx) => `
        <article class="analytics-insight-item analytics-category-breakdown-item">
          <div class="analytics-insight-head">
            <div class="analytics-category-row-title">
              <span class="analytics-category-color" style="background:${BREAKDOWN_PALETTE[idx % BREAKDOWN_PALETTE.length]}"></span>
              <strong>${escapeHtml(item.category_name || "Без категории")}</strong>
            </div>
            <span class="muted-small">${core.formatMoney(item.total_amount || 0)}</span>
          </div>
          <div class="muted-small">Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}${selectedKind === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}</div>
        </article>
      `,
      selectedLevel === "group" ? "Нет групп за выбранный период" : "Нет категорий за выбранный период",
    );
  }

  async function loadDashboardAnalyticsPreview(options = {}) {
    const ui = core.getUiSettings ? core.getUiSettings() : null;
    if (ui && ui.showDashboardAnalytics === false) {
      return null;
    }
    if (window.App.actions?.ensureAllTimeBounds) {
      await window.App.actions.ensureAllTimeBounds();
    }
    const force = options.force === true;
    const period = state.dashboardAnalyticsPeriod || "month";
    const { dateFrom, dateTo } = core.getPeriodBounds(period);
    const params = new URLSearchParams({
      period,
      date_from: dateFrom,
      date_to: dateTo,
      category_kind: state.dashboardCategoryKind || "expense",
      category_breakdown_level: state.dashboardBreakdownLevel || "category",
    });
    const cacheKey = `dashboard:highlights:${params.toString()}`;
    const trendModule = window.App.featureAnalyticsModules?.trend;
    const formatPct = trendModule?.formatPct || ((v) => String(v ?? "нет базы"));
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, HIGHLIGHTS_CACHE_TTL_MS);
      if (cached) {
        renderPeriodKpiBlocks(el.dashboardKpiPrimary, el.dashboardKpiSecondary, el.dashboardAnalyticsPeriodLabel, cached, formatPct);
        renderDashboardBreakdown(cached);
        return cached;
      }
    }
    const data = await core.requestJson(`/api/v1/dashboard/analytics/highlights?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    core.setUiRequestCache(cacheKey, data);
    renderPeriodKpiBlocks(el.dashboardKpiPrimary, el.dashboardKpiSecondary, el.dashboardAnalyticsPeriodLabel, data, formatPct);
    renderDashboardBreakdown(data);
    return data;
  }

  function buildHighlightsParams(month) {
    const period = state.analyticsGlobalPeriod || "month";
    const params = new URLSearchParams({
      period,
      month,
      category_kind: state.analyticsCategoryKind || "expense",
      category_breakdown_level: state.analyticsBreakdownLevel || "category",
    });
    if (period === "custom" && state.analyticsGlobalDateFrom && state.analyticsGlobalDateTo) {
      params.set("date_from", state.analyticsGlobalDateFrom);
      params.set("date_to", state.analyticsGlobalDateTo);
    }
    return params;
  }

  async function loadAnalyticsHighlights(options = {}) {
    const force = options.force === true;
    const calendarModule = window.App.featureAnalyticsModules?.calendar;
    const month = state.analyticsMonthAnchor || calendarModule?.serializeMonthAnchor?.(calendarModule.currentAnchorDate()) || "";
    const params = buildHighlightsParams(month);
    const cacheKey = `analytics:highlights:${params.toString()}`;

    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, HIGHLIGHTS_CACHE_TTL_MS);
      if (cached) {
        renderAnalyticsHighlights(cached);
        return cached;
      }
    }

    try {
      const data = await core.requestJson(`/api/v1/dashboard/analytics/highlights?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      core.setUiRequestCache(cacheKey, data);
      renderAnalyticsHighlights(data);
      return data;
    } catch (err) {
      const message = core.errorMessage ? core.errorMessage(err) : String(err);
      if (!String(message).includes("[404]")) {
        throw err;
      }
      const fallback = {
        period: state.analyticsGlobalPeriod || "month",
        category_breakdown_kind: state.analyticsCategoryKind || "expense",
        category_breakdown_level: state.analyticsBreakdownLevel || "category",
        date_from: state.analyticsGlobalDateFrom || `${month}-01`,
        date_to: state.analyticsGlobalDateTo || `${month}-01`,
        month,
        month_start: `${month}-01`,
        month_end: `${month}-01`,
        income_total: "0",
        expense_total: "0",
        balance: "0",
        prev_income_total: "0",
        prev_expense_total: "0",
        prev_balance: "0",
        prev_operations_count: 0,
        surplus_total: "0",
        deficit_total: "0",
        operations_count: 0,
        avg_daily_expense: "0",
        max_expense_day_date: null,
        max_expense_day_total: "0",
        income_change_pct: 0,
        expense_change_pct: 0,
        balance_change_pct: 0,
        operations_change_pct: 0,
        category_breakdown: [],
        top_operations: [],
        top_categories: [],
        anomalies: [],
        top_positions: [],
        price_increases: [],
      };
      renderAnalyticsHighlights(fallback);
      return fallback;
    }
  }

  window.App.featureAnalyticsModules = window.App.featureAnalyticsModules || {};
  window.App.featureAnalyticsModules.highlights = {
    loadAnalyticsHighlights,
    loadDashboardAnalyticsPreview,
    setCategoryBreakdownHover,
    clearCategoryBreakdownHover,
    focusDefaultCategoryBreakdown,
    toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems,
  };
})();
