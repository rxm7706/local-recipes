/**
 * /herald/fonts.css -- the herald pages' faces at one fixed URL (Story 43.4, spec-pyforge-herald CAP-61; AD-21, AD-23)
 * for the pages Astro does not style: each twin under /herald/twins/ (its one vendored font link, Story 31.3's
 * mechanism) and each reader page's back-bar. The stylesheet is `styles/herald-fonts.css` as Vite builds it, so every
 * face it names is an @fontsource file Astro emits under the artifact's own `_astro/`; the herald layouts import the
 * same file through `styles/herald.css`. A rest-shaped route, so with pyforge.herald.pages_one_generator off it emits
 * nothing.
 */
import type { APIRoute, GetStaticPaths } from 'astro';

import { HERALD_FONTS } from '../../lib/herald-pages';
import { pagesOneGenerator } from '../../loaders/herald-pages-loader';
import fontsCss from '../../styles/herald-fonts.css?inline';

export const getStaticPaths: GetStaticPaths = () =>
  pagesOneGenerator() ? [{ params: { fonts: HERALD_FONTS.slice(0, -'.css'.length) } }] : [];

export const GET: APIRoute = () => new Response(fontsCss, { headers: { 'Content-Type': 'text/css; charset=utf-8' } });
