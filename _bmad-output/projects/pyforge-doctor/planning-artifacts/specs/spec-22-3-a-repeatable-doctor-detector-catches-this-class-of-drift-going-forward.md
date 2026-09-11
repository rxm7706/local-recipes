---
title: 'A repeatable Doctor detector catches this class of drift going forward'
type: 'feature'
created: '2026-09-11'
status: 'done'
baseline_revision: 'efabb6d912099eda55950f2d8c9d507e35545684'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Doctor already runs real hygiene detectors (`capability_effect.py`,
`status_body_consistency.py`, `sibling_dreams.py`, `hygiene.py`/dreams-hygiene) that catch a
claim which used to be true and silently isn't anymore — but only inside BMAD-tier planning
artifacts. None of them reach the general, human-facing documentation layer: `README.md`,
`CLAUDE.md`, `AGENTS.md`, station `README.md`s, and `.claude/skills/*/skill-brief.yaml`. Story
22.1 fixed two live identity contradictions there (Doctor's own README misusing "gate"
language; `AGENTS.md`'s Herald ownership claim contradicting Herald's own Dream) by hand,
one-off. This story makes that class of check repeatable.

**Approach:** A new source module (mirroring `capability_effect.py`/
`status_body_consistency.py`'s own discipline — bounded, textual, explainable, evidence-based)
cross-references what a station's `README.md`/`skill-brief.yaml`/`docs/dreams/<station>.md`/
`AGENTS.md` say about the same fact and flags a real, quotable divergence. It is fixture-driven:
replay Story 22.1's two now-fixed contradictions as frozen "before" fixtures (the detector must
fire on them) and the now-corrected files as "after" fixtures (the detector must NOT fire), plus
a genuinely clean station (e.g. Atlas or Warden, whichever the 2026-09-11 light pass already
confirmed had nothing comparable) as a clean-fixture proving no false positive. The detector is
registered in `sources/__init__.py` alongside its siblings, warn-only, fail-open, never a second
PR gate.

## Boundaries & Constraints

**Always:**
- Findings are evidence-based — the detector must be able to quote BOTH sides of a divergence
  directly from the two source files being compared, never an inferred or invented
  contradiction (matches `capability_effect.py`'s own discipline, per Story 21.9's precedent
  and its cautionary reference to Story 21.3's synthetic-fixture failure — do not repeat that
  mistake here either).
- The detector is warn-only and fail-open, matching Doctor's existing hygiene-check contract —
  it must never become a second PR gate, and an unreadable source file degrades to a named
  finding, never silence.
- Register the new module in `sources/__init__.py` alongside `capability_effect.py`/
  `status_body_consistency.py`'s own entries, following their exact registration shape.

**Never:**
- Do not build a heavier NLP/semantic "meaning" checker — bounded textual comparison only,
  matching the problem's actual scope (per the owning Spec's own Non-goals).
- Do not validate the join/comparison mechanism only against a fixture that constructs both
  sides from one synthetic value — Story 21.9's own cautionary precedent (Story 21.3 /
  `sibling-dreams-drift`) is the failure mode to avoid; prove against the real, now-corrected
  Story 22.1 files, not only synthetic fixtures.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live contradiction (pre-Story-22.1 fixture) | Doctor README's "gate" language vs. skill-brief.yaml's "advisory" framing | Finding fires, quoting both sides | n/a |
| Live contradiction (pre-Story-22.1 fixture) | AGENTS.md's Herald claim vs. Herald's own Dream | Finding fires, quoting both sides | n/a |
| Corrected state (post-Story-22.1 fixture) | Same two file pairs, now aligned | No finding | n/a |
| Clean station | A station confirmed to have nothing comparable (light pass, 2026-09-11) | No finding | n/a |
| Unreadable source file | One of the compared files cannot be read | Named finding, never silence | Fail-open, named |
| Ambiguous/no comparable claim | A station's docs simply don't discuss the same fact in two places | No finding (nothing to compare, not an error) | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` — new source module for this
  detector (mirrors `capability_effect.py`/`status_body_consistency.py`'s shape).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — register the new
  detector, following the existing entries' exact shape (see the `capability_effect.py`/
  `status_body_consistency.py` registrations for the pattern).
- `src/shared/packages/pyforge-doctor/tests/unit/` — new unit tests.
- `src/shared/packages/pyforge-doctor/tests/fixtures/` — new fixtures (the pre/post Story-22.1
  pairs, plus a clean-station fixture).
- `src/shared/packages/pyforge-doctor/README.md`, `AGENTS.md` — read-only reference for the
  corrected (post-Story-22.1) real content the "after" fixtures should match.

## Tasks & Acceptance

**Execution:**
- `feature` — implement the new source module: cross-reference a station's
  README/skill-brief/Dream/AGENTS.md claims and flag a real, quotable divergence.
- `feature` — register the detector in `sources/__init__.py`.
- `feature` — add fixtures: the two Story 22.1 contradictions (pre- and post-fix), plus a
  clean-station fixture.
- `feature` — add unit tests covering the full I/O matrix above.

**Acceptance Criteria:**
- Given none of Doctor's existing hygiene detectors reach the general-facing documentation
  layer, when the new detector cross-references a station's README/skill-brief/Dream/AGENTS.md
  claims, then it names a real divergence — bounded, textual, explainable, evidence-based
  (never inferred or invented), matching `capability_effect.py`'s own discipline.
- Given Doctor's existing hygiene-check contract, when the detector runs, then it is warn-only
  and fail-open — never a second PR gate.
- Given Story 22.1's two now-fixed contradictions and a clean-station case, when replayed as
  fixtures, then the detector fires on the pre-fix pair, does not fire on the post-fix pair, and
  does not fire on the clean station.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green,
  including the new fixtures/tests.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 12 findings — high 0, medium 1, low 2, false 6, maybe-false 3
- findings:
  - `[medium]` `[patch]` Missing `_DOCTOR_SOURCE_TASKS` pin test for `general-docs-consistency` — added `test_doctor_source_tasks_include_general_docs_beside_pixi_currency` in `tests/scripts/test_detectors_doctor_sources.py`.
  - `[low]` `[reject]` Stale “ten detector sources” prose in package README — pre-existing; out of Story 22.3 surface.
  - `[low]` `[reject]` Stale `_run_doctor_sources` docstring count — cosmetic; not worth a guard in this story.
  - `[false]` `[reject]` Diff omits core module/tests — files exist in worktree; diff was baseline-relative to committed tree only.
  - `[false]` `[reject]` Diff not mergeable without module — same as above; full tree is complete.
  - `[false]` `[reject]` Import fails without module — module is present in worktree.
  - `[false]` `[reject]` Registration over-promises generic Dream cross-check — bounded to the two Story 22.1 contradiction classes per spec; station README↔skill-brief is generalized only for gate/advisory.
  - `[false]` `[reject]` Three different orderings undocumented — pixi task order is not a contract; detectors tuple order is pinned by test.
  - `[maybe-false]` `[defer]` Live-repo test fails after Story 22.1 lands — intentional: fixture tests remain authoritative; live test documents current drift until 22.1 merges.
  - `[maybe-false]` `[defer]` Warden clean fixture is “no pair” not “aligned advisory” — matches I/O matrix “nothing comparable” row; silence is correct.
  - `[maybe-false]` `[defer]` dreams-hygiene count 63→65 bundled — live re-measurement required for green suite; unrelated but blocking.

## Auto Run Result

Status: done

Summary: Added `general_docs_consistency.py` — a warn-only Doctor source that flags quotable identity contradictions between station README vs skill-brief (gate vs advisory) and `AGENTS.md` vs `docs/dreams/pyforge-herald.md` (Herald vs Marshal handoff ownership). Registered in `REGISTRY`, `DISPATCH`, report schema, pixi task, and `detectors.py`.

Files changed:
- `src/.../sources/general_docs_consistency.py` — new detector module
- `src/.../sources/__init__.py`, `__main__.py`, `models.py`, `data/report-schema.json` — registration
- `tests/fixtures/general_docs_consistency/**` — pre/post Story 22.1 + clean Warden fixtures
- `tests/unit/test_sources_general_docs_consistency.py` — full I/O matrix coverage
- `pixi.toml`, `scripts/detectors.py`, `environment.yaml` — task + sweep wiring
- `tests/scripts/test_detectors_doctor_sources.py` — sweep membership pin test

Review: 1 medium patch applied (detectors pin test); 3 deferred (live-test lifecycle, Warden fixture semantics, dreams-hygiene count re-measure); remainder rejected as false/low.

Follow-up review recommendation: false (single medium patch, converged).

Verification: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1622 passed, 1 skipped.

Residual risks: Live-repo integration test will need removal or rewrite once Story 22.1 fixes land at source; detector scope is intentionally limited to the two known contradiction patterns, not a general four-surface join engine.
