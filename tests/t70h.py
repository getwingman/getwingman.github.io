def swipe(pg,sel,dx):
    pg.evaluate("""([sel,dx])=>{const el=document.querySelector(sel);const r=el.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+Math.min(r.height/2,20);
     const mk=(t,X)=>new Touch({identifier:1,target:el,clientX:X,clientY:y});
     el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[mk(0,x)],changedTouches:[mk(0,x)]}));
     el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[mk(0,x+dx)]}))}""",[sel,dx])
