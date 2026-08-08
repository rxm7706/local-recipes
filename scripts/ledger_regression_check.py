#!/usr/bin/env python3
"""Detector: no commit may un-finish a story in a tracked sprint ledger.

**Why this exists, precisely.** On 2026-08-08 a single `sprint-ledger-sync` run —
invoked while working on ONE project, but writing all eight — destroyed **96 `done`
markers across four stations** (herald 55, steward 19, doctor 14, scribe 8) by letting
each station's stale gitignored Tier-3 feed overwrite its good tracked twin. It printed
success. It was found only by hand-tracing one station's ledger through `git log`.

Three guards now exist, and this is the outermost:

1. `promote_sprint_status.py` refuses the write (pre-write, local).
2. `--project` scoping stops a single-project task touching seven other stations.
3. **This detector** compares two TRACKED files across a revision range, so it holds
   even when the local guards are bypassed, skipped, `--allow-regression`-ed, or when
   the ledger is hand-edited. It is the only layer that survives an agent that does not
   run the other two.

**Why it can run in bare CI.** The Tier-3 feeds are gitignored and invisible to CI —
that asymmetry is the whole reason the tracked twin exists. This detector reads only
the twin, at two revisions, via `git show`. No Tier-3, no pixi env, no network.

`done` is the only terminal state guarded. backlog / in-progress / blocked / optional
are legitimate two-way transitions and are deliberately not policed — a story CAN be
reopened, but that is an explicit act, not a side effect of a sync.
"""

from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER_GLOB = "_bmad-output/projects/*/planning-artifacts/sprint-status-ledger.yaml"
TERMINAL = frozenset({"done"})

# A story key is `<id>-<kebab-title>`, where `<id>` is either the canonical
# `<epic>-<num>[suffix]` or a legacy alias (`a1`, `b10`). The TAIL is what
# survives a convention migration, so it is what identifies a story across one.
_ID_PREFIX_RE = re.compile(r"^(?:\d+-\d+[a-z]?|[a-z]+\d+)-")


def _tail(key: str) -> str:
    """`2-1-scaffold-the-kedro` and `a1-scaffold-the-kedro` share a tail."""
    return _ID_PREFIX_RE.sub("", key, count=1)


def _git(*args: str) -> str | None:
    """`git` stdout, or None when the command fails (e.g. path absent at that rev)."""
    try:
        out = subprocess.run(("git", *args), cwd=REPO_ROOT, capture_output=True,
                             text=True, check=False)
    except OSError:
        return None
    return out.stdout if out.returncode == 0 else None


def parse_statuses(text: str) -> dict[str, str]:
    """`key: value` pairs under `development_status:`.

    Deliberately a tiny parser rather than PyYAML: this detector must run in the
    barest possible CI, and the file's shape is fixed by its own generator.
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
            break                      # dedent ends the block
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def ledger_paths(rev: str) -> list[str]:
    """Tracked ledger paths at `rev` — listed from git, not the working tree, so a
    ledger deleted in the working tree is still compared."""
    listing = _git("ls-tree", "-r", "--name-only", rev) or ""
    return sorted(
        p for p in listing.splitlines()
        if p.startswith("_bmad-output/projects/")
        and p.endswith("planning-artifacts/sprint-status-ledger.yaml")
    )


def check(base: str, head: str) -> list[dict]:
    findings: list[dict] = []
    for path in sorted(set(ledger_paths(base)) | set(ledger_paths(head))):
        before_text = _git("show", f"{base}:{path}")
        after_text = _git("show", f"{head}:{path}")
        project = path.split("/")[2]

        if before_text is None:
            continue                                   # new ledger: nothing to regress
        before = parse_statuses(before_text)

        if after_text is None:
            done = sorted(k for k, v in before.items() if v in TERMINAL)
            if done:
                findings.append({
                    "kind": "ledger-deleted", "project": project, "path": path,
                    "count": len(done), "keys": done,
                    "detail": f"ledger deleted while holding {len(done)} `done` key(s)",
                })
            continue

        after = parse_statuses(after_text)
        # A RENAME is not a loss, and the difference is decidable rather than a
        # matter of trust: the completion must still EXIST in this same ledger,
        # terminal, under a key whose descriptive tail is byte-identical. Only
        # the numeric/alias id prefix may differ.
        #
        # This does NOT weaken the guard — it narrows a false positive. A genuine
        # loss still fires, because a deleted key has no surviving twin to match;
        # the 96-marker incident of 2026-08-08 would still be caught in full (its
        # keys vanished outright, with no renamed counterpart). What it stops
        # punishing is a convention migration: normalizing atlas's alias ids to
        # the canonical `<epic>-<num>` form (EXEMPLAR-STANDARD INV-5) moved 32
        # `done` keys with every status preserved, and the old check reported that
        # as 32 lost completions.
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
            findings.append({
                "kind": "done-key-regressed", "project": project, "path": path,
                "count": len(lost),
                "keys": [f"{k} ({o} -> {n})" for k, o, n in lost],
                "detail": f"{len(lost)} story key(s) moved out of `done`",
            })
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="ledger-regression-check",
        description="Fail if any commit un-finishes a story in a tracked sprint ledger.",
    )
    ap.add_argument("--base", default="origin/main",
                    help="revision to compare against (default: origin/main)")
    ap.add_argument("--head", default="HEAD", help="revision to check (default: HEAD)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if _git("rev-parse", "--verify", "--quiet", args.base) is None:
        msg = f"base revision {args.base!r} not resolvable"
        print(json.dumps({"error": msg}) if args.json else f"UNDETERMINED: {msg}")
        return 2                                        # never green on can't-evaluate

    # Comparing a revision to ITSELF proves nothing, and would report clean forever.
    # This is the shape CI takes on a `push: branches: [main]` event, where the default
    # `origin/main` IS the commit just pushed — the detector would have run on every
    # direct-to-main commit and passed unconditionally. Fall back to the head's first
    # parent, which is the honest question for a push: "what did this change?"
    base_sha = (_git("rev-parse", args.base) or "").strip()
    head_sha = (_git("rev-parse", args.head) or "").strip()
    if base_sha and base_sha == head_sha:
        parent = (_git("rev-parse", "--verify", "--quiet", f"{args.head}^") or "").strip()
        if not parent:
            msg = (f"{args.base!r} and {args.head!r} are the same commit and it has no "
                   f"parent — nothing to compare")
            print(json.dumps({"error": msg}) if args.json else f"UNDETERMINED: {msg}")
            return 2
        if not args.json:
            print(f"note: {args.base} == {args.head}; comparing against {args.head}^ "
                  f"instead — a revision compared to itself is always clean")
        args.base = parent

    findings = check(args.base, args.head)

    if args.json:
        print(json.dumps({"base": args.base, "head": args.head,
                          "findings": findings}, indent=2))
        return 1 if findings else 0

    total = sum(f["count"] for f in findings)
    print(f"ledger regression — {args.base}..{args.head}")
    if not findings:
        print("\nOK: no tracked ledger un-finishes a story.")
        return 0

    for f in findings:
        print(f"\n  ✗ [{f['kind']}] {f['project']}: {f['detail']}")
        for k in f["keys"][:12]:
            print(f"      {k}")
        if len(f["keys"]) > 12:
            print(f"      … {len(f['keys']) - 12} more")
        print(f"      → git checkout {args.base} -- {f['path']}")
    print(f"\nREGRESSION: {total} `done` key(s) lost across {len(findings)} ledger(s).")
    print("A story that finished does not un-finish as a side effect. If a reopen is")
    print("genuinely intended, it belongs in its own commit that says so.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
