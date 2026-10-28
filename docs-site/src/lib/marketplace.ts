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

function filesUnder(dir: string): string[] {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    return [];
  }
  return fs
    .readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .map((rel) => rel.split(path.sep).join('/'))
    .filter((rel) => fs.statSync(path.join(dir, rel)).isFile())
    .sort();
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
    if (!scope || !slug || !rest.length || !isShippedSkillFile(rest.join('/'))) {
      continue;
    }
    out.push({ rel: `skills/${rel}`, data: fs.readFileSync(path.join(skills, rel)) });
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
