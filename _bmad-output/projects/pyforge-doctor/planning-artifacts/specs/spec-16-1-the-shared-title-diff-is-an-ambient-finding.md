---
title: 'The shared-title diff is an ambient finding'
type: 'feature'
created: '2026-08-22'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** A sibling PyForge tree (OpenTeams mgmt-wf) shares this repo's Dream convention — 13/15 titles overlap, owners already diverge (their deck work = scribe; ours = herald) — and nothing names that drift.

**Approach:** Add a new warn-only doctor source that diffs shared dream titles (local `docs/dreams/` vs the sibling's via the operator token) on status, owner, and content-hash, and pass WARN findings through `doctor check` plus fleet-picture ATTENTION the same way Story 15.2 rides those surfaces.

## Boundaries & Constraints

**Always:**
- Read-only. Compare fingerprints only: `title`, `status`, `owner`, sha256 of the body after the closing `---` fence. Discard sibling bytes immediately; never write them to disk, caches, or Finding.evidence.
- Match on stripped frontmatter `title:` (filename is not the key — 8 of 13 shared titles used different filenames). Skip a file with no usable title.
- Shared titles that agree on all three axes produce no Finding. Sibling-only and local-only titles produce none.
- One WARN Finding per diverging shared title, `check="sibling-dreams-drift"`, never FAIL. Evidence may hold title + axis names + local/sibling status/owner/hash strings only.
- No token (`GH_TOKEN` then `GITHUB_TOKEN`, first non-empty) → `gather()` returns `()` with no error. Unreachable sibling, HTTP/timeout/parse failure → same fail-open empty result (never a degrade WARN that would spam ATTENTION).
- Fetch only `OpenTeams-WFT-CDO/mgmt-wf-python-modernization` `docs/dreams/` via unauthenticated-shape GitHub Contents API plus `Authorization: Bearer <token>`. Stdlib `urllib` only. Shared deadline `_SIBLING_FETCH_TOTAL_BUDGET_SECONDS = 10.0`.
- New `Source.SIBLING_DREAMS_DRIFT` (`sibling-dreams-drift`), own module, REGISTRY + DISPATCH + `SOURCE_MODULE` row. `scope="repo"`, `subject_station="fleet"`, `owning_station="doctor"`.
- Opt-in `doctor check --sibling-dreams` (never the zero-flag default — live GitHub call vs NFR-4), same narrowing/scope rules as `--bmad-core`. Fleet-picture ATTENTION always probes WARNs and degrades to one "could not check" line.
- Wrap `gather()` in `degrade_on_exception` so unexpected exceptions become one WARN (CLI/DISPATCH safety); the fetch/token miss path itself stays empty, not that wrapper.

**Block If:** None.

**Never:**
- Sync, import, or watch any other repo. No new CLI verb. No sibling prose in fixtures — titles/hashes/status/owner only. Do not persist fetched bodies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 2026-08-22 demonstrated drift | Shared title (local deck dream title), local `owner=herald`, sibling snapshot `owner=scribe` (and/or status or hash differ) | One WARN `sibling-dreams-drift` naming that title and the diverging axes | n/a |
| Trees agree | Shared title, equal status/owner/hash | No Finding | n/a |
| No token | Env has neither `GH_TOKEN` nor `GITHUB_TOKEN` | `()` | Silent |
| Offline / unreachable | Token present, Contents API `URLError`/timeout/non-2xx | `()` | Fail-open, silent |
| Sibling-only or local-only title | Title in one tree only | No Finding | n/a |
| Unreadable local `docs/dreams/` | Missing/unreadable dir | `()` | Fail-open |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — append `SIBLING_DREAMS_DRIFT = "sibling-dreams-drift"` after `BACKLOG_INTAKE` (~201), comment: Epic 16 / spec-sibling-dreams-drift CAP-1; warn-only; fleet subject.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` — NEW. Local scan of `target/docs/dreams/*.md`; `_operator_token`; `_fetch_sibling_fingerprints` (Contents API list + file GETs, in-memory parse, drop bodies); `_diff_shared_titles`; `gather` via `degrade_on_exception`. Reuse the local frontmatter-fence discipline from `hygiene.py::_dream_frontmatter_status` (copy, do not import). Hash: sha256 hex of UTF-8 body after closing fence (empty body → hash of `b""`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — REGISTRY row after BACKLOG_INTAKE; import stays lazy-free (registration is data-only).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` — `DISPATCH[Source.SIBLING_DREAMS_DRIFT.value] = sibling_dreams.gather`; import `sibling_dreams`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — `_CATEGORY_SOURCE["sibling-dreams"]`; `--sibling-dreams` flag; `_gather_sibling_dreams`; `_run_check` opt-in + explicit-flag narrowing (copy `--bmad-core` at ~668–712); `_validate_scope_against_explicit_categories` tuple (~411–416).
- `scripts/fleet_picture.py` — `sibling_dreams_drift_findings()` mirroring `bmad_core_drift_findings` (subprocess `python -m pyforge.doctor.sources sibling-dreams-drift --json`, filter `status==warn`, timeout=20); ATTENTION `try` after the dream-chain probe (~504) appends `{check}: {message}` truncated like bmad-core.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` — NEW. Stub fetch/token; 2026-08-22 owner-axis fixture; agree/no-token/offline/one-sided cases.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` — add expected row.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` — `--sibling-dreams` suite cloned from the `--bmad-core` block (~166–320).
- `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py` — `SOURCE_MODULE[Source.SIBLING_DREAMS_DRIFT] = "sibling_dreams.py"`.
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_sibling_dreams_drift.py` — NEW, clone `test_fleet_picture_bmad_core_drift.py` against the new helper.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- add Source member -- closed taxonomy must extend, not open.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py` -- implement gather + fail-open fetch -- CAP-1 surface.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- register Source -- REGISTRY↔Source equality.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py` -- DISPATCH row -- fleet-picture subprocess name.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- opt-in `--sibling-dreams` -- doctor report surface, NFR-4 safe.
- `scripts/fleet_picture.py` -- ATTENTION probe -- ambient watch line.
- Tests listed in Code Map -- cover the I/O matrix + wiring.

**Acceptance Criteria:**
- Given local `docs/dreams/` and a sibling snapshot of the 2026-08-22 owner split (shared deck title: local herald vs sibling scribe), when `gather()` runs, then a warn-only Finding names that title and the owner axis, and no sibling prose is stored.
- Given no operator token or an unreachable sibling, when `gather()` runs, then the result is empty and no error is raised.
- Given agreeing shared titles, when `gather()` runs, then no Finding is emitted.
- Given a WARN Finding from this source, when `doctor check --sibling-dreams` or fleet-picture ATTENTION runs, then the finding appears on that surface; the default `doctor check` does not call this gather.

## Spec Change Log

## Review Triage Log

## Design Notes

Sibling is hardcoded to the one named repo in the Dream — a registry is a non-goal. Token names follow `gh` (`GH_TOKEN`, then `GITHUB_TOKEN`). Content-hash is body-only so a status/owner-only edit is an axis diff, not a hash diff. Empty-on-miss (not degrade WARN) keeps ATTENTION quiet offline, matching CAP-1 "offline yields nothing."

Fixture title: use this repo's licensed deck-dream `title:` string plus synthetic sibling fingerprints — never sibling file text.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3bb7a56939` (2026-08-22, "Merge pull request #633 from rxm7706/doctor/16-1-shared-title-diff-ambient"). Ledger row `16-1-the-shared-title-diff-is-an-ambient-finding: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_sibling_dreams_drift.py`, `scripts/fleet_picture.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py`, `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_models.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` (+1 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
