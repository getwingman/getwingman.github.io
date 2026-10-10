"""Survivor eligibility + pool data isolation + Pick'em completeness"""
import sys,csv,io;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F=sys.argv[1];OUT=sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
SV1="SURVtestsheet0000000000001";SV2="SURVtestsheet0000000000002";PK1="PICKtestsheet0000000000001"
def page(b,seed_conns=None,w=1500,hgt=1000,mobile=False):
    pg=b.new_page(viewport={"width":w,"height":hgt},is_mobile=mobile,has_touch=mobile);errs=[];pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    js="localStorage.setItem('lm_user','xParRaidr');"
    if seed_conns is not None:js+="localStorage.setItem('lm_conns',%r);"%seed_conns
    pg.add_init_script(js);pg.goto(F);pg.wait_for_timeout(4500);return pg,errs
def link(pg,p,sid):
    pg.click("#who");pg.wait_for_timeout(200);pg.click(f'.pcard[data-p={p}] .pcta');pg.wait_for_timeout(200)
    pg.fill("#shurl",f"https://docs.google.com/spreadsheets/d/{sid}/edit");pg.click("#shgo");pg.wait_for_timeout(2500)
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---------- public page carries no pool data ----------
    src=open(F.replace("file://","")).read()
    leaked=[w for w in __import__("json").load(open("fixtures/forbidden.json")) if w in src]
    chk("no personal pool data or sheet IDs in the public HTML",not leaked,leaked)
    # ---------- new user: nothing from anyone else's pool ----------
    pg,errs=page(b)
    chk("new user: no Survivor / Pick'em tabs",pg.evaluate("['s','p'].map(t=>document.querySelector(`header .tb[data-t=${t}]`).style.display)")==["none","none"])
    chk("new user: Survivor/Pick'em state empty",pg.evaluate("[SV.lanes,PK.rows,SV.d.sheet,PK.d.sheet]")==[None,None,"",""])
    # ---------- link a survivor sheet ----------
    link(pg,"survivor",SV1);pg.click('#wback');pg.click('header .tb[data-t="s"]');pg.wait_for_timeout(2500)
    chk("survivor: asks which entries are yours (no assumption)",pg.is_visible("#svme"),pg.evaluate("document.getElementById('surv').innerText.slice(0,120)"))
    opts=pg.evaluate("[...document.querySelectorAll('#svme option')].map(o=>o.value)");chk("participants come from the sheet",len(opts)>50 and "Our Group" in opts,len(opts))
    pg.select_option("#svme","Our Group");pg.click("#svmego");pg.wait_for_timeout(1500)
    chk("survivor dashboard renders for the chosen participant",pg.evaluate("document.querySelectorAll('#surv .tok').length")==12,pg.evaluate("document.querySelectorAll('#surv .tok').length"))
    # ---------- rule engine ----------
    r=pg.evaluate("""(()=>{const L=(p,out)=>({who:'x',let:'Z',p,out:out||0,def:{}});const c=x=>{SV.cfg=Object.assign({},SV.cfg,x)};const out={};
      const l=L(['Bills','Chiefs','','Bills']);
      c({reuse:'once'});out.once=[svCanUse(l,'Bills',5).ok,svCanUse(l,'Chiefs',5).ok,svCanUse(l,'Lions',5).ok];
      c({reuse:'gap1'});out.gap1=[svCanUse(l,'Bills',5).ok,svCanUse(l,'Chiefs',5).ok];
      c({reuse:'any'});out.any=[svCanUse(l,'Bills',5).ok];
      c({reuse:'once'});const m=L(['Bills/Chiefs','Lions']);out.multi=[svCanUse(m,'Bills',3).ok,svCanUse(m,'Chiefs',3).ok,svCanUse(m,'Lions',3).ok,svCanUse(m,'Rams',3).ok];
      out.elim=svCanUse(L(['Bills'],2),'Rams',3).ok;out.why=svCanUse(l,'Bills',5).why;c({reuse:'gap1'});return out})()""")
    chk("once-per-season: any earlier week blocks the team",r["once"]==[False,False,True],r["once"])
    chk("no back-to-back: only last week's team blocked",r["gap1"]==[False,True],r["gap1"])
    chk("no limit",r["any"]==[True])
    chk("multi-pick weeks: every team in the cell counts as used",r["multi"]==[False,False,False,True],r["multi"])
    chk("eliminated entries are never eligible",r["elim"] is False)
    chk("reason shown",r["why"]=="used W4",r["why"])
    ms=pg.evaluate("""(()=>{const keep=SV.res;SV.res={};SV.res[1]={Bills:{r:'W',st:'post'},Chiefs:{r:'L',st:'post'},Lions:{r:'W',st:'post'}};const save=SV.lanes;SV.lanes=[{who:'a',let:'A',p:['Bills/Chiefs']},{who:'b',let:'B',p:['Bills/Lions']}];svEval(1,false);const o=SV.lanes.map(l=>[l.alive,l.s[1]]);SV.lanes=save;SV.res=keep;return o})()""")
    chk("multi-pick week: every pick has to win",ms==[[False,"L"],[True,"W"]],ms)
    # planner never recommends an ineligible team: check every ✓ against full history, for each rule
    for rule in ["once","gap1"]:
        pg.evaluate(f"SV.open.plan=true;savePoolCfg('survivor',{{reuse:'{rule}'}});svRender()");pg.wait_for_timeout(300)
        bad=pg.evaluate("""(()=>{const V=SV.week||Math.min(SV.maxPick||1,18),N=V+1;svEval(V,false);const ours=SV.lanes.filter(isOurs),bad=[];let n=0;
          document.querySelectorAll('#surv .pmx .pmr:not(.pmh)').forEach(row=>{const t=row.querySelector('.pmt b').textContent;row.querySelectorAll('.pmc').forEach(c=>{const L=c.title.match(/Life (\\w+)/)[1],l=ours.find(x=>x.let===L);n++;
            const used=svUsed(l,N);const okRule=SV.cfg.reuse==='once'?!used.has(t):SV.cfg.reuse==='gap1'?used.get(t)!==N-1:true;if(c.classList.contains('ok')&&!okRule)bad.push(L+':'+t)})});return{bad,n}})()""")
        chk(f"planner ({rule}): no ✓ on a team the entry can't use ({bad['n']} cells checked)",bad["n"]>0 and not bad["bad"],bad)
    # ---------- broken sheet rows + private sheet ----------
    rows=list(csv.reader(open('fixtures/sv_swimlanes.csv',encoding='utf-8')));rows.insert(4,["#REF!"]+[""]*20)
    buf=io.StringIO();csv.writer(buf,quoting=csv.QUOTE_ALL,lineterminator="\n").writerows(rows);mock.SHEET_OVERRIDE[(SV2,"🏊 Swimlanes")]=buf.getvalue();mock.SHEET_OVERRIDE[(SV2,"⚙️ Our Picks Data")]="\"\"\n"
    # switch to a different survivor sheet (unlink, link another): whole context resets
    pg.click("#who");pg.click('.pcard[data-p=survivor] .pcta');pg.wait_for_timeout(200);pg.click("#pvform .cx");pg.wait_for_timeout(300);pg.click('#wback') if pg.is_visible('#wback') else None
    link(pg,"survivor",SV2);pg.click('#wback');pg.click('header .tb[data-t="s"]');pg.wait_for_timeout(2500)
    chk("switching sheets resets the pool context (asks again)",pg.is_visible("#svme") and pg.evaluate("SV.d.sheet")==SV2)
    pg.select_option("#svme","Our Group");pg.click("#svmego");pg.wait_for_timeout(1200)
    chk("#REF! rows flagged, not silently dropped",pg.evaluate("SV.broken")==1 and "#REF!" in pg.evaluate("document.querySelector('#surv .mt').innerText"),pg.evaluate("document.querySelector('#surv .mt').innerText"))
    pg.screenshot(path=OUT+"/surv40.png",full_page=False)
    # unlink → everything cleared
    pg.click("#who");pg.click('.pcard[data-p=survivor] .pcta');pg.wait_for_timeout(200);pg.click("#pvform .cx");pg.wait_for_timeout(300)
    chk("unlinking clears the pool from memory and hides the tab",pg.evaluate("[SV.lanes,SV.d.sheet,document.querySelector('header .tb[data-t=s]').style.display]")==[None,"","none"])
    chk("no errors (survivor)",not errs,errs[:3])
    pg.close()
    # private sheet
    pg,errs=page(b,'[{"key":"sleeper:xparraidr","p":"sleeper","username":"xParRaidr"},{"key":"survivor:PRIVtestsheet00000000001","p":"survivor","sheet":"PRIVtestsheet00000000001"}]')
    pg.click('header .tb[data-t="s"]');pg.wait_for_timeout(2000)
    chk("private sheet: clear message + Try again (no raw error)",pg.is_visible("#svretry") and "Anyone with the link" in pg.evaluate("document.getElementById('surv').innerText"),pg.evaluate("document.getElementById('surv').innerText"))
    pg.close()
    # ---------- Pick'em ----------
    pg,errs=page(b,'[{"key":"sleeper:xparraidr","p":"sleeper","username":"xParRaidr"},{"key":"pickem:%s","p":"pickem","sheet":"%s"}]'%(PK1,PK1))
    pg.click('header .tb[data-t="p"]');pg.wait_for_timeout(3000)
    chk("pick'em: identifies you from your Sleeper username (no prompt)",not pg.is_visible("#pkme") and pg.evaluate("PK.cfg.me")=="xParRaidr",pg.evaluate("PK.cfg.me"))
    chk("pick'em renders standings for all members",pg.evaluate("document.querySelectorAll('#pick .pkt2 tbody tr').length")==23,pg.evaluate("document.querySelectorAll('#pick .pkt2 tbody tr').length"))
    chk("no fixed row limit in requests",all(rg=="" for sid,tab,rg in mock.SHEET_HITS if sid.startswith("PICK")),[h for h in mock.SHEET_HITS if h[2]][:2])
    chk("money hidden until the user enters payouts",not any(x in pg.evaluate("document.querySelector('#pick .hu').innerText") for x in ["$"]),pg.evaluate("document.querySelector('#pick .hu').innerText"))
    chk("fixture is complete: no missing weeks / mismatches",pg.evaluate("[PK.missing,PK.mism]")==[[],[]],pg.evaluate("[PK.missing,PK.mism]"))
    # a full season (6,600+ pick rows) parses completely
    big=pg.evaluate("""(()=>{const P=[['Season','Week','Player','Game','Away','','Away Score','Home','','Home Score','Pick','','SU Winner','ATS Winner','Result']],S=[['Rank','Player',...Array.from({length:18},(_,i)=>'W'+(i+1)),'Total']];
      const us=Array.from({length:23},(_,i)=>'u'+i);us.forEach((u,ui)=>{const ws=[];for(let w=1;w<=18;w++){let c=0;for(let g=0;g<16;g++){const ok=(ui+g+w)%2===0;if(ok)c++;P.push(['2026',w,u,w+'-'+g,'A'+g,'',10,'H'+g,'',20,ok?'H'+g:'A'+g,'','H'+g,'H'+g,ok?'Correct':'Incorrect'])}ws.push(c)}S.push([ui+1,u,...ws,ws.reduce((a,b)=>a+b,0)])});
      const x=pkParse(P.map(r=>r.map(String)),S.map(r=>r.map(String)));return[P.length-1,x.games.length,x.picks.length,Math.max(...x.games.map(g=>g[0])),x.missing.length,x.mism.length]})()""")
    chk("full season: 6,624 pick rows, all 18 weeks parsed, totals agree",big==[6624,288,6624,18,0,0],big)
    # partial import is detected
    part=pg.evaluate("""(()=>{const P=[['Season','Week','Player','Game','Away','','Away Score','Home','','Home Score','Pick','','SU Winner','ATS Winner','Result'],['2026','1','a','1-0','X','','1','Y','','2','Y','','Y','Y','Correct']],S=[['Rank','Player','W1','W2'],['1','a','1','5']];const x=pkParse(P,S);return[x.missing,x.mism]})()""")
    chk("partial import flagged (W2 standings but no W2 picks)",part==[[2],[]],part)
    chk("no errors (pick'em)",not errs,errs[:3])
    pg.screenshot(path=OUT+"/pick40.png");b.close()
print("FAILED:",fails)
