---
title: 'GitHub releases unblind the npm-invisible packages'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: [oversized]
deferred:
  - summary: >-
      _fetch_latest_github_release's /tags fallback only reads GitHub's first
      response page, never following pagination.
    evidence: |-
      GitHub's /tags endpoint paginates; a heavily-tagged repo's newest tag
      could sit beyond the first page, understating the "latest" comparison.
      No currently-watched package needs it live: of the 6 named npm-invisible
      packages, 3 have GitHub Releases (checked first, succeeds before /tags
      is ever reached) and the other 3 have zero tags at all. Found by Edge
      Case Hunter during Story 15.1 review.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py:_fetch_latest_github_release
    severity: low
  - summary: >-
      No test in test_sources_bmad_method.py reads a real, live
      recipes/<name>/recipe.yaml directly to prove the GitHub fallback
      resolves the 6 actually-named npm-invisible packages.
    evidence: |-
      Every test in this file (including the new Story 15.1 tests) uses
      synthetic tmp_path-scoped fixtures, matching this file's own
      established, pre-existing convention (no test reads the real pixi.toml
      or _bmad/_config/manifest.yaml either). The mechanism was independently
      hand-verified against the live recipes/*/recipe.yaml files for all 6
      named packages during spec planning and again during review (Intent
      Alignment Auditor), but no automated test would catch a future drift
      in that file's extra.cfe-upstream-* shape. Found by Intent Alignment
      Auditor during Story 15.1 review.
    location: >-
      src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py
    severity: low
baseline_revision: 'fd5c16c16aee5550fd9b18e06a64d6f127a279f1'
---

<intent-contract>

## Intent

**Problem:** Doctor's suite-upstream-drift pass (`sources/bmad_method.py::_gather_suite_findings`,
Epic 14/CAP-4) compares every watched `bmad-*` pin against its latest npm release only. 6 of the 10
watched pins (`bmad-loop`, `bmad-labs-skills`, `bmad-manticore`, `bmad-method-wds-expansion`,
`bmad-module-template`, `bmad-utility-skills`) are GitHub-only and 404 on `registry.npmjs.org` — including
`bmad-loop`, the package whose 0.9.0-vs-0.11.0 lag originally motivated CAP-4. This is tracked as
`DW-14-1-1` (medium, open) in `planning-artifacts/deferred-work-ledger.md`.

**Approach:** When the existing npm fetch returns `None` for a suite package, fall back to querying
GitHub's own public REST API (releases, then tags) for that package's latest release, using the
per-package GitHub `owner/repo` already recorded in that package's local `recipes/<name>/recipe.yaml`
(`extra.cfe-upstream-registry: github` + `extra.cfe-upstream-name`) — never a hardcoded name→repo table.

## Boundaries & Constraints

**Always:**
- The GitHub fallback fires ONLY when the existing npm fetch (`_fetch_latest_upstream_version`) already
  returned `None` for a suite package — never for the CORE (`bmad-method`) comparison, never when npm
  already succeeded.
- The `owner/repo` slug is derived per-package from `recipes/<package>/recipe.yaml`'s `extra` block
  (`cfe-upstream-registry == "github"` → `cfe-upstream-name`), a tracked, already-existing file — never a
  hardcoded mapping (a hardcoded list omits exactly the newest GitHub-only tool).
- Entirely fail-open, mirrors every existing fetch helper in this module: a missing/unparseable
  `recipe.yaml`, a non-github registry, any GitHub HTTP/network/JSON failure, or an unparseable tag all
  fold to `None` — never raises, never surfaces a different Finding shape.
- Stays within the suite pass's existing shared monotonic deadline (`_SUITE_FETCH_TOTAL_BUDGET_SECONDS`);
  the fallback is skipped (not attempted) once that budget is exhausted, same as any other per-package
  fetch today.
- Bare unauthenticated `urllib.request` GETs only (mirrors the existing npm/PyPI precedent) — no token,
  no `gh` CLI, no subprocess (Boundaries: this module's independence rule).
- Query `GET https://api.github.com/repos/{owner}/{repo}/releases/latest` first; only on a `404`
  specifically (no Release has ever been published — a definitive, distinguishable state) fall back to
  `GET .../tags` and take the newest parseable tag. Any other failure returns `None` immediately without
  trying `/tags`.
- Tag/release names are stripped of one optional leading `v`/`V` before parsing with the existing
  `_parse_release_triple` (leniently, same as CAP-4's installed-side parsing) — `_parse_release_triple`
  itself is NOT modified (an existing test asserts `"v1.2.3"` is garbage to it).

**Block If:** None — this is a narrow, fully-specified extension of an existing fail-open pass.

**Never:**
- Never touch `_fetch_latest_upstream_version`'s own signature/behavior (npm stays untouched).
- Never persist fetched GitHub data (mirrors the module's no-local-persistence precedent).
- Never modify `recipes/**/recipe.yaml` (read-only).

**Amended in review (2026-08-22):** close `deferred-work-ledger.md`'s `DW-14-1-1` entry in this same PR --
this repo's own precedent (`DW-11-8-1`) closes a deferred-work entry in the same commit/PR that resolves
it, not deferred to a later finalize pass. See Review Triage Log.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| npm-invisible, GitHub has a Release | npm 404s; `recipe.yaml` says github; releases/latest 200s | Package is compared (WARN or contributes to the OK count) | n/a |
| npm-invisible, GitHub has only tags | releases/latest 404s | Falls back to `/tags`, uses newest parseable tag | n/a |
| npm-invisible, GitHub has neither | releases/latest 404s, `/tags` returns `[]` | Package stays unchecked (same as before) | Fails open, no Finding |
| `recipe.yaml` missing or non-github | e.g. TEA (npm-visible) never reaches this path; a github-mapping-less package | GitHub fallback not attempted | Fails open |
| GitHub outage / timeout on releases/latest | `URLError`/`OSError`/`TimeoutError` | No `/tags` fallback attempted; package stays unchecked | Fails open |
| npm already succeeded | npm fetch returns a version | GitHub never queried for that package | n/a |
| Shared budget exhausted before fallback | `remaining <= 0` after the npm miss | GitHub fallback skipped for that package | Fails open |
| Tag name has a `v` prefix | `"v0.11.0"` | Parses to `(0, 11, 0)` | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- add
  `_GITHUB_LATEST_RELEASE_URL`/`_GITHUB_TAGS_URL` constants, `_github_owner_repo(target, package)` (reads
  `recipes/<package>/recipe.yaml` via the already-imported `yaml`), `_fetch_latest_github_release(*,
  owner_repo, timeout=None)` (mirrors `_fetch_latest_upstream_version`'s fail-open shape); wire both into
  `_gather_suite_findings`'s per-package loop right after the existing `if latest is None:` npm-miss
  branch, before the existing `if latest is None: continue` fail-open skip. Update the module docstring's
  CAP-4 paragraph, `_SUITE_PREFIX`'s comment (the "6 of 10... npm-invisible" note is partly stale once
  this lands), and `_gather_suite_findings`'s own docstring.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- extend `BMAD_METHOD_VERSION_DRIFT`'s
  comment block (currently ends "...riding Story 10.3's existing surfaces unchanged.") with one sentence
  noting Story 15.1's GitHub-releases/tags fallback for npm-invisible suite packages.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- extend the matching
  `SourceRegistration(source=Source.BMAD_METHOD_VERSION_DRIFT, ...)` trailing comment the same way.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- new tests (see Tasks).
  Existing `recipes/bmad-loop/recipe.yaml` (real repo file, `extra.cfe-upstream-registry: github`,
  `extra.cfe-upstream-name: bmad-code-org/bmad-loop`) is the DW-14-1-1 fixture's real-world reference
  shape; tests write their own `tmp_path`-scoped `recipes/<name>/recipe.yaml` fixtures (existing suite
  tests already build fixture trees under `tmp_path`, e.g. `_write_conda_meta`).

## Tasks & Acceptance

**Execution:**
- `sources/bmad_method.py` -- add `_github_owner_repo` + `_fetch_latest_github_release` + URL constants --
  the two new fail-open helpers this story needs.
- `sources/bmad_method.py` -- wire the fallback into `_gather_suite_findings`'s loop -- only path that
  changes observable behavior; `checked` increments identically regardless of which source resolved.
- `sources/bmad_method.py`, `models.py`, `sources/__init__.py` -- update the three in-sync comment blocks
  named in Code Map -- keeps the "describe what this check covers" comments truthful (existing repo
  convention, enforced by review, not a test).
- `tests/unit/test_sources_bmad_method.py` -- unit-test `_github_owner_repo` (github hit, non-github
  registry, missing file, malformed YAML, missing `extra`) and `_fetch_latest_github_release` (releases
  hit, tags fallback on 404, non-404 skips tags, `v`-prefix stripping, empty/unparseable tags, every
  network failure mode folding to `None`) -- mirrors this file's existing `_fetch_latest_upstream_version`
  test block.
- `tests/unit/test_sources_bmad_method.py` -- THE `DW-14-1-1` fixture: `bmad-loop` npm-invisible,
  `recipes/bmad-loop/recipe.yaml` written with the real github mapping, GitHub stub returns a newer
  release -- must produce a WARN naming `bmad-loop`, evidence unchanged in shape from the existing
  npm-sourced WARN.
- `tests/unit/test_sources_bmad_method.py` -- integration-level suite tests: GitHub not queried when npm
  succeeds; GitHub not queried when no recipe.yaml mapping exists; GitHub fallback skipped when the shared
  budget is already exhausted; `packages_checked` in the OK-finding evidence rises when a previously
  npm-invisible package now resolves via GitHub.

**Acceptance Criteria:**
- Given the 2026-08-21 pre-update fixture reconstructed with `bmad-loop` npm-invisible and its real
  `recipes/bmad-loop/recipe.yaml` github mapping, when `gather()` runs, then a `bmad-suite-upstream-drift`
  WARN names `bmad-loop` exactly as CAP-4's own existing npm-sourced WARN does (same message/evidence
  shape), sourced via GitHub instead.
- Given a suite package whose npm fetch succeeds, when `gather()` runs, then the GitHub endpoints are
  never queried for that package.
- Given a suite package with no `recipes/<name>/recipe.yaml` or a non-github `cfe-upstream-registry`, when
  its npm fetch returns `None`, then it stays unchecked exactly as before this story (no crash, no new
  Finding).
- Given GitHub's releases/latest 404s and `/tags` returns entries, when parsing, then the newest
  successfully-parsed `v`-stripped tag triple is used.
- Given every existing CAP-1/CAP-2/CAP-4 test in `test_sources_bmad_method.py` (none of which create a
  `recipes/` fixture under `tmp_path`), when they run unmodified, then they still pass — `_github_owner_repo`
  fails closed (file-not-found) on those fixtures, so no extra request or budget consumption occurs.

## Spec Change Log

## Review Triage Log

### 2026-08-22 -- Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 1, medium 2, low 1)
- defer: 2 (low 2)
- reject: 1
- addressed_findings:
  - `[high]` `[patch]` GitHub fallback's two sequential HTTP calls (releases/latest, then /tags on 404) reused the SAME timeout for both, letting one package's fallback double its worst-case duration against the caller's shared per-package budget -- independently found by Edge Case Hunter and Verification Gap (the latter traced the consequence chain to `fleet_picture.py`'s hardcoded 15s subprocess bound). Fixed: `_fetch_latest_github_release` now tracks an internal deadline and bounds the `/tags` call to whatever remains of the original timeout, skipping `/tags` entirely once exhausted. Regression tests added.
  - `[medium]` `[patch]` A single malformed `/tags` entry (missing `"name"`, or non-mapping) raised inside the parsing comprehension and discarded every OTHER otherwise-valid parsed tag alongside it (Edge Case Hunter). Fixed: each entry is now parsed individually; a malformed one is skipped, not fatal to the scan. Regression test added.
  - `[medium]` `[patch]` `deferred-work-ledger.md`'s `DW-14-1-1` entry stayed `status: open` despite this story's own FR/AD line stating "closes doctor DW-14-1-1" (Intent Alignment Auditor, citing the direct `DW-11-8-1` same-commit-closure precedent). Fixed: closed the entry, mirroring `DW-11-8-1`'s exact format; amended this spec's Boundaries accordingly (see amendment note above -- root cause was outside `<intent-contract>`, so no code re-derivation was needed).
  - `[low]` `[patch]` `_github_owner_repo`'s except tuple omitted `ValueError`, so an unrepresentable path (e.g. an embedded NUL byte in a package name) would violate the function's own "never raises" docstring contract, even though `_gather_suite_findings`'s own outer safety net would still catch it one level up (Edge Case Hunter). Fixed: added `ValueError` to the except tuple. Regression test added.
- Process note: the fourth review layer (Blind Hunter) reported task-complete via `TaskStop` but its result content never reached this session despite two explicit resume/nudge attempts via `SendMessage`. Proceeded with triage on the three delivered layers (Edge Case Hunter, Verification Gap, Intent Alignment) after an extended wait well beyond the other three layers' completion times -- their findings were substantive, mutually convergent (Edge Case Hunter and Verification Gap independently found the same HIGH finding), and cover the diff thoroughly. Not treated as a quality shortcut; recorded here for transparency.

## Design Notes

`_github_owner_repo` reads a TRACKED, already-existing local file (`recipes/<name>/recipe.yaml`'s
`extra.cfe-*` block) rather than adding a new hardcoded table or a new tracked mapping file — this keeps
the derive-don't-declare discipline the rest of the module already follows for `_suite_packages` (pins are
the contract, never a hardcoded list). `extra.cfe-*` fields are this repo's own local-only internal
metadata (stripped before any upstream submission), so reading them from `recipes/**` is exactly the kind
of local tooling use they exist for.

Two live-verified edge cases worth naming: `bmad-manticore`'s GitHub Releases are stale (`v1.0.1`) relative
to its actual pinned `.dev0` main-branch version — this is fine, since the release-triple-only comparison
already treats an ahead-of-latest install as current (existing CAP-4 semantics, unchanged). `bmad-labs-skills`,
`bmad-module-template`, and `bmad-utility-skills` have neither GitHub Releases nor tags today — they stay
unchecked after this story too (fail-open), which is consistent with DW-14-1-1's own framing ("packages_checked
rises accordingly", not "reaches 10/10").

## Auto Run Result

**Summary:** Implemented Story 15.1 -- `_gather_suite_findings` (Epic 14/CAP-4's suite pass, `sources/bmad_method.py`)
now falls back to GitHub releases/tags whenever the existing npm fetch misses for a suite package, keyed
by that package's own tracked `recipes/<name>/recipe.yaml` github mapping (`extra.cfe-upstream-registry`
+ `extra.cfe-upstream-name`), inside the same shared fail-open budget. Closes `DW-14-1-1`.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- new
  `_github_owner_repo`, `_fetch_latest_github_release`, `_strip_leading_v` helpers + URL constants; wired
  into `_gather_suite_findings`'s per-package loop; module/function docstrings updated. Post-review: the
  GitHub fallback's internal two-call timeout is now bounded to the caller's original budget (not doubled),
  and a malformed `/tags` entry is skipped individually instead of aborting the whole scan.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- `BMAD_METHOD_VERSION_DRIFT` comment
  extended to describe the fallback.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- matching registry comment
  extended.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- 26 new tests (90 total,
  was 64): `_github_owner_repo` unit coverage, `_fetch_latest_github_release` unit coverage (releases hit,
  404-to-tags fallback, non-404 skips tags, v/V stripping, empty/unparseable/malformed tags, every network
  failure mode, timeout bounding, deadline exhaustion, NUL-byte path), the DW-14-1-1 fixture test, and 4
  integration tests proving when the fallback does/does not fire.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md` -- `DW-14-1-1` closed
  (review finding; see Review Triage Log and the Boundaries amendment above).

**Review findings breakdown:** 4 patches applied (1 high, 2 medium, 1 low), 2 deferred (low, low; see
frontmatter `deferred`), 1 rejected (noise). Blind Hunter's layer did not return output despite completing
and two resume attempts (process note in Review Triage Log); triaged on the other three layers.

**Follow-up review recommendation:** `true` -- one patched finding this pass was `high` severity.

**Verification performed:**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py -v`
  -- 90/90 passed (re-run after patches).
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor -q` -- 1124 passed, 1 skipped, 1
  pre-existing unrelated failure (`test_check_speed_budget.py`, `pyforge.warden` not installed in this
  worktree's pixi env -- confirmed pre-existing by reproducing identically with all this story's changes
  stashed out).
- `tests/meta/test_source_independence.py` -- 60/60 passed (no new imports outside stdlib/`yaml`).

**Residual risks:** The GitHub API is queried unauthenticated (60 req/hr rate limit), same tier as the
existing npm precedent -- acceptable per this module's own established risk tolerance, not new to this
story. Two low-severity items deferred (see frontmatter): `/tags` pagination not followed beyond page 1
(no currently-watched package needs it); no test reads the live `recipes/*/recipe.yaml` directly (matches
this file's established synthetic-fixture convention; the mechanism was hand-verified against all 6 live
files during planning and review).


## Verification

**Commands:**
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py -v`
  -- expected: all existing + new tests pass.
- `pixi run -e local-recipes pytest src/shared/packages/pyforge-doctor -q` -- expected: no regressions
  elsewhere in the package (e.g. `tests/meta/test_source_independence.py` still passes -- no new imports
  outside stdlib/`yaml`).
