(() => {
  function createOperationsDisplayFeature(deps) {
    const { el, core, getCategoryMetaById } = deps;
    let activeReceiptItem = null;

    function getOperationDisplayCategories(item) {
      const categories = core.getReceiptCategoryMetas
        ? core.getReceiptCategoryMetas(item?.receipt_items, item?.category_id, getCategoryMetaById)
        : [];
      if (categories.length) {
        return categories;
      }
      if (item?.category_name) {
        return [{
          id: item?.category_id ? Number(item.category_id) : null,
          name: item.category_name,
          icon: item.category_icon || null,
          accent_color: item.category_accent_color || null,
        }];
      }
      const fallback = getCategoryMetaById(item?.category_id);
      return fallback?.name ? [fallback] : [];
    }

    function getOperationDisplayCategory(item) {
      return getOperationDisplayCategories(item)[0] || null;
    }

    function receiptDiscountLabel(row) {
      if (!row?.is_discounted) {
        return "";
      }
      const typeLabel = {
        promo: "Акция",
        coupon: "Купон",
        loyalty_points: "Баллы",
      }[row.discount_type] || "Скидка";
      const regular = Number(row.regular_unit_price || 0);
      const price = Number(row.unit_price || 0);
      if (regular > 0 && price > 0 && price < regular) {
        const percent = Math.round(((regular - price) / regular) * 100);
        return `${typeLabel} -${percent}%`;
      }
      return typeLabel;
    }

    function openOperationReceiptModal(item, options = {}) {
      if (!item || !Array.isArray(item.receipt_items) || item.receipt_items.length === 0) {
        return;
      }
      if (!el.operationReceiptModal || !el.operationReceiptItems) {
        return;
      }
      activeReceiptItem = item;
      const esc = (value) => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
      if (el.operationReceiptMeta) {
        const note = item.note ? ` · ${item.note}` : "";
        const money = item.currency && item.base_currency && item.currency !== item.base_currency
          ? `${core.formatMoney(item.original_amount || item.amount, { currency: item.currency })} · ≈ ${core.formatMoney(item.amount, { currency: item.base_currency })}`
          : core.formatMoney(item.amount, { currency: item.base_currency || item.currency || undefined });
        el.operationReceiptMeta.textContent = `${core.formatDateRu(item.operation_date)} · ${money}${note}`;
      }
      el.operationReceiptItems.innerHTML = item.receipt_items.map((row) => {
        const qty = Number(row.quantity || 0);
        const price = Number(row.unit_price || 0);
        const total = Number(row.line_total || qty * price || 0);
        const receiptCurrency = String(item.currency || item.base_currency || core.getCurrencyConfig?.().code || "BYN").toUpperCase();
        const media = window.App.getRuntimeModule?.("catalog-media") || {};
        const shopChip = row.shop_name
          ? `<div class="operation-receipt-shop catalog-source-identity">${media.renderThumb?.(row.source_image_id, { kind: "source", size: "chip", alt: row.shop_name, fallback: String(row.shop_name).slice(0, 1) }) || ""}${core.renderCategoryChip({ name: row.shop_name, icon: null, accent_color: null }, "")}</div>`
          : "";
        const categoryChip = row.category_id
          ? `<div class="operation-receipt-shop">${core.renderCategoryChip(getCategoryMetaById(row.category_id), "")}</div>`
          : "";
        const brandRenderer = window.App.getRuntimeModule?.("item-brands")?.renderBrandChip;
        const brandChip = row.brand_name
          ? `<span class="operation-receipt-brand">${typeof brandRenderer === "function" ? brandRenderer({ name: row.brand_name, accent_color: row.brand_accent_color || null, image_id: row.brand_image_id || null }) : core.renderCategoryChip({ name: row.brand_name, icon: null, accent_color: row.brand_accent_color || null }, "")}</span>`
          : "";
        const discountLabel = receiptDiscountLabel(row);
        const discountChip = discountLabel
          ? `<span class="operation-receipt-discount-chip">${esc(discountLabel)}</span>`
          : "";
        const regularPrice = row.is_discounted && Number(row.regular_unit_price || 0) > 0
          ? ` · обычная цена ${core.formatMoney(row.regular_unit_price, { currency: receiptCurrency })}`
          : "";
        const itemThumb = media.renderThumb?.(row.item_image_id, {
          kind: "item",
          size: "receipt",
          alt: row.name || "Позиция",
          fallback: String(row.name || "П").slice(0, 1),
        }) || "";
        const itemName = row.template_id
          ? `<button class="operation-receipt-item-open" type="button" data-open-receipt-template-card="${Number(row.template_id)}" title="Открыть карточку ${esc(row.name || "позиции")}">${itemThumb}<strong>${esc(row.name || "Без названия")}</strong></button>`
          : `<span class="operation-receipt-item-identity">${itemThumb}<strong title="${esc(row.name || "Без названия")}">${esc(row.name || "Без названия")}</strong></span>`;
        return `
          <article class="operation-receipt-item">
            <div class="operation-receipt-head">
              <div class="operation-receipt-title">
                ${brandChip}
                ${itemName}
                ${discountChip}
              </div>
              <span class="muted-small">${core.formatMoney(total, { currency: receiptCurrency })}</span>
            </div>
            ${shopChip}
            ${categoryChip}
            <div class="operation-receipt-meta muted-small">
              ${esc(core.formatAmount(qty))} × ${core.formatMoney(price, { currency: receiptCurrency })}${regularPrice}
            </div>
            ${row.note ? `<div class="muted-small">${esc(row.note)}</div>` : ""}
          </article>
        `;
      }).join("");
      el.operationReceiptModal.classList.remove("hidden");
      if (options.bringToFront !== false) {
        core.bringModalToFront?.(el.operationReceiptModal);
      }
    }

    function closeOperationReceiptModal() {
      activeReceiptItem = null;
      el.operationReceiptModal?.classList.add("hidden");
      core.markModalClosed?.(el.operationReceiptModal);
    }

    function refreshOpenReceiptTemplate(template) {
      const templateId = Number(template?.id || 0);
      if (!templateId || !activeReceiptItem || el.operationReceiptModal?.classList.contains("hidden")) {
        return false;
      }
      let changed = false;
      activeReceiptItem.receipt_items = (activeReceiptItem.receipt_items || []).map((row) => {
        if (Number(row?.template_id || 0) !== templateId) {
          return row;
        }
        changed = true;
        return {
          ...row,
          name: template?.name || row.name,
          item_image_id: template?.image_id || null,
          shop_name: template?.source_name || template?.shop_name || null,
          source_id: template?.source_id || null,
          source_image_id: template?.source_image_id || null,
          category_id: template?.last_category_id || null,
          brand_id: template?.brand_id || null,
          brand_name: template?.brand_name || null,
          brand_accent_color: template?.brand_accent_color || null,
          brand_image_id: template?.brand_image_id || null,
          brand_is_archived: Boolean(template?.brand_is_archived),
        };
      });
      if (!changed) {
        return false;
      }
      const card = el.operationReceiptModal?.querySelector?.(".modal-card");
      const scrollTop = card?.scrollTop || 0;
      openOperationReceiptModal(activeReceiptItem, { bringToFront: false });
      if (card) card.scrollTop = scrollTop;
      return true;
    }

    return {
      getOperationDisplayCategory,
      getOperationDisplayCategories,
      openOperationReceiptModal,
      closeOperationReceiptModal,
      refreshOpenReceiptTemplate,
    };
  }

  window.App.registerRuntimeModule?.("operations-display-factory", createOperationsDisplayFeature);
})();
