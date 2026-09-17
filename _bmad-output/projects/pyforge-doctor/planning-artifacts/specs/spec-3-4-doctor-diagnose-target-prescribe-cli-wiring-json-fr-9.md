---
title: '`doctor diagnose --target … --prescribe` CLI wiring, `--json`'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-2-3-doctor-monitor-fleet-cli-wiring-default-axis-set-json.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-3-3-root-cause-naming.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/prescribe.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
]
warnings: []
baseline_revision: 'HEAD at Story 3.4 start (after Story 3.3 landed)'
---

<intent-contract>

## Intent

**Problem:** Epic 3's `partition`/`rank`/`name_root_cause` (Stories 3.1-3.3) are all library-level pure functions with no CLI entry point — `doctor diagnose` doesn't exist yet.

**Approach:** Wire a `diagnose` subparser (`--target TARGET` required, `--prescribe` optional, `--json`) that gathers Findings for one target — Epic 2's `sources.atlas.gather` (always, scoped to `TARGET` as the maintainer/feedstock filter, default axis set `staleness,cve` reusing `monitor`'s own default) composed with Epic 1's engine+env checks (only when `TARGET` is ALSO a real local directory — "when the target implies an environment check," the AC's own wording, operationalized as `Path(target).is_dir()`) — then, only with `--prescribe`, runs Story 3.1→3.2→3.3's pipeline over every gathered Finding to populate `prescriptions`.

## Boundaries & Constraints

**Always:**
- `--target` is required (usage error, exit 2, if omitted).
- Without `--prescribe`: Findings are gathered and reported; the JSON envelope's `prescriptions` key is STILL PRESENT (an empty array) — Story 1.1's frozen `DoctorReport` contract requires `prescriptions` for every `verb == "diagnose"` report regardless of `--prescribe`. The HUMAN-readable render, however, shows NO prescription section at all when `--prescribe` wasn't given (an empty section would misleadingly read as "ran and found nothing" rather than "didn't run").
- With `--prescribe`: EVERY gathered Finding becomes exactly one `Prescription` (Story 3.1's "never a silent drop" rule, extended past partitioning into the full pipeline) — `ACTIONABLE` Findings carry a real 1-based `rank`/populated `rank_factors` from `prescribe.rank`; `BLOCKED`/`ACCEPTED_RISK` Findings carry `rank=None`/`rank_factors=None` (the schema's own documented null-until-populated shape).
- `target_path.is_dir()` gates the engine+env gather — this is the ONE operational meaning of "when the target implies an environment check": `TARGET` doubles as a local path when it happens to resolve to one, exactly the same way `check`'s own positional `path` argument works, and is skipped entirely (never attempted, never even a `Path.exists()` probe beyond the initial check) otherwise.
- `--json` produces a schema-valid `DoctorReport`, `verb: "diagnose"`, with the same self-validation-before-stdout discipline `check`/`monitor` already have.

**Never:**
- Never omit the `prescriptions` key from JSON output for `verb == "diagnose"`, with or without `--prescribe` — `DoctorReport.__post_init__` itself would raise if this were attempted (Story 1.1's own frozen invariant, unchanged and unbypassed here).
- Never add a new gather path of its own — `diagnose` composes ONLY Epic 1's `warden_source.gather`/`env_hygiene.gather` and Epic 2's `atlas.gather`, zero new subprocess/MCP call sites (this story adds none; `prescribe.py`'s own AD-4 purity is untouched, since `_build_prescriptions` only calls `prescribe`'s already-pure functions).
- Never let `--prescribe`'s pipeline run when the flag is absent — the plain (no-`--prescribe`) path must never call `prescribe.partition`/`prescribe.rank`/`prescribe.name_root_cause` at all.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `doctor diagnose` (no `--target`) | Missing required flag | Usage error, exit 2 | argparse's own required-arg check |
| `doctor diagnose --target X` (no `--prescribe`) | Findings gathered | Findings reported; human output has no prescription section; `--json`'s `prescriptions` is `[]` | No error |
| `--target X --prescribe` | Mixed actionable/blocked/accepted-risk Findings | Every Finding becomes a `Prescription`; actionable ones ranked, others `rank=None` | No error |
| `--target X --prescribe`, only blocked/accepted-risk Findings | Nothing actionable today | Still lists every one of them, `rank=None` for all — never an empty/misleadingly-clean result | No error |
| `--target <existing local dir>` | Directory-shaped target | `warden_source.gather`/`env_hygiene.gather` ALSO run against it, findings merged with the atlas ones | No error |
| `--target <non-directory string, e.g. a maintainer handle>` | Ordinary case | Only the atlas gather runs — engine/env checks skipped entirely | No error |
| `--json` | Any run | Schema-valid `DoctorReport`, `verb: "diagnose"`, `prescriptions` array always present | Self-validated before stdout |
| `--prescribe --json` | Any run | `prescriptions[].rank`/`rank_factors`/`root_cause`/`action`/`finding_ref` all populated per Story 3.1/3.2/3.3's own output shapes | No error |
| A gathered `FAIL` finding present | Any | Exit code 2 | `verdict.exit_code_for`, unchanged |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — EDIT. New `diagnose` subparser in `_build_parser` (now returns a 4-tuple); `_action_text`/`_build_prescriptions` (assembles `Prescription` objects from `prescribe`'s three pipeline functions); `_run_diagnose`; `_emit_json`/`_emit_text` gain an optional `prescriptions` keyword (JSON always receives the real tuple for `verb="diagnose"`; text receives `None` when `--prescribe` wasn't given, suppressing the section entirely). New `from . import prescribe` and `Partition`/`Prescription` imports from `.models`. `_DEFAULT_DIAGNOSE_AXES` (an alias of `_DEFAULT_MONITOR_AXES`).
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py` — NEW. Full I/O matrix (11 tests): `--target` required, plain gather-and-report with no prescription section, JSON `prescriptions: []` when `--prescribe` is omitted, `--prescribe` populating prescriptions for every Finding with correct partitions, schema-valid `--prescribe --json` with rank/root-cause/action/finding_ref all populated, the blocked/accepted-risk-only AC3 case (all unranked, still listed), human-readable prescription-section rendering, directory-shaped-target engine+env composition (both positive and negative cases), exit-code reflection, default-axis-set proof.

## Design Notes

**Why "the target implies an environment check" is operationalized as `Path(target).is_dir()`, not a separate `--path` flag:** the AC's exact wording ("composing Epic 1's check filter when the target implies an environment check") describes a CONDITION on `--target`'s own value, not a second independent input. `check`'s own positional `path` argument already establishes the convention that a string naming an existing local directory IS a scan target; reusing that exact semantic for `--target` avoids introducing a second flag whose relationship to `--target` would need its own explanation, and makes `doctor diagnose --target .` (diagnosing the current checkout) behave exactly as an operator would expect without reading documentation first.

**Why the plain (no-`--prescribe`) JSON path still carries an empty `prescriptions` array while the text path shows nothing:** these are two DIFFERENT parity requirements operating at different layers. The JSON envelope's shape is Story 1.1's frozen, machine-facing contract (`verb == "diagnose"` requires the key, period — enforced by `DoctorReport.__post_init__` itself, which this story does not and cannot bypass). The human-readable render is a DIFFERENT, presentation-layer decision: an operator running `doctor diagnose --target X` without `--prescribe` should see a plain Finding report, not a "0 prescription(s)" line that reads as a (mis)leading claim that ranking was attempted and came up empty. Resolved by conditioning `_emit_text`'s `prescriptions` argument on `args.prescribe` while `_emit_json`'s stays unconditional — a deliberate, documented asymmetry, not an oversight.

**Why `_build_prescriptions` correlates `rank`/`rank_factors` back onto each `PartitionedFinding` via `id(finding)`, not equality:** `prescribe.rank()` returns `RankedPrescription`s built directly from the SAME `Finding` objects `prescribe.partition()` produced (no copying anywhere in the pipeline), so object identity is both sufficient and the more defensively-correct choice — two structurally-identical-but-distinct `Finding`s (a real possibility if a future axis ever emits a duplicate row) must not accidentally share a rank via value-equality; `id()` guarantees the lookup only ever matches the exact object `rank()` actually scored.

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py -q`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — **331 passed** (320 baseline from Story 3.3 + 11 new tests from `test_cli_diagnose.py`).
- Isolated run: 11 passed.

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0

Checked specifically for: exception handling (`_run_diagnose`'s dispatch has no new exception surface -- `atlas.gather`/`warden_source.gather`/`env_hygiene.gather` already degrade to FAIL Findings internally per their own Epic 1/2 contracts; `prescribe`'s three functions are provably exception-free over well-formed `Finding` input, per Stories 3.1-3.3's own review passes); resource leaks (none -- `Path(target).is_dir()` is a single stat call, no open handle); silent failures (every gathered Finding becomes exactly one Prescription when `--prescribe` is given, proven by the "only blocked/accepted-risk" test mirroring AC3's own scenario); id()-based correlation risk (double-checked `prescribe.rank`'s own implementation -- it slices `[pf.finding for pf in partitioned ...]` with no copy, so `id()` matching in `_build_prescriptions` is sound, not merely "usually works"); docstring-vs-behavior drift (re-read `_run_diagnose`'s and `_build_prescriptions`'s docstrings against the actual code -- both match, including the JSON-vs-text prescriptions asymmetry, which is explicitly called out in both the docstring and this spec's own Design Notes rather than left implicit).

**Follow-up review recommendation: false** -- no findings; this story composes only already-reviewed Epic 1/2/3 building blocks with no new failure surface of its own.


### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter, Epic 2+3 batch)

Dispatched with the diff file path only, no shared context. Two findings landed here:

- `high` `patch` **`_action_text` told the operator to remediate a clean Finding.** A clean (`DoctorStatus.OK`) Finding lands in `Partition.ACTIONABLE` (Story 3.1's "every Finding lands somewhere" rule) with `reason="clean -- no remediation needed"`, but `_action_text`'s `ACTIONABLE` branch unconditionally rendered `f"address {check} ({source})"`, discarding that reason -- actively telling the operator to remediate something that already passed. Fixed: `_action_text` now checks `pf.finding.status is DoctorStatus.OK` first and returns `pf.reason` verbatim in that case. New test: `test_diagnose_prescribe_clean_finding_action_is_not_a_remediation_instruction`. (The companion rank-layer half of this same finding is recorded in Story 3.2's own spec.)
- `medium` `patch` **`--target ""` silently scoped the local engine/env checks to the CWD.** `argparse`'s `required=True` only requires the flag be present, not that its value be non-blank, so `--target ""` parsed fine with `args.target == ""`. `Path("").is_dir()` resolves to `PosixPath('.')` and returns `True`, so a blank target unintentionally triggered `warden_source.gather()`/`env_hygiene.gather()` against wherever `doctor` happened to be invoked from, rather than refusing like any other non-directory target. Fixed: `_run_diagnose` now treats a blank/whitespace-only `--target` the same as a non-directory target (`target_path = Path(args.target) if args.target.strip() else None`). New test: `test_diagnose_blank_target_does_not_scope_engine_env_checks_to_cwd`.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **336 passed** (full suite).

**Follow-up review recommendation (updated): false** -- both findings are narrow, each covered by a dedicated regression test.

</intent-contract>
