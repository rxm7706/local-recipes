"""Unit tests for pyforge.scribe.extras.cocoindex_flow -- the cocoindex
`compile_surface` incremental-ingest extra (Story 6.2).

`cocoindex` is NOT a declared dependency of the lean `pyforge-scribe` pixi
env (it is an optional extra, off by default per AD-6/air-gap) -- every "on
mode" test here drives the adapter through a hand-rolled fake `cocoindex`
module double rather than the real package, so this suite passes
identically whether or not cocoindex happens to be installed. The one
"genuinely unavailable" test below is the exception: it skips itself if
cocoindex IS installed in the current environment, rather than asserting a
result that would flip. Mirrors `test_extras_graphify.py` exactly.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from pyforge.scribe.extras import cocoindex_flow as cocoindex_module
from pyforge.scribe.extras.cocoindex_flow import (
    COCOINDEX_EXTRA_ENV,
    CocoindexUnavailableError,
    DerivedArtifact,
    cocoindex_extra_enabled,
    default_cocoindex_index_path,
    refresh_incremental,
)

_SCRIBE_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe"


class _FakeFingerprint:
    """Duck-typed double for `cocoindex._internal.core.Fingerprint`: the
    real object supports `bytes(fp)`. A deterministic digest of ``repr()``
    keeps this fake dependency-free while still varying with content."""

    def __init__(self, obj: object) -> None:
        import hashlib

        self._digest = hashlib.sha256(repr(obj).encode("utf-8")).digest()[:16]

    def __bytes__(self) -> bytes:
        return self._digest


class _FakeCocoindexModule:
    """A duck-typed double for the top-level `cocoindex` public API this
    adapter calls: `memo_fingerprint`."""

    def __init__(self) -> None:
        self.calls: list[object] = []

    def memo_fingerprint(self, obj: object) -> _FakeFingerprint:
        self.calls.append(obj)
        return _FakeFingerprint(obj)


@pytest.fixture()
def fake_cocoindex(monkeypatch: pytest.MonkeyPatch) -> _FakeCocoindexModule:
    fake = _FakeCocoindexModule()
    monkeypatch.setattr(cocoindex_module, "_import_cocoindex", lambda: fake)
    return fake


# --- env-var gating (AC1) ----------------------------------------------------


def test_cocoindex_extra_enabled_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(COCOINDEX_EXTRA_ENV, raising=False)
    assert cocoindex_extra_enabled() is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("nope", False),
    ],
)
def test_cocoindex_extra_enabled_parses_env_var(monkeypatch: pytest.MonkeyPatch, value: str, expected: bool) -> None:
    monkeypatch.setenv(COCOINDEX_EXTRA_ENV, value)
    assert cocoindex_extra_enabled() is expected


# --- refresh_incremental() unavailable-package path --------------------------


def test_refresh_incremental_raises_clear_error_when_cocoindex_not_installed(
    tmp_path: Path,
) -> None:
    try:
        import cocoindex  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("cocoindex is installed in this environment")

    artifact = DerivedArtifact(name="a", sources=(), derive=lambda: None)
    with pytest.raises(CocoindexUnavailableError):
        refresh_incremental(tmp_path, [artifact])


# --- refresh_incremental() incremental behavior (AC2) ------------------------


def test_refresh_incremental_first_run_derives_every_artifact(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    calls = {"a": 0, "b": 0}
    artifacts = [
        DerivedArtifact(name="a", sources=(), derive=lambda: calls.__setitem__("a", calls["a"] + 1)),
        DerivedArtifact(name="b", sources=(), derive=lambda: calls.__setitem__("b", calls["b"] + 1)),
    ]

    result = refresh_incremental(tmp_path, artifacts)

    assert calls == {"a": 1, "b": 1}
    assert result.refreshed == ("a", "b")
    assert result.skipped == ()
    assert result.index_path.is_file()


def test_refresh_incremental_second_run_unchanged_sources_skips_all(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    source_a = tmp_path / "a.txt"
    source_a.write_text("hello", encoding="utf-8")
    source_b = tmp_path / "b.txt"
    source_b.write_text("world", encoding="utf-8")
    calls = {"a": 0, "b": 0}

    def make_artifacts() -> list[DerivedArtifact]:
        return [
            DerivedArtifact(name="a", sources=(source_a,), derive=lambda: calls.__setitem__("a", calls["a"] + 1)),
            DerivedArtifact(name="b", sources=(source_b,), derive=lambda: calls.__setitem__("b", calls["b"] + 1)),
        ]

    first = refresh_incremental(tmp_path, make_artifacts())
    assert first.refreshed == ("a", "b")
    assert calls == {"a": 1, "b": 1}

    second = refresh_incremental(tmp_path, make_artifacts())

    assert calls == {"a": 1, "b": 1}  # zero recompute
    assert second.refreshed == ()
    assert second.skipped == ("a", "b")


def test_refresh_incremental_one_changed_source_refreshes_only_that_artifact(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    source_a = tmp_path / "a.txt"
    source_a.write_text("hello", encoding="utf-8")
    source_b = tmp_path / "b.txt"
    source_b.write_text("world", encoding="utf-8")
    calls = {"a": 0, "b": 0}

    def make_artifacts() -> list[DerivedArtifact]:
        return [
            DerivedArtifact(name="a", sources=(source_a,), derive=lambda: calls.__setitem__("a", calls["a"] + 1)),
            DerivedArtifact(name="b", sources=(source_b,), derive=lambda: calls.__setitem__("b", calls["b"] + 1)),
        ]

    refresh_incremental(tmp_path, make_artifacts())
    assert calls == {"a": 1, "b": 1}

    source_a.write_text("hello, changed", encoding="utf-8")
    result = refresh_incremental(tmp_path, make_artifacts())

    assert calls == {"a": 2, "b": 1}  # exactly one refresh, touching only "a"
    assert result.refreshed == ("a",)
    assert result.skipped == ("b",)


def test_refresh_incremental_directory_source_picks_up_new_file(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "one.py").write_text("x = 1\n", encoding="utf-8")
    calls = {"a": 0}

    def make_artifact() -> DerivedArtifact:
        return DerivedArtifact(name="a", sources=(target,), derive=lambda: calls.__setitem__("a", calls["a"] + 1))

    refresh_incremental(tmp_path, [make_artifact()])
    assert calls == {"a": 1}

    refresh_incremental(tmp_path, [make_artifact()])
    assert calls == {"a": 1}  # unchanged directory -- skipped

    (target / "two.py").write_text("y = 2\n", encoding="utf-8")
    refresh_incremental(tmp_path, [make_artifact()])
    assert calls == {"a": 2}  # a new file under the directory is a change


def test_refresh_incremental_directory_source_excludes_pycache_noise(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    """[HIGH fix] The graphify-ingest artifact's default source is
    `src/shared/packages` -- the exact tree an ordinary `pytest` run under
    this repo litters with fresh `__pycache__/*.pyc` churn. Without the same
    `_rglob_excluding`/`_EXCLUDED_DIR_NAMES` exclusion `move_list.py`/
    `compile.py` already apply, that churn would defeat AC2's "zero
    recompute on unchanged sources" promise in ordinary dev use."""
    target = tmp_path / "target"
    target.mkdir()
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")
    calls = {"a": 0}

    def make_artifact() -> DerivedArtifact:
        return DerivedArtifact(name="a", sources=(target,), derive=lambda: calls.__setitem__("a", calls["a"] + 1))

    refresh_incremental(tmp_path, [make_artifact()])
    assert calls == {"a": 1}

    pycache = target / "__pycache__"
    pycache.mkdir()
    (pycache / "example.cpython-312.pyc").write_bytes(b"\x00\x01\x02")

    result = refresh_incremental(tmp_path, [make_artifact()])

    assert calls == {"a": 1}  # __pycache__ churn must NOT count as a change
    assert result.skipped == ("a",)


def test_source_signature_file_that_vanishes_between_listing_and_stat_warns_not_crashes(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[MEDIUM fix] A file that disappears/becomes unreadable between the
    directory listing and `_file_entry`'s own `.stat()` call degrades to a
    warning and is skipped -- it must not crash the whole refresh, matching
    `scan_move_list`'s own `except OSError: continue` precedent. Monkeypatches
    `_rglob_excluding` (the listing step) to return a path that never
    actually existed on disk, simulating the listing having raced ahead of
    a since-deleted file without relying on a fragile global `Path.stat`
    patch (which `_rglob_excluding`'s own internal `is_file()` checks would
    otherwise also trip, before `_file_entry` is ever reached)."""
    target = tmp_path / "target"
    target.mkdir()
    ok_file = target / "ok.py"
    ok_file.write_text("x = 1\n", encoding="utf-8")
    vanished_file = target / "vanished.py"  # never created

    monkeypatch.setattr(
        cocoindex_module,
        "_rglob_excluding",
        lambda root, pattern: [ok_file, vanished_file],
    )

    warnings: list[str] = []
    artifact = DerivedArtifact(name="a", sources=(target,), derive=lambda: None)

    result = refresh_incremental(tmp_path, [artifact], warnings=warnings)

    assert result.refreshed == ("a",)
    assert any("could not be stat" in w and "vanished.py" in w for w in warnings)


def test_refresh_incremental_missing_source_is_deterministic_and_warns(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    missing = tmp_path / "does-not-exist"
    calls = {"a": 0}
    warnings: list[str] = []

    def make_artifact() -> DerivedArtifact:
        return DerivedArtifact(name="a", sources=(missing,), derive=lambda: calls.__setitem__("a", calls["a"] + 1))

    refresh_incremental(tmp_path, [make_artifact()], warnings=warnings)
    result = refresh_incremental(tmp_path, [make_artifact()], warnings=warnings)

    assert calls == {"a": 1}  # missing source is a stable signature -- skipped the 2nd time
    assert result.skipped == ("a",)
    assert any("does not exist" in w for w in warnings)


# --- AC3: outputs are bookkeeping only, never a store-of-record --------------


def test_index_lives_under_the_gitignored_data_home(tmp_path: Path) -> None:
    assert default_cocoindex_index_path(tmp_path) == (
        tmp_path / ".claude" / "data" / "pyforge-scribe" / "cocoindex-index.json"
    )


def test_index_file_holds_only_fingerprints_never_facts(tmp_path: Path, fake_cocoindex: _FakeCocoindexModule) -> None:
    artifact = DerivedArtifact(name="graphify-ingest", sources=(), derive=lambda: None)

    result = refresh_incremental(tmp_path, [artifact])

    document = json.loads(result.index_path.read_text(encoding="utf-8"))
    assert set(document.keys()) == {"fingerprints"}
    assert set(document["fingerprints"].keys()) == {"graphify-ingest"}
    fingerprint = document["fingerprints"]["graphify-ingest"]
    assert isinstance(fingerprint, str)
    # A hex digest, not a node/citation/text payload.
    assert re.fullmatch(r"[0-9a-f]+", fingerprint)


def test_refresh_incremental_survives_a_non_dict_top_level_index_document(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    """[LOW fix] A hand-corrupted index file holding a bare JSON list (or
    any other non-dict top level) must degrade to "no prior fingerprints"
    (first-run behavior) rather than raising `AttributeError` out of
    `.get("fingerprints", {})` on a list."""
    index_path = default_cocoindex_index_path(tmp_path)
    index_path.parent.mkdir(parents=True)
    index_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    calls = {"a": 0}
    artifact = DerivedArtifact(name="a", sources=(), derive=lambda: calls.__setitem__("a", calls["a"] + 1))

    result = refresh_incremental(tmp_path, [artifact], index_path=index_path)

    assert calls == {"a": 1}
    assert result.refreshed == ("a",)
    document = json.loads(index_path.read_text(encoding="utf-8"))
    assert document == {"fingerprints": {"a": document["fingerprints"]["a"]}}


def test_refresh_incremental_derive_failure_still_persists_prior_progress(
    tmp_path: Path, fake_cocoindex: _FakeCocoindexModule
) -> None:
    """A later artifact's `derive()` raising must not discard an earlier
    artifact's freshly-recorded fingerprint (the `finally`-guarded save)."""

    def boom() -> None:
        raise RuntimeError("boom")

    artifacts = [
        DerivedArtifact(name="ok", sources=(), derive=lambda: None),
        DerivedArtifact(name="broken", sources=(), derive=boom),
    ]

    with pytest.raises(RuntimeError, match="boom"):
        refresh_incremental(tmp_path, artifacts)

    index_path = default_cocoindex_index_path(tmp_path)
    document = json.loads(index_path.read_text(encoding="utf-8"))
    assert "ok" in document["fingerprints"]
    assert "broken" not in document["fingerprints"]


# --- AC4: cocoindex is imported only inside this adapter ---------------------


def test_cocoindex_package_not_imported_at_module_level_in_the_adapter() -> None:
    tree = ast.parse((_SCRIBE_SRC / "extras" / "cocoindex_flow.py").read_text(encoding="utf-8"))
    for node in tree.body:  # top-level statements only -- lazy imports inside
        # function bodies are fine and expected; this walks module scope only.
        if isinstance(node, ast.Import):
            assert "cocoindex" not in {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "cocoindex"


@pytest.mark.parametrize(
    "rel",
    [
        "compile.py",
        "recall.py",
        "cli.py",
        "graph_store.py",
        "graph_store_plugins.py",
        "extras/graphify.py",
        "extras/move_list.py",
    ],
)
def test_cocoindex_not_imported_outside_the_extras_adapter(rel: str) -> None:
    tree = ast.parse((_SCRIBE_SRC / rel).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # `from pyforge.scribe.extras.cocoindex_flow import ...` binds "pyforge",
    # not the third-party "cocoindex" package -- this only flags a direct
    # import of the bare package itself.
    assert "cocoindex" not in imported, f"{rel} imports cocoindex directly"


def test_no_cocoindex_serve_or_coco_fn_decorator_anywhere() -> None:
    """AC4: no `cocoindex.serve` MCP product, no `@coco.fn`/`@cocoindex.fn`
    lineage decorator anywhere in the package.

    Matches actual USAGE syntax only (a call with parens; a decorator line
    starting with ``@``) -- this module's own docstring names both strings
    in prose to document their absence, which a bare substring search would
    misflag as an offender of itself.
    """
    offenders: list[str] = []
    for path in sorted(_SCRIBE_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"cocoindex\s*\.\s*serve\s*\(", text):
            offenders.append(f"{path}: cocoindex.serve(")
        for line in text.splitlines():
            if re.match(r"@\s*coco(index)?\s*\.\s*fn\b", line.strip()):
                offenders.append(f"{path}: @coco(index).fn decorator")
    assert offenders == []
