"""scoring across league settings, cross-league exposure, screenshot-import roster matching"""
import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F=sys.argv[1];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={"width":1500,"height":900});e=[];pg.on("pageerror",lambda x:e.append(str(x)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000)
    cases=pg.evaluate("""(()=>{const base={pass_yd:.04,pass_td:4,pass_int:-2,rush_yd:.1,rush_td:6,rec_yd:.1,rec_td:6,fum_lost:-2};
      const std={...base,rec:0},half={...base,rec:.5},ppr={...base,rec:1},six={...ppr,pass_td:6},teprem={...ppr,bonus_rec_te:.5};
      const wr={rec:5,rec_yd:82,rec_td:1},qb={pass_yd:300,pass_td:3,pass_int:1,rush_yd:20};
      return{
        std:calcPts(wr,std),half:calcPts(wr,half),ppr:calcPts(wr,ppr),
        qb4:calcPts(qb,ppr),qb6:calcPts(qb,six),
        bonus:calcPts({rec:7,rec_yd:104},{...ppr,bonus_rec_yd_100:3}),
        fg:calcPts({fgm_50p:1,fgm_30_39:2,xpm:3},{fgm_30_39:3,fgm_50p:5,xpm:1}),
        pa0:calcPts({pts_allow:0,sack:3,int:1},{pts_allow_0:10,pts_allow_1_6:7,sack:1,int:2}),
        pa17:calcPts({pts_allow:17},{pts_allow_0:10,pts_allow_1_6:7,pts_allow_7_13:4,pts_allow_14_20:1,pts_allow_21_27:0}),
        neg:calcPts({pass_int:3,fum_lost:1},ppr)}})()""")
    want=dict(std=14.2,half=16.7,ppr=19.2,qb4=24.0,qb6=30.0,bonus=20.4,fg=14.0,pa0=15.0,pa17=1.0,neg=-8.0)
    for k,v in want.items():chk(f"scoring: {k}",abs(cases[k]-v)<1e-6,(cases[k],v))
    # league formats come from each league's own settings (L1 half-PPR, L2 PPR in the mock)
    fm=pg.evaluate("S.L.map(l=>l.fmt)");chk("each league scored under its own settings",fm==["Half-PPR","PPR"],fm)
    pts=pg.evaluate("S.L.map(l=>{const m=myMatch(l);return m&&m.a.rows.find(r=>r&&r.p&&r.p.id==='202').a})")
    chk("same player, different points per league format (Flowers: 16.70 half / 19.20 PPR)",pts==[16.7,19.2],pts)
    # cross-league exposure
    xp=pg.evaluate("(()=>{const r=['200','201','2005'].map(id=>{const x=xpInfo(id);return x?x.kind:null});return r})()")
    chk("cross-league exposure detected (yours in both / facing you)",xp[0] in("me","mix") and xp[1] in ("op","mix"),xp)
    # import matching: confident, ambiguous never auto-merged, DEF by nickname
    im=pg.evaluate("""(async()=>{await imEnsurePlayers();const t=imFromJson({teams:[{name:'A',players:['QB Lamar Jackson (BAL)','WR Zay Flowers','Bears D/ST','RB Nobody Atall']}]});
      return t.teams[0].players.map(p=>{const m=imMatch(p);return[p.name,m.id,m.conf]})})()""")
    chk("import: exact name+team → confident",im[0][1]=="200" and im[0][2]=="confident",im[0])
    chk("import: team defense from nickname",im[2][1]=="CHI",im[2])
    chk("import: unknown player is never guessed",im[3][1] is None and im[3][2] in("unresolved","needs"),im[3])
    try:pg.evaluate("imFromJson({teams:[]})");chk("import: bad JSON rejected with a plain message",False)
    except Exception as ex:chk("import: bad JSON rejected with a plain message","teams" in str(ex),str(ex)[:80])
    chk("no errors",not e,e[:2]);b.close()
print("FAILED:",fails)
