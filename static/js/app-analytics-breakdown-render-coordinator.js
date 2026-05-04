(() => {
  const ALL_KIND_ARCS = {
    income: { start: 188, end: 352 },
    expense: { start: 8, end: 172 },
  };
  const INCOME_PALETTE = ["#5fd3bc", "#7ee7cf", "#49bfa8", "#9bf3df", "#3ea792", "#74cbb7", "#a7f6e7"];
  const EXPENSE_PALETTE = ["#ff8f6b", "#ffb067", "#ff7c96", "#f7c14f", "#c084fc", "#7aa8ff", "#5eead4", "#fb7185", "#93c5fd"];

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

  function buildAllKindsDonutMarkup({ items, buildDonutSegmentPath, datasetBuilder, center, outerRadius, innerRadius }) {
    const grouped = {
      income: items.filter((item) => String(item?.category_kind || "") === "income"),
      expense: items.filter((item) => String(item?.category_kind || "") !== "income"),
    };
    return ["income", "expense"].map((kind) => {
      const groupItems = grouped[kind];
      const arc = ALL_KIND_ARCS[kind];
      const palette = kind === "income" ? INCOME_PALETTE : EXPENSE_PALETTE;
      const total = groupItems.reduce((acc, item) => acc + Number(item.total_amount || 0), 0);
      let currentAngle = arc.start;
      const availableDegrees = arc.end - arc.start;
      return groupItems.map((item, localIdx) => {
        const share = total > 0 ? Number(item.total_amount || 0) / total : 0;
        const startAngle = currentAngle;
        const endAngle = localIdx === groupItems.length - 1 ? arc.end : Math.min(arc.end, currentAngle + (share * availableDegrees));
        const midAngle = startAngle + ((endAngle - startAngle) / 2);
        const shiftX = Math.cos((midAngle - 90) * (Math.PI / 180)) * 10;
        const shiftY = Math.sin((midAngle - 90) * (Math.PI / 180)) * 10;
        currentAngle = endAngle;
        const globalIdx = Number.isInteger(item.chart_index) ? item.chart_index : items.indexOf(item);
        return `
          <path
            class="analytics-category-slice"
            d="${buildDonutSegmentPath(center, center, outerRadius, innerRadius, startAngle, endAngle)}"
            fill="${palette[localIdx % palette.length]}"
            style="--slice-shift-x:${shiftX.toFixed(2)}px; --slice-shift-y:${shiftY.toFixed(2)}px;"
            ${datasetBuilder(item, globalIdx)}
          ></path>
        `;
      }).join("");
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
        ? `Структура доходов и расходов по ${breakdownEntityLabel(selectedLevel)} в выбранном периоде`
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
        ? "Топ-5 категорий периода с раздельными доходами и расходами"
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

    if (el.analyticsCategoryBreakdownSvg) {
      if (visibleItems.length) {
        el.analyticsCategoryBreakdownSvg.innerHTML = selectedKind === "all"
          ? buildAllKindsDonutMarkup({
            items: visibleItems,
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
          })
          : buildDonutMarkup({
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
        const visibleIndex = item.is_visible_in_chart ? item.chart_index : item.palette_index;
        const displayShare = Number((item.display_share_pct ?? item.share_pct) ?? 0);
        const shareText = selectedKind === "all"
          ? `Доля в ${String(item.category_kind || "") === "income" ? "доходах" : "расходах"}: ${displayShare.toFixed(1)}%`
          : `Доля: ${Number(item.share_pct || 0).toFixed(1)}%`;
        return `
          <article class="${itemClasses}" data-analytics-category-index="${item.is_visible_in_chart ? item.chart_index : ""}" data-analytics-category-id="${canDrilldown ? item.category_id : ""}" data-analytics-category-name="${itemName}" data-analytics-category-kind="${item.category_kind || selectedKind}" data-analytics-breakdown-level="${selectedLevel}">
            <div class="analytics-insight-head">
              <div class="analytics-category-row-title">
                <span class="analytics-category-color" style="background:${selectedKind === "all"
                  ? (String(item.category_kind || "") === "income"
                    ? INCOME_PALETTE[visibleIndex % INCOME_PALETTE.length]
                    : EXPENSE_PALETTE[visibleIndex % EXPENSE_PALETTE.length])
                  : palette[visibleIndex % palette.length]}"></span>
                <strong>${itemName}</strong>
                ${kindBadge(item.category_kind || selectedKind)}
              </div>
              <span class="muted-small">${formatMoney(item.total_amount || 0)}</span>
            </div>
            <div class="muted-small">
              ${shareText} · Операций: ${item.operations_count}
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
    const payload = snapshot.payload || {};
    renderInsightList(
      el.analyticsPriceIncreasesList,
      payload.price_increases || [],
      (item) => `
        <article class="analytics-insight-item">
          <div class="analytics-insight-head">
            <strong>${escapeHtml(item.name || "Позиция")}</strong>
            <span class="muted-small">+${Number(item.change_pct || 0).toFixed(1)}%</span>
          </div>
          <div class="muted-small">
            ${item.shop_name ? `${escapeHtml(item.shop_name)} · ` : ""}
            ${formatMoney(item.previous_avg_unit_price || 0)} → ${formatMoney(item.current_avg_unit_price || 0)}
          </div>
        </article>
      `,
      "Нет заметного роста цен",
    );
    renderInsightList(
      el.analyticsTopDiscountSavingsList,
      payload.top_discount_savings || [],
      (item) => `
        <article class="analytics-insight-item">
          <div class="analytics-insight-head">
            <strong>${escapeHtml(item.name || "Позиция")}</strong>
            <span class="muted-small">${formatMoney(item.savings_total || 0)}</span>
          </div>
          <div class="muted-small">
            ${item.shop_name ? `${escapeHtml(item.shop_name)} · ` : ""}
            Скидка ${Number(item.discount_pct || 0).toFixed(1)}% · Потрачено ${formatMoney(item.actual_total || 0)}
          </div>
        </article>
      `,
      "Нет акций с обычной ценой",
    );
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
      el.dashboardCategoryBreakdownChartMeta.textContent = selectedKind === "all"
        ? `Доход ${formatMoney(snapshot.defaultIncomeTotal || 0)} · Расход ${formatMoney(snapshot.defaultExpenseTotal || 0)}`
        : items.length
          ? `${items.length} ${breakdownEntityCountLabel(selectedLevel)} · ${totalOps} опер.`
          : "Нет расходов за период";
    }
    if (el.dashboardCategoryBreakdownSvg) {
      if (items.length) {
        el.dashboardCategoryBreakdownSvg.innerHTML = selectedKind === "all"
          ? buildAllKindsDonutMarkup({
            items,
            buildDonutSegmentPath,
            datasetBuilder: (_, idx) => `data-dashboard-category-index="${idx}"`,
            center: donutCenter,
            outerRadius: donutOuterRadius,
            innerRadius: donutInnerRadius,
          })
          : buildDonutMarkup({
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
      (item, idx) => {
        const displayShare = Number((item.display_share_pct ?? item.share_pct) ?? 0);
        const shareText = selectedKind === "all"
          ? `Доля в ${String(item.category_kind || "") === "income" ? "доходах" : "расходах"}: ${displayShare.toFixed(1)}%`
          : `Доля: ${Number(item.share_pct || 0).toFixed(1)}%`;
        const color = selectedKind === "all"
          ? (String(item.category_kind || "") === "income"
            ? INCOME_PALETTE[idx % INCOME_PALETTE.length]
            : EXPENSE_PALETTE[idx % EXPENSE_PALETTE.length])
          : palette[idx % palette.length];
        return `
          <article class="analytics-insight-item analytics-category-breakdown-item" data-dashboard-category-index="${idx}">
            <div class="analytics-insight-head">
              <div class="analytics-category-row-title">
                <span class="analytics-category-color" style="background:${color}"></span>
                <strong>${escapeHtml(item.category_name || "Без категории")}</strong>
                ${kindBadge(item.category_kind || selectedKind)}
              </div>
              <span class="muted-small">${formatMoney(item.total_amount || 0)}</span>
            </div>
            <div class="muted-small">${shareText} · Операций: ${item.operations_count}${selectedKind === "all" ? ` · Тип: ${categoryKindShort(item.category_kind)}` : ""}</div>
          </article>
        `;
      },
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
