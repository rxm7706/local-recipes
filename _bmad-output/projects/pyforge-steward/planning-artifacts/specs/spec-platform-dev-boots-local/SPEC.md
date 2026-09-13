---
spec: platform-dev-boots-local
status: ready
created: "2026-09-13"
updated: "2026-09-13"
owner-dream: docs/dreams/platform-dev-boots-local.md
extends: spec-python-agent-platform
surface:
  - pixi.toml
  - pixi.lock
  - src/platform/config/settings/local.py
  - src/platform/tests/policy/test_platform_dev_local_leaf.py
companions: []
sources:
  - ../../../../../../docs/dreams/platform-dev-boots-local.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-13 from
> `docs/dreams/platform-dev-boots-local.md` and `.memlog.md`. Cite
> this file's ids as `pdl:CAP-1`. Decomposed as steward **Epic 56**.
> Does not flip Epic 44 `blocked` keys.

# SPEC — platform-dev boots the local leaf

## Why

**A pain to solve.** pap:AD-16 names `platform-dev` as the one
containerless local baseline. `manage.py` and mint load
`config.settings.local`, which always installs `debug_toolbar`. That
package is pinned only on `platform-ci-test`. An operator who follows
the Story 11.1 env cannot mint or `runserver`. Found live 2026-09-13.

## Capabilities

- **CAP-1 — Local leaf on platform-dev.**
  - **intent:** The operator can load `config.settings.local` and run
    mint/`manage.py` from the `platform-dev` pixi env without Docker,
    CRC, or a second env.
  - **success:** `django-debug-toolbar` is declared on
    `[feature.platform-dev]` only; it is absent from
    `[feature.python-agent-platform]`; `platform-dev` python imports
    `debug_toolbar` and can `django.setup()` under
    `DJANGO_SETTINGS_MODULE=config.settings.local`; a policy test
    fails if either pin is wrong.

## Constraints

- The toolbar pin lives on the `platform-dev` feature, never on
  `python-agent-platform` (image solve).
- Proof uses pixi-provisioned Postgres/Redis or `manage.py check`
  against that cluster. No compose, no CRC, no `:800x` process farm.
- Do not flip Epic 44 `blocked` keys.
- Never commit on the shared checkout.

## Non-goals

- Changing `config.settings.local` to make the toolbar optional.
- Adding a Keycloak-free browser login path.
- Folding `platform-ci-test` into `platform-dev`.
- Shipping Langflow/DB-GPT sidecars as part of this story.

## Success signal

From `platform-dev` python, `COMPONENT_RUNTIME=local` plus
`config.settings.local` imports without `ModuleNotFoundError`. A
policy test on `pixi.toml` (and the `platform-dev` lock) stays green.

## Assumptions

- Conda-forge `django-debug-toolbar >=8.0.0` solves with the current
  `platform-dev` Django 5.2 line (already locked on `platform-ci-test`).
