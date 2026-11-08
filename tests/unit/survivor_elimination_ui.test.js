/* Wingman Survivor elimination drilldown regression: node tests/unit/survivor_elimination_ui.test.js index.html */
const fs=require("fs"),assert=require("assert");
const source=fs.readFileSync(process.argv[2],"utf8");
const a=source.indexOf("function svEliminationData("),b=source.indexOf("function svRender(",a);
assert(a>=0&&b>a,"Survivor elimination functions must be present");
const code=source.slice(a,b);
const SV={lanes:[],cfg:{tieOut:true},elimTeam:"",elimQ:"",elimOpen:{},elimRiskOpen:false};
const status={KC:{r:"L"},DET:{r:"L"},BUF:{r:"W"},SF:{r:"W"},LAR:{st:"in",me:9,op:13}};
SV.lanes=[
{who:"Parag",let:"A",p:["KC","BUF"],out:9,alive:false,s:{9:"L"},flag:{},def:{}},
{who:"Amish",let:"B",p:["KC"],out:9,alive:false,s:{9:"L"},flag:{},def:{}},
{who:"Sarju",let:"C",p:["DET"],out:9,alive:false,s:{9:"L"},flag:{},def:{}},
{who:"Rikin",let:"D",p:["LAR"],out:0,alive:true,s:{9:"losing"},flag:{},def:{}},
{who:"Ronak",let:"E",p:["SF"],out:0,alive:true,s:{9:"W"},flag:{},def:{}},
{who:"Jay",let:"F",p:[],out:9,alive:false,s:{9:"L"},flag:{},def:{9:"KC"}}
];
const deps={SV,svEval:()=>{},svPicks:l=>l.p,svRes:(w,t)=>status[t]||{},svLogo:(w,t)=>'<img class="tl" alt="'+t+'">',isOurs:l=>l.who==="Parag",esc:x=>String(x).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/"/g,"&quot;")};
const api=new Function(...Object.keys(deps),code+";return {svEliminationData,svElimHtml}")(...Object.values(deps));
let n=0;const test=(label,ok)=>{assert(ok,label);n++};
const data=api.svEliminationData(9);
test("confirmed eliminated entries counted once",data.rows.length===4);
test("at-risk entries not confirmed eliminated",data.risk.length===1&&data.risk[0].l.who==="Rikin");
test("multi-pick all teams preserved",data.rows.find(x=>x.l.who==="Parag").ps.length===2);
test("default pick correctly shown",data.rows.find(x=>x.l.who==="Jay").ps[0]==="KC");
test("default pick not mislabeled missed",data.rows.find(x=>x.l.who==="Jay").reason==="lost");
let html=api.svElimHtml(9,data);
test("all eliminated managers visible",["Parag","Amish","Sarju","Jay"].every(x=>html.includes(x)));
test("losing team summary present",html.includes('data-sve-team="KC"')&&html.includes('data-sve-team="DET"'));
test("default team labeled",html.includes("Default pick"));
test("trailing entries shown separately",html.includes("Rikin")&&html.includes("not eliminated"));
test("multi-pick losing and surviving teams distinguishable",html.includes("sve-pick lost")&&html.includes("sve-pick safe"));
SV.elimTeam="KC";html=api.svElimHtml(9,data);
test("team filter removes other losing team",html.includes("Parag")&&!html.includes("Sarju"));
SV.elimTeam="";SV.elimQ="sar";html=api.svElimHtml(9,data);
test("participant search",html.includes("Sarju")&&!html.includes("Amish"));
SV.elimQ="";SV.elimOpen={"9|KC":false};html=api.svElimHtml(9,data);
test("collapsed group persists across refresh",html.includes('data-sve-group="KC" ><summary>'));
test("hero jump has explicit expand handler",source.includes('SV.open.elim=true;save("svopen2"'));
test("live risk group toggle state retained",source.includes('SV.elimRiskOpen=riskPanel.open'));
test("UI version correct",source.includes('WM_VERSION="1.30"'));
console.log("PASS survivor-elimination-ui: "+n+" regression checks");
