/**
 * `/llms.txt` and `/llms-full.txt` (Story 43.6, spec-pyforge-herald CAP-61): the shelf's pages (`docs/map.yaml`)
 * and herald's (the map's `herald` section) for agents, the first as the llmstxt.org index, the second with each
 * page's text. Emitted only with `pyforge.herald.pages_one_generator` on; off, `getStaticPaths` lists nothing and
 * neither file exists. The hand-maintained `docs/reference/*-llms-full.md` catalogues are `scribe catalog`'s and
 * are not these files.
 */
import type { APIRoute } from 'astro';

import { llmsSections } from '../lib/agent-data.ts';
import { llmsFullTxt, llmsTxt, pagesOneGenerator } from '../lib/agent-surface.ts';

export function getStaticPaths() {
  return pagesOneGenerator() ? [{ params: { llms: 'llms' } }, { params: { llms: 'llms-full' } }] : [];
}

export const GET: APIRoute = async ({ params, site }) => {
  if (!site) {
    throw new Error('llms.txt needs the site URL (astro.config.mjs site)');
  }
  const surface = await llmsSections(site);
  const body =
    params.llms === 'llms-full'
      ? llmsFullTxt({ ...surface, sections: surface.sections.filter((section) => section.name !== 'Data') })
      : llmsTxt(surface);
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
