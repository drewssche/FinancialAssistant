(() => {
  // Each run owns a document and its OCR worker. Removing it also ends initialization,
  // including cancellation before Tesseract's createWorker promise has resolved.
  function recognize(canvas, progress) {
    const frame=document.createElement('iframe');frame.hidden=true;frame.title='Локальное распознавание';
    frame.src='/static/receipt-ocr.html?v=20261015-ocr1';
    const id=crypto.randomUUID();let settled=false, resolveResult, rejectResult;
    const promise=new Promise((resolve,reject)=>{resolveResult=resolve;rejectResult=reject;});
    function cleanup(){clearTimeout(timer);window.removeEventListener('message',receive);frame.remove();}
    function finish(error,result){if(settled)return;settled=true;cleanup();if(error)rejectResult(new Error(error));else resolveResult(result);}
    function receive(event){
      if(event.origin!==location.origin||event.source!==frame.contentWindow||event.data?.id!==id)return;
      const message=event.data;
      if(message.type==='progress')progress(message.progress);
      else if(message.type==='result')finish(null,message.result);
      else if(message.type==='error')finish(message.error);
    }
    const timer=setTimeout(()=>finish('Распознавание заняло больше 90 секунд. Попробуйте уменьшить фото.'),90000);
    frame.onload=()=>{
      if(settled)return;
      canvas.toBlob(blob=>{
        if(settled)return;
        if(!blob){finish('Не удалось подготовить изображение');return;}
        frame.contentWindow.postMessage({id,type:'recognize',image:blob},location.origin);
      },'image/png');
    };
    frame.onerror=()=>finish('Не удалось загрузить распознавание. Повторите попытку.');
    window.addEventListener('message',receive);document.body.append(frame);
    return {promise,cancel:()=>finish('Распознавание отменено')};
  }
  window.App.receiptScanEngine={recognize};
})();
