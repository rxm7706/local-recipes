---
title: "21.1: Warden's archived compliance-gates Spec folder moves to the archive home"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
---

<intent-contract>

## Intent

**Problem:** CHAIN-STANDARD § 11 (`spec-one-chain-per-station` CAP-11) puts everything the fleet retires at `archive/<original path>`, yet at main `97c8211773` the `status: archived` Spec folder `spec-pyforge-warden-compliance-gates` (retired 2026-08-02 as a duplicate; a retirement record) still sat under the station `specs/` directory, where only the station Spec, the absorbed folders and `spec-<E>-<S>-<slug>.md` story specs belong (§ 1).

**Approach:**
- `git mv` the folder, with its `.memlog.md`, to `archive/_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden-compliance-gates/`; no text changes.
- Prune `docs/governance/chain-sprawl-baseline.json` with `scripts/chain_sprawl_baseline.py --prune`.
- The Dream `docs/dreams/pyforge-warden-compliance-gates.md` and `docs/dreams/compliance-factory-web-face.md` name the Spec by stem, which still resolves; they stay as written.

Ledger key: `21-1-warden-s-archived-compliance-gates-spec-folder-moves-to-the-archive-home`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / XS / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-11** (one archive home): `archive/<original path>`, structure-preserving, `git mv`, nothing deleted.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): an archived Spec folder travels with its memlog.

## Acceptance Criteria

- **AC1 — Two renames, no deletion.** `git diff --stat -M` against `97c8211773` shows the folder's `SPEC.md` + `.memlog.md` as renames into `archive/_bmad-output/projects/pyforge-warden/planning-artifacts/specs/`; nothing deleted, no text changed.
- **AC2 — The station directory.** `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/` holds no `SPEC.md` reading `status: archived`.
- **AC3 — The baseline.** `docs/governance/chain-sprawl-baseline.json` no longer lists the folder; `chain-sprawl-check` exits 0.
- **AC4 — Detectors.** `spec-surface-check` (after the scoped stamp), `governance-currency`, `fold-complete-check`, `bmad-drift-check` and `detectors-ci` exit 0; the Spec's `owner-dream:` path resolves.

## Boundaries & Constraints

**Always:**
- Move by `git mv`; keep the moved files byte-identical; name both moved paths in the station memlog.

**Never:**
- Never delete a retired artifact; never hand-edit `SPEC.md`; never move the Dream out of `docs/dreams/` here (the archived-Dreams move is its own task).

## I/O & Edge-Case Matrix

| Path | Before | After |
|---|---|---|
| `planning-artifacts/specs/spec-pyforge-warden-compliance-gates/` (`SPEC.md`, `.memlog.md`) | under the station directory, `status: archived` | `archive/_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden-compliance-gates/` |
| `docs/governance/chain-sprawl-baseline.json` | lists the folder | pruned |

</intent-contract>

## Binding

- Parent capability: `spec-one-chain-per-station` CAP-11; CAP-3 for the folder-with-memlog rule.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-10-26 entry (planning artifacts outside the one-chain shape).
- Epic: Epic 21, minted with this story.
- Ledger key: `21-1-warden-s-archived-compliance-gates-spec-folder-moves-to-the-archive-home`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR with steward 113.1 and marshal 109.1 (the one-chain residue effort).

## Verification

**Commands:**
- `git diff --stat -M 97c8211773 -- _bmad-output/projects/pyforge-warden/planning-artifacts/specs archive/_bmad-output/projects/pyforge-warden` — expected: renames only (AC1).
- `grep -l '^status: archived' _bmad-output/projects/pyforge-warden/planning-artifacts/specs/*/SPEC.md` — expected: no output (AC2).
- `pixi run -e pyforge-guild chain-sprawl-check` — expected: exit 0 (AC3).
- `pixi run -e pyforge-guild spec-surface-check && pixi run -e pyforge-guild governance-currency && pixi run -e pyforge-guild fold-complete-check && pixi run -e pyforge-guild bmad-drift-check && pixi run -e pyforge-guild detectors-ci` — expected: each exit 0 (AC4).

## Auto Run Result

Status: done (built 2026-10-26 in the one-chain residue PR with steward 113.1 and marshal 109.1). Two renames (`git mv`), no deletion, no text change; `chain-sprawl-baseline.json` pruned of the folder; every named detector exit 0 on the tip.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (planning artifacts outside the one-chain shape), on the 2026-10-26 re-audit of the one-chain rule.
