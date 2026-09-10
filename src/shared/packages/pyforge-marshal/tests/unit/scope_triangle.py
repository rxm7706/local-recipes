"""Shared scope-triangle seeding for dispatch unit tests (Story 33.9)."""

from __future__ import annotations

from pathlib import Path


def point_scope_triangle(root: Path, slug: str) -> None:
    """Write marker + both artifact symlinks at the recognized relative shape."""
    marker = root / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(slug + "\n", encoding="utf-8")
    out = root / "_bmad-output"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("planning-artifacts", "implementation-artifacts"):
        target_dir = out / "projects" / slug / name
        target_dir.mkdir(parents=True, exist_ok=True)
        link = out / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(Path("projects") / slug / name)
