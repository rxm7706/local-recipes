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
    # the docs generators restamp the map entry of each page they write
    "docs/map.yaml",
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


def _parse_bmad_suite_report(stdout: str | None) -> dict[str, Any] | None:
    if not stdout or not stdout.strip():
        return None
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("members"), list):
        return None
    return data


def _bmad_suite_floor_summary(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for row in report.get("members") or []:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        floor_before = row.get("floor_before")
        floor = row.get("floor")
        source = row.get("source")
        if name is None or floor is None:
            continue
        if floor_before != floor:
            lines.append(f"{name} {floor_before} -> {floor} [{source}]")
    return lines


def _build_generators(
    journal: dict[str, Any], root: Path, *, journal_path: Path | None = None
) -> list[tuple[str, list[str], str | None]]:
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
        argv = [py, ".claude/scripts/conda-forge-expert/bmad_suite_metapackage.py"]
        if journal_path is not None:
            argv.extend(["--journal", str(journal_path)])
        argv.append("--json")
        gens.append(("generate-bmad-suite", argv, None))
    return gens


def _guild_python(*args: str) -> list[str]:
    """Checks are Guild tasks: the steward env carries no ``pyforge.doctor``, so they run in pyforge-guild."""
    return ["pixi", "run", "--as-is", "-x", "-e", "pyforge-guild", "python", *args]


GATING_CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("llms-full-check", _guild_python("scripts/llms_full_check.py")),
    ("bmad-estate-check", _guild_python("scripts/bmad_estate_check.py")),
    ("pixi-version-check", _guild_python("scripts/pixi_version_check.py")),
    ("target-version-check", _guild_python("scripts/target_version_check.py")),
    ("sbom-gaps-check", _guild_python("scripts/sbom_gap_derive.py")),
    ("platform-policy-suite-check", _guild_python("-m", "pyforge.doctor.sources", "platform-policy-suite")),
    ("pin-policy-check", _guild_python("scripts/pin_policy_check.py", "--check")),
    ("pixi-lock-check", ["pixi", "lock", "--check"]),
)

WARN_CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("pixi-currency-staleness-check", _guild_python("-m", "pyforge.doctor.sources", "pixi-currency-ledger")),
    (
        "steward-deck-drift",
        _guild_python("-m", "pyforge.steward.cli", "deck-drift", "--slug", "pyforge-steward", "--path", "deck.dc.html"),
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


@dataclass(frozen=True)
class ReconcileSeams:
    memlog_append: Callable[[Path, str], int]
    git_add: Callable[[Path, list[str]], int]
    stamp_spec: Callable[[Path, str], int]


def production_reconcile_seams(runner: Callable[[list[str], Path], Any]) -> ReconcileSeams:
    """The memlog, git-add and stamp seams the CLI duty runs; the dataclass defaults are no-ops."""

    def memlog_append(memlog_path: Path, text: str) -> int:
        argv = [
            sys.executable,
            "_bmad/scripts/memlog.py",
            "append",
            "--path",
            str(memlog_path),
            "--type",
            "event",
            "--text",
            text,
        ]
        return int(runner(argv, _repo_of(memlog_path)).returncode)

    def git_add(root: Path, paths: list[str]) -> int:
        return int(runner(["git", "add", "--", *paths], root).returncode)

    def stamp_spec(root: Path, spec_name: str) -> int:
        argv = [sys.executable, "scripts/spec_surface_check.py", "--write-baseline", "--spec", spec_name]
        return int(runner(argv, root).returncode)

    return ReconcileSeams(memlog_append=memlog_append, git_add=git_add, stamp_spec=stamp_spec)


def _repo_of(memlog_path: Path) -> Path:
    """The repo root above ``_bmad-output/projects/<p>/planning-artifacts/specs/<s>/.memlog.md``."""
    for parent in memlog_path.parents:
        if parent.name == "_bmad-output":
            return parent.parent
    return memlog_path.parent


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

    surface_argv = _guild_python("-m", "pyforge.doctor.sources", "spec-surface")
    started = time.monotonic()
    surface_proc = deps.runner(surface_argv, deps.root)
    block["spec_surface"] = {
        "specs": sorted(by_spec),
        "memlogs": memlog_events,
        "stamps": stamps,
        "spec_surface_check": {
            "argv": surface_argv,
            "exit": int(surface_proc.returncode),
            "seconds": round(time.monotonic() - started, 3),
        },
    }
    if surface_proc.returncode != 0:
        return _refusal(
            f"estate reconcile: spec-surface-check failed after scoped stamps (exit {surface_proc.returncode})"
        )
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
    bmad_floor_lines: list[str] = []
    generator_failed = False
    for label, argv, output_rel in _build_generators(journal_doc, deps.root, journal_path=journal_path):
        if label == "generate-bmad-suite":
            started = time.monotonic()
            proc = deps.runner(argv, deps.root)
            step: dict[str, Any] = {
                "label": label,
                "argv": list(argv),
                "exit": int(proc.returncode),
                "seconds": round(time.monotonic() - started, 3),
            }
            if proc.returncode != 0:
                step["error"] = "non-zero exit"
                generator_failed = True
            else:
                parsed = _parse_bmad_suite_report(proc.stdout)
                if parsed is None:
                    step["error"] = "stdout is not a JSON report with members"
                    generator_failed = True
                else:
                    bmad_floor_lines = _bmad_suite_floor_summary(parsed)
                    step["bmad_suite"] = parsed
            gen_steps.append(step)
        else:
            code = _run_generator(deps, argv, output_rel, gen_steps)
            if code != 0 and "bmad-estate" in " ".join(argv):
                # scribe non-zero: continue remaining checks per spec I/O matrix
                pass

    if generator_failed:
        reconcile_block: dict[str, Any] = {
            "generators": gen_steps,
            "checks": [],
            "moved_paths": sorted(_moved_paths(before, _fingerprints(deps.root, WATCH_PATHS))),
        }
        journal_doc["reconcile"] = reconcile_block
        if journal_path.is_file() or journal_path.parent.exists():
            journal_path.parent.mkdir(parents=True, exist_ok=True)
            journal_path.write_text(json.dumps(journal_doc, indent=2) + "\n", encoding="utf-8")
        fail_step = next((s for s in gen_steps if s.get("label") == "generate-bmad-suite"), {})
        reason = fail_step.get("error") or "unknown"
        return DutyResult(
            ok=False,
            summary=f"estate reconcile: generate-bmad-suite failed ({reason})",
            details={"exit_code": EXIT_RECONCILE_CHECKS, "reconcile": reconcile_block},
        )

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
    reconcile_block = {
        "generators": gen_steps,
        "checks": checks,
        "moved_paths": sorted(moved),
    }
    bmad_step = next((s for s in gen_steps if s.get("label") == "generate-bmad-suite"), None)
    if bmad_step and isinstance(bmad_step.get("bmad_suite"), dict):
        reconcile_block["bmad_suite"] = bmad_step["bmad_suite"]
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
    ]
    summary_lines.extend(bmad_floor_lines)
    summary_lines.append(f"recommended commit:\n{recommended}")
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
