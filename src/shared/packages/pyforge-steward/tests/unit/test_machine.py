"""Stories 135.1 and 135.2 (spec-pyforge-steward CAP-183): ``steward init`` reads its checks from a data file.

Everything here runs against a checkout built under ``tmp_path`` and a fake runner: the loader and its refusals, each
probe kind's ``ok`` and ``fail``, the five statuses, the profile verdicts, both reports, and the read-only promise
(every command inside an environment is ``pixi run --as-is``, and a run changes no file of the checkout). The tracked
data file itself is held to the tree by ``tests/meta/test_machine_readiness_data.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.steward import bootstrap, machine, session
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main
from pyforge.steward.machine import BLOCKED, FAIL, NA, OK, SKIPPED, MachineDeps

REMEDY = {"command": "do the thing", "who": "operator"}


def _row(row_id: str, probe: Any, **extra: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": row_id,
        "profile": "desktop",
        "class": "software",
        "severity": "required",
        "what": f"{row_id} holds.",
        "probe": probe,
        "remedy": dict(REMEDY),
    }
    row.update(extra)
    return row


def _doc(*rows: dict[str, Any], profiles: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "profiles": profiles
        or {
            "desktop": {"title": "desktop work", "requires": []},
            "container": {"title": "container work", "requires": ["desktop"]},
            "nkp": {"title": "nkp work", "requires": ["container"], "platforms": ["linux-64"]},
        },
        "checks": list(rows),
    }


def _checkout(
    root: Path,
    doc: dict[str, Any] | None,
    *,
    lock: dict[str, list[str]] | None = None,
    materialized: Sequence[str] = (),
) -> Path:
    """A checkout with the data file, a v7-shaped lock and the named environments materialized."""
    (root / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    if doc is not None:
        (root / machine.DATA_REL).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    (root / "pixi.toml").write_text('[workspace]\nname = "x"\nrequires-pixi = ">=0.80.0"\n', encoding="utf-8")
    environments = {env: {"packages": {key: [] for key in keys}} for env, keys in (lock or {}).items()}
    lock_doc = {
        "version": 7,
        "platforms": [{"name": "linux-64"}, {"name": "osx-arm64-min", "subdir": "osx-arm64"}],
        "environments": environments,
    }
    (root / "pixi.lock").write_text(yaml.safe_dump(lock_doc), encoding="utf-8")
    for env in materialized:
        marker = root / ".pixi" / "envs" / env / "conda-meta" / "pixi"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("{}", encoding="utf-8")
    return root


def _done(code: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, stdout=out, stderr=err)


class FakeRunner:
    """Answers a command by the longest matching prefix of its argv (``which`` returns ``/bin/<name>``)."""

    def __init__(self, answers: dict[tuple[str, ...], subprocess.CompletedProcess[str]] | None = None) -> None:
        self.answers = answers or {}
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        words = [Path(argv[0]).name, *argv[1:]]
        self.calls.append(words)
        best: tuple[str, ...] | None = None
        for prefix in self.answers:
            if tuple(words[: len(prefix)]) == prefix and (best is None or len(prefix) > len(best)):
                best = prefix
        return self.answers[best] if best is not None else _done(1, err="no such command in the fake")


def _refuse(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("this seam must not be reached")


def _deps(
    root: Path,
    *,
    runner: FakeRunner | None = None,
    on_path: Sequence[str] = (),
    platform: str = "osx-arm64",
    environ: dict[str, str] | None = None,
    **seams: Any,
) -> MachineDeps:
    present = set(on_path)
    return MachineDeps(
        root=root,
        runner=runner or FakeRunner(),
        which=lambda name: f"/bin/{name}" if name in present else None,
        platform=platform,
        environ=environ or {},
        home=root / "home",
        session_findings=seams.get("session_findings", _refuse),
        register_row=seams.get("register_row", _refuse),
        register_probe=seams.get("register_probe", _refuse),
        env_sync=seams.get("env_sync", _refuse),
        lane_environments=seams.get("lane_environments", _refuse),
        pixi_floor=seams.get("pixi_floor", lambda _root: "0.80.0"),
    )


def _one(root: Path, doc: dict[str, Any], deps: MachineDeps, **kwargs: Any) -> machine.Report:
    data = machine.load_data(_checkout(root, doc) if not (root / machine.DATA_REL).is_file() else root)
    return machine.run_checks(data, deps, chosen=kwargs.pop("chosen", ["desktop"]), **kwargs)


def _status(report: machine.Report, row_id: str) -> machine.CheckResult:
    return next(result for result in report.checks if result.id == row_id)


def _ns(**kwargs: Any) -> argparse.Namespace:
    base: dict[str, Any] = {
        "json": False,
        "profile": None,
        "check_class": None,
        "deep": False,
        "list": False,
        "repo": None,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


# ── the loader ──────────────────────────────────────────────────────────────────────────────────────────────────


def test_load_data_returns_the_validated_document(tmp_path: Path) -> None:
    doc = _doc(_row("pixi", {"kind": "tool", "name": "pixi"}))
    assert machine.load_data(_checkout(tmp_path, doc)) == doc


def test_load_data_refuses_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(machine.DataFileError, match="could not be read"):
        machine.load_data(_checkout(tmp_path, None))


def test_load_data_refuses_a_file_that_is_not_yaml(tmp_path: Path) -> None:
    _checkout(tmp_path, None)
    (tmp_path / machine.DATA_REL).write_text("checks: [unclosed\n", encoding="utf-8")
    with pytest.raises(machine.DataFileError, match="is not YAML"):
        machine.load_data(tmp_path)


def test_load_data_names_the_first_problems_and_counts_the_rest(tmp_path: Path) -> None:
    rows = [_row(f"bad-{n}", {"kind": "tool", "name": "x"}, severity="sometimes") for n in range(7)]
    with pytest.raises(machine.DataFileError) as caught:
        machine.load_data(_checkout(tmp_path, _doc(*rows)))
    assert "check bad-0: `severity` is one of required, advisory" in str(caught.value)
    assert "and 2 more" in str(caught.value)


def _mutated(**changes: Any) -> dict[str, Any]:
    row = _row("pixi", {"kind": "tool", "name": "pixi"})
    for key, value in changes.items():
        if value is None:
            row.pop(key)
        else:
            row[key] = value
    return _doc(row)


@pytest.mark.parametrize(
    ("doc", "expected"),
    [
        ([], "the document is not a mapping"),
        ({**_doc(_row("a", {"kind": "tool", "name": "a"})), "extra": 1}, "unknown top-level key `extra`"),
        ({**_doc(_row("a", {"kind": "tool", "name": "a"})), "version": 2}, "`version` is 1"),
        ({"version": 1, "profiles": {}, "checks": []}, "`profiles` is a non-empty mapping"),
        (
            {"version": 1, "profiles": {"desktop": {"title": "t", "requires": []}}, "checks": []},
            "`checks` is a non-empty list",
        ),
        (
            _doc(_row("a", {"kind": "tool", "name": "a"}), profiles={"Desk Top": {"title": "t", "requires": []}}),
            "the id is kebab-case",
        ),
        (_doc(_row("a", {"kind": "tool", "name": "a"}), profiles={"desktop": "x"}), "profile desktop: is a mapping"),
        (
            _doc(_row("a", {"kind": "tool", "name": "a"}), profiles={"desktop": {"title": "", "requires": [], "x": 1}}),
            "unknown key `x`",
        ),
        (
            _doc(_row("a", {"kind": "tool", "name": "a"}), profiles={"desktop": {"title": "", "requires": []}}),
            "`title` is a sentence",
        ),
        (
            _doc(_row("a", {"kind": "tool", "name": "a"}), profiles={"desktop": {"title": "t", "requires": "x"}}),
            "`requires` is a list",
        ),
        (
            _doc(_row("a", {"kind": "tool", "name": "a"}), profiles={"desktop": {"title": "t", "requires": ["pod"]}}),
            "requires the undefined profile 'pod'",
        ),
        (
            _doc(
                _row("a", {"kind": "tool", "name": "a"}),
                profiles={"desktop": {"title": "t", "requires": [], "platforms": ["amiga"]}},
            ),
            "`platforms` is a non-empty list",
        ),
        (
            _doc(
                _row("a", {"kind": "tool", "name": "a"}),
                profiles={
                    "desktop": {"title": "t", "requires": ["pod"]},
                    "pod": {"title": "t", "requires": ["desktop"]},
                },
            ),
            "`requires` is a cycle",
        ),
        (_doc("not a row"), "check #1: is a mapping"),  # type: ignore[arg-type]
        (_mutated(extra=1), "check pixi: unknown key `extra`"),
        (_mutated(what=None), "check pixi: lacks `what`"),
        (_mutated(id="Not Kebab"), "`id` is kebab-case"),
        (
            _doc(_row("a", {"kind": "tool", "name": "a"}), _row("a", {"kind": "tool", "name": "a"})),
            "the id is used twice",
        ),
        (_mutated(profile="pod"), "names the undefined profile 'pod'"),
        (_mutated(**{"class": "hardware"}), "`class` is one of"),
        (_mutated(cost="dear"), "`cost` is one of cheap, deep"),
        (_mutated(what=""), "`what` is a sentence"),
        (_mutated(declared_in=""), "`declared_in` is a tracked path"),
        (_mutated(platforms=[]), "`platforms` is a non-empty list"),
        (_mutated(needs=[]), "`needs` is a non-empty list"),
        (_mutated(needs=["later"]), "needs 'later', which is not an earlier check"),
        (_mutated(probe=[]), "`probe` is one probe or a non-empty list of probes"),
        (_mutated(probe="tool"), "a probe is a mapping with a `kind`"),
        (_mutated(probe={"kind": "telepathy"}), "unknown probe kind 'telepathy'"),
        (_mutated(probe={"kind": "tool", "name": "a", "argv": ["x"]}), "tool does not take `argv`"),
        (_mutated(probe={"kind": "tool"}), "tool needs exactly one of `name` or `any_of`"),
        (_mutated(probe={"kind": "tool", "name": "a", "any_of": [{"name": "b"}]}), "tool needs exactly one of"),
        (_mutated(probe={"kind": "command", "argv": []}), "`argv` is a non-empty list of strings"),
        (_mutated(probe={"kind": "tool", "any_of": []}), "`any_of` is a non-empty list"),
        (
            _mutated(probe={"kind": "tool", "any_of": ["docker"]}),
            "each `any_of` entry is a mapping with a non-empty `name`",
        ),
        (
            _mutated(probe={"kind": "tool", "any_of": [{"name": ""}]}),
            "each `any_of` entry is a mapping with a non-empty `name`",
        ),
        (_mutated(probe={"kind": "tool", "any_of": [{"name": "a", "label": ""}]}), "`label` is a non-empty string"),
        (_mutated(platforms=["linux-64", "linux-64"]), "`platforms` names 'linux-64' twice"),
        (_mutated(needs=["pixi", "pixi"]), "`needs` names 'pixi' twice"),
        (
            _doc(
                _row("a", {"kind": "tool", "name": "a"}),
                profiles={
                    "desktop": {"title": "t", "requires": []},
                    "pod": {"title": "t", "requires": ["desktop"] * 2},
                },
            ),
            "profile pod: `requires` names 'desktop' twice",
        ),
        (
            _mutated(remedy={"command": "x", "who": "agent", "doc": "README.md"}),
            "remedy `doc` 'README.md' is not a page under docs/",
        ),
        (
            _mutated(probe={"kind": "env-or-file", "var": "lower-case", "file": ".env"}),
            "`var` 'lower-case' does not match",
        ),
        (
            _mutated(probe={"kind": "env-or-file", "var": "A", "file": ".env", "key": "b"}),
            "`key` 'b' does not match",
        ),
        (_mutated(probe={"kind": "sysctl", "key": "fs inotify", "min": 1}), "`key` 'fs inotify' does not match"),
        (_mutated(probe={"kind": "sysctl", "key": "a.b", "min": -5}), "`min` is at least 0"),
        (_mutated(probe={"kind": "command", "argv": ["a"], "expect_exit": -1}), "`expect_exit` is at least 0"),
        (_mutated(id="pixi\n"), "`id` is kebab-case"),
        (
            _mutated(probe={"kind": "tool", "any_of": [{"name": "a", "path": "x"}]}),
            "takes only name, version_argv and label",
        ),
        (
            _mutated(probe={"kind": "tool", "any_of": [{"name": "a", "version_argv": []}]}),
            "`version_argv` is a non-empty list",
        ),
        (_mutated(probe={"kind": "tool", "name": "a", "floor": {"literal": "new"}}), "`floor` is"),
        (_mutated(probe={"kind": "tool", "name": "a", "floor": "1.0"}), "`floor` is"),
        (_mutated(probe={"kind": "environments", "from": "guesswork"}), "`from` is preflight-lanes"),
        (_mutated(probe={"kind": "session-finding", "name": "mood"}), "unknown session finding 'mood'"),
        (_mutated(probe={"kind": "sysctl", "key": "a.b", "min": "many"}), "`min` is an integer"),
        (_mutated(probe={"kind": "file", "path": ""}), "`path` is a non-empty string"),
        (_mutated(probe={"kind": "command", "argv": ["a"], "stdout_match": "("}), "is not a regular expression"),
        (_mutated(probe={"kind": "command", "argv": ["a"], "expect_exit": "0"}), "`expect_exit` is an integer"),
        (_mutated(probe={"kind": "command", "argv": ["a"], "timeout_s": 0}), "`timeout_s` is a positive number"),
        (
            _mutated(probe={"kind": "command", "argv": ["a"], "exit_notes": {"two": "x"}}),
            "`exit_notes` maps an exit code",
        ),
        (_mutated(remedy="reboot"), "`remedy` is a mapping"),
        (_mutated(remedy={"command": "x", "who": "operator", "cost": 1}), "remedy has the unknown key `cost`"),
        (_mutated(remedy={"who": "operator"}), "remedy lacks `command`"),
        (_mutated(remedy={"command": "x"}), "remedy lacks `who`"),
        (_mutated(remedy={"command": "x", "who": "agent", "where": "moon"}), "remedy `where` is one of"),
        (_mutated(remedy={"command": "x", "who": "agent", "note": ""}), "remedy `note` is a non-empty string"),
    ],
)
def test_validate_data_names_each_broken_rule(doc: object, expected: str) -> None:
    assert any(expected in problem for problem in machine.validate_data(doc)), machine.validate_data(doc)


@pytest.mark.parametrize(
    ("probe", "expected"),
    [
        (
            {"kind": "tool", "any_of": [{"name": "a"}], "version_argv": ["a", "--version"]},
            "tool with `any_of` does not take `version_argv`",
        ),
        ({"kind": "tool", "name": "a", "any_of": [{"name": "b"}]}, "tool needs exactly one of"),
        ({"kind": "environments", "names": ["x"], "from": "preflight-lanes"}, "environments needs exactly one of"),
    ],
)
def test_a_probe_must_fit_one_of_its_kinds_key_groups(probe: dict[str, Any], expected: str) -> None:
    """The schema's ``oneOf``: each group allows its own keys, so a key of the other group is refused."""
    problems = machine.validate_data(_mutated(probe=probe))
    assert any(expected in problem for problem in problems), problems


def _profiles_with_requires(requires: list[Any]) -> dict[str, Any]:
    return {"desktop": {"title": "desktop work", "requires": requires}}


@pytest.mark.parametrize("bad", [["x"], {"x": 1}], ids=["list", "mapping"])
@pytest.mark.parametrize(
    ("build", "expected"),
    [
        (
            lambda bad: _doc(
                _row("a", {"kind": "tool", "name": "a"}), _row("b", {"kind": "tool", "name": "b"}, needs=[bad])
            ),
            "check b: `needs` is a non-empty list of check ids",
        ),
        (
            lambda bad: _doc(_row("a", {"kind": "tool", "name": "a"}), profiles=_profiles_with_requires([bad])),
            "profile desktop: `requires` is a list of profile ids",
        ),
        (lambda bad: _doc(_row("a", {"kind": "tool", "name": "a"}, profile=bad)), "check a: `profile` is a profile id"),
        (lambda bad: _doc(_row("a", {"kind": bad, "name": "a"})), "check a: unknown probe kind"),
    ],
    ids=["needs-item", "requires-item", "row-profile", "probe-kind"],
)
def test_a_list_or_mapping_where_an_id_belongs_is_a_problem_never_a_crash(
    tmp_path: Path, build: Any, expected: str, bad: object
) -> None:
    doc = build(bad)
    problems = machine.validate_data(doc)
    assert any(expected in problem for problem in problems), problems
    result = machine.run_init(_ns(), deps=_deps(_checkout(tmp_path, doc)))
    assert result.details == {"exit_code": machine.EXIT_CANNOT_JUDGE}


def test_profile_closure_puts_a_required_profile_first() -> None:
    data = _doc(_row("a", {"kind": "tool", "name": "a"}))
    assert machine.profile_closure(data, ["nkp", "desktop"]) == ["desktop", "container", "nkp"]


def test_desktop_software_tools_are_the_default_profiles_named_tools(tmp_path: Path) -> None:
    doc = _doc(
        _row("pixi", {"kind": "tool", "name": "pixi"}),
        _row("identity", {"kind": "git-config", "keys": ["user.name"]}, **{"class": "configuration"}),
        _row("git", {"kind": "tool", "name": "git"}),
        _row("engine", {"kind": "tool", "any_of": [{"name": "docker"}]}, profile="container"),
    )
    assert machine.desktop_software_tools(_checkout(tmp_path, doc)) == ("pixi", "git")


# ── tool ────────────────────────────────────────────────────────────────────────────────────────────────────────


def test_tool_ok_reports_the_version_and_the_floor(tmp_path: Path) -> None:
    doc = _doc(_row("pixi", {"kind": "tool", "name": "pixi", "floor": {"pixi-requires": True}}))
    runner = FakeRunner({("pixi", "--version"): _done(out="pixi 0.84.2\n")})
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["pixi"])), "pixi")
    assert (result.status, result.found, result.required) == (OK, "0.84.2", "0.80.0")
    assert result.detail == "pixi 0.84.2 (floor >= 0.80.0)"


def test_tool_fails_when_it_is_not_on_path(tmp_path: Path) -> None:
    doc = _doc(_row("gh", {"kind": "tool", "name": "gh"}))
    result = _status(_one(tmp_path, doc, _deps(tmp_path)), "gh")
    assert (result.status, result.detail) == (FAIL, "gh is not on PATH")


def test_tool_fails_below_a_literal_floor(tmp_path: Path) -> None:
    doc = _doc(
        _row("kind", {"kind": "tool", "name": "kind", "version_argv": ["version"], "floor": {"literal": "0.32.0"}})
    )
    runner = FakeRunner({("kind", "version"): _done(out="kind v0.20.0 go1.21\n")})
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["kind"])), "kind")
    assert (result.status, result.found, result.required) == (FAIL, "0.20.0", "0.32.0")
    assert "below the floor 0.32.0" in result.detail


def test_tool_fails_when_the_version_cannot_be_read(tmp_path: Path) -> None:
    doc = _doc(_row("oc", {"kind": "tool", "name": "oc", "version_argv": ["version", "--client"]}))
    runner = FakeRunner({("oc",): _done(1, err="boom")})
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["oc"])), "oc")
    assert result.status == FAIL
    assert "`oc version --client` gave no version (exit 1)" in result.detail


ENGINE = {
    "kind": "tool",
    "any_of": [{"name": "docker"}, {"name": "podman"}],
    "found_note": "pass `--engine {name}` to the script",
}


@pytest.mark.parametrize("engine", ["docker", "podman"])
def test_engine_is_ok_with_either_engine_and_names_the_one_it_found(tmp_path: Path, engine: str) -> None:
    doc = _doc(_row("engine", ENGINE, profile="container"))
    runner = FakeRunner({(engine, "--version"): _done(out=f"{engine} version 5.1.0\n")})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=[engine]), chosen=["container"])
    result = _status(report, "engine")
    assert result.status == OK
    assert result.detail == f"{engine} 5.1.0; pass `--engine {engine}` to the script"
    assert report.found == {"engine": engine}


def test_engine_fails_with_neither_engine_and_the_remedy_is_the_operators(tmp_path: Path) -> None:
    doc = _doc(_row("engine", ENGINE, profile="container"))
    report = _one(tmp_path, doc, _deps(tmp_path), chosen=["container"])
    assert _status(report, "engine").detail == "docker is not on PATH; podman is not on PATH"
    text = machine.format_report(report)
    assert "  FAIL    engine: docker is not on PATH; podman is not on PATH" in text
    assert "          remedy (operator): do the thing" in text
    assert "steward init: container NOT READY (not ok: engine)" in text


def test_a_tool_with_a_label_runs_its_own_version_argv(tmp_path: Path) -> None:
    probe = {
        "kind": "tool",
        "any_of": [{"name": "docker", "version_argv": ["compose", "version"], "label": "docker compose"}],
    }
    runner = FakeRunner({("docker", "compose", "version"): _done(out="Docker Compose version v2.29.1\n")})
    result = _status(
        _one(tmp_path, _doc(_row("compose", probe)), _deps(tmp_path, runner=runner, on_path=["docker"])), "compose"
    )
    assert (result.status, result.detail) == (OK, "docker compose 2.29.1")


# ── command ─────────────────────────────────────────────────────────────────────────────────────────────────────


def test_a_command_in_an_environment_runs_as_is_and_only_when_materialized(tmp_path: Path) -> None:
    doc = _doc(_row("cli", {"kind": "command", "env": "guild", "argv": ["steward", "--version"]}))
    _checkout(tmp_path, doc, lock={"guild": ["osx-arm64-min"]}, materialized=["guild"])
    runner = FakeRunner({("pixi", "run", "--as-is", "-x", "-e", "guild", "steward", "--version"): _done()})
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner)), "cli")
    assert (result.status, result.detail) == (OK, "`pixi run --as-is -e guild steward --version` exit 0")
    assert runner.calls == [["pixi", "run", "--as-is", "-x", "-e", "guild", "steward", "--version"]]


def test_a_command_is_blocked_when_its_environment_is_not_materialized(tmp_path: Path) -> None:
    doc = _doc(
        _row(
            "cli",
            {"kind": "command", "env": "guild", "argv": ["steward"]},
            remedy={"command": "pixi install -e {env}", "who": "agent"},
        )
    )
    _checkout(tmp_path, doc, lock={"guild": ["osx-arm64-min"]})
    runner = FakeRunner()
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner))
    result = _status(report, "cli")
    assert (result.status, result.missing) == (BLOCKED, ("guild",))
    assert runner.calls == []
    text = machine.format_report(report)
    assert "  BLOCKED cli: the environment guild is not materialized" in text
    assert "          remedy (agent): pixi install -e guild" in text


def test_a_command_is_not_applicable_when_the_lock_lacks_its_environment_here(tmp_path: Path) -> None:
    doc = _doc(_row("cli", {"kind": "command", "env": "stack", "argv": ["x"]}))
    _checkout(tmp_path, doc, lock={"stack": ["linux-64"]})
    report = _one(tmp_path, doc, _deps(tmp_path))
    assert _status(report, "cli").status == NA
    assert "the lock does not carry stack for osx-arm64" in _status(report, "cli").detail
    assert report.ok, "a check that cannot be measured here is never a failure"


def test_a_command_fails_when_the_lock_cannot_be_read(tmp_path: Path) -> None:
    doc = _doc(_row("cli", {"kind": "command", "env": "guild", "argv": ["x"]}))
    _checkout(tmp_path, doc)
    (tmp_path / "pixi.lock").write_text("[not, a, mapping]\n", encoding="utf-8")
    assert _status(_one(tmp_path, doc, _deps(tmp_path)), "cli").detail == "pixi.lock could not be read"


def test_a_command_fails_on_another_exit_code_and_uses_the_rows_note(tmp_path: Path) -> None:
    probe = {"kind": "command", "argv": ["oc", "whoami"], "exit_notes": {"2": "the switch is off"}}
    doc = _doc(_row("a", probe), _row("b", {"kind": "command", "argv": ["oc", "status"]}))
    runner = FakeRunner({("oc", "whoami"): _done(2), ("oc", "status"): _done(1, out="first\nlast line\n")})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["oc"]))
    assert _status(report, "a").detail == "`oc whoami` exited 2: the switch is off"
    assert _status(report, "b").detail == "`oc status` exited 1: last line"


def test_a_command_fails_when_stdout_lacks_the_pattern(tmp_path: Path) -> None:
    doc = _doc(_row("pg", {"kind": "command", "argv": ["status"], "stdout_match": "listening on"}))
    runner = FakeRunner({("status",): _done(out="[scribe-pg] not listening on 127.0.0.1:5433\n")})
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["status"])), "pg")
    assert result.status == OK, "the fixture's own line contains the pattern"
    doc = _doc(_row("pg", {"kind": "command", "argv": ["status"], "stdout_match": r"\] listening on"}))
    (tmp_path / machine.DATA_REL).unlink()
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["status"])), "pg")
    assert result.status == FAIL
    assert "printed no line matching" in result.detail


@pytest.mark.parametrize(("platform", "status"), [("osx-arm64", FAIL), ("linux-64", OK)])
def test_platform_in_a_command_is_this_machines_platform_name(tmp_path: Path, platform: str, status: str) -> None:
    """``{platform}`` in argv and stdout_match is this machine's pixi platform, escaped in the pattern."""
    probe = {"kind": "command", "argv": ["estate", "{platform}"], "stdout_match": "(?m)^{platform}: .*confirmed"}
    out = "linux-64: lock_sha=1 verdict=confirmed\nosx-arm64: lock_sha=1 verdict=lock-solved\n"
    runner = FakeRunner({("estate", platform): _done(out=out)})
    result = _status(
        _one(tmp_path, _doc(_row("e", probe)), _deps(tmp_path, runner=runner, on_path=["estate"], platform=platform)),
        "e",
    )
    assert runner.calls == [["estate", platform]]
    assert result.status == status, result.detail


def test_a_missed_pattern_reads_the_rows_miss_note_instead_of_the_last_line(tmp_path: Path) -> None:
    probe = {
        "kind": "command",
        "argv": ["estate"],
        "stdout_match": "^{platform}: confirmed",
        "miss_note": "nothing confirms {platform}",
    }
    runner = FakeRunner({("estate",): _done(out="linux-64: confirmed\n}\n")})
    result = _status(_one(tmp_path, _doc(_row("e", probe)), _deps(tmp_path, runner=runner, on_path=["estate"])), "e")
    assert result.status == FAIL
    assert result.detail.endswith(": nothing confirms osx-arm64"), result.detail


def test_a_miss_note_without_a_pattern_is_refused() -> None:
    doc = _doc(_row("e", {"kind": "command", "argv": ["x"], "miss_note": "why"}))
    assert "check e: `miss_note` explains a missed `stdout_match`, which the probe lacks" in machine.validate_data(doc)


def test_a_command_outside_an_environment_needs_its_program_on_path(tmp_path: Path) -> None:
    doc = _doc(_row("crc", {"kind": "command", "argv": ["crc", "status"]}))
    assert _status(_one(tmp_path, doc, _deps(tmp_path)), "crc").detail == "crc is not on PATH"


def test_a_command_uses_the_tool_an_earlier_row_found(tmp_path: Path) -> None:
    doc = _doc(
        _row("engine", ENGINE),
        _row("daemon", {"kind": "command", "argv": ["{found:engine}", "info"]}, needs=["engine"]),
    )
    runner = FakeRunner({("podman", "--version"): _done(out="podman version 5.1.0"), ("podman", "info"): _done()})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["podman"]))
    assert _status(report, "daemon").detail == "`podman info` exit 0"


# ── environments ────────────────────────────────────────────────────────────────────────────────────────────────


def test_environments_ok_when_each_is_in_the_lock_here_and_materialized(tmp_path: Path) -> None:
    doc = _doc(_row("envs", {"kind": "environments", "names": ["guild", "ci"]}))
    _checkout(tmp_path, doc, lock={"guild": ["osx-arm64-min"], "ci": ["osx-arm64-min"]}, materialized=["guild", "ci"])
    assert _status(_one(tmp_path, doc, _deps(tmp_path)), "envs").detail == "materialized: guild, ci"


def test_environments_fail_names_each_missing_one_and_prints_a_remedy_per_environment(tmp_path: Path) -> None:
    doc = _doc(
        _row(
            "envs",
            {"kind": "environments", "names": ["guild", "ci", "site"]},
            remedy={"command": "pixi install --frozen -e {env}", "who": "agent"},
        )
    )
    _checkout(tmp_path, doc, lock={name: ["osx-arm64-min"] for name in ("guild", "ci", "site")}, materialized=["guild"])
    report = _one(tmp_path, doc, _deps(tmp_path))
    assert _status(report, "envs").detail == "not materialized: ci, site"
    text = machine.format_report(report)
    assert "          remedy (agent): pixi install --frozen -e ci" in text
    assert "          remedy (agent): pixi install --frozen -e site" in text


def test_environments_from_the_preflight_lanes_name_the_lanes_an_absent_one_removes(tmp_path: Path) -> None:
    doc = _doc(_row("lanes", {"kind": "environments", "from": "preflight-lanes"}))
    _checkout(tmp_path, doc, lock={"guild": ["osx-arm64-min"], "stack": ["linux-64"]}, materialized=["guild"])
    deps = _deps(tmp_path, lane_environments=lambda _root: {"guild": ["lint"], "stack": ["platform-test", "e2e"]})
    result = _status(_one(tmp_path, doc, deps), "lanes")
    assert result.status == OK
    assert result.detail == (
        "materialized: guild; not applicable here, the lock does not carry for osx-arm64: "
        "stack (its lanes do not run here: platform-test, e2e)"
    )


def test_environments_are_not_applicable_when_the_lock_carries_none_of_them_here(tmp_path: Path) -> None:
    doc = _doc(_row("envs", {"kind": "environments", "names": ["stack"]}))
    _checkout(tmp_path, doc, lock={"stack": ["linux-64"]})
    assert _status(_one(tmp_path, doc, _deps(tmp_path)), "envs").status == NA


def test_environments_fail_without_a_lock(tmp_path: Path) -> None:
    doc = _doc(_row("envs", {"kind": "environments", "names": ["guild"]}))
    _checkout(tmp_path, doc)
    (tmp_path / "pixi.lock").unlink()
    assert "pixi.lock could not be read" in _status(_one(tmp_path, doc, _deps(tmp_path)), "envs").detail


def test_a_lock_without_a_platforms_table_is_read_by_its_own_keys(tmp_path: Path) -> None:
    doc = _doc(_row("envs", {"kind": "environments", "names": ["guild"]}))
    _checkout(tmp_path, doc, materialized=["guild"])
    (tmp_path / "pixi.lock").write_text(
        yaml.safe_dump({"version": 6, "environments": {"guild": {"packages": {"osx-arm64": []}}, "odd": "x"}}),
        encoding="utf-8",
    )
    assert _status(_one(tmp_path, doc, _deps(tmp_path)), "envs").status == OK


# ── the composed duties ─────────────────────────────────────────────────────────────────────────────────────────


def test_session_findings_are_composed_and_the_kit_is_asked_once(tmp_path: Path) -> None:
    asked: list[tuple[str, ...]] = []

    def findings(_root: Path, names: Sequence[str]) -> dict[str, tuple[bool, str]]:
        asked.append(tuple(names))
        return {name: (name != "codegraph-index", f"{name} detail") for name in names}

    doc = _doc(
        _row("auth", {"kind": "session-finding", "name": "gh-auth"}),
        _row(
            "kit",
            [{"kind": "session-finding", "name": "token-kit"}, {"kind": "session-finding", "name": "codegraph-index"}],
            severity="advisory",
        ),
    )
    report = _one(tmp_path, doc, _deps(tmp_path, session_findings=findings))
    assert asked == [("gh-auth",), ("token-kit", "codegraph-index")]
    assert (_status(report, "auth").status, _status(report, "auth").composes) == (OK, "steward session check: gh-auth")
    assert (_status(report, "kit").status, _status(report, "kit").detail) == (FAIL, "codegraph-index detail")
    assert report.ok, "an advisory row never changes the verdict"
    assert "  WARN    kit: codegraph-index detail" in machine.format_report(report)


@pytest.mark.parametrize(("state", "status"), [("live", OK), ("stale", FAIL), ("missing", FAIL)])
def test_a_register_probe_is_the_registers_own_verdict(tmp_path: Path, state: str, status: str) -> None:
    doc = _doc(
        _row(
            "pg",
            {"kind": "register-probe", "package": "postgresql"},
            remedy={"command": "pixi install -e {env}", "who": "agent"},
        )
    )
    _checkout(tmp_path, doc, lock={"platform-dev": ["osx-arm64-min"]}, materialized=["platform-dev"])
    seen: list[str] = []

    def probe(_root: Path, row: dict[str, Any], package: str, lock_platform: str, _runner: Any) -> str:
        seen.append(f"{package}@{lock_platform}")
        return state

    deps = _deps(tmp_path, register_row=lambda _root, _package: {"env": "platform-dev"}, register_probe=probe)
    report = _one(tmp_path, doc, deps)
    result = _status(report, "pg")
    assert (result.status, result.composes) == (status, "realization register: postgresql")
    assert seen == ["postgresql@osx-arm64-min"], "the register reads the lock by the lock's own platform name"
    if status == FAIL:
        assert "remedy (agent): pixi install -e platform-dev" in machine.format_report(report)


def test_a_register_probe_fails_on_a_package_the_register_lacks_and_waits_for_its_environment(tmp_path: Path) -> None:
    doc = _doc(
        _row("gone", {"kind": "register-probe", "package": "nope"}),
        _row("pg", {"kind": "register-probe", "package": "postgresql"}),
    )
    _checkout(tmp_path, doc, lock={"platform-dev": ["osx-arm64-min"]})
    deps = _deps(tmp_path, register_row=lambda _root, package: None if package == "nope" else {"env": "platform-dev"})
    report = _one(tmp_path, doc, deps)
    assert "has no row nope" in _status(report, "gone").detail
    assert (_status(report, "pg").status, _status(report, "pg").composes) == (
        BLOCKED,
        "realization register: postgresql",
    )


@pytest.mark.parametrize(("ok", "status"), [(True, OK), (False, FAIL)])
def test_env_sync_is_provisions_own_comparison(tmp_path: Path, ok: bool, status: str) -> None:
    doc = _doc(_row("sync", {"kind": "env-sync"}))
    result = _status(_one(tmp_path, doc, _deps(tmp_path, env_sync=lambda _root: (ok, "the detail"))), "sync")
    assert (result.status, result.detail, result.composes) == (status, "the detail", "steward provision --verify")


# ── configuration probes ────────────────────────────────────────────────────────────────────────────────────────


def test_git_config_reports_presence_and_never_the_value(tmp_path: Path) -> None:
    doc = _doc(_row("identity", {"kind": "git-config", "keys": ["user.name", "user.email"]}))
    runner = FakeRunner({("git", "config", "--get", "user.name"): _done(out="Ada Lovelace\n")})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner))
    assert _status(report, "identity").detail == "not set: user.email"
    runner.answers[("git", "config", "--get", "user.email")] = _done(out="ada@example.test\n")
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner))
    assert _status(report, "identity").detail == "set: user.name, user.email"
    for rendered in (machine.format_report(report), json.dumps(machine.report_payload(report))):
        assert "Ada" not in rendered and "example.test" not in rendered


def test_git_hooks_reads_the_shared_hooks_directory(tmp_path: Path) -> None:
    doc = _doc(_row("hooks", {"kind": "git-hooks", "types": ["commit-msg", "pre-push"]}))
    common = tmp_path / "primary" / ".git"
    (common / "hooks").mkdir(parents=True)
    (common / "hooks" / "commit-msg").write_text("#!/bin/sh\n", encoding="utf-8")
    runner = FakeRunner({("git", "rev-parse", "--git-common-dir"): _done(out=f"{common}\n")})
    deps = _deps(tmp_path, runner=runner)
    assert _status(_one(tmp_path, doc, deps), "hooks").detail == "not installed in the shared hooks directory: pre-push"
    (common / "hooks" / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
    assert _status(_one(tmp_path, doc, deps), "hooks").status == OK
    assert "not a git checkout" in _status(_one(tmp_path, doc, _deps(tmp_path)), "hooks").detail


@pytest.mark.parametrize(
    ("environ", "status"),
    [
        ({"LANG": "en_US.UTF-8"}, OK),
        ({"LC_ALL": "C", "LANG": "en_US.UTF-8"}, FAIL),
        ({"LC_ALL": "en_GB.utf8"}, OK),
        ({"LC_CTYPE": "en_US.UTF-8"}, OK),
        ({"LC_CTYPE": "C", "LANG": "en_US.UTF-8"}, FAIL),
        ({}, FAIL),
        # CPython coerces its own LC_CTYPE under a C locale; that value says nothing about the shell.
        ({"LC_CTYPE": "UTF-8"}, FAIL),
        ({"LC_CTYPE": "C.UTF-8", "LANG": "en_US.UTF-8"}, OK),
    ],
)
def test_the_locale_is_read_from_its_variables(tmp_path: Path, environ: dict[str, str], status: str) -> None:
    doc = _doc(_row("locale", {"kind": "locale-utf8"}, severity="advisory"))
    result = _status(_one(tmp_path, doc, _deps(tmp_path, environ=environ)), "locale")
    assert result.status == status
    assert "LANG=" in result.detail


SECRET = "hunter2-do-not-print"


def test_a_variable_or_a_file_key_is_reported_by_presence_never_by_value(tmp_path: Path) -> None:
    doc = _doc(
        _row("secret", {"kind": "env-or-file", "var": "APP_PASSWORD", "file": "compose/.env"}),
        _row("pull", {"kind": "file", "path": "~/.config/pull-secret.json"}),
    )
    _checkout(tmp_path, doc)
    absent = _one(tmp_path, doc, _deps(tmp_path))
    assert (
        _status(absent, "secret").detail
        == "APP_PASSWORD is not set in the environment and compose/.env has no APP_PASSWORD"
    )
    assert _status(absent, "pull").detail == "~/.config/pull-secret.json does not exist"

    from_env = _one(tmp_path, doc, _deps(tmp_path, environ={"APP_PASSWORD": SECRET}))
    (tmp_path / "compose").mkdir()
    (tmp_path / "compose" / ".env").write_text(f"OTHER=1\nexport APP_PASSWORD='{SECRET}'\n", encoding="utf-8")
    (tmp_path / "home" / ".config").mkdir(parents=True)
    (tmp_path / "home" / ".config" / "pull-secret.json").write_text(json.dumps({"auths": SECRET}), encoding="utf-8")
    from_file = _one(tmp_path, doc, _deps(tmp_path))
    assert _status(from_env, "secret").detail == "APP_PASSWORD is set in the environment (its value is not read out)"
    assert _status(from_file, "secret").detail == "APP_PASSWORD is a key of compose/.env (its value is not read out)"
    assert _status(from_file, "pull").status == OK
    for report in (from_env, from_file):
        for rendered in (machine.format_report(report), json.dumps(machine.report_payload(report))):
            assert SECRET not in rendered


def test_a_file_key_with_an_empty_value_and_an_unreadable_file_are_absent(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("APP_PASSWORD=\n", encoding="utf-8")
    assert machine._file_has_key(tmp_path / ".env", "APP_PASSWORD") is False
    assert machine._file_has_key(tmp_path / "nope", "APP_PASSWORD") is False


def test_a_file_probe_takes_a_relative_and_an_absolute_path(tmp_path: Path) -> None:
    (tmp_path / "here.txt").write_text("x", encoding="utf-8")
    doc = _doc(
        _row("rel", {"kind": "file", "path": "here.txt"}),
        _row("abs", {"kind": "file", "path": str(tmp_path / "here.txt")}),
    )
    report = _one(tmp_path, doc, _deps(tmp_path))
    assert (_status(report, "rel").status, _status(report, "abs").status) == (OK, OK)


def test_sysctl_is_not_applicable_off_linux(tmp_path: Path) -> None:
    doc = _doc(_row("inotify", {"kind": "sysctl", "key": "fs.inotify.max_user_instances", "min": 1024}))
    result = _status(_one(tmp_path, doc, _deps(tmp_path, platform="osx-arm64")), "inotify")
    assert result.status == NA
    assert "is a Linux kernel setting, and this is osx-arm64" in result.detail


@pytest.mark.parametrize(
    ("answer", "status", "fragment"),
    [
        (_done(out="1024\n"), OK, "is 1024 (at least 1024)"),
        (_done(out="128\n"), FAIL, "is 128, below 1024"),
        (_done(1, err="unknown key"), FAIL, "gave no number (exit 1)"),
    ],
)
def test_sysctl_compares_the_kernel_value_on_linux(
    tmp_path: Path, answer: subprocess.CompletedProcess[str], status: str, fragment: str
) -> None:
    doc = _doc(_row("inotify", {"kind": "sysctl", "key": "fs.inotify.max_user_instances", "min": 1024}))
    runner = FakeRunner({("sysctl", "-n", "fs.inotify.max_user_instances"): answer})
    result = _status(_one(tmp_path, doc, _deps(tmp_path, runner=runner, platform="linux-64")), "inotify")
    assert result.status == status
    assert fragment in result.detail


# ── statuses and verdicts ───────────────────────────────────────────────────────────────────────────────────────


def test_a_failed_need_blocks_the_row_and_its_probe_is_not_run(tmp_path: Path) -> None:
    doc = _doc(
        _row("engine", ENGINE, profile="container"),
        _row("daemon", {"kind": "command", "argv": ["{found:engine}", "info"]}, profile="container", needs=["engine"]),
        _row("amd64", {"kind": "command", "argv": ["{found:engine}", "run"]}, profile="container", needs=["daemon"]),
    )
    runner = FakeRunner()
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner), chosen=["container"])
    assert (_status(report, "daemon").status, _status(report, "daemon").detail) == (
        BLOCKED,
        "needs engine, which is fail",
    )
    assert _status(report, "amd64").detail == "needs daemon, which is blocked"
    assert runner.calls == []
    assert "  BLOCKED daemon: needs engine, which is fail" in machine.format_report(report)


def test_a_row_for_other_platforms_is_not_applicable_and_holds_nothing_back(tmp_path: Path) -> None:
    doc = _doc(_row("win", {"kind": "tool", "name": "x"}, platforms=["win-64"]))
    report = _one(tmp_path, doc, _deps(tmp_path))
    assert _status(report, "win").detail == "not applicable here: the check applies to win-64, not osx-arm64"
    assert report.ok
    assert "  n/a     win: not applicable here" in machine.format_report(report)


def test_a_deep_row_is_skipped_without_deep_and_run_with_it(tmp_path: Path) -> None:
    doc = _doc(
        _row("amd64", {"kind": "command", "argv": ["podman", "run", "--rm"]}, cost="deep"),
        _row("after", {"kind": "command", "argv": ["podman", "ps"]}, needs=["amd64"]),
    )
    runner = FakeRunner({("podman",): _done()})
    deps = _deps(tmp_path, runner=runner, on_path=["podman"])
    shallow = _one(tmp_path, doc, deps)
    assert (_status(shallow, "amd64").status, _status(shallow, "after").status) == (SKIPPED, SKIPPED)
    assert runner.calls == [], "a deep row starts nothing without --deep"
    assert shallow.ok, "a skipped row never blocks"
    assert "steward init: desktop READY (2 deep checks skipped; --deep runs them)" in machine.format_report(shallow)
    assert "  skip    amd64: a deep check; --deep runs it" in machine.format_report(shallow)
    deep = _one(tmp_path, doc, deps, deep=True)
    assert (_status(deep, "amd64").status, _status(deep, "after").status) == (OK, OK)
    assert runner.calls == [["podman", "run", "--rm"], ["podman", "ps"]]


def test_a_profile_is_not_ready_when_a_required_row_of_a_profile_it_requires_fails(tmp_path: Path) -> None:
    doc = _doc(
        _row("gh", {"kind": "tool", "name": "gh"}),
        _row("engine", ENGINE, profile="container"),
    )
    runner = FakeRunner({("docker", "--version"): _done(out="Docker version 27.0.1")})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["docker"]), chosen=["container"])
    verdicts = {profile.id: profile for profile in report.profiles}
    assert _status(report, "engine").status == OK
    assert (verdicts["desktop"].ready, verdicts["desktop"].chosen) == (False, False)
    assert (verdicts["container"].ready, verdicts["container"].reason) == (False, "not ok: gh")
    assert verdicts["container"].counts == {"ok": 1, "fail": 0, "blocked": 0, "skipped": 0, "advisory": 0, "na": 0}
    assert not report.ok


def test_nkp_is_unsupported_off_linux_64_and_its_rows_are_not_applicable(tmp_path: Path) -> None:
    doc = _doc(
        _row("gh", {"kind": "tool", "name": "gh"}),
        _row("nic", {"kind": "tool", "name": "nic"}, profile="nkp"),
    )
    runner = FakeRunner({("gh", "--version"): _done(out="gh 2.1.0")})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["gh"], platform="osx-arm64"), chosen=["nkp"])
    nkp = report.profiles[-1]
    assert (nkp.id, nkp.supported, nkp.ready) == ("nkp", False, False)
    assert nkp.reason == "unsupported here: the nkp profile needs linux-64, and this machine is osx-arm64"
    assert _status(report, "nic").status == NA
    assert not report.ok
    text = machine.format_report(report)
    assert "steward init: nkp NOT READY (unsupported here: the nkp profile needs linux-64" in text
    assert "remedy" not in text, "an unsupported profile has no remedy"


def test_nkp_is_judged_on_linux_64(tmp_path: Path) -> None:
    doc = _doc(_row("nic", {"kind": "tool", "name": "nic"}, profile="nkp"))
    runner = FakeRunner({("nic", "--version"): _done(out="nic 0.17.0")})
    report = _one(tmp_path, doc, _deps(tmp_path, runner=runner, on_path=["nic"], platform="linux-64"), chosen=["nkp"])
    assert (report.profiles[-1].supported, report.profiles[-1].ready, report.ok) == (True, True, True)


def test_a_probe_that_raises_is_a_failed_row_never_a_crash(tmp_path: Path) -> None:
    def explode(_root: Path) -> tuple[bool, str]:
        raise RuntimeError("the export died")

    doc = _doc(_row("sync", {"kind": "env-sync"}))
    result = _status(_one(tmp_path, doc, _deps(tmp_path, env_sync=explode)), "sync")
    assert (result.status, result.detail) == (FAIL, "the env-sync probe could not run: RuntimeError: the export died")


def test_a_class_filter_keeps_every_row_a_chosen_row_needs(tmp_path: Path) -> None:
    doc = _doc(
        _row("git", {"kind": "tool", "name": "git"}),
        _row("gh", {"kind": "tool", "name": "gh"}),
        _row("identity", {"kind": "git-config", "keys": ["user.name"]}, **{"class": "configuration"}, needs=["git"]),
    )
    data = machine.load_data(_checkout(tmp_path, doc))
    assert [row["id"] for row in machine.select_rows(data, ["desktop"], ["configuration"])] == ["git", "identity"]
    assert [row["id"] for row in machine.select_rows(data, ["desktop"], None)] == ["git", "gh", "identity"]


def test_a_profile_with_no_chosen_row_says_so(tmp_path: Path) -> None:
    doc = _doc(
        _row("gh", {"kind": "tool", "name": "gh"}), _row("engine", ENGINE, profile="container", **{"class": "usable"})
    )
    report = _one(tmp_path, doc, _deps(tmp_path), chosen=["container"], classes=["usable"])
    assert "desktop - desktop work\n  (no check of this profile was chosen)" in machine.format_report(report)


def test_a_remedy_names_where_it_runs_its_note_and_its_page(tmp_path: Path) -> None:
    remedy = {
        "command": "steward setup",
        "who": "agent",
        "where": "primary-checkout",
        "note": "once",
        "doc": "docs/how-to/x.md",
    }
    doc = _doc(_row("hooks", {"kind": "tool", "name": "x"}, remedy=remedy))
    report = _one(tmp_path, doc, _deps(tmp_path))
    text = machine.format_report(report)
    assert "          remedy (agent): steward setup   [from the primary checkout, never a linked worktree]" in text
    assert "          note: once" in text
    assert "          see: docs/how-to/x.md" in text
    assert machine.report_payload(report)["checks"][0]["remedy"] == {  # type: ignore[index]
        "command": "steward setup",
        "commands": ["steward setup"],
        "who": "agent",
        "where": "primary-checkout",
        "note": "once",
        "doc": "docs/how-to/x.md",
    }


def test_a_remedy_with_no_missing_environment_keeps_a_placeholder() -> None:
    row = _row("x", {"kind": "tool", "name": "x"}, remedy={"command": "pixi install -e {env}", "who": "agent"})
    assert machine.remedy_commands(row, (), {}) == ["pixi install -e <environment>"]
    row["remedy"]["command"] = "{found:engine} info"
    assert machine.remedy_commands(row, (), {}) == ["<engine> info"]
    assert machine.remedy_commands(row, (), {"engine": "podman"}) == ["podman info"]


def test_a_blocked_environment_row_prints_an_exact_command_from_its_own_probe(tmp_path: Path) -> None:
    """With no pixi nothing is measured, so each ``{env}`` is filled from what the row's own probe names."""
    install = {"command": "pixi install --frozen -e {env}", "who": "agent"}
    environment = {"class": "environment", "needs": ["pixi"], "remedy": install}
    doc = _doc(
        _row("pixi", {"kind": "tool", "name": "pixi"}),
        _row("guild", {"kind": "environments", "names": ["guild", "other"]}, **environment),
        _row("lanes", {"kind": "environments", "from": "preflight-lanes"}, **environment),
        _row("own", {"kind": "command", "env": "atlas", "argv": ["pyforge", "atlas", "--version"]}, **environment),
        _row("servers", {"kind": "register-probe", "package": "postgresql"}, **environment),
    )
    deps = _deps(
        tmp_path,
        lane_environments=lambda _root: {"pyforge-guild": ["lint-types"], "platform-ci-test": ["platform-ci-local"]},
        register_row=lambda _root, package: {"package": package, "env": "platform-dev"},
    )
    report = _one(tmp_path, doc, deps)
    assert {row: _status(report, row).status for row in ("guild", "lanes", "own", "servers")} == dict.fromkeys(
        ("guild", "lanes", "own", "servers"), BLOCKED
    )
    text = machine.format_report(report)
    assert "<environment>" not in text
    for command in (
        "  BLOCKED guild: needs pixi, which is fail\n          remedy (agent): pixi install --frozen -e guild\n"
        "          remedy (agent): pixi install --frozen -e other",
        "  BLOCKED lanes: needs pixi, which is fail\n          remedy (agent): pixi install --frozen -e pyforge-guild\n"
        "          remedy (agent): pixi install --frozen -e platform-ci-test",
        "  BLOCKED own: needs pixi, which is fail\n          remedy (agent): pixi install --frozen -e atlas",
        "  BLOCKED servers: needs pixi, which is fail\n          remedy (agent): pixi install --frozen -e platform-dev",
    ):
        assert command in text
    lanes = next(check for check in machine.report_payload(report)["checks"] if check["id"] == "lanes")  # type: ignore[attr-defined]
    assert lanes["remedy"]["commands"] == [
        "pixi install --frozen -e pyforge-guild",
        "pixi install --frozen -e platform-ci-test",
    ]


def test_a_blocked_row_whose_environments_cannot_be_named_keeps_the_placeholder(tmp_path: Path) -> None:
    def no_lanes(_root: Path) -> dict[str, list[str]]:
        raise FileNotFoundError("pixi.toml")

    install = {"command": "pixi install --frozen -e {env}", "who": "agent"}
    doc = _doc(
        _row("pixi", {"kind": "tool", "name": "pixi"}),
        _row("lanes", {"kind": "environments", "from": "preflight-lanes"}, needs=["pixi"], remedy=install),
    )
    report = _one(tmp_path, doc, _deps(tmp_path, lane_environments=no_lanes))
    assert "remedy (agent): pixi install --frozen -e <environment>" in machine.format_report(report)


def test_a_class_filter_qualifies_the_verdict(tmp_path: Path) -> None:
    deps = _desktop_deps(tmp_path)
    narrowed = machine.run_init(_ns(check_class=["software"]), deps=deps)
    assert narrowed.ok is True
    assert narrowed.summary.splitlines()[-1] == "steward init: desktop READY (software checks only)"
    both = machine.run_init(_ns(check_class=["software", "usable"]), deps=deps)
    assert both.summary.splitlines()[-1] == "steward init: desktop READY (software, usable checks only)"
    payload = json.loads(machine.run_init(_ns(check_class=["software"], json=True), deps=deps).summary)
    assert [profile["classes"] for profile in payload["profiles"]] == [["software"]]
    whole = json.loads(machine.run_init(_ns(json=True), deps=deps).summary)
    assert [profile["classes"] for profile in whole["profiles"]] == [list(machine.CLASSES)]
    assert machine.run_init(_ns(), deps=deps).summary.splitlines()[-1] == "steward init: desktop READY"


def test_a_class_filter_qualifies_a_not_ready_verdict_and_its_reason(tmp_path: Path) -> None:
    result = machine.run_init(_ns(check_class=["software"]), deps=_desktop_deps(tmp_path, on_path=("pixi", "git")))
    assert result.summary.splitlines()[-1] == "steward init: desktop NOT READY (software checks only; not ok: gh)"


# ── the verb ────────────────────────────────────────────────────────────────────────────────────────────────────

DESKTOP = _doc(
    _row("pixi", {"kind": "tool", "name": "pixi", "floor": {"pixi-requires": True}}),
    _row("git", {"kind": "tool", "name": "git"}),
    _row("gh", {"kind": "tool", "name": "gh"}),
    _row("guild", {"kind": "environments", "names": ["guild"]}, **{"class": "environment"}, needs=["pixi"]),
    _row(
        "cli",
        {"kind": "command", "env": "guild", "argv": ["steward", "--version"]},
        **{"class": "usable"},
        needs=["guild"],
    ),
    _row("engine", ENGINE, profile="container"),
)


def _desktop_deps(root: Path, *, on_path: Sequence[str] = ("pixi", "git", "gh")) -> MachineDeps:
    _checkout(root, DESKTOP, lock={"guild": ["osx-arm64-min"]}, materialized=["guild"])
    runner = FakeRunner(
        {
            ("pixi", "--version"): _done(out="pixi 0.84.2"),
            ("git", "--version"): _done(out="git version 2.50.1"),
            ("gh", "--version"): _done(out="gh version 2.80.0"),
            ("pixi", "run", "--as-is"): _done(out="steward 0.1.0"),
        }
    )
    return _deps(root, runner=runner, on_path=on_path)


def test_a_bare_init_is_the_desktop_profile_and_ready_with_no_container_engine(tmp_path: Path) -> None:
    result = machine.run_init(_ns(), deps=_desktop_deps(tmp_path))
    assert result.ok is True
    assert result.details["summary_stream"] == "stdout"
    assert "exit_code" not in result.details
    assert result.summary.splitlines()[-1] == "steward init: desktop READY"
    assert "engine" not in result.summary, "a container engine is not a desktop check"


def test_init_json_carries_the_verdicts_the_rows_and_the_earlier_prereqs_array(tmp_path: Path) -> None:
    result = machine.run_init(
        _ns(json=True, profile=["container"]), deps=_desktop_deps(tmp_path, on_path=("pixi", "git"))
    )
    payload = json.loads(result.summary)
    assert result.ok is False
    assert set(payload) == {"ok", "platform", "root", "data", "profiles", "checks", "prereqs"}
    assert (payload["ok"], payload["platform"], payload["data"]) == (
        False,
        "osx-arm64",
        machine.DATA_REL.as_posix(),
    )
    assert [(p["id"], p["chosen"], p["ready"], p["supported"]) for p in payload["profiles"]] == [
        ("desktop", False, False, True),
        ("container", True, False, True),
    ]
    assert payload["profiles"][1]["requires"] == ["desktop"]
    assert payload["profiles"][0]["counts"] == {"ok": 4, "fail": 1, "blocked": 0, "skipped": 0, "advisory": 0, "na": 0}
    engine = next(check for check in payload["checks"] if check["id"] == "engine")
    assert set(engine) == {
        "id", "profile", "class", "severity", "cost", "status", "what", "found", "required", "detail", "composes",
        "declared_in", "remedy",
    }  # fmt: skip
    assert (engine["status"], engine["remedy"]["who"], engine["cost"]) == ("fail", "operator", "cheap")
    assert payload["prereqs"] == [
        {"name": "pixi", "ok": True, "found": "0.84.2", "required": "0.80.0", "remedy": None},
        {"name": "git", "ok": True, "found": "2.50.1", "required": None, "remedy": None},
        {"name": "gh", "ok": False, "found": None, "required": None, "remedy": "do the thing"},
    ]


def test_list_prints_the_profiles_and_rows_and_probes_nothing(tmp_path: Path) -> None:
    _checkout(tmp_path, DESKTOP)
    deps = MachineDeps(root=tmp_path, runner=_refuse, which=_refuse)
    result = machine.run_init(_ns(list=True), deps=deps)
    assert result.ok is True
    assert "(nothing is probed)" in result.summary
    for line in (
        "desktop - desktop work (requires nothing)",
        "container - container work (requires desktop)",
        "nkp - nkp work (requires container; only on linux-64)",
        "  engine [software, required]: engine holds.",
        "          remedy (operator): do the thing",
    ):
        assert line in result.summary
    only = machine.run_init(_ns(list=True, profile=["desktop"], json=True), deps=deps)
    listed = json.loads(only.summary)
    assert [profile["id"] for profile in listed["profiles"]] == ["desktop"]
    assert listed["checks"][3] == {
        "id": "guild",
        "profile": "desktop",
        "class": "environment",
        "severity": "required",
        "cost": "cheap",
        "platforms": None,
        "needs": ["pixi"],
        "what": "guild holds.",
        "probes": ["environments"],
        "remedy": REMEDY,
        "declared_in": None,
    }


def test_list_marks_a_deep_row(tmp_path: Path) -> None:
    doc = _doc(_row("amd64", {"kind": "tool", "name": "x"}, cost="deep"))
    assert "  amd64 [software, required, deep]: amd64 holds." in machine.format_listing(doc, ["desktop"])


def test_profile_all_is_every_profile(tmp_path: Path) -> None:
    result = machine.run_init(_ns(profile=["all"], json=True), deps=_desktop_deps(tmp_path))
    assert [profile["id"] for profile in json.loads(result.summary)["profiles"]] == ["desktop", "container", "nkp"]


@pytest.mark.parametrize("asked", [["moon", "all"], ["all", "moon"], ["moon", "all", "desktop"]])
def test_an_unknown_profile_beside_all_is_a_usage_error(tmp_path: Path, asked: list[str]) -> None:
    deps = _desktop_deps(tmp_path)
    for listing in (False, True):
        result = machine.run_init(_ns(profile=asked, list=listing), deps=deps)
        assert (result.ok, result.details) == (False, {"exit_code": machine.EXIT_UNKNOWN_PROFILE})
        assert result.summary == "init: unknown profile moon (profiles: desktop, container, nkp, all)"


@pytest.mark.parametrize("as_json", [False, True])
def test_an_unknown_profile_is_a_usage_error(tmp_path: Path, as_json: bool) -> None:
    result = machine.run_init(_ns(profile=["moon"], json=as_json), deps=_desktop_deps(tmp_path))
    message = "init: unknown profile moon (profiles: desktop, container, nkp, all)"
    assert (result.ok, result.details) == (False, {"exit_code": machine.EXIT_UNKNOWN_PROFILE})
    assert result.summary == (json.dumps({"ok": False, "error": message}, indent=2) if as_json else message)


def test_a_missing_and_an_invalid_data_file_are_the_refusal_code(tmp_path: Path) -> None:
    missing = machine.run_init(_ns(), deps=_deps(_checkout(tmp_path / "a", None)))
    assert missing.details == {"exit_code": machine.EXIT_CANNOT_JUDGE}
    assert "machine-readiness.yaml could not be read" in missing.summary
    invalid = machine.run_init(_ns(), deps=_deps(_checkout(tmp_path / "b", {"version": 1})))
    assert invalid.details == {"exit_code": machine.EXIT_CANNOT_JUDGE}
    assert "breaks machine-readiness.schema.json" in invalid.summary


def test_the_cli_projects_each_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ready = _desktop_deps(tmp_path / "ready")
    not_ready = _desktop_deps(tmp_path / "not-ready", on_path=("pixi", "git"))
    monkeypatch.setattr(machine, "production_deps", lambda root: ready if root.name == "ready" else not_ready)
    assert main(["init", "--repo", str(tmp_path / "ready")]) == EXIT_OK
    assert capsys.readouterr().out.rstrip().endswith("steward init: desktop READY")
    assert main(["init", "--repo", str(tmp_path / "not-ready"), "--class", "software"]) == EXIT_FAILED
    out = capsys.readouterr().out
    assert "  FAIL    gh: gh is not on PATH" in out, "the report goes to stdout whatever the verdict"
    assert main(["init", "--repo", str(tmp_path / "ready"), "--profile", "no-such-profile"]) == EXIT_USAGE
    assert main(["init", "--repo", str(tmp_path / "ready"), "--list", "--profile", "all"]) == EXIT_OK
    assert "nkp - nkp work" in capsys.readouterr().out
    assert main(["init", "--repo", str(tmp_path / "ready"), "--class", "hardware"]) == EXIT_USAGE
    (tmp_path / "ready" / machine.DATA_REL).unlink()
    assert main(["init", "--repo", str(tmp_path / "ready")]) == machine.EXIT_CANNOT_JUDGE


def test_init_without_a_repo_root_is_a_finding_not_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_root() -> Path:
        raise RuntimeError("repo root not found")

    monkeypatch.setattr(machine, "repo_root", no_root)
    result = bootstrap.InitDuty().run(_ns(json=True))
    assert json.loads(result.summary) == {"ok": False, "error": "init: repo root not found"}
    assert result.ok is False


# ── read-only ───────────────────────────────────────────────────────────────────────────────────────────────────


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_a_run_of_init_changes_no_file_of_the_checkout_its_environments_or_its_hooks(tmp_path: Path) -> None:
    deps = _desktop_deps(tmp_path)
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
    before = _tree_digest(tmp_path)
    for ns in (_ns(), _ns(profile=["all"], deep=True, json=True), _ns(list=True)):
        machine.run_init(ns, deps=deps)
    assert _tree_digest(tmp_path) == before, "init changed .pixi/, the working tree or the hooks directory"
    assert isinstance(deps.runner, FakeRunner)
    inside = [call for call in deps.runner.calls if call[0] == "pixi" and call[1:2] == ["run"]]
    assert inside, "the fixture runs a command inside an environment"
    assert all(call[:4] == ["pixi", "run", "--as-is", "-x"] for call in inside), inside


def test_the_register_probe_runs_the_registers_command_as_is(tmp_path: Path) -> None:
    runner = FakeRunner({("pixi", "run", "--as-is"): _done()})
    row = {"env": "platform-dev", "probe": {"expect": "exit-0", "command": ["redis-server", "--version"]}}
    assert machine._register_probe(tmp_path, row, "redis-server", "osx-arm64-min", runner) == "live"
    assert runner.calls == [["pixi", "run", "--as-is", "-x", "-e", "platform-dev", "redis-server", "--version"]]


def test_the_session_findings_init_composes_run_as_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launched: list[list[str]] = []

    def drift(argv: Sequence[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        launched.append(list(argv))
        return _done()

    kit = json.dumps({"verb": "check", "ok": True, "result": {"kit": [{"item": "codegraph-index", "status": "ok"}]}})

    def seed(root: Path) -> subprocess.CompletedProcess[str]:
        launched.append(list(session._SEED_CHECK_AS_IS_ARGV))
        return _done(out=kit)

    monkeypatch.setattr(session, "_run_drift_check", drift)
    monkeypatch.setattr(session, "_run_seed_check_as_is", seed)
    monkeypatch.setattr(session, "_run_seed_check", _refuse)
    monkeypatch.setattr(
        session,
        "_gh_auth_finding",
        lambda root=None: session.SessionFinding(name="gh-auth", ok=True, detail="signed in"),
    )
    found = machine._session_findings(tmp_path, session.MACHINE_FINDING_NAMES)
    assert found == {
        "gh-auth": (True, "signed in"),
        "bmad-method": (True, "no HARD/FAIL integrity findings (via `pixi run -e pyforge-guild bmad-drift-check`)"),
        "token-kit": (True, "codegraph-index: ok"),
        "codegraph-index": (True, "codegraph-index: ok"),
    }
    assert len(launched) == 2, "one drift check and one seed check, whatever the number of kit findings"
    assert all(argv[:3] == ["pixi", "run", "--as-is"] for argv in launched), launched
    assert machine._session_findings(tmp_path, ["token-kit"]) == {"token-kit": (True, "codegraph-index: ok")}
    with pytest.raises(ValueError, match="unknown session finding"):
        session.machine_findings(tmp_path, ["tier3-feed"])


def test_the_as_is_seed_check_is_the_seed_check_with_as_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(argv=argv, **kwargs)
        return _done(out="{}")

    monkeypatch.setattr(session.subprocess, "run", fake_run)
    session._run_seed_check_as_is(tmp_path)
    assert seen["argv"] == ["pixi", "run", "--as-is", "-e", "pyforge-guild", "marshal", "seed", "check", "--json"]
    assert seen["cwd"] == str(tmp_path)
    session._run_drift_check_as_is(["pixi", "run", "-e", "x", "t"], tmp_path)
    assert seen["argv"] == ["pixi", "run", "--as-is", "-e", "x", "t"]
    session._run_drift_check_as_is(["pixi", "run", "--as-is", "-e", "x", "t"], tmp_path)
    assert seen["argv"] == ["pixi", "run", "--as-is", "-e", "x", "t"], "an argv that is already as-is is left alone"


# ── the production seams ────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("system", "arch", "expected"),
    [
        ("Darwin", "arm64", "osx-arm64"),
        ("Darwin", "x86_64", "osx-64"),
        ("Linux", "x86_64", "linux-64"),
        ("Linux", "aarch64", "linux-aarch64"),
        ("Windows", "AMD64", "win-64"),
        ("Windows", "ARM64", "win-arm64"),
        ("Plan9", "mips", "plan9-mips"),
    ],
)
def test_host_platform_is_the_pixi_name(system: str, arch: str, expected: str) -> None:
    assert machine.host_platform(system, arch) == expected


def test_host_platform_reads_this_machine_by_default() -> None:
    assert "-" in machine.host_platform()


def test_the_default_runner_never_raises(tmp_path: Path) -> None:
    ok = machine._default_runner([sys.executable, "-c", "print('hi')"], tmp_path, 30)
    assert (ok.returncode, ok.stdout.strip()) == (0, "hi")
    slow = machine._default_runner([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, 0.2)
    assert (slow.returncode, slow.stderr) == (124, "timeout after 0.2s")
    gone = machine._default_runner([str(tmp_path / "no-such-program")], tmp_path, 5)
    assert gone.returncode == 127
    assert gone.stderr.startswith("could not launch:")


def test_the_default_runner_launches_through_the_kernel_process_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pyforge.core.process import PosixProcess, ProcessResult

    seen: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(_self: PosixProcess, argv: Sequence[str], **kwargs: Any) -> ProcessResult:
        seen.append((list(argv), kwargs))
        return ProcessResult(returncode=3, stdout="out", stderr="err")

    monkeypatch.setattr(PosixProcess, "run", fake_run)
    done = machine._default_runner(["probe", "--version"], tmp_path, 7)
    assert seen == [(["probe", "--version"], {"cwd": tmp_path, "timeout_s": 7})]
    assert (done.args, done.returncode, done.stdout, done.stderr) == (["probe", "--version"], 3, "out", "err")


def test_production_deps_are_the_real_seams(tmp_path: Path) -> None:
    deps = machine.production_deps(tmp_path)
    assert (deps.root, deps.runner, deps.env_sync) == (tmp_path, machine._default_runner, machine._env_sync)
    assert deps.platform == machine.host_platform()
    assert deps.home == Path.home()


def test_the_register_row_seam_reads_the_register(tmp_path: Path) -> None:
    (tmp_path / "docs" / "governance").mkdir(parents=True)
    (tmp_path / "docs" / "governance" / "realization-register.yaml").write_text(
        yaml.safe_dump({"version": 1, "rows": [{"package": "gh", "env": "pyforge-guild"}]}), encoding="utf-8"
    )
    assert machine._register_row(tmp_path, "gh") == {"package": "gh", "env": "pyforge-guild"}
    assert machine._register_row(tmp_path, "nope") is None


def test_the_env_sync_seam_reads_each_answer_of_the_comparison(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.steward import provision

    def raising(exc: BaseException) -> Any:
        def _inner(**_kwargs: Any) -> Any:
            raise exc

        return _inner

    monkeypatch.setattr(provision, "check_environment_sync", lambda **_k: (True, ""))
    assert machine._env_sync(tmp_path) == (True, "environment.yaml matches pixi.toml")
    monkeypatch.setattr(provision, "check_environment_sync", lambda **_k: (False, "-a\n+b\n"))
    assert machine._env_sync(tmp_path) == (False, "environment.yaml differs from pixi.toml (2 diff lines)")
    monkeypatch.setattr(provision, "check_environment_sync", raising(FileNotFoundError("environment.yaml")))
    assert machine._env_sync(tmp_path) == (False, "could not compare: environment.yaml")
    monkeypatch.setattr(provision, "check_environment_sync", raising(subprocess.CalledProcessError(3, "pixi")))
    assert machine._env_sync(tmp_path) == (False, "`pixi project export conda-environment -e build` exited 3")


def test_the_lane_seam_groups_the_preflights_lanes_by_environment(tmp_path: Path) -> None:
    (tmp_path / "pixi.toml").write_text(
        "[feature.guild-tasks.tasks.pr-preflight-lanes]\n"
        'depends-on = ["lint", { task = "pages", environment = "site" }]\n'
        '[feature.guild-tasks.tasks.lint]\ncmd = "ruff check"\n'
        '[feature.site.tasks.pages]\ncmd = "npm run build"\n',
        encoding="utf-8",
    )
    assert machine._lane_environments(tmp_path) == {"pyforge-guild": ["lint"], "site": ["pages"]}


def test_the_pixi_floor_seam_reads_requires_pixi(tmp_path: Path) -> None:
    _checkout(tmp_path, None)
    assert machine._pixi_floor(tmp_path) == "0.80.0"


# ── bootstrap: validate-fast and initrepo no longer need a container engine ─────────────────────────────────────


def test_prereq_names_come_from_the_data_file_and_fall_back_without_one(tmp_path: Path) -> None:
    assert bootstrap.prereq_names(_checkout(tmp_path / "plain", None)) == ("pixi", "git", "gh")
    doc = _doc(_row("pixi", {"kind": "tool", "name": "pixi"}), _row("jq", {"kind": "tool", "name": "jq"}))
    assert bootstrap.prereq_names(_checkout(tmp_path / "own", doc)) == ("pixi", "jq")
    only_config = _doc(_row("identity", {"kind": "git-config", "keys": ["user.name"]}, **{"class": "configuration"}))
    assert bootstrap.prereq_names(_checkout(tmp_path / "none", only_config)) == ("pixi", "git", "gh")


PIXI_REMEDY = {
    "command": "curl -fsSL https://example.test/install.sh | bash",
    "who": "operator",
    "note": "run self-update",
}


def test_validate_fast_and_initrepo_take_each_remedy_from_its_desktop_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = _doc(
        _row("pixi", {"kind": "tool", "name": "pixi", "floor": {"pixi-requires": True}}, remedy=PIXI_REMEDY),
        _row("jq", {"kind": "tool", "name": "jq"}, remedy={"command": "pixi global install jq", "who": "operator"}),
    )
    root = _checkout(tmp_path, doc)
    assert bootstrap.prereq_remedies(root) == {
        "pixi": {
            "missing": "install-pixi: curl -fsSL https://example.test/install.sh | bash",
            "below-floor": "upgrade-pixi: run self-update",
        },
        "jq": {"missing": "install-jq: pixi global install jq", "below-floor": "upgrade-jq: pixi global install jq"},
    }
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    assert [row.remedy for row in bootstrap.gather_prereqs(root=root)] == [
        "install-pixi: curl -fsSL https://example.test/install.sh | bash",
        "install-jq: pixi global install jq",
    ]
    steps = bootstrap.validate_fast_steps(root=root, env="pyforge-guild")
    assert (steps[0].name, steps[0].remedy) == (
        "prereqs",
        "install-pixi: curl -fsSL https://example.test/install.sh | bash",
    )
    monkeypatch.setattr(bootstrap, "materialize_environment", lambda *_a, **_k: None)
    monkeypatch.setattr(bootstrap, "scaffold_pyforge_toml", lambda **_k: False)
    initrepo = bootstrap.initrepo_steps(root=root, env="pyforge-guild")
    assert initrepo[-1].remedy == "install-pixi: curl -fsSL https://example.test/install.sh | bash"
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(bootstrap, "_tool_version", lambda _name, _path: "0.0.1")
    below = bootstrap.gather_prereqs(root=root)[0]
    assert (below.ok, below.remedy) == (False, "upgrade-pixi: run self-update")


def test_without_a_data_file_the_remedies_are_the_code_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _checkout(tmp_path, None)
    assert bootstrap.prereq_remedies(root) == bootstrap._REMEDIES
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    assert [row.remedy for row in bootstrap.gather_prereqs(root=root)] == [
        bootstrap._REMEDIES[name]["missing"] for name in ("pixi", "git", "gh")
    ]


def test_gather_prereqs_never_names_a_container_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap.shutil, "which", lambda name: None if name in ("docker", "podman") else f"/bin/{name}"
    )
    monkeypatch.setattr(bootstrap, "_tool_version", lambda _name, _path: "99.0.0")
    results = bootstrap.gather_prereqs(root=_checkout(tmp_path, None))
    assert [row.name for row in results] == ["pixi", "git", "gh"]
    assert all(row.ok for row in results)


def test_validate_fast_is_green_with_no_container_engine_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        bootstrap.shutil, "which", lambda name: None if name in ("docker", "podman") else f"/bin/{name}"
    )
    monkeypatch.setattr(bootstrap, "_tool_version", lambda _name, _path: "99.0.0")
    monkeypatch.setattr(bootstrap, "_run_steward_version", lambda **_k: "steward 0.1.0")
    steps = bootstrap.validate_fast_steps(root=_checkout(tmp_path, None), env="pyforge-guild")
    assert [(step.name, step.ok) for step in steps] == [("prereqs", True), ("env-sync", True), ("steward-cli", True)]


def test_a_prerequisite_the_remedy_table_lacks_points_at_init(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)
    result = bootstrap.check_prereq("jq", pixi_floor="0.80.0")
    assert (result.ok, result.remedy) == (False, "install-jq: run `steward init` for the remedy of the jq check")
