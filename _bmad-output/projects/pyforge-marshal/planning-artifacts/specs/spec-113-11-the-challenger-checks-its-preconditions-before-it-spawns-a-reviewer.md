---
title: "113.11: the challenger checks its preconditions before it spawns a reviewer"
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
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
---

<intent-contract>

## Intent

**Problem:** the challenger's preconditions sit in memlog deviations, not in the Spec, and one of them is checked
nowhere. Line numbers are at `03a7aff5d9`.

- Memlog deviations (1)-(5) of 2026-11-01 record the mechanism as built: the `[challenge].plugin_version` pin (default
  `0.1.0`, checked against `~/.claude/plugins/installed_plugins.json` and the cache `plugin.json`), one synchronous claude
  session from the packaged profile that orchestrates the Agent-tool spawns (reviewers on `model: inherit` under its
  `--model`, its own `--settings` Read rules on the plugin cache), the switch matrix, and plugin-absent dispatch. CAP-298
  still cites a `.claude/settings.json` pin, and the `core/challenge.py` module docstring (`:4-5`) repeats it (EGM audit
  MAR-M-Z6, MAR-M-D3, MAR-M-C3, MAR-D-C4).
- `omitClaudeMd` needs Claude Code 2.1.271 or later; nothing states or checks that floor (MAR-M-Z6).
- How the six `egm_*` switches, `[challenge].enabled` and `stages` combine is in code only; `resolve` also needs
  `egm_challenge`, which CAP-303 does not say (MAR-M-C4).
- No test composes a `[challenge]` block at the repo-default layer (MAR-D-R6).
- The Assumption at `SPEC.md:1294` claims the Agent tool's `model` override applies to plugin agents (the code passes
  `--model` instead) and a steward refresh verb re-verifies the pin (a deferred steward Kinship, memlog decision).
- CAP-302's success line and FR-244 (`prds/prd-pyforge-marshal-2026-07-25/prd.md:3597`) name
  `.claude/skills/pyforge-<station>/SKILL.md`, a path SKF never writes; the code reads
  `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md` first (`station_skill_path`,
  `cli/challenge.py:234-243`) (cluster MAR-CL10: MAR-E1, MAR-D-C1).
- The Dream lists story specs in the audit at `docs/dreams/pyforge-marshal.md:13740` and leaves them out at `:13799`;
  the operator ruled on 2026-11-01 that `--audit` leaves story specs to the readiness stage.

**Approach:**
- **The floor, checked.** `plugin_refusal`
  (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py:172`) runs `claude --version` through the
  existing seam and refuses a version below 2.1.271, or one it cannot read, with the usage code before any spawn,
  journaled like the other refusals.
- **The stale docstring.** The `core/challenge.py` module docstring names `[challenge].plugin_version`.
- **The repo-default layer.** A test in `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`
  composes `policy.compose(repo_defaults={"challenge": BLOCK})` and asserts `REPO_DEFAULTS` provenance without reading
  a file (a live-tree read would need `_bmad-output/policy-defaults.toml` in the station-tests trigger map; 113.2 AC7).
- **The contract follows the code.** The memlog events for every finding above are already on `spec-pyforge-marshal`
  (commit `7dde4a0202`), with the operator's decisions. Re-derive with `bmad-spec`:
  - CAP-298: the pin is `[challenge].plugin_version`; the mechanism is one synchronous claude session from the packaged
    profile that orchestrates the Agent-tool spawns, reviewers inherit its `--model` through `model: inherit`, and its
    own `--settings` carries the plugin-cache Read rules; Claude Code >= 2.1.271 is refused below.
  - CAP-299: `plugin_version` joins the block's key list; the switch matrix (ad hoc: `egm_challenge`,
    `egm_policy_block` and an enabled block; drift adds `egm_retro_drift`; audit adds `egm_audit`; resolve:
    `egm_challenge` and `egm_resolve_bridge`; readiness: `egm_challenge`, `egm_dispatch_readiness`, `egm_policy_block`,
    an enabled block and `readiness` in `stages`; `stages` gates only the dispatch hook).
  - CAP-300: a plugin absent or refused lets dispatch proceed with an `MRS-DISP-067` WARN (113.3 AC4, AC6).
  - CAP-302: `--audit` leaves story specs to the readiness stage, and a rules target is
    `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md` (SKF-compiled from `skill-brief.yaml`, never
    hand-edited; `station_skill_path`'s flat fallback stays as tolerance). FR-244's text in the PRD is fixed in the
    same cascade re-stamp. `AGENTS.md:39` belongs to the scribe rules-slice story, not here.
  - The Assumption at `SPEC.md:1294` names Claude Code >= 2.1.271, drops the Agent-tool `model`-override claim, and
    records the pin refresh as the deferred steward Kinship.
  Then the cascade re-stamp (`updated:` on the PRD, the architecture spine and `epics.md`), `git add`, and the scoped
  stamp for every Spec `spec-surface-check` names.
- **`type: fix`, no flag** (`spec-feature-flag-governance` Q1); the verb stays behind `pyforge.marshal.egm_challenge`.

Ledger key: `113-11-the-challenger-checks-its-preconditions-before-it-spawns-a-reviewer`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-298** (FR-240): the verb, its pin and its refusals.
- **CAP-299** (FR-241): the block's keys and the switch coupling.
- **CAP-300** (FR-242) and **CAP-302** (FR-244): re-derived text only (plugin-absent dispatch; the audit's scope and
  rules-target path).
- This story mints no CAP. Origin: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`
  (cluster MAR-CL6: MAR-M-Z6, MAR-M-D3, MAR-M-C3, MAR-M-C4, MAR-D-C4, MAR-D-R6; the re-derive of cluster MAR-CL10:
  MAR-E1, MAR-D-C1); the operator's ruling of 2026-11-01 on the audit's story-spec scope.

## Acceptance Criteria

- **AC1 — The floor.** With `claude --version` stubbed to `2.1.270`, an unreadable version, and `2.1.271`, the verb
  refuses with the usage code before any spawn (journaled) in the first two cases and proceeds in the third
  (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`).
- **AC2 — The docstring.** `core/challenge.py` names `[challenge].plugin_version` and no `.claude/settings.json` pin.
- **AC3 — The repo-default layer.** A test composes a `[challenge]` block at `repo_defaults` and asserts its
  `REPO_DEFAULTS` provenance, with no file read.
- **AC4 — The contract.** CAP-298, CAP-299, CAP-300, CAP-302 and the Assumption read as the Approach states, re-derived
  by `bmad-spec` (both self-validate passes logged); FR-244 names the `active/` skill path; `spec-surface-check`,
  `chain-currency-sweep-check`, `chain-completeness-check` and `fr-without-cap-check` exit 0.
- **AC5 — Mutation.** Removing the version comparison fails AC1's `2.1.270` case. Restore it.
- **AC6 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` green.

## Boundaries & Constraints

**Always:**
- Read the version through a seam the tests stub; never shell to `claude` from a unit test.

**Ask first:**
- Raising the floor above 2.1.271, or refusing on a version string the parser cannot read in a way other than the usage
  code.

**Never:**
- Never hand-edit `SPEC.md`, a compiled station `SKILL.md` or `AGENTS.md`; never mint a new exit code.
- A story that fails its independent review twice drops to `backlog` and the landing PR proceeds without it (operator
  ruling 2026-11-01).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-298 (FR-240).
- Parent capability: `spec-pyforge-marshal` CAP-299 (FR-241).

Parent: `spec-pyforge-marshal` CAP-298 and CAP-299 (a fix; no CAP minted)

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (the audit lands) entry.
- Research: `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (MAR-CL6,
  MAR-CL10).
- Epic: Epic 113.
- Ledger key: `113-11-the-challenger-checks-its-preconditions-before-it-spawns-a-reviewer`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`,
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`,
  `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`, the re-derived `SPEC.md` and
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md` (FR-244); within
  `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); implemented in the Story 113.7 landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — expected: pass.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0 after the cascade re-stamp.

## Auto Run Result

Status: done (independent review passed 2026-11-01; see Review Triage Log)
this story's; see below). AC4 belongs to the re-derive phase: the `bmad-spec` re-derive, the FR-244 text, the cascade
re-stamp and the scoped stamp are the session owner's, and the memlog events it reads are on `spec-pyforge-marshal`.

**What changed.**

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/challenge.py`: the module docstring names the
  `[challenge].plugin_version` pin (default `0.1.0`, checked against `installed_plugins.json` and the cache
  `plugin.json`) and the Claude Code 2.1.271 floor; it no longer says `.claude/settings.json` (AC2). New
  `CLAUDE_CODE_FLOOR = (2, 1, 271)` and a pure `claude_code_version_refusal(output)`. It returns `None` at or above
  the floor. It returns a reason below the floor, and also when the output is missing or holds no `X.Y.Z`. The
  comparison is numeric on a tuple, so `10.0.1` passes and `2.1.270` refuses.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py`: new `claude_version()`,
  the seam. It runs the packaged claude profile's binary with `--version` through `PosixProcess`. It returns `None`
  when the profile or the binary is missing, the launch fails, or the exit is non-zero.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/challenge.py`: `plugin_refusal` ends with
  `core.claude_code_version_refusal(claude_version())`. The ad hoc, drift and audit paths refuse with the usage code
  before any spawn, journaled as `challenge-refused` through the existing `journal_refusal` (AC1). The readiness hook
  reports it as an `MRS-DISP-067` WARN, spawns nothing, and the dispatch proceeds. The check runs last, so the
  subprocess runs only when every file check has passed. No new exit code, no flag.
- `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`: the `repo` fixture stubs
  `challenge_harness.claude_version`, so no unit test shells to `claude`. New tests:
  - the AC1 matrix (`2.1.270` and an unreadable string refuse, with the usage code, no prompt and one journaled
    `challenge-refused` entry; so does `None`; `2.1.271` and `10.0.1` run);
  - the dispatch-hook floor case (`MRS-DISP-067`, no spawn);
  - AC3: `policy.compose(repo_defaults={"challenge": BLOCK})` gives `PolicyLayer.REPO_DEFAULTS` provenance with no
    file read, and a project block still wins.
- `src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py`: the Story 113.10 `plugin_refusal` test
  stubs the seam, and a new test covers `claude_version` against a stubbed `PosixProcess`. That test checks the argv,
  a non-zero exit, a launch failure, a missing binary and a missing profile.

**Commands run (exit codes read from `$?`).**

- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py src/shared/packages/pyforge-marshal/tests/unit/test_challenge_harness.py src/shared/packages/pyforge-marshal/tests/unit/test_challenge_core.py`
  exited 0 (144 passed).
- AC5, the mutation, ran in memory and left the worktree untouched. A pytest plugin in the scratchpad re-executed
  `claude_code_version_refusal` with the `found < CLAUDE_CODE_FLOOR` comparison deleted. Under it, `-k floor` exited 1:
  the `below-the-floor` case and the dispatch-hook floor test failed, and the other four passed.
- No-shell-out guard: the whole marshal suite ran with a scratch plugin that makes the real `claude_version` raise.
  Nothing reached it except the adapter's own `claude_version` test, which exercises the real function over a stubbed
  `PosixProcess`.
- `ruff check` exited 0 and `ruff format --check` exited 0. Both used the `pyforge-marshal` env's ruff, run from the
  package directory as `lint-types` does, over the five changed Python files.
- `mypy --cache-dir <scratch> -p pyforge.marshal` exited 0 from the package directory (pyforge-guild's mypy, 217
  files). This is marshal's slice of `lint-types`.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` exited 1: 13650 passed, 15 skipped, 3 failed. All
  three are meta-tests that red on `src/platform/tests/test_warden_fleet_proposals.py:31-33` importing `pyforge.warden`.
  That file is another station's uncommitted change in this shared worktree, not this story's:
  - `test_27_2_portal_loop_homes.py::test_src_platform_diff_has_no_pyforge_import`
  - `test_skf_domain_skill.py::test_story_does_not_add_pyforge_under_src_platform`
  - `test_station_persona.py::test_story_does_not_add_pyforge_under_src_platform`
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exited 0. Touched-module unit coverage:
  `adapters/challenge_harness.py` 99.4%, `cli/challenge.py` 84.7%, `core/challenge.py` 95.1%. Every new line is
  covered.
- `pixi run --frozen -e pyforge-guild spec-surface-check` exited 0 before the stamps.
- Not run here: `chain-currency-sweep-check` and the post-stamp `spec-surface-check`. Both follow the re-derive and
  the cascade re-stamp (AC4).

**Memlog.** Two events are on `spec-pyforge-marshal/.memlog.md`:

- the surface reconcile, which names the five Python files and this story spec;
- the CAP-298 / CAP-300 behaviour line for the re-derive.

### Fix round 1 — 2026-11-01

Status: blocked. AC4 is closed except for the `SPEC.md` render and the two self-validate passes that follow it. Earlier
this session the auto-mode classifier refused the script-render route for Story 113.8's fix (`[Auto-Mode Bypass]`),
and this round's brief forbids a `SPEC.md` write. This round did not attempt it: the route needs the operator's
go-ahead (the PR #1605 precedent). No code changed in this round.

- **AC4, the re-derive (`bmad-spec`, headless).**
  - The memlog decision is on `spec-pyforge-marshal/.memlog.md`: `(decision) Re-derive 2026-11-01 (marshal Story
    113.11; EGM audit MAR-M-Z6, MAR-M-D3, MAR-M-C3, MAR-M-C4, MAR-D-C4, MAR-D-R6, MAR-E1, MAR-D-C1; …)`. Its sources
    are the Story 113.11 behaviour event, the Epic 113 build deviations, the Dream's *2026-11-01 (the synthesizer)*
    line and the operator's ruling that story specs stay out of `--audit`.
  - The re-derived text, as the Approach states:
    - CAP-298: the `[challenge].plugin_version` pin (default `0.1.0`, checked against `installed_plugins.json` and the
      cached `plugin.json`), not a `.claude/settings.json` pin. One synchronous session from the packaged `claude`
      profile orchestrates the Agent-tool spawns and assembles the report. The five reviewer agents run on
      `model: inherit` under its `--model`, and its own `--settings` carries the plugin-cache `Read` rules.
      `egm:egm-synthesizer` is never spawned. Claude Code below 2.1.271, or an unreadable version, is refused with the
      usage code and a journaled `challenge-refused` entry before any spawn.
    - CAP-299: `plugin_version` in the key list, the repo-default layer (`REPO_DEFAULTS` provenance, a station block
      wins), and the switch matrix, with `stages` gating only the dispatch hook.
    - CAP-300: a plugin absent or refused, or a refused challenger model, spawns nothing; the hook records an
      `MRS-DISP-067` WARN and the dispatch proceeds.
    - CAP-302: rules targets are `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md` (SKF-compiled,
      never hand-edited; the flat path is a fallback), and the audit never targets a story spec.
    - The Assumption names Claude Code >= 2.1.271 and `model: inherit`, drops the Agent-tool `model`-override claim,
      and records the pin re-verification as the deferred steward Kinship.
  - The anchor-asserting render script is
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/render_113_11.py`.
    It takes the `SPEC.md` path as its argument, and `--dry-run` checks without writing.
  - The script changes 10 lines: the frontmatter `updated:` note, the CAP-298, CAP-299, CAP-300 and CAP-302 definition
    lines (provenance extended at the end) and success lines, and the Assumption. It asserts every needle once,
    undo-to-original byte for byte, an unchanged CAP definition count (303), an unchanged line count (1388), and that
    no stale clause (the `.claude/settings.json` pin, the Agent-tool override, the synthesizer in the roster) is left.
  - It overlaps neither `render_113_8.py` nor `render_113_10.py`, but it must run **last**: it prefixes the `updated:`
    note both of them anchor on.
  - On scratch copies of the live `SPEC.md`, in
    `/tmp/claude-1000/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/f004f771-b628-48bc-8566-9d9f8b02ff2e/scratchpad/r11311/`,
    every run exits 0: the script alone (`--dry-run`), and `render_113_8.py`, then `render_113_10.py`, then this script
    (dry run, then a write). A second run on the rendered copy exits 1, as expected. The live `SPEC.md` is untouched
    (`cmp` against the copy).
  - **Not done:** writing `SPEC.md` and logging the two self-validate passes.
- **AC4, the cascade.**
  - PRD (`prds/prd-pyforge-marshal-2026-07-25/prd.md`): FR-244 names the `active/` compiled-skill path and leaves story
    specs to the `readiness` stage. The FR-240, FR-241 and FR-242 bodies follow the re-derive: the pin key and the
    floor; `plugin_version`, the repo-default layer and the switch matrix; plugin-absent dispatch. § 50 is added, and
    the `updated:` note is prefixed. No FR is added or renumbered, and no arrow moves.
  - Spine: § *Currency reconciliation — 2026-11-01 (Story 113.11)*, with readings on AD-1/AD-3, AD-7, AD-10/AD-50 and
    canopy:AD-11, and the `updated:` note prefixed. No AD is added, amended or removed.
  - `epics.md`: the `updated:` note is prefixed; no epic or story moves.
  - None of the three is on marshal's spec surface (`spec-surface-check` 0), so no surface-reconcile event is needed.
    `AGENTS.md:39` stays with the scribe rules-slice story.
- Commands, exit codes read from `$?`:
  - `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: 0 (13666 passed, 15 skipped; 34 passed, 4 skipped).
  - `pixi run --frozen -e pyforge-marshal python -m pytest` over `test_factory_challenge.py` and
    `test_challenge_harness.py`: 0 (105 passed).
  - `pyforge-marshal-coverage-gate`: 0. It judged no module, because the change is uncommitted.
  - `lint-types`: 1. Its only non-ok leg is pyforge-doctor's ruff import order in
    `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file. pyforge-marshal is ok.
  - `spec-surface-check`: 0. Its one warning is steward's `spec-pyforge-unifying-strategy`.
  - `chain-completeness-check`: 0. `fr-without-cap-check`: 0. `ad-citation-check`: 0. `story-status-check`: 0.
    `deferred-work-check`: 0.
  - `chain_currency_sweep_check.py --json --project pyforge-marshal`: 0 (marshal current). The repo-wide
    `chain-currency-sweep-check` exits 1 on the seven other stations' staleness checkpoints, which are other agents'
    work; marshal reads `current` in it.
- **To unblock (session owner, under the operator-approved render route):**
  1. Run `render_113_8.py`, then `render_113_10.py`, then `render_113_11.py`, on
     `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md`. If Story 113.12
     brings a render script that touches CAP-299's standards span, it can run after these three; this script's
     CAP-299 needles are the key list and the kill-switch sentence only.
  2. Append the two self-validate events with `uv run _bmad/scripts/memlog.py append --workspace
     _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal --type event --text "…"`:
     - Pass 1 (coherence): "bmad-spec self-validate 2026-11-01, Pass 1 (coherence) on the Story 113.11 re-derive of
       CAP-298, CAP-299, CAP-300, CAP-302 and the EGM Assumption: PASS. Each capability keeps its id, title, intent
       and provenance, extended with its findings; each success stays testable against the shipped tree (the floor
       matrix and the REPO_DEFAULTS composition test in test_factory_challenge.py, the flag requirements in
       cli/challenge.py, the dispatch-hook floor test, station_skill_path); no CAP minted (303 definitions), no
       Constraint moved; the Assumption no longer claims an Agent-tool model override or a shipped steward verb.
       SPEC.md script-rendered by render_113_11.py (needles asserted once, undo byte-equal, 10 lines changed, 1388
       lines)."
     - Pass 2 (preservation): "bmad-spec self-validate 2026-11-01, Pass 2 (preservation) on the Story 113.11
       re-derive: PASS. Every load-bearing claim of the Story 113.11 behaviour event, the Epic 113 build deviations
       (1)-(3) and (5), the Dream's 2026-11-01 (the synthesizer) line and the operator's ruling that story specs stay
       out of --audit landed in SPEC.md: the pin key and its two checks, the one orchestrating session,
       model: inherit, the plugin-cache Read rules, no synthesizer, the floor and its journaled refusal on all three
       paths, plugin_version, the repo-default layer, the switch matrix, the plugin-absent MRS-DISP-067 WARN, the
       compiled skill path with its flat fallback, and the deferred steward Kinship. The Story 113.8 and 113.10
       renders' text is kept. Wrapper-only content dropped: the story spec's line numbers and its ledger key."
  3. `git add`, then run the scoped stamp `--spec pyforge-marshal/spec-pyforge-marshal`.
  4. Return this story to `in-review`.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (`research/egm-audit-2026-11-01.md`, cluster MAR-CL6: MAR-M-Z6, MAR-M-D3,
  MAR-M-C3, MAR-M-C4, MAR-D-C4, MAR-D-R6; the CAP-302 re-derive of cluster MAR-CL10: MAR-E1, MAR-D-C1) and the
  operator's ruling of 2026-11-01 (story specs stay out of `--audit`; implement in the Story 113.7 landing PR). The
  Story 113.1 Given's stale pin text is corrected by an append-only note at mint. `type: fix`, no flag, no CAP.

## Review Triage Log

- 2026-11-01 — reviewer: independent session. I did not write this code. I judged `git diff HEAD` of the story's
  files against this spec, not against the Auto Run Result. **Verdict: fail**; status is back to `in-progress`.
  - Read:
    - `core/challenge.py`: `CLAUDE_CODE_FLOOR`, `claude_code_version_refusal` (a numeric tuple compare; no output, or
      no `X.Y.Z`, refuses) and the module docstring.
    - `adapters/challenge_harness.py`: `claude_version()`, the seam. It runs the profile binary's `--version` through
      `PosixProcess` and returns `None` on a missing profile or binary, a launch failure or a non-zero exit.
    - `cli/challenge.py`: `plugin_refusal` ends with the floor check. It is journaled through `journal_refusal`
      before any spawn on the ad hoc, drift and audit paths, and it is an `MRS-DISP-067` WARN in the dispatch hook.
    - The tests.
  - AC1 holds. `test_claude_code_below_the_floor_or_unreadable_refuses_before_any_spawn`:
    - `2.1.270`, an unreadable string and `None` each return the usage code, no prompt and one `challenge-refused`
      journal entry;
    - `2.1.271` and `10.0.1` run.
    - The hook case warns and spawns nothing.
  - AC2 holds. The docstring names `[challenge].plugin_version`. `.claude/settings.json` appears nowhere in
    `core/challenge.py`.
  - AC3 holds. `test_a_repo_default_challenge_block_composes_at_its_own_layer` gives `REPO_DEFAULTS` provenance with
    no file read, and a project block wins.
  - AC5 holds, re-observed. With the `found < CLAUDE_CODE_FLOOR` comparison removed, the run exits 1: the
    `below-the-floor` id and the hook floor test failed.
  - AC6 holds. The suite is green (see the shared evidence).
  - The Always boundary holds: the guard run shows no unit test shells out to `claude`.
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
    1. AC4 is not met. Nothing in the contract has been re-derived:
       - CAP-298 still cites the `.claude/settings.json` pin and lists `egm:egm-synthesizer`;
       - CAP-299, CAP-300, CAP-302 and the Assumption are unchanged (`SPEC.md` has no diff);
       - FR-244 (`prd.md:3597`) still names `.claude/skills/pyforge-<station>/SKILL.md`, not the `active/` path;
       - no self-validate pass is logged for this story;
       - `chain-currency-sweep-check` exits 1.
       `fr-without-cap-check`, `chain-completeness-check` and `spec-surface-check` exit 0. No code change is needed.
       A re-derive with both passes logged, the FR-244 fix in the cascade re-stamp, and marshal's stamp close it;
       return the story to `in-review` after that.

- 2026-11-01 — reviewer: independent session, second review. I did not write this work. I judged the committed code
  (`origin/main..HEAD`), the rendered `SPEC.md` and the PRD against this spec, not against the Auto Run Result or
  the fix rounds. **Verdict: pass**; status set to `done`.
  - AC1 holds. `plugin_refusal` ends with `core.claude_code_version_refusal(claude_version())`.
    `test_claude_code_below_the_floor_or_unreadable_refuses_before_any_spawn` covers `2.1.270`, an unreadable
    string and `None` (usage code, no spawn, one `challenge-refused` entry) and `2.1.271` and `10.0.1` (run). The
    hook case warns and spawns nothing.
  - AC2 holds. The `core/challenge.py` docstring names `[challenge].plugin_version` and the 2.1.271 floor. There is
    no `.claude/settings.json` pin.
  - AC3 holds. `test_a_repo_default_challenge_block_composes_at_its_own_layer` passes.
  - AC4 holds (this review's re-check of the first review's failure):
    - CAP-298 success:
      - the `[challenge].plugin_version` pin (default `0.1.0`, checked against `installed_plugins.json` and the
        cached `plugin.json`); no `settings.json` remains in CAP-298..CAP-303;
      - one synchronous session from the packaged `claude` profile that orchestrates the Agent-tool spawns and
        assembles the report;
      - reviewers on `model: inherit` under its `--model`, and its own `--settings` carrying the plugin-cache
        `Read` rules;
      - a version below 2.1.271, or one it cannot read, refused with the usage code and a journaled
        `challenge-refused` entry before any spawn, on the ad hoc, `drift` and `--audit` paths.
    - CAP-299 success:
      - `plugin_version` is in the key list;
      - the repo-default layer composes with `REPO_DEFAULTS` provenance, and a station block wins;
      - the switch matrix is as the Approach states: `resolve` needs `egm_challenge` and `egm_resolve_bridge` and
        reads no block, and `stages` gates only the hook. This matches `run_challenge`, `_run` and
        `readiness_for_dispatch`.
    - CAP-300 success: a plugin absent or any CAP-298 refusal, the floor among them, or a refused challenger model
      spawns nothing, records an `MRS-DISP-067` WARN, and the dispatch proceeds.
    - CAP-302 success: the rules target is the compiled `active/` skill, with the flat path as the fallback, and the
      audit never targets a story spec. This matches `station_skill_path` and `audit_plan`.
    - The Assumption names Claude Code 2.1.271 or later and `model: inherit`, drops the Agent-tool `model`-override
      claim, and records the pin re-verification as a deferred steward Kinship.
    - FR-244 (`prds/prd-pyforge-marshal-2026-07-25/prd.md:3617-3619`) names
      `.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md`. `fr-without-cap-check` exits 0.
    - The memlog carries the Story 113.11 behaviour event and its `(decision) Re-derive 2026-11-01 (marshal Story
      113.11 ...)`. The CAP-298, CAP-299, CAP-300 and CAP-302 definition lines name Story 113.11. The self-validate
      pair is logged. `spec-surface-check` 0, `chain-completeness-check` 0, chain-currency for marshal 0.
  - AC5 holds, re-observed. With the floor comparison removed, the run exits 1: the `below-the-floor` id and
    `test_dispatch_hook_below_the_claude_code_floor_warns_and_spawns_nothing` failed.
  - AC6 holds. The suite exits 0. The repo fixture stubs `claude_version`, so no unit test shells out to `claude`.
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
