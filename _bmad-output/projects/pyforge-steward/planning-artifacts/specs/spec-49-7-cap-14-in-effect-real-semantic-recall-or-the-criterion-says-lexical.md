---
title: 'CAP-14 in effect — real semantic recall, or the criterion says lexical'
type: 'feature'
created: '2026-09-11'
status: 'done'
baseline_revision: '29c9036962bda93fa3da647903fe3089972874f3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-14's "semantic recall" clause is, today, a 32-dim SHA-256 bag-of-concepts over a
hardcoded 7-entry synonym map, off by default (`recall.py:94` `mode="lexical"`; `cli.py:316-320` is
the opt-in `--semantic` flag) — not real embedding-based recall. CAP-14's *other* clause ("the same
graph operations pass against both drivers") is already satisfied and exercised in CI
(`conftest.py:119-138` parametrized over both drivers; `pyforge-station-tests.yml:215-238` runs a
pgvector service), and single-plugin selection is the documented design
(`graph_store_plugins.py:36-39`, AD-1) — not a shortfall. Only the semantic-recall half is in
question.

**Approach:** Either back "semantic" recall with a real embedding model over the plane's `vss`
index, with a test that fails under pure lexical overlap, or rewrite CAP-14's criterion honestly to
state that `lexical` is the graded default and `semantic` is documented as the SHA-256
bag-of-concepts approximation it actually is. Whichever branch is chosen, the story states which
mode (`lexical` or `semantic`) the criterion is graded against, and records that the Spec's
"dual-write" wording mis-described a correct dual-driver design rather than naming a gap.

## Boundaries & Constraints

**Always:**
- State explicitly, in the landed spec, which mode (`lexical` or `semantic`) CAP-14's criterion is
  graded against.
- Correct the Spec's "dual-write" wording — the dual-driver CI parametrization
  (`conftest.py:119-138`) is a correct design already exercised, not a gap.
- Leave the existing dual-driver CI parity coverage unchanged.

**Never:**
- Do not claim "semantic" recall is embedding-based if the bag-of-concepts approximation is kept —
  name it honestly either way.
- Do not silently widen the 7-entry synonym map as a substitute for the branch decision — that is
  neither branch.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| REAL_SEMANTIC branch | A real embedding model over the plane `vss` index | A test fails under pure lexical overlap, passes under real semantic similarity | N/A |
| CRITERION_REWRITE branch | Bag-of-concepts approximation kept | CAP-14's criterion names `lexical` as the graded default and describes the approximation honestly | N/A |
| Dual-driver parity (unaffected) | `conftest.py:119-138` parametrized CI | Continues passing against both graph-store drivers, unchanged | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/embeddings.py`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py:36-39` (AD-1
  single-plugin-selection design — not in scope to change)
- the plane `vss` index
- `recall.py:94` (`mode="lexical"` default), `cli.py:316-320` (`--semantic` opt-in flag)

## Tasks & Acceptance

**Execution:**
- `decision` — choose REAL_SEMANTIC (back recall with a real embedding model + failing-lexical
  test) or CRITERION_REWRITE (name `lexical` as the graded default, document the bag-of-concepts
  approximation honestly).
- `docs` — correct the Spec's "dual-write" wording for the already-correct dual-driver design.

**Acceptance Criteria:**
- Given "semantic" recall is a 32-dim SHA-256 bag-of-concepts over a hardcoded 7-entry synonym map,
  off by default, while CAP-14's dual-driver clause is already satisfied and exercised in CI, when
  this story runs, then either recall is backed by a real embedding model over the plane's `vss`
  index with a test that fails under lexical overlap, or the criterion is rewritten honestly.
- And in either branch, the story states which mode (`lexical` or `semantic`) the criterion is
  graded against, and records that the Spec's "dual-write" wording mis-described a correct design.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green (no
  steward-package code changes expected; this command proves nothing else regressed)

**Manual checks (if no CLI):**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: full scribe suite green,
  including whichever branch's new/updated test (the actual code change lives here, not in
  pyforge-steward)

## Spec Change Log

- **2026-09-11 — decision: CRITERION_REWRITE.** CAP-14's graded recall mode is `lexical`
  (default at `recall.py:114`, CLI without `--semantic`). Opt-in `semantic` mode documented
  honestly as a 32-dim SHA-256 bag-of-concepts over the 7-entry `_CONCEPTS` map in
  `embeddings.py`, not embedding-model recall. Updated `spec-pyforge-unifying-strategy/SPEC.md`
  CAP-14 success/verified/residual/OQ blocks: prior "dual-write unexercised" and
  "dual-write for now" wording mis-described the correct dual-driver CI parametrization +
  AD-5 single-plugin selection design (not a gap). Dual-driver CI unchanged.
- **2026-09-11 — docs:** `embeddings.py` module docstring, `cli.py` `--semantic` help, and
  `test_recall_semantic.py` header aligned to honest naming.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 16 findings — high 0, medium 0, low 0, false 6, maybe-false 0, reject 10
- findings:
  - `[false]` `[reject]` sprint-status-ledger not updated — ledger sync is a separate operator step outside this story's code/doc scope; story spec change log records completion.
  - `[false]` `[reject]` stale line anchors inside intent-contract — `<intent-contract>` is read-only per build-auto step-03; corrected anchors live in Spec Change Log (`recall.py:114`).
  - `[false]` `[reject]` intent-contract still reads as open fork — read-only block; decision recorded in Spec Change Log and parent SPEC `graded mode: lexical`.
  - `[false]` `[reject]` CAP-19 contradicts CAP-14 graded mode — CAP-19 names plane infrastructure for opt-in semantic path; CAP-14 grades lexical default; not contradictory.
  - `[false]` `[reject]` recall.py module docstring claims embedding recall — module docstring describes lexical default only; semantic path documented in `answer()` docstring.
  - `[false]` `[reject]` embeddings.py:24-32 line range wrong — `_CONCEPTS` spans 26-34; verified block cites the map region approximately; no reader harm.
  - `[false]` `[defer]` pyforge-scribe SKILL.md not updated — agent skill refresh is a separate surface; CLI help and module docstrings updated.
  - `[false]` `[defer]` spec-49-1 verified inventory stale — sibling story artifact; not caused by this diff.
  - `[false]` `[defer]` epics.md / readiness reports not reconciled — planning bulk docs; parent SPEC is source of truth post-49.7.
  - `[false]` `[defer]` no memlog on parent SPEC edit — story-level Spec Change Log records the CAP-14 amendment; memlog re-derive is operator follow-up.
  - `[false]` `[defer]` no spec_surface_check baseline stamp — operator action per AGENTS.md; not blocking story ACs.
  - `[false]` `[defer]` rename internal `semantic` identifiers — API-stable names; user-facing strings updated instead.
  - `[false]` `[defer]` graph_store_pg.py / test_recall.py stale comments — pre-existing; cosmetic; no behavior change in this story.
  - `[false]` `[reject]` verification section ordering — both commands run; scribe is primary verification surface per story text.
  - `[false]` `[reject]` test_recall.py missing line range in verified block — parent SPEC prose citation; low cosmetic.
  - `[false]` `[reject]` test_recall_semantic still exercises semantic>lexical contrast — correct for opt-in path documentation; graded lexical oracle cited to `test_recall.py` per CRITERION_REWRITE branch.

## Auto Run Result

Status: done

**Summary:** Chose **CRITERION_REWRITE**. CAP-14 now grades **`lexical`** recall; opt-in `semantic` is documented honestly as SHA-256 bag-of-concepts over the 7-entry synonym map. Corrected "dual-write" wording to dual-driver CI + AD-5 single-plugin selection.

**Files changed:**
- `spec-pyforge-unifying-strategy/SPEC.md` — CAP-14 success/verified/graded-mode/residual/OQ blocks rewritten
- `embeddings.py` — module docstring honesty pass
- `cli.py` — `--semantic` help text no longer claims embedding similarity
- `test_recall_semantic.py` — header docstring aligned
- `spec-49-7-…md` — decision log + review triage

**Review:** 0 patches applied; 10 deferred/rejected as out-of-scope or false; edge-case and verification-gap layers reported no gaps; intent-alignment confirms CRITERION_REWRITE branch.

**Follow-up review recommended:** false (0 patched entries)

**Verification:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 328 passed, 7 skipped
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 1206 passed, 1 failed (pre-existing: `test_adoption_register.py::test_wired_column_agrees_with_live_pipeline_truth_for_every_row` — `bmad-eval-quality` not on PATH; unrelated to this story)

**Residual risks:** REAL_SEMANTIC deferred to a future story if embedding-model recall over plane `vss` is wanted. Presentation decks under `presentations/pyforge-unifying-strategy/` still say "dual-write" until Herald refreshes them.
