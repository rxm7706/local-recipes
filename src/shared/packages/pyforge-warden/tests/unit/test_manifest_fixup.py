"""Story 14.2 — throwaway copy, tree digest, and actuator wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyforge.warden.actuator import run_actuator
from pyforge.warden.manifest_fixup import prepare_manifest_fix, tree_content_digest
from pyforge.warden.models import Finding, Severity, SeverityTier


class _AcceptAllForge:
    def existing_open_pr(self, finding_id: str) -> None:
        return None

    def open_pull_request(self, proposal, *, manifest_fix=None, draft=False):  # noqa: ANN001
        return "https://example.test/pr/1"


def _vuln(pkg: str = "leftpad") -> Finding:
    return Finding(
        id=f"vuln:GHSA-test:{pkg}@1.2.0",
        axis="vulnerability",
        message=f"{pkg}: GHSA-test",
        subject=pkg,
        severity=Severity(tier=SeverityTier.HIGH, raw=None),
    )


def _write_pixi_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pixi.toml").write_text(
        '[project]\nname = "demo"\n\n[pypi-dependencies]\nleftpad = ">=1.2"\n',
        encoding="utf-8",
    )
    (root / "pixi.lock").write_text("lock-version = 1\n", encoding="utf-8")


def test_prepare_manifest_fix_returns_diff_and_leaves_scan_tree_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    digest_before = tree_content_digest(repo)

    def _fake_lock(*, cwd: Path):  # noqa: ANN001
        assert cwd != repo
        (cwd / "pixi.lock").write_text("lock-version = 2\n", encoding="utf-8")
        return None, 0

    monkeypatch.setattr("pyforge.warden.manifest_fixup.run_pixi_lock", _fake_lock)
    outcome = prepare_manifest_fix(
        scan_target=repo,
        package="leftpad",
        floor="1.3.0",
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        location_keys=("leftpad",),
    )
    assert outcome.failure_detail is None
    assert outcome.plan is not None
    paths = {change.path for change in outcome.plan.files}
    assert "pixi.toml" in paths
    assert "pixi.lock" in paths
    assert tree_content_digest(repo) == digest_before


def test_flag_off_skips_manifest_fixup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    spy = MagicMock()
    monkeypatch.setattr("pyforge.warden.actuator.prepare_manifest_fix", spy)
    finding = _vuln()
    actuation = run_actuator(
        [finding],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fix_manifest_edit_enabled=False,
        fixed_version_candidates={finding.id: ("1.3.0",)},
        scan_target=repo,
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        client=_AcceptAllForge(),
        solver=lambda **_: "accepted",
    )
    spy.assert_not_called()
    (outcome,) = actuation.outcomes
    assert outcome.manifest_fix is None


def test_flag_on_prepares_manifest_fix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    monkeypatch.setattr(
        "pyforge.warden.manifest_fixup.run_pixi_lock",
        lambda *, cwd: (None, 0),
    )
    finding = _vuln()
    actuation = run_actuator(
        [finding],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fix_manifest_edit_enabled=True,
        fixed_version_candidates={finding.id: ("1.3.0",)},
        scan_target=repo,
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        client=_AcceptAllForge(),
        solver=lambda **_: "accepted",
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "opened"
    assert outcome.manifest_fix is not None
    assert any(change.path == "pixi.toml" for change in outcome.manifest_fix.files)


def test_resolve_failure_is_failed_outcome(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    monkeypatch.setattr(
        "pyforge.warden.manifest_fixup.run_pixi_lock",
        lambda *, cwd: (None, 1),
    )
    finding = _vuln()
    actuation = run_actuator(
        [finding],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fix_manifest_edit_enabled=True,
        fixed_version_candidates={finding.id: ("1.3.0",)},
        scan_target=repo,
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        client=_AcceptAllForge(),
        solver=lambda **_: "accepted",
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "failed"
    assert "manifest edit failed" in (outcome.detail or "")


def test_forced_failure_still_leaves_scan_tree_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    digest_before = tree_content_digest(repo)

    def _boom(**_kwargs: object) -> None:
        raise RuntimeError("forced")

    monkeypatch.setattr("pyforge.warden.manifest_fixup.shutil.copytree", _boom)
    finding = _vuln()
    actuation = run_actuator(
        [finding],
        dry_run=False,
        fix_target_resolution_enabled=True,
        fix_manifest_edit_enabled=True,
        fixed_version_candidates={finding.id: ("1.3.0",)},
        scan_target=repo,
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        client=_AcceptAllForge(),
        solver=lambda **_: "accepted",
    )
    (outcome,) = actuation.outcomes
    assert outcome.status == "failed"
    assert tree_content_digest(repo) == digest_before


@pytest.mark.parametrize(
    ("lock_exit", "expect_plan"),
    [(0, True), (1, False)],
    ids=["re-solve-succeeds", "re-solve-fails"],
)
def test_throwaway_copy_is_removed_after_the_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_exit: int, expect_plan: bool
) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    seen: list[Path] = []

    def _fake_lock(*, cwd: Path):  # noqa: ANN001
        seen.append(cwd)
        assert cwd.is_dir()
        (cwd / "pixi.lock").write_text("lock-version = 2\n", encoding="utf-8")
        return None, lock_exit

    monkeypatch.setattr("pyforge.warden.manifest_fixup.run_pixi_lock", _fake_lock)
    outcome = prepare_manifest_fix(
        scan_target=repo,
        package="leftpad",
        floor="1.3.0",
        manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
        location_keys=("leftpad",),
    )
    assert (outcome.plan is not None) is expect_plan
    (copy,) = seen
    assert not copy.exists()


def test_throwaway_copy_is_removed_when_the_re_solve_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    _write_pixi_repo(repo)
    seen: list[Path] = []

    def _raising_lock(*, cwd: Path):  # noqa: ANN001
        seen.append(cwd)
        raise RuntimeError("solver crashed")

    monkeypatch.setattr("pyforge.warden.manifest_fixup.run_pixi_lock", _raising_lock)
    with pytest.raises(RuntimeError, match="solver crashed"):
        prepare_manifest_fix(
            scan_target=repo,
            package="leftpad",
            floor="1.3.0",
            manifest_locations={"leftpad": ("pixi.toml [pypi-dependencies]",)},
            location_keys=("leftpad",),
        )
    (copy,) = seen
    assert not copy.exists()
