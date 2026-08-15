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
