# Marshal — Phase 1 backlog-truth audit (2026-08-10)

Gate report of `spec-artifact-chain-reconciliation` (CAP-2/CAP-4), third and
largest station (103 stories, 67 done, 35 backlog + 1 blocked). Method:
`audit-method.md`. Station suite: **3157 passed, 9 deselected** (executed).
The blind pair REFUTED this report's first draft in load-bearing places;
every correction is applied below and the draft's errors are named where
they change dispositions.

## The headline finding: an incomplete fold-in — on both sides

The 36 remaining stories (Epics 7–12, the `marshal seed` block) came from the
retired genesis-installer satellite. The architecture recorded a complete
renumbering mapping on 2026-08-08 (Part II: `FR1..62` → `FR-66..127`,
`AD-01..15` → `AD-51..65` verbatim table) — but **neither side finished**:

- **epics.md never received the renumbering at all** — 195 citations in the
  retired namespace, unresolvable against the current PRD. The
  `spec-genesis-installer-name-retirement` Spec is banner-stamped **SHIPPED
  2026-08-08** with success defined as "zero bare forms outside archive/" —
  **that claim was false until this landing** (195 live).
- **The architecture itself still carries the retired name as live rules**:
  AD-64 mandates `genesis = "pyforge.genesis.cli:main"` verbatim
  (architecture.md:1102-1113), FR-118 says templates ship "inside the
  `pyforge-genesis` package" (prd.md:1564), and Part II's body still reads
  "Distribution: `pyforge-genesis` / `pyforge.genesis` / `genesis`" — while
  Part II's own preamble retires the name and AD-70 mandates one argparse
  tree. The contradiction is **architecture-internal**.

**Repaired this landing (mechanical, verified by the reviewer at all 195):**
FR/AD citations re-issued (159 FR at +65, 36 AD at +50, zero mismatches,
Epics 1–6/13 provably untouched — the satellite's bare/zero-padded style made
collision impossible by construction); retired `NFR-O1` → `NFR-12` at its 4
surviving sites (the mapping row the first pass skipped); **S-12.5's AC
re-issued** — the renumbered AD-51 citation had inverted meaning (the AC
ordered a typer/rich import-location test; amended AD-51 forbids typer/rich
entirely); the Epic List table corrected (E1=12, E3=10, E4=15, E5=7, E13 row
added, total 86→103 — its "verified three ways, all agree at 86" note was
false when written); 5 unpromoted done-story specs (4-11..4-15) promoted from
gitignored Tier-3.

## Traceability matrix — the 36 remaining stories

| Claim | Ledger | Code reality (citation) | Verdict | Action |
|---|---|---|---|---|
| 7-1 package skeleton (`pyforge-genesis`, `genesis` entry point) | backlog | Story text **faithfully transcribes live AD-64** — which Part II's preamble + AD-70 contradict ("the name `genesis` is retired"; one argparse tree, "two parsers in one binary" prevented). No later decision revives the name (PROJECTS.md records the project dissolved 2026-08-02) | **CONTRADICTED** — by the architecture's own internal split, not by the story's sloppiness | `bmad-correct-course` must re-issue **AD-64 + FR-118 + Part II body + the story ACs together**; fixing stories against the current upstream would re-transcribe the retired name |
| 7-2..7-5 taxonomy, write guard, manifest loader, V1 manifest | backlog | No pre-empting code (no seed module, no manifest schema in the package); write-guard-first sequencing sound; module refs ride the 7-1 naming decision | **STILL-VALID ×4** | after the naming session |
| 7-6 Spike-0 Copier fit (CRITICAL GATE) | backlog | `copier` absent workspace-wide (verified zero pixi.toml refs) — the spike's reason to exist; failure path re-decides AD-52 | **STILL-VALID** | dispatch early; gates E10 |
| 8-1..8-4 marker/region engine | backlog | No marker/region code anywhere in the package; self-contained ACs | **STILL-VALID ×4** | after E7 |
| 8-5 marker deletion opt-out | **blocked** | Cross-epic dep (S-10.2); the fleet's only `blocked` key; `promote_sprint_status.py` classes it non-terminal; Tier-3 twin agrees | **STILL-VALID, correctly blocked** | unblocks at 10-2 |
| 9-1..9-6 detect & plan | backlog | No detect/plan code; citations now resolve (FR-93 spot-verified: "check runs offline <5s" ↔ 10-5's AC; FR-112 ↔ 8-5) | **STILL-VALID ×6** | after E7 |
| 10-1..10-7 materialize + core verbs | backlog | Verb headings already `marshal seed <verb>` (AD-54's noun group); copier wrapper gated by 7-6 | **STILL-VALID ×7** | after 7-6 |
| 11-1..11-6 derive/migrate/update | backlog | 11-5's Doctor delegation matches doctor's landed `sources/` registry; 11-2's symlink premise matches the live layout | **STILL-VALID ×6** | after E10 |
| 12-1..12-6 packaging, oracle, hardening | backlog | 12-1 owns the pixi wiring 7-1 defers; 12-5's AC now matches amended AD-51 (fixed this landing); empty-plan oracle premise sound | **STILL-VALID ×6** | last |

**Disposition: 34 STILL-VALID, 1 correctly blocked, 1 CONTRADICTED (7-1,
architecture-internal).** One `bmad-correct-course` session: AD-64 + FR-118 +
Part II body + story-text naming (54 `genesis` occurrences measured across
E7–E13's range) + `Surface:` lines for the block (OBS-R1).

## Artifact findings

| # | Finding | Evidence | Action |
|---|---|---|---|
| AF-R1 | E7–E12 + appendices cited the retired namespace — 195 unresolvable refs in the canonical story source; the retirement Spec's SHIPPED banner was false | reviewer-verified at all 195; `spec-genesis-installer-name-retirement` CAP-2/3 | **Fixed** (FR/AD); memlog note appended to the retirement spec recording the falsified-then-satisfied banner |
| AF-R2 | `genesis` naming: live AD-64/FR-118 vs Part II retirement — architecture-internal contradiction; 7-1 transcribes the losing side | architecture.md:1102-1113, prd.md:1564 vs :667, AD-70 | Epic-7 dispatch guard amended (post-review) to name the real scope; → correct-course |
| AF-R3 | Ledger epic-1 rollup stale (12/12 done) — 4th station with the same class | ledger + Tier-3 | **Fixed** via Tier-3 + `sprint-ledger-sync` |
| AF-R4 | Retired `NFR-O1` cited at 4 sites incl. a coverage-matrix row claiming coverage of a requirement that no longer exists | prd.md:1034,1637 retirement rows | **Fixed** → NFR-12 |
| AF-R5 | S-12.5's AC semantically inverted by the renumber (typer/rich test vs amended-AD-51 prohibition) — caught by the blind pair, falsifying the draft note's "non-naming ACs verify sound" | epics.md:2359 (old), AD-51 amended text | **Fixed** — AC re-issued |
| AF-R6 | Epic List table wrong for 4 epics, omitted E13, total 86 vs 103 — under a note claiming three-way verification | epics.md:90-108 | **Fixed** with a dated correction note |
| AF-R7 | **5 done-story specs unpromoted** (4-11..4-15, the five most recent Epic-4 landings — including the story *about* the ledger reaching tracked state) | git ls-files vs implementation-artifacts | **Fixed** — promoted (3rd station: mason 6, marshal 5) |
| AF-R8 | **FR-128..FR-163 — 36 PRD-defined FRs with zero decomposition anywhere** (8 absorbed Specs: testing-charter, loop-home-fleet-refresh, sprint-status-auto-promote, dashboard-path-derivation, detector-self-verification, fleet-chain-completeness, agent-tool-surface, pyforge-core); AD-66/67/71 bind stories that do not exist | prd.md:6; probe of FR-1..180 vs epics.md | The fleet's largest decomposition gap — routed to Phase 3 planning (this is the 10-1/FR-157 memory's other half: FR-157 has an AD and no story) |
| AF-R9 | test-architecture.md scoped to "All 50 stories (E1–E6)", 53 stories/3 epics missing — against FR-132 ("test architecture stays current") | test-architecture.md:7,154,412 | → `bmad-document-project` at marshal re-plan (3rd station, same class) |
| AF-R10 | `epics-with-stories.md` derived twin never regenerated (50/6 vs 103/13); repo-level `index.md` parked here, stale (5 packages vs 8, self-contradicting env counts); README SYNC-RUNBOOK link broken (fixed) | epics-with-stories.md:6-9; index.md:41 | Twin + index → same document-project session; link **fixed** |
| AF-R11 | Two live CRITICAL escalation records in Tier-3 for story 4.12 — which is done and demonstrably landed (`cli/land.py:87`, `adapters/vcs_git.py:1003`) | runs/…99e553ef, …c396f50d | Re-spin preflight hazard (steward-AF-4 class): clear/annotate before spin; S-5.3's queue will show 2 resolved-but-open CRITICALs |

## Done-claim sample — 21 of 67, all held

3 per done epic. **Evidence method varies by epic and is stated per row**
(the draft implied Surface-line verification for all 21; 6 rows verify by
landing evidence instead — 4.x carry no Surface lines, and Epic 13 has none
at all, contra the draft's OBS-R1).

| Epic | Sampled | Evidence (method stated) |
|---|---|---|
| 1 (12) | 1.2, 1.7, 1.10 | Surface files verified: `core/identity.py`+`tests/unit/test_identity.py`; `cli/init.py`+`adapters/harness_bmadloop.py`+`ports/harness.py`; `tests/meta/test_rendered_policy_untracked.py` |
| 2 (7) | 2.1, 2.2, 2.5 | Surface files verified: `core/gate.py`, `core/verdict.py`+`tests/unit/test_verdict.py`, `core/policy.py` |
| 3 (10) | 3.1, 3.2, 3.8 | Surface files verified: `core/journal.py`+`schemas/journal.json`, `tests/unit/test_fold.py`, `supervisor/durability.py`+`cli/spin.py` |
| 4 (15) | 4.12, 4.13, 4.15 | **Landing evidence** (no Surface lines): Phase 0D patch-id matches (`f93a4f7f2b`, `ad4f274f60`, `5947637ebc`), Epic-4 closure PR #387; 4.12's code present at `cli/land.py:87`, `adapters/vcs_git.py:1003` |
| 5 (7) | 5.1, 5.3, 5.6 | Surface files verified: `core/status.py`+`cli/status.py` (5.1 and 5.3 declare identical surfaces — the suite's status-contract tests are the differentiator), `cli/check.py`+`core/context.py` |
| 6 (9) | 6.2, 6.4, 6.5 | Surface files verified: `cli/adapters.py`, `adapters/harness_bmadloop.py`, `core/conformance.py` |
| 13 (7) | 13.1, 13.3, 13.5 | **Evidence by use** (no Surface lines): this audit's Phase 0 exercised Epic 13's deliverables directly — scoped stamps, `[drift-presumed]`, per-file memlog matching; PRs #326/#327/#329/#330 |

## TEA / coverage-debt

Sampled Surface files carry their named tests; suite 3157 as batch test-half.
Package hygiene verified clean by the blind pair: zero TODO/FIXME/xfail, all
5 skips environment-conditional, no dead config. E7–E12 meta-test story
(12-4) chartered.

## Verdict

Marshal's remaining block is **coherent and buildable behind one
correct-course session** — but that session's true scope is larger than any
story: it must resolve the architecture's own internal split (AD-64 + FR-118
vs Part II/AD-70), then re-issue 7-1 and the block's naming. The citation
namespace is repaired and reviewer-verified at all 195. **AF-R8 is the
audit's largest single finding fleet-wide**: 36 PRD FRs (8 absorbed Specs)
with no stories, while ADs already bind them — Phase 3 planning work, not a
dispatch blocker for E7–E12. The 67 done stories sampled at 31% held without
exception. Dispatch order when re-spun: correct-course (naming + AD split) →
7-2..7-6 → E8..E12; FR-128..163 decomposition is its own planning effort.
