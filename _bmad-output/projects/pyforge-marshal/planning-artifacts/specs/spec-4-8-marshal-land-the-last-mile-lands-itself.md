---
title: 'marshal land -- the last mile lands itself'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '93061c9511e4707c2cf68f68afebc4b72005e317'
---

<intent-contract>

## Intent

**Problem:** every landing primitive up to this story is a piece an operator (or a future scheduler) must still sequence by hand: `marshal deploy batch-pr` opens/updates a PR and applies labels, but never merges it; `marshal deploy land-story` merges DIRECTLY to `main` with no PR at all (a manual, `--justification`-gated escape hatch, not the ordinary path); `core/landing.py`'s `LandingRule`/`rule_applies` (Story 4.7) declare which checks/labels a repo demands but nothing evaluates whether they are actually satisfied. A run that ends with "the batch PR is open and green" has not actually landed anything — "somebody should open a PR" becomes "somebody should notice CI went green and click merge". FR-60/AD-40 close this gap: one command that takes a wave from "gates passed" to "merged, branch retired, feed resynced" with no human in the sequencing loop, and refuses — loudly, via a registered finding, never a silent force — the instant a required check is red or an advisory finding sits unacknowledged.

**Approach:** `cli/land.py` (NEW top-level `marshal land <slug>` command, sibling to `deploy`/`gate`/`init`, not nested under `deploy`) orchestrates three already-shipped primitives plus one new one:
1. Wave discovery + hygiene preflight + PR open/update + label application — reuses `cli/deploy.py`'s own already-shipped private helpers (`_evaluate_hygiene`, `_gather_gate_verdicts`, `_batch_pr_title`/`_batch_pr_body`/`_batch_pr_redact`, `_DeployRun`/`_deploy_writer_id`/`_reconcile_open_intents`, `promotion.merged_story_keys`) via `from . import deploy` — never a second, drifting reimplementation of `batch-pr`'s own wave/hygiene/PR logic. `run_land` does NOT call `run_batch_pr` itself (that would double-emit an envelope); it imports and calls the SAME underlying helpers `run_batch_pr` already calls.
2. Required-check satisfaction — a NEW pure read against `ForgePort.check_run_status` (Story 4.4) for every `LandingRule` (Story 4.7's `core/landing.py`) whose `rule_applies` fires against this wave's changed paths and carries a `required_check`. A single poll per invocation, never an in-process sleep loop (this package's own idempotent/re-entrant convention — AD-22's detached-execution-as-default already assumes the operator or a scheduler re-invokes; a still-pending check is `Verdict.WARN`, "not yet ready, re-run later", never a hard refusal; only a `"failure"`/`None`-after-the-check-should-exist read is a refusal).
3. Merge + branch retirement in ONE `ForgePort` call — a NEW `merge_pr` method on `ForgePort`/`GhForge` (`gh pr merge <number> --<strategy> [--delete-branch]`), because `gh pr merge --delete-branch` already atomically performs both AC clauses ("merges by the declared strategy" + "retires the branch") as a single forge-side write; adding a second, separate `delete_branch`-style forge call would just be two round-trips racing each other for no benefit.
4. Resync — reuses `cli/deploy.py::run_refresh_feed`'s own already-shipped machinery (Story 4.5) the SAME way step 1 reuses `batch-pr`'s: imported and called in-process, never shelled out to a second `marshal` invocation.

"Unacknowledged advisory finding" reuses `cli/init.py`'s ALREADY-SHIPPED acknowledgement store (`_ack_state_path`/`_read_acknowledged`, Story 1.7) rather than inventing a second acknowledgement mechanism: any WARN-severity finding this command's own hygiene/gate-verdict gathering surfaces must have its `code` already present in that shared, persisted set, or landing refuses — exactly like `land-story`'s own "must be exactly clean" precedent, but re-entrant (an operator acks once via `marshal preflight --acknowledge <code>`; every subsequent unattended `marshal land` run honors it, no per-run flag).

## Boundaries & Constraints

**Always:**
- **`cli/land.py` is a NEW top-level subcommand** (`marshal land <slug>`, wired in `cli/main.py` alongside `config`/`init`/`gate`/`deploy`/`factory` — NOT nested under `deploy`; Code Map is explicit: `cli/land.py`, not a new `deploy` action). One required positional `slug` argument, same `_is_valid_project_slug` precondition every other deploy-family command checks first.
- **Reuse, never reimplement.** Wave discovery (merge-base + `commit_subjects` + `promotion.merged_story_keys`), the hygiene preflight (`_evaluate_hygiene`), gate-verdict gathering for the PR body (`_gather_gate_verdicts`), PR title/body assembly + redaction (`_batch_pr_title`/`_batch_pr_body`/`_batch_pr_redact`), and the Story 4.6 idempotence machinery (`_DeployRun`, `_deploy_writer_id`, `_reconcile_open_intents`, `Phase`) are ALL imported from `cli/deploy.py` (module-level private helpers, exactly like `cli/gate.py::evaluate_gate` is already reused in-process by `land-story`) — this story adds zero new wave-discovery or hygiene logic.
- **The malformed-`landing_rules`-hard-refuses precondition** (`batch-pr`'s own P1 review fix: a composition-time `MRS-POLICY-002` ERROR naming `'landing_rules'` in its message is a hard stop BEFORE any forge call, never a silent fall-back to an empty rule set) applies here identically — copy the exact guard, not a softened variant.
- **PR open/update+labels is byte-for-byte the same sequence `batch-pr` already performs** (find_open_pr -> base-branch match check -> reconcile open intents -> re-pin head sha immediately before the write (TOCTOU close) -> create_pr/update_pr -> add_labels), reusing the SAME helpers. `marshal land`'s only NEW work starts once the PR (freshly opened/updated OR already-existing-and-current) is in hand.
- **Required-check evaluation is ONE poll per invocation, never a blocking wait loop.** For every `LandingRule` in `effective.landing_rules.value` where `landing.rule_applies(rule, changed_paths)` is `True` and `rule.required_check` is not `None`: call `forge.check_run_status(repo_ref, ForgeRef(head_sha), ForgeRef(rule.required_check))` exactly once. `"success"` -> satisfied. `"failure"`/any other non-`None` non-`"success"` conclusion (e.g. `"cancelled"`, `"timed_out"`) -> a registered ERROR/`Verdict.GATE_FAILED` finding, merge refused. `None` (check has not run at all against this sha, or has not yet concluded) -> a registered WARN/`Verdict.WARN` finding ("required check `<name>` has not yet concluded -- re-run `marshal land` once it has"), merge refused THIS run but the run is not an error-tier failure — mirrors `land-story`'s own strictness (no partial force) while staying idempotent (AD-8: an unevaluable/pending signal is treated as NOT-YET-SAFE-TO-ACT, never silently treated as passing).
- **Unacknowledged WARN-tier findings block the merge**, reusing `cli/init.py`'s existing `_ack_state_path()`/`_read_acknowledged(fs, path)` (Story 1.7) — a local import inside `run_land`, mirroring `run_land_story`'s/`run_batch_pr`'s own existing `from .init import _home_path` local-import convention (documented cycle-avoidance reason, copy verbatim). Any Finding this command's OWN hygiene/required-check evaluation appends with `severity is Severity.WARN` whose `code` is not in the acknowledged set is escalated to a registered ERROR finding at the END of evaluation (never silently dropped, never silently promoted without a NEW finding naming which code was unacknowledged) and blocks the merge. A finding whose code IS already acknowledged is reported but does not block.
- **Merge + retire is ONE `ForgePort.merge_pr` call.** NEW method: `merge_pr(self, repo: ForgeRef, number: int, strategy: str, *, delete_branch: bool) -> None`, implemented in `GhForge` as `gh pr merge <number> --repo <repo> --<merge|squash|rebase> [--delete-branch]`. `strategy` comes from `effective.landing_merge_strategy.value` (already a closed `{"merge","squash","rebase"}` vocabulary per Story 4.7 — `merge_pr` trusts its caller, no redundant re-validation). `delete_branch` is `effective.landing_branch_retirement.value` (already a plain `bool`). Raises `ForgeCommandError` on any `gh` failure, same shape as every other `GhForge` method.
- **A half-landed wave converges on re-run** (AC's own literal example: "PR open, checks green, merge never issued"). Achieved for free by making every step idempotent-by-construction rather than by a separate "resume" branch: `find_open_pr` finds the SAME PR on re-run (no duplicate create); the merged_story_keys "already landed" check (copied from `batch-pr`) short-circuits straight to branch-retirement+resync once the wave's own keys are reachable from `base`; `check_run_status` is re-read fresh each run (no cached "green" from a prior invocation is trusted).
- **Already-merged wave still retires+resyncs.** If `wave_keys` are all already reachable from `base` (the SAME `merged_story_keys`-against-`base` check `batch-pr`'s own P8-adjacent already-landed check performs) but the head branch STILL EXISTS (nothing retired it yet — e.g. a prior `marshal land` run merged the PR but crashed before `--delete-branch` completed, or GitHub's own web UI was used to merge without deleting the branch), this run's job is ONLY to retire the branch (best-effort: `vcs.delete_branch` if a local ref exists is out of THIS story's scope -- `merge_pr`'s own `--delete-branch` deletes the REMOTE branch as part of the merge call; if the merge already happened, this run has no remaining `merge_pr` call to make, so remote branch retirement is reported as `data["branch_retired"]: null` with a WARN finding naming that it could not be confirmed or re-driven post-hoc through this port) and resync -- never a fresh PR write.
- **Journal an intent BEFORE the merge, an outcome AFTER it succeeds** (AD-6, mirroring `land-story`'s/`batch-pr`'s own identical pattern) via `_DeployRun`/`Phase`, kind `"land-merge"` (a NEW `_LAND_MERGE_PR_KIND` constant in `cli/land.py`, distinct from `deploy.py`'s own `_LAND_MERGE_KIND` (`land-story`'s direct-merge kind) and `_BATCH_PR_WRITE_KIND` -- three distinct writer namespaces per AD-28, never conflated). A `merge_pr` failure leaves the intent open, no outcome written, per the story's own I/O matrix.
- **Every landing appends a journal verdict recording: checks required, checks passed, what merged, under whose authority** (`"marshal land (automated)"`, distinct from `land-story`'s own `--justification`-carrying manual authority string) — one OBSERVATION entry after a successful merge, redacted at capture exactly like `_journal_manual_landing`'s own convention (reuse that function's redaction helper `_land_redact_text` via `from . import deploy`, do not reimplement).
- **Resync reuses `run_refresh_feed` in-process**, imported from `cli/deploy.py` and called directly (mirrors how `land-story` calls `evaluate_gate` in-process) -- gated by `effective.landing_resync.value`; `False` skips resync entirely (`data["resynced"]: false`, no finding).
- **Nothing emitted carries an AI-attribution trailer** (FR-35, unchanged) -- the PR title/body assembly this story reuses from `batch-pr` already honors this; no new text-generation path in this story adds one.

**Never:**
- No new wave-discovery, hygiene, or PR-open/update logic -- 100% reused from `cli/deploy.py`'s existing private helpers.
- No blocking wait/sleep loop for CI checks -- one poll per invocation, converge on re-run (matches this package's session-long idempotent-re-entrant design, avoids inventing a new sleep primitive `ClockPort` does not offer).
- No silent force -- a red required check or an unacknowledged WARN finding is ALWAYS a registered finding and a refused merge, never an operator flag that bypasses either (mirrors teardown's own "no silent force" precedent literally -- there is no `--force` flag on this command at all).
- Do not touch `cli/init.py`'s `_ack_state_path`/`_read_acknowledged`/`_write_acknowledged` (Story 1.7, already shipped) beyond READING the acknowledged set -- this story never writes to it; acknowledging stays `marshal preflight`'s own action.
- Do not implement Story 4.9's derived-surfaces-regenerate-on-main-after-merge refinement or its FsPort lock -- this story calls the EXISTING `run_refresh_feed` as-is; 4.9 is the one that changes what resync means post-landing.
- Do not implement Story 4.10's fleet-wide sweep (multiple projects, batch retirement across the whole fleet) -- this story retires exactly ONE project's ONE branch, as a side effect of ONE merge call, for the wave it itself just landed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Malformed project slug | `slug` fails `_is_valid_project_slug` | Refused before any I/O | `MRS-POLICY-006` ERROR |
| Station branch does not exist | `loop/<slug>` unresolvable | Refused | `MRS-LAND-001` ERROR |
| Malformed `landing_rules` policy layer | A bad TOML entry | Hard refuse before any forge call (mirrors `batch-pr`'s P1 fix) | `MRS-LAND-002` ERROR |
| Empty wave (nothing to land) | No story keys since merge-base | Clean no-op, `data.opened/updated/merged: false` | No finding |
| Wave already fully merged into `base`, branch still exists | PR was merged out-of-band | Skip PR/checks/merge; attempt retire+resync only | `MRS-LAND-003` WARN if retire cannot be confirmed |
| Wave already fully merged into `base`, branch already gone | Fully converged | Clean no-op, `data.merged: true, data.branch_retired: true` (or already absent) | No finding |
| Fired `required_check` reads `"success"` for every applicable rule | All green | Proceeds to merge | No finding |
| Fired `required_check` reads `"failure"`/`"cancelled"`/etc. | A red check | Refused, no merge attempted | `MRS-LAND-004` ERROR, `Verdict.GATE_FAILED` |
| Fired `required_check` reads `None` (not yet concluded) | Still running | Refused THIS run, re-entrant on next invocation | `MRS-LAND-005` WARN, `Verdict.WARN` |
| A WARN-tier finding from this run's own hygiene/check evaluation, code NOT in the shared acknowledged set | Unacknowledged advisory | Merge refused | `MRS-LAND-006` ERROR (names the unacknowledged code) |
| Same WARN-tier finding, code IS in the acknowledged set | Operator already acked via `marshal preflight` | Merge proceeds, finding still reported (non-blocking) | Reported WARN, not escalated |
| `merge_pr` (gh) fails | Network/auth/conflict | Refused, intent left open (no outcome) | `MRS-LAND-007` ERROR |
| A half-landed wave (PR open, checks green, merge never issued) re-run | Prior invocation crashed after checks, before merge | Converges: re-checks (fresh reads), merges, retires, resyncs | No finding beyond the normal successful path |
| `landing_branch_retirement` is `False` | Policy opts out | `merge_pr` called with `delete_branch=False`; PR merges, branch stays | No finding |
| `landing_resync` is `False` | Policy opts out | Resync skipped entirely | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/cli/land.py` -- NEW. `add_land_subparser`, `run_land(args, *, vcs=None, fs=None, forge=None) -> int`, `_render_text_land`. Imports `cli/deploy.py`'s private helpers (`_evaluate_hygiene`, `_gather_gate_verdicts`, `_batch_pr_title`/`_batch_pr_body`/`_batch_pr_redact`, `_DeployRun`/`_deploy_writer_id`/`_reconcile_open_intents`, `run_refresh_feed`, `_land_redact_text`) and `cli/init.py`'s `_home_path`/`_ack_state_path`/`_read_acknowledged` -- both as LOCAL imports inside `run_land` (mirrors `run_land_story`'s own documented cycle-avoidance convention: `cli/init.py` imports `deploy`, so a module-level `from . import land` anywhere in that chain would cycle).
- `src/pyforge/marshal/ports/forge.py` -- EDIT. New `ForgePort.merge_pr(self, repo: ForgeRef, number: int, strategy: str, *, delete_branch: bool) -> None` Protocol method.
- `src/pyforge/marshal/adapters/forge_gh.py` -- EDIT. `GhForge.merge_pr` implementation (`gh pr merge <number> --repo <repo> --<strategy> [--delete-branch]`).
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register `MRS-LAND-001` through `MRS-LAND-007`.
- `src/pyforge/marshal/core/verdict.py` -- EDIT. Classify each new code into the lattice (`MRS-LAND-001/002/007` -> `ERROR`; `MRS-LAND-003/006` -> `ERROR`/`WARN` per the matrix above; `MRS-LAND-004` -> `GATE_FAILED`; `MRS-LAND-005` -> `WARN`).
- `src/pyforge/marshal/cli/main.py` -- EDIT. Import `land as land_cli`, wire `land_cli.add_land_subparser(subparsers)`.
- `tests/unit/test_land.py` -- NEW. Full matrix above, fake `VcsPort`/`FsPort`/`ForgePort` doubles (mirrors `test_deploy.py`'s own fake-port conventions).
- `tests/unit/test_forge_gh.py` -- EDIT. `merge_pr` argv-construction + error-translation tests.
- `tests/unit/test_main.py` -- EDIT. `land` subcommand wiring smoke test (mirrors the existing `deploy`/`gate` wiring tests).

## Tasks & Acceptance

1. **`ForgePort.merge_pr` + `GhForge.merge_pr`.** AC: unit tests cover `--merge`/`--squash`/`--rebase` argv construction, `--delete-branch` present/absent, and `ForgeCommandError` translation on a non-zero `gh` exit.
2. **Register + classify `MRS-LAND-001..007`.** AC: `test_findings_registry_completeness`-style meta-test (every registered code appears in `verdict.py`'s classification table) stays green.
3. **`cli/land.py::run_land` -- preconditions + wave discovery + PR open/update+labels (reused).** AC: byte-identical behavior to `batch-pr`'s own equivalent steps, verified by tests that assert the SAME helper functions are called (not reimplemented).
4. **Required-check evaluation.** AC: matrix rows for `"success"`/`"failure"`/`None` all covered; a wave with zero applicable `required_check` rules proceeds with no forge check-status calls at all.
5. **Acknowledgement gate.** AC: an unacknowledged WARN blocks; the same code, once present in `_read_acknowledged`'s set, does not.
6. **Merge + retire + journal.** AC: intent-before/outcome-after journal entries verified; a `merge_pr` failure leaves the intent open (a subsequent fold reports it via `open_intents`).
7. **Resync.** AC: `landing_resync=True` calls `run_refresh_feed` in-process exactly once; `False` skips it, `data["resynced"]: false`.
8. **Re-entrancy.** AC: a simulated "PR open, checks green, merge never issued" state (via fakes) converges to a full landing on the next `run_land` call with no duplicate PR/merge/label writes.
9. **`cli/main.py` wiring.** AC: `marshal land --help` succeeds; `marshal land <slug>` with no acting doubles exercises the real `GitVcs`/`LocalFs`/`GhForge` default construction path (smoke-level only).

## Design Notes

- **Why one poll, not a wait loop:** AD-22 already establishes detached execution as this package's default operating mode -- the operator or a scheduler (bmad-loop's own supervisor, or a future cron-style invocation) re-invokes `marshal` commands rather than any one command blocking for an unbounded external event. A `time.sleep`-based poll loop inside `run_land` would be the first place in this codebase where a CLI handler blocks on an external, unbounded-duration event, breaking that convention and needing a NEW `ClockPort.sleep`-style primitive this story's Code Map does not authorize. Treating "still pending" as a non-blocking WARN that simply asks for a re-run is both simpler and consistent with every other idempotent-re-entrant primitive already shipped (`land-story`, `batch-pr`, `promote`).
- **Why `merge_pr` folds retirement into one call rather than a separate `delete_branch`-on-`ForgePort` method:** `gh pr merge --delete-branch` is one atomic server-side action; a caller sequencing `merge` then a SEPARATE `delete-branch` forge call introduces a window where the merge succeeds but the second call could fail independently, needing its own retry/idempotence story for no real benefit -- `gh` already gives this atomically for free.
- **Why acknowledgement reuses `cli/init.py`'s store rather than a new one:** Story 1.7's `_ack_state_path`/`_read_acknowledged`/`_write_acknowledged` already exist for exactly this "the operator has seen and accepted this non-blocking finding" purpose (`marshal preflight --acknowledge <name>`). A second, `land`-scoped acknowledgement file would fragment "what has the operator already accepted" across two stores an operator would have to remember separately -- one shared store, one mental model.
- **Why `run_land` never calls `run_batch_pr` as a function:** `run_batch_pr` ends by calling `_emit`, which both constructs AND PRINTS an envelope and returns an int -- calling it in-process from `run_land` would either print a spurious second envelope (if not suppressed) or require threading a "don't print" flag through `_emit` that no other caller needs. Importing and calling the SAME private helpers `run_batch_pr` itself calls (one level below `_emit`) gets full reuse with a single envelope, matching `land-story`'s own precedent of reusing `evaluate_gate` (a function that returns a value, not one that emits) rather than reusing `run_evaluate` (the CLI-emitting wrapker) directly.
- **Already-merged-but-not-retired is reported, not silently accepted:** the matrix's `MRS-LAND-003` WARN exists because `ForgePort` has no "delete this branch on its own, independent of a merge" primitive (deliberately -- see the Design Note above), so a wave that landed by some OTHER path (a manual `gh pr merge` on the web UI, an operator's own `git push`) leaves this command with no forge-side action left to retire it through. Reporting rather than silently treating branch-still-exists as fine keeps the gap visible until Story 4.10's fleet-wide sweep (which DOES have a standalone retirement primitive) picks it up.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Spec Change Log

**1. `cli/deploy.py::run_refresh_feed` was split into `reconcile_feed` (pure value-returning core) + a thin `_emit`-calling wrapper — a necessary adaptation the spec's own "Resync reuses `run_refresh_feed` in-process" wording did not anticipate needing.** The spec's literal Design Notes text ("Resync reuses `run_refresh_feed`'s own machinery ... called directly") was implemented literally in the first pass and produced a real bug: `run_refresh_feed` ends by calling `_emit`, so calling it in-process from `run_land` printed a SECOND, spurious JSON/text envelope after `land`'s own — the exact failure mode the Design Notes explicitly warn `run_batch_pr` reuse must avoid ("would either print a spurious second envelope... or need a 'don't print' flag"). Fixed post-implementation by extracting `reconcile_feed(args, *, vcs, fs, process, harness) -> tuple[dict, list[Finding]]` (the SAME split shape `cli/gate.py`'s `evaluate_gate`/`run_evaluate` already established) — `run_refresh_feed` now calls `reconcile_feed` then `_emit`; `run_land` calls `reconcile_feed` directly and folds its returned findings into its own `findings` list, never printing a second envelope.

**2. `ForgePort.merge_pr` gained a REQUIRED `expected_head_sha: ForgeRef` parameter, not in the original Code Map signature — a safety-critical adaptation found by BOTH adversarial reviewers independently as their top finding.** The original signature (`merge_pr(repo, number, strategy, *, delete_branch)`) merged by PR NUMBER ALONE, with no re-verification that the PR's head commit was still the one this run's required-check poll actually evaluated — every OTHER write in this package's landing family (`land-story`'s `merge_branch`, `batch-pr`'s PR write) pins a captured sha and re-verifies it immediately before the write; this method's first version had no equivalent guard, leaving a real TOCTOU window between the check poll and the merge. Fixed: `expected_head_sha` is passed through to `gh pr merge --match-head-commit <sha>`, a native `gh` primitive that refuses atomically, forge-side, if the PR's current head has moved — closing the race without a caller-side re-check racing the same window it would be trying to close.

**3. The acknowledgement key for a still-pending required check is SCOPED (`_required_check_ack_key(rule_name, required_check, slug)`, carried on `Finding.path`), not the bare `MRS-LAND-005` finding code — a correctness-critical adaptation found by BOTH adversarial reviewers independently as their #1 finding.** Since a Finding's `code` must be a REGISTERED, closed-vocabulary value (never minted per-rule), the original implementation's acknowledgement check (`warn_finding.code not in acknowledged`) used that same fixed code for every project/rule/check — a single `marshal preflight --acknowledge MRS-LAND-005` would have permanently disabled the pending-check merge gate for EVERY future `land` invocation, everywhere, directly contradicting this story's own "re-entrant, never silently treated as passing" design. Fixed: the WARN `Finding`'s `path` field (an existing, optional field on the model, not a new one) carries the scoped key; the acknowledgement gate checks `warn_finding.path` against the ack set instead of `warn_finding.code`.

**4. `_evaluate_required_checks` is evaluated BEFORE the PR write (alongside hygiene), not after it as originally sequenced — an adaptation needed to fix a real label-loss bug, found by both reviewers independently.** `core.landing.LandingRule` explicitly permits a rule to declare BOTH `label` and `required_check`; the original implementation excluded any such rule from `_evaluate_hygiene`'s label-only subset (correctly, to avoid `_evaluate_hygiene`'s own ERROR-tier block on a merely-pending check) but never applied its label anywhere else, since the required-check evaluation ran only as a post-write merge gate and never collected labels. Fixed: `_evaluate_required_checks` now ALSO returns `fired_labels` for any rule whose check reads `"success"`, and is called once, before the PR write, so its labels fold into the SAME `add_labels` call `_evaluate_hygiene`'s own labels go through — still exactly one `check_run_status` poll per rule per invocation (the later merge gate reuses these same results, never re-polling).

**5. A required-check ERROR finding no longer suppresses an unrelated rule's pending WARN finding — a correctness fix found by the Edge Case Hunter.** The original implementation only extended `findings` with `required_warnings` inside the `if required_warnings:` branch guarding the acknowledgement gate, which the code never reached once `required_errors` triggered an early return — so a genuinely failed check on one rule silently dropped a DIFFERENT rule's "still pending" WARN from the printed envelope entirely. Fixed: `findings.extend(required_warnings)` now runs unconditionally, before the `required_errors` check.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 5 (critical 1, high 3, medium 1)
- defer: 2
- reject: 0
- addressed_findings:
  - `[critical]` `[patch]` **The acknowledgement gate checked the bare, invariant `MRS-LAND-005` finding code, so one acknowledgement permanently disabled the pending-check merge gate for every project/rule/check, forever.** Independently found by both reviewers as the single most severe finding against this story — see Spec Change Log entry 3. Fixed: acknowledgement is now scoped via `_required_check_ack_key`, carried on `Finding.path`. New tests: `test_required_check_pending_and_acknowledged_proceeds_to_merge` (updated to ack the scoped key, not the bare code).
  - `[high]` `[patch]` **`ForgePort.merge_pr` merged by PR number alone with no re-verification the PR's head still matched the commit this run's required-check poll evaluated — a real TOCTOU window between the check poll and the irreversible merge.** Independently found by both reviewers — see Spec Change Log entry 2. Fixed: `expected_head_sha` threaded through to `gh pr merge --match-head-commit`. New/updated tests: `tests/unit/test_forge_gh.py`'s `merge_pr` argv tests now assert `--match-head-commit <sha>`; `cli/land.py`'s merge call now passes `expected_head_sha=ForgeRef(head_sha)`.
  - `[high]` `[patch]` **A landing rule declaring BOTH `label` and `required_check` never got its label applied under `land` at all.** Independently found by both reviewers — see Spec Change Log entry 4. Fixed: `_evaluate_required_checks` now also returns `fired_labels`, evaluated before the PR write. New test: `test_rule_with_both_label_and_required_check_applies_label_once_satisfied`.
  - `[high]` `[patch]` **Resync (`reconcile_feed`, née `run_refresh_feed`) printed a second, spurious envelope after `land`'s own.** Found during implementation, before either adversarial review pass, and confirmed independently by the implementing agent's own self-reported design gap — see Spec Change Log entry 1. Fixed: `run_refresh_feed` split into `reconcile_feed` + a thin wrapper.
  - `[medium]` `[patch]` **A required-check ERROR for one rule silently dropped a different rule's pending WARN from the printed findings.** Found by the Edge Case Hunter — see Spec Change Log entry 5. Fixed: `findings.extend(required_warnings)` now runs unconditionally. New test: `test_required_check_error_does_not_drop_an_unrelated_rules_pending_warn`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[low]` D1: the "already landed, branch still exists" shortcut's `MRS-LAND-003` WARN never checks the found PR's own base branch, unlike the main path's `existing.base != base` guard — an unrelated PR sharing the head branch name but targeting a different base is reported identically to a real one. No write happens in this branch either way.
  - `[low]` D2 (inherited from `batch-pr`, Story 4.4): a `VcsCommandError` reading `base`'s own commit history for the already-landed check is silently swallowed with no finding, degrading `already_landed_keys` to empty rather than distinguishing "read failure" from "nothing landed yet." `merge_pr`'s own `--match-head-commit` guard (this pass's own fix) still protects against an incorrect merge even if this path is taken.
- rejected: none this pass.

## Suggested Review Order

**The safety-critical fixes — start here**

- `_required_check_ack_key` + the scoped acknowledgement gate (fixes the permanent-bypass bug).
  [`land.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py) — search `_required_check_ack_key`

- `ForgePort.merge_pr`'s `expected_head_sha`/`--match-head-commit` (closes the merge TOCTOU).
  [`ports/forge.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/forge.py) — search `merge_pr`
  [`adapters/forge_gh.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py) — search `merge_pr`

**Correctness fixes**

- `_evaluate_required_checks`'s combined-rule label collection, moved earlier in `run_land`'s own sequence.
  [`land.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py) — search `_evaluate_required_checks`

- `reconcile_feed`'s extraction from `run_refresh_feed`.
  [`deploy.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py) — search `def reconcile_feed`

**Tests (peripherals)**

- `tests/unit/test_land.py`'s full I/O matrix, re-entrancy test, and the four new regression tests added by this review pass.
</intent-contract>
