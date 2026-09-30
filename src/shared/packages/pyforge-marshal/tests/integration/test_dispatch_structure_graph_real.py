"""Integration test -- Story 77.1 (spec-pyforge-marshal CAP-282): the dispatch
half of the ``structure-graph`` layer against the REAL ``codegraph`` binary.

The unit suite (``tests/unit/test_dispatch_structure_graph.py``) pins every
argv, ceiling and outcome against fakes. What a fake cannot prove is the claim
the whole story rests on: an index built in one directory, copied into a
sibling worktree and synced there, *answers for the worktree*. Measured
2026-09-29 while writing the story -- the index stores no absolute path, and a
symbol that exists only in the worktree is found there and not in the base --
and pinned here so a codegraph release that changes it fails a test rather than
sending sessions to another checkout's files.

Also pinned against the real binary: the fallback the story's failure ladder
depends on. A damaged copied index makes ``codegraph sync`` exit non-zero, and
``codegraph init -y`` over an existing ``.codegraph/`` exits 0 having done
nothing, so the seed must clear the copy before it rebuilds.

Skipped, with the reason, where ``codegraph`` is not on PATH or will not run
(it needs a supported Node; the ``pyforge-guild`` environment carries both).
Run it there: ``pixi run -e pyforge-guild pytest <this file>``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess

import pyforge.marshal.cli.dispatch as dispatch_module
from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.seed.verbs.kit import build_codegraph_index

_ENABLED = {"structure-graph": {"enabled": True, "aggressiveness": "medium"}}
_BASE_SYMBOL = "zebra_quokka_frobnicate"
_WORKTREE_ONLY_SYMBOL = "wt_only_platypus_marker"

_ALPHA = f'''def {_BASE_SYMBOL}(value):
    """Frobnicate a value."""
    return helper_widget(value) + 1


def helper_widget(value):
    return value * 2
'''
_BETA = f"""from pkg.alpha import {_BASE_SYMBOL}


class Runner:
    def go(self):
        return {_BASE_SYMBOL}(3)
"""
_WORKTREE_ONLY = f"""

def {_WORKTREE_ONLY_SYMBOL}():
    return 42
"""


def _codegraph_unusable_reason() -> str | None:
    binary = shutil.which("codegraph")
    if binary is None:
        return "codegraph is not on PATH (it is in the pyforge-guild environment)"
    probe = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=60)
    if probe.returncode != 0:
        tail = (probe.stderr or probe.stdout).strip().splitlines()
        return f"codegraph is on PATH but will not run: {tail[-1] if tail else 'no output'}"
    return None


_UNUSABLE = _codegraph_unusable_reason()
pytestmark = pytest.mark.skipif(_UNUSABLE is not None, reason=_UNUSABLE or "")


def _write_tree(root: Path, *, worktree_only: bool) -> None:
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "alpha.py").write_text(_ALPHA + (_WORKTREE_ONLY if worktree_only else ""), encoding="utf-8")
    (root / "pkg" / "beta.py").write_text(_BETA, encoding="utf-8")


def _context(directory: Path, symbol: str) -> dict[str, object]:
    result = subprocess.run(
        ["codegraph", "context", symbol, "--format", "json", "--no-code"],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _entry_files(directory: Path, symbol: str) -> list[str]:
    context = _context(directory, symbol)
    return [entry["filePath"] for entry in context["entryPoints"] if entry["name"] == symbol]


def _snapshot(directory: Path) -> dict[str, tuple[int, int]]:
    return {
        str(path.relative_to(directory)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _build_base(tmp_path: Path) -> Path:
    primary = tmp_path / "primary"
    _write_tree(primary, worktree_only=False)
    failure = build_codegraph_index(primary, stale=False, process=PosixProcess())
    assert failure is None, failure
    assert (primary / ".codegraph" / "codegraph.db").is_file()
    return primary


def _seed(primary: Path, worktree: Path):
    return dispatch_module._seed_dispatch_structure_graph(
        fs=LocalFs(),
        process=PosixProcess(),
        worktree=worktree,
        repo_root=primary,
        context_payload=_ENABLED,
    )


def test_a_worktree_seeded_from_a_base_in_a_sibling_directory_answers_for_the_worktree(tmp_path: Path) -> None:
    primary = _build_base(tmp_path)
    worktree = tmp_path / "worktree"
    _write_tree(worktree, worktree_only=True)
    base_before = _snapshot(primary / ".codegraph")

    result = _seed(primary, worktree)

    assert result.findings == ()
    assert (result.applied, result.mode, result.reason) == (True, "sync", None)
    # The index answers for a symbol that exists only in the worktree, with a path inside it ...
    [relative] = _entry_files(worktree, _WORKTREE_ONLY_SYMBOL)
    assert (worktree / relative).is_file()
    assert _WORKTREE_ONLY_SYMBOL in (worktree / relative).read_text(encoding="utf-8")
    assert _WORKTREE_ONLY_SYMBOL not in (primary / relative).read_text(encoding="utf-8")
    # ... and it still answers for the code both trees share.
    assert _entry_files(worktree, _BASE_SYMBOL) == ["pkg/alpha.py"]
    # Provisioning never wrote to the base (snapshotted before anything opens its db) ...
    assert _snapshot(primary / ".codegraph") == base_before
    # ... and the base never learned of the worktree's symbol.
    assert _entry_files(primary, _WORKTREE_ONLY_SYMBOL) == []


def test_a_synced_worktree_index_drops_a_file_the_worktree_removed(tmp_path: Path) -> None:
    primary = _build_base(tmp_path)
    worktree = tmp_path / "worktree"
    _write_tree(worktree, worktree_only=False)
    (worktree / "pkg" / "beta.py").unlink()

    result = _seed(primary, worktree)

    assert result.mode == "sync"
    assert _entry_files(worktree, "Runner") == []
    assert _entry_files(primary, "Runner") == ["pkg/beta.py"]


def test_a_damaged_copied_index_is_cleared_and_rebuilt_with_init(tmp_path: Path) -> None:
    primary = _build_base(tmp_path)
    (primary / ".codegraph" / "codegraph.db").write_bytes(b"not a sqlite database")
    worktree = tmp_path / "worktree"
    _write_tree(worktree, worktree_only=True)

    result = _seed(primary, worktree)

    assert (result.applied, result.mode) == (True, "init")
    assert [finding.code for finding in result.findings] == ["MRS-DISP-053"]
    [relative] = _entry_files(worktree, _WORKTREE_ONLY_SYMBOL)
    assert (worktree / relative).is_file()


def test_with_no_base_index_the_worktree_is_built_with_init(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    primary.mkdir()
    worktree = tmp_path / "worktree"
    _write_tree(worktree, worktree_only=True)

    result = _seed(primary, worktree)

    assert (result.applied, result.mode) == (True, "init")
    assert [finding.code for finding in result.findings] == ["MRS-DISP-053"]
    assert not (primary / ".codegraph").exists()
    [relative] = _entry_files(worktree, _WORKTREE_ONLY_SYMBOL)
    assert (worktree / relative).is_file()
