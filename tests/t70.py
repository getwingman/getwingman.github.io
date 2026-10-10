import sys;sys.path.insert(0,'.');import mock
from playwright.sync_api import sync_playwright
F=sys.argv[1]
def swipe(pg,sel,dx):
    pg.evaluate("""([sel,dx])=>{const el=document.querySelector(sel);const r=el.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+Math.min(r.height/2,20);
     const mk=(t,X)=>new Touch({identifier:1,target:el,clientX:X,clientY:y});
     el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[mk(0,x)],changedTouches:[mk(0,x)]}));
     el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[mk(0,x+dx)]}))}""",[sel,dx])
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
    pg.route("**/*",lambda r:r.continue_() if r.request.url.startswith(("file:","data:")) else mock.handle(r))
    pg.add_init_script("localStorage.setItem('lm_user','xParRaidr')");pg.goto(F);pg.wait_for_timeout(5000)
    print("tiles strip class chain:",pg.evaluate("(()=>{let e=document.querySelector('.lg .mini');const a=[];while(e&&e!==document.body){a.push(e.className);e=e.parentElement}return a.slice(0,4).join(' < ')})()"))
    swipe(pg,".lg .mini",-150);pg.wait_for_timeout(400);print("swipe on tiles strip ->",pg.evaluate("S.tab+' '+mobId()"))
    pg.evaluate("setTab('m')");swipe(pg,"#lgs",-150);pg.wait_for_timeout(400);print("swipe on league chips ->",pg.evaluate("S.tab+' '+mobId()"))
    pg.evaluate("setTab('t')");pg.wait_for_timeout(3500)
    swipe(pg,"#moves .pwt tbody tr",150);pg.wait_for_timeout(400);print("swipe on Lab table ->",pg.evaluate("S.tab"))
    pg.evaluate("setTab('t')");pg.wait_for_timeout(1500)
    pg.locator("#moves .pwt th .ti, #moves .pwt th [data-tip]").first.tap() if pg.locator("#moves .pwt th [data-tip]").count() else None
    pg.wait_for_timeout(300);print("tap Power ⓘ shows tip:",pg.evaluate("[...document.querySelectorAll('.flt,.tipop')].filter(e=>getComputedStyle(e).display!=='none'&&getComputedStyle(e).opacity>0&&e.innerText.trim()).map(e=>e.className+':'+e.innerText.slice(0,60))"))
    pg.locator("#moves .iqr").first.tap();pg.wait_for_timeout(300);print("tap IQ ring shows tip:",pg.evaluate("[...document.querySelectorAll('.flt,.tipop')].filter(e=>getComputedStyle(e).display!=='none'&&getComputedStyle(e).opacity>0&&e.innerText.trim()).map(e=>e.className+':'+e.innerText.slice(0,60))"))
    pg.locator("#moves .awd").first.tap();pg.wait_for_timeout(300);print("tap award shows tip:",pg.evaluate("[...document.querySelectorAll('.flt,.tipop')].filter(e=>getComputedStyle(e).display!=='none'&&getComputedStyle(e).opacity>0&&e.innerText.trim()).map(e=>e.className+':'+e.innerText.slice(0,60))"))
    pg.evaluate("setTab('m')");pg.wait_for_timeout(800)
    pg.locator("#setb").tap();pg.wait_for_timeout(200);o1=pg.evaluate("$('setp').classList.contains('open')")
    pg.mouse.click(200,pg.evaluate("Math.round($('setp').getBoundingClientRect().bottom)+20"));pg.wait_for_timeout(200);print("settings opens",o1,"closes on outside tap",not pg.evaluate("$('setp').classList.contains('open')"))
    pg.locator("#setb").tap();pg.keyboard.press("Escape");pg.wait_for_timeout(200);print("Esc closes settings",not pg.evaluate("$('setp').classList.contains('open')"));pg.evaluate("$('setp').classList.remove('open')")
    print("settings max-height / bottom:",pg.evaluate("(()=>{const r=$('setp').getBoundingClientRect();return [Math.round(r.top),Math.round(r.bottom),innerHeight]})()"))
    # player cell tap
    pg.locator(".lg td[data-pos] .nm").first.tap();pg.wait_for_timeout(500);print("tap player name ->",pg.evaluate("[...document.querySelectorAll('.flt')].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.innerText.slice(0,80))"))
    pg.mouse.click(5,400)
    pg.locator(".lg tr.pr").nth(1).tap();pg.wait_for_timeout(500);print("tap row expands:",pg.evaluate("document.querySelectorAll('.lg tr.xp,.lg tr.open,.lg .pdet').length"))
    # pulse
    if pg.is_visible("#swb"):
        pg.locator("#swb").tap();pg.wait_for_timeout(300);print("pulse rect",pg.evaluate("(()=>{const r=$('swp').getBoundingClientRect();return [Math.round(r.left),Math.round(r.right),Math.round(r.top),Math.round(r.bottom)]})()"))
    b.close()
