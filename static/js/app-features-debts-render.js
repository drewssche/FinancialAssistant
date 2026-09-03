(() => {
  const { state, el, core } = window.App;
  const debtUi = core.debtUi;
  const formatMoney = debtUi.formatMoney;
  const parseIsoDateEnd = debtUi.parseIsoDateEnd;
  const debtDueState = debtUi.debtDueState;
  const debtDueProgress = debtUi.debtDueProgress;
  const debtDueDaysBadge = debtUi.debtDueDaysBadge;
  const debtRepaymentProgress = debtUi.debtRepaymentProgress;

  function formatDebtMoney(value, currency = "BYN") {
    return core.formatMoney(value, { currency });
  }

  function formatDebtAmountBlock(primaryValue, currency, currentBaseValue, baseCurrency = "BYN", extraClass = "") {
    const primary = formatDebtMoney(primaryValue, currency);
    if (String(currency || "BYN").toUpperCase() === String(baseCurrency || "BYN").toUpperCase()) {
      return `<span class="${extraClass}">${primary}</span>`;
    }
    return `<span class="${extraClass}">${primary}</span><div class="muted-small">≈ ${core.formatMoney(currentBaseValue || 0, { currency: baseCurrency })}</div>`;
  }

  function debtDueLabel(stateValue, dueDate) {
    if (stateValue === "overdue") {
      return "Просрочено";
    }
    if (stateValue === "soon") {
      return `Скоро срок: ${core.formatDateRu(dueDate)}`;
    }
    if (stateValue === "future" && dueDate) {
      return `Срок: ${core.formatDateRu(dueDate)}`;
    }
    if (stateValue === "closed") {
      return "Закрыт";
    }
    return "Без срока";
  }

  function debtClosureMeta(debt) {
    const forgiven = Number(debt.forgiven_total || 0);
    if (forgiven <= 0) {
      return String(debt.closure_reason || "") === "forgiven"
        ? '<span class="muted-small">Прощен</span>'
        : "";
    }
    return `<span class="muted-small">Прощено: <strong>${formatDebtMoney(forgiven, debt.currency || "BYN")}</strong></span>`;
  }

  function debtRepaidClass(debt) {
    const direction = debt.direction === "borrow" ? "borrow" : "lend";
    const repaid = Number(debt.repaid_total || 0);
    const outstanding = Number(debt.outstanding_total || 0);
    if (direction === "borrow") {
      if (repaid <= 0) {
        return "debt-amount-repaid-borrow-zero";
      }
      if (outstanding > 0) {
        return "debt-amount-repaid-borrow-partial";
      }
      return "debt-amount-repaid-borrow-closed";
    }
    return "debt-amount-repaid-lend";
  }

  function debtPriorityRank(stateValue) {
    if (stateValue === "overdue") {
      return 0;
    }
    if (stateValue === "soon") {
      return 1;
    }
    if (stateValue === "future") {
      return 2;
    }
    if (stateValue === "none") {
      return 3;
    }
    return 4;
  }

  function isClosedDebt(debt) {
    return Number(debt?.outstanding_total || 0) <= 0.000001;
  }

  function filterCards(cards) {
    const statusFilter = state.debtStatusFilter || "active";
    if (statusFilter === "all") {
      return cards.slice();
    }
    const filtered = [];

    for (const card of cards) {
      const allDebts = card.debts || [];
      const activeDebts = allDebts.filter((debt) => !isClosedDebt(debt));
      const closedDebts = allDebts.filter(isClosedDebt);
      const counterpartyId = Number(card.counterparty_id || 0);
      const closedExpanded = statusFilter === "active"
        && state.expandedDebtClosedCounterpartyIds?.has(counterpartyId);
      const statusDebts = statusFilter === "closed" ? closedDebts : activeDebts;
      if (!statusDebts.length) {
        continue;
      }
      const visibleDebts = closedExpanded ? [...activeDebts, ...closedDebts] : statusDebts;
      const outstandingTotal = statusDebts.reduce(
        (total, debt) => total + Number(debt.current_base_outstanding_total ?? debt.outstanding_total ?? 0),
        0,
      );
      filtered.push({
        ...card,
        debts: visibleDebts,
        outstanding_total: outstandingTotal,
        status: statusFilter,
        closed_debts_count: closedDebts.length,
        closed_debts_expanded: closedExpanded,
      });
    }
    return filtered;
  }

  function cardPriorityInfo(card, now) {
    let rank = 9;
    let dueTs = Number.POSITIVE_INFINITY;
    for (const debt of card.debts || []) {
      if (Number(debt.outstanding_total || 0) <= 0) {
        continue;
      }
      const dueState = debtDueState(debt, now);
      const dueRank = debtPriorityRank(dueState);
      if (dueRank < rank) {
        rank = dueRank;
      }
      const due = parseIsoDateEnd(debt.due_date);
      if (due && due.getTime() < dueTs) {
        dueTs = due.getTime();
      }
    }
    return { rank, dueTs };
  }

  function sortCards(cards) {
    const preset = state.debtSortPreset || "priority";
    const now = new Date();
    const sorted = cards.slice();
    if (preset === "name") {
      sorted.sort((a, b) => String(a.counterparty || "").localeCompare(String(b.counterparty || ""), "ru"));
      return sorted;
    }
    if (preset === "amount") {
      sorted.sort((a, b) => {
        const diff = Number(b.outstanding_total || 0) - Number(a.outstanding_total || 0);
        if (diff !== 0) {
          return diff;
        }
        return String(a.counterparty || "").localeCompare(String(b.counterparty || ""), "ru");
      });
      return sorted;
    }
    sorted.sort((a, b) => {
      const aStatus = a.status === "active" ? 0 : 1;
      const bStatus = b.status === "active" ? 0 : 1;
      if (aStatus !== bStatus) {
        return aStatus - bStatus;
      }
      const aInfo = cardPriorityInfo(a, now);
      const bInfo = cardPriorityInfo(b, now);
      if (aInfo.rank !== bInfo.rank) {
        return aInfo.rank - bInfo.rank;
      }
      if (aInfo.dueTs !== bInfo.dueTs) {
        return aInfo.dueTs - bInfo.dueTs;
      }
      return String(a.counterparty || "").localeCompare(String(b.counterparty || ""), "ru");
    });
    return sorted;
  }

  function summarizeDebtCards(cards) {
    const configCurrency = core.normalizeCurrencyCode?.(core.getCurrencyConfig?.().code || "BYN", "BYN") || "BYN";
    const summary = {
      lendTotal: 0,
      borrowTotal: 0,
      activeCardCount: 0,
      baseCurrency: configCurrency,
    };
    for (const card of cards || []) {
      let hasActiveDebt = false;
      for (const debt of card.debts || []) {
        const outstanding = Number(debt.current_base_outstanding_total ?? debt.outstanding_total ?? 0);
        if (Math.abs(outstanding) <= 0.000001) {
          continue;
        }
        const baseCurrency = core.normalizeCurrencyCode?.(debt.base_currency || summary.baseCurrency, summary.baseCurrency) || summary.baseCurrency;
        summary.baseCurrency = baseCurrency || summary.baseCurrency;
        if (debt.direction === "borrow") {
          summary.borrowTotal += outstanding;
        } else {
          summary.lendTotal += outstanding;
        }
        hasActiveDebt = true;
      }
      if (hasActiveDebt || card.status === "active") {
        summary.activeCardCount += 1;
      }
    }
    summary.netTotal = summary.lendTotal - summary.borrowTotal;
    return summary;
  }

  function renderDebtsSectionKpi(cards) {
    if (!el.debtsSectionKpi) {
      return;
    }
    const summary = summarizeDebtCards(cards);
    const netTone = summary.netTotal > 0.000001
      ? "analytics-kpi-positive"
      : summary.netTotal < -0.000001
        ? "analytics-kpi-negative"
        : "analytics-kpi-neutral";
    const netPrefix = summary.netTotal > 0.000001 ? "+" : summary.netTotal < -0.000001 ? "-" : "";
    el.debtsSectionKpi.innerHTML = `
      <article class="analytics-kpi-card analytics-kpi-negative">
        <div class="muted-small">Я должен</div>
        <strong>${formatDebtMoney(summary.borrowTotal, summary.baseCurrency)}</strong>
      </article>
      <article class="analytics-kpi-card analytics-kpi-positive">
        <div class="muted-small">Мне должны</div>
        <strong>${formatDebtMoney(summary.lendTotal, summary.baseCurrency)}</strong>
      </article>
      <article class="analytics-kpi-card ${netTone}">
        <div class="muted-small">Чистая позиция</div>
        <strong>${netPrefix}${formatDebtMoney(Math.abs(summary.netTotal), summary.baseCurrency)}</strong>
      </article>
      <article class="analytics-kpi-card analytics-kpi-neutral">
        <div class="muted-small">Активных карточек</div>
        <strong>${summary.activeCardCount}</strong>
      </article>
    `;
  }

  function renderDebtCards(cards) {
    if (!el.debtsCards) {
      return;
    }
    el.debtsCards.innerHTML = "";
    const visibleCards = sortCards(filterCards(cards));
    renderDebtsSectionKpi(visibleCards);
    const pageSize = Number(state.debtCardsPageSize || 20);
    const visibleLimit = Number(state.debtCardsVisibleLimit || pageSize);
    const renderedCards = visibleCards.slice(0, Math.max(pageSize, visibleLimit));
    state.debtCardsVisibleTotal = visibleCards.length;
    state.debtCardsHasMore = renderedCards.length < visibleCards.length;
    if (el.debtsInfiniteSentinel) {
      el.debtsInfiniteSentinel.classList.toggle("hidden", !state.debtCardsHasMore);
    }
    const searchQuery = String(el.debtSearchQ?.value || "").trim();
    const compactMobile = window.matchMedia("(max-width: 640px)").matches;
    if (!renderedCards.length) {
      const empty = document.createElement("div");
      empty.className = "muted-small";
      empty.textContent = "Долги не найдены";
      el.debtsCards.appendChild(empty);
      return;
    }

    for (const card of renderedCards) {
      const item = document.createElement("article");
      item.className = "panel debt-card";
      item.dataset.debtCounterpartyId = String(card.counterparty_id || "");
      const now = new Date();
      const sortedDebts = (card.debts || []).slice().sort((a, b) => {
        const aState = debtDueState(a, now);
        const bState = debtDueState(b, now);
        const rankDiff = debtPriorityRank(aState) - debtPriorityRank(bState);
        if (rankDiff !== 0) {
          return rankDiff;
        }
        const aDue = parseIsoDateEnd(a.due_date);
        const bDue = parseIsoDateEnd(b.due_date);
        if (aDue && bDue) {
          return aDue.getTime() - bDue.getTime();
        }
        if (aDue) {
          return -1;
        }
        if (bDue) {
          return 1;
        }
        return b.id - a.id;
      });

      const debtsRows = sortedDebts
        .map((debt) => {
          const dueState = debtDueState(debt, now);
          const dueProgress = debtDueProgress(debt, dueState, now);
          const dueDays = debtDueDaysBadge(debt, dueState, now);
          const repayProgress = debtRepaymentProgress(debt);
          const repayments = debt.repayments || [];
          const issuances = debt.issuances || [];
          const direction = debt.direction === "borrow" ? "borrow" : "lend";
          const directionLabel = debtUi.debtDirectionActionLabel(direction);
          const repaidClass = debtRepaidClass(debt);
          const noteText = debt.note ? core.highlightText(String(debt.note), searchQuery) : "";
          if (compactMobile) {
            return `
              <article class="debt-mobile-entry debt-row-${dueState} debt-row-${direction} table-record-open-row" data-debt-row-id="${debt.id}" tabindex="0">
                <div class="debt-mobile-entry-head">
                  <div class="debt-mobile-entry-main">
                    <div class="debt-mobile-entry-topline">
                      <span class="debt-direction-pill debt-direction-pill-${direction}">${directionLabel}</span>
                      <strong class="debt-amount-principal debt-amount-principal-${direction}">${formatDebtMoney(debt.outstanding_total, debt.currency || "BYN")}</strong>
                    </div>
                    <div class="debt-mobile-entry-meta">
                      <span class="muted-small">Старт: ${core.formatDateRu(debt.start_date)}</span>
                      <span class="muted-small">${debtDueLabel(dueState, debt.due_date)}</span>
                      ${String(debt.currency || "BYN").toUpperCase() !== String(debt.base_currency || "BYN").toUpperCase() ? `<span class="muted-small">≈ ${core.formatMoney(debt.current_base_outstanding_total || 0, { currency: debt.base_currency || "BYN" })}</span>` : ""}
                      ${dueDays ? `<span class="debt-due-days-badge debt-due-days-badge-${dueState}">${dueDays}</span>` : ""}
                    </div>
                  </div>
                  <div class="mobile-card-kebab-wrap">
                    <button class="btn btn-secondary mobile-card-kebab-trigger" data-mobile-card-menu-trigger="debt-${debt.id}" type="button" aria-label="Действия долга">
                      <span aria-hidden="true">⋮</span>
                    </button>
                    <div class="app-popover hidden mobile-card-actions-popover" data-mobile-card-menu="debt-${debt.id}">
                      <div class="mobile-card-actions-menu">
                        <button class="btn btn-secondary" type="button" data-history-debt-id="${debt.id}">Движения</button>
                        <button class="btn btn-secondary" type="button" data-add-debt-issuance-id="${debt.id}">Добавить сумму</button>
                        <button class="btn btn-secondary" type="button" data-activity-entity-type="debt" data-activity-entity-id="${debt.id}">Журнал</button>
                        <button class="btn btn-secondary" type="button" data-forgive-debt-id="${debt.id}" ${Number(debt.outstanding_total) <= 0 ? "disabled" : ""}>Простить</button>
                        <button class="btn btn-secondary" type="button" data-edit-debt-id="${debt.id}">Редактировать</button>
                        <button class="btn btn-danger" type="button" data-delete-debt-id="${debt.id}">Удалить</button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="debt-mobile-entry-body">
                  <div class="debt-mobile-entry-stats">
                    <span class="muted-small">Сумма: <strong class="debt-amount-principal debt-amount-principal-${direction}">${formatDebtMoney(debt.principal, debt.currency || "BYN")}</strong></span>
                    <span class="muted-small">Погашено: <strong class="debt-amount-repaid ${repaidClass}">${formatDebtMoney(debt.repaid_total, debt.currency || "BYN")}</strong></span>
                    ${debtClosureMeta(debt)}
                  </div>
                  <div class="debt-repay-progress">
                    <div class="debt-repay-progress-track">
                      <span class="debt-repay-progress-bar debt-repay-progress-bar-${repayProgress.tone}" style="width:${repayProgress.percent}%"></span>
                    </div>
                    <span class="muted-small">Погашено: ${repayProgress.percent}%</span>
                  </div>
                  ${
                    dueProgress
                      ? `<div class="debt-due-progress"><div class="debt-due-progress-track"><span class="debt-due-progress-bar debt-due-progress-bar-${dueProgress.tone}" style="width:${dueProgress.percent}%"></span></div><span class="muted-small">Срок: ${dueProgress.percent}%</span></div>`
                      : ""
                  }
                  ${noteText ? `<div class="muted-small debt-mobile-entry-note">${noteText}</div>` : ""}
                </div>
                <div class="debt-mobile-entry-actions">
                  <button class="btn btn-secondary" type="button" data-add-debt-issuance-id="${debt.id}">+ Сумма</button>
                  <button class="btn btn-repay" type="button" data-repay-debt-id="${debt.id}" ${Number(debt.outstanding_total) <= 0 ? "disabled" : ""}>Погашение</button>
                </div>
              </article>
            `;
          }
          return `<tr class="debt-row-${dueState} debt-row-${direction} debt-record-row table-record-open-row" data-debt-row-id="${debt.id}">
            <td>${core.formatDateRu(debt.start_date)}</td>
            <td><span class="debt-direction-pill debt-direction-pill-${direction}">${directionLabel}</span></td>
            <td>${formatDebtAmountBlock(debt.principal, debt.currency || "BYN", debt.current_base_principal, debt.base_currency || "BYN", `debt-amount-principal debt-amount-principal-${direction}`)}</td>
            <td>${formatDebtAmountBlock(debt.repaid_total, debt.currency || "BYN", debt.current_base_repaid_total, debt.base_currency || "BYN", `debt-amount-repaid ${repaidClass}`)}</td>
            <td>
              ${formatDebtAmountBlock(debt.outstanding_total, debt.currency || "BYN", debt.current_base_outstanding_total, debt.base_currency || "BYN", `debt-amount-outstanding debt-amount-outstanding-${direction}`)}
              <div class="debt-repay-progress">
                <div class="debt-repay-progress-track">
                  <span class="debt-repay-progress-bar debt-repay-progress-bar-${repayProgress.tone}" style="width:${repayProgress.percent}%"></span>
                </div>
                <span class="muted-small">Погашено: ${repayProgress.percent}%</span>
              </div>
            </td>
            <td>
              <div class="row debt-due-head">
                <span class="muted-small">${debtDueLabel(dueState, debt.due_date)}</span>
                ${dueDays ? `<span class="debt-due-days-badge debt-due-days-badge-${dueState}">${dueDays}</span>` : ""}
              </div>
              ${
                dueProgress
                  ? `<div class="debt-due-progress"><div class="debt-due-progress-track"><span class="debt-due-progress-bar debt-due-progress-bar-${dueProgress.tone}" style="width:${dueProgress.percent}%"></span></div><span class="muted-small">Прогресс срока: ${dueProgress.percent}%</span></div>`
                  : ""
              }
              ${debtClosureMeta(debt)}
              ${noteText ? `<div class="muted-small">${noteText}</div>` : ""}
            </td>
            <td>
              <div class="debt-desktop-actions">
                <button class="btn btn-secondary btn-xs" type="button" data-add-debt-issuance-id="${debt.id}">+ Сумма</button>
                <button class="btn btn-repay btn-xs" type="button" data-repay-debt-id="${debt.id}" ${Number(debt.outstanding_total) <= 0 ? "disabled" : ""}>Погашение</button>
                ${core.renderInlineKebabMenu?.(
                  `debt-${debt.id}`,
                  `<button class="btn btn-secondary" type="button" data-history-debt-id="${debt.id}">Движения</button>
                  <button class="btn btn-secondary" type="button" data-add-debt-issuance-id="${debt.id}">Добавить сумму</button>
                  <button class="btn btn-secondary" type="button" data-activity-entity-type="debt" data-activity-entity-id="${debt.id}">Журнал</button>
                  <button class="btn btn-secondary" type="button" data-forgive-debt-id="${debt.id}" ${Number(debt.outstanding_total) <= 0 ? "disabled" : ""}>Простить</button>
                  <button class="btn btn-secondary" type="button" data-edit-debt-id="${debt.id}">Редактировать</button>
                  <button class="btn btn-danger" type="button" data-delete-debt-id="${debt.id}">Удалить</button>`,
                  "Действия долга",
                  "debt-row-kebab",
                ) || ""}
              </div>
            </td>
          </tr>`;
        })
        .join("");

      const closedDebtsCount = Number(card.closed_debts_count || 0);
      const closedDebtsExpanded = card.closed_debts_expanded === true;
      const debtRowsId = `debt-card-rows-${Number(card.counterparty_id || 0)}`;
      const closedDebtsToggle = (state.debtStatusFilter || "active") === "active" && closedDebtsCount > 0
        ? `<button class="btn btn-secondary btn-xs debt-closed-toggle" type="button"
            data-debt-closed-toggle-counterparty-id="${Number(card.counterparty_id || 0)}"
            aria-expanded="${closedDebtsExpanded ? "true" : "false"}"
            aria-controls="${debtRowsId}">${closedDebtsExpanded ? "Скрыть" : "Показать"} завершённые (${closedDebtsCount})</button>`
        : "";

      item.innerHTML = compactMobile
        ? `
          <div class="debt-mobile-card-head">
            <div class="debt-mobile-card-title-block">
              <h3>${core.highlightText(card.counterparty, searchQuery)}</h3>
              <span class="debt-status debt-status-${card.status}">${card.status === "active" ? "Активный" : "Закрыт"}</span>
              ${closedDebtsToggle}
            </div>
          </div>
          <div id="${debtRowsId}" class="debt-mobile-entries">${debtsRows}</div>
        `
        : `
          <div class="row between">
            <div>
              <h3>${core.highlightText(card.counterparty, searchQuery)}</h3>
              <p class="subtitle">Статус: <span class="debt-status debt-status-${card.status}">${card.status === "active" ? "Активный" : "Закрыт"}</span></p>
            </div>
            ${closedDebtsToggle}
          </div>
          <div id="${debtRowsId}" class="debt-card-children-wrap">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Направление</th>
                  <th>Сумма</th>
                  <th>Погашено</th>
                  <th>Остаток</th>
                  <th>Срок/Движения</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>${debtsRows}</tbody>
            </table>
          </div>
        `;
      el.debtsCards.appendChild(item);
    }
  }

  window.App.debtCardsRenderer = {
    isClosedDebt,
    renderDebtCards,
  };
})();
