/**
 * Rehype plugin (local, not vendored): make a shelf page's local links resolve on the site.
 *
 * Runs before the vendored rehype-markdown-links and rehype-base-paths. For each `a[href]` that is
 * neither external nor an in-page anchor, it resolves the target against the page's real file
 * (docs/ reached through the content symlink), decoding percent-escapes, and:
 *   - a page the shelf publishes: a `README.md` link becomes `index.md`, because the shelf loader
 *     publishes every README as its directory's index (`how-to/README.md` -> `/how-to/`), while the
 *     vendored plugin would map it to `/how-to/README/`; any other page link is left for the vendored
 *     plugin;
 *   - a directory: its absolute site route (`/how-to/`), because a non-index page is served one level
 *     deeper than its file (`how-to/x.md` -> `/how-to/x/`), so a relative `../` would land one level off;
 *     a directory with no page goes to its repository tree;
 *   - a file the Pages assembler serves as-is (docs/dashboard/**): its site path;
 *   - any other file in the repository (docs/MAP.md, docs/governance/**, a JSON or TOML file, anything
 *     outside docs/): its repository page, so the reader reaches it instead of a 404;
 *   - a missing target: left alone, for the upstream link validator and pages-check to report.
 * Query strings and fragments are kept.
 */

import fs from 'node:fs';
import path from 'node:path';
import { visit } from 'unist-util-visit';

import { detectContentDir, findFirstDelimiter } from './rehype-markdown-links.js';
import { directoryRoute, isPublished, repositoryUrl, servedStaticPath } from './lib/shelf.mjs';

const EXTERNAL = /^(?:[a-z][a-z0-9+.-]*:|\/\/|#)/i;

function decode(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function inside(parent, child) {
  const rel = path.relative(parent, child);
  return !rel.startsWith('..') && !path.isAbsolute(rel) ? rel.split(path.sep).join('/') : null;
}

export default function rehypeShelfLinks() {
  return (tree, file) => {
    if (!file.path) return;
    const contentDir = detectContentDir(file.path);
    if (!contentDir) return;
    const docsDir = fs.realpathSync(contentDir);
    const repoRoot = path.dirname(docsDir);
    const pageFile = fs.realpathSync(file.path);
    const existsInDocs = (rel) => fs.existsSync(path.join(docsDir, rel));

    visit(tree, 'element', (node) => {
      if (node.tagName !== 'a' || typeof node.properties?.href !== 'string') return;
      const href = node.properties.href;
      if (!href || EXTERNAL.test(href)) return;

      const delim = findFirstDelimiter(href);
      const linkPath = delim === -1 ? href : href.slice(0, delim);
      const suffix = delim === -1 ? '' : href.slice(delim);
      if (!linkPath) return;

      const fsPath = decode(linkPath);
      const target = fsPath.startsWith('/')
        ? path.join(docsDir, fsPath.replace(/^\/docs\//, '/'))
        : path.resolve(path.dirname(pageFile), fsPath);
      let stat;
      try {
        stat = fs.statSync(target);
      } catch {
        return; // missing: leave it for the link validator and pages-check
      }
      const isDirectory = stat.isDirectory();
      const inDocs = inside(docsDir, target);

      if (inDocs !== null) {
        if (!isDirectory && isPublished(inDocs)) {
          node.properties.href = linkPath.replace(/(^|\/)README\.md$/, '$1index.md') + suffix;
          return;
        }
        if (isDirectory) {
          const route = directoryRoute(inDocs, existsInDocs);
          if (route) {
            node.properties.href = route + suffix;
            return;
          }
        }
        const served = servedStaticPath(inDocs, isDirectory);
        if (served) {
          node.properties.href = served + suffix;
          return;
        }
      }
      const inRepo = inside(repoRoot, target);
      if (inRepo === null) return;
      node.properties.href = repositoryUrl(inRepo, isDirectory) + suffix;
    });
  };
}
