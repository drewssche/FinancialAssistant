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
      document.getElementById('settingsForm').classList.toggle('hidden', ['data','reports'].includes(view));
    }
    nav.addEventListener('click', event => {
      const button = event.target.closest('[data-settings-view]');
      if (button) {select(button.dataset.settingsView);if(button.dataset.settingsView==='data')loadPhotos();if(button.dataset.settingsView==='reports')loadReports();}
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
    const reportForm=document.getElementById('reportSettingsForm'), reportFields=document.getElementById('reportSettingsFields');
    const reportStatus=document.getElementById('reportSettingsStatus'), reportNext=document.getElementById('reportNextSend');
    let reportAccount=null, reportsLoading=false, reportDirty=false, reportData=null;
    const reportKeys=['enabled','weekly','monthly','yearly','telegram','email'];
    const emailInput=document.getElementById('reportEmailInput'), emailCode=document.getElementById('reportEmailCode');
    const emailStatus=document.getElementById('reportEmailStatus');
    const accountKey=()=>JSON.stringify(window.App.core.authHeaders());
    function showRecipients(data){
      reportData=data;
      document.getElementById('reportEmailRecipient').textContent=data.email_address?'Подтверждена: '+data.email_address:'Сначала подтвердите адрес';
      document.getElementById('reportTelegramRecipient').textContent=data.telegram_account||'Telegram текущего аккаунта';
      const bot=document.getElementById('reportTelegramBot');
      const botUrl=/^https:\/\/t\.me\/[A-Za-z0-9_]+$/.test(data.telegram_bot_url||'')?data.telegram_bot_url:null;
      bot.classList.toggle('hidden',!botUrl);if(botUrl)bot.href=botUrl;else bot.removeAttribute('href');
      emailInput.value=data.pending_email||data.email_address||'';
      document.getElementById('reportEmailVerification').classList.toggle('hidden',!data.pending_email);
      document.getElementById('reportEmailPending').textContent=data.pending_email?'Код для '+data.pending_email+' действует 15 минут.'+(data.email_address?' До подтверждения отчёты идут на прежний адрес.':''):'';
      document.getElementById('reportEmailRemove').classList.toggle('hidden',!data.email_address&&!data.pending_email);
      reportForm.elements.email.disabled=!data.email_address;
      if(!data.email_address)reportForm.elements.email.checked=false;
    }
    function showReports(data){
      reportKeys.forEach(key=>reportForm.elements[key].checked=data.settings[key]);
      reportForm.elements.send_time.value=data.settings.send_time;
      reportFields.disabled=!data.available;
      showRecipients(data);
      reportNext.textContent=!data.available?'Рассылка для профиля не подключена':!data.settings.enabled?'Рассылка приостановлена':data.next_send?'Ближайшая отправка: '+new Intl.DateTimeFormat('ru-RU',{timeZone:'Europe/Minsk',dateStyle:'long',timeStyle:'short'}).format(new Date(data.next_send)):'Нет запланированной отправки';
    }
    async function loadReports(){
      const account=accountKey();
      if(reportsLoading || (reportDirty && reportAccount===account))return;
      reportsLoading=true;reportFields.disabled=true;reportStatus.textContent='Загрузка настроек…';
      if(reportAccount!==account){emailInput.value='';emailCode.value='';document.getElementById('reportEmailRecipient').textContent='';document.getElementById('reportEmailPending').textContent='';document.getElementById('reportEmailVerification').classList.add('hidden');}
      try{const data=await window.App.core.requestJson('/api/v1/preferences/financial-reports',{headers:window.App.core.authHeaders()});
        if(account!==accountKey())return;
        showReports(data);reportAccount=account;reportDirty=false;reportStatus.textContent=data.available?'Изменения применяются после сохранения.':'Рассылка для этого профиля пока не подключена.';
      }catch(error){if(account===accountKey())reportStatus.textContent=error.message||'Не удалось загрузить настройки. Откройте вкладку ещё раз.';}
      finally{reportsLoading=false;}
    }
    reportForm.addEventListener('change',event=>{if(reportKeys.includes(event.target.name)||event.target.name==='send_time'){reportDirty=true;reportStatus.textContent='Есть несохранённые изменения.';}});
    async function emailAction(action){
      const account=accountKey();if(account!==reportAccount)return;
      const address=emailInput.value.trim();
      if(action!=='remove'&&(!address||!emailInput.checkValidity())){emailStatus.textContent='Укажите корректный адрес почты.';emailInput.focus();return;}
      if(action==='confirm'&&!/^[0-9]{6}$/.test(emailCode.value.trim())){emailStatus.textContent='Введите шестизначный код из письма.';emailCode.focus();return;}
      reportFields.disabled=true;emailStatus.textContent='Обработка…';
      try{
        const payload={email_address:address};if(action==='confirm')payload.code=emailCode.value.trim();
        const data=await window.App.core.requestJson('/api/v1/preferences/financial-reports/email'+(action==='remove'?'':'/'+action),{method:action==='remove'?'DELETE':'POST',headers:window.App.core.authHeaders(),...(action==='remove'?{}:{body:JSON.stringify(payload)})});
        if(account!==accountKey())return;
        if(action==='remove'){
          // Removing the address persists channel deactivation, independently of the draft.
          if(!reportDirty)showReports(data);else{showRecipients(data);reportForm.elements.email.checked=false;}
        }else showRecipients(data);
        emailCode.value='';
        emailStatus.textContent=action==='request'?'Код отправлен. Повторный запрос — через минуту, не более 5 писем в сутки.':action==='confirm'?'Почта подтверждена. Включите канал «Почта» и сохраните рассылку.':'Почта отключена.';
      }catch(error){if(account===accountKey())emailStatus.textContent=error.message||'Не удалось выполнить действие.';}
      finally{if(account===accountKey())reportFields.disabled=!reportData?.available;}
    }
    document.getElementById('reportEmailRequest').onclick=()=>emailAction('request');
    document.getElementById('reportEmailConfirm').onclick=()=>emailAction('confirm');
    document.getElementById('reportEmailRemove').onclick=()=>emailAction('remove');
    reportForm.addEventListener('submit',async event=>{
      event.preventDefault();const account=accountKey();if(account!==reportAccount)return;
      const data=Object.fromEntries(reportKeys.map(key=>[key,reportForm.elements[key].checked]));data.send_time=reportForm.elements.send_time.value;
      if(data.enabled && (!['weekly','monthly','yearly'].some(k=>data[k]) || !['telegram','email'].some(k=>data[k]))){reportStatus.textContent='Выберите хотя бы один период и один канал доставки.';return;}
      reportFields.disabled=true;reportStatus.textContent='Сохранение…';
      try{const saved=await window.App.core.requestJson('/api/v1/preferences/financial-reports',{method:'PUT',headers:window.App.core.authHeaders(),body:JSON.stringify(data)});
        if(account!==accountKey())return;
        showReports(saved);reportDirty=false;reportStatus.textContent='Настройки рассылки сохранены.';emailStatus.textContent=saved.email_address?'Подтверждённый адрес можно заменить или отключить.':'Адрес подключается после подтверждения кодом из письма.';
      }catch(error){if(account===accountKey()){reportFields.disabled=false;reportStatus.textContent=error.message||'Не удалось сохранить. Изменения остались в форме.';}}
    });
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
