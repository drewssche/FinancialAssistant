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
  const DEFAULT_FRAMING = Object.freeze({ mode: "contain", zoom: 1, offset_x: 0, offset_y: 0 });
  const OWNER_PATHS = Object.freeze({
    brand: "item-brands",
    template: "item-templates",
    source: "item-sources",
    product: "catalog-products",
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
    root.classList.toggle("has-image", active);
    ensureFramingControls(root);
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
            ? picker.framingError || (picker.framingReady ? "Изображение загружено" : "Загрузка настроек изображения…")
            : "JPEG, PNG или WebP · до 8 МБ";
    }
    updateFramingPreview(name);
    hydrate(preview || root);
  }

  function ensureFramingControls(root) {
    if (root.querySelector("[data-image-framing-controls]")) return;
    const name = root.dataset.catalogImagePicker;
    root.querySelector(".catalog-image-picker-actions")?.insertAdjacentHTML("beforeend", `
      <div class="catalog-image-framing-controls hidden" data-image-framing-controls>
        <div class="segmented catalog-image-fit" aria-label="Как вписать изображение">
          <button type="button" class="segmented-btn" data-image-fit="contain">Вписать</button>
          <button type="button" class="segmented-btn" data-image-fit="cover">Заполнить</button>
        </div>
        <label class="catalog-image-zoom" for="${escapeHtml(name)}-zoom">
          <span>Масштаб <output data-image-zoom-value>100%</output></span>
          <input id="${escapeHtml(name)}-zoom" type="range" min="1" max="4" step="0.01" value="1" data-image-zoom />
        </label>
        <div class="catalog-image-framing-help"><small class="muted-small">Сместить — перетащите фото или используйте стрелки на клавиатуре</small>
          <button type="button" class="btn btn-secondary btn-xs" data-image-framing-reset>Сбросить</button></div>
      </div>`);
    const preview = root.querySelector("[data-catalog-image-preview]");
    preview.tabIndex = 0;
    preview.setAttribute("role", "group");
    preview.setAttribute("aria-label", "Кадрирование изображения. Перетащите фото или используйте стрелки для смещения");
    let drag = null;
    preview.addEventListener("pointerdown", (event) => {
      const picker = pickerStates.get(name);
      if (event.button !== 0 || !picker?.framingReady || !picker.width || picker.removed) return;
      event.preventDefault();
      preview.focus({ preventScroll: true });
      preview.setPointerCapture(event.pointerId);
      drag = { picker, pointerId: event.pointerId, x: event.clientX, y: event.clientY, frame: { ...picker.framing }, size: preview.getBoundingClientRect().width };
      preview.classList.add("is-dragging");
    });
    preview.addEventListener("pointermove", (event) => {
      if (!drag || drag.pointerId !== event.pointerId || pickerStates.get(name) !== drag.picker) return;
      setFraming(name, { offset_x: drag.frame.offset_x + (event.clientX - drag.x) * 2 / drag.size, offset_y: drag.frame.offset_y + (event.clientY - drag.y) * 2 / drag.size });
    });
    const endDrag = () => { drag = null; preview.classList.remove("is-dragging"); };
    preview.addEventListener("pointerup", (event) => { if (preview.hasPointerCapture(event.pointerId)) preview.releasePointerCapture(event.pointerId); endDrag(); });
    preview.addEventListener("pointercancel", endDrag);
    preview.addEventListener("lostpointercapture", endDrag);
    preview.addEventListener("keydown", (event) => {
      const picker = pickerStates.get(name);
      const direction = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
      if (!direction || !picker?.framingReady || !picker.width || picker.removed) return;
      event.preventDefault();
      const step = event.shiftKey ? .15 : .05;
      setFraming(name, { offset_x: picker.framing.offset_x + direction[0] * step, offset_y: picker.framing.offset_y + direction[1] * step });
    });
    root.querySelector("[data-image-zoom]").addEventListener("input", (event) => setFraming(name, { zoom: Number(event.target.value) }));
    root.querySelectorAll("[data-image-fit]").forEach((button) => button.addEventListener("click", () => setFraming(name, { mode: button.dataset.imageFit })));
    root.querySelector("[data-image-framing-reset]").addEventListener("click", () => setFraming(name, DEFAULT_FRAMING));
  }

  function setFraming(name, updates) {
    const picker = pickerStates.get(name);
    if (!picker?.framingReady) return;
    picker.framing = { ...picker.framing, ...updates };
    picker.framing.offset_x = Math.max(-1, Math.min(1, picker.framing.offset_x));
    picker.framing.offset_y = Math.max(-1, Math.min(1, picker.framing.offset_y));
    picker.framingDirty = JSON.stringify(picker.framing) !== JSON.stringify(picker.initialFraming);
    updateFramingPreview(name);
  }

  function updateFramingPreview(name) {
    const picker = pickerStates.get(name), root = pickerNode(name);
    if (!picker || !root) return;
    const active = Boolean(picker.file || (picker.imageId && !picker.removed));
    const controls = root.querySelector("[data-image-framing-controls]");
    controls?.classList.toggle("hidden", !active);
    controls?.querySelectorAll("button, input").forEach((node) => { node.disabled = !picker.framingReady || !picker.width; });
    const frame = picker.framing;
    root.querySelectorAll("[data-image-fit]").forEach((button) => {
      button.classList.toggle("active", button.dataset.imageFit === frame.mode);
      button.setAttribute("aria-pressed", String(button.dataset.imageFit === frame.mode));
    });
    const slider = root.querySelector("[data-image-zoom]");
    if (slider) slider.value = String(frame.zoom);
    const output = root.querySelector("[data-image-zoom-value]");
    if (output) output.textContent = `${Math.round(frame.zoom * 100)}%`;
    const image = root.querySelector("[data-catalog-image-preview] img");
    if (image && picker.width && picker.height) {
      const fit = frame.mode === "cover" ? Math.max : Math.min;
      const scale = fit(1 / picker.width, 1 / picker.height) * frame.zoom;
      image.style.cssText = `inset: auto; width: ${picker.width * scale * 100}%; height: ${picker.height * scale * 100}%; left: ${50 + frame.offset_x * 50}%; top: ${50 + frame.offset_y * 50}%; transform: translate(-50%, -50%); max-width: none; padding: 0;`;
    }
    const status = root.querySelector("[data-catalog-image-status]");
    if (status && active && picker.framingReady) {
      status.textContent = picker.framingDirty
        ? "Кадрирование применится после сохранения"
        : picker.file ? `Выбрано: ${picker.file.name}` : "Изображение загружено";
    }
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
      framing: { ...DEFAULT_FRAMING },
      initialFraming: { ...DEFAULT_FRAMING },
      framingDirty: false,
      framingReady: !options.imageId,
      width: 0,
      height: 0,
    });
    const input = pickerNode(name)?.querySelector("input[type='file']");
    if (input) input.value = "";
    renderPicker(name);
    const picker = pickerStates.get(name);
    if (picker.imageId) {
      core.requestJson(`/api/v1/operations/media/${picker.imageId}/framing`, { headers: core.authHeaders() })
        .then((data) => {
          if (pickerStates.get(name) !== picker || picker.file || picker.removed) return;
          picker.framing = { ...DEFAULT_FRAMING, ...data.framing };
          picker.initialFraming = { ...picker.framing };
          picker.width = data.width;
          picker.height = data.height;
          picker.framingReady = true;
          updateFramingPreview(name);
          const status = pickerNode(name)?.querySelector("[data-catalog-image-status]");
          if (status) status.textContent = "Изображение загружено";
        }).catch(() => {
          if (pickerStates.get(name) !== picker || picker.file || picker.removed) return;
          picker.framingError = "Не удалось загрузить кадрирование. Переоткройте карточку.";
          const status = pickerNode(name)?.querySelector("[data-catalog-image-status]");
          if (status) status.textContent = picker.framingError;
        });
    }
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
    picker.framing = { ...DEFAULT_FRAMING };
    picker.initialFraming = { ...DEFAULT_FRAMING };
    picker.framingReady = true;
    picker.framingDirty = false;
    picker.width = 0;
    picker.height = 0;
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
    picker.framingDirty = false;
    renderPicker(name);
  }

  async function commitPicker(name, ownerType, ownerId) {
    const picker = pickerStates.get(name);
    const endpoint = OWNER_PATHS[ownerType];
    const id = Number(ownerId || 0);
    if (!picker || !endpoint || !id || (!picker.file && !picker.removed && !picker.framingDirty)) {
      return null;
    }
    const previousImageId = picker.imageId;
    let updated;
    if (picker.file || picker.framingDirty) {
      const body = new FormData();
      if (picker.file) body.append("file", picker.file, picker.file.name);
      body.append("framing", JSON.stringify(picker.framing));
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
    if (!item || !Object.prototype.hasOwnProperty.call(item, "latest_price_date")) {
      item = await core.requestJson(`/api/v1/operations/item-templates/${id}`, { headers: core.authHeaders() });
    }
    const catalog = window.App.getRuntimeModule?.("item-catalog") || {};
    catalog.applySavedItemCatalogItem?.(item);
    catalog.applySavedReceiptTemplateHint?.(item);
    catalog.openItemTemplateModal?.(item);
    const modal = document.getElementById("itemTemplateModal");
    core.bringModalToFront?.(modal);
  }

  async function openCatalogProductCard(productId) {
    const id = Number(productId || 0);
    if (!(id > 0)) return;
    await window.App.getRuntimeModule?.("catalog-products")?.openEditor?.(id);
    core.bringModalToFront?.(document.getElementById("catalogProductModal"));
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
  document.addEventListener("load", (event) => {
    const preview = event.target.closest?.("[data-catalog-image-preview]");
    const name = preview?.closest("[data-catalog-image-picker]")?.dataset.catalogImagePicker;
    const picker = pickerStates.get(name);
    if (!picker || !event.target.naturalWidth) return;
    picker.width = event.target.naturalWidth;
    picker.height = event.target.naturalHeight;
    updateFramingPreview(name);
  }, true);
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
    openCatalogProductCard,
  });
  hydrate(document);
})();
