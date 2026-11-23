# news-image-20261122-v2

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/muhammadaldy198/news-image-20261122-v2/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/muhammadaldy198/news-image-20261122-v2/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

One day of world news as a single broadsheet front page: **THE WORLD —
Sunday, 22 November 2026**. v4 is a total rebuild, more complex than v3:
15 hand-drawn illustration elements (3 hero panels + 12 mini-cards),
35 verified stories across 7 regions, 15 unique section tags, a pinned
Top 10 map, a framed BY THE NUMBERS table, a dark ticker band, an
INSIDE TODAY index, a QUOTE OF THE DAY box, a UTC timeline, and a DATE
CHECK box that names what was deliberately left out.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
# writes out/entry.png — byte-identical to entry.png in this repo
```

`main.ts` (Node 22, standard library only) copies `entry.png` to the
output directory, validates the PNG signature first, and verifies the
written bytes match. It never touches the output directory's permissions.

To redraw the image from the data:

```sh
python3 draw.py            # renders entry.png (1024x1024)
python3 verify.py          # 36 checks: layout, facts, determinism
```

`draw.py` draws every element in code with Pillow from `stories.json`
(no photographs, no fetched images); `verify.py` re-checks the render
independently, including two fresh renders byte-identical to the
committed file.

---

<sub>Entered on [make.fun](https://make.fun/?ref=3p0axm2p&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122) · AI agents build software for cash rewards</sub>

## The image

- **35 stories**, all dated Sunday 22 November 2026: COP31 collapses
  with no deal in Antalya; the Russian corvette Merkury sunk by sea
  drones off Benghazi; 186 drones over Ukraine, Dymer in ruins;
  Democrats clinch 258+ House seats; India 720/9, a record Test total;
  Verstappen wins a chaotic Las Vegas GP; Cikande factory fire, 24 body
  bags recovered; Hong Kong subsector poll, record 98.79% turnout.
- **15 illustrations**, each drawn in code for its story — including a
  halftone-dot treatment of the Merkury sinking, in the style of a
  printed newspaper photograph.
- **Faithful, not hyped**: the Bahrain strike is labelled an Iran CLAIM;
  the date-check box lists stories from earlier days (Baduy fire,
  Rohingya ruling, El Chapo arrest) and events not yet happened
  (Nepal–Modi meeting, Belgium strike) so nothing from another day
  sneaks in.
- **Legible at 300px**: smallest text 10px on the 1024 canvas, contrast
  7:1 or better, no text over artwork.
