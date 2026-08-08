---
id: SPEC-kedro-org-tooling-adoption
spec: kedro-org-tooling-adoption
status: draft
owner-dream: docs/dreams/kedro-org-tooling-adoption.md
surface:
  - "kedro-skills audit report (generated guidance vs Atlas AD-invariants) + conditional, version-pinned install into .claude/skills/ if the audit passes"
  - "CI job publishing `kedro viz build` output from the real pyforge-atlas package to GitHub Pages (default: via the `steward deploy dashboard` mechanism, not the dormant publish-kedro-viz Action)"
  - "recorded adopt/defer decision on vscode-kedro (plus, if deferred, an optional one-line .vscode/extensions.json recommendation)"
sources:
  - ../../../../../../docs/dreams/kedro-org-tooling-adoption.md
  - ../../research/technical-kedro-ecosystem-and-stack-currency-research-2026-08-08.md
  - ../../../../../../docs/specs/cfe-atlas-datapipeline-kedro-migration.md
open_questions:
  - "Is publish-kedro-viz dormant-and-abandoned or stable-and-done? Last push 2025-11-25 (~8.5 months); the Action is thin enough that quiet may mean finished, but it wraps kedro-viz's build interface and kedro-viz itself is moving (v12.4.0, pushed 2026-08-08) — a future kedro-viz major could strand the v3 pin. The research recommends Path B (Steward publishes `kedro viz build` output directly) precisely because this question is unresolved."
  - "Which station's backlog carries the viz-publishing story? The Dream blesses owner ≠ mechanism (Atlas owns the outcome, Steward owns `deploy dashboard`), but the story has to live somewhere concrete."
  - "Does the kedro-skills upstream-contribution angle (Atlas as an unusually invariant-heavy Kedro deployment) become an AC on the audit story ('file upstream issues for guidance the audit finds wrong') or a separate goodwill task?"
  - "Does [[bmad-module-provisioning]] land before this Spec's kedro-skills story runs? If yes, provision through it; if this moves first, the provisioning story here must be written as an adoptable precedent, not a competing one-off installer."
---

# kedro-org-tooling-adoption — Spec

## Why

Atlas runs Kedro exclusively (the shipped Kedro/Dagster/DuckDB migration,
`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`), but three of the Kedro
organization's own surrounding tools were never even considered: `kedro-skills`
(AI-guidance distribution into `.claude/skills/` / `AGENTS.md`), `publish-kedro-viz`
(auto-published Kedro-Viz on GitHub Pages), and `vscode-kedro` (IDE integration).
The 2026-08-08 org-sweep research grounded the gap in live telemetry and inverted
part of the Dream's framing: `kedro-skills` v0.1.1 was released **the same day the
Dream was captured** (2026-08-07) and has exactly 1 star — the risk is not "we're
late," it is adopting week-zero guidance that contradicts Atlas's own architecture
invariants. This Spec authorizes an **audit-and-decide pass over each of the three
tools** — adoption is conditional on the audit, not presumed; a recorded deferral
with a stated reason satisfies the contract.

`kedro-mcp` is out of scope: already resolved (FR-7, "wrapped, never load-bearing"),
and the research re-verified that decision as vindicated (repo dormant ~9 months,
3 stars — exactly the failure mode the non-load-bearing wrapping protects against).

## Capabilities

1. **kedro-skills audit-then-adopt.** Run `kedro-skills` (pinned at the evaluated
   version, v0.1.1 at spec time) against the real `pyforge-atlas` Kedro project and
   produce a written audit of every piece of generated guidance against Atlas's
   AD-invariants (AD-1 no-inline-IO AST scan, injected-fetcher seams, the
   `kedro-catalog-check=38` invariant, credential-scoping allowlist). Content that
   passes is committed to `.claude/skills/` reproducibly; content that contradicts an
   invariant is excluded with the contradiction recorded (and, per the open question,
   possibly filed upstream). Adoption may legitimately conclude "not yet" at v0.1.x.
2. **Always-current published DAG view.** A CI job builds the Kedro-Viz output from
   the **real** `pyforge-atlas` package (not the 77-node stub-mirror prototype) on
   pushes touching `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**`,
   publishing to GitHub Pages the way `docs/dashboard/` already auto-publishes —
   replacing (or standing alongside) the manual `kedro-viz-proto` /
   `capture-kedro-viz-proto` capture tasks. Default mechanism is Path B (Steward's
   `deploy dashboard` shape publishing `kedro viz build` output directly); adopting
   the `publish-kedro-viz` Action itself requires resolving its dormancy question first.
3. **A recorded vscode-kedro decision.** An explicit adopt-or-defer decision with a
   stated reason, committed where the next reader finds it. The research's
   evidence-backed lean: defer ("this repo's Kedro code is written and maintained
   almost entirely by agents — 38/38 stories via bmad-loop — and the extension's
   catalog validation duplicates the deterministic `kedro-catalog-check` gate"), plus
   an optional zero-cost `.vscode/extensions.json` recommendation for rare human
   sessions. Either outcome closes the capability; silence does not.

## Constraints

- **Do not adopt kedro-skills' guidance blind.** At v0.1.1 / 1 star / one day old at
  Dream capture, the generated content has no field history and knows nothing of
  Atlas's invariants. The audit (Capability 1) gates every install; no guidance file
  lands in `.claude/skills/` without a pass verdict against the AD-invariants.
- **Pin what you evaluate.** Any kedro-skills adoption pins the tool version audited;
  a version bump re-triggers the audit, not a silent regenerate.
- **No second one-off installer.** kedro-skills provisioning goes through
  [[bmad-module-provisioning]]'s mechanism if it has landed, or is written as an
  adoptable precedent for it if this Spec moves first — never as an undiscoverable
  driver script (the exact anti-pattern that Dream was captured to close).
- **Publish from the real package, not the prototype.** The stub-mirror
  (`src/prototype/packages/pyforge-atlas-kedro-viz`) exists only because the real
  DAG's viz needed dependency-free serving; a CI job running in the real
  `pyforge-atlas` pixi env removes that reason and must not entrench the stub.
- **Owner ≠ mechanism.** Atlas owns the outcomes and every judgment call (which
  guidance is correct, what the DAG view must show); Steward owns the provisioning
  and Pages-deployment mechanisms leaned on. Neither station absorbs the other's role.

## Non-goals

- **Re-evaluating `kedro-mcp`.** Resolved 2026-07-16 (FR-7), re-verified 2026-08-08.
- **`kedro-builder`.** Sighted in the sweep (4 stars, visual pipeline authoring);
  it solves human-boilerplate friction, the opposite of Atlas's agent-authored,
  contract-tested pipelines. Named here so a future pass doesn't re-open it.
- **Pre-deciding the vscode-kedro outcome.** The contract is that a decision exists
  and is recorded, not that any particular answer wins.
- **Mandating the `publish-kedro-viz` Action specifically.** The Dream asks for the
  outcome (always-current published DAG); the dormant Action is one path, not the goal.

## Success signal

All three tools have an explicit, evidenced disposition: the kedro-skills audit
report exists (with any passing content installed reproducibly and version-pinned),
a live auto-published Kedro-Viz of the real Atlas DAG replaces manual capture, and
the vscode-kedro decision is written down. `dream_chain_check.py` shows the Dream
carrying a Spec, and no future "why isn't Atlas using kedro-org's own tooling?" pass
starts from zero.
