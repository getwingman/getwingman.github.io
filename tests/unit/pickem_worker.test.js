/* Secure Worker Pick'em reader regression. node tests/unit/pickem_worker.test.js */
const assert=require("assert"),fs=require("fs"),path=require("path"),vm=require("vm");
const worker=fs.readFileSync(path.resolve(__dirname,"../../wingman-connect-worker.js"),"utf8");
const a=worker.indexOf("async function pickemSeason("),b=worker.indexOf("/* ---------------- Yahoo OAuth",a);
assert(a>=0&&b>a,"Pick'em Worker route missing");
let seen=[],calls=0;
const net=async(url,opts={})=>{
  calls++;seen.push({url,opts});
  const respond=x=>({ok:true,status:200,json:async()=>x});
  if(url.endsWith("/rosters"))return respond([{roster_id:1,owner_id:"u1"}]);
  if(url.endsWith("/users"))return respond([{user_id:"u1",username:"qauser",display_name:"QA Player"}]);
  if(url.includes("/scores/"))return respond([
    {game_id:"g1",status:"complete",metadata:{home_team:"KC",away_team:"BUF",home_score:28,away_score:21}},
    {game_id:"g2",status:"in_progress",metadata:{home_team:"SF",away_team:"SEA",home_score:7,away_score:0}}
  ]);
  if(url==="https://sleeper.com/graphql"){
    assert(opts.headers.Authorization==="SESSION_TOKEN","Worker did not use server-side Sleeper session");
    assert(!JSON.stringify(opts).includes("VIEW_KEY_FOR_TEST_12345"),"Viewing key leaked to Sleeper");
    return respond({data:{get_pickem_picks_for_league:{"1":{picks:{
      g1:{team:"KC",outcome:"win"},g2:{team:"SF",outcome:"win"}
    }}}}});
  }
  throw Error("Unexpected upstream request "+url);
};
const ctx=vm.createContext({fetch:net,Response,TextEncoder,Date,URL,JSON,Number,String,Object,Array,Map,Math});
vm.runInContext(worker.slice(a,b)+"\nthis.pickemSeason=pickemSeason",ctx);
const h=key=>({get:k=>k==="Origin"?"https://getwingman.github.io":k==="X-WM-Pickem-Key"?key:null});
const url=new URL("https://worker.example/pickem/season?season=2026&week=5&upto=5");
const env={ALLOWED_ORIGIN:"https://getwingman.github.io",SLEEPER_TOKEN:"SESSION_TOKEN",
 WM_PICKEM_VIEW_KEY:"VIEW_KEY_FOR_TEST_12345",WM_PICKEM_POOL_ID:"1392587441361129472"};
let n=0;const ok=(name,v)=>{assert(v,name);n++};
(async()=>{
  let r=await ctx.pickemSeason({headers:h("BAD")},url,env,{});
  ok("invalid viewer key rejected",r.status===401);ok("no upstream call after rejected key",calls===0);
  r=await ctx.pickemSeason({headers:h("VIEW_KEY_FOR_TEST_12345")},url,{...env,SLEEPER_TOKEN:null},{});
  ok("missing session rejected",r.status===503);
  r=await ctx.pickemSeason({headers:h("VIEW_KEY_FOR_TEST_12345")},url,env,{});
  const j=await r.json();
  ok("authorized reader returns success",r.status===200&&j.ok);
  ok("one authenticated entry",j.pool.entries.length===1&&j.pool.entries[0].username==="qauser");
  ok("scores contain two games",j.weeks[0].games.length===2);
  const [fin,live]=j.weeks[0].games;
  ok("only completed game is final",fin.final===true&&live.final===false);
  ok("picks revealed only after final",fin.picks.length===1&&fin.picks[0].team==="KC"&&live.picks.length===0);
  ok("worker doesn't treat outcome win as a graded result",!fin.picks[0].grade&&!fin.picks[0].points);
  ok("server session token not in output",!JSON.stringify(j).includes(env.SLEEPER_TOKEN));
  ok("viewer key not in output",!JSON.stringify(j).includes(env.WM_PICKEM_VIEW_KEY));
  console.log("PASS pickem-worker: "+n+" regression checks");
})().catch(e=>{console.error("FAIL",e.stack||e);process.exitCode=1});
