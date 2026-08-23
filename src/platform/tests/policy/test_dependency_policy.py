"""Dependency policy: pixi is the sole platform dep authority (steward 16.1 / 16.4).

Live clean tree must pass the requirements resurrection checker. Deliberate
resurrection of ``requirements/base.txt`` must red with kind
``resurrected-requirements-file``. Also pins the platform-ci-test feature and
Platform CI setup action, and forbids ``pip install -r requirements`` in the
workflow.
"""

from __future__ import annotations

import importlib.util
import re
from typing import TYPE_CHECKING

import pytest

from tests.policy import readers

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

RESURRECTED_KIND = "resurrected-requirements-file"
PIP_REQUIREMENTS_RE = re.compile(
    r"pip\s+install\b[^\n]*-r\s+requirements\b",
    re.IGNORECASE,
)
PLATFORM_TEST_SETUP_USES_RE = re.compile(
    r"uses:\s*\./\.github/actions/platform-test-setup\b",
)


def _load_requirements_checker() -> ModuleType:
    path = readers.REQUIREMENTS_CHECKER
    spec = importlib.util.spec_from_file_location(
        "platform_ci_test_requirements_check",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def requirements_checker() -> ModuleType:
    return _load_requirements_checker()


def test_platform_ci_test_feature_exists() -> None:
    """``[feature.platform-ci-test]`` remains the CI/test dep authority."""
    pixi = readers.pixi_manifest()
    features = pixi.get("feature", {})
    assert "platform-ci-test" in features, (
        "pixi.toml must declare [feature.platform-ci-test] "
        "(steward 16.1 / CAP-5 sole authority)"
    )
    envs = pixi.get("environments", {})
    assert "platform-ci-test" in envs, (
        "pixi.toml must declare environments.platform-ci-test"
    )


def test_platform_test_setup_action_exists() -> None:
    """Platform CI installs deps via the composite setup action, not pip -r."""
    assert readers.PLATFORM_TEST_SETUP_ACTION.is_file(), (
        f"missing {readers.PLATFORM_TEST_SETUP_ACTION.relative_to(readers.REPO_ROOT)}"
    )
    action = readers.load_yaml(readers.PLATFORM_TEST_SETUP_ACTION)
    text = readers.PLATFORM_TEST_SETUP_ACTION.read_text(encoding="utf-8")
    assert "platform-ci-test" in text, (
        "platform-test-setup action must install the platform-ci-test env"
    )
    assert action.get("runs", {}).get("using") == "composite"


def test_platform_ci_workflow_uses_test_setup_action() -> None:
    """Platform CI test job must install deps via platform-test-setup action."""
    text = readers.platform_ci_workflow_text()
    assert PLATFORM_TEST_SETUP_USES_RE.search(text), (
        "platform-ci.yml test job must declare "
        "uses: ./.github/actions/platform-test-setup"
    )


def test_platform_ci_workflow_has_no_pip_install_requirements() -> None:
    """Workflow must not reintroduce ``pip install -r requirements``."""
    text = readers.platform_ci_workflow_text()
    match = PIP_REQUIREMENTS_RE.search(text)
    assert match is None, (
        "platform-ci.yml must not pip-install from requirements/: "
        f"found {match.group(0)!r}"
    )


def test_clean_tree_has_no_resurrected_requirements(
    requirements_checker: ModuleType,
) -> None:
    """Live tree: retired requirements/{base,local,production}.txt stay gone."""
    findings, _stats = requirements_checker.run()
    assert findings == [], (
        "resurrected requirements files must not exist: "
        + "; ".join(f.get("detail", f.get("kind", "?")) for f in findings)
    )


def test_deliberate_resurrect_reds_with_expected_kind(
    requirements_checker: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resurrecting requirements/base.txt must red with the expected finding kind."""
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    (req_dir / "base.txt").write_text("django==0.0.0\n", encoding="utf-8")
    monkeypatch.setattr(requirements_checker, "REQUIREMENTS_DIR", req_dir)

    findings, stats = requirements_checker.run()

    assert findings, "expected resurrection findings, got none"
    kinds = {f.get("kind") for f in findings}
    assert RESURRECTED_KIND in kinds, (
        f"expected finding kind {RESURRECTED_KIND!r}, got {kinds!r}"
    )
    assert any(
        f.get("kind") == RESURRECTED_KIND and f.get("package") == "base.txt"
        for f in findings
    ), findings
    assert stats.get("resurrected"), stats
