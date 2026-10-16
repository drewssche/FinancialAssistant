(() => {
  // Keep native select values, validation and events; replace only the OS popup.
  let source = null, ownerObserver = null;
  const dialog = document.createElement('dialog');
  dialog.className = 'choice-dialog'; dialog.id = 'appChoiceDialog';
  dialog.setAttribute('aria-labelledby', 'choiceDialogTitle');
  dialog.innerHTML = `<header><h3 id="choiceDialogTitle">Выбрать</h3><button type="button" class="btn btn-secondary btn-icon" aria-label="Закрыть выбор" title="Закрыть">${window.App.icons.svg('close')}</button></header><input type="search" aria-label="Поиск вариантов" placeholder="Поиск" autocomplete="off"><div class="choice-results" role="group" aria-label="Варианты"></div><p role="status" class="muted-small"></p>`;
  document.body.append(dialog);
  const search = dialog.querySelector('input'), results = dialog.querySelector('.choice-results');
  function render() {
    if (!source) return;
    results.replaceChildren();
    for (const option of source.options) {
      if (option.hidden || !window.App.search.matches(option.textContent, search.value)) continue;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'choice-option';
      const category = option.dataset.categoryId
        ? window.App.state.categories.find(item => String(item.id) === option.dataset.categoryId) : null;
      if (category) button.innerHTML = window.App.core.renderCategoryChip(category, search.value);
      else button.textContent = option.textContent;
      button.disabled = option.disabled || option.closest('optgroup')?.disabled || false;
      button.setAttribute('aria-pressed', String(option.selected));
      button.addEventListener('click', () => {
        const target = source;
        const row = target?.closest('.receipt-item-row');
        const field = target?.dataset.receiptField;
        dialog.close();
        if (!target?.isConnected || target.disabled) return;
        target.value = option.value;
        target.dispatchEvent(new Event('input', {bubbles: true}));
        target.dispatchEvent(new Event('change', {bubbles: true}));
        const replacement = row && field ? document.querySelector(`[data-receipt-mode="${row.dataset.receiptMode}"][data-receipt-item-id="${row.dataset.receiptItemId}"] select[data-receipt-field="${CSS.escape(field)}"]`) : null;
        (target.isConnected ? target : replacement)?.focus({preventScroll: true});
      });
      results.append(button);
    }
    dialog.querySelector('[role="status"]').textContent = results.children.length ? '' : 'Ничего не найдено';
  }
  function open(select) {
    if (select.disabled || select.multiple || select.size > 1) return;
    source = select;
    select.setAttribute('aria-haspopup','dialog'); select.setAttribute('aria-controls',dialog.id); select.setAttribute('aria-expanded','true');
    dialog.querySelector('h3').textContent = select.getAttribute('aria-label') || select.labels?.[0]?.querySelector('span')?.textContent || select.title || 'Выбрать';
    ownerObserver?.disconnect();
    const owner = select.closest('.modal');
    if(owner) {ownerObserver=new MutationObserver(() => {if(owner.classList.contains('hidden'))dialog.close();}); ownerObserver.observe(owner,{attributes:true,attributeFilter:['class']});}
    search.value = ''; render(); dialog.showModal(); search.focus();
  }
  search.addEventListener('input', render);
  dialog.querySelector('header button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => {if (e.target === dialog) dialog.close();});
  dialog.addEventListener('close', () => {if(dialog.open)return; ownerObserver?.disconnect(); source?.setAttribute('aria-expanded','false'); if (source?.isConnected) source.focus({preventScroll:true}); source = null;});
  document.addEventListener('pointerdown', e => {
    const select = e.target.closest('select');
    if (!select || select.multiple || select.size > 1 || select.disabled) return;
    e.preventDefault(); open(select);
  }, true);
  document.addEventListener('keydown', e => {
    if (dialog.open) {
      // Escape must close only this picker, never its parent editor.
      if (e.key === 'Escape') {e.preventDefault(); e.stopImmediatePropagation(); dialog.close();}
      if (['ArrowDown', 'ArrowUp'].includes(e.key)) {
        e.preventDefault(); e.stopImmediatePropagation();
        const buttons = [...results.querySelectorAll('button:not(:disabled)')];
        const index = buttons.indexOf(document.activeElement);
        buttons[(index + (e.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length]?.focus();
      }
      if (e.key === 'Enter' && e.target === search) {e.preventDefault(); e.stopImmediatePropagation(); results.querySelector('button:not(:disabled)')?.click();}
      return;
    }
    if (e.target.matches('select') && !e.target.multiple && e.target.size <= 1 && ['Enter',' ','ArrowDown','ArrowUp'].includes(e.key)) {e.preventDefault(); e.stopImmediatePropagation(); open(e.target);}
  }, true);
})();

(() => {
  const panels = new Set();
  // Retain controls inside their original form so submission and draft identity stay intact.
  function attach(content, title, toolbar) {
    const dialog = document.createElement('dialog'); dialog.className = 'choice-dialog task-dialog';
    const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-secondary btn-icon';
    button.title = title; button.setAttribute('aria-label', title); button.innerHTML = window.App.icons.svg('filter');
    dialog.setAttribute('aria-label', title);
    const header = document.createElement('header'), heading = document.createElement('h3'), close = document.createElement('button');
    heading.textContent=title; close.type='button'; close.className='btn btn-secondary btn-icon'; close.title='Закрыть'; close.setAttribute('aria-label','Закрыть настройки'); close.innerHTML=window.App.icons.svg('close');
    header.append(heading,close); content.before(dialog); dialog.append(header,content);
    toolbar.prepend(button); panels.add(dialog);
    button.addEventListener('click', () => dialog.showModal());
    close.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', e => {if(e.target===dialog)dialog.close();});
    dialog.addEventListener('close', () => button.focus({preventScroll:true}));
    const owner=content.closest('.modal, .section-block');
    const sync = () => {button.hidden=content.classList.contains('hidden'); if((button.hidden||owner?.classList.contains('hidden'))&&dialog.open)dialog.close();};
    const observer=new MutationObserver(sync); observer.observe(content,{attributes:true,attributeFilter:['class']});
    if(owner)observer.observe(owner,{attributes:true,attributeFilter:['class']}); sync();
    dialog.trigger = button;
    return dialog;
  }
  document.addEventListener('keydown', e => {
    if(e.key!=='Escape')return;
    const dialog=[...panels].find(d=>d.open); if(!dialog)return;
    e.preventDefault();e.stopImmediatePropagation();dialog.close();
  },true);
  window.App.taskDialogs={attach};
})();

(() => {
  const dialog = document.createElement('dialog');
  dialog.className = 'choice-dialog help-dialog';
  dialog.setAttribute('aria-labelledby', 'appHelpTitle');
  dialog.innerHTML = `<header><h3 id="appHelpTitle"></h3><button type="button" class="btn btn-secondary btn-icon" aria-label="Закрыть справку" title="Закрыть справку">${window.App.icons.svg('close')}</button></header><p class="help-dialog-text"></p>`;
  document.body.append(dialog);
  let trigger = null, observer = null;
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-help-text]');
    if (!button) return;
    trigger = button;
    dialog.querySelector('h3').textContent = button.dataset.helpTitle || 'Справка';
    dialog.querySelector('p').textContent = button.dataset.helpText;
    observer?.disconnect();
    const owner = button.closest('.modal, dialog, .section-block');
    if (owner) {
      observer = new MutationObserver(() => {
        if (!button.isConnected || owner.classList.contains('hidden') || owner.hidden || (owner.tagName === 'DIALOG' && !owner.open)) dialog.close();
      });
      observer.observe(owner, {attributes:true, attributeFilter:['class','hidden','open'], childList:true, subtree:true});
    }
    dialog.showModal();
  });
  dialog.querySelector('button').onclick = () => dialog.close();
  dialog.addEventListener('click', event => {if(event.target===dialog)dialog.close();});
  document.addEventListener('keydown', event => {
    if (!dialog.open || event.key !== 'Escape') return;
    event.preventDefault();event.stopImmediatePropagation();dialog.close();
  }, true);
  dialog.addEventListener('close', () => {
    observer?.disconnect();observer=null;
    if(trigger?.isConnected)trigger.focus({preventScroll:true});trigger=null;
  });
})();
