/**
 * docs-site/public/, written from scratch on every Astro build (Story 43.3, spec-pyforge-herald CAP-61): this script is
 * its only writer, run by `astro.config.mjs` at `astro:build:start` and runnable alone
 * (`node scripts/populate-public.mts`). It holds, for Astro to serve as static files:
 * - each twin the herald pages frame, at `herald/twins/...`, with Story 31.3's font-link vendoring as its one change
 *   (AD-21; the ruling of 2026-10-15 on Story 43.2), the link naming the @fontsource faces at `/herald/fonts.css`
 *   (Story 43.4);
 * - each family download, byte for byte, at `herald/decks/<slug>/downloads/<name>`;
 * - every entry of the tracked `docs/dashboard/` tree but its `README.md`, byte for byte, at `dashboard/` -- the tree
 *   AD-21 gives `/dashboard/`: steward's `deploy static` boards, and the two exports, `kedro-viz/` (Story 42.2) and
 *   `vizro/` (atlas Story 30.2), each mounted only when it holds a file, never failing the build when absent;
 *   dot-entries (staging leftovers) never mount;
 * - the SIL Open Font License text of each @fontsource package the site's faces come from, from the package's own
 *   `LICENSE`, at `fonts/<package>.LICENSE.txt` (Story 43.7: the faces ship in the artifact, so their licence does);
 * - `favicon.svg`, the site's one icon -- `site.yml`'s `favicon`, the glyph the herald pages already show -- where
 *   Starlight links it on every docs page (Story 43.7: until then that link named a file no build wrote).
 *
 * Astro lets a `public/` file win over a route that emits the same path and only warns (`checkPublicConflict`), so
 * `src/lib/redirects.ts`'s `refusePublicCollisions` fails the build at `astro:build:done` instead, naming each path
 * (AD-21 rule 1).
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { HERALD_FONTS, vendorFontLinks } from '../src/lib/herald-pages.ts';
import { DASHBOARD_EXPORTS, holdsAFile } from '../src/lib/nav.ts';
import { heraldPagesRoot, loadHeraldPages } from '../src/loaders/herald-pages-loader.ts';

export { DASHBOARD_EXPORTS };

/** The @fontsource packages the site's faces come from (`src/styles/herald-fonts.css`), each OFL-1.1. */
export const FONT_PACKAGES = [
  '@fontsource/big-shoulders-display',
  '@fontsource/ibm-plex-sans',
  '@fontsource/ibm-plex-mono',
  '@fontsource/archivo',
  '@fontsource-variable/archivo',
];

/** Where a font package's licence is served, relative to the site root. */
export function fontLicensePath(pkg: string): string {
  return `fonts/${pkg.replace(/^@/, '').replace('/', '-')}.LICENSE.txt`;
}

/** Rewrite `publicDir` for this build; returns the files written, relative to it, in order. */
export function populatePublic(publicDir: string, repoRoot: string = heraldPagesRoot()): string[] {
  fs.rmSync(publicDir, { recursive: true, force: true });
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
    // the README and dot-entries (gitignored `.vizro-*` staging leftovers) never mount; an export, only with a file
    const skipped =
      top === 'README.md' ||
      top.startsWith('.') ||
      (DASHBOARD_EXPORTS.includes(top) && !holdsAFile(path.join(dashboard, top)));
    if (!skipped && fs.statSync(path.join(dashboard, rel)).isFile()) {
      put(`dashboard/${rel.split(path.sep).join('/')}`, fs.readFileSync(path.join(dashboard, rel)));
    }
  }
  const glyph = String(pages.site.favicon ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
  put('favicon.svg', `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">${glyph}</text></svg>\n`);
  const modules = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'node_modules');
  for (const pkg of FONT_PACKAGES) {
    put(fontLicensePath(pkg), fs.readFileSync(path.join(modules, pkg, 'LICENSE')));
  }
  return written;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const publicDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'public');
  const written = populatePublic(publicDir);
  console.log(`populate-public: ${written.length} file(s) under ${publicDir}`);
}
