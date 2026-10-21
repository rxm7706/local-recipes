/**
 * `pages-build` and `pages-check` (Story 43.7, spec-pyforge-herald CAP-61; AD-21, AD-23): the one generator builds
 * the one GitHub Pages artifact, and one check judges it. Replaces the retired Jinja path's assembler: Astro now writes
 * every page, mount, redirect and the artifact build itself (`astro.config.mjs`), so this script only runs it and
 * reads what it wrote.
 *
 *     node scripts/pages.mts build    # pixi run -e site pages-build
 *     node scripts/pages.mts check    # pixi run -e site pages-check (after pages-build); exit 1 naming each finding
 *
 * **build** resolves the site URL the way `actions/configure-pages` hands it over (`PAGES_HOST_BASE_URL` and
 * `PAGES_HOST_BASE_PATH`, else the public github.io URL; Stories 31.1, 42.3), sets `PAGES_BUILT_AT` once (Story 43.5:
 * every page's built-from line names one build time) in the build's own environment, never this process's, runs
 * `npm run build` in `docs-site/`, and records the site URL in the artifact for the check.
 *
 * **check** reads `docs-site/build/site/` (`--root` names another): every path the site must hold (AC7) and every
 * family page the decks index links, the dashboard mount exactly the build input's, the Kedro-Viz and Vizro mounts
 * when present, the frozen legacy redirects, one CSP per page that allows every inline script and `on*=` handler the
 * page carries, one built-from line per page (all naming one build), the machine-read documents, every local link of
 * every page, a non-empty body on every shelf page (and at least one shelf page), one menu on every navigable page,
 * each menu link landing on a file of the artifact, faces from the bundle only, and -- through
 * `scripts/origin_check.py` -- nothing loading from another origin. Node builtins only (the origin check is Python,
 * run with `$HERALD_PYTHON` or `python`): the herald tests run it over fixture trees.
 */

import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { ARTIFACT_DOSSIER, NOT_PAGES } from '../src/lib/artifact.ts';
import { BUILT_FROM_OPEN } from '../src/lib/built-from.ts';
import { envFlagOn } from '../src/lib/flags.ts';
import { DASHBOARD_EXPORTS, holdsAFile } from '../src/lib/nav.ts';
import { marketplacePagesEnabled } from './populate-public.mts';

const DOCS_SITE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPO = path.dirname(DOCS_SITE);
/** The artifact `pages-build` writes and `actions/upload-pages-artifact` uploads. */
export const ARTIFACT = path.join(DOCS_SITE, 'build', 'site');
/** The site URL the build used, recorded in the artifact for the check. */
export const SITE_URL_MARKER = '.pages-build-site-url';

type Env = Record<string, string | undefined>;

// ------------------------------------------------------------------------------------------- the site URL

/** The public github.io site URL (Story 27.2). */
export function publicSiteUrl(env: Env = process.env): string {
  const repo = env.GITHUB_REPOSITORY || 'rxm7706/local-recipes';
  const [owner, name, ...rest] = repo.split('/');
  if (!owner || !name || rest.length) {
    throw new Error(`invalid GITHUB_REPOSITORY: ${JSON.stringify(repo)}`);
  }
  return `https://${owner}.github.io/${name}`;
}

/** `configure-pages`' `base_url` and `base_path` as one site URL; an empty or `/` path is a root-hosted site. */
export function combinePagesHost(baseUrl: string, basePath: string): string {
  const origin = baseUrl.replace(/\/+$/, '');
  let p = basePath.trim();
  if (!p || p === '/') {
    return origin;
  }
  p = `/${p.replace(/^\/+/, '').replace(/\/+$/, '')}`;
  return new URL(origin).pathname.replace(/\/+$/, '') === p ? origin : `${origin}${p}`;
}

/** The site URL the build and the check use: the deploying host's whenever a base URL is given, else the public one. */
export function resolveSiteUrl(env: Env = process.env): string {
  const base = (env.PAGES_HOST_BASE_URL ?? '').trim();
  return base ? combinePagesHost(base, env.PAGES_HOST_BASE_PATH ?? '') : publicSiteUrl(env);
}

/** Scheme, host and port of `url`, lower case. */
export function siteOrigin(url: string): string {
  const u = new URL(url);
  return `${u.protocol}//${u.host}`.toLowerCase();
}

function basePathOf(siteUrl: string): string {
  const p = new URL(siteUrl).pathname;
  return p.endsWith('/') ? p : `${p}/`;
}

// ------------------------------------------------------------------------------------------------ build

/** Build the artifact; returns the site URL it was built for. */
export function build(env: Env = process.env): string {
  const siteUrl = resolveSiteUrl(env);
  // a given time reaches the build as given: `built-from.ts` judges it (a byte-order mark, which trim() drops, included)
  const given = env.PAGES_BUILT_AT ?? '';
  const builtAt = given.trim() ? given : new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const done = spawnSync('npm', ['run', 'build'], {
    cwd: DOCS_SITE,
    env: { ...env, SITE_URL: siteUrl, PAGES_BUILT_AT: builtAt },
    stdio: 'inherit',
  });
  if (done.status !== 0) {
    throw new Error(`npm run build exited ${done.status ?? done.signal}`);
  }
  fs.writeFileSync(path.join(ARTIFACT, SITE_URL_MARKER), `${siteUrl}\n`);
  return siteUrl;
}

// --------------------------------------------------------------------------------------- reading pages

/** Vendored roots and files the origin check does not judge (AD-21 rule 5), each with its reason. */
export const VENDORED: Record<string, string> = {
  'dashboard/kedro-viz/':
    "Kedro-Viz static build: atlas's kedro-viz-export artifact (viz-publish-stage), mounted verbatim from docs/dashboard/kedro-viz/",
  'dashboard/vizro/assets/plotly.min.js':
    "plotly.js, the env's plotly package_data bundle the Vizro export copies byte for byte (atlas Story 30.2); its " +
    'geo and map traces name a CDN no exported page draws -- the file only, every Vizro page stays judged ' +
    '(orchestrator ruling 2026-10-15, operator may override)',
};
/** The frozen root redirects (Story 43.3). */
const REDIRECTS_JSON = path.join(DOCS_SITE, 'redirects.json');
const REFRESH_URL = /http-equiv=["']refresh["'][^>]*content=["'][^"']*url=([^"']+)["']/i;
const CSP_META = /<meta\s+http-equiv=["']Content-Security-Policy["']/gi;
const BUILT_FROM = new RegExp(`${BUILT_FROM_OPEN.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^<]*)</p>`, 'g');
const READER_VIEWS = new Set(['infographic-deck.html', 'executive-summary.html']);

function files(root: string): string[] {
  return fs
    .readdirSync(root, { recursive: true, encoding: 'utf8' })
    .map((rel) => rel.split(path.sep).join('/'))
    .filter((rel) => fs.statSync(path.join(root, rel)).isFile())
    .sort();
}

const ENTITIES: Record<string, string> = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };

/**
 * An attribute value's character references decoded -- XML's five named ones and numeric ones only, not HTML5's full
 * table: a handler written with another named reference (`&lpar;`) is hashed undecoded, which fails loud against a
 * hash of the decoded text (no page writes one). The CSP check models hashes, `'unsafe-hashes'` and
 * `'unsafe-inline'`; it does not model `'strict-dynamic'`, which no policy of this site emits (Story 43.7's re-review).
 */
function unescapeAttr(value: string): string {
  return value.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, ref: string) => {
    if (ref[0] === '#') {
      return String.fromCodePoint(ref[1].toLowerCase() === 'x' ? parseInt(ref.slice(2), 16) : parseInt(ref.slice(1), 10));
    }
    return ENTITIES[ref.toLowerCase()] ?? whole;
  });
}

export interface Tag {
  name: string;
  attrs: Record<string, string>;
}

/** The attributes of a tag's attribute text, names lower-cased, values unescaped; of a name given twice the first
 * counts, as a browser keeps it (`<a onclick="x()" ONCLICK="y()">` runs `x()`). */
function attributes(text: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  for (const a of text.matchAll(/([^\s=/>"']+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g)) {
    const name = a[1].toLowerCase();
    if (!Object.hasOwn(attrs, name)) {
      attrs[name] = unescapeAttr(a[2] ?? a[3] ?? a[4] ?? '');
    }
  }
  return attrs;
}

/** Every tag of `html` with its attributes; script and style bodies and comments are not markup and are skipped. */
export function tags(html: string): Tag[] {
  const markup = html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/(<(script|style)\b[^>]*>)[\s\S]*?<\/\2>/gi, '$1');
  return [...markup.matchAll(/<([a-zA-Z][\w:-]*)\b((?:[^>"']|"[^"]*"|'[^']*')*)>/g)].map((m) => ({
    name: m[1].toLowerCase(),
    attrs: attributes(m[2]),
  }));
}

// ------------------------------------------------------------------------------------- the page's own CSP

const SCRIPT_ELEMENT = /<script\b((?:[^>"']|"[^"]*"|'[^']*')*)>([\s\S]*?)<\/script\s*>/gi;
/** A data block (`application/json`, `application/ld+json` ...) runs nothing, so no CSP judges it. */
const DATA_BLOCK = /(?:^|\/|\+)json$/i;

const sha256Source = (text: string): string => `'sha256-${createHash('sha256').update(text, 'utf8').digest('base64')}'`;

/** The sources of the first of `directives` that `policy` states (CSP's fallback order); `null` when none is stated. */
function sourcesOf(policy: string, directives: string[]): string[] | null {
  const stated = new Map<string, string[]>();
  for (const part of policy.split(';')) {
    const [name, ...sources] = part.trim().split(/\s+/);
    if (name && !stated.has(name.toLowerCase())) {
      stated.set(name.toLowerCase(), sources);
    }
  }
  const first = directives.find((d) => stated.has(d));
  return first === undefined ? null : (stated.get(first) ?? null);
}

/** `sources` run an inline script (`handler`: an `on*=` value) whose digest is `hash`, as a browser decides it. */
function runs(sources: string[] | null, hash: string, handler: boolean): boolean {
  if (sources === null) {
    return true;
  }
  const words = sources.map((s) => s.toLowerCase());
  // a hash or nonce in the list makes the browser ignore 'unsafe-inline' (CSP Level 2)
  if (words.includes("'unsafe-inline'") && !words.some((s) => /^'(?:sha(?:256|384|512)-|nonce-)/.test(s))) {
    return true;
  }
  return sources.includes(hash) && (!handler || words.includes("'unsafe-hashes'"));
}

/**
 * Each inline script and `on*=` handler of `html` that its own CSP meta would block, one line each (AD-21; Story
 * 43.7's review: `HERALD_CSP` is a fixed list and a Starlight upgrade can add a handler, either of which the browser
 * blocks silently): an inline `<script>`'s sha256 in `script-src-elem` / `script-src` / `default-src`, a handler's
 * with `'unsafe-hashes'` in `script-src-attr` / `script-src` / `default-src`, unless `'unsafe-inline'` holds.
 */
export function blockedScripts(html: string): string[] {
  const meta = tags(html).find((t) => t.name === 'meta' && (t.attrs['http-equiv'] ?? '').toLowerCase() === 'content-security-policy');
  if (!meta) {
    return [];
  }
  const policy = meta.attrs.content ?? '';
  const elements = sourcesOf(policy, ['script-src-elem', 'script-src', 'default-src']);
  const handlers = sourcesOf(policy, ['script-src-attr', 'script-src', 'default-src']);
  const out = new Set<string>();
  for (const [, attrText, body] of html.matchAll(SCRIPT_ELEMENT)) {
    const attrs = attributes(attrText);
    if ('src' in attrs || DATA_BLOCK.test((attrs.type ?? '').trim())) {
      continue;
    }
    const hash = sha256Source(body);
    if (!runs(elements, hash, false)) {
      out.add(`an inline <script> its CSP blocks (${hash} is not in its script-src)`);
    }
  }
  for (const tag of tags(html)) {
    for (const [name, value] of Object.entries(tag.attrs)) {
      const hash = sha256Source(value);
      if (/^on[a-z]+$/.test(name) && !runs(handlers, hash, true)) {
        out.add(`an inline ${name}= handler its CSP blocks (${hash} with 'unsafe-hashes' is not in its script-src)`);
      }
    }
  }
  return [...out];
}

/** Every URL a page names in an `href`, `src`, `srcset`, `poster` or `data` attribute. */
export function urls(html: string): string[] {
  return tags(html).flatMap((tag) => [
    ...['href', 'src', 'poster', 'data'].filter((key) => key in tag.attrs && !(key === 'data' && tag.name !== 'object')).map((key) => tag.attrs[key]),
    ...(tag.attrs.srcset ?? '').split(',').map((c) => c.trim().split(/\s+/)[0]).filter(Boolean),
  ]);
}

function isStub(html: string): boolean {
  return REFRESH_URL.test(html);
}

function readerPage(rel: string): boolean {
  if (rel.startsWith('herald/infographics/') && !rel.endsWith('/index.html')) {
    return true;
  }
  return rel.startsWith('herald/decks/') && READER_VIEWS.has(rel.split('/').pop() ?? '');
}

/**
 * Where `raw`, written on page `rel`, lands inside `root`: a file, or a directory's `index.html`. `null` for a URL that
 * names no file of the artifact (another site, a fragment, `mailto:` ...); a string naming the problem otherwise.
 */
export function resolveLink(root: string, rel: string, raw: string, base: string): { file: string } | { problem: string } | null {
  const url = raw.trim().split('#')[0].split('?')[0];
  if (!url || /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(url)) {
    return null;
  }
  if (url.startsWith('/') && !url.startsWith(base)) {
    return { problem: `outside the base path ${base}` };
  }
  if (!url.startsWith('/') && rel === '404.html') {
    return { problem: 'relative on the 404 page, which is served at any path' };
  }
  let decoded: string;
  try {
    decoded = decodeURIComponent(url.startsWith('/') ? url.slice(base.length) : url);
  } catch {
    return { problem: 'malformed percent-encoding' };
  }
  const target = url.startsWith('/') ? path.join(root, decoded) : path.join(root, path.dirname(rel), decoded);
  const inside = path.relative(root, target);
  if (inside.startsWith('..') || path.isAbsolute(inside)) {
    return { problem: 'escapes the artifact' };
  }
  for (const candidate of [target, path.join(target, 'index.html')]) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      return { file: candidate };
    }
  }
  return { problem: 'resolves to nothing' };
}

// ------------------------------------------------------------------------------------------------ check

/** The paths every build holds (AC7), and those `pyforge.herald.status_pages` adds. */
export const REQUIRED = [
  'index.html',
  '404.html',
  'herald/index.html',
  'herald/dossier/index.html',
  'herald/infographics/index.html',
  'herald/decks/index.html',
  ARTIFACT_DOSSIER,
  'llms.txt',
  'llms-full.txt',
  'facts.json',
  'changes/index.html',
  'changes/rss.xml',
];
export const STATUS_PAGES = ['status/index.html', 'status/ci/index.html', 'status/runs/index.html'];
const DECKS_INDEX = 'herald/decks/index.html';

/** The attributes that take a URL a browser would run as script when it names the `javascript:` scheme. */
const URL_ATTRIBUTES = ['href', 'xlink:href', 'src', 'action', 'formaction'];

/**
 * Each `javascript:` URL a page names in a link, a frame or image source, or a form's target, one line each: an inline
 * script by a third route, which no page's CSP allows (none carries `'unsafe-inline'`), so a dead control in the
 * browser that the link walk, skipping every scheme, never sees (Story 43.7's re-review). The scheme is read as a
 * browser reads it: any case, leading spaces and control characters dropped, tabs and newlines inside ignored.
 */
export function javascriptUrls(html: string): string[] {
  return tags(html).flatMap((tag) =>
    URL_ATTRIBUTES.filter((key) => {
      const url = (tag.attrs[key] ?? '').replace(/[\t\n\r]/g, '').replace(/^[\u0000-\u0020]+/, '');
      return Object.hasOwn(tag.attrs, key) && /^javascript:/i.test(url);
    }).map((key) => `a javascript: URL in <${tag.name} ${key}> (${JSON.stringify(tag.attrs[key])})`),
  );
}

/** The family pages the decks index links (`<slug>/index.html`, relative or under the base), as artifact paths. */
export function familyPages(html: string, base: string): string[] {
  const out = new Set<string>();
  for (const tag of tags(html)) {
    const href = (tag.attrs.href ?? '').split(/[?#]/)[0];
    if (tag.name !== 'a' || !href || /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(href) || (href.startsWith('/') && !href.startsWith(base))) {
      continue;
    }
    const rel = href.startsWith('/') ? href.slice(base.length) : path.posix.join(path.posix.dirname(DECKS_INDEX), href);
    const slug = /^herald\/decks\/([^/]+)\/(?:index\.html)?$/.exec(path.posix.normalize(rel))?.[1];
    if (slug) {
      out.add(`herald/decks/${slug}/index.html`);
    }
  }
  return [...out].sort();
}

/** What the build input mounts at `/dashboard/`: every entry of `docs/dashboard/` but its README and dot-entries, an
 * export only when it holds a file (`scripts/populate-public.mts`'s rule). */
export function dashboardInput(repoRoot: string): string[] {
  const dir = path.join(repoRoot, 'docs', 'dashboard');
  if (!fs.existsSync(dir)) {
    return [];
  }
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.name !== 'README.md' && !e.name.startsWith('.'))
    .filter((e) => (e.isDirectory() ? holdsAFile(path.join(dir, e.name)) : true))
    .map((e) => e.name)
    .sort();
}

/** A `&` that starts none of XML's five named entities or a character reference (`&nbsp;` is HTML, not XML). */
const BARE_AMPERSAND = /&(?!(?:amp|lt|gt|quot|apos);|#\d+;|#x[0-9a-fA-F]+;)/; // XML names are case-sensitive

/**
 * An XML document's elements nest and close, its text and attribute values hold no bare `<` or `&` and no entity but
 * XML's five (no parser in node builtins; the feed is ours and escaped, and carries no comment or CDATA section,
 * which this refuses).
 */
function wellFormed(xml: string): boolean {
  const body = xml.replace(/^<\?xml[^?]*\?>\s*/, '');
  const stack: string[] = [];
  const pattern = new RegExp(
    `<(\\/?)([A-Za-z][\\w:.-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\\/?)>|<|${BARE_AMPERSAND.source}`,
    'g',
  );
  for (const m of body.matchAll(pattern)) {
    if (!m[2] || /</.test(m[3]) || BARE_AMPERSAND.test(m[3])) {
      return false; // a bare < or & in text, or in an attribute value
    }
    if (m[1]) {
      if (stack.pop() !== m[2]) {
        return false;
      }
    } else if (!m[4]) {
      stack.push(m[2]);
    }
  }
  return stack.length === 0;
}

export interface CheckOptions {
  /** The repository whose `docs/dashboard/` the build mounted (`HERALD_PAGES_REPO_ROOT`, else this one). */
  repoRoot?: string;
  env?: Env;
  /** Run the origin check (Python); the herald tests that judge the rest over a fixture tree turn it off. */
  origins?: boolean;
}

/** Every finding about the artifact at `root`, one line each; empty when it passes. */
export function check(root: string, options: CheckOptions = {}): string[] {
  const env = options.env ?? process.env;
  const repoRoot = options.repoRoot ?? (env.HERALD_PAGES_REPO_ROOT ? path.resolve(env.HERALD_PAGES_REPO_ROOT) : REPO);
  const marker = path.join(root, SITE_URL_MARKER);
  const siteUrl = fs.existsSync(marker) ? fs.readFileSync(marker, 'utf8').trim() : resolveSiteUrl(env);
  const base = basePathOf(siteUrl);
  const out: string[] = [];
  const all = files(root);
  const has = (rel: string) => all.includes(rel);
  const read = (rel: string) => fs.readFileSync(path.join(root, rel), 'utf8');

  // AC7: the paths every build holds, every family page the decks index links (there is at least one), and the
  // status pages exactly with their flag.
  const statusOn = envFlagOn('PYFORGE_STATUS_PAGES', env);
  const families = has(DECKS_INDEX) ? familyPages(read(DECKS_INDEX), base) : [];
  if (has(DECKS_INDEX) && !families.length) {
    out.push(`${DECKS_INDEX} links no family page (herald/decks/<slug>/)`);
  }
  for (const rel of [...REQUIRED, ...families, ...(statusOn ? STATUS_PAGES : [])]) {
    if (!has(rel)) {
      out.push(`missing required path ${rel}`);
    }
  }
  if (!statusOn && all.some((rel) => rel.startsWith('status/'))) {
    out.push('status/ exists in the artifact but pyforge.herald.status_pages is off');
  }

  // The dashboard mount is exactly the build input's (AD-21 rule 1), its exports well formed.
  const mounted = [...new Set(all.filter((rel) => rel.startsWith('dashboard/')).map((rel) => rel.split('/')[1]))].sort();
  const input = dashboardInput(repoRoot);
  const extra = mounted.filter((name) => !input.includes(name));
  const lost = input.filter((name) => !mounted.includes(name));
  if (extra.length) {
    out.push(`collision at dashboard/: ${extra.join(', ')} not in the build input docs/dashboard/`);
  }
  if (lost.length) {
    out.push(`docs/dashboard/ entries not mounted at dashboard/: ${lost.join(', ')}`);
  }
  const kedroViz = mounted.includes('kedro-viz');
  if (kedroViz) {
    let manifest: Record<string, unknown> | null = null;
    try {
      manifest = JSON.parse(read('dashboard/kedro-viz/manifest.json'));
    } catch {
      manifest = null;
    }
    if (!has('dashboard/kedro-viz/index.html') || !manifest || ['export_commit', 'export_date'].some((k) => typeof manifest?.[k] !== 'string' || !(manifest[k] as string).trim())) {
      out.push('dashboard/kedro-viz/ lacks index.html or a manifest.json naming export_commit and export_date');
    }
    const stub = has('kedro-viz/index.html') ? REFRESH_URL.exec(read('kedro-viz/index.html'))?.[1] ?? '' : '';
    const landed = stub ? resolveLink(root, 'kedro-viz/index.html', stub, base) : null;
    if (!landed || !('file' in landed) || landed.file !== path.join(root, 'dashboard', 'kedro-viz', 'index.html')) {
      out.push(`kedro-viz/index.html does not redirect to dashboard/kedro-viz/ under the base path ${base}`);
    }
  } else if (all.some((rel) => rel.startsWith('kedro-viz/'))) {
    out.push('kedro-viz/ exists in the artifact but no Kedro-Viz export is mounted at dashboard/kedro-viz/');
  }
  // Story 109.3: /marketplace/ is the generated site, mounted only while
  // pyforge.steward.marketplace_pages is on. Off, the prefix is absent.
  const marketplaceOn = marketplacePagesEnabled(repoRoot, env.PYFORGE_ENVIRONMENT || 'dev');
  const marketplaceFiles = all.filter((rel) => rel.startsWith('marketplace/'));
  if (marketplaceOn) {
    if (!has('marketplace/index.html') || !has('marketplace/marketplace.json')) {
      out.push('pyforge.steward.marketplace_pages is on but marketplace/index.html or marketplace/marketplace.json is missing');
    } else {
      let manifest: { name?: string; plugins?: { source?: { source?: string; url?: string; path?: string } }[] } | null = null;
      try {
        manifest = JSON.parse(read('marketplace/marketplace.json'));
      } catch {
        manifest = null;
      }
      const plugin = manifest?.plugins?.[0]?.source;
      if (manifest?.name !== 'pyforge-bmad-marketplace' || plugin?.source !== 'git-subdir' || !plugin.url || !plugin.path) {
        out.push('marketplace/marketplace.json is not the URL form (name pyforge-bmad-marketplace, plugin source git-subdir with url and path)');
      }
    }
  } else if (marketplaceFiles.length) {
    out.push('marketplace/ exists in the artifact but pyforge.steward.marketplace_pages is off');
  }

  if (mounted.includes('vizro')) {
    let manifest: unknown = null;
    try {
      manifest = JSON.parse(read('dashboard/vizro/manifest.json'));
    } catch {
      manifest = null;
    }
    if (!has('dashboard/vizro/index.html') || typeof manifest !== 'object' || manifest === null || Array.isArray(manifest)) {
      out.push('dashboard/vizro/ lacks index.html or a manifest.json object');
    }
  }

  // The frozen legacy redirects land on their targets (Story 43.3; the operator ruling of 2026-10-13).
  const legacy = (JSON.parse(fs.readFileSync(REDIRECTS_JSON, 'utf8')) as { legacy: Record<string, string> }).legacy;
  for (const [from, to] of Object.entries(legacy)) {
    const rel = from.replace(/^\//, '');
    const target = has(rel) ? REFRESH_URL.exec(read(rel))?.[1] ?? '' : '';
    const landed = target ? resolveLink(root, rel, target, base) : null;
    if (!landed || !('file' in landed) || landed.file !== path.join(root, to.replace(/^\//, ''))) {
      out.push(`legacy redirect ${from} does not land on ${to}`);
    }
  }

  // The machine-read documents parse (Story 43.6's review).
  if (has('changes/rss.xml')) {
    const feed = read('changes/rss.xml');
    if (!wellFormed(feed) || !/<rss version="2\.0">/.test(feed) || (feed.match(/<channel>/g) ?? []).length !== 1) {
      out.push('changes/rss.xml is not a well-formed RSS 2.0 document with one channel');
    }
  }
  if (has('facts.json')) {
    let facts: unknown = null;
    try {
      facts = JSON.parse(read('facts.json'));
    } catch {
      facts = null;
    }
    if (typeof facts !== 'object' || facts === null || Array.isArray(facts)) {
      out.push('facts.json is not a JSON object keyed by deck');
    }
  }

  // Every page of the build: one CSP allowing the page's own scripts, one built-from line naming one build, every
  // local link resolving.
  const pages = all.filter((rel) => rel.endsWith('.html') && !NOT_PAGES.some((prefix) => rel.startsWith(prefix)));
  const builds = new Set<string>();
  const menus = new Map<string, string[]>();
  let shelfPages = 0;
  for (const rel of pages) {
    const html = read(rel);
    if (isStub(html)) {
      continue;
    }
    const csp = (html.match(CSP_META) ?? []).length;
    if (csp !== 1) {
      out.push(`${rel} carries ${csp} Content-Security-Policy metas, not one`);
    } else {
      out.push(...blockedScripts(html).map((line) => `${rel} carries ${line}`));
    }
    const lines = [...html.matchAll(BUILT_FROM)].map((m) => m[1]);
    if (lines.length !== 1) {
      out.push(`${rel} carries ${lines.length} built-from lines, not one`);
    }
    lines.forEach((line) => builds.add(line));
    out.push(...javascriptUrls(html).map((line) => `${rel} carries ${line}`));
    for (const raw of urls(html)) {
      const landed = resolveLink(root, rel, raw, base);
      if (landed && 'problem' in landed) {
        out.push(`broken link: ${rel} -> ${JSON.stringify(raw)} (${landed.problem})`);
      }
    }
    if (html.includes('sl-markdown-content')) {
      shelfPages += 1;
      if (!shelfBodyHasWords(html)) {
        out.push(`empty shelf page body: ${rel}`);
      }
    }
    if (!readerPage(rel)) {
      const links = menuLinks(html);
      menus.set(rel, links.map(([label]) => label));
      for (const [, href] of links) {
        const landed = resolveLink(root, rel, href, base);
        if (!landed || !('file' in landed) || !href.split('#')[0].trim()) {
          out.push(`menu link lands on no file of the artifact: ${rel} -> ${JSON.stringify(href)}`);
        }
      }
    }
    if (rel.startsWith('herald/') && /<style\b[^>]*>[^<]*(?<![\w-])--[\w-]+\s*:/i.test(html)) {
      out.push(`${rel} carries an inline theme (a custom property in a <style> of its own)`);
    }
  }
  if (builds.size > 1) {
    out.push(`the pages name ${builds.size} builds: ${[...builds].sort().join(' | ')}`);
  }
  if (!shelfPages) {
    out.push('no shelf page found (no page carries the docs shelf body, sl-markdown-content)');
  }

  // One menu (the registry's, CAP-58) on every navigable page, as the docs root shows it.
  const expected = menus.get('index.html') ?? [];
  if (!expected.length) {
    out.push('index.html carries no top menu');
  }
  for (const [rel, labels] of menus) {
    if (labels.join('\u0000') !== expected.join('\u0000')) {
      out.push(`the menu on ${rel} reads ${JSON.stringify(labels)}, the docs root's ${JSON.stringify(expected)}`);
    }
  }

  // Faces come from the bundle (Story 43.4): every @font-face source in the site's stylesheets is a file under _astro/.
  for (const rel of all.filter((r) => r.endsWith('.css') && (r.startsWith('_astro/') || r.startsWith('herald/')))) {
    for (const face of read(rel).match(/@font-face\s*\{[^}]*\}/gi) ?? []) {
      for (const [, , url] of face.matchAll(/url\(\s*(["']?)([^)"']+)\1\s*\)/gi)) {
        if (url.startsWith('data:')) {
          continue;
        }
        const landed = resolveLink(root, rel, url, base);
        if (!landed || !('file' in landed) || !path.relative(root, landed.file).startsWith('_astro')) {
          out.push(`${rel} loads a face ${JSON.stringify(url)} that is not a file under _astro/`);
        }
      }
    }
  }

  // Nothing loads from another origin (AD-21, CAP-56): scripts/origin_check.py, the vendored paths exempt by name.
  if (options.origins !== false) {
    const python = env.HERALD_PYTHON || 'python';
    const args = [path.join(DOCS_SITE, 'scripts', 'origin_check.py'), root, siteOrigin(siteUrl), siteOrigin(publicSiteUrl(env)), ...Object.keys(VENDORED)];
    const done = spawnSync(python, args, { encoding: 'utf8', env: { ...env } });
    if (done.error || done.status !== 0) {
      const said = `${done.stdout ?? ''}${done.stderr ?? ''}`.split('\n').filter(Boolean);
      out.push(...(said.length ? said : [`the origin check could not run (${python}): ${done.error ?? `exit ${done.status}`}`]));
    }
  }
  return out;
}

/** `[label, href]` of each link of a page's top menu (`data-pf-menu-link` anchors), in order. */
export function menuLinks(html: string): Array<[string, string]> {
  const menu = /<a\b((?=[^>]*\bdata-pf-menu-link\b)[^>]*)>\s*([^<]*?)\s*<\/a>/gi;
  return [...html.matchAll(menu)].map((m) => [unescapeAttr(m[2]), attributes(m[1]).href ?? '']);
}

/** The labels of a page's top menu, in order. */
export function menuLabels(html: string): string[] {
  return menuLinks(html).map(([label]) => label);
}

/** The words of a shelf page's markdown container (Story 44.1: its body must not render empty). */
function shelfBodyHasWords(html: string): boolean {
  const start = html.search(/<div\b[^>]*class=["'][^"']*\bsl-markdown-content\b/);
  if (start < 0) {
    return true;
  }
  let depth = 0;
  let text = '';
  let last = start;
  for (const m of html.slice(start).matchAll(/<(\/?)div\b[^>]*>/gi)) {
    const at = start + (m.index ?? 0);
    if (depth > 0) {
      text += html.slice(last, at);
    }
    depth += m[1] ? -1 : 1;
    last = at + m[0].length;
    if (depth === 0) {
      break;
    }
  }
  return /\w/.test(text.replace(/<[^>]+>/g, ' '));
}

function main(argv: string[]): number {
  const [verb, ...rest] = argv;
  const rootFlag = rest.indexOf('--root');
  const root = rootFlag >= 0 ? path.resolve(rest[rootFlag + 1]) : ARTIFACT;
  if (verb === 'build') {
    console.log(`pages-build: ${ARTIFACT} built for ${build()}`);
    return 0;
  }
  if (verb !== 'check') {
    console.error('usage: node scripts/pages.mts build | check [--root DIR]');
    return 2;
  }
  for (const [rel, reason] of Object.entries(VENDORED)) {
    console.log(`pages-check: exempt vendored ${rel.endsWith('/') ? 'root' : 'file'} ${rel} (AD-21 rule 5: ${reason})`);
  }
  const findings = check(root);
  for (const line of findings) {
    console.error(`pages-check: ${line}`);
  }
  if (findings.length) {
    console.error(`pages-check: ${findings.length} finding(s)`);
    return 1;
  }
  console.log(`pages-check: ${root} passes`);
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main(process.argv.slice(2)));
}
