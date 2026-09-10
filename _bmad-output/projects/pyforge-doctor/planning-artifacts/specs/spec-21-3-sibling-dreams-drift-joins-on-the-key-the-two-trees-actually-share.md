---
title: '`sibling-dreams-drift` joins on the key the two trees actually share'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: '69192cd1b967436ed5cca1f628910f6ff866cb48'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The detector keys both fingerprint maps on frontmatter `title:` while
the sibling tree shares **0 titles and 8 filenames** with the local tree (measured
live 2026-09-09 with the operator's token: 131 local Dreams parsed, 15 sibling). Story
16.1 is marked `done`, but the capability is structurally incapable of ever producing
a live finding, because the join key the code uses does not exist in the shared data.

**Approach:** Move the join from `title` to the filename slug. `_local_fingerprints`
and `_fetch_sibling_fingerprints` key on the path stem instead of `title`;
`_diff_shared_titles` intersects on slug; `title` is demoted from join key to a
**compared axis**, joining `("status","owner","content_hash")`. The eight shared
filenames then report their real divergence (at least `developer-machine-bootstrap`,
local `specified` vs sibling `dreamt`). The token-absent and fetch-failed paths stop
returning a bare `()` and instead emit a warn-only `sibling-dreams-unreachable`
finding naming the reason, so "could not look" no longer renders identically to
"looked and agreed." The unit test is rebuilt on the real 8-shared-filename shape
rather than today's single synthetic `_DECK_TITLE` fixture, which by construction
cannot reproduce the live failure.

## Boundaries & Constraints

**Always:**
- The join key for both `_local_fingerprints` and `_fetch_sibling_fingerprints` is the
  filename (path) stem, not `title`.
- `_diff_shared_titles` intersects on the slug; `title` moves from join key to a
  compared axis alongside `status`, `owner`, `content_hash`.
- A token-absent or fetch-failed path emits a warn-only `sibling-dreams-unreachable`
  finding naming the reason — never a bare `()` that renders identically to "checked
  and agreed."
- The unit test fixture is rebuilt on the real, measured 8-shared-filename shape
  (including at least `developer-machine-bootstrap`'s known `specified`/`dreamt`
  divergence), not a single synthetic title.

**Never:**
- Never leave `title` as a join key anywhere in the diff path — it is demoted to a
  compared axis only.
- Never let "could not reach the sibling" and "reached the sibling, trees agree"
  produce the same silent, empty result — they must be distinguishable outcomes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real shared filenames, live divergence | 131 local Dreams, 15 sibling, 8 shared filenames (0 shared titles) | Real divergence reported for the shared set, e.g. `developer-machine-bootstrap` local `specified` vs sibling `dreamt` | n/a |
| Shared filename, all axes agree | Same slug, same status/owner/content_hash/title | No Finding | n/a |
| No operator token | Token absent | Warn-only `sibling-dreams-unreachable` finding naming the reason (not a bare empty result) | Fail-open but named |
| Fetch failure | Sibling unreachable / HTTP error / timeout | Same warn-only `sibling-dreams-unreachable` finding naming the reason | Fail-open but named |
| Filename-only match, title differs | Same slug, differing `title` frontmatter | Reported as a divergence on the `title` axis (now compared, not joined) | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` — `_local_fingerprints` (`:118`), `_fetch_sibling_fingerprints` (`:155`), `_diff_shared_titles` (`:189`), the compared-axes tuple (`:194`), and the fail-open returns at `:45`/`:48`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` — rebuilt fixture on the real 8-shared-filename shape.

## Tasks & Acceptance

**Execution:**
- `fix` — re-key `_local_fingerprints` and `_fetch_sibling_fingerprints` on the filename/path stem instead of `title`.
- `fix` — change `_diff_shared_titles` to intersect on slug; add `title` to the compared-axes tuple alongside `status`, `owner`, `content_hash`.
- `feature` — replace the `return ()` at the token-absent and fetch-failed paths (`:45`/`:48`) with a warn-only `sibling-dreams-unreachable` finding naming the reason.
- `feature` — rebuild `test_sources_sibling_dreams.py`'s fixture on the real 8-shared-filename shape (not the single synthetic `_DECK_TITLE`), covering at least the `developer-machine-bootstrap` divergence.

**Acceptance Criteria:**
- Given the detector keys both fingerprint maps on frontmatter `title:` while the sibling tree shares 0 titles and 8 filenames, when the join moves to the filename slug with `title` demoted to a compared axis, then `_local_fingerprints` and `_fetch_sibling_fingerprints` key on the path stem, `_diff_shared_titles` intersects on slug, and `title` joins `("status","owner","content_hash")` in the compared axes.
- The eight shared filenames report their real divergence, at least `developer-machine-bootstrap` (local `specified` vs sibling `dreamt`).
- The token-absent and fetch-failed paths emit a warn-only `sibling-dreams-unreachable` finding naming the reason instead of `return ()`, so "could not look" never renders as "looked and agreed."
- The unit test is rebuilt on the real 8-shared-filename shape rather than the single synthetic `_DECK_TITLE`, which by construction cannot reproduce the live failure.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 0, false 2, maybe-false 1
- findings:
  - `[false]` `[reject]` Evidence key rename from `title` to `slug` breaks fleet consumers — fleet_picture.py uses `finding.get("check")` and `message` only; no code reads `evidence["title"]`.
  - `[false]` `[reject]` Unreachable findings filtered out of ATTENTION — `sibling_dreams_drift_findings()` returns all WARN findings including `sibling-dreams-unreachable`.
  - `[maybe-false]` `[reject]` `_diff_shared_titles` alias is dead code — alias exists for backward compatibility; no import references it; zero runtime cost; not worth a patch.

## Auto Run Result

Status: done

**Summary:** Re-keyed sibling-dreams drift detection from frontmatter `title` to filename slug; demoted `title` to a compared axis; token-absent and fetch-failed paths now emit `sibling-dreams-unreachable` WARN findings instead of silent empty tuples.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` — slug-keyed fingerprints, unreachable finding helper, title in compared axes
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` — rebuilt on 8 shared-filename fixture with live divergence shape
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-21-3-sibling-dreams-drift-joins-on-the-key-the-two-trees-actually-share.md` — spec status and run metadata

**Review:** 0 patches applied; 3 findings rejected (2 false, 1 maybe-false not worth fixing).

**Follow-up review recommended:** false

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — exit 0, full suite green (824 tests).

**Residual risks:** Live sibling fetch still requires operator token; unreachable finding surfaces in fleet ATTENTION when token absent (intentional per spec).
