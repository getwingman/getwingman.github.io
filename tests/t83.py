import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F,OUT=sys.argv[1],sys.argv[2];fails=[]
def chk(n,c,info=""):print(("PASS " if c else "FAIL ")+n+(" — "+str(info) if info!="" else ""));(not c) and fails.append(n)
def page(b,pre=False):
    mock.PREGAME[0]=pre;pg=b.new_page(viewport={"width":1500,"height":900});e=[];pg.on("pageerror",lambda x:e.append(str(x)))
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000);return pg,e
with sync_playwright() as p:
    b=p.chromium.launch()
    # adaptive cadence
    for pre,lab in [(False,"live"),(True,"pregame (kickoff 2 days out)")]:
        pg,e=page(b,pre);mock.REQ.clear();pg.wait_for_timeout(20000)
        n=sum(1 for u in mock.REQ if "scoreboard" in u and "week=" not in u or ("scoreboard" in u and "dates" in u));n2=sum(1 for u in mock.REQ if "scoreboard" in u)
        print(f"     {lab}: {n2} scoreboard + {sum(1 for u in mock.REQ if '/matchups/' in u)} matchup requests in 20s")
        if pre:chk("pregame: far fewer requests than live",n2<=2,n2)
        else:live_n=n2;chk("live: refreshes at the chosen cadence",n2>=5,n2)
        pg.close()
    mock.PREGAME[0]=False
    # backoff + friendly errors
    pg,e=page(b);mock.FAIL["sleeper"]=50;pg.wait_for_timeout(16000)
    st=pg.evaluate("S.L.map(l=>[l.failN||0,l.syncErr||'',l.retryAt>Date.now()])")
    chk("failing provider: backs off and explains in plain words",all(x[0]>=1 and "Retrying" in x[1] and "http" not in x[1].lower() for x in st[:1]),st)
    gaps=[u for u in mock.REQ if "/matchups/" in u];print("     matchup attempts while failing:",len(gaps))
    pg.click("#who");pg.click('.pcard[data-p=sleeper] .pcta');pg.wait_for_timeout(300)
    row=pg.evaluate("document.querySelector('#pvform .crow').innerText.replace(/\\s+/g,' ')")
    chk("connection shows Retrying + Retry button, no raw HTTP",("Retrying" in row) and pg.is_visible("#pvform .cretry") and "503" not in row and "http" not in row,row)
    mock.FAIL["sleeper"]=0;pg.click("#pvform .cretry");pg.wait_for_timeout(5000)
    row=pg.evaluate("document.querySelector('#pvform .crow').innerText.replace(/\\s+/g,' ')")
    chk("after retry: Connected · updated …",row.find("Connected")>=0,row)
    pg.screenshot(path=OUT+"/conn40.png");chk("no page errors",not e,e[:2]);pg.close()
    # status bar never shows a raw URL
    pg,e=page(b);r=pg.evaluate("(()=>{status('503 https://api.sleeper.app/v1/league/L1/matchups/5',true);return document.getElementById('status').textContent})()")
    chk("status bar translates raw HTTP errors",not r.startswith("503") and "http" not in r,r);pg.close()
    # calibration note in Lab
    pg,e=page(b);pg.click('header .tb[data-t="t"]');pg.wait_for_timeout(7000)
    cal=pg.evaluate("(document.querySelector('#moves .calb')||{}).innerText||''")
    chk("Lab: win-probability calibration check shown (≥12 past matchups)","Win-% check" in cal,cal);pg.close()
    b.close()
print("FAILED:",fails)
