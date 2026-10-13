"""Shared pytest fixtures for pyforge-steward unit tests.

The flag-provider fixture lives here, not in ``tests/conftest.py``: the pip-only lane
(``pyforge-pip-install.yml``) installs pyforge-steward without the testing kit and runs
``tests/meta``, so a root conftest importing ``pyforge.testing_kit`` breaks collection there
(the marshal station keeps its copy in ``tests/unit/conftest.py`` for the same reason).
"""

from __future__ import annotations

from pyforge.testing_kit import make_flag_provider_fixture

flag_provider = make_flag_provider_fixture()
