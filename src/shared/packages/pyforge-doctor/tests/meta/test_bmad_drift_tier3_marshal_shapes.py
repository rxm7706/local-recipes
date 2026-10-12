"""Story 43.1: ``TIER3_RUN_ARTIFACTS`` stays aligned with marshal Tier-3 writers (no import).

The scan reads ``pyforge-marshal``'s source with ``ast`` -- never by import, since the
classifier never imports the station it judges -- and collects every path segment marshal
builds directly under ``implementation-artifacts``. It recognises three forms:

- a ``/`` chain (``root / ... / slug / "implementation-artifacts" / X``), flattened, taking
  the operand after ``"implementation-artifacts"``;
- an f-string whose head is a call to a helper returning the Tier-3 directory
  (``f"{implementation_artifacts_relpath(slug)}/epic-{epic}-continuity.md"``);
- a string literal holding ``implementation-artifacts/<segment>``.

A ``Name`` resolves through the enclosing function's single assignment, then the module's
top-level ``str`` assignments; a call resolves through the single ``return`` of a top-level
function the scanned tree defines. Anything unresolved reads as ``{}``. A path built some
other way (a ``with_name`` suffix such as ``.query-ran``) is covered by its table row and
writer token, not by the scan -- the story's named residual risk.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from pyforge.doctor.sources import factory

REPO_ROOT = Path(__file__).resolve().parents[6]
MARSHAL_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-marshal" / "src" / "pyforge" / "marshal"
BMAD_BUILD_AUTO_WORKFLOW = REPO_ROOT / ".claude" / "skills" / "bmad-build-auto" / "workflow.md"
BMAD_BUILD_REVIEW_STEP = REPO_ROOT / ".claude" / "skills" / "bmad-build" / "step-04-review.md"
WORKTREE_SWEEP = REPO_ROOT / "scripts" / "worktree_sweep.py"

#: What the scan collects from live marshal at the story's baseline (``70975ae790``): the
#: twelve segments the planning prototype found. The scan must keep seeing every one -- a
#: blinded scan (a skipped writer file, an idiom it stops resolving) fails here.
_EXPECTED_MARSHAL_SEGMENTS = frozenset(
    {
        "deferred-work.md",
        "dispatch-runs",
        "dispatch-runs-quarantine",
        "epic-{}-context.md",
        "epic-{}-continuity.md",
        "fleet-drain-runs",
        "recall-feedback__{}__{}.md",
        "runs",
        "session-advisories",
        "sprint-status.yaml",
        "token-economy-benchmark-{}.json",
        "token-economy-benchmark-per-layer-{}.json",
    }
)


@dataclass(frozen=True)
class _ShapeRow:
    """One Tier-3 shape: the segments the scan collects for it (empty when the scan cannot
    see the writer's form), a sample path, the class ``classify()`` must give it, and the
    writer token that must stay in the cited source."""

    segments: tuple[str, ...]
    sample_rel: str
    expected_class: str
    writer_path: Path
    writer_token: str


_SHAPE_TABLE: tuple[_ShapeRow, ...] = (
    _ShapeRow(
        ("deferred-work.md",),
        "implementation-artifacts/deferred-work.md",
        "tracked:deferred",
        BMAD_BUILD_REVIEW_STEP,
        "{{.implementation_artifacts}}/deferred-work.md",
    ),
    _ShapeRow(
        ("dispatch-runs",),
        "implementation-artifacts/dispatch-runs/run-a/journal.jsonl",
        "local:run-journal",
        MARSHAL_SRC / "core" / "layer_savings_sources.py",
        "dispatch-runs",
    ),
    _ShapeRow(
        ("dispatch-runs-quarantine",),
        "implementation-artifacts/dispatch-runs-quarantine/run-a/journal.jsonl",
        "local:run-journal",
        MARSHAL_SRC / "core" / "dispatch_stale.py",
        "dispatch-runs-quarantine",
    ),
    _ShapeRow(
        ("epic-{}-continuity.md",),
        "implementation-artifacts/epic-97-continuity.md",
        "local:sprint-feed",
        MARSHAL_SRC / "core" / "derived_context.py",
        "continuity_output_relpath",
    ),
    _ShapeRow(
        ("epic-{}-context.md",),
        "implementation-artifacts/epic-97-context.md",
        "local:sprint-feed",
        MARSHAL_SRC / "core" / "derived_context.py",
        "implementation_artifacts_relpath",
    ),
    _ShapeRow(
        ("fleet-drain-runs",),
        "implementation-artifacts/fleet-drain-runs/run-a/journal.jsonl",
        "local:run-journal",
        MARSHAL_SRC / "core" / "dispatch_fleet.py",
        "fleet-drain-runs",
    ),
    _ShapeRow(
        ("recall-feedback__{}__{}.md",),
        "implementation-artifacts/recall-feedback__97.2__run.md",
        "local:recall-feedback",
        MARSHAL_SRC / "core" / "recall_feedback.py",
        "recall-feedback__",
    ),
    _ShapeRow(
        (),
        "implementation-artifacts/recall-feedback__97.2__run.md.query-ran",
        "local:recall-feedback",
        MARSHAL_SRC / "adapters" / "harness_bmadloop.py",
        ".query-ran",
    ),
    _ShapeRow(
        ("runs",),
        "implementation-artifacts/runs/run-a/journal.jsonl",
        "local:run-journal",
        MARSHAL_SRC / "cli" / "status.py",
        'implementation-artifacts" / "runs"',
    ),
    _ShapeRow(
        ("session-advisories",),
        "implementation-artifacts/session-advisories/run-a/journal.jsonl",
        "local:run-journal",
        MARSHAL_SRC / "cli" / "context.py",
        "session-advisories",
    ),
    _ShapeRow(
        # The story spec a run drafts into Tier-3 (``spin.py``), the recovered copy
        # ``deploy recover-spec`` writes, and the conformance-smoke home's fixture spec.
        ("spec-{}-{}{}.md", "spec-{}-{}{}-recovered.md", "spec-1-1-marshal-conformance-smoke.md"),
        "implementation-artifacts/spec-97-2-some-story.md",
        "tracked:spec",
        MARSHAL_SRC / "cli" / "deploy.py",
        "-recovered.md",
    ),
    _ShapeRow(
        ("sprint-status.yaml",),
        "implementation-artifacts/sprint-status.yaml",
        "local:sprint-feed",
        MARSHAL_SRC / "cli" / "land.py",
        "sprint-status.yaml",
    ),
    _ShapeRow(
        ("token-economy-benchmark-{}.json",),
        "implementation-artifacts/token-economy-benchmark-2026-10-12T103206Z.json",
        "local:benchmark",
        MARSHAL_SRC / "cli" / "benchmark.py",
        "token-economy-benchmark-",
    ),
    _ShapeRow(
        ("token-economy-benchmark-per-layer-{}.json",),
        "implementation-artifacts/token-economy-benchmark-per-layer-2026-10-12T103206Z.json",
        "local:benchmark",
        MARSHAL_SRC / "cli" / "benchmark.py",
        "token-economy-benchmark-per-layer-",
    ),
    _ShapeRow(
        (),
        "implementation-artifacts/bmad-build-auto-result-97-2-some-story.md",
        "local:run-result",
        BMAD_BUILD_AUTO_WORKFLOW,
        "bmad-build-auto-result-",
    ),
    _ShapeRow(
        (),
        "implementation-artifacts/bmad-build-auto-result-2026-10-12T103206Z.md",
        "local:run-result",
        BMAD_BUILD_AUTO_WORKFLOW,
        "bmad-build-auto-result-<slug-or-timestamp>.md",
    ),
    _ShapeRow(
        (),
        "implementation-artifacts/97-2-x-attempted-change.patch",
        "local:attempted-change",
        MARSHAL_SRC / "dispatch_supervisor" / "__main__.py",
        "*attempted-change*.patch",
    ),
    _ShapeRow(
        (),
        "implementation-artifacts/worktree-verdicts-2026-10-12.json",
        "local:sweep-verdicts",
        WORKTREE_SWEEP,
        "implementation-artifacts/worktree-verdicts-",
    ),
)

_ROWS_BY_SEGMENT: dict[str, _ShapeRow] = {segment: row for row in _SHAPE_TABLE for segment in row.segments}


# --- the scan ---------------------------------------------------------------------------

_HOLE = "{}"
_MAX_DEPTH = 10
_SEGMENT_AFTER_IMPL = re.compile(r"(?<![A-Za-z0-9_-])implementation-artifacts/([A-Za-z0-9._{}-]+)")
_ANGLE_PLACEHOLDER = re.compile(r"<[A-Za-z0-9_.-]+>")
#: Helpers that return a project's Tier-3 directory. Resolved through their own ``return``
#: when the scanned tree defines them; this name list covers a module scanned alone.
_IMPL_DIR_HELPERS = frozenset({"implementation_artifacts_relpath"})
#: Calls that pass a path through unchanged (``Path(x) / "y"``).
_PATH_PASSTHROUGH = frozenset({"Path", "PurePath", "PurePosixPath"})


@dataclass(frozen=True)
class _Hit:
    segment: str
    path: Path
    lineno: int

    @property
    def where(self) -> str:
        try:
            shown = self.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            shown = self.path.as_posix()
        return f"{shown}:{self.lineno}"


@dataclass
class _Module:
    path: Path
    tree: ast.Module
    #: Top-level names bound exactly once (``_DIRNAME = "session-advisories"``,
    #: ``_SPEC = f"spec-{_KEY}.md"``), to their value; ``None`` when bound more than once.
    constants: dict[str, ast.expr | None] = field(default_factory=dict)


@dataclass
class _Index:
    modules: list[_Module] = field(default_factory=list)
    functions: dict[str, list[tuple[_Module, ast.FunctionDef | ast.AsyncFunctionDef]]] = field(default_factory=dict)


def _parse_module(path: Path) -> _Module:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module = _Module(path=path, tree=tree)
    for stmt in tree.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target, value = stmt.targets[0], stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            target, value = stmt.target, stmt.value
        if isinstance(target, ast.Name) and value is not None:
            module.constants[target.id] = None if target.id in module.constants else value
    return module


def _build_index(paths: Iterable[Path]) -> _Index:
    index = _Index()
    for path in sorted(paths):
        module = _parse_module(path)
        index.modules.append(module)
        for stmt in module.tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                index.functions.setdefault(stmt.name, []).append((module, stmt))
    return index


def _own_nodes(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterable[ast.AST]:
    """Nodes of ``fn``'s own body, not of functions or lambdas nested in it."""
    stack: list[ast.AST] = list(fn.body)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _locals_of(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, ast.expr | None]:
    """Each local name bound exactly once by a plain assignment, to its value; a name bound
    more than once, or by a loop / ``with`` / walrus / augmented assignment / tuple target,
    maps to ``None`` (ambiguous). Parameters stay unresolved."""
    bindings: dict[str, list[ast.expr | None]] = {}
    for node in _own_nodes(fn):
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.NamedExpr, ast.AugAssign)):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.optional_vars for item in node.items if item.optional_vars is not None]
        for target in targets:
            if isinstance(target, ast.Name) and value is not None and len(targets) == 1:
                bindings.setdefault(target.id, []).append(value)
                continue
            for sub in ast.walk(target):
                if isinstance(sub, ast.Name):
                    bindings.setdefault(sub.id, []).append(None)
    for arg in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs):
        bindings.pop(arg.arg, None)
    return {name: values[0] if len(values) == 1 else None for name, values in bindings.items()}


def _single_return(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.expr | None:
    returns = [n for n in _own_nodes(fn) if isinstance(n, ast.Return)]
    if len(returns) == 1 and returns[0].value is not None:
        return returns[0].value
    return None


def _flatten(node: ast.expr, op: type[ast.operator]) -> list[ast.expr]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, op):
        return _flatten(node.left, op) + _flatten(node.right, op)
    return [node]


@dataclass(frozen=True)
class _Scope:
    module: _Module
    index: _Index
    frames: tuple[dict[str, ast.expr | None], ...] = ()

    def render(self, node: ast.expr, depth: int = 0) -> str | None:
        """``node`` as a path template, unresolved parts as ``{}``; ``None`` when it is not
        a string-shaped expression at all."""
        if depth > _MAX_DEPTH:
            return None
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    inner = self.render(value.value, depth + 1)
                    parts.append(_HOLE if inner is None else inner)
            return "".join(parts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
            sep = "/" if isinstance(node.op, ast.Div) else ""
            rendered = [self.render(operand, depth + 1) for operand in _flatten(node, type(node.op))]
            if all(part is None for part in rendered):
                return None
            return sep.join(_HOLE if part is None else part for part in rendered)
        if isinstance(node, ast.Name):
            return self._resolve_name(node.id, depth)
        if isinstance(node, ast.Call):
            return self._resolve_call(node, depth)
        return None

    def _resolve_name(self, name: str, depth: int) -> str | None:
        for frame in reversed(self.frames):
            if name in frame:
                value = frame[name]
                return None if value is None else self.render(value, depth + 1)
        constant = self.module.constants.get(name)
        if constant is None:
            return None
        return _Scope(self.module, self.index).render(constant, depth + 1)

    def _resolve_call(self, call: ast.Call, depth: int) -> str | None:
        func = call.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name is None:
            return None
        if name in _PATH_PASSTHROUGH and len(call.args) == 1:
            return self.render(call.args[0], depth + 1)
        defs = self.index.functions.get(name, [])
        same_module = [d for d in defs if d[0] is self.module]
        chosen = same_module[0] if len(same_module) == 1 else defs[0] if len(defs) == 1 else None
        if chosen is not None:
            module, fn = chosen
            returned = _single_return(fn)
            if returned is not None:
                return _Scope(module, self.index, (_locals_of(fn),)).render(returned, depth + 1)
        if name in _IMPL_DIR_HELPERS:
            return f"{_HOLE}/implementation-artifacts"
        return None


def _segments_in(text: str) -> list[str]:
    text = _ANGLE_PLACEHOLDER.sub(_HOLE, text)
    found: list[str] = []
    for match in _SEGMENT_AFTER_IMPL.finditer(text):
        segment = match.group(1).rstrip(".")
        if re.search(r"[A-Za-z0-9]", segment.replace(_HOLE, "")):
            found.append(segment)
    return found


def _fragment_ids(tree: ast.Module) -> set[int]:
    """Nodes that are a fragment of a larger string or path expression -- read through
    their parent, never alone (``"implementation-artifacts/epic-"`` inside an f-string
    would otherwise yield the partial segment ``epic-``)."""
    skip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            skip.update(id(value) for value in node.values)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
            for child in (node.left, node.right):
                if isinstance(child, ast.BinOp) and isinstance(child.op, type(node.op)):
                    skip.add(id(child))
                elif isinstance(node.op, ast.Add) and isinstance(child, (ast.Constant, ast.JoinedStr)):
                    skip.add(id(child))
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                skip.add(id(body[0].value))  # a docstring is prose, not a path marshal builds
    return skip


class _Scanner(ast.NodeVisitor):
    def __init__(self, module: _Module, index: _Index) -> None:
        self.module = module
        self.index = index
        self.frames: list[dict[str, ast.expr | None]] = []
        self.skip = _fragment_ids(module.tree)
        self.hits: list[_Hit] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.frames.append(_locals_of(node))
        self.generic_visit(node)
        self.frames.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self._extract(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        self._extract(node)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Div, ast.Add)):
            self._extract(node)
        self.generic_visit(node)

    def _extract(self, node: ast.expr) -> None:
        if id(node) in self.skip:
            return
        text = _Scope(self.module, self.index, tuple(self.frames)).render(node)
        if text is None:
            return
        for segment in _segments_in(text):
            self.hits.append(_Hit(segment, self.module.path, node.lineno))


def _scan(root: Path) -> list[_Hit]:
    """Every ``(segment, path, lineno)`` the ``*.py`` files under ``root`` build directly
    under ``implementation-artifacts``."""
    index = _build_index(root.rglob("*.py"))
    hits: list[_Hit] = []
    for module in index.modules:
        scanner = _Scanner(module, index)
        scanner.visit(module.tree)
        hits.extend(scanner.hits)
    return sorted(set(hits), key=lambda h: (h.segment, str(h.path), h.lineno))


def _instantiate(segment: str, row: _ShapeRow) -> str:
    """The collected template as a concrete path (holes filled), under the same
    directory tail as the row's sample when the segment is a directory."""
    name = segment.replace(_HOLE, "97")
    parts = row.sample_rel.removeprefix("implementation-artifacts/").split("/", 1)
    return f"implementation-artifacts/{name}" + (f"/{parts[1]}" if len(parts) == 2 else "")


def _assert_scan_covered(hits: list[_Hit], classify: Callable[[str], str]) -> None:
    """Every collected segment has a table row, and both that row's sample and the
    collected template itself classify to the row's declared class. A failure names each
    ``path:lineno`` that builds the segment."""
    problems: list[str] = []
    by_segment: dict[str, list[_Hit]] = {}
    for hit in hits:
        by_segment.setdefault(hit.segment, []).append(hit)
    for segment, seg_hits in sorted(by_segment.items()):
        where = ", ".join(h.where for h in seg_hits)
        row = _ROWS_BY_SEGMENT.get(segment)
        if row is None:
            problems.append(f"{where}: builds implementation-artifacts/{segment} -- no _SHAPE_TABLE row")
            continue
        for sample in (row.sample_rel, _instantiate(segment, row)):
            got = classify(sample)
            if got != row.expected_class:
                problems.append(
                    f"{where}: builds implementation-artifacts/{segment}; {sample} classifies {got!r}, "
                    f"expected {row.expected_class!r} -- add or fix its TIER3_RUN_ARTIFACTS row"
                )
    assert not problems, "\n".join(problems)


def _factory_classify(repo: Path) -> Callable[[str], str]:
    impl = factory._impl(repo)

    def classify(sample_rel: str) -> str:
        path = impl / sample_rel.removeprefix("implementation-artifacts/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return factory.classify(path, repo)

    return classify


# --- the tests --------------------------------------------------------------------------


def test_every_table_sample_classifies_to_its_declared_class(tmp_path: Path) -> None:
    classify = _factory_classify(tmp_path / "repo")
    tier3_classes = {rule.classification for rule in factory.TIER3_RUN_ARTIFACTS}
    for row in _SHAPE_TABLE:
        got = classify(row.sample_rel)
        assert got == row.expected_class, (row.sample_rel, got, row.expected_class)
        if row.expected_class.startswith("local:"):
            assert got in tier3_classes, (row.sample_rel, got)


def test_writer_tokens_still_present_in_cited_sources() -> None:
    for row in _SHAPE_TABLE:
        assert row.writer_path.is_file(), row.writer_path
        text = row.writer_path.read_text(encoding="utf-8")
        assert row.writer_token in text, (row.sample_rel, row.writer_path, row.writer_token)


def test_every_tier3_rule_names_a_real_writer() -> None:
    """Each ``TIER3_RUN_ARTIFACTS`` writer is a repo-relative ``file::symbol`` whose file
    exists and defines that top-level symbol, or a bare file path (a skill file)."""
    for rule in factory.TIER3_RUN_ARTIFACTS:
        file_part, _, symbol = rule.writer.partition("::")
        path = REPO_ROOT / file_part
        assert path.is_file(), (rule.pattern.pattern, rule.writer)
        if not symbol:
            assert path.suffix == ".md", (rule.pattern.pattern, rule.writer)
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {
            node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        assert symbol in defined, (rule.pattern.pattern, rule.writer)


def test_marshal_ast_scan_covers_expected_segments(tmp_path: Path) -> None:
    hits = _scan(MARSHAL_SRC)
    _assert_scan_covered(hits, _factory_classify(tmp_path / "repo"))
    collected = {hit.segment for hit in hits}
    missing = sorted(_EXPECTED_MARSHAL_SEGMENTS - collected)
    assert _EXPECTED_MARSHAL_SEGMENTS <= collected, f"scan no longer sees: {missing}"


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('run_dir = root / "implementation-artifacts" / "new-kind"\n', id="div-literal"),
        pytest.param(
            'run_dir = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "new-kind"\n',
            id="div-after-variable",
        ),
        pytest.param(
            'run_dir = root / "implementation-artifacts" / _NEW_KIND_DIRNAME\n_NEW_KIND_DIRNAME = "new-kind"\n',
            id="module-constant",
        ),
        pytest.param(
            'path = f"{implementation_artifacts_relpath(slug)}/new-kind-{stamp}.md"\n',
            id="fstring-tail",
        ),
        pytest.param('NOTE = "move it to implementation-artifacts/new-kind/ first"\n', id="literal"),
    ],
)
def test_fixture_new_kind_fails_naming_file_and_line(tmp_path: Path, source: str) -> None:
    fake_src = tmp_path / "marshal"
    fake_src.mkdir()
    (fake_src / "fake_marshal_module.py").write_text(source, encoding="utf-8")
    hits = _scan(fake_src)
    assert [h.segment.startswith("new-kind") for h in hits] == [True]
    with pytest.raises(AssertionError, match=r"fake_marshal_module\.py:1: builds implementation-artifacts/new-kind"):
        _assert_scan_covered(hits, _factory_classify(tmp_path / "repo"))


def test_known_segment_still_passes_the_fixture_scan(tmp_path: Path) -> None:
    fake_src = tmp_path / "marshal"
    fake_src.mkdir()
    (fake_src / "fake_marshal_module.py").write_text(
        'run_dir = root / "implementation-artifacts" / "dispatch-runs" / run_id\n', encoding="utf-8"
    )
    hits = _scan(fake_src)
    assert [h.segment for h in hits] == ["dispatch-runs"]
    _assert_scan_covered(hits, _factory_classify(tmp_path / "repo"))


def test_meta_test_never_imports_marshal() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not [name for name in imported if name.startswith("pyforge.marshal")], imported
