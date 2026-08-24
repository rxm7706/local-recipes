---
title: "Product Brief: the Canopy mounts the eight stations"
status: "ready"
created: "2026-08-23"
updated: "2026-08-24"
chain: "pyforge-unifying-strategy"
author: "steward"
supersedes: "the 2026-08-23 pre-audit draft of this file (herald), written on a greenfield premise the audit disproved"
inputs:
  - "docs/dreams/pyforge-unifying-strategy.md"
  - "../../specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "../../specs/spec-pyforge-unifying-strategy/convergence.md"
  - "../../research/technical-pyforge-unifying-strategy-research-2026-08-24.md"
  - "../../research/technical-pyforge-unifying-strategy-airgap-delivery-2026-08-24.md"
---

# Product Brief: the Canopy mounts the eight stations

> **This is an extension brief, not a product-launch brief.** The platform it describes is
> partly built and running. Everything below is scoped to the residual — what `convergence.md`
> proves is genuinely absent. Where this brief and the 2026-08-23 draft disagree, this one wins;
> that draft was written before the audit and assumed a greenfield.

## The problem, stated honestly

PyForge is eight capability stations — atlas, doctor, herald, marshal, mason, scribe, steward and
warden. Each shipped as a genuinely good command-line tool and stopped there. The operator who
wants to see compliance findings, package health, fleet status and build queues opens eight
terminals, holds eight mental models, and gets no help from the estate in relating them. No station
can tell another that something happened.

The Canopy already proved the fix is available. `src/platform/` is live: a Django host with OIDC
single sign-on, Langflow and DB-GPT mounted as pluggable apps on isolated PostgreSQL schemas, a
Helm chart with an OpenShift overlay, and **one** station portal — warden's, at `/compliance/`.
One of eight. The pattern works and simply has not been repeated.

Riding on top of that is a governance problem that is not a UI problem at all. The deployment
target is air-gapped and regulated, which means schema change has to be auditable rather than
incidental, access has to be revocable rather than cached, and a failing dependency has to degrade
its caller rather than take down its neighbours. Those are the Dream's five numbered RFCs and eight
blind-spot directives, carried into `SPEC.md`, and they are why this is more than a front-end
effort.

## Who it is for

| Who | Reaches the estate through | What is broken for them today |
|---|---|---|
| **Packaging / platform engineer** | Eight separate station CLIs | No shared grammar; every station has its own verbs and its own output shape. |
| **Compliance auditor** | Warden's portal — the one that exists | Can see compliance and nothing else. No path from a finding to the package, build or fleet context around it. |
| **Platform operator** | `kubectl`, Helm, and the shipped chart | Schema change is whatever Django's migration graph did; no separate authority, and the app's own database role can alter its own schema. |
| **Autonomous agent** | Atlas's MCP server — the only one | Seven stations expose no service face, only a CLI to shell out to, and long operations die with the connection. |

The agent reads as a first-class user here: five of the sixteen capabilities — the service face, the
command grammar, the event backbone, the domain skills and the personas — exist mainly to make the
estate legible to something that is not a human. That emphasis is derived from the capability set
rather than from a stated user requirement, so the PRD should confirm or correct it.

## What we are actually building

Fourteen of the sixteen capabilities extend the host outward: a shared chrome package so portals
stop reinventing navigation, a CMS-managed front door, the seven missing portals, atlas's
analytical boards reachable through the host with per-user row isolation, a service face for the
seven stations without one and the current-spec transport for atlas's existing one, one command
grammar over the eight existing CLIs, a client that carries the end user's identity as a signed
assertion instead of a trusted header, and an event backbone so one station's action can be
another's input.

Two capabilities close a gap the Dream stated and the first convergence sweep missed, caught on the
Spec's preservation pass: the Dream promises **five-tier symmetry** — CLI, portal, service, domain
skill, agent persona — and the estate has one domain skill of eight and zero station personas. A
station missing any of the five is unfinished, whatever its ledger says.

Underneath, the governance work: DDL authority enforced by database privilege rather than
convention, four containment invariants so a failing dependency degrades its caller instead of
cascading, queue and cache separated so they cannot evict each other, roles sourced from the
identity provider, secrets from a secret manager, feature flags evaluated offline, and Scribe's
knowledge graph moved off a single JSON file.

## What success looks like

These are observable end states, not percentages — no baseline measurement exists for this estate,
so a number here would be invented.

- An operator signs in once and moves from the front door to any station portal to an analytical
  board showing only their own rows, without re-authenticating or leaving the origin.
- An agent drives a station over MCP, survives a proxy disconnect during a multi-minute build, and
  still collects its result.
- One station's action arrives as an event another station consumes; a poisoned event lands in a
  dead-letter queue instead of retrying forever.
- The whole thing deploys into an egress-blocked namespace carrying only PostgreSQL, Redis and the
  platform images — and the application's database role is provably incapable of altering its own
  schema.

Each capability in `SPEC.md` carries its own success criterion, written so it fails when the
capability is absent. An invariant with no test that fails without it is not implemented.

## What makes this hard

**Six new conda-forge builds gate real work.** Four OpenFeature feedstocks and Liquibase are absent
from conda-forge — OpenFeature is absent from anaconda.org entirely — and the flag provider
additionally needs a `cachebox` 5.x build, since conda-forge ships only 6.2.5. That last one is a
downgrade build on an existing feedstock rather than a new recipe, which is a different size of
task. Two epics therefore open with packaging work rather than platform work, and each of those
stories must invoke `conda-forge-expert`.

**One capability reopens shipped code.** Governed DDL contradicts two `done` stories that
provisioned schemas through Django migrations. That correction is not optional, and the literal
directive turned out to be unimplementable — Django's own migration machinery cannot leave the
deploy path (see `addendum.md`). The revised form moves enforcement to the database role, which is
the only control an auditor can actually verify. How the ledger records that reopening is
`bmad-correct-course`'s call, not the epic pass's.

**The front door displaces something that works.** The CMS front door supersedes Marshal's shipped
console rather than sitting beside it, so it carries a migration obligation: parity proven before
the old build path is removed. The inventory that proves it is done, and it found seven of
twenty-three surfaces that no request-time query can reproduce — so this is a real scope
conversation, not a formality. See `console-parity-inventory.md`.

**The Django pin has no headroom.** conda-forge's 5.2 line stopped at 5.2.15 while upstream shipped
5.2.16 and 5.2.17. Exactly one build satisfies our pin, two patch releases behind, with no
maintenance branch on the feedstock.

**Four questions are open and named**, including whether the official MCP SDK yet ships a
server-side Tasks runtime — the largest gap between CAP-4's recommended pattern and shippable code
— and whether our new front door can serve the live La Suite/Wagtail bring-up atlas has been
waiting on. Atlas's shipped client speaks La Suite Docs' API rather than Wagtail's own, so that
one is a compatibility question rather than a formality.

## What this is not

Not a rewrite of the host, not a ninth station, not a replacement for any station's CLI, and not a
re-decision of the monolith-versus-microservices topology, which is closed in
`enterprise-multi-agent-orchestration` and `asgi-multiplexer-monolith`. It does not adopt CodeRed
CMS, whose upstream has been dormant since 2025 and supports Wagtail only through 7.1 against a
current 7.4.3 LTS. It does not absorb atlas's own Wagtail Spec. And it is not a general-purpose
multi-tenancy model — the row isolation is for analytical boards, not a tenancy layer for the
estate.

## Where this goes next

The PRD traces functional requirements to the sixteen capability IDs so nothing floats. The
architecture pass fixes the invariants the pieces have to agree on — the portal registration seam,
the client's token-minting contract, the event envelope, the DDL pipeline. Epics group by delivery
seam, run to roughly seven to nine, and begin at **Epic 18**; Steward runs to 17 today. Then eight
`bmad-correct-course` runs record each station's Canopy obligations, with Marshal's additionally
retiring `spec-factory-console`. `addendum.md` holds the depth that belongs downstream rather than
here.
