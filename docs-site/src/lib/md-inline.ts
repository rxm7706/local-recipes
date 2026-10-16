/** Inline markdown subset — the retired Jinja build's ``md_inline`` (Stories 41.1, 43.1; the only one since 43.7). */

const ESCAPED = /\\(.)/gs;
const ARROW = /<<(.+?)>>/gs;
const CODE = /`([^`]+)`/g;
const BOLD = /\*\*(.+?)\*\*/gs;
const EM = /(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/gs;
const LINK = /\[([^\]]+)\]\(([^)]+)\)/g;
const SLOT = /\x00(\d+)\x00/g;

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function mdInline(text: string | null | undefined): string {
  if (text == null) {
    return '';
  }
  let raw = String(text);
  const slots: string[] = [];

  const put = (fragment: string): string => {
    slots.push(fragment);
    return `\x00${slots.length - 1}\x00`;
  };

  raw = raw.replace(ESCAPED, (_, ch: string) => put(escapeHtml(ch)));
  raw = raw.replace(ARROW, (_, inner: string) =>
    put(`<span class="rel-arrow">${escapeHtml(inner)}</span>`),
  );
  raw = raw.replace(CODE, (_, inner: string) => put(`<code>${escapeHtml(inner)}</code>`));

  raw = escapeHtml(raw);
  raw = raw.replace(LINK, (_, label: string, href: string) => {
    const safeHref = href.replace(/"/g, '&quot;');
    return `<a href="${safeHref}">${label}</a>`;
  });
  raw = raw.replace(BOLD, '<b>$1</b>');
  raw = raw.replace(EM, '<em>$1</em>');

  while (SLOT.test(raw)) {
    raw = raw.replace(SLOT, (_, index: string) => slots[Number(index)] ?? '');
  }
  return raw;
}

const TOKEN = /^--[\w-]+$/;

/**
 * A theme token from dossier.yml / site.yml (``accent``, ``tone``, ``exit_tone``) as ``var(<token>)``. Only a custom
 * property name is accepted -- a literal colour there would reach an inline ``style=`` past the one theme contract
 * (Story 43.4's re-review) -- so anything else fails the build naming the value; an absent value is ''.
 */
export function cssVar(token: string | undefined): string {
  if (token == null || token === '') {
    return '';
  }
  if (!TOKEN.test(token)) {
    throw new Error(`cssVar: ${JSON.stringify(token)} is not a theme token (a --custom-property name)`);
  }
  return `var(${token})`;
}

/**
 * A station or tone token used as small text (a station pill, a finding label): the hue mixed 75% toward the ink, so
 * it reads AA on the paper in both themes (Story 43.4's re-review) and still names no colour of its own. The same 75%
 * mixes the red and green callout labels in `styles/herald.css` (`.callout.red .label`); change the three together.
 */
export function cssTextTone(token: string | undefined): string {
  const value = cssVar(token);
  return value ? `color-mix(in srgb, ${value} 75%, var(--ink))` : '';
}
