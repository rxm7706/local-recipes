#!/usr/bin/env python3
"""Generate and drift-check Cursor `.mdc` rules for the BMAD pilot pair.

Story 45.1 / 45.2 / spec-bmad-cursor-interactive-routing CAP-2 (OQ-3):
`.cursor/rules/bmad-build.mdc` and `bmad-build-auto.mdc` are mechanical
derivatives of `.claude/skills/bmad-*/SKILL.md`. A one-time generate is
not the lasting shape — this script is the generator *and* the detector.

Exit 0 clean / 1 findings / 2 could-not-run.
`--write` regenerates the two files (does not exit 1 on drift).
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ("bmad-build", "bmad-build-auto")

CURSOR_TAIL = """## Cursor interactive chat (generated — do not hand-edit)

Reviewer steps that require a context-free subagent: if the Task tool is
available, launch a Task subagent and consume the in-turn result. If the
running surface has no model-invoked Task tool (Ask, no-tools), HALT
`blocked`/`no subagents`. Do not skip review. Do not shell out to
`cursor-agent -p` as a substitute reviewer.

Team memory: Read or @file `.claude/memory/MEMORY.md`. There is no Claude
Code `@path` inline import on this surface.
"""


def _skill_path(name: str) -> Path:
    return ROOT / ".claude" / "skills" / name / "SKILL.md"


def _mdc_path(name: str) -> Path:
    return ROOT / ".cursor" / "rules" / f"{name}.mdc"


def _parse_skill(text: str) -> tuple[str, str, str]:
    if not text.startswith("---"):
        raise ValueError("SKILL.md has no YAML frontmatter")
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---\n")
    if end < 0:
        raise ValueError("SKILL.md frontmatter is unclosed")
    raw, body = rest[:end], rest[end + 5 :]
    data: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        if line.startswith("  ") and key:
            data[key] = data[key] + " " + line.strip()
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if (val.startswith("'") and val.endswith("'")) or (
            val.startswith('"') and val.endswith('"')
        ):
            val = val[1:-1]
        data[key] = val
    name = data.get("name") or ""
    description = data.get("description") or ""
    if not name or not description:
        raise ValueError("SKILL.md frontmatter missing name or description")
    return name, description, body.lstrip("\n")


def render(name: str, description: str, body: str) -> str:
    desc = json.dumps(description, ensure_ascii=False)
    body = body.rstrip() + "\n"
    return (
        f"---\n"
        f"description: {desc}\n"
        f"alwaysApply: false\n"
        f"---\n"
        f"\n"
        f"# {name}\n"
        f"\n"
        f"{body}\n"
        f"{CURSOR_TAIL}"
    )


def expected_for(skill: str) -> str:
    text = _skill_path(skill).read_text(encoding="utf-8")
    name, description, body = _parse_skill(text)
    return render(name, description, body)


def write_all() -> None:
    rules = ROOT / ".cursor" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    for skill in PILOT:
        path = _mdc_path(skill)
        path.write_text(expected_for(skill), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


def check() -> int:
    findings: list[str] = []
    for skill in PILOT:
        src = _skill_path(skill)
        dest = _mdc_path(skill)
        if not src.is_file():
            print(f"[bmad-cursor-mdc] cannot run: missing {src}", file=sys.stderr)
            return 2
        try:
            expected = expected_for(skill)
        except (OSError, ValueError) as exc:
            print(f"[bmad-cursor-mdc] cannot run: {src}: {exc}", file=sys.stderr)
            return 2
        if not dest.is_file():
            findings.append(f"{dest.relative_to(ROOT)}: missing (run --write)")
            continue
        actual = dest.read_text(encoding="utf-8")
        if actual != expected:
            findings.append(
                f"{dest.relative_to(ROOT)}: stale vs {src.relative_to(ROOT)} "
                f"(run pixi run -e local-recipes bmad-cursor-mdc-generate)"
            )
    if findings:
        print(f"[bmad-cursor-mdc] {len(findings)} NEW issue(s):")
        for line in findings:
            print(f"[bmad-cursor-mdc]   NEW: {line}")
        return 1
    print("[bmad-cursor-mdc] ok: pilot .mdc files match SKILL.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate .cursor/rules/bmad-build.mdc and bmad-build-auto.mdc",
    )
    args = parser.parse_args(argv)
    try:
        if args.write:
            write_all()
            return 0
        return check()
    except OSError as exc:
        print(f"[bmad-cursor-mdc] cannot run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
