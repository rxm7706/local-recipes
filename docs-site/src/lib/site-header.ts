/**
 * The one header of the Pages site (Story 53.1, spec-pyforge-herald CAP-63; pyforge-herald:AD-23, amended 2026-11-22):
 * the site title, the registry's menu grouped by section, search and the theme toggle, as one HTML string. The docs
 * shell (`components/Header.astro`), both herald layouts and the reader pages render it through
 * `components/SiteHeader.astro` or directly, and the build's assembly step writes the same string into each page another
 * station mounts (`src/lib/artifact.ts` `addShell`). Nothing else lists the menu.
 *
 * Behind `pyforge.herald.site_shell` (`flags.ts` `siteShell()`): off, each shell keeps the header it had.
 *
 * Node builtins only and no `astro:*` import, so the herald tests import this module with node's type stripping.
 */

import type { MapSection } from './nav.ts';
import { DOCS_ENTRY } from './nav.ts';

/** The header's script, served at the site root (`src/pages/[shell].js.ts`). */
export const SHELL_SCRIPT = 'pf-shell.js';
/** The id the skip link targets. */
export const MAIN_ID = 'pf-main';
/** Where the theme a reader chose is stored: Starlight's own key, so the docs and every other page agree. */
export const THEME_KEY = 'starlight-theme';

/** One slot of the menu: a single link, or a section's label over its entries. */
export interface HeaderGroup {
  label: string;
  /** Site-root paths, in the registry's order; one entry is a plain link. */
  links: Array<{ label: string; path: string }>;
  grouped: boolean;
}

/** The menu's slots: the docs root, then one per section, a section with entries as a group. */
export function headerGroups(sections: MapSection[]): HeaderGroup[] {
  return [
    { label: DOCS_ENTRY.label, links: [{ label: DOCS_ENTRY.label, path: DOCS_ENTRY.href }], grouped: false },
    ...sections.map((section) =>
      section.entries?.length
        ? {
            label: section.label,
            links: section.entries.map((entry) => ({ label: entry.label, path: entry.href })),
            grouped: true,
          }
        : { label: section.label, links: [{ label: section.label, path: section.href }], grouped: false },
    ),
  ];
}

/** The menu path a page sits under: the longest one that prefixes `pagePath` (site-root relative), else the docs root. */
export function currentMenuPath(groups: HeaderGroup[], pagePath: string): string {
  const paths = groups.flatMap((group) => group.links.map((link) => link.path)).filter((p) => p !== '');
  const hits = paths.filter((p) => pagePath === p || pagePath.startsWith(p));
  return hits.sort((a, b) => b.length - a.length)[0] ?? '';
}

function esc(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export interface HeaderOptions {
  /** From the page to the site root: `''`, `'../'`, or the host's base path. */
  toRoot: string;
  /** The page's own path, site-root relative (`'herald/decks/'`), for `aria-current`. */
  pagePath: string;
  /** A page under no path of the menu (a board mounted beside the sections): no link is marked current. */
  unlisted?: boolean;
  /** The docs shell: Starlight supplies the skip link, the `<header>` landmark and the phone menu. */
  docs?: boolean;
  /** The search control's HTML; the default is the header's own Pagefind dialog. */
  searchHtml?: string;
}

const DEFAULT_SEARCH =
  '<button type="button" class="pf-search" data-pf-search>Search</button>' +
  '<dialog class="pf-search-dialog" data-pf-search-dialog aria-label="Search the docs">' +
  '<div class="pf-search-row"><input type="search" name="q" placeholder="Search the docs" aria-label="Search the docs" autocomplete="off">' +
  '<form method="dialog"><button type="submit">Close</button></form></div>' +
  '<ol data-pf-search-results aria-live="polite"></ol></dialog>';

/** The header, with its skip link ahead of it on every page but the docs (Starlight's own skip link is there). */
export function siteHeaderHtml(sections: MapSection[], options: HeaderOptions): string {
  const { toRoot, pagePath, docs = false, searchHtml, unlisted = false } = options;
  const groups = headerGroups(sections);
  const current = currentMenuPath(groups, pagePath);
  // `page` on the link to this very page, `true` on the link to the section a deeper page sits under.
  const mark = (path: string): string =>
    unlisted || path !== current ? '' : path === pagePath ? ' aria-current="page"' : ' aria-current="true"';
  const link = (item: { label: string; path: string }): string =>
    `<a data-pf-menu-link href="${esc(`${toRoot}${item.path}`)}"${mark(item.path)}>${esc(item.label)}</a>`;
  const items = groups
    .map((group) => {
      if (!group.grouped) {
        return `<li>${link(group.links[0])}</li>`;
      }
      const open = !unlisted && group.links.some((item) => item.path === current) ? ' data-pf-current' : '';
      return (
        `<li class="pf-group"><details${open}><summary>${esc(group.label)}</summary>` +
        `<ul>${group.links.map((item) => `<li>${link(item)}</li>`).join('')}</ul></details></li>`
      );
    })
    .join('');
  const tag = docs ? 'div' : 'header';
  const skip = docs ? '' : `<a class="pf-skip" href="#${MAIN_ID}">Skip to content</a>`;
  return (
    `${skip}<${tag} class="pf-header${docs ? ' pf-header--docs' : ''}" data-pf-header>` +
    `<div class="pf-header-inner">` +
    `<a class="pf-brand" href="${esc(toRoot)}"><span class="pf-spark" aria-hidden="true"></span>PyForge</a>` +
    `<button type="button" class="pf-menu-btn" data-pf-menu-toggle aria-expanded="false" aria-controls="pf-nav">Menu</button>` +
    `<nav id="pf-nav" class="pf-nav" aria-label="Site"><ul>${items}</ul></nav>` +
    `<div class="pf-tools">${searchHtml ?? DEFAULT_SEARCH}` +
    `<button type="button" class="pf-theme" data-pf-theme aria-label="Switch between dark and light theme">` +
    `<span aria-hidden="true">Theme</span></button></div>` +
    `</div></${tag}>`
  );
}

/**
 * The theme a page starts in, as an inline script (the herald pages' and the mounted pages'; the docs take the same
 * rule through `components/ThemeProvider.astro`). With the shell, a reader who stored no theme gets dark (operator
 * ruling 2026-11-22); without it, the system scheme decides, as before Story 53.1.
 */
export function themeScript(shell: boolean): string {
  const fallback = shell ? "'dark'" : "(m.matches?'light':'dark')";
  return (
    "(()=>{const r=document.documentElement,m=matchMedia('(prefers-color-scheme: light)');" +
    `const s=()=>{try{return localStorage.getItem('${THEME_KEY}')}catch(e){return null}};` +
    `const a=()=>{r.dataset.theme=(s()||${fallback})==='light'?'light':'dark'};` +
    "a();m.addEventListener('change',a);addEventListener('pageshow',a)})()"
  );
}

/**
 * The header's behaviour, one external script every page loads from the site root (so no page's CSP needs a hash for
 * it): the theme toggle, the phone menu, closing an open group on a click elsewhere, and, where the page has no
 * search of its own, a dialog over the docs' Pagefind index (a result's excerpt is rebuilt as text and `<mark>`
 * nodes, never set as HTML).
 */
export const SHELL_SCRIPT_SOURCE = `(()=>{
const d=document,r=d.documentElement,K='${THEME_KEY}';
const root=new URL('.',d.currentScript.src).href;
r.classList.add('pf-js');
const groups=()=>d.querySelectorAll('[data-pf-header] details');
let pf=null;
async function search(input,list){
  const q=input.value.trim();
  if(!q){list.replaceChildren();return}
  try{pf=pf||await import(root+'pagefind/pagefind.js')}catch(e){list.innerHTML='<li>Search is not available on this build.</li>';return}
  const found=await pf.search(q);
  const top=await Promise.all(found.results.slice(0,8).map((x)=>x.data()));
  if(input.value.trim()!==q)return;
  if(!top.length){list.innerHTML='<li>No results.</li>';return}
  list.replaceChildren(...top.map((x)=>{
    const li=d.createElement('li'),a=d.createElement('a'),p=d.createElement('p'),t=d.createElement('template');
    a.href=x.url;a.textContent=x.meta&&x.meta.title||x.url;
    t.innerHTML=x.excerpt;
    t.content.childNodes.forEach((n)=>{
      if(n.nodeName==='MARK'){const k=d.createElement('mark');k.textContent=n.textContent;p.append(k)}else{p.append(n.textContent)}
    });
    li.append(a,p);return li;
  }));
}
d.addEventListener('click',(e)=>{
  const t=e.target instanceof Element?e.target:null;
  groups().forEach((g)=>{if(!t||!g.contains(t))g.open=false});
  if(!t)return;
  const theme=t.closest('[data-pf-theme]');
  if(theme){const n=r.dataset.theme==='light'?'dark':'light';r.dataset.theme=n;try{localStorage.setItem(K,n)}catch(x){}return}
  const menu=t.closest('[data-pf-menu-toggle]');
  if(menu){const h=menu.closest('[data-pf-header]');const on=h.classList.toggle('pf-open');menu.setAttribute('aria-expanded',String(on));return}
  const s=t.closest('[data-pf-search]');
  if(s){const dlg=s.parentElement.querySelector('[data-pf-search-dialog]');if(dlg&&dlg.showModal){dlg.showModal();dlg.querySelector('input').focus()}}
});
d.addEventListener('input',(e)=>{
  const t=e.target;
  if(t instanceof HTMLInputElement&&t.closest('[data-pf-search-dialog]')){search(t,t.closest('[data-pf-search-dialog]').querySelector('[data-pf-search-results]'))}
});
d.addEventListener('keydown',(e)=>{if(e.key==='Escape')groups().forEach((g)=>{if(g.open){g.open=false;g.querySelector('summary').focus()}})});
})();
`;
