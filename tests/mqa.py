"""Mobile audit: python3 mqa.py <file-url> <pwdir> <outdir> [devices]"""
import sys, json
sys.path.insert(0, sys.argv[2])
import mock
from playwright.sync_api import sync_playwright
F, OUT = sys.argv[1], sys.argv[3]
DEV = {
  "se": dict(viewport={"width": 375, "height": 667}, device_scale_factor=2),
  "i14": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3),
  "max": dict(viewport={"width": 430, "height": 932}, device_scale_factor=3),
  "fold": dict(viewport={"width": 344, "height": 882}, device_scale_factor=3),
  "pixel": dict(viewport={"width": 412, "height": 915}, device_scale_factor=2.6),
  "land": dict(viewport={"width": 844, "height": 390}, device_scale_factor=3),
  "ipad": dict(viewport={"width": 768, "height": 1024}, device_scale_factor=2),
}
only = sys.argv[4].split(",") if len(sys.argv) > 4 else list(DEV)
AUDIT = r"""(root)=>{
 const W=innerWidth,H=innerHeight,res={};const vis=e=>{const s=getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&e.offsetParent!==null||s.position==='fixed'};
 const desc=e=>{let s=e.tagName.toLowerCase();if(e.id)s+='#'+e.id;if(e.className&&typeof e.className==='string')s+='.'+e.className.trim().split(/\s+/).slice(0,2).join('.');const t=(e.innerText||e.getAttribute('aria-label')||e.title||'').trim().replace(/\s+/g,' ').slice(0,24);return s+(t?' «'+t+'»':'')};
 const inScroller=e=>{let p=e.parentElement;while(p&&p!==document.body){const s=getComputedStyle(p);if(/(auto|scroll|hidden)/.test(s.overflowX)&&p.scrollWidth>p.clientWidth+1)return true;p=p.parentElement}return false};
 const R=document.querySelector(root)||document.body;
 res.docW=document.documentElement.scrollWidth;res.bodyW=document.body.scrollWidth;
 // elements poking past the right edge that aren't inside a horizontal scroller
 res.overflow=[...R.querySelectorAll('*')].filter(e=>{if(!vis(e))return false;const r=e.getBoundingClientRect();return (r.right>W+1||r.left<-1)&&r.width<W*3&&!inScroller(e)&&!e.closest('#fxlayer,.tipop,.flt,#toasts')}).slice(0,12).map(e=>desc(e)+' ['+Math.round(e.getBoundingClientRect().left)+'..'+Math.round(e.getBoundingClientRect().right)+']');
 // tap targets
 const I=[...R.querySelectorAll('button,a[href],select,input,textarea,[onclick],[role=tab],[data-sort],.pcta,.chip,summary,.svh,label.sw')].filter(vis);
 res.taps=I.map(e=>{const r=e.getBoundingClientRect();return [desc(e),Math.round(r.width),Math.round(r.height)]}).filter(x=>x[1]<32||x[2]<32);
 res.nTaps=I.length;
 // text size
 const tx=[...R.querySelectorAll('*')].filter(e=>vis(e)&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim().length>1));
 const small={};tx.forEach(e=>{const f=parseFloat(getComputedStyle(e).fontSize);if(f<10){const k=Math.round(f*10)/10;(small[k]=small[k]||[]).push(desc(e))}});
 res.small=Object.fromEntries(Object.entries(small).map(([k,v])=>[k,[v.length,...v.slice(0,4)]]));
 // inputs that make iOS zoom
 res.zoomInputs=[...document.querySelectorAll('input,select,textarea')].filter(vis).filter(e=>parseFloat(getComputedStyle(e).fontSize)<16).map(e=>desc(e)+' '+getComputedStyle(e).fontSize);
 // fixed bottom bar covering last content
 const bar=[...document.querySelectorAll('header .tabs')].find(vis);if(bar){const br=bar.getBoundingClientRect();res.bar=[Math.round(br.top),Math.round(br.height),getComputedStyle(bar).position];
   res.padBottom=getComputedStyle(document.body).paddingBottom+' / main '+getComputedStyle(document.querySelector('main')).paddingBottom;
   document.scrollingElement.scrollTop=1e7;const last=[...R.querySelectorAll('.card,section,table')].filter(vis).map(e=>e.getBoundingClientRect().bottom);res.lastBottom=Math.round(Math.max(0,...last));res.barTop=Math.round(bar.getBoundingClientRect().top);document.scrollingElement.scrollTop=0}
 const hd=document.querySelector('header').getBoundingClientRect();res.header=Math.round(hd.height);res.headerPos=getComputedStyle(document.querySelector('header')).position;
 res.pageH=document.documentElement.scrollHeight;
 return res}"""

def route(pg):
    pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("file:", "data:", "blob:")) else mock.handle(r))

SEED = """localStorage.setItem('lm_user','xParRaidr');localStorage.setItem('lm_tab','m');
localStorage.setItem('lm_conns',JSON.stringify([{key:'sleeper:xparraidr',p:'sleeper',username:'xParRaidr'},{key:'survivor:SURVtestsheet0000000000001',p:'survivor',sheet:'SURVtestsheet0000000000001',cfg:{me:'Our Group',reuse:'gap1',price:25,split:4}},{key:'pickem:PICKtestsheet0000000000001',p:'pickem',sheet:'PICKtestsheet0000000000001',cfg:{me:'xParRaidr',dues:50,first:200,second:100,weekly:50}}]));"""
report = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name in only:
        ctx = b.new_context(**DEV[name], is_mobile=name != "ipad" or True, has_touch=True)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text[:160]))
        route(pg); pg.add_init_script(SEED)
        pg.goto(F); pg.wait_for_timeout(5500)
        R = report[name] = {}
        def shot(tag, root):
            R[tag] = pg.evaluate(AUDIT, root)
            pg.screenshot(path=f"{OUT}/m_{name}_{tag}.png")
        shot("matchups", "main")
        for t, root in [("f", "#field"), ("t", "#moves"), ("s", "#surv"), ("p", "#pick")]:
            pg.evaluate(f"setTab('{t}')"); pg.wait_for_timeout(3500 if t == "t" else 1500)
            shot("tab_" + t, root)
        pg.evaluate("setTab('m')"); pg.wait_for_timeout(800)
        pg.click("#setb"); pg.wait_for_timeout(400); shot("settings", "#setp"); pg.click("#setb"); pg.wait_for_timeout(200)
        if pg.is_visible("#swb"):
            pg.click("#swb"); pg.wait_for_timeout(400); shot("pulse", "#swp"); pg.click("#swb")
        pg.click("#who"); pg.wait_for_timeout(500); shot("connect", "#welcome")
        pg.click(".pcard[data-p=espn] .pcta"); pg.wait_for_timeout(500); shot("connect_espn", "#welcome")
        R["errors"] = errs
        ctx.close()
    b.close()
json.dump(report, open(OUT + "/mqa.json", "w"), indent=1)
for d, R in report.items():
    print("=====", d)
    for tag, a in R.items():
        if tag == "errors":
            print("  errors:", a[:5]); continue
        print(f"  [{tag}] docW={a['docW']} header={a['header']}({a['headerPos']}) bar={a.get('bar')} lastBottom={a.get('lastBottom')} barTop={a.get('barTop')} taps<32={len(a['taps'])}/{a['nTaps']} zoom={a['zoomInputs']}")
        if a["overflow"]: print("     OVERFLOW:", a["overflow"][:6])
        if a["taps"]: print("     small taps:", a["taps"][:10])
        if a["small"]: print("     tiny text:", a["small"])
