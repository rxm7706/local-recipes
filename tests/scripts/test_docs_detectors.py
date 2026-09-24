"""Unit tests for ``scripts/docs_detectors.py`` (Story 30.3,
spec-pyforge-doctor CAP-84): docs/reference/detectors.md generated from
``scripts/detectors.py``'s own registry (``discover()`` +
``_DOCTOR_SOURCE_TASKS``), imported directly rather than duplicated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common  # noqa: E402
import detectors as detectors_registry  # noqa: E402
import docs_detectors as m  # noqa: E402

_STAMP = {"derived_at": "2026-01-01T00:00:00", "tree": "deadbeef"}


def _patch_registry(monkeypatch: pytest.MonkeyPatch, *, scanned=None, findings=None, doctor_tasks=None) -> None:
    monkeypatch.setattr(detectors_registry, "discover", lambda: (scanned or [], findings or []))
    monkeypatch.setattr(detectors_registry, "_DOCTOR_SOURCE_TASKS", tuple(doctor_tasks or ()))


def test_render_lists_scanned_scripts_and_doctor_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _patch_registry(
        monkeypatch,
        scanned=[{"path": "scripts/foo_check.py", "name": "foo_check", "scope": "repo", "task": "foo-check"}],
        doctor_tasks=[("docs-currency", "docs-currency-check")],
    )

    content = m.render(tmp_path, _STAMP)

    assert "`foo_check`" in content
    assert "`foo-check`" in content
    assert "`docs-currency`" in content
    assert "`docs-currency-check`" in content
    assert "Registry gaps" in content
    assert "None -- every scanned script" in content


def test_render_surfaces_registry_findings_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _patch_registry(monkeypatch, findings=["scripts/bad_check.py: looks like a detector but declares nothing"])

    content = m.render(tmp_path, _STAMP)

    assert "scripts/bad_check.py: looks like a detector but declares nothing" in content
    assert "None -- every scanned script" not in content


def test_render_marks_a_task_less_scanned_detector(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _patch_registry(
        monkeypatch,
        scanned=[{"path": "scripts/foo_check.py", "name": "foo_check", "scope": "repo", "task": None}],
    )

    content = m.render(tmp_path, _STAMP)

    assert "*(none)*" in content


def test_scope_lookup_degrades_to_unknown_when_doctor_is_unimportable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name.startswith("pyforge.doctor"):
            raise ImportError("blocked for this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    _patch_registry(monkeypatch, doctor_tasks=[("docs-currency", "docs-currency-check")])

    content = m.render(tmp_path, _STAMP)

    assert "| `docs-currency` | `unknown` | `docs-currency-check` |" in content


def test_render_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _patch_registry(
        monkeypatch,
        scanned=[{"path": "scripts/foo_check.py", "name": "foo_check", "scope": "repo", "task": "foo-check"}],
        doctor_tasks=[("docs-currency", "docs-currency-check")],
    )

    assert m.render(tmp_path, _STAMP) == m.render(tmp_path, dict(_STAMP))


def test_main_write_then_check_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _patch_registry(
        monkeypatch,
        scanned=[{"path": "scripts/foo_check.py", "name": "foo_check", "scope": "repo", "task": "foo-check"}],
    )
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "head_stamp", lambda root: dict(_STAMP))

    monkeypatch.setattr(sys, "argv", ["docs_detectors.py"])
    assert m.main() == 0

    monkeypatch.setattr(sys, "argv", ["docs_detectors.py", "--check"])
    assert m.main() == 0

    # A new detector registered, not yet regenerated -> --check reds it.
    _patch_registry(
        monkeypatch,
        scanned=[
            {"path": "scripts/foo_check.py", "name": "foo_check", "scope": "repo", "task": "foo-check"},
            {"path": "scripts/bar_check.py", "name": "bar_check", "scope": "repo", "task": "bar-check"},
        ],
    )
    assert m.main() == 1
