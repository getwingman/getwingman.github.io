import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,F38,OUT=sys.argv[1],sys.argv[2],sys.argv[3];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
reqs=[0]
def route(pg):
    def h(r):
        if r.request.url.startswith(("file:","data:")):return r.continue_()
        reqs[0]+=1;return mock.handle(r)
    pg.route("**/*",h)
with sync_playwright() as p:
    b=p.chromium.launch()
    # desktop geometry unchanged vs v38
    geo={}
    for tag,f in [("v38",F38),("v39",F)]:
        pg=b.new_page(viewport={"width":1500,"height":1000});route(pg);pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(f);pg.wait_for_timeout(5000)
        geo[tag]=pg.evaluate("""['header','header .tabs','header .tb[data-t=m]','header .tb[data-t=f]','#lgs','#week','.lg .card.tw','.lg tr.pr','main'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return s+':'+[r.left,r.top,r.width,r.height].map(Math.round).join(',')})""")
        pg.close()
    diff=[(a,c) for a,c in zip(geo["v38"],geo["v39"]) if a!=c]
    chk("desktop layout identical to v38",not diff,diff)
    # light theme phone
    m=b.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True);e=[];m.on("pageerror",lambda x:e.append(str(x)));route(m)
    m.add_init_script("localStorage.setItem('lm_user','xParRaidr');localStorage.setItem('lm_theme','light');localStorage.setItem('lm_base_2020_1','{}');localStorage.setItem('wph_old_2020_1','{}');localStorage.setItem('lm_keepme','1')")
    m.goto(F);m.wait_for_timeout(5500)
    chk("theme-color follows light mode",m.evaluate("document.getElementById('thc').content")=="#f3f4f8")
    chk("stale week caches pruned, settings kept",m.evaluate("[localStorage.getItem('lm_base_2020_1'),localStorage.getItem('wph_old_2020_1'),localStorage.getItem('lm_keepme'),!!localStorage.getItem('lm_conns')]")==[None,None,"1",True])
    m.screenshot(path=OUT+"/m_light_m.png")
    m.evaluate("setTab('t')");m.wait_for_timeout(3500);m.screenshot(path=OUT+"/m_light_t.png")
    # background polling paused
    m.evaluate("setTab('m')");m.wait_for_timeout(1000)
    m.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true})");r0=reqs[0];m.wait_for_timeout(9000);r1=reqs[0]
    chk("no network polling while app is in background",r1-r0<=1,r1-r0)
    m.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))");m.wait_for_timeout(2500)
    chk("refreshes immediately on return",reqs[0]>r1)
    chk("no errors light phone",not e,e[:3])
    m.close()
    # first run on phone: welcome + connect sheet + back
    w=b.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True);e=[];w.on("pageerror",lambda x:e.append(str(x)));route(w)
    w.goto(F);w.wait_for_timeout(2500);w.screenshot(path=OUT+"/m_first.png")
    chk("first run: welcome fits phone",w.evaluate("document.documentElement.scrollWidth")<=390)
    w.locator('.pcard[data-p=sleeper] .pcta').tap();w.wait_for_timeout(500)
    chk("connect step opens full-screen",w.evaluate("document.body.classList.contains('pvsheet')"))
    w.screenshot(path=OUT+"/m_first_sheet.png")
    fs=w.evaluate("[...document.querySelectorAll('#pvform input')].map(i=>getComputedStyle(i).fontSize)")
    chk("connect inputs are 16px (no iOS zoom)",all(x=="16px" for x in fs),fs)
    w.go_back();w.wait_for_timeout(400)
    chk("phone back button closes the connect step",not w.evaluate("document.body.classList.contains('pvsheet')"))
    chk("no errors first run",not e,e[:3])
    w.close()
    # landscape phone
    l=b.new_page(viewport={"width":844,"height":390},is_mobile=True,has_touch=True);route(l);l.add_init_script("localStorage.setItem('lm_user','xParRaidr')");l.goto(F);l.wait_for_timeout(5000)
    chk("landscape: one-row header, no overflow",l.evaluate("[Math.round(document.querySelector('header').getBoundingClientRect().height),document.documentElement.scrollWidth]"),l.evaluate("[Math.round(document.querySelector('header').getBoundingClientRect().height),document.documentElement.scrollWidth]"))
    l.screenshot(path=OUT+"/m_land2.png");l.close()
    b.close()
print("FAILED:",fails)
