(() => {
  let started=false;
  window.addEventListener('message',async event=>{
    if(started||event.origin!==location.origin||event.source!==parent||event.data?.type!=='recognize'||!(event.data.image instanceof Blob))return;
    started=true;const {id,image}=event.data, base='/static/vendor/receipt-ocr/v7';
    const send=data=>parent.postMessage({id,...data},location.origin);
    let worker, progressBase=0, progressSpan=1;
    try{
      if(!window.Tesseract)throw new Error('Не удалось загрузить движок распознавания');
      worker=await Tesseract.createWorker(['rus','eng'],1,{
        workerPath:`${base}/worker.min.js`,corePath:base,langPath:`${base}/lang`,workerBlobURL:false,
        cachePath:'fa-receipt-ocr-v7',errorHandler:()=>{},
        logger:m=>send({type:'progress',progress:m.status==='recognizing text'?Math.min(99,Math.round((progressBase+m.progress*progressSpan)*100)):null}),
      });
      await worker.setParameters({tessedit_pageseg_mode:'6',preserve_interword_spaces:'1',thresholding_method:'0'});
      const bitmap=await createImageBitmap(image),lines=[];
      const tile=document.createElement('canvas'),core=450,overlap=80;
      try{
        for(let top=0;top<bitmap.height;top+=core){
          progressBase=top/bitmap.height;progressSpan=Math.min(core,bitmap.height-top)/bitmap.height;
          const start=Math.max(0,top-overlap),end=Math.min(bitmap.height,top+core+overlap);
          tile.width=bitmap.width;tile.height=end-start;tile.getContext('2d').drawImage(bitmap,0,start,bitmap.width,end-start,0,0,tile.width,tile.height);
          const {data}=await worker.recognize(tile.toDataURL('image/png'),{}, {text:true,blocks:true});
          for(const block of data.blocks||[])for(const paragraph of block.paragraphs||[])for(const line of paragraph.lines||[]){
            const center=(line.bbox.y0+line.bbox.y1)/2+start;
            if(center>=top&&center<Math.min(bitmap.height,top+core))lines.push({y:center,text:line.text});
          }
        }
      }finally{bitmap.close();tile.width=tile.height=1;}
      await worker.terminate();worker=null;
      send({type:'result',result:{text:lines.sort((a,b)=>a.y-b.y).map(l=>l.text.trim()).join('\n').slice(0,80000),blocks:[]}});
    }catch(error){await worker?.terminate();send({type:'error',error:String(error?.message||error)});}
  });
})();
