import { execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import type { Loader } from 'astro/loaders';
import { parse as parseYaml } from 'yaml';

import { pagesOneGenerator } from '../lib/flags.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
/** The tree the dossier reads and the measurer counts: `HERALD_PAGES_REPO_ROOT` (a test's fixture), else this one. */
const DATA_ROOT = process.env.HERALD_PAGES_REPO_ROOT ? path.resolve(process.env.HERALD_PAGES_REPO_ROOT) : REPO_ROOT;
const DOSSIER_YML = path.join(DATA_ROOT, 'docsite/content/dossier.yml');
const CONTENT_DIR = path.join(REPO_ROOT, 'docsite/content');
/** The one measurer (CAP-46), never a second measurement: Story 43.5 reads what it emits. */
const MEASURER = path.join(REPO_ROOT, 'docsite/tools/verify_claims.py');

type Stat = { value: string; label: string; check?: string };
type Measured = Record<string, Record<string, { value: string; files?: number }>>;

/**
 * `verify_claims.py --emit` over `DATA_ROOT` with `HERALD_PYTHON`, else the `python` on `PATH` (it needs PyYAML, as the
 * `site` env provides): a failure (an unknown `check:` key, a missing package) fails the build.
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
 * `src_lines` stat's label names the measured file count; a stat without `check:` keeps its typed value.
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

function tileEnabledFromEnv(): boolean {
  const raw = process.env.PYFORGE_CI_SURFACES_TILE ?? '';
  return ['1', 'true', 'yes'].includes(raw.trim().toLowerCase());
}

async function loadCiSnapshot(): Promise<Record<string, unknown>> {
  const snapPath = path.join(CONTENT_DIR, 'ci-status.json');
  const text = await fs.readFile(snapPath, 'utf8');
  return JSON.parse(text) as Record<string, unknown>;
}

function buildCiSurfacesBlock(data: Record<string, unknown>): Record<string, unknown> {
  const rows = (data.rows as Array<Record<string, unknown>>) ?? [];
  const lines = rows.map((row) => `${row.id}: ${row.verdict}`);
  return {
    type: 'ci_surfaces',
    fetched_at: data.fetched_at,
    lines,
    all_live: lines.length === 1 && String(lines[0]).toLowerCase().includes('live'),
  };
}

async function applyCiSurfacesAsync(doc: Record<string, unknown>): Promise<void> {
  const sections = (doc.sections as Array<Record<string, unknown>>) ?? [];
  if (!tileEnabledFromEnv()) {
    for (const section of sections) {
      const blocks = section.blocks as Array<Record<string, unknown>> | undefined;
      if (blocks) {
        section.blocks = blocks.filter((b) => b.type !== 'ci_surfaces');
      }
    }
    return;
  }
  const data = await loadCiSnapshot();
  const payload = buildCiSurfacesBlock(data);
  for (const section of sections) {
    const blocks = section.blocks as Array<Record<string, unknown>> | undefined;
    if (!blocks) {
      continue;
    }
    section.blocks = blocks.map((b) => (b.type === 'ci_surfaces' ? payload : b));
  }
}

export function dossierLoader(): Loader {
  return {
    name: 'dossier-yml-loader',
    load: async ({ store, logger, parseData }) => {
      if (!pagesOneGenerator()) {
        logger.info('dossier collection skipped (PYFORGE_PAGES_ONE_GENERATOR off)');
        return;
      }
      const raw = await fs.readFile(DOSSIER_YML, 'utf8');
      const doc = parseYaml(raw) as Record<string, unknown>;
      applyMeasured(doc, measure());
      await applyCiSurfacesAsync(doc);
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
