(() => {
  const {icons, state} = window.App;
  const parser = window.App.receiptScanParser;
  const inputMoney = value => /^\d{1,7}([.,]\d{1,2})?$/.test(value.trim()) ? Math.round(Number(value.replace(',','.'))*100) : null;
  const node = id => document.getElementById(id);
  const dialog = document.createElement('dialog');
  dialog.id='receiptScanDialog';dialog.className='receipt-scan-dialog';dialog.setAttribute('aria-labelledby','receiptScanTitle');
  const iconButton=(id,icon,label)=>`<button id="${id}" type="button" class="btn btn-secondary btn-icon" aria-label="${label}" title="${label}">${icons.svg(icon)}</button>`;
  dialog.innerHTML=`<header><h3 id="receiptScanTitle">Сканировать чек · пилот</h3>${iconButton('scanClose','close','Закрыть сканирование')}</header>
    <p class="muted-small" id="scanPrivacy">Фото обрабатывается на устройстве. Проверьте результат перед переносом в операцию.</p>
    <div class="scan-toolbar">${iconButton('scanBack','back','Изменить фото и распознать заново')}${iconButton('scanUpload','upload','Загрузить фото чека')}${iconButton('scanRotate','refresh','Повернуть фото')}${iconButton('scanReset','expand','Сбросить углы')}<input id="scanFile" type="file" accept="image/jpeg,image/png,image/webp" hidden><span id="scanStep" class="muted-small">Один чек на фото · JPG, PNG или WebP до 20 МБ</span></div>
    <div id="scanWorkspace" hidden><div class="scan-image-column"><div id="scanImageFrame"><canvas id="scanCanvas"></canvas><svg id="scanOutline" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polygon fill="#79acff18" stroke="#79acff" stroke-width=".5"/></svg>${[0,1,2,3].map((i)=>`<button type="button" class="scan-corner" data-corner="${i}" aria-label="Угол ${i+1} чека">${i+1}</button>`).join('')}</div><p id="scanCropHint" class="muted-small">Перетащите четыре угла к краям чека. Клавиатура: стрелки.</p></div>
    <form id="scanReview" hidden><div class="scan-meta"><label class="field"><span>Дата покупки</span><input id="scanDate" type="date" required></label><label class="field"><span>Магазин</span><input id="scanShop" maxlength="160" required></label><label class="field"><span>Итого по чеку</span><input id="scanTotal" inputmode="decimal" required></label><label class="field"><span>Валюта</span><select id="scanCurrency"><option>BYN</option><option>RUB</option><option>USD</option><option>EUR</option></select></label></div>
    <div class="scan-review-toolbar"><strong>Позиции</strong>${iconButton('scanAddRow','plus','Добавить строку')}${iconButton('scanShowText','receipt','Распознанный текст')}</div><div id="scanRows"></div>
    <p id="scanArithmetic" role="status"></p><label class="scan-confirm"><input id="scanConfirmed" type="checkbox">Сверил дату, магазин, валюту и позиции с фото</label>
    <footer><button type="submit" class="btn btn-primary" id="scanTransfer" disabled>В черновик операции</button></footer></form></div>
    <p id="scanStatus" class="muted-small" role="status"></p><div class="scan-toolbar" id="scanRunBar"><button id="scanRun" type="button" class="btn btn-primary" disabled>Распознать</button><button id="scanCancel" type="button" class="btn btn-secondary" hidden>Отменить</button></div>
    <dialog id="scanTextDialog" class="choice-dialog task-dialog"><header><h3>Распознанный текст</h3>${iconButton('scanTextClose','close','Закрыть текст')}</header><textarea id="scanText" rows="15" maxlength="80000" aria-label="Распознанный текст"></textarea><button id="scanReparse" class="btn btn-primary" type="button">Разобрать исправленный текст</button></dialog>`;
  document.body.append(dialog);
  let source=null, points=[], draft=null, job=null, generation=0, transferred=false, originalText='', busy=false;
  const canvas=node('scanCanvas');
  function resetPoints(){points=[[0,0],[1,0],[1,1],[0,1]];draw();}
  function draw(){
    if(!source)return;
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
  function invalidateReview(){delete dialog.dataset.stage;node('scanStep').textContent='Один чек на фото · JPG, PNG или WebP до 20 МБ';draft=null;node('scanReview').hidden=true;node('scanConfirmed').checked=false;transferred=false;}
  function cancel(){generation++;job?.cancel();job=null;setBusy(false);status('Распознавание отменено');}
  function cleanup(){cancel();node('scanTextDialog').close();if(source)source.width=source.height=1;source=null;canvas.width=canvas.height=1;node('scanFile').value='';node('scanText').value='';node('scanRows').replaceChildren();originalText='';invalidateReview();node('scanWorkspace').hidden=true;setBusy(false);status('');}
  function open(){cleanup();dialog.showModal();node('scanUpload').focus();}
  node('scanClose').onclick=()=>dialog.close();
  dialog.addEventListener('close',cleanup);
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  // Installed before the global choice listener: Escape in a nested choice belongs to it.
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||!dialog.open||node('appChoiceDialog')?.open)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(node('scanTextDialog').open)node('scanTextDialog').close();else dialog.close();
  },true);
  node('scanUpload').onclick=()=>node('scanFile').click();
  node('scanFile').onchange=async()=>{
    const file=node('scanFile').files[0];if(!file)return;
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
  function showDraft(value){
    draft=value;dialog.dataset.stage='review';node('scanStep').textContent='Проверьте поля по фото';node('scanDate').value=draft.date;node('scanShop').value=draft.shop;node('scanTotal').value=decimal(draft.total);
    node('scanReview').hidden=false;node('scanConfirmed').checked=false;renderRows();validate();
  }
  function renderRows(){
    node('scanRows').replaceChildren();
    draft.rows.forEach((row,index)=>{
      const el=document.createElement('section');el.className='scan-row';
      el.innerHTML=`<label class="field scan-name"><span>Позиция ${index+1}</span><input data-scan-field="name" maxlength="160" required></label>${iconButton('', 'trash', 'Удалить позицию '+(index+1))}<div class="scan-row-numbers">${[['price','Цена до скидки'],['quantity','Количество'],['discount','Скидка на строку'],['total','Оплачено']].map(([field,label])=>`<label class="field"><span>${label}</span><input data-scan-field="${field}" inputmode="decimal" required></label>`).join('')}</div><label class="field scan-discount-type"><span>Тип скидки</span><select data-scan-field="discount_type"><option value="promo">Акция</option><option value="loyalty_points">Баллы</option><option value="coupon">Купон</option></select></label><small class="muted-small scan-source"></small>`;
      el.querySelector('.scan-source').textContent=row.source;
      el.querySelector('[data-scan-field=name]').value=row.name;
      for(const field of ['price','quantity','discount','total']){const input=el.querySelector(`[data-scan-field=${field}]`);input.value=field==='quantity'?row.quantity??'':decimal(row[field]);input.placeholder='Не распознано';}
      el.querySelector('select').value=row.discount_type||'promo';el.querySelector('.scan-discount-type').hidden=!row.discount;
      el.addEventListener('input',e=>{
        const field=e.target.dataset.scanField;if(!field)return;
        row[field]=field==='name'||field==='discount_type'?e.target.value:field==='quantity'?Number(e.target.value.replace(',','.')):inputMoney(e.target.value);
        el.querySelector('.scan-discount-type').hidden=!row.discount;node('scanConfirmed').checked=false;validate();
      });
      el.querySelector('button').onclick=()=>{draft.rows.splice(index,1);node('scanConfirmed').checked=false;renderRows();validate();};
      node('scanRows').append(el);
    });
  }
  function readMeta(){if(!draft)return;draft.date=node('scanDate').value;draft.shop=node('scanShop').value;draft.total=inputMoney(node('scanTotal').value);}
  function validate(){
    if(!draft)return;readMeta();const errors=parser.validate(draft);
    node('scanArithmetic').textContent=errors.length?errors.join(' · '):'Суммы сходятся. Сверьте названия и цифры с фото.';
    node('scanArithmetic').classList.toggle('scan-error',!!errors.length);
    node('scanTransfer').disabled=errors.length>0||!node('scanConfirmed').checked||transferred;return errors;
  }
  for(const id of ['scanDate','scanShop','scanTotal','scanCurrency'])node(id).addEventListener('input',()=>{node('scanConfirmed').checked=false;validate();});
  node('scanConfirmed').onchange=validate;
  node('scanAddRow').onclick=()=>{if(draft.rows.length>=150)return;draft.rows.push({name:'',price:null,quantity:1,discount:0,total:null,source:'Добавлено вручную',discount_type:'promo'});node('scanConfirmed').checked=false;renderRows();validate();node('scanRows').lastElementChild.querySelector('input').focus();};
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
    state.createReceiptItems=draft.rows.map(r=>modal.createReceiptDraft({name:r.name,quantity:r.quantity,shop_name:draft.shop,
      unit_price:r.price/100, is_discounted:r.discount>0, regular_unit_price:r.discount>0?r.price/100:null,
      discount_mode:r.discount>0?'amount':null, discount_value:r.discount>0?r.discount/100:null,
      discount_type:r.discount>0?r.discount_type||'promo':null,note:('OCR: '+r.source).slice(0,300)},'create'));
    modal.setCreateOperationMode('receipt');
    node('opAmount').value=decimal(draft.total);node('opAmount').dispatchEvent(new Event('input',{bubbles:true}));
    modal.renderReceiptSummary('create');dialog.close();
  };
  const button=document.createElement('button');button.type='button';button.id='openReceiptScan';button.className='btn btn-secondary btn-icon';icons.apply(button,'receipt','Сканировать чек');button.onclick=open;
  // Layout setup moves header controls but retains this button and its listener.
  node('opReceiptFields').prepend(button);
  const sync=()=>{button.hidden=node('opEntryMode').value!=='operation'||state.createFlowMode==='plan';if(node('createModal').classList.contains('hidden')&&dialog.open)dialog.close();};
  new MutationObserver(sync).observe(node('createModal'),{attributes:true,attributeFilter:['class']});
  node('createEntryModeSwitch').addEventListener('click',()=>queueMicrotask(sync));
})();
