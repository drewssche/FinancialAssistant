(() => {
  window.App = window.App || {};

  const bindings = new WeakMap();

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
    const previous = bindings.get(container);
    bindings.set(container, { itemSelector, getIndex, setHover, clearHover });
    if (previous) return;
    const currentBinding = () => bindings.get(container);
    container.addEventListener("mouseover", (event) => {
      const { itemSelector, getIndex, setHover, clearHover } = currentBinding();
      const node = event.target.closest(itemSelector);
      if (!node) {
        return;
      }
      const index = getIndex(node);
      if (index === null || index === undefined || String(index).trim() === "") { clearHover?.(); return; }
      setHover?.(index);
    });
    container.addEventListener("focusin", (event) => {
      const { itemSelector, getIndex, setHover, clearHover } = currentBinding();
      const node = event.target.closest(itemSelector);
      if (!node) {
        return;
      }
      const index = getIndex(node);
      if (index === null || index === undefined || String(index).trim() === "") { clearHover?.(); return; }
      setHover?.(index);
    });
    container.addEventListener("mouseout", (event) => {
      const { itemSelector, getIndex, setHover, clearHover } = currentBinding();
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
      const { itemSelector, getIndex, setHover, clearHover } = currentBinding();
      if (container.contains(event.relatedTarget)) {
        return;
      }
      clearHover?.();
    });
    container.addEventListener("mouseleave", () => {
      currentBinding().clearHover?.();
    });
  }

  const api = {
    bindIndexedHover,
  };

  window.App.registerRuntimeModule?.("analytics-hover-coordinator", api);
})();
