"""Story 9.4's static-JSON-snapshot exporter (``scripts/export_web_snapshot.py``).

Imported directly via ``importlib`` -- the script lives outside the
``pyforge.herald`` package (it is a build-time tool, not shipped
runtime code), so it is not reachable via a normal package import.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "export_web_snapshot.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("export_web_snapshot", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


export_web_snapshot = _load_module()

from pyforge.herald import claims


def _fake_validator(url, **_kwargs):
    return None


def test_export_success_snapshot_writes_only_published_claims(tmp_path):
    repo_root = tmp_path / "repo"
    claims_path = repo_root / claims.DEFAULT_CLAIMS_PATH
    claims.create(claims_path, project_name="draft-one")
    published = claims.create(claims_path, project_name="published-one")
    claims.publish(
        claims_path, published.id, thesis="Shipped", validate=_fake_validator
    )

    out_dir = tmp_path / "out"
    out_path = export_web_snapshot.export_success_snapshot(
        repo_root=repo_root, out_dir=out_dir
    )

    assert out_path == out_dir / "success.json"
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["id"] == published.id
    assert payload[0]["project_name"] == "published-one"


def test_export_success_snapshot_creates_out_dir(tmp_path):
    repo_root = tmp_path / "repo"
    out_dir = tmp_path / "does" / "not" / "exist" / "yet"
    out_path = export_web_snapshot.export_success_snapshot(
        repo_root=repo_root, out_dir=out_dir
    )
    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8")) == []


def test_main_writes_and_prints(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    claims_path = repo_root / claims.DEFAULT_CLAIMS_PATH
    claim = claims.create(claims_path, project_name="warden")
    claims.publish(claims_path, claim.id, thesis="Shipped", validate=_fake_validator)
    out_dir = tmp_path / "out"

    rc = export_web_snapshot.main(
        ["--repo-root", str(repo_root), "--out-dir", str(out_dir)]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert str(out_dir / "success.json") in out
    assert (out_dir / "success.json").exists()
