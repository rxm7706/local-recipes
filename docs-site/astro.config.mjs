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
  redirects: {
    '/kedro-viz/': '/dashboard/kedro-viz/',
  },
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
      components: {
        SiteTitle: './src/components/SiteTitle.astro',
      },
    }),
  ],
});
