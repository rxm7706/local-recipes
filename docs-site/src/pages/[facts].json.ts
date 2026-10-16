/**
 * `/facts.json` (Story 43.6, spec-pyforge-herald CAP-61): every `presentations/<slug>/facts.yaml` as one JSON
 * document, one object per deck keyed by its `deck` slug. A `facts.yaml` with no `deck` fails the build naming
 * the file.
 */
import type { APIRoute } from 'astro';

import { facts } from '../lib/agent-data.ts';

export function getStaticPaths() {
  return [{ params: { facts: 'facts' } }];
}

export const GET: APIRoute = () =>
  new Response(`${JSON.stringify(facts(), null, 2)}\n`, {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
