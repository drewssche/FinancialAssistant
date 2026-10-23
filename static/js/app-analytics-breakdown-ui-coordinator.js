(() => {
  window.App = window.App || {};

  // Both surfaces use one delegated binding, retained across chart/list redraws.
  function bindChartSliceHover({ svgNode, hoverSetter, hoverClearer, attrName }) {
    window.App.getRuntimeModule?.("analytics-hover-coordinator")?.bindIndexedHover({
      container: svgNode,
      itemSelector: ".analytics-category-slice",
      getIndex: node => node.dataset[attrName],
      setHover: hoverSetter,
      clearHover: hoverClearer,
    });
  }

  function bindListItemHover({ container, attrName, hoverSetter, hoverClearer }) {
    window.App.getRuntimeModule?.("analytics-hover-coordinator")?.bindIndexedHover({
      container,
      itemSelector: `[data-${attrName}]`,
      getIndex: node => node.getAttribute(`data-${attrName}`),
      setHover: hoverSetter,
      clearHover: hoverClearer,
    });
  }

  window.App.registerRuntimeModule?.("analytics-breakdown-ui-coordinator", {
    bindChartSliceHover, bindListItemHover,
  });
})();
