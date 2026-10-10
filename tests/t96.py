"""v47: built-in league nicknames (PEOPLE) apply by default; device entries (link import / Settings) override them"""
import sys,json,base64;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
PK2="PK2testsheet00000000000001"
names={"xparraidr":"Captain"}
link=F+"#wm_names="+base64.urlsafe_b64encode(json.dumps(names).encode()).decode().rstrip("=")
with sync_playwright() as p:
    b=p.chromium.launch();mock.PREGAME[0]=True
    c0=b.new_context(viewport={"width":1500,"height":1000});p0=c0.new_page();e0=[];p0.on("pageerror",lambda x:e0.append(str(x)))
    p0.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    p0.add_init_script("localStorage.setItem('lm_user','xParRaidr');localStorage.setItem('lm_conns',%r)"%json.dumps([{"key":"sleeper:x","p":"sleeper","username":"xParRaidr"}]))
    p0.goto(F);p0.wait_for_timeout(5500)
    bi=p0.evaluate("typeof PEOPLE==='object'?PEOPLE.xparraidr:''")
    chk("built-in nickname map ships with the page",bool(bi) and p0.evaluate("Object.keys(PEOPLE).length")>=30)
    chk("built-in names apply with no setup",p0.evaluate("!localStorage.getItem('lm_nicks')") and p0.evaluate("t=>document.querySelector('#view').innerText.includes(t)",bi),bi)
    chk("lookup is case-insensitive",p0.evaluate("nickOf('xParRaidr')===PEOPLE.xparraidr&&nickOf('nobody_here')===''"))
    chk("no errors (built-in)",not e0,e0[:2]);c0.close()
    pg=b.new_page(viewport={"width":1500,"height":1000});e=[];pg.on("pageerror",lambda x:e.append(str(x)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr');if(!localStorage.getItem('lm_conns'))localStorage.setItem('lm_conns',%r)"%json.dumps([{"key":"sleeper:x","p":"sleeper","username":"xParRaidr"},{"key":"pickem:"+PK2,"p":"pickem","sheet":PK2}]))
    pg.goto(link);pg.wait_for_timeout(5500)
    chk("link import stores the names on this device and strips the hash",pg.evaluate("JSON.parse(localStorage.getItem('lm_nicks')).xparraidr")=="Captain" and "wm_names" not in pg.evaluate("location.href"))
    chk("matchups show the nickname",pg.evaluate("document.querySelector('#view').innerText.includes('Captain')"))
    pg.evaluate("setTab('t')");pg.wait_for_timeout(8000)
    chk("Lab board shows the nickname",pg.evaluate("[...document.querySelectorAll('#moves .pwt .bnm')].some(x=>x.textContent==='Captain')"))
    pg.evaluate("setTab('p')");pg.wait_for_timeout(3000)
    chk("Pick'em standings show the nickname (username kept small)",pg.evaluate("[...document.querySelectorAll('#pick .pkn')].some(x=>x.textContent.includes('Captain')&&x.textContent.includes('xParRaidr'))"))
    pg.click('#setb');pg.wait_for_timeout(400);chk('Settings list is prefilled',pg.evaluate("document.getElementById('nicks').value").startswith('xparraidr = Captain'));pg.evaluate("document.getElementById('nicks').value='xparraidr = Skipper';document.getElementById('nicksave').click()");pg.wait_for_timeout(500)
    chk("Settings edit replaces the names",pg.evaluate("JSON.parse(localStorage.getItem('lm_nicks')).xparraidr")=="Skipper")
    chk("device entry overrides the built-in name",pg.evaluate("nickOf('xparraidr')")=="Skipper")
    pg.evaluate("document.getElementById('nicks').value='xparraidr =';document.getElementById('nicksave').click()");pg.wait_for_timeout(400)
    chk("a blank device entry hides the built-in name",pg.evaluate("nickOf('xparraidr')")=="" and pg.evaluate("'xparraidr' in JSON.parse(localStorage.getItem('lm_nicks'))"))
    pg.evaluate("document.getElementById('nicks').value='xparraidr = Skipper';document.getElementById('nicksave').click()");pg.wait_for_timeout(400)
    chk("setup link carries the nicknames",pg.evaluate("(()=>{const u=setupLink(),m=u.match(/wm_setup=([^&]+)/);return JSON.parse(unb64u(m[1])).n.xparraidr})()")=="Skipper")
    chk("no errors",not e,e[:2]);b.close()
print("FAILED:",fails)
