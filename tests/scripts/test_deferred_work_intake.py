"""Coverage for ``scripts/deferred_work_intake.py`` (marshal Story 25.6).

Uses fixture trees under tmp_path — same discipline as
``test_deferred_work_promote.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

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


def test_intake_marks_long_summary_truncation_instead_of_silently_corrupting(
    tmp_path: Path,
) -> None:
    # DW-FU-21-8-6: a `summary:` over 500 chars used to be hard-sliced with no
    # marker -- silent, mid-sentence data loss in the promoted ledger heading AND
    # `summary:` line. It must now say so (and the original length must be
    # recoverable), not disappear.
    long_summary = "The widget subsystem silently drops every third request. " * 12
    assert len(long_summary) > 500
    long_summary_yaml = f"""\
---
title: canary spec
status: done
deferred:
  - summary: {long_summary.strip()!r}
    evidence: seen in prod logs
    location: src/pyforge/doctor/sources/widget.py
    severity: medium
---

# Canary
"""
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(repo, "pyforge-doctor", "spec-long-summary.md", long_summary_yaml)
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
    flat_original = " ".join(long_summary.split()).strip()
    assert "[truncated" in text
    assert str(len(flat_original)) in text  # original length recoverable, not lost


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


UNCITED_DEFERRED_YAML = """\
---
title: uncited spec
status: done
deferred:
  - summary: deferred to a later story
    evidence: out of scope for this pass
    severity: medium
---

# Uncited
"""


def test_intake_refuses_entry_with_no_resolvable_location(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(repo, "pyforge-doctor", "spec-uncited.md", UNCITED_DEFERRED_YAML)
    tracked = _write_tracked(repo, "pyforge-doctor", "# existing ledger\n")

    mod = _load_intake_module(repo)
    outcome = mod._ingest_project("doctor", repo / "_bmad-output" / "projects" / "pyforge-doctor")

    assert outcome.status == "refused"
    assert outcome.refused == 1
    assert tracked.read_text(encoding="utf-8") == "# existing ledger\n"
    captured = capsys.readouterr()
    assert "spec-uncited.md" in captured.err
    assert "missing resolvable `location:`" in captured.err


def test_intake_main_exits_nonzero_when_all_refused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(repo, "pyforge-doctor", "spec-uncited.md", UNCITED_DEFERRED_YAML)
    _write_tracked(repo, "pyforge-doctor", "# existing ledger\n")

    mod = _load_intake_module(repo)
    old_argv = sys.argv
    try:
        sys.argv = ["deferred_work_intake.py", "--fix", "--project", "doctor"]
        assert mod.main() == 1
    finally:
        sys.argv = old_argv


def test_intake_preserves_pre_existing_ledger_on_append(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    existing = """\
# ledger

### DW-OLD-1: pre-existing entry

- source_spec: `old-spec.md`
  summary: keep me verbatim
  status: open
"""
    _write_spec(repo, "pyforge-doctor", "spec-good.md", CANARY_DEFERRED_YAML)
    tracked = _write_tracked(repo, "pyforge-doctor", existing)

    mod = _load_intake_module(repo)
    outcome = mod._ingest_project("doctor", repo / "_bmad-output" / "projects" / "pyforge-doctor")

    assert outcome.status == "ingested"
    text = tracked.read_text(encoding="utf-8")
    assert "keep me verbatim" in text
    assert "GitHub-releases fallback" in text


EVIDENCE_ONLY_DEFERRED_YAML = """\
---
title: evidence-only spec
status: done
deferred:
  - summary: tighten the parser
    evidence: |-
      `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` over-matches
    severity: medium
---

# Evidence only
"""


def test_intake_accepts_deferral_with_path_only_in_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(repo, "pyforge-doctor", "spec-evidence-only.md", EVIDENCE_ONLY_DEFERRED_YAML)
    _write_tracked(repo, "pyforge-doctor", "# empty ledger\n")

    mod = _load_intake_module(repo)
    outcome = mod._ingest_project("doctor", repo / "_bmad-output" / "projects" / "pyforge-doctor")

    assert outcome.status == "ingested"
    text = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    ).read_text(encoding="utf-8")
    assert "tighten the parser" in text
    assert "chain.py" in text


def test_intake_accepts_resolvable_entry_and_refuses_uncited_in_same_run(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_spec(repo, "pyforge-doctor", "spec-good.md", CANARY_DEFERRED_YAML)
    _write_spec(repo, "pyforge-doctor", "spec-uncited.md", UNCITED_DEFERRED_YAML)
    _write_tracked(repo, "pyforge-doctor", "# empty ledger\n")

    mod = _load_intake_module(repo)
    outcome = mod._ingest_project("doctor", repo / "_bmad-output" / "projects" / "pyforge-doctor")

    assert outcome.status == "ingested"
    assert outcome.refused == 1
    text = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "deferred-work-ledger.md"
    ).read_text(encoding="utf-8")
    assert "GitHub-releases fallback" in text
    assert "deferred to a later story" not in text
