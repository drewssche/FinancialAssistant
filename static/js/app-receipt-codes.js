(() => {
  const {core} = window.App;
  let codeHintId=0;
  const thumbnails=new Map();
  const siteQueue=[];let siteActive=0;
  function siteRequest(run){
    return new Promise((resolve,reject)=>{siteQueue.push({run,resolve,reject});drainSites();});
  }
  function drainSites(){
    while(siteActive<2&&siteQueue.length){
      const job=siteQueue.shift();siteActive++;
      Promise.resolve().then(job.run).then(job.resolve,job.reject).finally(()=>{siteActive--;drainSites();});
    }
  }
  function validBarcode(value) {
    if (!/^(?:\d{8}|\d{12,14})$/.test(value) || !Number(value)) return false;
    const digits=[...value].map(Number),check=digits.pop();
    return (10-digits.reverse().reduce((sum,n,i)=>sum+n*(i%2?1:3),0)%10)%10===check;
  }
  function internalRetailerCode(code) {
    const value=code.length===14&&code.startsWith('0')?code.slice(1):code;
    return /^2\d{12}$/.test(value)||(/^2\d{13}$/.test(value)&&!validBarcode(value));
  }
  function entries(row) {
    return row.code_entries ||= (row.catalog_codes || []).map(e=>({...e}));
  }
  function inferKind(code) {
    return !code.trim()?'unknown':internalRetailerCode(code)?'internal':validBarcode(code)||/^(?:\d{8}|\d{12,14})$/.test(code)?'barcode':'retailer';
  }
  function payload(row) {
    return entries(row).filter(e=>e.code.trim()&&!e.from_catalog).map(e=>({kind:internalRetailerCode(e.code.trim())?'internal':e.kind==='unknown'?inferKind(e.code.trim()):e.kind,code:e.code.trim()}));
  }
  function receiptPayload(row) {
    return entries(row).filter(e=>e.code.trim()&&(!e.from_catalog||e.from_receipt)).map(e=>({kind:internalRetailerCode(e.code.trim())?'internal':e.kind==='unknown'?inferKind(e.code.trim()):e.kind,code:e.code.trim()}));
  }
  function savedEntries(seed) {
    const saved=(seed.receipt_codes||[]).map(e=>({...e,kind:internalRetailerCode(e.code)?'internal':e.kind,from_catalog:true,from_receipt:true}));
    for(const code of seed.variant_snapshot?.codes||[]){
      if(!saved.some(e=>e.kind==='barcode'&&e.code===code))saved.push({kind:'barcode',code,from_catalog:true});
    }
    return saved;
  }
  function validationError(codes, shop) {
    const invalid=codes.find(e=>e.kind==='barcode'&&!internalRetailerCode(e.code)&&!validBarcode(e.code));
    const badInternal=codes.find(e=>e.kind==='internal'&&!/^[0-9]{1,32}$/.test(e.code));
    const unknown=codes.find(e=>!['barcode','retailer','internal'].includes(e.kind));
    const retailers=new Set(codes.filter(e=>e.kind==='retailer'&&!internalRetailerCode(e.code)).map(e=>e.code));
    return invalid?`Проверьте длину и контрольную цифру штрихкода ${invalid.code}.`:badInternal?'Внутренний штрихкод должен содержать от 1 до 32 цифр.':codes.some(e=>e.kind==='internal')&&!shop?.trim()?'Выберите магазин для внутреннего штрихкода.':unknown?`Выберите тип кода ${unknown.code}.`:retailers.size>1?'Оставьте один артикул этого магазина.':retailers.size&&!shop?.trim()?'Укажите магазин для артикула.':'';
  }
  function conflict(row, found) {
    const current=window.App.measurements.snapshot(row);
    const sizes={кг:['g',1000],г:['g',1],л:['ml',1000],мл:['ml',1]};
    const named=String(row.name||'').match(/(?:^|[^\p{L}\d])(\d+(?:[.,]\d+)?)\s*(кг|мл|г|л)(?=$|[^\p{L}])/iu);
    if(named&&found.package_quantity){
      const [unit,scale]=sizes[named[2].toLowerCase()];
      const conversions={kg:['g',1000],g:['g',1],l:['ml',1000],ml:['ml',1]};
      const target=conversions[found.package_unit];
      if(target&&(unit!==target[0]||Math.abs(Number(named[1].replace(',','.'))*scale-Number(found.package_quantity)*target[1])>.001))return true;
    }
    return ['sale_unit','package_unit','package_quantity'].some(key=>current[key]!=null && current[key]!=='' && (key==='package_quantity'?Number(current[key])!==Number(found[key]):String(current[key])!==String(found[key]??'')));
  }
  function apply(row,found) {
    if(Number(row.template_id)!==Number(found.template_id)){
      const list=entries(row),kept=list.filter(e=>!e.from_catalog||e.from_receipt).map(e=>e.from_receipt?{...e,from_catalog:false}:e);list.splice(0,list.length,...kept);row.codes_loaded_entity=null;
    }
    row.catalog_name_touched=false;row.catalog_measurement_touched=false;row.catalog_edit_variant_id=null;
    row.site_selection=null;row.site_name='';row.site_preview=null;
    row.code_errors=[];row.variant_id=null;row.variant_snapshot=null;row.variant_options=null;row.variant_status='';row.brand_touched=false;
    for(const key of ['product_id','product_name','name','template_id','source_id','brand_id']) row[key]=found[key]??null;
    if(!row.category_touched) row.category_id=found.category_id||null;
    if(found.variant_id){
      Object.assign(row,window.App.measurements.snapshot(found),{variant_id:found.variant_id,variant_snapshot:found.variant_snapshot,measurement_touched:true});
    }else if(!row.measurement_touched)Object.assign(row,window.App.measurements.snapshot(found));
    row.price_touched=true;
    const brand=window.App.state.itemBrands?.find(b=>Number(b.id)===Number(found.brand_id));
    row.brand_name=brand?.name||'';row.brand_accent_color=brand?.accent_color||null;row.brand_image_id=brand?.image_id||null;
    row.code_match_label=found.matched_by.includes('internal')?'Найден по внутреннему штрихкоду':found.matched_by.includes('barcode')?'Найден по штрихкоду':'Найден по артикулу магазина';
  }
  function mount(host,{row,shop,onSelect,onChange=()=>{},auto=false,loadKnown=false,siteSearch=false,onSiteSelect=()=>{},isActive=()=>true}) {
    const list=entries(row);
    const details=document.createElement('section');details.className='receipt-codes';
    const heading=document.createElement('strong');heading.textContent='Коды товара';details.append(heading);
    const fields=document.createElement('div');fields.className='receipt-code-fields';details.append(fields);
    const actions=document.createElement('div');actions.className='receipt-code-actions';
    const add=document.createElement('button');add.type='button';add.className='btn btn-secondary btn-xs';window.App.icons.apply(add,'plus','Ещё код');
    const search=document.createElement('button');search.type='button';search.className='btn btn-secondary btn-xs';window.App.icons.apply(search,'search','Найти по коду');
    actions.append(add,search);heading.after(actions);
    const hint=document.createElement('p');hint.className='form-error receipt-code-error';hint.id='receiptCodeError'+(++codeHintId);hint.setAttribute('aria-live','polite');details.append(hint);
    const codeRecovery=document.createElement('div');codeRecovery.className='receipt-code-actions';codeRecovery.hidden=true;details.append(codeRecovery);
    function refreshCodes(){
      const reason=validationError(payload(row),shop());
      search.hidden=!list.length;
      const conflicts=(row.code_errors||[]).filter(error=>list.some(entry=>entry.code.trim()===error.code&&entry.kind===error.kind));
      const messages=conflicts.map(error=>`${error.kind==='internal'?'Внутренний штрихкод':error.kind==='barcode'?'Штрихкод':'Артикул'} ${error.code}: ${error.message}${error.product_name?' · '+error.product_name:''}`);
      const invalidBarcodes=list.filter(e=>!e.from_catalog&&e.kind==='barcode'&&e.code.trim()&&!validBarcode(e.code.trim()));
      const explanation=invalidBarcodes.length?'Если цифры совпадают с чеком, выберите тип «Внутренний штрихкод».':'';
      hint.textContent=[reason,explanation,...new Set(messages)].filter(Boolean).join(' · ');hint.hidden=!hint.textContent;
      codeRecovery.replaceChildren();codeRecovery.hidden=!invalidBarcodes.length;
      for(const entry of invalidBarcodes){
        const button=document.createElement('button');button.type='button';button.className='btn btn-secondary btn-xs';
        button.textContent='Использовать как внутренний штрихкод'+(invalidBarcodes.length>1?' · '+entry.code:'');
        button.disabled=!shop()?.trim();button.title=button.disabled?'Сначала укажите магазин':'Сохранить исходные цифры как внутренний штрихкод выбранного магазина';
        button.dataset.receiptCodeAsRetailer=entry.code;
        button.onclick=()=>{entry.kind='internal';entry.manual_kind=true;entry.from_catalog=false;changed();draw();lookup(false);};
        codeRecovery.append(button);
      }
      for(const [index,input] of [...fields.querySelectorAll('input')].entries()){
        input.setAttribute('aria-describedby',hint.id);
        const entry=list[index], invalid=Boolean(reason && (validationError([{kind:entry.kind,code:entry.code}],shop()) || (entry.kind==='retailer'&&reason.startsWith('Оставьте')))) || conflicts.some(error=>error.code===entry.code.trim()&&error.kind===entry.kind);
        input.setAttribute('aria-invalid',String(invalid));input.closest('.receipt-code-line').classList.toggle('is-invalid',invalid);
      }
    }
    const connected=()=>details.isConnected&&isActive();
    host.refreshCodeState=refreshCodes;
    const status=document.createElement('p');status.className='muted-small';status.setAttribute('role','status');details.append(status);
    const results=document.createElement('div');results.className='receipt-code-results';details.append(results);host.replaceChildren(details);
    const siteStatus=document.createElement('p');siteStatus.className='muted-small';siteStatus.setAttribute('role','status');
    const siteResults=document.createElement('div');siteResults.className='receipt-code-results';
    if(siteSearch)details.append(siteStatus,siteResults);
    const siteActions=document.createElement('div');siteActions.className='receipt-preview-actions';
    if(siteSearch)details.append(siteActions);
    function webActions(){
      siteActions.replaceChildren();
      const codes=payload(row),barcode=codes.find(e=>e.kind==='barcode'&&validBarcode(e.code)&&!internalRetailerCode(e.code));
      if(!barcode)return;
      const others=document.createElement('button');others.type='button';others.className='btn btn-secondary btn-xs';others.textContent='Другие магазины';
      others.onclick=()=>lookupSite(true,true);siteActions.append(others);
      const web=document.createElement('a');web.className='btn btn-secondary btn-xs';web.textContent='Поиск в интернете';
      web.href='https://www.google.com/search?q='+encodeURIComponent('"'+barcode.code+'"');web.target='_blank';web.rel='noopener noreferrer';siteActions.append(web);
    }
    function showPreview(items){
      siteResults.replaceChildren();
      for(const found of items){
        const card=document.createElement('article');card.className='receipt-product-preview';
        const photo=document.createElement('div');photo.className='receipt-preview-photo';photo.textContent='Нет фото';
        const body=document.createElement('div');body.className='receipt-preview-body';
        const title=document.createElement('strong');title.textContent=found.name;
        const source=document.createElement('small');source.className='muted-small';
        source.textContent=[found.source,found.reference_only?'Другой магазин · для сверки':'Сайт выбранного источника'].filter(Boolean).join(' · ');
        const match=document.createElement('small');match.textContent=(found.matched_by==='retailer'?'Артикул совпадает':'Штрихкод совпадает')+(found.matched_code?' · '+found.matched_code.replace(/^0(?=\d{13}$)/,''):'');
        const size=document.createElement('small');
        const named=String(found.size_label||found.name||'').match(/(?:^|[^\p{L}\d])(\d+(?:[.,]\d+)?)\s*(кг|мл|г|л)(?=$|[^\p{L}])/iu);
        if(named)size.textContent='Фасовка на сайте: '+named[1]+' '+named[2];
        if(found.brand)size.textContent=[found.brand,size.textContent].filter(Boolean).join(' · ');
        const warning=document.createElement('small');warning.className='receipt-preview-warning';
        warning.textContent=[found.code_warning,sizeMismatch(found)?'Другая фасовка — проверьте товар':''].filter(Boolean).join(' · ');
        const price=document.createElement('div');price.className='receipt-preview-price';
        const quote=found.site_price,current=Number(quote?.price),regular=Number(quote?.regular_price);
        if(Number.isFinite(current)&&current>0){
          const money=value=>value.toLocaleString('ru-RU',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+(quote.currency||'');
          const label=document.createElement('small');label.textContent='Цена на сайте'+(quote.unit?' · за '+quote.unit:'');
          const amount=document.createElement('strong');amount.textContent=money(current);price.append(label,amount);
          if(Number.isFinite(regular)&&regular>current){
            const old=document.createElement('s');old.textContent=money(regular);old.title='Исходная цена';
            const discount=document.createElement('small');discount.textContent='Скидка '+money(regular-current)+' (−'+((regular-current)/regular*100).toLocaleString('ru-RU',{maximumFractionDigits:1})+'%)';
            price.append(old,discount);
          }
          const conditions=document.createElement('small');conditions.className='muted-small';
          const checked=quote.checked_at&&Number.isFinite(Date.parse(quote.checked_at))?'Проверено '+core.formatDateTimeRu(quote.checked_at):'';
          conditions.textContent=[quote.available===false?'Нет в наличии':'',quote.conditions,checked,'Суммы чека не меняются.'].filter(Boolean).join(' · ');price.append(conditions);
        }else{
          const missing=document.createElement('small');missing.className='muted-small';missing.textContent='Не удалось получить цену при последней проверке. Можно обновить данные сайта.';price.append(missing);
        }
        const actions=document.createElement('div');actions.className='receipt-preview-actions';
        const refresh=document.createElement('button');refresh.type='button';refresh.className='btn btn-secondary btn-xs';refresh.textContent='Обновить цену';
        refresh.onclick=()=>lookupSite(Boolean(found.reference_only),true,found.site_selection);actions.append(refresh);
        let safeUrl=null;try{const u=new URL(found.url);if(u.protocol==='https:'&&!u.username&&!u.password)safeUrl=u.href;}catch{}
        if(safeUrl){const link=document.createElement('a');link.href=safeUrl;link.target='_blank';link.rel='noopener noreferrer';link.className='btn btn-secondary btn-xs';link.textContent='Открыть страницу';actions.append(link);}
        if(found.site_selection){
          const select=document.createElement('button');select.type='button';select.className='btn btn-secondary btn-xs';
          select.textContent=row.site_selection===found.site_selection?'Ссылка выбрана':'Выбрать ссылку';select.disabled=row.site_selection===found.site_selection;
          select.onclick=()=>{row.site_selection=found.site_selection;row.site_name=found.name;row.site_preview=items;if(!found.code_warning&&!sizeMismatch(found))onSiteSelect({...found,use_measurement:true});showPreview(items);onChange();};actions.append(select);
        }
        // Public metadata is a proposal: never replace receipt fields automatically.
        const use=document.createElement('button');use.type='button';use.className='btn btn-secondary btn-xs';use.textContent='Использовать название';
        use.onclick=()=>{onSiteSelect({...found,use_name:true});onChange();};actions.append(use);
        body.append(title,source,match);if(size.textContent)body.append(size);if(price.childElementCount)body.append(price);if(warning.textContent)body.append(warning);body.append(actions);card.append(photo,body);siteResults.append(card);
        if(found.image_token){
          const expected=seq;
          const render=data=>{if(!connected()||expected!==seq||!photo.isConnected||!data?.image?.startsWith('data:image/jpeg;base64,'))return;
            const img=document.createElement('img');img.src=data.image;img.alt=found.name;img.width=80;img.height=80;photo.replaceChildren(img);};
          if(thumbnails.has(found.image_token))render(thumbnails.get(found.image_token));
          else siteRequest(()=>core.requestJson('/api/v1/operations/catalog-products/receipt-thumbnail',{method:'POST',headers:{...core.authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({token:found.image_token})}))
            .then(data=>{if(thumbnails.size>=32)thumbnails.delete(thumbnails.keys().next().value);thumbnails.set(found.image_token,data);render(data);}).catch(()=>{});
        }
      }
    }
    const sizeMismatch=found=>{
      const size=text=>String(text||'').match(/(?:^|[^\p{L}\d])(\d+(?:[.,]\d+)?)\s*(кг|мл|г|л)(?=$|[^\p{L}])/iu);
      const named=size(row.name),site=size(found.size_label||found.name);
      const units={kg:['g',1000],кг:['g',1000],g:['g',1],г:['g',1],l:['ml',1000],л:['ml',1000],ml:['ml',1],мл:['ml',1]};
      const current=row.package_quantity&&units[row.package_unit]?[Number(row.package_quantity),row.package_unit]:named?[Number(named[1].replace(',','.')),named[2].toLowerCase()]:null;
      return Boolean(current&&site&&(units[current[1]][0]!==units[site[2].toLowerCase()][0]||Math.abs(current[0]*units[current[1]][1]-Number(site[1].replace(',','.'))*units[site[2].toLowerCase()][1])>.001));
    };
    let timer,seq=0;
    host.invalidateSite=()=>{seq++;onSiteSelect({clear_measurement:true});row.site_selection=null;row.site_name='';row.site_preview=null;siteStatus.textContent='';siteResults.replaceChildren();siteActions.replaceChildren();};
    async function lookupSite(otherSources=false,force=false,refreshSelection=null){
      if(!siteSearch||!connected())return;
      if(!force&&row.site_preview?.length){
        const complete=row.site_preview.every(item=>Number(item.site_price?.price)>0);
        if(complete||Date.now()-(row.site_price_retry_at||0)<300000){showPreview(row.site_preview);webActions();return;}
        row.site_price_retry_at=Date.now();force=true;refreshSelection=row.site_preview.find(item=>item.site_selection)?.site_selection;
      }
      const codes=payload(row);
      if(!codes.length||validationError(codes,shop()))return;
      const token=++seq,before=signature();siteStatus.textContent=otherSources?'Ищу по штрихкоду в других магазинах…':'Ищу на сайте магазина…';siteResults.replaceChildren();siteActions.replaceChildren();
      try{
        const template=row.template_id||row.catalog?.template_id;
        const request={codes,shop_name:shop()||'',...(template?{template_id:Number(template)}:{}),...(otherSources?{other_sources:true}:{}),...(force?{refresh:true,...(refreshSelection?{refresh_selection:refreshSelection}:{})}:{})};
        const data=await siteRequest(()=>{if(token!==seq||!connected()||before!==signature())return null;return core.requestJson('/api/v1/operations/catalog-products/lookup-site-codes',{timeoutMs:60000,method:'POST',headers:{...core.authHeaders(),'Content-Type':'application/json'},body:JSON.stringify(request)});});
        if(!data||token!==seq||!connected()||before!==signature())return;
        const items=data.items||[];
        row.site_preview=items;
        row.site_price_retry_at=Date.now();
        siteStatus.textContent=items.length?(otherSources?'Найдено в других магазинах — для сверки':'Найдено на сайте источника'):data.state==='unavailable'?'Не удалось проверить сайт или прочитать карточку. Повторите поиск или проверьте другие магазины.':data.state==='not_found'?'На сайте точных совпадений по коду не найдено':data.state==='unsupported'?'Поиск на сайте этого источника пока не поддерживается.':data.state==='missing_codes'?'Внутренние коды проверяются только в каталоге выбранного магазина.':'';
        if(data.partial&&items.length)siteStatus.textContent+=' · Поиск выполнен не полностью';
        if(!otherSources&&!data.partial&&items.length===1&&!items[0].reference_only&&!items[0].code_warning&&!sizeMismatch(items[0])){
          if(onSiteSelect({...items[0],use_measurement:true}))onChange();
        }
        showPreview(items);webActions();
      }catch(error){if(token===seq&&connected()&&before===signature()){siteStatus.textContent='Не удалось проверить сайт. Повторите поиск.';webActions();}}
    }
    const signature=()=>JSON.stringify([shop(),list,row.name,row.catalog_new,window.App.measurements.snapshot(row)]);
    function changed(){seq++;onSiteSelect({clear_measurement:true});row.site_selection=null;row.site_name='';row.site_preview=null;siteStatus.textContent='';siteResults.replaceChildren();siteActions.replaceChildren();row.code_errors=[];row.code_match_label='';results.replaceChildren();status.textContent='';refreshCodes();onChange();}
    function draw(){
      fields.replaceChildren();
      list.forEach((entry,index)=>{
        if(internalRetailerCode(entry.code))entry.kind='internal';else if(!entry.manual_kind&&entry.kind==='unknown')entry.kind=inferKind(entry.code);
        const line=document.createElement('div');line.className='receipt-code-line';
        const input=document.createElement('input');input.type='text';input.maxLength=160;input.autocomplete='off';input.value=entry.code;input.placeholder='Штрихкод или артикул';input.setAttribute('aria-label','Код товара');
        const type=document.createElement('select');type.setAttribute('aria-label','Тип кода');
        for(const [value,label] of [['unknown','Определить'],['barcode','Штрихкод'],['internal','Внутренний штрихкод'],['retailer','Артикул']])type.add(new Option(label,value));
        type.value=entry.kind||'unknown';
        const remove=document.createElement('button');remove.type='button';remove.className='btn btn-secondary btn-icon';window.App.icons.apply(remove,'close','Удалить код');
        input.oninput=()=>{entry.code=input.value.trim();entry.from_catalog=false;if(!entry.manual_kind){entry.kind=inferKind(entry.code);type.value=entry.kind;}changed();clearTimeout(timer);timer=setTimeout(()=>lookup(false),300);};
        input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();clearTimeout(timer);lookup(false);}};
        type.onchange=()=>{entry.from_catalog=false;entry.kind=type.value;entry.manual_kind=type.value!=='unknown';changed();draw();lookup(false);};
        remove.onclick=()=>{list.splice(index,1);changed();draw();};
        line.append(input,type,remove);fields.append(line);
      });
      add.disabled=list.length>=10;window.App.icons.apply(add,'plus',list.length?'Ещё код':'Добавить код');refreshCodes();
    }
    async function lookup(allowAuto){
      const codes=list.filter(e=>e.code.trim()).map(e=>({kind:e.manual_kind||e.from_catalog?e.kind:'unknown',code:e.code.trim()}));
      if(!codes.length)return;
      const token=++seq, before=signature();status.textContent='Ищу по кодам…';results.replaceChildren();
      try{
        const data=await core.requestJson('/api/v1/operations/catalog-products/lookup-codes',{method:'POST',headers:{...core.authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({codes,shop_name:shop()||''})});
        if(token!==seq||!connected()||before!==signature())return;
        const items=data.items||[];
        status.textContent=[...(data.warnings||[]),...(data.unmatched?.length?['Не найдены коды: '+data.unmatched.join(', ')]:[]),items.length>1?'Найдены разные варианты — выберите подходящий':items.length?'':'Совпадений по кодам нет. Можно выбрать товар по названию.'].filter(Boolean).join(' · ');
        function choose(found,automatic=false){
          for(const entry of list){if((entry.kind==='unknown'||!entry.manual_kind)&&found.matched_codes.includes(entry.code)&&found.matched_by.length===1)entry.kind=found.matched_by[0];}
          onSelect(found);status.textContent=row.code_match_label||'Товар выбран по коду';results.replaceChildren();draw();if(!automatic&&connected())add.focus({preventScroll:true});
        }
        if(allowAuto&&data.auto_match&&!conflict(row,items[0])){choose(items[0],true);lookupSite();return;}
        if(items.length===1&&Number(row.product_id)===Number(items[0].product_id)&&Number(row.variant_id||0)===Number(items[0].variant_id||0)&&!conflict(row,items[0])){
          status.textContent=[status.textContent,'Код соответствует выбранному товару'].filter(Boolean).join(' · ');lookupSite();return;
        }
        for(const found of items){
          const button=document.createElement('button');button.type='button';button.className='btn btn-secondary receipt-code-result';
          const title=document.createElement('strong');title.textContent=found.product_name;
          const detail=document.createElement('small');detail.textContent=[found.variant_snapshot?.name,window.App.measurements.summary(found),found.matched_by.includes('internal')?'Внутренний штрихкод совпадает':found.matched_by.includes('barcode')?'Штрихкод совпадает':'Артикул совпадает',conflict(row,found)?'Другая фасовка — выбор заменит единицы и размер':''].filter(Boolean).join(' · ');
          button.append(title,detail);button.onclick=()=>{choose(found);lookupSite();};results.append(button);
        }
        if(!items.length)lookupSite();
      }catch(error){if(token===seq&&connected())status.textContent='Не удалось проверить коды. Повторите поиск: '+error.message;}
    }
    add.onclick=()=>{list.push({kind:'unknown',code:''});changed();draw();fields.lastElementChild.querySelector('input').focus();};
    search.onclick=()=>{clearTimeout(timer);row.site_preview=null;lookup(false);};
    host.lookupCodes=()=>lookup(false);
    draw();if(auto&&list.some(e=>e.code))timer=setTimeout(()=>{if(connected())lookup(true);},500);
    else if(siteSearch&&list.some(e=>e.code))timer=setTimeout(()=>{if(connected())lookupSite();},500);
    const entity=String(row.product_id||'')+':'+String(row.template_id||'');
    if(loadKnown&&row.product_id&&row.template_id&&row.codes_loaded_entity!==entity){
      const before=signature();
      core.requestJson(`/api/v1/operations/catalog-products/${row.product_id}/identity`,{headers:core.authHeaders()}).then(data=>{
        if(!connected()||before!==signature())return;
        row.codes_loaded_entity=entity;
        const saved=data.offers?.find(offer=>Number(offer.template_id)===Number(row.template_id));
        for(const code of saved?.internal_codes||[]){if(!list.some(e=>e.code===code))list.push({kind:'internal',code,from_catalog:true});}
        draw();
        if(saved?.retailer_code&&!list.some(e=>e.code===saved.retailer_code)){
          list.push({kind:'retailer',code:saved.retailer_code,from_catalog:true});draw();
        }
      }).catch(()=>{if(connected())status.textContent='Не удалось загрузить сохранённые коды. Можно повторить, открыв детали заново.';});
    }
  }
  async function saveRequest(url, options, mode, items) {
    const stateKey=mode==='edit'?'editReceiptItems':'createReceiptItems';
    const remaining=[...(window.App.state[stateKey]||[])];
    const signatures=(items||[]).map(item=>{
      const index=remaining.findIndex(row=>row.name?.trim()===item.name&&JSON.stringify(payload(row))===JSON.stringify(item.catalog_codes||[]));
      const row=index<0?null:remaining.splice(index,1)[0];
      return {row, name:row?.name, codes:row?JSON.stringify(entries(row)):null, product:row?.product_id, variant:row?.variant_id, shop:row?.shop_name};
    });
    try {return await core.requestJson(url,options);}
    catch(error){
      const detail=error.detail, saved=signatures[detail?.item_index];
      if(detail?.type==='receipt_code_conflict'&&saved?.row){
        const row=saved.row;
        const current=(window.App.state[stateKey]||[]).includes(row)&&row.name===saved.name&&JSON.stringify(entries(row))===saved.codes&&row.product_id===saved.product&&row.variant_id===saved.variant&&row.shop_name===saved.shop;
        if(current){
          row.code_errors=(detail.codes||[]).map(code=>({...code,message:detail.message,...(detail.owners||[]).find(owner=>owner.code===code.code&&owner.kind===code.kind)}));
          window.App.getRuntimeModule('operation-modal').renderReceiptItems(mode);
          const host=document.querySelector(`#${mode}Modal [data-receipt-item-id="${row.draft_id}"] .receipt-codes-host`);
          host?.scrollIntoView({block:'center',behavior:'smooth'});
          host?.querySelector('input[aria-invalid="true"]')?.focus({preventScroll:true});
          host?.lookupCodes?.();
          error.message=`Позиция ${detail.item_index+1} «${detail.item_name}»: ${detail.message}. Проверьте выделенный код.`;
        }
      }
      throw error;
    }
  }
  window.App.receiptCodes={validBarcode,entries,payload,receiptPayload,savedEntries,validationError,mount,apply,conflict,saveRequest};
})();
