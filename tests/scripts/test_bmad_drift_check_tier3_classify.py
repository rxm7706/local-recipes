"""Story 43.1: reference ``classify()`` in ``bmad_drift_check.py`` stays aligned with factory."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bmad_drift_check.py"
DOCTOR_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
if str(DOCTOR_SRC) not in sys.path:
    sys.path.insert(0, str(DOCTOR_SRC))

from pyforge.doctor.sources import factory  # noqa: E402

SAMPLE_RELS = (
    "implementation-artifacts/recall-feedback__97.2__pyforge-marshal-20261012T103206150Z-210a0f06.md",
    "implementation-artifacts/recall-feedback__97.2__pyforge-marshal-20261012T103206150Z-210a0f06.md.query-ran",
    "implementation-artifacts/epic-97-continuity.md",
    "implementation-artifacts/session-advisories/run-1/journal.jsonl",
    "implementation-artifacts/dispatch-runs-quarantine/run-1/journal.jsonl",
    "implementation-artifacts/dispatch-runs-quarantine/README.md",
    "implementation-artifacts/token-economy-benchmark-2026-10-12T103206Z.json",
    "implementation-artifacts/token-economy-benchmark-per-layer-2026-10-12T103206Z.json",
    "implementation-artifacts/bmad-build-auto-result-97-2-some-story.md",
    "implementation-artifacts/97-2-x-attempted-change.patch",
    "implementation-artifacts/recall-feedback.md",
    "implementation-artifacts/recall-feedback__97.2.md",
    "implementation-artifacts/recall-feedback__a__b.txt",
    "implementation-artifacts/notes.query-ran",
    "implementation-artifacts/session-advisories.md",
    "implementation-artifacts/token-economy-benchmark.json",
    "implementation-artifacts/epic-x-continuity.md",
    "implementation-artifacts/bmad-build-auto-result.md",
    "implementation-artifacts/randomfile.txt",
    "implementation-artifacts/dispatch-runs/run-1/journal.jsonl",
)


def _load_script_mod(tmp_root: Path):
    spec = importlib.util.spec_from_file_location("bmad_drift_tier3_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPO_ROOT = tmp_root
    mod.PROJ = tmp_root / "_bmad-output" / "projects" / "pyforge-marshal"
    mod.PLAN = mod.PROJ / "planning-artifacts"
    mod.IMPL = mod.PROJ / "implementation-artifacts"
    return mod


@pytest.fixture
def drift_repo(tmp_path: Path):
    proj = tmp_path / "_bmad-output" / "projects" / "pyforge-marshal"
    proj.mkdir(parents=True)
    mod = _load_script_mod(tmp_path)
    return tmp_path, mod


@pytest.mark.parametrize("rel", SAMPLE_RELS)
def test_reference_classify_matches_factory(rel: str, drift_repo) -> None:
    repo_root, mod = drift_repo
    suffix = rel.removeprefix("implementation-artifacts/")
    path = factory._proj(repo_root) / suffix
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")
    assert mod.classify(path) == factory.classify(path, repo_root)


def test_do_fix_keeps_attempted_change_patch(drift_repo) -> None:
    tmp_path, mod = drift_repo
    impl = mod.IMPL
    impl.mkdir(parents=True, exist_ok=True)
    kept = impl / "97-2-x-attempted-change.patch"
    kept.write_text("diff\n", encoding="utf-8")
    stray = impl / "review-diff.patch"
    stray.write_text("diff\n", encoding="utf-8")
    bak = impl / "scratch.bak"
    bak.write_text("x\n", encoding="utf-8")
    actions = mod.do_fix()
    assert kept.is_file()
    assert not stray.exists()
    assert not bak.exists()
    assert any("review-diff.patch" in a for a in actions)
    assert any("scratch.bak" in a for a in actions)
    assert not any("attempted-change" in a for a in actions)
