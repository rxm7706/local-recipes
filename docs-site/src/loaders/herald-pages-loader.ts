/**
 * Loads the herald overview, gallery and deck-family pages' data at build time (Story 43.2, CAP-61):
 * `docsite/content/site.yml` and each `presentations/<slug>/facts.yaml` parsed here, the rest read by
 * `src/lib/herald-pages.ts` -- all in place, nothing copied or edited.
 *
 * `HERALD_PAGES_REPO_ROOT` points the loader at another tree (the parity test's fixtures), as
 * `docsite/build.py --repo-root` does for the Jinja path; unset, it is this repository.
 */

import fs from 'node:fs';
import path from 'node:path';

import { parse as parseYaml } from 'yaml';

import {
  builtAt,
  collectFamilies,
  collectInfographics,
  gitCommit,
  neighbours,
  type Family,
  type FamilyFacts,
  type Infographic,
  type SiteConfig,
} from '../lib/herald-pages.ts';

export interface HeraldPages {
  site: SiteConfig;
  neighbours: Array<Record<string, unknown>>;
  infographics: Infographic[];
  families: Family[];
  commit: string;
  builtAt: string;
}

/** `pyforge.herald.pages_one_generator` (Story 43.1), read by the docs-site's one flag reader (`src/lib/flags.ts`). */
export { pagesOneGenerator } from '../lib/flags.ts';

/**
 * The tree the pages read: `HERALD_PAGES_REPO_ROOT`, else the repository holding the build's working
 * directory (`docs-site/`). Not this module's own URL: the build bundles pages into `.astro/` chunks.
 */
export function heraldPagesRoot(): string {
  const override = process.env.HERALD_PAGES_REPO_ROOT;
  if (override) {
    return path.resolve(override);
  }
  for (let dir = process.cwd(); ; dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, 'pixi.toml')) && fs.existsSync(path.join(dir, 'docsite', 'content', 'site.yml'))) {
      return dir;
    }
    if (path.dirname(dir) === dir) {
      throw new Error(`no repository with docsite/content/site.yml above ${process.cwd()}`);
    }
  }
}

function readFacts(repoRoot: string, slug: string): FamilyFacts | null {
  const file = path.join(repoRoot, 'presentations', slug, 'facts.yaml');
  if (!fs.existsSync(file)) {
    return null;
  }
  const data = parseYaml(fs.readFileSync(file, 'utf8')) as Record<string, unknown> | null;
  const facts = Array.isArray(data?.facts) ? data.facts : [];
  return { count: facts.length, derivedAt: String(data?.derived_at ?? '') };
}

let loaded: HeraldPages | null = null;

/** The pages' data, read once per build. Throws (failing the build) on a second current export of a kind. */
export function loadHeraldPages(): HeraldPages {
  if (loaded) {
    return loaded;
  }
  const repoRoot = heraldPagesRoot();
  const site = parseYaml(fs.readFileSync(path.join(repoRoot, 'docsite/content/site.yml'), 'utf8')) as SiteConfig;
  const commit = gitCommit(repoRoot);
  const infographics = collectInfographics(site, repoRoot);
  loaded = {
    site,
    neighbours: neighbours(site, repoRoot),
    infographics,
    families: collectFamilies(infographics, repoRoot, commit, (slug) => readFacts(repoRoot, slug)),
    commit,
    builtAt: builtAt(),
  };
  return loaded;
}
