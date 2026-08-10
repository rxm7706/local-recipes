---
title: A dashboard can be handed to the company without being rebuilt
type: dream
owner: steward
status: dreamt
---

# A dashboard can be handed to the company without being rebuilt

## The Dream

Someone builds a Vizro board that answers a real question. Then it has to leave the laptop —
and today that is where it stops, because everything that makes it safe to hand to a company
is missing and none of it is dashboard work: who is looking at it, which rows they may see,
what they did, how it runs behind the corporate proxy, and what happens when someone
bypasses the UI and calls the download endpoint directly.

The dream is that this second half already exists as a **pattern any dashboard in the estate
adopts**, not as a thing each dashboard reinvents. Atlas's board is the first adopter and the
proof; it is not the subject. A second dashboard should reach production by declaring which
column carries access and which header carries identity — not by rewriting an audit schema, a
container stack, and a CI security suite.

## What it looks like when real

- A dashboard gains row-level isolation by naming its access column and its proxy headers.
  No dashboard writes its own filtering pipeline.
- The master dataset is cached once, server-side, and shared across concurrent users; the
  role-filtered slice is computed **per request and never written back to the shared cache**.
  Two users at once produce one upstream fetch, not two, and never each other's rows.
- A viewer cannot see an admin page in the DOM at all — the navigation tree is built from
  the caller's role, not hidden with CSS.
- Every load, filter, navigation and export lands in an audit trail with the row count, not
  merely the fact that something happened.
- Someone who bypasses the UI and posts directly to a restricted download endpoint is
  refused **server-side**, logged as critical, and announced to a SIEM/Slack/Teams webhook —
  the front-end absence of a button is never the control.
- The same stack runs against SQLite on a laptop and PostgreSQL in production by changing one
  connection string, so the security boundaries are exercised in development rather than
  first met in production.
- Exports can be delivered encrypted, and the toggle is configuration rather than a fork.
- The security boundaries are asserted by tests that mock different corporate identities and
  prove isolation holds — and those tests run on every push, against an in-memory database,
  before a merge is allowed.

## What is real

- **The full blueprint exists** as intake material: system integration and token lifecycle,
  the two-step RLS pipeline (global cache → per-request slice), the audit schema
  (`id`, `timestamp`, `username`, `role`, `action_description`, `row_count`), webhook alerting,
  role-gated and optionally Fernet-encrypted CSV export, the four-service Compose stack
  (app / Postgres / Redis / backup) behind an Nginx edge, the corporate palette, the pytest
  security suite, and GitHub Actions + GitLab CI pipelines.
- **Vizro is already in this repo and already load-bearing.** `pyforge-atlas` ships a
  BSL-driven Vizro dashboard (`pyforge/atlas/dashboard/app.py`) with a `dashboard-dryrun`
  gate and a `query_vizro_ai` MCP tool. This Dream does not introduce Vizro; it makes what is
  already here shippable to other people.
- **Steward already owns the neighbouring surfaces.** `spec-unified-container` (the one-image
  Guild build), `spec-enterprise-airgap`, and the `keys` credential surface are the same
  estate this pattern deploys into — including a live secrets-scan gate
  (`scripts/container-gates`) that already refuses to bake credentials into an image.

## Why Steward, and why a pattern

The blueprint is roughly five parts security and infrastructure to one part dashboard: token
lifecycle, identity from proxy headers, row isolation, audit persistence, webhook alerting,
export gating and encryption, WSGI topology, container orchestration, TLS and subnet policy,
and a CI security suite. Steward is the station that *"provisions the engines the factory runs
on, deploys the services it ships, holds the keys that guard it"* — Vizro is the thing being
secured here, not the work being done.

And a pattern rather than an application, because the second dashboard is where the value
lands. A one-off hardening of one board leaves the next one facing the same wall.

## Open questions

- **Where does the pattern live?** A `steward` subcommand that scaffolds and verifies, a
  library the dashboard imports, or a template repository. Each implies a different upgrade
  story when the pattern improves — and an adopter that has diverged is the case that matters.
- **How much does the pattern own versus assert?** It could *provide* the RLS pipeline and
  audit writer, or it could *verify* that a dashboard has an acceptable one. The first is
  reusable and rigid; the second tolerates dashboards that already made their own choices.
- **Does the identity model bind to one proxy convention?** The blueprint reads `ROLE_HEADER`
  and `USER_ID_HEADER` from the environment, which is configurable but still assumes headers
  from a trusted reverse proxy. What happens where that assumption does not hold is not
  answered.
- **Is trusting proxy headers acceptable here?** Anything that can reach the app directly can
  forge them, so the pattern's guarantee is only as strong as the network path. Whether that
  needs a defence, or an explicit recorded assumption, is a genuine security decision.
- **Does the audit trail have a retention and access story?** It accumulates every user's
  activity, which makes it both a compliance asset and a privacy liability.
- **Is Redis a requirement or one cache backend?** The blueprint names it for cross-worker
  shared state; whether the pattern mandates it or treats it as pluggable changes the floor
  for a small adopter.

## Non-goals

- Not a replacement for Atlas's dashboard, and not a second Vizro application. Atlas's board
  is the first adopter and the proof.
- Not an authentication system. The pattern consumes an identity that a corporate proxy has
  already established; it never authenticates a user itself.
- Not a general BI platform. It secures dashboards this estate builds, not arbitrary
  third-party analytics.
- Not a decision, here, about how the pattern is packaged or how much it owns — those are the
  open questions above and belong to the Spec and architecture phases.

## Realization log

- **2026-08-09** — Seeded from a complete, externally-authored blueprint (role-based live
  dashboard architecture: RLS, audit, webhooks, encrypted export, Compose/Nginx stack,
  security CI). Operator chose `owner: steward` over `atlas` on the reasoning above, and
  scoped it as a **reusable pattern** other dashboards adopt rather than a hardening of the
  existing board or a standalone system.
