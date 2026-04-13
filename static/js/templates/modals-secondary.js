(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.modalsSecondary = `

    <div id="periodCustomModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="periodCustomTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="periodCustomTitle">Настроить период</h3>
          <button id="closePeriodCustomModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="periodCustomForm" class="category-modal-form">
          <input id="customPeriodMode" type="hidden" value="day" />
          <div id="periodCustomModeTabs" class="segmented period-custom-mode-tabs" role="tablist" aria-label="Режим настройки периода">
            <button class="segmented-btn active" data-period-custom-mode="day" type="button">День</button>
            <button class="segmented-btn" data-period-custom-mode="range" type="button">Диапазон</button>
          </div>
          <div id="customDayField" class="period-custom-field">
            <div class="field-head row between">
              <span class="muted-small">Дата</span>
              <button id="customDayTodayBtn" class="btn btn-secondary btn-xs" type="button">Сегодня</button>
            </div>
            <div class="date-input-wrap">
              <input id="customDayDate" class="input" type="date" aria-label="Дата периода" />
              <button class="date-input-trigger" type="button" data-date-picker-trigger="customDayDate" aria-label="Открыть календарь"></button>
            </div>
          </div>
          <div id="customRangeFields" class="period-custom-range-fields hidden">
            <div class="period-custom-field">
              <span class="muted-small">С даты</span>
              <div class="date-input-wrap">
                <input id="customDateFrom" class="input" type="date" aria-label="Дата начала периода" required />
                <button class="date-input-trigger" type="button" data-date-picker-trigger="customDateFrom" aria-label="Открыть календарь"></button>
              </div>
            </div>
            <div class="period-custom-field">
              <span class="muted-small">По дату</span>
              <div class="date-input-wrap">
                <input id="customDateTo" class="input" type="date" aria-label="Дата окончания периода" required />
                <button class="date-input-trigger" type="button" data-date-picker-trigger="customDateTo" aria-label="Открыть календарь"></button>
              </div>
            </div>
          </div>
        </form>
        <div class="modal-footer">
          <button id="submitPeriodCustomBtn" class="btn btn-cta modal-main-cta" type="submit" form="periodCustomForm">
            Показать день
          </button>
        </div>
      </div>
    </div>

    <div id="debtRepaymentModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="debtRepaymentTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="debtRepaymentTitle">Внести погашение</h3>
          <button id="closeDebtRepaymentModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="debtRepaymentForm" class="category-modal-form">
          <input id="repaymentDebtId" type="hidden" />
          <div class="repayment-card">
            <div class="repayment-head row between">
              <div>
                <div id="repaymentCounterparty" class="repayment-counterparty">Контрагент</div>
                <div id="repaymentDirection" class="debt-direction-pill debt-direction-pill-lend">Я дал</div>
              </div>
              <div class="repayment-outstanding">
                <span class="muted-small">Остаток</span>
                <strong id="repaymentOutstanding">0.00</strong>
              </div>
            </div>
            <div class="repayment-progress">
              <div id="repaymentProgressBar" class="repayment-progress-bar"></div>
            </div>
          </div>
          <div id="repaymentPresetRow" class="repayment-preset-row">
            <button class="btn btn-secondary btn-xs" type="button" data-repayment-preset="0.25">25%</button>
            <button class="btn btn-secondary btn-xs" type="button" data-repayment-preset="0.5">50%</button>
            <button class="btn btn-secondary btn-xs" type="button" data-repayment-preset="1">Весь остаток</button>
          </div>
          <div id="repaymentAmountField" class="money-input-wrap" data-money-input-wrap>
            <input id="repaymentAmount" data-money-input type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Сумма" title="Можно вводить выражения: 1000+250/2" required />
          </div>
          <div class="repayment-delta-box">
            <div class="muted-small">До: <span id="repaymentBeforeValue">0.00</span></div>
            <div class="muted-small">После: <span id="repaymentAfterValue">0.00</span></div>
            <div id="repaymentCarryRow" class="muted-small hidden">Перенос: <span id="repaymentCarryValue">0.00</span></div>
          </div>
          <div class="date-input-wrap">
            <input id="repaymentDate" class="input" type="date" aria-label="Дата погашения" required />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="repaymentDate" aria-label="Открыть календарь"></button>
          </div>
          <input id="repaymentNote" type="text" placeholder="Комментарий" />
        </form>
        <div class="modal-footer">
          <button id="forgiveDebtFromRepaymentBtn" class="btn btn-secondary" type="button">
            Простить остаток
          </button>
          <button id="submitDebtRepaymentBtn" class="btn btn-cta modal-main-cta" type="submit" form="debtRepaymentForm">
            Сохранить погашение
          </button>
        </div>
      </div>
    </div>

    <div id="debtHistoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="debtHistoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="debtHistoryTitle">История долга</h3>
          <button id="closeDebtHistoryModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <div class="debt-history-head">
          <div class="row between">
            <div id="debtHistoryCounterparty" class="repayment-counterparty">Контрагент</div>
            <span id="debtHistoryDirection" class="debt-direction-pill debt-direction-pill-lend">Я дал</span>
          </div>
          <div class="subtitle">Остаток: <strong id="debtHistoryOutstanding">0.00</strong></div>
        </div>
        <div id="debtHistoryList" class="debt-history-list">
          <div id="debtHistoryItems" class="debt-history-items"></div>
          <div id="debtHistoryInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
        </div>
      </div>
    </div>

    <div id="debtForgivenessModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="debtForgivenessTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="debtForgivenessTitle">Простить долг</h3>
          <button id="closeDebtForgivenessModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="debtForgivenessForm" class="category-modal-form">
          <input id="forgivenessDebtId" type="hidden" />
          <div class="repayment-card">
            <div class="repayment-head row between">
              <div>
                <div id="forgivenessCounterparty" class="repayment-counterparty">Контрагент</div>
                <div id="forgivenessDirection" class="debt-direction-pill debt-direction-pill-lend">Я дал</div>
              </div>
              <div class="repayment-outstanding">
                <span class="muted-small">Остаток</span>
                <strong id="forgivenessOutstanding">0.00</strong>
              </div>
            </div>
            <div id="forgivenessContextHint" class="subtitle">Списание закроет долг без выплаты</div>
          </div>
          <div id="forgivenessAmountField" class="money-input-wrap" data-money-input-wrap>
            <input id="forgivenessAmount" data-money-input type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Сумма прощения" title="Можно вводить выражения: 1000+250/2" required />
          </div>
          <div class="date-input-wrap">
            <input id="forgivenessDate" class="input" type="date" aria-label="Дата прощения" required />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="forgivenessDate" aria-label="Открыть календарь"></button>
          </div>
          <input id="forgivenessNote" type="text" placeholder="Комментарий" />
        </form>
        <div class="modal-footer">
          <button id="submitDebtForgivenessBtn" class="btn btn-danger modal-main-cta" type="submit" form="debtForgivenessForm">
            Простить долг
          </button>
        </div>
      </div>
    </div>

    <div id="operationReceiptModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="operationReceiptTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="operationReceiptTitle">Позиции чека</h3>
          <button id="closeOperationReceiptModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <div id="operationReceiptMeta" class="subtitle">—</div>
        <div id="operationReceiptItems" class="operation-receipt-items"></div>
      </div>
    </div>

    <div id="confirmModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="confirmTitle">
      <div class="modal-card modal-small">
        <div class="panel-head">
          <h3 id="confirmTitle">Подтверждение удаления</h3>
        </div>
        <p id="confirmText" class="subtitle">Вы уверены, что хотите удалить объект?</p>
        <div class="row confirm-actions">
          <button id="confirmCancelBtn" class="btn btn-secondary" type="button">Отмена</button>
          <button id="confirmDeleteBtn" class="btn btn-danger" type="button">Удалить</button>
        </div>
      </div>
    </div>

    <div id="settingsPickerModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="settingsPickerTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="settingsPickerTitle">Выбор значения</h3>
          <button id="closeSettingsPickerModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <div id="settingsPickerOptions" class="settings-picker-options"></div>
      </div>
    </div>
  `;
})();
