/**
 * The registry, read once per build (Story 43.7, CAP-61): `astro.config.mjs` takes the docs sidebar from here, and
 * the top menu (`components/SiteTitle.astro`, `layouts/Herald*.astro`) and the home's doors
 * (`components/MarkdownContent.astro`) take theirs, so all three list the same sections in the same order.
 *
 * The registry is `docs/map.yaml` (the herald tests point `HERALD_PAGES_REPO_ROOT` at a fixture tree, whose own
 * `docs/map.yaml` is read when it has one); the quadrant pages are judged against the shelf the build renders, this
 * repository's `docs/`. A mounted export is judged in the tree the build mounts from (`scripts/populate-public.mts`).
 */

import fs from 'node:fs';
import path from 'node:path';

import { parse as parseYaml } from 'yaml';

import { marketplacePages, siteShell, statusPages } from './flags.ts';
import {
  doors,
  framedSections,
  holdsAFile,
  type MapSection,
  type MenuItem,
  quadrantEntries,
  registry,
  sidebar,
  type SidebarGroup,
  siteSections,
  topMenu,
} from './nav.ts';
import { heraldPagesRoot, SITE_YML } from '../loaders/herald-pages-loader.ts';
import { repoRoot } from './agent-surface.ts';

export interface SiteNav {
  sections: MapSection[];
  menu: MenuItem[];
  sidebar: SidebarGroup[];
  doors: ReturnType<typeof doors>;
}

let loaded: SiteNav | null = null;

/** The flags a section can be gated on, by key. */
const FLAGS: Record<string, () => boolean> = {
  'pyforge.herald.status_pages': statusPages,
  'pyforge.steward.marketplace_pages': marketplacePages,
};

export function siteNav(): SiteNav {
  if (loaded) {
    return loaded;
  }
  const repo = repoRoot();
  const data = heraldPagesRoot();
  const fixture = path.join(data, 'docs', 'map.yaml');
  const file = fs.existsSync(fixture) ? fixture : path.join(repo, 'docs', 'map.yaml');
  const reg = registry(parseYaml(fs.readFileSync(file, 'utf8')), file);
  const presence = {
    mounted: (name: string) => holdsAFile(path.join(data, 'docs', 'dashboard', name)),
    flag: (key: string) => (FLAGS[key] ?? (() => false))(),
  };
  // Story 53.1 (CAP-63): what each door says is behind it is the site's own copy (`site.yml` `doors`), keyed by the
  // registry's section keys; the registry keeps its shape.
  const site = (parseYaml(fs.readFileSync(path.join(data, SITE_YML), 'utf8')) ?? {}) as { doors?: Record<string, string> };
  const about = site.doors ?? {};
  const published = siteSections(reg.sections, presence).map((section) =>
    typeof about[section.key] === 'string' ? { ...section, description: about[section.key] } : section,
  );
  // Story 53.3 (CAP-63): with the shell, the Kedro-Viz section links its framed page under the site header.
  const sections = siteShell() ? framedSections(published) : published;
  loaded = {
    sections,
    menu: topMenu(sections),
    sidebar: sidebar(reg, path.join(repo, 'docs'), presence, siteShell(), siteShell()),
    doors: doors(sections, quadrantEntries(reg.pages)),
  };
  return loaded;
}
