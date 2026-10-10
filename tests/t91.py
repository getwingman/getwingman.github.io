"""ideal lineup: signals, locks, optimality, rebuild on every visit"""
import sys,itertools;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
with sync_playwright() as p:
    b=p.chromium.launch()
    for pre,W in [(True,1500),(False,1500),(True,390)]:
        mock.PREGAME[0]=pre;pg=b.new_page(viewport={"width":W,"height":1000},is_mobile=W<800,has_touch=W<800);e=[];pg.on("pageerror",lambda x:e.append(str(x)))
        pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
        pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000)
        tag=("pregame" if pre else "live")+(" phone" if W<800 else "")
        # Drake London (Q) missed practice; Mark Andrews ruled Out
        pg.evaluate("S.players['205'].practice_participation='DNP';S.players['204'].injury_status='Out';S.pc={}")
        if pre and W>800:
            pg.evaluate("setTab('e')");pg.wait_for_timeout(300)
            chk(f"[{tag}] Edge is locked: password prompt, no Edge content",pg.is_visible("#elkp") and pg.evaluate("S.tab")!="e" and pg.evaluate("document.querySelector('header .tb[data-t=e]').style.display")=="none")
            pg.fill("#elkp","Edge ");pg.click("#elkf button");pg.wait_for_timeout(500)
            chk(f"[{tag}] password 'edge' unlocks; Edge tab appears",pg.evaluate("S.tab")=="e" and pg.evaluate("document.querySelector('header .tb[data-t=e]').style.display")=="")
            chk(f"[{tag}] only a hash token is stored (no password)",pg.evaluate("localStorage.getItem('lm_edge_ok')")=="v1:a1cb100f57e971ca" and "edge" not in pg.evaluate("JSON.stringify(Object.values(localStorage))").lower().replace("lm_edge",""))
        else:pg.evaluate("localStorage.setItem('lm_edge_ok','v1:a1cb100f57e971ca');updateNav()")
        pg.evaluate("MV.open.ideal=true;setTab('e')");pg.wait_for_timeout(7000)
        R=pg.evaluate("(()=>{const R=IL.res[MV.lg];if(!R||!R.rec)return R;return{rec:R.rec.map(x=>[x.sl,x.id,!!x.lock]),ins:R.ins.map(x=>x.id),outs:R.outs,cur:R.curPts,best:R.recPts,at:R.at,sig205:(R.info['205']||{}).sig,v205:(R.info['205']||{}).v,v2005:(R.info['2005']||{}).v,g:Object.values(R.info).map(i=>!!i.g&&i.g.implied!=null)}})()")
        chk(f"[{tag}] ideal lineup card renders",pg.evaluate("!!document.querySelector('#moves .ilg')") and R and "rec" in R,R if not R or "rec" not in R else "")
        if not R or "rec" not in R:pg.close();continue
        if pre:
            chk(f"[{tag}] DNP questionable player discounted (London 11.5 → ≤7)",R["v205"]<=7.5 and any("DNP" in s[0] for s in R["sig205"]),[R["v205"],R["sig205"]])
            chk(f"[{tag}] Vegas implied totals used",any(R["g"]),R["g"][:4])
            chk(f"[{tag}] DNP starter sat, bench WR starts",("205" in R["outs"]) and "2005" in [x[1] for x in R["rec"]],R)
            chk(f"[{tag}] Out player with no healthy backup is flagged to replace",pg.evaluate("[...document.querySelectorAll('#moves .edcol:first-child .ilr.dead')].length")==1)
            chk(f"[{tag}] nothing locked before kickoff",not any(x[2] for x in R["rec"]))
            # optimality: brute force over the same adjusted values (pure expected points, no tilt when wp unknown/neutral)
            bf=pg.evaluate("""(()=>{const R=IL.res[MV.lg],I=R.info,ids=Object.keys(I),slots=R.rec.map(x=>x.sl);let best=-1;const el=s=>ELIG2[s]||[s];
              const rec=(i,used,s)=>{if(i===slots.length){best=Math.max(best,s);return}let any=false;for(const id of ids){if(used.has(id))continue;if(!eligOf(id).some(z=>el(slots[i]).includes(z)))continue;any=true;used.add(id);rec(i+1,used,s+I[id].vt);used.delete(id)}if(!any)rec(i+1,used,s)};rec(0,new Set(),0);
              return[best,R.rec.reduce((s,x)=>s+(x.id?I[x.id].vt:0),0)]})()""")
            chk(f"[{tag}] recommended lineup = brute-force optimum",abs(bf[0]-bf[1])<1e-6,bf)
            # every visit rebuilds
            at0=R["at"];pg.evaluate("setTab('m')");pg.wait_for_timeout(500);pg.evaluate("setTab('e')");pg.wait_for_timeout(4000)
            at1=pg.evaluate("IL.res[MV.lg].at");chk(f"[{tag}] rebuilt on revisit",at1>at0,(at0,at1))
        else:
            locked=[x for x in R["rec"] if x[2]];chk(f"[{tag}] started games are locked in place",len(locked)>=3,locked)
        if W<800:chk(f"[{tag}] no horizontal scroll",pg.evaluate("document.documentElement.scrollWidth")<=W)
        if pre and W>800:
            pg.evaluate("edgeLock()");pg.wait_for_timeout(300)
            chk(f"[{tag}] 🔒 lock hides Edge again",pg.evaluate("S.tab")!="e" and pg.evaluate("document.querySelector('header .tb[data-t=e]').style.display")=="none" and not pg.evaluate("localStorage.getItem('lm_edge_ok')"))
            pg.evaluate("localStorage.setItem('lm_edge_ok','v1:a1cb100f57e971ca');updateNav();setTab('e')");pg.wait_for_timeout(1500)
        pg.locator("#moves .card.svc").first.screenshot(path=f"{OUT}/ideal_{'pre' if pre else 'live'}_{W}.png")
        chk(f"[{tag}] no errors",not e,e[:2]);pg.close()
    mock.PREGAME[0]=False;b.close()
print("FAILED:",fails)
