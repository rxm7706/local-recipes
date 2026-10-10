#!/usr/bin/env python3
"""One-off recovery: local archive tags for orphaned branch tips (Story 87.16 / CAP-287).

Dry-run by default. Reads branch-deletion events (GitHub activity API plus Story 87.1's
attempt-preserve retirement table), classifies each ``before`` tip for reachability, writes
a tracked manifest under ``preserve-manifests/``, and with ``--execute`` creates local
annotated ``refs/tags/archive/heads/<branch>`` tags only for tips still unreachable.

Never pushes or deletes refs. Stdlib-only — no ``pyforge`` imports (Story 87.3 can pin names later).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GITHUB_REPO = "rxm7706/local-recipes"
DEFAULT_ACTIVITY_DATE = "2026-10-04"
ORIGIN_MAIN = "refs/remotes/origin/main"
ARCHIVE_PREFIX = "refs/tags/archive/"
PRESERVE_PREFIX = "refs/tags/preserve/"
MANIFEST_REL = (
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests"
)

ARCHIVE_REASON = "orphan-tip-archive recovery after 2026-10-04 branch cleanup"
ARCHIVE_EVIDENCE = (
    "operator ruling 2026-10-04 (preserved-work refs review Q4): local annotated archive "
    "tags before gc; push only after content review (Story 87.15)"
)

# Story 87.1 spec — attempt-preserve branches retired 2026-10-04 (tip shas).
ATTEMPT_PRESERVE_RETIREMENTS: tuple[tuple[str, str], ...] = (
    ("attempt-preserve/20260809-114839-7af9-e63ea1e7", "e63ea1e7dcf504d16cf8497929d52d82a20d4726"),
    ("attempt-preserve/20260812-191714-167d-6725b773", "6725b773fd251bc62b6f562e5c61b2f2e6a23aa8"),
    ("attempt-preserve/20260813-094917-9bba-c9e59028", "c9e59028ffad5ed42adf0cf8816add80a4cae0db"),
    ("attempt-preserve/20260813-094919-bfcb-1f6320dc", "1f6320dc4c54329a56e1da6187d55a8a33b167ae"),
    ("attempt-preserve/20260813-094919-bfcb-523e938c", "523e938c79783d06d72030afdb92932d3d02f62f"),
    ("attempt-preserve/20260813-094919-bfcb-95ea70c9", "95ea70c9e374c74b5ed7994b81878e89975141fb"),
    ("attempt-preserve/20260813-094919-bfcb-a71b81c4", "a71b81c4cfeb3ce2d9fcc4e3b8e63527e6c9e661"),
    ("attempt-preserve/20260813-094919-bfcb-accc097e", "accc097e6ab585d0398a4e66bb1c7365ee1ba960"),
    ("attempt-preserve/20260813-094919-bfcb-bf979ece", "bf979ece863e872102b1d332e60b2d68a3139bf6"),
    ("attempt-preserve/20260813-094919-bfcb-e5c52f83", "e5c52f83c072b80e07e17194839f76a0c7792449"),
    ("attempt-preserve/20260813-094919-bfcb-edd3a0ef", "edd3a0ef9890dfedff95ecaa2922e722dc75a997"),
    ("attempt-preserve/20260813-145934-3eb0-4edeb666", "4edeb666fceadd614836a1802085d5ff139cf7a5"),
    ("attempt-preserve/20260813-145934-3eb0-855522fe", "855522fe024b2460b0d19652cf2863a47422e6a5"),
    ("attempt-preserve/20260813-160412-936a-137d3f9c", "137d3f9c5b944fa2a479f169ad50c8cccf7d3294"),
    ("attempt-preserve/20260813-160412-936a-85a60d06", "85a60d06e673b50ee9553fcd9d369fc1f3273f2a"),
    ("attempt-preserve/20260814-202328-e168-01027a26", "01027a26ec95369152f04aa5aab081cc0f79a3ed"),
    ("attempt-preserve/20260814-202328-e168-4bc53701", "4bc5370124f19efa806105a85c160930cef95ed5"),
    ("attempt-preserve/20260814-202329-6e05-3ab65098", "3ab650982398e8944d250b8c234a0cbc9ed42165"),
    ("attempt-preserve/20260814-202329-6e05-9de381a0", "9de381a01e279385e778dedffe7cbf7ec54cc0b8"),
    ("attempt-preserve/20260815-112702-c77e-1f526046", "1f5260468e17565dd5d27940bcf28076e542fa80"),
    ("attempt-preserve/20260815-115702-0501-066d3633", "066d3633d996953e91167daf6ce8ebab9749090b"),
    ("attempt-preserve/20260815-115702-0501-34fcec5c", "34fcec5c6dd6d0099aec548858f397fbb60efdba"),
    ("attempt-preserve/20260815-115702-0501-46cf7ae6", "46cf7ae664f09d9bdcafd859d91c9dffe46c800a"),
    ("attempt-preserve/20260910-100021-1dbc-b9f867c9", "b9f867c912a06dbe6c3990a6fbcda3e83fdf433e"),
    ("attempt-preserve/20260910-100021-1dbc-de30608a", "de30608a1f84a71525f66dd5a1e22f79c3c0879c"),
    ("attempt-preserve/20260910-100021-1dbc-e6827596", "e6827596cd5a42bd36245776aa12130033d6842a"),
    ("attempt-preserve/20260914-201759-bd47-1a029b86", "1a029b86a0ab720b262c7ee031b11e278ff1d522"),
    ("attempt-preserve/20260914-201759-bd47-f909c5d7", "f909c5d726d81419ac753d0f30d5282765a5be86"),
    ("attempt-preserve/20260918-011855-dc48-54b60530", "54b60530294390044bc3c64353d729eaed41aba9"),
    ("attempt-preserve/doctor-11-4-46cf7ae664", "46cf7ae664f09d9bdcafd859d91c9dffe46c800a"),
)

DeletionReader = Callable[[], tuple[list["DeletionEvent"], str]]


@dataclass(frozen=True, slots=True)
class DeletionEvent:
    branch: str
    before_sha: str
    source: str


@dataclass(frozen=True, slots=True)
class ManifestRow:
    branch: str
    before_sha: str
    reachability: str
    reachability_evidence: str
    archive_tag: str
    archive_from: str
    archive_reason: str
    archive_evidence: str
    reviewed: bool = False


def _git(repo: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _gh_json(args: list[str], *, cwd: Path | None = None) -> tuple[object | None, str]:
    try:
        proc = subprocess.run(
            ["gh", "api", *args],
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        return None, err
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from gh api: {exc}"


def gh_has_authenticated_quota() -> tuple[bool, str]:
    data, err = _gh_json(["rate_limit"])
    if data is None:
        return False, err or "gh api rate_limit failed"
    core = (data.get("resources") or {}).get("core") or {}  # type: ignore[union-attr]
    limit = int(core.get("limit") or 0)
    if limit <= 60:
        return False, "gh api rate_limit shows no authenticated quota (core limit 60)"
    return True, ""


def render_archive_heads_ref(branch: str) -> str:
    branch = branch.removeprefix("refs/heads/")
    return f"{ARCHIVE_PREFIX}heads/{branch}"


def format_archive_message(*, archive_from: str, archive_reason: str, archive_evidence: str) -> str:
    lines = [
        f"Archive-From: {archive_from}",
        f"Archive-Reason: {archive_reason}",
        f"Archive-Evidence: {archive_evidence}",
    ]
    return "\n".join(lines) + "\n"


def retirement_table_events() -> list[DeletionEvent]:
    return [
        DeletionEvent(branch=b, before_sha=sha, source="story-87-1-retirement-table")
        for b, sha in ATTEMPT_PRESERVE_RETIREMENTS
    ]


def github_branch_deletion_reader(
    github_repo: str,
    activity_date: str,
) -> DeletionReader:
    def _read() -> tuple[list[DeletionEvent], str]:
        ok, err = gh_has_authenticated_quota()
        if not ok:
            return [], err
        query = (
            f"repos/{github_repo}/activity"
            f"?activity_type=branch_deletion&time_period=week&per_page=100"
        )
        events: list[DeletionEvent] = []
        page = 1
        while True:
            data, err = _gh_json([f"{query}&page={page}"])
            if data is None:
                return [], err
            if not isinstance(data, list):
                return [], "activity response was not an array"
            if not data:
                break
            for row in data:
                if not isinstance(row, dict):
                    continue
                ts = str(row.get("timestamp") or "")
                if not ts.startswith(activity_date):
                    continue
                ref = str(row.get("ref") or "")
                before = str(row.get("before") or "")
                if not ref.startswith("refs/heads/") or len(before) != 40:
                    continue
                branch = ref.removeprefix("refs/heads/")
                events.append(
                    DeletionEvent(branch=branch, before_sha=before, source="github-activity")
                )
            if len(data) < 100:
                break
            page += 1
        return events, ""

    return _read


def merge_deletion_events(*parts: Iterable[DeletionEvent]) -> list[DeletionEvent]:
    seen: set[tuple[str, str]] = set()
    out: list[DeletionEvent] = []
    for part in parts:
        for ev in part:
            key = (ev.branch, ev.before_sha)
            if key in seen:
                continue
            seen.add(key)
            out.append(ev)
    return out


def object_exists(repo: Path, sha: str) -> bool:
    rc, _, _ = _git(repo, "cat-file", "-e", f"{sha}^{{commit}}")
    return rc == 0


def tip_is_ancestor_of_origin_main(repo: Path, tip_sha: str) -> bool:
    rc, _, _ = _git(repo, "merge-base", "--is-ancestor", tip_sha, ORIGIN_MAIN)
    return rc == 0


def refs_containing_tip(repo: Path, tip_sha: str) -> list[str]:
    rc, out, _ = _git(
        repo,
        "for-each-ref",
        "--contains",
        tip_sha,
        "--format=%(refname)",
    )
    if rc != 0 or not out.strip():
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def classify_reachability(repo: Path, tip_sha: str) -> tuple[str, str]:
    if tip_is_ancestor_of_origin_main(repo, tip_sha):
        return "ancestor-of-origin-main", f"tip is ancestor of {ORIGIN_MAIN}"
    refs = refs_containing_tip(repo, tip_sha)
    if refs:
        sample = refs[0]
        if len(refs) > 1:
            return "reachable-from-ref", f"contained in {sample} (+{len(refs) - 1} more)"
        return "reachable-from-ref", f"contained in {sample}"
    return "unreachable", "no ref contains tip"


def build_manifest_rows(repo: Path, events: list[DeletionEvent]) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for ev in events:
        if not object_exists(repo, ev.before_sha):
            continue
        reach, evidence = classify_reachability(repo, ev.before_sha)
        if reach != "unreachable":
            continue
        archive_from = f"refs/heads/{ev.branch}"
        archive_tag = render_archive_heads_ref(ev.branch)
        rows.append(
            ManifestRow(
                branch=ev.branch,
                before_sha=ev.before_sha,
                reachability=reach,
                reachability_evidence=evidence,
                archive_tag=archive_tag,
                archive_from=archive_from,
                archive_reason=ARCHIVE_REASON,
                archive_evidence=ARCHIVE_EVIDENCE,
            )
        )
    rows.sort(key=lambda r: (r.branch, r.before_sha))
    return rows


def write_manifest(manifest_path: Path, *, activity_date: str, rows: list[ManifestRow]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "activity_date": activity_date,
        "written_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": [asdict(r) for r in rows],
    }
    manifest_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def tag_exists(repo: Path, refname: str) -> bool:
    rc, _, _ = _git(repo, "rev-parse", "--verify", f"{refname}^{{commit}}")
    return rc == 0


def create_local_archive_tag(repo: Path, row: ManifestRow) -> tuple[bool, str]:
    """Return (created, skip_reason). created False with empty reason means already existed."""
    reach, _ = classify_reachability(repo, row.before_sha)
    if reach != "unreachable":
        return False, f"tip now {reach}"
    if tag_exists(repo, row.archive_tag):
        return False, ""
    short = row.archive_tag.removeprefix("refs/tags/")
    msg = format_archive_message(
        archive_from=row.archive_from,
        archive_reason=row.archive_reason,
        archive_evidence=row.archive_evidence,
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tf:
        tf.write(msg)
        msg_path = tf.name
    try:
        rc, _, err = _git(repo, "tag", "-a", "-F", msg_path, short, row.before_sha)
    finally:
        Path(msg_path).unlink(missing_ok=True)
    if rc != 0:
        return False, err.strip() or "git tag failed"
    return True, ""


def execute_archive_tags(repo: Path, rows: list[ManifestRow]) -> list[str]:
    notes: list[str] = []
    for row in rows:
        created, reason = create_local_archive_tag(repo, row)
        if created:
            notes.append(f"tagged {row.archive_tag} -> {row.before_sha[:8]}")
        elif reason:
            notes.append(f"skipped {row.branch}: {reason}")
    return notes


def default_manifest_path(manifest_dir: Path, activity_date: str) -> Path:
    return manifest_dir / f"orphan-tip-archive-{activity_date}.json"


def run(
    repo: Path,
    *,
    manifest_dir: Path,
    activity_date: str,
    execute: bool,
    reader: DeletionReader,
) -> int:
    gh_events, err = reader()
    if err:
        print(f"orphan-tip-archive: {err}", file=sys.stderr)
        return 2
    events = merge_deletion_events(gh_events, retirement_table_events())
    rows = build_manifest_rows(repo, events)
    manifest_path = default_manifest_path(manifest_dir, activity_date)
    write_manifest(manifest_path, activity_date=activity_date, rows=rows)
    try:
        rel = manifest_path.relative_to(repo)
    except ValueError:
        rel = manifest_path
    print(f"wrote manifest {rel} ({len(rows)} unreachable tip(s))")
    if execute:
        for line in execute_archive_tags(repo, rows):
            print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--repo",
        type=Path,
        default=REPO_ROOT,
        help="git checkout whose object database holds the tips (default: repo root)",
    )
    p.add_argument(
        "--manifest-dir",
        type=Path,
        default=None,
        help=f"manifest directory (default: {MANIFEST_REL})",
    )
    p.add_argument(
        "--activity-date",
        default=DEFAULT_ACTIVITY_DATE,
        help="ISO date (YYYY-MM-DD) filtering GitHub branch_deletion events",
    )
    p.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help="owner/repo for gh api activity reads",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="write local archive tags for manifest rows still unreachable",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.resolve()
    manifest_dir = (args.manifest_dir or (repo / MANIFEST_REL)).resolve()
    reader = github_branch_deletion_reader(args.github_repo, args.activity_date)
    return run(
        repo,
        manifest_dir=manifest_dir,
        activity_date=args.activity_date,
        execute=args.execute,
        reader=reader,
    )


if __name__ == "__main__":
    sys.exit(main())
