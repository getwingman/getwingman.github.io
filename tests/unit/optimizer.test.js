/* Regression tests: exact lineup optimizer vs exhaustive brute force (node tests/optimizer.test.js <opt.js>) */
const fs=require("fs");
const ELIG2={QB:["QB"],RB:["RB"],WR:["WR"],TE:["TE"],K:["K"],DEF:["DEF"],FLEX:["RB","WR","TE"],SUPER_FLEX:["QB","RB","WR","TE"],REC_FLEX:["WR","TE"],WRRB_FLEX:["WR","RB"],DL:["DL","DE","DT"],LB:["LB","ILB","OLB"],DB:["DB","CB","S","SS","FS"],IDP_FLEX:["DL","DE","DT","LB","ILB","OLB","DB","CB","S","SS","FS"]};
const S={players:{}};const pinfo=id=>({pos:(S.players[id]||{}).fantasy_positions?.[0]||"WR"});
let SRC=fs.readFileSync(process.argv[2],"utf8");if(/\.html?$/.test(process.argv[2])){const a=SRC.indexOf("/* ---------- exact lineup optimizer ----------"),b=SRC.indexOf("/* ---------- Lineup IQ: completed weeks");SRC=SRC.slice(a,b)}
eval(SRC+";globalThis.bestLineup=bestLineup;globalThis.slotsLaminar=slotsLaminar");
let pass=0,fail=0;const ok=(n,c,info)=>{if(c)pass++;else{fail++;console.log("FAIL",n,info||"")}};
const el=s=>ELIG2[s]||[s];
function brute(ids,slots,vf,prefer){let best=null;const n=slots.length;
  const rec=(i,used,pts,filled,k)=>{if(i===n){if(!best||filled>best.filled||(filled===best.filled&&(pts>best.pts+1e-9||(Math.abs(pts-best.pts)<=1e-9&&k>best.k))))best={pts,filled,k};return}
    let any=false;for(const id of ids){if(used.has(id))continue;const e=S.players[id].fantasy_positions;if(!e.some(z=>el(slots[i]).includes(z)))continue;any=true;used.add(id);rec(i+1,used,pts+vf(id),filled+1,k+(prefer&&prefer.has(id)?1:0));used.delete(id)}
    rec(i+1,used,pts,filled,k)};rec(0,new Set(),0,0,0);return best}
let seed=7;const rnd=()=>(seed=(seed*1103515245+12345)%2147483648)/2147483648;
const POS=["QB","RB","WR","TE","K","DEF"],IDP=["DL","LB","DB"];
const CONFIGS={
 standard:["QB","RB","RB","WR","WR","TE","FLEX","K","DEF"],
 superflex:["QB","RB","RB","WR","WR","TE","FLEX","SUPER_FLEX"],
 twoqb:["QB","QB","RB","RB","WR","WR","WR","TE","FLEX","FLEX"],
 overlapping:["QB","RB","WR","TE","WRRB_FLEX","REC_FLEX","FLEX"],
 idp:["QB","RB","WR","TE","FLEX","DL","LB","DB","IDP_FLEX","IDP_FLEX"],
 tiny:["WRRB_FLEX","REC_FLEX"]};
for(const [name,slots] of Object.entries(CONFIGS)){
  for(let t=0;t<120;t++){S.players={};const ids=[];const N=4+Math.floor(rnd()*8);const posSet=name==="idp"?[...POS,...IDP]:POS;
    for(let i=0;i<N;i++){const id="p"+i,p=posSet[Math.floor(rnd()*posSet.length)];const e=[p];
      if(rnd()<.2){const q=posSet[Math.floor(rnd()*4)];if(q!==p)e.push(q)}         /* dual-position players */
      S.players[id]={fantasy_positions:e};ids.push(id)}
    const val={};ids.forEach(id=>val[id]=rnd()<.15?Math.round(rnd()*4)/1:rnd()<.08?-Math.round(rnd()*30)/10:Math.round(rnd()*300)/10); /* ties, zeros, negatives */
    const prefer=new Set(ids.filter(()=>rnd()<.4)),vf=id=>val[id];
    const sl=slots.slice(0,Math.min(slots.length,6+Math.floor(rnd()*4)));
    const got=bestLineup(ids,sl,vf,prefer),want=brute(ids,sl,vf,prefer);
    ok(`${name}#${t}`,Math.abs(got.pts-want.pts)<1e-6&&got.filled===want.filled,JSON.stringify({got:[got.pts,got.filled],want}));
    /* legality: every chosen player sits in a slot he can play, nobody twice */
    const seen=new Set();ok(`${name}#${t} legal`,got.by.every(([s,id])=>!id||(!seen.has(id)&&(seen.add(id),true)&&S.players[id].fantasy_positions.some(z=>el(s).includes(z)))));
  }
}
/* known cases */
S.players={a:{fantasy_positions:["QB","TE"]},b:{fantasy_positions:["QB"]},c:{fantasy_positions:["TE"]}};
let r=bestLineup(["a","b","c"],["QB","TE"],id=>({a:20,b:18,c:5})[id]);ok("QB/TE dual player goes to TE",r.pts===38,r.pts);
S.players={w1:{fantasy_positions:["WR"]},r1:{fantasy_positions:["RB"]},t1:{fantasy_positions:["TE"]}};
r=bestLineup(["w1","r1","t1"],["WRRB_FLEX","REC_FLEX"],id=>({w1:20,r1:15,t1:10})[id]);ok("overlapping flexes: WR to W/T is wrong, best is WR+RB? no: W/R=r1,W/T=w1",r.pts===35,r.pts);
S.players={q:{fantasy_positions:["QB"]},d:{fantasy_positions:["DEF"]}};
r=bestLineup(["q","d"],["QB","RB","DEF"],id=>({q:10,d:-3})[id]);ok("empty slot stays empty, negative DEF still starts (legal lineup)",r.filled===2&&r.pts===7,r);
S.players={x:{fantasy_positions:["WR"]},y:{fantasy_positions:["WR"]}};
r=bestLineup(["x","y"],["WR"],id=>10,new Set(["y"]));ok("tie goes to the player actually started",r.set.has("y"));
console.log(`optimizer: ${pass} passed, ${fail} failed`);process.exit(fail?1:0);
