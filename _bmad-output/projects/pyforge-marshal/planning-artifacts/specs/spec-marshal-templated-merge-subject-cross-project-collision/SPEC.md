---
id: SPEC-marshal-templated-merge-subject-cross-project-collision
status: shipped
updated: "2026-09-11"
owner-dream: docs/dreams/marshal-templated-merge-subject-cross-project-collision.md
covers-dreams:
  - docs/dreams/marshal-templated-merge-subject-cross-project-collision.md
companions: []
sources: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to
> build, test, and validate. The source Dream is for traceability — consult it only for
> narrative rationale this contract intentionally omits.

# The templated merge-subject shape never masquerades as a same-numbered story from another project

## Why

A pain to solve. `pyforge.core.landing_evidence.parse_templated_merge_subject` — the AD-24
templated `"Merge {key} into main"` shape, tried FIRST in `classify_merge_subject`'s precedence
chain (`landing_evidence.py:332`) — is the one parser among its five siblings with no
`project_slug` parameter at all (`landing_evidence.py:199`). Its four siblings
(`parse_github_pr_merge_subject`, `parse_bmadloop_merge_subject`, `parse_recovery_commit_subject`,
`parse_story_direct_commit_subject`) all take and use `project_slug` for scoping. This is the
sibling gap the already-shipped fix
(`docs/dreams/marshal-land-cross-project-story-key-collision.md`, `_branch_belongs_to_project`
scoping on `parse_github_pr_merge_subject`, `landing_evidence.py:161`) deliberately left open —
that Dream's own Non-goals said "Not auditing every OTHER caller of `merged_story_keys`."
Confirmed live 2026-09-11: `merged_story_keys(subjects, 'Merge {key} into main',
'pyforge-doctor')` against real `main` (5,629 commit subjects) returns 129 keys, a majority
attributable to other stations' epics (`22.11`/`22.12` from marshal itself; `23.x`/`28.x`/
`39.x`–`49.x` from entirely other stations). This produced 3 false "already merged" dispatch
verdicts and 1 orphaned dev session during doctor's Epic 22 dispatch (2026-09-11), all recovered
by hand. The contamination is permanent — the colliding commits are already on `main` — so every
future dispatch of a same-numbered story for any station recurs identically until fixed.

## Capabilities

- **CAP-1**
  - **intent:** A templated-form merge subject is trusted as `project_slug`'s own merged key
    only when corroborated by a project-scoped signal — never by the subject text alone, since
    the templated shape carries no station token by construction (AD-24).
  - **success:** `merged_story_keys(subjects, template, 'pyforge-doctor', known_keys=...)` against
    real `main` no longer returns `22.11`/`22.12` (marshal's own) or any other station's
    exclusive keys. Re-running the Dream's own live reproduction returns only keys doctor's
    `epics.md` actually contains. (Story 35.1.)
  - **verified:** `_classify_merge_subject`/`merged_story_keys`/`marshal_native_merged_keys` all
    gain an optional `known_keys` parameter (`core/promotion.py`), backward-compatible when
    omitted; `dispatch_supervisor/__main__.py::gather_dispatch_git_facts` (the exact function
    that produced 2026-09-11's false verdicts) wired to load the querying project's own tracked
    `sprint-status-ledger.yaml` and supply it. Re-running the Dream's own live reproduction: the
    templated-shape match count for a `pyforge-doctor` query drops from 79 to 30 keys, with
    `22.11`/`22.12`/`23.x`/`28.x`/`39.x`–`49.x` all excluded. Full `pyforge-marshal` test suite
    green (7,799 passed) including new regression tests reproducing the exact 2026-09-11 false
    positive; landed via `local-recipes` PR (Story 35.1). Residual: `cli/dispatch.py`'s wave/
    reconcile paths, `dispatch_land.py`, `cli/status.py`, `cli/land.py`, and
    `branch_story_merge_confirmed_by_grammar` remain unwired — named explicitly in the story, not
    silently left exposed.

## Constraints

- Must not regress the templated form's correct, intended use: a story genuinely landed BY
  `pyforge-marshal` itself (`deploy land-story`, which renders the template from policy for its
  own `project_slug`) must still classify as merged for that project.
- The templated subject carries no station token in its own text — the fix cannot rely on
  parsing the subject string alone, unlike the already-fixed GitHub PR-merge case, which had a
  branch name to scope against. It needs either an out-of-band scoping signal or a documented,
  deliberate narrowing of what the shape is trusted to prove.
- AD-4 pure-function discipline holds for `core/promotion.py` and `pyforge.core.landing_evidence`:
  no I/O, no subprocess, no `pathlib` methods added to the classifier itself — any new scoping
  signal must be computed by an existing impure caller (`cli/deploy.py`) and passed in as a
  parameter, not fetched by the pure function.

## Non-goals

- Re-litigating the already-shipped GitHub PR-merge fix (`parse_github_pr_merge_subject` /
  `_branch_belongs_to_project`) — that parser is untouched.
- Adding a plausibility bound on raw epic/story numbers — a `core.identity.normalize` concern,
  unrelated to this scoping gap.
- Auditing every historical false positive this parser may have already produced before the fix
  lands (e.g. a past `run_reconcile_completions` mis-confirmation) — scoped to closing the
  extraction bug itself, not a forensic audit of its past consequences.
- Re-dispatching or re-landing any of doctor's Epic 22 work — already recovered and landed by
  hand this session (`local-recipes` PRs #1251–#1254, #1256–#1257).

## Success signal

`merged_story_keys`/`classify_merge_subject`'s templated-form branch, for any `project_slug`,
returns only keys reachable via a corroborating project-scoped signal. Verified by re-running
the Dream's own live reproduction against current `main` and confirming the contamination list
(`22.11`, `22.12`, `23.x`, `28.x`, `39.x`–`49.x` for a doctor query) is gone, while a genuine
`pyforge-marshal`-driven `land-story` landing for marshal's own `project_slug` still classifies
correctly.
