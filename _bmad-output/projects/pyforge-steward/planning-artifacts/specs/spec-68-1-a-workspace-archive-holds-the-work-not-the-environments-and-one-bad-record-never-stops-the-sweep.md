---
title: '68.1: A workspace archive holds the work, not the environments, and one bad record never stops the sweep'
type: 'fix'
created: '2026-09-27'
status: 'done'
review_loop_iteration: 2
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

**Approach:** a `tarfile` filter in `_archive_worktree` drops `REINSTALLABLE_ENV_DIRS` (`.pixi/envs`, `.pixi/solve-group-envs`, `.pixi/bld`) and everything beneath them; every other file, the tracked `.pixi/config.toml` included, archives as before. A tar that fails (an `OSError` or a `tarfile.TarError`) removes its partial archive and raises `WorkspaceError`. In `clean_workspaces` each record's decision and archive run inside a per-record `try`: a `WorkspaceError` becomes a `skipped` row with reason `error: <message>`, the record goes back to `remaining`, and the sweep continues; the record in flight is tracked, so the `finally` saves it back when any other exception escapes (a Ctrl-C at the confirm prompt). The clean duty exits non-zero when any row errored, whichever form ran (one slug, the fleet, or a repo set).

Ledger key: `68-1-a-workspace-archive-holds-the-work-not-the-environments-and-one-bad-record-never-stops-the-sweep`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-steward` CAP-155 (extends CAP-107, absorbed from `spec-scratch-worktree-lifecycle` CAP-4).

## Acceptance Criteria

- Given a worktree with populated `.pixi/envs`, `.pixi/solve-group-envs` and `.pixi/bld` When `workspace clean` archives it Then the archive holds its files and `.pixi/config.toml` and no member under any of the three dirs
- Given bookkeeping with a record whose branch no longer exists ahead of a merged record When `workspace clean --merged-only` sweeps the fleet Then the merged record is archived, the stale one is reported skipped with its git error and is still in bookkeeping, and the CLI exits non-zero
- Given a worktree holding an unreadable file When the sweep archives it Then no partial archive is left, the worktree stays, and the record stays with its error
- Given an interrupt at the confirm prompt When the sweep is running Then no record is lost from bookkeeping

## Boundaries & Constraints

**Always:** archive-not-delete stands — the work still archives; only reinstallable pixi dirs are left out. A record the sweep cannot decide is kept, never dropped.

**Never:**
- Do not delete a worktree without archiving its non-env content.
- Do not change `--merged-only` semantics (merged into the record's own `source`).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| env and build dirs present | `.pixi/envs`, `.pixi/solve-group-envs`, `.pixi/bld`, `.pixi/config.toml` | archive has config, none of the three dirs | none |
| name that merely starts with `envs` | `.pixi/envs-notes.txt` | archived | none |
| stale record first | branch gone, then a merged record | merged archived; stale skipped `error: …`, kept; exit non-zero | sweep continues |
| archive write fails | unreadable file in the worktree | no partial archive; worktree and record kept | `error: could not archive …` row |
| interrupt | `KeyboardInterrupt` at the confirm prompt | exception propagates; every record still in bookkeeping | — |
| interrupt mid-tar | `KeyboardInterrupt` while the archive is written | no partial archive; record kept; exception propagates | — |
| interrupt after the worktree is gone | `KeyboardInterrupt` during the best-effort branch delete | record kept; later `--merged-only` sweeps report it `error:` and exit non-zero | an interactive `clean <slug>` writes its `.missing.txt` marker and retires it |
| repo-set member errors | `clean <set> --merged-only`, one member's archive fails | other members cleaned; the failing member's `error:` row; exit non-zero | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-155.
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 (later) — Proposed: housekeeping that leaks, and a gate that re-checks what `main` already checked*.
Ledger key: `68-1-a-workspace-archive-holds-the-work-not-the-environments-and-one-bad-record-never-stops-the-sweep`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

### Review 1 — 2026-09-27, independent adversarial reviewer, commit `cda3257cff` — FAIL (the story pair: 1 high on 68.2, 2 medium here)

Verified clean: the tar filter's `None` stops recursion (CPython 3.14 `tarfile.py`); `.pixi/envs-notes.txt` kept; special-character arcnames fine; symlinked `.pixi` not followed; `remaining` keeps order without duplicates; `--merged-only` unchanged.

- `[medium]` `[patch]` **M1 — a non-`WorkspaceError` still dropped the in-flight record.** Only `WorkspaceError` was caught; the `finally` saved `remaining + pending`, and the popped record was in neither. Probe: Ctrl-C at the `[y/N]` prompt → bookkeeping lost the record while its worktree stayed on disk — no longer owned (CAP-108), never cleaned. **Fix:** the record in flight is tracked and the `finally` saves it back; `test_an_interrupt_mid_sweep_never_drops_the_record_in_flight`.
- `[medium]` `[patch]` **M2 — a failed archive left a partial `.tar.gz`, now once per sweep.** Keeping the failing record means each sweep retries it and wrote another timestamped partial archive (three 2 MB leftovers after three sweeps in the probe; root-owned files from `recipe-build-docker` are a plausible real trigger). **Fix:** a tar failure (`OSError` or `tarfile.TarError`) unlinks the partial archive and raises `WorkspaceError`; `test_a_failed_archive_leaves_no_partial_file_and_keeps_the_record`.
- `[low]` `[patch]` **L3 — an erroring clean exited 0.** **Fix:** the duty's `ok` is false when any skipped row carries `error:`; the sweep still finishes; `test_clean_via_cli_exits_failed_when_a_record_errored`.
- `[low]` `[patch]` **L5 — `.pixi/bld` still archived** (1.1 GB of 1.45 GB left in a measured archive; >2 GB in another). The path-dependency build cache is reinstallable. **Fix:** added to `REINSTALLABLE_ENV_DIRS`; the env-dirs test covers it.
- Test gap "AC3 / archive write fails had no test" — closed by M2's test.

### Review 2 — 2026-09-27, independent adversarial reviewer, commit `db044dad6a` — PASS with lows

Verified closed: M1 (a Ctrl-C at the prompt and during the best-effort `git branch -D` both keep the record), M2 for `OSError` / `TarError`, L3 for the one-slug and fleet forms, L5.

- `[low]` `[patch]` **L-A — a repo-set clean still exited 0 when a member errored.** The `clean_repo_set` branch returned `ok=True` above the new check; before 68.1 a member error raised, so this regressed. **Fix:** the duty computes `errored` from whichever result ran; `test_cli_clean_repo_set_exits_failed_when_a_member_errored`.
- `[low]` `[patch]` **L-E — a Ctrl-C mid-tar still left one partial archive.** **Fix:** the partial archive is unlinked for any exception; `OSError` / `TarError` are still wrapped as `WorkspaceError`, everything else re-raised; `test_an_interrupt_mid_tar_leaves_no_partial_archive`.
- `[low]` `[note]` **L-F — an interrupt after the worktree is removed leaves a record that errors on every later fleet sweep** until an interactive `clean <slug>` writes the `.missing.txt` marker. Safe by design (M1); recorded as an I/O row.
- `[nit]` `[defer → none]` A signal landing exactly between `remaining.append(record)` and `in_flight = None` would save the record twice — a duplicate row, never a lost one; negligible.
