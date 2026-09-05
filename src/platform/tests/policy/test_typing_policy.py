"""Typing policy: ``check_untyped_defs`` stays on; only migrations ignore errors.

Steward 16.4 freezes the mypy gate surface so a one-line relaxation cannot
quietly turn the gate into a warning. Platform CI must keep a Mypy step
targeting ``platformapp config tests``.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from tests.policy import readers

MYPY_TARGETS = ("platformapp", "config", "tests")
MIGRATIONS_MODULE = "*.migrations.*"
MYPY_STEP_RE = re.compile(
    r"^\s+-\s+name:\s*Mypy\s*$"
    r"(?:\n^\s+.*$)*?"
    r"\n^\s+run:\s*mypy\s+(?P<args>.+?)\s*$",
    re.MULTILINE,
)
POLICY_SUITE_STEP_RE = re.compile(
    r"^\s+-\s+name:\s*Policy suite\s*$"
    r"(?:\n^\s+.*$)*?"
    r"\n^\s+run:\s*(?P<command>.+?)\s*$",
    re.MULTILINE,
)


def _assert_check_untyped_defs(mypy: dict[str, Any]) -> None:
    assert mypy.get("check_untyped_defs") is True, (
        "[tool.mypy] check_untyped_defs must be true "
        f"(got {mypy.get('check_untyped_defs')!r})"
    )


def _assert_only_migrations_ignore_errors(mypy: dict[str, Any]) -> None:
    overrides = mypy.get("overrides", [])
    assert isinstance(overrides, list), "mypy overrides must be a list"
    ignoring = [
        override for override in overrides if override.get("ignore_errors") is True
    ]
    assert ignoring, "expected a migrations ignore_errors override; found none"
    modules: list[str] = []
    for override in ignoring:
        module = override.get("module")
        if isinstance(module, str):
            modules.append(module)
        elif isinstance(module, list):
            modules.extend(str(item) for item in module)
        else:
            modules.append(repr(module))
    offenders = [m for m in modules if m != MIGRATIONS_MODULE]
    assert offenders == [], (
        f"only {MIGRATIONS_MODULE!r} may set ignore_errors=true; found {offenders}"
    )


def test_check_untyped_defs_is_true() -> None:
    """Happy path: strict untyped-defs checking stays enabled."""
    _assert_check_untyped_defs(readers.mypy_table())


def test_deliberate_check_untyped_defs_false_reds() -> None:
    """Drift: flipping check_untyped_defs to false must fail."""
    drifted = dict(readers.mypy_table())
    drifted["check_untyped_defs"] = False
    with pytest.raises(AssertionError, match="check_untyped_defs"):
        _assert_check_untyped_defs(drifted)


def test_only_migrations_may_ignore_errors() -> None:
    """Happy path: ignore_errors is migrations-only."""
    _assert_only_migrations_ignore_errors(readers.mypy_table())


def test_deliberate_non_migration_ignore_errors_reds() -> None:
    """Drift: a non-migration ignore_errors override must fail."""
    drifted = dict(readers.mypy_table())
    overrides = list(drifted.get("overrides", []))
    overrides.append({"module": "platformapp.users.*", "ignore_errors": True})
    drifted["overrides"] = overrides
    with pytest.raises(AssertionError, match="ignore_errors"):
        _assert_only_migrations_ignore_errors(drifted)


def test_platform_ci_mypy_step_targets_required_packages() -> None:
    """Platform CI Mypy step must target platformapp config tests."""
    text = readers.platform_ci_workflow_text()
    match = MYPY_STEP_RE.search(text)
    assert match is not None, (
        "platform-ci.yml must contain a named Mypy step running mypy ..."
    )
    args = match.group("args").split()
    for target in MYPY_TARGETS:
        assert target in args, f"Mypy step must include {target!r}; got {args!r}"


def test_deliberate_mypy_step_removal_reds() -> None:
    """Drift: removing the Mypy step from workflow text must fail detection."""
    text = readers.platform_ci_workflow_text()
    drifted = re.sub(
        r"^\s+-\s+name:\s*Mypy\s*\n(?:^\s+.*\n)*?",
        "",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    assert MYPY_STEP_RE.search(drifted) is None

    def _require_mypy_step(workflow_text: str) -> None:
        match = MYPY_STEP_RE.search(workflow_text)
        assert match is not None, (
            "platform-ci.yml must contain a named Mypy step running mypy ..."
        )

    with pytest.raises(AssertionError, match="Mypy step"):
        _require_mypy_step(drifted)


def _require_policy_suite_step(workflow_text: str) -> None:
    match = POLICY_SUITE_STEP_RE.search(workflow_text)
    assert match is not None, (
        "platform-ci.yml must contain a named Policy suite step running "
        "pytest tests/policy"
    )
    command = match.group("command")
    assert "pytest" in command, f"Policy suite step must invoke pytest; got {command!r}"
    assert "tests/policy" in command, (
        f"Policy suite step must target tests/policy; got {command!r}"
    )


def test_platform_ci_policy_suite_step_invokes_tests_policy() -> None:
    """Platform CI Policy suite step must run pytest against tests/policy."""
    _require_policy_suite_step(readers.platform_ci_workflow_text())


def test_deliberate_policy_suite_step_removal_reds() -> None:
    """Drift: removing the Policy suite step from workflow text must fail."""
    text = readers.platform_ci_workflow_text()
    drifted = re.sub(
        r"^\s+-\s+name:\s*Policy suite\s*\n(?:^\s+.*\n)*?",
        "",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    assert POLICY_SUITE_STEP_RE.search(drifted) is None
    with pytest.raises(AssertionError, match="Policy suite"):
        _require_policy_suite_step(drifted)
