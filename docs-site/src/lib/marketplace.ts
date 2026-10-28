/**
 * The marketplace mount (steward Story 109.3, spec-pyforge-steward CAP-171): what `scripts/populate-public.mts`
 * copies to `marketplace/` while `pyforge.steward.marketplace_pages` is on -- read as `PYFORGE_MARKETPLACE_PAGES`
 * through `src/lib/flags.ts`, the build's one flag reader, exported by `python -m pyforge.steward.marketplace_pages
 * --flag-env` beside herald's `pages_env` lines -- and what `scripts/pages.mts check` holds the mount to, as pure
 * functions the herald tests run over fixture trees. Node builtins only.
 *
 * - every file of `docs/foundry/marketplace/site/` (the generated index, listings, cards and the URL-form
 *   `marketplace.json`), the last with its public git URL rewritten to the deploying host's
 *   (`GITHUB_SERVER_URL` / `GITHUB_REPOSITORY`, so an enterprise mirror's deploy points at itself);
 * - of each `skills/<scope>/<slug>/` folder only `SKILL.md`, `steps.md`, `listing.yaml` and `references/**`
 *   (the review of 2026-10-28, row 9): a dotfile, a cache or a stray file in a contribution never ships. The
 *   release zips in `.github/workflows/pages.yml` carry the same four.
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
  return parts[0] === SKILL_REFERENCES_DIR;
}

/** `marketplace.json` for the host that runs the build: GitHub Actions names it, and the public URL is replaced. */
export function rewriteMarketplaceGitUrl(text: string, env: Env = process.env): string {
  const server = (env.GITHUB_SERVER_URL ?? '').trim().replace(/\/+$/, '');
  const repo = (env.GITHUB_REPOSITORY ?? '').trim();
  if (!server || !repo) {
    return text;
  }
  return text.split(PUBLIC_MARKETPLACE_GIT_URL).join(`${server}/${repo}.git`);
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
    if (rel === 'marketplace.json') {
      data = Buffer.from(rewriteMarketplaceGitUrl(data.toString('utf8'), env), 'utf8');
    }
    out.push({ rel, data });
  }
  const skills = path.join(marketplaceDir, 'skills');
  for (const rel of filesUnder(skills)) {
    const [scope, slug, ...rest] = rel.split('/');
    if (!scope || !slug || !SLUG.test(scope) || !SLUG.test(slug) || !rest.length || !isShippedSkillFile(rest.join('/'))) {
      continue;
    }
    out.push({ rel: `skills/${rel}`, data: fs.readFileSync(path.join(skills, rel)) });
  }
  return out;
}

const SKILL_FOLDER_PATH = /^marketplace\/skills\/([^/]+)\/([^/]+)\/(.+)$/;
const CARD_PATH = /^marketplace\/skills\/([^/]+)\/([^/]+)\.html$/;

/**
 * The converse of {@link marketplaceManifestFindings} (loop 2, row 27): the artifact held to the manifest and the
 * listings. `marketplace/listings.json` parses with this schema; every mounted skill folder and card is a listing
 * and a plugin; every mounted skill file is one the folder ships; no plugin name repeats. `all` is the artifact's
 * file list, `/`-joined and relative to its root.
 */
export function marketplaceArtifactFindings(listingsText: string, manifestText: string, all: string[]): string[] {
  const out: string[] = [];
  let listed = new Set<string>();
  try {
    const doc = JSON.parse(listingsText) as { schema?: unknown; listings?: unknown };
    if (doc.schema !== SCHEMA_ID) {
      out.push(`marketplace/listings.json: schema is not ${SCHEMA_ID}`);
    }
    if (Array.isArray(doc.listings)) {
      listed = new Set(
        (doc.listings as Array<{ kind?: unknown; scope?: unknown; slug?: unknown }>)
          .filter((row) => row?.kind === 'skill' && typeof row.scope === 'string' && typeof row.slug === 'string')
          .map((row) => `${row.scope}/${row.slug}`),
      );
    } else {
      out.push('marketplace/listings.json: listings is not a list');
    }
  } catch {
    out.push('marketplace/listings.json is not JSON');
  }
  let plugins = new Set<string>();
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
  } catch {
    // marketplaceManifestFindings names a manifest that is not JSON
  }
  const mounted = new Set<string>();
  for (const rel of all) {
    const folder = SKILL_FOLDER_PATH.exec(rel);
    if (folder) {
      const [, scope, slug, inside] = folder;
      mounted.add(`${scope}/${slug}`);
      if (!isShippedSkillFile(inside)) {
        out.push(`${rel} is mounted but is not a file a skill folder ships (SKILL.md, steps.md, listing.yaml, references/**)`);
      }
      continue;
    }
    const card = CARD_PATH.exec(rel);
    if (card) {
      mounted.add(`${card[1]}/${card[2]}`);
    }
  }
  for (const key of [...mounted].sort()) {
    if (!listed.has(key)) {
      out.push(`marketplace/skills/${key} is mounted but marketplace/listings.json lists no skill ${key}`);
    }
    if (!plugins.has(key)) {
      out.push(`marketplace/skills/${key} is mounted but marketplace/marketplace.json has no plugin for it`);
    }
  }
  return out;
}

const GIT_URL = /^https:\/\/[^/\s]+\/[^/\s]+\/[^/\s]+\.git$/;
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
    for (const rel of [`marketplace/skills/${scope}/${slug}/SKILL.md`, `marketplace/skills/${scope}/${slug}.html`]) {
      if (!has(rel)) {
        out.push(`${label}: ${rel} is not mounted`);
      }
    }
  });
  return out;
}
