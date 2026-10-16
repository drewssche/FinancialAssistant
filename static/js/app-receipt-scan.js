(() => {
  const {icons, state, core} = window.App;
  const parser = window.App.receiptScanParser;
  function inputNumber(value, quantity = false) {
    const result = core.evaluateMathExpression(String(value).replace(/−/g, '-').replace(/×/g, '*').replace(/÷/g, '/'), quantity ? 3 : 2);
    return result.ok && result.value >= 0 && result.value <= (quantity ? 100000 : 9999999.99) ? result.value : null;
  }
  const inputMoney = value => {const result = inputNumber(value);return result == null ? null : Math.round(result * 100);};
  const rowTotal = row => row.price != null && row.quantity > 0 && row.discount != null ? Math.round(row.price * Math.round(row.quantity * 1000) / 1000) - row.discount : null;
  const node = id => document.getElementById(id);
  const dialog = document.createElement('dialog');
  dialog.id='receiptScanDialog';dialog.className='receipt-scan-dialog';dialog.setAttribute('aria-labelledby','receiptScanTitle');
  const iconButton=(id,icon,label)=>`<button id="${id}" type="button" class="btn btn-secondary btn-icon" aria-label="${label}" title="${label}">${icons.svg(icon)}</button>`;
  dialog.innerHTML=`<header><h3 id="receiptScanTitle">Сканировать чек</h3>${iconButton('scanClose','close','Закрыть сканирование')}</header>
    <p class="muted-small" id="scanPrivacy">Фото обрабатывается на устройстве.</p>
    <button type="button" id="scanDropzone" class="scan-dropzone">${icons.svg('upload')}<strong>Выберите или перетащите фото чека</strong><span>Или вставьте из буфера: <kbd>Ctrl+V</kbd> / <kbd>⌘V</kbd></span><small>JPG, PNG, WebP · до 20 МБ</small></button>
    <div class="scan-toolbar" id="scanPhotoTools">${iconButton('scanBack','back','Изменить фото и распознать заново')}${iconButton('scanUpload','upload','Загрузить фото чека')}${iconButton('scanRotate','refresh','Повернуть фото')}${iconButton('scanReset','expand','Сбросить углы')}<input id="scanFile" type="file" accept="image/jpeg,image/png,image/webp" hidden><span id="scanStep" class="muted-small">Загрузите фото или вставьте Ctrl+V / ⌘V · до 20 МБ</span></div>
    <div id="scanPasteReplace" class="scan-toolbar" hidden><span>Заменить фото и сбросить текущий черновик?</span>${iconButton("scanPasteAccept","save","Заменить фото")}${iconButton("scanPasteDismiss","close","Оставить текущий чек")}</div><div id="scanWorkspace" hidden><div class="scan-image-column"><div id="scanImageFrame"><canvas id="scanCanvas"></canvas><svg id="scanOutline" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polygon fill="#79acff18" stroke="#79acff" stroke-width=".5"/></svg>${[0,1,2,3].map((i)=>`<button type="button" class="scan-corner" data-corner="${i}" aria-label="Угол ${i+1} чека">${i+1}</button>`).join('')}</div><p id="scanCropHint" class="muted-small">Подвиньте углы к краям чека</p></div>
    <form id="scanReview" hidden><div class="scan-meta"><label class="field"><span>Дата покупки</span><input id="scanDate" type="date" required></label><label class="field"><span>Магазин</span><input id="scanShop" maxlength="160" required></label><label class="field"><span>Итого по чеку</span><input id="scanTotal" inputmode="decimal" aria-describedby="scanMathHint" required></label><label class="field"><span>Валюта</span><select id="scanCurrency"><option>BYN</option><option>RUB</option><option>USD</option><option>EUR</option></select></label></div>
    <div class="scan-review-toolbar"><strong>Позиции</strong>${iconButton('scanAddRow','plus','Добавить строку')}${iconButton('scanShowText','receipt','Распознанный текст')}</div><p class="sr-only" id="scanMathHint">Можно вводить вычисления: 7,11 − 0,71 · Enter — получить результат.</p><div id="scanRows"></div>
    <p id="scanArithmetic" role="status"></p><label class="scan-confirm"><input id="scanConfirmed" type="checkbox">Сверил дату, магазин, валюту и позиции с фото</label>
    <footer><button type="submit" class="btn btn-primary btn-icon" id="scanTransfer" aria-label="В черновик операции" title="В черновик операции" disabled>${icons.svg("save")}</button></footer></form></div>
    <p id="scanStatus" class="muted-small" role="status"></p><footer id="scanRunBar"><button id="scanCancel" type="button" class="btn btn-secondary btn-icon" aria-label="Отменить распознавание" title="Отменить распознавание" hidden>${icons.svg("close")}</button><button id="scanRun" type="button" class="btn btn-primary btn-icon" aria-label="Распознать чек" title="Распознать чек" disabled>${icons.svg("receipt")}</button></footer>
    <dialog id="scanTextDialog" class="choice-dialog task-dialog"><header><h3>Распознанный текст</h3>${iconButton('scanTextClose','close','Закрыть текст')}</header><textarea id="scanText" rows="15" maxlength="80000" aria-label="Распознанный текст"></textarea><button id="scanReparse" class="btn btn-primary btn-icon" type="button" aria-label="Разобрать исправленный текст" title="Разобрать исправленный текст">${icons.svg("refresh")}</button></dialog>`;
  document.body.append(dialog);
  let source=null, points=[], draft=null, job=null, generation=0, transferred=false, originalText='', busy=false, pendingPaste=null;
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
  function invalidateReview(){dialog.dataset.stage=source?'crop':'upload';node('scanStep').textContent='Границы чека';draft=null;node('scanReview').hidden=true;node('scanConfirmed').checked=false;transferred=false;}
  function cancel(){generation++;job?.cancel();job=null;setBusy(false);status('Распознавание отменено');}
  function cleanup(){dialog.classList.remove('scan-drag-over');pendingPaste=null;node('scanPasteReplace').hidden=true;cancel();node('scanTextDialog').close();if(source)source.width=source.height=1;source=null;canvas.width=canvas.height=1;node('scanFile').value='';node('scanText').value='';node('scanRows').replaceChildren();originalText='';invalidateReview();node('scanWorkspace').hidden=true;setBusy(false);status('');}
  function open(){cleanup();dialog.showModal();node('scanDropzone').focus();catalog().load().then(()=>{if(draft)refreshCatalog();}).catch(()=>{});}
  node('scanClose').onclick=()=>dialog.close();
  dialog.addEventListener('close',cleanup);
  dialog.addEventListener('click',e=>{const r=dialog.getBoundingClientRect();if(e.target===dialog&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dialog.close();});
  // Installed before the global choice listener: Escape in a nested choice belongs to it.
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||!dialog.open||node('appChoiceDialog')?.open)return;
    e.preventDefault();e.stopImmediatePropagation();
    const list=dialog.querySelector('.scan-catalog-list:not([hidden])');
    if(list&&!node('scanTextDialog').open){closeCatalogLists();return;}
    if(node('scanTextDialog').open)node('scanTextDialog').close();else dialog.close();
  },true);
  node('scanUpload').onclick=node('scanDropzone').onclick=()=>node('scanFile').click();
  async function loadImage(file){
    if(!file)return;
    pendingPaste=null;node('scanPasteReplace').hidden=true;
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>20*1024*1024){status('Выберите JPG, PNG или WebP размером до 20 МБ');node('scanFile').value='';return;}
    cancel();invalidateReview();const token=++generation;setBusy(true);status('Открываю фото…');
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
    for(const row of draft.rows){if(row.total==null){row.autoTotal=true;row.total=rowTotal(row);}}
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
    node('scanRows').querySelectorAll('.scan-row').forEach(el=>{el.refreshCatalog?.();el.refreshSearch?.();});
  }
  function renderRows(){
    node('scanRows').replaceChildren();
    draft.rows.forEach((row,index)=>{
      const el=document.createElement('section');el.className='scan-row';
      el.innerHTML=`<div class="scan-name"><label class="field"><span>Товар ${index+1}</span><input data-scan-field="name" maxlength="160" placeholder="Найти или ввести товар" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="scanCatalog${index}" required></label><div id="scanCatalog${index}" class="scan-catalog-list app-popover hidden" role="listbox" hidden></div></div>${iconButton('', 'trash', 'Удалить позицию '+(index+1))}<div class="scan-match"></div><div class="scan-codes-host"></div><label class="field scan-category"><span>Категория</span><select data-scan-category aria-label="Категория позиции"></select></label><div class="scan-sale-units" role="group" aria-label="Единица цены и количества"></div><div class="scan-row-numbers">${[['price','Цена за ед.'],['quantity','Кол-во'],['discount','Скидка, сумма'],['total','Оплачено']].map(([field,label])=>`<label class="field"><span>${label}</span><input data-scan-field="${field}" inputmode="decimal" aria-describedby="scanMathHint" required></label>`).join('')}</div><label class="field scan-discount-type"><span>Тип скидки</span><select data-scan-field="discount_type"><option value="promo">Акция</option><option value="loyalty_points">Баллы</option><option value="coupon">Купон</option></select></label>`;
      const name=el.querySelector('[data-scan-field=name]'), list=el.querySelector('.scan-catalog-list'), match=el.querySelector('.scan-match');
      name.value=row.name;name.title=row.source||'';
      if(row.merged_rows?.length){
        const group=document.createElement('div');group.className='scan-merged-actions';
        const note=document.createElement('small');note.className='scan-merged-note muted-small';note.textContent=`${row.merged_rows.length} строки вместе`;
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
        confirmation.append(hint,accept,cancel);group.append(note,split,confirmation);el.querySelector('.scan-name').append(group);
      }
      el.querySelector('[data-scan-field=price]').title='Цена за единицу до скидки';
      const category=el.querySelector('[data-scan-category]');
      category.add(new Option('Без категории', ''));
      (state.categories||[]).filter(c=>c.kind==='expense').sort((a,b)=>a.name.localeCompare(b.name,'ru')).forEach(c=>category.add(core.createCategoryOption(c)));
      const refreshCategory=()=>{category.value=String(row.category_touched?row.category_id||'':row.catalog?.category_id||'');};
      refreshCategory();
      category.onchange=()=>{row.category_id=Number(category.value)||null;row.category_touched=true;node('scanConfirmed').checked=false;validate();};
      const unitHost=el.querySelector('.scan-sale-units');
      const unitTitle=document.createElement('span');unitTitle.textContent='Единица цены';unitHost.append(unitTitle);
      for(const [unit,label] of [['','Не указана'],...Object.entries(window.App.measurements.units)]){
        const button=document.createElement('button');button.type='button';button.className='btn btn-secondary measurement-unit';button.dataset.scanUnit=unit;button.textContent=label;
        button.onclick=()=>{row.sale_unit=unit||null;row.package_quantity=null;row.package_unit=null;row.variant_id=null;row.variant_snapshot=null;row.code_save=false;row.measurement_touched=true;refreshUnits();node('scanConfirmed').checked=false;validate();};unitHost.append(button);
      }
      function refreshUnits(){
        unitHost.querySelectorAll('button').forEach(button=>{const active=button.dataset.scanUnit===(row.sale_unit||'');button.classList.toggle('is-active',active);button.setAttribute('aria-pressed',String(active));});
        for(const field of ['price','quantity']){
          const input=el.querySelector(`[data-scan-field=${field}]`);
          input.previousElementSibling.textContent=field==='price'?window.App.measurements.priceLabel(row):window.App.measurements.quantityLabel(row);
        }
      }
      function unlink(){delete row.catalog;row.variant_id=null;row.variant_snapshot=null;row.code_match_label='';row.code_save=false;refreshCategory();if(!row.measurement_touched)Object.assign(row,window.App.measurements.snapshot());refreshUnits();}
      refreshUnits();
      let options=[],active=-1;
      function choose(item){
        unlink();
        row.catalog=catalog().identity(item,node('scanShop').value);
        row.name=row.catalog.name;name.value=row.name;refreshCategory();
        if(!row.measurement_touched){Object.assign(row,window.App.measurements.snapshot(row.catalog));row.variant_id=row.catalog.variant_id||null;}
        refreshUnits();
        closeCatalogLists();node('scanConfirmed').checked=false;el.refreshCatalog();validate();name.focus();closeCatalogLists();
      }
      function suggestionButton(item){
        const b=document.createElement('button');b.type='button';b.className='scan-catalog-option';
        const title=document.createElement('strong');title.textContent=item.name;
        const sub=document.createElement('small');sub.textContent=[item.selected_offer?.shop_name||item.selected_offer?.source_name||item.shop_name, item.brand_name].filter(Boolean).join(' · ')||'Каталог';
        if(item.scan_match){
          const words=item.scan_match.words.slice(0,3).join(', ');
          sub.textContent=[item.scan_match.exact?'Название совпадает':words?`По словам: ${words}`:'Совпадение в названии',item.scan_match.sizeConflict?'Другой размер упаковки':''].filter(Boolean).join(' · ');
        }
        b.append(title,sub);b.onclick=()=>choose(item);return b;
      }
      el.refreshCatalog=()=>{
        match.replaceChildren();match.classList.toggle('is-linked',!!row.catalog);
        if(row.catalog){
          const label=document.createElement('span');label.textContent=(row.code_match_label||'Из каталога')+' · '+(row.catalog.product_name||row.name);match.append(label);
          const clear=document.createElement('button');clear.type='button';clear.className='btn btn-secondary btn-icon';window.App.icons.apply(clear,'unlink','Отвязать товар каталога');clear.onclick=()=>{unlink();node('scanConfirmed').checked=false;el.refreshCatalog();validate();};match.append(clear);
        }else if(row.name.trim()){
          const candidates=catalog().suggestions(row.name,node('scanShop').value,3);
          const heading=document.createElement('div');heading.className='scan-match-heading';
          const label=document.createElement('span');label.textContent=catalogNotice()||(candidates.length?'Варианты из каталога':'В каталоге нет совпадений по словам');heading.append(label);
          const more=document.createElement('button');more.type='button';more.className='btn btn-secondary btn-icon';icons.apply(more,'search','Искать товар в каталоге');more.onclick=async()=>{if(catalog().status().incomplete){await catalog().load();refreshCatalog();}name.focus();search();};heading.append(more);match.append(heading);
          candidates.forEach(candidate=>{const b=suggestionButton(candidate);b.classList.add('scan-suggestion');b.title='Выбрать товар из каталога';match.append(b);});
        }
        match.hidden=!match.childElementCount;
      };
      function search(){
        closeCatalogLists();options=catalog().suggestions(name.value,node('scanShop').value,8);active=-1;list.replaceChildren();
        options.forEach((item,i)=>{const b=suggestionButton(item);b.id=`scanOption${index}-${i}`;b.setAttribute('role','option');b.setAttribute('aria-selected','false');b.tabIndex=-1;list.append(b);});
        if(!options.length){const empty=document.createElement('span');empty.className='muted-small';empty.textContent=catalogNotice()||'В каталоге нет совпадений по словам';list.append(empty);}
        setCatalogOpen(list,true);
      }
      el.refreshSearch=()=>{if(document.activeElement===name&&!list.hidden)search();};
      name.onfocus=search;
      name.onkeydown=e=>{
        if(['ArrowDown','ArrowUp'].includes(e.key)){
          e.preventDefault();if(list.hidden)search();if(!options.length)return;
          active=active<0?(e.key==='ArrowDown'?0:options.length-1):(active+(e.key==='ArrowDown'?1:-1)+options.length)%options.length;
          Array.from(list.children).forEach((b,i)=>b.setAttribute('aria-selected',String(i===active)));
          name.setAttribute('aria-activedescendant',list.children[active].id);list.children[active].scrollIntoView({block:'nearest'});
        }else if(e.key==='Enter'&&!list.hidden){e.preventDefault();if(active>=0)choose(options[active]);}
      };
      el.addEventListener('focusout',()=>setTimeout(()=>{if(!el.querySelector('.scan-name').contains(document.activeElement)){setCatalogOpen(list,false);}},0));
      for(const field of ['price','quantity','discount','total']){const input=el.querySelector(`[data-scan-field=${field}]`);input.value=field==='quantity'?row.quantity??'':decimal(row[field]);input.placeholder='Не распознано';}
      el.querySelector('[data-scan-field=discount_type]').value=row.discount_type||'promo';el.querySelector('.scan-discount-type').hidden=!row.discount;
      el.addEventListener('input',e=>{
        const field=e.target.dataset.scanField;if(!field)return;
        row[field]=field==='name'||field==='discount_type'?e.target.value:field==='quantity'?inputNumber(e.target.value,true):inputMoney(e.target.value);
        if(field==='name'){unlink();el.refreshCatalog();search();}
        if(field==='total')row.autoTotal=false;
        if(row.autoTotal&&['price','quantity','discount'].includes(field)){
          row.total=rowTotal(row);
          el.querySelector('[data-scan-field=total]').value=decimal(row.total);
        }
        el.querySelector('.scan-discount-type').hidden=!row.discount;node('scanConfirmed').checked=false;validate();
      });
      el.querySelector(':scope > button').onclick=()=>{draft.rows.splice(index,1);node('scanConfirmed').checked=false;renderRows();validate();};
      el.unlinkCatalog=unlink;node('scanRows').append(el);el.refreshCatalog();
      el.refreshCodes=()=>{
        const key=codeLookupKey(row);
        const auto=!row.catalog&&row.code_auto_attempted!==key;row.code_auto_attempted=key;
        window.App.receiptCodes.mount(el.querySelector('.scan-codes-host'),{row,shop:()=>node('scanShop').value,auto,
          onChange:()=>{node('scanConfirmed').checked=false;validate();},
          onSelect:found=>{
            window.App.receiptCodes.apply(row,found);row.catalog={...found};name.value=row.name;
            refreshCategory();refreshUnits();el.refreshCatalog();closeCatalogLists();node('scanConfirmed').checked=false;validate();
          },
        });
      };el.refreshCodes();
    });
  }
  dialog.addEventListener('pointerdown',e=>{if(!e.target.closest('.scan-name'))closeCatalogLists();});
  function readMeta(){if(!draft)return;draft.date=node('scanDate').value;draft.shop=node('scanShop').value;draft.total=inputMoney(node('scanTotal').value);}
  function validate(){
    if(!draft)return;readMeta();const errors=parser.validate(draft);
    node('scanRows').querySelectorAll('.scan-codes-host').forEach(host=>host.refreshCodeState?.());
    node('scanArithmetic').textContent=errors.length?errors.join(' · '):'Суммы сходятся. Сверьте названия и цифры с фото.';
    node('scanArithmetic').classList.toggle('scan-error',!!errors.length);
    node('scanTransfer').disabled=errors.length>0||!node('scanConfirmed').checked||transferred;return errors;
  }
  for(const id of ['scanDate','scanShop','scanTotal','scanCurrency'])node(id).addEventListener('input',()=>{node('scanConfirmed').checked=false;if(id==='scanShop'){node('scanRows').querySelectorAll('.scan-row').forEach(el=>{el.unlinkCatalog();el.refreshCodes?.();});refreshCatalog();}validate();});
  function commitCalculation(input) {
    const quantity=input.dataset.scanField==='quantity';
    const result=inputNumber(input.value,quantity);
    if(result==null){input.setAttribute('aria-invalid','true');return;}
    input.removeAttribute('aria-invalid');
    input.value=quantity?String(result):result.toFixed(2);
    // Typing already updated the draft; formatting must not turn an automatic total into a manual override.
    validate();
  }
  const numericField=input=>input.matches?.('#scanTotal, [data-scan-field=price], [data-scan-field=quantity], [data-scan-field=discount], [data-scan-field=total]');
  node('scanReview').addEventListener('focusout',e=>{if(numericField(e.target))commitCalculation(e.target);});
  node('scanReview').addEventListener('keydown',e=>{if(e.key==='Enter'&&numericField(e.target)){e.preventDefault();commitCalculation(e.target);}});
  node('scanReview').addEventListener('input',e=>{if(numericField(e.target))e.target.setAttribute('aria-invalid',String(inputNumber(e.target.value,e.target.dataset.scanField==='quantity')==null));});
  node('scanConfirmed').onchange=validate;
  node('scanAddRow').onclick=()=>{if(draft.rows.length>=150)return;draft.rows.push({name:'',price:null,quantity:1,discount:0,total:null,source:'Добавлено вручную',discount_type:'promo',manual:true,autoTotal:true});node('scanConfirmed').checked=false;renderRows();validate();node('scanRows').lastElementChild.querySelector('input').focus();};
  node('scanShowText').onclick=()=>node('scanTextDialog').showModal();
  node('scanTextClose').onclick=()=>node('scanTextDialog').close();
  node('scanReparse').onclick=()=>{showDraft(parser.parse(node('scanText').value));node('scanTextDialog').close();};
  node('scanReview').onsubmit=e=>{
    e.preventDefault();if(!draft||transferred||validate().length||!node('scanConfirmed').checked)return;
    // Import only into an empty new-operation form. Existing edits are never overwritten.
    const modal=window.App.getRuntimeModule('operation-modal');
    if(node('createModal').classList.contains('hidden')||node('opEntryMode').value!=='operation'||state.createFlowMode==='plan'||state.createReceiptItems?.some(r=>r.name||r.unit_price)||node('opAmount').value){status('В операции уже есть данные. Закройте сканирование и откройте новую пустую операцию.');return;}
    transferred=true;
    modal.setOperationKind('create','expense');
    node('opDate').value=draft.date;node('opDate').dispatchEvent(new Event('change',{bubbles:true}));
    node('opCurrency').value=node('scanCurrency').value;node('opCurrency').dispatchEvent(new Event('change',{bubbles:true}));
    state.createReceiptItems=draft.rows.map(r=>modal.createReceiptDraft({...r.catalog,category_id:r.category_touched?r.category_id:r.catalog?.category_id,category_touched:Boolean(r.category_touched),name:r.name,quantity:r.quantity,shop_name:draft.shop,...window.App.measurements.snapshot(r),variant_id:r.variant_id||null,variant_snapshot:r.variant_snapshot||null,code_entries:r.code_entries||[],code_save:Boolean(r.code_save),code_match_label:r.code_match_label||'',measurement_touched:true,
      unit_price:r.price/100, is_discounted:r.discount>0, regular_unit_price:r.discount>0?r.price/100:null,
      discount_mode:r.discount>0?'amount':null, discount_value:r.discount>0?r.discount/100:null,
      discount_type:r.discount>0?r.discount_type||'promo':null,note:null},'create'));
    modal.setCreateOperationMode('receipt');
    node('opAmount').value=decimal(draft.total);node('opAmount').dispatchEvent(new Event('input',{bubbles:true}));
    modal.renderReceiptSummary('create');dialog.close();
  };
  const button=document.createElement('button');button.type='button';button.id='openReceiptScan';button.className='btn btn-secondary receipt-scan-entry';
  button.innerHTML=icons.svg('receipt')+'<span><strong>Сканировать чек</strong><small>Фото, файл или вставка из буфера</small></span>';
  button.onclick=open;
  node('createOperationForm').before(button);
  const sync=()=>{button.hidden=node('opEntryMode').value!=='operation'||state.createFlowMode==='plan';if(node('createModal').classList.contains('hidden')&&dialog.open)dialog.close();};
  new MutationObserver(sync).observe(node('createModal'),{attributes:true,attributeFilter:['class']});
  node('createEntryModeSwitch').addEventListener('click',()=>queueMicrotask(sync));
})();
