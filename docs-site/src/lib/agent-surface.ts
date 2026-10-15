/**
 * Agents and the changes feed read the site (Story 43.6, spec-pyforge-herald CAP-61, on CAP-11 and CAP-13).
 *
 * The machine surfaces at the artifact root (`/llms.txt`, `/llms-full.txt`, `/facts.json`), the changes page
 * with its RSS feed (`/changes/`, `/changes/rss.xml`) and the runs page (`/status/runs/`), as pure functions
 * over parsed data. Node builtins only and no `astro:*` import, so the herald tests import this module with
 * node's type stripping and no `node_modules`; YAML is parsed by the callers (`src/lib/agent-data.ts`).
 *
 * The three Guild-step inputs are build inputs, read as data and never fetched: `changes.json` (the merge
 * subjects to `main` in the last 30 days), `marshal-status.json` (`marshal status --format json`) and
 * `herald-progress.json` (`herald progress --json`). A missing input is a normal build -- the page that reads
 * it says so in one line -- and a malformed one fails the build naming the file. Nothing here calls `gh`,
 * `git`, `marshal` or `herald`: a Guild step runs them and hands the build their JSON.
 *
 * Every surface is emitted only with `pyforge.herald.pages_one_generator` on (Story 43.1's flag, exported to
 * the build as `PYFORGE_PAGES_ONE_GENERATOR`); `/status/runs/` also needs `pyforge.herald.status_pages`
 * (`PYFORGE_STATUS_PAGES`), the flag that owns the `/status/` prefix (Story 42.1).
 */

import fs from 'node:fs';
import path from 'node:path';

/** The three Guild-step inputs, by file name, under {@link inputsDir}. */
export const CHANGES_INPUT = 'changes.json';
export const MARSHAL_STATUS_INPUT = 'marshal-status.json';
export const HERALD_PROGRESS_INPUT = 'herald-progress.json';
/** Where the inputs live, relative to the repository root (gitignored, beside Story 42.1's `fleet-status.json`). */
export const INPUTS_DIR_REL = 'docsite/content';
/** Points the build at another input directory (the herald tests' fixtures). */
export const INPUTS_DIR_ENV = 'PAGES_BUILD_INPUTS_DIR';
/** The changes window, in days, until a CalVer tag anchors "since the last release". */
export const CHANGES_WINDOW_DAYS = 30;

/** An input that exists but cannot be read as the page needs it; the build fails naming the file. */
export class BuildInputShapeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BuildInputShapeError';
  }
}

function flagOn(name: string): boolean {
  return ['1', 'true', 'yes'].includes((process.env[name] ?? '').trim().toLowerCase());
}

/** `pyforge.herald.pages_one_generator`, as the Guild step exports it (Story 43.1). */
export function pagesOneGenerator(): boolean {
  return flagOn('PYFORGE_PAGES_ONE_GENERATOR');
}

/** `pyforge.herald.status_pages`, as the Guild step exports it (Story 42.1). */
export function statusPages(): boolean {
  return flagOn('PYFORGE_STATUS_PAGES');
}

/** The repository holding `start` (the build runs in `docs-site/`). */
export function repoRoot(start: string = process.cwd()): string {
  for (let dir = path.resolve(start); ; dir = path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, 'pixi.toml')) && fs.existsSync(path.join(dir, 'docs', 'map.yaml'))) {
      return dir;
    }
    if (path.dirname(dir) === dir) {
      throw new Error(`no repository with docs/map.yaml above ${start}`);
    }
  }
}

/** The input directory: `PAGES_BUILD_INPUTS_DIR`, else `<repo>/docsite/content`. */
export function inputsDir(root: string): string {
  const override = process.env[INPUTS_DIR_ENV];
  return override ? path.resolve(override) : path.join(root, INPUTS_DIR_REL);
}

export type Input<T> = { present: false; file: string } | { present: true; file: string; value: T };

/** Read `name` from `dir`: absent is `{ present: false }`; present is `parse(text, file)`'s value. */
export function readInput<T>(dir: string, name: string, parse: (text: string, file: string) => T): Input<T> {
  const file = path.join(dir, name);
  if (!fs.existsSync(file)) {
    return { present: false, file };
  }
  return { present: true, file, value: parse(fs.readFileSync(file, 'utf8'), file) };
}

function parseJson(text: string, file: string): unknown {
  try {
    return JSON.parse(text);
  } catch (exc) {
    throw new BuildInputShapeError(`${file}: not valid JSON (${(exc as Error).message})`);
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function optionalNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

// ------------------------------------------------------------------------------------- the changes

export interface Merge {
  date: string;
  station: string;
  subject: string;
  sha: string | null;
}

export interface Changes {
  generatedAt: string | null;
  windowDays: number | null;
  /** Newest first. */
  merges: Merge[];
}

/**
 * `changes.json`: an object `{ generated_at, window_days, merges: [...] }`, or the bare `merges` list. Each
 * merge carries `date` (an ISO date or date-time), `station` and `subject` (strings); `sha` is optional.
 * Listed newest first by `date` (ties keep the input's order).
 */
export function parseChanges(text: string, file: string): Changes {
  const data = parseJson(text, file);
  const list = Array.isArray(data) ? data : isObject(data) ? data.merges : undefined;
  if (!Array.isArray(list)) {
    throw new BuildInputShapeError(`${file}: neither a list of merges nor an object with a merges list`);
  }
  const merges = list.map((item, index): Merge & { at: number; index: number } => {
    if (!isObject(item)) {
      throw new BuildInputShapeError(`${file}: merge ${index} is not an object`);
    }
    for (const key of ['date', 'station', 'subject']) {
      if (typeof item[key] !== 'string') {
        throw new BuildInputShapeError(`${file}: merge ${index} has no string ${key}`);
      }
    }
    const at = Date.parse(item.date as string);
    if (Number.isNaN(at)) {
      throw new BuildInputShapeError(`${file}: merge ${index} date ${JSON.stringify(item.date)} is not a date`);
    }
    if (!(item.subject as string).trim()) {
      throw new BuildInputShapeError(`${file}: merge ${index} has an empty subject`);
    }
    return {
      date: item.date as string,
      station: item.station as string,
      subject: item.subject as string,
      sha: optionalString(item.sha),
      at,
      index,
    };
  });
  merges.sort((a, b) => b.at - a.at || a.index - b.index);
  return {
    generatedAt: isObject(data) ? optionalString(data.generated_at) : null,
    windowDays: isObject(data) ? optionalNumber(data.window_days) : null,
    merges: merges.map(({ date, station, subject, sha }) => ({ date, station, subject, sha })),
  };
}

/** The anchor id of a merge on the changes page; the feed's item links point at it. */
export function mergeAnchor(merge: Merge, index: number): string {
  return merge.sha ? `merge-${merge.sha.slice(0, 12)}` : `merge-${index + 1}`;
}

export function xmlEscape(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export interface FeedItem {
  title: string;
  link: string;
  guid: string;
  pubDate: Date;
  description: string;
}

/** An RSS 2.0 document: one `<channel>`, its items in the given order, every link the artifact's own. */
export function rssXml(channel: { title: string; link: string; description: string; items: FeedItem[] }): string {
  const items = channel.items.map(
    (item) =>
      `    <item>\n` +
      `      <title>${xmlEscape(item.title)}</title>\n` +
      `      <link>${xmlEscape(item.link)}</link>\n` +
      `      <guid isPermaLink="false">${xmlEscape(item.guid)}</guid>\n` +
      `      <pubDate>${item.pubDate.toUTCString()}</pubDate>\n` +
      `      <description>${xmlEscape(item.description)}</description>\n` +
      `    </item>\n`,
  );
  return (
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<rss version="2.0">\n` +
    `  <channel>\n` +
    `    <title>${xmlEscape(channel.title)}</title>\n` +
    `    <link>${xmlEscape(channel.link)}</link>\n` +
    `    <description>${xmlEscape(channel.description)}</description>\n` +
    items.join('') +
    `  </channel>\n` +
    `</rss>\n`
  );
}

/** The feed for `changes` (absent: an empty channel); each item links its anchor on `pageUrl`. */
export function changesFeed(changes: Changes | null, pageUrl: string): string {
  const merges = changes?.merges ?? [];
  return rssXml({
    title: 'PyForge changes',
    link: pageUrl,
    description: `Merges to main in the last ${changes?.windowDays ?? CHANGES_WINDOW_DAYS} days, newest first.`,
    items: merges.map((merge, index) => ({
      title: merge.subject,
      link: `${pageUrl}#${mergeAnchor(merge, index)}`,
      guid: merge.sha ?? `${merge.date} ${merge.subject}`,
      pubDate: new Date(Date.parse(merge.date)),
      description: merge.station ? `${merge.station}: ${merge.subject}` : merge.subject,
    })),
  });
}

// ------------------------------------------------------------------------------------ the runs page

/** One loop home of `marshal status --format json`: only the fields the page shows, never a Tier-3 path. */
export interface LoopHome {
  slug: string;
  branch: string | null;
  state: string;
  currentStory: string | null;
  elapsedSeconds: number | null;
  budgetConsumed: number | null;
  budgetConsumedUsd: number | null;
}

export interface MarshalStatus {
  generatedAt: string | null;
  homes: LoopHome[];
}

/**
 * `marshal-status.json`: marshal's envelope (`data.homes`, one row per loop home) with an optional top-level
 * `generated_at` the Guild step adds, or `{ generated_at, homes }`. Each home needs `slug` and `state`; the page
 * keeps branch, current story, elapsed time and budget and drops the rest (escalation artifacts, failed patches
 * and unpushed work name Tier-3 paths, which never reach Pages).
 */
export function parseMarshalStatus(text: string, file: string): MarshalStatus {
  const data = parseJson(text, file);
  if (!isObject(data)) {
    throw new BuildInputShapeError(`${file}: not a JSON object`);
  }
  const homes = isObject(data.data) ? data.data.homes : data.homes;
  if (!Array.isArray(homes)) {
    throw new BuildInputShapeError(`${file}: no homes list (data.homes)`);
  }
  return {
    generatedAt: optionalString(data.generated_at),
    homes: homes.map((home, index) => {
      if (!isObject(home)) {
        throw new BuildInputShapeError(`${file}: home ${index} is not an object`);
      }
      for (const key of ['slug', 'state']) {
        if (typeof home[key] !== 'string' || !(home[key] as string).trim()) {
          throw new BuildInputShapeError(`${file}: home ${index} has no ${key}`);
        }
      }
      return {
        slug: home.slug as string,
        branch: optionalString(home.branch),
        state: home.state as string,
        currentStory: optionalString(home.current_story),
        elapsedSeconds: optionalNumber(home.elapsed_seconds),
        budgetConsumed: optionalNumber(home.budget_consumed),
        budgetConsumedUsd: optionalNumber(home.budget_consumed_usd),
      };
    }),
  };
}

/** One `herald progress --json` record, as the page shows it. */
export interface ProgressRecord {
  station: string;
  date: string;
  shippedCapabilities: string[];
  computeHours: number | null;
  tokenSpend: number | null;
  wallClockHours: number | null;
  unblockNarrative: string;
  updatedAt: string;
}

export interface HeraldProgress {
  generatedAt: string | null;
  /** The latest record per station, by station. */
  latest: ProgressRecord[];
}

function progressRecord(value: unknown, where: string): ProgressRecord {
  if (!isObject(value)) {
    throw new BuildInputShapeError(`${where} is not an object`);
  }
  for (const key of ['station', 'date']) {
    if (typeof value[key] !== 'string' || !(value[key] as string).trim()) {
      throw new BuildInputShapeError(`${where} has no ${key}`);
    }
  }
  const shipped = value.shipped_capabilities;
  if (shipped !== undefined && !(Array.isArray(shipped) && shipped.every((cap) => typeof cap === 'string'))) {
    throw new BuildInputShapeError(`${where} shipped_capabilities is not a list of strings`);
  }
  return {
    station: value.station as string,
    date: value.date as string,
    shippedCapabilities: (shipped as string[] | undefined) ?? [],
    computeHours: optionalNumber(value.compute_hours),
    tokenSpend: optionalNumber(value.token_spend),
    wallClockHours: optionalNumber(value.wall_clock_hours),
    unblockNarrative: typeof value.unblock_narrative === 'string' ? value.unblock_narrative : '',
    updatedAt: typeof value.updated_at === 'string' ? value.updated_at : '',
  };
}

/** The newest record per station (by `date`, then `updated_at`), ordered by station. */
export function latestPerStation(records: ProgressRecord[]): ProgressRecord[] {
  const latest = new Map<string, ProgressRecord>();
  for (const record of records) {
    const seen = latest.get(record.station);
    if (!seen || [record.date, record.updatedAt].join(' ') > [seen.date, seen.updatedAt].join(' ')) {
      latest.set(record.station, record);
    }
  }
  return [...latest.values()].sort((a, b) => a.station.localeCompare(b.station));
}

/**
 * `herald-progress.json`: `{ generated_at, records: [...] }`, a JSON list of records, or the newline-delimited
 * JSON `herald progress --json` prints (one record per line).
 */
export function parseHeraldProgress(text: string, file: string): HeraldProgress {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    const lines = text.split('\n').filter((line) => line.trim());
    data = lines.map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (exc) {
        throw new BuildInputShapeError(`${file}: line ${index + 1} is not valid JSON (${(exc as Error).message})`);
      }
    });
  }
  const list = Array.isArray(data) ? data : isObject(data) ? data.records : undefined;
  if (!Array.isArray(list)) {
    throw new BuildInputShapeError(`${file}: neither a list of progress records nor an object with a records list`);
  }
  return {
    generatedAt: isObject(data) ? optionalString(data.generated_at) : null,
    latest: latestPerStation(list.map((record, index) => progressRecord(record, `${file}: record ${index}`))),
  };
}

// --------------------------------------------------------------------------------------- facts.json

/**
 * `/facts.json`: one object per `presentations/<slug>/facts.yaml`, keyed by its `deck` slug, each carrying that
 * file's `deck`, `persona`, `derived_at`, `tree` and `facts`. `entries` are the parsed files with their
 * repository-relative paths; a file with no `deck`, a `facts` that is not a list, or a second file for one deck
 * fails the build naming the files.
 */
export function factsDocument(entries: Array<{ file: string; data: unknown }>): Record<string, unknown> {
  const decks = new Map<string, { file: string; value: Record<string, unknown> }>();
  for (const { file, data } of entries) {
    if (!isObject(data) || typeof data.deck !== 'string' || !data.deck.trim()) {
      throw new BuildInputShapeError(`${file}: no deck slug`);
    }
    if (!Array.isArray(data.facts)) {
      throw new BuildInputShapeError(`${file}: facts is not a list`);
    }
    const seen = decks.get(data.deck);
    if (seen) {
      throw new BuildInputShapeError(`${file}: deck ${JSON.stringify(data.deck)} is also ${seen.file}`);
    }
    decks.set(data.deck, {
      file,
      value: {
        deck: data.deck,
        persona: data.persona ?? null,
        derived_at: data.derived_at ?? null,
        tree: data.tree ?? null,
        source: file,
        facts: data.facts,
      },
    });
  }
  return Object.fromEntries([...decks.keys()].sort().map((deck) => [deck, decks.get(deck)!.value]));
}

// -------------------------------------------------------------------------------- llms.txt and friends

/** The site route of a `docs/map.yaml` page path: `x/README.md` is `x/`, `x/y.md` is `x/y/`. */
export function shelfRoute(mapPath: string): string {
  const norm = mapPath.replace(/\\/g, '/');
  if (norm.endsWith('/README.md') || norm.endsWith('/index.md')) {
    return norm.slice(0, norm.lastIndexOf('/') + 1);
  }
  return `${norm.replace(/\.mdx?$/, '')}/`;
}

/** The shelf collection id of a `docs/map.yaml` page path (the shelf loader's `generateId`). */
export function shelfId(mapPath: string): string {
  const id = mapPath.replace(/\\/g, '/').replace(/\.mdx?$/, '');
  return id.endsWith('/README') ? `${id.slice(0, -'/README'.length)}/index` : id;
}

/** Markdown-ish text as plain text: emphasis, code ticks and link targets removed. */
export function plainText(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1$2')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/[ \t]+/g, ' ')
    .trim();
}

const NON_TEXT_KEYS = new Set(['type', 'id', 'key', 'accent', 'glyph', 'alarm', 'mono', 'href', 'src', 'tone', 'kind']);

/** Every text leaf of a parsed YAML document (the dossier), in document order, as plain text. */
export function flattenText(value: unknown, key = ''): string[] {
  if (typeof value === 'string') {
    return NON_TEXT_KEYS.has(key) || !value.trim() ? [] : [plainText(value)];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => flattenText(item, key));
  }
  if (isObject(value)) {
    return Object.entries(value).flatMap(([child, item]) => flattenText(item, child));
  }
  return [];
}

export interface LlmsEntry {
  title: string;
  url: string;
  description?: string;
  /** The page's text, for `/llms-full.txt`. */
  text?: string;
}

export interface LlmsSection {
  name: string;
  entries: LlmsEntry[];
}

/** `/llms.txt` (the llmstxt.org shape): the site's name, its summary, and one linked list per section. */
export function llmsTxt(site: { title: string; summary: string; sections: LlmsSection[] }): string {
  const lines = [`# ${site.title}`, '', `> ${site.summary.replace(/\s+/g, ' ').trim()}`, ''];
  for (const section of site.sections) {
    lines.push(`## ${section.name}`, '');
    for (const entry of section.entries) {
      const description = entry.description ? `: ${entry.description.replace(/\s+/g, ' ').trim()}` : '';
      lines.push(`- [${entry.title}](${entry.url})${description}`);
    }
    lines.push('');
  }
  return `${lines.join('\n').trimEnd()}\n`;
}

/** `/llms-full.txt`: every listed page's title, URL and text, in `/llms.txt`'s order. */
export function llmsFullTxt(site: { title: string; summary: string; sections: LlmsSection[] }): string {
  const parts = [`# ${site.title}\n\n> ${site.summary.replace(/\s+/g, ' ').trim()}\n`];
  for (const section of site.sections) {
    for (const entry of section.entries) {
      const body = (entry.text ?? entry.description ?? '').trim();
      parts.push(`## ${entry.title}\n\nURL: ${entry.url}\n\n${body}\n`);
    }
  }
  return `${parts.join('\n---\n\n').trimEnd()}\n`;
}

/** The entries of `/llms.txt`'s page sections (Docs, Herald): the count AC1 compares with `docs/map.yaml`. */
export function countPageEntries(llms: string, sections: string[] = ['Docs', 'Herald']): number {
  let current = '';
  let count = 0;
  for (const line of llms.split('\n')) {
    if (line.startsWith('## ')) {
      current = line.slice(3).trim();
    } else if (sections.includes(current) && line.startsWith('- [')) {
      count += 1;
    }
  }
  return count;
}

// ------------------------------------------------------------------------------------------- Lane 1

/**
 * `site.yml`'s `lane1` entry when its `href` is an absolute `http(s)://` URL, else `null`: Lane 1 is the
 * platform's host, not Pages, so a root-absolute href would 404 on the Pages origin (the rule
 * `docsite/tools/status_pages.lane1_link` applies to Story 42.1's board).
 */
export function lane1Link(lane1: unknown): { href: string; label: string } | null {
  if (!isObject(lane1) || typeof lane1.href !== 'string') {
    return null;
  }
  const href = lane1.href.trim();
  if (!/^https?:\/\//i.test(href)) {
    return null;
  }
  return { href, label: typeof lane1.label === 'string' ? lane1.label : '' };
}
