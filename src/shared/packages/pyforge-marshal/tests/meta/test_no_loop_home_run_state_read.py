"""Story 33.12 CAP-4 -- forbid untagged loop-home run-state reads outside the publisher.

Story 115.1 (CAP-227, amended 2026-11-10): the guard can fire. It used to add the lines of every
string constant to its exempt set, so any code line holding a string literal was skipped -- and the
forbidden patterns only ever occur inside string literals, so the guard named nothing. It now exempts
docstrings, comments and help text only, and judges a string literal on a code line. The fixture
tests below are its proof: an untagged loop-home read in a temp module is one offender; the same text
tagged, in a docstring or in ``help=`` is none.

This is the package half: it reads only this package's own sources and ``tmp_path``. Doctor's
marshal source is judged by ``test_no_loop_home_run_state_read_doctor_live_tree.py``.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
MARSHAL_SRC = Path(_PACKAGE_FILE).resolve().parent
PUBLISHER_ADAPTER = MARSHAL_SRC / "adapters" / "publisher_host.py"
CAP4_TAG = "CAP-4: loop-home FILE read"
_FORBIDDEN = (
    re.compile(r"\.bmad-loops"),
    re.compile(r"\.bmad-loop/runs"),
    re.compile(r"state\.json"),
    re.compile(r"journal\.jsonl"),
)

_UNTAGGED_READ = 'home = Path.home() / ".bmad-loops" / slug'


def _docstring_lines(source: str) -> set[int]:
    """The lines of real docstrings and of bare string-expression statements.

    A docstring is the first statement of a module, class or function when it is a string
    expression; a bare string-expression statement anywhere else is the same inert text. Both are an
    ``ast.Expr`` over a ``str`` constant, and nothing else is: a string constant in an assignment, a
    call argument, a comparison or a return is code, and the guard judges it.
    """
    tree = ast.parse(source)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def _comment_columns(source: str) -> dict[int, int]:
    """Line number -> the column its comment starts at: a trailing comment is a comment too."""
    columns: dict[int, int] = {}
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            columns[token.start[0]] = token.start[1]
    return columns


def _tagged_lines(lines: list[str]) -> set[int]:
    tagged: set[int] = set()
    for index, line in enumerate(lines):
        if CAP4_TAG in line:
            tagged.add(index + 1)
            if index + 1 < len(lines):
                tagged.add(index + 2)
    return tagged


def _scan_file(path: Path) -> list[str]:
    if path.resolve() == PUBLISHER_ADAPTER.resolve():
        return []
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    doc_lines = _docstring_lines(source)
    comments = _comment_columns(source)
    tagged = _tagged_lines(lines)
    offenders: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        code = line[: comments[line_no]] if line_no in comments else line
        if not code.strip():
            continue
        if line_no in doc_lines:
            continue
        if line_no in tagged:
            continue
        if "help=" in code or "Help(" in code:
            continue
        for pattern in _FORBIDDEN:
            if pattern.search(code):
                offenders.append(f"{path}:{line_no}: {stripped}")
                break
    return offenders


def _marshal_sources() -> list[Path]:
    return sorted(MARSHAL_SRC.rglob("*.py"))


def _fixture_module(tmp_path: Path, body: str) -> Path:
    module = tmp_path / "fixture_module.py"
    module.write_text(body, encoding="utf-8")
    return module


def test_no_untagged_loop_home_run_state_reads_in_marshal_src() -> None:
    offenders: list[str] = []
    for path in _marshal_sources():
        offenders.extend(_scan_file(path))
    assert offenders == []


def test_forbidden_patterns_match_run_state_glob_line() -> None:
    line = 'for state in sorted(home.glob(".bmad-loop/runs/*/state.json")):'
    assert any(pattern.search(line) for pattern in _FORBIDDEN)


def test_the_guard_fires_on_an_untagged_loop_home_read(tmp_path: Path) -> None:
    module = _fixture_module(
        tmp_path,
        "from pathlib import Path\n\n\ndef home_for(slug: str) -> Path:\n    " + _UNTAGGED_READ + "\n    return home\n",
    )

    offenders = _scan_file(module)

    assert offenders == [f"{module}:5: {_UNTAGGED_READ}"]


def test_the_guard_fires_on_a_run_state_file_name_on_a_code_line(tmp_path: Path) -> None:
    """A string constant on a code line is judged: the old rule exempted every one of them."""
    module = _fixture_module(tmp_path, '"""A module docstring."""\n\nSTATE = "state.json"\n')

    assert _scan_file(module) == [f'{module}:3: STATE = "state.json"']


def test_the_same_read_tagged_is_not_an_offender(tmp_path: Path) -> None:
    module = _fixture_module(
        tmp_path,
        "from pathlib import Path\n\n\ndef home_for(slug: str) -> Path:\n"
        f"    # {CAP4_TAG} -- a fixture's reason\n"
        f"    {_UNTAGGED_READ}\n"
        "    return home\n",
    )

    assert _scan_file(module) == []


def test_the_same_read_in_a_docstring_is_not_an_offender(tmp_path: Path) -> None:
    module = _fixture_module(
        tmp_path,
        f'"""Module docstring: {_UNTAGGED_READ}."""\n\n\n'
        "class Home:\n"
        f'    """Class docstring:\n    {_UNTAGGED_READ}\n    """\n\n'
        "    def path(self) -> None:\n"
        f'        """Function docstring: {_UNTAGGED_READ}."""\n'
        f"        'A bare string-expression statement: {_UNTAGGED_READ}'\n",
    )

    assert _scan_file(module) == []


def test_the_same_read_in_help_text_is_not_an_offender(tmp_path: Path) -> None:
    module = _fixture_module(
        tmp_path,
        "import argparse\n\n"
        "parser = argparse.ArgumentParser()\n"
        f"parser.add_argument('--home', help='{_UNTAGGED_READ}')\n",
    )

    assert _scan_file(module) == []


def test_a_comment_naming_the_read_is_not_an_offender(tmp_path: Path) -> None:
    module = _fixture_module(tmp_path, f"# {_UNTAGGED_READ}\nX = 1  # {_UNTAGGED_READ}\n")

    assert _scan_file(module) == []
