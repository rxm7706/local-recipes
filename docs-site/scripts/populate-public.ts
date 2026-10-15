/**
 * docs-site/public/, written from scratch on every Astro build (Story 43.3, spec-pyforge-herald CAP-61): this script is
 * its only writer, run by `astro.config.mjs` at `astro:build:start` and runnable alone
 * (`node scripts/populate-public.ts`).
 *
 * With pyforge.herald.pages_one_generator on it holds, for Astro to serve as static files:
 * - each twin the herald pages frame, at `herald/twins/...`, with Story 31.3's font-link vendoring as its one change
 *   (AD-21; the ruling of 2026-10-15 on Story 43.2), the link naming the @fontsource faces at `/herald/fonts.css`
 *   (Story 43.4);
 * - each family download, byte for byte, at `herald/decks/<slug>/downloads/<name>`;
 * - every entry of the tracked `docs/dashboard/` tree but its `README.md`, byte for byte, at `dashboard/` -- the tree
 *   AD-21 gives `/dashboard/`, as the Jinja path's assembler copies it: steward's `deploy static` boards, and the two
 *   exports, `kedro-viz/` (Story 42.2) and `vizro/` (atlas Story 30.2), each mounted only when present (a non-empty
 *   directory), never failing the build when absent.
 * Off, it is empty: the Jinja path's assembler mounts and copies everything as before.
 *
 * Astro lets a `public/` file win over a route that emits the same path and only warns (`checkPublicConflict`), so
 * `src/lib/redirects.ts`'s `refusePublicCollisions` fails the build at `astro:build:done` instead, naming each path
 * (AD-21 rule 1).
 */

import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { HERALD_FONTS, vendorFontLinks } from '../src/lib/herald-pages.ts';
import { heraldPagesRoot, loadHeraldPages, pagesOneGenerator } from '../src/loaders/herald-pages-loader.ts';

/** The dashboard exports in `docs/dashboard/<name>/`, mounted at `/dashboard/<name>/` only when present. */
export const DASHBOARD_EXPORTS = ['kedro-viz', 'vizro'];

function isPresent(dir: string): boolean {
  return fs.existsSync(dir) && fs.statSync(dir).isDirectory() && fs.readdirSync(dir).length > 0;
}

/** Rewrite `publicDir` for this build; returns the files written, relative to it, in order. */
export function populatePublic(
  publicDir: string,
  enabled: boolean = pagesOneGenerator(),
  repoRoot: string = heraldPagesRoot(),
): string[] {
  fs.rmSync(publicDir, { recursive: true, force: true });
  if (!enabled) {
    return [];
  }
  const written: string[] = [];
  const put = (rel: string, data: string | Buffer): void => {
    const dest = path.join(publicDir, rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, data);
    written.push(rel);
  };
  const twin = (source: string, rel: string): void => {
    const fonts = `${'../'.repeat(rel.split('/').length - 1)}${HERALD_FONTS}`;
    put(`herald/${rel}`, vendorFontLinks(fs.readFileSync(path.join(repoRoot, source), 'utf8'), fonts));
  };

  const pages = loadHeraldPages();
  for (const ig of pages.infographics) {
    twin(ig.source, ig.twin);
  }
  for (const family of pages.families) {
    for (const view of family.views) {
      twin(view.source, view.twin);
    }
    for (const d of [...family.pptx, ...family.marp]) {
      put(`herald/decks/${family.slug}/downloads/${d.name}`, fs.readFileSync(path.join(repoRoot, d.source)));
    }
  }
  const dashboard = path.join(repoRoot, 'docs', 'dashboard');
  const entries = fs.existsSync(dashboard) ? fs.readdirSync(dashboard, { recursive: true, encoding: 'utf8' }) : [];
  for (const rel of entries.sort()) {
    const [top] = rel.split(path.sep);
    const skipped = top === 'README.md' || (DASHBOARD_EXPORTS.includes(top) && !isPresent(path.join(dashboard, top)));
    if (!skipped && fs.statSync(path.join(dashboard, rel)).isFile()) {
      put(`dashboard/${rel.split(path.sep).join('/')}`, fs.readFileSync(path.join(dashboard, rel)));
    }
  }
  return written;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const publicDir = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'public');
  const written = populatePublic(publicDir);
  console.log(`populate-public: ${written.length} file(s) under ${publicDir}`);
}
