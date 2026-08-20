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
    repo: pathlib.Path = REPO, timeout: int = 15
    # 15s, not 5s: the subprocess bounds only its own HTTP call at
    # `_UPSTREAM_FETCH_TIMEOUT_SECONDS = 5.0` -- this timeout must also
    # cover interpreter startup and package import before that call even
    # starts, so it carries a margin rather than matching the inner bound.
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
                     live.get(slug, {}).get("state", "idle"), counts["backlog"]))
        for k, v in (("tot", len(stories)), ("done", counts["done"]), ("proj", proj),
                     ("blkd", counts["blocked"]), ("ep", len(by_epic)),
                     ("epn", ep_now), ("epp", ep_proj)):
            tot[k] += v

    hdr = (f"{'station':<9}{'stories':>8}{'done':>6}{'->proj':>8}{'blkd':>6}"
           f"{'epics':>7}{'ep now':>8}{'->proj':>8}  {'state'}")
    print(hdr)
    print("-" * (len(hdr) + 24))
    for (slug, n, done, proj, blkd, ep, epn, epp, run, hstate, back) in rows:
        if run:
            state = f"RUNNING  {current.get(slug, '')[:38]}"
        elif hstate == "paused-on-escalation":
            state = "PAUSED - needs you (escalation)"
        elif hstate in ("stopped", "unsupervised", "unknown") and back:
            state = f"{hstate.upper()} - {back} left, needs re-spin"
        elif done == n:
            state = "complete"
        elif back:
            state = f"idle - {back} not started"
        else:
            state = "idle"
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
    for (slug, n, done, proj, blkd, ep, epn, epp, run, hstate, back) in rows:
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
