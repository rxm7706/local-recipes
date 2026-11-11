---
fold-exemption: different-lifecycle
spec: python-foundry-cutover
status: ready
chain: pyforge-unifying-strategy
created: "2026-09-04"
updated: "2026-11-11"
owner-dream: docs/dreams/pyforge-unifying-strategy.md
extends: spec-pyforge-unifying-strategy  # cite this file's ids as fnd:CAP-N outside it; Unifying CAP-1..19 and pap:CAP-1..6 are different sets — never collapse
surface: []
companions:
  - cutover.md
  - launch-slice.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
  - ../../../../../../archive/docs/dreams/pyforge-unifying-strategy-2026-08-23-topology.md
  - ../../research/technical-pyforge-unifying-strategy-bmad-method-whitepaper-2026-09-25.md
open_questions: []
---

> **Canonical contract.** Re-derived 2026-11-11 from `.memlog.md` (D1–D3,
> regenerate-not-fold, the 2026-09-25 consolidation of PRs #1563 / #1564 / #1576 and
> the operator's rulings of 2026-11-10). `local-recipes` (A) writes every Dream, Frame,
> Spec and the capability ledger until the flip; foundry receives proven capability by
> the mode its ledger row names, as **regenerated** packages, never a fold of
> `src/shared/packages/`. **`local-recipes` is never archived** (CAP-7 retired
> 2026-09-25). Extends `spec-pyforge-unifying-strategy`; cite this file as
> `fnd:CAP-1..15`. Decomposed as steward **Epic 44** (44.1–44.15), **Epic 54** (kernel),
> **Epic 67** (laptop SBOM, dossier, instruction surface) and **Epics 120 and 121** (the
> 2026-11-10 rulings), with herald **26.1** and scribe **21.1** taking the stories on the
> surfaces they own. Stories 44.1, 44.4, 44.5 and 44.6 (retired 2026-11-10) and 44.10
> (retired 2026-09-25) are never dispatched. The cutover is regenerative: Dreams and
> memlogs, `archive/**/.memlog.md` included, seed foundry.

# SPEC — Cutover to `python-foundry` (Phases 0–6)

## Why

**A mandate to meet and a vision to realize.** The Dream names `python-foundry`
(pixi workspace `pyforge`) as the lasting git root and `factory/` as the recipe
island. Today's clone is a `staged-recipes` shape the estate outgrew: workspace
name `staged-recipes`, 7,855 recipe dirs beside the platform, one 59k-line lock
for 29 environments, a staged-recipes linter gating every non-recipe PR, and 268
registered worktrees. The review's gate on the cutover (Epics 40 → 43, Mason 13)
closed 2026-09-03 with nothing downstream of it. This Spec is that downstream:
the contract Epic 44 realizes, and the gate Phase 0 waits on. On 2026-09-25
three proposals arrived beside the chain — a laptop SBOM, a cutover dossier, an
estate-first instruction surface — and were folded in as CAP-12..15, so the
laptop, the claim surface and the agents all describe the same two-root estate.

## Capabilities

- **CAP-1 — Open foundry (Phase 0).** (shipped 2026-09-13)
  - **intent:** The operator can create `rxm7706/python-foundry` as a fresh,
    recipe-free, lean-pixi estate with estate-only CI.
  - **success:** The clone exists; no `recipes/` directory; the `environment.yaml`
    export is automated or absent, never by hand. Authoritative proof is a
    **fresh-clone local** run of `detectors-ci` and `platform-ci-local` (plus CRC
    IFF the empty repo already carries the estate Helm chart). GHA is a twin and
    may stay red; force-merge after that local proof is the campaign gate
    (operator 2026-09-13 D1). Fresh-clone local is not provisional.

- **CAP-2 — Realize the estate (Phase 1).** (ready 2026-11-10)
  - **intent:** Every capability of the estate reaches foundry by the mode its capability-ledger
    row names (`rebuild`, `retire`, `A-only`, `B-only`). Launch is a self-hosting slice: B lands
    one story on itself through its own dispatch, gated by its own detectors, and the ledger rows
    Launch needs derive from that proof. The BMAD chain is seeded from Dreams and memlogs. Host
    and `django-*` are out of Launch.
  - **success:** A merge on B's `main` with subject `Merge <station>/<key> into main`, made by
    B's own `marshal factory dispatch`, with B's own `detectors-ci` exit 0 at that SHA, and every
    ledger row marked `launch: true` reads `verified-in-foundry` with a case-list id. Companion
    `launch-slice.md` lists each step, the A verb or detector that runs it, its capability and its
    A test, derives the rows marked `launch: true`, and names the detector subset Launch runs,
    each source's import closure taken from `spec-pyforge-doctor` `contract.md`. `src/shared/`
    may remain on `local-recipes` indefinitely; the ledger's A-only rows decide what stays. No
    Containerfile `COPY` of package source. Host boot is not a Launch success criterion.

- **CAP-3 — CFE on foundry (Phase 2).** (ready 2026-11-10)
  - **intent:** Foundry gains conda-forge-expert by **rebuild from its own Spec** after the
    flip, using `local-recipes` as the legacy oracle — never by carrying the
    `.claude/skills/conda-forge-expert` cell across.
  - **success:** Until that Spec exists (mason Story 39.2, minted `blocked`), conda-forge-expert
    is `A-only` with ledger expiry `"mason:39.2"` and the factory island may resolve it on
    `local-recipes`; Launch does not require `MASON_CFE_ROOT` to stop pointing at
    `local-recipes`. A foundry-born CFE then matches its rebuilt Spec and the archived suite.
    Story 44.6 is retired (2026-11-10).

- **CAP-4 — Factory island (Phase 3).** (shipped 2026-09-13)
  - **intent:** Recipe work runs from `factory/` with its own `pixi.toml` and lock
    and a recipes-only CI.
  - **success:** `mason recipe build factory/recipes/<r>` matches today's CFE wrap;
    the estate lock holds no factory solver dependency; factory CI triggers on
    `paths: factory/**` only. Mason's half of the island is `spec-pyforge-mason:CAP-36`.

- **CAP-5 — Working set (Phase 4).** (ready 2026-11-10)
  - **intent:** Only in-flight and sole-maintainer recipes are carried into the working set.
  - **success:** `factory/recipes/` is the working set under a count ceiling asserted against a
    working-set list, not manifest rows; the 7,855-dir universe is not copied.

- **CAP-6 — Mason talks to conda-forge (Phase 5).** (ready 2026-09-13)
  - **intent:** From foundry, `submit` targets staged-recipes or the bot fork and
    `update` targets the feedstock maintainer-edit path.
  - **success:** Later Phase 5: an agent-opened PR never targets `local-recipes`
    (asserted on the submit path). Out of this campaign; 44.9 stays blocked
    (operator 2026-09-13 D2).

- **CAP-7 — Archive `local-recipes` (Phase 6).** (retired 2026-09-25)
  - **intent:** (retired) `local-recipes` was to become read-only history.
  - **success:** None — retired by the operator's no-archive ruling (2026-09-25).
    Two git roots stay live after the `cutover_root` flip; what `local-recipes`
    hosts afterwards is decided per capability by the ledger's modes. Story 44.10
    retires with it (ledger key stays `blocked`, never dispatched). The id is not
    reused.

- **CAP-9 — Capability ledger and rebuild harness.** (ready 2026-11-10)
  - **intent:** The operator sets a mode per capability by the written rules of
    `spec-foundry-capability-ledger` `modes.md`; `steward cutover plan` generates and validates
    the ledger from the live Specs; a `rebuild` re-derives Spec, spine and epics on B from Dream
    plus memlog and is drained by Marshal with A as oracle.
  - **success:** `steward cutover plan --regenerate` rewrites the derived fields (id, spec,
    station, heading, path) of `docs/foundry/capability-ledger.yaml` from the live Specs and keeps
    the decided ones; `--append` adds rows for new capabilities only; `--check` (the default)
    writes nothing and exits 1 on a broken rule (`spec-foundry-capability-ledger:CAP-1`). The two
    write modes sit behind the kill switch `pyforge.steward.cutover_ledger_write` (default on).
    States are `planned`, `rebuilding`, `verified-in-foundry` and `cut`; a rebuilt capability
    passes the archived suite or an equivalence check before `verified-in-foundry`; the freeze of
    a `rebuilding` row is judged by `spec-pyforge-doctor:CAP-94`, not by `plan`. The four scored
    decision signals are retired in favour of `modes.md`'s written rules (operator 2026-11-10).

- **CAP-8 — The root-of-record flag is the writer lock.** (ready 2026-11-10)
  - **intent:** The operator names, with one flag, the root that writes every Dream, Frame,
    Spec and the capability ledger; `steward cutover flip` is the cutover and flipping back the
    rollback. Routing per capability is the ledger row, never the flag.
  - **success:** `pyforge.cutover_root` is read through
    `pyforge.core.cutover_root.root_of_record() -> RootOfRecord(root, forge_slug, source)`
    (`spec-pyforge-core:CAP-13`, marshal Story 117.2). Its consumers are the three operator
    ruling 2 names: the chain-write guard, marshal's default forge remote (marshal Story 115.4)
    and, with Story 44.8, Mason's ship and submit root. The guard has two halves: a session
    denial of an Edit or Write to a chain path off the writer (Story 121.4, guild-roster
    `chain-write-off-the-writer`) and doctor's `writer-lock` source in `detectors-ci`
    (`spec-pyforge-doctor:CAP-100`, Story 56.5), which judges the branch for every harness and
    reads the flag at the merge base, never at HEAD, so the branch that carries the flip passes
    (fnd:AD-24). A checkout knows its own root from `docs/governance/guild-roster.json`
    `roots.this`; an answer whose `source` is `default` does not prove the checkout is the
    writer. A flip is refused while a loop runs and stamps the Realization log.
    The operator flips `pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven; nothing flips it automatically.
    The slice is proven when B lands one story on itself through its own dispatch and detectors
    and every Launch row of the case list reads `verified-in-foundry`. `steward cutover apply`
    and the manifest are retired.
    `pixi run -e pyforge-guild python -m pytest tests/scripts/test_pre_shell_hook.py -q -k chain_write`
    and
    `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_writer_lock.py -q`
    each exit 0.

- **CAP-11 — Foundry kernel regenerate.** (ready 2026-11-10)
  - **intent:** The operator can regenerate `pyforge-core`, steward, and marshal in
    foundry `src/packages/` from Dream plus memlog and the re-derived Spec, against a thin
    archived-test oracle; a Frame is a pointer, not a seed. The seed includes
    `archive/**/.memlog.md`, with no backfill.
  - **success:** CLI + MCP for those three are green on a python-foundry checkout; one
    marshal dispatch against the foundry remote passes. `scripts/memlog_fidelity_check.py`
    (Story 44.13) holds the seed: every live Spec has a memlog. B's three leaves are a
    prototype pinned at A PR #1344 and are not re-pinned until the core, steward and marshal
    Specs pass the truth sweep. Stories 44.4 and 44.5 are retired (2026-11-10). Full contract:
    `spec-foundry-regenerate-not-fold`.

- **CAP-10 — Metered minutes budget.** (ready 2026-09-13)
  - **intent:** `steward budget` knows the account's GitHub Actions-minutes spend and
    ceiling, so the foundry dispatch, Marshal's drains and the rebuild harness never run
    blind into a billing block again.
  - **success:** Later, when GHA twins or Marshal drains spend minutes:
    `steward budget check` returns a real under/over verdict against the plan's
    included minutes and the declared ceiling from a metering source (the Actions
    billing API through a `user`-scoped credential held in `steward keys`, never
    in a tracked file); those drains and the rebuild harness read it as their
    ceiling; the honest-stub property is retired for this source only. Not a
    Launch / 44.3 confirmation gate (operator 2026-09-13 D1b).

- **CAP-12 — The laptop SBOM.** (shipped 2026-10-08)
  - **intent:** A developer laptop installs `pyforge-foundry-full` and from it
    alone runs the stations, local recipe generation and builds, tests, lint and
    the local CI mirrors, and — through a layer environment — the platform local
    stack. It is the default laptop install (a new capability over
    `spec-pyforge-steward:CAP-151`, amended 2026-09-25 by its own memlog). The session and
    runtime default stays `pyforge-guild` (`spec-pyforge-steward:CAP-5`); the laptop installs
    the superset.
  - **success:** `pixi install -e pyforge-foundry-full` solves on linux-64,
    osx-arm64 and win-64 and composes the `build` and `grayskull` features beside the
    station features, with `pnpm` in the `python` feature. The `crm` feature
    (conda-recipe-manager ≥0.8 and feedrattler) is a named SBOM gap on CAP-13's list;
    grayskull's own dependency brings conda-recipe-manager in at 0.5.0. The
    platform-limited stack (`platform-dev`, `platform-object-storage`) solves as a layer
    environment over it on the platforms its features declare. Every `postgresql` pin in
    the estate is `>=17.11,<18` and no environment resolves libpq 18: each driver is
    capped at its last libpq-17 release (psycopg 3.2.10, psycopg2 2.9.10, pgvector
    0.8.1, measured 2026-09-26), with a direct `libpq` pin beside it. Neither
    `local-recipes` nor a `desktop-lab` feature is composed; `AGENTS.md` names it the
    laptop install.

- **CAP-13 — The SBOM is checkable.** (shipped 2026-10-10)
  - **intent:** The operator can prove the laptop needs nothing beyond the SBOM,
    and every gap has an owner.
  - **success:** One pixi task run from the SBOM (plus its layer) alone runs
    `lint-types`, the station suites, the platform bring-up smoke and a channel
    audit; a failure names a gap. A tracked `docs/foundry/` gap list, derived
    from `pixi.toml`, gives every residual solve gap (`conda-smithy`, `crm`,
    `python-agent-platform`) and every fat-only `local-recipes` pin a disposition
    — promote, won't-do or upstream — with an owner. Upstream filing is outward and
    operator-flipped; closing conda-forge gaps is Mason work minted from that list.

- **CAP-14 — The dossier is the cutover's control plane.** (ready 2026-11-10)
  - **intent:** Operators and Smiths read the A→B cutover's state in one place.
  - **success:** `docs-site/src/content/dossier/dossier.yml` (`docsite/content/` until herald Story 43.7, 2026-10-15) carries Estate, Foundation,
    Synthesis and Verified sections stating the A/B roles, the modes of
    `spec-foundry-capability-ledger` `modes.md`, A as the writer until the flip,
    `pyforge.cutover_root`, the four campaign verbs each with a done / not-done line, and SBOM
    claims labelled A-side; every Verified claim cites the capability ledger, the case list or a
    CI run; each A→B and Verified row carries `asserts:` resolved against the steward sprint
    ledger, the capability ledger and the flag tree, and herald's
    `src/shared/packages/pyforge-herald/tests/meta/test_dossier_cutover_claims.py` (herald Story
    51.2) and `pages-check` exit 0. The four campaign verbs: Launch the Foundry is CAP-2's proof;
    Adopt Frames is the nine Frames as pointers written on A (`spec-pyforge-steward:CAP-53`,
    Story 120.4); Build the Intelligence Hub is `spec-pyforge-steward:CAP-52` to
    `spec-pyforge-steward:CAP-56`; Wire every BMAD-suite component is steward Epic 46 on A,
    re-provisioned on B from the adoption register, not established until B's own dispatch runs
    a suite member.

- **CAP-15 — The instruction surface names the estate first.** (shipped 2026-09-26)
  - **intent:** Every harness reads first what this repository is and how A and B
    divide work, then a short behavioural core.
  - **success:** `AGENTS.md` opens with A's identity (control plane and BMAD
    Agentic-SDLC host; the recipe factory one cell), the A/B roles, modes and
    writer lock, and a behavioural core adding heal-the-tissue, state over action,
    read-only harness ledgers and implement / review separation; every removed
    incident note has a pointer target first; scribe's parity meta-test and
    `governance-currency` are green; `CLAUDE.md` stays the `@AGENTS.md` import plus
    Claude-only notes.

## Constraints

- Solutioning before implementation (operator 2026-09-04): this Spec, the cutover spine
  and Epic 44 are BMAD Phase 3 artifacts the operator reviews and refines in iterations;
  no story spec is drafted and no 44.x leaves ledger `blocked` until the operator flips it.
- The seed is Dreams plus memlogs only, `archive/**/.memlog.md` included, with no backfill:
  rendered `SPEC.md`, spines, epics and stories are re-derived in foundry, and a Frame is a
  pointer to the seed; memlog fidelity (44.13) precedes Phase 0.
- The oracle gate is non-negotiable: no rebuilt capability is verified without the archived
  suite or an equivalence check passing against it.
- Mode is per capability (`rebuild`, `retire`, `A-only`, `B-only`), decided by the operator by
  the written rules of `spec-foundry-capability-ledger` `modes.md`; this is not a rebuild of
  everything, and no capability reaches foundry by a file copy.
- The cutover is a flag, not a date: `pyforge.cutover_root` in the `canopy:CAP-13` flag tree
  is the only switch of the root of record and the writer lock. The operator flips
  `pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven;
  nothing flips it automatically. Before the flip `local-recipes` evolves normally; only the
  source of a `rebuilding` row is frozen, and Doctor judges that freeze
  (`spec-pyforge-doctor:CAP-94`).
- `steward cutover apply` and the file manifest are retired (operator 2026-11-10): no
  capability is copied into foundry by a replay; a `rebuild` is a regeneration drill against
  the oracle.
- No symlink is tracked in git; runtime links are generated per machine (symlink on POSIX,
  junction on Windows) and gitignored. Runtime state lives in gitignored `var/`.
- Contract before repo: CAP-1 is not dispatched until this Spec is `ready` and Epic 44
  exists. CAP-1 and CAP-6 are outward; the ledger holds them `blocked` until the
  operator flips each one. Never auto-drained. CAP-13's upstream filing, tracking and
  retiring are the operator's acts alone, recorded in the repo's upstream to-do list
  with `decided_by: operator`; no story performs them (Story 67.4 keeps the list and
  files nothing). CAP-7 is retired; Story 44.10 is never dispatched.
- The SBOM never composes the fat `local-recipes` feature or a `desktop-lab`
  feature; inclusion is "used by PyForge code or needed by a PyForge developer or
  operator workflow". PostgreSQL stays major 17, and libpq 17 in every environment
  (operator 2026-09-26). No Postgres bump, no lifted driver cap and no dropping
  `platform-dev` to clear a solve; if a psycopg / pgvector cap breaks a station's
  suite, the story halts `blocked`. Never push a stub or placeholder `pixi.toml`;
  after any write, verify the full manifest and a `--frozen` re-solve.
- `AGENTS.md`'s managed `bmad:context` block changes only through
  `bmad-project-context` under `spec-pyforge-scribe:CAP-27`. `python-foundry`'s
  instruction surface is B's (writer lock). Every dossier Verified claim cites a
  source; SBOM claims stay A-side until the capability ledger carries them.
- PRs #1563 / #1564 / #1576 are reference only: the stories port their payloads;
  none is merged.
- Foundry is private, permanently (operator 2026-09-04, iteration 4): Pages and the win-64
  leg ride the paid plan; Actions minutes are a standing budget; nothing Mason submits
  carries a foundry URL.
- CI evidence is a real run (spine fnd:AD-23, operator 2026-09-13 D1): the
  authoritative run is fresh-clone local `detectors-ci` + `platform-ci-local`
  (plus CRC IFF the empty repo already carries the estate Helm chart). GHA is a
  twin and may stay red; a registered runner and `steward budget check` (CAP-10)
  are not confirmation gates for 44.3.
- Fresh repo (operator 2026-09-04): no history import. B keeps its repository, its epoch
  (`docs/foundry/EPOCH.md`) and its CI, and reads A at a pinned SHA (operator 2026-11-10).
- The capability ledger (`docs/foundry/capability-ledger.yaml`) is generated by
  `steward cutover plan` from the live Specs (CAP-9); never a hand list. Story 44.1 is retired
  (2026-11-10); its ledger half lands in Stories 121.1 to 121.7.
- No package fold and no tree copy: Stories 44.4, 44.5 and 44.6 are retired (2026-11-10);
  B rebuilds what its ledger rows name.
- The estate `pixi.lock` never absorbs the factory solver farm.
- No `services/` or `:800x` tree; no root `docker-compose.yml`; no
  `src/platform/compliance_face/` as the portal; no lasting `.claude/skills/pyforge-mason/`
  — `A-only` until the cutover flip, never carried to B (B rebuilds Mason's skills under
  `skills/stations/`).
- CAP-3 and CAP-6 are Mason work under Rule 1 and Rule 2: `conda-forge-expert` is
  invoked and a CFE retro lands. Marshal's `Deps:` parser is station-local, so Mason
  gates are ledger state, as 43.6 was behind Mason 13.
- `DW-RT-2026-09-02-2..6` (R-18..R-22) never block CAP-2; they stay steward-owned
  ledger entries.
- Cite this Spec's ids as `fnd:CAP-N` outside this file; the evergreen Spec is not
  re-derived.
- Physical writes under `_bmad-output/projects/pyforge-steward/` with
  `BMAD_ACTIVE_PROJECT=pyforge-steward`; no `bmad-switch` from parallel agents. The
  Tier-3 feed is repaired (`sprint-ledger-sync --project steward --repair-feed`, then
  `story-status-check`) before any ledger write.

## Non-goals

- Re-deciding the modular-monolith topology or any Unifying `CAP-1..19`.
- Renaming the pixi env `python-agent-platform`, or the parked `pap:` Single-Spec merge.
- Rewriting `local-recipes` git history; the fresh repo leaves it behind.
- Closing R-18..R-22 (an Epic 45 candidate).
- Copying the `recipes/` universe or the feedstock mirrors.
- Migrating the 268 registered worktrees.
- Archiving `local-recipes` (CAP-7 retired 2026-09-25).
- A package fold or a tree copy into foundry: `steward cutover apply` and the file
  manifest are retired (operator 2026-11-10).
- Closing conda-forge gaps inside Epic 67; Mason stories are minted from CAP-13's
  gap list.
- Adopting a claim from the BMAD-method whitepaper without re-verifying it
  against the installed skill.
- Carrying rendered planning narrative (research, reviews, proposals, reports, retros, run
  records, per-story specs of shipped stories); `local-recipes` keeps them.

## Success signal

B lands one story on itself: a merge on B's `main` with subject
`Merge <station>/<key> into main`, made by B's own `marshal factory dispatch`, with B's own
`detectors-ci` exit 0 at that SHA, and every ledger row marked `launch: true` reading
`verified-in-foundry` (`fnd:CAP-2`, `launch-slice.md`). Then the operator flips
`pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven, and the
writer lock passes to B. A fresh clone of `rxm7706/python-foundry` runs the regenerated kernel
(core, steward, marshal CLI + MCP) against the thin oracle (`fnd:CAP-11` / Epic 54) and
`mason recipe build factory/recipes/<r>` builds a recipe there with the publish path a
SelfExplainML upload — not an agent-opened conda-forge PR (operator 2026-09-13 D2). Host boot is
not a Launch signal. Two git roots stay live, and `local-recipes` is never archived (CAP-7
retired). Beside it, a laptop on linux-64, osx-arm64 or win-64 installs `pyforge-foundry-full` and
passes the laptop gate from it alone, and the dossier's Verified section cites only ledger,
case-list or CI evidence. Launch stories: 44.3 / 44.7 / 44.12 done; Epic 54 kernel; Epics 120 and
121. Consolidation: Epic 67, herald 26.1, scribe 21.1. Later: CFE rebuild-from-spec (mason 39.2),
44.8, 44.14, 44.15. Out: 44.9, 44.11. Retired: 44.1, 44.4, 44.5, 44.6 (2026-11-10) and 44.10
(2026-09-25).

## Assumptions

- `gh` auth for rxm7706 can create a private repository (CAP-1).
- The paid GitHub plan that serves Pages from the private `local-recipes` today persists
  for foundry (CAP-1, CAP-10).
- No detector enforces a line-count cap on the living Dream; the Dream section grows
  the file past 43.1's 400-line target by design.
- Stock Windows developers (no WSL, no Developer Mode) are a real population; the estate
  is native for them and the host is remote (spine fnd:AD-19).
- The layer environment is linux-64 only because `platform-object-storage`
  declares linux-64 alone (verified live there only), not for lack of builds: every
  backing service publishes osx-arm64 (measured 2026-09-26). A live macOS
  object-storage check would extend the layer to Macs; Windows stays blocked by
  `redis-server`, `garage` and pgvector's libpq-16-only win-64 builds.

## Open Questions

None. `deck-carriage` answered 2026-09-25 (operator): the deck binaries under
`presentations/` stay `A-only`; B regenerates any deck on demand from its `.dc.html`
prototype through herald's deck pipeline, already a `rebuild` row
(`spec-pyforge-herald:CAP-20` to `spec-pyforge-herald:CAP-23`). Nothing is carried and no
story is needed; 44.5's former deck-filter question closes with it.

Also answered: `actions-minutes` (2026-09-04, amended 2026-09-13 D1/D1b — authoritative CAP-1
evidence is fresh-clone local `detectors-ci` + `platform-ci-local`; CAP-10 / 44.15 is
later metering, not a 44.3 gate); `repo-visibility` (2026-09-04 — private, permanently,
spine fnd:AD-14); `flip-trigger` (2026-11-10, second addendum ruling 1 — the operator
flips `pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven;
CAP-8).
