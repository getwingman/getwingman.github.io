"""v45: trade rows — partners, AVG, per-manager bars, GIVE/GET, one amber warning; compact phone rows"""
import sys,json,re;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
with sync_playwright() as p:
    b=p.chromium.launch();mock.TRADES[0]=True;mock.PREGAME[0]=True
    for W in (1500,390):
        pg=b.new_page(viewport={"width":W,"height":1000},is_mobile=W<800,has_touch=W<800);e=[];pg.on("pageerror",lambda x:e.append(str(x)))
        pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
        pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000);pg.evaluate("setTab('t')");pg.wait_for_timeout(9000)
        r=pg.evaluate("""(()=>{const R=MV.res[MV.lg],D=R.deals,nm=id=>pinfo(id).name.replace(/^(\\S)\\S*\\s+/,"$1. ");
          return[...document.querySelectorAll('#moves .tdl:not(.sub)>.tdr')].map(row=>{const d=D.find(x=>x.key===row.dataset.tx),me=d.P.find(p=>p.t.mine);
            const bars=[...row.querySelectorAll('.tbn2')].map(x=>[x.querySelector('.tbl2').textContent,+x.querySelector('b').textContent]);
            const exp=d.P.map(p=>[p.t.mine?'YOU':d.kind===2?'THEM':p.t.name,+p.g.toFixed(1)]);
            const widths=[...row.querySelectorAll('.tbb i')].map(i=>parseFloat(i.style.width)),wexp=d.P.map(p=>Math.max(4,p.g/MV.mxg*100));
            const give=row.querySelector('.tgx.gv').innerText,get=row.querySelector('.tgx.gt').innerText;
            const W=MV.warnsOf(d),hi=W.filter(x=>x.sev==='hi');
            return{avgOk:Math.abs(+row.querySelector('.tq1 .tavg b').textContent-+d.avg.toFixed(1))<.051&&/AVG/.test(row.querySelector('.tq1 .tavg').innerText),
              bars:JSON.stringify(bars)===JSON.stringify(exp),give:/^GIVE/.test(give)&&me.give.every(id=>give.includes(nm(id))),get:/^GET/.test(get)&&me.get.every(id=>get.includes(nm(id))),
              warn:!!row.querySelector('.tdw0.hi')===(hi.length>0)&&!!row.querySelector('.tdw0.lo')===(hi.length===0&&W.length>0),scale:widths.every((w,i)=>Math.abs(w-wexp[i])<.11),h:row.getBoundingClientRect().height,dot:!!row.querySelector('.tdb')}})})()""")
        tag=f"[{W}]"
        chk(f"{tag} AVG +x/wk labeled and equal to the deal's average",r and all(x["avgOk"] for x in r),len(r))
        chk(f"{tag} one labeled bar per manager (YOU / THEM or each 3-way partner) with exact gains",all(x["bars"] for x in r))
        chk(f"{tag} bars share one scale across every trade on the board",all(x["scale"] for x in r))
        chk(f"{tag} GIVE ↗ lists what leaves your roster, GET ↙ what joins it",all(x["give"] and x["get"] for x in r))
        chk(f"{tag} material risks → amber tag on the row; minor cautions → quiet ⓘ only",all(x["warn"] for x in r))
        chk(f"{tag} no old dot/progress bar",not any(x["dot"] for x in r))
        if W<800:
            hs=[round(x["h"]) for x in r];chk(f"{tag} compact rows (~70–100px)",all(60<=h<=110 for h in hs),hs[:6])
            chk(f"{tag} one-row header on Lab (no empty second row)",pg.evaluate("Math.round(document.querySelector('header').getBoundingClientRect().height)")<=60,pg.evaluate("Math.round(document.querySelector('header').getBoundingClientRect().height)"))
        chk(f"{tag} ranking still by avg → least gain → yours",pg.evaluate("(()=>{const D=MV.res[MV.lg].deals,c=(x,y)=>Math.abs(x-y)>1e-9?x-y:0;for(let i=1;i<D.length;i++){const a=D[i-1],b=D[i];if((c(b.avg,a.avg)||c(b.min,a.min)||c(b.my,a.my))>0)return false}return true})()"))
        if W>800:
            v=pg.evaluate("(()=>{const R=MV.res[MV.lg],ids=Object.keys(S.players).filter(id=>R.V(id)>0);const below=ids.find(id=>R.V(id)<=(R.repl[pinfo(id).pos]||0));const above=ids.find(id=>R.V(id)>(R.repl[pinfo(id).pos]||0)+1);return{below:below?R.aval(below):null,above:above?+(R.aval(above)-(R.V(above)-R.repl[pinfo(above).pos])).toFixed(6):null,repl:Object.keys(R.repl).length}})()")
            chk(f"{tag} trade value = value over the best free agent at the position (replaceable backups ≈ 0)",v["below"]==0 and v["above"]==0 and v["repl"]>=4,v)
            t=pg.evaluate("(()=>{const R=MV.res[MV.lg],d=R.deals[0];d.flags.push({k:'over',who:R.me.rid,d:6.2,sev:'hi'});MV.lastHtml='';mvRender();const r=document.querySelector('#moves .tdl>.tdr');const tag=r.querySelector('.tdw0.hi');const out=tag?tag.textContent:'';d.flags.pop();MV.lastHtml='';mvRender();return out})()")
            chk(f"{tag} a material overpay shows a short amber tag on the row",t.startswith("⚠ overpay"),t)
        pg.locator("#moves .tdr").first.click();pg.wait_for_timeout(300)
        chk(f"{tag} expanded view doesn't repeat the player transfers (2-way)",pg.evaluate("(()=>{const D=MV.res[MV.lg].deals.find(x=>x.key===MV.tx);return D.kind===3||!document.querySelector('#moves .tdd .tcyc,#moves .tdd .tfr2')})()"))
        chk(f"{tag} similar packages collapsed by default",pg.evaluate("!document.querySelector('#moves .tsim')&&!!document.querySelector('#moves [data-sim]')"))
        pg.click("#moves [data-sim]");pg.wait_for_timeout(300);chk(f"{tag} …and open on tap",pg.evaluate("document.querySelectorAll('#moves .tsim .tsr').length")>=1)
        chk(f"{tag} expanded view stays inside the viewport",pg.evaluate("(()=>{const d=document.querySelector('#moves .tdd').getBoundingClientRect();return d.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth})()"))
        rid=pg.evaluate("document.querySelectorAll('#moves .tbc')[2].dataset.bp");pg.locator("#moves .tbc").nth(2).click();pg.wait_for_timeout(300)
        f=pg.evaluate(f"(()=>{{const D=MV.res[MV.lg].deals,rows=[...document.querySelectorAll('#moves .tdl>.tdr')];return{{n:rows.length,all:rows.every(r=>D.find(d=>d.key===r.dataset.tx).rids.map(String).includes('{rid}')),on:document.querySelector('#moves .tbc.on').dataset.bp}}}})()")
        chk(f"{tag} partner chip filters the board to that partner (chip highlighted)",f["n"]>=1 and f["all"] and f["on"]==rid,f)
        pg.locator("#moves .tbc").first.click();pg.wait_for_timeout(300);chk(f"{tag} 'All' clears the partner filter",pg.evaluate("MV.pfil==null"))
        fo=pg.evaluate("""(()=>{const D=MV.res[MV.lg].deals,c={};let ok=true;[...document.querySelectorAll('#moves .tdl>.tdr')].forEach(r=>{const k=D.find(d=>d.key===r.dataset.tx).rids.slice().sort().join(',');c[k]=(c[k]||0)+1;if(c[k]>2&&!(MV.fold||{})[k])ok=false});return{ok,folds:document.querySelectorAll('#moves .tfold').length}})()""")
        chk(f"{tag} one partner never takes more than two rows before folding",fo["ok"],fo)
        if fo["folds"]:
            pg.locator("#moves .tfold").first.click();pg.wait_for_timeout(300);chk(f"{tag} fold line expands that partner's remaining packages",pg.evaluate("Object.values(MV.fold||{}).some(Boolean)"))
        g=pg.evaluate("(()=>{const D=MV.res[MV.lg].deals,G={};D.forEach(d=>(G[d.grp]=G[d.grp]||[]).push(d));return Object.values(G).every(g=>g.every(d=>d.rids.slice().sort().join()===g[0].rids.slice().sort().join()&&d.kind===g[0].kind))&&Object.values(G).some(g=>g.length>1)})()")
        chk(f"{tag} grouping: same partners + same headline player; variations exist",g)
        chk(f"{tag} no errors",not e,e[:2]);pg.close()
    mock.TRADES[0]=False;b.close()
print("FAILED:",fails)
