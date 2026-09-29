"""Unit tests for Story 28.7 index freshness (CAP-10).

Covers the detector script and the marshal-check front door: named advisory
MRS-IDXF-* findings, layer-off silence, and WARN-only exit domain.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

from pyforge.core.process import ProcessResult

import pyforge.marshal
from pyforge.marshal.cli import check as check_cli
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.verdict import Verdict, classify, compute_verdict, exit_code_for
from pyforge.marshal.seed.model.kit import CODEGRAPH_INDEX_RELPATH

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
REPO_ROOT = Path(_PACKAGE_FILE).resolve().parents[7]
CHECKER = REPO_ROOT / "scripts" / "index_freshness_check.py"
DETECTORS = REPO_ROOT / "scripts" / "detectors.py"


def _load_checker(monkeypatch, loop_root: Path):
    """Import index_freshness_check with LOOP_ROOT bound to ``loop_root``."""
    src = CHECKER.read_text(encoding="utf-8").replace(
        'LOOP_ROOT = Path.home() / ".bmad-loops"',
        f"LOOP_ROOT = Path({str(loop_root)!r})",
    )
    mod_path = loop_root / "_index_freshness_under_test.py"
    mod_path.parent.mkdir(parents=True, exist_ok=True)
    mod_path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("index_freshness_under_test", mod_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["index_freshness_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return p.stdout.strip()


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(path), "config", k, v], check=True)


def _loop_home(tmp_path: Path, name: str, *, policy_toml: str) -> Path:
    home = tmp_path / name
    home.mkdir(parents=True)
    _init_repo(home)
    loop_dir = home / ".bmad-loop"
    loop_dir.mkdir()
    (loop_dir / "policy.toml").write_text(policy_toml, encoding="utf-8")
    return home


def test_detector_uses_kit_and_scribe_canonical_index_paths():
    """Index paths must match Story 28.3 kit + Scribe cocoindex seam."""
    src = CHECKER.read_text(encoding="utf-8")
    assert CODEGRAPH_INDEX_RELPATH in src
    assert ".claude/data/pyforge-scribe/cocoindex-index.json" in src
    assert ".codegraph/index" not in src
    assert ".cocoindex/index" not in src


def test_layer_off_raises_no_staleness_finding(tmp_path, monkeypatch):
    mod = _load_checker(monkeypatch, tmp_path)
    _loop_home(
        tmp_path,
        "home-off",
        policy_toml=("[context.structure-graph]\nenabled = false\n[context.derived-context]\nenabled = false\n"),
    )
    checks = mod.check_home(tmp_path / "home-off")
    assert all(c.status == "layer-off" for c in checks)


def test_missing_codegraph_in_enabled_layer_is_mrs_idxf_001(tmp_path, monkeypatch):
    mod = _load_checker(monkeypatch, tmp_path)
    _loop_home(
        tmp_path,
        "home-missing",
        policy_toml="[context.structure-graph]\nenabled = true\n",
    )
    checks = mod.check_home(tmp_path / "home-missing")
    codegraph = next(c for c in checks if c.index_name == "codegraph")
    assert codegraph.status == "missing"


def test_stale_codegraph_is_mrs_idxf_002(tmp_path, monkeypatch):
    mod = _load_checker(monkeypatch, tmp_path)
    home = _loop_home(
        tmp_path,
        "home-stale",
        policy_toml="[context.structure-graph]\nenabled = true\n",
    )
    index_file = home / ".codegraph" / "codegraph.db"
    index_file.parent.mkdir(parents=True)
    index_file.write_text("old\n", encoding="utf-8")
    old = int(time.time()) - 3600
    import os

    os.utime(index_file, (old, old))
    (home / "tracked.txt").write_text("new commit\n", encoding="utf-8")
    _git(home, "add", "-A")
    _git(home, "commit", "-qm", "after index")

    checks = mod.check_home(home)
    codegraph = next(c for c in checks if c.index_name == "codegraph")
    assert codegraph.status == "stale"


def test_missing_cocoindex_in_enabled_layer_is_mrs_idxf_003(tmp_path, monkeypatch):
    mod = _load_checker(monkeypatch, tmp_path)
    _loop_home(
        tmp_path,
        "home-coco-missing",
        policy_toml="[context.derived-context]\nenabled = true\n",
    )
    checks = mod.check_home(tmp_path / "home-coco-missing")
    coco = next(c for c in checks if c.index_name == "cocoindex")
    assert coco.status == "missing"


def test_stale_cocoindex_is_mrs_idxf_004(tmp_path, monkeypatch):
    mod = _load_checker(monkeypatch, tmp_path)
    home = _loop_home(
        tmp_path,
        "home-coco-stale",
        policy_toml="[context.derived-context]\nenabled = true\n",
    )
    index_file = home / ".claude" / "data" / "pyforge-scribe" / "cocoindex-index.json"
    index_file.parent.mkdir(parents=True)
    index_file.write_text("{}\n", encoding="utf-8")
    old = int(time.time()) - 3600
    import os

    os.utime(index_file, (old, old))
    (home / "tracked.txt").write_text("new commit\n", encoding="utf-8")
    _git(home, "add", "-A")
    _git(home, "commit", "-qm", "after cocoindex")

    checks = mod.check_home(home)
    coco = next(c for c in checks if c.index_name == "cocoindex")
    assert coco.status == "stale"


def test_json_output_carries_structured_findings(tmp_path, monkeypatch, capsys):
    mod = _load_checker(monkeypatch, tmp_path)
    _loop_home(
        tmp_path,
        "home-json",
        policy_toml="[context.structure-graph]\nenabled = true\n",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["index_freshness_check.py", "--json"],
    )
    rc = mod.main()
    assert rc == 1
    lines = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines()]
    findings_line = next(ln for ln in lines if "_findings" in ln)
    assert findings_line["_findings"][0]["code"] == "MRS-IDXF-001"


def test_json_output_stale_codegraph_emits_mrs_idxf_002(tmp_path, monkeypatch, capsys):
    mod = _load_checker(monkeypatch, tmp_path)
    home = _loop_home(
        tmp_path,
        "home-json-stale",
        policy_toml="[context.structure-graph]\nenabled = true\n",
    )
    index_file = home / ".codegraph" / "codegraph.db"
    index_file.parent.mkdir(parents=True)
    index_file.write_text("old\n", encoding="utf-8")
    old = int(time.time()) - 3600
    import os

    os.utime(index_file, (old, old))
    (home / "tracked.txt").write_text("new commit\n", encoding="utf-8")
    _git(home, "add", "-A")
    _git(home, "commit", "-qm", "after index")

    monkeypatch.setattr(sys, "argv", ["index_freshness_check.py", "--json"])
    rc = mod.main()
    assert rc == 1
    lines = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines()]
    findings_line = next(ln for ln in lines if "_findings" in ln)
    assert findings_line["_findings"][0]["code"] == "MRS-IDXF-002"


def test_json_output_missing_cocoindex_emits_mrs_idxf_003(tmp_path, monkeypatch, capsys):
    mod = _load_checker(monkeypatch, tmp_path)
    _loop_home(
        tmp_path,
        "home-json-coco",
        policy_toml="[context.derived-context]\nenabled = true\n",
    )
    monkeypatch.setattr(sys, "argv", ["index_freshness_check.py", "--json"])
    rc = mod.main()
    assert rc == 1
    lines = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines()]
    findings_line = next(ln for ln in lines if "_findings" in ln)
    codes = {f["code"] for f in findings_line["_findings"]}
    assert "MRS-IDXF-003" in codes


def test_json_output_stale_cocoindex_emits_mrs_idxf_004(tmp_path, monkeypatch, capsys):
    mod = _load_checker(monkeypatch, tmp_path)
    home = _loop_home(
        tmp_path,
        "home-json-coco-stale",
        policy_toml="[context.derived-context]\nenabled = true\n",
    )
    index_file = home / ".claude" / "data" / "pyforge-scribe" / "cocoindex-index.json"
    index_file.parent.mkdir(parents=True)
    index_file.write_text("{}\n", encoding="utf-8")
    old = int(time.time()) - 3600
    import os

    os.utime(index_file, (old, old))
    (home / "tracked.txt").write_text("new commit\n", encoding="utf-8")
    _git(home, "add", "-A")
    _git(home, "commit", "-qm", "after cocoindex")

    monkeypatch.setattr(sys, "argv", ["index_freshness_check.py", "--json"])
    rc = mod.main()
    assert rc == 1
    lines = [json.loads(ln) for ln in capsys.readouterr().out.strip().splitlines()]
    findings_line = next(ln for ln in lines if "_findings" in ln)
    assert findings_line["_findings"][0]["code"] == "MRS-IDXF-004"


def test_layer_off_main_emits_no_findings_json(tmp_path, monkeypatch, capsys):
    mod = _load_checker(monkeypatch, tmp_path)
    _loop_home(
        tmp_path,
        "home-off-json",
        policy_toml=("[context.structure-graph]\nenabled = false\n[context.derived-context]\nenabled = false\n"),
    )
    monkeypatch.setattr(sys, "argv", ["index_freshness_check.py", "--json"])
    rc = mod.main()
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out
    assert "_findings" not in out
    for line in out.splitlines():
        payload = json.loads(line)
        assert "status" not in payload or payload.get("status") == "layer-off"


def test_git_unavailable_does_not_emit_staleness_finding(tmp_path, monkeypatch):
    mod = _load_checker(monkeypatch, tmp_path)
    home = _loop_home(
        tmp_path,
        "home-no-git-ts",
        policy_toml="[context.structure-graph]\nenabled = true\n",
    )
    index_file = home / ".codegraph" / "codegraph.db"
    index_file.parent.mkdir(parents=True)
    index_file.write_text("old\n", encoding="utf-8")
    old = int(time.time()) - 3600
    import os

    os.utime(index_file, (old, old))
    monkeypatch.setattr(mod, "head_commit_timestamp", lambda _repo: None)
    status, reason = mod.check_index_freshness(home, ".codegraph/codegraph.db", "codegraph")
    assert status == "ok"
    assert "freshness not evaluated" in reason


def test_mrs_idxf_codes_classify_warn_only():
    for code in ("MRS-IDXF-001", "MRS-IDXF-002", "MRS-IDXF-003", "MRS-IDXF-004"):
        assert classify(code) is Verdict.WARN


def test_advisory_findings_alone_never_block_exit_domain():
    findings = (Finding(code="MRS-IDXF-002", severity=Severity.WARN, message="stale codegraph"),)
    verdict = compute_verdict(findings)
    assert verdict is Verdict.WARN
    assert exit_code_for(verdict) == 0


class _FakeProcess:
    def __init__(self, *, run_result: ProcessResult) -> None:
        self.run_result = run_result

    def run(self, argv, *, cwd, timeout_s=None):
        return self.run_result


def test_marshal_check_surfaces_structured_idxf_not_check_002(capsys):
    structured = [
        {
            "code": "MRS-IDXF-002",
            "message": "the codegraph index predates HEAD",
        }
    ]
    process = _FakeProcess(
        run_result=ProcessResult(
            returncode=1,
            stdout=json.dumps(
                {
                    "registry": [],
                    "results": [
                        {
                            "path": "scripts/index_freshness_check.py",
                            "name": "index_freshness_check",
                            "scope": "runtime",
                            "task": "index-freshness-check",
                            "rc": 1,
                            "status": "FINDINGS",
                            "secs": 0.1,
                            "summary": "stale",
                            "structured_findings": structured,
                        }
                    ],
                }
            ),
            stderr="",
        )
    )
    exit_code = check_cli.run_check(argparse.Namespace(scope="all", project=None, format="json"), process=process)
    payload = json.loads(capsys.readouterr().out)
    codes = [f["code"] for f in payload["findings"]]
    assert codes == ["MRS-IDXF-002"]
    assert "MRS-CHECK-002" not in codes
    assert payload["verdict"] == "warn"
    assert exit_code == 0


def test_detectors_parse_structured_findings_from_json_output():
    spec = importlib.util.spec_from_file_location("detectors_under_test", DETECTORS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    out = (
        json.dumps(
            {
                "home_name": "h",
                "index_name": "codegraph",
                "index_path": ".codegraph/codegraph.db",
                "status": "missing",
                "reason": "x",
            }
        )
        + "\n"
        + json.dumps(
            {
                "_findings": [
                    {
                        "code": "MRS-IDXF-001",
                        "home": "h",
                        "index": "codegraph",
                        "message": "no index",
                    }
                ]
            }
        )
        + "\n"
    )
    parsed = mod._structured_findings_from_output("index_freshness_check", out)
    assert parsed == [{"code": "MRS-IDXF-001", "message": "[h] no index"}]
    assert mod._structured_findings_from_output("other_check", out) == []


def test_run_one_index_freshness_check_wires_json_and_structured_findings(tmp_path, monkeypatch):
    """Exercise detectors.run_one subprocess + --json + structured_findings parse."""
    _load_checker(monkeypatch, tmp_path)
    patched_script = tmp_path / "_index_freshness_under_test.py"
    _loop_home(
        tmp_path,
        "home-run-one",
        policy_toml="[context.structure-graph]\nenabled = true\n",
    )

    spec = importlib.util.spec_from_file_location("detectors_under_test", DETECTORS)
    det_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(det_mod)

    real_run = subprocess.run

    def _intercept_run(argv, **kwargs):
        if len(argv) >= 2 and argv[0] == sys.executable and "--json" in argv:
            argv = [sys.executable, str(patched_script), "--json"]
        return real_run(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", _intercept_run)

    det = {
        "name": "index_freshness_check",
        "path": "scripts/index_freshness_check.py",
        "scope": "runtime",
        "task": "index-freshness-check",
    }
    result = det_mod.run_one(det, timeout=30)
    assert result["status"] == "FINDINGS"
    assert result["structured_findings"] == [
        {
            "code": "MRS-IDXF-001",
            "message": "[home-run-one] no codegraph index at .codegraph/codegraph.db",
        }
    ]
