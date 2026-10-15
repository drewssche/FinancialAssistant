(() => {
  // Projective transform from the output rectangle into four user-selected corners.
  function transform(points, width, height) {
    const from = [[0,0],[width,0],[width,height],[0,height]], a = [];
    from.forEach(([x,y], i) => {
      const [u,v] = points[i];
      a.push([x,y,1,0,0,0,-u*x,-u*y,u], [0,0,0,x,y,1,-v*x,-v*y,v]);
    });
    for (let c=0;c<8;c++) {
      let pivot=c; for(let r=c+1;r<8;r++) if(Math.abs(a[r][c])>Math.abs(a[pivot][c]))pivot=r;
      [a[c],a[pivot]]=[a[pivot],a[c]];
      if(Math.abs(a[c][c])<1e-9)throw new Error('Разместите углы по краям чека');
      const n=a[c][c]; for(let k=c;k<9;k++)a[c][k]/=n;
      for(let r=0;r<8;r++)if(r!==c){const f=a[r][c];for(let k=c;k<9;k++)a[r][k]-=f*a[c][k];}
    }
    return a.map(row=>row[8]);
  }
  function prepare(source, normalized) {
    const points = normalized.map(([x,y]) => [x*source.width,y*source.height]);
    const cross = points.map((p,i) => {const q=points[(i+1)%4],r=points[(i+2)%4];return (q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0]);});
    if(cross.some(v=>v<=0))throw new Error('Углы должны идти по краям одного чека, без пересечений');
    const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
    const w=(distance(points[0],points[1])+distance(points[2],points[3]))/2;
    const h=(distance(points[0],points[3])+distance(points[1],points[2]))/2;
    if(w<60||h<80)throw new Error('Область слишком мала — выберите весь чек');
    const scale=Math.min(Math.max(1,1000/w),1600/w,3600/h,Math.sqrt(4000000/(w*h)));
    const out=document.createElement('canvas');out.width=Math.round(w*scale);out.height=Math.round(h*scale);
    const m=transform(points,out.width,out.height), ctx=out.getContext('2d'), data=ctx.createImageData(out.width,out.height);
    const input=source.getContext('2d').getImageData(0,0,source.width,source.height).data;
    const grayAt=(x,y)=>{const i=(y*source.width+x)*4,alpha=input[i+3]/255;return (.299*input[i]+.587*input[i+1]+.114*input[i+2])*alpha+255*(1-alpha);};
    const gray=new Float32Array(out.width*out.height);
    for(let y=0;y<out.height;y++)for(let x=0;x<out.width;x++){
      const d=m[6]*x+m[7]*y+1;
      const sx=Math.max(0,Math.min(source.width-1,(m[0]*x+m[1]*y+m[2])/d));
      const sy=Math.max(0,Math.min(source.height-1,(m[3]*x+m[4]*y+m[5])/d));
      const x0=Math.floor(sx),y0=Math.floor(sy),x1=Math.min(x0+1,source.width-1),y1=Math.min(y0+1,source.height-1),fx=sx-x0,fy=sy-y0;
      gray[y*out.width+x]=(grayAt(x0,y0)*(1-fx)+grayAt(x1,y0)*fx)*(1-fy)+(grayAt(x0,y1)*(1-fx)+grayAt(x1,y1)*fx)*fy;
    }
    // Flatten broad shadows before thresholding; never change recognized characters.
    const stride=out.width+1, integral=new Float64Array(stride*(out.height+1));
    for(let y=0;y<out.height;y++){let sum=0;for(let x=0;x<out.width;x++){sum+=gray[y*out.width+x];integral[(y+1)*stride+x+1]=integral[y*stride+x+1]+sum;}}
    const radius=Math.max(12,Math.round(out.width*.025));
    for(let y=0;y<out.height;y++)for(let x=0;x<out.width;x++){
      const left=Math.max(0,x-radius),right=Math.min(out.width,x+radius+1),top=Math.max(0,y-radius),bottom=Math.min(out.height,y+radius+1);
      const mean=(integral[bottom*stride+right]-integral[top*stride+right]-integral[bottom*stride+left]+integral[top*stride+left])/((right-left)*(bottom-top));
      const value=Math.max(0,Math.min(255,235+(gray[y*out.width+x]-mean)*2)),di=(y*out.width+x)*4;
      data.data[di]=data.data[di+1]=data.data[di+2]=value;data.data[di+3]=255;
    }
    ctx.putImageData(data,0,0);
    // Paper edges and printed baselines need not be parallel. Align text by ink
    // projection, independently of the user's perspective rectangle.
    const samples=[], step=3;
    for(let y=Math.floor(out.height*.04);y<out.height*.70;y++)for(let x=Math.floor(out.width*.07);x<out.width*.93;x+=step){
      if(data.data[(y*out.width+x)*4]<150)samples.push([x-out.width/2,y]);
    }
    const score=slope=>{const bins=new Uint32Array(out.height+out.width);for(const [x,y] of samples)bins[Math.round((y+slope*x+out.width/2)/3)]++;let value=0;for(const n of bins)value+=n*n;return value;};
    const base=score(0);let best=base,slope=0;
    for(let i=-48;i<=48;i++){const candidate=i*.0025,value=score(candidate);if(value>best){best=value;slope=candidate;}}
    if(Math.abs(slope)<.005||best<base*1.02)return out;
    const pad=Math.ceil(Math.abs(slope)*out.width/2)+4,aligned=document.createElement('canvas');
    const fit=Math.min(1,3600/(out.height+pad*2),Math.sqrt(4000000/(out.width*(out.height+pad*2))));
    aligned.width=Math.floor(out.width*fit);aligned.height=Math.floor((out.height+pad*2)*fit);
    const ac=aligned.getContext('2d');ac.fillStyle='white';ac.fillRect(0,0,aligned.width,aligned.height);
    ac.setTransform(fit,slope*fit,0,fit,0,(pad-slope*out.width/2)*fit);ac.drawImage(out,0,0);
    return aligned;
  }
  window.App.receiptScanImage = {prepare};
})();
