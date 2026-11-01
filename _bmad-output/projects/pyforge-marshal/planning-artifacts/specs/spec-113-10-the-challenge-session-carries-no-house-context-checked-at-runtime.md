---
title: "113.10: the challenge session carries no house context, checked at runtime"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
---

<intent-contract>

## Intent

**Problem:** reviewer isolation rests on the plugin adapters' frontmatter alone. Line numbers are at `03a7aff5d9`.

- `widen_settings` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py:50-67`)
  starts from `claude.toml`'s settings, so the challenge session loads user-scope hooks (a `SubagentStart` hook's
  payload and `gitStatus` reached an `omitClaudeMd` reviewer during the audit), the `claude-md-and-agents-md`
  `instructionFiles` plugin config, `CLAUDE.md` and `AGENTS.md` (EGM audit MAR-M-D2, MAR-E3).
- The session's `--settings` denies `Bash`, `Edit` and `Write` (except one run-folder `Write` rule) but carries no `Read`
  deny for `AGENTS.md`, `CLAUDE.md`, a memlog or `.claude/memory/`, so the goldfish rule holds only as a prompt
  instruction. `SPEC.md:1204` already settles that context isolation is not filesystem isolation; this story closes the
  context half at runtime.
- The orchestrator session that writes `report.json` loads `CLAUDE.md` (memlog, 2026-11-01), and CAP-299's "receives
  exactly" overstates what a reviewer gets. The synthesizer half of MAR-M-D2 is Story 113.12's.

**Approach:**
- **Hooks off.** `widen_settings` sets `disableAllHooks: true` in the challenge `--settings` (or the argv limits
  `--setting-sources` so user-scope hooks never load). `Bash`, `Edit` and `Write` stay denied except the run-folder
  `Write` rule, so turning hooks off removes no guard; a test pins the deny list.
- **No instruction files.** The challenge settings strip the `instructionFiles` (`claude-md-and-agents-md`) plugin
  config and add `Read` deny rules for `AGENTS.md`, `CLAUDE.md`, `**/.memlog.md` and `.claude/memory/**`, with the
  target excepted (a rules-stage target may be `AGENTS.md`).
- **Outside the repo.** The session launches from a cwd outside the repo (the run folder under Tier 3, or a temp dir),
  and the challenge `--settings` carries `enabledPlugins` `{"egm@egm": true}` so the plugin is enabled there;
  `plugin_refusal` (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:172`) checks the same
  scope the session uses.
- **The contract follows the code.** The memlog events for MAR-M-D2 and MAR-E3 are already on `spec-pyforge-marshal`
  (commit `7dde4a0202`). Re-derive CAP-299 with `bmad-spec`: "receives exactly" means the adapter frontmatter plus the
  session's own settings; name what still reaches a reviewer (managed policies) and whether the orchestrator loads
  `CLAUDE.md` after this story. Then the cascade re-stamp and the scoped stamp.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the session launches only while
  `pyforge.marshal.egm_challenge` is on.

Ledger key: `113-10-the-challenge-session-carries-no-house-context-checked-at-runtime`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-299** (FR-241): the goldfish context rule; a reviewer never receives `AGENTS.md`,
  `CLAUDE.md`, a memlog, a URL or session text.
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL7; findings MAR-M-D2, MAR-E3).

## Acceptance Criteria

- **AC1 — Hooks off.** The rendered challenge `--settings` sets `disableAllHooks: true` (or the argv limits
  `--setting-sources` to exclude user scope); a test in
  `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py` pins it.
- **AC2 — The Read denies.** The settings deny `Read` on `AGENTS.md`, `CLAUDE.md`, `**/.memlog.md` and
  `.claude/memory/**`, carry no `instructionFiles` plugin config, and except the target when the target is one of those
  paths; tests pin the list and the exception.
- **AC3 — The guards stay.** `Bash`, `Edit` and `Write` are denied except the run-folder `Write` rule, with hooks off.
- **AC4 — The plugin scope.** The session's cwd is outside the repo, its `--settings` carries `enabledPlugins`
  `{"egm@egm": true}`, and `plugin_refusal` refuses when that scope does not enable the plugin.
- **AC5 — The contract.** CAP-299 is re-derived by `bmad-spec` (both self-validate passes logged);
  `spec-surface-check`, `chain-currency-sweep-check` and `chain-completeness-check` exit 0.
- **AC6 — Mutation.** Removing `disableAllHooks` (or the setting-sources limit) fails AC1's test; removing the
  `AGENTS.md` deny fails AC2's. Restore each.
- **AC7 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Change only the challenge session's own settings and cwd; never `claude.toml`'s shared dispatch argv.

**Ask first:**
- If `disableAllHooks` would also disable a managed-policy hook the operator relies on, which form (hooks off or
  setting-sources) to use.

**Never:**
- Never widen a reviewer's tools beyond `Read`, `Grep` and `Glob`; never hand-edit `SPEC.md`.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

**Residual risk:**
- Managed (enterprise) policy settings still load; the re-derived CAP-299 names them as what still reaches a reviewer.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL7).
- Epic: Epic 113.
- Ledger key: `113-10-the-challenge-session-carries-no-house-context-checked-at-runtime`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py` and the re-derived `SPEC.md`; within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Auto Run Result

Status: in-review

Summary: the challenge session now carries no house context at runtime. Its `--settings` turn every hook off, drop the
`instructionFiles` plugin config, deny `Read` on the repo's instruction files, memlogs and team memory (the target
excepted), and enable `egm@egm` in that same scope. The session launches from a fresh temp dir outside the repo.
`claude.toml`'s shared dispatch argv is unchanged.

What changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py`:
  - `widen_settings` sets `disableAllHooks: true` (AC1). It drops every `pluginConfigs` entry that carries an
    `instructionFiles` option, sets `enabledPlugins["egm@egm"] = true`, and appends the new `deny_rules` after
    `DENIED_TOOLS` (AC2, AC4).
  - New `FORBIDDEN_READ_GLOBS` (`AGENTS.md`, `*/**/AGENTS.md`, `CLAUDE.md`, `*/**/CLAUDE.md`, `**/.memlog.md`,
    `.claude/memory/**`) and `forbidden_read_rules(root, target)`. These render `Read(//<root>/<glob>)` deny rules and
    leave out the glob the target matches. `*/**/` means one directory deep or more, so a rules-stage review of the
    root `AGENTS.md` can read it while nested `AGENTS.md` files stay denied (AC2).
  - `render_argv` takes `deny_rules`. When a profile carries no `--settings`, it prepends the widened settings, so the
    session never launches without its guards.
  - New `session_settings(plugins_root)`.
  - `ClaudeChallengeRunner.run(prompt, model, root, target, log_path)`:
    - runs the session from a `tempfile.TemporaryDirectory(prefix="marshal-egm-")`, so no `CLAUDE.md`, `AGENTS.md`
      or git status is discovered;
    - refuses with `ChallengeHarnessError` when `TMPDIR` puts that temp dir inside `root`;
    - drops `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` from the env, because the operator's user settings list
      the repo's parent dir in `additionalDirectories` (AC4).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`:
  - The `ChallengeRunner` protocol takes `root` and `target`. It no longer takes `cwd`, so `root` is never the
    session's cwd.
  - `run_one` passes the context target.
  - `plugin_refusal(plugins, version, personas)` checks that `egm@egm` is enabled in the session's own `--settings`
    (`session_settings`), the scope the session uses from outside the repo. It no longer checks the tracked
    `.claude/settings.json`. `SETTINGS_RELPATH` is removed, and both call sites follow (AC4).
- Tests:
  - `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py` pins:
    - hooks off (AC1);
    - the exact Read-deny list, its rendered rules, the target exception (root `AGENTS.md`, root `CLAUDE.md`, nested
      `AGENTS.md`, a non-forbidden target, a target outside the repo) and the glob semantics (AC2);
    - the deny list and the single run-folder `Write` rule with hooks off (AC3);
    - `enabledPlugins` in the session scope, `plugin_refusal` refusing when that scope does not enable the plugin, the
      cwd outside the repo and the in-repo-`TMPDIR` refusal (AC4);
    - `run_one` handing the runner `root` and `target`.
  - `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`: the `FakeRunner.run` signature follows
    the protocol. One line changed.
- Memlog (`spec-pyforge-marshal/.memlog.md`): one surface-reconcile event naming the four paths, and one CAP-299
  behaviour event for the re-derive.

Commands and exit codes, all from the worktree root:
- `pixi run --frozen -e pyforge-marshal python -m pytest .../tests/unit/test_challenge_harness.py .../tests/unit/test_factory_challenge.py`
  exited 0 (84 passed; `test_challenge_core.py` also ran green alongside these, 135 passed).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exited 0: 13644 passed and 15 skipped, then 34 passed and
  4 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exited 0. It reported "no packages touched"
  because the change is not committed yet. Its report gives `adapters/challenge_harness.py` 98.1% and
  `cli/challenge.py` 84.7%, both above the 80% floor.
- `ruff check` and `ruff format --check` on the four files (`.pixi/envs/pyforge-marshal/bin/ruff`) exited 0.
- `mypy -p pyforge.marshal`, run from the package with the guild env and its cache dir, exited 0 (217 files).
- `pixi run --frozen -e pyforge-guild lint-types` exited 1. The only finding is in pyforge-doctor's ruff leg: an
  import-order error in another station's in-flight file, which this story may not edit. The pyforge-marshal ruff leg
  is ok, and `lint_types.py ruff-format` exited 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` exited 0.
- `chain-completeness-check` exited 0.
- `chain-currency-sweep-check` exited 1: staleness checkpoints fail on 8 stations after this session's audit memlog
  appends. The cascade re-stamp belongs to the session's re-derive phase.
- AC6 mutation, each restored byte-identical (`cmp`):
  - removing `disableAllHooks` fails `test_the_session_runs_with_every_hook_off` (exit 1);
  - removing the root `"AGENTS.md"` glob fails `test_the_session_denies_reading_the_house_context` (exit 1).

Open for the session owner:
- AC5: the `bmad-spec` re-derive of CAP-299 (two self-validate passes), then the cascade re-stamp and the scoped stamp.
  The behaviour event on the memlog states the new "receives exactly" text.
- The Ask-first boundary did not fire. No managed settings exist on this host (`/etc/claude-code` is absent), and a
  non-managed `disableAllHooks` does not disable managed-policy hooks. Managed settings and their hooks remain the
  residual that reaches a reviewer.
- Not verified against a live `claude` session, which would cost a real provider round-trip. The flags were read from
  `claude --help` (2.1.314). `disableAllHooks`, `enabledPlugins` and the `Read(//abs)` deny form come from Claude
  Code's settings, and `egm@egm` is installed at user scope (`installed_plugins.json`), so enabling it from flag
  settings in a non-repo cwd resolves.

### Fix round 1 — 2026-11-01

Status: blocked. AC5 is closed except for the `SPEC.md` render. Earlier this session the auto-mode classifier
refused the same render route for Story 113.8's fix (`[Auto-Mode Bypass]`). This round did not retry it: the route
needs the operator's go-ahead. No code changed in this round.

- **AC5, the re-derive (`bmad-spec`, headless).**
  - The memlog decision is on `spec-pyforge-marshal/.memlog.md`: `(decision) Re-derive 2026-11-01 (marshal Story
    113.10; EGM audit MAR-M-D2, MAR-E3)`. It re-derives CAP-299 success from the Story 113.10 behaviour event.
    "Receives exactly" now covers the session as well as the paths: the adapter's frontmatter and the challenge
    session's own `--settings`, checked at runtime.
  - It names what still reaches a reviewer: managed (policy) settings and their hooks, and user-scope settings, which
    a flag scope cannot unset (the review's non-blocking note).
  - For coherence, the Constraint *Context isolation is not filesystem isolation* now reads that a reviewer can read
    any accessible file the session's `Read` denies leave open.
  - The anchor-asserting render script is
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/render_113_10.py`.
    It takes the `SPEC.md` path as its argument, and `--dry-run` checks without writing.
  - The script changes 4 lines: the frontmatter `updated:` note (5), the CAP-299 provenance (1125), the CAP-299
    success (1127) and the Constraint (1204). It asserts every needle once, undo-to-original byte for byte, an
    unchanged CAP definition count (303) and an unchanged line count (1388).
  - It does not overlap `render_113_8.py`, but it must run **after** that script: it prefixes the `updated:` note that
    `render_113_8.py` anchors on.
  - Dry runs on scratch copies of the live `SPEC.md` exit 0 both alone and after `render_113_8.py`. Run before
    `render_113_8.py`, the 113.8 script exits 1 on its frontmatter needle, as expected. The live `SPEC.md` is
    untouched.
  - **Not done:** writing `SPEC.md` and logging the two self-validate passes.
- **AC5, the cascade.**
  - PRD: the FR-241 body follows the re-derive, § 49 is added, and the `updated:` note is prefixed. No FR is added or
    renumbered, and no arrow moves.
  - Spine: § *Currency reconciliation — 2026-11-01 (Story 113.10)*, with readings on AD-1/AD-3 and AD-19, and the
    `updated:` note prefixed. No AD is added, amended or removed.
  - The PRD and the spine are not on marshal's spec surface (`spec-surface-check` 0), so no surface-reconcile event
    is needed.
- Commands, exit codes read from `$?`:
  - The two story test files: 0 (105 passed).
  - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: 0 (13666 passed, 15 skipped; 34 passed, 4 skipped).
  - `pyforge-marshal-coverage-gate`: 0. It judged no module, because the change is uncommitted.
  - `lint-types`: 1. Its only non-ok leg is pyforge-doctor's ruff import order, another station's file.
    pyforge-marshal is ok.
  - `spec-surface-check`: 0. Its one warning is steward's `spec-pyforge-unifying-strategy`.
  - `chain-completeness-check`: 0.
  - `fr-without-cap-check`: 0.
  - `chain_currency_sweep_check.py --project pyforge-marshal`: 0 (marshal current). The repo-wide
    `chain-currency-sweep-check` exits 1 on the seven other stations, which are other agents' work.
- **To unblock (session owner, under the operator-approved render route):**
  1. Run `render_113_8.py`, then `render_113_10.py`, on
     `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md`. If Stories 113.11
     to 113.13 bring their own render scripts that touch CAP-299's success line, merge them by hand. This script's
     needle is the span from ` as absolute paths — never` through `tools: [Read, Grep, Glob]`;`.
  2. Append the pass 1 (coherence) and pass 2 (preservation) `--type event` lines for the Story 113.10 re-derive.
  3. `git add`, then run the scoped stamp `--spec pyforge-marshal/spec-pyforge-marshal`.
  4. Return this story to `in-review`.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL7: MAR-M-D2, MAR-E3; the
  contested MAR-M-D2 settled in the cluster) at the operator's ruling of 2026-11-01 (implement in the Story 113.7
  landing PR). `type: fix`, no flag, no CAP.

## Review Triage Log

- 2026-11-01 — reviewer: independent session. I did not write this code. I judged `git diff HEAD` of the story's
  files against this spec, not against the Auto Run Result. **Verdict: fail**; status is back to `in-progress`.
  - Read:
    - `adapters/challenge_harness.py`: `widen_settings`, `forbidden_read_rules`, `render_argv`'s fallback
      `--settings`, `session_settings`, and `ClaudeChallengeRunner.run`.
    - `cli/challenge.py`: the `ChallengeRunner` protocol, `run_one` handing over `root` and `target`, and
      `plugin_refusal` reading the session's own settings.
    - The tests, and the packaged `claude.toml`, which is unchanged (the Always boundary holds).
    - Callers: `ChallengeRunner` has the one real implementer, and `plugin_refusal` has two call sites, both updated.
  - AC1 holds. `disableAllHooks: true` is forced even over an incoming `false`; `test_the_session_runs_with_every_hook_off`.
  - AC2 holds.
    - Six `Read(//<root>/…)` deny rules cover root and nested `AGENTS.md` and `CLAUDE.md`, `**/.memlog.md` and
      `.claude/memory/**`.
    - No `pluginConfigs` entry with `instructionFiles` survives; only that entry is dropped.
    - The target exception and the glob semantics are pinned (`full_match`).
  - AC3 holds. The deny list starts with the six tools, the only path-scoped `Write` allow is the run folder, and
    `--permission-mode` is `default`.
  - AC4 holds.
    - The cwd is a `marshal-egm-*` temp dir outside the repo, removed afterwards.
    - A `TMPDIR` inside the repo is refused before any launch.
    - `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is dropped from the env.
    - `enabledPlugins` is `{"egm@egm": true}` in the session settings, and `plugin_refusal` refuses when that scope
      does not enable the plugin (the seam is stubbed).
  - AC6 holds, re-observed:
    - Dropping `disableAllHooks`: exit 1; `test_the_session_runs_with_every_hook_off`,
      `test_the_guards_stay_with_hooks_off` and `test_a_profile_without_settings_still_gets_the_guards` failed.
    - Dropping the root `AGENTS.md` glob: exit 1; `test_the_session_denies_reading_the_house_context` and the
      `AGENTS.md-True` glob case failed.
  - AC7 holds. The suite is green (see the shared evidence).
  - Shared evidence (one run covers all five Epic 113 fix stories; every verdict read from `$?`):
    `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (13666 passed, 15 skipped; 34 passed,
    4 skipped). The challenge, harness, status, watch and dispatch unit files exit 0 (730 passed). ruff check and
    ruff format --check over the 14 changed marshal files (package config, package cwd) exit 0 and 0.
    `lint_types.py ruff-format` exit 0 and `lint_types.py mypy` exit 0, with marshal ok in both. `lint-types` exit 1;
    its only finding is pyforge-doctor's `tests/unit/test_sources_pages_liveness.py` import order, which is another
    station's in-flight file. `pyforge-marshal-coverage-gate` exit 0 but judged nothing, because the change is
    uncommitted. `coverage_gates_ci.py --paths-file` over the 8 touched marshal `src` modules (`--suites unit`) exit 0,
    with every module at or above 80%. `spec-surface-check` 0, `chain-completeness-check` 0, `deferred-work-check` 0,
    `dream-chain-check` 0, `dreams-hygiene-check` 0, `fr-without-cap-check` 0. `chain-currency-sweep-check` exit 1:
    a staleness checkpoint fails on all eight stations, marshal included. `spec-pyforge-marshal/SPEC.md` and the
    marshal PRD have no diff against HEAD. The memlog's newest self-validate entries are the 2026-11-01 amendment's
    pass 1 and pass 2, which predate these stories' events.
  - Mutations ran on a scratch copy of the package `src`, placed first on `PYTHONPATH`. The import path was
    confirmed and the unmutated scratch baseline exits 0 (157 passed). Each mutant was restored from the live file,
    and the live tree was never touched.
  - A guard plugin on `PosixProcess.run` covered the whole unit and meta suite: no challenge test reached a real
    `claude --version`. The only hits were the pre-existing `test_harness_bmadloop_probe.py` cases, which stub
    `subprocess.run`.
  - Failures:
    1. AC5 is not met. CAP-299 is not re-derived: `SPEC.md` has no diff, no self-validate pass is logged for this
       story, and `chain-currency-sweep-check` exits 1. The behaviour event the re-derive reads is on the memlog. No
       code change is needed. A re-derive with both passes logged, then marshal's cascade re-stamp, closes it; return
       the story to `in-review` after that.
  - Not blocking, for the CAP-299 re-derive's "what still reaches a reviewer":
    - The operator's user `~/.claude/settings.json` still sets `pluginConfigs."agents-md@builtin".instructionFiles =
      claude-md-and-agents-md` and `enabledPlugins` (`caveman@caveman` among them). Removing the key from the flag
      settings cannot unset a user-scope value, so the effective guards are the temp-dir cwd and the Read denies, not
      the stripped key. The re-derive should name user-scope settings beside managed policy.
    - A nested `AGENTS.md` target leaves out the whole `*/**/AGENTS.md` rule, so every nested `AGENTS.md` becomes
      readable in that run. This is still narrower than the spec's single `AGENTS.md` rule.
    - The `plugin_refusal` enablement check cannot fire at runtime while `widen_settings` always enables `egm@egm`.
      It is a regression guard only.
    - The temp-dir launch, `enabledPlugins` from flag settings and the `Read(//abs)` rules are not verified against a
      live `claude` session; the implementer disclosed this.

- 2026-11-01 — reviewer: independent session, second review. I did not write this work. I judged the committed code
  (`origin/main..HEAD`) and the rendered `SPEC.md` against this spec, not against the Auto Run Result or the fix
  rounds. **Verdict: pass**; status set to `done`.
  - AC1 holds. `widen_settings` forces `disableAllHooks: true`, and `test_the_session_runs_with_every_hook_off`
    passes.
  - AC2 holds. `FORBIDDEN_READ_GLOBS` and `forbidden_read_rules` deny `Read` on root and nested `AGENTS.md` and
    `CLAUDE.md`, `**/.memlog.md` and `.claude/memory/**`, with the glob the target matches left out. No
    `pluginConfigs` entry with `instructionFiles` survives.
  - AC3 holds. `DENIED_TOOLS` leads the deny list. The only path-scoped `Write` allow is the run folder, under
    `--permission-mode default`. `test_the_guards_stay_with_hooks_off` passes.
  - AC4 holds:
    - The session runs from a `marshal-egm-*` temp dir outside the repo, and an in-repo `TMPDIR` is refused.
    - `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` is dropped from the env.
    - `enabledPlugins["egm@egm"]` is set in the session's own settings.
    - `plugin_refusal` reads `session_settings` (`test_plugin_refusal_checks_the_session_settings_scope`).
    - `claude.toml` has no diff against `origin/main`, so the Always boundary holds.
  - AC5 holds (this review's re-check of the first review's failure):
    - CAP-299 success now says that, beyond its paths, a reviewer's context is exactly the EGM adapter's frontmatter
      and the challenge session's own `--settings`, checked at runtime.
    - It names each runtime guard: the temp dir outside the repo (refused when `TMPDIR` puts it inside),
      `disableAllHooks`, no `instructionFiles` plugin config, the dropped env variable, `egm@egm` enabled in the scope
      the plugin refusal checks, the `Bash`/`Edit`/`Write` guard with the run-folder `Write` rule, and the `Read`
      denies with the target excepted.
    - It says that neither the orchestrator session nor a reviewer loads `CLAUDE.md`, `AGENTS.md` or the git status.
    - It names what still reaches a reviewer: managed (policy) settings and their hooks, and user-scope settings.
    - The Constraint *Context isolation is not filesystem isolation* follows the `Read` denies.
    - This matches `widen_settings`, `forbidden_read_rules`, `render_argv`, `ClaudeChallengeRunner.run` and
      `plugin_refusal`.
    - The memlog carries the Story 113.10 behaviour event and its `(decision) Re-derive 2026-11-01 (marshal Story
      113.10 ...)`, which adds the first review's user-scope note. CAP-299's definition line names Story 113.10.
      The self-validate pair is logged.
  - AC6 holds, re-observed:
    - `disableAllHooks` dropped: exit 1; `test_the_session_runs_with_every_hook_off` and
      `test_the_guards_stay_with_hooks_off` failed.
    - The root `AGENTS.md` glob dropped: exit 1; `test_the_session_denies_reading_the_house_context` and the
      `AGENTS.md-True` glob case failed.
  - AC7 holds. The suite exits 0.
  - Not blocking, for the next CAP-299 re-derive:
    - "Neither ... loads `CLAUDE.md`" holds for the repo's files. A user-scope `~/.claude/CLAUDE.md` (none on this
      host) would still load into the orchestrator session, which has no `omitClaudeMd`. Name it beside user-scope
      settings.
    - `Write` is guarded by the allow list and the default permission mode, not by a `Write` entry in
      `DENIED_TOOLS`. That is accurate in effect.
  - Shared evidence (one run covers Stories 113.8-113.13 on committed `HEAD` f742908321; every verdict read from `$?`,
    from the worktree root):
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exit 0 (13667 passed, 15 skipped; 34 passed,
      4 skipped).
    - `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exit 0. The change is committed now, so the
      gate judged `origin/main..HEAD`: "coverage gate OK for pyforge-marshal unit: 8 module(s) ≥ 80%".
    - `chain-completeness-check` 0, `spec-surface-check` 0 (its only warnings are steward's
      `spec-pyforge-unifying-strategy`), `fr-without-cap-check` 0, `deferred-work-check` 0, `dream-chain-check` 0,
      `dreams-hygiene-check` 0, `scripts/chain_currency_sweep_check.py --project pyforge-marshal` 0 (marshal
      `current`).
    - `ad-citation-check` exit 1, on one NEW cap-citation issue outside these six stories:
      `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/.memlog.md:586` (added in
      f742908321 by herald's glossary decision) cites bare `CAP-299`. Qualify it as `spec-pyforge-marshal:CAP-299`
      before the landing PR is pushed. No marshal file is named.
    - The contract, `spec-pyforge-marshal/SPEC.md` (the working tree equals `HEAD`):
      - 303 CAP definitions at `origin/main` and at `HEAD`, with an identical id-and-title list; 1388 lines in both.
        No CAP id changed.
      - The intent and success lines of CAP-298..CAP-303 equal the memlog's six `(capability) ... (amended
        2026-11-01 ...)` entries byte for byte.
      - Each story's `(decision) Re-derive 2026-11-01 (marshal Story 113.n ...)` entry and behaviour event are on the
        memlog. Each changed definition line's provenance names the story.
      - One self-validate pair is logged after the final render: `Self-validate pass 1 (coherence) 2026-11-01, EGM
        audit re-derive` and `Self-validate pass 2 (preservation)`. Pass 1 judges all six CAPs, the four EGM
        Constraints and the EGM Assumption. Pass 2 names the Story 113.8, 113.10, 113.11, 113.12 and 113.13
        re-derives as kept verbatim, and the Story 113.9 findings as landed. The per-story pass texts drafted in the
        fix rounds were not appended separately; this one pair stands for them.
      - The 22 tests the CAP success lines name each exist exactly once in pyforge-marshal's `tests/unit`.
    - Mutations ran on a scratch copy of the package `src`, placed first on `PYTHONPATH`; the import path was
      confirmed. The unmutated scratch baseline (`test_challenge_core.py`, `test_factory_challenge.py`,
      `test_challenge_harness.py`) exits 0 (158 passed). Each mutant was restored, and `git status` shows the live
      package untouched.
