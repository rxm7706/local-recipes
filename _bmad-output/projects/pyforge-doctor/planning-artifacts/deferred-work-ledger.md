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

### DW-FU-6-8: Follow-up review still recommended for 6-8-bmad-drift-comes-home-without-breaking-the-board after the damping cap was spent

- source_spec: `spec-6-8-bmad-drift-comes-home-without-breaking-the-board.md`
  summary: Follow-up review still recommended for 6-8-bmad-drift-comes-home-without-breaking-the-board after the damping cap was spent
  evidence: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the
    story finalized (status: done, verify green) while the review pass still recommended an
    independent follow-up. The work was committed by bmad-loop run 20260809-195207-7471; this
    entry preserves the lingering recommendation for a deliberate later review.
  context: this story ran to every ceiling at once — dev attempt 2/2, review cycle 3/3,
    follow-ups 2/2 — and cleared its LAST review rather than escalating. It is also the
    largest single deliverable in Epic 6 (`sources/factory.py`, 1,197 lines, porting
    `scripts/bmad_drift_check.py`'s judgements), which is why an independent follow-up is
    worth more here than on a routine story.
  promoted: 2026-08-09 — promoted from Tier-3 `implementation-artifacts/deferred-work.md`
    (id `DW-4` there) under the ledger's `DW-FU-<story>` convention, so the next damped story
    cannot collide with a generic `DW-4`. Same act as DW-FU-6-5 / DW-FU-6-6; Marshal FR-175 /
    Story 4.13 exists to make this promotion an obligation of the story rather than
    archaeology someone performs later.
  severity: low
  status: open

### DW-FU-7-1: The Review Triage Log's `addressed_findings` never itemizes `defer` entries by the id they were just minted
- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: The Review Triage Log's `addressed_findings` never itemizes `defer` entries by the id they were just minted, unlike `patch`/`bad_spec`, so a review pass and the DW id(s) it produced aren't linked anywhere in the spec file itself.
  evidence: Found by review pass 1 (Blind Hunter, independent adversarial pass on this story's own diff). Confirmed by inspection of `step-04-review.md`'s Classify section (step 4): the triage-log template records only `intent_gap`/`bad_spec`/`patch`/`defer`/`reject` counts plus a free-text `addressed_findings` list, and only the `patch`/`bad_spec` triage branches (step 5) actually instruct listing specifics under `addressed_findings` — the `defer` branch never did, before or after this story's edit. Pre-existing (not introduced by this story's change to the `defer` bullet itself), but now more valuable to close since `defer` entries carry real, citable ids going forward. Deferred rather than patched in this pass: fixing it means extending the Classify section's shared triage-log format and step 5's `defer` branch — a change to a different part of the file than this story's own scoped edit — and deserves its own focused pass.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass for doctor 7-1)


### DW-FU-7-1-2: The `DW-FU-{story}` shape this story mints for non-mason stations already has an established, different meaning
- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: The `DW-FU-{story}` id shape this story mints for every non-mason station's generic `defer` findings is the exact same shape the pre-existing "follow-up review still recommended" promotion mechanism already uses exclusively, under a different field schema (`origin`/`severity`/`reason`/`status` there vs. `source_spec`/`summary`/`evidence` here) — collision-safe by suffix, but no longer distinguishable by id prefix alone.
  evidence: Found by review pass 1 (Blind Hunter). Confirmed by inspection of all four `### DW-FU-*` entries currently in `_bmad-output/planning-artifacts/deferred-work-ledger.md` (`DW-FU-6-4`, `DW-FU-6-5`, `DW-FU-6-6`, `DW-FU-6-8`) — every one carries `summary: Follow-up review still recommended for ...` and a `promoted:` annotation; none is a generic defer. This story's own convention (`DW-FU-{story}` for doctor/atlas/marshal/warden) is taken literally from the epic/SPEC text (`_bmad-output/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md`'s Constraints section), which does not address this overlap. Not patched in this pass: the epic's convention is explicit and was operator-confirmed the same day as this story, so resolving the overlap (e.g. giving generic defers a distinct discriminator) is a deliberate planning-level decision above this story's remit, not something an unattended pass should silently override.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass for doctor 7-1)

### DW-FU-7-1-3: `bmad-loop-sweep`'s canonical deferred-work format mandates a different id scheme and a dedupe check for the very file this emitter now mints station-convention ids into
- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: `.claude/skills/bmad-loop-sweep/deferred-work-format.md` declares itself the "Canonical entry format for `{implementation_artifacts}/deferred-work.md`" and mandates two rules the `step-04-review.md` defer bullet now contradicts: ids "numbered sequentially (`DW-1`, `DW-2`, …) by scanning the file for the highest existing number", and a mandatory "Before appending: dedupe check" that adds a `seen-again:` line to an existing entry rather than appending a duplicate. The defer bullet mints `DW-FU-<story>` / `DW-<story>-<n>` instead, and explicitly instructs the opposite on dedup ("Do not modify existing entries or look for duplicate content"). The two mechanisms need reconciling at planning level.
  evidence: Found by review pass 2 (Blind Hunter, independent adversarial pass). Confirmed by direct inspection of `deferred-work-format.md` lines 1-35: it names this exact file, explicitly covers "the inner dev path the bmad-dev-auto session appends its own flat entries (review defers, multi-goal splits, token splits)", and states both rules verbatim. Partially defused by that same doc — it says "the orchestrator owns the ledger and normalizes those flat entries into this canonical form on sweep", so a flat, non-canonical entry from bmad-dev-auto is anticipated by design; and `chain.py`'s `_GENERIC_RE = ^DW-\d+$` already flags sequential `DW-<n>` ids with the hint "Rename it to the ledger's DW-<story>-<n> convention on promotion, or the next damped story collides with it", so the fleet already treats sequential numbering as the shape needing correction. The residual, genuinely unreconciled half is the sweep's "highest existing number" scan, which is undefined in a file now holding both `DW-1`..`DW-4` and `DW-FU-7-1`..`DW-FU-7-1-4`, plus the flat contradiction on whether a dedupe check is required. Not patched in this pass: Story 7.1's Never clause explicitly scopes ledger-format normalization out ("that ledger normalization is a separate, later mechanism (`deferred-work-format.md`), not this story's job"), and changing either mechanism means deciding which document is authoritative for this file — a planning-level call above an unattended review pass.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-1 review)


### DW-FU-7-1-4: Three stations fall into the emitter's "every other station" default whose tracked ledgers use mason's shape exclusively, and atlas uses neither shape
- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: CAP-1 assigns `DW-FU-<story>` to doctor/atlas/marshal/warden and `DW-<story>-<n>` to mason, naming five of the fleet's eight stations. The emitter's "every other station, including unknown" branch therefore silently imposes `DW-FU-<story>` on scribe, steward and herald — all three of whose tracked ledgers use mason's `DW-<story>-<n>` shape essentially exclusively. Atlas is a separate mismatch: it is explicitly assigned `DW-FU-<story>` but its 44 tracked entries use scope-coded shapes — the `DW-` prefix followed by a letter-coded scope (`B`, `D`, `F`, `G`, `H`) plus numbers — and not one uses the `FU` scope.
  evidence: Found by review pass 2 (Edge Case Hunter), then measured directly across all eight stations' `planning-artifacts/deferred-work-ledger.md`. Counts by normalized heading shape — scribe: 7/7 `DW-<n>-<n>-<n>`; steward: 23/23 `DW-<n>-<n>-<n>`; herald: 29/30 `DW-<n>-<n>-<n>` (1 `DW-<n>`); mason: 5/5 `DW-<n>-<n>-<n>`; warden: 39 `DW-<n>-<n>-<n>` vs 2 `DW-FU-<n>-<n>`; marshal: 39 `DW-<n>-<n>-<n>` vs 8 `DW-FU-<n>-<n>`; doctor: 5 `DW-FU-<n>-<n>` vs 4 `DW-<n>-<n>-<n>`; atlas: 0 `DW-FU-` of 44. So the shape the emitter defaults three unassigned stations onto is the one none of them has ever used, and for warden/marshal the assigned shape is the minority of their own precedent. Distinct from `DW-FU-7-1-2`, which is about `DW-FU-<story>` colliding with the *follow-up-review promotion* meaning rather than about which stations get which shape. Not patched in this pass: Story 7.1's Never clause forbids normalizing one station's shape onto another's, CAP-1's mapping is explicit and was operator-confirmed the same day, and extending the mapping to the three unnamed stations is a planning-level decision for the epic, not something an unattended review pass should decide.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-1 review)


### DW-FU-7-1-5: Minting an id converts every new Tier-3 defer into a hard `tier3-only-deferral` FAIL of the always-on deferred-work gate, and no automatic promoter recognizes the minted shape
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: Before Story 7.1 an anonymous defer bullet carried no id, so the deferred-work check never saw it. Now every minted entry is an id present in the Tier-3 file and absent from the tracked ledger, which is exactly the `tier3-only-deferral` FAIL condition -- so each defer reds an always-on gate until a human promotes it by hand. Nothing in the fleet promotes this shape automatically.
  evidence: Found by review pass 3 (Blind Hunter and Edge Case Hunter independently), then measured. `pyforge/doctor/sources/chain.py::_check_project_deferred_work` FAILs on every id in `_ids(tier3) - _ids(tracked)`. Running that logic against doctor right now returns exactly two such ids -- `DW-FU-7-1-3` and `DW-FU-7-1-4`, both minted by this story's own pass 2 (Blind Hunter reported four; the earlier two had already been promoted to the tracked ledger by hand, so its count was wrong). The auto-promoter in `pyforge/marshal/core/deferred_work.py` cannot close the gap: its `_HEADING_RE` is `^### (DW-\d+): ` (digits only) and `parse_followup_deferrals` additionally requires all five of `origin`/`source_spec`/`severity`/`reason`/`status` with `origin: review-budget-followup`, none of which the minted three-field entry has. Not patched in this pass: Story 7.1's Never clause explicitly scopes out the tracked ledger, the promotion mechanism, and the detector (Stories 7.2/7.3), so deciding whether minted defers should auto-promote, be exempted by the detector, or stay a deliberate manual gate is a planning-level call for the epic. Distinct from `DW-FU-7-1-3`, which concerns the sweep format's id-scheme and dedupe contradiction rather than the detector gate and the absent promoter.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-1 review)


### DW-FU-7-1-6: The minted entry carries no `status:`, and giving it an id heading makes it look already-canonical to the one mechanism that would have supplied one
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: `bmad-loop-sweep` defines an open deferral as an id'd block whose `status:` line reads `open`, so a three-field `source_spec`/`summary`/`evidence` entry is invisible to sweep triage no matter how well-formed its id is. Worse, the sweep's stated remedy is to normalize *flat* (un-id'd) entries into the canonical form on sweep -- so adding the heading makes a minted entry read as already-normalized, and the one mechanism that would have given it a `status:` is now the one most likely to skip it. The change can therefore leave these entries less likely to be triaged than the anonymous bullets it replaced.
  evidence: Found by review pass 3 (Blind Hunter, corroborated by Edge Case Hunter, which proposed adding `status: open` and `origin:` lines as the guard). Confirmed by direct inspection: `.claude/skills/bmad-loop-sweep/deferred-work-format.md` declares itself canonical for this exact file and requires `origin`/`location`/`severity`/`reason`/`status`, and that skill's SKILL.md Step 1 builds its open set from blocks whose `status:` is `open`. Not patched in this pass: Story 7.1's Always clause freezes the field schema ("Preserve the existing `source_spec`/`summary`/`evidence` field schema ... exactly as they are today") and its Never clause forbids rewriting entries into the `origin`/`location`/`severity`/`reason`/`status` shape, so adding `status:` here would directly violate the intent contract. Related to `DW-FU-7-1-3` but causally distinct: that entry records that two documents disagree about id numbering and dedupe; this one records that the id heading actively defeats the normalization pass, which `DW-FU-7-1-3` cites as the reason the conflict was tolerable.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-1 review)

### DW-5: Follow-up review still recommended for 7-1-the-emitter-mints-identity-at-defer-time after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-7-1-the-emitter-mints-identity-at-defer-time.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260810-192603-53da; this entry preserves the lingering recommendation for a deliberate later review.
status: open
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-1 review)


### DW-FU-7-1-7: marshal's promoter cannot suffix around an id collision, so a minted id that reuses a promoted-follow-up id silently cancels a real promotion
- source_spec: `{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: marshal's promoter cannot suffix around an id collision, so a minted id that reuses a promoted-follow-up id silently cancels a real promotion.
  evidence: Found by review pass 4 (Blind Hunter). Verified by direct inspection of `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/deferred_work.py`: `promoted_id()` is documented as having "no numeric counter" and returns the follow-up shape built from `render_filename_slug(story_key)` alone, while `deferrals_to_promote()` skips any candidate whose `promoted_id` already appears as a complete token in the tracked text (`_tracked_promoted_ids`, `_PROMOTED_ID_TOKEN_RE`). The emitter can suffix around a collision; the promoter cannot. So once an emitter-minted entry for a story is promoted into the tracked ledger, a genuine `review-budget-followup` deferral for that same story is dropped by `marshal land` with no error, and its Tier-3 generic id then reds the deferred-work gate with nothing able to close it. Live today for this very story: `DW-FU-7-1` is already in doctor's tracked ledger. This is causally distinct from `DW-FU-7-1-2`, and in fact falsifies that entry's stated premise -- it records the overlap as "collision-safe by suffix", which holds only on the emitter side. Not patched in this pass: Story 7.1's Never clause scopes the promotion mechanism out ("Never touch the tracked ledger, the promotion mechanism..."), and the shape mapping itself is operator-confirmed in the epic. Resolving it is a planning-level decision on `DW-FU-7-1-2`'s ground, now with the harder constraint that suffixing is not a workaround.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-1 review)


### DW-FU-7-2: Whether the backlog's growth from 470 to 506 predates or postdates Story 7.1's merge is unverified, so this baseline neither confirms nor refutes whether 7.1 stopped new anonymous entries
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-7-2-grandfather-the-470-at-a-dated-cut-off.md`
  summary: Whether the backlog's growth from 470 to 506 predates or postdates Story 7.1's merge is unverified, so this baseline neither confirms nor refutes whether 7.1 stopped new anonymous entries.
  evidence: Found by review pass 1 (Blind Hunter). The epic's 470 figure was measured 2026-08-10T19:15 (per spec-deferred-work-visibility's own `.memlog.md`); Story 7.1 ("the emitter mints identity at defer time") merged at 2026-08-10 21:06:04, after that measurement; this story's own stamp (2026-08-11) measures 506, a growth of 36 across the window. Story 7.2's own Design Notes already explain why 506 differs from 470 in general terms (the backlog is "a live, growing thing") and that explanation was already reviewed and accepted -- but it does not address WHEN the growth happened relative to 7.1's merge, which is the one fact that would show whether 7.1's fix is actually holding. Tier-3 entries carry no timestamp field, so this cannot be answered from the data alone without a dedicated investigation (e.g. diffing each project's Tier-3 file at the 7.1 merge commit against its current state). Not patched in this pass: this story's Never clause explicitly forbids triaging or wiring the backlog, and confirming 7.1's efficacy is a distinct question from stamping the current count -- but real and worth a focused follow-up, since a "yes, still growing after 7.1" answer would be a live regression in already-shipped work.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-2)

### DW-FU-7-2-2: A project whose Tier-3 file is deleted can never have its baseline entry lowered or zeroed via `--project`
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-7-2-grandfather-the-470-at-a-dated-cut-off.md`
  summary: A project whose Tier-3 file is deleted can never have its baseline entry lowered or zeroed via `--project`, because the unknown-project validation only consults currently-discoverable projects, not the union of the committed baseline and the currently-discoverable set.
  evidence: Found by Blind Hunter and Edge Case Hunter independently (Blind Hunter's finding, Edge Case Hunter's related finding #6). Confirmed by reading `scripts/deferred_work_baseline.py::main`: `unknown = sorted(set(args.project) - set(current))` checks only `_live_state()`'s locally-discoverable projects; a project already present in the committed baseline but whose Tier-3 file no longer exists (backlog fully resolved and the file deleted, or a not-yet-backlinked worktree) is reported "unknown project(s)" and cannot be re-baselined at a lower or zero count -- its stamped count becomes a permanent ceiling. This is the mirror image of the already-fixed "bare mode silently drops an invisible project" defect (this story's own review pass 1 patched that one); the fix there was to always merge and never drop, but that same merge now means there is no path to deliberately LOWER a count once stamped, only to raise or leave it. Out of scope for this pass: this story's Never clause forbids triaging the backlog and this scenario (a known project's Tier-3 scratch disappearing entirely while the project itself remains active) has not occurred yet in this repo -- but it is a real gap Story 7.3 or a future maintenance pass should account for before relying on the baseline as authoritative for a shrinking count.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass, doctor 7-2)


### DW-6-11-1: No test in test_sources_factory.py asserts classify()'s literal return string for any rule, including the new spike-report one
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-6-11-the-classifier-recognizes-a-spike-report.md`
  summary: No test in test_sources_factory.py asserts classify()'s literal return string for any rule, including the new spike-report one, so a typo in a returned label would sail through the whole file's coverage as long as it isn't literally "UNKNOWN".
  evidence: Found by review pass 1 (Blind Hunter). Verified by inspection: every test in test_sources_factory.py exercises classify() only indirectly through factory.gather()/check_coverage()'s check/status/evidence fields (e.g. check == "bmad-drift" and status is DoctorStatus.OK, or check == "uncovered" and status is DoctorStatus.FAIL) -- none calls factory.classify(path, target) directly and asserts its return string. This story's own three new tests (test_spike_report_is_classified_and_not_flagged_uncovered, test_a_second_spike_index_is_also_classified, test_spike_report_look_alike_without_a_numeric_index_still_hard_fails) follow that same pre-existing convention, so a typo in the new rule's return label (e.g. "archive:spike_report" for "archive:spike-report") would still pass every test in the file. Pre-existing across the whole file -- every prior classify() rule has the identical gap -- not a regression introduced by this story, and out of Story 6.11's Boundaries & Constraints, which scope the change to exactly one new rule using the file's existing test pattern. Worth a dedicated follow-up: add direct classify()-return-value assertions across the file's coverage tests.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-6-11` there) during the pre-shutdown deferred-work audit.

### DW-7-3-1: The committed anonymous-Tier-3 baseline has no automated freshness check, only this landing's one-off manual verification
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-7-3-the-detector-sees-anonymous-tier-3-entries.md`
  summary: The committed anonymous-Tier-3 baseline has no automated freshness check, only this landing's one-off manual verification that live counts still match the stamped counts.
  evidence: Found by Blind Hunter (review pass 1). This story's detector compares each project's live anonymous-Tier-3 entries against the count stamped in `scripts/.deferred-work-baseline.json` (Story 7.2), and CAP-3's "green on an unchanged repo" claim is confirmed in this landing only by a manual, one-time `pixi run -e pyforge-doctor python -m pyforge.doctor.sources deferred-work` inspection recorded in this Spec's `.memlog.md` -- not by any repeatable test or CI gate. If the fleet's live counts drift ahead of the stamped baseline over time (new anonymous entries accumulating faster than anyone re-runs `--write-baseline`), the first symptom is a bare `tier3-entry-unidentified` FAIL with no pointer back to this landing's context, and no automated signal warns that the baseline itself has gone stale. Related to `DW-FU-7-2-2` (a baseline count can never be LOWERED once a project's Tier-3 file disappears) but causally distinct: that entry is about the baseline being too CONSERVATIVE for a shrinking project; this one is about the baseline having no mechanism to detect it has fallen BEHIND a growing one. Not patched in this pass: this story's Never clause forbids triaging or wiring the backlog, and adding a staleness-detection mechanism for the baseline itself is a distinct capability outside CAP-2/CAP-3's stated scope -- worth a dedicated follow-up.
  status: open
  promoted: 2026-08-15 — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-FU-7-3` there) during the pre-shutdown deferred-work audit.

### DW-CHAIN-COMPLETENESS-1: INV-A's spec-not-decomposed test is a bare substring match, so a Spec can grow capabilities with no stories and still read as fully decomposed
- source_spec: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md`
  summary: `chain-completeness`'s INV-A (`sources/board.py::_check_project_chain_completeness`) decides "this open Spec is decomposed" by testing whether the Spec's slug appears **anywhere** in the concatenated prose of the project's PRDs and `epics*.md` (`if bare not in prose and slug not in prose`). It is a substring test over a blob, not a coverage test over capabilities — so once ANY epic mentions a Spec by name, that Spec reads as decomposed forever, no matter how many capabilities are later added to it with zero stories against them.
  evidence: Found by execution 2026-08-15, not inference. `spec-deferred-work-visibility` was extended the same day from 3 capabilities to 10 (CAP-4..10 added, PR #521). Epic 7's prose already contained the string `spec-deferred-work-visibility`, so `pixi run -e local-recipes python -m pyforge.doctor.sources chain-completeness` reported `ok -- every open Spec is decomposed, and epics, ledger and board agree` while **seven of its ten capabilities had no story anywhere in the fleet**. Confirmed by reading `board.py:463-477`: the loop is over `pa.glob("specs/spec-*/SPEC.md")`, the membership test is `bare not in prose and slug not in prose`, and nothing parses `CAP-` ids on either side. This is structurally the SAME defect class the owning Spec itself exists to fix -- a set/substring membership test that reports OK while missing most of what it claims to check (cf. that Spec's own `_DW_RE` two-set comparison, which passed while 470 anonymous deferrals were invisible). The gap was closed for THIS spec by hand (Epics 8 and 9, appended 2026-08-15), which is exactly the manual compensation that makes the detector's blind spot easy to keep not noticing.
  status: partially closed
  raised: 2026-08-15 — raised directly (not promoted from Tier-3) while answering that Spec's Q5, and deliberately NOT folded into it as CAP-11: it is a different detector (`sources/board.py`'s chain-completeness, not `sources/chain.py`'s deferred-work), and reopening a Spec at the moment its decomposition lands would defeat the purpose of decomposing it. Owner: doctor (owns `board.py`). A real fix needs INV-A to compare the Spec's declared `CAP-` ids against the CAP ids cited in the project's epics/stories prose, and to report the uncovered ones by id rather than answering a yes/no per Spec.
  closed: 2026-08-21 — Story 12.3 landed (Round 4 re-derive, after three bad_spec loopbacks on rounds 1-3), and closes the ORIGINAL defect this entry was raised for: `board.py` now parses each open Spec's declared `CAP-N` ids from its `## Capabilities` section and every `CAP-` citation actually present in the project's PRD/epics prose (bare `CAP-N`, inclusive range `CAP-N..M`, prefixed range `CAP-N..CAP-M`, slash-grouped `CAP-N/M/O`), scoped per-Spec via an any-slug-occurrence citation window (ended by the next Spec's own anchor or capped at the second `## ` heading past the anchor, whichever is nearer) — never pooled flat across a project, which would let two same-numbered Specs falsely cover each other (the Round 2 defect class). The uncovered ids are reported by name (e.g. `CAP-4..10`), not a single yes/no per Spec. A Spec with zero declared CAP ids keeps the original bare-substring fallback, byte-identical. Round 4's own contribution: each source file's own preamble (everything before THAT FILE'S first `## ` heading) is stripped at prose-build time, before concatenation — replacing Round 3's whole-blob, first-file-only exclusion, which only protected whichever file happened to sort first and left every later file's own preamble (e.g. an epics.md's own frontmatter `currency_review` field) still exploitable. Verified against both real live reproductions Round 3/4 review found (`pyforge-marshal/prd.md`'s changelog-block `CAP-9` mention and `pyforge-doctor/epics.md`'s own `currency_review` field, both before their file's first `## ` heading) — neither leaks after the fix, confirmed live and via a targeted redaction repro. `pixi run -e local-recipes python -m pyforge.doctor.sources chain-completeness` reports the same 7 genuine findings as before the fix (pyforge-marshal x6, pyforge-steward x1) — both repro fixes only removed latent/inert leaks, not real findings. **Marked "partially closed", not "closed"**: Round 4's own post-landing adversarial review (Blind Hunter) live-reproduced two further leaks in the SAME preamble-stripping heuristic — see `DW-CHAIN-COMPLETENESS-4` and `DW-CHAIN-COMPLETENESS-5`, minted the same day rather than triggering a fifth bad_spec loopback on a heuristic that has now needed narrowing four times running.

### DW-CHAIN-COMPLETENESS-2: Story 12.3's newly-precise INV-A surfaces 7 real CAP-coverage gaps in pyforge-marshal and pyforge-steward that the old bare-substring check could never have caught
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-12-3-chain-completeness-parses-capability-ids-not-a-bare-substring-match.md`
  summary: Now that `chain-completeness`'s INV-A compares a Spec's declared `CAP-N` ids against the ids actually cited for that Spec in its own project's PRD/epics prose (Story 12.3, closing `DW-CHAIN-COMPLETENESS-1`), a live run against this repo's real `_bmad-output/projects/` tree surfaces 7 genuine, previously-invisible capability-coverage gaps — none owned by `pyforge-doctor`, so none are this story's own to fix. `pyforge-marshal`: `spec-agent-tool-surface` (CAP-1..4), `spec-dashboard-project-path-derivation` (CAP-1..4), `spec-loop-home-fleet-refresh` (CAP-1..3), `spec-sprint-status-auto-promote` (CAP-1..4), `spec-pyforge-core` (CAP-1..7, ALL of it), and `spec-surface-drift-reconciliation` (CAP-7 only, a partial gap). `pyforge-steward`: `spec-jira-github-projects-sync` (CAP-2..5).
  evidence: Confirmed genuine for every entry, not a parsing artifact, by reading the underlying planning artifacts directly (independently re-verified across this story's Round 2, 3, and 4 review passes; the live finding set was identical across all of them, including after Round 3/4's preamble-leak fixes — proving the two fixed leaks were latent/inert and never the source of any of these 7 findings). Five of the six marshal Specs (`agent-tool-surface`, `dashboard-project-path-derivation`, `loop-home-fleet-refresh`, `sprint-status-auto-promote`, `pyforge-core`) are among the "8 previously-undecomposed Marshal Specs absorbed as FR-128..FR-163" named in `prd.md`'s own 2026-08-08 `currency_review` comment — their epics (where any exist at all; `spec-pyforge-core`'s Epic 14 cites only `FR-N`, never once repeating a `CAP-` id) predate or never adopted the `CAP-N` citation convention their own SPEC.md later gained. `spec-surface-drift-reconciliation`'s `prd.md` cites `CAP-1..CAP-6` explicitly but never `CAP-7`. `spec-jira-github-projects-sync`'s own `epics.md` Story 8.7 cites only "CAP-1 residual," matching its own `currency_review`'s "previously undecomposed" language for the rest. This is precisely the defect class `DW-CHAIN-COMPLETENESS-1` existed to surface — it was structurally impossible for the OLD bare-substring check to ever report any of these, since every one of these Specs' slugs already appears somewhere in its own project's prose. Reproducible: `pixi run -e local-recipes python -m pyforge.doctor.sources chain-completeness`.
  status: open
  severity: medium
  raised: 2026-08-21 — raised while running Story 12.3's own required live-sanity-check gate (its spec's Acceptance Criteria: inspect every new finding before closing `DW-CHAIN-COMPLETENESS-1`); first drafted during Round 2's review pass, then re-minted (identically) after Rounds 2 and 3's own code was separately reverted by later bad_spec loopbacks, landing here once Round 4's fix shipped with the same 7 findings unchanged throughout. Owner: pyforge-marshal (6 of 7 findings) and pyforge-steward (1 of 7) — decomposing these Specs' own remaining capabilities into their own epics/stories is planning work for those stations, not a `board.py` code change, and out of `board.py`'s own Never clause ("do not touch INV-B/C/D... same signature, same call site").

### DW-CHAIN-COMPLETENESS-3: `_parse_declared_cap_ids`'s `## Capabilities` heading match is exact-string, case-sensitive, no trailing text, so a SPEC.md using a different heading convention silently falls back to the (weaker) bare-substring check
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-12-3-chain-completeness-parses-capability-ids-not-a-bare-substring-match.md`
  summary: `board.py::_parse_declared_cap_ids` recognizes only a literal `## Capabilities` heading (exact string, case-sensitive, no trailing text) as the start of a Spec's declared-CAP-ids section. A SPEC.md using any other heading for the same content — confirmed live: `spec-dream-to-code-model-self-verification`'s `SPEC.md` uses `## Scope (capabilities)` — parses to zero declared ids, which is INV-A's own signal to fall back to the original, weaker bare-substring check instead of being detected and flagged as a genuine coverage gap or a malformed-but-real Capabilities section.
  evidence: Found during Story 12.3's review pass 1 (adversarial review) via a live grep of every tracked `SPEC.md`'s section headings fleet-wide; confirmed by reading `spec-dream-to-code-model-self-verification/SPEC.md` directly. Deliberately not folded into Story 12.3's own fix (its Never clause scopes the story to the `board.py` INV-A comparison logic, not to auditing every SPEC.md heading-convention variant fleet-wide — a separate, larger scope question, possibly its own catalog item under `hygiene-gap-catalog.md` Category 1).
  status: open
  severity: low
  raised: 2026-08-21 — raised during Story 12.3's review pass 1, deferred rather than folded in to keep that story's diff bounded to its one scoped bug; minted here as promised in that pass's own triage log, once the story actually landed. Owner: doctor (owns `board.py`'s INV-A parsing) — a real fix widens `_CAP_SECTION_HEADING_RE` to tolerate case/trailing-text variance, or standardizes every SPEC.md onto one heading spelling (a `bmad-spec` template question, not purely a `board.py` one).

### DW-CHAIN-COMPLETENESS-4: Round 4's per-file preamble stripping only strips text BEFORE a file's own first `## ` heading — irrelevant content AFTER that heading (e.g. a `## Changelog` section) can still open a false citation window
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-12-3-chain-completeness-parses-capability-ids-not-a-bare-substring-match.md`
  summary: `board.py`'s Round 4 fix slices each source file to start at its own first `## ` heading, discarding everything before it. It does not distinguish a decomposition-relevant heading from an irrelevant one — if the file's FIRST heading happens to be something like `## Changelog` and that section incidentally mentions a Spec's slug near an unrelated CAP id, that text is never stripped (it comes after the first heading) and can still open a false citation window, crediting a CAP id the Spec's own epics/stories never actually cite.
  evidence: Live-reproduced during Story 12.3's Round 4 review pass (Blind Hunter) against the actual merged `board.gather_chain_completeness`: a Spec declaring `CAP-1,2,3,9` with a legitimate `CAP-1..3` citation in `epics.md`, plus a `prd.md` whose first `## ` heading is `## Changelog` containing "spec-foo's CAP-9 was discussed and deferred" — reports `ok` instead of `FAIL: CAP-9 uncovered`. Same defect class as `DW-CHAIN-COMPLETENESS-1`'s original bug (a real, open gap silently reading as covered), recurring in a new position after four rounds of narrowing. Not folded into Story 12.3's own fix by operator decision (2026-08-21): the heuristic has already needed narrowing on rounds 2, 3, and 4, and a fifth loopback risks the same pattern recurring in yet another position rather than closing the underlying class. Landed with this residual documented instead.
  status: open
  severity: medium
  raised: 2026-08-21 — raised during Story 12.3's Round 4 review pass, landed as a documented residual rather than triggering a fifth bad_spec loopback. Owner: doctor (owns `board.py`'s INV-A parsing). A real fix likely needs to allowlist decomposition-relevant heading shapes (e.g. `## Epic N`, `### Story N.M`) rather than treating "any `## ` heading" as the boundary of relevant content — a larger redesign of the windowing model, not a narrow patch, given the heuristic's track record.

### DW-CHAIN-COMPLETENESS-5: a source file with NO `## ` heading anywhere is kept whole, unstripped — its entire text (including anything preamble-shaped) remains searchable for false citations
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-12-3-chain-completeness-parses-capability-ids-not-a-bare-substring-match.md`
  summary: When a source file has no `## ` heading at all, Round 4's per-file preamble stripping has no signal to slice against and keeps the file's text whole, unchanged — so a slug+CAP-id adjacency anywhere in that file's prose (there being no "preamble" boundary to strip) can still open a false citation window, the same leak class as `DW-CHAIN-COMPLETENESS-4` triggered by a different shape.
  evidence: Confirmed directly in `board.py`'s own preamble-stripping code and comments ("a file with no `## ` heading anywhere is kept whole, unchanged -- there is no signal to slice against"), live-reproduced during Story 12.3's Round 4 review pass with a synthetic headerless `epics*.md`-shaped fixture. This exact edge was already identified and consciously deferred during Story 12.3's Review pass 3 ("a project with zero `## `-level headings anywhere would disable both the heading-cap and preamble-exclusion logic simultaneously... untested, not live-triggered by any of the 8 tracked projects today... revisit only if a real headerless project file surfaces") — re-confirmed here as still real and still not live-triggered (`grep -L '^## ' _bmad-output/projects/*/planning-artifacts/{prd.md,epics*.md}` finds none), so minted as its own tracked entry now rather than left as a one-off note buried in a landed story's Review Triage Log.
  status: open
  severity: low
  raised: 2026-08-21 — raised during Story 12.3's Review pass 3, minted as a proper ledger entry at landing time per that pass's own commitment. Owner: doctor (owns `board.py`'s INV-A parsing). No live occurrence today; revisit if a real headerless `prd.md`/`epics*.md` ever surfaces fleet-wide, or fold into `DW-CHAIN-COMPLETENESS-4`'s redesign if that work happens first.

### DW-11-8-1: CAP-8 (backlog-intake check) split out of Epic 11 — RESOLVED, follow-on Spec + Epic 13 now exist
- source_spec: `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-backlog-intake-check/SPEC.md`
  summary: former Story 11.8 ("backlog-intake surfaces deferred entries during story drafting," CAP-8) removed from Epic 11 2026-08-21. Its own Spec's Open Question — same story wave as CAP-1..7, or its own follow-on Spec, since it is write-adjacent to story-drafting rather than the read-only sweep the rest of the Spec is — resolved to "own follow-on Spec": Epic 11 shipped cleanly as Stories 11.1–11.7, a self-contained read-only pipeline, and bundling a write-adjacent capability into it after the fact would have muddied that result. `spec-deferred-work-resolution-sweep`'s own CAP-8 entry marked split-out (now covers CAP-1..7 only); the capability re-emerged the same day as its own Spec (`spec-backlog-intake-check`, CAP-1, via `bmad-spec`) and Epic 13 / Story 13.1 in `epics.md`, cleared to dispatch.
  evidence: `epics.md` Epic 11 (Story 11.8 removed, dated split-out note) and Epic 13 (Story 13.1, new); `spec-deferred-work-resolution-sweep/SPEC.md` (CAP-8 marked split-out); `spec-backlog-intake-check/SPEC.md` (the new companion Spec, CAP-1, `.memlog.md` records the full derivation); `docs/dreams/deferred-work-resolution-sweep.md` Realization log (both Specs' owner-dream).
  status: closed — Story 13.1 landed 2026-08-21: `pyforge.doctor.sources.backlog_intake` (`Source.BACKLOG_INTAKE`) + the `doctor backlog-intake <identifier>` CLI verb ship the fleet-wide, precisely-id-matched deferred-work surfacing this entry called for.
  raised: 2026-08-21 — raised directly while resolving Epic 11's own closeout; resolved same day once the operator directed the follow-on Spec be written.
  closed: 2026-08-21 — Story 13.1 (`spec-13-1-a-drafting-session-surfaces-matching-deferred-work-entries-for-an-epic.md`) landed.

## DW-FU-12-4 — A glob-less, trailing-slash spec-surface entry that can never match (foreign defect, surfaced by Story 12.4's review)

`spec-dream-to-code-model-self-verification/SPEC.md:13` declares the surface entry
`.claude/skills/conda-forge-expert/tests/meta/` — glob-less with a trailing slash, which
`chain.py::_glob_to_re`'s exact-match rule can never match; the directory is actually
governed by pyforge-mason's `spec-packaging-factory` blanket glob. Pre-existing and
marshal-owned (foreign to doctor); surfaced incidentally by Story 12.4's pass-2 review and
deferred rather than fixed cross-station. Remedy: fix the entry in the owning spec (a real
glob or the file list), then re-stamp that spec's surface baseline. Severity: low. Status:
open. Relayed from the story worktree's ephemeral Tier-3 file at landing, 2026-08-21.

## DW-FU-12-5 — Corrupt committed baseline dies with a raw JSONDecodeError on scoped stamps

Pre-existing in `scripts/spec_surface_check.py`: a corrupt `scripts/.spec-surface-baseline.json`
raises raw `json.JSONDecodeError` on a scoped `--write-baseline`. Remedy: a diagnostic naming
the file and the re-stamp recovery path — never an `except -> {}` fallback (rejected in Story
12.5's review as reintroducing the drop-every-other-spec hazard). Severity: low. Status: open.
Relayed from the story worktree's ephemeral Tier-3 at landing, 2026-08-21.

## DW-FU-12-5-2 — Zero-discoverable-specs full stamp silently wipes the baseline to `{}` at exit 0

Pre-existing accept-everything semantics of the `--spec`-less full stamp, degenerate case: with
spec discovery returning nothing it replaces the whole baseline with `{}`, exit 0. Remedy:
refuse (or gate behind a flag) when the live snapshot is empty and the existing baseline is
not. Severity: low. Status: open. Relayed 2026-08-21.

### DW-14-1-1: GitHub-releases fallback for the 6 npm-invisible bmad-suite packages
  origin: story-14-1 review (deferred, medium — carried in the story spec's 6.11-era frontmatter `deferred:` list)
  source_spec: `planning-artifacts/specs/spec-14-1-the-bmad-suite-is-compared-against-upstream-derived-not-declared.md`
  severity: medium
  reason: 6 of the 10 watched bmad-* pins (bmad-loop, bmad-labs-skills, bmad-manticore, bmad-method-wds-expansion, bmad-module-template, bmad-utility-skills) are GitHub-only and 404 on registry.npmjs.org, so CAP-4's live npm path is structurally blind to them — including bmad-loop, the package whose 0.9.0-vs-0.11.0 lag motivated CAP-4. The `packages_watched` (10) vs `packages_checked` (4) evidence keeps the gap operator-visible; the follow-on is a GitHub-releases fallback query through the same fail-open budget. Relayed here because the DW pipeline cannot yet read frontmatter `deferred:` lists (marshal DW-BL011-2).
  status: open
