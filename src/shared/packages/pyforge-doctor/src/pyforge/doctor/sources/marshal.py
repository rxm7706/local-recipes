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

One known exception, recorded rather than quietly implied: ``gather``'s
WORKING-TREE read (``ledger.read_text``) catches ``OSError`` only, so a ledger
holding a non-UTF-8 byte on disk still raises ``UnicodeDecodeError``. Every git-side
read in this module is guarded (see ``_git``); this one line pre-dates Story 6.4 and
sits inside the shipped ``MARSHAL_DURABILITY`` check that 6.4's spec puts off-limits,
so the fix is recorded in ``deferred-work.md`` rather than taken here.
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


def _git(target: Path, *args: str, timeout: float | None = None) -> str | None:
    """``git`` stdout, or None on any failure.

    Routes through ``cli_bridge.run_git`` — AD-5 makes that module the SOLE
    subprocess site in the package, enforced by
    ``tests/meta/test_cli_bridge_sole_subprocess.py``. The first cut of this module
    called ``subprocess`` directly and that meta-test caught it.

    ``timeout=None`` means "whatever ``run_git``'s own default is" -- the kwarg is
    genuinely not forwarded in that case, rather than restating the default as a
    literal here (which would silently pin the old value if ``run_git``'s default
    ever moved). ``gather_story_status``'s ``git log`` calls pass ``timeout=60.0``
    to match ``scripts/story_status_check.py``'s own ``sh()`` helper exactly;
    every other call site in this module is unaffected.

    Never raises: a missing binary, a non-repo target and a failed command are all
    "cannot evaluate", which this module reports as a WARN Finding rather than
    crashing on — the house rule for every Doctor source. ``UnicodeDecodeError``
    is caught alongside ``CliBridgeError`` because ``run_git`` decodes with
    ``text=True`` and catches only ``TimeoutExpired``/``OSError``, so non-UTF-8
    git output would otherwise raise straight out of the gather (see
    ``sources/ledger.py``'s own ``_git`` for the verified repro; the shared fix
    in ``cli_bridge`` stays recorded in ``deferred-work.md``).
    """
    kwargs = {} if timeout is None else {"timeout": timeout}
    try:
        return run_git(target, list(args), **kwargs)
    except (CliBridgeError, UnicodeDecodeError):
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
            # `_git` collapses EVERY failure to None, so "HEAD does not track
            # this path" and "HEAD tracks it but the blob would not decode"
            # arrive identically — and reporting the second as the first tells
            # the operator to commit a file that IS committed, while the
            # regression comparison is skipped in silence. Ask git which it is;
            # only on this already-failing path, so the healthy case pays
            # nothing.
            listed = _git(target, "ls-tree", "--name-only", "HEAD", "--", rel)
            if listed and listed.strip():
                findings.append(Finding(
                    source=Source.MARSHAL_DURABILITY,
                    check="ledger-unreadable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}: sprint ledger is committed but its blob at HEAD "
                        f"could not be read — regression cannot be evaluated"
                    ),
                    evidence={"project": project, "path": rel},
                ))
                continue
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


def _harness_tasks(
    loop_root: Path | None,
    slug: str,
    *,
    skipped: set[str] | None = None,
    unreadable: list[str] | None = None,
) -> dict[str, dict]:
    """Most-advanced run record per story key, across every run of a station.

    Two optional out-parameters record what was DROPPED, because a dropped
    record is indistinguishable downstream from "this story has no run record
    at all" -- the detector's SILENT branch -- so without them the
    corrupt-harness case (the exact state a broken loop run leaves behind)
    turns a potential false-green into a clean pass with nothing to show for
    it. They are separate because they support different claims:

    * ``skipped`` collects the story KEYS whose entry was malformed. The caller
      intersects it with the keys it actually audited, so the count it reports
      is precisely "audited stories whose record was unusable".
    * ``unreadable`` collects the ``state.json`` PATHS that could not be read or
      parsed at all -- a truncated file, the likeliest corruption a killed loop
      run leaves, has no keys to attribute, so it can only be counted as a
      file. Counting it nowhere was the gap: the whole-file branch was the one
      the counter was written for and the one it missed.

    Both are optional so the plain two-arg call keeps working unchanged.
    ``loop_root=None`` means the harness root could not be determined at all
    (see ``gather_story_status``) and yields no records rather than raising.

    'Most advanced' = prefer a record carrying a ``commit_sha``, since a
    later run can re-drive a story an earlier run deferred. Port of
    ``scripts/story_status_check.py``'s own ``harness_tasks`` -- reads ONLY
    host filesystem state (``pathlib``/``json``, no git, no subprocess), and
    a missing or corrupt ``state.json`` is silently skipped rather than
    raising, mirroring the script's own broad try/except-and-continue.
    """
    out: dict[str, dict] = {}
    if loop_root is None:
        return out
    home = loop_root / f"pyforge-{slug}"
    for state in sorted(home.glob(".bmad-loop/runs/*/state.json")):
        # Only the READ+PARSE is guarded by try/except: an unreadable file or
        # invalid JSON makes the whole record unusable, so that file is skipped
        # whole. A WARN Finding would misattribute a per-run read failure to the
        # story-status verdict itself, so this degrades silently instead
        # (mirrors the source script's own try/except-and-continue).
        try:
            payload = json.loads(state.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 -- corrupt/unreadable run record
            if unreadable is not None:
                unreadable.append(str(state))
            continue

        # SHAPE guards are per-entry and OUTSIDE the try, deliberately. Folding
        # the loop into the try above looks equivalent but is not, twice over:
        # (a) `prev is None or task.get(...)` short-circuits on a key's FIRST
        # sighting, so a non-dict task value is stored without `.get` ever being
        # evaluated -- it then detonates in `gather_story_status`'s own
        # `task.get("commit_sha")` instead, where nothing catches it (the exact
        # AttributeError this guard exists to prevent); and (b) an exception
        # mid-iteration would discard every remaining entry in that file, so one
        # malformed record would silently un-audit its healthy neighbours. Both
        # violate this module's "degrades, never crashes" rule. `isinstance` is
        # the honest guard: skip exactly the malformed entry, keep the rest.
        tasks = payload.get("tasks") if isinstance(payload, dict) else None
        if not isinstance(tasks, dict):
            if unreadable is not None:
                unreadable.append(str(state))
            continue
        for key, task in tasks.items():
            if not isinstance(task, dict):
                if skipped is not None:
                    skipped.add(key)
                continue  # malformed entry -- skip it, keep its neighbours
            prev = out.get(key)
            if prev is None or (task.get("commit_sha") and not prev.get("commit_sha")):
                out[key] = task
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
    script's own hardcoded ``LOOP_ROOT``. ``Path.home()`` itself RAISES
    ``RuntimeError`` when ``HOME`` is unset and the uid has no passwd entry
    (the ordinary rootless-container shape), which would escape this gather
    before any Finding could be built, so it degrades to "no harness records
    visible" instead. Tier-3 feeds
    (``_bmad-output/projects/pyforge-*/implementation-artifacts/
    sprint-status.yaml``) are gitignored, so in a bare CI checkout this glob
    finds nothing and the gather degrades to a vacuous ``audited=0`` OK
    Finding rather than crashing.

    Feeds present but git unusable is the one case that must NOT fall through:
    two of the three evidence routes are git queries, so an ungathered answer
    would read as "no evidence found" and convict a genuinely-landed story.
    That case returns a single WARN instead — cannot-evaluate is never a FAIL.
    """
    if loop_root is None:
        try:
            loop_root = Path.home() / ".bmad-loops"
        except RuntimeError:
            loop_root = None  # no resolvable home -- no harness records to read

    feeds = sorted(target.glob(SPRINT_STATUS_GLOB))

    # Two of the three landing-evidence routes are git queries. With git absent
    # or `target` not a repository, both fail closed -- and a story would fall
    # through to the `phase in NOT_LANDED` test and be ACCUSED of being a false
    # green on the strength of evidence that was never actually gathered. That
    # is the one outcome this detector must never produce, so "cannot evaluate"
    # is reported as WARN instead, mirroring the probe `gather()` above already
    # runs for exactly the same reason. Probed only when feeds exist, so the
    # no-feeds case still degrades to the vacuous audited=0 OK.
    if feeds and _git(target, "rev-parse", "--git-dir") is None:
        return (
            Finding(
                source=Source.STORY_STATUS,
                check="story-status",
                status=DoctorStatus.WARN,
                message=(
                    f"{len(feeds)} sprint feed(s) present but git is unavailable "
                    f"or {target} is not a repository — landing evidence cannot "
                    f"be checked"
                ),
                evidence={"target": str(target), "feeds": len(feeds), "audited": 0},
            ),
        )

    # Route 3 asks one question of `main`'s whole history, and the answer is
    # identical for every key in every feed (`target` never changes mid-gather).
    # Computed once, lazily, on the first key that actually reaches Route 3 --
    # a full history walk per candidate key would be O(keys x history) shell-outs
    # against Doctor's own NFR-4 wall-clock budget. `None` means "not computed
    # yet"; the separate `_unavailable` flag means "computed, and the query
    # FAILED" -- an empty list is a legitimate answer (a repo with no subjects)
    # and must not be confused with either.
    main_subjects: list[str] | None = None
    main_subjects_unavailable = False

    false_greens: list[dict] = []
    audited = 0
    no_record = 0
    unreadable_records = 0
    inconclusive = 0
    unverified = 0
    unreadable_run_files: list[str] = []
    unreadable_feeds = 0
    for feed in feeds:
        slug = feed.parent.parent.name.removeprefix("pyforge-")
        # Per-station, not shared across feeds: story keys are only unique
        # WITHIN a station, so a global set would let one station's malformed
        # `1-1-foo` be charged to another station's healthy `1-1-foo`.
        station_skipped: set[str] = set()
        tasks = _harness_tasks(
            loop_root, slug, skipped=station_skipped, unreadable=unreadable_run_files
        )
        try:
            text = feed.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # This drops a whole station from the audit. The OK Finding must
            # not then read as a confident green over a station it never
            # opened, so the caveat below names it. (Escalating to WARN and
            # putting the count in `evidence` would change the OK Finding's
            # evidence shape, which the spec's I/O matrix pins -- that decision
            # stays recorded in `deferred-work.md`.)
            unreadable_feeds += 1
            continue

        for key in DONE_RE.findall(text):
            audited += 1
            task = tasks.get(key)
            if task is None:
                # Two different absences, and the caveat must not merge them: a
                # story whose record was DROPPED as malformed was not "never
                # recorded", it was recorded and unreadable.
                if key in station_skipped:
                    unreadable_records += 1
                else:
                    no_record += 1  # pre-loop or hand-implemented. Stay silent.
                continue
            if task.get("commit_sha"):
                continue  # harness recorded a commit

            # `_git` returns None on FAILURE and "" on "ran, found nothing".
            # Collapsing the two would convict a story on evidence that was
            # never gathered -- the one outcome this detector must never
            # produce (the same rule the git-dir probe above enforces, applied
            # per query rather than once).
            merged = _git(
                target, "log", "--oneline", "--all", "-F", f"--grep=/{key} into",
                timeout=60.0,
            )
            if merged is None:
                inconclusive += 1
                continue
            if merged:
                continue  # merge commit found

            # Route 3: landed BY HAND, reachable from main -- see the source
            # script's own docstring for why this must be a commit SUBJECT
            # (not anywhere in the message) naming both the slug and the
            # `Story <epic>.<seq>` phrase.
            m = re.match(r"^(\d+)-(\d+)-", key)
            if m:
                needle = f"story {m.group(1)}.{m.group(2)}"
                if main_subjects is None and not main_subjects_unavailable:
                    raw = _git(target, "log", "--format=%s", "main", timeout=60.0)
                    if raw is None:
                        # No local `main` (a PR checkout, a shallow clone, a
                        # differently-named default branch) or a failed query.
                        # Route 3 cannot run, so this key cannot be judged.
                        main_subjects_unavailable = True
                    else:
                        main_subjects = raw.lower().splitlines()
                if main_subjects_unavailable:
                    inconclusive += 1
                    continue
                if any(slug in s and needle in s for s in main_subjects or ()):
                    continue  # hand-landed; named in a commit subject on main

            phase = task.get("phase", "")
            # `phase in NOT_LANDED` HASHES `phase`, so a JSON record giving it a
            # list or dict value raised TypeError straight out of the gather --
            # the container guard in `_harness_tasks` validates the task dict,
            # never the values inside it.
            if isinstance(phase, str) and phase in NOT_LANDED:
                false_greens.append({
                    "slug": slug, "key": key, "phase": phase,
                    "defer_reason": task.get("defer_reason") or "",
                })
            else:
                # A record exists, no landing evidence was found, and the
                # harness does not say the story failed either. Not an
                # accusation -- but not a verified landing, so it must not be
                # counted into the green's silent majority.
                unverified += 1

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

    # The source script printed a flat "OK: every `done` story is backed by a
    # merge commit or a recorded commit sha." and offered `--verbose` to show
    # the `(no run record -- hand-landed or pre-loop)` rows behind it. The port
    # inherited the claim and dropped the surface that qualified it, so the
    # message asserted landing evidence for stories it deliberately never
    # checked: measured live against this repo, 19 of 27 audited keys had NO run
    # record at all and were passed on the silent branch. What this gather
    # actually establishes is the weaker (and true) "nothing CONTRADICTS its
    # landing evidence", so that is what it now says, with the breakdown that
    # was previously only reachable via --verbose folded into the message.
    #
    # The breakdown lives in the message rather than in `evidence` on purpose:
    # the spec's I/O matrix pins this Finding's evidence to exactly
    # `{"audited": 0}` for the no-feeds row, so widening the shape here would
    # be a spec deviation. Enriching it stays recorded in `deferred-work.md`
    # for the story that owns the contract.
    # Every clause names a population the audit did NOT verify, and each is
    # counted exactly once against `audited` (or, for the two input-level
    # clauses, reported as inputs rather than as stories) -- an earlier form
    # could print "1 audited, 3 run record(s) unreadable" by charging records
    # for keys no feed ever listed.
    detail = f"{audited} audited"
    if no_record:
        detail += f", {no_record} with no run record (unchecked)"
    if unreadable_records:
        detail += f", {unreadable_records} with an unreadable run record"
    if inconclusive:
        detail += f", {inconclusive} whose git landing evidence could not be queried"
    if unverified:
        detail += f", {unverified} with no landing evidence and no harness verdict"
    if unreadable_run_files:
        detail += f", {len(unreadable_run_files)} run record file(s) unreadable"
    if unreadable_feeds:
        detail += f", {unreadable_feeds} sprint feed(s) unreadable"
    return (
        Finding(
            source=Source.STORY_STATUS,
            check="story-status",
            status=DoctorStatus.OK,
            message=f"no `done` story contradicts its landing evidence ({detail})",
            evidence={"audited": audited},
        ),
    )
