"""v42: trade partner matrix + reasons, power movement, legible board, Edge pickups vs stashes, Survivor portfolio, Replay pregame, 6-tab phone bar"""
import sys,json;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
SV2="SV2testsheet00000000000001";PK2="PK2testsheet00000000000001"
EDGE="localStorage.setItem('lm_edge_ok','v1:a1cb100f57e971ca');"
def page(b,W,init="",pre=True):
    mock.PREGAME[0]=pre;pg=b.new_page(viewport={"width":W,"height":1000},is_mobile=W<800,has_touch=W<800);e=[];pg.on("pageerror",lambda x:e.append(str(x)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr');"+init);pg.goto(F);pg.wait_for_timeout(5000);return pg,e
with sync_playwright() as p:
    b=p.chromium.launch();mock.TRADES[0]=True
    # ---------- Lab ----------
    pg,e=page(b,1500);pg.evaluate("setTab('t')");pg.wait_for_timeout(9000)
    d=pg.evaluate("""(()=>{const R=MV.res[MV.lg];return{n:R.deals.length,ok:R.deals.every(x=>x.P.every(p=>p.g>.4)&&Math.abs(x.avg-x.P.reduce((s,p)=>s+p.g,0)/x.P.length)<1e-9),rows:document.querySelectorAll('#moves .tdr').length}})()""")
    chk("trades board: every deal improves every manager; avg = mean gain",d["n"]>=1 and d["ok"] and d["rows"]>=1,d)
    pg.locator("#moves .tdr").first.click();pg.wait_for_timeout(300)
    w=pg.evaluate("[...document.querySelectorAll('#moves .tdd .tpos')].map(x=>x.innerText.replace(/\\s+/g,' '))")
    chk("tap a deal → lineup changes for each side",len(w)>=2 and w[0].startswith("You"),w[:2])
    pg.locator("#moves .tdr").first.click();pg.wait_for_timeout(300);chk("tap again collapses",pg.evaluate("document.querySelectorAll('#moves .tdd').length")==0)
    t=pg.evaluate("(()=>{const lg=S.L.find(l=>l.id===MV.lg);return{n:document.querySelectorAll('#moves .pwt .ptr svg').length,last:Object.keys(lg.ptrend).every(k=>lg.ptrend[k][lg.ptrend[k].length-1]===lg.power[k].rank),len:Object.values(lg.ptrend)[0].length,wk:lg.pweeks.length}})()")
    chk("power movement: trend line per manager, last point = official season rank",t["n"]==12 and t["last"] and t["len"]==t["wk"]>=2,t)
    mv=pg.evaluate("[...document.querySelectorAll('#moves .pmvc small')].map(x=>x.innerText)")
    chk("risers / fallers / roster-vs-results chips",any("riser" in x.lower() for x in mv) and any("faller" in x.lower() for x in mv),mv)
    lz=pg.evaluate("(()=>{const b=document.querySelector('#moves .iqr b'),r=b.getBoundingClientRect(),c=b.closest('.iqr').getBoundingClientRect();const o=[...document.querySelectorAll('#moves .pwt td')].filter(td=>td.scrollWidth>td.clientWidth+1).length;return{fs:parseFloat(getComputedStyle(b).fontSize),fits:r.width<=c.width,trunc:o}})()")
    chk("board legibility: IQ number fits its ring, no truncated cells",lz["fs"]<=11 and lz["fits"] and lz["trunc"]==0,lz)
    chk("🏆 odds have a methodology tip",pg.evaluate("!!document.querySelector('#moves .pwt .odn[data-tip*=\"simulations\"]')"))
    chk("no errors (Lab)",not e,e[:2]);pg.close()
    # ---------- Edge pickups ----------
    pg,e=page(b,1500,EDGE);pg.evaluate("setTab('e')");pg.wait_for_timeout(9000)
    ed=pg.evaluate("""(()=>{const R=MV.res[S.L[0].id],sec=[...document.querySelectorAll('#moves .edcol')][0];const h=[...sec.querySelectorAll('.svh')].map(x=>x.innerText);
      return{h,real:R.adds.filter(x=>x.g>=.5).length,cards:sec.querySelectorAll('.adds .add').length,stash:R.adds.filter(x=>x.g<.5).length,wl:sec.querySelectorAll('.wl .wlr').length,zero:[...sec.querySelectorAll('.adds .gain')].some(g=>/\\+0\\.0/.test(g.textContent))}})()""")
    chk("Edge: real upgrades (≥0.5) separate from watchlist/stashes, no +0.0 'best pickup'",ed["cards"]==ed["real"] and ed["wl"]==ed["stash"] and not ed["zero"],ed)
    chk("Edge: leagues side by side",pg.evaluate("document.querySelectorAll('#moves .edcol').length")==2)
    chk("no errors (Edge)",not e,e[:2]);pg.close()
    # ---------- Survivor portfolio ----------
    conns=json.dumps([{"key":"sleeper:x","p":"sleeper","username":"xParRaidr"},{"key":"survivor:"+SV2,"p":"survivor","sheet":SV2},{"key":"pickem:"+PK2,"p":"pickem","sheet":PK2}])
    pg,e=page(b,1500,"localStorage.setItem('lm_conns',%r);"%conns+EDGE,pre=False);pg.evaluate("SV.open.plan=true;setTab('s')");pg.wait_for_timeout(5000)
    sv=pg.evaluate("""(()=>{const c=[...document.querySelectorAll('#surv .svplan')].map(x=>({t:x.querySelector('.svph b').textContent,stk:x.classList.contains("stkd"),ups:x.querySelectorAll('.ups').length,rows:x.querySelectorAll('.svpt').length}));
      return{c,up:document.querySelectorAll('#surv .upt tbody tr').length,title:[...document.querySelectorAll('#surv .svh')].map(x=>x.innerText.split('\\n')[0]).find(x=>/planner/.test(x))}})()""")
    chk("portfolio planner: Most lives + Portfolio cards, 💥 upset cost on every team",any(c["t"]=="Portfolio" for c in sv["c"]) and all(c["ups"]==c["rows"] for c in sv["c"]),sv)
    chk("stacking is obvious: all lives on one team → ⚠ stacked + upset table",any(c["stk"] for c in sv["c"] if c["t"]=="Most lives") and sv["up"]>=2,sv)
    pf=pg.evaluate("""(()=>{const c=[...document.querySelectorAll('#surv .svplan')];const kv=x=>{const m=x.querySelector('.svph span').textContent.match(/keep ≥1 (\\d+)/);return m?+m[1]:null};return c.map(kv)})()""")
    chk("portfolio keeps ≥1 life more often than the stacked plan",pf[1]>pf[0],pf)
    tk=pg.evaluate("(()=>{const i=document.querySelector('#surv .tok .tokl');if(!i)return null;const cs=getComputedStyle(i),t=i.closest('.tok').getBoundingClientRect(),r=i.getBoundingClientRect();return{w:r.width,pos:cs.position,dx:Math.abs((r.left+r.width/2)-(t.left+t.width/2)),dy:Math.abs((r.top+r.height/2)-(t.top+t.height/2))}})()")
    chk("hero tokens: logo fills the circle, centered",tk and tk["w"]>=34 and tk["pos"]=="static" and tk["dx"]<1.5 and tk["dy"]<1.5,tk)
    ov=pg.evaluate("[...document.querySelectorAll('#surv .rvo')].map(x=>x.innerText)")
    chk("rival overlap never shows 0% when picks are unknown",all(("not visible" in x) or ("%" in x and not x.startswith("0%")) or x.startswith("0%")==False for x in ov) and not any(x.startswith("0% same") for x in ov if "not visible" in x),ov[:3])
    chk("no errors (Survivor)",not e,e[:2]);pg.close()
    # ---------- Replay pregame + phone tab bar ----------
    pg,e=page(b,390,"localStorage.setItem('lm_conns',%r);"%conns+EDGE);pg.evaluate("updateNav();setTab('f')");pg.wait_for_timeout(3000)
    rd=pg.evaluate("({kf:document.querySelectorAll('#field .kfr').length,mm:document.querySelectorAll('#field .mm').length,h2:document.querySelectorAll('#field .h2c').length})")
    chk("Replay pregame: calm kickoff schedule, no empty field rectangles",rd["kf"]>=1 and rd["mm"]==0 and rd["h2"]==0,rd)
    pg.set_viewport_size({"width":344,"height":800});pg.wait_for_timeout(400)
    tb=pg.evaluate("""(()=>{const bs=[...document.querySelectorAll('header .tabs > .tb')].filter(b=>getComputedStyle(b).display!=='none');return{n:bs.length,labels:bs.map(b=>b.innerText.replace(/\\s+/g,' ').trim()),ov:bs.some(b=>{const l=b.querySelector('.tbl');return l.scrollWidth>l.clientWidth||b.getBoundingClientRect().right>344}),sw:document.documentElement.scrollWidth}})()""")
    chk("phone tab bar fits 6 tabs at 344px: Matchups, Replay, Lab, Edge, Survivor, Pick'em",tb["n"]==6 and not tb["ov"] and tb["sw"]<=344,tb)
    chk("no errors (Replay/phone)",not e,e[:2]);pg.close()
    mock.TRADES[0]=False;mock.PREGAME[0]=False;b.close()
print("FAILED:",fails)
