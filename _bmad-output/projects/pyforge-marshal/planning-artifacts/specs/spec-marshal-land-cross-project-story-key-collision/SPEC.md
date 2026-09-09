---
id: SPEC-marshal-land-cross-project-story-key-collision
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/marshal-land-cross-project-story-key-collision.md
companions: []
sources:
  - docs/dreams/marshal-land-cross-project-story-key-collision.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source document is for traceability only.

# A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another

## Why

Reproduced live 2026-08-15: `marshal land pyforge-mason` reported story `4.2`
(`4-2-manifest-discovery`) as `already_landed`/`merged: true` when
`origin/main` demonstrably does not contain that commit. Traced to
`core/promotion.py::extract_story_key_from_github_merge_subject`
(`core/promotion.py:146`), one of `merged_story_keys`'s three merge-subject
patterns: it extracts a `StoryKey` from any GitHub PR-merge branch's final
path segment with **no check that the branch belongs to the `project_slug`
being queried** — unlike its sibling
`extract_story_key_from_bmadloop_merge_subject`, which already carries
exactly this scoping, for the identical reason (this repo hosts every BMAD
project's history in one shared git). Live proof: PR #274's branch
`marshal/4-2-teardown-reachability-spec-recovery` (a **marshal** story) was
misattributed as mason's own `4.2` purely by numeric coincidence. This same
function backs `marshal land`'s and `marshal deploy batch-pr`'s
already-landed short-circuit and `run_reconcile_completions`'s "confirmed"
classification, so the false positive can silently misfire for any project
whenever another project's branch history carries a numerically-matching
`<epic>-<story>` segment — routine across 8 concurrently-active projects
sharing one repo. This is a known, previously-deferred gap
(`implementation-artifacts/deferred-work.md`, 2026-08-10, review passes 2+4)
measured then against `main`'s 2,353 subjects with the same shape of
result — `cli/status.py` already hedges a present key as evidence, never
proof, because of it — but this Spec is the first concrete, consequential
failure (`marshal land` reporting false success) the gap has actually
caused.

## Capabilities

- **CAP-1 — the GitHub PR-merge pattern is scoped to `project_slug`.**
  - **intent:** `extract_story_key_from_github_merge_subject`'s branch-segment
    match only returns a `StoryKey` when the branch actually belongs to the
    project being queried, the same way the bmad-loop pattern already scopes
    itself — a same-numbered story from a different project's branch history
    can never be mistaken for this project's own.
  - **success:** `merged_story_keys(subjects_from_main, template, 'mason')`
    no longer returns `4.2` for PR #274's real subject (`Merge pull request
    #274 from rxm7706/marshal/4-2-teardown-reachability-spec-recovery`) — a
    regression test pins this exact real subject against
    `project_slug='mason'` and asserts no key is returned, and against
    `project_slug='marshal'` and asserts `StoryKey(4, 2)` is still returned.

- **CAP-2 — both real branch-naming shapes still resolve correctly for a
  project's own stories.**
  - **intent:** The existing, correct single-project extraction keeps
    working for both real branch-naming conventions in this repo's history:
    `<slug>/<epic>-<seq>-<desc>` (e.g. `marshal/4-2-teardown-...`) and
    `land/<slug>-<epic>-<seq>-<desc>` (e.g.
    `land/mason-4-3-mason-environment-lock`).
  - **success:** Every existing `test_promotion.py` case for
    `extract_story_key_from_github_merge_subject` still passes unmodified,
    plus new tests covering both shapes scoped correctly against their own
    `project_slug`.

## Constraints

- **Pure-function discipline (AD-4) holds** — no I/O, no subprocess, no
  `pathlib` methods added to `core/promotion.py`; the fix operates only on
  the subject text and the `project_slug` already passed in.
- **Must not weaken `extract_story_key_from_bmadloop_merge_subject`'s
  existing `project_slug` scoping** — this Spec brings the GitHub pattern up
  to the same standard; it never loosens the bmad-loop pattern.
- **Must support both observed branch shapes**, not just one — scoping by a
  bare prefix-equals-`project_slug` check would silently break the
  `land/<slug>-...` shape, which is the more common landing-branch
  convention in this repo's own history.

## Non-goals

- Not adding a plausibility bound on raw epic/story numbers in
  `core.identity.normalize` (the separately-observed `2026.8` bogus-key
  symptom, from PR #441's date-stamped dependency-bump branch
  `2026-08-11-Pixi-v0.76.2`) — a different function with its own contract;
  scoping the GitHub pattern to `project_slug` already prevents this Spec's
  cross-project false positive without touching `normalize`.
- Not auditing every other caller of `merged_story_keys` (e.g.
  `run_reconcile_completions`/`_reconcile_open_intents`) for downstream
  consequences of past false positives — scoped to the extraction bug
  itself, not a forensic audit of everything it may have already touched.
- Not landing mason's actual `4.2` wave as part of this fix — that is normal
  fleet operation once `marshal land` can be trusted again, not this Spec's
  concern.

## Success signal

`pixi run --frozen -e pyforge-marshal pyforge-marshal-test` is fully green,
including new regression tests pinning PR #274's and PR #441's real
subjects. A live re-run of `marshal land pyforge-mason` against the current,
still-unlanded `4.2` wave reports a fresh landing, not `already_landed` —
the fix's own acceptance evidence against the exact real bug that motivated
it.

## Assumptions

- **`status:` ADDED 2026-09-09 — `(absent)` → `shipped`.** The key was missing entirely; doctor's
  chain-completeness reports 2/2 CAPs uncovered only because no story key names this Spec.
- CAP-1/CAP-2 are live and fixture-pinned. Fixed by direct commit `d7fd62707b` *("marshal: scope
  the GitHub PR-merge story-key pattern to `project_slug`")* and then **absorbed into Story 20.8's
  shared grammar**, where the scoping lives as `_branch_belongs_to_project`
  (`pyforge-core` `landing_evidence.py:161`, applied at `:227`). The regression is pinned on PR
  #274's real subject against **both** slugs (`pyforge-core`
  `tests/unit/test_landing_evidence.py:72`; `pyforge-marshal` `tests/unit/test_promotion.py:42-95`).
- **Decomposition note, checked before flipping:** no `epics.md` story ever owned this fix — it
  landed outside the story ledger and was back-filled by Story 20.8 (`done`). The work is therefore
  decomposed-and-done through 20.8, which is why the value is `shipped`, not `ready`.
