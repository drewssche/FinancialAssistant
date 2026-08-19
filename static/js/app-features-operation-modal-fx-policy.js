(() => {
  const BANKS = [
    { code: "priorbank", name: "Приорбанк", channel: "online", channelLabel: "онлайн" },
    { code: "technobank", name: "Технобанк", channel: "cash", channelLabel: "наличные" },
    { code: "bsb", name: "БСБ Банк", channel: "cash", channelLabel: "наличные" },
    { code: "sber", name: "Сбер Банк", channel: "cash", channelLabel: "наличные" },
  ];
  const PAYMENT_MODE_HINTS = {
    valuation: "Только BYN-эквивалент. Валютный остаток не изменится.",
    direct_conversion: "Одна расходная операция: BYN конвертируются в валюту и сразу идут на оплату — без двойного расхода.",
    foreign_balance: "Оплата из уже пополненного валютного остатка. Сервис проверит и спишет доступную валюту.",
  };
  const PAYMENT_MODE_LABELS = {
    valuation: "только пересчёт",
    direct_conversion: "пополнить и оплатить",
    foreign_balance: "с валютного остатка",
  };

  function formatFxPolicyProvenance(item = {}) {
    const currency = String(item.currency || "BYN").toUpperCase();
    const baseCurrency = String(item.base_currency || "BYN").toUpperCase();
    if (!currency || currency === baseCurrency) {
      return "";
    }
    const source = String(item.fx_rate_source || "").toLowerCase();
    const scale = Number(item.fx_rate_scale || item.current_rate_scale || (currency === "RUB" ? 100 : 1)) || 1;
    const unitRate = Number(item.fx_rate || item.current_rate || 0);
    const displayRate = Number(item.fx_rate_display || item.current_rate_display || (unitRate * scale));
    const rateText = displayRate > 0
      ? `курс ${displayRate.toLocaleString("ru-RU", { minimumFractionDigits: 4, maximumFractionDigits: 6 })} за ${scale} ${currency}`
      : "";
    let sourceText = "";
    if (source === "bank") {
      const side = item.fx_rate_kind === "buy" ? "покупка банком" : "продажа банком";
      const channel = ({ cash: "наличные", online: "онлайн" }[item.fx_bank_channel] || item.fx_bank_channel || "");
      const quotedAt = item.fx_quoted_at || item.current_rate_quoted_at || item.fx_fetched_at || item.current_rate_fetched_at;
      const quotedDate = quotedAt ? new Date(quotedAt) : null;
      const freshness = quotedDate && !Number.isNaN(quotedDate.getTime())
        ? `обновл. ${new Intl.DateTimeFormat("ru-RU", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }).format(quotedDate)}`
        : "";
      const stale = item.fx_rate_stale === true || item.current_rate_stale === true ? "котировка устарела" : "";
      sourceText = [item.fx_bank_name || item.fx_bank_code || "Банк", side, channel, freshness, stale].filter(Boolean).join(" · ");
    } else if (source === "nbrb") {
      const rateDate = item.fx_rate_date || item.current_rate_date;
      const formattedDate = rateDate
        ? new Intl.DateTimeFormat("ru-RU").format(new Date(`${String(rateDate).slice(0, 10)}T00:00:00`))
        : "";
      sourceText = ["НБРБ", formattedDate].filter(Boolean).join(" · ");
    } else if (source === "manual" || !source) {
      sourceText = source ? "Ручной курс" : "Сохранённый курс";
    }
    const mode = PAYMENT_MODE_LABELS[item.fx_payment_mode] || "";
    return [sourceText, mode, rateText].filter(Boolean).join(" · ");
  }

  function createOperationModalFxPolicyFeature(deps) {
    const {
      state,
      el,
      core,
      formatTradeRateValue,
      renderReceiptSummary,
      updateCreatePreview,
      updateEditPreview,
      syncCreateFxSettlementFieldUi,
      syncEditFxSettlementFieldUi,
    } = deps;
    const uiState = {
      create: freshState(),
      edit: freshState(),
    };

    function freshState() {
      return {
        currency: "",
        options: null,
        pending: null,
        requestSeq: 0,
        preserveSnapshot: false,
        policyDirty: false,
        refreshRequested: false,
        snapshot: null,
        hydratedEntityId: null,
        lastKind: "",
      };
    }

    function nodes(mode = "create") {
      const edit = mode === "edit";
      return {
        field: edit ? el.editFxRateField : el.opFxRateField,
        rate: edit ? el.editFxRate : el.opFxRate,
        hint: edit ? el.editFxRateHint : el.opFxRateHint,
        refresh: edit ? el.editFxRateRefreshBtn : el.opFxRateRefreshBtn,
        sourceSwitch: edit ? el.editFxRateSourceSwitch : el.opFxRateSourceSwitch,
        source: edit ? el.editFxRateSource : el.opFxRateSource,
        bankFields: edit ? el.editFxBankFields : el.opFxBankFields,
        bankOptions: edit ? el.editFxBankOptions : el.opFxBankOptions,
        bankCode: edit ? el.editFxBankCode : el.opFxBankCode,
        rateKindSwitch: edit ? el.editFxRateKindSwitch : el.opFxRateKindSwitch,
        rateKind: edit ? el.editFxRateKind : el.opFxRateKind,
        paymentSwitch: edit ? el.editFxPaymentModeSwitch : el.opFxPaymentModeSwitch,
        paymentMode: edit ? el.editFxPaymentMode : el.opFxPaymentMode,
        paymentHint: edit ? el.editFxPaymentModeHint : el.opFxPaymentModeHint,
        rateLabel: edit ? el.editFxRateLabel : el.opFxRateLabel,
        rateMeta: edit ? el.editFxRateMeta : el.opFxRateMeta,
        computed: edit ? el.editFxComputedAmount : el.opFxComputedAmount,
        currency: edit ? el.editCurrency : el.opCurrency,
        amount: document.getElementById(edit ? "editAmount" : "opAmount"),
        date: document.getElementById(edit ? "editDate" : "opDate"),
        kind: edit ? el.editKind : el.opKind,
      };
    }

    function normalizeSource(value) {
      return ["nbrb", "bank", "manual"].includes(String(value || "")) ? String(value) : "nbrb";
    }

    function normalizeRateKind(value, kind = "expense") {
      if (value === "buy" || value === "sell") {
        return value;
      }
      return kind === "income" ? "buy" : "sell";
    }

    function normalizePaymentMode(value) {
      return ["valuation", "direct_conversion", "foreign_balance"].includes(String(value || ""))
        ? String(value)
        : "valuation";
    }

    function displayScale(currency, options = null, snapshot = null) {
      const explicit = Number(snapshot?.fx_rate_scale || snapshot?.current_rate_scale || options?.display_scale || 0);
      if (Number.isFinite(explicit) && explicit > 0) {
        return explicit;
      }
      return String(currency || "").toUpperCase() === "RUB" ? 100 : 1;
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatDateTime(value) {
      if (!value) {
        return "";
      }
      const dt = new Date(value);
      if (Number.isNaN(dt.getTime())) {
        return "";
      }
      return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(dt);
    }

    function getContext(mode = "create") {
      const n = nodes(mode);
      const baseCurrency = String(core.getCurrencyConfig?.().code || "BYN").toUpperCase();
      const currency = String(n.currency?.value || baseCurrency).toUpperCase();
      const scale = displayScale(currency, uiState[mode].options, uiState[mode].snapshot);
      const displayRate = core.resolveRateInput(n.rate?.value || "", currency === baseCurrency ? 1 : 0, 6);
      const perUnitValue = Number(displayRate.previewValue || 0) / scale;
      return {
        mode,
        isEdit: mode === "edit",
        isPlanFlow: mode === "create" && state.createFlowMode === "plan",
        baseCurrency,
        currency,
        scale,
        displayRate: Number(displayRate.previewValue || 1),
        displayRateState: displayRate,
        fxRate: perUnitValue,
        hasForeignCurrency: currency !== baseCurrency,
        operationDate: core.parseDateInputValue(n.date?.value || "") || "",
        source: normalizeSource(n.source?.value),
        bankCode: String(n.bankCode?.value || "technobank").trim().toLowerCase(),
        rateKind: normalizeRateKind(n.rateKind?.value, n.kind?.value || "expense"),
        paymentMode: normalizePaymentMode(n.paymentMode?.value),
      };
    }

    function setHint(mode, message = "", tone = "neutral") {
      const node = nodes(mode).hint;
      if (!node) {
        return;
      }
      node.textContent = message;
      node.classList.toggle("hidden", !message);
      node.dataset.tone = tone;
    }

    function syncControl(node, dataName, value) {
      if (node) {
        core.syncSegmentedActive(node, dataName, value);
      }
    }

    function selectedBankQuote(mode) {
      const context = getContext(mode);
      const rows = Array.isArray(uiState[mode].options?.bank_rates) ? uiState[mode].options.bank_rates : [];
      return rows.find((row) => String(row.bank_code || "").toLowerCase() === context.bankCode) || null;
    }

    function bankDescriptors(mode) {
      const n = nodes(mode);
      const options = uiState[mode].options || {};
      const providers = Array.isArray(options.providers) ? options.providers : [];
      const quotes = Array.isArray(options.bank_rates) ? options.bank_rates : [];
      const saved = uiState[mode].snapshot || {};
      const savedCode = String(saved.fx_bank_code || "").toLowerCase();
      const merged = BANKS.map((bank) => ({ ...bank }));
      for (const provider of providers) {
        const code = String(provider.bank_code || "").toLowerCase();
        const existing = merged.find((item) => item.code === code);
        const descriptor = {
          code,
          name: provider.bank_name || code,
          channel: provider.channel || "",
          channelLabel: provider.channel_label || provider.channel || "",
        };
        if (existing) {
          Object.assign(existing, descriptor);
        } else if (code) {
          merged.push(descriptor);
        }
      }
      if (savedCode && !merged.some((item) => item.code === savedCode)) {
        merged.push({
          code: savedCode,
          name: saved.fx_bank_name || savedCode,
          channel: saved.fx_bank_channel || "",
          channelLabel: saved.fx_bank_channel || "сохранённый",
        });
      }
      return merged.map((bank) => ({
        ...bank,
        quote: quotes.find((row) => String(row.bank_code || "").toLowerCase() === bank.code) || null,
        selected: String(n.bankCode?.value || "technobank").toLowerCase() === bank.code,
      }));
    }

    function renderBanks(mode) {
      const n = nodes(mode);
      if (!n.bankOptions) {
        return;
      }
      n.bankOptions.innerHTML = bankDescriptors(mode).map((bank) => {
        const channel = bank.quote?.channel_label || bank.channelLabel || bank.quote?.channel || bank.channel || "курс недоступен";
        const stale = bank.quote?.stale === true;
        return `
          <button class="fx-policy-option${bank.selected ? " active" : ""}" type="button" data-fx-bank-code="${escapeHtml(bank.code)}" data-stale="${stale ? "true" : "false"}" aria-pressed="${bank.selected ? "true" : "false"}">
            <strong>${escapeHtml(bank.quote?.bank_name || bank.name)}</strong>
            <span>${escapeHtml(stale ? `${channel} · устарел` : channel)}</span>
          </button>
        `;
      }).join("");
    }

    function provenanceMeta(mode) {
      const context = getContext(mode);
      const snapshot = uiState[mode].snapshot || {};
      if (context.source === "manual") {
        return "Ручной курс · изменяется только вами";
      }
      if (context.source === "nbrb") {
        const row = uiState[mode].options?.nbrb_rate || {};
        const rateDate = snapshot.fx_rate_date || snapshot.current_rate_date || row.rate_date || "";
        return `НБРБ${rateDate ? ` · ${core.formatDateRu(String(rateDate).slice(0, 10))}` : ""}`;
      }
      const quote = selectedBankQuote(mode) || {};
      const descriptor = bankDescriptors(mode).find((item) => item.code === context.bankCode) || {};
      const snapshotMatches = String(snapshot.fx_bank_code || "").toLowerCase() === context.bankCode;
      const bankName = quote.bank_name || descriptor.name || (snapshotMatches ? snapshot.fx_bank_name : null) || context.bankCode;
      const rawChannel = quote.channel || descriptor.channel || (snapshotMatches ? snapshot.fx_bank_channel : null) || "";
      const channel = quote.channel_label
        || descriptor.channelLabel
        || ({ cash: "наличные", online: "онлайн" }[rawChannel] || rawChannel);
      const quoted = (snapshotMatches && (snapshot.fx_quoted_at
        || snapshot.current_rate_quoted_at
        || snapshot.fx_fetched_at
        || snapshot.current_rate_fetched_at))
        || quote.quoted_at
        || quote.fetched_at
        || "";
      const snapshotStale = Object.prototype.hasOwnProperty.call(snapshot, "fx_rate_stale")
        ? snapshot.fx_rate_stale === true
        : snapshot.current_rate_stale === true;
      const stale = (snapshotMatches && snapshotStale)
        || quote.stale === true;
      return [
        bankName,
        channel,
        quoted ? `на ${formatDateTime(quoted)}` : "",
        stale ? "котировка устарела" : "",
      ].filter(Boolean).join(" · ");
    }

    function renderComputed(mode) {
      const n = nodes(mode);
      if (!n.computed) {
        return;
      }
      const context = getContext(mode);
      if (!context.hasForeignCurrency) {
        n.computed.textContent = "";
        return;
      }
      const amount = core.resolveMoneyInput(n.amount?.value || 0);
      const original = Number(amount.previewValue || 0);
      const baseAmount = original * Number(context.fxRate || 0);
      n.computed.textContent = original > 0 && context.fxRate > 0
        ? `${core.formatMoney(original, { currency: context.currency })} ≈ ${core.formatMoney(baseAmount, { currency: context.baseCurrency })}`
        : "Укажите сумму, чтобы увидеть BYN-эквивалент";
    }

    function renderUi(mode) {
      const n = nodes(mode);
      const context = getContext(mode);
      const incomeMode = n.kind?.value === "income";
      const previousKind = uiState[mode].lastKind;
      const kindChanged = Boolean(previousKind) && previousKind !== (n.kind?.value || "expense");
      uiState[mode].lastKind = n.kind?.value || "expense";
      if (kindChanged && context.hasForeignCurrency && context.source === "bank") {
        const defaultKind = incomeMode ? "buy" : "sell";
        if (n.rateKind) n.rateKind.value = defaultKind;
        context.rateKind = defaultKind;
        uiState[mode].preserveSnapshot = false;
        uiState[mode].policyDirty = true;
        if (!applyBankRate(mode, selectedBankQuote(mode))) {
          loadRateOptions(mode, { apply: true }).catch(() => {});
        }
      }
      if (incomeMode && n.paymentMode?.value !== "valuation") {
        n.paymentMode.value = "valuation";
        context.paymentMode = "valuation";
      }
      const source = context.source;
      syncControl(n.sourceSwitch, "fx-rate-source", source);
      syncControl(n.rateKindSwitch, "fx-rate-kind", context.rateKind);
      syncControl(n.paymentSwitch, "fx-payment-mode", context.paymentMode);
      n.bankFields?.classList.toggle("hidden", source !== "bank");
      if (n.rate) {
        n.rate.readOnly = source !== "manual";
      }
      if (n.refresh) {
        n.refresh.classList.toggle("hidden", source === "manual");
        n.refresh.disabled = uiState[mode].pending !== null;
        n.refresh.textContent = uiState[mode].pending ? "Обновляем…" : "Обновить курс";
      }
      if (n.rateLabel) {
        n.rateLabel.textContent = `Курс ${context.baseCurrency} за ${context.scale} ${context.currency}`;
      }
      if (n.paymentHint) {
        n.paymentHint.textContent = incomeMode
          ? "Для дохода доступна только BYN-оценка без списания или пополнения валютного остатка."
          : (PAYMENT_MODE_HINTS[context.paymentMode] || PAYMENT_MODE_HINTS.valuation);
      }
      n.paymentSwitch?.querySelectorAll("button[data-fx-payment-mode]").forEach((button) => {
        button.disabled = incomeMode && button.dataset.fxPaymentMode !== "valuation";
      });
      if (n.rateMeta) {
        const side = source === "bank" ? (context.rateKind === "buy" ? "Покупка банком" : "Продажа банком") : "";
        n.rateMeta.innerHTML = [side, provenanceMeta(mode)].filter(Boolean).map((value) => `<span>${escapeHtml(value)}</span>`).join("");
      }
      renderBanks(mode);
      renderComputed(mode);
    }

    function notifyUpdated(mode) {
      renderUi(mode);
      renderReceiptSummary(mode);
      if (mode === "edit") {
        syncEditFxSettlementFieldUi?.();
        updateEditPreview();
      } else {
        syncCreateFxSettlementFieldUi?.();
        updateCreatePreview();
      }
    }

    function reset(mode = "create") {
      const n = nodes(mode);
      uiState[mode] = freshState();
      uiState[mode].lastKind = n.kind?.value || "expense";
      if (n.source) n.source.value = "nbrb";
      if (n.bankCode) n.bankCode.value = "technobank";
      if (n.rateKind) n.rateKind.value = n.kind?.value === "income" ? "buy" : "sell";
      if (n.paymentMode) n.paymentMode.value = "valuation";
      if (n.rate) n.rate.value = "1";
      setHint(mode, "");
      renderUi(mode);
    }

    function hydrate(mode, item = null, options = {}) {
      const n = nodes(mode);
      const contextBefore = getContext(mode);
      const foreign = contextBefore.currency !== contextBefore.baseCurrency;
      const isPlan = options.isPlan === true;
      const fallbackSource = isPlan ? "nbrb" : "manual";
      const source = foreign ? normalizeSource(item?.fx_rate_source || fallbackSource) : "nbrb";
      const kind = n.kind?.value || item?.kind || "expense";
      const bankCode = String(item?.fx_bank_code || "technobank").toLowerCase();
      const rateKind = normalizeRateKind(item?.fx_rate_kind, kind);
      const paymentMode = normalizePaymentMode(item?.fx_payment_mode || (item?.fx_settlement ? "foreign_balance" : "valuation"));
      if (n.source) n.source.value = source;
      if (n.bankCode) n.bankCode.value = bankCode;
      if (n.rateKind) n.rateKind.value = rateKind;
      if (n.paymentMode) n.paymentMode.value = paymentMode;
      const snapshotRate = Number(item?.fx_rate || item?.current_rate || 0);
      const scale = displayScale(contextBefore.currency, null, item);
      const displayRate = Number(item?.fx_rate_display || item?.current_rate_display || (snapshotRate > 0 ? snapshotRate * scale : 0));
      if (n.rate) {
        n.rate.value = displayRate > 0 ? formatTradeRateValue(displayRate) : "";
      }
      uiState[mode] = {
        ...freshState(),
        currency: contextBefore.currency,
        preserveSnapshot: foreign && options.preserveSnapshot !== false,
        snapshot: item ? { ...item } : null,
        hydratedEntityId: item?.id ?? null,
        lastKind: kind,
      };
      renderUi(mode);
      if (foreign) {
        loadRateOptions(mode, { apply: options.applyCurrent === true }).catch(() => {});
      }
    }

    function applyNbrbRate(mode, row) {
      const n = nodes(mode);
      const context = getContext(mode);
      const unitRate = Number(row?.unit_rate || row?.rate || 0) / (row?.unit_rate ? 1 : Number(row?.scale || context.scale || 1));
      const shown = Number(row?.rate || (unitRate * context.scale));
      if (!(shown > 0) || !n.rate) {
        return false;
      }
      n.rate.value = formatTradeRateValue(shown);
      uiState[mode].snapshot = {
        ...(uiState[mode].snapshot || {}),
        fx_rate_scale: Number(row?.scale || context.scale || 1),
        fx_rate: unitRate,
        fx_rate_display: shown,
        fx_rate_date: row?.rate_date || null,
        fx_quoted_at: row?.rate_date || null,
        fx_fetched_at: null,
        fx_rate_stale: false,
      };
      return true;
    }

    function applyBankRate(mode, row) {
      const n = nodes(mode);
      const context = getContext(mode);
      const kind = context.rateKind;
      const unitKey = kind === "buy" ? "buy_unit_rate" : "sell_unit_rate";
      const displayKey = kind === "buy" ? "buy_rate" : "sell_rate";
      const unitRate = Number(row?.[unitKey] || 0) || (Number(row?.[displayKey] || 0) / Number(row?.scale || context.scale || 1));
      const shown = Number(row?.[displayKey] || (unitRate * context.scale));
      if (!(shown > 0) || !n.rate) {
        return false;
      }
      n.rate.value = formatTradeRateValue(shown);
      uiState[mode].snapshot = {
        ...(uiState[mode].snapshot || {}),
        fx_rate: unitRate,
        fx_rate_scale: Number(row?.scale || context.scale || 1),
        fx_rate_display: shown,
        fx_bank_code: row?.bank_code || context.bankCode,
        fx_bank_name: row?.bank_name || context.bankCode,
        fx_bank_channel: row?.channel || null,
        fx_quoted_at: row?.quoted_at || row?.fetched_at || null,
        fx_fetched_at: row?.fetched_at || null,
        fx_rate_stale: row?.stale === true,
      };
      return true;
    }

    function usesHistoricalNbrbRate(context) {
      return context.source === "nbrb"
        && !context.isPlanFlow
        && Boolean(context.operationDate)
        && context.operationDate < core.getTodayIso();
    }

    function rateOptionsUrl(context) {
      const params = new URLSearchParams({
        currency: context.currency,
        base_currency: context.baseCurrency,
      });
      if (usesHistoricalNbrbRate(context)) {
        params.set("as_of", context.operationDate);
      }
      return `/api/v1/currency/rate-options?${params.toString()}`;
    }

    async function requestRateOptions(context, requestStillCurrent = () => true) {
      let result = await core.requestJson(rateOptionsUrl(context), {
        headers: core.authHeaders(),
        cache: "no-store",
      });
      if (!requestStillCurrent()) {
        return null;
      }
      if (!usesHistoricalNbrbRate(context) || result?.nbrb_rate) {
        return result;
      }
      await core.requestJson(
        `/api/v1/currency/rates/history/fill?currency=${encodeURIComponent(context.currency)}&date_from=${encodeURIComponent(context.operationDate)}&date_to=${encodeURIComponent(context.operationDate)}`,
        { method: "POST", headers: core.authHeaders() },
      );
      if (!requestStillCurrent()) {
        return null;
      }
      result = await core.requestJson(rateOptionsUrl(context), {
        headers: core.authHeaders(),
        cache: "no-store",
      });
      return requestStillCurrent() ? result : null;
    }

    async function loadRateOptions(mode, options = {}) {
      const context = getContext(mode);
      if (!context.hasForeignCurrency) {
        return null;
      }
      const current = uiState[mode];
      const seq = current.requestSeq + 1;
      current.requestSeq = seq;
      const requestStillCurrent = () => {
        const latestContext = getContext(mode);
        return uiState[mode] === current
          && current.requestSeq === seq
          && latestContext.currency === context.currency
          && latestContext.baseCurrency === context.baseCurrency;
      };
      const shouldApply = options.apply === true && !current.preserveSnapshot;
      const request = requestRateOptions(context, requestStillCurrent);
      current.pending = request;
      renderUi(mode);
      try {
        const result = await request;
        if (!requestStillCurrent()) {
          return null;
        }
        uiState[mode].options = result || null;
        let applied = false;
        if (shouldApply) {
          const latestContext = getContext(mode);
          if (latestContext.source === "bank") {
            applied = applyBankRate(mode, selectedBankQuote(mode));
          } else if (latestContext.source === "nbrb") {
            applied = applyNbrbRate(mode, result?.nbrb_rate);
          }
          if (!applied) {
            setHint(mode, "Котировка не найдена. Выберите другой банк или укажите курс вручную.", "warning");
          } else {
            setHint(mode, "Курс подставлен по выбранному источнику", "auto");
          }
        }
        return result;
      } catch (error) {
        if (requestStillCurrent()) {
          setHint(mode, "Не удалось получить котировки. Сохранённый курс не изменён.", "warning");
        }
        return null;
      } finally {
        if (requestStillCurrent()) {
          uiState[mode].pending = null;
          notifyUpdated(mode);
        }
      }
    }

    async function syncFields(mode = "create", options = {}) {
      const n = nodes(mode);
      const context = getContext(mode);
      const policyState = uiState[mode];
      n.field?.classList.toggle("hidden", !context.hasForeignCurrency);
      if (!context.hasForeignCurrency) {
        if (n.rate) n.rate.value = "1";
        if (n.source) n.source.value = "nbrb";
        if (n.bankCode) n.bankCode.value = "technobank";
        if (n.rateKind) n.rateKind.value = n.kind?.value === "income" ? "buy" : "sell";
        if (n.paymentMode) n.paymentMode.value = "valuation";
        uiState[mode] = freshState();
        setHint(mode, "");
        notifyUpdated(mode);
        return;
      }
      const currencyChanged = policyState.currency && policyState.currency !== context.currency;
      if (currencyChanged || options.resetPolicy === true) {
        const entityId = policyState.hydratedEntityId;
        reset(mode);
        uiState[mode].currency = context.currency;
        uiState[mode].hydratedEntityId = entityId;
      } else {
        policyState.currency = context.currency;
      }
      renderUi(mode);
      if (uiState[mode].preserveSnapshot) {
        loadRateOptions(mode, { apply: false }).catch(() => {});
        return;
      }
      if (context.source === "manual") {
        notifyUpdated(mode);
        return;
      }
      await loadRateOptions(mode, { apply: true });
    }

    async function setSource(mode, value) {
      const n = nodes(mode);
      if (n.source) n.source.value = normalizeSource(value);
      uiState[mode].preserveSnapshot = false;
      uiState[mode].policyDirty = true;
      if (n.source?.value === "manual") {
        setHint(mode, "Укажите фактический курс вручную", "manual");
        notifyUpdated(mode);
        n.rate?.focus();
        return;
      }
      await loadRateOptions(mode, { apply: true });
    }

    async function setBank(mode, value) {
      const n = nodes(mode);
      if (n.bankCode) n.bankCode.value = String(value || "technobank").toLowerCase();
      uiState[mode].preserveSnapshot = false;
      uiState[mode].policyDirty = true;
      await loadRateOptions(mode, { apply: true });
    }

    async function setRateKind(mode, value) {
      const n = nodes(mode);
      if (n.rateKind) n.rateKind.value = normalizeRateKind(value, n.kind?.value || "expense");
      uiState[mode].preserveSnapshot = false;
      uiState[mode].policyDirty = true;
      await loadRateOptions(mode, { apply: true });
    }

    function setPaymentMode(mode, value) {
      const n = nodes(mode);
      const nextValue = normalizePaymentMode(value);
      if (n.kind?.value === "income" && nextValue !== "valuation") {
        return;
      }
      if (n.paymentMode) n.paymentMode.value = nextValue;
      const toggle = mode === "edit" ? el.editUseFxSettlement : el.opUseFxSettlement;
      if (toggle) toggle.checked = false;
      notifyUpdated(mode);
    }

    async function refresh(mode) {
      const context = getContext(mode);
      if (!context.hasForeignCurrency || context.source === "manual") {
        return;
      }
      const current = uiState[mode];
      const seq = current.requestSeq + 1;
      current.requestSeq = seq;
      const requestStillCurrent = () => {
        const latestContext = getContext(mode);
        return uiState[mode] === current
          && current.requestSeq === seq
          && latestContext.currency === context.currency
          && latestContext.baseCurrency === context.baseCurrency
          && latestContext.source === context.source
          && latestContext.bankCode === context.bankCode;
      };
      const params = new URLSearchParams({
        currency: context.currency,
        base_currency: context.baseCurrency,
      });
      if (context.source === "bank") {
        params.set("bank_code", context.bankCode);
      }
      const refreshRequest = (async () => {
        if (context.source === "bank") {
          return core.requestJson(
            `/api/v1/currency/rate-options/refresh?${params.toString()}`,
            { method: "POST", headers: core.authHeaders() },
          );
        }
        if (!usesHistoricalNbrbRate(context)) {
          await core.requestJson(
            `/api/v1/currency/rates/refresh?currency=${encodeURIComponent(context.currency)}`,
            { method: "POST", headers: core.authHeaders() },
          );
        }
        if (!requestStillCurrent()) {
          return null;
        }
        return requestRateOptions(context, requestStillCurrent);
      })();
      current.pending = refreshRequest;
      renderUi(mode);
      try {
        const refreshedOptions = await refreshRequest;
        if (!requestStillCurrent()) {
          return;
        }
        current.options = refreshedOptions || current.options;
        const latestContext = getContext(mode);
        let applied = false;
        if (latestContext.source === "bank") {
          const refreshedQuote = selectedBankQuote(mode);
          if (!refreshedQuote || refreshedQuote.stale === true) {
            throw new Error("selected bank quote is missing or stale");
          }
          applied = applyBankRate(mode, refreshedQuote);
        } else if (latestContext.source === "nbrb") {
          applied = applyNbrbRate(mode, current.options?.nbrb_rate);
        }
        if (!applied) {
          throw new Error("rate option is unavailable");
        }
      } catch (error) {
        if (!requestStillCurrent()) {
          return;
        }
        current.pending = null;
        setHint(mode, "Не удалось обновить котировку. Сохранённый курс не изменён.", "warning");
        notifyUpdated(mode);
        return;
      }
      if (!requestStillCurrent()) {
        return;
      }
      current.pending = null;
      current.preserveSnapshot = false;
      current.refreshRequested = true;
      setHint(mode, "Котировка обновлена явно", "auto");
      notifyUpdated(mode);
    }

    function markManual(mode) {
      const context = getContext(mode);
      if (context.source !== "manual") {
        return;
      }
      uiState[mode].preserveSnapshot = false;
      uiState[mode].policyDirty = true;
      setHint(mode, "Ручной курс будет сохранён как снимок", "manual");
      notifyUpdated(mode);
    }

    function payload(mode = "create", options = {}) {
      const context = getContext(mode);
      if (!context.hasForeignCurrency) {
        // Currency itself is authoritative: both Operation and Plan services
        // clear foreign-rate policy when it becomes the base currency.  Omitting
        // the policy here also keeps legacy BYN + fx_settlement edits compatible.
        return {};
      }
      const quote = selectedBankQuote(mode);
      const snapshot = uiState[mode].snapshot || {};
      const descriptor = bankDescriptors(mode).find((item) => item.code === context.bankCode) || {};
      const savedChannel = String(snapshot.fx_bank_code || "").toLowerCase() === context.bankCode
        ? snapshot.fx_bank_channel
        : null;
      const result = {
        fx_rate_source: context.source,
        fx_bank_code: context.source === "bank" ? context.bankCode : null,
        fx_bank_channel: context.source === "bank"
          ? (quote?.channel || descriptor.channel || savedChannel || null)
          : null,
        fx_rate_kind: context.source === "bank" ? context.rateKind : null,
        fx_payment_mode: context.paymentMode,
        fx_manual_rate: context.source === "manual"
          ? core.resolveRateInput(context.displayRate, 1, 6).formatted
          : null,
      };
      if (context.source === "manual" && (!context.displayRateState.valid || !(context.displayRate > 0))) {
        throw new Error("Проверь ручной курс конверсии");
      }
      if (mode === "edit" && options.isPlan !== true) {
        result.fx_refresh_rate = uiState[mode].refreshRequested || uiState[mode].policyDirty;
      }
      return result;
    }

    function preview(mode = "create") {
      const context = getContext(mode);
      if (!context.hasForeignCurrency) {
        return {};
      }
      const quote = selectedBankQuote(mode) || {};
      const snapshot = uiState[mode].snapshot || {};
      const descriptor = bankDescriptors(mode).find((item) => item.code === context.bankCode) || {};
      const savedBankMatches = String(snapshot.fx_bank_code || "").toLowerCase() === context.bankCode;
      return {
        fx_rate: context.fxRate,
        fx_rate_scale: context.scale,
        fx_rate_display: context.displayRate,
        fx_rate_source: context.source,
        fx_bank_code: context.source === "bank" ? context.bankCode : null,
        fx_bank_name: context.source === "bank"
          ? (quote.bank_name || descriptor.name || (savedBankMatches ? snapshot.fx_bank_name : null) || context.bankCode)
          : null,
        fx_bank_channel: context.source === "bank"
          ? (quote.channel || descriptor.channel || (savedBankMatches ? snapshot.fx_bank_channel : null) || null)
          : null,
        fx_rate_kind: context.source === "bank" ? context.rateKind : null,
        fx_payment_mode: context.paymentMode,
        fx_quoted_at: snapshot.fx_quoted_at || quote.quoted_at || quote.fetched_at || null,
        fx_fetched_at: snapshot.fx_fetched_at || quote.fetched_at || null,
        fx_rate_stale: snapshot.fx_rate_stale === true || quote.stale === true,
        fx_rate_date: snapshot.fx_rate_date || snapshot.current_rate_date || null,
      };
    }

    function bindMode(mode) {
      const n = nodes(mode);
      n.sourceSwitch?.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-fx-rate-source]");
        if (button) setSource(mode, button.dataset.fxRateSource).catch(() => {});
      });
      n.bankOptions?.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-fx-bank-code]");
        if (button) setBank(mode, button.dataset.fxBankCode).catch(() => {});
      });
      n.rateKindSwitch?.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-fx-rate-kind]");
        if (button) setRateKind(mode, button.dataset.fxRateKind).catch(() => {});
      });
      n.paymentSwitch?.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-fx-payment-mode]");
        if (button) setPaymentMode(mode, button.dataset.fxPaymentMode);
      });
      n.refresh?.addEventListener("click", () => refresh(mode).catch(() => {}));
      n.rate?.addEventListener("input", () => markManual(mode));
      n.amount?.addEventListener("input", () => renderComputed(mode));
      n.amount?.addEventListener("change", () => renderComputed(mode));
    }

    function bind() {
      bindMode("create");
      bindMode("edit");
      renderBanks("create");
      renderBanks("edit");
    }

    return {
      bind,
      reset,
      hydrate,
      getContext,
      getPayload: payload,
      getPreview: preview,
      syncFields,
      refresh,
      markManual,
      setHint,
      renderUi,
      loadRateOptions,
    };
  }

  window.App.registerRuntimeModule?.("operation-modal-fx-policy-factory", createOperationModalFxPolicyFeature);
  window.App.registerRuntimeModule?.("fx-policy-display", { formatFxPolicyProvenance });
})();
