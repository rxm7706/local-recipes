"""The marshal-durability gather filter — Doctor's verdict on the Marshal's own row.

**Why this module exists, and why it is HERE rather than in ``pyforge.marshal``.**

Charter §6, ratified 2026-07-28: *"the Doctor holds the verdict on the Marshal's
conformance — the one station that would otherwise grade itself,"* and *"the Marshal
may not weaken, re-threshold or disable a check that judges the Marshal."*

On 2026-08-08 that clause stopped being abstract. A single ``sprint-ledger-sync`` run
destroyed **96 ``done`` markers across four stations** (herald 55, steward 19, doctor
14, scribe 8) by letting each station's stale, gitignored Tier-3 feed overwrite its
durable tracked twin. It printed success. Three guards were then built — a pre-write
refusal, ``--project`` blast-radius scoping, and a CI regression detector — and **all
three live in Marshal's own surface**. Marshal grading Marshal is precisely what §6
forbids.

**The independence rule, which is the entire point of this module:**

    This module reads the DURABLE ARTIFACTS — tracked ledgers and git history —
    and never imports ``pyforge.marshal``.

Contrast ``sources/warden.py``, which deliberately DOES import warden and wraps
warden's own ``--doctor`` self-check (AD-1). That is correct there: Doctor is relaying
an instrument's self-report about its own environment. It would be wrong here. A
durability verdict assembled from Marshal's own code would be Marshal's self-report
wearing Doctor's badge, and would fail exactly when Marshal's own machinery is what
broke — which is the only case that matters. Reading the artifacts directly means this
check keeps working when ``pyforge.marshal`` is absent, broken, or lying.

That independence is structural, not a policy anyone must remember: the check lives in
Doctor's package and depends on nothing Marshal ships, so a Marshal story physically
cannot re-threshold it. ``tests/unit/test_sources_marshal_independence.py`` pins it,
mirroring ``test_no_warden_import.py`` in the opposite direction.

**Degrades, never crashes** — the house rule for every Doctor source. A repo with no
ledgers, no git, or an unreadable tree yields a WARN Finding, never a traceback:
Doctor's whole purpose is to survive and report on a broken environment.
"""

from __future__ import annotations

from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source

__all__ = ("gather",)

LEDGER_REL = "planning-artifacts/sprint-status-ledger.yaml"
PROJECTS_REL = "_bmad-output/projects"
TERMINAL = frozenset({"done"})


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or None on any failure.

    Routes through ``cli_bridge.run_git`` — AD-5 makes that module the SOLE
    subprocess site in the package, enforced by
    ``tests/meta/test_cli_bridge_sole_subprocess.py``. The first cut of this module
    called ``subprocess`` directly and that meta-test caught it.

    Never raises: a missing binary, a non-repo target and a failed command are all
    "cannot evaluate", which this module reports as a WARN Finding rather than
    crashing on — the house rule for every Doctor source.
    """
    try:
        return run_git(target, list(args))
    except CliBridgeError:
        return None


def _parse_statuses(text: str) -> dict[str, str]:
    """``key: value`` pairs under ``development_status:``.

    A deliberately tiny parser rather than PyYAML — this must not acquire a
    dependency to read a file whose shape is fixed by its own generator, and it must
    keep working on a partially-corrupt file rather than raising.
    """
    out: dict[str, str] = {}
    in_block = False
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _ledgers(target: Path) -> list[Path]:
    projects = target / PROJECTS_REL
    if not projects.is_dir():
        return []
    try:
        return sorted(p / LEDGER_REL for p in projects.iterdir()
                      if (p / LEDGER_REL).is_file())
    except OSError:
        return []


def gather(target: Path) -> tuple[Finding, ...]:
    """Judge the Marshal's durability guarantees from the durable record alone.

    Two questions, both answered without asking Marshal:

    1. **Does the tracked record still hold every completion it once held?**
       Compares each ledger's committed state against its working-tree state. A
       story that finished must not un-finish; the only sanctioned way is an explicit
       commit that says so, which this reports rather than silently accepts.
    2. **Is the durable record present at all?** A project with planning artifacts but
       no tracked ledger has no durable completions — CI cannot see them, and a clone
       cannot either. That is the condition the tracked twin exists to prevent.
    """
    findings: list[Finding] = []
    ledgers = _ledgers(target)

    if not ledgers:
        return (Finding(
            source=Source.MARSHAL_DURABILITY,
            check="ledger-inventory",
            status=DoctorStatus.WARN,
            message=(
                f"no tracked sprint ledger found under {PROJECTS_REL}/*/{LEDGER_REL} "
                f"— Marshal's durability guarantee cannot be evaluated here"
            ),
            evidence={"target": str(target), "ledgers": 0},
        ),)

    if _git(target, "rev-parse", "--git-dir") is None:
        return (Finding(
            source=Source.MARSHAL_DURABILITY,
            check="ledger-regression",
            status=DoctorStatus.WARN,
            message=(
                f"{len(ledgers)} tracked ledger(s) present but git is unavailable or "
                f"{target} is not a repository — regression cannot be evaluated"
            ),
            evidence={"target": str(target), "ledgers": len(ledgers)},
        ),)

    total_lost = 0
    for ledger in ledgers:
        project = ledger.relative_to(target / PROJECTS_REL).parts[0]
        rel = ledger.relative_to(target).as_posix()

        committed = _git(target, "show", f"HEAD:{rel}")
        if committed is None:
            findings.append(Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-untracked",
                status=DoctorStatus.WARN,
                message=(
                    f"{project}: sprint ledger exists on disk but is not committed — "
                    f"CI and every fresh clone are blind to its completions"
                ),
                evidence={"project": project, "path": rel},
            ))
            continue

        try:
            working = ledger.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-unreadable",
                status=DoctorStatus.WARN,
                message=f"{project}: sprint ledger could not be read ({exc})",
                evidence={"project": project, "path": rel},
            ))
            continue

        before, after = _parse_statuses(committed), _parse_statuses(working)
        lost = [
            (k, v) for k, v in sorted(before.items())
            if v in TERMINAL and after.get(k) not in TERMINAL
        ]
        if lost:
            total_lost += len(lost)
            findings.append(Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-regression",
                status=DoctorStatus.FAIL,
                message=(
                    f"{project}: {len(lost)} story(ies) un-finished relative to the "
                    f"committed ledger — a completion that was durable is not any more"
                ),
                evidence={
                    "project": project, "path": rel, "count": len(lost),
                    "keys": [k for k, _ in lost[:20]],
                    "remedy": f"git checkout HEAD -- {rel}",
                },
            ))

    if not findings:
        findings.append(Finding(
            source=Source.MARSHAL_DURABILITY,
            check="ledger-regression",
            status=DoctorStatus.OK,
            message=(
                f"{len(ledgers)} tracked ledger(s) hold every completion they held at "
                f"HEAD — no story un-finished"
            ),
            evidence={"ledgers": len(ledgers), "regressed": 0},
        ))
    elif total_lost:
        findings.append(Finding(
            source=Source.MARSHAL_DURABILITY,
            check="ledger-regression-total",
            status=DoctorStatus.FAIL,
            message=(
                f"{total_lost} completion(s) lost across "
                f"{sum(1 for f in findings if f.check == 'ledger-regression')} ledger(s)"
            ),
            evidence={"lost": total_lost, "ledgers": len(ledgers)},
        ))
    return tuple(findings)
