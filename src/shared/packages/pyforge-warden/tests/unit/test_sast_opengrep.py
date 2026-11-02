"""Story 15.1 — opengrep optional SAST advisory lens.

Story 15.2 — the estate-authored rules ship in ``data/sast-rules/`` and trip
their fixtures under ``tests/fixtures/sast-trips/``; the planted marker rule is
a test fixture (``tests/fixtures/sast-rules-planted/``); the telemetry-off argv
and env are pinned; the flag-off strip is pinned through ``warden scan``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest
import yaml
from pyforge.core import flags as core_flags
from pyforge.core.hooks import PluginRegistry

from pyforge.warden.engines import OPENGREP_VERSION_RANGE, build_opengrep_scan_argv, run_opengrep_engine
from pyforge.warden.hooks import PR_GATE_SCAN, invoke_pr_gate
from pyforge.warden.sast import (
    OPENGREP_SCANNER_ID,
    SAST_OPENGREP_FLAG,
    OpengrepScanPlugin,
    bundled_sast_rules_dir,
    opengrep_selectable,
    parse_opengrep_json,
    run_opengrep_advisory,
)
from pyforge.warden.scanner_plugins import OPTIONAL_SCANNER_IDS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FIXTURE_ROOT = FIXTURES / "projects" / "opengrep_tripped"
# Story 15.2: the planted marker rule is a test fixture, never package data.
PLANTED_RULES_DIR = FIXTURES / "sast-rules-planted"
PLANTED_RULE_ID = "planted-opengrep-match"
# Story 15.2: one fixture repo per estate rule, ``sast-trips/<rule id>/trips.py``.
SAST_TRIPS = FIXTURES / "sast-trips"
ESTATE_RULE_IDS = ("subprocess-shell-true", "yaml-unsafe-load", "eval-exec")
RULE_PATTERN_KEYS = frozenset({"pattern", "patterns", "pattern-either"})

needs_opengrep = pytest.mark.skipif(
    shutil.which("opengrep") is None,
    reason="opengrep binary absent (published for linux-64 only, mason Story 21.4)",
)


def _bool_flag_entry(*, default_variant: str) -> dict[str, object]:
    return {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": default_variant,
        "metadata": {
            "owner": "warden",
            "story": "15-1-opengrep-is-an-optional-sast-scanner-that-informs-never-publishes-the-verdict",
            "created": "2026-09-28",
            "on_everywhere": "",
            "cleanup_by": "",
        },
    }


def _flag_tree(tmp_path: Path, *, enabled: bool) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    variant = "on" if enabled else "off"
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps({"flags": {SAST_OPENGREP_FLAG: _bool_flag_entry(default_variant="off")}}),
        encoding="utf-8",
    )
    overlays = {
        "dev": {SAST_OPENGREP_FLAG: variant},
        "staging": {SAST_OPENGREP_FLAG: variant},
        "production": {SAST_OPENGREP_FLAG: "off"},
    }
    (tmp_path / core_flags.OVERLAYS_FILE_NAME).write_text(json.dumps(overlays), encoding="utf-8")
    return path


def test_opengrep_is_listed_as_optional_scanner_id() -> None:
    assert OPENGREP_SCANNER_ID in OPTIONAL_SCANNER_IDS


def test_parse_opengrep_json_maps_a_result_to_advisory_fields() -> None:
    raw = json.dumps(
        {
            "results": [
                {
                    "check_id": "planted-opengrep-match",
                    "path": "sample.py",
                    "start": {"line": 3},
                    "extra": {"severity": "WARNING"},
                }
            ]
        }
    )
    notes, error = parse_opengrep_json(raw)
    assert error is None
    assert len(notes) == 1
    note = notes[0]
    assert note.tool == "opengrep"
    assert note.rule_id == "planted-opengrep-match"
    assert note.path == "sample.py"
    assert note.line == 3
    assert note.severity == "WARNING"


def test_parse_opengrep_json_unparseable_returns_error_message() -> None:
    notes, error = parse_opengrep_json("{not-json")
    assert notes == ()
    assert error is not None


def test_parse_opengrep_json_missing_results_is_empty() -> None:
    notes, error = parse_opengrep_json("{}")
    assert notes == ()
    assert error is None


def test_parse_opengrep_json_results_not_array() -> None:
    notes, error = parse_opengrep_json('{"results": "bad"}')
    assert notes == ()
    assert error is not None


def test_parse_opengrep_json_root_not_object() -> None:
    notes, error = parse_opengrep_json("[]")
    assert notes == ()
    assert error is not None


def test_parse_opengrep_json_skips_non_mapping_entries() -> None:
    notes, error = parse_opengrep_json('{"results": [42, {"check_id": "r1", "path": "a.py", "start": {"line": 2}}]}')
    assert error is None
    assert len(notes) == 1
    assert notes[0].rule_id == "r1"


def test_build_opengrep_scan_argv_uses_local_rules_only(tmp_path: Path) -> None:
    rules = bundled_sast_rules_dir()
    argv = build_opengrep_scan_argv(
        binary="opengrep",
        rules_dir=rules,
        target=tmp_path,
        json_output="/tmp/out.json",
    )
    joined = " ".join(argv)
    assert "--config" in argv
    assert str(rules) in argv
    assert "http" not in joined
    assert "semgrep.dev" not in joined
    assert "auto" not in argv


def test_run_opengrep_advisory_absent_binary_is_silent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.warden.sast.shutil.which", lambda _name: None)
    assert run_opengrep_advisory(tmp_path) == ()


def test_run_opengrep_advisory_whitespace_only_engine_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.warden.sast.shutil.which", lambda _name: "/bin/opengrep")
    monkeypatch.setattr(
        "pyforge.warden.sast.run_opengrep_engine",
        lambda **_kwargs: ("   ", None, 0),
    )
    assert run_opengrep_advisory(tmp_path) == ()


def test_run_opengrep_advisory_runner_bad_exit_is_silent(tmp_path: Path) -> None:
    def runner(_target: Path, _rules: Path, json_path: Path) -> types.SimpleNamespace:
        json_path.write_text('{"results": []}', encoding="utf-8")
        return types.SimpleNamespace(returncode=2)

    assert run_opengrep_advisory(tmp_path, runner=runner) == ()


def test_run_opengrep_advisory_version_failure_becomes_advisory_note(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pyforge.warden.sast.shutil.which", lambda _name: "/bin/opengrep")

    def _fake_engine(**_kwargs: object) -> tuple[str | None, object, int | None]:
        from pyforge.warden.models import ErrorKind, ErrorRecord

        return (
            None,
            ErrorRecord(
                kind=ErrorKind.ENGINE_UNAVAILABLE,
                owner="opengrep",
                message=f"opengrep version 9.9.9 is outside tested range {OPENGREP_VERSION_RANGE!s}",
            ),
            None,
        )

    monkeypatch.setattr("pyforge.warden.sast.run_opengrep_engine", _fake_engine)
    notes = run_opengrep_advisory(tmp_path)
    assert len(notes) == 1
    assert "outside tested range" in notes[0].summary


def test_plugin_appends_advisory_note_when_enabled(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert opengrep_selectable()

    def fake_runner(_target: Path, _rules: Path, json_path: Path) -> types.SimpleNamespace:
        json_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "check_id": "planted-opengrep-match",
                            "path": "sample.py",
                            "start": {"line": 1},
                            "extra": {"severity": "WARNING"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return types.SimpleNamespace(returncode=0)

    plugin = OpengrepScanPlugin(runner=fake_runner)
    context: dict[str, object] = {
        "enabled_optional": ("opengrep",),
        "target": tmp_path,
        "advisory_notes": [],
    }
    registry = PluginRegistry()
    registry.register(plugin)
    invoke_pr_gate(PR_GATE_SCAN, "around", context, registry=registry)
    notes = context["advisory_notes"]
    assert len(notes) == 1
    assert notes[0]["tool"] == "opengrep"
    assert notes[0]["rule_id"] == "planted-opengrep-match"


def test_plugin_enabled_optional_as_string(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")

    def fake_runner(_target: Path, _rules: Path, json_path: Path) -> types.SimpleNamespace:
        json_path.write_text('{"results": [{"check_id": "r", "path": "x.py"}]}', encoding="utf-8")
        return types.SimpleNamespace(returncode=0)

    plugin = OpengrepScanPlugin(runner=fake_runner)
    context: dict[str, object] = {
        "enabled_optional": "opengrep",
        "target": tmp_path,
        "advisory_notes": [],
    }
    plugin.call("around", context)
    assert len(context["advisory_notes"]) == 1


def test_plugin_invokes_next_when_present(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    seen: list[str] = []

    def nxt(ctx: dict[str, object]) -> dict[str, object]:
        seen.append("next")
        return ctx

    plugin = OpengrepScanPlugin(runner=lambda *_: types.SimpleNamespace(returncode=0))
    context: dict[str, object] = {
        "enabled_optional": ("opengrep",),
        "target": tmp_path,
        "advisory_notes": [],
        "next": nxt,
    }
    plugin.call("around", context)
    assert seen == ["next"]


def test_plugin_skips_when_target_is_not_a_path(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    plugin = OpengrepScanPlugin(runner=lambda *_: types.SimpleNamespace(returncode=0))
    context: dict[str, object] = {
        "enabled_optional": ("opengrep",),
        "target": "not-a-path",
        "advisory_notes": [],
    }
    plugin.call("around", context)
    assert context["advisory_notes"] == []


def test_plugin_flag_off_writes_no_note_even_when_enabled_in_env(monkeypatch, tmp_path: Path) -> None:
    tree = _flag_tree(tmp_path / "flags", enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert not opengrep_selectable()

    plugin = OpengrepScanPlugin(
        runner=lambda *_args: types.SimpleNamespace(returncode=0),
    )
    context: dict[str, object] = {
        "enabled_optional": ("opengrep",),
        "target": tmp_path,
        "advisory_notes": [],
    }
    plugin.call("around", context)
    assert context["advisory_notes"] == []


def _scan_json(capsys, target: Path | str) -> tuple[int, dict[str, Any]]:
    from pyforge.warden.cli import main as warden_main

    rc = warden_main(["scan", str(target), "--format", "json"])
    return rc, json.loads(capsys.readouterr().out)


def test_cli_filters_opengrep_when_flag_off(monkeypatch, tmp_path: Path, capsys) -> None:
    """Story 15.2 AC5: with ``WARDEN_OPTIONAL_SCANNERS=opengrep`` and the flag
    OFF, ``warden scan`` strips opengrep before plugin selection (no
    ``PluginError``), opengrep never runs, no error is recorded, and the exit
    code equals a default run."""
    from pyforge.warden import cli as cli_module
    from pyforge.warden import sast as sast_module

    tree = _flag_tree(tmp_path / "flags", enabled=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert not opengrep_selectable()

    real_select = cli_module.select_scanner_plugins
    selections: list[tuple[str, ...]] = []

    def spy_select(enabled_optional: Any = (), **kwargs: Any) -> tuple[Any, ...]:
        selections.append(tuple(enabled_optional))
        return real_select(enabled_optional, **kwargs)

    runs: list[Path] = []

    def spy_run(target: Path, **_kwargs: Any) -> tuple[Any, ...]:
        runs.append(target)
        return ()

    monkeypatch.setattr(cli_module, "select_scanner_plugins", spy_select)
    monkeypatch.setattr(sast_module, "run_opengrep_advisory", spy_run)
    target = SAST_TRIPS / "eval-exec"  # a repo the estate rules would trip

    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)
    rc_default, default = _scan_json(capsys, target)
    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "opengrep")
    rc_flag_off, flag_off = _scan_json(capsys, target)

    assert selections == [(), ()], "the flag-off CLI must strip opengrep before plugin selection"
    assert runs == []
    assert flag_off["errors"] == default["errors"]
    assert not any(error["owner"] == "scanner-plugins" for error in flag_off["errors"])
    assert flag_off.get("advisory") is None
    assert flag_off["status"] == default["status"]
    assert rc_flag_off == rc_default


def test_opengrep_engine_argv_capture(monkeypatch, tmp_path: Path) -> None:
    """Story 15.2 AC4: the socket guard cannot see a subprocess's egress, so the
    argv and env are opengrep's only offline proof. The parent env carries the
    opposite values, so the assertions hold only because ``engines.py`` sets them."""
    captured: dict[str, Any] = {}
    monkeypatch.setenv("SEMGREP_SEND_METRICS", "on")
    monkeypatch.setenv("OPENGREP_ENABLE_VERSION_CHECK", "1")

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if argv[:2] == ["opengrep", "--version"]:
            return subprocess.CompletedProcess(argv, 0, b"1.30.2\n", b"")
        captured["argv"] = list(argv)
        captured["env"] = dict(kwargs["env"])
        json_out = argv[argv.index("--json-output") + 1]
        Path(json_out).write_text('{"results": []}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr("pyforge.warden.engines.subprocess.run", fake_run)
    text, error, _code = run_opengrep_engine(
        binary="opengrep",
        rules_dir=bundled_sast_rules_dir(),
        cwd=tmp_path,
    )
    assert error is None
    assert text is not None
    argv = captured["argv"]
    assert "http" not in " ".join(argv)
    assert str(bundled_sast_rules_dir()) in argv
    assert "--disable-version-check" in argv
    env = captured["env"]
    assert env["SEMGREP_SEND_METRICS"] == "off"
    assert env["OPENGREP_ENABLE_VERSION_CHECK"] == "0"


@pytest.mark.parametrize("flag_on", [True, False])
def test_flag_states_do_not_change_default_scan_exit(monkeypatch, tmp_path: Path, flag_on: bool) -> None:
    """Given the same repo, enabled vs disabled optional opengrep must not move exit/status."""
    from pyforge.warden.cli import main as warden_main

    project = tmp_path / "proj"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="x"\nversion="0.0.0"\n', encoding="utf-8")
    (project / "module.py").write_text("x = 1\n", encoding="utf-8")

    tree = _flag_tree(tmp_path / "flags", enabled=flag_on)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)

    def _deptry_ok(*_args: object, **_kwargs: object) -> tuple[str | None, object, int]:
        return ("[]", None, 0)

    def _osv_ok(*_args: object, **_kwargs: object) -> tuple[str | None, object, int]:
        return ('{"results": []}', None, 0)

    monkeypatch.setattr("pyforge.warden.engines._engine_env", _deptry_ok)
    monkeypatch.setattr("pyforge.warden.engines.run_opengrep_engine", lambda **_k: (None, None, None))

    baseline_code = warden_main(["scan", str(project)])
    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "opengrep")
    with_flag_code = warden_main(["scan", str(project)])
    assert baseline_code == with_flag_code


def test_fixture_repo_trips_rule_with_injected_runner(tmp_path: Path) -> None:
    target = FIXTURE_ROOT
    seen_rules: list[Path] = []

    def runner(_target: Path, rules: Path, json_path: Path) -> types.SimpleNamespace:
        seen_rules.append(rules)
        json_path.write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "check_id": "planted-opengrep-match",
                            "path": "sample.py",
                            "start": {"line": 1},
                            "extra": {"severity": "WARNING"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return types.SimpleNamespace(returncode=1)

    notes = run_opengrep_advisory(target, runner=runner, rules_dir=PLANTED_RULES_DIR)
    assert seen_rules == [PLANTED_RULES_DIR]
    assert any(n.rule_id == PLANTED_RULE_ID for n in notes)


# --- Story 15.2: estate-authored rules, the planted marker as a fixture ------


def _rule_documents(rules_dir: Path) -> dict[str, dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {}
    for path in sorted(rules_dir.glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for rule in document["rules"]:
            rules[rule["id"]] = rule
    return rules


def _marked_lines(fixture: Path, marker: str) -> list[int]:
    lines = fixture.read_text(encoding="utf-8").splitlines()
    return [number for number, line in enumerate(lines, start=1) if line.rstrip().endswith(f"# {marker}")]


def test_bundled_rules_dir_ships_the_estate_rules_and_no_planted_marker() -> None:
    """AC1: the package data holds the estate rules and never the planted marker."""
    rules_dir = bundled_sast_rules_dir()
    names = sorted(path.name for path in rules_dir.iterdir())
    assert "planted-opengrep-match.yaml" not in names
    assert all(name.endswith(".yaml") for name in names), names
    rules = _rule_documents(rules_dir)
    assert set(ESTATE_RULE_IDS) <= set(rules)
    assert PLANTED_RULE_ID not in rules


@pytest.mark.parametrize("rule_path", sorted(bundled_sast_rules_dir().glob("*.yaml")), ids=lambda path: path.name)
def test_every_bundled_rule_parses_with_id_pattern_message_and_severity(rule_path: Path) -> None:
    """AC2's everywhere half: each rule file parses as YAML with an ``id``,
    ``pattern(s)``, ``message`` and ``severity``, and has a trip fixture."""
    document = yaml.safe_load(rule_path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    rules = document.get("rules")
    assert isinstance(rules, list) and rules
    for rule in rules:
        assert isinstance(rule.get("id"), str) and rule["id"]
        assert isinstance(rule.get("message"), str) and rule["message"].strip()
        assert rule.get("severity") in {"INFO", "WARNING", "ERROR"}
        assert rule.get("languages") == ["python"]
        assert RULE_PATTERN_KEYS & set(rule), f"{rule['id']} names no pattern"
        fixture = SAST_TRIPS / rule["id"] / "trips.py"
        assert fixture.is_file(), f"{rule['id']} has no trip fixture"
        assert _marked_lines(fixture, "trips"), f"{fixture} marks no tripping line"


def test_planted_marker_rule_is_a_test_fixture() -> None:
    """AC3: the planted rule lives under ``tests/fixtures/``."""
    assert (PLANTED_RULES_DIR / "planted-opengrep-match.yaml").is_file()
    assert set(_rule_documents(PLANTED_RULES_DIR)) == {PLANTED_RULE_ID}


def test_parse_opengrep_json_strips_the_rules_dir_prefix_from_the_rule_id(tmp_path: Path) -> None:
    """opengrep prefixes each ``check_id`` with the rules directory, dotted."""
    rules_dir = tmp_path / "py3.14" / "sast-rules"
    dotted = ".".join(part for part in rules_dir.parts if part != rules_dir.anchor)
    raw = json.dumps(
        {
            "results": [
                {"check_id": f"{dotted}.eval-exec", "path": "a.py", "start": {"line": 4}},
                {"check_id": "elsewhere.eval-exec", "path": "a.py", "start": {"line": 5}},
            ]
        }
    )
    notes, error = parse_opengrep_json(raw, rules_dir=rules_dir)
    assert error is None
    assert [note.rule_id for note in notes] == ["eval-exec", "elsewhere.eval-exec"]
    assert "rule=eval-exec " in notes[0].summary
    unstripped, _ = parse_opengrep_json(raw)
    assert unstripped[0].rule_id == f"{dotted}.eval-exec"


def test_run_opengrep_advisory_hands_the_engine_an_absolute_target(monkeypatch, tmp_path: Path) -> None:
    """The engine runs inside ``cwd`` and names it as the scan target: a
    relative ``warden scan <dir>`` target must reach it absolute."""
    seen: list[Path] = []

    def fake_engine(**kwargs: Any) -> tuple[str | None, object, int | None]:
        seen.append(kwargs["cwd"])
        return ('{"results": []}', None, 0)

    monkeypatch.chdir(tmp_path)
    (tmp_path / "repo").mkdir()
    monkeypatch.setattr("pyforge.warden.sast.shutil.which", lambda _name: "/bin/opengrep")
    monkeypatch.setattr("pyforge.warden.sast.run_opengrep_engine", fake_engine)
    assert run_opengrep_advisory(Path("repo")) == ()
    assert len(seen) == 1
    assert seen[0].is_absolute()
    assert seen[0].resolve() == (tmp_path / "repo").resolve()


@needs_opengrep
def test_planted_rule_trips_the_planted_fixture_with_the_real_binary() -> None:
    """AC3: a test that runs the planted rule passes ``rules_dir``."""
    notes = run_opengrep_advisory(FIXTURE_ROOT, rules_dir=PLANTED_RULES_DIR)
    assert [(note.rule_id, Path(note.path).name, note.line) for note in notes] == [(PLANTED_RULE_ID, "sample.py", 1)]


@needs_opengrep
@pytest.mark.parametrize("rule_id", ESTATE_RULE_IDS)
def test_each_estate_rule_trips_its_fixture_through_warden_scan(
    monkeypatch, tmp_path: Path, capsys, rule_id: str
) -> None:
    """AC2: with opengrep enabled (env + flag ON), ``warden scan`` of the
    rule's fixture repo -- a relative target, as an operator types it --
    carries one advisory note per ``# trips`` line naming the rule id, the
    fixture path and the line, and none on a ``# safe`` line; the status,
    the exit code and every other report field equal the same run with the
    scanner disabled."""
    fixture = SAST_TRIPS / rule_id / "trips.py"
    tree = _flag_tree(tmp_path / "flags", enabled=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    monkeypatch.chdir(SAST_TRIPS)

    monkeypatch.delenv("WARDEN_OPTIONAL_SCANNERS", raising=False)
    rc_disabled, disabled = _scan_json(capsys, rule_id)
    monkeypatch.setenv("WARDEN_OPTIONAL_SCANNERS", "opengrep")
    rc_enabled, enabled = _scan_json(capsys, rule_id)

    assert disabled.get("advisory") is None
    notes = [note for note in enabled["advisory"] or () if note["tool"] == "opengrep"]
    assert notes, "opengrep ran but raised no advisory note"
    assert {note["rule_id"] for note in notes} == {rule_id}
    assert {Path(note["path"]).resolve() for note in notes} == {fixture.resolve()}
    assert sorted(note["line"] for note in notes) == _marked_lines(fixture, "trips")
    assert not set(_marked_lines(fixture, "safe")) & {note["line"] for note in notes}
    assert rc_enabled == rc_disabled
    assert enabled["status"] == disabled["status"]
    for key in disabled:
        if key == "advisory":
            continue
        assert enabled[key] == disabled[key], f"{key!r} differs with opengrep enabled"
