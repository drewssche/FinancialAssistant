(() => {
  const node=id=>document.getElementById(id);
  let product=null, data=null, bound=false;
  const barcodes=new Map(), retailers=new Map();
  const ids=['catalogProductBarcode','catalogProductCodeVariant','catalogProductSku','catalogProductCodeOffer','catalogProductCodeShop'];
  const split=value=>value.split(/[\s,;]+/).filter(Boolean);
  function renderBarcode(){
    const key=node('catalogProductCodeVariant').value;
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
  function accept(value){
    data=value;
    const active=(data.variants||[]).filter(v=>!v.is_archived);
    const selector=node('catalogProductCodeVariant'), previous=selector.value;
    selector.replaceChildren();
    if(active.length>1)selector.add(new Option('Выберите фасовку',''));
    for(const v of active)selector.add(new Option(`${v.name} · ${window.App.measurements.summary(v)}`,String(v.id)));
    selector.add(new Option('Размер из вкладки «Товар»','new'));
    selector.value=barcodes.size&&[...selector.options].some(o=>o.value===previous)?previous:active.length===1?String(active[0].id):active.length?'':'new';
    node('catalogProductCodeVariantField').hidden=active.length<=1;
    node('catalogProductCodeVariantHint').hidden=active.length!==1;
    node('catalogProductCodeVariantHint').querySelector('small').textContent=active.length===1?window.App.measurements.summary(active[0]):'';
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
    node('catalogProductBarcode').addEventListener('input',()=>barcodes.set(node('catalogProductCodeVariant').value,split(node('catalogProductBarcode').value)));
    const remember=()=>retailers.set(node('catalogProductCodeOffer').value,{retailer_code:node('catalogProductSku').value,shop_name:node('catalogProductCodeShop').value});
    node('catalogProductSku').addEventListener('input',remember);
    node('catalogProductCodeShop').addEventListener('input',remember);
    node('catalogProductCodeVariant').addEventListener('change',renderBarcode);
    node('catalogProductCodeOffer').addEventListener('change',renderRetailer);
    for(const name of ['Variant','Offer'])node(`catalogProductCode${name}Hint`).querySelector('button').addEventListener('click',()=>{node(`catalogProductCode${name}Hint`).hidden=true;node(`catalogProductCode${name}Field`).hidden=false;node(`catalogProductCode${name}`).focus();});
    node('catalogProductCodesRetry').addEventListener('click',()=>window.App.getRuntimeModule('catalog-identity').reload());
  }
  function loading(){ids.forEach(id=>node(id).disabled=true);node('catalogProductCodesStatus').textContent='Загружаю коды…';node('catalogProductCodesRetry').hidden=true;}
  function open(value){
    bind();product=value;data=null;barcodes.clear();retailers.clear();
    ids.forEach(id=>node(id).value='');
    node('catalogProductCodeVariantField').hidden=true;node('catalogProductCodeOfferField').hidden=true;node('catalogProductCodeShopField').hidden=true;
    node('catalogProductCodeVariantHint').hidden=true;node('catalogProductCodeOfferHint').hidden=true;
    if(product)loading();else{node('catalogProductCodesRetry').hidden=true;accept({variants:[],offers:[]});}
  }
  function payload(){
    const result={barcodes:[...barcodes].map(([key,codes])=>({variant_id:key==='new'?null:Number(key),codes})),retailers:[...retailers].map(([key,value])=>({template_id:key==='new'?null:Number(key),...value}))};
    if(result.barcodes.some(v=>v.codes.some(code=>!window.App.receiptCodes.validBarcode(code))))throw new Error('Проверьте штрихкод: нужны 8, 12, 13 или 14 цифр с верной контрольной цифрой.');
    if(result.retailers.some(r=>!r.template_id&&r.retailer_code.trim()&&!r.shop_name.trim()))throw new Error('Укажите магазин для артикула.');
    return result.barcodes.length||result.retailers.length?result:undefined;
  }
  window.App.registerRuntimeModule('catalog-product-codes',{open,accept,payload,loading,refresh(value){product=value;},
    failed(){node('catalogProductCodesStatus').textContent='Не удалось загрузить коды.';node('catalogProductCodesRetry').hidden=false;},
    close(){product=null;data=null;barcodes.clear();retailers.clear();},
  });
})();
