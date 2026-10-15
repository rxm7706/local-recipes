import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import type { Loader } from 'astro/loaders';
import { parse as parseYaml } from 'yaml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const DOSSIER_YML = path.join(REPO_ROOT, 'docsite/content/dossier.yml');
const CONTENT_DIR = path.join(REPO_ROOT, 'docsite/content');

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
      if (process.env.PYFORGE_PAGES_ONE_GENERATOR !== '1') {
        logger.info('dossier collection skipped (PYFORGE_PAGES_ONE_GENERATOR off)');
        return;
      }
      const raw = await fs.readFile(DOSSIER_YML, 'utf8');
      const doc = parseYaml(raw) as Record<string, unknown>;
      await applyCiSurfacesAsync(doc);
      const parsed = await parseData({
        id: 'dossier',
        ...doc,
      });
      store.set({
        id: 'dossier',
        data: parsed,
        body: '',
      });
    },
  };
}
