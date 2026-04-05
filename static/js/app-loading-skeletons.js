(() => {
  const { el } = window.App;

  function line(widthClass = "skeleton-w-100", sizeClass = "") {
    return `<span class="skeleton-line ${sizeClass} ${widthClass}" aria-hidden="true"></span>`;
  }

  function inlineLine(widthClass = "skeleton-w-100", sizeClass = "") {
    return `<span class="skeleton-inline-host" aria-hidden="true">${line(widthClass, sizeClass)}</span>`;
  }

  function renderDashboardAnalyticsSkeleton() {
    if (el.dashboardAnalyticsPeriodLabel) {
      el.dashboardAnalyticsPeriodLabel.innerHTML = inlineLine("skeleton-w-72", "skeleton-line-sm");
    }
    if (el.dashboardKpiPrimary) {
      el.dashboardKpiPrimary.innerHTML = Array.from({ length: 4 }, () => `
        <article class="analytics-kpi-card skeleton-card-block skeleton-stack-md">
          ${line("skeleton-w-40", "skeleton-line-xs")}
          ${line("skeleton-w-72", "skeleton-line-lg")}
          ${line("skeleton-w-56", "skeleton-line-sm")}
          ${line("skeleton-w-48", "skeleton-line-sm")}
        </article>
      `).join("");
    }
    if (el.dashboardKpiSecondary) {
      el.dashboardKpiSecondary.innerHTML = Array.from({ length: 3 }, () => `<span class="skeleton-chip" aria-hidden="true"></span>`).join("");
    }
    if (el.dashboardStructurePeriodLabel) {
      el.dashboardStructurePeriodLabel.innerHTML = inlineLine("skeleton-w-80", "skeleton-line-sm");
    }
    if (el.dashboardCategoryBreakdownSvg) {
      el.dashboardCategoryBreakdownSvg.innerHTML = "";
    }
    if (el.dashboardCategoryBreakdownChart) {
      el.dashboardCategoryBreakdownChart.classList.add("dashboard-skeleton-chart");
    }
    if (el.dashboardCategoryBreakdownChartTitle) {
      el.dashboardCategoryBreakdownChartTitle.innerHTML = inlineLine("skeleton-w-40", "skeleton-line-xs");
    }
    if (el.dashboardCategoryBreakdownChartPeriod) {
      el.dashboardCategoryBreakdownChartPeriod.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-xs");
    }
    if (el.dashboardCategoryBreakdownChartValue) {
      el.dashboardCategoryBreakdownChartValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.dashboardCategoryBreakdownChartMeta) {
      el.dashboardCategoryBreakdownChartMeta.innerHTML = inlineLine("skeleton-w-64", "skeleton-line-xs");
    }
    if (el.dashboardCategoryBreakdownList) {
      el.dashboardCategoryBreakdownList.innerHTML = `
        <div class="dashboard-skeleton-list">
          ${Array.from({ length: 5 }, () => `
            <div class="dashboard-skeleton-list-item skeleton-card-block skeleton-stack-sm">
              ${line("skeleton-w-40", "skeleton-line-xs")}
              ${line("skeleton-w-80", "skeleton-line-sm")}
              ${line("skeleton-w-56", "skeleton-line-xs")}
            </div>
          `).join("")}
        </div>
      `;
    }
  }

  function clearDashboardAnalyticsSkeletonState() {
    el.dashboardCategoryBreakdownChart?.classList.remove("dashboard-skeleton-chart");
  }

  function renderDashboardDebtsSkeleton() {
    if (el.dashboardDebtKpiGrid) {
      el.dashboardDebtKpiGrid.classList.remove("hidden");
    }
    if (el.debtLendTotal) {
      el.debtLendTotal.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-money");
    }
    if (el.debtBorrowTotal) {
      el.debtBorrowTotal.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-money");
    }
    if (el.debtNetTotal) {
      el.debtNetTotal.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-money");
    }
    if (el.dashboardDebtsList) {
      el.dashboardDebtsList.innerHTML = `
        <div class="dashboard-skeleton-list">
          ${Array.from({ length: 2 }, () => `
            <article class="panel debt-card debt-card-compact dashboard-skeleton-debt-card skeleton-card-block">
              <div class="debt-card-compact-grid">
                <div class="debt-card-compact-col skeleton-stack-md">
                  ${line("skeleton-w-48", "skeleton-line-xs")}
                  ${line("skeleton-w-72", "skeleton-line-lg")}
                  ${line("skeleton-w-40", "skeleton-line-xs")}
                </div>
                <div class="debt-card-compact-col dashboard-skeleton-row-group">
                  ${Array.from({ length: 2 }, () => `
                    <div class="dashboard-skeleton-row skeleton-row-block skeleton-stack-sm">
                      ${line("skeleton-w-32", "skeleton-line-xs")}
                      ${line("skeleton-w-64", "skeleton-line-sm")}
                      ${line("skeleton-w-100", "skeleton-line-xs")}
                      ${line("skeleton-w-56", "skeleton-line-sm")}
                    </div>
                  `).join("")}
                </div>
              </div>
            </article>
          `).join("")}
        </div>
      `;
    }
  }

  function renderDashboardPlansSkeleton() {
    if (el.dashboardPlansPeriodLabel) {
      el.dashboardPlansPeriodLabel.innerHTML = inlineLine("skeleton-w-64", "skeleton-line-sm");
    }
    if (el.dashboardPlansKpi) {
      el.dashboardPlansKpi.innerHTML = Array.from({ length: 4 }, () => `<span class="skeleton-chip" aria-hidden="true"></span>`).join("");
    }
    if (el.dashboardPlansList) {
      el.dashboardPlansList.innerHTML = `
        <div class="dashboard-skeleton-list">
          ${Array.from({ length: 3 }, () => `
            <article class="panel skeleton-card-block skeleton-stack-md dashboard-skeleton-list-item">
              ${line("skeleton-w-48", "skeleton-line-xs")}
              ${line("skeleton-w-72", "skeleton-line-lg")}
              ${line("skeleton-w-56", "skeleton-line-sm")}
              ${line("skeleton-w-100", "skeleton-line-xs")}
            </article>
          `).join("")}
        </div>
      `;
    }
  }

  function renderDashboardCurrencySkeleton() {
    if (el.dashboardCurrencyBalances) {
      el.dashboardCurrencyBalances.innerHTML = Array.from({ length: 3 }, () => `
        <article class="currency-balance-card skeleton-card-block skeleton-stack-md">
          ${line("skeleton-w-40", "skeleton-line-xs")}
          ${line("skeleton-w-56", "skeleton-line-lg")}
          ${line("skeleton-w-80", "skeleton-line-sm")}
          ${line("skeleton-w-72", "skeleton-line-sm")}
        </article>
      `).join("");
    }
    if (el.dashboardCurrencyRates) {
      el.dashboardCurrencyRates.innerHTML = Array.from({ length: 2 }, () => `
        <article class="dashboard-currency-rate-card skeleton-card-block skeleton-stack-md">
          ${line("skeleton-w-32", "skeleton-line-xs")}
          ${line("skeleton-w-48", "skeleton-line-lg")}
          ${line("skeleton-w-64", "skeleton-line-sm")}
          ${line("skeleton-w-56", "skeleton-line-xs")}
          ${line("skeleton-w-32", "skeleton-line-sm")}
        </article>
      `).join("");
    }
    if (el.dashboardCurrencyPositions) {
      el.dashboardCurrencyPositions.innerHTML = Array.from({ length: 5 }, () => `<span class="skeleton-chip" aria-hidden="true"></span>`).join("");
    }
  }

  function renderPlansSectionSkeleton() {
    if (el.plansDueChip) {
      el.plansDueChip.innerHTML = inlineLine("skeleton-w-64", "skeleton-line-sm");
    }
    if (el.plansTodayChip) {
      el.plansTodayChip.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-sm");
    }
    if (el.plansOverdueChip) {
      el.plansOverdueChip.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-sm");
    }
    if (el.plansFinancialValue) {
      el.plansFinancialValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.plansFinancialDelta) {
      el.plansFinancialDelta.innerHTML = inlineLine("skeleton-w-40", "skeleton-line-sm");
      el.plansFinancialDelta.classList.remove(
        "plans-financial-kpi-delta-positive",
        "plans-financial-kpi-delta-negative",
        "plans-financial-kpi-delta-neutral",
      );
    }
    if (el.plansFinancialMeta) {
      el.plansFinancialMeta.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-sm");
    }
    if (el.plansList) {
      el.plansList.innerHTML = `
        <div class="plans-skeleton-list">
          ${Array.from({ length: 4 }, () => `
            <article class="panel skeleton-card-block skeleton-stack-lg plans-skeleton-card">
              <div class="plans-skeleton-head">
                <div class="skeleton-stack-sm">
                  ${line("skeleton-w-56", "skeleton-line-sm")}
                  ${line("skeleton-w-40", "skeleton-line-xs")}
                </div>
                <span class="skeleton-chip" aria-hidden="true"></span>
              </div>
              <div class="plans-skeleton-fields">
                ${Array.from({ length: 4 }, () => `
                  <div class="skeleton-stack-sm">
                    ${line("skeleton-w-32", "skeleton-line-xs")}
                    ${line("skeleton-w-64", "skeleton-line-sm")}
                  </div>
                `).join("")}
              </div>
              <div class="skeleton-stack-sm">
                ${line("skeleton-w-72", "skeleton-line-sm")}
                ${line("skeleton-w-100", "skeleton-line-xs")}
              </div>
            </article>
          `).join("")}
        </div>
      `;
    }
  }

  function renderAnalyticsStructureSkeleton() {
    if (el.analyticsCategoryBreakdownLabel) {
      el.analyticsCategoryBreakdownLabel.innerHTML = inlineLine("skeleton-w-72", "skeleton-line-sm");
    }
    if (el.analyticsCategoryBreakdownSvg) {
      el.analyticsCategoryBreakdownSvg.innerHTML = "";
    }
    if (el.analyticsCategoryBreakdownChart) {
      el.analyticsCategoryBreakdownChart.classList.add("dashboard-skeleton-chart");
    }
    if (el.analyticsCategoryBreakdownChartTitle) {
      el.analyticsCategoryBreakdownChartTitle.innerHTML = inlineLine("skeleton-w-40", "skeleton-line-xs");
    }
    if (el.analyticsCategoryBreakdownChartPeriod) {
      el.analyticsCategoryBreakdownChartPeriod.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-xs");
    }
    if (el.analyticsCategoryBreakdownChartValue) {
      el.analyticsCategoryBreakdownChartValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsCategoryBreakdownChartMeta) {
      el.analyticsCategoryBreakdownChartMeta.innerHTML = inlineLine("skeleton-w-64", "skeleton-line-xs");
    }
    if (el.analyticsCategoryBreakdownList) {
      el.analyticsCategoryBreakdownList.innerHTML = `
        <div class="dashboard-skeleton-list">
          ${Array.from({ length: 6 }, () => `
            <div class="dashboard-skeleton-list-item skeleton-card-block skeleton-stack-sm">
              ${line("skeleton-w-48", "skeleton-line-xs")}
              ${line("skeleton-w-80", "skeleton-line-sm")}
              ${line("skeleton-w-56", "skeleton-line-xs")}
            </div>
          `).join("")}
        </div>
      `;
    }
  }

  function clearAnalyticsStructureSkeletonState() {
    el.analyticsCategoryBreakdownChart?.classList.remove("dashboard-skeleton-chart");
  }

  function renderAnalyticsCalendarSkeleton() {
    if (el.analyticsCalendarTotalsTitle) {
      el.analyticsCalendarTotalsTitle.innerHTML = inlineLine("skeleton-w-40", "skeleton-line-lg");
    }
    if (el.analyticsCalendarTotalsRangeLabel) {
      el.analyticsCalendarTotalsRangeLabel.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-sm");
    }
    if (el.analyticsCalendarTotals) {
      el.analyticsCalendarTotals.innerHTML = Array.from({ length: 4 }, () => `
        <article class="analytics-kpi-card skeleton-card-block skeleton-stack-md">
          ${line("skeleton-w-40", "skeleton-line-xs")}
          ${line("skeleton-w-64", "skeleton-line-lg")}
        </article>
      `).join("");
    }
    if (el.analyticsCalendarTotalsSecondary) {
      el.analyticsCalendarTotalsSecondary.innerHTML = Array.from({ length: 2 }, () => `<span class="skeleton-chip" aria-hidden="true"></span>`).join("");
    }
    if (el.analyticsMonthGridWrap) {
      el.analyticsMonthGridWrap.classList.remove("hidden");
    }
    if (el.analyticsYearGridWrap) {
      el.analyticsYearGridWrap.classList.add("hidden");
    }
    if (el.analyticsCalendarBody) {
      el.analyticsCalendarBody.innerHTML = Array.from({ length: 5 }, () => `
        <tr>
          ${Array.from({ length: 11 }, () => `
            <td><div class="skeleton-row-block analytics-calendar-skeleton-cell"></div></td>
          `).join("")}
        </tr>
      `).join("");
    }
  }

  function renderAnalyticsTrendSkeleton() {
    if (el.analyticsTrendRangeLabel) {
      el.analyticsTrendRangeLabel.innerHTML = inlineLine("skeleton-w-72", "skeleton-line-sm");
    }
    if (el.analyticsTrendChart) {
      el.analyticsTrendChart.classList.add("analytics-trend-chart-skeleton");
      el.analyticsTrendChart.innerHTML = `
        <defs>
          <linearGradient id="analyticsTrendSkeletonFill" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="rgba(72, 92, 128, 0.18)" />
            <stop offset="45%" stop-color="rgba(232, 239, 255, 0.14)" />
            <stop offset="100%" stop-color="rgba(72, 92, 128, 0.18)" />
            <animateTransform
              attributeName="gradientTransform"
              type="translate"
              from="-1 0"
              to="1 0"
              dur="1.4s"
              repeatCount="indefinite"
            />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="980" height="280" rx="18" fill="rgba(57, 74, 104, 0.12)"></rect>
        ${Array.from({ length: 8 }, (_, idx) => `
          <rect
            x="${idx * 122 + 14}"
            y="24"
            width="94"
            height="232"
            rx="14"
            fill="rgba(108, 167, 255, 0.06)"
          ></rect>
        `).join("")}
        <rect x="0" y="146" width="980" height="2" fill="rgba(141,160,190,0.28)"></rect>
        <path
          d="M 20 170 C 120 150, 180 110, 280 132 S 460 200, 580 144 S 760 92, 960 126"
          fill="none"
          stroke="url(#analyticsTrendSkeletonFill)"
          stroke-width="8"
          stroke-linecap="round"
        ></path>
      `;
    }
    if (el.analyticsIncomeDelta) {
      el.analyticsIncomeDelta.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsExpenseDelta) {
      el.analyticsExpenseDelta.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsBalanceDelta) {
      el.analyticsBalanceDelta.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsOpsDelta) {
      el.analyticsOpsDelta.innerHTML = inlineLine("skeleton-w-32", "skeleton-line-lg");
    }
  }

  function clearAnalyticsTrendSkeletonState() {
    el.analyticsTrendChart?.classList.remove("analytics-trend-chart-skeleton");
  }

  function renderDebtsSectionSkeleton() {
    if (el.deleteAllDebtsBtn) {
      el.deleteAllDebtsBtn.disabled = true;
    }
    if (el.debtsCards) {
      el.debtsCards.innerHTML = `
        <div class="debts-skeleton-list">
          ${Array.from({ length: 3 }, () => `
            <article class="panel debts-skeleton-card skeleton-card-block skeleton-stack-lg">
              <div class="skeleton-stack-sm">
                ${line("skeleton-w-32", "skeleton-line-xs")}
                ${line("skeleton-w-48", "skeleton-line-lg")}
              </div>
              <div class="debts-skeleton-row-group">
                ${Array.from({ length: 2 }, () => `
                  <div class="debts-skeleton-row skeleton-row-block skeleton-stack-sm">
                    ${line("skeleton-w-24", "skeleton-line-xs")}
                    ${line("skeleton-w-40", "skeleton-line-sm")}
                    ${line("skeleton-w-100", "skeleton-line-xs")}
                    ${line("skeleton-w-56", "skeleton-line-sm")}
                  </div>
                `).join("")}
              </div>
            </article>
          `).join("")}
        </div>
      `;
    }
  }

  function renderOperationsSectionSkeleton() {
    if (el.operationsPeriodLabel) {
      el.operationsPeriodLabel.innerHTML = inlineLine("skeleton-w-56", "skeleton-line-sm");
    }
    if (el.operationsIncomeTotal) {
      el.operationsIncomeTotal.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.operationsExpenseTotal) {
      el.operationsExpenseTotal.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.operationsBalanceTotal) {
      el.operationsBalanceTotal.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.operationsTotalCount) {
      el.operationsTotalCount.innerHTML = inlineLine("skeleton-w-32", "skeleton-line-lg");
    }
    if (el.deleteAllOperationsBtn) {
      el.deleteAllOperationsBtn.disabled = true;
    }
    if (el.operationsBody) {
      el.operationsBody.innerHTML = Array.from({ length: 7 }, () => `
        <tr class="operations-skeleton-row">
          <td><div class="skeleton-row-block operations-skeleton-cell operations-skeleton-checkbox"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell operations-skeleton-action"></div></td>
        </tr>
      `).join("");
    }
  }

  function renderCurrencySectionSkeleton() {
    if (el.currencySummaryCurrentValue) {
      el.currencySummaryCurrentValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.currencySummaryBookValue) {
      el.currencySummaryBookValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.currencySummaryResultValue) {
      el.currencySummaryResultValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.currencySummaryRealizedValue) {
      el.currencySummaryRealizedValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.currencySummaryCombinedValue) {
      el.currencySummaryCombinedValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.currencySummaryActiveCount) {
      el.currencySummaryActiveCount.innerHTML = inlineLine("skeleton-w-24", "skeleton-line-lg");
    }
    if (el.currencyPerformanceRangeLabel) {
      el.currencyPerformanceRangeLabel.innerHTML = inlineLine("skeleton-w-72", "skeleton-line-sm");
    }
    if (el.currencyPerformanceChart) {
      el.currencyPerformanceChart.classList.add("analytics-trend-chart-skeleton");
      el.currencyPerformanceChart.innerHTML = `
        <defs>
          <linearGradient id="currencyPerformanceSkeletonFill" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="rgba(72, 92, 128, 0.18)" />
            <stop offset="45%" stop-color="rgba(232, 239, 255, 0.14)" />
            <stop offset="100%" stop-color="rgba(72, 92, 128, 0.18)" />
            <animateTransform
              attributeName="gradientTransform"
              type="translate"
              from="-1 0"
              to="1 0"
              dur="1.4s"
              repeatCount="indefinite"
            />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="980" height="280" rx="18" fill="rgba(57, 74, 104, 0.12)"></rect>
        <path
          d="M 20 188 C 130 170, 230 112, 360 136 S 600 214, 720 160 S 860 116, 960 128"
          fill="none"
          stroke="url(#currencyPerformanceSkeletonFill)"
          stroke-width="8"
          stroke-linecap="round"
        ></path>
      `;
    }
    if (el.currencyBalancesRow) {
      el.currencyBalancesRow.innerHTML = Array.from({ length: 3 }, () => `
        <article class="currency-balance-card skeleton-card-block skeleton-stack-md">
          ${line("skeleton-w-32", "skeleton-line-xs")}
          ${line("skeleton-w-48", "skeleton-line-lg")}
          ${line("skeleton-w-80", "skeleton-line-sm")}
        </article>
      `).join("");
    }
    if (el.currencyPositionsList) {
      el.currencyPositionsList.innerHTML = `
        <div class="plans-skeleton-list">
          ${Array.from({ length: 2 }, () => `
            <article class="panel skeleton-card-block skeleton-stack-lg plans-skeleton-card">
              <div class="plans-skeleton-head">
                <div class="skeleton-stack-sm">
                  ${line("skeleton-w-40", "skeleton-line-sm")}
                  ${line("skeleton-w-56", "skeleton-line-xs")}
                </div>
                <span class="skeleton-chip" aria-hidden="true"></span>
              </div>
              <div class="analytics-kpi-grid">
                ${Array.from({ length: 6 }, () => `
                  <article class="analytics-kpi-card skeleton-card-block skeleton-stack-sm">
                    ${line("skeleton-w-40", "skeleton-line-xs")}
                    ${line("skeleton-w-56", "skeleton-line-lg")}
                  </article>
                `).join("")}
              </div>
            </article>
          `).join("")}
        </div>
      `;
    }
    if (el.currencyTradesBody) {
      el.currencyTradesBody.innerHTML = Array.from({ length: 6 }, () => `
        <tr class="operations-skeleton-row">
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell operations-skeleton-action"></div></td>
        </tr>
      `).join("");
    }
    if (el.currencyTradesInfiniteSentinel) {
      el.currencyTradesInfiniteSentinel.classList.add("hidden");
    }
  }

  function clearCurrencySectionSkeletonState() {
    el.currencyPerformanceChart?.classList.remove("analytics-trend-chart-skeleton");
  }

  function renderAnalyticsCurrencySkeleton() {
    if (el.analyticsCurrencyRangeLabel) {
      el.analyticsCurrencyRangeLabel.innerHTML = inlineLine("skeleton-w-72", "skeleton-line-sm");
    }
    if (el.analyticsCurrencyCurrentValue) {
      el.analyticsCurrencyCurrentValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsCurrencyBookValue) {
      el.analyticsCurrencyBookValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsCurrencyResultValue) {
      el.analyticsCurrencyResultValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsCurrencyRealizedValue) {
      el.analyticsCurrencyRealizedValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsCurrencyCombinedValue) {
      el.analyticsCurrencyCombinedValue.innerHTML = inlineLine("skeleton-w-48", "skeleton-line-money");
    }
    if (el.analyticsCurrencyActiveCount) {
      el.analyticsCurrencyActiveCount.innerHTML = inlineLine("skeleton-w-24", "skeleton-line-lg");
    }
    if (el.analyticsCurrencyBalancesRow) {
      el.analyticsCurrencyBalancesRow.innerHTML = Array.from({ length: 3 }, () => `
        <article class="currency-balance-card skeleton-card-block skeleton-stack-md">
          ${line("skeleton-w-32", "skeleton-line-xs")}
          ${line("skeleton-w-48", "skeleton-line-lg")}
          ${line("skeleton-w-80", "skeleton-line-sm")}
        </article>
      `).join("");
    }
    if (el.analyticsCurrencySecondary) {
      el.analyticsCurrencySecondary.innerHTML = Array.from({ length: 4 }, () => `<span class="skeleton-chip" aria-hidden="true"></span>`).join("");
    }
    if (el.analyticsCurrencyChart) {
      el.analyticsCurrencyChart.classList.add("analytics-trend-chart-skeleton");
      el.analyticsCurrencyChart.innerHTML = `
        <defs>
          <linearGradient id="analyticsCurrencySkeletonFill" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="rgba(72, 92, 128, 0.18)" />
            <stop offset="45%" stop-color="rgba(232, 239, 255, 0.14)" />
            <stop offset="100%" stop-color="rgba(72, 92, 128, 0.18)" />
            <animateTransform
              attributeName="gradientTransform"
              type="translate"
              from="-1 0"
              to="1 0"
              dur="1.4s"
              repeatCount="indefinite"
            />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="980" height="280" rx="18" fill="rgba(57, 74, 104, 0.12)"></rect>
        ${Array.from({ length: 2 }, (_, idx) => `
          <path
            d="${idx === 0 ? "M 20 188 C 130 170, 230 112, 360 136 S 600 214, 720 160 S 860 116, 960 128" : "M 20 154 C 150 134, 250 172, 380 148 S 620 104, 760 126 S 880 154, 960 118"}"
            fill="none"
            stroke="url(#analyticsCurrencySkeletonFill)"
            stroke-width="${idx === 0 ? "8" : "6"}"
            stroke-linecap="round"
          ></path>
        `).join("")}
      `;
    }
    if (el.analyticsCurrencyTradesBody) {
      el.analyticsCurrencyTradesBody.innerHTML = Array.from({ length: 6 }, () => `
        <tr class="operations-skeleton-row">
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
          <td><div class="skeleton-row-block operations-skeleton-cell"></div></td>
        </tr>
      `).join("");
    }
    if (el.analyticsCurrencyTradesInfiniteSentinel) {
      el.analyticsCurrencyTradesInfiniteSentinel.classList.add("hidden");
    }
  }

  function clearAnalyticsCurrencySkeletonState() {
    el.analyticsCurrencyChart?.classList.remove("analytics-trend-chart-skeleton");
  }

  const api = {
    renderDashboardAnalyticsSkeleton,
    clearDashboardAnalyticsSkeletonState,
    renderDashboardDebtsSkeleton,
    renderDashboardPlansSkeleton,
    renderDashboardCurrencySkeleton,
    renderPlansSectionSkeleton,
    renderDebtsSectionSkeleton,
    renderOperationsSectionSkeleton,
    renderCurrencySectionSkeleton,
    clearCurrencySectionSkeletonState,
    renderAnalyticsStructureSkeleton,
    clearAnalyticsStructureSkeletonState,
    renderAnalyticsCalendarSkeleton,
    renderAnalyticsTrendSkeleton,
    clearAnalyticsTrendSkeletonState,
    renderAnalyticsCurrencySkeleton,
    clearAnalyticsCurrencySkeletonState,
  };

  window.App.registerRuntimeModule?.("loading-skeletons", api);
})();
