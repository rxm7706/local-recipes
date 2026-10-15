// The one rule for which files under docs/ the site serves, and where (local, not vendored).
// The shelf loader (src/loaders/shelf-docs-loader.ts) and the link plugin (src/rehype-shelf-links.js)
// both read it, so a page and the links to it can never disagree.

export const QUADRANTS = new Set(['tutorials', 'how-to', 'reference', 'explanation']);

/** True when `relativePath` (POSIX, relative to docs/) is a page the shelf publishes. */
export function isPublished(relativePath) {
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

/**
 * The site route of a directory under docs/ (POSIX, '' for docs/ itself), or null when the site has
 * no page there. A directory is a page when it holds a published README.md or index.md (the loader
 * publishes either as the directory's index); docs/ itself is the site root.
 */
export function directoryRoute(relativeDir, exists) {
  const norm = relativeDir.replace(/\\/g, '/').replace(/\/$/, '');
  if (norm === '') {
    return '/';
  }
  for (const index of ['README.md', 'index.md']) {
    const candidate = `${norm}/${index}`;
    if (isPublished(candidate) && exists(candidate)) {
      return `/${norm}/`;
    }
  }
  return null;
}

/**
 * The site path of a file under docs/ that the Pages build serves in the artifact as-is, or null:
 * scripts/populate-public.mts copies docs/dashboard/ (all but its README.md) to /dashboard/.
 */
export function servedStaticPath(relativePath, isDirectory = false) {
  const norm = relativePath.replace(/\\/g, '/').replace(/\/$/, '');
  if (!norm.startsWith('dashboard/') || norm === 'dashboard/README.md') {
    return null;
  }
  return isDirectory ? `/${norm}/` : `/${norm}`;
}

/** The repository page for a repo-relative path, for links to files the site does not serve. */
export function repositoryUrl(repoRelativePath, isDirectory = false) {
  const server = (process.env.GITHUB_SERVER_URL || 'https://github.com').replace(/\/$/, '');
  const repo = process.env.GITHUB_REPOSITORY || 'rxm7706/local-recipes';
  const encoded = repoRelativePath.replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/');
  return `${server}/${repo}/${isDirectory ? 'tree' : 'blob'}/main/${encoded}`;
}
