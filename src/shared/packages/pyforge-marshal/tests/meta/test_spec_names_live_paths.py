"""Meta test -- Story 114.2 (a fix under spec-pyforge-marshal:CAP-229 and
spec-one-chain-per-station:CAP-6): no marshal capability names a file, script
or check that is gone.

At 82a2b18828 fourteen capabilities still named the Guildhall console's
``data.js`` and ``generate.py`` (deleted 2026-08-25, steward Story 30.2) or
``scripts/forward_dependency_check.py`` and ``scripts/dashboard_drift_check.py``
(deleted 2026-08-10, ported to ``pyforge.doctor.sources``), and nothing read
the Spec's names against the tree. This guard does.

The rule. In every capability block of the Spec (its ``- **CAP-n — ...**``
heading and the indented lines under it) whose heading is not marked
``(retired <date>...)``, every name below must resolve in ``git ls-files``:

* a backticked repo path, its first segment a tracked top-level directory;
* a backticked file name with a known extension, optionally carrying a
  ``:line``, ``:line-line`` or ``::test`` suffix;
* a backticked symbol ``<path>.<name>``, judged by its path;
* every ``<x>_check`` name, backticked or bare, judged as ``<x>_check.py``.

A name resolves when it is a tracked file or directory, the basename of one,
a path suffix of one, or a glob matching one. A templated token (one carrying
``<``, ``{``, ``$``, ``~`` or a space) is a shape, not a name, and passes.

A name that is right by design -- a loop home's runtime file, bmad-loop's own
module, an upstream file, a fixture name, a name kept as history, a file a
later story writes -- sits on ``ALLOW`` with its reason; story spec 114.2
copies the table. An entry whose capability no longer carries its token is
stale and fails ``test_every_allow_entry_is_still_carried``.

The Spec sits outside this package, so the module is marked ``live_tree`` and
fails, never skips, when the Spec or git is absent. The checkout root is
found at call time, never at import.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

_MARSHAL_PACKAGE_RELPATH = Path("src/shared/packages/pyforge-marshal")
_SPEC_RELPATH = Path("_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md")

_CAP_HEADING = re.compile(r"^- \*\*(CAP-\d+) — ")
_RETIRED = re.compile(r"\(retired \d{4}-\d{2}-\d{2}")
_TICKED = re.compile(r"`([^`\n]+)`")
_CHECK_NAME = re.compile(r"(?<![\w./-])([a-z][a-z0-9_]*_check)(?![\w-])")
_LOCATION_SUFFIX = re.compile(r"(?:::[\w\[\]-]+|:\d+(?:-\d+)?)$")
_TEMPLATED = frozenset("<{$~ ")
_GLOB = frozenset("*?[")
_KNOWN_EXTENSIONS = frozenset(
    {
        "cfg",
        "css",
        "csv",
        "html",
        "ini",
        "j2",
        "js",
        "json",
        "jsonl",
        "lock",
        "md",
        "mdc",
        "patch",
        "py",
        "sh",
        "sql",
        "toml",
        "ts",
        "txt",
        "yaml",
        "yml",
    }
)

# (capability, token, reason): names that are right by design.
ALLOW: tuple[tuple[str, str, str], ...] = (
    ("CAP-19", "policy.toml", "a loop home's rendered bmad-loop policy, a runtime file never tracked"),
    ("CAP-20", "policy.toml", "a loop home's rendered bmad-loop policy, a runtime file never tracked"),
    ("CAP-39", "project-context.md", "the eight per-station rulebooks this capability refreshed, since retired"),
    ("CAP-40", "removals.txt", "bmad-method's own removals list, an upstream file"),
    ("CAP-41", "project-context.md", "the per-station rulebooks this capability retired"),
    ("CAP-42", "llms-full.txt", "bmad-method's discontinued upstream documentation file"),
    ("CAP-42", "llms.txt", "bmad-method's discontinued upstream documentation file"),
    ("CAP-45", "policy.toml", "the eight loop homes' rendered bmad-loop policy, runtime files"),
    ("CAP-50", "failed/*/changes.patch", "a bmad-loop run output under .bmad-loop/runs/"),
    ("CAP-52", "engine.py:1707", "bmad-loop's own module, cited in the upstream issue"),
    ("CAP-52", "runs.py:872-908", "bmad-loop's own module, cited in the upstream issue"),
    ("CAP-59", ".bmad-loop/policy.toml", "a loop home's rendered bmad-loop policy, gitignored"),
    ("CAP-69", "src/pyforge_genesis", "the pre-split installer tree, named as what was removed"),
    ("CAP-72", "project-context.md", "the per-station rulebooks this capability regenerated, since retired"),
    ("CAP-74", "product-brief-pyforge-marshal.md", "the loose name of the brief this capability moved, history"),
    ("CAP-105", "orphans.json", "a consolidation run's output under its run folder"),
    ("CAP-105", "orphans.md", "a consolidation run's output under its run folder"),
    ("CAP-132", ".bmad-loop/policy.toml", "a loop home's rendered bmad-loop policy, gitignored"),
    ("CAP-134", ".bmad-loop/policy.toml", "a loop home's rendered bmad-loop policy, gitignored"),
    ("CAP-134", "policy.toml", "a loop home's rendered bmad-loop policy, a runtime file never tracked"),
    ("CAP-164", "changes.patch", "a bmad-loop run output, named as the analog dispatch keeps"),
    ("CAP-165", "policy.toml", "a loop home's rendered bmad-loop policy, a runtime file never tracked"),
    ("CAP-171", ".bmad-loop/runs/", "bmad-loop's runtime run directory, gitignored"),
    ("CAP-172", ".bmad-loop/runs/", "bmad-loop's runtime run directory, gitignored"),
    ("CAP-227", ".bmad-loop/runs", "bmad-loop's runtime run directory, the literal the guard matches"),
    ("CAP-263", ".pixi/envs/local-recipes", "named as what the watch must never reach"),
    ("CAP-273", "_bmad/custom/.active-project", "the shared active-project marker, untracked by design"),
    ("CAP-279", ".bmad-loop/policy.toml", "a loop home's rendered bmad-loop policy, gitignored"),
    ("CAP-279", "_bmad/custom/.active-project", "the shared active-project marker, untracked by design"),
    ("CAP-279", "docs/dreams/demo.md", "a fixture name in the seed check's test project"),
    ("CAP-279", "run_check", "a function in seed/verbs/check.py, not a script"),
    ("CAP-298", "installed_plugins.json", "Claude Code's own plugin registry, outside the repository"),
    ("CAP-298", "plugin.json", "the cached EGM plugin's manifest, outside the repository"),
    ("CAP-298", "report.json", "a challenge run's output under implementation-artifacts/egm/<run>/"),
    ("CAP-305", "tests/_support/tree_read_guard.py", "written by Story 116.4, open while CAP-305 reads ready"),
    ("CAP-305", "tests/meta/test_tree_read_guard.py", "written by Story 116.4, open while CAP-305 reads ready"),
)


@dataclass(frozen=True)
class _Tree:
    """The tracked tree as the guard judges it."""

    paths: frozenset[str]
    tops: frozenset[str]
    basenames: frozenset[str]
    suffixes: frozenset[str]


def _checkout_root() -> Path:
    """The source checkout this test file sits in: the nearest ancestor carrying the package."""
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / _MARSHAL_PACKAGE_RELPATH).is_dir():
            return ancestor
    pytest.fail(f"{__file__} is not inside a source checkout of {_MARSHAL_PACKAGE_RELPATH}")


def _tracked_tree(root: Path) -> _Tree:
    try:
        listing = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.fail(f"git ls-files could not list {root}: {exc}")
    files = [entry for entry in listing.split("\0") if entry]
    if not files:
        pytest.fail(f"git ls-files listed nothing under {root}")
    paths: set[str] = set()
    for name in files:
        parts = name.split("/")
        for depth in range(1, len(parts) + 1):
            paths.add("/".join(parts[:depth]))
    suffixes: set[str] = set()
    for path in paths:
        parts = path.split("/")
        for start in range(len(parts)):
            suffixes.add("/".join(parts[start:]))
    tops = {name.split("/", 1)[0] for name in files if "/" in name}
    return _Tree(
        paths=frozenset(paths),
        tops=frozenset(tops),
        basenames=frozenset(path.rsplit("/", 1)[-1] for path in paths),
        suffixes=frozenset(suffixes),
    )


def _live_capability_blocks(spec_text: str) -> list[tuple[str, str]]:
    """(capability, block text) for each capability whose heading is not retired."""
    blocks: list[tuple[str, str]] = []
    lines = spec_text.splitlines()
    index = 0
    while index < len(lines):
        match = _CAP_HEADING.match(lines[index])
        if match is None:
            index += 1
            continue
        heading = lines[index]
        body = [heading]
        index += 1
        while index < len(lines) and lines[index].startswith("  "):
            body.append(lines[index])
            index += 1
        if _RETIRED.search(heading) is None:
            blocks.append((match.group(1), "\n".join(body)))
    return blocks


def _is_file_name(name: str) -> bool:
    stem, dot, extension = name.rpartition(".")
    return bool(dot) and extension in _KNOWN_EXTENSIONS and bool(stem.rsplit("/", 1)[-1])


def _named_path(token: str, tree: _Tree) -> str | None:
    """The path a backticked token names, or None when it names no path."""
    if any(char in _TEMPLATED for char in token):
        return None
    name = _LOCATION_SUFFIX.sub("", token)
    if "/" in name and name.split("/", 1)[0] in tree.tops:
        return name
    if _is_file_name(name):
        return name
    head, dot, attribute = name.rpartition(".")
    if dot and attribute.isidentifier() and _is_file_name(head):
        return head
    if re.fullmatch(r"[a-z][a-z0-9_]*_check", name):
        return name
    return None


def _resolves(name: str, tree: _Tree) -> bool:
    candidates = [name.rstrip("/")]
    if re.fullmatch(r"[a-z][a-z0-9_]*_check", name):
        candidates.append(f"{name}.py")
    for candidate in candidates:
        if candidate in tree.paths or candidate in tree.suffixes:
            return True
        if "/" not in candidate and candidate in tree.basenames:
            return True
        if any(char in _GLOB for char in candidate):
            for path in tree.paths:
                if fnmatch.fnmatchcase(path, candidate) or fnmatch.fnmatchcase(path, f"*/{candidate}"):
                    return True
    return False


def _carried_names(block: str, tree: _Tree) -> list[str]:
    """Every name a capability block carries, in order, once each."""
    names: dict[str, None] = {}
    for token in _TICKED.findall(block):
        if _named_path(token, tree) is not None:
            names.setdefault(token, None)
    for check_name in _CHECK_NAME.findall(_TICKED.sub(" ", block)):
        names.setdefault(check_name, None)
    return list(names)


def _unresolved(spec_text: str, tree: _Tree) -> list[tuple[str, str]]:
    """(capability, token) for every carried name that resolves nowhere."""
    found: list[tuple[str, str]] = []
    for capability, block in _live_capability_blocks(spec_text):
        for token in _carried_names(block, tree):
            name = _named_path(token, tree) or token
            if not _resolves(name, tree):
                found.append((capability, token))
    return found


@pytest.fixture(scope="module")
def tree() -> _Tree:
    return _tracked_tree(_checkout_root())


@pytest.fixture(scope="module")
def spec_text() -> str:
    spec = _checkout_root() / _SPEC_RELPATH
    if not spec.is_file():
        pytest.fail(f"the live tree has no {_SPEC_RELPATH}")
    return spec.read_text(encoding="utf-8")


def test_every_name_a_live_capability_carries_resolves_or_is_allowed(spec_text: str, tree: _Tree) -> None:
    allowed = {(capability, token) for capability, token, _reason in ALLOW}
    offenders = [pair for pair in _unresolved(spec_text, tree) if pair not in allowed]
    assert offenders == [], (
        "capabilities name a file, script or check the tree does not hold (amend the text through the "
        "memlog, or add an ALLOW entry with its reason when the name is right by design): "
        + "; ".join(f"{capability} names `{token}`" for capability, token in offenders)
    )


def test_every_allow_entry_is_still_carried(spec_text: str, tree: _Tree) -> None:
    carried = {
        (capability, token)
        for capability, block in _live_capability_blocks(spec_text)
        for token in _carried_names(block, tree)
    }
    stale = [(capability, token) for capability, token, _reason in ALLOW if (capability, token) not in carried]
    assert stale == [], f"ALLOW entries whose capability no longer carries the token: {stale}"
    assert all(reason.strip() for _capability, _token, reason in ALLOW)
    assert len({(capability, token) for capability, token, _reason in ALLOW}) == len(ALLOW)


def test_a_capability_naming_a_missing_script_fails_the_guard(tree: _Tree) -> None:
    fixture = (
        "## Capabilities\n\n"
        "- **CAP-1 — a detector that is gone** ← fixture (shipped 2026-01-01)\n"
        "  - **intent:** `scripts/no_such_check.py` judges the tree.\n"
        "  - **success:** `scripts/detectors.py` registers it.\n"
    )

    assert _unresolved(fixture, tree) == [("CAP-1", "scripts/no_such_check.py")]


def test_a_bare_check_name_that_is_gone_fails_the_guard(tree: _Tree) -> None:
    fixture = "- **CAP-2 — bare names** ← fixture (shipped 2026-01-01)\n  - **success:** no_such_check and spec_surface_check run.\n"

    assert _unresolved(fixture, tree) == [("CAP-2", "no_such_check")]


def test_a_retired_capability_and_a_templated_token_are_not_judged(tree: _Tree) -> None:
    fixture = (
        "- **CAP-3 — gone with its console** ← fixture (retired 2026-08-25: deleted)\n"
        "  - **intent:** `scripts/no_such_check.py` refreshed `data.js`.\n"
        "- **CAP-4 — shapes pass** ← fixture (shipped 2026-01-01)\n"
        "  - **intent:** `spec-<e>-<n>-*.md` and `python -m pyforge.doctor.sources <name>` are shapes; "
        "`core/dispatch_retry.py:115` and `cli/spin.py::_latest_run_dir` resolve.\n"
    )

    assert _unresolved(fixture, tree) == []
