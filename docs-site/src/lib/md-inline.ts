/** Inline markdown subset — mirrors docsite/build.py ``md_inline`` (Story 41.1 / 43.1). */

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

export function cssVar(token: string | undefined): string {
  if (token && token.startsWith('--')) {
    return `var(${token})`;
  }
  return token ?? '';
}
