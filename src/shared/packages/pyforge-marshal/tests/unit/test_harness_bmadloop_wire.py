"""Regression coverage for ``attempt_spin_wire_layer``'s wire-port
substitution (live bug, 2026-09-10).

``attempt_spin_wire_layer`` (Story 33.3) writes a bmad-loop adapter profile
overlay whose ``launch_args`` come from a harness profile's own
``[wrapper].argv`` -- for ``claude.toml`` that includes the literal
``{wire_port}`` placeholder token. Before this fix, the overlay writer
copied that argv verbatim, so headroom received the string ``'{wire_port}'``
as its own ``--port`` value and refused every launch (``Error: Invalid
value for '--port'``) -- reproduced live: a real ``marshal factory spin
pyforge-marshal`` run deferred every one of 4 attempted stories with 'dev
session crashed' inside ~13 seconds each, and the dev-session log showed
exactly this headroom refusal.

No prior test exercised ``attempt_spin_wire_layer`` at all (a real gap this
finding also closes)."""

from __future__ import annotations

import pytest

import pyforge.marshal.adapters.harness_bmadloop as module
from pyforge.marshal.core.harness_profile import wire_port_for_worktree


def test_attempt_spin_wire_layer_never_writes_the_raw_wire_port_token(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda binary: "/usr/bin/headroom" if binary == "headroom" else None,
    )
    loop_home = tmp_path / "loop-home"
    loop_home.mkdir()

    wire = module.attempt_spin_wire_layer(
        loop_home=loop_home,
        adapter_name="claude",
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        repo_root=None,
    )

    assert wire.applied is True, wire.reason
    overlay_path = loop_home / ".bmad-loop" / "profiles" / "claude.toml"
    assert overlay_path.is_file()
    text = overlay_path.read_text(encoding="utf-8")
    assert "{wire_port}" not in text, "the raw template token reached the written overlay"
    assert "--port" in text


def test_attempt_spin_wire_layer_writes_a_real_deterministic_port(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The substituted port must be the SAME deterministic derivation
    dispatch's own ``render_dispatch_argv`` uses (Story 33.8) -- not an
    arbitrary or random value."""
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda binary: "/usr/bin/headroom" if binary == "headroom" else None,
    )
    loop_home = tmp_path / "loop-home"
    loop_home.mkdir()
    expected_port = wire_port_for_worktree(loop_home)

    module.attempt_spin_wire_layer(
        loop_home=loop_home,
        adapter_name="claude",
        wire_layer={"enabled": True, "aggressiveness": "medium"},
        repo_root=None,
    )

    overlay_path = loop_home / ".bmad-loop" / "profiles" / "claude.toml"
    text = overlay_path.read_text(encoding="utf-8")
    assert f'"{expected_port}"' in text or f"'{expected_port}'" in text, text


def test_attempt_spin_wire_layer_auto_with_no_resolvable_profile_is_a_clean_skip(
    tmp_path,
) -> None:
    """Story 46.4: an adapter with no ``PROFILE_BY_BMADLOOP_ADAPTER`` entry
    has no marshal harness profile to read a ``[wrapper]`` fact from, so
    ``"auto"`` resolves to ``False`` via ``resolve_wire_enabled`` -- a clean
    skip, not the WARN-class degraded reason this branch returns for an
    explicit ``enabled=True``."""
    loop_home = tmp_path / "loop-home"
    loop_home.mkdir()

    wire = module.attempt_spin_wire_layer(
        loop_home=loop_home,
        adapter_name="unknown-adapter",
        wire_layer={"enabled": "auto", "aggressiveness": "medium"},
        repo_root=None,
    )

    assert wire.applied is False
    assert wire.reason is None


def test_attempt_spin_wire_layer_auto_with_unresolvable_packaged_profile_is_a_clean_skip(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 46.4: ``PROFILE_BY_BMADLOOP_ADAPTER`` resolves ``adapter_name``
    to a profile stem, but that stem is absent from
    ``load_packaged_profiles()`` -- the second, distinct fallback branch
    ``attempt_spin_wire_layer`` falls through to. ``"auto"`` must resolve
    the same clean-skip way here as it does when no adapter mapping exists
    at all."""
    monkeypatch.setattr(module, "load_packaged_profiles", dict)
    loop_home = tmp_path / "loop-home"
    loop_home.mkdir()

    wire = module.attempt_spin_wire_layer(
        loop_home=loop_home,
        adapter_name="claude",
        wire_layer={"enabled": "auto", "aggressiveness": "medium"},
        repo_root=None,
    )

    assert wire.applied is False
    assert wire.reason is None
