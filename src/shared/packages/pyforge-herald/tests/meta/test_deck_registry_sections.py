"""Story 21.10: every real deck README's § *Design project* section stays
``registry.read()``-parseable.

A hand-edit that reintroduces a multi-line body under the ``## Design
project (the bridge's far end)`` heading breaks the fresh-clone bootstrap
recipe in ``docs/specs/presentation-deck.md`` silently -- this has already
happened once live (``unity-data-stack``'s own ``### Provenance`` note).
``test_registry.py`` only exercises synthetic ``tmp_path`` fixtures per its
own docstring, so nothing previously covered the real ``presentations/``
tree.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import registry
from pyforge.herald.errors import HeraldError

DELIBERATELY_UNREGISTERED = frozenset({"agentic-sdlc"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "presentations").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + presentations/)")


def test_every_deck_readme_parses_or_is_deliberately_unregistered():
    root = _repo_root()
    readmes = sorted((root / "presentations").glob("*/README.md"))
    assert readmes, "expected at least one presentations/*/README.md"

    failures: list[str] = []
    for readme in readmes:
        slug = readme.parent.name
        try:
            project = registry.read(readme)
        except HeraldError as exc:
            failures.append(f"{slug}: registry.read() raised {exc!r}")
            continue
        if project is None and slug not in DELIBERATELY_UNREGISTERED:
            failures.append(f"{slug}: no § Design project section (expected one)")
        if project is not None and slug in DELIBERATELY_UNREGISTERED:
            failures.append(f"{slug}: unexpectedly registered -- update DELIBERATELY_UNREGISTERED")

    assert not failures, "\n".join(failures)
