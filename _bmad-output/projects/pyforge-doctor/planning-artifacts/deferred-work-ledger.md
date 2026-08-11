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

