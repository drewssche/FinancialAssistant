(() => {
  const {core} = window.App;
  const esc = v => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
  const api = '/api/v1/catalog-watches';
  let product = null, generation = 0, dashboardSeq = 0, matchingTimer = null, dashboardView = null, dashboardOwner = null;
  const matchLabels = {pending:"Подбираем страницу по коду…", choice:"Выберите подходящую карточку", not_found:"По кодам пока не найдено", missing_codes:"Добавьте штрихкод или артикул", error:"Не удалось проверить сайт · повторим позже", paused:"Автоподключение отключено", linked:"Страница подключена"};
  const request = (path, method='GET', body) => core.requestJson(api+path,{method,headers:core.authHeaders(),...(body?{body:JSON.stringify(body)}:{})});
  const date = v => v ? core.formatDateTimeRu(v) : 'ещё не проверено';
  const priceText = s => s.price == null ? 'Цена не указана' : `${s.price} BYN / ${s.unit}`;
  function quote(s, compact=false){
    const source=s.source||'Е-доставка';
    const info=s.conditions?`<button type="button" class="btn btn-secondary btn-icon" title="Условия цены" aria-label="Условия цены" data-help-title="Условия цены" data-help-text="${esc(s.conditions)}">${window.App.icons.svg("info")}</button>`:'';
    const external=`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-icon" aria-label="Открыть на сайте магазина" title="Открыть на сайте магазина">${window.App.icons.svg("external")}</a>`;
    return `<div class="watch-quote"><div class="watch-quote-head"><strong>${esc(compact?source:s.name)}</strong><div class="watch-quote-actions">${info}${external}</div></div><div class="watch-quote-price"><b>${esc(priceText(s))}</b> ${Number(s.regular_price)>Number(s.price)?`<s>${esc(s.regular_price)}</s><span class="watch-down"> −${Math.round((1-Number(s.price)/Number(s.regular_price))*100)}%</span>`:''}</div><small>${[compact?'':source,s.normalized,s.available?'В наличии':'Нет в наличии'].filter(Boolean).map(esc).join(' · ')}</small></div>`;
  }
  function decorateActions(host) {
    const actions = {'watch-remove':['unlink','Отключить страницу'], 'watch-saved':['link','Подключить цену сайта'], 'watch-search':['search','Найти по кодам'], 'watch-name-search':['search','Найти по названию'], 'watch-preview':['eye','Проверить ссылку'], 'watch-confirm':['save','Подключить этот товар и размер'], 'watch-select':['link','Выбрать товар'], 'match-select':['link','Выбрать товар'], 'match-retry':['refresh','Повторить подбор']};
    for (const [key,[icon,label]] of Object.entries(actions)) {
      for (const button of host.querySelectorAll(`[data-${key}]`)) window.App.icons.apply(button,icon,label);
    }
  }
  async function guarded(button,action){
    button.disabled=true;
    try{await action();}catch(e){core.showToast(core.errorMessage?.(e)||e.message,{type:'error'});}finally{if(button.isConnected)button.disabled=false;}
  }
  function render(data){
    const host=document.getElementById('catalogProductWatch');
    if(!product)return;
    host.innerHTML=`<label class="watch-toggle" title="История на дашборде${data.telegram_connected?' и дайджест в Telegram':''}. Цены обновляются независимо от уведомлений"><input type="checkbox" role="switch" ${data.enabled?'checked':''}><span>Уведомлять об изменении цены</span></label>${data.offers.length?`<span class="muted-small">Источников: ${data.offers.length}</span>`:''}`;
    const toggle=host.querySelector('input'),id=product.id,token=generation;
    toggle.onchange=()=>guarded(toggle,async()=>{try{const result=await request('/'+id,'PUT',{enabled:toggle.checked});if(token===generation)render(result);loadDashboard();}catch(e){toggle.checked=!toggle.checked;throw e;}});
    for(const target of document.querySelectorAll('[data-offer-watch]')){
      const offerId=Number(target.dataset.offerWatch),saved=data.offers.find(o=>o.template_id===offerId);
      if(!saved && !(data.supported_offer_ids||[]).includes(offerId)){
        target.replaceChildren();target.hidden=true;continue;
      }
      const meta=data.supported_offers?.[offerId]||{source:saved?.snapshot?.source||'Е-доставка',search:true,example_url:'https://edostavka.by/product/…'};
      target.hidden=false;
      target.innerHTML=`<div class="watch-source-head"><strong>${esc(meta.source)} · цена на сайте</strong>${saved?'<button type="button" class="btn btn-secondary btn-xs" data-watch-remove>Отключить страницу</button>':meta.saved_url?'<button type="button" class="btn btn-secondary btn-xs" data-watch-saved>Подключить цену сайта</button>':''}</div>${saved?quote(saved.snapshot)+`<small class="muted-small">Проверено: ${esc(date(saved.checked_at))}${saved.error?' · '+esc(saved.error):''}</small>`:`<div class="watch-connect-modes segmented" role="group" aria-label="Способ подключения: ${esc(meta.source)}">${meta.search?'<button type="button" class="segmented-btn active" aria-pressed="true" data-watch-method="code">По коду</button><button type="button" class="segmented-btn" aria-pressed="false" data-watch-method="name">По названию</button>':''}<button type="button" class="segmented-btn ${!meta.search?'active':''}" aria-pressed="${!meta.search}" data-watch-method="url">По ссылке</button></div>${meta.search?`<div class="watch-connect-panel" data-watch-method-panel="code"><button type="button" class="btn btn-secondary btn-xs" data-watch-search>Найти по кодам</button></div><div class="watch-link-row watch-connect-panel" data-watch-method-panel="name" hidden><label class="field"><span>Название: ${esc(meta.source)}</span><input type="text" maxlength="160" data-watch-name value="${esc(product.name)}"></label><button type="button" class="btn btn-secondary btn-xs" data-watch-name-search>Найти</button></div>`:''}<div class="watch-link-row watch-connect-panel" data-watch-method-panel="url" ${meta.search?'hidden':''}><label class="field"><span>Ссылка на товар</span><input type="url" placeholder="${esc(meta.example_url)}" aria-label="Ссылка на товар: ${esc(meta.source)}" data-watch-url></label><button type="button" class="btn btn-secondary btn-xs" data-watch-preview>Проверить</button></div><div data-watch-result aria-live="polite"></div>`}`;
      for(const button of target.querySelectorAll('[data-watch-method]'))button.onclick=()=>{
        for(const option of target.querySelectorAll('[data-watch-method]')){
          const active=option===button;option.classList.toggle('active',active);option.setAttribute('aria-pressed',String(active));
        }
        for(const panel of target.querySelectorAll('[data-watch-method-panel]'))panel.hidden=panel.dataset.watchMethodPanel!==button.dataset.watchMethod;
      };
      decorateActions(target);
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
          decorateActions(result);
          const confirm=result.querySelector('[data-watch-confirm]');
          confirm.onclick=()=>guarded(confirm,async()=>{
            const d=await request(`/${id}/offers/${offerId}`,'PUT',{url:snapshot.url,expected_key:snapshot.comparison_key,expected_name:snapshot.name});
            if(current(n))render(d);loadDashboard();
          });
        }catch(e){if(current(n)){result.textContent='Не удалось проверить карточку. Повторите выбор.';throw e;}}
      };
      const search=async body=>{
        const n=++seq;result.textContent=`Ищу: ${meta.source}…`;
        try{
          const found=await request(`/${id}/offers/${offerId}/search`,'POST',body);
          if(!current(n))return;
          if(!found.items.length){result.textContent=body.name?'По названию ничего не найдено.':'По кодам ничего не найдено. Можно попробовать название.';return;}
          result.innerHTML='<div class="watch-search-results">'+found.items.map((hit,i)=>`<article class="watch-search-card"><strong>${esc(hit.name)}</strong><span>${esc(priceText(hit))} · ${hit.available?'В наличии':'Нет в наличии'}</span><small class="muted-small">${hit.match_kind==='barcode'?'Поиск по штрихкоду':hit.match_kind==='retailer'?'Поиск по артикулу':'Поиск по названию'}: ${esc(hit.matched_query)}</small><button type="button" class="btn btn-secondary btn-xs" data-watch-select="${i}">Выбрать</button></article>`).join('')+'</div>';
          decorateActions(result);
          for(const button of result.querySelectorAll('[data-watch-select]'))button.onclick=()=>guarded(button,()=>previewCard(found.items[Number(button.dataset.watchSelect)].url));
        }catch(e){if(current(n)){result.textContent='Не удалось выполнить поиск. Повторите позже.';throw e;}}
      };
      const matching=meta.matching;
      if(matching){
        result.innerHTML=`<div class="row between"><span class="muted-small">${esc(matchLabels[matching.state]||'')}</span>${['error','not_found','paused'].includes(matching.state)?'<button type="button" class="btn btn-secondary btn-xs" data-match-retry>Повторить подбор</button>':''}</div>`;
        if(matching.candidates?.length){
          result.insertAdjacentHTML('beforeend','<div class="watch-search-results">'+matching.candidates.map((hit,i)=>`<article class="watch-search-card"><strong>${esc(hit.name)}</strong><span>${esc(priceText(hit))}</span><small>${hit.conflict?'Коды расходятся':hit.exact?'Код подтверждён':'Совпадение кода не подтверждено'}</small><button type="button" class="btn btn-secondary btn-xs" data-match-select="${i}">Выбрать</button></article>`).join('')+'</div>');
          for(const button of result.querySelectorAll('[data-match-select]'))button.onclick=()=>guarded(button,()=>previewCard(matching.candidates[Number(button.dataset.matchSelect)].url));
        }
        decorateActions(result);
        const retry=result.querySelector('[data-match-retry]');
        if(retry)retry.onclick=()=>guarded(retry,async()=>{const d=await request(`/${id}/offers/${offerId}/autolink`,'POST');if(token===generation)render(d);});
      }
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
    clearTimeout(matchingTimer);
    if(Object.entries(data.supported_offers||{}).some(([tid,meta])=>meta.matching?.state==='pending'&&!data.offers.some(o=>String(o.template_id)===tid))){
      matchingTimer=setTimeout(()=>{if(token===generation&&!document.querySelector('[data-watch-confirm]')&&!document.activeElement?.closest('.catalog-offer-watch'))open(product);},15000);
    }
  }
  async function open(p){
    product=p;const token=++generation,host=document.getElementById('catalogProductWatch');
    host.classList.toggle('hidden',!p);host.innerHTML=p?'<span class="muted-small">Загружаю цены…</span>':'';
    if(!p)return;
    try{const data=await request('/'+p.id);if(token===generation)render(data);}
    catch(e){if(token===generation){host.innerHTML='<span class="form-error">Не удалось загрузить цены</span> <button class="btn btn-secondary" type="button">Повторить</button>';window.App.icons.apply(host.querySelector('button'),'refresh','Повторить');host.querySelector('button').onclick=()=>open(p);}}
  }
  async function loadDashboard(){
    const host=document.getElementById('dashboardProductWatches');if(!host)return;
    const token=++dashboardSeq,authToken=window.App.state.token;
    try{
      const data=await request('');if(token!==dashboardSeq||authToken!==window.App.state.token)return;
      if(dashboardOwner!==authToken){dashboardOwner=authToken;dashboardView=null;}
      const products=new Map();
      for(const offer of data.offers){
        if(!products.has(offer.product_id))products.set(offer.product_id,{id:offer.product_id,name:offer.product_name,offers:[],unlinked:[]});
        products.get(offer.product_id).offers.push(offer);
      }
      for(const item of data.unlinked){
        if(!products.has(item.product_id))products.set(item.product_id,{id:item.product_id,name:item.name,offers:[],unlinked:[]});
        products.get(item.product_id).unlinked.push(item);
      }
      dashboardView ||= !data.events.length&&products.size?'products':'changes';
      host.innerHTML=`<div class="panel-head row between"><h3>Уведомления о ценах</h3><span class="muted-small">Включено товаров: ${data.tracked_count}</span></div><div class="segmented watch-view-tabs" role="tablist" aria-label="Уведомления о ценах"><button type="button" class="segmented-btn" role="tab" id="watchChangesTab" aria-controls="watchChangesPanel" data-watch-view="changes">Изменения</button><button type="button" class="segmented-btn" role="tab" id="watchProductsTab" aria-controls="watchProductsPanel" data-watch-view="products">Товары · ${data.tracked_count}</button></div><section id="watchChangesPanel" role="tabpanel" aria-labelledby="watchChangesTab"><div class="watch-grid" data-watch-events tabindex="0" aria-label="История уведомлений о ценах"></div><div data-watch-more></div></section><section id="watchProductsPanel" role="tabpanel" aria-labelledby="watchProductsTab"><div class="watch-grid" data-watch-products></div></section>`;
      const selectView=(view,focus=false)=>{
        dashboardView=view;
        for(const tab of host.querySelectorAll('[data-watch-view]')){
          const active=tab.dataset.watchView===view;tab.classList.toggle('active',active);tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;
          host.querySelector('#'+tab.getAttribute('aria-controls')).hidden=!active;
          if(active&&focus)tab.focus();
        }
      };
      for(const tab of host.querySelectorAll('[data-watch-view]')){
        tab.onclick=()=>selectView(tab.dataset.watchView);
        tab.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();selectView(e.key==='Home'?'changes':e.key==='End'?'products':dashboardView==='changes'?'products':'changes',true);};
      }
      selectView(dashboardView);
      const eventHost=host.querySelector('[data-watch-events]'),more=host.querySelector('[data-watch-more]');
      const bindOpen=()=>{for(const b of host.querySelectorAll('[data-watch-open]'))b.onclick=()=>core.runAction({errorPrefix:'Не удалось открыть товар',action:()=>window.App.getRuntimeModule('catalog-products').openEditor(Number(b.dataset.watchOpen),{tab:'offers'})});};
      const appendEvents=page=>{
        eventHost.insertAdjacentHTML('beforeend',page.events.map(e=>`<article class="watch-card"><button type="button" class="catalog-product-name-btn" data-watch-open="${e.product_id}" title="${esc(e.product_name)}">${esc(e.product_name)}</button><strong class="watch-${e.direction==='down'?'down':'up'}">${e.direction==='down'?'↓':'↑'} ${esc(e.old_price)} → ${esc(e.price)} BYN / ${esc(e.unit)} <small>(${esc(e.percent)}%)</small></strong><small>${esc(e.source||'Е-доставка')} · ${esc(date(e.created_at))}</small></article>`).join(''));
        more.innerHTML=page.next_cursor?'<button type="button" class="btn btn-secondary btn-xs">Ещё изменения</button>':'';
        const next=more.querySelector('button');
        if(next)window.App.icons.apply(next,'down','Ещё изменения');
        if(next)next.onclick=()=>guarded(next,async()=>{const older=await request('?before_id='+page.next_cursor);if(token===dashboardSeq&&authToken===window.App.state.token)appendEvents(older);});
        bindOpen();
      };
      appendEvents(data);
      if(!data.events.length)eventHost.innerHTML='<p class="muted-small">Изменений цен пока нет</p>';
      host.querySelector('[data-watch-products]').innerHTML=[...products.values()].map(p=>`<article class="watch-card watch-product-card"><button type="button" class="catalog-product-name-btn" data-watch-open="${p.id}" title="${esc(p.name)}">${esc(p.name)}</button>${p.offers.map(o=>`<div class="watch-product-source">${quote(o.snapshot,true)}<small class="muted-small">${esc(date(o.checked_at))}${o.error?' · '+esc(o.error):''}</small></div>`).join('')}${p.unlinked.map(item=>`<div class="watch-match-state"><strong>${esc(item.matching_sources?.join(', ')||'Источник')}</strong><span>${esc(matchLabels[item.matching_state]||'Подбираем страницу по коду…')}</span></div>`).join('')}</article>`).join('')||'<p class="muted-small">Уведомления о товарах пока не включены</p>';
      bindOpen();
    }catch(e){if(token===dashboardSeq&&authToken===window.App.state.token){host.innerHTML='<h3>Уведомления о ценах</h3><span class="muted-small">Не удалось загрузить предложения.</span> <button type="button" class="btn btn-secondary">Повторить</button>';window.App.icons.apply(host.querySelector('button'),'refresh','Повторить');host.querySelector('button').onclick=loadDashboard;}}
  }
  window.App.registerRuntimeModule('catalog-watch',{open,close(){generation++;product=null;clearTimeout(matchingTimer);},loadDashboard});
})();
