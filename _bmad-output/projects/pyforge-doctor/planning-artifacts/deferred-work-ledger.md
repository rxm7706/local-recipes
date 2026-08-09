---
doc_type: deferred-work-ledger
project: pyforge-doctor
date: 2026-07-29
status: promoted-verbatim
---

# pyforge-doctor — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-29 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown, and this repo has already lost data that way
(pyforge-atlas's live ledger is still truncated to 11 of 64 entries, collateral of the
2026-07-19 copy failure). Until today this project had **no tracked ledger at all**, so
its entire deferred-work record — 6 KB — existed only in
scratch space. Found by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current. The one intentional edit is
id renaming, below.

Durability first; curation is owned follow-up work.

---

# Deferred Work

## DW-1-1-1 — The loop's exact `[verify]` command (`pixi run -e pyforge-doctor pyforge-doctor-test`, unfrozen)…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-frozen-finding-doctorreport-contract-exit-code-module.md`
  summary: The loop's exact `[verify]` command (`pixi run -e pyforge-doctor pyforge-doctor-test`, unfrozen) fails environmentally in every bmad-loop worktree — pixi-build-python 0.8.3 panics (`tools.rs:461` byte-index out-of-bounds) when the build `workDirectory` exceeds ~250 chars (this run's worktree root is 204 chars, over the threshold once nested build-metadata paths are appended). This is the same failure signature already recorded for `pyforge-warden`'s Story 1.1 (`_bmad-output/projects/pyforge-warden/implementation-artifacts/deferred-work.md`), with one added wrinkle: `pyforge-doctor` is a brand-new environment with zero existing `pixi.lock` entries, so `pixi run --frozen -e pyforge-doctor …` (the fix that worked for warden, which already had a solved lock) cannot bootstrap it either — `--frozen` refuses to add missing entries. The environment needs one successful *unfrozen* solve from a short-path checkout (e.g. the main `local-recipes` checkout, not a `.bmad-loop/runs/**/worktrees/**` path) to populate `pixi.lock` with `pyforge-doctor`'s entries; once committed, `--frozen` will work in future worktrees the same way it does for `pyforge-warden`/`pyforge-atlas` today. Recommend: (1) run `pixi install -e pyforge-doctor` (or any `pixi run -e pyforge-doctor …`) once from the main checkout to solve + commit the lock, then (2) switch `.bmad-loop/policy.toml` `[verify]` to `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`.
  evidence: Reproduced on the untouched sibling `pyforge-warden` environment in this same worktree (`pixi run -e pyforge-warden pyforge-warden-test` → identical "the build backend (pixi-build-python) exited prematurely" panic), proving the failure is pre-existing/environmental, not caused by this story's changes — confirmed via `git status`/`git diff --stat` showing only `pixi.toml` (39 lines, no `pixi.lock` churn) and the new untracked `src/shared/packages/pyforge-doctor/` package. Story verification instead used three independent substitutes, all passing: `PYTHONPATH=src python3 -m pytest tests -q` → 35/35 passed; `python -m build --no-isolation --wheel` → clean wheel containing `data/report-schema.json`, empty `__init__.py`, and an `entry_points.txt` with `doctor = pyforge.doctor.__main__:main`; installing that wheel into a fresh venv and running the real console script (`doctor --version`/`--help`/no-args all exit 0 with correct output, `doctor --bogus` exits 2, no tracebacks).

  status: done 2026-07-30

  verified: 2026-07-30 — ALREADY RESOLVED — both halves of this entry's own two-step prescription have since landed. (1) The lock is bootstrapped: `pixi.lock:8279` carries a `pyforge-doctor:` environment block and three `conda_source: pyforge-doctor[…] @ src/shared/packages/pyforge-doctor` entries (`:8330`, `:8371`, `:8413`), so `--frozen` no longer has missing entries to refuse. (2) The verify command is frozen: `planning-artifacts/marshal-policy.toml:35` declares `"pixi run --frozen -e pyforge-doctor pyforge-doctor-test"`, and the live home `~/.bmad-loops/pyforge-doctor/.bmad-loop/policy.toml:32` carries the identical command. Resolved as a side effect of the Story 1.10 policy-rendering work (PR #139) plus the lock solve, which is why nobody marked it — the same pattern as warden's DW-1-1-1.

## DW-1-1-2 — The team's own auto-memory (`project_bmad_loop_worktree_path_length_limit.md`, updated 2026-07-2…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-frozen-finding-doctorreport-contract-exit-code-module.md`
  summary: The team's own auto-memory (`project_bmad_loop_worktree_path_length_limit.md`, updated 2026-07-25 by a concurrent pyforge-herald session) confirms bmad-loop's orchestrator classifies the above pixi-build-python panic as a *code* failure (not `env_fault`, since its return code isn't 126/127) and, with `scm.rollback_on_failure = true`, resets the story branch to `baseline_commit` — discarding a finished, reviewed, green story. This worktree's root path is 239 bytes, well over the ~173-byte panic threshold, so this story's own post-session `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` re-check is expected to hit the identical panic and may trigger the same rollback a third time (attempts 1 and 2 of this exact story were already lost this way — see the Spec Change Log above). Recommend fixing `bmad_loop.verify.ENV_FAULT_RCS`/`verify_commands_outcome` (or the panic's root cause upstream in pixi-build-backends) so this whole panic signature is treated as `env_fault` rather than a per-story code failure.
  evidence: This story's own two prior attempts are direct evidence (dev pass 1 fully implemented + verified 35/35, per the note above, yet the worktree was clean-at-baseline with `sprint-status.yaml` still `backlog` when attempt 3 started — no commit, no `final_revision`, nothing to recover). Cross-confirmed independently by pyforge-herald story 1.2 hitting the same panic class the same day (per the cited memory). If this session's commit is likewise rolled back, recovery is cheap and already on record: `git merge --ff-only <final_revision>` (this commit's parent is the baseline) — see this spec's frontmatter `final_revision` once step 4 commits.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and now locatable to the line. bmad-loop has moved 0.8.1 → **0.9.0** since this entry was written, and the classification is unchanged: `bmad_loop/verify.py:1474` still reads `ENV_FAULT_RCS = frozenset({126, 127})`, and `:1508` still gates solely on `if result.returncode in ENV_FAULT_RCS`. The pixi-build-python panic returns neither, so it is still scored a *code* failure and still triggers the rollback. Worth recording as intent rather than oversight: the comment at `:1469-1471` deliberately scopes the set to the sh-launcher convention (126 = found-but-not-executable, 127 = not-found), so widening it is a design change upstream, not a bug fix. Note the TRIGGER is now largely mitigated while the CLASSIFICATION is not — the fleet's homes moved to `~/.bmad-loops/` (worst-case story worktree 157–159 chars, under the ~173 panic threshold), so the panic rarely fires; any future long-path home would still lose a finished story.

## DW-1-1-3 — Three uncoordinated version constraints exist for the same `hatchling` build backend across the…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-frozen-finding-doctorreport-contract-exit-code-module.md`
  summary: Three uncoordinated version constraints exist for the same `hatchling` build backend across the whole `pyforge-*` package family (unconstrained in each package's `pyproject.toml [build-system] requires`, `>=1.31.0` in the root `pixi.toml`'s `[feature.pyforge-<pkg>.dependencies]`, and `"*"` in each package's own `pixi.toml [package.host-dependencies]`) — nothing ties these together, so the conda build and the wheel/sdist build can silently resolve to different hatchling versions.
  evidence: Pre-existing in `pyforge-warden`'s own three files (identical shape), faithfully mirrored — not introduced by this story. Cross-cutting across `pyforge-warden`/`pyforge-atlas`/`pyforge-doctor`; a fix belongs in a shared follow-up touching all three, not a one-off deviation in this story's scaffold (which is explicitly mandated to mirror warden's shape exactly).

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN, and WIDER than recorded — the entry described three packages (warden/atlas/doctor); the family is now **eight**. All three uncoordinated constraints are intact and measured: (a) unconstrained in every package's `pyproject.toml:3` — `requires = ["hatchling"]` in all 8 of atlas, doctor, herald, marshal, mason, scribe, steward, warden; (b) `hatchling = ">=1.31.0"` at 6 sites in the root `pixi.toml` (`:135`, `:164`, `:199`, `:267`, `:878`, `:1323`); (c) `hatchling = "*"` in all 8 packages' own `pixi.toml` `[package.host-dependencies]` (atlas `:23`, steward `:21`, warden `:24`, doctor `:25`, mason `:23`, herald `:25`, marshal `:26`, scribe `:25`). Nothing ties the three together, so the conda build and the wheel/sdist build can still resolve different hatchling versions.

## DW-1-1-4 — The AD-2 sole-ownership meta-test's AST exit-literal detector (mirroring `pyforge-warden/tests/m…

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-package-scaffold-frozen-finding-doctorreport-contract-exit-code-module.md`
  summary: The AD-2 sole-ownership meta-test's AST exit-literal detector (mirroring `pyforge-warden/tests/meta/test_verdict_sole_ownership.py`'s technique) only matches `ast.Call` nodes, so a bare `raise SystemExit` (or `raise SystemExit(2)` is caught, but a bare `raise SystemExit` with no parens/args is an `ast.Raise` wrapping a plain `Name`, never a `Call`) would evade the guard.
  evidence: Confirmed by direct inspection of the detector's `_is_exit_callable`/`_exit_literal_violations` logic (both here and in the exemplar `pyforge-warden` file it mirrors) — this is an inherited limitation of the exemplar technique itself, not something introduced by this story's implementation; the exemplar's own docstring already states "this is a best-effort STATIC check," so fixing it is a shared cross-package hardening task, not this story's problem.
  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — and the entry's parenthetical is exactly right, proven by execution rather than reading. `tests/meta/test_verdict_sole_ownership.py:151` still opens with `if not isinstance(node, ast.Call)`, so any non-`Call` node never reaches `_is_exit_callable`. Ran the detector directly against four synthetic sources: `raise SystemExit(2)` → `[2]` (caught), `sys.exit(2)` → `[3]` (caught), `e = SystemExit(2); raise e` → `[2]` (caught), and bare `raise SystemExit` → **`[]` — evades**. This is not a harmless gap: a bare `raise SystemExit` exits with code 0, and `GUARDED_EXIT_LITERALS` is `frozenset({0, 2, 130})`, so it slips a genuinely guarded literal past the gate. Still an inherited exemplar limitation shared with warden, whose copy carries the identical `ast.Call` gate at `pyforge-warden/tests/meta/test_verdict_sole_ownership.py:154` — so a fix belongs in both.

### DW-FU-6-4: Follow-up review still recommended for 6-4-the-ledger-verdicts-come-home after the damping cap was spent

- source_spec: `spec-6-4-the-ledger-verdicts-come-home.md`
  summary: Follow-up review still recommended for 6-4-the-ledger-verdicts-come-home after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260808-210255-c88b; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-1` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-1`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-6-5: Follow-up review still recommended for 6-5-the-board-verdicts-come-home after the damping cap was spent

- source_spec: `spec-6-5-the-board-verdicts-come-home.md`
  summary: Follow-up review still recommended for 6-5-the-board-verdicts-come-home after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260808-210255-c88b; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-2` there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide with a generic `DW-2`. This promotion is the manual act Marshal FR-175 / Story 4.13 exists to make an obligation of the story itself.
  severity: low
  status: open

### DW-FU-6-6: Follow-up review still recommended for 6-6-the-chain-verdicts-come-home after the damping cap was spent

- source_spec: `spec-6-6-the-chain-verdicts-come-home.md`
  summary: Follow-up review still recommended for 6-6-the-chain-verdicts-come-home after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260808-210255-c88b; this entry preserves the lingering recommendation for a deliberate later review.
  promoted: 2026-08-09 — promoted from Tier-3 (id `DW-3` there) under the ledger's
    `DW-FU-<story>` convention, at the wind-down landing of this run. Marshal FR-175 /
    Story 4.13 exists to make this promotion an obligation of the story rather than
    archaeology someone performs later.
  severity: low
  status: open
