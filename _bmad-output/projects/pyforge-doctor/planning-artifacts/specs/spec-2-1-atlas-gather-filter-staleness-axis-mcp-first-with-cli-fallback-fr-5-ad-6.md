---
title: 'Atlas gather filter — staleness axis, MCP-first with CLI fallback'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py',
  '{project-root}/src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py',
  '{project-root}/.claude/tools/conda_forge_server.py',
  '{project-root}/.claude/scripts/conda-forge-expert/staleness_report.py',
  '{project-root}/pixi.toml',
]
warnings: []
baseline_revision: '27ccab3ab7f505c1b79ac645e220c6043118b067'
---

<intent-contract>

## Intent

**Problem:** `doctor monitor --fleet --watch staleness` (FR-5, AD-6) does not exist yet. Doctor needs one Watch axis working end-to-end on the MCP-first/CLI-fallback seam AD-5/AD-6 declare but leave unimplemented — the architecture spine's own "MCP client wiring detail... deferred to epics/stories" note names this story's job explicitly.

**Approach:** `doctor.sources.atlas.gather(axis, target=None)` for `axis="staleness"` calls cf_atlas's `staleness_report` MCP tool when reachable, normalizing its JSON into `Finding(source=Source.STALENESS_REPORT, ...)` tuples; when unreachable it falls back through `doctor.cli_bridge` (AD-5's sole subprocess site) to the same underlying `.claude/scripts/conda-forge-expert/staleness_report.py --json` script the MCP tool itself wraps (confirmed identical data source: `conda_forge_server.py::staleness_report` is a thin `_run_script(ATLAS_STALENESS_SCRIPT, args)` shim over that exact script) — both paths normalize to the *same* `Finding` shape (AD-6's "never diverge" rule).

The MCP path mirrors `pyforge-herald`'s proven `mcp_transport.py` pattern (Story 1.2 there): a lazy `mcp` SDK import inside an async helper, one `asyncio.run()`-scoped session per call, injectable `caller`/session-factory seam for tests. It differs in transport: Herald talks to a *remote* streamable-HTTP endpoint; this story talks to the *local* FastMCP server at `.claude/tools/conda_forge_server.py` over `mcp.client.stdio.stdio_client` (spawn `python3 .claude/tools/conda_forge_server.py` as the MCP server subprocess, per the SDK's own stdio transport contract). "An MCP client is available in-process" (the AC's own wording) is operationalized as "the stdio session establishes and `initialize()` succeeds" — attempted every call, not detected ambiently; a connection/import/protocol failure at any stage is "no MCP client available," falling through to CLI.

## Boundaries & Constraints

**Always:**
- `doctor.sources.atlas` is the sole module permitted to import the `mcp` SDK (mirrors `sources/warden.py`'s sole-import-site pattern from Story 1.2) — proven by a new AST meta-test mirroring `test_sources_warden_no_subprocess.py`'s shape.
- `doctor.cli_bridge` (NEW) is the *only* module in `pyforge-doctor` permitted to call `subprocess`/`os.system`/`os.spawn*` (AD-5) — extend Story 1.2's existing subprocess-scan meta-test machinery (currently scoped to prove `sources/warden.py` has *zero* subprocess calls) to also assert `cli_bridge.py` is the *sole* site where a real subprocess call is permitted anywhere else in the package.
- `cli_bridge.run_cli_json(script_path, args, *, timeout)` is bounded-timeout, typed-failure, argv-as-a-list (never `shell=True`), and strips/ignores color via `NO_COLOR=1` in the subprocess environment — mirrors AD-5's own wording exactly.
- Both the MCP path and the CLI-fallback path normalize `staleness_report`'s JSON (list of feedstock objects: at minimum `name`/`feedstock` identifier + a staleness/age signal — read the live script's actual `--json` output shape before writing the normalizer, do not assume a field name) into `Finding(source=Source.STALENESS_REPORT, check=<feedstock name>, status=..., message=..., evidence={...raw fields...})` — one `Finding` per feedstock row, never one aggregate `Finding` for the whole report (mirrors `sources/warden.py`'s "never re-aggregated" rule).
- `gather()` never raises: MCP failure falls back to CLI; CLI failure (script missing, non-zero exit, timeout, unparseable JSON) returns exactly one `Finding(status=FAIL, check="doctor.sources.atlas", source=Source.STALENESS_REPORT, ...)` naming the failure, mirroring `sources/warden.py`'s degrade-to-Finding contract.
- New meta-test `tests/meta/test_atlas_sole_mcp_import.py` (AST-scan, non-vacuous synthetic-violation self-test, mirrors `test_sources_warden_no_subprocess.py`'s idiom): only `sources/atlas.py` may import `mcp`/`mcp.*`.
- New meta-test `tests/meta/test_cli_bridge_sole_subprocess.py` (AST-scan, non-vacuous synthetic-violation self-test): only `cli_bridge.py` may import/call `subprocess`/`os.system`/`os.spawn*`/`os.popen` — mirror the closed-surface + relative-import-resolution hardening already proven necessary in `test_sources_warden_no_subprocess.py`'s three review passes (resolve relative imports, catch `from os import system`, catch os-aliasing) rather than re-discovering those gaps from scratch.
- `gather(axis, target=None)` validates `axis` against a small closed set (`{"staleness"}` this story — `cve`/`abandonment` are Story 2.2's job); an unrecognized axis raises `ValueError` at the call boundary (a programmer error, not a runtime degrade case) rather than silently returning nothing.
- `target` (an optional maintainer/feedstock scope) threads to both `staleness_report`'s MCP `maintainer` argument and the CLI's `--maintainer` flag identically.

**Never:**
- Never let `doctor.sources.atlas` call `subprocess` directly — CLI fallback goes through `cli_bridge`, no exceptions.
- Never let the MCP path and the CLI path diverge in `Finding` shape for equivalent underlying data — same field mapping, same `Source` tag, same `check`-naming convention.
- Never wire `doctor monitor` CLI dispatch, `--watch` flag parsing, or the `cve`/`abandonment` axes — that's Stories 2.2/2.3.
- Never persist a long-lived MCP session across calls — one `asyncio.run()`-scoped stdio session per `gather()` invocation (mirrors Herald's own documented "no session continuity needed" reasoning; do not add background-event-loop machinery for this story).
- Never assume the MCP tool's JSON shape without reading `conda_forge_server.py::staleness_report`'s real return value (`json.dumps(_run_script(...), indent=2)`) and the underlying `staleness_report.py --json` script's actual output structure first — both must be inspected live before writing the normalizer.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MCP stdio session establishes, tool call succeeds | Normal local dev/agent environment | `Finding` per feedstock row, `source=Source.STALENESS_REPORT` | No error |
| MCP stdio session fails to establish (server script missing/import error/timeout) | e.g. `.claude/tools/conda_forge_server.py` unreachable | Falls back to `cli_bridge` transparently, same `Finding` shape | Logged as fallback, not surfaced as a Finding-level failure unless CLI also fails |
| MCP unavailable, CLI fallback succeeds | No MCP, script runs fine | Identical `Finding` set to the MCP-success case for the same data | No error |
| Both MCP and CLI fail | Script missing/non-zero exit/timeout | Exactly one `Finding(status=FAIL, source=Source.STALENESS_REPORT)` naming the failure | Caught inside `gather()`, never propagates |
| CLI subprocess produces unparseable JSON | Corrupted/truncated output | One FAIL `Finding`, never a raw `JSONDecodeError` escaping | Caught, degraded |
| `target="somemaintainer"` scoping | Both paths | Both MCP `maintainer=` arg and CLI `--maintainer` flag receive the same value | No error |
| Unrecognized `axis` | `gather("bogus")` | `ValueError` at the call boundary | Raised, not swallowed (programmer error) |
| Equivalence check | Same underlying data, both paths forced | MCP-path and CLI-path `Finding` sets are field-for-field equal (order may differ; assert as a set/sorted comparison) | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py` — NEW. `gather(axis: str, *, target: str | None = None) -> tuple[Finding, ...]`. Sole `mcp` import site.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py` — NEW. `run_cli_json(script_path: Path, args: list[str], *, timeout: float) -> Any`. Sole subprocess site (AD-5).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` — EDIT (additive only, if `Source.STALENESS_REPORT` doesn't already exist — check first, Story 1.1/1.2 may have pre-declared the full `Source` enum).
- `src/shared/packages/pyforge-doctor/tests/meta/test_atlas_sole_mcp_import.py` — NEW.
- `src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py` — NEW.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas.py` — NEW. Full I/O matrix, MCP path faked via an injectable session/caller seam (mirror Herald's `caller: ToolCaller | None` constructor pattern — never spawn a real subprocess or hit a real MCP session in the unit suite), CLI path faked via a fake/injectable `cli_bridge` call.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py` — NEW. Timeout, non-zero exit, unparseable JSON, argv-as-list (no `shell=True`) proof.
- `.claude/tools/conda_forge_server.py` lines 1482-1511 (`staleness_report` MCP tool) — read before writing the normalizer; confirms the MCP tool is a thin wrapper over the same script.
- `.claude/scripts/conda-forge-expert/staleness_report.py` — read its `--json` output shape live; do not assume field names.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py` — the stdio-swap-for-streamable-HTTP precedent: lazy `mcp` import inside an async helper, one-session-per-call, `ExceptionGroup` flattening (`_flatten`/`_describe`), injectable caller seam. Reuse the *pattern*, not the code (Herald's is HTTP+OAuth-specific; this story's is stdio+no-auth, since the local FastMCP server has no credential layer).
- `pixi.toml` `[feature.pyforge-doctor.dependencies]` (~line 1506) — add `mcp = ">=2.0.0"` (mirror `[feature.pyforge-herald.dependencies]`'s identical pin).

## Design Notes

**Why stdio, not streamable-HTTP:** `.claude/tools/conda_forge_server.py` is a local FastMCP server started by Claude Code at session boot over stdio (per this repo's own CLAUDE.md) — it has no HTTP endpoint. The MCP SDK's `mcp.client.stdio.stdio_client(StdioServerParameters(command=sys.executable, args=[str(server_script_path)]))` is the standard way to talk to a local stdio MCP server as an independent client, distinct from the Claude-Code-hosted session Doctor's own process cannot reach into. This does mean `stdio_client` spawns the server script as its own child process under the hood (the SDK's internal implementation) — this is *not* a violation of AD-5's "cli_bridge is the sole subprocess site" rule, since AD-5/the meta-tests scan Doctor's *own* source for direct `subprocess`/`os.*` calls; a third-party SDK's internal transport mechanics are outside that scan's scope (exactly as `sources/warden.py` freely imports `pyforge.warden` without violating the "no subprocess in sources/warden.py" guard).

**Why "MCP available" is operationalized as "the session establishes," not ambiently detected:** there is no reliable process-level signal for "an MCP host happens to be present" from inside a plain Python library call — the AC's own framing ("an MCP client is available in-process" vs. "a bare terminal invocation") is best read as an outcome, not a precondition to branch on. Attempting the stdio connection every call and falling back on any failure gives the same observable behavior (works under an MCP-capable agent, works at a bare terminal) without needing an undetectable ambient signal.

**Resolve the `Source.STALENESS_REPORT` question before writing code:** Story 1.1 declared the `Source` enum's overall shape. Check `models.py` first — if `STALENESS_REPORT` isn't already a member, add it additively (Story 1.1's contract is frozen for *existing* members, per every prior spec's "Never modify doctor.models... this story is a producer only" boundary — adding a new enum member for a genuinely new producer is consistent with that, not a violation of it; if in doubt, treat this as a `Block If` and confirm against the live file).

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests -q` (substitute if the pixi task cannot run; note in Verification results if a non-frozen `pixi install -e pyforge-doctor` was needed first to pick up the new `mcp` dependency, mirroring Story 1.2's own precedent)
- A live equivalence smoke test (not part of the unit suite; run once, record the result in Verification): with the real `.claude/tools/conda_forge_server.py` reachable, compare `gather("staleness")`'s MCP-path output against the same call with the MCP path forced to fail (e.g. an unreachable server path) so CLI fallback runs — confirm field-for-field equivalence on real data, mirroring `sources/warden.py`'s own "live equivalence" verification step.

**Actual results (2026-08-07):**
- `pixi install -e pyforge-doctor` (non-frozen, to pick up the new `mcp` dependency) ran once to re-solve `pixi.lock`, then `--frozen` ran clean against the updated lock — mirrors Story 1.2's own precedent for the `pyforge-warden` path dependency.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- **240 passed** (238 baseline from the implementation pass + 2 new tests from the review patch pass below). One transient failure during the implementation pass (`test_check_speed_budget.py`, a pre-existing unrelated timing test under machine load) did not recur.
- `PYTHONPATH=src/shared/packages/pyforge-doctor/src python3 -m pytest src/shared/packages/pyforge-doctor/tests -q` -- 238 passed during the implementation pass (no contention that run); not independently re-run after the patch pass (redundant with the pixi run above).
- Live equivalence smoke test: run once during implementation against the real `.claude/tools/conda_forge_server.py` (symlinking the gitignored `cf_atlas.db` from the main checkout into the isolated review worktree, removed afterward, never committed). Confirmed live: the real FastMCP server spawns via stdio, `initialize()`/`call_tool()` succeed, and the CLI subprocess runs — MCP-path and forced-CLI-fallback-path results were structurally identical. The linked db snapshot had 0 matching `packages` rows at review time, so equivalence was proven on empty result sets, not non-trivial row content -- noted plainly, not re-attempted with richer data during the review pass.

## Review Triage Log

### 2026-08-07 -- Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 1, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` (Blind Hunter + Edge Case Hunter, converged independently) **The `timeout` argument was never applied to the MCP transport.** `gather()`'s `timeout` parameter only ever reached `_call_staleness_cli` (via `cli_bridge.run_cli_json`); `_call_staleness_mcp`/`_call_staleness_mcp_async` had no timeout wrapping at all around the `asyncio.run(...)` session (connect + `initialize()` + `call_tool()` + close). A stalled local `conda_forge_server.py` process (mid-import, deadlocked) would hang `gather()` indefinitely regardless of the `timeout` value passed in, directly contradicting `cli_bridge.py`'s own docstring framing of `timeout` as bounding "the call" and the module's own "MCP-first with CLI fallback" promise -- a hang on the primary path never reaches the fallback at all. Fixed: the whole MCP session lifecycle is now wrapped in `asyncio.wait_for(_run(), timeout=timeout)` inside `_call_staleness_mcp_async`, with `timeout` threaded through `_call_staleness_mcp` and `gather()`'s own call site. New test: `test_mcp_transport_is_bounded_by_the_timeout_argument` (exercises the real async transport via a monkeypatched hanging `stdio_client`, not the `mcp_caller` fake, which bypasses the async path entirely).
  - `medium` `patch` (Blind Hunter + Edge Case Hunter, converged independently) `gather()`'s MCP call site caught `except BaseException`, so a `KeyboardInterrupt` (e.g. Ctrl-C while the stdio session is in flight) or `SystemExit` was silently absorbed as "no MCP client available" and execution fell through into a fresh CLI subprocess spawn instead of propagating -- the interrupt was effectively eaten, requiring a second Ctrl-C during the CLI leg to actually stop the program. Fixed: narrowed to `except Exception`, which still satisfies "ANY MCP failure falls back to CLI" (every realistic MCP failure mode -- import, connection, protocol, timeout -- is an `Exception` subclass) while letting `BaseException`-only signals propagate normally. New test: `test_keyboard_interrupt_during_mcp_call_propagates_not_swallowed`.

**Follow-up review recommendation: false** -- both findings are isolated to the MCP transport's failure/timeout handling, each covered by a dedicated new test proving the fix; no new design questions opened. Both reviewers converged independently on the identical two findings.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `095a5087c5` (2026-08-07, "Merge pull request #290 from rxm7706/doctor/2-1-atlas-gather-filter-staleness-axis"). Ledger row `2-1-atlas-gather-filter-staleness-axis-mcp-first-with-cli-fallback-fr-5-ad-6: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `pixi.lock`, `pixi.toml`, `src/shared/packages/pyforge-doctor/pyproject.toml`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py`, `src/shared/packages/pyforge-doctor/tests/meta/test_atlas_sole_mcp_import.py`, `src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
