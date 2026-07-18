// One-time restructure of the prototype (2026-07 antigravity review):
//  - inserts clean dark dividers for Acts I–III (Acts IV–VI already have covers)
//  - merges the redundant "Cover · Framework" + "Meet BMAD" pair into a single
//    Act IV banner divider carrying the stats row
//  - moves the Act V cover + Phase map out of the agent-team act so the deck
//    matches its own Contents slide (agent team p.15–22, phases from p.23)
//  - moves Governance + Build for agents behind the Act VI cover
//  - renumbers all slide footers to the new NN / 45
// Idempotence is not a goal — run once; extract-slides.mjs consumes the result.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = join(__dirname, '..', 'project', 'Agentic SDLC.dc.html');

const raw = readFileSync(SRC, 'utf8');

// --- parse: header, [comment+section] blocks, tail -------------------------
const blockRe = /<!-- =+ [^\n]*? =+ -->\s*\n<section\b[\s\S]*?<\/section>/g;
const blocks = [];
let m;
let firstStart = -1;
let lastEnd = -1;
while ((m = blockRe.exec(raw)) !== null) {
  if (firstStart < 0) firstStart = m.index;
  lastEnd = m.index + m[0].length;
  const label = m[0].match(/data-label="([^"]*)"/)[1];
  blocks.push({ label, html: m[0] });
}
const header = raw.slice(0, firstStart);
const tail = raw.slice(lastEnd);
console.log(`parsed ${blocks.length} sections`);

const byLabel = Object.fromEntries(blocks.map((b) => [b.label, b.html]));

// --- new divider slides -----------------------------------------------------
const divider = (numeral, act, title, sub, notes, label) => `<!-- ============ ${act} · DIVIDER ============ -->
<section data-label="${label}" data-speaker-notes="${notes}" style="background:#0B1626">
  <div style="position:relative;width:100%;height:100%;overflow:hidden;font-family:'IBM Plex Sans',sans-serif;color:#F6F4EE">
    <div style="position:absolute;inset:0;background:radial-gradient(1100px 560px at 80% 12%, rgba(46,155,238,.14), transparent 60%);"></div>
    <div style="position:absolute;right:96px;top:8px;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:430px;line-height:1;color:rgba(91,179,245,.08)">${numeral}</div>
    <div style="position:absolute;left:120px;right:120px;bottom:132px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:16px;letter-spacing:.26em;text-transform:uppercase;color:#F4C233;font-weight:500;display:flex;align-items:center;gap:14px"><span style="width:10px;height:10px;background:#F4C233;display:inline-block"></span>${act}</div>
      <h2 style="font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:82px;line-height:1.02;letter-spacing:-.025em;margin:18px 0 0;max-width:1400px">${title}</h2>
      <p style="font-size:27px;line-height:1.45;color:rgba(246,244,238,.75);margin:18px 0 0;max-width:1120px">${sub}</p>
    </div>
    <div style="position:absolute;left:120px;bottom:56px;font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.16em;color:rgba(246,244,238,.4)">BMAD METHOD · AGENTIC SDLC</div>
    <div style="position:absolute;right:120px;bottom:56px;font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.14em;color:rgba(246,244,238,.4)">00 / 00</div>
  </div>
</section>`;

const actI = divider(
  'I',
  'ACT I',
  'The case for change',
  'Why AI-augmented isn&rsquo;t enough &mdash; and what changes when agents run the phases.',
  "Act one. Why the AI-augmented status quo isn't enough: the shift, what agentic AI-SDLC means, the maturity spectrum, and the core idea.",
  'Act I · The case for change'
);
const actII = divider(
  'II',
  'ACT II',
  'Spec-driven development',
  'The operating model: documentation as the brain, agents as transient workers.',
  'Act two. The operating model everything else builds on — spec-driven development, specs as code, and the docs-are-the-brain mental model.',
  'Act II · Spec-driven development'
);
const actIII = divider(
  'III',
  'ACT III',
  'Choosing your framework',
  'The SDD tool landscape &mdash; and why this deck lands on BMAD.',
  'Act three. SDD is a category now: the three tool families, method versus machinery, and why BMAD earns the choice.',
  'Act III · Choosing your framework'
);

// Merged Act IV divider — banner art from "Cover · Framework" + the stats row
// and framing from "Meet BMAD" (both replaced by this slide).
const actIV = `<!-- ============ ACT IV · THE BMAD METHOD ============ -->
<section data-label="Act IV · The BMAD Method" data-speaker-notes="Act four — the bridge into the concrete half of the deck. Of that landscape, we use BMAD-METHOD as the working example: the archetype of the agent-team family, and the most complete open implementation of everything covered so far — spec-driven, doc-anchored, phase-gated. Free and MIT-licensed, 12+ named agents, 34+ workflows, and it runs inside the coding agent you already use. Up next: the agent team, then the four phases end to end." style="background:#0B1626">
  <div style="position:relative;width:100%;height:100%;overflow:hidden;font-family:'IBM Plex Sans',sans-serif;color:#F6F4EE">
    <img src="https://dev-to-uploads.s3.amazonaws.com/uploads/articles/u0pbo16u36ywgrbym3eb.jpeg" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover">
    <div style="position:absolute;inset:0;background:linear-gradient(180deg, rgba(11,22,38,.55) 0%, rgba(11,22,38,.28) 28%, rgba(11,22,38,.66) 56%, rgba(11,22,38,.96) 100%)"></div>
    <div style="position:absolute;left:120px;right:120px;bottom:236px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:16px;letter-spacing:.26em;text-transform:uppercase;color:#F4C233;font-weight:500;display:flex;align-items:center;gap:14px"><span style="width:10px;height:10px;background:#F4C233;display:inline-block"></span>ACT IV · THE BMAD AGENT TEAM</div>
      <h2 style="font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:82px;line-height:1.02;letter-spacing:-.025em;margin:18px 0 0;max-width:1400px;text-shadow:0 2px 34px rgba(0,0,0,.6)">The BMAD Method</h2>
      <p style="font-size:26px;line-height:1.45;color:rgba(246,244,238,.9);margin:16px 0 0;max-width:1220px;text-shadow:0 2px 22px rgba(0,0,0,.7)">The archetype of the agent-team family &mdash; everything the deck has argued for, implemented: spec-driven, document-anchored, phase-gated.</p>
    </div>
    <div style="position:absolute;left:120px;right:120px;bottom:104px;display:flex;gap:72px;border-top:1px solid rgba(246,244,238,.28);padding-top:24px">
      <div><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:36px;color:#F4C233">MIT</div><div style="font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.14em;color:rgba(246,244,238,.65);margin-top:6px">FREE &amp; OPEN SOURCE</div></div>
      <div><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:36px;color:#F6F4EE">12+</div><div style="font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.14em;color:rgba(246,244,238,.65);margin-top:6px">NAMED AGENTS</div></div>
      <div><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:36px;color:#F6F4EE">34+</div><div style="font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.14em;color:rgba(246,244,238,.65);margin-top:6px">WORKFLOWS</div></div>
      <div><div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:36px;color:#F6F4EE">0</div><div style="font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.14em;color:rgba(246,244,238,.65);margin-top:6px">NEW TOOLS &mdash; RUNS IN YOUR CODING AGENT</div></div>
    </div>
    <div style="position:absolute;left:120px;bottom:52px;font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.16em;color:rgba(246,244,238,.6)">BMAD METHOD · AGENTIC SDLC</div>
    <div style="position:absolute;right:120px;bottom:52px;font-family:'IBM Plex Mono',monospace;font-size:14px;letter-spacing:.14em;color:rgba(246,244,238,.6)">00 / 00</div>
  </div>
</section>`;

// --- the new order -----------------------------------------------------------
const order = [
  'Title',
  'Contents',
  '@ACT1',
  'The shift',
  'What is AI-SDLC',
  'Maturity spectrum',
  'Core idea',
  '@ACT2',
  'What is SDD',
  'Spec-driven',
  'Mental model',
  '@ACT3',
  'SDD landscape',
  'Method vs machinery',
  '@ACT4',
  'Why BMAD',
  'The crew',
  'Why named agents',
  'Party mode',
  'Execution matrix',
  'Skill roster',
  'Repo artifacts',
  'Act V · The four phases',
  'Phase map',
  'Phase 1 · Analysis',
  'Choosing a tool',
  'Phase 2 · Planning',
  'Phase 3 · Solutioning',
  'Why solutioning',
  'Phase 4 · Implementation',
  'The dev loop',
  'Act V · Testing focus',
  'TEA testing',
  'Quick flow',
  'Scale-adaptive',
  'Act VI · Scale &amp; ecosystem',
  'Governance',
  'Build for agents',
  'Module ecosystem',
  'BMad Builder',
  'Plan anywhere',
  'In action',
  'Get started',
  'Principles',
  'Closing',
];

const inserts = { '@ACT1': actI, '@ACT2': actII, '@ACT3': actIII, '@ACT4': actIV };
const dropped = ['Cover · Framework', 'Meet BMAD']; // replaced by merged @ACT4

const used = new Set();
const out = order.map((key) => {
  if (inserts[key]) return inserts[key];
  const html = byLabel[key];
  if (!html) throw new Error(`No section with label "${key}"`);
  used.add(key);
  return html;
});

// Every original section must be either reused or intentionally dropped.
for (const b of blocks) {
  if (!used.has(b.label) && !dropped.includes(b.label)) {
    throw new Error(`Section "${b.label}" was silently lost`);
  }
}

const TOTAL = out.length;
console.log(`new slide count: ${TOTAL}`);

// Fix the &amp; in the ecosystem cover's label (breaks JSON/React text rendering).
let doc =
  header +
  out.join('\n\n') +
  tail;
doc = doc.replace('data-label="Act VI · Scale &amp; ecosystem"', 'data-label="Act VI · Scale, governance, ecosystem"');

// --- renumber footers ("NN / 43" or "00 / 00" placeholders) -------------------
let idx = 0;
doc = doc.replace(/<section\b[\s\S]*?<\/section>/g, (sec) => {
  idx += 1;
  const num = String(idx).padStart(2, '0');
  return sec.replace(/\d{2} \/ (?:43|00)/g, `${num} / ${String(TOTAL).padStart(2, '0')}`);
});
if (idx !== TOTAL) throw new Error(`renumbered ${idx} sections, expected ${TOTAL}`);

writeFileSync(SRC, doc);
console.log('restructure complete');
