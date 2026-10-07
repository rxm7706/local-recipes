"""One current dated export per kind under ``presentations/*/src/{pptx,marp}/`` (CAP-53).

Every writer adds ``<stem>-YYYY-MM-DD.<ext>``; pickers keep the newest ISO date per
kind. This module is the single definition of that rule for enforcement — stdlib only.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

_DATE_SUFFIX = re.compile(r"-(?P<iso>\d{4}-\d{2}-\d{2})$")
_EXPORT_SUBDIRS = ("src/pptx", "src/marp")


def _kind_key(path: Path, presentations_root: Path) -> tuple[str, str, str] | None:
    """Directory (relative to ``presentations/``), product stem, suffix — or skip."""
    name = path.name
    if name.endswith(".stamp.json"):
        return None
    stem = path.stem
    match = _DATE_SUFFIX.search(stem)
    if match is None:
        return None
    try:
        date.fromisoformat(match.group("iso"))
    except ValueError:
        return None
    try:
        rel_dir = path.parent.relative_to(presentations_root).as_posix()
    except ValueError:
        return None
    product = stem[: match.start()]
    return (rel_dir, product, path.suffix)


def superseded(root: Path | None = None) -> list[tuple[Path, Path]]:
    """Every dated export that is not the newest of its kind.

    Returns ``(superseded_path, current_path)`` pairs. Sidecar ``.stamp.json`` files
    are not kinds themselves; callers prune ``<file>.stamp.json`` alongside a removed
    export when present.
    """
    presentations = (root or Path.cwd()) / "presentations"
    if not presentations.is_dir():
        return []

    by_kind: dict[tuple[str, str, str], list[tuple[str, Path]]] = defaultdict(list)
    for topic_dir in sorted(presentations.iterdir()):
        if not topic_dir.is_dir():
            continue
        for sub in _EXPORT_SUBDIRS:
            export_dir = topic_dir / sub
            if not export_dir.is_dir():
                continue
            for path in export_dir.iterdir():
                if not path.is_file():
                    continue
                kind = _kind_key(path, presentations)
                if kind is None:
                    continue
                iso = _DATE_SUFFIX.search(path.stem).group("iso")  # type: ignore[union-attr]
                by_kind[kind].append((iso, path))

    out: list[tuple[Path, Path]] = []
    for entries in by_kind.values():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda pair: pair[0])
        current = entries[-1][1]
        for _iso, path in entries[:-1]:
            out.append((path, current))
    out.sort(key=lambda pair: pair[0].as_posix())
    return out


def newest_export(
    presentations_root: Path,
    topic: str,
    subdir: str,
    product: str,
    suffix: str,
) -> Path | None:
    """The current dated export for one kind (newest ISO date), or ``None``."""
    if subdir not in _EXPORT_SUBDIRS:
        msg = f"subdir must be one of {_EXPORT_SUBDIRS}, got {subdir!r}"
        raise ValueError(msg)
    export_dir = presentations_root / topic / subdir
    if not export_dir.is_dir():
        return None
    kind = (f"{topic}/{subdir}", product, suffix)
    dated: list[tuple[str, Path]] = []
    for path in export_dir.iterdir():
        if not path.is_file():
            continue
        if _kind_key(path, presentations_root) != kind:
            continue
        iso = _DATE_SUFFIX.search(path.stem).group("iso")  # type: ignore[union-attr]
        dated.append((iso, path))
    if not dated:
        return None
    dated.sort(key=lambda pair: pair[0])
    return dated[-1][1]


def _sidecar(export_path: Path) -> Path:
    return export_path.parent / f"{export_path.name}.stamp.json"


def main(argv: list[str] | None = None) -> int:
    root = Path.cwd()
    if argv is None:
        argv = sys.argv[1:]
    if argv:
        root = Path(argv[0]).resolve()
    pairs = superseded(root)
    if not pairs:
        return 0
    presentations = root / "presentations"
    for old, current in pairs:
        try:
            old_rel = old.relative_to(presentations.parent)
            cur_rel = current.relative_to(presentations.parent)
        except ValueError:
            old_rel = old
            cur_rel = current
        sidecar = _sidecar(old)
        if sidecar.is_file():
            try:
                side_rel = sidecar.relative_to(presentations.parent)
            except ValueError:
                side_rel = sidecar
            print(f"{old_rel} (sidecar {side_rel}; current {cur_rel})")
        else:
            print(f"{old_rel} (current {cur_rel})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
