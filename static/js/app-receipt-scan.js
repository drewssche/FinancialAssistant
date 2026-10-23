(() => {
  const {icons, state, core} = window.App;
  const parser = window.App.receiptScanParser;
  const categoryChoice = row => window.App.receiptCategories.resolve(row, state.categories || [], state.receiptProductHints || []);
  function inputNumber(value, quantity = false) {
    const result = core.evaluateMathExpression(String(value).replace(/−/g, '-').replace(/×/g, '*').replace(/÷/g, '/'), quantity ? 3 : 2);
    return result.ok && result.value >= 0 && result.value <= (quantity ? 100000 : 9999999.99) ? result.value : null;
  }
  const inputMoney = value => {const result = inputNumber(value);return result == null ? null : Math.round(result * 100);};
  const node = id => document.getElementById(id);
  const dialog = document.createElement('dialog');
  dialog.id='receiptScanDialog';dialog.className='receipt-scan-dialog';dialog.setAttribute('aria-labelledby','receiptScanTitle');
  const iconButton=(id,icon,label)=>`<button id="${id}" type="button" class="btn btn-secondary btn-icon" aria-label="${label}" title="${label}">${icons.svg(icon)}</button>`;
  dialog.innerHTML=`<header><h3 id="receiptScanTitle">Сканировать чек</h3>${iconButton('scanClose','close','Закрыть сканирование')}</header>
    <p class="muted-small" id="scanPrivacy">Фото обрабатывается на устройстве.</p>
    <button type="button" id="scanDropzone" class="scan-dropzone">${icons.svg('upload')}<strong>Выберите или перетащите фото чека</strong><span>Или вставьте из буфера: <kbd>Ctrl+V</kbd> / <kbd>⌘V</kbd></span><small>JPG, PNG, WebP · до 20 МБ</small></button>
    <div class="scan-toolbar" id="scanPhotoTools">${iconButton('scanBack','back','Изменить фото и распознать заново')}${iconButton('scanUpload','upload','Загрузить фото чека')}${iconButton('scanRotate','refresh','Повернуть фото')}${iconButton('scanReset','expand','Сбросить углы')}<input id="scanFile" type="file" accept="image/jpeg,image/png,image/webp" hidden><span id="scanStep" class="muted-small">Загрузите фото или вставьте Ctrl+V / ⌘V · до 20 МБ</span></div>
    <div id="scanPasteReplace" class="scan-toolbar" hidden><span>Заменить фото и сбросить текущий черновик?</span>${iconButton("scanPasteAccept","save","Заменить фото")}${iconButton("scanPasteDismiss","close","Оставить текущий чек")}</div><div id="scanWorkspace" hidden><div class="scan-image-column"><div id="scanImageFrame"><canvas id="scanCanvas"></canvas><div id="scanNoPhoto" hidden>Фото чека не сохранено или удалено</div><svg id="scanOutline" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polygon fill="#79acff18" stroke="#79acff" stroke-width=".5"/></svg>${[0,1,2,3].map((i)=>`<button type="button" class="scan-corner" data-corner="${i}" aria-label="Угол ${i+1} чека">${i+1}</button>`).join('')}</div><p id="scanCropHint" class="muted-small">Подвиньте углы к краям чека</p></div>
    <form id="scanReview" hidden><div class="scan-meta"><label class="field"><span>Дата покупки</span><input id="scanDate" type="date" required></label><label class="field"><span>Магазин</span><input id="scanShop" maxlength="160" placeholder="Выбрать или ввести магазин" autocomplete="off" required></label><label class="field"><span>Итого по чеку</span><input id="scanTotal" inputmode="decimal" aria-describedby="scanMathHint" required></label><label class="field"><span>Валюта</span><select id="scanCurrency"><option>BYN</option><option>RUB</option><option>USD</option><option>EUR</option></select></label></div>
    <div class="scan-review-toolbar"><strong>Позиции</strong>${iconButton('scanAddRow','plus','Добавить строку')}${iconButton('scanShowText','receipt','Распознанный текст')}</div><p class="sr-only" id="scanMathHint">Можно вводить вычисления: 7,11 − 0,71 · Enter — получить результат.</p><div id="scanRows"></div>
    <p id="scanArithmetic" role="status"></p><div id="scanReplaceOperation" class="scan-toolbar" hidden><span>Заменить заполненные поля операции данными этого чека?</span>${iconButton('scanReplaceYes','save','Заменить данные операции')}${iconButton('scanReplaceNo','close','Оставить операцию')}</div><label class="scan-confirm"><input id="scanConfirmed" type="checkbox">Проверил дату, магазин, валюту и позиции</label>
    <footer><button type="submit" class="btn btn-primary btn-icon" id="scanTransfer" aria-label="В черновик операции" title="В черновик операции" disabled>${icons.svg("save")}</button></footer></form></div>
    <p id="scanStatus" class="muted-small" role="status"></p><footer id="scanRunBar"><button id="scanCancel" type="button" class="btn btn-secondary btn-icon" aria-label="Отменить распознавание" title="Отменить распознавание" hidden>${icons.svg("close")}</button><button id="scanRun" type="button" class="btn btn-primary btn-icon" aria-label="Распознать чек" title="Распознать чек" disabled>${icons.svg("receipt")}</button></footer>
    <dialog id="scanTextDialog" class="choice-dialog task-dialog"><header><h3>Распознанный текст</h3>${iconButton('scanTextClose','close','Закрыть текст')}</header><div class="segmented" id="scanTextModes"><button type="button" class="segmented-btn active" data-text-mode="edited">Уточнённый</button><button type="button" class="segmented-btn" data-text-mode="original">Исходный</button></div><textarea id="scanText" rows="15" maxlength="80000" aria-label="Распознанный текст"></textarea><button id="scanReparse" class="btn btn-primary btn-icon" type="button" aria-label="Разобрать исправленный текст" title="Разобрать исправленный текст">${icons.svg("refresh")}</button></dialog>`;
  document.body.append(dialog);
  const storePicker=window.App.getRuntimeModule('operation-store-picker').bind(node('scanShop').closest('.field'),'scan');
  let source=null, points=[], draft=null, job=null, generation=0, transferred=false, originalText='', busy=false, pendingPaste=null;
  let originalTextMode=false, editedText='', storedImage=null;
  const reviewText=()=>originalTextMode?editedText:node('scanText').value;
  let context='create', createRecovery=null, applied=false, openGeneration=0;
  const pending={create:null,edit:null};
  function snapshot(){
    if(!draft&&!source)return null;
    readMeta();
    return {draft, source, points, originalText, text:reviewText(), currency:node('scanCurrency').value,
      image:canvas.width>1?(storedImage||canvas.toDataURL('image/webp',.9).split(',')[1]):null, applied};
  }
  async function restore(saved){
    storedImage=saved.image||null;source=saved.source||null;points=saved.points||[[0,0],[1,0],[1,1],[0,1]];
    draft=saved.draft||saved.review;originalText=saved.originalText||saved.original_text||'';
    node('scanText').value=saved.text||originalText;node('scanCurrency').value=saved.currency||draft?.currency||'BYN';
    applied=Boolean(saved.applied);transferred=false;
    if(saved.image){
      const blob=new Blob([Uint8Array.from(atob(saved.image),c=>c.charCodeAt(0))],{type:'image/webp'});
      const bitmap=await createImageBitmap(blob);
      canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
      if(!source){source=document.createElement('canvas');source.width=canvas.width;source.height=canvas.height;source.getContext('2d').drawImage(canvas,0,0);}
    }
    node('scanNoPhoto').hidden=Boolean(saved.image);canvas.hidden=!saved.image;
    node('scanBack').hidden=!saved.image;node('scanWorkspace').hidden=false;
    if(draft?.rows){renderDraft();}else{draft=null;draw();}
    setBusy(false);
  }
  function renderDraft(){
    dialog.dataset.stage='review';node('scanReview').hidden=false;
    node('scanDate').value=draft.date||'';node('scanShop').value=draft.shop||'';node('scanTotal').value=decimal(draft.total);
    node('scanConfirmed').checked=false;renderRows();validate();
  }
  function operationReview(mode, previous, keepSavedCodes=false){
    const prefix=mode==='create'?'op':'edit', rows=state[mode+'ReceiptItems']?.filter(r=>r.name);
    if(!rows?.length)return previous;
    return {date:node(prefix+'Date').value,shop:rows[0].shop_name||'',total:inputMoney(node(prefix+'Amount').value),currency:node(prefix+'Currency').value,rows:rows.map((r,index)=>{
      const money=window.App.receiptPricing.calculate(r), price=Number(r.regular_unit_price||r.unit_price);
      const old=previous?.rows?.[index];
      const codes=keepSavedCodes&&!r.code_entries?.length&&old?.name===r.name?old.code_entries:r.code_entries;
      return {...r,code_errors:[],code_entries:codes||[],catalog:r.product_id||r.template_id?{...r}:null,category_touched:true,price:Math.round(price*100),
        quantity:Number(r.quantity),discount:Math.max(0,Math.round(((money.subtotal??money.total)-money.total)*100)),total:Math.round(money.total*100)};
    })};
  }
  function syncOperation(keepSavedCodes=false){
    const mode=context==='create'?'create':'edit';
    draft=operationReview(mode,draft,keepSavedCodes);
    if(!draft)return;
    node('scanCurrency').value=draft.currency||'BYN';renderDraft();applied=false;
  }
  function savedReview(value){
    const review=structuredClone(value);
    for(const row of review?.rows||[]){
      delete row.merged_rows;delete row.source;delete row.code_match_result;delete row.site_selection;
      if(row.catalog)delete row.catalog.site_selection;
    }
    return review;
  }
  function scanPayload(){
    readMeta();
    // Catalog lookup state and OCR source lines aren't needed in the saved review.
    const review=savedReview({...draft,currency:node('scanCurrency').value});
    return {image:canvas.width>1&&!canvas.hidden?(storedImage||canvas.toDataURL('image/webp',.9).split(',')[1]):null,
      original_text:originalText,text:reviewText(),review};
  }
  const catalog=()=>window.App.getRuntimeModule('operation-modal').receiptCatalog;
  const catalogNotice=()=>catalog().status().loading?'Ищу в каталоге…':catalog().status().incomplete?'Каталог загружен не полностью':'';
  const canvas=node('scanCanvas');
  function resetPoints(){points=[[0,0],[1,0],[1,1],[0,1]];draw();}
  function fitCrop(){
    if(!source)return;
    const imageHeight=Math.max(120,Math.min(innerHeight*.62,innerHeight-300));
    dialog.style.setProperty('--scan-crop-width',`${Math.max(420,Math.min(900,source.width/source.height*imageHeight+80))}px`);
  }
  window.addEventListener('resize',()=>{if(dialog.open)fitCrop();});
  function draw(){
    if(!source)return;
    dialog.dataset.stage='crop';fitCrop();
    canvas.width=source.width;canvas.height=source.height;canvas.getContext('2d').drawImage(source,0,0);
    dialog.querySelectorAll('[data-corner]').forEach((b,i)=>{b.style.left=`${points[i][0]*100}%`;b.style.top=`${points[i][1]*100}%`;});
    node('scanOutline').querySelector('polygon').setAttribute('points',points.map(([x,y])=>`${x*100},${y*100}`).join(' '));
  }
  function status(text){node('scanStatus').textContent=text;}
  function setBusy(value){
    busy=value;
    for(const id of ['scanRun','scanUpload','scanRotate','scanReset'])node(id).disabled=value || (id!=='scanUpload'&&!source);
    node('scanCancel').hidden=!value;
    dialog.querySelectorAll('[data-corner]').forEach(b=>b.disabled=value);
  }
  function invalidateReview(){storedImage=null;dialog.dataset.stage=source?'crop':'upload';node('scanStep').textContent='Границы чека';draft=null;node('scanReview').hidden=true;node('scanConfirmed').checked=false;transferred=false;}
  function cancel(){generation++;job?.cancel();job=null;setBusy(false);status('Распознавание отменено');}
  function cleanup(){storePicker.close();originalTextMode=false;editedText='';node('scanText').readOnly=false;node('scanReparse').hidden=false;node('scanTextModes').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.textMode==='edited'));dialog.classList.remove('scan-drag-over');pendingPaste=null;node('scanPasteReplace').hidden=true;cancel();node('scanTextDialog').close();source=null;canvas.width=canvas.height=1;canvas.hidden=false;node('scanNoPhoto').hidden=true;node('scanBack').hidden=false;node('scanFile').value='';node('scanText').value='';node('scanRows').replaceChildren();originalText='';invalidateReview();node('scanWorkspace').hidden=true;setBusy(false);status('');}
  async function open(mode='create'){
    if(mode==='edit'&&state.editDebtMovement)return;
    const next=mode==='create'?'create':String(state.editOperationId), token=++openGeneration;
    try{
      if(next!==context){
        if(context==='create')createRecovery=snapshot();
        cleanup();context=next;
        if(next==='create'&&createRecovery)await restore(createRecovery);
        else if(next!=='create'){
          const saved=await core.requestJson(`/api/v1/operations/${next}/receipt-scan`,{headers:core.authHeaders()});
          if(token!==openGeneration)return;
          await restore(saved);syncOperation(true);
        }
      }
      if(token!==openGeneration||node(mode==='create'?'createModal':'editModal').classList.contains('hidden'))return;
      if(applied)syncOperation();
      transferred=false;if(draft)validate();
      if(!dialog.open)dialog.showModal();
      (draft?node('scanDate'):node('scanDropzone')).focus();
      Promise.all([catalog().load(),window.App.getRuntimeModule('item-brands').ensureItemBrandsLoaded()]).then(()=>{if(draft)refreshCatalog();storePicker.refresh();}).catch(()=>{});
    }catch(error){if(token!==openGeneration)return;if(mode==='edit')context='';core.notify(error.message||'Не удалось открыть чек',{type:'error'});}
  }
  node('scanClose').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>{storePicker.close();if(busy)cancel();node('scanTextDialog').close();closeCatalogLists();refreshEntry();});
  dialog.addEventListener('click',e=>{const r=dialog.getBoundingClientRect();if(e.target===dialog&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dialog.close();});
  // Installed before the global choice listener: Escape in a nested choice belongs to it.
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||!dialog.open||node('appChoiceDialog')?.open)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(storePicker.isOpen()&&!node('scanTextDialog').open){storePicker.close();return;}
    const list=dialog.querySelector('.scan-catalog-list:not([hidden])');
    if(list&&!node('scanTextDialog').open){closeCatalogLists();return;}
    if(node('scanTextDialog').open)node('scanTextDialog').close();else dialog.close();
  },true);
  node('scanUpload').onclick=node('scanDropzone').onclick=()=>node('scanFile').click();
  async function loadImage(file){
    if(!file)return;
    pendingPaste=null;node('scanPasteReplace').hidden=true;
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>20*1024*1024){status('Выберите JPG, PNG или WebP размером до 20 МБ');node('scanFile').value='';return;}
    cancel();invalidateReview();canvas.hidden=false;node('scanNoPhoto').hidden=true;node('scanBack').hidden=false;const token=++generation;setBusy(true);status('Открываю фото…');
    let bitmap;
    try{
      bitmap=await createImageBitmap(file);
      if(token!==generation)return;
      if(bitmap.width*bitmap.height>24000000)throw new Error('Слишком большое фото — уменьшите его до 24 мегапикселей');
      source=document.createElement('canvas');const scale=Math.min(1,2800/Math.max(bitmap.width,bitmap.height));
      source.width=Math.round(bitmap.width*scale);source.height=Math.round(bitmap.height*scale);source.getContext('2d').drawImage(bitmap,0,0,source.width,source.height);
      node('scanWorkspace').hidden=false;resetPoints();status('');
    }catch(e){if(token===generation)status(e.message||'Не удалось прочитать фото');}
    finally{bitmap?.close();if(token===generation){setBusy(false);node('scanFile').value='';}}
  };
  function offerImage(file){
    if(!file)return;
    if(draft||busy){pendingPaste=file;node('scanPasteReplace').hidden=false;node('scanPasteAccept').focus();}
    else loadImage(file);
  }
  node('scanFile').onchange=()=>offerImage(node('scanFile').files[0]);
  for(const eventName of ['dragenter','dragover'])dialog.addEventListener(eventName,e=>{
    if(!Array.from(e.dataTransfer?.types||[]).includes('Files'))return;
    e.preventDefault();e.dataTransfer.dropEffect='copy';dialog.classList.add('scan-drag-over');
  });
  dialog.addEventListener('dragleave',e=>{if(!dialog.contains(e.relatedTarget))dialog.classList.remove('scan-drag-over');});
  dialog.addEventListener('drop',e=>{
    if(!e.dataTransfer?.files.length)return;
    e.preventDefault();dialog.classList.remove('scan-drag-over');
    if(e.dataTransfer.files.length!==1){status('Добавьте одно фото чека');return;}
    offerImage(e.dataTransfer.files[0]);
  });
  dialog.addEventListener('paste',e=>{
    if(node('scanTextDialog').open)return;
    const file=Array.from(e.clipboardData?.items||[]).find(i=>i.kind==='file'&&i.type.startsWith('image/'))?.getAsFile() || Array.from(e.clipboardData?.files||[]).find(f=>f.type.startsWith('image/'));
    if(!file)return; // Leave normal text paste in every input untouched.
    e.preventDefault();
    offerImage(file);
  });
  node('scanPasteAccept').onclick=()=>{const file=pendingPaste;pendingPaste=null;node('scanPasteReplace').hidden=true;loadImage(file);};
  node('scanPasteDismiss').onclick=()=>{pendingPaste=null;node('scanPasteReplace').hidden=true;};
  node('scanBack').onclick=()=>{invalidateReview();draw();status('');};
  node('scanRotate').onclick=()=>{
    if(!source||busy)return;const rotated=document.createElement('canvas');rotated.width=source.height;rotated.height=source.width;
    const ctx=rotated.getContext('2d');ctx.translate(rotated.width,0);ctx.rotate(Math.PI/2);ctx.drawImage(source,0,0);source=rotated;invalidateReview();resetPoints();
  };
  node('scanReset').onclick=()=>{invalidateReview();resetPoints();};
  dialog.querySelectorAll('[data-corner]').forEach(button=>{
    const index=Number(button.dataset.corner);let dragging=false;
    button.onpointerdown=e=>{if(busy)return;dragging=true;button.setPointerCapture(e.pointerId);e.preventDefault();};
    button.onpointermove=e=>{if(!dragging)return;const r=canvas.getBoundingClientRect();points[index]=[Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];invalidateReview();draw();};
    button.onpointerup=button.onpointercancel=()=>{dragging=false;};
    button.onkeydown=e=>{if(!e.key.startsWith('Arrow'))return;e.preventDefault();const axis=['ArrowLeft','ArrowRight'].includes(e.key)?0:1;const delta=['ArrowLeft','ArrowUp'].includes(e.key)?-.005:.005;points[index][axis]=Math.max(0,Math.min(1,points[index][axis]+delta));invalidateReview();draw();};
  });
  node('scanCancel').onclick=cancel;
  node('scanRun').onclick=async()=>{
    if(!source||busy)return;invalidateReview();const token=++generation;setBusy(true);status('Подготовка фото…');
    let prepared;
    try{
      await new Promise(resolve=>requestAnimationFrame(resolve));
      prepared=window.App.receiptScanImage.prepare(source,points);
      const started=performance.now();
      job=window.App.receiptScanEngine.recognize(prepared,p=>{if(token===generation)status(p===null?'Загрузка движка… В первый раз потребуется несколько мегабайт.':`Распознавание: ${p}%`);});
      const result=await job.promise;if(token!==generation||!result)return;
      originalText=result.text;node('scanText').value=originalText;showDraft(parser.parse(originalText));
      canvas.width=prepared.width;canvas.height=prepared.height;canvas.getContext('2d').drawImage(prepared,0,0);
      status(`Черновик за ${((performance.now()-started)/1000).toFixed(1)} с. Проверьте каждую строку: OCR может ошибаться.`);
    }catch(e){if(token===generation)status(e.message||'Не удалось распознать. Повторите попытку или введите чек вручную.');}
    finally{if(prepared){prepared.width=prepared.height=1;}if(token===generation){job=null;setBusy(false);}}
  };
  const decimal=cents=>cents==null?'':(cents/100).toFixed(2);
  const codeLookupKey=row=>JSON.stringify([node('scanShop').value,(row.code_entries||[]).map(e=>[e.code,e.manual_kind?e.kind:'auto'])]);
  function showDraft(value){
    draft=value;
    for(const row of draft.rows){if(row.total==null)parser.recalculateRow(row,'price');}
    draft.rows.forEach((row,index)=>row.scan_order=index);
    draft.rows=parser.mergeDuplicates(draft.rows,window.App.receiptCodes.validBarcode);
    dialog.dataset.stage='review';node('scanStep').textContent='Проверьте поля по фото';node('scanDate').value=draft.date;node('scanShop').value=draft.shop;node('scanTotal').value=decimal(draft.total);
    node('scanReview').hidden=false;node('scanConfirmed').checked=false;renderRows();validate();
  }
  function setCatalogOpen(list, open){
    const owner=list.closest('.scan-name'), name=owner.querySelector('[data-scan-field=name]');
    const syncClosed=()=>{list.hidden=true;name.setAttribute('aria-expanded','false');name.removeAttribute('aria-activedescendant');};
    list.hidden=!open;
    window.App.getRuntimeModule('picker-utils').setPopoverOpen(list,open,{owners:[owner],onClose:syncClosed});
    name.setAttribute('aria-expanded',String(open));
    if(!open)name.removeAttribute('aria-activedescendant');
  }
  function closeCatalogLists(){
    dialog.querySelectorAll('.scan-catalog-list').forEach(n=>setCatalogOpen(n,false));
  }
  function refreshCatalog(){
    node('scanRows').querySelectorAll('.scan-row').forEach(el=>{el.refreshCategory?.();el.refreshBrand?.();el.refreshCatalog?.();el.refreshSearch?.();});
  }
  function renderRows(){
    node('scanRows').replaceChildren();
    draft.rows.forEach((row,index)=>{
      const el=document.createElement('section');el.className='scan-row';
      el.innerHTML=`<div class="scan-name"><label class="field"><span>Товар ${index+1}</span><input data-scan-field="name" maxlength="160" placeholder="Найти или ввести товар" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="scanCatalog${index}" required></label><div id="scanCatalog${index}" class="scan-catalog-list receipt-name-picker app-popover hidden" role="listbox" hidden></div></div><div class="scan-row-actions">${iconButton('', 'trash', 'Удалить позицию '+(index+1))}</div><div class="scan-match"></div><div class="scan-codes-host"></div><label class="field scan-category"><span>Категория</span><select data-scan-category aria-label="Категория позиции"></select></label><label class="field scan-brand"><span>Бренд</span><select data-scan-brand aria-label="Бренд товара"></select></label><div class="scan-sale-units" role="group" aria-label="Единица цены и количества"></div><div class="scan-row-numbers">${[['price','Цена за ед.'],['quantity','Кол-во'],['discount','Скидка, сумма'],['total','Оплачено']].map(([field,label])=>`<label class="field"><span>${label}</span><input data-scan-field="${field}" inputmode="decimal" aria-describedby="scanMathHint" required></label>`).join('')}</div><label class="field scan-discount-type"><span>Тип скидки</span><select data-scan-field="discount_type"><option value="promo">Акция</option><option value="loyalty_points">Баллы</option><option value="coupon">Купон</option></select></label>`;
      const name=el.querySelector('[data-scan-field=name]'), list=el.querySelector('.scan-catalog-list'), match=el.querySelector('.scan-match');
      name.value=row.name;name.title=row.source||'';
      if(row.merged_rows?.length){
        const split=document.createElement('button');split.type='button';split.className='btn btn-secondary btn-xs';window.App.icons.apply(split,'split','Разделить обратно');split.dataset.scanSplit='';
        const confirmation=document.createElement('div');confirmation.className='scan-split-confirm';confirmation.hidden=true;
        const hint=document.createElement('small');hint.className='muted-small';hint.textContent='Восстановить количество, цены и скидки исходных строк?';
        const accept=document.createElement('button');accept.type='button';accept.className='btn btn-secondary btn-xs';window.App.icons.apply(accept,'save','Вернуть строки из чека');
        const cancel=document.createElement('button');cancel.type='button';cancel.className='btn btn-secondary btn-xs';window.App.icons.apply(cancel,'close','Отмена');
        const restore=()=>{
          const current=draft.rows.indexOf(row);if(current<0)return;
          const originals=parser.splitMergedRow(row);
          if(draft.rows.length-1+originals.length>150){status('Для разделения удалите лишние позиции: в чеке может быть до 150 строк.');return;}
          originals.forEach(restored=>restored.code_auto_attempted=codeLookupKey(restored));
          draft.rows.splice(current,1,...originals);
          draft.rows.sort((a,b)=>(a.scan_order??Infinity)-(b.scan_order??Infinity));
          node('scanConfirmed').checked=false;renderRows();validate();
          node('scanRows').children[draft.rows.indexOf(originals[0])]?.querySelector('[data-scan-field=name]')?.focus({preventScroll:true});closeCatalogLists();
        };
        split.onclick=()=>{if(parser.mergedMoneyChanged(row)){confirmation.hidden=false;accept.focus();}else restore();};
        accept.onclick=restore;cancel.onclick=()=>{confirmation.hidden=true;split.focus();};
        confirmation.append(hint,accept,cancel);el.querySelector('.scan-row-actions').prepend(split);el.append(confirmation);
      }
      el.querySelector('[data-scan-field=price]').title='Цена за единицу до скидки';
      const category=el.querySelector('[data-scan-category]');
      category.add(new Option('Без категории', ''));
      (state.categories||[]).filter(c=>c.kind==='expense').sort((a,b)=>a.name.localeCompare(b.name,'ru')).forEach(c=>category.add(core.createCategoryOption(c)));
      const refreshCategory=()=>{
        const choice=categoryChoice(row);category.value=String(choice.id||'');
        category.previousElementSibling.textContent=choice.reason?'Категория · предложена':'Категория';
        category.title=choice.reason||'';
      };
      el.refreshCategory=refreshCategory;
      refreshCategory();
      category.onchange=()=>{row.category_id=Number(category.value)||null;row.category_touched=true;refreshCategory();node('scanConfirmed').checked=false;validate();};
      const brand=el.querySelector('[data-scan-brand]');
      const refreshBrand=()=>{
        brand.replaceChildren(new Option('Без бренда',''));
        (state.itemBrands||[]).filter(b=>!b.is_archived).forEach(b=>brand.add(new Option(b.name,String(b.id))));
        const id=row.brand_touched?row.brand_id:row.catalog?.brand_id;
        if(id&&![...brand.options].some(o=>o.value===String(id)))brand.add(new Option(row.catalog?.brand_name||row.brand_name||'Выбранный бренд',String(id)));
        brand.value=String(id||'');
      };
      el.refreshBrand=refreshBrand;refreshBrand();
      brand.onchange=()=>{row.brand_id=Number(brand.value)||null;row.brand_touched=true;node('scanConfirmed').checked=false;validate();};
      const unitHost=el.querySelector('.scan-sale-units');
      const measurementControls=window.App.measurements.fields.map(key=>{
        const label=document.createElement('label'),input=document.createElement('input');
        input.value=row[key]??'';label.hidden=true;label.append(input);unitHost.append(label);
        input.addEventListener('input',()=>{
          Object.assign(row,Object.fromEntries(window.App.measurements.fields.map((field,i)=>[field,measurementControls[i].value||null])));
          if(row.catalog){row.catalog_edit_variant_id ||= row.catalog.variant_id||row.variant_snapshot?.variant_id||null;row.catalog_measurement_touched=true;}
          row.site_selection=null;row.variant_id=null;row.variant_snapshot=null;row.measurement_touched=true;
          refreshUnits();node('scanConfirmed').checked=false;validate();
        });return input;
      });
      const measurementEditor=window.App.measurements.mount(unitHost,measurementControls,{unitDataset:'scanUnit'});
      function refreshUnits(){
        measurementControls.forEach((input,i)=>{input.value=row[window.App.measurements.fields[i]]??'';});
        measurementEditor.refresh();
        for(const field of ['price','quantity']){
          const input=el.querySelector(`[data-scan-field=${field}]`);
          input.previousElementSibling.textContent=field==='price'?window.App.measurements.priceLabel(row):window.App.measurements.quantityLabel(row);
        }
      }
      function unlink(){row.catalog_name_touched=false;row.catalog_measurement_touched=false;row.catalog_edit_variant_id=null;el.querySelector('.scan-codes-host').invalidateSite?.();row.site_selection=null;row.site_name='';delete row.catalog;row.variant_id=null;row.variant_snapshot=null;row.code_match_label='';refreshCategory();refreshBrand();if(!row.measurement_touched)Object.assign(row,window.App.measurements.snapshot());refreshUnits();}
      refreshUnits();
      let options=[],active=-1;
      function choose(item){
        row.catalog_new=false;unlink();
        row.catalog=catalog().identity(item,node('scanShop').value);
        row.name=row.catalog.name;name.value=row.name;refreshCategory();refreshBrand();
        if(!row.measurement_touched){Object.assign(row,window.App.measurements.snapshot(row.catalog));row.variant_id=row.catalog.variant_id||null;}
        refreshUnits();
        closeCatalogLists();node('scanConfirmed').checked=false;el.refreshCatalog();el.refreshCodes?.();validate();name.focus();closeCatalogLists();
      }
      function createNew(){
        if(!name.value.trim())return;
        unlink();row.catalog_new=true;row.name=name.value.trim();name.value=row.name;
        closeCatalogLists();node('scanConfirmed').checked=false;el.refreshCatalog();el.refreshCodes?.();validate();
        name.focus({preventScroll:true});closeCatalogLists();
      }
      function searchAgain(){row.catalog_new=false;el.refreshCatalog();name.focus();search();}
      el.refreshCatalog=()=>{
        match.replaceChildren();match.classList.toggle('is-linked',!!row.catalog||!!row.catalog_new);
        if(row.catalog){
          const label=document.createElement('span');label.textContent=(row.code_match_label||'Из каталога')+' · '+(row.catalog.product_name||row.name);match.append(label);
          const clear=document.createElement('button');clear.type='button';clear.className='btn btn-secondary btn-icon';window.App.icons.apply(clear,'unlink','Отвязать товар каталога');clear.onclick=()=>{unlink();node('scanConfirmed').checked=false;el.refreshCatalog();validate();};match.append(clear);
        }else if(row.catalog_new){
          const label=document.createElement('span');label.textContent='Новый товар';match.append(label);
          const change=document.createElement('button');change.type='button';change.className='btn btn-secondary btn-icon';icons.apply(change,'search','Выбрать из каталога');change.onclick=searchAgain;match.append(change);
        }
        match.hidden=!match.childElementCount;
      };
      function search(){
        if(row.catalog_new||row.catalog){closeCatalogLists();return;}
        closeCatalogLists();options=catalog().suggestions(name.value,node('scanShop').value,8);active=-1;
        catalog().renderOptions(list,{suggestions:options,query:name.value.trim(),allowCreate:!options.some(item=>item.scan_match?.exact),showPrices:false,emptyText:catalogNotice()||'Нет совпадений'});
        list.querySelectorAll('.receipt-template-suggestion').forEach((button,i)=>{button.onclick=()=>choose(options[i]);});
        const create=list.querySelector('[data-receipt-create-name]');if(create)create.onclick=createNew;
        if(catalogNotice()&&list.querySelector('button')){const notice=document.createElement('span');notice.className='muted-small receipt-picker-empty';notice.textContent=catalogNotice();list.prepend(notice);}
        list.querySelectorAll('button').forEach((button,i)=>{button.id=`scanOption${index}-${i}`;button.setAttribute('role','option');button.setAttribute('aria-selected','false');button.tabIndex=-1;});
        setCatalogOpen(list,true);
      }
      el.refreshSearch=()=>{if(document.activeElement===name&&!list.hidden)search();};
      name.onfocus=search;
      name.onkeydown=e=>{
        if(['ArrowDown','ArrowUp'].includes(e.key)){
          e.preventDefault();if(row.catalog_new)searchAgain();else if(list.hidden)search();
          const choices=[...list.querySelectorAll('[role=option]')];if(!choices.length)return;
          active=active<0?(e.key==='ArrowDown'?0:choices.length-1):(active+(e.key==='ArrowDown'?1:-1)+choices.length)%choices.length;
          choices.forEach((b,i)=>b.setAttribute('aria-selected',String(i===active)));
          name.setAttribute('aria-activedescendant',choices[active].id);choices[active].scrollIntoView({block:'nearest'});
        }else if(e.key==='Enter'&&!list.hidden){e.preventDefault();if(active>=0)list.querySelectorAll('[role=option]')[active]?.click();}
      };
      el.addEventListener('focusout',()=>setTimeout(()=>{if(!el.querySelector('.scan-name').contains(document.activeElement)){setCatalogOpen(list,false);}},0));
      for(const field of ['price','quantity','discount','total']){const input=el.querySelector(`[data-scan-field=${field}]`);input.value=field==='quantity'?row.quantity??'':decimal(row[field]);input.placeholder='Не распознано';}
      el.querySelector('[data-scan-field=discount_type]').value=row.discount_type||'promo';el.querySelector('.scan-discount-type').hidden=!row.discount;
      el.addEventListener('input',e=>{
        const field=e.target.dataset.scanField;if(!field)return;
        row[field]=field==='name'||field==='discount_type'?e.target.value:field==='quantity'?inputNumber(e.target.value,true):inputMoney(e.target.value);
        if(field==='name'){row.name_touched=true;row.catalog_new=false;if(row.catalog){row.catalog_name_touched=true;row.site_selection=null;closeCatalogLists();}else unlink();el.refreshCatalog();search();}
        for(const changed of parser.recalculateRow(row,field)){
          const input=el.querySelector(`[data-scan-field=${changed}]`);input.value=decimal(row[changed]);
          input.setAttribute('aria-invalid',String(row[changed]==null||row[changed]<0||(changed==='total'&&row[changed]===0)));
        }
        el.querySelector('.scan-discount-type').hidden=!row.discount;node('scanConfirmed').checked=false;validate();
      });
      el.querySelector('.scan-row-actions > button:last-child').onclick=()=>{draft.rows.splice(index,1);node('scanConfirmed').checked=false;renderRows();validate();};
      el.unlinkCatalog=unlink;node('scanRows').append(el);el.refreshCatalog();
      el.refreshCodes=()=>{
        const key=codeLookupKey(row);
        const auto=!row.catalog_new&&!row.catalog&&row.code_auto_attempted!==key;row.code_auto_attempted=key;
        window.App.receiptCodes.mount(el.querySelector('.scan-codes-host'),{row,shop:()=>node('scanShop').value,auto,siteSearch:true,isActive:()=>dialog.open&&!transferred,
          onSiteSelect:found=>{if(!row.catalog&&!row.catalog_new&&!row.name_touched){row.name=found.name.slice(0,160);name.value=row.name;refreshCategory();el.refreshCatalog();}},
          onChange:()=>{node('scanConfirmed').checked=false;validate();},
          onSelect:found=>{
            row.catalog_new=false;window.App.receiptCodes.apply(row,found);row.catalog={...found};name.value=row.name;
            row.catalog_name_touched=false;row.catalog_measurement_touched=false;row.catalog_edit_variant_id=null;refreshCategory();refreshBrand();refreshUnits();el.refreshCatalog();closeCatalogLists();node('scanConfirmed').checked=false;validate();
          },
        });
      };el.refreshCodes();
    });
  }
  dialog.addEventListener('pointerdown',e=>{if(!e.target.closest('.scan-name'))closeCatalogLists();});
  function readMeta(){if(!draft)return;draft.date=node('scanDate').value;draft.shop=node('scanShop').value;draft.total=inputMoney(node('scanTotal').value);}
  function validate(){
    if(!draft)return;readMeta();const errors=parser.validate(draft);
    draft.rows.forEach((row,index)=>{const reason=window.App.receiptCodes.validationError(window.App.receiptCodes.payload(row),draft.shop);if(reason)errors.push(`Позиция ${index+1}: ${reason}`);});
    node('scanRows').querySelectorAll('.scan-codes-host').forEach(host=>host.refreshCodeState?.());
    node('scanArithmetic').textContent=errors.length?errors.join(' · '):'Суммы сходятся. Сверьте названия и цифры с фото.';
    node('scanArithmetic').classList.toggle('scan-error',!!errors.length);
    node('scanTransfer').disabled=errors.length>0||!node('scanConfirmed').checked||transferred;return errors;
  }
  function metaChanged(id){
    node('scanConfirmed').checked=false;
    if(id==='scanShop'&&draft?.shop!==node('scanShop').value){
      node('scanRows').querySelectorAll('.scan-row').forEach(el=>{el.unlinkCatalog();el.refreshCodes?.();});refreshCatalog();
    }
    validate();
  }
  for(const id of ['scanDate','scanShop','scanTotal','scanCurrency'])node(id).addEventListener('input',()=>metaChanged(id));
  node('scanShop').addEventListener('change',()=>metaChanged('scanShop'));
  function commitCalculation(input) {
    const quantity=input.dataset.scanField==='quantity';
    const result=inputNumber(input.value,quantity);
    if(result==null){input.setAttribute('aria-invalid','true');return;}
    input.removeAttribute('aria-invalid');
    input.value=quantity?String(result):result.toFixed(2);
    // Input already recalculated dependent fields; formatting alone must not recalculate again.
    validate();
  }
  const numericField=input=>input.matches?.('#scanTotal, [data-scan-field=price], [data-scan-field=quantity], [data-scan-field=discount], [data-scan-field=total]');
  node('scanReview').addEventListener('focusout',e=>{if(numericField(e.target))commitCalculation(e.target);});
  node('scanReview').addEventListener('keydown',e=>{if(e.key==='Enter'&&numericField(e.target)){e.preventDefault();commitCalculation(e.target);}});
  node('scanReview').addEventListener('input',e=>{if(numericField(e.target))e.target.setAttribute('aria-invalid',String(inputNumber(e.target.value,e.target.dataset.scanField==='quantity')==null));});
  node('scanConfirmed').onchange=validate;
  node('scanAddRow').onclick=()=>{if(draft.rows.length>=150)return;draft.rows.push({name:'',price:null,quantity:1,discount:0,total:null,source:'Добавлено вручную',discount_type:'promo',manual:true});node('scanConfirmed').checked=false;renderRows();validate();node('scanRows').lastElementChild.querySelector('input').focus();};
  function setTextMode(original){
    if(original===originalTextMode)return;
    if(original){editedText=node('scanText').value;node('scanText').value=originalText;}
    else node('scanText').value=editedText;
    originalTextMode=original;node('scanText').readOnly=original;node('scanReparse').hidden=original;
    node('scanTextModes').querySelectorAll('button').forEach(b=>b.classList.toggle('active',(b.dataset.textMode==='original')===original));
  }
  node('scanTextModes').onclick=e=>{const b=e.target.closest('[data-text-mode]');if(b)setTextMode(b.dataset.textMode==='original');};
  node('scanTextDialog').addEventListener('close',()=>setTextMode(false));
  node('scanShowText').onclick=()=>node('scanTextDialog').showModal();
  node('scanTextClose').onclick=()=>node('scanTextDialog').close();
  node('scanReparse').onclick=()=>{showDraft(parser.parse(node('scanText').value));node('scanTextDialog').close();};
  function transfer(replace=false){
    if(!draft||transferred||validate().length||!node('scanConfirmed').checked)return;
    const modal=window.App.getRuntimeModule('operation-modal');
    const mode=context==='create'?'create':'edit', prefix=mode==='create'?'op':'edit';
    if(mode==='create'&&(node('createModal').classList.contains('hidden')||node('opEntryMode').value!=='operation'||state.createFlowMode==='plan'))return;
    if(mode==='edit'&&(String(state.editOperationId)!==context||node('editModal').classList.contains('hidden')))return;
    if(!replace&&(state[mode+'ReceiptItems']?.some(r=>r.name||r.unit_price)||node(prefix+'Amount').value)){
      node('scanReplaceOperation').hidden=false;node('scanReplaceYes').focus();return;
    }
    node('scanReplaceOperation').hidden=true;
    pending[mode]={id:context,value:scanPayload()};
    transferred=true;
    modal.setOperationKind(mode,'expense');
    node(prefix+'Date').value=draft.date;node(prefix+'Date').dispatchEvent(new Event('change',{bubbles:true}));
    node(prefix+'Currency').value=node('scanCurrency').value;node(prefix+'Currency').dispatchEvent(new Event('change',{bubbles:true}));
    state[mode+'ReceiptItems']=draft.rows.map(r=>modal.createReceiptDraft({...r.catalog,catalog_editable:Boolean(r.catalog),catalog_name_touched:Boolean(r.catalog_name_touched),catalog_measurement_touched:Boolean(r.catalog_measurement_touched),catalog_edit_variant_id:r.catalog_edit_variant_id||null,...(r.brand_touched?{brand_id:r.brand_id,brand_touched:true}:{}),category_id:categoryChoice(r).id,category_touched:Boolean(r.category_touched||categoryChoice(r).reason),name:r.name,quantity:r.quantity,shop_name:draft.shop,...window.App.measurements.snapshot(r),variant_id:r.variant_id||null,variant_snapshot:r.variant_snapshot||null,site_selection:r.site_selection||null,site_name:r.site_name||'',code_entries:r.code_entries||[],code_match_label:r.code_match_label||'',measurement_touched:true,
      unit_price:r.price/100, is_discounted:r.discount>0, regular_unit_price:r.discount>0?r.price/100:null,
      discount_mode:r.discount>0?'amount':null, discount_value:r.discount>0?r.discount/100:null,
      discount_type:r.discount>0?r.discount_type||'promo':null,note:r.note||null},mode));
    if(mode==='create')modal.setCreateOperationMode('receipt');else modal.setEditOperationMode('receipt');
    node(prefix+'Amount').value=decimal(draft.total);node(prefix+'Amount').dispatchEvent(new Event('input',{bubbles:true}));
    modal.renderReceiptSummary(mode);applied=true;dialog.close();
  };
  node('scanReview').onsubmit=e=>{e.preventDefault();transfer();};
  node('scanReplaceYes').onclick=()=>transfer(true);
  node('scanReplaceNo').onclick=()=>{node('scanReplaceOperation').hidden=true;};
  const button=document.createElement('button');button.type='button';button.id='openReceiptScan';button.className='btn btn-secondary receipt-scan-entry';
  button.innerHTML=icons.svg('receipt')+'<span>Сканировать чек</span>';
  button.onclick=()=>open('create');
  node('createOperationForm').before(button);
  const savedButton=document.createElement('button');savedButton.type='button';savedButton.id='openSavedReceiptScan';savedButton.className='btn btn-secondary receipt-scan-entry';
  savedButton.innerHTML=icons.svg('receipt')+'<span>Исходный чек</span>';savedButton.hidden=true;savedButton.onclick=()=>open('edit');
  node('editOperationForm').before(savedButton);
  window.App.registerRuntimeModule('receipt-scan',{
    beginOperation(){pending.create=null;applied=false;if(context==='create')transferred=false;else if(createRecovery)createRecovery.applied=false;refreshEntry();},
    editOperation(item){openGeneration++;savedButton.hidden=!item.has_receipt_scan;pending.edit=null;if(context!=='create'){cleanup();context='';}},
    payload(mode){
      const entry=pending[mode];
      if(!entry||(mode==='edit'&&entry.id!==String(state.editOperationId)))return null;
      // Keep corrections made in the operation (including removed conflicting codes).
      return {...entry.value,review:savedReview(operationReview(mode,entry.value.review))};
    },
    saved(mode){pending[mode]=null;if(mode==='create'){createRecovery=null;if(context==='create')cleanup();}else if(context!=='create'){cleanup();context='';}refreshEntry();},
    photosDeleted(){
      // Never re-upload a removed saved photo from the open editor's cached attachment.
      if(pending.edit)pending.edit.value.image=null;
      if(context!=='create'){storedImage=null;source=null;canvas.width=canvas.height=1;canvas.hidden=true;node('scanNoPhoto').hidden=false;node('scanBack').hidden=true;}
    },
    reset(){openGeneration++;if(dialog.open)dialog.close();cleanup();createRecovery=null;pending.create=pending.edit=null;context='create';},
  });
  function refreshEntry(){button.querySelector('span').textContent=pending.create?'Проверить чек':((context==='create'&&(draft||source))||createRecovery)?'Продолжить чек':'Сканировать чек';}
  const sync=()=>{button.hidden=node('opEntryMode').value!=='operation'||state.createFlowMode==='plan';if(node(context==='create'?'createModal':'editModal').classList.contains('hidden')&&dialog.open)dialog.close();};
  new MutationObserver(sync).observe(node('createModal'),{attributes:true,attributeFilter:['class']});
  new MutationObserver(sync).observe(node('editModal'),{attributes:true,attributeFilter:['class']});
  node('createEntryModeSwitch').addEventListener('click',()=>queueMicrotask(sync));
  cleanup();
})();
