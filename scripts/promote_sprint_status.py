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
``fleet_scan.parse_sprint_status`` reads it unchanged — no second parser to drift.

Idempotent: re-running with no upstream change rewrites nothing, so it is safe in
a pre-commit hook or a loop's post-story step.

**Monotonic in terminal states** (added 2026-08-08, DW-SYNC-2026-08-08-1). The Tier-3
feed is a statement of *intent* — bmad-loop marks a story `done` at DEV completion, and
a feed can lag, be truncated by a worktree teardown, or predate work that landed by
another route. The tracked twin is the record of *fact*. So a sync that let the feed
overwrite the twin wholesale could — and did — destroy real completions: on 2026-08-08
a stale marshal feed silently dropped six `done` keys and printed success. Measured the
same day, `pyforge-atlas` was one command away from losing **35**.

This script therefore refuses any write that moves a key backwards out of `done` or
story `blocked`, or drops such a key entirely, naming every affected key and exiting
non-zero. `done` is STRICTLY senior to `blocked` — a key moving `done` -> `blocked`
is refused too, not treated as a lateral move between two protected states (found
live 2026-09-10, DW-SYNC-2026-09-10-1: a genuinely `done` story's stale Tier-3
`blocked` value silently overwrote the tracked twin's correct `done` because the
original guard treated `done` and `blocked` as interchangeable). Twin-only keys
absent from the feed are refused on the bare path too — not only under
``--repair-feed``. Override with ``--allow-regression`` only when the twin is
genuinely the wrong one. The pre-existing empty-feed guard below is the same idea
at whole-file granularity; this is its per-key counterpart, which is where the real
losses happen.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE = REPO_ROOT / "scripts" / "fleet_scan.py"
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
# Same shape as the Tier-3 feed on purpose: fleet_scan.parse_sprint_status
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


# Statuses that must never move backwards. `done` is terminal; `blocked` is sticky
# on stories (mirrors sprint_plan.py:77) — both are protected from feed overwrite.
TERMINAL = frozenset({"done"})
STICKY_STATUSES = {"story": frozenset({"blocked"})}

_EPIC_KEY_RE = re.compile(r"^epic-(\d+)$")
_RETRO_KEY_RE = re.compile(r"^epic-(\d+)-retrospective$")
_STORY_KEY_RE = re.compile(r"^(\d+)-(\d+)([a-z]?)-.+")
_STORY_PROGRESS_RANK = {
    "backlog": 0,
    "ready-for-dev": 1,
    "in-progress": 2,
    "review": 3,
    "done": 4,
}


def _classify_key(key: str) -> tuple[str, int] | None:
    m = _RETRO_KEY_RE.match(key)
    if m:
        return "retro", int(m.group(1))
    m = _EPIC_KEY_RE.match(key)
    if m:
        return "epic", int(m.group(1))
    m = _STORY_KEY_RE.match(key)
    if m:
        return "story", int(m.group(1))
    return None


def _is_protected(kind: str | None, status: str) -> bool:
    if status in TERMINAL:
        return True
    return kind == "story" and status in STICKY_STATUSES.get("story", frozenset())


def regressions(existing: dict[str, str], incoming: dict[str, str]) -> list[tuple[str, str, str]]:
    """Keys the incoming feed would move OUT of a protected state (``done`` or story
    ``blocked``), as ``(key, old, new)`` where ``new`` is ``"<absent>"`` if the feed
    drops the key entirely.

    ``done`` is STRICTLY senior to ``blocked``: unlike the other protected pairing
    (``blocked`` guarded only against silently reverting to an earlier-progress
    status like ``backlog``), a ``done`` key moving to ANY other value — including
    ``blocked`` — is a regression, never accepted as a lateral move between two
    equally-protected states. Found live 2026-09-10: a genuinely `done` story
    (confirmed by its own spec's frontmatter and a landed commit) had a stale
    Tier-3 `blocked` value that neither this check nor `--repair-feed` caught,
    because both previously treated `done` and `blocked` as interchangeable
    "protected" states — `done -> blocked` silently overwrote the tracked twin's
    correct `done` with no refusal and no repair."""
    out: list[tuple[str, str, str]] = []
    for key, old in sorted(existing.items()):
        kind = _classify_key(key)
        kind_name = kind[0] if kind else None
        new = incoming.get(key)
        if old == "done":
            if new != "done":
                out.append((key, old, new if new is not None else "<absent>"))
            continue
        if not _is_protected(kind_name, old):
            continue
        if new is None:
            out.append((key, old, "<absent>"))
        elif not _is_protected(kind_name, new):
            out.append((key, old, new))
    return out


def _compute_epic_status(story_statuses: list[str]) -> str:
    if not story_statuses:
        return "backlog"
    if all(s == "done" for s in story_statuses):
        return "done"
    active = [s for s in story_statuses if s != "blocked"]
    if not active:
        return "backlog"
    if max(_STORY_PROGRESS_RANK.get(s, 0) for s in active) >= 1:
        return "in-progress"
    return "backlog"


def apply_epic_rollups(statuses: dict[str, str]) -> dict[str, str]:
    """Refresh ``epic-N`` rows from child story statuses before writing the twin."""
    by_epic: dict[int, list[str]] = {}
    for key, value in statuses.items():
        parsed = _classify_key(key)
        if parsed and parsed[0] == "story":
            by_epic.setdefault(parsed[1], []).append(value)
    out = dict(statuses)
    for epic_num, story_values in by_epic.items():
        epic_key = f"epic-{epic_num}"
        if epic_key in out:
            out[epic_key] = _compute_epic_status(story_values)
    return out


def repair_feed(
    feed_path: Path,
    incoming: dict[str, str],
    twin_values: dict[str, str],
) -> tuple[dict[str, str] | None, list[tuple[str, str, str]], list[str]]:
    """The merge-then-write half of ``--repair-feed`` (extracted so
    ``pyforge.marshal.cli.deploy::run_reconcile_completions`` (Story 5.9,
    "a story finished by hand is not invisible to the ledger") can reuse
    the SAME logic to close the Tier-3 divergence its own ledger-advancing
    write creates, scoped to only the keys it just advanced, rather than
    re-deriving it). ``incoming`` is the Tier-3 feed's own already-parsed
    ``development_status`` map; ``twin_values`` is the tracked twin's own
    state for whichever keys the CALLER cares about — ``main()``'s own
    ``--repair-feed`` path below passes the twin's FULL map (every key),
    while ``run_reconcile_completions`` passes ONLY the raw keys it just
    wrote ``done`` for, so a scoped call never touches any OTHER
    pre-existing divergence the twin may carry.

    Computes ``regressions()`` (a terminal state the feed would lose) plus
    ``missing`` (present in ``twin_values``, absent from ``incoming``
    altogether — the same "absence is loss whatever the state" case
    ``main()`` already guards, folded in here so a caller need run only
    ONE function). When there is nothing to repair (both empty), returns
    ``(None, [], [])`` and writes nothing. Otherwise folds ``twin_values``'
    own state for every ``missing``/``lost`` key back into ``incoming``,
    writes the merged map into ``feed_path`` — preserving everything in
    the file before its own ``development_status:`` marker untouched —
    and returns ``(merged, lost, missing)``.

    Never commits: ``feed_path`` (the Tier-3 feed) is gitignored (Tier-3),
    so there is nothing to commit — only ``sprint-status-ledger.yaml``,
    the tracked twin, is ever git-committed, and that happens elsewhere."""
    lost = regressions(twin_values, incoming)
    missing = [k for k in twin_values if k not in incoming]
    if not lost and not missing:
        return None, lost, missing
    merged = dict(incoming)
    for k in missing:
        merged[k] = twin_values[k]
    for k, old, _new in lost:
        merged[k] = old
    feed_body = "".join(f"  {k}: {v}\n" for k, v in sorted(merged.items()))
    head = feed_path.read_text(encoding="utf-8").split("development_status:")[0]
    feed_path.write_text(head + "development_status:\n" + feed_body, encoding="utf-8")
    return merged, lost, missing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sprint-ledger-sync",
        description="Promote each project's Tier-3 story-status map to its tracked twin.",
    )
    ap.add_argument(
        "--project",
        metavar="KEY",
        action="append",
        help="Limit the sync to this dashboard key (repeatable). Default is EVERY "
             "project, which is how a single-project task destroyed 96 `done` markers "
             "across four other stations on 2026-08-08 — scope deliberately when the "
             "work is scoped.",
    )
    ap.add_argument(
        "--repair-feed",
        action="store_true",
        help="Reverse direction: where the tracked twin holds a `done` the Tier-3 feed "
             "has lost, write it BACK into the feed. Closes the loop a one-way sync "
             "leaves open — a truncated feed otherwise makes every later sync refuse "
             "forever, with no sanctioned way to converge.",
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

    selected = set(args.project or [])
    if selected:
        unknown = selected - set(gen.PROJECT_SOURCES)
        if unknown:
            print(f"unknown --project key(s): {', '.join(sorted(unknown))}; "
                  f"valid: {', '.join(sorted(gen.PROJECT_SOURCES))}")
            return 2

    for key, rel in sorted(gen.PROJECT_SOURCES.items()):
        if selected and key not in selected:
            continue
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

        # Per-key monotonic guard (DW-SYNC-2026-08-08-1). Read the twin we are about
        # to overwrite and refuse to un-finish anything, unless explicitly allowed.
        if dest.is_file():
            existing = gen.parse_sprint_status(dest)
            lost = regressions(existing, statuses)
            # Repair triggers on EITHER a terminal regression or a key the feed has
            # simply lost. The first cut keyed only on regression, so a feed already
            # carrying every `done` still silently dropped the twin's seven
            # `epic-N-retrospective: optional` rows — absence is loss whatever the state.
            missing = [k for k in existing if k not in statuses]
            if (lost or missing) and args.repair_feed:
                # The twin is the durable record; the feed is the lossy one. Push the
                # twin's terminal states back into the feed so the two converge, then
                # proceed with a now-clean promotion. `repair_feed` (extracted so
                # `pyforge.marshal.cli.deploy::run_reconcile_completions` can reuse the
                # SAME merge-then-write logic, scoped to just its own advanced keys)
                # recomputes `lost`/`missing` from `(statuses, existing)` — identical
                # to what was already computed above, so the counts below are unchanged.
                merged, lost, missing = repair_feed(src, statuses, existing)
                # `repair_feed` only returns `None` when its OWN recomputed
                # `lost`/`missing` both come up empty -- structurally
                # impossible here since we just entered this branch on the
                # identical `(lost or missing)` condition from the SAME
                # `(statuses, existing)` inputs. Asserted, not silently
                # trusted, now that the recomputation lives in a separate
                # function a future edit could decouple from this check.
                assert merged is not None
                print(f"  REPAIRED  {key}: restored {len(lost)} regressed + "
                      f"{len(missing)} missing key(s) into the Tier-3 feed from the "
                      f"tracked twin")
                statuses = merged
                lost = []
                missing = []
            if lost or missing:
                if lost:
                    detail = ", ".join(f"{k} ({old} -> {new})" for k, old, new in lost)
                    label = "un-finish"
                else:
                    detail = ", ".join(sorted(missing))
                    label = "drop"
                if not args.allow_regression:
                    refused.append(
                        f"{key} — feed would {label} {len(lost or missing)} "
                        f"twin key(s): {detail}"
                    )
                    continue
                print(f"  WARNING   {key}: --allow-regression, {label}ing "
                      f"{len(lost or missing)} key(s): {detail}")

        statuses = apply_epic_rollups(statuses)
        text = render(key, rel, statuses)
        if dest.is_file() and dest.read_text(encoding="utf-8") == text:
            unchanged.append(f"{key} ({len(statuses)})")
            continue

        _write_ledger_locked(dest, text)
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


def _write_ledger_locked(dest: Path, text: str) -> None:
    """Write ``dest`` under ``FsPort.acquire_advisory_lock`` when
    ``pyforge.marshal`` is importable (Story 15.2 / FR-139 / AD-42).

    Concurrent ``marshal land`` promotions and this script must serialize on
    the SAME lock primitive — never a second lock implementation. When
    marshal is absent (plain ``local-recipes`` env), fall back to a direct
    write: the land path still holds the lock for its own concurrent writers.
    """
    try:
        from pyforge.marshal.adapters.fs_local import FsError, LocalFs
    except ImportError:
        dest.write_text(text, encoding="utf-8")
        return

    fs = LocalFs()
    lock = None
    try:
        lock = fs.acquire_advisory_lock(dest, timeout_s=5.0)
        dest.write_text(text, encoding="utf-8")
    except FsError as exc:
        raise SystemExit(
            f"sprint-ledger-sync: cannot acquire lock on {dest}: {exc}"
        ) from exc
    finally:
        if lock is not None:
            fs.release_advisory_lock(lock)


if __name__ == "__main__":
    raise SystemExit(main())
