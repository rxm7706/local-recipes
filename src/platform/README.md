# Python Agent Platform

Django host for the python-agent-platform — Langflow and DB-GPT join as pluggable apps

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

Identity is OIDC-delegated (CAP-1). There is no local password login and no
`createsuperuser` path — staff and superuser derive from IdP group claims on
each authentication.

**Local development without Keycloak:** mint a persona JWT and exercise the
mapper-backed flows:

    $ cd src/platform
    $ COMPONENT_RUNTIME=local python -m config.local_dev.mint staff

**Local development with Keycloak:** start the compose stack (includes a
realm-as-code Keycloak import) and sign in through the IdP:

    $ docker compose -f src/platform/compose/compose.yml up keycloak platform

Configure OIDC via `COMPONENT_OIDC_*` environment variables (see
`config/settings/base.py`). Default local claim names: identity `sub`, groups
`groups`, staff group `platform-staff`, superuser group `platform-superuser`.

### Type checks

Running type checks with mypy:

    $ mypy platformapp

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd platform
celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd platform
celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd platform
celery -A config.celery_app worker -B -l info
```

## Deployment

The following details how to deploy this application.
