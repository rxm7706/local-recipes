"""Coverage for ``scripts/deferred_work_intake.py`` (marshal Story 25.6).

Uses fixture trees under tmp_path — same discipline as
``test_deferred_work_promote.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTAKE = REPO_ROOT / "scripts" / "deferred_work_intake.py"

# DW-14-1-1 canary shape (doctor Story 14.1 frontmatter deferred item)
CANARY_DEFERRED_YAML = """\
---
title: canary spec
status: done
deferred:
  - summary: >-
      GitHub-releases fallback for the npm-invisible suite packages
    evidence: |-
      Live probe: bmad-loop 404 on registry.npmjs.org
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py
    severity: medium
---

# Canary
"""


def _write_spec(repo: Path, project: str, rel: str, body: str) -> Path:
    path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "specs"
        / rel
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _write_tracked(repo: Path, project: str, text: str) -> Path:
    path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _load_intake_module(repo: Path):
    text = INTAKE.read_text(encoding="utf-8")
    patched = text.replace(
        "REPO_ROOT = Path(__file__).resolve().parent.parent",
        f"REPO_ROOT = Path({str(repo)!r})",
    )
    tmp_script = repo / "scripts" / "deferred_work_intake_patched.py"
    tmp_script.parent.mkdir(parents=True, exist_ok=True)
    tmp_script.write_text(patched, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("deferred_work_intake_patched", tmp_script)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["deferred_work_intake_patched"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_intake_promotes_canary_frontmatter_deferral(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(
        repo,
        "pyforge-doctor",
        "spec-14-1-canary.md",
        CANARY_DEFERRED_YAML,
    )
    _write_tracked(repo, "pyforge-doctor", "# empty ledger\n")

    mod = _load_intake_module(repo)
    outcome = mod._ingest_project("doctor", repo / "_bmad-output" / "projects" / "pyforge-doctor")

    assert outcome.status == "ingested"
    tracked = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    )
    text = tracked.read_text(encoding="utf-8")
    assert "spec-deferred" in text
    assert "GitHub-releases fallback" in text
    assert "bmad_method.py" in text
    assert "status: open" in text


def test_intake_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(repo, "pyforge-marshal", "spec-25-6-test.md", CANARY_DEFERRED_YAML)
    _write_tracked(repo, "pyforge-marshal", "")

    mod = _load_intake_module(repo)
    proj = repo / "_bmad-output" / "projects" / "pyforge-marshal"
    first = mod._ingest_project("marshal", proj)
    second = mod._ingest_project("marshal", proj)

    assert first.status == "ingested"
    assert second.status == "no-op"
    assert "already in tracked ledger" in second.message


def test_intake_no_op_without_frontmatter_deferred(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(
        repo,
        "pyforge-doctor",
        "spec-plain.md",
        "---\ntitle: plain\nstatus: done\n---\n\n# Plain\n",
    )
    mod = _load_intake_module(repo)
    outcome = mod._ingest_project("doctor", repo / "_bmad-output" / "projects" / "pyforge-doctor")
    assert outcome.status == "no-op"
