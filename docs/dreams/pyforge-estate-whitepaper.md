---
title: PyForge Estate — A→B Cutover Control Plane
type: dream
owner: steward
status: dreamt
seeded: 2026-09-21
revised: 2026-09-21
audience: internal-ops
purpose: forward-looking-dossier-seed
dossier: https://rxm7706.github.io/local-recipes/dossier/index.html
target: https://github.com/rxm7706/python-foundry
kins:
  - pyforge-unifying-strategy
  - pyforge-charter
  - pyforge-foundry-full-sbom
  - foundry-regenerate-not-fold
  - intelligence-hub
---

# PyForge Estate — A→B Cutover Control Plane

> **Internal Guild dossier seed.** Forward-looking control plane for the cutover
> from **A** (`rxm7706/local-recipes`) to **B** (`rxm7706/python-foundry`), aligned
> to [`docs/dreams/pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md)
> and B’s README. Not a forensic inventory of A-as-found. Audience: operators and
> Smiths running the strangler — not an external marketing narrative.

## Source

| Artifact | Role |
|---|---|
| `docs/dreams/pyforge-unifying-strategy.md` | Grounding, Dream, constraints, cutover Epic 44 / `fnd:CAP-*` |
| `https://github.com/rxm7706/python-foundry` | Lasting root B — opened 2026-09-13 (steward 44.3); four campaign verbs; modes |
| `docs/foundry/` (`EPOCH.md`, `capability-ledger.yaml`, `frames/`, `guards/`, `tracks/`) | Ledger + Frames surface on A |
| `_bmad-output/projects/pyforge-steward/.../specs/spec-python-foundry-cutover/` | Cutover SPEC (`fnd:CAP-1..`) |
| `_bmad-output/projects/pyforge-steward/.../specs/spec-foundry-capability-ledger/` | Ledger contract |
| `_bmad-output/PROJECTS.md` | Eight-station registry; foundry AD-12 note |
| Station Dreams + `src/shared/packages/pyforge-*` | A oracle evidence |
| `docs/dreams/pyforge-foundry-full-sbom.md` | Laptop SBOM — **A-side until ledger absorbs it** |
| `docsite/content/dossier.yml` | Published claim surface |

---

## The Dream (target state)

One Foundry mounts eight canonical stations. Developers and agents enter through
**Foundry Platform** (today `src/platform/` on A — one ASGI process). Station
engines are **rebuilt** under B’s `src/packages/` from Frame + Spec — not folded
from A’s `src/shared/packages/`. The lasting git root is **`python-foundry`**.
Pixi / `python-pixi-solver` powers solves. Steward owns the through-line. The host
is **not** a ninth station.

Until the kernel clears the shared case list, **`pyforge.cutover_root` stays
`local-recipes`**. A remains control and oracle. B is already open (epoch SHA on
`docs/foundry/EPOCH.md`); factory island is on B (44.7). Cutover flip is an
operator flag, not a silent merge.

> Launch the Foundry. Adopt Frames. Build the Intelligence Hub. Wire every
> component of the BMAD-suite.
> — campaign verbs, `python-foundry` README

---

## A and B — who is who

| | **A — `local-recipes`** | **B — `python-foundry`** |
|---|---|---|
| Role | Control plane + legacy oracle | Lasting estate root |
| Opened | Brownfield factory | 2026-09-13 (steward 44.3) |
| Packages | `src/shared/packages/pyforge-*` (oracle) | `src/packages/` **rebuild** from Frame+Spec |
| Platform host | `src/platform/` (live) | Regenerated when Launch rows say so — not a copy |
| `cutover_root` | Current value | Flips here only after case list + operator |
| Dreams / BMAD / Hub invention | Invent here first | Receive verified rebuilds; Hub objects invented on A first |
| Laptop SBOM | `pyforge-foundry-full` compose lives here | Absorb only via Frames / capability ledger |

**Never `move`.** Modes (B README + `docs/foundry/` modes):

| Mode | Meaning |
|---|---|
| `rebuild` | B re-derives from Frame/Spec; A is oracle until `verified-in-foundry` |
| `retire` | Must not appear on B; A may keep history |
| `A-only` | Allowed on A; needs expiry (story id or date) |
| `B-only` | Named on a Spec before `done` |

A long-lived git mirror of A onto B is **out of contract**.

---

## Target topology (Unifying Strategy)

```
User / Agent
    → Foundry Platform (one ASGI: identity, Lane 1, portals, POST /stations/<name>/mcp)
         → eight stations: herald · marshal · atlas · warden · mason · doctor · scribe · steward
              → shared leaf (pyforge-core on A today; rebuild on B)
```

**Grounding overrides greenfield drafts** in the Unifying Strategy: no nine-station
count; no FastAPI `services/` farm as delivery shape; `pap:CAP-*` host space stays
distinct from Unifying bare `CAP-*` until a named steward merge story.

### Eight Smiths (roster does not grow)

| Smith | Owns | A evidence (oracle) | B expectation |
|---|---|---|---|
| Herald | Outward voice / decks | `pyforge-herald` | `rebuild` from Frame |
| Marshal | BMAD loops / Genesis | `pyforge-marshal` | `rebuild` (Launch kernel) |
| Atlas | Ecosystem intelligence / SBOM intake | `pyforge-atlas` | `rebuild` |
| Warden | Compliance gate + CycloneDX emit | `pyforge-warden` | `rebuild` |
| Mason | Recipes / packages / envs (wraps CFE) | `pyforge-mason` | `rebuild`; CFE home on B per cutover |
| Doctor | Fleet diagnostics (advisory) | `pyforge-doctor` | `rebuild` |
| Scribe | Team memory | `pyforge-scribe` | `rebuild` |
| Steward | Provision / keys / platform through-line / cutover | `pyforge-steward` + host | `rebuild` + owns Epic 44 |

Planning ownership: each station’s chain under `_bmad-output/projects/pyforge-<station>/`.
Foundry + platform Specs live under **steward** — there is no ninth project folder.

---

## Campaign — four verbs (operator checklist)

| Verb | Done looks like | Not done |
|---|---|---|
| **Launch the Foundry** | B exists **and** regenerated kernel runs (`estate-smoke`); Launch packages verified | “A’s tree arrived on B” |
| **Adopt Frames** | Company + eight station `.frame.md` (v0.3 draft) are Spec, preflight green | Frames as a copy list of A paths |
| **Build the Intelligence Hub** | Charter / Frames / Tracks / Guards invented on A, then adopted | Inventing Hub-only objects first on B |
| **Wire the BMAD-suite** | Re-provision from the register | `apply --phase 1b`-shaped fairy dust |

Epic 44 / `spec-python-foundry-cutover` rows (44.1 manifest → open foundry → fold packages
as rebuild → CFE home → … → flip `cutover_root`) remain the steward-owned sequence.
44.1 blocked on solutioning is a control-plane fact — do not paper over it in the dossier.

---

## Laptop SBOM — A-honest

`pyforge-foundry-full` is the checkable laptop compose **on A** (PR #1564 /
`docs/dreams/pyforge-foundry-full-sbom.md`). It is **not** yet proof that B has an
equivalent closure.

Until Frames + `capability-ledger.yaml` carry the compose:

- PostgreSQL major **17**; keep `platform-dev`
- Cap `psycopg` / `pgvector` for libpq 17 (do not bump PG 18 to force a solve)
- Never compose fat `local-recipes`; no `desktop-lab`
- Inclusion = PyForge code **or** developer/operator need

Dossier must label SBOM claims **A-side**. Promoting them to B is a ledger/Frame
story, not a docs-only assertion.

---

## Accountability (internal)

1. Dream → Spec → Story before code (`AGENTS.md`; one-chain-per-station).
2. Warden merge-blocks; Doctor advises; Marshal supervises loops.
3. Capability ledger modes; `never_move`; Frame preflight ≠ A/B proof.
4. Realization gate (Unifying Strategy § Where next): **shipped ≠ in effect** —
   done means mechanism live under the intended flag/root, not only tests green on A.

Intelligence Hub vocabulary (Frames / Cogs / Guards / Tracks) maps onto this plane;
formal adoption stays Spec-driven (`docs/dreams/intelligence-hub.md`).

---

## What the dossier must show (this revision)

| Section | Forward-looking job |
|---|---|
| **Estate (01)** | A/B roles, four verbs, modes, cutover_root, SBOM A-honest |
| **Foundation (00)** | Shared leaf as oracle on A + rebuild destiny on B |
| **Stations** | Keep A forensics for now; next pass adds rebuild-vine callouts |
| **Synthesis** | Strangler progress, not only cross-fleet code rhyme |
| **Verified** | What case-list / ledger / CI actually prove |

---

## Non-goals

- Claiming `cutover_root` already flipped
- Describing B as a mirror or subtree of A
- Treating fat `local-recipes` or PG18 bumps as foundry policy
- External “vision deck” tone without control-plane facts
- Ninth station or silent Spec merge of `pap:` into Unifying CAP space

---

## Mental model

```
        invent & prove on A (oracle)
                  │
                  │ rebuild (Frame+Spec)
                  ▼
              python-foundry (B)
                  │
                  │ operator flips cutover_root
                  ▼
           lasting estate root
```

**Include** what the Guild must operate tomorrow.
**Exclude** kitchen-sink and fold mythology.
**Own** the hub — on B when verified, on A until then.

---

## After this seed

1. Keep `docsite/content/dossier.yml` Estate / foundation / synthesis aligned.
2. Steward Epic 44 / ledger updates change this Dream before marketing copy does.
3. Follow-up: per-station rebuild-vine callouts (mode + Frame path + `verified-in-foundry`).
4. Rebuild Pages: `python docsite/build.py` → deploy `docsite/dist/`.
