---title: platform-dev boots the local canopy without a second env
type: dream
owner: steward
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `platform-dev-boots-local`).


# platform-dev boots the local canopy without a second env

## The Dream

`pixi install -e platform-dev` is the no-Docker, no-CRC local baseline
(pap:AD-16). An operator should mint a persona and run `manage.py` from
**that** env. Today `config.settings.local` always loads
`debug_toolbar`, and that package lives only on `platform-ci-test`.
`platform-dev` dies on import. The workaround is a second env. The
Dream is one env: servers and the local Django leaf resolve together.

> A baseline that cannot load its own settings is not a baseline.

## Why now

Found 2026-09-13 while launching the canopy without Docker or CRC.
`platform-dev` python has Django, Wagtail, gunicorn, `django_extensions`,
and PyJWT. It does not have `django-debug-toolbar`.
`COMPONENT_RUNTIME=local python -m config.local_dev.mint staff` and
`manage.py runserver` both fail. The image feature
(`python-agent-platform`) must stay clean of the toolbar.

## What it looks like when real

- `platform-dev` python imports `config.settings.local`.
- `manage.py check` and mint run from that env against pixi Postgres.
- A policy test refuses a `platform-dev` solve that omits the toolbar
  or an image feature that gains it.
- CRC and Docker are unused for this proof.

## Constraints / Non-goals

- Pin `django-debug-toolbar` on `[feature.platform-dev]` only.
- Do not add it to `python-agent-platform` (the image).
- Do not start a `:800x` services farm; do not require compose or CRC.
- Do not flip Epic 44 `blocked` keys.

## Kinships

[[python-agent-platform]] (pap:AD-16, Story 11.1 — the env this Dream
repairs) · [[pyforge-steward]] (the host and the local leaf).

## Realization log

- **2026-09-13** — Seeded after a live `ModuleNotFoundError: debug_toolbar`
  on `platform-dev`. Operator asked the gap to be minted and implemented
  as a steward story, not a silent pin.
- **2026-09-13** — Spec `ready` (`pdl:CAP-1`), Epic 56 / Story 56.1. Live:
  `platform-dev` imports `debug_toolbar` 8.0.0, `django.setup()` under
  `config.settings.local`, `manage.py check`, and mint `staff`. Policy
  suite 6 passed. Image feature still omits the toolbar.
