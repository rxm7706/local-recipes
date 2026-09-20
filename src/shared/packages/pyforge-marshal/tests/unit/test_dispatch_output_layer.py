"""Story 28.30 (SPEC-marshal-token-economy CAP-3, dispatch half of the
``output`` layer): ``_seed_dispatch_output_layer`` deploys the caveman
output-compression skill into a fresh dispatch worktree, mirroring what
``seed/verbs/kit.py::_apply_caveman_skill`` already does for a loop home.

``probe_instrument`` and ``packaged_seed_model_version`` are both
monkeypatched at the ``pyforge.marshal.cli.dispatch`` call site -- the same
injection-by-monkeypatch shape ``test_seed_kit.py`` uses for the identical
instrument-probe seam, so the whole matrix (layer off, instrument
unavailable, a real deploy, a write failure) is exercised without caveman
installed."""

from __future__ import annotations

from pathlib import Path

import pytest

import pyforge.marshal.cli.dispatch as dispatch_module
from pyforge.marshal.seed.detect.kit import InstrumentProbe
from pyforge.marshal.seed.model.kit import CAVEMAN_SKILL_RELPATH
from pyforge.marshal.seed.model.version import ModelVersion


class _FakeFs:
    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.files: dict[Path, str] = {}

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content


_ENABLED_OUTPUT = {"output": {"enabled": True, "aggressiveness": "medium"}}
_DISABLED_OUTPUT = {"output": {"enabled": False, "aggressiveness": "medium"}}
_MODEL_VERSION = ModelVersion.parse("1.0.0")


def test_layer_disabled_deploys_nothing(tmp_path: Path) -> None:
    fs = _FakeFs()

    result = dispatch_module._seed_dispatch_output_layer(fs=fs, worktree=tmp_path, context_payload=_DISABLED_OUTPUT)

    assert result is None
    assert fs.files == {}


def test_layer_absent_from_payload_deploys_nothing(tmp_path: Path) -> None:
    """A context payload with no ``output`` key at all reads the same as
    declared off -- never a crash on a missing key."""
    fs = _FakeFs()

    result = dispatch_module._seed_dispatch_output_layer(fs=fs, worktree=tmp_path, context_payload={})

    assert result is None
    assert fs.files == {}


def test_instrument_unavailable_degrades_with_a_named_finding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dispatch_module,
        "probe_instrument",
        lambda item: InstrumentProbe(available=False, reason="caveman is not installed here"),
    )
    fs = _FakeFs()

    result = dispatch_module._seed_dispatch_output_layer(fs=fs, worktree=tmp_path, context_payload=_ENABLED_OUTPUT)

    assert result is not None
    assert result.code == "MRS-DISP-042"
    assert result.severity.value == "warn"
    assert "caveman is not installed here" in result.message
    assert fs.files == {}


def test_available_instrument_deploys_the_rendered_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = tmp_path / "upstream" / "SKILL.md"
    payload.parent.mkdir(parents=True)
    payload.write_text("# caveman\n\nupstream skill body\n", encoding="utf-8")
    monkeypatch.setattr(
        dispatch_module,
        "probe_instrument",
        lambda item: InstrumentProbe(available=True, payload=payload),
    )
    monkeypatch.setattr(dispatch_module, "packaged_seed_model_version", lambda: _MODEL_VERSION)
    fs = _FakeFs()
    worktree = tmp_path / "worktree"

    result = dispatch_module._seed_dispatch_output_layer(fs=fs, worktree=worktree, context_payload=_ENABLED_OUTPUT)

    assert result is None
    target = worktree / CAVEMAN_SKILL_RELPATH
    assert target.parent in fs.dirs
    deployed = fs.files[target]
    assert "upstream skill body" in deployed
    assert "token-economy-articulate" in deployed


def test_model_version_resolution_failure_degrades_with_a_named_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = tmp_path / "SKILL.md"
    payload.write_text("# caveman\n", encoding="utf-8")
    monkeypatch.setattr(
        dispatch_module,
        "probe_instrument",
        lambda item: InstrumentProbe(available=True, payload=payload),
    )

    def _raise() -> ModelVersion:
        raise ValueError("packaged manifest missing")

    monkeypatch.setattr(dispatch_module, "packaged_seed_model_version", _raise)
    fs = _FakeFs()

    result = dispatch_module._seed_dispatch_output_layer(
        fs=fs, worktree=tmp_path / "worktree", context_payload=_ENABLED_OUTPUT
    )

    assert result is not None
    assert result.code == "MRS-DISP-042"
    assert "packaged manifest missing" in result.message
    assert fs.files == {}


def test_write_failure_degrades_with_a_named_finding_never_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = tmp_path / "SKILL.md"
    payload.write_text("# caveman\n", encoding="utf-8")
    monkeypatch.setattr(
        dispatch_module,
        "probe_instrument",
        lambda item: InstrumentProbe(available=True, payload=payload),
    )
    monkeypatch.setattr(dispatch_module, "packaged_seed_model_version", lambda: _MODEL_VERSION)

    class _RefusingFs(_FakeFs):
        def write_text_atomic(self, path: Path, content: str) -> None:
            raise OSError("disk full")

    result = dispatch_module._seed_dispatch_output_layer(
        fs=_RefusingFs(),
        worktree=tmp_path / "worktree",
        context_payload=_ENABLED_OUTPUT,
    )

    assert result is not None
    assert result.code == "MRS-DISP-042"
    assert "disk full" in result.message
