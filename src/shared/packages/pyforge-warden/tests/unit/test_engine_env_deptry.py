"""Unit tests — the ``_engine_env`` subprocess-normalization seam + the
``DeptryEngine`` runner (Story 1.3; ``extra_env``/exit-code widening Story
1.5), exercised with INJECTED FAKES only.

``subprocess.run`` is monkeypatched: no real deptry, no real network, no real
sleep. The seam's load-bearing invariants (argv list, temp-file output in
system temp, ``NO_COLOR=1`` + ``extra_env`` merging, ``stdin=DEVNULL``,
cleanup, typed errors for timeout / unavailable / undecodable, and the
exit-code contract — ``None`` on every early-return path, the real
``returncode`` once the child completes) are all proven against fakes.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import types
from pathlib import Path

import pytest

from pyforge.warden.engines import (
    DEPTRY_TIMEOUT_SECONDS,
    DEPTRY_VERSION_RANGE,
    DeptryEngine,
    ENGINE_VERSION_CHECK_TIMEOUT_SECONDS,
    _DEPTRY_VERSION_PATTERN,
    _check_engine_version,
    _engine_env,
)
from pyforge.warden.inventory import ResolvedInventory, merge_components
from pyforge.warden.models import (
    AXIS_HYGIENE,
    ErrorKind,
    ScannedManifest,
)

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")


def DEPTRY_ARGV(output_path: str) -> list[str]:
    return ["deptry", ".", "-o", output_path, "--no-ansi"]


def make_inventory(*components) -> ResolvedInventory:
    return ResolvedInventory(
        components=merge_components(components),
        resolved_scan_set=(MANIFEST,),
    )


def _fake_run_writing(content, captured: dict, *, returncode: int = 1):
    """A ``subprocess.run`` stand-in that writes ``content`` (str or bytes) to
    the ``-o`` path and records the call. Story 6.6: ``DeptryEngine.run`` now
    calls ``["deptry", "--version"]`` FIRST (the version pre-flight) -- this
    fake transparently answers that call with a fixed in-range version so
    every EXISTING ``DeptryEngine.run``-level test (which doesn't care about
    the version gate) is unaffected; ``_engine_env``-level tests never
    produce a ``--version`` argv in the first place, so this branch is a
    no-op for them."""

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 0.25.1\n", stderr=b""
            )
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        out_path = argv[argv.index("-o") + 1]
        captured["out_path"] = out_path
        if isinstance(content, bytes):
            Path(out_path).write_bytes(content)
        else:
            Path(out_path).write_text(content, encoding="utf-8")
        return types.SimpleNamespace(returncode=returncode, stdout=b"", stderr=b"")

    return fake_run


# --- _engine_env normalization invariants ------------------------------------


def test_engine_env_uses_argv_list_temp_file_no_color_and_devnull(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)

    assert error is None
    assert text == "[]"
    assert exit_code == 1  # _fake_run_writing's default returncode, surfaced
    argv = captured["argv"]
    assert isinstance(argv, list)
    assert argv[0] == "deptry"
    assert argv[1] == "."
    assert "--no-ansi" in argv
    assert "-o" in argv
    kwargs = captured["kwargs"]
    # argv-only: never a shell.
    assert kwargs.get("shell", False) is False
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["env"]["NO_COLOR"] == "1"
    assert kwargs["cwd"] == str(tmp_path)
    # exit code is content: check=False (or absent), never raising on non-zero.
    assert kwargs.get("check", False) is False


def test_engine_env_output_file_is_in_system_temp_not_the_scanned_tree(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)

    out_path = Path(captured["out_path"])
    assert out_path.parent == Path(tempfile.gettempdir())
    # Never inside the scanned tree (NFR-S4).
    assert tmp_path not in out_path.parents


def test_engine_env_cleans_up_the_temp_file_on_success(monkeypatch, tmp_path):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert not os.path.exists(captured["out_path"])


def test_engine_env_passes_the_configured_timeout(monkeypatch, tmp_path):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert captured["kwargs"]["timeout"] == DEPTRY_TIMEOUT_SECONDS


# --- typed failure paths (injected, never a real sleep/binary) ---------------


def test_engine_env_timeout_is_a_typed_engine_timeout(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["out_path"] = argv[argv.index("-o") + 1]
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error is not None
    assert error.kind is ErrorKind.ENGINE_TIMEOUT
    assert error.owner == "deptry"
    assert exit_code is None  # the child's outcome is unknown (timed out)
    # cleaned up even on the failure path.
    assert not os.path.exists(captured["out_path"])


def test_engine_env_missing_binary_is_engine_unavailable(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["out_path"] = argv[argv.index("-o") + 1]
        raise FileNotFoundError("deptry")

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert error.owner == "deptry"
    assert exit_code is None  # the child never ran (binary not found)
    assert not os.path.exists(captured["out_path"])


def test_engine_env_vanished_cwd_is_not_misreported_as_missing_binary(
    monkeypatch, tmp_path
):
    """subprocess raises FileNotFoundError for BOTH a missing binary AND a
    missing cwd (failed pre-exec chdir). A target dir that vanished after
    discovery (TOCTOU) must report engine-execution-failed, NOT
    engine-unavailable ('binary not found on PATH') — the seam Story 1.5's
    osv runner reuses. Follow-up Opus review, 2026-07-14."""
    gone = tmp_path / "vanished"  # never created

    def fake_run(argv, **kwargs):
        raise FileNotFoundError(gone)

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=gone)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert "not an existing directory" in error.message
    assert "not found on PATH" not in error.message
    assert exit_code is None  # the child never ran


def test_engine_env_undecodable_output_is_output_unparseable(
    monkeypatch, tmp_path
):
    captured: dict = {}
    # Invalid UTF-8 bytes written to the machine-output file.
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_run_writing(b"\xff\xfe\x00garbage", captured, returncode=0),
    )
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE
    # The child DID complete (it wrote undecodable bytes) — its real exit
    # code is still surfaced even though the output is unusable.
    assert exit_code == 0
    assert not os.path.exists(captured["out_path"])


def test_engine_env_surfaces_exit_code_on_unreadable_output_file(
    monkeypatch, tmp_path
):
    """The second post-completion decode-failure path (an OSError reading
    the output file, distinct from UnicodeDecodeError) also carries the
    child's real exit code."""
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["out_path"] = argv[argv.index("-o") + 1]
        # Unlink the output file out from under _engine_env's own read —
        # forces the OSError-reading-output path (engine-execution-failed),
        # not the UnicodeDecodeError path.
        os.unlink(captured["out_path"])
        return types.SimpleNamespace(returncode=3, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert exit_code == 3


def test_engine_env_mkstemp_failure_yields_typed_error_and_no_exit_code(
    monkeypatch, tmp_path
):
    """The earliest early-return path: the temp output file could not even
    be created, so the child never spawned — exit_code is None."""

    def fake_mkstemp(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(tempfile, "mkstemp", fake_mkstemp)
    text, error, exit_code = _engine_env(DEPTRY_ARGV, owner="deptry", cwd=tmp_path)
    assert text is None
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert exit_code is None


# --- extra_env merging (Story 1.5's osv-scanner runner needs this) -----------


def test_engine_env_merges_extra_env_over_the_copied_os_environ(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    monkeypatch.setenv("PDOS_PREEXISTING", "from-os-environ")
    _engine_env(
        DEPTRY_ARGV,
        owner="deptry",
        cwd=tmp_path,
        extra_env={"OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY": "/some/cache"},
    )
    env = captured["kwargs"]["env"]
    # The parent's own environment is still present (a COPY, not a replace)...
    assert env["PDOS_PREEXISTING"] == "from-os-environ"
    # ...NO_COLOR is still forced...
    assert env["NO_COLOR"] == "1"
    # ...and extra_env is merged in on top.
    assert env["OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"] == "/some/cache"


def test_engine_env_extra_env_can_override_no_color(monkeypatch, tmp_path):
    """extra_env is merged OVER the NO_COLOR default (last-write-wins) —
    documents the actual precedence rather than asserting NO_COLOR is
    unconditionally un-overridable."""
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    _engine_env(
        DEPTRY_ARGV,
        owner="deptry",
        cwd=tmp_path,
        extra_env={"NO_COLOR": "0"},
    )
    assert captured["kwargs"]["env"]["NO_COLOR"] == "0"


def test_engine_env_none_extra_env_behaves_like_deptrys_default_call(
    monkeypatch, tmp_path
):
    """extra_env=None (the default) must not change DeptryEngine's existing
    behavior — no KeyError, no spurious env keys."""
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    text, error, exit_code = _engine_env(
        DEPTRY_ARGV, owner="deptry", cwd=tmp_path, extra_env=None
    )
    assert error is None
    assert text == "[]"
    assert captured["kwargs"]["env"]["NO_COLOR"] == "1"


# --- DeptryEngine wiring on top of _engine_env -------------------------------


def test_deptry_engine_maps_valid_output_to_findings_and_coverage(
    monkeypatch, tmp_path, component_factory
):
    captured: dict = {}
    record = {
        "error": {"code": "DEP001", "message": "'absent' imported but missing"},
        "module": "absent",
        "location": {"file": "pkg/__init__.py", "line": 1, "column": 8},
    }
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps([record]), captured)
    )
    inventory = make_inventory(
        component_factory(name="requests", version="2.31.0"),
        component_factory(name="packaging", version="24.0"),
    )
    result = DeptryEngine().run(tmp_path, inventory)

    assert [f.id for f in result.findings] == ["hygiene:DEP001:absent"]
    assert result.findings[0].axis == AXIS_HYGIENE
    assert result.errors == ()
    (coverage,) = result.coverage
    assert coverage.axis == AXIS_HYGIENE
    assert coverage.deps_assessed == inventory.count == 2


def test_deptry_engine_ignores_the_exit_code(monkeypatch, tmp_path):
    """deptry exits 1 when issues are found; a clean ``[]`` with returncode 1
    is still clean (exit code is content, never the gate)."""
    captured: dict = {}
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing("[]", captured, returncode=1)
    )
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    assert result.errors == ()
    assert len(result.coverage) == 1  # a coverage claim on a successful run


def test_deptry_engine_unavailable_binary_yields_typed_error_no_coverage(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        raise FileNotFoundError("deptry")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert result.coverage == ()  # no coverage claim when nothing was assessed


def test_deptry_engine_timeout_yields_typed_error(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_TIMEOUT
    assert result.coverage == ()


def test_deptry_engine_non_array_output_is_output_unparseable(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps({"not": "array"}), captured)
    )
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNPARSEABLE
    assert result.coverage == ()


def test_deptry_engine_malformed_record_is_counted_and_reported(
    monkeypatch, tmp_path, component_factory
):
    """A structurally-broken record inside a valid array is surfaced as an
    engine-output-unrecognized error (never dropped) while valid records
    still become findings."""
    captured: dict = {}
    payload = [
        {"error": {"code": "DEP002", "message": "unused"}, "module": "requests"},
        {"module": "no-code"},  # malformed
    ]
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps(payload), captured)
    )
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    result = DeptryEngine().run(tmp_path, inventory)
    assert [f.id for f in result.findings] == ["hygiene:DEP002:requests"]
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED


# --- Story 2.2: the unconditional synthesized front-door --------------------


def test_deptry_engine_always_appends_requirements_files_flag(
    monkeypatch, tmp_path, component_factory
):
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    argv = captured["argv"]
    assert "--requirements-files" in argv
    input_path = argv[argv.index("--requirements-files") + 1]
    assert input_path != ""
    # No requirements.txt at the scan root: the flag carries ONLY the
    # synthesized temp file (follow-up review, 2026-07-16).
    assert "," not in input_path


def test_deptry_engine_reappends_the_projects_own_requirements_txt(
    monkeypatch, tmp_path, component_factory
):
    """Follow-up review (2026-07-16): --requirements-files REPLACES deptry's
    own native default requirements source (`requirements.txt`) rather than
    merging with it (verified live against deptry 0.25.1) -- so a scan root
    carrying its own requirements.txt must have it re-appended to the
    flag's comma-list, or every pip-declared dep there becomes a false
    DEP001."""
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    argv = captured["argv"]
    value = argv[argv.index("--requirements-files") + 1]
    synth_path, _, reappended = value.partition(",")
    assert synth_path  # the synthesized front-door always comes first
    assert reappended == "requirements.txt"


def test_deptry_engine_frontdoor_content_matches_synthesized_lines(
    monkeypatch, tmp_path, component_factory
):
    """The temp input file's content is read INSIDE the fake subprocess
    call, before this test's own cleanup assertion — the file must
    genuinely carry the synthesized `name==version` line."""
    captured: dict = {}

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 0.25.1\n", stderr=b""
            )
        captured["argv"] = argv
        input_path = argv[argv.index("--requirements-files") + 1]
        captured["frontdoor_content"] = Path(input_path).read_text(encoding="utf-8")
        out_path = argv[argv.index("-o") + 1]
        Path(out_path).write_text("[]", encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    assert captured["frontdoor_content"] == "numpy==1.26.0\n"


def test_deptry_engine_cleans_up_the_frontdoor_input_file(
    monkeypatch, tmp_path, component_factory
):
    captured: dict = {}

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 0.25.1\n", stderr=b""
            )
        captured["argv"] = argv
        captured["input_path"] = argv[argv.index("--requirements-files") + 1]
        out_path = argv[argv.index("-o") + 1]
        Path(out_path).write_text("[]", encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    assert not os.path.exists(captured["input_path"])


def test_deptry_engine_frontdoor_survives_an_empty_inventory(
    monkeypatch, tmp_path
):
    """No candidates at all: the flag is STILL passed (unconditional), with
    an empty input file — never skipped, never a crash."""
    captured: dict = {}

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 0.25.1\n", stderr=b""
            )
        captured["argv"] = argv
        input_path = argv[argv.index("--requirements-files") + 1]
        captured["frontdoor_content"] = Path(input_path).read_text(encoding="utf-8")
        out_path = argv[argv.index("-o") + 1]
        Path(out_path).write_text("[]", encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert "--requirements-files" in captured["argv"]
    assert captured["frontdoor_content"] == ""
    assert result.findings == ()


def test_deptry_engine_frontdoor_mkstemp_failure_yields_typed_error(
    monkeypatch, tmp_path, component_factory
):
    def fake_mkstemp(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(tempfile, "mkstemp", fake_mkstemp)
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    result = DeptryEngine().run(tmp_path, inventory)
    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert result.coverage == ()


def test_deptry_engine_surfaces_a_finding_for_an_unsafe_identity_component(
    monkeypatch, tmp_path, component_factory
):
    """Fix 6 (2026-07-16 review): a component whose resolved pypi identity
    fails the NFR-S6 safe-token purity guard used to just vanish from the
    front-door synthesis with ZERO surfaced record --
    `_synthesize_deptry_frontdoor`'s `.excluded` was computed but never
    wired into `DeptryEngine.run`'s returned findings, unlike every other
    withhold/exclusion path in this codebase (e.g. `OsvEngine.run`'s
    identically-shaped `excluded_findings`)."""
    from pyforge.warden.inventory import PypiIdentity

    captured: dict = {}

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 0.25.1\n", stderr=b""
            )
        captured["argv"] = argv
        input_path = argv[argv.index("--requirements-files") + 1]
        captured["frontdoor_content"] = Path(input_path).read_text(encoding="utf-8")
        out_path = argv[argv.index("-o") + 1]
        Path(out_path).write_text("[]", encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    unsafe = component_factory(
        name="evil",
        version="1.0.0",
        pypi_identity=PypiIdentity(name="-rf /", version="1.0.0"),
    )
    safe = component_factory(name="requests", version="2.31.0")
    inventory = make_inventory(unsafe, safe)

    result = DeptryEngine().run(tmp_path, inventory)

    assert [f.id for f in result.findings] == [
        "indeterminate:unsafe-identity-hygiene:evil@1.0.0"
    ]
    assert result.findings[0].axis == AXIS_HYGIENE
    assert result.errors == ()
    # The safe component still made it into the synthesized front-door --
    # the unsafe one was excluded, never written raw (NFR-S6).
    assert captured["frontdoor_content"] == "requests==2.31.0\n"


def test_deptry_engine_merges_unsafe_identity_findings_with_parsed_findings(
    monkeypatch, tmp_path, component_factory
):
    """The excluded-component finding survives ALONGSIDE a real deptry
    finding from the SAME run, sorted together (never one clobbering the
    other)."""
    from pyforge.warden.inventory import PypiIdentity

    captured: dict = {}
    record = {
        "error": {"code": "DEP002", "message": "unused"},
        "module": "requests",
    }
    monkeypatch.setattr(
        subprocess, "run", _fake_run_writing(json.dumps([record]), captured)
    )
    unsafe = component_factory(
        name="evil",
        version="1.0.0",
        pypi_identity=PypiIdentity(name="-rf /", version="1.0.0"),
    )
    inventory = make_inventory(unsafe)

    result = DeptryEngine().run(tmp_path, inventory)

    assert [f.id for f in result.findings] == [
        "hygiene:DEP002:requests",
        "indeterminate:unsafe-identity-hygiene:evil@1.0.0",
    ]


def test_deptry_engine_deps_assessed_excludes_purity_guard_exclusions(
    monkeypatch, tmp_path, component_factory
):
    """Story 1.7 fix: ``deps_assessed`` must count ONLY what actually
    reached deptry's front-door (``len(synthesized.lines)``) — mirrors
    ``OsvEngine.run``'s own formula exactly. Before this fix, ``DeptryEngine``
    over-claimed ``deps_assessed == inventory.count`` even though the
    excluded component never reached deptry's front-door at all
    (deferred-work.md)."""
    from pyforge.warden.inventory import PypiIdentity

    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    unsafe = component_factory(
        name="evil",
        version="1.0.0",
        pypi_identity=PypiIdentity(name="-rf /", version="1.0.0"),
    )
    safe = component_factory(name="requests", version="2.31.0")
    inventory = make_inventory(unsafe, safe)

    result = DeptryEngine().run(tmp_path, inventory)

    (coverage,) = result.coverage
    assert inventory.count == 2
    assert coverage.deps_total == 2
    # 1 of 2 was excluded by the purity guard -- never reached the front-door.
    assert coverage.deps_assessed == 1


def test_deptry_engine_deps_assessed_excludes_hygiene_uncovered_components(
    monkeypatch, tmp_path, component_factory
):
    """Review finding (2026-07-17): a component skipped by
    ``_synthesize_deptry_frontdoor``'s ``continue`` (``hygiene_covered=
    False`` or no resolved ``pypi_identity``) lands in NEITHER
    ``synthesized.lines`` NOR ``synthesized.excluded`` — a third bucket the
    now-fixed ``deps_assessed=len(synthesized.lines)`` formula correctly
    excludes, but the original ``inventory.count - len(excluded)`` formula
    silently over-counted as assessed (reproduced live before the fix:
    ``deps_assessed`` computed 1 for a 1-real-dependency inventory whose
    OTHER component was never sent to deptry at all)."""
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    uncovered = component_factory(
        name="skipped", version="1.0.0", hygiene_covered=False
    )
    safe = component_factory(name="requests", version="2.31.0")
    inventory = make_inventory(uncovered, safe)

    result = DeptryEngine().run(tmp_path, inventory)

    (coverage,) = result.coverage
    assert inventory.count == 2
    assert coverage.deps_total == 2
    # "skipped" never reached the front-door (hygiene_covered=False) --
    # never in `excluded` either, so only len(lines) counts it correctly.
    assert coverage.deps_assessed == 1


def test_deptry_engine_frontdoor_is_a_no_op_when_native_pyproject_present(
    monkeypatch, tmp_path, component_factory
):
    """Regression for the Boundaries' central claim: the flag is added
    UNCONDITIONALLY, never conditionally detected — this test proves our
    OWN code never skips it based on target contents (the claim that REAL
    deptry then silently ignores it for a native pyproject.toml target is
    deptry's own documented behavior, empirically confirmed live against
    deptry 0.25.1: `deptry . --requirements-files <nonexistent-path>` exits
    0 with no error when a `[project].dependencies`-bearing pyproject.toml
    is present)."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n'
        'dependencies = ["requests"]\n',
        encoding="utf-8",
    )
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    inventory = make_inventory(component_factory(name="requests", version="2.31.0"))
    DeptryEngine().run(tmp_path, inventory)
    assert "--requirements-files" in captured["argv"]


def test_deptry_engine_reappends_config_declared_requirements_files(
    monkeypatch, tmp_path, component_factory
):
    """Second review pass (2026-07-16): --requirements-files REPLACES
    deptry's requirements-source SETTING -- which is the config-declared
    `[tool.deptry].requirements_files` list when present, not always the
    literal default `requirements.txt`. Re-appending only the default
    false-DEP001'd every dep a config-declared file carries (verified live
    against real deptry 0.25.1: bare `deptry .` green, with the flag red).
    The config list replaces the default in the re-append too."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.deptry]\nrequirements_files = ["reqs/base.txt"]\n',
        encoding="utf-8",
    )
    (tmp_path / "reqs").mkdir()
    (tmp_path / "reqs" / "base.txt").write_text("requests\n", encoding="utf-8")
    # A sibling requirements.txt must NOT be re-appended once config
    # declares its own list -- deptry itself would not read it natively.
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    argv = captured["argv"]
    value = argv[argv.index("--requirements-files") + 1]
    synth_path, _, reappended = value.partition(",")
    assert synth_path
    assert reappended == "reqs/base.txt"


def test_deptry_engine_skips_a_missing_configured_requirements_file(
    monkeypatch, tmp_path, component_factory
):
    """A configured path that definitively does not exist is dropped from
    the re-append (deptry crashes outright on a nonexistent
    --requirements-files entry, unlike its tolerant native default)."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.deptry]\nrequirements_files = ["missing.txt"]\n',
        encoding="utf-8",
    )
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    argv = captured["argv"]
    value = argv[argv.index("--requirements-files") + 1]
    assert "," not in value


def test_deptry_engine_malformed_pyproject_degrades_to_the_default(
    monkeypatch, tmp_path, component_factory
):
    """An unreadable/malformed pyproject.toml degrades the config read to
    deptry's default source list -- the engine still runs; deptry's own run
    against the same file surfaces the real problem loudly."""
    (tmp_path / "pyproject.toml").write_text("not = [valid toml", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
    captured: dict = {}
    monkeypatch.setattr(subprocess, "run", _fake_run_writing("[]", captured))
    inventory = make_inventory(component_factory(name="numpy", version="1.26.0"))
    DeptryEngine().run(tmp_path, inventory)
    argv = captured["argv"]
    value = argv[argv.index("--requirements-files") + 1]
    _synth, _, reappended = value.partition(",")
    assert reappended == "requirements.txt"


# --- Story 6.6 (FR21): the `_check_engine_version` pre-flight helper --------


def _fake_run_version(stdout: bytes, *, returncode: int = 0):
    """A ``subprocess.run`` stand-in for a ``--version`` invocation: no
    output file, just captured stdout bytes -- distinct from
    ``_fake_run_writing`` (which writes to an ``-o``/``--output-file`` path)
    because ``_check_engine_version`` never goes through ``_engine_env``."""

    def fake_run(argv, **kwargs):
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=b"")

    return fake_run


def test_check_engine_version_in_range_passes(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", _fake_run_version(b"deptry 0.25.1\n"))
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is None


def test_check_engine_version_patch_release_of_the_same_minor_passes(
    monkeypatch, tmp_path
):
    """NFR-C1: a RANGE, not an exact pin -- a later patch of the SAME
    evidence-backed minor is still trusted."""
    monkeypatch.setattr(subprocess, "run", _fake_run_version(b"deptry 0.25.9\n"))
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is None


def test_check_engine_version_out_of_range_is_engine_unavailable(
    monkeypatch, tmp_path
):
    """A newer, untested minor must fail loud, never silently pass (NFR-C1's
    entire point) -- via the EXISTING ENGINE_UNAVAILABLE kind (no new
    ErrorKind member)."""
    monkeypatch.setattr(subprocess, "run", _fake_run_version(b"deptry 0.26.0\n"))
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert result.owner == "deptry"
    assert "outside tested range" in result.message


def test_check_engine_version_missing_binary_is_engine_unavailable(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        raise FileNotFoundError("deptry")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert "not found" in result.message


def test_check_engine_version_vanished_cwd_is_distinguished_from_missing_binary(
    monkeypatch, tmp_path
):
    """Review finding, 2026-07-24: FileNotFoundError is raised for BOTH a
    missing executable AND a missing cwd -- a vanished scan target must not
    be misreported as "engine not installed" (mirrors _engine_env's own
    TOCTOU disambiguation)."""
    vanished = tmp_path / "does-not-exist"

    def fake_run(argv, **kwargs):
        raise FileNotFoundError("deptry")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=vanished,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_EXECUTION_FAILED
    assert "not an existing directory" in result.message


def test_check_engine_version_nonzero_exit_is_engine_unavailable_even_with_matching_stdout(
    monkeypatch, tmp_path
):
    """Review finding, 2026-07-24: stdout content alone is never trusted -- a
    broken/misconfigured install that exits non-zero but still prints a
    matching (e.g. stale/cached) version banner must not pass the gate."""
    monkeypatch.setattr(
        subprocess, "run", _fake_run_version(b"deptry 0.25.1\n", returncode=1)
    )
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert "exited 1" in result.message


def test_check_engine_version_unparseable_output_is_engine_unavailable(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        subprocess, "run", _fake_run_version(b"totally unexpected output\n")
    )
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert "could not parse version" in result.message


def test_check_engine_version_timeout_is_engine_timeout(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_TIMEOUT


def test_check_engine_version_other_oserror_is_engine_execution_failed(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert result is not None
    assert result.kind is ErrorKind.ENGINE_EXECUTION_FAILED


def test_check_engine_version_passes_the_version_check_timeout(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured["kwargs"] = kwargs
        return types.SimpleNamespace(returncode=0, stdout=b"deptry 0.25.1\n", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    _check_engine_version(
        owner="deptry",
        argv=["deptry", "--version"],
        version_pattern=_DEPTRY_VERSION_PATTERN,
        expected=DEPTRY_VERSION_RANGE,
        cwd=tmp_path,
    )
    assert captured["kwargs"]["timeout"] == ENGINE_VERSION_CHECK_TIMEOUT_SECONDS
    assert captured["kwargs"]["stdin"] is subprocess.DEVNULL
    assert captured["kwargs"]["check"] is False


# --- Story 6.6: the version gate wired into DeptryEngine.run ----------------


def _fake_run_deptry_version_and_scan(
    version_stdout: bytes, scan_content: str, captured: dict, *, scan_returncode: int = 0
):
    """A combined ``subprocess.run`` stand-in that answers BOTH the
    ``["deptry", "--version"]`` pre-flight call and the real
    ``deptry . -o ...`` scan call, distinguished by argv."""

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            captured["version_argv"] = argv
            captured["version_kwargs"] = kwargs
            return types.SimpleNamespace(
                returncode=0, stdout=version_stdout, stderr=b""
            )
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        out_path = argv[argv.index("-o") + 1]
        Path(out_path).write_text(scan_content, encoding="utf-8")
        return types.SimpleNamespace(
            returncode=scan_returncode, stdout=b"", stderr=b""
        )

    return fake_run


def test_deptry_engine_calls_the_version_check_before_the_real_scan(
    monkeypatch, tmp_path
):
    captured: dict = {}
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake_run_deptry_version_and_scan(b"deptry 0.25.1\n", "[]", captured),
    )
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert captured["version_argv"] == ["deptry", "--version"]
    assert "argv" in captured  # the real scan DID run -- in-range passes through
    assert result.errors == ()


def test_deptry_engine_out_of_range_version_never_invokes_the_real_subprocess(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 9.9.9\n", stderr=b""
            )
        pytest.fail(
            "the real deptry subprocess must never be invoked when the "
            "version gate fails"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    assert result.findings == ()
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert error.owner == "deptry"
    assert result.coverage == ()


def test_deptry_engine_missing_binary_version_never_invokes_the_real_subprocess(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            raise FileNotFoundError("deptry")
        pytest.fail("the real deptry subprocess must never be invoked")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert result.coverage == ()


def test_deptry_engine_version_gate_failure_preserves_excluded_findings(
    monkeypatch, tmp_path, component_factory
):
    """Boundaries: a version-check failure must not drop the purity-guard
    ``excluded_findings`` already computed before the gate -- mirrors the
    adjacent ``mkstemp`` OSError branch's own never-silently-dropped
    handling."""
    from pyforge.warden.inventory import PypiIdentity

    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"deptry 9.9.9\n", stderr=b""
            )
        pytest.fail("the real deptry subprocess must never be invoked")

    monkeypatch.setattr(subprocess, "run", fake_run)
    unsafe = component_factory(
        name="evil",
        version="1.0.0",
        pypi_identity=PypiIdentity(name="-rf /", version="1.0.0"),
    )
    inventory = make_inventory(unsafe)

    result = DeptryEngine().run(tmp_path, inventory)

    assert [f.id for f in result.findings] == [
        "indeterminate:unsafe-identity-hygiene:evil@1.0.0"
    ]
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE


def test_deptry_engine_unparseable_version_never_invokes_the_real_subprocess(
    monkeypatch, tmp_path
):
    def fake_run(argv, **kwargs):
        if argv[:2] == ["deptry", "--version"]:
            return types.SimpleNamespace(
                returncode=0, stdout=b"garbage output\n", stderr=b""
            )
        pytest.fail("the real deptry subprocess must never be invoked")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = DeptryEngine().run(tmp_path, make_inventory())
    (error,) = result.errors
    assert error.kind is ErrorKind.ENGINE_UNAVAILABLE
    assert "could not parse version" in error.message
