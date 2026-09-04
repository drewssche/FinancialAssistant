(() => {
  function createOperationModalReceiptFeature(deps) {
    const {
      state,
      el,
      core,
      updateCreatePreview,
      updateEditPreview,
      syncCreateFxSettlementFieldUi,
      syncEditFxSettlementFieldUi,
    } = deps;

    const RECEIPT_TEMPLATES_CACHE_TTL_MS = 20000;
    const receiptUiState = {
      activePicker: null,
      localTemplateSeq: 0,
      hintsPromise: null,
      hintsLoadedAt: 0,
      brandsPromise: null,
      brandsLoadedAt: 0,
    };
    const RECEIPT_DISCOUNT_TYPES = [
      { value: "promo", label: "Акция" },
      { value: "coupon", label: "Купон" },
      { value: "loyalty_points", label: "Баллы" },
    ];

    function normalizeReceiptName(value) {
      return String(value || "")
        .replace(/\s+/g, " ")
        .trim();
    }

    function asMoney(value) {
      const resolved = core.resolveMoneyInput?.(value || 0);
      const num = resolved ? Number(resolved.previewValue || 0) : Number(value || 0);
      if (!Number.isFinite(num)) {
        return 0;
      }
      return Math.round(num * 100) / 100;
    }

    function asQty(value) {
      const num = Number(value || 0);
      if (!Number.isFinite(num)) {
        return 0;
      }
      return Math.round(num * 1000) / 1000;
    }

    function receiptLineTotal(item) {
      return asMoney(asQty(item.quantity) * asMoney(item.unit_price));
    }

    function receiptDiscountToggleLabel(item) {
      if (!item?.is_discounted) {
        return "Скидка";
      }
      const purchasePrice = asMoney(item.unit_price || 0);
      const regularPrice = asMoney(item.regular_unit_price || 0);
      if (!(regularPrice > purchasePrice && purchasePrice > 0)) {
        return "Скидка —%";
      }
      const percent = ((regularPrice - purchasePrice) / regularPrice) * 100;
      return `Скидка −${Number(percent.toFixed(1))}%`;
    }

    function getReceiptLatestTemplatePrice(item) {
      const templateId = Number(item?.template_id || 0);
      if (!templateId) {
        return 0;
      }
      const template = (state.receiptTemplateHints || []).find((entry) => Number(entry.id) === templateId);
      return asMoney(template?.latest_unit_price || 0);
    }

    function getReceiptCurrency(mode = "create") {
      const selected = mode === "edit" ? el.editCurrency?.value : el.opCurrency?.value;
      return String(selected || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    }

    function getReceiptCurrencyLabel(mode = "create") {
      return core.formatCurrencyLabel?.(getReceiptCurrency(mode)) || getReceiptCurrency(mode);
    }

    function formatReceiptMoney(value, mode = "create", options = {}) {
      return core.formatMoney(value, {
        currency: getReceiptCurrency(mode),
        ...options,
      });
    }

    function formatReceiptInputAmount(value) {
      const amount = asMoney(value || 0);
      return amount > 0 ? core.formatAmount(amount) : "";
    }

    function getReceiptBaseCurrency(mode = "create") {
      const operationModal = window.App.getRuntimeModule?.("operation-modal");
      const context = operationModal?.getOperationCurrencyContext?.(mode);
      return String(context?.baseCurrency || (core.getCurrencyConfig?.().code || "BYN")).toUpperCase();
    }

    function getReceiptFxRate(mode = "create") {
      const operationModal = window.App.getRuntimeModule?.("operation-modal");
      const context = operationModal?.getOperationCurrencyContext?.(mode);
      const rate = Number(context?.fxRate || 1);
      return Number.isFinite(rate) && rate > 0 ? rate : 1;
    }

    function getReceiptContext(mode = "create") {
      const isEdit = mode === "edit";
      return {
        mode,
        itemsKey: isEdit ? "editReceiptItems" : "createReceiptItems",
        seqKey: isEdit ? "editReceiptSeq" : "createReceiptSeq",
        fieldsNode: isEdit ? el.editReceiptFields : el.opReceiptFields,
        listNode: isEdit ? el.editReceiptItemsList : el.receiptItemsList,
        totalNode: isEdit ? el.editReceiptTotalValue : el.receiptTotalValue,
        totalLabelNode: isEdit ? el.editReceiptTotalLabel : el.receiptTotalLabel,
        diffNode: isEdit ? el.editReceiptDiffValue : el.receiptDiffValue,
        diffLabelNode: isEdit ? el.editReceiptDiffLabel : el.receiptDiffLabel,
        amountNode: document.getElementById(isEdit ? "editAmount" : "opAmount"),
      };
    }

    function getReceiptModeFromNode(node) {
      const mode = node?.closest?.("[data-receipt-mode]")?.dataset?.receiptMode || "create";
      return mode === "edit" ? "edit" : "create";
    }

    function getReceiptItems(mode = "create") {
      const ctx = getReceiptContext(mode);
      if (!Array.isArray(state[ctx.itemsKey])) {
        state[ctx.itemsKey] = [];
      }
        return state[ctx.itemsKey];
      }

    function getReceiptOperationKind(mode = "create") {
      return mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense");
    }

    function getReceiptDefaultCategoryId(mode = "create") {
      return mode === "edit"
        ? (el.editCategory?.value ? Number(el.editCategory.value) : null)
        : (el.opCategory?.value ? Number(el.opCategory.value) : null);
    }

    function isReceiptModeEnabled(mode = "create") {
      return mode === "edit"
        ? el.editOperationMode?.value === "receipt"
        : el.opOperationMode?.value === "receipt";
    }

    function createReceiptDraft(seed = {}, mode = "create") {
      const ctx = getReceiptContext(mode);
      const hasQuantity = seed.quantity !== undefined && seed.quantity !== null && String(seed.quantity).trim() !== "";
      const hasUnitPrice = seed.unit_price !== undefined && seed.unit_price !== null && String(seed.unit_price).trim() !== "";
      state[ctx.seqKey] = Number(state[ctx.seqKey] || 0) + 1;
      return {
        draft_id: state[ctx.seqKey],
        template_id: seed.template_id || null,
        item_image_id: seed.item_image_id || seed.image_id || null,
        source_id: seed.source_id || null,
        source_image_id: seed.source_image_id || null,
        brand_id: seed.brand_id ? Number(seed.brand_id) : null,
        brand_name: normalizeReceiptName(seed.brand_name || ""),
        brand_accent_color: seed.brand_accent_color || null,
        brand_image_id: seed.brand_image_id || null,
        brand_is_archived: Boolean(seed.brand_is_archived),
        brand_touched: Boolean(seed.brand_touched),
        category_id: seed.category_id ? Number(seed.category_id) : null,
        shop_name: normalizeReceiptName(seed.shop_name || ""),
        shop_name_inherited: Boolean(seed.shop_name_inherited),
        name: normalizeReceiptName(seed.name || ""),
        quantity: hasQuantity ? asQty(seed.quantity) : 0,
        unit_price: hasUnitPrice ? asMoney(seed.unit_price) : 0,
        is_discounted: Boolean(seed.is_discounted),
        regular_unit_price: seed.regular_unit_price ? asMoney(seed.regular_unit_price) : 0,
        discount_type: seed.discount_type || (seed.is_discounted ? "promo" : null),
        note: seed.note || "",
      };
    }

    function getReceiptItemByDraftId(draftId, mode = "create") {
      return getReceiptItems(mode).find((entry) => Number(entry.draft_id) === Number(draftId)) || null;
    }

    function unlinkReceiptTemplateIdentity(item) {
      item.template_id = null;
      item.item_image_id = null;
      if (item.brand_is_archived) {
        item.brand_id = null;
        item.brand_name = "";
        item.brand_accent_color = null;
        item.brand_image_id = null;
        item.brand_is_archived = false;
        item.brand_touched = true;
        return true;
      }
      if (item.brand_id) {
        // The visible active brand follows a newly named/sourced catalog item.
        // Send it explicitly because there is no longer a template link from
        // which the backend can infer that relation.
        item.brand_touched = true;
      }
      return false;
    }

    function applySavedTemplateToReceiptDrafts(template) {
      const templateId = Number(template?.id || 0);
      if (!templateId) {
        return false;
      }
      let changedAny = false;
      for (const mode of ["create", "edit"]) {
        const rows = getReceiptItems(mode);
        const linkedRows = rows.filter((item) => Number(item?.template_id || 0) === templateId);
        if (!linkedRows.length) {
          continue;
        }
        const ctx = getReceiptContext(mode);
        const scrollNodes = [ctx.listNode, ctx.fieldsNode?.closest?.(".modal-card")].filter(Boolean);
        const scrollPositions = scrollNodes.map((node) => [node, node.scrollTop]);
        for (const item of linkedRows) {
          item.name = normalizeReceiptName(template?.name || item.name || "");
          item.item_image_id = template?.image_id || null;
          item.shop_name = normalizeReceiptName(template?.source_name || template?.shop_name || "");
          item.source_id = template?.source_id || null;
          item.source_image_id = template?.source_image_id || null;
          item.category_id = template?.last_category_id ? Number(template.last_category_id) : null;
          item.brand_id = template?.brand_id ? Number(template.brand_id) : null;
          item.brand_name = normalizeReceiptName(template?.brand_name || "");
          item.brand_accent_color = template?.brand_accent_color || null;
          item.brand_image_id = template?.brand_image_id || null;
          item.brand_is_archived = Boolean(template?.brand_is_archived);
          item.brand_touched = false;
        }
        renderReceiptItems(mode);
        scrollPositions.forEach(([node, scrollTop]) => {
          node.scrollTop = scrollTop;
        });
        if (mode === "create") {
          updateCreatePreview();
        } else {
          updateEditPreview();
        }
        changedAny = true;
      }
      return changedAny;
    }

    function syncReceiptBrandField(item, mode = "create") {
      const row = getReceiptContext(mode).listNode?.querySelector(
        `[data-receipt-item-id="${Number(item?.draft_id || 0)}"]`,
      );
      const input = row?.querySelector('[data-receipt-field="brand_search"]');
      const brand = getReceiptBrandPresentation(item);
      const brandName = brand.name;
      if (input) {
        input.value = brandName;
        input.title = brandName || "Бренд не выбран";
      }
      const cell = row?.querySelector(".receipt-brand-cell");
      if (cell) {
        cell.classList.toggle("has-brand", Boolean(brandName));
        cell.style.setProperty("--receipt-brand-accent", brand.accent);
        let thumb = cell.querySelector(".receipt-brand-thumb");
        if (!brandName) {
          thumb?.remove();
          return;
        }
        if (!thumb) {
          thumb = document.createElement("span");
          thumb.className = "receipt-brand-thumb";
          input?.before(thumb);
        }
        thumb.title = `Логотип ${brandName}`;
        thumb.innerHTML = renderReceiptBrandThumb(brand);
        window.App.getRuntimeModule?.("catalog-media")?.hydrate?.(thumb);
      }
    }

    function updateReceiptItemField(draftId, key, value, mode = "create") {
      const items = getReceiptItems(mode);
      const item = items.find((entry) => Number(entry.draft_id) === Number(draftId));
      if (!item) {
        return null;
      }
      const hadName = hasReceiptRowName(item);
      if (key === "quantity") {
        item.quantity = asQty(value);
      } else if (key === "unit_price") {
        item.unit_price = asMoney(value);
      } else if (key === "regular_unit_price") {
        item.regular_unit_price = asMoney(value);
      } else if (key === "is_discounted") {
        item.is_discounted = Boolean(value);
        item.discount_type = item.is_discounted ? (item.discount_type || "promo") : null;
        if (item.is_discounted && !item.regular_unit_price) {
          const latestPrice = getReceiptLatestTemplatePrice(item);
          if (latestPrice > 0) {
            item.regular_unit_price = latestPrice;
          }
        }
        if (!item.is_discounted) {
          item.regular_unit_price = 0;
        }
      } else if (key === "discount_type") {
        item.discount_type = RECEIPT_DISCOUNT_TYPES.some((entry) => entry.value === value)
          ? value
          : "promo";
      } else if (key === "shop_name") {
        const nextShopName = normalizeReceiptName(value);
        const identityChanged = normalizeReceiptName(item.shop_name || "").toLowerCase() !== nextShopName.toLowerCase();
        item.shop_name = nextShopName;
        const source = (state.itemSources || []).find((entry) => normalizeReceiptName(entry?.name || "").toLowerCase() === nextShopName.toLowerCase())
          || (state.receiptTemplateHints || []).find((entry) => normalizeReceiptName(entry?.source_name || entry?.shop_name || "").toLowerCase() === nextShopName.toLowerCase());
        item.source_id = source?.source_id || source?.id || null;
        item.source_image_id = source?.source_image_id || source?.image_id || null;
        item.shop_name_inherited = false;
        if (identityChanged) {
          if (unlinkReceiptTemplateIdentity(item)) {
            syncReceiptBrandField(item, mode);
          }
        }
      } else if (key === "name") {
        const nextName = normalizeReceiptName(value);
        const identityChanged = normalizeReceiptName(item.name || "").toLowerCase() !== nextName.toLowerCase();
        item.name = nextName;
        if (identityChanged) {
          item.item_image_id = null;
          if (unlinkReceiptTemplateIdentity(item)) {
            syncReceiptBrandField(item, mode);
          }
        }
      } else if (key === "brand_id") {
        const brandId = value ? Number(value) : null;
        const brand = brandId
          ? (state.itemBrands || []).find((entry) => Number(entry.id) === brandId)
          : null;
        item.brand_id = brand?.id ? Number(brand.id) : null;
        item.brand_name = normalizeReceiptName(brand?.name || "");
        item.brand_accent_color = brand?.accent_color || null;
        item.brand_image_id = brand?.image_id || null;
        item.brand_is_archived = Boolean(brand?.is_archived);
        item.brand_touched = true;
      } else if (key === "brand_search") {
        // The text box is only a search query. Keep the persisted selection
        // until the user explicitly picks a brand or chooses “Без бренда”.
      } else if (key === "category_id") {
        item.category_id = value ? Number(value) : null;
      } else if (key === "note") {
        item.note = value || "";
      }
      return {
        item,
        hadName,
        hasName: hasReceiptRowName(item),
      };
    }

    function isReceiptRowEmpty(item) {
      const shopName = item?.shop_name_inherited ? "" : normalizeReceiptName(item?.shop_name || "");
      const brandId = Number(item?.brand_id || 0);
      const brandName = normalizeReceiptName(item?.brand_name || "");
      const name = normalizeReceiptName(item?.name || "");
      const qty = asQty(item?.quantity || 0);
      const price = asMoney(item?.unit_price || 0);
      return !shopName && !brandId && !brandName && !name && qty <= 0 && price <= 0;
    }

    function hasReceiptRowName(item) {
      return normalizeReceiptName(item?.name || "") !== "";
    }

    function hasReceiptRowContent(item) {
      return !isReceiptRowEmpty(item);
    }

    function createTrailingReceiptDraft(mode = "create") {
      const primaryShopName = normalizeReceiptName(getReceiptItems(mode)[0]?.shop_name || "");
      return createReceiptDraft({
        shop_name: primaryShopName,
        source_id: getReceiptItems(mode)[0]?.source_id || null,
        source_image_id: getReceiptItems(mode)[0]?.source_image_id || null,
        shop_name_inherited: Boolean(primaryShopName),
      }, mode);
    }

    function inheritReceiptShopFromFirstRow(changedDraftId, mode = "create") {
      const rows = getReceiptItems(mode);
      const firstRow = rows[0];
      if (!firstRow || Number(firstRow.draft_id) !== Number(changedDraftId)) {
        return false;
      }
      const primaryShopName = normalizeReceiptName(firstRow.shop_name || "");
      let changed = false;
      for (const item of rows.slice(1)) {
        if (!normalizeReceiptName(item.shop_name || "") || item.shop_name_inherited) {
          if (normalizeReceiptName(item.shop_name || "") !== primaryShopName) {
            item.shop_name = primaryShopName;
            item.source_id = firstRow.source_id || null;
            item.source_image_id = firstRow.source_image_id || null;
            if (unlinkReceiptTemplateIdentity(item)) {
              syncReceiptBrandField(item, mode);
            }
            changed = true;
          }
          item.shop_name_inherited = true;
          const input = getReceiptContext(mode).listNode?.querySelector(
            `[data-receipt-item-id="${Number(item.draft_id)}"] [data-receipt-field="shop_name"]`,
          );
          if (input && input.value !== primaryShopName) {
            input.value = primaryShopName;
          }
        }
      }
      return changed;
    }

    function ensureTrailingReceiptRow(mode = "create") {
      const ctx = getReceiptContext(mode);
      const rows = getReceiptItems(mode);
      if (!rows.length) {
        state[ctx.itemsKey] = [createReceiptDraft({}, mode)];
        return;
      }
      const normalizedRows = rows.filter((item) => hasReceiptRowContent(item));
      if (!normalizedRows.length) {
        state[ctx.itemsKey] = [createReceiptDraft({}, mode)];
        return;
      }
      const last = normalizedRows[normalizedRows.length - 1];
      if (hasReceiptRowName(last)) {
        state[ctx.itemsKey] = [...normalizedRows, createTrailingReceiptDraft(mode)];
        return;
      }
      state[ctx.itemsKey] = normalizedRows;
    }

    function resizeReceiptNameTextarea(node) {
      if (!node) {
        return;
      }
      node.style.height = "auto";
      const computed = window.getComputedStyle(node);
      const lineHeight = Number.parseFloat(computed.lineHeight) || 20;
      const padding = (Number.parseFloat(computed.paddingTop) || 0) + (Number.parseFloat(computed.paddingBottom) || 0);
      const border = (Number.parseFloat(computed.borderTopWidth) || 0) + (Number.parseFloat(computed.borderBottomWidth) || 0);
      const maxHeight = (lineHeight * 3) + padding + border;
      node.style.height = `${Math.min(node.scrollHeight, maxHeight)}px`;
      node.classList.toggle("is-overflowing", node.scrollHeight > maxHeight + 1);
    }

    function safeBrandAccent(value) {
      const accent = String(value || "").trim();
      return /^#[0-9a-f]{3,8}$/i.test(accent) ? accent : "#7aa2f7";
    }

    function getReceiptBrandPresentation(item) {
      const brandMeta = item?.brand_id
        ? (state.itemBrands || []).find((entry) => Number(entry.id) === Number(item.brand_id))
        : null;
      const name = normalizeReceiptName(brandMeta?.name || item?.brand_name || "");
      const imageId = brandMeta
        ? (brandMeta.image_id ?? brandMeta.brand_image_id ?? null)
        : (item?.brand_image_id ?? null);
      return {
        meta: brandMeta,
        name,
        accent: safeBrandAccent(brandMeta?.accent_color || item?.brand_accent_color),
        imageId,
      };
    }

    function renderReceiptBrandThumb(brand) {
      if (!brand?.name) {
        return "";
      }
      return window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(brand.imageId, {
        kind: "brand",
        size: "chip",
        className: "receipt-brand-media",
        alt: `Логотип ${brand.name}`,
        fallback: brand.name.slice(0, 1),
      }) || "";
    }

    function renderReceiptItems(mode = "create") {
      const ctx = getReceiptContext(mode);
      if (!ctx.listNode) {
        return;
      }
      const rows = getReceiptItems(mode);
      const esc = (value) => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
      ctx.listNode.innerHTML = rows.map((item, idx) => {
        const total = receiptLineTotal(item);
        const isLast = idx === rows.length - 1;
        const removeHidden = isLast && isReceiptRowEmpty(item);
        const pickerMode = receiptUiState.activePicker?.mode || "create";
        const activeDraftId = Number(receiptUiState.activePicker?.draft_id || 0);
        const activeField = receiptUiState.activePicker?.field || "";
        const shopPickerOpen = activeDraftId === Number(item.draft_id) && activeField === "shop_name" && pickerMode === mode;
        const namePickerOpen = activeDraftId === Number(item.draft_id) && activeField === "name" && pickerMode === mode;
        const brandPickerOpen = activeDraftId === Number(item.draft_id) && activeField === "brand_id" && pickerMode === mode;
        const categoryPickerOpen = activeDraftId === Number(item.draft_id) && activeField === "category_id" && pickerMode === mode;
        const hasOpenPicker = shopPickerOpen || brandPickerOpen || namePickerOpen || categoryPickerOpen;
        const explicitCategoryId = item.category_id ? Number(item.category_id) : null;
        const effectiveCategoryId = explicitCategoryId || getReceiptDefaultCategoryId(mode);
        const categoryMeta = effectiveCategoryId
          ? (state.categories || []).find((entry) => Number(entry.id) === effectiveCategoryId)
          : null;
        const categorySource = explicitCategoryId ? "explicit" : (categoryMeta ? "default" : "none");
        const brand = getReceiptBrandPresentation(item);
        const brandName = brand.name;
        const brandAccent = brand.accent;
        const brandThumb = renderReceiptBrandThumb(brand);
        const activeDiscountType = item.discount_type || "promo";
        const media = window.App.getRuntimeModule?.("catalog-media") || {};
        const linkedItemThumb = item.template_id ? media.renderThumb?.(item.item_image_id, {
          kind: "item",
          size: "picker",
          alt: item.name || "Позиция",
          fallback: String(item.name || "П").slice(0, 1),
        }) || "" : "";
        const discountTypeButtons = RECEIPT_DISCOUNT_TYPES.map((entry) => `
          <button
            class="receipt-discount-type-chip ${activeDiscountType === entry.value ? "is-active" : ""}"
            type="button"
            data-receipt-discount-type="${entry.value}"
            data-receipt-item-id="${item.draft_id}"
            aria-pressed="${activeDiscountType === entry.value ? "true" : "false"}"
          >${esc(entry.label)}</button>
        `).join("");
        return `
          <div class="receipt-item-row ${item.is_discounted ? "receipt-item-row-discounted" : ""} ${hasOpenPicker ? "has-open-popover" : ""}" data-receipt-mode="${mode}" data-receipt-item-id="${item.draft_id}">
            <div class="receipt-item-identity">
              <div class="receipt-shop-cell ${shopPickerOpen ? "has-open-popover" : ""}">
                <input type="text" data-receipt-field="shop_name" value="${esc(item.shop_name || "")}" placeholder="Источник" title="${esc(item.shop_name || "Источник")}" autocomplete="off" aria-label="Источник позиции" />
                <div class="receipt-shop-picker app-popover ${shopPickerOpen ? "" : "hidden"}"></div>
              </div>
              <div class="receipt-brand-cell ${brandPickerOpen ? "has-open-popover" : ""} ${brandName ? "has-brand" : ""}" style="--receipt-brand-accent: ${brandAccent}">
                ${brandName ? `<span class="receipt-brand-thumb" title="${esc(`Логотип ${brandName}`)}">${brandThumb}</span>` : ""}
                <input type="text" data-receipt-field="brand_search" value="${esc(brandName)}" placeholder="Бренд" title="${esc(brandName || "Бренд не выбран")}" autocomplete="off" aria-label="Бренд позиции" />
                <div class="receipt-brand-picker app-popover ${brandPickerOpen ? "" : "hidden"}"></div>
              </div>
              <div class="receipt-name-cell ${namePickerOpen ? "has-open-popover" : ""}">
                <div class="receipt-name-field-wrap">
                  ${item.template_id ? `<button class="receipt-linked-thumb" type="button" data-open-receipt-template-card="${Number(item.template_id)}" title="Открыть карточку позиции" aria-label="Открыть карточку ${esc(item.name || "позиции")}">${linkedItemThumb}</button>` : ""}
                  <textarea class="receipt-name-input" rows="1" data-receipt-field="name" placeholder="Позиция" title="${esc(item.name || "Позиция")}" aria-label="Название позиции">${esc(item.name)}</textarea>
                  ${item.template_id ? `<button class="receipt-template-card-btn" type="button" data-open-receipt-template-card="${Number(item.template_id)}" title="Открыть карточку позиции" aria-label="Открыть карточку позиции">↗</button>` : ""}
                </div>
                <span class="receipt-new-badge ${item.name && !item.template_id ? "" : "hidden"}">Новая позиция</span>
                <div class="receipt-name-picker app-popover ${namePickerOpen ? "" : "hidden"}"></div>
              </div>
              <div class="receipt-category-cell ${categoryPickerOpen ? "has-open-popover" : ""}">
                <span class="receipt-category-badge ${categorySource === "default" ? "" : "hidden"}">По умолчанию</span>
                <input
                  type="text"
                  data-receipt-field="category_search"
                  value="${esc(categoryMeta?.name || "")}"
                  data-receipt-category-source="${categorySource}"
                  data-receipt-effective-category-id="${effectiveCategoryId || ""}"
                  placeholder="Категория"
                  title="${esc(categoryMeta?.name || "Категория не выбрана")}"
                  autocomplete="off"
                  aria-label="Категория позиции"
                />
                <div class="receipt-category-picker app-popover ${categoryPickerOpen ? "" : "hidden"}"></div>
              </div>
            </div>
            <div class="receipt-item-money">
              <div class="receipt-price-cell ${item.is_discounted ? "receipt-price-cell-discounted" : ""}">
                <div class="receipt-price-field">
                  <input type="text" inputmode="decimal" data-receipt-field="unit_price" value="${formatReceiptInputAmount(item.unit_price)}" placeholder="Цена" title="Цена покупки в ${esc(getReceiptCurrencyLabel(mode))}" aria-label="Цена позиции" />
                </div>
                <button class="receipt-discount-toggle ${item.is_discounted ? "is-active" : ""}" type="button" data-receipt-discount-toggle="${item.draft_id}" aria-pressed="${item.is_discounted ? "true" : "false"}" title="Скидка, купон, промокод или бонусы">${receiptDiscountToggleLabel(item)}</button>
                <div class="receipt-discount-type-row ${item.is_discounted ? "" : "hidden"}" role="group" aria-label="Тип скидки">${discountTypeButtons}</div>
                <div class="receipt-price-field receipt-regular-price-field ${item.is_discounted ? "" : "hidden"}">
                  <input class="receipt-regular-price" type="text" inputmode="decimal" data-receipt-field="regular_unit_price" value="${formatReceiptInputAmount(item.regular_unit_price)}" placeholder="До скидки" title="Обычная цена для истории" aria-label="Цена до скидки" />
                </div>
              </div>
              <div class="receipt-quantity-cell">
                <span>Количество</span>
                <input type="number" step="0.001" min="0" data-receipt-field="quantity" value="${item.quantity || ""}" placeholder="Кол-во" aria-label="Количество позиции" />
              </div>
              <div class="receipt-line-total"><span>Итого</span><strong>${formatReceiptMoney(total, mode)}</strong></div>
              <button class="btn btn-danger receipt-remove-btn ${removeHidden ? "hidden" : ""}" type="button" data-receipt-remove-id="${item.draft_id}" title="Удалить позицию" aria-label="Удалить позицию">×</button>
            </div>
          </div>
        `;
      }).join("");
      ctx.listNode.querySelectorAll('textarea[data-receipt-field="name"]').forEach(resizeReceiptNameTextarea);
    }

    function getReceiptTotal(mode = "create") {
      return getReceiptItems(mode).reduce((acc, item) => acc + receiptLineTotal(item), 0);
    }

    function syncReceiptNumericInputs(mode = "create") {
      const ctx = getReceiptContext(mode);
      ctx.listNode?.querySelectorAll("[data-receipt-item-id]").forEach((row) => {
        const draftId = Number(row.dataset.receiptItemId || 0);
        for (const field of ["quantity", "unit_price", "regular_unit_price"]) {
          const input = row.querySelector(`[data-receipt-field="${field}"]`);
          if (input) {
            updateReceiptItemField(draftId, field, input.value, mode);
          }
        }
      });
    }

    function renderReceiptSummary(mode = "create", options = {}) {
      const resolvedMode = mode === "edit" ? "edit" : "create";
      const ctx = getReceiptContext(resolvedMode);
      if (!ctx.totalNode || !ctx.diffNode) {
        return;
      }
      const total = getReceiptTotal(resolvedMode);
      const receiptCurrency = getReceiptCurrency(resolvedMode);
      const baseCurrency = getReceiptBaseCurrency(resolvedMode);
      const fxRate = getReceiptFxRate(resolvedMode);
      const totalHtml = receiptCurrency === baseCurrency
        ? formatReceiptMoney(total, resolvedMode)
        : `${formatReceiptMoney(total, resolvedMode)} <span class="muted-small">· ≈ ${core.formatMoney(total * fxRate, { currency: baseCurrency })}</span>`;
      if (ctx.totalLabelNode) {
        ctx.totalLabelNode.textContent = `Сумма чека (${getReceiptCurrencyLabel(resolvedMode)})`;
      }
      if (ctx.totalNode) {
        ctx.totalNode.innerHTML = totalHtml;
      }
      const resolvedAmount = core.resolveMoneyInput(ctx.amountNode?.value || 0);
      const hasAmountOverride = Number.isFinite(Number(options?.amountValue));
      const comparedAmount = hasAmountOverride ? Number(options.amountValue) : Number(resolvedAmount.previewValue || 0);
      const diff = hasAmountOverride || !resolvedAmount.empty ? asMoney(comparedAmount - total) : 0;
      const diffHtml = receiptCurrency === baseCurrency
        ? formatReceiptMoney(diff, resolvedMode)
        : `${formatReceiptMoney(diff, resolvedMode)} <span class="muted-small">· ≈ ${core.formatMoney(diff * fxRate, { currency: baseCurrency })}</span>`;
      if (ctx.diffLabelNode) {
        ctx.diffLabelNode.textContent = `Расхождение (${getReceiptCurrencyLabel(resolvedMode)})`;
      }
      if (ctx.diffNode) {
        ctx.diffNode.innerHTML = diffHtml;
        ctx.diffNode.classList.toggle("receipt-diff-warn", !resolvedAmount.empty && Math.abs(diff) >= 0.01);
      }
    }

    function removeReceiptItem(draftId, mode = "create") {
      const ctx = getReceiptContext(mode);
      state[ctx.itemsKey] = getReceiptItems(mode).filter((entry) => Number(entry.draft_id) !== Number(draftId));
      if (Number(receiptUiState.activePicker?.draft_id || 0) === Number(draftId) && (receiptUiState.activePicker?.mode || "create") === mode) {
        receiptUiState.activePicker = null;
      }
      ensureTrailingReceiptRow(mode);
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        syncCreateFxSettlementFieldUi?.();
      } else {
        syncEditFxSettlementFieldUi?.();
      }
      if (mode === "create") {
        updateCreatePreview();
      } else {
        updateEditPreview();
      }
    }

    function handlePullReceiptTotal(modeOrEvent = "create") {
      const mode = typeof modeOrEvent === "string"
        ? modeOrEvent
        : (modeOrEvent?.target?.dataset?.receiptMode || "create");
      const ctx = getReceiptContext(mode);
      syncReceiptNumericInputs(mode);
      const total = getReceiptTotal(mode);
      if (!ctx.amountNode) {
        return;
      }
      ctx.amountNode.value = core.formatAmount(total);
      renderReceiptSummary(mode, { amountValue: total });
      if (mode === "create") {
        syncCreateFxSettlementFieldUi?.();
      } else {
        syncEditFxSettlementFieldUi?.();
      }
      if (mode === "create") {
        updateCreatePreview();
      } else {
        updateEditPreview();
      }
    }

    const createOperationModalReceiptInteractionsFeature = window.App.getRuntimeModule?.("operation-modal-receipt-interactions-factory");
    const interactions = createOperationModalReceiptInteractionsFeature
      ? createOperationModalReceiptInteractionsFeature({
        state,
        el,
        core,
        receiptUiState,
        normalizeReceiptName,
        getReceiptModeFromNode,
        getReceiptItemByDraftId,
        getReceiptContext,
        updateReceiptItemField,
        inheritReceiptShopFromFirstRow,
        ensureTrailingReceiptRow,
        renderReceiptItems,
        renderReceiptSummary,
        receiptLineTotal,
        receiptDiscountToggleLabel,
        formatReceiptMoney,
        resizeReceiptNameTextarea,
        removeReceiptItem,
        updateCreatePreview,
        updateEditPreview,
        RECEIPT_TEMPLATES_CACHE_TTL_MS,
      })
      : {};

    const loadReceiptTemplateHints = interactions.loadReceiptTemplateHints || (async () => {});
    const hideAllReceiptPickers = interactions.hideAllReceiptPickers || (() => {
      receiptUiState.activePicker = null;
    });
    const handleReceiptItemsListInput = interactions.handleReceiptItemsListInput || (() => {});
    const handleReceiptItemsListFocusOut = interactions.handleReceiptItemsListFocusOut || (() => {});
    const handleReceiptItemsListFocusIn = interactions.handleReceiptItemsListFocusIn || (() => {});
    const handleReceiptItemsListKeydown = interactions.handleReceiptItemsListKeydown || (() => {});
    const handleReceiptItemsListClick = interactions.handleReceiptItemsListClick || (() => {});
    const handleReceiptOutsidePointer = interactions.handleReceiptOutsidePointer || (() => {});

    function setReceiptEnabled(enabled, mode = "create") {
      const ctx = getReceiptContext(mode);
      const isEnabled = enabled === true;
      if (ctx.fieldsNode) {
        ctx.fieldsNode.classList.toggle("hidden", !isEnabled);
      }
      if (ctx.amountNode) {
        ctx.amountNode.required = !isEnabled;
      }
      if (isEnabled) {
        ensureTrailingReceiptRow(mode);
        loadReceiptTemplateHints().catch(() => {});
      } else {
        hideAllReceiptPickers();
      }
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        syncCreateFxSettlementFieldUi?.();
      } else {
        syncEditFxSettlementFieldUi?.();
      }
      if (mode === "create") {
        updateCreatePreview();
      } else {
        updateEditPreview();
      }
    }

    function clearReceiptItems(mode = "create") {
      const ctx = getReceiptContext(mode);
      state[ctx.itemsKey] = [];
      state[ctx.seqKey] = 0;
      hideAllReceiptPickers();
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        syncCreateFxSettlementFieldUi?.();
      } else {
        syncEditFxSettlementFieldUi?.();
      }
    }

    function syncReceiptCategoriesToKind(mode = "create") {
      const kind = getReceiptOperationKind(mode);
      const allowedIds = new Set(
        (state.categories || [])
          .filter((item) => item.kind === kind)
          .map((item) => Number(item.id)),
      );
      for (const item of getReceiptItems(mode)) {
        if (item.category_id && !allowedIds.has(Number(item.category_id))) {
          item.category_id = null;
        }
      }
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === "create") {
        syncCreateFxSettlementFieldUi?.();
      } else {
        syncEditFxSettlementFieldUi?.();
      }
    }

    function resolveReceiptPayloadCategoryId(item, mode = "create", defaultCategoryId = null) {
      if (item?.category_id) {
        return Number(item.category_id);
      }
      const ctx = getReceiptContext(mode);
      const categoryInput = ctx.listNode?.querySelector(
        `[data-receipt-item-id="${Number(item?.draft_id || 0)}"] [data-receipt-field="category_search"]`,
      );
      const kind = getReceiptOperationKind(mode);
      const rawValue = normalizeReceiptName(categoryInput?.value || "");
      if (rawValue) {
        const exactMatch = (state.categories || []).find((entry) => (
          entry?.kind === kind && normalizeReceiptName(entry?.name || "").toLowerCase() === rawValue.toLowerCase()
        ));
        if (exactMatch?.id) {
          return Number(exactMatch.id);
        }
      }
      return defaultCategoryId;
    }

    function getCreateReceiptPayload() {
      if (!isReceiptModeEnabled("create")) {
        return [];
      }
      const defaultCategoryId = el.opCategory?.value ? Number(el.opCategory.value) : null;
      return getReceiptItems("create")
        .map((item) => ({
          ...(Number(item.template_id) > 0 ? { template_id: Number(item.template_id) } : {}),
          ...(Number(item.source_id) > 0 ? { source_id: Number(item.source_id) } : {}),
          ...(item.brand_touched ? { brand_id: item.brand_id ? Number(item.brand_id) : null } : {}),
          category_id: resolveReceiptPayloadCategoryId(item, "create", defaultCategoryId),
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          name: normalizeReceiptName(item.name),
          quantity: String(asQty(item.quantity || 0)),
          unit_price: core.formatAmount(item.unit_price || 0),
          is_discounted: Boolean(item.is_discounted),
          regular_unit_price: item.is_discounted && Number(item.regular_unit_price || 0) > 0
            ? core.formatAmount(item.regular_unit_price)
            : null,
          discount_type: item.is_discounted ? (item.discount_type || "promo") : null,
        }))
        .filter((item) => item.name && Number(item.quantity) > 0 && Number(item.unit_price) > 0);
    }

    function getEditReceiptPayload() {
      if (!isReceiptModeEnabled("edit")) {
        return [];
      }
      const defaultCategoryId = el.editCategory?.value ? Number(el.editCategory.value) : null;
      return getReceiptItems("edit")
        .map((item) => ({
          ...(Number(item.template_id) > 0 ? { template_id: Number(item.template_id) } : {}),
          ...(Number(item.source_id) > 0 ? { source_id: Number(item.source_id) } : {}),
          ...(item.brand_touched ? { brand_id: item.brand_id ? Number(item.brand_id) : null } : {}),
          category_id: resolveReceiptPayloadCategoryId(item, "edit", defaultCategoryId),
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          name: normalizeReceiptName(item.name),
          quantity: String(asQty(item.quantity || 0)),
          unit_price: core.formatAmount(item.unit_price || 0),
          is_discounted: Boolean(item.is_discounted),
          regular_unit_price: item.is_discounted && Number(item.regular_unit_price || 0) > 0
            ? core.formatAmount(item.regular_unit_price)
            : null,
          discount_type: item.is_discounted ? (item.discount_type || "promo") : null,
        }))
        .filter((item) => item.name && Number(item.quantity) > 0 && Number(item.unit_price) > 0);
    }

    return {
      createReceiptDraft,
      clearReceiptItems,
      setReceiptEnabled,
      renderReceiptItems,
      applySavedTemplateToReceiptDrafts,
      renderReceiptSummary,
      loadReceiptTemplateHints,
      handleReceiptItemsListInput,
      handleReceiptItemsListFocusOut,
      handleReceiptItemsListFocusIn,
      handleReceiptItemsListKeydown,
      handleReceiptItemsListClick,
      handleReceiptOutsidePointer,
      resizeReceiptNameTextarea,
      handlePullReceiptTotal,
      getCreateReceiptPayload,
      getEditReceiptPayload,
      syncReceiptCategoriesToKind,
    };
  }

  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-receipt-factory", createOperationModalReceiptFeature);
})();
