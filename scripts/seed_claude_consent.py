#!/usr/bin/env python3
"""Pre-approve the Claude CLI's per-workspace startup dialogs for loop homes.

OPERATOR DECISION, 2026-07-31 — recorded here because this removes a human
checkpoint, and the next reader deserves the reasoning rather than a silent
config edit.

THE COST OF NOT DOING IT
------------------------
A bmad-loop session that hits an interactive startup dialog sits forever, and
nothing in the orchestrator can see it:

  * `bmad-loop status` reports the last phase it WROTE, so the story reads
    `dev-running` indefinitely;
  * the supervisor's stall ladder (`dev_stall_grace_s`, `dev_stall_nudges`)
    never fires;
  * the dialog is **not written to the session log** — verified: it appears in
    none of scribe's six logs. It renders only in the multiplexer pane, so the
    log simply stops growing.

Live cost 2026-07-31: scribe story 1.3 sat **74 minutes** on

    Allow external CLAUDE.md file imports?
      /home/rxm7706/.bmad-loops/pyforge-scribe/.claude/memory/MEMORY.md

— seven times its 600 s grace — while five sibling stations wrote every second.
Cleared by hand with `tmux send-keys`. The folder-trust dialog cost ~1 h the same
way earlier (warden 6.3). The trigger is self-inflicted and recurring: scribe's
own story 1.2 added `@.claude/memory/MEMORY.md` to CLAUDE.md, so every station
whose CLAUDE.md imports team memory is exposed on every fresh home, forever.

WHAT THIS DOES *NOT* CHANGE
---------------------------
It grants the agent **no** additional in-session capability. Loop sessions
already run `--permission-mode bypassPermissions` (verified in the live
invocation), so tool use is already unconfirmed. These are *workspace startup*
dialogs — a different layer, which is precisely why bypassPermissions did not
suppress them and scribe stalled anyway. The two are orthogonal; neither
substitutes for the other.

WHAT IT DOES CHANGE — stated plainly
------------------------------------
The external-import dialog is the one moment a human sees the literal list of
files being pulled into the model's system context. After seeding, that list is
never shown again for these paths. The imported file, `.claude/memory/MEMORY.md`,
is **agent-written** — that is scribe's entire purpose; its spec surface is
`.claude/memory/**`. So agent-authored content reaches every future session's
context with no startup checkpoint.

The residual control is that `.claude/memory/**` is git-tracked: a change shows
in a diff and in PR review. That — not the dialog — is now where this gets
caught. **Reviewers of scribe's captures should read them as instructions, not
as notes.**

Detection, not prevention, is the compensating control: `loop-stall-check`
(added the same day) catches any FUTURE interactive prompt within 15 minutes by
watching progress rather than any particular dialog.

SCOPE — deliberately narrow
---------------------------
Only exact paths named on the command line, each of which must be an existing
git worktree under the loop root. Never `~`, never the main checkout, never a
prefix covering unrelated projects. Consent in `~/.claude.json` is keyed per
absolute path with no inheritance, so this cannot leak to a sibling project.

USAGE
    seed-claude-consent -- --check             # report gaps, change nothing (exit 1 if any)
    seed-claude-consent -- --all-loop-homes    # seed every git worktree under ~/.bmad-loops
    seed-claude-consent -- <path> [<path>...]  # seed specific homes
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

CONFIG = Path.home() / ".claude.json"
LOOP_ROOT = Path.home() / ".bmad-loops"
KEYS = {
    "hasTrustDialogAccepted": True,
    "hasClaudeMdExternalIncludesApproved": True,
    "hasClaudeMdExternalIncludesWarningShown": True,
}


def loop_homes() -> list[Path]:
    if not LOOP_ROOT.is_dir():
        return []
    return sorted(p for p in LOOP_ROOT.iterdir() if (p / ".git").exists())


def ineligible(p: Path) -> str | None:
    """Reject anything that is not a git worktree under the loop root.

    This guard IS the scope guarantee: a typo, a shell glob or a stale argument
    cannot make this approve `~`, the main checkout, or an unrelated project.
    """
    try:
        p.relative_to(LOOP_ROOT)
    except ValueError:
        return f"outside {LOOP_ROOT}"
    if not p.is_dir():
        return "not a directory"
    if not (p / ".git").exists():
        return "not a git worktree"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all-loop-homes", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="report only; exit 1 if any target would stall on a dialog")
    args = ap.parse_args()

    targets = [Path(p).resolve() for p in args.paths]
    if args.all_loop_homes or (args.check and not targets):
        targets = loop_homes()
    if not targets:
        ap.error("name at least one path, or pass --all-loop-homes")

    try:
        cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    except json.JSONDecodeError as exc:
        sys.exit(f"refusing to touch a malformed {CONFIG}: {exc}")

    projects = cfg.setdefault("projects", {})
    changed: list[Path] = []
    gaps: list[Path] = []

    for t in targets:
        why = ineligible(t)
        if why:
            print(f"  REFUSE  {t}  ({why})")
            continue
        entry = projects.get(str(t), {})
        missing = [k for k, v in KEYS.items() if entry.get(k) is not v]
        if not missing:
            print(f"  ok      {t.name}")
            continue
        if args.check:
            print(f"  GAP     {t.name}  ({len(missing)} dialog(s) would fire)")
            gaps.append(t)
            continue
        entry.update(KEYS)
        projects[str(t)] = entry
        changed.append(t)
        print(f"  seeded  {t.name}")

    if args.check:
        if gaps:
            print(f"\n{len(gaps)} loop home(s) can stall a run on an interactive dialog.")
            print("Fix: pixi run -e local-recipes seed-claude-consent -- --all-loop-homes")
            return 1
        print("\nOK: every loop home is pre-approved; no startup dialog can stall a run.")
        return 0

    if not changed:
        print("\nnothing to do — every target was already approved")
        return 0

    # Atomic write: this file holds every project's state, so an interrupted run
    # must never leave it half-written.
    if CONFIG.exists():
        shutil.copy2(CONFIG, CONFIG.with_name(".claude.json.bak"))
    fd, tmp = tempfile.mkstemp(dir=str(CONFIG.parent), prefix=".claude.json.")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(cfg, fh, indent=2)
        os.replace(tmp, CONFIG)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

    print(f"\nseeded {len(changed)} home(s); previous config kept as ~/.claude.json.bak")
    return 0


if __name__ == "__main__":
    sys.exit(main())