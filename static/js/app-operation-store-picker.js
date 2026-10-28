(() => {
  function bind(owner, mode, config = {}) {
    const input = owner.querySelector('input');
    const utils = window.App.getRuntimeModule('picker-utils');
    const popup = document.createElement('div');
    popup.id = `${mode}ReceiptStoreOptions`;
    popup.className = 'app-popover app-popover-floating receipt-store-options hidden';
    popup.dataset.popoverAlign = 'start';
    popup.dataset.popoverMaxHeight = '280';
    popup.setAttribute('role', 'listbox');
    popup.setAttribute('aria-label', config.label || 'Магазины');
    owner.append(popup);
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', popup.id);
    input.setAttribute('aria-expanded', 'false');
    let active = -1;
    let options = [];
    let loading = false;
    let currentQuery = "";
    const canonical = value => !config.getNames && /(?:^|[^а-яё])либрет[ие]к(?:$|[^а-яё])/i.test(value) ? 'Соседи' : value;
    async function ensureSources() {
      if (config.getNames || loading) return;
      loading = true;
      try {
        await window.App.getRuntimeModule('item-catalog')?.loadItemSources?.();
      } catch (_) { /* The existing names and explicit creation stay available. */ }
      finally {
        loading = false;
        if (owner.isConnected && !popup.classList.contains('hidden')) render(currentQuery);
      }
    }
    function close() {
      utils.setPopoverOpen(popup, false, {owners: [input]});
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      active = -1;
    }
    function choose(name) {
      input.value = canonical(name);
      input.dispatchEvent(new Event('change', {bubbles: true}));
      input.focus({preventScroll: true});
      close();
    }
    function render(query = '') {
      currentQuery = query;
      query = canonical(query);
      const names = [...new Set((config.getNames?.() || (window.App.state.itemSources || []).map(item => item.name)).filter(Boolean))];
      const matches = names.filter(name => window.App.search.matches(name, query))
        .sort((a, b) => window.App.search.compare(query, [a], [b]) || a.localeCompare(b, 'ru'));
      const custom = query.trim();
      options = matches.map(name => ({name, custom: false}));
      if (custom && !names.some(name => name.toLocaleLowerCase() === custom.toLocaleLowerCase())) options.push({name: custom, custom: true});
      popup.replaceChildren();
      active = -1;
      input.removeAttribute('aria-activedescendant');
      for (const [index, option] of options.entries()) {
        const button = document.createElement('button');
        button.type = 'button';
        button.tabIndex = -1;
        button.className = 'chip-btn receipt-store-option' + (option.custom ? ' chip-btn-create' : '');
        button.id = `${popup.id}-${index}`;
        button.setAttribute('role', 'option');
        const selected = option.name === input.value && !option.custom;
        button.setAttribute('aria-selected', String(selected));
        const name = document.createElement('span');
        name.textContent = option.custom ? `+ ${option.name}` : option.name;
        const check = document.createElement('span');
        check.setAttribute('aria-hidden', 'true');
        check.textContent = selected ? '✓' : '';
        button.append(name, check);
        button.addEventListener('pointerdown', event => { if (event.pointerType === 'mouse') event.preventDefault(); });
        button.addEventListener('click', () => choose(option.name));
        popup.append(button);
      }
      if (!options.length) {
        const empty = document.createElement('span');
        empty.className = 'muted-small';
        empty.textContent = config.emptyLabel || 'Введите название магазина';
        popup.append(empty);
      }
      utils.pinCreateActions(popup, {stack: true});
      utils.setPopoverOpen(popup, true, {owners: [input], outsideScopes: [owner], onClose: close});
      input.setAttribute('aria-expanded', 'true');
    }
    input.addEventListener('focus', () => { render(); ensureSources(); });
    input.addEventListener('click', () => { if (popup.classList.contains('hidden')) render(); });
    input.addEventListener('input', () => { render(input.value); ensureSources(); });
    input.addEventListener('keydown', event => {
      if (event.isComposing) return;
      if (event.key === 'Escape' && !popup.classList.contains('hidden')) {
        event.preventDefault(); event.stopPropagation(); close();
      } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        if (popup.classList.contains('hidden')) render(input.value);
        if (!options.length) return;
        const down = event.key === 'ArrowDown';
        active = active < 0 ? (down ? 0 : options.length - 1) : (active + (down ? 1 : -1) + options.length) % options.length;
        [...popup.querySelectorAll('[role=option]')].forEach((node, index) => node.classList.toggle('is-focused', index === active));
        const selected = popup.querySelectorAll('[role=option]')[active];
        input.setAttribute('aria-activedescendant', selected.id);
        selected.scrollIntoView({block: 'nearest'});
      } else if (event.key === 'Enter') {
        event.preventDefault();
        const option = active >= 0 ? options[active] : options.find(item => !item.custom);
        if (option) choose(option.name);
      } else if (event.key === 'Tab') close();
    });
    input.addEventListener('blur', event => {
      if (!popup.contains(event.relatedTarget)) close();
    });
    // A programmatic modal close must also remove its portalled suggestions.
    // Also close company suggestions when their work view or section is hidden.
    for (let parent = owner; parent; parent = parent.parentElement) {
      const container = parent;
      new MutationObserver(() => { if (container.classList.contains('hidden') || (container.tagName === 'DIALOG' && !container.open)) close(); })
        .observe(container, {attributes: true, attributeFilter: ['class', 'open']});
    }
    return {close, isOpen: () => !popup.classList.contains('hidden'), refresh: () => {if (!popup.classList.contains('hidden')) render(currentQuery);}};
  }
  window.App.registerRuntimeModule('operation-store-picker', {bind});
})();
