---
title: "MCP service-face runtime — Tasks availability, protocol revisions, and a live incompatibility"
chain: "pyforge-unifying-strategy"
type: "technical"
created: "2026-08-24"
updated: "2026-08-24"
status: "ready"
decision: "What CAP-4's service faces are built on, which protocol revisions they accept, and how long operations survive disconnect"
answers:
  - mcp-tasks-runtime
  - mcp-client-revision
---

# MCP service-face runtime

Two open questions closed, and a third thing found on the way: **the estate's MCP servers cannot
start in the current environment.** That defect and the architecture answer turn out to be the same
problem, which is the most useful thing in this document.

---

## Part A — Is there a server-side Tasks runtime?

**Verdict: no, and it is not close.**

The official `mcp` Python SDK 2.0.0 — the current stable line, and what conda-forge ships — states
it verbatim under *Known gaps*: **"The tasks extension (SEP-2663) is not part of this release."**
The SDK passes the official conformance suite on both sides *except* the tasks suite, which is
baselined as known-failing. The tracking issue remains open.

The history matters for how we write the requirement. Tasks first shipped as an experimental
**core** feature in revision `2025-11-25` (SEP-1686). That design was withdrawn and the
implementation deleted from the SDK — roughly 13k lines removed rather than maintained against a
moving target. It returned as **SEP-2663**, status *Final*, which re-lands it as an optional,
opt-in, versioned **extension** (`io.modelcontextprotocol/tasks`) rather than core protocol.
Blocking `tasks/result` became polling `tasks/get`; `tasks/update` was added; `tasks/list` was
dropped because it cannot be scoped safely against a stateless core.

The only working server-side runtime in **any** language is `fastmcp-tasks`, whose own README says
so: the extension "ships in the ecosystem as a schema and a prose specification — no language SDK
provides a working runtime for it." It is `4.0.0b3` — a beta, tracking a draft schema it warns
"may still move at field level", requiring FastMCP 4 (also pre-release), built on Docket. Neither
`fastmcp-tasks` nor `docket` is on conda-forge, and conda-forge does not accept betas as stable
releases. **This is blocked upstream, not merely unqueued.**

### What FR-12 ships instead

CAP-4's success criterion — *an agent completes a multi-minute station operation across a simulated
ingress disconnect and still retrieves the result* — is shippable. It is only shippable **via the
Tasks extension** that is not. Those two things must be decoupled in the requirement text, or the
story blocks on upstream.

The pattern is a two-tool pair per station, implementing SEP-2663's lifecycle in application space:

1. `start_<operation>(...) -> {handle}` enqueues, persists an initial record, returns immediately.
   It must not hold the connection open — that is the entire point, and it also sidesteps the
   OpenShift `timeout client` constraint, because no long-lived stream exists to keep alive.
2. `get_<operation>(handle) -> {state, progress, result | error}` reads that record. **Any replica
   can serve it**, so this works behind plain round-robin ingress with no session affinity.
3. Handles are opaque, high-entropy and TTL'd. SEP-2663's own guidance is to treat a task ID as a
   capability, since without sessions anyone holding the ID can read the task.

Two properties make it cheap to retire later: the wire shape *is* the lifecycle Tasks standardizes,
and the durable store is the genuinely hard part — the extension only replaces the wire layer above
it. FastMCP's own migration note said exactly this, that having Docket already meant SEP-2663 was
"mostly a wire-layer swap rather than new infrastructure."

**Not substitutes.** Progress notifications (`ctx.report_progress`) travel down the live connection
and die with it — they solve "the operator sees a spinner", not "it survives a disconnect". Also
avoid sticky-session affinity (the `2026-07-28` core deliberately removed sessions) and home-grown
SSE reconnection with replay.

**Recommendation: record Tasks as a scheduled re-check, not a closed question.** The SEP is Final,
the SDK's pluggable extension API (SEP-2133) has landed, and the tracking issue is open
specifically to bring the extension in-repo. This plausibly resolves within the chain's lifetime.

---

## Part B — Which protocol revisions do we accept?

**Verdict: accept `2025-03-26` through `2026-07-28`.** Four handshake revisions plus the modern
one. This costs nothing — it is exactly what `mcp` 2.0.0 already does with no configuration.

Five revisions exist, confirmed from the installed package's own registry rather than inferred:
`2024-11-05`, `2025-03-26`, `2025-06-18`, `2025-11-25` are **handshake** revisions; `2026-07-28` is
**modern**. The split is the load-bearing part. Handshake opens with
`initialize`/`notifications/initialized` and carries an `Mcp-Session-Id`. Modern has **no handshake
at all** — every request carries its own version, identity and capabilities in `_meta`, mirrored
into the `MCP-Protocol-Version` header. Supporting both is "dual-era".

On the modern path, an unsupported version returns `UnsupportedProtocolVersionError` (`-32022`,
HTTP 400) with `data.supported` listing what the server speaks. Note this revision **renumbered**
the error codes — `-32001`/`-32003`/`-32004` became `-32020`/`-32021`/`-32022` — and stale values
still circulate in draft documentation.

The legacy failure mode is nastier and deserves an explicit invariant. A client sends its desired
version in `initialize`; if the server answers with a version the client has never heard of, **the
client aborts even when the server's version is newer**. A field report captured Claude Code
refusing with `Server's protocol version is not supported: 2026-07-28`.

### Two invariants worth binding

- **Never assert your own newest version in an `initialize` response** — echo the client's
  requested version whenever you can serve it.
- **Never select behavior from the client name**, only from the declared protocol version.
  User-agent sniffing becomes very tempting mid-migration and is always wrong.

### Client landscape

Mixed enough that pinning to `2026-07-28`-only would reject most of what we have. Claude Code's v2
runtime supports it, but asks **stdio** servers about the newer revision only when
`MCP_PROTOCOL_NEGOTIATION=auto` is set — and our servers are stdio, so handshake-era is the
realistic default. VS Code/Copilot and Zed sit at `2025-11-25`, Gemini CLI at `2025-06-18`.
**Cursor's revision is genuinely unpublished** — treat as unknown rather than assuming.

One data point argues against assuming slow uptake: an operator reported OpenAI Codex traffic
already declaring `2026-07-28` within two weeks of release, while Claude clients still opened with
`initialize`. So the range needs both ends, now.

---

## Part C — The live incompatibility, and why it decides Part B's implementation

**Every in-repo MCP server is broken in the `local-recipes` environment right now.** Reproduced
directly:

```
ImportError: cannot import name 'McpError' from 'mcp.shared.exceptions'. Did you mean: 'MCPError'?
```

`mcp` 2.0.0 renamed `McpError` to `MCPError`; `fastmcp` 2.14.3 imports the old name at module load,
so `import fastmcp` fails outright. Affected: `.claude/tools/conda_forge_server.py`,
`.claude/tools/gemini_server.py`, `pyforge/atlas/mcp/server.py`,
`pyforge/marshal/mcp/server.py`, `pyforge/herald/transport/mcp_transport.py`, and herald's
`test_bridge.py`.

### The obvious fix does not work

Raising the floor to `fastmcp >=3.4.7` (the version our own `recipes/fastmcp/recipe.yaml` carries)
looks right and is not. **Every conda-forge `fastmcp` 3.x build declares `mcp >=1.24.0,<2.0`** —
they exclude `mcp` 2.0.0 explicitly. Verified across all builds:

| fastmcp | declared `mcp` bound |
|---|---|
| 3.4.3 – 3.4.7 (all 3.x) | `>=1.24.0,<2.0` — **excludes 2.0** |
| 2.14.1 – 2.14.3 | `>=1.24` — **unbounded** |
| 2.13.3 | `>=1.19.0,<1.23,!=1.21.1` |

So **no `fastmcp` on conda-forge is compatible with `mcp` 2.0.0.** The 2.14.x line only *appears*
compatible because its upper bound is missing — a packaging defect, since 2.14.3 predates the
rename and should carry `<2.0` like its successors. The solver is being walked into a broken solve
by incorrect metadata, which is why this surfaced as a runtime `ImportError` rather than a solve
failure.

Both pins sit in the same table, `[feature.local-recipes.dependencies]`:
`fastmcp = ">=2.14.3"` and `mcp = ">=2.0.0"`. The doctor and herald features pin `mcp >=2.0.0`
without fastmcp, though herald's source imports fastmcp.

### Why this settles the architecture question

Part B says accept the full revision range. **conda-forge FastMCP cannot deliver the modern end of
it** — 3.4.x is handshake-era only; modern-era serving arrives in FastMCP 4, which is `4.0.0b3` and
unpackaged. Built on the official `mcp` 2.0.0 SDK directly, a server is dual-era for free: the same
`streamable_http_app()` answers both a 2025-era `initialize` and a 2026-era request with no flag
set.

So the live outage and the architecture recommendation are one decision:

- **Stay on FastMCP** → `mcp` must drop below 2.0, the estate is handshake-era only, and modern
  clients (Codex already sends `2026-07-28`) are rejected. Servers work again immediately.
- **Build on `mcp` directly** → dual-era as specified, but five modules move off FastMCP. That is
  CAP-4's own work rather than a pin change.

There is no third option that keeps both FastMCP and `mcp` 2.0.0, because no such pair is
published.

## Confidence and gaps

Verified directly rather than inferred: the `ImportError` (reproduced), every conda-forge `fastmcp`
build's `mcp` bound (registry API), the five protocol revisions (read from the installed package's
own registry), and the pixi table ownership of both pins.

High confidence from upstream: Tasks' removal from core and return as Final SEP-2663; the SDK's
"known gaps" statement and open tracking issue; `fastmcp-tasks` being the first working runtime, at
beta; the `-32022` negotiation rule and error renumbering.

Gaps worth naming. **Cursor's protocol revision is unpublished** and was not determined. **Which
environment actually launches the CFE MCP server** is unknown — there is no `.mcp.json` or
`.cursor/mcp.json` in the repo, so registration is user-scoped, and the break may or may not affect
the live server depending on invocation. FastMCP 3.4.x's handshake-only status comes from the
maintainer's own answer rather than from reading 3.4.7's source. And the handle-and-poll
recommendation is **synthesis, not citation** — no upstream document says "do this instead"; it is
reasoned from SEP-2663 defining that lifecycle, from no SDK runtime existing, and from the
stateless core ruling out session-affinity alternatives.
