---
title: 'The standard has one home and the deck spec points to it'
type: 'docs'
created: '2026-09-13'
status: 'done'
baseline_revision: e4eec92bd9
review_loop_iteration: 0
followup_review_recommended: false
context: ['spec-deck-family-currency/SPEC.md', 'spec-deck-family-currency/infographic-standard.md']
warnings: []
deferred: []
declared_low_risk: true
verdict_mode: advisory
---

<intent-contract>

## Intent

**Problem:** The infographic standard (six-act arc, full-depth section set, inline-diagram floor,
90 KB+ class, source-cited facts) existed only as operator rulings in auto-memory and as three
exemplar files. `docs/specs/presentation-deck.md` named "the warden family" as the sole form
exemplar and its verify checklist was entirely run-shaped — no floor was written anywhere a
deck author would read.

**Approach:** The standard's single home is the Spec companion
`spec-deck-family-currency/infographic-standard.md` (CAP-1). This story only points at it: the
deck spec's editing-surfaces paragraph names the home, the two references (Unifying Strategy =
structure/acts/length, Warden = density/visual form) and the floors; the "How to use this spec"
checklist gains a poster step (floors + full-page PNG review) beside the existing `deck-qa`
step; `presentations/README.md` gains a pointer line. No second copy of the floors is written.

## Boundaries & Constraints

**Always:**
- `infographic-standard.md` is the only place the floors are defined; every other surface links.
- The legacy `docs/specs/` tier gains a pointer only — never a second standard.
- `presentation-deck.md` keeps its existing `deck-qa` step unchanged; the poster step is added
  beside it because `deck-qa` needs `dist/` and does not see the standalone poster.

**Never:**
- Never restate the floors with different numbers anywhere; never move the standard into
  `docs/specs/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Reader opens the deck spec | `docs/specs/presentation-deck.md` § Artifact dependency tree | reaches `infographic-standard.md` in one hop; sees both references and the floors | — |
| Reader follows the verify checklist | § How to use this spec, step 5 | the poster step names the floors and the PNG review | — |
| Reader lands in `presentations/` | `presentations/README.md` | pointer to the standard | — |
| Floors grep | `grep -rn "≥ 18 sections"` | matches the standard plus link-carrying pointers only, no divergent copy | — |

</intent-contract>

## Tasks & Acceptance

**Execution:** hand-implemented 2026-09-13 in the Dream/Spec/Epic PR (`herald/deck-family-currency`),
low-risk docs pointers per `bmad-build`'s own skip rule for mechanical edits.

**Acceptance Criteria:** `presentation-deck.md:245` names the home, both references and the floors;
`presentation-deck.md:74-78` adds the poster step; `presentations/README.md` carries the pointer;
no second definition of the floors exists outside `infographic-standard.md`.

## Auto Run Result

**Summary:** Repointed `docs/specs/presentation-deck.md` (§ Artifact dependency tree paragraph; verify
step 5 poster sub-step) and `presentations/README.md` at `infographic-standard.md`. No code touched.

**Verification:** `grep -n infographic-standard.md docs/specs/presentation-deck.md presentations/README.md`
→ three hits (lines 78, 245; README line 15). `spec-surface-check` reconciles the governed
`presentation-deck.md` change through `spec-deck-family-currency/.memlog.md` (event appended same date).
