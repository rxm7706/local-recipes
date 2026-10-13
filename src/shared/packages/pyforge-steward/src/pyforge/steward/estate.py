"""``steward estate`` — policy-driven pin refresh conductor (Story 100.2 / CAP-167).

Four verbs in v1: ``plan``, ``refresh``, ``reconcile``, ``status``. Every mutating step is a
subprocess (AD-1); this module never edits ``pixi.toml`` (AD-5). Returns
``DutyResult`` only (AD-8).
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from .bootstrap import repo_root
from .interfaces import DutyResult

ESTATE_FLAG_KEY = "pyforge.steward.estate_refresh"
EXIT_ESTATE_REFUSAL = 3
JOURNAL_DIR = Path(".steward/estate-refresh")
SCHEMA_RESOURCE = Path(__file__).resolve().parent / "data" / "estate-journal-schema.json"
_DUE_DAYS = 30
_BMAD_CORE = "bmad-method"


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


SubprocessRunner = Callable[[list[str], Path], _Completed]


@dataclass
class EstateDeps:
    """Injectable seams for unit tests (AC6: no live pixi/git/network)."""

    root: Path
    runner: SubprocessRunner
    branch: Callable[[], str | None] = field(default=lambda: None)
    dirty: Callable[[], bool] = field(default=lambda: False)
    head_sha: Callable[[], str] = field(default=lambda: "deadbeef")
    platform: Callable[[], str] = field(default=lambda: "linux-64")
    flag_on: Callable[[], bool] = field(default=lambda: True)
    bmad_latest: Callable[[str], str | None] = field(default=lambda _pkg: None)
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    enforce_require: bool = True


def _default_runner(argv: list[str], cwd: Path) -> _Completed:
    import subprocess

    return subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _git_branch(root: Path) -> str | None:
    import subprocess

    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _git_head(root: Path) -> str:
    import subprocess

    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return "unknown"
    return out.stdout.strip()


def _worktree_dirty(root: Path) -> bool:
    import subprocess

    out = subprocess.run(  # noqa: S603
        [
            "git",
            "-C",
            str(root),
            "-c",
            "status.showUntrackedFiles=normal",
            "status",
            "--porcelain",
            "--ignore-submodules=none",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return True
    return bool((out.stdout or "").strip())


def _flag_enabled() -> bool:
    from pyforge.core.flags import read_boolean

    return read_boolean(ESTATE_FLAG_KEY, default=False)


def _production_deps(root: Path) -> EstateDeps:
    return EstateDeps(
        root=root,
        runner=_default_runner,
        branch=lambda: _git_branch(root),
        dirty=lambda: _worktree_dirty(root),
        head_sha=lambda: _git_head(root),
        platform=lambda: "linux-64",
        flag_on=_flag_enabled,
    )


def _refusal(summary: str) -> DutyResult:
    return DutyResult(
        ok=False,
        summary=summary,
        details={"exit_code": EXIT_ESTATE_REFUSAL},
    )


def _ensure_flag(deps: EstateDeps) -> DutyResult | None:
    """Gate every verb on ``pyforge.steward.estate_refresh`` (``read_boolean`` / ``require`` parity)."""
    from pyforge.core.flags import require

    if not deps.flag_on():
        return _refusal(f"estate: refused — flag {ESTATE_FLAG_KEY} is off")
    if deps.enforce_require:
        require(ESTATE_FLAG_KEY)
    return None


def _policy_path(root: Path) -> Path:
    return root / "docs" / "governance" / "pin-policy.yaml"


def _load_policy(root: Path) -> dict[str, Any]:
    path = _policy_path(root)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def _row_covers_feature(row_features: object, feature: str) -> bool:
    if row_features == "*":
        return True
    if isinstance(row_features, list):
        return feature in row_features or any(feature == f or feature.startswith(f + ".") for f in row_features)
    return False


def _held_by(policy: dict[str, Any], package: str, feature: str) -> str | None:
    holds = policy.get("holds") or []
    rows = [
        h
        for h in holds
        if isinstance(h, dict) and h.get("package") == package and _row_covers_feature(h.get("features"), feature)
    ]
    if not rows:
        return None
    row = rows[0]
    hold = row.get("hold", "")
    authority = row.get("authority", "")
    return f"{hold} ({authority})" if authority else str(hold)


def _render_upgrade_command(deps: EstateDeps) -> tuple[str, list[str]]:
    argv = [sys.executable, "scripts/pin_policy_check.py", "--render-command"]
    proc = deps.runner(argv, deps.root)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "render-command failed").strip())
    command = (proc.stdout or "").strip()
    return command, shlex.split(command)


def _parse_pixi_moves(payload: object) -> list[dict[str, str]]:
    """Normalize pixi upgrade --json (or --dry-run --json) into move rows."""
    moves: list[dict[str, str]] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("packages") or payload.get("updates") or payload.get("moves") or []
    else:
        return moves
    if not isinstance(items, list):
        return moves
    for item in items:
        if not isinstance(item, dict):
            continue
        package = str(item.get("package") or item.get("name") or "")
        feature = str(item.get("feature") or item.get("environment") or item.get("env") or "*")
        from_v = str(item.get("from") or item.get("old") or item.get("before") or "")
        to_v = str(item.get("to") or item.get("new") or item.get("after") or "")
        if package:
            moves.append({"package": package, "feature": feature, "from": from_v, "to": to_v})
    return moves


def _run_pixi_upgrade_json(
    deps: EstateDeps, command_argv: list[str], *, dry_run: bool
) -> tuple[list[dict], _Completed]:
    argv = list(command_argv)
    if dry_run and "--dry-run" not in argv and "upgrade" in argv:
        idx = argv.index("upgrade")
        argv = [*argv[: idx + 1], "--dry-run", *argv[idx + 1 :]]
    if "--json" not in argv:
        argv.append("--json")
    proc = deps.runner(argv, deps.root)
    moves: list[dict] = []
    text = (proc.stdout or "").strip()
    if text:
        try:
            moves = _parse_pixi_moves(json.loads(text))
        except json.JSONDecodeError:
            pass
    return moves, proc


def _journal_dir(root: Path) -> Path:
    return root / JOURNAL_DIR


def _list_journals(root: Path) -> list[Path]:
    directory = _journal_dir(root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.json"))


def _days_since_last_journal(root: Path, *, now: datetime) -> int | None:
    journals = _list_journals(root)
    if not journals:
        return None
    last = journals[-1]
    stem = last.stem  # YYYY-MM-DD or YYYY-MM-DD-2
    day_part = stem.split("-")[:3]
    if len(day_part) < 3:  # noqa: PLR2004
        return None
    try:
        journal_day = date(int(day_part[0]), int(day_part[1]), int(day_part[2]))
    except ValueError:
        return None
    today = now.date()
    return (today - journal_day).days


def _is_due(root: Path, *, now: datetime) -> bool:
    days = _days_since_last_journal(root, now=now)
    return days is None or days > _DUE_DAYS


def _read_manifest_version(manifest_path: Path) -> str | None:
    if not manifest_path.is_file():
        return None
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    inst = data.get("installation")
    if not isinstance(inst, dict):
        return None
    ver = inst.get("version")
    return str(ver) if ver is not None else None


def _bmad_floor_from_pixi(pixi_path: Path, package: str) -> str | None:
    if not pixi_path.is_file():
        return None
    data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    pattern = re.compile(r">=\s*(\d+\.\d+\.\d+)")
    for _table, deps in _walk_dependency_tables(data):
        if not isinstance(deps, dict):
            continue
        spec = deps.get(package)
        if spec is None:
            continue
        spec_str = spec if isinstance(spec, str) else str(spec)
        m = pattern.search(spec_str)
        if m:
            return m.group(1)
    return None


def _walk_dependency_tables(node: object, path: list[str] | None = None):
    path = path or []
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        here = [*path, str(key)]
        if str(key).endswith("dependencies") and isinstance(value, dict):
            yield ".".join(path), value
        elif isinstance(value, dict):
            yield from _walk_dependency_tables(value, here)


def _bmad_package_names(pixi_path: Path) -> list[str]:
    if not pixi_path.is_file():
        return [_BMAD_CORE]
    data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for _table, deps in _walk_dependency_tables(data):
        if not isinstance(deps, dict):
            continue
        for name in deps:
            if isinstance(name, str) and (name == _BMAD_CORE or name.startswith("bmad-")):
                names.add(name)
    names.add(_BMAD_CORE)
    return sorted(names)


def _bmad_table(deps: EstateDeps) -> list[dict[str, str]]:
    root = deps.root
    pixi_path = root / "pixi.toml"
    manifest_path = root / "_bmad" / "_config" / "manifest.yaml"
    installed = _read_manifest_version(manifest_path) or "unknown"
    rows: list[dict[str, str]] = []
    for package in _bmad_package_names(pixi_path):
        pinned = _bmad_floor_from_pixi(pixi_path, package) or "unknown"
        latest_val = deps.bmad_latest(package)
        latest = latest_val if latest_val is not None else "unknown"
        rows.append(
            {
                "package": package,
                "pinned": pinned,
                "installed": installed if package == _BMAD_CORE else pinned,
                "latest": latest,
            }
        )
    return rows


def _format_plan_text(moves: list[dict], bmad: list[dict], days: int | None) -> str:
    lines: list[str] = []
    for move in moves:
        held = move.get("held-by") or ""
        lines.append(f"{move['package']}\t{move['feature']}\t{move['from']}\t{move['to']}\t{held}")
    lines.append("--- bmad ---")
    for row in bmad:
        lines.append(f"{row['package']}\tpinned={row['pinned']}\tinstalled={row['installed']}\tlatest={row['latest']}")
    if days is None:
        lines.append("days since last journal: (none)")
    else:
        lines.append(f"days since last journal: {days}")
    return "\n".join(lines)


def run_plan(deps: EstateDeps, *, json_out: bool, due_only: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    policy = _load_policy(deps.root)
    command, command_argv = _render_upgrade_command(deps)
    raw_moves, _proc = _run_pixi_upgrade_json(deps, command_argv, dry_run=True)
    moves = []
    for move in raw_moves:
        held = _held_by(policy, move["package"], move["feature"])
        moves.append({**move, "held-by": held})
    bmad = _bmad_table(deps)
    days = _days_since_last_journal(deps.root, now=deps.now())
    due = _is_due(deps.root, now=deps.now())
    if due_only:
        if due:
            return DutyResult(ok=False, summary="estate plan --due: refresh is overdue", details={"due": True})
        return DutyResult(ok=True, summary="estate plan --due: within cadence", details={"due": False})
    payload = {
        "kind": "plan",
        "moves": moves,
        "bmad": bmad,
        "days_since_last_journal": days,
        "due": due,
        "command": command,
    }
    if json_out:
        return DutyResult(ok=True, summary=json.dumps(payload, indent=2), details={"plan": payload})
    return DutyResult(ok=True, summary=_format_plan_text(moves, bmad, days), details={"plan": payload})


def _record_step(steps: list[dict], argv: list[str], proc: _Completed, started: float) -> None:
    steps.append(
        {
            "argv": list(argv),
            "exit": int(proc.returncode),
            "seconds": round(time.monotonic() - started, 3),
        }
    )


def _next_journal_path(root: Path, *, today: date) -> Path:
    directory = _journal_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"{today.isoformat()}.json"
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = directory / f"{today.isoformat()}-{suffix}.json"
        if not candidate.exists():
            return candidate
        suffix += 1


def run_refresh(deps: EstateDeps, *, transitive: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    if deps.dirty():
        return _refusal("estate refresh: refused — working tree is dirty")
    branch = deps.branch()
    if branch == "main":
        return _refusal("estate refresh: refused — branch is main")
    steps: list[dict] = []
    base_sha = deps.head_sha()
    command, command_argv = _render_upgrade_command(deps)
    started = time.monotonic()
    moves, upgrade_proc = _run_pixi_upgrade_json(deps, command_argv, dry_run=False)
    _record_step(steps, command_argv + ["--json"], upgrade_proc, started)

    if transitive:
        update_argv = ["pixi", "update"]
        started = time.monotonic()
        update_proc = deps.runner(update_argv, deps.root)
        _record_step(steps, update_argv, update_proc, started)

    diff_argv = [sys.executable, "scripts/pin_policy_check.py", "--diff", base_sha, "--json"]
    started = time.monotonic()
    diff_proc = deps.runner(diff_argv, deps.root)
    _record_step(steps, diff_argv, diff_proc, started)
    losses: list[Any] = []
    if diff_proc.returncode != 0 and (diff_proc.stdout or "").strip():
        try:
            losses = json.loads(diff_proc.stdout)
        except json.JSONDecodeError:
            losses = [{"raw": diff_proc.stdout.strip()}]
        restore_argv = [sys.executable, "scripts/pin_policy_restore.py", "--from", base_sha]
        started = time.monotonic()
        restore_proc = deps.runner(restore_argv, deps.root)
        _record_step(steps, restore_argv, restore_proc, started)
        if restore_proc.returncode != 0:
            return DutyResult(
                ok=False,
                summary=f"estate refresh: pin policy restore refused (exit {restore_proc.returncode})",
                details={"exit_code": EXIT_ESTATE_REFUSAL, "steps": steps},
            )

    lock_argv = ["pixi", "lock"]
    started = time.monotonic()
    lock_proc = deps.runner(lock_argv, deps.root)
    _record_step(steps, lock_argv, lock_proc, started)

    fan_argv = [sys.executable, "scripts/pin_policy_check.py", "--fan-out", "--json"]
    started = time.monotonic()
    fan_proc = deps.runner(fan_argv, deps.root)
    _record_step(steps, fan_argv, fan_proc, started)
    fan_findings: list[Any] = []
    fan_ok = fan_proc.returncode == 0
    if (fan_proc.stdout or "").strip():
        try:
            parsed = json.loads(fan_proc.stdout)
            fan_findings = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            fan_findings = [{"raw": fan_proc.stdout.strip()}]

    pixi_moved = any(m.get("package") == "pixi" for m in moves)
    if pixi_moved:
        bump_argv = [sys.executable, "scripts/bump_pixi_version.py"]
        started = time.monotonic()
        bump_proc = deps.runner(bump_argv, deps.root)
        _record_step(steps, bump_argv, bump_proc, started)

    manifest_path = deps.root / "_bmad" / "_config" / "manifest.yaml"
    pixi_path = deps.root / "pixi.toml"
    bmad_block = {
        "pinned": _bmad_floor_from_pixi(pixi_path, _BMAD_CORE) or "unknown",
        "installed": _read_manifest_version(manifest_path) or "unknown",
        "latest": deps.bmad_latest(_BMAD_CORE) or "unknown",
        "applied": False,
    }
    from .estate_realize import compute_realize_due_for_refresh

    realize_due = compute_realize_due_for_refresh(deps.root, moves)
    journal = {
        "base_sha": base_sha,
        "result_sha": "",
        "platform": deps.platform(),
        "command": command,
        "moves": moves,
        "losses_restored": losses,
        "fan_out": {"ok": fan_ok, "findings": fan_findings},
        "realize_due": realize_due,
        "transitive": transitive,
        "bmad": bmad_block,
        "steps": steps,
        "realize": {},
        "reconcile": {},
        "verify": {},
    }
    today = deps.now().date()
    journal_path = _next_journal_path(deps.root, today=today)
    journal_path.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")

    summary_lines = [f"estate refresh: journal → {journal_path.relative_to(deps.root)}"]
    if realize_due:
        summary_lines.append("realize-due: " + ", ".join(realize_due))
    if not fan_ok:
        summary_lines.append("fan-out: FAIL")
        return DutyResult(
            ok=False,
            summary="\n".join(summary_lines),
            details={"journal_path": str(journal_path), "steps": steps},
        )
    return DutyResult(
        ok=True,
        summary="\n".join(summary_lines),
        details={"journal_path": str(journal_path), "steps": steps},
    )


def _load_journal(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_status(deps: EstateDeps, *, json_out: bool, show_all: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    journals = _list_journals(deps.root)
    if not journals:
        return DutyResult(ok=True, summary="estate status: no journals yet")
    selected = journals if show_all else [journals[-1]]
    due = _is_due(deps.root, now=deps.now())
    lines: list[str] = []
    for path in selected:
        doc = _load_journal(path)
        lines.append(f"=== {path.name} ===")
        lines.append(f"base_sha={doc.get('base_sha')} moves={len(doc.get('moves') or [])}")
        lines.append(f"fan_out.ok={doc.get('fan_out', {}).get('ok')}")
    lines.append(f"due={'yes' if due else 'no'}")
    if json_out:
        payload = {"journals": [_load_journal(p) for p in selected], "due": due}
        return DutyResult(ok=True, summary=json.dumps(payload, indent=2), details=payload)
    return DutyResult(ok=True, summary="\n".join(lines), details={"due": due})


class EstateDuty:
    name = "estate"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        root = repo_root()
        deps = getattr(ns, "_estate_deps", None) or _production_deps(root)
        verb = getattr(ns, "estate_verb", None)
        if verb == "plan":
            return run_plan(deps, json_out=bool(getattr(ns, "json", False)), due_only=bool(getattr(ns, "due", False)))
        if verb == "refresh":
            return run_refresh(deps, transitive=bool(getattr(ns, "transitive", False)))
        if verb == "reconcile":
            from .estate_reconcile import ReconcileDeps, run_reconcile

            rdeps = getattr(ns, "_reconcile_deps", None)
            if rdeps is None:
                rdeps = ReconcileDeps(
                    root=deps.root,
                    runner=deps.runner,
                    branch=deps.branch,
                    dirty=deps.dirty,
                    head_sha=deps.head_sha,
                    platform=deps.platform,
                    flag_on=deps.flag_on,
                    bmad_latest=deps.bmad_latest,
                    now=deps.now,
                    enforce_require=deps.enforce_require,
                )
            journal_path = getattr(ns, "journal_path", None)
            return run_reconcile(rdeps, journal_path=journal_path)
        if verb == "status":
            return run_status(
                deps,
                json_out=bool(getattr(ns, "json", False)),
                show_all=bool(getattr(ns, "all", False)),
            )
        if verb == "realize":
            from .estate_realize import RealizeDeps, production_realize_deps, run_realize

            rdeps = getattr(ns, "_realize_deps", None)
            if rdeps is None:
                rdeps = production_realize_deps(root)
            journal_arg = getattr(ns, "journal", None)
            return run_realize(
                rdeps,
                plan=bool(getattr(ns, "plan", False)),
                yes=bool(getattr(ns, "yes", False)),
                all_rows=bool(getattr(ns, "all", False)),
                journal_path=Path(journal_arg) if journal_arg else None,
            )
        return DutyResult(ok=False, summary="estate: need plan, refresh, reconcile, realize, or status")
