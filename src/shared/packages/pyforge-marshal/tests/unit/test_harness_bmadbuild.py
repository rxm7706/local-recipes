"""Unit tests for ``pyforge.marshal.adapters.harness_bmadbuild`` (Story
22.8, FR-193 CAP-8) -- the impure half of the profile-driven session
harness: binary/fallback probing, the authcheck subprocess, resolution
order + structured skips, and the detached profile-rendered launch. FAKE
BINARIES ONLY (tmp shell scripts on a controlled PATH) -- no test here ever
invokes a real coding-agent CLI.

Story 28.2 (SPEC-marshal-token-economy CAP-2) adds the wire-compression
seam's impure half: probing the ``[wrapper]`` binary, creating the
loop-home-scoped CCR store, and launching THROUGH the wrapper. Same
discipline -- the wrapper under test is an injectable stub (the spec's own
"testable without the real instrument"), never headroom itself: marshal
declares no dependency on it, its availability is exactly the thing that
must be allowed to be absent, and a test that reached for the operator's
own PATH would prove nothing about the degradation path."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
from pyforge.marshal.adapters.harness_bmadbuild import (
    _SPEC_SURFACE_OBLIGATION,
    BmadBuildHarness,
    BuildHarnessError,
)
from pyforge.marshal.ports.build_harness import HarnessResolution

#: Story 28.2: the ENABLED `[context]` wire layer, in exactly the shape
#: `core/policy.py::resolve_context_layers` hands the launch seam.
_WIRE_ON = {"enabled": True, "aggressiveness": "medium"}
_WIRE_OFF = {"enabled": False, "aggressiveness": "medium"}


def _write_script(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_python_script(directory: Path, name: str, body: str) -> Path:
    """A stub executable written in Python rather than ``sh`` -- the wrapper
    stub below needs ``zlib`` for its reversible-store round-trip, which no
    portable shell builtin offers."""
    path = directory / name
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_overlay(repo_root: Path, name: str, text: str) -> Path:
    overlay = repo_root / "_bmad-output" / "harness-profiles"
    overlay.mkdir(parents=True, exist_ok=True)
    path = overlay / f"{name}.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture()
def bare_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A controlled PATH containing only ``bin/`` under tmp -- no real CLI
    can leak into resolution."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    return bin_dir


# --- resolution --------------------------------------------------------------


def test_resolution_skips_missing_binary_then_resolves(
    tmp_path: Path, bare_path: Path
) -> None:
    _write_overlay(
        tmp_path, "one", 'name = "one"\nbinary = "one-cli"\nargv = ["{prompt}"]\n'
    )
    _write_overlay(
        tmp_path, "two", 'name = "two"\nbinary = "two-cli"\nargv = ["{prompt}"]\n'
    )
    _write_script(bare_path, "two-cli", "exit 0")
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("one", "two"), repo_root=tmp_path)
    assert bool(resolution) is True
    assert resolution.profile == "two"
    assert resolution.binary_path == str(bare_path / "two-cli")
    assert [s.profile for s in resolution.skipped] == ["one"]
    assert "not found on PATH" in resolution.skipped[0].reason


def test_resolution_skips_unknown_profile_name(tmp_path: Path, bare_path: Path) -> None:
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("no-such-profile",), repo_root=tmp_path)
    assert not resolution
    assert resolution.skipped[0].profile == "no-such-profile"
    assert "unknown harness profile" in resolution.skipped[0].reason


def test_resolution_authcheck_nonzero_exit_skips(
    tmp_path: Path, bare_path: Path
) -> None:
    _write_overlay(
        tmp_path,
        "authy",
        'name = "authy"\nbinary = "authy-cli"\nargv = ["{prompt}"]\n'
        'authcheck_args = ["status"]\n',
    )
    _write_script(bare_path, "authy-cli", 'echo "Authentication required" >&2\nexit 1')
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("authy",), repo_root=tmp_path)
    assert not resolution
    assert "exited 1" in resolution.skipped[0].reason
    assert "Authentication required" in resolution.skipped[0].reason


def test_resolution_authcheck_pattern_miss_skips_despite_exit_zero(
    tmp_path: Path, bare_path: Path
) -> None:
    """The 2026-08-27 lesson, regression-pinned: cursor's trust prompt and
    gemini's trust refusal both EXIT 0 -- output must confirm, exit code
    alone never suffices."""
    _write_overlay(
        tmp_path,
        "authy",
        'name = "authy"\nbinary = "authy-cli"\nargv = ["{prompt}"]\n'
        'authcheck_args = ["status"]\nauthcheck_ok_pattern = "Logged in as"\n',
    )
    _write_script(bare_path, "authy-cli", 'echo "Not logged in"\nexit 0')
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("authy",), repo_root=tmp_path)
    assert not resolution
    assert "did not confirm login" in resolution.skipped[0].reason


def test_resolution_authcheck_pass_with_pattern(tmp_path: Path, bare_path: Path) -> None:
    _write_overlay(
        tmp_path,
        "authy",
        'name = "authy"\nbinary = "authy-cli"\nargv = ["{prompt}"]\n'
        'authcheck_args = ["status"]\nauthcheck_ok_pattern = "Logged in as"\n',
    )
    _write_script(bare_path, "authy-cli", 'echo "Logged in as someone"\nexit 0')
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("authy",), repo_root=tmp_path)
    assert resolution.profile == "authy"
    assert resolution.skipped == ()


def test_resolution_uses_fallback_bin_dirs(tmp_path: Path, bare_path: Path) -> None:
    """A binary invisible to PATH resolves through the profile's
    repo-root-relative fallback dirs (the pixi-env CLI case)."""
    pixi_bin = tmp_path / "envbin"
    pixi_bin.mkdir()
    _write_script(pixi_bin, "pixi-cli", "exit 0")
    _write_overlay(
        tmp_path,
        "pixied",
        'name = "pixied"\nbinary = "pixi-cli"\nargv = ["{prompt}"]\n'
        'fallback_bin_dirs = ["envbin"]\n',
    )
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("pixied",), repo_root=tmp_path)
    assert resolution.profile == "pixied"
    assert resolution.binary_path == str(pixi_bin / "pixi-cli")


def test_resolution_reports_overlay_load_errors(tmp_path: Path, bare_path: Path) -> None:
    _write_overlay(tmp_path, "broken", "not [ toml")
    harness = BmadBuildHarness()
    resolution = harness.binary_present((), repo_root=tmp_path)
    assert not resolution
    assert len(resolution.profile_errors) == 1
    assert "broken" in resolution.profile_errors[0]


def test_empty_preference_resolves_nothing(tmp_path: Path, bare_path: Path) -> None:
    resolution = BmadBuildHarness().binary_present((), repo_root=tmp_path)
    assert not resolution
    assert resolution.skipped == ()


# --- dispatch launch ---------------------------------------------------------


def _launch_ready_resolution(tmp_path: Path, bare_path: Path) -> HarnessResolution:
    args_file = tmp_path / "seen-args.txt"
    _write_script(
        bare_path,
        "fakecli",
        f'printf \'%s\\n\' "$@" > "{args_file}"\n'
        'echo "session output"\n'
        'echo "PROJ=$BMAD_ACTIVE_PROJECT" ; echo "EXTRA=$FAKE_EXTRA"',
    )
    _write_overlay(
        tmp_path,
        "fakecli",
        'name = "fakecli"\nbinary = "fakecli"\n'
        'argv = ["--flag", "{worktree}", "{model_args}", "{prompt}"]\n'
        'model_args = ["--model", "{model}"]\n'
        'model_map = { opus = "mapped-big" }\n'
        '[env]\nFAKE_EXTRA = "yes"\n',
    )
    return BmadBuildHarness().binary_present(("fakecli",), repo_root=tmp_path)


def test_dispatch_renders_profile_argv_env_and_detaches(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    assert resolution.profile == "fakecli"
    worktree = tmp_path / "wt"
    worktree.mkdir()
    log_path = tmp_path / "session.log"
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="22-8-example",
        spec_path=worktree / "spec.md",
        model="opus",
        budget_env={"MARSHAL_MAX_TOKENS_PER_STORY": "5"},
        log_path=log_path,
    )
    assert result.profile == "fakecli"
    assert result.model == "mapped-big"
    assert result.model_omitted_reason is None
    assert result.command[0] == str(bare_path / "fakecli")
    assert result.command[1:3] == ("--flag", str(worktree))
    assert result.command[3:5] == ("--model", "mapped-big")
    assert "bmad-build-auto" in result.command[5]
    for _ in range(100):
        if (tmp_path / "seen-args.txt").is_file() and log_path.is_file():
            time.sleep(0.05)
            break
        time.sleep(0.05)
    seen = (tmp_path / "seen-args.txt").read_text(encoding="utf-8")
    assert seen.splitlines()[0] == "--flag"
    log_text = log_path.read_text(encoding="utf-8")
    assert "PROJ=pyforge-marshal" in log_text
    assert "EXTRA=yes" in log_text


def test_spec_surface_obligation_states_the_full_s13_7_contract() -> None:
    """Story 53.1 (spec-53-1, CAP-261a), "Always" bullet 4: the prompt text
    is a tested constant asserting the obligation, the co-governor rule, the
    ``--write-baseline`` prohibition, and the ``location:`` rule are all
    present -- a dispatched session never reads ``policy.toml`` and has no
    other way to learn the guard is coming (see the constant's own
    docstring)."""
    from pyforge.marshal.adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND

    assert _SURFACE_RECONCILE_COMMAND in _SPEC_SURFACE_OBLIGATION
    assert ".memlog.md" in _SPEC_SURFACE_OBLIGATION
    assert "co-governor" in _SPEC_SURFACE_OBLIGATION
    assert "--write-baseline" in _SPEC_SURFACE_OBLIGATION
    assert "location:" in _SPEC_SURFACE_OBLIGATION


def test_dispatch_prompt_carries_the_spec_surface_obligation(
    tmp_path: Path, bare_path: Path
) -> None:
    """The obligation constant is not just defined -- it is actually wired
    into the prompt every dispatched session receives (``dispatch()``'s
    ``{prompt}`` argv placeholder, ``result.command[5]`` per the existing
    ``test_dispatch_renders_profile_argv_env_and_detaches`` convention)."""
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="53-1-example",
        spec_path=worktree / "spec.md",
        model="opus",
        budget_env={},
        log_path=tmp_path / "session.log",
    )
    assert _SPEC_SURFACE_OBLIGATION in result.command[5]


def test_dispatch_omitted_model_tier_reports_reason(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="22-8-example",
        spec_path=worktree / "spec.md",
        model="haiku",  # not in fakecli's model_map, no passthrough
        budget_env={},
        log_path=tmp_path / "session.log",
    )
    assert result.model is None
    assert "haiku" in result.model_omitted_reason
    assert "--model" not in result.command


def test_dispatch_refuses_a_falsy_resolution(tmp_path: Path) -> None:
    with pytest.raises(BuildHarnessError, match="no resolved profile"):
        BmadBuildHarness().dispatch(
            tmp_path,
            resolution=HarnessResolution(profile=None),
            project_slug="s",
            story_key="1-1-x",
            spec_path=tmp_path / "spec.md",
            model=None,
            budget_env={},
            log_path=tmp_path / "log",
        )


def test_dispatch_refuses_spec_outside_worktree(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    with pytest.raises(BuildHarnessError, match="not inside dispatch worktree"):
        BmadBuildHarness().dispatch(
            worktree,
            resolution=resolution,
            project_slug="pyforge-marshal",
            story_key="22-8-example",
            spec_path=tmp_path / "outside.md",
            model="opus",
            budget_env={},
            log_path=tmp_path / "session.log",
        )


# --- Story 28.2: the wire-compression seam -----------------------------------

#: The stub wrapper: a *reversible* compressing launcher. It (a) records the
#: argv and env it was handed, (b) does a real compress -> store -> retrieve
#: round-trip through the CCR store directory marshal provisioned for it,
#: writing the verdict where the test can read it, and (c) execs the wrapped
#: CLI it resolves OFF PATH with everything after its own `--` passed through
#: verbatim -- the same contract `headroom wrap <tool> -- <tool args>` has.
_WRAPPER_STUB = '''
import hashlib
import os
import shutil
import sys
import zlib
from pathlib import Path

argv = sys.argv[1:]
store = Path(os.environ["WRAP_STORE"])
store.joinpath("seen-argv.txt").write_text("\\n".join(argv), encoding="utf-8")
store.joinpath("seen-env.txt").write_text(
    "WRAP_MODE=%s\\nSTORE=%s\\nPROJ=%s"
    % (
        os.environ.get("WRAP_MODE", ""),
        os.environ["WRAP_STORE"],
        os.environ.get("BMAD_ACTIVE_PROJECT", ""),
    ),
    encoding="utf-8",
)

# The reversible half, exercised against the store marshal handed us: a
# FATAL line (the spec's own worked example of what must never be lost)
# compressed in, retrieved out, compared byte for byte.
original = b"FATAL: assertion failed at line 42 \\xf0\\x9f\\x92\\xa5\\n" * 64
digest = hashlib.sha256(original).hexdigest()
blob = store / (digest + ".z")
blob.write_bytes(zlib.compress(original, 9))
retrieved = zlib.decompress(blob.read_bytes())
store.joinpath("roundtrip.txt").write_text(
    ("EXACT" if retrieved == original else "LOSSY")
    + "\\ncompressed=%d original=%d" % (blob.stat().st_size, len(original)),
    encoding="utf-8",
)

# ... then launch the wrapped tool, exactly as `headroom wrap <tool> --` does.
tool = argv[1]
tail = argv[argv.index("--") + 1 :]
os.execv(shutil.which(tool), [tool, *tail])
'''

_WRAPPED_PROFILE_TOML = (
    'name = "fakecli"\nbinary = "fakecli"\n'
    'argv = ["--flag", "{worktree}", "{model_args}", "{prompt}"]\n'
    'model_args = ["--model", "{model}"]\n'
    'model_map = { opus = "mapped-big" }\n'
    "[wrapper]\n"
    'binary = "wrapcli"\n'
    'argv = ["wrap", "fakecli", "--"]\n'
    'store_env = "WRAP_STORE"\n'
    'store_relpath = ".marshal/wire"\n'
    "reversible = true\n"
    '[wrapper.env]\nWRAP_MODE = "cache"\n'
)


def _wired_resolution(
    tmp_path: Path,
    bare_path: Path,
    *,
    profile_toml: str = _WRAPPED_PROFILE_TOML,
    with_wrapper: bool = True,
) -> HarnessResolution:
    _write_script(
        bare_path,
        "fakecli",
        'echo "session output" ; echo "PROJ=$BMAD_ACTIVE_PROJECT"',
    )
    if with_wrapper:
        _write_python_script(bare_path, "wrapcli", _WRAPPER_STUB)
    _write_overlay(tmp_path, "fakecli", profile_toml)
    return BmadBuildHarness().binary_present(("fakecli",), repo_root=tmp_path)


def _await_file(path: Path, *, tries: int = 200) -> str:
    for _ in range(tries):
        if path.is_file():
            time.sleep(0.05)
            return path.read_text(encoding="utf-8")
        time.sleep(0.05)
    raise AssertionError(f"{path} never appeared")


def test_binary_present_resolves_the_wrapper_binary(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _wired_resolution(tmp_path, bare_path)
    assert resolution.profile == "fakecli"
    assert resolution.wrapper_binary_path == str(bare_path / "wrapcli")


def test_an_unresolvable_wrapper_never_disqualifies_the_profile(
    tmp_path: Path, bare_path: Path
) -> None:
    """Graceful degradation is per LAYER, never per candidate: a missing
    wrapper turns the wire layer off, it does not make an otherwise
    dispatchable profile un-dispatchable."""
    resolution = _wired_resolution(tmp_path, bare_path, with_wrapper=False)
    assert bool(resolution) is True
    assert resolution.profile == "fakecli"
    assert resolution.wrapper_binary_path is None
    assert resolution.skipped == ()


def test_wrapper_resolves_through_its_own_fallback_bin_dirs(
    tmp_path: Path, bare_path: Path
) -> None:
    """The wrapper probes through the IDENTICAL PATH-then-repo-root-relative
    resolution the profile's own binary does (the pixi-env case: headroom
    lives in `.pixi/envs/local-recipes/bin`, invisible to a bare operator
    PATH)."""
    envbin = tmp_path / "envbin"
    envbin.mkdir()
    _write_python_script(envbin, "wrapcli", _WRAPPER_STUB)
    resolution = _wired_resolution(
        tmp_path,
        bare_path,
        with_wrapper=False,
        profile_toml=_WRAPPED_PROFILE_TOML.replace(
            'argv = ["wrap", "fakecli", "--"]\n',
            'argv = ["wrap", "fakecli", "--"]\nfallback_bin_dirs = ["envbin"]\n',
        ),
    )
    assert resolution.wrapper_binary_path == str(envbin / "wrapcli")


def test_dispatch_wraps_the_launch_and_scopes_the_store_to_the_worktree(
    tmp_path: Path, bare_path: Path
) -> None:
    """CAP-2's first AC end to end on the engine that owns this seam: an
    enabled wire layer -> the launched command is DEMONSTRABLY wrapped
    (profile-resolved wrapper first in argv, reported on the result for the
    caller to journal) and the CCR store lives inside the loop home."""
    resolution = _wired_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model="opus",
        budget_env={},
        log_path=tmp_path / "session.log",
        wire_layer=_WIRE_ON,
    )
    store = worktree / ".marshal" / "wire"
    assert result.wire is not None and result.wire.applied is True
    assert result.wire.reason is None
    assert result.wire.store_dir == str(store)
    assert result.wire.aggressiveness == "medium"
    # the store is provisioned BY the launch, inside the worktree that is
    # torn down with the story -- never a user-global cache
    assert store.is_dir() and store.is_relative_to(worktree)
    # ...and the argv really is the wrapper's, not the CLI's
    assert result.command[:4] == (
        str(bare_path / "wrapcli"),
        "wrap",
        "fakecli",
        "--",
    )
    # the child process saw the wrapper's declared env AND the store pin
    seen_env = _await_file(store / "seen-env.txt")
    assert f"STORE={store}" in seen_env
    assert "WRAP_MODE=cache" in seen_env
    # ...without the wrapper's env displacing marshal's per-invocation pin
    assert "PROJ=pyforge-marshal" in seen_env
    # and the wrapped CLI actually ran underneath it
    assert "session output" in _await_file(tmp_path / "session.log")


def test_dispatch_ccr_store_round_trip_is_byte_exact(
    tmp_path: Path, bare_path: Path
) -> None:
    """CAP-2's second AC ("a compressed artifact is retrievable byte-exact")
    proven at the seam marshal owns: the store directory marshal hands the
    wrapper is a real, writable directory in which a compress -> retrieve
    round-trip returns the ORIGINAL bytes -- a FATAL line included, which is
    the spec's own worked example of what silently-lossy compression must
    never eat. The compression itself is the stub's (marshal does not
    compress anything); what is under test is that marshal provisions a
    store a reversible wrapper can actually be reversible in."""
    resolution = _wired_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
        wire_layer=_WIRE_ON,
    )
    verdict = _await_file(worktree / ".marshal" / "wire" / "roundtrip.txt")
    assert verdict.startswith("EXACT")
    # ...and it really was compressed, not stored verbatim -- otherwise
    # "byte-exact retrieval" would be a tautology about a copy.
    compressed, original = (
        int(field.split("=")[1]) for field in verdict.split("\n")[1].split(" ")
    )
    assert compressed < original


def test_wrapped_launch_tail_is_byte_identical_to_the_unwrapped_one(
    tmp_path: Path, bare_path: Path
) -> None:
    """CAP-2's third AC at the launch seam (the pure-render half is pinned in
    ``test_harness_profile.py``): identical inputs, wrapped vs unwrapped ->
    everything marshal composed, prompt included, crosses byte-identically.
    Only a launcher prefix is prepended."""
    resolution = _wired_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()

    def _launch(wire_layer):
        return BmadBuildHarness().dispatch(
            worktree,
            resolution=resolution,
            project_slug="pyforge-marshal",
            story_key="28-2-example",
            spec_path=worktree / "spec.md",
            model="opus",
            budget_env={},
            log_path=tmp_path / f"session-{wire_layer['enabled']}.log",
            wire_layer=wire_layer,
        )

    off = _launch(_WIRE_OFF)
    on = _launch(_WIRE_ON)
    prefix = on.wire.argv_prefix
    assert [arg.encode("utf-8") for arg in on.command[len(prefix) :]] == [
        arg.encode("utf-8") for arg in off.command[1:]
    ]
    # the OFF launch is untouched by 28.2 in every respect
    assert off.command[0] == str(bare_path / "fakecli")
    assert off.wire is not None and off.wire.applied is False
    assert off.wire.reason is None  # nothing enabled, nothing to report


def test_dispatch_without_a_wire_layer_is_byte_identical_to_pre_28_2(
    tmp_path: Path, bare_path: Path
) -> None:
    """The default call shape (``wire_layer`` omitted entirely) still
    launches bare -- the parameter is optional so every existing caller and
    the whole pre-28.2 behavior survive untouched."""
    resolution = _wired_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
    )
    assert result.command[0] == str(bare_path / "fakecli")
    assert result.wire is not None and result.wire.applied is False
    assert not (worktree / ".marshal").exists()


def test_dispatch_degrades_when_the_wrapper_binary_is_absent(
    tmp_path: Path, bare_path: Path
) -> None:
    """CAP-2's fourth AC: instrument unavailable -> the layer disables with
    a NAMED reason and the run proceeds UNWRAPPED. Never a blocked run
    (a real pid comes back), never a silent no-op (the reason is there for
    the caller's MRS-DISP-033)."""
    resolution = _wired_resolution(tmp_path, bare_path, with_wrapper=False)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
        wire_layer=_WIRE_ON,
    )
    assert result.pid > 0
    assert result.command[0] == str(bare_path / "fakecli")
    assert result.wire is not None and result.wire.applied is False
    assert "wrapcli" in result.wire.reason and "did not resolve" in result.wire.reason
    assert result.wire.aggressiveness == "medium"
    assert not (worktree / ".marshal").exists()


def test_dispatch_degrades_when_the_profile_declares_no_wrapper(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
        wire_layer=_WIRE_ON,
    )
    assert result.pid > 0
    assert result.wire is not None and result.wire.applied is False
    assert "declares no [wrapper]" in result.wire.reason


def test_dispatch_degrades_when_the_ccr_store_cannot_be_created(
    tmp_path: Path, bare_path: Path
) -> None:
    """Reversible-or-absent, enforced at the last moment it still can be: a
    store the wrapper cannot write to would make its compression
    irreversible, so an uncreatable store turns the layer OFF rather than
    launching a wrapper into it. Modelled by a plain FILE squatting on the
    store path -- ``mkdir(parents=True)`` raises ``FileExistsError``."""
    resolution = _wired_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".marshal").mkdir()
    (worktree / ".marshal" / "wire").write_text("not a directory", encoding="utf-8")
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
        wire_layer=_WIRE_ON,
    )
    assert result.pid > 0
    assert result.command[0] == str(bare_path / "fakecli")
    assert result.wire is not None and result.wire.applied is False
    assert "could not be created" in result.wire.reason
    # and no store env var leaked into a launch that is not using one
    assert result.wire.store_dir is None


def test_wrapped_launch_keeps_a_fallback_dir_cli_reachable(
    tmp_path: Path, bare_path: Path
) -> None:
    """Wrapping replaces the resolved CLI PATH with the wrapper's, and the
    wrapper then resolves the CLI itself off PATH. A CLI that only lives in
    a profile ``fallback_bin_dirs`` entry -- the pixi-env case this repo
    actually runs on -- would vanish at that point, so the launch prepends
    its directory: exactly the reachability the unwrapped launch already
    had, and nothing more."""
    envbin = tmp_path / "envbin"
    envbin.mkdir()
    _write_script(envbin, "fakecli", 'echo "session output from the fallback dir"')
    _write_python_script(bare_path, "wrapcli", _WRAPPER_STUB)
    _write_overlay(
        tmp_path,
        "fakecli",
        _WRAPPED_PROFILE_TOML.replace(
            'model_map = { opus = "mapped-big" }\n',
            'model_map = { opus = "mapped-big" }\nfallback_bin_dirs = ["envbin"]\n',
        ),
    )
    resolution = BmadBuildHarness().binary_present(("fakecli",), repo_root=tmp_path)
    assert resolution.binary_path == str(envbin / "fakecli")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="28-2-example",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "session.log",
        wire_layer=_WIRE_ON,
    )
    assert "session output from the fallback dir" in _await_file(
        tmp_path / "session.log"
    )


def test_dispatch_child_survives_via_new_session(
    tmp_path: Path, bare_path: Path
) -> None:
    """The detach decision, pinned: Popen with start_new_session -- the
    returned pid IS the session process (no CLI self-backgrounding
    double-detach), so the dispatch supervisor's liveness probe is
    meaningful."""
    _write_script(bare_path, "sleeper", "sleep 5")
    _write_overlay(
        tmp_path,
        "sleeper",
        'name = "sleeper"\nbinary = "sleeper"\nargv = ["{prompt}"]\n',
    )
    resolution = BmadBuildHarness().binary_present(("sleeper",), repo_root=tmp_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    log_path = tmp_path / "log"
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="s",
        story_key="1-1-x",
        spec_path=worktree / "spec.md",
        model=None,
        budget_env={},
        log_path=log_path,
    )
    # pid alive and in its own session (detached from this test process).
    # Seen reaped once in ~9 CI runs (retro-pyforge-steward-2026-09-04.md
    # action item 6) with no diagnostic beyond the bare ProcessLookupError --
    # the dispatch log (child stdout+stderr, per dispatch()'s log_file
    # redirect) is captured into the failure message so a repeat is
    # debuggable instead of a second blind traceback.
    try:
        os.kill(result.pid, 0)
    except ProcessLookupError:
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else "<no log file>"
        pytest.fail(
            f"dispatched pid {result.pid} was already gone when probed "
            f"(reaped before the liveness check) -- dispatch log:\n{log_text}"
        )
    assert os.getsid(result.pid) != os.getsid(0)
    os.kill(result.pid, 15)
