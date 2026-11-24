/**
 * /herald/pipelines/index.html -- the reader's page around the mounted Kedro-Viz export (Story 53.3,
 * spec-pyforge-herald CAP-63): the one site header, then atlas's app in a frame filling the rest of the page, with a
 * link to the app by itself. The export under /dashboard/kedro-viz/ is upstream's build, mounted verbatim and never
 * written to (AD-21 rule 5); this page is how a reader reaches it without losing the site. Emitted only with
 * `pyforge.herald.site_shell` on and the export in the build input -- the rule the menu's section follows
 * (`src/lib/nav.ts`). An endpoint, as the other reader pages are. A dynamic route, `[page]`.
 */
import type { APIRoute, GetStaticPaths } from 'astro';

import path from 'node:path';

import { siteShell } from '../../../lib/flags';
import { frameBackbar, twinWrapperHtml } from '../../../lib/herald-pages';
import { holdsAFile, KEDRO_VIZ_FRAME, KEDRO_VIZ_MOUNT } from '../../../lib/nav';
import { siteHeaderHtml } from '../../../lib/site-header';
import { siteNav } from '../../../lib/site-nav';
import { heraldPagesRoot } from '../../../loaders/herald-pages-loader';

const TITLE = 'Kedro-Viz: the Atlas pipelines';

export const getStaticPaths: GetStaticPaths = () => {
  const mounted = holdsAFile(path.join(heraldPagesRoot(), 'docs', 'dashboard', 'kedro-viz'));
  return siteShell() && mounted ? [{ params: { page: 'index' } }] : [];
};

export const GET: APIRoute = () => {
  // from /herald/pipelines/ the herald mount is one level up, the site root two
  const app = `../${KEDRO_VIZ_MOUNT}`;
  const html = twinWrapperHtml({
    title: TITLE,
    backbar: frameBackbar(TITLE, `../${app}`),
    rel: '../',
    twin: app,
    description:
      'The Atlas data pipelines as an interactive Kedro-Viz graph, from the latest export, under the PyForge site header.',
    header: siteHeaderHtml(siteNav().sections, { toRoot: '../../', pagePath: KEDRO_VIZ_FRAME }),
  });
  return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
};
