"""Unit tests for ``cli.upstream.run_upstream`` (Story 6.8, FR-58, AD-2)
against a fake ``FsPort`` double -- no real filesystem."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.cli import upstream as upstream_cli

_ROOT = Path("/fake/repo")
_REGISTER_PATH = (
    _ROOT / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "upstream-register.json"
)

_GOOD_ENTRY = {
    "id": "idle-strand-detection",
    "gap": "no built-in idle detection",
    "workaround": "core/supervise.py's idle ladder",
    "compensating_fr": "FR-12",
    "upstream_status": "open",
}
_LANDED_ENTRY = {
    "id": "non-posix-multiplexer-support",
    "gap": "no Windows multiplexer backend",
    "workaround": "MRS-PREFLIGHT-003 honest detection",
    "compensating_fr": "FR-5",
    "upstream_status": "landed",
    "note": "landed upstream 2026-08-01",
}


class FakeFs:
    def __init__(self, *, texts: dict[Path, str] | None = None, fail_read_text: dict[Path, Exception] | None = None) -> None:
        self.texts: dict[Path, str] = dict(texts or {})
        self.fail_read_text: dict[Path, Exception] = dict(fail_read_text or {})
        self.write_calls: list[Path] = []
        self.symlink_calls: list[Path] = []

    def read_text(self, path: Path) -> str | None:
        if path in self.fail_read_text:
            raise self.fail_read_text[path]
        return self.texts.get(path)

    def write_text_atomic(self, path: Path, content: str) -> None:  # pragma: no cover - must never be called
        self.write_calls.append(path)

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:  # pragma: no cover
        self.symlink_calls.append(path)


def _args(fmt: str = "json") -> argparse.Namespace:
    return argparse.Namespace(format=fmt)


@pytest.fixture(autouse=True)
def _patch_repo_root(monkeypatch):
    monkeypatch.setattr(upstream_cli, "repo_root", lambda: _ROOT)


def _envelope_from(capsys) -> dict:
    out = capsys.readouterr().out
    return json.loads(out)


def test_well_formed_register_round_trips(capsys):
    fs = FakeFs(texts={_REGISTER_PATH: json.dumps({"entries": [_GOOD_ENTRY]})})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert len(envelope["data"]["entries"]) == 1
    assert envelope["data"]["entries"][0]["id"] == "idle-strand-detection"
    assert envelope["data"]["flagged_for_removal"] == []
    assert code == 0


def test_the_real_five_entry_register_content_round_trips(capsys):
    """Reads the ACTUAL tracked register content this story ships,
    round-tripped through a FakeFs (not a real filesystem read) --
    confirms the file this story commits parses cleanly."""
    register_path = (
        Path(__file__).resolve().parents[6]
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / "upstream-register.json"
    )
    if not register_path.is_file():
        pytest.skip("tracked register file not present in this checkout")
    real_text = register_path.read_text(encoding="utf-8")
    fs = FakeFs(texts={_REGISTER_PATH: real_text})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    ids = {entry["id"] for entry in envelope["data"]["entries"]}
    assert ids == {
        "idle-strand-detection",
        "per-story-model-tiering",
        "hardcoded-planning-artifacts-composition",
        "acp-evaluation",
        "non-posix-multiplexer-support",
    }
    assert len(envelope["data"]["flagged_for_removal"]) == 1
    assert envelope["data"]["flagged_for_removal"][0]["id"] == "non-posix-multiplexer-support"
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-002" in codes
    assert "MRS-UPSTREAM-001" not in codes
    assert code == 0


def test_landed_entry_reports_flagged_for_removal_and_warn_finding(capsys):
    fs = FakeFs(texts={_REGISTER_PATH: json.dumps({"entries": [_GOOD_ENTRY, _LANDED_ENTRY]})})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-002" in codes
    flagged = envelope["data"]["flagged_for_removal"]
    assert len(flagged) == 1
    assert flagged[0]["id"] == "non-posix-multiplexer-support"
    assert code == 0


def test_absent_register_reports_empty_with_warn(capsys):
    fs = FakeFs()
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-001" in codes
    assert envelope["data"]["entries"] == []
    assert code == 0


def test_malformed_json_reports_empty_with_warn(capsys):
    fs = FakeFs(texts={_REGISTER_PATH: "{not json"})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-001" in codes
    assert envelope["data"]["entries"] == []
    assert code == 0


def test_unreadable_register_reports_warn_never_crashes(capsys):
    fs = FakeFs(fail_read_text={_REGISTER_PATH: FsError("permission denied")})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-001" in codes
    assert code == 0


def test_one_malformed_entry_others_still_report(capsys):
    incomplete = dict(_GOOD_ENTRY)
    del incomplete["compensating_fr"]
    fs = FakeFs(texts={_REGISTER_PATH: json.dumps({"entries": [incomplete, _LANDED_ENTRY]})})
    code = upstream_cli.run_upstream(_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-UPSTREAM-001" in codes
    ids = {entry["id"] for entry in envelope["data"]["entries"]}
    assert ids == {"non-posix-multiplexer-support"}
    assert code == 0


def test_text_format_renders_flagged_marker(capsys):
    fs = FakeFs(texts={_REGISTER_PATH: json.dumps({"entries": [_GOOD_ENTRY, _LANDED_ENTRY]})})
    upstream_cli.run_upstream(_args(fmt="text"), fs=fs)
    out = capsys.readouterr().out
    assert "upstream contribution register" in out
    assert "[FLAGGED]" in out
    assert "non-posix-multiplexer-support" in out


def test_never_writes_the_register(capsys):
    fs = FakeFs(texts={_REGISTER_PATH: json.dumps({"entries": [_GOOD_ENTRY, _LANDED_ENTRY]})})
    upstream_cli.run_upstream(_args(), fs=fs)
    _envelope_from(capsys)
    assert fs.write_calls == []
    assert fs.symlink_calls == []
