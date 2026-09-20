"""AD-13 — no configuration file in v1: no module under `pyforge/mason/` may
import a config-file parser. Configuration is flags and environment
variables only (`_resolve_str`/`_resolve_bool`/`_resolve_optional_float` in
`cli.py`); a config-file parser import anywhere in the package would be the
first thread of a second configuration system this invariant exists to rule
out before it starts.

Banned modules: `configparser` (stdlib INI), `tomllib` (stdlib TOML,
3.11+), `tomli`/`toml`/`tomlkit` (TOML backport and the two most common
third-party TOML libraries), `yaml`/`pyyaml`'s import name, `ruamel.yaml`,
`configobj` (INI), and `dotenv` (`python-dotenv`'s import name). The two
YAML libraries are named because CFE itself depends on them (see
`cfe.CFE_IMPORT_FLOOR`), which makes them the most plausible accidental
import if a future story reached for "the YAML library that's already on
the floor" to read a settings file; the TOML and `.env` entries are named
because they are what a developer adding "just a small config file" reaches
for first (review pass, 2026-08-10 -- the original list banned `tomli` but
not `toml`, and a `.env` loader not at all).

What this guard does NOT catch, stated so a future story does not mistake
its silence for proof: a *dynamic* import (`importlib.import_module("yaml")`,
`__import__`), which is invisible to a static AST scan; a hand-rolled
parser that reads a settings file with nothing but `open()` and `str.split`;
and `json`, which cannot be banned because `render.py` already imports it
for `--format json` output, so a `~/.mason.json` reader would sail straight
through this scan (review pass, 2026-08-10 -- `json` is the most plausible
of the three holes precisely because the import is already legitimate and
unremarkable).
AD-13's invariant is broader than this test ("no code path reads a
Mason-specific key from a file"); the test enforces the statically decidable
part of it, which is the part a static guard can honestly enforce.

AD-13's own text carves out one sanctioned exception this guard does not yet
need to encode: "Mason reads no key from `pyproject.toml` other than the
packaging metadata it is asked to build." No code path reads a *target*
package's `pyproject.toml` today (Story 1.10's Never boundary: nothing
delegates to a build yet), so `tomllib`/`tomli` stay unconditionally banned
here; a future story that legitimately needs that carve-out will have to
extend this guard deliberately, not rediscover the gap as a test failure.

Story 4.4 is that future story, for `yaml` rather than `tomllib`:
`engines/condalock.py::check()` needs `yaml.safe_load` to read
`metadata.content_hash` out of a lockfile CONDA-LOCK itself produced -- not
a Mason-owned settings/config file (spec Design Notes for
`environment check`), the identical "reading a *target*/third-party
artifact's own structured output is not a second Mason configuration
system" distinction the `pyproject.toml` paragraph above already draws for
TOML. `_SANCTIONED_YAML_EXCEPTIONS` below encodes this deliberately and
narrowly: only a bare `yaml` import in exactly `engines/condalock.py` is
exempted from the real-package assertion below -- the detector itself
(`_find_config_file_parser_imports`) stays unmodified and un-aware of any
exception, so every regression fixture below still proves it flags a plain
`import yaml`/`from yaml import ...` unconditionally; every OTHER banned
module, and every OTHER file (including every other line in
`condalock.py` itself, were it to import e.g. `tomllib`), stays fully
covered by this guard.

Relative imports (`from .yaml import X`, `level > 0`) are never flagged even
when the trailing segment matches a banned name -- that names a local
sibling module (e.g. a hypothetical `mason/yaml.py`), not the third-party
package, and it would be a real false positive to treat the two the same.

AST-based, not string/regex matching, mirroring
`test_dependency_direction.py`'s AD-2 guard exactly (Story 1.1's retro
finding: a naive text scan fails on a comment that merely *mentions* the
banned name) — including its unreadable/non-UTF-8/invalid-syntax
error-handling rigor: a file this guard cannot read or parse is a file it
cannot prove clean, so it fails the test loudly rather than skipping.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"

_BANNED_MODULES = (
    "configparser",
    "tomllib",
    "tomli",
    "toml",
    "tomlkit",
    "yaml",
    "ruamel.yaml",
    "configobj",
    "dotenv",
)

_SANCTIONED_YAML_EXCEPTIONS = {
    (PKG_ROOT / "engines" / "condalock.py", "yaml"),
}
"""Story 4.4's narrow, deliberate carve-out (module docstring) -- applied
only in `test_no_module_imports_a_config_file_parser` below, never inside
`_find_config_file_parser_imports` itself, so the detector stays exception-
free and every regression fixture below keeps proving it fires
unconditionally on a plain `yaml` import."""


def _matches_banned(dotted_name: str) -> str | None:
    """Return the banned-module name `dotted_name` matches (exact, or a
    submodule of it, e.g. `ruamel.yaml.main` matching `ruamel.yaml`), or
    `None` if it matches none of `_BANNED_MODULES`."""
    for banned in _BANNED_MODULES:
        if dotted_name == banned or dotted_name.startswith(f"{banned}."):
            return banned
    return None


def _find_config_file_parser_imports(root: Path) -> list[tuple[Path, str]]:
    """Return `(path, banned_module)` for every `.py` file under `root` that
    imports one of `_BANNED_MODULES`, via either `import x` or
    `from x import y`."""
    violators: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.py")):
        try:
            # utf-8-sig, not utf-8: CPython itself strips a UTF-8 BOM from
            # source files, but `ast.parse` on a string that still carries
            # the BOM character raises SyntaxError -- so a perfectly valid,
            # importable module would fail this guard as "invalid Python
            # syntax" (review pass, 2026-08-10). `utf-8-sig` decodes files
            # with and without a BOM identically to `utf-8` otherwise.
            source = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            # A file the scanner cannot even read (broken symlink,
            # permissions) is a file it cannot prove clean — fail loudly
            # rather than silently skip, mirroring
            # test_dependency_direction.py's own rationale verbatim.
            raise AssertionError(
                f"{path}: unreadable ({exc}); the AD-13 config-file-parser guard cannot AST-scan this file"
            ) from exc
        except UnicodeDecodeError as exc:
            raise AssertionError(
                f"{path}: not valid UTF-8; the AD-13 config-file-parser guard cannot AST-scan this file"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise AssertionError(
                f"{path}: invalid Python syntax; the AD-13 config-file-parser guard cannot AST-scan this file"
            ) from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    banned = _matches_banned(alias.name)
                    if banned is not None:
                        violators.append((path, banned))
            elif isinstance(node, ast.ImportFrom):
                # node.level > 0 is a relative import (`from .yaml import
                # X`) -- it names a local sibling module, never the
                # third-party/stdlib package `_BANNED_MODULES` bans, even
                # when the trailing segment happens to match.
                if node.module is not None and node.level == 0:
                    banned = _matches_banned(node.module)
                    if banned is None:
                        # `from ruamel import yaml` names the banned dotted
                        # module across the import's two halves, so matching
                        # `node.module` alone ("ruamel") misses it entirely
                        # -- the single most natural way to import
                        # ruamel.yaml, waved straight through until the
                        # 2026-08-10 review pass. Recheck each bound name
                        # joined onto the module path.
                        for alias in node.names:
                            banned = _matches_banned(f"{node.module}.{alias.name}")
                            if banned is not None:
                                break
                    if banned is not None:
                        violators.append((path, banned))
    return violators


def test_no_module_imports_a_config_file_parser():
    # Guard the guard: if the package layout ever moves, rglob over a stale
    # path would yield zero files and this test would pass vacuously forever.
    assert PKG_ROOT.is_dir(), f"AD-13 guard is scanning nothing — package root moved? {PKG_ROOT}"
    violators = _find_config_file_parser_imports(PKG_ROOT)
    # Story 4.4's one deliberate, narrow carve-out (module docstring,
    # `_SANCTIONED_YAML_EXCEPTIONS`) -- filtered here, not inside the
    # detector, so the detector itself stays exception-free.
    unsanctioned = [v for v in violators if v not in _SANCTIONED_YAML_EXCEPTIONS]
    assert not unsanctioned, (
        # Derived from _BANNED_MODULES, never re-typed (review pass,
        # 2026-08-10, third): the hand-written list here named 5 of the 9
        # banned modules, so a developer who tripped the guard with `import
        # dotenv` read a message that did not mention dotenv and could
        # reasonably conclude the guard had misfired.
        "AD-13: no module under pyforge/mason/ may import a config-file "
        f"parser ({'/'.join(_BANNED_MODULES)}); found: {unsanctioned}"
    )


def test_every_sanctioned_yaml_exception_is_live_and_import_form_scoped():
    """Guard the carve-out itself (review pass, 2026-08-15 second).

    `_SANCTIONED_YAML_EXCEPTIONS` keys on `(path, banned_module)`, which is
    all `_find_config_file_parser_imports` reports -- so on its own it
    exempts every possible yaml import in that file, including `from yaml
    import unsafe_load`, the exact thing AD-13's safe-load-only invariant
    exists to keep out. It also cannot notice its own rot: were
    `condalock.py` to stop importing yaml, the stale entry would sit there
    silently re-authorizing reintroduction.

    Both halves are closed here rather than by teaching the detector about
    exceptions (which would cost it the exception-free property the
    regression fixtures below depend on): every sanctioned file must still
    actually trip the detector, and must import the banned module ONLY in
    the bare `import <module>` form -- never `from <module> import ...`,
    which is what would bind `unsafe_load`.
    """
    violators = set(_find_config_file_parser_imports(PKG_ROOT))
    for path, banned in sorted(_SANCTIONED_YAML_EXCEPTIONS):
        assert (path, banned) in violators, (
            f"AD-13: the sanctioned carve-out for ({path.name}, {banned}) is "
            "stale -- that file no longer imports it. Drop the entry rather "
            "than leaving it to re-authorize a future reintroduction."
        )
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                assert _matches_banned(node.module or "") != banned, (
                    f"AD-13: {path.name} imports {banned} via `from {banned} "
                    "import ...`; the carve-out sanctions only a bare `import "
                    f"{banned}` (whose sole sanctioned use is `yaml.safe_load`). "
                    "A from-import can bind `unsafe_load`, which the carve-out "
                    "does not cover."
                )


# --- Regression fixtures proving the detection logic itself (mirrors
# test_dependency_direction.py's rigor): synthetic trees, not the real
# package, so these assert the scanner's behavior independent of what
# src/pyforge/mason/ currently contains. --------------------------------------


@pytest.mark.parametrize(
    "import_stmt,expected_banned",
    [
        ("import configparser\n", "configparser"),
        ("from configparser import ConfigParser\n", "configparser"),
        ("import tomllib\n", "tomllib"),
        ("from tomllib import load\n", "tomllib"),
        ("import tomli\n", "tomli"),
        ("from tomli import load\n", "tomli"),
        ("import yaml\n", "yaml"),
        ("from yaml import safe_load\n", "yaml"),
        ("import ruamel.yaml\n", "ruamel.yaml"),
        ("from ruamel.yaml import YAML\n", "ruamel.yaml"),
        # Review pass (2026-08-10): the banned dotted name split across the
        # import's two halves -- `node.module` alone is only "ruamel".
        ("from ruamel import yaml\n", "ruamel.yaml"),
        # Review pass (2026-08-10): ban-list gaps -- what a developer adding
        # "just a small config file" actually reaches for.
        ("import toml\n", "toml"),
        ("from toml import load\n", "toml"),
        ("import tomlkit\n", "tomlkit"),
        ("import configobj\n", "configobj"),
        ("from configobj import ConfigObj\n", "configobj"),
        ("import dotenv\n", "dotenv"),
        ("from dotenv import load_dotenv\n", "dotenv"),
    ],
)
def test_detector_fires_on_every_banned_config_file_parser_import(
    tmp_path,
    import_stmt,
    expected_banned,
):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(import_stmt, encoding="utf-8")

    violators = _find_config_file_parser_imports(root)

    assert (root / "sneaky.py", expected_banned) in violators


def test_detector_permits_a_relative_import_of_a_local_module_with_the_same_name(tmp_path):
    """Edge-case-hunter finding (review pass, 2026-08-10): `from .yaml
    import X` names a local sibling module, never the third-party `yaml`
    package `_BANNED_MODULES` bans -- must not false-positive."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "yaml.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "user.py").write_text("from .yaml import VALUE\n", encoding="utf-8")

    violators = _find_config_file_parser_imports(root)

    assert violators == []


def test_detector_permits_an_innocent_from_import_of_a_non_banned_name(tmp_path):
    """The `from X import Y` recheck added for `from ruamel import yaml`
    joins the two halves -- it must not turn an ordinary import whose bound
    name merely resembles nothing banned into a false positive (review pass,
    2026-08-10)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "from json import loads\nfrom os import environ\n",
        encoding="utf-8",
    )

    violators = _find_config_file_parser_imports(root)

    assert violators == []


def test_detector_reads_a_file_carrying_a_utf8_bom(tmp_path):
    """A BOM-prefixed source file is valid, importable Python (CPython
    strips the BOM), but `ast.parse` chokes on the BOM character -- reading
    as plain `utf-8` made this guard fail such a file as "invalid Python
    syntax" (review pass, 2026-08-10)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "bom.py").write_bytes(b"\xef\xbb\xbfimport json\n")

    assert _find_config_file_parser_imports(root) == []

    # ...and a BOM must not hide a real violation either.
    (root / "bom_sneaky.py").write_bytes(b"\xef\xbb\xbfimport yaml\n")

    assert (root / "bom_sneaky.py", "yaml") in _find_config_file_parser_imports(root)


def test_detector_permits_a_module_with_no_banned_import(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        '"""Docstring only."""\n\nimport json\nimport os\nfrom pathlib import Path\n',
        encoding="utf-8",
    )

    violators = _find_config_file_parser_imports(root)

    assert violators == []


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _find_config_file_parser_imports(root)


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _find_config_file_parser_imports(root)


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _find_config_file_parser_imports(root)
