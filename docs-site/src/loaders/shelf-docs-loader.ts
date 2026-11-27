import { firstParagraph, readerTitle } from '../lib/reader-text.ts';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import type { Loader, LoaderContext } from 'astro/loaders';

import { envFlagOn } from '../lib/flags.ts';
import { isPublished, repositoryUrl } from '../lib/shelf.mjs';

/**
 * Herald Story 61.1: `PAGES_REUSE_RENDERED_DOCS` on, a page whose source, path and rendering pipeline are what an
 * earlier build in this tree rendered keeps that rendering (Astro's content store, `node_modules/.astro/`), as Astro's
 * own glob loader does. Rendering also reads whether the files a page links to exist, and which are folders
 * (`rehype-shelf-links.js`), and nothing here sees those change, so only a caller whose tree cannot change between its
 * builds turns it on: herald's tests, which build many times in one copy of the repository per process
 * (`tests/meta/pages_astro.py`). The Pages build leaves it off and renders every page, as before.
 */
function reuseRendered(): boolean {
  return envFlagOn('PAGES_REUSE_RENDERED_DOCS');
}

/** The code and the config a page's rendering runs through besides the page itself; any change renders every page. */
const PIPELINE_SOURCES = [
  '../../astro.config.mjs',
  '../rehype-shelf-links.js',
  '../rehype-markdown-links.js',
  '../rehype-base-paths.js',
  '../lib/shelf.mjs',
  '../lib/reader-text.ts',
  './shelf-docs-loader.ts',
];

async function pipelineFingerprint(base: string): Promise<string> {
  const sources = await Promise.all(PIPELINE_SOURCES.map((rel) => fs.readFile(new URL(rel, import.meta.url), 'utf8')));
  // The base path the link plugins write, and the repository page a link to an unpublished file goes to.
  return [base, repositoryUrl(''), ...sources].join('\0');
}

type Reuse = {
  fingerprint: string;
  digest: LoaderContext['generateDigest'];
  get: LoaderContext['store']['get'];
  reused: number;
};

// Which files are pages: one rule, shared with the link plugin (src/lib/shelf.mjs).
function isIncluded(relativePath: string): boolean {
  return isPublished(relativePath);
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

async function walkDocs(
  root: string,
  store: {
    set: LoaderContext['store']['set'];
  },
  siteRoot: string,
  renderMarkdown: LoaderContext['renderMarkdown'],
  seen: Set<string>,
  reuse: Reuse | null,
  prefix = '',
): Promise<void> {
  const entries = await fs.readdir(root, { withFileTypes: true });
  for (const entry of entries) {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      await walkDocs(full, store, siteRoot, renderMarkdown, seen, reuse, rel);
      continue;
    }
    if (!isIncluded(rel)) {
      continue;
    }
    const raw = await fs.readFile(full, 'utf8');
    const id = generateId(rel);
    seen.add(id);
    const digest = reuse ? reuse.digest(`${reuse.fingerprint}\0${rel}\0${raw}`) : undefined;
    if (reuse && digest !== undefined) {
      const kept = reuse.get(id);
      if (kept && kept.digest === digest && kept.rendered) {
        reuse.reused += 1;
        continue;
      }
    }
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
    // Story 53.2 (CAP-63): the published title drops the story id a page was filed under, and a page that states no
    // description takes its first paragraph.
    title = readerTitle(title);
    const entryData: Record<string, unknown> = { ...data, title, draft: false };
    if (typeof entryData.description !== 'string' || !entryData.description.trim()) {
      const about = firstParagraph(body);
      if (about) {
        entryData.description = about;
      }
    }
    if (!Array.isArray(entryData.head)) {
      entryData.head = [];
    }
    const sidebar = entryData.sidebar;
    if (typeof sidebar !== 'object' || sidebar === null) {
      entryData.sidebar = { hidden: false };
    }
    store.set({
      id,
      data: entryData,
      body,
      // Render the body here: an entry stored without `rendered` shows an empty page body
      // (every shelf page did so until 2026-10-14). The file URL lets the rehype link plugins
      // resolve relative links against the page's own location.
      rendered: await renderMarkdown(body, { fileURL: pathToFileURL(full) }),
      filePath: path.relative(siteRoot, full).replace(/\\/g, '/'),
      digest,
    });
  }
}

export function shelfDocsLoader(): Loader {
  return {
    name: 'shelf-docs-loader',
    async load({ store, config, renderMarkdown, generateDigest, logger }) {
      const root = fileURLToPath(new URL('../content/docs', import.meta.url));
      const siteRoot = fileURLToPath(config.root);
      const reuse: Reuse | null = reuseRendered()
        ? {
            fingerprint: await pipelineFingerprint(config.base),
            digest: generateDigest,
            get: (id) => store.get(id),
            reused: 0,
          }
        : null;
      const seen = new Set<string>();
      await walkDocs(root, store, siteRoot, renderMarkdown, seen, reuse);
      // Story 61.1: the store outlives a build in the same tree, so a page that is gone leaves it too.
      for (const id of store.keys()) {
        if (!seen.has(id)) {
          store.delete(id);
        }
      }
      if (reuse) {
        logger.info(`kept ${reuse.reused} of ${seen.size} rendered pages (PAGES_REUSE_RENDERED_DOCS)`);
      }
    },
  };
}
