#!/usr/bin/env python3
"""One-off legacy ref promotion (Story 87.12 / CAP-287 FR-234).

Dry-run by default. Inventories legacy preserved-work refs, writes a tracked manifest under
``preserve-manifests/``, and with ``--execute`` creates local annotated ``preserve/`` or
``archive/`` twins via ``pyforge.core.preserve_refs``. With ``--push-reviewed`` each reviewed
row is pushed through the content gate (Story 87.15); unreviewed rows are refused.

Never deletes refs. Operator-gated protection removals are manifest rows only — this script
never changes GitHub settings or ``guild-roster.json``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from pyforge.core.preserve_refs import (
    ARCHIVE_REF_PREFIX,
    ATTEMPT_PRESERVE_BRANCH_PREFIX,
    ATTEMPT_PRESERVE_DIRTY_PREFIX,
    PRESERVE_REF_PREFIX,
    PreserveTrailers,
    parse_preserve_ref,
    push_preserve_ref,
    render_archive_heads_ref,
    render_archive_tags_ref,
    render_preserve_ref,
    tag_preserve,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_REL = (
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests"
)
DEFAULT_MANIFEST_DATE = "2026-10-04"
RESCUE_DANGLING_PREFIX = "refs/tags/rescue/dangling-"

SYNTHETIC_SUBJECT_SUFFIX = "(not a real commit)"
_STASH_SUBJECT_RE = re.compile(r"^(?:WIP on |On .+: |index on )")
_PATCH_EQUIV_SINCE = "2026-06-01"

PROMOTE_REASON = "legacy ref promotion (Story 87.12, operator review B1)"
PROMOTE_EVIDENCE = (
    "research preserved-work-refs-2026-10-04 §7.5; twins written locally; "
    "push only after manifest review and Story 87.15 content gate"
)

# Story 87.1 operator ruling: the three kept attempt-preserve branches on origin.
KEPT_ATTEMPT_PRESERVE: dict[str, tuple[str | None, str | None]] = {
    "attempt-preserve/47.1-dispatch-20260920-80e85c57": ("pyforge-marshal", "47.1"),
    "attempt-preserve/20260821-082415-mason-6-3-github-version-checker-gap": (
        "pyforge-mason",
        "6.3",
    ),
    "attempt-preserve/20260712-125315-0aaa-c2605ff1": (None, None),
}

# Local-only legacy tags with fixed twin naming (research §7.5).
LEGACY_TAG_TWINS: dict[str, tuple[str, str | tuple[str | None, str | None]]] = {
    "bmad-loop-preserve/5-9-intent-gap-2026-08-12": (
        "preserve",
        ("pyforge-marshal", "5.9"),
    ),
    "archive/recover-scribe-1-3": ("archive_tags", "recover-scribe-1-3"),
    "archive/scribe-1-3-dangling-91d3571f": ("archive_tags", "scribe-1-3-dangling-91d3571f"),
}

BACKUP_BRANCH_PREFIXES = ("backup/",)
ARCHIVE_BRANCH_NAMES = frozenset({"archive/crewai-toolkit-wip-2026"})
CUSTOM_REF_PREFIXES = ("refs/backup/", "refs/bundle/")


@dataclass(frozen=True, slots=True)
class ManifestRow:
    kind: str
    source_ref: str
    commit_sha: str
    twin_ref: str | None
    twin_evidence: str
    reviewed: bool = False
    classification: str | None = None
    action: str = "none"
    push_findings: tuple[str, ...] = ()


def _git(repo: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _git_out(repo: Path, *args: str) -> str:
    rc, out, err = _git(repo, *args)
    if rc != 0:
        raise RuntimeError(err.strip() or out.strip() or f"git failed: {args}")
    return out.strip()


def _peeled_commit(repo: Path, ref: str) -> str:
    rc, out, _ = _git(repo, "rev-parse", "-q", f"{ref}^{{commit}}")
    if rc == 0 and out.strip():
        return out.strip()
    return _git_out(repo, "rev-parse", ref)


def _for_each_ref(repo: Path, pattern: str) -> list[str]:
    rc, out, err = _git(repo, "for-each-ref", "--format=%(refname)", pattern)
    if rc != 0:
        raise RuntimeError(err.strip() or "git for-each-ref failed")
    return [line.strip() for line in out.splitlines() if line.strip()]


def _short_ref(ref: str) -> str:
    for prefix in ("refs/heads/", "refs/tags/"):
        if ref.startswith(prefix):
            return ref[len(prefix) :]
    return ref


def _infer_story_from_dirty_name(short: str) -> tuple[str | None, str | None]:
    if "47.1" in short or "47-1" in short:
        return "pyforge-marshal", "47.1"
    if "mason-6-3" in short or "mason-6" in short:
        return "pyforge-mason", "6.3"
    if re.search(r"\b5-9\b|5\.9", short):
        return "pyforge-marshal", "5.9"
    return None, None


def _render_preserve_twin(
    repo: Path, *, commit: str, slug: str | None, story: str | None, producer: str
) -> str:
    return render_preserve_ref(
        commit_sha=commit,
        producer=producer,
        project_slug=slug,
        story_key=story,
    )


def _trailers_for_legacy(*, commit: str, source: str, producer: str, run: str = "") -> PreserveTrailers:
    return PreserveTrailers(
        producer=producer,
        provenance="human",
        reason=PROMOTE_REASON,
        source=source,
        run=run or "legacy-preserve-promote",
        journal="",
        commit=commit,
    )


def _format_archive_message(*, archive_from: str) -> str:
    lines = [
        f"Archive-From: {archive_from}",
        f"Archive-Reason: {PROMOTE_REASON}",
        f"Archive-Evidence: {PROMOTE_EVIDENCE}",
    ]
    return "\n".join(lines) + "\n"


def _tag_exists(repo: Path, refname: str) -> bool:
    rc, _, _ = _git(repo, "rev-parse", "--verify", f"{refname}^{{commit}}")
    return rc == 0


def _create_archive_tag(repo: Path, *, refname: str, commit: str, archive_from: str) -> bool:
    if _tag_exists(repo, refname):
        return False
    short = refname.removeprefix("refs/tags/")
    msg = _format_archive_message(archive_from=archive_from)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tf:
        tf.write(msg)
        msg_path = tf.name
    try:
        rc, _, err = _git(repo, "tag", "-a", "-F", msg_path, short, commit)
    finally:
        Path(msg_path).unlink(missing_ok=True)
    if rc != 0:
        raise RuntimeError(err.strip() or "git tag failed")
    return True


def _patch_id(repo: Path, commit: str) -> str | None:
    rc, out, _ = _git(repo, "show", "--format=email", "--no-prefix", "--binary", commit)
    if rc != 0 or not out:
        return None
    proc = subprocess.run(
        ["git", "patch-id"],
        input=out,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return proc.stdout.split()[0].strip()


def _origin_main_patch_ids_since(repo: Path, since: str) -> set[str]:
    ids: set[str] = set()
    try:
        log = _git_out(repo, "log", f"--since={since}", "--format=%H", "refs/remotes/origin/main")
    except RuntimeError:
        return ids
    for commit in log.splitlines():
        commit = commit.strip()
        if not commit:
            continue
        pid = _patch_id(repo, commit)
        if pid:
            ids.add(pid)
    return ids


def classify_rescue_dangling(repo: Path, commit: str, *, origin_patch_ids: set[str]) -> tuple[str, str]:
    subject = ""
    rc, out, _ = _git(repo, "log", "-1", "--format=%s", commit)
    if rc == 0:
        subject = out.strip()
    if subject.endswith(SYNTHETIC_SUBJECT_SUFFIX):
        return "synthetic", f"subject ends with {SYNTHETIC_SUBJECT_SUFFIX!r}"
    if _STASH_SUBJECT_RE.match(subject):
        return "stash", f"subject matches stash heuristic: {subject[:60]!r}"
    rc, out, _ = _git(repo, "rev-list", "--parents", "-1", commit)
    if rc == 0:
        parts = out.strip().split()
        if len(parts) >= 3:
            return "merge", "commit has two or more parents"
    pid = _patch_id(repo, commit)
    if pid is None:
        return "unresolved", "no patch-id (empty or unreadable diff)"
    if pid in origin_patch_ids:
        return "patch-equivalent", f"patch-id {pid} matches origin/main since {_PATCH_EQUIV_SINCE}"
    return "unresolved", f"patch-id {pid} matches no origin/main commit since {_PATCH_EQUIV_SINCE}"


def _promotion_row(
    *,
    source_ref: str,
    commit: str,
    twin_ref: str,
    evidence: str,
    action: str = "write_twin",
) -> ManifestRow:
    return ManifestRow(
        kind="promote",
        source_ref=source_ref,
        commit_sha=commit,
        twin_ref=twin_ref,
        twin_evidence=evidence,
        action=action,
    )


def collect_promotion_rows(repo: Path) -> list[ManifestRow]:
    rows: list[ManifestRow] = []

    for ref in _for_each_ref(repo, ATTEMPT_PRESERVE_DIRTY_PREFIX):
        commit = _peeled_commit(repo, ref)
        short = ref[len(ATTEMPT_PRESERVE_DIRTY_PREFIX) :]
        slug, story = _infer_story_from_dirty_name(short)
        twin = _render_preserve_twin(
            repo, commit=commit, slug=slug, story=story, producer="bmad-loop"
        )
        rows.append(
            _promotion_row(
                source_ref=ref,
                commit=commit,
                twin_ref=twin,
                evidence=f"dirty ref {short!r}; story inferred {slug}/{story}",
            )
        )

    for ref in _for_each_ref(repo, f"refs/heads/{ATTEMPT_PRESERVE_BRANCH_PREFIX}*"):
        short = _short_ref(ref)
        if short not in KEPT_ATTEMPT_PRESERVE:
            continue
        commit = _peeled_commit(repo, ref)
        slug, story = KEPT_ATTEMPT_PRESERVE[short]
        twin = _render_preserve_twin(repo, commit=commit, slug=slug, story=story, producer="hand")
        rows.append(
            _promotion_row(
                source_ref=ref,
                commit=commit,
                twin_ref=twin,
                evidence=f"kept origin branch per Story 87.1 ruling: {short!r}",
            )
        )

    for ref in _for_each_ref(repo, "refs/tags/*"):
        short = _short_ref(ref)
        if ref.startswith(PRESERVE_REF_PREFIX) or ref.startswith(ARCHIVE_REF_PREFIX):
            continue
        if short.startswith("rescue/dangling-"):
            continue
        if short not in LEGACY_TAG_TWINS:
            continue
        commit = _peeled_commit(repo, ref)
        kind, tail = LEGACY_TAG_TWINS[short]
        if kind == "preserve":
            slug, story = tail  # type: ignore[misc]
            twin = _render_preserve_twin(
                repo, commit=commit, slug=slug, story=story, producer="hand"
            )
        else:
            twin = render_archive_tags_ref(str(tail))
        rows.append(
            _promotion_row(
                source_ref=ref,
                commit=commit,
                twin_ref=twin,
                evidence=f"legacy local tag {short!r} → grammar twin",
            )
        )

    for ref in _for_each_ref(repo, "refs/heads/*"):
        short = _short_ref(ref)
        if short.startswith(ATTEMPT_PRESERVE_BRANCH_PREFIX):
            continue
        if any(short.startswith(p) for p in BACKUP_BRANCH_PREFIXES) or short in ARCHIVE_BRANCH_NAMES:
            commit = _peeled_commit(repo, ref)
            twin = render_archive_heads_ref(short)
            rows.append(
                _promotion_row(
                    source_ref=ref,
                    commit=commit,
                    twin_ref=twin,
                    evidence=f"legacy branch → archive/heads twin",
                )
            )

    for prefix in CUSTOM_REF_PREFIXES:
        for ref in _for_each_ref(repo, f"{prefix}*"):
            commit = _peeled_commit(repo, ref)
            twin = _render_preserve_twin(
                repo, commit=commit, slug=None, story=None, producer="hand"
            )
            rows.append(
                _promotion_row(
                    source_ref=ref,
                    commit=commit,
                    twin_ref=twin,
                    evidence=f"custom ref {ref!r} → preserve/unbound/hand-*",
                )
            )

    rows.append(
        ManifestRow(
            kind="operator_gate",
            source_ref="refs/heads/attempt-preserve/**",
            commit_sha="",
            twin_ref=None,
            twin_evidence=(
                "After all three kept branches have preserve/ twins on origin, operator confirms "
                "removing refs/heads/attempt-preserve/** from GitHub ruleset 24451573"
            ),
            action="operator_confirmation",
        )
    )
    rows.append(
        ManifestRow(
            kind="operator_gate",
            source_ref="docs/governance/guild-roster.json protected_refs",
            commit_sha="",
            twin_ref=None,
            twin_evidence=(
                "After twins on origin, operator confirms removing refs/heads/attempt-preserve/ "
                "from roster protected_refs (Story 85.1)"
            ),
            action="operator_confirmation",
        )
    )

    rows.sort(key=lambda r: (r.kind, r.source_ref, r.commit_sha))
    return rows


def collect_rescue_classifications(repo: Path) -> list[ManifestRow]:
    origin_ids = _origin_main_patch_ids_since(repo, _PATCH_EQUIV_SINCE)
    rows: list[ManifestRow] = []
    for ref in _for_each_ref(repo, f"{RESCUE_DANGLING_PREFIX}*"):
        commit = _peeled_commit(repo, ref)
        classification, evidence = classify_rescue_dangling(repo, commit, origin_patch_ids=origin_ids)
        rows.append(
            ManifestRow(
                kind="classify",
                source_ref=ref,
                commit_sha=commit,
                twin_ref=None,
                twin_evidence=evidence,
                classification=classification,
                action="none",
            )
        )
    rows.sort(key=lambda r: r.source_ref)
    return rows


def merge_reviewed_flags(new_rows: list[ManifestRow], prior: dict[tuple[str, str], bool]) -> None:
    for i, row in enumerate(new_rows):
        key = (row.source_ref, row.commit_sha)
        if prior.get(key):
            new_rows[i] = replace(row, reviewed=True)


def load_prior_reviewed(manifest_path: Path) -> dict[tuple[str, str], bool]:
    if not manifest_path.is_file():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], bool] = {}
    for raw in data.get("rows", []):
        if raw.get("reviewed"):
            out[(raw["source_ref"], raw.get("commit_sha", ""))] = True
    return out


def write_manifest(manifest_path: Path, *, manifest_date: str, rows: list[ManifestRow]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_date": manifest_date,
        "written_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": [asdict(r) for r in rows],
    }
    manifest_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def execute_twins(repo: Path, rows: Iterable[ManifestRow]) -> list[str]:
    notes: list[str] = []
    for row in rows:
        if row.action != "write_twin" or not row.twin_ref:
            continue
        if row.twin_ref.startswith(PRESERVE_REF_PREFIX):
            parsed = parse_preserve_ref(row.twin_ref)
            trailers = _trailers_for_legacy(
                commit=row.commit_sha,
                source=row.source_ref,
                producer=parsed.producer,
            )
            result = tag_preserve(
                repo,
                refname=row.twin_ref,
                commit=row.commit_sha,
                trailers=trailers,
            )
            if result.noop:
                notes.append(f"noop preserve {row.twin_ref}")
            else:
                notes.append(f"tagged preserve {row.twin_ref} -> {row.commit_sha[:8]}")
        elif row.twin_ref.startswith(ARCHIVE_REF_PREFIX):
            created = _create_archive_tag(
                repo,
                refname=row.twin_ref,
                commit=row.commit_sha,
                archive_from=row.source_ref,
            )
            if created:
                notes.append(f"tagged archive {row.twin_ref} -> {row.commit_sha[:8]}")
            else:
                notes.append(f"noop archive {row.twin_ref}")
    return notes


def push_reviewed_rows(repo: Path, rows: list[ManifestRow]) -> list[str]:
    notes: list[str] = []
    run_count = 0
    story_counts: dict[str, int] = {}
    for row in rows:
        if row.action != "write_twin" or not row.twin_ref:
            continue
        if not row.reviewed:
            notes.append(f"refused push {row.twin_ref}: row not reviewed")
            continue
        if not _tag_exists(repo, row.twin_ref):
            notes.append(f"refused push {row.twin_ref}: twin not present locally")
            continue
        result = push_preserve_ref(
            repo,
            row.twin_ref,
            run_push_count=run_count,
            story_push_counts=story_counts,
        )
        if result.pushed:
            run_count += 1
            notes.append(f"pushed {row.twin_ref}")
        else:
            findings = ", ".join(f.message for f in result.findings)
            notes.append(f"refused push {row.twin_ref}: {findings}")
    return notes


def default_manifest_path(manifest_dir: Path, manifest_date: str) -> Path:
    return manifest_dir / f"legacy-preserve-promote-{manifest_date}.json"


def run(
    repo: Path,
    *,
    manifest_dir: Path,
    manifest_date: str,
    execute: bool,
    push_reviewed: bool,
) -> int:
    manifest_path = default_manifest_path(manifest_dir, manifest_date)
    prior = load_prior_reviewed(manifest_path)
    promote = collect_promotion_rows(repo)
    classify = collect_rescue_classifications(repo)
    rows = promote + classify
    merge_reviewed_flags(rows, prior)
    write_manifest(manifest_path, manifest_date=manifest_date, rows=rows)
    try:
        rel = manifest_path.relative_to(repo)
    except ValueError:
        rel = manifest_path
    promote_n = sum(1 for r in rows if r.kind == "promote")
    classify_n = sum(1 for r in rows if r.kind == "classify")
    print(
        f"wrote manifest {rel} ({promote_n} promotion row(s), "
        f"{classify_n} rescue/dangling classification(s))"
    )
    if execute:
        for line in execute_twins(repo, rows):
            print(line)
    if push_reviewed:
        for line in push_reviewed_rows(repo, rows):
            print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=REPO_ROOT, help="git checkout (default: repo root)")
    p.add_argument(
        "--manifest-dir",
        type=Path,
        default=None,
        help=f"manifest directory (default: {MANIFEST_REL})",
    )
    p.add_argument(
        "--manifest-date",
        default=DEFAULT_MANIFEST_DATE,
        help="ISO date (YYYY-MM-DD) embedded in the manifest filename",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="write local preserve/archive twins for promotion rows",
    )
    p.add_argument(
        "--push-reviewed",
        action="store_true",
        help="push reviewed twins through the content gate (refuses unreviewed rows)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.resolve()
    manifest_dir = (args.manifest_dir or (repo / MANIFEST_REL)).resolve()
    return run(
        repo,
        manifest_dir=manifest_dir,
        manifest_date=args.manifest_date,
        execute=args.execute,
        push_reviewed=args.push_reviewed,
    )


if __name__ == "__main__":
    sys.exit(main())
