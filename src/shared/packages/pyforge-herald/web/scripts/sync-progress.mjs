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

// Regression: the previous default resolved against `process.cwd()`, which
// is `web/` under this package's own documented workflow (`npm run
// dev`/`build` invoked from inside `web/`, per this package's README) --
// not the repo root `herald progress <station> --update` itself resolves
// `.herald/progress.json` against. Following the README exactly silently
// produced an empty snapshot on every build (only a console.warn, no
// failure), so the Progress tab always rendered "No progress recorded
// yet." even after real --update runs. Default now derives the repo root
// from this script's own fixed location
// (src/shared/packages/pyforge-herald/web/scripts/) rather than the
// caller's cwd -- still overridable via HERALD_PROGRESS_PATH or an
// explicit first CLI arg for a nonstandard layout.
const repoRoot = resolve(webRoot, '..', '..', '..', '..', '..');
const sourcePath =
  process.argv[2] ||
  process.env.HERALD_PROGRESS_PATH ||
  resolve(repoRoot, '.herald', 'progress.json');

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
