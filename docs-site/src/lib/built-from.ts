/**
 * Story 43.5 (CAP-61): every page says what built it -- the first seven characters of `GITHUB_SHA`, the build time
 * and `GITHUB_RUN_ID`, read from the environment the workflow already provides (no `gh` call, no token); with no
 * `GITHUB_SHA` it says `local build`. The time is `PAGES_BUILT_AT` (ISO 8601, which `pages-build` --
 * `scripts/pages.mts build` -- sets once per build in the build's environment, so every page agrees), else this
 * module's load time.
 *
 * The line is build provenance, not content: it is one element of plain text, exactly `BUILT_FROM_OPEN` + text +
 * `</p>`, which steward's `tree_hash` (`pyforge.steward.pages.BUILT_FROM_TEXT`) reads without its text, so a rebuild
 * of an unmoved tree hashes the same and deploys nothing (the 24-hour liveness rule keeps the live build honest), and
 * `data-pagefind-ignore` keeps it out of the search index. **Three things change together** (Story 43.7): this markup,
 * steward's `BUILT_FROM_TEXT` regex, which matches it byte for byte, and `pages-check`'s built-from check
 * (`scripts/pages.mts`, which reads `BUILT_FROM_OPEN` from here). A markup change without steward's regex keeps the
 * text in the hash and redeploys every build, silently; a herald test pins the two equal. Node builtins only: the
 * reader pages and the tests import it with type stripping.
 */

const LOADED_AT = new Date();
/**
 * The one `PAGES_BUILT_AT` form: an ISO 8601 date-time with seconds and an explicit offset, on a real calendar date
 * from year 0001 -- what the retired Python twin (`datetime.fromisoformat`, Story 43.5) accepted. `Date` alone would
 * roll `2026-02-30` to March, read year `0000` and drop a leading byte-order mark with the whitespace.
 */
const ISO_INSTANT = /^(\d{4})-(\d{2})-(\d{2})T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

/** `raw` names a day the calendar has: year 1 to 9999, month 1 to 12, a day the month holds. */
function realDate(raw: string): boolean {
  const [, y, m, d] = (ISO_INSTANT.exec(raw) ?? []).map(Number);
  const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
  return y >= 1 && days !== undefined && d >= 1 && d <= days;
}

/** `YYYY-MM-DD HH:MM UTC`. */
function utcMinute(value: Date): string {
  return `${value.toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

/** The footer's text for `env`. */
export function builtFromText(env: Record<string, string | undefined> = process.env): string {
  const sha = (env.GITHUB_SHA ?? '').trim();
  if (!sha) {
    return 'local build';
  }
  const given = env.PAGES_BUILT_AT ?? '';
  const raw = given.trim();
  const at = raw ? new Date(raw) : LOADED_AT;
  if (raw && (given.includes('\ufeff') || !ISO_INSTANT.test(raw) || !realDate(raw) || Number.isNaN(at.getTime()))) {
    throw new Error(`PAGES_BUILT_AT is not an ISO 8601 time with an offset: ${JSON.stringify(given)}`);
  }
  const run = (env.GITHUB_RUN_ID ?? '').trim();
  return [`Built from ${sha.slice(0, 7)}`, utcMinute(at), ...(run ? [`run ${run}`] : [])].join(' · ');
}

/** The element's opening tag, byte for byte: steward's `BUILT_FROM_TEXT` and `pages-check` match exactly this. */
export const BUILT_FROM_OPEN = '<p class="built-from" data-pages-built-from data-pagefind-ignore>';

/** The footer element every page carries (text only: the text holds no markup to escape). */
export function builtFromHtml(env: Record<string, string | undefined> = process.env): string {
  const text = builtFromText(env).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return `${BUILT_FROM_OPEN}${text}</p>`;
}
