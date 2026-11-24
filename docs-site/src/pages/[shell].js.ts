/**
 * /pf-shell.js -- the one header's script at a fixed URL at the site root (Story 53.1, spec-pyforge-herald CAP-63), for
 * every page that carries the header: the docs, the herald pages, the reader pages and the pages other stations mount.
 * An external file from the site's own origin, so no page's CSP lists a hash for it. Emitted only with
 * `pyforge.herald.site_shell` on. A dynamic route, `[shell]`.
 */
import type { APIRoute, GetStaticPaths } from 'astro';

import { siteShell } from '../lib/flags';
import { SHELL_SCRIPT, SHELL_SCRIPT_SOURCE } from '../lib/site-header';

export const getStaticPaths: GetStaticPaths = () =>
  siteShell() ? [{ params: { shell: SHELL_SCRIPT.slice(0, -'.js'.length) } }] : [];

export const GET: APIRoute = () =>
  new Response(SHELL_SCRIPT_SOURCE, { headers: { 'Content-Type': 'text/javascript; charset=utf-8' } });
