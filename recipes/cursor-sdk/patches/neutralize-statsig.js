#!/usr/bin/env node
// Replace the Statsig Network.js webpack module body with a no-op shim in
// every dist file. Severs all in-bundle Statsig network calls without changing
// the StatsigClient API surface; checkGate/getConfig calls fall through to
// their default-value paths.
//
// The webpack bundle uses object-literal method-shorthand registration with a
// string key:
//     "...Network.js"(e,t,n){body}
// We replace the (params){body} portion, keeping the key.
//
// Run during the conda build, after `npm install --global @cursor/sdk`,
// before any test step. Usage: node neutralize-statsig.js <dist-file> [...]

'use strict';

const fs = require('node:fs');

const NETWORK_KEY_RE =
  /"\.\.\/\.\.\/node_modules\/\.pnpm\/@statsig\+js-client@[^"]+\/node_modules\/@statsig\/js-client\/src\/Network\.js"/;

const STUB_BODY =
  '(e,t,n){"use strict";Object.defineProperty(e,"__esModule",{value:!0});class N{async post(){return{ok:false,error:"network-disabled-by-conda-recipe"};}async get(){return{ok:false,error:"network-disabled-by-conda-recipe"};}async beacon(){return false;}isBeaconSupported(){return false;}}e.Network=N;}';

function findBalancedEnd(src, start, openCh, closeCh) {
  // Walk from src[start] (which must equal openCh) until matched-close.
  // Skip string literals (single, double, backtick, with backslash-escape).
  let depth = 0;
  let i = start;
  while (i < src.length) {
    const c = src[i];
    if (c === '"' || c === "'" || c === '`') {
      const quote = c;
      i++;
      while (i < src.length && src[i] !== quote) {
        if (src[i] === '\\') i++;
        i++;
      }
    } else if (c === openCh) {
      depth++;
    } else if (c === closeCh) {
      depth--;
      if (depth === 0) return i + 1;
    }
    i++;
  }
  return -1;
}

let touched = 0;

for (const file of process.argv.slice(2)) {
  const src = fs.readFileSync(file, 'utf8');
  const keyMatch = src.match(NETWORK_KEY_RE);
  if (!keyMatch) {
    console.error(`[neutralize-statsig] No Statsig Network.js module found in ${file}; refusing to touch it.`);
    process.exit(2);
  }

  // After the closing quote of the key, walk past whitespace and find '('.
  let p = keyMatch.index + keyMatch[0].length;
  while (src[p] === ' ' || src[p] === ':' || src[p] === '\t' || src[p] === '\n') p++;
  if (src[p] !== '(') {
    console.error(`[neutralize-statsig] Expected '(' after Network.js key in ${file}; got ${JSON.stringify(src[p])}`);
    process.exit(2);
  }
  const replaceStart = p;
  // Find end of params
  const paramsEnd = findBalancedEnd(src, p, '(', ')');
  if (paramsEnd < 0) {
    console.error(`[neutralize-statsig] Unbalanced params in ${file}`);
    process.exit(2);
  }
  // Skip whitespace, expect '{'
  let q = paramsEnd;
  while (src[q] === ' ' || src[q] === '\n' || src[q] === '\t') q++;
  if (src[q] !== '{') {
    console.error(`[neutralize-statsig] Expected body '{' in ${file}; got ${JSON.stringify(src[q])}`);
    process.exit(2);
  }
  const bodyEnd = findBalancedEnd(src, q, '{', '}');
  if (bodyEnd < 0) {
    console.error(`[neutralize-statsig] Unbalanced body in ${file}`);
    process.exit(2);
  }
  const before = src.slice(0, replaceStart);
  const after = src.slice(bodyEnd);
  const patched = before + STUB_BODY + after;
  fs.writeFileSync(file, patched);
  touched++;
  console.log(
    `[neutralize-statsig] Patched ${file}: replaced ${bodyEnd - replaceStart} bytes -> ${STUB_BODY.length} bytes`
  );
}

if (touched === 0) {
  console.error('[neutralize-statsig] No files patched');
  process.exit(2);
}
