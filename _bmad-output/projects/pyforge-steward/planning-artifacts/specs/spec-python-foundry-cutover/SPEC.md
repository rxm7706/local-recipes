---
fold-exemption: different-lifecycle
spec: python-foundry-cutover
status: ready
chain: pyforge-unifying-strategy
created: "2026-09-04"
updated: "2026-09-25"
owner-dream: docs/dreams/pyforge-unifying-strategy.md
extends: spec-pyforge-unifying-strategy  # cite this file's ids as fnd:CAP-N outside it; Unifying CAP-1..19 and pap:CAP-1..6 are different sets — never collapse
surface: []
companions:
  - cutover.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
  - ../../../../../../docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md
  - ../../research/technical-pyforge-unifying-strategy-bmad-method-whitepaper-2026-09-25.md
open_questions: []
---

> **Canonical contract.** Re-derived 2026-09-25 from `.memlog.md` (D1–D3,
> regenerate-not-fold, and the 2026-09-25 consolidation of PRs #1563 / #1564 /
> #1576). Invent in `local-recipes`; foundry receives proven capability as
> **regenerated** packages, not a fold of `src/shared/packages/`. **`local-recipes`
> is never archived** (CAP-7 retired 2026-09-25). Extends
> `spec-pyforge-unifying-strategy`; cite this file as `fnd:CAP-1..15`. Decomposed as
> steward **Epic 44** (44.1–44.15), **Epic 54** (kernel) and **Epic 67** (laptop
> SBOM, dossier, instruction surface), with herald **26.1** and scribe **21.1**
> taking the stories on the surfaces they own. 44.4 / 44.5 / 44.6 are parked
> file-move stories and 44.10 is retired — do not dispatch. The cutover is
> regenerative: Dreams and memlogs seed foundry.

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

- **CAP-1 — Open foundry (Phase 0).**
  - **intent:** The operator can create `rxm7706/python-foundry` as a fresh,
    recipe-free, lean-pixi estate with estate-only CI.
  - **success:** The clone exists; no `recipes/` directory; the `environment.yaml`
    export is automated or absent, never by hand. Authoritative proof is a
    **fresh-clone local** run of `detectors-ci` and `platform-ci-local` (plus CRC
    IFF the empty repo already carries the estate Helm chart). GHA is a twin and
    may stay red; force-merge after that local proof is the campaign gate
    (operator 2026-09-13 D1). Fresh-clone local is not provisional.

- **CAP-2 — Realize the estate (Phase 1).**
  - **intent:** Every capability of the estate reaches foundry by rebuild or by move per the
    capability ledger. Launch engines (core, steward, marshal) are **rebuild-from-Frame**
    under `src/packages/`. The BMAD chain is seeded from Dreams and memlogs. Host and
    `django-*` are out of Launch.
  - **success:** Each Launch kernel row is `verified-in-foundry` under its rebuild gate
    (thin archived suite, `fnd:CAP-11`). `src/shared/` may remain on `local-recipes`
    indefinitely; the ledger's A-only rows decide what stays. No Containerfile `COPY` of
    package source. Host boot is not a Launch success criterion. `apply --phase 1a` is not
    the realization path.

- **CAP-3 — CFE on foundry (Phase 2).**
  - **intent:** Foundry gains conda-forge-expert by **rebuild from Specs**, using
    `local-recipes` as the legacy oracle — not a cell move of
    `.claude/skills/conda-forge-expert`.
  - **success:** A foundry-born CFE (when that Story runs) matches the rebuilt
    Spec and the archived suite; until then factory island may resolve CFE on
    `local-recipes`. Story 44.6 (file-move the cell) is parked. Do not require
    `MASON_CFE_ROOT` to stop pointing at local-recipes for Launch.

- **CAP-4 — Factory island (Phase 3).**
  - **intent:** Recipe work runs from `factory/` with its own `pixi.toml` and lock
    and a recipes-only CI.
  - **success:** `mason recipe build factory/recipes/<r>` matches today's CFE wrap;
    the estate lock holds no factory solver dependency; factory CI triggers on
    `paths: factory/**` only.

- **CAP-5 — Working set (Phase 4).**
  - **intent:** Only in-flight and sole-maintainer recipes move.
  - **success:** `factory/recipes/` is the working set under an asserted count
    ceiling; the 7,855-dir universe is not copied.

- **CAP-6 — Mason talks to conda-forge (Phase 5).**
  - **intent:** From foundry, `submit` targets staged-recipes or the bot fork and
    `update` targets the feedstock maintainer-edit path.
  - **success:** Later Phase 5: an agent-opened PR never targets `local-recipes`
    (asserted on the submit path). Out of this campaign; 44.9 stays blocked
    (operator 2026-09-13 D2).

- **CAP-7 — Archive `local-recipes` (Phase 6). RETIRED 2026-09-25.**
  - **intent:** (retired) `local-recipes` was to become read-only history.
  - **success:** None — retired by the operator's no-archive ruling (2026-09-25).
    Two git roots stay live after the `cutover_root` flip; what `local-recipes`
    hosts afterwards is decided per capability by the ledger's modes. Story 44.10
    retires with it (ledger key stays `blocked`, never dispatched). The id is not
    reused.

- **CAP-9 — Capability ledger and rebuild harness.**
  - **intent:** The operator sets a mode per capability; the ledger derives from the Dreams
    and the owner map; a `rebuild` re-derives Spec, spine and epics in foundry from the moved
    memlog and is drained by Marshal with the archive as oracle.
  - **success:** `steward cutover plan` emits the ledger with modes, states, dependencies and
    the four decision signals; a rebuilt capability passes the archived suite or an equivalence
    check before `verified-in-foundry`; a capability in `rebuilding` or `moving` has its source
    frozen and `--append` reports drift against it.

- **CAP-8 — Flag-gated, replayable cutover.**
  - **intent:** The operator can regenerate or append the cutover plan at any time while
    `local-recipes` keeps evolving, replay every move into foundry, and flip the root of
    record by one flag.
  - **success:** `steward cutover plan --regenerate` and `--append` both yield a manifest
    that preserves `moved` rows; `steward cutover apply --phase <n>` is idempotent;
    flipping `pyforge.cutover_root` switches the ledger of record, Mason's targets and the
    loop-home remotes without a redeploy, and flipping back restores them.

- **CAP-11 — Foundry kernel regenerate.**
  - **intent:** The operator can regenerate `pyforge-core`, steward, and marshal in
    foundry `src/packages/` from Frames and Specs against a thin archived-test oracle.
  - **success:** CLI + MCP for those three are green on a python-foundry checkout; one
    marshal dispatch against the foundry remote passes; 44.4 / 44.5 stay undispatched
    file-move stories. Full contract: `spec-foundry-regenerate-not-fold`.

- **CAP-10 — Metered minutes budget.**
  - **intent:** `steward budget` knows the account's GitHub Actions-minutes spend and
    ceiling, so the foundry dispatch, Marshal's drains and the rebuild harness never run
    blind into a billing block again.
  - **success:** Later, when GHA twins or Marshal drains spend minutes:
    `steward budget check` returns a real under/over verdict against the plan's
    included minutes and the declared ceiling from a metering source (the Actions
    billing API through a `user`-scoped credential held in `steward keys`, never
    in the manifest); those drains and the rebuild harness read it as their
    ceiling; the honest-stub property is retired for this source only. Not a
    Launch / 44.3 confirmation gate (operator 2026-09-13 D1b).

- **CAP-12 — The laptop SBOM.**
  - **intent:** A developer laptop installs `pyforge-foundry-full` and from it
    alone runs the stations, local recipe generation and builds, tests, lint and
    the local CI mirrors, and — through a layer environment — the platform local
    stack. It is the default laptop install (a new capability over
    `spec-pyforge-steward:CAP-151`, amended 2026-09-25 by its own memlog). The session and
    runtime default stays `pyforge-guild` (`spec-pyforge-steward:CAP-5`); the laptop installs
    the superset.
  - **success:** `pixi install -e pyforge-foundry-full` solves on linux-64,
    osx-arm64 and win-64 and composes the `build`, `grayskull` and `crm` features
    beside the station features, with `pnpm` in the `python` feature; the
    platform-limited stack (`platform-dev`,
    `platform-object-storage`) solves as a layer environment over it; every
    `postgresql` pin in the estate is `>=17.11,<18`, with psycopg and pgvector capped
    below the first builds that require libpq 18 (psycopg `<3.3` as measured in the lock
    on 2026-09-25 — 3.2.10 already solves on libpq 17.11; Story 67.1 re-measures before it
    pins); neither `local-recipes` nor a `desktop-lab` feature is composed; `AGENTS.md`
    names it the laptop install.

- **CAP-13 — The SBOM is checkable.**
  - **intent:** The operator can prove the laptop needs nothing beyond the SBOM,
    and every gap has an owner.
  - **success:** One pixi task run from the SBOM (plus its layer) alone runs
    `lint-types`, the station suites, the platform bring-up smoke and a channel
    audit; a failure names a gap. A tracked `docs/foundry/` gap list, derived
    from `pixi.toml`, gives every residual solve gap (`conda-smithy`,
    `python-agent-platform`) and every fat-only `local-recipes` pin a disposition
    — promote, won't-do or upstream — with an owner. Upstream filing is outward and
    operator-flipped; closing conda-forge gaps is Mason work minted from that list.

- **CAP-14 — The dossier is the cutover's control plane.**
  - **intent:** Operators and Smiths read the A→B cutover's state in one place.
  - **success:** `docsite/content/dossier.yml` carries Estate, Foundation,
    Synthesis and Verified sections stating the A/B roles, the modes (never
    `move`), `pyforge.cutover_root`, the four campaign verbs each with a done /
    not-done line, and SBOM claims labelled A-side; every Verified claim cites the
    capability ledger, the case list or a CI run; herald's `site-check` is green.

- **CAP-15 — The instruction surface names the estate first.**
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
- The seed is Dreams plus memlogs only: rendered `SPEC.md`, spines, epics and stories are
  re-derived in foundry; memlog fidelity (44.13) precedes Phase 0.
- The oracle gate is non-negotiable: no rebuilt capability is verified without the archived
  suite or an equivalence check passing against it.
- Mode is per capability, decided by the operator on scored signals; this is not a rebuild
  of everything and not a move of everything.
- The cutover is a flag, not a date: `pyforge.cutover_root` in the CAP-13 flag tree is the
  only switch of the root of record; the transition point is the flip (after 44.5 today);
  before it nothing in `local-recipes` is frozen.
- Every move is a replay: a move the `steward cutover apply` step cannot reproduce is
  review-blocking.
- No symlink is tracked in git; runtime links are generated per machine (symlink on POSIX,
  junction on Windows) and gitignored. Runtime state lives in gitignored `var/`.
- Contract before repo: CAP-1 is not dispatched until this Spec is `ready` and Epic 44
  exists. CAP-1, CAP-6 and CAP-13's upstream filing (Story 67.4) are outward; the
  ledger holds them `blocked` until the operator flips each one. Never auto-drained.
  CAP-7 is retired; Story 44.10 is never dispatched.
- The SBOM never composes the fat `local-recipes` feature or a `desktop-lab`
  feature; inclusion is "used by PyForge code or needed by a PyForge developer or
  operator workflow". PostgreSQL stays major 17: no Postgres bump and no dropping
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
- Fresh repo (operator 2026-09-04): no history import; source SHAs live in the
  move-list manifest.
- The move-list manifest (Story 44.1) is derived from the spec-surface map and precedes
  CAP-2. Never a hand list.
- Package fold and the skills / BMAD move are separate stories. Never one.
- The estate `pixi.lock` never absorbs the factory solver farm.
- No `services/` or `:800x` tree; no root `docker-compose.yml`; no
  `src/platform/compliance_face/` as the portal; no `.claude/skills/pyforge-mason/`.
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
- Closing conda-forge gaps inside Epic 67; Mason stories are minted from CAP-13's
  gap list.
- Adopting a claim from the BMAD-method whitepaper without re-verifying it
  against the installed skill.
- Carrying rendered planning narrative (research, reviews, proposals, reports, retros, run
  records, per-story specs of shipped stories); `local-recipes` keeps them.

## Success signal

A fresh clone of `rxm7706/python-foundry` runs the regenerated kernel (core,
steward, marshal CLI + MCP) against the thin oracle (`fnd:CAP-11` / Epic 54)
and `mason recipe build factory/recipes/<r>` builds a recipe there with the
publish path a SelfExplainML upload — not an agent-opened conda-forge PR
(operator 2026-09-13 D2). Host boot is not a Launch signal. Two git roots stay
live, and `local-recipes` is never archived (CAP-7 retired). Beside it, a laptop
on linux-64, osx-arm64 or win-64 installs `pyforge-foundry-full` and passes the
laptop gate from it alone, and the dossier's Verified section cites only ledger,
case-list or CI evidence. Launch stories: 44.3 / 44.7 / 44.12 done; Epic 54 kernel;
44.4 / 44.5 / 44.6 parked file-move. Consolidation: Epic 67, herald 26.1, scribe
21.1. Later: CFE rebuild-from-spec, 44.8, 44.14, 44.15. Out: 44.9, 44.11. Retired:
44.10.

## Assumptions

- `gh` auth for rxm7706 can create a private repository (CAP-1).
- The paid GitHub plan that serves Pages from the private `local-recipes` today persists
  for foundry (CAP-1, CAP-10).
- No detector enforces a line-count cap on the living Dream; the Dream section grows
  the file past 43.1's 400-line target by design.
- Stock Windows developers (no WSL, no Developer Mode) are a real population; the estate
  is native for them and the host is remote (spine fnd:AD-19).
- Scribe's code runs on the last psycopg below the libpq-18 boundary (3.2.10 as measured;
  CAP-12); Story 67.1 proves it against scribe's Postgres suite or halts `blocked`.
- `build`, `grayskull` and `crm` declare no platform restriction, and only
  `platform-dev` and `platform-object-storage` are platform-limited (measured
  2026-09-25); that the union co-solves on all three platforms is what Story 67.1
  proves.

## Open Questions

None. `deck-carriage` answered 2026-09-25 (operator): the deck binaries under
`presentations/` stay `A-only`; B regenerates any deck on demand from its `.dc.html`
prototype through herald's deck pipeline, already a `rebuild` row
(`deck-family-lockstep:CAP-1..4`). Nothing moves, no story; 44.5's former deck-filter
question closes with it.

Also answered: `actions-minutes` (2026-09-04, amended 2026-09-13 D1/D1b — authoritative CAP-1
evidence is fresh-clone local `detectors-ci` + `platform-ci-local`; CAP-10 / 44.15 is
later metering, not a 44.3 gate); `repo-visibility` (2026-09-04 — private, permanently,
spine fnd:AD-14).
