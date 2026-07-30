# Campaign record — factory spec-completion (2026-07-25)

**One day, ten parallel planning chains.** Every pyforge persona and component taken through
**research → Analyst brief → PRD → architecture → epics+stories** (epics omitted for the two
far-horizon platforms by design), each persona defined as a REAL installable package
(warden pattern: dist `pyforge-X` / module `pyforge.X` / CLI `X`). All chains ran **headless
and parallel** in isolated bmad-loop worktrees (one `loop/<slug>` branch each, per-worktree
`bmad-switch` state), merged to `main` as each landed. Model tiering: sonnet for
well-inventoried chains, opus for the four judgment-heavy ones (marshal, mason, unity,
genesis); no Fable in the fleet. Live progress published throughout on the program console's
**Campaign board** (`docs/dashboard/`, added at launch).

Every research report is **tracked and durable** under each project's
`planning-artifacts/research/` — the same durability principle as story specs.

## Results (10/10 landed)

| Wave | Project | Model | Depth | Output | Headline |
|---|---|---|---|---|---|
| 1a | pyforge-doctor | sonnet | full | 9 FRs · 3 epics / 12 stories | Consolidative health CLI; exit codes a strict subset of warden's frozen `{0,1,2,130}` |
| 1b | pyforge-steward | sonnet | full | 18 FRs · 4 epics / 18 stories | Keys/deploy/provision/budget; hexagonal wrap of existing tools; JFROG regression test is Story 1.2 |
| 1c | pyforge-scribe | sonnet | full | 15 FRs · 2 epics / 9 stories | Legacy team-memory spec fully folded (mapping in PRD addendum); markdown-only constraint formally superseded (D-1) |
| 1d | pyforge-herald | sonnet | full | 26 FRs · 5 epics / 17 stories | Stories trace 1:1 to the settled bridge CAPs; comms half stays roadmap |
| 1e | pyforge-marshal | opus | full | 58 FRs · 6 epics / 40 stories · 39 ADs | **Wrap-and-supervise** (Option A): bmad-loop already conda-packaged here; all 9 known gaps peripheral to the engine. Agent-portability folded; copilot-api bridge premise obsolete (0.9.0 ships a copilot profile + `copilot --acp`) |
| 1f | pyforge-mason | opus | full | 50 FRs · 5 epics / 38 stories | **Seam-by-capability** (Option C): subprocess-wrap CFE for `recipe`; build native for `package`/`environment`. Atlas-rebuild cited as the failed-precedent evidence |
| 2a | presenton-pixi-image | sonnet | full | 7 epics / 30 stories | Pre-campaign PRD revised with delta log; upstream dropped LibreOffice (kills a recipe + license risk); MS disconnected-stack check now Phase-0-blocking |
| 2b | wasm-analytics-stack | sonnet | PRD+arch | 17 FRs · 10 ADs | Honest maturity verdict: DuckDB/dlt/dbt-in-WASI still blocked upstream; WASI sandbox scoped to pure-Python upload validation only |
| 2c | unity-data-stack | opus | PRD+arch | 60 FRs · 23 ADs | Constitution absorbed with an 8-amendment list; flagship `pdm export --override-platform` flag found nonexistent; EU CRA obligations (2026-09-11) surfaced |
| 2d | pyforge-genesis | opus | full | 6 epics / 36 stories | Extraction question resolved: **5-class manifest** (referenced / copied-managed / copied-seeded / generated-derived / hybrid-managed-region) + a structurally-enforced never-write set; wraps copier |

**Sidecar:** `spec-upstream-discovery` Tier-2 kernel (5 CAPs + 2 companions) under
pyforge-atlas — Phase T reframed as Kedro-pipeline work; confirmed no global
SCHEMA_VERSION survives the shipped migration.

**Supersessions recorded** (frontmatter `status: superseded` + `superseded_by:`):
`claude-team-memory` → scribe chain · `copilot-bridge-vscode-extension` +
`bmad-copilot-adapter-upstream` → marshal chain · `trendshift-conda-forge` →
spec-upstream-discovery.

**Dreams flipped to `in-spec`:** pyforge-herald, pyforge-doctor, pyforge-scribe,
team-memory, pyforge-steward, pyforge-genesis, presenton-pixi-image,
wasm-analytics-stack, unity-data-stack, upstream-discovery. (marshal/mason Dreams stay
`realized` — their chains productize realized capabilities.)

## Cross-chain contracts to hold

- **Genesis ↔ Marshal:** Marshal owns the *source* of `bmad-switch`/`bmad-loop-worktree`;
  Genesis owns *delivery* and never forks (genesis PRD assumption 8; marshal's Option A is
  consistent).
- **Doctor ↔ Warden:** doctor depends on warden via an optional extra; exit-code subset
  discipline.
- **Mason ↔ CFE:** the skill stays canonical for recipe semantics (CLAUDE.md Rules 1&2);
  mason never forks recipe knowledge.
- **Presenton ↔ Deckcraft:** repackaged app vs from-primitives pipeline — complementary,
  scope walls held in both PRDs.

## Top open questions for the operator (full lists live in each PRD § open questions)

1. **Marshal Q-2 — AGENTS.md-family ownership**: `AGENTS.md` says Herald,
   `agent-portability.md` says Marshal; one is stale. Marshal ships drift-*detection*-only
   until settled.
2. **Unity OQ-1/OQ-2** — lock architecture confirmation (spine answers AD-2
   workspace-lock-primary) and one-Domain-vs-eleven sizing (order-of-magnitude fork).
3. **Presenton exit-6a** — does Microsoft's disconnected stack already include
   Copilot-deck-generation? Single most consequential unknown; Phase-0-blocking.
4. **Upstream-discovery** — which of the 7 shipped atlas pipelines hosts discovery
   (`vcs_health` closest fit, unconfirmed); discovery dataset naming.
5. **Mason OQ-6** — competitive-coverage risk: no discovery sweep for unknown dual-publish
   entrants ran (web budget); could undercut D-1's premise.
6. **Doctor** — severity default for the credential-hygiene check; its generalization
   boundary beyond `JFROG_API_KEY`.
7. **Scribe** — graph storage engine (flat-file v1 recommended, swap deferred); `recall`
   output format / LLM-optionality.
8. **Genesis kill criteria** (live, testable in V1): K-01 region-merge reliability; K-02 the
   `local-recipes` empty-plan oracle — failing it means the model isn't actually extractable.
9. **Marshal follow-up** — a second adversarial pass over the 15 ADs added by its reviewer
   lenses (AD-25–39) before implementation.

## Known campaign-wide caveats

- All chains ran **headless/express**: elicitation menus self-confirmed; several skipped the
  full parallel reviewer-gate dispatch (self-review substituted) — marshal, wasm, unity DID
  run reviewer lenses (which earned their keep: 7-15 real findings each).
- **WebSearch budget exhausted mid-campaign** — later chains (mason, genesis, presenton,
  wasm, unity) researched via direct WebFetch + `gh` against primary sources; cited but
  coverage-limited (each discloses this in its methodology notes).
- Run-folder names use literal `<project-slug>` rather than the `{project_name}` template
  token (which resolves globally to `local-recipes`) — deliberate, recorded per chain.

## bmad-loop readiness verdict

**Ready to enter implementation now** (full epics+stories on main): herald (nearest-term,
17 stories), doctor (12), scribe (9), steward (18), mason (38), marshal (40), genesis (36),
presenton (30 — after its Phase-0 gates). **Not loop-ready by design:** wasm + unity
(PRD+architecture; stories decompose when scheduled). Implementation runs per project via
bmad-loop with the durable story-spec convention (specs promote to
`planning-artifacts/specs/` post-merge).
