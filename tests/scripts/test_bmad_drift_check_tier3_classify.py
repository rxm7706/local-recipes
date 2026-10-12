"""Story 43.1: reference ``classify()`` in ``bmad_drift_check.py`` stays aligned with factory.

AC5: for every sample path in the doctor meta-test's shape table and every AC2 look-alike,
the script's hand-synced reference ``classify()`` returns the same class as
``sources/factory.py``'s -- and that class is the one the sample is declared to have, so
a planting mistake (or a classifier that returns ``UNKNOWN`` for everything) cannot make
the agreement vacuous. Every sample is planted under ``implementation-artifacts/``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bmad_drift_check.py"
DOCTOR_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
META_TEST = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "pyforge-doctor"
    / "tests"
    / "meta"
    / "test_bmad_drift_tier3_marshal_shapes.py"
)
if str(DOCTOR_SRC) not in sys.path:
    sys.path.insert(0, str(DOCTOR_SRC))

from pyforge.doctor.sources import factory


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


#: The meta-test's shape table, read from that file (never hand-copied here).
_SHAPE_SAMPLES: tuple[tuple[str, str], ...] = tuple(
    (row.sample_rel, row.expected_class) for row in _load("bmad_drift_tier3_meta_table", META_TEST)._SHAPE_TABLE
)

#: Beyond the table: the real recall-feedback pair name, the quarantine README, a dotted /
#: mixed-case ``bmad-build-auto-result`` slug (R9), a moved-rule control, patches inside run
#: records that are not a failed attempt's ``changes.patch`` (``local:run-journal``, so
#: still ``stray-file``), and the AC2 look-alikes and stray-suffix files (all ``UNKNOWN``).
_EXTRA_SAMPLES: tuple[tuple[str, str], ...] = (
    (
        "implementation-artifacts/recall-feedback__97.2__pyforge-marshal-20261012T103206150Z-210a0f06.md",
        "local:recall-feedback",
    ),
    (
        "implementation-artifacts/recall-feedback__97.2__pyforge-marshal-20261012T103206150Z-210a0f06.md.query-ran",
        "local:recall-feedback",
    ),
    ("implementation-artifacts/dispatch-runs-quarantine/README.md", "local:run-journal"),
    ("implementation-artifacts/bmad-build-auto-result-97.2-Some_Story.md", "local:run-result"),
    ("implementation-artifacts/sprint-status-pyforge-marshal.yaml", "local:sprint-feed"),
    ("implementation-artifacts/dispatch-runs/run-a/failed/97.2/other.patch", "local:run-journal"),
    ("implementation-artifacts/dispatch-runs/run-a/changes.patch", "local:run-journal"),
    ("implementation-artifacts/runs/run-a/failed/97.2/changes.patch", "local:run-journal"),
    ("implementation-artifacts/fleet-drain-runs/other.lock", "UNKNOWN"),
    ("implementation-artifacts/fleet-drain-runs/campaign", "UNKNOWN"),
    ("implementation-artifacts/fleet-drain-runs/campaign.lock.bak", "UNKNOWN"),
    ("implementation-artifacts/recall-feedback.md", "UNKNOWN"),
    ("implementation-artifacts/recall-feedback__97.2.md", "UNKNOWN"),
    ("implementation-artifacts/recall-feedback__a__b.txt", "UNKNOWN"),
    ("implementation-artifacts/notes.query-ran", "UNKNOWN"),
    ("implementation-artifacts/session-advisories.md", "UNKNOWN"),
    ("implementation-artifacts/token-economy-benchmark.json", "UNKNOWN"),
    ("implementation-artifacts/epic-x-continuity.md", "UNKNOWN"),
    ("implementation-artifacts/bmad-build-auto-result.md", "UNKNOWN"),
    ("implementation-artifacts/randomfile.txt", "UNKNOWN"),
    ("implementation-artifacts/review-diff.patch", "UNKNOWN"),
    ("implementation-artifacts/scratch.bak", "UNKNOWN"),
)

SAMPLES = _SHAPE_SAMPLES + _EXTRA_SAMPLES


def _load_script_mod(tmp_root: Path):
    mod = _load("bmad_drift_tier3_under_test", SCRIPT)
    mod.REPO_ROOT = tmp_root
    mod.PROJ = tmp_root / "_bmad-output" / "projects" / "pyforge-marshal"
    mod.PLAN = mod.PROJ / "planning-artifacts"
    mod.IMPL = mod.PROJ / "implementation-artifacts"
    return mod


@pytest.fixture
def drift_repo(tmp_path: Path):
    factory._proj(tmp_path).mkdir(parents=True)
    mod = _load_script_mod(tmp_path)
    assert mod.PROJ == factory._proj(tmp_path)
    return tmp_path, mod


def test_meta_table_was_read() -> None:
    assert len(_SHAPE_SAMPLES) >= 14
    assert {cls for _, cls in _SHAPE_SAMPLES} >= {"local:recall-feedback", "local:attempted-change"}


def test_reference_rows_and_kept_classes_equal_factorys(drift_repo) -> None:
    """Same rows in the same order (first match wins) and the same kept classes."""
    _repo_root, mod = drift_repo
    factory_rows = [(rule.pattern.pattern, rule.classification) for rule in factory.TIER3_RUN_ARTIFACTS]
    assert list(mod._TIER3_RUN_ARTIFACT_PATTERNS) == factory_rows
    assert mod._TIER3_KEPT_CLASSES == factory.TIER3_KEPT_CLASSES


@pytest.mark.parametrize(("rel", "expected"), SAMPLES, ids=[rel for rel, _ in SAMPLES])
def test_reference_classify_matches_factory(rel: str, expected: str, drift_repo) -> None:
    repo_root, mod = drift_repo
    assert rel.startswith("implementation-artifacts/")
    path = factory._impl(repo_root) / rel.removeprefix("implementation-artifacts/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")
    assert factory._rel(path, repo_root) == rel
    assert factory.classify(path, repo_root) == expected
    assert mod.classify(path) == expected


def test_do_fix_keeps_attempted_change_patch(drift_repo) -> None:
    _tmp_path, mod = drift_repo
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


def test_do_fix_keep_follows_the_reference_table(drift_repo) -> None:
    """``do_fix``'s keep is derived from the reference table's class: a row that no longer
    claims the attempted-change patch lets ``--fix`` remove it."""
    _tmp_path, mod = drift_repo
    mod.IMPL.mkdir(parents=True, exist_ok=True)
    patch = mod.IMPL / "97-2-x-attempted-change.patch"
    patch.write_text("diff\n", encoding="utf-8")
    mod._TIER3_RUN_ARTIFACT_RULES = tuple(
        (pattern, cls) for pattern, cls in mod._TIER3_RUN_ARTIFACT_RULES if cls != "local:attempted-change"
    )
    assert any("attempted-change" in a for a in mod.do_fix())
    assert not patch.exists()


def test_do_fix_never_reaches_a_failed_attempt_patch(drift_repo) -> None:
    """``do_fix`` removes root-level strays only (``IMPL.iterdir()``), and a failed
    attempt's ``dispatch-runs/<run>/failed/<story>/changes.patch`` is a kept class as well,
    so ``--fix`` leaves it in place."""
    _tmp_path, mod = drift_repo
    kept = mod.IMPL / "dispatch-runs" / "run-a" / "failed" / "97.2" / "changes.patch"
    kept.parent.mkdir(parents=True)
    kept.write_text("diff\n", encoding="utf-8")
    assert mod._is_kept_tier3_artifact(mod._rel(kept))
    mod.do_fix()
    assert kept.is_file()
