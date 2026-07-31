#!/usr/bin/env python3
"""The detector registry — derived from the filesystem, never hand-listed.

WHY THIS EXISTS. On 2026-07-31 this repo had **three** registries of its own
detectors and no two agreed:

    8 scripts on disk · 7 pixi tasks · 3 rows on the dashboard · 0 in CI

`dream_chain_check` — the newest — was missing from two of the three, and
`check_layout` from all of them. That is the shape a hand-written list always
takes: it omits exactly the newest thing, because adding a detector and
remembering every place that names it are separate acts and only the first is
forced. `docs/dashboard/generate.py` already derives a task's *command* from
`pixi.toml` "DERIVED, never declared twice" — but the list of detectors above it
was typed by hand, and that was the bug.

So: discover detectors by scanning, and **fail on the registry's own gaps**. A
script that declares itself a detector but has no pixi task is a finding; a
script that looks like a detector but declares nothing is a finding. The
registry cannot silently omit a detector, which is the only property that makes
it worth having.

SCOPE, declared by each detector rather than inferred here:

    DETECTOR = {"scope": "repo"}      reads tracked files only — runs anywhere
    DETECTOR = {"scope": "runtime"}   reads host state (Tier-3 sprint feeds,
                                      tmux, ~/.bmad-loops) — cannot run in CI

The split is not an inconvenience to route around. It is the factory's missing
observation plane showing up as a deployment constraint: the runtime detectors
are precisely the ones with nowhere to run, which is the gap
docs/dreams/fidelity-enforcement.md exists to close.

EXIT CODES, and the rule that governs them:

    0   every selected detector ran and passed
    1   at least one reported findings
    2   at least one COULD NOT RUN, and none reported findings

2 is not a softer 0. A detector that cannot run reports **unknown, never green**
(fidelity-enforcement, invariant 3) — the dashboard's status strip has behaved
this way since it was built ("the strip never claims green it did not measure"),
and this promotes it to a rule binding every consumer of the registry.

Declarations are read with `ast`, never by importing: a detector's module body
may open files, spawn a browser, or shell out, and discovery must be free of
side effects.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Where detectors may live, and what they are named. Two roots because the
# dashboard's layout gate belongs beside the page it measures, not in scripts/.
SEARCH = (
    (ROOT / "scripts", "*_check.py"),
    (ROOT / "docs" / "dashboard", "check_*.py"),
)

SCOPES = ("repo", "runtime")


def _declared_scope(path: pathlib.Path) -> str | None:
    """Read `DETECTOR = {...}` from a module without importing it."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "DETECTOR" for t in node.targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except ValueError:
            return None
        if isinstance(value, dict):
            scope = value.get("scope")
            return scope if scope in SCOPES else None
    return None


def _pixi_tasks() -> dict[str, str]:
    try:
        import tomllib
    except ModuleNotFoundError:                      # pragma: no cover
        import tomli as tomllib                      # type: ignore
    cfg = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for feat in cfg.get("feature", {}).values():
        for name, spec in (feat.get("tasks") or {}).items():
            cmd = spec.get("cmd") if isinstance(spec, dict) else spec
            if isinstance(cmd, str):
                out[name] = cmd
    return out


def discover() -> tuple[list[dict], list[str]]:
    """Return (detectors, registry_findings). Findings are gaps in the registry itself."""
    tasks = _pixi_tasks()
    detectors: list[dict] = []
    findings: list[str] = []

    for directory, pattern in SEARCH:
        for path in sorted(directory.glob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            scope = _declared_scope(path)
            if scope is None:
                findings.append(
                    f"{rel}: looks like a detector but declares no valid "
                    f'DETECTOR = {{"scope": "repo"|"runtime"}} — it would be invisible '
                    f"to CI, the board and the loop")
                continue
            task = next((t for t, c in tasks.items()
                         if path.name in c and "--json" not in c), None)
            if task is None:
                findings.append(
                    f"{rel}: declares scope={scope} but has no pixi task — "
                    f"nothing can invoke it by name")
            detectors.append({"path": rel, "name": path.stem, "scope": scope, "task": task})
    return detectors, findings


def run_one(det: dict, timeout: int) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / det["path"])],
            cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        rc, out = 2, f"UNKNOWN: exceeded {timeout}s"
    status = {0: "pass", 1: "FINDINGS"}.get(rc, "unknown")
    tail = [ln for ln in out.strip().splitlines() if ln.strip()]
    return {**det, "rc": rc, "status": status,
            "secs": round(time.monotonic() - started, 1),
            "summary": tail[-1][:200] if tail else "", "output": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scope", choices=(*SCOPES, "all"), default="all",
                    help="repo = CI-safe subset; runtime = host-state detectors")
    ap.add_argument("--list", action="store_true", help="show the registry and exit")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    detectors, registry_findings = discover()
    selected = [d for d in detectors if args.scope in ("all", d["scope"])]

    if args.list:
        if args.json:
            print(json.dumps({"detectors": detectors, "registry": registry_findings}, indent=1))
        else:
            for d in detectors:
                print(f"  {d['scope']:7} {d['name']:22} task={d['task'] or '(NONE)'}")
            for f in registry_findings:
                print(f"  ✗ registry: {f}")
        return 1 if registry_findings else 0

    results = [run_one(d, args.timeout) for d in selected]

    if args.json:
        for r in results:
            r.pop("output", None)
        print(json.dumps({"registry": registry_findings, "results": results}, indent=1))
    else:
        print(f"detectors — scope={args.scope}, {len(selected)} selected\n")
        for r in results:
            mark = {"pass": "✔", "FINDINGS": "✗", "unknown": "?"}[r["status"]]
            print(f"  {mark} {r['name']:22} {r['status']:9} {r['secs']:5.1f}s  {r['summary']}")
        for f in registry_findings:
            print(f"\n  ✗ registry: {f}")
        bad = [r for r in results if r["status"] == "FINDINGS"]
        if bad:
            print("\n" + "=" * 72)
            for r in bad:
                print(f"\n--- {r['name']} ({r['path']}) ---\n{r['output'].rstrip()}")

    # Registry gaps are findings in their own right: a detector nothing can
    # invoke is the same defect class as a rule nothing enforces.
    if registry_findings or any(r["status"] == "FINDINGS" for r in results):
        return 1
    if any(r["status"] == "unknown" for r in results):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
