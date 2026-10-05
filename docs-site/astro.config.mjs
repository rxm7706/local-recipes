// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { getSiteUrl } from './src/lib/site-url.mjs';

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
  integrations: [
    starlight({
      title: 'PyForge documentation',
      sidebar: [
        {
          label: 'Tutorials',
          autogenerate: { directory: 'tutorials' },
        },
        {
          label: 'How-to',
          autogenerate: { directory: 'how-to' },
        },
        {
          label: 'Reference',
          autogenerate: { directory: 'reference' },
        },
        {
          label: 'Explanation',
          autogenerate: { directory: 'explanation' },
        },
      ],
    }),
  ],
});
