---
spec: secure-live-dashboards
status: draft
owner-dream: docs/dreams/secure-live-dashboards.md
surface: []          # frontier — no implementation exists (verified 2026-08-09: zero hits for dashboard_audit_trail, ROLE_HEADER, USER_ID_HEADER, allowed_roles, SECURITY_WEBHOOK_URL, ENCRYPT_EXPORT_FILE outside docs/dreams+docs/intake; the Flask-Caching hits are conda recipes and warden fixtures, not code)
companions: []
sources:
  - ../../../../../../docs/dreams/secure-live-dashboards.md
  - ../../../../../../docs/intake/secure-live-dashboards/role-based-live-dashboard-blueprint.md
  - ../../../../../../docs/intake/secure-live-dashboards/vizro-static-github-pages-workaround.md
open_questions:
  - "Where the pattern lives: a `steward` subcommand that scaffolds and verifies, a library the dashboard imports, or a template repository. Each implies a different upgrade story when the pattern improves, and an adopter that has diverged is the case that decides it."
  - "Whether the pattern PROVIDES the RLS pipeline and audit writer or VERIFIES that an adopter has an acceptable one. Provide is reusable and rigid; verify tolerates dashboards that already made their own choices. This bounds every capability below."
  - "Proxy headers are trusted implicitly — anything able to reach the app directly can forge the role header. The blueprint makes header NAMES configurable but never defends the trust boundary. Needs either a defence (mTLS, a shared secret, network policy) or an explicitly recorded assumption that the network path is the control."
  - "Whether Redis is mandated or one pluggable cache backend. The blueprint's own sample uses `FileSystemCache`, which contradicts its Compose stack: under Gunicorn `--workers 4` a filesystem cache does not deliver the shared-cache guarantee Redis is provisioned to provide. Mandating Redis raises the floor for a small adopter."
  - "Whether the audit trail has a retention and access policy. It accumulates per-user activity, making it simultaneously a compliance asset and a privacy liability; the blueprint is silent."
  - "What ENFORCES that search runs after role filtering. The blueprint's sample orders it correctly, but nothing binds the order, and reversing it leaks across roles."
---

## Why

A dashboard that answers a real question stops at the laptop, because everything needed to
hand it to a company is missing and none of it is dashboard work: who is looking, which rows
they may see, what they did, how it runs behind the corporate proxy, and what happens when
someone skips the UI and calls the download endpoint directly.

Today that second half is rebuilt per dashboard or not at all. This repo already has the
first half — `pyforge-atlas` ships a BSL-driven Vizro dashboard with a `dashboard-dryrun`
gate and a `query_vizro_ai` MCP tool, and `vizro` and `flask-caching` are already packaged
as conda recipes here — so the gap is not the dashboard, it is everything around it.

The unit of value is the **second** dashboard. A one-off hardening of one board leaves the
next one facing the same wall, so this is a pattern adopters take on, not an application.
Atlas's board is the first adopter and the proof, never the subject.

Steward owns it because the work is roughly five parts security and infrastructure to one
part dashboard — token lifecycle, identity, row isolation, audit persistence, alerting,
export gating, WSGI topology, container orchestration, TLS and subnet policy, security CI.
Steward provisions the engines, deploys the services, and holds the keys.

## Capabilities

- **CAP-1 — identity and role arrive from the request; the pattern authenticates no one.**
  - **intent:** An adopting dashboard obtains the caller's identity and group membership from
    headers set by a trusted reverse proxy, with the header names configurable per deployment
    rather than baked in.
  - **success:** the same dashboard runs unmodified behind two proxies that use different
    header names, by configuration alone; with no proxy present it degrades to a single
    known-unprivileged identity rather than to an error or to an elevated one.

- **CAP-2 — row-level isolation is declared, not implemented, by the adopter.**
  - **intent:** A dashboard states which column carries access and which roles exist; the
    pattern performs the filtering. The master dataset is cached once and shared; the
    role-filtered slice is computed per request, in memory, after it leaves the shared cache.
  - **success:** two concurrent users of different roles produce **one** upstream fetch and
    see disjoint row sets; a role-filtered frame never appears in the shared cache; and an
    adopter that adds a dashboard obtains isolation without writing a filtering pipeline.

- **CAP-3 — an unauthorized page is absent, not hidden.**
  - **intent:** The navigation tree is constructed from the caller's role, so a page a user
    may not see is never emitted.
  - **success:** the served DOM for a low-privilege caller contains no reference to a
    restricted page — verified by inspecting the response, not by observing that a link is
    not visually rendered.

- **CAP-4 — the audit trail records what was seen, not merely that something happened.**
  - **intent:** Every data load, filter, navigation and export lands in a durable trail
    carrying the actor, their role, the action, and the number of rows involved.
  - **success:** for any completed session the trail can answer "who saw how many rows of
    what, and when" without consulting application logs; the same schema is written whether
    the backing store is the development database or the production one.

- **CAP-5 — export is gated server-side, and may be encrypted.**
  - **intent:** Only authorized roles obtain a data export. Authorization is enforced where
    the data is produced, not where the button is drawn. Encryption of the delivered artifact
    is a configuration choice, not a fork of the code.
  - **success:** a direct request to the export endpoint by an unauthorized caller — with no
    UI involved — is refused, recorded as a security event, and announced to a configured
    webhook; with encryption enabled the delivered artifact is unreadable without the key.

- **CAP-6 — the deployment perimeter ships with the pattern.**
  - **intent:** An adopter receives a production-shaped runtime rather than assembling one:
    a multi-worker WSGI topology, a container stack whose cache state is shared across
    workers, and an edge that terminates TLS and enforces network policy — all driven by
    configuration.
  - **success:** the same artifact runs on a laptop against a file-backed database and in
    production against a clustered one by changing connection configuration only, so the
    security boundaries are exercised in development rather than first met in production.

- **CAP-7 — the security boundaries are proven by tests that cannot pass vacuously.**
  - **intent:** Isolation is asserted by a suite that impersonates different identities and
    checks both that a privileged caller sees more and that an unprivileged one sees less —
    and that suite runs before a merge is permitted.
  - **success:** each isolation test fails when its guard is removed, demonstrated rather
    than claimed; a test that exercises only the restricted path, and would therefore pass
    against an implementation that always restricts, is treated as a defect.

- **CAP-8 — the same dashboard definition ships hosted or static, without a fork.**
  - **intent:** A board that needs no isolation can be published as a free static site on
    GitHub Pages — its Plotly components exported to HTML, assembled into a responsive grid,
    rebuilt by CI — from the *same* definition the hosted mode deploys. Two delivery modes,
    one dashboard.
  - **success:** the same board is published both ways without anyone hand-re-deriving its
    charts for the static build; and the static build **refuses** — not warns — when the board
    has declared an access column, because that combination cannot be honoured.

## Constraints

- **Secrets come from Steward's `keys` surface — never from source, and never from a default
  constant.** The blueprint's sample embeds a literal `ENCRYPTION_KEY` plus a `DEFAULT_KEY`
  fallback; `scripts/container-gates`' `secrets-scan` already exists in this estate to refuse
  exactly that, so the sample is incompatible as written and must not be copied.
- **The absent UI control is never the access control.** Any capability gated in the
  interface must be independently refused at the endpoint that produces the data.
- **A role-filtered dataset is never written back to the shared cache.** The shared cache
  holds only the master set; slicing is per request and in memory.
- **The pattern never authenticates a user.** It consumes an identity a corporate proxy has
  already established. Its guarantee is therefore bounded by the trust of that network path —
  which is why the trust boundary is an open question above rather than an assumed given.
- **One schema across environments.** Development and production differ by connection
  configuration, not by code path, so a boundary cannot hold in one and not the other.
- **Choosing a delivery mode is choosing a security posture, not a hosting preference.** The
  static mode's optional client-side filtering embeds the data for *all* states in the page,
  so every role's rows reach every browser; and with no server there is no audit trail at all,
  not a reduced one. A board that declares an access column therefore **may not** be delivered
  statically, and the static build refuses rather than warns. The two modes are a per-dashboard
  choice, not a spectrum: public and unrestricted at zero infrastructure, or role-isolated and
  hosted.

## Non-goals

- **Not a replacement for Atlas's dashboard, and not a second Vizro application.** Atlas's
  board is the first adopter and the proof.
- **Not an authentication or identity provider.** Establishing who the user is remains the
  corporate proxy's job.
- **Not a general BI platform.** It secures dashboards this estate builds, not arbitrary
  third-party analytics.
- **Not a decision here about packaging or ownership depth.** Whether the pattern ships as a
  subcommand, a library or a template, and whether it provides or merely verifies the
  pipeline, are open questions for the architecture phase — deciding them here would
  pre-commit the shape before the adopter set is known.
- **Not a migration of existing dashboards.** Adoption is opt-in per dashboard.

## Success signal

A second dashboard — one that did not exist when the pattern was written — reaches production
behind the corporate proxy by declaring its access column and its role vocabulary, and passes
the same isolation suite unchanged. No audit schema, container stack, or filtering pipeline is
written for it.
