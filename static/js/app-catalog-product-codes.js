(() => {
  const node=id=>document.getElementById(id);
  let product=null,data=null,bound=false,generation=0,controller=null,failed=false;
  const barcodes=new Map(),retailers=new Map(),choices=new Map(),sizes=new Map();
  const hosts=()=>[...document.querySelectorAll('[data-offer-codes]')];
  const sizeKey=value=>JSON.stringify([value.sale_unit||null,Number(value.package_quantity)||null,value.package_unit||null]);
  const measurement=()=>window.App.measurements.snapshot({sale_unit:node('catalogProductSaleUnit').value,package_quantity:node('catalogProductPackageQuantity').value,package_unit:node('catalogProductPackageUnit').value});
  function sourceSize(id){
    if(sizes.has(id))return sizes.get(id);
    const mapped=data?.offers?.find(o=>Number(o.template_id)===id);
    return data?.variants?.find(v=>Number(v.id)===Number(mapped?.variant_id))||null;
  }
  function selection(id){
    const own=sourceSize(id),size=own||measurement();
    const mapped=data?.offers?.find(o=>Number(o.template_id)===id);
    const linked=!sizes.has(id)&&own?data?.variants?.find(v=>Number(v.id)===Number(mapped?.variant_id)):null;
    const matches=linked?[linked]:(data?.variants||[]).filter(v=>!v.is_archived&&sizeKey(v)===sizeKey(size));
    const choice=choices.get(id);
    const variant=matches.length===1?matches[0]:matches.find(v=>String(v.id)===choice);
    return {matches,variant,size,own,key:variant?String(variant.id):matches.length?'':'new:'+sizeKey(size)};
  }
  function sizeFields(host,id,current){
    const section=document.createElement('div');section.className='offer-source-size';
    const label=document.createElement('label');label.className='offer-size-toggle';
    const toggle=document.createElement('input');toggle.type='checkbox';toggle.dataset.offerOwnSize='';toggle.checked=Boolean(current.own);toggle.disabled=!data;
    label.append(toggle,document.createTextNode('Свой размер для этого источника'));section.append(label);
    const note=document.createElement('small');note.className='muted-small';note.textContent=current.own?'':'Из товара: '+window.App.measurements.summary(measurement());if(note.textContent)section.append(note);
    toggle.onchange=()=>{sizes.set(id,toggle.checked?{...measurement(),sale_unit:measurement().sale_unit||'piece'}:null);choices.delete(id);render();};
    if(current.own){
      const grid=document.createElement('div');grid.className='offer-size-fields';
      for(const [field,title] of [['sale_unit','Единица продажи'],['package_quantity','Размер одной штуки / упаковки'],['package_unit','Единица размера']]){
        const wrap=document.createElement('label');wrap.className='field';const text=document.createElement('span');text.textContent=title;
        const input=document.createElement(field==='package_quantity'?'input':'select');input.dataset.offerSizeField=field;input.setAttribute('form','catalogProductForm');
        if(field==='package_quantity'){input.type='number';input.min='0.001';input.step='0.001';input.placeholder='Например, 200';}else input.innerHTML=window.App.measurements.options(current.size[field],field==='package_unit');
        input.value=current.size[field]||'';input.disabled=!data||(field!=='sale_unit'&&!['piece','pack'].includes(current.size.sale_unit));
        input.onchange=()=>{const updated={...current.size,[field]:input.value||null};if(field==='sale_unit'&&!['piece','pack'].includes(updated.sale_unit)){updated.package_quantity=null;updated.package_unit=null;}sizes.set(id,updated);choices.delete(id);render();};
        wrap.append(text,input);grid.append(wrap);
      }
      section.append(grid);
    }
    host.append(section);
  }
  function status(){
    node('catalogProductCodesStatus').textContent=failed?'Не удалось загрузить коды.':!data&&product?'Загружаю коды…':'';
    node('catalogProductCodesRetry').hidden=!failed;
  }
  function syncBarcode(key,value,except){
    for(const host of hosts())if(host.dataset.codeKey===key){const field=host.querySelector('[data-code=barcode]');if(field&&field!==except)field.value=value;}
  }
  function inputField(host,name,title,max){
    const label=document.createElement('label');label.className='field';
    const text=document.createElement('span');text.textContent=title;
    const input=document.createElement('input');input.type='text';input.dataset.code=name;input.maxLength=max;input.autocomplete='off';input.setAttribute('form','catalogProductForm');
    label.append(text,input);host.append(label);return input;
  }
  function render(){
    for(const host of hosts()){
      const id=Number(host.dataset.offerCodes);
      const selected=selection(id),{matches,variant,key}=selected;
      host.dataset.codeKey=key;host.replaceChildren();
      sizeFields(host,id,selected);
      const barcode=inputField(host,'barcode','Штрихкод',480);
      barcode.value=(barcodes.get(key)||variant?.codes||[]).join(', ');barcode.placeholder='Цифры под штрихкодом';
      barcode.disabled=!data||!key||Boolean(variant?.is_archived);
      barcode.oninput=()=>{barcodes.set(key,barcode.value.split(/[\s,;]+/).filter(Boolean));syncBarcode(key,barcode.value,barcode);};
      const sku=inputField(host,'sku','Артикул магазина',160);
      sku.value=retailers.get(id)??data?.offers?.find(o=>Number(o.template_id)===id)?.retailer_code??'';sku.placeholder='Например, 000-42';sku.disabled=!data;
      sku.oninput=()=>retailers.set(id,sku.value);
      if(matches.length>1){
        const label=document.createElement('label');label.className='field offer-code-variant';
        const title=document.createElement('span');title.textContent='Запись штрихкода для этого размера';
        const select=document.createElement('select');select.add(new Option('Выберите запись',''));
        for(const v of matches)select.add(new Option(`${v.name} · ${(v.codes||[]).join(', ')||'без штрихкода'}`,String(v.id)));
        select.value=variant?String(variant.id):'';select.onchange=()=>{choices.set(id,select.value);render();};
        label.append(title,select);host.append(label);
      }
      if(variant?.is_archived){const note=document.createElement('small');note.className='muted-small offer-code-size';note.textContent='Штрихкод архивного размера';host.append(note);}
    }
    status();

  }
  function bind(){
    if(bound)return;bound=true;
    for(const id of ['catalogProductSaleUnit','catalogProductPackageQuantity','catalogProductPackageUnit'])for(const event of ['input','change'])node(id).addEventListener(event,render);
    node('catalogProductCodesRetry').addEventListener('click',load);
  }
  function close(){generation++;controller?.abort();product=null;data=null;failed=false;barcodes.clear();retailers.clear();choices.clear();sizes.clear();}
  function open(value){close();bind();product=value;render();if(product)load();}
  function payload(){
    const keys=new Set(hosts().map(h=>h.dataset.codeKey)),ids=new Set(hosts().map(h=>Number(h.dataset.offerCodes)));
    const standardKey='new:'+sizeKey(measurement());
    const result={barcodes:[...barcodes].filter(([key])=>keys.has(key)&&(!key.startsWith('new:')||key===standardKey)).map(([key,codes])=>({variant_id:key.startsWith('new:')?null:Number(key),codes})),retailers:[...retailers].filter(([id])=>ids.has(id)).map(([template_id,retailer_code])=>({template_id,retailer_code}))};
    const offerSizes=[];
    for(const id of ids){
      const selected=selection(id),codes=barcodes.get(selected.key);
      if(!sizes.has(id)&&!(selected.own&&selected.key.startsWith('new:')&&codes))continue;
      if(selected.own&&!selected.key)throw new Error('Уточните фасовку источника перед сохранением.');
      const edit={template_id:id,use_product_size:!selected.own,...(selected.own?{...window.App.measurements.snapshot(selected.size),variant_id:selected.variant?.id||null}:{})};
      if(selected.own&&selected.key.startsWith('new:')&&selected.key!==standardKey&&codes)edit.codes=codes;
      offerSizes.push(edit);
    }
    if(offerSizes.length)result.offer_sizes=offerSizes;
    if([...result.barcodes,...offerSizes].some(v=>(v.codes||[]).some(code=>!window.App.receiptCodes.validBarcode(code))))throw new Error('Проверьте штрихкод: нужны 8, 12, 13 или 14 цифр с верной контрольной цифрой.');
    return result.barcodes.length||result.retailers.length||offerSizes.length?result:undefined;
  }

  async function load(){
    if(!product)return;
    controller?.abort();controller=new AbortController();const token=++generation;failed=false;
    data=null;render();
    try{
      const value=await window.App.core.requestJson(`/api/v1/operations/catalog-products/${product.id}/identity`,{headers:window.App.core.authHeaders(),signal:controller.signal});
      if(token===generation){data=value;render();}
    }catch(error){if(token===generation&&error.name!=='AbortError'){failed=true;render();}}
  }
  window.App.registerRuntimeModule('catalog-product-codes',{open,payload,reload:load,refresh(value){product=value;load();},close});
})();
