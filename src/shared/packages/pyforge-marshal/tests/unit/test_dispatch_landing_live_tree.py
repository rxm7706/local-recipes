"""Story 53.4: the co-governor spec-surface reconcile, run against this checkout's stamp and memlog scripts.

Story 116.3 (spec-pyforge-marshal:CAP-305): the three ``test_dispatch_landing.py`` tests that build their fixture
repository from this checkout's ``scripts/spec_surface_check.py`` (patched to the fixture's root) and
``_bmad/scripts/memlog.py`` (copied) moved here, marked ``live_tree``; the root is found when a test runs, never at
import, and a missing script fails the test, never skips it. Every other landing test stays in
``test_dispatch_landing.py``, which keeps the fakes both files use.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult
from test_dispatch_landing import (
    FakeProcess,
    _calls,
    _doctor_answer,
    _install_fake_spec_surface,
    _ReconcileVcs,
    _spec_args,
)

from pyforge.marshal.core.identity import normalize
from pyforge.marshal.dispatch_land import _own_path_stamp_refusals, _reconcile_spec_surface_drift

pytestmark = pytest.mark.live_tree


_CO_GOV_STATION = "proj/spec-station"
_CO_GOV_CORE = "proj/spec-core"
_CO_GOV_PATH = "a.py"


def _repo_root() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages -> shared -> src -> this checkout's root, found when a
    # test runs, never at import
    return Path(__file__).resolve().parents[6]


def _co_governor_spec_dir(repo: Path, slug: str) -> Path:
    return repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts" / "specs" / slug


def _patched_stamp_script(repo: Path) -> Path:
    source = (_repo_root() / "scripts" / "spec_surface_check.py").read_text(encoding="utf-8")
    patched = source.replace(
        "REPO_ROOT = Path(__file__).resolve().parent.parent",
        f"REPO_ROOT = Path({str(repo)!r})",
    )
    assert patched != source
    destination = repo / "scripts" / "spec_surface_check.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(patched, encoding="utf-8")
    return destination


def _stamp_repo_baseline(repo: Path) -> None:
    subprocess.run(
        [sys.executable, str(repo / "scripts" / "spec_surface_check.py"), "--write-baseline"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _co_governor_fixture_repo(tmp_path: Path) -> Path:
    """Two specs co-govern ``a.py`` with a stamped baseline."""
    for slug in ("spec-station", "spec-core"):
        directory = _co_governor_spec_dir(tmp_path, slug)
        directory.mkdir(parents=True)
        (directory / "SPEC.md").write_text(
            f"---\nsurface:\n  - {_CO_GOV_PATH}\n---\n# {slug}\n",
            encoding="utf-8",
        )
        (directory / ".memlog.md").write_text(
            "---\ntopic: test\nupdated: 2026-10-06T00:00\n---\n\n- (note) initial\n",
            encoding="utf-8",
        )
    (tmp_path / _CO_GOV_PATH).write_text("x = 1\n", encoding="utf-8")
    memlog_dest = tmp_path / "_bmad" / "scripts" / "memlog.py"
    memlog_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(_repo_root() / "_bmad" / "scripts" / "memlog.py", memlog_dest)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    _patched_stamp_script(tmp_path)
    _stamp_repo_baseline(tmp_path)
    return tmp_path


class _RealReconcileProcess:
    """Runs memlog and spec_surface_check subprocesses against the fixture repo; Doctor's command answers
    from the test's script."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path]] = []
        self.doctor_calls: list[tuple[list[str], Path, float | None]] = []

    def run(self, tokens, *, cwd: Path, timeout_s: float | None = None):
        doctor = _doctor_answer(self.doctor_calls, tokens, cwd, timeout_s)
        if doctor is not None:
            return doctor
        self.calls.append((list(tokens), cwd))
        if len(tokens) > 1 and ("memlog.py" in tokens[1] or "spec_surface_check.py" in tokens[1]):
            completed = subprocess.run(tokens, cwd=cwd, capture_output=True, text=True, check=False)
            return ProcessResult(completed.returncode, completed.stdout, completed.stderr)
        return ProcessResult(returncode=0, stdout="", stderr="")


def test_reconcile_spec_surface_drift_reconciles_co_governor_doctor_cleared_by_overlap_tolerance(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 53.4: when the session named a path only on its station spec, doctor's overlap
    tolerance emits no row, but the co-governor still refuses a scoped stamp until its memlog
    names the path."""
    repo = _co_governor_fixture_repo(tmp_path)
    (repo / _CO_GOV_PATH).write_text("x = 2\n", encoding="utf-8")
    station_memlog = _co_governor_spec_dir(repo, "spec-station") / ".memlog.md"
    station_memlog.write_text(
        station_memlog.read_text(encoding="utf-8") + f"- (event) session named {_CO_GOV_PATH}\n",
        encoding="utf-8",
    )
    core_memlog = _co_governor_spec_dir(repo, "spec-core") / ".memlog.md"
    core_memlog.write_text(
        core_memlog.read_text(encoding="utf-8") + "- (event) unrelated story moved memlog\n", encoding="utf-8"
    )

    _install_fake_spec_surface(monkeypatch, ())
    process = _RealReconcileProcess()
    worktree = repo
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=repo,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.4",
        key=normalize("53-4-example"),
        run_id="run-53",
        vcs=_ReconcileVcs(changed=(_CO_GOV_PATH,)),
        process=process,
    )
    assert outcome.refuse is False
    assert outcome.finding is not None and outcome.finding.code == "MRS-DISP-047"
    assert _CO_GOV_CORE in outcome.finding.message
    memlog_targets = [Path(tokens[tokens.index("--path") + 1]).parent.name for tokens in _calls(process, "memlog.py")]
    assert memlog_targets == ["spec-core"]
    assert _spec_args(_calls(process, "spec_surface_check.py")[0]) == [_CO_GOV_CORE]


def test_reconcile_spec_surface_drift_without_stamp_refusal_expansion_leaves_co_governor_unnamed(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 53.4 AC2: without the stamp-refusal expansion, a doctor-cleared co-governor stays unnamed."""
    repo = _co_governor_fixture_repo(tmp_path)
    (repo / _CO_GOV_PATH).write_text("x = 2\n", encoding="utf-8")
    station_memlog = _co_governor_spec_dir(repo, "spec-station") / ".memlog.md"
    station_memlog.write_text(
        station_memlog.read_text(encoding="utf-8") + f"- (event) session named {_CO_GOV_PATH}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land._own_path_stamp_refusals",
        lambda _worktree, _own_paths: {},
    )
    _install_fake_spec_surface(monkeypatch, ())
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=repo,
        worktree=repo,
        head_branch="dispatch/pyforge-marshal/53.4",
        key=normalize("53-4-example"),
        run_id=None,
        vcs=_ReconcileVcs(changed=(_CO_GOV_PATH,)),
        process=process,
    )
    assert outcome.finding is None
    assert _calls(process, "memlog.py") == []


def test_own_path_stamp_refusals_names_co_governor_when_station_memlog_cleared_doctor_verdict(
    tmp_path: Path,
) -> None:
    repo = _co_governor_fixture_repo(tmp_path)
    (repo / _CO_GOV_PATH).write_text("x = 2\n", encoding="utf-8")
    station_memlog = _co_governor_spec_dir(repo, "spec-station") / ".memlog.md"
    station_memlog.write_text(
        station_memlog.read_text(encoding="utf-8") + f"- (event) session named {_CO_GOV_PATH}\n",
        encoding="utf-8",
    )
    refusals = _own_path_stamp_refusals(repo, frozenset({_CO_GOV_PATH}))
    assert refusals == {_CO_GOV_CORE: {_CO_GOV_PATH}}
    assert _CO_GOV_STATION not in refusals
