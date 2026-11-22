/**
 * /herald/fonts.css and /herald/theme.css -- the herald stylesheets at fixed URLs (Story 43.4 and its review;
 * spec-pyforge-herald CAP-61; AD-21, AD-23), for the pages Astro does not bundle a stylesheet into: `fonts.css` is the
 * faces alone (`styles/herald-fonts.css`), the one link each twin under /herald/twins/ is given (Story 31.3's
 * mechanism); `theme.css` is the site theme with the faces (`styles/theme.css`), linked by each reader page, followed by the site shell's rules (`styles/shell.css`, Story 53.1) for the header those
 * pages and the mounted pages carry. Both are
 * the files as Vite builds them, so every face is an @fontsource file Astro emits under the artifact's own `_astro/`,
 * the same files the herald layouts' bundle and the docs' `customCss` name. A dynamic route, `[sheet]`.
 */
import type { APIRoute, GetStaticPaths } from 'astro';

import { HERALD_FONTS, HERALD_THEME } from '../../lib/herald-pages';
import fontsCss from '../../styles/herald-fonts.css?inline';
import shellCss from '../../styles/shell.css?inline';
import themeCss from '../../styles/theme.css?inline';

const SHEETS: Record<string, string> = { [HERALD_FONTS]: fontsCss, [HERALD_THEME]: `${themeCss}\n${shellCss}` };

export const getStaticPaths: GetStaticPaths = () =>
  Object.keys(SHEETS).map((name) => ({ params: { sheet: name.slice(0, -'.css'.length) } }));

export const GET: APIRoute = ({ params }) =>
  new Response(SHEETS[`${params.sheet}.css`], { headers: { 'Content-Type': 'text/css; charset=utf-8' } });
