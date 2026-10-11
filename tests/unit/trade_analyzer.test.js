/* Wingman Edge Trade Analyzer: run with node tests/unit/trade_analyzer.test.js index.html */
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const src=fs.readFileSync(process.argv[2],"utf8"),names=["twState","twOwner","twEvaluate","twSuggestions","twHTML"];
const parts=names.map(name=>{const a=src.indexOf("function "+name+"("),b=src.indexOf("\nfunction ",a+9);assert(a>=0,"Missing "+name);return src.slice(a,b<0?src.length:b)});
const players={
 a:{full_name:"Christian McCaffrey",team:"SF",position:"RB",fantasy_positions:["RB"],years_exp:6},
 b:{full_name:"Josh Allen",team:"BUF",position:"QB",fantasy_positions:["QB"],years_exp:7},
 g:{full_name:"A.J. Brown",team:"PHI",position:"WR",fantasy_positions:["WR"],years_exp:6},
 h:{full_name:"Courtland Sutton",team:"DEN",position:"WR",fantasy_positions:["WR"],years_exp:8},
 c:{full_name:"Saquon Barkley",team:"PHI",position:"RB",fantasy_positions:["RB"],years_exp:8},
 d:{full_name:"Lamar Jackson",team:"BAL",position:"QB",fantasy_positions:["QB"],years_exp:8},
 e:{full_name:"Nico Collins",team:"HOU",position:"WR",fantasy_positions:["WR"],years_exp:5},
 f:{full_name:"Jaylen Waddle",team:"MIA",position:"WR",fantasy_positions:["WR"],years_exp:6}
};
const values={a:14,b:24,g:17,h:8,c:18,d:22,e:15,f:12};
const lg={id:"qa",mineRid:1,league:{name:"QA League",settings:{},roster_positions:["QB","RB","WR","BN"]},
 rosters:[{roster_id:1,players:["a","b","g","h"]},{roster_id:2,players:["c","d","e","f"]}]};
const elig={QB:["QB"],RB:["RB"],WR:["WR"]};
const bestLineup=(ids,slots,vf)=>{const used=new Set(),set=new Set();let pts=0;
 for(const sl of slots){const id=ids.filter(id=>!used.has(id)&&players[id]&&players[id].position===sl).sort((a,b)=>vf(b)-vf(a))[0];if(id){used.add(id);set.add(id);pts+=vf(id)}}
 return{pts,set}};
const line=ids=>bestLineup(ids,["QB","RB","WR"],id=>values[id]).pts;
const mine={rid:1,ids:["a","b","g","h"],wks:[line(["a","b","g","h"]),line(["a","b","g","h"])],name:"Mine",mine:true};
const theirs={rid:2,ids:["c","d","e","f"],wks:[line(["c","d","e","f"]),line(["c","d","e","f"])],name:"Theirs",mine:false};
const wk=Object.fromEntries(Object.entries(values).map(([id,val])=>[id,[val,val]]));
const R={ws:[7,8],wk,slots:["QB","RB","WR"],me:mine,teams:[mine,theirs],
 V:id=>values[id],aval:id=>values[id],strength:line,
 swap:(ids,give,get)=>ids.filter(x=>!give.includes(x)).concat(get),prof:{}};
const MV={tw:{qa:{give:["a"],get:["c"],partner:""}},trend:{},news:{}};
const context={S:{players,nflWeek:6},MV,ELIG2:elig,pinfo:id=>({name:players[id]?.full_name||id,pos:players[id]?.position||"WR",inj:""}),
 bestLineup,edgeLeagues:()=>[lg],load:()=>"",esc:x=>String(x)};
vm.createContext(context);vm.runInContext(parts.join("\n"),context);
let passed=0;
function check(name,expr){assert(expr,name);passed++}
const basic=context.twEvaluate(lg,R,{give:["a"],get:["c"],partner:""});
check("valid 1-for-1",basic.ok&&basic.sides.length===2);
check("auto-detects partner",String(basic.other.rid)==="2");
check("my lineup improves",basic.sides[0].gain===4);
check("theirs gets worse",basic.sides[1].gain===-4);
check("separate decision scores",basic.sides[0].score>basic.sides[1].score);
check("scores bounded",basic.sides.every(x=>x.score>=0&&x.score<=100));
check("substring anywhere in first name",context.twSuggestions(lg,R,{give:[],get:[]},"get","mar").some(x=>x.id==="d"));
check("substring in surname",context.twSuggestions(lg,R,{give:[],get:[]},"give","Caff").some(x=>x.id==="a"));
check("initials with punctuation",context.twSuggestions(lg,R,{give:[],get:[]},"give","AJ").some(x=>x.id==="g"));
check("ranks my roster first",context.twSuggestions(lg,R,{give:[],get:[]},"give","a")[0].relevant);
check("missing side isn't scored",!context.twEvaluate(lg,R,{give:[],get:["c"],partner:""}).ok);
check("rejects wrong ownership",!context.twEvaluate(lg,R,{give:["c"],get:["a"],partner:"2"}).ok);
check("rejects cross-team package",!context.twEvaluate(lg,R,{give:["a"],get:["c","b"],partner:""}).ok);
check("rejects duplicate player",!context.twEvaluate(lg,R,{give:["a"],get:["a"],partner:"2"}).ok);
check("rejects more than 4",!context.twEvaluate(lg,R,{give:["a","b","g","h","c"],get:["d"],partner:"2"}).ok);
check("doesn't score without projections",!context.twEvaluate(lg,{...R,wk:{...wk,a:undefined}},{give:["a"],get:["c"],partner:""}).ok);
const multi=context.twEvaluate(lg,R,{give:["a"],get:["c","e","f"],partner:"2"});
check("multi-player packages work",multi.ok);
check("roster-cut count correct",multi.sides[0].cuts.length===2);
check("roster cap enforced",multi.sides[0].team.rid===1&&multi.sides[0].warn.some(x=>x.includes("Roster limit")));
check("roster cuts affect asset tally",multi.sides[0].asset<values.c+values.e+values.f-values.a);
const html=context.twHTML(lg,R);
check("both scorecards render",html.includes("YOUR SIDE")&&html.includes("THEIR SIDE"));
check("editable chips render",html.includes('data-tw-rm="a"')&&html.includes('data-tw-rm="c"'));
check("weekly impact renders",html.includes("W7")&&html.includes("W8"));
check("four max visible",html.includes("1/4 players"));
check("scores change with player change",context.twEvaluate(lg,R,{give:["a"],get:["c"],partner:""}).sides[0].score!==context.twEvaluate(lg,R,{give:["a"],get:["f"],partner:""}).sides[0].score);
console.log("PASS trade-analyzer: "+passed+" regression checks");