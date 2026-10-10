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
            const exp=d.P.map(p=>[p.t.mine?'YOU':p.t.name,+p.g.toFixed(1)]);
            const give=row.querySelector('.tgx.gv').innerText,get=row.querySelector('.tgx.gt').innerText;
            const fl=d.flags.some(f=>(f.k==='over'&&f.who===R.me.rid)||f.k==='lop'||f.k==='inj')||R.thin(d).length>0;
            return{avgOk:Math.abs(+row.querySelector('.tq1 .tavg b').textContent-+d.avg.toFixed(1))<.051&&/AVG/.test(row.querySelector('.tq1 .tavg').innerText),
              bars:JSON.stringify(bars)===JSON.stringify(exp),give:/^GIVE/.test(give)&&me.give.every(id=>give.includes(nm(id))),get:/^GET/.test(get)&&me.get.every(id=>get.includes(nm(id))),
              warn:!!row.querySelector('.tdw0')===fl,h:row.getBoundingClientRect().height,dot:!!row.querySelector('.tdb')}})})()""")
        tag=f"[{W}]"
        chk(f"{tag} AVG +x/wk labeled and equal to the deal's average",r and all(x["avgOk"] for x in r),len(r))
        chk(f"{tag} one labeled bar per manager (YOU + each partner) with exact gains",all(x["bars"] for x in r))
        chk(f"{tag} GIVE ↗ lists what leaves your roster, GET ↙ what joins it",all(x["give"] and x["get"] for x in r))
        chk(f"{tag} amber ⚠ appears exactly when a material issue exists",all(x["warn"] for x in r))
        chk(f"{tag} no old dot/progress bar",not any(x["dot"] for x in r))
        if W<800:
            hs=[round(x["h"]) for x in r];chk(f"{tag} compact rows (~70–100px)",all(60<=h<=110 for h in hs),hs[:6])
            chk(f"{tag} one-row header on Lab (no empty second row)",pg.evaluate("Math.round(document.querySelector('header').getBoundingClientRect().height)")<=60,pg.evaluate("Math.round(document.querySelector('header').getBoundingClientRect().height)"))
        chk(f"{tag} ranking still by avg → least gain → yours",pg.evaluate("(()=>{const D=MV.res[MV.lg].deals,c=(x,y)=>Math.abs(x-y)>1e-9?x-y:0;for(let i=1;i<D.length;i++){const a=D[i-1],b=D[i];if((c(b.avg,a.avg)||c(b.min,a.min)||c(b.my,a.my))>0)return false}return true})()"))
        pg.locator("#moves .tdr").first.click();pg.wait_for_timeout(300)
        chk(f"{tag} similar packages collapsed by default",pg.evaluate("!document.querySelector('#moves .tsim')&&!!document.querySelector('#moves [data-sim]')"))
        pg.click("#moves [data-sim]");pg.wait_for_timeout(300);chk(f"{tag} …and open on tap",pg.evaluate("document.querySelectorAll('#moves .tsim .tsr').length")>=1)
        chk(f"{tag} expanded view stays inside the viewport",pg.evaluate("(()=>{const d=document.querySelector('#moves .tdd').getBoundingClientRect();return d.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth})()"))
        n=pg.evaluate("document.querySelectorAll('#moves .tbc').length");pg.locator("#moves .tbc").nth(1).click();pg.wait_for_timeout(300)
        chk(f"{tag} 'Best per partner' chips jump to that partner's deals",n>=2 and pg.evaluate("MV.tv==='p'&&document.querySelectorAll('#moves .tdl.sub .tdr').length>=1"),n)
        chk(f"{tag} no errors",not e,e[:2]);pg.close()
    mock.TRADES[0]=False;b.close()
print("FAILED:",fails)
