"""Conformance — ``warden scan --doctor`` end-to-end (Story 5.1, D8).

Real ``cli.main(["scan", ..., "--doctor"])`` invocations against the
provisioned pyforge-warden environment (real deptry/osv-scanner binaries,
the real ambient offline OSV DB + KEV/endoflife feed caches
``tests/conftest.py`` provisions once per session) — both ``--format``
values, and proof that ``--doctor`` performs NO discovery/extraction/
policy work (a manifest dropped under the target is never even read; the
real ``discover()`` seam is never called).
"""

from __future__ import annotations

import json

from pyforge.warden import cli as cli_module
from pyforge.warden.cli import main


def test_doctor_real_environment_is_healthy_end_to_end(capsys, tmp_path):
    """Against the REAL provisioned pyforge-warden pixi environment (real
    deptry/osv-scanner binaries within their tested version ranges, the
    real ambient offline OSV DB ``tests/conftest.py`` builds once per
    session) — ``warden scan --doctor`` exits 0 and reports every check
    ``ok``, with zero network (the autouse socket-deny harness would raise
    otherwise — this is the same live proof ``test_scan_harness.py`` gives
    a real scan, one level over)."""
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    lines = captured.out.splitlines()
    assert lines[0] == "warden: doctor status=ok checks=5"
    assert len(lines) == 6  # header + 5 checks
    for line in lines[1:]:
        assert " ok -- " in line
    assert captured.err == ""


def test_doctor_real_environment_format_json(capsys, tmp_path):
    rc = main(["scan", str(tmp_path), "--doctor", "--format", "json"])
    captured = capsys.readouterr()
    assert rc == 0
    document = json.loads(captured.out)
    assert document["status"] == "ok"
    assert len(document["checks"]) == 5
    assert all(check["ok"] is True for check in document["checks"])


def test_doctor_performs_no_discovery_extraction_or_policy_work(capsys, tmp_path):
    """A real, perfectly valid manifest naming a genuinely-missing package
    is dropped under the target — a real scan of it would compose
    ``policy-violation`` (DEP001) end to end (mirrors ``test_scan_harness.
    py``'s own ``test_deptry_missing_dependency_blocks_by_default``).
    ``--doctor`` must never read it: none of that manifest's content, nor
    any report/policy vocabulary (axis tags, a ``findings=`` count), reach
    the doctor output — it is an environment check, not a project scan."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\n'
        'dependencies = ["totally-absent-pkg-xyz"]\n',
        encoding="utf-8",
    )
    rc = main(["scan", str(tmp_path), "--doctor"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "totally-absent-pkg-xyz" not in captured.out
    assert "DEP001" not in captured.out
    assert "findings=" not in captured.out
    assert "[hygiene]" not in captured.out
    assert "[vulnerability]" not in captured.out


def test_doctor_never_calls_the_discovery_seam(monkeypatch, capsys, tmp_path):
    """Structural proof (not just output absence): ``_run_doctor`` never
    calls ``discovery.discover`` at all — a real scan's own first
    pipeline step."""

    def _boom(*args, **kwargs):
        raise AssertionError("--doctor must never call discover()")

    monkeypatch.setattr(cli_module, "discover", _boom)
    rc = main(["scan", str(tmp_path), "--doctor"])
    capsys.readouterr()
    assert rc == 0  # _boom never fired
