/**
 * Story 43.5 (CAP-61): every page says what built it -- the first seven characters of `GITHUB_SHA`, the build time
 * and `GITHUB_RUN_ID`, read from the environment the workflow already provides (no `gh` call, no token); with no
 * `GITHUB_SHA` it says `local build`. The time is `PAGES_BUILT_AT` (ISO 8601, which the Pages assembler sets once per
 * build so every page and generator agrees), else this module's load time.
 *
 * The line is build provenance, not content: it is one `data-pages-built-from` element of plain text, which steward's
 * `tree_hash` (`pyforge.steward.pages`) reads without its text, so a rebuild of an unmoved tree hashes the same and
 * deploys nothing (the 24-hour liveness rule keeps the live build honest), and `data-pagefind-ignore` keeps it out of
 * the search index. `docsite/tools/status_pages.py` renders the same element for the Jinja status pages until Story
 * 43.7; a test holds the two equal. Node builtins only: the reader pages and the tests import it with type stripping.
 */

const LOADED_AT = new Date();

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
  const raw = (env.PAGES_BUILT_AT ?? '').trim();
  const at = raw ? new Date(raw) : LOADED_AT;
  if (Number.isNaN(at.getTime())) {
    throw new Error(`PAGES_BUILT_AT is not an ISO 8601 time: ${JSON.stringify(raw)}`);
  }
  const run = (env.GITHUB_RUN_ID ?? '').trim();
  return [`Built from ${sha.slice(0, 7)}`, utcMinute(at), ...(run ? [`run ${run}`] : [])].join(' · ');
}

/** The footer element every page carries (text only: the text holds no markup to escape). */
export function builtFromHtml(env: Record<string, string | undefined> = process.env): string {
  const text = builtFromText(env).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return `<p class="built-from" data-pages-built-from data-pagefind-ignore>${text}</p>`;
}
