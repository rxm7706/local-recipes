/**
 * The herald overview, gallery and deck-family pages, read as data (Story 43.2, spec-pyforge-herald
 * CAP-61 on CAP-35, CAP-53 and CAP-55).
 *
 * The inputs are `site.yml`'s `infographics` include, exclude and override lists, each `presentations/<slug>/` export
 * set and each export's `<file>.stamp.json` sidecar; the rules are the ones the retired Jinja build applied
 * (`collect_infographics`, `collect_families`, `_artifact_stamp`; Story 43.2 held the two paths equal until Story 43.7
 * deleted the Jinja one). Node builtins only, and YAML is parsed by the caller (`src/loaders/herald-pages-loader.ts`):
 * the herald tests import this module with node's type stripping and no `node_modules`.
 *
 * One current version per export (CAP-53; AD-4 as amended 2026-09-28): `pyforge.herald.deck_versions`
 * is the writers' one definition of current. This module lists the one dated file per kind the tree
 * holds and never chooses a newest date; a kind holding more than one dated file is refused, naming
 * every file.
 */

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { builtFromHtml } from './built-from.ts';
import { holdsAFile } from './nav.ts';

/** Where each twin is served under the `/herald/` mount (`scripts/populate-public.mts`, Story 43.3). */
export const TWINS_DIR = 'twins';

/**
 * The herald faces at one fixed URL, `/herald/<HERALD_FONTS>` (`pages/herald/[sheet].css.ts`, Story 43.4), for the
 * pages Astro does not bundle a stylesheet into: each twin's one vendored line (`vendorFontLinks`) links it.
 */
export const HERALD_FONTS = 'fonts.css';

/**
 * The site theme -- Starlight's variables filled with the herald look, and the faces (`styles/theme.css`) -- at
 * `/herald/<HERALD_THEME>` (Story 43.4's review), for the reader pages, whose back-bar reads only those variables.
 */
export const HERALD_THEME = 'theme.css';

/** The preview frame's load handler (`components/herald/Shot.astro`), allowed by hash in the CSP below. */
export const PREVIEW_ONLOAD = "this.parentElement.classList.add('is-loaded')";

/**
 * The herald pages follow the docs header's theme toggle (Story 43.4 and its review): Starlight's toggle keeps its
 * choice under `starlight-theme` ('light', 'dark', or '' for auto) and sets `data-theme` on `<html>`, which
 * `styles/theme.css` keys the dark values to. This script, inline in each herald page's head so no page paints in the
 * other theme first, reads that key and resolves auto from the system scheme as Starlight's ThemeProvider does, then
 * again when the system scheme changes (as Starlight's ThemeSelect does) and when the page is shown from the
 * back-forward cache after a toggle elsewhere. No second toggle, no second store, no global name. Allowed by hash in
 * the CSP below.
 */
export const THEME_SCRIPT =
  "(()=>{const r=document.documentElement,m=matchMedia('(prefers-color-scheme: light)');" +
  "const s=()=>{try{return localStorage.getItem('starlight-theme')}catch(e){return null}};" +
  "const a=()=>{r.dataset.theme=(s()||(m.matches?'light':'dark'))==='light'?'light':'dark'};" +
  "a();m.addEventListener('change',a);addEventListener('pageshow',a)})()";

const sha256 = (text: string): string => `'sha256-${createHash('sha256').update(text).digest('base64')}'`;

/**
 * The site's one `Content-Security-Policy` (Story 43.3, AD-21; every page since Story 43.7): nothing loads from another
 * origin; `script-src` is `'self'` plus `scripts`, the inline scripts a page runs (by hash) and what else it needs.
 */
export function cspWith(scripts: string[]): string {
  return [
    "default-src 'self'",
    ['script-src', "'self'", ...scripts].join(' '),
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    "frame-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
}

/**
 * The CSP every herald layout and reader page writes itself: inline styles are the dossier's accents and the
 * back-bar's; the inline scripts are the preview handler and the theme script. Every Starlight page gets the same
 * policy with its own scripts at build end (`src/lib/artifact.ts`).
 */
export const HERALD_CSP = cspWith(["'unsafe-hashes'", sha256(PREVIEW_ONLOAD), sha256(THEME_SCRIPT)]);

const GOOGLE_FONT_LINK = /<link\b[^>]*\b(?:href|rel)=['"][^'"]*fonts\.(?:googleapis|gstatic)\.com[^'"]*['"][^>]*>\s*/gi;
const GOOGLE_FONT_IMPORT = /@import\s+url\(['"]?https:\/\/fonts\.googleapis\.com[^)]+\)\s*;?\s*/gi;

/**
 * A twin as the site serves it: Google Fonts links and imports dropped and one link to the site's own fonts added,
 * Story 31.3's `rewrite_google_font_links` -- the one transformation a twin gets (AD-21). Since Story 43.4 the link
 * names the @fontsource faces at `HERALD_FONTS`.
 */
export function vendorFontLinks(html: string, stylesheetHref: string): string {
  const out = html.replace(GOOGLE_FONT_LINK, '').replace(GOOGLE_FONT_IMPORT, '');
  if (out.includes(stylesheetHref)) {
    return out;
  }
  const link = `<link rel="stylesheet" href="${stylesheetHref}">\n`;
  const head = /<head[^>]*>/i.exec(out);
  if (!head) {
    return link + out;
  }
  const end = head.index + head[0].length;
  return `${out.slice(0, end)}\n${link}${out.slice(end)}`;
}

/**
 * A twin as `scripts/populate-public.mts` writes it at `/herald/<twin>`: the tracked `source` (relative to `repoRoot`)
 * with its font links vendored to `HERALD_FONTS` at the mount's root, climbing from the twin's own directory. Node
 * builtins only, so the herald tests judge every tracked twin without docs-site's `node_modules`.
 */
export function publishedTwin(repoRoot: string, source: string, twin: string): string {
  const fonts = `${'../'.repeat(twin.split('/').length - 1)}${HERALD_FONTS}`;
  return vendorFontLinks(fs.readFileSync(path.join(repoRoot, source), 'utf8'), fonts);
}

/** The family views' published names, as the retired Jinja build's `_FAMILY_VIEW_OUT_NAMES`. */
export const FAMILY_VIEWS = [
  { key: 'infographic_deck', suffix: ' - Infographic Deck.dc.html', label: 'Infographic Deck', outName: 'infographic-deck.html' },
  { key: 'executive_summary', suffix: ' - Executive Summary.dc.html', label: 'Executive Summary', outName: 'executive-summary.html' },
] as const;

export interface InfographicOverride {
  title?: string;
  description?: string;
  order?: number;
  slug?: string;
}

export interface SiteConfig {
  name: string;
  short_name?: string;
  eyebrow?: string;
  blurb?: string;
  favicon?: string;
  neighbours?: Array<Record<string, unknown>>;
  infographics: {
    include: string[];
    exclude?: string[] | null;
    overrides?: Record<string, InfographicOverride | null> | null;
    inject_backbar?: boolean;
  };
}

export interface Stamp {
  tree: string;
  etag: string;
}

export interface Infographic {
  /** The tracked file, relative to the repository root. */
  source: string;
  title: string;
  description: string;
  order: number;
  /** The reader's page under `/herald/infographics/` (the wrapper with the back-bar). */
  outName: string;
  /** The copied twin, relative to the `/herald/` mount. */
  twin: string;
  bytes: number;
}

export interface FamilyView {
  key: (typeof FAMILY_VIEWS)[number]['key'];
  label: string;
  source: string;
  outName: string;
  twin: string;
  bytes: number;
  stamp: Stamp;
}

export interface Download {
  name: string;
  source: string;
  bytes: number;
  stamp: Stamp;
}

export interface FamilyFacts {
  count: number;
  derivedAt: string;
}

export interface Family {
  slug: string;
  title: string;
  description: string;
  poster: Infographic & { stamp: Stamp };
  views: FamilyView[];
  pptx: Download[];
  marp: Download[];
  facts: FamilyFacts | null;
}

/** A kind of export holding more than one dated file (CAP-53): the build names every one. */
export class MoreThanOneCurrentExport extends Error {
  readonly files: string[];

  constructor(problems: string[][]) {
    const lines = problems.map((files) => `  ${files.join(', ')}`);
    super(
      `more than one dated export of one kind (CAP-53 keeps one current version per kind; ` +
        `\`python -m pyforge.herald.deck_versions\` names the superseded files):\n${lines.join('\n')}`,
    );
    this.name = 'MoreThanOneCurrentExport';
    this.files = problems.flat();
  }
}

// ------------------------------------------------------------------ helpers mirroring the retired Jinja build

/** the retired Jinja build's `slugify`: NFKD, ASCII only, word characters, spaces and dashes to one dash. */
export function slugify(name: string): string {
  const ascii = name.normalize('NFKD').replace(/[^\x00-\x7f]/g, '');
  const s = ascii.replace(/[^\w\s-]/g, '').trim().toLowerCase();
  return s.replace(/[\s_]+/g, '-') || 'untitled';
}

const TITLE_RE = /<title[^>]*>([\s\S]*?)<\/title>/i;
const NAMED_ENTITIES: Record<string, string> = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
  mdash: '—',
  ndash: '–',
  middot: '·',
  rarr: '→',
  larr: '←',
  hellip: '…',
};

/**
 * Character references in a `<title>`, as Python's `html.unescape` reads them for the names in `NAMED_ENTITIES`
 * (an out-of-range number reads U+FFFD, as there). Any other name is left in place for `readTitle` to refuse.
 */
function unescapeHtml(text: string): string {
  return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z][a-z0-9]*);/gi, (whole, ref: string) => {
    if (ref[0] === '#') {
      const code = ref[1].toLowerCase() === 'x' ? parseInt(ref.slice(2), 16) : parseInt(ref.slice(1), 10);
      const valid = code > 0 && code <= 0x10ffff && (code < 0xd800 || code > 0xdfff);
      return valid ? String.fromCodePoint(code) : '\ufffd';
    }
    return NAMED_ENTITIES[ref] ?? whole;
  });
}

/**
 * the retired Jinja build's `read_title`: the file's own `<title>`, else its stem. A title holding a named character reference
 * this module does not decode is refused, naming the file: Python's table is all of HTML5, so the two paths could
 * title (and name) the infographic differently -- give it an override `title` in `site.yml` instead.
 */
export function readTitle(file: string): string {
  const head = fs.readFileSync(file, 'utf8').slice(0, 100_000);
  const match = TITLE_RE.exec(head);
  if (!match) {
    return path.basename(file, path.extname(file));
  }
  const title = unescapeHtml(match[1]).trim();
  const unknown = /&[a-z][a-z0-9]*;/i.exec(title);
  if (unknown) {
    throw new Error(`${file}: its <title> holds ${unknown[0]}, which the Astro path does not decode; give it an override title in site.yml`);
  }
  return title;
}

function comparePaths(a: string, b: string): number {
  const pa = a.split('/');
  const pb = b.split('/');
  for (let i = 0; i < Math.min(pa.length, pb.length); i += 1) {
    if (pa[i] !== pb[i]) {
      return pa[i] < pb[i] ? -1 : 1;
    }
  }
  return pa.length - pb.length;
}

function glob(repoRoot: string, pattern: string): string[] {
  return fs
    .globSync(pattern, { cwd: repoRoot })
    .map((rel) => rel.split(path.sep).join('/'))
    .sort(comparePaths);
}

function isFile(file: string): boolean {
  try {
    return fs.statSync(file).isFile();
  } catch {
    return false;
  }
}

/**
 * An artifact's provenance stamp: the `<file>.stamp.json` sidecar's `tree` and `etag` when the derive pipeline wrote
 * one, else `unstamped` and a short content hash. Never the build's commit (Story 43.7): that stamped every family page
 * with every commit, so a rebuild of an unmoved tree from a later commit changed the Pages tree and redeployed; what
 * built the page is its built-from line.
 */
export function artifactStamp(file: string): Stamp {
  const sidecar = `${file}.stamp.json`;
  if (isFile(sidecar)) {
    let data: unknown = null;
    try {
      data = JSON.parse(fs.readFileSync(sidecar, 'utf8'));
    } catch {
      data = null;
    }
    if (data && typeof data === 'object' && !Array.isArray(data)) {
      const record = data as Record<string, unknown>;
      if (typeof record.tree === 'string') {
        return {
          tree: record.tree.slice(0, 12),
          etag: typeof record.etag === 'string' ? record.etag.slice(0, 12) : 'unstamped',
        };
      }
    }
  }
  const digest = createHash('sha256').update(fs.readFileSync(file)).digest('hex').slice(0, 12);
  return { tree: 'unstamped', etag: digest };
}

// ------------------------------------------------------------------ the gallery

function overrideFor(
  overrides: Record<string, InfographicOverride | null> | null | undefined,
  rel: string,
): InfographicOverride {
  const table = overrides ?? {};
  for (const key of [rel, path.posix.basename(rel)]) {
    const value = table[key];
    if (value && Object.keys(value).length > 0) {
      return value;
    }
  }
  return {};
}

/**
 * The gallery, as the retired Jinja build's `collect_infographics`: the `include` globs resolved in order, the
 * `exclude` globs removed, each item titled and placed by its override (or its own `<title>`), sorted
 * by `order` then title, and each published name made unique.
 */
export function collectInfographics(site: SiteConfig, repoRoot: string): Infographic[] {
  const cfg = site.infographics;
  const found = new Map<string, null>();
  for (const pattern of cfg.include) {
    for (const rel of glob(repoRoot, pattern)) {
      if (isFile(path.join(repoRoot, rel)) && rel.toLowerCase().endsWith('.html')) {
        found.set(rel, null);
      }
    }
  }
  for (const pattern of cfg.exclude ?? []) {
    for (const rel of glob(repoRoot, pattern)) {
      found.delete(rel);
    }
  }

  const items: Infographic[] = [...found.keys()].map((rel) => {
    const file = path.join(repoRoot, rel);
    const ov = overrideFor(cfg.overrides, rel);
    const title = ov.title || readTitle(file);
    return {
      source: rel,
      title,
      description: ov.description ?? '',
      order: ov.order ?? 500,
      outName: `${ov.slug || slugify(title)}.html`,
      twin: '',
      bytes: fs.statSync(file).size,
    };
  });

  items.sort((a, b) => {
    if (a.order !== b.order) {
      return a.order - b.order;
    }
    const ta = a.title.toLowerCase();
    const tb = b.title.toLowerCase();
    return ta < tb ? -1 : ta > tb ? 1 : 0;
  });

  const seen = new Map<string, number>();
  for (const item of items) {
    const base = item.outName;
    const count = seen.get(base);
    if (count === undefined) {
      seen.set(base, 0);
    } else {
      seen.set(base, count + 1);
      item.outName = `${base.slice(0, -5)}-${count + 1}.html`;
    }
    item.twin = `${TWINS_DIR}/infographics/${item.outName}`;
  }
  return items;
}

// ------------------------------------------------------------------ the deck families

function singleFile(dir: string, suffix: string): string | null {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    return null;
  }
  const matches = fs
    .readdirSync(dir)
    .filter((name) => name.endsWith(suffix) && isFile(path.join(dir, name)))
    .sort();
  return matches.length ? path.join(dir, matches[0]) : null;
}

/** The ISO date a dated export's stem ends with, when it is a real calendar date (`deck_versions._kind_key`). */
function exportDate(stem: string): string | null {
  const match = /-(\d{4}-\d{2}-\d{2})$/.exec(stem);
  if (!match) {
    return null;
  }
  const parsed = new Date(`${match[1]}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === match[1] ? match[1] : null;
}

/**
 * The exports of one kind directory (`src/pptx/*.pptx`, `src/marp/*.md`), newest name first as the
 * Jinja page lists them. A kind is `pyforge.herald.deck_versions`' (`_kind_key`): the stem before a valid
 * `-YYYY-MM-DD`; a kind holding more than one file is recorded in `problems`, never resolved by picking a date.
 * An undated (or invalidly dated) file is no kind there and is listed on its own here.
 */
function currentExports(dir: string, suffix: string, repoRoot: string, problems: string[][]): string[] {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    return [];
  }
  const byKind = new Map<string, string[]>();
  for (const name of fs.readdirSync(dir)) {
    if (!name.endsWith(suffix) || !isFile(path.join(dir, name))) {
      continue;
    }
    const stem = name.slice(0, name.length - path.extname(name).length);
    const date = exportDate(stem);
    const kind = date ? stem.slice(0, -(date.length + 1)) : `\u0000${name}`;
    byKind.set(kind, [...(byKind.get(kind) ?? []), name]);
  }
  const listed: string[] = [];
  for (const names of byKind.values()) {
    if (names.length > 1) {
      problems.push(names.sort().map((name) => path.relative(repoRoot, path.join(dir, name)).split(path.sep).join('/')));
    }
    listed.push(...names);
  }
  return listed.sort().reverse().map((name) => path.join(dir, name));
}

function download(file: string, repoRoot: string): Download {
  return {
    name: path.basename(file),
    source: path.relative(repoRoot, file).split(path.sep).join('/'),
    bytes: fs.statSync(file).size,
    stamp: artifactStamp(file),
  };
}

/**
 * One family per gallery infographic under `presentations/<slug>/`, as the retired Jinja build's
 * `collect_families` -- never a second hand-maintained list. `facts` reads the deck's `facts.yaml`
 * (parsed by the caller), or `null` where it has none.
 */
export function collectFamilies(
  infographics: Infographic[],
  repoRoot: string,
  facts: (slug: string) => FamilyFacts | null = () => null,
): Family[] {
  const families: Family[] = [];
  const problems: string[][] = [];
  const seen = new Set<string>();
  for (const ig of infographics) {
    const parts = ig.source.split('/');
    if (parts.length < 2 || parts[0] !== 'presentations') {
      continue;
    }
    const slug = parts[1];
    if (seen.has(slug)) {
      continue;
    }
    seen.add(slug);

    const deckDir = path.join(repoRoot, 'presentations', slug);
    const views: FamilyView[] = [];
    for (const view of FAMILY_VIEWS) {
      const file = singleFile(path.join(deckDir, 'project'), view.suffix);
      if (file === null) {
        continue;
      }
      views.push({
        key: view.key,
        label: view.label,
        source: path.relative(repoRoot, file).split(path.sep).join('/'),
        outName: view.outName,
        twin: `${TWINS_DIR}/decks/${slug}/${view.outName}`,
        bytes: fs.statSync(file).size,
        stamp: artifactStamp(file),
      });
    }
    const pptx = currentExports(path.join(deckDir, 'src', 'pptx'), '.pptx', repoRoot, problems);
    const marp = currentExports(path.join(deckDir, 'src', 'marp'), '.md', repoRoot, problems);

    families.push({
      slug,
      title: ig.title,
      description: ig.description,
      poster: { ...ig, stamp: artifactStamp(path.join(repoRoot, ig.source)) },
      views,
      pptx: pptx.map((file) => download(file, repoRoot)),
      marp: marp.map((file) => download(file, repoRoot)),
      facts: facts(slug),
    });
  }
  if (problems.length) {
    throw new MoreThanOneCurrentExport(problems);
  }
  return families;
}

// ------------------------------------------------------------------ the overview's neighbours

export interface KedroVizExport {
  commit: string;
  date: string;
  version: string;
}

/**
 * `site.yml`'s neighbours, the overview's tiles: an entry carrying `mount: kedro-viz` shows only when the export is in
 * the build input (`docs/dashboard/kedro-viz/` holding a file, the one presence rule, `nav.ts`'s `holdsAFile`) and
 * then names its manifest's commit and date. A present export without a
 * well-formed manifest is refused, naming the file (Story 42.2).
 */
export function neighbours(site: SiteConfig, repoRoot: string): Array<Record<string, unknown>> {
  const exportDir = path.join(repoRoot, 'docs', 'dashboard', 'kedro-viz');
  const present = holdsAFile(exportDir);
  const shown: Array<Record<string, unknown>> = [];
  for (const entry of site.neighbours ?? []) {
    if (entry.mount !== 'kedro-viz') {
      shown.push({ ...entry });
      continue;
    }
    if (present) {
      shown.push({ ...entry, export: readKedroVizManifest(exportDir) });
    }
  }
  return shown;
}

function readKedroVizManifest(exportDir: string): KedroVizExport {
  const label = 'docs/dashboard/kedro-viz';
  if (!isFile(path.join(exportDir, 'index.html'))) {
    throw new Error(`${label}/index.html: missing from the Kedro-Viz export`);
  }
  const manifest = path.join(exportDir, 'manifest.json');
  if (!isFile(manifest)) {
    throw new Error(`${label}/manifest.json: missing from the Kedro-Viz export`);
  }
  let data: unknown;
  try {
    data = JSON.parse(fs.readFileSync(manifest, 'utf8'));
  } catch (exc) {
    throw new Error(`${label}/manifest.json: not JSON (${String(exc)})`);
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error(`${label}/manifest.json: not a JSON object`);
  }
  const record = data as Record<string, unknown>;
  for (const key of ['export_commit', 'export_date']) {
    const value = record[key];
    if (typeof value !== 'string' || !value.trim()) {
      throw new Error(`${label}/manifest.json: lacks '${key}'`);
    }
  }
  const version = record.kedro_viz_version;
  return {
    commit: String(record.export_commit).trim(),
    date: String(record.export_date).trim(),
    version: typeof version === 'string' ? version.trim() : '',
  };
}

// ------------------------------------------------------------------ the wrapper's back-bar

function escapeText(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** The back-bar's rules: Starlight's theme variables only (`styles/theme.css`, linked by the reader page). */
const BACKBAR_STYLE = `<style>
.ig-backbar{position:fixed;top:0;left:0;right:0;z-index:2147483000;
background:color-mix(in srgb,var(--sl-color-black) 86%,transparent);
-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);font-family:var(--sl-font-mono);
font-size:12px;padding:7px 16px;display:flex;align-items:center;gap:14px;
color:var(--sl-color-white);box-sizing:border-box;border-bottom:1px solid var(--sl-color-gray-5)}
.ig-backbar a{color:var(--sl-color-white);text-decoration:none;
border-bottom:1px solid color-mix(in srgb,var(--sl-color-white) 40%,transparent)}
.ig-backbar a:hover{border-bottom-color:var(--sl-color-accent);color:var(--sl-color-text-accent)}
.ig-backbar .ig-title{color:var(--sl-color-gray-3);margin-left:auto;text-align:right;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
body{padding-top:32px!important}
@media print{.ig-backbar{display:none!important}body{padding-top:0!important}}
</style>
`;

/**
 * The infographic page's back-bar, as the retired Jinja build's `BACKBAR` (links relative to `/herald/infographics/`), plus a
 * link to the framed file itself (`twinHref`), to read or print it whole.
 */
export function infographicBackbar(title: string, twinHref: string): string {
  return `<div class="ig-backbar">
  <a href="index.html">&larr; All infographics</a>
  <a href="../index.html">Overview</a>
  <a href="../dossier/index.html">Dossier</a>
  <a href="${escapeAttr(twinHref)}">Full page</a>
  <span class="ig-title">${escapeText(title)}</span>
</div>
${BACKBAR_STYLE}`;
}

/**
 * A family view's back-bar, as the retired Jinja build's `FAMILY_VIEW_BACKBAR` (links relative to `/herald/decks/<slug>/`), plus a
 * link to the framed file itself (`twinHref`).
 */
export function familyViewBackbar(deckTitle: string, title: string, twinHref: string): string {
  return `<div class="ig-backbar">
  <a href="index.html">&larr; ${escapeText(deckTitle)} family</a>
  <a href="../../index.html">Overview</a>
  <a href="../../dossier/index.html">Dossier</a>
  <a href="${escapeAttr(twinHref)}">Full page</a>
  <span class="ig-title">${escapeText(title)}</span>
</div>
${BACKBAR_STYLE}`;
}

function escapeAttr(text: string): string {
  return escapeText(text).replace(/"/g, '&quot;');
}

/**
 * The reader's page around one twin (CAP-55: wrap, never edit): the back-bar, then the twin the build
 * copied, in a frame filling the rest of the viewport. `rel` climbs from the page to the `/herald/`
 * mount; `twin` is the twin's path under it. The page runs the theme script and links the site theme, so its
 * back-bar follows the docs toggle (Story 43.4's review); the twin keeps its own design. Below the frame, the line
 * saying what built the page (Story 43.5).
 */
export function twinWrapperHtml(options: { title: string; backbar: string; rel: string; twin: string }): string {
  const { title, backbar, rel, twin } = options;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeText(title)}</title>
<meta name="generator" content="Astro">
<meta http-equiv="Content-Security-Policy" content="${HERALD_CSP}">
<script>${THEME_SCRIPT}</script>
<link rel="stylesheet" href="${escapeAttr(`${rel}${HERALD_THEME}`)}">
<style>
html,body{margin:0;height:100%;background:var(--sl-color-black)}
body{box-sizing:border-box}
.ig-twin{display:block;width:100%;height:calc(100vh - 32px - 1.5rem);border:0;background:var(--sl-color-black)}
.built-from{box-sizing:border-box;height:1.5rem;margin:0;padding:0 16px;line-height:1.5rem;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
</style>
</head>
<body>
${backbar}<iframe class="ig-twin" src="${escapeAttr(`${rel}${twin}`)}" title="${escapeAttr(title)}"></iframe>
${builtFromHtml()}
</body>
</html>
`;
}
