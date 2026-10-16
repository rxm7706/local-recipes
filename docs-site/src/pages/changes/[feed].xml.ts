/**
 * `/changes/rss.xml` (Story 43.6, spec-pyforge-herald CAP-61): RSS 2.0 over the `changes.json` build input, the
 * same merges as `/changes/` in the same order, each item linking its entry on that page. With the input absent
 * the channel is empty.
 */
import type { APIRoute } from 'astro';

import { changesInput } from '../../lib/agent-data.ts';
import { changesFeed } from '../../lib/agent-surface.ts';

export function getStaticPaths() {
  return [{ params: { feed: 'rss' } }];
}

export const GET: APIRoute = ({ site }) => {
  if (!site) {
    throw new Error('changes/rss.xml needs the site URL (astro.config.mjs site)');
  }
  const input = changesInput();
  const body = changesFeed(input.present ? input.value : null, new URL('changes/', site).href);
  return new Response(body, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
};
