"""Unit tests for pyforge.scribe.extras.graphify -- the graphify
`compile_surface` ingest extra (Story 6.1).

`graphifyy` is NOT a declared dependency of the lean `pyforge-scribe` pixi
env (it is an optional extra, off by default per AD-6/air-gap) -- every "on
mode" test here drives the adapter through a hand-rolled fake `graphify`
module double rather than the real package, so this suite passes
identically whether or not graphifyy happens to be installed. The one
"genuinely unavailable" test below is the exception: it skips itself if
graphifyy IS installed in the current environment, rather than asserting a
result that would flip.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyforge.scribe.extras import graphify as graphify_module
from pyforge.scribe.extras.graphify import (
    DEFAULT_GRAPHIFY_TARGET,
    DEFAULT_GRAPHIFY_TARGETS,
    GRAPHIFY_EXTRA_ENV,
    GraphifyUnavailableError,
    _graphify_api,
    build_graph_report,
    graphify_extra_enabled,
    ingest_repo,
)

_SCRIBE_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "scribe"


class _FakeGraph:
    def __init__(self, nodes: dict[str, dict]) -> None:
        self._nodes = nodes

    def nodes(self, data: bool = False):
        items = list(self._nodes.items())
        return items if data else [nid for nid, _ in items]

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return 0


class _FakeGraphifyModule:
    """A duck-typed double for the top-level `graphify` public API this
    adapter calls: `collect_files`, `extract`, `build_from_json`,
    `god_nodes`."""

    def __init__(self, nodes: dict[str, dict], god: list[dict] | None = None) -> None:
        self._nodes = nodes
        self._god = god or []
        self.extract_calls: list[dict] = []

    def collect_files(self, target, root=None):
        return [Path(target) / "a.py"]

    def extract(self, files, cache_root=None, root=None, parallel=True):
        self.extract_calls.append({"files": files, "cache_root": cache_root, "root": root, "parallel": parallel})
        return {"nodes": [], "edges": [], "hyperedges": []}

    def build_from_json(self, extraction, root=None):
        return _FakeGraph(self._nodes)

    def god_nodes(self, graph, top_n=10):
        return self._god


class _ExtractSubmodule:
    """graphifyy's `graphify.extract` after `collect_files` imports the
    submodule -- not callable; the function lives at `.extract`."""

    def __init__(self, parent: "_ShadowingGraphifyModule") -> None:
        self._parent = parent

    def extract(self, files, cache_root=None, root=None, parallel=True):
        return self._parent.extract_impl(files, cache_root, root, parallel)


class _ShadowingGraphifyModule(_FakeGraphifyModule):
    """Live graphifyy shape: `extract` is a module, `extract.extract` is
    the callable Story 8.2 / CAP-1 must unwrap."""

    def __init__(self, nodes: dict[str, dict], god: list[dict] | None = None) -> None:
        super().__init__(nodes, god)
        self.extract = _ExtractSubmodule(self)

    def extract_impl(self, files, cache_root=None, root=None, parallel=True):
        return super().extract(files, cache_root, root, parallel)


# --- env-var gating (AC1) ------------------------------------------------


def test_graphify_extra_enabled_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(GRAPHIFY_EXTRA_ENV, raising=False)
    assert graphify_extra_enabled() is False


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
def test_graphify_extra_enabled_parses_env_var(monkeypatch: pytest.MonkeyPatch, value: str, expected: bool) -> None:
    monkeypatch.setenv(GRAPHIFY_EXTRA_ENV, value)
    assert graphify_extra_enabled() is expected


# --- ingest_repo() ---------------------------------------------------------


def test_ingest_repo_missing_target_warns_and_never_imports_graphify(tmp_path: Path) -> None:
    """No `src/shared/packages/` in this repo -- degrades to a warning
    without ever needing graphifyy installed (target check runs before the
    lazy import)."""
    warnings: list[str] = []
    nodes = ingest_repo(tmp_path, warnings=warnings)

    assert nodes == []
    assert len(warnings) == 1
    assert "do not exist" in warnings[0]


def test_ingest_repo_raises_clear_error_when_graphify_not_installed(tmp_path: Path) -> None:
    try:
        import graphify  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("graphifyy is installed in this environment")

    target = tmp_path / DEFAULT_GRAPHIFY_TARGET
    target.mkdir(parents=True)
    (target / "a.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(GraphifyUnavailableError):
        ingest_repo(tmp_path)


def test_ingest_repo_converts_nodes_and_drops_sourceless_stubs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("def foo():\n    pass\n", encoding="utf-8")

    fake_nodes = {
        "python:example.foo": {
            "label": "foo()",
            "type": "function",
            "source_file": "src/shared/packages/example.py",
            "source_location": "L1",
        },
        "python:stub": {
            # graphify's own "sourceless" cross-file-reference stub -- must
            # be dropped, it has nothing citable.
            "label": "Stub",
            "source_file": "",
        },
    }
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes))

    warnings: list[str] = []
    nodes = ingest_repo(tmp_path, warnings=warnings)

    assert warnings == []
    assert len(nodes) == 1
    node = nodes[0]
    assert node.kind == "code"
    assert node.id == "code:python:example.foo"
    assert node.title == "foo()"
    assert node.citation == "src/shared/packages/example.py:L1"


def test_ingest_repo_node_without_source_location_citation_is_bare_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")

    fake_nodes = {
        "python:example": {
            "label": "example",
            "type": "module",
            "source_file": "src/shared/packages/example.py",
        }
    }
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes))

    nodes = ingest_repo(tmp_path)

    assert len(nodes) == 1
    assert nodes[0].citation == "src/shared/packages/example.py"


def test_ingest_repo_writes_through_the_same_flatfile_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC2: never a parallel store -- the returned nodes upsert cleanly
    through the ordinary `GraphStore` port."""
    from pyforge.scribe.graph_store import FlatFileGraphStore

    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")
    fake_nodes = {
        "python:example": {
            "label": "example",
            "source_file": "src/shared/packages/example.py",
            "source_location": "L1",
        }
    }
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes))

    nodes = ingest_repo(tmp_path)
    store = FlatFileGraphStore(tmp_path / "graph.json")
    store.reset()
    for node in nodes:
        store.upsert_node(node)
    store.commit()

    reopened = FlatFileGraphStore(tmp_path / "graph.json")
    assert [n.id for n in reopened.iter_nodes()] == ["code:python:example"]


def test_graphify_api_unwraps_submodule_shadowing_the_callable() -> None:
    fake = _ShadowingGraphifyModule({})
    extract = _graphify_api(fake, "extract")
    assert extract.__func__ is fake.extract.extract.__func__


def test_ingest_repo_unwraps_extract_submodule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")
    fake_nodes = {
        "python:example": {
            "label": "example",
            "source_file": "src/shared/packages/example.py",
        }
    }
    fake = _ShadowingGraphifyModule(fake_nodes)
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: fake)

    nodes = ingest_repo(tmp_path)

    assert len(nodes) == 1
    assert fake.extract_calls
    assert nodes[0].kind == "code"


def test_ingest_repo_never_creates_a_foundry_root_graphify_out_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: graphify's own AST cache is redirected under Scribe's already-
    gitignored `.claude/data/` home -- no `graphify-out/` at the foundry
    root."""
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    (target / "example.py").write_text("x = 1\n", encoding="utf-8")
    fake = _FakeGraphifyModule({})
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: fake)

    ingest_repo(tmp_path)

    assert not (tmp_path / "graphify-out").exists()
    cache_dir = tmp_path / ".claude" / "data" / "pyforge-scribe" / "graphify-cache"
    assert cache_dir.is_dir()
    assert fake.extract_calls[0]["cache_root"] == cache_dir
    assert fake.extract_calls[0]["root"] == tmp_path


# --- build_graph_report() (AC3) --------------------------------------------


def test_build_graph_report_missing_target_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        build_graph_report(tmp_path)


def test_build_graph_report_includes_god_node_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    fake_nodes = {"a": {"label": "A", "source_file": "src/shared/packages/a.py"}}
    god = [{"id": "a", "label": "A", "degree": 5}]
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule(fake_nodes, god))

    report = build_graph_report(tmp_path)

    assert report.startswith("# GRAPH_REPORT")
    assert "nodes: 1" in report
    assert "## God Nodes" in report
    assert "A (degree=5)" in report


def test_build_graph_report_no_god_nodes_says_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "src" / "shared" / "packages"
    target.mkdir(parents=True)
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: _FakeGraphifyModule({}, []))

    report = build_graph_report(tmp_path)

    assert "(none)" in report


# --- AC4: graphifyy is imported only inside this adapter --------------------


def test_graphify_package_not_imported_at_module_level_in_the_adapter() -> None:
    tree = ast.parse((_SCRIBE_SRC / "extras" / "graphify.py").read_text(encoding="utf-8"))
    for node in tree.body:  # top-level statements only -- lazy imports inside
        # function bodies are fine and expected; this walks module scope only.
        if isinstance(node, ast.Import):
            assert "graphify" not in {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "graphify"


@pytest.mark.parametrize(
    "rel",
    ["compile.py", "recall.py", "cli.py", "graph_store.py", "graph_store_plugins.py"],
)
def test_graphify_not_imported_outside_the_extras_adapter(rel: str) -> None:
    tree = ast.parse((_SCRIBE_SRC / rel).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    # `from pyforge.scribe.extras.graphify import ...` binds "pyforge", not
    # the third-party "graphify" package -- this only flags a direct import
    # of the bare package itself.
    assert "graphify" not in imported, f"{rel} imports graphify directly"


def test_default_graphify_targets_are_the_named_list_not_recipes() -> None:
    rels = {p.as_posix() for p in DEFAULT_GRAPHIFY_TARGETS}
    assert rels == {"src/shared/packages", "src/platform", "scripts"}
    assert DEFAULT_GRAPHIFY_TARGET.as_posix() == "src/shared/packages"


class _PerTargetFake(_FakeGraphifyModule):
    def __init__(self) -> None:
        super().__init__({})
        self.seen: list[Path] = []
        self._last: Path | None = None

    def collect_files(self, target, root=None):
        self._last = Path(target)
        self.seen.append(self._last)
        return [self._last / "a.py"]

    def build_from_json(self, extraction, root=None):
        last = self._last
        assert last is not None
        posix = last.as_posix()
        rel = next(
            name for name in ("src/shared/packages", "src/platform", "scripts", "recipes") if posix.endswith(name)
        )
        return _FakeGraph(
            {
                f"python:{rel}": {
                    "label": rel,
                    "type": "module",
                    "source_file": f"{rel}/a.py",
                    "source_location": "L1",
                }
            }
        )


def test_ingest_repo_walks_named_list_and_skips_recipes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rel in (
        "src/shared/packages",
        "src/platform",
        "scripts",
        "recipes",
    ):
        path = tmp_path / rel
        path.mkdir(parents=True)
        (path / "a.py").write_text("x = 1\n", encoding="utf-8")
    fake = _PerTargetFake()
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: fake)
    warnings: list[str] = []

    nodes = ingest_repo(tmp_path, warnings=warnings)

    citations = {n.citation for n in nodes}
    assert "src/shared/packages/a.py:L1" in citations
    assert "src/platform/a.py:L1" in citations
    assert "scripts/a.py:L1" in citations
    assert not any(c.startswith("recipes/") for c in citations)
    assert warnings == []


def test_ingest_repo_missing_optional_targets_are_silent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packages = tmp_path / "src" / "shared" / "packages"
    packages.mkdir(parents=True)
    (packages / "a.py").write_text("x = 1\n", encoding="utf-8")
    fake = _PerTargetFake()
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: fake)
    warnings: list[str] = []

    nodes = ingest_repo(tmp_path, warnings=warnings)

    assert warnings == []
    assert {n.citation for n in nodes} == {"src/shared/packages/a.py:L1"}


def test_ingest_repo_explicit_target_stays_one_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rel in ("src/shared/packages", "scripts"):
        path = tmp_path / rel
        path.mkdir(parents=True)
        (path / "a.py").write_text("x = 1\n", encoding="utf-8")
    fake = _PerTargetFake()
    monkeypatch.setattr(graphify_module, "_import_graphify", lambda: fake)

    nodes = ingest_repo(tmp_path, target=Path("scripts"))

    assert {n.citation for n in nodes} == {"scripts/a.py:L1"}
    assert len(fake.seen) == 1


class _PerTargetFake(_FakeGraphifyModule):
    def __init__(self) -> None:
        super().__init__({})
        self.seen: list[Path] = []
        self._last: Path | None = None

    def collect_files(self, target, root=None):
        self._last = Path(target)
        self.seen.append(self._last)
        return [self._last / "a.py"]

    def build_from_json(self, extraction, root=None):
        last = self._last
        assert last is not None
        posix = last.as_posix()
        rel = next(
            name for name in ("src/shared/packages", "src/platform", "scripts", "recipes") if posix.endswith(name)
        )
        return _FakeGraph(
            {
                f"python:{rel}": {
                    "label": rel,
                    "type": "module",
                    "source_file": f"{rel}/a.py",
                    "source_location": "L1",
                }
            }
        )
