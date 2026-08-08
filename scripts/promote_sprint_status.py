#!/usr/bin/env python3
"""Promote each project's Tier-3 story-status map to a TRACKED twin.

`_bmad-output/projects/*/implementation-artifacts/` is gitignored wholesale
(`.gitignore:736`), so `sprint-status.yaml` — the only place that knows a story is
done — does not survive a clone and **CI cannot read it**. The dashboard therefore
reconstructed DONE from commit-subject archaeology, which fails the moment a
completion signal is not an ancestor of `main`: squash-merging PR #132 made Epic
10's `Merge bmad-loop/<run>/10-N-…` subjects unreachable, and the published board
sat at 36/38 with a ticking wall clock on a finished story.

This promotes the `development_status:` map to
`planning-artifacts/sprint-status-ledger.yaml`, which IS tracked, so the deploy
reads truth instead of guessing. It is the same move this repo already made for
`deferred-work-ledger.md` in atlas and doctor, for the same reason.

The twin is written in the SAME shape the Tier-3 feed uses, so
`generate.py:parse_sprint_status` reads it unchanged — no second parser to drift.

Idempotent: re-running with no upstream change rewrites nothing, so it is safe in
a pre-commit hook or a loop's post-story step.

**Monotonic in terminal states** (added 2026-08-08, DW-SYNC-2026-08-08-1). The Tier-3
feed is a statement of *intent* — bmad-loop marks a story `done` at DEV completion, and
a feed can lag, be truncated by a worktree teardown, or predate work that landed by
another route. The tracked twin is the record of *fact*. So a sync that let the feed
overwrite the twin wholesale could — and did — destroy real completions: on 2026-08-08
a stale marshal feed silently dropped six `done` keys and printed success. Measured the
same day, `pyforge-atlas` was one command away from losing **35**.

This script therefore refuses any write that moves a key backwards out of `done`, or
drops a `done` key entirely, naming every affected key and exiting non-zero. Override
with `--allow-regression` only when the twin is genuinely the wrong one. The pre-existing
empty-feed guard below is the same idea at whole-file granularity; this is its per-key
counterpart, which is where the real losses happen.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE = REPO_ROOT / "docs" / "dashboard" / "generate.py"
LEDGER_NAME = "sprint-status-ledger.yaml"

_HEADER = """\
# GENERATED — do not hand-edit. Regenerate with:
#     pixi run -e local-recipes sprint-ledger-sync
#
# TRACKED twin of {src}
# which is gitignored Tier-3 (.gitignore:736) and therefore invisible to CI and
# absent from every fresh clone. The dashboard's deploy-time render reads THIS
# file, so a story's completion no longer has to be reconstructed from commit
# subjects — the archaeology that failed when squash-merging PR #132 made Epic
# 10's bmad-loop merge subjects unreachable from main.
#
# Same shape as the Tier-3 feed on purpose: generate.py's parse_sprint_status
# reads both, so there is no second parser to drift.
#
# project: {project}
# stories: {count}
development_status:
"""


def _load_generate():
    spec = importlib.util.spec_from_file_location("_dashboard_generate", GENERATE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_dashboard_generate"] = mod
    spec.loader.exec_module(mod)
    return mod


def ledger_path_for(slug: str) -> Path:
    return (REPO_ROOT / "_bmad-output" / "projects" / slug
            / "planning-artifacts" / LEDGER_NAME)


def render(project: str, src_rel: str, statuses: dict[str, str]) -> str:
    body = "".join(f"  {k}: {v}\n" for k, v in sorted(statuses.items()))
    return _HEADER.format(src=src_rel, project=project, count=len(statuses)) + body


# Statuses that must never move backwards. `done` is the only terminal state in this
# vocabulary — everything else (backlog / in-progress / blocked / optional) is a
# legitimate two-way transition and is deliberately NOT guarded.
TERMINAL = frozenset({"done"})


def regressions(existing: dict[str, str], incoming: dict[str, str]) -> list[tuple[str, str, str]]:
    """Keys the incoming feed would move OUT of a terminal state, as
    ``(key, old, new)`` where ``new`` is ``"<absent>"`` if the feed drops the key
    entirely. Dropping a `done` key is the more dangerous of the two — it leaves no
    trace in the rendered file at all — so it is reported the same way, not skipped."""
    out: list[tuple[str, str, str]] = []
    for key, old in sorted(existing.items()):
        if old not in TERMINAL:
            continue
        new = incoming.get(key)
        if new is None:
            out.append((key, old, "<absent>"))
        elif new not in TERMINAL:
            out.append((key, old, new))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sprint-ledger-sync",
        description="Promote each project's Tier-3 story-status map to its tracked twin.",
    )
    ap.add_argument(
        "--allow-regression",
        action="store_true",
        help="Write even when the feed would move a key out of `done` or drop it. "
             "Every affected key is still named. Use only when the tracked twin is "
             "genuinely the wrong one.",
    )
    args = ap.parse_args(argv)

    gen = _load_generate()
    wrote, unchanged, skipped, refused = [], [], [], []

    for key, rel in sorted(gen.PROJECT_SOURCES.items()):
        src = REPO_ROOT / rel
        slug = gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")
        if not src.is_file():
            skipped.append(f"{key} (no Tier-3 feed at {rel})")
            continue
        statuses = gen.parse_sprint_status(src)
        if not statuses:
            # An empty map would silently blank a good twin — refuse rather than
            # write nothing over something.
            skipped.append(f"{key} (feed parsed 0 statuses — refusing to blank the twin)")
            continue
        dest = ledger_path_for(slug)
        if not dest.parent.is_dir():
            skipped.append(f"{key} (no planning-artifacts dir at {dest.parent})")
            continue
        text = render(key, rel, statuses)
        if dest.is_file() and dest.read_text(encoding="utf-8") == text:
            unchanged.append(f"{key} ({len(statuses)})")
            continue

        # Per-key monotonic guard (DW-SYNC-2026-08-08-1). Read the twin we are about
        # to overwrite and refuse to un-finish anything, unless explicitly allowed.
        if dest.is_file():
            lost = regressions(gen.parse_sprint_status(dest), statuses)
            if lost:
                detail = ", ".join(f"{k} ({old} -> {new})" for k, old, new in lost)
                if not args.allow_regression:
                    refused.append(
                        f"{key} — feed would un-finish {len(lost)} key(s): {detail}"
                    )
                    continue
                print(f"  WARNING   {key}: --allow-regression, un-finishing "
                      f"{len(lost)} key(s): {detail}")

        dest.write_text(text, encoding="utf-8")
        wrote.append(f"{key} ({len(statuses)})")

    print(f"sprint-status ledger sync — wrote {len(wrote)}, unchanged {len(unchanged)}, "
          f"skipped {len(skipped)}, refused {len(refused)}")
    for label, items in (("wrote", wrote), ("unchanged", unchanged),
                         ("skipped", skipped), ("refused", refused)):
        for i in items:
            print(f"  {label:9} {i}")
    if refused:
        print("\nREFUSED: the Tier-3 feed is BEHIND the tracked twin for the project(s)\n"
              "above. The feed states intent; the twin is the record of fact — so this\n"
              "is far more often a stale feed than a wrong twin. Reconcile the feed, or\n"
              "pass --allow-regression if the twin really is the wrong one.")
        return 1
    if not wrote and not unchanged:
        print("\nNOTHING promoted — every feed was missing or unparseable.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
