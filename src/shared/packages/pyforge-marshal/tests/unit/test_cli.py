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
    fields. The layer half is counted, not merely detected: exactly one
    `(layer=...)` suffix per key line, so a regression that drops the
    suffix from all but one line cannot ship green."""
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
    assert captured.out.count("(layer=") == 9


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
    """The 9-key vocabulary is declared in three places (_FIELD_ORDER, the
    _STATIC_KEYS/_SEED_KEYS sets, schemas/policy.json). This is the derive-
    don't-declare tie: adding a 10th key to core/policy.py without updating
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
