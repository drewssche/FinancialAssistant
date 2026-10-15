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
      return window.App.receiptPricing.calculate(item).total;
    }

    function receiptPricingExplanation(item, mode) {
      if (!item.discount_mode) return "Можно применить скидку после взвешивания или ввести оплаченный итог из чека.";
      const price = window.App.receiptPricing.calculate(item);
      if (price.error) return price.error;
      const before = price.subtotal == null ? "Цена до скидки неизвестна" : `До скидки: ${core.formatAmount(price.subtotal)}; скидка: ${core.formatAmount(price.subtotal - price.total)}`;
      return `${before}. Итого: ${core.formatAmount(price.total)} ${getReceiptCurrencyLabel(mode)}. ${item.discount_mode === "final" ? "При изменении количества введённый итог сохраняется." : "При изменении количества скидка пересчитывается выбранным способом."}`;
    }

    function receiptDiscountToggleLabel(item) {
      if (!item?.is_discounted) {
        return item?.discount_expanded ? "Закрыть настройки скидки" : "Настроить скидку";
      }
      const calculation = window.App.receiptPricing.calculate(item);
      const purchasePrice = item.discount_mode ? calculation.total : asMoney(item.unit_price || 0);
      const regularPrice = item.discount_mode ? calculation.subtotal : asMoney(item.regular_unit_price || 0);
      if (!(regularPrice > purchasePrice && purchasePrice > 0)) {
        return item.discount_expanded ? "Убрать скидку" : "Изменить скидку";
      }
      const percent = ((regularPrice - purchasePrice) / regularPrice) * 100;
      return `Скидка −${Number(percent.toFixed(1))}% · ${item.discount_expanded ? "убрать" : "изменить"}`;
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
        details_expanded: Boolean(seed.details_expanded),
        discount_expanded: false,
        template_id: seed.template_id || null,
        product_id: seed.product_id || null,
        product_name: normalizeReceiptName(seed.product_name || ""),
        product_image_id: seed.product_image_id || null,
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
        category_touched: Boolean(seed.category_touched),
        shop_name: normalizeReceiptName(seed.shop_name || ""),
        shop_name_inherited: Boolean(seed.shop_name_inherited),
        name: normalizeReceiptName(seed.name || ""),
        ...window.App.measurements.snapshot(seed),
        variant_id: seed.variant_id || null,
        variant_snapshot: seed.variant_snapshot ? structuredClone(seed.variant_snapshot) : null,
        measurement_touched: Boolean(seed.measurement_touched),
        quantity: hasQuantity ? asQty(seed.quantity) : 0,
        unit_price: hasUnitPrice ? (seed.discount_mode ? Number(seed.unit_price) : asMoney(seed.unit_price)) : 0,
        price_touched: seed.price_touched === undefined ? hasUnitPrice : Boolean(seed.price_touched),
        is_discounted: Boolean(seed.is_discounted),
        regular_unit_price: seed.regular_unit_price ? asMoney(seed.regular_unit_price) : 0,
        discount_type: seed.discount_type || (seed.is_discounted ? "promo" : null),
        discount_mode: seed.discount_mode || null,
        discount_value: seed.discount_value == null ? null : Number(seed.discount_value),
        note: seed.note || "",
      };
    }

    function getReceiptItemByDraftId(draftId, mode = "create") {
      return getReceiptItems(mode).find((entry) => Number(entry.draft_id) === Number(draftId)) || null;
    }

    function unlinkReceiptTemplateIdentity(item, options = {}) {
      item.template_id = null;
      if (!options.preserveProduct) {
        item.product_id = null;
        item.variant_id = null;
        item.variant_snapshot = null;
        item.variant_options = null;
        item.variant_status = "";
        item.product_name = "";
        item.product_image_id = null;
        item.item_image_id = null;
      } else {
        item.item_image_id = item.product_image_id || null;
      }
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

    function resolveReceiptProductOffer(item) {
      const productId = Number(item?.product_id || 0);
      if (!productId) return null;
      const product = (state.receiptProductHints || []).find((entry) => Number(entry.id) === productId);
      if (!product) return null;
      const sourceId = Number(item.source_id || 0);
      const shopCi = normalizeReceiptName(item.shop_name || "").toLowerCase();
      return (product.offers || []).find((offer) => (
        (sourceId && Number(offer.source_id || 0) === sourceId)
        || (shopCi && normalizeReceiptName(offer.source_name || offer.shop_name || "").toLowerCase() === shopCi)
      )) || null;
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
          item.product_id = template?.product_id || item.product_id || null;
          item.product_name = normalizeReceiptName(template?.product_name || item.product_name || item.name || "");
          item.product_image_id = template?.product_image_id || item.product_image_id || null;
          item.item_image_id = item.product_image_id || template?.image_id || null;
          item.shop_name = normalizeReceiptName(template?.source_name || template?.shop_name || "");
          item.source_id = template?.source_id || null;
          item.source_image_id = template?.source_image_id || null;
          item.category_id = template?.last_category_id ? Number(template.last_category_id) : null;
          item.category_touched = false;
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
        if (!thumb) {
          thumb = document.createElement("button");
          thumb.type = "button";
          thumb.className = "receipt-brand-thumb";
          thumb.dataset.receiptBrandThumb = "true";
          input?.before(thumb);
        }
        thumb.title = brandName ? `Открыть бренд ${brandName}` : "Выбрать бренд";
        thumb.setAttribute("aria-label", thumb.title);
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
      if (window.App.measurements.fields.includes(key)) {
        item[key] = value || null;
        item.measurement_touched = true;
        item.variant_id = null;
        item.variant_snapshot = null;
        item.variant_status = "";
      } else if (key === "variant_id") {
        if (value === "saved") return {item, hadName, hasName: hasReceiptRowName(item)};
        const variant = (item.variant_options || []).find((v) => String(v.id) === value);
        item.variant_id = variant?.id || null;
        item.variant_snapshot = variant ? {variant_id: variant.id, name: variant.name, codes: [...(variant.codes || [])]} : null;
        if (variant) Object.assign(item, window.App.measurements.snapshot(variant));
        item.measurement_touched = true;
        item.variant_status = variant ? "Фасовка выбрана. Проверьте количество и цену." : "Фасовка не связана с каталогом. Размеры можно указать вручную.";
      } else if (key === "quantity") {
        item.quantity = asQty(value);
      } else if (key === "unit_price") {
        item.unit_price = asMoney(value);
      } else if (key === "discount_mode") {
        const total = receiptLineTotal(item);
        const subtotal = asMoney(item.regular_unit_price * asQty(item.quantity));
        item.discount_mode = ["amount", "percent", "final"].includes(value) ? value : null;
        item.discount_value = value === "final" ? total : value === "percent"
          ? (subtotal > 0 ? Number(((subtotal - total) / subtotal * 100).toFixed(4)) : 0)
          : value === "amount" ? Math.max(0, asMoney(subtotal - total)) : null;
        if (!item.discount_mode) item.unit_price = asMoney(total / (item.quantity || 1));
        item.price_touched = true;
      } else if (key === "discount_value") {
        item.discount_value = item.discount_mode === "percent"
          ? Number(String(value).replace(",", ".")) : asMoney(value);
      } else if (key === "regular_unit_price") {
        item.regular_unit_price = asMoney(value);
      } else if (key === "is_discounted") {
        item.is_discounted = Boolean(value);
        item.discount_type = item.is_discounted ? (item.discount_type || "promo") : null;
        if (!item.is_discounted) {
          if (item.discount_mode) item.unit_price = asMoney(item.regular_unit_price || receiptLineTotal(item) / (item.quantity || 1));
          item.discount_mode = null;
          item.discount_value = null;
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
          const keepProduct = Boolean(item.product_id);
          if (unlinkReceiptTemplateIdentity(item, { preserveProduct: keepProduct })) {
            syncReceiptBrandField(item, mode);
          }
          if (keepProduct) {
            const offer = resolveReceiptProductOffer(item);
            item.template_id = Number(offer?.template_id || offer?.id || 0) || null;
            item.name = normalizeReceiptName(offer?.name || item.product_name || item.name || "");
            item.item_image_id = item.product_image_id || offer?.image_id || null;
            if (!item.price_touched) item.unit_price = offer?.latest_unit_price || 0;
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
        item.category_touched = true;
      } else if (key === "note") {
        item.note = value || "";
      }
      // Opening the editor is not a purchase discount. Only edited price data
      // can activate it; invalid values remain active so validation still blocks save.
      if (["discount_mode", "discount_value", "regular_unit_price", "unit_price", "quantity"].includes(key) && item.discount_expanded) {
        const calculation = window.App.receiptPricing.calculate(item);
        item.is_discounted = item.discount_mode
          ? Boolean(calculation.error || (calculation.subtotal == null ? item.discount_mode === "final" : calculation.total < calculation.subtotal))
          : Number(item.regular_unit_price) > Number(item.unit_price);
        // Keep the chosen type while entering a discount; payloads omit it until a discount exists.
        item.discount_type = item.discount_type || (item.is_discounted ? "promo" : null);
        if (!item.is_discounted && item.discount_mode) item.unit_price = item.regular_unit_price;
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
            if (unlinkReceiptTemplateIdentity(item, { preserveProduct: Boolean(item.product_id) })) {
              syncReceiptBrandField(item, mode);
            }
            const offer = resolveReceiptProductOffer(item);
            item.template_id = Number(offer?.template_id || offer?.id || 0) || null;
            item.name = normalizeReceiptName(offer?.name || item.product_name || item.name || "");
            item.item_image_id = item.product_image_id || offer?.image_id || null;
            if (!item.price_touched) item.unit_price = offer?.latest_unit_price || 0;
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
      const name = normalizeReceiptName(brand?.name || "");
      return window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(brand.imageId, {
        kind: "brand",
        size: "picker",
        className: "receipt-brand-media",
        alt: name ? `Логотип ${name}` : "Бренд не выбран",
        fallback: name.slice(0, 1) || "Б",
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
        const linkedItemThumb = (item.product_id || item.template_id) ? media.renderThumb?.(item.product_image_id || item.item_image_id, {
          kind: "item",
          size: "picker",
          alt: item.name || "Позиция",
          fallback: String(item.name || "П").slice(0, 1),
        }) || "" : "";
        const known = Boolean(item.product_id || item.template_id);
        const compact = !item.details_expanded;
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
          <div class="receipt-item-row ${known ? "receipt-item-known" : ""} ${compact ? "is-compact" : ""} ${!item.name && !item.is_discounted && !item.unit_price && !item.quantity ? "receipt-item-empty" : ""} ${item.discount_expanded ? "discount-open" : ""} ${item.is_discounted ? "receipt-item-row-discounted" : ""} ${hasOpenPicker ? "has-open-popover" : ""}" data-receipt-mode="${mode}" data-receipt-item-id="${item.draft_id}">
            ${known ? `<div class="receipt-compact-heading">
              <div><button class="receipt-compact-name" type="button" ${item.product_id ? `data-open-receipt-product-card="${Number(item.product_id)}"` : `data-open-receipt-template-card="${Number(item.template_id)}"`}>${esc(item.product_name || item.name)}</button>
              <small>${esc([brandName, item.shop_name || "Без источника", item.variant_snapshot?.name, (item.sale_unit || item.package_quantity ? window.App.measurements.summary(item) : "")].filter(Boolean).join(" · "))}</small></div>
            </div>` : ""}
            ${!known ? `<div class="receipt-compact-heading receipt-new-heading"><span>${item.name ? "Новый товар" : "Добавить товар"}</span></div>` : ""}
            <button class="btn btn-secondary btn-xs ${compact ? "" : "is-active"}" type="button" data-receipt-details-toggle="${item.draft_id}" aria-label="Подробности товара" aria-expanded="${!compact}" title="${compact ? "Показать подробности товара" : "Скрыть подробности товара"}">Детали</button>
            <div class="receipt-item-identity">
              <div class="receipt-shop-cell ${shopPickerOpen ? "has-open-popover" : ""}">
                <input type="text" data-receipt-field="shop_name" value="${esc(item.shop_name || "")}" placeholder="Источник" title="${esc(item.shop_name || "Источник")}" autocomplete="off" aria-label="Источник позиции" />
                <div class="receipt-shop-picker app-popover ${shopPickerOpen ? "" : "hidden"}"></div>
              </div>
              <div class="receipt-brand-cell ${brandPickerOpen ? "has-open-popover" : ""} ${brandName ? "has-brand" : ""}" style="--receipt-brand-accent: ${brandAccent}">
                <button class="receipt-brand-thumb" type="button" data-receipt-brand-thumb="true" title="${esc(brandName ? `Открыть бренд ${brandName}` : "Выбрать бренд")}" aria-label="${esc(brandName ? `Открыть бренд ${brandName}` : "Выбрать бренд")}">${brandThumb}</button>
                <input type="text" data-receipt-field="brand_search" value="${esc(brandName)}" placeholder="Бренд" title="${esc(brandName || "Бренд не выбран")}" autocomplete="off" aria-label="Бренд позиции" />
                <div class="receipt-brand-picker app-popover ${brandPickerOpen ? "" : "hidden"}"></div>
              </div>
              <div class="receipt-name-cell ${namePickerOpen ? "has-open-popover" : ""}">
                <div class="receipt-name-field-wrap">
                  ${item.product_id ? `<button class="receipt-linked-thumb" type="button" data-open-receipt-product-card="${Number(item.product_id)}" title="Открыть карточку товара" aria-label="Открыть карточку ${esc(item.name || "товара")}">${linkedItemThumb}</button>` : (item.template_id ? `<button class="receipt-linked-thumb" type="button" data-open-receipt-template-card="${Number(item.template_id)}" title="Открыть карточку позиции" aria-label="Открыть карточку ${esc(item.name || "позиции")}">${linkedItemThumb}</button>` : "")}
                  <textarea class="receipt-name-input" rows="1" data-receipt-field="name" placeholder="Найти или ввести товар" title="${esc(item.name || "Позиция")}" aria-label="Название позиции">${esc(item.name)}</textarea>
                  ${item.product_id ? `<button class="receipt-template-card-btn" type="button" data-open-receipt-product-card="${Number(item.product_id)}" title="Открыть карточку товара" aria-label="Открыть карточку товара">↗</button>` : (item.template_id ? `<button class="receipt-template-card-btn" type="button" data-open-receipt-template-card="${Number(item.template_id)}" title="Открыть карточку позиции" aria-label="Открыть карточку позиции">↗</button>` : "")}
                </div>
                <span class="receipt-new-badge ${item.name && !item.template_id ? "" : "hidden"}">${item.product_id ? "Новое предложение" : "Новая позиция"}</span>
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
            <section class="receipt-measurements">
              <div class="receipt-variant-controls">
                <small data-receipt-variant-snapshot>${esc(item.variant_snapshot ? `Фасовка: ${item.variant_snapshot.name}${item.variant_snapshot.codes?.length ? " · " + item.variant_snapshot.codes.join(", ") : ""}` : "")}</small>
                ${item.product_id ? `<button class="btn btn-secondary btn-xs" type="button" data-receipt-variants-load ${item.variant_loading ? "disabled" : ""}>${item.variant_loading ? "Загрузка…" : item.variant_options ? "Другие размеры" : "Другие размеры"}</button>` : ""}
                ${item.variant_options || item.variant_snapshot ? `<label class="field"><span>Сохранённые размеры</span><select data-receipt-field="variant_id" aria-label="Фасовка товара">
                  <option value="">Свой размер</option>
                  ${item.variant_snapshot && !item.variant_id ? `<option value="saved" selected>Сохранено: ${esc(item.variant_snapshot.name)}</option>` : ""}
                  ${(item.variant_options || []).map((v) => `<option value="${Number(v.id)}" ${Number(item.variant_id) === Number(v.id) ? "selected" : ""}>${esc(v.name)} · ${esc(window.App.measurements.summary(v))}${v.codes?.length ? " · " + esc(v.codes.join(", ")) : ""}</option>`).join("")}
                </select></label>` : ""}
                <small role="status">${esc(item.variant_status || "")}</small>
              </div>
              <div class="form-grid">
                <label class="field"><span>Единица продажи</span><select data-receipt-field="sale_unit" aria-label="Единица продажи">${window.App.measurements.options(item.sale_unit)}</select></label>
                <label class="field"><span>В одной штуке / упаковке</span><input type="number" min="0.001" step="0.001" data-receipt-field="package_quantity" value="${esc(item.package_quantity || "")}" placeholder="Например, 900" aria-label="Содержимое упаковки" /></label>
                <label class="field"><span>Единица содержимого</span><select data-receipt-field="package_unit" aria-label="Единица содержимого">${window.App.measurements.options(item.package_unit, true)}</select></label>
              </div>
            </section>
            ${item.is_discounted || item.discount_expanded ? `<section class="receipt-discount-calculation">
              <div class="receipt-discount-type-row" role="group" aria-label="Тип скидки"><span class="muted-small">Тип скидки</span>${discountTypeButtons}</div>
              <div class="form-grid">
                <label class="field"><span>Способ расчёта</span><select data-receipt-field="discount_mode" aria-label="Способ расчёта скидки">
                  ${[["", "Цена за единицу"], ["amount", "Скидка на сумму"], ["percent", "Скидка в процентах"], ["final", "Оплаченный итог"]].map(([value, label]) => `<option value="${value}" ${(item.discount_mode || "") === value ? "selected" : ""}>${label}</option>`).join("")}
                </select></label>
                ${item.discount_mode ? `<label class="field"><span>${item.discount_mode === "final" ? "Оплачено за позицию" : item.discount_mode === "percent" ? "Скидка, %" : "Скидка за всю позицию"}</span><input type="text" inputmode="decimal" data-receipt-field="discount_value" value="${esc(String(item.discount_value ?? 0))}" aria-label="Значение скидки или итог" /></label>` : ""}
              </div>
              <div class="muted-small receipt-pricing-explanation">${esc(receiptPricingExplanation(item, mode))}</div><button class="btn btn-secondary btn-xs" type="button" data-receipt-discount-remove="${item.draft_id}">Убрать скидку</button>
            </section>` : ""}
            <div class="receipt-item-money">
              <div class="receipt-price-cell ${item.is_discounted ? "receipt-price-cell-discounted" : ""}">
                <span class="receipt-known-price-label">${esc(window.App.measurements.priceLabel(item, Boolean(item.is_discounted)))}</span>
                <div class="receipt-price-field">
                  <input type="text" inputmode="decimal" data-receipt-field="unit_price" ${item.discount_mode ? "readonly" : ""} value="${formatReceiptInputAmount(item.discount_mode && item.is_discounted ? total / (item.quantity || 1) : item.unit_price)}" placeholder="Цена" title="${item.discount_mode ? "Эффективная цена после скидки; итог рассчитывается отдельно" : "Цена покупки в " + esc(getReceiptCurrencyLabel(mode))}" aria-label="Цена позиции" />
                </div>
                <button class="receipt-discount-toggle ${item.is_discounted ? "is-active" : ""}" type="button" data-receipt-discount-toggle="${item.draft_id}" aria-pressed="${item.is_discounted ? "true" : "false"}" aria-expanded="${item.discount_expanded ? "true" : "false"}" aria-label="${receiptDiscountToggleLabel(item)}" title="${receiptDiscountToggleLabel(item)}">${window.App.icons.svg("discount")}</button>
                <div class="receipt-price-field receipt-regular-price-field ${item.is_discounted || item.discount_expanded ? "" : "hidden"}">
                  <input class="receipt-regular-price" type="text" inputmode="decimal" data-receipt-field="regular_unit_price" value="${formatReceiptInputAmount(item.regular_unit_price)}" placeholder="До скидки" title="Обычная цена для истории" aria-label="Цена до скидки" />
                </div>
              </div>
              <div class="receipt-quantity-cell">
                <span>${esc(window.App.measurements.quantityLabel(item))}</span>
                <input type="number" step="0.001" min="0" data-receipt-field="quantity" value="${item.quantity || ""}" placeholder="Кол-во" aria-label="Количество позиции" />
              </div>
              <div class="receipt-line-total"><span>Итого</span><strong>${formatReceiptMoney(total, mode)}</strong></div>
              <button class="btn btn-danger receipt-remove-btn ${removeHidden ? "hidden" : ""}" type="button" data-receipt-remove-id="${item.draft_id}" title="Удалить позицию" aria-label="Удалить позицию">×</button>
            </div>
          </div>
        `;
      }).join("");
      ctx.listNode.querySelectorAll('.receipt-measurements .form-grid').forEach(grid => {
        window.App.measurements.mount(grid, window.App.measurements.fields.map(key => grid.querySelector(`[data-receipt-field="${key}"]`)));
      });
      ctx.listNode.querySelectorAll('textarea[data-receipt-field="name"]').forEach(resizeReceiptNameTextarea);
      ctx.listNode.querySelectorAll('.receipt-item-row').forEach(row => {
        row.querySelector('.receipt-price-field')?.append(row.querySelector('.receipt-discount-toggle'));
      });
      // Discount editing is independent of catalog details.
      ctx.listNode.querySelectorAll('.receipt-item-row-discounted, .discount-open').forEach(row => {
        const panel = row.querySelector('.receipt-discount-calculation');
        const price = row.querySelector('.receipt-regular-price-field');
        if (panel && price) {
          const label = document.createElement('span'); label.textContent = 'Цена за единицу до скидки';
          price.prepend(label); panel.querySelector('.form-grid').prepend(price);
        }
      });
      const store = ctx.fieldsNode?.querySelector('[data-receipt-store]');
      if (store && document.activeElement !== store) store.value = rows[0]?.shop_name || '';
      priceHints?.refresh(mode);
    }

    document.addEventListener('change', event => {
      const store = event.target.closest('[data-receipt-store]');
      if (!store) return;
      const mode = store.dataset.receiptStore;
      const first = getReceiptItems(mode)[0];
      if (!first || normalizeReceiptName(first.shop_name || '') === normalizeReceiptName(store.value)) return;
      updateReceiptItemField(first.draft_id, 'shop_name', store.value, mode);
      inheritReceiptShopFromFirstRow(first.draft_id, mode);
      renderReceiptItems(mode);
      renderReceiptSummary(mode);
      if (mode === 'create') updateCreatePreview(); else updateEditPreview();
    });

    function getReceiptTotal(mode = "create") {
      return getReceiptItems(mode).reduce((acc, item) => acc + receiptLineTotal(item), 0);
    }

    function syncReceiptNumericInputs(mode = "create") {
      const ctx = getReceiptContext(mode);
      ctx.listNode?.querySelectorAll("[data-receipt-item-id]").forEach((row) => {
        const draftId = Number(row.dataset.receiptItemId || 0);
        for (const field of ["quantity", "unit_price", "regular_unit_price", "discount_value", ...window.App.measurements.fields]) {
          const input = row.querySelector(`[data-receipt-field="${field}"]`);
          if (input && !input.readOnly && (!window.App.measurements.fields.includes(field) || String(getReceiptItems(mode).find(item => Number(item.draft_id) === draftId)?.[field] ?? "") !== input.value)) {
            updateReceiptItemField(draftId, field, input.value, mode);
          }
        }
      });
    }

    function renderReceiptSummary(mode = "create", options = {}) {
      priceHints?.refresh(mode);
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
      // Compare cents: floating-point residue such as 3.55e-15 must never enter the expression parser.
      const diff = hasAmountOverride || !resolvedAmount.empty
        ? (Math.round(comparedAmount * 100) - Math.round(total * 100)) / 100 : 0;
      const diffHtml = receiptCurrency === baseCurrency
        ? formatReceiptMoney(diff, resolvedMode)
        : `${formatReceiptMoney(diff, resolvedMode)} <span class="muted-small">· ≈ ${core.formatMoney(diff * fxRate, { currency: baseCurrency })}</span>`;
      if (ctx.diffLabelNode) {
        ctx.diffLabelNode.textContent = `Расхождение (${getReceiptCurrencyLabel(resolvedMode)})`;
      }
      if (ctx.diffNode) {
        ctx.diffNode.innerHTML = diffHtml;
        const mismatch = !resolvedAmount.empty && Math.abs(diff) >= 0.01;
        ctx.diffNode.classList.toggle("receipt-diff-warn", mismatch);
        ctx.diffNode.parentElement.hidden = !mismatch;
        const pull = document.getElementById(mode === 'edit' ? 'editPullReceiptTotalBtn' : 'pullReceiptTotalBtn');
        if (pull) pull.hidden = !mismatch;
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

    const priceHints = window.App.getRuntimeModule?.("receipt-price-hints-factory")?.({
      state, core, getReceiptItems, getReceiptContext, getReceiptCurrency, getReceiptOperationKind,
    });

    const createOperationModalReceiptInteractionsFeature = window.App.getRuntimeModule?.("operation-modal-receipt-interactions-factory");
    const interactions = createOperationModalReceiptInteractionsFeature
      ? createOperationModalReceiptInteractionsFeature({
        state,
        el,
        core,
        receiptUiState,
        priceHints,
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
        receiptPricingExplanation,
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
          item.category_touched = false;
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
          ...(Number(item.product_id) > 0 ? { product_id: Number(item.product_id) } : {}),
          ...(Number(item.source_id) > 0 ? { source_id: Number(item.source_id) } : {}),
          ...(item.brand_touched ? { brand_id: item.brand_id ? Number(item.brand_id) : null } : {}),
          category_id: resolveReceiptPayloadCategoryId(item, "create", defaultCategoryId),
          category_touched: Boolean(item.category_touched),
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          name: normalizeReceiptName(item.name),
          ...(item.note ? { note: item.note } : {}),
          ...window.App.measurements.snapshot(item),
          variant_id: item.variant_id || null,
          variant_snapshot: item.variant_snapshot || null,
          quantity: String(asQty(item.quantity || 0)),
          unit_price: core.formatAmount(item.unit_price || 0),
          is_discounted: Boolean(item.is_discounted),
          regular_unit_price: item.is_discounted && Number(item.regular_unit_price || 0) > 0
            ? core.formatAmount(item.regular_unit_price)
            : null,
          discount_type: item.is_discounted ? (item.discount_type || "promo") : null,
          ...window.App.receiptPricing.payload(item.is_discounted ? item : {...item, discount_mode: null}),
        }))
        .filter((item) => item.name && (item.discount_mode || (Number(item.quantity) > 0 && Number(item.unit_price) > 0)));
    }

    function getEditReceiptPayload() {
      if (!isReceiptModeEnabled("edit")) {
        return [];
      }
      const defaultCategoryId = el.editCategory?.value ? Number(el.editCategory.value) : null;
      return getReceiptItems("edit")
        .map((item) => ({
          ...(Number(item.template_id) > 0 ? { template_id: Number(item.template_id) } : {}),
          ...(Number(item.product_id) > 0 ? { product_id: Number(item.product_id) } : {}),
          ...(Number(item.source_id) > 0 ? { source_id: Number(item.source_id) } : {}),
          ...(item.brand_touched ? { brand_id: item.brand_id ? Number(item.brand_id) : null } : {}),
          category_id: resolveReceiptPayloadCategoryId(item, "edit", defaultCategoryId),
          category_touched: Boolean(item.category_touched),
          shop_name: normalizeReceiptName(item.shop_name || "") || null,
          name: normalizeReceiptName(item.name),
          ...(item.note ? { note: item.note } : {}),
          ...window.App.measurements.snapshot(item),
          variant_id: item.variant_id || null,
          variant_snapshot: item.variant_snapshot || null,
          quantity: String(asQty(item.quantity || 0)),
          unit_price: core.formatAmount(item.unit_price || 0),
          is_discounted: Boolean(item.is_discounted),
          regular_unit_price: item.is_discounted && Number(item.regular_unit_price || 0) > 0
            ? core.formatAmount(item.regular_unit_price)
            : null,
          discount_type: item.is_discounted ? (item.discount_type || "promo") : null,
          ...window.App.receiptPricing.payload(item.is_discounted ? item : {...item, discount_mode: null}),
        }))
        .filter((item) => item.name && (item.discount_mode || (Number(item.quantity) > 0 && Number(item.unit_price) > 0)));
    }

    return {
      receiptCatalog: interactions.receiptCatalog,
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
