(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.modalsItemCatalog = `

    <div id="itemTemplateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateModalTitle">
      <div class="modal-card modal-medium item-template-modal-card">
        <div class="panel-head row between">
          <h3 id="itemTemplateModalTitle">Новая позиция</h3>
          <div class="modal-head-actions">
            <button id="itemTemplateActivityBtn" class="btn btn-secondary modal-head-icon-btn hidden" type="button" title="Журнал" aria-label="Открыть журнал"><span aria-hidden="true">◷</span></button>
            <button id="itemTemplateUsageBtn" class="btn btn-secondary modal-head-icon-btn hidden" type="button" title="Операции" aria-label="Открыть операции"><span aria-hidden="true">↗</span></button>
            <button id="itemTemplateHistoryBtn" class="btn btn-secondary modal-head-icon-btn hidden" type="button" title="История цен" aria-label="Открыть историю цен"><span aria-hidden="true">⌁</span></button>
            <button id="closeItemTemplateModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
              <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
            </button>
          </div>
        </div>
        <form id="itemTemplateForm" class="category-modal-form">
          <p class="muted-small item-template-product-help">Добавляется магазин для существующего товара. Бренд, категория и фото общие. Цена необязательна; покупка или операция не создаётся.</p>
          <section class="catalog-image-field" data-catalog-image-picker="item-template" aria-label="Фотография позиции">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Фото позиции</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-xs catalog-image-upload-btn">
                  <span>Загрузить</span>
                  <input data-catalog-image-input type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-xs hidden" data-catalog-image-remove type="button">Удалить</button>
              </div>
              <small class="muted-small" data-catalog-image-status>JPEG, PNG или WebP · до 8 МБ</small>
            </div>
          </section>
          <input id="itemTemplateSource" type="hidden" />
          <div id="itemTemplateSourceField" class="create-category-field">
            <input id="itemTemplateSourceSearch" type="text" placeholder="Источник" autocomplete="off" />
            <div id="itemTemplateSourcePickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="itemTemplateSourceAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <input id="itemTemplateBrand" type="hidden" />
          <div id="itemTemplateBrandField" class="create-category-field">
            <input id="itemTemplateBrandSearch" type="text" placeholder="Бренд (необязательно)" autocomplete="off" />
            <div id="itemTemplateBrandPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="itemTemplateBrandAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <input id="itemTemplateName" type="text" placeholder="Позиция" required />
          <input id="itemTemplateCategory" type="hidden" />
          <div id="itemTemplateCategoryField" class="create-category-field">
            <input id="itemTemplateCategorySearch" type="text" placeholder="Категория позиции" autocomplete="off" />
            <div id="itemTemplateCategoryPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="itemTemplateCategoryAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <div class="form-grid item-template-price-grid">
            <label class="field item-template-price-field">
              <span>Последняя цена</span>
              <div id="itemTemplatePriceField" class="money-input-wrap" data-money-input-wrap>
                <input id="itemTemplatePrice" data-money-input type="text" inputmode="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Сумма" title="Можно вводить выражения: 1000+250/2" />
              </div>
            </label>
            <label class="field item-template-date-field">
              <span>Дата цены</span>
              <div id="itemTemplatePriceDateField" class="date-input-wrap" data-date-stepper>
                <input id="itemTemplatePriceDate" class="input" type="date" aria-label="Дата цены" />
                <button class="date-input-trigger" type="button" data-date-picker-trigger="itemTemplatePriceDate" aria-label="Открыть календарь"></button>
              </div>
            </label>
          </div>
        </form>
        <div class="preview-panel">
          <div class="preview-title">Превью строки в каталоге</div>
          <div class="table-wrap">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Источник</th>
                  <th>Бренд</th>
                  <th>Позиция</th>
                  <th>Категория</th>
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

    <div id="catalogProductModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="catalogProductModalTitle">
      <div class="modal-card modal-medium catalog-product-modal-card">
        <div class="panel-head row between">
          <div>
            <h3 id="catalogProductModalTitle">Новый товар</h3>
            <p class="subtitle">Общая карточка товара для предложений из разных источников</p>
          </div>
          <div class="modal-head-actions">
            <button id="catalogProductActivityBtn" class="btn btn-secondary modal-head-icon-btn hidden" type="button" title="Журнал" aria-label="Открыть журнал"><span aria-hidden="true">◷</span></button>
            <button id="closeCatalogProductModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
              <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
            </button>
          </div>
        </div>
        <form id="catalogProductForm" class="category-modal-form">
          <section class="catalog-image-field" data-catalog-image-picker="catalog-product" aria-label="Фотография товара">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Фото товара</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-xs catalog-image-upload-btn">
                  <span>Загрузить</span>
                  <input data-catalog-image-input type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-xs hidden" data-catalog-image-remove type="button">Удалить</button>
              </div>
              <small class="muted-small" data-catalog-image-status>JPEG, PNG или WebP · до 8 МБ</small>
            </div>
          </section>
          <label class="field">
            <span>Название товара</span>
            <input id="catalogProductName" type="text" maxlength="160" placeholder="Например, Сырок с печеньем клубника 40 г" required />
          </label>
          <div class="form-grid catalog-product-meta-grid">
            <div id="catalogProductBrandField" class="field create-category-field">
              <label for="catalogProductBrandSearch">Бренд</label>
              <input id="catalogProductBrand" type="hidden" />
              <input id="catalogProductBrandSearch" type="text" placeholder="Без бренда" autocomplete="off" aria-haspopup="dialog" aria-expanded="false" aria-controls="catalogProductBrandPicker" />
              <div id="catalogProductBrandPicker" class="app-popover app-popover-floating catalog-product-picker hidden" role="dialog" aria-label="Выбор бренда"><div class="chip-list"></div></div>
            </div>
            <div id="catalogProductCategoryField" class="field create-category-field">
              <label for="catalogProductCategorySearch">Категория</label>
              <input id="catalogProductCategory" type="hidden" />
              <input id="catalogProductCategorySearch" type="text" placeholder="Без категории" autocomplete="off" aria-haspopup="dialog" aria-expanded="false" aria-controls="catalogProductCategoryPicker" />
              <div id="catalogProductCategoryPicker" class="app-popover app-popover-floating catalog-product-picker hidden" role="dialog" aria-label="Выбор категории"><div class="chip-list"></div></div>
            </div>
          </div>
        </form>
        <section id="catalogProductOffersSection" class="catalog-product-modal-offers hidden">
          <div class="row between">
            <div>
              <strong>Источники товара</strong>
              <div class="muted-small">Цена и история остаются отдельными для каждого магазина</div>
            </div>
            <div class="row catalog-product-offers-actions">
              <button id="addCatalogProductSourceBtn" class="btn btn-primary btn-xs" type="button">Добавить источник</button>
              <button id="openCatalogProductOperationsBtn" class="btn btn-secondary btn-xs" type="button">Все операции товара</button>
            </div>
          </div>
          <div id="catalogProductOffersList" class="catalog-product-offers-list"></div>
        </section>
        <div class="modal-footer catalog-product-modal-footer">
          <button id="deleteCatalogProductBtn" class="btn btn-danger hidden" type="button">Удалить товар</button>
          <button id="submitCatalogProductBtn" class="btn btn-cta modal-main-cta" type="submit" form="catalogProductForm">Создать товар</button>
        </div>
      </div>
    </div>

    <div id="catalogProductMergeModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="catalogProductMergeTitle">
      <div class="modal-card modal-small catalog-product-merge-card">
        <div class="panel-head row between">
          <div>
            <h3 id="catalogProductMergeTitle">Объединить товары</h3>
            <p class="subtitle">Выберите карточку, которая останется главной</p>
          </div>
          <button id="closeCatalogProductMergeModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="catalogProductMergeForm" class="catalog-product-merge-form">
          <div id="catalogProductMergeOptions" class="catalog-product-merge-options"></div>
          <div id="catalogProductMergeWarning" class="catalog-product-merge-warning hidden"></div>
          <p class="muted-small">Все предложения и история операций перейдут в выбранную карточку. Отменить объединение целиком нельзя, но отдельное предложение можно отделить.</p>
        </form>
        <div class="modal-footer">
          <button id="submitCatalogProductMergeBtn" class="btn btn-cta modal-main-cta" type="submit" form="catalogProductMergeForm">Объединить</button>
        </div>
      </div>
    </div>

    <div id="itemBrandModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemBrandModalTitle">
      <div class="modal-card modal-small item-brand-modal-card">
        <div class="panel-head row between">
          <div>
            <h3 id="itemBrandModalTitle">Новый бренд</h3>
            <p class="subtitle">Название и цвет чипа бренда</p>
          </div>
          <button id="closeItemBrandModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <form id="itemBrandForm" class="category-modal-form">
          <section class="catalog-image-field" data-catalog-image-picker="item-brand" aria-label="Логотип бренда">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Логотип</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-xs catalog-image-upload-btn">
                  <span>Загрузить</span>
                  <input data-catalog-image-input type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-xs hidden" data-catalog-image-remove type="button">Удалить</button>
              </div>
              <small class="muted-small" data-catalog-image-status>JPEG, PNG или WebP · до 8 МБ</small>
            </div>
          </section>
          <label class="field">
            <span>Название</span>
            <input id="itemBrandName" type="text" maxlength="160" placeholder="Например, Vici" required />
          </label>
          <fieldset class="item-brand-color-fieldset">
            <legend>Акцентный цвет</legend>
            <div class="item-brand-color-control">
              <input id="itemBrandAccentColor" type="color" value="#7aa8ff" aria-label="Акцентный цвет бренда" />
              <div id="itemBrandColorPresets" class="item-brand-color-presets" aria-label="Готовые цвета">
                <button type="button" data-item-brand-color="#7aa8ff" style="--brand-preset:#7aa8ff" aria-label="Синий"></button>
                <button type="button" data-item-brand-color="#5fd3bc" style="--brand-preset:#5fd3bc" aria-label="Бирюзовый"></button>
                <button type="button" data-item-brand-color="#ff8f6b" style="--brand-preset:#ff8f6b" aria-label="Коралловый"></button>
                <button type="button" data-item-brand-color="#ffd166" style="--brand-preset:#ffd166" aria-label="Жёлтый"></button>
                <button type="button" data-item-brand-color="#c084fc" style="--brand-preset:#c084fc" aria-label="Фиолетовый"></button>
                <button type="button" data-item-brand-color="#fb7185" style="--brand-preset:#fb7185" aria-label="Розовый"></button>
              </div>
            </div>
          </fieldset>
          <div id="itemBrandPreview" class="item-brand-preview" aria-live="polite"></div>
        </form>
        <div class="modal-footer">
          <button id="submitItemBrandBtn" class="btn btn-cta modal-main-cta" type="submit" form="itemBrandForm">Создать бренд</button>
        </div>
      </div>
    </div>

    <div id="itemBrandDetailModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemBrandDetailTitle">
      <div class="modal-card modal-medium item-brand-detail-card">
        <div class="panel-head row between">
          <div>
            <h3 id="itemBrandDetailTitle">Бренд</h3>
            <p id="itemBrandDetailSubtitle" class="subtitle">Связанные позиции по источникам</p>
          </div>
          <button id="closeItemBrandDetailModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
            <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
          </button>
        </div>
        <div id="itemBrandDetailKpiGrid" class="analytics-kpi-grid section-kpi-grid" aria-label="Итоги бренда"></div>
        <div class="item-brand-detail-actions">
          <button id="openItemBrandOperationsBtn" class="btn btn-secondary" type="button">Открыть операции бренда</button>
          <button id="editItemBrandFromDetailBtn" class="btn btn-secondary" type="button">Изменить бренд</button>
        </div>
        <div class="table-wrap">
          <table class="table table-hover mobile-card-table item-brand-detail-table">
            <thead><tr><th>Источник</th><th>Позиция</th><th>Категория</th><th>Последняя цена</th><th></th></tr></thead>
            <tbody id="itemBrandDetailBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="sourceGroupModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="sourceGroupTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="sourceGroupTitle">Новый источник</h3>
          <div class="modal-head-actions">
            <button id="sourceGroupCreateItemBtn" class="btn btn-secondary modal-head-icon-btn hidden" type="button" title="Добавить позицию" aria-label="Добавить позицию"><span aria-hidden="true">+</span></button>
            <button id="closeSourceGroupModalBtn" class="btn btn-secondary modal-close-btn" type="button" aria-label="Закрыть">
              <span aria-hidden="true">×</span><span class="modal-close-label">Закрыть</span>
            </button>
          </div>
        </div>
        <form id="sourceGroupForm" class="category-modal-form">
          <input id="sourceGroupOriginalName" type="hidden" />
          <section class="catalog-image-field" data-catalog-image-picker="item-source" aria-label="Логотип источника">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Логотип магазина или источника</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-xs catalog-image-upload-btn">
                  <span>Загрузить</span>
                  <input data-catalog-image-input type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-xs hidden" data-catalog-image-remove type="button">Удалить</button>
              </div>
              <small class="muted-small" data-catalog-image-status>JPEG, PNG или WebP · до 8 МБ</small>
            </div>
          </section>
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
                <th aria-label="Действия"></th>
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
