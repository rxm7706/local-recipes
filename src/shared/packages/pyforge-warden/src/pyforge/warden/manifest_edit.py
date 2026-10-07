"""Field-scoped manifest requirement edits (Story 14.2).

Pure data transforms only — no subprocess, no jinja rendering, no execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_RE_JINJA = re.compile(r"\{\{")


@dataclass(frozen=True)
class ManifestEditResult:
    """Outcome of attempting one scoped requirement edit."""

    ok: bool
    failure_reason: str | None = None


def _count_package_occurrences(text: str, package: str, *, kind: str) -> int:
    if kind == "pixi":
        patterns = (
            re.compile(rf'^\s*"{re.escape(package)}"\s*=', re.MULTILINE),
            re.compile(rf"^\s*{re.escape(package)}\s*=", re.MULTILINE),
        )
        return sum(len(p.findall(text)) for p in patterns)
    if kind == "pyproject":
        pattern = re.compile(rf'["\']{re.escape(package)}[^"\']*["\']', re.MULTILINE)
        return len(pattern.findall(text))
    if kind == "recipe":
        pattern = re.compile(rf"^\s*-\s*{re.escape(package)}\s+", re.MULTILINE)
        return len(pattern.findall(text))
    return 0


def _edit_pixi_toml(text: str, package: str, floor: str) -> tuple[str, int]:
    patterns = (
        re.compile(
            rf'^(\s*"{re.escape(package)}"\s*=\s*")([^"]*)(")\s*$',
            re.MULTILINE,
        ),
        re.compile(
            rf"^(\s*{re.escape(package)}\s*=\s*')([^']*)(')\s*$",
            re.MULTILINE,
        ),
        re.compile(
            rf"^(\s*{re.escape(package)}\s*=\s*\")([^\"]*)(\")\s*$",
            re.MULTILINE,
        ),
        re.compile(
            rf"^(\s*{re.escape(package)}\s*=\s*)([^\s#]+)(\s*(?:#.*)?)$",
            re.MULTILINE,
        ),
    )
    replacement = rf"\1>={floor}\3"
    for pattern in patterns:
        updated, count = pattern.subn(replacement, text, count=1)
        if count:
            return updated, count
    return text, 0


def _edit_pyproject_toml(text: str, package: str, floor: str) -> tuple[str, int]:
    pattern = re.compile(
        rf'^(\s*["\'])({re.escape(package)})([^"\']*)(["\'],?\s*)$',
        re.MULTILINE,
    )

    def _repl(match: re.Match[str]) -> str:
        return f'{match.group(1)}{match.group(2)}>={floor}{match.group(4)}'

    updated, count = pattern.subn(_repl, text, count=1)
    return updated, count


def _edit_recipe_requirement_line(text: str, package: str, floor: str) -> tuple[str, int]:
    pattern = re.compile(
        rf"^(\s*-\s*{re.escape(package)}\s+)([^\s#]+)(\s*(?:#.*)?)$",
        re.MULTILINE,
    )
    updated, count = pattern.subn(rf"\1>={floor}\3", text, count=1)
    return updated, count


def _manifest_kind(path: Path) -> str | None:
    name = path.name.lower()
    if name == "pixi.toml":
        return "pixi"
    if name == "pyproject.toml":
        return "pyproject"
    if name in {"meta.yaml", "recipe.yaml"}:
        return "recipe"
    return None


def edit_requirement_to_floor(
    manifest_path: Path,
    *,
    package: str,
    floor: str,
) -> ManifestEditResult:
    """Edit exactly one requirement in ``manifest_path`` to ``>=floor``."""
    if not manifest_path.is_file():
        return ManifestEditResult(ok=False, failure_reason=f"manifest not found: {manifest_path}")
    kind = _manifest_kind(manifest_path)
    if kind is None:
        return ManifestEditResult(ok=False, failure_reason=f"unsupported manifest kind: {manifest_path.name}")
    text = manifest_path.read_text(encoding="utf-8")
    if _count_package_occurrences(text, package, kind=kind) > 1:
        return ManifestEditResult(ok=False, failure_reason="requirement appears in more than one place")
    if kind == "pixi":
        updated, count = _edit_pixi_toml(text, package, floor)
    elif kind == "pyproject":
        updated, count = _edit_pyproject_toml(text, package, floor)
    else:
        updated, count = _edit_recipe_requirement_line(text, package, floor)
    if count == 0:
        return ManifestEditResult(ok=False, failure_reason="could not scope edit to one requirement")
    if _RE_JINJA.search(updated):
        return ManifestEditResult(ok=False, failure_reason="requirement uses a template expression")
    manifest_path.write_text(updated, encoding="utf-8")
    return ManifestEditResult(ok=True)


def parse_manifest_path_from_location(location: str) -> str | None:
    """``pixi.toml [pypi-dependencies]`` -> ``pixi.toml``."""
    segment = location.strip().split("[", 1)[0].strip()
    return segment or None
