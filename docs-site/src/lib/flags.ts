/**
 * The docs-site's one reader of the flags the Guild step exports into the build environment (the lane merge of
 * Stories 43.1-43.6, the 43.6 review's M5 and N8): `pyforge.herald.pages_one_generator` as
 * `PYFORGE_PAGES_ONE_GENERATOR` and `pyforge.herald.status_pages` as `PYFORGE_STATUS_PAGES`.
 *
 * A flag reads on for `1`, `true` or `yes` (trimmed, any case), the rule `docsite/tools/pages_one_generator.py` and
 * `docsite/tools/status_pages.py` apply on the Python side; anything else is off. The assembler keeps a value the
 * environment already holds (`setdefault`), so a `true` reaching the build means on here too. Node builtins only:
 * `astro.config.mjs`, `scripts/populate-public.ts` and the herald tests import it with node's type stripping.
 */

/** The values that read a flag on. */
export const FLAG_ON_VALUES: readonly string[] = ['1', 'true', 'yes'];

/** `name` in `env` reads on. */
export function envFlagOn(name: string, env: Record<string, string | undefined> = process.env): boolean {
  return FLAG_ON_VALUES.includes((env[name] ?? '').trim().toLowerCase());
}

/** `pyforge.herald.pages_one_generator` (Story 43.1). */
export function pagesOneGenerator(): boolean {
  return envFlagOn('PYFORGE_PAGES_ONE_GENERATOR');
}

/** `pyforge.herald.status_pages` (Story 42.1). */
export function statusPages(): boolean {
  return envFlagOn('PYFORGE_STATUS_PAGES');
}
