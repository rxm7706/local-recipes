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

import json
import re
from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source

__all__ = ("gather", "gather_story_status")

LEDGER_REL = "planning-artifacts/sprint-status-ledger.yaml"
PROJECTS_REL = "_bmad-output/projects"
TERMINAL = frozenset({"done"})

# --- gather_story_status (Story 6.4, FR-15) -------------------------------
#
# Ported from scripts/story_status_check.py -- see that script's own module
# docstring for the full false-green defect and the three-route evidence
# rationale ("git is the sole authority for repository facts; the journal
# owns process facts"). Independence: `_harness_tasks` reads ONLY host
# filesystem state under `loop_root` (plain pathlib/json, never Marshal's
# code) and the two git calls below route through this module's own `_git`
# wrapper -- no second subprocess pathway.

SPRINT_STATUS_GLOB = "_bmad-output/projects/pyforge-*/implementation-artifacts/sprint-status.yaml"
DONE_RE = re.compile(r"^  ([a-z0-9][a-z0-9-]*): done$", re.MULTILINE)
NOT_LANDED = frozenset({"deferred", "escalated", "abandoned"})


def _git(target: Path, *args: str, timeout: float = 30.0) -> str | None:
    """``git`` stdout, or None on any failure.

    Routes through ``cli_bridge.run_git`` — AD-5 makes that module the SOLE
    subprocess site in the package, enforced by
    ``tests/meta/test_cli_bridge_sole_subprocess.py``. The first cut of this module
    called ``subprocess`` directly and that meta-test caught it.

    ``timeout`` defaults to ``run_git``'s own default (kept explicit here so a
    caller can widen it) -- ``gather_story_status``'s two ``git log`` calls pass
    ``timeout=60.0`` to match ``scripts/story_status_check.py``'s own ``sh()``
    helper exactly; every other call site in this module is unaffected.

    Never raises: a missing binary, a non-repo target and a failed command are all
    "cannot evaluate", which this module reports as a WARN Finding rather than
    crashing on — the house rule for every Doctor source.
    """
    try:
        return run_git(target, list(args), timeout=timeout)
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


def _harness_tasks(loop_root: Path, slug: str) -> dict[str, dict]:
    """Most-advanced run record per story key, across every run of a station.

    'Most advanced' = prefer a record carrying a ``commit_sha``, since a
    later run can re-drive a story an earlier run deferred. Port of
    ``scripts/story_status_check.py``'s own ``harness_tasks`` -- reads ONLY
    host filesystem state (``pathlib``/``json``, no git, no subprocess), and
    a missing or corrupt ``state.json`` is silently skipped rather than
    raising, mirroring the script's own broad try/except-and-continue.
    """
    out: dict[str, dict] = {}
    home = loop_root / f"pyforge-{slug}"
    for state in sorted(home.glob(".bmad-loop/runs/*/state.json")):
        try:
            tasks = json.loads(state.read_text(encoding="utf-8")).get("tasks") or {}
            for key, task in tasks.items():
                prev = out.get(key)
                if prev is None or (
                    task.get("commit_sha") and not prev.get("commit_sha")
                ):
                    out[key] = task
        except Exception:  # noqa: BLE001, S112 -- a corrupt/unreadable run
            # record (unreadable file, invalid JSON, or a `tasks`/per-task
            # shape that isn't the expected dict -- e.g. a list, or a task
            # value with no `.get`) is skipped whole, not fatal to the whole
            # gather; a WARN Finding would misattribute a per-run read
            # failure to the story-status verdict itself, so this degrades
            # silently instead (mirrors the source script's own broad
            # try/except-and-continue, widened to cover the same shape
            # assumptions the original script also makes without guarding).
            continue
    return out


def gather_story_status(
    target: Path, *, loop_root: Path | None = None
) -> tuple[Finding, ...]:
    """Judge whether every ``done`` story in every station's Tier-3 sprint
    feed is backed by real landing evidence -- the library form of
    ``scripts/story_status_check.py``'s own ``main()``, minus the print/exit
    CLI surface.

    A ``done`` story is confirmed landed if any of three routes holds: a
    merge commit naming its key exists on any ref; the harness recorded a
    ``commit_sha`` for it; or a commit reachable from ``main`` names it as
    ``Story <epic>.<seq>`` (the hand-landed route). It is reported ONLY when
    none of those hold AND the harness positively says the story is
    ``deferred``/``escalated``/``abandoned`` -- a story with no run record at
    all (hand-implemented, pre-loop) stays silent, since absence of evidence
    is not evidence of absence.

    ``loop_root`` defaults to ``Path.home() / ".bmad-loops"``, matching the
    script's own hardcoded ``LOOP_ROOT``. Tier-3 feeds
    (``_bmad-output/projects/pyforge-*/implementation-artifacts/
    sprint-status.yaml``) are gitignored, so in a bare CI checkout this glob
    finds nothing and the gather degrades to a vacuous ``audited=0`` OK
    Finding rather than crashing.
    """
    if loop_root is None:
        loop_root = Path.home() / ".bmad-loops"

    false_greens: list[dict] = []
    audited = 0
    for feed in sorted(target.glob(SPRINT_STATUS_GLOB)):
        slug = feed.parent.parent.name.removeprefix("pyforge-")
        tasks = _harness_tasks(loop_root, slug)
        try:
            text = feed.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for key in DONE_RE.findall(text):
            audited += 1
            task = tasks.get(key)
            # No run record at all -> pre-loop or hand-implemented. Stay silent.
            if task is None:
                continue
            if task.get("commit_sha"):
                continue  # harness recorded a commit

            if _git(
                target, "log", "--oneline", "--all", "-F", f"--grep=/{key} into",
                timeout=60.0,
            ):
                continue  # merge commit found

            # Route 3: landed BY HAND, reachable from main -- see the source
            # script's own docstring for why this must be a commit SUBJECT
            # (not anywhere in the message) naming both the slug and the
            # `Story <epic>.<seq>` phrase.
            m = re.match(r"^(\d+)-(\d+)-", key)
            if m:
                needle = f"story {m.group(1)}.{m.group(2)}"
                subjects = (
                    _git(target, "log", "--format=%s", "main", timeout=60.0) or ""
                ).lower().splitlines()
                if any(slug in s and needle in s for s in subjects):
                    continue  # hand-landed; named in a commit subject on main

            phase = task.get("phase", "")
            if phase in NOT_LANDED:
                false_greens.append({
                    "slug": slug, "key": key, "phase": phase,
                    "defer_reason": task.get("defer_reason") or "",
                })

    # Findings are constructed AFTER the loop, not appended during it, so
    # every one -- FAIL or OK -- carries the FINAL `audited` total in its
    # evidence: an automated `--json` consumer reading a FAIL finding must
    # be able to tell "3 of 50 audited" from "3 of 3 audited" without a
    # separate summary finding.
    if false_greens:
        return tuple(
            Finding(
                source=Source.STORY_STATUS,
                check="story-status",
                status=DoctorStatus.FAIL,
                message=(
                    f"{fg['slug']}/{fg['key']}: reads `done` in the sprint feed, "
                    f"but the harness says {fg['phase']!r} with no commit and no "
                    f"merge commit anywhere"
                    + (f" — {fg['defer_reason']}" if fg["defer_reason"] else "")
                ),
                evidence={**fg, "audited": audited},
            )
            for fg in false_greens
        )

    return (
        Finding(
            source=Source.STORY_STATUS,
            check="story-status",
            status=DoctorStatus.OK,
            message=(
                f"every `done` story is backed by a merge commit or a recorded "
                f"commit sha ({audited} audited)"
            ),
            evidence={"audited": audited},
        ),
    )
