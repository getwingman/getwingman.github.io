/* Survivor transparent eliminations. Run: node tests/unit/survivor_eliminations.test.js index.html */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const source=fs.readFileSync(process.argv[2],"utf8");
const start=source.indexOf("function svEliminationData(w)"),end=source.indexOf("function svRender(){",start);
assert(start>=0&&end>start,"Survivor elimination helpers absent");
const js=source.slice(start,end);
const esc=x=>String(x).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const records={
 Chiefs:{r:"L",st:"post"},Raiders:{r:"W",st:"post"},
 Vikings:{r:"T",st:"post"},Bears:{r:"",st:"in",me:3,op:10}
};
const mk=(who,let0,out,ps,opts={})=>({
 who,let:let0,out,p:Array(18).fill(""),s:{6:opts.status||(out===6?"L":"winning")},
 alive:!out,flag:opts.missed?{6:"missed"}:{},def:{},ours:opts.ours||false,
 ...opts
});
const alice=mk("Alice","A",6,[],{ours:true}),bob=mk("Bob","B",6),
 carol=mk("Carol","C",5),drew=mk("Drew","D",0,[],{status:"losing"}),
 eve=mk("Eve","E",6,[],{missed:true}),frank=mk("Frank","F",6,[],{status:"T"}),
 grace=mk("Grace","G",0);
alice.p[5]="Chiefs";bob.p[5]="Chiefs/Raiders";carol.p[4]="Chiefs";
drew.p[5]="Bears";frank.p[5]="Vikings";grace.p[5]="Raiders";
const SV={cfg:{tieOut:true},lanes:[alice,bob,carol,drew,eve,frank,grace],elimQ:""};
const q={SV,svEval:()=>{},svPicks:(l,w)=>(l.p[w-1]||"").split("/").filter(Boolean),
 svRes:(w,t)=>records[t],isOurs:l=>!!l.ours,esc,svLogo:(w,t)=>'<span class="tl">'+esc(t.slice(0,3))+'</span>'};
const ctx=vm.createContext(q);
vm.runInContext(js+"\nthis.api={svEliminationData,svElimHtml}",ctx);
let checks=0;const ok=(label,pass)=>{assert(pass,label);checks++};
const data=ctx.api.svEliminationData(6);
ok("Current eliminations counted once",data.rows.length===4);
ok("Earlier eliminations excluded",!data.rows.some(x=>x.l.who==="Carol"));
ok("Ongoing-game trailing does not equal eliminated",data.risk.length===1&&data.risk[0].l.who==="Drew");
const b=data.rows.find(x=>x.l.who==="Bob");
ok("Multi-pick entry counted once",!!b&&b.ps.length===2&&b.losers.length===1);
ok("Correct losing team distinguished from safe team",b.primary==="Chiefs"&&!b.losers.includes("Raiders"));
ok("Missing selection separately identified",data.rows.some(x=>x.l.who==="Eve"&&x.reason==="missed"&&x.key==="__missed"));
ok("Tie is elimination when rules require it",data.rows.some(x=>x.l.who==="Frank"&&x.reason==="tied"));
const html=ctx.api.svElimHtml(6,data);
ok("Named participants visible",["Alice","Bob","Eve","Frank"].every(x=>html.includes(x)));
ok("Entry lane explicitly labeled",html.includes("Entry B")&&html.includes("Entry A"));
ok("Losing and surviving picks shown in same multi-pick row",html.includes("Chiefs")&&html.includes("Raiders")&&html.includes('sve-pick lost')&&html.includes('sve-pick safe'));
ok("Group counts correct",html.includes("2 entries")&&html.includes("No valid pick")&&html.includes("Vikings"));
ok("Compact pool shows entries without extra tapping",html.includes('<details class="sve-group" open>'));
ok("Hero jump and discoverable section implemented",source.includes('href="#svelim"')&&source.includes("Who got eliminated"));
ok("Elimination view placed after overview",source.includes('h+="<!--M:elim-->"'));
ok("Search UI wired",source.includes('querySelector("#svelq")'));
ok("Full pool toggle and more rows",source.includes('id="svall"')&&source.includes('id="svmore"')&&source.includes('SV.swimLimit=(SV.swimLimit||150)+150'));
ok("Eliminated search results shown automatically",source.includes('const reveal=SV.showOut||!!q'));
SV.elimQ="bob";const filtered=ctx.api.svElimHtml(6,data);
ok("Search filters by participant",filtered.includes("Bob")&&!filtered.includes("Alice</b>"));
SV.elimQ="vik";const byTeam=ctx.api.svElimHtml(6,data);
ok("Search filters by team name",byTeam.includes("Frank")&&!byTeam.includes("Alice</b>"));
SV.elimQ="does-not-exist";const none=ctx.api.svElimHtml(6,data);
ok("Empty search displays explanation",none.includes("No entries match"));
SV.elimQ="";SV.cfg.tieOut=false;
const tied=mk("Tied", "H",0);tied.p[5]="Vikings";tied.s[6]="W";
SV.lanes.push(tied);ok("Surviving ties not listed",!ctx.api.svEliminationData(6).rows.some(x=>x.l.who==="Tied"));
const many=Array.from({length:40},(_,i)=>{const x=mk("Person"+i,String(i),6);x.p[5]="Chiefs";return x});
SV.lanes=many;const big=ctx.api.svElimHtml(6,ctx.api.svEliminationData(6));
ok("Large elimination groups collapse initially",!big.includes('<details class="sve-group" open>'));
const unsafe=mk("<img src=x onerror=alert(1)>","J",6);unsafe.p[5]="Chiefs";SV.lanes=[unsafe];
const safe=ctx.api.svElimHtml(6,ctx.api.svEliminationData(6));
ok("Escapes names from sheet data",safe.includes("&lt;img")&&!safe.includes("<img src=x"));
ok("Version shipped",source.includes('WM_VERSION="1.27"'));
console.log("PASS survivor-eliminations: "+checks+" focused checks");
