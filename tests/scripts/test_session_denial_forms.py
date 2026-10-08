"""Story 85.6 — every backticked command in session_denials reasons resolves.

Runs under ``pixi run -e pyforge-ci pyforge-doctor-scripts-test`` (stdlib-only),
like ``tests/scripts/test_pre_shell_hook.py``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROSTER = REPO_ROOT / "docs" / "governance" / "guild-roster.json"
PIXII = REPO_ROOT / "pixi.toml"
PACKAGES = REPO_ROOT / "src" / "shared" / "packages"

_PLACEHOLDERS = {
    "<branch>": "example-branch",
    "<slug>": "example-slug",
    "<project>/<spec>": "pyforge-steward/spec-pyforge-steward",
    "<station>": "steward",
    "{task}": "detectors-ci",
}


def _substitute_placeholders(span: str) -> str:
    out = span
    for key, value in _PLACEHOLDERS.items():
        out = out.replace(key, value)
    return out


def _pixi_task_names() -> frozenset[str]:
    text = PIXII.read_text(encoding="utf-8")
    return frozenset(
        re.findall(r"^\[(?:feature\.[^.]+\.)?tasks\.([A-Za-z0-9._-]+)\]", text, re.M)
    )


def _pixi_environment_names() -> frozenset[str]:
    text = PIXII.read_text(encoding="utf-8")
    return frozenset(re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*) = \{ features", text, re.M))


def _iter_reason_strings(reason: str | dict[str, str]) -> Iterator[str]:
    if isinstance(reason, str):
        yield reason
        return
    for value in reason.values():
        if isinstance(value, str):
            yield value


def _backtick_spans(text: str) -> list[str]:
    return re.findall(r"`([^`]+)`", text)


def _classify_span(span: str) -> str:
    stripped = span.strip()
    if not stripped:
        return "unclassified"
    if stripped.startswith("--") and " " not in stripped:
        return "third-party"
    parts = shlex.split(_substitute_placeholders(stripped))
    if not parts:
        return "unclassified"
    head = parts[0]
    if head in ("git", "gh", "npx"):
        return "third-party"
    if head == "uv" and len(parts) >= 2 and parts[1] == "run":
        if len(parts) >= 3 and ("/" in parts[2] or parts[2].endswith(".py")):
            return "repo-script"
        return "third-party"
    if head == "pixi":
        if len(parts) >= 2 and parts[1] == "run":
            return "pixi-task"
        return "third-party"
    if head == "python" and len(parts) >= 2:
        script = parts[1]
        if script.startswith("scripts/") or script.endswith(".py"):
            return "repo-script"
    if head == "pyforge" and len(parts) >= 2:
        return "station-verb"
    return "unclassified"


def _repo_script_path(parts: list[str]) -> Path | None:
    if parts[0] == "python" and len(parts) >= 2:
        rel = parts[1]
        if rel.startswith("scripts/"):
            return REPO_ROOT / rel
        return REPO_ROOT / rel if rel.endswith(".py") else None
    if parts[0] == "uv" and len(parts) >= 3 and parts[1] == "run":
        rel = parts[2]
        return REPO_ROOT / rel
    return None


def _script_accepts_argv(script: Path, argv: list[str]) -> str | None:
    if not script.is_file():
        return f"missing script path {script.relative_to(REPO_ROOT).as_posix()}"
    trial = subprocess.run(
        [sys.executable, str(script), *argv],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    combined = trial.stderr + trial.stdout
    if "unrecognized arguments" in combined or "invalid choice:" in combined:
        rel = script.relative_to(REPO_ROOT).as_posix()
        return f"{rel} rejects {argv!r}"
    return None


def _resolve_repo_script(span: str) -> str | None:
    parts = shlex.split(_substitute_placeholders(span.strip()))
    script = _repo_script_path(parts)
    if script is None:
        return f"unrecognized repo script span {span!r}"
    if not script.is_file():
        return f"missing script {script.relative_to(REPO_ROOT).as_posix()}"
    if parts[0] == "python":
        argv = parts[2:]
    else:
        argv = parts[3:]
    if argv:
        err = _script_accepts_argv(script, argv)
        if err:
            return err
    return None


def _resolve_pixi_task(span: str) -> str | None:
    parts = shlex.split(_substitute_placeholders(span.strip()))
    if len(parts) < 4 or parts[0] != "pixi" or parts[1] != "run" or parts[2] != "-e":
        return f"malformed pixi task span {span!r}"
    env = parts[3]
    if env not in _pixi_environment_names():
        return f"pixi environment {env!r} not declared"
    if len(parts) < 5:
        return f"pixi task span missing task name: {span!r}"
    task = parts[4]
    if task == "{task}":
        return None
    if task not in _pixi_task_names():
        return f"pixi task {task!r} not declared"
    return None


def _station_build_parser(station: str) -> argparse.ArgumentParser:
    pkg_root = PACKAGES / f"pyforge-{station}" / "src"
    core_root = PACKAGES / "pyforge-core" / "src"
    if not pkg_root.is_dir():
        raise FileNotFoundError(station)
    for entry in (str(core_root), str(pkg_root)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    if station == "marshal":
        from pyforge.marshal.cli.main import _build_parser

        return _build_parser()
    if station == "steward":
        from pyforge.steward.cli import build_parser

        return build_parser()
    mod = importlib.import_module(f"pyforge.{station}.cli")
    build = getattr(mod, "build_parser", None) or getattr(mod, "_build_parser", None)
    if build is None:
        raise AttributeError(station)
    return build()


def _resolve_station_verb(span: str) -> str | None:
    parts = shlex.split(_substitute_placeholders(span.strip()))
    if len(parts) < 2 or parts[0] != "pyforge":
        return f"malformed pyforge span {span!r}"
    station = parts[1]
    argv = parts[2:]
    try:
        parser = _station_build_parser(station)
    except (FileNotFoundError, AttributeError, ImportError) as exc:
        return f"pyforge {station} parser not buildable here: {exc}"
    try:
        parser.parse_args(argv)
    except SystemExit:
        return f"pyforge {station} {' '.join(argv)!r} not accepted by parser"
    return None


def verify_span(span: str) -> str | None:
    kind = _classify_span(span)
    if kind == "third-party":
        return None
    if kind == "repo-script":
        return _resolve_repo_script(span)
    if kind == "pixi-task":
        return _resolve_pixi_task(span)
    if kind == "station-verb":
        return _resolve_station_verb(span)
    return f"unclassified span {span!r}"


def verify_session_denials(roster: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for rule in roster.get("session_denials", []):
        rule_id = rule.get("id", "?")
        for reason in _iter_reason_strings(rule["reason"]):
            for span in _backtick_spans(reason):
                err = verify_span(span)
                if err:
                    errors.append(f"{rule_id}: {err} (span `{span}`)")
    return errors


def test_live_roster_session_denial_forms_resolve() -> None:
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    errors = verify_session_denials(roster)
    assert errors == []


def test_broken_retire_form_in_reason_fails() -> None:
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    for rule in roster["session_denials"]:
        if rule["id"] == "protected-ref-deletion":
            rule = dict(rule)
            rule["reason"] = (
                rule["reason"]
                + " Retry with `python scripts/worktree_sweep.py --retire <branch>`."
            )
            roster = dict(roster)
            roster["session_denials"] = [
                rule if r["id"] == "protected-ref-deletion" else r for r in roster["session_denials"]
            ]
            break
    errors = verify_session_denials(roster)
    assert any("worktree_sweep.py" in e and "--retire" in e for e in errors)


@pytest.fixture
def roster_template() -> dict[str, Any]:
    return json.loads(ROSTER.read_text(encoding="utf-8"))


def test_fixture_bad_script_flag(roster_template: dict[str, Any]) -> None:
    roster_template["session_denials"] = [
        {
            "id": "fixture-bad-flag",
            "applies_to": "bash",
            "trigger": "x",
            "reason": "Use `python scripts/worktree_sweep.py --no-such-flag`.",
        }
    ]
    errors = verify_session_denials(roster_template)
    assert len(errors) == 1
    assert "--no-such-flag" in errors[0]


def test_fixture_missing_script(roster_template: dict[str, Any]) -> None:
    roster_template["session_denials"] = [
        {
            "id": "fixture-missing-script",
            "applies_to": "bash",
            "trigger": "x",
            "reason": "Use `python scripts/no_such_script.py`.",
        }
    ]
    errors = verify_session_denials(roster_template)
    assert len(errors) == 1
    assert "no_such_script.py" in errors[0]


def test_fixture_bad_station_verb(roster_template: dict[str, Any]) -> None:
    roster_template["session_denials"] = [
        {
            "id": "fixture-bad-verb",
            "applies_to": "bash",
            "trigger": "x",
            "reason": "Use `pyforge steward no-such-verb`.",
        }
    ]
    errors = verify_session_denials(roster_template)
    assert len(errors) == 1
    assert "no-such-verb" in errors[0] or "steward" in errors[0]


def test_fixture_unclassified_span(roster_template: dict[str, Any]) -> None:
    roster_template["session_denials"] = [
        {
            "id": "fixture-unclassified",
            "applies_to": "bash",
            "trigger": "x",
            "reason": "Do `totally-unknown-command foo`.",
        }
    ]
    errors = verify_session_denials(roster_template)
    assert len(errors) == 1
    assert "unclassified" in errors[0]


def test_historical_roster_with_retire_and_marshal_preserve_fails() -> None:
    """AC: on b364823896 roster text the guard names the broken spans."""
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    denials: list[dict[str, Any]] = []
    for rule in roster["session_denials"]:
        if rule["id"] == "protected-ref-deletion":
            patched = dict(rule)
            patched["reason"] = (
                "Protected refs and loop homes are not deleted from an agent session -- "
                "retire a branch with `python scripts/worktree_sweep.py --retire <branch>`, "
                "and remove a loop home only after an explicit operator decision."
            )
            denials.append(patched)
        elif rule["id"] == "unreachable-ref-deletion":
            patched = dict(rule)
            patched["reason"] = {
                "unreachable": (
                    "This ref's tip is not on origin/main and no preserve/ or archive/ tag holds it -- "
                    "use `pyforge marshal preserve tag` or "
                    "`python scripts/worktree_sweep.py --retire <branch>` before deleting."
                ),
                "fetch_remedy": (
                    "Cannot resolve this remote branch's tip -- run `git fetch origin` "
                    "so refs/remotes/origin/<branch> exists, then retry."
                ),
            }
            denials.append(patched)
        else:
            denials.append(rule)
    roster = dict(roster)
    roster["session_denials"] = denials
    errors = verify_session_denials(roster)
    joined = "\n".join(errors)
    assert "worktree_sweep.py" in joined and "--retire" in joined
    assert "preserve tag" in joined or "marshal preserve" in joined
