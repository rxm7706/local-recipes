/**
 * Dossier block HTML — one implementation shared by Astro components and the golden-test renderer.
 * The fifteen block types (Epic 43's fourteen + ci_surfaces), the shapes the retired Jinja macros had (Story 43.7).
 */

import { cssTextTone, cssVar, mdInline } from './md-inline.ts';

export type DossierBlock = Record<string, unknown> & { type: string };

export function renderBlock(block: DossierBlock): string {
  switch (block.type) {
    case 'lede':
      return `<p class="lede">${mdInline(block.md as string)}</p>`;
    case 'quote':
      return `<blockquote class="station-quote">${mdInline(block.md as string)}</blockquote>`;
    case 'stats': {
      const stats = (block.stats as Array<{ value: string; label: string }>) ?? [];
      const inner = stats
        .map(
          (s) =>
            `<div class="s"><b>${mdInline(s.value)}</b><span>${mdInline(s.label)}</span></div>`,
        )
        .join('');
      return `<div class="stat-row">${inner}</div>`;
    }
    case 'h3': {
      const num = block.num ? `<span class="h3-num">${mdInline(String(block.num))}</span>` : '';
      return `<h3>${num}${mdInline(block.text as string)}</h3>`;
    }
    case 'prose': {
      const body = (block.body as string[]) ?? [];
      const paras = body.map((p) => `<p>${mdInline(p)}</p>`).join('');
      return `<div class="prose">${paras}</div>`;
    }
    case 'note':
      return `<p class="soft-note">${mdInline(block.md as string)}</p>`;
    case 'verify':
      return `<p class="verify-note">${mdInline(block.md as string)}</p>`;
    case 'table': {
      const headers = (block.headers as string[]) ?? [];
      const rows = (block.rows as Array<{ cells: string[]; mono?: boolean[] }>) ?? [];
      const th = headers.map((h) => `<th>${mdInline(h)}</th>`).join('');
      const tbody = rows
        .map((row) => {
          const cells = row.cells.map((cell, i) => {
            const mono = row.mono?.[i] ? ' class="mono"' : '';
            return `<td${mono}>${mdInline(cell)}</td>`;
          });
          return `<tr>${cells.join('')}</tr>`;
        })
        .join('');
      return `<div class="table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${tbody}</tbody></table></div>`;
    }
    case 'callout': {
      const tone = block.tone === 'red' || block.tone === 'green' ? ` ${block.tone}` : '';
      const label = block.label
        ? `<span class="label">${mdInline(block.label as string)}</span>`
        : '';
      const body = ((block.body as string[]) ?? []).map((p) => `<p>${mdInline(p)}</p>`).join('');
      return `<div class="callout${tone}">${label}${body}</div>`;
    }
    case 'finding': {
      const alarm = block.alarm ? ' red' : '';
      const accent = block.accent ? String(block.accent) : '';
      const border = accent ? ` style="border-left-color:${cssVar(accent)}"` : '';
      const flabel = block.label
        ? `<span class="flabel"${accent ? ` style="color:${cssTextTone(accent)}"` : ''}>${mdInline(block.label as string)}</span>`
        : '';
      const body = ((block.body as string[]) ?? []).map((p) => `<p>${mdInline(p)}</p>`).join('');
      return `<div class="find-box${alarm}"${border}>${flabel}${body}</div>`;
    }
    case 'chips': {
      const chips = ((block.chips as string[]) ?? [])
        .map((c) => `<span class="chip">${mdInline(c)}</span>`)
        .join('');
      return `<div class="chips">${chips}</div>`;
    }
    case 'relations': {
      const items = (block.items as Array<{ glyph: string; md: string }>) ?? [];
      const lis = items
        .map(
          (item) =>
            `<li><span class="rel-arrow">${mdInline(item.glyph)}</span> ${mdInline(item.md)}</li>`,
        )
        .join('');
      return `<ul class="rel-list">${lis}</ul>`;
    }
    case 'lattice': {
      const rungs = (block.rungs as Array<Record<string, string>>) ?? [];
      const rungHtml = rungs
        .map((r) => {
          const tone = r.tone ? ` style="background:${cssVar(r.tone)}"` : '';
          const exitTone = r.exit_tone ? ` style="background:${cssVar(r.exit_tone)}"` : '';
          return `<div class="rung"${tone}><span class="exit"${exitTone}>${mdInline(r.exit)}</span><span class="name">${mdInline(r.name)}</span><span class="desc">${mdInline(r.desc)}</span></div>`;
        })
        .join('');
      const note = block.note
        ? `<p class="lattice-note">${mdInline(block.note as string)}</p>`
        : '';
      return `<div class="lattice-wrap"><div class="lattice">${rungHtml}</div>${note}</div>`;
    }
    case 'engines': {
      const engines = (block.engines as Array<Record<string, unknown>>) ?? [];
      const inner = engines
        .map((e) => {
          const body = ((e.body as string[]) ?? []).map((p) => `<p>${mdInline(p)}</p>`).join('');
          return `<div class="engine"><h4>${mdInline(e.name as string)}</h4><span class="verb">${mdInline(e.verb as string)}</span>${body}</div>`;
        })
        .join('');
      return `<div class="engines">${inner}</div>`;
    }
    case 'ci_surfaces': {
      const lines = ((block.lines as string[]) ?? []).map((line) => `<p>${mdInline(line)}</p>`).join('');
      return `<h3><span class="h3-num">A→B.5</span>CI surfaces</h3><p class="soft-note">Snapshot captured at ${mdInline(block.fetched_at as string)}</p><div class="ci-surfaces-tile prose">${lines}</div>`;
    }
    default:
      throw new Error(`unknown dossier block type: ${block.type}`);
  }
}
