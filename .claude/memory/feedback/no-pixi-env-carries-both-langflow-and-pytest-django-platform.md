---
name: "no-pixi-env-carries-both-langflow-and-pytest-django-platform"
description: "No pixi env carries both langflow and pytest-django: platform-ci-test has pytest-django but no langflow (so tests/test_…"
metadata:
  type: feedback
---

No pixi env carries both langflow and pytest-django: platform-ci-test has pytest-django but no langflow (so tests/test_langflow_mount.py skips in platform-ci-local), platform-dev has langflow but no pytest-django. A story that changes Langflow behaviour must run its live test by hand under platform-dev with Postgres and Redis up, manage.py migrate first, -o addopts=--import-mode=importlib, DJANGO_SETTINGS_MODULE=config.settings.test, and the in-repo src/shared/packages/pyforge-*/src dirs on PYTHONPATH; the built-image curl smoke is the only CI proof. Also: a compose ${VAR:?} is evaluated for every compose command on the file, not only the service that uses it, so adding one silently skips any test that drives that compose file (the live Keycloak PKCE test turns the failed up into pytest.skip) until its subprocess env supplies the variable. Found on steward Story 78.1, 2026-10-01.
