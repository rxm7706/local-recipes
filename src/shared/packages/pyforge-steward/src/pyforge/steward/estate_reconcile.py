"""``estate reconcile`` — regenerate derived surfaces and reconcile spec drift (Story 100.3)."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

from .estate import (
    EstateDeps,
    _ensure_flag,
    _list_journals,
    _load_journal,
    _record_step,
    _refusal,
)
from .interfaces import DutyResult

EXIT_RECONCILE_CHECKS = 1

WATCH_PATHS: tuple[str, ...] = (
    "pixi.toml",
    "pixi.lock",
    "environment.yaml",
    "docs/reference/library-llms-full.md",
    "docs/reference/bmad-estate-llms-full.md",
    "docs/dreams/pyforge-unifying-strategy.md",
    "docs/reference/environments.md",
    "docs/how-to/pixi-tasks.md",
    "recipes/bmad-suite/recipe.yaml",
)

BASELINE_REL = Path("scripts") / ".spec-surface-baseline.json"


def _sha1(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _fingerprints(root: Path, paths: tuple[str, ...]) -> dict[str, str | None]:
    return {rel: _sha1(root / rel) for rel in paths}


def _moved_paths(before: dict[str, str | None], after: dict[str, str | None]) -> set[str]:
    moved: set[str] = set()
    for rel in before:
        if before.get(rel) != after.get(rel):
            moved.add(rel)
    return moved


def _journal_moves_include(journal: dict[str, Any], predicate: Callable[[str], bool]) -> bool:
    for move in journal.get("moves") or []:
        if isinstance(move, dict) and predicate(str(move.get("package") or "")):
            return True
    return False


def _build_generators(journal: dict[str, Any], root: Path) -> list[tuple[str, list[str], str | None]]:
    """Return ordered (label, argv, output_rel) rows; output_rel when stdout must be captured."""
    py = sys.executable
    gens: list[tuple[str, list[str], str | None]] = [
        (
            "environment.yaml",
            ["pixi", "project", "export", "conda-environment", "-e", "build"],
            "environment.yaml",
        ),
        ("library-catalog-floors", [py, "scripts/llms_full_check.py", "--fix-floors"], None),
        (
            "bmad-estate-catalog",
            [py, "-m", "pyforge.scribe.cli", "catalog", "bmad-estate", "--write"],
            None,
        ),
        (
            "env-matrix",
            [
                py,
                "scripts/pixi_env_matrix.py",
                "--update",
                "docs/dreams/pyforge-unifying-strategy.md",
            ],
            None,
        ),
        ("docs-environments", [py, "scripts/docs_environments.py"], None),
        ("docs-pixi-tasks", [py, "scripts/docs_pixi_tasks.py"], None),
    ]
    if _journal_moves_include(journal, lambda pkg: pkg == "pixi"):
        gens.append(("bump-pixi-version", [py, "scripts/bump_pixi_version.py"], None))
    if _journal_moves_include(journal, lambda pkg: pkg == "bmad-method" or pkg.startswith("bmad-")):
        gens.append(
            (
                "generate-bmad-suite",
                [py, ".claude/scripts/conda-forge-expert/bmad_suite_metapackage.py"],
                None,
            )
        )
    return gens


GATING_CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("llms-full-check", [sys.executable, "scripts/llms_full_check.py"]),
    ("bmad-estate-check", [sys.executable, "scripts/bmad_estate_check.py"]),
    ("pixi-version-check", [sys.executable, "scripts/pixi_version_check.py"]),
    ("target-version-check", [sys.executable, "scripts/target_version_check.py"]),
    ("sbom-gaps-check", [sys.executable, "scripts/sbom_gap_derive.py"]),
    ("platform-policy-suite-check", [sys.executable, "-m", "pyforge.doctor.sources", "platform-policy-suite"]),
    ("pin-policy-check", [sys.executable, "scripts/pin_policy_check.py", "--check"]),
    ("pixi-lock-check", ["pixi", "lock", "--check"]),
)

WARN_CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("pixi-currency-staleness-check", [sys.executable, "-m", "pyforge.doctor.sources", "pixi-currency-ledger"]),
    (
        "steward-deck-drift",
        [
            sys.executable,
            "-m",
            "pyforge.steward.cli",
            "deck-drift",
            "--slug",
            "pyforge-steward",
            "--path",
            "deck.dc.html",
        ],
    ),
)


def _memlog_has_frontmatter(memlog: Path) -> bool:
    if not memlog.is_file():
        return False
    text = memlog.read_text(encoding="utf-8")
    return text.startswith("---\n") and "\n---\n" in text[4:]


def specs_for_moved_paths(baseline: dict[str, Any], moved: set[str]) -> dict[str, set[str]]:
    """Map spec keys to the subset of ``moved`` paths that spec governs (baseline file keys)."""
    by_spec: dict[str, set[str]] = {}
    for spec_name, entry in baseline.items():
        if not isinstance(entry, dict):
            continue
        files = entry.get("files") or {}
        if not isinstance(files, dict):
            continue
        overlap = set(files).intersection(moved)
        if overlap:
            by_spec[spec_name] = overlap
    return by_spec


@dataclass
class ReconcileDeps(EstateDeps):
    """Extra seams for reconcile (spec-surface, git add, memlog)."""

    read_baseline: Callable[[Path], dict[str, Any]] = field(
        default=lambda root: json.loads((root / BASELINE_REL).read_text(encoding="utf-8"))
    )
    memlog_append: Callable[[Path, str], int] = field(default=lambda _path, _text: 0)
    git_add: Callable[[Path, list[str]], int] = field(default=lambda _root, _paths: 0)
    stamp_spec: Callable[[Path, str], int] = field(default=lambda _root, _spec: 0)


def _run_generator(
    deps: ReconcileDeps,
    argv: list[str],
    output_rel: str | None,
    steps: list[dict],
) -> int:
    started = time.monotonic()
    proc = deps.runner(argv, deps.root)
    if output_rel is not None and proc.returncode == 0:
        out_path = deps.root / output_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(proc.stdout or "", encoding="utf-8")
    _record_step(steps, argv, proc, started)
    return int(proc.returncode)


def _run_check(
    deps: ReconcileDeps,
    name: str,
    argv: list[str],
    checks: list[dict],
) -> int:
    started = time.monotonic()
    proc = deps.runner(argv, deps.root)
    checks.append(
        {
            "name": name,
            "argv": list(argv),
            "exit": int(proc.returncode),
            "seconds": round(time.monotonic() - started, 3),
            "warn_only": False,
        }
    )
    return int(proc.returncode)


def _reconcile_spec_surface(
    deps: ReconcileDeps,
    *,
    moved: set[str],
    journal_path: Path,
    today: date,
    block: dict[str, Any],
) -> DutyResult | None:
    try:
        baseline = deps.read_baseline(deps.root)
    except (OSError, json.JSONDecodeError) as exc:
        return _refusal(f"estate reconcile: spec-surface baseline unreadable ({exc})")

    by_spec = specs_for_moved_paths(baseline, moved)
    if not by_spec:
        block["spec_surface"] = {"specs": [], "memlogs": [], "stamps": []}
        return None

    memlog_events: list[dict[str, Any]] = []
    stamps: list[dict[str, Any]] = []
    paths_union = sorted({p for paths in by_spec.values() for p in paths})
    event_text = (
        f"Surface reconcile {today.isoformat()}: estate refresh moved "
        f"{', '.join(paths_union)}; journal {journal_path.relative_to(deps.root)}"
    )

    for spec_name in sorted(by_spec):
        project, _, spec_dir = spec_name.partition("/")
        memlog_path = (
            deps.root / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / spec_dir / ".memlog.md"
        )
        if not _memlog_has_frontmatter(memlog_path):
            return _refusal(f"estate reconcile: memlog lacks frontmatter: {memlog_path.relative_to(deps.root)}")

        exit_code = deps.memlog_append(memlog_path, event_text)
        memlog_events.append({"spec": spec_name, "path": str(memlog_path.relative_to(deps.root)), "exit": exit_code})
        if exit_code != 0:
            return _refusal(f"estate reconcile: memlog append failed for {spec_name} (exit {exit_code})")

    add_exit = deps.git_add(deps.root, paths_union)
    block["git_add"] = {"paths": paths_union, "exit": add_exit}
    if add_exit != 0:
        return _refusal(f"estate reconcile: git add failed (exit {add_exit})")

    for spec_name in sorted(by_spec):
        stamp_exit = deps.stamp_spec(deps.root, spec_name)
        stamps.append(
            {
                "spec": spec_name,
                "argv": ["spec_surface_check.py", "--write-baseline", "--spec", spec_name],
                "exit": stamp_exit,
            }
        )
        if stamp_exit != 0:
            return _refusal(f"estate reconcile: scoped stamp failed for {spec_name} (exit {stamp_exit})")

    block["spec_surface"] = {"specs": sorted(by_spec), "memlogs": memlog_events, "stamps": stamps}
    return None


def run_reconcile(deps: ReconcileDeps, *, journal_path: Path | None = None) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused

    journals = _list_journals(deps.root)
    if journal_path is None:
        if not journals:
            journal_doc: dict[str, Any] = {"moves": []}
            journal_path = deps.root / ".steward/estate-refresh/reconcile-only.json"
        else:
            journal_path = journals[-1]
            journal_doc = _load_journal(journal_path)
    else:
        journal_doc = _load_journal(journal_path) if journal_path.is_file() else {"moves": []}

    before = _fingerprints(deps.root, WATCH_PATHS)
    gen_steps: list[dict] = []
    for _label, argv, output_rel in _build_generators(journal_doc, deps.root):
        code = _run_generator(deps, argv, output_rel, gen_steps)
        if code != 0 and "bmad-estate" in " ".join(argv):
            # scribe non-zero: continue remaining checks per spec I/O matrix
            pass

    after = _fingerprints(deps.root, WATCH_PATHS)
    moved = _moved_paths(before, after)

    checks: list[dict] = []
    gating_failed = False
    first_fail_name = ""
    for name, argv in GATING_CHECKS:
        code = _run_check(deps, name, argv, checks)
        if code != 0 and not gating_failed:
            gating_failed = True
            first_fail_name = name

    for name, argv in WARN_CHECKS:
        started = time.monotonic()
        proc = deps.runner(argv, deps.root)
        checks.append(
            {
                "name": name,
                "argv": list(argv),
                "exit": int(proc.returncode),
                "seconds": round(time.monotonic() - started, 3),
                "warn_only": True,
            }
        )

    today = deps.now().date()
    reconcile_block: dict[str, Any] = {
        "generators": gen_steps,
        "checks": checks,
        "moved_paths": sorted(moved),
    }
    surface_err = _reconcile_spec_surface(
        deps,
        moved=moved,
        journal_path=journal_path,
        today=today,
        block=reconcile_block,
    )
    if surface_err is not None:
        return surface_err

    recommended = (
        "estate reconcile: regenerate derived surfaces and reconcile spec-surface\n\n"
        f"Journal: {journal_path.relative_to(deps.root)}"
    )
    reconcile_block["recommended_commit"] = recommended
    journal_doc["reconcile"] = reconcile_block
    if journal_path.is_file():
        journal_path.write_text(json.dumps(journal_doc, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "estate reconcile: generators and checks journaled",
        f"moved paths: {len(moved)}",
        f"recommended commit:\n{recommended}",
    ]
    if gating_failed:
        return DutyResult(
            ok=False,
            summary=f"estate reconcile: check {first_fail_name} failed\n" + "\n".join(summary_lines),
            details={"exit_code": EXIT_RECONCILE_CHECKS, "reconcile": reconcile_block},
        )
    return DutyResult(
        ok=True,
        summary="\n".join(summary_lines),
        details={"reconcile": reconcile_block},
    )
