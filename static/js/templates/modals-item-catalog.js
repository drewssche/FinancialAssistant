(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.modalsItemCatalog = `

    <div id="itemTemplateModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateModalTitle">
      <div class="modal-card modal-medium item-template-modal-card">
        <div class="panel-head row between">
          <h3 id="itemTemplateModalTitle">Новая позиция</h3>
          <div class="modal-head-actions">
            <button id="itemTemplateActivityBtn" class="btn btn-secondary modal-head-icon-btn hidden btn-icon" type="button" title="Открыть журнал" aria-label="Открыть журнал">${window.App.icons.svg("history")}</button>
            <button id="itemTemplateUsageBtn" class="btn btn-secondary modal-head-icon-btn hidden btn-icon" type="button" title="Открыть операции" aria-label="Открыть операции">${window.App.icons.svg("receipt")}</button>
            <button id="itemTemplateHistoryBtn" class="btn btn-secondary modal-head-icon-btn hidden btn-icon" type="button" title="Открыть историю цен" aria-label="Открыть историю цен">${window.App.icons.svg("chart")}</button>
            <button id="itemTemplatePreviewBtn" class="btn btn-secondary btn-icon" type="button" title="Предпросмотр позиции" aria-label="Предпросмотр позиции" aria-expanded="false" aria-controls="itemTemplatePreviewPanel">${window.App.icons.svg("eye")}</button>
            <button id="closeItemTemplateModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
          </div>
        </div>
        <form id="itemTemplateForm" class="category-modal-form">

          <section class="catalog-image-field" data-catalog-image-picker="item-template" aria-label="Фотография позиции">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Фото позиции</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-icon catalog-image-upload-btn" title="Загрузить фото">
                  ${window.App.icons.svg("upload")}
                  <input data-catalog-image-input aria-label="Загрузить фото" type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-icon hidden" data-catalog-image-remove type="button" title="Удалить фото" aria-label="Удалить фото">${window.App.icons.svg("trash")}</button>
              </div>
              <small class="muted-small" data-catalog-image-status></small>
            </div>
          </section>
          <input id="itemTemplateSource" type="hidden" />
          <div id="itemTemplateSourceField" class="create-category-field">
            <label class="field"><span>Источник</span><input id="itemTemplateSourceSearch" type="text" placeholder="Источник" autocomplete="off" /></label>
            <div id="itemTemplateSourcePickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="itemTemplateSourceAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <input id="itemTemplateBrand" type="hidden" />
          <div id="itemTemplateBrandField" class="create-category-field">
            <label class="field"><span>Бренд</span><input id="itemTemplateBrandSearch" type="text" placeholder="Бренд (необязательно)" autocomplete="off" /></label>
            <div id="itemTemplateBrandPickerBlock" class="operation-category-picker app-popover hidden">
              <div class="category-picker-block">
                <div id="itemTemplateBrandAll" class="category-chip-list"></div>
              </div>
            </div>
          </div>
          <label class="field item-template-name-field"><span>Название позиции</span><input id="itemTemplateName" type="text" placeholder="Позиция" required /></label>
          <input id="itemTemplateCategory" type="hidden" />
          <div id="itemTemplateCategoryField" class="create-category-field">
            <label class="field"><span>Категория</span><input id="itemTemplateCategorySearch" type="text" placeholder="Категория позиции" autocomplete="off" /></label>
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
        <div id="itemTemplatePreviewPanel" class="preview-panel hidden">
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
          <button id="submitItemTemplateBtn" class="btn btn-cta modal-main-cta btn-icon" type="submit" form="itemTemplateForm" title="Сохранить позицию" aria-label="Сохранить позицию">${window.App.icons.svg("save")}</button>
        </div>
      </div>
    </div>

    <div id="catalogProductModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="catalogProductModalTitle">
      <div class="modal-card modal-medium catalog-product-modal-card">
        <div class="panel-head row between">
          <div>
            <h3 id="catalogProductModalTitle">Новый товар</h3>

          </div>
          <div class="modal-head-actions">
            <button id="catalogProductActivityBtn" class="btn btn-secondary modal-head-icon-btn hidden btn-icon" type="button" title="Открыть журнал" aria-label="Открыть журнал">${window.App.icons.svg("history")}</button>
            <button id="closeCatalogProductModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
          </div>
        </div>
        <nav id="catalogProductTabs" class="segmented catalog-product-tabs hidden" aria-label="Разделы товара">
          <button type="button" class="segmented-btn active" data-product-tab="product" aria-pressed="true">Товар</button>
          <button type="button" class="segmented-btn" data-product-tab="offers" aria-pressed="false">Предложения</button>
          <button type="button" class="segmented-btn" data-product-tab="prices" aria-pressed="false">Цены</button>
          <button type="button" class="segmented-btn" data-product-tab="purchases" aria-pressed="false">Покупки</button>
        </nav>
        <div id="catalogProductWatch" class="catalog-product-watch hidden"></div>
        <form data-product-panel="product" id="catalogProductForm" class="category-modal-form">
          <section class="catalog-image-field" data-catalog-image-picker="catalog-product" aria-label="Фотография товара">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Фото товара</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-icon catalog-image-upload-btn" title="Загрузить фото">
                  ${window.App.icons.svg("upload")}
                  <input data-catalog-image-input aria-label="Загрузить фото" type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-icon hidden" data-catalog-image-remove type="button" title="Удалить фото" aria-label="Удалить фото">${window.App.icons.svg("trash")}</button>
              </div>
              <small class="muted-small" data-catalog-image-status></small>
            </div>
          </section>
          <label class="field">
            <span>Название товара</span>
            <input id="catalogProductName" type="text" maxlength="160" placeholder="Например, Сырок с печеньем клубника 40 г" required />
          </label>
          <section class="catalog-product-measurements" aria-label="Единицы и фасовка">
            <div class="form-grid">
              <label class="field"><span>Единица продажи</span><select id="catalogProductSaleUnit"><option value="">Не указана</option><option value="piece">шт.</option><option value="pack">упак.</option><option value="kg">кг</option><option value="g">г</option><option value="l">л</option><option value="ml">мл</option></select></label>
              <label class="field"><span>В одной штуке / упаковке</span><input id="catalogProductPackageQuantity" type="number" min="0.001" step="0.001" placeholder="Например, 900" /></label>
              <label class="field"><span>Единица содержимого</span><select id="catalogProductPackageUnit"><option value="">Не указана</option><option value="piece">шт.</option><option value="kg">кг</option><option value="g">г</option><option value="l">л</option><option value="ml">мл</option></select></label>
            </div>
          </section>

          <div class="form-grid catalog-product-meta-grid">
            <div id="catalogProductBrandField" class="field create-category-field">
              <label for="catalogProductBrandSearch">Бренд</label>
              <input id="catalogProductBrand" type="hidden" />
              <input id="catalogProductBrandSearch" type="text" placeholder="Без бренда" autocomplete="off" aria-haspopup="dialog" aria-expanded="false" aria-controls="catalogProductBrandPicker" />
              <div id="catalogProductBrandPicker" class="app-popover app-popover-floating catalog-product-picker hidden" data-popover-max-height="420" role="dialog" aria-label="Выбор бренда"><div class="chip-list"></div></div>
            </div>
            <div id="catalogProductCategoryField" class="field create-category-field">
              <label for="catalogProductCategorySearch">Категория</label>
              <input id="catalogProductCategory" type="hidden" />
              <input id="catalogProductCategorySearch" type="text" placeholder="Без категории" autocomplete="off" aria-haspopup="dialog" aria-expanded="false" aria-controls="catalogProductCategoryPicker" />
              <div id="catalogProductCategoryPicker" class="app-popover app-popover-floating catalog-product-picker hidden" data-popover-max-height="420" role="dialog" aria-label="Выбор категории"><div class="chip-list"></div></div>
            </div>
          </div>
        </form>
        <section data-product-panel="offers" id="catalogProductOffersSection" class="catalog-product-modal-offers hidden">
          <div class="row between">
            <div>
              <strong>Источники товара</strong>

            </div>
            <div class="row catalog-product-offers-actions">
              <button id="addCatalogProductSourceBtn" class="btn-icon btn btn-primary btn-xs" type="button" title="Добавить источник" aria-label="Добавить источник">${window.App.icons.svg("plus")}</button>
            </div>
          </div>
          <p id="catalogProductCodesStatus" class="muted-small" role="status"></p>
          <button id="catalogProductCodesRetry" type="button" class="btn btn-secondary btn-xs btn-icon" hidden title="Повторить загрузку кодов" aria-label="Повторить загрузку кодов">${window.App.icons.svg("refresh")}</button>
          <div id="catalogProductOffersList" class="catalog-product-offers-list"></div>
        </section>
        <section data-product-panel="prices" class="catalog-product-detail-panel hidden">
          <label class="field"><span>Предложение магазина</span><select id="catalogProductPriceOffer" aria-label="Предложение для истории цен"></select></label>
          <label class="field"><span>История</span><select id="catalogProductPriceMode"><option value="purchases">По покупкам</option><option value="offers">Сохранённые цены предложения</option></select></label>
          <section id="catalogProductHistoryControls"><div class="product-price-controls">
            <label class="field"><span>Цена</span><select id="catalogProductPriceKind"><option value="paid">Фактически оплаченная</option><option value="regular">Обычная, если указана</option></select></label>
            <label class="field"><span>Сравнение</span><select id="catalogProductPriceBasis"><option value="unit">За единицу продажи / упаковку</option><option value="normalized">За кг / л / штуку содержимого</option></select></label>
            <label class="field"><span>С даты</span><input id="catalogProductPriceFrom" type="date"></label>
            <label class="field"><span>По дату</span><input id="catalogProductPriceTo" type="date"></label>
          </div></section>
          <p id="catalogProductLegacyPriceNote" class="muted-small hidden">Справочные цены источника. История покупок — в отдельном режиме.</p>
          <div id="catalogProductComparisonSummary" class="catalog-comparison-summary hidden"></div>
          <div id="catalogProductPricesList" aria-live="polite"></div>
        </section>
        <section data-product-panel="purchases" class="catalog-product-detail-panel hidden">
          <label class="field"><span>Предложения</span><select id="catalogProductPurchaseOffer" aria-label="Предложения в покупках"></select></label>

          <div id="catalogProductPurchasesList" aria-live="polite"></div>
          <button id="catalogProductMorePurchases" class="btn-icon btn btn-secondary hidden" type="button" title="Показать ещё покупки" aria-label="Показать ещё покупки">${window.App.icons.svg("down")}</button>
          <button id="openCatalogProductOperationsBtn" class="btn-icon btn btn-secondary" type="button" title="Открыть операции товара" aria-label="Открыть операции товара">${window.App.icons.svg("receipt")}</button>
        </section>
        <div data-product-panel="product offers" class="modal-footer catalog-product-modal-footer">
          <button id="deleteCatalogProductBtn" class="btn-icon btn btn-danger hidden" type="button" title="Удалить товар" aria-label="Удалить товар">${window.App.icons.svg("trash")}</button>
          <button id="submitCatalogProductBtn" class="btn-icon btn btn-cta modal-main-cta" type="submit" form="catalogProductForm" title="Сохранить товар" aria-label="Сохранить товар">${window.App.icons.svg("save")}</button>
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
          <button id="closeCatalogProductMergeModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
        </div>
        <form id="catalogProductMergeForm" class="catalog-product-merge-form">
          <div id="catalogProductMergeOptions" class="catalog-product-merge-options"></div>
          <div id="catalogProductMergeWarning" class="catalog-product-merge-warning hidden"></div>
          <p id="catalogProductMergeError" class="form-error" role="alert" hidden></p>
          <p class="muted-small">Все предложения и история операций перейдут в выбранную карточку. Отменить объединение целиком нельзя, но отдельное предложение можно отделить.</p>
        </form>
        <div class="modal-footer">
          <button id="submitCatalogProductMergeBtn" class="btn btn-cta modal-main-cta btn-icon" type="submit" form="catalogProductMergeForm" title="Объединить" aria-label="Объединить">${window.App.icons.svg("merge")}</button>
        </div>
      </div>
    </div>

    <div id="itemBrandModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemBrandModalTitle">
      <div class="modal-card modal-small item-brand-modal-card">
        <div class="panel-head row between">
          <div>
            <h3 id="itemBrandModalTitle">Новый бренд</h3>

          </div>
          <button id="closeItemBrandModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
        </div>
        <form id="itemBrandForm" class="category-modal-form">
          <section class="catalog-image-field" data-catalog-image-picker="item-brand" aria-label="Логотип бренда">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Логотип</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-icon catalog-image-upload-btn" title="Загрузить фото">
                  ${window.App.icons.svg("upload")}
                  <input data-catalog-image-input aria-label="Загрузить фото" type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-icon hidden" data-catalog-image-remove type="button" title="Удалить фото" aria-label="Удалить фото">${window.App.icons.svg("trash")}</button>
              </div>
              <small class="muted-small" data-catalog-image-status></small>
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
          <button id="submitItemBrandBtn" class="btn btn-cta modal-main-cta btn-icon" type="submit" form="itemBrandForm" title="Создать бренд" aria-label="Создать бренд">${window.App.icons.svg("save")}</button>
        </div>
      </div>
    </div>

    <div id="itemBrandDetailModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemBrandDetailTitle">
      <div class="modal-card modal-medium item-brand-detail-card">
        <div class="panel-head row between">
          <div>
            <h3 id="itemBrandDetailTitle">Бренд</h3>
            <p id="itemBrandDetailSubtitle" class="subtitle"></p>
          </div>
          <button id="closeItemBrandDetailModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
        </div>
        <div id="itemBrandDetailKpiGrid" class="analytics-kpi-grid section-kpi-grid" aria-label="Итоги бренда"></div>
        <div class="item-brand-detail-actions">
          <button id="openItemBrandOperationsBtn" class="btn btn-secondary btn-icon" type="button" title="Открыть операции бренда" aria-label="Открыть операции бренда">${window.App.icons.svg("receipt")}</button>
          <button id="editItemBrandFromDetailBtn" class="btn btn-secondary btn-icon" type="button" title="Изменить бренд" aria-label="Изменить бренд">${window.App.icons.svg("edit")}</button>
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
            <button id="sourceGroupCreateItemBtn" class="btn btn-secondary modal-head-icon-btn hidden btn-icon" type="button" title="Добавить позицию" aria-label="Добавить позицию">${window.App.icons.svg("plus")}</button>
            <button id="closeSourceGroupModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
          </div>
        </div>
        <form id="sourceGroupForm" class="category-modal-form">
          <input id="sourceGroupOriginalName" type="hidden" />
          <section class="catalog-image-field" data-catalog-image-picker="item-source" aria-label="Логотип источника">
            <div class="catalog-image-picker-preview" data-catalog-image-preview></div>
            <div class="catalog-image-picker-actions">
              <strong>Логотип магазина или источника</strong>
              <div class="catalog-image-picker-buttons">
                <label class="btn btn-secondary btn-icon catalog-image-upload-btn" title="Загрузить фото">
                  ${window.App.icons.svg("upload")}
                  <input data-catalog-image-input aria-label="Загрузить фото" type="file" accept="image/jpeg,image/png,image/webp" />
                </label>
                <button class="btn btn-danger btn-icon hidden" data-catalog-image-remove type="button" title="Удалить фото" aria-label="Удалить фото">${window.App.icons.svg("trash")}</button>
              </div>
              <small class="muted-small" data-catalog-image-status></small>
            </div>
          </section>
          <label class="field"><span>Название</span><input id="sourceGroupName" type="text" placeholder="Название источника" required /></label>
        </form>
        <div id="sourceGroupPreviewBody" class="catalog-directory-summary" aria-live="polite"></div>
        <div class="modal-footer">
          <button id="submitSourceGroupBtn" class="btn btn-cta modal-main-cta btn-icon" type="submit" form="sourceGroupForm" title="Создать источник" aria-label="Создать источник">${window.App.icons.svg("save")}</button>
        </div>
      </div>
    </div>

    <div id="itemTemplateHistoryModal" class="modal hidden" role="dialog" aria-modal="true" aria-labelledby="itemTemplateHistoryTitle">
      <div class="modal-card modal-small">
        <div class="panel-head row between">
          <h3 id="itemTemplateHistoryTitle">История цен</h3>
          <button id="closeItemTemplateHistoryModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
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
          <button id="closeBatchItemTemplateModalBtn" class="btn btn-secondary modal-close-btn btn-icon" type="button" title="Закрыть" aria-label="Закрыть">${window.App.icons.svg("close")}</button>
        </div>
        <form id="batchItemTemplateForm" class="category-modal-form">
          <p class="subtitle"><code>Источник;позиция;цена</code> — по одной позиции на строку. Цена необязательна; новые источники создаются автоматически.</p>
          <textarea aria-label="Строки позиций для импорта" id="batchItemTemplateInput" rows="8" placeholder="Евроопт;Сигареты Rothmans;9,40&#10;WB;USB кабель;12.99"></textarea>
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
          <button id="previewBatchItemTemplateBtn" class="btn btn-secondary btn-icon" type="submit" form="batchItemTemplateForm" title="Проверить строки" aria-label="Проверить строки">${window.App.icons.svg("eye")}</button>
          <button id="confirmBatchItemTemplateBtn" class="btn btn-cta modal-main-cta hidden btn-icon" type="button" title="Импортировать строки" aria-label="Импортировать строки">${window.App.icons.svg("save")}</button>
        </div>
      </div>
    </div>
`;
})();
