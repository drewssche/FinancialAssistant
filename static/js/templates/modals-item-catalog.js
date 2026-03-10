(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.modalsItemCatalog = `

    <div id="itemTemplateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateModalTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="itemTemplateModalTitle">Новая позиция</h3>
          <button id="closeItemTemplateModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="itemTemplateForm" class="category-modal-form">
          <input id="itemTemplateSource" type="hidden" />
          <div id="itemTemplateSourceField" class="create-category-field">
            <input id="itemTemplateSourceSearch" type="text" placeholder="Источник" autocomplete="off" />
            <div id="itemTemplateSourcePickerBlock" class="operation-category-picker hidden">
              <div class="category-picker-block">
                <div id="itemTemplateSourceAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <input id="itemTemplateName" type="text" placeholder="Позиция" required />
          <div class="money-input-wrap" data-money-input-wrap>
            <input id="itemTemplatePrice" data-money-input type="text" inputmode="decimal" placeholder="Последняя цена или выражение" title="Можно вводить выражения: 1000+250/2" />
          </div>
        </form>
        <div class="preview-panel">
          <div class="preview-title">Превью строки в каталоге</div>
          <div class="table-wrap">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Источник</th>
                  <th>Позиция</th>
                  <th>Последняя цена</th>
                </tr>
              </thead>
              <tbody id="itemTemplatePreviewBody"></tbody>
            </table>
          </div>
        </div>
        <div class="modal-footer">
          <button id="submitItemTemplateBtn" class="btn btn-cta modal-main-cta" type="submit" form="itemTemplateForm">
            Сохранить
          </button>
        </div>
      </div>
    </div>

    <div id="sourceGroupModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="sourceGroupTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="sourceGroupTitle">Новый источник</h3>
          <button id="closeSourceGroupModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="sourceGroupForm" class="category-modal-form">
          <input id="sourceGroupOriginalName" type="hidden" />
          <input id="sourceGroupName" type="text" placeholder="Название источника" required />
        </form>
        <div class="preview-panel">
          <div class="preview-title">Превью группы в каталоге</div>
          <div class="table-wrap">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Источник</th>
                  <th>Позиции</th>
                  <th>Использования</th>
                  <th>Ср. цена</th>
                </tr>
              </thead>
              <tbody id="sourceGroupPreviewBody"></tbody>
            </table>
          </div>
        </div>
        <div class="modal-footer">
          <button id="submitSourceGroupBtn" class="btn btn-cta modal-main-cta" type="submit" form="sourceGroupForm">
            Создать источник
          </button>
        </div>
      </div>
    </div>

    <div id="itemTemplateHistoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateHistoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="itemTemplateHistoryTitle">История цен</h3>
          <button id="closeItemTemplateHistoryModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <div id="itemTemplateHistoryMeta" class="subtitle item-template-history-meta">—</div>
        <div class="table-wrap">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Цена</th>
              </tr>
            </thead>
            <tbody id="itemTemplateHistoryBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="batchItemTemplateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="batchItemTemplateTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="batchItemTemplateTitle">Массовое добавление позиций</h3>
          <button id="closeBatchItemTemplateModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="batchItemTemplateForm" class="category-modal-form">
          <p class="subtitle">Одна строка: <code>источник;позиция;цена</code>. Цена опциональна.</p>
          <p class="muted-small">Новый источник будет создан автоматически. Сумма поддерживает <code>01,23</code> и <code>01.23</code>.</p>
          <textarea id="batchItemTemplateInput" rows="8" placeholder="Евроопт;Сигареты Rothmans;9,40&#10;WB;USB кабель;12.99"></textarea>
          <div id="batchItemTemplateFeedback" class="status-box hidden"></div>
          <div id="batchItemTemplatePreview" class="bulk-import-preview hidden">
            <div class="preview-title">Предпросмотр строк</div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Источник</th>
                    <th>Позиция</th>
                    <th>Цена</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody id="batchItemTemplatePreviewBody"></tbody>
              </table>
            </div>
          </div>
        </form>
        <div class="modal-footer">
          <button id="previewBatchItemTemplateBtn" class="btn btn-secondary" type="submit" form="batchItemTemplateForm">
            Проверить строки
          </button>
          <button id="confirmBatchItemTemplateBtn" class="btn btn-cta modal-main-cta hidden" type="button">
            Импортировать 0 строк
          </button>
        </div>
      </div>
    </div>
`;
})();
