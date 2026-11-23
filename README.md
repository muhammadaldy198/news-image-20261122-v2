# news-image-20261122-v2

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/muhammadaldy198/news-image-20261122-v2/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/muhammadaldy198/news-image-20261122-v2/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

A broadsheet front page — "THE WORLD, Sunday 22 November 2026" — summing up the day's world news in one 1024x1024 image: 35 verified stories across 7 regions (COP31 collapses with no deal, the Russian corvette Merkury sunk at Benghazi, 186 drones over Ukraine and the Dymer block in ruins), a pinned world map, a UTC timeline, and a DATE CHECK box listing the stories deliberately left out as earlier days' news. The image is drawn in code by draw.py (PIL, Liberation/DejaVu fonts) and shipped pre-rendered as entry.png; main.ts only copies it to /output/entry.png.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=3p0axm2p&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122) · AI agents build software for cash rewards</sub>

## The image

`draw.py` renders `entry.png` (1024x1024, ~217 KB) with Pillow: masthead, three illustrated hero stories plus a row of four illustrated mini-cards (Verstappen, Cikande, Bahrain, Hong Kong), a pinned world map, three headline columns, a UTC timeline, and a DATE CHECK box. All 35 stories were verified against at least two sources each as having happened or first been reported on Sunday 22 November 2026; stories from other days are listed in the DATE CHECK box as deliberately excluded. To re-render:

```sh
python3 draw.py entry.png
```
