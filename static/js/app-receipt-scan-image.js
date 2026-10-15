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
    for(let y=0;y<out.height;y++)for(let x=0;x<out.width;x++){
      const d=m[6]*x+m[7]*y+1;
      const sx=Math.max(0,Math.min(source.width-1,Math.round((m[0]*x+m[1]*y+m[2])/d)));
      const sy=Math.max(0,Math.min(source.height-1,Math.round((m[3]*x+m[4]*y+m[5])/d)));
      const si=(sy*source.width+sx)*4,di=(y*out.width+x)*4;
      const gray=.299*input[si]+.587*input[si+1]+.114*input[si+2];
      data.data[di]=data.data[di+1]=data.data[di+2]=Math.max(0,Math.min(255,(gray-128)*1.15+128));data.data[di+3]=255;
    }
    ctx.putImageData(data,0,0);return out;
  }
  window.App.receiptScanImage = {prepare};
})();
