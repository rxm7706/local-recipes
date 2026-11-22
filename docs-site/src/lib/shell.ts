/**
 * The one header on the pages other stations mount (Story 53.1, spec-pyforge-herald CAP-63; pyforge-herald:AD-23,
 * amended 2026-11-22), written at `astro:build:done` beside the CSP pass (`src/lib/artifact.ts`): each HTML page of the
 * tree mounted at `dashboard/` (the Vizro export, steward's `deploy static` boards) and of the marketplace gets the theme script, a link to the site's
 * theme sheet, the header's script and the header itself, and its body becomes the page's `<main>`. The mounting
 * station ships no copy of the menu; it reads the theme variables by name, with fallbacks of its own. The Kedro-Viz
 * mount is upstream's app and is never written to.
 *
 * Node builtins only: the herald tests import this module with node's type stripping.
 */

import fs from 'node:fs';
import path from 'node:path';

import { HERALD_THEME } from './herald-pages.ts';
import type { MapSection } from './nav.ts';
import { KEDRO_VIZ_MOUNT } from './nav.ts';
import { MAIN_ID, SHELL_SCRIPT, siteHeaderHtml, themeScript } from './site-header.ts';

/**
 * The mounted trees that take the header, each with the menu path its pages sit under: the whole `/dashboard/` tree
 * (the Vizro export and steward's `deploy static` boards) but `skip`, and the marketplace.
 */
export const SHELL_MOUNTS: ReadonlyArray<{ prefix: string; pagePath: string; skip?: string[] }> = [
  { prefix: 'dashboard/', pagePath: 'dashboard/vizro/', skip: [KEDRO_VIZ_MOUNT] },
  { prefix: 'marketplace/', pagePath: 'marketplace/' },
];

const HEADER_MARK = /\bdata-pf-header\b/;

/**
 * `html` (a mounted page at `rel`, site-root relative) with the header; `null` when it has one. A page written
 * without `<head>` and `<body>` tags (HTML allows it) gets them: its `<title>` stays in the head, the rest is the body.
 */
export function withShell(html: string, rel: string, pagePath: string, sections: MapSection[]): string | null {
  if (HEADER_MARK.test(html)) {
    return null;
  }
  const toRoot = '../'.repeat(rel.split('/').length - 1);
  const headAdd =
    `<script>${themeScript(true)}</script>` +
    `<link rel="stylesheet" href="${toRoot}herald/${HERALD_THEME}">` +
    `<script defer src="${toRoot}${SHELL_SCRIPT}"></script>`;
  // The page's own path decides `aria-current`: the section's index is the page, a page under it is not, and a
  // page under no section of the menu (a board mounted beside the exports) marks nothing.
  const own = rel.replace(/index\.html$/, '');
  const listed = own.startsWith(pagePath);
  const header = siteHeaderHtml(sections, { toRoot, pagePath: listed ? own : pagePath, unlisted: !listed });
  const framed = (inner: string): string => {
    // A page that brings its own <main> keeps it: the skip link lands on a wrapper around it.
    const wrap = /<main\b/i.test(inner) ? 'div' : 'main';
    return `${header}<${wrap} id="${MAIN_ID}" class="pf-mounted">${inner}</${wrap}>`;
  };
  const head = /<\/head>/i.exec(html);
  const bodyOpen = /<body\b[^>]*>/i.exec(html);
  const closes = [...html.matchAll(/<\/body\s*>/gi)];
  const bodyClose = closes.length ? (closes[closes.length - 1].index ?? -1) : -1;
  if (head && bodyOpen && bodyClose >= 0 && bodyOpen.index > head.index) {
    const bodyStart = bodyOpen.index + bodyOpen[0].length;
    return (
      html.slice(0, head.index) +
      headAdd +
      html.slice(head.index, bodyStart) +
      framed(html.slice(bodyStart, bodyClose)) +
      html.slice(bodyClose)
    );
  }
  if (head || bodyOpen || /<head\b/i.test(html)) {
    return null; // half-written structure: left as it is, and pages-check names the page
  }
  // No <head> and no <body>: the page opens with its doctype, perhaps an <html> tag, then what belongs in a head
  // (meta, title, link, style, base), then its content. Anything else ahead of that is left as it is.
  const lead = /^\s*(?:<!doctype[^>]*>)?\s*(?:<html\b([^>]*)>)?/i.exec(html);
  if (!lead || /^\s*(?:<!--|<\?)/.test(html)) {
    return null;
  }
  let rest = html.slice(lead[0].length).replace(/<\/html\s*>\s*$/i, '');
  let hoisted = '';
  for (;;) {
    const one = /^\s*(?:<(?:meta|link|base)\b[^>]*>|<title\b[^>]*>[\s\S]*?<\/title>|<style\b[^>]*>[\s\S]*?<\/style>)/i.exec(rest);
    if (!one) {
      break;
    }
    hoisted += one[0].trim();
    rest = rest.slice(one[0].length);
  }
  const attrs = lead[1]?.trim() ? ` ${lead[1].trim()}` : ' lang="en"';
  const charset = /<meta\s+charset\b/i.test(hoisted) ? '' : '<meta charset="utf-8">';
  return `<!doctype html><html${attrs}><head>${charset}${hoisted}${headAdd}</head><body>${framed(rest)}</body></html>\n`;
}

/** Give every mounted page of `outDir` the header; returns the pages written. */
export function addShell(outDir: string, sections: MapSection[]): string[] {
  const written: string[] = [];
  for (const mount of SHELL_MOUNTS) {
    const dir = path.join(outDir, mount.prefix);
    if (!fs.existsSync(dir)) {
      continue;
    }
    const pages = fs
      .readdirSync(dir, { recursive: true, encoding: 'utf8' })
      .map((rel) => `${mount.prefix}${rel.split(path.sep).join('/')}`)
      .filter((rel) => rel.endsWith('.html') && fs.statSync(path.join(outDir, rel)).isFile())
      .sort();
    for (const rel of pages) {
      if ((mount.skip ?? []).some((prefix) => rel.startsWith(prefix))) {
        continue;
      }
      const file = path.join(outDir, rel);
      const next = withShell(fs.readFileSync(file, 'utf8'), rel, mount.pagePath, sections);
      if (next !== null) {
        fs.writeFileSync(file, next);
        written.push(rel);
      }
    }
  }
  return written;
}
