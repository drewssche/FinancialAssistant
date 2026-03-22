(() => {
  function bindCategoryKindTabs({ el, state, core, loadCategoriesTable, setStatus }) {
    if (!el.categoryKindTabs) {
      return;
    }
    el.categoryKindTabs.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-cat-kind]");
      if (!btn) {
        return;
      }
      state.categoryFilterKind = btn.dataset.catKind;
      core.syncSegmentedActive(el.categoryKindTabs, "cat-kind", state.categoryFilterKind);
      loadCategoriesTable?.({ reset: true }).catch((err) => setStatus?.(String(err)));
    });
  }

  function bindCategorySearch({ el, loadCategoriesTable, setStatus }) {
    if (!el.categorySearchQ) {
      return;
    }
    let debounceId = null;
    el.categorySearchQ.addEventListener("input", () => {
      if (debounceId) {
        clearTimeout(debounceId);
      }
      debounceId = setTimeout(() => {
        loadCategoriesTable?.({ reset: true }).catch((err) => setStatus?.(String(err)));
      }, 250);
    });
  }

  function bindCategoryCollapseExpand({ el, collapseAllCategoryGroups, expandAllCategoryGroups }) {
    if (el.categoriesCollapseAllBtn && collapseAllCategoryGroups) {
      el.categoriesCollapseAllBtn.addEventListener("click", () => {
        collapseAllCategoryGroups();
      });
    }
    if (el.categoriesExpandAllBtn && expandAllCategoryGroups) {
      el.categoriesExpandAllBtn.addEventListener("click", () => {
        expandAllCategoryGroups();
      });
    }
  }

  function bindCategoriesInfiniteObserver({
    el,
    state,
    getCategoriesObserver,
    setCategoriesObserver,
    loadMoreCategoriesTable,
    setStatus,
  }) {
    if (!el.categoriesInfiniteSentinel || !("IntersectionObserver" in window)) {
      return;
    }
    const existingObserver = getCategoriesObserver?.();
    if (existingObserver) {
      existingObserver.disconnect();
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry?.isIntersecting) {
          return;
        }
        if (state.activeSection !== "categories") {
          return;
        }
        if (!state.categoriesHasMore || state.categoriesLoading) {
          return;
        }
        loadMoreCategoriesTable?.().catch((err) => setStatus?.(String(err)));
      },
      {
        root: null,
        rootMargin: "240px 0px",
        threshold: 0,
      },
    );
    observer.observe(el.categoriesInfiniteSentinel);
    setCategoriesObserver?.(observer);
  }

  const api = {
    bindCategoryKindTabs,
    bindCategorySearch,
    bindCategoryCollapseExpand,
    bindCategoriesInfiniteObserver,
  };

  window.App.registerRuntimeModule?.("categories-section-coordinator", api);
})();
