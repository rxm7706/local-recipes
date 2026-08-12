---
id: SPEC-marshal-land-merge-subject
owner-dream: docs/dreams/marshal-land-merge-subject.md
companions: []
sources: ['docs/dreams/marshal-land-merge-subject.md']
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# marshal land renders a detectable merge subject

## Why

**A pain to solve.** `core.promotion.marshal_native_merged_keys` classifies merge subjects as Marshal-driven via two patterns: `deploy land-story`'s templated form and bmad-loop's own native form. `marshal land` is equally Marshal-driven but merges through `forge.merge_pr` → `gh pr merge`, which lets GitHub auto-generate the subject — a shape byte-identical to a human's plain PR merge. Discovered 2026-08-12 during pyforge-marshal Story 5.9's review pass 2: of the keys `merged_story_keys` finds outside the templated/native patterns, the large majority are `marshal land` landings, not genuine `bmad-quick-dev` sessions. Every consumer of this classification — fleet-picture, `marshal status`, `dashboard-drift-check`, and Story 5.9's new `reconcile-completions` — currently mislabels them as not-loop-native/quick-dev. The fix is small and low-risk (`gh pr merge` already supports `-t/--subject` for every strategy), but not urgent — nothing currently in flight depends on it.

## Capabilities

- **CAP-1**
  - **intent:** `marshal land` renders the same templated merge subject `deploy land-story` already does (`identity.render_merge_subject(story_key, template)`, AD-24) and applies it to the GitHub merge, instead of leaving GitHub to auto-generate one.
  - **success:** `marshal_native_merged_keys(subjects, template, project_slug)`, given a real subject string from a `marshal land`-driven merge, classifies it as native — the same outcome it already produces for a `deploy land-story` merge.

## Constraints

- `gh pr merge` supports `-t/--subject text` for all three strategies (`--merge`/`--squash`/`--rebase`) — confirmed via `gh pr merge --help`. `ForgePort.merge_pr`'s adapter (`adapters/forge_gh.py`) passes the subject through to the CLI invocation; the port method itself gains an optional `subject: ForgeRef | None` parameter, typed the same way its existing `ForgeRef` parameters are (AD-34's egress-registry-completeness pattern) — never a second, separate PR-title-edit API call before the merge.
- Purely additive: no change to `marshal land`'s default `landing_merge_strategy`, its existing gates, or any other step of `run_land` — only the merge commit's subject line changes.

## Non-goals

- Does not retroactively relabel already-`done` ledger rows that were misclassified as `not-loop-native` before this fix ships — corrects classification for merges going forward only.
- Does not touch `deploy land-story` (already correct), `bmad-quick-dev`, or Story 5.9's `reconcile-completions` code — 5.9 already reads `marshal_native_merged_keys` as-is, so fixing the classifier's input here sharpens 5.9's downstream label precision with zero change to 5.9 itself.

## Success signal

- A `marshal land` landing's merge commit subject parses successfully via `core.identity.parse_merge_subject` using the same templated form `deploy land-story` produces, and `marshal_native_merged_keys` includes that key in its native set — verified against a real `marshal land` invocation, not a synthetic subject string.

## Assumptions

- The port-level fix (an optional `subject` parameter on `ForgePort.merge_pr`, threaded through to `gh pr merge -t`) is preferred over having `run_land` set the PR's title via a separate `gh pr edit` call before merging, since the former is one atomic write matching how `deploy land-story`'s own single `vcs.merge_branch(..., subject=...)` call already works, while the latter is two round-trips with a race window between them.
