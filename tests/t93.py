"""v43 mobile: slot pill centred in its column, full player names (3-row cells), Lab fun-stats strip, one full-width Trades module"""
import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
LONG="""(()=>{const N={'202':'Amon-Ra St. Brown','204':'Ashton Jeanty','205':'Cam Skattebo','300':"Ja'Marr Chase",'203':'Zay Flowers','900':'Tucker Kraft'};for(const k in N)S.players[k].full_name=N[k];S.players['204'].injury_status='Questionable';S.players['203'].injury_status='Questionable';S.pc={};S.L.forEach(l=>{l.lastHtml="";render(l)})})()"""
with sync_playwright() as p:
    b=p.chromium.launch()
    for W in (344,390,412):
        mock.PREGAME[0]=False;pg=b.new_page(viewport={"width":W,"height":900},is_mobile=True,has_touch=True);e=[];pg.on("pageerror",lambda x:e.append(str(x)))
        pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
        pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(6000);pg.evaluate(LONG);pg.wait_for_timeout(500)
        sl=pg.evaluate("""[...document.querySelectorAll('.lg td.pos .slot')].map(s=>{const r=s.getBoundingClientRect(),t=s.parentElement.getBoundingClientRect();return[+(r.left-t.left).toFixed(1),+(t.right-r.right).toFixed(1)]})""")
        chk(f"[{W}] slot pills sit inside the middle column, centred",sl and all(a>=0 and c>=0 and abs(a-c)<=1.5 for a,c in sl),sl[:4])
        nm=pg.evaluate("""[...document.querySelectorAll('.lg td[data-pos] .nm')].filter(n=>n.offsetParent).map(n=>[n.textContent.replace(/^.*?([A-Z]\\. .*)$/,'$1'),n.scrollWidth>n.clientWidth+1])""")
        tr=[n for n,t in nm if t]
        chk(f"[{W}] player names not truncated (tags moved to row 2)",len(nm)>=10 and not tr,tr)
        rows=pg.evaluate("[...new Set([...document.querySelectorAll('.lg tr.pr')].map(r=>Math.round(r.getBoundingClientRect().height)))]")
        chk(f"[{W}] matchup rows keep one height",len(rows)<=2,rows)
        chk(f"[{W}] no horizontal page scroll",pg.evaluate("document.documentElement.scrollWidth")<=W)
        if W==412:
            mock.TRADES[0]=True;pg.evaluate("MV.res={};setTab('t')");pg.wait_for_timeout(9000)
            f=pg.evaluate("(()=>{const s=document.querySelector('#moves .funs');return s?{cs:getComputedStyle(s).overflowX,sw:s.scrollWidth,cw:s.clientWidth,n:s.querySelectorAll('.awd,.pmvc').length}:null})()")
            chk("Lab fun stats: one horizontal scrolling strip on phones",f and f["cs"]=="auto" and f["sw"]>f["cw"] and f["n"]>=5,f)
            hs=pg.evaluate("[...document.querySelectorAll('#moves .svh')].map(x=>x.innerText.split('\\n')[0].replace(/^[▾▸]/,'').trim())")
            chk("Lab: 2-way and 3-way trades live in one Trades module",sum(1 for x in hs if "Trades" in x or "3-way" in x)==1,hs)
            pg.click("#moves [data-tv='p']");pg.wait_for_timeout(300)
            chk("Trades: By partner view groups deals by manager",pg.evaluate("document.querySelectorAll('#moves .tbr').length")>=11)
            pg.click("#moves [data-tv='b']");pg.wait_for_timeout(300);chk("Trades: back to Best deals",pg.evaluate("document.querySelectorAll('#moves .tdr').length")>=1)
            chk("Lab phone: no horizontal page scroll",pg.evaluate("document.documentElement.scrollWidth")<=W)
            mock.TRADES[0]=False
        chk(f"[{W}] no errors",not e,e[:2]);pg.close()
    b2=b.new_page(viewport={"width":1500,"height":1000});mock.TRADES[0]=True
    b2.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    b2.add_init_script("localStorage.setItem('lm_user','xParRaidr')");b2.goto(F);b2.wait_for_timeout(5000);b2.evaluate("setTab('t')");b2.wait_for_timeout(9000)
    w=b2.evaluate("(()=>{const t=[...document.querySelectorAll('#moves .svc')].find(c=>c.classList.contains('wide')),bd=document.querySelector('#moves .svc');return t&&bd?[Math.round(t.getBoundingClientRect().width),Math.round(bd.getBoundingClientRect().width)]:null})()")
    chk("desktop: Trades module spans the full width like the board",w and abs(w[0]-w[1])<=2,w)
    mock.TRADES[0]=False;b.close()
print("FAILED:",fails)
