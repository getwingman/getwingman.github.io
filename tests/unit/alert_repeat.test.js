/* Wingman alert regressions: node tests/unit/alert_repeat.test.js index.html
   1) injury "cleared" alert must not repeat when two tabs (or a reload) disagree about a live return
   2) toast text must never show raw HTML when a win-% badge's tooltip contains " · " */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const src=fs.readFileSync(process.argv[2],"utf8");
const part=(a,b)=>{const i=src.indexOf(a),j=src.indexOf(b,i+a.length);assert(i>=0&&j>i,"Missing source block: "+a);return src.slice(i,j)};
let n=0;const ok=(msg,cond)=>{assert(cond,msg);n++};

/* ---------- injury alerts ---------- */
const injJS=part("function injCheck(){","function leadChange(){");
const retJS=part("/* players confirmed back in their game","function syncLiveInjuries(){");
const store={};   // one device's localStorage, shared by every tab
function tab(name){
  const toasts=[],T={st:"Questionable"};
  const S={players:{dj:{}},fx:{},liveInj:{},season:"2026",week:9,quietUntil:0,dirty:false};
  const lg={matchups:[{roster_id:2,starters:["dj"]}],mineRid:1};
  const ctx={S,vis:()=>[lg],pinfo:()=>({name:"Test Receiver",inj:T.st}),load:k=>store["lm_"+k]??null,save:(k,v)=>{store["lm_"+k]=v},
    esc:x=>String(x),toast:(k,h)=>toasts.push(h),playEventAnimation:()=>{},FX_DELAY:0,Date,JSON,Math,
    setTimeout:(f)=>f()};
  vm.createContext(ctx);vm.runInContext(retJS+injJS+";this.api={injCheck,liveRet,liveRetSave}",ctx);
  return{T,S,toasts,api:ctx.api,name}
}
const A=tab("A"),B=tab("B");
A.api.injCheck();B.api.injCheck();
ok("no alert while nothing changed",A.toasts.length+B.toasts.length===0);
A.T.st="";   // tab A saw a new play: player is back in the game; tab B (opened later) still says Questionable
for(let i=0;i<25;i++){A.api.injCheck();B.api.injCheck()}
ok("tab that saw the return announces it once",A.toasts.length===1&&/cleared/.test(A.toasts[0]));
ok("other tab never ping-pongs an alert",B.toasts.length===0);

/* one tab whose status flaps (e.g. a reload resets the live return) */
const C=tab("C");Object.keys(store).forEach(k=>delete store[k]);C.api.injCheck();
for(let i=0;i<12;i++){C.T.st=i%2?"Questionable":"";C.api.injCheck()}
ok("a flapping status alerts at most once per status",C.toasts.length<=2,C.toasts);
ok("the clear is still announced",C.toasts.some(t=>/cleared/.test(t)));

/* a confirmed return survives a reload for the same game + tag, and nothing else */
const D=tab("D");D.api.liveRetSave("dj","2026:9:e1|Questionable");
const D2=tab("D2");
ok("return kept across reloads",D2.api.liveRet().dj==="2026:9:e1|Questionable");
D2.S.week=10;D2.api.liveRetSave("x","2026:10:e2|Doubtful");
ok("returns from other weeks are pruned",!("dj" in D2.api.liveRet()));
const live=part("function syncLiveInjuries(){","const settled=");
ok("syncLiveInjuries restores a stored return for the same game and tag",/liveRet\(\)\[id\]===game\+"\|"\+tag/.test(live)&&/returned:kept/.test(live));

/* ---------- toast HTML ---------- */
const toastJS=part("/* split \"title · sub\"","function celebrate(");
const box={kids:[],prepend(d){this.kids.unshift(d)},get children(){return this.kids}};
const doc={createElement:()=>({classList:{add(){}},dataset:{},setAttribute(){},innerHTML:"",remove(){}})};
const tctx={$:()=>box,document:doc,quiet:()=>false,TACC:{},TPRI:{},sounds:{info(){}},setTimeout:()=>0,String,RegExp};
vm.createContext(tctx);vm.runInContext(toastJS+";this.api={toast,splitDot}",tctx);
const badge=`<span class="tsw dn" title="Win probability −6% · Home League" style="--k:0.20"></span>`;
ok("splitDot ignores separators inside a tag",tctx.api.splitDot(`A · ${badge} · B`).length===3);
tctx.api.toast("warn",`😬 Test Receiver TD (Rival)${badge}`,5000);
const h=box.kids[0].innerHTML;
ok("win-% badge stays a whole tag",h.includes(badge),h);
ok("no tag fragments leak as text",!/<div class="ts">[^<]*(style=|title=|&quot;|">)/.test(h)&&(h.match(/<span/g)||[]).length===(h.match(/<\/span>/g)||[]).length,h);
tctx.api.toast("warn",`😬 Opponent Test Receiver +6.4 · 24 yd catch from Passer`,3200);
const h2=box.kids[0].innerHTML;
ok("opponent scoring toast keeps title, points and play line",/<b>😬?\s*Opponent Test Receiver<\/b><em>\+6\.4<\/em>/.test(h2)||(/Opponent Test Receiver/.test(h2)&&/<em>\+6\.4<\/em>/.test(h2)&&/24 yd catch from Passer/.test(h2)),h2);
console.log(`PASS ${n} alert checks`);
