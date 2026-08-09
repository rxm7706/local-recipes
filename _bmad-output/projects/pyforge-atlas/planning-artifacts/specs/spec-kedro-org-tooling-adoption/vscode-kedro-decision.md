# vscode-kedro decision — **defer**

Story: `12-3-record-the-vscode-kedro-verdict` (fulfills Capability 3 of
`spec-kedro-org-tooling-adoption/SPEC.md`, closes FR-63).

**Date:** 2026-08-09

**Verdict: defer.** No installation, no configuration beyond the zero-cost
`.vscode/extensions.json` recommendation described below. This decision
document is itself what closes FR-63 — the epic's contract requires a
recorded, evidenced disposition, not any particular answer or any installed
tooling.

## Live re-check (2026-08-09, `gh api`)

Re-verified `kedro-org/vscode-kedro` live, same session, immediately before
writing this doc:

- `gh api repos/kedro-org/vscode-kedro`: v0.8.0 latest release
  (2026-06-03), 21 stars, Apache-2.0, **not archived**, pushed **today**
  (2026-08-09).
- `gh api repos/kedro-org/vscode-kedro/releases/latest`: confirms v0.8.0.
- `gh api repos/kedro-org/vscode-kedro/contents/package.json`: `publisher:
  kedro`, `name: Kedro` → candidate extension ID `kedro.Kedro`.
- Cross-checked live on both registries this ID must actually resolve
  against (`.vscode/extensions.json` targets the VS Code Marketplace;
  Cursor resolves the same file against Open VSX, per vscode-kedro's own
  README): the Marketplace gallery API confirms `publisher: kedro`,
  `extensionName: Kedro`, latest version `0.8.0`; `open-vsx.org/api/kedro/Kedro`
  confirms `namespace: kedro`, `name: Kedro`, version `0.8.0`. Same ID, same
  version, both registries — `kedro.Kedro` resolves correctly for both VS
  Code and Cursor.

No block condition fires — checked against the intent-contract's three
named conditions: not archived (`archived: false`), license unchanged
(Apache-2.0, matches the 2026-08-08 research), and no stated deprecation
notice (none found in the repo, README, or release notes). The tool is
live, maintained, and unambiguously what that research assumed. The verdict
below is not a staleness/dormancy call — contrast `kedro-mcp`, which FR-7
wrapped as non-load-bearing for an architectural reason (never depend on an
unproven MCP server), a decision that dormancy only *vindicated* later, not
the reason it was originally made. This decision is a fit call specific to
how this repo's Kedro code is written, not a maturity judgment on the tool.

## Reasoning

1. **This repo's Kedro code is agent-authored, not interactively edited.**
   The Kedro/Dagster/DuckDB migration (`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`)
   and every subsequent Epic-migration story — 38/38 — were driven by
   bmad-loop agents running non-interactive dev sessions, not a human
   working inside a VS Code/Cursor window. `vscode-kedro`'s value proposition
   (in-editor node debugging, Kedro-Viz panel navigation, autocompletion
   while typing) targets exactly the interactive-human workflow this repo's
   Kedro code essentially never goes through.
2. **Its flagship feature duplicates an existing deterministic gate.**
   `vscode-kedro`'s catalog Schema Validation surfaces `catalog.yml` errors
   inline in the editor. This repo already enforces the equivalent —
   deterministically, in CI, without depending on any human having the
   extension installed — via the `kedro-catalog-check` pytest gate (47
   passing checks as of story 12-1's 2026-08-09 audit,
   `kedro-skills-audit-report.md`). An IDE-only validation surface adds no
   coverage a session (human or agent) doesn't already get from the gate.
3. **Its other features are genuine, honestly-acknowledged conveniences with
   no existing equivalent.** Go to Definition/Reference across pipeline
   nodes, autocompletion, node debugging, and Kedro-Viz navigation are real
   IDE-only capabilities this repo has no deterministic substitute for. They
   are not redundant in the way Schema Validation is — they're simply
   low-value given how rarely a human session occurs here. This is the
   entire basis for "defer," not "reject": the reasoning is about *this
   repo's* usage pattern, not a claim that the extension is bad or
   unmaintained.

## The zero-cost middle ground

For the rare human session, `.vscode/extensions.json` is added alongside
this decision (`{"recommendations": ["kedro.Kedro"]}`, extension ID
confirmed from live `package.json` above). This costs nothing — it's a
recommendation, not an install — and means a human opening this repo in VS
Code or Cursor gets prompted to install `vscode-kedro` on their own time,
without this repo taking on any maintenance burden for the extension itself.
`.vscode/settings.json` is untouched; no extension configuration is added.

## Re-opening this decision

Defer is not permanent. If this repo's Kedro-authorship pattern changes
(e.g. a sustained run of interactive human sessions against
`src/shared/packages/pyforge-atlas`), or `vscode-kedro` ships a capability
with no deterministic equivalent that becomes load-bearing, this decision
should be revisited against that new evidence — not silently re-litigated
from scratch.
