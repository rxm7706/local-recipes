---
title: '26.1: A touched live-proof-only surface gets an advisory Doctor finding naming it'
type: 'feature'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** bugs cluster where a dev/review pass structurally cannot verify them from inside the repo alone — a live round-trip against something outside it (a third-party API, a live browser, a service with its own auth and drift) is the only real proof, and no self-report is evidence of that. `live-proof-surfaces.md` (CAP-77's companion) already catalogs six such surfaces fleet-wide, each with a real, existing proof mechanism (or an honest "no mechanism yet" note) — but nothing currently reads that catalog or surfaces it to a reviewer.

**Approach:** A new Doctor Source (`live_proof_surfaces.py`) parses `live-proof-surfaces.md`'s table into a lookup of `(station, surface, surface_globs, how_to_prove, cost)`. Given a set of changed paths, it matches them against the row's hand-authored **Surface globs** column and nothing else — never a keyword pulled from the prose — and reports an advisory Finding for every catalogued surface a changed path matches, quoting the catalog's own "how to prove it live" cell verbatim. A row with an empty globs cell is never diff-matched. A surface whose catalog row says no mechanism exists yet reports that honestly — never invents one. *Amended 2026-09-20 after run `pyforge-doctor-20260919T233255320Z-8f2b958e` halted on an intent gap (four review layers, one reproduction): the first attempt's bare-substring fallback for the three path-less rows matched `docs/how-to/ocp-cluster-bringup.md`, `docs/how-to/presentation-deck.md` and `recipes/docker/recipe.yaml`. The companion now carries the column (all eight rows); the saved attempt at `implementation-artifacts/26-1-live-proof-surface-attempted-change.patch` has a reusable parser and wiring and an unusable matcher.*
## Boundaries & Constraints

**Always:**
- The finding is always `status=warn`, never `fail` — matches AD-2's operability-not-policy posture and CAP-77's own constraint.
- The proof-step text in a finding is quoted verbatim from `live-proof-surfaces.md`, never re-derived or paraphrased.
- The catalog is the single source of truth — adding a new live-proof surface means editing `live-proof-surfaces.md`, not hardcoding a second list in the source module.
- `Source` enum gains exactly one new member (`LIVE_PROOF_SURFACE`), extending AD-3's closed taxonomy.
- **Zero false positives against the live tree is a hard, testable gate:** a test walks `git ls-files` of the real repo against every row's globs and asserts each hit sits under the row's own station (or the named cross-station paths for the container row); a keyword, substring or fuzzy match of any kind is out.
- The `Surface globs` column is the only matching input; a row with an empty cell is catalogued but never diff-matched.

**Never:**
- Do not fabricate a live-proof mechanism for the atlas Chromium/DuckDB/WASM row (the catalog's own named gap) — the finding for that row states plainly no mechanism is documented yet.
- Do not gate a PR on this finding — advisory only, per CAP-77's own constraint and this Spec's AD-2.
- Do not duplicate the catalog's content into the source module's own docstrings or constants — parse the one tracked file.
- Do not derive path patterns from the prose cells (station name, surface name, "how to prove") — the first attempt did, and it matched unrelated tracked files.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR touches `mcp_transport.py` | changed path under herald's Design MCP bridge glob | warn Finding naming herald's Claude Design bridge, quoting `--prove` as the proof step | none |
| PR touches `docsite/build.py` only | no changed path matches any catalogued surface | zero `LIVE_PROOF_SURFACE` findings | none |
| PR touches `docs/how-to/ocp-cluster-bringup.md`, `docs/how-to/presentation-deck.md`, `recipes/docker/recipe.yaml` | the first attempt's three false positives | zero `LIVE_PROOF_SURFACE` findings (regression fixture) | none |
| a catalog row with an empty `Surface globs` cell | changed paths anywhere | that row never fires | none |
| PR touches atlas's Chromium/DuckDB glob | changed path matches the no-mechanism-yet row | warn Finding stating no documented live-proof mechanism exists for this surface | none |
| `live-proof-surfaces.md` malformed/unparseable | catalog file present but table structurally broken | Finding-gathering degrades to a single warn naming the parse failure, never a crash | warn, fail-open |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-77`.
Companion (matching input, hand-authored): `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md` — its `Surface globs` column (added 2026-09-20).
Companion: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/live_proof_surfaces.py` (new), `models.py` (Source enum), `report-schema.json`, `__main__.py` (DISPATCH + REGISTRY), `scripts/detectors.py` (detectors-ci row), doctor unit tests.
Ledger key: `26-1-a-touched-live-proof-only-surface-gets-an-advisory-doctor-finding-naming-it`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-26-1-a-touched-live-proof-only-surface-gets-an-advisory-doctor-finding-naming-it.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 13 findings — high 4, medium 1, low 8, false 0, maybe-false 0
- findings:
  - `[high]` `[intent_gap]` Blind Hunter: the keyword-fallback path-matching heuristic (`_row_globs`/`_keywords`/`_row_match`) is a bare case-insensitive substring match against generic single English words pulled from a row's `Surface` column, with no notion of relatedness beyond that. Verified independently against the real tracked catalog and real tracked repo paths: scribe's "Postgres+pgvector cluster" row's fallback token `cluster` matches `docs/how-to/ocp-cluster-bringup.md`; herald's "`deck sync-all` idempotency" row's token `deck` matches `docs/how-to/presentation-deck.md`; the `guild-container` row's token `docker` matches `recipes/docker/recipe.yaml`. 3 of 8 real catalog rows depend entirely on this fallback (no explicit path token in any cell). Word-boundary tightening does not fix this — in each reproduced case the matched word is already a whole path segment (`cluster`, `deck`, `docker` are literally the filename/dirname), so the defect is architectural (single generic dictionary words as match keys), not a small regex guard.
  - `[low]` `[intent_gap]` Blind Hunter: no test in the diff exercises the false-positive risk of the keyword fallback — the one fallback test (`test_row_match_keyword_fallback_substring_match`) only covers the synthetic fixture's deliberately distinctive true-positive case (`chromium`/`duckdb`/`wasm`), so the regression above would not be caught by the suite as shipped. Shares root cause with the row above.
  - `[high]` `[intent_gap]` Edge Case Hunter: same defect (bare substring, no word-boundary or relatedness check) reproduced independently against real tracked paths (`docs/dreams/...`, `.github/workflows/sync-pypi-mappings.yml`-style examples). Shares root cause and evidence with the row above.
  - `[low]` `[intent_gap]` Edge Case Hunter: a catalog row whose four cells hold no path-like backtick token AND whose `Surface` text words are all short/stopword-filtered would silently produce an empty `path_globs` tuple with nothing flagging it — verified by code inspection (`_row_globs` returns `_keywords(surface)` unguarded; `parse_catalog` never validates non-empty `path_globs`). Not reachable against today's tracked catalog (all 8 real rows currently yield a non-empty token set), but a real, demonstrated code-path for a future row. Flip side of the same underlying design gap: the derivation heuristic for `path_globs` has no validated middle ground between "too broad" (the row above) and "silently dead."
  - `[high]` `[intent_gap]` Verification Gap Reviewer (pre-verified): same defect, independently reproduced with three concrete real-file examples (`docs/how-to/ocp-cluster-bringup.md` via scribe's `cluster`; `docs/how-to/presentation-deck.md` via herald's `deck`; `recipes/docker/recipe.yaml`, `recipes/docker-py/recipe.yaml`, `recipes/dockerfile-parse/meta.yaml` via guild-container's `docker`). Filed disposition was `patch` (add a negative-case test + tighten matching); triage judgment (see below) is that no bounded patch closes this without reopening the Edge Case Hunter's dead-row failure mode in the opposite direction, so it routes with its sibling rows instead.
  - `[high]` `[intent_gap]` Intent Alignment Auditor: the Approach paragraph and I/O & Edge-Case Matrix are written and tested against exactly two "clean" catalog rows (herald's explicit backtick path; atlas's honest named-gap row) — the diff's actual matching surface is broader and fuzzier, with 3 of 8 real rows depending entirely on an un-bounded keyword-substring fallback that neither the code comments nor the test suite acknowledge as the majority mechanism for rows lacking a natural path field. Same root cause and consequence as the four rows above.
  - `[medium]` `[patch]` Blind Hunter: `parse_catalog`'s naive `stripped[1:-1].split("|")` cell-splitting silently drops a row whose `how_to_prove` (or any) cell contains an unescaped literal `|` (e.g., a shell pipe in a documented live-proof command) — reproduced directly: a 2-row fixture with one row containing `` `cmd1 | grep foo` `` parses to 1 row with the affected row silently vanishing, no error or warning. Not currently triggered by the tracked catalog (no cell today contains an unescaped `|`), but a realistic future-edit risk given this catalog documents literal shell commands. Rejected as an immediate fix in this pass — see disposition below (moot under the cascade rule).
  - `[low]` `[reject]` Blind Hunter: header-row detection (`cells[0].lower() == "station"`) would misparse the header as a data row if the column were ever reworded — real but the correct fix (position-based first-row detection) is more than a direct correction, and a header-wording change is unlikely in everyday use. Rejected per the low-severity rule.
  - `[low]` `[patch]` Blind Hunter: `_row_match`'s docstring claims it returns "the first changed path (in `changed_paths` order)" but the implementation loops path_globs outer / changed_paths inner, so result order actually follows token order, not changed-path order. Direct docstring correction — not applied in this pass, moot under the cascade rule.
  - `[low]` `[patch]` Blind Hunter: `_changed_paths`'s docstring claims it "mirrors `sources/frozen_path.py`'s own `_changed_paths` exactly," but `frozen_path.py` returns a `set[str]` while this module returns a `sorted(list(...))` — a reasonable behavior choice (deterministic match order) but a misleading "exactly." Direct docstring correction — not applied in this pass, moot under the cascade rule.
  - `[low]` `[patch]` Blind Hunter: the catalog's relative path is hand-duplicated as an independent literal in both the module (`_CATALOG_RELATIVE`) and the test file (`_CATALOG_PATH`) instead of the test importing the module's own constant — verified this narrowly undercuts the module's own "single source of truth" principle: a future rename would cause `test_live_repo_catalog_parses_and_has_every_known_row`'s `pytest.skip` guard to silently start skipping rather than failing loudly (the tmp-repo fixture tests would fail loudly instead). Direct fix (import the constant) — not applied in this pass, moot under the cascade rule.
  - `[low]` `[defer]` Blind Hunter: `scripts/detectors.py`'s `_run_doctor_sources` docstring and a nearby comment still say "the ten ported Doctor sources," which is already stale independent of this diff — verified `_DOCTOR_SOURCE_TASKS` had 23 entries at baseline (pre-diff) and this diff's own addition only takes it to 24; the staleness predates this story and is not caused by it.
  - `[low]` `[patch]` Blind Hunter: `path_globs` is a misleading field/contract name — neither the dataclass field nor `_row_match` interprets actual glob syntax (`*`, `**`, `?`); a real glob authored in a future catalog row (e.g. `` `src/**/mcp_transport.py` `` ) would never match anything, silently making that row permanently dead. A rename (e.g. to `path_tokens`) is mechanical, not applied in this pass, moot under the cascade rule.

**Cascade disposition:** an `intent_gap` group exists (the six rows above sharing the keyword-fallback root cause), so per the workflow's cascade rule all lower-priority entries (the `patch` and `defer` rows) are moot this pass — none were applied. The attempted implementation was reverted in full (see below); only this spec file's own status/log/frontmatter changes remain.

## Auto Run Result (run `pyforge-doctor-20260919T233255320Z-8f2b958e`, superseded by the 2026-09-20 amendment — kept as the record)

Status: blocked
Blocking condition: intent gap

**Summary:** Implementation was attempted in full and passed every verification gate (`pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 1862 passed, 1 skipped; the full `pyforge-station-tests` fleet sweep: pyforge-core + all 8 stations green; `spec-surface-check` clean after reconcile; `environment.yaml` unaffected). Independent 4-layer review (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor) converged — independently, with concrete reproductions against the real tracked catalog and real tracked repo paths — on a `high`-severity design gap the Spec's own `<intent-contract>` does not settle: the `<intent-contract>`'s Approach and I/O & Edge-Case Matrix are written and tested against exactly two "clean" catalog rows (an explicit backtick path; the atlas named-gap row), but 3 of the catalog's 8 real rows (scribe's Postgres cluster, herald's `deck sync-all` idempotency, the cross-station `guild-container` row) have no natural per-row path/glob field at all. The implementation filled that gap with a generic keyword-substring fallback that is demonstrably unsound on data already in this exact repository (`cluster`→`docs/how-to/ocp-cluster-bringup.md`, `deck`→`docs/how-to/presentation-deck.md`, `docker`→`recipes/docker/recipe.yaml`, all real tracked files, all unrelated to the matched surface) — and tightening the heuristic (e.g. word-boundary matching) does not fix it, since the offending words are already whole path segments. The Edge Case Hunter separately showed the opposite failure mode is equally reachable: a sparse enough `Surface` column silently produces a permanently-unmatchable row. Per the workflow's routing rule (root cause inside `<intent-contract>`, no single defensible reading resolves it), this routes to `intent_gap`, not `bad_spec` or `patch`: there is no bounded code-only fix, only a genuine design choice among differently-flawed options (see Unresolved Questions below), and the current spec content does not pick one.

**Unresolved questions (for the operator / a future planning pass):**
1. For a catalog row with a real, documented proof mechanism but no natural per-row path/glob field (scribe's Postgres+pgvector cluster, warden's live OSV/CISA-KEV/EPSS feeds, `guild-container`) — should the source (a) never auto-match these rows at all (treat them like atlas's honest "no mechanism" row, i.e., advisory-only, never diff-triggered), (b) require `live-proof-surfaces.md` itself to be extended with an explicit, hand-authored path/glob column per row (a tracked-catalog schema change), or (c) adopt a materially stricter automatic heuristic (e.g. multi-keyword conjunctive matching, or a curated per-row keyword allowlist distinct from generic English-word extraction)? Each has different, real tradeoffs: (a) is always-silent for those rows even on a genuinely relevant change; (b) is precise but changes the catalog's own tracked structure and requires ongoing hand-authoring; (c) reduces but does not eliminate false-positive risk and adds complexity the current Spec never asked for.
2. Should the Story's acceptance bar require zero false positives against the *current* catalog + *current* repo tree as a hard, testable gate before this ships (the shipped heuristic fails that bar today, as demonstrated above), given the source's entire value proposition is being a *trustworthy* fleet-wide advisory?

**Files changed:** none remain — the attempted implementation (new module `live_proof_surfaces.py`, its unit tests, and all wiring in `models.py`, `sources/__init__.py`, `sources/__main__.py`, `report-schema.json`, `scripts/detectors.py`, `pixi.toml`, `tests/unit/test_models.py`, `tests/unit/test_sources_dispatch.py`, `tests/meta/test_source_independence.py`, both co-governor `.memlog.md` files, and `scripts/.spec-surface-baseline.json`) was fully reverted to `baseline_revision` per the `intent_gap` protocol. Only this spec file's `status`, `baseline_revision`, this Review Triage Log, and this Auto Run Result section remain changed.

**Saved attempted change:** `_bmad-output/implementation-artifacts/26-1-live-proof-surface-attempted-change.patch` (unified diff of the full attempted implementation against `baseline_revision`, for reference — this file is Tier-3/gitignored, not tracked).

**Verification performed:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (1862 passed, 1 skipped) and the full `pixi run -e pyforge-guild pyforge-station-tests` fleet sweep (pyforge-core + all 8 stations, exit 0) both ran green on the attempted implementation before review; `pixi run -e pyforge-guild spec-surface-check` was clean after reconcile. After the revert, `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` was re-run and confirmed back to the pre-story baseline (1825 passed, 1 skipped, matching `baseline_revision`'s own count).

**Residual risks:** none from shipped code — nothing from this story shipped. The design gap identified above is real and will recur if a future attempt at this story does not first resolve the Unresolved Questions.

**Follow-up review recommendation:** `false` — not applicable; this pass did not reach a `done` state.

