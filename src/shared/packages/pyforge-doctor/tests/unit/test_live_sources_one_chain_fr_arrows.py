"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_one_chain_fr_arrows.py``.

The ``scripts/fr_baseline.py`` tests load this repository's own script over a
fixture tree, and the live-tree legs pin the reference-heading and
honest-lockstep cases this checkout carries, so they run in the station's
live-tree half. The fixture builders are ``test_sources_one_chain_fr_arrows.py``'s
own (the package half).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from test_sources_one_chain_fr_arrows import (  # noqa: F401 -- _isolate_git_env is the module's autouse scrub
    _RATCHET_PRD,
    _STATION,
    _baseline,
    _by_check,
    _commit,
    _edit_baseline,
    _fails,
    _git,
    _isolate_git_env,
    _read_baseline,
    _repo,
    _tree,
)

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import one_chain
from pyforge.doctor.verdict import exit_code_for

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _live_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


# --- 9. scripts/fr_baseline.py -----------------------------------------------


def _cli(monkeypatch: pytest.MonkeyPatch, root: Path) -> ModuleType:
    script = _live_root() / "scripts" / "fr_baseline.py"
    assert script.is_file(), "scripts/fr_baseline.py is missing"
    spec = importlib.util.spec_from_file_location("fr_baseline_under_test", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "REPO_ROOT", root)
    return mod


def test_cli_snapshot_once_then_project_and_prune(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    root = _tree(tmp_path, "#### FR-1: cited ← CAP-1\n\n#### FR-2: bare\n")
    (root / one_chain.FR_BASELINE_REL).unlink()
    cli = _cli(monkeypatch, root)
    assert cli.main(["--project", _STATION]) == 1  # no baseline yet
    assert "take --snapshot first" in capsys.readouterr().out
    assert cli.main(["--snapshot", "--ruling-sha", "abc123"]) == 0
    assert _read_baseline(root)["projects"] == {_STATION: ["FR-2"]}
    assert cli.main(["--snapshot"]) == 1  # refused once it exists
    assert "refusing" in capsys.readouterr().out
    assert cli.main(["--project", _STATION]) == 0
    data = _read_baseline(root)
    assert data["ruling_sha"] == "abc123" and _STATION in data["rebaselined"]
    prd = root / "_bmad-output" / "projects" / _STATION / "planning-artifacts" / "prds" / f"prd-{_STATION}-2026-01-01"
    (prd / "prd.md").write_text("#### FR-1: cited ← CAP-1\n\n#### FR-2: now cited ← CAP-2\n")
    assert cli.main(["--prune"]) == 0
    out = capsys.readouterr().out
    assert "pruned 1 entry" in out and f"{_STATION}: FR-2" in out
    assert _read_baseline(root)["projects"] == {_STATION: []}


def test_cli_snapshot_findings_is_one_time_and_force_prints_the_delta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    root = _tree(tmp_path, "- **FR33** ← CAP-1 *(v1)*: unhyphenated\n")
    cli = _cli(monkeypatch, root)
    assert cli.main(["--snapshot-findings"]) == 0  # the one-time act
    data = _read_baseline(root)
    assert data["findings"] == {_STATION: ["fr-id-unhyphenated:FR33"]} and data["findings_sha"] == "unknown"
    prd = root / "_bmad-output" / "projects" / _STATION / "planning-artifacts" / "prds" / f"prd-{_STATION}-2026-01-01"
    (prd / "prd.md").write_text("- **FR35** ← CAP-1 *(v1)*: a NEW structural finding\n")
    assert cli.main(["--snapshot-findings"]) == 1  # refused: it would launder FR35 in
    out = capsys.readouterr().out
    assert "ADD    fr-id-unhyphenated:FR35" in out and "REMOVE fr-id-unhyphenated:FR33" in out
    assert "refusing" in out and "1 key(s) would be ADDED" in out
    assert _read_baseline(root)["findings"] == {_STATION: ["fr-id-unhyphenated:FR33"]}  # untouched
    assert cli.main(["--snapshot-findings", "--force"]) == 0
    out = capsys.readouterr().out
    assert "ADD    fr-id-unhyphenated:FR35" in out
    assert f"FORCED {_STATION} findings fr-id-unhyphenated:FR35 @ unknown" in out
    data = _read_baseline(root)
    assert data["findings"] == {_STATION: ["fr-id-unhyphenated:FR35"]}
    # Story 50.2 (AC5): the forced key is recorded with the run's HEAD; FR33's record left with its key.
    assert data["forced"] == [
        {"station": _STATION, "kind": "findings", "key": "fr-id-unhyphenated:FR35", "head": "unknown"}
    ]


def test_cli_project_prints_the_delta_and_refuses_growth_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Story 50.2 AC5 (mutation: `--project` growth admitted without `--force`)."""
    root = _tree(tmp_path, "#### FR-1: cited ← CAP-1\n\n#### FR-2: bare\n")
    _baseline(root, projects={_STATION: ["FR-2", "FR-9"]}, findings={_STATION: []})
    cli = _cli(monkeypatch, root)
    assert cli.main(["--project", _STATION]) == 0  # shrinking needs no --force
    out = capsys.readouterr().out
    assert "REMOVE FR-9" in out and "refusing" not in out
    assert _read_baseline(root)["projects"] == {_STATION: ["FR-2"]}
    prd = root / "_bmad-output" / "projects" / _STATION / "planning-artifacts" / "prds" / f"prd-{_STATION}-2026-01-01"
    (prd / "prd.md").write_text("#### FR-1: cited ← CAP-1\n\n#### FR-2: bare\n\n#### FR-3: bare, minted since\n")
    before = (root / one_chain.FR_BASELINE_REL).read_text()
    assert cli.main(["--project", _STATION]) == 1  # refused: it would launder FR-3 in
    out = capsys.readouterr().out
    assert f"{_STATION}: +1 -0" in out and "ADD    FR-3" in out
    assert "refusing" in out and "would ADD 1 id(s)" in out
    assert (root / one_chain.FR_BASELINE_REL).read_text() == before  # untouched
    assert cli.main(["--project", _STATION, "--force"]) == 0
    out = capsys.readouterr().out
    assert "ADD    FR-3" in out and f"FORCED {_STATION} projects FR-3 @ unknown" in out
    data = _read_baseline(root)
    assert data["projects"] == {_STATION: ["FR-2", "FR-3"]}
    assert data["forced"] == [{"station": _STATION, "kind": "projects", "key": "FR-3", "head": "unknown"}]


# --- 10. the ratchet against the merge-base (Story 50.2) ----------------------


def test_a_key_the_script_forced_is_admitted_and_an_owners_row_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """AC2 (mutation: the forced record ignored -- a forced key FAILs)."""
    root = _tree(tmp_path, _RATCHET_PRD)
    _baseline(root, projects={_STATION: []}, findings={_STATION: []})
    _repo(root)
    head = _git(root, "rev-parse", "HEAD").strip()
    cli = _cli(monkeypatch, root)
    assert cli.main(["--project", _STATION, "--force"]) == 0
    assert cli.main(["--snapshot-findings", "--force"]) == 0
    capsys.readouterr()
    assert _read_baseline(root)["forced"] == [
        {"station": _STATION, "kind": "projects", "key": "FR-2", "head": head},
        {"station": _STATION, "kind": "findings", "key": "fr-id-unhyphenated:FR33", "head": head},
    ]
    _commit(root, "the reviewed --force")
    findings = one_chain.gather_fr_without_cap(root)
    by = _by_check(findings)
    assert "fr-baseline-grown" not in by and not _fails(findings)
    assert by["fr-baselined"][0].evidence["keys"] == ["fr-id-unhyphenated:FR33"]
    assert exit_code_for(findings) == 0
    # a key added by hand whose only cover is an `owners` row still fails
    prd = root / "_bmad-output" / "projects" / _STATION / "planning-artifacts" / "prds" / f"prd-{_STATION}-2026-01-01"
    (prd / "prd.md").write_text(_RATCHET_PRD + "\n#### FR-3: bare, owned by a story\n")
    _edit_baseline(root, projects={_STATION: ["FR-2", "FR-3"]}, owners={_STATION: ["99.1 (FR-3)"]})
    by = _by_check(one_chain.gather_fr_without_cap(root))
    assert [(f.status, f.evidence["key"]) for f in by["fr-baseline-grown"]] == [(DoctorStatus.FAIL, "FR-3")]
    assert [f.evidence["fr"] for f in by["fr-without-cap"]] == ["FR-3"]


# --- live tree ---------------------------------------------------------------


def test_live_tree_reference_headings_never_duplicate_and_satellites_do() -> None:
    keys = one_chain.snapshot_fr_findings(_live_root())
    dups = {slug: [k for k in v if k.startswith("fr-duplicate-id:")] for slug, v in keys.items()}
    assert dups["pyforge-steward"] == [] and dups["pyforge-herald"] == [] and dups["pyforge-marshal"] == []
    assert dups["pyforge-atlas"] == []  # atlas 41.2: the Unity / Wasm satellites are Fold provenance record sections


def test_live_tree_honest_lockstep_runs_stay_quiet() -> None:
    keys = one_chain.snapshot_fr_findings(_live_root())
    assert "fr-counted-run:FR-32..FR-41" not in keys["pyforge-steward"]
    assert "fr-counted-run:FR-69..FR-77" not in keys["pyforge-atlas"]
    assert not any(k.startswith("fr-counted-run:") for k in keys["pyforge-doctor"])
