(() => {
  function createOperationsDisplayFeature(deps) {
    const { el, core, getCategoryMetaById } = deps;

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

    function openOperationReceiptModal(item) {
      if (!item || !Array.isArray(item.receipt_items) || item.receipt_items.length === 0) {
        return;
      }
      if (!el.operationReceiptModal || !el.operationReceiptItems) {
        return;
      }
      const esc = (value) => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
      if (el.operationReceiptMeta) {
        const note = item.note ? ` · ${item.note}` : "";
        el.operationReceiptMeta.textContent = `${core.formatDateRu(item.operation_date)} · ${core.formatMoney(item.amount)}${note}`;
      }
      el.operationReceiptItems.innerHTML = item.receipt_items.map((row) => {
        const qty = Number(row.quantity || 0);
        const price = Number(row.unit_price || 0);
        const total = Number(row.line_total || qty * price || 0);
        const shopChip = row.shop_name
          ? `<div class="operation-receipt-shop">${core.renderCategoryChip({ name: row.shop_name, icon: null, accent_color: null }, "")}</div>`
          : "";
        const categoryChip = row.category_id
          ? `<div class="operation-receipt-shop">${core.renderCategoryChip(getCategoryMetaById(row.category_id), "")}</div>`
          : "";
        return `
          <article class="operation-receipt-item">
            <div class="operation-receipt-head">
              <strong>${esc(row.name || "Без названия")}</strong>
              <span class="muted-small">${core.formatMoney(total)}</span>
            </div>
            ${shopChip}
            ${categoryChip}
            <div class="operation-receipt-meta muted-small">
              ${esc(core.formatAmount(qty))} × ${core.formatMoney(price)}
            </div>
            ${row.note ? `<div class="muted-small">${esc(row.note)}</div>` : ""}
          </article>
        `;
      }).join("");
      el.operationReceiptModal.classList.remove("hidden");
    }

    function closeOperationReceiptModal() {
      el.operationReceiptModal?.classList.add("hidden");
    }

    return {
      getOperationDisplayCategory,
      getOperationDisplayCategories,
      openOperationReceiptModal,
      closeOperationReceiptModal,
    };
  }

  window.App.registerRuntimeModule?.("operations-display-factory", createOperationsDisplayFeature);
})();
