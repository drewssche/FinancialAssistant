(() => {
  window.App = window.App || {};

  function bindChartSliceHover({ svgNode, hoverSetter, hoverClearer, attrName }) {
    if (!svgNode) {
      return;
    }
    svgNode.querySelectorAll(".analytics-category-slice").forEach((node) => {
      node.addEventListener("pointerenter", () => {
        hoverSetter?.(node.dataset[attrName]);
      });
      node.addEventListener("focus", () => {
        hoverSetter?.(node.dataset[attrName]);
      });
    });
    svgNode.addEventListener("pointerleave", () => {
      hoverClearer?.();
    });
    svgNode.addEventListener("focusout", (event) => {
      if (svgNode.contains(event.relatedTarget)) {
        return;
      }
      hoverClearer?.();
    });
  }

  function bindListItemHover({ container, attrName, hoverSetter, hoverClearer }) {
    if (!container) {
      return;
    }
    container.querySelectorAll(`[data-${attrName}]`).forEach((node) => {
      const attrValue = String(node.getAttribute(`data-${attrName}`) || "").trim();
      if (!attrValue) {
        return;
      }
      node.addEventListener("pointerenter", () => {
        hoverSetter?.(attrValue);
      });
      node.addEventListener("pointerleave", () => {
        hoverClearer?.();
      });
      node.addEventListener("focusin", () => {
        hoverSetter?.(attrValue);
      });
      node.addEventListener("focusout", (event) => {
        if (node.contains(event.relatedTarget)) {
          return;
        }
        hoverClearer?.();
      });
    });
  }

  const api = {
    bindChartSliceHover,
    bindListItemHover,
  };

  window.App.registerRuntimeModule?.("analytics-breakdown-ui-coordinator", api);
})();
