"""Geometry checks for actual controls; popovers and sticky footers are layers."""
CONTROL_METRICS = """root => {
  const card=root.querySelector('.modal-card')||root, cr=card.getBoundingClientRect();
  const controls=[...root.querySelectorAll('input:not([type=hidden]),select,textarea,button')]
    .filter(n=>n.checkVisibility() && n.getBoundingClientRect().width>0 && n.closest('.modal,dialog')===root);
  const id=n=>n.id||n.getAttribute('aria-label')||n.textContent.trim().slice(0,60)||n.className;
  const issues=[];
  for(const n of controls){
    const r=n.getBoundingClientRect();
    if(r.left<Math.max(0,cr.left)-1||r.right>Math.min(innerWidth,cr.right)+1)
      issues.push({type:'outside',id:id(n),x:r.left,width:r.width});
    if(n.tagName==='BUTTON'&&n.scrollWidth>n.clientWidth+2)
      issues.push({type:'clipped-button',id:id(n),width:r.width,content:n.scrollWidth});
    if(n.tagName==='SELECT'&&r.width<65)issues.push({type:'narrow-select',id:id(n),width:r.width});
  }
  const layer=n=>n.closest('.modal-footer,footer,.app-popover');
  for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
    const a=controls[i],b=controls[j],ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
    if(a.contains(b)||b.contains(a)||layer(a)!==layer(b))continue;
    if(a.closest('.date-input-wrap')?.contains(b))continue;
    if(a.closest('.money-input-wrap')?.contains(b))continue;
    if(Math.min(ar.right,br.right)-Math.max(ar.left,br.left)>2 && Math.min(ar.bottom,br.bottom)-Math.max(ar.top,br.top)>2)
      issues.push({type:'overlap',a:id(a),b:id(b),aRect:ar.toJSON(),bRect:br.toJSON()});
  }
  return {id:root.id,controls:controls.length,overflow:card.scrollWidth>card.clientWidth+1,issues};
}"""


def assert_controls_fit(root):
    root.page.evaluate('async()=>{await document.fonts.ready;await new Promise(requestAnimationFrame);}')
    result = root.evaluate(CONTROL_METRICS)
    assert not result['overflow'], result
    assert not result['issues'], result
    return result


def assert_text_fits(input_node, text):
    assert input_node.evaluate("""(n,text)=>{
      const s=getComputedStyle(n), c=document.createElement('canvas').getContext('2d');c.font=s.font;
      return n.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)>=c.measureText(text).width+12;
    }""", text), input_node.get_attribute('aria-label')
