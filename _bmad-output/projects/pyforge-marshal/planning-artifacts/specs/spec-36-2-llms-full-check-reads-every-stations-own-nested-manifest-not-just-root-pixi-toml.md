---
title: '36.2: `llms-full-check` reads every station''s own nested manifest, not just root pixi.toml'
type: 'feature'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `llms-full-check` reads every station's own nested manifest, not just root pixi.toml (contract recovered from epics.md Intent + ACs).

**Approach:** `scripts/llms_full_check.py` (`STATION_MANIFESTS`, `station_run_deps()`, `run()`), `tests/scripts/test_llms_full_check.py` (new)

Ledger key: `36-2-llms-full-check-reads-every-stations-own-nested-manifest-not-just-root-pixi-toml`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / S-36.1.

### Living CAP citations

- Cited from epics.md: `spec-library-catalog-manifest-sync` CAP-2

## Acceptance Criteria

- Given `manifest_deps()` only ever walked root `pixi.toml`, so a station declaring a real run-dep only in its own `pixi.toml [package.run-dependencies]` would never be flagged as undocumented no matter how long it went unmirrored When `station_run_deps()` parses every `src/shared/packages/pyforge-*/pixi.toml`'s `[package.run-dependencies]` table (same path-dep handling as the existing root-manifest walk) and `run()` merges it into the same active-dependency set Then a synthetic station-manifest-only entry is caught as `undocumented-dep` (`tests/scripts/test_llms_full_check.py::test_run_flags_a_station_only_dep_as_undocumented`), and once mirrored + documented the same fixture reports clean (`::test_run_stays_clean_when_station_dep_is_mirrored_and_documented`) And the pre-existing root-pixi.toml-only behavior, the exit-code contract (0/1/2), and the `--json` flag are all unchanged — proven by `::test_no_station_manifests_falls_back_to_root_only_behavior` and a full clean run against the real repo (`pixi run -e local-recipes llms-full-check`, 352 active deps / 320 catalog entries, zero findings) And turning the scan on against the real repo immediately surfaced Story 36.1's own `filelock` scoping miss — the new capability catching a gap in the story that shipped one commit before it, the exact self-detection this Epic exists for

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `manifest_deps()` only ever walked root `pixi.toml`, so a station declaring a re | `station_run_deps()` parses every `src/shared/packages/pyfor | a synthetic station-manifest-only entry is caught as `undocumented-dep` (`tests/ | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 36.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `36-2-llms-full-check-reads-every-stations-own-nested-manifest-not-just-root-pixi-toml: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
