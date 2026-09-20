---
title: '51.7: Landing evidence is intent-scoped, not just station-scoped'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: 'f819e046250a3bf9d8f41a803408e2e245d424ec'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 doctor Story 27.4 was minted on `doctor/27-4-mint`; when PR #1477 merged, `story_merged_on_main` read true for 27.4 and its first dispatch completed in one second and detached from a live session (story re-keyed to 27.5, 27.4 a reserved hole)

**Approach:** corroborate by content, not name — for the dispatch consumers (`dispatch_supervisor` `story_merged_on_main`, `dispatch_land`'s already-landed check, `dispatch_land_finalize`'s promotion) a station-branch match reached through a GitHub PR-merge subject counts as a landing only when the key's tracked story spec on `origin/main` reads `status: done` (a mint/fallout/fix PR merges it `ready`/`backlog`; a landing merges the promoted twin); the retrospective scanners are unchanged. Amended 2026-09-19 (night) after run `pyforge-marshal-20260919T202703469Z-0b70f736` returned blocked: name-based corroboration is unreachable through `promotion._classify_merge_subject` (a branch is only present when the GitHub PR-merge grammar already matched), and an exact-match branch grammar drops the only landing evidence for 83 of 347 marshal `done` rows (baseline worktree sweep). Saved attempt: `implementation-artifacts/story-51-7-attempted-change-2026-09-19.patch` — do not reuse its grammar tightening.

## Boundaries & Constraints

**Always:**
- on the PR #1477 fixture (`Merge pull request #1477 from rxm7706/doctor/27-4-mint`, spec-27-4 at `status: ready`) 27.4 is absent from `promotion.corroborated_merged_story_keys` and present in `merged_story_keys`; every `done` row of the eight tracked ledgers with real landing evidence still classifies through `merged_story_keys` (the CAP-247 regression fixture extended; the 347-key marshal sweep yields 0 regressions)
- a landing whose tracked spec is not `status: done` on `origin/main` (a hollow landing) is not corroborated — the same posture as CAP-252 / Story 51.9
- `landing_evidence.py` stays a pure parser (no filesystem, no git): `LandingEvidenceMatch` gains the branch-derived shape; the `spec_status_for(key)` reader is injected by marshal (`promotion.corroborated_merged_story_keys(subjects, template, slug, *, spec_status_for)`), never read inside core
- live history is never re-attributed; the MRS-GATE scope advisory for `pyforge-core/**` is expected and recorded, not suppressed

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-255`.
Surface: `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` (`LandingEvidenceMatch` exposes the branch-derived shape a GitHub PR-merge subject matched through — `dispatch/<slug>/<key>` vs a bare station branch; parsers otherwise unchanged, no grammar tightening), `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` (new `corroborated_merged_story_keys(subjects, template, slug, *, spec_status_for)` beside the unchanged `merged_story_keys`; a `spec_status_for` reader over `origin/main:<planning-artifacts>/specs/spec-<key>-*.md` frontmatter, banner-tolerant per CAP-256), the three dispatch consumers `dispatch_supervisor/__main__.py` (`story_merged_on_main`), `dispatch_land.py` (already-landed check), `dispatch_land_finalize/__main__.py`; tests in both packages incl. the PR #1477 fixture; `cli/status.py`, `cli/deploy.py`, `cli/land.py` and doctor's `sources/marshal.py` untouched, verified green (`pyforge-doctor-test`, `pyforge-core-test` — outside marshal's `verify_commands`, so run by hand before land).
Ledger key: `51-7-landing-evidence-is-intent-scoped-not-just-station-scoped`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-7-landing-evidence-is-intent-scoped-not-just-station-scoped.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.7 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 12 findings — high 4, medium 4, low 2, false 2, maybe-false 0
- findings:
  - `high` `patch` (Blind Hunter) `dispatch_land_finalize`'s promotion path still classified durability through the uncorroborated `merged_story_keys` (via `cli/deploy.py`'s `_scan_promotions`), so a mint/fallout/fix PR's station-branch merge could promote a Tier-3 spec that was never actually landed — the exact CAP-255 bug pattern, left open in this consumer. — Fixed: added a `_spec_status_for` closure in `dispatch_land_finalize/__main__.py` and filtered `scan.plan.to_promote` down to `promotion.corroborated_merged_story_keys` membership before calling `_execute_promotion_plan`, without touching `cli/deploy.py` (per the Binding's "untouched, verified green" declaration for that file).
  - `medium` `reject` (Blind Hunter) `read_spec_status`/`SPEC_STATUS_DONE` recognizes only the literal value `done`; a spec using `shipped` or other done-adjacent vocabulary would never corroborate. — Rejected: the fix is to widen this build's own status vocabulary decision (`SPEC_STATUS_DONE = "done"`, set in this story's `<intent-contract>`/Binding), i.e. to edit this build's spec — rejected unconditionally per the classify rule against fixes that edit the spec.
  - `medium` `patch` (Blind Hunter) `_reconcile_campaign_blocked` in `cli/dispatch.py` is a fourth call site still using the uncorroborated `merged_story_keys` to prune a campaign's `blocked` entries, so the same mint/fallout/fix-PR false positive could prematurely unblock a campaign row even though the three named dispatch consumers were fixed. — Fixed: wired the same `_spec_status_for`/`corroborated_merged_story_keys` pattern into `_reconcile_campaign_blocked`, scoped per-slug via a `_slug: str = slug` default-argument closure to avoid a late-binding bug across the enclosing `for slug, station_blocked in blocked.items()` loop.
  - `low` `reject` (Blind Hunter) `spec_text_at_ref` offers no way for a caller that already holds resolved commit/subject data to skip its own git read (no `commits` passthrough parameter, unlike some other dispatch helpers). — Rejected: no current caller needs this — the fix would add a new parameter and branch with no live use, which is more than a direct correction for a low-severity, not-encountered-in-practice gap.
  - `false` `reject` (Blind Hunter) concern that a local checkout's `main` could diverge from `origin/main`, making the corroboration read stale or wrong data. — Refuted: `spec_text_at_ref` reads only the explicit `ref="origin/main"`, never a local `main`; any resolution or fetch failure raises `VcsCommandError`, which `_spec_status_for` catches and turns into `None`, so corroboration fails closed on divergence or absence rather than trusting local state.
  - `medium` `patch` (Blind Hunter) none of the corroboration wiring sites had a direct test of the shared `spec_text_at_ref` primitive they all depend on; the existing `FakeVcs`/`HealCapableVcs` test doubles in `test_dispatch_landing.py` never exercise its success path. — Fixed: added `test_spec_text_at_ref_reads_the_resolved_path_at_the_given_ref`, `test_spec_text_at_ref_none_when_no_local_candidate_resolves`, and `test_spec_text_at_ref_none_when_ref_has_no_such_path` to `tests/unit/test_dispatch.py`.
  - `medium` `patch` (Blind Hunter) `_classify_merge_subject` and `corroborated_merged_story_keys` duplicated the same subject-classification logic (parse via `classify_merge_subject`, else fall back to the GitHub-merge-subject regex plus `classify_branch_name`) inline in two places — a future grammar change would need to be kept in sync by hand in both. — Fixed: extracted a shared `_classify_merge_subject_match` helper and rewrote both callers to use it.
  - `false` `reject` (Edge Case Hunter) concern that a case-varied status value (e.g. `status: Done`) would silently fail to corroborate a real landing. — Refuted: no tracked spec in the repo uses a non-lowercase `status:` value, and an unrecognized value returns `None` from `read_spec_status`, which `corroborated_merged_story_keys` treats as not-done — fails closed safely rather than mis-corroborating, and there is no live instance of the concern.
  - `low` `patch` (Edge Case Hunter) `_STATUS_VALUE_RE`'s independent `['"]?` groups at open and close accepted a mismatched quote pair (e.g. `status: 'done"`) as a valid `done` value. — Fixed: changed the regex to capture the opening quote and back-reference it at the close, so the open and close characters must match (or both be absent).
  - `high` `patch` (Edge Case Hunter) same root cause as the Blind Hunter finding above: `dispatch_land_finalize`'s promotion decision itself was still unguarded by corroboration, an edge case at the seam between the untouched `cli/deploy.py` scan and the new corroboration logic. — Same fix as the grouped Blind Hunter finding above.
  - `high` `patch` (Verification Gap) no test in the diff demonstrated that `dispatch_land_finalize`'s promotion path was actually gated by `corroborated_merged_story_keys`; the Binding names it as a consumer to fix but the pre-patch diff left its promotion call site unchanged. — Same fix as the grouped finding above; the full `pyforge-marshal-test` suite (8295 passed) re-run after the fix confirms no regression, though see Residual Risks for what remains unverified at the fixture level.
  - `high` `patch` (Intent Alignment) the verbatim intent names three consumers to fix (`dispatch_supervisor`, `dispatch_land`, `dispatch_land_finalize`) but the pre-patch diff's tests exercised only the first two surfaces — intent expectations and diff test coverage diverged at `dispatch_land_finalize`. — Same fix as the grouped finding above, closing the divergence.

## Auto Run Result

**Summary of implemented change:** `LandingEvidenceMatch` (pyforge-core) now exposes the branch-derived shape (`DISPATCH_BRANCH` vs `STATION_BRANCH`) a GitHub PR-merge subject matched through. `pyforge-marshal`'s `core/promotion.py` gained `corroborated_merged_story_keys(subjects, template, slug, *, spec_status_for, known_keys=None)`, which additionally requires a `STATION_BRANCH`-shaped match's tracked spec to read `status: done` on `origin/main` before counting it as a landing — closing the bug where a mint/fallout/fix PR's station-branch merge (e.g. PR #1477, `doctor/27-4-mint`) was indistinguishable from a real landing. All four consumers that made a landing/durability decision from an uncorroborated merged-key set were re-gated onto the corroborated set: `dispatch_supervisor/__main__.py` (`story_merged_on_main`), `dispatch_land.py` (already-landed check), and, added during this review pass, `dispatch_land_finalize/__main__.py` (promotion) and `cli/dispatch.py`'s `_reconcile_campaign_blocked`. `merged_story_keys` and its existing callers (`cli/deploy.py`'s other uses, `cli/status.py`, `cli/land.py`, doctor's `sources/marshal.py`) are unchanged, per the Binding.

**Files changed:**
- `src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py` — added `BranchDerivedShape`, threaded the branch-derived shape onto `LandingEvidenceMatch`.
- `src/shared/packages/pyforge-core/tests/unit/test_landing_evidence.py` — coverage for the new shape field.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` — added `corroborated_merged_story_keys`, `_requires_spec_corroboration`, `read_spec_status`, `SPEC_STATUS_DONE`; extracted `_classify_merge_subject_match` (review fix, dedup); fixed `_STATUS_VALUE_RE`'s quote-backreference (review fix).
- `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` — pure-function tests incl. the PR #1477 fixture and the 347-key marshal regression sweep.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — `spec_text_at_ref`, the shared impure primitive every consumer's `spec_status_for` closure calls.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — direct tests of `spec_text_at_ref` (review fix, closes a coverage gap).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — `story_merged_on_main` now calls `corroborated_merged_story_keys`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` — already-landed check now calls `corroborated_merged_story_keys`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` — promotion path re-gated onto `corroborated_merged_story_keys` (review fix).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — `_reconcile_campaign_blocked` re-gated onto `corroborated_merged_story_keys` (review fix).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-51-7-landing-evidence-is-intent-scoped-not-just-station-scoped.md` — this spec's own review triage log, auto run result, and frontmatter.

**Review findings breakdown:**
- Patched (5 entries, 12 rows total incl. the 4-way group): dispatch_land_finalize promotion gap (high, grouped: Blind Hunter + Edge Case Hunter + Verification Gap + Intent Alignment); `_reconcile_campaign_blocked` fourth call site (medium); missing `spec_text_at_ref` test coverage (medium); duplicated classification logic (medium); quote-mismatch regex (low).
- Deferred: none.
- Rejected: "shipped" status vocabulary not recognized — fix would edit this build's spec (medium); missing `commits` passthrough parameter — unreachable today, fix adds unused surface (low); local/origin `main` divergence — refuted, reads only `origin/main` and fails closed (false); case-sensitivity of `status:` values — refuted, no live case-variant exists and fails closed (false).

**Follow-up review recommendation:** `true`. This pass patched one `high`-verdict entry (the grouped `dispatch_land_finalize` finding) and three `medium`-verdict entries (`_reconcile_campaign_blocked`, missing test coverage, duplicated classification logic) — either the `high` alone or the two-or-more `medium` count would trigger `true` on a first pass. Named unverified risk: the `dispatch_land_finalize` promotion-filtering wiring and the `_reconcile_campaign_blocked` corroboration wiring are exercised only by the full `pyforge-marshal-test` suite passing, not by a dedicated fixture reproducing the PR #1477 mint-PR-promotes-incorrectly scenario end-to-end through those two specific call sites — unlike `dispatch_land`/`dispatch_supervisor`, which `test_promotion.py`'s existing PR #1477 fixtures already cover directly at the pure-function level. A follow-up pass should add direct fixtures for these two wiring sites mirroring that coverage. Patched-by-verdict: high 1, medium 3, low 1.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — exit 0, 8295 passed, 1 skipped, 12 deselected (re-run after all review patches; up from 8292 before the BH6 test additions). Verdict read from the command's own exit code, never through a pipe.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — exit 0, clean.
- `pixi run -e pyforge-marshal ruff check` on touched files was attempted and found unavailable in that environment (exit 127; no such pixi task) — consistent with AGENTS.md's note that repo-level ruff/mypy invocations are a decided-but-not-yet-landed TODO; not invented.

**Residual risks:**
- See the named follow-up risk above: `dispatch_land_finalize` and `_reconcile_campaign_blocked`'s corroboration wiring lack dedicated fixture-level regression tests (only full-suite-green coverage).
- The `spec_text_at_ref` primitive fetches spec content from `origin/main` at call time; if a caller's local clone has a stale or missing `origin/main` ref (never fetched), corroboration fails closed (returns not-corroborated) rather than erroring loudly — intentional per the Binding's fail-closed posture, but means a genuinely landed story could transiently read as not-yet-landed on a stale clone until the next fetch.
