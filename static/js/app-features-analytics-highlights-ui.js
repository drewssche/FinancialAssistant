(() => {
  const { state, el, core } = window.App;
  const shared = window.App.analyticsShared || {};
  const BREAKDOWN_PALETTE = ["#ff8f6b", "#5fd3bc", "#7aa8ff", "#ffd166", "#c084fc", "#5eead4", "#fb7185", "#93c5fd", "#a3e635"];
  const DONUT_CENTER = 130;
  const DONUT_OUTER_RADIUS = 118;
  const DONUT_INNER_RADIUS = 62;
  const escapeHtml = shared.escapeHtml || ((value) => String(value ?? ""));
  const renderInsightList = shared.renderInsightList || (() => {});
  const renderPeriodKpiBlocks = shared.renderPeriodKpiBlocks || (() => {});
  const categoryKindLabel = shared.categoryKindLabel || ((kind) => kind);
  const categoryKindShort = shared.categoryKindShort || ((kind) => kind);
  const breakdownEntityLabel = shared.breakdownEntityLabel || ((level) => level);
  const breakdownEntityCountLabel = shared.breakdownEntityCountLabel || ((level) => level);
  const breakdownTitle = shared.breakdownTitle || ((level) => level);
  const breakdownItemKey = shared.breakdownItemKey || ((level, item) => `${level}:${item?.id ?? "none"}`);
  const buildDonutSegmentPath = shared.buildDonutSegmentPath || (() => "");
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
  let activeDashboardBreakdown = {
    items: [],
    kind: "expense",
    level: "category",
    total: 0,
    totalOps: 0,
    defaultIndex: null,
    hoveredIndex: null,
  };

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

  function applyDashboardBreakdownHover(index = null) {
    activeDashboardBreakdown.hoveredIndex = Number.isInteger(index) ? index : null;
    const resolvedIndex = activeDashboardBreakdown.hoveredIndex ?? activeDashboardBreakdown.defaultIndex;
    const hasHover = activeDashboardBreakdown.hoveredIndex !== null;
    const hasDefault = !hasHover && activeDashboardBreakdown.defaultIndex !== null;
    const resolvedColor = Number.isInteger(resolvedIndex)
      ? BREAKDOWN_PALETTE[resolvedIndex % BREAKDOWN_PALETTE.length]
      : "";
    if (el.dashboardCategoryBreakdownChart) {
      el.dashboardCategoryBreakdownChart.classList.toggle("analytics-category-donut-has-hover", hasHover);
      el.dashboardCategoryBreakdownChart.classList.toggle("analytics-category-donut-has-default", hasDefault);
      if (resolvedColor) {
        el.dashboardCategoryBreakdownChart.style.setProperty("--active-slice-color", resolvedColor);
      } else {
        el.dashboardCategoryBreakdownChart.style.removeProperty("--active-slice-color");
      }
    }
    document.querySelectorAll("[data-dashboard-category-index]").forEach((node) => {
      const nodeIndex = Number(node.dataset.dashboardCategoryIndex);
      const isActive = hasHover && nodeIndex === resolvedIndex;
      const isInactive = hasHover && nodeIndex !== resolvedIndex;
      const isDefault = hasDefault && nodeIndex === resolvedIndex;
      node.classList.toggle("is-active", isActive);
      node.classList.toggle("is-inactive", isInactive);
      node.classList.toggle("is-default", isDefault);
    });
    const hoveredItem = Number.isInteger(resolvedIndex) ? activeDashboardBreakdown.items[resolvedIndex] : null;
    if (el.dashboardCategoryBreakdownChartTitle) {
      el.dashboardCategoryBreakdownChartTitle.textContent = hoveredItem
        ? String(hoveredItem.category_name || "Без категории")
        : "Итог периода";
    }
    if (el.dashboardCategoryBreakdownChartValue) {
      el.dashboardCategoryBreakdownChartValue.textContent = hoveredItem
        ? core.formatMoney(hoveredItem.total_amount || 0)
        : core.formatMoney(activeDashboardBreakdown.total);
    }
    if (el.dashboardCategoryBreakdownChartMeta) {
      el.dashboardCategoryBreakdownChartMeta.textContent = hoveredItem
        ? `${Number(hoveredItem.share_pct || 0).toFixed(1)}% · ${Number(hoveredItem.operations_count || 0)} опер.`
        : activeDashboardBreakdown.items.length
          ? `${activeDashboardBreakdown.items.length} ${breakdownEntityCountLabel(activeDashboardBreakdown.level)} · ${activeDashboardBreakdown.totalOps} опер.`
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

  function setDashboardBreakdownHover(indexValue) {
    const index = Number(indexValue);
    if (!Number.isInteger(index) || index < 0 || index >= activeDashboardBreakdown.items.length) {
      applyDashboardBreakdownHover(null);
      return;
    }
    applyDashboardBreakdownHover(index);
  }

  function clearDashboardBreakdownHover() {
    applyDashboardBreakdownHover(null);
  }

  function bindBreakdownChartHover(svgNode, hoverSetter, hoverClearer, attrName) {
    if (!svgNode) {
      return;
    }
    svgNode.querySelectorAll(".analytics-category-slice").forEach((node) => {
      node.addEventListener("pointerenter", () => {
        hoverSetter(node.dataset[attrName]);
      });
      node.addEventListener("focus", () => {
        hoverSetter(node.dataset[attrName]);
      });
    });
    svgNode.addEventListener("pointerleave", hoverClearer);
    svgNode.addEventListener("focusout", (event) => {
      if (svgNode.contains(event.relatedTarget)) {
        return;
      }
      hoverClearer();
    });
  }

  function buildDonutMarkup(items, datasetBuilder) {
    let accAngle = 0;
    return items.map((item, idx) => {
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
          ${datasetBuilder(item, idx)}
        ></path>
      `;
    }).join("");
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
        el.analyticsCategoryBreakdownSvg.innerHTML = buildDonutMarkup(
          visibleItems,
          (item, idx) => `
            data-analytics-category-index="${idx}"
            data-analytics-category-id="${item.category_id ?? ""}"
            data-analytics-category-name="${escapeHtml(item.category_name || "Без категории")}"
            data-analytics-category-kind="${item.category_kind || selectedKind}"
            data-analytics-breakdown-level="${selectedLevel}"
          `,
        );
        bindBreakdownChartHover(el.analyticsCategoryBreakdownSvg, setCategoryBreakdownHover, clearCategoryBreakdownHover, "analyticsCategoryIndex");
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
      (item) => {
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
              <button class="analytics-visibility-toggle ${item.is_visible_in_chart ? "is-on" : "is-off"}" type="button" aria-pressed="${item.is_visible_in_chart ? "true" : "false"}" data-analytics-breakdown-toggle="${item.breakdown_key}">
                <span class="analytics-visibility-toggle-track"><span class="analytics-visibility-toggle-thumb"></span></span>
                <span class="analytics-visibility-toggle-label">${item.is_visible_in_chart ? "Вкл" : "Выкл"}</span>
              </button>
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
    const total = items.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
    const totalOps = items.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
    const selectedKind = data.category_breakdown_kind || state.dashboardCategoryKind || "expense";
    const selectedLevel = data.category_breakdown_level || state.dashboardBreakdownLevel || "category";
    activeDashboardBreakdown = {
      items,
      kind: selectedKind,
      level: selectedLevel,
      total,
      totalOps,
      defaultIndex: items.length ? 0 : null,
      hoveredIndex: null,
    };

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
      el.dashboardCategoryBreakdownChartMeta.textContent = items.length
        ? `${items.length} ${breakdownEntityCountLabel(selectedLevel)} · ${totalOps} опер.`
        : "Нет расходов за период";
    }
    if (el.dashboardCategoryBreakdownSvg) {
      if (items.length) {
        el.dashboardCategoryBreakdownSvg.innerHTML = buildDonutMarkup(items, (_, idx) => `data-dashboard-category-index="${idx}"`);
        bindBreakdownChartHover(el.dashboardCategoryBreakdownSvg, setDashboardBreakdownHover, clearDashboardBreakdownHover, "dashboardCategoryIndex");
        el.dashboardCategoryBreakdownChart?.classList.remove("analytics-category-donut-empty");
        el.dashboardCategoryBreakdownChart?.classList.add("analytics-category-donut-has-data");
      } else {
        el.dashboardCategoryBreakdownSvg.innerHTML = "";
        el.dashboardCategoryBreakdownChart?.classList.add("analytics-category-donut-empty");
        el.dashboardCategoryBreakdownChart?.classList.remove("analytics-category-donut-has-data");
      }
    }
    renderInsightList(
      el.dashboardCategoryBreakdownList,
      items,
      (item, idx) => `
        <article class="analytics-insight-item analytics-category-breakdown-item" data-dashboard-category-index="${idx}">
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
    applyDashboardBreakdownHover(null);
  }

  window.App.featureAnalyticsHighlightsUi = {
    renderPeriodKpiBlocks,
    renderCategoryBreakdown,
    renderAnalyticsHighlights,
    renderDashboardBreakdown,
    setCategoryBreakdownHover,
    clearCategoryBreakdownHover,
    setDashboardBreakdownHover,
    clearDashboardBreakdownHover,
    focusDefaultCategoryBreakdown,
    toggleCategoryBreakdownVisibility,
    showAllCategoryBreakdownItems,
  };
})();
