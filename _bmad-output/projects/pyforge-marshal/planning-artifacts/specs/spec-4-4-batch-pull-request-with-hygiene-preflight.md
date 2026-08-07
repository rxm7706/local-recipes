---
title: 'Batch pull request with hygiene preflight'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'b5af6aeb3673e0939303dc3caa97fe40ade214fe'
---

<intent-contract>

## Intent

**Problem:** opening the PR for a landed wave is today a manual `gh pr create` invocation (this whole session's own practice, every PR from #266 onward) with no mechanical check that the wave satisfies this repo's own declared landing rules (Story 4.7's `landing_rules` — the `maintenance` label, the ungated `environment.yaml` sync check) before the PR goes up, and no derivation of title/body from what actually landed.

**Approach:** `marshal deploy batch-pr` is Marshal's first and only outbound-network command (NFR-2). A new `ports/forge.py::ForgePort` (an AD-34 egress port, mirroring Story 3.7's `NotifyPort` exactly — every text field accepts only `Redacted`) is implemented by `adapters/forge_gh.py::GhForge`, a thin wrapper around the `gh` CLI (this repo's own established practice all session — never a raw HTTP/REST client). Hygiene preflight reuses Story 4.7's `core.landing.LandingRule`/`rule_applies` directly: a triggered rule with `required_check` set is a blocking gate (checked against the forge's own check-run status for the wave's head commit); a triggered rule with `label` set is an action, applied to the PR, never blocking.

## Boundaries & Constraints

**Always:**
- **`ports/forge.py::ForgePort`** (new, AD-34 egress port, registered `True` in `core/egress.py::EGRESS_PORTS` alongside `RecordPort`/`NotifyPort`): `find_open_pr(repo: str, head_branch: str) -> PrInfo | None`; `create_pr(repo: str, base: str, head: str, title: Redacted, body: Redacted) -> PrInfo`; `update_pr(repo: str, number: int, title: Redacted, body: Redacted) -> PrInfo`; `add_labels(repo: str, number: int, labels: tuple[str, ...]) -> None`; `check_run_status(repo: str, ref: str, check_name: str) -> str | None` (returns the check's conclusion, e.g. `"success"`/`"failure"`, or `None` if no such check has run). `title`/`body` accept ONLY `Redacted` — no bare `str` anywhere in this Protocol, matching `NotifyPort`'s own established shape and the AD-34 registry-completeness meta-test that already enforces this pattern.
- **`adapters/forge_gh.py::GhForge`** implements `ForgePort` by shelling out to the `gh` CLI (`gh pr view --json ...`, `gh pr create ...`, `gh pr edit ...`, `gh pr edit --add-label ...`, `gh api repos/.../commits/{sha}/check-runs` for check-run status) — this repo's own established practice throughout this entire session, never a raw HTTP client. `gh`'s own auth (`gh auth status`, already a documented precondition elsewhere in this codebase's docs) is assumed configured; a `gh` invocation failure (not authenticated, network error, rate limit) raises a new `ForgeCommandError` (mirrors `VcsCommandError`'s own shape), never silently swallowed.
- **Title/body derivation**: the batch-PR title and body are built from the merged story set (reusing Story 4.1's `merged_story_keys`/durability machinery to identify what's in the wave) and the journal fold's own gate-verdict records for each key (reusing Story 3.2's `core.journal.fold`) — the body lists every story with its gate verdict. All PR text is redacted at the point it's assembled (before it ever reaches `ForgePort`, matching `NotifyPort`'s own "redact at capture" idiom), never passed as a bare string into `create_pr`/`update_pr`.
- **Target base branch is read from policy** (`effective.merge_subject_template`'s own sibling concept — check whether a `landing` base-branch key already exists from Story 4.7, or whether one more STATIC key is needed here; if the latter, add `landing_base_branch: str`, default `"main"`) — never the forge's own "default branch" concept, which for a fork defaults to the UPSTREAM's default, not this repo's own `main` (a real, named risk in this story's own AC: "never opened against an upstream fork's default").
- **Existing-PR detection updates rather than duplicates**: `find_open_pr` is called first; if a PR already exists for this head branch, `update_pr` is called instead of `create_pr` — idempotent, re-entrant (a `batch-pr` re-run after new stories landed on the same wave updates the existing PR's title/body/labels rather than opening a second one).
- **Hygiene preflight, before any PR write**: for every `landing_rules` entry whose `rule_applies(rule, changed_paths)` is `True` (`changed_paths` = the wave's own changed-file set, gathered the same way Story 2.3's `changed_files` already does): if `required_check` is set, query `ForgePort.check_run_status` for that check against the wave's head commit — `"success"` is satisfied, anything else (including `None`, no such check run yet) is UNSATISFIED and BLOCKING (FR-29: "exits non-zero on an unsatisfied blocking rule with a remediation line" — the remediation line names the rule and what would satisfy it, e.g. "regenerate environment.yaml and re-push"). If `label` is set (and the rule fired), it is an ACTION — never blocking — applied via `add_labels` once the PR exists.
- **No AI-attribution or courtesy preamble anywhere Marshal emits text** (FR-35) — the title/body assembly must not add a co-author trailer, a "Generated with" line, or any courtesy preamble; this is default-off, opt-in-only configuration (if this story doesn't need to build the opt-in toggle itself, it must at minimum guarantee the default path emits none — verify no such text appears anywhere in the assembled title/body before this story is done).

**Never:**
- No raw HTTP/REST calls to GitHub — always through the `gh` CLI, matching this repo's own entire session-long practice.
- No PR title/body text ever passed as a bare `str` into `ForgePort` — always through `Redacted`, assembled and redacted before the port boundary.
- No hard-coded hygiene rule anywhere in `cli/deploy.py`/`core/landing.py` — every rule comes from `effective.landing_rules` (FR-29's own text: "not hard-coded into Marshal"). This story adds ZERO new hygiene logic beyond generically evaluating whatever `landing_rules` already declares.
- Do not touch `cli/land.py`/`core/landing.py`'s enforcement wiring beyond what's needed to EVALUATE rules (Story 4.8 is the one that acts on landing as a whole, merges, retires branches, etc.) — this story only opens/updates a PR and reports hygiene status.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No existing PR for this head branch | `find_open_pr` returns `None` | `create_pr` called | No error |
| Existing open PR for this head branch | `find_open_pr` returns a `PrInfo` | `update_pr` called, not a duplicate `create_pr` | No error |
| All triggered hygiene rules satisfied | Every `required_check` rule's check is `"success"` | Preflight reports all-satisfied; PR opened/updated | Exit 0 |
| One triggered `required_check` rule unsatisfied | Check missing or failed | Blocking; exits non-zero with a remediation line naming the rule; no PR write attempted | Registered finding |
| A triggered `label` rule | `rule_applies` true, `label` set | Applied via `add_labels` after the PR exists; never blocks | No error |
| `gh` CLI failure (auth, network, rate limit) | `ForgeCommandError` | Reported plainly, non-zero exit; no partial PR state assumed | Registered finding |
| Empty wave (nothing merged since last batch-pr) | No candidate stories | Clean no-op, `data.opened: false`, `data.updated: false` | No error |
| PR base branch resolution | Fork scenario | Uses policy-declared base, never the forge's own default-branch concept | No error |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/forge.py` — NEW. `ForgePort` Protocol, `PrInfo` frozen dataclass, `ForgeCommandError`.
- `src/pyforge/marshal/adapters/forge_gh.py` — NEW. `GhForge` (`gh` CLI wrapper).
- `src/pyforge/marshal/core/egress.py` — EDIT. Register `ForgePort: True`.
- `src/pyforge/marshal/core/policy.py` — EDIT (only if a new `landing_base_branch` key is genuinely needed — verify against Story 4.7's actual shipped keys first).
- `src/pyforge/marshal/cli/deploy.py` — EDIT. New `batch-pr` action: wave discovery (reuse Story 4.1's durability machinery), hygiene preflight (reuse Story 4.7's `rule_applies`), title/body assembly + redaction, existing-PR detection, create/update, label application.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New codes: unsatisfied blocking hygiene rule, forge command failure.
- `tests/unit/test_forge_gh.py` — NEW. `GhForge` against a fake `gh` subprocess (mirror `test_vcs_git.py`'s real-subprocess-where-safe style, but `gh` calls a live API — use a fake/injected process runner, never a real network call in tests).
- `tests/unit/test_deploy.py` — EDIT. `batch-pr` end-to-end via fake `ForgePort`.

## Tasks & Acceptance

**Execution:**
- [x] `ports/forge.py` — `ForgePort`, `PrInfo`, `ForgeCommandError`.
- [x] `adapters/forge_gh.py` — `GhForge`.
- [x] `core/egress.py` — register `ForgePort`.
- [x] `cli/deploy.py` — `batch-pr` action: wave discovery, hygiene preflight, title/body assembly + redaction, existing-PR detection, labels.
- [x] `core/findings.py` / `core/verdict.py` — register new codes.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log any scope narrowed during implementation.

**Acceptance Criteria:**
*(Story 4.4's ACs from `epics.md`, preserved as the contract of record.)*
- Given a wave of merged stories, when the batch PR is opened, then title and body derive from the merged set and the journal, and the body lists stories with their gate verdicts
- And it targets the configured base branch and is never opened against an upstream fork's default
- And existing-PR detection updates rather than duplicating
- And hygiene preflight reports which project-configured rules apply to the change set and whether each is satisfied, with rules declared in policy, never hard-coded into Marshal (FR-29)
- And an unsatisfied blocking rule exits non-zero with a remediation line
- And no AI-attribution or courtesy preamble appears in any commit, PR body, or comment Marshal emits; attribution is opt-in configuration, default-off (FR-35)
- And PR text routes through the egress serializer and is redacted (AD-34)
- And the forge adapter is the only outbound network path; everything else is local (NFR-2)

## Design Notes

**Why hygiene-rule satisfaction is answered generically via `required_check`'s forge status, never rule-specific logic.** FR-29 requires "rules declared in policy, never hard-coded into Marshal" — if satisfying `environment-yaml-sync` meant Marshal code that specifically diffs `pixi.toml` against `environment.yaml`, every future repo-specific rule would need its own bespoke satisfaction check compiled into Marshal, defeating the whole premise. Routing satisfaction through "is there a green CI check by this declared name" is the one generic mechanism that works for ANY future rule a project declares, without Marshal ever knowing what the check actually verifies.

**Why `gh` CLI, never a raw REST client.** This entire session's own practice (every PR #266 through #276) already goes through `gh pr create`/`gh pr edit`, and this repo's `git config`/auth setup already trusts `gh auth status` — building a second, parallel GitHub-auth path (a REST client with its own token handling) would duplicate a solved problem and widen the credential-handling surface this project has to reason about.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold, especially the AD-34 egress-registry-completeness meta-test recognizing the new `ForgePort`.

**Manual checks (if no CLI):**
- Do NOT run `marshal deploy batch-pr` for real against this repo during implementation — it would open/update a real PR. Verify entirely through the unit-test suite with a fake `ForgePort`, matching this project's own established precedent (Stories 4.1/4.3 both declined to run their own real-network/real-git-write manual checks during implementation for the identical reason).

## Spec Change Log

**1. `ForgePort`'s literal Boundaries wording (`repo: str`, `head_branch: str`, `base: str`, `head: str`, `ref: str`, `check_name: str`) fails the AD-34 egress-registry-completeness meta-test — verified live, not assumed.** `tests/meta/test_ad34_egress_registry_completeness.py`'s guard (2) flags ANY bare-`str`-typed parameter on an egress-classified Protocol method, "regardless of which parameter is semantically 'the payload'" (its own docstring, and `ports/notify.py::NotifyPort.notify_desktop`'s own docstring citing the identical guard as the reason its signature departs from ITS OWN intent-contract's literal `title: str` wording). Running the guard against a first draft of `ForgePort` typed exactly as spec'd confirmed it: 10 violations across `find_open_pr`/`create_pr`/`update_pr`/`add_labels`/`check_run_status`, none of them `title`/`body` (already correctly `Redacted`). None of `repo`/`head_branch`/`base`/`head`/`ref`/`check_name` carries secret or session-derived free text — they are `gh`-CLI routing identifiers Marshal itself constructs — but the guard is intentionally undiscriminating about semantic role, only about type (the same reason `RecordPort`/`NotifyPort` both type their own non-payload identifier as `Path`, never `str`, for their single `path` parameter). Fixed: a new `ForgeRef` frozen dataclass (one `value: str` field, non-empty-validated) wraps every one of the six identifiers; `ForgePort`'s five methods now type them `ForgeRef` instead of `str`. `PrInfo.number` stays a plain `int` (already outside the guard's str-only scope) and `labels: tuple[str, ...]` stays a container (the guard's own stated Bounds: "does NOT recognize a `str` buried inside a container type"). Verified live: `test_guard_does_not_fire_on_the_real_forge_port` (new, mirrors `test_guard_does_not_fire_on_the_real_notify_port`'s own precedent) asserts zero violations against the real, shipped `ForgePort`; `adapters/forge_gh.py::GhForge` unwraps each `ForgeRef.value` exactly once, at the point a `gh` argv is assembled.

**2. `landing_base_branch` needed a new STATIC policy key — Story 4.7 shipped none of its own four that covers "the batch-PR target base branch".** The spec's own Always bullet flagged this as conditional ("check whether a landing base-branch key already exists from Story 4.7 ... if the latter, add `landing_base_branch: str`, default `"main"`") — grepped `core/policy.py`'s `_STATIC_KEYS`/`DEFAULT_POLICY` before adding anything: `landing_rules`/`landing_merge_strategy`/`landing_branch_retirement`/`landing_resync` are the only four, none names a base branch. Added `landing_base_branch` as `core/policy.py`'s 20th key (STATIC, default `"main"`, validated non-empty-`str` via a new `_valid_landing_base_branch`, a deliberate near-duplicate of `_valid_merge_subject_template` rather than a shared alias — the two fields answer unrelated questions and a future branch-name-specific check must not silently apply to the subject template too). Every "19-key"/"9 static fields" reference this ripples through was updated to 20/10: `core/policy.py`'s own module docstring and `EffectivePolicy` (dataclass field, `__post_init__`, `__repr__`, `content_hash`), `schemas/policy.json` (`required`/`properties`), `cli/config.py` (`_FIELD_ORDER`, `_UNSETTABLE_KEYS`, `_PROJECT_POLICY_ONLY_KEYS` — no `--set` surface, `marshal-policy.toml` only, same reason as its 3 landing scalar siblings), and the corresponding meta/unit tests (`test_schema_file_declares_the_twenty_keys`, `test_config_prints_all_twenty_keys`, the three direct `EffectivePolicy(...)` constructions in `tests/unit/test_policy.py`). `cli/deploy.py`'s own `_MERGE_BASE_BRANCH = "main"` module constant (used by the PRE-EXISTING `land-story` action) is left untouched — this story's own Never bullet forbids touching `land-story`'s enforcement wiring beyond what evaluating rules requires, and `land-story` was not in this story's Code Map at all; only the NEW `batch-pr` action reads `effective.landing_base_branch`.

**3. The forge repo slug (`"rxm7706/local-recipes"`) has no policy field — deliberately hardcoded as a module constant, not added as a 21st key.** No Code Map entry, Always bullet, or AC names a repo-slug policy field, and `landing_base_branch` is the ONE new key the spec's own text flags as conditionally needed. Every Marshal station lives inside this one physical repo (confirmed against the team's own reference note: "gh pr create needs --repo rxm7706/local-recipes — this repo is a staged-recipes fork") — a fact about which repo Marshal itself runs inside, not a per-project policy decision the way `landing_base_branch` is. `cli/deploy.py::_FORGE_REPO` names it, with a comment recording the reasoning for a future reader who might otherwise wonder why it isn't policy-governed like everything else `batch-pr` reads.

**4. `_gather_gate_verdicts` reuses Story 4.3's own `land-story` journal shape (`kind: "manual-landing"`, `payload.story_key`/`payload.gate_verdict`) rather than inventing a new journal kind.** The spec's own Always bullet says "the journal fold's own gate-verdict records for each key (reusing Story 3.2's `core.journal.fold`)" without naming which `kind` carries a gate verdict — grepped `core/journal.py`'s own docstring first: every kind it lists as "illustrative" (including a `"gate-verdict"`-shaped one) has "no real writer... yet" anywhere in this codebase. The ONE real, shipped source of a per-story gate verdict in the journal today is `land-story`'s own `_LAND_KIND = "manual-landing"` observation (`cli/deploy.py::_journal_manual_landing`), whose payload already carries both `story_key` and `gate_verdict`. `_gather_gate_verdicts` scans every Tier-3 run directory's `journal.jsonl` (+ any `blobs/*.json` sidecars) via `fold`, collecting that shape — a story landed through the ordinary dev/review flow (never through `land-story`) simply has no entry, and `_batch_pr_body` reports that as `"unknown"`, never fabricated (matches every sibling command's own "reports, never fabricates" posture, e.g. `deploy recover-spec`).

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 5, medium 5, low 1)
- defer: 3
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **P1: a malformed `landing_rules` policy layer silently disabled the entire hygiene preflight.** `core/policy.py::compose` never raises — a malformed `landing_rules` layer degrades to a non-blocking `MRS-POLICY-002` finding and the field falls back to `DEFAULT_POLICY["landing_rules"]` (empty), so a config typo, not a deliberate decision, could bypass the hygiene gate entirely. Fixed: `run_batch_pr` now checks `policy.compose`'s own findings for an ERROR-severity finding naming `'landing_rules'` and HARD REFUSES the whole invocation (new `MRS-DEPLOY-015`) before evaluating hygiene or touching the forge. New test: `test_batch_pr_p1_refuses_on_malformed_landing_rules_policy`.
  - `[high]` `[patch]` **P2: `data["labels_applied"]` claimed success before `add_labels` had actually run.** It was set to the intended labels BEFORE the `forge.add_labels` call, so a raised `ForgeCommandError` still left the report claiming those labels landed. Fixed: `data["labels_applied"]` is now set only after `add_labels` returns successfully; on failure it stays empty. New test: `test_batch_pr_p2_add_labels_failure_does_not_claim_labels_applied`.
  - `[high]` `[patch]` **P3: `GhForge.check_run_status` trusted response order, not recency.** It returned the FIRST check run matching `check_name` by name with no `started_at`/`completed_at` handling — GitHub can report multiple runs under the same name (reruns) with no documented response ordering, so a stale "success" could mask a real, newer "failure". Fixed: every matching run is now sorted by `started_at` (ISO-8601, string-sortable) and the most recent conclusion wins. New tests: `test_check_run_status_prefers_the_most_recent_run_over_response_order`, `test_check_run_status_treats_a_missing_started_at_as_oldest`.
  - `[high]` `[patch]` **P4: the hygiene preflight vetted a pinned SHA, but the PR write targeted the mutable branch ref.** `check_run_status` was queried against `head_sha` (pinned once via `resolve_ref`), but `create_pr`/`update_pr` ran afterward against `head_branch` — a commit landing on the branch in that window would open/update a PR for content the preflight never vetted. Fixed (mirrors Story 4.3's own `land-story` P4 fix): `head_branch`'s tip is re-resolved and reconfirmed against `head_sha` immediately before the PR write; a mismatch refuses with a new finding (`MRS-DEPLOY-016`) rather than proceeding. New test: `test_batch_pr_p4_branch_moved_before_pr_write_refuses`.
  - `[high]` `[patch]` **P5: `changed_files` trusted the local worktree without confirming it matched the pinned head SHA.** `changed_files(git_repo_root, home, base=base)` diffs `home`'s own `HEAD`, with no prior guarantee `home` was checked out at `head_sha` — a stale or detached worktree could silently under-report the real change set, skipping a `required_check` rule that should have fired. Fixed: a new `VcsPort.worktree_head_sha` primitive (`git rev-parse HEAD` in `home`) is checked against `head_sha` before `changed_files` is ever trusted; a mismatch or read failure refuses with a new finding (`MRS-DEPLOY-017`). New tests: `test_batch_pr_p5_stale_worktree_refuses_before_changed_files`, `test_batch_pr_p5_worktree_head_sha_read_failure_refuses`, plus real-git coverage in `test_vcs_git.py`.
  - `[medium]` `[patch]` **P6: `_gather_gate_verdicts` caught only `TypeError` around `fold`, narrower than its own "one bad run directory never aborts the gather" docstring promise.** Broadened to `(TypeError, ValueError, KeyError, OSError)`, matching the same per-item degradation tier this codebase already uses for filesystem/directory reads elsewhere. New test: `test_gather_gate_verdicts_p6_skips_a_run_dir_whose_fold_raises_non_typeerror`.
  - `[medium]` `[patch]` **P7: `_gather_gate_verdicts` ordered run directories lexicographically, not chronologically.** `sorted(path for path in runs_dir.iterdir() ...)` breaks for names like `run-10` sorting before `run-2`, and combined with "last write wins", could report a stale gate verdict for a story actually re-landed more recently under a lexicographically-earlier directory name. Fixed: a new `_run_dir_sort_key` sorts by directory `mtime` instead. New test: `test_gather_gate_verdicts_p7_orders_by_mtime_not_directory_name`.
  - `[medium]` `[patch]` **P8: `find_open_pr`'s result was never checked against the policy-declared base branch before `update_pr`.** An open PR for this head branch targeting a DIFFERENT base than `landing_base_branch` would have been silently updated as if it were this command's own batch PR. Fixed: `PrInfo` gained a `base` field (parsed from `gh`'s own `baseRefName`), and `run_batch_pr` refuses with a new finding (`MRS-DEPLOY-018`) when `existing.base != base`. New test: `test_batch_pr_p8_existing_pr_with_a_different_base_refuses`.
  - `[medium]` `[patch]` **P9: a rule's label fired inconsistently depending on HOW its `required_check` failed.** A raised `ForgeCommandError` skipped the label (an early `continue`), but a normally-resolved non-success conclusion still fired it — the same underlying condition ("this rule's gate did not pass") handled two different ways. Fixed: `_evaluate_hygiene` now fires a rule's label only when its own `required_check` (if any) is satisfied, treating a raised check and a resolved-failure check identically. New tests: `test_evaluate_hygiene_p9_label_does_not_fire_when_check_raises`, `test_evaluate_hygiene_p9_label_does_not_fire_when_check_resolves_failure`, `test_evaluate_hygiene_p9_label_still_fires_when_check_succeeds`.
  - `[medium]` `[patch]` **P10: `existing is None` conflated "never opened" with "already merged and closed".** Re-running `batch-pr` on an already-fully-landed wave could open a spurious duplicate PR for content already merged. Fixed: reuses Story 4.1's own `merged_story_keys` durability machinery, read against `base` itself — if every wave story key is already reachable from `base`'s own history, the run short-circuits to a clean no-op (`data.already_landed: true`) before touching the forge at all. New test: `test_batch_pr_p10_already_landed_wave_is_a_noop`.
  - `[low]` `[patch]` **P11: `_batch_pr_redact`'s exception net was a hardcoded allowlist (`ValueError`/`LookupError`/`TypeError`) that could miss an exception type `to_redacted`/its callees raise, letting it propagate instead of degrading to "redaction failed, refuse to write".** Fixed: broadened to a deliberate, narrow `except Exception` (`# noqa: BLE001`) at this one call site, justified in a comment as the one place "fail closed on literally anything" IS the contract — `to_redacted`'s own stated purpose is "never let unredacted text through, no matter what goes wrong". New test: `test_batch_pr_redact_p11_returns_none_on_any_redaction_failure`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[low]` **D1:** `cli/deploy.py::_FORGE_REPO` is a hardcoded module constant with no runtime verification against the actual git remote of the working repo — low practical risk today (this repo's own remote genuinely is that value), but a portability gap if this package is ever used against a differently-configured checkout.
  - `[low]` **D2:** Only a local branch-existence check (`vcs.branch_exists`) gates entry into the hygiene+PR-write path — nothing confirms `loop/{slug}` has actually been pushed to the forge repo before hygiene evaluation begins. `gh pr create --head <branch>` already fails cleanly and loudly if unpushed, so the natural failure path is reasonably safe; an earlier check would only fail faster with a better message.
  - `[low]` **D3:** `GhForge.add_labels`'s multi-label `gh pr edit --add-label X --add-label Y` call reports all-or-nothing failure — if GitHub partially applies labels before rejecting one, the caller cannot tell which of the intended labels actually landed. Low practical impact (labels are rarely rejected once the rule's own name is a valid, pre-existing label); a real observability gap.

</intent-contract>

## Suggested Review Order

**Safety-critical fixes — start here**

- `run_batch_pr`: the P1 hard-refuse on malformed `landing_rules`, P4 branch-tip re-verification before the PR write, P5 worktree-matches-head-SHA check, P10 already-landed-wave short-circuit.
  [`deploy.py:1800`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1800)

- `_evaluate_hygiene`: the P2 `labels_applied` truthfulness fix, P9 uniform label-firing on check-failed vs. check-undetermined.
  [`deploy.py:1704`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1704)

- `GhForge.check_run_status`: the P3 most-recent-run selection (was first-match).
  [`forge_gh.py:251`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py#L251)

- `VcsPort.worktree_head_sha`, the new primitive P5 depends on.
  [`vcs_git.py:950`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py#L950)

**Supporting fixes**

- `_gather_gate_verdicts`: the P6 broadened exception net, P7 mtime-based (not lexicographic) run-dir ordering.
  [`deploy.py:1637`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1637)

**Tests (peripherals)**

- `batch-pr` end-to-end, full I/O matrix plus every P1-P11 regression.
  [`test_deploy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py#L1)

- `GhForge` against a fake subprocess runner, including the P3 recency-selection tests.
  [`test_forge_gh.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py#L1)

- `worktree_head_sha` against real temp git repos.
  [`test_vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py#L1)
