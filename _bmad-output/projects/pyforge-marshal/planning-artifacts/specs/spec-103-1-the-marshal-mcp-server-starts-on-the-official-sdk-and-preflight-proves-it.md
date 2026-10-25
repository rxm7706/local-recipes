---
title: "103.1: The marshal-mcp server starts on the official SDK, and preflight proves it"
type: 'fix'
created: '2026-10-25'
status: 'in-review'
baseline_revision: d287eceb0aad21de55ab9579ce565b1e00c25abd
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/server.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/tools.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/egress.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_ad34_egress_registry_completeness.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py
  - src/shared/packages/pyforge-marshal/pyproject.toml
  - src/shared/packages/pyforge-marshal/pixi.toml
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py
  - src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py
  - scripts/docs_station_cli.py
  - docs/reference/library-llms-full.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the pyforge-marshal policy registers a `marshal` MCP server that cannot start, and `marshal preflight`
reports it healthy. Line numbers are at `028cbceaac`.

- **The registration.** `marshal-policy.toml:899` declares `[mcp_servers.marshal] command = "marshal-mcp"` (Story
  18.1). `marshal init` renders it into the loop home's `.mcp.json` (`cli/init.py::_render_mcp_json`, `:468`); the file
  in `~/.bmad-loops/pyforge-marshal/` was written on 2026-10-04. No other station's policy declares a server.
- **The server cannot start.** `mcp/server.py:15` imports `FastMCP` from the third-party `fastmcp` package inside
  `build_server`, and `main` (`:66`) calls `build_server().run()` without reading its arguments. `fastmcp` is installed
  only in the `local-recipes` env, which has no `marshal-mcp` script. From `pyforge-guild`, `marshal-mcp` exits 1 with
  `ModuleNotFoundError: No module named 'fastmcp'`. pyforge-marshal declares no MCP dependency at all, in
  `pyproject.toml` or in its package `pixi.toml`.
- **Everything else moved.** mcp 2.x renamed the SDK's `FastMCP` class to `MCPServer` (`mcp.server.mcpserver`). Atlas
  (`pyforge/atlas/mcp/server.py:43`), the conda-forge server (`.claude/tools/conda_forge_server.py:17`) and marshal's
  own HTTP face (`django_marshal_portal/mcp_asgi.py:159`) all use it. `pyforge-guild` resolves mcp 2.2.0 through
  pyforge-doctor's run-dependencies; the `pyforge-marshal` test env has no `mcp`.
- **Nothing catches it.** No test builds the server: `tests/unit/test_mcp_tools.py:161` only proves the module imports
  without `fastmcp`. `_probe_mcp_servers` (`cli/init.py:505`, called from `run_preflight` at `:1719`) marks a bare
  command resolvable through `harness.binary_present` (`:587`), a `PATH` lookup, so `MRS-PREFLIGHT-012` stays green.
  Open `DW-FU-18-2` names the same gap from the coverage side (a file counts as covered, not a registered tool).
- **Proved feasible on 2026-10-25 (scratch, not committed).** The same `build_server` body on `MCPServer` answered
  `initialize` (protocol `2025-06-18`) and `tools/list` in 0.47 s from `pyforge-guild`. A plain JSON-RPC stdio probe
  (`initialize`, then `tools/list`) read exit 1 and the import error from today's server.
- **A side effect to handle.** `scripts/docs_station_cli.py:138` runs `marshal-mcp --help` with the caller's stdin
  and a 30 s timeout. Once the server can start, an entry point that ignores its arguments would serve stdio there: an
  empty capture, or a 30 s hang. `docs/reference/station-cheat-sheet.md:138-140` shows the current "not resolvable"
  note.

**Approach:**
- **The server.** `build_server` imports `MCPServer` from `mcp.server.mcpserver` lazily, inside the function, so
  `pyforge.marshal.mcp` still imports without the SDK. The eight registered tools (`list_marshal_tools`,
  `marshal_status`, `marshal_check`, `marshal_homes`, `marshal_preflight`, `marshal_upstream`, `marshal_refresh`,
  `marshal_watch`) keep their names, arguments, docstrings and delegation to `tools.py`. The server name stays
  `pyforge-marshal`. No `fastmcp` import remains anywhere in the package. Atlas's `sys.path` shadow guard
  (`_official_mcp_server_class`) is copied only if a marshal test path shadows the SDK's `mcp`; none does today
  (there is no `tests/mcp/`).
- **The entry point.** `main(argv: list[str] | None = None) -> int` parses its arguments with `argparse` before it
  builds the server. `--help` prints usage (what the server is, that it speaks MCP over stdio, the policy key that
  registers it) and exits 0. `--version` prints the installed `pyforge-marshal` version and exits 0. Any other argument
  exits 2 (argparse's usage error). None of the three reads stdin or builds the server. With no argument it serves
  stdio as today. `__main__.py` keeps calling `main()`.
- **The dependency.** `mcp>=2.2` joins `pyproject.toml`'s `dependencies` and the package `pixi.toml`'s
  `[package.run-dependencies]` (pyforge-doctor's pattern). Because pixi does not rehash a path dependency's own
  manifests, `mcp = ">=2.2.0"` also joins the root `pixi.toml`'s `[feature.pyforge-marshal.dependencies]` (the
  bmad-loop precedent there) so the `pyforge-marshal` test env resolves it. `pixi.lock` is refreshed and
  `environment.yaml` regenerated in the same PR (AGENTS.md § Policy). No new package enters `pyforge-guild`, which
  already carries mcp 2.2.0.
- **The probe.** A new port, `ports/mcp_probe.py` (a `Protocol` and frozen value types only), and a new adapter,
  `adapters/mcp_stdio_probe.py`, start one declared server and complete a handshake:
  - the command, args and env come from the home's own rendered `.mcp.json` (what an agent would launch, which a hand
    edit may have made differ from policy), the env merged over the caller's environment as Claude Code does; the
    working directory is the home;
  - the child starts in its own session (`start_new_session=True`), so a server launched through a wrapper (`npx`,
    `uvx`, `pixi run`, a shell script) is stopped together with every process it spawned;
  - it writes newline-delimited JSON-RPC to the child's stdin in the MCP lifecycle's order: `initialize` (a fixed
    `protocolVersion`, empty `capabilities`, `clientInfo.name` `marshal-preflight`); once the `initialize` result
    arrives, `notifications/initialized` and then `tools/list`;
  - it reads stderr concurrently, so a server that writes a lot to stderr cannot block on a full pipe, and keeps the
    last 2 KiB;
  - it waits at most a timeout (`MCP_PROBE_TIMEOUT_S`, 15 s) for both replies, then always signals the child's process
    group (terminate, then kill after a short grace) and reaps the child, whatever happened;
  - it returns a frozen result: `started` / `exited` (with the exit code) / `timed-out` / `bad-reply` / `error-reply` /
    `spawn-failed`, the server name, the tool count and the stderr tail;
  - it imports no MCP SDK, so it judges any declared server the same way.
- **The port is not an egress port (AD-34).** `McpProbePort` passes argv and an environment to a child process, the
  carve-out AD-34's Rule makes for `ProcessPort` and `HarnessPort`, so it joins `core/egress.py`'s `EGRESS_PORTS` as
  `False` (`tests/meta/test_ad34_egress_registry_completeness.py` requires every port `Protocol` to be classified).
  The stderr tail is a child's raw text bound for a finding, which every `Envelope` consumer prints, so it passes
  through `core.egress.redact_raw_text` first.
- **The decision is pure.** `core/mcp_probe.py` maps a probe result to `(startable, findings)`. Only `started` with a
  `serverInfo` and a `tools` list is startable. Every other outcome is one `MRS-PREFLIGHT-012` (ERROR, the code's
  existing tier; `core/verdict.py:1026`) naming the server, the outcome and the redacted stderr tail. `core/findings.py`'s
  description of `MRS-PREFLIGHT-012` gains the fourth sub-case.
- **The wiring.** `run_preflight` gains an `mcp_probe` DI seam (Story 28.3's `kit_probe` pattern); production
  supplies the adapter. `_probe_mcp_servers` runs it only for a server whose command already resolved, so a command
  missing from `PATH` keeps today's message. Each `data.mcp_servers` entry gains `startable` and `tool_count` beside
  `name`, `command` and `resolvable`. A project with no declared server runs no probe. Story 6.9's existing preflight
  tests (`tests/unit/test_init.py:2780-2914`) inject the fake probe, so none of them starts a real binary.
- **The cheat sheet.** `pixi run -e pyforge-guild docs-station-cli` regenerates `docs/reference/station-cheat-sheet.md`,
  which then shows `marshal-mcp --help`'s usage. The page is doctor's (`spec-pyforge-doctor` CAP-84), so its memlog
  carries the surface reconcile and its scoped stamp.
- **Two texts that name today's failure.** `scripts/docs_station_cli.py`'s `capture_help` docstring (`:113-116`)
  gives `marshal-mcp` without `fastmcp` as its example of a crashing script; it gets a neutral example. The
  `pyforge-marshal` env row of `docs/reference/library-llms-full.md` (`:99`) and its `mcp` entry gain the new
  dependency, so `llms-full-check` stays green.
- **AD-3 is unchanged.** The new adapter sits under `adapters/`, which the AD-3 contract's `source_modules` leaves out
  on purpose (`tests/meta/test_ad3_ad4_import_linter.py:109-132` pins that set); it never references `bmad_loop`.
- **`type: fix`, no flag.** Story 18.1's server and Story 6.9's probe are meant to work; this restores both. Under
  `spec-feature-flag-governance` Q1 a fix carries no flag.

**Rejected:**
- **Adding `fastmcp` to `pyforge-guild`.** A new dependency tree the rest of the factory has moved off; operator
  ruling 2026-10-25.
- **Dropping `[mcp_servers.marshal]`.** Regresses FR-153 and FR-154; operator ruling 2026-10-25.
- **An import check instead of a handshake.** It proves one module imports, not that the declared command serves
  MCP, and it cannot judge another station's or an adopter's server.
- **Probing through the SDK's client.** It would tie preflight to one SDK major and to `pyforge-marshal`'s own
  dependency; the protocol's first two requests are a dozen lines of JSON.
- **A policy key for the timeout.** Marshal's policy vocabulary is closed (`schemas/policy.json`); one constant serves.
- **A new finding code.** `MRS-PREFLIGHT-012` already bundles "not satisfiably recorded" sub-cases (missing file,
  malformed file, unresolvable command); "cannot start" is the fourth.

Ledger key: `103-1-the-marshal-mcp-server-starts-on-the-official-sdk-and-preflight-proves-it`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-1** (loop homes and isolation, FR-5): a home is preflight-verified. This story makes
  the verification start the tool surface the home registers once its command resolves on `PATH`.
- **`spec-pyforge-marshal` CAP-21** (← `spec-agent-tool-surface` CAP-1, FR-153, one governed surface) and **CAP-22**
  (← `spec-agent-tool-surface` CAP-2, FR-154, the surface survives a clone): marshal's tools are reachable through the
  registered server. The PRD's § 16.7 headings still carry the pre-fold arrows `← CAP-111` / `← CAP-112`; the Spec's
  own ids are cited here. This story mints no CAP and changes no `SPEC.md` text.
- **AD-43:** the tool surface is policy-declared and home-rendered, and the user-scoped registry is never read or
  written; the probe reads only the home's rendered `.mcp.json`. **AD-4:** the decision is pure in `core/`; the
  process lives in an adapter. **AD-34:** the new port is classified non-egress, and the stderr tail is redacted.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-25 (marshal's own MCP server has never
  started) entry; the operator's ruling of 2026-10-25.

## Acceptance Criteria

- **AC1 — The server starts.** From `pyforge-guild`, `marshal-mcp` answers `initialize` with a `result` whose
  `serverInfo.name` is `pyforge-marshal`, and `tools/list` returns exactly the eight tools named above. An integration
  test drives the real console script through the new adapter and asserts both.
- **AC2 — The tools are registered, in process.** A unit test calls `build_server()` and lists its tools through the
  SDK; the set equals the eight names, and each delegates to its `tools.py` function (a monkeypatched `tools` function
  is what a call returns).
- **AC3 — No `fastmcp`.** No module under `src/pyforge/marshal/` imports `fastmcp` (a test walks the package's source
  with `ast`); `test_tools_import_without_fastmcp` is replaced by a test that `pyforge.marshal.mcp.server` imports with
  the `mcp` SDK blocked, and `build_server` then raises an `ImportError` naming `mcp`.
- **AC4 — `--help` and `--version`.** `marshal-mcp --help` and `marshal-mcp --version` exit 0 with stdin closed and
  with stdin left open, within 5 s, never building the server; `--help`'s output names MCP and stdio; `--version`'s
  is the installed version. An unknown argument exits 2.
- **AC5 — The probe's outcomes.** With the fake probe, `_probe_mcp_servers` reports: a started server as
  `startable: true` with its `tool_count` and no finding; an exited, timed-out, bad-reply, error-reply and
  spawn-failed server each as `startable: false` and one `MRS-PREFLIGHT-012` naming the server and the outcome, the
  stderr tail included when there is one. A command that does not resolve keeps today's message and runs no probe. A
  project with no declared server runs no probe.
- **AC6 — The adapter.** Against small scripted servers (a test fixture that answers, one that exits 1 after writing
  to stderr, one that never answers, one that prints a line that is not JSON, one that answers `initialize` with a
  JSON-RPC error, one that forks a grandchild and then never answers, one that writes 1 MiB to stderr before it
  answers), the adapter returns `started`, `exited`, `timed-out` (bounded by a short test timeout), `bad-reply`,
  `error-reply`, `timed-out` and `started`, and no process of the child's group is left running after any of them.
- **AC7 — Preflight end to end.** `marshal preflight pyforge-marshal --format json`, run against a home whose `.mcp.json`
  registers `marshal-mcp`, shows the server `startable: true` with `tool_count: 8` and no `MRS-PREFLIGHT-012`; the
  same run against today's `fastmcp`-importing server (a fixture standing in for it) shows `MRS-PREFLIGHT-012` with
  `ModuleNotFoundError` in its message.
- **AC8 — Mutation.** Each of these fails a named test: skipping the handshake call in `_probe_mcp_servers`; mapping
  `timed-out` to startable; dropping the child's termination in the adapter. Restore each.
- **AC9 — The cheat sheet.** `pixi run -e pyforge-guild docs-station-cli -- --check` exits 0, and the page shows
  `marshal-mcp --help`'s usage instead of the "not resolvable" note.
- **AC10 — The suites.** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci
  pyforge-deps-test` are green; the `pyforge-marshal` coverage gate holds. AC2, AC4, AC5 and AC6's tests live under
  `tests/unit`, which the coverage gate measures; AC4 also calls `main(argv)` in process.

## Boundaries & Constraints

**Always:**
- Stop every process the probe starts (the child's whole process group), on every path, and reap the child.
- Read the server's command, args and env from the home's own rendered `.mcp.json`.
- Keep the eight tools' names, arguments and answers exactly as they are.
- Reconcile every governed path on the memlogs of the Specs that govern it (`spec-pyforge-marshal`;
  `spec-pyforge-core`, which co-governs station `src/`; `spec-pyforge-doctor` for the cheat sheet and `scripts/docs_station_cli.py`), then stamp scoped
  (AGENTS.md pre-PR item 5).
- Regenerate `environment.yaml` in the PR that changes `pixi.toml` (AGENTS.md § Policy), and run every station suite
  (AGENTS.md pre-PR item 7).

**Ask first:**
- Raising or lowering the 15 s timeout, or making the probe a WARN instead of an ERROR.

**Never:**
- Never read or write `~/.claude.json` (AD-43).
- Never import the MCP SDK in the probe adapter or in `core/`.
- Never add `fastmcp` to any environment, a flag, a CAP, a new finding code or a policy key; never edit `SPEC.md`.
- Never change `marshal init`'s render of `.mcp.json` or its copy-when-absent rule.

**Residual risk:**
- A server that starts but fails on its first real tool call still passes; the probe lists tools, it does not call
  them.
- Preflight runs each declared server for up to 15 s; a station with many declared servers pays that per server.
- The probe sends one `protocolVersion`. A server that refuses every version but its own replies with an error and is
  reported as `error-reply`, which is the right verdict for an agent that sends the same.

## I/O & Edge-Case Matrix

| Declared server | Probe result | Preflight |
|---|---|---|
| none declared | not run | no `mcp_servers` entries, no finding |
| command not on `PATH` (bare name) | not run | `resolvable: false`, today's `MRS-PREFLIGHT-012` |
| command with a path separator | not run | `resolvable: false`, today's `MRS-PREFLIGHT-012` |
| answers `initialize` and `tools/list` | `started` | `startable: true`, `tool_count`, no finding |
| exits before replying (today's `marshal-mcp`) | `exited`, exit code, stderr tail | `startable: false`, `MRS-PREFLIGHT-012` |
| no reply within 15 s | `timed-out` | `startable: false`, `MRS-PREFLIGHT-012` |
| a line that is not JSON-RPC | `bad-reply` | `startable: false`, `MRS-PREFLIGHT-012` |
| a JSON-RPC error to `initialize` or `tools/list` | `error-reply` | `startable: false`, `MRS-PREFLIGHT-012` |
| the process cannot be spawned | `spawn-failed` | `startable: false`, `MRS-PREFLIGHT-012` |
| `.mcp.json` missing or malformed | not run | today's `MRS-PREFLIGHT-012` |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-1 (FR-5), CAP-21 (FR-153) and CAP-22 (FR-154). No CAP is
  minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 (marshal's own MCP server has never
  started) entry.
- Epic: Epic 103 (new), minted with this story, because Epics 6 and 18 are done. `epic-103` and
  `epic-103-retrospective` are minted with it.
- Ledger key: `103-1-the-marshal-mcp-server-starts-on-the-official-sdk-and-preflight-proves-it`.
- Deps: —.
- Deferred work: `DW-FU-18-2` stays open, a kinship only. This story proves marshal's registered tools (AC2) but does
  not change `mcp/coverage.py`, the entry's own location.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"`, added with this mint.
- Minted 2026-10-25 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1–AC8's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"check","version":"0"}}}' | timeout 20 pixi run --frozen -e pyforge-guild marshal-mcp` — expected: one JSON line whose `result.serverInfo.name` is `pyforge-marshal` (AC1).
- `pixi run --frozen -e pyforge-guild marshal-mcp --help </dev/null` — expected: exit 0, usage text (AC4).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run -e pyforge-guild docs-station-cli -- --check` — expected: exit 0 after the regeneration (AC9).
- `pixi run -e pyforge-steward pyforge steward estate reconcile` — expected: `environment.yaml` current with `pixi.toml`.
- `pixi run -e pyforge-guild llms-full-check` — expected: exit 0.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (a `pixi.toml` change fires every station suite).
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- The three mutations of AC8 — expected: each fails its named test. Restore each.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (marshal's own MCP server has never started) at the
  operator's ruling "Go with the migration: move marshal-mcp to the official SDK MCPServer, add a real --help, and make
  preflight run a startup handshake. Plan it as one marshal story through the full Dream-to-code chain." `type: fix`,
  no flag, no CAP.
- 2026-10-25: chain review round 1 (independent reviewer, PASS, 0 blockers). Applied: AD-34 classification and stderr
  redaction; the MCP lifecycle order (wait for the `initialize` result); process-group stop, concurrent stderr and
  two more AC6 fixtures; `--format json` in AC7; the AD-3 step dropped (its meta-test pins the set); `DW-FU-18-2` kept
  as a kinship; cwd = the home; the existing preflight tests inject the fake probe; unit-suite placement for the
  coverage gate; `scripts/docs_station_cli.py` and `docs/reference/library-llms-full.md` joined the surface.

## Review Triage Log

- **Round 1, 2026-10-25 (chain review of `863ee4395c`, independent reviewer): PASS, 0 blockers, 7 should-fix, 8 nits;
  all applied.**
  - should-fix: the AD-3 `source_modules` step would red `test_ad3_ad4_import_linter.py:109-132` — dropped.
  - should-fix: a new port `Protocol` needs an AD-34 `EGRESS_PORTS` entry — added (non-egress, process-spawn
    carve-out), stderr tail redacted.
  - should-fix: AC7 used `--json`; preflight takes `--format json` (`cli/init.py:1251`) — fixed.
  - should-fix: the handshake was pipelined; `notifications/initialized` now waits for the `initialize` result.
  - should-fix: only the direct child was stopped — process group, concurrent stderr, grandchild and heavy-stderr
    fixtures added.
  - should-fix: `DW-FU-18-2` was claimed half-closed outside the surface — kept as a kinship.
  - should-fix: the spine read AD-43 as reinterpreted — reworded as met more strongly, not amended.
  - nits: memlog design aligned (rendered `.mcp.json`, root `pixi.toml` pin) by a follow-up event; epics FR/AD and
    Surface aligned; "instead of" `PATH` wording fixed in the PRD and here; two stale texts joined the surface;
    Story 6.9's tests inject the fake probe; unit placement for coverage; cwd = the home.

## Auto Run Result

Status: in-review  
Implementation: marshal-mcp on official `MCPServer`, `mcp>=2.2` dependency, stdio preflight handshake via `McpProbePort` / `adapters/mcp_stdio_probe.py`, pure verdict in `core/mcp_probe.py`, wired through `_probe_mcp_servers` and `run_preflight(mcp_probe=…)`.  
Verification (2026-10-25): `pyforge-marshal-test` green (13286 passed); `pyforge-marshal-coverage-gate` green; `docs-station-cli --check` green; `llms-full-check` clean; `python scripts/spec_surface_reconcile.py` OK after memlog reconcile on `spec-pyforge-marshal`, `spec-pyforge-core`, `spec-pyforge-doctor`.  
Note: `pyforge-deps-test` reports a pre-existing `pyforge-atlas` import completeness failure unrelated to this diff.
