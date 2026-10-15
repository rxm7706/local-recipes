/**
 * The root redirects of `docs-site/redirects.json` (Story 43.3, spec-pyforge-herald CAP-61; AD-21 rule 1).
 *
 * `legacy` is the frozen set of root paths the herald pages were served at before the `/herald/` mount, each a
 * file name (`dossier/index.html`, `infographics/atlas.html`): Astro's `redirects` writes `<path>/index.html` for
 * every key, so these stubs are written into the build after it, in the Jinja assembler's shape, each pointing at
 * its target by a relative URL (any host, any base path). `kedro-viz` stays an Astro redirect (Story 42.2).
 *
 * One owner per path: a stub whose path the build already holds -- a page, or a file from `public/` -- fails the
 * build naming it, never overwrites it. Node builtins only (the herald suite runs this module with node).
 */

import fs from 'node:fs';
import path from 'node:path';

export interface RedirectsFile {
  legacy: Record<string, string>;
  'kedro-viz': Record<string, string>;
}

export function readRedirects(file: string): RedirectsFile {
  return JSON.parse(fs.readFileSync(file, 'utf8')) as RedirectsFile;
}

function escapeAttr(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

/** The stub, as `assemble_pages.REDIRECT_TEMPLATE` writes it. */
export function redirectHtml(target: string): string {
  const t = escapeAttr(target);
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirect</title>
<meta http-equiv="refresh" content="0; url=${t}">
<link rel="canonical" href="${t}">
</head>
<body>
<p><a href="${t}">Continue</a></p>
</body>
</html>
`;
}

/** Write every legacy stub under `outDir`; refuses a non-HTML path and any path the build already holds. */
export function writeLegacyRedirects(outDir: string, legacy: Record<string, string>): string[] {
  const entries = Object.entries(legacy).map(([from, to]) => [from.replace(/^\//, ''), to.replace(/^\//, '')]);
  const notHtml = entries.filter(([from]) => !from.endsWith('.html')).map(([from]) => from);
  if (notHtml.length) {
    throw new Error(`legacy redirect(s) not to an HTML file (AD-21: a non-HTML file carries no redirect): ${notHtml.join(', ')}`);
  }
  const taken = entries.filter(([from]) => fs.existsSync(path.join(outDir, from))).map(([from]) => from);
  if (taken.length) {
    throw new Error(`legacy redirect path(s) already hold a page or file (AD-21 rule 1, one owner): ${taken.join(', ')}`);
  }
  for (const [from, to] of entries) {
    const dest = path.join(outDir, from);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, redirectHtml(path.posix.relative(path.posix.dirname(from), to)), 'utf8');
  }
  return entries.map(([from]) => from);
}
