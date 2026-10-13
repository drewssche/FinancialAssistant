(() => {
  function bind() {
    const root = document.getElementById('settingsSection');
    const nav = document.getElementById('settingsViewTabs');
    const panels = [...root.querySelectorAll('[data-settings-panel]')];
    function select(view) {
      if (!panels.some(node => node.dataset.settingsPanel === view)) return;
      panels.forEach(node => node.classList.toggle('hidden', node.dataset.settingsPanel !== view));
      nav.querySelectorAll('button').forEach(button => {
        const active = button.dataset.settingsView === view;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      document.getElementById('settingsForm').classList.toggle('hidden', view === 'data');
    }
    nav.addEventListener('click', event => {
      const button = event.target.closest('[data-settings-view]');
      if (button) select(button.dataset.settingsView);
    });
    // Hidden pages retain their inputs, listeners and unsaved field values.
    // Reveal invalid fields before native validation tries to focus them.
    root.addEventListener('invalid', event => {
      const panel = event.target.closest('[data-settings-panel]');
      if (panel) select(panel.dataset.settingsPanel);
    }, true);
    const icons = window.App.icons;
    for (const [id, icon, label] of [
      ['addCategoryCta', 'plus', 'Создать категорию'],
      ['addGroupCta', 'folderPlus', 'Создать группу'],
      ['batchCategoryCta', 'upload', 'Массовое добавление категорий'],
      ['resetUiScaleBtn', 'refresh', 'Масштаб 100%'],
      ['addBankCurrencyAlertBtn', 'plus', 'Добавить порог банковского курса'],
      ['categoriesCollapseAllBtn', 'collapse', 'Свернуть группы'],
      ['categoriesExpandAllBtn', 'expand', 'Развернуть группы'],
      ['deleteAllCategoriesBtn', 'trash', 'Удалить все категории'],
    ]) icons.apply(document.getElementById(id), icon, label);
    for (const id of ['addCategoryCta', 'addGroupCta', 'batchCategoryCta']) {
      document.getElementById(id)?.classList.add('directory-header-action');
    }
  }
  window.App.registerRuntimeModule('settings-layout', {bind});
})();
