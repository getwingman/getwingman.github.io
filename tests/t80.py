import sys,itertools,json;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F=sys.argv[1];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
EL={"QB":["QB"],"RB":["RB"],"WR":["WR"],"TE":["TE"],"K":["K"],"DEF":["DEF"],"FLEX":["RB","WR","TE"],"SUPER_FLEX":["QB","RB","WR","TE"]}
def brute(players,slots):
    best=-1e9
    def rec(i,used,pts):
        nonlocal best
        if i==len(slots):best=max(best,pts);return
        any_=False
        for pid,(pos,v) in players.items():
            if pid in used or not set(pos)&set(EL.get(slots[i],[slots[i]])):continue
            any_=True;used.add(pid);rec(i+1,used,pts+v);used.discard(pid)
        if not any_:rec(i+1,used,pts)
    rec(0,set(),0);return best
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={"width":1500,"height":1000});errs=[];pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000)
    t=pg.evaluate("(async()=>{const t0=performance.now();setTab('t');await new Promise(r=>{const i=setInterval(()=>{if(MV.res[MV.lg]&&!MV.busy){clearInterval(i);r()}},50)});return Math.round(performance.now()-t0)})()")
    chk("Lab builds (exact optimizer) in reasonable time",t<4000,f"{t} ms");pg.wait_for_timeout(2500)
    # independent brute-force check of every completed team-week
    data=pg.evaluate("""(async()=>{const out=[];for(const lg of S.L){const slots=lineupSlots(lg);for(let w=1;w<S.nflWeek;w++){const M=await lg.adapter.matchups(lg,w),rows=await iqWeek(lg,w);
      for(const r of rows){const m=M.find(x=>x.roster_id===r[0]);const pl={};m.players.forEach(id=>pl[id]=[eligOf(id),+m.players_points[id]||0]);out.push({lg:lg.id,w,rid:r[0],act:r[1],opt:r[2],slots,pl,st:m.starters})}}}return out})()""")
    bad=[]
    for d in data:
        want=round(max(brute({k:tuple(v) for k,v in d["pl"].items()} and {k:(v[0],v[1]) for k,v in d["pl"].items()},d["slots"]),d["act"]),2)
        if abs(want-d["opt"])>0.011:bad.append((d["lg"],d["w"],d["rid"],d["opt"],want))
    chk(f"Lineup IQ optimal = brute force on {len(data)} completed team-weeks",not bad,bad[:4])
    chk("board: Season and Strength are separate columns",pg.evaluate("[...document.querySelectorAll('#moves .pwt th')].map(t=>t.innerText.trim()).join('|')").startswith("#|Manager|Rec|Season ⓘ|Trend|Strength ⓘ"),pg.evaluate("[...document.querySelectorAll('#moves .pwt th')].map(t=>t.innerText.trim()).join('|')"))
    chk("board title / summary",pg.evaluate("document.querySelector('#moves .svh').innerText.replace(/\\s+/g,' ')"),pg.evaluate("document.querySelector('#moves .svh').innerText.replace(/\\s+/g,' ')"))
    pg.click('#moves th.srt[data-sort="season"]');pg.wait_for_timeout(300)
    rk=pg.evaluate("[...document.querySelectorAll('#moves .pwt tbody tr .srk')].map(x=>+x.textContent.slice(1))")
    chk("sort by Season rank",rk==sorted(rk),rk)
    chk("awards shown with 4 completed weeks",pg.evaluate("document.querySelectorAll('#moves .awd:not(.ld)').length")>=3)
    # fewer than 3 weeks → locked awards
    pg.evaluate("MV.iq[MV.lg].ws=[1,2];MV.lastHtml='';mvRender()")
    chk("awards locked with <3 weeks",pg.evaluate("document.querySelector('#moves .awd.ld').innerText.replace(/\\s+/g,' ')").startswith("🔒 SEASON AWARDS") ,pg.evaluate("document.querySelector('#moves .awd.ld').innerText.replace(/\\s+/g,' ')"))
    chk("IQ ring hidden until enough history",pg.evaluate("document.querySelectorAll('#moves .iqr').length")==0)
    # final week math
    fw=pg.evaluate("[finalWeek({league:{settings:{playoff_week_start:15,playoff_teams:6}}}),finalWeek({league:{settings:{playoff_week_start:15,playoff_teams:4,playoff_round_type:1}}}),finalWeek({league:{settings:{playoff_week_start:15,playoff_teams:8,playoff_round_type:2}}}),finalWeek({league:{settings:{playoff_week_start:14,playoff_teams:6}}})]")
    chk("championship week from playoff settings",fw==[17,17,18,16],fw)
    # end-of-season state
    pg.evaluate("(async()=>{S.nflWeek=18;MV.res={};MV.lastHtml='';await mvTick(true)})()");pg.wait_for_timeout(4000)
    chk("season over: clear state, no zero rankings, no trade/pickup panels",pg.evaluate("[[...document.querySelectorAll('#moves .svnote')].some(n=>n.innerText.includes('Season complete')),document.querySelectorAll('#moves .trd,#moves .add').length,document.querySelectorAll('#moves .pwr').length]")==[True,0,0],pg.evaluate("[document.querySelector('#moves .svnote')&&document.querySelector('#moves .svnote').innerText,document.querySelectorAll('#moves .trd,#moves .add').length,document.querySelectorAll('#moves .pwr').length]"))
    pg.screenshot(path=sys.argv[2]+"/lab_end.png",full_page=True)
    chk("no errors",not errs,errs[:3])
    b.close()
print("FAILED:",fails)
