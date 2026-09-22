---
title: PyForge — The Owned Agentic Foundry
type: dream
owner: steward
status: dreamt
seeded: 2026-09-21
purpose: whitepaper-seed-for-dossier
dossier: https://rxm7706.github.io/local-recipes/dossier/index.html
kins:
  - pyforge-charter
  - pyforge-unifying-strategy
  - pyforge-foundry-full-sbom
  - intelligence-hub
  - one-chain-per-station
---

# PyForge — The Owned Agentic Foundry

> **Whitepaper seed.** Distills this repository's own Dreams, BMAD planning trees,
> station packages, and published dossier into one publishable thesis — the same
> role `docs/dreams/intelligence-hub.md` plays for the OpenTeams Intelligence Hub
> paper. The live dossier at
> [rxm7706.github.io/local-recipes/dossier](https://rxm7706.github.io/local-recipes/dossier/index.html)
> is rebuilt from `docsite/content/dossier.yml`; this file is the long-form prose
> that dossier section **Estate** now summarises. Nothing below invents a product
> that is not already named in-repo.

## Source

Evidence read for this seed (2026-09-21). Prefer these paths over memory:

### Dreams & governance
- `docs/dreams/pyforge-charter.md` — Guild constitution; eight Smiths; mission line
- `docs/dreams/pyforge-unifying-strategy.md` — hub-and-spoke Foundry; Grounding overrides greenfield prose
- `docs/dreams/pyforge-{herald,marshal,atlas,warden,mason,doctor,scribe,steward}.md` — station Dreams
- `docs/dreams/pyforge-foundry-full-sbom.md` + `docs/foundry/pyforge-foundry-full-sbom.md` — laptop SBOM campaign
- `docs/dreams/intelligence-hub.md` — rhetorical model (Frames / Cogs / Guards mapping discipline)
- `docs/dreams/one-chain-per-station.md`, `docs/governance/` — minting and sprawl rules
- `docs/foundry/EPOCH.md`, `docs/foundry/capability-ledger.yaml`, `docs/foundry/frames/` — Foundry cutover plane
- `AGENTS.md` — Dream-first, `pyforge-guild` session env, no fat default

### BMAD planning (`_bmad-output/projects/`)
- `pyforge-marshal/planning-artifacts/PRD.md` + `architecture.md` (+ MCP / bmad-infra / cf-atlas architecture slices)
- Peer trees: `pyforge-{atlas,herald,mason,doctor,steward,scribe,warden}/planning-artifacts/` (architecture, test-architecture, specs)
- Steward research / scorecards under that project's `planning-artifacts/` (Build League, red-team, canopy closeouts)

### Code & compose
- `src/shared/packages/pyforge-{core,atlas,doctor,herald,marshal,mason,scribe,steward,warden}/` (+ `pyforge-testing-kit`)
- `src/shared/packages/django-*` portals; host at `src/platform/`
- Root `pixi.toml` — feature topology; env `pyforge-foundry-full` (SBOM); env `local-recipes` (fat factory, not Guild runtime)
- `docsite/content/dossier.yml` + `docsite/README.md` — published claim surface

### Integrity note
Figures on the dossier that carry `check:` are machine-verified by
`docsite/tools/verify_claims.py`. Prose claims in this whitepaper that are not so
tagged should be treated as thesis until a Spec or verify row backs them.

---

## The Dream

An organisation can run its **entire software lifecycle** — not only coding — with
autonomous agents a human can **trust**: every stage owned by a named Smith, every
artifact traced to a Spec, every Spec to a human Dream, autonomy a **governed
gradient**, and no station allowed to report a green it did not earn.

That factory is **PyForge**: eight stations on one shared leaf (`pyforge-core`),
mounted on a Foundry Platform host (`src/platform/`), planned through BMAD, and
closed as a **checkable laptop SBOM** named `pyforge-foundry-full` — not as a
ten-gigabyte kitchen-sink feature dump.

> Humans Dream. Agents Deliver. Governed. Auditable. Production-ready.
> — mission line, `docs/dreams/pyforge-charter.md` (canonized 2026-07-25)

PyForge is already an Intelligence Hub in miniature (see `intelligence-hub.md`):
owned context in tracked files, workers as station skills, workflows as BMAD /
Marshal loops, checks as detectors and Warden, evidence in ledgers and Tracks.
The Dream is that the estate says that out loud — in dossier, Frames, and Specs —
rather than only by accident of good engineering.

---

## 1. Mission — Build More Architect Dreams

The Charter Dream (`docs/dreams/pyforge-charter.md`) constitutes **the PyForge Guild**:
eight Smiths, each holding a station of the Agentic SDLC and wielding Skills; the
**Guildhall** is where their work stands open.

| Smith | Station job (one line) | Package |
|---|---|---|
| **Herald** | Capture the Dream as decks; proclaim releases | `pyforge-herald` |
| **Marshal** | Orchestrate BMAD loops; Genesis seeds the operating model into other repos | `pyforge-marshal` |
| **Atlas** | Produce feedstock / upstream intelligence (data, not verdicts) | `pyforge-atlas` |
| **Warden** | Compliance / dependency hygiene gate — sole PR verdict authority | `pyforge-warden` |
| **Mason** | Recipe / package / environment craft over conda-forge-expert | `pyforge-mason` |
| **Doctor** | Fleet diagnostics — advisory findings, never a second PR gate | `pyforge-doctor` |
| **Scribe** | Capture / compile / recall team memory into the repo | `pyforge-scribe` |
| **Steward** | Provision, credentials, deploy, ops; owns Foundry Platform through-line | `pyforge-steward` |

The dual ecosystem is intentional: **PyPI + conda-forge**. Packaging is not a side
quest; Mason's station and the BoM features (`build`, `grayskull`, `crm`, …) are
first-class Guild work.

### Dream → Spec → Story (non-negotiable)

`AGENTS.md` and `docs/governance/`: every non-trivial effort enters as a Dream
under `docs/dreams/`; `bmad-spec` derives the Spec under
`_bmad-output/projects/<station>/planning-artifacts/`; a numbered Story exists
before code outside dreams/spec. **One chain per station** — append to the station
Dream unless a closed `fold-exemption` applies (`different-owner`,
`different-lifecycle`, `cross-station-seam`, `governance`).

That is the accountability plane for *how work is born*, parallel to Warden's
accountability for *whether work may land*.

---

## 2. Topology — hub, spokes, leaf, host

### Grounding (Unifying Strategy wins over greenfield drafts)

`docs/dreams/pyforge-unifying-strategy.md` opens with an authoritative **Grounding**
section: Foundry Platform already exists at `src/platform/` (cookiecutter-Django,
OIDC, Langflow Pattern A, DB-GPT Pattern B sidecar, Helm/OCP). Steward owns the
through-line. The host is **not** a ninth station — Charter §5; the roster stays eight.

Two CAP namespaces must not be collapsed: host work cites `pap:CAP-*` from
`spec-python-agent-platform`; Unifying Strategy has its own `CAP-*` space. The
architecture is a **modular monolith**: MCP and portal compute mount on the host
ASGI (`POST /stations/<name>/mcp`), not a farm of nine public FastAPI processes.

### Shared leaf

`pyforge-core` is a pure-stdlib leaf (`dependencies = []`) with an AST meta-test
against non-stdlib imports. It owns mechanisms stations used to reinvent: verdict
`Lattice`, atomic write, report envelopes, hooks (`pyforge.core.hooks`), and the
unified `pyforge <station> …` dispatcher that forwards to each station's primary
console script. The dossier foundation section is the verified public statement of
this spine.

### Pixi features as the physical topology

Stations are path-dependencies under root `pixi.toml`, each with a lean
`pyforge-<station>` environment (`no-default-feature`) so loop worktrees never
materialise the fat factory by accident. Runtime session env is **`pyforge-guild`**.
Container union and SBOM envs compose deliberately; see §5.

```
                    ┌─────────────────────────┐
                    │   Foundry Platform host │
                    │      src/platform/      │
                    └───────────┬─────────────┘
                                │ mounts / MCP
         ┌──────────┬───────────┼───────────┬──────────┐
         ▼          ▼           ▼           ▼          ▼
      Herald    Marshal      Atlas      Warden     … (8)
         │          │           │           │
         └──────────┴─────┬─────┴───────────┘
                          ▼
                   pyforge-core (leaf)
```

---

## 3. The eight stations — what the code actually does

Summaries grounded in package READMEs under `src/shared/packages/` and station Dreams.
Status labels follow `docs/dreams/README.md` (dreamt → pitched → specified → realized).

### Herald — proclaim
Dream-to-deck bridge (`herald deck seed|pull|…`) against Claude Design; Four Moments
dashboard. Outward voice of the Guild. **Realized** in-repo.

### Marshal — command
BMAD-loop supervisor: gates-as-objects, run supervision, landing, fleet status,
closed verdict lattice. **Genesis** (`marshal seed init|adopt|check|update`) installs
the operating model into other git repos — machinery, not a one-off template copy.
**Realized.**

### Atlas — chart
Kedro/Dagster/DuckDB intelligence pipelines (feedstock, PyPI intelligence, universal
SBOM, upstream discovery, VCS health, vulnerability, …) plus MCP read surface.
Produces **data** Warden may consume; does not issue the PR verdict. **Realized.**

### Warden — judge
Unified dependency-hygiene + vulnerability gate (`deptry` + `osv-scanner` →
`ComplianceReport`). Sole strict CI exit-code gate among peer diagnostics. Plugin
bundle on `pyforge.core.hooks`. **Specified / shipping.**

### Mason — forge packages
`mason recipe|package|environment` — wraps conda-forge-expert craft by subprocess
rather than forking it. Ships artifacts; does not judge landings. **Specified.**

### Doctor — diagnose
`doctor check|monitor|diagnose` consolidates signals into advisory `DoctorReport`
envelopes. Explicitly **not** a second PR gate. **Realized.**

### Scribe — remember
`scribe capture|graph compile|recall` — append-only team memory under
`.claude/memory/`, visible to humans and agents. **Realized.**

### Steward — provision
`steward keys|deploy|provision|budget|sync|workspace` — Duty contract, Foundry
Platform ownership, ops through-line. **Realized** as station; platform epics are
the living canopy program in `_bmad-output/projects/pyforge-steward/`.

Django portals (`django-*`) and the host give the Guildhall its chrome; engines stay
independently installable.

---

## 4. Accountability — gradients, not leaps

Four interlocking controls:

1. **Dream-first minting** — no Story without Spec without Dream (`AGENTS.md`).
2. **One chain per station** — sprawl checks and fold-exemptions
   (`docs/governance/`, `one-chain-per-station`).
3. **Verdict lattice** — shared `pyforge-core` vocabulary; Warden gates merges;
   Doctor advises; Marshal supervises loops without laundering false greens.
4. **Foundry regenerate-not-fold** — capability ledger modes (`rebuild|retire|A-only|B-only`);
   never silent path-rename as "migration" (`docs/foundry/`,
   `docs/dreams/foundry-regenerate-not-fold.md`).

The Intelligence Hub whitepaper's Guards / Gates / Tracks map cleanly here: station
detectors and Warden plugins as Guards; CI and Marshal landing rules as Gates;
BMAD ledgers, Scribe memory, and foundry Tracks as evidence. The Spec derived from
`intelligence-hub.md` decides which names PyForge adopts formally; this estate already
behaves like that plane.

---

## 5. The laptop SBOM — `pyforge-foundry-full`

### Thesis

A developer laptop should install **one** composed environment —
`pixi install -e pyforge-foundry-full` — and from it alone: install, launch apps,
test, lint, run local CI mirrors, and bring up platform plugins via **existing**
features. That composed closure **is** the SBOM.

The fat `local-recipes` **feature** (~200+ pins / multi-GB) is a historical recipe
factory dump. **Never compose it** to paper over a missing union. No `desktop-lab`
feature. Lean station envs use `no-default-feature` so worktrees stay honest.

### Inclusion rule (usage, not a name blacklist)

**In** if used by PyForge **code** or required by a PyForge **developer/operator**
workflow. **Out** if unused kitchen-sink — even if pinned today under fat
`local-recipes`. Promote via the feature that owns the dependency.

### Hard operator constraints (2026-09-21 campaign / PR #1564)

Documented in `docs/dreams/pyforge-foundry-full-sbom.md` and
`docs/foundry/pyforge-foundry-full-sbom.md`:

| Constraint | Why |
|---|---|
| PostgreSQL **major 17** (`>=17.11,<18`) | Intentional estate pin — do not bump to 18 to clear a solve |
| Keep **`platform-dev`** in the foundry-full compose | Do not drop the feature to dodge the solver |
| Cap **`psycopg`** `>=3.2.9,<3.2.10` and **`pgvector`** `>=0.8.0,<0.8.2` | Higher floors pull libpq 18; last good psycopg-c on libpq 17 is 3.2.9 |
| `pixi.toml` integrity (~290KB+) | Stub/`PLACEHOLDER` auth probes corrupted CI; restore from known-good, never leave a stub |
| Edit SBOM campaign on **PR #1564** only | No side PRs; Dream → Spec → Story before further realization |

### Phase map

1. **BoM + platform stack** — compose `build` / `grayskull` / `crm` (+ `conda-smithy` when solvable) with `platform-dev` / `platform-object-storage` (+ `python-agent-platform` when solvable) and `pnpm` on an existing feature; land what solves; ticket the rest.
2. **Laptop gate** — CI install + list + channel audit + lint/tests/local CI + platform smokes. Failure means SBOM incomplete.
3. **OpenTeams triage** — ticket every CF gap and every fat-only pin (promote or won't-do).
4. **Point the estate** — CFE / AGENTS / Mason docs → foundry-full.
5. **Close conda-forge gaps** — execute the ticket list.

Residual unions called out in the SBOM Dream (do not fat-compose): `conda-smithy`
vs newer `conda`/`py-rattler` from `build`; `python-agent-platform` / Langflow vs
pandas·onnxruntime in the station union.

### Authoritative compose line

See root `pixi.toml` env `pyforge-foundry-full` (features list is the contract;
comments forbid pulling fat `local-recipes`). Re-read the file before publishing
numbers — the line moves only by PR.

---

## 6. Foundry cutover — regenerate, do not fold

`docs/foundry/` and the regenerate-not-fold Dream: lasting root is
`python-foundry` (epoch / remote named in `EPOCH.md`). Capability rows use ledger
modes; Frames under `docs/foundry/frames/` are the identity surface
(`pyforge/<station>`). Repository A (`local-recipes`) remains oracle under PIN
until verified rebuilds land on B. Steward carries platform ownership without
minting a ninth station.

This is the same philosophy as Nebi-on-pixi-on-conda in the Intelligence Hub paper:
compound shared abstractions; do not invent a second distribution by copying a
brownfield tree and renaming it.

---

## 7. Publication surface — dossier as claim ledger

The public dossier is not hand-edited HTML. **Source of truth:**
`docsite/content/dossier.yml` → `python docsite/build.py` →
`dist/dossier/index.html` (and artifact single-file). Stats with `check:` are
re-verified by `docsite/tools/verify_claims.py`.

Existing dossier spine (reverified 2026-09-13 per file header):

| Section | Role |
|---|---|
| Foundation | `pyforge-core` leaf, dispatcher, seven consolidated mechanisms |
| Eight station sections | Per-Smith verified claims from source |
| Synthesis | Cross-fleet patterns |
| Verified | What this pass proved / still open |

**Estate** (added with this whitepaper) summarises §§1–6 for readers who land on
the dossier first; this Dream remains the long form.

Republish loop (`docsite/README.md`): edit YAML → build → verify → Pages deploy.

---

## 8. What it looks like when real

- [ ] A new contributor installs `pyforge-guild` for daily CLI work and
      `pyforge-foundry-full` when they need the full laptop SBOM — never the fat
      feature by accident.
- [ ] Every station answers `pyforge <station> …` through the core dispatcher.
- [ ] Warden is the only merge-blocking compliance gate; Doctor stays advisory.
- [ ] Dreams append on station files; Specs live under `_bmad-output/projects/…`;
      Stories exist before code.
- [ ] Platform host mounts stations without importing `pyforge.*` engines directly
      (port/seam rules in AGENTS.md).
- [ ] PG17 + `platform-dev` + libpq17 caps hold; SBOM Phase 2 gate is green.
- [ ] Dossier stats that claim counts still pass `verify_claims.py`.
- [ ] Intelligence Hub vocabulary — where adopted — is named in Specs, not only in prose.

---

## 9. Non-goals

- Treating fat `local-recipes` as the developer SBOM
- Bumping PostgreSQL to 18 (or dropping `platform-dev`) to force a pixi solve
- A ninth "platform" station or a `desktop-lab` kitchen sink
- Silent folder renames sold as Foundry migration
- Publishing dossier HTML without updating `dossier.yml`
- Claiming Hub marketplace / Frames economy outcomes that only exist in
  `intelligence-hub.md` thesis until a Spec says otherwise

---

## 10. Mental model

```
Dream  →  Spec  →  Story  →  code
  ↑         ↑         ↑
Charter   BMAD     Marshal loop / CI
                Warden gate · Doctor advise

eight Smiths on pyforge-core
         mounted on src/platform/
         closed by pyforge-foundry-full (SBOM)
         told by dossier.yml → Pages
```

**Include** what PyForge code or operators need.
**Exclude** unused kitchen-sink; never compose the fat feature.
**Own** the hub — context, workers, workflows, checks, evidence — inside a
perimeter the Guild can audit.

---

## After this seed

1. Keep `docsite/content/dossier.yml` Estate section aligned with this file.
2. `bmad-spec` any adoption decisions that promote Hub vocabulary or SBOM Phase 2+
   into Specs with acceptance checks.
3. Continue SBOM Phases 2–5 on PR #1564 only (see `pyforge-foundry-full-sbom` Dream).
4. Rebuild and republish the dossier when Estate claims change:
   `python docsite/build.py` (or `pixi run` site task if configured) → deploy Pages.

