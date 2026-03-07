(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.modalsItemCatalog = `

    <div id="itemTemplateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateModalTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="itemTemplateModalTitle">Новая позиция</h3>
          <button id="closeItemTemplateModalBtn" class="btn btn-secondary" type="button">Закрыть</button>
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
            <input id="itemTemplatePrice" data-money-input type="number" step="0.01" placeholder="Последняя цена (опционально)" />
          </div>
        </form>
        <div class="modal-footer">
          <button id="submitItemTemplateBtn" class="btn btn-cta modal-main-cta" type="submit" form="itemTemplateForm">
            Сохранить
          </button>
        </div>
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
      </div>
    </div>

    <div id="sourceGroupModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="sourceGroupTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="sourceGroupTitle">Новый источник</h3>
          <button id="closeSourceGroupModalBtn" class="btn btn-secondary" type="button">Закрыть</button>
        </div>
        <form id="sourceGroupForm" class="category-modal-form">
          <input id="sourceGroupName" type="text" placeholder="Название источника" required />
        </form>
        <div class="modal-footer">
          <button id="submitSourceGroupBtn" class="btn btn-cta modal-main-cta" type="submit" form="sourceGroupForm">
            Создать источник
          </button>
        </div>
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
      </div>
    </div>

    <div id="itemTemplateHistoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateHistoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="itemTemplateHistoryTitle">История цен</h3>
          <button id="closeItemTemplateHistoryModalBtn" class="btn btn-secondary" type="button">Закрыть</button>
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
`;
})();
