"""Story 80.1 -- the one ``requires_helm`` gate for the chart tests.

The chart render/lint tests (``test_chart_invariants.py``,
``test_openfeature_file_flags.py``) shell out to ``helm template``. Until 80.1
each module guarded them with a ``pytest.mark.skipif`` on ``helm`` being absent,
so in the Platform CI ``test`` job -- whose env had no helm -- all 73 skipped
without a word. helm is now pixi-provisioned in ``platform-ci-test`` (AD-16);
this gate makes its absence loud where it must not happen:

* ``helm`` on ``PATH``            -- the test is returned unchanged;
* ``helm`` absent, ``CI`` set     -- a stand-in that FAILS naming ``helm``;
* ``helm`` absent, ``CI`` unset   -- ``pytest.mark.skip`` (a laptop without the
  ``platform-dev`` env still runs the rest of the suite).

A mark cannot fail a test, so this is a decorator rather than a ``skipif``. It
reads ``shutil.which("helm")`` and ``os.environ`` when it is applied (import
time, like the ``skipif(bool)`` it replaces); ``tests/test_helm_gate.py`` patches
``PATH`` and ``CI`` and applies it again to prove each branch. ``CI`` counts as
set when non-empty -- GitHub Actions exports ``CI=true``.
"""

from __future__ import annotations

import functools
import os
import shutil
from collections.abc import Callable
from typing import Any

import pytest

_HELM_ABSENT = (
    "helm not on PATH (AD-16: provided by the platform-ci-test and platform-dev "
    "pixi envs) -- chart render/lint tests need it"
)


def requires_helm[F: Callable[..., Any]](test: F) -> F:
    """Gate ``test`` on ``helm``: run it, fail it under ``CI``, or skip it."""
    if shutil.which("helm") is not None:
        return test
    if os.environ.get("CI"):

        @functools.wraps(test)
        def _helm_missing_under_ci(*_args: Any, **_kwargs: Any) -> None:
            pytest.fail(
                f"{_HELM_ABSENT}; CI is set, so a missing helm fails the chart "
                "tests instead of skipping them",
                pytrace=False,
            )

        return _helm_missing_under_ci  # type: ignore[return-value]
    return pytest.mark.skip(reason=_HELM_ABSENT)(test)
