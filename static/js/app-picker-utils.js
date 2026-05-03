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

  function isFloatingActionPopover(popover) {
    return Boolean(
      popover?.classList?.contains("table-kebab-popover")
      || popover?.classList?.contains("mobile-card-actions-popover")
      || popover?.classList?.contains("app-popover-floating")
      || popover?.classList?.contains("period-control-popover"),
    );
  }

  function clearFloatingPopoverStyles(popover) {
    if (!popover) {
      return;
    }
    [
      "position",
      "top",
      "right",
      "bottom",
      "left",
      "maxHeight",
      "overflowY",
      "zIndex",
      "width",
      "minWidth",
      "maxWidth",
    ].forEach((prop) => {
      popover.style[prop] = "";
    });
  }

  function ensureFloatingPopoverMounted(popover) {
    if (!popover || popover.__appPopoverPortalActive) {
      return;
    }
    popover.__appPopoverPortalParent = popover.parentNode || null;
    popover.__appPopoverPortalNextSibling = popover.nextSibling || null;
    document.body.appendChild(popover);
    popover.__appPopoverPortalActive = true;
  }

  function restoreFloatingPopoverMount(popover) {
    if (!popover || !popover.__appPopoverPortalActive) {
      return;
    }
    const parent = popover.__appPopoverPortalParent;
    const nextSibling = popover.__appPopoverPortalNextSibling;
    if (parent instanceof Node) {
      if (nextSibling instanceof Node && nextSibling.parentNode === parent) {
        parent.insertBefore(popover, nextSibling);
      } else {
        parent.appendChild(popover);
      }
    }
    delete popover.__appPopoverPortalParent;
    delete popover.__appPopoverPortalNextSibling;
    delete popover.__appPopoverPortalActive;
  }

  function detachFloatingPopoverObservers(popover) {
    if (!popover) {
      return;
    }
    if (typeof popover.__appPopoverFloatingReposition === "function") {
      window.removeEventListener("resize", popover.__appPopoverFloatingReposition);
      window.removeEventListener("scroll", popover.__appPopoverFloatingReposition, true);
    }
    delete popover.__appPopoverFloatingReposition;
  }

  function positionFloatingActionPopover(popover, owners = []) {
    if (!popover || popover.classList.contains("hidden")) {
      return;
    }
    const anchor = owners.find((node) => node instanceof HTMLElement && node.matches("button,[role=\"button\"]"))
      || owners.find((node) => node instanceof HTMLElement)
      || null;
    if (!anchor || !anchor.isConnected) {
      const activeOwners = Array.isArray(popover.__appPopoverOwners) ? popover.__appPopoverOwners : owners;
      const onClose = typeof popover.__appPopoverOnClose === "function" ? popover.__appPopoverOnClose : null;
      setPopoverOpen(popover, false, { owners: activeOwners });
      if (onClose) {
        onClose();
      }
      return;
    }
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    const margin = 12;
    clearFloatingPopoverStyles(popover);
    popover.style.position = "fixed";
    popover.style.zIndex = "220";
    popover.style.maxHeight = `${Math.max(160, viewportHeight - margin * 2)}px`;
    popover.style.overflowY = "auto";
    const anchorRect = anchor.getBoundingClientRect();
    const isControlPopover = popover.classList.contains("app-popover-floating") || popover.classList.contains("period-control-popover");
    let preferredWidth = Math.min(360, Math.max(320, viewportWidth - margin * 2));
    if (!isControlPopover) {
      popover.style.width = "max-content";
      popover.style.minWidth = "10.5rem";
      popover.style.maxWidth = `calc(100vw - ${margin * 2}px)`;
      const naturalWidth = Math.ceil(popover.getBoundingClientRect().width);
      preferredWidth = Math.min(Math.max(naturalWidth, 168), viewportWidth - margin * 2);
    }
    popover.style.width = `${preferredWidth}px`;
    popover.style.minWidth = `${Math.min(isControlPopover ? 320 : 168, preferredWidth)}px`;
    popover.style.left = `${Math.max(margin, Math.min(anchorRect.right - preferredWidth, viewportWidth - preferredWidth - margin))}px`;
    popover.style.top = `${Math.min(anchorRect.bottom + 8, viewportHeight - margin)}px`;
    const rect = popover.getBoundingClientRect();
    const spaceBelow = viewportHeight - anchorRect.bottom - margin;
    const spaceAbove = anchorRect.top - margin;
    const shouldOpenUp = rect.height > spaceBelow && spaceAbove > spaceBelow;
    if (shouldOpenUp) {
      popover.style.top = "auto";
      popover.style.bottom = `${Math.max(margin, viewportHeight - anchorRect.top + 8)}px`;
    }
    const adjustedRect = popover.getBoundingClientRect();
    if (adjustedRect.right > viewportWidth - margin) {
      popover.style.left = `${Math.max(margin, viewportWidth - adjustedRect.width - margin)}px`;
    }
    if (adjustedRect.left < margin) {
      popover.style.left = `${margin}px`;
    }
    if (adjustedRect.bottom > viewportHeight - margin && !shouldOpenUp) {
      popover.style.top = `${Math.max(margin, viewportHeight - adjustedRect.height - margin)}px`;
    }
    if (adjustedRect.top < margin && shouldOpenUp) {
      popover.style.bottom = "auto";
      popover.style.top = `${margin}px`;
    }
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
    if (!isOpen) {
      detachFloatingPopoverObservers(popover);
      clearFloatingPopoverStyles(popover);
      restoreFloatingPopoverMount(popover);
    }
    popover.classList.toggle("hidden", !isOpen);
    const activeOwners = Array.isArray(popover.__appPopoverOwners) ? popover.__appPopoverOwners : owners;
    for (const owner of activeOwners) {
      owner.classList.toggle("has-open-popover", Boolean(isOpen));
    }
    if (isOpen && isFloatingActionPopover(popover)) {
      ensureFloatingPopoverMounted(popover);
      popover.classList.remove("hidden");
      const reposition = () => positionFloatingActionPopover(popover, activeOwners);
      popover.__appPopoverFloatingReposition = reposition;
      reposition();
      requestAnimationFrame(reposition);
      window.addEventListener("resize", reposition);
      window.addEventListener("scroll", reposition, true);
    } else if (isOpen) {
      requestAnimationFrame(() => {});
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
    setPopoverOpen(popover, false, { owners: allScopes.filter((scope) => scope !== popover) });
    if (typeof onClose === "function") {
      onClose();
    }
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
