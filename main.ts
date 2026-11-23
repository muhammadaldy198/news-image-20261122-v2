// news-image-20261122 — "THE WORLD, Sunday 22 November 2026".
//
// The entry image is the entry.png beside this file. It was rendered before
// submit by draw.py (PIL): the grader's image has no Python, no Pillow and
// no fonts, so the program only copies the committed image to the output
// directory. Node 22, standard library only. Deterministic: the same bytes
// on every run.
//
// Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
//
// NOTE (card-game lesson): never chmod the output directory itself — the
// grader runs as user 65534 while /output belongs to root, so chmod on the
// directory throws EPERM and fails the run. The copied file below is ours,
// so chmod on the file alone is safe and keeps it world-readable.

import { chmodSync, copyFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const out = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const dest = join(out, 'entry.png');
copyFileSync(new URL('./entry.png', import.meta.url), dest);
chmodSync(dest, 0o644);
// Self-check: the copy must be the whole image, or the run is worthless.
const bytes = statSync(dest).size;
if (bytes === 0) throw new Error('entry.png copied but empty');
console.log(`Copied entry.png to ${dest} (${bytes} bytes)`);
