---
title: The templated merge-subject shape never masquerades as a same-numbered story from another project
type: dream
owner: marshal
status: realized
---

# The templated merge-subject shape never masquerades as a same-numbered story from another project

## The Dream

`core/promotion.py::merged_story_keys`'s FIRST merge-subject shape in
precedence order — the AD-24 templated form (`merge_subject_template`,
default `"Merge {key} into main"`) via
`pyforge.core.landing_evidence.parse_templated_merge_subject` — extracts a
`StoryKeyRef` (`epic` + `seq` + `suffix`, nothing else) from a bare
prefix/suffix slice around `{key}`, with **no `project_slug` parameter at
all**. Every one of its four sibling parsers in the same precedence chain
(`parse_github_pr_merge_subject`, `parse_bmadloop_merge_subject`,
`parse_recovery_commit_subject`, `parse_story_direct_commit_subject`) takes
`project_slug` and scopes on it (branch prefix, `loop/<slug>` target,
station-name match); the templated parser is the one shape in the chain
that does not, and it is tried FIRST — so a station whose own historical
`main` history carries `"Merge 22.5 into main"`-shaped commits makes that
key falsely "already merged" for every OTHER station in the repo's shared
history that happens to mint the same epic.seq number, with zero
cross-project check anywhere in the path.

This is the sibling gap
[[marshal-land-cross-project-story-key-collision]] scoped itself away
from: that Dream (realized 2026-09-09) fixed ONLY the second parser in the
chain, `parse_github_pr_merge_subject`, via the now-shared
`_branch_belongs_to_project` helper. Its own Non-goals said "Not auditing
every OTHER caller of `merged_story_keys` for downstream consequences" —
the templated-form parser was never touched, and nothing in its
Realization log claims it was.

## What is real

Confirmed live, 2026-09-11, while dispatching `pyforge-doctor` Epic 22
(Stories 22.1–22.6) via `marshal factory dispatch --stories`. The dispatch
campaign supervisor reported `story_merged_on_main: True, verdict:
"completed"` for Stories 22.1, 22.2, and 22.4 within ~1 second of
dispatch, before their real `bmad-build-auto` sessions had done any
meaningful work (`changed_paths: []`). Root-caused to `pyforge-marshal`
having its OWN, unrelated Epic 22 (Stories 22.1 through at least 22.12),
landed earlier the same session via marshal's own native
`"Merge 22.1 into main"`-style merge subjects — those commits are
permanently present in `main`'s history now, so ANY future dispatch of a
same-numbered story for ANY OTHER station collides identically, forever.

Reproduced directly against the current `main` (5,629 commit subjects,
2026-09-11) with `project_slug='pyforge-doctor'`:

```python
promotion.merged_story_keys(subjects, 'Merge {key} into main', 'pyforge-doctor')
```

returns 129 keys, the large majority demonstrably NOT doctor's own —
`22.11`, `22.12` (real marshal-only story numbers doctor has never had),
plus entire runs of keys from other stations' epics that doctor's own
`epics.md` does not contain: `23.1`–`23.9`, `28.1`–`28.31`, `39.4`,
`40.1`–`40.2`, `41.1`–`41.4`, `42.1`–`42.5`, `43.1`–`43.6`, `46.10`,
`48.2`–`48.4`, `49.1`–`49.7`. The contamination is not a one-off — it is
the general-case behavior of this parser for every station in this
repo's shared history whenever two stations' epics happen to number the
same.

The false "already merged" verdict did not always kill the real work
underneath — 22.1/22.2/22.4's actual `bmad-build-auto` sessions kept
running independently and completed genuinely correct work despite the
supervisor's premature wrong report — but Story 22.3's session was
orphaned mid-task by the same false signal (process death with no clean
completion, real substantial work left uncommitted, recovered by hand).
The false verdict backs the SAME `merged_story_keys` call `marshal
land`'s already-landed short-circuit and `run_reconcile_completions`'s
"confirmed" classification use, so this is not scoped to dispatch alone —
any caller of `merged_story_keys` inherits it.

## What it looks like when real

- `parse_templated_merge_subject` (or its caller,
  `classify_merge_subject`'s templated-form branch) is scoped to
  `project_slug` the same way its four sibling parsers already are — a
  bare `"Merge {key} into main"` subject is trusted as THIS project's own
  key only when something in the commit (a station-prefixed branch name
  captured alongside the merge, or an equivalent scoping signal) confirms
  it belongs to `project_slug`.
- Re-running the reproduction above against the fixed code returns only
  keys doctor's own `epics.md` actually contains — no `22.11`/`22.12`, no
  `23.x`/`28.x`/`39.x`–`49.x` bleed.
- `marshal factory dispatch`/`factory drain` no longer reports a false
  `story_merged_on_main: True` for a story number another station has
  used, confirmed by re-dispatching a colliding number (e.g. doctor
  22.1–22.6 again, now against the fixed code, as a regression check —
  not to re-land anything already merged).

## Constraints

- Must not regress the templated form's correct, intended use: a story
  genuinely landed BY `pyforge-marshal` itself (`deploy land-story`,
  which renders the template from policy) for its OWN `project_slug` must
  still classify as merged.
- The templated merge subject, by construction (AD-24), carries no
  station token in its own text — `"Merge 22.5 into main"` looks
  identical regardless of which station produced it. The fix therefore
  cannot rely on parsing the subject text alone; it needs either an
  additional out-of-band scoping signal (e.g. restricting the scan to
  commits reachable only via the querying project's own tracked
  branches/worktree lineage) or a documented, deliberate narrowing of
  what the templated shape is trusted to prove — mirroring how
  `marshal_native_merged_keys`'s own docstring already reasons about what
  git alone can and cannot prove per shape.
- Pure-function discipline (AD-4) holds for `core/promotion.py` and
  `pyforge.core.landing_evidence`: no I/O, no subprocess, no `pathlib`
  methods added — if the fix needs a new scoping signal, the signal must
  be computed by an existing impure caller and passed in, not fetched by
  the pure classifier itself.

## Non-goals

- Not re-litigating the already-`realized` GitHub PR-merge fix
  ([[marshal-land-cross-project-story-key-collision]]) — that parser
  stays as-is.
- Not adding a plausibility bound on raw epic/story numbers — a
  `core.identity.normalize` concern, unrelated to this scoping gap.
- Not auditing every historical false-positive this parser may have
  already produced before this fix lands (e.g. whether a past
  `run_reconcile_completions` run silently mis-confirmed an open intent
  using a stale cross-project key) — scoped to closing the extraction
  bug itself, not a forensic audit of its past consequences.
- Not re-dispatching or re-landing any of doctor's Epic 22 work — all six
  stories (22.1–22.6) were independently recovered and landed by hand
  this session despite the false verdicts; that recovery is complete and
  is not part of this Dream's scope.

## Kinships

[[marshal-land-cross-project-story-key-collision]] (the sibling gap in
the same precedence chain, already fixed for a different parser) ·
[[pyforge-marshal]] (the station; `core/promotion.py` is its own core
module) · [[marshal-status-harness-run-id-poisoning]] (same family: "a
field trusted as proof that turned out not to be").

## Realization log

- **2026-09-11** — Dream captured. Found live during `pyforge-doctor`
  Epic 22 dispatch: three of four dispatched stories (22.1, 22.2, 22.4)
  received an instant, false "already merged" verdict from the fleet-
  drain campaign supervisor; a fourth (22.3) was actually orphaned by the
  same false signal mid-task. Root-caused to `parse_templated_merge_
  subject` lacking the `project_slug` scoping its four sibling parsers in
  the same `classify_merge_subject` precedence chain already carry.
  Reproduced directly against live `main` (5,629 subjects): doctor's own
  `project_slug` query returns 129 keys, a large majority attributable to
  other stations' epics (`22.11`/`22.12` from marshal; `23.x`/`28.x`/
  `39.x`–`49.x` from other stations entirely). All affected work (22.1,
  22.2, 22.3, 22.4) recovered and landed by hand this session
  (`local-recipes` PRs #1251–#1254); not hotfixed per this repo's
  Dream-first policy — captured as its own Dream for a real fix.
- **2026-09-11 (later, same session)** — Specced via `bmad-spec`
  (`spec-marshal-templated-merge-subject-cross-project-collision`, 1
  capability, self-validate PASS both passes), decomposed into Epic 35
  (Story 35.1), and fixed. `_classify_merge_subject`/`merged_story_keys`/
  `marshal_native_merged_keys` (`core/promotion.py`) gain an optional
  `known_keys` parameter — a templated-shape match is trusted only when
  its key is a member of the querying project's own tracked story
  catalog, corroboration the bare subject text cannot provide.
  `dispatch_supervisor/__main__.py::gather_dispatch_git_facts` (the exact
  function that produced this session's false verdicts) wired to load
  `known_keys` from the project's own `sprint-status-ledger.yaml` via a
  new `_load_known_story_keys` helper, failing closed (trusts nothing) on
  a missing or malformed ledger. Re-running this Dream's own live
  reproduction: the templated-shape match count for a `pyforge-doctor`
  query drops from 79 to 30, with `22.11`/`22.12`/`23.x`/`28.x`/`39.x`–
  `49.x` all excluded. Full `pyforge-marshal` test suite green (7,799
  passed), including new regression tests reproducing the exact
  2026-09-11 false positive against a fake filesystem/ledger. Named,
  explicit residual (not closed by this story, mirroring the sibling
  fix's own "not every caller" Non-goal): `cli/dispatch.py`'s wave/
  reconcile paths, `dispatch_land.py`, `cli/status.py`, `cli/land.py`, and
  `branch_story_merge_confirmed_by_grammar` remain unwired. Status:
  `dreamt` → `realized`; the Spec closes as `shipped`.
