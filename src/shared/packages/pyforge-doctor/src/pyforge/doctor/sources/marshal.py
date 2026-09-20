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
import tomllib
from collections.abc import Callable
from pathlib import Path

from pyforge.core.landing_evidence import (
    StoryKeyRef,
    classify_branch_name,
    classify_commit,
    parse_bmadloop_merge_subject,
    parse_github_pr_merge_subject,
    parse_recovery_commit_subject,
    parse_templated_merge_subject,
)

from ..bare_merge import DiffCache, attribute_bare_merge, known_story_keys
from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from ..rekey import load_rekey_maps, reverse_map

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
# Repo-default template (Story 50.4), shared with
# ``pyforge.core.landing_evidence`` conformance. Carries a ``{slug}`` token,
# so ``parse_templated_merge_subject`` self-scopes a subject rendered from it
# to the project that rendered it -- ``_project_merge_subject_template``
# below is the per-project override this module reads FIRST (Story 27.1);
# this constant is only the fallback for a project whose policy declares
# none.
_MERGE_SUBJECT_TEMPLATE = "Merge {slug}/{key} into main"
_MARSHAL_POLICY_SUFFIX = "planning-artifacts/marshal-policy.toml"
_FEED_KEY_RE = re.compile(r"^(\d+)-(\d+)([a-z])?-")


def _project_merge_subject_template(target: Path, project_slug: str) -> str:
    """``project_slug``'s own ``merge_subject_template``, read directly from
    its tracked ``marshal-policy.toml`` as TOML -- never through
    ``pyforge.marshal`` (this module's independence rule, see the module
    docstring). Degrades to the repo default when the policy file is
    absent, unreadable, not valid TOML, or does not declare the key --
    "degrades, never crashes," and Story 27.1's own "policy declares no
    template -> default honoured" row. Duplicated in
    ``sources/ledger.py`` rather than shared via a cross-import, mirroring
    this module's own ``_git``/``_parse_statuses`` precedent of small,
    per-file self-contained helpers over sibling-module coupling.
    """
    path = target / PROJECTS_REL / project_slug / _MARSHAL_POLICY_SUFFIX
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return _MERGE_SUBJECT_TEMPLATE
    value = data.get("merge_subject_template")
    return value if isinstance(value, str) and value else _MERGE_SUBJECT_TEMPLATE


# GitHub PR-merge subject shape retained only to extract the ``branch`` token
# for ``land/<station>-<epic>-<seq>`` / ``bmad-loop/<run>/<key>`` recovery
# landings whose merge commit subject does not carry a station-prefixed
# branch segment -- ``pyforge.core.landing_evidence.parse_github_pr_merge_
# subject`` handles the ordinary ``<station>/<key>-<desc>``/``dispatch/
# <project_slug>/<key>`` case inside the shared grammar; this module cannot
# import that private regex (module independence rule, see this file's own
# docstring), so it is duplicated here exactly as ``pyforge.marshal.core.
# promotion._classify_merge_subject`` already does for the identical reason
# (verified live 2026-08-28: doctor's story-status Routes 2/3 were missing
# this fallback entirely, producing a false-positive FAIL finding for every one of 25
# genuinely-landed stories audited that session -- marshal's own port of
# the same grammar already had it).
_GITHUB_MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+ from \S+?/(?P<branch>\S+)$")


def _feed_key_to_ref(key: str) -> StoryKeyRef | None:
    match = _FEED_KEY_RE.match(key)
    if match is None:
        return None
    return StoryKeyRef(
        epic=int(match.group(1)),
        seq=int(match.group(2)),
        suffix=match.group(3) or "",
    )


def _loose_subject_key_match(
    subjects: tuple[tuple[str, str], ...] | list[tuple[str, str]],
    *,
    station: str,
    key_ref: StoryKeyRef,
) -> bool:
    """Best-effort, LAST-RESORT landing check: does any commit subject
    mention this station AND this exact numeric key together, in any
    phrasing at all?

    The strict grammar (`_keys_from_merge_subjects`/`_keys_from_main_
    commits`) requires an anchored shape; real hand-authored landing
    commits vary far more than any fixed set of regexes can enumerate
    (``"<station>: promote story <e>.<s> to done..."``,
    ``"<station>: reconcile ... for Story <e>.<s>, ..."``,
    ``"land <station> <e>.<s>+<e2>.<s2> (N stories): ..."``, etc. -- all
    confirmed live 2026-08-28 as real landing commits for stories this
    detector still flagged after the branch-name fallback above). This
    route is deliberately loose (no anchor, no leading-token requirement)
    but still requires BOTH the station name and the EXACT epic.seq pair
    as their own tokens (never a digit substring of a longer number) --
    scoped ONLY to this advisory detector (never wired into
    ``pyforge.core.landing_evidence``, so it cannot loosen any
    safety-critical marshal gating decision that shares the strict
    grammar)."""
    station_re = re.compile(rf"\b{re.escape(station)}\b", re.IGNORECASE)
    epic, seq, suffix = key_ref.epic, key_ref.seq, key_ref.suffix
    # A trailing-letter guard, not just the digit one: without it, a bare
    # "11.1" in a commit subject would equally satisfy a search for the
    # SUFFIXED sibling key "11-1a" (split-story convention, StoryKeyRef.
    # suffix), and a search for plain "11-1" would equally accept a subject
    # that actually names "11.1a" -- two genuinely different stories.
    key_re = re.compile(rf"(?<!\d){epic}[.\-]{seq}{re.escape(suffix)}(?![\da-zA-Z])")
    for item in subjects:
        subject = item[1] if isinstance(item, tuple) else item
        if station_re.search(subject) and key_re.search(subject):
            return True
    return False


def _branch_name_fallback_key(subject: str, project_slug: str) -> StoryKeyRef | None:
    """A GitHub PR merge subject whose branch is ``land/<station>-<epic>-<seq>``
    or a bare ``bmad-loop/<run>/<key>`` -- shapes ``parse_github_pr_merge_
    subject`` does not recognize (it scopes on ``<station>/``/``dispatch/
    <project_slug>/`` branch prefixes only). Mirrors ``pyforge.marshal.core.
    promotion._classify_merge_subject``'s own fallback."""
    match = _GITHUB_MERGE_SUBJECT_RE.match(subject)
    if match is None:
        return None
    branch_match = classify_branch_name(match.group("branch"), project_slug=project_slug)
    return branch_match.key if branch_match is not None else None


def _keys_from_merge_subjects(
    target: Path,
    commits: tuple[tuple[str, str], ...],
    *,
    project_slug: str,
    diff_cache: DiffCache,
    unreadable_diff_shas: list[tuple[str, str]] | None = None,
) -> frozenset[StoryKeyRef]:
    """Merge-shaped subjects on any ref (route 2) -- excludes story-direct.

    The templated shape (tried first) uses ``project_slug``'s own override
    when its policy declares one (Story 27.1), else the ``{slug}``-scoped
    repo default (Story 50.4) -- either way ``parse_templated_merge_subject``
    self-scopes the read to ``project_slug``, so a sibling station's landing
    rendered from the textually identical default template still refuses.

    Story 27.5 (CAP-80 amended): once every scoped shape above misses, the
    AD-24 bare legacy form (``Merge {key} into main``) is tried once more --
    attributed to ``project_slug`` only when ``sha``'s first-parent diff
    touches this station's own paths AND this station's own tracked ledger
    already knows the extracted key (``bare_merge.attribute_bare_merge``,
    shared verbatim with ``sources/ledger.py::_merged_ids_for_project``).
    Replaces Story 27.3's reverted ledger-membership-alone gate, which
    reopened the cross-station collision whenever two stations share a
    numeric key -- the common case under one shared grammar.

    Before Story 50.4 the repo default was the bare, station-blind
    ``Merge {key} into main``, so a project with NO override of its own had
    the templated parser skipped entirely (trying it against that default
    matched every OTHER station's bare-form merge too -- this module's own
    pre-27.5 defect: unconditional and unscoped). The ``{slug}`` default
    removes that ambiguity at the source, so the parser now runs for every
    project; a bare legacy subject can never match a ``{slug}`` template and
    so always reaches the corroborated fallback below. ``commits`` therefore
    carries the sha alongside each subject (routed from ``git log
    --format=%H%x00%s``), unlike this function's pre-27.5 subject-only
    shape.
    """
    template = _project_merge_subject_template(target, project_slug)
    known_keys = known_story_keys(target, project_slug)
    keys: set[StoryKeyRef] = set()
    for sha, subject in commits:
        parsers: list[Callable[[str], StoryKeyRef | None]] = []
        parsers.append(lambda s: parse_templated_merge_subject(s, template, project_slug))
        parsers.extend(
            (
                lambda s: parse_github_pr_merge_subject(s, project_slug),
                lambda s: parse_bmadloop_merge_subject(s, project_slug),
                lambda s: parse_recovery_commit_subject(s, project_slug),
                lambda s: _branch_name_fallback_key(s, project_slug),
            )
        )
        for parser in parsers:
            key = parser(subject)
            if key is not None:
                keys.add(key)
                break
        else:
            attribution = attribute_bare_merge(
                subject,
                sha,
                target=target,
                project_slug=project_slug,
                known_keys=known_keys,
                cache=diff_cache,
            )
            if attribution.key is not None:
                keys.add(attribution.key)
            elif attribution.diff_unreadable_sha is not None and unreadable_diff_shas is not None:
                unreadable_diff_shas.append((project_slug, attribution.diff_unreadable_sha))
    return frozenset(keys)


def _keys_from_main_commits(
    target: Path,
    commits: list[tuple[str, str]],
    *,
    project_slug: str,
    diff_cache: DiffCache,
    unreadable_diff_shas: list[tuple[str, str]] | None = None,
) -> frozenset[StoryKeyRef]:
    template = _project_merge_subject_template(target, project_slug)
    known_keys = known_story_keys(target, project_slug)
    keys: set[StoryKeyRef] = set()
    for sha, subject in commits:
        match = classify_commit(
            sha,
            subject,
            template=template,
            project_slug=project_slug,
        )
        # Every shape `classify_commit` recognizes is trusted unconditionally:
        # the templated shape is self-scoped by `{slug}` (Story 50.4), so a
        # project with no override of its own can no longer match a sibling's
        # subject through the repo default it was handed (the pre-50.4 guard
        # that lived here -- see `_keys_from_merge_subjects`'s own docstring).
        if match is not None:
            keys.add(match.key)
            continue
        fallback = _branch_name_fallback_key(subject, project_slug)
        if fallback is not None:
            keys.add(fallback)
            continue
        # Story 27.5 (CAP-80 amended): same corroborated bare-form fallback
        # as `_keys_from_merge_subjects` above, tried once the strict
        # grammar and the branch-name fallback both miss -- see that
        # function's own docstring for the full rationale.
        attribution = attribute_bare_merge(
            subject,
            sha,
            target=target,
            project_slug=project_slug,
            known_keys=known_keys,
            cache=diff_cache,
        )
        if attribution.key is not None:
            keys.add(attribution.key)
        elif attribution.diff_unreadable_sha is not None and unreadable_diff_shas is not None:
            unreadable_diff_shas.append((project_slug, attribution.diff_unreadable_sha))
    return frozenset(keys)


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
    except CliBridgeError, UnicodeDecodeError:
        return None


def _parse_sha_subject_lines(raw: str) -> list[tuple[str, str]]:
    """``git log --format=%H%x00%s`` stdout -> ``(sha, subject)`` pairs.

    Shared by both Route 2's (``--all``) and Route 3's (``main``) fetches --
    identical NUL-delimited shape, so the split logic lives once.
    """
    out: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if not line:
            continue
        sha, _, subject = line.partition("\0")
        if sha and subject:
            out.append((sha, subject))
    return out


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
        return sorted(p / LEDGER_REL for p in projects.iterdir() if (p / LEDGER_REL).is_file())
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
        return (
            Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-inventory",
                status=DoctorStatus.WARN,
                message=(
                    f"no tracked sprint ledger found under {PROJECTS_REL}/*/{LEDGER_REL} "
                    f"— Marshal's durability guarantee cannot be evaluated here"
                ),
                evidence={"target": str(target), "ledgers": 0},
            ),
        )

    if _git(target, "rev-parse", "--git-dir") is None:
        return (
            Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-regression",
                status=DoctorStatus.WARN,
                message=(
                    f"{len(ledgers)} tracked ledger(s) present but git is unavailable or "
                    f"{target} is not a repository — regression cannot be evaluated"
                ),
                evidence={"target": str(target), "ledgers": len(ledgers)},
            ),
        )

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
                findings.append(
                    Finding(
                        source=Source.MARSHAL_DURABILITY,
                        check="ledger-unreadable",
                        status=DoctorStatus.WARN,
                        message=(
                            f"{project}: sprint ledger is committed but its blob at HEAD "
                            f"could not be read — regression cannot be evaluated"
                        ),
                        evidence={"project": project, "path": rel},
                    )
                )
                continue
            findings.append(
                Finding(
                    source=Source.MARSHAL_DURABILITY,
                    check="ledger-untracked",
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project}: sprint ledger exists on disk but is not committed — "
                        f"CI and every fresh clone are blind to its completions"
                    ),
                    evidence={"project": project, "path": rel},
                )
            )
            continue

        try:
            working = ledger.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.MARSHAL_DURABILITY,
                    check="ledger-unreadable",
                    status=DoctorStatus.WARN,
                    message=f"{project}: sprint ledger could not be read ({exc})",
                    evidence={"project": project, "path": rel},
                )
            )
            continue

        before, after = _parse_statuses(committed), _parse_statuses(working)
        lost = [(k, v) for k, v in sorted(before.items()) if v in TERMINAL and after.get(k) not in TERMINAL]
        if lost:
            total_lost += len(lost)
            findings.append(
                Finding(
                    source=Source.MARSHAL_DURABILITY,
                    check="ledger-regression",
                    status=DoctorStatus.FAIL,
                    message=(
                        f"{project}: {len(lost)} story(ies) un-finished relative to the "
                        f"committed ledger — a completion that was durable is not any more"
                    ),
                    evidence={
                        "project": project,
                        "path": rel,
                        "count": len(lost),
                        "keys": [k for k, _ in lost[:20]],
                        "remedy": f"git checkout HEAD -- {rel}",
                    },
                )
            )

    if not findings:
        findings.append(
            Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-regression",
                status=DoctorStatus.OK,
                message=(
                    f"{len(ledgers)} tracked ledger(s) hold every completion they held at HEAD — no story un-finished"
                ),
                evidence={"ledgers": len(ledgers), "regressed": 0},
            )
        )
    elif total_lost:
        findings.append(
            Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-regression-total",
                status=DoctorStatus.FAIL,
                message=(
                    f"{total_lost} completion(s) lost across "
                    f"{sum(1 for f in findings if f.check == 'ledger-regression')} ledger(s)"
                ),
                evidence={"lost": total_lost, "ledgers": len(ledgers)},
            )
        )
    return tuple(findings)


def _published_story_tasks(slug: str) -> dict[str, dict] | None:
    """Published-plane task records when reachable; None triggers filesystem fallback."""
    try:
        from pyforge.core.published_loop import fetch_story_tasks
    except ImportError:
        return None
    try:
        return fetch_story_tasks(slug)
    except Exception:  # noqa: BLE001 -- degrade to loop-home fallback
        return None


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
    published = _published_story_tasks(slug)
    if published is not None:
        return published
    out: dict[str, dict] = {}
    if loop_root is None:
        return out
    home = loop_root / f"pyforge-{slug}"
    # CAP-4: loop-home FILE read -- story-status fallback when published plane is unreachable
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


def gather_story_status(target: Path, *, loop_root: Path | None = None) -> tuple[Finding, ...]:
    """Judge whether every ``done`` story in every station's Tier-3 sprint
    feed is backed by real landing evidence -- the library form of
    ``scripts/story_status_check.py``'s own ``main()``, minus the print/exit
    CLI surface.

    A ``done`` story is confirmed landed if any of three routes holds: the
    harness recorded a ``commit_sha`` for it; a merge commit on any ref matches
    the shared landing-evidence grammar (FR-191 / Story 20.9); or a commit on
    ``main`` matches the same grammar (recovery subjects, story-direct commits,
    pre-convention allowlist, and the other sanctioned shapes). It is reported
    ONLY when none of those hold AND the harness positively says the story is
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

    Premise note (2026-08-22, text-only — marshal Story 25.5): BMAD 6.11's
    build-auto finalize writes ``done`` only at TRUE finalize (post-review),
    no longer at dev completion, so the dev-marks-done window this detector
    was built to contain has shrunk on 6.11-era runs. It has not closed —
    pre-6.11 feeds, interrupted runs, and any non-finalize writer keep the
    premise live — so detector behavior and containment are unchanged.
    """
    if loop_root is None:
        try:
            # CAP-4: loop-home FILE read -- default harness root when published plane unavailable
            loop_root = Path.home() / ".bmad-loops"
        except RuntimeError:
            loop_root = None  # no resolvable home -- no harness records to read

    feeds = sorted(target.glob(SPRINT_STATUS_GLOB))
    # Story 25.3 (spec-one-chain-per-station CAP-3(g)): a station fold
    # renumbers every story key and ships planning-artifacts/rekey-<date>.md.
    # Landing evidence (harness record, merge subject, main commit) was
    # written under the OLD spelling, so a renumbered `done` story is
    # confirmed by evidence under any earlier spelling the maps record.
    # Tracked maps are durable provenance: read every one, always.
    rekey_maps = load_rekey_maps(target)

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

    # Routes 2 and 3 ask git questions whose answers are identical for every
    # key in every feed. Computed once, lazily -- a full history walk per
    # candidate key would be O(keys x history) shell-outs against Doctor's
    # NFR-4 wall-clock budget.
    all_ref_commits: tuple[tuple[str, str], ...] | None = None
    all_ref_subjects_unavailable = False
    main_commits: list[tuple[str, str]] | None = None
    main_commits_unavailable = False
    # Story 27.5: the bare-form fallback's `git diff` per merge sha, shared
    # across EVERY key/route this run audits (a given sha's touched station
    # paths do not depend on which key or project is asking) -- see
    # ``bare_merge.DiffCache``'s own docstring.
    diff_cache: DiffCache = {}
    # (project_slug, sha) pairs -- carries the project so the standalone WARN
    # Finding below can name it, mirroring ``sources/ledger.py``'s own
    # per-sha WARN Finding shape.
    unreadable_diff_shas: list[tuple[str, str]] = []

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
        tasks = _harness_tasks(loop_root, slug, skipped=station_skipped, unreadable=unreadable_run_files)
        earlier_spellings = reverse_map(rekey_maps.get(f"pyforge-{slug}", []))
        try:
            text = feed.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
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
            aliases = (key, *earlier_spellings.get(key, ()))
            task = next((tasks[a] for a in aliases if a in tasks), None)
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

            key_ref = _feed_key_to_ref(key)
            key_refs = tuple(r for r in (_feed_key_to_ref(a) for a in aliases) if r is not None)
            project_slug = f"pyforge-{slug}"

            # Route 2: commit subjects on any ref, via shared landing-evidence
            # grammar (replaces the private ``/{key} into`` grep dialect).
            # Story 27.5: carries the sha alongside each subject (was
            # subject-only pre-27.5) -- the bare-form fallback needs it.
            if all_ref_commits is None and not all_ref_subjects_unavailable:
                raw = _git(
                    target,
                    "log",
                    "--format=%H%x00%s",
                    "--all",
                    timeout=60.0,
                )
                if raw is None:
                    all_ref_subjects_unavailable = True
                else:
                    all_ref_commits = tuple(_parse_sha_subject_lines(raw))
            if all_ref_subjects_unavailable:
                inconclusive += 1
                continue
            if key_refs and all_ref_commits is not None:
                merged_keys = _keys_from_merge_subjects(
                    target,
                    all_ref_commits,
                    project_slug=project_slug,
                    diff_cache=diff_cache,
                    unreadable_diff_shas=unreadable_diff_shas,
                )
                if any(r in merged_keys for r in key_refs):
                    continue  # merge evidence found (under any spelling)

            # Route 3: commits reachable from ``main``, via the same grammar
            # (replaces the private ``<slug>`` + ``story <e>.<s>`` subject
            # needle dialect).
            if key_ref is not None:
                if main_commits is None and not main_commits_unavailable:
                    raw = _git(
                        target,
                        "log",
                        "--format=%H%x00%s",
                        "main",
                        timeout=60.0,
                    )
                    if raw is None:
                        main_commits_unavailable = True
                    else:
                        main_commits = _parse_sha_subject_lines(raw)
                if main_commits_unavailable:
                    inconclusive += 1
                    continue
                if main_commits is not None:
                    main_keys = _keys_from_main_commits(
                        target,
                        main_commits,
                        project_slug=project_slug,
                        diff_cache=diff_cache,
                        unreadable_diff_shas=unreadable_diff_shas,
                    )
                    if any(r in main_keys for r in key_refs):
                        continue  # hand-landed or recovery; grammar recognized

                # Route 4: loose station+key co-occurrence, last resort (see
                # `_loose_subject_key_match`'s own docstring for why the
                # strict grammar above still misses real hand-authored
                # landings). Checked against both subject pools already
                # fetched above -- no new git call.
                if any(
                    (
                        all_ref_commits is not None
                        and _loose_subject_key_match(
                            all_ref_commits,
                            station=slug,
                            key_ref=r,
                        )
                    )
                    or (
                        main_commits is not None
                        and _loose_subject_key_match(
                            main_commits,
                            station=slug,
                            key_ref=r,
                        )
                    )
                    for r in key_refs
                ):
                    continue  # station+key co-occurrence found

            phase = task.get("phase", "")
            # `phase in NOT_LANDED` HASHES `phase`, so a JSON record giving it a
            # list or dict value raised TypeError straight out of the gather --
            # the container guard in `_harness_tasks` validates the task dict,
            # never the values inside it.
            if isinstance(phase, str) and phase in NOT_LANDED:
                false_greens.append(
                    {
                        "slug": slug,
                        "key": key,
                        "phase": phase,
                        "defer_reason": task.get("defer_reason") or "",
                    }
                )
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
    #
    # The unverified-population caveats below ride on the OK Finding only. A
    # FAIL is a specific accusation about one named story, not a claim about
    # the audit's completeness, so it needs no qualifier -- and widening the
    # FAIL evidence to carry them would put the same counts in two shapes.
    #
    # Story 27.5: a bare-form merge subject's `git diff` query failing is its
    # OWN standalone WARN Finding (mirrors `sources/ledger.py::gather_
    # direction`'s per-sha `bare-merge-diff-unreadable` WARN) -- built here,
    # BEFORE the `false_greens` branch, so it surfaces unconditionally. A
    # version of this that only rode on the OK-message caveat dropped it
    # silently whenever the same run also had an unrelated false-green FAIL.
    diff_warn_findings = tuple(
        Finding(
            source=Source.STORY_STATUS,
            check="bare-merge-diff-unreadable",
            status=DoctorStatus.WARN,
            message=(
                f"{project}: first-parent diff for {sha} could not be read "
                "— a bare legacy-form merge subject naming a key this "
                "project's ledger knows could not be attributed"
            ),
            evidence={"project": project, "sha": sha},
        )
        for project, sha in sorted(set(unreadable_diff_shas))
    )

    if false_greens:
        return diff_warn_findings + tuple(
            Finding(
                source=Source.STORY_STATUS,
                check="story-status",
                status=DoctorStatus.FAIL,
                message=(
                    f"{fg['slug']}/{fg['key']}: reads `done` in the sprint feed, "
                    f"but the harness says {fg['phase']!r} with no commit and no "
                    f"merge commit anywhere" + (f" — {fg['defer_reason']}" if fg["defer_reason"] else "")
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
    # Story 27.5: `unreadable_diff_shas` is surfaced above as its own
    # standalone WARN Finding per sha (`diff_warn_findings`), not folded
    # into this OK message's detail string -- one shape, not two.
    return diff_warn_findings + (
        Finding(
            source=Source.STORY_STATUS,
            check="story-status",
            status=DoctorStatus.OK,
            message=f"no `done` story contradicts its landing evidence ({detail})",
            evidence={"audited": audited},
        ),
    )
