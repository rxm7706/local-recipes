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
    missing = next(f for f in findings if f.check == "capability-effect-absent-surface-path")
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
        "## Epic 1\n\n### Story 1.1: no surface\n\n**FR/AD:** spec-no-surface CAP-1\n\n",
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
    assert no_caller, "expected at least one live capability-effect-no-caller finding on the real fleet"

    risk_findings = [
        f
        for f in no_caller
        if f.evidence.get("spec_slug") == "spec-risk-tiered-review-depth"
        and f.evidence.get("symbol") in {"classify_review_tier", "resolve_review_cycles"}
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

    assert any(f.check == "capability-effect-no-caller" and f.evidence.get("symbol") == "orphan_only" for f in findings)


def test_station_relative_surface_resolves_under_pyforge_package(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    station_root = tmp_path / "src" / "shared" / "packages" / "pyforge-demo" / "src" / "pyforge" / "demo"
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

    assert any(f.check == "capability-effect-no-caller" and f.evidence.get("symbol") == "station_fn" for f in findings)


def test_directory_surface_fragment_resolves_as_existing(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    pkg_dir = tmp_path / "src" / "shared" / "packages" / "pyforge-demo" / "src" / "pyforge" / "demo" / "views"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-dir-surface",
        caps="- **CAP-1 — directory surface.**\n",
    )
    rel = pkg_dir.relative_to(tmp_path).as_posix() + "/"
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: directory surface\n\n"
        "**FR/AD:** spec-dir-surface CAP-1\n\n"
        f"**Surface:** `{rel}` (delete)\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert not any(f.check == "capability-effect-absent-surface-path" for f in findings)


def test_brace_expansion_fragment_not_split_on_internal_comma(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-brace-surface",
        caps="- **CAP-1 — brace surface.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: brace surface\n\n"
        "**FR/AD:** spec-brace-surface CAP-1\n\n"
        # `.py`, not `.yml`/`.md` — a document-suffixed fragment would be
        # filtered out as a document surface before reaching path resolution,
        # which would pass for the wrong reason (see the doc-suffix test
        # above) rather than exercising the brace-depth fix.
        "**Surface:** `src/pkg/{mod_a,mod_b}.py`\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    missing = [f for f in findings if f.check == "capability-effect-absent-surface-path"]
    assert len(missing) == 1
    assert missing[0].evidence["missing_path"] == "src/pkg/{mod_a,mod_b}.py"


def test_double_colon_symbol_suffix_resolves_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    module = tmp_path / "src" / "packages" / "demo" / "core.py"
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text("def some_fn():\n    return 1\n", encoding="utf-8")

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-colon-surface",
        caps="- **CAP-1 — colon surface.**\n",
    )
    rel = module.relative_to(tmp_path).as_posix()
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: colon surface\n\n"
        "**FR/AD:** spec-colon-surface CAP-1\n\n"
        f"**Surface:** `{rel}::some_fn`\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert not any(f.check == "capability-effect-absent-surface-path" for f in findings)


def test_document_suffix_with_annotation_is_not_absent_path(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs",
        slug="spec-doc-annotated",
        caps="- **CAP-1 — doc with annotation.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: doc with annotation\n\n"
        "**FR/AD:** spec-doc-annotated CAP-1\n\n"
        "**Surface:** `install-matrix.md` (installed-stage caveat retired)\n",
    )

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert not any(f.check == "capability-effect-absent-surface-path" for f in findings)
    assert any(f.check == "capability-effect-document-surface" for f in findings)


def test_package_relative_tests_path_resolves(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    test_file = tmp_path / "src" / "shared" / "packages" / "pyforge-demo" / "tests" / "unit" / "test_thing.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_x():\n    assert True\n", encoding="utf-8")

    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-tests-rel",
        caps="- **CAP-1 — tests relative.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: tests relative surface\n\n"
        "**FR/AD:** spec-tests-rel CAP-1\n\n"
        "**Surface:** `tests/unit/test_thing.py`\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert not any(f.check == "capability-effect-absent-surface-path" for f in findings)


def test_sibling_spec_shorthand_resolves_under_specs_dir(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    pa = _pa(tmp_path, "pyforge-demo")
    _write_spec(
        pa / "specs",
        slug="spec-sibling-target",
        caps="- **CAP-1 — sibling target.**\n",
    )
    _write_spec(
        pa / "specs",
        slug="spec-citer",
        caps="- **CAP-1 — cites sibling.**\n",
    )
    _write_epics(
        pa,
        "## Epic 1\n\n"
        "### Story 1.1: sibling spec shorthand\n\n"
        "**FR/AD:** spec-citer CAP-1\n\n"
        "**Surface:** `spec-sibling-target/SPEC.md`\n",
    )
    _commit_all(tmp_path)

    findings = capability_effect.gather_caller_reach(tmp_path)

    assert not any(f.check == "capability-effect-absent-surface-path" for f in findings)


# --- corpus fallback (the path taken when `git grep` cannot run) ------------


def _write_corpus_tree(tmp_path: Path) -> None:
    """A tree exercising every branch of the corpus scan: a defining module,
    an external caller, a test-only caller, a pruned ``__pycache__`` file, a
    non-UTF-8 file, and a non-``.py`` mention that must not count."""
    src = tmp_path / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "core.py").write_text(
        "def shared_fn():\n    return shared_fn\n\nclass Other:\n    pass\n",
        encoding="utf-8",
    )
    (src / "use.py").write_text(
        "from core import shared_fn\n\n\ndef shared_fn_wrapper():\n    return shared_fn()\n",
        encoding="utf-8",
    )
    (src / "notes.txt").write_text("shared_fn shared_fn\n", encoding="utf-8")
    cache = src / "__pycache__"
    cache.mkdir()
    (cache / "stale.py").write_text("shared_fn()\n", encoding="utf-8")
    (src / "binary.py").write_bytes(b"\xff\xfe shared_fn\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "tool.py").write_text("x = shared_fn()  # shared_fn\n", encoding="utf-8")
    tests = tmp_path / "src" / "pkg" / "tests"
    tests.mkdir()
    (tests / "test_use.py").write_text("shared_fn()\n", encoding="utf-8")


def test_build_python_corpus_prunes_pycache_and_undecodable(tmp_path: Path) -> None:
    _write_corpus_tree(tmp_path)

    corpus = capability_effect._build_python_corpus(tmp_path)

    assert set(corpus) == {
        "src/pkg/core.py",
        "src/pkg/use.py",
        "src/pkg/tests/test_use.py",
        "scripts/tool.py",
    }
    assert corpus["scripts/tool.py"] == ["x = shared_fn()  # shared_fn"]


def test_external_reference_count_in_corpus_skips_tests_and_declarations(
    tmp_path: Path,
) -> None:
    _write_corpus_tree(tmp_path)
    corpus = capability_effect._build_python_corpus(tmp_path)
    corpus["docs/prose.md"] = ["shared_fn shared_fn"]

    count = capability_effect._external_reference_count_in_corpus(
        corpus,
        symbol="shared_fn",
        defining_rel_paths={"src/pkg/core.py"},
    )

    # core.py: only the `def shared_fn` line counts, minus the declaration
    # itself (0); use.py: the import line and the call line (2), while
    # `def shared_fn_wrapper` is not a whole-word match; scripts/tool.py: one
    # line (1). tests/ and the .md entry never count.
    assert count == 3


def test_external_reference_count_falls_back_to_corpus_without_git(
    tmp_path: Path,
) -> None:
    _write_corpus_tree(tmp_path)  # deliberately NOT a git repo
    corpus_holder: list[dict[str, list[str]] | None] = [None]

    count = capability_effect._external_reference_count(
        tmp_path,
        symbol="shared_fn",
        defining_rel_paths={"src/pkg/core.py"},
        grep_cache={},
        corpus_holder=corpus_holder,
    )

    assert count == 3
    assert corpus_holder[0] is not None  # corpus built once and cached
