import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import type { Loader } from 'astro/loaders';

const QUADRANTS = new Set(['tutorials', 'how-to', 'reference', 'explanation']);

function isIncluded(relativePath: string): boolean {
  const norm = relativePath.replace(/\\/g, '/');
  if (norm === 'index.md' || norm === '404.md') {
    return true;
  }
  const top = norm.split('/')[0];
  if (!QUADRANTS.has(top)) {
    return false;
  }
  return norm.endsWith('.md') || norm.endsWith('.mdx');
}

function parseFrontmatter(raw: string): { data: Record<string, unknown>; body: string } {
  if (!raw.startsWith('---')) {
    return { data: {}, body: raw };
  }
  const end = raw.indexOf('\n---', 3);
  if (end === -1) {
    return { data: {}, body: raw };
  }
  const fmBlock = raw.slice(3, end).trim();
  const body = raw.slice(end + 4).replace(/^\n/, '');
  const data: Record<string, unknown> = {};
  for (const line of fmBlock.split('\n')) {
    const match = line.match(/^([\w-]+):\s*(.*)$/);
    if (!match) {
      continue;
    }
    const [, key, value] = match;
    data[key] = value.replace(/^["']|["']$/g, '');
  }
  return { data, body };
}

function extractFirstH1(body: string): { title: string | null; rest: string } {
  const lines = body.split('\n');
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();
    if (trimmed.startsWith('<!--')) {
      while (index < lines.length && !lines[index].includes('-->')) {
        index += 1;
      }
      index += 1;
      continue;
    }
    const match = line.match(/^#\s+(.+)$/);
    if (match) {
      const rest = [...lines.slice(0, index), ...lines.slice(index + 1)].join('\n').replace(/^\n+/, '');
      return { title: match[1].trim(), rest };
    }
    if (trimmed === '') {
      index += 1;
      continue;
    }
    break;
  }
  return { title: null, rest: body };
}

function generateId(relativePath: string): string {
  let id = relativePath.replace(/\\/g, '/').replace(/\.mdx?$/, '');
  if (id.endsWith('/README')) {
    return `${id.slice(0, -'/README'.length)}/index`;
  }
  return id;
}

async function walkDocs(root: string, store: { set: (entry: { id: string; data: Record<string, unknown>; body: string }) => void }, prefix = ''): Promise<void> {
  const entries = await fs.readdir(root, { withFileTypes: true });
  for (const entry of entries) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      await walkDocs(full, store, rel);
      continue;
    }
    if (!isIncluded(rel)) {
      continue;
    }
    const raw = await fs.readFile(full, 'utf8');
    let { data, body } = parseFrontmatter(raw);
    let title = typeof data.title === 'string' ? data.title : undefined;
    if (!title) {
      const extracted = extractFirstH1(body);
      if (!extracted.title) {
        throw new Error(`docs-site: missing title and no # heading in ${rel}`);
      }
      title = extracted.title;
      body = extracted.rest;
    }
    const id = generateId(rel);
    const entryData: Record<string, unknown> = { ...data, title };
    if (!Array.isArray(entryData.head)) {
      entryData.head = [];
    }
    store.set({
      id,
      data: entryData,
      body,
    });
  }
}

export function shelfDocsLoader(): Loader {
  return {
    name: 'shelf-docs-loader',
    async load({ store }) {
      const root = fileURLToPath(new URL('../content/docs', import.meta.url));
      await walkDocs(root, store);
    },
  };
}
