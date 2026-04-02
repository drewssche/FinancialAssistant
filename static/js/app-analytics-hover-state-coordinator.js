(() => {
  function setCenterText(node, text) {
    if (!node) {
      return;
    }
    const value = String(text || "").trim();
    node.textContent = value;
    if (value) {
      node.setAttribute("title", value);
      node.setAttribute("aria-label", value);
    } else {
      node.removeAttribute("title");
      node.removeAttribute("aria-label");
    }
  }

  window.App = window.App || {};

  function applyBreakdownHoverState({
    snapshot,
    index = null,
    chartNode,
    indexSelector,
    indexDatasetName,
    titleNode,
    periodNode,
    valueNode,
    metaNode,
    palette,
    formatMoney,
    countLabel,
  }) {
    snapshot.hoveredIndex = Number.isInteger(index) ? index : null;
    const resolvedIndex = snapshot.hoveredIndex ?? snapshot.defaultIndex;
    const hasHover = snapshot.hoveredIndex !== null;
    const hasDefault = !hasHover && snapshot.defaultIndex !== null;
    const resolvedColor = Number.isInteger(resolvedIndex)
      ? palette[resolvedIndex % palette.length]
      : "";

    if (chartNode) {
      chartNode.classList.toggle("analytics-category-donut-has-hover", hasHover);
      chartNode.classList.toggle("analytics-category-donut-has-default", hasDefault);
      if (resolvedColor) {
        chartNode.style.setProperty("--active-slice-color", resolvedColor);
      } else {
        chartNode.style.removeProperty("--active-slice-color");
      }
    }

    document.querySelectorAll(indexSelector).forEach((node) => {
      const nodeIndex = Number(node.dataset[indexDatasetName]);
      const isActive = hasHover && nodeIndex === resolvedIndex;
      const isInactive = hasHover && nodeIndex !== resolvedIndex;
      const isDefault = hasDefault && nodeIndex === resolvedIndex;
      node.classList.toggle("is-active", isActive);
      node.classList.toggle("is-inactive", isInactive);
      node.classList.toggle("is-default", isDefault);
    });

    const hoveredItem = Number.isInteger(resolvedIndex) ? snapshot.items[resolvedIndex] : null;
    setCenterText(
      titleNode,
      hoveredItem
        ? String(hoveredItem.category_name || "Без категории")
        : (snapshot.defaultTitle || "Итог периода"),
    );
    if (periodNode) {
      periodNode.textContent = snapshot.periodLabel || "Нет периода";
    }
    if (valueNode) {
      valueNode.textContent = hoveredItem
        ? formatMoney(hoveredItem.total_amount || 0)
        : formatMoney(snapshot.total);
    }
    if (metaNode) {
      metaNode.textContent = hoveredItem
        ? `${Number(hoveredItem.share_pct || 0).toFixed(1)}% · ${Number(hoveredItem.operations_count || 0)} опер.`
        : snapshot.kind === "all"
          ? `Доход ${formatMoney(snapshot.defaultIncomeTotal || 0)} · Расход ${formatMoney(snapshot.defaultExpenseTotal || 0)}`
        : snapshot.items.length
          ? `${snapshot.items.length} ${countLabel(snapshot.level)} · ${snapshot.totalOps} опер.`
          : "Нет данных за период";
    }
  }

  const api = {
    applyBreakdownHoverState,
  };

  window.App.registerRuntimeModule?.("analytics-hover-state-coordinator", api);
})();
