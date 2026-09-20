#!/usr/bin/env python3
"""The detector registry — derived from the filesystem, never hand-listed.

WHY THIS EXISTS. On 2026-07-31 this repo had **three** registries of its own
detectors and no two agreed:

    8 scripts on disk · 7 pixi tasks · 3 rows on the dashboard · 0 in CI

`dream_chain_check` — the newest — was missing from two of the three, and
`check_layout` from all of them. That is the shape a hand-written list always
takes: it omits exactly the newest thing, because adding a detector and
remembering every place that names it are separate acts and only the first is
forced. `pyforge.doctor.sources.fleet_scan` already derives a task's *command* from
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

DOCTOR-PORTED SOURCES (Story 6.9). Ten detectors that used to be
`scripts/*_check.py` files (`--list` still shows a diagnostic
`_doctor_sources()` catalog of every `sources.REGISTRY` entry) are now
`pyforge.doctor.sources` library gathers with no file left to AST-scan --
`discover()` above is permanently blind to them. `main()`'s real run path
threads them in separately (`_run_doctor_sources`), in-process, merged into
the SAME `results` list and the SAME exit-code aggregation a scanned
detector's row feeds. `pyforge.doctor` unimportable in the active
environment is no longer an "expected, uncounted absence" the way it was
while the origin scripts still existed as a fallback -- it is now the ONLY
source of truth for those ten, so it degrades to ten **unknown, never
green** rows here too, exactly like a detector `discover()` cannot run.
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

# Sentinel for `_declared_scope`: a file matches the `*_check.py`/`check_*.py`
# glob but explicitly opts out via `DETECTOR = None` -- a residual mutation-only
# script (Story 6.9 reduced `spec_surface_check.py`/`bmad_drift_check.py` this
# way) that keeps its historical name for doc/CLI continuity but was never a
# detector and should not trip the "looks like one but declares nothing"
# registry gap below.
_NOT_A_DETECTOR = object()


def _declared_scope(path: pathlib.Path) -> str | None | object:
    """Read `DETECTOR = {...}` from a module without importing it.

    Returns a scope string, `None` (no/invalid `DETECTOR` -- a registry gap),
    or `_NOT_A_DETECTOR` (`DETECTOR = None` -- an explicit, intentional opt-out).
    """
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
        if value is None:
            return _NOT_A_DETECTOR
        if isinstance(value, dict):
            scope = value.get("scope")
            return scope if scope in SCOPES else None
        return None
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
            if scope is _NOT_A_DETECTOR:
                continue
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


def _doctor_sources() -> tuple[bool, list[dict]]:
    """Doctor-owned sources, declared not scanned -- feeds `--list` ONLY.

    A source can live inside `pyforge.doctor`'s own package (e.g.
    `marshal-durability`) with no `scripts/*_check.py` file to AST-scan --
    `discover()` above is blind to it by construction. This reads Doctor's
    own `sources.REGISTRY` (Story 6.2) directly instead of scanning for it.

    Returns `(available, rows)`. `available` is False -- and `rows` is `[]`
    -- when `pyforge.doctor` isn't importable in the active environment
    (Doctor is a dedicated lean package, not installed in every environment
    that runs this script). That is DELIBERATELY not the same discipline as
    `discover()`'s "unknown, never green" handling of a detector it cannot
    run: a Doctor-owned source's absence here is a normal, expected outcome,
    not a detector failing to execute, so it is never a registry finding and
    never a crash -- but the caller still needs `available` to tell "the
    package is here and reports zero" apart from "the package isn't here."

    Story 6.9: this relaxed discipline stays correct for THIS function
    because `--list` is a diagnostic catalog view, never a verdict -- but it
    is no longer the whole story. `_run_doctor_sources` below is the real
    run path's OWN, separate helper, and it deliberately does NOT relax:
    post-retirement, the ten `scripts/*_check.py` origins are gone, so an
    unimportable `pyforge.doctor` there means ten verdicts have no source of
    truth at all, and that MUST read as "unknown," exactly like a scanned
    detector `discover()` cannot run -- never a silently empty registry.
    """
    try:
        from pyforge.doctor.sources import list_sources
    except ImportError:
        return False, []
    return True, [reg.to_json_dict() for reg in list_sources()]


# Story 6.9: the ten retiring `scripts/*_check.py` (+ `docs/dashboard/
# check_layout.py`) origins, each now a `pyforge.doctor.sources.__main__.
# DISPATCH` entry -- paired here with the pixi task name that invokes it, so
# a result row looks like a scanned detector's own `{"task": ...}` field.
# The dispatch mapping itself is NOT re-declared here (imported from
# `DISPATCH` at call time below) -- only the pixi-task-name pairing, which
# has no other home, is.
_DOCTOR_SOURCE_TASKS: tuple[tuple[str, str], ...] = (
    ("ledger-regression", "ledger-regression-check"),
    # Wired 2026-09-08, after the false-positive class that kept it out was
    # fixed. Judged on merge subjects alone it reported 383 done-but-unmerged
    # findings -- 53% of every done story in the fleet -- because batched
    # `chore/`/`docs/`/`dispatch/` PRs name no story in their merge subject.
    # `_base_done_ids` now consults the ledger as committed at the base ref;
    # the live count is 0 and the FAIL half (landed-but-unpromoted) is what
    # actually gates. Offline and deterministic, like its neighbours here.
    ("ledger-direction", "ledger-direction-check"),
    ("story-status", "story-status-check"),
    # Story 21.11 (Epic 21): capability-effect beside story-status in one
    # detectors run -- offline, deterministic, no budget concerns.
    ("capability-effect", "capability-effect-check"),
    # Story 21.16 (Epic 21): status-body-consistency beside capability-effect
    # in one detectors run -- offline, deterministic, no budget concerns.
    ("status-body-consistency", "status-body-consistency-check"),
    ("chain-completeness", "chain-completeness-check"),
    ("dashboard-drift", "retired-console-check"),
    ("check-layout", "dashboard-layout-check"),
    ("dream-chain", "dream-chain-check"),
    ("spec-surface", "spec-surface-check"),
    ("deferred-work", "deferred-work-check"),
    ("forward-dependency", "forward-dependency-check"),
    ("bmad-drift", "bmad-drift-check"),
    # Retro action item 3 (retro-pyforge-steward-2026-09-04.md, 2026-09-05):
    # genuinely NEW (not a retiring scripts/*_check.py origin), added here
    # like the original ten -- offline, deterministic, no budget concerns
    # (unlike bmad-method-version-drift/sibling-dreams-drift/due-for-
    # verification, which stay opt-in-only and are deliberately absent from
    # this tuple).
    ("platform-policy-suite", "platform-policy-suite-check"),
    # Story 20.2 (Epic 20): another genuinely NEW (not a retiring
    # scripts/*_check.py origin) entry, added here like platform-policy-suite
    # above -- offline, deterministic, no budget concerns (unlike
    # bmad-method-version-drift/sibling-dreams-drift/due-for-verification,
    # which stay opt-in-only and are deliberately absent from this tuple).
    ("bmad-render-config-ambiguity", "bmad-render-config-ambiguity-check"),
    # Story 20.3 (Epic 20): another genuinely NEW (not a retiring
    # scripts/*_check.py origin) entry, added here like bmad-render-config-
    # ambiguity above -- offline, deterministic, no budget concerns.
    ("frozen-path-changed", "frozen-path-changed-check"),
    # Story 21.7 (Epic 21 / spec-pixi-candidate-currency CAP-4): pixi-currency
    # ledger staleness beside the other repo-scope doctor sources.
    ("pixi-currency-ledger", "pixi-currency-staleness-check"),
    # Story 22.3 (Epic 22 / spec-general-docs-consistency CAP-3): human-facing
    # documentation identity contradictions beside the other repo-scope sources.
    ("general-docs-consistency", "general-docs-consistency-check"),
    # Story 55.2 (fcl:CAP-2): CAP extract vs capability-ledger.yaml.
    ("capability-ledger", "capability-ledger-check"),
    # Doctor Epic 25 (spec-one-chain-per-station CAP-2 / CAP-5, guild outcome
    # / doctor mechanism): the sprawl gate and the FR<-CAP check. Both
    # offline, deterministic, baselined from a dated snapshot so a folded and
    # an unfolded station both pass (eventual consistency).
    ("chain-sprawl", "chain-sprawl-check"),
    ("fr-without-cap", "fr-without-cap-check"),
    # Story 30.1 (spec-pyforge-doctor CAP-83): docs/MAP.md vs the four
    # Diátaxis quadrants -- missing link FAIL, unmapped page WARN.
    ("docs-map-hygiene", "docs-map-hygiene-check"),
    # Story 23.7 (Epic 23 / spec-pyforge-doctor CAP-54): leftover-shelf
    # occupancy vs the docs/MAP.md allow-list, beside its sibling repo-scope
    # sources -- offline, deterministic, no budget concerns.
    ("docs-shelf-occupancy", "docs-shelf-occupancy-check"),
    # Story 26.1 (spec-pyforge-doctor CAP-77): a touched surface catalogued
    # in live-proof-surfaces.md gets an advisory finding naming it -- reads
    # only the tracked catalog + a git diff, offline, deterministic.
    ("live-proof-surface", "live-proof-surface-check"),
    # Story 30.2 (spec-pyforge-doctor CAP-84): docs/map.yaml vs its render
    # (docs/MAP.md), authored-page staleness, skill-dir hygiene -- offline,
    # deterministic, beside docs-map-hygiene above.
    ("docs-currency", "docs-currency-check"),
)


def _run_doctor_sources(scope: str) -> list[dict]:
    """Run the ten ported Doctor sources for real -- the counterpart to
    `run_one` above, but in-process (a library `gather(target)` call, never
    a subprocess: there is no script left to shell out to) rather than
    AST-discovered-then-subprocess-run.

    `pyforge.doctor` unimportable -> synthesize ten `status="unknown"` rows,
    never silently return `[]`. Once the origin scripts retire, this is the
    ONLY place these ten verdicts are measured -- `discover()` above no
    longer finds them (their files are gone), so a `main()` that skipped
    this branch on ImportError would discover zero detectors here and
    return exit 0, the exact "false green from standing somewhere the
    failure cannot occur" this package's own `unpushed_work_check.py`
    docstring warns about. `unknown` participates in `main()`'s existing
    `1` (findings) / `2` (unknown) exit aggregation unchanged -- it is
    merged into the same `results` list a scanned detector's row lands in.

    A per-source gather that raises escaping `degrade_on_exception`'s own
    net (a defect in Doctor itself, not a "cannot evaluate this artifact"
    WARN) is treated the same as the whole package being unimportable for
    THAT one row: `status="unknown"`, never a silently dropped source --
    the other nine still run.
    """
    try:
        from pyforge.doctor.sources import scope_for
        from pyforge.doctor.sources.__main__ import DISPATCH
        from pyforge.doctor.models import Source
        from pyforge.doctor.verdict import exit_code_for
    except ImportError as exc:
        return [
            {"path": f"pyforge.doctor.sources:{name}", "name": name,
             "scope": "?", "task": task, "rc": 2, "status": "unknown",
             "secs": 0.0,
             "summary": f"pyforge.doctor is not importable here — {exc}",
             "output": ""}
            for name, task in _DOCTOR_SOURCE_TASKS
        ]

    rows: list[dict] = []
    for name, task in _DOCTOR_SOURCE_TASKS:
        source_scope = scope_for(Source(name))
        if scope not in ("all", source_scope):
            continue
        started = time.monotonic()
        try:
            findings = DISPATCH[name](ROOT)
            rc = 1 if exit_code_for(findings) != 0 else 0
            lines = [f"[{f.source.value}] {f.check}: {f.status.value} -- {f.message}"
                     for f in findings]
            status = {0: "pass", 1: "FINDINGS"}.get(rc, "unknown")
            summary = lines[-1][:200] if lines else "no findings"
            output = "\n".join(lines)
        except Exception as exc:  # noqa: BLE001 -- a defect in the source
            # itself (escaping its own degrade_on_exception net) must not
            # take the other nine sources down with it, and must not read
            # as a silent pass -- unknown, same as the import-failure path.
            rc, status = 2, "unknown"
            summary = f"{name} raised {exc.__class__.__name__}: {exc}"
            output = summary
        rows.append({
            "path": f"pyforge.doctor.sources:{name}", "name": name,
            "scope": source_scope, "task": task, "rc": rc, "status": status,
            "secs": round(time.monotonic() - started, 1),
            "summary": summary, "output": output,
        })
    return rows


def _structured_findings_from_output(name: str, out: str) -> list[dict]:
    """Parse machine-readable findings a detector embeds in its stdout.

    Story 28.7 (index freshness): ``index_freshness_check`` emits a final
    ``{"_findings": [...]}`` JSON line when run with ``--json``. Marshal's
    ``check`` front door surfaces those as named ``MRS-IDXF-*`` advisories
    instead of a generic ``MRS-CHECK-002`` wrapper."""
    if name != "index_freshness_check":
        return []
    for line in reversed(out.strip().splitlines()):
        line = line.strip()
        if not line.startswith("{") or "_findings" not in line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw = payload.get("_findings") if isinstance(payload, dict) else None
        if not isinstance(raw, list):
            return []
        structured: list[dict] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            code = entry.get("code")
            message = entry.get("message")
            if isinstance(code, str) and isinstance(message, str):
                home = entry.get("home")
                if isinstance(home, str) and home:
                    message = f"[{home}] {message}"
                structured.append({"code": code, "message": message})
        return structured
    return []


def run_one(det: dict, timeout: int) -> dict:
    started = time.monotonic()
    argv = [sys.executable, str(ROOT / det["path"])]
    # Story 28.7: only this detector currently ships structured findings;
    # pass --json so its `_findings` envelope is parseable. Other detectors
    # are unchanged (many do not accept unknown flags).
    if det["name"] == "index_freshness_check":
        argv.append("--json")
    try:
        proc = subprocess.run(
            argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        rc, out = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        rc, out = 2, f"UNKNOWN: exceeded {timeout}s"
    status = {0: "pass", 1: "FINDINGS"}.get(rc, "unknown")
    tail = [ln for ln in out.strip().splitlines() if ln.strip()]
    structured_findings = _structured_findings_from_output(det["name"], out)
    return {
        **det,
        "rc": rc,
        "status": status,
        "secs": round(time.monotonic() - started, 1),
        "summary": tail[-1][:200] if tail else "",
        "output": out,
        "structured_findings": structured_findings,
    }


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
        doctor_sources_available, doctor_sources = _doctor_sources()
        if args.json:
            print(json.dumps({
                "detectors": detectors,
                "registry": registry_findings,
                "doctor_sources_available": doctor_sources_available,
                "doctor_sources": doctor_sources,
            }, indent=1))
        else:
            for d in detectors:
                print(f"  {d['scope']:7} {d['name']:22} task={d['task'] or '(NONE)'}")
            for f in registry_findings:
                print(f"  ✗ registry: {f}")
            print("\n  doctor sources (declared, not scanned):")
            if not doctor_sources_available:
                print("    (unavailable -- pyforge.doctor is not importable "
                      "in this environment)")
            for s in doctor_sources:
                print(f"  {s['scope']:7} {s['source']:22} "
                      f"subject={s['subject_station']:<8} owner={s['owning_station']}")
        return 1 if registry_findings else 0

    # Story 6.9: the ten ported Doctor sources run for real here too, merged
    # into the SAME results/exit-code aggregation a scanned detector's row
    # feeds -- discover() above is blind to them (their `scripts/*_check.py`
    # origins are gone once retired; nothing left on disk to AST-scan), so
    # without this the registry would silently discover fewer detectors
    # rather than reporting the ten as unknown.
    results = [run_one(d, args.timeout) for d in selected] + _run_doctor_sources(args.scope)

    if args.json:
        for r in results:
            r.pop("output", None)
            # Preserve structured_findings for marshal check's front door.
            if not r.get("structured_findings"):
                r.pop("structured_findings", None)
        print(json.dumps({"registry": registry_findings, "results": results}, indent=1))
    else:
        print(f"detectors — scope={args.scope}, {len(results)} selected\n")
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
