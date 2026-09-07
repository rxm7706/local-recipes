---
title: 'Suite drift maps every active member, derived from the roster'
type: 'feature'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      epics.md Story 20.1's Surface line (naming suite-members.yaml and
      _manifest_suite_members/_pixi_suite_package_names) and its AC's
      'packages_checked reads 13' wording do not precisely match the shipped
      implementation (per-recipe.yaml cfe-source-kind derivation; suite
      evidence reads 12, core excluded).
    evidence: |-
      suite-members.yaml carries no registry/probe-class field on any entry,
      so the literal Surface reading has no data to read; the recipe.yaml-based
      approach is the only functionally coherent one (matches Story 19.1 and
      steward's spec-bmad-suite-metapackage precedent) and is fully justified
      in this spec's own Design Notes ('Why 12, not 13'). Pre-existing
      imprecision in the epics.md text, not introduced by this diff.
    location: >-
      _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
      (Story 20.1, Surface + AC lines)
    severity: low
baseline_revision: 'a35c8218566ff2a0c37e72380de7f42f0d70fe57'
---

<intent-contract>

## Intent

**Problem:** `bmad_method.py`'s suite pass (`_gather_suite_findings`) resolves an
"upstream latest" for a watched `bmad-suite` package only via npm-or-github
releases/tags (`_resolve_upstream_latest` -> `_fetch_latest_upstream_version` /
`_fetch_latest_github_release`). Members whose `recipes/<name>/recipe.yaml`
records `extra.cfe-source-kind: github-commit` (7 of the roster's 13
`suite-members.yaml` entries -- e.g. `bmad-eval-quality`, `bmad-manticore`,
`mybmad-dashboard`) are pinned to a raw commit on the default branch, not a
version tag; querying releases/tags for them either 404s or returns a stale
tag that misrepresents drift, so most of the roster stays effectively
unwatched, and no Finding names *how* a package was probed at all.

**Approach:** Read each watched package's own `extra.cfe-source-kind`
(already-tracked, already read for other fields by `_upstream_registry`/
`_github_owner_repo`) to pick its probe: `github-tag` (unchanged -- releases/
tags, via the existing `_resolve_upstream_latest`), `npm-registry` (unchanged
-- npm, via the existing path), `github-commit` (NEW -- fetch the GitHub repo's
default-branch HEAD commit sha and compare it to the recipe's own tracked
`context.commit`). Every `bmad-suite-upstream-drift` per-package WARN Finding
now names its probe class in `evidence["probe_class"]`. The aggregate OK
Finding's evidence shape (`packages_checked`/`packages_watched`) is unchanged.

## Boundaries & Constraints

**Always:**
- Read-only: only already-tracked files (`recipes/<name>/recipe.yaml`) and one
  new unauthenticated GitHub GET. No subprocess, no git history, no writes.
- Entirely fail-open per package, exactly like every existing probe in this
  module: a missing `context.commit`, a missing/non-github owner-repo mapping,
  or any GitHub fetch failure (network, timeout, malformed JSON, empty array)
  leaves that package unchecked (`checked` does not increment for it) -- never
  raises past `_gather_suite_findings`'s own `except Exception: return ()` net.
- The per-package fetch draws from the SAME shared `deadline`/`remaining` pool
  (`_SUITE_FETCH_TOTAL_BUDGET_SECONDS`, unchanged at `15.0`) via the same
  `min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)` formula every other fetch
  in this loop already uses.
- `probe_class` is one of exactly `"tag"`, `"npm"`, `"commit-pinned"` for every
  real roster member today; a package with no recognized `cfe-source-kind`
  defaults to `"tag"` when its registry is not `"npm"` (preserves today's only
  pre-existing github behavior for any fixture that predates
  `cfe-source-kind`), or `"npm"`/`"pypi"` when the registry says so.
- The core `bmad-method` package's own `bmad-method-upstream-drift` Finding
  (CAP-1/CAP-2, outside `_gather_suite_findings`) is untouched -- `probe_class`
  is a `bmad-suite-upstream-drift`-only addition.

**Never:**
- Never add `probe_class` to the aggregate `bmad-suite-upstream-drift` OK
  Finding's evidence (stays exactly `{"packages_checked": N, "packages_watched": M}`)
  -- only per-package WARN Findings carry it.
- Never fold `bmad-method` (the core) into `_gather_suite_findings`'s loop --
  `_suite_packages` keeps excluding `DEPENDENCY_NAME`, per this file's own
  documented invariant ("including it would duplicate
  `bmad-method-upstream-drift`"). `suite-members.yaml` lists 13 entries total
  (core + 12 suite members); the suite loop's `packages_checked`/
  `packages_watched` therefore read **12** when every non-core member
  resolves, not 13 -- the core's own always-separate check is the 13th. Do not
  attempt to make the suite evidence literally read 13; that would require
  duplicating the core into a second Finding, which this file's existing
  docstring explicitly forbids.
- Never reformat the commit-pinned package's pinned version through
  `_recipe_version`/`_parse_release_triple` for the evidence text -- that
  parser drops the `.dev0` suffix the `"X.Y.Z.dev0 @ sha"` encoding requires.
  Read `context.version` as a raw string instead.
- Never change `_resolve_upstream_latest`'s existing signature, return type,
  or its npm/github/pypi callers/tests -- the new commit-pinned probe is a
  parallel branch in `_gather_suite_findings`'s own loop, not a code path
  inside `_resolve_upstream_latest`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tag-class regression (2026-08-21 fixture) | `bmad-loop` pinned 0.9.0, no `cfe-source-kind` fixture, stubbed resolve returns (0,11,0) | `bmad-suite-upstream-drift` WARN; evidence adds `"probe_class": "tag"` alongside existing keys | No error expected |
| npm-class WARN | A package with `cfe-source-kind: npm-registry`, installed behind stubbed npm latest | WARN Finding, evidence `"probe_class": "npm"` | No error expected |
| Commit-pinned WARN | `cfe-source-kind: github-commit`, `context.version: "0.2.0.dev0"`, `context.commit: "aaaa...(40 hex)"`, stubbed HEAD sha `"bbbb...(40 hex)"` (differs) | WARN Finding; message and evidence `installed` = `"0.2.0.dev0 @ aaaaaaaaaaaa"` (first 12 chars of the commit), evidence `latest_upstream` = `"bbbbbbbbbbbb"` (first 12 chars of HEAD), `"probe_class": "commit-pinned"` | No error expected |
| Commit-pinned current | Same as above but stubbed HEAD sha equals `context.commit` exactly | No WARN for this package; it still counts toward `checked` | No error expected |
| Commit-pinned, no recipe commit | `cfe-source-kind: github-commit`, recipe.yaml has no `context.commit` | Package unchecked (no WARN, does not increment `checked`); rest of the suite pass unaffected | Fail-open, no exception |
| Commit-pinned, no github mapping | `cfe-source-kind: github-commit`, `extra.cfe-upstream-registry` missing/non-github | Package unchecked | Fail-open, no exception |
| Commit-pinned, HEAD fetch fails | Valid mapping + commit, but the GitHub commits endpoint raises/404s/returns an empty array | Package unchecked | Fail-open, `_fetch_default_branch_head_sha` returns `None`, never raises |
| Full-roster count | 12 non-core members mirroring the real roster (4 `github-tag`, 7 `github-commit`, 1 `npm-registry`), all current | Aggregate OK Finding: `evidence == {"packages_checked": 12, "packages_watched": 12}` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py`
  - `_upstream_registry` (existing, ~L429) -- reads `extra.cfe-upstream-registry`; reuse verbatim, called again from the new loop branch (redundant-read style already used elsewhere in this file, e.g. `_recipe_version` is independently re-read inside `_channel_and_recipe_drift_findings`).
  - `_github_owner_repo` (existing, ~L610) -- reuse verbatim for the commit-pinned branch's owner/repo lookup (it only checks `cfe-upstream-registry == "github"`, not source-kind, so it already works for commit-pinned packages unmodified).
  - `_recipe_version` (existing, ~L750) -- do NOT reuse for the commit-pinned encoding (drops `.dev0`); add a new sibling reader instead (see below).
  - `_fetch_latest_github_release` / `_GITHUB_LATEST_RELEASE_URL` / `_GITHUB_TAGS_URL` (existing, ~L593-729) -- pattern to mirror for the new `_fetch_default_branch_head_sha`, NOT to be modified.
  - `_gather_suite_findings` (existing, ~L906-1039) -- the per-package loop (`for name in packages:`, ~L958) is where the new branch goes, before the existing `latest = _resolve_upstream_latest(...)` call.
  - `_resolve_upstream_latest` (existing, ~L483) -- unmodified; still the probe for `github-tag`/`npm-registry`/unmapped-registry members.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py`
  - `_stub_fetch_by_package` (~L719) -- existing helper that monkeypatches `_resolve_upstream_latest`/`_fetch_latest_upstream_version` wholesale; reuse unmodified for tag/npm-class tests.
  - `_write_recipe_yaml` (~L1263) and the `_RECIPE_*` fixture strings (~L1270-1296) -- pattern to follow for new commit-pinned recipe.yaml fixtures (add `context:` with `version`/`commit`, and `extra.cfe-source-kind`).
  - `_write_conda_meta` (~L706) -- reuse to mark each fixture package "installed" (the loop's own gate; commit-pinned packages still need a conda-meta marker even though the comparison itself reads the recipe, not the marker's version).
  - Exact assertions needing a `"probe_class": "tag"` key added: `loop_finding.evidence` and `tea_finding.evidence` in `test_2026_08_21_pre_update_fixture_names_bmad_loop_and_tea` (~L793, ~L801); `suite[0].evidence` in `test_mixed_suite_one_behind_one_current_reports_only_the_warn` (~L857); `finding.evidence` in `test_dw_14_1_1_bmad_loop_npm_invisible_resolves_via_github` (~L1610). These are the ONLY existing `evidence ==` assertions on `bmad-suite-upstream-drift` per-package WARN Findings in the file (verified by grep for `"package":` / `evidence ==`) -- every other `evidence ==` assertion in the file is either the aggregate OK shape (`packages_checked`/`packages_watched`, unaffected) or a `bmad-method`/core-side (`bmad-channel-drift`, `bmad-recipe-upstream-drift`, `bmad-method-version-drift`, `bmad-method-upstream-drift`) Finding, none of which this story touches.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- add constants `_SOURCE_KIND_GITHUB_TAG = "github-tag"`, `_SOURCE_KIND_GITHUB_COMMIT = "github-commit"`, `_SOURCE_KIND_NPM_REGISTRY = "npm-registry"`, `_PROBE_CLASS_TAG = "tag"`, `_PROBE_CLASS_COMMIT_PINNED = "commit-pinned"`, `_PROBE_CLASS_NPM = "npm"`, and `_GITHUB_COMMITS_URL = "https://api.github.com/repos/{owner_repo}/commits?per_page=1"` -- these name the three registry classes and the one new GitHub endpoint the AC requires.
- same file -- add `_source_kind(target: Path, package: str) -> str | None`, mirroring `_upstream_registry`'s exact try/except shape (same exception tuple), reading `extra.cfe-source-kind` -- gives every other new function a single, already-tracked signal for which probe a package uses.
- same file -- add `_probe_class(source_kind: str | None, registry: str | None) -> str`: `github-commit` -> `"commit-pinned"`; `registry == "npm"` or `source_kind == "npm-registry"` -> `"npm"`; `registry == "pypi"` -> `"pypi"`; else -> `"tag"` -- the fallback ordering matters (commit-pinned checked first) so a package with both fields set is never mislabeled.
- same file -- add `_recipe_pinned_commit(target: Path, package: str) -> tuple[str, str] | None` returning `(raw context.version text, raw context.commit text)` on success, `None` on any missing/malformed input (same exception tuple as `_recipe_version`) -- deliberately reads `context.version` as a raw string (never through `_parse_release_triple`) so the `.dev0` suffix survives for the `"X.Y.Z.dev0 @ sha"` encoding.
- same file -- add `_fetch_default_branch_head_sha(*, owner_repo: str, timeout: float | None = None) -> str | None`: one GET to `_GITHUB_COMMITS_URL`, return `str(entries[0]["sha"])`; fold `urllib.error.URLError` (covers `HTTPError`), `http.client.HTTPException`, `OSError`, `TimeoutError`, `ValueError`, `KeyError`, `TypeError`, `IndexError` to `None` -- mirrors `_fetch_latest_upstream_version`'s never-raises contract; `IndexError` covers an empty `[]` body (a brand-new/emptied repo).
- same file -- in `_gather_suite_findings`'s per-package loop, after computing `per_fetch_timeout = min(remaining, _UPSTREAM_FETCH_TIMEOUT_SECONDS)`, compute `source_kind = _source_kind(target, name)` and `probe_class = _probe_class(source_kind, _upstream_registry(target, name))`; when `source_kind == _SOURCE_KIND_GITHUB_COMMIT`, branch to the new commit-pinned path (resolve `_recipe_pinned_commit` then `_github_owner_repo` then `_fetch_default_branch_head_sha`; `continue` immediately -- fail-open -- if any is `None`; otherwise increment `checked`, and append a WARN Finding when `head_sha != pinned_commit`, with `evidence={"package": name, "probe_class": probe_class, "installed": f"{pinned_version_text} @ {pinned_commit[:12]}", "latest_upstream": head_sha[:12]}`, message `f"{name} {pinned_version_text} @ {pinned_commit[:12]} is behind the default-branch HEAD {head_sha[:12]}"`; then `continue` past the existing triple-based branch) -- otherwise fall through unchanged to the existing `_resolve_upstream_latest` call, adding `"probe_class": probe_class` to that branch's existing WARN evidence dict only (the OK/aggregate evidence dict is untouched).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` -- update the 4 existing `evidence ==` assertions named in Code Map to add `"probe_class": "tag"`.
- same test file -- add unit tests for `_source_kind` (hit, missing file, malformed yaml, missing extra -- mirror `_github_owner_repo`'s own 4-test block), `_recipe_pinned_commit` (hit returns the raw `.dev0` string + full sha, missing `context.commit`, missing `context.version`, missing recipe.yaml, malformed yaml), `_fetch_default_branch_head_sha` (success parses `entries[0]["sha"]`, HTTPError/URLError/timeout/malformed-json/empty-array/missing-sha-key each fold to `None`), and `_probe_class` (all four branches, including the commit-pinned-takes-priority-over-npm-registry ordering case).
- same test file -- add one `_gather_suite_findings`/`gather()`-level test per non-regression Matrix row: npm-class WARN naming `probe_class: "npm"`; commit-pinned WARN with the full `"X.Y.Z.dev0 @ sha"` message/evidence encoding; commit-pinned current (sha match, no WARN, still counted); commit-pinned missing-`context.commit` (unchecked); commit-pinned missing-github-mapping (unchecked); commit-pinned HEAD-fetch-failure (unchecked, stub `_fetch_default_branch_head_sha` to return `None`).
- same test file -- add the full-roster count test: 12 synthetic non-core members (4 `github-tag`, 7 `github-commit`, 1 `npm-registry`) all current, asserting the aggregate `bmad-suite-upstream-drift` OK Finding's evidence reads exactly `{"packages_checked": 12, "packages_watched": 12}`.

**Acceptance Criteria:**
- Given the real `recipes/bmad-suite/suite-members.yaml` roster's registry-class mix (4 `github-tag`, 7 `github-commit`, 1 `npm-registry`, plus the core), when every non-core member's probe succeeds, then the suite's aggregate `bmad-suite-upstream-drift` OK Finding's evidence reads `{"packages_checked": 12, "packages_watched": 12}` (the core's own separate, pre-existing `bmad-method-upstream-drift` Finding accounts for the 13th roster entry -- see Boundaries & Constraints).
- Given a `github-commit` package whose recipe `context.commit` differs from the GitHub API's reported default-branch HEAD sha, when `_gather_suite_findings` runs, then it emits a `bmad-suite-upstream-drift` WARN Finding whose message and evidence encode the pinned side as `"{version} @ {commit[:12]}"` and the upstream side as the HEAD sha's first 12 characters, with `evidence["probe_class"] == "commit-pinned"`.
- Given every existing `bmad-suite-upstream-drift` WARN-Finding test in `test_sources_bmad_method.py` (tag-class, npm-invisible-via-github-fallback), when the suite updated in this story runs, then each still fires WARN exactly as before, now additionally carrying `evidence["probe_class"] == "tag"`.
- Given this module's own "never crashes" discipline, when any commit-pinned probe input is missing or the GitHub fetch fails, then the package is silently skipped (not counted, no Finding), and every other package's own outcome (including the aggregate) is unaffected.

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 17 findings — high 0, medium 1, low 6, false 10, maybe-false 0
- findings:
  - `[low]` `[defer]` Blind Hunter: epics.md's Story 20.1 AC text says "packages_checked reads 13", but the shipped/tested code reads 12 (bmad-method core is excluded, per this module's pre-existing "no duplicate bmad-method-upstream-drift" invariant) — evidence: pre-existing imprecision in the epics.md wording (predates this diff), the shipped behavior is the only functionally coherent reading and is documented at length in this spec's own Design Notes ("Why 12, not 13"); deferred for the next Epic 20 currency-validation pass to reconcile epics.md's wording, not this story's fix to make.
  - `[low]` `[defer]` Intent Alignment: the story's Surface line names `recipes/bmad-suite/suite-members.yaml` and functions `_manifest_suite_members`/`_pixi_suite_package_names` as this story's touch points, but the diff instead reads each member's own `recipes/<name>/recipe.yaml` (`extra.cfe-source-kind`) and leaves those two functions untouched — evidence: verified `suite-members.yaml` carries no registry/probe-class field on any entry (only `name`/`notes`/`deprecated`), so the literal Surface reading has no data to read; the recipe.yaml-based approach is the only coherent one and matches the precedent Story 19.1 and steward's `spec-bmad-suite-metapackage` already established. Same root cause as the row above (epics.md's Story 20.1 text is imprecise about the actual mechanism) — grouped, shares the `defer` route.
  - `[low]` `[defer]` Intent Alignment: same "13 vs 12" headcount divergence as the first row above — grouped, shares the `defer` route.
  - `[low]` `[patch]` Blind Hunter: `probe_class = _probe_class(source_kind, _upstream_registry(target, name))` calls `_upstream_registry` unconditionally, even for `github-commit` packages whose `_probe_class` branch never uses the registry argument (it returns `"commit-pinned"` from `source_kind` alone) — evidence: verified in `_gather_suite_findings`'s per-package loop; a wasted local YAML read/parse for 7 of 12 real roster members every gather() call. Applied: the commit-pinned branch now sets `probe_class` directly from `source_kind`, with no `_upstream_registry` call at all; `_upstream_registry` is now read only in the tag/npm/pypi fall-through branch.
  - `[low]` `[patch]` Blind Hunter: for non-commit-pinned packages, `_upstream_registry` is now read twice per package per gather() call — once for `probe_class`, once again inside `_resolve_upstream_latest` itself — evidence: confirmed `_resolve_upstream_latest` independently calls `_upstream_registry(target, package)` in its own body. Grouped with the row above (same root cause: unconditional/duplicate registry read introduced by the new probe_class line). The residual duplication for the non-commit-pinned case is an accepted byproduct of the spec's explicit "never change `_resolve_upstream_latest`'s signature" boundary — action is limited to the commit-pinned short-circuit above; no further fix for this half.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter (duplicate finding, same root cause): `_recipe_pinned_commit` reads `context["version"]`/`context["commit"]` and coerces with `str(...)` without checking the value is a non-empty string first — a YAML-null `commit:`/`version:` key (present but empty) does not raise `KeyError`, so `str(None)` silently becomes the literal text `"None"` instead of the function fail-opening, contradicting this spec's own Boundaries ("a missing `context.commit` ... leaves that package unchecked") — evidence: verified against `_recipe_pinned_commit`'s code, which lacks the non-empty-string guard that the registry/source-kind readers both already use. Applied: added a non-empty-string guard for both version and commit fields, matching the registry/source-kind readers; a YAML-null value now returns None instead of coercing to the literal text "None".
  - `[low]` `[patch]` Edge Case Hunter: the commit-pinned comparison `head_sha != pinned_commit` does not normalize case — a recipe.yaml `context.commit` written in mixed/upper case (the API this compares against always returns lowercase hex) would report a permanent spurious WARN even when the pin is actually current — evidence: verified no lowercasing normalization exists at the comparison site; real-world likelihood is low (git tooling always emits lowercase hex shas) but the fix is a trivial one-line normalization. Applied: the comparison now uses stripped, lowercased forms of both shas, and the message/evidence display those same normalized values.
  - `[false]` `[reject]` Blind Hunter: `_probe_class`'s pypi-registry branch returns the bare literal `"pypi"` instead of a named constant, called "inconsistent" — refutation: the code's own comment directly above the constant block already documents this as deliberate (a fourth probe-class value reachable via that branch, with no dedicated constant because no roster member uses it today); the claimed oversight is disproven by the existing, accurate documentation.
  - `[false]` `[reject]` Blind Hunter: no test exercises a gather() call where multiple probe classes each produce a WARN in the same pass, implying an untested coexistence risk — refutation: traced the loop; the probe-class and pinned-commit values are all fresh per-iteration local bindings and the warn-findings list append is the same shared-list-append pattern already used identically for every package before this story — no cross-iteration aliasing or shared mutable state exists that a multi-class scenario could expose differently from the single-class tests already present.
  - `[false]` `[reject]` Blind Hunter: `_probe_class` checks the npm-registry condition before defaulting to the tag class, so a hypothetical package combining the tag source-kind with an npm registry would misclassify as npm — refutation: verified against every real recipe.yaml; the only real package combining an npm registry with a tag source-kind is the core package itself, and the core is unconditionally excluded from `_gather_suite_findings`'s loop — this combination can never actually reach `_probe_class` in production.
  - `[false]` `[reject]` Blind Hunter: no test feeds an unrecognized/garbage source-kind value through the full gather loop to confirm the fallback — refutation: traced `_probe_class`'s logic; an unrecognized string and a missing value both fail every specific branch identically and fall through to the exact same default tag-class return — there is no distinct code path for "unrecognized" versus "missing" for a test to additionally exercise; the existing default-fallback unit test already covers this exact branch.
  - `[false]` `[reject]` Blind Hunter: docstrings cite "(Design Notes)"/"(Boundaries)" but no such spec artifact is discoverable — refutation: the cited artifact is this very spec file, which contains both a Design Notes and a Boundaries & Constraints section; the reviewer was scoped to the diff file only and did not have this spec in view, but the artifact demonstrably exists.
  - `[medium]` `[patch]` Verification Gap (arrives pre-verified, filed disposition accepted as-is): no test proves the commit-pinned branch's early loop-continue actually blocks fallthrough to the tag/npm path — every existing commit-pinned gather()-level test stubs the tag/npm resolver to return nothing for that package name regardless, so a future regression that removed or reordered that continue would silently reintroduce the exact stale-tag duplicate-finding noise this story exists to eliminate, undetected by this test suite. Applied: added test_commit_pinned_branch_never_falls_through_to_the_tag_npm_path, which stubs the tag/npm resolver to return a resolvable-but-wrong triple for the commit-pinned package, tracks call names, and asserts the package name never appears among them while exactly one commit-pinned Finding still fires.
  - `[false]` `[reject]` Intent Alignment: tests build their recipe/pixi/manifest fixtures synthetically under a temp path rather than running gather() against the live checked-in recipes tree, so the comment's claim of mirroring the real roster is not self-verified by the test — refutation: this is this test file's own pre-existing, deliberate isolation convention (every earlier capability's test before this story already works this way, never reading the live tree); the auditor's own independent inspection confirmed the synthetic fixture's registry-class split genuinely matches the live recipe classification — the claim is true, just not self-checking, which is consistent with every other test in this file.
  - `[false]` `[reject]` Intent Alignment: a related deferred-work item is named as "kin" in the story's FR/AD line but its own distinct ask (an offline pin-floor-vs-installed comparison) is not resolved by this diff — refutation: the auditor's own report concludes this is consistent with "kin" rather than "resolves" — this is a confirmation of correct scoping, not a divergence or defect.

## Design Notes

**Why 12, not 13.** `suite-members.yaml` lists 13 active entries (the core `bmad-method` plus 12 suite tools). This file's own docstring documents, at length, that `_suite_packages` deliberately excludes the core from the suite loop ("including it would duplicate `bmad-method-upstream-drift`") -- CAP-1/CAP-2 already own the core's drift signal via a separate Finding. The epic's own AC phrase "`packages_checked` reads 13" describes the roster's headline size (also used that way in the cross-station relay note in `spec-bmad-method-core-upgrade`'s open questions: "doctor maps 7 of 13 members today"), not a literal requirement to fold the core into the suite Finding's own evidence count. This story achieves full 13/13 coverage across the two Findings taken together (1 core + 12 suite); it does not, and per this file's existing architecture should not, make the suite Finding's own `packages_checked` literally read 13.

**Why a new sibling reader instead of reusing `_recipe_version`.** `_recipe_version` intentionally lenient-parses `context.version` into a bare `(X, Y, Z)` triple via `_parse_release_triple` (drops any `.dev0`/prerelease suffix) -- correct for every OTHER caller, which only ever needs a comparable triple. The commit-pinned encoding the AC names (`"X.Y.Z.dev0 @ sha"`) needs the *raw* version string with its suffix intact, so `_recipe_pinned_commit` reads `context.version` as a plain string, never through that parser.

**Why `_fetch_default_branch_head_sha` needs no default-branch name.** GitHub's `GET /repos/{owner}/{repo}/commits` (no `sha`/`path` query params) already returns commits reachable from the repository's *default* branch, newest first -- so `?per_page=1` gets the HEAD commit in one GET, with no need to first resolve the default branch's name via a separate `GET /repos/{owner_repo}` call.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: full suite green, no regressions in `test_sources_bmad_method.py` or elsewhere.
- `pixi run -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py -v` -- expected: every existing test still passes (with the 4 updated evidence dicts) and every new test passes.

## Auto Run Result

**Summary of implemented change:** the bmad-suite drift detector now derives each watched package's own upstream probe from its recipe's tracked `extra.cfe-source-kind` (`github-tag`/`npm-registry`, unchanged; `github-commit`, new) instead of always going through the releases/tags-or-npm path. The new `github-commit` probe compares the recipe's own `context.commit` against the target repository's default-branch HEAD commit sha (one GitHub commits-endpoint GET, entirely fail-open). Every per-package `bmad-suite-upstream-drift` WARN Finding now names its probe class in `evidence["probe_class"]` (`"tag"`/`"npm"`/`"commit-pinned"`). The aggregate OK Finding's evidence shape is unchanged. All 7 real commit-pinned roster members (previously unwatchable via releases/tags) are now checkable; the suite's aggregate evidence reads 12/12 non-core members (core stays separately owned by the pre-existing `bmad-method-upstream-drift` Finding).

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` — added `_source_kind`, `_probe_class`, `_recipe_pinned_commit`, `_fetch_default_branch_head_sha`, and the new probe-class-branching logic inside `_gather_suite_findings`'s per-package loop.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` — updated 4 pre-existing evidence-dict assertions to add `"probe_class": "tag"`; added unit tests for all 4 new functions; added gather()-level tests for every I/O Matrix row (npm-class WARN, commit-pinned WARN/current/3 fail-open scenarios, the full-roster 12/12 count) plus the review-driven regression test proving the commit-pinned branch's `continue` is load-bearing.

**Review findings breakdown** (17 total across 4 layers — Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment):
- Patched (4, all applied and re-verified): unconditional/duplicate `_upstream_registry` read for commit-pinned packages (low); `_recipe_pinned_commit` silently coercing a YAML-null field to the literal text `"None"` instead of failing open (low); the commit-sha comparison not normalizing case (low); no test proving the commit-pinned branch's `continue` actually blocks fallthrough to the tag/npm path (medium).
- Deferred (1 group, 3 rows — low): epics.md's Story 20.1 Surface line and its "packages_checked reads 13" AC wording don't precisely describe the shipped implementation (which reads `recipes/<name>/recipe.yaml` per member rather than `suite-members.yaml` directly, and reports 12 in the suite's own evidence since the core is separately owned) — pre-existing imprecision in the epics.md text, not introduced by this diff; the shipped behavior is the only functionally coherent reading (verified `suite-members.yaml` carries no registry-class field) and is documented in this spec's Design Notes. Recorded in frontmatter `deferred` for the next Epic 20 currency-validation pass.
- Rejected as false (10): a bare `"pypi"` literal instead of a named constant (already documented as deliberate in a code comment); no test for multi-probe-class coexistence in one gather() pass (traced — no shared mutable state exists that would behave differently); asymmetric npm-vs-tag precedence in `_probe_class` (unreachable for any real non-core roster member — the one real combination, the core package itself, never reaches this loop); no test for an unrecognized `cfe-source-kind` value (identical code path to the already-tested missing-value case); a claim that this spec's own Design Notes/Boundaries are undiscoverable (they exist in this very file); tests using synthetic tmp_path fixtures rather than the live `recipes/` tree (this file's own pre-existing, deliberate isolation convention; independently verified the synthetic mix matches live data); `DW-FU-14-1-2` named as "kin" but not resolved (confirmed correct scoping, not a divergence).

**Follow-up review recommendation:** `false` — 3 patched entries were `low`, 1 was `medium`; the rule (`true` only if any patched entry was `high`, or 2+ `medium` entries were patched) is not met.

**Verification performed:**
- `pixi run -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py -q` → 157 passed (pre-patch), 157 passed again post-patch (156 original + 1 review-driven regression test).
- `pixi run -e pyforge-doctor pyforge-doctor-test` (full package suite) → 1375 passed, 1 skipped post-patch (1374 pre-patch; delta matches the one new test).
- `ruff check`/`mypy` on both changed files, before and after (via `git stash` comparison both times) → identical 4 pre-existing ruff findings, 0 new findings introduced by this diff at any point.
- Manually read the full unified diff against `baseline_revision` after the patch pass and confirmed each of the 4 requested fixes landed exactly as specified, with no unrelated changes.

**Residual risks:** none rated `high`/`medium` remain unaddressed. The one deferred item (epics.md's Story 20.1 text imprecision) is a documentation/traceability gap only — the shipped code's behavior is correct and thoroughly justified; it does not affect runtime correctness, fail-open guarantees, or the PR-gate-advisory-only invariant.
