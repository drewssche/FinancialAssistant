(() => {
  let sequence = 0;
  const {state, core} = window.App;
  function mount(host, {select, ownerDialog, onCreated}) {
    const utils = window.App.getRuntimeModule('picker-utils');
    const input = document.createElement('input');
    input.type = 'search'; input.autocomplete = 'off'; input.placeholder = 'Категория, товар или тег';
    input.setAttribute('aria-label', 'Категория позиции'); input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list'); input.setAttribute('aria-expanded', 'false');
    const list = document.createElement('div');
    list.id = 'scanCategoryOptions' + (++sequence);
    list.className = 'scan-category-picker app-popover app-popover-floating hidden'; list.setAttribute('role', 'listbox');
    input.setAttribute('aria-controls', list.id);
    list.dataset.popoverAlign = 'start'; list.dataset.popoverMaxHeight = '360';
    select.hidden = true; select.tabIndex = -1;
    host.append(input, list);
    let opened = false, active = -1;
    const selected = () => state.categories.find(c => String(c.id) === select.value);
    function sync() {
      if (opened) return;
      input.value = selected()?.name || '';
      input.title = select.title;
      core.setCategoryInputIcon(input, selected() || null);
    }
    function close() {
      opened = false; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');
      utils.setPopoverOpen(list, false); sync();
    }
    function choose(value) {
      if (value && ![...select.options].some(option => option.value === value)) {
        const category = state.categories.find(c => String(c.id) === value);
        if (category) select.add(core.createCategoryOption(category));
      }
      select.value = value;
      select.dispatchEvent(new Event('change', {bubbles: true}));
      close(); input.focus({preventScroll: true});
    }
    function render() {
      const raw = input.value.trim(), query = raw === selected()?.name ? '' : raw;
      const categories = utils.sortCategoriesByUsage(state.categories.filter(c => c.kind === 'expense'), query);
      list.replaceChildren(); active = -1;
      input.removeAttribute('aria-activedescendant');
      const add = (html, value) => {
        const button = utils.createChipButton({html, selected: select.value === value});
        button.setAttribute('role', 'option'); button.setAttribute('aria-selected', String(select.value === value));
        button.onclick = () => choose(value); list.append(button);
      };
      add(core.renderMetaChip('Без категории'), '');
      categories.forEach(c => add(utils.categorySearchHtml(c, query), String(c.id)));
      if (query && !categories.some(c => window.App.search.normalize(c.name) === window.App.search.normalize(query))) {
        const create = utils.createActionChipButton({label: `+ Создать категорию «${query}»`});
        create.setAttribute('role', 'option'); create.setAttribute('aria-selected', 'false');
        create.onclick = () => {
          close();
          window.App.categoryUi.openCreateCategoryModal({kind: 'expense', prefillName: query, ownerDialog,
            onCreated: category => { if (host.isConnected && ownerDialog.open) {onCreated(category); sync(); input.focus({preventScroll:true});} }});
        };
        list.append(create);
      }
      utils.pinCreateActions(list, {stack: true});
      [...list.querySelectorAll('[role=option]')].forEach((button, i) => button.id = list.id + '-' + i);
    }
    function open() {
      render(); opened = true; input.setAttribute('aria-expanded', 'true');
      utils.setPopoverOpen(list, true, {owners:[host], onClose: () => {opened=false;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');sync();}});
    }
    input.oninput = open;
    input.onclick = open;
    input.onkeydown = event => {
      if (event.key === 'Escape' && opened) {event.preventDefault();event.stopPropagation();close();return;}
      if (!['ArrowDown','ArrowUp','Enter'].includes(event.key)) return;
      event.preventDefault();
      if (!opened) {if(event.key !== 'Enter')open();return;}
      const buttons = [...list.querySelectorAll('[role=option]')];
      if (event.key === 'Enter') {if(active>=0)buttons[active]?.click();return;}
      active = active < 0 ? (event.key === 'ArrowDown' ? 0 : buttons.length - 1) : (active + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
      buttons.forEach((b,i) => b.classList.toggle('is-focused',i===active));
      input.setAttribute('aria-activedescendant',buttons[active].id);
      buttons[active].scrollIntoView({block:'nearest'});
    };
    host.closeCategoryPicker = close;
    return {sync, close};
  }
  window.App.scanCategoryPicker = {mount};
})();
