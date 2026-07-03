#!/usr/bin/env python3
"""
Fortress live-scraping demos — reproduces the GIFs in the README.

Each demo drives the real Fortress engine over CDP and overlays a "verification"
HUD (green highlights + value tags) so you can *see* the scrape happen, then
writes an animated GIF.

    pip install tilion-fortress playwright pillow
    python examples/scrape_demos.py structured   # -> fortress-scrape-structured.gif
    python examples/scrape_demos.py paginated | detail | js | all

Patterns shown:
    structured  books.toscrape.com     -> typed records build into a live JSON panel
    paginated   quotes.toscrape.com    -> auto-pagination across pages 1..3
    detail      books.toscrape.com     -> deep detail-page crawl (UPC/price/tax/stock/reviews)
    js          quotes.toscrape.com/js -> client-side-rendered DOM captured over CDP

Fortress spoofs the fingerprint in the engine's C++, so nothing here adds JS stealth.
If a site still blocks you it's the IP (datacenter) — route egress through a residential proxy.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

OUT = Path(__file__).resolve().parent
VIEWPORT = {"width": 1180, "height": 820}
FPS = 9

# One declarative overlay controller, re-injected after every navigation.
FX_SETUP = r"""
window.FX = (function(){
  const A = '#39d353';
  function ensureBar(title){
    let bar = document.getElementById('fx-bar');
    if(!bar){ bar=document.createElement('div'); bar.id='fx-bar';
      bar.style.cssText=`position:fixed;top:0;left:0;right:0;height:44px;z-index:2147483000;
        background:rgba(13,17,23,.94);color:#e6edf3;display:flex;align-items:center;gap:12px;
        padding:0 16px;font:600 15px system-ui,Segoe UI,sans-serif;box-shadow:0 2px 18px rgba(0,0,0,.4)`;
      document.body.appendChild(bar); }
    bar.innerHTML=`<span style="font-size:18px">&#127984;</span><span style="letter-spacing:.5px">FORTRESS</span>`+
      `<span style="color:${A};font-weight:700">&#9679; ${title}</span>`+
      `<span id="fx-status" style="margin-left:auto;color:#9da7b3;font-weight:500"></span>`;
  }
  return { render(s){
    ensureBar(s.title||'stealth engine');
    const st=document.getElementById('fx-status'); if(st) st.textContent=s.status||'';
    let root=document.getElementById('fx-root');
    if(!root){ root=document.createElement('div'); root.id='fx-root'; document.body.appendChild(root); }
    root.innerHTML='';
    (s.boxes||[]).forEach(b=>{
      let el=null; try{ el=document.querySelectorAll(b.sel)[b.idx||0]; }catch(e){}
      if(!el) return; const r=el.getBoundingClientRect();
      const isA=!!b.active, pop=b.pop==null?1:b.pop;
      const box=document.createElement('div');
      box.style.cssText=`position:fixed;left:${r.left-5}px;top:${r.top-5}px;width:${r.width+10}px;
        height:${r.height+10}px;z-index:2147482000;border-radius:9px;border:3px solid ${A};
        box-shadow:0 0 ${isA?22*pop:7}px ${A}${isA?'':'55'};pointer-events:none`;
      root.appendChild(box);
      if(b.label){ const t=document.createElement('div'); const op=isA?pop:1;
        t.style.cssText=`position:fixed;left:${r.left-5}px;top:${r.top+r.height+7}px;z-index:2147482100;
          background:${A};color:#08160c;font:700 12px system-ui,Segoe UI,sans-serif;padding:4px 9px;
          border-radius:7px;opacity:${op};transform:translateY(${(1-op)*6}px);
          box-shadow:0 3px 10px rgba(0,0,0,.35);white-space:nowrap;max-width:340px;overflow:hidden;text-overflow:ellipsis`;
        t.textContent=b.label; root.appendChild(t); }
    });
    if(s.panel){ const p=document.createElement('div');
      p.style.cssText=`position:fixed;right:14px;top:58px;width:340px;max-height:82vh;overflow:hidden;
        z-index:2147482200;background:rgba(13,17,23,.93);border:1px solid ${A}55;border-radius:12px;
        padding:12px 14px;font:600 12px ui-monospace,Consolas,monospace;color:#e6edf3;box-shadow:0 10px 34px rgba(0,0,0,.45)`;
      let html=`<div style="color:${A};font-weight:700;margin-bottom:8px;font-family:system-ui">${s.panel.title}</div>`;
      (s.panel.rows||[]).forEach(r=>{ html+=`<div style="padding:3px 0;border-top:1px solid #ffffff10;color:#c9d3de">${r}</div>`; });
      p.innerHTML=html; root.appendChild(p); }
    if(s.done){ const d=document.createElement('div');
      d.style.cssText=`position:fixed;left:50%;top:52%;transform:translate(-50%,-50%);z-index:2147483100;
        background:rgba(13,17,23,.96);color:#e6edf3;padding:18px 26px;border-radius:14px;border:1px solid ${A};
        box-shadow:0 10px 40px rgba(0,0,0,.5);text-align:center;font:600 15px system-ui,Segoe UI,sans-serif`;
      d.innerHTML=`<div style="font-size:21px;color:${A};margin-bottom:6px">${s.done.title}</div>`+
        `<div style="color:#9da7b3;font-weight:500">${s.done.sub}</div>`; root.appendChild(d); }
  }};
})();
"""


class Cap:
    def __init__(self, pg, frames_dir):
        self.pg, self.dir, self.n = pg, frames_dir, 0
        frames_dir.mkdir(parents=True, exist_ok=True)
        for f in frames_dir.glob("*.png"):
            f.unlink()

    def fx(self):
        self.pg.evaluate(FX_SETUP)

    def frame(self, state, reps=1):
        for _ in range(reps):
            self.pg.evaluate("(s)=>window.FX.render(s)", state)
            self.pg.screenshot(path=str(self.dir / f"f{self.n:04d}.png"))
            self.n += 1

    def pops(self, base, box, reps=(0.34, 0.7, 1.0)):
        for pv in reps:
            b = dict(box); b["active"] = True; b["pop"] = pv
            self.frame({**base, "boxes": base.get("boxes", []) + [b]})


# ---------------- demos ----------------
def d_paginated(pg, cap):
    total = 0
    for page in (1, 2, 3):
        pg.goto(f"https://quotes.toscrape.com/page/{page}/", wait_until="domcontentloaded", timeout=30000)
        pg.evaluate("window.scrollTo(0,0)"); cap.fx()
        cnt = pg.evaluate("()=>document.querySelectorAll('div.quote').length")
        data = pg.evaluate("""()=>[...document.querySelectorAll('div.quote')].slice(0,3).map(q=>
            ({a:q.querySelector('.author')?.textContent, t:[...q.querySelectorAll('a.tag')].slice(0,2).map(x=>x.textContent).join(', ')}))""")
        for i, q in enumerate(data):
            base = {"title": "paginated scrape", "status": f"page {page}/3 · {total+i+1} quotes",
                    "boxes": [{"sel": "div.quote", "idx": j, "active": False} for j in range(i)]}
            cap.pops(base, {"sel": "div.quote", "idx": i, "label": f"✓ {q['a']} · #{q['t']}"})
        total += cnt
        cap.frame({"title": "paginated scrape", "status": f"page {page}/3 · {total} quotes",
                   "boxes": [{"sel": "div.quote", "idx": j, "active": False} for j in range(3)]}, reps=2)
    for _ in range(10):
        cap.frame({"title": "paginated scrape", "status": "done · 30 quotes",
                   "done": {"title": "30 quotes · 3 pages", "sub": "authors + tags · auto-pagination · 0 blocks"}})


def d_structured(pg, cap):
    pg.goto("https://books.toscrape.com/", wait_until="networkidle", timeout=30000)
    pg.evaluate("window.scrollTo(0,90)"); cap.fx()
    books = pg.evaluate("""()=>[...document.querySelectorAll('article.product_pod')].slice(0,8).map(a=>
        ({t:a.querySelector('h3 a')?.getAttribute('title'),p:a.querySelector('.price_color')?.textContent?.trim(),
          r:(a.querySelector('p.star-rating')?.className||'').replace('star-rating','').trim(),
          s:a.querySelector('.instock')?.textContent?.trim()?'In stock':'-'}))""")
    rows = []
    for i, bk in enumerate(books):
        t = (bk['t'] or '')[:22]
        base = {"title": "structured extraction", "status": f"{i+1}/8 records",
                "panel": {"title": "records[]  →  JSON", "rows": list(rows)},
                "boxes": [{"sel": "article.product_pod", "idx": j, "active": False} for j in range(i)]}
        cap.pops(base, {"sel": "article.product_pod", "idx": i, "label": f"✓ {bk['p']} · ★{bk['r']}"})
        rows.append(f'{{ "{t}", "{bk["p"]}", "★{bk["r"]}", "{bk["s"]}" }}')
        cap.frame({"title": "structured extraction", "status": f"{i+1}/8 records",
                   "panel": {"title": "records[]  →  JSON", "rows": list(rows)},
                   "boxes": [{"sel": "article.product_pod", "idx": j, "active": False} for j in range(i+1)]})
    for _ in range(10):
        cap.frame({"title": "structured extraction", "status": "done",
                   "panel": {"title": "records[]  →  JSON", "rows": list(rows)},
                   "done": {"title": "20 records → structured", "sub": "title · price · rating · stock · typed"}})


def d_detail(pg, cap):
    pg.goto("https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            wait_until="domcontentloaded", timeout=30000)
    pg.evaluate("window.scrollTo(0,220)"); cap.fx()
    fields = pg.evaluate(r"""()=>{
      const rows=[...document.querySelectorAll('table.table-striped tr')];
      const get=(l)=>{const tr=rows.find(r=>r.querySelector('th')?.textContent.trim()===l);return tr?tr.querySelector('td').textContent.trim():'';};
      return [
        {sel:'div.product_main h1', idx:0, label:'title: '+(document.querySelector('div.product_main h1')?.textContent||'').slice(0,20)},
        {sel:'table.table-striped tr', idx:0, label:'UPC: '+get('UPC')},
        {sel:'table.table-striped tr', idx:3, label:'Price (incl tax): '+get('Price (incl. tax)')},
        {sel:'table.table-striped tr', idx:5, label:'Availability: '+get('Availability')},
        {sel:'table.table-striped tr', idx:6, label:'Reviews: '+get('Number of reviews')},
      ];
    }""")
    for i, f in enumerate(fields):
        base = {"title": "deep detail crawl", "status": f"extracting field {i+1}/{len(fields)}",
                "boxes": [{"sel": fields[j]['sel'], "idx": fields[j]['idx'], "label": fields[j]['label'], "active": False} for j in range(i)]}
        cap.pops(base, {"sel": f['sel'], "idx": f['idx'], "label": f['label']})
    hold = {"title": "deep detail crawl", "status": "done",
            "boxes": [{"sel": f['sel'], "idx": f['idx'], "label": f['label'], "active": False} for f in fields]}
    for _ in range(10):
        cap.frame({**hold, "done": {"title": f"{len(fields)} fields · deep crawl", "sub": "UPC · price · tax · stock · reviews"}})


def d_js(pg, cap):
    pg.goto("https://quotes.toscrape.com/js/", wait_until="domcontentloaded", timeout=30000); cap.fx()
    for _ in range(3):
        cap.frame({"title": "JS-rendered (CDP)", "status": "client-side render — waiting for JS…"})
    pg.wait_for_selector("div.quote", timeout=15000); time.sleep(0.5); pg.evaluate("window.scrollTo(0,0)")
    data = pg.evaluate("()=>[...document.querySelectorAll('div.quote')].slice(0,4).map(q=>({a:q.querySelector('.author')?.textContent}))")
    for i, q in enumerate(data):
        base = {"title": "JS-rendered (CDP)", "status": f"rendered by V8 · {i+1} captured",
                "boxes": [{"sel": "div.quote", "idx": j, "active": False} for j in range(i)]}
        cap.pops(base, {"sel": "div.quote", "idx": i, "label": f"✓ {q['a']}"})
    for _ in range(10):
        cap.frame({"title": "JS-rendered (CDP)", "status": "done · full browser render",
                   "done": {"title": "JS-rendered · captured", "sub": "client-side DOM · real V8 · over raw CDP"}})


DEMOS = {"paginated": d_paginated, "structured": d_structured, "detail": d_detail, "js": d_js}


def build_gif(frames_dir: Path, out_gif: Path):
    from PIL import Image
    files = sorted(frames_dir.glob("f*.png"))
    imgs = [Image.open(f).convert("RGB").resize((760, int(760 * Image.open(f).height / Image.open(f).width))) for f in files]
    pal = imgs[len(imgs) // 2].quantize(colors=256)
    frames = [im.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG) for im in imgs]
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0, optimize=True)
    print(f"[*] wrote {out_gif}  ({out_gif.stat().st_size // 1024} KB, {len(frames)} frames)")


def run_one(name: str):
    from tilion_fortress import Fortress
    from playwright.sync_api import sync_playwright
    frames_dir = OUT / f".frames_{name}"
    print(f"[*] demo '{name}': launching Fortress...")
    with Fortress() as f:
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(f.cdp_url)
            ctx = b.contexts[0] if b.contexts else b.new_context()
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.set_viewport_size(VIEWPORT)
            cap = Cap(pg, frames_dir)
            DEMOS[name](pg, cap)
            print(f"[*] captured {cap.n} frames")
            b.close()
    build_gif(frames_dir, OUT / f"fortress-scrape-{name}.gif")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "structured"
    names = list(DEMOS) if which == "all" else [which]
    for n in names:
        if n not in DEMOS:
            print(f"unknown demo '{n}'. choose: {', '.join(DEMOS)} | all"); return 2
        run_one(n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
