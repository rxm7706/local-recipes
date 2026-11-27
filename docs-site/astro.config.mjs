// @ts-check
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { unified } from '@astrojs/markdown-remark';
import rehypeShelfLinks from './src/rehype-shelf-links.js';
import rehypeMarkdownLinks from './src/rehype-markdown-links.js';
import rehypeBasePaths from './src/rehype-base-paths.js';
import { getSiteUrl } from './src/lib/site-url.mjs';
import { readRedirects, refusePublicCollisions, writeLegacyRedirects } from './src/lib/redirects.ts';
import { addCsp, writeArtifactDossier } from './src/lib/artifact.ts';
import { addShell } from './src/lib/shell.ts';
import { envFlagOn, siteShell } from './src/lib/flags.ts';
import { holdsAFile } from './src/lib/nav.ts';
import { siteNav } from './src/lib/site-nav.ts';
import { heraldPagesRoot } from './src/loaders/herald-pages-loader.ts';
import { populatePublic } from './scripts/populate-public.mts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Story 43.7 (CAP-61): the docs sidebar -- the four quadrants from docs/map.yaml's pages, then its sections -- from the
// one registry, read once per build (src/lib/site-nav.ts); the top menu and the home's doors read the same.
const sidebar = siteNav().sidebar;
// Story 42.2 (CAP-60): the /kedro-viz/ redirect exists only with the Kedro-Viz mount, decided from the build input
// (docs/dashboard/kedro-viz/ holding a file) by the rule the menu and populate-public decide it by.
const kedroVizMounted = holdsAFile(path.join(heraldPagesRoot(), 'docs', 'dashboard', 'kedro-viz'));

// Story 43.3 (CAP-61): the root redirects -- the frozen legacy set and /kedro-viz/ -- read from one file.
const siteRedirects = readRedirects(path.join(__dirname, 'redirects.json'));

const siteUrl = getSiteUrl();
const urlParts = new URL(siteUrl);
const basePath =
  urlParts.pathname === '/'
    ? '/'
    : urlParts.pathname.endsWith('/')
      ? urlParts.pathname
      : `${urlParts.pathname}/`;

// The destination carries the host's base path: Astro writes it into the stub verbatim, and a bare
// '/dashboard/kedro-viz/' sent the project site's /kedro-viz/ to the host's root (live until 2026-10-15).
const redirects = kedroVizMounted
  ? Object.fromEntries(
      Object.entries(siteRedirects['kedro-viz']).map(([from, to]) => [from, `${basePath}${to.replace(/^\//, '')}`]),
    )
  : {};

// Herald Story 61.1: with PAGES_REUSE_RENDERED_DOCS on (herald's test builds; src/loaders/shelf-docs-loader.ts), each
// set of redirects keeps its own content store. Astro empties its store whenever this config changes, and the tests'
// builds turn the Kedro-Viz mount, and with it the redirects, on and off. The Pages build keeps Astro's default.
const cacheDir = envFlagOn('PAGES_REUSE_RENDERED_DOCS')
  ? `./node_modules/.astro-${createHash('sha256').update(JSON.stringify(redirects)).digest('hex').slice(0, 12)}/`
  : undefined;

export default defineConfig({
  compressHTML: true,
  site: `${urlParts.origin}${basePath}`,
  base: basePath,
  outDir: './build/site',
  ...(cacheDir ? { cacheDir } : {}),
  // The shelf's links: the local plugin points README.md at the directory index and sends links to
  // repo files the shelf does not publish to their repository page; then upstream's .md -> route and
  // base-path plugins (vendored byte-identical, docs-site/README.md).
  markdown: {
    processor: unified({
      rehypePlugins: [
        [rehypeShelfLinks],
        [rehypeMarkdownLinks, { base: basePath }],
        [rehypeBasePaths, { base: basePath }],
      ],
    }),
  },
  redirects,
  integrations: [
    starlight({
      title: 'PyForge documentation',
      defaultLocale: 'root',
      locales: {
        root: {
          label: 'English',
          lang: 'en',
        },
      },
      sidebar,
      // Story 43.4's review (operator ruling 2026-10-15): one theme across the site -- Starlight's variables filled
      // with the herald look (src/styles/theme.css), which the docs take here and the herald pages through their own.
      customCss: ['./src/styles/theme.css', './src/styles/shell.css'],
      components: {
        SiteTitle: './src/components/SiteTitle.astro',
        // Story 43.5: the built-from line under Starlight's footer.
        Footer: './src/components/Footer.astro',
        // Story 43.7: the home's doors, from the registry, ahead of the docs root's markdown.
        MarkdownContent: './src/components/MarkdownContent.astro',
        // Story 53.1 (CAP-63), behind pyforge.herald.site_shell: the one site header in place of Starlight's, and
        // the stored-theme-else-dark rule in place of Starlight's stored-theme-else-system one.
        ...(siteShell()
          ? {
              Header: './src/components/Header.astro',
              ThemeProvider: './src/components/ThemeProvider.astro',
              MobileMenuFooter: './src/components/MobileMenuFooter.astro',
            }
          : {}),
      },
    }),
    heraldArtifact(),
  ],
});

/**
 * The herald side of the artifact, assembled by the build itself (Stories 43.3 and 43.7, CAP-61): `public/` written
 * from scratch before the build (twins, downloads, dashboard exports, font licences); after it, the legacy root
 * redirects, refusing any path the build already holds (AD-21 rule 1) -- a route whose output is a file `public/` serves
 * fails the build too (Astro itself only warns) -- then the artifact build of the dossier and every page's CSP
 * (`src/lib/artifact.ts`).
 */
function heraldArtifact() {
  /** @type {string[]} the files populatePublic wrote, judged against the routes' output at build end */
  let served = [];
  return {
    name: 'herald-artifact',
    hooks: {
      'astro:build:start': () => {
        served = populatePublic(path.join(__dirname, 'public'));
      },
      'astro:build:done': ({ dir, assets }) => {
        const outDir = fileURLToPath(dir);
        refusePublicCollisions(outDir, served, assets);
        writeLegacyRedirects(outDir, siteRedirects.legacy);
        writeArtifactDossier(outDir, basePath);
        // Story 53.1 (CAP-63; AD-23 amended 2026-11-22): the pages other stations mount get the one header here.
        if (siteShell()) {
          addShell(outDir, siteNav().sections);
        }
        addCsp(outDir);
      },
    },
  };
}
