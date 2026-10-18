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
      if (button) {select(button.dataset.settingsView);if(button.dataset.settingsView==='data')loadPhotos();}
    });
    // Hidden pages retain their inputs, listeners and unsaved field values.
    // Reveal invalid fields before native validation tries to focus them.
    root.addEventListener('invalid', event => {
      const panel = event.target.closest('[data-settings-panel]');
      if (panel) select(panel.dataset.settingsPanel);
    }, true);
    let photoStats={count:0,bytes:0}, loading=false;
    const photoButton=document.getElementById('deleteReceiptPhotos'), photoStatus=document.getElementById('receiptPhotoStorage');
    const size=bytes=>bytes<1024*1024?`${(bytes/1024).toFixed(0)} КБ`:`${(bytes/1024/1024).toFixed(1)} МБ`;
    async function loadPhotos(){
      if(loading)return;loading=true;photoButton.disabled=true;photoStatus.textContent='Загрузка…';
      try{photoStats=await window.App.core.requestJson('/api/v1/operations/receipt-photos/storage',{headers:window.App.core.authHeaders()});
        photoStatus.textContent=photoStats.count?`${photoStats.count} фото · ${size(photoStats.bytes)}`:'Нет сохранённых фото';
        photoButton.disabled=!photoStats.count;
      }catch(error){photoStatus.textContent=error.message||'Не удалось получить размер фото';}finally{loading=false;}
    }
    photoButton.onclick=()=>window.App.core.showConfirm(
      `Удалить ${photoStats.count} фото чеков (${size(photoStats.bytes)})? Операции, позиции и распознанный текст останутся.`,async()=>{
        photoButton.disabled=true;
        try{await window.App.core.requestJson('/api/v1/operations/receipt-photos/storage',{method:'DELETE',headers:window.App.core.authHeaders()});
          window.App.getRuntimeModule('receipt-scan').photosDeleted();await loadPhotos();
        }catch(error){photoStatus.textContent=error.message||'Не удалось удалить фото';photoButton.disabled=false;}
      },{title:'Удалить фото чеков',confirmLabel:'Удалить фото'});
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
