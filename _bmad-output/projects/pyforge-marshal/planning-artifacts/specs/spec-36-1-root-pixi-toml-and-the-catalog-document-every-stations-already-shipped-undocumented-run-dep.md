---
title: '36.1: Root pixi.toml and the catalog document every station''s already-shipped, undocumented run-dep'
type: 'fix'
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

**Problem:** Root pixi.toml and the catalog document every station's already-shipped, undocumented run-dep (contract recovered from epics.md Intent + ACs).

**Approach:** `pixi.toml` (`[feature.local-recipes.dependencies]` plus `[feature.pyforge-marshal.dependencies]`, `[feature.pyforge-mason.dependencies]`, `[feature.pyforge-warden.dependencies]`, `[feature.pyforge-doctor.dependencies]`, `[feature.pyforge-atlas.dependencies]`), `docs/reference/library-llms-full.md` (new § 1a, `pydantic` note sharpened)

Ledger key: `36-1-root-pixi-toml-and-the-catalog-document-every-stations-already-shipped-undocumented-run-dep`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Cited from epics.md: `spec-library-catalog-manifest-sync` CAP-1

## Acceptance Criteria

- Given `packaging`, `jsonschema`, `psutil`, `attrs`, `packageurl-python`, `license-expression`, and `filelock` are each already a direct run-dep of a station's own nested `pixi.toml [package.run-dependencies]` and already imported directly in that station's source, but none appears anywhere in root `pixi.toml` or the catalog When each is added to root `pixi.toml` — `[feature.local-recipes.dependencies]` plus the owning station's own feature block — floored at the version `pixi.lock` already resolves (`packaging` 26.3, `jsonschema` 4.26.0, `psutil` 7.2.2, `attrs` 26.1.0, `packageurl-python` 0.17.6, `license-expression` 30.4.4, `filelock` 3.32.0) Then `pixi lock --check` reports the lock file already up to date (no new solve required — the version was already resolved transitively) and `pixi run -e local-recipes llms-full-check` no longer reports any of the seven as `undocumented-dep` And the catalog's new § 1a documents all seven with their owning station(s) and import-name gotchas (`packageurl-python` imports as `packageurl`, `license-expression` as `license_expression`), and the existing `pydantic` note is sharpened to also name pyforge-atlas's and pyforge-scribe's direct declarations without adding a new root pin And `filelock` — found only after Story 36.2's own scan went live, a CAP-1 scoping miss (conflated with the separate marshal/scribe filelock *adoption* question in `spec-pyforge-unifying-strategy`'s Estate leverage table) — is folded into this story's own surface and Given/When/Then rather than deferred, since it is the identical class of gap

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `packaging`, `jsonschema`, `psutil`, `attrs`, `packageurl-python`, `license-expr | each is added to root `pixi.toml` — `[feature.local-recipes. | `pixi lock --check` reports the lock file already up to date (no new solve requi | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 36.1 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `36-1-root-pixi-toml-and-the-catalog-document-every-stations-already-shipped-undocumented-run-dep: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
