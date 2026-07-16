(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shell = `

    <div id="appShell" class="app-shell hidden">
      <div id="mobileNavOverlay" class="mobile-nav-overlay hidden"></div>
      <button id="mobileNavToggleBtn" class="mobile-nav-toggle" type="button" aria-label="Открыть меню" aria-expanded="false">☰</button>
      <aside class="sidebar" id="sidebarNav">
        <div class="sidebar-main">
          <div class="sidebar-head">
            <div class="brand" aria-label="ФинАсист">
              <img src="/static/favicon.svg?v=2" alt="" width="40" height="40" />
            </div>
            <button id="mobileNavCloseBtn" class="mobile-nav-close" type="button" aria-label="Закрыть меню">×</button>
          </div>
          <div class="sidebar-today">
            <div id="todayWeekday" class="today-weekday">Сегодня</div>
            <div id="todayDate" class="today-date">--</div>
          </div>

          <nav class="nav" id="mainNav">
            <div class="nav-group-title">Обзор</div>
            <button class="nav-btn active" data-section="dashboard">Дашборд</button>
            <button class="nav-btn" data-section="analytics">Аналитика</button>
            <div class="nav-group-title">Учет</div>
            <button class="nav-btn" data-section="operations">Операции</button>
            <button class="nav-btn" data-section="currency">Валюта</button>
            <button class="nav-btn" data-section="plans">Планы</button>
            <button class="nav-btn" data-section="debts">Долги</button>
            <button class="nav-btn" data-section="categories">Категории</button>
            <button class="nav-btn" data-section="item_catalog">Каталог позиций</button>
            <div class="nav-group-title">Система</div>
            <button id="adminNavBtn" class="nav-btn hidden" data-section="admin">Админ</button>
            <button class="nav-btn" data-section="settings">Настройки</button>
          </nav>
        </div>

        <div class="user-area">
          <div id="sessionStatusRow" class="session-status-panel hidden">
            <div class="session-status-copy">
              <span>Сессия</span>
              <strong id="sessionRemainingLabel">30 мин</strong>
            </div>
            <button id="sessionRefreshBtn" class="btn btn-secondary session-renew-btn" type="button" title="Продлить сессию">Продлить</button>
          </div>
          <div class="user-block user-block-static">
            <div class="avatar" id="userAvatar" aria-hidden="true">П</div>
            <div class="meta">
              <div id="userName">Пользователь</div>
              <div id="userHandle">Telegram</div>
            </div>
            <button id="sidebarLogoutBtn" class="user-logout-icon-btn" type="button" title="Выйти" aria-label="Выйти">
              <svg class="user-logout-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M13 8l5 4-5 4" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M18 12H9" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"></path>
              </svg>
            </button>
          </div>
        </div>
      </aside>

      <main class="main">
        <header class="topbar">
          <div class="topbar-title-block">
            <button id="sectionBackBtn" class="section-back-btn hidden" type="button" aria-label="Назад" title="Назад">
              <span class="section-back-btn-icon" aria-hidden="true">←</span>
            </button>
            <div>
            <h2 id="sectionTitle">Дашборд</h2>
            <p class="subtitle" id="sectionSubtitle">Доходы, расходы и быстрый контроль результата</p>
            </div>
          </div>
          <div class="top-actions">
            <div class="cta-row">
              <button id="addOperationCta" class="btn btn-cta" type="button">+ Добавить операцию</button>
              <button id="batchOperationCta" class="btn btn-secondary" type="button">+ Массовое добавление</button>
              <button id="addPlanCta" class="btn btn-cta hidden" type="button">+ Создать план</button>
              <button id="addDebtCta" class="btn btn-cta hidden" type="button">+ Новый долг</button>
              <button id="addCategoryCta" class="btn btn-cta hidden" type="button">+ Создать категорию</button>
              <button id="addGroupCta" class="btn btn-secondary hidden" type="button">+ Создать группу</button>
              <button id="batchCategoryCta" class="btn btn-secondary hidden" type="button">+ Массовое добавление</button>
              <button id="addItemTemplateCta" class="btn btn-cta hidden" type="button">+ Создать позицию</button>
              <button id="addItemSourceCta" class="btn btn-secondary hidden" type="button">+ Создать источник</button>
              <button id="batchItemCatalogCta" class="btn btn-secondary hidden" type="button">+ Массовое добавление</button>
            </div>
          </div>
        </header>

        ${window.App.templates.shellSections || ""}

      </main>
      <div id="sessionRecoveryOverlay" class="session-recovery-overlay hidden" role="dialog" aria-modal="true" aria-labelledby="sessionRecoveryTitle">
        <section class="session-recovery-panel">
          <div class="login-brand-motion" aria-hidden="true">
            <img class="login-brand-mark" src="/static/favicon.svg?v=2" alt="" width="52" height="52" />
          </div>
          <h3 id="sessionRecoveryTitle">Нужно обновить сессию</h3>
          <p id="sessionRecoveryMessage">Данные формы сохранены. Обновите авторизацию, чтобы продолжить.</p>
          <button id="sessionRecoveryBtn" class="btn btn-primary" type="button">Продолжить через Telegram</button>
        </section>
      </div>
      <div id="financeCalculatorOverlay" class="finance-calculator-overlay hidden" aria-hidden="true"></div>
      <aside id="financeCalculatorDrawer" class="finance-calculator-drawer hidden" aria-label="Финансовый калькулятор" aria-hidden="true">
        <div class="finance-calculator-head">
          <div>
            <h3>Калькулятор</h3>
            <p class="muted-small">Скидки, изменения цены и быстрые расчеты</p>
          </div>
          <button id="financeCalculatorClose" class="btn btn-secondary finance-calculator-close" type="button" aria-label="Закрыть калькулятор">×</button>
        </div>
        <div id="financeCalculatorTabs" class="segmented finance-calculator-tabs" role="tablist" aria-label="Режим калькулятора">
          <button class="segmented-btn active" type="button" data-calculator-mode="discount">Скидка</button>
          <button class="segmented-btn" type="button" data-calculator-mode="change">Изменение</button>
          <button class="segmented-btn" type="button" data-calculator-mode="unit">За единицу</button>
          <button class="segmented-btn" type="button" data-calculator-mode="split">Разделить</button>
        </div>
        <div id="financeCalculatorFields" class="finance-calculator-fields"></div>
        <div id="financeCalculatorResult" class="finance-calculator-result" aria-live="polite"></div>
      </aside>
    </div>
`;
})();
