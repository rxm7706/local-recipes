"""Unit tests for ``sources.capability_effect`` caller reach (Story 21.9)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import capability_effect

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "capability_effect"


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "doctor-test@example.com"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Doctor Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)


def _commit_all(repo: Path, message: str = "seed") -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)


def _write_spec(
    specs_dir: Path,
    *,
    slug: str,
    caps: str,
    status: str = "in-progress",
) -> None:
    spec_dir = specs_dir / slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.joinpath("SPEC.md").write_text(
        f"---\nstatus: {status}\n---\n\n## Capabilities\n\n{caps}\n",
        encoding="utf-8",
    )


def _write_epics(pa: Path, body: str) -> None:
    pa.mkdir(parents=True, exist_ok=True)
    pa.joinpath("epics.md").write_text(body, encoding="utf-8")


def _pa(tmp_path: Path, project: str) -> Path:
    return tmp_path / "_bmad-output" / "projects" / project / "planning-artifacts"


def test_document_surface_reports_not_applicable(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs",
        slug="spec-doc-cap",
        caps="- **CAP-1 — doc only.**\n  - **intent:** x\n",
    )
    _write_epics(pa, (_FIXTURES / "epics-doc-surface.md").read_text(encoding="utf-8"))

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert len(findings) == 1
    assert findings[0].check == "capability-effect-document-surface"
    assert "not applicable, document surface" in findings[0].message


def test_missing_surface_path_is_named(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs",
        slug="spec-missing-path",
        caps="- **CAP-1 — code cap.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: missing path\n\n"
        "**FR/AD:** spec-missing-path CAP-1\n\n"
        "**Surface:** `src/no/such/module.py`\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert any(f.check == "capability-effect-absent-surface-path" for f in findings)
    missing = next(
        f for f in findings if f.check == "capability-effect-absent-surface-path"
    )
    assert "src/no/such/module.py" in missing.message


def test_unreadable_epics_emits_named_finding(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs",
        slug="spec-any",
        caps="- **CAP-1 — x.**\n",
    )
    pa.mkdir(parents=True, exist_ok=True)
    # A directory at the epics path makes read_text fail deterministically.
    (pa / "epics.md").mkdir()

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert any(f.check == "capability-effect-unreadable-epics" for f in findings)


def test_no_caller_symbol_on_synthetic_fixture(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    module = tmp_path / "src" / "packages" / "demo" / "core.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text("def orphan_helper():\n    return 1\n", encoding="utf-8")

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-orphan",
        caps="- **CAP-1 — orphan.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: orphan cap\n\n"
        "**FR/AD:** spec-orphan CAP-1\n\n"
        f"**Surface:** `{module.relative_to(tmp_path)}` (`orphan_helper`)\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    no_caller = [f for f in findings if f.check == "capability-effect-no-caller"]
    assert len(no_caller) == 1
    assert no_caller[0].evidence["symbol"] == "orphan_helper"
    assert "whole-word textual scan" in no_caller[0].message


def test_external_caller_suppresses_no_caller_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    module = tmp_path / "src" / "packages" / "demo" / "core.py"
    caller = tmp_path / "src" / "packages" / "demo" / "use.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text("def shared_fn():\n    return 1\n", encoding="utf-8")
    caller.write_text(
        "from core import shared_fn\n\ndef run():\n    return shared_fn()\n",
        encoding="utf-8",
    )

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-called",
        caps="- **CAP-1 — called.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: called cap\n\n"
        "**FR/AD:** spec-called CAP-1\n\n"
        f"**Surface:** `{module.relative_to(tmp_path)}` (`shared_fn`)\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert not any(f.check == "capability-effect-no-caller" for f in findings)


def test_citing_story_without_surface_line_is_named(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs",
        slug="spec-no-surface",
        caps="- **CAP-1 — x.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: no surface\n\n"
        "**FR/AD:** spec-no-surface CAP-1\n\n",
    )

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert any(f.check == "capability-effect-no-surface-line" for f in findings)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pixi.toml").is_file() and (parent / "_bmad-output").is_dir():
            return parent
    pytest.skip("repo root not found")


def test_live_fleet_proves_capability_effect_no_caller_finding() -> None:
    """Live fleet proof — Story 21.3 caution: not a single synthetic join value.

    Original target (2026-09-09): ``spec-risk-tiered-review-depth`` symbols
    ``classify_review_tier`` / ``resolve_review_cycles`` with zero callers
    outside ``core/gate.py`` and ``tests/unit/test_gate.py``.

    Marshal Story 33.5 (done) wired ``cli/gate.py`` callers at
    ``cli/gate.py:701`` and ``:705``, so those symbols now have production
    callers outside ``core/gate.py``. This test therefore requires at least
    one other live ``capability-effect-no-caller`` finding on the real fleet.
    """
    root = _repo_root()
    findings = capability_effect.gather_caller_reach(root)

    no_caller = [f for f in findings if f.check == "capability-effect-no-caller"]
    assert no_caller, (
        "expected at least one live capability-effect-no-caller finding on "
        "the real fleet"
    )

    risk_findings = [
        f
        for f in no_caller
        if f.evidence.get("spec_slug") == "spec-risk-tiered-review-depth"
        and f.evidence.get("symbol")
        in {"classify_review_tier", "resolve_review_cycles"}
    ]
    if not risk_findings:
        assert len(no_caller) >= 1
    else:
        for finding in risk_findings:
            assert finding.status is DoctorStatus.WARN
            assert "whole-word textual scan" in finding.message


def test_gather_includes_caller_reach_pass(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs",
        slug="spec-doc-cap",
        caps="- **CAP-1 — doc only.**\n",
        status="in-progress",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: cite doc cap\n\n"
        "**FR/AD:** spec-doc-cap CAP-1\n\n"
        "**Surface:** `docs/dreams/example.md`\n",
    )

    findings = capability_effect.gather(tmp_path)

    checks = {f.check for f in findings}
    assert "capability-effect-document-surface" in checks
    assert "capability-effect-verified" not in checks


def test_test_only_reference_still_reports_no_caller(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    module = tmp_path / "src" / "packages" / "demo" / "core.py"
    test_file = tmp_path / "src" / "packages" / "demo" / "tests" / "test_core.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    test_file.parent.mkdir(parents=True, exist_ok=True)
    module.write_text("def orphan_only():\n    return 1\n", encoding="utf-8")
    test_file.write_text(
        "from core import orphan_only\n\ndef test_it():\n    assert orphan_only()\n",
        encoding="utf-8",
    )

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-orphan-test",
        caps="- **CAP-1 — orphan.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: orphan cap\n\n"
        "**FR/AD:** spec-orphan-test CAP-1\n\n"
        f"**Surface:** `{module.relative_to(tmp_path)}` (`orphan_only`)\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert any(
        f.check == "capability-effect-no-caller"
        and f.evidence.get("symbol") == "orphan_only"
        for f in findings
    )


def test_station_relative_surface_resolves_under_pyforge_package(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    station_root = (
        tmp_path
        / "src"
        / "shared"
        / "packages"
        / "pyforge-demo"
        / "src"
        / "pyforge"
        / "demo"
    )
    module = station_root / "core.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text("def station_fn():\n    return 0\n", encoding="utf-8")

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-station-rel",
        caps="- **CAP-1 — station path.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: station relative surface\n\n"
        "**FR/AD:** spec-station-rel CAP-1\n\n"
        "**Surface:** `core.py` (`station_fn`)\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert any(
        f.check == "capability-effect-no-caller"
        and f.evidence.get("symbol") == "station_fn"
        for f in findings
    )
