---
title: 'Transport port + primary MCP-client adapter (the transport spike)'
type: 'feature'
created: '2026-07-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: '2f9c635f7b8ab74956d2e95f830349bf3f3a4491'
final_revision: 'bd71f5659a'
---

<intent-contract>

## Intent

**Problem:** Herald's package exists (Story 1.1) but has no way to reach the `claude-design`
surface. Every later story (bridge-core 1.4, seed 1.6, all of Epics 2–5) depends on a
`DesignTransport` port existing *and* on knowing whether the primary pure-MCP-client path can
reach the server from a plain, non-interactive Python process — the PRD's prove-or-kill spike
(FR-21/FR-22), sequenced as the first implementation story precisely because the answer
reshapes everything downstream.

**Approach:** Define the `DesignTransport` `typing.Protocol` (the exact 8-tool
`bridge-protocol.md` surface) in `transport/base.py` alongside the result types and the two
protocol invariants every adapter upholds (`serve_url` sanitization, read-response parsing),
then implement `McpTransport` against the `mcp` >=1.28.1 SDK reusing the stored `/design-login`
OAuth credential, and record the live spike result as re-runnable, env-gated evidence.

## Boundaries & Constraints

**Always:**
- `DesignTransport` is a `@runtime_checkable typing.Protocol` in
  `src/pyforge/herald/transport/base.py` exposing exactly these 8 methods (Herald-side names,
  per AD-3 / epics AC): `get_design_prompt`, `create_project`, `finalize_plan`,
  `create_support_js`, `copy_files`, `write_files`, `read_file`, `render_preview`. Warden's
  `interfaces.py` is the shape precedent — `@runtime_checkable`, `...` bodies, no ABCs.
- **FR-24 is enforced structurally, not documented:** every write-side port method requires an
  etag. `create_support_js` takes a required `if_match: str`; `write_files` / `copy_files`
  validate that *every* entry in `files` carries `if_match` (or `leaf_if_match` for a folder
  dest) and raise `UnconditionalWriteError` otherwise. `read_file` takes an optional
  `if_none_match` (a first read legitimately has no prior etag).
- **NFR-04 is enforced by construction:** `render_preview` returns a `PreviewRef` frozen
  dataclass that has **no `serve_url` field at all**. Additionally `sanitize_payload()` in
  `base.py` recursively drops any `serve_url` key and redacts any string containing
  `claudeusercontent.com`, and is applied to **every** tool response before it crosses the
  adapter boundary (defence in depth for tool payloads this story doesn't model).
- The transport port is **synchronous**. `McpTransport` bridges to the async SDK with one
  `asyncio.run()` per call (rationale + evidence in Design Notes). The `mcp` import is lazy —
  inside the calling function, mirroring `pyforge.atlas.mcp.server`'s lazy `from fastmcp import`.
- Credentials resolve through an **injectable** seam, copying warden's
  `resolve_forge(env=...)` convention (`actuator.py:235-263`):
  `resolve_design_credential(*, credentials_path: Path | None = None, env: Mapping[str, str] |
  None = None)`. Reads `~/.claude/.credentials.json` → `designOauth.accessToken`; honours a
  `HERALD_DESIGN_CREDENTIALS` path override. Missing file/key or `expiresAt` in the past →
  `AuthError` naming the `/design-login` remediation.
- No token value may ever be logged, returned in a message, or written to disk.
- This story resolves the architecture spine's Deferred open question ("whether `mcp` lands as
  a `[package.run-dependencies]` entry or stays feature-level") → **run-dependency**: `mcp` is a
  genuine runtime dependency of the shipped package. Wire it in all three manifests.
- Match Story 1.1 / warden conventions exactly: `from __future__ import annotations` in every
  module except `__init__.py`; plain-prose module docstrings citing Story/FR/AD; frozen
  dataclasses for value objects; hand-written fakes in tests (warden's suite uses
  `unittest.mock` **zero** times); ruff-format defaults (88 cols, double quotes).

**Block If:**
- The live spike fails in a way that is neither a clean success nor a clean, attributable
  "cannot reach the server outside a session" (e.g. the credential is expired and cannot be
  re-minted non-interactively). Either verified outcome is acceptable per the AC; an
  *indeterminate* outcome is not — HALT rather than guess which transport V1 ships.

**Never:**
- No `bridge.py`, `state.py`, `registry.py`, `deck_pipeline.py`, `models.py`, no
  `seed`/`pull`/`status`/`watch` CLI parsers — Stories 1.4–1.6+. `cli.py` is **untouched**.
- No `AgentSdkTransport` — that is Story 1.3, and this spike's success means 1.3 is the
  fallback, not the shipped default.
- No OAuth **refresh** and no write-back to `~/.claude/.credentials.json`. NFR-05 says Herald
  reuses the stored credential and introduces no new credential storage; minting/refreshing is
  the Claude Code CLI's job. An expired token is a clean `AuthError`, not a self-heal attempt.
- No exit-code map and no CLI-boundary error catching — AD-6 assigns those to Story 1.4.
  `errors.py` is created here with only the root plus the transport-scoped subset 1.2 needs.
- No live network in the default test gate. No writes to any Design project (the spike is
  read-only: `initialize`, `list_tools`, `get_claude_design_prompt`).
- Do not touch `src/shared/packages/pyforge-warden/` or `pyforge-atlas/` — read-only precedents.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Protocol conformance | `McpTransport` instance | `isinstance(t, DesignTransport)` is `True` | No error expected |
| Preview sanitization | `render_preview` response containing `serve_url`, `open_url`, `expires_at` | `PreviewRef(open_url=..., expires_at=...)`; the tokenized URL is absent from every field and from `repr()` | No error expected |
| Generic payload scrub | any tool response with a nested `serve_url` or a `claudeusercontent.com` string | key dropped / value redacted before return | No error expected |
| Full read | `read_file` returning `<untrusted-project-content path="p" etag="E">…</untrusted-project-content>` + trailer | `FileRead(path="p", etag="E", body=<entity-decoded>, unchanged=False)`; trailer note stripped | No error expected |
| Unchanged read | `read_file` with matching `if_none_match` → `{"unchanged":true,"etag":"E","path":"p"}` | `FileRead(path="p", etag="E", body=None, unchanged=True)` | No error expected |
| Missing path | `read_file` on absent path → `isError=True`, text `read file: file not found` | raise `TransportCallError` naming tool + message | `TransportCallError` |
| Unconditional write | `write_files` with a `files` entry lacking `if_match` | raise before any network call | `UnconditionalWriteError` |
| No credential | credentials file absent / `designOauth` key missing | raise naming `/design-login` | `AuthError` |
| Expired credential | `designOauth.expiresAt` in the past | raise naming `/design-login`; no refresh attempted | `AuthError` |
| Server unreachable | SDK connection/HTTP failure | raise naming the endpoint; no token in message | `TransportUnreachableError` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- Story 1.1 skeleton; **read-only reference** for docstring/typing style. Not modified.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py:241-248` -- `@runtime_checkable Protocol` + frozen-dataclass seam precedent to mirror
- `src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py:134-146,235-263` -- `ForgeClient` port-with-injectable-adapter + `resolve_forge(env=...)` credential convention to copy
- `src/shared/packages/pyforge-warden/tests/conftest.py:134-246` -- socket-deny harness precedent (herald gets a smaller marker-carved variant)
- `_bmad-output/planning-artifacts/specs/spec-design-code-bridge/bridge-protocol.md` -- the 8-tool sequence + Modernist id `fbc1d6c8-b35f-4df6-9044-a64d2675427b` + pilot project ids
- `_bmad-output/planning-artifacts/architecture/architecture-pyforge-herald-2026-07-25/ARCHITECTURE-SPINE.md` -- AD-3 (port), AD-4 (determinism), AD-6 (errors), Deferred § (the `mcp` placement question this story closes)
- `pixi.toml:1166-1170` -- `[feature.pyforge-herald.dependencies]`, insertion point for `mcp`
- `src/shared/packages/pyforge-herald/pixi.toml:27-29` -- `[package.run-dependencies]`, self-documented as the Story 1.2 insertion point
- `docs/reference/library-llms-full.md:461` -- `mcp (>=1.28.1)` already catalogued, so adding it creates **no** `llms-full-check` drift (verified)

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/errors.py` -- create -- `HeraldError(Exception)` root plus the transport-scoped subset this story raises: `TransportError(HeraldError)`, `AuthError(TransportError)`, `TransportUnreachableError(TransportError)`, `TransportCallError(TransportError)`, `UnconditionalWriteError(TransportError)`. Docstring states Story 1.4 extends this file with the conflict errors + exit-code map (AD-6); no exit-code map here.
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/__init__.py` -- create -- re-export `DesignTransport`, the result dataclasses, and `McpTransport` so `bridge-core` (1.4) imports the port from one place
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py` -- create -- `@runtime_checkable class DesignTransport(Protocol)` with the 8 methods (keyword-only args, `...` bodies); frozen dataclasses `ProjectRef(project_id, url)`, `PlanHandle(plan_token, base_etags)`, `FileRead(path, etag, body, unchanged)`, `PreviewRef(open_url, expires_at)` (**no `serve_url` field**); `ToolResult(text, is_error)`; `ToolCaller` Protocol (the injectable low-level seam); `sanitize_payload(obj)` and `parse_read_response(text)` as the shared adapter invariants Story 1.3 reuses
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py` -- create -- `DesignCredential` frozen dataclass; `resolve_design_credential(*, credentials_path=None, env=None)`; `McpTransport` implementing all 8 port methods (marshal → `_call` → `sanitize_payload` → typed result), FR-24 write validation, `DESIGN_MCP_URL = "https://api.anthropic.com/v1/design/mcp"`, `MODERNIST_DESIGN_SYSTEM_ID`, and `_call_via_mcp_sdk` doing one `asyncio.run()` per call with a **lazy** `mcp` import, mapping SDK/connection failures to `TransportUnreachableError`
- [x] `src/shared/packages/pyforge-herald/src/pyforge/herald/py.typed` -- create -- empty marker, mirroring `pyforge/warden/py.typed`; this story is the first to ship a typed public interface
- [x] `src/shared/packages/pyforge-herald/tests/conftest.py` -- create -- autouse socket-deny fixture (patch `socket.socket.connect`/`create_connection`/`getaddrinfo` to raise a `RuntimeError` subclass, **not** `OSError`, per warden's rationale) carved out for tests marked `live`; a `fake_caller` factory fixture recording `(tool, arguments)` and returning canned `ToolResult`s; a `credentials_file` factory writing a fake `designOauth` blob under `tmp_path`
- [x] `src/shared/packages/pyforge-herald/tests/test_transport_base.py` -- create -- cover the I/O matrix rows owned by `base.py`: protocol conformance, `sanitize_payload` (nested `serve_url` drop + `claudeusercontent.com` redaction), `parse_read_response` full/unchanged forms, and that `PreviewRef` has no `serve_url` attribute
- [x] `src/shared/packages/pyforge-herald/tests/test_mcp_transport.py` -- create -- cover the remaining I/O matrix rows against the injected fake caller (no network): all 8 methods marshal the right tool name + argument keys (asserting `get_design_prompt` → tool `get_claude_design_prompt`), FR-24 `UnconditionalWriteError` for each write method, `render_preview` returning a serve_url-free `PreviewRef`, `read_file` full/unchanged/not-found, and every `resolve_design_credential` failure mode
- [x] `src/shared/packages/pyforge-herald/tests/test_live_design_spike.py` -- create -- the FR-21 re-runnable proof, `@pytest.mark.live` + `skipif` on `HERALD_LIVE_DESIGN` being unset (so the default gate never egresses): resolve the real credential, `McpTransport().get_design_prompt(design_system_id=MODERNIST)`, assert a non-empty prompt and that no `claudeusercontent.com` string is present
- [x] `src/shared/packages/pyforge-herald/pyproject.toml` -- edit -- add `dependencies = ["mcp>=1.28.1"]` to `[project]` and register the `live` marker via `[tool.pytest.ini_options] markers` (warden's `pyproject.toml:32-41` is the shape)
- [x] `src/shared/packages/pyforge-herald/pixi.toml` -- edit -- add `mcp = ">=1.28.1"` to `[package.run-dependencies]`, replacing the "Story 1.2+ deps land here" placeholder comment with the real entry
- [x] `pixi.toml` (root) -- edit -- add `mcp = ">=1.28.1"` to `[feature.pyforge-herald.dependencies]` so the lean env can import it
- [x] `pixi.lock` -- regenerate -- extend the `pyforge-herald` env with `mcp` and its transitive deps. The known worktree blocker (`bmad-ui`'s absent local `build_artifacts/linux64` channel forces a whole-workspace re-solve to fail) is resolved exactly as Story 1.1's repair pass did: create empty structurally-valid `repodata.json` stubs under `build_artifacts/linux64/{linux-64,noarch}/`, then run the gate unfrozen. Confirm no environment is dropped from the lock.

**Acceptance Criteria:**
- Given the `DesignTransport` protocol and `McpTransport`, when `pixi run -e pyforge-herald pyforge-herald-test` runs, then every test passes and no test opens a network socket (the deny fixture is active for all unmarked tests)
- Given a valid stored `/design-login` credential, when the live spike is run non-interactively as `HERALD_LIVE_DESIGN=1 pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_live_design_spike.py`, then `get_design_prompt` for the Modernist design system returns a non-empty prompt from a plain Python process outside any Claude Code session — the FR-21 primary-path proof
- Given the spike outcome, when the run completes, then the spec's Verification section records it as an explicit, dated finding (primary path proven → Story 1.3's `AgentSdkTransport` is the fallback, not V1's shipped default) and the architecture spine's Deferred `mcp`-placement question is recorded as closed in favour of `[package.run-dependencies]`
- Given the dependency wiring, when `pixi run -e pyforge-herald pyforge-herald-build` runs, then both the `.conda` and the wheel+sdist build, and the built metadata declares the `mcp` runtime dependency
- Given the manifest edits, when `pixi run -e local-recipes llms-full-check` runs, then it reports no **new** drift finding beyond the pre-existing `pyforge-herald` `undocumented-dep` entry inherited from Story 1.1

## Spec Change Log

## Review Triage Log

### 2026-07-25 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 17: (high 2, medium 5, low 10)
- defer: 4: (medium 2, low 2)
- reject: 12: (high 0, medium 0, low 12)
- addressed_findings:
  - `[high]` `[patch]` **`read_file` silently truncated large files.** The server caps a read at 256 KiB and marks a partial read on the wrapper with `lines="A-B"` / `total_lines`; `parse_read_response` parsed those attributes and then discarded them, so a truncated body came back with `unchanged=False` and a valid-looking etag — indistinguishable from a complete read, and the etag would then have licensed a whole-file overwrite in the other direction. **Confirmed live against the real 411,764-byte `Warden Infographic standalone.html`** (the exact file `bridge-protocol.md` scopes for Story 2.4): it returns 206,829 chars with `lines="1-208" total_lines="212"`. `FileRead` gained `first_line`/`last_line`/`total_lines` + a `truncated` property (fails closed when the window is unparsable), and `read_file` gained `offset`/`limit` on both the protocol and the adapter. Re-verified live: the file now reports `truncated=True`, and `offset=209` returns lines 209–212.
  - `[high]` `[patch]` **The design-system prompt was being annihilated.** `_call_text` ran `sanitize_payload` over the whole prompt string, and `sanitize_payload` replaces an *entire* string that merely mentions the tokenized host — so the real 33,985-character Modernist prompt was replaced by a 33-character placeholder. This is FR-21's own gate and Story 1.6's mandatory pre-write step. Caught by this pass's own strengthened live assertion (the `[low]` P15 fix below), which failed on the first re-run. Verified live that the prompt names the host exactly once, in the rule forbidding it, and carries no tokenized URL (no `?t=` shape). `_call_text` no longer scrubs prose; regression test added.
  - `[medium]` `[patch]` `_raw_text` interpolated the raw server error text into `TransportCallError` — the one path a `serve_url` could ride into an operator-visible, log-bound message (NFR-04). Now sanitized.
  - `[medium]` `[patch]` `read_file` whole-body redaction would have replaced a legitimate deck body mentioning the host with a 40-char constant and written it over the repo's prototype. Body is content, not envelope — exemption documented so it is not "restored". (Measured: 0 of 77 live deck files contain the host, so this was latent, not active.)
  - `[medium]` `[patch]` FR-24 validation was a truthiness test, so `if_match=5`/`True`/`["x"]` all passed; a generator `files` was drained by validation and marshalled as `[]` (a silent no-op write); a non-Mapping entry raised a bare `AttributeError`; an empty `files` was a no-op reported as success. All hardened, and `require_conditional` moved to `base.py` as public — it is the third shared adapter invariant and Story 1.3 would otherwise have imported a sibling's private.
  - `[medium]` `[patch]` Every SDK failure collapsed to `TransportUnreachableError` with an `ExceptionGroup`'s useless "unhandled errors in a TaskGroup" text, so no HTTP 401 could ever produce `AuthError` — leaving `bridge-protocol.md`'s "Halt on auth error, never retry a 401" unreachable for Story 4.3. Group leaves are now flattened into the message and 401/403 maps to `AuthError`; token scrubbing runs before the status scan.
  - `[medium]` `[patch]` Test harness: `connect_ex`/`sendto`/`gethostbyname` were unpatched escape hatches; the liveness self-test never exercised `socket.socket.connect`; and no guard stopped a non-`live` test from reading the developer's real `~/.claude/.credentials.json`. All closed (the deny fixture now also points the credentials-path env var at a missing `tmp_path`).
  - `[low]` `[patch]` ×10 — body extraction used `rfind` on the closing tag (a trailer naming the tag would be swallowed into the body); `asyncio.run` from a running loop was reported as an endpoint outage; `str(None)` produced a truthy 4-char `"None"` etag; a non-Mapping `base_etags` escaped the error hierarchy; an unrecognised `scope` silently degraded to a paths plan authorizing nothing; `expiresAt: true` hard-expired a good credential (`bool` is an `int` subclass) and NaN/Inf escaped as `ValueError`; host matching was case-sensitive and skipped mapping keys; the live spike's NFR-04 assertion was vacuous; the spine's *Etag headers* convention row contradicted `read_file`'s deliberately-optional `if_none_match`; +60 regression tests.

Deferred (4): the port has no `list_files`/`delete_files` though the live `finalize_plan`/`copy_files` schemas direct callers to them for etags (AD-3 fixes the 8-tool surface, so widening it is not this story's call); `FileRead` drops the server's `untrusted-project-content` provenance marking; a conflicted write returns as an ordinary success `Mapping` (correct hexagonal layering — AD-6 assigns conflict *interpretation* to Story 1.4's bridge-core — but recorded so 1.4 does not assume it raises); `_call_tool_async`'s header construction and content-block filter are covered only by the opt-in live spike. All four appended to `deferred-work.md`.

Rejected as noise (12, all verified non-issues or by-design): the suggestion to swap `_decode_entities` for `html.unescape` would **introduce** a bug — the server documents escaping exactly `& < >`, so unescaping `&quot;`/`&#39;` would corrupt any source file legitimately containing them; `etag` not entity-decoded while `path` is (etags are numeric, paths can contain `&`); `PlanHandle` unhashable (cosmetic); `sanitize_payload` not handling bytes/sets/cycles (JSON cannot produce them); "lazy `mcp` import contradicts the hard runtime dep" (different concerns — import cost/testability vs runtime correctness; both hold); the root feature's `mcp` entry called redundant (it makes the lean env explicit); "`deferred-work.md` does not exist" — **verified false**, it is present via the gitignored artifact symlink the reviewer could not resolve; duplicated fake-token constant between conftest and a test module; `plan_token=None` routing to an interactive grant (the real flow always supplies one); `__protocol_attrs__` called brittle (it is the only thing that actually pins the 8-tool surface — kept deliberately); the `maintenance` PR label (a real repo rule, but a process step at PR time, not a code finding — noted in the result); one copy-edit nit.

All 17 patches applied; full suite re-verified green after patching (**123 passed, 2 skipped**, net +60 tests), live spike **2 passed**, `ruff format --check` and `ruff check` clean from the package root.

### 2026-07-25 — Review pass (independent follow-up, dev attempt 3)

Context: the loop's verify gate failed on the pre-existing worktree path-length panic (below),
not on the code, and the branch was rolled back to baseline. The reviewed commit `73e6ef5c21`
was restored intact and re-verified; this is the independent follow-up review the previous pass
recommended, run against the **patched** code it had never seen.

- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 5, low 6)
- defer: 10: (medium 5, low 5)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[medium]` `[patch]` **`FileRead.truncated` failed *open* in one direction.** The property
    documents "coverage that cannot be proven is not assumed" and honoured it only when
    `total_lines` was known: a declared `lines="1-208"` window with an absent or unparsable
    `total_lines` reported `truncated=False`. That is the dangerous direction — the window would
    be written over the prototype as if whole, and its etag would then license an `if_match`
    overwrite of the lines outside it, the exact data-loss path the previous pass added the
    window for. The rule is now symmetric; only an answer declaring *no* window counts as whole.
  - `[medium]` `[patch]` **A bare "401" anywhere in a failure message raised `AuthError`.** The
    text fallback scanned for the substrings `401`/`403`, which occur in ordinary transport
    noise — `[Errno 101] ... 2607:f8b0:4003::401`, `Mcp-Session-Id=8f403abc401d`. Since
    `bridge-protocol.md` § Watch parameters halts on an auth error and never retries, one
    transient blip would have stopped `herald deck watch` permanently and told the operator to
    re-run `/design-login` on a perfectly good credential. The scan now requires HTTP context
    (`unauthorized`/`forbidden`, or a status keyword adjacent to the code); the unambiguous
    `.response.status_code` path is unchanged and still preferred.
  - `[medium]` `[patch]` `finalize_plan(project_id=...)` with the default empty `writes`/`deletes`
    marshalled `writes: [], deletes: []` — a plan authorizing nothing — and returned a
    valid-looking token. This is the identical failure the adjacent unknown-scope guard exists to
    prevent, reached the other way; it now raises before the call.
  - `[medium]` `[patch]` A `finalize_plan` answer with no `plan_token` produced
    `PlanHandle(plan_token="")`, which is marshalled as an explicit empty `plan_token` on every
    later write rather than omitted. Now refused at the boundary.
  - `[medium]` `[patch]` A `read_file` `if_none_match` short-circuit carrying no etag produced
    `FileRead(etag="")`. The caller stores that as the next poll's `if_none_match`, silently
    converting the cheap etag poll into a full download every cycle with nothing to see. Now
    refused: the etag is the entire point of the short-circuit.
  - `[low]` `[patch]` `sanitize_payload` scrubbed non-string mapping keys, so a tuple key returned
    an unhashable list and raised a bare `TypeError` out of a function the package exports —
    escaping the `HeraldError` hierarchy that AD-6's CLI boundary catches. Non-string keys are now
    passed through (JSON cannot produce one).
  - `[low]` `[patch]` `McpTransport(url=...)` accepted a non-https endpoint, which would have put
    the stored `/design-login` bearer token on the wire in cleartext. Refused in the constructor.
  - `[low]` `[patch]` A missing/broken `mcp` install surfaced as "could not reach the
    claude-design MCP endpoint", sending the operator to look at the network. `ImportError` now
    maps to `TransportError` naming the dependency.
  - `[low]` `[patch]` Token scrubbing was an exact-substring replace, so a library that elides a
    long `Authorization` header would leave a token *prefix* in the raised message — still
    credential material, and the spec's rule is absolute. The longest prefix of >=12 characters is
    now scrubbed too.
  - `[low]` `[patch]` `docs/reference/library-llms-full.md` § 11 asserted "All in
    `local-recipes`", which this story made false for `mcp`. `llms_full_check.py` leaves
    env-membership prose deliberately unchecked, so the gate structurally could not catch it.
  - `[low]` `[patch]` The environment note below claimed `64 passed, 2 skipped` — the pre-patch
    figure, stale after the previous pass added 60 tests. Corrected, and re-measured this pass.

Deferred (10): `McpError` (a server-*answered* JSON-RPC failure) collapses into
`TransportUnreachableError`, so "reached and refused" reads as "never reached"; 429/5xx have no
class distinct from an outage, so a caller cannot tell back-off from give-up; no request timeout
is set on the SDK session or call; `mcp>=1.28.1` has no upper bound while the adapter binds SDK
internals only the live spike executes; the credential is cached for the process lifetime with no
re-read after an external `/design-login`; `AuthError` subclasses `TransportError`, so Story 4.3's
obvious retry predicate would swallow the one error that must halt; `sanitize_payload` collapses
two distinct host-naming string keys onto one entry; `_as_text`/`_as_optional_text` are still
cross-module privates that Story 1.3 will need; the spine's amended *Etag headers* row asserts an
`if_none_match` obligation nothing enforces; and Story 1.1's spec is still unpromoted to the
tracked specs dir. All ten appended to `deferred-work.md` with reproduction detail. The unbounded
`mcp` pin was deliberately *not* patched: capping it forces a `pixi.lock` regeneration, and the
lock was being rebuilt out-of-band on `build/pyforge-herald-1-2` while this pass ran.

Rejected as noise (10, verified non-issues or by-design): "validation drains a generator `files`"
— **verified false**, both write methods materialize with `list(files)` before validating, which
the previous pass fixed; `except Exception` not catching a `BaseExceptionGroup` (its leaves are
`CancelledError`/`KeyboardInterrupt`, which must propagate, not become a transport error); a
non-JSON answer *after* an applied write (the server's documented contract is JSON, and the
proposed change is message-only); `RecursionError` from deeply nested JSON; client-side bounds on
`offset`/`limit` (inventing them risks contradicting unobserved server semantics); an `open_url`
host allowlist; `from None` suppressing the SDK traceback (deliberate — the flattened leaves carry
the cause and the raw traceback is the one place unscrubbed material could ride); the `_call_text`
NFR-04 exemption (deliberate and evidence-backed — scrubbing there destroyed the whole 33,985-char
prompt); the body's single-newline framing strip (documented server framing; changing it on
speculation risks corrupting real reads); and the `pixi.lock` `bmad-ui` ephemeral-channel URL,
already deferred by the previous pass.

All 11 patches applied with 17 new regression tests; full suite green (**140 passed, 2 skipped**,
net +17), live spike **2 passed**, `ruff format --check` and `ruff check` clean.

## Design Notes

**Spike outcome is already ground truth — do not re-derive it.** The primary path was proven
live during planning (2026-07-25 ~13:55 UTC) with `mcp` 1.28.1 from a plain
`.pixi/envs/local-recipes/bin/python` process: `initialize` returned
`serverInfo(name='Claude Design', version='0.1.0')`, `list_tools` returned 23 tools including
all 8 port tools, and `get_claude_design_prompt(design_system_id=Modernist)` returned a
33,985-character prompt. **FR-21 holds; FR-22's fallback is not V1's default.**

**Connection recipe (verified):** POST `https://api.anthropic.com/v1/design/mcp` via
`mcp.client.streamable_http.streamablehttp_client`, headers `Authorization: Bearer
<designOauth.accessToken>`, `anthropic-version: 2023-06-01`,
`X-Anthropic-Client: claude-cli-design-tool`. The SDK supplies `Accept` and `Mcp-Session-Id`.

**Why one `asyncio.run()` per call rather than a persistent session.** The obvious worry is
losing session continuity, but the live schemas show there is no session-scoped state to lose:
`plan_token` and `if_match`/`if_none_match` etags are **explicit parameters** on every
subsequent call, not implicit server-side session state. A persistent session would need a
background event loop plus a single owning task (anyio cancel scopes forbid entering and
exiting `streamablehttp_client` from different tasks) — real concurrency machinery, and a new
`anyio` dependency that `llms-full-check` would flag as `undocumented-dep`. Cost of the simple
path is one extra initialize round-trip per call, on commands that make a handful of calls.
Note the trade in `deferred-work.md` as an available optimization if `watch` ever needs it.

**Verified wire formats** (these are exact — do not guess):
- `read_file` full: `<untrusted-project-content path="P" etag="E">\n<body>\n</untrusted-project-content>\n(The body above is HTML-entity-escaped: …)` — parse the attributes, strip the trailing note, then decode `&amp; &lt; &gt;` → `& < >` (decode `&amp;` **last**).
- `read_file` unchanged: `{"unchanged":true,"etag":"E","path":"P"}`.
- `read_file` missing: `isError=True`, text `read file: file not found`.
- `render_preview`: `{expires_at, note, open_url, serve_url}` — `open_url` is the safe
  `claude.ai/design/p/<id>?file=<path>` link; `serve_url` is a `*.claudeusercontent.com` URL
  carrying a project-scoped token that expires in ~3600s. **It is the only tool that returns
  one**, and the server's own `note` says never to surface it.
- `create_project` returns `{project_id, url}`; `get_project` returns `{id, name, sharing, type, url}` — both already `claude.ai/design/...`-safe.
- `write_files.files[]`: `{path, data, encoding?: "base64", if_match?, local_path?}`;
  `copy_files.files[]`: `{src…, dest, if_match?, leaf_if_match?}`; `finalize_plan`:
  `{project_id, writes: [str], deletes: [str], scope}`. `if_match: "0"` asserts the path does
  not exist.

**Port method name ≠ MCP tool name in exactly one place:** the port's `get_design_prompt`
(named by AD-3 and the epics AC) maps to the MCP tool `get_claude_design_prompt`. That
translation is the adapter's job and must be asserted in tests.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: all tests pass (5 existing smoke + the new transport tests); the live spike test reports as skipped
- `HERALD_LIVE_DESIGN=1 pixi run -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/test_live_design_spike.py -q` -- expected: 1 passed; this is the FR-21 proof
- `pixi run -e pyforge-herald herald deck --help` -- expected: exit 0, unchanged from Story 1.1 (proves `cli.py` was not disturbed)
- `pixi run -e pyforge-herald pyforge-herald-build` -- expected: `.conda` in `dist-conda/` and wheel+sdist in `dist/`, with `mcp` declared as a runtime dependency
- `pixi run -e local-recipes llms-full-check` -- expected: exactly the one pre-existing `pyforge-herald` `undocumented-dep` finding, no new ones
- `git diff --stat pixi.lock` -- expected: `pyforge-herald` env gains `mcp` + transitive deps; **no environment key removed** (diff the environment key set explicitly)

**Manual checks:**
- `grep -r claudeusercontent src/shared/packages/pyforge-herald/` returns hits only in test fixtures and the sanitizer's own pattern constant — never in a return path.
- No token material anywhere: `git diff` carries no `sk-ant-` string.

### Spike finding (2026-07-25) — FR-21 PRIMARY PATH PROVEN

**The pure-MCP-client primary transport works from a plain, non-interactive Python process.**
Verified twice: first as a throwaway probe during planning, then as the shipped, re-runnable
`tests/test_live_design_spike.py` (`2 passed`, live against `api.anthropic.com`). `initialize`
answered `serverInfo(name='Claude Design', version='0.1.0')`, `list_tools` returned 23 tools
including all 8 port tools, and `get_claude_design_prompt(design_system_id=<Modernist>)`
returned a 33,985-character prompt — no Claude Code session, no agent harness, only the
credential `/design-login` had already stored.

Consequences, both recorded:
- **FR-21 holds.** `McpTransport` is V1's shipped transport; Story 1.3's `AgentSdkTransport`
  (FR-22) is the fallback, **not** V1's default. Story 1.3 should be scoped accordingly.
- **The architecture spine's Deferred `mcp`-placement question is CLOSED** in favour of
  `[package.run-dependencies]` — `mcp` is a genuine runtime dependency of the shipped package.
  Struck through and annotated in `ARCHITECTURE-SPINE.md` § Deferred. Confirmed in the built
  artifacts: the `.conda`'s `info/index.json` depends carries `mcp >=1.28.1` and the wheel's
  METADATA carries `Requires-Dist: mcp>=1.28.1`.

### Verification environment note (2026-07-25) — the gate cannot run in THIS worktree

`pixi run -e pyforge-herald ...` cannot execute here, and **this is pre-existing, not caused by
this story**. `pixi-build-python` panics with an unchecked `usize` underflow
(`end byte index 18446744073709551595 is out of bounds for string of length 260`,
`crates/pixi_build_backend/src/tools.rs:461`): it slices a placeholder at
`255 - len(build_dir)`, and the fixed 73-byte build-dir suffix means the workspace root must be
≤173 bytes. This worktree's root is **194 bytes** — 21 over, matching the `2^64 − 21` underflow
exactly. Story 1.1's worktree slug was 27 chars shorter, which is why it stayed under the ceiling.

**Proven pre-existing:** with every story change stashed (`git stash -u`, tree clean at
`2f9c635f7b`), the same command fails identically — and it fails while solving the *unrelated*
`pyforge-warden` / `pyforge-atlas` environments, which this story never touches.

All Verification commands above were therefore run in a short-path `git worktree`
(`/home/rxm7706/h2`, 16 bytes) holding a byte-identical copy of this tree — mirrored status
verified identical before running, worktree removed afterwards. Results: `pyforge-herald-test`
**140 passed, 2 skipped** (123 before this pass's 17 regression tests; the "64" first written here
predated the previous pass's 60); live spike **2 passed**; `herald deck --help` **exit 0**;
`pyforge-herald-build` produced both artifacts; `llms-full-check` output **byte-identical to the
pre-change baseline** (the single `pyforge-herald undocumented-dep` finding is inherited from
Story 1.1); `pixi.lock` environment-key set **unchanged at 14, none dropped**. The committed
lock's `bmad-ui` channel URL points at *this* worktree (Story 1.1's pattern), with no
short-path-worktree reference anywhere.

**For the bmad-loop verify gate:** it will fail here with the panic above, not a test failure.
Re-verify via a short-path worktree, or after merge to `loop/pyforge-herald`. Logged in
`deferred-work.md` with the reproduction recipe.

### Verification re-run (2026-07-25, dev attempt 3)

Attempt 1 produced and committed the whole story at `73e6ef5c21`; the loop's verify gate then hit
the path-length panic above, classified it as a code failure, and rolled the branch back to
baseline. The commit was restored by fast-forward (its parent *is* the baseline, so the restore is
byte-exact, not a re-derivation) and re-verified in a fresh short-path worktree
(`/home/rxm7706/hv`, 16 bytes) built from that exact commit, running the lock **`--frozen`**:

- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -> **123 passed, 2 skipped** on the
  restored commit, **140 passed, 2 skipped** after this pass's patches
- `HERALD_LIVE_DESIGN=1 ... pytest tests/test_live_design_spike.py` -> **2 passed** (FR-21
  re-proven live against `api.anthropic.com`, twice: before and after patching)
- `pixi run --frozen -e pyforge-herald herald deck --help` -> **exit 0** (`cli.py` undisturbed)
- built `.conda` `info/index.json` `depends` -> `['python >=3.12', 'python *', 'mcp >=1.28.1']`,
  confirming the run-dependency reaches the artifact (the package is rebuilt by the gate itself)
- `pixi.lock` environment keys re-diffed baseline-vs-commit -> **14 before, 14 after, none
  dropped, none added**
- `ruff format --check` + `ruff check` from the package root -> clean

`llms-full-check` was not re-run this pass: it needs the `local-recipes` env, which is not
installed in the throwaway worktree, and the only catalog edit made here is prose inside § 11 —
the checker's own docstring declares env-membership prose unchecked, so it cannot change the
result. Attempt 1's byte-identical-to-baseline finding stands.

**Out-of-band note:** while attempt 3 ran, `73e6ef5c21` was merged into `loop/pyforge-herald`
(`f970307872`) and a `build/pyforge-herald-1-2` branch began a re-lock outside the loop. This
pass therefore touched **no manifest and no lock** — only source, tests, and one doc line — so
that in-flight re-lock stays valid.


## Auto Run Result

Status: **done**. FR-21's prove-or-kill spike resolves in favour of the **primary path**:
`McpTransport` is V1's shipped transport and Story 1.3's `AgentSdkTransport` (FR-22) is the
fallback, not the default. The architecture spine's deferred `mcp`-placement question is closed in
favour of `[package.run-dependencies]`.

**What this attempt did.** Attempt 1 implemented and reviewed the whole story and committed it at
`73e6ef5c21`. The loop's verify gate then failed on the pre-existing `pixi-build-python`
path-length panic (this worktree's root is 194 bytes against a 173-byte ceiling), classified it as
a code failure, and rolled the branch back to baseline — discarding a complete, green story.
Attempt 3 restored that commit by fast-forward (its parent *is* the baseline, so the restore is
exact), re-verified it in a short-path worktree, and then ran the independent follow-up review the
previous pass had recommended, against the patched code it had never seen.

**Files changed** (14 in the restored commit, 5 further in this pass):
- `transport/base.py` — the 8-tool `DesignTransport` Protocol, frozen result types, and the three
  shared adapter invariants (`sanitize_payload`, `parse_read_response`, `require_conditional`).
  This pass: `truncated` now fails closed in both directions; the `unchanged` read form requires an
  etag; non-string mapping keys are left unscrubbed.
- `transport/mcp_transport.py` — the adapter, the injectable credential seam, one
  `asyncio.run()`-scoped session per call. This pass: contextual (not substring) HTTP-status
  detection, an empty-plan guard, a `plan_token` guard, an https-only endpoint guard, `ImportError`
  split out from "unreachable", and prefix-aware token scrubbing.
- `transport/__init__.py`, `errors.py`, `py.typed` — the public seam, the transport-scoped error
  subset (Story 1.4 adds the conflict errors and exit-code map per AD-6), and the typing marker.
- `tests/conftest.py` + `tests/test_transport_base.py` + `tests/test_mcp_transport.py` +
  `tests/test_live_design_spike.py` — egress-deny harness, fakes, the I/O matrix, and the
  re-runnable FR-21 proof. +17 regression tests this pass.
- `pyproject.toml`, `pixi.toml` (x2), `pixi.lock` — `mcp>=1.28.1` as a run-dependency. **Untouched
  this pass**, deliberately: a re-lock was in flight out-of-band on `build/pyforge-herald-1-2`.
- `ARCHITECTURE-SPINE.md` — the deferred `mcp`-placement question struck through and closed.
- `docs/reference/library-llms-full.md` — § 11's "All in `local-recipes`" corrected for `mcp`.
- `planning-artifacts/specs/spec-1-2-...md` — this spec promoted to the tracked tier per CLAUDE.md's
  2026-07-25 durable-story-spec convention.

**Review findings.** Two independent passes. First: 17 patched, 4 deferred, 12 rejected. This
follow-up: 11 patched (5 medium, 6 low), 10 deferred, 10 rejected — including one reviewer claim
verified **false** (the generator-drain, already fixed by the previous pass).

**Verification.** `pyforge-herald-test` **140 passed, 2 skipped**; live FR-21 spike **2 passed**
against the real endpoint; `herald deck --help` exit 0; built `.conda` declares `mcp >=1.28.1`;
`pixi.lock` environment keys 14 before and after with none dropped; ruff format + lint clean. All
run from a short-path worktree on the lock `--frozen`, because the gate cannot execute in this
worktree at all (see the environment note above).

**Residual risks.**
1. **The loop's verify gate will fail here again.** It is the path-length panic, not the code, and
   it is reproducible on the pristine baseline with every story change stashed. Re-verify from a
   short-path checkout or after merge. The durable fix (cap the generated worktree slug) is in
   `deferred-work.md`.
2. **Three new hard-fail paths.** The `plan_token`, empty-plan, and etag-less-`unchanged` guards
   turn previously-degraded-but-usable answers into `TransportCallError`. Each refuses a shape the
   observed server does not produce, but none has been seen in the wild — if the server does emit
   one, Herald now stops where it used to limp. This is why a follow-up review is still
   recommended.
3. **The SDK binding is only covered by the opt-in live spike**, and the `mcp` pin has no upper
   bound. Both deferred, and they compound: a breaking major release would pass the entire default
   gate.
4. `AuthError` subclasses `TransportError`, so Story 4.3 must catch it first or the watch loop will
   retry a 401 that `bridge-protocol.md` says must halt. Deferred and flagged for that story.
