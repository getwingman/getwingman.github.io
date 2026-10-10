import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.launch();w=b.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True);e=[];w.on("pageerror",lambda x:e.append(str(x)))
    w.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    w.goto(F);w.wait_for_timeout(2500)
    print("first run: tabs hidden",w.evaluate("getComputedStyle(document.querySelector('.tabs')).display")=="none","week hidden",w.evaluate("getComputedStyle($('week')).display")=="none")
    w.screenshot(path=sys.argv[2]+"/m_first2.png")
    w.locator('.pcard[data-p=sleeper] .pcta').tap();w.wait_for_timeout(300)
    w.fill("#pvform input","xParRaidr");w.locator("#pvadd").tap();w.wait_for_timeout(800);print("conns",w.evaluate("getConns().length"),"go visible",w.is_visible("#go"));w.wait_for_timeout(6000)
    print("after connecting: tabs shown",w.evaluate("getComputedStyle(document.querySelector('.tabs')).display")!="none","week shown",w.evaluate("getComputedStyle($('week')).display")!="none","leagues",w.evaluate("S.L.length"),"pvsheet",w.evaluate("document.body.classList.contains('pvsheet')"))
    w.screenshot(path=sys.argv[2]+"/m_after_connect.png")
    print("errors",e[:3]);b.close()
