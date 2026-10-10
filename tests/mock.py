"""Mock Sleeper / ESPN backend for Wingman headless tests (week 5, BAL-CIN live, GB@ATL final)."""
import json, re, random, time
NOW = int(time.time()*1000)
random.seed(7)
TEAMS = ["ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU","IND","JAX","KC","LV","LAC","LAR","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT","SEA","SF","TB","TEN","WAS"]
P = {}
def add(pid,name,pos,team,**kw):
    f,l=(name.split(" ",1)+[""])[:2]
    P[pid]=dict(player_id=pid,full_name=name,first_name=f,last_name=l,position=pos,fantasy_positions=[pos],team=team,injury_status=kw.get("inj"),years_exp=kw.get("yx",4),espn_id=kw.get("espn"),depth_chart_order=kw.get("dco",1))
add("200","Lamar Jackson","QB","BAL",espn="3916387")
add("500","Emanuel Wilson","RB","GB",espn="4040")
add("202","Zay Flowers","WR","BAL",espn="4429205")
add("204","Mark Andrews","TE","BAL")
add("205","Drake London","WR","ATL",inj="Questionable")
add("600","Brandon McManus","K","GB")
add("800","Rookie Back","RB","NYG",yx=0,dco=2)
add("700","Hurt Guy","WR","SEA",inj="IR")
add("201","Joe Burrow","QB","CIN")
add("300","Ja'Marr Chase","WR","CIN",inj="Questionable")
add("203","Tee Higgins","WR","CIN")
add("900","Opp Bench","TE","CIN")
add("901","Tony Pollard","RB","TEN")
add("902","Trevor Lawrence","QB","JAX")
for t in TEAMS: P[t]=dict(player_id=t,position="DEF",fantasy_positions=["DEF"],team=t,full_name=t+" D/ST")
# filler players for 10 other rosters
POS=["QB","RB","RB","WR","WR","TE","WR","RB","K"]
fill={}
k=1000
for r in range(3,13):
    ids=[]
    for i,pos in enumerate(POS):
        k+=1; pid=str(k); tm=TEAMS[(k*7)%32]
        if tm in ("BAL","CIN","GB","ATL"): tm="DAL"
        add(pid,f"{pos}{r} Player{i}",pos,tm); ids.append(pid)
    fill[r]=ids
# free agents for Roster Lab pickups
for i,(n,pos,tm) in enumerate([("Zonovan Knight","RB","ARI"),("Waiver Wire","WR","SEA"),("Streamer TE","TE","DET")]):
    add(str(2000+i),n,pos,tm)
add("2005","Bench Wideout","WR","DAL")
ROST={1:dict(players=["200","500","202","204","205","600","800","2005","700"],starters=["200","500","202","204","205","600"],reserve=["700"]),
      2:dict(players=["201","300","203","900","901","902"],starters=["201","300","203","900","0","0"],reserve=[])}
for r,ids in fill.items(): ROST[r]=dict(players=ids,starters=[ids[0],ids[1],ids[3],ids[5],ids[2],ids[8]],reserve=[])
USERS=[dict(user_id="U%d"%r,display_name=n,metadata={"team_name":"Team "+n}) for r,n in zip(range(1,13),["xParRaidr","manager2","manager3","manager4","manager5","manager6","manager7","manager8","manager9","manager10","manager11","manager12"])]
def rosters(lg):
    out=[]
    for r in range(1,13):
        R=ROST[r]; out.append(dict(roster_id=r,owner_id="U%d"%r,players=R["players"],starters=R["starters"],reserve=R["reserve"],taxi=[],settings=dict(wins=r%4,losses=3-r%4,ties=0,fpts=400+r*7,fpts_decimal=50,waiver_budget_used=10)))
    return out
HALF=dict(pass_yd=.04,pass_td=4,pass_int=-2,rush_yd=.1,rush_td=6,rec=.5,rec_yd=.1,rec_td=6,fum_lost=-2,xpm=1,fgm_0_19=3,fgm_20_29=3,fgm_30_39=3,fgm_40_49=4,fgm_50p=5,sack=1,int=2,fum_rec=2,def_td=6,safe=2,pts_allow_0=10,pts_allow_1_6=7,pts_allow_7_13=4,pts_allow_14_20=1,pts_allow_21_27=0,pts_allow_28_34=-1,pts_allow_35p=-4,bonus_rec_yd_100=3)
PPR=dict(HALF,rec=1)
def league(lid):
    return dict(league_id=lid,name="League One" if lid=="L1" else "League Two",season="2026",status="in_season",total_rosters=12,
                roster_positions=["QB","RB","WR","TE","FLEX","K","BN","BN","BN","IR"],scoring_settings=HALF if lid=="L1" else PPR,
                settings=dict(playoff_teams=6,playoff_week_start=15,waiver_type=2,waiver_budget=100,num_teams=12))
LIVE={"200":dict(pass_td=1,pass_cmp=12,pass_att=18,pass_yd=160,rush_yd=20,rush_att=4),"500":dict(rush_att=12,rush_yd=58,rec=1,rec_tgt=1,rec_yd=10),
      "202":dict(rec=5,rec_tgt=8,rec_yd=82,rec_td=1),"204":dict(rec=2,rec_tgt=3,rec_yd=19),"205":dict(rec=0,rec_tgt=2),"600":dict(xpm=0),
      "201":dict(pass_td=2,pass_cmp=20,pass_att=28,pass_yd=230),"300":dict(rec=3,rec_tgt=5,rec_yd=27),"203":dict(rec=4,rec_tgt=6,rec_yd=45),"900":dict(rec=0)}
PROJ={"200":22,"500":11.5,"202":15,"204":9,"205":11.5,"600":8,"800":6,"700":0,"201":20,"300":17,"203":12,"900":4,"901":13,"902":17,"2000":10,"2001":8,"2002":5,"2005":9}
def pts(st,sc): return round(sum(v*sc.get(k,0) for k,v in st.items()),2)
TRADES=[False]
TPROJ={"1002":16,"1003":15,"1008":14,"1004":4,"1005":3.5,"1007":3}   # roster 3: RB-rich, WR-poor -> trades with my WR depth
def proj_stats(pid,w):
    base=TPROJ.get(pid) if TRADES[0] and pid in TPROJ else PROJ.get(pid)
    if base is None:
        p=P.get(pid,{}); base={"QB":17,"RB":10,"WR":10,"TE":7,"K":8,"DEF":6}.get(p.get("position"),5)*(0.7+((int(pid) if pid.isdigit() else 7)%5)*0.1)
    return dict(pts_half_ppr=base,pts_ppr=base*1.1,pts_std=base*.9,rush_yd=base*4,rec=base/5)
def hist_points(pid,w):
    random.seed(hash((pid,w))%100000); b=PROJ.get(pid,9); return round(max(0,random.gauss(b,6)),2)
def matchups(lid,w):
    out=[]
    for r in range(1,13):
        R=ROST[r]; mid=(r+1)//2
        if w<5:
            pp={pid:hist_points(pid,w) for pid in R["players"]}
            st=R["starters"]
        else:
            sc=HALF if lid=="L1" else PPR
            pp={pid:(pts(LIVE[pid],sc) if pid in LIVE and not PREGAME[0] else 0) for pid in R["players"]}
            st=R["starters"]
        out.append(dict(roster_id=r,matchup_id=mid,starters=st,players=R["players"],players_points=pp,starters_points=[pp.get(x,0) for x in st],points=round(sum(pp.get(x,0) for x in st),2)))
    return out
NICK=dict(ARI="Cardinals",ATL="Falcons",BAL="Ravens",BUF="Bills",CAR="Panthers",CHI="Bears",CIN="Bengals",CLE="Browns",DAL="Cowboys",DEN="Broncos",DET="Lions",GB="Packers",HOU="Texans",IND="Colts",JAX="Jaguars",KC="Chiefs",LV="Raiders",LAC="Chargers",LAR="Rams",MIA="Dolphins",MIN="Vikings",NE="Patriots",NO="Saints",NYG="Giants",NYJ="Jets",PHI="Eagles",PIT="Steelers",SEA="Seahawks",SF="49ers",TB="Buccaneers",TEN="Titans",WAS="Commanders")
def ev(eid,home,away,hid,aid,state,hs=0,as_=0,period=0,clock=0,detail="",poss=None,spot="",dd="",rz=False,date=None):
    sit={} if state!="in" else dict(possession=str(poss) if poss else None,possessionText=spot,downDistanceText=dd,shortDownDistanceText=dd,isRedZone=rz,lastPlay={"id":"p1"})
    return dict(id=eid,date=date or time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(NOW/1000-3600)),
                status=dict(type=dict(state=state,shortDetail=detail),period=period,clock=clock),
                competitions=[dict(competitors=[dict(homeAway="home",team=dict(id=str(hid),abbreviation=home,name=NICK.get(home,home)),score=str(hs)),
                                               dict(homeAway="away",team=dict(id=str(aid),abbreviation=away,name=NICK.get(away,away)),score=str(as_))],situation=sit,odds=[])])
FUT=time.strftime("%Y-%m-%dT%H:%MZ",time.gmtime(NOW/1000+86400*2))
NYG_LIVE=[False]
PREGAME=[False]
FAIL={"sleeper":0}
REQ=[]
def scoreboard(w):
    if PREGAME[0]:
        E=[ev("p%d"%i,TEAMS[i],TEAMS[i+1],300+i,400+i,"pre",date=FUT,detail="Sun 1:00p") for i in range(0,32,2)]
        for i,e in enumerate(E): e["competitions"][0]["odds"]=[dict(details=f"{TEAMS[2*i]} -{3+i%5}.5",overUnder=40+i)]   # home favored by 3.5–7.5, totals 40–55
        return dict(events=E,week=dict(number=w),season=dict(year=2026))
    E=[ev("e1","BAL","CIN",33,4,"in",14,10,3,312,"5:12 - 3rd",33,"CIN 35","2nd & 7"),
       ev("e2","ATL","GB",1,9,"post",20,27,4,0,"Final")]
    others=[t for t in TEAMS if t not in ("BAL","CIN","ATL","GB","LV","ARI","SEA","NYG")]
    for i in range(0,len(others)-1,2): E.append(ev("f%d"%i,others[i],others[i+1],100+i,200+i,"pre",date=FUT,detail="Sun 10:00a"))
    E.append(ev("f90","NYG","LV",19,13,"in",21,3,2,400,"6:40 - 2nd",19,"LV 40","1st & 10") if NYG_LIVE[0] else ev("f90","NYG","LV",19,13,"pre",date=FUT)); E.append(ev("f91","SEA","ARI",26,22,"pre",date=FUT))
    return dict(events=E,week=dict(number=w),season=dict(year=2026))
def J(route,obj,status=200):
    route.fulfill(status=status,content_type="application/json",headers={"Access-Control-Allow-Origin":"*"},body=json.dumps(obj))
def handle(route):
    u=route.request.url;REQ.append(u)
    if FAIL["sleeper"] and "sleeper.app/v1/league" in u: FAIL["sleeper"]-=1; return route.fulfill(status=503,body="")
    if re.search(r"\.(png|jpe?g|svg|webp|gif)(\?|$)",u) or "fonts.g" in u or "espncdn" in u or "static.www.nfl.com" in u or "google.com/s2" in u:
        return route.fulfill(status=404,body="")
    m=re.search(r"api\.sleeper\.app/v1/(.*?)(\?|$)",u)
    if m:
        p=m.group(1)
        if p.startswith("user/") and p.endswith("/leagues/nfl/2026"): return J(route,[{"league_id":"L1"},{"league_id":"L2"}])
        if p.startswith("user/"): return J(route,dict(user_id="U1",username="xparraidr",display_name="xParRaidr"))
        if p=="state/nfl": return J(route,dict(season="2026",week=5,display_week=5,season_type="regular"))
        if p=="players/nfl": return J(route,P)
        if p.startswith("players/nfl/trending"): return J(route,[{"player_id":"2000","count":5000}])
        mm=re.match(r"league/(L\d)(/(\w+))?(/(\d+))?",p)
        if mm:
            lid,what,w=mm.group(1),mm.group(3),mm.group(5)
            if not what: return J(route,league(lid))
            if what=="rosters": return J(route,rosters(lid))
            if what=="users": return J(route,USERS)
            if what=="matchups": return J(route,matchups(lid,int(w)))
        if p.startswith("stats/"): return J(route,[])
        return J(route,{},404)
    if "api.sleeper.com/projections/nfl/2026/" in u:
        w=int(re.search(r"/2026/(\d+)",u).group(1))
        return J(route,[dict(player_id=pid,stats=proj_stats(pid,w)) for pid in P])
    if "api.sleeper.com/stats/nfl/2026/" in u:
        return J(route,[] if PREGAME[0] else [dict(player_id=pid,stats=st) for pid,st in LIVE.items()])
    if "api.sleeper.com/stats/nfl/2026" in u: return J(route,[])
    if "api.sleeper.app/scores" in u: return J(route,[])
    if "site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard" in u:
        w=int((re.search(r"week=(\d+)",u) or [0,"5"])[1]); return J(route,scoreboard(w))
    if "summary?event=" in u: return J(route,dict(drives=dict(previous=[]),boxscore=dict(players=[]),scoringPlays=[]))
    if "nfl/news" in u: return J(route,dict(articles=[]))
    if "docs.google.com" in u: return sheet(route,u)
    if "workers.dev" in u: return J(route,{"error":"mock"},503)
    return route.fulfill(status=404,body="")

import urllib.parse,os
FIX=os.path.join(os.path.dirname(os.path.abspath(__file__)),"fixtures")
SHEETS={"SURV":{"🏊 Swimlanes":"sv_swimlanes.csv","⚙️ Our Picks Data":"sv_ourpicks.csv"},"PICK":{"Picks":"pk_picks.csv","Standings":"pk_standings.csv"}}
SHEET_OVERRIDE={}
SHEET_HITS=[]
def sheet(route,u):
    q=urllib.parse.urlparse(u);qs=urllib.parse.parse_qs(q.query);tab=qs.get("sheet",[""])[0]
    sid=q.path.split("/d/")[1].split("/")[0] if "/d/" in q.path else ""
    SHEET_HITS.append((sid,tab,qs.get("range",[""])[0]))
    if (sid,tab) in SHEET_OVERRIDE: return route.fulfill(status=200,body=SHEET_OVERRIDE[(sid,tab)],headers={"content-type":"text/csv","access-control-allow-origin":"*"})
    if sid.startswith("SURV") and tab not in SHEETS["SURV"]: tab="🏊 Swimlanes"   # first-tab fallback for the legacy sheet
    if sid.startswith("PICK") and tab not in SHEETS["PICK"]: tab="Picks"
    if sid.startswith("PRIV"): return route.fulfill(status=200,body="<!DOCTYPE html><html>sign in</html>",headers={"content-type":"text/html","access-control-allow-origin":"*"})
    for k,tabs in SHEETS.items():
        if sid.startswith(k) and tab in tabs:
            return route.fulfill(status=200,body=open(os.path.join(FIX,tabs[tab]),encoding="utf-8").read(),headers={"content-type":"text/csv","access-control-allow-origin":"*"})
    for k,pre in (("SV2","sv2_"),("PK2","pk2_")):
        if sid.startswith(k):
            order=open(os.path.join(FIX,"v2",pre+"_order.txt")).read().split("\n")
            t=tab if tab in order else order[0]          # real gviz answers an unknown tab name with the FIRST tab
            body=open(os.path.join(FIX,"v2",pre+t+".csv"),encoding="utf-8").read()
            return route.fulfill(status=200,body=body,headers={"content-type":"text/csv","access-control-allow-origin":"*"})
    return route.fulfill(status=400,body="",headers={"access-control-allow-origin":"*"})
