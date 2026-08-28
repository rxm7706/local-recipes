---
id: SPEC-conda-forge-expert-rebuild
spec: conda-forge-expert-rebuild
status: in-progress
updated: "2026-08-28"
owner-dream: docs/dreams/conda-forge-expert-rebuild.md
surface:
  - .claude/skills/conda-forge-expert/**      # the skill being rebuilt slice by slice (parallel-run target; flips at the end cutover)
  - .claude/scripts/conda-forge-expert/**     # CLI wrapper layer — each slice redirects its wrappers
  - .claude/tools/conda_forge_server.py       # MCP registrations — each slice redirects its tools
sources:
  - ../../../../../../docs/dreams/conda-forge-expert-rebuild.md
  - ../spec-pyforge-mason/SPEC.md                                              # D-1 (wrap, never fork) — reopened for CFE only, untouched for Mason
  - ../../research/market-mason-packaging-automation-2026-08-08.md             # CFE ground truth: v8.81.0, 67 canonical scripts, 46 MCP tools
  - ../../../pyforge-atlas/planning-artifacts/retros/epic-1-wave-0-skill-forge.md  # the rebuild-without-migration precedent this Spec is structured against
---

> **Canonical contract (ready, 2026-08-10).** Distilled from the Dream via `bmad-spec`. This is the
> five-field contract for the rebuild effort; the planning chain (PRD → epics) decomposes
> it per slice per the operator directives of 2026-08-10 (rebuild GO; parallel-run shape); the remaining Open Questions are the pilot slice's outputs, not gates.

# conda-forge-expert rebuild — Skill-Forge-authored, slice by slice, parallel-run to an enforced end cutover

## Why

`conda-forge-expert` is the repo's largest and most actively maintained asset: ~41,410 LOC,
v8.81.0 with 100+ dated releases, 106 gotchas and 10 hard constraints earned one build
failure at a time, 67 canonical scripts, ~57 CLI wrappers, 46 MCP tool registrations, and
a 3-tier layout (skill scripts → CLI wrappers → MCP server) that every pixi recipe task and
every BMAD conda-forge effort routes through. It was accreted, not designed — and the repo
now carries Skill Forge (`_bmad/skf/`: `skf-analyze-source`, `skf-brief-skill`,
`skf-create-skill`, `skf-audit-skill`, `skf-campaign`), a toolchain built to compile skills
from briefs with drift auditing and campaign-scale resume.

The user explicitly reopened Mason's D-1 ("wrap, never fork the craft") **for CFE itself
only** and chose **full scope** — all tiers, all tools — but bound to one non-negotiable
discipline — originally **hard cutover per slice**, re-shaped 2026-08-10 by operator
override to **parallel-run with a detector-enforced end cutover**. The `pyforge-atlas`
precedent remains the reason either way: ~29,000 rebuilt lines (PRs #58–#105, all merged)
that never displaced the 8,902-LOC legacy `conda_forge_atlas.py`, because migration was
deferred to a future that never came — under parallel-run, the equivalence harness, the
dual-landing rule and the endgame detector (CAP-3) are what make that outcome structurally
impossible. Every slice ships parallel-validated in the epic that builds it; the caller
flip and retirement ship once, at the recorded end cutover, and the campaign cannot close
without it.

This Spec is honest about scale: full scope is a **multi-epic, multi-session campaign**
comparable to the atlas migration (32 stories). The contract therefore commits concretely
to the slice map and the **first slice end-to-end** (build + parallel-validate + audit; cutover and retirement are campaign-end), and
commits to the remainder only as campaign-tracked sequence, re-scoped after the first
slice's real cost is measured.

## Capabilities

- **CAP-1 — the slice map, derived not guessed**
  - **intent:** Before any brief is written, `skf-analyze-source` runs against the live
    skill (`.claude/skills/conda-forge-expert/`) to confirm or correct the Dream's
    hypothesized seams (recipe-authoring · atlas-intelligence · project-scanning/MCP) and
    produce the authoritative slice map.
  - **success:** A tracked slice-map artifact under this Spec's directory lists every slice
    with: its canonical scripts, its CLI wrappers, its MCP tool registrations, its pixi
    tasks, its SKILL.md/reference/guides knowledge sections, and its **complete caller
    inventory** (including Mason's `cfe.py` adapter surface). Coverage is total — every one
    of the 67 scripts, ~57 wrappers, and 46 MCP tools appears in exactly one slice (derive,
    don't declare); an unclassified file is a failing check, not a gap. The map fixes the
    slice ordering and names the first slice explicitly.

- **CAP-2 — first slice: recipe generation, built + parallel-validated in one epic** *(re-derived 2026-08-10: operator chose parallel-run-then-end-cutover over per-slice cutover)*
  - **intent:** The recipe-generation slice — `scripts/recipe-generator.py` and its
    satellites, the `generate_recipe_from_pypi` / `update_recipe_from_github` MCP tools,
    their wrappers and pixi tasks, plus the generator's knowledge (G54 source-decision
    order, G91 build-system mirroring, G94c/G98 naming, the CFE-block emission contract) —
    is compiled as a Skill-Forge-authored replacement and **parallel-validated** in the same
    epic (the live original stays authoritative; flip and retirement are campaign-end). Chosen first because it is the skill's most volatile surface (v8.69/v8.70/v8.81
    all churned it), has the richest regression-test net, and has a small, enumerable
    caller set.
  - **success:** `skf-brief-skill` produces the slice brief with the relevant gotchas and
    constraints as verbatim inputs; `skf-create-skill` compiles the replacement; the slice's
    existing regression tests pass unmodified against the replacement (behavioral
    equivalence, not rewritten expectations); the **equivalence harness** runs old and new
    against the same corpus and reports zero divergence; `skf-audit-skill` reports zero
    drift. **The old path remains authoritative and every caller keeps resolving to it** —
    caller flip and retirement happen once, at the campaign's end cutover (CAP-3).

- **CAP-3 — the anti-atlas guard, parallel-run form: divergence and the endgame enforced by a detector, not by discipline** *(re-derived 2026-08-10)*
  - **intent:** Parallel-run's two killers — silent divergence between the live original and
    the replacement, and an end cutover that never comes (the atlas outcome) — are made
    structurally impossible by a repo detector, in the style of `scripts/dream_chain_check.py`.
  - **success:** A detector (registered in `scripts/detectors.py`) reads the slice map and
    fails CI when (a) any slice marked `parallel` has a red or stale equivalence-harness
    result — old and new must agree on the shared corpus at every commit; (b) any Rule-2
    retro landing in the live skill is not mirrored into the affected slice briefs
    (dual-landing rule) — while parallel, knowledge has two homes ON PURPOSE and the
    detector is what makes that survivable; or (c) the campaign reaches its declared
    endgame date/state and any caller still resolves to legacy, or legacy code survives
    without a dated deprecation marker. It exits green pre-rebuild and each clause is
    proven red by a fixture before the first slice lands. The campaign cannot close — and
    the Dream cannot read `realized` — until the end cutover completes under clause (c).

- **CAP-4 — campaign state: the sequence survives sessions**
  - **intent:** The multi-slice sequence is tracked by `skf-campaign`'s file-based state
    with resume, so the effort behaves like a `bmad-loop` run — interruptible, resumable,
    auditable — rather than living in any one session's memory.
  - **success:** Campaign state records per-slice status (mapped → briefed → compiled →
    cut-over → audited → retired), survives session teardown, and a fresh session can
    resume from state alone; after the first slice completes, a dated re-scope note in the
    campaign state records the measured cost and the go/adjust/stop decision for the
    remaining slices before any second brief is written.

## Constraints

- **Rule-1 delegation must never break mid-rebuild.** CFE (or its slice-wise successors)
  remains the authoritative, invocable skill for all conda-forge work at every commit on
  `main`. Mason's `cfe.py` wrap-by-subprocess, every pixi recipe task, and every MCP tool
  stay functional throughout; entry-point compatibility per slice is a gate, and an
  incompatible drift is a defect in this effort, not a license to reopen Mason's D-1.
- **Parallel-run with an enforced endgame (operator override, 2026-08-10).** The original
  hard-cutover-per-slice rule was overridden in-session with the atlas precedent explicitly
  on the table: slices are built and validated IN PARALLEL with the live original, which
  stays authoritative throughout; the caller flip and legacy retirement happen once, at a
  declared end cutover. The override is survivable only with CAP-3's three clauses
  (equivalence harness, dual-landing, detector-enforced endgame) — weakening any of them
  reverts this effort to the rejected atlas shape.
- **No knowledge loss.** The 106 gotchas and 10 critical constraints in `SKILL.md` /
  `reference/` / `guides/` are verbatim inputs to each slice's brief; Skill Forge never
  re-derives them, and each slice's audit checks its gotchas survived into the replacement.
- **Rule 1 and Rule 2 continue to bind** whatever replaces CFE: the successor skill's
  guidance stays authoritative over BMAD stories, and every conda-forge effort — including
  each slice epic of this rebuild — still closes with a retro that lands skill edits, a
  CHANGELOG entry, and a semver bump.
- **Mason's own architecture is out of scope for this effort's STORIES.** This Spec changes
  what lives at the CFE root, never how Mason reaches it — no rebuild story edits Mason's
  PRD, ARCHITECTURE-SPINE, or Epic 5. *(Clarified 2026-08-10: governance changes that this
  effort NEEDS from Mason — the AD-15 amendment, FR-45 scoping, S-5.2 re-issue — route
  through Mason's own correct-course, as happened that date. The constraint forbids the
  rebuild's implementation from reaching into Mason's contracts, not Mason from governing
  itself.)*
- **The test net is the safety rail.** Existing CFE tests (unit + meta, ~1,186 across the
  suite) run green at every slice boundary; a slice may add tests but may not weaken or
  delete existing ones to pass.

## Non-goals

- **Not an untracked drift into permanence.** Full scope, delivered as parallel-validated slices with ONE tracked, detector-enforced end cutover — the campaign cannot close without it (re-shaped 2026-08-10).
- **Not a redesign of the lifecycle.** The 10-step loop, Operating Principles, Build
  Failure Protocol, and the gotcha corpus are carried forward, not reinvented.
- **Not an atlas re-rebuild.** The `pyforge.atlas` Kedro stack and the legacy
  `conda_forge_atlas.py` question is *informed by* this effort's cutover discipline but is
  not in this Spec's scope; if the atlas-intelligence slice reaches the front of the queue,
  its brief decides whether to cut over to the legacy path's rebuild or to `pyforge.atlas`
  — a decision recorded then, not now.
- **Not a change to Mason's verbs, seam, or knowledge deny-list.**

## Success signal

A session six months from now invokes conda-forge recipe generation and lands on
Skill-Forge-authored code with zero legacy generator path remaining; the CAP-3 detector is
green in CI; campaign state shows every completed slice as parallel-validated (equivalence green), the end cutover recorded as executed, and none
parked in "built, unmigrated"; and no user of `mason recipe`, the pixi tasks, or the MCP
tools noticed the transition except through the CHANGELOG.

## Open Questions

1. **Is this genuinely Mason's to own, or cross-station?** The Dream is owned by `mason`
   (so this chain lives here per INV-2), but CFE is repo-wide infrastructure serving every
   station, and the atlas-intelligence tier arguably belongs to `atlas`. Should the slice
   map assign per-slice station ownership (mason owns the campaign, atlas owns its tier's
   briefs), or does mason own the whole rebuild? Needs an operator decision before any
   slice beyond the first.

   **Resolved — 2026-08-28 (Story 12.5).** **Per-slice station ownership.** Mason owns the
   campaign through-line — `campaign-state.yaml`, the guard detector, the re-scope gates,
   and the endgame/cutover. Atlas owns the Slice-3 (atlas-intelligence) tier: when slices
   3–5 decompose after Story 12.8's checkpoint, Slice 3's brief is authored on and its
   stories carried by the `pyforge-atlas` chain, with its Rule-2 retro and equivalence
   sign-off owned by atlas. Rationale (operator, after full briefing): atlas is the tier's
   station of competence — it already rebuilt the `cf_atlas` orchestrator as the live
   Kedro/DuckDB estate and owns the CAP-19 query plane this tier's data feeds — so atlas
   ownership forces the legacy-vs-Kedro convergence question into the right hands instead
   of risking a parallel rebuild of the legacy tier. Precedent: CAP-19's "atlas owns the
   engine, steward owns the through-line" split, and Phase-T trending landing as atlas
   Epic 13 despite its mason handoff. Slices 1, 2, 4, and 5 remain mason-owned under this
   ruling — only the Slice-3 tier moves. Mirrored into `campaign-state.yaml`
   (`campaign.ownership_decision`; closes `re_scope_gate.pre_conditions.d_ownership_decision`).
2. **Can `skf-create-skill` actually carry ~41K LOC of *implementation*?** Skill Forge
   compiles skills (knowledge + progressive capability); CFE is knowledge *plus* a large
   tested Python codebase. The first slice must establish whether "Skill-Forge-authored"
   means Forge compiles the knowledge layer while code migrates conventionally under the
   brief's contract, or Forge genuinely drives code generation. The answer re-scopes
   everything after CAP-2.
3. **Does full scope survive the first slice's measured cost?** The user chose full scope
   with eyes open; CAP-4's re-scope gate is where that choice gets its first real price
   tag. Stopping after a clean first slice is an allowed outcome of the gate, not a
   failure of the Spec.
4. **What is the deprecation posture for the long tail?** Delete-on-cutover is cleanest
   for the detector; a dated stub is kinder to out-of-repo callers (Mason installed
   elsewhere). Per-slice choice, but the default needs deciding in the slice map.
5. **How do Rule-2 retros work mid-campaign?** Each slice epic ends with a retro — but
   does it edit the legacy `SKILL.md`, the successor slice's skill, or both during the
   overlap window? The first slice's retro sets the precedent.

## Decomposition record — 2026-08-27 (reconcile pass; status `ready → in-progress`)

Reconciled against mason's chain (`epics.md`, the tracked `sprint-status-ledger.yaml`, this
directory's `campaign-state.yaml` + `slice-map.md`, and `scripts/cfe_rebuild_guard_check.py`'s
live output). Capability coverage as found:

- **CAP-1 — decomposed and done.** Story 6.1 (`6-1-slice-map-and-campaign-state: done`;
  commit `23130ee53f`, PR #570, 2026-08-21). `slice-map.md` derives 5 slices covering all
  68 scripts / 57 wrappers / 46 MCP tools with zero unclassified files; ordering fixed,
  first slice named.
- **CAP-2 — decomposed and done for the pilot, with a recorded substitute.** Story 6.3
  (done; commits `bf81f0b7ff` BLOCKED-then-retry + `ec193303b6`, PR #586). Slice 1 is
  `compiled` with `equivalence: green` (60/60 regression + 6/6 equivalence tests); clause 5
  (skf-audit-skill zero drift) was verified by a manual sha256 substitute because
  `forge-tier.yaml` is absent (campaign-state GATHERED GAPS #1) — the real-audit residual is
  now **Story 12.3**. CAP-2's pattern for slice 2 is **Stories 12.6/12.7**.
- **CAP-3 — decomposed and done for the detector, open on enforcement.** Story 6.2 (done;
  commit `1510a022e6`, PR #578) shipped `scripts/cfe_rebuild_guard_check.py`, all three
  clauses proven red by fixture. Residuals: the CI step is advisory-only (`exit 0` always —
  GATHERED GAPS #2; "fails CI" is not yet literally true) → **Story 12.2**; the detector has
  a LIVE clause-(b) finding today (4 qualifying Rule-2 retros in `806cb63046..HEAD`, newest
  `565ef7d194`, none mirrored into slice 1's brief) → **Story 12.1**; the re-scope gate
  itself is unenforced (GATHERED GAPS #5) → **Story 12.4**.
- **CAP-4 — decomposed and done.** Stories 6.1 + 6.4 (done; commit `f04553bced`).
  `campaign-state.yaml` tracks per-slice status, survives sessions, and carries the dated
  re-scope note (2026-08-21, decision **ADJUST**: four pre-conditions gate slice 2's brief).
  The second checkpoint the note recommends before the 12.3x slice is **Story 12.8**.

**Uncovered remainder → Epic 12** (`epics.md`, 8 stories, `backlog` in the tracked ledger):
gate closure (12.1–12.5, mapping 1:1 to the live clause-(b) finding, pre-conditions (a),
(b), (d) and gap #5) and the campaign's continuation through slice 2 (12.6–12.8, honoring
pre-condition (c)). Open Question 1 above is now owned by **Story 12.5**. Slices 3–5 and
the end cutover (clause (c) endgame) deliberately remain undecomposed until Story 12.8's
recorded decision — the campaign decomposes in checkpoint-gated waves, per this Spec's own
"commits to the remainder only as campaign-tracked sequence" and Epic 6's
decompose-no-further discipline. Nothing in this pass implemented, briefed, or compiled any
slice; the live skill remains authoritative throughout.
