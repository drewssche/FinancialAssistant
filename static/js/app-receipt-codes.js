(() => {
  const {core} = window.App;
  let saveHintId=0;
  function validBarcode(value) {
    if (!/^(?:\d{8}|\d{12,14})$/.test(value) || !Number(value)) return false;
    const digits=[...value].map(Number),check=digits.pop();
    return (10-digits.reverse().reduce((sum,n,i)=>sum+n*(i%2?1:3),0)%10)%10===check;
  }
  function entries(row) {
    return row.code_entries ||= (row.catalog_codes || []).map(e=>({...e}));
  }
  function payload(row) {
    if(!row.code_save) return [];
    return entries(row).filter(e=>e.code.trim()).map(e=>({kind:e.kind,code:e.code.trim()}));
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
      const list=entries(row),kept=list.filter(e=>!e.from_catalog);list.splice(0,list.length,...kept);row.codes_loaded_entity=null;
    }
    row.variant_id=null;row.variant_snapshot=null;row.variant_options=null;row.variant_status='';row.brand_touched=false;
    for(const key of ['product_id','product_name','name','template_id','source_id','brand_id']) row[key]=found[key]??null;
    if(!row.category_touched) row.category_id=found.category_id||null;
    if(found.variant_id){
      Object.assign(row,window.App.measurements.snapshot(found),{variant_id:found.variant_id,variant_snapshot:found.variant_snapshot,measurement_touched:true});
    }else if(!row.measurement_touched)Object.assign(row,window.App.measurements.snapshot(found));
    row.price_touched=true;
    const brand=window.App.state.itemBrands?.find(b=>Number(b.id)===Number(found.brand_id));
    row.brand_name=brand?.name||'';row.brand_accent_color=brand?.accent_color||null;row.brand_image_id=brand?.image_id||null;
    row.code_match_label=found.matched_by.includes('barcode')?'Найден по штрихкоду':'Найден по артикулу магазина';
  }
  function mount(host,{row,shop,onSelect,onChange=()=>{},auto=false,loadKnown=false}) {
    const list=entries(row);
    const details=document.createElement('details');details.className='receipt-codes';details.open=row.codes_open==null?Boolean(list.length):Boolean(row.codes_open);
    const summary=document.createElement('summary');summary.textContent=list.length?'Коды товара':'Добавить код';details.append(summary);
    details.addEventListener('toggle',()=>row.codes_open=details.open);
    const fields=document.createElement('div');fields.className='receipt-code-fields';details.append(fields);
    const actions=document.createElement('div');actions.className='receipt-code-actions';
    const add=document.createElement('button');add.type='button';add.className='btn btn-secondary btn-xs';add.textContent='Ещё код';
    const search=document.createElement('button');search.type='button';search.className='btn btn-secondary btn-xs';search.textContent='Найти по коду';
    actions.append(add,search);details.append(actions);
    const saveLabel=document.createElement('label');saveLabel.className='receipt-code-save';
    const save=document.createElement('input');save.type='checkbox';save.checked=Boolean(row.code_save);
    saveLabel.append(save,document.createTextNode('Добавить коды в каталог'));details.append(saveLabel);
    const saveHint=document.createElement('p');saveHint.className='muted-small receipt-code-save-hint';saveHint.id='receiptCodeSaveHint'+(++saveHintId);saveHint.setAttribute('aria-live','polite');details.append(saveHint);save.setAttribute('aria-describedby',saveHint.id);
    function refreshSave(){
      const codes=list.filter(e=>e.code.trim());
      const unknown=codes.find(e=>!['barcode','retailer'].includes(e.kind));
      const invalid=codes.find(e=>e.kind==='barcode'&&!validBarcode(e.code));
      const retailers=new Set(codes.filter(e=>e.kind==='retailer').map(e=>e.code.trim()));
      const reason=!codes.length?'Введите штрихкод или артикул.':unknown?`Для кода ${unknown.code} выберите тип: штрихкод или артикул.`:invalid?`Проверьте длину и контрольную цифру штрихкода ${invalid.code}.`:retailers.size>1?'Оставьте один артикул этого магазина.':retailers.size&&!shop()?.trim()?'Укажите магазин, чтобы сохранить его артикул.':'';
      save.disabled=Boolean(reason);
      if(reason)row.code_save=false;
      save.checked=Boolean(row.code_save);
      saveHint.textContent=reason||(row.code_save?'Коды будут добавлены в каталог вместе с сохранением операции. Отмена черновика ничего не изменит.':'Включите, чтобы запомнить новые коды для следующих чеков. Уже сохранённые коды повторно добавлять не нужно.');
    }
    host.refreshCodeState=refreshSave;
    const status=document.createElement('p');status.className='muted-small';status.setAttribute('role','status');details.append(status);
    const results=document.createElement('div');results.className='receipt-code-results';details.append(results);host.replaceChildren(details);
    let timer,seq=0;
    const signature=()=>JSON.stringify([shop(),list,row.name,window.App.measurements.snapshot(row)]);
    function changed(){seq++;row.code_match_label='';row.code_save=false;save.checked=false;results.replaceChildren();status.textContent='';refreshSave();onChange();}
    function draw(){
      fields.replaceChildren();
      list.forEach((entry,index)=>{
        if(!entry.manual_kind&&entry.kind==='unknown'&&validBarcode(entry.code))entry.kind='barcode';
        const line=document.createElement('div');line.className='receipt-code-line';
        const input=document.createElement('input');input.type='text';input.maxLength=160;input.autocomplete='off';input.value=entry.code;input.placeholder='Штрихкод или артикул';input.setAttribute('aria-label','Код товара');
        const type=document.createElement('select');type.setAttribute('aria-label','Тип кода');
        for(const [value,label] of [['unknown','Определить'],['barcode','Штрихкод'],['retailer','Артикул']])type.add(new Option(label,value));
        type.value=entry.kind||'unknown';
        const remove=document.createElement('button');remove.type='button';remove.className='btn btn-secondary btn-icon';window.App.icons.apply(remove,'close','Удалить код');
        input.oninput=()=>{entry.code=input.value.trim();if(!entry.manual_kind){entry.kind=validBarcode(entry.code)?'barcode':'unknown';type.value=entry.kind;}changed();clearTimeout(timer);timer=setTimeout(()=>lookup(false),300);};
        input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();clearTimeout(timer);lookup(false);}};
        type.onchange=()=>{entry.kind=type.value;entry.manual_kind=type.value!=='unknown';changed();draw();lookup(false);};
        remove.onclick=()=>{list.splice(index,1);changed();draw();};
        line.append(input,type,remove);fields.append(line);
      });
      add.disabled=list.length>=10;refreshSave();
    }
    async function lookup(allowAuto){
      const codes=list.filter(e=>e.code.trim()).map(e=>({kind:e.manual_kind||e.from_catalog?e.kind:'unknown',code:e.code.trim()}));
      if(!codes.length)return;
      const token=++seq, before=signature();status.textContent='Ищу по кодам…';results.replaceChildren();
      try{
        const data=await core.requestJson('/api/v1/operations/catalog-products/lookup-codes',{method:'POST',headers:{...core.authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({codes,shop_name:shop()||''})});
        if(token!==seq||!host.isConnected||before!==signature())return;
        const items=data.items||[];
        status.textContent=[...(data.warnings||[]),...(data.unmatched?.length?['Не найдены коды: '+data.unmatched.join(', ')]:[]),items.length>1?'Найдены разные варианты — выберите подходящий':items.length?'':'Совпадений по кодам нет. Можно выбрать товар по названию.'].filter(Boolean).join(' · ');
        function choose(found,collapse=false){
          if(collapse)row.codes_open=false;
          for(const entry of list){if((entry.kind==='unknown'||!entry.manual_kind)&&found.matched_codes.includes(entry.code)&&found.matched_by.length===1)entry.kind=found.matched_by[0];}
          row.code_save=false;save.checked=false;onSelect(found);status.textContent=row.code_match_label||'Товар выбран по коду';results.replaceChildren();draw();if(collapse)details.open=false;else if(host.isConnected)summary.focus({preventScroll:true});
        }
        if(allowAuto&&data.auto_match&&!conflict(row,items[0])){choose(items[0],true);return;}
        if(items.length===1&&Number(row.product_id)===Number(items[0].product_id)&&Number(row.variant_id||0)===Number(items[0].variant_id||0)){
          status.textContent=[status.textContent,'Код соответствует выбранному товару'].filter(Boolean).join(' · ');return;
        }
        for(const found of items){
          const button=document.createElement('button');button.type='button';button.className='btn btn-secondary receipt-code-result';
          const title=document.createElement('strong');title.textContent=found.product_name;
          const detail=document.createElement('small');detail.textContent=[found.variant_snapshot?.name,window.App.measurements.summary(found),found.matched_by.includes('barcode')?'Штрихкод совпадает':'Артикул совпадает',conflict(row,found)?'Другая фасовка — выбор заменит единицы и размер':''].filter(Boolean).join(' · ');
          button.append(title,detail);button.onclick=()=>choose(found);results.append(button);
        }
      }catch(error){if(token===seq&&host.isConnected)status.textContent='Не удалось проверить коды. Повторите поиск: '+error.message;}
    }
    add.onclick=()=>{list.push({kind:'unknown',code:''});changed();draw();fields.lastElementChild.querySelector('input').focus();};
    summary.addEventListener('click',()=>{if(!details.open&&!list.length){list.push({kind:'unknown',code:''});draw();}});
    search.onclick=()=>{clearTimeout(timer);lookup(false);};
    save.onchange=()=>{
      // An explicit save choice must not be undone by an earlier automatic lookup.
      seq++;clearTimeout(timer);results.replaceChildren();status.textContent='';
      row.code_save=save.checked;refreshSave();onChange();
    };
    draw();if(auto&&list.some(e=>e.code))lookup(true);
    const entity=String(row.product_id||'')+':'+String(row.template_id||'');
    if(loadKnown&&row.product_id&&row.template_id&&row.codes_loaded_entity!==entity){
      const before=signature();
      core.requestJson(`/api/v1/operations/catalog-products/${row.product_id}/identity`,{headers:core.authHeaders()}).then(data=>{
        if(!host.isConnected||before!==signature())return;
        row.codes_loaded_entity=entity;
        const saved=data.offers?.find(offer=>Number(offer.template_id)===Number(row.template_id));
        if(saved?.retailer_code&&!list.some(e=>e.code===saved.retailer_code)){
          list.push({kind:'retailer',code:saved.retailer_code,from_catalog:true});summary.textContent='Коды товара';draw();
        }
      }).catch(()=>{if(host.isConnected)status.textContent='Не удалось загрузить сохранённые коды. Можно повторить, открыв детали заново.';});
    }
  }
  window.App.receiptCodes={validBarcode,entries,payload,mount,apply,conflict};
})();
