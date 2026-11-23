#!/usr/bin/env python3
"""draw.py — renderer for the news-image-20261122 entry (Hunter Office, Bima).

Renders a 1024x1024 broadsheet front page ("THE WORLD — Sunday, 22 November
2026") with PIL, from the verified 22 Nov 2026 story list (35 stories, 7
regions). The PNG is committed beside this script; main.ts only copies it.

Written from scratch in the builder's own session. No rival code was copied;
the layout follows the office research (Nadia's report + Dimas's autopsy):
masthead + number strip + region bar + 3 hero panels + world map with numbered
pins + 3 headline columns + UTC timeline + DATE CHECK box + footer.

Run:  ~/workspace/office/.venv/bin/python draw.py [out.png]
Fonts are render-time tools only (system Liberation/DejaVu); they are NOT
part of the entry. Output is deterministic: same bytes every run.

v2: +4 illustrated cards (Verstappen, Cikande, Bahrain, Hong Kong);
timeline wording fixed; quadcopter drones.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 236)      # warm newsprint
INK = (20, 20, 20)           # near-black text
NAVY = (27, 42, 74)          # masthead band / headers
NAVY_SOFT = (38, 58, 100)
RED = (185, 28, 28)          # breaking accent / date-check border
RED_SOFT = (252, 234, 234)   # date-check fill
RULE = (120, 110, 90)        # hairline rules
SEA = (216, 228, 238)        # map sea
LAND = (232, 222, 190)       # map land
LAND_EDGE = (168, 156, 118)
GREY = (90, 88, 82)          # secondary text
PANEL = (243, 238, 222)      # hero panel background
WHITE = (255, 255, 255)

# Region colours (muted, one per region) for the 2-letter chips.
REGION_COLOURS = {
    "EU": (46, 80, 140),     # Europe — blue
    "AS": (156, 84, 20),     # Asia — ochre
    "ME": (140, 40, 40),     # Middle East — brick
    "AM": (32, 110, 70),     # Americas — green
    "AF": (110, 70, 140),    # Africa — purple
    "OC": (20, 120, 130),    # Oceania — teal
    "WD": (70, 70, 70),      # World — grey
}
REGION_NAMES = {
    "EU": "EUROPE", "AS": "ASIA", "ME": "MIDDLE EAST", "AM": "AMERICAS",
    "AF": "AFRICA", "OC": "OCEANIA", "WD": "WORLD",
}

# ---------------------------------------------------------------- fonts
LIB = "/usr/share/fonts/truetype/liberation/"
DEJ = "/usr/share/fonts/truetype/dejavu/"
_font_cache = {}


def font(size, bold=False, serif=False):
    """Liberation first (Times/Arial-like, newspaper feel), DejaVu fallback."""
    key = (size, bold, serif)
    if key in _font_cache:
        return _font_cache[key]
    if serif:
        names = ["LiberationSerif-Bold.ttf" if bold else "LiberationSerif-Regular.ttf",
                 "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"]
    else:
        names = ["LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
                 "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for base in (LIB, DEJ):
        for name in names:
            p = Path(base) / name
            if p.exists():
                try:
                    f = ImageFont.truetype(str(p), size)
                    _font_cache[key] = f
                    return f
                except OSError:
                    continue
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


# ---------------------------------------------------------------- text helpers
def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def wrap(draw, text, f, max_w):
    """Greedy word wrap by pixel width. Returns list of lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if text_w(draw, trial, f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text, max_w, start, minimum, bold=False, serif=False):
    """Largest font size in [minimum, start] letting text fit one line."""
    size = start
    while size > minimum and text_w(draw, text, font(size, bold, serif)) > max_w:
        size -= 1
    return font(size, bold, serif)


def draw_wrapped(draw, x, y, text, f, max_w, fill, leading=None):
    """Draw wrapped text; returns total height used."""
    lines = wrap(draw, text, f, max_w)
    lh = leading or int(f.size * 1.22)
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=f, fill=fill)
    return len(lines) * lh


def centre(draw, y, text, f, fill, cx=W // 2):
    draw.text((cx - text_w(draw, text, f) / 2, y), text, font=f, fill=fill)


# ---------------------------------------------------------------- the 35 stories
# (number, headline, region code, short label for the map legend)
# Headlines are written short on purpose: they must fit one 330px column line.
STORIES = [
    # --- Top 10 (1-3 are the hero panels; all ten are pinned on the map) ---
    (1, "COP31 COLLAPSES — NO DEAL", "WD", "COP31 collapses"),
    (2, "MERKURY SUNK AT BENGHAZI", "AF", "Merkury sunk"),
    (3, "186 DRONES; DYMER IN RUINS", "EU", "186 drones, Dymer"),
    (4, "Democrats clinch 258+ House seats", "AM", "Democrats 258+ seats"),
    (5, "India 720/9 — record Test total in NZ", "OC", "India 720/9"),
    (6, "Verstappen wins chaotic Las Vegas GP", "AM", "Verstappen wins Vegas"),
    (7, "Marquez takes 8th MotoGP crown", "EU", "Marquez 8th title"),
    (8, "Iran claims US-base strikes in Bahrain", "ME", "Iran claims Bahrain hit"),
    (9, "'Jewish terrorism': Eisenkot on arson", "ME", "West Bank arson"),
    (10, "Cikande fire: 24 body bags recovered", "AS", "Cikande search"),
    # --- the next 25, in the three columns ---
    (11, "Hong Kong vote: record 98.79% turnout", "AS", "HK vote 98.79%"),
    (12, "Sparta II towed out of Finnish waters", "EU", "Sparta II towed"),
    (13, "Russia twice tried to kill Kyivstoner", "EU", "Kyivstoner plots"),
    (14, "China eases margin trading to 80%", "AS", "China eases margin"),
    (15, "US-China power gap narrowest ever", "AS", "Lowy: gap 5.3 pts"),
    (16, "S. Korea minister quits over AI cheating", "AS", "Korea minister quits"),
    (17, "Kh-101 debris found in Poland", "EU", "Kh-101 debris"),
    (18, "Gaza: 3 killed despite ceasefire", "ME", "Gaza: 3 killed"),
    (19, "Pugh swims 15 km across Hormuz", "ME", "Pugh swims Hormuz"),
    (20, "Germany tests kamikaze drones", "EU", "Germany drone tests"),
    (21, "Hormuz: tanker incident, power rationing", "ME", "Hormuz tension"),
    (22, "Eisenkot invites Likud to coalition talks", "ME", "Eisenkot-Likud talks"),
    (23, "Iran shows underground 'missile city'", "ME", "Iran 'missile city'"),
    (24, "Spain poll: PP ahead before Nov 29 vote", "EU", "Spain: PP ahead"),
    (25, "Suffolk village votes to 'leave England'", "EU", "Suffolk secession vote"),
    (26, "Turkey seeks freeze on 108 traders", "AS", "Turkey freezes traders"),
    (27, "French ministry hit by leak probe", "EU", "France leak probe"),
    (28, "Taiwan warns Canada over China trade", "AS", "Taiwan warns Canada"),
    (29, "US probes Nvidia chips reaching China", "AS", "Nvidia chip probe"),
    (30, "NYT: China spies chase AI chips", "AS", "China chases AI chips"),
    (31, "China memory-chip makers advance", "AS", "CXMT, YMTC advance"),
    (32, "India youth protest at Meta offices", "AS", "India youth vs Meta"),
    (33, "Whale 'Timmy' starved in the Baltic", "EU", "Whale Timmy starved"),
    (34, "Morocco opens surrealist sculpture park", "AF", "Ramakech opens"),
    (35, "Madeira survey: ocean protection works", "EU", "Madeira survey"),
]

HEROES = [
    {
        "num": 1,
        "kicker": "CLIMATE — ANTALYA",
        "headline": "COP31 COLLAPSES — NO DEAL",
        "caption": ("Two weeks of talks end with no pact; the draft never "
                    "mentions fossil fuels. 'Deeply disappointing' — Guterres."),
    },
    {
        "num": 2,
        "kicker": "AFRICA — BENGHAZI",
        "headline": "MERKURY SUNK AT BENGHAZI",
        "caption": ("Russian corvette hit by sea drones, capsizes in Libya. "
                    "Six launched, two struck; satellites confirm the wreck."),
    },
    {
        "num": 3,
        "kicker": "EUROPE — KYIV REGION",
        "headline": "186 DRONES; DYMER IN RUINS",
        "caption": ("161 downed overnight; a 5-storey block collapses at "
                    "~05:00. At least 4 dead across the Kyiv region."),
    },
]

NUMBERS = [
    ("186", "drones launched\nat Ukraine"),
    ("161", "drones downed\nor jammed"),
    ("720/9", "India's record\nTest total"),
    ("258+", "Democrat House\nseats, most since '92"),
    ("98.79%", "Hong Kong\nturnout, a record"),
    ("0", "fossil-fuel words\nin the COP31 draft"),
]

# UTC timeline: (label, text) — only times the research actually sources.
TIMELINE = [
    ("04:31", "Pugh's Hormuz swim reported"),
    ("~05:00", "Dymer block hit"),
    ("~05:00", "Verstappen wins in Vegas"),
    ("11:00", "Cikande search paused"),
    ("AFTERNOON", "Sparta II towed out"),
    ("SUNDAY", "COP31 collapses"),
]

# Map pins for the Top 10: (number, lon, lat, label).
PINS = [
    (1, 30.7, 36.9, "ANTALYA"),
    (2, 20.1, 32.1, "BENGHAZI"),
    (3, 30.2, 50.9, "DYMER"),
    (4, -77.0, 38.9, "WASHINGTON"),
    (5, 174.8, -41.3, "WELLINGTON"),
    (6, -115.1, 36.2, "LAS VEGAS"),
    (7, -8.5, 37.1, "PORTUGAL"),
    (8, 50.6, 26.2, "BAHRAIN"),
    (9, 35.2, 31.9, "WEST BANK"),
    (10, 106.3, -6.2, "CIKANDE"),
]

# Coarse continent outlines (lon, lat) for the schematic map.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 72), (-85, 70),
     (-80, 73), (-65, 62), (-55, 52), (-60, 46), (-70, 42), (-75, 35),
     (-80, 32), (-81, 25), (-90, 21), (-97, 26), (-105, 22), (-110, 23),
     (-114, 29), (-120, 34), (-124, 42), (-124, 48), (-135, 57), (-150, 61),
     (-165, 60)],
    # South America
    [(-79, 9), (-72, 12), (-60, 8), (-50, 4), (-44, -3), (-35, -8),
     (-39, -17), (-48, -27), (-57, -38), (-65, -45), (-69, -52), (-73, -53),
     (-73, -44), (-73, -37), (-70, -30), (-70, -20), (-75, -15), (-77, -8),
     (-80, -3)],
    # Africa
    [(-17, 15), (-16, 21), (-10, 31), (-6, 35), (3, 37), (10, 37), (20, 32),
     (30, 31), (35, 28), (35, 18), (40, 15), (43, 12), (48, 11), (51, 10),
     (44, 0), (40, -10), (35, -20), (32, -29), (28, -33), (20, -35),
     (17, -29), (14, -22), (12, -12), (13, -2), (9, 4), (-8, 4), (-13, 8)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (28, 60), (32, 70), (45, 68), (60, 69), (75, 72),
     (90, 75), (105, 77), (120, 73), (135, 72), (150, 70), (165, 69),
     (178, 65), (178, 62), (165, 60), (158, 52), (150, 59), (142, 50),
     (140, 40), (135, 35), (128, 38), (122, 37), (120, 32), (121, 28),
     (114, 23), (109, 20), (107, 15), (105, 9), (103, 1), (100, 6), (98, 12),
     (94, 17), (91, 22), (88, 22), (86, 20), (80, 15), (77, 8), (74, 13),
     (72, 20), (67, 23), (64, 25), (58, 26), (54, 27), (51, 28), (48, 30),
     (43, 12), (39, 21), (35, 28), (36, 36), (30, 36), (27, 37), (23, 36),
     (19, 40), (16, 38), (12, 44), (8, 44), (3, 43), (-2, 37), (-6, 36),
     (-9, 37)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 52), (1, 51)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (140, 36), (141, 39), (141, 43),
     (144, 44), (142, 42), (140, 38), (139, 35), (135, 34), (132, 33)],
    # Australia
    [(114, -22), (114, -28), (115, -33), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (147, -39),
     (150, -37), (153, -30), (153, -27), (151, -24), (146, -19), (142, -15),
     (142, -11), (137, -12), (135, -15), (132, -12), (130, -13), (126, -14),
     (122, -17), (118, -20)],
    # New Zealand
    [(167, -45), (169, -43), (172, -41), (174, -39), (176, -38), (178, -38),
     (176, -40), (174, -41), (172, -43), (170, -44)],
    # Indonesia (rough)
    [(95, 5), (100, 0), (105, -5), (110, -7), (114, -8), (118, -9),
     (122, -10), (128, -8), (132, -4), (136, -2), (140, -3), (141, -1),
     (136, 0), (130, 0), (125, 1), (120, 0), (115, 1), (110, 2), (105, 3),
     (100, 5)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (49, -20), (47, -25), (45, -25),
     (44, -20)],
    # Greenland
    [(-45, 60), (-40, 64), (-32, 68), (-22, 70), (-20, 76), (-30, 78),
     (-45, 77), (-55, 75), (-58, 70), (-55, 64)],
]


def region_counts():
    counts = {}
    for _, _, code, _ in STORIES:
        counts[code] = counts.get(code, 0) + 1
    return counts


# ---------------------------------------------------------------- sections
def draw_kicker(draw):
    draw.rectangle([0, 0, W, 20], fill=NAVY)
    f = font(12, bold=True)
    centre(draw, 3, "THE WORLD IN ONE DAY  —  35 STORIES  ·  7 REGIONS  ·  "
                    "EVERY ONE DATED SUNDAY 22 NOVEMBER 2026", f, WHITE)


def draw_masthead(draw):
    draw.line([16, 106, W - 16, 106], fill=INK, width=2)
    draw.line([16, 109, W - 16, 109], fill=INK, width=1)
    centre(draw, 22, "THE WORLD", font(54, bold=True, serif=True), INK)
    centre(draw, 80, "SUNDAY, 22 NOVEMBER 2026",
           font(24, bold=True, serif=True), RED)


def draw_numbers(draw):
    cell = (W - 32) // 6
    for i, (num, label) in enumerate(NUMBERS):
        cx = 16 + cell * i + cell // 2
        fnum = font(24, bold=True, serif=True)
        draw.text((cx - text_w(draw, num, fnum) / 2, 112), num,
                  font=fnum, fill=NAVY)
        flab = font(10)
        for j, line in enumerate(label.split("\n")):
            draw.text((cx - text_w(draw, line, flab) / 2, 138 + j * 11),
                      line, font=flab, fill=GREY)
        if i:
            draw.line([16 + cell * i, 114, 16 + cell * i, 152],
                      fill=(210, 200, 175), width=1)
    draw.line([16, 160, W - 16, 160], fill=RULE, width=1)


def draw_region_bar(draw):
    counts = region_counts()
    assert sum(counts.values()) == 35, counts
    parts = []
    for code in ("EU", "AS", "ME", "AM", "AF", "OC", "WD"):
        parts.append(f"{REGION_NAMES[code]} {counts.get(code, 0)}")
    centre(draw, 164, "  ·  ".join(parts), font(13, bold=True), INK)
    draw.line([16, 182, W - 16, 182], fill=INK, width=2)


# ------------------------------------------------------------- hero art
def paint_cop31(draw, x, y, w, h):
    """Globe over an empty table; the pact document crossed out in red."""
    draw.rectangle([x, y, x + w, y + h], fill=(221, 232, 240))
    # globe
    gx, gy, r = x + w // 2 - 30, y + 54, 38
    draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(168, 200, 220),
                 outline=NAVY, width=2)
    draw.ellipse([gx - r // 2, gy - r, gx + r // 2, gy + r], outline=NAVY)
    draw.line([gx - r, gy, gx + r, gy], fill=NAVY, width=1)
    draw.ellipse([gx - 26, gy - 22, gx - 4, gy + 2], fill=(110, 160, 110))
    draw.ellipse([gx + 2, gy + 6, gx + 26, gy + 28], fill=(110, 160, 110))
    # table + chairs
    draw.ellipse([x + 20, y + h - 42, x + w - 20, y + h - 22], fill=(120, 90, 60))
    draw.rectangle([x + 34, y + h - 24, x + 44, y + h - 6], fill=(90, 65, 40))
    draw.rectangle([x + w - 44, y + h - 24, x + w - 34, y + h - 6],
                   fill=(90, 65, 40))
    # document with red X
    dx, dy = x + w // 2 - 34, y + h - 66
    draw.rectangle([dx, dy, dx + 68, dy + 30], fill=WHITE, outline=INK)
    for k in range(3):
        draw.line([dx + 8, dy + 8 + k * 8, dx + 60, dy + 8 + k * 8],
                  fill=(170, 170, 170), width=2)
    draw.line([dx - 4, dy - 4, dx + 72, dy + 34], fill=RED, width=4)
    draw.line([dx + 72, dy - 4, dx - 4, dy + 34], fill=RED, width=4)
    # NO DEAL stamp
    sx, sy = x + w - 108, y + 8
    draw.rectangle([sx, sy, sx + 98, sy + 26], outline=RED, width=3)
    draw.text((sx + 8, sy + 4), "NO DEAL", font=font(16, bold=True), fill=RED)


def paint_merkury(draw, x, y, w, h):
    """Capsized corvette: keel up, flames, smoke over a dark sea."""
    draw.rectangle([x, y, x + w, y + h], fill=(168, 200, 220))
    draw.rectangle([x, y + h - 52, x + w, y + h], fill=(52, 96, 140))
    for wx in range(x + 8, x + w - 8, 34):
        draw.arc([wx, y + h - 40, wx + 26, y + h - 22], 180, 360,
                 fill=WHITE, width=2)
    # smoke
    for cx, cy, r in ((x + 150, y + 18, 16), (x + 172, y + 8, 20),
                      (x + 196, y + 18, 14)):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(140, 140, 140))
    # flames
    for fx, fh, col in ((150, 38, (240, 120, 20)), (170, 44, (250, 180, 30)),
                        (190, 34, (240, 120, 20))):
        draw.polygon([(x + fx - 12, y + h - 52), (x + fx, y + h - 52 - fh),
                      (x + fx + 12, y + h - 52)], fill=col)
    # capsized hull: deck line at top, superstructure hanging below it
    hx, hy = x + 60, y + h - 78
    draw.polygon([(hx, hy), (hx + 200, hy), (hx + 178, hy + 26),
                  (hx + 22, hy + 26)], fill=(48, 52, 58))
    draw.rectangle([hx + 40, hy + 26, hx + 70, hy + 44], fill=(48, 52, 58))
    draw.rectangle([hx + 130, hy + 26, hx + 160, hy + 44], fill=(48, 52, 58))
    draw.line([hx + 100, hy, hx + 100, hy - 22], fill=(48, 52, 58), width=4)
    draw.text((x + 8, y + h - 18), "BENGHAZI, LIBYA",
              font=font(11, bold=True), fill=WHITE)


def paint_dymer(draw, x, y, w, h):
    """Apartment block with a collapsed section; drones cross the sky."""
    draw.rectangle([x, y, x + w, y + h], fill=(232, 228, 216))
    # drones: quadcopter silhouettes, kept right of the top-left caption
    for dx, dy in ((170, 12), (250, 10), (210, 32)):
        cx, cy = x + dx, y + dy
        # 4 arms out to the rotors
        for ax, ay in ((-9, -5), (9, -5), (-9, 5), (9, 5)):
            draw.line([cx, cy, cx + ax, cy + ay], fill=INK, width=1)
        # 4 rotors (horizontal ellipses) at the arm ends
        for ax, ay in ((-9, -5), (9, -5), (-9, 5), (9, 5)):
            draw.ellipse([cx + ax - 5, cy + ay - 1, cx + ax + 5, cy + ay + 1],
                         fill=(70, 70, 70))
        # body + 2 legs
        draw.rounded_rectangle([cx - 5, cy - 2, cx + 5, cy + 3], radius=2,
                               fill=INK)
        draw.line([cx - 3, cy + 3, cx - 3, cy + 6], fill=INK, width=1)
        draw.line([cx + 3, cy + 3, cx + 3, cy + 6], fill=INK, width=1)
    # buildings
    for bx, bw, bh in ((18, 70, 74), (228, 76, 96)):
        draw.rectangle([x + bx, y + h - bh, x + bx + bw, y + h],
                       fill=(90, 100, 116))
        for wy in range(y + h - bh + 10, y + h - 8, 16):
            for wx in range(x + bx + 8, x + bx + bw - 8, 16):
                draw.rectangle([wx, wy, wx + 7, wy + 9], fill=(250, 220, 120))
    # broken middle block: jagged top, rubble at the base
    mx = x + 100
    draw.polygon([(mx, y + h), (mx, y + 62), (mx + 24, y + 44),
                  (mx + 40, y + 58), (mx + 64, y + 40), (mx + 88, y + 56),
                  (mx + 112, y + 46), (mx + 116, y + h)],
                 fill=(70, 76, 88))
    for wy in range(y + 66, y + h - 8, 16):
        for wx in range(mx + 8, mx + 108, 16):
            draw.rectangle([wx, wy, wx + 7, wy + 9], fill=(250, 220, 120))
    draw.polygon([(mx - 6, y + h), (mx + 30, y + h - 26), (mx + 62, y + h)],
                 fill=(150, 145, 130))
    draw.polygon([(mx + 58, y + h), (mx + 92, y + h - 20), (mx + 122, y + h)],
                 fill=(170, 164, 148))
    draw.text((x + 8, y + 8), "DYMER, KYIV REGION",
              font=font(11, bold=True), fill=INK)

PAINTERS = {1: paint_cop31, 2: paint_merkury, 3: paint_dymer}


# ------------------------------------------------------- illustrated cards (v2)
def paint_verstappen(draw, x, y, w, h):
    """Night race in Las Vegas: F1 car, chequered flag, speed lines."""
    draw.rectangle([x, y, x + w, y + h], fill=(28, 32, 56))
    draw.rectangle([x, y + h - 18, x + w, y + h], fill=(50, 50, 56))
    # speed lines
    for ly, lx in ((8, 10), (14, 14), (20, 10)):
        draw.line([x + 2, y + ly, x + lx, y + ly], fill=WHITE, width=1)
    # chequered flag, top right (3x2)
    for r in range(2):
        for c in range(3):
            fill = WHITE if (r + c) % 2 == 0 else INK
            draw.rectangle([x + 38 + c * 4, y + 4 + r * 4,
                            x + 42 + c * 4, y + 8 + r * 4], fill=fill)
    draw.line([x + 38, y + 4, x + 38, y + 16], fill=WHITE, width=1)
    # F1 car silhouette
    draw.polygon([(x + 4, y + 36), (x + 10, y + 30), (x + 26, y + 28),
                  (x + 42, y + 30), (x + 50, y + 34), (x + 50, y + 38),
                  (x + 4, y + 38)], fill=(20, 60, 160))
    draw.rectangle([x + 44, y + 24, x + 52, y + 28], fill=(20, 60, 160))
    draw.ellipse([x + 26, y + 24, x + 32, y + 30], fill=(250, 200, 40))
    draw.ellipse([x + 10, y + 36, x + 18, y + 44], fill=INK)
    draw.ellipse([x + 34, y + 36, x + 42, y + 44], fill=INK)


def paint_cikande(draw, x, y, w, h):
    """Factory at dusk, smoke, fire-lit windows, a searchlight beam.
    Respectful: no body bags drawn."""
    draw.rectangle([x, y, x + w, y + h], fill=(232, 220, 200))
    # searchlight beam from top right
    draw.polygon([(x + 50, y), (x + w, y), (x + 38, y + 34),
                  (x + 30, y + 34)], fill=(250, 238, 170))
    # factory + chimney
    draw.rectangle([x + 6, y + 30, x + 38, y + h], fill=(120, 110, 95))
    draw.rectangle([x + 38, y + 18, x + 44, y + h], fill=(100, 92, 78))
    # smoke puffs above the chimney
    for cx, cy, r in ((41, 10, 5), (46, 6, 4), (36, 6, 4)):
        draw.ellipse([x + cx - r, y + cy - r, x + cx + r, y + cy + r],
                     fill=(150, 150, 150))
    # fire-lit windows
    draw.rectangle([x + 12, y + 38, x + 20, y + 46], fill=(240, 120, 20))
    draw.rectangle([x + 26, y + 38, x + 32, y + 46], fill=(240, 120, 20))


def paint_bahrain(draw, x, y, w, h):
    """Radar dish under a night sky; missile streaks; CLAIM tag."""
    draw.rectangle([x, y, x + w, y + h], fill=(24, 48, 60))
    # radar dish + mast
    draw.polygon([(x + 8, y + 30), (x + 14, y + 18), (x + 28, y + 18),
                  (x + 24, y + 30)], fill=WHITE)
    draw.line([x + 18, y + 30, x + 18, y + 48], fill=WHITE, width=2)
    draw.rectangle([x + 12, y + 48, x + 24, y + 52], fill=WHITE)
    # missile streaks
    draw.line([x + 30, y + 8, x + 52, y + 30], fill=(240, 120, 20), width=3)
    draw.line([x + 36, y + 4, x + 50, y + 18], fill=(250, 180, 30), width=2)
    draw.ellipse([x + 48, y + 26, x + 54, y + 32], fill=(250, 180, 30))
    # CLAIM tag, top left — the claim framing must be visible
    draw.rectangle([x + 2, y + 2, x + 36, y + 13], fill=RED)
    draw.text((x + 4, y + 2), "CLAIM", font=font(9, bold=True), fill=WHITE)


def paint_hongkong(draw, x, y, w, h):
    """Ballot box under the turnout number; city silhouettes below."""
    draw.rectangle([x, y, x + w, y + h], fill=(240, 235, 220))
    draw.text((x + 4, y + 4), "98.79%", font=font(13, bold=True), fill=NAVY)
    # city silhouettes
    draw.rectangle([x + 2, y + 44, x + 14, y + h], fill=(180, 175, 160))
    draw.rectangle([x + 42, y + 40, x + w - 2, y + h], fill=(180, 175, 160))
    # ballot paper going in
    draw.rectangle([x + 26, y + 20, x + 30, y + 28], fill=WHITE,
                   outline=GREY)
    # ballot box + navy slot
    draw.rectangle([x + 14, y + 26, x + 42, y + 50], fill=WHITE,
                   outline=NAVY)
    draw.rectangle([x + 22, y + 28, x + 34, y + 32], fill=NAVY)
    # small red check
    draw.line([x + 46, y + 46, x + 49, y + 49], fill=RED, width=2)
    draw.line([x + 49, y + 49, x + 54, y + 42], fill=RED, width=2)


CARDS = [
    (paint_verstappen, "Verstappen wins chaotic Las Vegas GP",
     "35 lead changes; beats Norris by 0.639s."),
    (paint_cikande, "Cikande fire: 24 body bags recovered",
     "3 confirmed dead; dozens still missing."),
    (paint_bahrain, "Iran claims US-base strikes in Bahrain",
     "Claim unconfirmed; civilian site hit, 2 hurt."),
    (paint_hongkong, "Hong Kong vote: record 98.79% turnout",
     "Subsector poll, not a general election."),
]


def draw_cards(draw, y0=814):
    """One row of 4 illustrated mini-cards (v2)."""
    cw, gap, ch = 239, 12, 68
    for i, (painter, headline, caption) in enumerate(CARDS):
        x = 16 + i * (cw + gap)
        draw.rectangle([x, y0, x + cw, y0 + ch], fill=PANEL, outline=RULE)
        painter(draw, x + 6, y0 + 6, 56, 56)
        tx, tw = x + 68, 165
        hl = wrap(draw, headline, font(12, bold=True), tw)[:2]
        for j, line in enumerate(hl):
            draw.text((tx, y0 + 6 + j * 14), line, font=font(12, bold=True),
                      fill=INK)
        cap = wrap(draw, caption, font(10), tw)[:2]
        cy = y0 + 6 + len(hl) * 14 + 2
        for j, line in enumerate(cap):
            draw.text((tx, cy + j * 12), line, font=font(10), fill=GREY)


def draw_heroes(draw):
    pw, gap = 322, 12
    y0, ph = 186, 218
    for i, hero in enumerate(HEROES):
        x = 16 + i * (pw + gap)
        draw.rectangle([x, y0, x + pw, y0 + ph], fill=PANEL, outline=RULE)
        # number badge
        bx, by = x + 10, y0 + 8
        draw.ellipse([bx, by, bx + 22, by + 22], fill=NAVY)
        num = str(hero["num"])
        nf = font(13, bold=True)
        draw.text((bx + 11 - text_w(draw, num, nf) / 2, by + 3), num,
                  font=nf, fill=WHITE)
        draw.text((bx + 30, by + 4), hero["kicker"], font=font(11, bold=True),
                  fill=RED)
        PAINTERS[hero["num"]](draw, x + 8, y0 + 34, pw - 16, 96)
        hl = wrap(draw, hero["headline"], font(19, bold=True, serif=True),
                  pw - 20)
        hy = y0 + 136
        for j, line in enumerate(hl[:2]):
            draw.text((x + 10, hy + j * 22), line,
                      font=font(19, bold=True, serif=True), fill=INK)
        draw_wrapped(draw, x + 10, hy + len(hl[:2]) * 22 + 4, hero["caption"],
                     font(12), pw - 20, GREY, leading=15)


# ---------------------------------------------------------------- map zone
def draw_map_zone(draw):
    draw.text((16, 410), "WHERE IT HAPPENED — THE TOP 10, PINNED",
              font=font(13, bold=True), fill=NAVY)
    # --- legend (left) ---
    lx, ly = 16, 432
    draw.text((lx, ly), "TOP 10", font=font(12, bold=True), fill=RED)
    for num, _, _, label in STORIES[:10]:
        yy = ly + 20 + (num - 1) * 11
        draw.text((lx, yy), f"{num}.", font=font(11, bold=True), fill=NAVY)
        draw.text((lx + 20, yy), label, font=font(11), fill=INK)
    # --- map (centre): drawn on its own layer so polygons clip cleanly ---
    mx, my, mw, mh = 290, 432, 444, 112
    layer = Image.new("RGB", (mw, mh), SEA)
    md = ImageDraw.Draw(layer)
    lon0, lon1, lat0, lat1 = -180.0, 180.0, 72.0, -50.0

    def proj(lon, lat):
        px = (lon - lon0) / (lon1 - lon0) * mw
        py = (lat0 - lat) / (lat0 - lat1) * mh
        return (px, py)

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        md.polygon(pts, fill=LAND, outline=LAND_EDGE)
    # graticule
    for lon in range(-150, 181, 30):
        gx = (lon - lon0) / (lon1 - lon0) * mw
        md.line([gx, 0, gx, mh], fill=(200, 214, 226), width=1)
    # Label offsets per pin. Only isolated pins get a text label: the
    # Europe/Middle East cluster is too dense, so those stories are named
    # by number in the TOP 10 legend beside the map instead.
    label_off = {4: (-78, 8), 5: (-72, -6), 6: (-68, -16), 10: (12, 4)}
    # Small cartographic nudges so pin circles in the cluster don't overlap.
    pin_nudge = {2: (-10, 6), 3: (-8, -6), 8: (14, -2), 9: (10, 8)}
    for num, lon, lat, label in PINS:
        px, py = proj(lon, lat)
        dx, dy = pin_nudge.get(num, (0, 0))
        px, py = px + dx, py + dy
        r = 9
        md.ellipse([px - r, py - r, px + r, py + r], fill=NAVY,
                   outline=WHITE, width=2)
        nf = font(11, bold=True)
        s = str(num)
        md.text((px - text_w(md, s, nf) / 2, py - 7), s, font=nf, fill=WHITE)
        if num in label_off:
            dx, dy = label_off[num]
            md.text((px + dx, py + dy), label, font=font(10, bold=True),
                    fill=NAVY)
    img = draw._image
    img.paste(layer, (mx, my))
    draw.rectangle([mx, my, mx + mw, my + mh], outline=RULE)
    # --- by the numbers (right) ---
    rx = 744
    draw.text((rx, ly), "BY THE NUMBERS", font=font(12, bold=True), fill=RED)
    extra = [
        ("2,700", "drones Russia fired in a week"),
        ("352", "overtakes in the Las Vegas GP"),
        ("35", "lead changes in that race"),
        ("102", "points Marquez clawed back"),
        ("6", "sea drones launched at Merkury"),
        ("5", "storeys of the Dymer block"),
    ]
    for i, (num, label) in enumerate(extra):
        yy = ly + 20 + i * 18
        draw.text((rx, yy), num, font=font(14, bold=True, serif=True),
                  fill=NAVY)
        draw.text((rx + 52, yy + 2), label, font=font(10), fill=INK)


# ---------------------------------------------------------------- columns
def draw_columns(draw):
    draw.text((16, 568), "THE DAY IN BRIEF", font=font(14, bold=True),
              fill=NAVY)
    draw.line([16, 586, W - 16, 586], fill=INK, width=1)
    cols = [STORIES[3:14], STORIES[14:25], STORIES[25:36]]
    cw, gap = 322, 12
    shrunk = []
    for ci, col in enumerate(cols):
        x = 16 + ci * (cw + gap)
        for ri, (num, head, code, _) in enumerate(col):
            y = 592 + ri * 20
            draw.text((x, y), f"{num}.", font=font(13, bold=True), fill=RED)
            # region chip
            cx = x + 24
            draw.rounded_rectangle([cx, y + 1, cx + 26, y + 15], radius=3,
                                   fill=REGION_COLOURS[code])
            cf = font(10, bold=True)
            draw.text((cx + 13 - text_w(draw, code, cf) / 2, y + 2), code,
                      font=cf, fill=WHITE)
            # headline, auto-fit 14 -> 12
            hx, hw = cx + 32, cw - 56
            f = fit_font(draw, head, hw, 14, 12, bold=True)
            if f.size < 14:
                shrunk.append((num, f.size))
            draw.text((hx, y), head, font=f, fill=INK)
        if ci:
            draw.line([x - gap // 2 - 1, 592, x - gap // 2 - 1, 806],
                      fill=(215, 205, 180), width=1)
    return shrunk


# ---------------------------------------------------------------- timeline
def draw_timeline(draw):
    draw.line([16, 890, W - 16, 890], fill=INK, width=2)
    draw.text((16, 894), "THE DAY\nIN UTC", font=font(11, bold=True),
              fill=NAVY)
    x0, x1 = 170, 990
    step = (x1 - x0) / (len(TIMELINE) - 1)
    ly = 906
    draw.line([x0, ly, x1, ly], fill=RULE, width=2)
    for i, (when, text) in enumerate(TIMELINE):
        cx = x0 + i * step
        draw.ellipse([cx - 5, ly - 5, cx + 5, ly + 5], fill=RED,
                     outline=WHITE, width=1)
        wf = font(11, bold=True)
        wlab = text_w(draw, when, wf)
        draw.text((min(max(cx - wlab / 2, 16), W - 16 - wlab), 894), when,
                  font=wf, fill=NAVY)
        tf = font(10)
        line = text.replace("\n", " ")
        tlab = text_w(draw, line, tf)
        draw.text((min(max(cx - tlab / 2, 16), W - 16 - tlab), 912), line,
                  font=tf, fill=INK)


# ---------------------------------------------------------------- date check
def draw_date_check(draw):
    draw.rectangle([16, 928, W - 16, 984], fill=RED_SOFT, outline=RED,
                   width=2)
    draw.text((24, 932), "DATE CHECK — WHAT WE LEFT OUT ON PURPOSE",
              font=font(12, bold=True), fill=RED)
    f = font(10)
    left = ("LEFT OUT (earlier days): Baduy fire 19 Nov · Rohingya ruling "
            "19 Nov · El Chapo arrest 20 Nov · Peru quake 20 Nov · "
            "Shenzhen summit 19–20 Nov · Hormuz tankers 21 Nov · "
            "BepiColombo 21 Nov · EU–Indonesia CEPA 21 Nov · Basra blast "
            "21 Nov · Nigeria boat 20 Nov")
    draw_wrapped(draw, 24, 948, left, f, 472, INK, leading=11)
    right = ("NOT YET: Nepal PM–Modi (Mon 23) · Belgium air-traffic "
             "strike (Mon 23) · Shenzhou-24 (~25 Nov).  CORRECTED: 186 "
             "drones, not 400 · India 720/9, not 629/6 · COP31 collapsed "
             "— no deal · Bahrain is an Iran CLAIM, unconfirmed.")
    draw_wrapped(draw, 516, 948, right, f, 484, INK, leading=11)


# ---------------------------------------------------------------- footer
def draw_footer(draw):
    centre(draw, 988,
           "Every story above happened or was first reported on Sunday "
           "22 November 2026.", font(13, bold=True), INK)
    centre(draw, 1006,
           "Sources: Reuters · AP · CNN · UN News · AFP · BBC · Kyiv "
           "Independent · Formula1.com · MotoGP.com — Drawn in code; "
           "illustrations, not photographs.", font(10), GREY)


# ---------------------------------------------------------------- main
def build(out_path):
    assert len(STORIES) == 35, f"{len(STORIES)} stories, want 35"
    assert [n for n, _, _, _ in STORIES] == list(range(1, 36))
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_kicker(draw)
    draw_masthead(draw)
    draw_numbers(draw)
    draw_region_bar(draw)
    draw_heroes(draw)
    draw_map_zone(draw)
    shrunk = draw_columns(draw)
    draw_cards(draw)
    draw_timeline(draw)
    draw_date_check(draw)
    draw_footer(draw)
    img.save(out_path, optimize=True)
    size = Path(out_path).stat().st_size
    print(f"saved {out_path}  {img.size[0]}x{img.size[1]}  {size} bytes "
          f"({size / 1024:.0f} KB, limit 1024 KB)")
    print("regions:", region_counts(), "sum:",
          sum(region_counts().values()))
    print("headlines shrunk below 14px:", shrunk or "none")
    return size


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    build(out)
