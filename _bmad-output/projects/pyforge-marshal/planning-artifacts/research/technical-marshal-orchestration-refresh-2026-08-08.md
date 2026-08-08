# Technical research — Marshal orchestration, 2026-08-08 refresh

> **Refreshes** `technical-bmad-ecosystem-verification-research-2026-07-31.md`
> (whose upstream-verification verdicts are carried, not re-litigated — § 5)
> and grounds a fresh debt/opportunity survey in the shipped package:
> `src/shared/packages/pyforge-marshal/` — **34,173 src LOC / 46 modules,
> 44,616 test LOC / 65 files (1.3× source)**, 14 top-level `marshal`
> subcommands, all 50 Epic 1–6 stories `done` in
> `planning-artifacts/sprint-status-ledger.yaml`. Companion docs of the same
> date: `domain-marshal-orchestration-2026-08-08.md`,
> `market-marshal-orchestration-refresh-2026-08-08.md`,
> `technical-pyforge-unification-2026-08-08.md`.

## 1. The dream map — synthesizing the sprawl into one table

The operator's framing was "16 dream files is itself evidence of scope
sprawl." Measured 2026-08-08 (frontmatter `owner: marshal`,
`docs/dreams/*.md`): **23 files** — and the count is *evidence of hygiene,
not sprawl*, because 11 of the 23 are deliberate archive records of
consolidation, not open scope:

| State | Count | Files |
|---|---|---|
| **Realized** (standing, kept) | 5 | `pyforge-marshal.md` (the hub), `agent-tool-surface.md`, `regenerable-factory.md`, `bmad-loop-forward-dependency-blindness.md`, `bmad-output-hygiene.md` |
| **Pitched** (practice, kept) | 1 | `agentic-sdlc-autonomy.md` |
| **Archived/absorbed** (vision lives in FRs/Specs) | 9 | `agent-portability` (→CAP-6/E6), `durable-runs` (→FR-61..63), `fidelity-enforcement` (→FR-64), `one-front-door` (→FR-65), `pr-lifecycle` (→FR-59/60), `factory-console` (spec live), `fleet-chain-completeness` (spec live), `pyforge-testing-charter` (CAP-3/4 unbuilt), `genesis-installer` (epics 7–12 live) |
| **Archived/retired or duplicate** | 2 | `artifact-console` (superseded by the Pages console), `pyforge-marshal-loop-orchestrator` (fabricated bulk-commit duplicate, retired same day) |
| **Dreamt (the REAL open backlog beyond the epics)** | 6 | `genesis-installer-name-retirement`, `sprint-status-auto-promote`, `loop-home-fleet-refresh`, `dashboard-project-path-derivation`, `dream-to-code-model-self-verification`, `jira-github-projects-sync` |

The actionable synthesis: Marshal's open surface is exactly (a) Epics 7–12
(36 stories: 35 `backlog` + `8-5` `blocked` on forward-dep S-10.2), (b) the
six `dreamt` files above, (c) two live undecomposed Specs
(`spec-fleet-chain-completeness`, `spec-factory-console` frontier) plus the
testing charter's CAP-3/CAP-4, and (d) the deferred-work ledger (§ 3). Every
other dream file is a closed record. A `dream_chain_check.py --dreams`
hygiene mode (the `dream-to-code-model-self-verification` ask) would let this
table be derived instead of hand-counted — this doc's own § 1 is the use case.

## 2. Shipped-code quality — what is genuinely good

Worth stating before the debt, because it is unusual and load-bearing:

- **Zero TODO/FIXME/XXX markers in src.** Debt is tracked out-of-band in
  `planning-artifacts/deferred-work-ledger.md` (493 lines, 35 entries
  `status: open`, 11 done) — the ledger, not the code, is the debt registry.
- **17 meta-tests enforce the architecture by AST/import-lint** (AD-3
  bmad_loop containment, AD-4 core purity — `core/**` may not import
  `subprocess`/`os`/`time`/adapters, AD-7 verdict sole-ownership, AD-9
  supervisor→cli forbidden so a session structurally cannot silence its own
  supervisor, AD-31 conformance-can-genuinely-fail, AD-36 no
  platform-branching outside one table, …). The governance claims in the
  domain doc are mechanically enforced, not conventions.
- **Ports/adapters is real**: 9 Protocol ports, exactly one adapter each;
  `harness_bmadloop.py` is the only module permitted to import `bmad_loop`.
- **Policy defaults are empirically calibrated** (comment in
  `core/policy.py`: measured over 30 real runs / 53 stories —
  `idle_threshold_minutes=25`, `max_tokens_per_story=50M`, etc.).
- **The supervisor closes bmad-loop's worst documented blind spot.** Auto-
  memory (`feedback_bmad_loop_blind_spots.md`) records a 2.5-hour stall at an
  interactive billing prompt that `bmad-loop status` reported as
  `review-running`. Epic 3's shipped idle ladder samples exactly the
  externally-observable quantities the manual runbook used —
  `SessionObserverPort.pane_content` + log mtime (`core/supervise.py::
  evaluate_idle`, 3 rungs nudge → stop-and-retry → defer) — so a
  static-pane prompt stall now trips the ladder at the 25-minute threshold.
  The memory entry predates supervised runs and should gain a "superseded
  when the run is marshal-spun" note.

## 3. Real technical debt (ranked)

1. **`tests/contract/` contains only a README — no harness contract tests
   exist despite NFR-9.** This is the largest verification gap: the wrap
   seam to bmad-loop (`>=0.9.0,<0.10`, argv literals at
   `harness_bmadloop.py:668,764,889,994,1102,1176`, lazy imports of five
   `bmad_loop.*` modules) is exercised only through unit mocks. The 07-31
   research noted v0.9.0's JSON output "makes NFR-9 contract tests cheaper" —
   they were never written.
2. **The vendored `_POLICY_TEMPLATE`** (115 lines at
   `harness_bmadloop.py:222`) reproduces bmad-loop 0.9.0's entire
   `.bmad-loop/policy.toml` schema because upstream hard-codes the policy
   path. It will silently rot on any harness minor bump; a contract test
   (item 1) is also the mitigation here — render the template, run
   `bmad-loop validate` against it.
3. **The resolve-context-once refactor is knowingly half-done.**
   `cli/main.py` documents that `run_spin`/`run_status`/`run_land` accept
   `context=` but still re-derive policy and home paths internally; the
   slug-validate → policy-path → OSError-probe sequence is copy-pasted in
   `cli/status.py`, `cli/land.py`, `cli/retire.py`, `cli/gate.py`, and
   `main._resolve_context` (one review finding was fixed by adding a sixth
   copy). Story 5.6 named `MarshalContext` a "deliberately scoped-down first
   step"; the second step has no story.
4. **CLI-layer megafiles.** `cli/deploy.py` 3,278 lines (five handlers),
   `cli/init.py` 2,404 (four commands), `cli/spin.py` 2,319,
   `supervisor/__main__.py` 2,499 with `run_supervisor` a ~1,700-line
   function, `cli/adapters.py` 1,988. The core stayed clean because AD-4
   polices it; the CLI layer has no equivalent size discipline. Splitting
   `deploy.py` by handler and extracting the supervisor tick body are
   mechanical.
5. **AD-3's documented scope gap**: the import-linter contract's
   `source_modules` deliberately excludes `pyforge.marshal.adapters` as a
   package, so a *future* adapter that wrongly imports `bmad_loop` is
   uncaught until someone remembers to list it. Derive the module list from
   the filesystem (the repo's own "derive, don't declare" memory rule).
6. **Five in-package copies of the `_run()` subprocess wrapper**
   (`vcs_git.py`, `forge_gh.py` — whose docstring admits it "mirrors
   `vcs_git.py`'s own `_run()` almost exactly" — `harness_bmadloop.py`,
   `observer_mux.py`, `notify_file_desktop.py`), and `SystemClock`
   duplicating `cli/spin.py::_now_utc`. Fleet-wide this same wrapper exists
   in 7+ variants across stations — the unification doc § 7 ranks it.
7. **Small hygiene**: `__version__ = "0.1.0"` in `cli/main.py` hand-synced
   with pyproject; `tomlkit>=0.13,<0.13.3` upper bound copied from the root
   repo's unrelated dagster-dg-core pin (an inherited constraint, not a
   marshal need); exactly one integration test
   (`tests/integration/test_init_worktree.py`, slow-marked, excluded from
   the default test task); the sprint ledger carries `epic-*` retro keys in
   mixed states (7 backlog / 8 optional / 9 done) that inflate naive counts
   (110 keys ≠ 86 stories).
8. **Docstring-as-ADR drift risk**: module docstrings run 40–100+ lines of
   rationale (`core/findings.py` is ~1,200 lines of narrative around three
   code objects). Deliberate and valuable — but nothing detects prose that
   stops matching code, and this package's whole thesis is that undetected
   drift is a defect.

## 4. Real opportunities (beyond fixing § 3)

1. **Make Epic 7 the shared-spine extraction, not another copy.** Stories
   7.2 (error taxonomy + exit codes) and 7.3 (write primitive + never-write
   guard) are scoped to *rebuild inside a new `pyforge-genesis` package*
   what already exists 5× (exit codes) and ~20× (atomic write) across the
   fleet — the full duplication census is in
   `technical-pyforge-unification-2026-08-08.md` § 7. Deciding
   shared-vs-rebuilt *before* S-7.1 opens is the single highest-leverage
   sequencing call available, and the `genesis-installer-name-retirement`
   Dream already demands a planning-chain pass over the unified Spec first
   (argparse-vs-typer, `check`/`init` verb collisions — Open Question 17).
2. **Wire the supervisor's triggers to the two "remembered step" dreams.**
   `supervisor/durability.py::classify_push_triggers` already detects the
   `done`-phase boundary edge per story; the same edge is precisely the
   trigger `sprint-status-auto-promote` needs (run
   `promote_sprint_status.py` + dashboard regen) and half of
   `loop-home-fleet-refresh` (push side). Both dreams could be one small
   supervisor duty + one `marshal` verb rather than new products.
3. **Turn `marshal status --reconcile-ledger` into the standing detector.**
   It already tags discrepancies confirmed/unconfirmed against git evidence;
   scheduling it (detector registry, `marshal check`) closes the
   dashboard-staleness class structurally.
4. **Ship the contract-test layer as the next test story** (§ 3.1/3.2
   together): version-range probe, `--version`/JSON-output shape, policy
   template round-trip through `bmad-loop validate`, merge-subject format.
   This is also the cheapest insurance on the upstream convergence watch
   ("Dev Loop Automation" on the BMAD roadmap, 07-31 research § 3).

## 5. Refreshed 2026-08-08 — carry-forward from the 07-31 verification

Confirmed still-standing, no re-verification performed this round: bmad-loop
pin `>=0.9.0,<0.10` (now consumed as a plain conda dep built from the repo's
own `recipes/bmad-loop/recipe.yaml` — the git-pin era described in
`docs/specs/bmad-loop-adoption.md` is over); wrap-never-absorb with the
Dev-Loop-Automation convergence watch; ACP Q-6 deferral (pressure rising);
OTel `gen_ai.*` Q-5 deferral. The FR-13 re-scope ("external, un-disableable
enforcement" rather than "no enforcement upstream") is now moot in the best
way: the external supervisor shipped. New watch item this round: **the
harness version range's upper bound (`<0.10`)** — upstream released 10 times
in 23 days at last measurement; a 0.10 release will hard-warn every
`marshal --version` and strand the vendored policy template (§ 3.2) at the
same moment.
