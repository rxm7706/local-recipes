#!/usr/bin/env python3
"""PyForge fleet progress REPORT (not a detector -- never gates, always exits 0).

Lives in scripts/ rather than a scratchpad so a scheduled status check survives a
session restart; allowlisted in spec_surface_allowlist.txt for the same reason
`unpushed_work_check.py` is -- it is operator tooling, not a governed surface.

PyForge fleet progress: done / in-progress / projected / blocked, per station.

Measured from each station's TRACKED sprint-status-ledger.yaml (the twin of the
gitignored Tier-3 feed) — never from an ad-hoc regex over commit subjects, and
never from the board, which lags until a merge to main.

`->proj` is what the CURRENTLY RUNNING stations will reach if they work their
backlog to completion: done + backlog for a running station, done alone for an
idle one. Blocked stories are excluded from the projection by construction —
they are not `backlog` and will not be dispatched.

An epic counts as done only when EVERY story in it is done; `->proj` applies the
same rule to the projected state, so a single blocked story keeps its epic open
(steward E8 is exactly that case).

Running stations are detected live from `marshal status`, so the table reflects
reality rather than a hardcoded list that would rot the moment a run ends.
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


def station_state(*, running: bool, story: str, hstate: str, done: int,
                  total: int, backlog: int) -> str:
    """The state-column cell for one station row -- pure, so the meta test
    (test_fleet_picture_awaiting_operator.py) can pin the naming without
    driving main()'s subprocess sweep. `hstate` is `marshal status`'s own
    derived state for the station ("idle" when marshal reported nothing).

    A `hstate == "awaiting-operator"` station (bmad-loop 0.11: >=1 story
    parked for external human-only actions, nothing else active) is NAMED
    with the confirm remedy -- never folded into the stopped/unsupervised
    "needs re-spin" bucket: the parked story's work is already committed,
    so `bmad-loop confirm` is the next action, not a re-spin."""
    if running:
        return f"RUNNING  {story[:38]}"
    if hstate == "awaiting-operator":
        return AWAITING_OPERATOR_LABEL
    if hstate == "paused-on-escalation":
        return "PAUSED - needs you (escalation)"
    if hstate in ("stopped", "unsupervised", "unknown") and backlog:
        return f"{hstate.upper()} - {backlog} left, needs re-spin"
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


def bmad_core_drift_findings(
    repo: pathlib.Path = REPO, timeout: int = 20
    # 20s vs the source's own ~15s worst-case network design budget: since
    # Story 14.1 (CAP-4) the gather issues CAP-2's core fetch (bounded at
    # `_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0`) PLUS a suite fetch loop under
    # its own 5.0s shared deadline (`_SUITE_FETCH_TOTAL_BUDGET_SECONDS`);
    # Story 15.2 adds one more CORE-side fetch (the SelfExplainML channel
    # lookup, also bounded at `_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0`,
    # issued only when CAP-2's own fetch already resolved) -- 5+5+5 = 15s
    # inner worst case, up from 10s pre-15.2. This timeout must also cover
    # interpreter startup and package import before any of the three
    # starts, so it is bumped by the same 5s the inner budget grew
    # (15 -> 20), preserving the ~5s margin Story 14.1 already established
    # as "still positive" rather than letting it shrink to zero.
) -> list[dict]:
    """WARN-status Findings from ``pyforge.doctor``'s bmad-method-version-
    drift source (Story 10.1/10.2's CAP-1/CAP-2 -- installed BMAD-METHOD
    behind pixi.toml's declared floor, and/or behind the latest release
    published upstream on npm; Story 15.2's CORE-side channel/recipe drift
    checks -- see that source module for the fuller picture).

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


def verification_staleness_findings(
    repo: pathlib.Path = REPO, timeout: int = 90
    # 90s, not `bmad_core_drift_findings`'s 20s: measured live against this
    # repo's own real fleet (`time python -m pyforge.doctor.sources
    # due-for-verification --json`) at ~48s -- the due-for-verification
    # source, unlike the cheap bmad-method-version-drift check, does real
    # per-entry `git log`/`git grep` churn and mechanical-verdict work
    # (Stories 11.2/11.3) across the fleet's 400+ tracked entries, so a 20s
    # bound would degrade EVERY real invocation, defeating this story's own
    # "ambient, always-visible" Intent. 90s carries a ~2x margin over the
    # measured cost, the same proportional margin `bmad_core_drift_findings`
    # itself carries over its own inner HTTP bound.
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
                "escalation_reason": r.get("escalation_reason"),
                "escalation_artifact": r.get("escalation_artifact"),
            }
            if r.get("state") == "running":
                running.add(slug)
        return running, info
    except Exception:
        return set(), {}


def main() -> int:
    running, live = running_stations()
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

        is_running = slug in running
        proj = counts["done"] + (counts["backlog"] if is_running else 0)
        ep_now = sum(1 for e in by_epic.values() if all(v == "done" for v in e))
        ep_proj = sum(1 for e in by_epic.values()
                      if all(v == "done" or (v == "backlog" and is_running) for v in e))

        rows.append((slug, len(stories), counts["done"], proj, counts["blocked"],
                     len(by_epic), ep_now, ep_proj, is_running,
                     live.get(slug, {}).get("state", "idle"), counts["backlog"],
                     counts["awaiting-operator"]))
        for k, v in (("tot", len(stories)), ("done", counts["done"]), ("proj", proj),
                     ("blkd", counts["blocked"]), ("ep", len(by_epic)),
                     ("epn", ep_now), ("epp", ep_proj)):
            tot[k] += v

    hdr = (f"{'station':<9}{'stories':>8}{'done':>6}{'->proj':>8}{'blkd':>6}"
           f"{'epics':>7}{'ep now':>8}{'->proj':>8}  {'state'}")
    print(hdr)
    print("-" * (len(hdr) + 24))
    for (slug, n, done, proj, blkd, ep, epn, epp, run, hstate, back, _aw) in rows:
        state = station_state(running=run, story=current.get(slug, ""),
                              hstate=hstate, done=done, total=n, backlog=back)
        print(f"{slug:<9}{n:>8}{done:>6}{proj:>8}{blkd:>6}{ep:>7}{epn:>8}{epp:>8}  {state}")
    print("-" * (len(hdr) + 24))
    print(f"{'PYFORGE':<9}{tot['tot']:>8}{tot['done']:>6}{tot['proj']:>8}"
          f"{tot['blkd']:>6}{tot['ep']:>7}{tot['epn']:>8}{tot['epp']:>8}"
          f"  {len(running)}/8 running")

    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"
    print(f"\nNOW:        {tot['done']}/{tot['tot']} stories ({pct(tot['done'], tot['tot'])})"
          f"   ·   {tot['epn']}/{tot['ep']} epics ({pct(tot['epn'], tot['ep'])})")
    print(f"IN FLIGHT:  {len(running)} station(s) — "
          + ", ".join(f"{s}:{current.get(s, '?')[:28]}" for s in sorted(running)))
    print(f"PROJECTED:  {tot['proj']}/{tot['tot']} stories ({pct(tot['proj'], tot['tot'])})"
          f"   ·   {tot['epp']}/{tot['ep']} epics ({pct(tot['epp'], tot['ep'])})")
    print(f"LEFT AFTER: {tot['tot'] - tot['proj']} stories, {tot['ep'] - tot['epp']} epics"
          f"  ({tot['blkd']} blocked)")

    # --- ATTENTION: what, if anything, is waiting on a human ----------------
    # Deterministic causes only. A pause Claude itself took (an epic boundary,
    # a decision story) cannot be seen from here and is added by the caller --
    # which is why the report always states one or the other explicitly rather
    # than staying silent and letting "no news" mean two different things.
    needs, watch = [], []
    for (slug, n, done, proj, blkd, ep, epn, epp, run, hstate, back, awaiting) in rows:
        if hstate == "paused-on-escalation":
            reason = ((live.get(slug, {}) or {}).get("escalation_reason") or "unstated").split(chr(10))[0][:110]
            needs.append(f"{slug}: PAUSED on escalation ({reason}) -- "
                         f"run `/bmad-loop-resolve {current.get(slug, '<story>')}`")
        elif hstate in ("stopped", "unsupervised") and back:
            needs.append(f"{slug}: run {hstate} with {back} story(ies) left -- "
                         f"needs `marshal factory spin pyforge-{slug}`")
        elif hstate == "unknown":
            watch.append(f"{slug}: status unreadable (stale journal) -- cosmetic "
                         f"unless it persists after a spin")
        elif not run and back and done != n:
            needs.append(f"{slug}: idle with {back} story(ies) not started -- "
                         f"needs a spin if it should be running")
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
        drift = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "bmad_loop_baseline_drift_check.py")],
            cwd=REPO, capture_output=True, text=True, timeout=60)
        if drift.returncode == 1:
            n = sum(1 for line in drift.stdout.splitlines() if line.startswith("  ✗"))
            needs.append(f"{n} unrecovered baseline-drift defer(s) -- real reviewed "
                         f"work stranded by bmad-loop's stuck-orchestrator bug: run "
                         f"`pixi run -e local-recipes baseline-drift-check` for "
                         f"story/run/preserve-ref details, then recover per "
                         f"docs/dreams/bmad-loop-baseline-drift.md")
    except Exception:
        watch.append("could not run baseline-drift-check")

    try:
        for slug, branch, n in loop_home_staleness():
            needs.append(f"{slug}: loop home ({branch}) is {n} commit(s) behind "
                         f"origin/main -- resync the loop home before its next spin")
    except Exception:
        watch.append("could not check loop-home staleness")

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
