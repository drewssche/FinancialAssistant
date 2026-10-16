(() => {
  const {core} = window.App;
  const esc = (s) => core.escapeHtml(String(s ?? ""));
  const units = {pack: "уп.", piece: "шт.", kg: "кг", g: "г", l: "л", ml: "мл"};
  const number = (v) => Number(v).toLocaleString("ru-RU", {maximumFractionDigits: 4});
  const pct = (v) => v == null ? "нет базы для %" : `${Number(v) > 0 ? "+" : ""}${number(v)}%`;
  const pack = (r) => r.package_quantity && r.package_unit ? `${number(r.package_quantity)} ${units[r.package_unit] || r.package_unit}` : "";
  let payload = null, selected = 0, count = 50;
  function graph(rows, label) {
    const values = rows.map((r) => Number(r.price)), low = values.reduce((a,b) => Math.min(a,b), Infinity), high = values.reduce((a,b) => Math.max(a,b), -Infinity);
    const x = (i) => 40 + (rows.length > 1 ? i / (rows.length - 1) : 0.5) * 620;
    const y = (v) => 135 - (high === low ? 0.5 : (v - low) / (high - low)) * 95;
    // Horizontal handles stay inside each pair's price range: no invented peaks.
    const path = rows.map((r, i) => {
      const px=x(i), py=y(Number(r.price));
      if (!i) return `M${px} ${py}`;
      const mid=(x(i-1)+px)/2;
      return `C${mid} ${y(Number(rows[i-1].price))} ${mid} ${py} ${px} ${py}`;
    }).join(" ");
    return `<svg class="product-price-chart" viewBox="0 0 700 170" role="group" tabindex="0" aria-label="${esc(label)}. Стрелки — выбор покупки, Escape — скрыть подсказку"><defs><linearGradient id="productPriceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="currentColor" stop-opacity=".18"/><stop offset="100%" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><text x="8" y="16">${esc(number(high))}</text><path d="${path} L${x(rows.length-1)} 140 L${x(0)} 140 Z" fill="url(#productPriceFill)" aria-hidden="true"/><path class="product-price-line" d="${path}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>${rows.map((r,i) => `<circle data-price-index="${i}" cx="${x(i)}" cy="${y(Number(r.price))}" r="3" fill="currentColor"></circle>`).join("")}<text x="40" y="160">${esc(core.formatDateRu(rows[0].recorded_at))}</text><text x="660" y="160" text-anchor="end">${esc(core.formatDateRu(rows.at(-1).recorded_at))}</text></svg>`;
  }
  function render() {
    const target = document.getElementById("catalogProductPricesList");
    const series = payload?.series || [];
    if (!series.length) { target.innerHTML = `<p class="empty">Нет покупок с данными для выбранного расчёта.</p>${excluded()}`; return; }
    selected = Math.min(selected, series.length - 1);
    const group = series[selected], rows = group.observations;
    const label = (s) => `${s.currency} · ${s.shop_name || "Магазин не указан"} · за ${units[s.unit] || "ед. (не указана)"}${pack(s) ? ` · ${pack(s)}` : ""}`;
    const title = `${payload.price_kind === "paid" ? "Оплаченная" : "Обычная"} цена: ${label(group)}`;
    target.innerHTML = `<label class="field"><span>Сопоставимые покупки</span><select id="catalogProductPriceSeries">${series.map((s,i) => `<option value="${i}" ${i === selected ? "selected" : ""}>${esc(label(s))}</option>`).join("")}</select></label>
      <p class="product-price-summary"><strong>${esc(pct(group.change_percent))}</strong> от первой до последней покупки · повышений: ${group.increases} · снижений: ${group.decreases}</p>
      <div class="product-price-chart-host">${graph(rows, title)}<div class="analytics-chart-tooltip hidden" role="status"></div></div>
      <div class="product-price-events">${[...rows].reverse().slice(0, count).map((r) => `<button type="button" class="catalog-product-purchase-row" data-product-purchase-id="${Number(r.operation_id)}"><span><strong>${esc(core.formatDateRu(r.recorded_at))}</strong><small>${esc(pack(r) || units[r.sale_unit] || "Единица не указана")}${r.is_discounted ? " · со скидкой" : ""}${r.package_changed ? " · другая фасовка/единица" : ""}</small></span><span><strong>${esc(number(r.price))} ${esc(group.currency)}/${esc(units[group.unit] || "ед.")}</strong><small>${r.direction > 0 ? "↑ " : r.direction < 0 ? "↓ " : ""}${r.change_percent == null ? "—" : esc(pct(r.change_percent))}</small></span></button>`).join("")}</div>
      ${rows.length > count ? '<button type="button" class="btn btn-secondary" data-price-history-more>Показать ещё</button>' : ""}${excluded()}`;
    bindChart(target, rows, group);
    target.querySelector("#catalogProductPriceSeries").addEventListener("change", (event) => {selected = Number(event.target.value); count = 50; render(); document.getElementById("catalogProductPriceSeries").focus();});
    window.App.icons.apply(target.querySelector("[data-price-history-more]"), "down", "Показать ещё цены");
    target.querySelector("[data-price-history-more]")?.addEventListener("click", () => {count += 50; render(); target.querySelector("[data-price-history-more]")?.focus();});
  }
  function bindChart(target, rows, group) {
    const host=target.querySelector('.product-price-chart-host'), chart=host.querySelector('svg'), tooltip=host.querySelector('.analytics-chart-tooltip');
    const points=[...chart.querySelectorAll('[data-price-index]')];
    const guide=document.createElementNS('http://www.w3.org/2000/svg','line');
    guide.setAttribute('y1','24');guide.setAttribute('y2','140');guide.setAttribute('stroke','currentColor');guide.setAttribute('stroke-dasharray','3 3');guide.setAttribute('opacity','.45');guide.style.display='none';chart.append(guide);
    let active=-1;
    function hide(){tooltip.classList.add('hidden');guide.style.display='none';points.forEach(p=>p.setAttribute('r','3'));active=-1;}
    function show(index, clientX, clientY){
      if(!rows.length)return;
      const row=rows[index], point=points[index];
      if(active!==index){
        active=index;points.forEach((p,i)=>p.setAttribute('r',i===index?'5':'3'));
        guide.setAttribute('x1',point.getAttribute('cx'));guide.setAttribute('x2',point.getAttribute('cx'));guide.style.display='';
        tooltip.innerHTML=`<div class="analytics-chart-tooltip-title">${esc(core.formatDateRu(row.recorded_at))}</div><div class="analytics-chart-tooltip-grid analytics-chart-tooltip-grid-compact"><strong>${esc(number(row.price))} ${esc(group.currency)}/${esc(units[group.unit]||'ед.')}</strong><span>${row.change_percent==null?'Первая покупка':esc(pct(row.change_percent))+' к предыдущей покупке'}</span><span class="muted-small">${esc([group.shop_name,pack(row),row.is_discounted?'Со скидкой':''].filter(Boolean).join(' · '))}</span></div>`;
      }
      tooltip.classList.remove('hidden');
      const rect=host.getBoundingClientRect(), tip=tooltip.getBoundingClientRect();
      tooltip.style.left=`${Math.max(8,Math.min(rect.width-tip.width-8,clientX-rect.left+12))}px`;
      tooltip.style.top=`${Math.max(8,Math.min(rect.height-tip.height-8,clientY-rect.top-tip.height-10))}px`;
    }
    function move(event){
      const matrix=chart.getScreenCTM();if(!matrix)return;
      const location=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
      const index=Math.max(0,Math.min(rows.length-1,Math.round((location.x-40)/620*(rows.length-1))));
      show(index,event.clientX,event.clientY);
    }
    function keyboard(index){const point=points[index];if(!point)return;const box=point.getBoundingClientRect();show(index,box.x+box.width/2,box.y);}
    chart.addEventListener('pointermove',move);
    chart.addEventListener('pointerdown',move);
    chart.addEventListener('pointerleave',event=>{if(event.pointerType!=='touch')hide();});
    chart.addEventListener('pointercancel',hide);
    chart.addEventListener('focus',()=>{if(chart.matches(':focus-visible'))keyboard(0);});
    chart.addEventListener('blur',hide);
    chart.addEventListener('keydown',event=>{
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();hide();return;}
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
      event.preventDefault();
      keyboard(event.key==='Home'?0:event.key==='End'?rows.length-1:Math.max(0,Math.min(rows.length-1,(active<0?0:active)+(event.key==='ArrowRight'?1:-1))));
    });
  }
  function excluded() { return payload?.excluded_count ? `<p class="muted-small">Не показано позиций: ${Number(payload.excluded_count)} — нет нужных единиц, обычной цены или положительного количества.</p>` : ""; }
  window.App.registerRuntimeModule("catalog-price-history", {
    render(value, preserve = false, preferred = null) {
      const key = (s) => s ? JSON.stringify([s.currency, s.shop_name, s.unit, s.package_quantity == null ? null : Number(s.package_quantity), s.package_unit]) : "";
      const previous = key(payload?.series?.[selected]);
      payload = value;
      selected = preserve || preferred ? Math.max(0, (payload?.series || []).findIndex((s) => key(s) === (preserve ? previous : key(preferred)))) : 0;
      if (!preserve) count = 50;
      render();
    },
    cleanup() {payload = null; selected = 0; count = 50;},
  });
})();
