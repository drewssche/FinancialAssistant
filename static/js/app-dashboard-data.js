(() => {
  const { core } = window.App;
  const SUMMARY_CACHE_TTL_MS = 20000;
  const DEBT_PREVIEW_CACHE_TTL_MS = 20000;

  function buildSummaryCacheKey(params) {
    return `dashboard:summary:${params.toString()}`;
  }

  async function loadSummary(params, options = {}) {
    const force = options.force === true;
    const cacheKey = buildSummaryCacheKey(params);
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, SUMMARY_CACHE_TTL_MS);
      if (cached) {
        return cached;
      }
    }
    const data = await core.requestJson(`/api/v1/dashboard/summary?${params.toString()}`, {
      headers: core.authHeaders(),
    });
    core.setUiRequestCache(cacheKey, data);
    return data;
  }

  async function loadAllTimeSummary(options = {}) {
    const params = new URLSearchParams({ period: "all_time" });
    return loadSummary(params, options);
  }

  async function loadDebtPreview(options = {}) {
    const force = options.force === true;
    const limit = Number(options.limit || 6);
    const cacheKey = `dashboard:debts:preview:${limit}`;
    if (!force) {
      const cached = core.getUiRequestCache(cacheKey, DEBT_PREVIEW_CACHE_TTL_MS);
      if (cached) {
        return cached;
      }
    }
    let data;
    try {
      data = await core.requestJson(`/api/v1/dashboard/debts/preview?limit=${limit}`, {
        headers: core.authHeaders(),
      });
    } catch (err) {
      const message = core.errorMessage ? core.errorMessage(err) : String(err);
      if (!String(message).includes("[404]")) {
        throw err;
      }
      const legacyCards = await core.requestJson("/api/v1/debts/cards?include_closed=false", {
        headers: core.authHeaders(),
      });
      data = Array.isArray(legacyCards) ? legacyCards.slice(0, limit) : [];
    }
    core.setUiRequestCache(cacheKey, data);
    return data;
  }

  function invalidateSummaryCache() {
    core.invalidateUiRequestCache("dashboard:summary");
  }

  function invalidateDebtPreviewCache() {
    core.invalidateUiRequestCache("dashboard:debts:preview");
  }

  function invalidateReadCaches(options = {}) {
    invalidateSummaryCache();
    if (options.includeDebtPreview !== false) {
      invalidateDebtPreviewCache();
    }
  }

  window.App.dashboardData = {
    loadSummary,
    loadAllTimeSummary,
    loadDebtPreview,
    invalidateSummaryCache,
    invalidateDebtPreviewCache,
    invalidateReadCaches,
  };
})();
