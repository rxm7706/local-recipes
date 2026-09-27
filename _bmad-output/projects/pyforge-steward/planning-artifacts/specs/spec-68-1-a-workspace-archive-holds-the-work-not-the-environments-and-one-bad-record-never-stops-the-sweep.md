---
title: '68.1: A workspace archive holds the work, not the environments, and one bad record never stops the sweep'
type: 'fix'
created: '2026-09-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward workspace clean` archives a worktree by tarring all of it, `.pixi/envs` included — ~13 GB in a worktree that has run `pr-preflight` — so `.steward/workspace-archive/` in the primary checkout reached 75 GB in 62 archives (2026-09-27). And a fleet `clean --merged-only` raises on the first record whose branch no longer exists (`git merge-base --is-ancestor steward-pyforge-guild-env origin/steward-guild-env-frames-regrounding` → exit 128): the sweep stops, no later record is examined, and because the record was popped from `pending` before the check, the `finally` that saves bookkeeping keeps neither it nor its reason — the failing row is silently deleted.

**Approach:** a `tarfile` filter in `_archive_worktree` drops `REINSTALLABLE_ENV_DIRS` (`.pixi/envs`, `.pixi/solve-group-envs`) and everything beneath them; every other file, the tracked `.pixi/config.toml` included, archives as before. In `clean_workspaces` each record's decision and archive run inside a per-record `try`: a `WorkspaceError` (the merge check, or `_archive_worktree`, which already wraps every `OSError`) becomes a `skipped` row with reason `error: <message>`, the record goes back to `remaining`, and the sweep continues.

Ledger key: `68-1-a-workspace-archive-holds-the-work-not-the-environments-and-one-bad-record-never-stops-the-sweep`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-155 (extends CAP-107, absorbed from `spec-scratch-worktree-lifecycle` CAP-4).

## Acceptance Criteria

- Given a worktree with a populated `.pixi/envs` and `.pixi/solve-group-envs` When `workspace clean` archives it Then the archive holds its files and `.pixi/config.toml` and no member under either env dir
- Given bookkeeping with a record whose branch no longer exists ahead of a merged record When `workspace clean --merged-only` sweeps the fleet Then the merged record is archived, the stale one is reported skipped with its git error, and the stale record is still in bookkeeping afterwards
- Given any `WorkspaceError` during one record When the sweep runs Then no record is lost from bookkeeping and later records are still examined

## Boundaries & Constraints

**Always:** archive-not-delete stands — the work still archives; only reinstallable env dirs are left out. A record the sweep cannot decide is kept, never dropped.

**Never:**
- Do not delete a worktree without archiving its non-env content.
- Do not change `--merged-only` semantics (merged into the record's own `source`).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| env dirs present | `.pixi/envs`, `.pixi/solve-group-envs`, `.pixi/config.toml` | archive has config, not the env dirs | none |
| name that merely starts with `envs` | `.pixi/envs-notes.txt` | archived (not an env dir) | none |
| stale record first | branch gone, then a merged record | merged archived; stale skipped `error: …`, kept | sweep continues |
| archive write fails | `OSError` inside `_archive_worktree` | wrapped `WorkspaceError` → skipped, kept | sweep continues |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-155.
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 (later) — Proposed: housekeeping that leaks, and a gate that re-checks what `main` already checked*.
Ledger key: `68-1-a-workspace-archive-holds-the-work-not-the-environments-and-one-bad-record-never-stops-the-sweep`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- A worktree that ran `pr-preflight` archives in seconds at a few hundred MB instead of multiple GB.
