(() => {
  function renderContextActions(entityType, entity, escapeHtml) {
    const contextActions = window.App.getRuntimeModule?.("context-actions");
    return (contextActions?.keys?.(entityType, "row") || []).map((key) => {
      if (entityType === "item_template") {
        if (key === "activity") return `<button class="btn btn-secondary" data-activity-entity-type="item_template" data-activity-entity-id="${entity.id}" type="button">Журнал</button>`;
        if (key === "usage") return `<button class="btn btn-secondary" data-usage-entity-type="item_template" data-usage-entity-id="${entity.id}" data-usage-entity-name="${escapeHtml(entity.name || "")}" type="button">Операции</button>`;
        if (key === "history") return `<button class="btn btn-secondary" data-item-template-history-id="${entity.id}" type="button">История</button>`;
        if (key === "edit") return `<button class="btn btn-secondary" data-edit-item-template-id="${entity.id}" type="button">Редактировать</button>`;
        if (key === "delete") return `<button class="btn btn-danger" data-delete-item-template-id="${entity.id}" type="button">Удалить</button>`;
      }
      if (entityType === "item_source") {
        const sourceName = escapeHtml(entity.shopName || "");
        if (key === "create_child") return `<button class="btn btn-secondary" data-create-item-template-source-name="${sourceName}" type="button">Добавить позицию</button>`;
        if (key === "edit") return `<button class="btn btn-secondary" data-edit-item-source-name="${sourceName}" type="button">Редактировать</button>`;
        if (key === "delete") return `<button class="btn btn-danger" data-delete-item-source-name="${sourceName}" type="button">Удалить</button>`;
      }
      return "";
    }).join("");
  }

  function isCompactMobileViewport() {
    return window.matchMedia("(max-width: 640px)").matches;
  }

  function buildItemCatalogGroups({
    rows,
    state,
    readItemCatalogSourceGroups,
    normalizeItemCatalogShopName,
    getItemCatalogShopKey,
    compareItemCatalogItems,
    itemCatalogLastUsedMs,
    itemCatalogNoShopKey,
  }) {
    const grouped = new Map();
    for (const sourceName of readItemCatalogSourceGroups()) {
      const sourceKey = getItemCatalogShopKey(sourceName);
      if (!grouped.has(sourceKey)) {
        grouped.set(sourceKey, {
          shopKey: sourceKey,
          shopName: sourceName || "Без источника",
          items: [],
        });
      }
    }
    for (const item of rows) {
      const shopNameRaw = normalizeItemCatalogShopName(item.shop_name || "");
      const shopKey = getItemCatalogShopKey(shopNameRaw);
      if (!grouped.has(shopKey)) {
        grouped.set(shopKey, {
          shopKey,
          shopName: shopNameRaw || "Без источника",
          items: [],
        });
      }
      grouped.get(shopKey).items.push(item);
    }
    const preset = state.itemCatalogSortPreset || "usage";
    const groups = Array.from(grouped.values()).map((group) => {
      const sortedItems = group.items.slice().sort((a, b) => compareItemCatalogItems(a, b, preset));
      const useCountTotal = sortedItems.reduce((acc, item) => acc + Number(item.use_count || 0), 0);
      const prices = sortedItems
        .map((item) => Number(item.latest_unit_price || 0))
        .filter((value) => Number.isFinite(value) && value > 0);
      const avgPrice = prices.length ? prices.reduce((acc, value) => acc + value, 0) / prices.length : null;
      const lastUsedMs = sortedItems.reduce((max, item) => {
        const ts = itemCatalogLastUsedMs(item);
        return ts > max ? ts : max;
      }, 0);
      return {
        ...group,
        items: sortedItems,
        useCountTotal,
        avgPrice,
        lastUsedMs,
        lastUsedLabel: lastUsedMs ? new Date(lastUsedMs).toLocaleDateString("ru-RU") : "—",
      };
    });

    groups.sort((a, b) => {
      const aNoShop = a.shopKey === itemCatalogNoShopKey ? 1 : 0;
      const bNoShop = b.shopKey === itemCatalogNoShopKey ? 1 : 0;
      if (aNoShop !== bNoShop) {
        return aNoShop - bNoShop;
      }
      if (preset === "name") {
        return a.shopName.localeCompare(b.shopName, "ru");
      }
      if (preset === "recent") {
        const tsDiff = b.lastUsedMs - a.lastUsedMs;
        if (tsDiff !== 0) {
          return tsDiff;
        }
        const usageDiff = b.useCountTotal - a.useCountTotal;
        if (usageDiff !== 0) {
          return usageDiff;
        }
        return a.shopName.localeCompare(b.shopName, "ru");
      }
      const usageDiff = b.useCountTotal - a.useCountTotal;
      if (usageDiff !== 0) {
        return usageDiff;
      }
      const tsDiff = b.lastUsedMs - a.lastUsedMs;
      if (tsDiff !== 0) {
        return tsDiff;
      }
      return a.shopName.localeCompare(b.shopName, "ru");
    });

    return groups;
  }

  function renderItemCatalog({
    items,
    el,
    state,
    core,
    escapeHtml,
    readItemCatalogCollapsedShops,
    buildItemCatalogGroups,
    syncItemCatalogControls,
  }) {
    if (!el.itemCatalogBody) {
      return;
    }
    const allRows = Array.isArray(items) ? items : [];
    const query = String(el.itemCatalogSearchQ?.value || "").trim();
    const queryActive = Boolean(query);
    const brandFilter = String(state.itemCatalogBrandFilter || "all");
    const brandFilterActive = brandFilter !== "all";
    const rows = allRows.filter((item) => {
      if (brandFilter === "unassigned") {
        return !Number(item?.brand_id || 0);
      }
      if (/^\d+$/.test(brandFilter)) {
        return Number(item?.brand_id || 0) === Number(brandFilter);
      }
      return true;
    });
    core.syncSegmentedActive(el.itemCatalogSortTabs, "item-sort", state.itemCatalogSortPreset || "usage");
    const groupsAll = buildItemCatalogGroups(rows);
    const groups = queryActive || brandFilterActive
      ? groupsAll.filter((group) => {
        const sourceMatch = group.shopName.toLowerCase().includes(query.toLowerCase());
        return group.items.length > 0 || (queryActive && sourceMatch && !brandFilterActive);
      })
      : groupsAll;
    if (el.itemCatalogKpiGrid) {
      const visibleItems = groups.flatMap((group) => group.items || []);
      const sourceCount = groups.filter((group) => group.shopKey !== "__no_shop__" && (group.items || []).length > 0).length;
      const totalUseCount = visibleItems.reduce((sum, item) => sum + Number(item.use_count || 0), 0);
      const brandedCount = visibleItems.filter((item) => Number(item?.brand_id || 0)).length;
      el.itemCatalogKpiGrid.innerHTML = `
        <article class="analytics-kpi-card analytics-kpi-neutral">
          <div class="muted-small">Позиций</div>
          <strong>${visibleItems.length}</strong>
        </article>
        <article class="analytics-kpi-card analytics-kpi-neutral">
          <div class="muted-small">Источников</div>
          <strong>${sourceCount}</strong>
        </article>
        <article class="analytics-kpi-card analytics-kpi-positive">
          <div class="muted-small">Использований</div>
          <strong>${totalUseCount}</strong>
        </article>
        <article class="analytics-kpi-card ${brandedCount === visibleItems.length ? "analytics-kpi-positive" : "analytics-kpi-neutral"}">
          <div class="muted-small">С брендом</div>
          <strong>${brandedCount} из ${visibleItems.length}</strong>
        </article>
      `;
    }
    if (!groups.length) {
      syncItemCatalogControls({ el, queryActive: queryActive || brandFilterActive, hasRows: false });
      el.itemCatalogBody.innerHTML = '<tr><td colspan="7">Нет позиций</td></tr>';
      return;
    }
    syncItemCatalogControls({ el, queryActive: queryActive || brandFilterActive, hasRows: true });
    const collapsedShops = readItemCatalogCollapsedShops();
    const selectedIds = state.selectedItemCatalogIds || new Set();
    const brandsById = new Map((state.itemBrands || []).map((brand) => [Number(brand?.id || 0), brand]));
    const brandFeature = window.App.getRuntimeModule?.("item-brands") || {};

    const compactMobile = isCompactMobileViewport();
    el.itemCatalogBody.innerHTML = groups.map((group) => {
      const isCollapsed = !queryActive && !brandFilterActive && collapsedShops.has(group.shopKey);
      const chevron = isCollapsed ? "▸" : "▾";
      const sourceActions = renderContextActions("item_source", group, escapeHtml);
      const childRows = group.items.map((item) => {
        const itemActions = renderContextActions("item_template", item, escapeHtml);
        const category = (state.categories || []).find((row) => Number(row?.id || 0) === Number(item?.last_category_id || 0));
        const categoryHtml = category?.name
          ? core.renderCategoryChip({
            name: category.name,
            icon: category.icon || category.group_icon || null,
            accent_color: category.group_accent_color || null,
          }, query)
          : "<span class='muted-small'>Без категории</span>";
        const brandMeta = brandsById.get(Number(item?.brand_id || 0)) || (item?.brand_name ? {
          id: item.brand_id,
          name: item.brand_name,
          accent_color: item.brand_accent_color,
          is_archived: Boolean(item.brand_is_archived),
        } : null);
        const brandHtml = brandFeature.renderBrandChip?.(brandMeta) || (brandMeta?.name
          ? `<span class="item-brand-chip"><span class="item-brand-chip-name">${escapeHtml(brandMeta.name)}</span></span>`
          : '<span class="item-brand-unassigned">Без бренда</span>');
        const selected = selectedIds.has(Number(item.id));
        if (compactMobile) {
          return `
            <tr class="item-catalog-item-row table-hierarchy-child-row item-catalog-mobile-item-row table-record-open-row ${isCollapsed ? "hidden" : ""}" data-item-template-row="1" data-item-template-open-id="${item.id}">
              <td colspan="7" class="item-catalog-mobile-item-cell">
                <div class="item-catalog-mobile-item-card">
                  <div class="item-catalog-mobile-item-head">
                    <label class="item-catalog-mobile-item-select"><input data-item-catalog-select-id="${Number(item.id)}" type="checkbox" ${selected ? "checked" : ""} aria-label="Выбрать ${escapeHtml(item.name || "позицию")}" /></label>
                    <div class="item-catalog-mobile-item-title">${core.highlightText(item.name || "—", query)}</div>
                    <div class="mobile-card-kebab-wrap">
                      <button class="btn btn-secondary mobile-card-kebab-trigger" data-mobile-card-menu-trigger="item-template-${item.id}" type="button" aria-label="Действия позиции">
                        <span aria-hidden="true">⋮</span>
                      </button>
                      <div class="app-popover hidden mobile-card-actions-popover" data-mobile-card-menu="item-template-${item.id}">
                        <div class="mobile-card-actions-menu">
                          ${itemActions}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="item-catalog-mobile-item-main">
                    <div class="item-catalog-mobile-item-meta">
                      <span class="muted-small">Цена</span>
                      <strong>${core.formatMoney(item.latest_unit_price || 0)}</strong>
                    </div>
                    <div class="item-catalog-mobile-item-meta">
                      <span class="muted-small">Бренд</span>
                      ${brandHtml}
                    </div>
                    <div class="item-catalog-mobile-item-meta">
                      <span class="muted-small">Категория</span>
                      ${categoryHtml}
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          `;
        }
        return `
          <tr class="item-catalog-item-row table-hierarchy-child-row table-record-open-row ${isCollapsed ? "hidden" : ""}" data-item-template-row="1" data-item-template-open-id="${item.id}">
            <td class="item-catalog-select-cell" data-label="Выбор"><input data-item-catalog-select-id="${Number(item.id)}" type="checkbox" ${selected ? "checked" : ""} aria-label="Выбрать ${escapeHtml(item.name || "позицию")}" /></td>
            <td class="item-catalog-source-context-cell" data-label="Источник"><span class="hierarchy-child-label">↳ ${core.highlightText(group.shopName, query)}</span></td>
            <td class="item-catalog-brand-cell" data-label="Бренд">${brandHtml}</td>
            <td data-label="Позиция">${core.highlightText(item.name || "—", query)}</td>
            <td data-label="Категория">${categoryHtml}</td>
            <td data-label="Цена">${core.formatMoney(item.latest_unit_price || 0)}</td>
            <td class="mobile-actions-cell table-kebab-cell" data-label="Действия">
              ${core.renderInlineKebabMenu?.(
                `item-template-${item.id}`,
                itemActions,
                "Действия позиции",
                "item-template-kebab",
              ) || ""}
            </td>
          </tr>
        `;
      }).join("");
      const emptyRow = !group.items.length && !isCollapsed
        ? compactMobile
          ? `<tr class="item-catalog-item-row item-catalog-mobile-item-row"><td colspan="7" class="item-catalog-mobile-item-cell"><div class="item-catalog-mobile-empty muted-small">Позиции в источнике пока не добавлены</div></td></tr>`
          : `<tr class="item-catalog-item-row"><td></td><td data-label="Источник">${core.highlightText(group.shopName, query)}</td><td data-label="Позиция" colspan="5" class="muted-small">Позиции в источнике пока не добавлены</td></tr>`
        : "";
      if (compactMobile) {
        return `
          <tr class="item-catalog-group-row table-hierarchy-parent-row item-catalog-mobile-group-row">
            <td colspan="7" class="item-catalog-group-cell item-catalog-mobile-group-cell">
              <div class="item-catalog-mobile-group-card">
                <div class="item-catalog-mobile-group-head">
                  <button type="button" class="item-catalog-group-btn item-catalog-mobile-group-toggle" data-item-catalog-shop-key="${encodeURIComponent(group.shopKey)}" ${queryActive ? "disabled" : ""}>
                    <span class="item-catalog-group-chevron">${chevron}</span>
                    <span class="item-catalog-group-main">
                      <span class="item-catalog-group-name">${core.highlightText(group.shopName, query)}</span>
                      <span class="item-catalog-group-metas item-catalog-mobile-group-metas">
                        <span class="item-catalog-group-meta">${group.items.length} поз.</span>
                        <span class="item-catalog-group-meta">исп: ${group.useCountTotal}</span>
                        <span class="item-catalog-group-meta">ср: ${group.avgPrice !== null ? core.formatMoney(group.avgPrice, { withCurrency: false }) : "—"}</span>
                        <span class="item-catalog-group-meta">посл: ${group.lastUsedLabel}</span>
                      </span>
                    </span>
                  </button>
                  ${group.shopKey !== "__no_shop__" ? `<div class="mobile-card-kebab-wrap">
                    <button class="btn btn-secondary mobile-card-kebab-trigger" data-mobile-card-menu-trigger="item-source-${escapeHtml(group.shopKey)}" type="button" aria-label="Действия источника">
                      <span aria-hidden="true">⋮</span>
                    </button>
                    <div class="app-popover hidden mobile-card-actions-popover" data-mobile-card-menu="item-source-${escapeHtml(group.shopKey)}">
                      <div class="mobile-card-actions-menu">
                        ${sourceActions}
                      </div>
                    </div>
                  </div>` : ""}
                </div>
              </div>
            </td>
          </tr>
          ${childRows}
          ${emptyRow}
        `;
      }
      return `
        <tr class="item-catalog-group-row table-hierarchy-parent-row">
          <td colspan="7" class="item-catalog-group-cell">
            <div class="category-table-group-wrap item-catalog-source-wrap">
              <div class="category-table-group-content">
                <div class="category-table-group-title">
                  <button type="button" class="item-catalog-group-btn" data-item-catalog-shop-key="${encodeURIComponent(group.shopKey)}" ${queryActive ? "disabled" : ""}>
                    <span class="item-catalog-group-chevron">${chevron}</span>
                    <span class="item-catalog-group-name">${core.highlightText(group.shopName, query)}</span>
                  </button>
                  ${group.shopKey !== "__no_shop__" ? `<button class="btn btn-secondary category-context-create-btn item-source-context-create-btn" data-create-item-template-source-name="${escapeHtml(group.shopName)}" type="button" aria-label="Добавить позицию в источник">+</button>` : ""}
                </div>
                <span class="item-catalog-group-metas">
                  <span class="item-catalog-group-meta">${group.items.length} поз.</span>
                  <span class="item-catalog-group-meta">исп: ${group.useCountTotal}</span>
                  <span class="item-catalog-group-meta">ср: ${group.avgPrice !== null ? core.formatMoney(group.avgPrice, { withCurrency: false }) : "—"}</span>
                  <span class="item-catalog-group-meta">посл: ${group.lastUsedLabel}</span>
                </span>
              </div>
              ${group.shopKey !== "__no_shop__" ? core.renderInlineKebabMenu?.(
                `item-source-${escapeHtml(group.shopKey)}`,
                sourceActions,
                "Действия источника",
                "item-source-kebab",
              ) : ""}
            </div>
          </td>
        </tr>
        ${childRows}
        ${emptyRow}
      `;
    }).join("");
    const rowNodes = el.itemCatalogBody.querySelectorAll('tr.item-catalog-item-row[data-item-template-row="1"]');
    let index = 0;
    for (const group of groups) {
      for (const item of group.items) {
        const row = rowNodes[index];
        if (row) {
          row.dataset.itemTemplate = JSON.stringify(item);
        }
        index += 1;
      }
    }
  }

  const api = {
    buildItemCatalogGroups,
    renderItemCatalog,
  };

  window.App.registerRuntimeModule?.("item-catalog-render-coordinator", api);
})();
