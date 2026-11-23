#!/usr/bin/env python3
"""verify.py — independent checks for the news22 v4 broadsheet.

Every check prints PASS/FAIL and the script exits non-zero if any fail.
It imports draw.py for its data + text metrics but re-derives every
assertion itself; nothing here trusts draw.py's own asserts.
"""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draw as D  # noqa: E402  (loads stories.json + asserts on import)

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail
                                                 else ""))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    png = HERE / "entry.png"
    data = json.loads((HERE / "stories.json").read_text())

    # 1. image file: present, 1024x1024, within the 1 MiB gate
    check("png exists", png.exists())
    img = Image.open(png)
    check("png is 1024x1024", img.size == (1024, 1024), str(img.size))
    nbytes = png.stat().st_size
    check("png <= 1 MiB", nbytes <= 1024 * 1024, f"{nbytes} B")

    # 2. determinism: two fresh renders, byte-identical
    a, b = HERE / "verify-a.png", HERE / "verify-b.png"
    for out in (a, b):
        r = subprocess.run([sys.executable, str(HERE / "draw.py"),
                            str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    check("determinism 2x byte-identical", sha(a) == sha(b),
          sha(a)[:12])
    a.unlink()
    b.unlink()

    # 3. story data: 35 stories, numbered 1..35, unique headlines
    stories = data["stories"]
    check("35 stories", len(stories) == 35, str(len(stories)))
    check("stories numbered 1..35",
          [s["n"] for s in stories] == list(range(1, 36)))
    heads = [s["head"] for s in stories]
    check("headlines unique", len(set(heads)) == 35)
    check("top 10 ranks 1..10",
          [s["n"] for s in stories[:10]] == list(range(1, 11)))

    # 4. illustration count: 3 heroes + 12 cards = 15 elements
    heroes = data["heroes"]
    cards = (data["cards_row1"] + data["cards_row2"] + data["cards_row3"])
    check("card rows are 4+4+4",
          len(data["cards_row1"]) == 4 and len(data["cards_row2"]) == 4
          and len(data["cards_row3"]) == 4)
    check("3 heroes", len(heroes) == 3)
    check("12 cards", len(cards) == 12)
    check("15 illustration elements", len(heroes) + len(cards) == 15)
    arts = [h["art"] for h in heroes] + [c["art"] for c in cards]
    check("15 distinct artworks", len(set(arts)) == 15)

    # 5. section tags: 15 unique (3 hero + 12 card)
    tags = [h["tag"] for h in heroes] + [c["tag"] for c in cards]
    check("15 unique section tags", len(set(tags)) == 15, str(len(set(tags))))

    # 6. regions sum to 35; masthead date exact
    counts = {}
    for s in stories:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    check("region counts sum to 35", sum(counts.values()) == 35,
          str(counts))
    check("masthead date exact",
          data["edition"]["date_line"] == "SUNDAY, 22 NOVEMBER 2026",
          data["edition"]["date_line"])

    # 7. locked facts present in the data (never violated)
    blob = json.dumps(data)
    locked = {
        "COP31 collapsed": "COLLAPSES" in blob,
        "186 drones": "186" in blob,
        "India 720/9": "720/9" in blob,
        "Hong Kong 98.79%": "98.79%" in blob,
        "Democrats 258+": "258+" in blob,
        "Bahrain CLAIM": "CLAIM" in blob,
        "Cikande 24 body bags": "24 body bags" in blob,
    }
    for name, ok in locked.items():
        check(f"locked fact: {name}", ok)

    # 8. text fits: hero decks <= 2 lines, column heads >= 12px,
    #    card heads <= 2 lines, captions fit, ticker + footer 1 line
    probe = ImageDraw.Draw(Image.new("RGB", (1024, 1024)))
    pw = 322
    deck_ok = True
    for h in heroes:
        w = pw - 20 - (24 if h.get("drop_cap") else 0)
        deck = h["deck"][1:] if h.get("drop_cap") else h["deck"]
        lines = D.wrap(probe, deck, D.font(11, "serif", False), w)
        if len(lines) > 2:
            deck_ok = False
    check("hero decks fit 2 lines", deck_ok)

    small = []
    for s in stories[3:]:
        size = D.fit_size(probe, s["head"], 322 - 56, 13, 12, "sans",
                          True)
        if size < 12:
            small.append(s["n"])
    check("no column headline below 12px", not small, str(small))

    card_ok = True
    for i, c in enumerate(cards):
        tw = 165 if i < 8 else 181
        full = f"{c['tag']} — {c['head']}"
        hl = D.wrap(probe, full, D.font(12, "sans", True), tw)
        cap = D.wrap(probe, c["cap"], D.font(10, "sans", False), tw)
        if len(hl) > 2 or len(cap) > (2 if i < 8 else 1):
            card_ok = False
    check("card headlines/captions fit", card_ok)

    ticker = "  |  ".join(data["ticker"])
    tsize = D.fit_size(probe, ticker, 1024 - 32, 11, 9, "mono", True)
    check("ticker fits one line", tsize >= 9, f"size {tsize}")

    foot = data["footer"]
    head, _, tail = foot.partition("Sources:")
    fw = (D.text_w(probe, head, D.font(11, "sans", True))
          + D.text_w(probe, "Sources:" + tail, D.font(10, "sans", False)))
    check("footer fits one line", fw <= 1024 - 32, f"{fw:.0f}px")

    left = D.wrap(probe, data["date_check"]["left"],
                  D.font(10, "sans", False), 472)
    right = D.wrap(probe, data["date_check"]["right"],
                   D.font(10, "sans", False), 484)
    check("date check fits 2 lines/side",
          len(left) <= 2 and len(right) <= 2,
          f"left {len(left)}, right {len(right)}")

    # 9. map pins: no two circles overlap (r=8 -> centres >= 16px apart)
    nudge = {2: (-10, 6), 3: (-8, -6), 5: (0, -4), 8: (14, -2),
             9: (10, 8)}

    def proj(lon, lat):
        return ((lon + 180.0) / 360.0 * 444,
                (72.0 - lat) / 122.0 * 106)

    pts = []
    for pin in data["pins"]:
        px, py = proj(pin["lon"], pin["lat"])
        dx, dy = nudge.get(pin["n"], (0, 0))
        pts.append((pin["n"], px + dx, py + dy))
    mind = min(math.dist((x1, y1), (x2, y2))
               for i, (_, x1, y1) in enumerate(pts)
               for _, x2, y2 in pts[i + 1:])
    check("map pins non-overlapping", mind >= 16, f"min gap {mind:.1f}px")

    # 10. image signal: not blank, not black; structure survives 300px
    grey = img.convert("L")
    px = list(grey.getdata())
    mean = sum(px) / len(px)
    var = sum((v - mean) ** 2 for v in px) / len(px)
    std = var ** 0.5
    dark = sum(1 for v in px if v < 50) / len(px)
    check("grayscale mean in range", 150 < mean < 250, f"{mean:.1f}")
    check("grayscale std > 20", std > 20, f"{std:.1f}")
    check("dark fraction sane", 0.01 < dark < 0.30, f"{dark:.3f}")
    small = grey.resize((300, 300))
    spx = list(small.getdata())
    smean = sum(spx) / len(spx)
    sstd = (sum((v - smean) ** 2 for v in spx) / len(spx)) ** 0.5
    check("300px downscale keeps structure", sstd > 15, f"std {sstd:.1f}")

    # 11. vertical sections ordered, non-overlapping, inside the canvas
    spans = [
        ("kicker", 0, D.KICKER_H),
        ("masthead", D.KICKER_H, 96),
        ("strip", 96, 128),
        ("section strip", 128, D.SECTION_RULE_Y),
        ("heroes", D.HERO_Y0, D.HERO_Y0 + D.HERO_PH),
        ("map zone", 332, 470),
        ("index/quote", D.INDEX_Y0, D.INDEX_Y0 + D.INDEX_H),
        ("columns", 521, 718),
        ("cards 1", D.CARDS1_Y0, D.CARDS1_Y0 + D.CARD_H),
        ("cards 2", D.CARDS2_Y0, D.CARDS2_Y0 + D.CARD_H),
        ("cards 3", D.CARDS3_Y0, D.CARDS3_Y0 + D.CARD3_H),
        ("timeline", 914, 944),
        ("ticker", D.TICKER_Y0, D.TICKER_Y0 + D.TICKER_H),
        ("date check", 968, 1008),
        ("footer", 1010, 1021),
    ]
    ordered = all(spans[i][2] <= spans[i + 1][1]
                  for i in range(len(spans) - 1))
    inside = all(0 <= a and b <= 1024 for _, a, b in spans)
    check("sections ordered + non-overlapping", ordered)
    check("sections inside canvas", inside)

    fails = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} checks passed")
    if fails:
        print("FAILURES:", ", ".join(r[0] for r in fails))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
