---
title: "Product Brief: Herald (pyforge-herald)"
status: "draft"
created: "2026-07-25"
updated: "2026-07-25"
inputs:
  - "planning-artifacts/specs/spec-design-code-bridge/SPEC.md + bridge-protocol.md (settled kernel, adopted verbatim, zero open questions)"
  - "docs/dreams/pyforge-herald.md (persona charter, 2026-07-23 ownership review)"
  - "docs/dreams/design-code-bridge.md (flagship-capability Dream, realized)"
  - "docs/dreams/ecosystem-crew.md § 1 The Herald (role, motto, CLI cadence)"
  - "docs/dreams/modernist-identity.md (visual language contract)"
  - "docs/specs/presentation-deck.md § The MCP bridge, § Artifact dependency tree & editing surfaces, § Standard export set"
  - "planning-artifacts/research/market-herald-updates-broadcast-analogues-research-2026-07-25.md (4 analogues)"
  - "presentations/ (10-deck family); docs/dashboard/ (program console)"
project_slug: "pyforge-herald"
---

# Product Brief: Herald (`pyforge-herald`)

## Executive Summary

**Herald** is the pyforge Ecosystem Crew's voice and visual surface, shipped as a real
installable product: distribution `pyforge-herald`, module `pyforge.herald`, CLI `herald`.
It has two halves at very different maturity:

1. **The Design↔Code Bridge (CAP-1..5)** — seed/pull/status/watch/export-push-back, making
   Claude Design and this repo one continuous surface for the 10-deck persona family. This
   half is **fully specced with zero open questions** (`SPEC-design-code-bridge`), proven in a
   2026-07-23 pilot across 7 decks, and is the **near-term build target** of this brief.
2. **`updates compile` + `broadcast`** — turning pyforge's own run telemetry (sprint-status,
   Warden compliance reports, Atlas run summaries, gate reports) into weekly release notables
   and pushing them to Slack/email/wiki. This half is **unspecced** — grounded here by a light
   market scan of 4 analogues (release-please, towncrier, Gitmore-class digest tools, Slack
   Workflow Builder/LaunchNotes) — and is scoped as **roadmap, not V1**.

Herald exists because invisible engineering is failed engineering: the factory (Marshal,
Atlas, Warden, Mason, Doctor) produces real telemetry and real artifacts, but until the bridge
was piloted, turning any of it into something a human could see and act on required manual,
one-off work — the "Local recipes repository connection" stale hand-mirror project is the
fossil of that pain. `herald` makes the proven bridge loop a repeatable command, and sets up
the comms half as its logical next organ.

## The Problem

Three concrete pains, at three points in the Herald lifecycle:

1. **The bridge exists as a session transcript, not a tool.** The 2026-07-23 pilot proved
   seed/pull/status/watch/export-push-back work over the `claude-design` MCP surface — but
   every operator or agent who wants to run that loop today has to re-derive the exact tool
   sequence (`bridge-protocol.md`) by hand inside a Claude Code session. There is no `herald`
   binary; there is a spec and a memory of how it was done once.
2. **Decks and the dashboard drift from the factory's real state.** Ten persona decks
   (`presentations/`) and the program console (`docs/dashboard/`) describe the pipeline, but
   nothing currently *compiles* what actually happened in a given week (stories shipped, gates
   passed, compliance deltas) into anything Herald can proclaim — humans hand-author dashboard
   narrative (`data.js`) and deck content by hand, per `docs/dashboard/README.md`.
3. **Nothing broadcasts.** Even if a weekly update existed, there is no delivery mechanism —
   no Slack post, no email digest, no wiki update. The Dream's "last touch a release,
   proclaiming what shipped" half of Herald's motto has no implementation at all.

The cost of (1) is concrete and immediate: every future bridge operation either burns agent
context re-deriving the protocol or risks drifting from the proven sequence. The cost of (2)
and (3) is more diffuse — the factory ships real work continuously (31/31 Warden stories,
32/32 Atlas stories, etc.) and none of it is proclaimed anywhere a stakeholder would see it
without reading commit logs.

## The Solution

`herald` is a pixi-workspace-member Python CLI with two command groups mapping directly to the
two halves above:

**`herald deck {seed,pull,status,watch}` — the bridge, CAP-1..5, built first.** Wraps the
proven `bridge-protocol.md` tool sequence (`claude-design` MCP calls: `get_claude_design_prompt`
→ `create_project`/`finalize_plan`/`create_support_js`/`copy_files`/`write_files`/`read_file`)
behind deterministic, no-LLM-in-the-loop commands. Etag discipline on every cross-surface
read/write; prove-before-cross (local `extract`+`build` gate seed); directional crossing
(authored sources inbound, seeds + derived exports outbound — never a mirrored app tree).
Transport is dual-path per the settled spec: a pure MCP client on the claude-design remote
server (primary, spike-first story) with a headless Claude Code/Agent SDK fallback.

**`herald updates compile` + `herald broadcast` — the comms half, roadmap.** `compile` reads
pyforge's own structured telemetry — `sprint-status.yaml` per BMAD project, Warden
`ComplianceReport` JSON, Atlas run summaries, gate-pass/fail events — and produces a compiled
update artifact (notables + optionally an infographic, per the deck-family export pipeline)
on a duration window (`--duration weekly`). `broadcast` takes that one compiled artifact and
fans it out to named channel adapters (`slack,email`), each reporting success/failure
explicitly — no silent drops, mirroring the bridge's structured-failure bar rather than the
silent-webhook-failure pattern the market scan flagged in Slack Workflow Builder.
**[ASSUMPTION]** `compile`'s source-of-record is telemetry, never commit-message parsing —
the one explicit divergence the research surfaced from every surveyed analogue.

## What Makes This Different

| Dimension | release-please / towncrier | Gitmore-class digest tools | Slack Workflow Builder / LaunchNotes | **Herald** |
|---|---|---|---|---|
| Bridge to a visual design surface | — (not applicable) | — | — | ✓ Only Herald owns Design↔Code (CAP-1..5) |
| Update source | git commit history / hand-authored fragments | git/PR/issue activity (cross-repo) | caller-supplied payload | pyforge's own structured telemetry (sprint-status, ComplianceReport, gate reports) |
| Delivery failure model | n/a (single output file) | scheduled delivery, failure mode unclear | **silent** — webhook failures don't retry or surface | structured per-channel success/failure (bridge's etag-conflict discipline extended to broadcast) |
| Deterministic / no LLM required | ✓ (both) | ✗ (AI-summarized) | ✓ | ✓ bridge ops always; `compile`'s narrative step may use LLM, sourcing stays deterministic |
| One canonical artifact, many channel adapters | ✗ (one file, one place) | partial (per-channel formatting baked in) | ✓ (LaunchNotes) | ✓ compile once, `broadcast` fans out |

The bridge half has no real analogue — it is a narrow, purpose-built protocol for one
proprietary design surface (Claude Design) and one repo shape (the deck-family engine). The
comms half borrows shape (narrative-over-raw-list, one-artifact-many-adapters) while
explicitly rejecting the sourcing model every surveyed tool uses.

## Who This Serves

**Primary user — any operator or agent running a pyforge session.** Today they either burn
context re-deriving the bridge protocol from `bridge-protocol.md`, or skip the bridge and hand-
download from Claude Design. Success: `herald deck pull warden` behaves identically to the
piloted session transcript, with zero re-derivation.

**Primary user (roadmap) — Marshal / whoever consumes factory telemetry.** Right now, "what
shipped this week" is answered by reading commit logs or `docs/dashboard/`. Success:
`herald updates compile --duration weekly` produces the same narrative a human would have to
hand-assemble from `sprint-status.yaml` + gate reports today.

**Secondary user — stakeholders who never open the repo.** Decks, the dashboard, and (roadmap)
broadcast messages are Herald's face to anyone who isn't running Claude Code sessions. Success
is invisible-to-them: a Slack message or deck update that just appears, correctly, without a
human manually compiling it.

## Success Criteria

**Primary criterion (bridge, near-term):** an operator who has never seen the 2026-07-23 pilot
transcript runs `herald deck seed <slug>` → edits in Claude Design → `herald deck pull <slug>`,
and ships a green, fully exported deck without a single manual download — per
`SPEC-design-code-bridge`'s own success signal. This is the spec's bar; Herald's V1 must clear
it exactly, not a looser approximation.

Supporting criteria:

| Metric | Target | Why this matters |
|---|---|---|
| CAP-1..5 acceptance (from the settled spec) | All 5 pass their own `success:` clause | The spec is the contract; this brief does not loosen it |
| Unchanged-pull cost | Zero body bytes transferred (etag short-circuit) | Proven in the pilot; must hold in the packaged CLI |
| Conflict safety | Every conflict (seed-over-edits, export re-push clash) refused structurally, no partial clobber | Directly testable via exit code + file-state assertions |
| Watch-mode write volume | Zero writes on both surfaces across N consecutive unchanged polls | CAP-4's own bar |
| **[ASSUMPTION]** `updates compile` accuracy | Compiled notables match a human's hand-assembled summary of the same window, spot-checked | No existing test oracle; first roadmap story should establish one |
| **[ASSUMPTION]** `broadcast` delivery integrity | 100% of channel adapters report explicit success/failure; zero silent drops in a fault-injection test | The one bar this brief insists on, per the analogue-divergence finding |

## Technical Approach

- **Package shape:** `pyforge-herald` distribution, `pyforge.herald` module, `herald` CLI
  entrypoint — a pixi-workspace member alongside the other pyforge personas (Atlas, Warden),
  not a standalone repo. **[ASSUMPTION]** packaging mechanics (pip-installable + optionally
  conda-forge, per the Mason pattern used elsewhere in this repo) — not decided in the settled
  spec; Architecture phase should confirm against the deckcraft/Warden precedent.
- **Bridge implementation (CAP-1..5):** wraps the `claude-design` MCP tool surface
  (`get_claude_design_prompt`, `create_project`, `finalize_plan`, `create_support_js`,
  `copy_files`, `write_files`, `read_file`, `render_preview`) per `bridge-protocol.md`
  verbatim. Deterministic — no LLM in the loop for seed/pull/status/watch regardless of
  transport. Dual-path transport: primary a pure MCP client reusing the `/design-login` OAuth
  credential (first implementation story is the time-boxed spike proving or killing this
  path); fallback a headless Claude Code/Agent SDK wrapper with a tool allowlist (token-costed,
  bmad-loop-proven substrate).
- **Deck pipeline integration:** the bridge wraps `extract`/`build`/`deck-export`
  (`docs/specs/presentation-deck.md`) as black boxes — Herald never reimplements the deck
  engine or the export generators. `deck-export`'s editable-PPTX path is **deckcraft's** job;
  Herald transports, never generates (CAP-5 pushes deckcraft's output back to Design, it does
  not produce it).
- **`updates compile` (roadmap):** reads `sprint-status.yaml` (per active BMAD project),
  Warden `ComplianceReport` JSON, Atlas run summaries, and gate-report artifacts; produces a
  compiled update object (notables list + optional infographic handoff to the deck pipeline).
  **[OPEN QUESTION]** exact schema of the compiled-update artifact and how `--include
  notables,infographics` maps to concrete outputs — not addressed by any settled spec; first
  candidate for a dedicated SPEC kernel once this brief's roadmap half is greenlit.
  **[OPEN QUESTION]** whether `compile` needs to read across multiple BMAD projects
  simultaneously (cross-project weekly digest) or scopes to the active project only — the
  multi-project switching machinery (`scripts/bmad-switch`) is Marshal's, not Herald's, per
  the 2026-07-23 ownership review, so `compile` likely consumes Marshal's cross-project view
  rather than re-implementing it.
- **`broadcast` (roadmap):** channel-adapter architecture — one compiled artifact, N channel
  adapters (Slack, email, wiki), each independently reporting success/failure.
  **[OPEN QUESTION]** channel adapter authentication/credential model — likely a Steward
  concern (credential issuance/rotation, per `ecosystem-crew.md` § 8) rather than Herald's to
  own outright; needs an ownership decision before Architecture.
- **Visual identity:** all Herald output (decks, dashboard, future broadcast messages) speaks
  the Modernist design system (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`) — flat, Archivo, the
  family palette. Herald's own deck (`presentations/pyforge-herald/`) is currently
  **SCAFFOLD status** (engine copied verbatim, no prototype authored yet) — dogfooding Herald's
  own bridge to seed and pull its own deck is a natural first CAP-1/CAP-2 validation story.

## Relationship to Adjacent Projects

- **`deckcraft`** (sibling BMAD project): the designated editable-PPTX engine under every
  export. Herald's CAP-5 pushes deckcraft's regenerated derived set back into Design; Herald
  never generates PPTX itself. `marp --pptx` remains the interim generator until deckcraft
  ships.
- **`pyforge-marshal`**: owns BMAD multi-project/monorepo machinery and cross-agent
  portability — moved off Herald in the 2026-07-23 ownership review. Herald's `updates compile`
  (roadmap) likely consumes Marshal's cross-project sprint-status view rather than re-deriving
  project switching itself.
- **`docs/dashboard/`** (program console, its own Dream `factory-console.md`, not a BMAD
  project here): the console Herald "proclaims from" in the persona ideal. `updates compile`
  and the dashboard's `generate.py` sync logic likely converge — **[OPEN QUESTION]** whether
  `herald updates compile` supersedes or feeds `docs/dashboard/generate.py`'s sprint-status
  sync, deferred to Architecture.

## Roadmap Thinking

**V1 — the bridge (`herald deck seed/pull/status/watch`), CAP-1..5 exactly as specced.**
First story: the transport spike (pure-MCP-client vs. headless-wrapper decision). Then seed,
pull (incl. Marp-source + standalone-bundle pull), status (incl. stale-mirror detection),
watch, export push-back — each with the spec's own acceptance criteria as the test oracle.
Dogfood target: seed + pull Herald's own SCAFFOLD deck as the first end-to-end validation.

**V2 — `updates compile` (roadmap, unspecced).** Requires its own SPEC kernel
(`bmad-spec` on this brief's comms-half scope) before implementation — schema for the
compiled-update artifact, telemetry-source contract, and the notables/infographics split are
all open questions this brief surfaces but does not resolve.

**V3 — `broadcast` (roadmap, unspecced).** Depends on V2's compiled-artifact shape and an
ownership decision on channel-adapter credentials (likely Steward-adjacent). First channel:
Slack (per the Dream's CLI cadence example), per the LaunchNotes-style one-artifact/many-
adapters pattern the research recommends.

**V∞** — Herald closes the loop the Dream describes: first to touch a Dream (deck generation
from a raw vision — `herald deck generate`, not covered by either the bridge spec or this
brief's roadmap; **[OPEN QUESTION]** whether that's a third V-tier or folds into `deck seed`)
and last to touch a release (`broadcast`), with nothing the factory does staying invisible.

## Known Risks

- **Scope-mixing risk.** This brief deliberately spans a fully-specced near-term capability
  and two genuinely unspecced future ones. **Mitigation**: PRD and Architecture phases should
  treat the bridge as the sole V1 scope; `updates compile`/`broadcast` should NOT be
  epic/story-decomposed at the same depth in this pass — flagged explicitly in the epics stage
  guidance.
- **Transport uncertainty is load-bearing.** The bridge's dual-path transport assumption
  (pure MCP client primary, headless-wrapper fallback) is *unproven outside a Claude Code
  session* — the settled spec itself calls the first implementation story a "time-boxed spike."
  If the spike kills the primary path, CAP-1..5's implementation shape changes materially.
  **Mitigation**: sequence the spike first, before any other bridge story.
  **[ASSUMPTION]** carried directly from `SPEC-design-code-bridge`'s own Assumptions section.
- **Herald's own deck is unbuilt.** Dogfooding the bridge on Herald's own SCAFFOLD deck is
  attractive but adds a dependency (someone must author the Design-side prototype) outside
  Herald's own critical path. **Mitigation**: use an already-seeded deck (marshal/mason/doctor,
  per the pilot evidence table in `bridge-protocol.md`) as the primary acceptance fixture;
  treat Herald's own deck as a stretch validation, not a blocker.
- **Comms-half source of truth doesn't exist yet.** `updates compile` assumes
  `sprint-status.yaml` + `ComplianceReport` + Atlas run summaries are stable, machine-readable
  contracts — true today per CLAUDE.md's sync-runbook discipline, but the roadmap half has no
  spec pinning that contract. **Mitigation**: a dedicated `bmad-spec` pass is the prerequisite
  for V2, not an assumption this brief should paper over.

## Open Questions (carried into PRD/Architecture)

1. Exact schema of the `updates compile` output artifact and the notables/infographics split.
2. Whether `compile` scopes to one active BMAD project or reads cross-project (via Marshal).
3. Channel-adapter credential/ownership model for `broadcast` (Herald vs. Steward).
4. Whether `herald updates compile` supersedes or feeds `docs/dashboard/generate.py`'s existing
   sprint-status sync.
5. Whether `herald deck generate` (Dream→deck rendering, distinct from `deck seed`) is a
   distinct V-tier or folds into the seed capability.
6. Packaging mechanics for `pyforge-herald` (pip-only vs. also conda-forge via Mason's pattern).

## Kill Criteria

The comms half (V2/V3) does not proceed if, after V1 (the bridge) ships and is dogfooded for
a full sprint cycle: no operator has hit the "what shipped this week" pain badly enough to
hand-write a summary more than once. If that pain never materializes concretely, `updates
compile`/`broadcast` stay Dream-stage rather than being spec'd — the bridge alone already
resolves the sharper, provenly-felt pain (manual Design↔repo transfer). The bridge itself has
no kill criterion here — it is already proven and specced; only its *packaging as a CLI* is
this brief's bet, and that bet is low-risk given the pilot evidence.
