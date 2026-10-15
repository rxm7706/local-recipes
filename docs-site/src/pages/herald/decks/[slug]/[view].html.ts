/**
 * /herald/decks/<slug>/<view>.html -- the reader's page for a family's Infographic Deck or Executive
 * Summary (Story 43.2, CAP-61 on CAP-35 and CAP-55): the back-bar around the twin docsite/build.py
 * copied under /herald/twins/, which is never edited. An endpoint because the page keeps the
 * 2026-10-13 URL, a file name rather than a directory. With pyforge.herald.pages_one_generator off it
 * emits nothing and the Jinja page is the only one.
 */
import type { APIRoute, GetStaticPaths } from 'astro';

import { familyViewBackbar, twinWrapperHtml, type Family, type FamilyView } from '../../../../lib/herald-pages';
import { loadHeraldPages, pagesOneGenerator } from '../../../../loaders/herald-pages-loader';

export const getStaticPaths: GetStaticPaths = () => {
  if (!pagesOneGenerator()) {
    return [];
  }
  return loadHeraldPages().families.flatMap((family) =>
    family.views.map((view) => ({
      params: { slug: family.slug, view: view.outName.slice(0, -'.html'.length) },
      props: { family, view },
    })),
  );
};

export const GET: APIRoute = ({ props }) => {
  const { family, view } = props as { family: Family; view: FamilyView };
  const title = `${family.title} — ${view.label}`;
  const html = twinWrapperHtml({ title, backbar: familyViewBackbar(family.title, title, `../../${view.twin}`), rel: '../../', twin: view.twin });
  return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
};
