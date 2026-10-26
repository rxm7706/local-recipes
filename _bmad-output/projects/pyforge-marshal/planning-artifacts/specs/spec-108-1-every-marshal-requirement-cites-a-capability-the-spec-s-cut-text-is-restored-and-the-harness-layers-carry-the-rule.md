---
title: "108.1: Every marshal requirement cites a capability, the Spec's cut text is restored, and the harness layers carry the rule"
type: 'chore'
created: '2026-10-26'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - _bmad/custom/bmad-prd.toml
  - _bmad/custom/bmad-spec.toml
  - _bmad/custom/bmad-architecture.toml
  - _bmad/custom/bmad-build.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py
---

<intent-contract>

## Intent

**Problem:** Five marshal requirements cite a Spec Constraint (FR-120, FR-121, FR-125, FR-126 alone; FR-101 beside CAP-15), allowed by the 2026-10-25 rulings for Story 106.1; the 2026-10-26 re-audit showed the standard forbids the form and that each Constraint already lives as an AD (A-04, A-05, P-10, L-01) that does not name it. The pilot fold (`1e845b55fc`) left 124 placeholder titles, 11 one-letter titles, 138 '(see absorbed Spec memlog)' bullets and 280 cut bullets in the Spec the arrows point at. And the rule the Guild amended reaches a harness only if `_bmad/custom/` carries it, as the feature-flag mandate does (Story 74.3).

**Approach:**
- **Re-point the five.** FR-101 ← CAP-15 (the `--force` flag is the update verb's); FR-120 ← CAP-14, CAP-15 (ruling (a): the verbs that call Copier); FR-121 ← CAP-14, CAP-15, CAP-12 (`seed adopt` feeds templates through `copier.run_copy`, `seed/verbs/adopt.py`); FR-125 ← CAP-17 (state records both versions), CAP-13 (`seed check` reports model vs bundled); FR-126 ← CAP-13 (typed, stable findings with documented exits). Only the arrow text changes.
- **The AD names the Constraint.** A-04 and A-05 gain an *Implements Spec Constraint* sentence; the P-10 and L-01 table rows say which Constraint they implement and for which CAPs (CHAIN-STANDARD § 12).
- **Restore the Spec text.** `restore_caps.py` over `1e845b55fc^` (SPEC.md blocks, and each absorbed Spec's memlog `(capability)` entries where the SPEC.md carried only a status or mapping paragraph): titles restored from source lines (59, including the 11 one-letter ones), 76 authored from intent (the memlog decision lists every one), 137 placeholder bullets restored, 1 success authored (CAP-210), 280 bullets rejoined; three memlog `correction` entries record the render and its two parser fixes. 292 capability lines before and after; no id, order or provenance moves.
- **The harness layers** (marshal Story 74.3's placement): `bmad-prd.toml` (new) — the PRD author traces arrows from the CAP's intent and success and never cites a Constraint; `bmad-architecture.toml` (new) — an AD that implements a Constraint names it; `bmad-spec.toml` — a visible guarantee is a CAP, a design-bending Constraint stays a Constraint realized by an AD, never a requirement source; `bmad-build.toml` — the `fr-arrow` review lens checks each new or changed arrow on a PRD diff against the cited CAP's definition and text.
- **`type: chore`, no flag.** Planning artifacts and team overrides only; built in the chain PR.

Ledger key: `108-1-every-marshal-requirement-cites-a-capability-the-spec-s-cut-text-is-restored-and-the-harness-layers-carry-the-rule`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-12, CAP-13, CAP-14, CAP-15, CAP-17**: the capabilities the five requirements now cite; each arrow traced from the CAP's success (the memlog decision carries the five rows with their evidence).
- **`spec-one-chain-per-station` CAP-5** (amended) and **CAP-8** (the marshal pilot): the rule, and the fold this story corrects.
- **`spec-feature-flag-governance` CAP-6** (Story 74.3): the precedent for a mandate carried as `persistent_facts` and a review layer rather than in an installer-owned skill file.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-26 entry; the operator's 2026-10-26 rulings (a) and (e).

## Acceptance Criteria

- **AC1 — The five arrows.** A diff of the PRD's `- **FR-` lines against `92fa3edbbd` shows exactly 5 changed lines (FR-101, FR-120, FR-121, FR-125, FR-126), each arrow naming only `CAP-m` items; no other FR line changed.
- **AC2 — The ADs.** A-04, A-05, P-10 and L-01 each name the Constraint they implement and the CAP(s) it bounds; no AD added or removed.
- **AC3 — The Spec text.** `grep -c ' — from spec-' SPEC.md` is 0 (was 124); `grep -c '(see absorbed Spec memlog)' SPEC.md` is 0 (was 138); no title is shorter than four characters; 292 `- **CAP-` lines before and after; each authored title shares a content word with its intent and duplicates no other title.
- **AC4 — The layers.** `_bmad/custom/bmad-prd.toml` and `bmad-architecture.toml` exist with `[workflow] persistent_facts` carrying the mandate; `bmad-spec.toml`'s list has two facts; `bmad-build.toml` has a `[[workflow.review_layers]]` entry with `id = "fr-arrow"`; every file parses as TOML.
- **AC5 — Gates.** `fr-without-cap` reports no marshal FAIL and no counted run (CAP-235..CAP-238 titles restored); `chain-completeness`, `chain-currency` (marshal) and `detectors-ci` are green; `pyforge-marshal-test` passes.

## Boundaries & Constraints

**Always:**
- Memlog decisions before the render; the script asserts the CAP count; re-stamp PRD, spine and epics in the same commit; keep every `_bmad/custom/` fact under the key the installer's `customize.toml` names.

**Never:**
- Never change an FR's number, title or body beyond the five arrows; never renumber, add or remove a CAP; never hand-edit `SPEC.md`; never put a mandate in an installer-owned `SKILL.md`.

## I/O & Edge-Case Matrix

| Line | Before | After |
|---|---|---|
| FR-101 | `← CAP-15, Constraint "Copier is a dependency, not a framework"` | `← CAP-15` |
| FR-120 | `← Constraint "Copier is a dependency, not a framework"` | `← CAP-14, CAP-15` |
| FR-121 | same | `← CAP-14, CAP-15, CAP-12` |
| FR-125 | `← Constraint "Two clocks"` | `← CAP-17, CAP-13` |
| FR-126 | `← Constraint "Every finding type is a member of one enum …"` | `← CAP-13` |
| A-04, A-05, P-10, L-01 | carry the Constraint unnamed | name it and the CAPs it bounds |
| SPEC.md | 124 placeholder titles, 11 one-letter titles, 138 placeholder bullets, 280 cut bullets | restored (76 titles, 1 success authored; recorded) |
| `_bmad/custom/` | flag mandate only | + requirement-arrow mandate in four files |

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-marshal` CAP-12, CAP-13, CAP-14, CAP-15, CAP-17; `spec-one-chain-per-station` CAP-5 (amended) and CAP-8; `spec-feature-flag-governance` CAP-6 (placement precedent). No marshal CAP is minted.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 108 (new), minted with this story and with Story 108.2 (`backlog`); CAP-297 minted on the review and cited by FR-125. `epic-108` and `epic-108-retrospective` are minted with it.
- Ledger key: `108-1-every-marshal-requirement-cites-a-capability-the-spec-s-cut-text-is-restored-and-the-harness-layers-carry-the-rule`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (this story touches no marshal code).

**Run before the push (not dispatch gates):**
- `git diff 92fa3edbbd -- _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md | grep -c '^+- \*\*FR-[0-9]*\*\* ←'` — expected: `5` (AC1).
- `grep -c ' — from spec-' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md` — expected: `0` (AC3).
- `python3 -c "import tomllib,glob;[tomllib.load(open(p,'rb')) for p in glob.glob('_bmad/custom/bmad-*.toml')]"` — expected: exit 0 (AC4).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: no marshal FAIL (AC5).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-marshal` — expected: no errors (AC5).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC5).

## Auto Run Result

Status: in-review (hand-built in the chain PR)
Implementation: the five arrows; A-04/A-05/P-10/L-01; `restore_caps.py` over `1e845b55fc^` (three correction entries, the authored-text decision, self-validate passes 1 and 2 logged); the four `_bmad/custom/` layers; PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26 (Story 108.1).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

## Review Triage Log

- (none yet)
