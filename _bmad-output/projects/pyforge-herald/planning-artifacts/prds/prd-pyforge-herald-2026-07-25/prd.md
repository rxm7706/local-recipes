---
title: "Product Requirements Document — Herald (pyforge-herald)"
status: "final"
created: "2026-07-25"
updated: "2026-08-04"
currency_review: Reviewed 2026-08-04 — SPEC expanded to include HER-2 (release notables) and HER-3 (visual identity system) on 2026-07-29. These capabilities were authored in the SPEC but never decomposed into the PRD. Updated PRD scope note and added high-level capability descriptions for HER-2 and HER-3.
inputs:
  - "planning-artifacts/briefs/brief-pyforge-herald-2026-07-25/brief.md"
  - "planning-artifacts/specs/spec-design-code-bridge/SPEC.md + bridge-protocol.md (settled kernel, adopted verbatim for V1 FRs)"
  - "planning-artifacts/research/market-herald-updates-broadcast-analogues-research-2026-07-25.md"
project_slug: "pyforge-herald"
---

# Product Requirements Document — Herald (`pyforge-herald`)

## Executive Summary

Herald V1 is the Design↔Code Bridge, packaged: a `herald deck {seed,pull,status,watch}` CLI
that wraps the proven, fully-specced protocol in `SPEC-design-code-bridge` (HER-1 capabilities
CAP-1..5) so any operator or agent can run seed/pull/status/watch/export-push-back without
re-deriving the `bridge-protocol.md` tool sequence by hand inside a session. The SPEC (as of
2026-07-29) also declares two additional capabilities — **HER-2** (releases are proclaimed from
the ledger) and **HER-3** (the visual identity is one system) — which are **deferred from V1**
pending dedicated product definitions and epics work. This PRD's Functional Requirements trace
1:1 to HER-1's five settled capabilities; their `success:` clauses are adopted as this PRD's
acceptance criteria, not re-derived. `updates compile` and `broadcast` (which may relate to
HER-2) are **explicitly out of V1 scope** — carried forward as a Roadmap section per the
product brief's instruction not to decompose them at the same depth as the bridge.

## Success Criteria

**Primary:** an operator who has never seen the 2026-07-23 pilot transcript runs
`herald deck seed <slug>` → edits in Claude Design → `herald deck pull <slug>`, and ships a
green, fully exported deck without a single manual download — `SPEC-design-code-bridge`'s own
success signal, verified by exit codes and file artifacts alone (no subjective judgment call).

| Metric | Target | Source |
|---|---|---|
| CAP-1 seed | Seeded prototype passes local `extract` + `build`; re-seed over Design-side edits refused, writes nothing | CAP-1 success clause |
| CAP-2 pull | Post-edit pull yields green build + regenerated exports; unchanged pull transfers no body, reports "unchanged", exit 0 | CAP-2 success clause |
| CAP-3 status | Machine-readable per-deck state (linked/unlinked, unchanged/changed/conflict, last pull); stale hand-mirror flagged in a planted fixture | CAP-3 success clause |
| CAP-4 watch | Edit lands within poll + debounce; consecutive unchanged polls perform zero writes on both surfaces | CAP-4 success clause |
| CAP-5 export push-back | Design holds current derived set (etag-verified); unchanged re-push writes nothing; conflict refused, no partial clobber | CAP-5 success clause |

**Counter-metric:** writes on either surface during an unchanged-state poll/pull/push cycle —
any non-zero count is a regression against the spec's cheap-no-op guarantee, not a feature.

## User Journeys

Herald V1 is a single-operator-role internal tool (the pyforge operator or an agent acting on
their behalf) — no multi-stakeholder UX, so journeys are captured briefly rather than
persona-elaborated.

**UJ-1 — First seed.** An operator has authored a starter `.dc.html` for a new persona deck
locally. They run `herald deck seed <slug>`. Herald proves it locally (`extract` + `build`),
gates on `get_claude_design_prompt`, creates the Design project bound to Modernist, writes the
runtime + prototype, and prints only the `claude.ai/design/...` link — never a tokenized serve
URL. The operator opens that link and starts editing visually.

**UJ-2 — Pull after a Design edit.** The operator (or a teammate) has been editing in Claude
Design. The operator runs `herald deck pull <slug>`. Herald reads with `if_none_match`; since
the etag changed, it decodes the entity-escaped body, writes `project/<Deck>.dc.html`,
re-runs `extract` → `build` → `deck-export`, and reports what changed. The operator reviews the
diff and commits (or runs `--commit`).

**UJ-3 — Nothing happened.** The operator runs `herald deck pull <slug>` again immediately.
Herald's `read_file` returns `{unchanged: true}` — zero bytes transferred, "unchanged" printed,
exit 0. No file touched, no re-derivation triggered.

**UJ-4 — Mid-edit conflict.** The operator runs `herald deck seed <slug>` against a deck that
already has unsaved Design-side edits. Herald refuses structurally with a conflict message
naming what it detected — writes nothing on either surface.

**UJ-5 — Continuous sync.** The operator runs `herald deck watch` for a set of decks and walks
away. An hour later, a Design-side edit that happened 20 minutes in has already landed in the
repo — deferred until the etag was stable for one poll interval, applied automatically, logged.

## Project Scoping

### Strategy

Herald V1 is a **single-release, spec-driven build** — not phased delivery. The five
capabilities are adopted from an already-validated, zero-open-question spec; the work here is
packaging that proven protocol as a deterministic CLI, not designing new behavior. The
**first implementation story must be the dual-path transport spike** (pure MCP client vs.
headless Claude Code/Agent SDK wrapper) — every other story depends on which transport wins,
per the brief's risk analysis.

### Complete V1 Feature Set

#### Must-Have Capabilities (V1 = CAP-1..5, verbatim)

- `herald deck seed <slug>` — CAP-1 (FR-01–FR-04)
- `herald deck pull <slug>` — CAP-2, including Marp-source pull and Design-authored standalone
  bundle pull (FR-05–FR-10)
- `herald deck status [<slug>]` — CAP-3, including stale hand-mirror detection (FR-11–FR-13)
- `herald deck watch` — CAP-4 (FR-14–FR-17)
- Export push-back (invoked by `pull`'s post-`deck-export` step, or standalone) — CAP-5
  (FR-18–FR-20)
- Dual-path transport with the spike as first story (FR-21–FR-22)
- Deterministic, no-LLM core for all five (FR-23)
- Per-deck registry conformance (README § *Design project*) (FR-24)
- Distribution as a pixi-workspace-member CLI (FR-25–FR-26)

#### Explicitly Out of V1 (roadmap — see § Roadmap below)

- `herald updates compile`
- `herald broadcast`
- `herald deck generate` (Dream→deck rendering — distinct from `deck seed`, not covered by the
  settled spec)
- `herald bmad init` (BMAD monorepo/multi-project integration — Marshal's, per the 2026-07-23
  ownership review)
- Programmatic editing of Design-side content beyond the initial seed
- Marp-source **seeding** (only pull is in scope)
- PPTX/export **generation** (deckcraft's job; Herald transports via CAP-5, never generates)
- Automatic retirement of legacy hand-mirror projects (CAP-3 detects; humans retire)

### Risk Mitigation Strategy

- *Risk:* the primary transport (pure MCP client reusing `/design-login`) may not work outside
  a Claude Code session. *Mitigation:* sequence the time-boxed spike as literally the first
  story; the spec's own Assumptions section already frames it as prove-or-kill, with the
  headless Claude Code/Agent SDK wrapper as a known-working (bmad-loop-proven) fallback.
- *Risk:* re-implementing `bridge-protocol.md`'s tool sequence introduces drift from the proven
  pilot. *Mitigation:* every FR below cites the exact protocol step it wraps; acceptance tests
  use the pilot evidence table (marshal/mason/doctor project IDs) as fixtures, not synthetic
  data.
- *Risk:* scope creep toward the comms half during implementation. *Mitigation:* this PRD
  contains zero FRs for `updates compile`/`broadcast` — they are not numbered, not estimated,
  and not epic-decomposed in the next phase; § Roadmap exists only to preserve the brief's open
  questions for a future PRD pass.

---

## Functional Requirements

Every FR is testable via exit code + file-state assertions per the spec's own
framework-agnostic acceptance discipline (`AGENTS.md` § Portability contract). Each FR is WHO
can do WHAT — HOW (the exact MCP tool calls) lives in `bridge-protocol.md`, adopted not
restated.

### CAP-1 — Seed (repo → Design)

- **FR-01:** An operator can run `herald deck seed <slug>` from a clean state and receive a
  Design project bound to the Modernist design system (`fbc1d6c8-b35f-4df6-9044-a64d2675427b`),
  carrying the deck runtime and a contract-compliant starter prototype.
- **FR-02:** Before any write reaches Design, `herald deck seed` proves the prototype locally
  (`extract` yields the expected slide count with no lost sections; `build` succeeds) — a
  failing local prove blocks the seed entirely.
- **FR-03:** If Design-side edits already exist for the target slug, `herald deck seed` refuses
  with a structured conflict identifying what it detected, and writes nothing to either
  surface.
- **FR-04:** After a successful seed, `herald deck seed` prints only the `claude.ai/design/...`
  URL and registers the project (name, id, file URL) in the deck's README § *Design project*.

### CAP-2 — Pull (Design → repo)

- **FR-05:** An operator can run `herald deck pull <slug>` and, when the Design-side prototype
  etag is unchanged from the last-seen value, receive an "unchanged" report with exit 0 and no
  file body transferred.
- **FR-06:** When the etag has changed, `herald deck pull <slug>` decodes the entity-escaped
  body, writes it to `presentations/<slug>/project/<Deck>.dc.html`, and re-runs
  `extract` → `build` → `deck-export` in sequence, surfacing failure at any stage distinctly.
- **FR-07:** `herald deck pull <slug>` also pulls Design-authored Marp sources (deck, executive
  summary, infographic) into `presentations/<slug>/src/marp/` using the same etag/decode loop,
  with no `extract`/`build` step (deck-export regenerates the derived set instead).
- **FR-08:** `herald deck pull <slug>` pulls a Design-authored standalone bundle (e.g. an
  "Infographic standalone" page) to its export path, superseding a marp `--html` render for
  that artifact; the marp render remains the fallback only when no bundle exists.
- **FR-09:** Commits are left to the operator by default; a `--commit` flag opts into an
  automatic commit of the pulled + re-derived state.
- **FR-10:** `herald deck pull` stores the returned etag after every successful pull so the
  next invocation's `if_none_match` check is accurate.

### CAP-3 — Status

- **FR-11:** An operator can run `herald deck status` (all decks) or `herald deck status <slug>`
  and receive machine-readable per-deck state: linked/unlinked, unchanged/changed/conflict (via
  etag comparison), last-pull timestamp.
- **FR-12:** `herald deck status` detects a stale hand-mirror — a Design project holding a
  repo app-tree copy rather than a prototype-only bridge project — and flags it distinctly,
  verified against a planted fixture matching the "Local recipes repository connection"
  pattern.
- **FR-13:** `herald deck status` never writes to either surface — it is read-only by
  construction.

### CAP-4 — Watch

- **FR-14:** An operator can run `herald deck watch` and Herald polls each watched deck's
  prototype etag on a 60 s default interval (hard floor 30 s, jittered).
- **FR-15:** Herald defers a pull until the etag has been stable for one full poll interval
  (Design saves continuously mid-edit) before invoking CAP-2's pull logic.
- **FR-16:** After ~10 consecutive unchanged polls, Herald doubles the poll interval up to a
  10-minute cap, resetting to the default on the next detected change.
- **FR-17:** On an authentication error, `herald deck watch` halts (does not retry) and reports
  the failure structurally — never a silent no-op or infinite retry loop.

### CAP-5 — Export push-back

- **FR-18:** After `deck-export` regenerates a deck's derived set, Herald pushes the current
  derived files into the deck's Design project via `finalize_plan` + `write_files`, using each
  file's last-known etag (`"0"` for a first push).
- **FR-19:** An unchanged file (local hash matches the last-pushed etag record) is skipped —
  Herald writes nothing for it.
- **FR-20:** A conflict on any export file (Design-side change since last push) is refused
  structurally with no partial clobber of the rest of the push set.

### Transport & Cross-Cutting

- **FR-21:** Herald's primary transport is a pure MCP client on the `claude-design` remote
  server, reusing the stored `/design-login` OAuth credential — implemented and validated by a
  time-boxed spike as the first V1 story.
- **FR-22:** If the primary transport spike fails, Herald falls back to a headless Claude
  Code / Agent SDK wrapper with a tool allowlist, reusing the same stored login.
- **FR-23:** Every Herald bridge operation (seed/pull/status/watch/export-push-back) is
  deterministic — no LLM is invoked in the decision path, regardless of which transport is
  active.
- **FR-24:** Every cross-surface Herald read/write carries `if_none_match`/`if_match`;
  unconditional writes are not possible through the CLI.

### Distribution

- **FR-25:** Herald ships as a pixi-workspace-member Python package — distribution
  `pyforge-herald`, module `pyforge.herald`, CLI entrypoint `herald` — installable within this
  repo's pixi environment set. **[ASSUMPTION]** exact pixi-env membership (new env vs. existing
  `local-recipes`-family env) is an Architecture-phase decision, not fixed here.
- **FR-26:** `herald deck --help` documents every subcommand and its flags without requiring the
  operator to consult `bridge-protocol.md` directly.

---

## Non-Functional Requirements

### Determinism & Safety

- **NFR-01:** No bridge operation (seed/pull/status/watch/export-push-back) may invoke an LLM
  in its control-flow decision path — the deterministic-bridge constraint holds regardless of
  transport choice (FR-21/22).
- **NFR-02:** Every conflict (seed-over-edits, pull mid-edit, export-push clash) surfaces as a
  structured, machine-parseable failure — never a silent no-op and never a partial write.
- **NFR-03:** An unreachable Design surface is a clear structured failure at every command —
  `watch` halts rather than retries on auth errors (FR-17); `seed`/`pull`/`status` fail fast
  with a non-zero exit and a message naming what was unreachable.

### Security & Output Hygiene

- **NFR-04:** User-facing output (any command, any log line, any written file) carries only
  `claude.ai/design/...` URLs — a tokenized `serve_url` must never appear in output or in any
  persisted file.
- **NFR-05:** Herald reuses the existing stored `/design-login` credential; it introduces no
  new credential storage mechanism.

### Directional Integrity

- **NFR-06:** Inbound (Design → repo) transfers carry only authored sources — prototype, Marp
  `.md` sources, Design-authored standalone bundle. Outbound (repo → Design) transfers carry
  only seeds and regenerated derived exports. No Herald code path can construct or transfer a
  mirrored app tree in either direction.

### Portability & Acceptance

- **NFR-07:** Every FR's acceptance is framework-agnostic and machine-checkable — exit codes
  and file artifacts are the oracle, per `AGENTS.md` § Portability contract; no FR's acceptance
  depends on a specific agent harness being present at test time (beyond the transport itself).

### Performance

- **NFR-08:** An unchanged `pull`/`status`/watch-poll cycle transfers zero file bodies —
  verified by network/byte-count assertion in acceptance tests, not just by exit code.
- **NFR-09:** Default watch poll interval is 60 s; the CLI enforces a 30 s hard floor even if an
  operator requests a shorter interval.

---

## Open Questions (carried forward to architecture phase)

1. Exact pixi-env membership for `pyforge-herald` (new dedicated env vs. an existing shared
   env) — FR-25.
2. Packaging mechanics beyond the pixi workspace (pip-only vs. also conda-forge, per the
   Mason-pattern precedent used elsewhere in this repo) — brief's open question #6, unresolved
   here.
3. Whether the transport spike (FR-21/22) should be scoped as its own throwaway story or as
   architecture-phase spike work that then informs story breakdown — left to the epics phase.
4. **[STRETCH]** Whether the acceptance-fixture dogfood target is exclusively an
   already-seeded deck (marshal/mason/doctor, per `bridge-protocol.md`'s pilot evidence table)
   or should also validate against Herald's own currently-SCAFFOLD deck — the brief treats the
   latter as stretch, not required for V1 sign-off.

## Roadmap (explicitly deferred, NOT V1 scope)

### HER-2 & HER-3: New capabilities (awaiting dedicated spec + epic work)

Per the SPEC expansion on 2026-07-29:

- **HER-2 — Releases are proclaimed from the ledger** — Release notables compile from pipeline
  data (sprint-status, Warden ComplianceReport, Atlas run summaries, gate reports), never
  hand-written. May subsume or relate to the `herald updates compile` roadmap item below; open
  whether this owns compiled-artifact schema, cross-project scope, and relationship to
  `docs/dashboard/generate.py`.
- **HER-3 — The visual identity is one system** — Decks, infographics, and the Guildhall share
  the Modernist identity vocabulary (fonts, color tokens, motion language). Open: whether
  Modernist coverage is complete for all Herald surfaces, how identity drift is detected, and
  whether any Guildhall (Marshal's console) work is Herald-owned.

Both require dedicated `bmad-spec` passes to define success criteria and story scopes before
decomposition into epics.

### V1-deferred features (further down the roadmap)

Per the product brief's instruction, the following are represented here only as pointers, not as
numbered FRs — they require their own `bmad-spec` pass before any epic/story decomposition:

- **`herald updates compile`** — compiles pyforge's own structured telemetry (sprint-status,
  Warden `ComplianceReport`, Atlas run summaries, gate reports) into weekly notables. Open:
  compiled-artifact schema, single-project vs. cross-project (Marshal-mediated) scope,
  relationship to `docs/dashboard/generate.py`'s existing sync, relationship to HER-2 above.
- **`herald broadcast`** — fans a compiled artifact out to channel adapters (Slack/email/wiki),
  each reporting explicit success/failure. Open: channel-adapter credential ownership (likely
  Steward-adjacent, not Herald's to own outright).
- **`herald deck generate`** — Dream→deck rendering from a raw prompt; open whether this is a
  third roadmap tier or folds into `deck seed`.

All six open questions from the product brief (§ Open Questions there) are preserved verbatim
in that document and are not re-litigated or narrowed here.

## References

- `planning-artifacts/specs/spec-design-code-bridge/SPEC.md` — the settled kernel this PRD's
  V1 FRs trace to.
- `planning-artifacts/specs/spec-design-code-bridge/bridge-protocol.md` — the exact tool
  sequence every FR above wraps.
- `planning-artifacts/briefs/brief-pyforge-herald-2026-07-25/brief.md` — product brief, scope
  rationale, roadmap thinking, kill criteria.
- `docs/specs/presentation-deck.md` — adopted deck-pipeline contract (`extract`/`build`/
  `deck-export` as black boxes).
