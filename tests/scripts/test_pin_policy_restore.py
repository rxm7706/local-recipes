"""Tests for scripts/pin_policy_restore.py (Story 100.1 / CAP-167)."""
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pin_policy"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pin_policy_lib as lib  # noqa: E402
import pin_policy_restore as restore_mod  # noqa: E402


def test_restore_rewrites_and_recover_on_lock_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    policy_src = FIXTURES / "pin-policy.yaml"
    policy = lib.load_policy(policy_src)
    base = (FIXTURES / "pixi.toml.base").read_text(encoding="utf-8")
    after = (FIXTURES / "pixi.toml.after").read_text(encoding="utf-8")
    (tmp_path / "docs/governance").mkdir(parents=True)
    import yaml

    (tmp_path / "docs/governance/pin-policy.yaml").write_text(
        yaml.dump(policy), encoding="utf-8"
    )
    manifest = tmp_path / "pixi.toml"
    manifest.write_text(after, encoding="utf-8")
    original = manifest.read_bytes()

    def fake_read(ref: str, root: Path = REPO_ROOT) -> tuple[dict | None, str | None]:
        return tomllib.loads(base), None

    monkeypatch.setattr(lib, "_read_manifest_at_ref", fake_read)
    monkeypatch.setattr(
        sys,
        "argv",
        ["pin-policy-restore", "--from", "base", "--root", str(tmp_path)],
    )

    monkeypatch.setattr(restore_mod, "check_static", lambda *a, **k: [])
    with mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0)):
        rc = restore_mod.main()
    assert rc == 0
    text = manifest.read_text(encoding="utf-8")
    assert "<3" in text
    assert "channel = \"conda-forge\"" in text or 'channel = "conda-forge"' in text

    manifest.write_bytes(original)
    monkeypatch.setattr(
        sys,
        "argv",
        ["pin-policy-restore", "--from", "base", "--root", str(tmp_path)],
    )
    with mock.patch.object(
        subprocess,
        "run",
        return_value=mock.Mock(returncode=1, stderr="unsolvable", stdout=""),
    ):
        rc_fail = restore_mod.main()
    assert rc_fail == 1
    assert manifest.read_bytes() == original
