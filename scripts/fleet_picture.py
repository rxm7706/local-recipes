#!/usr/bin/env python3
"""PyForge fleet progress REPORT (not a detector -- never gates, always exits 0).

Lives in scripts/ rather than a scratchpad so a scheduled status check survives a
session restart; allowlisted in spec_surface_allowlist.txt for the same reason
`unpushed_work_check.py` is -- it is operator tooling, not a governed surface.

PyForge fleet progress: done / completeness / projection / blocked, per station.

Measured from each station's TRACKED sprint-status-ledger.yaml (the twin of the
gitignored Tier-3 feed) — never from an ad-hoc regex over commit subjects, and
never from the board, which lags until a merge to main.

Column semantics (operator, Aug-2026):

- ``done`` — ledger ``status: done`` count today.
- ``cmpl`` (**completeness**) — ``done + backlog``: the station's full reachable
  count if every backlog story eventually ships (idle stations included).
- ``proj`` (**projection**) — what this report expects to finish from what is
  **running or explicitly queued** right now (``fleet-drain-queue.yaml``
  ``order_overrides`` when a factory dispatch phase is active; otherwise ``done``
  only). Idle backlog waiting on a future drain does not inflate ``proj``.

An epic counts as done only when EVERY story in it is done; completeness/projection
apply the same per-epic rules at the epic columns.

Factory dispatch phases surface in the ``state`` column as BUILDING / VERIFY /
CHAIN / STUCK — not a generic RUNNING. The footer reports ``N/8 building`` (live
harness count), not marshal's raw ``running`` count.

UNSUPERVISED rows (no Marshal supervisor sidecar) are supervision state, not
engine liveness — the ATTENTION block names the CAP-2 follow-up before any
restart (`reference/fleet-landing-pass-liveness.md`). Preferred restart is
``marshal factory dispatch`` (bmad-build-auto), not ``factory spin``. Live
run ops belong on ``marshal watch --fleet`` / ``marshal watch --project``;
this report stays the ledger board.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
LOOP_ROOT = pathlib.Path.home() / ".bmad-loops"
# 20 is not derived from the 2026-08-15 incident's 55-60 (the magnitude at
# which it was noticed by accident, not a chosen threshold) -- it's picked to
# catch drift well before reaching that magnitude while tolerating the small,
# routine gap a loop home carries between other stations' independent merges.
STALE_BEHIND_THRESHOLD = 20

# bmad-loop 0.11's operator-parked run state (marshal Story 25.5, DW-BL011-1):
# the machine token stays bare `awaiting-operator`; the remedy suffix is the
# one human projection, spelled identically everywhere run state is shown
# (marshal status text, this table's state column, loop_stall_check.py).
AWAITING_OPERATOR_LABEL = "awaiting-operator (run bmad-loop confirm)"

# UNSUPERVISED follow-up (marshal Story 24.3, FR-195 CAP-3): the one-command
# engine-liveness check before assuming a restart — same primary check as
# fleet landing-pass STEP 2 (`.claude/memory/reference/fleet-landing-pass-liveness.md`).
UNSUPERVISED_LIVENESS_FOLLOWUP = (
    "`bmad-loop status <run_id> --json` + `bmad-loop list --json` "
    "in the loop home"
)


DRAIN_QUEUE_PATH = (
    REPO / "_bmad-output/projects/pyforge-marshal/planning-artifacts"
    / "fleet-drain-queue.yaml"
)


def load_drain_queue_overrides() -> dict[str, list[str]]:
    """``order_overrides`` from ``fleet-drain-queue.yaml`` keyed by bare slug."""
    if not DRAIN_QUEUE_PATH.is_file():
        return {}
    import yaml

    data = yaml.safe_load(DRAIN_QUEUE_PATH.read_text()) or {}
    raw = data.get("order_overrides") or {}
    return {
        str(station).replace("pyforge-", ""): list(keys)
        for station, keys in raw.items()
        if isinstance(keys, list)
    }


def dispatch_active(live_row: dict) -> bool:
    """True when factory dispatch has an observable in-flight phase."""
    phase = live_row.get("dispatch_phase")
    if phase in ("building", "verifying", "chaining"):
        return True
    return live_row.get("state") == "running" and bool(live_row.get("story"))


def dispatch_terminal_dead_tail(live_row: dict) -> bool:
    """True when dispatch ended in terminal failure with no live overlay phase."""
    story = live_row.get("story") or live_row.get("current_story")
    if not story:
        return False
    if live_row.get("dispatch_completion_verdict") not in (
        "failed",
        "stopped_externally",
        "blocked",
    ):
        return False
    return live_row.get("dispatch_phase") is None


def _station_project_slug(bare_slug: str) -> str:
    return bare_slug if bare_slug.startswith("pyforge-") else f"pyforge-{bare_slug}"


def _safe_dispatch_ref_segment(raw: str, fallback: str) -> str:
    """Same sanitizer as marshal ``_safe_ref_segment`` (Story 22.9).

    Inlined so ``pixi run -e local-recipes fleet-picture`` never imports
    ``pyforge.marshal`` (that package is not in the local-recipes env).
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
    cleaned = re.sub(r"\.{2,}", ".", cleaned).strip("-.")
    return cleaned or fallback


def _dispatch_branch_candidates(bare_slug: str, story_key: str) -> tuple[str, ...]:
    """Expected dispatch branch names for ATTENTION matching (Story 28.23).

    Mirrors marshal ``dispatch_worktree_branch`` / ``legacy_dispatch_worktree_branch``
    without importing that package — fleet-picture is a local-recipes reporter.
    """
    station = _station_project_slug(bare_slug)
    return (
        f"dispatch/{_safe_dispatch_ref_segment(station, 'project')}"
        f"/{_safe_dispatch_ref_segment(story_key, 'story')}",
        f"marshal/{_safe_dispatch_ref_segment(story_key, 'story')}",
    )


def _dispatch_stranded_work_needs_lines(
    *,
    slug: str,
    story: str,
    live_row: dict,
    open_prs_by_head: dict[str, dict[str, object]],
) -> list[str]:
    """ATTENTION ``needs`` lines for stranded dispatch work after verify-fail."""
    if not dispatch_terminal_dead_tail(live_row):
        return []

    lines: list[str] = []
    stranded = live_row.get("dispatch_stranded_work")
    if isinstance(stranded, dict) and stranded.get("kind") == "unpushed-branch":
        ref = stranded.get("ref") or "?"
        files = stranded.get("files")
        remedy = stranded.get("remedy") or f"git push origin {ref}"
        lines.append(
            f"{slug}: stranded dispatch work for {story} — unpushed branch "
            f"{ref!r} ({files} file(s) not on origin) — {remedy}"
        )
        return lines

    for branch in _dispatch_branch_candidates(slug, story):
        pr = open_prs_by_head.get(branch)
        if pr is None:
            continue
        number = pr.get("number") or "?"
        title = str(pr.get("title") or "").split(chr(10))[0][:110]
        lines.append(
            f"{slug}: stranded dispatch work for {story} — open unmerged PR "
            f"#{number} on {branch!r} ({title}) — merge or close after recovery"
        )
        return lines
    return lines


def _open_prs_by_head_ref(
    repo: pathlib.Path = REPO, timeout: int = 120
) -> dict[str, dict[str, object]]:
    """Open PRs keyed by head branch name (Story 28.23 ATTENTION helper)."""
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                "rxm7706/local-recipes",
                "--state",
                "open",
                "--json",
                "number,title,headRefName",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            return {}
        by_head: dict[str, dict[str, object]] = {}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            head = entry.get("headRefName")
            if isinstance(head, str) and head:
                by_head[head] = entry
        return by_head
    except Exception:
        return {}


def story_completeness(stories: dict[str, str]) -> int:
    """``done + backlog`` — full station reach if all backlog eventually ships."""
    counts = collections.Counter(stories.values())
    return counts["done"] + counts["backlog"]


def story_projection(
    stories: dict[str, str],
    *,
    queue_keys: list[str] | None,
    dispatch_in_flight: bool,
) -> int:
    """Stories expected to complete from what is running/queued **now**."""
    counts = collections.Counter(stories.values())
    done = counts["done"]
    if not dispatch_in_flight:
        return done
    if queue_keys:
        queued_backlog = sum(1 for key in queue_keys if stories.get(key) == "backlog")
        return done + queued_backlog
    return done + counts["backlog"]


def epic_completeness(by_epic: dict[int, list[str]]) -> int:
    return sum(
        1
        for values in by_epic.values()
        if values and all(v in ("done", "backlog") for v in values)
    )


def epic_projection(
    by_epic: dict[int, list[str]], *, dispatch_in_flight: bool
) -> int:
    if not dispatch_in_flight:
        return sum(1 for values in by_epic.values() if all(v == "done" for v in values))
    return sum(
        1
        for values in by_epic.values()
        if all(v == "done" or v == "backlog" for v in values)
    )


def ledger_story_done(stories: dict[str, str], story: str) -> bool:
    """True when the tracked ledger marks ``story`` (or its epic-seq) done."""
    if not story:
        return False
    if stories.get(story) == "done":
        return True
    m = re.match(r"(\d+-\d+)", story)
    if not m:
        return False
    prefix = m.group(1) + "-"
    return any(k.startswith(prefix) and v == "done" for k, v in stories.items())


def story_ledger_status(stories: dict[str, str], story: str) -> str | None:
    """Ledger status for ``story``'s epic-seq key, if any."""
    if not story:
        return None
    if story in stories:
        return stories[story]
    m = re.match(r"(\d+-\d+)", story)
    if not m:
        return None
    prefix = m.group(1) + "-"
    for key, value in stories.items():
        if key.startswith(prefix):
            return value
    return None


def station_state(*, running: bool, story: str, hstate: str, done: int,
                  total: int, backlog: int,
                  dispatch_phase: str | None = None,
                  ledger_done: bool = False,
                  verification_verdict: str | None = None,
                  verification_failed_gate: str | None = None,
                  queued_backlog: int | None = None,
                  awaiting_operator_remedy: str | None = None) -> str:
    """The state-column cell for one station row -- pure, so the meta test
    (test_fleet_picture_awaiting_operator.py) can pin the naming without
    driving main()'s subprocess sweep. `hstate` is `marshal status`'s own
    derived state for the station ("idle" when marshal reported nothing).

    Factory dispatch uses phase-specific prefixes (BUILDING / VERIFY / CHAIN)
    instead of a single RUNNING label — the Aug-2026 operator confusion case
    where four homes all read RUNNING but only one had a live harness.

    A `hstate == "awaiting-operator"` station (bmad-loop 0.11: >=1 story
    parked for external human-only actions, nothing else active) is NAMED
    with the confirm remedy -- never folded into the stopped/unsupervised
    "needs dispatch" bucket: the parked story's work is already committed,
    so `bmad-loop confirm` is the next action, not a restart."""
    if running:
        # `dispatch_verification_verdict` is dispatch-specific state that
        # persists on the row until the NEXT dispatch run overwrites it --
        # it does NOT get cleared when a different engine (spin) starts
        # running on the same station. Found live 2026-09-10: a station
        # whose current live run was a `factory spin` session still carried
        # a `refused` verdict from an unrelated `factory dispatch` attempt
        # 10 days earlier, mislabeling a healthy running spin as STUCK.
        # `dispatch_phase` is only ever set while dispatch itself is the
        # live engine (see BUILDING/VERIFY/CHAIN below), so requiring it
        # here scopes the refused verdict to the run it actually describes.
        if verification_verdict == "refused" and dispatch_phase is not None:
            gate = verification_failed_gate or "?"
            short = story[:28]
            return f"STUCK   {short} (verify refused {gate})"
        phase_prefix = {
            "building": "BUILDING",
            "verifying": "VERIFY  ",
            "chaining": "CHAIN   ",
        }.get(dispatch_phase or "", "RUNNING")
        label = story[:28]
        if dispatch_phase == "chaining" and ledger_done:
            return f"{phase_prefix} {label} (merged)"
        if dispatch_phase == "verifying":
            return f"{phase_prefix} {label}"
        if dispatch_phase == "building":
            suffix = f" [{queued_backlog} queued]" if queued_backlog else ""
            return f"{phase_prefix} {label}{suffix}"
        if dispatch_phase == "chaining":
            return f"{phase_prefix} {label}"
        return f"{phase_prefix} {label}"
    if hstate == "awaiting-operator":
        if awaiting_operator_remedy:
            return f"awaiting-operator ({awaiting_operator_remedy})"
        return AWAITING_OPERATOR_LABEL
    if hstate == "paused-on-escalation":
        return "PAUSED - needs you (escalation)"
    if hstate in ("stopped", "unsupervised", "unknown") and backlog:
        return f"{hstate.upper()} - {backlog} left, needs dispatch"
    if done == total:
        return "complete"
    if backlog:
        return f"idle - {backlog} not started"
    return "idle"


def loop_home_staleness(
    loop_root: pathlib.Path = LOOP_ROOT, threshold: int = STALE_BEHIND_THRESHOLD
) -> list[tuple[str, str, int]]:
    """(slug, branch, commits_behind) for each loop home whose branch is
    `threshold`+ commits behind a live-fetched `origin/main`.

    Live-fetches before measuring -- a stale local remote-tracking ref would
    defeat the point (the 2026-08-15 incident happened because nobody had
    fetched). Any per-home failure (detached HEAD, no `origin` remote,
    network error) skips that home rather than raising, matching
    `running_stations()`'s fault-tolerant idiom."""
    if not loop_root.is_dir():
        return []
    stale = []
    for home in sorted(p for p in loop_root.iterdir() if (p / ".git").exists()):
        slug = home.name.replace("pyforge-", "")
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=home, capture_output=True, text=True, timeout=30,
            ).stdout.strip()
            if not branch:
                continue  # detached HEAD
            subprocess.run(
                ["git", "fetch", "--quiet", "origin", "main"],
                cwd=home, capture_output=True, text=True, timeout=60, check=True,
            )
            count = subprocess.run(
                ["git", "rev-list", "--count", f"{branch}..origin/main"],
                cwd=home, capture_output=True, text=True, timeout=30, check=True,
            ).stdout.strip()
            if count.isdigit() and int(count) >= threshold:
                stale.append((slug, branch, int(count)))
        except Exception:
            continue
    return stale


def primary_checkout_staleness(
    repo: pathlib.Path = REPO, threshold: int = 1
) -> int | None:
    """Commits `repo`'s current branch is behind a live-fetched `origin/main`,
    or ``None`` if under `threshold` (default 1 -- any drift matters here,
    unlike a loop home's 20) or the check could not be made.

    Story 20.12: marshal's unattended CAP-4 land path can commit, push, open
    a PR, verify, and merge a story with zero operator action -- the primary
    checkout (where the operator's own next push/merge/worktree-creation
    happens) has no other signal this occurred and can silently drift behind
    `origin/main`. Same live-fetch-then-`rev-list` idiom and fault-tolerant
    degrade as `loop_home_staleness()` -- this is the one checkout that
    function's own `loop_root.iterdir()` walk never covers."""
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo, capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        if not branch:
            return None  # detached HEAD
        subprocess.run(
            ["git", "fetch", "--quiet", "origin", "main"],
            cwd=repo, capture_output=True, text=True, timeout=60, check=True,
        )
        count = subprocess.run(
            ["git", "rev-list", "--count", f"{branch}..origin/main"],
            cwd=repo, capture_output=True, text=True, timeout=30, check=True,
        ).stdout.strip()
        if count.isdigit() and int(count) >= threshold:
            return int(count)
    except Exception:
        pass
    return None


def bmad_core_drift_findings(
    repo: pathlib.Path = REPO, timeout: int = 30
    # 30s vs the source's own ~25s worst-case network design budget: since
    # Story 14.1 (CAP-4) the gather issues CAP-2's core fetch (bounded at
    # `_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0`) PLUS a suite fetch loop under
    # its own shared deadline (`_SUITE_FETCH_TOTAL_BUDGET_SECONDS`). Story
    # 15.2 (review pass 1, bad_spec repair) added a THIRD fetch -- the
    # CORE-side channel-vs-recipe/recipe-vs-upstream check's own bounded
    # `_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0` call -- and doubled the suite
    # loop's own shared deadline from 5.0s to 10.0s to keep it from starving
    # the PRE-EXISTING npm/GitHub upstream check once a third fetch type
    # draws from the same pool. Story 19.1 bumped the suite pool to 15.0s
    # for manifest-driven coverage: 5 (CAP-2 npm) + 15 (suite loop) + 5
    # (CORE channel via registry-aware resolve) = 25s is the new inner worst
    # case, so this timeout grew from 25 to 30, preserving the same ~5s
    # margin Story 14.1 originally established. This timeout must also cover
    # interpreter startup and package import before any fetch starts, so the
    # margin over the inner bound is thinner than the pre-14.1 15s-over-5s
    # arithmetic once suggested, but still positive for the blackholed-network
    # worst case.
) -> list[dict]:
    """WARN-status Findings from ``pyforge.doctor``'s bmad-method-version-
    drift source (Story 10.1/10.2's CAP-1/CAP-2 -- installed BMAD-METHOD
    behind pixi.toml's declared floor, and/or behind the latest release
    published upstream on npm).

    Shells out via ``sys.executable -m pyforge.doctor.sources
    bmad-method-version-drift --json`` -- the same subprocess discipline
    every other cross-package signal in this file already uses
    (``running_stations()``'s ``marshal status``,
    ``bmad_loop_baseline_drift_check.py``); this script never imports
    ``pyforge.doctor`` directly.

    Unlike ``loop_home_staleness``/``running_stations``, this function does
    NOT catch its own failures -- it raises on any (subprocess error,
    non-zero exit, malformed JSON, ...). The caller in ``main()``'s
    ATTENTION block wraps the call in the same ``try/except Exception:
    watch.append(...)`` idiom every other ATTENTION probe there already
    uses, so degrading to one "could not check" line is the CALLER's job,
    not this function's."""
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources",
         "bmad-method-version-drift", "--json"],
        cwd=repo, capture_output=True, text=True, timeout=timeout, check=True,
    )
    findings = json.loads(result.stdout)
    return [f for f in findings if f.get("status") == "warn"]


def sibling_dreams_drift_findings(
    repo: pathlib.Path = REPO, timeout: int = 20
) -> list[dict]:
    """WARN Findings from ``pyforge.doctor``'s sibling-dreams-drift source
    (Story 16.1 / CAP-1). Same subprocess discipline as
    ``bmad_core_drift_findings``; raises on failure so ATTENTION can degrade.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources",
         "sibling-dreams-drift", "--json"],
        cwd=repo, capture_output=True, text=True, timeout=timeout, check=True,
    )
    findings = json.loads(result.stdout)
    return [f for f in findings if f.get("status") == "warn"]


def capability_effect_findings(
    repo: pathlib.Path = REPO, timeout: int = 60
) -> list[dict]:
    """WARN Findings from ``pyforge.doctor``'s capability-effect source
    (Stories 21.10/21.11 -- missing ``verified:`` lines on terminal Spec
    CAPs). Same subprocess discipline as ``sibling_dreams_drift_findings``;
    raises on failure so ATTENTION can degrade.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources",
         "capability-effect", "--json"],
        cwd=repo, capture_output=True, text=True, timeout=timeout, check=True,
    )
    findings = json.loads(result.stdout)
    return [f for f in findings if f.get("status") == "warn"]


def status_body_consistency_findings(
    repo: pathlib.Path = REPO, timeout: int = 120
) -> list[dict]:
    """WARN Findings from ``pyforge.doctor``'s status-body-consistency source
    (Stories 21.12–21.16 -- terminal-tier narrative drift beside
    ``dream-vocab`` / ``spec-status-missing``). Same subprocess discipline
    as ``capability_effect_findings``; raises on failure so ATTENTION can
    degrade.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources",
         "status-body-consistency", "--json"],
        cwd=repo, capture_output=True, text=True, timeout=timeout, check=True,
    )
    findings = json.loads(result.stdout)
    return [f for f in findings if f.get("status") == "warn"]


def verification_staleness_findings(
    repo: pathlib.Path = REPO, timeout: int = 180
    # Originally 90s (~2x margin over a ~48s measured baseline) -- not
    # `bmad_core_drift_findings`'s 25s, since due-for-verification does real
    # per-entry `git log`/`git grep` churn and mechanical-verdict work
    # (Stories 11.2/11.3) across the fleet's 600+ tracked entries today, so a
    # 25s bound would degrade EVERY real invocation, defeating this story's
    # own "ambient, always-visible" Intent.
    #
    # Bumped to 180s 2026-08-30: `chain.py::_call_site_count`'s mechanical-
    # verdict git grep ran `--untracked --no-exclude-standard` (necessarily
    # un-ignoring `.gitignore`) with NO further exclusion -- against this
    # repo's live `.pixi/` (measured 32GB), a single call did not return
    # within 4 minutes, and `due-for-verification` hard-timed-out at 90s on
    # every real invocation (the "could not check verification staleness"
    # degrade this whole comment chain exists to prevent). Fixed in
    # `chain.py` by excluding `env_hygiene.py`'s own `_PRUNED_DIR_NAMES`
    # (the same curated "never first-party source" list the discovery-walk
    # pruning already trusts) from that git grep. Re-measured post-fix at
    # ~86s -- fleet growth (600+ tracked entries today vs. the original
    # ~400 this docstring's 48s baseline was measured against) means even
    # the now-BOUNDED cost sits close to the old 90s ceiling; 180s restores
    # this function's own documented ~2x-margin design intent over the new
    # measured cost, rather than leaving a razor-thin margin that the next
    # session's fleet growth trips again.
) -> list[dict]:
    """``verification-coverage`` items from ``pyforge.doctor``'s due-for-
    verification source (Story 11.7/CAP-7 -- the AGGREGATE picture, "N% of a
    project's tracked entries verified within the staleness window", that
    Story 11.1's own per-entry WARN findings never surface ambiently on
    their own).

    Shells out via ``sys.executable -m pyforge.doctor.sources
    due-for-verification --json`` -- the same subprocess discipline
    ``bmad_core_drift_findings`` above already establishes; this script
    never imports ``pyforge.doctor`` directly.

    Like ``bmad_core_drift_findings`` (and UNLIKE ``loop_home_staleness``/
    ``running_stations``), this function does NOT catch its own failures --
    it raises on any (subprocess error, non-zero exit, malformed JSON, ...).
    Degrading to one "could not check" line is the CALLER's job (``main()``'s
    own ``try/except Exception: watch.append(...)`` idiom), not this
    function's."""
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources",
         "due-for-verification", "--json"],
        cwd=repo, capture_output=True, text=True, timeout=timeout, check=True,
    )
    findings = json.loads(result.stdout)
    return [f for f in findings if f.get("check") == "verification-coverage"]


def dream_chain_gap_findings(
    repo: pathlib.Path = REPO, timeout: int = 30
    # 30s: measured live at ~0.4s for the bare `python -m` module run (an
    # earlier ~4s figure included pixi task/env startup, which this direct
    # `sys.executable -m` invocation never pays) -- 30s carries a wide
    # margin over the measured cost, same idiom as the sibling consumers'
    # commented bounds above.
) -> list[dict]:
    """Dream-chain gap Findings from ``pyforge.doctor``'s dream-chain
    source (Story 12.4/CAP-4 -- Dreams fleet-wide with no Spec, INV-1's
    ``dream-without-spec``), plus every unevaluable-equivalent shape that
    says the count cannot be trusted: per-cause ``dream-chain-unevaluable``
    items AND ``degrade_on_exception``'s total-degrade WARN, which is
    emitted under ``check="dream-chain"`` -- the same ``check`` as the
    vacuous OK, separable only by ``status`` (the OK stays filtered out).
    The ``dream-chain-unevaluable`` arm deliberately ignores ``status``:
    every live emitter sets WARN today, and a hypothetical future
    FAIL-status unevaluable item must not silently vanish from the filter.
    Every other kind (``spec-without-dream-link``, ``owner-unassigned``,
    ``spec-location-mismatch``, the INV-3 kinds) is dropped -- CAP-4 is the
    Dreams-without-Spec count only.

    Shells out via ``sys.executable -m pyforge.doctor.sources dream-chain
    --json`` -- the same subprocess discipline ``bmad_core_drift_findings``
    /``verification_staleness_findings`` above already establish; this
    script never imports ``pyforge.doctor`` directly.

    DELIBERATE deviation from the siblings' ``check=True``: exit codes
    {0, 2} are BOTH success here. The siblings' sources are WARN-only, so
    they always exit 0 and ``check=True`` is safe -- but
    ``dream-without-spec`` findings are FAIL-status, so ``exit_code_for``
    makes this CLI exit 2 on ANY real gap (verified live: exit=2 with 17
    gaps today). A verbatim ``check=True`` mirror would raise on exactly
    the case this function exists for and degrade every real invocation to
    "could not check". Honest limit: argparse usage errors ALSO exit 2
    (with empty stdout), so the exit-code gate alone cannot tell them
    apart -- the ``json.loads`` below is the guard that actually fires
    there. Any other exit code raises ``CalledProcessError`` with stderr
    attached.

    Like the siblings, this function does NOT catch its own failures -- it
    raises; degrading to one "could not check dream-chain gaps" line is
    the CALLER's job (``main()``'s own ``try/except Exception`` idiom)."""
    cmd = [sys.executable, "-m", "pyforge.doctor.sources",
           "dream-chain", "--json"]
    result = subprocess.run(
        cmd, cwd=repo, capture_output=True, text=True, timeout=timeout,
        check=False,  # {0, 2} are both success -- see docstring
    )
    if result.returncode not in (0, 2):
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    findings = json.loads(result.stdout)
    return [
        f for f in findings
        if f.get("check") in ("dream-without-spec", "dream-chain-unevaluable")
        or (f.get("check") == "dream-chain" and f.get("status") == "warn")
    ]


def _dream_chain_watch_lines(findings: list[dict]) -> list[str]:
    """ATTENTION ``watch`` lines for ``dream_chain_gap_findings()``'s
    output -- a pure assembly helper so the count/slug-cap/sanitization
    logic is directly unit-testable (unlike the verification-staleness
    consumer above, which only echoes a pre-formatted ``message``, this
    consumer BUILDS a line).

    One count line when any ``dream-without-spec`` item exists (count + up
    to 3 example slugs + the `dream-chain-check` pointer); one
    directionally-NEUTRAL trust line when any unevaluable-equivalent item
    is present -- spec-side unevaluable causes INFLATE the count (Specs
    dropped from ``covered`` make INV-1 fire falsely) while an unreadable
    ``docs/dreams/`` understates it, so the line claims neither direction.
    ``[]`` when clean, matching the siblings' clean-state silence."""
    gaps = [f for f in findings if f.get("check") == "dream-without-spec"]
    unevaluable = [
        f for f in findings
        if f.get("check") == "dream-chain-unevaluable"
        or (f.get("check") == "dream-chain" and f.get("status") == "warn")
    ]
    lines = []
    if gaps:
        # Same sanitization discipline as the `escalation_reason`/`message`
        # consumers in main(), applied PER SLUG, not to the joined string:
        # an externally-sourced slug (a docs/dreams/*.md file stem -- any
        # legal POSIX filename) must never inject extra, indistinguishable
        # bullet lines or flood the block. First line only (newline drops
        # the tail), remaining control chars scrubbed (`\r`/ESC are legal
        # in filenames and would overwrite or spoof the printed line in a
        # terminal), 40-char cap. `subject` present-but-null or non-string
        # degrades to the same `?` placeholder as a missing key -- one
        # malformed item must not send the whole probe to "could not
        # check" (review pass 2).
        slugs = [
            re.sub(
                r"[\x00-\x1f\x7f]", "?",
                str((f.get("evidence") or {}).get("subject") or "?")
                .split(chr(10))[0],
            )[:40]
            for f in gaps[:3]
        ]
        lines.append(
            f"{len(gaps)} Dream(s) with no Spec (e.g. {', '.join(slugs)}) -- "
            f"run `pixi run -e local-recipes dream-chain-check` for the full list"
        )
    if unevaluable:
        lines.append(
            "dream-chain could not be fully evaluated -- the "
            "Dreams-without-Spec count may be wrong in either direction"
        )
    return lines


def baseline_drift_findings(
    repo: pathlib.Path = REPO, timeout: int = 60
) -> list[dict]:
    """Unrecovered baseline-drift defers from CAP-1's detector (Story 20.2 /
    CAP-2 -- loud-defer containment on the ATTENTION plane).

    Shells out via ``sys.executable scripts/bmad_loop_baseline_drift_check.py
    --json`` -- same subprocess discipline as ``dream_chain_gap_findings``;
    this script never imports the detector module (or ``bmad_loop``).

    Timeout 60s: the detector walks every ``~/.bmad-loops`` home and runs
    ``git for-each-ref`` per unrecovered run; slower than dream-chain's 30s
    bound on a cold disk with many loop homes.

    DELIBERATE deviation from siblings' ``check=True``: exit codes {0, 1}
    are BOTH success here. Exit 1 means findings exist (the CAP-1 loud
    exit); a ``check=True`` mirror would raise on exactly the case this
    function exists for and degrade every real unrecovered defer to
    "could not run". Any other exit code raises ``CalledProcessError``.

    Does NOT catch its own failures -- raises so ``main()``'s ATTENTION
    ``try/except`` can degrade to one watch line.
    """
    cmd = [
        sys.executable,
        str(repo / "scripts" / "bmad_loop_baseline_drift_check.py"),
        "--json",
    ]
    result = subprocess.run(
        cmd, cwd=repo, capture_output=True, text=True, timeout=timeout,
        check=False,  # {0, 1} are both success -- see docstring
        stdin=subprocess.DEVNULL,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    raw = (result.stdout or "").strip()
    if not raw:
        return []
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError(
            f"baseline-drift-check --json expected a list, got {type(payload).__name__}"
        )
    return payload


def _baseline_drift_needs_lines(findings: list[dict]) -> list[str]:
    """ATTENTION ``needs`` lines for ``baseline_drift_findings()`` output.

    Pure assembly helper (dream_chain pattern): count + first finding's
    recovery fields (story, run, drifted-vs-real baselines, preserve ref
    or patch hint) + unambiguous ``baseline-drift-check`` pointer.
    ``[]`` when clean / recovered (empty findings) -- healthy silence.
    """
    if not findings:
        return []

    def _sanitize(val: object, cap: int) -> str:
        # First printable line only; scrub C0 controls AND Unicode line
        # breaks (U+0085/U+2028/U+2029) so journal fields cannot split one
        # needs bullet into many.
        text = str(val if val is not None else "?")
        text = re.split(r"[\n\r\u0085\u2028\u2029]", text, maxsplit=1)[0]
        return re.sub(r"[\x00-\x1f\x7f\u0085\u2028\u2029]", "?", text)[:cap]

    f0 = findings[0]
    slug = _sanitize(f0.get("slug") or "?", 40)
    story = _sanitize(f0.get("story") or "?", 110)
    run = _sanitize(f0.get("run") or "?", 40)
    real = _sanitize(f0.get("real") or "?", 40)
    drifted = _sanitize(f0.get("drifted") or "?", 40)
    refs = f0.get("refs") or []
    if not isinstance(refs, list):
        refs = [refs] if refs else []
    if refs:
        recover = f"recover from: {_sanitize(', '.join(str(r) for r in refs), 120)}"
    else:
        recover = (
            f"no attempt-preserve/{run}-* branch -- "
            f"check failed/{story}/changes.patch in the run dir"
        )
    return [
        f"{len(findings)} unrecovered baseline-drift defer(s) -- real reviewed "
        f"work stranded by bmad-loop's stuck-orchestrator bug "
        f"(e.g. {slug}/{story} run {run}: real {real} != drifted {drifted}; "
        f"{recover}) -- run `pixi run -e local-recipes baseline-drift-check` "
        f"for the full list, then recover per "
        f"docs/dreams/bmad-loop-baseline-drift.md"
    ]


def running_stations() -> tuple[set[str], dict[str, dict]]:
    """(slugs running, slug -> live row) from marshal status.

    The full row is kept, not just the story: `state` distinguishes running from
    paused-on-escalation / stopped / unsupervised, which is the difference
    between "working" and "waiting on a human" — the whole point of the ATTENTION
    block below."""
    try:
        out = subprocess.run(
            ["pixi", "run", "-e", "pyforge-marshal", "--", "marshal", "status",
             "--format", "json"],
            cwd=REPO, capture_output=True, text=True, timeout=300,
        ).stdout
        data = json.loads(out[out.index("{"):out.rindex("}") + 1])
        rows = data.get("data", data).get("homes", [])
        running, info = set(), {}
        for r in rows:
            slug = (r.get("slug") or r.get("project") or "").replace("pyforge-", "")
            info[slug] = {
                "state": r.get("state") or "unknown",
                "story": r.get("current_story") or "",
                "dispatch_phase": r.get("dispatch_phase"),
                "dispatch_completion_verdict": r.get("dispatch_completion_verdict"),
                "dispatch_verification_verdict": r.get("dispatch_verification_verdict"),
                "dispatch_verification_failed_gate": r.get(
                    "dispatch_verification_failed_gate"
                ),
                "escalation_reason": r.get("escalation_reason"),
                "escalation_artifact": r.get("escalation_artifact"),
                # Story 28.15 (CAP-17), AC4: a station's warn-mode
                # scope-violation advisories, visible here too -- never
                # journal-only.
                "scope_advisories": r.get("dispatch_verification_scope_advisories") or [],
                # Story 53.2 review (I1): `execute_dispatch_land`'s envelope
                # findings (MRS-DISP-047/048), same visibility rationale as
                # `scope_advisories` above.
                "landing_findings": r.get("dispatch_landing_findings") or [],
                "awaiting_operator_remedy": r.get("awaiting_operator_remedy"),
                "missing_spec_escalation_glob": r.get("missing_spec_escalation_glob"),
                "dispatch_stranded_work": r.get("dispatch_stranded_work"),
            }
            if r.get("state") == "running":
                running.add(slug)
        return running, info
    except Exception:
        return set(), {}


def main() -> int:
    running, live = running_stations()
    queue_overrides = load_drain_queue_overrides()
    building_slugs = {
        slug
        for slug, row in live.items()
        if (row or {}).get("dispatch_phase") == "building"
    }
    current = {k: v["story"] for k, v in live.items()}
    rows, tot = [], collections.Counter()
    for path in sorted(REPO.glob("_bmad-output/projects/*/planning-artifacts/"
                                 "sprint-status-ledger.yaml")):
        import yaml
        slug = path.parts[-3].replace("pyforge-", "")
        status = yaml.safe_load(path.read_text())["development_status"]
        stories = {k: v for k, v in status.items() if not k.startswith("epic-")}
        counts = collections.Counter(stories.values())

        by_epic: dict[int, list[str]] = collections.defaultdict(list)
        for key, value in stories.items():
            m = re.match(r"(\d+)-", key)
            if m:
                by_epic[int(m.group(1))].append(value)

        live_row = live.get(slug, {}) or {}
        queue_keys = queue_overrides.get(slug)
        in_flight = dispatch_active(live_row)
        cmpl = story_completeness(stories)
        proj = story_projection(
            stories, queue_keys=queue_keys, dispatch_in_flight=in_flight
        )
        ep_now = sum(1 for e in by_epic.values() if all(v == "done" for v in e))
        ep_cmpl = epic_completeness(by_epic)
        ep_proj = epic_projection(by_epic, dispatch_in_flight=in_flight)
        queued_backlog = (
            sum(1 for key in queue_keys if stories.get(key) == "backlog")
            if queue_keys
            else counts["backlog"]
        )

        rows.append((
            slug, len(stories), counts["done"], cmpl, proj, counts["blocked"],
            len(by_epic), ep_now, ep_cmpl, ep_proj, slug in running,
            live_row.get("state", "idle"), counts["backlog"],
            counts["awaiting-operator"], stories, queued_backlog, in_flight,
        ))
        for k, v in (
            ("tot", len(stories)),
            ("done", counts["done"]),
            ("cmpl", cmpl),
            ("proj", proj),
            ("blkd", counts["blocked"]),
            ("ep", len(by_epic)),
            ("epn", ep_now),
            ("epc", ep_cmpl),
            ("epp", ep_proj),
        ):
            tot[k] += v

    hdr = (
        f"{'station':<9}{'stories':>8}{'done':>6}{'cmpl':>6}{'proj':>6}{'blkd':>6}"
        f"{'epics':>7}{'ep now':>8}{'ep cmpl':>8}{'ep proj':>8}  {'state'}"
    )
    print(hdr)
    print("-" * (len(hdr) + 24))
    for (
        slug, n, done, cmpl, proj, blkd, ep, epn, epc, epp, run, hstate, back,
        _aw, stories, queued_backlog, _in_flight,
    ) in rows:
        story = current.get(slug, "")
        live_row = live.get(slug, {}) or {}
        state = station_state(
            running=run, story=story, hstate=hstate, done=done, total=n,
            backlog=back,
            dispatch_phase=live_row.get("dispatch_phase"),
            ledger_done=ledger_story_done(stories, story),
            verification_verdict=live_row.get("dispatch_verification_verdict"),
            verification_failed_gate=live_row.get("dispatch_verification_failed_gate"),
            queued_backlog=queued_backlog if live_row.get("dispatch_phase") == "building" else None,
            awaiting_operator_remedy=live_row.get("awaiting_operator_remedy"),
        )
        print(
            f"{slug:<9}{n:>8}{done:>6}{cmpl:>6}{proj:>6}{blkd:>6}"
            f"{ep:>7}{epn:>8}{epc:>8}{epp:>8}  {state}"
        )
    print("-" * (len(hdr) + 24))
    print(
        f"{'PYFORGE':<9}{tot['tot']:>8}{tot['done']:>6}{tot['cmpl']:>6}{tot['proj']:>6}"
        f"{tot['blkd']:>6}{tot['ep']:>7}{tot['epn']:>8}{tot['epc']:>8}{tot['epp']:>8}"
        f"  {len(building_slugs)}/8 building"
    )

    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
    print(
        f"\nNOW:          {tot['done']}/{tot['tot']} stories "
        f"({pct(tot['done'], tot['tot'])})"
        f"   ·   {tot['epn']}/{tot['ep']} epics ({pct(tot['epn'], tot['ep'])})"
    )
    print(
        f"COMPLETENESS: {tot['cmpl']}/{tot['tot']} stories "
        f"({pct(tot['cmpl'], tot['tot'])})"
        f"   ·   {tot['epc']}/{tot['ep']} epics ({pct(tot['epc'], tot['ep'])})"
    )
    if building_slugs:
        print(
            "BUILDING:     "
            + ", ".join(
                f"{s}:{current.get(s, '?')[:20]}" for s in sorted(building_slugs)
            )
        )
    else:
        print("BUILDING:     none")
    print(
        f"PROJECTION:   {tot['proj']}/{tot['tot']} stories "
        f"({pct(tot['proj'], tot['tot'])})"
        f"   ·   {tot['epp']}/{tot['ep']} epics ({pct(tot['epp'], tot['ep'])})"
        f"   (running/queued only)"
    )
    print(
        f"LEFT AFTER:   {tot['tot'] - tot['proj']} stories, "
        f"{tot['ep'] - tot['epp']} epics  ({tot['blkd']} blocked)"
    )
    print(
        "LIVE OPS:     `marshal watch --fleet` "
        "(or `marshal watch --project pyforge-<slug>`); "
        "restart prefer `marshal factory dispatch` (bmad-build-auto)"
    )

    # --- ATTENTION: what, if anything, is waiting on a human ----------------
    # Deterministic causes only. A pause Claude itself took (an epic boundary,
    # a decision story) cannot be seen from here and is added by the caller --
    # which is why the report always states one or the other explicitly rather
    # than staying silent and letting "no news" mean two different things.
    needs, watch = [], []
    open_prs_by_head = _open_prs_by_head_ref()
    for (
        slug, n, done, _cmpl, _proj, blkd, _ep, _epn, _epc, _epp, run, hstate, back,
        awaiting, _stories, _qb, _in_flight,
    ) in rows:
        live_row = live.get(slug, {}) or {}
        story = current.get(slug, live_row.get("story") or "")
        try:
            needs.extend(
                _dispatch_stranded_work_needs_lines(
                    slug=slug,
                    story=story,
                    live_row=live_row,
                    open_prs_by_head=open_prs_by_head,
                )
            )
        except Exception:  # noqa: BLE001 -- ATTENTION never kills the report
            watch.append(f"{slug}: could not check stranded dispatch work")
        # Same scoping as station_state()'s STUCK label above: a `refused`
        # verdict is dispatch-specific state that outlives the dispatch run
        # it describes, so `run` alone (true for ANY live engine on this
        # station, including an unrelated spin session) is not enough --
        # require `dispatch_phase` to confirm dispatch is the CURRENT
        # engine, not a stale field from an earlier, unrelated attempt.
        if (
            live_row.get("dispatch_verification_verdict") == "refused"
            and run
            and live_row.get("dispatch_phase") is not None
        ):
            gate = live_row.get("dispatch_verification_failed_gate") or "?"
            needs.append(
                f"{slug}: dispatch verify REFUSED ({gate}) on {current.get(slug, '?')}"
                f" — inspect dispatch-runs journal / epic_surfaces"
            )
        if hstate == "paused-on-escalation":
            reason = ((live.get(slug, {}) or {}).get("escalation_reason") or "unstated").split(chr(10))[0][:110]
            needs.append(f"{slug}: PAUSED on escalation ({reason}) -- "
                         f"run `/bmad-loop-resolve {current.get(slug, '<story>')}`")
        elif hstate == "unsupervised" and back:
            needs.append(
                f"{slug}: UNSUPERVISED with {back} story(ies) left -- "
                f"verify engine liveness first ({UNSUPERVISED_LIVENESS_FOLLOWUP}); "
                f"if dead, prefer `marshal factory dispatch pyforge-{slug}` "
                f"(bmad-build-auto); `marshal factory resume {slug}` only for a "
                f"still-active loop home"
            )
        elif hstate == "stopped" and back:
            needs.append(
                f"{slug}: run stopped with {back} story(ies) left -- "
                f"prefer `marshal factory dispatch pyforge-{slug}` "
                f"(bmad-build-auto); live ops: `marshal watch --project pyforge-{slug}`"
            )
        elif hstate == "unknown":
            watch.append(f"{slug}: status unreadable (stale journal) -- cosmetic "
                         f"unless it persists after a dispatch")
        elif hstate == "awaiting-operator":
            live_row = live.get(slug, {}) or {}
            spec_glob = live_row.get("missing_spec_escalation_glob")
            remedy = live_row.get("awaiting_operator_remedy")
            if spec_glob:
                needs.append(
                    f"{slug}: missing tracked spec for {current.get(slug, '?')} — "
                    f"author {spec_glob} (MRS-DISP-005 refuse, not idle)"
                )
            elif remedy:
                needs.append(f"{slug}: {remedy}")
        elif not run and back and done != n:
            watch.append(
                f"{slug}: {back} story(ies) backlog — idle (not draining); "
                f"prefer `marshal factory dispatch pyforge-{slug}` "
                f"(bmad-build-auto) when ready"
            )
        # bmad-loop 0.11 (marshal Story 25.5): stories parked at
        # `awaiting-operator` in the TRACKED ledger -- the durable board
        # record of external human-only actions still owed, which outlives
        # the run that parked them (the live-run case shows in the state
        # column above; this line is what survives once the run is gone).
        if awaiting:
            needs.append(f"{slug}: {awaiting} story(ies) parked "
                         f"{AWAITING_OPERATOR_LABEL} -- external actions "
                         f"owed; confirm in the loop home when done")
        if blkd:
            watch.append(f"{slug}: {blkd} story(ies) BLOCKED -- will not run, "
                         f"not waiting on you")
        # Story 28.15 (CAP-17), AC4: a warn-mode scope-violation advisory is
        # visible, never blocking -- the `watch` bucket, matching every
        # other non-blocking degrade above (unknown state, PR-query
        # failure). One line names the count + codes; the run's own
        # journal/`marshal status --format json` carries the full detail.
        advisories = (live.get(slug, {}) or {}).get("scope_advisories") or []
        if advisories:
            # `advisories` comes from `marshal status --format json` subprocess
            # stdout parsed in `running_stations()` (outside that function's own
            # try/except) -- a non-dict item, or a `"code"` that is explicitly
            # `None`, is guarded here rather than trusted, since `.get(...,
            # "?")` only substitutes the default when the key is ABSENT.
            # Deduped (`dict.fromkeys`) so several violations sharing one code
            # render once, not repeated -- the `len(advisories)` count below
            # stays the true total, unaffected by the dedup.
            codes = ",".join(dict.fromkeys(
                str(a.get("code") or "?") if isinstance(a, dict) else "?"
                for a in advisories
            ))
            watch.append(f"{slug}: {len(advisories)} scope-violation advisory(ies) "
                         f"(warn mode, not blocking) -- {codes}")
        # Story 53.2 review (I1): `execute_dispatch_land`'s envelope findings
        # (MRS-DISP-047/048) -- same non-dict/None guarding as `advisories`
        # above. An ERROR-severity finding (MRS-DISP-048) means the landing
        # was refused and a human must act, so it goes to `needs`; anything
        # else (MRS-DISP-047, WARN) is FYI in `watch`, matching the
        # scope-advisory treatment.
        land_findings = (live.get(slug, {}) or {}).get("landing_findings") or []
        if land_findings:
            errors = [
                f for f in land_findings
                if isinstance(f, dict) and f.get("severity") == "error"
            ]
            warns = [f for f in land_findings if f not in errors]
            if errors:
                codes = ",".join(dict.fromkeys(
                    str(f.get("code") or "?") for f in errors
                ))
                needs.append(f"{slug}: landing refused ({len(errors)} finding(s)) "
                             f"-- {codes}")
            if warns:
                codes = ",".join(dict.fromkeys(
                    str(f.get("code") or "?") if isinstance(f, dict) else "?"
                    for f in warns
                ))
                watch.append(f"{slug}: {len(warns)} landing finding(s) "
                             f"(not blocking) -- {codes}")
    try:
        prs = subprocess.run(
            ["gh", "pr", "list", "--repo", "rxm7706/local-recipes",
             "--json", "number,title", "-q", r'.[]|"#\(.number) \(.title)"' ],
            cwd=REPO, capture_output=True, text=True, timeout=120).stdout.split("\n")
        prs = [x for x in prs if x.strip()]
        if prs:
            needs.append(f"{len(prs)} PR(s) still OPEN (auto-merge should have "
                         f"cleared these -- CI red or a conflict): " + "; ".join(prs[:4]))
    except Exception:
        watch.append("could not query open PRs")

    try:
        needs.extend(_baseline_drift_needs_lines(baseline_drift_findings()))
    except Exception:  # noqa: BLE001 -- same ATTENTION-probe degrade idiom
        watch.append("could not run baseline-drift-check")

    try:
        for slug, branch, n in loop_home_staleness():
            needs.append(f"{slug}: loop home ({branch}) is {n} commit(s) behind "
                         f"origin/main -- resync the loop home before its next spin")
    except Exception:
        watch.append("could not check loop-home staleness")

    try:
        primary_behind = primary_checkout_staleness()
        if primary_behind is not None:
            needs.append(f"primary checkout is {primary_behind} commit(s) behind "
                         f"origin/main -- run `git pull` (an unattended CAP-4 land "
                         f"can merge without you noticing)")
    except Exception:
        watch.append("could not check primary-checkout staleness")

    try:
        for finding in bmad_core_drift_findings():
            # Review finding: an externally-sourced Finding.message (this
            # source's own degrade_on_exception wrapper can embed a
            # multi-line yaml.YAMLError/tomllib.TOMLDecodeError context
            # snippet) rendered raw would read as extra, indistinguishable
            # bullet lines -- same risk class `escalation_reason` above
            # already guards against with an identical split/truncate.
            # `check` (e.g. "bmad-method-version-drift" vs.
            # "bmad-method-upstream-drift") tags which capability fired,
            # since CAP-1/CAP-2 can both warn at once.
            check = finding.get("check", "bmad-method")
            message = finding.get("message", "drift detected").split(chr(10))[0][:110]
            watch.append(f"{check}: {message}")
    except Exception:
        watch.append("could not check bmad-method core version drift")

    try:
        for finding in verification_staleness_findings():
            # Review finding, patch: use the already-formatted `message`
            # DIRECTLY, exactly like the `bmad_core_drift_findings` consumer
            # immediately above -- a hand-reassembled string from `evidence`
            # fields had already drifted from `_due_for_verification_message`'s
            # own coverage-branch text (missing its trailing period), and a
            # second string-building copy of the same format is one more
            # place for the two to silently diverge again later. Same
            # split/truncate discipline as the bmad-core-drift case, for the
            # same reason (an externally-sourced message must never inject
            # extra, indistinguishable bullet lines).
            message = finding.get("message", "verification staleness detected")
            watch.append(message.split(chr(10))[0][:110])
    except Exception:  # noqa: BLE001 -- matches every other ATTENTION probe
        # in this file (loop_home_staleness/bmad_core_drift_findings/PR
        # query/baseline-drift-check above): degrade to one "could not
        # check" line rather than crash the whole report.
        watch.append("could not check verification staleness")

    try:
        watch.extend(_dream_chain_watch_lines(dream_chain_gap_findings()))
    except Exception:  # noqa: BLE001 -- same ATTENTION-probe degrade idiom
        # as the verification-staleness probe directly above: one "could
        # not check" line rather than crashing the whole report. Reached on
        # any probe or assembly failure (exit not in {0, 2}, timeout,
        # malformed or wrong-shape JSON, an unexpected item shape) -- never
        # on the normal any-gap path, which is exit 2 with valid JSON (see
        # dream_chain_gap_findings' docstring).
        watch.append("could not check dream-chain gaps")

    try:
        for finding in sibling_dreams_drift_findings():
            check = finding.get("check", "sibling-dreams-drift")
            message = finding.get("message", "sibling dream drift").split(chr(10))[0][:110]
            watch.append(f"{check}: {message}")
    except Exception:  # noqa: BLE001 -- same ATTENTION degrade idiom
        watch.append("could not check sibling-dreams drift")

    try:
        for finding in capability_effect_findings():
            check = finding.get("check", "capability-effect")
            message = finding.get("message", "capability effect gap").split(chr(10))[0][:110]
            watch.append(f"{check}: {message}")
    except Exception:  # noqa: BLE001 -- same ATTENTION degrade idiom
        watch.append("could not check capability-effect")

    try:
        for finding in status_body_consistency_findings():
            check = finding.get("check", "status-body-consistency")
            message = finding.get("message", "status/body drift").split(chr(10))[0][:110]
            evidence = finding.get("evidence") or {}
            precision = evidence.get("precision")
            if precision is not None:
                message = f"{message} (precision={precision:.3f})"
            watch.append(f"{check}: {message}")
    except Exception:  # noqa: BLE001 -- same ATTENTION degrade idiom
        watch.append("could not check status-body-consistency")

    print("\nATTENTION:")
    if needs:
        for item in needs:
            print(f"  >> {item}")
    else:
        print("  none of the stations is waiting on you (no escalation, no dead run,"
              " no open PR)")
    for item in watch:
        print(f"   - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
