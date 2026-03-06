(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shell = `

    <div id="appShell" class="app-shell hidden">
      <aside class="sidebar">
        <div class="brand">FA</div>
        <div class="sidebar-today">
          <div id="todayWeekday" class="today-weekday">Сегодня</div>
          <div id="todayDate" class="today-date">--</div>
        </div>

        <nav class="nav" id="mainNav">
          <button class="nav-btn active" data-section="dashboard">Дашборд</button>
          <button class="nav-btn" data-section="operations">Операции</button>
          <button class="nav-btn" data-section="debts">Долги</button>
          <button class="nav-btn" data-section="categories">Категории</button>
          <button class="nav-btn" data-section="settings">Настройки</button>
        </nav>

        <div class="user-area">
          <div class="user-block user-block-static">
            <div class="avatar" id="userAvatar">П</div>
            <div class="meta">
              <div id="userName">Пользователь</div>
              <div id="userHandle">@user</div>
            </div>
            <button id="sidebarLogoutBtn" class="user-logout-icon-btn" type="button" title="Выйти" aria-label="Выйти">⎋</button>
          </div>
        </div>
      </aside>

      <main class="main">
        <header class="topbar">
          <div>
            <h2 id="sectionTitle">Дашборд</h2>
            <p class="subtitle" id="sectionSubtitle">Доходы, расходы и быстрый контроль баланса</p>
          </div>
          <div class="top-actions">
            <div class="cta-row">
              <button id="addOperationCta" class="btn btn-cta" type="button">+ Добавить операцию</button>
              <button id="batchOperationCta" class="btn btn-secondary" type="button">+ Массовое добавление</button>
              <button id="addDebtCta" class="btn btn-cta hidden" type="button">+ Новый долг</button>
              <button id="addCategoryCta" class="btn btn-cta hidden" type="button">+ Создать категорию</button>
              <button id="addGroupCta" class="btn btn-secondary hidden" type="button">+ Создать группу</button>
            </div>
          </div>
        </header>

        <section id="dashboardSection" class="section-block">
          <section class="kpi-grid">
            <article class="kpi-card">
              <h3>Доход</h3>
              <p id="incomeTotal">0.00</p>
            </article>
            <article class="kpi-card">
              <h3>Расход</h3>
              <p id="expenseTotal">0.00</p>
            </article>
            <article class="kpi-card">
              <h3>Баланс</h3>
              <p id="balanceTotal">0.00</p>
            </article>
          </section>

          <section class="kpi-grid">
            <article class="kpi-card">
              <h3>Мне должны</h3>
              <p id="debtLendTotal">0.00</p>
            </article>
            <article class="kpi-card">
              <h3>Я должен</h3>
              <p id="debtBorrowTotal">0.00</p>
            </article>
            <article class="kpi-card">
              <h3>Чистая позиция по долгам</h3>
              <p id="debtNetTotal">0.00</p>
            </article>
          </section>

          <section id="dashboardDebtsPanel" class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Активные долги</h3>
                <p class="subtitle">Краткий список по контрагентам</p>
              </div>
              <button id="openDebtsTabBtn" class="btn btn-secondary" type="button">Открыть раздел Долги</button>
            </div>
            <div id="dashboardDebtsList" class="debt-cards debt-cards-compact"></div>
          </section>

          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Операции за период</h3>
                <p id="dashboardPeriodLabel" class="subtitle"></p>
              </div>
              <div class="panel-controls">
                <div class="segmented" data-period-tabs role="tablist" aria-label="Период дашборда">
                  <button class="segmented-btn active" data-period="day" type="button">День</button>
                  <button class="segmented-btn" data-period="week" type="button">Неделя</button>
                  <button class="segmented-btn" data-period="month" type="button">Месяц</button>
                  <button class="segmented-btn" data-period="year" type="button">Год</button>
                  <button class="segmented-btn" data-period="all_time" type="button">За все время</button>
                  <button class="segmented-btn" data-period="custom" type="button">Настроить</button>
                </div>
                <button id="openOperationsTabBtn" class="btn btn-secondary" type="button">Открыть раздел Операции</button>
              </div>
            </div>
            <div class="table-wrap">
              <table class="table table-hover">
                <thead>
                  <tr>
                    <th>Дата</th>
                    <th>Тип</th>
                    <th>Категория</th>
                    <th>Сумма</th>
                    <th>Комментарий</th>
                  </tr>
                </thead>
                <tbody id="dashboardOperationsBody"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section id="operationsSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <p id="operationsPeriodLabel" class="subtitle"></p>
              </div>
              <div class="toolbar">
                <div class="segmented" data-period-tabs role="tablist" aria-label="Период операций">
                  <button class="segmented-btn active" data-period="day" type="button">День</button>
                  <button class="segmented-btn" data-period="week" type="button">Неделя</button>
                  <button class="segmented-btn" data-period="month" type="button">Месяц</button>
                  <button class="segmented-btn" data-period="year" type="button">Год</button>
                  <button class="segmented-btn" data-period="all_time" type="button">За все время</button>
                  <button class="segmented-btn" data-period="custom" type="button">Настроить</button>
                </div>
                <div class="segmented" id="kindFilters" role="tablist" aria-label="Фильтр по типу">
                  <button class="segmented-btn active" data-kind="" type="button">Все</button>
                  <button class="segmented-btn" data-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-kind="income" type="button">Доход</button>
                </div>
                <div class="segmented" id="operationsSortTabs" role="tablist" aria-label="Сортировка операций">
                  <button class="segmented-btn active" data-op-sort="date" type="button">По дате</button>
                  <button class="segmented-btn" data-op-sort="amount" type="button">По сумме</button>
                  <button class="segmented-btn" data-op-sort="risk" type="button">Риск</button>
                </div>
              </div>
            </div>
            <div id="operationsBulkBar" class="bulk-bar sticky-bar">
              <span id="operationsSelectedCount">Всего: 0</span>
              <button id="bulkEditOperationsBtn" class="btn btn-secondary bulk-action hidden-action" type="button">Редактировать выбранные</button>
              <button id="bulkDeleteOperationsBtn" class="btn btn-danger bulk-action hidden-action" type="button">Удалить выбранные</button>
            </div>
            <div class="table-search-row sticky-search">
              <input id="filterQ" class="table-search-input" type="text" placeholder="Поиск" />
              <button id="deleteAllOperationsBtn" class="btn btn-danger" type="button">Удалить все</button>
            </div>

            <div class="table-wrap">
              <table class="table table-hover">
                <thead>
                  <tr>
                    <th class="select-col"><input id="operationsSelectAll" class="table-checkbox" type="checkbox" /></th>
                    <th>Дата</th>
                    <th>Тип</th>
                    <th>Категория</th>
                    <th>Сумма</th>
                    <th>Комментарий</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="operationsBody"></tbody>
              </table>
            </div>

            <div id="operationsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>

            <div class="pagination hidden" aria-hidden="true">
              <button id="prevPageBtn" class="btn btn-secondary" type="button">Назад</button>
              <span id="pageInfo">Страница 1</span>
              <button id="nextPageBtn" class="btn btn-secondary" type="button">Вперёд</button>
            </div>
          </section>
        </section>

        <section id="categoriesSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div></div>
              <div class="toolbar">
                <div class="segmented" id="categoryKindTabs">
                  <button class="segmented-btn active" data-cat-kind="all" type="button">Все</button>
                  <button class="segmented-btn" data-cat-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-cat-kind="income" type="button">Доход</button>
                </div>
              </div>
            </div>

            <div id="categoriesBulkBar" class="bulk-bar sticky-bar">
              <span id="categoriesSelectedCount" class="bulk-count-text">Ничего не выбрано</span>
              <div class="bulk-actions-fixed">
                <button id="bulkEditCategoriesBtn" class="btn btn-secondary bulk-action hidden-action" type="button">Редактировать выбранные</button>
                <button id="bulkDeleteCategoriesBtn" class="btn btn-danger bulk-action hidden-action" type="button">Удалить выбранные</button>
              </div>
            </div>
            <div class="table-search-row sticky-search">
              <input id="categorySearchQ" class="table-search-input" type="text" placeholder="Поиск" />
              <button id="deleteAllCategoriesBtn" class="btn btn-danger" type="button">Удалить все</button>
            </div>

            <div class="table-wrap">
              <table class="table table-hover">
                <thead>
                  <tr>
                    <th class="select-col"><input id="categoriesSelectAll" class="table-checkbox" type="checkbox" /></th>
                    <th>Группа</th>
                    <th>Название</th>
                    <th>Тип</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="categoriesBody"></tbody>
              </table>
            </div>
            <div id="categoriesInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="debtsSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Карточки долгов</h3>
                <p class="subtitle">Активные долги по контрагентам</p>
              </div>
            </div>
            <div class="table-search-row">
              <input id="debtSearchQ" class="table-search-input" type="text" placeholder="Поиск по контрагенту/комментарию" />
              <div class="toolbar">
                <div class="segmented" id="debtStatusTabs" role="tablist" aria-label="Статус долгов">
                  <button class="segmented-btn active" data-debt-status="active" type="button">Активные</button>
                  <button class="segmented-btn" data-debt-status="all" type="button">Все</button>
                  <button class="segmented-btn" data-debt-status="closed" type="button">Закрытые</button>
                </div>
                <div class="segmented" id="debtSortTabs" role="tablist" aria-label="Сортировка долгов">
                  <button class="segmented-btn active" data-debt-sort="priority" type="button">Приоритет</button>
                  <button class="segmented-btn" data-debt-sort="amount" type="button">По сумме</button>
                  <button class="segmented-btn" data-debt-sort="name" type="button">По имени</button>
                </div>
              </div>
            </div>
            <div id="debtsCards" class="debt-cards"></div>
            <div id="debtsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="settingsSection" class="section-block hidden">
          <section class="panel">
            <form id="settingsForm" class="settings-form">
              <section class="settings-block">
                <h3>Регион</h3>
                <label class="field">
                  <span>Таймзона</span>
                  <select id="timezoneSelect">
                    <option value="auto">Авто (из браузера)</option>
                    <option value="Europe/Moscow">Europe/Moscow</option>
                    <option value="Europe/Kaliningrad">Europe/Kaliningrad</option>
                    <option value="Europe/Samara">Europe/Samara</option>
                    <option value="Asia/Yekaterinburg">Asia/Yekaterinburg</option>
                    <option value="Asia/Omsk">Asia/Omsk</option>
                    <option value="Asia/Krasnoyarsk">Asia/Krasnoyarsk</option>
                    <option value="Asia/Irkutsk">Asia/Irkutsk</option>
                    <option value="Asia/Yakutsk">Asia/Yakutsk</option>
                    <option value="Asia/Vladivostok">Asia/Vladivostok</option>
                    <option value="Asia/Magadan">Asia/Magadan</option>
                    <option value="Asia/Kamchatka">Asia/Kamchatka</option>
                    <option value="UTC">UTC</option>
                  </select>
                </label>
              </section>
              <section class="settings-block">
                <h3>Интерфейс</h3>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Валюта</span>
                    <select id="currencySelect">
                      <option value="BYN">BYN (Br)</option>
                      <option value="RUB">RUB (₽)</option>
                      <option value="USD">USD (\\$)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="GBP">GBP (£)</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>Позиция символа</span>
                    <select id="currencyPositionSelect">
                      <option value="suffix">Справа</option>
                      <option value="prefix">Слева</option>
                    </select>
                  </label>
                </div>
                <div id="currencyPreview" class="settings-preview">Пример: 1 234,56 Br</div>
                <label class="settings-switch-row">
                  <input id="showDashboardDebtsToggle" type="checkbox" checked />
                  <span>Показывать карточки долгов на дашборде</span>
                </label>
                <div class="settings-scale-row">
                  <label class="field">
                    <span>Масштаб интерфейса: <strong id="uiScaleValue">100%</strong></span>
                    <input id="uiScaleRange" type="range" min="90" max="115" step="5" value="100" />
                  </label>
                  <button id="resetUiScaleBtn" class="btn btn-secondary btn-xs" type="button">Сбросить 100%</button>
                </div>
              </section>
              <div class="settings-actions">
                <button id="saveSettingsBtn" class="btn btn-primary" type="submit">Сохранить настройки</button>
              </div>
            </form>
            <section class="panel danger-zone">
              <h3>Danger Zone</h3>
              <p class="subtitle">Удаление аккаунта удалит все операции, долги, категории и настройки без возможности восстановления.</p>
              <div class="danger-zone-actions">
                <input id="deleteMePhrase" type="text" placeholder="Введите УДАЛИТЬ для подтверждения" />
                <button id="deleteMeBtn" class="btn btn-danger" type="button">Удалить меня</button>
              </div>
            </section>
          </section>
        </section>

      </main>
    </div>
`;
})();
