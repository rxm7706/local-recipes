import { execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import type { Loader } from 'astro/loaders';
import { parse as parseYaml } from 'yaml';

import { ciSurfacesTile } from '../lib/flags.ts';
import { CI_STATUS_SNAPSHOT, loadCiStatus, tileBlock } from '../lib/status.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
/** The tree the dossier reads and the measurer counts: `HERALD_PAGES_REPO_ROOT` (a test's fixture), else this one. */
const DATA_ROOT = process.env.HERALD_PAGES_REPO_ROOT ? path.resolve(process.env.HERALD_PAGES_REPO_ROOT) : REPO_ROOT;
/** The dossier's content, beside the generator (Story 43.7). */
export const DOSSIER_REL = 'docs-site/src/content/dossier/dossier.yml';
const DOSSIER_YML = path.join(DATA_ROOT, DOSSIER_REL);
/** The committed CAP-59 snapshot the CI surfaces tile reads. */
const CI_STATUS = path.join(REPO_ROOT, 'docs-site/src/content', CI_STATUS_SNAPSHOT);
/** The one measurer (CAP-46), never a second measurement: Story 43.5 reads what it emits. */
const MEASURER = path.join(REPO_ROOT, 'docs-site/scripts/verify_claims.py');

type Stat = { value: string; label: string; check?: string };
type Row = { cells: string[]; section?: string };
type Measured = Record<string, Record<string, { value: string; files?: number }>>;

/**
 * `verify_claims.py --emit` over `DATA_ROOT` with `HERALD_PYTHON`, else the `python` on `PATH` (it needs PyYAML, as the
 * `site` env provides): a failure (an unknown `check:` key, a missing package or sprint ledger, a checked table row
 * with no `section:`) fails the build.
 */
function measure(): Measured {
  const python = process.env.HERALD_PYTHON || 'python';
  try {
    const out = execFileSync(python, [MEASURER, '--emit', '-', '--root', DATA_ROOT, '--content', DOSSIER_YML], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    return JSON.parse(out) as Measured;
  } catch (error) {
    const stderr = String((error as { stderr?: unknown }).stderr ?? '').trim();
    throw new Error(`dossier: the measurer failed (${MEASURER} --emit): ${stderr || String(error)}`);
  }
}

/**
 * Story 43.5 (CAP-61): every stat carrying `check:` shows the measured value (its typed value ignored), and a
 * `src_lines` stat's label names the measured file count. A stat without `check:` is passed on untouched for the
 * content schema to refuse (Story 51.1, CAP-46: no dossier figure is typed).
 */
function applyMeasured(doc: Record<string, unknown>, measured: Measured): void {
  const show = (stat: Stat, where: string) => {
    if (!stat.check) {
      return;
    }
    const value = measured[stat.check]?.[where];
    if (!value) {
      throw new Error(`dossier: no measured ${stat.check} for ${where}`);
    }
    stat.value = value.value;
    if (value.files !== undefined) {
      stat.label = stat.label.replace(/\d[\d,]*(\s*files)/, `${value.files}$1`);
    }
  };
  for (const stat of (doc.stats as Stat[] | undefined) ?? []) {
    show(stat, 'fleet');
  }
  for (const section of (doc.sections as Array<Record<string, unknown>> | undefined) ?? []) {
    for (const block of (section.blocks as Array<Record<string, unknown>> | undefined) ?? []) {
      for (const stat of block.type === 'stats' ? ((block.stats as Stat[] | undefined) ?? []) : []) {
        show(stat, String(section.id));
      }
    }
  }
}

/**
 * Story 51.1 (CAP-46): a table block carrying `check: src_lines` (the scale table) shows, in each row, the measured
 * source lines and files of the row's `section:` (a station id, or `core`) in its "Source lines" and "Files" columns.
 */
function applyMeasuredRows(doc: Record<string, unknown>, measured: Measured): void {
  for (const section of (doc.sections as Array<Record<string, unknown>> | undefined) ?? []) {
    for (const block of (section.blocks as Array<Record<string, unknown>> | undefined) ?? []) {
      if (block.type !== 'table' || block.check === undefined) {
        continue;
      }
      const headers = (block.headers as string[] | undefined) ?? [];
      const [lines, files] = ['Source lines', 'Files'].map((header) => headers.indexOf(header));
      if (lines < 0 || files < 0) {
        throw new Error(`dossier: the checked table in ${String(section.id)} has no Source lines or Files column`);
      }
      for (const row of (block.rows as Row[] | undefined) ?? []) {
        const value = measured.rows?.[String(row.section)];
        if (!value || value.files === undefined) {
          throw new Error(`dossier: no measured row for ${String(row.section)} in ${String(section.id)}`);
        }
        row.cells[lines] = value.value;
        row.cells[files] = String(value.files);
      }
    }
  }
}

/**
 * The CI surfaces tile (Story 39.1, CAP-59): with `pyforge.herald.ci_surfaces_tile` on, each `ci_surfaces` block is
 * the snapshot's tile -- one line per surface that is not live, or the one all-live line (`src/lib/status.ts`); a
 * missing or malformed snapshot fails the build naming the file. Off, the block is dropped.
 */
function applyCiSurfaces(doc: Record<string, unknown>): void {
  const sections = (doc.sections as Array<Record<string, unknown>>) ?? [];
  const payload = ciSurfacesTile() ? tileBlock(loadCiStatus(CI_STATUS)) : null;
  for (const section of sections) {
    const blocks = section.blocks as Array<Record<string, unknown>> | undefined;
    if (blocks) {
      section.blocks = payload
        ? blocks.map((b) => (b.type === 'ci_surfaces' ? payload : b))
        : blocks.filter((b) => b.type !== 'ci_surfaces');
    }
  }
}

export function dossierLoader(): Loader {
  return {
    name: 'dossier-yml-loader',
    load: async ({ store, parseData }) => {
      const raw = await fs.readFile(DOSSIER_YML, 'utf8');
      const doc = parseYaml(raw) as Record<string, unknown>;
      const measured = measure();
      applyMeasured(doc, measured);
      applyMeasuredRows(doc, measured);
      applyCiSurfaces(doc);
      // An object loader validates through parseData (Story 43.5): the schema's refusals reach the build.
      const data = await parseData({ id: 'dossier', data: doc });
      store.set({
        id: 'dossier',
        data,
        body: '',
      });
    },
  };
}
