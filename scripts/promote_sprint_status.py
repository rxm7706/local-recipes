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
"""

from __future__ import annotations

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


def main() -> int:
    gen = _load_generate()
    wrote, unchanged, skipped = [], [], []

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
        dest.write_text(text, encoding="utf-8")
        wrote.append(f"{key} ({len(statuses)})")

    print(f"sprint-status ledger sync — wrote {len(wrote)}, unchanged {len(unchanged)}, "
          f"skipped {len(skipped)}")
    for label, items in (("wrote", wrote), ("unchanged", unchanged), ("skipped", skipped)):
        for i in items:
            print(f"  {label:9} {i}")
    if not wrote and not unchanged:
        print("\nNOTHING promoted — every feed was missing or unparseable.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
