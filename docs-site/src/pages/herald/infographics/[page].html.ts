/**
 * /herald/infographics/<page>.html -- the reader's page for one infographic (Story 43.2, CAP-61 on
 * CAP-55): the back-bar around the twin scripts/populate-public.mts copies under /herald/twins/, which is never
 * edited. An endpoint because the page keeps the 2026-10-13 URL, a file name rather than a directory.
 */
import type { APIRoute, GetStaticPaths } from 'astro';

import { infographicBackbar, twinWrapperHtml, type Infographic } from '../../../lib/herald-pages';
import { loadHeraldPages } from '../../../loaders/herald-pages-loader';

export const getStaticPaths: GetStaticPaths = () => {
  return loadHeraldPages().infographics.map((ig) => ({
    params: { page: ig.outName.slice(0, -'.html'.length) },
    props: { ig },
  }));
};

export const GET: APIRoute = ({ props }) => {
  const { ig } = props as { ig: Infographic };
  const html = twinWrapperHtml({ title: ig.title, backbar: infographicBackbar(ig.title, `../${ig.twin}`), rel: '../', twin: ig.twin });
  return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
};
