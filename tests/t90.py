import sys,json;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
SV2="SV2testsheet00000000000001";PK2="PK2testsheet00000000000001"
with sync_playwright() as p:
    b=p.chromium.launch()
    for W,tag in [(1500,"d"),(390,"m")]:
        pg=b.new_page(viewport={"width":W,"height":1000},is_mobile=W<800,has_touch=W<800);e=[];pg.on("pageerror",lambda x:e.append(str(x)))
        pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
        pg.add_init_script("localStorage.setItem('lm_user','xParRaidr');localStorage.setItem('lm_conns',%r)"%json.dumps([{"key":"sleeper:x","p":"sleeper","username":"xParRaidr"},{"key":"survivor:"+SV2,"p":"survivor","sheet":SV2},{"key":"pickem:"+PK2,"p":"pickem","sheet":PK2}]))
        pg.goto(F);pg.wait_for_timeout(5000);pg.evaluate("SV.open.plan=true;setTab('s')");pg.wait_for_timeout(4000)
        if tag=="d":
            st=pg.evaluate("[SV.layout,SV.lanes&&SV.lanes.length,SV.flagged,SV.lanes&&SV.lanes.filter(isOurs).length,SV.maxPick]")
            chk("survivor: normalized layout parsed (761 entries, 12 flagged ours, picks through W5)",st==["normalized",761,True,12,5],st)
            c=pg.evaluate("(()=>{const c=SV.cfg;return[c.name,c.reuse,c.price,c.split,c.jackpot,c.missed,c.days&&c.days.thursday,c.days&&c.days.friday,c.me]})()")
            chk("survivor: rules self-configure from Config",c==["Test Survivor Pool","gap1",25,4,19025,"default","no","pending","Our Group"],c)
            chk("survivor: no 'which entries are yours' prompt",not pg.is_visible("#svme"))
            bad=pg.evaluate("""(()=>{const V=SV.week||Math.min(SV.maxPick||1,18),N=V+1;const ours=SV.lanes.filter(isOurs),bad=[];let n=0;
              document.querySelectorAll('#surv .pmx .pmr:not(.pmh)').forEach(row=>{const t=row.querySelector('.pmt b').textContent;row.querySelectorAll('.pmc').forEach(c=>{const L=c.title.match(/Life (\\w+)/)[1],l=ours.find(x=>x.let===L);n++;if(c.classList.contains('ok')&&svUsed(l,N).get(t)===N-1)bad.push(L+':'+t)})});
              const planTeams=[...document.querySelectorAll('#surv .svplan .svpt')].map(x=>[x.querySelector('b').textContent,[...x.querySelectorAll('.ltk')].map(i=>i.textContent)]);
              planTeams.forEach(([t,ls])=>ls.forEach(L=>{const l=ours.find(x=>x.let===L);if(!svCanUse(l,t,N).ok)bad.push('plan '+L+':'+t)}));return{bad,n,plans:document.querySelectorAll('#surv .svplan').length,planTeams}})()""")
            chk("survivor planner: every ✓ and every plan pick is eligible",bad["n"]>0 and not bad["bad"] and bad["plans"]>=1,bad)
            pg.screenshot(path=OUT+"/sv2_d.png",full_page=True)
            # pick'em
            pg.evaluate("setTab('p')");pg.wait_for_timeout(3000)
            chk("pick'em: no 'which member' prompt (matched to the Sleeper username)",not pg.is_visible("#pkme") and pg.evaluate("PK.cfg.me")=="xParRaidr" and pg.evaluate("PK.cfg.meAuto")==1,pg.evaluate("PK.cfg.me"))
            cons=pg.evaluate("[...document.querySelectorAll('#pick .svh')].map(x=>x.innerText.split('\\n')[0])")
            chk("pick'em: 'You vs the pool' table once picks are visible",any("You vs the pool" in c for c in cons) and pg.evaluate("document.querySelectorAll('#pick .pkc tbody tr').length")>=10,cons)
            fl=pg.evaluate("""(()=>{const r=[...document.querySelectorAll('#pick .pah')].map(x=>({flip:x.classList.contains('flip'),star:!!x.querySelector('.lz'),bar:!!x.querySelector('.cov i'),toss:!!x.querySelector('.tossup')}));return{n:r.length,bad:r.filter(x=>x.flip&&(x.star||x.bar)||(!x.flip&&x.toss)).length,flips:r.filter(x=>x.flip).length}})()""")
            chk("pick'em: coin flips (<55%) get no star / bar, only a muted toss-up",fl["bad"]==0,fl)
            st=pg.evaluate("[PK.layout,PK.rows.length,PK.weeks,PK.d.games.length,PK.missing,PK.cfg.name,PK.cfg.dues]")
            chk("pick'em: WM tables parsed",st[0]=="normalized" and st[1]==23 and st[2]==4 and st[3]>=270 and st[5]=="Test Pick'em" and st[6]==50,st)
            # standings = authoritative points from WM_Picks; compare to legacy Standings tab
            leg={r[1]:sum(int(x) for x in r[2:6] if x.strip()) for r in __import__('csv').reader(open('fixtures/v2/pk2_Standings.csv')) if r and r[0] and r[0][0] in "0123456789T" and r[0]!="Rank"}
            mine=pg.evaluate("Object.fromEntries(PK.rows.map(r=>[r.u,r.w.reduce((a,b)=>a+b,0)]))")
            diff={k:(v,leg.get(k)) for k,v in mine.items() if leg.get(k)!=v}
            chk("pick'em standings match the pool's own Standings tab (W1–W4)",not diff,diff)
            tbw=pg.evaluate("Object.keys(PK.tb||{})");chk("tiebreakers loaded",len(tbw)>=1,tbw)
            sl=pg.evaluate("[pkSheetLine(5,'DAL','TB'),pkSheetLine(5,'TB','DAL'),pkSheetLine(1,'NE','SEA'),pkSheetLine(6,'X','Y')]")
            chk("sheet lines: team_a/team_b order handled, proxies labeled",sl[0]["hs"]==-9.5 and sl[1]["hs"]==9.5 and "proxy" in sl[2]["src"] and sl[3] is None,sl)
            pg.screenshot(path=OUT+"/pk2_d.png",full_page=True)
        else:
            chk("phone survivor: no horizontal scroll",pg.evaluate("document.documentElement.scrollWidth")<=W,pg.evaluate("document.documentElement.scrollWidth"))
            pg.screenshot(path=OUT+"/sv2_m.png",full_page=True)
            pg.evaluate("setTab('p')");pg.wait_for_timeout(3000)
            chk("phone pick'em: identified without asking",not pg.is_visible("#pkme"))
            chk("phone pick'em: no horizontal scroll",pg.evaluate("document.documentElement.scrollWidth")<=W)
            pg.screenshot(path=OUT+"/pk2_m.png",full_page=True)
        chk(f"no errors {tag}",not e,e[:3]);pg.close()
    b.close()
print("FAILED:",fails)
