---
title: 'A repeatable Doctor detector catches this class of drift going forward'
type: 'feature'
created: '2026-09-11'
status: 'backlog'
baseline_revision: 'a7752e7f91015b81d79a979bfca61a0dc8c8c8bb'
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
