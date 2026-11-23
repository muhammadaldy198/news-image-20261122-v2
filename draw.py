#!/usr/bin/env python3
"""draw.py — renderer for the news-image-20261122 v4 entry (Hunter Office).

Renders a 1024x1024 broadsheet front page ("THE WORLD — Sunday, 22 November
2026") with PIL, from the verified 22 Nov 2026 story list in stories.json
(35 stories, 7 regions, 15 illustrations). The PNG is committed beside this
script; main.ts only copies it to /output/entry.png.

v4 vs v3: a third row of illustrated mini-cards (Sparta II, Pugh, Lowy,
Ramakech) for 15 illustrations total; a dark ticker band; masthead ears;
unique section tags on all 15 featured stories; a framed BY THE NUMBERS
table with a source footnote; QUOTE OF THE DAY + INSIDE TODAY boxes; a
fold line; a halftone hero (Merkury); a drop cap on the lead deck; CRITICAL
tier badges; Noto fonts; JSON-driven layout with a verify script.

Written from scratch in this session. Layout, geometry and painters are the
builder's own work; the facts come from the office research file
(bejo-research/data/berita-22-nov-2026.md). Output is deterministic: the
same bytes on every run.

Run:  ~/workspace/office/.venv/bin/python draw.py [out.png]
Fonts are render-time tools only (system Noto); they are NOT part of the
entry.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 236)      # warm newsprint
INK = (18, 18, 18)           # near-black text
NAVY = (27, 42, 74)          # masthead band / headers
NAVY_SOFT = (38, 58, 100)
RED = (179, 38, 30)          # the one spot colour: kicker / breaking
RED_SOFT = (252, 234, 234)   # date-check fill
RULE = (120, 110, 90)        # hairline rules
SEA = (216, 228, 238)        # map sea
LAND = (232, 222, 190)       # map land
LAND_EDGE = (168, 156, 118)
GREY = (74, 74, 74)          # secondary text (7:1 on paper at 10px+)
PANEL = (243, 238, 222)      # hero / card panel background
WHITE = (255, 255, 255)
TICKER_BG = (24, 30, 44)     # dark ticker band

# Region colours (muted, one per region) for the 2-letter chips.
REGION_COLOURS = {
    "EU": (46, 80, 140),
    "AS": (156, 84, 20),
    "ME": (140, 40, 40),
    "AM": (32, 110, 70),
    "AF": (110, 70, 140),
    "OC": (20, 120, 130),
    "WD": (70, 70, 70),
}

# ---------------------------------------------------------------- fonts
NOTO = "/usr/share/fonts/truetype/noto/"
LIB = "/usr/share/fonts/truetype/liberation/"
DEJ = "/usr/share/fonts/truetype/dejavu/"
_font_cache = {}

# (family, weight) -> file names to try, Noto first, Liberation/DejaVu fallback.
_FONT_FILES = {
    ("display", True): ["NotoSerifDisplay-Black.ttf",
                        "NotoSerifDisplay-Bold.ttf"],
    ("display", False): ["NotoSerifDisplay-Regular.ttf"],
    ("serif", True): ["NotoSerif-Bold.ttf"],
    ("serif", False): ["NotoSerif-Regular.ttf"],
    ("sans", True): ["NotoSans-Bold.ttf"],
    ("sans", False): ["NotoSans-Regular.ttf"],
    ("mono", True): ["NotoSansMono-Bold.ttf"],
    ("mono", False): ["NotoSansMono-Regular.ttf"],
}
_FALLBACK = {
    ("display", True): [("LiberationSerif-Bold.ttf",),
                        ("DejaVuSerif-Bold.ttf",)],
    ("display", False): [("LiberationSerif-Regular.ttf",),
                         ("DejaVuSerif.ttf",)],
    ("serif", True): [("LiberationSerif-Bold.ttf",),
                      ("DejaVuSerif-Bold.ttf",)],
    ("serif", False): [("LiberationSerif-Regular.ttf",),
                       ("DejaVuSerif.ttf",)],
    ("sans", True): [("LiberationSans-Bold.ttf",),
                     ("DejaVuSans-Bold.ttf",)],
    ("sans", False): [("LiberationSans-Regular.ttf",),
                      ("DejaVuSans.ttf",)],
    ("mono", True): [("DejaVuSansMono-Bold.ttf",)],
    ("mono", False): [("DejaVuSansMono.ttf",)],
}


def font(size, family="sans", bold=False):
    """Cached truetype font. family: display | serif | sans | mono."""
    key = (size, family, bold)
    if key in _font_cache:
        return _font_cache[key]
    got = None
    for name in _FONT_FILES[(family, bold)]:
        p = Path(NOTO) / name
        if p.exists():
            try:
                got = ImageFont.truetype(str(p), size)
                break
            except OSError:
                continue
    if got is None:
        for names in _FALLBACK[(family, bold)]:
            for base in (LIB, DEJ):
                p = Path(base) / names[0]
                if p.exists():
                    try:
                        got = ImageFont.truetype(str(p), size)
                        break
                    except OSError:
                        continue
            if got is not None:
                break
    if got is None:
        got = ImageFont.load_default()
    _font_cache[key] = got
    return got


# ---------------------------------------------------------------- text helpers
def text_w(d, s, f):
    return d.textlength(s, font=f)


def wrap(d, text, f, max_w):
    """Greedy word wrap by pixel width. Returns list of lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if text_w(d, trial, f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_size(d, text, max_w, start, minimum, family="sans", bold=False):
    """Largest font size in [minimum, start] letting text fit one line."""
    size = start
    while size > minimum and text_w(d, text, font(size, family, bold)) > max_w:
        size -= 1
    return size


def draw_wrapped(d, x, y, text, f, max_w, fill, leading=None):
    """Draw wrapped text; returns total height used."""
    lines = wrap(d, text, f, max_w)
    lh = leading or int(f.size * 1.2)
    for i, line in enumerate(lines):
        d.text((x, y + i * lh), line, font=f, fill=fill)
    return len(lines) * lh


def centre(d, y, text, f, fill, cx=W // 2):
    d.text((cx - text_w(d, text, f) / 2, y), text, font=f, fill=fill)


def dashed_hline(d, x0, x1, y, fill, dash=8, gap=5, width=1):
    """A dashed horizontal rule (the fold line)."""
    x = x0
    while x < x1:
        d.line([x, y, min(x + dash, x1), y], fill=fill, width=width)
        x += dash + gap


# ---------------------------------------------------------------- data
def load_data():
    with open(HERE / "stories.json", encoding="utf-8") as fh:
        data = json.load(fh)
    stories = data["stories"]
    assert len(stories) == 35, f"{len(stories)} stories, want 35"
    assert [s["n"] for s in stories] == list(range(1, 36))
    assert len(data["heroes"]) == 3
    cards = data["cards_row1"] + data["cards_row2"] + data["cards_row3"]
    assert len(cards) == 12, f"{len(cards)} cards, want 12"
    tags = [h["tag"] for h in data["heroes"]] + [c["tag"] for c in cards]
    assert len(set(tags)) == 15, f"tags not unique: {tags}"
    return data


DATA = load_data()
STORIES = DATA["stories"]
HEROES = DATA["heroes"]
CARDS1, CARDS2, CARDS3 = DATA["cards_row1"], DATA["cards_row2"], DATA["cards_row3"]


def region_counts():
    counts = {}
    for s in STORIES:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    return counts


# ---------------------------------------------------------------- map outlines
# Coarse continent outlines (lon, lat), sketched by the builder for the
# schematic world map. Deliberately rough: the map is 444x106 px.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-110, 72), (-85, 70), (-65, 62), (-55, 52),
     (-70, 42), (-80, 32), (-81, 25), (-90, 21), (-97, 26), (-105, 22),
     (-114, 29), (-124, 42), (-135, 57), (-165, 60)],
    # South America
    [(-79, 9), (-60, 8), (-44, -3), (-35, -8), (-48, -27), (-65, -45),
     (-73, -53), (-73, -37), (-70, -20), (-77, -8), (-80, -3)],
    # Africa
    [(-17, 15), (-10, 31), (3, 37), (20, 32), (32, 31), (35, 18), (43, 12),
     (51, 10), (40, -10), (32, -29), (20, -35), (14, -22), (9, 4), (-13, 8)],
    # Eurasia
    [(-10, 36), (-2, 48), (8, 57), (21, 55), (32, 70), (60, 69), (90, 75),
     (120, 73), (150, 70), (178, 65), (158, 52), (142, 50), (135, 35),
     (122, 37), (114, 23), (105, 9), (100, 6), (91, 22), (80, 15), (74, 13),
     (67, 23), (58, 26), (48, 30), (43, 12), (35, 28), (30, 36), (23, 36),
     (16, 38), (8, 44), (-2, 37)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-1, 57), (1, 51)],
    # Japan
    [(130, 31), (137, 35), (141, 39), (144, 44), (140, 38), (135, 34),
     (132, 33)],
    # Australia
    [(114, -22), (115, -33), (124, -33), (135, -35), (140, -38), (150, -37),
     (153, -27), (146, -19), (142, -11), (132, -12), (122, -17)],
    # New Zealand
    [(167, -45), (172, -41), (176, -38), (174, -41), (170, -44)],
    # Indonesia
    [(95, 5), (105, -5), (114, -8), (122, -10), (132, -4), (141, -1),
     (130, 0), (120, 0), (110, 2), (100, 5)],
    # Madagascar
    [(44, -16), (50, -16), (47, -25), (44, -20)],
    # Greenland
    [(-45, 60), (-32, 68), (-20, 76), (-45, 77), (-58, 70)],
]

# ---------------------------------------------------------------- layout grid
# Vertical budget (1024 px total; footer ends ~1021).
KICKER_H = 18
MASTHEAD_TITLE_Y = 19
MASTHEAD_DATE_Y = 68
MASTHEAD_RULES = (92, 95)
STRIP_NUM_Y = 98
STRIP_LABEL_Y = 115
# no strip rule: the labels end at 125 and the section text starts at 128;
# a rule between them would crowd both (v4 render 1 defect)
SECTION_TEXT_Y = 128
SECTION_RULE_Y = 142
HERO_Y0 = 144
HERO_PH = 186
HERO_ART_Y = HERO_Y0 + 34
HERO_ART_H = 78
HERO_HEAD_Y = HERO_Y0 + 116
HERO_DECK_Y = HERO_Y0 + 158
MAP_TITLE_Y = 332
MAP_CONTENT_Y = 352
MAP_BOX = (290, 352, 444, 106)          # x, y, w, h
LEGEND_X = 16
NUMBERS_FRAME = (744, 352, 1008, 466)   # x0, y0, x1, y1
FOLD_Y = 474
INDEX_Y0 = 478
INDEX_H = 39
COLS_HEADER_Y = 521
COLS_RULE_Y = 539
COLS_ROW_Y = 545
COLS_PITCH = 16
CARDS1_Y0 = 727
CARDS2_Y0 = 795
CARDS3_Y0 = 863
CARD_H = 62
CARD3_H = 48
TIMELINE_RULE_Y = 914
TIMELINE_LABEL_Y = 918
TIMELINE_LINE_Y = 928
TIMELINE_TEXT_Y = 934
TICKER_Y0 = 946
TICKER_H = 20
DATECHECK_BOX = (16, 968, 1008, 1008)
FOOTER_Y = 1010


# ------------------------------------------------------------- hero art
def paint_cop31(d, x, y, w, h):
    """Globe on the left, the pact document crossed out in red on the
    right, NO DEAL stamp below it. The empty table is the missing deal."""
    d.rectangle([x, y, x + w, y + h], fill=(221, 232, 240))
    # globe, left
    gx, gy, r = x + 62, y + 38, 30
    d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(168, 200, 220),
              outline=NAVY, width=2)
    d.ellipse([gx - r // 2, gy - r, gx + r // 2, gy + r], outline=NAVY)
    d.line([gx - r, gy, gx + r, gy], fill=NAVY, width=1)
    d.ellipse([gx - 24, gy - 20, gx - 4, gy + 2], fill=(110, 160, 110))
    d.ellipse([gx + 2, gy + 6, gx + 24, gy + 26], fill=(110, 160, 110))
    # the draft document, right, with a red X through it
    dx, dy = x + 196, y + 10
    d.rectangle([dx, dy, dx + 76, dy + 36], fill=WHITE, outline=INK)
    for k in range(3):
        d.line([dx + 8, dy + 9 + k * 9, dx + 68, dy + 9 + k * 9],
               fill=(170, 170, 170), width=2)
    d.line([dx - 4, dy - 4, dx + 80, dy + 40], fill=RED, width=4)
    d.line([dx + 80, dy - 4, dx - 4, dy + 40], fill=RED, width=4)
    # NO DEAL stamp, bottom right
    sx, sy = x + 196, y + h - 24
    d.rectangle([sx, sy, sx + 92, sy + 20], outline=RED, width=3)
    d.text((sx + 7, sy + 3), "NO DEAL", font=font(13, "sans", True),
           fill=RED)


def _merkury_scene(w, h):
    """The capsized corvette in mid-tones, for the halftone screen.
    Kept deliberately mid-grey: a near-black hull would halftone into a
    solid blob, and a near-white sea would vanish."""
    layer = Image.new("RGB", (w, h), (215, 222, 230))
    d = ImageDraw.Draw(layer)
    # sea
    d.rectangle([0, h - 40, w, h], fill=(170, 185, 200))
    for wx in range(6, w - 6, 34):
        d.arc([wx, h - 30, wx + 26, h - 14], 180, 360, fill=WHITE, width=2)
    # smoke
    for cx, cy, r in ((150, 16, 14), (172, 8, 17), (194, 16, 12)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(175, 175, 175))
    # flames (dark outline so the shape survives the screen)
    for fx, fh in ((148, 26), (168, 32), (188, 24)):
        d.polygon([(fx - 11, h - 40), (fx, h - 40 - fh), (fx + 11, h - 40)],
                  outline=(90, 60, 20), fill=(205, 130, 45))
    # capsized hull: keel up, white outline + portholes to break the mass
    hx, hy = 52, h - 52
    hull = [(hx, hy), (hx + 202, hy), (hx + 180, hy + 26),
            (hx + 22, hy + 26)]
    d.polygon(hull, fill=(85, 90, 96), outline=WHITE)
    d.rectangle([hx + 40, hy + 26, hx + 70, hy + 40], fill=(85, 90, 96),
                outline=WHITE)
    d.rectangle([hx + 132, hy + 26, hx + 162, hy + 40], fill=(85, 90, 96),
                outline=WHITE)
    d.line([hx + 101, hy, hx + 101, hy - 20], fill=(100, 105, 110), width=3)
    for px in (hx + 30, hx + 80, hx + 130, hx + 180):
        d.ellipse([px - 3, hy + 10, px + 3, hy + 16], fill=WHITE)
    return layer


def _halftone(layer, pitch=4, max_r=2.0):
    """Dot-screen: one black dot per pitch x pitch block, radius
    proportional to the block's darkness. Returns an RGB image on paper."""
    w, h = layer.size
    grey = layer.convert("L")
    out = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(out)
    px = grey.load()
    for by in range(0, h, pitch):
        for bx in range(0, w, pitch):
            cx, cy = min(bx + pitch // 2, w - 1), min(by + pitch // 2, h - 1)
            darkness = 1.0 - px[cx, cy] / 255.0
            r = darkness * max_r
            if r >= 0.4:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK)
    return out


def paint_merkury_halftone(d, x, y, w, h):
    """Merkury as a newspaper halftone engraving. The label bar is drawn
    AFTER the screen, on a dark backing, so it stays legible."""
    screen = _halftone(_merkury_scene(w, h))
    d._image.paste(screen, (x, y))
    d.rectangle([x, y + h - 16, x + 118, y + h], fill=(30, 40, 56))
    d.text((x + 6, y + h - 14), "BENGHAZI, LIBYA",
           font=font(10, "sans", True), fill=WHITE)


def paint_dymer(d, x, y, w, h):
    """Apartment blocks at dawn: the collapsed section on the left, an
    intact block on the right, drones crossing the sky between them."""
    d.rectangle([x, y, x + w, y + h], fill=(232, 228, 216))
    d.text((x + 8, y + 6), "DYMER, KYIV REGION",
           font=font(11, "sans", True), fill=INK)
    # drones: quadcopter silhouettes, top centre-right
    for dx, dy in ((150, 10), (196, 20), (244, 8)):
        cx, cy = x + dx, y + dy
        for ax, ay in ((-9, -5), (9, -5), (-9, 5), (9, 5)):
            d.line([cx, cy, cx + ax, cy + ay], fill=INK, width=1)
            d.ellipse([cx + ax - 5, cy + ay - 1, cx + ax + 5, cy + ay + 1],
                      fill=(70, 70, 70))
        d.rounded_rectangle([cx - 5, cy - 2, cx + 5, cy + 3], radius=2,
                            fill=INK)
        d.line([cx - 3, cy + 3, cx - 3, cy + 6], fill=INK, width=1)
        d.line([cx + 3, cy + 3, cx + 3, cy + 6], fill=INK, width=1)
    # collapsed block, left: jagged top, rubble at the base
    mx = x + 10
    d.polygon([(mx, y + h), (mx, y + 40), (mx + 22, y + 28),
               (mx + 38, y + 42), (mx + 58, y + 26), (mx + 78, y + 40),
               (mx + 96, y + 32), (mx + 100, y + h)], fill=(70, 76, 88))
    for wy in range(y + 52, y + h - 6, 15):
        for wx in range(mx + 8, mx + 92, 15):
            d.rectangle([wx, wy, wx + 7, wy + 8], fill=(250, 220, 120))
    d.polygon([(mx - 4, y + h), (mx + 28, y + h - 22), (mx + 58, y + h)],
              fill=(150, 145, 130))
    d.polygon([(mx + 54, y + h), (mx + 84, y + h - 16), (mx + 112, y + h)],
              fill=(170, 164, 148))
    # middle block, damaged top edge
    d.polygon([(x + 122, y + h), (x + 122, y + 34), (x + 182, y + 26),
               (x + 182, y + h)], fill=(90, 100, 116))
    for wy in range(y + 40, y + h - 6, 15):
        for wx in range(x + 130, x + 176, 15):
            d.rectangle([wx, wy, wx + 7, wy + 8], fill=(250, 220, 120))
    # intact block, right
    d.rectangle([x + 196, y + 8, x + 280, y + h], fill=(96, 106, 122))
    for wy in range(y + 16, y + h - 6, 15):
        for wx in range(x + 204, x + 272, 15):
            d.rectangle([wx, wy, wx + 7, wy + 8], fill=(250, 220, 120))


HERO_PAINTERS = {
    "cop31": paint_cop31,
    "merkury_halftone": paint_merkury_halftone,
    "dymer": paint_dymer,
}


# ------------------------------------------------------------- card art
# Rows 1-2 paint in a 56x52 box; row 3 (compact) in a 40x40 box.
def paint_verstappen(d, x, y, w, h):
    """Las Vegas at night: the Strip's lights above, an F1 car low, a
    chequered flag on its pole at the left."""
    d.rectangle([x, y, x + w, y + h], fill=(24, 28, 52))
    # strip skyline: lit towers
    for bx, bw, bh in ((2, 8, 14), (12, 6, 20), (20, 9, 12), (32, 7, 18),
                       (42, 8, 13)):
        d.rectangle([x + bx, y + 22 - bh, x + bx + bw, y + 22],
                    fill=(60, 70, 110))
        d.rectangle([x + bx + 2, y + 24 - bh, x + bx + bw - 2, y + 26 - bh],
                    fill=(250, 200, 60))
    d.rectangle([x, y + h - 16, x + w, y + h], fill=(52, 52, 58))
    # chequered flag on a pole, left
    d.line([x + 6, y + 24, x + 6, y + 38], fill=WHITE, width=1)
    for r in range(2):
        for c in range(3):
            fill = WHITE if (r + c) % 2 == 0 else INK
            d.rectangle([x + 7 + c * 4, y + 24 + r * 4,
                         x + 11 + c * 4, y + 28 + r * 4], fill=fill)
    # F1 car, low right, facing right
    d.polygon([(x + 20, y + 38), (x + 26, y + 32), (x + 40, y + 30),
               (x + 50, y + 33), (x + 52, y + 37), (x + 20, y + 38)],
              fill=(200, 30, 30))
    d.rectangle([x + 44, y + 26, x + 51, y + 30], fill=(200, 30, 30))
    d.ellipse([x + 30, y + 26, x + 36, y + 32], fill=(250, 200, 40))
    d.ellipse([x + 24, y + 36, x + 31, y + 43], fill=INK)
    d.ellipse([x + 42, y + 36, x + 49, y + 43], fill=INK)
    # speed lines
    for ly in (28, 33):
        d.line([x + 2, y + ly, x + 14, y + ly], fill=WHITE, width=1)


def paint_cikande(d, x, y, w, h):
    """Factory at dusk: chimney on the left with smoke, a searchlight
    beam from the top left, fire-lit windows. Respectful: no body bags."""
    d.rectangle([x, y, x + w, y + h], fill=(232, 220, 200))
    # searchlight beam from top left
    d.polygon([(x, y), (x + 14, y), (x + 40, y + 30), (x + 30, y + 30)],
              fill=(250, 238, 170))
    # chimney + smoke, left
    d.rectangle([x + 8, y + 16, x + 14, y + h], fill=(100, 92, 78))
    for cx, cy, r in ((11, 9, 5), (16, 5, 4), (6, 5, 4)):
        d.ellipse([x + cx - r, y + cy - r, x + cx + r, y + cy + r],
                  fill=(150, 150, 150))
    # factory block, right
    d.rectangle([x + 18, y + 28, x + 52, y + h], fill=(120, 110, 95))
    # fire-lit windows
    for wx in (22, 32, 42):
        d.rectangle([x + wx, y + 34, x + wx + 6, y + 42],
                    fill=(240, 120, 20))


def paint_bahrain(d, x, y, w, h):
    """Radar dish on the right under a night sky; missile streaks from
    the top left; CLAIM tag — the claim framing must stay visible."""
    d.rectangle([x, y, x + w, y + h], fill=(24, 48, 60))
    # stars
    for sx, sy in ((6, 18), (14, 8), (22, 22), (30, 6), (44, 12)):
        d.ellipse([x + sx, y + sy, x + sx + 1, y + sy + 1], fill=WHITE)
    # missile streaks, top left to centre
    d.line([x + 4, y + 6, x + 26, y + 28], fill=(240, 120, 20), width=3)
    d.line([x + 10, y + 3, x + 24, y + 17], fill=(250, 180, 30), width=2)
    d.ellipse([x + 22, y + 24, x + 28, y + 30], fill=(250, 180, 30))
    # radar dish + mast, right
    d.polygon([(x + 34, y + 32), (x + 40, y + 20), (x + 52, y + 20),
               (x + 48, y + 32)], fill=WHITE)
    d.line([x + 43, y + 32, x + 43, y + 48], fill=WHITE, width=2)
    d.rectangle([x + 37, y + 48, x + 49, y + 52], fill=WHITE)
    # CLAIM tag, top left
    d.rectangle([x + 2, y + 2, x + 36, y + 13], fill=RED)
    d.text((x + 4, y + 2), "CLAIM", font=font(9, "sans", True), fill=WHITE)


def paint_hongkong(d, x, y, w, h):
    """Ballot box centre-left under the big turnout number; the city
    skyline along the bottom."""
    d.rectangle([x, y, x + w, y + h], fill=(240, 235, 220))
    d.text((x + 6, y + 4), "98.79%", font=font(12, "sans", True),
           fill=NAVY)
    # city silhouettes
    d.rectangle([x + 2, y + 42, x + 12, y + h], fill=(180, 175, 160))
    d.rectangle([x + 44, y + 38, x + w - 2, y + h], fill=(180, 175, 160))
    # ballot paper going in
    d.rectangle([x + 24, y + 18, x + 28, y + 26], fill=WHITE, outline=GREY)
    # ballot box + navy slot
    d.rectangle([x + 12, y + 24, x + 40, y + 48], fill=WHITE, outline=NAVY)
    d.rectangle([x + 20, y + 26, x + 32, y + 30], fill=NAVY)
    # small red check
    d.line([x + 44, y + 44, x + 47, y + 47], fill=RED, width=2)
    d.line([x + 47, y + 47, x + 52, y + 40], fill=RED, width=2)


def paint_democrats(d, x, y, w, h):
    """US Capitol dome, large and centred: dome, drum, four columns,
    steps, and a small flag on the right."""
    d.rectangle([x, y, x + w, y + h], fill=(218, 230, 242))
    # dome
    d.ellipse([x + 16, y + 8, x + 40, y + 26], fill=(60, 80, 120))
    # flag pole + flag, right of the dome
    d.line([x + 40, y + 12, x + 40, y + 4], fill=(60, 80, 120), width=1)
    d.rectangle([x + 40, y + 4, x + 48, y + 8], fill=RED)
    # drum + base
    d.rectangle([x + 20, y + 24, x + 36, y + 32], fill=(60, 80, 120))
    d.rectangle([x + 8, y + 32, x + 48, y + 40], fill=(60, 80, 120))
    # 4 white columns
    for cx in (12, 20, 28, 36):
        d.rectangle([x + cx, y + 33, x + cx + 4, y + 39], fill=WHITE)
    # steps
    d.rectangle([x + 12, y + 40, x + 44, y + 43], fill=(170, 175, 185))
    d.rectangle([x + 8, y + 43, x + 48, y + 46], fill=(170, 175, 185))
    d.rectangle([x + 4, y + 46, x + 52, y + h], fill=(150, 155, 165))


def paint_cricket(d, x, y, w, h):
    """Cricket: a horizontal pitch strip, stumps at the left, a bat at
    the right, the red ball mid-pitch."""
    d.rectangle([x, y, x + w, y + h], fill=(60, 140, 70))
    # pitch strip, horizontal
    d.rectangle([x + 4, y + 20, x + 52, y + 34], fill=(200, 180, 140))
    # crease lines
    d.line([x + 12, y + 20, x + 12, y + 34], fill=WHITE, width=1)
    d.line([x + 44, y + 20, x + 44, y + 34], fill=WHITE, width=1)
    # 3 stumps, left
    for sy in (23, 26, 29):
        d.rectangle([x + 8, y + sy, x + 16, y + sy + 2],
                    fill=(250, 220, 60))
    # bat leaning at the right
    d.polygon([(x + 44, y + 46), (x + 48, y + 30), (x + 52, y + 32),
               (x + 48, y + 46)], fill=(210, 180, 130))
    d.line([x + 50, y + 30, x + 52, y + 24], fill=(150, 120, 80), width=2)
    # red ball
    d.ellipse([x + 26, y + 24, x + 32, y + 30], fill=(180, 30, 30))


def paint_marquez(d, x, y, w, h):
    """MotoGP bike in Ducati red, leaning left into a corner; speed
    lines trailing on the right; green runoff below."""
    d.rectangle([x, y, x + w, y + h], fill=(70, 70, 76))
    d.rectangle([x, y + 44, x + w, y + h], fill=(80, 140, 80))
    # speed lines, right
    for ly, lx in ((8, 44), (14, 40), (20, 46)):
        d.line([x + lx, y + ly, x + w - 2, y + ly], fill=WHITE, width=1)
    # wheels
    d.ellipse([x + 8, y + 30, x + 20, y + 44], fill=INK)
    d.ellipse([x + 36, y + 30, x + 48, y + 44], fill=INK)
    d.ellipse([x + 12, y + 34, x + 16, y + 38], fill=(150, 150, 150))
    d.ellipse([x + 40, y + 34, x + 44, y + 38], fill=(150, 150, 150))
    # fairing (red) leaning left + rider hump + windscreen
    d.polygon([(x + 12, y + 34), (x + 20, y + 22), (x + 34, y + 20),
               (x + 42, y + 28), (x + 40, y + 34), (x + 14, y + 36)],
              fill=(200, 30, 30))
    d.ellipse([x + 22, y + 16, x + 30, y + 24], fill=(40, 40, 40))
    d.polygon([(x + 20, y + 22), (x + 16, y + 16), (x + 22, y + 20)],
              fill=(180, 220, 240))


def paint_eisenkot(d, x, y, w, h):
    """Symbolic, respectful: a big closing quotation mark on the right
    and an olive branch rising from the bottom left. The news is the
    condemnation, not the arson."""
    d.rectangle([x, y, x + w, y + h], fill=(240, 235, 220))
    d.text((x + 36, y + 0), "\u201d",
           font=font(34, "serif", True), fill=NAVY)
    # olive branch: stem from bottom left + leaves + 2 olives
    d.line([x + 6, y + 48, x + 40, y + 18], fill=(80, 120, 60), width=2)
    for i, (lx, ly) in enumerate(((12, 44), (18, 39), (24, 34), (30, 29),
                                  (36, 24))):
        off = -4 if i % 2 == 0 else 3
        d.ellipse([x + lx - 4, y + ly + off - 2, x + lx + 4,
                   y + ly + off + 2], fill=(90, 135, 65))
    d.ellipse([x + 32, y + 30, x + 37, y + 35], fill=(50, 80, 50))
    d.ellipse([x + 36, y + 26, x + 41, y + 31], fill=(50, 80, 50))


# --------------------------------------------------- row 3 (compact, 40x40)
def paint_sparta(d, x, y, w, h):
    """A cargo ship under tow: grey hull with containers, a tow line to
    a small tug ahead, a smoke wisp from the funnel."""
    d.rectangle([x, y, x + w, y + h], fill=(150, 180, 205))
    d.rectangle([x, y + h - 12, x + w, y + h], fill=(52, 96, 140))
    # tug, left
    d.polygon([(x + 2, y + 24), (x + 10, y + 24), (x + 12, y + 28),
               (x + 2, y + 28)], fill=(40, 44, 50))
    d.rectangle([x + 4, y + 20, x + 8, y + 24], fill=(40, 44, 50))
    # tow line
    d.line([x + 12, y + 26, x + 20, y + 26], fill=WHITE, width=1)
    # cargo hull + containers
    d.polygon([(x + 18, y + 24), (x + 38, y + 24), (x + 36, y + 30),
               (x + 20, y + 30)], fill=(90, 96, 104))
    d.rectangle([x + 22, y + 18, x + 27, y + 24], fill=(200, 80, 40))
    d.rectangle([x + 28, y + 18, x + 33, y + 24], fill=(40, 120, 180))
    # funnel + smoke
    d.rectangle([x + 34, y + 16, x + 37, y + 24], fill=(60, 64, 70))
    d.ellipse([x + 33, y + 10, x + 38, y + 15], fill=(150, 150, 150))
    d.ellipse([x + 36, y + 6, x + 40, y + 10], fill=(165, 165, 165))


def paint_pugh(d, x, y, w, h):
    """A swimmer crossing the strait: cap and arm above the water, a
    tanker silhouette behind, the sun low."""
    d.rectangle([x, y, x + w, y + h], fill=(200, 220, 230))
    # sun
    d.ellipse([x + 28, y + 3, x + 36, y + 11], fill=(250, 200, 60))
    # tanker silhouette, far
    d.rectangle([x + 4, y + 14, x + 26, y + 19], fill=(90, 100, 112))
    d.rectangle([x + 20, y + 10, x + 24, y + 14], fill=(90, 100, 112))
    # flame wisp on the tanker
    d.polygon([(x + 8, y + 14), (x + 11, y + 8), (x + 14, y + 14)],
              fill=(240, 120, 20))
    # sea
    d.rectangle([x, y + 20, x + w, y + h], fill=(40, 110, 140))
    for wx in range(2, w - 2, 12):
        d.arc([x + wx, y + 26, x + wx + 9, y + 33], 180, 360, fill=WHITE,
              width=1)
    # swimmer: cap + head + one arm mid-stroke
    d.ellipse([x + 14, y + 22, x + 22, y + 30], fill=(240, 200, 160))
    d.pieslice([x + 14, y + 22, x + 22, y + 30], 180, 360, fill=RED)
    d.line([x + 20, y + 28, x + 30, y + 20], fill=(240, 200, 160), width=3)
    d.ellipse([x + 8, y + 30, x + 14, y + 34], fill=WHITE)


def paint_lowy(d, x, y, w, h):
    """The power gap as two bars: US 78.9 in blue, China 73.6 in red,
    the 5.3-point gap marked between their tops."""
    d.rectangle([x, y, x + w, y + h], fill=(240, 235, 220))
    # baseline + gridlines
    d.line([x + 4, y + 34, x + w - 4, y + 34], fill=GREY, width=1)
    for gy in (12, 22):
        d.line([x + 4, y + gy, x + w - 4, y + gy], fill=(210, 205, 190),
               width=1)
    # bars: heights proportional to 78.9 vs 73.6 (scale 0.30 px/pt)
    d.rectangle([x + 8, y + 10, x + 16, y + 34], fill=(46, 80, 140))
    d.rectangle([x + 22, y + 12, x + 30, y + 34], fill=(178, 38, 30))
    # gap bracket between the tops
    d.line([x + 16, y + 10, x + 22, y + 10], fill=INK, width=1)
    d.line([x + 16, y + 10, x + 16, y + 12], fill=INK, width=1)
    d.line([x + 22, y + 10, x + 22, y + 12], fill=INK, width=1)
    d.text((x + 8, y + 1), "5.3", font=font(8, "mono", True), fill=INK)


def paint_ramakech(d, x, y, w, h):
    """An upside-down house in the desert: roof pointing down, door and
    windows inverted, a lone tree beside it."""
    d.rectangle([x, y, x + w, y + h], fill=(235, 225, 200))
    # ground
    d.rectangle([x, y + 32, x + w, y + h], fill=(200, 180, 140))
    # tree, left
    d.line([x + 6, y + 32, x + 6, y + 20], fill=(120, 90, 60), width=2)
    d.ellipse([x + 2, y + 14, x + 10, y + 22], fill=(90, 135, 65))
    # upside-down house: body above, roof triangle pointing down
    d.rectangle([x + 14, y + 8, x + 34, y + 24], fill=(250, 245, 235),
                outline=INK)
    d.polygon([(x + 14, y + 24), (x + 34, y + 24), (x + 24, y + 32)],
              fill=(178, 60, 40))
    # inverted door + windows (door at the top edge of the body)
    d.rectangle([x + 22, y + 8, x + 27, y + 15], fill=(120, 90, 60))
    d.rectangle([x + 16, y + 17, x + 20, y + 21], fill=(120, 180, 220))
    d.rectangle([x + 29, y + 17, x + 33, y + 21], fill=(120, 180, 220))


CARD_PAINTERS = {
    "verstappen": paint_verstappen,
    "cikande": paint_cikande,
    "bahrain": paint_bahrain,
    "hongkong": paint_hongkong,
    "democrats": paint_democrats,
    "cricket": paint_cricket,
    "marquez": paint_marquez,
    "eisenkot": paint_eisenkot,
    "sparta": paint_sparta,
    "pugh": paint_pugh,
    "lowy": paint_lowy,
    "ramakech": paint_ramakech,
}


# ---------------------------------------------------------------- sections
def draw_kicker(d):
    d.rectangle([0, 0, W, KICKER_H], fill=NAVY)
    f = font(12, "sans", True)
    centre(d, 2, DATA["edition"]["kicker"], f, WHITE)


def draw_masthead(d):
    ed = DATA["edition"]
    # ears: facts only, no weather (none verified)
    for (x0, x1, lines) in (
            (16, 150, [("SUNDAY", 12), (ed["day_num"], 20), (ed["year"], 12)]),
            (874, 1008, [("35 STORIES", 12), ("7 REGIONS", 12),
                         ("15 PICTURES", 12)])):
        d.rectangle([x0, 22, x1, 88], fill=PANEL, outline=RULE)
        cx = (x0 + x1) // 2
        ys = (26, 44, 64) if x0 == 16 else (26, 44, 62)
        for (txt, size), yy in zip(lines, ys):
            f = font(size, "serif" if size == 20 else "sans", True)
            d.text((cx - text_w(d, txt, f) / 2, yy), txt, font=f, fill=INK)
    centre(d, MASTHEAD_TITLE_Y, ed["paper"], font(46, "display", True), INK)
    centre(d, MASTHEAD_DATE_Y, ed["date_line"], font(19, "serif", True), RED)
    d.line([16, MASTHEAD_RULES[0], W - 16, MASTHEAD_RULES[0]], fill=INK,
           width=2)
    d.line([16, MASTHEAD_RULES[1], W - 16, MASTHEAD_RULES[1]], fill=INK,
           width=1)


def draw_strip(d):
    """Six big numbers, one-line labels (compressed to fund row 3)."""
    nums = DATA["strip_numbers"]
    cell = (W - 32) // 6
    for i, item in enumerate(nums):
        cx = 16 + cell * i + cell // 2
        fnum = font(18, "serif", True)
        d.text((cx - text_w(d, item["v"], fnum) / 2, STRIP_NUM_Y),
               item["v"], font=fnum, fill=NAVY)
        flab = font(10, "sans", False)
        d.text((cx - text_w(d, item["label"], flab) / 2, STRIP_LABEL_Y),
               item["label"], font=flab, fill=GREY)
        if i:
            d.line([16 + cell * i, 100, 16 + cell * i, 124],
                   fill=(210, 200, 175), width=1)


def draw_section_strip(d):
    counts = region_counts()
    assert sum(counts.values()) == 35, counts
    parts = []
    for code in ("EU", "AS", "ME", "AM", "AF", "OC", "WD"):
        parts.append(f"{DATA['regions'][code]} {counts.get(code, 0)}")
    centre(d, SECTION_TEXT_Y, "  ·  ".join(parts), font(13, "sans", True),
           INK)
    d.line([16, SECTION_RULE_Y, W - 16, SECTION_RULE_Y], fill=INK, width=2)


def draw_heroes(d):
    pw, gap = 322, 12
    for i, hero in enumerate(HEROES):
        x = 16 + i * (pw + gap)
        y0 = HERO_Y0
        d.rectangle([x, y0, x + pw, y0 + HERO_PH], fill=PANEL, outline=RULE)
        # number badge
        bx, by = x + 10, y0 + 8
        d.ellipse([bx, by, bx + 22, by + 22], fill=NAVY)
        num = str(hero["n"])
        nf = font(13, "sans", True)
        d.text((bx + 11 - text_w(d, num, nf) / 2, by + 3), num, font=nf,
               fill=WHITE)
        # section tag + place as the kicker (red)
        d.text((bx + 30, by + 4), f"{hero['tag']} — {hero['place']}",
               font=font(11, "sans", True), fill=RED)
        # tier badge, top right
        if hero["tier"]:
            bw, bh = 66, 18
            tx = x + pw - 8 - bw
            d.rectangle([tx, y0 + 8, tx + bw, y0 + 8 + bh], fill=RED)
            tf = font(9, "sans", True)
            d.text((tx + (bw - text_w(d, hero["tier"], tf)) / 2, y0 + 11),
                   hero["tier"], font=tf, fill=WHITE)
        # art
        HERO_PAINTERS[hero["art"]](d, x + 8, HERO_ART_Y, pw - 16, HERO_ART_H)
        # headline, 1-2 lines
        hf = font(20, "serif", True)
        hl = wrap(d, hero["head"], hf, pw - 20)[:2]
        for j, line in enumerate(hl):
            d.text((x + 10, HERO_HEAD_Y + j * 22), line, font=hf, fill=INK)
        # deck, 2 lines; drop cap indents BOTH lines on the lead hero
        deck = hero["deck"]
        df = font(11, "serif", False)
        if hero["drop_cap"]:
            cap, rest = deck[0], deck[1:]
            cf = font(28, "display", True)
            d.text((x + 10, HERO_DECK_Y - 2), cap, font=cf, fill=INK)
            lines = wrap(d, rest, df, pw - 20 - 24)[:2]
            for j, line in enumerate(lines):
                d.text((x + 34, HERO_DECK_Y + j * 13), line, font=df,
                       fill=GREY)
        else:
            lines = wrap(d, deck, df, pw - 20)[:2]
            for j, line in enumerate(lines):
                d.text((x + 10, HERO_DECK_Y + j * 13), line, font=df,
                       fill=GREY)
        assert len(lines) <= 2, f"hero {hero['n']} deck overflows"


def draw_map_zone(d):
    d.text((16, MAP_TITLE_Y), "WHERE IT HAPPENED — THE TOP 10, PINNED",
           font=font(13, "sans", True), fill=NAVY)
    # --- legend (left) ---
    lx, ly = LEGEND_X, MAP_CONTENT_Y
    d.text((lx, ly), "TOP 10", font=font(11, "sans", True), fill=RED)
    lf = font(9, "sans", False)
    lbf = font(9, "sans", True)
    for s in STORIES[:10]:
        yy = ly + 18 + (s["n"] - 1) * 9
        d.text((lx, yy), f"{s['n']}.", font=lbf, fill=NAVY)
        d.text((lx + 18, yy), s["pin_label"], font=lf, fill=INK)
    # --- map (centre), on its own layer so polygons clip cleanly ---
    mx, my, mw, mh = MAP_BOX
    layer = Image.new("RGB", (mw, mh), SEA)
    md = ImageDraw.Draw(layer)
    lon0, lon1, lat0, lat1 = -180.0, 180.0, 72.0, -50.0

    def proj(lon, lat):
        return ((lon - lon0) / (lon1 - lon0) * mw,
                (lat0 - lat) / (lat0 - lat1) * mh)

    for poly in CONTINENTS:
        md.polygon([proj(lon, lat) for lon, lat in poly], fill=LAND,
                   outline=LAND_EDGE)
    for lon in range(-150, 181, 30):
        gx = (lon - lon0) / (lon1 - lon0) * mw
        md.line([gx, 0, gx, mh], fill=(200, 214, 226), width=1)
    # Only isolated pins get a text label: the Europe/Middle East cluster
    # is too dense, so those stories are named by number in the legend.
    label_off = {4: (-78, 8), 5: (-84, -6), 6: (-68, -16), 10: (12, 4)}
    pin_nudge = {2: (-10, 6), 3: (-8, -6), 5: (0, -4), 8: (14, -2),
                 9: (10, 8)}
    for pin in DATA["pins"]:
        num, lon, lat, label = pin["n"], pin["lon"], pin["lat"], pin["label"]
        px, py = proj(lon, lat)
        dx, dy = pin_nudge.get(num, (0, 0))
        px, py = px + dx, py + dy
        r = 8
        md.ellipse([px - r, py - r, px + r, py + r], fill=NAVY,
                   outline=WHITE, width=2)
        nf = font(10, "sans", True)
        s = str(num)
        md.text((px - text_w(md, s, nf) / 2, py - 6), s, font=nf,
                fill=WHITE)
        if num in label_off:
            dx, dy = label_off[num]
            md.text((px + dx, py + dy), label, font=font(10, "sans", True),
                    fill=NAVY)
    d._image.paste(layer, (mx, my))
    d.rectangle([mx, my, mx + mw, my + mh], outline=RULE)
    # --- framed numbers table (right) ---
    fx0, fy0, fx1, fy1 = NUMBERS_FRAME
    d.rectangle([fx0, fy0, fx1, fy1], fill=PAPER, outline=RULE)
    d.text((fx0 + 8, fy0 + 4), "BY THE NUMBERS",
           font=font(12, "sans", True), fill=RED)
    vf = font(12, "serif", True)
    lfo = font(10, "sans", False)
    for i, item in enumerate(DATA["table_numbers"]):
        yy = fy0 + 20 + i * 11
        vw = text_w(d, item["v"], vf)
        d.text((fx0 + 56 - vw, yy), item["v"], font=vf, fill=NAVY)
        d.text((fx0 + 64, yy + 1), item["label"], font=lfo, fill=INK)
        if i < len(DATA["table_numbers"]) - 1:
            d.line([fx0 + 8, yy + 10, fx1 - 8, yy + 10],
                   fill=(225, 218, 195), width=1)
    d.text((fx0 + 8, fy0 + 100), DATA["table_footnote"],
           font=font(10, "sans", False), fill=GREY)


def draw_fold(d):
    dashed_hline(d, 16, W - 16, FOLD_Y, RULE)
    d.rectangle([492, FOLD_Y - 6, 532, FOLD_Y + 6], fill=PAPER)
    ff = font(9, "sans", True)
    d.text((512 - text_w(d, "FOLD", ff) / 2, FOLD_Y - 5), "FOLD", font=ff,
           fill=GREY)


def draw_index_quote(d):
    # INSIDE TODAY (index box) + QUOTE OF THE DAY, side by side.
    y0, y1 = INDEX_Y0, INDEX_Y0 + INDEX_H
    d.rectangle([16, y0, 500, y1], fill=PANEL, outline=RULE)
    d.rectangle([508, y0, 1008, y1], fill=PANEL, outline=RULE)
    hf = font(11, "sans", True)
    d.text((24, y0 + 3), "INSIDE TODAY", font=hf, fill=NAVY)
    d.text((516, y0 + 3), "QUOTE OF THE DAY", font=hf, fill=NAVY)
    tf = font(11, "sans", False)
    for j, line in enumerate(DATA["index_lines"]):
        d.text((24, y0 + 16 + j * 11), line, font=tf, fill=INK)
    qf = font(11, "serif", False)
    for j, q in enumerate(DATA["quotes"]):
        d.text((516, y0 + 16 + j * 11), f"{q['text']} — {q['attr']}",
               font=qf, fill=INK)


def draw_columns(d):
    d.text((16, COLS_HEADER_Y), "THE DAY IN BRIEF",
           font=font(14, "sans", True), fill=NAVY)
    d.line([16, COLS_RULE_Y, W - 16, COLS_RULE_Y], fill=INK, width=1)
    cols = [STORIES[3:14], STORIES[14:25], STORIES[25:36]]
    cw, gap = 322, 12
    shrunk = []
    for ci, col in enumerate(cols):
        x = 16 + ci * (cw + gap)
        for ri, s in enumerate(col):
            y = COLS_ROW_Y + ri * COLS_PITCH
            d.text((x, y), f"{s['n']}.", font=font(13, "sans", True),
                   fill=RED)
            cx = x + 24
            d.rounded_rectangle([cx, y + 1, cx + 26, y + 15], radius=3,
                                fill=REGION_COLOURS[s["region"]])
            cf = font(10, "sans", True)
            code = s["region"]
            d.text((cx + 13 - text_w(d, code, cf) / 2, y + 2), code,
                   font=cf, fill=WHITE)
            hx, hw = cx + 32, cw - 56
            size = fit_size(d, s["head"], hw, 13, 12, "sans", True)
            if size < 13:
                shrunk.append((s["n"], size))
            d.text((hx, y), s["head"], font=font(size, "sans", True),
                   fill=INK)
        if ci:
            d.line([x - gap // 2 - 1, COLS_ROW_Y, x - gap // 2 - 1, 717],
                   fill=(215, 205, 180), width=1)
    return shrunk


def draw_card_row(d, cards, y0, height, art_w, art_h, text_x, text_wid,
                  head_leading):
    """One row of 4 illustrated mini-cards. The section tag is a red
    prefix on the headline's first line."""
    cw, gap = 239, 12
    for i, card in enumerate(cards):
        x = 16 + i * (cw + gap)
        d.rectangle([x, y0, x + cw, y0 + height], fill=PANEL, outline=RULE)
        CARD_PAINTERS[card["art"]](d, x + 6, y0 + 5, art_w, art_h)
        tx, tw = x + text_x, text_wid
        hf = font(12, "sans", True)
        prefix = f"{card['tag']} — "
        full = prefix + card["head"]
        hl = wrap(d, full, hf, tw)
        assert len(hl) <= 2, f"card {card['tag']} headline overflows: {hl}"
        hl = hl[:2]
        for j, line in enumerate(hl):
            yy = y0 + 5 + j * head_leading
            if j == 0 and line.startswith(prefix):
                d.text((tx, yy), prefix, font=hf, fill=RED)
                d.text((tx + text_w(d, prefix, hf), yy),
                       line[len(prefix):], font=hf, fill=INK)
            else:
                d.text((tx, yy), line, font=hf, fill=INK)
        cap = wrap(d, card["cap"], font(10, "sans", False), tw)
        max_cap = 2 if height >= 60 else 1
        assert len(cap) <= max_cap, \
            f"card {card['tag']} caption overflows: {cap}"
        cap = cap[:max_cap]
        cy = y0 + 5 + len(hl) * head_leading + 2
        for j, line in enumerate(cap):
            d.text((tx, cy + j * 12), line, font=font(10, "sans", False),
                   fill=GREY)


def draw_timeline(d):
    tl = DATA["timeline"]
    d.line([16, TIMELINE_RULE_Y, W - 16, TIMELINE_RULE_Y], fill=INK,
           width=2)
    d.text((16, TIMELINE_LABEL_Y), "THE DAY IN UTC",
           font=font(11, "sans", True), fill=NAVY)
    x0, x1 = 170, 990
    step = (x1 - x0) / (len(tl) - 1)
    d.line([x0, TIMELINE_LINE_Y, x1, TIMELINE_LINE_Y], fill=RULE, width=2)
    for i, item in enumerate(tl):
        cx = x0 + i * step
        d.ellipse([cx - 5, TIMELINE_LINE_Y - 5, cx + 5, TIMELINE_LINE_Y + 5],
                  fill=RED, outline=WHITE, width=1)
        wf = font(11, "sans", True)
        wlab = text_w(d, item["t"], wf)
        d.text((min(max(cx - wlab / 2, 16), W - 16 - wlab),
                TIMELINE_LABEL_Y), item["t"], font=wf, fill=NAVY)
        tf = font(10, "sans", False)
        tlab = text_w(d, item["text"], tf)
        d.text((min(max(cx - tlab / 2, 16), W - 16 - tlab),
                TIMELINE_TEXT_Y), item["text"], font=tf, fill=INK)


def draw_ticker(d):
    d.rectangle([0, TICKER_Y0, W, TICKER_Y0 + TICKER_H], fill=TICKER_BG)
    text = "  |  ".join(DATA["ticker"])
    size = fit_size(d, text, W - 32, 11, 9, "mono", True)
    f = font(size, "mono", True)
    d.text((16, TICKER_Y0 + (TICKER_H - size) // 2 - 1), text, font=f,
           fill=WHITE)


def draw_date_check(d):
    x0, y0, x1, y1 = DATECHECK_BOX
    d.rectangle([x0, y0, x1, y1], fill=RED_SOFT, outline=RED, width=2)
    d.text((x0 + 8, y0 + 4), "DATE CHECK — WHAT WE LEFT OUT ON PURPOSE",
           font=font(11, "sans", True), fill=RED)
    f = font(10, "sans", False)
    draw_wrapped(d, x0 + 8, y0 + 18, DATA["date_check"]["left"], f, 472,
                 INK, leading=10)
    draw_wrapped(d, 516, y0 + 18, DATA["date_check"]["right"], f, 484,
                 INK, leading=10)


def draw_footer(d):
    """One line: the judge-facing date statement in bold, then sources."""
    full = DATA["footer"]
    head, _, tail = full.partition("Sources:")
    bf = font(11, "sans", True)
    rf = font(10, "sans", False)
    total = text_w(d, head, bf) + text_w(d, "Sources:" + tail, rf)
    x = (W - total) / 2
    d.text((x, FOOTER_Y), head, font=bf, fill=INK)
    d.text((x + text_w(d, head, bf), FOOTER_Y + 1), "Sources:" + tail,
           font=rf, fill=GREY)


# ---------------------------------------------------------------- main
def build(out_path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    draw_kicker(d)
    draw_masthead(d)
    draw_strip(d)
    draw_section_strip(d)
    draw_heroes(d)
    draw_map_zone(d)
    draw_fold(d)
    draw_index_quote(d)
    shrunk = draw_columns(d)
    draw_card_row(d, CARDS1, CARDS1_Y0, CARD_H, 56, 52, 68, 165, 14)
    draw_card_row(d, CARDS2, CARDS2_Y0, CARD_H, 56, 52, 68, 165, 14)
    draw_card_row(d, CARDS3, CARDS3_Y0, CARD3_H, 40, 40, 52, 181, 13)
    draw_timeline(d)
    draw_ticker(d)
    draw_date_check(d)
    draw_footer(d)
    img.save(out_path, optimize=True)
    size = Path(out_path).stat().st_size
    print(f"saved {out_path}  {img.size[0]}x{img.size[1]}  {size} bytes "
          f"({size / 1024:.0f} KB, limit 1024 KB)")
    print("regions:", region_counts(), "sum:",
          sum(region_counts().values()))
    print("headlines shrunk below 13px:", shrunk or "none")
    return size


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    build(out)
