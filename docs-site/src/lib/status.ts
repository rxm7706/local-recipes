/**
 * The fleet board (`/status/`), the guild status page (`/status/ci/`) and the dossier's CI surfaces tile, read as
 * data (herald Stories 39.1 and 42.1, CAP-59 and CAP-60; ported from the retired Jinja path's `status_pages.py` and
 * `ci_surfaces_tile.py` by Story 43.7, CAP-61).
 *
 * Two build inputs, both steward's output read as data and re-derived from nothing:
 *
 * - `fleet-status.json` (gitignored, under the build-input directory; `scripts/pages_fleet_status.py` writes it in a
 *   Guild step of steward's Pages workflow from `sprint-ledger-query --format json`). Required: `stations`, a list,
 *   each with `done` and `total` (non-negative integers, `done` no more than `total`); `stories`, when present, a
 *   list whose rows carry `story_id` and `status`. Every other field is optional and read under steward's name.
 * - `ci-status.json` (committed, `docs-site/src/content/`; the stdout of `pyforge steward ci status --json`, CAP-59).
 *   Required: `fetched_at` and `rows`, a list whose rows carry `id` and `verdict`.
 *
 * A missing or malformed input fails the build naming the file (`StatusInputShapeError`); with
 * `pyforge.herald.status_pages` off neither page renders and `fleet-status.json` is never opened. Node builtins only:
 * the herald tests import this module with node's type stripping and no `node_modules`.
 */

import fs from 'node:fs';

/** Where the board's input lives, by file name, under the build-input directory (`agent-surface.ts`'s `inputsDir`). */
export const FLEET_STATUS_INPUT = 'fleet-status.json';
/** The committed snapshot, by file name, under `docs-site/src/content/`. */
export const CI_STATUS_SNAPSHOT = 'ci-status.json';
/** The attention block's statuses, in the order the block lists them. */
export const ATTENTION_STATUSES = ['blocked', 'backlog'] as const;
/** Optional per-station counts, read under steward's names. */
export const COUNT_KEYS = ['epics', 'in_progress', 'backlog', 'blocked'] as const;
/** The tile's verdict order; an unknown verdict follows these (by name), `live` comes last. */
export const VERDICT_ORDER = ['drift', 'stuck', 'overdue', 'paused', 'paused-manually', 'opt-in-off', 'retired'];
/** The guild status page's columns, in order. */
export const GUILD_FIELDS = ['id', 'verdict', 'switch', 'paused_since', 'review_by', 'owner', 'detail'] as const;
const DASH = '—';

/** A status input that is missing, not JSON, or lacks a key a page needs; the build fails naming the file. */
export class StatusInputShapeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'StatusInputShapeError';
  }
}

type Json = Record<string, unknown>;

function isObject(value: unknown): value is Json {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0;
}

function readJson(file: string, missing: string): unknown {
  if (!fs.existsSync(file)) {
    throw new StatusInputShapeError(`${file}: ${missing}`);
  }
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (exc) {
    throw new StatusInputShapeError(`${file}: not valid JSON (${(exc as Error).message})`);
  }
}

// ------------------------------------------------------------------------------------------- the board

function stationLabel(index: number, station: Json): string {
  const name = station.station;
  return typeof name === 'string' && name ? `station ${index} (${name})` : `station ${index}`;
}

/** The board's input shape check; throws `StatusInputShapeError` naming `file` and the first defect. */
export function validateFleetStatus(data: unknown, file: string): asserts data is Json {
  if (!isObject(data)) {
    throw new StatusInputShapeError(`${file}: envelope is not a JSON object`);
  }
  if (!('stations' in data)) {
    throw new StatusInputShapeError(`${file}: missing stations`);
  }
  if (!Array.isArray(data.stations)) {
    throw new StatusInputShapeError(`${file}: stations is not a list`);
  }
  data.stations.forEach((station: unknown, index: number) => {
    if (!isObject(station)) {
      throw new StatusInputShapeError(`${file}: station ${index} is not an object`);
    }
    const label = stationLabel(index, station);
    for (const key of ['done', 'total']) {
      if (!(key in station)) {
        throw new StatusInputShapeError(`${file}: ${label} missing ${key}`);
      }
      if (!isCount(station[key])) {
        throw new StatusInputShapeError(`${file}: ${label} ${key} is not a non-negative integer`);
      }
    }
    if ((station.done as number) > (station.total as number)) {
      throw new StatusInputShapeError(`${file}: ${label} done ${station.done} is more than total ${station.total}`);
    }
  });
  if (data.stories === undefined || data.stories === null) {
    return;
  }
  // Optional, but never read loosely: a malformed list would render a false "nothing needs attention".
  if (!Array.isArray(data.stories)) {
    throw new StatusInputShapeError(`${file}: stories is not a list`);
  }
  data.stories.forEach((story: unknown, index: number) => {
    if (!isObject(story)) {
      throw new StatusInputShapeError(`${file}: story ${index} is not an object`);
    }
    for (const key of ['story_id', 'status']) {
      if (!(key in story)) {
        throw new StatusInputShapeError(`${file}: story ${index} missing ${key}`);
      }
    }
  });
}

/** `fleet-status.json`, validated. */
export function loadFleetStatus(file: string): Json {
  const data = readJson(file, 'fleet-status input missing');
  validateFleetStatus(data, file);
  return data;
}

/** The integer percentage of `done` over `total` (floored); 0 when `total` is 0, never above 100. */
export function barWidth(done: number, total: number): number {
  return total <= 0 ? 0 : Math.min(100, Math.floor((done * 100) / total));
}

export interface StationRow {
  name: string;
  done: number;
  total: number;
  width: number;
  epics: string;
  in_progress: string;
  backlog: string;
  blocked: string;
}

export interface AttentionItem {
  station: string;
  story_id: string;
  status: string;
  title: string;
}

export interface Board {
  generatedAt: string | null;
  stations: StationRow[];
  attention: AttentionItem[];
  attentionNote: string | null;
}

function stations(data: Json): Json[] {
  return data.stations as Json[];
}

function stationKey(station: Json): string {
  return typeof station.station === 'string' ? station.station : '';
}

export function stationRows(data: Json): StationRow[] {
  return stations(data).map((station, index) => {
    const name = typeof station.station === 'string' && station.station ? station.station : `station ${index}`;
    const counts = Object.fromEntries(COUNT_KEYS.map((key) => [key, isCount(station[key]) ? String(station[key]) : DASH]));
    const done = station.done as number;
    const total = station.total as number;
    return { name, done, total, width: barWidth(done, total), ...counts } as StationRow;
  });
}

/** Every `blocked` then every `backlog` story the input carries, each once, in input order. */
export function attentionItems(data: Json): AttentionItem[] {
  const stories = Array.isArray(data.stories) ? (data.stories as Json[]) : [];
  const seen = new Set<string>();
  const items: AttentionItem[] = [];
  for (const status of ATTENTION_STATUSES) {
    for (const story of stories) {
      if (story.status !== status) {
        continue;
      }
      const station = story.station ? String(story.station) : '';
      const storyId = String(story.story_id);
      const key = JSON.stringify([station, storyId]);
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      items.push({ station, story_id: storyId, status, title: typeof story.title === 'string' ? story.title : '' });
    }
  }
  return items;
}

/** The stations' summed `key` count, and whether every station gave one. */
function counted(data: Json, key: string): [number, boolean] {
  const values = stations(data).map((station) => station[key]);
  return [values.filter(isCount).reduce((a, b) => a + b, 0), values.every(isCount)];
}

/**
 * Per station, each attention status whose listed rows differ from that station's own count -- compared station by
 * station, never as fleet-wide sums, so one station's surplus never hides another's missing rows. A count the input
 * does not give is not compared; a listed story whose station no `stations` row names is a disagreement of its own.
 */
function disagreements(data: Json, items: AttentionItem[]): string[] {
  const counts = new Map<string, Record<string, number | null>>();
  for (const station of stations(data)) {
    const name = stationKey(station);
    const merged = counts.get(name) ?? Object.fromEntries(ATTENTION_STATUSES.map((s) => [s, 0]));
    for (const status of ATTENTION_STATUSES) {
      const previous = merged[status];
      const value = station[status];
      merged[status] = previous !== null && isCount(value) ? previous + value : null;
    }
    counts.set(name, merged);
  }
  const listed = new Map<string, Record<string, number>>();
  for (const item of items) {
    const per = listed.get(item.station) ?? Object.fromEntries(ATTENTION_STATUSES.map((s) => [s, 0]));
    per[item.status] += 1;
    listed.set(item.station, per);
  }
  const lines: string[] = [];
  for (const [name, perStatus] of counts) {
    const shown = listed.get(name) ?? Object.fromEntries(ATTENTION_STATUSES.map((s) => [s, 0]));
    const parts = ATTENTION_STATUSES.filter((s) => perStatus[s] !== null && shown[s] !== perStatus[s]).map(
      (s) => `${shown[s]} ${s} listed, ${perStatus[s]} counted`,
    );
    if (parts.length) {
      lines.push(`${name || 'a station without a name'}: ${parts.join(', ')}`);
    }
  }
  for (const [name, shown] of listed) {
    if (!counts.has(name)) {
      const parts = ATTENTION_STATUSES.filter((s) => shown[s]).map((s) => `${shown[s]} ${s}`);
      lines.push(`${name || 'no station'}: ${parts.join(', ')} listed, no station row counts them`);
    }
  }
  return lines;
}

/**
 * What the attention block says beside (or instead of) its list. The all-clear is said only when every station counts
 * 0 blocked and 0 backlog: an input whose `stories` lists fewer rows than its counts show says so instead of claiming
 * nothing needs attention; a list that disagrees with the counts names each station where it does.
 */
export function attentionNote(data: Json, items: AttentionItem[]): string | null {
  const [blocked, blockedKnown] = counted(data, 'blocked');
  const [backlog, backlogKnown] = counted(data, 'backlog');
  if (!items.length) {
    if (blocked || backlog) {
      return `The input lists none of the ${blocked} blocked / ${backlog} backlog stories the station counts show.`;
    }
    if (blockedKnown && backlogKnown) {
      return 'Nothing needs attention: no story is blocked or in the backlog.';
    }
    return 'The input lists no blocked or backlog story, and its station counts do not say whether any exist.';
  }
  const lines = disagreements(data, items);
  return lines.length ? `The input's story list and its station counts disagree. ${lines.join('; ')}.` : null;
}

/** The fleet board's view of a validated input. */
export function board(data: Json): Board {
  const items = attentionItems(data);
  const generatedAt = typeof data.generated_at === 'string' && data.generated_at.trim() ? data.generated_at : null;
  return { generatedAt, stations: stationRows(data), attention: items, attentionNote: attentionNote(data, items) };
}

// ---------------------------------------------------------------------------- the CI surfaces snapshot

export interface CiStatus {
  fetched_at: string;
  rows: Json[];
}

/** The snapshot's shape check; throws `StatusInputShapeError` naming `file` and the first defect. */
export function validateCiStatus(data: unknown, file: string): asserts data is CiStatus {
  if (!isObject(data)) {
    throw new StatusInputShapeError(`${file}: envelope is not a JSON object`);
  }
  for (const key of ['fetched_at', 'rows']) {
    if (!(key in data)) {
      throw new StatusInputShapeError(`${file}: missing ${key}`);
    }
  }
  if (!Array.isArray(data.rows)) {
    throw new StatusInputShapeError(`${file}: rows is not a list`);
  }
  data.rows.forEach((row: unknown, index: number) => {
    if (!isObject(row)) {
      throw new StatusInputShapeError(`${file}: row ${index} is not an object`);
    }
    if (!('id' in row)) {
      throw new StatusInputShapeError(`${file}: row ${index} missing id`);
    }
    if (!('verdict' in row)) {
      const id = row.id === null || row.id === undefined ? '' : ` (${String(row.id)})`;
      throw new StatusInputShapeError(`${file}: row ${index}${id} missing verdict`);
    }
  });
}

/** `ci-status.json`, validated. */
export function loadCiStatus(file: string): CiStatus {
  const data = readJson(file, 'snapshot missing');
  validateCiStatus(data, file);
  return data;
}

function verdictKey(row: Json): [number, number, string, string] {
  const verdict = String(row.verdict);
  const id = String(row.id);
  const known = VERDICT_ORDER.indexOf(verdict);
  if (known >= 0) {
    return [0, known, '', id];
  }
  return verdict === 'live' ? [2, 0, '', id] : [1, 0, verdict, id];
}

/** The snapshot's rows in the tile's order: `VERDICT_ORDER`, unknown verdicts by name, `live` last; by id within one. */
export function orderRows(rows: Json[], includeLive = true): Json[] {
  const chosen = includeLive ? [...rows] : rows.filter((row) => row.verdict !== 'live');
  const cmp = (a: string | number, b: string | number) => (a < b ? -1 : a > b ? 1 : 0);
  return chosen.sort((a, b) => {
    const ka = verdictKey(a);
    const kb = verdictKey(b);
    return cmp(ka[0], kb[0]) || cmp(ka[1], kb[1]) || cmp(ka[2], kb[2]) || cmp(ka[3], kb[3]);
  });
}

function field(value: unknown): string {
  return value === null || value === undefined ? DASH : String(value);
}

/** The guild status page's rows: every snapshot row in the tile's order, `live` last, each field as text. */
export function guildRows(snapshot: CiStatus): Array<Record<(typeof GUILD_FIELDS)[number], string>> {
  return orderRows(snapshot.rows).map(
    (row) => Object.fromEntries(GUILD_FIELDS.map((key) => [key, field(row[key])])) as Record<(typeof GUILD_FIELDS)[number], string>,
  );
}

function daysLeft(value: unknown): string {
  if (typeof value !== 'number') {
    return DASH;
  }
  if (value < 0) {
    return `${Math.abs(value)} days overdue`;
  }
  return value === 0 ? 'due today' : `${value} days left`;
}

/** One tile line for a surface that is not live (CAP-59's wording). */
export function tileLine(row: Json): string {
  const detail = row.detail ? ` · ${String(row.detail)}` : '';
  return (
    `**${field(row.id)}** · ${field(row.verdict)} · switch ${field(row.switch)} · paused since ${field(row.paused_since)} · ` +
    `review by ${field(row.review_by)} · ${daysLeft(row.review_days_left)} · owner ${field(row.owner)}${detail}`
  );
}

/** The dossier's `ci_surfaces` block: one line per surface that is not live, or the one all-live line. */
export function tileBlock(snapshot: CiStatus): { type: 'ci_surfaces'; fetched_at: string; lines: string[]; all_live: boolean } {
  const notLive = orderRows(snapshot.rows, false);
  return {
    type: 'ci_surfaces',
    fetched_at: snapshot.fetched_at,
    lines: notLive.length ? notLive.map(tileLine) : ['All CI surfaces reported **live** at capture.'],
    all_live: notLive.length === 0,
  };
}
