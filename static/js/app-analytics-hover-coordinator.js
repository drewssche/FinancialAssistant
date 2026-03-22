(() => {
  window.App = window.App || {};

  function bindIndexedHover({
    container,
    itemSelector,
    getIndex,
    setHover,
    clearHover,
  }) {
    if (!container) {
      return;
    }
    container.addEventListener("mouseover", (event) => {
      const node = event.target.closest(itemSelector);
      if (!node) {
        return;
      }
      setHover?.(getIndex(node));
    });
    container.addEventListener("focusin", (event) => {
      const node = event.target.closest(itemSelector);
      if (!node) {
        return;
      }
      setHover?.(getIndex(node));
    });
    container.addEventListener("mouseout", (event) => {
      const current = event.target.closest(itemSelector);
      const related = event.relatedTarget instanceof Element ? event.relatedTarget.closest(itemSelector) : null;
      if (!current || (related && getIndex(related) === getIndex(current))) {
        return;
      }
      if (!container.contains(event.relatedTarget)) {
        clearHover?.();
      }
    });
    container.addEventListener("focusout", (event) => {
      if (container.contains(event.relatedTarget)) {
        return;
      }
      clearHover?.();
    });
    container.addEventListener("mouseleave", () => {
      clearHover?.();
    });
  }

  const api = {
    bindIndexedHover,
  };

  window.App.registerRuntimeModule?.("analytics-hover-coordinator", api);
})();
