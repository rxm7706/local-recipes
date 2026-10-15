/**
 * The agent surface's build-time data (Story 43.6, spec-pyforge-herald CAP-61): the tracked files and the three
 * Guild-step inputs, read once per build and shaped by the pure functions in `agent-surface.ts`.
 *
 * - `/llms.txt`'s Docs section is `docs/map.yaml`'s `pages` (the shelf's registry), each page's title and text
 *   from the shelf collection; its Herald section is `docs/map.yaml`'s `herald` section entries (the nav
 *   registry, doctor CAP-90), each with the text herald renders there from tracked data: the site's blurb for the
 *   overview, the dossier's prose for the dossier (Story 43.1's collection), a pointer for the gallery and decks.
 * - `/facts.json` is every `presentations/<slug>/facts.yaml`, keyed by its deck.
 */

import fs from 'node:fs';
import path from 'node:path';

import { getCollection, getEntry } from 'astro:content';
import { parse as parseYaml } from 'yaml';

import {
  BuildInputShapeError,
  CHANGES_INPUT,
  CHANGES_WINDOW_DAYS,
  type Changes,
  factsDocument,
  flattenText,
  HERALD_PROGRESS_INPUT,
  type HeraldProgress,
  type Input,
  inputsDir,
  lane1Link,
  type LlmsSection,
  MARSHAL_STATUS_INPUT,
  type MarshalStatus,
  parseChanges,
  parseHeraldProgress,
  parseMarshalStatus,
  plainText,
  readInput,
  repoRoot,
  shelfId,
  shelfRoute,
  statusPages,
} from './agent-surface.ts';

interface MapPage {
  path: string;
}

interface MapEntry {
  key: string;
  label: string;
  href: string;
}

interface SiteYml {
  name: string;
  blurb?: string;
  lane1?: unknown;
}

function readYaml(root: string, rel: string): unknown {
  return parseYaml(fs.readFileSync(path.join(root, rel), 'utf8'));
}

export function siteYml(): SiteYml {
  return readYaml(repoRoot(), 'docsite/content/site.yml') as SiteYml;
}

/** The Lane 1 live-view link, or `null` while `site.yml`'s `lane1.href` is not an absolute URL. */
export function lane1(): { href: string; label: string } | null {
  return lane1Link(siteYml().lane1);
}

export function changesInput(): Input<Changes> {
  return readInput(inputsDir(repoRoot()), CHANGES_INPUT, parseChanges);
}

export function marshalStatusInput(): Input<MarshalStatus> {
  return readInput(inputsDir(repoRoot()), MARSHAL_STATUS_INPUT, parseMarshalStatus);
}

export function heraldProgressInput(): Input<HeraldProgress> {
  return readInput(inputsDir(repoRoot()), HERALD_PROGRESS_INPUT, parseHeraldProgress);
}

/** Every `presentations/<slug>/facts.yaml`, as `/facts.json` publishes it. */
export function facts(): Record<string, unknown> {
  const root = repoRoot();
  const presentations = path.join(root, 'presentations');
  const entries = fs
    .readdirSync(presentations, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(presentations, entry.name, 'facts.yaml')))
    .map((entry) => {
      const file = `presentations/${entry.name}/facts.yaml`;
      try {
        return { file, data: readYaml(root, file) };
      } catch (exc) {
        throw new BuildInputShapeError(`${file}: not valid YAML (${(exc as Error).message})`);
      }
    });
  return factsDocument(entries);
}

const HERALD_TEXT: Record<string, string> = {
  infographics:
    'The infographics gallery: every PyForge poster the site publishes, each on its own page. Each deck ' +
    "family's facts are in /facts.json.",
  decks:
    'The deck families: one page per deck with its infographic deck, executive summary, PPTX and Marp ' +
    'downloads. Each family is listed with its facts in /facts.json.',
};

/** `/llms.txt`'s sections, with each page's text for `/llms-full.txt`. `site` is the site URL with its base. */
export async function llmsSections(site: URL): Promise<{ title: string; summary: string; sections: LlmsSection[] }> {
  const root = repoRoot();
  const map = readYaml(root, 'docs/map.yaml') as { pages: MapPage[]; sections?: Array<{ key: string; entries?: MapEntry[] }> };
  const config = siteYml();
  const docs = new Map((await getCollection('docs')).map((entry) => [entry.id, entry]));
  const shelf = map.pages.map((page) => {
    const entry = docs.get(shelfId(page.path));
    if (!entry) {
      throw new Error(`docs/map.yaml page ${page.path} has no shelf page (collection id ${shelfId(page.path)})`);
    }
    const data = entry.data as { title: string; description?: string };
    return {
      title: data.title,
      url: new URL(shelfRoute(page.path), site).href,
      description: data.description,
      text: entry.body ?? '',
    };
  });

  const heraldSection = (map.sections ?? []).find((section) => section.key === 'herald');
  const dossier = await getEntry('dossier', 'dossier');
  const herald = (heraldSection?.entries ?? []).map((entry) => {
    let text = HERALD_TEXT[entry.key] ?? '';
    if (entry.key === 'overview') {
      text = plainText(config.blurb ?? '');
    } else if (entry.key === 'dossier') {
      if (!dossier) {
        throw new Error('the dossier collection entry is missing while PYFORGE_PAGES_ONE_GENERATOR=1');
      }
      text = flattenText(dossier.data).join('\n\n');
    }
    return { title: entry.label, url: new URL(entry.href, site).href, text };
  });

  const changes = changesInput();
  const windowDays = (changes.present ? changes.value.windowDays : null) ?? CHANGES_WINDOW_DAYS;
  const data = [
    {
      title: 'Deck facts',
      url: new URL('facts.json', site).href,
      description: 'every deck family\'s measured facts (presentations/<slug>/facts.yaml), keyed by deck',
    },
    {
      title: 'Changes',
      url: new URL('changes/', site).href,
      description: `merges to main in the last ${windowDays} days, newest first; RSS at changes/rss.xml`,
    },
    ...(statusPages()
      ? [
          { title: 'Fleet board', url: new URL('status/', site).href, description: 'one row per station, a build-time snapshot' },
          {
            title: 'Runs and progress',
            url: new URL('status/runs/', site).href,
            description: 'one row per loop home and the latest progress record per station, a build-time snapshot',
          },
        ]
      : []),
    {
      title: 'Full text',
      url: new URL('llms-full.txt', site).href,
      description: 'every page listed above with its text',
    },
  ];
  return {
    title: config.name,
    summary: config.blurb ?? '',
    sections: [
      { name: 'Docs', entries: shelf },
      { name: 'Herald', entries: herald },
      { name: 'Data', entries: data },
    ],
  };
}
