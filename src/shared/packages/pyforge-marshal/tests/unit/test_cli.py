"""Unit tests for ``pyforge.marshal.cli.main`` (Story 1.1 stub;
``--version``/``--help`` with no subcommand) and ``pyforge.marshal.cli.config``
(Story 1.3's first real subcommand, ``marshal config``). ``main`` always
returns an int and never raises ``SystemExit`` itself.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from unittest.mock import patch

import jsonschema
import pytest

from pyforge.marshal.cli.main import __version__, main
from pyforge.marshal.core.verdict import EXIT_SIGINT, EXIT_USAGE

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal" / "schemas" / "policy.json"
)


def test_version_returns_zero_and_prints_version(capsys):
    exit_code = main(["--version"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_returns_zero_and_prints_usage(capsys):
    exit_code = main(["--help"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()


def test_no_args_returns_zero():
    assert main([]) == 0


def test_bogus_flag_returns_two_with_stderr_diagnostic(capsys):
    exit_code = main(["--bogus"])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.err


def test_main_never_raises_systemexit():
    """main() must RETURN an int; core/verdict.py is the sole exit-primitive
    caller under pyforge.marshal (sole-ownership rule)."""
    for argv in (["--version"], ["--help"], [], ["--bogus"]):
        try:
            main(argv)
        except SystemExit:
            pytest.fail(f"main({argv!r}) raised SystemExit instead of returning")


@pytest.mark.parametrize("argv", [["--version"], ["--help"], [], ["--bogus"]])
def test_exit_code_always_in_guarded_domain(argv, capsys):
    assert main(argv) in {0, 1, 2, 3, 4, 130}


def test_keyboard_interrupt_during_parsing_returns_exit_sigint():
    with patch(
        "argparse.ArgumentParser.parse_args", side_effect=KeyboardInterrupt
    ):
        assert main([]) == EXIT_SIGINT


def test_keyboard_interrupt_during_parser_construction_returns_exit_sigint():
    """The interrupt window opens before parse_args: _build_parser() must
    sit inside the same try, or a Ctrl-C during parser construction makes
    main() raise in violation of its returns-an-int-never-raises contract."""
    with patch(
        "pyforge.marshal.cli.main._build_parser", side_effect=KeyboardInterrupt
    ):
        assert main([]) == EXIT_SIGINT


def test_bool_systemexit_code_is_clamped_not_relayed():
    """``SystemExit(True)`` passes an isinstance-int check (bool is an int
    subclass) -- the relay must exclude bools like every other boundary in
    this package, clamping to the usage code instead of returning True."""
    with patch(
        "argparse.ArgumentParser.parse_args", side_effect=SystemExit(True)
    ):
        result = main([])
    assert result == 2
    assert not isinstance(result, bool)


def test_hand_synced_version_literal_matches_pyproject():
    """``__version__`` is hand-duplicated from ``pyproject.toml`` (scaffold
    stage -- see the module docstring); this is the safety net that catches
    the two drifting apart on the next version bump."""
    pyproject = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    assert __version__ == pyproject["project"]["version"]


# --- Story 1.3: the `config` subcommand -------------------------------------


def test_help_lists_config_subcommand(capsys):
    exit_code = main(["--help"])
    assert exit_code == 0
    assert "config" in capsys.readouterr().out


def test_config_defaults_only_exits_zero(capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["config"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "gate_mode" in captured.out
    assert "content_hash" in captured.out


def test_config_prints_all_nine_keys(capsys, monkeypatch):
    """AC: 'every one of the 9 keys prints its effective value and winning
    layer' -- checked exhaustively, not just a couple of spot-checked
    fields."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["config"])
    assert exit_code == 0
    captured = capsys.readouterr()
    for key in (
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
    ):
        assert f"{key}:" in captured.out, f"marshal config did not print {key!r}"
        assert captured.out.count(f"(layer=") >= 1


def test_config_redacts_a_secret_shaped_field(capsys, monkeypatch):
    """None of the 9 real fields are secret-shaped today -- proven via a
    monkeypatched suffix set so `gate_mode` becomes secret-shaped for the
    duration of this test, exercising the REAL `marshal config` render path
    (not just core.policy.redact() called directly, as in
    test_policy.py)."""
    import pyforge.marshal.core.policy as policy_module

    monkeypatch.setattr(policy_module, "SECRET_KEY_SUFFIXES", frozenset({"_MODE"}))
    exit_code = main(["config", "--set", "gate_mode=none"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "***REDACTED***" in captured.out
    assert "'none'" not in captured.out


def test_config_set_bogus_gate_mode_prints_fallback_and_nonzero_exit(capsys):
    exit_code = main(["config", "--set", "gate_mode=bogus"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-003" in captured.out
    # the fallback (Marshal default) value is printed, not the bogus one
    assert "per-story-spec-approval" in captured.out


def test_config_set_scalar_override_applies(capsys):
    exit_code = main(["config", "--set", "gate_mode=none", "--set", "max_dev_attempts=7"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "layer=flag" in captured.out
    assert "'none'" in captured.out


def test_config_project_policy_toml_is_read(tmp_path, capsys):
    toml_path = tmp_path / "project-policy.toml"
    toml_path.write_text('gate_mode = "per-epic"\n', encoding="utf-8")
    exit_code = main(["config", "--project-policy", str(toml_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "'per-epic'" in captured.out
    assert "layer=project" in captured.out


def test_config_project_slug_resolves_from_env(monkeypatch, capsys):
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "widget-co")
    exit_code = main(["config"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "widget-co" in captured.out


def test_config_project_flag_wins_over_env(monkeypatch, capsys):
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-slug")
    exit_code = main(["config", "--project", "flag-slug"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "flag-slug" in captured.out
    assert "env-slug" not in captured.out


def test_config_missing_project_slug_does_not_crash(monkeypatch, capsys):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["config"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "worktree_seed_paths" in captured.out


def test_config_format_json_prints_a_valid_envelope(capsys):
    exit_code = main(["config", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "config"
    assert payload["status"] == "ok"
    assert payload["verdict"] == "clean"
    assert "policy" in payload["data"]
    assert "content_hash" in payload["data"]


def test_config_format_json_with_findings_has_error_status(capsys):
    exit_code = main(["config", "--format", "json", "--set", "gate_mode=bogus"])
    assert exit_code != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["verdict"] == "unevaluable"
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["code"] == "MRS-POLICY-003"


def test_config_materialize_writes_once_and_second_call_is_a_true_noop(tmp_path, capsys):
    target_dir = tmp_path / "materialized"
    exit_code = main(["config", "--materialize", str(target_dir)])
    assert exit_code == 0
    written = list(target_dir.glob("policy-*.json"))
    assert len(written) == 1
    first_mtime = written[0].stat().st_mtime_ns
    first_content = written[0].read_bytes()

    capsys.readouterr()
    exit_code_again = main(["config", "--materialize", str(target_dir)])
    assert exit_code_again == 0
    written_again = list(target_dir.glob("policy-*.json"))
    assert len(written_again) == 1
    assert written_again[0].stat().st_mtime_ns == first_mtime
    assert written_again[0].read_bytes() == first_content


def test_materialize_function_returns_same_path_and_is_a_true_noop(tmp_path):
    """Direct unit coverage of ``cli.config.materialize()`` itself (AD-35),
    independent of the CLI dispatch above."""
    from pyforge.marshal.cli.config import materialize
    from pyforge.marshal.core.policy import compose

    effective, _ = compose(project_slug="acme", project={}, flags={})
    first_path = materialize(effective, tmp_path)
    assert first_path == tmp_path / f"policy-{effective.content_hash}.json"
    assert first_path.exists()
    first_mtime = first_path.stat().st_mtime_ns

    second_path = materialize(effective, tmp_path)
    assert second_path == first_path
    assert second_path.stat().st_mtime_ns == first_mtime


def test_config_materialized_file_matches_policy_schema(tmp_path):
    target_dir = tmp_path / "materialized"
    exit_code = main(["config", "--materialize", str(target_dir)])
    assert exit_code == 0
    written = next(target_dir.glob("policy-*.json"))
    document = json.loads(written.read_text(encoding="utf-8"))
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=document, schema=schema)


def test_config_materialize_path_is_content_addressed_by_hash(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    target_dir = tmp_path / "materialized"
    main(["config", "--materialize", str(target_dir)])
    written = next(target_dir.glob("policy-*.json"))
    document = json.loads(written.read_text(encoding="utf-8"))
    # the filename embeds the same content_hash compose() would compute
    from pyforge.marshal.core.policy import compose

    effective, _ = compose(project_slug="", project={}, flags={})
    assert written.name == f"policy-{effective.content_hash}.json"
    assert document["gate_mode"]["value"] == effective.seed_view()["gate_mode"].value


# --- review-pass regressions (2026-07-30) ------------------------------------


def test_config_explicit_empty_project_flag_wins_over_env(monkeypatch, capsys):
    """An explicit `--project ""` must win over BMAD_ACTIVE_PROJECT, not be
    treated as 'omitted' (a Python-truthiness footgun: `"" or env` silently
    falls through to the env var)."""
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-slug")
    exit_code = main(["config", "--project", ""])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "env-slug" not in captured.out


def test_config_missing_project_policy_file_reports_finding_not_crash(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.toml"
    exit_code = main(["config", "--project-policy", str(missing)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-004" in captured.out
    # still prints the (default) effective policy alongside the finding
    assert "gate_mode" in captured.out


def test_config_malformed_project_policy_toml_reports_finding_not_crash(tmp_path, capsys):
    bad_toml = tmp_path / "project-policy.toml"
    bad_toml.write_text("this is not [ valid toml\n", encoding="utf-8")
    exit_code = main(["config", "--project-policy", str(bad_toml)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-004" in captured.out


def test_config_materialize_target_collision_with_directory_reports_finding(tmp_path, capsys):
    """A directory occupying the content-addressed path must not read as a
    silent no-write 'success' -- the write-once check distinguishes file
    from non-file."""
    from pyforge.marshal.core.policy import compose

    target_dir = tmp_path / "materialized"
    effective, _ = compose(project_slug="", project={}, flags={})
    target_dir.mkdir(parents=True)
    (target_dir / f"policy-{effective.content_hash}.json").mkdir()

    exit_code = main(["config", "--project", "", "--materialize", str(target_dir)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-004" in captured.out


def test_materialize_raises_policy_io_error_on_unwritable_target(tmp_path):
    """Direct unit coverage of materialize()'s own exception wrapping,
    independent of the CLI dispatch above."""
    from pyforge.marshal.cli.config import PolicyIOError, materialize
    from pyforge.marshal.core.policy import compose

    blocked = tmp_path / "not-a-directory"
    blocked.write_text("occupied", encoding="utf-8")
    effective, _ = compose(project_slug="acme", project={}, flags={})
    with pytest.raises(PolicyIOError):
        materialize(effective, blocked / "subdir")


def test_config_materialize_failure_preserves_a_successful_project_layer(tmp_path, capsys):
    """A LATER materialize() failure must not discard an already-successful
    compose() and silently swap the operator's real project-policy layer
    for Marshal's bare defaults -- only a --project-policy READ failure
    earns that fallback."""
    toml_path = tmp_path / "project-policy.toml"
    toml_path.write_text('gate_mode = "per-epic"\n', encoding="utf-8")

    from pyforge.marshal.core.policy import compose

    # Must match exactly what run_config() will compose below (same slug,
    # same project layer) so the collision lands on the SAME content hash.
    effective, _ = compose(
        project_slug="", project={"gate_mode": "per-epic"}, flags={}
    )
    target_dir = tmp_path / "materialized"
    target_dir.mkdir(parents=True)
    (target_dir / f"policy-{effective.content_hash}.json").mkdir()  # forces a collision

    exit_code = main(
        [
            "config",
            "--project",
            "",
            "--project-policy",
            str(toml_path),
            "--materialize",
            str(target_dir),
        ]
    )
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-004" in captured.out
    # the real project-layer value survives the materialize() failure
    assert "'per-epic'" in captured.out
    assert "layer=project" in captured.out


def test_config_set_without_equals_is_a_usage_error(capsys):
    """A malformed `--set` entry (no `=`) must be a clean usage error, not
    silently dropped with zero operator feedback."""
    exit_code = main(["config", "--set", "gate_mode"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert "gate_mode" in captured.err or "gate_mode" in captured.out
