(() => {
  const DEFAULT_CATEGORY_USAGE_KEY = "fa_category_usage_v1";

  function readUsageMap(storageKey = DEFAULT_CATEGORY_USAGE_KEY) {
    try {
      const raw = localStorage.getItem(storageKey);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function sortCategoriesByUsage(categories, query = "", storageKey = DEFAULT_CATEGORY_USAGE_KEY) {
    const usage = readUsageMap(storageKey);
    const normalizedQuery = String(query || "").trim().toLowerCase();
    return (categories || [])
      .filter((item) => {
        if (!normalizedQuery) {
          return true;
        }
        return item.name.toLowerCase().includes(normalizedQuery) || (item.group_name || "").toLowerCase().includes(normalizedQuery);
      })
      .map((item) => ({ ...item, usage: Number(usage[String(item.id)] || 0) }))
      .sort((a, b) => {
        if (b.usage !== a.usage) {
          return b.usage - a.usage;
        }
        const colorA = (a.group_accent_color || "~").toLowerCase();
        const colorB = (b.group_accent_color || "~").toLowerCase();
        if (colorA !== colorB) {
          return colorA.localeCompare(colorB, "ru");
        }
        const groupA = (a.group_name || "~").toLowerCase();
        const groupB = (b.group_name || "~").toLowerCase();
        if (groupA !== groupB) {
          return groupA.localeCompare(groupB, "ru");
        }
        return a.name.localeCompare(b.name, "ru");
      });
  }

  function createChipButton({ datasetName, datasetValue = "", selected = false, html = "", className = "chip-btn" } = {}) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = className;
    if (selected) {
      btn.classList.add("active");
    }
    if (datasetName) {
      btn.dataset[datasetName] = String(datasetValue ?? "");
    }
    btn.innerHTML = html;
    return btn;
  }

  function createMetaChipButton({ datasetName, datasetValue = "", selected = false, label = "", core } = {}) {
    return createChipButton({
      datasetName,
      datasetValue,
      selected,
      className: "chip-btn chip-btn-meta",
      html: core.renderMetaChip(label),
    });
  }

  function createActionChipButton({ datasetName, datasetValue = "", label = "" } = {}) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip-btn chip-btn-create";
    if (datasetName) {
      btn.dataset[datasetName] = String(datasetValue ?? "");
    }
    btn.textContent = label;
    return btn;
  }

  function eventPathIncludes(event, matcher) {
    if (!event || typeof matcher !== "function") {
      return false;
    }
    const path = typeof event.composedPath === "function" ? event.composedPath() : [];
    if (path.length) {
      return path.some((node) => matcher(node));
    }
    return matcher(event.target);
  }

  function setPopoverOpen(popover, isOpen, options = {}) {
    if (!popover) {
      return;
    }
    const owners = Array.isArray(options.owners) ? options.owners.filter(Boolean) : [];
    if (owners.length) {
      popover.__appPopoverOwners = owners;
    }
    if (typeof options.onClose === "function") {
      popover.__appPopoverOnClose = options.onClose;
    }
    popover.classList.toggle("hidden", !isOpen);
    const activeOwners = Array.isArray(popover.__appPopoverOwners) ? popover.__appPopoverOwners : owners;
    for (const owner of activeOwners) {
      owner.classList.toggle("has-open-popover", Boolean(isOpen));
    }
    if (isOpen) {
      const alignWithinViewport = () => {
        if (!popover || popover.classList.contains("hidden")) {
          return;
        }
        popover.style.top = "";
        popover.style.bottom = "";
        popover.style.left = "";
        popover.style.right = "";
        popover.style.maxHeight = "";
        popover.style.overflowY = "";
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
        const margin = 12;
        const rect = popover.getBoundingClientRect();
        const parentRect = popover.offsetParent?.getBoundingClientRect?.() || { top: 0, left: 0, right: viewportWidth };
        if (rect.bottom > viewportHeight - margin && parentRect.top >= rect.height + margin) {
          popover.style.top = "auto";
          popover.style.bottom = "calc(100% + var(--space-2))";
        }
        if (rect.left < margin && parentRect.right - parentRect.left >= rect.width) {
          popover.style.left = "0";
          popover.style.right = "auto";
        } else if (rect.right > viewportWidth - margin) {
          popover.style.right = "0";
          popover.style.left = "auto";
        }
        const adjustedRect = popover.getBoundingClientRect();
        if (adjustedRect.top < margin) {
          popover.style.top = "calc(100% + var(--space-2))";
          popover.style.bottom = "auto";
        }
        if (adjustedRect.height > viewportHeight - margin * 2) {
          popover.style.maxHeight = `${Math.max(160, viewportHeight - margin * 2)}px`;
          popover.style.overflowY = "auto";
        }
      };
      alignWithinViewport();
      requestAnimationFrame(alignWithinViewport);
    }
  }

  function closePopoverOnOutside(event, options = {}) {
    const {
      popover = null,
      scopes = [],
      onClose = null,
    } = options;
    if (!popover || popover.classList.contains("hidden")) {
      return false;
    }
    const allScopes = [popover, ...(Array.isArray(scopes) ? scopes.filter(Boolean) : [])];
    const inside = eventPathIncludes(event, (node) => {
      if (!(node instanceof Node)) {
        return false;
      }
      return allScopes.some((scope) => {
        if (!(scope instanceof Node)) {
          return false;
        }
        return node === scope || scope.contains(node);
      });
    });
    if (inside) {
      return false;
    }
    if (typeof onClose === "function") {
      onClose();
      return true;
    }
    setPopoverOpen(popover, false, { owners: allScopes.filter((scope) => scope !== popover) });
    return true;
  }

  function closeOpenPopoversOnOutside(event) {
    const openPopovers = Array.from(document.querySelectorAll(".app-popover:not(.hidden)"));
    let closedAny = false;
    for (const popover of openPopovers) {
      const owners = Array.isArray(popover.__appPopoverOwners) ? popover.__appPopoverOwners : [];
      const onClose = typeof popover.__appPopoverOnClose === "function" ? popover.__appPopoverOnClose : null;
      const didClose = closePopoverOnOutside(event, {
        popover,
        scopes: owners,
        onClose,
      });
      closedAny = closedAny || didClose;
    }
    return closedAny;
  }

  window.App = window.App || {};
  const api = {
    DEFAULT_CATEGORY_USAGE_KEY,
    readUsageMap,
    sortCategoriesByUsage,
    createChipButton,
    createMetaChipButton,
    createActionChipButton,
    eventPathIncludes,
    setPopoverOpen,
    closePopoverOnOutside,
    closeOpenPopoversOnOutside,
  };

  window.App.registerRuntimeModule?.("picker-utils", api);
})();
