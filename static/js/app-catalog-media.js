(() => {
  const { state, core } = window.App;
  const objectUrls = new Map();
  const pendingLoads = new Map();
  const pickerStates = new Map();
  let cacheGeneration = 0;
  let nodeLoadSeq = 0;
  const MAX_OBJECT_URLS = 160;
  const SUPPORTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
  const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
  const OWNER_PATHS = Object.freeze({
    brand: "item-brands",
    template: "item-templates",
    source: "item-sources",
  });

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function normalizedImageId(value) {
    const imageId = Number(value || 0);
    return Number.isInteger(imageId) && imageId > 0 ? imageId : null;
  }

  function renderThumb(imageId, options = {}) {
    const id = normalizedImageId(imageId);
    const kind = ["brand", "source", "item"].includes(options.kind) ? options.kind : "item";
    const variant = options.variant === "detail" ? "detail" : "thumb";
    const size = ["chip", "row", "picker", "receipt", "detail"].includes(options.size) ? options.size : "row";
    const alt = String(options.alt || "").trim();
    const fallback = String(options.fallback || alt.slice(0, 1) || "·").trim().slice(0, 2);
    const extraClass = String(options.className || "").trim();
    return `
      <span class="catalog-media-thumb catalog-media-${kind} catalog-media-${size} ${id ? "has-media" : "is-fallback"} ${escapeHtml(extraClass)}"
        ${id ? `data-catalog-media-id="${id}" data-catalog-media-variant="${variant}"` : ""}
        role="img" aria-label="${escapeHtml(alt || "Изображение")}">
        ${id ? `<img alt="${escapeHtml(alt)}" loading="lazy" decoding="async" draggable="false" />` : ""}
        <span class="catalog-media-fallback" aria-hidden="true">${escapeHtml(fallback)}</span>
      </span>
    `;
  }

  async function fetchMediaBlob(imageId, variant = "thumb", allowRecovery = true) {
    const id = normalizedImageId(imageId);
    if (!id) {
      throw new Error("Некорректный идентификатор изображения");
    }
    const response = await fetch(`/api/v1/operations/media/${id}/${variant === "detail" ? "detail" : "thumb"}`, {
      headers: { Authorization: `Bearer ${state.token}` },
      cache: "force-cache",
    });
    if (response.status === 401 && allowRecovery && state.token) {
      const recovered = await window.App.getRuntimeModule?.("session")?.recoverUnauthorized?.();
      if (recovered) {
        return fetchMediaBlob(id, variant, false);
      }
    }
    if (!response.ok) {
      throw new Error(`Изображение недоступно [${response.status}]`);
    }
    return response.blob();
  }

  function mediaCacheKey(imageId, variant) {
    return `${Number(imageId)}:${variant === "detail" ? "detail" : "thumb"}`;
  }

  async function getMediaObjectUrl(imageId, variant = "thumb") {
    const key = mediaCacheKey(imageId, variant);
    if (objectUrls.has(key)) {
      const cached = objectUrls.get(key);
      objectUrls.delete(key);
      objectUrls.set(key, cached);
      return cached;
    }
    if (pendingLoads.has(key)) {
      return pendingLoads.get(key);
    }
    const generation = cacheGeneration;
    let pending;
    pending = fetchMediaBlob(imageId, variant)
      .then((blob) => {
        if (generation !== cacheGeneration) {
          throw new Error("Загрузка изображения отменена");
        }
        const url = URL.createObjectURL(blob);
        objectUrls.set(key, url);
        while (objectUrls.size > MAX_OBJECT_URLS) {
          const oldestKey = objectUrls.keys().next().value;
          const oldestUrl = objectUrls.get(oldestKey);
          objectUrls.delete(oldestKey);
          if (oldestUrl) URL.revokeObjectURL(oldestUrl);
        }
        return url;
      })
      .finally(() => {
        if (pendingLoads.get(key) === pending) pendingLoads.delete(key);
      });
    pendingLoads.set(key, pending);
    return pending;
  }

  async function loadNode(node) {
    if (!(node instanceof Element)) {
      return;
    }
    const imageId = normalizedImageId(node.dataset.catalogMediaId);
    const variant = node.dataset.catalogMediaVariant === "detail" ? "detail" : "thumb";
    const signature = imageId ? `${imageId}:${variant}` : "";
    if (!imageId || node.dataset.catalogMediaBound === signature) {
      return;
    }
    node.dataset.catalogMediaBound = signature;
    nodeLoadSeq += 1;
    const loadToken = String(nodeLoadSeq);
    node.dataset.catalogMediaLoadToken = loadToken;
    try {
      const url = await getMediaObjectUrl(imageId, variant);
      if (!node.isConnected || node.dataset.catalogMediaBound !== signature || node.dataset.catalogMediaLoadToken !== loadToken) {
        return;
      }
      const image = node.querySelector("img");
      if (image) {
        image.src = url;
        image.addEventListener("load", () => node.classList.add("is-loaded"), { once: true });
        image.addEventListener("error", () => node.classList.add("is-error"), { once: true });
      }
    } catch (_err) {
      if (node.dataset.catalogMediaLoadToken !== loadToken) return;
      node.dataset.catalogMediaBound = "";
      node.classList.add("is-error");
    }
  }

  const lazyObserver = "IntersectionObserver" in window
    ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        lazyObserver.unobserve(entry.target);
        loadNode(entry.target);
      });
    }, { rootMargin: "180px 0px" })
    : null;

  function hydrateNode(node) {
    if (!(node instanceof Element) || !normalizedImageId(node.dataset.catalogMediaId)) {
      return;
    }
    if (node.dataset.catalogMediaVariant === "detail" || !lazyObserver) {
      loadNode(node);
      return;
    }
    lazyObserver.observe(node);
  }

  function hydrate(root = document) {
    if (root instanceof Element && root.matches("[data-catalog-media-id]")) {
      hydrateNode(root);
    }
    root.querySelectorAll?.("[data-catalog-media-id]").forEach(hydrateNode);
  }

  function invalidate(imageId) {
    const id = normalizedImageId(imageId);
    if (!id) {
      return;
    }
    for (const [key, url] of objectUrls.entries()) {
      if (key.startsWith(`${id}:`)) {
        URL.revokeObjectURL(url);
        objectUrls.delete(key);
      }
    }
    document.querySelectorAll(`[data-catalog-media-id="${id}"]`).forEach((node) => {
      node.dataset.catalogMediaBound = "";
      node.classList.remove("is-loaded", "is-error");
      const image = node.querySelector("img");
      if (image) image.removeAttribute("src");
    });
    queueMicrotask(() => hydrate(document));
  }

  function clear() {
    cacheGeneration += 1;
    for (const url of objectUrls.values()) {
      URL.revokeObjectURL(url);
    }
    objectUrls.clear();
    pendingLoads.clear();
    document.querySelectorAll("[data-catalog-media-id]").forEach((node) => {
      lazyObserver?.unobserve(node);
      node.dataset.catalogMediaBound = "";
      delete node.dataset.catalogMediaLoadToken;
      node.classList.remove("is-loaded", "is-error");
      node.querySelector("img")?.removeAttribute("src");
    });
    for (const picker of pickerStates.values()) {
      if (picker.localUrl) URL.revokeObjectURL(picker.localUrl);
    }
    pickerStates.clear();
  }

  function pickerNode(name) {
    return document.querySelector(`[data-catalog-image-picker="${CSS.escape(String(name || ""))}"]`);
  }

  function renderPicker(name) {
    const picker = pickerStates.get(name);
    const root = pickerNode(name);
    if (!picker || !root) {
      return;
    }
    const preview = root.querySelector("[data-catalog-image-preview]");
    const removeButton = root.querySelector("[data-catalog-image-remove]");
    const status = root.querySelector("[data-catalog-image-status]");
    const active = Boolean(picker.file || (!picker.removed && picker.imageId));
    if (preview) {
      if (picker.file && picker.localUrl) {
        preview.innerHTML = `<span class="catalog-media-thumb catalog-media-${picker.kind} catalog-media-detail has-media is-loaded"><img src="${escapeHtml(picker.localUrl)}" alt="${escapeHtml(picker.label)}" /><span class="catalog-media-fallback" aria-hidden="true">${escapeHtml(picker.label.slice(0, 1) || "·")}</span></span>`;
      } else if (!picker.removed && picker.imageId) {
        preview.innerHTML = renderThumb(picker.imageId, { kind: picker.kind, size: "detail", variant: "detail", alt: picker.label });
      } else {
        preview.innerHTML = renderThumb(null, { kind: picker.kind, size: "detail", alt: picker.label, fallback: "+" });
      }
    }
    if (removeButton) {
      removeButton.classList.toggle("hidden", !active);
    }
    if (status) {
      status.textContent = picker.file
        ? `Выбрано: ${picker.file.name}`
        : picker.removed
          ? "Изображение будет удалено после сохранения"
          : picker.imageId
            ? "Изображение загружено"
            : "JPEG, PNG или WebP · до 8 МБ";
    }
    hydrate(preview || root);
  }

  function resetPicker(name, options = {}) {
    const previous = pickerStates.get(name);
    if (previous?.localUrl) {
      URL.revokeObjectURL(previous.localUrl);
    }
    pickerStates.set(name, {
      imageId: normalizedImageId(options.imageId),
      kind: ["brand", "source", "item"].includes(options.kind) ? options.kind : "item",
      label: String(options.label || "Изображение"),
      file: null,
      localUrl: "",
      removed: false,
    });
    const input = pickerNode(name)?.querySelector("input[type='file']");
    if (input) input.value = "";
    renderPicker(name);
  }

  function stagePickerFile(name, file) {
    const picker = pickerStates.get(name);
    if (!picker || !file) {
      return false;
    }
    if (!SUPPORTED_TYPES.has(String(file.type || "").toLowerCase())) {
      core.showToast?.("Поддерживаются только JPEG, PNG и WebP", { type: "error" });
      return false;
    }
    if (Number(file.size || 0) > MAX_UPLOAD_BYTES) {
      core.showToast?.("Файл больше 8 МБ", { type: "error" });
      return false;
    }
    if (picker.localUrl) URL.revokeObjectURL(picker.localUrl);
    picker.file = file;
    picker.localUrl = URL.createObjectURL(file);
    picker.removed = false;
    renderPicker(name);
    return true;
  }

  function removePickerImage(name) {
    const picker = pickerStates.get(name);
    if (!picker) {
      return;
    }
    if (picker.localUrl) URL.revokeObjectURL(picker.localUrl);
    picker.file = null;
    picker.localUrl = "";
    picker.removed = Boolean(picker.imageId);
    renderPicker(name);
  }

  async function commitPicker(name, ownerType, ownerId) {
    const picker = pickerStates.get(name);
    const endpoint = OWNER_PATHS[ownerType];
    const id = Number(ownerId || 0);
    if (!picker || !endpoint || !id || (!picker.file && !picker.removed)) {
      return null;
    }
    const previousImageId = picker.imageId;
    let updated;
    if (picker.file) {
      const body = new FormData();
      body.append("file", picker.file, picker.file.name);
      updated = await core.requestJson(`/api/v1/operations/${endpoint}/${id}/image`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${state.token}` },
        body,
        timeoutMs: 45000,
      });
    } else {
      updated = await core.requestJson(`/api/v1/operations/${endpoint}/${id}/image`, {
        method: "DELETE",
        headers: core.authHeaders(),
      });
    }
    if (previousImageId) invalidate(previousImageId);
    resetPicker(name, {
      imageId: updated?.image_id,
      kind: picker.kind,
      label: picker.label,
    });
    return updated;
  }

  async function openItemTemplateCard(templateId) {
    const id = Number(templateId || 0);
    if (!(id > 0)) {
      return;
    }
    let item = (state.itemCatalogItems || []).find((entry) => Number(entry?.id || 0) === id)
      || (state.itemCatalogAllItems || []).find((entry) => Number(entry?.id || 0) === id)
      || (state.receiptTemplateHints || []).find((entry) => Number(entry?.id || 0) === id);
    if (!item || !Object.prototype.hasOwnProperty.call(item, "recommendation_enabled")) {
      item = await core.requestJson(`/api/v1/operations/item-templates/${id}`, { headers: core.authHeaders() });
    }
    const catalog = window.App.getRuntimeModule?.("item-catalog") || {};
    catalog.applySavedItemCatalogItem?.(item);
    catalog.applySavedReceiptTemplateHint?.(item);
    catalog.openItemTemplateModal?.(item);
    const modal = document.getElementById("itemTemplateModal");
    core.bringModalToFront?.(modal);
  }

  document.addEventListener("change", (event) => {
    const input = event.target.closest?.("[data-catalog-image-input]");
    if (!input) return;
    const root = input.closest("[data-catalog-image-picker]");
    const file = input.files?.[0];
    if (root?.dataset.catalogImagePicker && file) {
      if (!stagePickerFile(root.dataset.catalogImagePicker, file)) input.value = "";
    }
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-catalog-image-remove]");
    const root = button?.closest?.("[data-catalog-image-picker]");
    if (root?.dataset.catalogImagePicker) {
      removePickerImage(root.dataset.catalogImagePicker);
    }
  });

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof Element) hydrate(node);
      });
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.App.registerRuntimeModule?.("catalog-media", {
    renderThumb,
    hydrate,
    invalidate,
    clear,
    resetPicker,
    commitPicker,
    openItemTemplateCard,
  });
  hydrate(document);
})();
