// @ts-check
import fs from 'node:fs';
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
import { pagesOneGenerator } from './src/lib/flags.ts';
import { populatePublic } from './scripts/populate-public.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const sidebarGenerated = path.join(__dirname, 'src', 'sidebar.generated.json');
if (!fs.existsSync(sidebarGenerated)) {
  throw new Error(
    `Missing ${sidebarGenerated}. Run pixi run -e site docs-site-sidebar before building.`,
  );
}
const sidebar = JSON.parse(fs.readFileSync(sidebarGenerated, 'utf8'));
// Story 40.1: the top menu (src/components/SiteTitle.astro) reads this file, written by the same generator.
const topnavGenerated = path.join(__dirname, 'src', 'topnav.generated.json');
if (!fs.existsSync(topnavGenerated)) {
  throw new Error(
    `Missing ${topnavGenerated}. Run pixi run -e site docs-site-sidebar before building.`,
  );
}
// Story 42.2 (CAP-60): the /kedro-viz/ redirect exists only with the Kedro-Viz mount. The generator
// decides that from the build input (docs/dashboard/kedro-viz/) and marks the menu entry it keeps.
const kedroVizMounted = JSON.parse(fs.readFileSync(topnavGenerated, 'utf8')).some(
  (item) => item.mount === 'kedro-viz',
);

// Story 43.3 (CAP-61): the root redirects -- the frozen legacy set and /kedro-viz/ -- read from one file.
const siteRedirects = readRedirects(path.join(__dirname, 'redirects.json'));

// Story 43.4's review (operator ruling 2026-10-15): with pyforge.herald.pages_one_generator on, one theme across the
// site -- Starlight's variables filled with the herald look (src/styles/theme.css), which the docs take through
// customCss and the herald pages through their own stylesheet. Off, Starlight's stock theme, as before.
const oneGenerator = pagesOneGenerator();

const siteUrl = getSiteUrl();
const urlParts = new URL(siteUrl);
const basePath =
  urlParts.pathname === '/'
    ? '/'
    : urlParts.pathname.endsWith('/')
      ? urlParts.pathname
      : `${urlParts.pathname}/`;

export default defineConfig({
  compressHTML: true,
  site: `${urlParts.origin}${basePath}`,
  base: basePath,
  outDir: './build/site',
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
  // The destination carries the host's base path: Astro writes it into the stub verbatim, and a bare
  // '/dashboard/kedro-viz/' sent the project site's /kedro-viz/ to the host's root (live until 2026-10-15).
  redirects: kedroVizMounted
    ? Object.fromEntries(
        Object.entries(siteRedirects['kedro-viz']).map(([from, to]) => [from, `${basePath}${to.replace(/^\//, '')}`]),
      )
    : {},
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
      customCss: oneGenerator ? ['./src/styles/theme.css'] : [],
      components: {
        SiteTitle: './src/components/SiteTitle.astro',
      },
    }),
    heraldArtifact(),
  ],
});

/**
 * Story 43.3 (CAP-61): with pyforge.herald.pages_one_generator on, the build assembles the herald side of the
 * artifact itself -- public/ written from scratch before the build (twins, downloads, dashboard exports), and the
 * legacy root redirects written into it after, refusing any path the build already holds (AD-21 rule 1); a route
 * whose output is a file public/ already serves fails the build too (Astro itself only warns). Off, public/ is
 * emptied and the Jinja path's assembler does both, as before.
 *
 * Story 43.4 and its review: off, no herald page renders and the docs keep Starlight's stock theme, so every
 * stylesheet under src/styles/ loads empty and the build emits none of their files; the Jinja path serves its own.
 */
function heraldArtifact() {
  /** @type {string[]} the files populatePublic wrote, judged against the routes' output at build end */
  let served = [];
  const heraldStyles = /[\\/]src[\\/]styles[\\/][^\\/]+\.css$/;
  return {
    name: 'herald-artifact',
    hooks: {
      'astro:config:setup': ({ updateConfig }) => {
        if (!oneGenerator) {
          const load = (id) => (heraldStyles.test(id.split('?')[0]) ? '' : undefined);
          updateConfig({ vite: { plugins: [{ name: 'herald-styles-off', enforce: 'pre', load }] } });
        }
      },
      'astro:build:start': () => {
        served = populatePublic(path.join(__dirname, 'public'), oneGenerator);
      },
      'astro:build:done': ({ dir, assets }) => {
        refusePublicCollisions(fileURLToPath(dir), served, assets);
        if (oneGenerator) {
          writeLegacyRedirects(fileURLToPath(dir), siteRedirects.legacy);
        }
      },
    },
  };
}
