(() => {
  function createOperationModalReceiptPickerFeature(deps) {
    const {
      state,
      el,
      core,
      receiptUiState,
      normalizeReceiptName,
      getReceiptModeFromNode,
      RECEIPT_TEMPLATES_CACHE_TTL_MS,
    } = deps;

    function getPickerUtils() {
      return window.App.getRuntimeModule?.("picker-utils");
    }

    function getCategoryActions() {
      return window.App.getRuntimeModule?.("category-actions") || {};
    }

    const pickerUtils = getPickerUtils();
    const CATEGORY_USAGE_KEY = pickerUtils.DEFAULT_CATEGORY_USAGE_KEY;
    const RECEIPT_ENTITY_TOOLTIP_ID = "receiptEntityPickerTooltip";
    let receiptEntityTooltipTarget = null;
    let receiptEntityTooltipTimer = null;
    let receiptEntityTooltipGlobalBound = false;

    function escHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderReceiptBrandChip(brand) {
      const renderer = window.App.getRuntimeModule?.("item-brands")?.renderBrandChip;
      const normalizedBrand = {
        name: brand?.brand_name || brand?.name || "",
        accent_color: brand?.brand_accent_color || brand?.accent_color || null,
        image_id: brand?.brand_image_id || brand?.image_id || null,
      };
      return typeof renderer === "function"
        ? renderer(normalizedBrand)
        : core.renderCategoryChip({ ...normalizedBrand, icon: null }, "");
    }

    function receiptEntityMonogram(value) {
      const words = normalizeReceiptName(value)
        .split(/\s+/u)
        .filter(Boolean);
      if (!words.length) return "·";
      if (words.length > 1) return `${words[0][0] || ""}${words[1][0] || ""}`.toUpperCase();
      return Array.from(words[0]).slice(0, 2).join("").toUpperCase();
    }

    function receiptEntityHue(value) {
      let hash = 0;
      for (const character of normalizeReceiptName(value).toLowerCase()) {
        hash = ((hash * 31) + character.codePointAt(0)) >>> 0;
      }
      return hash % 360;
    }

    function renderReceiptEntityAvatar(entity, kind) {
      const name = normalizeReceiptName(entity?.name || "") || "Без названия";
      const imageId = entity?.image_id || null;
      const rendered = window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(imageId, {
        kind,
        size: "picker",
        alt: name,
        fallback: receiptEntityMonogram(name),
      });
      if (rendered) return rendered;
      return `
        <span class="catalog-media-thumb catalog-media-${kind} catalog-media-picker is-fallback" role="img" aria-label="${escHtml(name)}">
          <span class="catalog-media-fallback" aria-hidden="true">${escHtml(receiptEntityMonogram(name))}</span>
        </span>
      `;
    }

    function ensureReceiptEntityTooltip() {
      let tooltip = document.getElementById(RECEIPT_ENTITY_TOOLTIP_ID);
      if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.id = RECEIPT_ENTITY_TOOLTIP_ID;
        tooltip.className = "receipt-entity-tooltip";
        tooltip.setAttribute("role", "tooltip");
        tooltip.setAttribute("aria-hidden", "true");
        document.body.appendChild(tooltip);
      }
      return tooltip;
    }

    function positionReceiptEntityTooltip(target, tooltip) {
      if (!target?.isConnected || !tooltip) return;
      const margin = 10;
      const offset = 9;
      const targetRect = target.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
      const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
      const centeredLeft = targetRect.left + ((targetRect.width - tooltipRect.width) / 2);
      const left = Math.max(margin, Math.min(centeredLeft, viewportWidth - tooltipRect.width - margin));
      const fitsAbove = targetRect.top - tooltipRect.height - offset >= margin;
      const preferredTop = fitsAbove
        ? targetRect.top - tooltipRect.height - offset
        : targetRect.bottom + offset;
      const top = Math.max(margin, Math.min(preferredTop, viewportHeight - tooltipRect.height - margin));
      tooltip.style.left = `${Math.round(left)}px`;
      tooltip.style.top = `${Math.round(top)}px`;
      tooltip.dataset.placement = fitsAbove ? "top" : "bottom";
    }

    function hideReceiptEntityTooltip(target = null) {
      if (target && receiptEntityTooltipTarget && target !== receiptEntityTooltipTarget) return;
      if (receiptEntityTooltipTimer) {
        window.clearTimeout(receiptEntityTooltipTimer);
        receiptEntityTooltipTimer = null;
      }
      const tooltip = document.getElementById(RECEIPT_ENTITY_TOOLTIP_ID);
      tooltip?.classList.remove("is-visible");
      tooltip?.setAttribute("aria-hidden", "true");
      receiptEntityTooltipTarget?.removeAttribute("aria-describedby");
      receiptEntityTooltipTarget = null;
    }

    function showReceiptEntityTooltip(target, { immediate = false } = {}) {
      const label = normalizeReceiptName(target?.dataset?.receiptPickerTooltip || "");
      if (!label) return;
      hideReceiptEntityTooltip();
      receiptEntityTooltipTarget = target;
      receiptEntityTooltipTimer = window.setTimeout(() => {
        if (receiptEntityTooltipTarget !== target || !target.isConnected) return;
        const tooltip = ensureReceiptEntityTooltip();
        tooltip.textContent = label;
        tooltip.setAttribute("aria-hidden", "false");
        target.setAttribute("aria-describedby", RECEIPT_ENTITY_TOOLTIP_ID);
        positionReceiptEntityTooltip(target, tooltip);
        window.requestAnimationFrame(() => {
          if (receiptEntityTooltipTarget === target) tooltip.classList.add("is-visible");
        });
        receiptEntityTooltipTimer = null;
      }, immediate ? 0 : 100);
    }

    function bindReceiptEntityTooltip(picker) {
      if (!picker || picker.dataset.receiptEntityTooltipBound === "true") return;
      picker.dataset.receiptEntityTooltipBound = "true";
      if (!receiptEntityTooltipGlobalBound) {
        receiptEntityTooltipGlobalBound = true;
        window.addEventListener("resize", () => hideReceiptEntityTooltip(), { passive: true });
        window.addEventListener("scroll", () => hideReceiptEntityTooltip(), { passive: true, capture: true });
      }
      picker.addEventListener("pointerover", (event) => {
        const target = event.target.closest?.("[data-receipt-picker-tooltip]");
        if (!target || !picker.contains(target) || target.contains(event.relatedTarget)) return;
        showReceiptEntityTooltip(target);
      });
      picker.addEventListener("pointerout", (event) => {
        const target = event.target.closest?.("[data-receipt-picker-tooltip]");
        if (!target || target.contains(event.relatedTarget)) return;
        hideReceiptEntityTooltip(target);
      });
      picker.addEventListener("focusin", (event) => {
        const target = event.target.closest?.("[data-receipt-picker-tooltip]");
        if (target) showReceiptEntityTooltip(target, { immediate: true });
      });
      picker.addEventListener("focusout", (event) => {
        const target = event.target.closest?.("[data-receipt-picker-tooltip]");
        if (!target || target.contains(event.relatedTarget)) return;
        hideReceiptEntityTooltip(target);
      });
      picker.addEventListener("scroll", () => hideReceiptEntityTooltip(), { passive: true });
    }

    function normalizeReceiptProduct(raw = {}) {
      const normalizer = window.App.getRuntimeModule?.("catalog-products")?.normalizeProduct;
      if (typeof normalizer === "function") return normalizer(raw);
      return {
        ...raw,
        id: Number(raw.id || raw.product_id || 0) || null,
        name: normalizeReceiptName(raw.name || raw.product_name || ""),
        image_id: raw.image_id || raw.product_image_id || null,
        brand_id: raw.brand_id ? Number(raw.brand_id) : null,
        brand_name: normalizeReceiptName(raw.brand_name || "") || null,
        brand_accent_color: raw.brand_accent_color || null,
        brand_image_id: raw.brand_image_id || null,
        category_id: raw.category_id || raw.last_category_id || null,
        offers: Array.isArray(raw.offers) ? raw.offers : [],
      };
    }

    function rebuildReceiptProductHints(extraProducts = []) {
      const byId = new Map();
      const upsert = (raw) => {
        const product = normalizeReceiptProduct(raw);
        const productId = Number(product?.id || 0);
        if (!productId) return;
        const previous = byId.get(productId);
        const offerById = new Map();
        for (const offer of [...(previous?.offers || []), ...(product.offers || [])]) {
          const offerId = Number(offer?.template_id || offer?.id || 0);
          // Template hints are shorter than product offers. Keep enriched price
          // and package metadata when the same offer appears in both responses.
          if (offerId) offerById.set(offerId, { ...offerById.get(offerId), ...offer, id: offerId, template_id: offerId });
        }
        byId.set(productId, {
          ...previous,
          ...product,
          id: productId,
          name: normalizeReceiptName(product.name || previous?.name || ""),
          name_ci: normalizeReceiptName(product.name || previous?.name || "").toLowerCase(),
          offers: Array.from(offerById.values()),
        });
      };
      for (const product of state.receiptProductHints || []) upsert(product);
      for (const product of extraProducts || []) upsert(product);
      for (const template of state.receiptTemplateHints || []) {
        const productId = Number(template.product_id || 0);
        if (!productId) continue;
        upsert({
          id: productId,
          name: template.product_name || template.name,
          image_id: template.product_image_id || template.image_id || null,
          brand_id: template.brand_id || null,
          brand_name: template.brand_name || null,
          brand_accent_color: template.brand_accent_color || null,
          brand_image_id: template.brand_image_id || null,
          category_id: template.product_category_id || template.last_category_id || null,
          offers: [template],
        });
      }
      state.receiptProductHints = Array.from(byId.values());
      return state.receiptProductHints;
    }

    function receiptProductOfferForSource(product, shopName = "", sourceId = null) {
      const offers = Array.isArray(product?.offers) ? product.offers : [];
      const selectedSourceId = Number(sourceId || 0);
      if (selectedSourceId) {
        const match = offers.find((offer) => Number(offer.source_id || 0) === selectedSourceId);
        if (match) return match;
      }
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      if (shopCi) {
        const match = offers.find((offer) => normalizeReceiptName(offer.source_name || offer.shop_name || "").toLowerCase() === shopCi);
        if (match) return match;
        return null;
      }
      return selectedSourceId ? null : (offers.length === 1 ? offers[0] : null);
    }

    function receiptProductPresentation(product, shopName = "", sourceId = null) {
      const offer = receiptProductOfferForSource(product, shopName, sourceId);
      return {
        ...offer,
        ...product,
        id: Number(product.id || 0),
        product_id: Number(product.id || 0),
        product_name: product.name,
        product_image_id: product.image_id || null,
        name: product.name,
        name_ci: normalizeReceiptName(product.name).toLowerCase(),
        image_id: product.image_id || offer?.image_id || null,
        selected_offer: offer || null,
        offers: product.offers || [],
        latest_unit_price: offer?.latest_unit_price || null,
      };
    }

    function getReceiptCategoriesSorted(kind, query = "") {
      return pickerUtils.sortCategoriesByUsage(
        (state.categories || []).filter((item) => item.kind === kind),
        query,
        CATEGORY_USAGE_KEY,
      );
    }

    function createReceiptCategoryChipButton(category, selected, searchQuery = "") {
      return pickerUtils.createChipButton({
        datasetName: "receiptCategoryId",
        datasetValue: category.id,
        selected,
        html: core.renderCategoryChip(
          {
            name: category.name,
            icon: category.icon || category.group_icon || null,
            accent_color: category.group_accent_color || null,
          },
          searchQuery,
        ),
      });
    }

    function createReceiptNoCategoryChipButton(selected) {
      return pickerUtils.createMetaChipButton({
        datasetName: "receiptCategoryId",
        datasetValue: "",
        selected,
        label: "Без категории",
        core,
      });
    }

    function getReceiptTemplateMatch(token, shopName = "", brandId = null, sourceId = null) {
      const normalizedToken = normalizeReceiptName(token).toLowerCase();
      if (!normalizedToken) {
        return null;
      }
      const selectedBrandId = brandId ? Number(brandId) : null;
      const matchingProducts = (state.receiptProductHints || []).filter((item) => (
        normalizeReceiptName(item.name).toLowerCase() === normalizedToken
        && (!selectedBrandId || Number(item.brand_id || 0) === selectedBrandId)
      ));
      const hasSourceScope = Boolean(Number(sourceId || 0) || normalizeReceiptName(shopName));
      const product = hasSourceScope
        ? matchingProducts.find((item) => receiptProductOfferForSource(item, shopName, sourceId))
        : matchingProducts[0];
      if (product) return receiptProductPresentation(product, shopName, sourceId);
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      return (state.receiptTemplateHints || []).find((item) => (
        !item.product_id && item.name_ci === normalizedToken
        && (!sourceId || Number(item.source_id || 0) === Number(sourceId))
        && (!shopCi || (item.shop_name_ci || "") === shopCi)
        && (!selectedBrandId || Number(item.brand_id || 0) === selectedBrandId)
      )) || null;
    }

    function getReceiptTemplateSuggestions(query, shopName = "", limit = 50, brandId = null, sourceId = null) {
      const normalized = normalizeReceiptName(query).toLowerCase();
      const selectedBrandId = brandId ? Number(brandId) : null;
      const products = (state.receiptProductHints || [])
        .filter((item) => !selectedBrandId || Number(item.brand_id || 0) === selectedBrandId)
        .map((item, index) => ({ item, index, sourceMatch: Boolean(receiptProductOfferForSource(item, shopName, sourceId)) }))
        .sort((left, right) => Number(right.sourceMatch) - Number(left.sourceMatch) || left.index - right.index)
        .map(({ item }) => receiptProductPresentation(item, shopName, sourceId));
      const legacy = (state.receiptTemplateHints || []).filter((item) => (
        !item.product_id
        && (!selectedBrandId || Number(item.brand_id || 0) === selectedBrandId)
      ));
      const shopCi = normalizeReceiptName(shopName).toLowerCase();
      const scopedTemplates = [...products, ...legacy.filter((item) => !shopCi || (item.shop_name_ci || "") === shopCi)];
      if (!normalized) {
        return limit > 0 ? scopedTemplates.slice(0, limit) : scopedTemplates;
      }
      const matches = scopedTemplates
        .filter((item) => window.App.search.matches(item.name_ci, normalized))
        .sort((a, b) => window.App.search.compare(query, a.name_ci, b.name_ci)
          || Number(window.App.search.normalize(b.name_ci).startsWith(window.App.search.normalize(query)))
          - Number(window.App.search.normalize(a.name_ci).startsWith(window.App.search.normalize(query))));
      return limit > 0 ? matches.slice(0, limit) : matches;
    }

    function getReceiptScanSuggestions(query, shopName = "", limit = 6) {
      const search = window.App.search;
      const candidates = getReceiptTemplateSuggestions("", shopName, 0);
      if (!query.trim()) return candidates.slice(0, limit);
      // Extra receipt words must not dilute a useful keyword match. Numbers,
      // packaging and generic processing terms cannot establish product identity.
      const clean = value => search.normalize(value).replace(/[aceopxykmthb]/g, c => ({a:'а',c:'с',e:'е',o:'о',p:'р',x:'х',y:'у',k:'к',m:'м',t:'т',h:'н',b:'в'})[c]);
      const ignored = new Set(['категория','первый','первая','второй','вторая','высший','сорт','новый','новая','новое','нар','нарезка','сдоб','пак','уп','упаковка','фас','дой','дозатор','дозатором','шт','штука','кг','мл','грамм','литр','варено','вареная','вареный','копченая','копченые','копченый','сырокопченая','полукопченая','охлажденная','охлажденные']);
      const stem = word => word.length < 5 ? word : word.replace(/(?:ами|ями|ого|ему|ая|яя|ое|ые|ие|ий|ый|ой|ов|ев|ы|и|а|я|у|ю|е|о)$/u, '');
      const tokens = value => [...new Set((clean(value).match(/[\p{L}]+/gu)||[]).filter(t=>t.length>=3&&!ignored.has(t)))];
      const measures = value => Array.from(clean(value).matchAll(/(\d+(?:[.,]\d+)?)\s*(кг|мл|г|л)(?=$|[^\p{L}])/gu),m=>{
        const factor=m[2]==='кг'||m[2]==='л'?1000:1;
        return `${m[2]==='кг'||m[2]==='г'?'mass':'volume'}:${Math.round(Number(m[1].replace(',','.'))*factor*1000)/1000}`;
      });
      function similarity(a,b) {
        if(a===b)return 1;
        if(stem(a).length>=4&&stem(a)===stem(b))return .9;
        // One/two OCR substitutions, not arbitrary shared prefixes (батон != батончик).
        const allowed=Math.min(a.length,b.length)>=7?2:1;
        if(Math.min(a.length,b.length)<4||Math.abs(a.length-b.length)>allowed)return 0;
        let row=Array.from({length:b.length+1},(_,i)=>i);
        for(let i=1;i<=a.length;i++){
          const next=[i];for(let j=1;j<=b.length;j++)next[j]=Math.min(next[j-1]+1,row[j]+1,row[j-1]+Number(a[i-1]!==b[j-1]));row=next;
        }
        return row[b.length] <= allowed ? .65 : 0;
      }
      const records=candidates.map((item,index)=>({item,index,aliases:[...new Set([item.name,item.selected_offer?.name,...(item.offers||[]).map(o=>o.name)].filter(Boolean))].map(name=>({name,words:tokens(name),measures:measures(name)}))}));
      const frequency=new Map();
      for(const r of records)for(const word of new Set(r.aliases.flatMap(a=>a.words.map(stem))))frequency.set(word,(frequency.get(word)||0)+1);
      const variants=search.variants(query).map(v=>({raw:v,words:tokens(v)})).filter(v=>v.words.length);
      const queryMeasures=measures(query);
      return records.map(r=>{
        let best={score:0,words:[],exact:false,sizeConflict:false};
        for(const alias of r.aliases)for(const variant of variants){
          const hits=new Map();
          for(const word of variant.words){
            let hit=null;
            for(const other of alias.words){
              const quality=similarity(word,other);
              if(quality&&(!hit||quality>hit.quality))hit={word,other,quality};
            }
            if(hit&&(!hits.has(stem(hit.other))||hits.get(stem(hit.other)).quality<hit.quality))hits.set(stem(hit.other),hit);
          }
          // Keep the ordinary typed substring/layout search alongside keyword matching.
          const direct=search.matches(alias.name,variant.raw);
          if(!hits.size&&!direct)continue;
          const exact=clean(alias.name)===clean(variant.raw);
          let score=exact?10000:0;
          for(const hit of hits.values())score+=hit.quality*(1+Math.log(1+records.length/(frequency.get(stem(hit.other))||1)));
          if(direct)score+=2;
          const sizeConflict=!!(queryMeasures.length&&alias.measures.length&&!queryMeasures.some(m=>alias.measures.includes(m)));
          if(queryMeasures.some(m=>alias.measures.includes(m)))score+=1;
          if(sizeConflict)score-=.5;
          if(score>best.score)best={score,words:[...hits.values()].map(h=>h.word),exact,sizeConflict};
        }
        return {...r,...best};
      }).filter(r=>r.score>0).sort((a,b)=>b.score-a.score||a.index-b.index).slice(0,limit)
        .map(r=>({...r.item,scan_match:{words:r.words,exact:r.exact,sizeConflict:r.sizeConflict}}));
    }

    function getReceiptBrandSuggestions(query = "") {
      const normalized = normalizeReceiptName(query).toLowerCase();
      return (state.itemBrands || [])
        .filter((item) => !item.is_archived)
        .filter((item) => !normalized || window.App.search.matches(item.name, normalized))
        .sort((left, right) => window.App.search.compare(query, left.name, right.name) || normalizeReceiptName(left.name).localeCompare(normalizeReceiptName(right.name), "ru"));
    }

    function getReceiptSourceMeta(shopName) {
      const normalized = normalizeReceiptName(shopName).toLowerCase();
      if (!normalized) return null;
      const source = (state.itemSources || []).find(
        (item) => normalizeReceiptName(item?.name || "").toLowerCase() === normalized,
      );
      if (source) return source;
      const template = (state.receiptTemplateHints || []).find(
        (item) => normalizeReceiptName(item?.source_name || item?.shop_name || "").toLowerCase() === normalized,
      );
      return template ? {
        id: template.source_id || null,
        name: template.source_name || template.shop_name || shopName,
        image_id: template.source_image_id || null,
      } : null;
    }

    function getReceiptShopSuggestions(query = "", limit = 100) {
      const normalized = normalizeReceiptName(query).toLowerCase();
      const byShop = new Map();
      const preferenceSources = state.preferences?.data?.ui?.item_catalog_sources;
      if (!state.itemSourcesLoaded && Array.isArray(preferenceSources)) {
        for (const sourceName of preferenceSources) {
          const shopName = normalizeReceiptName(sourceName || "");
          if (!shopName) {
            continue;
          }
          const shopNameCi = shopName.toLowerCase();
          if (normalized && !window.App.search.matches(shopNameCi, normalized)) {
            continue;
          }
          if (!byShop.has(shopNameCi)) {
            byShop.set(shopNameCi, shopName);
          }
        }
      }
      for (const source of state.itemSources || []) {
        if (source?.is_archived) continue;
        const shopName = normalizeReceiptName(source?.name || "");
        const shopNameCi = shopName.toLowerCase();
        if (!shopName || (normalized && !window.App.search.matches(shopNameCi, normalized))) continue;
        if (!byShop.has(shopNameCi)) byShop.set(shopNameCi, shopName);
      }
      for (const item of state.receiptTemplateHints || []) {
        const shopName = normalizeReceiptName(item.shop_name || "");
        if (!shopName) {
          continue;
        }
        const shopNameCi = shopName.toLowerCase();
        if (normalized && !window.App.search.matches(shopNameCi, normalized)) {
          continue;
        }
        if (!byShop.has(shopNameCi)) {
          byShop.set(shopNameCi, shopName);
        }
      }
      const matches = window.App.search.prioritize(Array.from(byShop.values()), query, (name) => name);
      return limit > 0 ? matches.slice(0, limit) : matches;
    }

    function upsertLocalReceiptTemplate(name, latestUnitPrice = 0, shopName = "", brand = {}) {
      const normalizedName = normalizeReceiptName(name);
      if (!normalizedName) {
        return null;
      }
      const normalizedShop = normalizeReceiptName(shopName);
      const shopNameCi = normalizedShop.toLowerCase();
      const nameCi = normalizedName.toLowerCase();
      const existing = (state.receiptTemplateHints || []).find((item) => (
        item.name_ci === nameCi && (item.shop_name_ci || "") === shopNameCi
      ));
      if (existing) {
        if (Number(latestUnitPrice || 0) > 0) {
          existing.latest_unit_price = Number(latestUnitPrice || 0);
        }
        if (Object.prototype.hasOwnProperty.call(brand, "brand_id")) {
          existing.brand_id = brand.brand_id ? Number(brand.brand_id) : null;
          existing.brand_name = normalizeReceiptName(brand.brand_name || "") || null;
          existing.brand_accent_color = brand.brand_accent_color || null;
          existing.brand_image_id = brand.brand_image_id || null;
          existing.brand_is_archived = Boolean(brand.brand_is_archived);
        }
        return existing;
      }
      receiptUiState.localTemplateSeq += 1;
      const created = {
        id: -receiptUiState.localTemplateSeq,
        shop_name: normalizedShop || null,
        shop_name_ci: shopNameCi || "",
        name: normalizedName,
        name_ci: nameCi,
        brand_id: brand.brand_id ? Number(brand.brand_id) : null,
        brand_name: normalizeReceiptName(brand.brand_name || "") || null,
        brand_accent_color: brand.brand_accent_color || null,
        brand_image_id: brand.brand_image_id || null,
        brand_is_archived: Boolean(brand.brand_is_archived),
        image_id: null,
        source_id: null,
        source_image_id: null,
        last_category_id: null,
        latest_unit_price: Number(latestUnitPrice || 0) || 0,
      };
      state.receiptTemplateHints = [created, ...(state.receiptTemplateHints || [])];
      return created;
    }

    function normalizeServerReceiptTemplate(item) {
      return {
        id: Number(item.id || 0),
        product_id: item.product_id ? Number(item.product_id) : null,
        product_name: normalizeReceiptName(item.product_name || "") || null,
        product_image_id: item.product_image_id || null,
        product_category_id: item.product_category_id ? Number(item.product_category_id) : null,
        shop_name: normalizeReceiptName(item.shop_name || "") || null,
        shop_name_ci: normalizeReceiptName(item.shop_name || "").toLowerCase(),
        name: normalizeReceiptName(item.name || ""),
        name_ci: normalizeReceiptName(item.name || "").toLowerCase(),
        brand_id: item.brand_id ? Number(item.brand_id) : null,
        brand_name: normalizeReceiptName(item.brand_name || "") || null,
        brand_accent_color: item.brand_accent_color || null,
        brand_image_id: item.brand_image_id || null,
        brand_is_archived: Boolean(item.brand_is_archived),
        image_id: item.image_id || null,
        source_id: item.source_id || null,
        source_image_id: item.source_image_id || null,
        last_category_id: item.last_category_id ? Number(item.last_category_id) : null,
        latest_unit_price: Number(item.latest_unit_price || 0) || 0,
      };
    }

    function mergeReceiptTemplateHints(items = []) {
      const byKey = new Map();
      for (const item of state.receiptTemplateHints || []) {
        if (item?.name_ci) {
          byKey.set(`${item.name_ci}::${item.shop_name_ci || ""}`, item);
        }
      }
      for (const raw of items) {
        const item = raw?.name_ci ? raw : normalizeServerReceiptTemplate(raw);
        if (item?.name_ci) {
          byKey.set(`${item.name_ci}::${item.shop_name_ci || ""}`, item);
        }
      }
      state.receiptTemplateHints = Array.from(byKey.values());
      rebuildReceiptProductHints();
      return state.receiptTemplateHints;
    }

    function hideAllReceiptPickers() {
      hideReceiptEntityTooltip();
      for (const listNode of [el.receiptItemsList, el.editReceiptItemsList]) {
        if (!listNode) {
          continue;
        }
        listNode.querySelectorAll(".receipt-item-row").forEach((node) => node.classList.remove("has-open-popover"));
        listNode.querySelectorAll(".receipt-shop-cell, .receipt-brand-cell, .receipt-name-cell, .receipt-category-cell").forEach((node) => node.classList.remove("has-open-popover"));
        listNode.querySelectorAll(".receipt-shop-picker, .receipt-brand-picker, .receipt-name-picker, .receipt-category-picker").forEach((node) => {
          pickerUtils.setPopoverOpen(node, false);
        });
      }
      receiptUiState.activePicker = null;
    }

    function renderReceiptShopPickerForRow(rowNode, rowItem, query) {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-shop-picker");
      if (!picker) {
        return;
      }
      hideAllReceiptPickers();
      const normalizedQuery = normalizeReceiptName(query);
      const shopSuggestions = getReceiptShopSuggestions(normalizedQuery);
      const exact = shopSuggestions.some((shop) => shop.toLowerCase() === normalizedQuery.toLowerCase());
      if (!normalizedQuery && !shopSuggestions.length) {
        picker.classList.add("hidden");
        picker.innerHTML = "";
        return;
      }
      const suggestionsHtml = shopSuggestions.map((shopName) => {
        const source = getReceiptSourceMeta(shopName) || { name: shopName, image_id: null };
        const selected = (
          (Number(rowItem.source_id || 0) && Number(source.id || 0) === Number(rowItem.source_id))
          || normalizeReceiptName(rowItem.shop_name || "").toLowerCase() === shopName.toLowerCase()
        );
        return `
        <button type="button" class="chip-btn receipt-entity-option ${selected ? "active" : ""}" data-receipt-shop-name="${escHtml(shopName)}" data-receipt-item-id="${rowItem.draft_id}" data-receipt-picker-tooltip="${escHtml(shopName)}" aria-label="${escHtml(shopName)}" aria-pressed="${selected ? "true" : "false"}" style="--receipt-entity-hue:${receiptEntityHue(shopName)}">
          ${renderReceiptEntityAvatar({ ...source, name: shopName }, "source")}
          <span class="receipt-entity-option-label">${escHtml(shopName)}</span>
          <span class="receipt-entity-option-check" aria-hidden="true">✓</span>
        </button>
      `;
      }).join("");
      const createHtml = !normalizedQuery || exact ? "" : `
        <button type="button" class="chip-btn chip-btn-create" data-receipt-create-shop="${escHtml(normalizedQuery)}" data-receipt-item-id="${rowItem.draft_id}">
          + Создать источник «${escHtml(normalizedQuery)}»
        </button>
      `;
      picker.innerHTML = `${suggestionsHtml}${createHtml}` || "<span class='muted-small'>Нет источников</span>";
      pickerUtils.pinCreateActions(picker);
      bindReceiptEntityTooltip(picker);
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-shop-cell")],
        outsideScopes: [rowNode.querySelector(".receipt-shop-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "shop_name", mode: getReceiptModeFromNode(rowNode) };
    }

    function renderReceiptBrandPickerForRow(rowNode, rowItem, query = "") {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-brand-picker");
      if (!picker) {
        return;
      }
      hideAllReceiptPickers();
      const rawQuery = normalizeReceiptName(query);
      const normalizedQuery = rawQuery.toLowerCase() === normalizeReceiptName(rowItem.brand_name || "").toLowerCase()
        ? ""
        : rawQuery;
      const suggestions = getReceiptBrandSuggestions(normalizedQuery);
      const clearHtml = `
        <button type="button" class="chip-btn receipt-entity-service-option ${rowItem.brand_id ? "" : "active"}" data-receipt-brand-clear="true" data-receipt-item-id="${rowItem.draft_id}">
          <span aria-hidden="true">∅</span> Без бренда
        </button>
      `;
      const suggestionsHtml = suggestions.map((brand) => {
        const selected = Number(rowItem.brand_id || 0) === Number(brand.id);
        return `
        <button type="button" class="chip-btn receipt-entity-option ${selected ? "active" : ""}" data-receipt-brand-id="${Number(brand.id)}" data-receipt-item-id="${rowItem.draft_id}" data-receipt-picker-tooltip="${escHtml(brand.name)}" aria-label="${escHtml(brand.name)}" aria-pressed="${selected ? "true" : "false"}" style="--receipt-entity-hue:${receiptEntityHue(brand.name)}">
          ${renderReceiptEntityAvatar(brand, "brand")}
          <span class="receipt-entity-option-label">${escHtml(brand.name)}</span>
          <span class="receipt-entity-option-check" aria-hidden="true">✓</span>
        </button>
      `;
      }).join("");
      const emptyHtml = suggestions.length
        ? ""
        : "<span class='muted-small receipt-picker-empty'>Бренд не найден · создать можно в Каталоге → Бренды</span>";
      picker.innerHTML = `${clearHtml}${suggestionsHtml}${emptyHtml}`;
      bindReceiptEntityTooltip(picker);
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-brand-cell")],
        outsideScopes: [rowNode.querySelector(".receipt-brand-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "brand_id", mode: getReceiptModeFromNode(rowNode) };
      if (!(state.itemBrands || []).length) {
        loadReceiptBrands()
          .then(() => {
            const active = receiptUiState.activePicker;
            if (
              active?.field === "brand_id"
              && Number(active.draft_id) === Number(rowItem.draft_id)
              && !picker.classList.contains("hidden")
            ) {
              renderReceiptBrandPickerForRow(rowNode, rowItem, query);
            }
          })
          .catch(() => {});
      }
    }

    function receiptProductSourcesLabel(item) {
      const sources = new Map();
      const offers = item.product_id ? (item.offers || []) : [item];
      for (const offer of offers) {
        const name = normalizeReceiptName(offer.source_name || offer.shop_name || "");
        if (!name) continue;
        const key = offer.source_id ? `id:${offer.source_id}` : `name:${name.toLowerCase()}`;
        if (!sources.has(key)) sources.set(key, name);
      }
      const names = Array.from(sources.values());
      return names.length ? names.join(" · ") : "Источник не указан";
    }

    // Shared product options for manual receipt entry and OCR review.
    // Callers own draft selection; rendering never imports catalog prices or writes data.
    function renderReceiptProductOptions(picker, {suggestions, query = "", draftId = "", allowCreate = false, showPrices = true, emptyText = "Нет совпадений"}) {
      const suggestionsHtml = suggestions.map((item) => `
        <button type="button" class="chip-btn receipt-template-suggestion" ${item.product_id ? `data-receipt-product-id="${item.product_id}"` : `data-receipt-template-id="${item.id}"`} data-receipt-item-id="${draftId}" title="${escHtml(item.name)}">
          ${window.App.getRuntimeModule?.("catalog-media")?.renderThumb?.(item.product_image_id || item.image_id, { kind: "item", size: "picker", alt: item.name, fallback: String(item.name || "П").slice(0, 1) }) || ""}
          <span class="receipt-template-suggestion-main">
            <span class="receipt-template-suggestion-name">${core.highlightText?.(item.name, query) || escHtml(item.name)}</span>
            <span class="receipt-template-suggestion-meta">
              ${item.brand_name ? `<span class="receipt-template-suggestion-brand">${renderReceiptBrandChip(item)}</span>` : ""}
              ${showPrices && Number(item.latest_unit_price || 0) > 0 ? `<span>${core.formatMoney(item.latest_unit_price)}</span>` : ""}
              <span class="receipt-template-suggestion-sources">${escHtml(receiptProductSourcesLabel(item))}</span>
              ${item.scan_match?.sizeConflict ? "<span>Другая фасовка</span>" : ""}
            </span>
          </span>
        </button>
      `).join("");
      const createHtml = !query || !allowCreate ? "" : `
        <button type="button" class="chip-btn chip-btn-create" data-receipt-create-name="${escHtml(query)}" data-receipt-item-id="${draftId}" title="Создать позицию «${escHtml(query)}»">
          <span class="receipt-product-create-label">+ Создать позицию «${escHtml(query)}»</span>
        </button>
      `;
      picker.classList.add("receipt-product-picker");
      picker.innerHTML = `<div class="receipt-product-options">${suggestionsHtml || (!createHtml ? `<span class="muted-small receipt-picker-empty">${escHtml(emptyText)}</span>` : "")}</div>${createHtml ? `<div class="receipt-product-create-footer">${createHtml}</div>` : ""}`;
    }

    function renderReceiptNamePickerForRow(rowNode, rowItem, query) {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-name-picker");
      const badge = rowNode.querySelector(".receipt-new-badge");
      if (!picker) {
        return;
      }
      hideAllReceiptPickers();
      const normalizedQuery = normalizeReceiptName(query);
      const exact = getReceiptTemplateMatch(normalizedQuery, rowItem.shop_name || "", rowItem.brand_id, rowItem.source_id);
      const suggestions = getReceiptTemplateSuggestions(normalizedQuery, rowItem.shop_name || "", 50, rowItem.brand_id, rowItem.source_id);
      if (!normalizedQuery) {
        if (badge) {
          badge.classList.add("hidden");
        }
        if (!suggestions.length) {
          picker.classList.add("hidden");
          picker.innerHTML = "";
          return;
        }
      }
      if (badge) {
        badge.classList.toggle("hidden", Boolean(exact));
      }
      renderReceiptProductOptions(picker, {suggestions, query: normalizedQuery, draftId: rowItem.draft_id, allowCreate: !exact});
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-name-cell")],
        outsideScopes: [rowNode.querySelector(".receipt-name-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "name", mode: getReceiptModeFromNode(rowNode) };
      if (normalizedQuery && !exact && suggestions.length < 50) {
        Promise.all([loadReceiptTemplates(normalizedQuery), loadReceiptProducts(normalizedQuery).catch(() => [])])
          .then(([items, products]) => {
            const prevCount = Array.isArray(state.receiptTemplateHints) ? state.receiptTemplateHints.length : 0;
            const prevProductCount = Array.isArray(state.receiptProductHints) ? state.receiptProductHints.length : 0;
            mergeReceiptTemplateHints(items);
            rebuildReceiptProductHints(products);
            const active = receiptUiState.activePicker;
            if (
              active?.field === "name"
              && Number(active.draft_id) === Number(rowItem.draft_id)
              && !picker.classList.contains("hidden")
              && (state.receiptTemplateHints.length !== prevCount || state.receiptProductHints.length !== prevProductCount)
            ) {
              renderReceiptNamePickerForRow(rowNode, rowItem, query);
            }
          })
          .catch(() => {});
      }
    }

    function openCreateCategoryFromReceipt(rowNode, rowItem, query) {
      const trimmed = String(query || "").trim();
      if (!trimmed) {
        return;
      }
      const mode = getReceiptModeFromNode(rowNode);
      const kind = mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense");
      state.pendingCreateCategoryFromReceipt = {
        draft_id: Number(rowItem.draft_id),
        mode,
        kind,
        query: trimmed,
      };
      hideAllReceiptPickers();
      if (getCategoryActions().openCreateCategoryModal) {
        getCategoryActions().openCreateCategoryModal({
          kind,
          prefillName: trimmed,
          reset: true,
        });
      }
    }

    function renderReceiptCategoryPickerForRow(rowNode, rowItem, query) {
      if (!rowNode || !rowItem) {
        return;
      }
      const picker = rowNode.querySelector(".receipt-category-picker");
      const input = rowNode.querySelector('[data-receipt-field="category_search"]');
      if (!picker || !input) {
        return;
      }
      hideAllReceiptPickers();
      const mode = getReceiptModeFromNode(rowNode);
      const kind = mode === "edit" ? (el.editKind?.value || "expense") : (el.opKind?.value || "expense");
      const selectedId = rowItem.category_id ? Number(rowItem.category_id) : null;
      const effectiveCategoryId = Number(input.dataset.receiptEffectiveCategoryId || 0) || null;
      const displayedCategory = (state.categories || []).find((item) => (
        Number(item.id) === Number(selectedId || effectiveCategoryId || 0) && item.kind === kind
      ));
      const rawQuery = String(query ?? input.value ?? "").trim();
      const normalizedQuery = displayedCategory && rawQuery.toLowerCase() === displayedCategory.name.toLowerCase() ? "" : rawQuery;
      const categories = getReceiptCategoriesSorted(kind, normalizedQuery);
      picker.innerHTML = "";
      picker.appendChild(createReceiptNoCategoryChipButton(!selectedId && !effectiveCategoryId));
      for (const item of categories) {
        const isActive = selectedId
          ? selectedId === Number(item.id)
          : effectiveCategoryId === Number(item.id);
        picker.appendChild(createReceiptCategoryChipButton(item, isActive, normalizedQuery));
      }
      if (normalizedQuery && !categories.some(item => item.name.toLowerCase() === normalizedQuery.toLowerCase())) {
        const createChip = pickerUtils.createActionChipButton({
          datasetName: "receiptCreateCategory",
          datasetValue: normalizedQuery,
          label: `+ Создать категорию «${normalizedQuery}»`,
        });
        createChip.dataset.receiptItemId = String(rowItem.draft_id);
        picker.appendChild(createChip);
      }
      if (!categories.length && !normalizedQuery) {
        const empty = document.createElement("span");
        empty.className = "muted-small";
        empty.textContent = "Без категорий для выбранного типа";
        picker.appendChild(empty);
      }
      pickerUtils.pinCreateActions(picker);
      pickerUtils.setPopoverOpen(picker, true, {
        owners: [rowNode, rowNode.querySelector(".receipt-category-cell")],
        outsideScopes: [rowNode.querySelector(".receipt-category-cell")],
        onClose: hideAllReceiptPickers,
      });
      receiptUiState.activePicker = { draft_id: Number(rowItem.draft_id), field: "category_id", mode };
    }

    async function loadReceiptTemplates(query = "", options = {}) {
      const normalized = String(query || "").trim().toLowerCase();
      const allPages = options.allPages === true && !normalized;
      const cacheKey = `op:receipt:templates:q=${normalized}:all=${allPages ? "1" : "0"}`;
      const cached = core.getUiRequestCache ? core.getUiRequestCache(cacheKey, RECEIPT_TEMPLATES_CACHE_TTL_MS) : null;
      if (cached) {
        return cached.items || [];
      }
      const params = new URLSearchParams({
        page: "1",
        page_size: "100",
      });
      if (normalized) {
        params.set("q", normalized);
      }
      const payload = await core.requestJson(`/api/v1/operations/item-templates?${params.toString()}`, {
        headers: core.authHeaders(),
      });
      const items = Array.isArray(payload.items) ? payload.items.slice() : [];
      const total = Number(payload.total || items.length || 0);
      if (allPages && total > items.length) {
        const pageSize = Number(payload.page_size || 100) || 100;
        const pageCount = Math.ceil(total / pageSize);
        for (let page = 2; page <= pageCount; page += 1) {
          const pageParams = new URLSearchParams(params);
          pageParams.set("page", String(page));
          const pagePayload = await core.requestJson(`/api/v1/operations/item-templates?${pageParams.toString()}`, {
            headers: core.authHeaders(),
          });
          items.push(...(Array.isArray(pagePayload.items) ? pagePayload.items : []));
        }
      }
      const result = { ...payload, items };
      if (core.setUiRequestCache) {
        core.setUiRequestCache(cacheKey, result);
      }
      return items;
    }

    async function loadReceiptProducts(query = "", options = {}) {
      const normalized = String(query || "").trim().toLowerCase();
      const allPages = options.allPages === true && !normalized;
      const cacheKey = `op:receipt:products:q=${normalized}:all=${allPages ? "1" : "0"}`;
      const cached = core.getUiRequestCache?.(cacheKey, RECEIPT_TEMPLATES_CACHE_TTL_MS);
      if (cached) return cached.items || [];
      const params = new URLSearchParams({ page: "1", page_size: "100" });
      if (normalized) params.set("q", normalized);
      const payload = await core.requestJson(`/api/v1/operations/catalog-products?${params.toString()}`, { headers: core.authHeaders() });
      const items = (Array.isArray(payload) ? payload : (payload.items || [])).slice();
      const total = Number(payload?.total || items.length);
      const pageSize = Number(payload?.page_size || 100) || 100;
      if (allPages && total > items.length) {
        for (let page = 2; page <= Math.ceil(total / pageSize); page += 1) {
          const next = new URLSearchParams(params);
          next.set("page", String(page));
          const part = await core.requestJson(`/api/v1/operations/catalog-products?${next.toString()}`, { headers: core.authHeaders() });
          items.push(...(Array.isArray(part) ? part : (part.items || [])));
        }
      }
      core.setUiRequestCache?.(cacheKey, { ...payload, items });
      return items;
    }

    async function loadReceiptBrands(options = {}) {
      const force = options.force === true;
      const now = Date.now();
      const brandsFresh = now - Number(receiptUiState.brandsLoadedAt || 0) < RECEIPT_TEMPLATES_CACHE_TTL_MS;
      if (!force && brandsFresh && state.itemBrandsLoaded && Array.isArray(state.itemBrands)) {
        return state.itemBrands;
      }
      if (receiptUiState.brandsPromise) {
        return receiptUiState.brandsPromise;
      }
      receiptUiState.brandsPromise = (async () => {
        const itemBrands = window.App.getRuntimeModule?.("item-brands");
        const itemCatalog = window.App.getRuntimeModule?.("item-catalog");
        const runtimeLoader = itemBrands?.ensureItemBrandsLoaded
          || itemBrands?.ensureItemBrands
          || itemBrands?.loadItemBrands
          || itemCatalog?.loadItemBrands;
        if (typeof runtimeLoader === "function") {
          try {
            await runtimeLoader({ force });
          } catch {
            // Fall through to the lightweight receipt loader.
          }
        }
        if ((!Array.isArray(state.itemBrands) || (!state.itemBrands.length && !state.itemBrandsLoaded)) || force) {
          const params = new URLSearchParams({ page: "1", page_size: "100", include_archived: "false" });
          const firstPayload = await core.requestJson(`/api/v1/operations/item-brands?${params.toString()}`, {
            headers: core.authHeaders(),
          });
          const brands = (Array.isArray(firstPayload) ? firstPayload : (firstPayload.items || [])).slice();
          const total = Number(firstPayload?.total || brands.length || 0);
          const pageSize = Number(firstPayload?.page_size || 100) || 100;
          const pageCount = Math.ceil(total / pageSize);
          for (let page = 2; page <= pageCount; page += 1) {
            const pageParams = new URLSearchParams(params);
            pageParams.set("page", String(page));
            const payload = await core.requestJson(`/api/v1/operations/item-brands?${pageParams.toString()}`, {
              headers: core.authHeaders(),
            });
            brands.push(...(Array.isArray(payload) ? payload : (payload.items || [])));
          }
          state.itemBrands = brands.filter((item) => !item.is_archived);
          state.itemBrandsLoaded = true;
        }
        receiptUiState.brandsLoadedAt = Date.now();
        return state.itemBrands || [];
      })();
      try {
        return await receiptUiState.brandsPromise;
      } finally {
        receiptUiState.brandsPromise = null;
      }
    }

    async function loadReceiptTemplateHints() {
      const now = Date.now();
      const hintsFresh = now - Number(receiptUiState.hintsLoadedAt || 0) < RECEIPT_TEMPLATES_CACHE_TTL_MS;
      if (hintsFresh && !receiptUiState.hintsLoadFailed && Array.isArray(state.receiptTemplateHints) && state.receiptTemplateHints.length > 0) {
        return;
      }
      if (receiptUiState.hintsPromise) {
        await receiptUiState.hintsPromise;
        return;
      }
      receiptUiState.hintsPromise = (async () => {
        let templates = [];
        let products = [];
        receiptUiState.hintsLoadFailed = false;
        await Promise.all([
          loadReceiptTemplates("", { allPages: true }).then((items) => { templates = items; }).catch(() => { receiptUiState.hintsLoadFailed = true; }),
          loadReceiptProducts("", { allPages: true }).then((items) => { products = items; }).catch(() => { receiptUiState.hintsLoadFailed = true; }),
          loadReceiptBrands().catch(() => {}),
          Promise.resolve(window.App.getRuntimeModule?.("item-catalog")?.loadItemSources?.()).catch(() => {}),
        ]);
        mergeReceiptTemplateHints(templates);
        rebuildReceiptProductHints(products);
        receiptUiState.hintsLoadedAt = Date.now();
      })();
      try {
        await receiptUiState.hintsPromise;
      } finally {
        receiptUiState.hintsPromise = null;
      }
    }

    return {
      getReceiptCategoriesSorted,
      getReceiptTemplateMatch,
      getReceiptTemplateSuggestions,
      getReceiptScanSuggestions,
      renderReceiptProductOptions,
      getReceiptCatalogStatus: () => ({loading: Boolean(receiptUiState.hintsPromise), incomplete: Boolean(receiptUiState.hintsLoadFailed)}),
      getReceiptBrandSuggestions,
      getReceiptShopSuggestions,
      upsertLocalReceiptTemplate,
      mergeReceiptTemplateHints,
      rebuildReceiptProductHints,
      receiptProductOfferForSource,
      loadReceiptProducts,
      hideAllReceiptPickers,
      renderReceiptShopPickerForRow,
      renderReceiptBrandPickerForRow,
      renderReceiptNamePickerForRow,
      openCreateCategoryFromReceipt,
      renderReceiptCategoryPickerForRow,
      loadReceiptTemplateHints,
      loadReceiptBrands,
    };
  }

  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-receipt-picker-factory", createOperationModalReceiptPickerFeature);
})();
