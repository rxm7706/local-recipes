---
title: "91.1: A corrupt environment.yaml never lands"
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-12-a-shared-surface-diff-also-clears-its-own-full-suite-not-just-the-stations-bound-gate.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-14-the-cross-surface-gate-runs-each-touched-surface-s-own-check.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-3-verification-is-the-product-no-landing-on-a-self-report.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-9-dispatch-applies-ruff-format-to-a-story-s-files-before-it-verifies.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-83-15-dispatch-applies-ruff-s-safe-fixes-before-it-verifies.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-85-7-a-cross-surface-refusal-gets-the-same-one-fix-turn.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-34-2-a-dispatch-spin-sessions-worktree-is-checkpointed-before-it-can-be-lost-to-a-crash.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/worktree_checkpoint.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  - .github/workflows/scripts/linter.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** dispatch landings put an `environment.yaml` whose first line is a pixi warning onto `main`, six times
between 2026-10-04 and 2026-10-10, and nothing on the dispatch path noticed. `main` carries it now. Line numbers below
are at `909a725e16`.

**What the file must be.** `environment.yaml` is derived: it must equal the stdout of `pixi project export
conda-environment -e build` (`.github/workflows/scripts/linter.py:64`-`:80`, and steward's `check_environment_sync`,
`provision.py:318`-`:352`, which compares the two `.rstrip()`ed).

**How it goes wrong (reproduced 2026-10-10, pixi 0.81.0).** Inside a `pixi run` shell (`PIXI_IN_SHELL=1`,
`PIXI_PROJECT_MANIFEST` set to the primary checkout's `pixi.toml`), running the export from a story worktree prints
" WARN Using local manifest <worktree>/pixi.toml rather than <primary>/pixi.toml from environment variable
`PIXI_PROJECT_MANIFEST`" on **stderr**; stdout is clean. A session that regenerates the file with stderr captured
into it writes that line first, in ANSI colour. `yaml.safe_load` then raises `ReaderError: unacceptable character
#x001b`, and `steward provision --verify` exits 1 with a diff of exactly that one line.

**The evidence (git, GitHub and the host).**
- **`main` now.** `origin/main`'s `environment.yaml` starts `\x1b[33m WARN\x1b[0m Using local manifest
  …/.worktrees/dispatch-pyforge-warden-15.1/pixi.toml rather than …/pixi.toml from environment variable
  PIXI_PROJECT_MANIFEST`; every other line equals the export. It arrived with warden 15.1's landing `bab2162d73`
  ("Merge pyforge-warden/15-1 into main", PR #2099) from its idle checkpoint `795ff55c06` ("wip: 15.1
  (auto-checkpoint)"). Atlas 25.1's open PR #2104 carries a repaired file.
- **Six windows on `main`'s first-parent history** (the first byte of `environment.yaml` at each commit):

  | Carried onto `main` by | From checkpoint | Taken out by |
  |---|---|---|
  | `ce04ebb710` Merge pyforge-marshal/86-6 (2026-10-04) | `0b4a9112b3` wip: 86.6 | `960e9ad3b7` Merge pyforge-marshal/19-5 |
  | `ec46b781a8` Merge pyforge-herald/27-3 (2026-10-08) | `421d6393a6` wip: 27.3 | `3e989874f7` PR #1941 (`a4c99d2be4`, a hand repair) |
  | `3445952b51` Merge pyforge-steward/71-5 (2026-10-08) | `211a170572` wip: 71.5 | `acd32aca25` Merge pyforge-steward/71-6 |
  | `a5d20bf13d` Merge pyforge-steward/71-7 (2026-10-09) | `3dc792218f` wip: 71.7 | `a35318c31c` Merge pyforge-steward/76-3 |
  | `85e70dedf5` Merge pyforge-steward/87-3 (2026-10-10) | `863ea88c6a` wip: 87.3 | `c183207e67` Merge hygiene-873-dark-2026-10-10 |
  | `bab2162d73` Merge pyforge-warden/15-1 (2026-10-10) | `795ff55c06` wip: 15.1 | not yet (`909a725e16`) |

  Checkpoints of 72.1 (`4f8ad495ce`) and 85.2 (`aa7e0018cf`) carried it on their branches too. On 2026-10-10 the atlas
  25.1 session also wrote it into its worktree (operator report); none of that branch's commits carries it.
- **Why nothing stopped it.**
  - Marshal's idle checkpoint (`commit_worktree_checkpoint`, `core/worktree_checkpoint.py:45`-`:70`) commits every
    changed path, and the default epic surface admits `environment.yaml` (`_COMMON_BOOKKEEPING_PATHS`,
    `core/gate.py:344`), so the scope gate passes it.
  - Dispatch verification (`evaluate_dispatch_verification`, `dispatch_verify.py:743`) runs the station's
    `verify_commands`, the surface guard, `lint-types` and the cross-surface rules (`CROSS_SURFACE_RULES`,
    `core/gate.py:647`-`:651`: `platform`, `bmad-estate`, `flag-gate`). None reads `environment.yaml`.
  - The landing waits on every CI check run on the head (Story 80.1, `dispatch_land.py:938`). PR #2099's 27 checks
    all passed, `detectors` included. The repo's only sync lint runs in the `staged-recipes-linter` workflow, which is
    `disabled_manually` (state change 2026-08-24; its last run was that day). `marshal-policy.toml`'s
    `environment-yaml-sync` landing rule (`:670`-`:690`) fires only on a `pixi.toml` change and is not read by the
    dispatch landing.
  - `scripts/pre_push_preflight.sh:57`-`:63` skips the preflight for `dispatch/*` branches, by design.

**The cost.** A file the feedstock build scripts hand to the environment solver (`.scripts/build_steps.sh:123`,
`.scripts/run_osx_build.sh:35`) and steward's `validate-fast` compares was unparseable on `main` for hours at a time,
and each repair was a hand commit or a lucky later merge.

**Approach:** marshal regenerates the file from the exporter before it verifies, and its verification refuses a file
that still differs. Both act only when the story's diff touches `environment.yaml` or `pixi.toml`.
- **Regenerate before verifying (the repair).** Beside Story 83.9/83.15's ruff step, in `_run_and_journal_verification`
  (`dispatch_supervisor/__main__.py:2386`, the ruff call at `:2402`), when the paths the story changed against
  `origin/main` include `environment.yaml` or `pixi.toml`:
  - run `pixi project export conda-environment -e build` in the worktree through `ProcessPort.run`, and take its
    **stdout only**; stderr is never written anywhere near the file;
  - if the export exits 0 and its `.rstrip()`ed stdout differs from the file's, write the stdout to `environment.yaml`
    and commit that one path on the dispatch branch through `commit_paths`, then journal a new
    `dispatch-environment-yaml` INTENT and OUTCOME (paths, `committed`, the export's exit code), as the ruff step
    journals `dispatch-ruff-format`;
  - if the export fails, write nothing and journal the failure; the gate below then refuses.
  - The pure part (does the diff call for it; do the two texts differ) lives in a new `core/` module, and the process
    and file I/O stay at the edge (AD-4), as `core/dispatch_ruff_format.py` does.
- **Refuse what still differs (the gate).** A fourth cross-surface rule, `environment-yaml`, matches a changed
  `environment.yaml` or `pixi.toml` and runs `pixi run -e pyforge-guild steward provision --verify`, steward's
  existing comparison, so the dispatch gate and the repo's own sync check are one comparison. Run in a dispatch
  worktree it checks that worktree's file: each dispatch worktree has its own `pyforge-guild` env whose editable
  `pyforge-steward` points into the worktree (`src_editable_impl_pyforge_steward.pth`, checked on
  `.worktrees/dispatch-pyforge-marshal-47.1`), and steward's `repo_root()` walks up from that module. A non-zero exit refuses
  under `MRS-GATE-015` like the other cross-surface rules (`dispatch_verify.py:974`-`:1000`), and for this rule the
  finding message also names `environment.yaml` and the fix command `pixi project export conda-environment -e build
  2>/dev/null > environment.yaml`. Story 85.7's fix turn sees it as it sees any `MRS-GATE-015` refusal.
- **Every landing path verifies,** so nothing else changes: the supervisor's first landing, the land-only paths of
  Stories 29.2 and 83.10 (they re-verify), and the drain all run `evaluate_dispatch_verification`.
- **Unchanged:** the idle checkpoint, the other three cross-surface rules, the station `verify_commands`, the surface
  guard, `lint-types`, the landing's CI wait, Story 85.7's one fix turn and its flag, and every landing and promotion
  rule.

Ledger key: `91-1-a-corrupt-environment-yaml-never-lands`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-170 (← `spec-marshal-single-story-dispatch` CAP-12): Stories
  22.12 and 22.14, the cross-surface gate that runs each touched shared surface's own check. This story adds the rule
  for `environment.yaml` and `pixi.toml`. With it, CAP-161 (← `spec-marshal-single-story-dispatch` CAP-3, Story 22.3:
  verification before any landing), under which Stories 83.9 and 83.15 apply their pre-verify ruff step, the pattern
  the regeneration step follows. It fixes their realization, so it mints no CAP and changes no `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it restores intended behaviour (a
  derived file equals its generator's output), and a flag would keep the defect reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-10 (a corrupt environment.yaml landed).
  Operator ruling 2026-10-10, verbatim: "yes mint both stories".

## Acceptance Criteria

The fixtures write the corrupt file as `main` holds it: the export's text with the line `\x1b[33m WARN\x1b[0m Using
local manifest <worktree>/pixi.toml rather than <primary>/pixi.toml from environment variable
\`PIXI_PROJECT_MANIFEST\`` first. The exporter is a fake `ProcessPort` in unit tests, returning that warning on stderr
and the clean text on stdout.

- **AC1 — The warden 15.1 shape is repaired before verification.**
  - **Given** a dispatch worktree whose diff against `origin/main` includes the corrupt `environment.yaml` (and no
    `pixi.toml` change), and an exporter that writes the warning on stderr and the clean text on stdout.
  - **When** the supervisor runs `_run_and_journal_verification`.
  - **Then** before any verify command runs, `environment.yaml` equals the exporter's stdout byte for byte, the warning
    appears nowhere in it, one commit on the dispatch branch changes only that path, and the run journal holds a
    `dispatch-environment-yaml` INTENT and OUTCOME naming `environment.yaml` with `committed: true`.
  - **And** the same holds when only `pixi.toml` changed and the file was not regenerated at all.
- **AC2 — A file that still differs never lands.**
  - **Given** the corrupt file and an exporter that fails (non-zero exit), or a regeneration that cannot commit.
  - **When** verification runs **Then** the `environment-yaml` cross-surface rule runs `pixi run -e pyforge-guild
    steward provision --verify`, the verdict is `refused` with an `MRS-GATE-015` finding whose message names
    `environment.yaml` and `pixi project export conda-environment -e build 2>/dev/null > environment.yaml`, and the
    verification envelope's `cross_surface_checks` holds the rule with its touched paths.
  - **And** a refused run is never landed (the existing refusal path); with `pyforge.marshal.verify_fix_loop` on, Story
    85.7's fix turn receives the failed command and its output like any `MRS-GATE-015` refusal.
- **AC3 — A clean file costs nothing.**
  - A diff whose `environment.yaml` already equals the export: no commit and no `dispatch-environment-yaml` entry; the
    rule runs once and passes.
  - A diff that touches neither path: the exporter never runs and the rule is not matched (`cross_surface_check`
    reads `checked: false` as today when no rule matches).
  - The rule runs once however many of its paths changed, keyed on the diff alone, never on the dispatching station.
- **AC4 — One comparison, steward's.** A test pins the rule: id `environment-yaml`, command `pixi run -e pyforge-guild
  steward provision --verify`, matched on exactly `environment.yaml` and `pixi.toml`. Marshal never imports
  `pyforge.steward`; the comparison itself stays covered by steward's own `tests/unit/test_provision_verify.py`. The
  refusal-message test drives the rule through a fake `ProcessPort` that exits 1 with steward's real output for the
  corrupt file.
- **AC5 — Everything else is unchanged.** Every existing marshal test passes, with one named exception:
  `test_cross_surface_rules_table_pins_all_three_rules` (`tests/unit/test_gate.py:541`-`:549`) pins four rules,
  `environment-yaml` last, and keeps its mutation purpose. The dev names any other changed expectation, with its
  reason, in the Spec Change Log. The idle checkpoint's tests (`tests/unit/test_worktree_checkpoint.py`) are untouched.
- **AC6 — Mutation.**
  - Writing the exporter's stderr (or stdout and stderr together) into the file fails AC1.
  - Dropping the regeneration step fails AC1.
  - Dropping the `environment-yaml` rule, or matching it on `environment.yaml` alone, fails AC2 and AC1's `pixi.toml`
    case.
  - Dropping the fix command from the finding message fails AC2.

## Boundaries & Constraints

**Always:**
- Regenerate only from the exporter's stdout; never edit the file's text by hand or by pattern (no "strip the WARN
  line"), so a future pixi message of another shape is handled the same way.
- Keep the decision pure (`core/`, AD-4) and the process, file and git I/O at the edge, through `ProcessPort` and the
  committing VCS port.
- Journal the regeneration's INTENT before acting on it (AD-6).
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal` and `spec-pyforge-core` (it co-governs `core/gate.py`), plus every co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never land a story whose `environment.yaml` differs from the export when the story's diff touches it or `pixi.toml`.
- Never run the exporter, or the rule, for a diff that touches neither path.
- Never change steward's `provision --verify`, the idle checkpoint, the landing's CI wait or Story 85.7's budget here.
- Never enable a GitHub workflow or change a GitHub setting from this story.

**Residual risk:**
- A hand-landed branch (a chain or hygiene PR) never passes through dispatch verification. The repo-scope detector that
  catches it there is steward's: deferred-work row `DW-marshal-91-1-1` in
  `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`.
- An intermediate `wip:` checkpoint may still carry a bad file on the dispatch branch; the landed tree never does.

## I/O & Edge-Case Matrix

| Diff touches | `environment.yaml` vs export | Exporter | At `909a725e16` | After |
|---|---|---|---|---|
| `environment.yaml` | WARN line first | ok | lands | regenerated, committed, journaled; rule passes; lands |
| `pixi.toml` only | stale (not regenerated) | ok | lands | regenerated, committed, journaled; rule passes; lands |
| `environment.yaml` | WARN line first | fails | lands | nothing written; rule refuses `MRS-GATE-015` with the fix command |
| `environment.yaml` | equal | ok | lands | no commit, no journal entry; rule passes |
| neither | any | not run | lands | unchanged: no regeneration, rule not matched |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-10 (a corrupt environment.yaml landed)
  entry.
- Epic: Epic 91 (a new fix epic, because Epics 22 and 83, which shipped the cross-surface gate and the pre-verify
  step, are `done`).
- Ledger key: `91-1-a-corrupt-environment-yaml-never-lands`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `[epic_surfaces]` `"91"` in `marshal-policy.toml` (the default surface and every Spec memlog).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- The four mutations of AC6 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- On the next dispatch whose diff touches `environment.yaml` or `pixi.toml`, its run's `journal.jsonl` holds a
  `dispatch-environment-yaml` pair or a passing `environment-yaml` entry under `cross_surface_checks`, and the landed
  `environment.yaml` parses with `yaml.safe_load`.

## Named, not fixed here

- **A repo-scope detector for hand-landed branches.** `detectors-ci` and `pr-preflight` do not compare
  `environment.yaml` with the export, and `steward provision --verify`'s remedy text omits `2>/dev/null`. Steward
  owns environment checks (`provision --verify`, `validate-fast`'s env-sync step), so the detector is steward's:
  `DW-marshal-91-1-1` in steward's deferred-work ledger.
- **The disabled CI lint.** `staged-recipes-linter.yml` (the repo's only CI sync lint) is `disabled_manually`.
  Re-enabling a workflow is an operator act and outside this story.
- **`marshal-policy.toml`'s `environment-yaml-sync` landing rule** requires a `linter` check that no active workflow
  emits; only `marshal deploy batch-pr` reads `landing_rules`.
- **`main`'s current corrupt file** is repaired by whichever lands first, atlas 25.1's PR #2104 or this story's own
  first dispatch that touches the file; this story adds no hand repair.
