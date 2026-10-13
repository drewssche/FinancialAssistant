(() => {
  function bind(owner, mode) {
    const input = owner.querySelector('input');
    const utils = window.App.getRuntimeModule('picker-utils');
    const popup = document.createElement('div');
    popup.id = `${mode}ReceiptStoreOptions`;
    popup.className = 'app-popover app-popover-floating receipt-store-options hidden';
    popup.dataset.popoverAlign = 'start';
    popup.dataset.popoverMaxHeight = '280';
    popup.setAttribute('role', 'listbox');
    popup.setAttribute('aria-label', 'Магазины');
    owner.append(popup);
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', popup.id);
    input.setAttribute('aria-expanded', 'false');
    let active = -1;
    let options = [];
    function close() {
      utils.setPopoverOpen(popup, false, {owners: [input]});
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      active = -1;
    }
    function choose(name) {
      input.value = name;
      input.dispatchEvent(new Event('change', {bubbles: true}));
      input.focus({preventScroll: true});
      close();
    }
    function render(query = '') {
      const names = [...new Set((window.App.state.itemSources || []).map(item => item.name).filter(Boolean))];
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
        button.className = 'chip-btn receipt-store-option';
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
        empty.textContent = 'Введите название магазина';
        popup.append(empty);
      }
      utils.setPopoverOpen(popup, true, {owners: [input], outsideScopes: [owner], onClose: close});
      input.setAttribute('aria-expanded', 'true');
    }
    input.addEventListener('focus', () => render());
    input.addEventListener('click', () => { if (popup.classList.contains('hidden')) render(); });
    input.addEventListener('input', () => render(input.value));
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
        [...popup.children].forEach((node, index) => node.classList.toggle('is-focused', index === active));
        const selected = popup.children[active];
        input.setAttribute('aria-activedescendant', selected.id);
        selected.scrollIntoView({block: 'nearest'});
      } else if (event.key === 'Enter') {
        event.preventDefault();
        choose(active >= 0 ? options[active].name : input.value.trim());
      } else if (event.key === 'Tab') close();
    });
    input.addEventListener('blur', event => {
      if (!popup.contains(event.relatedTarget)) close();
    });
    // A programmatic modal close must also remove its portalled suggestions.
    const modal = owner.closest('.modal');
    new MutationObserver(() => { if (modal.classList.contains('hidden')) close(); })
      .observe(modal, {attributes: true, attributeFilter: ['class']});
  }
  window.App.registerRuntimeModule('operation-store-picker', {bind});
})();
