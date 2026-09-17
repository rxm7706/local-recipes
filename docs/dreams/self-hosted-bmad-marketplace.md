---title: The estate hosts its own BMAD catalog, not Claude's public marketplace
type: dream
owner: steward
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `self-hosted-bmad-marketplace`).


# The estate hosts its own BMAD catalog, not Claude's public marketplace

> **Seed Dream.** Operator asked 2026-09-14 to capture "what you would still invent"
> after the suite on A is fully wielded: a self-hosted App Store. Live org
> inventory the same day (bmad-code-org, openteams-ai, nebari-dev,
> ownyourintelligence.ai) is recorded below so later research and `bmad-spec`
> do not re-discover it from chat. Scribe recall that morning:
> `scribe recall "self-hosted BMAD marketplace Hub Layer 3 labs" --mode planning`
> → **no grounded answer** — no prior team decision or Dream exists.

## The Dream

The estate points installers and agent harnesses at **our** module and skill
catalog — air-gapped if need be — and reviews what we publish. Claude's public
plugin marketplace and github.com are optional upstreams, not the only index.

A self-hosted App Store, in the shape that already exists: fork or mirror
`bmad-plugins-marketplace`, put `registry/` on internal git or object storage,
point the installer and Claude/Codex `extraKnownMarketplaces` at that clone,
use Builder / module-template (and SKF) as the publish path, add trust review
of our own.

What the org still does not ship — and this Dream names as the product — is a
hosted browse/buy UI, an air-gap index, billing, and Hub Layer 3. Those are
**three different SKUs**. Mixing them is how Hub LC-3 got bundled with
"Desktop/Web Application." Keep them distinct.

## Why now

Full BMAD-suite integration on A is done (steward Epics 46 and 47 `done`,
adoption register 13/13 `wield`). `spec-bmad-suite-lifecycle` still records
**"The whole labs marketplace"** as a non-goal of *that* chain — skill-by-skill
labs, never the store. Hub Launch (CAP-1..4) still parks **Skills / Agent
Marketplace** as later-cap **LC-3**. Air-gap cannot depend on github.com plus
Claude's public marketplace. This Dream is the later product those two
contracts deferred, not a reopen of either.

## Three SKUs (conclusion — do not collapse)

| SKU | Artifact | Reuse | Still invent |
|---|---|---|---|
| **A — BMAD module/skill catalog** | YAML registry + `npx bmad-method install` + Claude/Codex `extraKnownMarketplaces` | Fork/mirror [bmad-plugins-marketplace](https://github.com/bmad-code-org/bmad-plugins-marketplace); Builder + [bmad-module-template](https://github.com/bmad-code-org/bmad-module-template) + SKF as publish; [bmad-plugins](https://github.com/bmad-code-org/bmad-plugins) as the public Claude/Codex shape | Trust review of our own; air-gap **YAML** index; browse UI if we want more than a git tree |
| **B — Claude skill registry** (optional second face) | Claude Code skill dirs | Consume [nebari-dev/skillsctl](https://github.com/nebari-dev/skillsctl) (`explore` / `install` / `publish`, ConnectRPC + SQLite + OIDC). Kin to SKF, not an adoption | Point it at an internal clone; steward/object-storage wiring. Do not mint a second registry |
| **C — Hub Layer 3** | Ops / Cogs / Frames / Guards across independent Hubs; Tracks stay home | Vocabulary from the whitepaper / field guide; Frame Spec v0.2; nebari-frames as a *pattern*; [nebari-catalog-pack](https://github.com/nebari-dev/nebari-catalog-pack) + Harbor + nebi for **OCI packs** | The four-class marketplace, billing, inter-Hub exchange. Still **thesis** upstream (field guide 2026-08-18) |

**v1 default candidate (not chosen):** SKU A only. B is a later face. C stays
on Hub `later-caps.md` LC-3 until someone hoists it.

## What is real (measured 2026-09-14, not remembered)

### On A

- No hosted App Store. The suite **consumes and authors** catalogs.
- `spec-bmad-suite-lifecycle` non-goal: "The whole labs marketplace."
- `spec-intelligence-hub` Launch non-goal: marketplace / Desktop-Web App;
  LC-3 is adopt-anytime, not forbidden, not Launch.
- Scribe: no plugin packaging until a second consumer repo.
- Object storage is a **consumed** kind (`docs/dreams/platform-object-storage-kind.md`
  realized; steward Epic 50). A YAML or tarball index may live there. We do
  not become the operator of a fourth infra kind.
- `bmad-builder` is already wielded (`steward provision --module bmb`).
- `bmad-module-template` is authoring-only (steward 52.1 / [[suite-scaffold-and-mybmad-sidecar]]).
- MyBMAD is a **sprint GPS sidecar**, never a store (`spec-bmad-suite-lifecycle`
  and 52.1). [bmad-method-ui](https://github.com/bmad-code-org/bmad-method-ui)
  is the same class.

### bmad-code-org (live `gh repo list` 2026-09-14)

| Repo | Role |
|---|---|
| [bmad-plugins-marketplace](https://github.com/bmad-code-org/bmad-plugins-marketplace) | Official YAML registry, schema, trust tiers, PR submit, Claude `extraKnownMarketplaces`. Index at check time: **3 modules** |
| [bmad-plugins](https://github.com/bmad-code-org/bmad-plugins) | Claude + Codex plugin marketplace (`bmad-method` + `bmad-toolbox`) |
| [bmad-builder](https://github.com/bmad-code-org/bmad-builder) | Author / validate / distribute |
| [bmad-module-template](https://github.com/bmad-code-org/bmad-module-template) | Scaffold + `marketplace.json` |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | `npx bmad-method install` / `--custom-content` |
| [bmad-method-ui](https://github.com/bmad-code-org/bmad-method-ui) | VS Code + MyBMAD `web/` — not a store |

Outside the org, still relevant: SKF (`armelhbobdad/bmad-module-skill-forge`);
labs (`bmad-labs/skills`). `bmad-automator` is archived.

### ownyourintelligence.ai (field guide, fetched 2026-09-14)

A field guide, not a product. Distils the OpenTeams whitepaper *The Distributed
AI Economy* (Oliphant, Rev 9; canonical git
[openteams-ai/inthub-whitepaper](https://github.com/openteams-ai/inthub-whitepaper)
tag `v9` — cite that, never a PDF URL alone). Four traded classes: Ops, Cogs,
Frames, Guards. Tracks stay home.

Its own maturity ledger (site audit date **2026-08-18**, still the live copy
today) puts **“public marketplace” under thesis**. Nearest live analogue named
there: nebari.dev “Community hub (coming soon).” Collab Desktop is listed as
**exists** on `openteams.com` — that is the Desktop/Web Application
`spec-intelligence-hub` already refused to rebuild.

Leverage: vocabulary and “Tracks stay home.” Not a registry, installer, or
billing system. Do not endorse or market OpenTeams.

### openteams-ai (live `gh repo list` 2026-09-14)

No store. Protocols and distribution only.

| Repo | What it is | For this product |
|---|---|---|
| [frame-spec](https://github.com/openteams-ai/frame-spec) | Frame markdown + YAML (v0.2). No registry. RB-1: no LICENSE file and no git tag as of 2026-09-09 | Already used as git Frames (Hub CAP-2). Wrong artifact for BMAD modules. In-repo four-field preflight only — do not bind ACs to `tools/validate_frames.py` |
| [inthub-whitepaper](https://github.com/openteams-ai/inthub-whitepaper) | Rev 9 source of record | Cite by tag; do not reproduce |
| [apollo-capabilities](https://github.com/openteams-ai/apollo-capabilities) | Community Apollo bits as **OCI via nebi** | Same shape as conda/OCI publish, not `extraKnownMarketplaces` |
| checkmaite / datamaite / modelmaite | MAITE wrappers | Unrelated |
| POST Python / `pp*` | SciPy rebuild | Unrelated |

### nebari-dev (live `gh repo list` 2026-09-14)

This is the leverage, and it is **three different products**. Hub Dream RB-3
(2026-09-09) already mapped most of this; today's check confirms it still holds.

**Closest to a skill App Store — [skillsctl](https://github.com/nebari-dev/skillsctl)**
(Apache-2.0, last push 2026-08-26). CLI + ConnectRPC registry + SQLite BLOB
store + OIDC + `explore` / `install` / `publish` for **Claude Code skills**.
Docs: https://packs.nebari.dev/skillsctl/. Local backend: `DEV_MODE=true go run
./backend/cmd/server` on `:8080`. Hub research: “kin to SKF, not an adoption.”
README still says it **ships as the Claude Code skill registry**.

**Successor investment — [nebari-frames](https://github.com/nebari-dev/nebari-frames)**
(beta, Apache-2.0, Helm `oci://quay.io/nebari/charts/nebari-frames`). Hosted UI
+ CLI + MCP for **Frames** (context slots, inheritance, RBAC). README:
borrowed registry foundations from skillsctl; **new work goes here**.
SQLite single-writer, `replicaCount: 1` — a fourth infra kind, already parked
(Hub LC-2 / B9; git is our Frame store). Wrong artifact for BMAD modules.

**Marketplace-in-miniature for packs, not agents**

- [nebari-catalog-pack](https://github.com/nebari-dev/nebari-catalog-pack) —
  browses an **OCI** pack registry and installs packs into GitOps as ArgoCD
  Apps. Hub Dream: “the marketplace in miniature.”
- [software-pack-dashboard](https://github.com/nebari-dev/software-pack-dashboard)
  — running list of Nebari software packs.
- [nebi](https://github.com/nebari-dev/nebi) — OCI / pixi publish. Live scope
  is environment management; the paper’s larger “package Frames/Cogs/Ops/Guards
  across Hubs” role remains roadmap.
- [harbor-pack](https://github.com/nebari-dev/harbor-pack) — Harbor; air-gap
  **container** registry, not a BMAD YAML index.

**Do not reuse as the BMAD store**

- [collab-hub-pack](https://github.com/nebari-dev/collab-hub-pack) — Collab API
  (Frames store on fs / S3 / Postgres). Confirms the Desktop/Web Application
  non-goal — it exists upstream.
- [nebari-landing](https://github.com/nebari-dev/nebari-landing) /
  [apps-pack](https://github.com/nebari-dev/apps-pack) — can *host* a UI on the
  cluster; they are not a catalog.

## What we reuse vs invent

**Reuse (SKU A)**

1. Fork or mirror `bmad-plugins-marketplace` (schema, trust tiers, PR submit).
2. Host `registry/` on internal git **or** the consumed object-storage kind.
3. Point `bmad-method install` / `--custom-content` and Claude/Codex
   `extraKnownMarketplaces` at that clone.
4. Publish via Builder + module-template + SKF (already wielded / authoring-only).
5. Trust review of **our** listings — the public marketplace's tiers are a
   starting vocabulary, not a delegation of review.

**Invent (the product gap)**

1. Hosted browse / install UI — if v1 is more than a git tree. Not MyBMAD,
   not Collab, not nebari-frames.
2. Air-gap **YAML** index (object storage or git bundle). Harbor/catalog-pack
   cover OCI packs, not this schema.
3. Billing — candidate **non-goal for v1** (open question).
4. Hub Layer 3 (SKU C) — still thesis; not this Dream's v1 unless hoisted.

## Constraints

- Owner **steward** (suite install, object storage, Hub later-caps).
- AD-1: PostgreSQL + Redis + Kubernetes. Object storage is consumed, not
  self-hosted in Helm. **Do not** stand up skillsctl or nebari-frames SQLite
  as a fourth kind we operate.
- Do not replace Foundry with Nebari. Do not replace `conda-forge-expert`.
- Do not endorse or market OpenTeams. Distil; do not reproduce the whitepaper
  or commit its PDF.
- Do not rebuild Collab / Desktop-Web Application. MyBMAD stays a sidecar.
- Do not flip Epic 44 `blocked` keys or unpark 44.4 / 44.5 / 44.6.
- Foundry-product Dreams after 54.5 are authored on B. This is **A-only**
  (factory / suite / Hub).
- Suite-lifecycle's "whole labs marketplace" non-goal still holds **for that
  Spec**. This Dream is the later product, not a silent drop of that line.
- No station story and no ledger row until open questions close and
  `bmad-spec` (or a hand stub that then re-derives) settles the contract.

## Non-goals

- Reminting Hub CAP-1..4 or Launch.
- Dumping the whole labs marketplace into `.claude/skills/` (CAP-6 consent
  list stays).
- Becoming operator of a fifth infra kind.
- Folding `src/shared/packages/` (44.4 parked).
- First-install on B / P18.
- Replacing conda-forge-expert.
- Endorsing the OpenTeams store or calling Layer 3 "the OpenTeams marketplace"
  (the field guide de-branded it).
- Binding acceptance criteria to `frame-spec`'s unlicensed validator.
- Shipping billing, four-class exchange, or Collab in v1 unless an open
  question is answered that way.

## Open questions for the Spec

Answered 2026-09-15. Recorded in § *Operator rulings* below. They bind the
Spec re-derive. The Dream is `specified` only after that Spec is `ready`.

1. **v1 SKU** — A only, or A plus a consumed skillsctl face (B) in the same
   contract?
2. **Browse UI in v1** — git + `extraKnownMarketplaces` is enough, or do we
   invent a hosted browse/install surface (and where does it run)?
3. **Registry home** — internal git, object storage, conda channel, or a
   switchable set?
4. **Fork vs mirror** of `bmad-plugins-marketplace` — and do we carry their
   public index or start empty?
5. **Trust review** — who reviews our listings, and do we reuse their trust
   tiers or write our own?
6. **Billing** — non-goal for v1, or a named later-cap on *this* Spec?
7. **Layer 3 / Frames** — hoist the whitepaper marketplace, or only estate
   Frame list/share/add on the same rails?

## Operator rulings (accepted 2026-09-15)

Operator approved the session plan. Short names from the seed stay; each is
defined in prose here.

**SKU A** = our BMAD module catalog (YAML the installer already understands).
**SKU B** = a Claude Code skill store (`skillsctl`). **SKU C / Layer 3** =
buying and selling Frames, Cogs, Ops, Guards across independent Hubs, plus
billing. **LC-2** = Hub's parked "Frame registry." **LC-3** = Hub's parked
"skills / agent marketplace" ticket (this Dream owns the BMAD-catalog half).

1. **v1 is our BMAD catalog plus estate Frames on the same rails.** Not the
   Claude-skill store. That store gets an empty *source slot* so it can plug
   in later without a rewrite.

2. **A thin browse list in v1.** Operators can read the catalog (modules and
   Frames, trust tier, link or install hint). Not a click-to-install App
   Store. Not MyBMAD, Collab Desktop, or Nebari's Frames website. Install
   still uses `bmad-method install` / pixi.

3. **Git is where listings are edited. Shipping is a config switch.**
   Default ship path: a small pixi/conda package on the channel we already
   use (SelfExplainML locally; Artifactory when air-gapped). Object storage
   and a git bundle / tarball are extra backends you can turn on. Adding a
   backend later is a plugin, not a new product.

4. **Our repo, their file format. Not an automatic mirror.** Start with no
   community modules. We may point at official modules we already wield.
   Their public catalog is an optional *source plugin*, default off. The
   2026-09-14 "three modules" count is stale — do not bake in a number.

5. **Steward reviews our list.** Reuse their tier *names*: Unverified
   (validator passed), Community Reviewed (steward approved our PR), BMad
   Certified (operator endorsed, or already in the wielded suite). Their
   team does not review us. Every listing names which *source* produced it.

6. **No billing on this Spec.**

7. **No Layer 3.** Frame list / share / add-as-a-reviewed-git-listing is in
   (Hub LC-2 is done here). Frame files stay under `docs/foundry/frames/`.
   Do not stand up Nebari Frames or trade with other Hubs.

Creating a new GitHub repo for the catalog still needs operator confirm at
that story. Do not flip Epic 44 `blocked` keys.

## Kinships

[[intelligence-hub]] (Layer 3 / LC-3; Desktop/Web Application stays a
non-goal; Frames stay git) · [[bmad-suite-lifecycle]] ("whole labs
marketplace" non-goal of *that* chain) · [[bmad-suite-channel-product]]
(private channel as a marketplace in miniature) ·
[[suite-scaffold-and-mybmad-sidecar]] (template is publish path; MyBMAD is
not the store) · [[platform-object-storage-kind]] (air-gap index blob, if
chosen) · [[pyforge-steward]] (owner) · [[pyforge-unifying-strategy]]
(estate; do not re-decide the platform shape)

## Realization log

- **2026-09-14** — Seeded after the operator asked to capture "what you would
  still invent" and then to inventory openteams-ai, nebari-dev, and
  ownyourintelligence.ai before research/`bmad-spec`. Live `gh repo list` on
  both orgs + field-guide fetch the same day. Conclusion: none of those three
  surfaces ships a self-hosted BMAD App Store; skillsctl / catalog-pack /
  Harbor / nebi are optional later faces; Layer 3 remains thesis; Collab
  exists and stays a non-goal. Scribe planning recall: no grounded prior
  answer. Next act: `bmad-spec` under steward once the open questions close;
  until then the stub Spec is the chain link only (`status: draft`, Dream
  stays `dreamt`).
- **2026-09-15** — Operator approved Q1–7 (thin browse; git to edit; conda /
  Artifactory default ship backend; object storage and bundles as plugins;
  Frames list/share on the same rails; no Layer 3; no billing). Spec `ready`.
  Steward Epic **60** (60.1–60.4 `backlog`) is the marshal dispatch home.
  Dream `dreamt` → `specified`.
