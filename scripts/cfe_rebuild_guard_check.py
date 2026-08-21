#!/usr/bin/env python3
"""cfe-rebuild-guard-check — guard the CFE-rebuild campaign (Epic 6,
pyforge-mason) against its two known failure modes: silent divergence
between the live skill and a parallel replacement, and an endgame that
never arrives (the fate of the ~29,000-line `pyforge-atlas` rebuild,
stranded behind legacy code for months).

Reads `campaign-state.yaml` (the real, tracked instance at
`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/
spec-conda-forge-expert-rebuild/campaign-state.yaml`) plus bounded git
history and enforces three clauses:

    (a) stale-equivalence          any slice whose `status` is `parallel`,
                                    `audited`, or `cut-over` must have
                                    `equivalence: "green"`. The detector
                                    never computes staleness itself from
                                    timestamps -- it trusts the recorded
                                    enum value (writing/refreshing it is the
                                    equivalence harness's job, out of this
                                    story's scope).

    (b) unmirrored-retro           a "landed CFE Rule-2 retro" = a commit in
                                    `<since>..HEAD` (default: the Story-6.1
                                    landing merge, PR #570; overridable via
                                    `--since` so tests can bound a scratch
                                    repo) whose diff touches the CFE surface
                                    (.claude/skills/conda-forge-expert/**,
                                    .claude/scripts/conda-forge-expert/**,
                                    .claude/tools/conda_forge_server.py)
                                    AND touches
                                    .claude/skills/conda-forge-expert/
                                    CHANGELOG.md (status A or M) in the same
                                    commit. No commit-subject pattern is
                                    ever part of the test -- that was the
                                    defect in a prior, reverted attempt,
                                    which wrongly gated on a literal
                                    `retro:` subject prefix that no real CFE
                                    retro commit in this repo's history
                                    actually uses. For every slice with a
                                    non-null `brief_path`, if the newest
                                    qualifying retro SHA in range differs
                                    from that slice's `brief_mirrored_through`,
                                    that is a finding. Slices with
                                    `brief_path: null` are never checked --
                                    no brief exists yet for anything to go
                                    stale.

    (c) legacy-caller-at-endgame   only evaluated when
                                    `campaign.endgame_declared: true`; any
                                    entry in `campaign.callers` with
                                    `resolves_to: "legacy"` is a finding.
                                    While `endgame_declared` is false (true
                                    throughout Epic 6), this clause is
                                    vacuously clean -- the real
                                    caller-resolution population is future
                                    cutover work, not this story's.

Never gates clause (b) on any commit-subject-line pattern. Never confuses
its own clause-(b) scope with `mason_cfe_surface_check.py`'s narrower,
self-scoped `retro:`-subject sanctioned-exception check (FR-45/Story 5.5) --
that check stays untouched. Never implements real caller-introspection for
clause (c) or a real equivalence-harness runner for clause (a) -- both are
declared-state readers only.

Exit codes: 0 clean, 1 findings, 2 could not run (bad/missing
campaign-state.yaml, or `git log` failed). `--json` machine output
supported.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: every input
# (campaign-state.yaml, git log) is tracked/committed state — nothing
# runtime-only, so this runs identically in CI and locally.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAMPAIGN_STATE_PATH = (
    ROOT
    / "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/"
      "spec-conda-forge-expert-rebuild/campaign-state.yaml"
)

# Story-6.1 landing merge (PR #570) — the default lower bound for clause
# (b)'s retro scan. Overridable via --since so tests can bound a scratch repo.
DEFAULT_SINCE = "806cb630469688d596cac00a53573f01f39386e2"

CFE_CHANGELOG = ".claude/skills/conda-forge-expert/CHANGELOG.md"
CFE_SURFACE_PREFIXES = (
    ".claude/skills/conda-forge-expert/",
    ".claude/scripts/conda-forge-expert/",
)
CFE_SURFACE_FILES = frozenset({".claude/tools/conda_forge_server.py"})

# Clause (a): slice statuses that require equivalence: "green".
EQUIVALENCE_GATED_STATUSES = frozenset({"parallel", "audited", "cut-over"})


def _run(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                               text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None


def git(root: pathlib.Path, *args: str) -> str:
    """git stdout, or "" on any failure — matches every sibling detector's
    `git()` wrapper (e.g. mason_cfe_surface_check.py): a failed per-commit
    lookup and a genuinely empty one are handled identically."""
    proc = _run(root, *args)
    return proc.stdout.strip() if proc and proc.returncode == 0 else ""


def is_cfe_path(path: str) -> bool:
    return path in CFE_SURFACE_FILES or any(path.startswith(p) for p in CFE_SURFACE_PREFIXES)


def campaign_state(path: pathlib.Path) -> dict | None:
    """Parsed campaign-state.yaml, or None if the file is missing, unreadable,
    or not valid YAML mapping at its top level — the exit-2 "could not run"
    case."""
    try:
        import yaml
    except ModuleNotFoundError:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _parse_name_status_lines(lines: list[str]) -> list[tuple[str, str]]:
    """Parse `git diff --name-status`-style lines into (status, path) pairs.
    A rename/copy line has THREE tab-separated fields (status, old path, new
    path) rather than two -- the current path is always the last field,
    whichever shape the line has. Neither call site below passes `-M`/`-C`,
    so a 3-field line cannot occur through this module today; this still
    handles it correctly rather than relying on that staying true."""
    return [(ln.split("\t")[0], ln.split("\t")[-1]) for ln in lines]


def diff_name_status(root: pathlib.Path, sha: str) -> list[tuple[str, str]]:
    """(status, path) pairs for `sha`'s diff. Falls back to the first-parent
    diff when plain `diff-tree` returns empty (a real multi-parent merge, for
    which plain `diff-tree` prints nothing) so a conflict-resolving merge is
    never silently read as "touches nothing" — same pattern as
    mason_cfe_surface_check.py's own helper."""
    for args in (
        ("diff-tree", "--no-commit-id", "--name-status", "-r", "--root", sha),
        ("diff", "--name-status", f"{sha}^1", sha),
    ):
        lines = [ln for ln in git(root, *args).splitlines() if ln.strip()]
        if lines:
            return _parse_name_status_lines(lines)
    return []


def retro_commits_since(root: pathlib.Path, since: str) -> list[str] | None:
    """SHAs (newest first) in `since..HEAD` that qualify as a landed CFE
    Rule-2 retro: diff touches the CFE surface AND touches CFE_CHANGELOG with
    status A or M in the same commit. None if `git log` itself could not run
    (e.g. `since` unknown to this repo, or `root` is not a git repository) —
    the exit-2 case."""
    proc = _run(root, "log", "--format=%H", "--topo-order", f"{since}..HEAD")
    if proc is None or proc.returncode != 0:
        return None
    shas = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    retros: list[str] = []
    for sha in shas:
        status_lines = diff_name_status(root, sha)
        files = [path for _status, path in status_lines]
        if not any(is_cfe_path(f) for f in files):
            continue
        changelog_status = next(
            (status[:1] for status, path in status_lines if path == CFE_CHANGELOG), None)
        if changelog_status in ("A", "M"):
            retros.append(sha)
    return retros


def scan(state: dict, retros: list[str]) -> list[dict]:
    findings: list[dict] = []
    slices = state.get("slices")
    slices = slices if isinstance(slices, list) else []
    newest_retro = retros[0] if retros else None

    # Clause (a): stale-equivalence.
    for sl in slices:
        if not isinstance(sl, dict):
            continue
        slice_id = sl.get("id", "<unknown-slice>")
        status = sl.get("status")
        if status not in EQUIVALENCE_GATED_STATUSES:
            continue
        equivalence = sl.get("equivalence")
        if equivalence == "green":
            continue
        findings.append({
            "kind": "stale-equivalence",
            "ref": slice_id,
            "refs": [slice_id],
            "detail": f"slice '{slice_id}' has status={status!r} but "
                      f"equivalence={equivalence!r} (must be 'green')",
            "remedy": "re-run the equivalence harness for this slice and "
                      "record a fresh 'green' result before it may stay "
                      "parallel/audited/cut-over",
        })

    # Clause (b): unmirrored-retro. Only meaningful when at least one
    # qualifying retro landed in range -- otherwise there is nothing new for
    # any brief to be behind.
    if newest_retro is not None:
        for sl in slices:
            if not isinstance(sl, dict):
                continue
            brief_path = sl.get("brief_path")
            if not brief_path:
                continue
            slice_id = sl.get("id", "<unknown-slice>")
            mirrored_through = sl.get("brief_mirrored_through")
            if mirrored_through == newest_retro:
                continue
            findings.append({
                "kind": "unmirrored-retro",
                "ref": slice_id,
                "refs": [slice_id, newest_retro[:10]],
                "detail": f"slice '{slice_id}': newest qualifying CFE retro "
                          f"{newest_retro[:10]} (CFE surface + CHANGELOG.md "
                          f"touched) differs from brief_mirrored_through="
                          f"{mirrored_through!r} — the slice's brief may be stale",
                "remedy": "mirror the retro's CFE-surface delta into the "
                          "slice's brief, then set brief_mirrored_through to "
                          f"{newest_retro[:10]}",
            })

    # Clause (c): legacy-caller-at-endgame. Only evaluated once the campaign
    # has declared its endgame.
    campaign = state.get("campaign")
    campaign = campaign if isinstance(campaign, dict) else {}
    if campaign.get("endgame_declared") is True:
        for idx, caller in enumerate(campaign.get("callers") or []):
            if not isinstance(caller, dict) or caller.get("resolves_to") != "legacy":
                continue
            ref = caller.get("name") or caller.get("id") or f"caller[{idx}]"
            findings.append({
                "kind": "legacy-caller-at-endgame",
                "ref": ref,
                "refs": [ref],
                "detail": f"caller {ref!r} still resolves_to 'legacy' while "
                          "campaign.endgame_declared is true",
                "remedy": "flip this caller to the replacement before the "
                          "endgame is declared complete",
            })

    return findings


def _unknown(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message, "retros_scanned": None, "findings": []}))
    else:
        print(f"UNKNOWN: {message}", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="cfe-rebuild-guard-check",
        description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--since", default=DEFAULT_SINCE,
                     help="lower bound (exclusive) of the clause-(b) retro scan; "
                          "defaults to the Story-6.1 landing merge (PR #570)")
    args = ap.parse_args()

    state = campaign_state(CAMPAIGN_STATE_PATH)
    if state is None:
        return _unknown(f"could not read/parse {CAMPAIGN_STATE_PATH} as a YAML "
                         "mapping — file missing, unreadable, or malformed.",
                         args.json)

    retros = retro_commits_since(ROOT, args.since)
    if retros is None:
        return _unknown(f"`git log {args.since}..HEAD` could not run — not a "
                         f"git repository, or {args.since} is unreachable from "
                         "HEAD.", args.json)

    findings = scan(state, retros)

    if args.json:
        print(json.dumps({"retros_scanned": len(retros), "findings": findings}, indent=2))
        return 1 if findings else 0

    print(f"cfe-rebuild-guard-check: {len(retros)} qualifying CFE retro commit(s) "
          f"in {args.since[:10]}..HEAD\n")
    if not findings:
        print("  clean — no slice has a stale equivalence result, no briefed "
              "slice is behind a landed retro, and no legacy caller survives "
              "a declared endgame.")
        return 0

    for f in findings:
        print(f"  ✗ [{f['kind']}] {f['ref']}")
        print(f"      {f['detail']}")
        print(f"      → {f['remedy']}")
    print(f"\nFAIL: {len(findings)} finding(s). See docs/dreams/fidelity-enforcement.md "
          "and the Epic 6 campaign-state.yaml for context.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
