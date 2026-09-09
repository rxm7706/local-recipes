---
id: SPEC-agent-tool-surface
spec: agent-tool-surface
status: in-progress
updated: "2026-09-09"
owner-dream: docs/dreams/agent-tool-surface.md
surface:
  - .claude/tools/conda_forge_server.py
  - .claude/tools/gemini_server.py
sources:
  - ../../../../../../docs/dreams/agent-tool-surface.md
  - ../../../../../../docs/dreams/agent-portability.md
  - ../../../../../../docs/dreams/regenerable-factory.md
open_questions: []
  # Q1 ANSWERED 2026-09-09 (operator, fleet-readiness batch rows mars-A-B1 / C10): THE SURFACE
  # FEDERATES. The HTTP station face `POST /stations/<name>/mcp` (django-pyforge
  # `mcp_http.py:137`, with auth `mcp_auth.py:1`, rate limiting `rate_limit.py:3` and dual-era
  # routing `mcp_dual_era.py:29,40`) is the ONE GOVERNED FRONT DOOR; the stdio servers are LOCAL
  # ADAPTERS. The question was stale as posed -- it is no longer two surfaces but FIVE
  # (`.claude/tools/conda_forge_server.py` with 46 `@mcp.tool` decorators,
  # `.claude/tools/gemini_server.py`, `pyforge/atlas/mcp/server.py`, `pyforge/marshal/mcp/server.py`,
  # and the HTTP transport). Merging five into one binary re-couples the crafts the Charter
  # deliberately split; leaving them split leaves the surface ownerless, the failure this Dream
  # exists to name. Federation is the only option the existing code already implements: the HTTP
  # face is a mount point, not a server, so each craft keeps its own tools. See § Measured facts.
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete,
> preservation-validated contract for what to build, test, and validate. Source documents
> listed in frontmatter are for traceability only.

# The agent tool surface — the factory, callable

## Why

Every capability the factory has should be reachable by an agent through one governed,
typed surface — a named tool, a typed argument, a structured answer — rather than a pile
of bespoke integrations or powers only a human at a shell can invoke.

This Spec exists because the surface **shipped without one**. It was Part 3 of the
`local-recipes` rebuild and survived for months as a single bullet inside
[[packaging-factory]]; its Dream was authored 2026-07-25, after the fact, to close the last
unowned part of the factory. `status: realized` was reached without ever passing through
`specified` — which is precisely why four artifacts now disagree about whether
`.mcp.json` should exist, and why nobody noticed the surface covers 2 stations of 6.

The tools belong to the crafts. **The surface belongs to the operating model** — it is how
any agent reaches any craft, the same concern as [[agent-portability]] seen from the other
side. Splitting it by craft is what left it ownerless.

## Capabilities

- **CAP-1 — one governed surface.** *Intent:* an agent reaches any craft through a named,
  typed tool. *Success:* 46 tools on `conda_forge_server` + 11 on the pyforge-atlas server
  are callable; each is a thin wrapper over a Tier-1 script so the CLI and the tool surface
  cannot diverge.
- **CAP-2 — the surface survives a clone.** *Intent:* a fresh checkout has working tools
  without hand-editing a machine-global file. *Success:* registration is repo-tracked and
  path-relative; a clone on a new machine reaches the tools with no manual step.
- **CAP-3 — CLI ⇄ tool parity is gated, not reviewed.** *Intent:* the thin-wrapper property
  is mechanically enforced. *Success:* a typed contract test asserts every tool maps to its
  script and its signature matches; adding a tool without its script fails.
- **CAP-4 — coverage is measured, not assumed.** *Intent:* "every capability is reachable"
  is a checkable claim. *Success:* a check reports, per station, which realized capabilities
  are on the surface — and the number is published rather than asserted.

## Constraints

- **Thin wrappers only.** A tool contains no craft logic; it shells to the Tier-1 script.
  The moment a tool computes something the CLI cannot, the surfaces have diverged.
- **The server stays path-clean.** `conda_forge_server.py` resolves everything from
  `Path(__file__)` and `sys.executable`. It is already portable — **the portability defect
  is entirely in registration**, and no fix may introduce an absolute path into the server.
- **Registration is not a machine secret.** Today it lives only in `~/.claude.json` with
  machine-absolute paths, and **the only file in the repo that documents this is the Dream
  itself.** Delete that Dream and the recovery procedure for 57 tools leaves the repo.
- **The surface is Marshal's; the tools are not.** Marshal owns reachability. Mason owns the
  21 recipe-authoring tools' behavior, Atlas the 21 intelligence tools'. A change to what a
  tool *does* is the craft owner's; a change to *how it is reached* is Marshal's.
- **Two servers is a state, not a decision** (Q1). The second arrived additively with the
  pyforge-atlas rebuild. Neither federation nor merger has been chosen, and this Spec owns
  the choice.

## Non-goals

- **Re-implementing craft logic in the tool layer** — the thin-wrapper rule forbids it.
- **A public or authenticated API tier** — the surface is agent-local over stdio.
- **Forcing every station onto the surface before it has capabilities.** Doctor, Herald,
  Scribe and Steward are `specified`/`pitched`; absence there is sequence, not drift.
  Herald's case is different and *is* drift: `design-code-bridge` is **realized** and works
  through `claude-design`, an MCP the factory does not govern.

## Success signal

A fresh clone on a new machine reaches all tools with no hand-editing; a contract test
fails when a tool drifts from its script; and the coverage number is published in the
Guildhall rather than claimed in prose.

~~Today, honestly: **2 stations of 6** have realized capability on the surface (mason 21,
atlas 21; warden partial at 2; herald, steward and **marshal — the owner — at zero**).~~
**Re-measured 2026-09-09: 3 of 6.** The claim "every capability the factory has is reachable"
is still not true, which is why the Dream is `type: practice` and not a finished thing.

## Measured facts (2026-09-09)

Recorded because this Spec's body and the Dream both understate them.

- **Coverage is 3/6, not 2/6.** Running the gate this Dream asked for
  (`pyforge/marshal/mcp/coverage.py::tool_surface_coverage_report`) returns
  `{"ratio": "3/6", "coverage": 0.5}` — mason (via `conda_forge_server.py`), atlas, and marshal
  itself, no longer at zero.
- **CLI ⇄ tool parity is gated for marshal ONLY** (`mcp/parity.py`,
  `tests/meta/test_cli_tool_parity.py`, Story 18.2 / FR-155). The 46 CFE tools and
  `pyforge/atlas/mcp/tools.py` have **no equivalent gate**. CROSS-STATION: routed to mason and
  atlas per this Spec's own ownership split — a change to what a tool *does* belongs to the craft
  owner.
- **CAP-4's number is computed but not published.** `mcp/coverage.py` has a `main()`; no pixi
  task exposes it, and the console that would have carried it is retired.
- **`.mcp.json` still exists NOWHERE** — not at the repo root and not in any of the eight loop
  homes, despite `cli/init.py:447` `_render_mcp_json`.

## The `.mcp.json` decision — four artifacts, four positions

This Spec's first job is to end a contradiction that has stood since 2026-05-12:

| Artifact | Says |
|---|---|
| **Q-PRD-01** | ✅ *"CONFIRMED DECISION (2026-05-12, operator-approved): ACCEPTED — include `.mcp.json` in v1"* |
| **E10.S9** (epics) | Story *"stands as written"* — author repo-root `.mcp.json`. **Unimplemented.** |
| **NG6** (same PRD) | Non-goal — *"explicit registration is a v2 enhancement"* |
| **E10 acceptance** | Rewritten 2026-07-25 to describe the absence as the accepted state |

An operator-approved decision never shipped, a contradicting non-goal sits **in the same
PRD**, and the acceptance criteria were later edited to match the un-done reality.

**The escape hatch was broken.** Q-PRD-01 says *"If you change this to 'defer', move E10.S9
to deferred work (DW11)."* **DW11 was already taken** — assigned 2026-05-23 to the Phase K
checkpoint/watchdog work. The reversal could not be executed as written, which is the most
likely reason it resolved neither way.

**Resolution required before CAP-2 can be built.** The server is path-clean, so a tracked
`.mcp.json` with relative paths is cheap. Either it ships (honoring Q-PRD-01) or NG6 wins
and Q-PRD-01 is formally retracted with a *valid* deferral id. What may not continue is
both positions living in one document while a fresh clone gets zero tools.
