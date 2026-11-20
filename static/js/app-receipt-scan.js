(() => {
  const {icons, state, core} = window.App;
  const parser = window.App.receiptScanParser;
  const categoryChoice = row => window.App.receiptCategories.resolve(row, state.categories || [], state.receiptProductHints || []);
  function inputNumber(value, quantity = false) {
    const result = core.evaluateMathExpression(String(value).replace(/−/g, '-').replace(/×/g, '*').replace(/÷/g, '/'), quantity ? 3 : 2);
    return result.ok && result.value >= 0 && result.value <= (quantity ? 100000 : 9999999.99) ? result.value : null;
  }
  const inputMoney = value => {const result = inputNumber(value);return result == null ? null : Math.round(result * 100);};
  // A receipt often prints the deduction with a minus. Store its magnitude once.
  const discountText = value => String(value).trim().replace(/^[-−–—]\s*(?=\d+(?:[.,]\d+)?$)/, '');
  const inputDiscount = value => inputMoney(discountText(value));
  const node = id => document.getElementById(id);
  const dialog = document.createElement('dialog');
  dialog.id='receiptScanDialog';dialog.className='receipt-scan-dialog';dialog.setAttribute('aria-labelledby','receiptScanTitle');
  const iconButton=(id,icon,label)=>`<button id="${id}" type="button" class="btn btn-secondary btn-icon" aria-label="${label}" title="${label}">${icons.svg(icon)}</button>`;
  dialog.innerHTML=`<header>${iconButton('scanBack','back','Изменить фото и распознать заново')}<h3 id="receiptScanTitle" tabindex="-1">Сканировать чек</h3>${iconButton('scanClose','close','Закрыть сканирование')}</header>
    <label class="field scan-engine-choice"><span>Распознавание</span><select id="scanEngine"><option value="local">Tesseract · на устройстве</option><option value="rapid" disabled>RapidOCR · на сервере</option></select></label>
    <p class="muted-small" id="scanPrivacy">Фото обрабатывается на устройстве.</p>
    <button type="button" id="scanDropzone" class="scan-dropzone">${icons.svg('upload')}<strong>Выберите или перетащите фото чека</strong><span>Или вставьте из буфера: <kbd>Ctrl+V</kbd> / <kbd>⌘V</kbd></span><small>JPG, PNG, WebP · до 20 МБ</small></button>
    <div class="scan-toolbar" id="scanPhotoTools">${iconButton('scanUpload','upload','Загрузить фото чека')}${iconButton('scanRotate','refresh','Повернуть фото')}${iconButton('scanReset','expand','Сбросить углы')}<input id="scanFile" type="file" accept="image/jpeg,image/png,image/webp" hidden><span id="scanStep" class="muted-small">Загрузите фото или вставьте Ctrl+V / ⌘V · до 20 МБ</span></div>
    <div id="scanPasteReplace" class="scan-toolbar" hidden><span>Заменить фото и сбросить текущий черновик?</span>${iconButton("scanPasteAccept","save","Заменить фото")}${iconButton("scanPasteDismiss","close","Оставить текущий чек")}</div><div id="scanWorkspace" hidden><div class="scan-image-column"><div id="scanImageFrame"><canvas id="scanCanvas" role="img" aria-label="Фото чека"></canvas><div id="scanNoPhoto" hidden>Фото чека не сохранено или удалено</div><svg id="scanOutline" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polygon fill="#79acff18" stroke="#79acff" stroke-width=".5"/></svg>${[0,1,2,3].map((i)=>`<button type="button" class="scan-corner" data-corner="${i}" aria-label="Угол ${i+1} чека">${i+1}</button>`).join('')}</div>
      <div class="scan-zoom-tools" role="group" aria-label="Масштаб фото чека">
        ${iconButton('scanZoomOut','minus','Уменьшить фото')}<span id="scanZoomLevel">100%</span>${iconButton('scanZoomIn','plus','Увеличить фото')}
        ${iconButton('scanZoomFit','fitImage','Показать чек целиком')}
      </div><p id="scanCropHint" class="muted-small">Подвиньте углы к краям чека</p></div>
    <form id="scanReview" hidden><div class="scan-meta">
      <div class="scan-date-and-shop">
        <div class="field scan-date-field">
          <div class="scan-date-controls">
            <label for="scanDate"><span>Дата покупки</span></label>
            <div class="date-input-wrap" data-date-stepper>
              <input id="scanDate" type="date" required>
              <button type="button" class="date-input-trigger" data-date-picker-trigger="scanDate" title="Открыть календарь" aria-label="Открыть календарь"></button>
            </div>
            <button type="button" class="btn btn-secondary btn-icon" data-date-step-target="scanDate" data-date-step="today" title="Сегодня" aria-label="Сегодня">${icons.svg('calendarToday')}</button>
          </div>
        </div>
        <label class="field"><span>Магазин</span><input id="scanShop" maxlength="160" placeholder="Выбрать или ввести магазин" autocomplete="off" required></label>
      </div>
      <label class="field"><span>Итого по чеку</span><input id="scanTotal" inputmode="decimal" aria-describedby="scanMathHint" required></label><label class="field"><span>Валюта</span><select id="scanCurrency"><option>BYN</option><option>RUB</option><option>USD</option><option>EUR</option></select></label></div>
    <section id="scanDiscountReview" aria-label="Сверка скидок" hidden>
      <dl class="scan-discount-totals">
        <div><dt>До скидок</dt><dd id="scanGrossSum"></dd></div>
        <div><dt>Скидки по позициям</dt><dd id="scanDiscountSum"></dd></div>
        <div><dt>К оплате по позициям</dt><dd id="scanPaidSum"></dd></div>
      </dl>
      <details><summary id="scanDiscountStatus" aria-live="polite">Сверить со строкой «Итого скидка»</summary>
        <label class="field"><span>«Итого скидка» с чека</span><input id="scanPrintedDiscount" inputmode="decimal" placeholder="Не указано" aria-describedby="scanDiscountStatus"></label>
      </details>
      <button type="button" class="btn btn-secondary" id="scanFillDiscount" hidden></button>
    </section>
    <div class="scan-review-toolbar"><strong>Позиции</strong><button type="button" id="scanShowPhoto" class="btn btn-secondary" aria-haspopup="dialog">Посмотреть чек</button>${iconButton('scanAddRow','plus','Добавить строку')}${iconButton('scanShowText','receipt','Распознанный текст')}<button type="button" id="scanNextIssue" class="btn btn-secondary" hidden></button></div>
    <div id="scanEmptyRows" hidden><p>Позиции не найдены. Их можно добавить вручную кнопкой «+».</p><button type="button" id="scanRetry" class="btn btn-secondary">${icons.svg('refresh')}Распознать ещё раз</button><button type="button" id="scanRetryCancel" class="btn btn-secondary" hidden>Отменить распознавание</button><p id="scanRetryStatus" class="muted-small" role="status"></p></div>
    <p class="sr-only" id="scanMathHint">Можно вводить вычисления: 7,11 − 0,71 · Enter — получить результат.</p><div id="scanRows"></div>
    <p id="scanArithmetic" role="status"></p><div id="scanReplaceOperation" class="scan-toolbar" hidden><span>Заменить заполненные поля операции данными этого чека?</span>${iconButton('scanReplaceYes','save','Заменить данные операции')}${iconButton('scanReplaceNo','close','Оставить операцию')}</div><label class="scan-confirm"><input id="scanConfirmed" type="checkbox">Проверил дату, магазин, валюту и позиции</label>
    <footer><div id="scanScrollNav" role="group" aria-label="Прокрутка чека" hidden>
      ${iconButton('scanScrollTop','up','К началу чека')}${iconButton('scanScrollBottom','down','К концу чека')}
    </div><button type="submit" class="btn btn-primary" id="scanTransfer" disabled>${icons.svg("save")}<span></span></button></footer></form></div>
    <section id="scanSubmission" hidden><strong id="scanSubmissionReceipt"></strong><p id="scanSubmissionMessage" role="status"></p><button type="button" id="scanSubmitRetry" class="btn btn-primary">Повторить сохранение</button></section>
    <p id="scanStatus" class="muted-small" role="status"></p><footer id="scanRunBar"><button id="scanCancel" type="button" class="btn btn-secondary btn-icon" aria-label="Отменить распознавание" title="Отменить распознавание" hidden>${icons.svg("close")}</button><button id="scanRun" type="button" class="btn btn-primary btn-icon" aria-label="Распознать чек" title="Распознать чек" disabled>${icons.svg("receipt")}</button></footer>
    <dialog id="scanPhotoDialog" class="choice-dialog" aria-labelledby="scanPhotoTitle"><header><h3 id="scanPhotoTitle">Фото чека</h3>${iconButton('scanPhotoClose','close','Вернуться к позициям')}</header></dialog>
    <dialog id="scanTextDialog" class="choice-dialog task-dialog"><header><h3>Распознанный текст</h3>${iconButton('scanTextClose','close','Закрыть текст')}</header><div class="segmented" id="scanTextModes"><button type="button" class="segmented-btn active" data-text-mode="edited">Уточнённый</button><button type="button" class="segmented-btn" data-text-mode="original">Исходный</button></div><textarea id="scanText" rows="15" maxlength="80000" aria-label="Распознанный текст"></textarea><button id="scanReparse" class="btn btn-primary btn-icon" type="button" aria-label="Разобрать исправленный текст" title="Разобрать исправленный текст">${icons.svg("refresh")}</button></dialog>`;
  document.body.append(dialog);
  const scrollNav = node('scanScrollNav');
  const scrollTopButton = node('scanScrollTop');
  const scrollBottomButton = node('scanScrollBottom');
  function updateScrollNav() {
    const limit = dialog.scrollHeight - dialog.clientHeight;
    scrollNav.hidden = !dialog.open || dialog.dataset.stage !== 'review' || limit <= 1;
    scrollTopButton.disabled = dialog.scrollTop <= 1;
    scrollBottomButton.disabled = dialog.scrollTop >= limit - 1;
  }
  function jumpToReceiptEnd(atBottom) {
    node(atBottom ? 'scanConfirmed' : 'receiptScanTitle').focus({preventScroll:true});
    dialog.scrollTo({top: atBottom ? dialog.scrollHeight : 0, behavior:'instant'});
    updateScrollNav();
  }
  scrollTopButton.onclick = () => jumpToReceiptEnd(false);
  scrollBottomButton.onclick = () => jumpToReceiptEnd(true);
  dialog.addEventListener('scroll', updateScrollNav, {passive:true});
  const reviewResize = new ResizeObserver(updateScrollNav);
  [dialog, node('scanWorkspace'), node('scanStatus')].forEach(element => reviewResize.observe(element));
  const storePicker=window.App.getRuntimeModule('operation-store-picker').bind(node('scanShop').closest('.field'),'scan');
  let engineChosen=false, engineCheck=0, engineAvailable=null;
  const updatePrivacy=()=>{node('scanPrivacy').textContent=node('scanEngine').value==='rapid'?'Фото отправится на сервер ФинАсиста для распознавания. Внешние сервисы не используются; фото не сохраняется этим режимом.':(engineAvailable===false?'RapidOCR недоступен. ':'')+'Фото обрабатывается на устройстве.';};
  node('scanEngine').onchange=()=>{engineChosen=true;updatePrivacy();};
  async function refreshEngines(){
    const check=++engineCheck;
    let available=false;
    try{
      const result=await core.requestJson('/api/v1/receipt-ocr/status',{headers:core.authHeaders()});
      available=result.available===true;
    }catch{/* Tesseract remains usable when the server check fails. */}
    if(check!==engineCheck||busy)return;
    engineAvailable=available;
    const option=node('scanEngine').querySelector('[value=rapid]');option.disabled=!available;
    option.textContent=available?'RapidOCR · на сервере':'RapidOCR · недоступен';
    if(!available)node('scanEngine').value='local';
    else if(!engineChosen)node('scanEngine').value='rapid';
    updatePrivacy();
  }
  let source=null, points=[], draft=null, job=null, generation=0, transferred=false, originalText='', busy=false, pendingPaste=null;
  let originalTextMode=false, editedText='', storedImage=null;
  const reviewText=()=>originalTextMode?editedText:node('scanText').value;
  let context='create', createRecovery=null, applied=false, openGeneration=0;
  let standalone=false, saving=false, attempt=null;
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
    if (draft?.rows && !Object.hasOwn(draft, 'printed_discount') && node('scanText').value) {
      const original = parser.parse(node('scanText').value);
      if (Object.hasOwn(original, 'printed_discount')) draft.printed_discount = original.printed_discount;
    }
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
    node('scanPrintedDiscount').value=decimal(draft.printed_discount);
    node('scanConfirmed').checked=false;renderRows();validate();
  }
  function operationReview(mode, previous, keepSavedCodes=false){
    const prefix=mode==='create'?'op':'edit', rows=state[mode+'ReceiptItems']?.filter(r=>r.name);
    if(!rows?.length)return previous;
    return {...(previous && Object.hasOwn(previous, 'printed_discount') ? {printed_discount:previous.printed_discount} : {}),
      date:node(prefix+'Date').value,shop:rows[0].shop_name||'',total:inputMoney(node(prefix+'Amount').value),currency:node(prefix+'Currency').value,rows:rows.map((r,index)=>{
      const money=window.App.receiptPricing.savedAmounts(r), price=Number(r.regular_unit_price||r.unit_price);
      const old=previous?.rows?.[index];
      const sameLine=old?.name===r.name;
      const codes=keepSavedCodes&&!r.code_entries?.length&&sameLine?old.code_entries:r.code_entries;
      return {...r,code_errors:[],code_entries:codes||[],catalog:r.product_id||r.template_id?{...r}:null,category_touched:true,price:Math.round(price*100),
        printed_quantity:sameLine ? old.printed_quantity ?? Number(r.quantity) : Number(r.quantity),
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
      delete row.merged_rows;delete row.source;delete row.code_match_result;delete row.site_selection;delete row.site_preview;
      if(row.catalog){delete row.catalog.site_selection;delete row.catalog.site_preview;}
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
  const photoViewer = window.App.receiptPhotoViewer(dialog);
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
    for(const id of ['scanRun','scanUpload','scanRotate','scanReset','scanEngine'])node(id).disabled=value || (!['scanUpload','scanEngine'].includes(id)&&!source);
    node('scanCancel').hidden=!value;
    for(const id of ['scanBack','scanAddRow','scanShowText','scanConfirmed'])node(id).disabled=value;
    node('scanRetry').hidden=value||!source;
    node('scanRetryCancel').hidden=!value;
    dialog.querySelectorAll('[data-corner]').forEach(b=>b.disabled=value);
  }
  function invalidateReview(){photoViewer.close();photoViewer.reset();storedImage=null;dialog.dataset.stage=source?'crop':'upload';node('scanStep').textContent='Границы чека';draft=null;node('scanReview').hidden=true;node('scanRetryStatus').textContent='';node('scanConfirmed').checked=false;transferred=false;}
  function cancel(){
    if(busy&&draft)node('scanRetryStatus').textContent='Повтор отменён.';
    generation++;job?.cancel();job=null;setBusy(false);status('Распознавание отменено');
  }
  function cleanup(){storePicker.close();originalTextMode=false;editedText='';node('scanText').readOnly=false;node('scanReparse').hidden=false;node('scanTextModes').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.textMode==='edited'));dialog.classList.remove('scan-drag-over');pendingPaste=null;node('scanPasteReplace').hidden=true;cancel();node('scanTextDialog').close();source=null;canvas.width=canvas.height=1;canvas.hidden=false;node('scanNoPhoto').hidden=true;node('scanBack').hidden=false;node('scanFile').value='';node('scanText').value='';node('scanRows').replaceChildren();originalText='';invalidateReview();node('scanWorkspace').hidden=true;setBusy(false);status('');}
  async function open(mode='create', options={}){
    if(mode==='edit'&&state.editDebtMovement)return;
    standalone=mode==='create'&&Boolean(options.fromList);
    const next=mode==='create'?'create':String(state.editOperationId), token=++openGeneration;
    try{
      if(standalone){
        const owner=state.currentUserId;
        const saved = attempt || await window.App.receiptSubmissions.pending(owner).catch(() => null);
        if (token !== openGeneration || owner !== state.currentUserId) return;
        if (saved && saved.owner === owner) {
          attempt = saved;
          cleanup();
          context = 'create';
          applied = false;
          showSubmission('У предыдущей попытки нет подтверждения. Можно безопасно повторить сохранение.');
          if(!dialog.open)dialog.showModal();
          node('scanSubmitRetry').focus();
          return;
        }
      }
      refreshEngines();
      hideSubmission();
      node('scanReplaceOperation').hidden=true;
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
      if(token!==openGeneration||(!standalone&&node(mode==='create'?'createModal':'editModal').classList.contains('hidden')))return;
      if(applied&&!standalone)syncOperation();
      transferred=false;if(draft)validate();
      if(!dialog.open)dialog.showModal();
      (draft?node('scanDate'):node('scanDropzone')).focus();
      const categories=standalone&&!state.categories?.length
        ? window.App.getRuntimeModule('category-actions').loadCategoryCatalog().catch(()=>{}) : Promise.resolve();
      categories.then(()=>catalog().load()).then(()=>{if(token!==openGeneration||!dialog.open)return;if(draft)refreshCatalog();storePicker.refresh();}).catch(()=>{});
    }catch(error){if(token!==openGeneration)return;if(mode==='edit')context='';core.notify(error.message||'Не удалось открыть чек',{type:'error'});}
  }
  node('scanClose').onclick=()=>{if(!saving)dialog.close();};
  dialog.addEventListener('cancel',e=>{if(saving)e.preventDefault();});
  dialog.addEventListener('close', () => {
    if (dialog.open) return;
    photoViewer.close();photoViewer.reset();storePicker.close();if(busy)cancel();node('scanTextDialog').close();closeCatalogLists();closeCategoryPickers();refreshEntry();
    if(standalone&&attempt&&context==='create')cleanup();
    hideSubmission();
    standalone=false;
  });
  dialog.addEventListener('click',e=>{const r=dialog.getBoundingClientRect();if(!saving&&e.target===dialog&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dialog.close();});
  // Installed before the global choice listener: Escape in a nested choice belongs to it.
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||!dialog.open||node('appChoiceDialog')?.open)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(saving)return;
    if(node('scanPhotoDialog').open){node('scanPhotoDialog').close();return;}
    if(!node('createCategoryModal').classList.contains('hidden')&&dialog.contains(node('createCategoryModal'))){window.App.categoryUi.closeCreateCategoryModal();return;}
    if(dialog.querySelector('.scan-category-picker:not(.hidden)')){closeCategoryPickers();return;}
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
    if(!file||!node('scanSubmission').hidden)return;
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
  node('scanRetryCancel').onclick=()=>{cancel();node('scanRetry').focus();};
  node('scanRun').onclick=()=>runRecognition(false);
  node('scanRetry').onclick=()=>runRecognition(true);
  async function runRecognition(retry){
    if(!source||busy||(retry&&draft?.rows.length!==0))return;
    if(!retry)invalidateReview();
    const report=retry?message=>{node('scanRetryStatus').textContent=message;}:status;
    const token=++generation;
    setBusy(true);report('Подготовка фото…');
    let prepared;
    try{
      await new Promise(resolve=>requestAnimationFrame(resolve));
      if(token!==generation)return;
      const remote=node('scanEngine').value==='rapid';
      prepared=window.App.receiptScanImage.prepare(source,points,{enhance:!remote||retry,compact:retry&&!remote});
      const started=performance.now();
      job=window.App.receiptScanEngine[remote?'recognizeRemote':'recognize'](prepared,p=>{if(token===generation)report(remote?'Распознавание на сервере… Это может занять до 90 секунд.':p===null?'Загрузка движка… В первый раз потребуется несколько мегабайт.':`Распознавание: ${p}%`);});
      const result=await job.promise;if(token!==generation||!result)return;
      if(!retry||result.text.trim()){
        if(!retry||node('scanText').value===originalText)node('scanText').value=result.text;
        originalText=result.text;
        showDraft(parser.parse(originalText),retry);
      }
      // Keep the higher-resolution review photo when retrying at a different OCR scale.
      if(!retry){canvas.width=prepared.width;canvas.height=prepared.height;canvas.getContext('2d').drawImage(prepared,0,0);}
      if(retry)report(draft.rows.length?'':'Позиции снова не найдены. Попробуйте изменить границы фото или выбрать другой способ распознавания.');
      status(`Черновик за ${((performance.now()-started)/1000).toFixed(1)} с. Проверьте каждую строку: OCR может ошибаться.`);
    }catch(e){if(token===generation)report(e.message||'Не удалось распознать. Повторите попытку или введите чек вручную.');}
    finally{if(prepared){prepared.width=prepared.height=1;}if(token===generation){job=null;setBusy(false);}}
  }
  const decimal=cents=>cents==null?'':(cents/100).toFixed(2);
  const codeLookupKey=row=>JSON.stringify([node('scanShop').value,(row.code_entries||[]).map(e=>[e.code,e.manual_kind?e.kind:'auto'])]);
  function showDraft(value,keepFilledMeta=false){
    if (keepFilledMeta && draft?.printed_discount != null) value.printed_discount = draft.printed_discount;
    draft=value;
    for(const row of draft.rows){if(row.total==null)parser.recalculateRow(row,'price');}
    draft.rows.forEach((row,index)=>row.scan_order=index);
    draft.rows=parser.mergeDuplicates(draft.rows,window.App.receiptCodes.validBarcode);
    dialog.dataset.stage='review';node('scanStep').textContent='Проверьте поля по фото';
    for(const [id,field] of [['scanDate',draft.date],['scanShop',draft.shop],['scanTotal',decimal(draft.total)]]){
      if(!keepFilledMeta||!node(id).value)node(id).value=field;
    }
    node('scanPrintedDiscount').value=decimal(draft.printed_discount);
    node('scanDiscountReview').querySelector('details').open=false;
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
  function closeCategoryPickers(){dialog.querySelectorAll('.scan-category').forEach(host=>host.closeCategoryPicker?.());}
  function closeCatalogLists(){
    dialog.querySelectorAll('.scan-catalog-list').forEach(n=>setCatalogOpen(n,false));
  }
  function refreshCatalog(){
    node('scanRows').querySelectorAll('.scan-row').forEach(el=>{el.refreshCategory?.();el.refreshBrand?.();el.refreshCatalog?.();el.refreshSearch?.();});
  }
  const expandedRows = new WeakMap(), rowsWithIssues = new WeakSet();
  let lastVisitedIssue = null;
  const moneyFormat = new Intl.NumberFormat('ru-RU', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  function updateRowSummary(el, row, index, currency, reason, gross) {
    const summary = el.querySelector('.scan-row-summary');
    summary.querySelector('strong').textContent = row.name.trim() || `Позиция ${index + 1}`;
    summary.querySelector('b').textContent = row.total == null ? '—' : `${moneyFormat.format(row.total / 100)} ${currency}`;
    const quantity = Number.isFinite(row.quantity) ? window.App.measurements.formatQuantity(row.quantity) : '—';
    const price = row.price == null ? '—' : moneyFormat.format(row.price / 100);
    const unit = window.App.measurements.units[row.sale_unit];
    const discount = row.discount > 0 ? ` · скидка ${moneyFormat.format(row.discount / 100)} ${currency}` : '';
    const weighted = window.App.measurements.weightDiscountSummary(row, row.price / 100, gross / 100, row.discount / 100, currency);
    summary.querySelector('.scan-row-quantity').textContent = weighted || `${quantity}${unit ? ' ' + unit : ''} × ${price}${discount}`;
    summary.querySelector('.scan-row-warning').textContent = reason ? 'Требует проверки' : '';
    if (reason && !rowsWithIssues.has(row)) el.open = true;
    if (reason) rowsWithIssues.add(row); else rowsWithIssues.delete(row);
    el.classList.toggle('has-error', Boolean(reason));
  }
  node('scanNextIssue').onclick = () => {
    const indexes = draft.rows.map((row, index) => rowsWithIssues.has(row) ? index : -1).filter(index => index >= 0);
    if (!indexes.length) {
      node('scanDiscountReview').querySelector('details').open = true;
      node('scanPrintedDiscount').focus({preventScroll:true});
      node('scanPrintedDiscount').scrollIntoView({block:'center'});
      return;
    }
    const index = indexes.find(i => i > draft.rows.indexOf(lastVisitedIssue)) ?? indexes[0];
    lastVisitedIssue = draft.rows[index];
    const el = node('scanRows').children[index];
    el.open = true;
    const input = el.querySelector('input[aria-invalid=true]') || el.querySelector('[data-scan-field=price]');
    input.focus({preventScroll:true});
    input.scrollIntoView({block:'center'});
  };
  function renderRows(){
    closeCategoryPickers();
    for (const el of node('scanRows').children) expandedRows.set(el.reviewRow, el.open);
    node('scanRows').replaceChildren();
    draft.rows.forEach((row,index)=>{
      const el=document.createElement('details');el.className='scan-row';
      el.innerHTML=`<div class="scan-name"><label class="field"><span>Товар ${index+1}</span><input data-scan-field="name" maxlength="160" placeholder="Найти или ввести товар" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="scanCatalog${index}" required></label><div id="scanCatalog${index}" class="scan-catalog-list receipt-name-picker app-popover hidden" role="listbox" hidden></div></div><div class="scan-row-actions">${iconButton('', 'trash', 'Удалить позицию '+(index+1))}</div><div class="scan-match"></div><div class="scan-codes-host"></div><div class="field scan-category"><span>Категория</span><select data-scan-category aria-label="Категория позиции"></select></div><label class="field scan-brand"><span>Бренд</span><select data-scan-brand aria-label="Бренд товара"></select></label><div class="scan-sale-units" role="group" aria-label="Единица цены и количества"></div><div class="scan-catalog-reference" role="status" hidden></div><div class="scan-row-numbers">${[['price','Цена за ед.'],['quantity','Кол-во'],['discount','Скидка на всю позицию'],['total','Оплачено']].map(([field,label])=>`<label class="field"><span>${label}</span><input data-scan-field="${field}" inputmode="decimal" aria-describedby="scanMathHint" required></label>`).join('')}</div><p class="scan-row-calculation muted-small" hidden></p><p class="scan-row-error scan-error" id="scanRowError${index}" role="status" hidden></p><label class="field scan-discount-type"><span>Тип скидки</span><select data-scan-field="discount_type"><option value="promo">Акция</option><option value="loyalty_points">Баллы</option><option value="coupon">Купон</option></select></label>`;
      const fields = document.createElement('div');
      fields.className = 'scan-row-fields';
      fields.append(...el.children);
      const heading = document.createElement('summary');
      heading.className = 'scan-row-summary';
      heading.innerHTML = '<strong></strong><b></b><span class="scan-row-quantity"></span><span class="scan-row-warning"></span>';
      el.append(heading, fields);
      fields.querySelector('.scan-row-actions').after(fields.querySelector('.scan-row-numbers'),
        fields.querySelector('.scan-row-calculation'), fields.querySelector('.scan-row-error'));
      el.reviewRow = row;
      el.open = expandedRows.get(row) || false;
      el.ontoggle = () => { if (el.isConnected) expandedRows.set(row, el.open); };
      const name=el.querySelector('[data-scan-field=name]'), list=el.querySelector('.scan-catalog-list'), match=el.querySelector('.scan-match');
      name.value=row.name;name.title=row.source||'';
      el.querySelectorAll('[data-scan-field]').forEach(input=>input.setAttribute('aria-describedby',[input.getAttribute('aria-describedby'),`scanRowError${index}`].filter(Boolean).join(' ')));
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
          const first = node('scanRows').children[draft.rows.indexOf(originals[0])];
          first.querySelector('summary').focus({preventScroll:true});closeCatalogLists();
        };
        split.onclick=()=>{if(parser.mergedMoneyChanged(row)){confirmation.hidden=false;accept.focus();}else restore();};
        accept.onclick=restore;cancel.onclick=()=>{confirmation.hidden=true;split.focus();};
        confirmation.append(hint,accept,cancel);el.querySelector('.scan-row-actions').prepend(split);fields.append(confirmation);
      }
      el.querySelector('[data-scan-field=price]').title='Цена за единицу до скидки';
      const category=el.querySelector('[data-scan-category]');
      category.add(new Option('Без категории', ''));
      (state.categories||[]).filter(c=>c.kind==='expense').sort((a,b)=>a.name.localeCompare(b.name,'ru')).forEach(c=>category.add(core.createCategoryOption(c)));
      let categoryPicker;
      const refreshCategory=()=>{
        const choice=categoryChoice(row);category.value=String(choice.id||'');
        category.previousElementSibling.textContent=choice.reason?'Категория · предложена':'Категория';
        category.title=choice.reason||'';categoryPicker?.sync();
      };
      el.refreshCategory=refreshCategory;
      refreshCategory();
      category.onchange=()=>{row.category_id=Number(category.value)||null;row.category_touched=true;refreshCategory();node('scanConfirmed').checked=false;validate();};
      categoryPicker=window.App.scanCategoryPicker.mount(el.querySelector('.scan-category'),{select:category,ownerDialog:dialog,
        onCreated:created=>{category.add(core.createCategoryOption(created));category.value=String(created.id);category.dispatchEvent(new Event('change',{bubbles:true}));}});
      categoryPicker.sync();
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
          row.site_selection=null;row.variant_id=null;row.variant_snapshot=null;row.measurement_touched=true;row.measurement_user_edited=true;row.catalog_size_from_name=false;
          refreshUnits();node('scanConfirmed').checked=false;validate();
        });return input;
      });
      const measurementEditor=window.App.measurements.mount(unitHost,measurementControls,{unitDataset:'scanUnit'});
      function refreshReference(){
        const host=el.querySelector('.scan-catalog-reference');host.replaceChildren();
        const reference=row.catalog?.catalog_price;
        if(reference&&Number(reference.amount)>0){
          const heading=document.createElement('span');heading.textContent='Цена в каталоге';
          const value=document.createElement('strong');value.textContent=Number(reference.amount).toLocaleString('ru-RU',{minimumFractionDigits:2,maximumFractionDigits:2})+(reference.currency?' '+reference.currency:'');
          const date=document.createElement('small');date.textContent=[node('scanShop').value,reference.recorded_at?.split('-').reverse().join('.')].filter(Boolean).join(' · ');
          host.title='Последняя сохранённая цена выбранного магазина. Подставляется только по кнопке.';
          const apply=document.createElement('button');apply.type='button';
          apply.className='btn btn-secondary scan-apply-catalog-price';apply.textContent='Подтянуть цену';
          apply.dataset.catalogCurrency=reference.currency||'';
          apply.onclick=()=>{
            if(reference.currency&&reference.currency!==node('scanCurrency').value)return;
            const price=inputMoney(String(reference.amount));if(!Number.isSafeInteger(price)||price<=0)return;
            row.price=price;delete row.discount_basis;
            const priceInput=el.querySelector('[data-scan-field=price]');priceInput.value=decimal(price);
            // Missing quantity must not erase the paid amount read from the receipt.
            if(Number.isFinite(row.quantity)&&row.quantity>0){
              for(const field of parser.recalculateRow(row,'price')){
                el.querySelector(`[data-scan-field=${field}]`).value=decimal(row[field]);
              }
            }
            node('scanConfirmed').checked=false;validate();priceInput.focus({preventScroll:true});
          };
          host.append(heading,value,apply,date);
        }
        if(row.catalog&&row.catalog_size_from_name){const hint=document.createElement('small');hint.textContent='Размер упаковки подставлен из названия товара в каталоге';host.append(hint);}
        if(row.site_measurement_before&&!row.measurement_user_edited){const hint=document.createElement('small');hint.textContent='Фасовка подставлена с сайта выбранного магазина. Сохранится вместе с чеком.';host.append(hint);}
        host.hidden=!host.childElementCount;
      }
      function fillCatalogMeasurement(){
        if(!row.measurement_user_edited){
          row.catalog_size_from_name=false;
          Object.assign(row,parser.catalogMeasurement(row.catalog));
          row.variant_id=row.catalog.variant_id||null;row.variant_snapshot=row.catalog.variant_snapshot||null;
        }
        if(row.measurement_user_edited||row.catalog_size_from_name){
          row.catalog_measurement_touched=true;row.catalog_edit_variant_id=row.catalog.variant_id||null;
          row.variant_id=null;row.variant_snapshot=null;
        }
      }
      function refreshUnits(){
        measurementControls.forEach((input,i)=>{input.value=row[window.App.measurements.fields[i]]??'';});
        measurementEditor.refresh();refreshReference();
        for(const field of ['price','quantity']){
          const input=el.querySelector(`[data-scan-field=${field}]`);
          input.previousElementSibling.textContent=field==='price'?window.App.measurements.priceLabel(row):window.App.measurements.quantityLabel(row);
        }
      }
      function unlink(){row.catalog_name_touched=false;row.catalog_measurement_touched=false;row.catalog_edit_variant_id=null;el.querySelector('.scan-codes-host').invalidateSite?.();row.site_selection=null;row.site_name='';delete row.catalog;row.variant_id=null;row.variant_snapshot=null;row.code_match_label='';refreshCategory();refreshBrand();if(!row.measurement_user_edited)Object.assign(row,window.App.measurements.snapshot(),{catalog_size_from_name:false,measurement_touched:false});refreshUnits();}
      refreshUnits();
      let options=[],active=-1;
      function choose(item){
        row.catalog_new=false;unlink();
        row.catalog=catalog().identity(item,node('scanShop').value);
        row.name=row.catalog.name;name.value=row.name;refreshCategory();refreshBrand();
        fillCatalogMeasurement();
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
        if(catalogNotice()&&list.querySelector('button')){const notice=document.createElement('span');notice.className='muted-small receipt-picker-empty';notice.textContent=catalogNotice();list.querySelector('.receipt-product-options').prepend(notice);}
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
        const previousQuantity=row.quantity;
        if (field === 'name' || field === 'discount_type') row[field] = e.target.value;
        else if (field === 'quantity') row.quantity = inputNumber(e.target.value,true);
        else row[field] = field === 'discount' ? inputDiscount(e.target.value) : inputMoney(e.target.value);
        if(field==='name'){row.name_touched=true;row.catalog_new=false;if(row.catalog){row.catalog_name_touched=true;row.site_selection=null;closeCatalogLists();}else unlink();el.refreshCatalog();search();}
        for(const changed of parser.recalculateRow(row,field,previousQuantity)){
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
          onSiteSelect:found=>{
            if(found.clear_measurement){
              if(row.site_measurement_before&&!row.measurement_user_edited)Object.assign(row,row.site_measurement_before);
              delete row.site_measurement_before;refreshUnits();return;
            }
            if(found.use_measurement){
              const size=found.measurement,catalogSize=parser.catalogMeasurement(row.catalog||{});
              if(!size||found.reference_only||row.measurement_user_edited||row.package_quantity!=null||catalogSize.package_quantity!=null
                ||(row.sale_unit&&!['piece','pack'].includes(row.sale_unit))||!['g','kg','ml','l','piece'].includes(size.package_unit)
                ||!Number.isFinite(Number(size.package_quantity))||Number(size.package_quantity)<=0)return false;
              const keys=[...window.App.measurements.fields,'variant_id','variant_snapshot','measurement_touched','catalog_measurement_touched','catalog_edit_variant_id'];
              row.site_measurement_before=Object.fromEntries(keys.map(key=>[key,row[key]??null]));
              Object.assign(row,size,{sale_unit:row.sale_unit||'piece',measurement_touched:true});
              if(row.catalog){row.catalog_measurement_touched=true;row.catalog_edit_variant_id=row.catalog.variant_id||null;}
              row.variant_id=null;row.variant_snapshot=null;refreshUnits();return true;
            }
            if(found.use_name){row.name=found.name.slice(0,160);row.name_touched=true;if(row.catalog)row.catalog_name_touched=true;name.value=row.name;refreshCategory();el.refreshCatalog();}
          },
          onChange:()=>{node('scanConfirmed').checked=false;validate();},
          onSelect:found=>{
            const manualSize=row.measurement_user_edited?window.App.measurements.snapshot(row):null;
            row.catalog_new=false;window.App.receiptCodes.apply(row,found);row.catalog={...found};name.value=row.name;
            row.catalog_name_touched=false;row.catalog_measurement_touched=false;row.catalog_edit_variant_id=null;
            if(manualSize)Object.assign(row,manualSize);fillCatalogMeasurement();
            refreshCategory();refreshBrand();refreshUnits();el.refreshCatalog();closeCatalogLists();node('scanConfirmed').checked=false;validate();
          },
        });
      };el.refreshCodes();
    });
  }
  dialog.addEventListener('pointerdown',e=>{if(!e.target.closest('.scan-name'))closeCatalogLists();});
  function readMeta(){if(!draft)return;draft.date=node('scanDate').value;draft.shop=node('scanShop').value;draft.total=inputMoney(node('scanTotal').value);}
  function showDiscountTotals(totals, currency, mismatch, invalid) {
    const expected = draft.printed_discount;
    const panel = node('scanDiscountReview');
    panel.hidden = !draft.rows.length || !(Object.hasOwn(draft, 'printed_discount') ||
      draft.rows.some(row => row.discount > 0 || row.discount_type && row.discount == null) ||
      draft.total > 0 && totals.gross > draft.total);
    if (panel.hidden) return;
    const amount = cents => cents == null ? '—' : moneyFormat.format(cents / 100) + ' ' + currency;
    node('scanGrossSum').textContent = amount(totals.gross);
    node('scanDiscountSum').textContent = amount(totals.discount);
    node('scanPaidSum').textContent = amount(totals.paid);
    const status = node('scanDiscountStatus');
    status.classList.toggle('scan-error', invalid || mismatch);
    let message = 'Сверить со строкой «Итого скидка»';
    if (invalid) message = 'Проверьте введённую сумму скидки';
    else if (mismatch) message = `В чеке ${amount(expected)} · расхождение ${amount(Math.abs(totals.discount - expected))}`;
    else if (expected != null) message = (totals.discount == null ? 'Скидка в чеке · ' : 'Скидка совпадает с чеком · ') + amount(expected);
    if (status.textContent !== message) status.textContent = message;
    const suggestion = !invalid && totals.discount === null ? parser.missingLineDiscount(draft) : null;
    const fill = node('scanFillDiscount');
    fill.hidden = !suggestion;
    if (suggestion) {
      const name = draft.rows[suggestion.index].name || `Позиция ${suggestion.index + 1}`;
      fill.textContent = `Подставить скидку ${amount(suggestion.amount)} для «${name}»`;
    }
  }
  node('scanFillDiscount').onclick = () => {
    const suggestion = parser.missingLineDiscount(draft);
    if (!suggestion) return;
    const row = node('scanRows').children[suggestion.index];
    const input = row.querySelector('[data-scan-field=discount]');
    row.open = true;
    input.value = decimal(suggestion.amount);
    input.dispatchEvent(new Event('input', {bubbles:true}));
    input.focus();
  };
  function validate(){
    if(!draft)return;readMeta();
    const totals=parser.receiptTotals(draft.rows), issues=parser.validationIssues(draft, totals);
    const errors=issues.map(issue=>issue.message),globalErrors=issues.filter(issue=>issue.rowIndex===null && issue.field!=='printed_discount').map(issue=>issue.message);
    const currency=node('scanCurrency').value;
    const printedInput=node('scanPrintedDiscount');
    const invalid=Boolean(printedInput.value.trim() && inputDiscount(printedInput.value) == null);
    printedInput.setAttribute('aria-invalid', String(invalid));
    if(invalid) errors.push('Проверьте введённую сумму скидки');
    const discountMismatch=issues.some(issue=>issue.field==='printed_discount');
    showDiscountTotals(totals, currency, discountMismatch, invalid);
    const codeErrors=draft.rows.map(row=>window.App.receiptCodes.validationError(window.App.receiptCodes.payload(row),draft.shop));
    const rowIssues = new Map(issues.filter(issue => issue.rowIndex !== null).map(issue => [issue.rowIndex, issue]));
    codeErrors.forEach((reason,index)=>{if(reason)errors.push(`Позиция ${index+1}: ${reason}`);});
    node('scanRows').querySelectorAll('.scan-row').forEach((el,index)=>{
      const issue = rowIssues.get(index);
      const messages = [issue?.message, codeErrors[index]].filter(Boolean), hint=el.querySelector('.scan-row-error');
      for (const input of el.querySelectorAll('input[data-scan-field]')) {
        input.setAttribute('aria-invalid', String(Boolean(issue?.fields?.includes(input.dataset.scanField))));
      }
      hint.textContent=messages.join(' · ');hint.hidden=!messages.length;
      const row=draft.rows[index],calculation=el.querySelector('.scan-row-calculation');
      const gross=parser.rowSubtotal(row);
      updateRowSummary(el, row, index, currency, messages.length, gross);
      const applyPrice=el.querySelector('.scan-apply-catalog-price');
      if(applyPrice){
        applyPrice.disabled=Boolean(applyPrice.dataset.catalogCurrency&&applyPrice.dataset.catalogCurrency!==node('scanCurrency').value);
        applyPrice.title=applyPrice.disabled?'Валюта цены отличается от валюты чека':'Подставить цену и пересчитать оплату по количеству и скидке';
      }
      const show=gross!==null&&Number.isInteger(row.discount)&&row.discount>0;
      const weighed=window.App.measurements.isWeightUnit(row.sale_unit);
      el.querySelector('[data-scan-field=price]').previousElementSibling.textContent =
        window.App.measurements.priceLabel(row) + (row.discount > 0 ? ' до скидки' : '');
      el.querySelector('[data-scan-field=discount]').previousElementSibling.textContent = weighed ? 'Скидка за весь вес' : 'Скидка на всю позицию';
      calculation.hidden=!show;
      if (show) {
        const net=gross-row.discount;
        const unit=window.App.measurements.units[row.sale_unit];
        const showPaidRate=unit && (row.quantity!==1 || weighed) && net>0;
        const unitPrice=showPaidRate
          ? ` · после скидки ≈ ${moneyFormat.format(window.App.receiptPricing.paidUnitPrice(net/100, row.quantity))} ${currency}/${unit}` : '';
        calculation.textContent=`${moneyFormat.format(gross/100)} − ${moneyFormat.format(row.discount/100)} = ${moneyFormat.format(net/100)} ${currency}${unitPrice}`;
      }
      el.querySelector('.scan-codes-host').refreshCodeState?.();
    });
    const summary=node('scanArithmetic');
    const anchor = globalErrors.length ? dialog.querySelector('.scan-meta') : node('scanRows');
    if (anchor.nextElementSibling !== summary) anchor.after(summary);
    const count = draft.rows.filter(row => rowsWithIssues.has(row)).length;
    const next = node('scanNextIssue');
    next.hidden = !draft.rows.length || (!count && !discountMismatch && !invalid);
    next.textContent = count ? `К ошибке · ${count}` : 'К сверке скидки';
    next.title = count ? 'Перейти к следующей позиции с ошибкой' : 'Сверить общую скидку с чеком';
    dialog.classList.toggle('has-positions', draft.rows.length > 0);
    node('scanEmptyRows').hidden=draft.rows.length>0;
    summary.textContent=globalErrors.length?globalErrors.join(' · '):errors.length?'':'Суммы сходятся. Сверьте названия и цифры с фото.';
    summary.hidden=!summary.textContent||(!draft.rows.length&&!draft.unsupported);summary.classList.toggle('scan-error',!!globalErrors.length);
    const submit=node('scanTransfer');
    const amount=draft.total>0?' · '+moneyFormat.format(draft.total/100)+' '+currency:'';
    submit.querySelector('span').textContent=standalone?'Записать расход'+amount:'Перенести в черновик';
    submit.disabled=errors.length>0||!node('scanConfirmed').checked||transferred||saving;
    return errors;
  }

  function metaChanged(id){
    node('scanConfirmed').checked=false;
    if(id==='scanShop'&&draft?.shop!==node('scanShop').value){
      node('scanRows').querySelectorAll('.scan-row').forEach(el=>{el.unlinkCatalog();el.refreshCodes?.();});refreshCatalog();
    }
    validate();
  }
  for(const id of ['scanDate','scanShop','scanTotal','scanCurrency'])node(id).addEventListener('input',()=>metaChanged(id));
  node('scanPrintedDiscount').addEventListener('input', e => {
    const value=e.target.value.trim(), cents=inputDiscount(value);
    if (!value || cents!=null) draft.printed_discount=value ? cents : null;
    metaChanged('scanPrintedDiscount');
  });
  node('scanShop').addEventListener('change',()=>metaChanged('scanShop'));
  function commitCalculation(input) {
    const quantity=input.dataset.scanField==='quantity';
    const discount=input.dataset.scanField==='discount' || input.id==='scanPrintedDiscount';
    if(input.id==='scanPrintedDiscount' && !input.value.trim())return;
    const result=inputNumber(discount ? discountText(input.value) : input.value,quantity);
    if(result==null){input.setAttribute('aria-invalid','true');return;}
    input.removeAttribute('aria-invalid');
    input.value=quantity?String(result):result.toFixed(2);
    // Input already recalculated dependent fields; formatting alone must not recalculate again.
    validate();
  }
  const numericField=input=>input.matches?.('#scanTotal, #scanPrintedDiscount, [data-scan-field=price], [data-scan-field=quantity], [data-scan-field=discount], [data-scan-field=total]');
  node('scanReview').addEventListener('focusout',e=>{if(numericField(e.target))commitCalculation(e.target);});
  node('scanReview').addEventListener('keydown',e=>{if(e.key==='Enter'&&numericField(e.target)){e.preventDefault();commitCalculation(e.target);}});
  node('scanTotal').addEventListener('input', e => {
    e.target.setAttribute('aria-invalid', String(!(inputMoney(e.target.value) > 0)));
  });
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
  function reviewedItems(modal, mode) {
    return draft.rows.map(row => {
      const category = categoryChoice(row);
      const discounted = row.discount > 0;
      return modal.createReceiptDraft({
        ...row.catalog,
        catalog_editable: Boolean(row.catalog),
        catalog_name_touched: Boolean(row.catalog_name_touched),
        catalog_measurement_touched: Boolean(row.catalog_measurement_touched),
        catalog_edit_variant_id: row.catalog_edit_variant_id || null,
        ...(row.brand_touched ? {brand_id: row.brand_id, brand_touched: true} : {}),
        category_id: category.id,
        category_touched: Boolean(row.category_touched || category.reason),
        name: row.name, quantity: row.quantity, shop_name: draft.shop,
        ...window.App.measurements.snapshot(row),
        variant_id: row.variant_id || null, variant_snapshot: row.variant_snapshot || null,
        site_selection: row.site_selection || null, site_name: row.site_name || '', site_preview: row.site_preview || null,
        code_entries: row.code_entries || [], code_match_label: row.code_match_label || '', measurement_touched: true,
        unit_price: row.price / 100, is_discounted: discounted,
        regular_unit_price: discounted ? row.price / 100 : null,
        discount_mode: discounted ? 'amount' : null, discount_value: discounted ? row.discount / 100 : null,
        discount_type: discounted ? row.discount_type || 'promo' : null, note: row.note || null,
      }, mode);
    });
  }

  function showSubmission(message) {
    dialog.classList.add('has-submission');
    node('scanSubmission').hidden = false;
    node('scanSubmissionReceipt').textContent = attempt.label;
    node('scanSubmissionMessage').textContent = message;
    node('scanSubmitRetry').hidden = saving;
    node('scanClose').disabled = saving;
  }

  function hideSubmission() {
    dialog.classList.remove('has-submission');
    node('scanSubmission').hidden = true;
    node('scanClose').disabled = false;
  }

  function prepareExpense() {
    const modal = window.App.getRuntimeModule('operation-modal');
    const currency = node('scanCurrency').value;
    const foreign = currency !== (core.getCurrencyConfig?.().code || 'BYN');
    const payload = {
      kind: 'expense', operation_date: draft.date, amount: decimal(draft.total), currency,
      ...(foreign ? {fx_rate_source: 'nbrb', fx_payment_mode: 'valuation'} : {}),
      receipt_items: modal.serializeReceiptItems(reviewedItems(modal, 'create')),
      receipt_scan: scanPayload(),
    };
    return {
      key: crypto.randomUUID(), owner: state.currentUserId, body: JSON.stringify(payload),
      label: [draft.shop, core.formatDateRu(draft.date), moneyFormat.format(draft.total / 100) + ' ' + currency].join(' · '),
    };
  }

  async function restoreRejectedExpense(current, error) {
    if (error.status === 409) {
      cleanup();
      dialog.close();
    } else {
      if (!draft || context !== 'create') {
        cleanup();
        context = 'create';
        const payload = JSON.parse(current.body);
        const scan = payload.receipt_scan;
        scan.review.rows.forEach((row, index) => { row.site_selection = payload.receipt_items[index]?.site_selection; });
        await restore({...scan, currency: payload.currency});
      }
      node('scanConfirmed').checked = false;
      validate();
    }
    const detail = error.detail;
    const message = detail?.type === 'receipt_code_conflict'
      ? `Позиция ${detail.item_index + 1} «${detail.item_name}». ${detail.message}`
      : (typeof detail === 'string' ? detail : error.message);
    core.notify(message, {type: 'error'});
  }

  async function saveExpense() {
    if (!standalone || saving) return;
    const isNew = !attempt;
    if (isNew && (!draft || transferred || validate().length || !node('scanConfirmed').checked)) return;
    saving = true;
    if (isNew) {
      try {
        attempt = prepareExpense();
      } catch (error) {
        saving = false;
        validate();
        core.notify(error.message || 'Не удалось подготовить чек к отправке.', {type: 'error'});
        return;
      }
    }
    const current = attempt;
    const isCurrent = () => attempt === current && state.currentUserId === current.owner;
    showSubmission('Записываем расход…');
    // Persist before the POST so a reload between commit and response can replay exactly the same receipt.
    if (isNew) {
      await window.App.receiptSubmissions.remember(current).catch(() => { current.memoryOnly = true; });
    }
    if (!isCurrent()) return;
    let result, rejection;
    try {
      result = await core.requestJson('/api/v1/operations', {
        method: 'POST', headers: {...core.authHeaders(), 'Idempotency-Key': current.key}, body: current.body,
      });
      if (!result?.id) throw new Error('Сервер не подтвердил номер операции.');
    } catch (error) {
      if (!isCurrent()) return;
      if (![400, 409, 413, 415, 422].includes(error.status)) {
        saving = false;
        const keepTab = current.memoryOnly ? ' Оставьте эту вкладку открытой до подтверждения.' : '';
        showSubmission('Подтверждение от сервера не получено. Повторите сохранение этого чека.' + keepTab);
        node('scanSubmitRetry').focus();
        return;
      }
      rejection = error;
    }
    await window.App.receiptSubmissions.forget(current.key).catch(() => {});
    if (!isCurrent()) return;
    saving = false;
    attempt = null;
    hideSubmission();
    if (rejection) {
      await restoreRejectedExpense(current, rejection);
      return;
    }
    cleanup();
    createRecovery = null;
    pending.create = null;
    applied = false;
    context = 'create';
    dialog.close();
    core.notify('Расход записан', {type: 'success'});
    window.App.getRuntimeModule('operations').refreshAfterCreate(result.category_id).catch(() => {
      core.notify('Расход записан. Не удалось обновить список операций.', {type: 'error'});
    });
  }

  function transfer(replace=false){
    if(!draft||transferred||validate().length||!node('scanConfirmed').checked)return;
    const modal=window.App.getRuntimeModule('operation-modal');
    const mode=context==='create'?'create':'edit', prefix=mode==='create'?'op':'edit';
    if(mode==='create'&&(node('createModal').classList.contains('hidden')||node('opEntryMode').value!=='operation'||state.createFlowMode==='plan'))return;
    if(mode==='edit'&&(String(state.editOperationId)!==context||node('editModal').classList.contains('hidden')))return;
    const formDate=node(prefix+'Date').value, formCurrency=node(prefix+'Currency').value;
    const changesDate=formDate&&formDate!==core.getTodayIso()&&formDate!==draft.date;
    const changesCurrency=formCurrency!==(core.getCurrencyConfig?.().code||'BYN')&&formCurrency!==node('scanCurrency').value;
    if(!replace&&(modal.hasReceiptInput(mode)||node(prefix+'Amount').value||node(prefix+'Kind').value!=='expense'||changesDate||changesCurrency)){
      node('scanReplaceOperation').hidden=false;node('scanReplaceYes').focus();return;
    }
    node('scanReplaceOperation').hidden=true;
    pending[mode]={id:context,value:scanPayload()};
    transferred=true;
    modal.setOperationKind(mode,'expense');
    node(prefix+'Date').value=draft.date;node(prefix+'Date').dispatchEvent(new Event('change',{bubbles:true}));
    node(prefix+'Currency').value=node('scanCurrency').value;node(prefix+'Currency').dispatchEvent(new Event('change',{bubbles:true}));
    state[mode+'ReceiptItems']=reviewedItems(modal,mode);
    if(mode==='create')modal.setCreateOperationMode('receipt');else modal.setEditOperationMode('receipt');
    node(prefix+'Amount').value=decimal(draft.total);node(prefix+'Amount').dispatchEvent(new Event('input',{bubbles:true}));
    modal.renderReceiptSummary(mode);applied=true;dialog.close();
  };
  node('scanReview').onsubmit=e=>{
    e.preventDefault();
    if(standalone)saveExpense();else transfer();
  };
  node('scanSubmitRetry').onclick=()=>saveExpense();
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
    open,
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
      if(context!=='create'){photoViewer.close();photoViewer.reset();if(busy)cancel();storedImage=null;source=null;canvas.width=canvas.height=1;canvas.hidden=true;node('scanNoPhoto').hidden=false;node('scanBack').hidden=true;node('scanRetry').hidden=true;}
    },
    reset(){openGeneration++;attempt=null;saving=false;hideSubmission();if(dialog.open)dialog.close();cleanup();createRecovery=null;pending.create=pending.edit=null;context='create';},
  });
  function refreshEntry(){button.querySelector('span').textContent=pending.create?'Проверить чек':((context==='create'&&(draft||source))||createRecovery)?'Продолжить чек':'Сканировать чек';}
  const sync=()=>{button.hidden=node('opEntryMode').value!=='operation'||state.createFlowMode==='plan';if(!standalone&&node(context==='create'?'createModal':'editModal').classList.contains('hidden')&&dialog.open)dialog.close();};
  new MutationObserver(sync).observe(node('createModal'),{attributes:true,attributeFilter:['class']});
  new MutationObserver(sync).observe(node('editModal'),{attributes:true,attributeFilter:['class']});
  node('createEntryModeSwitch').addEventListener('click',()=>queueMicrotask(sync));
  cleanup();
})();
