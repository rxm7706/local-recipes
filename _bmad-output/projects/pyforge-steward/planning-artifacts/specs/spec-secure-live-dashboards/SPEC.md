---
spec: secure-live-dashboards
status: ready
updated: "2026-09-09"
surface: []          # SUPERSEDED 2026-09-09 — see § Built, not adopted. The 2026-08-09 note below
                     # ("frontier — no implementation exists") was true then and is false now:
                     # Epic 9 is 7/7 `done` and nine modules ship under `pyforge/steward/dashboard/`.
                     # Original note, kept for the record: frontier — no implementation exists
                     # (verified 2026-08-09: zero hits for dashboard_audit_trail, ROLE_HEADER,
                     # USER_ID_HEADER, allowed_roles, SECURITY_WEBHOOK_URL, ENCRYPT_EXPORT_FILE
                     # outside docs/dreams+docs/intake; the Flask-Caching hits are conda recipes
                     # and warden fixtures, not code)
owner-dream: docs/dreams/secure-live-dashboards.md
companions:
  # The architecture that answers every open question this Spec was holding.
  # Load-bearing: its AD-1..sld:AD-14 are the build contract any decomposition binds to.
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/secure-live-dashboards.md
  - ../../../../../../docs/intake/secure-live-dashboards/role-based-live-dashboard-blueprint.md
  - ../../../../../../docs/intake/secure-live-dashboards/vizro-static-github-pages-workaround.md
# All six open questions were ANSWERED by the architecture run of 2026-08-09 and by
# the operator's Django/ASGI and static-mode direction; status moved draft -> ready on
# that basis. Resolutions kept here rather than deleted, so the contract records what
# was decided and which AD decided it:
#   Q1 where the pattern lives (subcommand vs library vs template repo)
#       -> AD-1: BOTH, split on the process boundary. In-process concerns ship as the
#          library, out-of-process concerns as a `steward deploy` subcommand. Template
#          rejected: no upgrade path for a diverged adopter.
#   Q2 whether the pattern PROVIDES the pipeline or VERIFIES an acceptable one
#       -> AD-2: both, split by half. The library provides so nobody reimplements
#          isolation; the subcommand verifies so a diverged adopter is still caught.
#   Q3 proxy headers trusted implicitly / the undefended trust boundary
#       -> AD-4: the trusted ingress is DECLARED, and the app refuses to start when
#          identity headers arrive from outside it. AD-9 carves out machine callers,
#          which authenticate by HMAC proof and never receive a human role.
#   Q4 Redis mandated or one pluggable cache backend
#       -> AD-5: pluggable, but the SHARING PROPERTY is mandatory — any cross-worker
#          state (response cache AND Channels channel layer) that cannot be shared is
#          refused when workers > 1.
#   Q5 audit trail retention and access policy
#       -> AD-7: retention is declared by the adopter and has NO default; a deployment
#          without one is refused. The trail is itself role-isolated data, so reading
#          it is a recorded act.
#   Q6 what ENFORCES that search runs after role filtering
#       -> AD-6: the API shape. The library exposes no entry point that can search the
#          master set, so the ordering is not a matter of caller discipline.
# Later ADs from the same run bind the host and delivery: AD-8 (binds at the ASGI
# boundary, never to a dashboard framework), sld:AD-10 (static export and role isolation
# are mutually exclusive), sld:AD-11/sld:AD-12 (protocol-specific identity; per-message
# isolation and audit), sld:AD-13 (ships as a reusable Django app), sld:AD-14 (SQLite dev /
# PostgreSQL deploy, contention proven not inferred).
open_questions: []
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
    a multi-worker **ASGI** topology, a container stack whose cross-worker state is shared,
    and an edge that terminates TLS and enforces network policy — all driven by
    configuration. *(Was "WSGI" as first written, from the blueprint's Gunicorn `gthread`
    sample; superseded by AD-8 once the host was fixed as Django + Channels on ASGI. A
    WSGI-native dashboard is mounted through a WSGI→ASGI adapter rather than the host being
    forced to WSGI.)*
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

## Built, not adopted — graded 2026-09-09 against live code

Epic 9 is 7/7 `done` and nine modules ship under `pyforge/steward/dashboard/`. **Only `cache`,
`filtering` and `declarations` have any consumer outside the package** — all three in
`django-atlas/src/django_atlas_portal/board.py:17-20`, over a **5-row in-process fixture**
(`board.py:28-36`). `middleware`, `audit`, `views`, `navigation`, `models` and `export` have
**zero consumers**. `pyforge.steward.dashboard` appears in no `INSTALLED_APPS`
(`src/platform/config/settings/base.py` has zero `dashboard` matches), so `AuditEntry`
(`models.py:43`, `migrations/0001_initial.py`) has **no table in any running deployment** and Story
9.3's "every load, filter, navigation and export lands in an audit trail" is unexercised.

**Accuracy correction owed downstream:** `convergence.md:38` and `:129` say Atlas "never adopted"
this Spec. Strictly it did — **at fixture grade** (`django-atlas/board.py:17-20`); Atlas's real
Vizro board (`pyforge/atlas/dashboard/app.py`) imports **zero** steward dashboard modules. "Never
adopted" understates what exists and would send an implementer to build a seam that is already
there.

## The Django half gets an adopter — 2026-09-09

**Decision (operator, batch rows stB-B6 / C15), scoped to what Epic 49 already funds — Story
49.4.** One decision, not two:

- **If 49.4 mounts Atlas's real Vizro board on the host**, it must install
  `pyforge.steward.dashboard` in `INSTALLED_APPS` and route the board's loads through `audit` +
  `export`.
- **If 49.4 instead rewrites CAP-7's criterion to name the fixture**, this Spec's Django half is
  rewritten as deferred in the same act.
