"""Merge a fresh scrape (tools/scrape_framer.py output) into AMENA_RAW in live-prototype.html.

Case-study and gallery pages are replaced wholesale with the visible-content scrape, minus
the site header (everything before the page's first heading) and the footer (cat polaroids,
name, social links). The home page keeps its existing structure, because the desktop scrape
hides the featured cards' date lines (hover-only) that buildHome reads; only its changed copy
is patched, and the FAQ answers (captured by opening each question) are filled in.

    python tools/merge_raw.py scrape.json
"""
import json, re, sys

FILE = "live-prototype.html"
FOOTER_FIRST = "https://framerusercontent.com/images/ztE5fiQjxJisvK2TIJUvx1NaIGI.jpg"


def strip_chrome(items):
    start = next(i for i, x in enumerate(items) if x["t"] != "img" and x["t"] != "p")  # first heading
    end = next((i for i in range(start, len(items)) if items[i].get("src") == FOOTER_FIRST), len(items))
    return [x for x in items[start:end] if x.get("x") != "#"]


def main(scrape):
    new = json.load(open(scrape, encoding="utf-8"))
    s = open(FILE, encoding="utf-8").read()
    m = re.search(r"var AMENA_RAW = (\{.*?\});\n", s, re.S)
    raw = json.loads(m.group(1))

    for k in raw:
        if k != "/":
            raw[k] = strip_chrome(new[k])

    home = raw["/"]
    fresh = strip_chrome(new["/"])
    # hero tail line + the "outside" line under the polaroids, taken from the fresh scrape by position
    h1s = [x["x"] for x in fresh if x["t"] == "h1"]
    home[1]["x"] = h1s[1]
    outside = next(x["x"] for x in fresh if x["t"] == "p" and x["x"].startswith("When I"))
    next(x for x in home if x["t"] == "p" and x["x"].startswith(("I'm probably", "When I")))["x"] = outside
    # featured card date lines: Sahl now reads its own dates (mascot's were shown on both)
    dates = [i for i, x in enumerate(home) if x["t"] == "p" and re.search(r"\d{4}", x["x"])
             and i < next(j for j, y in enumerate(home) if y.get("x") == "What I Do")]
    home[dates[0]]["x"] = "2024 – 2025"

    # FAQ answers: each snapshot is the FAQ text with one question open (the page's own
    # default state, where the first one starts open, counts as a snapshot too)
    # Only the FAQ section of the fresh list counts: past its last question the next item is the
    # contact heading, which once got recorded as the relocation answer (11/02). First capture wins.
    fx = [x.get("x", "") for x in fresh]
    f0 = fx.index("FAQs") + 1
    f1 = next((i for i in range(f0, len(fresh)) if fresh[i]["t"] == "h2"), len(fresh))
    qa = {}
    for snap in new.get("faq", []) + [fx[f0:f1]]:
        for i, t in enumerate(snap):
            if not t.endswith("?") and i and snap[i - 1].endswith("?"):
                qa.setdefault(snap[i - 1], t)
    iq = next(i for i, x in enumerate(home) if x.get("x") == "FAQs")
    ic = next(i for i in range(iq + 1, len(home)) if home[i]["t"] == "h2")
    faq = [x for x in home[iq + 1:ic] if x["x"].endswith("?")]
    missing = [q["x"] for q in faq if q["x"] not in qa]
    if missing:
        sys.exit(f"no answer captured for: {missing}")
    block = []
    for q in faq:
        block += [q, {"t": "p", "x": qa[q["x"]]}]
    home[iq + 1:ic] = block

    out = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
    s = s[:m.start(1)] + out + s[m.end(1):]
    open(FILE, "w", encoding="utf-8").write(s)
    print({k: len(v) for k, v in raw.items()}, len(qa), "faq answers")


if __name__ == "__main__":
    main(sys.argv[1])
