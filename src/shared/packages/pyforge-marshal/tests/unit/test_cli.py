"""Unit tests for ``pyforge.marshal.cli.main`` (Story 1.1 stub;
``--version``/``--help`` with no subcommand) and ``pyforge.marshal.cli.config``
(Story 1.3's first real subcommand, ``marshal config``). ``main`` always
returns an int and never raises ``SystemExit`` itself.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
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


@pytest.fixture(autouse=True)
def _isolate_active_project_env(monkeypatch):
    """`marshal config` deliberately reads BMAD_ACTIVE_PROJECT (AD-2's one
    sanctioned env var) -- and this repo's own agent conventions EXPORT that
    var per invocation, so any test that doesn't pin the slug inherits
    whatever the invoking shell had (a malformed value flips exit-0
    assertions via MRS-POLICY-006). Every test starts env-clean; the tests
    that exercise the env-var path set it explicitly via monkeypatch."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


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


def test_no_args_returns_zero_and_prints_usage(capsys):
    """Story 1.1's bare-invocation exit code (0) is preserved, but with real
    subcommands present the invocation must not be SILENT -- a pipeline that
    lost its argument array would otherwise read as success with no trace."""
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "usage" in (captured.out + captured.err).lower()


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


# --- Story 1.9: --version's harness-version reporting ------------------------


class _FakeHarnessVersion:
    """A minimal stand-in for ``BmadLoopHarness``, driving only the one
    method ``_version_text()`` calls -- mirrors this file's existing
    ``fake_add``/``monkeypatch`` idiom used for the ``config``/``init``
    subcommand wiring tests below."""

    def __init__(self, version: str | None) -> None:
        self._version = version

    def harness_version(self) -> str | None:
        return self._version


def _patch_harness_version(monkeypatch, version: str | None) -> None:
    from pyforge.marshal.cli import main as main_module

    # main.py's --version handling constructs BmadLoopHarness() via the
    # module-level name (the same DI idiom cli/init.py uses for its own
    # default-port construction) -- monkeypatching THAT attribute is the
    # pragmatic seam, since there is no subcommand-handler frame to inject
    # a fake harness through here.
    monkeypatch.setattr(main_module, "BmadLoopHarness", lambda: _FakeHarnessVersion(version))


@pytest.fixture(autouse=True)
def _default_fake_harness(monkeypatch):
    """Every ``--version`` invocation in this file resolves the harness
    through a fake by default: ``_version_text()`` otherwise shells out to
    the REAL ``bmad-loop --version`` (up to its 5s timeout), which belongs
    in the slow tier per this package's own marker convention ("dominated
    by real git/subprocess calls"), and makes assertions PATH-dependent (an
    ambient out-of-range bmad-loop would add WARNING lines the tests never
    asked for). Tests that need a specific version override via
    ``_patch_harness_version`` -- their later ``setattr`` wins."""
    _patch_harness_version(monkeypatch, "0.9.3")


def test_version_harness_in_range_prints_both_versions_no_warning(monkeypatch, capsys):
    _patch_harness_version(monkeypatch, "0.9.3")
    exit_code = main(["--version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "bmad-loop 0.9.3" in out
    # pixi.toml's pyforge-marshal-smoke greps `^bmad-loop [0-9]` out of this
    # exact output for its harness-resolvable proof (FR-56) -- pin the
    # line-anchored shape, not just the substring, so a reformat cannot
    # silently break that cross-artifact contract in a different tool on a
    # different machine.
    assert re.search(r"^bmad-loop 0\.9\.3$", out, re.MULTILINE)
    assert "WARNING" not in out


def test_version_harness_same_major_out_of_range_shows_warning(monkeypatch, capsys):
    _patch_harness_version(monkeypatch, "0.10.2")
    exit_code = main(["--version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "bmad-loop 0.10.2" in out
    assert "WARNING" in out
    assert ">=0.9.0,<0.10" in out


def test_version_harness_major_mismatch_shows_warning(monkeypatch, capsys):
    _patch_harness_version(monkeypatch, "2.0.0")
    exit_code = main(["--version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "bmad-loop 2.0.0" in out
    assert "WARNING" in out


def test_version_harness_unparseable_shows_could_not_be_parsed_warning(monkeypatch, capsys):
    """Review finding: an unparseable-but-non-None version (e.g. "dev") is
    NOT "outside the supported range" -- it isn't a version at all. The
    warning must name that distinctly, not reuse the numerically-out-of-range
    wording ``test_version_harness_same_major_out_of_range_shows_warning``
    covers."""
    _patch_harness_version(monkeypatch, "dev")
    exit_code = main(["--version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "bmad-loop dev" in out
    assert "could not be parsed" in out
    assert "outside the supported range" not in out


def test_version_harness_absent_shows_not_determined(monkeypatch, capsys):
    _patch_harness_version(monkeypatch, None)
    exit_code = main(["--version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "not determined" in out
    assert "WARNING" in out


def test_version_wins_over_a_subcommand_missing_its_required_argument(capsys):
    """Review-caught regression: a first pass made ``--version`` a plain
    ``store_true`` flag checked only after ``parse_args`` fully succeeded,
    so ``marshal --version init`` (missing ``init``'s required ``slug``)
    started exiting 2 with a usage error instead of printing the version --
    breaking the "``--version``/``--help`` always win" convention every
    other argparse-based CLI in this repo follows. ``_VersionAction`` fires
    during parsing, before argparse ever validates ``init``'s required
    ``slug``, restoring that property."""
    exit_code = main(["--version", "init"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def test_version_wins_over_an_unrecognized_trailing_flag(capsys):
    exit_code = main(["--version", "--bogus"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert __version__ in out


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


def test_config_prints_all_twenty_keys(capsys, monkeypatch):
    """AC: 'every one of the (now 21, Story 4.5's `landing_resync_commands`
    joining Story 4.4's `landing_base_branch` and Story 4.7's 4 landing
    keys) keys prints its effective value and winning layer' -- checked
    exhaustively, not just a couple of spot-checked fields. The layer half
    is counted, not merely detected: exactly one `(layer=...)` suffix per
    key line, so a regression that drops the suffix from all but one line
    cannot ship green."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["config"])
    assert exit_code == 0
    captured = capsys.readouterr()
    for key in (
        "verify_commands",
        "worktree_seed_paths",
        "merge_subject_template",
        "model_tier_map",
        "epic_surfaces",
        "landing_rules",
        "landing_merge_strategy",
        "landing_branch_retirement",
        "landing_resync",
        "landing_base_branch",
        "landing_resync_commands",
        "gate_mode",
        "frozen_surfaces",
        "max_dev_attempts",
        "max_review_cycles",
        "max_followup_reviews",
        "idle_threshold_minutes",
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
    ):
        assert f"{key}:" in captured.out, f"marshal config did not print {key!r}"
    assert captured.out.count("(layer=") == 21


def test_config_redacts_a_secret_shaped_field(capsys, monkeypatch):
    """None of the 14 real fields are secret-shaped today -- proven via a
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


def test_config_missing_project_slug_reports_warn_finding_still_exits_zero(monkeypatch, capsys):
    """Spec: 'missing -> a registered finding, still prints defaults' AND
    '`marshal config` exits 0 with defaults only' -- reconciled by
    MRS-POLICY-005 classifying Verdict.WARN (exit 0). The project-derived
    seed path is OMITTED, never generated as a `projects//` garbage path."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["config"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "worktree_seed_paths" in captured.out
    assert "MRS-POLICY-005" in captured.out
    assert "_bmad-output/projects//" not in captured.out
    assert "_bmad/custom/.active-project" in captured.out


def test_config_malformed_project_slug_reports_finding_and_nonzero_exit(capsys):
    """A slug that cannot be one safe path segment (here a traversal shape)
    must be reported (MRS-POLICY-006, unevaluable -> exit 1) and the
    project-derived seed path omitted -- never silently folded into a
    traversal-shaped `_bmad-output/projects/../...` path."""
    exit_code = main(["config", "--project", "../evil"])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-006" in captured.out
    assert "_bmad-output/projects/../evil" not in captured.out


def test_config_format_json_prints_a_valid_envelope(capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["config", "--project", "acme", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "config"
    assert payload["status"] == "ok"
    assert payload["verdict"] == "clean"
    assert "policy" in payload["data"]
    assert "content_hash" in payload["data"]


def test_config_format_json_with_findings_has_error_status(capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(
        ["config", "--project", "acme", "--format", "json", "--set", "gate_mode=bogus"]
    )
    assert exit_code != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["verdict"] == "unevaluable"
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["code"] == "MRS-POLICY-003"


def test_config_format_json_renders_a_nonempty_landing_rule(tmp_path, capsys, monkeypatch):
    """Review finding P5: no existing test exercised `--format json` with a
    NON-EMPTY `landing_rules` -- the prior test changes only bumped
    generic key-count assertions against the empty-tuple default, so
    `_json_safe`'s `LandingRule` branch never actually executed in the
    test suite. Composes a real project-policy layer with one rule
    (including the new `trigger_mode` field) and asserts the JSON output
    renders it correctly."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    toml_path = tmp_path / "project-policy.toml"
    toml_path.write_text(
        """
        [[landing_rules]]
        name = "environment-yaml-sync"
        trigger_path_glob = "pixi.toml"
        trigger_mode = "include"
        required_check = "environment-yaml-sync"
        ungated = true
        """,
        encoding="utf-8",
    )
    exit_code = main(
        ["config", "--project-policy", str(toml_path), "--format", "json"]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    rules = payload["data"]["policy"]["landing_rules"]["value"]
    assert rules == [
        {
            "name": "environment-yaml-sync",
            "trigger_path_glob": "pixi.toml",
            "trigger_mode": "include",
            "label": None,
            "required_check": "environment-yaml-sync",
            "ungated": True,
        }
    ]
    assert payload["data"]["policy"]["landing_rules"]["layer"] == "project"


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


# --- follow-up review regressions (2026-07-30, second pass) -------------------


def test_config_non_utf8_project_policy_reports_finding_not_crash(tmp_path, capsys):
    """UnicodeDecodeError is a ValueError SIBLING of TOMLDecodeError --
    tomllib decodes the bytes itself and lets it propagate, so a UTF-16 or
    binary --project-policy file must land in the same MRS-POLICY-004 path
    as every other read failure, not crash straight through main()."""
    bad_bytes = tmp_path / "project-policy.toml"
    bad_bytes.write_bytes(b"\xff\xfe not utf-8 \x00")
    exit_code = main(["config", "--project", "acme", "--project-policy", str(bad_bytes)])
    assert exit_code != 0
    captured = capsys.readouterr()
    assert "MRS-POLICY-004" in captured.out


def test_field_order_matches_the_closed_policy_vocabulary():
    """The 20-key vocabulary is declared in three places (_FIELD_ORDER, the
    _STATIC_KEYS/_SEED_KEYS sets, schemas/policy.json). This is the derive-
    don't-declare tie: adding a 20th key to core/policy.py without updating
    the render order or the schema fails HERE, instead of silently vanishing
    from `marshal config` output and the materialized artifact while still
    being hashed."""
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.core import policy

    assert set(config_module._FIELD_ORDER) == set(policy._ALL_KEYS)
    assert len(config_module._FIELD_ORDER) == len(policy._ALL_KEYS)
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert set(schema["properties"].keys()) == set(policy._ALL_KEYS)
    assert set(schema["required"]) == set(policy._ALL_KEYS)


def test_config_json_envelope_validates_against_envelope_schema(tmp_path, capsys, monkeypatch):
    """The envelope output is the machine contract every consumer parses --
    validate it against schemas/envelope.v1.json (the materialized FILE was
    already schema-validated; the envelope was not), and pin the
    success-path data.materialized_path, asserted nowhere else."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    target_dir = tmp_path / "materialized"
    exit_code = main(
        ["config", "--project", "acme", "--format", "json", "--materialize", str(target_dir)]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    envelope_schema = json.loads(
        (_SCHEMA_PATH.parent / "envelope.v1.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=payload, schema=envelope_schema)
    written = next(target_dir.glob("policy-*.json"))
    assert payload["data"]["materialized_path"] == str(written)


def test_materialize_refuses_a_tampered_existing_artifact(tmp_path):
    """Write-once must not bless foreign bytes: content-addressing only
    guarantees identical content for files written by a cooperating atomic
    writer, so a hand-edited/truncated file squatting on the
    content-addressed name is a PolicyIOError, not a silent 'success'."""
    from pyforge.marshal.cli.config import PolicyIOError, materialize
    from pyforge.marshal.core.policy import compose

    effective, _ = compose(project_slug="acme", project={}, flags={})
    target_path = tmp_path / f"policy-{effective.content_hash}.json"
    target_path.write_bytes(b'{"tampered": true}\n')
    with pytest.raises(PolicyIOError):
        materialize(effective, tmp_path)
    # the tampered bytes are refused, never repaired-in-place either
    assert target_path.read_bytes() == b'{"tampered": true}\n'


def test_materialized_artifact_gets_umask_respecting_permissions(tmp_path):
    """The temp file is created via os.open(..., 0o666), so the KERNEL
    applies the process umask exactly like a plain open() would and
    os.replace carries ordinary permissions onto the final artifact --
    never mkstemp's owner-only 0600, and with no process-global
    os.umask(0) probe (which briefly zeroed the umask for every other
    thread on each write)."""
    import os as os_module

    from pyforge.marshal.cli.config import materialize
    from pyforge.marshal.core.policy import compose

    if os_module.name != "posix":
        pytest.skip("POSIX permission-bit semantics required")
    effective, _ = compose(project_slug="acme", project={}, flags={})
    written = materialize(effective, tmp_path)
    current_umask = os_module.umask(0)
    os_module.umask(current_umask)
    assert written.stat().st_mode & 0o777 == 0o666 & ~current_umask


def test_broken_pipe_during_config_output_returns_verdict_exit_code(monkeypatch):
    """`marshal config | head -1` closes stdout early: BrokenPipeError is an
    OSError that main()'s SystemExit/KeyboardInterrupt relay never catches,
    so run_config must suppress it itself and still return its
    verdict-derived exit code -- the compose work already completed; the
    reader hanging up is not a policy failure.

    The failure is injected at the sys.stdout level, NOT by monkeypatching
    builtins.print: with a replaced stdout the suppression guard's
    `sys.stdout is sys.__stdout__` check correctly declines to dup2 -- a
    print-level injection under `pytest -s` (capture disabled, stdout IS the
    real fd 1) would let the guard redirect the whole test session's output
    to devnull."""
    import sys as sys_module

    class _BrokenPipeStdout:
        def write(self, *args, **kwargs):
            raise BrokenPipeError(32, "Broken pipe")

        def flush(self):
            pass

    monkeypatch.setattr(sys_module, "stdout", _BrokenPipeStdout())
    assert main(["config", "--project", "acme"]) == 0


def test_nonpipe_oserror_during_config_output_returns_verdict_exit_code(monkeypatch):
    """A non-EPIPE OSError from the output print (EIO on a vanished pty,
    ENOSPC on a full-disk redirect) must land in the same guarded path --
    returned as the verdict-derived exit code, never an uncaught traceback
    through main()'s relay."""
    import sys as sys_module

    class _EIOStdout:
        def write(self, *args, **kwargs):
            raise OSError(5, "Input/output error")

        def flush(self):
            pass

    monkeypatch.setattr(sys_module, "stdout", _EIOStdout())
    assert main(["config", "--project", "acme"]) == 0


def test_config_materialize_is_skipped_when_composition_carries_error_findings(
    tmp_path, capsys
):
    """--materialize must not persist a durable, content-addressed artifact
    born of an error-class (unevaluable) invocation: the non-zero exit code
    protects only the immediate caller, while a written file would outlive
    it for any consumer globbing the target directory."""
    target_dir = tmp_path / "materialized"
    exit_code = main(
        ["config", "--set", "gate_mode=bogus", "--materialize", str(target_dir)]
    )
    assert exit_code != 0
    # the skip happens before materialize() -- the target dir is never even created
    assert not target_dir.exists()
    captured = capsys.readouterr()
    assert "skipped" in captured.out


# --- follow-up review regressions (2026-07-30, fourth pass) -------------------


@pytest.mark.parametrize(
    "argv",
    [["config", "--project", "acme"], ["--help"], []],
    ids=["config", "help", "bare-usage"],
)
def test_piped_invocation_with_closed_reader_exits_in_domain(argv):
    """The in-process fake-stdout regressions above inject the failure at
    write() time -- a shape that structurally cannot represent BUFFERING.
    In a real console-script invocation with stdout piped, output smaller
    than the block buffer never touches the fd inside run_config's guard;
    the EPIPE surfaced at interpreter-shutdown flush, which CPython
    converts to exit status 120 (outside the frozen domain) with an
    'Exception ignored' traceback on stderr. Spawning the real thing with
    the read end closed is the only test shape that catches it -- both
    prior passes' in-process guards shipped green while `marshal config |
    head -1` exited 120."""
    import os as os_module
    import subprocess
    import sys as sys_module

    env = {
        k: v
        for k, v in os_module.environ.items()
        if k not in ("PYTHONUNBUFFERED", "BMAD_ACTIVE_PROJECT")
    }
    code = (
        "import sys\n"
        "from pyforge.marshal.cli.main import main\n"
        f"sys.exit(main({argv!r}))\n"
    )
    proc = subprocess.Popen(
        [sys_module.executable, "-c", code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    proc.stdout.close()  # hang up before the child flushes
    stderr = proc.stderr.read()
    proc.stderr.close()
    returncode = proc.wait()
    assert returncode == 0, stderr.decode(errors="replace")
    assert b"Exception ignored" not in stderr


def test_config_set_on_a_list_or_mapping_key_is_a_usage_error(capsys):
    """`--set verify_commands=...` used to flow into compose() as a plain
    string and come back as 'malformed value ... in the flag layer' -- a
    categorically wrong diagnostic (no string value could ever satisfy a
    list/mapping-typed key). The flag boundary now rejects the KEY with a
    usage error naming the actual fix."""
    exit_code = main(["config", "--set", "verify_commands=pytest -q"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert "verify_commands" in captured.err
    assert "--project-policy" in captured.err


def test_config_set_on_idle_threshold_minutes_is_a_usage_error(capsys):
    """Review finding: the `_FIELD_ORDER` comment already stated
    `idle_threshold_minutes` "is deliberately NOT a --set target", but the
    key was in neither `_UNSETTABLE_KEYS` nor `_INT_SET_KEYS` -- so
    `--set idle_threshold_minutes=30` was silently accepted as an
    unconverted raw string and only failed later inside `compose()` as a
    misleading `MRS-POLICY-003` "malformed value" finding. It must now be
    rejected the same clean way the other 4 non-settable keys are: a usage
    error at the flag boundary, never a policy finding at all."""
    exit_code = main(["config", "--set", "idle_threshold_minutes=30"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert "idle_threshold_minutes" in captured.err
    assert "--project-policy" in captured.err
    assert "MRS-POLICY-003" not in captured.err
    # Second review finding: the shared rejection message called every
    # unsettable key "list/mapping-typed", which is true of the other 4 and
    # FALSE of this one -- a plain positive number excluded for an entirely
    # different reason (no AC asks for a CLI override surface for it).
    # Telling an operator a numeric key is list/mapping-typed is a false
    # statement about their own policy vocabulary that sends them looking
    # for a type error which does not exist.
    assert "list/mapping-typed" not in captured.err
    assert "project-policy-only" in captured.err


@pytest.mark.parametrize(
    "key",
    [
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
    ],
)
def test_config_set_on_a_budget_ceiling_is_a_usage_error(capsys, key):
    """Story 3.6's 4 new keys join `idle_threshold_minutes` as
    project-policy-only -- rejected the SAME clean way at the flag
    boundary, never as a `MRS-POLICY-003` "malformed value" finding."""
    exit_code = main(["config", "--set", f"{key}=30"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert key in captured.err
    assert "--project-policy" in captured.err
    assert "MRS-POLICY-003" not in captured.err
    assert "list/mapping-typed" not in captured.err
    assert "project-policy-only" in captured.err


def test_handler_returning_none_is_clamped_to_usage(monkeypatch):
    """A future handler that falls off the end returns None; the console
    script's sys.exit(None) would exit 0, masking the wiring bug as success.
    The dispatch clamps handler returns to the guarded domain exactly like
    the SystemExit relay."""
    from pyforge.marshal.cli import main as main_module

    def fake_add(subparsers):
        parser = subparsers.add_parser("config")
        parser.set_defaults(handler=lambda args: None)

    monkeypatch.setattr(main_module.config_cli, "add_config_subparser", fake_add)
    assert main_module.main(["config"]) == EXIT_USAGE


def test_handler_returning_out_of_domain_int_is_clamped_to_usage(monkeypatch):
    from pyforge.marshal.cli import main as main_module

    def fake_add(subparsers):
        parser = subparsers.add_parser("config")
        parser.set_defaults(handler=lambda args: 77)

    monkeypatch.setattr(main_module.config_cli, "add_config_subparser", fake_add)
    assert main_module.main(["config"]) == EXIT_USAGE


# --- Story 1.4: the `init` subcommand's wiring into main.py -----------------


def test_help_lists_init_subcommand(capsys):
    exit_code = main(["--help"])
    assert exit_code == 0
    assert "init" in capsys.readouterr().out


def test_init_missing_required_slug_is_a_usage_error(capsys):
    exit_code = main(["init"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    # Review finding: asserting `captured.err` alone is non-vacuous but too
    # weak -- it would pass for ANY argparse usage error, not specifically
    # the missing `slug` positional. Name the actual missing argument.
    assert "slug" in captured.err


def test_init_dispatches_to_run_init_with_parsed_args(monkeypatch):
    """A lightweight wiring proof (mirrors this file's existing
    fake_add/monkeypatch pattern): main() parses `init <slug>` and calls
    cli.init.run_init with a Namespace carrying that slug, relaying
    whatever int it returns -- the real orchestration is covered by
    tests/unit/test_init.py and the real end-to-end
    tests/integration/test_init_worktree.py."""
    from pyforge.marshal.cli import init as init_module

    received: list[str] = []

    def fake_run_init(args, **kwargs):
        received.append(args.slug)
        return 0

    monkeypatch.setattr(init_module, "run_init", fake_run_init)
    # main.py's _build_parser() binds cli.init.run_init at subparser-registration
    # time (`set_defaults(handler=run_init)` inside add_init_subparser), so the
    # monkeypatch above (applied to the module attribute) must be in place
    # BEFORE main() builds a fresh parser -- which it does on every call.
    assert main(["init", "acme"]) == 0
    assert received == ["acme"]


# --- Story 2.1: the `gate evaluate` subcommand -------------------------------
#
# These exercise `main()` end-to-end against REAL, trivial, fast verify
# commands (`true`/`false`/a nonexistent binary/a malformed shlex string),
# matching this package's own "real I/O, not heavy mocking" convention (see
# `test_vcs_git.py`) -- `run_evaluate`'s DI seam (`process: ProcessPort |
# None`) exists for callers that need a fake, but the CLI-wiring layer here
# proves the real PosixProcess integration. The pure per-command
# classification is separately, exhaustively covered by `test_gate.py` with
# synthetic ProcessResults, and PosixProcess itself by `test_process_posix.py`.
#
# Every policy fixture below goes through `_conventional_policy`, because the
# CONVENTIONAL path is the only policy source `gate evaluate` reads: unlike
# `marshal config` it deliberately offers no `--project-policy` override (a
# command that RUNS what it reads must not accept an arbitrary path -- see
# `cli/gate.py`'s module docstring). That makes these tests exercise the real
# production resolution rather than a test-only flag.


def _conventional_policy(tmp_path, monkeypatch, slug, body):
    """Plant a project policy at the only source `gate evaluate` reads, and
    point the repo root at `tmp_path`.

    BOTH `repo_root` bindings are patched: `cli/gate.py` imports the name
    directly (`from .config import ..., repo_root`), a separate binding from
    `config_module.repo_root`, and it is also what the spawned commands get
    as their `cwd` -- so patching only one leaves execution pointed at the
    real checkout.
    """
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "repo_root", lambda: tmp_path)
    policy_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_path = policy_dir / "marshal-policy.toml"
    policy_path.write_text(body, encoding="utf-8")
    return policy_path


def test_help_lists_gate_subcommand(capsys):
    """Asserts the SUBCOMMAND-LIST token, not a bare "gate" substring.
    Review finding: `preflight`'s own help line ends "... and gate on
    first-run acknowledgement", so a substring check stayed green with
    `add_gate_subparser` deleted from `cli/main.py` entirely."""
    exit_code = main(["--help"])
    assert exit_code == 0
    assert (
        "{config,init,homes,preflight,teardown,gate,factory,deploy,land,retire,status,check,adapters,upstream}"
        in capsys.readouterr().out
    )


def test_retire_subcommand_is_wired(tmp_path, capsys, monkeypatch):
    """Smoke test (Story 4.10): ``marshal retire`` dispatches to
    ``cli/retire.py::run_retire`` and prints a real envelope -- mirrors this
    module's own ``gate``/``land`` wiring precedent. Scoped to a nonexistent
    slug so it never touches this dev repo's own real fleet state."""
    from pyforge.marshal.cli import retire as retire_module

    monkeypatch.setattr(retire_module, "repo_root", lambda: tmp_path)

    exit_code = main(["retire", "--project", "no-such-project-xyz", "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "retire"
    assert payload["data"]["proposals"] == []


def test_status_subcommand_is_wired(capsys):
    """Smoke test (Story 5.1): ``marshal status`` dispatches to
    ``cli/status.py::run_status`` and prints a real envelope -- mirrors this
    module's own ``retire`` wiring precedent. Scoped to a nonexistent slug
    so it never touches this dev repo's own real fleet state."""
    exit_code = main(["status", "--project", "no-such-project-xyz", "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "status"
    assert payload["data"]["homes"] == []


def test_check_help_works(capsys):
    """Smoke test (Story 5.6): ``marshal check --help`` exits clean and
    documents the subcommand -- mirrors this module's own ``--help``
    conventions for every other subcommand."""
    exit_code = main(["check", "--help"])
    assert exit_code == 0
    assert "--scope" in capsys.readouterr().out


def test_check_subcommand_is_wired(capsys, monkeypatch):
    """Smoke test (Story 5.6): ``marshal check`` dispatches to
    ``cli/check.py::run_check`` and prints a real envelope -- mirrors this
    module's own ``retire``/``status`` wiring precedent. The underlying
    ``scripts/detectors.py`` subprocess call is stubbed via a fake
    ``PosixProcess`` so this test never depends on this dev repo's own real
    detector state, and never crashes for a normal invocation (confirming
    ``cli/main.py``'s new ``context=`` dispatch plumbing doesn't raise a
    TypeError for the one handler that DOES accept it)."""
    import json as json_module

    from pyforge.marshal.cli import check as check_module
    from pyforge.marshal.ports.process import ProcessResult

    class _FakeProcess:
        def run(self, argv, *, cwd, timeout_s=None):
            return ProcessResult(
                returncode=0,
                stdout=json_module.dumps({"registry": [], "results": []}),
                stderr="",
            )

    monkeypatch.setattr(check_module, "PosixProcess", _FakeProcess)

    exit_code = main(["check", "--scope", "repo", "--format", "json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "check"
    assert payload["data"]["results"] == []


def test_gate_missing_evaluate_action_is_a_usage_error(capsys):
    exit_code = main(["gate"])
    assert exit_code == EXIT_USAGE
    captured = capsys.readouterr()
    assert captured.err


def test_gate_evaluate_all_commands_pass_exits_clean(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    # --project supplied so the composition carries no MRS-POLICY-005
    # "no active project" warn finding alongside the command results --
    # this test's own concern is a pure clean/gate-only verdict.
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "clean"
    assert payload["status"] == "ok"
    assert payload["data"]["commands"] == [
        {"command": "true", "resolvable": True, "returncode": 0, "stdout": "", "stderr": ""}
    ]


def test_gate_evaluate_one_command_fails_reports_gate_failed(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true", "false"]\n'
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "gate-failed"
    assert payload["status"] == "error"
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-001" in codes
    # the failing command's own report still names it and its real exit code
    failing = next(c for c in payload["data"]["commands"] if c["command"] == "false")
    assert failing["returncode"] == 1
    assert failing["resolvable"] is True


def test_gate_evaluate_unresolvable_command_reports_unevaluable(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'verify_commands = ["definitely-not-a-real-binary-xyz"]\n',
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "unevaluable"
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-002" in codes
    assert payload["data"]["commands"] == [
        {
            "command": "definitely-not-a-real-binary-xyz",
            "resolvable": False,
            "returncode": None,
        }
    ]


def test_gate_evaluate_malformed_command_reports_unevaluable(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["\'unterminated"]\n'
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "unevaluable"
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-003" in codes
    assert payload["data"]["commands"] == [
        {"command": "'unterminated", "resolvable": False, "returncode": None}
    ]


def test_gate_evaluate_zero_commands_configured_reports_warn(capsys, monkeypatch):
    """Bare defaults (no --project-policy, no active project) compose
    verify_commands=() -- MRS-GATE-004, never a silent 'clean'."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["gate", "evaluate", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "warn"
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-004" in codes


def test_gate_evaluate_missing_project_and_empty_allowlist_surface_both_findings(
    capsys, monkeypatch
):
    """I/O matrix: '--project/env both omitted' -> MRS-POLICY-005 (no active
    project) AND MRS-GATE-004 (empty allowlist) surface together."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["gate", "evaluate", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    codes = {finding["code"] for finding in payload["findings"]}
    assert {"MRS-POLICY-005", "MRS-GATE-004"} <= codes


def test_gate_evaluate_run_flag_reports_mrs_gate_005_and_skips_commands(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    # Hermetic: --run now resolves a real loop home via _home_path (Story
    # 2.3) -- pin BMAD_LOOP_HOME_ROOT under tmp_path so this test never
    # depends on (or collides with) whatever a real operator's own
    # ~/.bmad-loops happens to contain.
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    # A command that would otherwise fail -- proves --run truly skips running
    # any configured command rather than merely also reporting MRS-GATE-005.
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["false"]\n')
    exit_code = main(
        ["gate", "evaluate", "--project", "acme", "--run", "run-42", "--format", "json"]
    )
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "unevaluable"
    codes = [finding["code"] for finding in payload["findings"]]
    assert codes == ["MRS-GATE-005"]
    assert "run-42" in payload["findings"][0]["message"]
    assert payload["data"]["commands"] == []
    assert payload["data"]["scope"] != "policy-seed-only"
    # AD-26: the --run branch stays a refusal -- a run-scoped answer must
    # come from the (not-yet-existing) journal fold, never from policy
    # directly, so no gate_mode/autonomy_label key ever appears here.
    assert "gate_mode" not in payload["data"]
    assert "autonomy_label" not in payload["data"]


def test_gate_evaluate_no_run_in_flight_scope_is_policy_seed_only(capsys, monkeypatch):
    """AC: with no --run supplied, data.scope == 'policy-seed-only' plus a
    'mid-run freezes not visible' note (AD-26/F-3)."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["gate", "evaluate", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["scope"] == "policy-seed-only"
    assert "mid-run freezes not visible" in payload["data"]["scope_note"]


def test_gate_evaluate_no_run_reports_gate_mode_autonomy_label(capsys, monkeypatch):
    """FR-24: the already-selected gate mode IS an autonomy declaration --
    every no-`--run` envelope carries `data.gate_mode`/`data.autonomy_label`,
    data (not prose), alongside the existing `scope: policy-seed-only`.
    Marshal's own DEFAULT_POLICY selects `per-story-spec-approval` (L2) when
    no project policy overrides it."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["gate", "evaluate", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["scope"] == "policy-seed-only"
    assert payload["data"]["gate_mode"] == "per-story-spec-approval"
    assert payload["data"]["autonomy_label"] == {
        "level": "L2",
        "name": "Task-Based / Operator",
        "meaning": "Human approves each unit's contract before work proceeds.",
    }


def test_gate_evaluate_no_run_reports_project_overridden_gate_mode_label(
    tmp_path, capsys, monkeypatch
):
    """The label tracks the EFFECTIVE (post-composition) gate mode, not just
    the built-in default -- a project policy selecting `per-epic` (L3)
    surfaces the L3 label, not L2."""
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'gate_mode = "per-epic"\n'
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["gate_mode"] == "per-epic"
    assert payload["data"]["autonomy_label"]["level"] == "L3"
    assert payload["data"]["autonomy_label"]["name"] == "Conditional / Context Gates"


def test_gate_evaluate_no_run_default_text_format_shows_gate_mode_and_label(
    capsys, monkeypatch
):
    """AD-14: `--format text` is a pure projection of the SAME envelope
    `data` `--format json` prints -- review finding, verified live that the
    original diff added `data.gate_mode`/`data.autonomy_label` without
    updating `_render_text`, leaving the DEFAULT (non-JSON) invocation
    silent about the one thing this story exists to surface."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(["gate", "evaluate"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "gate mode: per-story-spec-approval" in out
    assert "L2" in out
    assert "Task-Based / Operator" in out


def test_gate_evaluate_run_flag_default_text_format_omits_gate_mode_line(
    tmp_path, capsys, monkeypatch
):
    """The --run branch carries no gate_mode/autonomy_label key (AD-26), so
    the text projection must not print a `gate mode:` line for it either."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["false"]\n')
    exit_code = main(["gate", "evaluate", "--project", "acme", "--run", "run-42"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "gate mode:" not in out


def test_gate_evaluate_no_run_malformed_gate_mode_falls_back_to_default_label(
    tmp_path, capsys, monkeypatch
):
    """`_valid_gate_mode` already rejects an out-of-vocabulary `gate_mode` at
    composition time (falls through to the next layer), so
    `describe_gate_mode` only ever receives one of the 3 known values via
    this real CLI path -- proven end-to-end here, alongside the existing
    `MRS-POLICY-*` malformed-value finding, rather than merely asserted in
    `describe_gate_mode`'s own unit tests."""
    _conventional_policy(tmp_path, monkeypatch, "acme", 'gate_mode = "bogus"\n')
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    # the malformed value itself is a hard finding (MRS-POLICY-003, matching
    # `test_config_set_bogus_gate_mode_prints_fallback_and_nonzero_exit`'s
    # own precedent) -- this test's own concern is that describe_gate_mode
    # still received a VALID fallback value rather than the bogus one.
    assert exit_code != 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["gate_mode"] == "per-story-spec-approval"
    assert payload["data"]["autonomy_label"]["level"] == "L2"
    codes = [finding["code"] for finding in payload["findings"]]
    assert any(code.startswith("MRS-POLICY-") for code in codes)


def test_gate_evaluate_project_flag_wins_over_env(tmp_path, capsys, monkeypatch):
    """Precedence proven by EXECUTION, not just by the reported slug: both
    slugs have a real conventional policy, with distinct commands whose exit
    codes differ, so the run's verdict alone identifies which one was read."""
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-slug")
    _conventional_policy(tmp_path, monkeypatch, "env-slug", 'verify_commands = ["false"]\n')
    _conventional_policy(tmp_path, monkeypatch, "flag-slug", 'verify_commands = ["true"]\n')
    exit_code = main(["gate", "evaluate", "--project", "flag-slug", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["slug"] == "flag-slug"
    assert payload["data"]["commands"][0]["command"] == "true"


def test_gate_evaluate_only_the_selected_projects_conventional_policy_is_read(
    tmp_path, capsys, monkeypatch
):
    """I/O matrix: 'wrong project never runs' -- reuses cli/config.py's own
    conventional-path resolution, so only the SLUG-matching project's file
    is ever read; a differently-slugged project's own commands never
    execute. Proven constructively: two projects, two DISTINCT verify
    commands, and only the selected slug's command shows up in the report."""
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    _conventional_policy(
        tmp_path, monkeypatch, "other-slug", 'verify_commands = ["false"]\n'
    )

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["commands"] == [
        {"command": "true", "resolvable": True, "returncode": 0, "stdout": "", "stderr": ""}
    ]

    exit_code_other = main(["gate", "evaluate", "--project", "other-slug", "--format", "json"])
    assert exit_code_other == 3
    payload_other = json.loads(capsys.readouterr().out)
    assert payload_other["data"]["commands"][0]["command"] == "false"


def test_gate_evaluate_traversal_shaped_slug_never_reads_or_runs_a_file(
    tmp_path, capsys, monkeypatch
):
    """Review finding (security): `conventional_project_policy_path` builds
    its path by naive string interpolation with no traversal check, so an
    unvalidated `--project '../../../../whatever'` could resolve OUTSIDE
    `_bmad-output/projects/` -- and unlike `marshal config` (which only
    PRINTS a mis-resolved policy), `gate evaluate` would EXECUTE whatever
    verify_commands that file declares. Proven constructively: a real file
    sits at the traversal target with a command that would leave a marker
    if run; the malformed slug must be rejected (MRS-POLICY-006,
    unevaluable) before that file is ever read, so the marker never appears."""
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path / "repo")
    monkeypatch.setattr(gate_module, "repo_root", lambda: tmp_path / "repo")
    (tmp_path / "repo" / "_bmad-output" / "projects").mkdir(parents=True)
    marker = tmp_path / "marker-outside-projects"
    evil_dir = tmp_path / "outside" / "planning-artifacts"
    evil_dir.mkdir(parents=True)
    (evil_dir / "marshal-policy.toml").write_text(
        f'verify_commands = ["touch {marker}"]\n', encoding="utf-8"
    )

    exit_code = main(
        ["gate", "evaluate", "--project", "../../outside", "--format", "json"]
    )
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-POLICY-006" in codes
    assert payload["data"]["commands"] == []
    assert not marker.exists()


def test_gate_evaluate_rejects_an_arbitrary_project_policy_path(tmp_path, capsys, monkeypatch):
    """Review finding (security): `gate evaluate` briefly carried `marshal
    config`'s `--project-policy PATH` flag. On `config` that flag only PRINTS
    the policy it reads; here it EXECUTED the `verify_commands` of any file on
    disk -- verified live, a policy in /tmp ran an arbitrary command and the
    envelope reported `verdict: clean`, exit 0, under `"slug":
    "pyforge-marshal"`, asserting a project scope the run never had. That is
    precisely the ad-hoc command channel AD-17 forbids and the story spec's
    own **Never** clause rules out ("there is deliberately no such flag"), so
    the flag is gone: argparse must reject it, and the file must not run."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", "verify_commands = []\n")
    marker = tmp_path / "foreign-policy-was-executed"
    foreign = tmp_path / "foreign.toml"
    foreign.write_text(f'verify_commands = ["touch {marker}"]\n', encoding="utf-8")

    exit_code = main(
        ["gate", "evaluate", "--project", "acme", "--project-policy", str(foreign)]
    )

    assert exit_code == EXIT_USAGE
    assert "--project-policy" in capsys.readouterr().err
    assert not marker.exists()


def test_run_evaluate_uses_the_injected_process_port(tmp_path, capsys, monkeypatch):
    """Review finding: the `process: ProcessPort | None` DI seam the spec
    mandates ("injected the same DI way cli/init.py injects VcsPort") was
    entirely unexercised -- `main()` dispatches `handler(args)`, so no
    production path can reach the parameter, and no test passed it either.
    Every gate test would have stayed green with the parameter deleted and
    `PosixProcess()` hardcoded.

    The configured command is a binary that does NOT exist: a real
    PosixProcess would raise ProcessError -> MRS-GATE-002 -> exit 1, so a
    clean exit 0 carrying the fake's own stdout can only mean the injected
    port was the one actually used."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.ports.process import ProcessResult

    calls: list[tuple[list[str], object]] = []

    class _RecordingProcess:
        def run(self, argv, *, cwd, timeout_s=None):
            # `cwd` is RECORDED, not discarded (review finding): no test
            # asserted the working directory `cli/gate.py` spawns commands
            # in, so a regression to `Path.cwd()` -- which would gate a
            # different tree than the one `data["root"]` reports -- shipped
            # green. The write-boundary test cannot cover it either: it runs
            # only `true`/`false`, which write nothing anywhere.
            calls.append((list(argv), cwd))
            return ProcessResult(returncode=0, stdout="injected-stdout", stderr="")

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'verify_commands = ["definitely-not-a-real-binary-xyz"]\n',
    )
    args = argparse.Namespace(
        project="acme", run_id=None, scope_check=False, story=None, format="json"
    )

    exit_code = gate_module.run_evaluate(args, process=_RecordingProcess())

    assert exit_code == 0
    assert [argv for argv, _ in calls] == [["definitely-not-a-real-binary-xyz"]]
    # The spawn `cwd` is the tree the envelope says it evaluated -- not the
    # process's own working directory.
    assert [str(cwd) for _, cwd in calls] == [str(tmp_path)]
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "clean"
    assert payload["data"]["commands"][0]["stdout"] == "injected-stdout"
    assert payload["data"]["root"] == str(tmp_path)


def test_gate_evaluate_text_format_survives_output_stdout_cannot_encode(
    tmp_path, capsys, monkeypatch
):
    """Review finding: this is the first command to print ARBITRARY child
    output, and the adapter decodes it with errors="replace", so one
    undecodable byte puts U+FFFD into the text render. On a stdout whose
    encoding cannot represent it, `print` raises UnicodeEncodeError -- a
    ValueError, which `main()`'s SystemExit/KeyboardInterrupt relay does NOT
    catch, so the run died on a traceback and returned 1 for a gate that had
    really failed with 3. pytest's own capsys is a UTF-8 buffer, so no
    existing test could reach this; an ascii TextIOWrapper stands in."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.ports.process import ProcessResult

    class _NonAsciiProcess:
        def run(self, argv, *, cwd, timeout_s=None):
            # U+FFFD is exactly what the adapter's errors="replace" produces
            # from an undecodable byte -- see test_process_posix.py's
            # test_run_replaces_undecodable_output.
            return ProcessResult(returncode=1, stdout="caf\ufffd", stderr="")

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    buffer = io.BytesIO()
    monkeypatch.setattr(
        sys, "stdout", io.TextIOWrapper(buffer, encoding="ascii", errors="strict")
    )
    args = argparse.Namespace(
        project="acme", run_id=None, scope_check=False, story=None, format="text"
    )

    exit_code = gate_module.run_evaluate(args, process=_NonAsciiProcess())
    sys.stdout.flush()

    # The verdict-derived exit code survives, and the output is emitted
    # backslash-escaped rather than lost to a traceback.
    assert exit_code == 3
    written = buffer.getvalue()
    assert b"caf" in written
    assert rb"\ufffd" in written


def test_gate_evaluate_unreadable_policy_does_not_also_claim_it_is_unconfigured(
    tmp_path, capsys, monkeypatch
):
    """Review finding: MRS-GATE-004 asserts the allowlist is UNCONFIGURED.
    When the conventional policy file exists but cannot be parsed, the
    operator DID configure commands and Marshal could not read them --
    emitting "no verify commands configured" alongside MRS-POLICY-004
    misdirects triage toward "add a verify command" when the real fix is the
    syntax error. Verified live before the fix: both codes side by side.

    The run must still never be green: MRS-POLICY-004 keeps it unevaluable."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", "verify_commands = [ this is not toml\n"
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "unevaluable"
    codes = {finding["code"] for finding in payload["findings"]}
    assert "MRS-POLICY-004" in codes
    assert "MRS-GATE-004" not in codes


def test_gate_evaluate_unconfigured_project_slug_uses_bare_defaults(capsys, monkeypatch):
    """A project slug with no conventional policy file composes against
    Marshal's bare defaults (verify_commands=()) -- it can never accidentally
    pick up some OTHER project's commands."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    exit_code = main(
        ["gate", "evaluate", "--project", "definitely-not-a-real-marshal-project", "--format", "json"]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["commands"] == []
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-004" in codes


def test_gate_evaluate_text_format_is_a_projection_of_the_same_data(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true", "false"]\n'
    )
    exit_code = main(["gate", "evaluate", "--project", "acme"])
    assert exit_code == 3
    out = capsys.readouterr().out
    assert "scope: policy-seed-only" in out
    # Quoted: every command string is rendered with `!r` so a newline inside
    # one cannot forge report structure -- see
    # test_gate_evaluate_text_format_cannot_be_forged_by_a_command_string.
    assert "'true': returncode=0" in out
    assert "'false': returncode=1" in out
    assert "MRS-GATE-001" in out


def test_gate_evaluate_text_format_includes_captured_output(tmp_path, capsys, monkeypatch):
    """Review finding: `--format text` is the DEFAULT, and the AC's wording is
    "reported per command WITH captured output" -- but every other text-format
    test uses `true`/`false`, whose stdout and stderr are both empty, so the
    two render branches that carry captured output were never executed by any
    test. A regression dropping them would have shipped green."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path,
        monkeypatch,
        "acme",
        """verify_commands = ["sh -c 'echo to-stdout; echo to-stderr >&2; exit 1'"]\n""",
    )
    exit_code = main(["gate", "evaluate", "--project", "acme"])
    assert exit_code == 3
    out = capsys.readouterr().out
    assert "to-stdout" in out
    assert "to-stderr" in out


def test_gate_evaluate_json_envelope_validates_against_envelope_schema(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    envelope_schema = json.loads(
        (_SCHEMA_PATH.parent / "envelope.v1.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=payload, schema=envelope_schema)
    assert payload["command"] == "gate evaluate"


def test_gate_evaluate_deterministic_across_two_runs(tmp_path, capsys, monkeypatch):
    """NFR-1/FR-21: the same tree, the same configured commands, no model
    call anywhere in the path -- two consecutive runs produce an identical
    verdict and exit code."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true", "false"]\n'
    )
    argv = ["gate", "evaluate", "--project", "acme", "--format", "json"]

    exit_code_1 = main(argv)
    payload_1 = json.loads(capsys.readouterr().out)
    exit_code_2 = main(argv)
    payload_2 = json.loads(capsys.readouterr().out)

    assert exit_code_1 == exit_code_2
    assert payload_1["verdict"] == payload_2["verdict"]
    assert payload_1["data"] == payload_2["data"]


def test_gate_evaluate_writes_no_file_under_the_repo_root_it_evaluates(
    tmp_path, capsys, monkeypatch
):
    """AC: 'no file has been added, removed, or modified by Marshal itself'
    -- gate evaluate reads a policy file and spawns read-only-from-Marshal's-
    perspective subprocesses; it performs no filesystem write of its own.

    `_conventional_policy` makes `tmp_path` the resolved repo root AND the
    spawned commands' own `cwd`, so this snapshot now covers the directory
    Marshal actually operates in. (Review finding: the earlier version
    snapshotted a `tmp_path` that held nothing but the policy file the test
    itself wrote, and was never the execution root at all.) Content, not
    just the path set, is compared -- an in-place rewrite leaves the tree
    listing identical."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true", "false"]\n'
    )

    def _snapshot():
        return {
            str(p.relative_to(tmp_path)): (p.read_bytes() if p.is_file() else None)
            for p in sorted(tmp_path.rglob("*"))
        }

    before = _snapshot()
    exit_code = main(["gate", "evaluate", "--project", "acme"])
    capsys.readouterr()

    assert exit_code == 3
    assert _snapshot() == before


# --- Story 2.3: `gate evaluate --scope-check` --------------------------------
#
# `run_evaluate`'s `vcs`/`fs` DI seams exist for exactly this: a fake
# `VcsPort` stands in for a real git worktree (this story's own pure-core
# tests already cover `GitVcs.changed_files` against a real repo in
# test_vcs_git.py), matching the existing `process=` injection convention
# above (`_RecordingProcess`).


class _FakeVcs:
    """A minimal ``VcsPort`` stand-in: ``changed_files`` returns a
    caller-configured tuple, or raises ``VcsCommandError`` when
    ``fail_with`` is set. ``repo_common_root`` is a no-op passthrough --
    nothing in these tests inspects its return value."""

    def __init__(self, changed=(), *, fail_with: str | None = None):
        self._changed = changed
        self._fail_with = fail_with

    def repo_common_root(self, start):
        return start

    def changed_files(self, repo_root, worktree_path, *, base):
        if self._fail_with is not None:
            from pyforge.marshal.adapters.vcs_git import VcsCommandError

            raise VcsCommandError(self._fail_with)
        return self._changed


def _scope_check_args(*, project="acme", run_id=None, story=None, format="json"):
    return argparse.Namespace(
        project=project,
        run_id=run_id,
        scope_check=True,
        story=story,
        format=format,
    )


def _write_epic_surfaces_policy(tmp_path, monkeypatch, slug, epic_surfaces_toml, extra=""):
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "repo_root", lambda: tmp_path)
    policy_dir = tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "marshal-policy.toml").write_text(
        epic_surfaces_toml + extra, encoding="utf-8"
    )


def test_gate_evaluate_scope_check_without_story_reports_mrs_gate_009(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(tmp_path, monkeypatch, "acme", "")
    args = _scope_check_args(story=None)

    exit_code = gate_module.run_evaluate(args, vcs=_FakeVcs())
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-009" in codes
    assert exit_code == 1


def test_gate_evaluate_scope_check_without_active_project_reports_mrs_gate_009(
    capsys, monkeypatch,
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    args = _scope_check_args(project="", story="2.3")

    exit_code = gate_module.run_evaluate(args, vcs=_FakeVcs())
    # Review finding (Blind Hunter): this test previously asserted only
    # exit_code == 1, which would pass for ANY unrelated failure producing
    # the same exit code -- unlike every sibling test in this block, it
    # never confirmed MRS-GATE-009 specifically appeared.
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-009" in codes
    assert exit_code == 1


def test_gate_evaluate_scope_check_unresolved_story_reports_mrs_ident_001(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(tmp_path, monkeypatch, "acme", "")
    args = _scope_check_args(story="not-a-story-key")

    exit_code = gate_module.run_evaluate(args, vcs=_FakeVcs())
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-IDENT-001" in codes
    assert exit_code == 1


def test_gate_evaluate_scope_check_changed_file_inside_surface_passes(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'epic_surfaces = { "2" = ["recipes/x/**"] }\n',
    )
    args = _scope_check_args(story="2.3")

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/x/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["scope_check"]["checked"] is True
    assert payload["data"]["scope_check"]["violations"] == 0
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-007" not in codes
    assert "MRS-GATE-008" not in codes


def test_gate_evaluate_scope_check_changed_file_outside_surface_reports_mrs_gate_007(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.model import Verdict

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'epic_surfaces = { "2" = ["recipes/x/**"] }\n',
    )
    args = _scope_check_args(story="2.3")

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/y/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-007" in codes
    assert payload["verdict"] == Verdict.SCOPE_VIOLATION.value
    assert exit_code == 2


def test_gate_evaluate_scope_check_frozen_seed_path_reports_mrs_gate_008(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'epic_surfaces = { "2" = ["recipes/x/**"] }\n'
        'frozen_surfaces = ["recipes/x/recipe.yaml"]\n',
    )
    args = _scope_check_args(story="2.3")

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/x/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    frozen_finding = next(
        finding for finding in payload["findings"] if finding["code"] == "MRS-GATE-008"
    )
    assert "policy" in frozen_finding["message"]


def test_gate_evaluate_scope_check_spec_declared_surface_narrows(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey, render_filename_slug

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'epic_surfaces = { "2" = ["recipes/x/**", "recipes/y/**"] }\n',
    )
    specs_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "acme"
        / "planning-artifacts"
        / "specs"
    )
    specs_dir.mkdir(parents=True, exist_ok=True)
    key = StoryKey(epic=2, seq=3)
    (specs_dir / f"spec-{render_filename_slug(key)}-scope.md").write_text(
        "---\ntitle: 'x'\nsurface: [\"recipes/x/**\"]\n---\n\n<intent-contract>\n",
        encoding="utf-8",
    )
    args = _scope_check_args(story="2.3")

    # recipes/y/** is in the POLICY surface but excluded by the spec's own
    # narrower declaration -- a change there must now violate.
    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/y/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["scope_check"]["spec_surface"] == ["recipes/x/**"]
    assert payload["data"]["scope_check"]["effective_surface"] == ["recipes/x/**"]
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-007" in codes


def test_find_spec_text_degrades_to_none_on_a_non_utf8_spec_file(tmp_path):
    """Review finding: a non-UTF-8 spec file must degrade to "nothing to
    narrow against" (None) like every other best-effort read in this
    module, not crash with a raw UnicodeDecodeError."""
    from pyforge.marshal.cli.gate import _find_spec_text
    from pyforge.marshal.core.identity import StoryKey, render_filename_slug

    specs_dir = (
        tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "specs"
    )
    specs_dir.mkdir(parents=True, exist_ok=True)
    key = StoryKey(epic=2, seq=3)
    (specs_dir / f"spec-{render_filename_slug(key)}.md").write_bytes(b"\xff\xfe not utf-8")

    assert _find_spec_text(tmp_path, "acme", key) is None


def test_gate_evaluate_scope_check_multiline_surface_block_reports_mrs_gate_009(
    tmp_path, capsys, monkeypatch
):
    """AD-27, review finding (Edge Case Hunter): a multi-line YAML `surface:`
    block in the story's own tracked spec is a form the parser does not
    support -- it must be reported and skipped (MRS-GATE-009), never
    silently treated as "no declared surface" (which would widen the
    effective surface back to the bare policy surface)."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey, render_filename_slug

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'epic_surfaces = { "2" = ["recipes/x/**"] }\n',
    )
    specs_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "acme"
        / "planning-artifacts"
        / "specs"
    )
    specs_dir.mkdir(parents=True, exist_ok=True)
    key = StoryKey(epic=2, seq=3)
    # A `## Verification` section with no `**Commands:**` sub-list parses to
    # an EMPTY declared-commands tuple (Story 2.7), not `None` -- so the
    # spec-binding check this story's own --story wiring now runs
    # unconditionally (independent of --scope-check) reports nothing here,
    # and this test still isolates the ONE thing it means to pin: the
    # multi-line `surface:` block's own MRS-GATE-009.
    (specs_dir / f"spec-{render_filename_slug(key)}-scope.md").write_text(
        '---\ntitle: \'x\'\nsurface:\n  - "recipes/x/**"\n---\n\n'
        "<intent-contract>\n\n## Verification\n",
        encoding="utf-8",
    )
    args = _scope_check_args(story="2.3")

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/x/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["scope_check"]["checked"] is False
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-009" in codes
    assert exit_code == 1


def test_gate_evaluate_scope_check_vcs_failure_reports_mrs_gate_009(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey, render_filename_slug

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_epic_surfaces_policy(tmp_path, monkeypatch, "acme", "")
    # See the multi-line-surface test above: a bare `## Verification`
    # section (Story 2.7) keeps the now-unconditional spec-binding check
    # silent, so this test still isolates the VCS failure's own
    # MRS-GATE-009.
    specs_dir = (
        tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "specs"
    )
    specs_dir.mkdir(parents=True, exist_ok=True)
    key = StoryKey(epic=2, seq=3)
    (specs_dir / f"spec-{render_filename_slug(key)}.md").write_text(
        "---\ntitle: 'x'\n---\n\n<intent-contract>\n\n## Verification\n",
        encoding="utf-8",
    )
    args = _scope_check_args(story="2.3")

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(fail_with="not a git repository")
    )
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-009" in codes
    assert exit_code == 1


def test_gate_evaluate_scope_check_unconfigured_epic_flags_every_changed_file(
    tmp_path, capsys, monkeypatch
):
    """Pins the CORRECT, currently-unproven behavior (review finding, Blind
    Hunter): an unconfigured epic (`epic_surfaces` left at its DEFAULT `{}`)
    makes `compute_effective_surface` always empty, so EVERY changed file
    for that epic is flagged MRS-GATE-007 -- deny-by-default, consistent
    with "narrowing only". A future accidental change to "skip the check
    when unconfigured" must regress this test, not ship silently."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.model import Verdict

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    # No `epic_surfaces` key at all -- composes to DEFAULT_POLICY's `{}`.
    _write_epic_surfaces_policy(tmp_path, monkeypatch, "acme", "")
    args = _scope_check_args(story="2.3")

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/anything/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["scope_check"]["checked"] is True
    assert payload["data"]["scope_check"]["policy_surface"] == []
    assert payload["data"]["scope_check"]["effective_surface"] == []
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-007" in codes
    assert payload["verdict"] == Verdict.SCOPE_VIOLATION.value
    assert exit_code == 2


def test_gate_evaluate_scope_check_run_scope_unavailable_omits_scope_check_data(
    tmp_path, capsys, monkeypatch
):
    """When ``--run`` was requested but its fold could not be produced,
    MRS-GATE-005 already reports the root cause -- the scope check itself
    contributes no second, redundant finding, and `data` carries no
    `scope_check` key at all."""
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _write_epic_surfaces_policy(tmp_path, monkeypatch, "acme", "")
    args = _scope_check_args(story="2.3", run_id="run-99")

    exit_code = gate_module.run_evaluate(args, vcs=_FakeVcs())
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert codes == ["MRS-GATE-005"]
    assert "scope_check" not in payload["data"]
    assert exit_code == 1


# --- Story 2.7: `gate evaluate --story` binds to the spec's Success signal --
#
# AD-4/AD-31/AD-49: reuses the EXISTING `--story` flag, no new one. Runs
# whenever `--story` is supplied, WITH or WITHOUT `--scope-check`.


def _story_args(*, project="acme", run_id=None, scope_check=False, story="2.3", format="json"):
    return argparse.Namespace(
        project=project,
        run_id=run_id,
        scope_check=scope_check,
        story=story,
        format=format,
    )


def _write_tracked_spec(tmp_path, slug, key, *, commands=()):
    """A minimal tracked spec at the DURABLE `specs/spec-<key>.md` path
    (Story 4.1's own promotion target) with a `## Verification` ->
    `**Commands:**` Success signal declaring exactly `commands`."""
    from pyforge.marshal.core.identity import render_filename_slug

    specs_dir = (
        tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs"
    )
    specs_dir.mkdir(parents=True, exist_ok=True)
    commands_block = "\n".join(f"- `{command}` -- expected: ok." for command in commands)
    (specs_dir / f"spec-{render_filename_slug(key)}.md").write_text(
        "---\ntitle: 'x'\n---\n\n<intent-contract>\n\n"
        f"## Verification\n\n**Commands:**\n{commands_block}\n",
        encoding="utf-8",
    )


def test_gate_evaluate_story_with_no_tracked_spec_reports_mrs_gate_010(
    tmp_path, capsys, monkeypatch
):
    """No `--scope-check` at all -- the binding check still runs off the
    bare `--story` flag."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.model import Verdict

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    args = _story_args()

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-010" in codes
    assert payload["data"]["spec_binding"]["declared_commands"] is None
    # Review finding (P3): `has_binding` must be False for "no spec tracked
    # at all" -- distinct from "N commands narrowed" (`violations == 1` is
    # ambiguous between the two without this field).
    assert payload["data"]["spec_binding"]["has_binding"] is False
    assert payload["data"]["spec_binding"]["violations"] == 1
    assert payload["verdict"] == Verdict.SCOPE_VIOLATION.value
    assert exit_code == 2


def test_gate_evaluate_story_no_story_supplied_skips_binding_check(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    args = _story_args(story=None)

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-010" not in codes
    assert "MRS-GATE-011" not in codes
    assert "spec_binding" not in payload["data"]
    assert exit_code == 0


def test_gate_evaluate_story_declared_commands_subset_of_policy_no_binding_finding(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true", "false"]\n'
    )
    _write_tracked_spec(tmp_path, "acme", StoryKey(epic=2, seq=3), commands=("true",))
    args = _story_args()

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-010" not in codes
    assert "MRS-GATE-011" not in codes
    assert payload["data"]["spec_binding"]["declared_commands"] == ["true"]
    assert payload["data"]["spec_binding"]["has_binding"] is True
    assert payload["data"]["spec_binding"]["violations"] == 0
    assert exit_code == 3  # "false" itself still fails, MRS-GATE-001


def test_gate_evaluate_story_narrowed_command_reports_mrs_gate_011(
    tmp_path, capsys, monkeypatch
):
    """The spec's own Success signal promised `missing-check`, but the
    policy's `verify_commands` no longer runs it -- narrowed since
    tracking."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey
    from pyforge.marshal.core.model import Verdict

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    _write_tracked_spec(
        tmp_path, "acme", StoryKey(epic=2, seq=3), commands=("true", "missing-check")
    )
    args = _story_args()

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    finding = next(f for f in payload["findings"] if f["code"] == "MRS-GATE-011")
    assert "missing-check" in finding["message"]
    assert payload["verdict"] == Verdict.SCOPE_VIOLATION.value
    assert exit_code == 2


def test_gate_evaluate_story_extra_policy_command_is_not_a_finding(
    tmp_path, capsys, monkeypatch
):
    """One-directional (AC): policy running MORE than the spec declared is
    not itself a binding violation -- the spec's promise is a floor."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true", "false"]\n'
    )
    _write_tracked_spec(tmp_path, "acme", StoryKey(epic=2, seq=3), commands=("true",))
    args = _story_args()

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-010" not in codes
    assert "MRS-GATE-011" not in codes


def test_gate_evaluate_story_unresolved_story_key_skips_binding_reports_only_mrs_ident_001(
    tmp_path, capsys, monkeypatch
):
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    args = _story_args(story="not-a-story-key")

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert codes == ["MRS-IDENT-001"]
    assert "spec_binding" not in payload["data"]
    assert exit_code == 1


def test_gate_evaluate_story_no_resolvable_project_reports_mrs_gate_009(
    tmp_path, capsys, monkeypatch
):
    """Review finding (P1): an empty --project/active project must be
    reported the SAME loud way --scope-check's own identical precondition
    already reports it (MRS-GATE-009), never a silent skip -- this test
    used to assert the opposite (no finding at all, exit 0), which was
    exactly the false-green shape AD-49 exists to close."""
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    args = _story_args(project="")

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-009" in codes
    assert "MRS-GATE-010" not in codes
    assert "spec_binding" not in payload["data"]
    assert exit_code == 1


def test_gate_evaluate_story_syntactically_invalid_project_reports_mrs_gate_009(
    tmp_path, capsys, monkeypatch
):
    """The non-trivial case (P1): a NON-EMPTY but syntactically invalid
    project slug also fails `policy._is_valid_project_slug` -- unlike the
    empty-string case above, this exercises the actual validity check
    rather than short-circuiting on truthiness, and previously produced NO
    finding at all for the spec-binding check specifically (only an
    unrelated MRS-POLICY-006, from policy composition, happened to keep the
    verdict off `ok`)."""
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    args = _story_args(project="bad/slug")

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-009" in codes
    assert "MRS-GATE-010" not in codes
    assert "spec_binding" not in payload["data"]
    assert exit_code == 1


def test_gate_evaluate_story_run_scope_unavailable_skips_binding_check_too(
    tmp_path, capsys, monkeypatch
):
    """Mirrors --scope-check's own suppression (MRS-GATE-005 already covers
    the one root cause) -- with no --scope-check at all this time, proving
    the guard is not accidentally scope-check-specific."""
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n')
    args = _story_args(run_id="run-99")

    exit_code = gate_module.run_evaluate(args)
    payload = json.loads(capsys.readouterr().out)
    codes = [finding["code"] for finding in payload["findings"]]
    assert codes == ["MRS-GATE-005"]
    assert "spec_binding" not in payload["data"]
    assert exit_code == 1


def test_gate_evaluate_story_and_scope_check_share_one_spec_lookup(
    tmp_path, capsys, monkeypatch
):
    """`_find_spec_text` is called EXACTLY ONCE per invocation, its result
    used for both --scope-check and the spec-binding check (the story's
    own "Never duplicate" constraint)."""
    from pyforge.marshal.cli import gate as gate_module
    from pyforge.marshal.core.identity import StoryKey

    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'verify_commands = ["true"]\nepic_surfaces = { "2" = ["recipes/x/**"] }\n',
    )
    _write_tracked_spec(tmp_path, "acme", StoryKey(epic=2, seq=3), commands=("true",))

    calls: list[str] = []
    original = gate_module._find_spec_text

    def _counting_find_spec_text(root, project_slug, story_key):
        calls.append(project_slug)
        return original(root, project_slug, story_key)

    monkeypatch.setattr(gate_module, "_find_spec_text", _counting_find_spec_text)
    args = _story_args(scope_check=True)

    exit_code = gate_module.run_evaluate(
        args, vcs=_FakeVcs(changed=("recipes/x/recipe.yaml",))
    )
    payload = json.loads(capsys.readouterr().out)
    assert len(calls) == 1
    assert payload["data"]["scope_check"]["checked"] is True
    assert payload["data"]["spec_binding"]["declared_commands"] == ["true"]
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-010" not in codes
    assert "MRS-GATE-011" not in codes
    assert exit_code == 0


# --- Story 2.1 follow-up review pass -- regression guards ------------------


def test_gate_evaluate_symlinked_policy_out_of_tree_is_refused_and_never_runs(
    tmp_path, capsys, monkeypatch
):
    """A conventional policy path that RESOLVES outside
    `_bmad-output/projects/` must be refused, not executed.

    Review finding, verified live before the fix: the slug-shape gate proves
    the SLUG is well-formed, and `conventional_project_policy_path` builds a
    path -- neither proves where that path LANDS. Planting the conventional
    file as a symlink to an out-of-tree policy ran that policy's
    `verify_commands` and reported `verdict: clean`, `status: ok`, exit 0
    under `"slug": "acme"` -- the same "asserting a project scope the run
    never had" failure the previous pass removed `--project-policy` for.

    Asserts BOTH halves: the command never ran (the marker is the real
    evidence), and the refusal is non-green (MRS-POLICY-004 classifies
    UNEVALUABLE) rather than a silent skip to the exit-0 MRS-GATE-004 path.
    """
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "PROOF"
    (outside / "evil.toml").write_text(
        f'verify_commands = ["touch {marker}"]\n', encoding="utf-8"
    )
    root = tmp_path / "repo"
    policy_path = _conventional_policy(root, monkeypatch, "acme", "")
    policy_path.unlink()
    policy_path.symlink_to(outside / "evil.toml")

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert not marker.exists()
    assert exit_code == 1
    assert payload["verdict"] == "unevaluable"
    # MRS-POLICY-004 alone: the "no verify commands configured" finding is
    # correctly suppressed, because the operator DID configure commands and
    # Marshal refused to read them -- the same ok-status gate that branch
    # already carries.
    assert [f["code"] for f in payload["findings"]] == ["MRS-POLICY-004"]
    assert "outside" in payload["findings"][0]["message"]
    assert payload["data"]["policy_source"] is None


def test_gate_evaluate_text_format_cannot_be_forged_by_a_policy_path(
    tmp_path, capsys, monkeypatch
):
    """Review finding: the pass that quoted `slug` and the command strings
    left `root` and `policy source` interpolated RAW. Both are paths, POSIX
    filenames may contain newlines, and `policy_source` is a symlink TARGET
    -- chosen by whoever can write inside the projects tree, the same actor
    the containment check already assumes. A policy whose filename embedded
    a `findings:` block printed one on a run whose envelope carried none."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    forged = "real.toml\nfindings:\n  MRS-GATE-001 [error] FORGED-BY-PATH"
    policy_path = _conventional_policy(tmp_path, monkeypatch, "acme", "")
    target = policy_path.parent / forged
    target.write_text('verify_commands = ["true"]\n', encoding="utf-8")
    policy_path.unlink()
    policy_path.symlink_to(target)

    exit_code = main(["gate", "evaluate", "--project", "acme"])
    out = capsys.readouterr().out

    assert exit_code == 0
    # The envelope carried no findings, so no LINE of the report may be a
    # findings block or a finding -- the newline renders as an escape inside
    # the quoted path, not as report structure. (A substring check would not
    # discriminate: "findings:" legitimately appears inside the escaped
    # path, which is exactly the point.)
    lines = out.splitlines()
    assert "findings:" not in lines
    assert not any(line.startswith("  MRS-GATE-001") for line in lines)
    assert sum("FORGED-BY-PATH" in line for line in lines) == 1
    assert "\\n" in out


def test_gate_evaluate_symlinked_policy_inside_the_project_is_read_and_recorded(
    tmp_path, capsys, monkeypatch
):
    """The containment check refuses only what ESCAPES the project. A
    symlink pointing elsewhere inside the project's OWN directory is a
    legitimate layout (this repo symlinks artifact directories the same
    way), so it must still compose -- and `data["policy_source"]` records
    the RESOLVED target, not the symlink, so the file that really supplied
    the commands is auditable."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    policy_path = _conventional_policy(tmp_path, monkeypatch, "acme", "")
    shared = tmp_path / "_bmad-output" / "projects" / "acme" / "shared.toml"
    shared.write_text('verify_commands = ["true"]\n', encoding="utf-8")
    policy_path.unlink()
    policy_path.symlink_to(shared)

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["policy_source"] == str(shared.resolve())
    assert [entry["command"] for entry in payload["data"]["commands"]] == ["true"]


def test_gate_evaluate_symlink_to_another_project_is_refused_and_never_runs(
    tmp_path, capsys, monkeypatch
):
    """FR-20's "another project's gates never run", through the filesystem.

    Review finding, verified live: fencing containment at the shared
    `projects/` ROOT let one project's conventional path symlink to
    ANOTHER's. `--project acme` ran victim's `verify_commands` -- the marker
    file was created -- and reported `verdict: clean`, `status: ok`, exit 0
    under `"slug": "acme"`, which is exactly the "asserting a project scope
    the run never had" failure the `--project-policy` removal and the
    out-of-tree containment check were each meant to make structural. The
    fence is the SLUG's own directory now, so this is refused.
    """
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    marker = tmp_path / "VICTIM_RAN"
    victim_policy = _conventional_policy(
        tmp_path, monkeypatch, "victim", f'verify_commands = ["touch {marker}"]\n'
    )
    policy_path = _conventional_policy(tmp_path, monkeypatch, "acme", "")
    policy_path.unlink()
    policy_path.symlink_to(victim_policy)

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert not marker.exists()
    assert exit_code == 1
    assert payload["verdict"] == "unevaluable"
    assert [f["code"] for f in payload["findings"]] == ["MRS-POLICY-004"]
    assert payload["data"]["policy_source"] is None


def test_gate_evaluate_relocated_projects_tree_is_refused_and_never_runs(
    tmp_path, capsys, monkeypatch
):
    """The containment fence must not be relocatable along with the thing it
    fences.

    Review finding, verified live: `_resolve_policy_source` resolved BOTH
    the candidate and the `projects/` root, so symlinking
    `_bmad-output/projects` itself out of the tree made the fence move too
    -- containment held trivially and an out-of-repo policy's command ran,
    creating its marker, `verdict: clean`, exit 0. The project directory is
    anchored against `repo_root()` itself now.
    """
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli import gate as gate_module

    root = tmp_path / "repo"
    (root / "_bmad-output").mkdir(parents=True)
    monkeypatch.setattr(config_module, "repo_root", lambda: root)
    monkeypatch.setattr(gate_module, "repo_root", lambda: root)

    outside = tmp_path / "outside"
    (outside / "evil" / "planning-artifacts").mkdir(parents=True)
    marker = tmp_path / "OUTSIDE_RAN"
    (outside / "evil" / "planning-artifacts" / "marshal-policy.toml").write_text(
        f'verify_commands = ["touch {marker}"]\n', encoding="utf-8"
    )
    (root / "_bmad-output" / "projects").symlink_to(outside)

    exit_code = main(["gate", "evaluate", "--project", "evil", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert not marker.exists()
    assert exit_code == 1
    assert payload["verdict"] == "unevaluable"
    assert [f["code"] for f in payload["findings"]] == ["MRS-POLICY-004"]
    assert payload["data"]["policy_source"] is None


@pytest.mark.parametrize("kind", ["dangling", "loop"])
def test_gate_evaluate_broken_symlink_policy_is_not_a_green_gate(
    kind, tmp_path, capsys, monkeypatch
):
    """A broken symlink is a CONFIGURED policy that cannot be followed, not
    an absent one.

    Review finding, verified live for both shapes: `is_file()`/`is_dir()`
    are False for a dangling link and for a symlink loop, so both composed
    bare defaults and reported MRS-GATE-004 "no verify commands configured"
    -> warn -> exit 0, having run nothing -- telling the operator to add a
    command they had already added. This repo's own CLAUDE.md documents the
    `_bmad-output` symlinks as routinely desyncing, so it is a live failure
    mode whose outcome was the green half of the lattice.
    """
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    policy_path = _conventional_policy(tmp_path, monkeypatch, "acme", "")
    policy_path.unlink()
    if kind == "dangling":
        policy_path.symlink_to(tmp_path / "gone.toml")
    else:
        policy_path.symlink_to(policy_path)

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["verdict"] == "unevaluable"
    codes = [f["code"] for f in payload["findings"]]
    assert codes == ["MRS-POLICY-004"]
    assert "MRS-GATE-004" not in codes


def test_gate_evaluate_shell_syntax_never_half_runs_green(tmp_path, capsys, monkeypatch):
    """`true && false` must not report `clean`.

    Review finding, verified live for `&&`, `|` and `>`: `PosixProcess` never
    passes `shell=True`, so `shlex.split` handed the operators to `true` as
    ordinary arguments; `true` ignored them, exited 0, and the envelope said
    `verdict: clean`, exit 0, with ZERO findings while the `false` half never
    ran. Preflight's own resolvability check cannot catch it either -- it
    inspects `tokens[0]`, and `true` resolves.
    """
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true && false"]\n'
    )

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["verdict"] == "unevaluable"
    assert [f["code"] for f in payload["findings"]] == ["MRS-GATE-003"]
    assert "shell syntax" in payload["findings"][0]["message"]
    assert payload["data"]["commands"][0]["resolvable"] is False


@pytest.mark.parametrize(
    "command",
    [
        # Spaced forms -- the only ones the original whole-token denylist
        # could see.
        "echo hi | grep nope",
        "true > /dev/null",
        "a & b",
        "true >> log",
        "true && false",
        "a || b",
        # NO-SPACE forms (review finding, each verified live reporting
        # `clean`, exit 0, ZERO findings before the fix). This is the more
        # common way an operator writes a redirect, and every pre-existing
        # test of this guard used a spaced form, so the suite could not see
        # the hole.
        "true >out.txt",
        "echo hi|grep nope",
        "true 2>/dev/null",
        "true &> /dev/null",
        "true 1> /dev/null",
        "cmd <in.txt",
        "a 2>&1",
        # `;` was deliberately excluded by the previous guard (to spare
        # `find -exec cmd \\;`), which made the classic command separator a
        # silent green. Escaping is tracked now, so it is included.
        "true ; false",
        "true;false",
    ],
)
def test_gate_evaluate_every_shell_operator_form_fails_closed(
    command, tmp_path, capsys, monkeypatch
):
    """Each detected operator form lands `unevaluable`, never `clean`."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", f"verify_commands = [{command!r}]\n"
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["verdict"] == "unevaluable"
    assert [f["code"] for f in payload["findings"]] == ["MRS-GATE-003"]


@pytest.mark.parametrize(
    "command",
    [
        # A metacharacter QUOTED as data, in each spelling operators
        # actually use. Review finding: `shlex.split` strips quotes, so the
        # old whole-token denylist saw a lone quoted operator as
        # byte-identical to a bare one and failed these CLOSED -- a valid
        # verify command permanently `unevaluable` with no escape hatch.
        "echo '|'",
        "echo \"|\"",
        "echo '>'",
        "echo '&&'",
        "echo ';'",
        # BACKSLASH-escaped, the form that makes `;` safe to include:
        # `find . -exec cmd \\;` passes a bare `;` as a legitimate argument.
        "echo \\;",
        "echo \\|",
        # And an ordinary command with no metacharacter at all -- the shape
        # of this repo's own real policy-declared verify commands.
        "echo ok",
    ],
)
def test_gate_evaluate_quoted_or_escaped_metacharacters_still_run(
    command, tmp_path, capsys, monkeypatch
):
    """The guard must fire on SYNTAX, never on DATA -- otherwise it fails
    closed on legitimate commands and trains the gate away."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    # `json.dumps`, not `{command!r}`: Python's repr emits a SINGLE-quoted
    # string, which TOML reads as a LITERAL string where `\\;` stays two
    # characters -- so a backslash-escaped case would reach the guard
    # double-escaped and prove the opposite of what it claims. A TOML basic
    # string uses JSON's own escape rules.
    _conventional_policy(
        tmp_path, monkeypatch, "acme", f"verify_commands = [{json.dumps(command)}]\n"
    )
    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["commands"][0]["returncode"] == 0


def test_gate_evaluate_quoted_shell_metacharacters_still_run(tmp_path, capsys, monkeypatch):
    """The operator check matches WHOLE tokens only, so a metacharacter
    inside a quoted argument (where it is inert data, not shell syntax) must
    still execute -- otherwise the fix would fail-closed on legitimate
    commands and train the gate away."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["echo \'a && b\'"]\n'
    )

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["verdict"] == "clean"
    assert payload["data"]["commands"][0]["stdout"] == "a && b\n"


def test_gate_evaluate_unstattable_policy_path_never_escapes_main(
    tmp_path, capsys, monkeypatch
):
    """`Path.is_file()` PROPAGATES PermissionError on this package's 3.12
    floor (3.13+ suppresses all OSError), so an unsearchable
    planning-artifacts/ crashed straight out through `main()`'s
    SystemExit/KeyboardInterrupt relay: a traceback, no envelope, and an
    exit code unrelated to any verdict. `cli/init.py::run_preflight` already
    carried this guard; `cli/gate.py` did not.

    The 3.12 semantics are simulated (the suite may run on 3.13+, where the
    real filesystem condition can no longer produce the exception)."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", 'verify_commands = ["false"]\n')
    real_is_file = Path.is_file

    def _raising_is_file(self):
        if self.name == "marshal-policy.toml":
            raise PermissionError(13, "Permission denied")
        return real_is_file(self)

    with patch.object(Path, "is_file", _raising_is_file):
        exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    # No traceback, a real envelope, and a verdict-derived exit code. The
    # guard treats an unstattable path as PRESENT, so the read is attempted:
    # here it succeeds (only `is_file` was made to raise), the policy
    # composes, and `false` really runs -- exit 3, not a crash and not the
    # silent exit-0 fallback. A read that genuinely fails lands
    # MRS-POLICY-004 instead (covered by the read-failure test below).
    assert exit_code == 3
    assert payload["verdict"] == "gate-failed"
    assert payload["data"]["commands"][0]["command"] == "false"


def test_gate_evaluate_directory_on_the_policy_path_is_not_a_green_gate(
    tmp_path, capsys, monkeypatch
):
    """A directory squatting on `marshal-policy.toml` used to make
    `is_file()` False, compose bare defaults, and exit 0 on MRS-GATE-004
    having run nothing. It must report the unreadable policy instead."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    policy_path = _conventional_policy(tmp_path, monkeypatch, "acme", "")
    policy_path.unlink()
    policy_path.mkdir()

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["findings"][0]["code"] == "MRS-POLICY-004"


def test_policy_read_failure_never_names_a_flag_gate_evaluate_does_not_have(
    tmp_path, capsys, monkeypatch
):
    """`MRS-POLICY-004`'s message said "cannot read --project-policy ..." for
    a CONVENTIONAL-path read -- pointing the operator at a flag `marshal gate
    evaluate` rejects with a usage error (and which this command's own
    docstring spends eighteen lines explaining must never come back)."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(tmp_path, monkeypatch, "acme", "verify_commands = [oops\n")

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    message = payload["findings"][0]["message"]
    assert payload["findings"][0]["code"] == "MRS-POLICY-004"
    assert "--project-policy" not in message
    assert message.startswith("cannot read project policy ")


def test_gate_evaluate_text_format_cannot_be_forged_by_a_command_string(
    tmp_path, capsys, monkeypatch
):
    """A newline inside a verify command forged whole lines of the default
    text report -- verified live, a command string ending
    `\\nfindings:\\n  MRS-GATE-001 [error] FORGED` printed a `findings:`
    block no finding produced. Quoting renders it as `\\n`, inert."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _conventional_policy(
        tmp_path,
        monkeypatch,
        "acme",
        'verify_commands = ["true\\nfindings:\\n  MRS-GATE-001 [error] FORGED"]\n',
    )

    exit_code = main(["gate", "evaluate", "--project", "acme"])
    out = capsys.readouterr().out

    # The command itself is legitimate argv (`true` with four ignored
    # arguments), so it runs and passes -- exit 0 with NO findings. That is
    # precisely what made the forgery dangerous: the report printed a
    # `findings:` block while the envelope carried none.
    assert exit_code == 0
    assert "\nfindings:\n  MRS-GATE-001 [error] FORGED" not in out
    assert "\\nfindings:" in out


def test_gate_evaluate_text_format_cannot_be_forged_by_a_slug(tmp_path, capsys, monkeypatch):
    """The header line interpolated `data["slug"]` raw, so a newline in
    `--project` forged report structure even though a malformed slug never
    reaches a policy read at all."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli import gate as gate_module

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(gate_module, "repo_root", lambda: tmp_path)

    exit_code = main(
        ["gate", "evaluate", "--project", "bad\nfindings:\n  MRS-GATE-001 [error] FORGED"]
    )
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "\nfindings:\n  MRS-GATE-001 [error] FORGED" not in out


def test_gate_evaluate_envelope_records_the_tree_and_policy_it_evaluated(
    tmp_path, capsys, monkeypatch
):
    """An envelope asserting `clean` must say WHERE and FROM WHAT. `slug`
    alone does not: `repo_root()` is `__file__`-derived (which tree gets
    gated depends on which copy of the package is importable), and the
    conventional path can be a symlink, so slug + convention do not
    determine the file that was read."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    policy_path = _conventional_policy(
        tmp_path, monkeypatch, "acme", 'verify_commands = ["true"]\n'
    )

    exit_code = main(["gate", "evaluate", "--project", "acme", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["data"]["root"] == str(tmp_path)
    assert payload["data"]["policy_source"] == str(policy_path.resolve())
