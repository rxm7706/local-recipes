"""Helpers both chain-regeneration test modules use (Story 116.2, spec-pyforge-marshal:CAP-305).

``test_chain_regen.py`` (the package half) and ``test_chain_regen_live_tree.py`` (the tests that render a sprint
ledger with the repository's own ``scripts/promote_sprint_status.py``) share the planning-tree seed and the recording
invoker; nothing here reads outside ``root``.
"""

from __future__ import annotations

from pathlib import Path


def seed_project(root: Path, slug: str) -> Path:
    """One project's planning tree and its Dream under ``root``: epics, a Spec folder, the Dream file."""
    planning = root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text("# Epics\n\nSee spec-demo.\n", encoding="utf-8")
    specs = planning / "specs"
    specs.mkdir()
    (specs / "spec-demo").mkdir()
    (specs / "spec-demo" / "SPEC.md").write_text(
        "---\nowner-dream: docs/dreams/demo.md\n---\n# Demo\n",
        encoding="utf-8",
    )
    dreams = root / "docs" / "dreams"
    dreams.mkdir(parents=True, exist_ok=True)
    dream_file = dreams / "demo.md"
    if not dream_file.is_file():
        dream_file.write_text("# demo\n", encoding="utf-8")
    return planning


class RecordingInvoker:
    """A planning-skill invoker that records each skill and answers complete, blocked or failed."""

    def __init__(self, *, blocked_at: str | None = None, fail_times: int = 0) -> None:
        self.calls: list[str] = []
        self._blocked_at = blocked_at
        self._fail_times = fail_times
        self._failures_left = fail_times

    def invoke_planning_skill(
        self,
        skill: str,
        *,
        root: Path,
        project: str,
        dream: Path,
        phase: str,
        run_dir: Path,
    ) -> object:
        del root, project, dream, run_dir
        self.calls.append(skill)
        if self._blocked_at is not None and phase == self._blocked_at:
            return type("R", (), {"status": "blocked", "detail": "blocked by fixture"})()
        if self._failures_left > 0:
            self._failures_left -= 1
            return type("R", (), {"status": "failed", "detail": "transient"})()
        return type("R", (), {"status": "complete", "detail": f"ok:{skill}"})()
