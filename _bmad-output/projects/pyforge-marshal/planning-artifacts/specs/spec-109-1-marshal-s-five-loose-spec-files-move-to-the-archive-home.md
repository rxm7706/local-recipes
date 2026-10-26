---
title: "109.1: Marshal's five loose spec files move to the archive home"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
---

<intent-contract>

## Intent

**Problem:** CHAIN-STANDARD § 1 lets the station `specs/` directory hold the station Spec, its declared seams, the absorbed folders and `spec-<E>-<S>-<slug>.md` story specs; § 11 (`spec-one-chain-per-station` CAP-11) puts everything the fleet retires at `archive/<original path>`. At main `97c8211773` five loose `spec-<slug>.md` files sat there: `spec-code-audit-remediation-2026-07-26.md` (a 1,617-line Tier-2 Spec of the 2026-07-26 code audit, `status: ready`; its branch abandoned and its waves closed 2026-07-27 per its own closure stamp; the residual findings live as deferred-work rows and in the conda-forge-expert v8.81.0 retro), `spec-status-harness-run-id-poisoning.md` (2026-08-15; the ledger record is `spec-39-1-a-null-harness-run-id-recovers-by-filesystem-discovery.md`), `spec-marshal-land-cross-project-story-key-collision.md` (2026-08-15, direct commit `d7fd62707b`, no ledger key; its absorbed Spec folder stays), `spec-dispatch-tier-routing-fails-safe.md` (2026-09-12, direct commits `6113ac34f2` and `97ca64d1e3`, no ledger key; its absorbed Spec folder stays, Story 33.15 superseded its config values) and `spec-land-promote-isolation.md` (`status: in-progress` since 2026-09-02, delivered the same day by `21c29320a9`, no ledger key; Story 68.1 carries the live contract of `commit_paths_onto_remote_tip`).

**Approach:**
- `git mv` each file to `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/<same name>`. None is renamed to a story key: four never had one and the fifth is not a story spec.
- The audit Spec's frontmatter `status: ready` becomes `status: archived` with `archived-reason: superseded` (the one text change); the four story specs stay byte-identical.
- Re-point the live pointers: `docs/dreams/dispatch-tier-routing-fails-safe.md` (its "Story spec:" line) and `docs/reference/story-spec-flag-block.md` (its legacy-name example). Dated records naming the old paths (atlas Epic 10's note of 2026-07-27, steward's 2026-09-14 identifier research, the done story specs, this station's earlier memlog entries) stay as written; `tests/scripts/test_flag_rule.py`'s population test is name-only and unchanged.

Ledger key: `109-1-marshal-s-five-loose-spec-files-move-to-the-archive-home`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: chore / XS / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-11** (one archive home): `archive/<original path>`, structure-preserving, `git mv`, nothing deleted.
- **`spec-one-chain-per-station` CAP-3** (the station fold procedure): story specs are named by their ledger key; a record with no key is retired, not re-keyed.

## Acceptance Criteria

- **AC1 — Five renames, no deletion.** `git diff --stat -M` against `97c8211773` shows the five files as renames into `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/`; the four story specs are byte-identical and the audit Spec differs only in its `status:` / `archived-reason:` frontmatter lines.
- **AC2 — The station directory.** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/` holds no `spec-<slug>.md` that is neither a story spec (`spec-<E>-<S>-…`) nor a Spec folder's file.
- **AC3 — Pointers.** The two live pointers name the archive path; `pytest tests/scripts/test_flag_rule.py` passes.
- **AC4 — Detectors.** `spec-surface-check` (after the scoped stamp), `governance-currency`, `chain-sprawl-check`, `fold-complete-check`, `bmad-drift-check` and `detectors-ci` exit 0.

## Boundaries & Constraints

**Always:**
- Move by `git mv`; name every moved path in the station memlog; keep the story specs byte-identical.

**Never:**
- Never delete a retired artifact; never mint a story key after the fact for a fix that landed without one; never hand-edit `SPEC.md`; never edit a dated record to follow the move.

## I/O & Edge-Case Matrix

| Path (from `planning-artifacts/specs/`) | Before | After |
|---|---|---|
| `spec-code-audit-remediation-2026-07-26.md` | loose Tier-2 Spec, `status: ready` | `archive/.../specs/`, `status: archived`, `archived-reason: superseded` |
| `spec-status-harness-run-id-poisoning.md` | loose story spec beside `spec-39-1-…md` | `archive/.../specs/`, byte-identical |
| `spec-marshal-land-cross-project-story-key-collision.md` | loose story spec, no key | `archive/.../specs/`, byte-identical |
| `spec-dispatch-tier-routing-fails-safe.md` | loose story spec, no key | `archive/.../specs/`, byte-identical |
| `spec-land-promote-isolation.md` | loose story spec, `in-progress`, no key | `archive/.../specs/`, byte-identical |
| `docs/dreams/dispatch-tier-routing-fails-safe.md`, `docs/reference/story-spec-flag-block.md` | name the old path | name the archive path |

</intent-contract>

## Binding

- Parent capability: `spec-one-chain-per-station` CAP-11; CAP-3 for the story-key naming rule.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-26 entry (planning artifacts outside the one-chain shape).
- Epic: Epic 109, minted with this story.
- Ledger key: `109-1-marshal-s-five-loose-spec-files-move-to-the-archive-home`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR with steward 113.1 and warden 21.1 (the one-chain residue effort).

## Verification

**Commands:**
- `git diff --stat -M 97c8211773 -- _bmad-output/projects/pyforge-marshal/planning-artifacts/specs archive/_bmad-output/projects/pyforge-marshal` — expected: five renames (AC1).
- `ls _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/*.md | grep -vE 'spec-[0-9]+-[0-9]+-|README'` — expected: no output (AC2).
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_rule.py -q` — expected: pass (AC3).
- `pixi run -e pyforge-guild spec-surface-check && pixi run -e pyforge-guild governance-currency && pixi run -e pyforge-guild chain-sprawl-check && pixi run -e pyforge-guild fold-complete-check && pixi run -e pyforge-guild bmad-drift-check && pixi run -e pyforge-guild detectors-ci` — expected: each exit 0 (AC4).

## Auto Run Result

Status: done (built 2026-10-26 in the one-chain residue PR with steward 113.1 and warden 21.1). Five renames (`git mv`), no deletion; the audit Spec's two frontmatter lines are the only text change; the two live pointers re-pointed; the flag-rule population test and every named detector pass on the tip.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (planning artifacts outside the one-chain shape), on the 2026-10-26 re-audit of the one-chain rule.
