(() => {
  const {core} = window.App;
  const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
  const api = '/api/v1/catalog-watches';
  let product = null, generation = 0, dashboardSeq = 0;
  const request = (path, method='GET', body) => core.requestJson(api+path,{method,headers:core.authHeaders(),...(body?{body:JSON.stringify(body)}:{})});
  const date = v => v ? core.formatDateTimeRu(v) : 'ещё не проверено';
  function quote(s){
    return `<div class="watch-quote"><strong>${esc(s.name)}</strong><div><b>${esc(s.price)} BYN / ${esc(s.unit)}</b> ${Number(s.regular_price)>Number(s.price)?`<s>${esc(s.regular_price)}</s><span class="watch-down"> −${Math.round((1-Number(s.price)/Number(s.regular_price))*100)}%</span>`:''}</div><small>${esc(s.source||'Е-доставка')}${s.normalized?' · '+esc(s.normalized):''} · ${s.available?'В наличии':'Нет в наличии'}</small><details class="watch-conditions"><summary>Условия цены</summary><small>${esc(s.conditions)}</small></details><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">Открыть на сайте магазина ↗</a></div>`;
  }
  async function guarded(button,action){
    button.disabled=true;
    try{await action();}catch(e){core.showToast(core.errorMessage?.(e)||e.message,{type:'error'});}finally{if(button.isConnected)button.disabled=false;}
  }
  function render(data){
    const host=document.getElementById('catalogProductWatch');
    if(!product)return;
    host.innerHTML=`<label class="watch-toggle" title="Уведомления на дашборде${data.telegram_connected?' и в Telegram':''}; проверка каждые 6 часов"><input type="checkbox" role="switch" ${data.enabled?'checked':''}><span>Следить за ценой</span></label>${data.offers.length?`<span class="muted-small">Источников: ${data.offers.length}</span>`:''}`;
    const toggle=host.querySelector('input'),id=product.id,token=generation;
    toggle.onchange=()=>guarded(toggle,async()=>{try{const result=await request('/'+id,'PUT',{enabled:toggle.checked});if(token===generation)render(result);loadDashboard();}catch(e){toggle.checked=!toggle.checked;throw e;}});
    for(const target of document.querySelectorAll('[data-offer-watch]')){
      const offerId=Number(target.dataset.offerWatch),saved=data.offers.find(o=>o.template_id===offerId);
      if(!saved && !(data.supported_offer_ids||[]).includes(offerId)){
        target.replaceChildren();target.hidden=true;continue;
      }
      const meta=data.supported_offers?.[offerId]||{source:saved?.snapshot?.source||'Е-доставка',search:true,example_url:'https://edostavka.by/product/…'};
      target.hidden=false;
      target.innerHTML=`<div class="watch-source-head"><strong>${esc(meta.source)} · цена на сайте</strong>${saved?'<button type="button" class="btn btn-secondary btn-xs" data-watch-remove>Отключить страницу</button>':meta.saved_url?'<button type="button" class="btn btn-secondary btn-xs" data-watch-saved>Подключить отслеживание</button>':meta.search?'<button type="button" class="btn btn-secondary btn-xs" data-watch-search>Найти по кодам</button>':''}</div>${saved?quote(saved.snapshot)+`<small class="muted-small">Проверено: ${esc(date(saved.checked_at))}${saved.error?' · '+esc(saved.error):''}</small>`:`<details class="watch-alternative" ${!meta.search&&!meta.saved_url?'open':''}><summary>${meta.search?'По названию или ссылке':'Другая ссылка'}</summary>${meta.search?`${meta.saved_url?'<button type="button" class="btn btn-secondary btn-xs" data-watch-search>Найти по кодам</button>':''}<div class="watch-link-row"><label class="field"><span>Название в Е-доставке</span><input type="text" maxlength="160" data-watch-name value="${esc(product.name)}"></label><button type="button" class="btn btn-secondary btn-xs" data-watch-name-search>Найти</button></div>`:''}<div class="watch-link-row"><label class="field"><span>Ссылка на товар</span><input type="url" placeholder="${esc(meta.example_url)}" aria-label="Ссылка на товар: ${esc(meta.source)}" data-watch-url></label><button type="button" class="btn btn-secondary btn-xs" data-watch-preview>Проверить</button></div></details><div data-watch-result aria-live="polite"></div>`}`;
      const remove=target.querySelector('[data-watch-remove]');
      if(remove)remove.onclick=()=>guarded(remove,async()=>{const d=await request(`/${id}/offers/${offerId}`,'DELETE');if(token===generation)render(d);loadDashboard();});
      if(saved)continue;
      const result=target.querySelector('[data-watch-result]');let seq=0;
      const current=n=>token===generation&&target.isConnected&&result.isConnected&&n===seq;
      const previewCard=async url=>{
        const n=++seq;result.textContent='Проверяю карточку…';
        try{
          const snapshot=await request('/'+id+'/preview','POST',{url});
          if(!current(n))return;
          result.innerHTML=quote(snapshot)+'<button type="button" class="btn btn-cta" data-watch-confirm>Подключить этот товар и размер</button>';
          const confirm=result.querySelector('[data-watch-confirm]');
          confirm.onclick=()=>guarded(confirm,async()=>{
            const d=await request(`/${id}/offers/${offerId}`,'PUT',{url:snapshot.url,expected_key:snapshot.comparison_key,expected_name:snapshot.name});
            if(current(n))render(d);loadDashboard();
          });
        }catch(e){if(current(n)){result.textContent='Не удалось проверить карточку. Повторите выбор.';throw e;}}
      };
      const search=async body=>{
        const n=++seq;result.textContent='Ищу в Е-доставке…';
        try{
          const found=await request(`/${id}/offers/${offerId}/search`,'POST',body);
          if(!current(n))return;
          if(!found.items.length){result.textContent=body.name?'По названию ничего не найдено.':'По кодам ничего не найдено. Можно попробовать название.';return;}
          result.innerHTML='<div class="watch-search-results">'+found.items.map((hit,i)=>`<article class="watch-search-card"><strong>${esc(hit.name)}</strong><span>${esc(hit.price)} BYN / ${esc(hit.unit)} · ${hit.available?'В наличии':'Нет в наличии'}</span><small class="muted-small">${hit.match_kind==='barcode'?'Поиск по штрихкоду':hit.match_kind==='retailer'?'Поиск по артикулу':'Поиск по названию'}: ${esc(hit.matched_query)}</small><button type="button" class="btn btn-secondary btn-xs" data-watch-select="${i}">Выбрать</button></article>`).join('')+'</div>';
          for(const button of result.querySelectorAll('[data-watch-select]'))button.onclick=()=>guarded(button,()=>previewCard(found.items[Number(button.dataset.watchSelect)].url));
        }catch(e){if(current(n)){result.textContent='Не удалось выполнить поиск. Повторите позже.';throw e;}}
      };
      const searchButton=target.querySelector('[data-watch-search]');
      if(searchButton)searchButton.onclick=()=>guarded(searchButton,async()=>{
        const codesHost=document.querySelector(`[data-offer-codes="${offerId}"]`);
        const barcode=codesHost?.querySelector('[data-code=barcode]'),sku=codesHost?.querySelector('[data-code=sku]');
        if(!barcode||!sku||(barcode.disabled&&sku.disabled)){result.textContent='Дождитесь загрузки кодов и выберите размер источника.';return;}
        const codes=[...new Set((barcode.disabled?'':barcode.value).split(/[\s,;]+/).filter(Boolean))].slice(0,2).map(code=>({kind:'barcode',code}));
        if(!sku.disabled&&sku.value.trim())codes.push({kind:'retailer',code:sku.value.trim()});
        if(!codes.length){result.textContent='Добавьте штрихкод или артикул в этом источнике.';barcode.focus();return;}
        if(codes.some(c=>c.kind==='barcode'&&!window.App.receiptCodes.validBarcode(c.code))){result.textContent='Проверьте штрихкод перед поиском.';return;}
        await search({codes});
      });
      const nameButton=target.querySelector('[data-watch-name-search]'),nameInput=target.querySelector('[data-watch-name]');
      if(nameButton)nameButton.onclick=()=>guarded(nameButton,()=>search({name:nameInput.value.trim()}));
      if(nameInput)nameInput.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();nameButton.click();}};
      const savedButton=target.querySelector('[data-watch-saved]');
      if(savedButton)savedButton.onclick=()=>guarded(savedButton,()=>previewCard(meta.saved_url));
      const preview=target.querySelector('[data-watch-preview]');
      preview.onclick=()=>guarded(preview,()=>previewCard(target.querySelector('[data-watch-url]').value));
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
      host.innerHTML=`<div class="panel-head row between"><h3>Цены на мои товары</h3><span class="muted-small">Отслеживается: ${data.tracked_count}</span></div>`;
      if(!data.tracked_count){host.insertAdjacentHTML('beforeend','<p class="muted-small">Нет отслеживаемых товаров</p>');return;}
      for(const direction of ['down','up']){
        const events=data.events.filter(e=>e.direction===direction);
        if(!events.length)continue;
        host.insertAdjacentHTML('beforeend',`<h4>${direction==='down'?'Цена снизилась':'Цена выросла'}</h4><div class="watch-grid">${events.slice(0,6).map(e=>`<article class="watch-card"><button type="button" class="catalog-product-name-btn" data-watch-open="${e.product_id}">${esc(e.product_name)}</button><strong class="watch-${direction}">${esc(e.old_price)} → ${esc(e.price)} BYN / ${esc(e.unit)} <small>(${esc(e.percent)}%)</small></strong><small>${esc(e.source||'Е-доставка')} · ${esc(date(e.created_at))}</small></article>`).join('')}</div>`);
      }
      host.insertAdjacentHTML('beforeend',`<details ${!data.events.length?'open':''}><summary>Подключённые предложения (${data.offers.length})</summary><div class="watch-grid">${data.offers.map(o=>`<article class="watch-card"><button type="button" class="catalog-product-name-btn" data-watch-open="${o.product_id}">${esc(o.product_name)}</button>${quote(o.snapshot)}<small class="muted-small">${esc(date(o.checked_at))}${o.error?' · '+esc(o.error):''}</small></article>`).join('')}</div></details>${data.unlinked.map(p=>`<p class="muted-small"><button type="button" class="btn btn-secondary btn-xs" data-watch-open="${p.product_id}">${esc(p.name)}</button> · подключите страницу магазина</p>`).join('')}`);
      for(const b of host.querySelectorAll('[data-watch-open]'))b.onclick=()=>core.runAction({errorPrefix:'Не удалось открыть товар',action:()=>window.App.getRuntimeModule('catalog-products').openEditor(Number(b.dataset.watchOpen),{tab:'offers'})});
    }catch(e){if(token===dashboardSeq&&authToken===window.App.state.token){host.innerHTML='<h3>Цены на мои товары</h3><span class="muted-small">Не удалось загрузить предложения.</span> <button type="button" class="btn btn-secondary">Повторить</button>';host.querySelector('button').onclick=loadDashboard;}}
  }
  window.App.registerRuntimeModule('catalog-watch',{open,close(){generation++;product=null;},loadDashboard});
})();
