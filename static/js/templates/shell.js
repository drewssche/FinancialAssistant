(() => {
  window.App = window.App || {};
  window.App.templates = window.App.templates || {};
  window.App.templates.shell = `

    <div id="appShell" class="app-shell hidden">
      <div id="mobileNavOverlay" class="mobile-nav-overlay hidden"></div>
      <aside class="sidebar" id="sidebarNav">
        <div class="sidebar-head">
          <div class="brand">FA</div>
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
          <button class="nav-btn" data-section="plans">Планы</button>
          <button class="nav-btn" data-section="debts">Долги</button>
          <button class="nav-btn" data-section="categories">Категории</button>
          <button class="nav-btn" data-section="item_catalog">Каталог позиций</button>
          <div class="nav-group-title">Система</div>
          <button id="adminNavBtn" class="nav-btn hidden" data-section="admin">Админ</button>
          <button class="nav-btn" data-section="settings">Настройки</button>
        </nav>

        <div class="user-area">
          <div class="user-block user-block-static">
            <div class="avatar" id="userAvatar">П</div>
            <div class="meta">
              <div id="userName">Пользователь</div>
              <div id="userHandle">Telegram</div>
            </div>
            <button id="sidebarLogoutBtn" class="user-logout-icon-btn" type="button" title="Выйти" aria-label="Выйти">⎋</button>
          </div>
        </div>
      </aside>

      <main class="main">
        <header class="topbar">
          <div class="topbar-title-block">
            <button id="mobileNavToggleBtn" class="mobile-nav-toggle" type="button" aria-label="Открыть меню" aria-expanded="false">☰</button>
            <button id="sectionBackBtn" class="section-back-btn hidden" type="button" aria-label="Назад" title="Назад">
              <span class="section-back-btn-icon" aria-hidden="true">←</span>
              <span id="sectionBackLabel" class="section-back-btn-label">Назад</span>
            </button>
            <div>
            <h2 id="sectionTitle">Дашборд</h2>
            <p class="subtitle" id="sectionSubtitle">Доходы, расходы и быстрый контроль баланса</p>
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
    </div>
`;
})();
