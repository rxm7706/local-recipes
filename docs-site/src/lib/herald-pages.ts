/**
 * The herald overview, gallery and deck-family pages, read as data (Story 43.2, spec-pyforge-herald
 * CAP-61 on CAP-35, CAP-53 and CAP-55).
 *
 * The inputs are the ones `docsite/build.py` reads -- `site.yml`'s `infographics` include, exclude and
 * override lists, each `presentations/<slug>/` export set and each export's `<file>.stamp.json`
 * sidecar -- and the rules mirror its `collect_infographics`, `collect_families` and `_artifact_stamp`,
 * so both paths list the same infographics and families while both exist (the parity test,
 * `tests/meta/test_herald_pages_parity.py`, compares them). Node builtins only, and YAML is parsed by
 * the caller (`src/loaders/herald-pages-loader.ts`): the parity test imports this module with node's
 * type stripping and no `node_modules`.
 *
 * One current version per export (CAP-53; AD-4 as amended 2026-09-28): `pyforge.herald.deck_versions`
 * is the writers' one definition of current. This module lists the one dated file per kind the tree
 * holds and never chooses a newest date; a kind holding more than one dated file is refused, naming
 * every file.
 */

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

/** Where each twin is served under the `/herald/` mount with the flag on (`scripts/populate-public.ts`, Story 43.3). */
export const TWINS_DIR = 'twins';

/**
 * The herald pages' faces, served at `/herald/<HERALD_FONTS>` (`pages/herald/[fonts].css.ts`, Story 43.4) for the
 * pages Astro does not style: the twins (the one line `vendorFontLinks` gives them) and the reader pages.
 */
export const HERALD_FONTS = 'fonts.css';

/** The preview frame's load handler (`components/herald/Shot.astro`), allowed by hash in the CSP below. */
export const PREVIEW_ONLOAD = "this.parentElement.classList.add('is-loaded')";

/**
 * The herald pages follow the docs header's theme toggle (Story 43.4): Starlight's toggle keeps its choice under
 * `starlight-theme` ('light', 'dark', or '' for auto) and sets `data-theme` on `<html>`. This script, inline in each
 * herald layout's head so no page paints in the other theme first, reads that key and resolves auto from the system
 * scheme as Starlight's ThemeProvider does; `styles/herald.css` keys the dark tokens to `[data-theme='dark']`. No
 * second toggle and no second store. Allowed by hash in the CSP below.
 */
export const THEME_SCRIPT =
  "try{var t=localStorage.getItem('starlight-theme')}catch(e){}" +
  "document.documentElement.dataset.theme=(t||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'))==='light'?'light':'dark'";

const sha256 = (text: string): string => `'sha256-${createHash('sha256').update(text).digest('base64')}'`;

/**
 * The `Content-Security-Policy` every Astro herald page carries (Story 43.3, AD-21): nothing loads from another
 * origin. Inline styles are the dossier's accents and the back-bar's; the inline scripts are the preview handler
 * and the theme script.
 */
export const HERALD_CSP = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-hashes' ${sha256(PREVIEW_ONLOAD)} ${sha256(THEME_SCRIPT)}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "frame-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ');

const GOOGLE_FONT_LINK = /<link\b[^>]*\b(?:href|rel)=['"][^'"]*fonts\.(?:googleapis|gstatic)\.com[^'"]*['"][^>]*>\s*/gi;
const GOOGLE_FONT_IMPORT = /@import\s+url\(['"]?https:\/\/fonts\.googleapis\.com[^)]+\)\s*;?\s*/gi;

/**
 * A twin as the site serves it: Google Fonts links and imports dropped and one link to the site's own fonts added,
 * as `docsite/build.py`'s `rewrite_google_font_links` (Story 31.3) -- the one transformation a twin gets (AD-21).
 * Since Story 43.4 the link names the @fontsource faces at `HERALD_FONTS`, not the Jinja path's vendored files.
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

/** The family views' published names, as `build.py`'s `_FAMILY_VIEW_OUT_NAMES`. */
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

// ------------------------------------------------------------------ helpers mirroring build.py

/** `build.py`'s `slugify`: NFKD, ASCII only, word characters, spaces and dashes to one dash. */
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
 * `build.py`'s `read_title`: the file's own `<title>`, else its stem. A title holding a named character reference
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

/** The build's commit, as `build.py`'s `git_commit`: `GITHUB_SHA`'s first seven, else `git rev-parse --short HEAD`. */
export function gitCommit(repoRoot: string): string {
  const sha = process.env.GITHUB_SHA;
  if (sha) {
    return sha.slice(0, 7);
  }
  try {
    return execFileSync('git', ['-C', repoRoot, 'rev-parse', '--short', 'HEAD'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 10_000,
    }).trim();
  } catch {
    return '';
  }
}

/** The build date, as `build.py`'s `built_at` (UTC, `YYYY-MM-DD`). */
export function builtAt(now: Date = new Date()): string {
  return now.toISOString().slice(0, 10);
}

/**
 * An artifact's provenance stamp, as `build.py`'s `_artifact_stamp`: the `<file>.stamp.json` sidecar's
 * `tree` and `etag` when the derive pipeline wrote one, else the build's commit and a short content hash.
 */
export function artifactStamp(file: string, commit: string): Stamp {
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
  return { tree: (commit || 'unknown').slice(0, 12), etag: digest };
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
 * The gallery, as `build.py`'s `collect_infographics`: the `include` globs resolved in order, the
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

function download(file: string, repoRoot: string, commit: string): Download {
  return {
    name: path.basename(file),
    source: path.relative(repoRoot, file).split(path.sep).join('/'),
    bytes: fs.statSync(file).size,
    stamp: artifactStamp(file, commit),
  };
}

/**
 * One family per gallery infographic under `presentations/<slug>/`, as `build.py`'s
 * `collect_families` -- never a second hand-maintained list. `facts` reads the deck's `facts.yaml`
 * (parsed by the caller), or `null` where it has none.
 */
export function collectFamilies(
  infographics: Infographic[],
  repoRoot: string,
  commit: string,
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
        stamp: artifactStamp(file, commit),
      });
    }
    const pptx = currentExports(path.join(deckDir, 'src', 'pptx'), '.pptx', repoRoot, problems);
    const marp = currentExports(path.join(deckDir, 'src', 'marp'), '.md', repoRoot, problems);

    families.push({
      slug,
      title: ig.title,
      description: ig.description,
      poster: { ...ig, stamp: artifactStamp(path.join(repoRoot, ig.source), commit) },
      views,
      pptx: pptx.map((file) => download(file, repoRoot, commit)),
      marp: marp.map((file) => download(file, repoRoot, commit)),
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
 * `site.yml`'s neighbours for the overview, as `kedro_viz_export.neighbours`: an entry carrying
 * `mount: kedro-viz` shows only when the export is in the build input (`docs/dashboard/kedro-viz/`
 * holding anything) and then names its manifest's commit and date. A present export without a
 * well-formed manifest is refused, naming the file (Story 42.2).
 */
export function neighbours(site: SiteConfig, repoRoot: string): Array<Record<string, unknown>> {
  const exportDir = path.join(repoRoot, 'docs', 'dashboard', 'kedro-viz');
  const present = fs.existsSync(exportDir) && fs.statSync(exportDir).isDirectory() && fs.readdirSync(exportDir).length > 0;
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

const BACKBAR_STYLE = `<style>
.ig-backbar{position:fixed;top:0;left:0;right:0;z-index:2147483000;background:rgba(18,22,26,.86);
-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);font-family:"IBM Plex Mono",ui-monospace,
SFMono-Regular,Menlo,monospace;font-size:12px;padding:7px 16px;display:flex;align-items:center;gap:14px;
color:#e7ebe6;box-sizing:border-box}
.ig-backbar a{color:#e7ebe6;text-decoration:none;border-bottom:1px solid rgba(231,235,230,.4)}
.ig-backbar a:hover{border-bottom-color:#dd9a3f;color:#dd9a3f}
.ig-backbar .ig-title{color:rgba(231,235,230,.62);margin-left:auto;text-align:right;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
body{padding-top:32px!important}
@media print{.ig-backbar{display:none!important}body{padding-top:0!important}}
</style>
`;

/**
 * The infographic page's back-bar, as `build.py`'s `BACKBAR` (links relative to `/herald/infographics/`), plus a
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
 * A family view's back-bar, as `build.py`'s `FAMILY_VIEW_BACKBAR` (links relative to `/herald/decks/<slug>/`), plus a
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
 * mount; `twin` is the twin's path under it.
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
<link rel="stylesheet" href="${escapeAttr(`${rel}${HERALD_FONTS}`)}">
<style>
html,body{margin:0;height:100%;background:#12161a}
body{box-sizing:border-box}
.ig-twin{display:block;width:100%;height:calc(100vh - 32px);border:0;background:#fff}
</style>
</head>
<body>
${backbar}<iframe class="ig-twin" src="${escapeAttr(`${rel}${twin}`)}" title="${escapeAttr(title)}"></iframe>
</body>
</html>
`;
}
