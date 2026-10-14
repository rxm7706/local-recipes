"""``steward estate realize`` — re-apply side-effect installs after pin moves (Story 100.5)."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from .estate import (
    EstateDeps,
    SubprocessRunner,
    _ensure_flag,
    _list_journals,
    _load_journal,
    _production_deps,
)
from .interfaces import DutyResult

REGISTER_REL = Path("docs/governance/realization-register.yaml")


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


@dataclass
class RealizeDeps:
    root: Path
    runner: SubprocessRunner
    flag_on: Callable[[], bool] = field(default=lambda: True)
    enforce_require: bool = True
    loop_homes: Callable[[], list[Path]] = field(default=list)
    platform: Callable[[], str] = field(default=lambda: "linux-64")


def _load_register(root: Path) -> dict[str, Any]:
    path = root / REGISTER_REL
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def _rows_by_package(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = data.get("rows") or []
    return {str(r["package"]): r for r in rows if isinstance(r, dict) and r.get("package")}


def packages_moved_in_journal(journal: dict[str, Any]) -> set[str]:
    moved: set[str] = set()
    for move in journal.get("moves") or []:
        if isinstance(move, dict) and move.get("package"):
            frm = str(move.get("from") or "")
            to = str(move.get("to") or "")
            if frm != to:
                moved.add(str(move["package"]))
    return moved


def realize_due_packages(journal: dict[str, Any], register: dict[str, Any], *, all_rows: bool) -> list[str]:
    by_pkg = _rows_by_package(register)
    if all_rows:
        return sorted(by_pkg)
    moved = packages_moved_in_journal(journal)
    return sorted(pkg for pkg in moved if pkg in by_pkg)


def _locked_version(root: Path, env: str, package: str, platform: str) -> str | None:
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from pin_policy_lib import locked_version_in_env  # noqa: PLC0415

    lock_path = root / "pixi.lock"
    if not lock_path.is_file():
        return None
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    ver = locked_version_in_env(lock, env, package, platform=platform)
    return str(ver) if ver is not None else None


def _yaml_dotted_get(doc: dict[str, Any], dotted: str) -> str | None:
    cur: object = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return str(cur) if cur is not None else None


def _probe_locked_version_file(root: Path, probe: dict[str, Any], env: str, platform: str, *, package: str) -> str:
    rel = str(probe.get("path") or "")
    key = str(probe.get("key") or "")
    path = root / rel
    if not path.is_file():
        return "missing"
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        return "missing"
    installed = _yaml_dotted_get(doc, key) if key else None
    if installed is None:
        return "missing"
    locked = _locked_version(root, env, package, platform)
    if locked is None:
        return "missing"
    return "live" if str(installed) == str(locked) else "stale"


def _in_env(env: str, argv: list[Any]) -> list[str]:
    """Run a register argv inside the row's pixi env.

    Register steps and probes name bare tools (``osv-scanner``, ``pre-commit``); each row's
    ``env`` says where they live, and the calling env (pyforge-steward) carries only some.
    """
    return ["pixi", "run", "--frozen", "-e", env, *(str(part) for part in argv)]


def _probe_locked_version_command(deps: RealizeDeps, probe: dict[str, Any], env: str, package: str) -> str:
    cmd = probe.get("command")
    if isinstance(cmd, str):
        cmd = shlex_split(cmd)
    if not isinstance(cmd, list) or not cmd:
        return "missing"
    argv = _in_env(env, cmd)
    try:
        proc = deps.runner(argv, deps.root)
    except OSError:
        return "missing"
    if proc.returncode != 0:
        return "missing"
    out = (proc.stdout or proc.stderr or "").strip()
    locked = _locked_version(deps.root, env, package, deps.platform())
    if locked is None:
        return "missing"
    if locked in out or out.endswith(locked):
        return "live"
    # semver loose: first token on last line
    m = re.search(r"(\d+\.\d+\.\d+(?:\.\d+)?)", out)
    if m and m.group(1) == ".".join(locked.split(".")[0:3]):
        return "live"
    if m and locked.startswith(m.group(1).rsplit(".", 1)[0]):
        return "live"
    if m and m.group(1) in locked:
        return "live"
    return "stale" if out else "missing"


def shlex_split(text: str) -> list[str]:
    import shlex

    return shlex.split(text)


def _parse_seed_kit(stdout: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return []
    kit = result.get("kit")
    return kit if isinstance(kit, list) else []


def _probe_kit_ok(deps: RealizeDeps, probe: dict[str, Any]) -> str:
    argv = ["pyforge", "marshal", "seed", "check", "--json"]
    proc = deps.runner(argv, deps.root)
    kit = _parse_seed_kit(proc.stdout or "")
    if not kit:
        return "missing"
    item_id = str(probe.get("item") or "")
    for entry in kit:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("item")) != item_id:
            continue
        status = str(entry.get("status") or "")
        if status in ("ok", "layer-off"):
            return "live"
        if status == "missing":
            return "missing"
        return "stale"
    return "missing"


def _probe_stage_ok(deps: RealizeDeps, probe: dict[str, Any]) -> str:
    argv = ["pyforge", "steward", "suite", "pipeline-truth", "--json"]
    proc = deps.runner(argv, deps.root)
    if proc.returncode != 0 and not (proc.stdout or "").strip():
        return "missing"
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return "missing"
    packages = data.get("packages", data)
    member = str(probe.get("member") or "")
    stages = probe.get("stages") or ["installed", "wired"]
    for pkg in packages if isinstance(packages, list) else []:
        if not isinstance(pkg, dict) or str(pkg.get("name")) != member:
            continue
        for stage in stages:
            cell = pkg.get(stage)
            if isinstance(cell, dict):
                val = str(cell.get("value") or "").lower()
                if val not in ("ok", "green", "true", "wired", "installed"):
                    return "stale"
            elif cell is False:
                return "stale"
        return "live"
    return "missing"


def _probe_exit_0(deps: RealizeDeps, probe: dict[str, Any]) -> str:
    cmd = probe.get("command")
    if isinstance(cmd, str):
        cmd = shlex_split(cmd)
    if not isinstance(cmd, list):
        return "missing"
    argv = [sys.executable, *cmd[1:]] if cmd and cmd[0] == "python" else list(cmd)
    proc = deps.runner(argv, deps.root)
    return "live" if proc.returncode == 0 else "stale"


def _probe_import(deps: RealizeDeps, probe: dict[str, Any]) -> str:
    cmd = str(probe.get("command") or "")
    if not cmd:
        return "missing"
    proc = deps.runner([sys.executable, "-c", cmd], deps.root)
    return "live" if proc.returncode == 0 else "missing"


def run_probe(deps: RealizeDeps, row: dict[str, Any], *, package: str) -> str:
    probe = row.get("probe") or {}
    expect = str(probe.get("expect") or "")
    env = str(row.get("env") or "pyforge-guild")
    if expect == "locked-version":
        if probe.get("path"):
            return _probe_locked_version_file(deps.root, probe, env, deps.platform(), package=package)
        return _probe_locked_version_command(deps, probe, env, package)
    if expect == "kit-ok":
        return _probe_kit_ok(deps, probe)
    if expect == "stage-ok":
        return _probe_stage_ok(deps, probe)
    if expect == "exit-0":
        return _probe_exit_0(deps, probe)
    if expect == "import-probe":
        return _probe_import(deps, probe)
    return "missing"


def _realize_steps_for_row(deps: RealizeDeps, row: dict[str, Any]) -> list[list[str]]:
    realize = row.get("realize") or {}
    steps = list(realize.get("steps") or [])
    if realize.get("per_loop_home"):
        out: list[list[str]] = []
        for home in deps.loop_homes():
            slug = home.name
            out.append(["pyforge", "marshal", "refresh", "--project", slug])
        out.append([sys.executable, "scripts/pin_policy_check.py", "--fan-out", "--json"])
        return out
    return [list(s) for s in steps if s]


def _run_bmad_preflight(deps: RealizeDeps) -> dict[str, Any]:
    block: dict[str, Any] = {}
    pre = deps.runner(["pyforge", "steward", "upgrade", "bmad-core"], deps.root)
    block["preflight_exit"] = pre.returncode
    fan = deps.runner([sys.executable, "scripts/pin_policy_check.py", "--fan-out", "--json"], deps.root)
    block["fan_out_exit"] = fan.returncode
    if (fan.stdout or "").strip():
        try:
            block["fan_out"] = json.loads(fan.stdout)
        except json.JSONDecodeError:
            block["fan_out_raw"] = fan.stdout.strip()
    return block


def run_realize(
    deps: RealizeDeps,
    *,
    plan: bool,
    yes: bool,
    all_rows: bool,
    journal_path: Path | None,
) -> DutyResult:
    estate = EstateDeps(
        root=deps.root,
        runner=deps.runner,
        flag_on=deps.flag_on,
        enforce_require=deps.enforce_require,
        platform=deps.platform,
    )
    refused = _ensure_flag(estate)
    if refused is not None:
        return refused

    register = _load_register(deps.root)
    if journal_path is None:
        journals = _list_journals(deps.root)
        journal_path = journals[-1] if journals else None
    journal: dict[str, Any] = _load_journal(journal_path) if journal_path and journal_path.is_file() else {"moves": []}

    due = realize_due_packages(journal, register, all_rows=all_rows)
    by_pkg = _rows_by_package(register)
    lines: list[str] = []
    entries: dict[str, Any] = {}
    bmad_block: dict[str, Any] | None = None

    if plan:
        for pkg in due:
            lines.append(pkg)
        return DutyResult(
            ok=True,
            summary="\n".join(lines) if lines else "estate realize --plan: nothing due",
            details={"due": due, "plan": True},
        )

    for pkg in due:
        row = by_pkg[pkg]
        realize_state = "none"
        steps = _realize_steps_for_row(deps, row)
        operator_gate = bool((row.get("realize") or {}).get("operator_gate"))
        if not steps:
            realize_state = "none"
        elif operator_gate and not yes:
            realize_state = "skipped-operator-gate"
        else:
            realize_state = "ran"
            env = str(row.get("env") or "pyforge-guild")
            for argv in steps:
                try:
                    proc = deps.runner(_in_env(env, argv), deps.root)
                except OSError:
                    realize_state = "failed"
                    break
                if proc.returncode != 0:
                    realize_state = "failed"
                    break

        probe_state = run_probe(deps, row, package=pkg)
        from_v = ""
        to_v = ""
        for move in journal.get("moves") or []:
            if isinstance(move, dict) and move.get("package") == pkg:
                from_v = str(move.get("from") or "")
                to_v = str(move.get("to") or "")
        entries[pkg] = {
            "package": pkg,
            "from": from_v,
            "to": to_v,
            "platform": deps.platform(),
            "realize": realize_state,
            "probe": probe_state,
        }

        if pkg == "bmad-method" and (pkg in packages_moved_in_journal(journal) or all_rows):
            bmad_block = _run_bmad_preflight(deps)
        if row.get("class") == "module" and probe_state == "stale":
            entries[pkg]["suite_advance"] = "operator: steward suite advance"

    if journal_path and journal_path.is_file():
        doc = _load_journal(journal_path)
        doc["realize"] = entries
        if bmad_block is not None:
            doc.setdefault("bmad", {})
            if isinstance(doc["bmad"], dict):
                doc["bmad"]["realize_preflight"] = bmad_block
        journal_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    summary = f"estate realize: {len(due)} row(s)"
    return DutyResult(ok=True, summary=summary, details={"due": due, "realize": entries})


def compute_realize_due_for_refresh(root: Path, moves: list[dict[str, Any]]) -> list[str]:
    try:
        register = _load_register(root)
    except OSError, ValueError, yaml.YAMLError, FileNotFoundError:
        return []
    journal = {"moves": moves}
    return realize_due_packages(journal, register, all_rows=False)


def default_loop_homes() -> list[Path]:
    from .upgrade import _list_loop_homes  # noqa: PLC0415

    home_root = Path.home() / ".bmad-loops"
    return _list_loop_homes(home_root)


def production_realize_deps(root: Path) -> RealizeDeps:
    base = _production_deps(root)
    return RealizeDeps(
        root=root,
        runner=base.runner,
        flag_on=base.flag_on,
        enforce_require=base.enforce_require,
        loop_homes=default_loop_homes,
        platform=base.platform,
    )
