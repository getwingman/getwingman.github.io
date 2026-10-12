/* Wingman live-injury regression: node tests/unit/live_injury.test.js index.html */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const src=fs.readFileSync(process.argv[2],"utf8");
const part=(a,b)=>{const i=src.indexOf(a),j=src.indexOf(b,i+a.length);assert(i>=0&&j>i,"Missing source block: "+a);return src.slice(i,j)};
const mock={
  season:"2026",week:6,nflWeek:6,base:{"L:p":"20"},pc:{},players:{p:{full_name:"Test Quarterback",position:"QB",team:"KC",injury_status:"Questionable"}},
  games:{KC:{state:"in",period:3,clock:"08:00",eid:"event1"}},
  stats:{p:{pass_att:4,pass_yd:35}},eff:{p:{pass_att:4,pass_yd:35}},box:{p:{pass_att:4,pass_yd:35}},
  L:[{id:"L",mu:[{roster_id:1,players:["p"],starters:["p"],players_points:{p:7},points:7}]}],liveInj:{},dirty:false,okGames:true
};
const ctx={
 S:mock,NT:t=>t,team:()=>({reserve:[]}),seasonAvg:()=>12,
 matchVar:()=>100,Phi:z=>1/(1+Math.exp(-z)),
 SD:{QB:7},pinfo:null
};
const js=[
 part("const clockSec=", "const POSQ="),
 part("function pinfo(id)", "function team(lg,rid)"),
 part("const OUTS=", "function gcls(p)"),
 part("function expected(lg,p,a)", "const SD="),
 part("function side(lg,m)", "function needLine(lg,"),
 part("function wpPair(a,b", "function wpModel(")
].join("\n");
vm.createContext(ctx);vm.runInContext(js+"\nthis.api={clockSec,frac,pinfo,settled,syncLiveInjuries,effectiveInjury,injuryVolume,expected,side,wpPair}",ctx);
const a=ctx.api;
let n=0;const ok=(msg,cond)=>{assert(cond,msg);n++};
const near=(x,y)=>Math.abs(x-y)<1e-6;
ok("MM:SS clock parses",a.clockSec("12:34")===754);
ok("numeric clock works",a.clockSec(754)===754);
ok("mid-third quarter fraction finite",near(a.frac(mock.games.KC),(1800+420)/3600));
ok("pre game fraction 0",a.frac({...mock.games.KC,state:"pre"})===0);
ok("post game fraction 1",a.frac({...mock.games.KC,state:"post"})===1);
ok("OT fraction within bounds",a.frac({...mock.games.KC,period:5})===.98);
ok("invalid clock never yields NaN",Number.isFinite(a.frac({...mock.games.KC,clock:"??"})));
a.syncLiveInjuries();ok("questionable watch starts",!!mock.liveInj.p&&!mock.liveInj.p.returned);
ok("questionable tag initially visible",a.pinfo("p").inj==="Questionable");
ok("first questionable state settles the player",a.settled(a.pinfo("p")));
const lg={id:"L",proj:{p:0}},opp={total:12,proj:12,bs:12,rows:[],left:0};
let before=a.side(lg,mock.L[0].mu[0]);
ok("questionable initial forecast is actual score",near(before.proj,7));
ok("questionable initial variance is zero",before.vr===0);
const beforeOdds=a.wpPair(before,opp);
mock.box.p.pass_yd=47;a.syncLiveInjuries();
ok("yardage correction alone never proves return",!mock.liveInj.p.returned);
mock.stats.p.pass_att=4;a.syncLiveInjuries();
ok("no new attempt leaves injury frozen",!mock.liveInj.p.returned);
mock.box.p.pass_att=5;a.syncLiveInjuries();
ok("new pass attempt marks returned",mock.liveInj.p.returned);
ok("player cache invalidated",a.pinfo("p").inj==="");
ok("live game reopens",!a.settled(a.pinfo("p")));
let after=a.side(lg,mock.L[0].mu[0]);ok("projection rises above actual after return",after.proj>7);
ok("return restores baseline pace when provider projection zero",near(after.proj,7+20*(1-a.frac(mock.games.KC))));
ok("return restores nonzero remaining variance",after.vr>0);
ok("win probability responds to projection change",a.wpPair(after,opp)>beforeOdds);
a.syncLiveInjuries();ok("later idle refresh does not re-freeze",mock.liveInj.p.returned&&!a.settled(a.pinfo("p")));
mock.players.p.injury_status="Out";a.syncLiveInjuries();
ok("official Out overrides prior return",a.pinfo("p").inj==="Out"&&a.settled(a.pinfo("p"))&&!mock.liveInj.p);
mock.players.p.injury_status="Questionable";mock.games.KC.eid="event2";a.syncLiveInjuries();
ok("new injury/game begins new watch",!!mock.liveInj.p&&!mock.liveInj.p.returned);
mock.stats.p.pass_att=6;a.syncLiveInjuries();ok("Q status can recover again",mock.liveInj.p.returned);
mock.players.p.injury_status="";a.syncLiveInjuries();ok("official clearance drops temporary state",!mock.liveInj.p&&a.pinfo("p").inj==="");
mock.players.p.injury_status="Doubtful";a.syncLiveInjuries();ok("doubtful injury monitored",!!mock.liveInj.p&&!mock.liveInj.p.returned);
mock.box.p.pass_att=7;a.syncLiveInjuries();ok("doubtful also recovers on play",mock.liveInj.p.returned);
mock.games.KC.state="post";a.syncLiveInjuries();ok("postgame always final",a.settled(a.pinfo("p"))&&!mock.liveInj.p);
mock.games.KC={state:"in",period:1,clock:"12:00",eid:"event3"};
mock.players.p.injury_status="Questionable";mock.stats.p.pass_att=10;a.syncLiveInjuries();
ok("new event creates fresh baseline",!mock.liveInj.p.returned&&mock.liveInj.p.baseline.pass_att===10);
mock.week=7;ok("historical injury override not applied in next week",a.effectiveInjury("p",mock.players.p)==="Questionable");
ok("refresh flow actually runs return detection",src.includes("computeEff(now);\n    syncLiveInjuries()"));
ok("injury alerts can fire after initial sync",src.includes("function injCheck(){\n  if(!S.players)return"));
ok("live player list refresh guarded",src.includes("S.playersRefreshing||Date.now()<(S.playersRetryAt||0)"));
console.log("PASS live-injury: "+n+" regressions");
