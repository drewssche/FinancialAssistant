(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shellSectionsSecondary = `

        <section id="plansSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Плановые операции</h3>
              </div>
            </div>
            <div id="plansKpiGrid" class="plans-kpi-shell">
              <article class="kpi-card plans-financial-kpi-card">
                <div class="plans-financial-kpi-head">
                  <h3>Баланс с учетом планов</h3>
                  <div id="plansStatusChips" class="analytics-kpi-secondary plans-status-chips">
                    <span id="plansDueChip" class="analytics-kpi-chip analytics-kpi-chip-neutral">К подтверждению: 0</span>
                    <span id="plansOverdueChip" class="analytics-kpi-chip analytics-kpi-chip-negative">Просрочено: 0</span>
                  </div>
                </div>
                <div class="plans-financial-kpi-line">
                  <div id="plansFinancialValue" class="plans-financial-kpi-value">0,00 руб.</div>
                  <div id="plansFinancialDelta" class="plans-financial-kpi-delta">+0,00 руб.</div>
                </div>
                <div id="plansFinancialMeta" class="subtitle plans-financial-kpi-meta">После планов: 0,00 руб.</div>
              </article>
            </div>
            <div class="plans-controls-row">
              <div class="toolbar section-action-toolbar search-toolbar plans-toolbar">
                <div class="segmented" id="plansTabTabs" role="tablist" aria-label="Вкладки планов">
                  <button class="segmented-btn active" data-plan-tab="due" type="button">К подтверждению</button>
                  <button class="segmented-btn" data-plan-tab="oneoff" type="button">Разовые</button>
                  <button class="segmented-btn" data-plan-tab="recurring" type="button">Регулярные</button>
                  <button class="segmented-btn" data-plan-tab="history" type="button">История</button>
                </div>
                <div class="segmented" id="plansKindTabs" role="tablist" aria-label="Тип планов">
                  <button class="segmented-btn active" data-plan-kind="all" type="button">Все</button>
                  <button class="segmented-btn" data-plan-kind="expense" type="button">Расход</button>
                  <button class="segmented-btn" data-plan-kind="income" type="button">Доход</button>
                </div>
                <div class="segmented" id="plansStatusTabs" role="tablist" aria-label="Статус сроков планов">
                  <button class="segmented-btn active" data-plan-status="all" type="button">Все сроки</button>
                  <button class="segmented-btn" data-plan-status="overdue" type="button">Просрочено</button>
                  <button class="segmented-btn" data-plan-status="due" type="button">Сегодня</button>
                  <button class="segmented-btn" data-plan-status="upcoming" type="button">Впереди</button>
                </div>
                <div class="segmented hidden" id="plansHistoryEventTabs" role="tablist" aria-label="Тип событий истории планов">
                  <button class="segmented-btn active" data-plan-history-event="all" type="button">Все события</button>
                  <button class="segmented-btn" data-plan-history-event="confirmed" type="button">Подтверждения</button>
                  <button class="segmented-btn" data-plan-history-event="skipped" type="button">Пропуски</button>
                  <button class="segmented-btn" data-plan-history-event="reminded" type="button">Напоминания</button>
                </div>
              </div>
            </div>
            <div class="table-search-row plans-search-row">
              <input id="plansSearchQ" class="table-search-input plans-search-input" type="text" placeholder="Поиск по категории/комментарию" />
            </div>
            <div id="plansList" class="plans-list"></div>
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
              <div class="toolbar section-action-toolbar search-toolbar debt-toolbar">
                <div class="segmented debt-toolbar-status" id="debtStatusTabs" role="tablist" aria-label="Статус долгов">
                  <button class="segmented-btn active" data-debt-status="active" type="button">Активные</button>
                  <button class="segmented-btn" data-debt-status="all" type="button">Все</button>
                  <button class="segmented-btn" data-debt-status="closed" type="button">Закрытые</button>
                </div>
                <div class="segmented debt-toolbar-sort" id="debtSortTabs" role="tablist" aria-label="Сортировка долгов">
                  <button class="segmented-btn active" data-debt-sort="priority" type="button">Приоритет</button>
                  <button class="segmented-btn" data-debt-sort="amount" type="button">По сумме</button>
                  <button class="segmented-btn" data-debt-sort="name" type="button">По имени</button>
                </div>
                <button id="deleteAllDebtsBtn" class="btn btn-danger debt-toolbar-danger" type="button">Удалить все</button>
              </div>
            </div>
            <div id="debtsCards" class="debt-cards"></div>
            <div id="debtsInfiniteSentinel" class="infinite-sentinel" aria-hidden="true"></div>
          </section>
        </section>

        <section id="itemCatalogSection" class="section-block hidden">
          <section class="panel">
            <div class="table-search-row">
              <input id="itemCatalogSearchQ" class="table-search-input" type="text" placeholder="Поиск по источнику и позиции" />
              <div class="toolbar section-action-toolbar search-toolbar item-catalog-controls">
                <div class="segmented" id="itemCatalogSortTabs" role="tablist" aria-label="Сортировка каталога позиций">
                  <button class="segmented-btn active" data-item-sort="usage" type="button">Частота</button>
                  <button class="segmented-btn" data-item-sort="recent" type="button">Недавние</button>
                  <button class="segmented-btn" data-item-sort="name" type="button">Имя</button>
                </div>
                <button id="itemCatalogCollapseAllBtn" class="btn btn-secondary btn-xs" type="button">Свернуть все</button>
                <button id="itemCatalogExpandAllBtn" class="btn btn-secondary btn-xs" type="button">Развернуть все</button>
                <button id="deleteAllItemTemplatesBtn" class="btn btn-danger" type="button">Удалить все</button>
              </div>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table item-catalog-table">
                <thead>
                  <tr>
                    <th>Источник</th>
                    <th>Позиция</th>
                    <th>Последняя цена</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody id="itemCatalogBody"></tbody>
              </table>
            </div>
          </section>
        </section>

        <section id="settingsSection" class="section-block hidden">
          <section class="panel">
            <form id="settingsForm" class="settings-form">
              <section class="settings-block">
                <h3>Регион</h3>
                <label class="field">
                  <span>Таймзона</span>
                  <div class="settings-picker-field">
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
                    <button id="timezonePickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                  </div>
                </label>
              </section>
              <section class="settings-block">
                <h3>Интерфейс</h3>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Валюта</span>
                    <div class="settings-picker-field">
                      <select id="currencySelect">
                        <option value="BYN">BYN</option>
                        <option value="RUB">RUB (₽)</option>
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                      </select>
                      <button id="currencyPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                    </div>
                  </label>
                  <label class="field">
                    <span>Позиция символа</span>
                    <div class="settings-picker-field">
                      <select id="currencyPositionSelect">
                        <option value="suffix">Справа</option>
                        <option value="prefix">Слева</option>
                      </select>
                      <button id="currencyPositionPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                    </div>
                  </label>
                </div>
                <div id="currencyPreview" class="settings-preview">Пример: 1 234,56 руб.</div>
                <label class="settings-switch-row">
                  <input id="showDashboardAnalyticsToggle" type="checkbox" checked />
                  <span>Показывать блок аналитики на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardOperationsToggle" type="checkbox" checked />
                  <span>Показывать блок планов на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="showDashboardDebtsToggle" type="checkbox" checked />
                  <span>Показывать карточки долгов на дашборде</span>
                </label>
                <label class="settings-switch-row">
                  <input id="plansRemindersToggle" type="checkbox" checked />
                  <span>Напоминать о планах в Telegram</span>
                </label>
                <label class="field">
                  <span>Строк планов на дашборде</span>
                  <div class="settings-picker-field">
                    <select id="dashboardOperationsLimitSelect">
                      <option value="5">5</option>
                      <option value="8">8</option>
                      <option value="12">12</option>
                    </select>
                    <button id="dashboardOperationsLimitPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                  </div>
                </label>
                <div class="settings-scale-row">
                  <label class="field">
                    <span>Масштаб интерфейса: <strong id="uiScaleValue">100%</strong></span>
                    <input id="uiScaleRange" type="range" min="85" max="115" step="1" value="100" />
                  </label>
                  <button id="resetUiScaleBtn" class="btn btn-secondary btn-xs" type="button">Сбросить 100%</button>
                </div>
              </section>
              <section class="settings-block">
                <h3>Аналитика</h3>
                <div class="settings-grid-2">
                  <label class="field">
                    <span>Топ операций</span>
                    <div class="settings-picker-field">
                      <select id="analyticsTopOperationsLimitSelect">
                        <option value="3">3</option>
                        <option value="5">5</option>
                        <option value="10">10</option>
                      </select>
                      <button id="analyticsTopOperationsLimitPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                    </div>
                  </label>
                  <label class="field">
                    <span>Топ позиций</span>
                    <div class="settings-picker-field">
                      <select id="analyticsTopPositionsLimitSelect">
                        <option value="5">5</option>
                        <option value="10">10</option>
                        <option value="20">20</option>
                      </select>
                      <button id="analyticsTopPositionsLimitPickerBtn" class="btn btn-secondary settings-picker-btn hidden" type="button" aria-haspopup="dialog"></button>
                    </div>
                  </label>
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
                <input id="deleteMePhrase" type="text" placeholder="Введите УДАЛИТЬ" />
                <button id="deleteMeBtn" class="btn btn-danger" type="button">Удалить меня</button>
              </div>
            </section>
          </section>
        </section>

        <section id="adminSection" class="section-block hidden">
          <section class="panel">
            <div class="panel-head row between">
              <div>
                <h3>Управление доступом</h3>
                <p class="subtitle">Апрув, отклонение и удаление пользователей</p>
              </div>
            </div>
            <div class="segmented" id="adminUserStatusTabs" role="tablist" aria-label="Статус пользователей">
              <button class="segmented-btn active" data-admin-user-status="pending" type="button">Ожидают</button>
              <button class="segmented-btn" data-admin-user-status="approved" type="button">Одобрены</button>
              <button class="segmented-btn" data-admin-user-status="rejected" type="button">Отклонены</button>
              <button class="segmented-btn" data-admin-user-status="all" type="button">Все</button>
            </div>
            <div class="table-wrap">
              <table class="table table-hover mobile-card-table admin-users-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Пользователь</th>
                    <th>Telegram</th>
                    <th>Статус</th>
                    <th>Создан</th>
                    <th>Последний вход</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody id="adminUsersBody"></tbody>
              </table>
            </div>
          </section>
        </section>
`;
})();
