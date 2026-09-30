---
title: '74.2: Dispatch refuses a story the flag gate would red, before any session starts'
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: 'd7c798649479458741580630d995c69af722ec1b'
flag-exempt: detector-or-gate   # a refusal path is a gate; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
warnings:
  - oversized
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_re_preflight.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-3: a post-rule `type: feature` story spec with neither a `flag:` block
nor a `flag-exempt:` value is refused twice — by `detectors-ci` on its PR (CAP-2, doctor Story 34.2) and by `marshal
factory dispatch` before any session starts. Today the nearest refusal, `MRS-GATE-010` (`core/gate.py::check_spec_binding`),
fires in `dispatch_verify` only after a session has done the work. Under Charter §6 Marshal must not decide the flag
verdict itself: the gate belongs to no station, and Marshal is one of the Smiths it judges.

**Approach:** in `cli/dispatch.py::dispatch_once`'s preflight — beside the `MRS-DISP-041` / `042` / `049` refusals and
before any worktree or harness session exists — run the gate on the story's tracked spec as dispatch already locates it:
`<the running interpreter> scripts/flag_gate_check.py --spec <path>` from the repository root, through
`pyforge.core.process.ProcessPort` (the edge `dispatch_verify` already uses for verify commands). Hand the parsed JSON to
a new pure module, `core/dispatch_flag_gate.py`, which returns the decision:
- `red` → REFUSED `MRS-DISP-052`, naming the spec, the gate's findings and the remedy (a `flag:` block or a `flag-exempt:`
  value; `docs/reference/story-spec-flag-block.md` once doctor 34.1 lands).
- `warn` → one WARN finding naming the pre-rule spec; the dispatch proceeds (Ruling 3: backlog warns until retrofitted).
- `pass` → nothing.
- no `scripts/flag_gate_check.py` in the repository → one WARN naming its absence; the dispatch proceeds (a seeded
  repository that has not adopted the rule).
- exit 2, a timeout, or output that is not the gate's JSON → REFUSED `MRS-DISP-052` naming the gate's failure (AD-8:
  unevaluable is failure; never a silent green).
Register `MRS-DISP-052` in `core/findings.py`, and add it to `core/dispatch_re_preflight.py`'s `_RE_PREFLIGHTABLE_GATES`
so a drain's campaign block clears once the spec's fingerprint changes (the `MRS-DISP-005` shape). The module never reads
a spec's frontmatter: the rules live in the gate alone.

**Blocked until doctor Story 34.2 has landed; the operator flips it.** The `--spec` interface is 34.2's. The ledger key is
minted `blocked` because the `Deps:` parser is station-local (AGENTS.md § Known pitfalls; the doctor 33.1 precedent).

Ledger key: `74-2-dispatch-refuses-a-story-the-flag-gate-would-red-before-any-session-starts`.
Ledger status (do not edit the ledger): `backlog` -- flipped 2026-09-30 by the operator after doctor Story 34.2 landed on main (5a6dbc5e21).
Type / Effort / Deps: feature / S / — (cross-project gate: doctor Story 34.2).

### Living CAP citations

- `spec-feature-flag-governance` CAP-3 (Guild-owned; Marshal's stories per the Spec's table). No marshal CAP or FR (PRD
  § 31.11).
- AD-4 (pure decision, impure edge), AD-5 (the warning journaled), AD-8 (unevaluable is failure), AD-15 (a coded finding).
- Kinship: doctor Story 34.2 (the gate and its `--spec` interface); `MRS-GATE-010` (the spec-binding refusal after the
  work).

## Acceptance Criteria

- Given a fake `ProcessPort` answering `{"verdict": "red", …}` with exit 1 When `dispatch_once` runs Then it returns REFUSED `MRS-DISP-052` naming the spec and the findings, and no worktree is created and no harness launched
- Given `{"verdict": "warn", …}` with exit 0 When `dispatch_once` runs Then one WARN finding is journaled and the dispatch proceeds
- Given `{"verdict": "pass", …}` When `dispatch_once` runs Then no flag finding and the dispatch proceeds as today
- Given no `scripts/flag_gate_check.py` in the repository When `dispatch_once` runs Then one WARN names its absence and the dispatch proceeds
- Given exit 2, a timeout, or non-JSON output When `dispatch_once` runs Then it returns REFUSED `MRS-DISP-052` naming the gate's failure
- Given a drain cycle that met `MRS-DISP-052` When the spec's fingerprint changes Then the next cycle re-preflights the story
- Given `core/dispatch_flag_gate.py` When the unit suite runs Then a test fails if the module reads a spec's frontmatter itself
- Given the consult removed from the preflight When the red fixture runs Then it dispatches and the test fails (mutation)
- Given the code registry When the AD-15 meta-test runs Then `MRS-DISP-052` is registered once
- Given the change When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test` run Then both pass

## Boundaries & Constraints

**Always:**
- Keep the decision pure in `core/` and the process call at the edge (AD-4); consult the gate, never restate its rules.
- Refuse before any worktree, harness session or campaign launch; a refusal changes zero paths.
- Keep every other preflight refusal and its order unchanged.

**Never:**
- Do not import `scripts/` or any doctor module; the gate is a process.
- Do not add a policy key that turns the consult off: the gate is the Guild's (Charter §6), and CI reds regardless.
- Do not start before doctor Story 34.2 has landed; do not flip this story's ledger key.
- Do not edit `SPEC.md` or `sprint-status-ledger.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new feature, no block | gate `red`, exit 1 | REFUSED `MRS-DISP-052` | zero changed paths |
| pre-rule backlog | gate `warn`, exit 0 | WARN journaled, proceeds | — |
| flagged or exempt | gate `pass` | proceeds as today | — |
| gate absent | no script | WARN, proceeds | — |
| gate cannot judge | exit 2 | REFUSED naming the failure | — |
| gate hangs | timeout | REFUSED naming the timeout | — |
| drain re-run | spec edited after refusal | re-preflighted | — |

</intent-contract>

## Code Map

Investigated 2026-09-30 (step 2). Paths are under `src/shared/packages/pyforge-marshal/` unless they start `scripts/` or `docs/`.

- `src/pyforge/marshal/cli/dispatch.py` -- `dispatch_once` (L2024). Preflight order today: repo root (L2080) -> `_surface_session_precondition_findings` (L2091, WARN `MRS-DISP-049`) -> `_dispatch_scope_refusal` (L2095, ERROR `041`) -> `resolve_story_spec_path` (L2100, ERROR `005`) -> spec read (L2115-2125) -> `_compose_policy` (L2127) -> harness walk -> worktree. A refusal appends an ERROR `Finding` and `return _done()`; `DispatchAttempt.errors` (L159) is the ERROR-severity subset and `_classify_attempt` (L3697) turns `errors[0]` into the campaign-block detail `"<code>: <message>"`, which `dispatch_re_preflight.parse_refuse_gate` reads. Add `_consult_flag_gate(*, fs, process, repo_root, spec_path) -> Finding | None` next to `_surface_session_precondition_findings` (L458, the same `process.run` / `ProcessError` shape) and call it right after the spec read, before `_compose_policy`: append the finding; if its severity is ERROR, `return _done()`. Script presence through `fs.exists(repo_root / "scripts" / "flag_gate_check.py")`; argv `[sys.executable, "scripts/flag_gate_check.py", "--spec", <spec path relative to repo_root, posix>]`, `cwd=repo_root`, a `_FLAG_GATE_TIMEOUT_S = 60.0` beside `_SESSION_CHECK_TIMEOUT_S` (L455).
- `src/pyforge/marshal/core/dispatch_flag_gate.py` -- NEW, pure (AD-4). Imports only `json`, `dataclasses` if needed, and `.findings` (`Finding`, `Severity`); no `pathlib`, no `open`/`read_text`, no frontmatter parsing. Three functions: `decide_gate_result(spec, *, returncode, stdout, stderr)`, `decide_gate_failure(spec, failure)` (the `ProcessError` text, incl. the timeout) and `gate_absent_finding(script_rel)`; each returns `Finding | None`. Style sibling: `core/dispatch_prelaunch.py::spec_binding_findings`.
- `src/pyforge/marshal/core/findings.py` (`REGISTERED_CODES`, the `MRS-DISP-051` / `053` / `054` block, ~L1816-1835) and `src/pyforge/marshal/core/verdict.py` (`_CLASSIFY_TABLE`, the same block, ~L1181-1193) -- the two registries; a new code goes in both. `052` -> `Verdict.ERROR`, `055` -> `Verdict.WARN`. `050` is Story 65.2's and `053`/`054` Story 77.1's; `055` is claimed nowhere.
- `src/pyforge/marshal/core/dispatch_re_preflight.py` -- `_RE_PREFLIGHTABLE_GATES` (L55) gains `MRS-DISP-052`. `reconcile_station_re_preflight` (L126) rate-limits every non-`MRS-GATE-` gate whose spec fingerprint changed (L201-212), so `052` needs its own CLEARED branch: after the `previous is None` rate-limit (L175) and before the `MRS-GATE-` branch (L189), clear when `gate == "MRS-DISP-052"` and `previous.spec_fingerprint != current.spec_fingerprint`. The drain records the predicate for a REFUSED station at `cli/dispatch.py` L4421-4433.
- `scripts/flag_gate_check.py` (read only) -- `run_spec` (L525-546): prints one JSON object `{verdict, spec, rule_date, findings[], error?}`; exit 1 iff `red`, 2 for `unknown`, else 0. A finding is `{kind, severity: fail|warn, message, path?, station?, key?}`. It runs from its own checkout (`--root` defaults to the script's parent). `docs/reference/story-spec-flag-block.md` exists (doctor 34.1), so the refusal's remedy cites it.
- `pyforge-core` `src/pyforge/core/process.py` (read only) -- `ProcessPort.run` never raises for a non-zero exit; it raises `ProcessError` for an unlaunchable argv or a timeout ("command timed out after Ns: ...").
- `core/verdict.py::compute_verdict` (L1313) classifies by `finding.code` alone (L1327), never by `Finding.severity`; AD-31 forbids one code on two rungs. That is why the two WARN outcomes take their own code (Design Notes).
- Tests: `tests/unit/test_dispatch.py` (`FakeFs` L60-112, `FakeVcs`, `FakeBuildHarness`, `FakeProcess` L189-207, `_init_git_repo`, the `dispatch_once` wiring test L264-294 as the template); `tests/unit/test_dispatch_hotfix.py` L248-410 (the re-preflight tests, `re_preflight` alias); `tests/unit/test_findings.py` L65 (exact `REGISTERED_CODES` set) and L533 (a per-code tier test, the `MRS-DISP-051` shape). The seeded repos in those tests carry no `scripts/flag_gate_check.py`, so after this change every `dispatch_once` test sees the WARN `MRS-DISP-055`; a test that asserts the exact finding list needs the new code, never a suppression.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/marshal/core/findings.py`, `src/pyforge/marshal/core/verdict.py` -- register `MRS-DISP-052` (ERROR) and `MRS-DISP-055` (WARN), each with the dated comment its neighbours carry -- rationale: AD-15 and AD-31
- [x] `src/pyforge/marshal/core/dispatch_flag_gate.py` -- NEW. `decide_gate_result`: `returncode` 0 or 1 and `stdout` a JSON object whose `verdict` agrees with the exit code (`red` <-> 1; `pass`/`warn` <-> 0) -> `red`: ERROR `MRS-DISP-052` naming the spec, each `fail` finding's `kind` and `message`, and the remedy (a `flag:` block or a `flag-exempt:` value, `docs/reference/story-spec-flag-block.md`); `warn`: WARN `MRS-DISP-055` naming the pre-rule spec; `pass`: `None`. Anything else -- exit 2, another exit code, non-JSON, a non-object, a missing or `unknown` verdict, a verdict that disagrees with the exit code -- ERROR `MRS-DISP-052` naming the gate's failure (its `error` field, else the last stderr line, else the exit code). `decide_gate_failure`: ERROR `MRS-DISP-052` carrying the `ProcessError` text. `gate_absent_finding`: WARN `MRS-DISP-055` naming the missing script -- rationale: AD-8, unevaluable is failure, never a silent green
- [x] `src/pyforge/marshal/cli/dispatch.py` -- `_consult_flag_gate` and its call site in `dispatch_once`, as the Code Map places it; no policy key, no import of `scripts/` or a doctor module -- rationale: AD-4 (impure edge), the gate is a process
- [x] `src/pyforge/marshal/core/dispatch_re_preflight.py` -- `MRS-DISP-052` joins `_RE_PREFLIGHTABLE_GATES` with its own CLEARED branch -- rationale: a drain re-preflights once the spec is edited
- [x] `tests/unit/test_dispatch_flag_gate.py` (NEW), `tests/unit/test_dispatch.py`, `tests/unit/test_dispatch_re_preflight.py` (NEW), `tests/unit/test_findings.py` -- one test per Acceptance Criterion below, plus the I/O-matrix rows; every existing test that the new `055` WARN changes is updated to expect it
- [x] Surface reconcile -- run `python scripts/spec_surface_reconcile.py`; name every governed path this story changed on the owning Spec's `.memlog.md` (`spec-pyforge-marshal`) and on each co-governor `spec-surface` names (`spec-pyforge-core` governs every station's `src/`), with `python _bmad/scripts/memlog.py append --workspace <spec-folder> --type event --text "Surface reconcile 2026-09-30: <path> ..."`; never `--write-baseline`

**Acceptance Criteria:**
- Given the ten Acceptance Criteria in the intent contract, when the suite runs, then each maps to one named test and every one passes
- Given a red fixture and `_consult_flag_gate` patched to return `None`, when `dispatch_once` runs, then the story dispatches and the refusal test fails (the mutation)
- Given `core/dispatch_flag_gate.py`, when its source is scanned by AST, then it imports nothing outside the allow-list and calls no `open` / `read_text` / `read_bytes`; the scanner itself is proven on a synthetic module that reads frontmatter

## Design Notes

- **Why a second code.** The contract names only `MRS-DISP-052`, but `compute_verdict` reads `classify(finding.code)` and AD-31 forbids one code on two rungs, so a WARN under an ERROR-tier `052` would red a dispatch that proceeds. The two WARN outcomes (a pre-rule spec, an absent gate) therefore take `MRS-DISP-055`, WARN tier, the `042` / `049` / `053` tier. `052` stays registered once, as the AD-15 criterion requires.
- **Exit code and verdict must agree.** The gate documents `red` <-> exit 1 and `pass`/`warn` <-> exit 0. A JSON `pass` with exit 1, or `red` with exit 0, is not a verdict the consult can trust, so it refuses (AD-8) rather than choosing one of the two signals.
- **Drain shape.** The refusal detail begins `MRS-DISP-052:` (from `_classify_attempt`), which is the form `parse_refuse_gate` reads. The first re-preflight after a refusal rate-limits (no prior predicate); a later tick with a different spec fingerprint clears, so the next cycle runs `dispatch_once` again and the gate judges the edited spec.
- **Out of scope, on purpose.** `cli/drain_plan.py` mirrors some `dispatch_once` refusals for `--plan`; the contract does not ask for `052` there, and a drain's own cycle already reaches it through `dispatch_once`.

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-3 and the Q7 ruling (memlog 23),
decomposed 2026-09-28 (night) as Epic 74's mint.

## Spec Change Log

- 2026-09-30 -- operator flip, `blocked` -> `backlog`: the cross-station gate cleared when doctor Story 34.2 landed on main (5a6dbc5e21). Nothing else in the contract changed. A resumed worktree brings `origin/main` into its branch first (merge, never rebase).
- 2026-09-30 -- step-02 planning, no contract change: (1) the two WARN outcomes take a sibling code, `MRS-DISP-055`, because the verdict is classified by code and AD-31 gives one code one rung (Design Notes); `MRS-DISP-052` is still the only code the Acceptance Criteria name and is registered once. (2) The frontmatter `status` was `backlog`, which step-01 does not list; it was treated as "not yet planned", the path Stories 74.1, 75.1, 76.1, 77.1 and 78.1 took.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-3 (Guild-owned; Marshal's story).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `74-2-dispatch-refuses-a-story-the-flag-gate-would-red-before-any-session-starts`.
Ledger status at mint: `blocked` (cross-project gate: doctor Story 34.2).
Policy: `marshal-policy.toml` `[epic_surfaces]` `"74"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- On a scratch branch with a post-rule `type: feature` spec that has neither block nor exemption, `pixi run -e pyforge-guild marshal factory dispatch <project> <story>` — expected: REFUSED `MRS-DISP-052`, no worktree created.
- The same with a `flag-exempt:` value added — expected: the dispatch proceeds past preflight.

## Review Triage Log
