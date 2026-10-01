"""Story 80.1 -- ``tests.helm_gate.requires_helm`` runs, fails or skips by environment.

The chart tests used to skip silently when ``helm`` was absent, which is how all
73 of them skipped in the Platform CI ``test`` job for weeks. These tests pin the
three branches of the gate against a patched ``PATH`` and ``CI``:

* ``helm`` on ``PATH``           -> the test is returned unchanged;
* ``helm`` absent, ``CI`` set    -> it FAILS, naming ``helm``;
* ``helm`` absent, ``CI`` unset  -> it skips.

The gate reads both when it is applied, so each test patches the environment and
applies it afresh. The last test drives a real ``pytest`` run, so the CI branch is
proven to be reported as a failure by pytest, not merely to raise when called.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.helm_gate import requires_helm

if TYPE_CHECKING:
    from collections.abc import Callable

_PLATFORM_DIR = Path(__file__).resolve().parents[1]


def _chart_test() -> Callable[[], str]:
    """A fresh stand-in chart test each call (a skip mark is stored on the function
    it decorates, so a shared one would carry marks from test to test)."""

    def chart_test() -> str:
        return "ran"

    return chart_test


def _without_helm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`PATH` holds one empty directory, so `shutil.which("helm")` is None."""
    monkeypatch.setenv("PATH", str(tmp_path))


def _with_helm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`PATH` holds a directory with an executable named `helm`."""
    fake = tmp_path / "helm"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(tmp_path))


def test_helm_present_returns_the_test_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _with_helm(monkeypatch, tmp_path)
    for ci in ("true", None):
        if ci is None:
            monkeypatch.delenv("CI", raising=False)
        else:
            monkeypatch.setenv("CI", ci)
        chart_test = _chart_test()
        gated = requires_helm(chart_test)
        assert gated is chart_test
        assert gated() == "ran"


def test_helm_absent_under_ci_fails_naming_helm(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _without_helm(monkeypatch, tmp_path)
    monkeypatch.setenv("CI", "true")
    chart_test = _chart_test()
    gated = requires_helm(chart_test)
    assert gated is not chart_test
    with pytest.raises(pytest.fail.Exception, match="helm") as failure:
        gated()
    assert "CI" in str(failure.value)


def test_helm_absent_outside_ci_skips(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _without_helm(monkeypatch, tmp_path)
    monkeypatch.delenv("CI", raising=False)
    gated = requires_helm(_chart_test())
    marks = [m for m in gated.pytestmark if m.name == "skip"]  # type: ignore[attr-defined]
    assert len(marks) == 1
    assert "helm" in marks[0].kwargs["reason"]
    assert gated() == "ran"  # the mark skips at collection; the body is untouched


def test_an_empty_ci_variable_counts_as_unset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _without_helm(monkeypatch, tmp_path)
    monkeypatch.setenv("CI", "")
    gated = requires_helm(_chart_test())
    assert any(m.name == "skip" for m in gated.pytestmark)  # type: ignore[attr-defined]


_PYTEST_SESSION_TEST = textwrap.dedent(
    """
    import sys

    sys.path.insert(0, {platform_dir!r})

    import pytest
    from tests.helm_gate import requires_helm


    @pytest.fixture
    def a_fixture():
        return "fixture-value"


    @requires_helm
    def test_chart_proof(a_fixture):
        assert a_fixture == "fixture-value"
    """,
)


@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param((True, "true", 0, "1 passed"), id="helm-present"),
        pytest.param((False, "true", 1, "1 failed"), id="helm-absent-under-ci"),
        pytest.param((False, None, 0, "1 skipped"), id="helm-absent-outside-ci"),
    ],
)
def test_a_real_pytest_run_reports_each_branch(
    scenario: tuple[bool, str | None, int, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Scenario: (helm on PATH, value of CI or None, exit code, pytest summary)."""
    helm_on_path, ci, exit_code, outcome = scenario
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "test_session.py").write_text(
        _PYTEST_SESSION_TEST.format(platform_dir=str(_PLATFORM_DIR)),
    )
    if helm_on_path:
        _with_helm(monkeypatch, bin_dir)
    else:
        _without_helm(monkeypatch, bin_dir)
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"CI", "DJANGO_SETTINGS_MODULE", "PYTEST_ADDOPTS"}
    }
    if ci is not None:
        env["CI"] = ci
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            os.devnull,
            "--rootdir",
            str(tmp_path),
            "-p",
            "no:django",
            "-p",
            "no:sugar",
            "-p",
            "no:cacheprovider",
            "-q",
            "-rfs",
            str(tmp_path / "test_session.py"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert outcome in result.stdout, result.stdout + result.stderr
    if "failed" in outcome:
        assert "helm not on PATH" in result.stdout, result.stdout
