---
title: Marshal — autonomy a human can trust
type: dream
owner: marshal
status: realized
---

# Marshal — graduated autonomy on the factory floor

## The Dream

The Commander's dream: **unattended development loops a human can actually
trust.** Not autonomy as a leap of faith — autonomy as a *gradient*: attended
stories first, then unattended loops wrapped in verify gates and quality
gates, with a hard rule that anything the agent cannot safely decide
**escalates to a human** instead of being guessed. Spec in, validated code
out, every run visible. Anti-vibe, by construction.

Execution has one owner. Skills — existing, community, and forged — are the
unit of execution; the deterministic harness is the unit of governance;
station verdicts stay independent. The thing that governs the agent cannot be
a thing the agent authors.

## What is real

`marshal` (module `pyforge.marshal`) is 10/50 stories shipped — Epic 1
(provisioned, verified loop homes) complete; Epics 2-6 in progress. The
capability already exists as `bmad-loop` and has driven two sibling stations
to full completion unattended: `pyforge-atlas` (38/38) and `pyforge-warden`
(31/31). Ten real capabilities are contracted in `spec-pyforge-marshal`
(CAP-1 loop homes and isolation · CAP-2 supervised unattended runs · CAP-3
gates you can run · CAP-4 landing with a durable paper trail · CAP-5 fleet
visibility · CAP-6 portability proven, not claimed · CAP-7 policy composition
· CAP-8 one install yields the whole stack, plus CAP-9/CAP-10 from later
decomposition), decomposed into FR-1 through FR-65 across 6 epics / 50
stories.

The BMAD suite underneath: BMAD 6.10 (BMM 34+ workflows) + BMB/TEA/BMGD/CIS,
web bundles for flat-rate planning, community plugins (skill-forge), and the
multi-project machinery (`scripts/bmad-switch`, per-project config/artifact
isolation). Visibility runs through the GitHub Pages program console
(`docs/dashboard/`), regenerated from tracked ledgers, never hand-trusted.

## Six follow-on dreams, consolidated here (2026-08-02)

This Dream previously sat alongside six satellite dreams, each answering one
question the original scope raised. Five are now fully decomposed into
Marshal's real chain — their standalone dream files are archived, their
vision lives in the FRs named below, not as separate documents to track:

- **Durable runs** (bounded-loss durability) → **FR-61/62/63**. The measured
  cost of not having this: six station loop branches on no remote, ~5,150
  lines across rescue branches, one unpushed commit 40 minutes from a `git gc`.
  Stage-boundary push + fleet-launch wiring, branch retirement, durability as
  a reported fleet-status dimension.
- **Fidelity enforcement** (a gate that fires in both directions at every tier
  boundary) → **FR-64**, the Marshal-owned slice — a gate evaluation binds to
  the tracked spec's Success signal, so a spec that stops being tested does
  not silently keep passing. The Doctor- and Scribe-owned slices of the same
  Dream stay with their own stations, not folded in here.
- **One front door** (`marshal check` — the detector registry through a single
  command, context resolved once) → **FR-65**.
- **PR lifecycle** (open, label, wait for checks, merge, retire the branch,
  resync — done once by the harness instead of improvised each time) →
  **FR-59/60**, `marshal land`.
- **Agent portability** (the method outlives the tool — Devin, Copilot,
  Cursor, Gemini, not just Claude) → **CAP-6 / Epic 6** ("Portability proven,
  not claimed"): skill-tree projection, adapter probe, conformance matrix,
  entry-file drift detection. A standing practice, not a one-time build — its
  narrative now lives here rather than in a separate practice document.

## Eight more, consolidated here (2026-08-08)

The 2026-08-02 pass folded six. Eight more follow, on the same terms: the
standalone dream files are archived in place, the **Spec of each stays live and
remains the contract**, and the vision lives in the FRs named below rather than
in separate documents to track. What changed is that these eight finally have
FRs at all — until today Marshal's PRD decomposed only two of its twenty-four
Specs, because a rule scoped FRs to work touching `pyforge-marshal`'s own
package. Not one open Spec did, so the rule excluded all of them by
construction. It is now an **ownership** test: a capability decomposes into
Marshal's chain iff its Dream is `owner: marshal`.

- **The shared floor** ([[pyforge-core]], minted the same day) → **FR-157..163**.
  Five primitives written between three and twenty times across eight stations —
  atomic write ×20 (6/8 stations), verdict lattice ×5, report envelope ×3
  schemas, station roster ×3+1, no shared exception root. One leaf package, pure
  stdlib, importing no station. Sequenced **before Epic 7's stories 7.2/7.3**,
  which would otherwise have minted copy #21 and copy #6 inside the very rewrite
  meant to consolidate.
- **Loop-home fleet refresh** → **FR-133..135**. Nine worktrees found 227
  commits stale on 2026-08-08 and refreshed by hand, twice, in one session.
  Staleness detection, fast-forward with a clean-worktree refusal, and the
  policy re-render as a *checked step of the same command* rather than a
  separately remembered second one.
- **Landing-to-ledger promotion** → **FR-136..139**. Three live staleness
  incidents in one session. FR-139 also carries the fix for a defect found
  while writing it: a stale feed silently overwrote the tracked ledger and
  dropped six `done` keys while reporting success — terminal states are now
  monotonic, and a write that un-finishes a story is refused and named.
- **Dashboard path derivation** → **FR-140..143**. `generate.py` string-glued
  slugs onto project paths in several places, each with its own patch; a `TODO`
  in the code named the gap. One resolver, one override table, derived
  discovery, and an unresolvable slug fails loud instead of rendering a 404.
- **Detector self-verification** ([[dream-to-code-model-self-verification]]) →
  **FR-144..147**. Both detectors gate the tree; nothing gated the detectors.
  Three real incidents — and a fourth the same day this consolidated: a
  measurement taken with an ad-hoc regex instead of the real parser produced a
  false fleet-wide finding that had to be retracted within hours. The incident
  log is the capability.
- **Chain completeness** → **FR-148..152**. Regenerating Dream→Spec→…→Epics
  coherently, plus orphan detection. Now also carries the reconciliation
  measured on 2026-08-08: six of eight stations hold tracked story specs with
  no ledger key (herald 34, doctor 4, atlas 3, scribe 1, steward 1).
- **The governed tool surface** → **FR-153..156**. Shipped without one; the
  2026-07-28 audit found 2-of-6 station coverage with Marshal itself at zero,
  inside a Dream marked `realized`. Coverage is measured now, not asserted.
- **Retiring the installer's separate name** ([[genesis-installer-name-retirement]])
  → executed 2026-08-08, this session. One FR space (`FR-1..FR-163`, no gaps),
  one `epics.md` (Epics 1-12, 86 stories), one dashboard row, and the two
  contradictions the consolidation had preserved rather than resolved —
  argparse-versus-typer and the `init`/`check` verb collisions — actually
  decided (AD-51, AD-54, AD-70).

**Three Marshal-owned `type: practice` documents are deliberately NOT absorbed**
— [[agentic-sdlc-autonomy]], [[agent-tool-surface]] and [[regenerable-factory]].
A practice sits outside the lifecycle by the Dream tier's own contract
(`docs/dreams/README.md`): *tended, never finished*, excluded from Backlog and
from Realized. Archiving one would assert a completion that cannot exist. Their
*capabilities* decompose into the chain where they have any; the documents
stand.

## Kept separate on purpose

**Genesis installer** (`genesis init` / `genesis adopt` — standing up a repo
with the pixi environment, bmad-method, multi-project wiring, and the
BMM/BMB/TEA modules in one command) is real, substantial, Marshal-owned
buildable work — but it is not the `marshal` CLI itself. **Only its epics stay
kept separate now** (`epics-genesis-installer.md`, its own 6 epics / 36
stories, epics 7–12) — unchanged. *(Revised 2026-08-02, explicit user
override.)* Its brief, PRD, architecture, and Spec were **consolidated** into
this station's own single brief / PRD / architecture / Spec
(`product-brief-pyforge-marshal.md`, `prds/prd-pyforge-marshal-2026-07-25/prd.md`,
`architecture/architecture-pyforge-marshal-2026-07-25/architecture.md`,
`specs/spec-pyforge-marshal/SPEC.md`), each carrying a clearly labelled
"Satellite: Genesis Installer" section (brief/PRD) or continued `AD-`/`CAP-`
numbering (architecture: `AD-51..AD-65`; Spec: `CAP-10..CAP-18`) rather than
the previously-separate documents. This reverses the "not merged into
Marshal's own FR range" line that stood here before — the FR range is still
distinct (genesis-installer's own `FR1..FR62`, no dash, never renumbered into
Marshal's `FR-1..FR-65`), but the *documents* are no longer separate. The four
original standalone documents are preserved at
`archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/{research/product-brief-pyforge-genesis.md,
prds/prd-genesis-installer-2026-07-25/, architecture/architecture-genesis-installer-2026-07-25/,
specs/spec-genesis-installer/}`. Constitutive records (the Charter, the
Guild's membership) and the machine that installs them are still different
nouns; that boundary is unchanged by this consolidation.

**Factory console** (the GitHub Pages program console at
`docs/dashboard/`, published from `main`, two-source refresh, the Dreamscape
lifecycle board) is shipped and real — the "every run stays visible" doctrine
above, given a front door. Folded in here 2026-08-02 (dream-level only):
`spec-factory-console` (2 companions — `console-contract.md`,
`drill-evidence.md`) stays live and untouched, since real frontier work is
still named against it — per-Dream drill-through to deck/spec/BMAD-project
rows, a delivery/notables feed, and a fleet-health strip fed from
[[pyforge-doctor]]. No PRD exists for it yet; this Spec is the current,
binding reference for that unbuilt work, not this Dream's prose.

## The frontier — real, not yet built

**Fleet-chain completeness** — an orchestrated workflow that regenerates a
project's entire Dream→Spec→Research→Brief→PRD→Architecture→Epics chain from
a consolidated Dream, pausing for human review before committing. Moved here
2026-08-02 from Herald (it is infrastructure/machinery, not Herald's "voice
and visual surface" scope) and consolidated from its own former dream file.
Genuinely unbuilt — the eight-phase workflow it describes is exactly what this
session's own dream-consolidation pass did by hand, station by station. Real
enough to warrant its own Spec — authored 2026-08-02 (`spec-fleet-chain-completeness`,
5 capabilities: orchestrated regeneration, code-status preservation, an audit
mode, review-gated orphan cleanup, per-project configurability) — not yet
decomposed to PRD/Architecture/Epics.

**Fleet-wide test architecture** (`spec-pyforge-testing-charter`, 5
capabilities) — mixed disposition, folded in 2026-08-02 from its own former
dream file. Two capabilities already shipped this session: CAP-1 (the
dashboard's `tea` glob corrected to `src/shared/packages/<slug>/tests/**/test_*.py`,
verified on disk in `docs/dashboard/generate.py`) and CAP-2 (real, generated
`test-architecture.md` for all 8 stations, replacing the six boilerplate
stand-ins a prior bulk commit had fabricated). CAP-5 (test architecture stays
current as stories land) is an ongoing practice, not a one-time build. **CAP-3
(a shared `pyforge-testing-kit` package — verified 2026-08-02, does not yet
exist) and CAP-4 (a CI coverage gate — verified 2026-08-02, no
`--cov-fail-under` in any workflow) are real, unbuilt, and not yet decomposed
to a PRD.** The Spec (and its `station-tea-status.md` companion — the real,
verified per-station test-file counts this Dream's own claims got wrong) stays
live as the reference for that remaining work.

Other open frontier items, unchanged: many-lines-one-floor concurrency (a
floor that survives two writers, not just isolated worktrees); crossing the
boundary between stations as structured, machine-checkable output; a crash an
unattended reader can act on; a run that cannot be torn down while still
alive; a seam for estates this factory cannot see ([[enterprise-airgap]]).

## Realization log

- **2026-07-25** — three loop-policy actions adopted from the pyforge-atlas
  retro: the independent review pass made standing, not self-flagged; a
  deferral repeated in a second wave promoted to contract level; story size
  capped and keystones split at authoring time.
- **2026-07-17/18** — atlas proven: a full system shipped unattended-with-gates.
- **2026-07-23** — Dream retro-seeded; execution doctrine affirmed (one owner,
  skills as the unit of execution, the harness as the unit of governance,
  deliberately not itself a skill).
- **2026-07-23 (later)** — concurrent-loop isolation shipped as
  [[regenerable-factory]] Wave 0.
- **2026-07-24** — `spec-pyforge-marshal` backfilled, binding `.bmad-loop/**`
  into governance.
- **2026-07-31** — five open questions ruled on in one sitting; sequencing
  resolved as *sequence on verdicts, never author them*. Same day, an audit
  found four factual errors written into this Dream's frontier section by a
  prior pass — the lesson recorded then and worth repeating now: a premise
  handed to an agent is not evidence.
- **2026-08-01** — durable-runs, fidelity-enforcement, and one-front-door
  decomposed into FR-61..65 / AD-46..50; PRD now FR-1..65, architecture now
  AD-1..50, epics now 6 epics / 50 stories.
- **2026-08-02** — dream consolidation: agent-portability, durable-runs,
  fidelity-enforcement, one-front-door, and pr-lifecycle archived as absorbed
  (their vision already lives in the FRs above); genesis-installer kept
  separate on purpose; fleet-chain-completeness moved in from Herald as a
  real, unbuilt frontier item. Story 2.1 found missing a resolved
  architecture decision (F-3/AD-26) in its own acceptance criteria — fixed
  the same pass. Marshal's chain re-verified end to end: all 65 FRs trace to
  a story both directions, 50/50 unique story ids, zero dangling dependencies.
- **2026-08-02 (second pass)** — factory-console archived as absorbed
  (dream-level only, `spec-factory-console` stays live for its own unbuilt
  frontier). herald-pitch (Herald's) similarly folded there. pyforge-testing-charter
  archived as absorbed — `spec-pyforge-testing-charter` stays live: 2 of its 5
  capabilities (correct dashboard TEA signal, real per-station test
  architecture) already shipped this session; the shared `pyforge-testing-kit`
  package and a CI coverage gate remain real, unbuilt, undecomposed work.
  fleet-chain-completeness's own dream file (this session's first pass had
  moved it in from Herald and given it a Spec) archived the same way —
  `spec-fleet-chain-completeness` stays live, undecomposed. All four of this
  second pass keep their Specs untouched; only the top-level Dream files
  consolidated.
- **2026-08-02 (third pass, explicit user override)** — the "genesis-installer
  kept separate on purpose" call from the pass above is **reversed for
  brief/PRD/architecture/Spec**: those four are now folded into this station's
  own single chain (§ Kept separate on purpose, above, revised). Only the
  installer's epics (`epics-genesis-installer.md`) stay separate, unchanged.
  Architecture gains AD-51..AD-65 (genesis-installer's former AD-01..AD-15);
  the Spec gains CAP-10..CAP-18 (former CAP-1..CAP-9); the PRD gains a
  Satellite section carrying genesis-installer's own FR1..FR62 (no dash,
  never renumbered into this PRD's own FR-1..FR-65). Two contradictions
  surfaced by the fold are flagged, not resolved, in the merged Spec's
  Constraints: the CLI framework (Marshal's shipped `argparse` vs
  genesis-installer's designed-but-unbuilt `typer`+`rich`), and a `check`
  verb collision (`marshal check`/FR-65 routes to `scripts/detectors.py`;
  genesis-installer's `genesis check`/CAP-13 re-implements a generic subset
  of `bmad_drift_check.py` for a different, external-repo question) — both
  feed the pre-existing Open Question 17 (installer verb mapping, still
  undecided). The four original standalone documents survive at
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/`.
