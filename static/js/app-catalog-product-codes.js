(() => {
  const node=id=>document.getElementById(id);
  let product=null,data=null,bound=false,generation=0,controller=null,failed=false;
  const barcodes=new Map(),retailers=new Map(),choices=new Map();
  const hosts=()=>[...document.querySelectorAll('[data-offer-codes]')];
  const sizeKey=value=>JSON.stringify([value.sale_unit||null,Number(value.package_quantity)||null,value.package_unit||null]);
  const measurement=()=>window.App.measurements.snapshot({sale_unit:node('catalogProductSaleUnit').value,package_quantity:node('catalogProductPackageQuantity').value,package_unit:node('catalogProductPackageUnit').value});
  function selection(id){
    const mapped=data?.offers?.find(o=>Number(o.template_id)===id);
    const linked=data?.variants?.find(v=>Number(v.id)===Number(mapped?.variant_id));
    const matches=linked?[linked]:(data?.variants||[]).filter(v=>!v.is_archived&&sizeKey(v)===sizeKey(measurement()));
    const choice=choices.get(id);
    const variant=matches.length===1?matches[0]:matches.find(v=>String(v.id)===choice);
    return {matches,variant,key:variant?String(variant.id):matches.length?'':'new:'+sizeKey(measurement())};
  }
  function status(){
    node('catalogProductCodesStatus').textContent=failed?'Не удалось загрузить коды.':!data&&product?'Загружаю коды…':hosts().length?'Коды сохраняются общей кнопкой. Штрихкод одного размера общий для магазинов; артикул — свой у каждого источника.':'';
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
      const id=Number(host.dataset.offerCodes),oldKey=host.dataset.codeKey||'';
      const {matches,variant,key}=selection(id);
      if(oldKey.startsWith('new:')&&key.startsWith('new:')&&oldKey!==key&&barcodes.has(oldKey)){barcodes.set(key,barcodes.get(oldKey));barcodes.delete(oldKey);}
      host.dataset.codeKey=key;host.replaceChildren();
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
      const note=document.createElement('small');note.className='muted-small offer-code-size';
      note.textContent=variant?.is_archived?'Штрихкод архивного размера':window.App.measurements.summary(variant||measurement());host.append(note);
    }
    status();
    node('catalogProductSizeNote').textContent=product&&sizeKey(product)!==sizeKey(measurement())?'Размер изменён. После сохранения изменение появится в истории товара; старые чеки сохранят прежний размер.':'Изменение размера сохраняется в истории товара. В старых чеках остаётся прежний размер.';
  }
  function bind(){
    if(bound)return;bound=true;
    for(const id of ['catalogProductSaleUnit','catalogProductPackageQuantity','catalogProductPackageUnit'])for(const event of ['input','change'])node(id).addEventListener(event,render);
    node('catalogProductCodesRetry').addEventListener('click',load);
  }
  function close(){generation++;controller?.abort();product=null;data=null;failed=false;barcodes.clear();retailers.clear();choices.clear();}
  function open(value){close();bind();product=value;render();if(product)load();}
  function payload(){
    const keys=new Set(hosts().map(h=>h.dataset.codeKey)),ids=new Set(hosts().map(h=>Number(h.dataset.offerCodes)));
    const result={barcodes:[...barcodes].filter(([key])=>keys.has(key)).map(([key,codes])=>({variant_id:key.startsWith('new:')?null:Number(key),codes})),retailers:[...retailers].filter(([id])=>ids.has(id)).map(([template_id,retailer_code])=>({template_id,retailer_code}))};
    if(result.barcodes.some(v=>v.codes.some(code=>!window.App.receiptCodes.validBarcode(code))))throw new Error('Проверьте штрихкод: нужны 8, 12, 13 или 14 цифр с верной контрольной цифрой.');
    return result.barcodes.length||result.retailers.length?result:undefined;
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
