---
title: "Dependency currency — Django patch exposure and the Liquibase multi-schema regression"
chain: "pyforge-unifying-strategy"
type: "technical"
created: "2026-08-24"
updated: "2026-08-24"
status: "ready"
decision: "Whether the Django 5.2.15 pin is a live security exposure, and whether Liquibase 5.0.4 is safe for multi-schema changesets"
answers:
  - liquibase-7791-fixed
  - django-patch-exposure
---

# Dependency currency

Two independent audits run 2026-08-24. Each corrected a premise this chain had recorded as
established fact, and in both cases the correction was in our favour — which is worth noting,
because a premise that turns out to be *pessimistic* is just as much a planning error as an
optimistic one, and it had been sized as a risk.

---

## Part A — Django 5.2.16 and 5.2.17

**Verdict: both are security releases carrying seven CVEs, one Django-rated high — and every
affected code path is unreachable in `src/platform/`. A currency gap, not a live exposure.**

### What the releases carry

**5.2.16** (2026-07-07), three CVEs, all rated low by Django: a cache middleware bug caching a
`Set-Cookie` response into a shared cache, a heap over-read in the GeoDjango raster type, and a
domain-name validator accepting newlines.

**5.2.17** (2026-08-04), four CVEs including **CVE-2026-15307, rated high (CVSS 8.8)** — GeoDjango
spatial lookups passing raw values into the raster type, allowing a file write or an outbound
request as the Django process user, reachable by a staff user filtering an admin changelist on a
model with a spatial field. Plus a geometry-collection segfault, stored XSS via admin rendering of
`URLField` values, and unbounded memory growth in the language-code check.

### Why none of it reaches us

| CVE group | Why unreachable |
|---|---|
| Four GeoDjango CVEs (incl. the high one) | `django.contrib.gis` is **not installed** — `config/settings/base.py` lists auth, contenttypes, sessions, sites, messages, staticfiles, admin, forms. No GIS packages in any pixi environment. The one admin registration is over the plain `users.User` model, which has no spatial field. |
| Cached `Set-Cookie` | Neither cache middleware is in `MIDDLEWARE`; no `cache_page` anywhere. Redis is a plain cache backend, not a per-site page cache, so no response enters the vulnerable store. |
| Admin `URLField` XSS | **No `URLField` exists in `src/platform/` at all**, in models or forms. |
| Language-code DoS | `set_language()` is off by default and not routed — `config/urls.py` has no `i18n` include. |
| Domain-name validator | Not used. `django.contrib.sites` validates `Site.domain` with a different validator. |

### The premise that was wrong

This chain recorded "no maintenance branch on the feedstock." **That is false.**
`conda-forge/django-feedstock` carries live `5.x`, `4.x` and `3.2.x` branches, with `5.x` and `4.x`
formally registered in `conda-forge.yml` as `abi_migration_branches`. The `5.x` branch is simply
*stale* at 5.2.15, not absent.

More to the point: **this repo's maintainer already landed a bump on it.** PR #230, the 5.2.15
bump, was authored by `rxm7706` and merged 2026-06-06, following #220/#224/#227/#228 for the
preceding patches. The autotick bot will not do it — `github.branch_name: main` points version PRs
at the 6.x line — so it stays a manual bump, which is exactly what the branch's history shows.

So catching up is **a one-file change on an existing branch**: bump the version, update the
`sha256`, confirm `remove_tzdata.patch` still applies, re-render. Not a maintenance-branch request,
not core-team scope, and demonstrably within this maintainer's reach.

### Recommendation

**Audit-clean, but move the pin — treat it as maintenance with a clock, not an incident.**

The reachability analysis is what an assessor needs, and it holds. But in a regulated estate the
finding raised is not "you were exploited", it is "your SBOM declares a component with seven known
unremediated CVEs, one at CVSS 8.8". **Scanners key on version strings, not reachability**, so this
becomes a reachability justification written repeatedly, widening with every monthly Django
security release.

Concretely: a 5.2.17 PR against the feedstock's `5.x` branch, then move the three `pixi.toml` pins
(lines 177, 450, 1643) to `>=5.2.17,<6`.

One caveat if it is done: 5.2.17's fix for the high CVE is explicitly **backward-incompatible** —
spatial lookups now reject `dict` and non-geometry strings. Irrelevant here, since we have no
spatial lookups, but it matters to other consumers of the conda-forge `django` 5.2 package.

### Residual gaps

Third-party packages were not introspected for admin-registered `URLField`s — `django_celery_beat`,
`django-allauth` and `django-health-check` register models we did not audit field-by-field. Judged
low risk (allauth's `SocialApp` and celery-beat's schedules are staff-authored config rather than
user content), but it is an assumption. The applicability analysis is also static: a runtime
settings overlay outside `config/settings/` would be invisible to it.

---

## Part B — Liquibase issue 7791

**Verdict: fixed in 5.0.4, corroborated independently by the merged PR and the release notes.**

PR #7803 merged 2026-08-10; the merge commit is confirmed an ancestor of the `v5.0.4` tag
(published 2026-08-20, `behind_by: 0`), and the 5.0.4 notes name the fix explicitly. The two
sources agree, which is the corroboration standard this chain has been applying.

### The regression, and a scoping correction the SPEC needs

The cause is a good example of one fix creating another bug. PR #7488 changed Liquibase to emit
`SET LOCAL SEARCH_PATH` instead of a plain `SET`, closing a real problem — the session-level path
leaking to other clients through PgBouncer's transaction pool. But `SET LOCAL` only takes effect
inside a transaction block, so a changeset marked `runInTransaction="false"` runs in autocommit,
PostgreSQL emits a warning, and the statement is a no-op. The `search_path` stays at
`"$user", public` and unqualified references resolve in the wrong schema.

**The SPEC framed this too broadly.** It said the fix "must be verified before any multi-schema
changeset lands." In fact **changesets running inside a transaction were never affected** — only
`runInTransaction="false"` ones, which are the exception (`CREATE INDEX CONCURRENTLY`,
`ALTER TYPE … ADD VALUE`). The gate is real but narrower than recorded.

The merged fix keeps both properties: `LOCAL` inside a transaction, plain `SET` plus an explicit
save/restore outside one, so the PgBouncer leak is not reintroduced. The residual edge is that
restore runs in the changeset's cleanup path, so a hard JVM kill mid-changeset — a Helm job
timeout, a pod eviction — leaves the session path set on that physical connection. That only
matters through a transaction-pooling proxy.

### Version and packaging consequences

**Target 5.0.4.** It is also the latest Community release as of today, so there is no argument for
going newer, and 5.0.2/5.0.3 both carry the defect. Java 17 remains the floor, unchanged — the
packaging plan's assumption holds.

**One packaging detail that decides a recipe question:** the release signing key was rotated after
the previous key was revoked, and **GPG verification requires 5.0.4 or later**. If the recipe
verifies signatures, 5.0.4 is the first version that works against the current key.

### The hazard worth more attention than 7791

**Issue #7624 is open and unmentioned in the 5.0.4 notes.** With `preserveSchemaCase=true` on
PostgreSQL, `defaultSchemaName` is double-quoted, so schema `Test` becomes `""Test""`. That schema
does not exist, so **changes silently apply to whatever comes next in the search path — usually
`public`**. It worked in 5.0.1 and broke in 5.0.2.

Silent wrong-schema DDL is the worst available failure mode for this deployment, and it is a
*silent* one, which is worse than the loud failure 7791 produced. The mitigation is cheap and we
get it free: leave `preserveSchemaCase` off and keep schema names lowercase, which Django's naming
conventions already give us. **This should be a constraint, not a note.**

### An architecture decision this surfaces

`liquibaseSchemaName` controls where `DATABASECHANGELOG` and `DATABASECHANGELOGLOCK` live; unset,
they land in the `defaultSchemaName` schema. With a schema per mounted application, the choice
between **one shared tracking schema** and **per-schema tracking** determines whether the changelog
lock is global or per-application — and therefore whether two applications can migrate
concurrently. That is a real decision for the architecture pass, not a default to inherit.

### The search_path behaviour, verified from source

Liquibase **prepends** rather than replaces: it reads the current path and builds
`defaultSchemaName + ", " + <existing>`, skipping the operation entirely if the path already starts
with the default schema. So extensions installed in `public` stay reachable.

Recommended posture, and the pre-fix workaround for 7791: **do not depend on Liquibase's
`search_path` manipulation at all.** Set it on the connection instead, via the JDBC `currentSchema`
parameter or an init SQL statement. For a Helm pre-upgrade hook, connect directly to PostgreSQL
rather than through a pooling proxy, which sidesteps this whole class of problem.

### Residual gaps

Not verified by running 5.0.4 against a live multi-schema instance — the end-to-end confirmation
cited is a reviewer's report on the PR, not an independent test. Given how much CAP-9 rests on
this, a short local test with a `runInTransaction:false` changeset against a non-default schema
would convert this from "verified by evidence" to "verified by observation", and belongs in the
FR-21 story. Also unverified: whether #7624 was quietly fixed at the 5.0.4 tag without its issue
being closed.
