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
  function priceLabel(value, discounted = false) {
    const unit = units[value.sale_unit] || 'ед.';
    return `Цена за ${unit}${discounted ? ' · со скидкой' : ''}`;
  }
  function quantityLabel(value) {
    const unit = units[value.sale_unit];
    const label = ['kg','g'].includes(value.sale_unit) ? 'Вес' : ['l','ml'].includes(value.sale_unit) ? 'Объём' : 'Кол-во';
    return unit ? `${label}, ${unit}` : label;
  }
  function renderUnitButtons(host, {choices, dataset = 'unit', onSelect}) {
    for (const [key,label] of choices) {
      const button=document.createElement('button');button.type='button';button.className='btn btn-secondary measurement-unit';
      button.textContent=label;button.dataset[dataset]=key;button.addEventListener('click',()=>onSelect(key));host.append(button);
    }
  }
  // One visible editor, backed by the existing three persisted fields.
  // Mounting is read-only: legacy units and frozen receipt snapshots are preserved.
  function mount(container, controls, {unitDataset = 'saleUnit'} = {}) {
    if (!container || controls.some(control => !control)) return;
    container.querySelector('.measurement-editor')?.remove();
    controls.forEach(control => { control.closest('label').hidden = true; });
    const [sale, quantity, unit] = controls;
    const editor = document.createElement('div'); editor.className = 'measurement-editor';
    function write(values) {
      const changed=[];
      for (const [key,value] of Object.entries(values)) {
        const control = controls[fields.indexOf(key)];
        if (control.value === value) continue;
        control.value = value; changed.push(control);
      }
      for (const control of changed) {
        control.dispatchEvent(new Event('input', {bubbles:true}));
        control.dispatchEvent(new Event('change', {bubbles:true}));
      }
    }
    editor.innerHTML = `<div class="measurement-sale"><span class="muted-small">Единица цены</span><div class="measurement-units" role="group" aria-label="Единица цены"></div></div><div class="measurement-size"><label class="field"><span>Размер одной упаковки</span><input type="number" min="0.001" step="0.001" placeholder="Например, 250" aria-label="Размер одной упаковки"></label><div class="measurement-units" role="group" aria-label="Единица размера"></div></div>`;
    const input=editor.querySelector('input'), size=editor.querySelector('.measurement-size');
    const saleButtons=editor.querySelector('.measurement-sale .measurement-units');
    renderUnitButtons(saleButtons,{choices:[['','Не указана'],...Object.entries(units)],dataset:unitDataset,onSelect:key=>{
      const packed=['piece','pack'].includes(key);
      write(packed?{sale_unit:key}:{sale_unit:key,package_quantity:'',package_unit:''}); sync();
    }});
    input.addEventListener('input',()=>{write({package_quantity:input.value});sync();});
    renderUnitButtons(size.querySelector('.measurement-units'),{choices:['g','kg','ml','l','piece'].map(key=>[key,units[key]]),onSelect:key=>{write({package_unit:key});sync();}});
    const clear=document.createElement('button');clear.type='button';clear.className='btn btn-secondary btn-icon';
    window.App.icons.apply(clear,'close','Не указывать размер');
    clear.addEventListener('click',()=>{write({package_quantity:'',package_unit:''});sync();});size.append(clear);
    function sync() {
      const packed=['piece','pack'].includes(sale.value);
      size.hidden=!packed;
      input.disabled=!packed;
      input.value=quantity.value;
      input.required=packed&&Boolean(unit.value);
      input.setCustomValidity(packed&&quantity.value&&!unit.value?'Выберите единицу размера: г, кг, мл, л или шт.':'');
      saleButtons.querySelectorAll('button').forEach(button=>{
        const active=button.dataset[unitDataset]===sale.value;
        button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));
      });
      size.querySelectorAll('[data-unit]').forEach(button=>{
        const active=button.dataset.unit===unit.value;
        button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));
      });
    }
    container.append(editor);sync();
    return {refresh:sync};
  }
  window.App = window.App || {};
  window.App.measurements = { fields, units, snapshot, options, summary, priceLabel, quantityLabel, renderUnitButtons, mount };
})();
