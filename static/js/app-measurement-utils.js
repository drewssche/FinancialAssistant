(() => {
  const fields = ["sale_unit", "package_quantity", "package_unit"];
  const units = { piece: "шт.", pack: "упак.", kg: "кг", g: "г", l: "л", ml: "мл" };
  function snapshot(value = {}) {
    return Object.fromEntries(fields.map((key) => [key, value[key] === "" || value[key] == null ? null : value[key]]));
  }
  function options(selected, content = false) {
    return '<option value="">Не указана</option>' + Object.entries(units)
      .filter(([key]) => !content || key !== "pack")
      .map(([key, label]) => `<option value="${key}" ${key === selected ? "selected" : ""}>${label}</option>`).join("");
  }
  function summary(value) {
    const sale = units[value.sale_unit] || "Размер не указан";
    return value.package_quantity && units[value.package_unit]
      ? `${value.package_quantity} ${units[value.package_unit]} в упаковке` : sale;
  }
  // One visible editor, backed by the existing three persisted fields.
  // Mounting is read-only: legacy units and frozen receipt snapshots are preserved.
  function mount(container, controls) {
    if (!container || controls.some(control => !control)) return;
    container.querySelector('.measurement-editor')?.remove();
    controls.forEach(control => { control.closest('label').hidden = true; });
    const [sale, quantity, unit] = controls;
    const editor = document.createElement('div'); editor.className = 'measurement-editor';
    let weighted = ['kg','g','l','ml'].includes(sale.value);
    const current = () => Object.fromEntries(fields.map((key,i) => [key, controls[i].value]));
    function write(values) {
      for (const [key,value] of Object.entries(values)) {
        const control = controls[fields.indexOf(key)];
        if (control.value === value) continue;
        control.value = value;
        control.dispatchEvent(new Event('input', {bubbles:true}));
        control.dispatchEvent(new Event('change', {bubbles:true}));
      }
    }
    function render() {
      editor.innerHTML = `<div class="measurement-kind segmented" role="group" aria-label="Как продаётся товар"><button type="button" class="segmented-btn ${!weighted?'active':''}" aria-pressed="${!weighted}" data-measure-kind="pack">Упаковка / штука</button><button type="button" class="segmented-btn ${weighted?'active':''}" aria-pressed="${weighted}" data-measure-kind="weight">На вес / розлив</button></div><div class="measurement-size"><label class="field"><span>${weighted?'Цена и количество в чеке — за':'Размер одной упаковки'}</span>${weighted?'': '<input type="number" min="0.001" step="0.001" placeholder="Например, 1" aria-label="Размер одной упаковки">'}</label><div class="measurement-units" role="group" aria-label="Единица размера"></div></div><small class="muted-small measurement-example"></small>`;
      const input = editor.querySelector('input');
      if (input) {
        input.value = quantity.value;
        input.addEventListener('input', () => {write({sale_unit: ['piece','pack'].includes(sale.value)?sale.value:'piece', package_quantity:input.value, package_unit:unit.value}); sync();});
      }
      const unitsNode = editor.querySelector('.measurement-units');
      for (const key of (weighted ? ['kg','g','l','ml'] : ['g','kg','ml','l','piece'])) {
        const button = document.createElement('button'); button.type='button'; button.className='btn btn-secondary measurement-unit';
        button.textContent = units[key]; button.dataset.unit=key;
        button.addEventListener('click', () => {write(weighted?{sale_unit:key,package_quantity:'',package_unit:''}:{sale_unit:['piece','pack'].includes(sale.value)?sale.value:'piece',package_unit:key}); sync();});
        unitsNode.append(button);
      }
      editor.querySelectorAll('[data-measure-kind]').forEach(button => button.addEventListener('click', () => {
        const next = button.dataset.measureKind==='weight'; if (next===weighted) return;
        weighted=next;
        write(weighted?{sale_unit:'kg',package_quantity:'',package_unit:''}:{sale_unit:'piece',package_quantity:'',package_unit:''}); render();
      }));
      const clear = document.createElement('button'); clear.type='button'; clear.className='btn btn-secondary btn-icon';
      clear.title='Не указывать размер'; clear.setAttribute('aria-label',clear.title); clear.innerHTML=window.App.icons.svg('close');
      clear.addEventListener('click', () => {write({sale_unit:'',package_quantity:'',package_unit:''}); weighted=false; render();});
      editor.querySelector('.measurement-size').append(clear);
      sync();
    }
    function sync() {
      const input=editor.querySelector('input');
      if(input) {input.required=Boolean(unit.value); input.setCustomValidity(quantity.value && !unit.value ? 'Выберите единицу размера: г, кг, мл, л или шт.' : '');}
      editor.querySelectorAll('[data-unit]').forEach(button => {
        const active=button.dataset.unit===(weighted?sale.value:unit.value);
        button.classList.toggle('is-active',active); button.setAttribute('aria-pressed',String(active));
      });
      editor.querySelector('.measurement-example').textContent = weighted
        ? `Количество в чеке указывайте в ${units[sale.value] || 'кг'}`
        : quantity.value && unit.value ? `${summary(current())} · количество в чеке — число упаковок` : 'Необязательно · например, 1 л молока или 90 г пюре';
    }
    container.append(editor); render();
  }
  window.App = window.App || {};
  window.App.measurements = { fields, units, snapshot, options, summary, mount };
})();
