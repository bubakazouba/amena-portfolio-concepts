"""Re-scrape amenasahmoud.com (Framer) into the AMENA_RAW shape used by live-prototype.html.

Renders each page in headless Chromium at desktop width and keeps only VISIBLE
h1-h6/p/img in document order, so Framer's hidden breakpoint copies are skipped.
FAQ <details>/accordions are opened first so their answers are captured.

    python tools/scrape_framer.py > raw.json
"""
import json, re, sys
from playwright.sync_api import sync_playwright

PAGES = ["/", "/project/sahl-system-design", "/project/mascot", "/project/photography", "/project/graphicdesign"]

EXTRACT = r"""() => {
  const vis = e => { for (let n = e; n && n !== document.body; n = n.parentElement) {
      const cs = getComputedStyle(n); if (cs.display === 'none' || cs.visibility === 'hidden') return false; } return true; };
  // textContent keeps the authored case (innerText applies CSS uppercase) but glues
  // <br>-separated lines together, so walk the nodes and turn <br> into a space.
  const txt = n => n.nodeType === 3 ? n.data : n.nodeName === 'BR' ? ' ' : [...n.childNodes].map(txt).join('');
  const out = [];
  document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,img').forEach(e => {
    if (!vis(e)) return;
    if (e.tagName === 'IMG') {
      const s = (e.currentSrc || e.src || '').split('?')[0];
      if (s.includes('framerusercontent.com/images/')) out.push({t: 'img', src: s, alt: e.alt || ''});
      return;
    }
    if (e.parentElement.closest('h1,h2,h3,h4,h5,h6,p')) return;
    const x = txt(e).replace(/\s+/g, ' ').trim();
    if (x) out.push({t: e.tagName.toLowerCase(), x});
  });
  return out;
}"""


# visible text of the FAQ section (between the "FAQs" heading and the next h2)
FAQ = r"""() => { const h = [...document.querySelectorAll('h2')].find(e => e.textContent.trim() === 'FAQs');
  const out = []; let on = false;
  for (const e of document.querySelectorAll('h2,p')) {
    if (e === h) { on = true; continue; } if (on && e.tagName === 'H2') break;
    if (on && e.offsetParent !== null && e.getClientRects().length) out.push(e.textContent.replace(/\s+/g, ' ').trim()); }
  return out; }"""


def main():
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")  # system Edge; no bundled browser on this box
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        for path in PAGES:
            pg.goto("https://www.amenasahmoud.com" + path, wait_until="networkidle", timeout=60000)
            # scroll through so lazy/appear-on-scroll sections mount
            h = pg.evaluate("document.body.scrollHeight")
            for y in range(0, h + 900, 600):
                pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(120)
            pg.wait_for_timeout(1000)
            res[path] = pg.evaluate(EXTRACT)  # before the FAQ clicks: default state, first answer open
            if path == "/":
                # FAQ answers only mount while their question is open; open each in turn
                qs = pg.locator("p", has_text=re.compile(r"\?$"))
                for i in range(qs.count()):
                    try:
                        qs.nth(i).click(timeout=3000); pg.wait_for_timeout(700)
                        res.setdefault("faq", []).append(pg.evaluate(FAQ))
                    except Exception as ex:
                        print("faq click failed", i, ex, file=sys.stderr)
        b.close()
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
