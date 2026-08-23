"""The ledger-regression gather filter -- Doctor's verdict on the tracked
sprint ledger's own regression-freedom (Story 6.4, FR-15).

**Why this module exists, and why it is HERE rather than in ``pyforge.marshal``.**

Charter §6, ratified 2026-07-28: *"the Doctor holds the verdict on the Marshal's
conformance — the one station that would otherwise grade itself,"* and *"the Marshal
may not weaken, re-threshold or disable a check that judges the Marshal."* This module
is the second of the ledger's own guards to move onto Doctor's side of that line,
porting ``scripts/ledger_regression_check.py``'s read-only judgement verbatim in
behavior (see that script's own module docstring for the full 2026-08-08 incident this
guards against: a single sync run destroying 96 ``done`` markers across four stations).

**How this relates to ``sources/marshal.py``'s own ``gather`` (``Source.
MARSHAL_DURABILITY``), the first guard to move.** Both answer "did a `done` key
un-finish," but over different spans, and both are needed: ``MARSHAL_DURABILITY``
compares the WORKING TREE against ``HEAD`` — a local, immediate guard that catches
an uncommitted regression before it is ever pushed. This module compares two
COMMITTED REVISIONS (``base``..``head``, default ``origin/main``..``HEAD``) — the
outermost of three guards ``ledger_regression_check.py``'s own docstring describes
(pre-write refusal, ``--project`` scoping, this), designed to run in CI against a
whole revision range, including regressions that already landed on a branch. Neither
supersedes the other; a regression could in principle be caught by only one
depending on when it is measured.

The pair does NOT currently agree on the "I cannot see any ledger at all" case:
the sibling reports WARN (``check="ledger-inventory"``), this module reports OK.
That divergence is recorded in ``deferred-work.md`` rather than resolved here —
named in this paragraph because this paragraph exists precisely so a maintainer
comparing the two guards is not surprised by them.

**The independence rule, which is the entire point of this module:**

    This module reads the DURABLE ARTIFACTS — tracked ledgers at two revisions,
    via ``git show``/``git ls-tree`` — and never imports ``pyforge.marshal`` (or
    any other station package).

Mirrors ``sources/marshal.py``'s own independence rationale exactly: a regression
verdict assembled from Marshal's own code would be Marshal's self-report wearing
Doctor's badge, and would fail in exactly the case that matters — when Marshal's own
machinery is what broke. Reading the two revisions' committed blobs directly means
this check keeps working when ``pyforge.marshal`` is absent, broken, or lying.
``tests/unit/test_sources_ledger_independence.py`` pins it, mirroring
``test_sources_marshal_independence.py``.

**Degrades, never crashes** — the house rule for every Doctor source. An unresolvable
``base`` ref, or ``base``/``head`` naming the same commit with no parent to fall back
to, yields a WARN Finding rather than the original script's ``exit 2``/raised error —
this is a library function, not a CLI, so it never prints or exits.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source

__all__ = ("gather", "gather_ledger_staleness")

PROJECTS_PREFIX = "_bmad-output/projects/"
LEDGER_SUFFIX = "planning-artifacts/sprint-status-ledger.yaml"
TERMINAL = frozenset({"done"})

# A story key is `<id>-<kebab-title>`, where `<id>` is either the canonical
# `<epic>-<num>[suffix]` or a legacy alias (`a1`, `b10`). The TAIL is what
# survives a convention migration, so it is what identifies a story across one.
_ID_PREFIX_RE = re.compile(r"^(?:\d+-\d+[a-z]?|[a-z]+\d+)-")
_GITHUB_MERGE_RE = re.compile(
    r"^Merge pull request #\d+ from \S+?/(?P<branch>\S+)$"
)
_BMADLOOP_MERGE_RE = re.compile(
    r"^Merge bmad-loop/\S+/(?P<key_slug>\S+) into (?P<target>\S+) \(bmad-loop\)$"
)
_TEMPLATED_MERGE_RE = re.compile(
    # Require a kebab title after the id — bare "Merge 15-2 into main" is not
    # a durable story landing (cross-project collision; live false-positive).
    r"^Merge (?P<key_slug>\d+-\d+[a-z]?-\S+) into \S+"
)


def _tail(key: str) -> str:
    """``2-1-scaffold-the-kedro`` and ``a1-scaffold-the-kedro`` share a tail."""
    return _ID_PREFIX_RE.sub("", key, count=1)


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or None on any failure.

    Routes through ``cli_bridge.run_git`` — AD-5 makes that module the SOLE
    subprocess site in the package, enforced by
    ``tests/meta/test_cli_bridge_sole_subprocess.py``. Mirrors
    ``sources/marshal.py``'s own ``_git`` wrapper.

    Never raises: an unresolvable ref, a non-repo target, and a failed command
    are all "cannot evaluate", which this module reports as a WARN Finding
    rather than crashing on.

    ``UnicodeDecodeError`` is caught alongside ``CliBridgeError`` because
    ``run_git`` decodes with ``text=True`` and catches only ``TimeoutExpired``/
    ``OSError`` -- so a committed ledger blob holding a non-UTF-8 byte raises
    straight through ``git show`` and out of ``gather()``, breaking the spec's
    "degrade to a WARN/OK Finding on any unreadable/missing input, never raise"
    boundary (verified: a `\\xe9` byte in a tracked ledger raised out of
    ``gather``). The one-catch fix for EVERY ``run_git`` caller belongs in
    ``cli_bridge`` itself and stays recorded in ``deferred-work.md``; this
    local guard keeps THIS module's own documented contract true meanwhile.

    Not raising is only half the contract, though: ``None`` here means "could
    not evaluate", and every caller must keep that distinct from the ordinary
    absence it would otherwise look identical to. ``_check`` does that by
    consulting the ``ls-tree`` listings before interpreting a ``git show``
    failure — see its own docstring.
    """
    try:
        return run_git(target, list(args))
    except (CliBridgeError, UnicodeDecodeError):
        return None


def _parse_statuses(text: str) -> dict[str, str]:
    """``key: value`` pairs under ``development_status:``.

    A deliberately tiny parser rather than PyYAML — same rationale as
    ``sources/marshal.py``'s own ``_parse_statuses``: the file's shape is
    fixed by its own generator, and this must keep working on a
    partially-corrupt blob rather than raising.
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
            break  # dedent ends the block
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _ledger_paths(target: Path, rev: str) -> list[str]:
    """Tracked ledger paths at ``rev`` — listed from git, not the working
    tree, so a ledger deleted in the working tree is still compared."""
    listing = _git(target, "ls-tree", "-r", "--name-only", rev) or ""
    return sorted(
        p
        for p in listing.splitlines()
        if p.startswith(PROJECTS_PREFIX) and p.endswith(LEDGER_SUFFIX)
    )


def _check(target: Path, base: str, head: str) -> tuple[list[dict], int]:
    """Port of the script's own ``check(base, head)`` — see
    ``scripts/ledger_regression_check.py`` for the full rename-continuity
    rationale (a renamed-but-still-``done`` key, id prefix changed but kebab
    tail surviving, is continuity, not regression).

    Returns the findings AND how many ledgers were actually COMPARED — both
    blobs fetched and parsed, not merely listed. "clean" and "found nothing to
    look at" are the same empty finding list, and the caller reports both as OK
    today (recorded in ``deferred-work.md``, where the OK-vs-WARN verdict for an
    empty measurement is owned). Carrying the count means that decision is at
    least visible in the report meanwhile, instead of a green with nothing
    behind it — which is only true if the count excludes a ledger whose blob
    never got read.

    ``_git`` collapses EVERY failure to ``None``, so "this path does not exist
    at that revision" and "this path exists there but its blob would not
    decode" arrive here identically. They mean opposite things — the first is
    ordinary history, the second is an unevaluated ledger — so the two ``ls-tree``
    listings (already in hand) decide which happened, and an unreadable blob
    becomes a cannot-evaluate WARN rather than being silently absorbed into
    "new ledger" (a green over an unmeasured ledger) or "ledger deleted" (a FAIL,
    with a destructive ``git checkout`` remedy, for a ledger that is still
    there)."""
    findings: list[dict] = []
    base_paths = set(_ledger_paths(target, base))
    head_paths = set(_ledger_paths(target, head))
    compared = 0
    for path in sorted(base_paths | head_paths):
        project = path.split("/")[2]

        before_text = (
            _git(target, "show", f"{base}:{path}") if path in base_paths else None
        )
        if before_text is None:
            if path in base_paths:
                findings.append(
                    {
                        "kind": "ledger-unreadable",
                        "warn": True,
                        "project": project,
                        "path": path,
                        "detail": (
                            f"ledger is tracked at {base} but its blob could not "
                            f"be read — this ledger's regression status is unknown"
                        ),
                    }
                )
            continue  # otherwise: absent at base, i.e. a new ledger — nothing to regress
        before = _parse_statuses(before_text)

        after_text = (
            _git(target, "show", f"{head}:{path}") if path in head_paths else None
        )
        if after_text is None:
            if path in head_paths:
                findings.append(
                    {
                        "kind": "ledger-unreadable",
                        "warn": True,
                        "project": project,
                        "path": path,
                        "detail": (
                            f"ledger is tracked at {head} but its blob could not "
                            f"be read — this ledger's regression status is unknown"
                        ),
                    }
                )
                continue
            done = sorted(k for k, v in before.items() if v in TERMINAL)
            if done:
                findings.append(
                    {
                        "kind": "ledger-deleted",
                        "project": project,
                        "path": path,
                        "count": len(done),
                        "keys": done,
                        "detail": f"ledger deleted while holding {len(done)} `done` key(s)",
                    }
                )
            continue

        compared += 1

        after = _parse_statuses(after_text)
        surviving_tails = {_tail(k) for k, v in after.items() if v in TERMINAL}
        lost = []
        for key, old in sorted(before.items()):
            if old not in TERMINAL:
                continue
            new = after.get(key)
            if new is None:
                if _tail(key) in surviving_tails:
                    continue  # renamed, still done — continuity, not regression
                lost.append((key, old, "<absent>"))
            elif new not in TERMINAL:
                lost.append((key, old, new))
        if lost:
            findings.append(
                {
                    "kind": "done-key-regressed",
                    "project": project,
                    "path": path,
                    "count": len(lost),
                    "keys": [k for k, _o, _n in lost],
                    "transitions": [
                        {"key": k, "from": o, "to": n} for k, o, n in lost
                    ],
                    "detail": f"{len(lost)} story key(s) moved out of `done`",
                }
            )
    return findings, compared


def gather(
    target: Path, *, base: str = "origin/main", head: str = "HEAD"
) -> tuple[Finding, ...]:
    """Judge whether any commit between ``base`` and ``head`` un-finished a
    story in a tracked sprint ledger — the library form of
    ``scripts/ledger_regression_check.py``'s own ``main()``, minus the
    print/exit CLI surface: every branch that script maps to ``exit 2``
    ("UNDETERMINED") here becomes one WARN ``Finding`` instead, and every
    regression becomes a FAIL ``Finding`` rather than a printed report.

    ``base``/``head`` default to the script's own hardcoded defaults
    (``"origin/main"``/``"HEAD"``). Preserves the script's same-commit
    fallback: if ``base`` and ``head`` resolve to the same commit (the shape
    CI takes on a ``push: branches: [main]`` event), this compares against
    ``head``'s first parent instead — the honest question for a push is
    "what did this change?", not "compare a revision to itself" (which would
    report clean forever).
    """
    if _git(target, "rev-parse", "--verify", "--quiet", base) is None:
        # Both statuses are WARN, but the MESSAGE has to name the real cause:
        # "no such ref" sends an operator hunting for a ref problem, when the
        # actual state may be "this isn't a git repository at all." Probed only
        # on the failure path, so the healthy case pays nothing extra. Mirrors
        # the dedicated probe `sources/marshal.py`'s own gather() already runs.
        if _git(target, "rev-parse", "--git-dir") is None:
            message = (
                f"git is unavailable or {target} is not a repository — ledger "
                f"regression cannot be evaluated"
            )
        else:
            message = (
                f"base revision {base!r} not resolvable — ledger regression "
                f"cannot be evaluated"
            )
        return (
            Finding(
                source=Source.LEDGER_REGRESSION,
                check="ledger-regression",
                status=DoctorStatus.WARN,
                message=message,
                evidence={"base": base, "head": head, "target": str(target)},
            ),
        )

    base_sha = (_git(target, "rev-parse", base) or "").strip()
    head_sha = (_git(target, "rev-parse", head) or "").strip()
    effective_base = base
    if base_sha and base_sha == head_sha:
        parent = (
            _git(target, "rev-parse", "--verify", "--quiet", f"{head}^") or ""
        ).strip()
        if not parent:
            return (
                Finding(
                    source=Source.LEDGER_REGRESSION,
                    check="ledger-regression",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{base!r} and {head!r} are the same commit and it has "
                        f"no parent — nothing to compare"
                    ),
                    # `target` is carried on BOTH cannot-evaluate WARNs, not
                    # just the unresolvable-base one: same source, same check,
                    # same status, so a consumer reading evidence["target"]
                    # must not KeyError depending on which of the two fired.
                    evidence={"base": base, "head": head, "target": str(target)},
                ),
            )
        effective_base = parent

    # The original script PRINTED a "comparing against {head}^ instead" note
    # when it substituted. A library has no stdout to say that on, so the
    # substitution is carried in evidence instead: without it a `--json`
    # consumer that asked for base="origin/main" gets a 40-char sha back with
    # no way to tell "you asked for this" from "we quietly swapped it."
    substituted = effective_base != base
    range_evidence: dict[str, object] = {"base": effective_base, "head": head}
    if substituted:
        range_evidence["base_requested"] = base
        range_evidence["base_substituted"] = True

    raw_findings, ledgers_compared = _check(target, effective_base, head)
    range_evidence["ledgers_compared"] = ledgers_compared

    if not raw_findings:
        return (
            Finding(
                source=Source.LEDGER_REGRESSION,
                check="ledger-regression",
                status=DoctorStatus.OK,
                message=(
                    f"no tracked ledger un-finishes a story between "
                    f"{effective_base} and {head}"
                ),
                evidence=dict(range_evidence),
            ),
        )

    findings: list[Finding] = []
    for item in raw_findings:
        # A ledger whose blob would not decode is a cannot-evaluate, not a
        # verdict: WARN, and NO `remedy` — the FAIL branch's remedy is a
        # `git checkout <base> -- <path>`, which would discard the head ledger
        # over what may be a purely cosmetic edit.
        if item.get("warn"):
            findings.append(
                Finding(
                    source=Source.LEDGER_REGRESSION,
                    check=item["kind"],
                    status=DoctorStatus.WARN,
                    message=f"{item['project']}: {item['detail']}",
                    evidence={
                        "project": item["project"],
                        "path": item["path"],
                        **range_evidence,
                    },
                )
            )
            continue
        findings.append(
            Finding(
                source=Source.LEDGER_REGRESSION,
                check=item["kind"],
                status=DoctorStatus.FAIL,
                message=f"{item['project']}: {item['detail']}",
                evidence={
                    "project": item["project"],
                    "path": item["path"],
                    "count": item["count"],
                    # The original script's own [:12] truncates a TERMINAL
                    # print for a human to scroll; this evidence field is
                    # structured JSON for an automated `--json` consumer, not
                    # scrolled, so a slightly higher bound is used here --
                    # still bounded (never unbounded), just not required to
                    # match a print-width choice that doesn't apply to this
                    # shape.
                    #
                    # For the same reason `keys` is BARE story keys under both
                    # `check` kinds. It previously held pre-formatted
                    # "<key> (<old> -> <new>)" strings for done-key-regressed
                    # and bare keys for ledger-deleted -- one field name, two
                    # shapes, forcing the JSON consumer this comment invokes to
                    # re-parse a display string to recover the transition. The
                    # transition now travels beside it, already structured.
                    "keys": item["keys"][:20],
                    **(
                        {"transitions": item["transitions"][:20]}
                        if "transitions" in item
                        else {}
                    ),
                    **range_evidence,
                    "remedy": f"git checkout {effective_base} -- {item['path']}",
                },
            )
        )
    return tuple(findings)


# === gather_ledger_staleness (Story 15.2 / FR-137..FR-138) ==================
#
# Standalone ledger-vs-git drift WITH DIRECTION. Reads the TRACKED twin and
# merge history only — never the Tier-3 feed (FR-138). Independence: no
# ``pyforge.marshal`` import; merge-subject patterns restated here (Charter
# §6) so this check keeps working when Marshal is absent/broken/lying.


def _story_id_from_slug(key_slug: str) -> str | None:
    """Leading ``<epic>-<seq>[suffix]`` from a merge-subject key segment."""
    head = key_slug.split("-", 2)
    if len(head) < 2:
        return None
    candidate = f"{head[0]}-{head[1]}"
    # Include optional single-letter suffix glued to seq (e.g. ``6-1a``).
    m = re.match(r"^(\d+)-(\d+[a-z]?)", candidate)
    if m is None:
        # try full key_slug start
        m = re.match(r"^(\d+)-(\d+[a-z]?)", key_slug)
    if m is None:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def _story_id_from_ledger_key(raw_key: str) -> str | None:
    m = re.match(r"^(\d+)-(\d+[a-z]?)", raw_key)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _merged_ids_for_project(subjects: list[str], project_slug: str) -> set[str]:
    """Story ids durably merged for ``project_slug`` (merge history only)."""
    out: set[str] = set()
    loop_target = f"loop/{project_slug}"
    short = project_slug.removeprefix("pyforge-")
    for subject in subjects:
        m = _BMADLOOP_MERGE_RE.match(subject)
        if m is not None:
            if m.group("target") == loop_target:
                sid = _story_id_from_slug(m.group("key_slug"))
                if sid:
                    out.add(sid)
            continue
        m = _GITHUB_MERGE_RE.match(subject)
        if m is not None:
            branch = m.group("branch")
            if (
                branch.startswith(f"{short}/")
                or branch.startswith(f"{project_slug}/")
                or branch.startswith(f"land/{short}-")
                or branch.startswith(f"land/{project_slug}-")
            ):
                m2 = re.search(r"(\d+-\d+[a-z]?)", branch)
                if m2 is not None:
                    out.add(m2.group(1))
            continue
        m = _TEMPLATED_MERGE_RE.match(subject)
        if m is not None:
            sid = _story_id_from_slug(m.group("key_slug"))
            if sid:
                out.add(sid)
            continue
        low = subject.lower()
        if short in low or project_slug in low:
            m3 = re.search(r"\bstory\s+(\d+)\.(\d+[a-z]?)\b", low)
            if m3 is not None:
                out.add(f"{m3.group(1)}-{m3.group(2)}")
    return out


def gather_ledger_staleness(target: Path) -> tuple[Finding, ...]:
    """Report ledger-vs-git drift per key WITH DIRECTION (FR-137/FR-138).

    For each tracked ``sprint-status-ledger.yaml``:
    - ``MERGED_NOT_DONE_IN_LEDGER`` (landed-but-unpromoted) → FAIL
    - ``DONE_IN_LEDGER_NOT_MERGED`` → WARN (unconfirmed; squash-merge blind spot)

    Never reads a Tier-3 ``sprint-status.yaml`` feed. Degrades to WARN when
    git or ledgers are unevaluable.
    """
    projects = target / PROJECTS_PREFIX.rstrip("/")
    if not projects.is_dir():
        return (
            Finding(
                source=Source.LEDGER_STALENESS,
                check="ledger-staleness",
                status=DoctorStatus.WARN,
                message=(
                    f"no {PROJECTS_PREFIX} tree — ledger-vs-git staleness "
                    "cannot be evaluated"
                ),
                evidence={"target": str(target), "projects": 0},
            ),
        )

    ledgers: list[Path] = []
    try:
        for p in sorted(projects.iterdir()):
            cand = p / LEDGER_SUFFIX
            if cand.is_file():
                ledgers.append(cand)
    except OSError:
        ledgers = []

    if not ledgers:
        return (
            Finding(
                source=Source.LEDGER_STALENESS,
                check="ledger-staleness",
                status=DoctorStatus.WARN,
                message=(
                    f"no tracked sprint ledger under {PROJECTS_PREFIX}*/"
                    f"{LEDGER_SUFFIX} — staleness cannot be evaluated"
                ),
                evidence={"target": str(target), "ledgers": 0},
            ),
        )

    if _git(target, "rev-parse", "--git-dir") is None:
        return (
            Finding(
                source=Source.LEDGER_STALENESS,
                check="ledger-staleness",
                status=DoctorStatus.WARN,
                message=(
                    f"{len(ledgers)} tracked ledger(s) present but git is "
                    f"unavailable or {target} is not a repository — "
                    "staleness cannot be evaluated"
                ),
                evidence={"target": str(target), "ledgers": len(ledgers)},
            ),
        )

    raw_subjects = _git(target, "log", "--format=%s", "main")
    if raw_subjects is None:
        # Fall back to HEAD history when local `main` is absent (PR checkout).
        raw_subjects = _git(target, "log", "--format=%s", "HEAD")
    if raw_subjects is None:
        return (
            Finding(
                source=Source.LEDGER_STALENESS,
                check="ledger-staleness",
                status=DoctorStatus.WARN,
                message=(
                    "cannot read merge history (main/HEAD) — ledger-vs-git "
                    "staleness cannot be evaluated"
                ),
                evidence={"target": str(target), "ledgers": len(ledgers)},
            ),
        )
    subjects = raw_subjects.splitlines()

    findings: list[Finding] = []
    for ledger in ledgers:
        project = ledger.relative_to(projects).parts[0]
        try:
            text = ledger.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(
                Finding(
                    source=Source.LEDGER_STALENESS,
                    check="ledger-staleness",
                    status=DoctorStatus.WARN,
                    message=f"{project}: tracked ledger unreadable",
                    evidence={"project": project, "path": str(ledger)},
                )
            )
            continue

        statuses = _parse_statuses(text)
        ledger_done: set[str] = set()
        ledger_all: set[str] = set()
        raw_by_id: dict[str, str] = {}
        for raw_key, status in statuses.items():
            sid = _story_id_from_ledger_key(raw_key)
            if sid is None:
                continue
            ledger_all.add(sid)
            raw_by_id.setdefault(sid, raw_key)
            token = status.split()[0] if status else ""
            if token in TERMINAL:
                ledger_done.add(sid)

        merged = _merged_ids_for_project(subjects, project)
        # Only keys present in THIS ledger: a merge for another station's
        # colliding epic-seq must not convict this one. Absences (merged
        # with no ledger row) stay out of FAIL — that is a different gap
        # (ledger inventory), not "unpromoted status".
        merged_here = merged & ledger_all
        landed_unpromoted = sorted(merged_here - ledger_done)
        done_unmerged = sorted(ledger_done - merged)

        for sid in landed_unpromoted:
            findings.append(
                Finding(
                    source=Source.LEDGER_STALENESS,
                    check="ledger-staleness",
                    status=DoctorStatus.FAIL,
                    message=(
                        f"{project}/{raw_by_id.get(sid, sid)}: landed in "
                        "merge history but not `done` in the tracked ledger "
                        "(landed-but-unpromoted)"
                    ),
                    evidence={
                        "project": project,
                        "story_id": sid,
                        "direction": "MERGED_NOT_DONE_IN_LEDGER",
                        "confidence": "confirmed",
                    },
                )
            )
        for sid in done_unmerged:
            findings.append(
                Finding(
                    source=Source.LEDGER_STALENESS,
                    check="ledger-staleness",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}/{raw_by_id.get(sid, sid)}: `done` in the "
                        "tracked ledger but no matching merge subject found "
                        "(unconfirmed — squash-merge blind spot possible)"
                    ),
                    evidence={
                        "project": project,
                        "story_id": sid,
                        "direction": "DONE_IN_LEDGER_NOT_MERGED",
                        "confidence": "unconfirmed",
                    },
                )
            )

    if findings:
        return tuple(findings)
    return (
        Finding(
            source=Source.LEDGER_STALENESS,
            check="ledger-staleness",
            status=DoctorStatus.OK,
            message=(
                f"tracked ledger(s) agree with merge history "
                f"({len(ledgers)} ledger(s) audited)"
            ),
            evidence={"ledgers": len(ledgers), "discrepancies": 0},
        ),
    )
