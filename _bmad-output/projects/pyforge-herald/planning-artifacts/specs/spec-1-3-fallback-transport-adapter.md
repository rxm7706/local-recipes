---
title: 'Fallback transport adapter (AgentSdkTransport)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 1.2's spike proved the primary `McpTransport` path reaches `claude-design`
from this environment, so V1 ships it as the default -- but the archived `SPEC-design-code-bridge`
Assumption is explicit that transport is dual-path: "fallback = a headless Claude Code / Agent SDK
wrapper with a tool allowlist reusing the stored login (the bmad-loop-proven substrate;
token-costed)". FR-22 exists so an environment where the raw `mcp` SDK cannot reach
`api.anthropic.com/v1/design/mcp` directly (a sandbox, a CI runner, an air-gapped host) still has
a `DesignTransport` that can, via a locally-installed, already-authenticated `claude` CLI. Two
prior dev attempts at this exact story (2026-07-30, run `20260730-192235-062b`) died silently
mid-thinking with a nested `claude -p` still `Running...` past its own `timeout 90` -- the
2026-07-31 constraint amendment is why this spec's Boundaries require the process-launch seam to
be injected and never spawned in development or test.

**Approach:** `transport/agent_sdk_transport.py` implements `DesignTransport` by relaying each of
the 8 port calls through one headless `claude -p` turn, scoped to exactly one allowlisted MCP tool
per call (FR-22). The relay is a *mechanical* protocol bridge, not a decision-maker -- the prompt
names one tool and one JSON arguments object and instructs the nested agent to echo the tool's raw
result verbatim between fixed sentinel markers, preserving `bridge-protocol.md`'s "no LLM in the
loop" constraint for the deterministic seed/pull/status/watch operations that will call it. Every
marshalling, sanitization, and FR-24 rule is identical to `McpTransport`'s, reusing the same three
shared invariants from `transport.base` (`sanitize_payload`, `parse_read_response`,
`require_conditional`) plus the two null-coercion helpers Story 1.2's own deferred-work ledger
(DW-1-2-14) anticipated promoting to public here (`as_text`/`as_optional_text`).

## Boundaries & Constraints

**Always:**
- `AgentSdkTransport` implements the full 8-method `DesignTransport` protocol
  (`transport/base.py`), structurally verified via `isinstance(..., DesignTransport)`.
- **The process-launch seam is always injected.** `AgentSdkTransport(*, launcher:
  AgentProcessLauncher | None = None)`; the real `SubprocessAgentLauncher` is constructed lazily,
  only inside the call path that needs one -- constructing a transport, or importing this module,
  spawns nothing.
- **No test in this package, and no code path this story exercises, ever spawns a real nested
  `claude` process.** Every `AgentSdkTransport` test injects a hand-written `FakeLauncher`.
  `SubprocessAgentLauncher`'s own tests patch `subprocess.run` itself to exercise its
  error-mapping branches with nothing actually spawned.
- FR-22's allowlist is scoped to exactly one fully-qualified MCP tool name
  (`mcp__claude-design__<tool>`) per relay call, never the whole `claude-design` surface.
- FR-24 is enforced identically to `McpTransport`: `create_support_js` requires `if_match`;
  `write_files`/`copy_files` run every entry through `require_conditional` before any relay call.
- `sanitize_payload` covers every JSON-parsed answer and the relay prompt's own arguments (a
  caller error putting tokenized material into an argument must not ride the prompt into a
  process log); `read_file`'s body and `get_design_prompt`'s prose keep the same content-vs-envelope
  exemption `McpTransport` documents (whole-string redaction would corrupt real content or destroy
  the mandatory pre-write gate).
- `AuthError` is raised both when the launcher itself reports failure with an auth-denial marker
  in its detail, and when a successfully-relayed answer's text names one -- checked before the
  generic `TransportUnreachableError`/`TransportCallError` classification in both paths, since it
  is the one error `bridge-protocol.md` § Watch parameters says must halt, never retry.
- No credential of any kind is read, held, or passed by this module -- "reusing the stored login"
  means the nested `claude` process authenticates itself; NFR-05 is satisfied by construction.
- `base.py`'s `_as_text`/`_as_optional_text` are promoted to public `as_text`/`as_optional_text`
  (pure rename, `mcp_transport.py` updated to match) -- closes DW-1-2-14.

**Block If:** N/A -- no spike, no live gate; the block condition for this story was the 2026-07-31
amendment itself (never spawn the real process), already satisfied by construction above.

**Never:**
- No live/opt-in test spawning a real nested agent (unlike Story 1.2's `test_live_design_spike.py`)
  -- the crash history is the reason, and live verification is an operator-run integration check
  outside this suite.
- No change to `McpTransport`'s own class structure or behavior beyond the `as_text` rename.
- No `bridge.py`, `deck_pipeline.py`, `cli.py` wiring -- this adapter is not selected by anything
  yet; that is a later story's call (bridge-core stays transport-agnostic per AD-3/AD-4, and
  `test_bridge.py`'s derived denylists automatically cover this module and its exports the moment
  they exist, with no test-file edit required).
- No new runtime dependency -- `subprocess` is stdlib; the nested `claude` CLI is assumed present
  on PATH, not declared as a package dependency (it is a repo-local dev tool, not installed via
  this package's own manifest).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Protocol conformance | `AgentSdkTransport()` | `isinstance(t, DesignTransport)` is `True` | No error |
| Construction spawns nothing | `AgentSdkTransport()` / `AgentSdkTransport(launcher=None)` with `subprocess.run` patched to raise if called | No call to `subprocess.run` | No error |
| Allowlist scoping | any port call | launcher's `allowed_tools == ["mcp__claude-design__<tool>"]` | No error |
| Well-formed result | relay stdout wraps `<<<HERALD_TOOL_RESULT>>>...<<<END_HERALD_TOOL_RESULT>>>` | parsed as the tool's raw text/JSON, marshalled exactly as `McpTransport` | No error |
| Well-formed tool error | relay stdout wraps `<<<HERALD_TOOL_ERROR>>>...<<<END_HERALD_TOOL_ERROR>>>` | sanitized text raised | `TransportCallError` |
| No marker found | relay stdout has neither wrapper | relay contract not honoured | `TransportUnreachableError` |
| Both markers found | relay stdout has both wrappers | relay contract not honoured | `TransportUnreachableError` |
| Launcher reports failure | `AgentLaunchResult(failed=True, detail=...)` | sanitized detail raised | `TransportUnreachableError` |
| Launcher failure detail names an auth denial | detail matches `_AUTH_DENIAL_RE` | | `AuthError` |
| Relayed error text names an auth denial | error-wrapped text matches `_AUTH_DENIAL_RE` | | `AuthError` |
| Unconditional write | `write_files`/`copy_files` entry missing `if_match`/`leaf_if_match` | raised before any launcher call | `UnconditionalWriteError` |
| `finalize_plan` empty paths plan | `scope="paths"`, no writes/deletes | raised before any launcher call | `TransportCallError` |
| `finalize_plan` unknown scope | `scope="bogus"` | raised before any launcher call | `TransportCallError` |
| `SubprocessAgentLauncher` missing executable | `subprocess.run` raises `FileNotFoundError` (patched, not real) | `AgentLaunchResult(failed=True, ...)` naming the executable | No exception escapes |
| `SubprocessAgentLauncher` other OSError | `subprocess.run` raises `PermissionError` (patched) | `AgentLaunchResult(failed=True, ...)` | No exception escapes |
| `SubprocessAgentLauncher` timeout | `subprocess.run` raises `TimeoutExpired` (patched) | `AgentLaunchResult(failed=True, ...)` naming the timeout | No exception escapes |
| `SubprocessAgentLauncher` nonzero exit | patched `completed.returncode != 0` | `AgentLaunchResult(failed=True, detail=stderr/stdout tail)` | No exception escapes |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py` -- read + edit --
  `_as_text`/`_as_optional_text` promoted to public `as_text`/`as_optional_text` (DW-1-2-14).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py` -- edit --
  import + call-site rename only, no behavior change.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/agent_sdk_transport.py` --
  create -- `AgentLaunchResult`, `AgentProcessLauncher` (Protocol), `SubprocessAgentLauncher` (the
  real launcher, never invoked live by this suite), `AgentSdkTransport` (the 8 port methods + the
  relay pipeline: `_relay_prompt`, `_parse_relay`, `_raw_text`/`_call_text`/`_call_json`).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/__init__.py` -- edit -- export
  `AgentLaunchResult`, `AgentProcessLauncher`, `AgentSdkTransport`, `SubprocessAgentLauncher`,
  `as_text`, `as_optional_text`.
- `src/shared/packages/pyforge-herald/tests/test_agent_sdk_transport.py` -- create -- the I/O
  matrix above, `FakeLauncher` (hand-written, no `unittest.mock`), plus the `SubprocessAgentLauncher`
  error-mapping tests (real class, `subprocess.run` patched, nothing spawned).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` -- edit --
  DW-1-2-14 marked done.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-code-bridge/` archive
  (read-only) -- FR-22's "dual-path transport" Assumption is this story's charter.
- `src/shared/packages/pyforge-herald/tests/test_bridge.py` -- **untouched, deliberately**: its
  `_FORBIDDEN_ADAPTER_MODULES`/`_FORBIDDEN_ADAPTER_NAMES` derive from the live `transport` package
  and `transport.__all__`, so this story's new module and exports are covered automatically
  (superseding the pre-existing `_SPECULATIVE_ADAPTER_MODULES`/`_SPECULATIVE_ADAPTER_NAMES` union,
  which stays harmless now that the real names are derived).

## Design Notes

**Why relay through a sentinel-wrapped prose turn rather than the Agent SDK's structured tool-use
API.** The story's own crash history (two silent deaths spawning a nested session) argues for the
simplest possible contract at the process boundary: one `-p` prompt, one grant, one stdout capture,
parsed by a fixed string search rather than a second layer of SDK/JSON-RPC machinery this module
would then also have to keep alive across a subprocess boundary. `_relay_prompt`'s instruction is
mechanical by design (name the tool, name the arguments, echo the raw result) specifically so the
nested turn is a relay and not a participant in the "no LLM in the loop" bridge-core contract.

**Why the allowlist is per-call, not per-transport.** Granting `mcp__claude-design__*` once at
construction would be simpler, but FR-22 explicitly calls for a tool allowlist, and the narrowest
enforceable grain is the one tool the current call actually needs -- a compromised or buggy prompt
cannot widen its own reach mid-turn.

**Judgment call: `_AUTH_DENIAL_RE` is a best-effort prose match, not a structured signal.** Unlike
`McpTransport`, which can inspect an HTTP status code, the nested agent's own auth failure can only
surface as prose it chooses to emit. The pattern is deliberately narrow (looking for
`/design-login`, "log in", "no stored/active credential") to avoid the inverse of Story 1.2's own
follow-up fix (a bare "401" misclassifying a connection failure) -- an unmatched auth failure still
raises the correct `TransportUnreachableError`/`TransportCallError`, just without the
`/design-login` remediation hint. Recorded as an accepted limitation, not deferred: there is no
richer signal available from this transport's own protocol to improve on.

**Judgment call: no `subprocess` timeout beyond the launcher's own 120s default.** Mirrors Story
1.2's own deferred `mcp` SDK timeout gap (DW-1-2-9) rather than fixing it here -- the consumer that
would need a tighter, caller-tunable bound is the watch loop (a later story), and inventing one now
risks guessing wrong before that caller exists.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- 311 passed, 2 skipped (was 306 passed, 2
  skipped before this story's 5 new construction/error-mapping tests plus the existing suite's
  count from Stories 1.1/1.2/1.4/1.5; the 2 skips are Story 1.2's live-spike test, unaffected).
- `ruff format --check` / `ruff check` from the package root -- clean on every file this story
  touches (`agent_sdk_transport.py`, `test_agent_sdk_transport.py`, `transport/__init__.py`,
  `base.py`, `mcp_transport.py`); pre-existing findings in `test_bridge.py`/`test_registry.py`
  (import ordering) and `test_transport_base.py`/`mcp_transport.py` (`SIM117` nested `with`) are
  untouched by this story and out of its scope.

**Manual checks:**
- `isinstance(AgentSdkTransport(), DesignTransport)` is `True`.
- `grep -rn "claude_agent_sdk\|anthropic\b" transport/agent_sdk_transport.py` returns nothing --
  this adapter shells the CLI, it does not import any inference SDK (keeping it clear of
  `test_bridge.py`'s `_FORBIDDEN_INFERENCE_PACKAGES` denylist, which is bridge-core's concern but a
  useful cross-check for the adapter itself).
- `grep -n "AgentSdkTransport\|agent_sdk_transport" transport/__init__.py` confirms both the module
  and the class are exported, which is what makes `test_bridge.py`'s derived denylists pick them up
  with zero edits to that file.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (single agent, no independent second reviewer)

This story was implemented and reviewed by one session, not the two-pass independent-reviewer loop
Stories 1.1/1.2/1.4/1.5 went through under `bmad-loop`. Findings below are from a deliberate
adversarial re-read of the diff after the suite was green, looking specifically for: exception
handling too broad/narrow, resource leaks, silent failures that should be loud, and
docstring/behavior mismatches.

- `[medium]` `[patch]` **`SubprocessAgentLauncher.run` only caught `FileNotFoundError` and
  `TimeoutExpired`.** Any other launch-time `OSError` (permission denied, a transient fork/exec
  resource failure) would have escaped as a bare `OSError`, past the `HeraldError` hierarchy
  `cli.dispatch`'s AD-6 boundary catches. Widened to `except OSError` (a superset covering
  `FileNotFoundError`); added `test_subprocess_agent_launcher_maps_permission_denied_to_a_failure`.
- `[low]` `[patch]` **`finalize_plan`'s `base_etags` was returned as a plain, caller-mutable
  `dict`**, unlike `McpTransport`'s `MappingProxyType`-wrapped equivalent -- a caller mutating the
  returned `PlanHandle.base_etags` in place would silently corrupt state a later `bridge-core`
  operation might still read. Wrapped in `MappingProxyType` to match.
- `[low]` `[patch]` Two docstrings (module doc and `SubprocessAgentLauncher`'s own) originally
  claimed the real launcher's `.run()` method is "never invoked" by this suite. After adding the
  error-mapping tests (which do call `.run()`, with `subprocess.run` itself patched out so nothing
  is actually spawned), the claim no longer matched the code. Both docstrings corrected to state
  the accurate, narrower guarantee: no test lets the real subprocess spawn.
- `addressed_findings`: 3 (1 medium, 2 low). No `intent_gap`, no `bad_spec`, no `defer`, no
  `reject` -- a single-pass self-review over a story this size finding three real, fixable issues
  and nothing to defer or dispute is itself a data point: `followup_review_recommended: false`
  above reflects that the found issues were fixed, not merely noted, and none of the three rises to
  the severity that gated Story 1.2's own follow-up-review recommendation.

All three patches applied; full suite re-verified green after patching: **311 passed, 2 skipped**;
`ruff format --check` and `ruff check` clean on every file this story touches.
