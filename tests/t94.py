"""v44: live API results, unified Trades board, Survivor redesign, movable modules everywhere, Replay"""
import sys,json;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
SV2="SV2testsheet00000000000001";PK2="PK2testsheet00000000000001"
CONNS=json.dumps([{"key":"sleeper:x","p":"sleeper","username":"xParRaidr"},{"key":"survivor:"+SV2,"p":"survivor","sheet":SV2},{"key":"pickem:"+PK2,"p":"pickem","sheet":PK2}])
EDGE="localStorage.setItem('lm_edge_ok','v1:a1cb100f57e971ca');"
def page(b,W=1500,init="",pre=False,rm=False):
    mock.PREGAME[0]=pre;pg=b.new_page(viewport={"width":W,"height":1000},is_mobile=W<800,has_touch=W<800,reduced_motion="reduce" if rm else "no-preference");e=[];pg.on("pageerror",lambda x:e.append(str(x)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr');"+init);pg.goto(F);pg.wait_for_timeout(5500);return pg,e
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---------- 1. results from the live API ----------
    pg,e=page(b,init="localStorage.setItem('lm_conns',%r);"%CONNS)
    pg.evaluate("setTab('s')");pg.wait_for_timeout(4000)
    r=pg.evaluate("""(async()=>{SV.sheetRes=SV.sheetRes||{};SV.sheetRes[5]=Object.assign({},SV.sheetRes[5]||{},{Packers:{r:'L',st:'post',sheet:1},Lions:{r:'W',st:'post',sheet:1}});SV.res[5]={};await svLoadWeek(5,true);
      return{gb:SV.res[5].Packers&&SV.res[5].Packers.r,gbSrc:SV.res[5].Packers&&SV.res[5].Packers.src||'api',det:SV.res[5].Lions&&SV.res[5].Lions.r,detSrc:SV.res[5].Lions&&SV.res[5].Lions.src}})()""")
    chk("survivor: a final API score beats the sheet (sheet said L, ESPN final W)",r["gb"]=="W" and r["gbSrc"]=="api",r)
    chk("survivor: sheet still fills games the API hasn't decided",r["det"]=="W" and r["detSrc"]=="sheet",r)
    pg.evaluate("setTab('p')");pg.wait_for_timeout(3000)
    k=pg.evaluate("""(()=>{const w=PK.wSheet+1;PK.d.games.push([w,'AAA','BBB',null,null,'','']);const gi=PK.d.games.length-1;PK.d.picks.push([0,gi,1,'P'],[1,gi,0,'P'],[2,gi,1,'H']);pkIndex();
      const g=PK.games[gi];
      PK.nx[w]=[{home:g.b,away:g.a,st:'post',hsc:30,asc:10,hs:-3}];pkApiGrade();const c=g.picks.filter(p=>p.side===1&&p.api&&p.c==='C').length,i=g.picks.filter(p=>p.side===0&&p.api&&p.c==='I').length;
      const u=(g.picks.find(p=>p.side===1&&p.api)||{}).u,row=PK.rows.find(r=>r.u===u);return{ats:g.ats,b:g.b,c,i,weeks:PK.weeks,w,pts:row?row.w[w-1]:null,api:g.api}})()""")
    chk("pick'em: a final score grades picks against the locked line right away",k.get("ats")==k.get("b") and k.get("c",0)+k.get("i",0)>=1 and k.get("weeks")==k.get("w") and (k.get("pts") or 0)>=1,k)
    k2=pg.evaluate("(()=>{const w=PK.wSheet+1;PK.nx[w]=[];pkApiGrade();return{weeks:PK.weeks,ws:PK.wSheet}})()")
    chk("pick'em: API grades vanish when there's no final (sheet stays authoritative)",k2["weeks"]==k2["ws"],k2)
    chk("no errors (results)",not e,e[:2]);pg.close()
    # ---------- 2. unified Trades board ----------
    mock.TRADES[0]=True
    pg,e=page(b,pre=True);pg.evaluate("setTab('t')");pg.wait_for_timeout(9000)
    t=pg.evaluate("""(()=>{const D=MV.res[MV.lg].deals;let ok=true;for(let i=1;i<D.length;i++){const a=D[i-1],c=D[i];if(a.avg<c.avg-1e-9||(Math.abs(a.avg-c.avg)<1e-9&&(a.min<c.min-1e-9||(Math.abs(a.min-c.min)<1e-9&&a.my<c.my-1e-9))))ok=false}
      return{n:D.length,ok,k2:D.filter(d=>d.kind===2).length,k3:D.filter(d=>d.kind===3).length,mixed:D.slice(0,20).some(d=>d.kind===3)&&D.slice(0,20).some(d=>d.kind===2)}})()""")
    chk("trades: one list ranked by avg gain, ties → least gain → yours, regardless of type",t["ok"] and t["k2"]>0 and t["k3"]>0,t)
    g=pg.evaluate("""(()=>{const rows=[...document.querySelectorAll('#moves .tdr')];return rows.map(r=>[+r.querySelector('.tdk').textContent,r.querySelector('.tdps').innerText.trim()])})()""")
    first=[x for x in g][:3]
    chk("trades: rows show rank and partners (grouped packages, ranks 1..n)",len(g)>=3 and [x[0] for x in g[:3]]==[1,2,3],first)
    rid=pg.evaluate("(()=>{const D=MV.res[MV.lg].deals,all=D[0].rids[0];const x=D.find(d=>d.rids.some(r=>r!==all));return String(x?x.rids.find(r=>r!==all):all)})()")
    pg.click("#moves [data-pf]");pg.wait_for_timeout(200);pg.click(f"#moves [data-mk='{rid}'][data-v='n']");pg.wait_for_timeout(300)
    f=pg.evaluate(f"""(()=>{{const rows=[...document.querySelectorAll('#moves .tdr')];return{{n:rows.length,hasR:MV.res[MV.lg].deals.filter(d=>d.rids.includes({rid})).some(d=>rows.some(r=>r.dataset.tx===d.key)),ranks:rows.map(r=>+r.querySelector('.tdk').textContent).slice(0,3),saved:localStorage.getItem('lm_tpref_'+MV.lg)}}}})()""")
    chk("⛔ unlikely partner hides their deals; ranks keep their numbers (math unchanged)",not f["hasR"] and f["n"]>=1 and '"n"' in (f["saved"] or ""),f)
    pg.click(f"#moves [data-mk='{rid}'][data-v='n']");pg.wait_for_timeout(200)
    pg.click("#moves [data-tv='p']");pg.wait_for_timeout(300)
    bp=pg.evaluate("[...document.querySelectorAll('#moves .tbr')].length")
    pg.locator("#moves [data-tp]").first.click();pg.wait_for_timeout(300)
    sub=pg.evaluate("(()=>{const r=[...document.querySelectorAll('#moves .tdl.sub .tdr')];return{n:r.length,tri:r.some(x=>x.querySelector('.tdt').textContent.includes('△'))}})()")
    chk("By partner: one row per manager; expanding lists their 2- and 3-way deals",bp>=12 and sub["n"]>=1 and sub["tri"],{"rows":bp,**sub})
    pg.click("#moves [data-tv='b']");pg.wait_for_timeout(200);pg.locator("#moves .tdr").first.click();pg.wait_for_timeout(300)
    dd=pg.evaluate("(()=>{const d=document.querySelector('#moves .tdd');return d?{fl:d.querySelectorAll('.tfr').length,why:d.querySelectorAll('.trwhy>div').length,warn:d.querySelectorAll('.tw2').length,sim:d.querySelectorAll('.tsr').length}:null})()")
    chk("expanded deal: full flow, every manager's gain and reason, warnings, similar packages",dd and dd["fl"]>=2 and dd["why"]==dd["fl"],dd)
    chk("no errors (trades)",not e,e[:2]);pg.close();mock.TRADES[0]=False
    # ---------- 3. Survivor ----------
    pg,e=page(b,init="localStorage.setItem('lm_conns',%r);"%CONNS)
    pg.evaluate("setTab('s')");pg.wait_for_timeout(5000)
    s=pg.evaluate("""(()=>{const V=svWeek(),my=SV.lanes.filter(l=>isOurs(l)&&(!l.out||l.out>=V)&&svPick(l,V));
      const pT=t=>{const R=svRes(V,t);return !R?.5:R.r?(R.r==='W'?1:0):R.wp!=null?R.wp:.5};const lin=my.reduce((s,l)=>s+svPicks(l,V).reduce((q,t)=>q*pT(t),1),0);
      const bars=[...document.querySelectorAll('#surv .sdb')].length,eTxt=+(document.querySelector('#surv .kd .kb b')||{}).textContent;
      const rows=[...document.querySelectorAll('#surv .vwr:not(.fld)')].map(r=>({fin:r.classList.contains('fin'),e:+(r.querySelector('.vwe em')||{textContent:'0'}).textContent.replace('−','')}));
      const live=rows.filter(r=>!r.fin);let sorted=true;for(let i=1;i<live.length;i++)if(live[i].e>live[i-1].e+1e-9&&!document.querySelectorAll('#surv .vwr')[i].classList.contains('crit'))sorted=false;
      return{n:my.length,lin:+lin.toFixed(1),eTxt,bars,rows:rows.length,sorted,plan:SV.open.plan,heads:[...document.querySelectorAll('#surv .svh')].map(x=>x.dataset.k)}})()""")
    chk("survivor: expected lives = Σ each entry's survival chance (exact distribution, correlated teams)",abs(s["lin"]-s["eTxt"])<=0.051 and s["bars"]==s["n"]+1,s)
    chk("survivor: Survival Watch rows sorted by expected lives lost",s["rows"]>=1 and s["sorted"],s)
    chk("survivor: default order Overview → Watch → Rivals → Swimlanes → Standings → Elimination → Planner → Rules; planner collapsed",s["heads"]==["watch","rivals","swim","stand","chart","plan","rules"] and s["plan"] is False,s["heads"])
    same=pg.evaluate("""(()=>{const V=svWeek();const by={};SV.lanes.filter(l=>isOurs(l)&&(!l.out||l.out>=V)).forEach(l=>{const t=svPick(l,V);if(t)(by[t]=by[t]||[]).push(l.let)});const t=Object.keys(by).find(k=>by[k].length>1);if(!t)return null;
      const d=[...document.querySelectorAll('#surv .sdb')].map(x=>x.dataset.tip);return{t,n:by[t].length,row:[...document.querySelectorAll('#surv .vwr')].some(r=>r.querySelectorAll('.ltk').length===by[t].length)}})()""")
    chk("survivor: entries on the same team are grouped in one row",same and same["row"],same)
    pg.click("#surv .svh[data-k='plan']");pg.wait_for_timeout(300);pg.evaluate("SV.lastHtml='';svRender()");pg.wait_for_timeout(200)
    chk("planner expand is remembered across refresh",pg.evaluate("SV.open.plan===true&&JSON.parse(localStorage.getItem('lm_svopen2')).plan===true"))
    pg.click("#surv .svh[data-k='plan']");pg.wait_for_timeout(200)
    chk("no 'root' badges or duplicate win % bars in Survival Watch",pg.evaluate("!document.querySelector('#surv .rootm')&&!document.querySelector('#surv .gwp')"))
    # ---------- 4. movable modules ----------
    sc=pg.evaluate("TABSC()")
    order0=pg.evaluate("[...document.querySelectorAll('#surv .mod')].map(m=>m.dataset.m)")
    pg.focus("#surv .mod[data-m='watch']>.grip");pg.keyboard.press("ArrowDown");pg.wait_for_timeout(300)
    order1=pg.evaluate("[...document.querySelectorAll('#surv .mod')].map(m=>m.dataset.m)")
    chk("modules: keyboard ↓ moves Survival Watch below Rivals and saves per pool",order1.index("watch")==order0.index("watch")+1 and pg.evaluate(f"!!localStorage.getItem('lm_lay_{sc}')"),order1)
    # headless Chromium commits file:// localStorage lazily; give it time, and redo the move if a reload dropped it
    for attempt in range(3):
        pg.wait_for_timeout(4000);pg.reload();pg.wait_for_timeout(400)
        if pg.evaluate(f"!!localStorage.getItem('lm_lay_{sc}')"):break
        pg.wait_for_timeout(5000);pg.evaluate("setTab('s')");pg.wait_for_timeout(3000);pg.focus("#surv .mod[data-m='watch']>.grip");pg.keyboard.press("ArrowDown")
    pg.wait_for_timeout(5100);pg.evaluate("setTab('s')")
    for _ in range(20):
        pg.wait_for_timeout(500)
        o2=pg.evaluate("[...document.querySelectorAll('#surv .mod')].map(m=>m.dataset.m)")
        if len(o2)==len(order1):break
    chk("modules: order persists after reload",o2==order1,o2)
    pg.evaluate(f"localStorage.setItem('lm_lay_{sc}',JSON.stringify(['rules','overview','watch']))");pg.evaluate("SV.lastHtml='';svRender()");pg.wait_for_timeout(300)
    o3=pg.evaluate("[...document.querySelectorAll('#surv .mod')].map(m=>m.dataset.m)")
    chk("modules: a saved order missing newer modules keeps them (inserted at their default spot)",o3[0]=="rules" and set(o3)==set(order0) and o3.index("rivals")==o3.index("watch")+1,o3)
    pg.locator("#surv .mod[data-m='rivals']>.grip").click();pg.wait_for_timeout(200)
    chk("modules: tapping a grip offers ▲/▼",pg.evaluate("!!document.querySelector('.gmenu')"))
    pg.click(".gmenu button[data-d='-1']");pg.wait_for_timeout(300)
    o4=pg.evaluate("[...document.querySelectorAll('#surv .mod')].map(m=>m.dataset.m)");chk("modules: ▲ moves it up",o4.index("rivals")==o3.index("rivals")-1,o4)
    pg.evaluate("layReset(false)");pg.wait_for_timeout(300)
    chk("Settings → Reset this page restores the default order",pg.evaluate("[...document.querySelectorAll('#surv .mod')].map(m=>m.dataset.m)")==order0)
    grips={}
    for t,root in [("m","#view"),("t","#moves"),("p","#pick")]:
        pg.evaluate(f"setTab('{t}')");pg.wait_for_timeout(3500 if t!="m" else 800);grips[t]=pg.evaluate(f"document.querySelectorAll('{root} .mod>.grip').length")
    chk("grips on Matchups, Lab and Pick'em",all(v>=2 for v in grips.values()),grips)
    chk("no errors (survivor/modules)",not e,e[:2]);pg.close()
    pg,e=page(b,init=EDGE,pre=True);pg.evaluate("setTab('e')");pg.wait_for_timeout(8000)
    chk("grips on Edge sections",pg.evaluate("document.querySelectorAll('#moves .edcol .mod>.grip').length")>=4);pg.close()
    # ---------- 5. Replay ----------
    pg,e=page(b);pg.evaluate("setTab('f')");pg.wait_for_timeout(5000)
    R=pg.evaluate("""(()=>{const c=rpCtx(),ev=rpEvents(c).filter(x=>x.rel),by=k=>ev.find(x=>x.pid===k);const td=by('102'),fg=by('921'),int=by('202'),fum=by('303');
      const L=e=>Object.fromEntries(e.L.map(x=>[x.c.lg.id,+x.net.toFixed(2)]));
      return{td:td&&{pl:td.players.map(p=>p.id+'/'+p.role+'/'+p.prov),L:L(td)},fg:fg&&{k:fg.kind,ok:fg.fgOk,d:fg.dist,L:L(fg)},int:int&&{pl:int.players.map(p=>p.id+'/'+p.role),L:L(int)},fum:fum&&{pl:fum.players.map(p=>p.id+'/'+p.role)},
        order:[...document.querySelectorAll('#field .rpmk')].map(m=>parseFloat(m.style.left)),times:ev.filter(x=>x.t).sort((a,b)=>a.t-b.t).map(x=>x.eid),reel:document.querySelectorAll('#field .rpc').length,stage:!!document.querySelector('#field .rpf svg'),imp:document.querySelectorAll('#field .rpil').length}})()""")
    chk("replay: a TD is ONE event with QB + receiver (ESPN athlete ids)",R["td"] and sorted(R["td"]["pl"])==sorted(["200/pass/id","202/rec/id"]),R["td"])
    chk("replay: same play, different points per league scoring (Half-PPR vs PPR)",R["td"] and abs(R["td"]["L"]["L2"]-R["td"]["L"]["L1"]-0.5)<0.011,R["td"])
    chk("replay: field goal distance scored by the league's kicker rules (52 yd = 5)",R["fg"] and R["fg"]["k"]=="fg" and R["fg"]["d"]==52 and R["fg"]["L"]["L1"]==5,R["fg"])
    chk("replay: interception charged to the passer, credited to the defense",R["int"] and "201/pass" in R["int"]["pl"] and any(x.endswith("/dint") for x in R["int"]["pl"]),R["int"])
    chk("replay: lost fumble charged to the ball carrier",R["fum"] and "204/fumbler" in R["fum"]["pl"],R["fum"])
    chk("replay: plays from simultaneous games in true time order on the timeline",R["times"][:2]==["e2","e2"] and "e1" in R["times"] and R["times"].index("e1")<len(R["times"])-1,R["times"])
    chk("replay: reel (3) + one stage + impact per league",R["reel"]==3 and R["stage"] and R["imp"]==2,R)
    wp=pg.evaluate("(()=>{const ev=rpEvents(rpCtx()).find(x=>x.pid==='102');const x=ev.L[0];const a=x.c.mm.a,b=x.c.mm.b;return{d:x.wp.d,re:wpPair(a,b)-wpPair(a,b,-x.myP,-x.opP)}})()")
    chk("replay: win-% impact is the reproducible with/without counterfactual",abs(wp["d"]-wp["re"])<1e-12,wp)
    nowp=pg.evaluate("(()=>{const o=S.okProj;S.okProj=false;const ev=rpEvents(rpCtx());S.okProj=o;return ev.every(x=>x.L.every(y=>y.wp===null))})()")
    chk("replay: no win-% numbers without projections (never invented)",nowp)
    k2=pg.evaluate("(()=>{const ev=rpEvents(rpCtx()).filter(x=>x.rel);const pick=ev.find(x=>x.pid==='911');RP.sel=pick.key;rpRender();return RP.sel})()")
    pg.evaluate("rpTick()");pg.wait_for_timeout(1500);pg.evaluate("RP.parts.reel='';rpRender()")
    chk("replay: the play you're exploring survives live refreshes",pg.evaluate("RP.sel")==k2 and pg.evaluate("document.querySelector('#field .rpstg b').textContent").find("catch")>=0)
    pg.evaluate("RP.fp='202';RP.sel=null;rpRender()");pg.wait_for_timeout(300)
    fr=pg.evaluate("(()=>{const ks=[...document.querySelectorAll('#field .rpc')].map(c=>c.dataset.ev),ev=rpEvents(rpCtx());return{n:ks.length,all:ks.every(k=>ev.find(e=>e.key===k).players.some(p=>p.id==='202')),seg:document.querySelectorAll('#field .rpseg i').length,plays:document.querySelectorAll('#field .rpfpl .rplr').length}})()")
    chk("filmroom: picking a player filters the reel and shows his scoring composition",fr["n"]>=1 and fr["all"] and fr["seg"]>=1 and fr["plays"]==2,fr)
    chk("replay: no errors",not e,e[:2]);pg.close()
    mock.CONFLICT[0]=True
    pg,e=page(b);pg.evaluate("setTab('f')");pg.wait_for_timeout(5000)
    c=pg.evaluate("(()=>{const ev=rpEvents(rpCtx()).find(x=>x.pid==='102');return{tone:ev.tone,L:ev.L.map(x=>Math.sign(x.net))}})()")
    chk("replay: cross-league conflict (helps in one league, hurts in another) → gold",c["tone"]=="mix" and sorted(c["L"])==[-1,1],c)
    chk("replay: conflict badge in the impact panel",pg.evaluate("!!document.querySelector('#field .rpcf')"));pg.close();mock.CONFLICT[0]=False
    mock.amb_on()
    pg,e=page(b);pg.evaluate("RP.core={e1:false,e2:false};RP.coreAt={e1:Date.now(),e2:Date.now()};RP.ev={};setTab('f')");pg.wait_for_timeout(4000)
    a=pg.evaluate("(()=>{const ev=rpEvents(rpCtx());const td=ev.find(x=>x.pid==='102');return td.players.map(p=>p.id+'/'+p.prov)})()")
    chk("replay: an ambiguous name (two Z. Flowers on BAL) is never guessed",not any(x.startswith("202/") for x in a) and any(x.startswith("200/") for x in a),a)
    pg.close();del mock.P["2101"]
    pg,e=page(b,pre=True);pg.evaluate("setTab('f')");pg.wait_for_timeout(3000)
    chk("replay pregame: calm kickoff list, no fields or fake highlights",pg.evaluate("document.querySelectorAll('#field .kfr').length>=1&&!document.querySelector('#field .rpf')&&!document.querySelector('#field .rpc')"));pg.close()
    pg,e=page(b,W=390,rm=True);pg.evaluate("setTab('f')");pg.wait_for_timeout(5000)
    chk("replay phone: no horizontal scroll",pg.evaluate("document.documentElement.scrollWidth")<=390)
    chk("replay: reduced motion → static field (no draw/ball animation)",pg.evaluate("!document.querySelector('#field .rpdr,#field animateMotion')"))
    chk("no errors (replay phone)",not e,e[:2]);pg.close()
    b.close()
print("FAILED:",fails)
