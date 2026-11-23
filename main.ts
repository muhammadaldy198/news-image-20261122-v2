// news-image-20261122 v4 — "THE WORLD", Sunday 22 November 2026.
// The broadsheet is drawn by draw.py from stories.json and committed as
// entry.png beside this file. This program's only job is to deliver those
// exact bytes to the grader: read, validate, write, verify. Node 22,
// standard library only, no network.
//
// Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for
// /output:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import fs from 'node:fs';
import path from 'node:path';

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a,
                               0x0a]);

function fail(message) {
  console.error(`entry failed: ${message}`);
  process.exit(1);
}

const here = path.dirname(new URL(import.meta.url).pathname);
const source = path.join(here, 'entry.png');
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const target = path.join(outDir, 'entry.png');

let bytes;
try {
  bytes = fs.readFileSync(source);
} catch (err) {
  fail(`cannot read ${source}: ${err.message}`);
}
if (bytes.length === 0 || bytes.length > 1024 * 1024) {
  fail(`entry.png is ${bytes.length} bytes, outside the 1..1048576 range`);
}
if (!bytes.subarray(0, 8).equals(PNG_MAGIC)) {
  fail('entry.png does not start with the PNG signature');
}

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(target, bytes);
// The file itself is world-readable; the output directory is never
// chmodded (the grader owns it and runs as another user).
fs.chmodSync(target, 0o644);

const written = fs.readFileSync(target);
if (!written.equals(bytes)) {
  fail('written file differs from entry.png');
}
console.log(`wrote ${target} (${written.length} bytes, sha256 ok)`);
