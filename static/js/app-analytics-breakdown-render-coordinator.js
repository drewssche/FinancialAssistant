(() => {
  function splitBreakdownItems(items = []) {
    return {
      income: items.filter((item) => String(item?.category_kind || "") === "income"),
      expense: items.filter((item) => String(item?.category_kind || "") !== "income"),
    };
  }

  function buildDonutMarkup({ items, palette, buildDonutSegmentPath, datasetBuilder, center, outerRadius, innerRadius }) {
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
          d="${buildDonutSegmentPath(center, center, outerRadius, innerRadius, startAngle, endAngle)}"
          fill="${palette[idx % palette.length]}"
          style="--slice-shift-x:${shiftX.toFixed(2)}px; --slice-shift-y:${shiftY.toFixed(2)}px;"
          ${datasetBuilder(item, idx)}
        ></path>
      `;
    }).join("");
  }

  function renderSplitBreakdownMarkup({
    items,
    palette,
    buildDonutSegmentPath,
    center,
    outerRadius,
    innerRadius,
    formatMoney,
    escapeHtml,
  }) {
    const groups = splitBreakdownItems(items);
    const cards = [
      { key: "income", title: "Доходы", toneClass: "income", items: groups.income },
      { key: "expense", title: "Расходы", toneClass: "expense", items: groups.expense },
    ];
    return cards.map((group) => {
      const total = group.items.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
      const operations = group.items.reduce((acc, item) => acc + Number(item.operations_count || 0), 0);
      const normalizedItems = total > 0
        ? group.items.map((item) => ({
          ...item,
          share_pct: (Number(item.total_amount || 0) / total) * 100,
        }))
        : group.items;
      const markup = group.items.length
        ? buildDonutMarkup({
          items: normalizedItems,
          palette,
          buildDonutSegmentPath,
          datasetBuilder: (_, idx) => `data-split-breakdown-index="${idx}"`,
          center,
          outerRadius,
          innerRadius,
        })
        : "";
      return `
        <article class="analytics-category-split-card analytics-category-split-card-${group.toneClass}">
          <div class="analytics-category-split-title-row">
            <span class="analytics-breakdown-kind-badge analytics-breakdown-kind-badge-${group.toneClass}">${escapeHtml(group.title)}</span>
            <span class="muted-small">${group.items.length} кат.</span>
          </div>
          <div class="analytics-category-donut analytics-category-donut-mini ${group.items.length ? "analytics-category-donut-has-data" : "analytics-category-donut-empty"}">
            <svg class="analytics-category-donut-svg" viewBox="0 0 260 260">${markup}</svg>
            <div class="analytics-category-donut-hole analytics-category-donut-hole-mini">
              <span class="analytics-category-donut-title muted-small">${escapeHtml(group.title)}</span>
              <strong>${escapeHtml(formatMoney(total))}</strong>
              <span class="muted-small">${escapeHtml(String(operations))} опер.</span>
            </div>
          </div>
        </article>
      `;
    }).join("");
  }

  function renderAnalyticsCategoryBreakdownView({
    snapshot,
    el,
    palette,
    categoryKindLabel,
    categoryKindShort,
    breakdownEntityLabel,
    breakdownEntityCountLabel,
    breakdownTitle,
    renderInsightList,
    escapeHtml,
    formatMoney,
    syncSegmentedActive,
    breakdownUiCoordinator,
    setCategoryBreakdownHover,
    clearCategoryBreakdownHover,
    buildDonutSegmentPath,
    donutCenter,
    donutOuterRadius,
    donutInnerRadius,
  }) {
    const visibleItems = snapshot.items || [];
    const listItems = snapshot.listItems || [];
    const selectedKind = snapshot.kind || "expense";
    const selectedLevel = snapshot.level || "category";
    const kindBadge = (itemKind) => selectedKind === "all"
      ? `<span class="analytics-breakdown-kind-badge analytics-breakdown-kind-badge-${itemKind === "income" ? "income" : "expense"}">${escapeHtml(categoryKindShort(itemKind))}</span>`
      : "";

    if (el.analyticsCategoryBreakdownLabel) {
      el.analyticsCategoryBreakdownLabel.textContent = selectedKind === "all"
        ? `Раздельная структура доходов и расходов по ${breakdownEntityLabel(selectedLevel)} в выбранном периоде`
        : `Доли по сумме для ${categoryKindLabel(selectedKind)} по ${breakdownEntityLabel(selectedLevel)} в выбранном периоде`;
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
      el.analyticsTopCategoriesSubtitle.textContent = selectedKind === "all"
        ? "Топ-5 категорий периода с разделением доходов и расходов"
        : `Топ-5 категорий ${categoryKindLabel(selectedKind)}`;
    }
    if (el.analyticsTopCategoriesTitle) {
      el.analyticsTopCategoriesTitle.textContent = selectedKind === "income"
        ? "Категории доходов"
        : selectedKind === "all"
          ? "Категории периода"
          : "Категории расходов";
    }
    syncSegmentedActive(el.analyticsBreakdownLevelTabs, "analytics-breakdown-level", selectedLevel);
    syncSegmentedActive(el.analyticsCategoryKindTabs, "analytics-category-kind", selectedKind);

    if (el.analyticsCategoryBreakdownSplit) {
      const splitMode = selectedKind === "all";
      el.analyticsCategoryBreakdownSplit.classList.toggle("hidden", !splitMode);
      if (splitMode) {
        el.analyticsCategoryBreakdownSplit.innerHTML = renderSplitBreakdownMarkup({
          items: visibleItems,
          palette,
          buildDonutSegmentPath,
          center: donutCenter,
          outerRadius: donutOuterRadius,
          innerRadius: donutInnerRadius,
          formatMoney,
          escapeHtml,
        });
      } else {
        el.analyticsCategoryBreakdownSplit.innerHTML = "";
      }
    }
    if (el.analyticsCategoryBreakdownChart) {
      el.analyticsCategoryBreakdownChart.classList.toggle("hidden", selectedKind === "all");
    }

    if (el.analyticsCategoryBreakdownSvg) {
      if (visibleItems.length) {
        el.analyticsCategoryBreakdownSvg.innerHTML = buildDonutMarkup({
          items: visibleItems,
          palette,
          buildDonutSegmentPath,
          datasetBuilder: (item, idx) => `
            data-analytics-category-index="${idx}"
            data-analytics-category-id="${item.category_id ?? ""}"
            data-analytics-category-name="${escapeHtml(item.category_name || "Без категории")}"
            data-analytics-category-kind="${item.category_kind || selectedKind}"
            data-analytics-breakdown-level="${selectedLevel}"
          `,
          center: donutCenter,
          outerRadius: donutOuterRadius,
          innerRadius: donutInnerRadius,
        });
        breakdownUiCoordinator.bindChartSliceHover?.({
          svgNode: el.analyticsCategoryBreakdownSvg,
          hoverSetter: setCategoryBreakdownHover,
          hoverClearer: clearCategoryBreakdownHover,
          attrName: "analyticsCategoryIndex",
        });
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
                <span class="analytics-category-color" style="background:${palette[(item.is_visible_in_chart ? item.chart_index : item.palette_index) % palette.length]}"></span>
                <strong>${itemName}</strong>
                ${kindBadge(item.category_kind || selectedKind)}
              </div>
              <span class="muted-small">${formatMoney(item.total_amount || 0)}</span>
            </div>
            <div class="muted-small">
              Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}
              ${selectedKind === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}
            </div>
            <div class="analytics-insight-actions">
              <button class="analytics-visibility-toggle ${item.is_visible_in_chart ? "is-on" : "is-off"}" type="button" aria-pressed="${item.is_visible_in_chart ? "true" : "false"}" data-analytics-breakdown-toggle="${item.breakdown_key}">
                <span class="analytics-visibility-toggle-track"><span class="analytics-visibility-toggle-thumb"></span></span>
                <span class="analytics-visibility-toggle-label">${item.is_visible_in_chart ? "Вкл" : "Выкл"}</span>
              </button>
              ${canDrilldown ? '<button class="btn btn-secondary" type="button">Открыть операции</button>' : ""}
            </div>
          </article>
        `;
      },
      selectedLevel === "group" ? "Нет групп за выбранный период" : "Нет категорий за выбранный период",
    );
    breakdownUiCoordinator.bindListItemHover?.({
      container: el.analyticsCategoryBreakdownList,
      attrName: "analytics-category-index",
      hoverSetter: setCategoryBreakdownHover,
      hoverClearer: clearCategoryBreakdownHover,
    });
  }

  function renderDashboardBreakdownView({
    snapshot,
    data,
    el,
    palette,
    escapeHtml,
    renderInsightList,
    formatMoney,
    syncSegmentedActive,
    categoryKindLabel,
    categoryKindShort,
    breakdownEntityLabel,
    breakdownEntityCountLabel,
    breakdownUiCoordinator,
    setDashboardBreakdownHover,
    clearDashboardBreakdownHover,
    buildDonutSegmentPath,
    donutCenter,
    donutOuterRadius,
    donutInnerRadius,
  }) {
    const items = snapshot.items || [];
    const total = snapshot.total || 0;
    const totalOps = snapshot.totalOps || 0;
    const selectedKind = snapshot.kind || "expense";
    const selectedLevel = snapshot.level || "category";
    const kindBadge = (itemKind) => selectedKind === "all"
      ? `<span class="analytics-breakdown-kind-badge analytics-breakdown-kind-badge-${itemKind === "income" ? "income" : "expense"}">${escapeHtml(categoryKindShort(itemKind))}</span>`
      : "";

    if (el.dashboardStructurePeriodLabel) {
      el.dashboardStructurePeriodLabel.textContent = selectedKind === "all"
        ? `Структура доходов и расходов по ${breakdownEntityLabel(selectedLevel)}: ${data.date_from} - ${data.date_to}`
        : `Структура ${categoryKindLabel(selectedKind)} по ${breakdownEntityLabel(selectedLevel)}: ${data.date_from} - ${data.date_to}`;
    }
    syncSegmentedActive(el.dashboardBreakdownLevelTabs, "dashboard-breakdown-level", selectedLevel);
    syncSegmentedActive(el.dashboardCategoryKindTabs, "dashboard-category-kind", selectedKind);
    if (el.dashboardCategoryBreakdownSplit) {
      const splitMode = selectedKind === "all";
      el.dashboardCategoryBreakdownSplit.classList.toggle("hidden", !splitMode);
      if (splitMode) {
        el.dashboardCategoryBreakdownSplit.innerHTML = renderSplitBreakdownMarkup({
          items,
          palette,
          buildDonutSegmentPath,
          center: donutCenter,
          outerRadius: donutOuterRadius,
          innerRadius: donutInnerRadius,
          formatMoney,
          escapeHtml,
        });
      } else {
        el.dashboardCategoryBreakdownSplit.innerHTML = "";
      }
    }
    if (el.dashboardCategoryBreakdownChart) {
      el.dashboardCategoryBreakdownChart.classList.toggle("hidden", selectedKind === "all");
    }
    if (el.dashboardCategoryBreakdownChartTitle) {
      el.dashboardCategoryBreakdownChartTitle.textContent = "Итог периода";
    }
    if (el.dashboardCategoryBreakdownChartPeriod) {
      el.dashboardCategoryBreakdownChartPeriod.textContent = snapshot.periodLabel;
    }
    if (el.dashboardCategoryBreakdownChartValue) {
      el.dashboardCategoryBreakdownChartValue.textContent = formatMoney(total);
    }
    if (el.dashboardCategoryBreakdownChartMeta) {
      el.dashboardCategoryBreakdownChartMeta.textContent = items.length
        ? `${items.length} ${breakdownEntityCountLabel(selectedLevel)} · ${totalOps} опер.`
        : "Нет расходов за период";
    }
    if (el.dashboardCategoryBreakdownSvg) {
      if (items.length) {
        el.dashboardCategoryBreakdownSvg.innerHTML = buildDonutMarkup({
          items,
          palette,
          buildDonutSegmentPath,
          datasetBuilder: (_, idx) => `data-dashboard-category-index="${idx}"`,
          center: donutCenter,
          outerRadius: donutOuterRadius,
          innerRadius: donutInnerRadius,
        });
        breakdownUiCoordinator.bindChartSliceHover?.({
          svgNode: el.dashboardCategoryBreakdownSvg,
          hoverSetter: setDashboardBreakdownHover,
          hoverClearer: clearDashboardBreakdownHover,
          attrName: "dashboardCategoryIndex",
        });
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
              <span class="analytics-category-color" style="background:${palette[idx % palette.length]}"></span>
              <strong>${escapeHtml(item.category_name || "Без категории")}</strong>
              ${kindBadge(item.category_kind || selectedKind)}
            </div>
            <span class="muted-small">${formatMoney(item.total_amount || 0)}</span>
          </div>
          <div class="muted-small">Доля: ${Number(item.share_pct || 0).toFixed(1)}% · Операций: ${item.operations_count}${selectedKind === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}</div>
        </article>
      `,
      selectedLevel === "group" ? "Нет групп за выбранный период" : "Нет категорий за выбранный период",
    );
    breakdownUiCoordinator.bindListItemHover?.({
      container: el.dashboardCategoryBreakdownList,
      attrName: "dashboard-category-index",
      hoverSetter: setDashboardBreakdownHover,
      hoverClearer: clearDashboardBreakdownHover,
    });
  }

  window.App.registerRuntimeModule?.("analytics-breakdown-render-coordinator", {
    buildDonutMarkup,
    renderAnalyticsCategoryBreakdownView,
    renderDashboardBreakdownView,
  });
})();
