"""factory-status page data — reads the BMAD artifact state, agent-readably (§ 13.2).

Renders, as ONE deterministic semantic table, the live factory state from three tracked
artifacts:
  * ``sprint-status.yaml`` ``development_status`` (epic/story → status),
  * ``epics.md`` frontmatter ``status``,
  * each BMAD Tier-2 spec under ``_bmad-output/projects/<slug>/planning-artifacts/specs/``
    (``spec-*.md`` at the specs root and ``spec-*/SPEC.md`` + companion ``*.md`` in
    subfolders) → frontmatter ``status``.

The table carries a **build timestamp** (AD-17 — authoring-feeding pages carry build
stamps). The stamp is INJECTED (``build_stamp`` argument), never read from
``datetime.now()`` at import, so the page is deterministic under the gate.

All reads are plain filesystem + YAML (offline). The AC also names
``bmad-drift-check --specs`` JSON as an alternative source for the spec statuses; we read
the spec frontmatter directly instead because shelling out (``subprocess``) is banned in
package code by the A2 no-inline-IO gate — the frontmatter ``status:`` is the same source
of truth that CLI exposes. A missing/malformed artifact degrades to an empty contribution
(never a crash, never fabricated status).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

FRAME_COLUMNS = ["source", "artifact", "key", "status"]
SPEC_SOURCE = "planning-artifacts/specs"
_SKIP_SPEC_FILENAMES = frozenset({"README.md"})


class _StrictSafeLoader(yaml.SafeLoader):
    """A SafeLoader that additionally rejects YAML aliases (billion-laughs / entity-expansion
    resource exhaustion) and duplicate mapping keys — the BMAD artifacts are developer-owned but
    the loader hardening is cheap defense-in-depth (Gemini #87)."""

    def compose_node(self, parent, index):  # type: ignore[override]
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError("YAML aliases are not allowed")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        seen: set = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.YAMLError(f"duplicate key {key!r}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def default_repo_root() -> Path:
    # Walk up to the repo root so this resolves whether run from the source tree or an installed
    # layout (a hardcoded parents[N] is fragile). Anchor on ``.git`` — a UNIQUE repo-root marker:
    # ``pixi.toml`` is NOT unique (the pyforge-atlas member ships its own), so a pixi.toml walk
    # would stop at the member dir and miss ``_bmad-output/`` (Gemini #87, corrected).
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "_bmad-output").is_dir():
            return parent
    # Fallback: the historical source-tree depth (dashboard→atlas→pyforge→src→member→packages
    # →shared→src→root).
    return current.parents[8] if len(current.parents) > 8 else current.parent


def _default_paths() -> dict[str, Path]:
    root = default_repo_root()
    proj = root / "_bmad-output" / "projects" / "pyforge-atlas"
    return {
        "sprint_status_path": proj / "implementation-artifacts" / "sprint-status.yaml",
        "epics_path": proj / "planning-artifacts" / "epics.md",
        "projects_root": root / "_bmad-output" / "projects",
    }


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse a leading ``---``-delimited YAML frontmatter block; {} if absent/malformed."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        parsed = yaml.load(parts[1], Loader=_StrictSafeLoader)
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_sprint_status(path: str | Path | None) -> dict[str, Any]:
    """The ``development_status`` map (epic/story key → status); {} if missing/malformed."""
    if not path or not Path(path).exists():
        return {}
    try:
        doc = yaml.load(Path(path).read_text(encoding="utf-8-sig"), Loader=_StrictSafeLoader)
    except yaml.YAMLError:
        return {}
    if not isinstance(doc, dict):
        return {}
    dev = doc.get("development_status")
    return dict(dev) if isinstance(dev, dict) else {}


def read_epics_status(path: str | Path | None) -> str | None:
    """``epics.md`` frontmatter ``status``; None if missing/malformed/absent."""
    if not path or not Path(path).exists():
        return None
    fm = _parse_frontmatter(Path(path).read_text(encoding="utf-8-sig"))
    status = fm.get("status")
    return str(status) if status is not None else None


def read_spec_statuses(specs_dir: str | Path | None) -> dict[str, str]:
    """Each ``*.md`` in a flat specs directory (by stem) → frontmatter ``status``.

    Used when ``build_factory_status_frame(specs_dir=...)`` injects a fixture tree;
    production defaults use :func:`read_bmad_spec_statuses` instead.
    """
    out: dict[str, str] = {}
    if not specs_dir or not Path(specs_dir).exists():
        return out
    for md in sorted(Path(specs_dir).glob("*.md")):
        if md.name in _SKIP_SPEC_FILENAMES:
            continue
        fm = _parse_frontmatter(md.read_text(encoding="utf-8-sig"))
        status = fm.get("status")
        if status is not None:
            out[md.stem] = str(status)
    return out


def _collect_spec_md_files(specs_dir: Path) -> list[Path]:
    """Markdown spec files under one project's ``planning-artifacts/specs/``."""
    if not specs_dir.is_dir():
        return []
    files: list[Path] = []
    for md in sorted(specs_dir.glob("*.md")):
        if md.name not in _SKIP_SPEC_FILENAMES:
            files.append(md)
    for sub in sorted(specs_dir.iterdir()):
        if not sub.is_dir() or not sub.name.startswith("spec-"):
            continue
        spec_md = sub / "SPEC.md"
        if spec_md.is_file():
            files.append(spec_md)
            continue
        for md in sorted(sub.glob("*.md")):
            if md.name.startswith(".memlog"):
                continue
            files.append(md)
            break
    return files


def _bmad_spec_key(project_slug: str, specs_dir: Path, md: Path) -> str:
    rel = md.relative_to(specs_dir)
    if rel.parent == Path("."):
        return f"{project_slug}/{rel.stem}"
    return f"{project_slug}/{rel.parent.name}"


def read_bmad_spec_statuses(projects_root: str | Path | None) -> dict[str, str]:
    """Each BMAD Tier-2 spec ``<project>/<artifact>`` → frontmatter ``status``."""
    out: dict[str, str] = {}
    if not projects_root or not Path(projects_root).is_dir():
        return out
    for proj_dir in sorted(Path(projects_root).iterdir()):
        if not proj_dir.is_dir():
            continue
        specs_dir = proj_dir / "planning-artifacts" / "specs"
        for md in _collect_spec_md_files(specs_dir):
            fm = _parse_frontmatter(md.read_text(encoding="utf-8-sig"))
            status = fm.get("status")
            if status is not None:
                out[_bmad_spec_key(proj_dir.name, specs_dir, md)] = str(status)
    return out


def build_factory_status_frame(
    *,
    build_stamp: str,
    sprint_status_path: str | Path | None = None,
    epics_path: str | Path | None = None,
    specs_dir: str | Path | None = None,
    projects_root: str | Path | None = None,
) -> pd.DataFrame:
    """The deterministic factory-status table (AD-17 build stamp is row 0).

    ``build_stamp`` is injected (deterministic under test); the artifact paths default to
    the tracked repo locations but are injectable for the gate's fixtures.

    Spec statuses default to BMAD Tier-2 under ``_bmad-output/projects/*/planning-artifacts/specs/``.
    Pass ``specs_dir`` to override with a flat fixture directory (tests only).
    """
    defaults = _default_paths()
    sprint_status_path = (
        sprint_status_path if sprint_status_path is not None else defaults["sprint_status_path"]
    )
    epics_path = epics_path if epics_path is not None else defaults["epics_path"]
    if specs_dir is not None:
        spec_statuses = read_spec_statuses(specs_dir)
    else:
        root = projects_root if projects_root is not None else defaults["projects_root"]
        spec_statuses = read_bmad_spec_statuses(root)

    rows: list[dict[str, str]] = [
        # AD-17: the build timestamp travels IN the rendered surface, row 0.
        {"source": "build", "artifact": "build_stamp", "key": "generated_at", "status": build_stamp}
    ]
    for key, value in read_sprint_status(sprint_status_path).items():
        rows.append(
            {"source": "sprint-status.yaml", "artifact": "development_status", "key": str(key), "status": str(value)}
        )
    epics_status = read_epics_status(epics_path)
    # Only contribute a row when epics.md actually yields a status — a missing/malformed
    # epics.md contributes ZERO rows, exactly like sprint-status.yaml and BMAD specs above.
    # (Reviewer-B S1: appending str(None) rendered a literal "None" status an agent could
    # not distinguish from a real None; the "never fabricated status" contract wins.)
    if epics_status is not None:
        rows.append(
            {"source": "epics.md", "artifact": "frontmatter", "key": "status", "status": str(epics_status)}
        )
    for name, status in spec_statuses.items():
        rows.append({"source": SPEC_SOURCE, "artifact": name, "key": "status", "status": status})

    return pd.DataFrame(rows, columns=FRAME_COLUMNS)
