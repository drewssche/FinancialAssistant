(() => {
  function createOperationModalDebtCounterpartyFeature(deps) {
    const {
      state,
      el,
      core,
      getCurrentDebtEditId,
      getCurrentDebtDirection,
      getCurrentDebtCurrency,
      getCurrentDebtPrincipalValue,
      getCurrentDebtStartDate,
      getCurrentDebtDueDate,
      getCurrentDebtNote,
      updateCreatePreview,
    } = deps;

    const pickerUtils = window.App.getRuntimeModule?.("picker-utils");

    function normalizeCounterpartyName(value) {
      return String(value || "").trim().replace(/\s+/g, " ");
    }

    function getCounterpartyCards() {
      return Array.isArray(state.debtCardsCache) ? state.debtCardsCache : [];
    }

    function getCounterpartyEntries(query = "") {
      const normalizedQuery = normalizeCounterpartyName(query).toLowerCase();
      const byName = new Map();
      for (const card of getCounterpartyCards()) {
        const name = normalizeCounterpartyName(card?.counterparty || "");
        if (!name) {
          continue;
        }
        const key = name.toLowerCase();
        if (normalizedQuery && !key.includes(normalizedQuery)) {
          continue;
        }
        if (!byName.has(key)) {
          byName.set(key, {
            counterparty: name,
            counterparty_id: Number(card?.counterparty_id || 0) || null,
            status: card?.status === "active" ? "active" : "closed",
          });
        }
      }
      return Array.from(byName.values()).sort((a, b) => {
        if (a.status !== b.status) {
          return a.status === "active" ? -1 : 1;
        }
        return a.counterparty.localeCompare(b.counterparty, "ru");
      });
    }

    function findCounterpartyCardByName(value) {
      const normalized = normalizeCounterpartyName(value).toLowerCase();
      if (!normalized) {
        return null;
      }
      return getCounterpartyCards().find((card) => normalizeCounterpartyName(card?.counterparty || "").toLowerCase() === normalized) || null;
    }

    function findDebtMergeCandidate(card, direction, currency, excludeDebtId = 0) {
      if (!card || !Array.isArray(card.debts)) {
        return null;
      }
      const activeDebts = card.debts
        .filter((debt) => debt?.direction === direction)
        .filter((debt) => String(debt?.currency || "BYN").toUpperCase() === String(currency || "BYN").toUpperCase())
        .filter((debt) => Number(debt?.outstanding_total || 0) > 0)
        .filter((debt) => Number(debt?.id || 0) !== Number(excludeDebtId || 0))
        .sort((a, b) => {
          const aDate = String(a?.start_date || "");
          const bDate = String(b?.start_date || "");
          if (aDate !== bDate) {
            return aDate.localeCompare(bDate, "ru");
          }
          return Number(a?.id || 0) - Number(b?.id || 0);
        });
      return activeDebts[0] || null;
    }

    function getDebtPreviewSnapshot() {
      const inputCounterparty = normalizeCounterpartyName(el.debtCounterparty?.value || "");
      const direction = getCurrentDebtDirection();
      const currency = getCurrentDebtCurrency();
      const principalValue = Number(getCurrentDebtPrincipalValue() || 0);
      const startDate = getCurrentDebtStartDate();
      const dueDate = getCurrentDebtDueDate();
      const note = normalizeCounterpartyName(getCurrentDebtNote());
      const manual = {
        counterparty: inputCounterparty,
        direction,
        currency,
        principalValue,
        startDate,
        dueDate,
        note,
        mergeTargetId: null,
      };
      if (!inputCounterparty) {
        return manual;
      }
      const card = findCounterpartyCardByName(inputCounterparty);
      if (!card) {
        return manual;
      }
      const mergeTarget = findDebtMergeCandidate(card, direction, currency, getCurrentDebtEditId());
      if (!mergeTarget) {
        return { ...manual, counterparty: card.counterparty || inputCounterparty };
      }
      const mergedPrincipal = Number(mergeTarget.principal || 0) + principalValue;
      const mergedStartDate = startDate && mergeTarget.start_date
        ? (startDate < String(mergeTarget.start_date) ? startDate : String(mergeTarget.start_date))
        : (startDate || String(mergeTarget.start_date || ""));
      const mergedDueDate = mergeTarget.due_date ? String(mergeTarget.due_date) : (dueDate || "");
      const mergedNote = normalizeCounterpartyName(mergeTarget.note || "") || note;
      return {
        counterparty: card.counterparty || inputCounterparty,
        direction,
        currency,
        principalValue: mergedPrincipal,
        startDate: mergedStartDate,
        dueDate: mergedDueDate,
        note: mergedNote,
        mergeTargetId: Number(mergeTarget.id || 0) || null,
      };
    }

    function openDebtCounterpartyPopover() {
      pickerUtils.setPopoverOpen(el.debtCounterpartyPickerBlock, true, {
        owners: [el.debtCounterpartyField],
        onClose: closeDebtCounterpartyPopover,
      });
    }

    function closeDebtCounterpartyPopover() {
      pickerUtils.setPopoverOpen(el.debtCounterpartyPickerBlock, false, { owners: [el.debtCounterpartyField] });
    }

    function renderDebtCounterpartyPicker() {
      if (!el.debtCounterpartyAll) {
        return;
      }
      const selectedName = normalizeCounterpartyName(el.debtCounterparty?.value || "");
      const items = getCounterpartyEntries(selectedName);
      el.debtCounterpartyAll.innerHTML = "";
      for (const item of items) {
        const btn = pickerUtils.createChipButton({
          datasetName: "debtCounterpartyName",
          datasetValue: item.counterparty,
          selected: selectedName && selectedName.toLowerCase() === item.counterparty.toLowerCase(),
          html: core.renderCategoryChip({ name: item.counterparty, icon: null, accent_color: null }, selectedName),
        });
        el.debtCounterpartyAll.appendChild(btn);
      }
      const exactMatch = items.some((item) => item.counterparty.toLowerCase() === selectedName.toLowerCase());
      if (selectedName && !exactMatch) {
        const createBtn = pickerUtils.createActionChipButton({
          datasetName: "createDebtCounterparty",
          datasetValue: selectedName,
          label: `+ Создать контрагента «${selectedName}»`,
        });
        el.debtCounterpartyAll.appendChild(createBtn);
      }
      if (!items.length && !selectedName) {
        el.debtCounterpartyAll.innerHTML = "<span class='muted-small'>Нет контрагентов</span>";
      } else if (!items.length && selectedName) {
        const empty = document.createElement("span");
        empty.className = "muted-small";
        empty.textContent = "Совпадений нет";
        el.debtCounterpartyAll.appendChild(empty);
      }
    }

    function selectDebtCounterparty(name, options = {}) {
      const normalized = normalizeCounterpartyName(name);
      el.debtCounterparty.value = normalized;
      renderDebtCounterpartyPicker();
      updateCreatePreview();
      if (!options.keepOpen) {
        closeDebtCounterpartyPopover();
      }
    }

    function handleDebtCounterpartySearchFocus() {
      openDebtCounterpartyPopover();
      renderDebtCounterpartyPicker();
    }

    function handleDebtCounterpartySearchInput() {
      openDebtCounterpartyPopover();
      renderDebtCounterpartyPicker();
      updateCreatePreview();
    }

    function handleDebtCounterpartySearchKeydown(event) {
      if (event.key === "Escape") {
        closeDebtCounterpartyPopover();
        return;
      }
      if (event.key !== "Enter") {
        return;
      }
      event.preventDefault();
      const query = normalizeCounterpartyName(el.debtCounterparty?.value || "");
      if (!query) {
        closeDebtCounterpartyPopover();
        return;
      }
      const matches = getCounterpartyEntries(query);
      if (matches.length) {
        selectDebtCounterparty(matches[0].counterparty);
        return;
      }
      selectDebtCounterparty(query);
    }

    function handleDebtCounterpartyPickerClick(event) {
      const createBtn = event.target.closest("button[data-create-debt-counterparty]");
      if (createBtn) {
        selectDebtCounterparty(createBtn.dataset.createDebtCounterparty || "");
        return;
      }
      const chipBtn = event.target.closest("button[data-debt-counterparty-name]");
      if (!chipBtn) {
        return;
      }
      selectDebtCounterparty(chipBtn.dataset.debtCounterpartyName || "");
    }

    function handleDebtCounterpartyOutsidePointer(event) {
      pickerUtils.closePopoverOnOutside(event, {
        popover: el.debtCounterpartyPickerBlock,
        scopes: [el.debtCounterpartyField],
        onClose: closeDebtCounterpartyPopover,
      });
    }

    return {
      getDebtPreviewSnapshot,
      renderDebtCounterpartyPicker,
      openDebtCounterpartyPopover,
      closeDebtCounterpartyPopover,
      handleDebtCounterpartySearchFocus,
      handleDebtCounterpartySearchInput,
      handleDebtCounterpartySearchKeydown,
      handleDebtCounterpartyPickerClick,
      handleDebtCounterpartyOutsidePointer,
      selectDebtCounterparty,
    };
  }

  window.App = window.App || {};
  window.App.registerRuntimeModule?.("operation-modal-debt-counterparty-factory", createOperationModalDebtCounterpartyFeature);
})();
