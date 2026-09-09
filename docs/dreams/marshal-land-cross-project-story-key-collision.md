---
title: A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another
type: dream
owner: marshal
status: realized
---

# A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another

## The Dream

`marshal land`/`marshal deploy batch-pr`'s "already landed" short-circuit
(`core/promotion.py::merged_story_keys`) confirms only that a project's OWN
story actually merged into `main` — never a same-numbered story from a
completely different project that happens to share this one repo's history.
Today it does not: `extract_story_key_from_github_merge_subject`, the
second of the function's three merge-subject patterns, extracts a
`StoryKey` from ANY GitHub PR-merge branch's final path segment with no
check that the branch actually belongs to the `project_slug` being
queried — the exact cross-project collision protection its own sibling
pattern (`extract_story_key_from_bmadloop_merge_subject`) already carries,
and whose docstring names the identical risk this repo's shared history
creates.

## What is real

Confirmed live, 2026-08-15: `marshal land pyforge-mason` reported story
`4.2` (`4-2-manifest-discovery`) as `already_landed: true` / `merged: true`
immediately after wave discovery — even though `origin/main` demonstrably
does not contain that commit (`git merge-base --is-ancestor a723618553
main` → not an ancestor; `git log main --grep="4-2\|manifest-discovery"`
finds nothing). The branch `loop/pyforge-mason` still exists, un-retired,
holding the real un-promoted merge commit — so the false positive was
caught before anything was lost, but `marshal land` reported success on a
wave that never landed.

Reproduced directly against `promotion.merged_story_keys` with
`project_slug='mason'` and real `main` history (2,898 commit subjects): it
returned `4.2` as an "already landed" mason key, plus several other
clearly-bogus mason keys (`4.5`–`4.10`, `5.2`–`5.6`, `6.1`–`6.5` — several
of which don't correspond to any real mason story in mason's own
`epics.md`) and one nonsensical `2026.8`.

Traced each to its exact source commit:

- `4.2` comes from **PR #274**, branch
  `marshal/4-2-teardown-reachability-spec-recovery` — a **marshal**
  story, unrelated to mason. `extract_story_key_from_github_merge_subject`
  (`core/promotion.py:146`) matches `_GITHUB_MERGE_SUBJECT_RE`, takes the
  branch's final `/`-separated path segment
  (`4-2-teardown-reachability-spec-recovery`), and hands it straight to
  `normalize()` with **no check at all** that the branch's leading
  `marshal/` segment matches the `project_slug` being queried — that
  segment is simply discarded.
- `2026.8` comes from **PR #441**, branch `2026-08-11-Pixi-v0.76.2` — a
  routine dependency-bump branch with no story association whatsoever.
  Same code path: `normalize()` accepts `2026-08` as a syntactically-valid
  `<epic>-<story>` pair with no plausibility bound.
- `_classify_merge_subject` (`core/promotion.py:173`) documents, in its
  own docstring, that `project_slug` "scopes the bmad-loop pattern
  **only**" — the GitHub PR-merge pattern was never given the same
  scoping its sibling pattern's own docstring says this shared-history
  repo requires.

`merged_story_keys` backs both `marshal land`'s and `marshal deploy
batch-pr`'s already-landed short-circuit, AND
`run_reconcile_completions`/`_reconcile_open_intents`'s "confirmed"
classification — so the same false positive can silently short-circuit
landing (and mis-confirm open intents) for ANY project whenever another
project's branch history carries a numerically-matching `<epic>-<story>`
segment, which is routine across 8 concurrently-active projects sharing
one repo.

**This is a known, previously-deferred gap, not a fresh discovery** —
`implementation-artifacts/deferred-work.md` (Tier-3) already carries two
entries against this exact function (2026-08-10, review passes 2 and 4,
Blind Hunter + Edge Case Hunter independently): it names the missing
`project_slug` scoping, measures it live against `main`'s then-2,353
commit subjects (mason/doctor/scribe each returning ~30 keys, "most of
them another station's"), and explicitly defers a full fix as "a dedicated
story should extend the one owner to read both shapes." `cli/status.py`'s
own `_merged_keys_for_slug` already treats a present key as "STRONGER
evidence, not proof" specifically because of this known contamination —
but `cli/land.py`'s already-landed short-circuit does NOT hedge at all,
treating `all(key in already_landed_keys ...)` as definitive. This Dream
is the first time the gap has produced a concrete, consequential failure
(a real false "already landed") rather than staying a bounded, theoretical
risk — and scopes a fix narrower than the deferred entries' own "read both
shapes" framing: only closing the cross-project false-positive hole in the
EXISTING recognized shape, not adding new shape recognition (that larger
work stays exactly as deferred).

## What it looks like when real

- `extract_story_key_from_github_merge_subject`'s branch-segment match is
  scoped to `project_slug`, the same way
  `extract_story_key_from_bmadloop_merge_subject` already is — a branch
  must actually belong to the project being queried (its own
  project-prefix convention, e.g. `marshal/…`, `land/mason-…`) before its
  trailing `<epic>-<story>` segment is trusted as that project's own key.
- A syntactically-valid-looking `<epic>-<story>` pair from an unrelated
  branch (a date stamp, a version bump) no longer masquerades as a real
  story key for ANY project.
- `marshal land pyforge-mason` reports `already_landed` only for waves
  genuinely reachable from `main` under mason's own key space — re-run
  live against the current mason wave (`4.2`) as the fix's own acceptance
  evidence: it must report a fresh landing, not a no-op.
- `deploy batch-pr`'s identical short-circuit and
  `run_reconcile_completions`'s "confirmed" classification inherit the fix
  automatically, since both call the same `merged_story_keys`.

## Constraints

- Must not regress the EXISTING single-project story-key extraction this
  pattern already gets right for the common case (a project's own
  `land/<slug>-<epic>-<seq>...` / `<slug>/<epic>-<seq>...` branches) —
  every currently-passing `test_promotion.py` case for
  `extract_story_key_from_github_merge_subject` must still pass.
- The fix must work for BOTH observed real branch-naming conventions in
  this repo's own history: `<slug>/<epic>-<seq>-<desc>` (e.g.
  `marshal/4-2-teardown-...`) and `land/<slug>-<epic>-<seq>-<desc>` (e.g.
  `land/mason-4-3-mason-environment-lock`) — scoping by a bare
  prefix-equals-`project_slug` check would silently break the second,
  more common landing-branch shape.
- Pure-function discipline (AD-4) holds: no I/O, no subprocess, no
  `pathlib` methods added to `core/promotion.py`.

## Non-goals

- Not adding a plausibility bound on raw epic/story numbers (the
  `2026.8` symptom) — that is a `core.identity.normalize` concern, a
  different function with its own contract; scoping the GitHub pattern to
  `project_slug` already prevents THIS bug's cross-project false positive
  without touching `normalize`.
- Not auditing every OTHER caller of `merged_story_keys` for downstream
  consequences of past false positives (e.g., whether
  `run_reconcile_completions` already mis-confirmed some open intent
  using a stale cross-project key) — scoped to the extraction bug itself,
  not a forensic audit of everything it may have already touched.
- Not landing mason's actual `4-2` wave — that is normal fleet operation
  once `marshal land` can be trusted again, not part of this fix.

## Kinships

[[pyforge-marshal]] (the station; `core/promotion.py` is its own core
module) · [[marshal-status-harness-run-id-poisoning]] (a sibling "trusted
a field that turned out to lie" bug, found the same day) ·
[[bmad-loop-liveness-footgun]] (same family).

## Realization log

- **2026-08-15** — Dream captured. Found live while attempting to land
  mason's story `4.2` per this repo's own "land proactively" convention —
  `marshal land` reported false success. Root-caused to source in
  `core/promotion.py`, reproduced directly against real `main` history
  (2,898 commit subjects, `project_slug='mason'`), and traced the two
  concrete false positives (`4.2` from PR #274/marshal, `2026.8` from PR
  #441/pixi-bump) to their exact originating commits. Not hotfixed per
  this repo's Dream-first policy for any `pyforge-marshal` code change;
  captured as its own Dream once the user asked directly to fix it
  properly rather than work around it.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  fixture-pinned.** Fixed by direct commit `d7fd62707b` ("marshal: scope the GitHub PR-merge
  story-key pattern to project_slug") and subsequently absorbed into Story 20.8's shared grammar,
  where the scoping now lives as `_branch_belongs_to_project`
  (`pyforge-core/.../landing_evidence.py:161`, applied at `:227`). CAP-1's regression is pinned on
  the real PR #274 subject against BOTH slugs (`pyforge-core/tests/unit/test_landing_evidence.py:72`;
  `pyforge-marshal/tests/unit/test_promotion.py:42-95`). The Spec, which carried **no `status:` line
  at all**, is set to `shipped`.
  **Chain note, recorded rather than hidden:** no `epics.md` story ever owned this fix — it landed
  outside the story ledger and was back-filled by 20.8, which is why doctor's chain-completeness
  reports 2/2 CAPs uncovered. This Dream's own text says it was "NOT hotfixed per this repo's
  Dream-first policy"; it was, later. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
