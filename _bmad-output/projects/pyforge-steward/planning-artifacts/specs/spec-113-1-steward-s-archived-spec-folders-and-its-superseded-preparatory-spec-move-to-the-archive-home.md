---
title: "113.1: Steward's archived Spec folders and its superseded preparatory spec move to the archive home"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
---

<intent-contract>

## Intent

**Problem:** CHAIN-STANDARD § 11 (`spec-one-chain-per-station` CAP-11) puts everything the fleet retires at `archive/<original path>`, yet at main `97c8211773` two `status: archived` Spec folders (`spec-htap-query-plane`, absorbed 2026-08-26; `spec-pyforge-steward-feedstock-maintenance`, retired 2026-08-02) and one superseded preparatory spec with no ledger key (`spec-22-prep-atlas-kedro-cli-introspection.md`, superseded 2026-09-10 by atlas Story 24.3) still sat under the station `specs/` directory, where only the station Spec, its declared seams, the absorbed folders and `spec-<E>-<S>-<slug>.md` story specs belong (§ 1).

**Approach:**
- `git mv` each folder, with its `.memlog.md`, and the loose file to `archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/<same name>`; no text changes.
- Prune `docs/governance/chain-sprawl-baseline.json` with `scripts/chain_sprawl_baseline.py --prune` (the two folders).
- Re-point the live pointers: `planning-artifacts/specs/README.md` (the `spec-htap-query-plane` line) and `src/shared/packages/pyforge-core/README.md` (its preparatory-story sentence names the live `PREPARATORY_UNINTROSPECTABLE` entry, atlas Story 24.3's spec); dated records that name the old paths (Story 22.1's spec, the 2026-09-14 identifier research) stay as written.

Ledger key: `113-1-steward-s-archived-spec-folders-and-its-superseded-preparatory-spec-move-to-the-archive-home`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / XS / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-11** (one archive home): `archive/<original path>`, structure-preserving, `git mv`, nothing deleted.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): an archived Spec folder travels with its memlog.

## Acceptance Criteria

- **AC1 — Three renames, no deletion.** `git diff --stat -M` against `97c8211773` shows the two folders' `SPEC.md` + `.memlog.md` and the loose file as renames into `archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/`; no file is deleted and no moved file's text changes.
- **AC2 — The station directory.** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` holds no `SPEC.md` reading `status: archived` and no `spec-<slug>.md` that is neither a Spec folder nor a story spec.
- **AC3 — The baseline.** `docs/governance/chain-sprawl-baseline.json` no longer lists the two folders; `chain-sprawl-check` exits 0.
- **AC4 — Detectors.** `spec-surface-check` (after the scoped stamps), `governance-currency`, `fold-complete-check`, `bmad-drift-check` and `detectors-ci` exit 0; the moved Specs' `owner-dream:` paths resolve.

## Boundaries & Constraints

**Always:**
- Move by `git mv`; keep the moved files byte-identical; name every moved path in the station memlog.

**Never:**
- Never delete a retired artifact; never mint a story key for the preparatory spec after the fact; never hand-edit `SPEC.md`; never move the archived Specs' Dreams out of `docs/dreams/` here (the archived-Dreams move is its own task).

## I/O & Edge-Case Matrix

| Path | Before | After |
|---|---|---|
| `planning-artifacts/specs/spec-htap-query-plane/` (`SPEC.md`, `.memlog.md`) | under the station directory, `status: archived` | `archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-htap-query-plane/` |
| `planning-artifacts/specs/spec-pyforge-steward-feedstock-maintenance/` (`SPEC.md`, `.memlog.md`) | under the station directory, `status: archived` | `archive/.../specs/spec-pyforge-steward-feedstock-maintenance/` |
| `planning-artifacts/specs/spec-22-prep-atlas-kedro-cli-introspection.md` | loose, `status: superseded`, no ledger key | `archive/.../specs/spec-22-prep-atlas-kedro-cli-introspection.md` |
| `docs/governance/chain-sprawl-baseline.json` | lists the two folders | pruned |
| `planning-artifacts/specs/README.md`, `src/shared/packages/pyforge-core/README.md` | name the old path / the superseded prep spec | name the archive path / the live entry |

</intent-contract>

## Binding

- Parent capability: `spec-one-chain-per-station` CAP-11; CAP-3 for the folder-with-memlog rule.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-26 entry (planning artifacts outside the one-chain shape).
- Epic: Epic 113, minted with this story.
- Ledger key: `113-1-steward-s-archived-spec-folders-and-its-superseded-preparatory-spec-move-to-the-archive-home`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR with warden 21.1 and marshal 109.1 (the one-chain residue effort).

## Verification

**Commands:**
- `git diff --stat -M 97c8211773 -- _bmad-output/projects/pyforge-steward/planning-artifacts/specs archive/_bmad-output/projects/pyforge-steward` — expected: renames only (AC1).
- `grep -l '^status: archived' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/*/SPEC.md` — expected: no output (AC2).
- `pixi run -e pyforge-guild chain-sprawl-check` — expected: exit 0 (AC3).
- `pixi run -e pyforge-guild spec-surface-check && pixi run -e pyforge-guild governance-currency && pixi run -e pyforge-guild fold-complete-check && pixi run -e pyforge-guild bmad-drift-check && pixi run -e pyforge-guild detectors-ci` — expected: each exit 0 (AC4).

## Auto Run Result

Status: done (built 2026-10-26 in the one-chain residue PR with warden 21.1 and marshal 109.1). Three renames (`git mv`), no deletion, no text change in a moved file; `chain-sprawl-baseline.json` pruned of the two folders; the two live pointers re-pointed; every named detector exit 0 on the tip.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (planning artifacts outside the one-chain shape), on the 2026-10-26 re-audit of the one-chain rule.
