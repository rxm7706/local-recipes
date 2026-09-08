#!/usr/bin/env python3
"""Detector: the governance documents' own references still resolve.

The documents that define how this factory works — `_bmad-output/EXEMPLAR-STANDARD.md`,
`AGENTS.md`, `CLAUDE.md`, `docs/reference/test-charter.md` — name skills, scripts and
paths. Nothing checked that those names still existed, so EXEMPLAR-STANDARD.md spent two
BMAD versions telling readers to run `bmad-document-project`, `bmad-create-story`,
`bmad-check-implementation-readiness` and `bmad-dev-auto`, none of which had existed since
6.11, plus three research skills 6.12 folded into `bmad-deep-recon`. Seven staleness
findings, all discovered by hand on 2026-09-07, none by a gate.

This is INV-4's argument applied to prose: the instruments that enforce the model must
themselves be inside it. A governance document is an instrument.

What is checked, and only what can be checked mechanically:

* **Skill names** — a backticked ``bmad-*`` / ``skf-*`` token must resolve to a directory
  under ``.claude/skills/``. This is the class that actually rotted.
* **Script paths** — a backticked path ending ``.py`` under ``scripts/`` or ``_bmad/``
  must exist on disk.
* **Repo-relative file paths** — a backticked path with a directory separator that names
  a real top-level directory of this repo must exist.

Deliberate historical citations — a name quoted *because* it was removed — are exempted
by an explicit marker, never by a heuristic:

    <!-- governance-currency:ignore-start (reason) -->
    ...prose naming things that must NOT resolve...
    <!-- governance-currency:ignore-end -->

An unmarked dead reference fails. That asymmetry is the point: forgetting the marker
costs a red run, while a silent heuristic would have let the original rot through.

scope=repo: reads tracked documents and the tracked skills/scripts trees only.

Exit 0 every reference resolves / 1 findings / 2 could-not-run.
Flags: --json, --file <path> (check one document).
Contract: _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/
spec-fleet-consistency-standard/SPEC.md (CAP-6).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

DETECTOR = {"scope": "repo"}

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The governed documents. A document that does not exist is itself a finding —
# never a silent skip, which is how a "clean" run could mean "read nothing".
DOCUMENTS = (
    "_bmad-output/EXEMPLAR-STANDARD.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/reference/test-charter.md",
)

SKILLS_DIR = ROOT / ".claude" / "skills"

_IGNORE_START = re.compile(r"<!--\s*governance-currency:ignore-start")
_IGNORE_END = re.compile(r"<!--\s*governance-currency:ignore-end")

# `bmad-foo` / `skf-bar` inside backticks. Trailing punctuation is stripped by the
# character class rather than a lookbehind, so `bmad-prd.` and `bmad-prd,` both work.
_SKILL = re.compile(r"`((?:bmad|skf)-[a-z0-9][a-z0-9-]*)`")
# A backticked path ending in .py. Anchored on a known code root so prose like
# `foo.py` in an example does not mint a finding.
_SCRIPT = re.compile(r"`((?:scripts|_bmad)/[A-Za-z0-9._/-]+\.py)`")
# A backticked repo-relative path under a real top-level directory.
_PATH = re.compile(r"`((?:docs|src|recipes|_bmad-output|\.github|\.claude)/[A-Za-z0-9._/-]+)`")


def _strip_ignored(text: str) -> str:
    """Blank out ignore-marked regions, preserving line numbering."""
    out, skipping = [], False
    for line in text.splitlines():
        if _IGNORE_START.search(line):
            skipping = True
            out.append("")
            continue
        if _IGNORE_END.search(line):
            skipping = False
            out.append("")
            continue
        out.append("" if skipping else line)
    return "\n".join(out)


def _pixi_task_names() -> frozenset[str]:
    """Task names declared in pixi.toml, read as text.

    Deliberately not a TOML parse: this must work with no dependency beyond the
    stdlib, and a task header is unambiguous.
    """
    toml = ROOT / "pixi.toml"
    if not toml.is_file():
        return frozenset()
    return frozenset(
        re.findall(r"^\[(?:feature\.[^.]+\.)?tasks\.([A-Za-z0-9._-]+)\]",
                   toml.read_text(encoding="utf-8", errors="replace"), re.M)
    )


def _pixi_dependency_names() -> frozenset[str]:
    """Package names declared anywhere in pixi.toml.

    `bmad-loop` and `bmad-method` are installed packages with their own CLIs, not
    skills — `bmad-loop-resolve`/`-setup`/`-sweep` are the skills that wrap the
    former. Resolving against the manifest keeps that distinction derived.
    """
    toml = ROOT / "pixi.toml"
    if not toml.is_file():
        return frozenset()
    return frozenset(
        re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*=",
                   toml.read_text(encoding="utf-8", errors="replace"), re.M)
    )


_TASKS: frozenset[str] | None = None


def _resolves_as_identifier(name: str) -> bool:
    """A ``bmad-*``/``skf-*`` token names a skill, a script, or a pixi task.

    All three are DERIVED from the tree rather than hand-listed, because the first
    cut of this detector hand-assumed every such token was a skill and reported
    `bmad-loop` (the orchestrator package), `bmad-switch` (`scripts/bmad-switch`)
    and `bmad-groundtruth` (a pixi task) as dead. That is exactly the failure
    EXEMPLAR-STANDARD's INV-0 lesson names: a detector's own bugs propagate outward
    as confident, wrong numbers. Validated against a tree already known well before
    the backlog was trusted.
    """
    global _TASKS
    d = SKILLS_DIR / name
    if d.is_dir() and any(d.rglob("SKILL.md")):
        return True
    if (ROOT / "scripts" / name).exists() or (ROOT / "scripts" / f"{name}.py").exists():
        return True
    if _TASKS is None:
        _TASKS = _pixi_task_names() | _pixi_dependency_names()
    return name in _TASKS


def _is_git_ignored(rel: str) -> bool:
    """Tier-3 paths are gitignored and absent from a fresh clone by design.

    This detector is scope=repo, so it may only judge tracked state; a reference to
    a gitignored artifact is not a dead reference, it is a reference to something
    that never ships.
    """
    import subprocess
    try:
        return subprocess.run(
            ["git", "check-ignore", "-q", rel], cwd=ROOT, check=False
        ).returncode == 0
    except OSError:
        return False


def _check_document(rel: str) -> list[dict]:
    findings: list[dict] = []
    path = ROOT / rel
    if not path.is_file():
        return [{"document": rel, "kind": "missing-document", "reference": rel,
                 "line": 0, "detail": "governed document does not exist"}]

    raw = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_ignored(raw)

    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _SKILL.finditer(line):
            name = m.group(1)
            if not _resolves_as_identifier(name):
                findings.append({
                    "document": rel, "kind": "skill-not-found", "reference": name,
                    "line": lineno,
                    "detail": "resolves as no skill, script or pixi task",
                })
        for m in _SCRIPT.finditer(line):
            ref = m.group(1)
            if not (ROOT / ref).exists() and not _is_git_ignored(ref):
                findings.append({
                    "document": rel, "kind": "script-not-found", "reference": ref,
                    "line": lineno, "detail": "path does not exist",
                })
        for m in _PATH.finditer(line):
            ref = m.group(1).rstrip("/")
            if "*" in ref or "<" in ref:
                continue  # a glob or a placeholder, not a literal path
            if not (ROOT / ref).exists() and not _is_git_ignored(ref):
                findings.append({
                    "document": rel, "kind": "path-not-found", "reference": ref,
                    "line": lineno, "detail": "path does not exist",
                })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--file", metavar="PATH", action="append",
                    help="check this document instead of the governed set (repeatable)")
    args = ap.parse_args()

    documents = tuple(args.file) if args.file else DOCUMENTS
    findings: list[dict] = []
    for rel in documents:
        findings.extend(_check_document(rel))

    if args.json:
        print(json.dumps({"documents": list(documents), "findings": findings}, indent=2))
        return 1 if findings else 0

    if not findings:
        print(f"[governance-currency] governance-currency: ok -- every skill, script and "
              f"path named in {len(documents)} governed document(s) resolves")
        return 0

    by_doc: dict[str, list[dict]] = {}
    for f in findings:
        by_doc.setdefault(f["document"], []).append(f)
    for doc, items in by_doc.items():
        print(f"[governance-currency] {doc}: {len(items)} dead reference(s)")
        for f in items:
            print(f"[governance-currency]   {f['kind']}: {f['reference']} "
                  f"(line {f['line']}) -- {f['detail']}")
    print(f"[governance-currency] FINDINGS: {len(findings)} dead reference(s) across "
          f"{len(by_doc)} document(s). Fix the reference, or -- when the name is quoted "
          f"BECAUSE it was removed -- wrap it in governance-currency:ignore-start/end "
          f"with a reason.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # never a false green
        print(f"[governance-currency] could-not-run: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
