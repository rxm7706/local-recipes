/**
 * One registry orders every prefix of the site (Story 43.7, spec-pyforge-herald CAP-61 on doctor CAP-90; AD-21
 * amended 2026-10-14): `docs/map.yaml`'s `pages` give the docs sidebar its four quadrant groups, and its `sections`
 * give the docs sidebar, the top menu every page carries and the home's doors their entries, in `order`. The docs
 * shelf is the site root and no row: the renderer supplies its menu entry and its door first (CAP-58). Nothing else
 * lists a menu -- `site.yml`'s `nav` retired with `docs-site/scripts/sidebar_from_map.py`, which this replaces.
 *
 * Two kinds of section show only when what they link exists in this build:
 * - a section whose `href` is a mounted export (`dashboard/kedro-viz/`, `dashboard/vizro/`) only when that export is
 *   in the build input, `docs/dashboard/<name>/` holding a file (the rule `scripts/populate-public.mts` mounts by);
 * - a section a flag owns (`status`, `pyforge.herald.status_pages`) only with that flag on.
 *
 * Pure functions over parsed data: YAML is parsed by the caller (`astro.config.mjs` and `scripts/nav-check.mts`, with
 * the `yaml` package), so the herald tests import this module with node's type stripping and no `node_modules`.
 */

import fs from 'node:fs';
import path from 'node:path';

export const QUADRANTS = ['tutorials', 'how-to', 'reference', 'explanation'] as const;
const QUADRANT_LABELS: Record<string, string> = {
  tutorials: 'Tutorials',
  'how-to': 'How-to',
  reference: 'Reference',
  explanation: 'Explanation',
};
/** The dashboard exports in `docs/dashboard/<name>/`, each mounted at `/dashboard/<name>/` only when present. */
export const DASHBOARD_EXPORTS = ['kedro-viz', 'vizro'];
/** The sections a flag owns, by key, and that flag's key (read through `src/lib/flags.ts`). */
export const FLAG_SECTIONS: Record<string, string> = { status: 'pyforge.herald.status_pages' };
/** The docs shelf's menu entry and door: the site root, first (CAP-58). */
export const DOCS_ENTRY = { key: 'docs', label: 'Docs', href: '' };

export interface MapPage {
  path: string;
  quadrant: string;
}

export interface MapEntry {
  key: string;
  label: string;
  href: string;
}

export interface MapSection extends MapEntry {
  owner: string;
  order: number;
  entries?: MapEntry[];
}

export interface Registry {
  pages: MapPage[];
  sections: MapSection[];
}

/** A menu link: `path` is relative to the site root (`''` is the docs root), so any base path can prefix it. */
export interface MenuItem {
  label: string;
  path: string;
  /** The registry section it belongs to. */
  section: string;
}

/** What decides the gated sections in one build. */
export interface Presence {
  /** `docs/dashboard/<name>/` holds a file. */
  mounted: (name: string) => boolean;
  /** A flag key's state. */
  flag: (key: string) => boolean;
}

/** `docs/map.yaml`, parsed, as the registry; refuses a map without `pages` or `sections`, naming the key. */
export function registry(data: unknown, file = 'docs/map.yaml'): Registry {
  const map = (data ?? {}) as Record<string, unknown>;
  for (const key of ['pages', 'sections']) {
    if (!Array.isArray(map[key])) {
      throw new Error(`${file}: no ${key} list (the registry every menu of the site reads; doctor CAP-90)`);
    }
  }
  return { pages: map.pages as MapPage[], sections: map.sections as MapSection[] };
}

/** A directory holding a file: the one presence rule for a mounted export (`scripts/populate-public.mts`). */
export function holdsAFile(dir: string): boolean {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    return false;
  }
  return fs
    .readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .some((rel) => fs.statSync(path.join(dir, rel)).isFile());
}

/** The export a section's `href` mounts, or `null`. */
export function mountOf(href: string): string | null {
  const match = /^dashboard\/([^/]+)\//.exec(href);
  return match && DASHBOARD_EXPORTS.includes(match[1]) ? match[1] : null;
}

/** The registry's sections this build publishes, in `order`. */
export function siteSections(sections: MapSection[], presence: Presence): MapSection[] {
  return [...sections]
    .sort((a, b) => a.order - b.order)
    .filter((section) => {
      const mount = mountOf(section.href);
      const flag = FLAG_SECTIONS[section.key];
      return (mount === null || presence.mounted(mount)) && (flag === undefined || presence.flag(flag));
    });
}

/** A section's links: its entries, or the section itself when it has none. */
function links(section: MapSection): MapEntry[] {
  return section.entries?.length ? section.entries : [section];
}

/** The top menu every page carries: the docs root, then each section's links, in the registry's order. */
export function topMenu(sections: MapSection[]): MenuItem[] {
  return [
    { label: DOCS_ENTRY.label, path: DOCS_ENTRY.href, section: DOCS_ENTRY.key },
    ...sections.flatMap((section) => links(section).map((entry) => ({ label: entry.label, path: entry.href, section: section.key }))),
  ];
}

/** The docs door's entries: each quadrant the map lists, in map order, at its index. */
export function quadrantEntries(pages: MapPage[]): MenuItem[] {
  const seen = [...new Set(pages.map((page) => page.quadrant))].filter((q) => (QUADRANTS as readonly string[]).includes(q));
  return seen.map((quadrant) => ({ label: QUADRANT_LABELS[quadrant], path: `${quadrant}/`, section: DOCS_ENTRY.key }));
}

/** The home's doors: the docs shelf (its quadrants), then one per section, each listing its entries. */
export function doors(sections: MapSection[], docs: MenuItem[] = []): Array<{ label: string; path: string; entries: MenuItem[] }> {
  return [
    { label: DOCS_ENTRY.label, path: DOCS_ENTRY.href, entries: docs },
    ...sections.map((section) => ({
      label: section.label,
      path: section.href,
      entries: (section.entries ?? []).map((entry) => ({ label: entry.label, path: entry.href, section: section.key })),
    })),
  ];
}

type SidebarItem = { label: string; link: string } | { slug: string };
export type SidebarGroup = { label: string; collapsed: boolean; items: SidebarItem[] } | { label: string; link: string };

/** The shelf collection id of a map path (`shelf-docs-loader.ts`'s `generateId`). */
function slug(rel: string): string {
  const id = rel.replace(/\.mdx?$/, '');
  return id.endsWith('/README') ? `${id.slice(0, -'/README'.length)}/index` : id;
}

/** Every `docs/<quadrant>/**.md` page but the quadrant's own README, relative to `docsDir`. */
function quadrantPagesOnDisk(docsDir: string): string[] {
  return QUADRANTS.flatMap((quadrant) => {
    const dir = path.join(docsDir, quadrant);
    if (!fs.existsSync(dir)) {
      return [];
    }
    return fs
      .readdirSync(dir, { recursive: true, encoding: 'utf8' })
      .filter((rel) => rel.endsWith('.md') && rel !== 'README.md')
      .map((rel) => `${quadrant}/${rel.split(path.sep).join('/')}`);
  });
}

/**
 * The four quadrant groups in map order, each its README's index link then its pages. Returns the defects instead
 * when the map and `docs/` disagree: a duplicate or path-less entry, an unknown quadrant, a mapped page missing on
 * disk, or a quadrant page the map does not list.
 */
export function quadrantGroups(pages: MapPage[], docsDir: string): { groups: SidebarGroup[]; errors: string[] } {
  const errors: string[] = [];
  const byQuadrant = new Map<string, string[]>();
  const seen = new Set<string>();
  for (const page of pages) {
    if (typeof page.path !== 'string' || !page.path) {
      errors.push('map entry missing path');
      continue;
    }
    if (seen.has(page.path)) {
      errors.push(`duplicate map entry: ${page.path}`);
      continue;
    }
    seen.add(page.path);
    if (!(QUADRANTS as readonly string[]).includes(page.quadrant)) {
      errors.push(`${page.path}: invalid quadrant`);
      continue;
    }
    byQuadrant.set(page.quadrant, [...(byQuadrant.get(page.quadrant) ?? []), page.path]);
  }
  for (const rel of [...seen].sort()) {
    if (!fs.existsSync(path.join(docsDir, rel))) {
      errors.push(`mapped page missing on disk: ${rel}`);
    }
  }
  for (const rel of quadrantPagesOnDisk(docsDir).sort()) {
    if (!seen.has(rel)) {
      errors.push(`quadrant page missing from map.yaml: ${rel}`);
    }
  }
  if (errors.length) {
    return { groups: [], errors };
  }
  const groups = [...byQuadrant].map(([quadrant, paths]) => ({
    label: QUADRANT_LABELS[quadrant],
    collapsed: false,
    items: [
      { link: `/${quadrant}/`, label: QUADRANT_LABELS[quadrant] },
      ...paths.filter((rel) => rel !== `${quadrant}/README.md`).map((rel) => ({ slug: slug(rel) })),
    ],
  }));
  return { groups, errors };
}

/** The sidebar's groups after the quadrants: one per section with entries, else one link. */
export function sectionGroups(sections: MapSection[]): SidebarGroup[] {
  return sections.map((section) =>
    section.entries?.length
      ? {
          label: section.label,
          collapsed: false,
          items: section.entries.map((entry) => ({ link: `/${entry.href}`, label: entry.label })),
        }
      : { label: section.label, link: `/${section.href}` },
  );
}

/** The whole docs sidebar: the quadrants, then the sections; throws listing every defect. */
export function sidebar(reg: Registry, docsDir: string, presence: Presence): SidebarGroup[] {
  const { groups, errors } = quadrantGroups(reg.pages, docsDir);
  if (errors.length) {
    throw new Error(`docs/map.yaml and docs/ disagree:\n  ${errors.join('\n  ')}`);
  }
  return [...groups, ...sectionGroups(siteSections(reg.sections, presence))];
}
