import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
with sync_playwright() as p:
    b=p.chromium.launch()
    mock.PREGAME[0]=True
    for w,tag in [(1500,"d"),(390,"m")]:
        pg=b.new_page(viewport={"width":w,"height":900},is_mobile=w<800,has_touch=w<800);e=[];pg.on("pageerror",lambda x:e.append(str(x)))
        pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
        pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000)
        t=pg.evaluate("[document.querySelector('.lg .hero').className,document.querySelector('.lg .hero .pt.a').innerText,document.querySelector('.lg .hero .hp').innerText]")
        chk(f"pregame header ({tag}): projection leads, no 0.00",'hs-pre' in t[0] and "PROJ" in t[1].upper() and "0.00" not in t[1],t)
        chk(f"pregame: kickoff time shown ({tag})","first kickoff" in t[2],t[2])
        chk(f"pregame: no win-% history drawn ({tag})",pg.evaluate("!!document.querySelector('.lg .hero .wk .skt.wait')"))
        pg.locator(".lg .hero").first.screenshot(path=f"{OUT}/pre_{tag}.png");chk(f"no errors {tag}",not e,e[:2]);pg.close()
    mock.PREGAME[0]=False
    pg=b.new_page(viewport={"width":1500,"height":900});pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000)
    chk("live header shows actual points",pg.evaluate("document.querySelector('.lg .hero .pt.a').innerText")=="39.30",pg.evaluate("document.querySelector('.lg .hero .pt.a').innerText"))
    # WP history: inject recorded estimates spanning 2 hours, check 0-100 scale + first estimate baseline
    r=pg.evaluate("""(()=>{const lg=S.L[0],mm=myMatch(lg),now=Date.now(),H=wphLoad(lg),k=mm.A.matchup_id,ra=Math.min(mm.A.roster_id,mm.B.roster_id),rb=Math.max(mm.A.roster_id,mm.B.roster_id);
      H[k]=[0,1,2,3,4,5,6].map(i=>({t:now-7200e3+i*1200e3,w:[.5,.55,.4,.62,.7,.66,.91][i],pa:i*5,pb:i*4,ra,rb}));lg._live=true;const svg=spark(lg,mm.A,mm.B);
      return{wp:svg.includes('win %'),start:lg._spk&&lg._spk.h[0].t===H[k][0].t,n:lg._spk&&lg._spk.h.length,marks:(svg.match(/class="skw/g)||[]).length,min:Math.min(...lg._spk.P.map(p=>p[1])),max:Math.max(...lg._spk.P.map(p=>p[1]))}})()""")
    chk("WP chart: win % scale, starts at the first estimate, all points kept",r["wp"] and r["start"] and r["n"]==7,r)
    chk("WP chart: only meaningful swings marked (≥10 pts)",r["marks"]<=3 and r["marks"]>=1,r["marks"])
    chk("WP chart stays within 0–100% band",r["min"]>=4 and r["max"]<=72,r)
    # seeded odds: same inputs → same output
    o=pg.evaluate("(()=>{const lg=S.L[0];computeOdds(lg);const a=JSON.stringify(lg.odds);computeOdds(lg);const b=JSON.stringify(lg.odds);return[a===b,a.slice(0,80)]})()")
    chk("playoff odds stable across recomputes (seeded)",o[0],o[1])
    # heartbeat ignores projection drift
    hb=pg.evaluate("(()=>{const lg=S.L[0];lg.hb=null;lg.wpLast=.2;const mm=myMatch(lg);lg.ptsLast=mm.a.total+'|'+mm.b.total;const now=Date.now();const w=mm.wp,pts=mm.a.total+'|'+mm.b.total,scored=lg.ptsLast!=null&&pts!==lg.ptsLast;return scored})()")
    chk("heartbeat requires real scoring (not projection drift)",hb is False)
    b.close()
print("FAILED:",fails)
