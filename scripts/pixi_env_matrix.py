#!/usr/bin/env python3
"""Render a measured per-environment matrix from ``pixi.lock``.

Story 43.5 (spec-43-5-one-interpreter-story): replaces the Dream's empirical
Multi-Python "100 % SUCCESS / byte-for-byte" table with lock-derived facts —
env name, resolved Python minor, conda record count (``linux-64`` when present,
else the first platform block), and platform keys.

Stdlib + PyYAML only. Doctor's ``bmad-drift`` check warns when the embedded
Dream block is older than ``pixi.lock`` (``check_pixi_env_matrix`` in
``pyforge.doctor.sources.factory``).

Usage:
  python scripts/pixi_env_matrix.py
  python scripts/pixi_env_matrix.py --update docs/dreams/pyforge-unifying-strategy.md
  python scripts/pixi_env_matrix.py --check docs/dreams/pyforge-unifying-strategy.md
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK = REPO_ROOT / "pixi.lock"
DEFAULT_DREAM = REPO_ROOT / "docs" / "dreams" / "pyforge-unifying-strategy.md"

BEGIN_MARKER = "<!-- pixi-env-matrix:begin"
END_MARKER = "<!-- pixi-env-matrix:end -->"

_PYTHON_RE = re.compile(r"/(?:python|cpython)-(\d+)\.(\d+)")


@dataclass(frozen=True)
class EnvRow:
    name: str
    python: str
    conda_records: int
    platforms: tuple[str, ...]


def lock_digest(lock_path: Path) -> str:
    data = lock_path.read_bytes()
    return hashlib.sha256(data).hexdigest()[:16]


def load_lock(lock_path: Path) -> dict:
    return yaml.safe_load(lock_path.read_text(encoding="utf-8"))


def _python_from_entries(entries: list[dict]) -> str:
    for entry in entries:
        url = entry.get("conda", "")
        match = _PYTHON_RE.search(url)
        if match:
            return f"{match.group(1)}.{match.group(2)}.*"
    return "unknown"


def build_rows(lock: dict) -> list[EnvRow]:
    environments = lock.get("environments") or {}
    rows: list[EnvRow] = []
    for name in sorted(environments):
        packages_by_platform = environments[name].get("packages") or {}
        if not packages_by_platform:
            continue
        platforms = tuple(sorted(packages_by_platform))
        reference = "linux-64" if "linux-64" in packages_by_platform else platforms[0]
        entries = packages_by_platform[reference]
        conda_records = sum(1 for entry in entries if "conda" in entry)
        rows.append(
            EnvRow(
                name=name,
                python=_python_from_entries(entries),
                conda_records=conda_records,
                platforms=platforms,
            )
        )
    return rows


def render_markdown(rows: list[EnvRow], *, lock_path: Path) -> str:
    digest = lock_digest(lock_path)
    lines = [
        f"{BEGIN_MARKER} lock-sha256={digest} -->",
        "",
        "Measured from ``pixi.lock`` (not a cross-minor solver benchmark). "
        "Regenerate with ``python scripts/pixi_env_matrix.py --update "
        "docs/dreams/pyforge-unifying-strategy.md`` after lock changes.",
        "",
        "| Environment | Python | Conda records | Platforms |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        platform_cell = ", ".join(f"``{p}``" for p in row.platforms)
        lines.append(
            f"| ``{row.name}`` | ``{row.python}`` | {row.conda_records:,} | {platform_cell} |"
        )
    lines.extend(["", END_MARKER])
    return "\n".join(lines)


def embedded_block(dream_text: str) -> str | None:
    begin = dream_text.find(BEGIN_MARKER)
    if begin == -1:
        return None
    end = dream_text.find(END_MARKER, begin)
    if end == -1:
        return None
    return dream_text[begin : end + len(END_MARKER)]


def embedded_lock_digest(dream_text: str) -> str | None:
    match = re.search(r"<!-- pixi-env-matrix:begin lock-sha256=([0-9a-f]+)", dream_text)
    return match.group(1) if match else None


def matrix_is_stale(dream_path: Path, lock_path: Path) -> bool:
    dream_text = dream_path.read_text(encoding="utf-8")
    embedded = embedded_lock_digest(dream_text)
    if embedded is None:
        return True
    return embedded != lock_digest(lock_path)


def update_dream(dream_path: Path, lock_path: Path) -> str:
    dream_text = dream_path.read_text(encoding="utf-8")
    block = render_markdown(build_rows(load_lock(lock_path)), lock_path=lock_path)
    section_header = "## Pixi environment matrix (measured)\n\n"
    wrapped = section_header + block + "\n"

    begin = dream_text.find("## Pixi environment matrix (measured)")
    if begin != -1:
        end = dream_text.find("\n## ", begin + 1)
        if end == -1:
            end = dream_text.find("\n---\n", begin + 1)
        if end == -1:
            end = len(dream_text)
        return dream_text[:begin] + wrapped + dream_text[end:].lstrip("\n")

    anchor = "## Fleet conventions (one vocabulary)"
    idx = dream_text.find(anchor)
    if idx == -1:
        raise SystemExit(f"cannot find insertion anchor in {dream_path}")
    return dream_text[:idx] + wrapped + "\n" + dream_text[idx:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lockfile", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--dream", type=Path, default=DEFAULT_DREAM)
    parser.add_argument(
        "--update",
        action="store_true",
        help="Rewrite the measured matrix block in the Dream file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when the Dream matrix is missing or older than pixi.lock",
    )
    args = parser.parse_args(argv)

    lock_path = args.lockfile.resolve()
    dream_path = args.dream.resolve()
    rows = build_rows(load_lock(lock_path))

    if args.update:
        dream_path.write_text(update_dream(dream_path, lock_path), encoding="utf-8")
        return 0

    if args.check:
        if not dream_path.is_file():
            print(f"pixi_env_matrix: dream missing: {dream_path}", file=sys.stderr)
            return 1
        if matrix_is_stale(dream_path, lock_path):
            print(
                "pixi_env_matrix: dream matrix is stale relative to pixi.lock",
                file=sys.stderr,
            )
            return 1
        return 0

    print(render_markdown(rows, lock_path=lock_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
