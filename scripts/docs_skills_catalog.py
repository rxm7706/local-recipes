#!/usr/bin/env python3
"""Generator: ``docs/reference/skills-catalog.md`` from every
``.claude/skills/*/`` directory's own frontmatter (Story 30.3,
spec-pyforge-doctor CAP-84).

Three real on-disk layouts, all read directly (never imported, never
assumed -- a skill directory is data, not code):

* a plain skill (`bmad-*`, most curated skills, `skf-setup`): frontmatter
  lives in the directory's own top-level ``SKILL.md``.
* an SKF-exported skill (`pyforge-*`, `cf-atlas-legacy`): no top-level
  ``SKILL.md`` at all -- an ``active`` symlink names a versioned
  subdirectory, and the real ``SKILL.md`` sits one level deeper, at
  ``active/<dir-name>/SKILL.md`` (verified live 2026-09-24 against
  ``pyforge-doctor`` and ``cf-atlas-legacy``). ``skill-brief.yaml`` at the
  top level is the fallback when that nested file is somehow absent.
* not a skill at all (`shared/`, `knowledge/`): neither shape resolves --
  skipped, not a finding.

Usage::

    python scripts/docs_skills_catalog.py            # regenerate + write + stamp
    python scripts/docs_skills_catalog.py --check     # exit 0 if current, 1 if stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docs_gen_common as common  # noqa: E402

PAGE_REL = "reference/skills-catalog.md"
GENERATOR_REL = "scripts/docs_skills_catalog.py"
TASK_NAME = "docs-skills-catalog"

_INTRO = """\
# Skills catalog

Every `.claude/skills/*/` directory that carries a `SKILL.md` (directly, or
one level under its `active/` symlink for an SKF-exported skill), with the
`name`/`description` its own frontmatter declares. Category is derived
from the directory name's prefix (`bmad-`, `pyforge-`, `skf-`; everything
else is "project"). See `.claude/skills/*/SKILL.md` itself for the full
skill body -- this page is a lookup index, not a substitute for reading one.
"""


def _clean(text: str) -> str:
    return " ".join(str(text).split())


def _category(dir_name: str) -> str:
    if dir_name.startswith("bmad-"):
        return "bmad"
    if dir_name.startswith("pyforge-"):
        return "pyforge station"
    if dir_name.startswith("skf-"):
        return "skf"
    return "project"


def _skill_frontmatter(entry: Path) -> dict | None:
    skill_md = entry / "SKILL.md"
    if skill_md.is_file():
        return common.parse_frontmatter(skill_md.read_text(encoding="utf-8"))

    active = entry / "active"
    if active.is_dir():
        nested = active / entry.name / "SKILL.md"
        if nested.is_file():
            return common.parse_frontmatter(nested.read_text(encoding="utf-8"))

    brief = entry / "skill-brief.yaml"
    if brief.is_file():
        import yaml

        try:
            data = yaml.safe_load(brief.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            return None
        return data if isinstance(data, dict) else None

    return None


def discover_skills(root: Path) -> list[dict]:
    skills_dir = root / ".claude" / "skills"
    skills: list[dict] = []
    if not skills_dir.is_dir():
        return skills
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        frontmatter = _skill_frontmatter(entry)
        if frontmatter is None:
            continue
        name = frontmatter.get("name") or entry.name
        description = _clean(frontmatter.get("description") or "")
        skills.append(
            {
                "dir": entry.name,
                "name": name,
                "description": description,
                "category": _category(entry.name),
            }
        )
    return skills


def render(root: Path, stamp: dict[str, str]) -> str:
    skills = discover_skills(root)
    by_category: dict[str, int] = {}
    for skill in skills:
        by_category[skill["category"]] = by_category.get(skill["category"], 0) + 1
    counts = ", ".join(f"{count} {category}" for category, count in sorted(by_category.items()))

    lines = [
        common.render_header(GENERATOR_REL, TASK_NAME, stamp),
        "",
        _INTRO,
        f"{len(skills)} skills ({counts}), as of this render.\n",
        "| Skill | Category | Description |",
        "|---|---|---|",
    ]
    for skill in sorted(skills, key=lambda s: s["name"]):
        description = skill["description"].replace("|", "\\|")
        lines.append(f"| `{skill['name']}` | {skill['category']} | {description} |")
    lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report staleness; never write")
    args = parser.parse_args()

    stamp = common.head_stamp(common.REPO_ROOT)
    content = render(common.REPO_ROOT, stamp)
    return common.write_generated_page(common.REPO_ROOT, PAGE_REL, content, check=args.check, stamp=stamp)


if __name__ == "__main__":
    sys.exit(main())
