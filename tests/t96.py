"""v46: nicknames live on the device (link import / Settings), never in the page"""
import sys,json,base64;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
PK2="PK2testsheet00000000000001"
names={"xparraidr":"Captain"}
link=F+"#wm_names="+base64.urlsafe_b64encode(json.dumps(names).encode()).decode().rstrip("=")
src=open(F.replace("file://","")).read()
chk("no nickname map shipped in the page",'xparraidr:"' not in src.lower() and "const PEOPLE" not in src)
with sync_playwright() as p:
    b=p.chromium.launch();mock.PREGAME[0]=True
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
    chk("setup link carries the nicknames",pg.evaluate("(()=>{const u=setupLink(),m=u.match(/wm_setup=([^&]+)/);return JSON.parse(unb64u(m[1])).n.xparraidr})()")=="Skipper")
    chk("no errors",not e,e[:2]);b.close()
print("FAILED:",fails)
