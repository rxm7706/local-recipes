/**
 * Text as a reader outside the fleet meets it (Story 53.2, spec-pyforge-herald CAP-63): a time printed as a date a
 * person reads, a page title without the story id it was filed under, and a description for a page that states none.
 * Pure functions, node builtins only: the herald tests import this module with node's type stripping.
 */

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?\s*(Z|[+-]\d{2}:?\d{2})?)?$/;

/**
 * `2026-11-21T10:35:33-06:00` as `21 Nov 2026, 10:35 UTC-06:00`; `2026-11-21` as `21 Nov 2026`. Read from the string
 * itself -- its own day, clock and offset -- never converted through the build host's time zone. A string that is no
 * ISO date is returned as given.
 */
export function readableDate(iso: string): string {
  const m = ISO.exec(iso.trim());
  if (!m) {
    return iso;
  }
  const [, year, month, day, hour, minute, offset] = m;
  const name = MONTHS[Number(month) - 1];
  if (!name) {
    return iso;
  }
  const date = `${Number(day)} ${name} ${year}`;
  if (hour === undefined) {
    return date;
  }
  const zone = offset === undefined ? '' : offset === 'Z' || /^[+-]00:?00$/.test(offset) ? ' UTC' : ` UTC${offset}`;
  return `${date}, ${hour}:${minute}${zone}`;
}

/** A trailing parenthesis that only names the story or capability a page was filed under. */
const FILED_UNDER = /\s*\((?:[a-z]+ )?(?:Story|Epic|CAP)[- ]?[\d.]+(?:\s*\/\s*(?:Story|Epic|CAP)[- ]?[\d.]+)*\)\s*$/i;

/** `PostgreSQL restore runbook (steward Story 41.1)` as `PostgreSQL restore runbook`: the label a reader navigates by. */
export function readerTitle(title: string): string {
  const short = title.replace(FILED_UNDER, '').trim();
  return short || title;
}

/**
 * The first paragraph of a markdown body as one plain line of at most `max` characters, cut at a word; `''` when the
 * body opens with none (a table, a list, a code block).
 */
export function firstParagraph(body: string, max = 160): string {
  const blocks = body.replace(/\r\n/g, '\n').split(/\n\s*\n/);
  for (const raw of blocks) {
    const block = raw.trim();
    if (!block || /^(#|```|~~~|\||[-*+] |\d+\. |>|<|:::|---|import )/.test(block)) {
      continue;
    }
    const text = block
      .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[`*_]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    if (!text) {
      continue;
    }
    if (text.length <= max) {
      return text;
    }
    const cut = text.slice(0, max - 1);
    return `${cut.slice(0, Math.max(cut.lastIndexOf(' '), 40)).replace(/[\s,;:.]+$/, '')}…`;
  }
  return '';
}
