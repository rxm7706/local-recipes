/**
 * The docs-site's one reader of the flags the Guild step exports into the build environment (the lane merge of
 * Stories 43.1-43.6, the 43.6 review's M5 and N8; Story 43.7 retired the one-generator flag and moved the dossier
 * tile's reader here): `pyforge.herald.status_pages` as `PYFORGE_STATUS_PAGES` and
 * `pyforge.herald.ci_surfaces_tile` as `PYFORGE_CI_SURFACES_TILE`, each exported by
 * `python -m pyforge.herald.pages_env` (run in the Guild env, which resolves the flags); and steward's
 * `pyforge.steward.marketplace_pages` as `PYFORGE_MARKETPLACE_PAGES`, exported beside them by
 * `python -m pyforge.steward.marketplace_pages --flag-env` (steward Story 109.3; the review of 2026-10-28 retired the
 * build's own TypeScript reader of the flag tree, which defaulted every deploy to `dev`).
 *
 * A flag reads on for `1`, `true` or `yes` (trimmed, any case); anything else is off. Node builtins only:
 * `astro.config.mjs`, the loaders and the herald tests import it with node's type stripping.
 */

/** The values that read a flag on. */
export const FLAG_ON_VALUES: readonly string[] = ['1', 'true', 'yes'];

/** `name` in `env` reads on. */
export function envFlagOn(name: string, env: Record<string, string | undefined> = process.env): boolean {
  return FLAG_ON_VALUES.includes((env[name] ?? '').trim().toLowerCase());
}

/** `pyforge.herald.status_pages` (Story 42.1): the `/status/` prefix and its menu entry. */
export function statusPages(): boolean {
  return envFlagOn('PYFORGE_STATUS_PAGES');
}

/** `pyforge.herald.ci_surfaces_tile` (Story 39.1): the dossier's CI surfaces tile. */
export function ciSurfacesTile(): boolean {
  return envFlagOn('PYFORGE_CI_SURFACES_TILE');
}

/** `pyforge.steward.marketplace_pages` (steward Story 109.3): the `/marketplace/` mount and its menu entry. */
export function marketplacePages(): boolean {
  return envFlagOn('PYFORGE_MARKETPLACE_PAGES');
}
