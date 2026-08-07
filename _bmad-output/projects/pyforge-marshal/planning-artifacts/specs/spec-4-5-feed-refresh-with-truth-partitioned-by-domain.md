---
title: 'Feed refresh with truth partitioned by domain'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '7ce11b7fb508867eeb30876e6368e029d577a181'
---

<intent-contract>

## Intent

**Problem:** two facts about the same story can come from two different sources that can disagree — bmad-loop's own harness state (`TaskPhaseSnapshot.commit_sha`, read via `RunStatusSnapshot`, Story 3.7/3.8's own machinery) is a CLAIM about a repository fact (a commit exists for this story), while `core.promotion.merged_story_keys` (Story 4.1) is git's own ACTUAL answer. Nothing today reconciles the two, or declares which one a derived report should trust for which field — the exact class of bug AD-33 exists to prevent (a sibling project's own sprint ledger drifted to 26/32 against an actual 32/32 for precisely this reason).

**Approach:** `marshal deploy refresh-feed` builds one reconciled report from two independently-gathered sources: git-sourced repository facts (via `VcsPort`, reusing Story 4.1's `merged_story_keys`) and journal/harness-sourced process facts (via `core.journal.fold` and `RunStatusSnapshot`). Every harness-derived assertion ABOUT a repository fact (`commit_sha`, in-progress-phase-implying-not-yet-merged) is carried as a `claimed_*` field, cross-checked against git's own answer — a mismatch is a reported reconciliation finding, never silently resolved and never rendered as if it were the trusted value. When policy's `landing_resync` (Story 4.7) is `True`, configured resync commands run; re-running `refresh-feed` against an unchanged state is a provable no-op.

## Boundaries & Constraints

**Always:**
- **Domain partition is explicit per field, not just prose.** `core/status.py` gains a small typed shape — `DomainField` (or similar; a frozen dataclass wrapping a value with its `domain: Literal["git", "journal"]`) — used for every field `refresh-feed`'s report emits. A field whose value came from `VcsPort`/`merged_story_keys` is tagged `"git"`; a field derived from `core.journal.fold`/`RunStatusSnapshot` is tagged `"journal"`. No field is ever populated by reading the OTHER domain's source, by construction — the type itself makes "which domain" a a first-class, checkable fact, not a comment.
- **`claimed_*` fields are journal-sourced assertions about repository facts, never rendered as the trusted value.** For every story in the current wave, `RunStatusSnapshot`'s per-task `commit_sha` (when non-`None`) becomes `claimed_commit_sha` in the report — informational only. The REPORTED "is this story durable" answer always comes from `merged_story_keys` (git), never from the presence of a `claimed_commit_sha`. When `claimed_commit_sha` is set but the story does NOT appear in `merged_story_keys`'s result (the harness believes a commit landed; git disagrees), that mismatch is a registered reconciliation `Finding` — reported, never silently resolved by trusting either side.
- **Resync commands are policy-declared, matching `verify_commands`'s own allowlist shape** — new STATIC key `landing_resync_commands: tuple[str, ...]` (default `()`), validated identically to `verify_commands`. Executed via `ProcessPort` (the same allowlist-only execution discipline AD-17 already requires for `verify_commands` — no arbitrary command channel) ONLY when `effective.landing_resync.value` is `True`; when `False`, `refresh-feed` still produces its reconciliation report but skips the resync-command step entirely, reported in the envelope (`data.resync_skipped: true`).
- **Provable no-op**: re-running `refresh-feed` against an unchanged repository/journal state must produce a byte-identical report (excluding an explicit timestamp field, if one exists) and, if any resync command writes a file, that file must be unchanged on a second run — proven by a test that runs `refresh-feed` twice against the same fixture and diffs the two outputs.
- **Discrepancies are reported, never silently resolved** — a `claimed_*`/git mismatch produces a `Finding`; `refresh-feed` does not attempt to "fix" the journal or override git; it only reports.

**Never:**
- No derived field sources a repository fact from the journal or a process fact from git — enforced by `DomainField`'s own construction discipline, not just documentation.
- No arbitrary resync command — always through the `landing_resync_commands` policy allowlist, same discipline as `verify_commands`.
- Do not touch `cli/land.py`/Story 4.8's own surface, or Story 4.9's "derived surfaces regenerate on `main`, never merged from a home" rule (this story produces the REPORT and runs configured resync commands; where those regenerated artifacts ultimately get committed/merged is Story 4.9's own concern).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `claimed_commit_sha` set, story IS in `merged_story_keys` | Harness and git agree | No finding; report shows both, consistent | No error |
| `claimed_commit_sha` set, story NOT in `merged_story_keys` | Harness claims a commit; git disagrees | Registered reconciliation `Finding`; report does NOT claim the story is durable | No error, reported |
| `claimed_commit_sha` is `None` (harness has no opinion) | No claim to reconcile | No finding; git's own answer stands alone | No error |
| `landing_resync = True`, commands configured | Policy declares `landing_resync_commands` | Each command runs via `ProcessPort`; failures reported, not silently swallowed | Registered finding on command failure |
| `landing_resync = False` | Toggle off | Resync step skipped entirely; `data.resync_skipped: true` | No error |
| Re-run against unchanged state | No new commits, no new journal entries | Byte-identical report (minus any timestamp); no-op proven by test | No error |
| No wave / nothing to reconcile | Empty state | Clean report, empty findings | No error |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/status.py` — EDIT. `DomainField` frozen dataclass; a pure reconciliation function taking git-sourced facts + journal-sourced `claimed_*` facts and producing the tagged, reconciled report plus any mismatch `Finding`s.
- `src/pyforge/marshal/core/policy.py` — EDIT. New STATIC key `landing_resync_commands: tuple[str, ...]`, validated like `verify_commands`.
- `src/pyforge/marshal/schemas/policy.json` — EDIT. New property.
- `src/pyforge/marshal/cli/deploy.py` — EDIT. New `refresh-feed` action: gathers git facts (reusing Story 4.1's machinery), gathers journal/harness facts (`RunStatusSnapshot`), calls `core/status.py`'s reconciliation function, runs resync commands via `ProcessPort` when `landing_resync` is true.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New code for a `claimed_*`/git reconciliation mismatch, and a resync-command-failure code (or reuse `verify_commands`' own failure-classification pattern if directly applicable).
- `tests/unit/test_status.py` — EDIT. `DomainField`/reconciliation matrix.
- `tests/unit/test_deploy.py` — EDIT. `refresh-feed` end-to-end, including the provable-no-op test.

## Tasks & Acceptance

**Execution:**
- [x] `core/status.py` — `DomainField`, reconciliation function.
- [x] `core/policy.py` + `schemas/policy.json` — `landing_resync_commands`.
- [x] `cli/deploy.py` — `refresh-feed` action.
- [x] `core/findings.py` / `core/verdict.py` — register new codes.
- [x] Unit tests for every new/edited module, including the full I/O matrix above and the provable-no-op test.
- [x] `deferred-work.md` — log any scope narrowed during implementation.

**Acceptance Criteria:**
*(Story 4.5's ACs from `epics.md`, preserved as the contract of record.)*
- Given a landed wave, when feed refresh runs, then git is the sole authority for repository facts (merged/not, tree revision, branch existence, commit subject) and the journal is the sole authority for process facts (transitions, verdicts, escalations, consumption) (AD-33)
- And no derived artifact sources a repository fact from the journal or a process fact from git; each derived field declares its canonical domain
- And a journal claim about a repository fact is stored as `claimed_*` and is only ever an input to a reconciliation finding, never a rendered value
- And console data regeneration is invoked where configured
- And discrepancies are reported, never silently resolved
- And regenerating a derived artifact when nothing changed is a provable no-op (AD-12)

## Design Notes

**Why `TaskPhaseSnapshot.commit_sha` is this story's own worked example of a "journal claim about a repository fact."** It's the one field already flowing through this codebase (Stories 3.7/3.8) that is BOTH harness/journal-sourced AND asserts something git could independently confirm or deny — exactly the shape AD-33 warns about. Using it as the concrete `claimed_*` case (rather than inventing a hypothetical one) grounds this story in a real, already-shipped field instead of a speculative design.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold.

**Manual checks (if no CLI):**
- Run `marshal deploy refresh-feed` twice in a row against this repo's own state and confirm the second run's report is identical to the first (the provable no-op).

## Spec Change Log

- **Journal-facts gathering resolves `HarnessPort.run_status_snapshot` via `cli/spin.py`'s existing "most recent run" machinery, not `core.journal.fold`.** The Approach paragraph names `core.journal.fold` as a journal-facts source, but Marshal's own journal fold accumulates Marshal's OWN journal entries (run intents/outcomes/observations) — it has no notion of bmad-loop's own `state.json`/`TaskPhaseSnapshot.commit_sha`, which only `HarnessPort.run_status_snapshot` reads (exactly what the Design Notes section already names as this story's own worked `claimed_*` example, and what the Code Map's own `cli/deploy.py` bullet says to call). `run_status_snapshot` needs a HARNESS run id, which Marshal resolves from ITS OWN journal via `cli/spin.py::_resolve_harness_run_id_for_resume` (the same lookup `marshal factory resume` already uses) against `cli/spin.py::_latest_run_dir`'s own most-recent-run-for-this-slug primitive — reused rather than reimplemented, per this project's own "no second implementation of the same fact" convention. No new CLI flag: `refresh-feed` always reconciles against the current state (the most recent run), not a specific historical one — logged as a scope decision in `deferred-work.md` (no `--run` override).
- **`landing_resync_commands` failures mint two new codes (`MRS-DEPLOY-019`/`020`) rather than reusing `core.gate.classify_outcome`'s `MRS-GATE-*` codes.** The Code Map's own bullet offered "reuse `verify_commands`' own failure-classification pattern if directly applicable" as an alternative — it is not directly applicable: `core.gate.classify_outcome` hardcodes `MRS-GATE-001` for a non-zero exit, a different policy key's own area (AD-15 codes are stable per caller/scenario). `core/status.py::classify_resync_outcome` mirrors that function's SHAPE exactly (the `result is None` convention, the signal-vs-exit-code framing) with this story's own codes instead; the CLI-boundary execution recipe (`shlex.split`, `.gate._bare_shell_metacharacters`'s bare-shell-syntax guard, `ProcessPort.run`) is reused verbatim from `cli/gate.py::run_evaluate`, per the story's own Always bullet ("the same allowlist-only execution discipline AD-17 already requires for `verify_commands`").
- **No `claimed_*` field for "in-progress-phase-implying-not-yet-merged."** The Approach paragraph's first sentence names two harness-derived assertions ("`commit_sha`, in-progress-phase-implying-not-yet-merged"), but every other section (Boundaries' own Always bullet, the I/O matrix, the Design Notes, and the Acceptance Criteria) names only `commit_sha`/`claimed_commit_sha` as this story's concrete worked example. `TaskPhaseSnapshot.phase` is reported alongside `commit_sha` in `RunStatusSnapshot.tasks` but is not itself a claim ABOUT a repository fact the way `commit_sha` is (AD-33's own named failure mode is a commit CLAIM disagreeing with git, not a phase label) — so a second `claimed_phase` field was not added; `phase` was simply out of scope for the one worked reconciliation case this story implements.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 3, medium 3, low 2)
- defer: 2
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **A whitespace-only `landing_resync_commands` entry crashed the whole `refresh-feed` invocation instead of being reported.** `shlex.split(" ")` parses CLEANLY to an empty token list (distinct from a `ValueError`), which then reached `ProcessPort.run` with no `argv[0]` to exec — most real `ProcessPort` implementations raise for an empty argv, uncaught by the existing `except ProcessError` guard alone in every case. Fixed: `_run_resync_commands` now checks for an empty token list after `shlex.split` and reports it as a malformed entry (reusing `MRS-DEPLOY-019`) rather than ever calling `process.run([], ...)`. New test: `test_refresh_feed_whitespace_only_resync_command_is_reported_not_crashed`.
  - `[high]` `[patch]` **Several functions documented as "never raises"/"reported, never silently swallowed" only caught a narrow exception type.** `_run_resync_commands`'s `process.run` catch was broadened to `(ProcessError, OSError, TimeoutError)`; `_gather_claimed_commits`'s `harness.run_status_snapshot` call is now wrapped in the SAME guard tuple `adapters/harness_bmadloop.py`'s own implementation uses internally to hold its own "never raises" promise; `_gather_claimed_commits`'s `fs.exists(home)` call was broadened to `(FsError, OSError)`. The `identity.normalize(task.story_key)` catch and the `candidate.is_file()`-raises-`OSError`-then-`_read_project_policy` path were both individually verified ALREADY correct (the former because `normalize` itself guards non-`str` input; the latter because `_read_project_policy`'s own `open()` call already wraps every `OSError` into `PolicyIOError`) — locked in with new regression tests rather than changed. New tests: `test_refresh_feed_resync_command_oserror_is_reported_not_crashed`, `test_refresh_feed_degrades_gracefully_when_run_status_snapshot_raises`, `test_refresh_feed_degrades_gracefully_when_fs_exists_raises`, `test_gather_claimed_commits_skips_a_malformed_story_key_not_fatal`, `test_refresh_feed_policy_is_file_probe_oserror_still_reports_policyioerror`.
  - `[high]` `[patch]` **`reconcile_feed_domains`'s `claim_by_key` dict comprehension silently kept only the LAST of multiple same-`story_key` claims, by accidental iteration order.** A realistic shape (a story's own dev/review/done-phase snapshots, each potentially carrying a different `commit_sha`) resolved by whichever `RunStatusSnapshot.tasks` happened to iterate last — undermining the provable-no-op requirement, since that ordering is not a guaranteed-stable contract. Fixed: `ClaimedCommit` gained a `phase` field; a new `_select_claim` helper picks the winning claim by an explicit, deterministic precedence (a non-`None` `claimed_commit_sha` outranks `None`; among non-`None` entries, the later lifecycle `phase` — mirroring `bmad_loop.model.Phase`'s own declared ordering, ported not imported, per AD-3/AD-4 — wins; ties resolve to the first entry in `state.json`'s own stable iteration order). New tests: `test_reconcile_duplicate_story_key_prefers_later_phase_non_none_sha`, `test_reconcile_duplicate_story_key_prefers_non_none_sha_over_none`.
  - `[medium]` `[patch]` **The provable-no-op guarantee was only tested against a trivial deterministic command (`"true"`), which trivially never varies.** `_run_resync_commands`'s report embeds each command's raw `stdout`/`stderr` verbatim, which any realistic resync command (one printing a timestamp, an object count, etc.) would vary run to run even against unchanged repository state — the existing test could not have caught a claim that stdout must be byte-identical too. Scoped correctly: the RECONCILIATION portion of the report (`data.stories` plus every finding) is what the no-op guarantee actually covers, never a resync command's own volatile raw output. New test: `test_refresh_feed_noop_reconciliation_holds_even_with_volatile_resync_output` (a fake process port returning different stdout each call; asserts `data.stories`/`findings` still match while raw stdout differs).
  - `[medium]` `[patch]` **`run_refresh_feed`'s three early-return paths omitted `data["resync_commands"]` from the envelope, unlike the happy path.** An inconsistent JSON shape across exit branches, contradicting AD-14's "one envelope shape for every command". Fixed: both `data["resync_skipped"]` and `data["resync_commands"]` are now defaulted (`True`/`[]`) at the very top of the function, before any early-return path, so every exit carries the same envelope keys. New test: `test_refresh_feed_early_refusal_still_includes_resync_commands_key`.
  - `[medium]` `[patch]` **`_run_resync_commands` called `process.run` with no `timeout_s`, so a hung policy-declared command (a stalled network fetch) could hang the whole `refresh-feed` invocation indefinitely.** Fixed: a new `_RESYNC_TIMEOUT_S = 120.0` module constant (reusing `adapters/vcs_git.py::_GIT_PUSH_TIMEOUT_S`'s own precedent for a network-facing write operation, since `cli/gate.py`'s own `verify_commands` execution deliberately has NO timeout precedent to reuse — its own docstring explains why) is now passed to every `process.run` call. New tests: `test_refresh_feed_resync_command_passes_a_real_timeout`, `test_refresh_feed_resync_command_timeout_is_reported_not_hung`.
  - `[low]` `[patch]` **`data["resync_skipped"]` alone could not distinguish "attempted, nothing configured to run" from "a command actually ran".** Verified the two ARE already distinguishable via the combination of `resync_skipped` and `resync_commands` (`resync_skipped=False` + `resync_commands=[]` means "attempted, nothing configured"; `resync_skipped=True` + `resync_commands=[]` means "skipped, policy toggle off") — no behavior change; a clarifying comment was added at the call site rather than a new field.
  - `[low]` `[patch]` **The `MRS-STATUS-001` finding message hardcoded the internal implementation detail "`RunStatusSnapshot`'s own per-task `commit_sha`" into user-facing text.** Rephrased in plain domain terms: "the run harness recorded commit {sha!r} for this story, but git does not confirm it as merged". No test asserted the old exact wording, so no test change was required beyond the existing substring checks (`"2.1" in finding.message`, `"cafebabe" in finding.message`), which still hold.
- deferred (not fixed in this pass, appended to `deferred-work.md` as a NEW entry):
  - `[low]` (D1) Zero test coverage for the default `--format text` output path (`_render_text_refresh_feed`) — every existing test explicitly requests `--format json`. Low risk (a straightforward pure projection of the same already-tested envelope data, mirroring this module's other under-tested `_render_text*` siblings), but genuinely zero direct coverage. Should be covered in a future pass.
  - `[low]` (D2) `_run_resync_commands`'s own docstring cross-references `_gather_claimed_commits`'s comment for its local-import rationale, but that comment actually explains a different, unrelated import cycle (`cli.spin <-> cli.init`, not `cli.deploy -> cli.gate -> cli.init`). Purely cosmetic doc-comment misattribution; low-value fix, not urgent.
- rejected (noise, already-deliberate, or already captured): none this pass.

</intent-contract>

## Suggested Review Order

**Domain-partition core**

- `DomainField` and `reconcile_feed_domains`, including the P3 deterministic claim-precedence fix for duplicate story keys.
  [`status.py:383`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py#L383)

**CLI orchestration**

- `run_refresh_feed`: the P5 uniform envelope shape across every exit path.
  [`deploy.py:2496`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L2496)

- `_run_resync_commands`: the P1 empty-argv guard, P2 broadened exception handling, P6 timeout.
  [`deploy.py:2402`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L2402)

- `_gather_claimed_commits`: the P2 broadened exception handling for `run_status_snapshot`/`fs.exists`.
  [`deploy.py:2292`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L2292)

**Tests (peripherals)**

- Reconciliation matrix, including the P3 duplicate-claim precedence test.
  [`test_status.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_status.py#L1)

- `refresh-feed` end-to-end, including the P4 correctly-scoped no-op test.
  [`test_deploy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py#L1)
