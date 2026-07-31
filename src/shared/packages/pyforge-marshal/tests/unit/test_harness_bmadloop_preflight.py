"""Unit tests for ``pyforge.marshal.adapters.harness_bmadloop.BmadLoopHarness``
(Story 1.7, AD-3/AD-19) -- ``ports.HarnessPort``'s sole implementation,
against the REAL installed ``bmad_loop`` 0.9.0 (no fakes for the package
itself; ``cli/init.py::run_preflight``'s own tests in ``test_init.py`` use a
``FakeHarness`` for the CLI-layer I/O matrix). Kept in a file separate from
``test_harness_policy_render.py`` (Story 1.10's own ``render_policy_toml``/
``write_policy_toml`` coverage) since this is a distinct concern: seven new
``HarnessPort`` methods, none of which render or write ``policy.toml``.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from pyforge.marshal.adapters.harness_bmadloop import BmadLoopHarness, HarnessError


@pytest.fixture
def harness() -> BmadLoopHarness:
    return BmadLoopHarness()


# --- binary_present ----------------------------------------------------------


def test_binary_present_true_for_the_real_harness_binary(harness):
    assert harness.binary_present("bmad-loop") is True


def test_binary_present_false_when_not_on_path(harness, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert harness.binary_present("bmad-loop") is False


def test_binary_present_false_for_a_nonsense_name(harness):
    assert harness.binary_present("definitely-not-a-real-binary-xyz") is False


# --- harness_version -----------------------------------------------------------


def test_harness_version_matches_the_real_installed_package(harness):
    """``bmad_loop.__version__`` is ``"0.9.0"`` -- pinned as this package's
    floor (``pyproject.toml``/``pixi.toml``, ``>=0.9.0,<0.10``)."""
    import bmad_loop

    assert harness.harness_version() == bmad_loop.__version__


def test_harness_version_none_when_binary_absent(harness, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert harness.harness_version() is None


def test_harness_version_none_on_a_nonzero_exit(harness, monkeypatch):
    import pyforge.marshal.adapters.harness_bmadloop as module

    def _fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.harness_version() is None


def test_harness_version_none_on_unparseable_output(harness, monkeypatch):
    import pyforge.marshal.adapters.harness_bmadloop as module

    def _fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="\n", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.harness_version() is None


def test_harness_version_none_on_missing_binary_launch_failure(harness, monkeypatch):
    import pyforge.marshal.adapters.harness_bmadloop as module

    def _raise_not_found(*args, **kwargs):
        raise FileNotFoundError("no such file: bmad-loop")

    monkeypatch.setattr(module.subprocess, "run", _raise_not_found)
    assert harness.harness_version() is None


def test_harness_version_none_on_a_hung_process(harness, monkeypatch):
    import pyforge.marshal.adapters.harness_bmadloop as module

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["bmad-loop"], timeout=10.0)

    monkeypatch.setattr(module.subprocess, "run", _raise_timeout)
    assert harness.harness_version() is None


def test_harness_version_parses_the_token_after_the_last_space(harness, monkeypatch):
    """argparse's own ``action="version"`` output shape: ``"<prog> <version>"``."""
    import pyforge.marshal.adapters.harness_bmadloop as module

    def _fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="bmad-loop 0.10.2\n", stderr=""
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    assert harness.harness_version() == "0.10.2"


# --- multiplexer_backend_available ----------------------------------------------


def test_multiplexer_backend_available_returns_a_real_selected_backend(harness):
    backend_name, available = harness.multiplexer_backend_available()
    assert isinstance(backend_name, str) and backend_name
    assert isinstance(available, bool)


def test_multiplexer_backend_available_raises_harness_error_when_bmad_loop_unimportable(
    harness, monkeypatch
):
    # sys.modules[name] = None is the documented way to force ImportError for
    # ONE submodule without disturbing the (already-imported, cached) parent
    # package other tests in this session depend on.
    monkeypatch.setitem(sys.modules, "bmad_loop.adapters.multiplexer", None)
    with pytest.raises(HarnessError, match="not importable"):
        harness.multiplexer_backend_available()


def test_multiplexer_backend_available_raises_harness_error_not_raw_on_multiplexer_error(
    harness, monkeypatch
):
    """Review finding: ``HarnessError``'s docstring named ``MultiplexerError``
    as caught-and-re-raised while nothing actually caught it --
    ``detect_multiplexers`` documents "never raises", but this module's own
    contract (no ``bmad_loop`` exception type escapes raw) must not rest on
    an upstream promise."""
    import bmad_loop.adapters.multiplexer as mux

    def _boom():
        raise mux.MultiplexerError("backend probe blew up")

    monkeypatch.setattr(mux, "detect_multiplexers", _boom)
    with pytest.raises(HarnessError, match="multiplexer detection failed"):
        harness.multiplexer_backend_available()


# --- adapter_binary / adapter_seed_files / adapter_first_run_note --------------


def test_adapter_binary_for_the_real_claude_profile(harness, tmp_path):
    assert harness.adapter_binary("claude", tmp_path) == "claude"


def test_adapter_seed_files_for_the_real_claude_profile(harness, tmp_path):
    seed_files = harness.adapter_seed_files("claude", tmp_path)
    assert ".mcp.json" in seed_files
    assert ".claude/settings.json" in seed_files


def test_adapter_first_run_note_for_the_real_claude_profile(harness, tmp_path):
    note = harness.adapter_first_run_note("claude", tmp_path)
    assert "claude" in note


def test_adapter_binary_differs_from_name_for_antigravity_profile(harness, tmp_path):
    """The precise reason ``HarnessPort`` needs a dedicated ``adapter_binary``
    method rather than reusing the adapter NAME as its own binary: two of the
    six packaged profiles diverge."""
    assert harness.adapter_binary("antigravity", tmp_path) == "agy"


def test_adapter_binary_raises_harness_error_for_an_unknown_adapter(harness, tmp_path):
    with pytest.raises(HarnessError):
        harness.adapter_binary("not-a-real-adapter", tmp_path)


def test_adapter_seed_files_raises_harness_error_for_an_unknown_adapter(harness, tmp_path):
    with pytest.raises(HarnessError):
        harness.adapter_seed_files("not-a-real-adapter", tmp_path)


def test_adapter_binary_raises_harness_error_when_bmad_loop_unimportable(harness, tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "bmad_loop.adapters.profile", None)
    with pytest.raises(HarnessError, match="not importable"):
        harness.adapter_binary("claude", tmp_path)


def test_adapter_binary_raises_harness_error_not_raw_when_profile_overlay_is_not_utf8(
    harness, tmp_path
):
    """Review finding: ``get_profile`` reads EVERY ``.bmad-loop/profiles/
    *.toml`` overlay file (via ``load_profiles``) before looking up the
    requested name, via plain ``Path.read_text(encoding="utf-8")`` -- a
    corrupt overlay file raises ``UnicodeDecodeError`` RAW, past
    ``ProfileError``, even when looking up an UNRELATED adapter name
    (``claude``, never mentioned in the broken file)."""
    profiles_dir = tmp_path / ".bmad-loop" / "profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "broken.toml").write_bytes(b"name = \"broken\"\nbinary = \"\xff\xfe\"\n")

    with pytest.raises(HarnessError):
        harness.adapter_binary("claude", tmp_path)


def test_adapter_binary_raises_harness_error_when_profile_overlay_field_is_wrong_typed(
    harness, tmp_path
):
    """Same gap as the non-UTF-8 case above, one layer up (second review
    pass): ``_parse_profile`` coerces overlay values with bare
    ``float()``/``int()``/``.items()``, so a VALID-TOML overlay with a
    wrong-typed field (``usage_grace_s = "boom"``) raises ``ValueError`` RAW
    past ``ProfileError`` -- again even when looking up an UNRELATED adapter
    name the broken file never mentions."""
    profiles_dir = tmp_path / ".bmad-loop" / "profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "broken.toml").write_text(
        'name = "broken"\n'
        'binary = "broken"\n'
        'usage_grace_s = "boom"\n'
        "[hooks]\n"
        'dialect = "none"\n',
        encoding="utf-8",
    )

    with pytest.raises(HarnessError, match="cannot read adapter profile overlay"):
        harness.adapter_binary("claude", tmp_path)


# --- story_feed_error -----------------------------------------------------------


def _seed_bmad_config(project, *, valid_config: bool = True) -> None:
    bmad_dir = project / "_bmad" / "bmm"
    bmad_dir.mkdir(parents=True)
    if valid_config:
        (bmad_dir / "config.yaml").write_text(
            "implementation_artifacts: '{project-root}/_bmad-output/implementation-artifacts'\n"
            "planning_artifacts: '{project-root}/_bmad-output/planning-artifacts'\n",
            encoding="utf-8",
        )


def test_story_feed_error_none_for_a_valid_feed(harness, tmp_path):
    _seed_bmad_config(tmp_path)
    feed_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_text("development_status: {}\n", encoding="utf-8")
    assert harness.story_feed_error(tmp_path) is None


def test_story_feed_error_when_bmad_config_missing(harness, tmp_path):
    error = harness.story_feed_error(tmp_path)
    assert error is not None
    assert "config" in error.lower() or "bmad" in error.lower()


def test_story_feed_error_when_sprint_status_file_missing(harness, tmp_path):
    _seed_bmad_config(tmp_path)
    error = harness.story_feed_error(tmp_path)
    assert error is not None
    assert "sprint status" in error.lower() or "not found" in error.lower()


def test_story_feed_error_when_sprint_status_is_invalid_yaml(harness, tmp_path):
    _seed_bmad_config(tmp_path)
    feed_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
    error = harness.story_feed_error(tmp_path)
    assert error is not None


def test_story_feed_error_never_raises_when_bmad_config_is_not_utf8(harness, tmp_path):
    """Review finding: ``bmadconfig.load_paths`` reads ``_bmad/bmm/
    config.yaml`` via plain ``Path.read_text(encoding="utf-8")`` BEFORE its
    own ``BmadConfigError`` handling begins -- non-UTF-8 bytes previously
    raised ``UnicodeDecodeError`` RAW past this method's documented "never
    raises" contract."""
    bmad_dir = tmp_path / "_bmad" / "bmm"
    bmad_dir.mkdir(parents=True)
    (bmad_dir / "config.yaml").write_bytes(b"implementation_artifacts: \xff\xfe\n")

    error = harness.story_feed_error(tmp_path)
    assert error is not None


def test_story_feed_error_never_raises_when_bmad_config_top_level_is_a_list(harness, tmp_path):
    """Second review pass, same contract one shape over: ``load_paths`` calls
    ``doc.get(...)`` on whatever ``yaml.safe_load`` returned without an
    isinstance check, so a config.yaml whose top level is a LIST (valid YAML,
    wrong shape) raised ``AttributeError`` RAW past both
    ``BmadConfigError`` and the OSError/UnicodeDecodeError catches."""
    bmad_dir = tmp_path / "_bmad" / "bmm"
    bmad_dir.mkdir(parents=True)
    (bmad_dir / "config.yaml").write_text("- a\n- b\n", encoding="utf-8")

    error = harness.story_feed_error(tmp_path)
    assert error is not None
    assert "shape" in error or "bmad-config" in error


def test_story_feed_error_never_raises_when_sprint_status_is_not_utf8(harness, tmp_path):
    """Same gap as the config.yaml case above, one layer down:
    ``sprintstatus.load`` reads the feed file the same unguarded way."""
    _seed_bmad_config(tmp_path)
    feed_dir = tmp_path / "_bmad-output" / "implementation-artifacts"
    feed_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_bytes(b"development_status: \xff\xfe\n")

    error = harness.story_feed_error(tmp_path)
    assert error is not None


def test_story_feed_error_never_raises_when_bmad_loop_unimportable(harness, tmp_path, monkeypatch):
    # `from bmad_loop import bmadconfig, sprintstatus` resolves `bmadconfig`
    # as a FROMLIST name of the already-imported `bmad_loop` package -- once
    # any earlier test (this file's own `test_story_feed_error_none_for_a_
    # valid_feed`, first in file order) has imported it successfully, Python
    # caches it as an ATTRIBUTE of the `bmad_loop` module object, and
    # `_handle_fromlist` checks that attribute BEFORE consulting
    # `sys.modules` -- so poisoning `sys.modules` alone (sufficient for the
    # dotted-submodule imports above) does not reliably force ImportError
    # here; the attribute must be removed too.
    import bmad_loop

    monkeypatch.setitem(sys.modules, "bmad_loop.bmadconfig", None)
    monkeypatch.delattr(bmad_loop, "bmadconfig", raising=False)
    error = harness.story_feed_error(tmp_path)
    assert error is not None
    assert "not importable" in error
