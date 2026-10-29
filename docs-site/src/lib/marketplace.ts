/**
 * The marketplace mount (steward Story 109.3, spec-pyforge-steward CAP-171): what `scripts/populate-public.mts`
 * copies to `marketplace/` while `pyforge.steward.marketplace_pages` is on -- read as `PYFORGE_MARKETPLACE_PAGES`
 * through `src/lib/flags.ts`, the build's one flag reader, exported by `python -m pyforge.steward.marketplace_pages
 * --flag-env` beside herald's `pages_env` lines -- and what `scripts/pages.mts check` holds the mount to, as pure
 * functions the herald tests run over fixture trees. Node builtins only.
 *
 * - every file of `docs/foundry/marketplace/site/` (the generated index, listings, cards and the URL-form
 *   `marketplace.json`), the last with its public git URL rewritten to the deploying host's
 *   (`GITHUB_SERVER_URL` / `GITHUB_REPOSITORY`, so an enterprise mirror's deploy points at itself), and the cards
 *   with the two forms the renderer emits rewritten the same way: the clone URL and the public repository's
 *   `blob/main/` links, the latter to the deployed commit (`GITHUB_SHA`) on that host;
 * - of each `skills/<scope>/<slug>/` folder only `SKILL.md`, `steps.md`, `listing.yaml` and text files under
 *   `references/` (the review of 2026-10-28, row 9; loop 3, row 48: the suffix set and the two size caps are the
 *   validator's, `pyforge.steward.marketplace_pages`): a dotfile, a cache, a binary or a stray file in a
 *   contribution never ships, and a file or folder over its cap fails the build. The release zips in
 *   `.github/workflows/pages.yml` carry the same set.
 */

import fs from 'node:fs';
import path from 'node:path';

/** The public clone URL `site/marketplace.json` is rendered with (`pyforge.steward.catalog.PUBLIC_MARKETPLACE_GIT_URL`). */
export const PUBLIC_MARKETPLACE_GIT_URL = 'https://github.com/rxm7706/local-recipes.git';
/** The marketplace tree, relative to the repository root. */
export const MARKETPLACE_DIR = 'docs/foundry/marketplace';
/** The Claude marketplace file's `name` (`pyforge.steward.catalog.MARKETPLACE_NAME`). */
export const MARKETPLACE_NAME = 'pyforge-bmad-marketplace';
/** The files at a skill folder's root that ship. */
export const SKILL_FILES: readonly string[] = ['SKILL.md', 'steps.md', 'listing.yaml'];
/** The one subdirectory of a skill folder that ships. */
export const SKILL_REFERENCES_DIR = 'references';
/** What a file under `references/` may be (`pyforge.steward.marketplace_pages.SHIPPED_TEXT_SUFFIXES`). */
export const SHIPPED_TEXT_SUFFIXES: readonly string[] = ['.md', '.txt', '.yaml', '.yml', '.json'];
/** One shipped file's cap in bytes (`MAX_SHIPPED_FILE_BYTES`). */
export const MAX_SHIPPED_FILE_BYTES = 1048576;
/** A skill folder's cap in bytes (`MAX_SHIPPED_FOLDER_BYTES`). */
export const MAX_SHIPPED_FOLDER_BYTES = 4194304;
/** Each kind's card directory under the site root (`pyforge.steward.marketplace_pages.KIND_DIRS`). */
export const KIND_DIRS: Readonly<Record<string, string>> = { skill: 'skills', module: 'modules', agent: 'agents', bundle: 'bundles' };
/** `scope` and `slug`, as `pyforge.steward.marketplace_pages.SLUG` holds them: a folder outside it never mounts. */
export const SLUG = /^[a-z0-9][a-z0-9-]*$/;
/** The listings document's schema (`pyforge.steward.marketplace_pages.SCHEMA_ID`). */
export const SCHEMA_ID = 'pyforge.bmad-marketplace/v1';

type Env = Record<string, string | undefined>;

/** `rel`, a `/`-joined path inside a skill folder, is one the mount and the release zip carry. */
export function isShippedSkillFile(rel: string): boolean {
  const parts = rel.split('/');
  if (parts.some((part) => !part || part.startsWith('.'))) {
    return false;
  }
  if (parts.length === 1) {
    return SKILL_FILES.includes(parts[0]);
  }
  const suffix = path.posix.extname(parts[parts.length - 1]).toLowerCase();
  return parts[0] === SKILL_REFERENCES_DIR && SHIPPED_TEXT_SUFFIXES.includes(suffix);
}

/** The public repository URL the cards link documents under (`REPOSITORY_BLOB_URL`'s root). */
export const PUBLIC_REPOSITORY_URL = PUBLIC_MARKETPLACE_GIT_URL.replace(/\.git$/, '');
/** The card's repository links, as `pyforge.steward.marketplace_pages.REPOSITORY_BLOB_URL` renders them. */
export const PUBLIC_BLOB_URL = `${PUBLIC_REPOSITORY_URL}/blob/main/`;

/** The public clone URL as a whole token: a URL it merely begins (`…/local-recipes.github.io/…`) is another link
 * (loop 6, row 106). A trailing `.` ends a sentence, not the URL. */
const PUBLIC_CLONE_URL_TOKEN = new RegExp(
  PUBLIC_MARKETPLACE_GIT_URL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![A-Za-z0-9_~/?#%-])',
  'g',
);
/** The shapes GitHub Actions gives the three names the rewrite splices into every card's links (loop 6, row 106: an
 * unvalidated `GITHUB_SHA` such as `abc"onmouseover="…` became markup inside each `href`). */
const DEPLOY_SERVER = /^https?:\/\/[A-Za-z0-9.-]+(?::\d+)?(?:\/[A-Za-z0-9._~-]+)*$/;
const DEPLOY_REPOSITORY = /^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/;
const DEPLOY_SHA = /^[0-9a-f]{7,64}$/;

/** `marketplace.json` and the cards for the host that runs the build: GitHub Actions names it, and exactly the two
 * forms the renderer emits are replaced, the public clone URL and the public repository's `blob/main/` links (loop 4,
 * row 76: a card links the README, the checklist and the tool matrix, which the mount does not carry). A `blob/main/`
 * link moves to the deployed commit when `GITHUB_SHA` is set (loop 5, row 89: `main` on a mirror may not hold the
 * targets, or exist), and any other repository link on a runbook -- an issue, the bare repository URL, a URL the
 * clone URL only begins -- is left as it is (rows 88 and 106). A server, repository or commit outside the shape
 * Actions sets throws: the build fails rather than ship cards with a malformed or injected link (row 106). */
export function rewriteMarketplaceGitUrl(text: string, env: Env = process.env): string {
  const server = (env.GITHUB_SERVER_URL ?? '').trim().replace(/\/+$/, '');
  const repo = (env.GITHUB_REPOSITORY ?? '').trim();
  if (!server || !repo) {
    return text;
  }
  const sha = (env.GITHUB_SHA ?? '').trim();
  if (!DEPLOY_SERVER.test(server)) {
    throw new Error(`GITHUB_SERVER_URL ${JSON.stringify(server)} is not an http(s) origin; refusing to rewrite the marketplace links`);
  }
  if (!DEPLOY_REPOSITORY.test(repo)) {
    throw new Error(`GITHUB_REPOSITORY ${JSON.stringify(repo)} is not owner/name; refusing to rewrite the marketplace links`);
  }
  if (sha && !DEPLOY_SHA.test(sha)) {
    throw new Error(`GITHUB_SHA ${JSON.stringify(sha)} is not a commit hash; refusing to rewrite the marketplace links`);
  }
  const blob = `${server}/${repo}/blob/${sha || 'main'}/`;
  return text.replace(PUBLIC_CLONE_URL_TOKEN, `${server}/${repo}.git`).split(PUBLIC_BLOB_URL).join(blob);
}

export interface MountedFile {
  /** Relative to the `marketplace/` mount, `/`-joined. */
  rel: string;
  data: Buffer;
}

/** Every regular file under `dir`, `/`-joined and sorted; a symlink (file or directory) never mounts, so nothing
 * outside the tree is read (the review of 2026-10-28, loop 2, row 23). */
function filesUnder(dir: string): string[] {
  if (!fs.existsSync(dir) || fs.lstatSync(dir).isSymbolicLink() || !fs.statSync(dir).isDirectory()) {
    return [];
  }
  const out: string[] = [];
  const walk = (sub: string): void => {
    for (const entry of fs.readdirSync(sub, { withFileTypes: true })) {
      const abs = path.join(sub, entry.name);
      if (entry.isSymbolicLink()) {
        continue;
      }
      if (entry.isDirectory()) {
        walk(abs);
      } else if (entry.isFile()) {
        out.push(path.relative(dir, abs).split(path.sep).join('/'));
      }
    }
  };
  walk(dir);
  return out.sort();
}

/** The files the mount writes under `marketplace/`, in order, from the marketplace tree at `marketplaceDir`. */
export function marketplaceMount(marketplaceDir: string, env: Env = process.env): MountedFile[] {
  const out: MountedFile[] = [];
  const site = path.join(marketplaceDir, 'site');
  for (const rel of filesUnder(site)) {
    let data = fs.readFileSync(path.join(site, rel));
    if (rel === 'marketplace.json' || rel.endsWith('.html')) {
      data = Buffer.from(rewriteMarketplaceGitUrl(data.toString('utf8'), env), 'utf8');
    }
    out.push({ rel, data });
  }
  const skills = path.join(marketplaceDir, 'skills');
  const totals = new Map<string, number>();
  for (const rel of filesUnder(skills)) {
    const [scope, slug, ...rest] = rel.split('/');
    if (!scope || !slug || !SLUG.test(scope) || !SLUG.test(slug) || !rest.length || !isShippedSkillFile(rest.join('/'))) {
      continue;
    }
    const data = fs.readFileSync(path.join(skills, rel));
    // the validator's caps (loop 3, row 48): a folder past them fails the build rather than ships a slimmed copy
    if (data.length > MAX_SHIPPED_FILE_BYTES) {
      throw new Error(`skills/${rel} is ${data.length} bytes; one shipped file is at most ${MAX_SHIPPED_FILE_BYTES}`);
    }
    const key = `${scope}/${slug}`;
    const total = (totals.get(key) ?? 0) + data.length;
    if (total > MAX_SHIPPED_FOLDER_BYTES) {
      throw new Error(`skills/${key} ships over ${MAX_SHIPPED_FOLDER_BYTES} bytes; the cap is ${MAX_SHIPPED_FOLDER_BYTES}`);
    }
    totals.set(key, total);
    out.push({ rel: `skills/${rel}`, data });
  }
  return out;
}

const SKILL_FOLDER_PATH = /^marketplace\/skills\/([^/]+)\/([^/]+)\/(.+)$/;
const CARD_PATH = /^marketplace\/skills\/([^/]+)\/([^/]+)\.html$/;
/** The non-skill kinds' card directories, from the one map (loop 4, row 72: a kind added to `KIND_DIRS` is admitted). */
export const OTHER_CARD_DIRS: readonly string[] = Object.keys(KIND_DIRS)
  .filter((kind) => kind !== 'skill')
  .map((kind) => KIND_DIRS[kind]);
const OTHER_CARD_PATH = new RegExp(`^marketplace/(${OTHER_CARD_DIRS.join('|')})/([^/]+)\\.html$`);
const SITE_DOCUMENTS = ['marketplace/index.html', 'marketplace/listings.json', 'marketplace/marketplace.json'];

type ListingRow = { id?: unknown; kind?: unknown; scope?: unknown; slug?: unknown; name?: unknown };

/** A listing row's card path relative to the artifact root, or `null` when the row is not a well-formed row. */
function listingCard(row: unknown): string | null {
  if (!row || typeof row !== 'object') {
    return null;
  }
  const { id, kind, scope, slug, name } = row as ListingRow;
  // Object.hasOwn: `kind in KIND_DIRS` admits `constructor` and the other prototype names (loop 4, row 72)
  if (typeof id !== 'string' || typeof kind !== 'string' || !Object.hasOwn(KIND_DIRS, kind)) {
    return null;
  }
  if (kind === 'skill') {
    if (typeof scope !== 'string' || typeof slug !== 'string' || !SLUG.test(scope) || !SLUG.test(slug) || id !== `${scope}/${slug}`) {
      return null;
    }
    return `marketplace/skills/${scope}/${slug}.html`;
  }
  const leaf = typeof slug === 'string' ? slug : typeof name === 'string' ? name : '';
  return SLUG.test(leaf) ? `marketplace/${KIND_DIRS[kind]}/${leaf}.html` : null;
}

/**
 * The converse of {@link marketplaceManifestFindings} (loop 2, row 27; loop 3, row 48): the artifact held to the
 * listings and the manifest. `marketplace/listings.json` parses with this schema and well-formed rows; every listed
 * skill has its folder, its card and its plugin, and every other listing its card; every mounted skill folder and
 * card is a listing and a plugin; every mounted skill file is one the folder ships and under the file cap; nothing
 * else sits under `marketplace/`; no plugin name repeats. `all` is the artifact's file list, `/`-joined and relative
 * to its root; `sizeOf` gives a file's bytes (absent, the caps are not judged).
 */
export function marketplaceArtifactFindings(
  listingsText: string,
  manifestText: string,
  all: string[],
  sizeOf?: (rel: string) => number,
): string[] {
  const out: string[] = [];
  const listed = new Set<string>();
  const otherCards = new Set<string>();
  const seenIds = new Set<string>();
  try {
    const doc = JSON.parse(listingsText) as { schema?: unknown; listings?: unknown };
    if (doc.schema !== SCHEMA_ID) {
      out.push(`marketplace/listings.json: schema is not ${SCHEMA_ID}`);
    }
    if (Array.isArray(doc.listings)) {
      doc.listings.forEach((row, index) => {
        const card = listingCard(row);
        if (!card) {
          out.push(`marketplace/listings.json: listing ${index} is not a well-formed row (id, kind, scope/slug or name)`);
          return;
        }
        // a doubled row is a finding here too (loop 4, row 73): the render refuses a duplicate id, the artifact must;
        // each half names what repeats (loop 5, row 91: two ids on one card said the id repeated)
        const id = (row as ListingRow).id as string;
        if (seenIds.has(id)) {
          out.push(`marketplace/listings.json: id ${id} repeats (card ${card})`);
          return;
        }
        // a well-formed skill row's card is its id, so only another kind's card can repeat under a second id
        if (otherCards.has(card)) {
          out.push(`marketplace/listings.json: card ${card} repeats (id ${id})`);
          return;
        }
        seenIds.add(id);
        if ((row as ListingRow).kind === 'skill') {
          listed.add(`${(row as ListingRow).scope}/${(row as ListingRow).slug}`);
        } else {
          otherCards.add(card);
        }
      });
    } else {
      out.push('marketplace/listings.json: listings is not a list');
    }
  } catch {
    out.push('marketplace/listings.json is not JSON');
  }
  let plugins: Set<string> | null = null;
  try {
    const doc = JSON.parse(manifestText) as { plugins?: unknown };
    if (Array.isArray(doc.plugins)) {
      const names = (doc.plugins as Array<{ name?: unknown; source?: { path?: unknown } }>).map((plugin) =>
        typeof plugin?.name === 'string' ? plugin.name : '',
      );
      const repeated = names.filter((name, index) => name && names.indexOf(name) !== index);
      for (const name of [...new Set(repeated)]) {
        out.push(`marketplace/marketplace.json: plugin name ${name} repeats`);
      }
      plugins = new Set(
        (doc.plugins as Array<{ source?: { path?: unknown } }>)
          .map((plugin) => (typeof plugin?.source === 'object' && typeof plugin.source?.path === 'string' ? plugin.source.path : ''))
          .map((p) => p.replace(/^docs\/foundry\/marketplace\/skills\//, ''))
          .filter(Boolean),
      );
    }
    // plugins not a list: marketplaceManifestFindings names it once; no per-folder finding on top (row 48)
  } catch {
    // marketplaceManifestFindings names a manifest that is not JSON
  }
  const folders = new Set<string>();
  const cards = new Set<string>();
  const mountedOtherCards = new Set<string>();
  const folderBytes = new Map<string, number>();
  for (const rel of all) {
    if (!rel.startsWith('marketplace/')) {
      continue;
    }
    if (SITE_DOCUMENTS.includes(rel)) {
      continue;
    }
    const folder = SKILL_FOLDER_PATH.exec(rel);
    if (folder) {
      const [, scope, slug, inside] = folder;
      folders.add(`${scope}/${slug}`);
      if (!SLUG.test(scope) || !SLUG.test(slug) || !isShippedSkillFile(inside)) {
        out.push(
          `${rel} is mounted but is not a file a skill folder ships (SKILL.md, steps.md, listing.yaml, text files under references/)`,
        );
      } else if (sizeOf) {
        const bytes = sizeOf(rel);
        if (bytes > MAX_SHIPPED_FILE_BYTES) {
          out.push(`${rel} is mounted but is over ${MAX_SHIPPED_FILE_BYTES} bytes`);
        }
        folderBytes.set(`${scope}/${slug}`, (folderBytes.get(`${scope}/${slug}`) ?? 0) + bytes);
      }
      continue;
    }
    const card = CARD_PATH.exec(rel);
    if (card) {
      cards.add(`${card[1]}/${card[2]}`);
      continue;
    }
    if (OTHER_CARD_PATH.test(rel)) {
      mountedOtherCards.add(rel);
      continue;
    }
    out.push(`${rel} is mounted under marketplace/ but is not a site document, a card or a skill folder file`);
  }
  // the validator's folder cap, held at the artifact too (loop 4, row 75)
  for (const [key, bytes] of [...folderBytes].sort()) {
    if (bytes > MAX_SHIPPED_FOLDER_BYTES) {
      out.push(`marketplace/skills/${key}/ is mounted but ships ${bytes} bytes; the cap is ${MAX_SHIPPED_FOLDER_BYTES}`);
    }
  }
  for (const key of [...new Set([...folders, ...cards])].sort()) {
    if (!listed.has(key)) {
      out.push(`marketplace/skills/${key} is mounted but marketplace/listings.json lists no skill ${key}`);
    }
    if (plugins && !plugins.has(key)) {
      out.push(`marketplace/skills/${key} is mounted but marketplace/marketplace.json has no plugin for it`);
    }
  }
  for (const key of [...listed].sort()) {
    if (!folders.has(key)) {
      out.push(`marketplace/listings.json lists skill ${key} but marketplace/skills/${key}/ is not mounted`);
    }
    if (!cards.has(key)) {
      out.push(`marketplace/listings.json lists skill ${key} but marketplace/skills/${key}.html is not mounted`);
    }
    if (plugins && !plugins.has(key)) {
      out.push(`marketplace/listings.json lists skill ${key} but marketplace/marketplace.json has no plugin for it`);
    }
  }
  for (const card of [...otherCards].sort()) {
    if (!mountedOtherCards.has(card)) {
      out.push(`marketplace/listings.json lists a card at ${card} but it is not mounted`);
    }
  }
  for (const card of [...mountedOtherCards].sort()) {
    if (!otherCards.has(card)) {
      out.push(`${card} is mounted but marketplace/listings.json lists no such card`);
    }
  }
  return out;
}

const GIT_URL = /^https:\/\/[^/\s]+\/[^/\s]+\/[^/\s]+\.git$/;
/** The rolling release's own asset stem (`pyforge.steward.pages.RELEASE_TAG`): never a plugin name (loop 4, row 60). */
export const RELEASE_ASSET_STEM = 'pages-site';
const PLUGIN_PATH = /^docs\/foundry\/marketplace\/skills\/([^/]+)\/([^/]+)$/;

/**
 * What `pages-check` holds `marketplace/marketplace.json` to while the flag is on: the URL form (`name`, each plugin
 * a `git-subdir` source with an `https://<host>/<owner>/<repo>.git` url and a `docs/foundry/marketplace/skills/
 * <scope>/<slug>` path, named `<scope>-<slug>`), and every plugin's folder and card mounted. An empty `plugins`
 * list is a valid manifest. `has` answers whether the artifact holds a path.
 */
export function marketplaceManifestFindings(text: string, has: (rel: string) => boolean): string[] {
  let manifest: unknown;
  try {
    manifest = JSON.parse(text);
  } catch {
    return ['marketplace/marketplace.json is not JSON'];
  }
  const out: string[] = [];
  const doc = (manifest ?? {}) as { name?: unknown; plugins?: unknown };
  if (doc.name !== MARKETPLACE_NAME) {
    out.push(`marketplace/marketplace.json: name is not ${MARKETPLACE_NAME}`);
  }
  if (!Array.isArray(doc.plugins)) {
    out.push('marketplace/marketplace.json: plugins is not a list');
    return out;
  }
  type Plugin = { name?: unknown; source?: { source?: unknown; url?: unknown; path?: unknown } | string };
  (doc.plugins as Plugin[]).forEach((plugin, index) => {
    const label = `marketplace/marketplace.json plugin ${typeof plugin?.name === 'string' ? plugin.name : index}`;
    const source = plugin?.source;
    if (!source || typeof source !== 'object' || source.source !== 'git-subdir' || typeof source.url !== 'string' || typeof source.path !== 'string') {
      out.push(`${label}: source is not git-subdir with url and path (the URL form)`);
      return;
    }
    if (!GIT_URL.test(source.url)) {
      out.push(`${label}: url ${JSON.stringify(source.url)} is not https://<host>/<owner>/<repo>.git`);
    }
    const match = PLUGIN_PATH.exec(source.path);
    if (!match) {
      out.push(`${label}: path ${JSON.stringify(source.path)} is not docs/foundry/marketplace/skills/<scope>/<slug>`);
      return;
    }
    const [, scope, slug] = match;
    if (plugin.name !== `${scope}-${slug}`) {
      out.push(`${label}: name is not ${scope}-${slug}`);
    }
    if (plugin.name === RELEASE_ASSET_STEM) {
      out.push(`${label}: name is the site release's own asset (${RELEASE_ASSET_STEM}.zip)`);
    }
    for (const rel of [`marketplace/skills/${scope}/${slug}/SKILL.md`, `marketplace/skills/${scope}/${slug}.html`]) {
      if (!has(rel)) {
        out.push(`${label}: ${rel} is not mounted`);
      }
    }
  });
  return out;
}
