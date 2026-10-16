/* Pick'em live scoring: node tests/unit/pickem_refresh.test.js index.html */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const src=fs.readFileSync(process.argv[2],"utf8");
const cut=(a,b)=>{const x=src.indexOf(a),y=src.indexOf(b,x+a.length);assert(x>=0&&y>x,"Source extract failed: "+a);return src.slice(x,y)};
const JS=[
 cut("function pkIndex()","/* The current NFL week"),
 cut("function pkCurrentWeek()","// Historical migration"),
 cut("const PK_HIST_2026=","/* live sync from the sheet"),
 cut("async function pkSync(force=false)","/* =====================================================================\n   SLEEPER PICK'EM"),
 cut("async function pkTick(force=false)","/* =====================================================================\n   MOVES TAB")
].join("\n");
const S={season:"2026",nflWeek:6,dispWeek:6,tab:"p"},PK={
 d:{sheet:"qa",stand:[["xParRaidr",[]],["rgandhi3",[]]],players:["xParRaidr","rgandhi3"],
 games:[[1,"SEA","NE",null,null,"",""],[5,"TB","DAL",null,null,"",""],[6,"HOU","JAX",null,null,"",""]],
 picks:[[0,0,1,"P"],[1,0,0,"P"],[0,1,-1,"M"],[1,1,-1,"M"],[0,2,-1,"M"],[1,2,-1,"M"]]},
 rows:null,games:null,layout:"normalized",gx:[{id:"2026-W1-SEA-NE"},{id:"2026-W5-TB-DAL"},{id:"2026-W6-HOU-JAX"}],
 nx:{5:[{home:"DAL",away:"TB",st:"post",hsc:17,asc:24,hs:-9.5,hsVerified:true}],
     6:[{home:"JAX",away:"HOU",st:"in",hsc:3,asc:7,hs:3,hsVerified:true}]},
 nxt:{},cov:{},syncAt:0,nflAt:Date.now(),fails:0,syncBackoff:0
},PKS={data:{pool:{entries:[{id:"4",username:"xParRaidr"},{id:"9",username:"rgandhi3"}]},
 weeks:[{week:5,games:[{home:"DAL",away:"TB",final:true,picks:[{entryId:"4",team:"TB"},{entryId:"9",team:"DAL"}]}]},
 {week:6,games:[{home:"JAX",away:"HOU",final:false,picks:[{entryId:"4",team:"HOU"}]}]}]}};
const ctx=vm.createContext({S,PK,PKS,NT:x=>x,Date,pkSleeperActive:()=>false,pkSleeperSync:async()=>{},
 pkSyncNormalized:async()=>true,gvizCsv:async()=>[],pkParse:()=>({err:"layout"}),pkLoadNext:async()=>{},
 pkRender:()=>{},nflState:async()=>{},poolCfg:()=>({})});
vm.runInContext(JS+"\nthis.qa={pkIndex,pkApiGrade,pkSheetLatestWeek,pkWeekImport,pkCurrentWeek,pkHelperWeek,pkSync,pkTick}",ctx);
const q=ctx.qa;let n=0;const ok=(name,test)=>{assert(test,name);n++};
q.pkIndex();ok("source has three weeks of inputs",PK.games.length===3);
ok("NFL week is independent of sheet",q.pkCurrentWeek()===6);
q.pkApiGrade();
ok("historical pool winner preserved",PK.games[0].ats==="NE");
ok("2026 W1 archived participant scored",PK.rows[0].w[0]===1&&PK.rows[1].w[0]===0);
ok("final-only Sleeper selections imported",PK.games[1].picks[0].side===0&&PK.games[1].picks[1].side===1);
ok("ESPN final and locked spread determine cover",PK.games[1].ats==="TB"&&PK.games[1].atsSrc==="espn_verified");
ok("Week 5 per-member points calculated live",PK.rows[0].w[4]===1&&PK.rows[1].w[4]===0);
ok("no premature Week 6 picks",PK.games[2].picks.every(p=>p.c==="M"));
ok("all score rows through Week 6",PK.rows.every(r=>r.w.length===6));
ok("latest graded week is W5",q.pkSheetLatestWeek()===5);
q.pkApiGrade();ok("re-grading is idempotent",PK.rows[0].w[4]===1);
PK.nx[5][0].hsVerified=false;q.pkApiGrade();ok("no grade from unverified line",PK.games[1].ats===""&&PK.games[1].picks[0].c==="P");
PK.nx[5][0].hsVerified=true;PK.nx[5][0].st="in";q.pkApiGrade();ok("never grade non-final game",PK.games[1].ats==="");
PK.nx[5][0].st="post";q.pkApiGrade();ok("resumes grading when marked final",PK.games[1].ats==="TB");
ok("dynamic import counter",q.pkWeekImport(5).captured===2&&q.pkWeekImport(5).graded===2);
const old=PKS.data.pool.entries;PKS.data.pool.entries=[{id:"4",username:"other"},{id:"9",username:"unknown"}];
PK.base.games[1].c=["M","M"];PK.games[1].picks.forEach(p=>p.side=-1);
q.pkApiGrade();ok("unknown remote entrants never mapped",PK.games[1].picks.every(p=>p.side===-1));
PKS.data.pool.entries=old;
(async()=>{
 let updates=0;ctx.pkSyncNormalized=async()=>{updates++;await Promise.resolve();return true};
 await Promise.all([q.pkSync(),q.pkSync()]);
 ok("deduplicates simultaneous sheet-input sync",updates===1);
 const stamp=PK.syncAt;ctx.pkSyncNormalized=async()=>{throw new Error("network")};
 await q.pkSync();ok("failure preserves success time",PK.syncAt===stamp);
 ok("failure shown as stale with retry",PK.fails===1&&PK.st==="stale"&&PK.syncBackoff>Date.now());
 await q.pkSync();ok("retry backoff",PK.fails===1);
 ctx.pkSyncNormalized=async()=>true;await q.pkSync(true);
 ok("manual retry succeeds",PK.st==="ok"&&PK.fails===0);
 let weeks=[];ctx.pkLoadNext=async w=>{weeks.push(w)};
 PK.syncAt=Date.now();PK.nflAt=Date.now();await q.pkTick();
 ok("all previous NFL weeks fetched",weeks.includes(1)&&weeks.includes(5)&&weeks.includes(6)&&weeks.includes(7));
 ok("sheet no longer expected to carry grades",src.includes('picks:["week","game_id","player_id","pick_team","pick_status"]'));
 ok("source scores never used in normalized parser",src.includes('games.push([w,g.team_a,g.team_b,null,null,"",""])'));
 ok("live parser automatically combines final-only Sleeper picks",src.includes("function pkSleeperOverlay(){"));
 console.log("PASS pickem-refresh: "+n+" regression checks");
})().catch(e=>{console.error("FAIL",e.stack||e);process.exitCode=1});
