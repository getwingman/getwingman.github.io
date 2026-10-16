/* Pick'em current-week and sync regression. node tests/unit/pickem_refresh.test.js index.html */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const src=fs.readFileSync(process.argv[2],"utf8");
function between(start,end){const a=src.indexOf(start),b=src.indexOf(end,a+start.length);assert(a>=0&&b>a,"Cannot extract "+start);return src.slice(a,b)}
const code=[
 between("function pkIndex()","/* The current NFL week"),
 between("function pkCurrentWeek()","/* the moment ESPN marks"),
 between("function pkApiGrade()","/* live sync from the sheet"),
 between("async function pkSync(force=false)","/* =====================================================================\n   SLEEPER PICK'EM"),
 between("async function pkTick(force=false)","/* =====================================================================\n   MOVES TAB")
].join("\n");
const S={nflWeek:7,dispWeek:7,season:"2026",tab:"p"},PK={d:{sheet:"test",stand:[["Alice",[1,2,3,4,5]],["Bob",[5,4,3,2,1]]],
 players:["Alice","Bob"],games:[[5,"KC","BAL",0,0,"KC","KC"],[7,"LV","DEN",null,null,"",""]],
 picks:[[0,0,0,"C"],[1,0,1,"I"],[0,1,0,"P"],[1,1,1,"P"]]},
 rows:null,games:null,nx:{},nxt:{},syncAt:0,nflAt:Date.now(),layout:"normalized",fails:0,syncBackoff:0};
const mocks={
 S,PK,Date,pkSleeperActive:()=>false,pkSleeperSync:()=>Promise.resolve(),
 pkSyncNormalized:async()=>true,gvizCsv:async()=>[],pkParse:()=>({err:"layout"}),
 pkLoadNext:async()=>{},pkRender:()=>{},nflState:async()=>{},poolCfg:()=>({}),
};
const ctx=vm.createContext(mocks);vm.runInContext(code+"\nthis.qa={pkIndex,pkApiGrade,pkCurrentWeek,pkSheetLatestWeek,pkWeekImport,pkHelperWeek,pkSync,pkTick}",ctx);
const q=ctx.qa;let n=0;
function ok(title,condition){assert(condition,title);n++}
q.pkIndex();ok("sheet source last week is W5",PK.wSheet===5);
ok("actual NFL week is W7",q.pkCurrentWeek()===7);
q.pkApiGrade();
ok("scoreboard extends to W7",PK.weeks===7&&PK.rows.every(r=>r.w.length===7));
ok("prior authoritative sheet scores retained",PK.rows[0].w[4]===5&&PK.rows[1].w[4]===1);
ok("current W7 has no invented correct picks",PK.rows.every(r=>r.w[6]===0));
ok("last sheet-graded W5 detectable",q.pkSheetLatestWeek()===5);
ok("sheet coverage reflects 2 W5 graded picks",q.pkWeekImport(5).graded===2&&q.pkWeekImport(5).captured===2);
ok("W7 pending picks aren't graded",q.pkWeekImport(7).captured===2&&q.pkWeekImport(7).graded===0);
ok("helper stays on W7 before kickoff",q.pkHelperWeek(7)===7);
PK.nx[7]=[{st:"pre"},{st:"in"}];
ok("helper still W7 with one upcoming game",q.pkHelperWeek(7)===7);
PK.nx[7]=[{st:"post"},{st:"in"}];
ok("helper switches to W8 once all games started",q.pkHelperWeek(7)===8);
PK.nx[7]=[{home:"DEN",away:"LV",st:"post",hs:-3,hsVerified:true,hsc:20,asc:27}];
q.pkApiGrade();
ok("verified final grades ungraded game",PK.games[1].ats==="LV"&&PK.games[1].api===1);
ok("live ATS grading must not fake latest sheet grade",q.pkSheetLatestWeek()===5);
ok("sheet coverage remains authoritative despite API overlay",q.pkWeekImport(7).graded===0);
ok("only correct W7 pick receives point",PK.rows[0].w[6]===1&&PK.rows[1].w[6]===0);
q.pkApiGrade();
ok("repeated grade doesn't double-count",PK.rows[0].w[6]===1);
PK.nx[7][0].hsVerified=false;q.pkApiGrade();
ok("unverified market line can't grade ATS",PK.games[1].ats===""&&PK.rows[0].w[6]===0);
const old=S.nflWeek;S.nflWeek=8;ok("rollover advances without sheet change",q.pkCurrentWeek()===8);S.nflWeek=old;
const savedGames=PK.games,savedBase=PK.base;
PK.games=[{w:5,picks:[{c:"M"},{c:"M"}],ats:"KC"},{w:6,picks:[{c:"M"},{c:"M"}],ats:""}];
PK.base={games:[{c:["M","M"]},{c:["M","M"]}]};
ok("15-week phantom tie suppressed by source coverage",q.pkWeekImport(5).captured===0&&q.pkWeekImport(5).graded===0&&q.pkSheetLatestWeek()===0);
ok("current missing picks aren't recorded losses",q.pkWeekImport(6).expected===2&&q.pkWeekImport(6).captured===0);
PK.games=savedGames;PK.base=savedBase;
(async()=>{
 let updates=0;ctx.pkSyncNormalized=async()=>{updates++;await Promise.resolve();return true};
 PK.syncAt=0;PK.layout="normalized";await Promise.all([q.pkSync(),q.pkSync()]);
 ok("concurrent sheet sync deduplicated",updates===1);
 ok("successful sync advances timestamp",PK.syncAt>0&&PK.fails===0);
 const stamp=PK.syncAt;ctx.pkSyncNormalized=async()=>{throw new Error("network")};
 await q.pkSync();ok("failed sync keeps previous success time",PK.syncAt===stamp);
 ok("failed sync visibly marked stale",PK.fails===1&&PK.st==="stale"&&PK.syncBackoff>Date.now());
 await q.pkSync();ok("backoff prevents rapid retry",PK.fails===1);
 ctx.pkSyncNormalized=async()=>true;await q.pkSync(true);
 ok("manual retry bypasses backoff and recovers",PK.fails===0&&PK.st==="ok");
 let weeks=[],syncCalls=0;ctx.pkLoadNext=async w=>{weeks.push(w)};ctx.pkSyncNormalized=async()=>{syncCalls++;return true};
 PK.syncAt=0;PK.nflAt=Date.now();await q.pkTick();
 ok("tick polls current NFL week, even if graded sheet stuck",weeks.includes(7)&&weeks.includes(8)&&weeks.includes(5));
 ok("tick refreshes sheet when stale",syncCalls===1);
 ok("successful tick doesn't fake another sync",PK.syncAt>0);
 ok("visible Refresh UI is hooked",src.includes('id="pkrefresh"')&&src.includes('el.querySelector("#pkrefresh")'));
 ok("ungraded weeks labeled unreported",src.includes('unreported=imp.captured===0'));
 ok("future pick schedule anchored to current slate",src.includes('const N=pkHelperWeek(cw)'));
 ok("source check not called a data sync",src.includes('sheet checked '));
 ok("direct reader setup available when sheet incomplete",src.includes('id="pkdirect"')&&src.includes('querySelector("#pkdirect")'));
 ok("no silent normalized-to-legacy downgrade",src.includes('if(PK.layout==="normalized")throw new Error("layout")'));
 console.log("PASS pickem-refresh: "+n+" regression checks");
})().catch(e=>{console.error("FAIL",e.stack||e);process.exitCode=1});
