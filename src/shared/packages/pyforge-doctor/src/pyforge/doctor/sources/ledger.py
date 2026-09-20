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
import tomllib
from pathlib import Path

from pyforge.core.landing_evidence import parse_templated_merge_subject

from ..bare_merge import DiffCache, attribute_bare_merge, known_story_keys
from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from ..rekey import RekeyMap, parse_rekey

__all__ = ("gather", "gather_direction")

PROJECTS_PREFIX = "_bmad-output/projects/"
LEDGER_SUFFIX = "planning-artifacts/sprint-status-ledger.yaml"
#: A station's own policy file, read as TOML for exactly one key
#: (``merge_subject_template``) -- never through ``pyforge.marshal`` (this
#: module's own independence rule, see the module docstring). Duplicated in
#: ``sources/marshal.py`` rather than shared via a cross-import, mirroring
#: this file's own ``_git``/``_parse_statuses`` precedent of small, per-file
#: self-contained helpers over sibling-module coupling.
_MARSHAL_POLICY_SUFFIX = "planning-artifacts/marshal-policy.toml"
#: Repo-default template (Story 50.4) -- carries a ``{slug}`` token, so
#: ``parse_templated_merge_subject`` self-scopes a subject rendered from it
#: to the project that rendered it, even when that project declares no
#: override (Story 27.1's own "policy declares no template -> default
#: honoured" row). Kept identical to ``sources/marshal.py``'s own constant.
_MERGE_SUBJECT_TEMPLATE = "Merge {slug}/{key} into main"
#: A fold PR's re-key map (doctor Story 25.3 / spec-one-chain-per-station
#: CAP-3(g)). Considered ONLY when present at ``head`` and absent at ``base``
#: -- i.e. shipped by the range under judgement. Once merged it is in both
#: revisions and becomes inert provenance, so a dangling old key (which by
#: then no longer exists anywhere) can never fire forever.
_REKEY_RE = re.compile(r"^_bmad-output/projects/([^/]+)/planning-artifacts/rekey-[^/]+\.md$")
TERMINAL = frozenset({"done"})

# A story key is `<id>-<kebab-title>`, where `<id>` is either the canonical
# `<epic>-<num>[suffix]` or a legacy alias (`a1`, `b10`). The TAIL is what
# survives a convention migration, so it is what identifies a story across one.
_ID_PREFIX_RE = re.compile(r"^(?:\d+-\d+[a-z]?|[a-z]+\d+)-")


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
    except CliBridgeError, UnicodeDecodeError:
        return None


def _project_merge_subject_template(target: Path, project_slug: str) -> str:
    """``project_slug``'s own ``merge_subject_template``, read directly from
    its tracked ``marshal-policy.toml`` as TOML -- never through
    ``pyforge.marshal`` (this module's independence rule). Degrades to the
    repo default when the policy file is absent, unreadable, not
    valid TOML, or does not declare the key -- "degrades, never crashes,"
    and Story 27.1's own "policy declares no template -> default
    honoured" row.
    """
    path = target / PROJECTS_PREFIX / project_slug / _MARSHAL_POLICY_SUFFIX
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return _MERGE_SUBJECT_TEMPLATE
    value = data.get("merge_subject_template")
    return value if isinstance(value, str) and value else _MERGE_SUBJECT_TEMPLATE


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


def _rekey_paths(target: Path, rev: str) -> list[str]:
    listing = _git(target, "ls-tree", "-r", "--name-only", rev) or ""
    return sorted(p for p in listing.splitlines() if _REKEY_RE.match(p))


def _new_rekey_maps(target: Path, base: str, head: str) -> tuple[dict[str, dict[str, str]], list[dict]]:
    """``{project: forward_mapping}`` from maps shipped in ``base..head``,
    plus a finding dict for every map that is not clean (malformed line,
    duplicate old key, two old keys colliding on one new key)."""
    base_maps = set(_rekey_paths(target, base))
    maps: dict[str, dict[str, str]] = {}
    problems: list[dict] = []
    for path in _rekey_paths(target, head):
        if path in base_maps:
            continue
        m = _REKEY_RE.match(path)
        project = m.group(1) if m else path.split("/")[2]
        text = _git(target, "show", f"{head}:{path}")
        if text is None:
            problems.append(
                {
                    "kind": "rekey-map-unreadable",
                    "warn": True,
                    "project": project,
                    "path": path,
                    "detail": f"re-key map {path} is tracked at {head} but unreadable",
                }
            )
            continue
        parsed: RekeyMap = parse_rekey(text)
        if not parsed.clean:
            bad = [f"line {no}: {txt.strip()!r}" for no, txt in parsed.malformed]
            bad += [f"line {no}: duplicate old key {old!r}" for no, old in parsed.duplicates]
            bad += [f"collision on new key {k!r}" for k in parsed.collisions]
            problems.append(
                {
                    "kind": "rekey-map-malformed",
                    "project": project,
                    "path": path,
                    "count": len(bad),
                    "keys": bad,
                    "detail": f"re-key map has {len(bad)} unusable line(s): {'; '.join(bad[:5])}",
                }
            )
        maps.setdefault(project, {}).update(parsed.mapping)
    return maps, problems


def _ledger_paths(target: Path, rev: str) -> list[str]:
    """Tracked ledger paths at ``rev`` — listed from git, not the working
    tree, so a ledger deleted in the working tree is still compared."""
    listing = _git(target, "ls-tree", "-r", "--name-only", rev) or ""
    return sorted(p for p in listing.splitlines() if p.startswith(PROJECTS_PREFIX) and p.endswith(LEDGER_SUFFIX))


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
    rekey_maps, rekey_problems = _new_rekey_maps(target, base, head)
    findings.extend(rekey_problems)
    compared = 0
    for path in sorted(base_paths | head_paths):
        project = path.split("/")[2]

        before_text = _git(target, "show", f"{base}:{path}") if path in base_paths else None
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

        after_text = _git(target, "show", f"{head}:{path}") if path in head_paths else None
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

        # Story 25.3: a fold PR renumbers every key and ships the map. Apply it
        # to the BASE side before comparing, so a `done` row whose key moved
        # per the map is judged under its new name. The map moves keys and
        # only keys -- a status flip through it is still caught below. A map
        # line pointing at a key that exists on neither side is dangling: it
        # claims a move that did not happen, and is a FAIL in its own right.
        mapping = rekey_maps.get(project)
        if mapping:
            dangling = []
            for old, new in sorted(mapping.items()):
                if old not in before:
                    dangling.append({"line": f"{old} -> {new}", "why": f"{old} not in {base}"})
                elif new not in after:
                    dangling.append({"line": f"{old} -> {new}", "why": f"{new} not in {head}"})
            if dangling:
                findings.append(
                    {
                        "kind": "rekey-map-dangling",
                        "project": project,
                        "path": path,
                        "count": len(dangling),
                        "keys": [d["line"] for d in dangling],
                        "transitions": dangling,
                        "detail": f"{len(dangling)} re-key line(s) name a key that exists on neither side",
                    }
                )
            before = {mapping.get(k, k): v for k, v in before.items()}

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
                    "transitions": [{"key": k, "from": o, "to": n} for k, o, n in lost],
                    "detail": f"{len(lost)} story key(s) moved out of `done`",
                }
            )
    return findings, compared


def gather(target: Path, *, base: str = "origin/main", head: str = "HEAD") -> tuple[Finding, ...]:
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

    Story 27.1: when ``base`` and ``head`` name DIFFERENT commits (the
    PR-shaped case), the comparison is against ``merge-base(base, head)``,
    not ``base``'s own tip. ``base`` (typically ``origin/main``) can advance
    past the point this ``head`` branch forked from — an unrelated commit
    landing on ``base`` in the meantime (e.g. an unattended dispatch
    promoting a sibling story to ``done``) then reads as something ``head``
    "un-finished," even though ``head`` never touched it (herald PR #1465,
    2026-09-18, 18:17Z). Comparing against the honest common ancestor
    instead means only what ``head`` itself changed relative to the fork
    point is judged. A merge-base that fails to resolve (e.g. unrelated
    histories) degrades to a WARN rather than silently reverting to the
    bug this exists to fix.
    """
    if _git(target, "rev-parse", "--verify", "--quiet", base) is None:
        # Both statuses are WARN, but the MESSAGE has to name the real cause:
        # "no such ref" sends an operator hunting for a ref problem, when the
        # actual state may be "this isn't a git repository at all." Probed only
        # on the failure path, so the healthy case pays nothing extra. Mirrors
        # the dedicated probe `sources/marshal.py`'s own gather() already runs.
        if _git(target, "rev-parse", "--git-dir") is None:
            message = f"git is unavailable or {target} is not a repository — ledger regression cannot be evaluated"
        else:
            message = f"base revision {base!r} not resolvable — ledger regression cannot be evaluated"
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
    merge_base_sha: str | None = None
    if base_sha and base_sha == head_sha:
        parent = (_git(target, "rev-parse", "--verify", "--quiet", f"{head}^") or "").strip()
        if not parent:
            return (
                Finding(
                    source=Source.LEDGER_REGRESSION,
                    check="ledger-regression",
                    status=DoctorStatus.WARN,
                    message=(f"{base!r} and {head!r} are the same commit and it has no parent — nothing to compare"),
                    # `target` is carried on BOTH cannot-evaluate WARNs, not
                    # just the unresolvable-base one: same source, same check,
                    # same status, so a consumer reading evidence["target"]
                    # must not KeyError depending on which of the two fired.
                    evidence={"base": base, "head": head, "target": str(target)},
                ),
            )
        effective_base = parent
    elif base_sha and head_sha:
        # PR-shaped: `base` and `head` name different commits. The honest
        # comparison point is their common ancestor, not `base`'s own
        # (possibly since-advanced) tip -- see the docstring's Story 27.1
        # paragraph. A repo with no common ancestor between the two (e.g.
        # unrelated histories) cannot be judged; that degrades to a WARN
        # like every other cannot-evaluate branch in this function, rather
        # than silently comparing against `base`'s tip (the bug this exists
        # to fix).
        merge_base_sha = (_git(target, "merge-base", base, head) or "").strip()
        if not merge_base_sha:
            return (
                Finding(
                    source=Source.LEDGER_REGRESSION,
                    check="ledger-regression",
                    status=DoctorStatus.WARN,
                    message=(
                        f"no common ancestor between {base!r} and {head!r} — ledger regression cannot be evaluated"
                    ),
                    evidence={"base": base, "head": head, "target": str(target)},
                ),
            )
        if merge_base_sha != base_sha:
            effective_base = merge_base_sha

    # The original script PRINTED a "comparing against {head}^ instead" note
    # when it substituted. A library has no stdout to say that on, so the
    # substitution is carried in evidence instead: without it a `--json`
    # consumer that asked for base="origin/main" gets a 40-char sha back with
    # no way to tell "you asked for this" from "we quietly swapped it."
    # `merge_base` names the PR-shaped substitution specifically (Story
    # 27.1); `base_substituted` still names the pre-existing same-commit
    # push fallback above -- two different reasons a substitution happened,
    # two distinct evidence shapes, so a consumer can tell which one fired.
    substituted = effective_base != base
    range_evidence: dict[str, object] = {"base": effective_base, "head": head}
    if substituted:
        range_evidence["base_requested"] = base
        if merge_base_sha is not None and effective_base == merge_base_sha:
            range_evidence["merge_base"] = merge_base_sha
        else:
            range_evidence["base_substituted"] = True

    raw_findings, ledgers_compared = _check(target, effective_base, head)
    range_evidence["ledgers_compared"] = ledgers_compared

    if not raw_findings:
        return (
            Finding(
                source=Source.LEDGER_REGRESSION,
                check="ledger-regression",
                status=DoctorStatus.OK,
                message=(f"no tracked ledger un-finishes a story between {effective_base} and {head}"),
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
                    **({"transitions": item["transitions"][:20]} if "transitions" in item else {}),
                    **range_evidence,
                    "remedy": f"git checkout {effective_base} -- {item['path']}",
                },
            )
        )
    return tuple(findings)


# --- gather_direction (Story 15.2 / marshal FR-137, FR-138) ---------------
#
# Standalone check: tracked ledger vs. git merge history, WITH DIRECTION.
# Never reads the Tier-3 sprint-status.yaml feed (FR-138). Independence:
# never imports ``pyforge.marshal`` — merge-subject patterns are restated
# here so Doctor keeps judging Marshal without Marshal's own code. Story
# 27.1 adds the templated-merge-subject shape, station-scoped via each
# project's own tracked ``marshal-policy.toml`` (read as TOML by
# ``_project_merge_subject_template``, never through ``pyforge.marshal``).

_GITHUB_MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+ from \S+?/(?P<branch>\S+)$")
_BMADLOOP_MERGE_SUBJECT_RE = re.compile(r"^Merge bmad-loop/\S+/(?P<key_slug>\S+) into (?P<target>\S+) \(bmad-loop\)$")
_STORY_ID_RE = re.compile(r"^(\d+)-(\d+[a-z]?)(?:-.*)?$")
_STORY_DOT_RE = re.compile(r"^(\d+)\.(\d+[a-z]?)$")

DIRECTION_LANDED_UNPROMOTED = "landed-but-unpromoted"
DIRECTION_DONE_UNMERGED = "done-but-unmerged"


def _story_id(token: str) -> str | None:
    """Normalize a ledger key or merge-segment to ``<epic>-<seq>``."""
    token = token.strip()
    m = _STORY_ID_RE.match(token)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = _STORY_DOT_RE.match(token)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return None


def _merged_ids_for_project(
    target: Path,
    commits: list[tuple[str, str]],
    project_slug: str,
    *,
    diff_cache: DiffCache,
    unreadable_diff_shas: list[str] | None = None,
) -> set[str]:
    """Story ids durably named in ``commits`` for ``project_slug``.

    Covers GitHub PR-merge, bmad-loop native, and templated merge subjects.
    The first two are scoped to the station short name / ``loop/<slug>``
    target. The templated shape is attempted unconditionally: since
    ``merge_subject_template`` is ``{slug}``-scoped fleet-wide by default
    (Story 50.4), ``parse_templated_merge_subject`` self-scopes internally —
    a subject rendered by ``project_slug``'s own template parses, and a
    sibling's subject rendered from a DIFFERENT slug's template segment
    (even one that resolves to the textually identical default template)
    refuses. ``Merge pyforge-atlas/13-5 into main`` counts for atlas; a
    sibling's own ``Merge pyforge-herald/13-5 into main`` does not, even
    though both projects share the same unset-override template string.

    Before Story 50.4, this templated shape was DELIBERATELY skipped
    whenever a project's resolved template equalled the (then station-blind)
    repo default, to avoid the live 2026-09-18 incident where wiring it in
    unconditionally turned 3 findings into 306 fleet-wide, because most
    stations shared the identical, contentless template and any one of them
    could match any other's subject. Story 50.4's slug-scoping is what
    removes that ambiguity at the source, so the guard that used to carry it
    is gone — see ``spec-pyforge-marshal`` CAP-247.

    Story 27.5 (CAP-80 amended): once the scoped template, GitHub PR-merge,
    and bmad-loop shapes above all miss, the bare legacy form
    (``Merge {key} into main``, no station token -- which can never match a
    ``{slug}`` template) is tried once more — attributed to ``project_slug``
    only when ``sha``'s first-parent diff touches this station's own paths
    AND this station's own tracked ledger already knows the extracted key
    (``bare_merge.attribute_bare_merge``, shared verbatim with
    ``sources/marshal.py``'s ``_keys_from_merge_subjects``/``_keys_from_
    main_commits``). Replaces Story 27.3's reverted ledger-membership-alone
    gate, which reopened the cross-station collision whenever two stations
    share a numeric key — the common case under one shared grammar. A
    sibling's own bare-form merge touches only the SIBLING's paths, so it
    still attributes to nothing here.
    """
    station = project_slug.removeprefix("pyforge-")
    template = _project_merge_subject_template(target, project_slug)
    known_keys = known_story_keys(target, project_slug)
    out: set[str] = set()
    for sha, subject in commits:
        templated = parse_templated_merge_subject(subject, template, project_slug)
        if templated is not None:
            out.add(templated.hyphen_form())
            continue
        gh = _GITHUB_MERGE_SUBJECT_RE.match(subject)
        if gh is not None:
            branch = gh.group("branch")
            if station and branch.startswith(f"{station}/"):
                segment = branch.rsplit("/", 1)[-1]
                sid = _story_id(segment)
                if sid:
                    out.add(sid)
            continue
        bl = _BMADLOOP_MERGE_SUBJECT_RE.match(subject)
        if bl is not None and bl.group("target") == f"loop/{project_slug}":
            sid = _story_id(bl.group("key_slug"))
            if sid:
                out.add(sid)
            continue
        attribution = attribute_bare_merge(
            subject,
            sha,
            target=target,
            project_slug=project_slug,
            known_keys=known_keys,
            cache=diff_cache,
        )
        if attribution.key is not None:
            out.add(attribution.key.hyphen_form())
        elif attribution.diff_unreadable_sha is not None and unreadable_diff_shas is not None:
            unreadable_diff_shas.append(attribution.diff_unreadable_sha)
    return out


def _base_done_ids(target: Path, rel_path: str, base_ref: str) -> set[str] | None:
    """Story ids already terminal in the ledger **as committed at
    ``base_ref``** — or ``None`` when the ledger does not exist there.

    This is the authoritative answer to "did this key's promotion land?",
    and it is why ``done-but-unmerged`` is no longer decided by merge-subject
    naming alone. A merge subject only names a story when the branch happened
    to be shaped ``<station>/<epic>-<seq>-…``; the fleet also lands work in
    batched ``chore/``, ``docs/``, ``dispatch/`` and ``maintenance/`` PRs
    whose subjects carry no story key at all. Judged on subjects alone, every
    key promoted by such a PR reads as never-merged: the check reported **383
    of 724 done stories** that way, all of them false, while the ledger at
    ``main`` said ``done`` for all 917 of them.

    Reading the committed blob keeps FR-138 intact — the oracle is still git,
    and still never ``implementation-artifacts/sprint-status.yaml``. It is in
    fact the stronger git evidence: the tracked artifact at the base commit,
    rather than a string heuristic over commit messages.

    ``None`` (ledger absent at ``base_ref``) is deliberately distinct from an
    empty set (ledger present, nothing done there): a ledger added on this
    branch has no base evidence either way, so the caller falls back to merge
    subjects rather than accusing every key in a brand-new file.
    """
    blob = _git(target, "show", f"{base_ref}:{rel_path}")
    if blob is None:
        return None
    out: set[str] = set()
    for raw_key, status in _parse_statuses(blob).items():
        sid = _story_id(raw_key)
        if sid is not None and status in TERMINAL:
            out.add(sid)
    return out


def _rekey_sid_maps(target: Path, rev: str) -> tuple[dict[str, dict[str, str]], list[Finding]]:
    """Per-project ``{old_story_id: new_story_id}`` from every re-key map
    tracked at ``rev`` (Story 27.2 / spec-27-2-ledger-direction-reads-the-
    stations-rekey-map).

    ``gather_direction`` compares at the ``<epic>-<seq>`` grain (``_story_id``
    ), never the full ledger key — a templated merge subject's ``{key}``
    placeholder captures no slug at all (see
    ``pyforge.core.landing_evidence.parse_templated_merge_subject``), so this
    reduces each map line's OLD and NEW side to that same grain rather than
    matching full keys. This is what lets a merge that names a station's OLD
    number (e.g. atlas's ``13-5`` before ``rekey-2026-09-17.md`` renumbered it
    to ``12-5``) still resolve to the CURRENT ledger's key before the
    landed-vs-done comparison, instead of reading as a phantom
    ``landed-but-unpromoted`` row forever.

    Reuses ``_rekey_paths``/``parse_rekey`` — the same discovery and grammar
    ``gather()`` already has — rather than re-implementing either. Unlike
    ``gather()``'s own ``_new_rekey_maps``, there is no base/head range here
    (``gather_direction`` has only one ref): every map CURRENTLY tracked at
    ``rev`` is in scope, not merely one freshly shipped by a range.

    An unreadable or malformed map degrades to a WARN ``Finding`` naming the
    file — never a silent pass, never a crash — under one check name,
    ``rekey-map-unreadable``, covering both "the blob would not read" and
    "the blob read but its grammar is broken." ``gather()``'s sibling
    reports the malformed case as a FAIL instead; here there is no landed
    range to hold accountable for it, only a degraded input to a comparison
    that has other evidence (a merge subject, or the base-ref ledger) to
    fall back on.
    """
    maps: dict[str, dict[str, str]] = {}
    problems: list[Finding] = []
    for path in _rekey_paths(target, rev):
        # `_rekey_paths` already filtered every entry through `_REKEY_RE`,
        # so the match can never be None here.
        project = _REKEY_RE.match(path).group(1)
        text = _git(target, "show", f"{rev}:{path}")
        if text is None:
            problems.append(
                Finding(
                    source=Source.LEDGER_DIRECTION,
                    check="rekey-map-unreadable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}: re-key map {path} is tracked at {rev} "
                        "but unreadable — landed-key translation for this "
                        "project may be incomplete"
                    ),
                    evidence={"project": project, "path": path},
                )
            )
            continue
        parsed: RekeyMap = parse_rekey(text)
        if not parsed.clean:
            bad = [f"line {no}: {txt.strip()!r}" for no, txt in parsed.malformed]
            bad += [f"line {no}: duplicate old key {old!r}" for no, old in parsed.duplicates]
            bad += [f"collision on new key {k!r}" for k in parsed.collisions]
            problems.append(
                Finding(
                    source=Source.LEDGER_DIRECTION,
                    check="rekey-map-unreadable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}: re-key map {path} has {len(bad)} "
                        f"unusable line(s): {'; '.join(bad[:5])} — "
                        "landed-key translation for this project may be "
                        "incomplete"
                    ),
                    evidence={"project": project, "path": path, "count": len(bad)},
                )
            )
        project_map = maps.setdefault(project, {})
        for old, new in parsed.mapping.items():
            old_sid = _story_id(old)
            new_sid = _story_id(new)
            if old_sid and new_sid:
                project_map[old_sid] = new_sid

    # A station can ship a SECOND rekey map that renumbers an already
    # renumbered sid (13-5 -> 12-5 in one file, 12-5 -> 11-5 in a later
    # one). Resolve every entry to its fixed point through its own map --
    # same hop-walk, same cap, as ``rekey.reverse_map`` -- so a merge naming
    # the OLDEST spelling still lands on the CURRENT one, not an
    # intermediate one that itself moved on.
    for project_map in maps.values():
        for old_sid in project_map:
            cur, hops = project_map[old_sid], 0
            while cur in project_map and hops < 64:
                cur = project_map[cur]
                hops += 1
            project_map[old_sid] = cur
    return maps, problems


def gather_direction(target: Path, *, base_ref: str = "main") -> tuple[Finding, ...]:
    """Judge tracked-ledger vs. git merge-history drift WITH DIRECTION
    (Story 15.2 / FR-137 / FR-138).

    Per project that has a tracked ``sprint-status-ledger.yaml``:

    * ``landed-but-unpromoted`` — a story id appears in ``main``'s merge
      subjects for this station but is not ``done`` in the twin (FAIL).
    * ``done-but-unmerged`` — a twin ``done`` key is **not** ``done`` in the
      ledger as committed at ``base_ref``, and no merge subject names it
      (WARN). The base-ref half is what makes this survivable: judged on
      merge subjects alone it fired on 383 of 724 done stories, every one of
      them landed by a batched PR whose subject named no story.

    Never opens ``implementation-artifacts/sprint-status.yaml``. Degrades
    to WARN when git is unavailable; OK when every twin agrees with git.

    Story 27.2: before the ``landed-but-unpromoted``/``done-but-unmerged``
    comparison, every merge-derived story id is translated through the
    station's own ``rekey-*.md`` map(s), if any (``_rekey_sid_maps``) — the
    same reader ``gather()`` already applies. Without it, a station that
    renumbered its stories (a fold PR) reads its own merges, which still
    name the pre-fold number, as ``landed-but-unpromoted`` forever.
    """
    if _git(target, "rev-parse", "--git-dir") is None:
        return (
            Finding(
                source=Source.LEDGER_DIRECTION,
                check="ledger-direction",
                status=DoctorStatus.WARN,
                message=(
                    f"git is unavailable or {target} is not a repository — ledger-vs-git direction cannot be checked"
                ),
                evidence={"target": str(target)},
            ),
        )

    # Story 27.5: carries the sha alongside each subject (was subject-only
    # pre-27.5) -- the bare-form fallback in `_merged_ids_for_project` needs
    # it to run `git diff --name-only <sha>^1 <sha>`.
    commits_raw = _git(target, "log", "--format=%H%x00%s", base_ref)
    if commits_raw is None:
        return (
            Finding(
                source=Source.LEDGER_DIRECTION,
                check="ledger-direction",
                status=DoctorStatus.WARN,
                message=(f"cannot read {base_ref!r} commit subjects — ledger-vs-git direction cannot be checked"),
                evidence={"target": str(target), "base_ref": base_ref},
            ),
        )
    commits: list[tuple[str, str]] = []
    for line in commits_raw.splitlines():
        if not line:
            continue
        sha, _, subject = line.partition("\0")
        if sha and subject:
            commits.append((sha, subject))
    # Shared across every project audited below -- a given sha's touched
    # station paths do not depend on which project is asking (see
    # ``bare_merge.DiffCache``'s own docstring).
    diff_cache: DiffCache = {}

    ledger_paths = sorted(p for p in target.glob(f"{PROJECTS_PREFIX}*/{LEDGER_SUFFIX}") if p.is_file())
    rekey_maps, rekey_problems = _rekey_sid_maps(target, base_ref)
    if not ledger_paths:
        return (
            *rekey_problems,
            Finding(
                source=Source.LEDGER_DIRECTION,
                check="ledger-direction",
                status=DoctorStatus.OK,
                message="no tracked sprint ledgers found — nothing to direction-check",
                evidence={"audited": 0},
            ),
        )

    findings: list[Finding] = []
    audited = 0
    findings.extend(rekey_problems)
    for path in ledger_paths:
        project = path.relative_to(target).parts[2]
        try:
            text = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            findings.append(
                Finding(
                    source=Source.LEDGER_DIRECTION,
                    check="ledger-direction",
                    status=DoctorStatus.WARN,
                    message=(f"{project}: tracked ledger unreadable — direction status unknown"),
                    evidence={"project": project, "path": str(path)},
                )
            )
            continue

        statuses = _parse_statuses(text)
        audited += 1
        done_ids: set[str] = set()
        raw_by_id: dict[str, str] = {}
        for raw_key, status in statuses.items():
            sid = _story_id(raw_key)
            if sid is None:
                continue
            raw_by_id.setdefault(sid, raw_key)
            if status in TERMINAL:
                done_ids.add(sid)

        unreadable_diff_shas: list[str] = []
        merged_ids = _merged_ids_for_project(
            target,
            commits,
            project,
            diff_cache=diff_cache,
            unreadable_diff_shas=unreadable_diff_shas,
        )
        for sha in sorted(set(unreadable_diff_shas)):
            # Story 27.5: the bare-form fallback's `git diff` failed for
            # this sha -- "cannot evaluate", never a silent non-match and
            # never a crash. Named individually (project + sha), mirroring
            # this function's existing per-item WARN Findings (e.g.
            # `ledger-unreadable`, `rekey-map-unreadable`) rather than
            # folded into a caveat string.
            findings.append(
                Finding(
                    source=Source.LEDGER_DIRECTION,
                    check="bare-merge-diff-unreadable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}: first-parent diff for {sha} could not "
                        "be read — a bare legacy-form merge subject naming "
                        "a key this project's ledger knows could not be "
                        "attributed"
                    ),
                    evidence={"project": project, "sha": sha},
                )
            )
        # Story 27.2: a merge subject names the OLD story id when the
        # station has since renumbered (a fold PR's rekey-*.md). Translate
        # through the station's own map before comparing, so a merge that
        # still names the pre-fold number resolves to what the CURRENT
        # ledger actually calls it, instead of reading as a phantom
        # landed-but-unpromoted row forever.
        sid_map = rekey_maps.get(project)
        if sid_map:
            merged_ids = {sid_map.get(sid, sid) for sid in merged_ids}

        for sid in sorted(merged_ids - done_ids):
            # A merged key absent from the twin entirely OR present but not
            # done is landed-but-unpromoted.
            findings.append(
                Finding(
                    source=Source.LEDGER_DIRECTION,
                    check="ledger-direction",
                    status=DoctorStatus.FAIL,
                    message=(
                        f"{project}/{raw_by_id.get(sid, sid)}: "
                        f"{DIRECTION_LANDED_UNPROMOTED} — merge history "
                        "names this story, but the tracked ledger is not "
                        "done"
                    ),
                    evidence={
                        "project": project,
                        "story_id": sid,
                        "key": raw_by_id.get(sid, sid),
                        "direction": DIRECTION_LANDED_UNPROMOTED,
                        "path": str(path.relative_to(target)),
                    },
                )
            )

        # A key counts as landed on either evidence: the ledger at base_ref
        # already says done, or a merge subject names it. The first is
        # authoritative and covers batched PRs; the second still catches a
        # story landed by a scoped PR whose promote commit has not been
        # published to base_ref yet.
        base_done = _base_done_ids(target, path.relative_to(target).as_posix(), base_ref)
        landed_ids = merged_ids | (base_done or set())
        base_evidence = "absent-at-base" if base_done is None else "ledger-at-base"

        for sid in sorted(done_ids - landed_ids):
            findings.append(
                Finding(
                    source=Source.LEDGER_DIRECTION,
                    check="ledger-direction",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}/{raw_by_id.get(sid, sid)}: "
                        f"{DIRECTION_DONE_UNMERGED} — tracked ledger says "
                        f"done, but the ledger at {base_ref!r} does not and "
                        "no scoped merge subject names it"
                    ),
                    evidence={
                        "project": project,
                        "story_id": sid,
                        "key": raw_by_id.get(sid, sid),
                        "direction": DIRECTION_DONE_UNMERGED,
                        "path": str(path.relative_to(target)),
                        "base_ref": base_ref,
                        "base_evidence": base_evidence,
                    },
                )
            )

    if findings:
        return tuple(findings)
    return (
        Finding(
            source=Source.LEDGER_DIRECTION,
            check="ledger-direction",
            status=DoctorStatus.OK,
            message=(f"tracked ledgers agree with {base_ref!r} merge history ({audited} ledger(s) audited)"),
            evidence={"audited": audited, "base_ref": base_ref},
        ),
    )
