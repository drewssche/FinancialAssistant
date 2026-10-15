(() => {
  let started=false;
  window.addEventListener('message',async event=>{
    if(started||event.origin!==location.origin||event.source!==parent||event.data?.type!=='recognize'||!(event.data.image instanceof Blob))return;
    started=true;const {id,image}=event.data, base='/static/vendor/receipt-ocr/v7';
    const send=data=>parent.postMessage({id,...data},location.origin);
    let worker;
    try{
      if(!window.Tesseract)throw new Error('Не удалось загрузить движок распознавания');
      worker=await Tesseract.createWorker(['rus','eng'],1,{
        workerPath:`${base}/worker.min.js`,corePath:base,langPath:`${base}/lang`,workerBlobURL:false,
        cachePath:'fa-receipt-ocr-v7',errorHandler:()=>{},
        logger:m=>send({type:'progress',progress:m.status==='recognizing text'?Math.round(m.progress*100):null}),
      });
      await worker.setParameters({tessedit_pageseg_mode:'6',preserve_interword_spaces:'1'});
      const {data}=await worker.recognize(image,{}, {text:true,blocks:true});
      await worker.terminate();worker=null;
      send({type:'result',result:{text:data.text.slice(0,80000),blocks:data.blocks}});
    }catch(error){await worker?.terminate();send({type:'error',error:String(error?.message||error)});}
  });
})();
