(() => {
  const {core} = window.App;
  const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
  const api = '/api/v1/catalog-watches';
  let product = null, generation = 0, dashboardSeq = 0;
  const request = (path, method='GET', body) => core.requestJson(api+path,{method,headers:core.authHeaders(),...(body?{body:JSON.stringify(body)}:{})});
  const date = v => v ? core.formatDateTimeRu(v) : 'ещё не проверено';
  function quote(s){
    return `<div class="watch-quote"><strong>${esc(s.name)}</strong><div><b>${esc(s.price)} BYN / ${esc(s.unit)}</b> ${Number(s.regular_price)>Number(s.price)?`<s>${esc(s.regular_price)}</s><span class="watch-down"> −${Math.round((1-Number(s.price)/Number(s.regular_price))*100)}%</span>`:''}</div><small>${esc(s.normalized)} · ${s.available?'В наличии':'Нет в наличии'}</small><small>${esc(s.conditions)}</small><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">Открыть в Е-доставке ↗</a></div>`;
  }
  async function guarded(button,action){
    button.disabled=true;
    try{await action();}catch(e){core.showToast(core.errorMessage?.(e)||e.message,{type:'error'});}finally{if(button.isConnected)button.disabled=false;}
  }
  function render(data){
    const host=document.getElementById('catalogProductWatch');
    if(!product)return;
    host.innerHTML=`<label class="watch-toggle"><input type="checkbox" role="switch" ${data.enabled?'checked':''}><span>Следить за ценой</span></label><p class="muted-small">Изменения появятся на дашборде${data.telegram_connected?' и в Telegram':' · Для Telegram привяжите аккаунт в профиле'}. Проверка раз в 6 часов.</p><p class="muted-small">${data.offers.length?'Подключено предложений: '+data.offers.length:'Подключите страницу магазина во вкладке «Предложения».'}</p>`;
    const toggle=host.querySelector('input'),id=product.id,token=generation;
    toggle.onchange=()=>guarded(toggle,async()=>{try{const result=await request('/'+id,'PUT',{enabled:toggle.checked});if(token===generation)render(result);loadDashboard();}catch(e){toggle.checked=!toggle.checked;throw e;}});
    for(const target of document.querySelectorAll('[data-offer-watch]')){
      const offerId=Number(target.dataset.offerWatch),saved=data.offers.find(o=>o.template_id===offerId);
      if(!saved && !(data.supported_offer_ids||[]).includes(offerId)){
        target.innerHTML='<small class="muted-small">Автопроверка этого источника пока не подключена. Для цен Е-доставки добавьте её как источник товара.</small>';continue;
      }
      target.innerHTML=`<div class="watch-source-head"><strong>Цена на сайте · Е-доставка</strong>${saved?'<button type="button" class="btn btn-secondary btn-xs" data-watch-remove>Отключить страницу</button>':''}</div>${saved?quote(saved.snapshot)+`<small class="muted-small">Проверено: ${esc(date(saved.checked_at))}${saved.error?' · '+esc(saved.error):''}</small>`:`<div class="watch-link-row"><label class="field"><span>Ссылка на этот товар в Е-доставке</span><input type="url" placeholder="https://edostavka.by/product/…" aria-label="Ссылка на товар в Е-доставке"></label><button type="button" class="btn btn-secondary" data-watch-preview>Проверить</button></div><small class="muted-small">Сверьте название и размер. Цена сайта может отличаться от цены в магазине.</small><div data-watch-result aria-live="polite"></div>`}`;
      const remove=target.querySelector('[data-watch-remove]');
      if(remove)remove.onclick=()=>guarded(remove,async()=>{const d=await request(`/${id}/offers/${offerId}`,'DELETE');if(token===generation)render(d);loadDashboard();});
      const preview=target.querySelector('[data-watch-preview]');
      if(preview)preview.onclick=()=>guarded(preview,async()=>{
        const input=target.querySelector('input'),url=input.value;
        const result=target.querySelector('[data-watch-result]');result.textContent='Проверяю карточку…';
        let s;
        try{s=await request('/'+id+'/preview','POST',{url});}catch(e){result.textContent='Не удалось проверить страницу. Проверьте ссылку и повторите.';throw e;}
        if(token!==generation||!target.isConnected)return;
        result.innerHTML=quote(s)+'<button type="button" class="btn btn-cta" data-watch-confirm>Это мой товар и размер · подключить</button>';
        const confirm=result.querySelector('button');
        confirm.onclick=()=>guarded(confirm,async()=>{
          const d=await request(`/${id}/offers/${offerId}`,'PUT',{url:s.url,expected_key:s.comparison_key,expected_name:s.name});
          if(token===generation)render(d);loadDashboard();
        });
      });
    }
  }
  async function open(p){
    product=p;const token=++generation,host=document.getElementById('catalogProductWatch');
    host.classList.toggle('hidden',!p);host.innerHTML=p?'<span class="muted-small">Загружаю отслеживание…</span>':'';
    if(!p)return;
    try{const data=await request('/'+p.id);if(token===generation)render(data);}
    catch(e){if(token===generation){host.innerHTML='<span class="form-error">Не удалось загрузить отслеживание</span> <button class="btn btn-secondary" type="button">Повторить</button>';host.querySelector('button').onclick=()=>open(p);}}
  }
  async function loadDashboard(){
    const host=document.getElementById('dashboardProductWatches');if(!host)return;
    const token=++dashboardSeq,authToken=window.App.state.token;
    try{
      const data=await request('');if(token!==dashboardSeq||authToken!==window.App.state.token)return;
      host.innerHTML=`<div class="panel-head row between"><h3>Цены на мои товары</h3><span class="muted-small">Отслеживается: ${data.tracked_count}</span></div><p class="muted-small">Е-доставка · цены сайта, проверка раз в 6 часов</p>`;
      if(!data.tracked_count){host.insertAdjacentHTML('beforeend','<p class="muted-small">Включите «Следить за ценой» в карточке нужного товара и подключите предложение магазина.</p>');return;}
      for(const direction of ['down','up']){
        const events=data.events.filter(e=>e.direction===direction);
        if(!events.length)continue;
        host.insertAdjacentHTML('beforeend',`<h4>${direction==='down'?'Цена снизилась':'Цена выросла'}</h4><div class="watch-grid">${events.slice(0,6).map(e=>`<article class="watch-card"><button type="button" class="catalog-product-name-btn" data-watch-open="${e.product_id}">${esc(e.product_name)}</button><strong class="watch-${direction}">${esc(e.old_price)} → ${esc(e.price)} BYN / ${esc(e.unit)} <small>(${esc(e.percent)}%)</small></strong><small>Е-доставка · ${esc(date(e.created_at))}</small></article>`).join('')}</div>`);
      }
      host.insertAdjacentHTML('beforeend',`<details ${!data.events.length?'open':''}><summary>Подключённые предложения (${data.offers.length})</summary><div class="watch-grid">${data.offers.map(o=>`<article class="watch-card"><button type="button" class="catalog-product-name-btn" data-watch-open="${o.product_id}">${esc(o.product_name)}</button>${quote(o.snapshot)}<small class="muted-small">${esc(date(o.checked_at))}${o.error?' · '+esc(o.error):''}</small></article>`).join('')}</div></details>${data.unlinked.map(p=>`<p class="muted-small"><button type="button" class="btn btn-secondary btn-xs" data-watch-open="${p.product_id}">${esc(p.name)}</button> · подключите страницу магазина</p>`).join('')}`);
      for(const b of host.querySelectorAll('[data-watch-open]'))b.onclick=()=>core.runAction({errorPrefix:'Не удалось открыть товар',action:()=>window.App.getRuntimeModule('catalog-products').openEditor(Number(b.dataset.watchOpen),{tab:'offers'})});
    }catch(e){if(token===dashboardSeq&&authToken===window.App.state.token){host.innerHTML='<h3>Цены на мои товары</h3><span class="muted-small">Не удалось загрузить предложения.</span> <button type="button" class="btn btn-secondary">Повторить</button>';host.querySelector('button').onclick=loadDashboard;}}
  }
  window.App.registerRuntimeModule('catalog-watch',{open,close(){generation++;product=null;},loadDashboard});
})();
