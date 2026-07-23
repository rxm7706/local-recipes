// Extracts the 43 slides from the Claude Design handoff prototype into
// per-slide HTML fragments + a manifest the React deck consumes.
//
// Why a script: each slide is dense inline-styled HTML. Parsing it out
// mechanically guarantees pixel-fidelity with the source (no hand
// transcription of hundreds of style declarations), and re-running it keeps
// the React app in sync if the prototype is ever updated.
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
// The Claude Design handoff export for this deck — drop it in ./project/ and
// rename this to match (or rename the export to `PyForge Mason.dc.html`).
const SRC = join(root, 'project', 'PyForge Mason.dc.html');
const FRAG_DIR = join(root, 'src', 'slides', 'fragments');
const MANIFEST = join(root, 'src', 'slides', 'manifest.json');

// Map any remote images referenced by the prototype to locally-bundled copies
// under public/assets/banners/ (relative paths, no leading slash, so they
// resolve from a site root, a subpath, or a built file://). Empty for now —
// add one entry per remote image the PyForge-Mason prototype references, then
// download the image into public/assets/banners/.
const BANNER_MAP = {};

function attr(tag, name) {
  const m = tag.match(new RegExp(`${name}="([^"]*)"`));
  return m ? m[1] : '';
}

function slugify(label, i) {
  const base = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return `${String(i + 1).padStart(2, '0')}-${base || 'slide'}`;
}

// Turn the prototype's <image-slot> custom element into a self-contained
// dashed placeholder (the runtime that powered drag-to-drop is gone; the
// slot's job in the deck is to be a labelled drop target).
function replaceImageSlots(html) {
  return html.replace(
    /<image-slot\b([^>]*)>\s*<\/image-slot>/g,
    (_, a) => {
      const placeholder = attr(`<x ${a}>`, 'placeholder') || 'Drop image';
      return `<div class="image-slot" role="img" aria-label="${placeholder}"><span class="image-slot__plus">+</span><span class="image-slot__label">${placeholder}</span></div>`;
    }
  );
}

const raw = readFileSync(SRC, 'utf8');
const sectionRe = /<section\b([^>]*)>([\s\S]*?)<\/section>/g;

rmSync(FRAG_DIR, { recursive: true, force: true });
mkdirSync(FRAG_DIR, { recursive: true });

const manifest = [];
let m;
let i = 0;
while ((m = sectionRe.exec(raw)) !== null) {
  const openTag = `<section ${m[1]}>`;
  const label = attr(openTag, 'data-label');
  const notes = attr(openTag, 'data-speaker-notes');
  const styleBg = attr(openTag, 'style').match(/background:\s*(#[0-9A-Fa-f]{3,8})/);
  const bg = styleBg ? styleBg[1] : '#0B1626';

  let inner = m[2].trim();
  for (const [remote, local] of Object.entries(BANNER_MAP)) {
    inner = inner.split(remote).join(local);
  }
  inner = replaceImageSlots(inner);

  const slug = slugify(label, i);
  writeFileSync(join(FRAG_DIR, `${slug}.html`), inner + '\n');

  manifest.push({ id: slug, label, notes, bg });
  i += 1;
}

writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n');
console.log(`Extracted ${manifest.length} slides.`);
console.log(manifest.map((s, n) => `  ${String(n + 1).padStart(2, ' ')}. ${s.label} [${s.bg}]`).join('\n'));
