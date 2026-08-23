"""Unit tests for compliance_face phase guard + keys-not-blobs task args.

Runs without pytest-django: phases is Protocol-typed; task contract is
asserted from source so the Django addopts in pyproject.toml are overridden.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from compliance_face.phases import PHASES
from compliance_face.phases import advance
from compliance_face.phases import current_progress

TASKS_PATH = Path(__file__).resolve().parents[1] / "compliance_face" / "tasks.py"


class _Job:
    def __init__(self):
        self.phase_index = 0
        self.saved = []

    def save(self, update_fields=None):
        self.saved.append(list(update_fields or []))


def test_phase_guard_is_monotonic():
    job = _Job()
    assert current_progress(job).ratio == 0.0
    for name in PHASES:
        progress = advance(job, name)
        assert progress.name == name or progress.index == len(PHASES)
    assert job.phase_index == len(PHASES)
    with pytest.raises(RuntimeError, match="already complete"):
        advance(job, "validate")


def test_phase_guard_rejects_out_of_order():
    job = _Job()
    with pytest.raises(RuntimeError, match="phase guard"):
        advance(job, "scan")


def test_run_compliance_job_signature_is_key_only():
    """Celery task must accept job_id only — never blob bytes."""
    tree = ast.parse(TASKS_PATH.read_text(encoding="utf-8"))
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_compliance_job"
    )
    arg_names = [a.arg for a in fn.args.args]
    assert "job_id" in arg_names
    assert "manifest" not in arg_names
    assert "content" not in arg_names
    assert "blob" not in arg_names
