(() => {
  const node=id=>document.getElementById(id);
  let product=null, data=null, bound=false, generation=0, controller=null, lastBarcodeKey='';
  const barcodes=new Map(), retailers=new Map();
  const ids=['catalogProductBarcode','catalogProductCodeVariant','catalogProductSku','catalogProductCodeOffer','catalogProductCodeShop'];
  const split=value=>value.split(/[\s,;]+/).filter(Boolean);
  function renderBarcode(){
    const key=barcodeKey();
    const value=barcodes.get(key) || data?.variants?.find(v=>String(v.id)===key)?.codes || [];
    node('catalogProductBarcode').value=value.join(', ');
    node('catalogProductBarcode').disabled=key==='';
  }
  function renderRetailer(){
    const key=node('catalogProductCodeOffer').value;
    const saved=data?.offers?.find(o=>String(o.template_id)===key);
    node('catalogProductSku').value=retailers.get(key)?.retailer_code ?? saved?.retailer_code ?? '';
    node('catalogProductCodeShop').value=retailers.get(key)?.shop_name || '';
    node('catalogProductCodeShopField').hidden=key!=='new';
    node('catalogProductSku').disabled=key==='';
  }
  function measurement(){return window.App.measurements.snapshot({sale_unit:node('catalogProductSaleUnit').value,package_quantity:node('catalogProductPackageQuantity').value,package_unit:node('catalogProductPackageUnit').value});}
  function sizeKey(value){return JSON.stringify([value.sale_unit||null,Number(value.package_quantity)||null,value.package_unit||null]);}
  function barcodeKey(){return node('catalogProductCodeVariant').value==='new'?'new:'+sizeKey(measurement()):node('catalogProductCodeVariant').value;}
  function selectSize(){
    if(!data)return;
    const current=measurement(),key=sizeKey(current);
    const matches=(data.variants||[]).filter(v=>!v.is_archived&&sizeKey(v)===key);
    const selector=node('catalogProductCodeVariant'),previous=selector.value;
    selector.replaceChildren();
    if(matches.length>1)selector.add(new Option('Выберите запись штрихкода',''));
    for(const v of matches)selector.add(new Option(`${v.name} · ${(v.codes||[]).join(', ')||'без штрихкода'}`,String(v.id)));
    if(!matches.length)selector.add(new Option('Текущий размер','new'));
    selector.value=matches.length>1?(matches.some(v=>String(v.id)===previous)?previous:''):matches.length?String(matches[0].id):'new';
    const nextKey=barcodeKey();
    if(lastBarcodeKey.startsWith('new:')&&nextKey.startsWith('new:')&&lastBarcodeKey!==nextKey&&barcodes.has(lastBarcodeKey)){barcodes.set(nextKey,barcodes.get(lastBarcodeKey));barcodes.delete(lastBarcodeKey);}
    lastBarcodeKey=nextKey;
    node('catalogProductCodeVariantField').hidden=matches.length<=1;
    renderBarcode();
    node('catalogProductSizeNote').textContent=product&&sizeKey(product)!==key?'Размер изменён. После сохранения изменение появится в истории товара; старые чеки сохранят прежний размер.':'Изменение размера сохраняется в истории товара. В старых чеках остаётся прежний размер.';
  }
  function accept(value){
    data=value;
    ids.forEach(id=>node(id).disabled=false);
    selectSize();
    const offers=(product?.offers||[]).filter(o=>!o.is_archived);
    const offer=node('catalogProductCodeOffer'),old=offer.value;offer.replaceChildren();
    if(offers.length>1)offer.add(new Option('Выберите магазин',''));
    for(const o of offers)offer.add(new Option(`${o.source_name||o.shop_name||'Без магазина'}${offers.filter(x=>x.source_id===o.source_id).length>1?' · '+o.name:''}`,String(o.template_id)));
    offer.add(new Option('Другой магазин','new'));
    offer.value=retailers.size&&[...offer.options].some(o=>o.value===old)?old:offers.length===1?String(offers[0].template_id):offers.length?'':'new';
    node('catalogProductCodeOfferField').hidden=offers.length<=1;
    node('catalogProductCodeOfferHint').hidden=offers.length!==1;
    node('catalogProductCodeOfferHint').querySelector('small').textContent=offers.length===1?(offers[0].source_name||offers[0].shop_name||'Без магазина'):'';
    ids.forEach(id=>node(id).disabled=false);
    renderBarcode();renderRetailer();node('catalogProductCodesStatus').textContent='Сохраняются вместе с товаром.';
  }
  function bind(){
    if(bound)return;bound=true;
    node('catalogProductBarcode').addEventListener('input',()=>barcodes.set(barcodeKey(),split(node('catalogProductBarcode').value)));
    const remember=()=>retailers.set(node('catalogProductCodeOffer').value,{retailer_code:node('catalogProductSku').value,shop_name:node('catalogProductCodeShop').value});
    node('catalogProductSku').addEventListener('input',remember);
    node('catalogProductCodeShop').addEventListener('input',remember);
    node('catalogProductCodeVariant').addEventListener('change',()=>{lastBarcodeKey=barcodeKey();renderBarcode();});
    for(const id of ['catalogProductSaleUnit','catalogProductPackageQuantity','catalogProductPackageUnit'])for(const event of ['input','change'])node(id).addEventListener(event,selectSize);
    node('catalogProductCodeOffer').addEventListener('change',renderRetailer);
    for(const name of ['Offer'])node(`catalogProductCode${name}Hint`).querySelector('button').addEventListener('click',()=>{node(`catalogProductCode${name}Hint`).hidden=true;node(`catalogProductCode${name}Field`).hidden=false;node(`catalogProductCode${name}`).focus();});
    node('catalogProductCodesRetry').addEventListener('click',()=>load());
  }
  function loading(){ids.forEach(id=>node(id).disabled=true);node('catalogProductCodesStatus').textContent='Загружаю коды…';node('catalogProductCodesRetry').hidden=true;}
  function open(value){
    bind();controller?.abort();generation++;product=value;data=null;lastBarcodeKey='';barcodes.clear();retailers.clear();
    ids.forEach(id=>node(id).value='');
    node('catalogProductCodeVariantField').hidden=true;node('catalogProductCodeOfferField').hidden=true;node('catalogProductCodeShopField').hidden=true;
    node('catalogProductCodeOfferHint').hidden=true;
    if(product)load();else{node('catalogProductCodesRetry').hidden=true;accept({variants:[],offers:[]});}
  }
  function payload(){
    const result={barcodes:[...barcodes].filter(([key])=>!key.startsWith('new:')||key===barcodeKey()).map(([key,codes])=>({variant_id:key.startsWith('new:')?null:Number(key),codes})),retailers:[...retailers].map(([key,value])=>({template_id:key==='new'?null:Number(key),...value}))};
    if(result.barcodes.some(v=>v.codes.some(code=>!window.App.receiptCodes.validBarcode(code))))throw new Error('Проверьте штрихкод: нужны 8, 12, 13 или 14 цифр с верной контрольной цифрой.');
    if(result.retailers.some(r=>!r.template_id&&r.retailer_code.trim()&&!r.shop_name.trim()))throw new Error('Укажите магазин для артикула.');
    return result.barcodes.length||result.retailers.length?result:undefined;
  }
  async function load(){
    if(!product)return;
    controller?.abort();controller=new AbortController();const token=++generation;
    loading();
    try{
      const value=await window.App.core.requestJson(`/api/v1/operations/catalog-products/${product.id}/identity`,{headers:window.App.core.authHeaders(),signal:controller.signal});
      if(token===generation)accept(value);
    }catch(error){if(token===generation&&error.name!=='AbortError'){node('catalogProductCodesStatus').textContent='Не удалось загрузить коды.';node('catalogProductCodesRetry').hidden=false;}}
  }
  window.App.registerRuntimeModule('catalog-product-codes',{open,payload,reload:load,
    refresh(value){product=value;load();},
    close(){generation++;controller?.abort();product=null;data=null;barcodes.clear();retailers.clear();},
  });
})();
