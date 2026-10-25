---
title: "103.1: The marshal-mcp server starts on the official SDK, and preflight proves it"
type: 'fix'
created: '2026-10-25'
status: 'done'
baseline_revision: e7d271fa2f1b43d644413c946478c65cdf3a0be1
review_loop_iteration: 5
followup_review_recommended: true
landing_review: required
difficulty: frontier
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
- 2026-10-25 (dev pass 4): the `${VAR}` residual risk is recorded in the entry below (outside the contract). `McpProbeResult` carries
  `reported_server_name`, `tool_names` and `detail` (the probe's own one-line reason, redacted with the stderr tail) so
  AC1 can assert the server's name and the eight tool names. `tests/scripts/test_docs_station_cli.py` joins the surface
  (doctor's, with the generator): `capture_help` builds the child's environment deterministically (the AC9 root cause).
  The pyforge-core `tests/meta/test_process_sole_ownership.py` file-level exemption for `adapters/mcp_stdio_probe.py`
  (landed in dev pass 2, reconciled on the `spec-pyforge-core` memlog) is recorded here: the probe needs interactive
  stdin/stdout/stderr pipes and a live `Popen` handle's process-group teardown, the same capability gap as
  `harness_bmadloop`'s stdio passthrough -- no `ProcessPort` method offers it.

- 2026-10-25 (dev pass 4, orchestrator verify step): the atlas package `pyproject.toml` / `pixi.toml` gained `numpy>=2.5.3`
  so `pyforge-deps-test`, a verify command of this story, is green (its red was atlas Story 37.7's undeclared module-level
  import, on `main` too); named on the `spec-pyforge-atlas` memlog. `scripts/.spec-surface-baseline.json` is left as it
  was at `e7d271fa2f`: a dispatch run never stamps its own baseline.

- 2026-10-25 (dev pass 4, orchestrator): a residual-risk bullet the implementer had written inside `<intent-contract>`
  (read-only in a build-auto run) is recorded here instead: the rendered entry's `env` values are passed as written; the
  `${VAR}` / `${VAR:-default}` expansion Claude Code applies to `.mcp.json` is not applied by the probe, so a server whose
  env needs it is judged with the literal text. No declared server in this repo uses the form. The adapter's module
  docstring says the same.

- 2026-10-25 (dev pass 4, review pass): residual risk recorded outside the contract — the process-group stop reaches
  every member of the child's group; a descendant that calls `setsid()` (a daemonizing server or wrapper) leaves the
  group and survives the probe. No declared server here does so; a stop that reaches it needs a cgroup or PID
  namespace, not a probe change (edge-case finding 8 of this pass).

## Review Triage Log

### 2026-10-25 — Review pass
- verdicts: 30 findings — high 0, medium 4, low 22, false 4, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind hunter 1 — the AC9 root-cause text (the `_TERMINAL_FORCING_VARS` comment in `scripts/docs_station_cli.py`, the orchestrator's pre-flight diagnosis entry, the `spec-pyforge-doctor` memlog event) read the 140-character `FORCE_COLOR=1` render as the pty's width — verified: with `FORCE_COLOR=1 NO_COLOR=1 COLUMNS=100`, `scribe --help` carries 154 ANSI escape sequences, visible width 100, raw width 140; rich reads `COLUMNS` in `Console.__init__` and `Console.size`, and only the forced dumb-terminal branch ignores it (80x25). Grouped with blind hunter 12 (same root cause). Fixed: the comment rewritten to the true mechanism (forced + dumb → 80 columns; forced otherwise → escape codes in the capture), the diagnosis entry corrected in place, a correction event appended to the doctor memlog.
  - `[low]` `[reject]` Blind hunter 2 — `capture_help` cannot tell an escape-code-polluted render from a real change — after the scrub no variable that forces rich's console reaches the child and its stdout is a pipe, so no path produces escape codes today; refusing on `\x1b` guards a state not shown reachable and adds a branch.
  - `[low]` `[patch]` Blind hunter 3 — `_close_pipes`' docstring said a pipe a reader still holds "closes at EOF"; nothing closes it explicitly — verified by reading `_ThreadChunks._pump` and `_stderr_reader_fd` (neither closes its fd); the file object closes when the `Popen` is collected at the end of `probe_server`, so the leak is bounded to the call. Fixed: the docstring states the real mechanism.
  - `[low]` `[patch]` Blind hunter 4 — `_read_reply` bounded the post-drain `_wait_exit` with a `remaining` computed before the wait slice and the drain, so the grace could run past `deadline` by a slice plus the drain — verified in the code. Fixed: `remaining` is recomputed immediately before that wait.
  - `[low]` `[patch]` Blind hunter 5 — `closed_stdin()` dropped `reported_server_name` and its detail string had no test — verified: the sibling `failed` path carried the name, the only aimed test accepted either outcome. Grouped with verification-gap 1 (same root cause: an untested write-failure branch). Fixed: `closed_stdin` carries `reported_server_name`; see verification-gap 1 for the tests.
  - `[low]` `[patch]` Blind hunter 6 — a new `# type: ignore[arg-type]` on `failed(**carried)` — verified in the diff. Fixed: a typed `reported_server_name: str | None = None` parameter, the ignore removed; mypy clean in `lint-types`.
  - `[low]` `[patch]` Blind hunter 7 — the kept team-memory note `story-103-1-build-auto-fix-pass-2026-10-25-mcp-stdio-probe-n.md` was a progress note of the same kind as the one this pass deleted and inaccurate ("redacts stderr concurrently"; redaction happens in `core.mcp_probe`) — verified by reading it. Fixed: the file and its `MEMORY.md` line deleted; the durable lesson captured with `scribe capture --type feedback` as `.claude/memory/feedback/a-generated-page-that-captures-a-cli-s-help-is-not-determini.md`.
  - `[low]` `[reject]` Blind hunter 8 — the implementer's dev-pass-4 entry says `pyforge-deps-test` reds on "a file this branch does not touch" while the Change Log records the atlas declaration — true, but the fix is an edit to this build's spec; the orchestrator corrects the stale bullet in this write-back because the log is this run's own output, not a reviewed artifact.
  - `[low]` `[reject]` Blind hunter 9 — the "no `pixi.lock` change" justification leaned on the no-rehash behaviour — a spec-text edit; and the premise is overtaken: an unfrozen `pixi run` in this pass re-locked, this pixi does rehash the path package, and the lock now carries the atlas `conda_source` hash and `numpy >=2.5.3` in its depends (recorded in the Auto Run Result).
  - `[false]` `[reject]` Blind hunter 10 — the `numpy>=2.5.3` floor is "whatever resolved today" with no stated rule — the AUD-ATLAS-010 block the line sits in states its rule: "Floors are pinned to the versions resolved in the working env"; the new line follows the block's own convention and comment style.
  - `[low]` `[reject]` Blind hunter 11 — Auto Run Result counts and lint claims do not reconcile (13350 vs 13351; "485 files formatted") — a spec edit; the Finalize below rewrites the Auto Run Result from the orchestrator's own runs on the final tree, `lint-types` included.
  - `[low]` `[patch]` Blind hunter 12 — the pre-flight entry's "`FORCE_COLOR=1` alone 140 (the pty's width)" line — grouped with blind hunter 1; fixed there.
  - `[low]` `[reject]` Blind hunter 13 — `.claude/skills/pyforge-marshal/SKILL.md` and `docs/reference/library-llms-full.md` do not mention `startable`, `marshal-mcp` or the fourth sub-case; `docs-gen-test` is missing from Verification — the SKILL.md is SKF-compiled from source (`skf-update-skill`), not hand-edited, so the fix is a recompile outside this diff; the intent names the documentation surfaces it wants (the cheat sheet, the generator docstring, the library row); the Verification addition is a spec edit. Unlikely to mislead in everyday use.
  - `[low]` `[patch]` Edge case 1 — `stderr_reader` was assigned before `start()`, so a failed `start()` made the `finally`'s `join` raise `RuntimeError: cannot join thread before it is started` — verified in the code; reachable only at the thread limit. Fixed: the thread is built into a local, started, then assigned.
  - `[low]` `[reject]` Edge case 2 — `buf` grows unbounded for a server that streams stdout without a newline for the whole timeout — real but needs a newline-less flood from a mis-declared command for up to 15 s, which no declared server does; a size cap is a guard for a state not shown reachable.
  - `[low]` `[reject]` Edge case 3 — a server-initiated request (`roots/list`) is dropped unanswered and a server blocking on it reads `timed-out` — the probe declares no client capabilities, so a compliant server sends no `roots/list`, sampling or elicitation request; a server that blocks on one is non-compliant, and `timed-out` is the right verdict for an agent that sends the same; answering adds a branch.
  - `[low]` `[patch]` Edge case 4 — a `bad-reply`/`error-reply` from a child that already exited reported `exit_code=None` though the code was known — verified: `failed` carried the code only for `exited`. Fixed: `exit_code = proc.returncode if proc.poll() is not None else None`.
  - `[low]` `[reject]` Edge case 5 — `selector.register(fd)` raising in `_SelectorChunks.__init__` would leak the selector — `register` on the fresh pipe fd `_pipe_fd` returns does not raise; a guard for a state not shown reachable.
  - `[medium]` `[patch]` Edge case 6 — `busy()` could read `True` right after the EOF chunk because the pump thread may still be alive for a moment, so the `_ThreadChunks` case of `test_chunk_sources_deliver_data_then_report_eof_without_waiting` could flake under load — verified by reading `_pump` (`put` then `return`) and the test. A flaky test reds CI at random. Fixed: `next_chunk` joins the pump thread for one `_POLL_SLICE_S` on EOF before returning `b""`.
  - `[false]` `[reject]` Edge case 7 — the spec names the deleted team-memory file, "orphaning" the trail — the round-5 entry asked for that file to be corrected or deleted and the dev-pass-4 entry records the deletion; a log that records a deletion by path is the record, not a dangling reference.
  - `[low]` `[reject]` Edge case 8 — a descendant that calls `setsid()` leaves the group and survives `killpg` — true by construction of process groups; the intent's mechanism is the process group, no process-group fix exists, and a cgroup or PID-namespace stop is not a patch. Recorded as a residual risk in the Spec Change Log (outside the contract).
  - `[medium]` `[patch]` Verification gap 1 — `_handshake.closed_stdin` never ran in any test (the `os.close(0)` fixture yields `timed-out` 12 of 12 runs and the test accepted either outcome) — pre-verified. Fixed: `test_handshake_closed_stdin_on_the_first_write` (parametrized: `TimeoutExpired` → `bad-reply` with the "closed its stdin" detail; exit code 7 → `exited`, `exit_code == 7`), `test_handshake_closed_stdin_after_initialize_carries_the_reported_server_name`, and the two-outcome real-process test renamed to `test_adapter_never_raises_and_stops_the_group_when_the_server_closes_stdin_and_lives`.
  - `[medium]` `[patch]` Verification gap 2 — the post-exit drain and re-parse in `_read_reply` were protected only by a race (`_drain_available`'s `buf.extend` and the post-drain return never executed) — pre-verified. Fixed: `_ScriptedChunks` and `test_read_reply_drains_and_parses_a_reply_that_arrives_as_the_exit_is_noticed` (`None`, then the `id=2` reply, then `b""`, with `_FakeProc(returncode=0)`).
  - `[medium]` `[patch]` Verification gap 3 — the `capture_help` env test set and asserted from `_TERMINAL_FORCING_VARS`, so a shrunken tuple stayed green — pre-verified. Fixed: the six variables set and asserted absent by literal name, plus `set(m._TERMINAL_FORCING_VARS) >= {the six}`; `docs-gen-test` 48 passed.
  - `[low]` `[reject]` Intent audit 1 — AC1's test lives under `tests/unit` in the `pyforge-marshal` env while the AC says "integration test" from `pyforge-guild` — the test drives the real console script through the adapter (not a fake); AC10 places the story's tests under `tests/unit` for the coverage gate; the `pyforge-guild` surface is the AC's own command, run by the orchestrator (`serverInfo.name` `pyforge-marshal`, protocol `2025-06-18`, exit 0).
  - `[low]` `[reject]` Intent audit 2 — AC7 is exercised through `run_preflight(fmt="json")` with the shared `FakeFs`/`FakeHarness` fixtures (the resolvable gate faked) rather than the CLI verb — the intent itself prescribes the shared fixtures ("Story 6.9's existing preflight tests inject the fake probe"); the adapter, the spawned `marshal-mcp` and the home directory are real, and argparse adds no logic on this path. Accepted shape since round 2.
  - `[false]` `[reject]` Intent audit 3 — AC9's `--check` exit code is a prose claim, not a test — AC9 names a command and its exit code; the orchestrator ran it (exit 0 from a plain shell, exit 0 under `FORCE_COLOR=1 TERM=dumb`) and `docs-currency` runs the same check in `detectors-ci`.
  - `[low]` `[reject]` Intent audit 4 — `numpy>=2.5.3` lands in a foreign station's manifests with no atlas story — it is dependency-completeness hygiene that AC10's own verify command requires, not a capability, so no atlas chain is due; reconciled on the `spec-pyforge-atlas` memlog; the lock hash change on `spec-pixi-candidate-currency`'s.
  - `[false]` `[reject]` Intent audit 5 — the "stamp scoped" clause of the Always list was not executed — the dispatch forbids `--write-baseline` in a producer run; `spec-surface-check` and `spec_surface_reconcile.py` both exit 0 on the memlog movement, and the landing supervisor stamps.
  - `[low]` `[patch]` Intent audit 6 — `default_mcp_probe()` was referenced by no production code; `probe_server_from_rendered` built `StdioMcpProbe()` directly — verified by grep. Fixed: the fallback calls `default_mcp_probe()`.

- **Dev pass 4, 2026-10-25 (Claude Fable 5.1, frontier tier; from HEAD `e7d271fa2f`; the implementer's pass, not a
  review).** Worked the round-5 blocker, every should-fix and every nit; the verification results are in the Auto Run
  Result below.
  - **blocker — AC9, closed durably** as the pre-flight diagnosis prescribed: `scripts/docs_station_cli.py::capture_help`
    builds the child's environment through `_help_env()` — `FORCE_COLOR`, `PY_COLORS`, `CLICOLOR_FORCE`,
    `GITHUB_ACTIONS`, `TTY_COMPATIBLE` and `TERMINAL_WIDTH` removed, `NO_COLOR=1` and `COLUMNS=100` set; the measured
    cause is recorded beside the list. `tests/scripts/test_docs_station_cli.py` gains
    `test_capture_help_scrubs_terminal_forcing_variables_and_pins_columns` (monkeypatched `subprocess.run`, every
    forcing variable and `TERM=dumb` set, asserts the `env=` carries none of them and `COLUMNS == "100"`);
    `docs-gen-test` 48 passed. The page was regenerated with exactly `pixi run -e pyforge-guild docs-station-cli` from
    the worktree root; `pixi run --frozen -e pyforge-guild docs-station-cli -- --check` exits **0** from a plain shell
    and **0** under `FORCE_COLOR=1 TERM=dumb` (the shape that produced the three stale renders). `docs/map.yaml` carries
    the new stamp.
  - **Round-4 entry and Auto Run Result corrected** (above and below); the team-memory file
    `.claude/memory/project/story-103-1-build-auto-round-4-closed-round-3-probe-blockers.md` ("AC9 cheat sheet green")
    deleted with its `MEMORY.md` index line — a progress note, not a decision; the earlier fix-pass note stays.
  - **should-fix (1) Windows read path:** `_open_chunks` returns `_ThreadChunks` (a reader thread feeding a `queue`) on
    `win32` and `_SelectorChunks` elsewhere; `_read_reply` consumes either. Tested on fakes and real pipes (the thread
    source runs on Linux too); `probe_server` on `win32` is driven end to end against a duplex fake `Popen`
    (`creationflags`, no `start_new_session`, CTRL_BREAK_EVENT when present, then `terminate`/`kill`).
  - **(2) AC5:** one parametrized test per failure outcome through `run_preflight --format json` asserts
    `startable: false`, no `tool_count`, `outcome=<name>` and a redacted stderr tail (a `ghp_` token in, `***REDACTED***`
    out); `started` asserts `startable: true`, `tool_count`, no finding and that the home's rendered command/args/env and
    the home as cwd reached the probe. `test_init.py`'s five no-probe tests (nothing declared, missing and malformed
    `.mcp.json`, unresolvable and separator-bearing commands) inject `_FailIfCalledMcpProbe`.
  - **(3) AC1:** `McpProbeResult` carries `reported_server_name` and `tool_names`; the real-`marshal-mcp` test asserts
    `pyforge-marshal` and exactly the eight names. **(4) AC2:** each tool is monkeypatched in `tools.py` and the SDK
    call's content is asserted equal to the stub's value, with the forwarded kwargs. **(5) AC4:** `build_server` is
    patched to fail the test if reached; `--help`'s text (MCP, stdio, `[mcp_servers.marshal]`), `--version`'s equality
    with `importlib.metadata.version("pyforge-marshal")` and the unknown-argument exit 2 are asserted in process; two
    subprocess cases run the console script (or `python -m pyforge.marshal.mcp`) with stdin closed and with stdin left
    open, within 5 s. **(6) AC7:** two preflight runs go through the real adapter — the real `marshal-mcp`
    (`startable: true`, `tool_count: 8`, no 012) and a `marshal-mcp` stand-in on `PATH` that imports an absent module
    (012 with `ModuleNotFoundError`, `exit_code=1`). **(7)** every real-process fixture ends in `_assert_group_gone`:
    `os.killpg(pgid, 0)` must raise `ProcessLookupError` — retried for up to 2 s because a just-killed grandchild is a
    zombie (still a group member) until init reaps it, then asserted unconditionally; the pgid comes from a marker the
    fixture writes first (`$$` for the shell fixtures). **(8)** `.steward/estate-refresh/2026-10-14.json` restored from
    `origin/main`: `estate reconcile` does rewrite the latest journal by contract (`run_reconcile` picks
    `journals[-1]`), but this story has nothing to journal — `environment.yaml` is current against the exporter
    (`pixi project export conda-environment -e build`), so the reconcile was not rerun here. **(9)** one
    `spec-pyforge-marshal` memlog event names every path (see the Auto Run Result).
  - **nits:** the stdout-EOF spin is gone (`_SelectorChunks` unregisters the fd at EOF; EOF while the child lives waits
    a 1 s grace for its exit, then is `bad-reply` with the detail "closed its stdout"); stderr is closed only after the
    reader thread has exited (a pipe a thread is still blocked on is left to it); what an exited child wrote is parsed
    before `exited` is reported (a server that answers `tools/list` and exits is `started`); the stderr reader starts
    inside the `try`; a post-spawn exception maps to `exited` (child gone) or `bad-reply`, never `spawn-failed`; the
    group is signalled before it is reaped — SIGTERM, a 1 s grace, SIGKILL unconditionally, then the reap — and stopped
    **once**, in `probe_server`'s `finally`, on every path (the round-3 "stop before the drain" order is no longer
    needed: the drain is bounded by one wait slice and the deadline, so nothing can block on a grandchild's pipe);
    `_popen_kwargs` deleted; `mcp/__main__.py` raises `SystemExit(main())` (`python -m pyforge.marshal.mcp --bogus`
    exits 2, tested); `mcp/__init__.py` no longer says "FastMCP-free"; the `${VAR}` residual risk and the pyforge-core
    exemption are in the Change Log. **Kept as is, with the reason:** the shared preflight fakes are still taken with
    `import test_init` — `test_teardown_preserve.py` and `test_init_teardown_preserve.py` already do, and moving
    `FakeFs`/`FakeVcs`/`FakeHarness` out of that 3,000-line module is a refactor of Story 1.x's test seam, not this
    fix's; the module docstring says so.
  - **Also:** the result is built after the stop and the reader join, so the tail carries stderr written just before an
    exit (tested); `detail` is redacted beside the tail and text `redact_raw_text` cannot redact is never printed
    (`[unredactable]`); `_probe_mcp_servers`'s docstring names the fourth sub-case and the seam.
  - `pyforge-deps-test` red on `pyforge-atlas`'s undeclared `numpy` import at the end of this implementer pass (red on
    `main` too, round 5); closed in the orchestrator's verify step by declaring `numpy>=2.5.3` in the atlas manifests
    (Spec Change Log, 2026-10-25 "orchestrator verify step"), so the branch now touches those two files.

- **Dev pass 4 pre-flight diagnosis, 2026-10-25 (bmad-build-auto orchestrator, HEAD `e7d271fa2f`, before the
  implementation subagent ran).** The AC9 blocker has a root cause in the generator, not in how it was invoked.
  `scripts/docs_station_cli.py::capture_help` pins `COLUMNS=100` and claims deterministic wrapping "regardless of
  caller's terminal", but it inherits the rest of the caller's environment, and typer 0.27.2 / rich 15.0.0 ignore
  `COLUMNS` when the caller's environment forces a terminal and `TERM` is `dumb` or `unknown`. Measured in this
  worktree, `pixi run --frozen -e pyforge-guild scribe --help` with `NO_COLOR=1 COLUMNS=100`: plain environment 100
  columns; `TERM=dumb` alone 100; `TERM=dumb FORCE_COLOR=1` 80 (typer sets `force_terminal=True` whenever
  `FORCE_COLOR`, `PY_COLORS` or `GITHUB_ACTIONS` is set, and rich's `Console.size` returns 80x25 for a forced terminal
  whose `TERM` is `dumb` or `unknown` before it reads `COLUMNS`). `FORCE_COLOR=1` alone still wraps at 100 visible
  columns but emits ANSI styling into the capture (154 escape sequences; the 140-character raw lines are escape-code
  overhead, not the pty's width -- `NO_COLOR` removes colour, not bold/dim), so a forced terminal corrupts the page
  either way. (Corrected in the review pass of this dev pass: the first version of this entry read the 140 as the
  pty's width.) The three earlier passes ran under a harness with `TERM=dumb` and a forcing variable, so every one
  of their renders was an 80-column page, and `--check` run from a plain terminal reads it as stale. In this
  session's environment none of those variables is set and `--check` exits 1 against the committed page, as the
  round-5 reviewer found.
  - Durable close for AC9 (a broken window in a file this story already touches, AGENTS.md behavioural guideline 3):
    make `capture_help` build the child's environment deterministically. Remove `FORCE_COLOR`, `PY_COLORS`,
    `CLICOLOR_FORCE`, `GITHUB_ACTIONS`, `TTY_COMPATIBLE` and `TERMINAL_WIDTH` from the copied environment beside the
    existing `NO_COLOR=1` and `COLUMNS=100`; the child's stdout is a pipe, so rich then reads `COLUMNS`. Add a test in
    `tests/scripts/test_docs_station_cli.py` that monkeypatches `subprocess.run`, sets `FORCE_COLOR=1` and `TERM=dumb`
    in `os.environ`, and asserts the `env=` the generator passes carries none of the removed keys and has
    `COLUMNS == "100"`. Run `pixi run --frozen -e pyforge-guild docs-gen-test`. Then regenerate with exactly
    `pixi run -e pyforge-guild docs-station-cli` from the worktree root, confirm `pixi run --frozen -e pyforge-guild
    docs-station-cli -- --check` exits 0, and record the exit code in the Auto Run Result. `scripts/docs_station_cli.py`
    is already named on the `spec-pyforge-doctor` memlog for this story; the new reconcile entry names the generator
    change and the regenerated page.
  - Everything else in the round-5 entry stands as written: correct the round-4 entry and the Auto Run Result, fix
    or delete the team-memory file it names, and work the should-fix list and nits.

- **Round 5, 2026-10-25 (independent re-review of draft PR #2307, head `6f559f3de7`, rework `d4bdb881ce..HEAD`):
  FAIL — 1 blocker. Sent back to `ready-for-dev`; `landing_review: required` stays; the next pass runs on the
  operator-approved `fable` tier (Claude Fable 5.1), `difficulty: fable`.** Resolved and reproduced: the drain is
  select-bounded and the group is stopped first; `pgid = proc.pid`, SIGTERM then SIGKILL, reap; a SIGTERM-ignoring
  grandchild and both `sleep 600 & exit 1` shapes leave no group member; any exception maps to an outcome; the
  hollow mutation test is real; 66 tests pass; all five AC8-style mutations fail named tests.
  - **The "Round 4 … PASS — 0 blockers" entry above and the Auto Run Result are wrong and must be corrected**: the
    implementer's own fix pass is not a review verdict (AGENTS.md behavioural guideline 8), and AC9 was not green.
    The new team-memory file `.claude/memory/project/story-103-1-build-auto-round-4-closed-round-3-probe-blockers.md`
    says "AC9 cheat sheet green": correct it or delete it (and its `MEMORY.md` index line if one was added).
  - **blocker — AC9** (`docs/reference/station-cheat-sheet.md:193-222`): the scribe block is still wrapped at 80
    columns; `main` and a fresh render use 100; `pixi run --frozen -e pyforge-guild docs-station-cli -- --check`
    exits 1. Run exactly `pixi run -e pyforge-guild docs-station-cli` from the worktree root (the generator pins
    `COLUMNS=100`; do not render it any other way), commit, and quote the `--check` exit code.
  - **should-fix (carried, not attempted last pass)**: (1) Windows read path (`adapters/mcp_stdio_probe.py:67`,
    `:110`, `:127`): `selectors` on a pipe fd fails on win32 and maps to `spawn-failed`; use a reader thread and a
    queue on win32. (2) AC5: a `_probe_mcp_servers`-level test per failure outcome asserting `startable: false`, the
    outcome and the redacted stderr tail; a fail-if-called fake in `test_init.py:2809` and `:2867`. (3) AC1: carry the
    reported server name and tool names in `McpProbeResult` (`ports/mcp_probe.py:23-31`) and assert `pyforge-marshal`
    and the eight names. (4) AC2 (`tests/unit/test_mcp_story_103.py:149-163`): assert the call returns the stubbed
    value. (5) AC4 (`:209-216`): patch `build_server` to raise, assert the help text and the installed version, add a
    subprocess case with stdin open and closed. (6) AC7 (`:790-858`): at least one preflight run through the real
    adapter against the real `marshal-mcp`, and one against a tiny script that imports a missing module. (7) Assert
    `os.killpg(pgid, 0)` raises `ProcessLookupError` after every real-process fixture (`:255`, `:431`, `:521`, `:534`,
    `:550`, `:609`; `:340-357` checks a pid, not the group). (8) Restore `.steward/estate-refresh/2026-10-14.json`
    from `origin/main` (still +342/−48 with this worktree's absolute paths). (9) Append one `spec-pyforge-marshal`
    memlog event naming `cli/init.py`, `core/egress.py`, `core/findings.py`, the package `pyproject.toml` and
    `pixi.toml`, `tests/unit/test_init.py`, `tests/unit/test_egress.py`,
    `tests/meta/test_ad34_egress_registry_completeness.py`.
  - **nits**: the stdout-EOF busy loop (`:140-145`; unregister the fd and wait); close stderr only after the reader
    exits (`:482-490`); parse the drained stdout lines before reporting `exited` or drop the drain (`:120`, `:136`,
    `:143`); start the reader thread inside the `try` (`:319-331`); do not label post-spawn `OSError` as
    `spawn-failed` (`:466`); signal before reaping and stop once (`:231`, `:236`, `:244`); delete the dead
    `_popen_kwargs` (`:178-183`); `mcp/__main__.py:8` `raise SystemExit(main())` (`python -m pyforge.marshal.mcp --bogus`
    exits 0); `mcp/__init__.py:17` still says "FastMCP-free"; move the shared fixtures to `tests/unit/conftest.py`
    instead of `import test_init`; add the `${VAR}` residual risk and the pyforge-core `test_process_sole_ownership.py`
    exemption to the Change Log.
  - Unrelated and not this story's: `pyforge-deps-test` fails on `main` too (pyforge-atlas imports `numpy` without
    declaring it).

- **Dev pass 3, 2026-10-25 (bmad-build-auto fix pass for the round-3 blockers, head `205e11db70`) — not a review
  verdict.** *Corrected in dev pass 4: this entry was written as "Round 4 … PASS — 0 blockers". An implementer's own fix
  pass is not a review (AGENTS.md behavioural guideline 8), and its AC9 claim was false from a plain shell — the page it
  committed was an 80-column render; round 5 found `--check` exiting 1, and the dev pass 4 pre-flight diagnosis traced it
  to the generator's inherited environment.* Addressed the three round-3 blockers as follows:
  - **blocker 1 — bounded stdout drain:** `_drain_stdout_buffered` drains with select-bounded reads against the remaining deadline; on child exit, process group stop runs before drain (no EOF blocking).
  - **blocker 2 — process group teardown:** `_stop_process_group` uses `pgid = proc.pid` (never `getpgid` after reap), SIGTERM then unconditional SIGKILL with settle/retry for shell background children; pipe streams closed in `finally`.
  - **blocker 3 — AC9 cheat sheet:** claimed `docs-station-cli --check` green (marshal-mcp usage at 100 columns) — **wrong**
    (see the correction above): the render ran under a forced-terminal environment and wrapped the scribe block at 80.
  - **tests:** grandchild fixtures (detached stdio, stdout hold, SIGTERM-ignoring child), real mutation guard for stop teardown, coverage helpers for `_popen_kwargs` and probe exception mapping.
  - **verification:** `pyforge-marshal-test` 13286 passed; `pyforge-marshal-coverage-gate` OK; `lint-types` OK; `docs-station-cli --check` OK *(only under that pass's own environment; exit 1 from a plain shell)*; `python scripts/spec_surface_reconcile.py` OK after memlog on `spec-pyforge-marshal`.
  - **note:** `pyforge-deps-test` reports a pre-existing `pyforge-atlas` numpy import completeness failure unrelated to this diff.

- **Round 3, 2026-10-25 (independent re-review of draft PR #2307, head `d3910b6f59`, rework `2ab8529aeb..HEAD`):
  FAIL — 3 blockers. Sent back to `ready-for-dev`; `landing_review: required` stays.** Resolved since round 2: the
  deadline while the child lives, `BrokenPipeError` on write, `id` matching and `serverInfo`, chunked stderr, all three
  AC8 mutations, lint, spec-surface. Do the three blockers first, exactly as written:
  - **blocker 1 (new) — `_drain_stdout` hangs** (`adapters/mcp_stdio_probe.py:51-65`, called at `:96`, `:111`, `:117`):
    it reads to EOF with no deadline, so `sh -c 'sleep 600 & exit 1'` (a grandchild holding stdout after the child
    exits) blocks preflight forever. Fix: never block past the deadline — when the child has exited, stop the whole
    process group FIRST (blocker 2), then drain only what is already buffered with a select-bounded, non-blocking read
    against the remaining deadline.
  - **blocker 2 — the process group is still not stopped** (`:179-216`): `os.getpgid(proc.pid)` runs after the child
    was reaped, raises `ProcessLookupError`, and only `proc.terminate()` runs; SIGKILL is sent only if the direct child
    outlives 2 s. Fix: `pgid = proc.pid` (guaranteed by `start_new_session=True`; never call `getpgid`);
    `os.killpg(pgid, SIGTERM)` ignoring `ProcessLookupError`; wait the short grace; `os.killpg(pgid, SIGKILL)`
    UNCONDITIONALLY, ignoring `ProcessLookupError`; then reap the child with a guarded wait. Tests (no slow marker):
    after EVERY real-process fixture assert `os.killpg(pgid, 0)` raises `ProcessLookupError` — unconditionally, not
    behind `if pgid_file.is_file()`; add fixtures for (a) child exits while a grandchild with detached pipes lives
    (`sleep 600 </dev/null >/dev/null 2>&1 & exit 1`), (b) child exits while a grandchild holds stdout
    (`sleep 600 & exit 1`), (c) a grandchild that ignores SIGTERM (`(trap '' TERM; exec sleep 600) & sleep 600`).
    Each must return within the timeout and leave no group member alive. Replace the hollow
    `test_mutation_dropping_stop_process_group_fails_grandchild_test` (`tests/unit/test_mcp_story_103.py:775-777`,
    `assert callable(...)`) with a real assertion.
  - **blocker 3 — AC9 still stale** (`docs/reference/station-cheat-sheet.md:193-222`): the scribe block is wrapped at
    80 columns; `main` has 100. Fix: run exactly `pixi run -e pyforge-guild docs-station-cli`, commit, and confirm
    `pixi run --frozen -e pyforge-guild docs-station-cli -- --check` exits 0. Correct the Auto Run Result's claim.
  - **should-fix** — `probe_server` (`:312`, `:364`, `:372`): an unguarded `proc.wait(timeout=1)` raises
    `TimeoutExpired` for a server that answers `initialize`, closes stdin and stays alive, crashing preflight. Wrap the
    whole probe body so ANY exception maps to one of the six outcomes (with the stop always run). Windows read path
    (`:87-103`): `selectors` on a pipe fd does not work on Windows; use a reader thread and a queue on win32.
  - **should-fix — tests**: AC5 — a `_probe_mcp_servers`-level test for each of the five failure outcomes asserting
    `startable: false`, the outcome name and the redacted stderr tail; a recording fake that fails if called in the
    unresolvable and nothing-declared tests (`test_init.py:2809`, `:2870`). AC1 — carry the reported server name and
    tool names in `McpProbeResult` and assert `pyforge-marshal` and the eight names. AC2 — assert the call returns the
    stubbed value (`:163`). AC4 — patch `build_server` to raise, assert the help text and the installed version, and add
    a subprocess case with stdin open and closed. AC7 — at least one test drives a real server through the adapter (the
    real `marshal-mcp`, and a tiny script that imports a missing module as the fastmcp stand-in).
  - **should-fix — scope and stamp**: restore `.steward/estate-refresh/2026-10-14.json` from `origin/main` (it still
    carries this worktree's absolute paths, +342/−48). Append a `spec-pyforge-marshal` memlog event naming the eight
    still-unnamed paths: `cli/init.py`, `core/egress.py`, `core/findings.py`, the package `pyproject.toml` and
    `pixi.toml`, `tests/unit/test_init.py`, `tests/unit/test_egress.py`, `tests/meta/test_ad34_egress_registry_completeness.py`.
  - **nits** — `mcp/__main__.py:8` `raise SystemExit(main())`; close the three pipes after the joins; `mcp/__init__.py:8`
    still says "FastMCP-free"; delete or use the dead `_popen_kwargs` (`:152-157`); unregister the stdout fd on EOF
    (`:115-119` busy-loops); record `${VAR}` expansion as residual risk and the pyforge-core
    `test_process_sole_ownership.py` exemption in the Spec Change Log; move the shared sandbox fixtures to a
    `conftest.py`.
  - Note: the branch will conflict with `main` (81f66ee411) in four memlogs; the landing's union heal handles memlogs,
    then the scoped stamps must be re-run.

- **Round 2, 2026-10-25 (independent code review of the dispatch branch, `d287eceb0a..de66441fa4` plus the
  fix-pass commits through `44bc730c56`): FAIL — 7 blockers, 10 should-fix, 6 nits. Sent back to `ready-for-dev`;
  `landing_review: required` holds the verified landing at a draft PR for an independent re-review.** Run
  `pyforge-marshal-20261025T102941102Z-2ac9a1a6` ended `failed` at finalize: the scoped spec-surface stamp refused
  because the `spec-pyforge-marshal` memlog did not NAME `adapters/mcp_stdio_probe.py`, `core/mcp_probe.py`,
  `mcp/__init__.py`, `mcp/server.py`, `ports/mcp_probe.py` and `tests/unit/test_mcp_tools.py`.
  - **blocker — the timeout is never enforced** (`adapters/mcp_stdio_probe.py:40-48`): `proc.stdout.readline()`
    blocks and the deadline is checked only between lines. Measured: `timeout_s=1` against a server that sleeps 12 s
    returned after 12.04 s as `exited`; a grandchild holding stdout hung past 60 s. Read stdout against the remaining
    deadline (`selectors` + `os.read`, or a reader thread with `queue.get(timeout=remaining)`).
  - **blocker — `BrokenPipeError` on a write is unhandled** (`:145-149`, `:187-188`; `cli/init.py:607-619` does not
    catch it): a server that answers `initialize` and then exits crashes preflight (200/200 runs). Catch `OSError` on
    every write and map it to `exited`; wrap the probe body so any unexpected exception becomes one of the six
    outcomes.
  - **blocker — the process group is not always stopped** (`:77-79`): `_stop_process_group` returns early when the
    direct child already exited, leaving grandchildren running; after SIGTERM it waits only on the child. Always
    `os.killpg(pid, SIGTERM)` (ignore `ProcessLookupError`), wait, then `killpg(SIGKILL)` unconditionally, then reap.
  - **blocker — AC8: two of three mutations survive.** The skip-handshake test (`tests/unit/test_mcp_story_103.py:576-607`)
    exits on `MRS-PREFLIGHT-009` because `test_init.py`'s autouse sandbox fixtures do not apply in this module; set
    `BMAD_LOOP_HOME_ROOT` / `MARSHAL_STATE_HOME` to `tmp_path`, assert the fake probe was called and that
    `MRS-PREFLIGHT-012` and `exited` appear. Dropping `_stop_process_group` fails no test: add a real-process test
    asserting `os.killpg(pgid, 0)` raises `ProcessLookupError` after each probe.
  - **blocker — AC6 fixtures** (`:371-407`, `:441-471`): `timed-out` is monkeypatched, not real; the grandchild fixture
    is missing; the heavy-stderr fixture writes 3000 bytes, not 1 MiB; no test asserts the group is gone. Add the real
    never-answer, grandchild and 1 MiB fixtures with a liveness assertion after each.
  - **blocker — AC7 has no test**: `marshal preflight … --format json` against a home registering `marshal-mcp`
    (`startable: true`, `tool_count: 8`, no `MRS-PREFLIGHT-012`) and against a fastmcp-importing stand-in
    (`MRS-PREFLIGHT-012` with `ModuleNotFoundError`).
  - **blocker — AC9: `docs-station-cli -- --check` exits 1 (STALE)**: the committed `docs/reference/station-cheat-sheet.md`
    scribe block (about lines 192-223) is wrapped at 80 columns; the generator pins `COLUMNS=100`. Regenerate it in
    `pyforge-guild`.
  - **should-fix** — stderr is not captured while the server lives (`:65-74`, `:164-225`: `iter(proc.stderr.read, "")`
    reads to EOF; the result snapshots the tail before stop/join): read chunks with `os.read(fd, 4096)` and build the
    result after stop and join. Replies are not matched by JSON-RPC `id` and `serverInfo` is never checked (`:57-61`,
    `:180`): skip messages without the expected `id`; require `result.serverInfo` to be an object. `poll()` runs before
    stdout is drained (`:41-42`): drain to EOF before `exited`. Not portable to Windows (`:81-101`; the env is locked for
    win-64): branch on `sys.platform`, use `CREATE_NEW_PROCESS_GROUP` and `terminate()`/`kill()` there.
  - **should-fix — tests**: AC5 has no `_probe_mcp_servers`-level test of the five failure outcomes asserting
    `startable: false`, the outcome name, the redacted stderr tail; "runs no probe" is not asserted for the
    unresolvable and no-declared cases (inject a fake that fails when called). AC1: carry the reported server name and
    tool names in the result and assert `pyforge-marshal` and the eight names. AC2: assert the call returns the stubbed
    `tools` value. AC4: patch `build_server` to raise in the `--help`/`--version`/unknown tests, assert the text and
    the installed version, and add a subprocess case with stdin open and closed under 5 s.
  - **should-fix — out of scope**: `.steward/estate-refresh/2026-10-14.json` (+342/−48) rewrote steward Story 100.7's
    tracked journal with this worktree's absolute paths; restore it from `main` unless steward's contract says reconcile
    overwrites the latest journal.
  - **should-fix — the finalize stamp**: append a `spec-pyforge-marshal` memlog event that NAMES every changed path
    under `src/shared/packages/pyforge-marshal/` (and every other Spec `spec-surface-check` names), so the landing's
    scoped stamp succeeds.
  - **nits** — `mcp/__main__.py:8`: `raise SystemExit(main())`. Close the three pipes (`with Popen` or `finally`); pass
    `encoding="utf-8", errors="replace"`; guard the final `wait(timeout=2)`. The docstring at `:37` omits `exited`. Record
    in Residual risk that `${VAR}` expansion in `.mcp.json` env is not applied. Add the `pyforge-core`
    `test_process_sole_ownership.py` exemption to the Spec Change Log (the exemption itself is justified). Move the
    shared sandbox fixtures to `conftest.py` instead of importing `test_init`.
  - Note: the Auto Run Result's claim that `pyforge-deps-test` is red is not borne out; the supervisor's verification
    ran it and it passed (only `pyforge-core-test` and the coverage gate failed before the fix pass).

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

Status: done (dev pass 4 and its review pass, 2026-10-25, Claude Fable 5.1 on the frontier tier; `landing_review: required`
stays — an independent re-review on the draft PR before merge).

Summary of the implemented change: `marshal-mcp` runs on the official `MCPServer` with a real `--help`/`--version`
(`mcp>=2.2` declared on the package, the package `pixi.toml` and the root `[feature.pyforge-marshal.dependencies]`);
`marshal preflight` starts every declared server from the home's rendered `.mcp.json` through `McpProbePort` /
`adapters/mcp_stdio_probe.py` (deadline-bounded reads, concurrent stderr, one process-group stop on every path, a
reader-thread path for win32) and maps the outcome in `core/mcp_probe.py` to `startable` / `tool_count` or one redacted
`MRS-PREFLIGHT-012`. This pass closed the round-5 blocker at its root — `scripts/docs_station_cli.py::capture_help` now
builds a deterministic child environment, so the cheat sheet renders identically from a harness and a plain shell — and
worked every round-5 should-fix and nit, then the twelve patch entries of this pass's review.

Files changed in this pass (since `e7d271fa2f`):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/mcp_stdio_probe.py` — rewritten: `_SelectorChunks` /
  `_ThreadChunks` stdout sources, `_parse_buffered` / `_read_reply` with the post-exit drain, `_handshake` carrying
  `reported_server_name` / `tool_names` / `detail` and the child's exit code, one `_stop_process_group` in `probe_server`'s
  `finally`, `_close_pipes`, `default_mcp_probe()` as the production fallback.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/mcp_probe.py` — `McpProbeResult` gains
  `reported_server_name`, `tool_names`, `detail`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/mcp_probe.py` — redacts `detail` beside the stderr tail;
  never prints text it could not redact.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/server.py` — `--help` names MCP, stdio and
  `[mcp_servers.marshal]`; `--version` degrades when the distribution is absent; `SERVER_NAME`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/__main__.py` — `raise SystemExit(main())`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/__init__.py`, `cli/init.py` — docstrings (no FastMCP
  wording; the fourth sub-case and the DI seam named).
- `src/shared/packages/pyforge-marshal/tests/unit/test_mcp_story_103.py` — rewritten, 100 tests: AC1–AC8 as the
  Acceptance Criteria name them, every real-process fixture ending in an unconditional process-group check, the three
  AC8 mutation tests, the closed-stdin and post-exit-drain tests this pass's review added.
- `src/shared/packages/pyforge-marshal/tests/unit/test_init.py` — the five no-probe preflight tests inject
  `_FailIfCalledMcpProbe`.
- `scripts/docs_station_cli.py` — `_TERMINAL_FORCING_VARS` and `_help_env()`: the child runs without `FORCE_COLOR`,
  `PY_COLORS`, `CLICOLOR_FORCE`, `GITHUB_ACTIONS`, `TTY_COMPATIBLE`, `TERMINAL_WIDTH`, with `NO_COLOR=1` and
  `COLUMNS=100`.
- `tests/scripts/test_docs_station_cli.py` — the scrub asserted by literal variable name.
- `docs/reference/station-cheat-sheet.md`, `docs/map.yaml` — regenerated: `marshal-mcp --help` usage, every block at 100
  columns.
- `src/shared/packages/pyforge-atlas/pyproject.toml`, `src/shared/packages/pyforge-atlas/pixi.toml` — `numpy>=2.5.3`
  declared (imported at module level by `pipelines/derived_artifacts/alternatives.py`, atlas Story 37.7).
- `pixi.lock` — the `pyforge-atlas` `conda_source` hash and its depends list (`numpy >=2.5.3`) in the ten environments
  that build it; no resolved package changes.
- `.steward/estate-refresh/2026-10-14.json` — restored to `origin/main` (round-5 should-fix 8).
- `.claude/memory/project/story-103-1-build-auto-round-4-closed-round-3-probe-blockers.md`,
  `.claude/memory/project/story-103-1-build-auto-fix-pass-2026-10-25-mcp-stdio-probe-n.md` — deleted (progress notes,
  the first wrong about AC9); `.claude/memory/feedback/a-generated-page-that-captures-a-cli-s-help-is-not-determini.md`
  — new, the durable lesson, via `scribe capture --type feedback`; `.claude/memory/MEMORY.md` index updated.
- Memlogs: `spec-pyforge-marshal`, `spec-pyforge-core`, `spec-pyforge-doctor` (reconcile and a mechanism correction),
  `spec-pyforge-atlas`, `spec-pixi-candidate-currency` — every changed governed path named.
- This story spec: round-4 entry corrected, dev-pass-4 entries, the review-pass triage log, Spec Change Log entries, this
  result. `scripts/.spec-surface-baseline.json` is unchanged from `e7d271fa2f`.

Review findings breakdown (30 findings: high 0, medium 4, low 22, false 4):
- Patched, 12 entries: medium — the `_ThreadChunks` EOF race that could flake a test; the untested `closed_stdin` branch;
  the untested post-exit drain; the tautological scrub test. Low — the AC9 mechanism text (three places); the
  `_close_pipes` docstring; the stale `remaining` before the grace wait; the `# type: ignore` on `failed`; the inaccurate
  team-memory note; the stderr thread assigned before `start()`; the missing exit code on `bad-reply`/`error-reply`
  from an exited child; `default_mcp_probe()` unused by production code.
- Deferred: none.
- Rejected, 14: blind hunter 2 (an escape-code guard for a state the scrub makes unreachable), 8, 9 and 11 (edits to this
  spec's own log; corrected here as the run's output), 10 (false: the AUD-ATLAS-010 block's own floor rule), 13 (an SKF
  recompile and a spec edit); edge case 2, 3 and 5 (guards for states not shown reachable: a newline-less flood, a
  non-compliant server's request, `register` failing on a fresh pipe), 7 (false: the log records a deletion), 8 (a
  `setsid` descendant is beyond any process group; residual risk recorded in the Spec Change Log); intent audit 1, 2
  and 4 (the AC's named surface is run by hand, the shared fixtures are the ones the intent prescribes, the atlas
  declaration is hygiene a verify command requires), 3 and 5 (false: AC9's command was run; the stamp is the landing
  supervisor's by the dispatch rule).

Follow-up review recommendation: true — a first pass that patched four `medium` entries. The unverified risk: the
patched hunks (the two `_handshake` closed-stdin tests and the `_ScriptedChunks` drain test, the `_ThreadChunks` EOF join,
the literal-name scrub test, the `exit_code` and `reported_server_name` carries in `_handshake`) were verified by the
implementer's targeted tests and the orchestrator's full re-run below, not yet by an independent reader; the draft-PR
re-review that `landing_review: required` already demands should read those hunks first. Patched counts by verdict:
high 0, medium 4, low 8.

Verification performed on the final tree (every exit code read from `$?`, never through a pipe):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0 — 13355 passed, 15 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`: exit 0 — 130 passed, 3 skipped (red before the atlas declaration:
  `test_every_hard_import_is_a_declared_dependency[pyforge-atlas]`).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`: exit 0 — 7 touched modules ≥ 80%
  (`adapters/mcp_stdio_probe.py` 94%, `mcp/server.py` 97%, `cli/init.py` 91%).
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0 (ruff, `ruff format --check`, mypy over every package).
- `pixi run --frozen -e pyforge-guild docs-gen-test`: exit 0 — 48 passed.
- `pixi run --frozen -e pyforge-guild docs-station-cli -- --check`: exit 0 from a plain shell and exit 0 under
  `FORCE_COLOR=1 TERM=dumb` (AC9).
- AC1 by hand from `pyforge-guild`: the `initialize` pipe returns one JSON line, `result.serverInfo.name ==
  "pyforge-marshal"`, `protocolVersion 2025-06-18`, every pipeline stage 0. AC4 by hand: `marshal-mcp --help </dev/null`
  exit 0, `--version` prints `0.1.0` exit 0, `--bogus` exit 2.
- AC8: reproduced by the intent-alignment auditor on a scratch copy — each of the three mutations fails its named test
  (`test_mutation_skipping_handshake_in_probe_would_miss_finding`, `test_mutation_timed_out_not_startable`,
  `test_mutation_dropping_stop_process_group_leaves_a_grandchild`); all three pass unmutated.
- Matrix audit: every row of the I/O & Edge-Case Matrix is covered by a passing test (110 selected tests across
  `test_mcp_story_103.py` and `test_init.py`, exit 0).
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` with `TMPDIR` off tmpfs: exit 0 — core 2564, kit 95, atlas
  3478+103, doctor 3831+4, herald 2074, marshal 13355, mason 1622+12, scribe 428, steward 2981, warden 2440. (A first
  run with `TMPDIR` unset stopped red in herald on 23 `EXDEV` cross-device errors from the tmpfs `/tmp` — the documented
  trap, not this branch's.)
- `pixi lock --check`: exit 0 ("Lock-file was already up-to-date") after the re-lock; `environment.yaml` byte-identical to
  `pixi project export conda-environment -e build`.
- `python3 scripts/spec_surface_reconcile.py`: exit 0; `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 —
  on the memlog movement alone. No scoped stamp in this run (the dispatch forbids `--write-baseline` in a producer run);
  the landing supervisor stamps `spec-pyforge-marshal`, `spec-pyforge-core`, `spec-pyforge-doctor`, `spec-pyforge-atlas`
  and `spec-pixi-candidate-currency`.
- Not re-run after the review patches: `PYFORGE_PREFLIGHT_SCOPE=full pr-preflight` (the implementer's run before the
  patches: 34/37 lanes ok; `detectors-ci` red only on `ledger-direction` 87-19, which clears when the landing merges
  `origin/main`, and the fleet-wide `chain-currency` `code→retro` edge that `origin/main` carries too); `llms-full-check`
  (exit 0 before the patches; no manifest row changed since).

Residual risks: a server that starts but fails on its first tool call still passes (the probe lists tools); each declared
server costs up to 15 s per preflight; one `protocolVersion` is offered; the rendered `env` is passed as written (no
`${VAR}` expansion); a `setsid` descendant escapes the process-group stop. All recorded in the Spec Change Log.
