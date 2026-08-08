#!/usr/bin/env node
// Story 8.4's scoped-down "data source" step: there is no live REST API
// (this is a static dashboard reading a local CLI-written snapshot, per
// docs/dreams/herald-moments-2-4-live-backend.md), so before `dev`/`build`
// this copies the operator's local `.herald/progress.json` (written by
// `herald progress <station> --update`, resolved against the cwd Herald's
// CLI itself was run from -- normally the repo root) into
// `web/public/progress.json`, which `ProgressPanel.jsx` fetches at runtime.
//
// Missing source file (no `--update` has been run yet) is not an error --
// it writes `[]` so the app still builds and renders its empty state.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, '..');
const publicDir = resolve(webRoot, 'public');
const destPath = resolve(publicDir, 'progress.json');

// Override with an explicit path (env var or first CLI arg) for a repo
// layout where the cwd running this script differs from the cwd `herald`
// itself was run from; default assumes both are the repo root.
const sourcePath =
  process.argv[2] || process.env.HERALD_PROGRESS_PATH || resolve(process.cwd(), '.herald', 'progress.json');

let contents = '[]\n';
if (existsSync(sourcePath)) {
  const raw = readFileSync(sourcePath, 'utf-8');
  JSON.parse(raw); // fail loud on a corrupt source rather than ship bad data
  contents = raw;
} else {
  console.warn(`sync-progress: ${sourcePath} not found -- writing an empty snapshot`);
}

mkdirSync(publicDir, { recursive: true });
writeFileSync(destPath, contents);
console.log(`sync-progress: wrote ${destPath}`);
