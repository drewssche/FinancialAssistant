(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.modals = `

    <div id="createModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="createTitle">
      <div class="modal-card">
        <div class="panel-head row between">
          <h3 id="createTitle">Новая операция</h3>
          <button id="closeCreateModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>

        <form id="createOperationForm" class="form-grid modal-grid create-modal-grid">
          <div class="segmented" id="createEntryModeSwitch" aria-label="Режим создания">
            <button class="segmented-btn active" data-entry-mode="operation" type="button">Обычная операция</button>
            <button class="segmented-btn" data-entry-mode="debt" type="button">Долг</button>
          </div>
          <input id="opEntryMode" type="hidden" value="operation" />
          <div class="segmented" id="createOperationModeSwitch" aria-label="Формат операции">
            <button class="segmented-btn active" data-operation-mode="common" type="button">Общая</button>
            <button class="segmented-btn" data-operation-mode="receipt" type="button">Чек</button>
          </div>
          <input id="opOperationMode" type="hidden" value="common" />
          <div id="opDateField" class="date-input-wrap">
            <input id="opDate" class="input" type="date" aria-label="Дата операции" required />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="opDate" aria-label="Открыть календарь"></button>
          </div>
          <div class="segmented" id="createKindSwitch" aria-label="Тип операции">
            <button class="segmented-btn active" data-kind="expense" type="button">Расход</button>
            <button class="segmented-btn" data-kind="income" type="button">Доход</button>
          </div>
          <input id="opKind" type="hidden" value="expense" />
          <select id="opCategory" class="hidden"></select>
          <div id="createCategoryField" class="create-category-field">
            <input id="opCategorySearch" type="text" placeholder="Категория" autocomplete="off" />
            <div id="createCategoryPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="opCategoryAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <div id="opAmountField" class="money-input-wrap" data-money-input-wrap>
            <input id="opAmount" data-money-input type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Сумма" title="Можно вводить выражения: 1000+250/2" required />
          </div>
          <input id="opNote" class="create-note-field" type="text" placeholder="Комментарий" />

          <div id="opReceiptBlock" class="receipt-block">
            <div id="opReceiptFields" class="hidden">
              <div id="receiptItemsList" class="receipt-items-list"></div>
              <div class="receipt-summary">
                <div class="muted-small">Сумма чека: <strong id="receiptTotalValue">0.00</strong></div>
                <div class="muted-small">Расхождение: <strong id="receiptDiffValue">0.00</strong></div>
                <button id="pullReceiptTotalBtn" class="btn btn-secondary" type="button">Подтянуть сумму из чека</button>
              </div>
            </div>
          </div>

          <div id="createDebtFields" class="category-modal-form hidden">
            <div id="debtStartDateField" class="date-input-wrap">
              <input id="debtStartDate" class="input" type="date" aria-label="Дата начала долга" />
              <button class="date-input-trigger" type="button" data-date-picker-trigger="debtStartDate" aria-label="Открыть календарь"></button>
            </div>
            <div class="segmented" id="createDebtDirectionSwitch" aria-label="Направление долга">
              <button class="segmented-btn active" data-debt-direction="lend" type="button">Я дал</button>
              <button class="segmented-btn" data-debt-direction="borrow" type="button">Я взял</button>
            </div>
            <input id="debtDirection" type="hidden" value="lend" />
            <div id="debtCounterpartyField" class="create-category-field">
              <input id="debtCounterparty" type="text" placeholder="Имя контрагента" autocomplete="off" />
              <div id="debtCounterpartyPickerBlock" class="operation-category-picker app-popover hidden">
                <div class="category-picker-block">
                  <div id="debtCounterpartyAll" class="category-chip-list"></div>
                </div>
              </div>
            </div>
            <div id="debtPrincipalField" class="money-input-wrap" data-money-input-wrap>
              <input id="debtPrincipal" data-money-input type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Сумма" title="Можно вводить выражения: 1000+250/2" />
            </div>
            <div id="debtDueField" class="debt-due-field">
              <div id="debtDueDateField" class="date-input-wrap">
                <input id="debtDueDate" class="input" type="date" aria-label="Срок долга" />
                <button class="date-input-trigger" type="button" data-date-picker-trigger="debtDueDate" aria-label="Открыть календарь"></button>
              </div>
              <span id="debtDueHint" class="muted-small debt-due-inline-hint">Без срока</span>
            </div>
            <input id="debtNote" type="text" placeholder="Комментарий" class="create-note-field" />
          </div>
        </form>
        <div class="preview-panel">
          <div class="preview-title">Превью строки в таблице</div>
            <div class="table-wrap">
              <table class="table table-hover">
                <thead>
                <tr id="createPreviewHeadOperation">
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Категория</th>
                  <th>Сумма</th>
                  <th>Комментарий</th>
                </tr>
                <tr id="createPreviewHeadDebt" class="hidden">
                  <th>Дата</th>
                  <th>Направление</th>
                  <th>Контрагент</th>
                  <th>Сумма</th>
                  <th>Срок</th>
                  <th>Комментарий</th>
                </tr>
              </thead>
              <tbody id="createPreviewBody"></tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer">
          <button id="submitCreateOperationBtn" class="btn btn-cta modal-main-cta" type="submit" form="createOperationForm">
            Добавить
          </button>
        </div>
      </div>
    </div>

    <div id="batchCreateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="batchCreateTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="batchCreateTitle">Массовое добавление операций</h3>
          <button id="closeBatchCreateModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="batchCreateForm" class="category-modal-form">
          <p class="subtitle">Одна строка: <code>дата;тип;[группа];[категория];сумма;комментарий</code>.</p>
          <p id="batchCreateHint" class="muted-small">Дата: <code>ДД.ММ.ГГГГ</code>. Тип: расход/доход или expense/income. Группа и категория опциональны, пустые значения можно оставить как <code>;;</code>. Сумма: <code>01,23</code> или <code>01.23</code>. Комментарий опционален и не должен содержать <code>;</code>.</p>
          <textarea id="batchCreateInput" rows="8" placeholder="04.03.2026;Расход;Транспорт;Такси;150,50;Поездка&#10;05.03.2026;Доход;;;1000;Аванс"></textarea>
          <div id="batchCreateFeedback" class="status-box hidden"></div>
          <div id="batchCreatePreview" class="bulk-import-preview hidden">
            <div class="preview-title">Предпросмотр строк</div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Дата</th>
                    <th>Тип</th>
                    <th>Группа</th>
                    <th>Категория</th>
                    <th>Сумма</th>
                    <th>Комментарий</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody id="batchCreatePreviewBody"></tbody>
              </table>
            </div>
          </div>
        </form>
        <div class="modal-footer">
          <button id="previewBatchCreateBtn" class="btn btn-secondary" type="submit" form="batchCreateForm">
            Проверить строки
          </button>
          <button id="confirmBatchCreateBtn" class="btn btn-cta modal-main-cta hidden" type="button">
            Импортировать 0 строк
          </button>
        </div>
      </div>
    </div>

    <div id="batchCategoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="batchCategoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="batchCategoryTitle">Массовое добавление категорий и групп</h3>
          <button id="closeBatchCategoryModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="batchCategoryForm" class="category-modal-form">
          <div class="segmented" id="batchCategoryModeTabs" aria-label="Режим массового добавления категорий">
            <button class="segmented-btn active" data-batch-category-mode="categories" type="button">Категории</button>
            <button class="segmented-btn" data-batch-category-mode="groups" type="button">Группы</button>
          </div>
          <input id="batchCategoryMode" type="hidden" value="categories" />
          <p id="batchCategoryHint" class="subtitle">Категории: <code>тип;название;группа</code>. Пустая группа = «Без группы».</p>
          <textarea id="batchCategoryInput" rows="8" placeholder="Расход;Такси;Транспорт&#10;Доход;Подработка;"></textarea>
          <div id="batchCategoryFeedback" class="status-box hidden"></div>
          <div id="batchCategoryPreview" class="bulk-import-preview hidden">
            <div class="preview-title">Предпросмотр строк</div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Тип</th>
                    <th>Название</th>
                    <th>Группа</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody id="batchCategoryPreviewBody"></tbody>
              </table>
            </div>
          </div>
        </form>
        <div class="modal-footer">
          <button id="previewBatchCategoryBtn" class="btn btn-secondary" type="submit" form="batchCategoryForm">
            Проверить строки
          </button>
          <button id="confirmBatchCategoryBtn" class="btn btn-cta modal-main-cta hidden" type="button">
            Импортировать 0 строк
          </button>
        </div>
      </div>
    </div>

    <div id="bulkEditOperationsModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="bulkEditOperationsTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="bulkEditOperationsTitle">Массовое редактирование операций</h3>
          <button id="closeBulkEditOperationsModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="bulkEditOperationsForm" class="category-modal-form">
          <select id="bulkOpKind">
            <option value="">Тип (не менять)</option>
            <option value="expense">Расход</option>
            <option value="income">Доход</option>
          </select>
          <select id="bulkOpCategory">
            <option value="">Категория (не менять)</option>
          </select>
          <div id="bulkOpDateField" class="date-input-wrap">
            <input id="bulkOpDate" class="input" type="date" aria-label="Дата операций" />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="bulkOpDate" aria-label="Открыть календарь"></button>
          </div>
        </form>
        <div class="modal-footer">
          <button id="submitBulkEditOperationsBtn" class="btn btn-cta modal-main-cta" type="submit" form="bulkEditOperationsForm">
            Применить изменения
          </button>
        </div>
      </div>
    </div>

    <div id="editModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="editTitle">
      <div class="modal-card">
        <div class="panel-head row between">
          <h3 id="editTitle">Редактировать операцию</h3>
          <button id="closeEditModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>

        <form id="editOperationForm" class="form-grid modal-grid edit-modal-grid">
          <div class="segmented" id="editOperationModeSwitch" aria-label="Формат операции">
            <button class="segmented-btn active" data-operation-mode="common" type="button">Общая</button>
            <button class="segmented-btn" data-operation-mode="receipt" type="button">Чек</button>
          </div>
          <input id="editOperationMode" type="hidden" value="common" />
          <div id="editDateField" class="date-input-wrap">
            <input id="editDate" class="input" type="date" aria-label="Дата операции" required />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="editDate" aria-label="Открыть календарь"></button>
          </div>
          <div class="segmented" id="editKindSwitch" aria-label="Тип операции">
            <button class="segmented-btn active" data-kind="expense" type="button">Расход</button>
            <button class="segmented-btn" data-kind="income" type="button">Доход</button>
          </div>
          <input id="editKind" type="hidden" value="expense" />
          <select id="editCategory" class="hidden"></select>
          <div id="editCategoryField" class="create-category-field">
            <input id="editCategorySearch" type="text" placeholder="Категория" autocomplete="off" />
            <div id="editCategoryPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="editCategoryAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <div id="editAmountField" class="money-input-wrap" data-money-input-wrap>
            <input id="editAmount" data-money-input type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Сумма" title="Можно вводить выражения: 1000+250/2" required />
          </div>
          <input id="editNote" class="create-note-field" type="text" placeholder="Комментарий" />

          <div id="editReceiptBlock" class="receipt-block">
            <div id="editReceiptFields" class="hidden">
              <div id="editReceiptItemsList" class="receipt-items-list"></div>
              <div class="receipt-summary">
                <div class="muted-small">Сумма чека: <strong id="editReceiptTotalValue">0.00</strong></div>
                <div class="muted-small">Расхождение: <strong id="editReceiptDiffValue">0.00</strong></div>
                <button id="editPullReceiptTotalBtn" class="btn btn-secondary" type="button" data-receipt-mode="edit">Подтянуть сумму из чека</button>
              </div>
            </div>
          </div>
        </form>
        <div class="preview-panel">
          <div class="preview-title">Превью строки в таблице</div>
          <div class="table-wrap">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th>Категория</th>
                  <th>Сумма</th>
                  <th>Комментарий</th>
                  <th></th>
                </tr>
              </thead>
              <tbody id="editPreviewBody"></tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer">
          <button id="submitEditOperationBtn" class="btn btn-cta modal-main-cta" type="submit" form="editOperationForm">
            Сохранить
          </button>
        </div>
      </div>
    </div>

    <div id="createCategoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="createCategoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="createCategoryTitle">Новая категория</h3>
          <button id="closeCreateCategoryModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="categoryModalForm" class="category-modal-form">
          <div class="category-name-row">
            <div class="icon-select">
              <input id="categoryIcon" type="hidden" value="" />
              <button id="categoryIconToggle" class="btn btn-secondary icon-square-toggle" type="button" aria-label="Выбрать иконку">
                +
              </button>
              <div id="categoryIconPopover" class="icon-popover app-popover hidden"></div>
            </div>
            <input id="categoryName" type="text" placeholder="Название категории" required />
          </div>
          <select id="categoryGroup" class="hidden">
            <option value="">Без группы</option>
          </select>
          <div id="createCategoryGroupField" class="create-category-field">
            <input id="categoryGroupSearch" type="text" placeholder="Без группы" autocomplete="off" />
            <div id="createCategoryGroupPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="categoryGroupAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <div class="segmented" id="createCategoryKind">
            <button class="segmented-btn active" data-cat-create-kind="expense" type="button">Расход</button>
            <button class="segmented-btn" data-cat-create-kind="income" type="button">Доход</button>
          </div>
          <input id="categoryKind" type="hidden" value="expense" />
        </form>
        <div class="modal-footer">
          <button id="submitCreateCategoryBtn" class="btn btn-cta modal-main-cta" type="submit" form="categoryModalForm">
            Добавить категорию
          </button>
        </div>
      </div>
    </div>

    <div id="createGroupModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="createGroupTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="createGroupTitle">Новая группа</h3>
          <button id="closeCreateGroupModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="groupModalForm" class="category-modal-form">
          <input id="groupName" type="text" placeholder="Название группы" required />
          <div class="color-picker-row">
            <input id="groupAccentColor" type="color" value="#ff8a3d" />
            <input id="groupAccentColorHex" type="text" value="#ff8a3d" />
          </div>
          <div class="segmented" id="createGroupKind">
            <button class="segmented-btn active" data-group-create-kind="expense" type="button">Расход</button>
            <button class="segmented-btn" data-group-create-kind="income" type="button">Доход</button>
          </div>
          <input id="groupKind" type="hidden" value="expense" />
        </form>
        <div class="modal-footer">
          <button id="submitCreateGroupBtn" class="btn btn-cta modal-main-cta" type="submit" form="groupModalForm">
            Создать группу
          </button>
        </div>
      </div>
    </div>

    <div id="editGroupModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="editGroupTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="editGroupTitle">Редактировать группу</h3>
          <button id="closeEditGroupModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="editGroupForm" class="category-modal-form">
          <input id="editGroupName" type="text" placeholder="Название группы" required />
          <div class="color-picker-row">
            <input id="editGroupAccentColor" type="color" value="#ff8a3d" />
            <input id="editGroupAccentColorHex" type="text" value="#ff8a3d" />
          </div>
          <input id="editGroupId" type="hidden" value="" />
        </form>
        <div class="modal-footer">
          <button id="submitEditGroupBtn" class="btn btn-cta modal-main-cta" type="submit" form="editGroupForm">
            Сохранить
          </button>
        </div>
      </div>
    </div>

    <div id="editCategoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="editCategoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="editCategoryTitle">Редактировать категорию</h3>
          <button id="closeEditCategoryModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="editCategoryForm" class="category-modal-form">
          <div class="category-name-row">
            <div class="icon-select">
              <input id="editCategoryIcon" type="hidden" value="" />
              <button id="editCategoryIconToggle" class="btn btn-secondary icon-square-toggle" type="button" aria-label="Выбрать иконку">
                +
              </button>
              <div id="editCategoryIconPopover" class="icon-popover app-popover hidden"></div>
            </div>
            <input id="editCategoryName" type="text" placeholder="Название категории" required />
          </div>
          <select id="editCategoryGroup" class="hidden">
            <option value="">Без группы</option>
          </select>
          <div id="editCategoryGroupField" class="create-category-field">
            <input id="editCategoryGroupSearch" type="text" placeholder="Без группы" autocomplete="off" />
            <div id="editCategoryGroupPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="editCategoryGroupAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <div class="segmented" id="editCategoryKindSwitch">
            <button class="segmented-btn active" data-cat-edit-kind="expense" type="button">Расход</button>
            <button class="segmented-btn" data-cat-edit-kind="income" type="button">Доход</button>
          </div>
          <input id="editCategoryKind" type="hidden" value="expense" />
        </form>
        <div class="modal-footer">
          <button id="submitEditCategoryBtn" class="btn btn-cta modal-main-cta" type="submit" form="editCategoryForm">
            Сохранить
          </button>
        </div>
      </div>
    </div>

    <div id="periodCustomModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="periodCustomTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="periodCustomTitle">Настроить период</h3>
          <button id="closePeriodCustomModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="periodCustomForm" class="category-modal-form">
          <div class="date-input-wrap">
            <input id="customDateFrom" class="input" type="date" aria-label="Дата начала периода" required />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="customDateFrom" aria-label="Открыть календарь"></button>
          </div>
          <div class="date-input-wrap">
            <input id="customDateTo" class="input" type="date" aria-label="Дата окончания периода" required />
            <button class="date-input-trigger" type="button" data-date-picker-trigger="customDateTo" aria-label="Открыть календарь"></button>
          </div>
        </form>
        <div class="modal-footer">
          <button id="submitPeriodCustomBtn" class="btn btn-cta modal-main-cta" type="submit" form="periodCustomForm">
            Применить период
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

    ${window.App.templates.modalsItemCatalog || ""}

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
`;
})();
