---
title: '46.6: An interactive session whose layers lapse gets a persistence advisory'
type: 'feature'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: 'ef925d35dbd188c4526075a994d8841a7afb6544'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As an operator on the interactive path, I want a persistence advisory when a session's declared layers would lapse, So that silent savings do not silently stop.

**Approach:** the session-path advisory surface (journal + session-close output).

Ledger key: `46-6-an-interactive-session-whose-layers-lapse-gets-a-persistence-advisory`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-46.4.

### Living CAP citations

- `spec-pyforge-marshal` CAP-193 (fold remint of `spec-marshal-token-economy` CAP-20; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-193` ← `spec-marshal-token-economy CAP-20`.

## Acceptance Criteria

- Given an interactive session whose `[context]` layers were active When the session ends or the layers lapse Then the journal carries a persistence advisory naming what lapsed

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| an interactive session whose `[context]` layers were active | the session ends or the layers lapse | the journal carries a persistence advisory naming what lapsed | named finding / refuse |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` -- primary implementation surface. Add a fourth `advisory` action to `add_context_subparser` alongside `refresh`/`retrieve`/`bundle`; already imports `resolve_context_layers` (from `.seed`), `Finding`/`Severity`/`build_envelope` (`..core.model`), `ScribeCli` (`..adapters.scribe_cli`), `derived`/`planning` (`..core.derived_context`/`..core.planning_graph`), `_resolve_project_slug`, `repo_root`. `run_context_refresh` (this file) is the idiom to mirror: resolve layers, branch on `enabled`, build a `data` dict, emit via `_emit`-style `build_envelope(command=..., ...)`.
- `seed/detect/kit.py::kit_checks(repo_root, context_layers, *, probe=probe_instrument, process=None, fs=None) -> tuple[KitCheck, ...]` -- reuse directly for the 3 kit-provisioned layers (`output`, `wire`, `structure-graph`). Read `KitCheck.status` (`KitStatus.OK`/`OFF`/`MISSING`/`STALE`/`UNAVAILABLE`) directly -- do **not** call `kit_findings()`: it returns `seed.detect.findings.Finding`, a structurally separate dataclass (own `FindingType`/`remedy` vocabulary, never registered in `core/findings.py`'s `REGISTERED_CODES`) from `core.model.Finding`. Precedent call site: `seed/verbs/check.py:488` (`kit_checks(repo_root, context_layers, process=process) if context_layers is not None else ()`).
- `core/policy.py::resolve_context_layers` (via `cli/seed.py::resolve_context_layers`, already imported into `cli/context.py`) -- the one composition site for all `CONTEXT_LAYER_NAMES = ("wire", "output", "structure-graph", "derived-context", "planning-graph")`; each resolves to `{"enabled": bool | "auto" (wire only), "aggressiveness": str}`.
- `core/derived_context.py::DERIVED_CONTEXT_LAYER`, `layer_enabled`; `core/planning_graph.py::PLANNING_GRAPH_LAYER`, `layer_enabled` -- reuse for the remaining 2 layers. Combine with `adapters/scribe_cli.py::ScribeCli.resolve_binary(repo_root=None, *, fallback_bin_dirs=...) -> str | None`: an enabled layer whose `resolve_binary(root)` returns `None` is lapsed (mirrors `ScribeCli.refresh`'s own "did not resolve on PATH ... layer is off" degrade message).
- `core/journal.py::mint_run_id(slug, utc_compact, random_token)`, `JournalEntryId(writer_id, counter)`, `build_entry(*, id, ts, run_id, kind, phase, payload, story=None, intent_id=None)`, `Phase.OBSERVATION`, `prepare_for_write(entry) -> PreparedWrite` -- the journal-write composition. `Phase.OBSERVATION` needs no paired `intent_id` (`JournalEntry.__post_init__`: `intent_id` required iff `phase is Phase.OUTCOME`, forbidden otherwise) -- one complete, standalone entry, no run-lifecycle bookkeeping needed. Precedent composition: `cli/dispatch.py:2215-2234` (`_writer_id()` → `mint_run_id` → `fs.ensure_dir(run_dir.parent)` → `fs.create_dir_exclusive(run_dir)` → `build_entry`) and `cli/dispatch.py:305-309` (`_append_entry`: `prepare_for_write(entry)` → `fs.append_line(run_dir / _JOURNAL_FILENAME, prepared.line, fsync=fsync)`; `_JOURNAL_FILENAME = "journal.jsonl"`, `cli/dispatch.py:179`).
- `ports/fs.py::FsPort` (`create_dir_exclusive`, `ensure_dir`, `append_line`) and `adapters/fs_local.py::LocalFs`/`FsError` -- write seam, same `fs = fs if fs is not None else LocalFs()` DI idiom used throughout `cli/dispatch.py`.
- `core/dispatch.py::dispatch_runs_dir`/`dispatch_run_dir` (`_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/<run_id>/`) -- read-only precedent for the run-directory shape, **not** reused directly. A new, sibling Tier-3 dirname, `session-advisories` (mirroring `_DISPATCH_RUNS_DIRNAME`), keeps the advisory's synthetic run invisible to every existing reader that globs `dispatch-runs/*/journal.jsonl` specifically -- confirmed by direct read: `core/layer_savings_sources.py:196,326` (`runs_dir.glob("*/journal.jsonl")` where `runs_dir` is hardcoded to `.../dispatch-runs`) and `cli/status.py`'s `dispatch_core.dispatch_runs_dir`/`latest_dispatch_run_dir` call sites both scope to that one dirname; no reader globs a wider `implementation-artifacts/*`. Both directories are Tier-3 (gitignored) per `AGENTS.md`.
- `core/findings.py::REGISTERED_CODES` -- register one new WARN code (`MRS-CTX-009`), following the file's dated-comment-block convention (neighbors: `MRS-CTX-001..008`, `MRS-PLAN-001`, `MRS-IDXF-001..004`).
- Read, confirmed **out of scope**: `cli/check.py` (`marshal check` wraps `scripts/detectors.py` -- a different Surface); `scripts/index_freshness_check.py` (repo-root script; scans only `~/.bmad-loops/*` loop homes, never the live interactive session's own checkout -- this story's actual gap); `seed/detect/findings.py`/`kit_findings()` (separate Finding vocabulary, not converted).

## Tasks & Acceptance

**Execution:**
- `core/findings.py` -- add `MRS-CTX-009` to `REGISTERED_CODES` with a dated Story 46.6 comment block (WARN: a declared-active `[context]` layer's instrument/binary no longer resolves at session-close) -- so `Finding(code="MRS-CTX-009", ...)` does not raise `UnregisteredFindingCodeError`.
- `cli/context.py` -- add `advisory` to `add_context_subparser` (`--project`, `--root`, `--format`; no `--epic` -- the advisory scans layer state, not one epic's declarations). Add `run_context_advisory(args, *, scribe=None, process=None, fs=None) -> int`. Add `_lapsed_layer_findings(root, layers, *, scribe, process) -> list[Finding]`: run `kit_checks(root, layers, process=process)` for `output`/`wire`/`structure-graph`, emit `MRS-CTX-009` for any `MISSING`/`STALE`/`UNAVAILABLE` status; check `derived.layer_enabled`/`planning.layer_enabled` for the other two, emit `MRS-CTX-009` when enabled and `scribe.resolve_binary(root)` is `None`. Add `_write_advisory_journal_entry(root, slug, findings, *, fs) -> str | None`: when `findings` is empty, do nothing and return `None` (matches the module's existing "off/healthy -> no artifact" convention); otherwise `_writer_id()` (`f"context-advisory-{os.getpid()}"`) → `mint_run_id(slug, _format_utc_compact(now), _random_token())` → `fs.ensure_dir(run_dir.parent)` → `fs.create_dir_exclusive(run_dir)` → `build_entry(id=JournalEntryId(writer_id, 0), ts=..., run_id=run_id, kind="context-advisory", phase=Phase.OBSERVATION, payload={"lapsed": [f.to_json_dict() for f in findings]})` → `prepare_for_write` → `fs.append_line(run_dir / "journal.jsonl", prepared.line, fsync=True)`; return the journal path as `str`. Wire both into `run_context_advisory`, emitting through the same `build_envelope(command="context advisory", verdict=compute_verdict(findings), data=data, findings=tuple(findings))` pattern the other three actions use.
- `tests/unit/test_cli_context.py` -- add unit tests for `run_context_advisory`: all layers declared off (no findings, no journal write, `data["journal"] is None`); one kit layer `MISSING`/`STALE`/`UNAVAILABLE` in turn (one `MRS-CTX-009` finding, journal written); `derived-context`/`planning-graph` enabled with a fake `ScribeCli.resolve_binary` returning `None` (finding + journal write); everything `OK`/`OFF` (no findings, no write). Assert the written journal is a single valid `JournalEntry` line under `implementation-artifacts/session-advisories/<run_id>/journal.jsonl` (`phase: "observation"`, no `intent_id` key) and that it is NOT matched by `runs_dir.glob("*/journal.jsonl")` rooted at `implementation-artifacts/dispatch-runs`.

**Acceptance Criteria:**
- Given an interactive session whose `[context]` layers were declared active, when `marshal context advisory` runs and one or more of those layers is no longer resolvable (a kit item `MISSING`/`STALE`/`UNAVAILABLE`, or an enabled `derived-context`/`planning-graph` layer whose `scribe` binary does not resolve), then the command emits one `MRS-CTX-009` WARN finding per lapsed layer AND appends exactly one `Phase.OBSERVATION` journal entry (`kind="context-advisory"`) naming every lapsed layer in its payload, under a fresh, isolated run directory.
- Given every declared-active layer is still resolvable, or every layer is declared off, when `marshal context advisory` runs, then it emits no findings and writes no journal entry.
- Given the advisory journal entry was written, when `core/layer_savings_sources.py`'s rollups or `cli/status.py`'s run-facts readers run (both scoped to `implementation-artifacts/dispatch-runs/`), then they are unaffected -- the advisory lands under the sibling `implementation-artifacts/session-advisories/` directory, which none of those readers glob.

## Spec Change Log

## Review Triage Log

## Design Notes

"The journal" is `core/journal.py`'s real `JournalEntry`/`journal.jsonl` mechanism -- confirmed by `core/layer_savings_sources.py`'s own docstring, which reads "the SAME per-run `journal.jsonl`" `cli/dispatch.py`/`supervisor/__main__.py` write -- never a new bespoke file. AD-25's optional-`run_id` `sessions/` namespace stays unimplemented and is not needed here: each `marshal context advisory` invocation mints its own fresh, self-contained `run_id` via the already-shipped `mint_run_id()` (Story 3.1) and writes ONE `Phase.OBSERVATION` entry, which needs no paired `INTENT`/`OUTCOME`.

One entry per invocation naming every lapsed layer, not one entry per layer: the AC's singular "a persistence advisory naming what lapsed" reads as one advisory, and it matches `layer_savings_sources.py`'s own per-run single-payload accumulation idiom.

`kit_checks()`, not `kit_findings()`, is the reuse point for the 3 kit-covered layers: `kit_findings()`'s `seed.detect.findings.Finding` is a structurally separate dataclass (its own leaf-module docstring: "Nothing in this module imports from or references... any other `pyforge.marshal.*` module") from `core.model.Finding`, with a disjoint `FindingType`/`remedy` vocabulary never registered in `core/findings.py`. `KitCheck.status` is plain data, read directly to build native `core.model.Finding` instances in this module's own idiom -- exactly as `run_context_refresh` already does for its own degradation codes.

A dedicated `session-advisories/` Tier-3 dirname (not `dispatch-runs/`) was chosen, rather than auditing every present and future `dispatch-runs/` reader for tolerance of a run with no `dispatch-launch` entry, because a provably-disjoint glob target eliminates the risk by construction instead of by exhaustive case analysis.

## Source

Contract recovered from `epics.md` Story 46.6 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
