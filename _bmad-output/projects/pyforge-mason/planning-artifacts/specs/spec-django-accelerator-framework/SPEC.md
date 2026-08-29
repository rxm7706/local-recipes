---
spec: django-accelerator-framework
status: draft
owner-dream: docs/dreams/django-accelerator-framework.md
surface:
  - src/platform/**
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/**
  - scripts/emit_wagtailcore_schema_delta.py
sources:
  - ../../../../../../docs/dreams/django-accelerator-framework.md
  - ../../../../pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md
open_questions:
  - Does CAP-2's third-surface trigger count Django surfaces repo-wide only, or across the estate (sibling repos such as conda-forge-tracker)?
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/django-accelerator-framework.md` is listed in
> `sources:` for the decision trail (activation trigger, air-gap entry, feature audit) this
> contract intentionally compresses; `spec-python-agent-platform` is the family Spec whose
> CAP-1 host is this contract's first realization.

# The Django accelerator is a contract today; the engine waits for a third surface

## Why

The dream was captured thin on 2026-08-14 — one hand-built Django surface (Steward's dashboard),
no recurring scaffolding pain, an explicit constraint against building anything until a second
Django-backed surface was actually planned. The same day, three Realization-log entries changed
its standing: the operator directed that the Django/Langflow/DB-GPT family builds on a
cookiecutter-django host with FastAPI integration **based on this dream** ("at that intake this
dream is the basis and should be spec'd with (not after) the family"); the air-gap realization
requirements were carried over from the OpenTeams source original; and the subject project was
named **python-agent-platform**. Story 10.1 then rendered that host into `src/platform/` (landed
on main 2026-08-14): `config/settings/{base,local,production,test}.py` env()-split settings,
`config/urls.py:26` `path("ht/", include("health_check.urls"))`, the `config/asgi.py` FastAPI
seam owning `/api/`, `config/celery_app.py`. So the honest question this spec answers is not
"build the scaffolding engine?" — the dream's own constraint still says no — but "what is the
**named shape** any PyForge Django surface renders to, now that two surfaces exist to name it
from?" This spec closes the "spec'd with the family" obligation: CAP-1 names the contract (real
now); CAP-2 parks the engine on the dream's own trigger.

## Capabilities

- **CAP-1 — The accelerator contract (REAL now).**
  - **intent:** A named, documented shape — *the accelerator contract* — that any PyForge Django
    surface renders to: cookiecutter-django base with FastAPI integration (an ASGI seam owning
    the API namespace); `env()`-helper/split-settings configuration; `/ht/` django-health-check
    endpoints wired to K8s liveness/readiness probes; mirror endpoints (conda/pypi/registry)
    parameterized at render time; vendored zero-CDN static assets (Bootstrap 5.3 + HTMX shape);
    auth bound to an internal OIDC IdP. Its **first realization** is python-agent-platform's
    `src/platform/` render (Story 10.1, on main 2026-08-14); its **second reference shape** is
    Steward's dashboard — `middleware.py` identity-at-the-boundary + `declarations.py`
    adopter-declarations — the local precedent the dream names as what a second Django surface
    copies from directly.
  - **success:** The contract is documented in this spec, and both existing surfaces verifiably
    conform to the clauses applicable to each — or carry dated deviations (the steward dashboard
    predates the contract and embodies the identity/declaration clauses, not the full render
    shape; that asymmetry is recorded, not papered over).
- **CAP-2 — The templating engine (CONTINGENT, explicitly parked).**
  - **intent:** A FreeMarker-*style* stamping engine that renders new surfaces from the contract
    mechanically — built **only after** a third/fourth Django surface repeats the copy by hand,
    per the dream's own constraint ("one hand-built Django app doesn't justify a templating
    pipeline; three or four might"). When the trigger fires, the engine's templates are
    **extracted from the proven local shapes** (the 10.1 render + the steward dashboard), never
    imported from the WF source's FreeMarker templates.
  - **success:** The CAP stays parked with its trigger recorded here; no engine code, template
    repo, or pipeline exists before a third surface demonstrates the repeated hand-copy. If the
    trigger fires, the engine work starts from the then-live conforming surfaces, and this spec
    is updated first.

## Constraints

- **Always — air-gap parity per the dream's 2026-08-14 air-gap entry:** Artifactory coordinates
  are first-class render-time substitutions across `pyproject.toml`, `pixi.toml`, Helm charts,
  and CI workflows; every pip/conda/pixi install in a rendered surface resolves from mirrored
  indexes only; frontend assets are vendored and bundled locally with zero CDN
  `<script>`/`<link>` references in base templates (applied at template-authoring time, not as a
  later patch); all runtime config flows through env/secret mounts (`env()`-split settings,
  matching `_http.py`'s env-only enterprise routing) — never committed; auth binds to an
  internal OIDC IdP with no external identity callbacks; `/ht/` endpoints are wired to K8s
  liveness/readiness probes.
- **Always — the platform is the living exemplar:** the contract must never drift from what
  `src/platform/` actually ships. When contract and render disagree, either the render gains a
  dated deviation or the contract is amended — never silent divergence.
- **Always — CAP-2 stays parked until its trigger:** building the engine before a third surface
  repeats the copy is a violation of this spec, not initiative.

## Non-goals

- **Not** an engine build now — CAP-2 is parked on the dream's own third-surface trigger.
- **Not** an import of the WF source's FreeMarker templates, Jenkins wiring, or three-repo
  pipeline — carried unchanged from the dream's non-goals; local shapes are the only template
  source if CAP-2 ever activates.
- **Not** a new station — this is a mason planning artifact naming a shape two existing surfaces
  already carry; the platform's own build contract stays with `spec-python-agent-platform`.

## Success signal

The accelerator contract is documented (this spec); `src/platform/` and Steward's dashboard each
verifiably conform to their applicable clauses or carry dated deviations; CAP-2 remains parked
with its extraction-not-import rule and third-surface trigger recorded; and the owner dream reads
`status: specified` with a Realization-log entry closing the "spec'd with (not after) the family"
obligation.

## Open Questions

- **Trigger scope for CAP-2:** does the third/fourth-surface count include only Django surfaces
  in this repo, or Django surfaces across the estate (sibling repos)? Estate-wide counting fires
  the engine sooner; repo-wide keeps it strictly local evidence. Undecided — the answer changes
  when, not whether, CAP-2 activates.
