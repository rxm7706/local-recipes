"""Tests for _bmad/skf/shared/scripts/skf-provenance-gap-dispatch.py (Story 27.1)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "_bmad/skf/shared/scripts/skf-provenance-gap-dispatch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("skf_provenance_gap_dispatch", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_classify_retro_mirror_as_already_in_scope():
    m = _load_module()
    status, prior = m._classify(["retro-mirror"])
    assert status == m._ALREADY_IN_SCOPE
    assert prior == "retro-mirror"
