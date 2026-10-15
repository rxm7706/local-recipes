/**
 * What the build writes into its own output at `astro:build:done` (Story 43.7, spec-pyforge-herald CAP-61), after
 * every page exists:
 *
 * - **The CSP of every page** (AD-21; the CSP decision of Story 43.7, recorded in its change log): every HTML page the
 *   build rendered carries one `Content-Security-Policy` meta. The herald layouts and reader pages write
 *   `HERALD_CSP` themselves; every Starlight page -- the shelf, `/changes/`, `/status/**`, the 404 -- gets the same
 *   policy here, its own inline scripts (Starlight's theme, sidebar and search glue) allowed by hash and
 *   `'wasm-unsafe-eval'` for the Pagefind search, as the first element of its head. Redirect stubs, the twins, the
 *   artifact build and the mounted `dashboard/` tree are no pages of the build's and are left as they are.
 * - **The artifact build** `herald/artifact/dossier.html` (CAP-47): the built dossier page, single file, for the
 *   Claude Artifact tool -- its title, the stylesheets it links with the faces it names inlined as data URIs (the three
 *   families the dossier reads), and its body between the menu and the built-from line. No `<!doctype>`, `<html>`,
 *   `<head>` or `<body>`: the Artifact host supplies them and wraps what it is given. Republishing "The PyForge
 *   Dossier" from this file keeps the shared dossier link (`site.yml`'s `artifact.url`) current.
 *
 * Node builtins only: the herald tests import this module with node's type stripping.
 */

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { cspWith } from './herald-pages.ts';

/** Where the artifact build is written, relative to the build's output. */
export const ARTIFACT_DOSSIER = 'herald/artifact/dossier.html';
/** The built page it is made from. */
export const BUILT_DOSSIER = 'herald/dossier/index.html';
/** The families the dossier reads, the only faces the artifact inlines (the Jinja artifact's three). */
export const ARTIFACT_FONT_FAMILIES = ['Big Shoulders Display', 'IBM Plex Sans', 'IBM Plex Mono'];
/** Output the CSP pass never touches: no page of the build's own. */
export const NOT_PAGES = ['herald/twins/', 'herald/artifact/', 'dashboard/', 'pagefind/'];

const CSP_META = /<meta\s+http-equiv=["']Content-Security-Policy["']/i;
const REFRESH = /<meta\s+http-equiv=["']refresh["']/i;
const INLINE_SCRIPT = /<script\b(?![^>]*\bsrc\s*=)[^>]*>([\s\S]*?)<\/script>/gi;

function htmlFiles(dir: string): string[] {
  return fs
    .readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .map((rel) => rel.split(path.sep).join('/'))
    .filter((rel) => rel.endsWith('.html') && fs.statSync(path.join(dir, rel)).isFile())
    .sort();
}

const sha256 = (text: string): string => `'sha256-${createHash('sha256').update(text, 'utf8').digest('base64')}'`;

/** `html` with one CSP meta first in its head, allowing exactly its own inline scripts; `null` when it needs none. */
export function withCsp(html: string): string | null {
  if (CSP_META.test(html) || REFRESH.test(html)) {
    return null;
  }
  const head = /<head\b[^>]*>/i.exec(html);
  if (!head) {
    return null;
  }
  const hashes = [...new Set([...html.matchAll(INLINE_SCRIPT)].map((m) => sha256(m[1])))];
  const meta = `<meta http-equiv="Content-Security-Policy" content="${cspWith(["'wasm-unsafe-eval'", ...hashes])}">`;
  const end = head.index + head[0].length;
  return `${html.slice(0, end)}${meta}${html.slice(end)}`;
}

/** Give every page of `outDir` its CSP; returns the pages written. */
export function addCsp(outDir: string): string[] {
  const written: string[] = [];
  for (const rel of htmlFiles(outDir)) {
    if (NOT_PAGES.some((prefix) => rel.startsWith(prefix))) {
      continue;
    }
    const file = path.join(outDir, rel);
    const out = withCsp(fs.readFileSync(file, 'utf8'));
    if (out !== null) {
      fs.writeFileSync(file, out);
      written.push(rel);
    }
  }
  return written;
}

/** A root-absolute URL under `base` as a file of `outDir`, or `null`. */
function fileOf(outDir: string, base: string, url: string): string | null {
  const clean = url.split(/[?#]/)[0];
  if (!clean.startsWith(base)) {
    return null;
  }
  const file = path.join(outDir, decodeURIComponent(clean.slice(base.length)));
  return fs.existsSync(file) && fs.statSync(file).isFile() ? file : null;
}

const MIME: Record<string, string> = { '.woff2': 'font/woff2', '.woff': 'font/woff', '.svg': 'image/svg+xml', '.png': 'image/png' };

/** `css` with only the artifact's faces, every `url()` the build holds inlined as a data URI. */
export function inlineCss(css: string, outDir: string, base: string): string {
  const faces = css.replace(/@font-face\s*\{[^}]*\}/gi, (face) => {
    const family = /font-family\s*:\s*["']?([^;"'}]+)/i.exec(face)?.[1].trim() ?? '';
    return ARTIFACT_FONT_FAMILIES.includes(family) ? face : '';
  });
  return faces.replace(/url\(\s*(["']?)([^)"']+)\1\s*\)/gi, (whole, _quote: string, url: string) => {
    const file = fileOf(outDir, base, url);
    if (!file) {
      return whole;
    }
    const mime = MIME[path.extname(file)] ?? 'application/octet-stream';
    return `url(data:${mime};base64,${fs.readFileSync(file).toString('base64')})`;
  });
}

/** The artifact build from the built dossier page under `outDir`, served under `base` (`/` or `/repo/`). */
export function artifactDossier(outDir: string, base: string): string {
  const page = fs.readFileSync(path.join(outDir, BUILT_DOSSIER), 'utf8');
  const title = /<title>([\s\S]*?)<\/title>/i.exec(page)?.[1] ?? 'The PyForge Dossier';
  const head = page.slice(0, page.search(/<\/head>/i));
  const sheets = [...head.matchAll(/<link\b[^>]*\brel=["']?stylesheet["']?[^>]*>/gi)].map((m) => /\bhref=["']?([^"'\s>]+)/i.exec(m[0])?.[1] ?? '');
  const css = [
    ...sheets.map((href) => fileOf(outDir, base, href)).filter((file): file is string => file !== null).map((file) => fs.readFileSync(file, 'utf8')),
    ...[...head.matchAll(/<(style)\b[^>]*>([\s\S]*?)<\/\1>/gi)].map((m) => m[2]),
  ].join('\n');
  const bodyStart = page.search(/<\/header>/i);
  const bodyEnd = page.search(/<p class="built-from"/);
  if (bodyStart < 0 || bodyEnd < bodyStart) {
    throw new Error(`${BUILT_DOSSIER}: no body between the menu and the built-from line to make the artifact from`);
  }
  const body = page.slice(bodyStart + '</header>'.length, bodyEnd).trim();
  // The built bundle's own CSS, inlined: no source of this site declares it here (the theme is theme.css's).
  const style = ['<style>', inlineCss(css, outDir, base), '</style>'].join('\n');
  return `<title>${title}</title>\n${style}\n\n${body}\n`;
}

/** Write the artifact build into `outDir`. */
export function writeArtifactDossier(outDir: string, base: string): string {
  const file = path.join(outDir, ARTIFACT_DOSSIER);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, artifactDossier(outDir, base));
  return ARTIFACT_DOSSIER;
}
