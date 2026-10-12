"""Story 96.1: collapse repeated top-level story-spec frontmatter keys before verify."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from pyforge.marshal.ports.vcs import VcsPort

from . import dispatch as dispatch_core
from .commit_vcs import CommittingVcs
from .egress import to_redacted_text
from .model import Finding, Severity
from .refs import ORIGIN_MAIN

_STORY_SPEC_PREFIX = "_bmad-output/projects/"
_STORY_SPEC_SUFFIX = "/planning-artifacts/specs/spec-"
_FRONTMATTER_FENCE = "---"
_TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
SPEC_FRONTMATTER_GATE_CODE = "MRS-GATE-022"
_COLLAPSE_COMMIT_SUBJECT_TEXT = "marshal: collapse repeated story-spec frontmatter keys (Story 96.1)"
_UNCOMMITTED_SHA = "0" * 40

SameCommitTiebreak = Literal["refuse", "last_line"]


@dataclass(frozen=True)
class FrontmatterCollapseRefusal:
    spec_path: str
    key: str
    reason: str


@dataclass(frozen=True)
class DispatchSpecFrontmatterResult:
    """Outcome of the pre-verify story-spec frontmatter collapse pass."""

    collapsed: tuple[tuple[str, str], ...]
    committed_paths: tuple[str, ...]
    refusals: tuple[FrontmatterCollapseRefusal, ...]
    committed: bool


def is_tracked_story_spec_path(path: str) -> bool:
    if not path.endswith(".md"):
        return False
    if not path.startswith(_STORY_SPEC_PREFIX):
        return False
    return _STORY_SPEC_SUFFIX in path


def story_spec_paths_in_changed(changed_files: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(p for p in changed_files if is_tracked_story_spec_path(p)))


class _RepeatRecordingLoader(yaml.SafeLoader):
    """Records top-level repeated keys when loading a frontmatter block."""


def _mapping_constructor(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in mapping:
            repeats = getattr(loader, "repeated_keys", None)
            if repeats is None:
                repeats = set()
                loader.repeated_keys = repeats
            repeats.add(str(key))
        mapping[key] = loader.construct_object(value_node)
    return mapping


_RepeatRecordingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _mapping_constructor,
)


def _split_story_spec(text: str) -> tuple[int, int, str] | None:
    """Return (open_fence_line_index, close_fence_line_index, body_bytes) or None."""
    if not text.startswith(_FRONTMATTER_FENCE):
        return None
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return None
    close_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            close_idx = idx
            break
    if close_idx is None:
        return None
    body = "".join(lines[close_idx + 1 :])
    return 0, close_idx, body


def _frontmatter_line_range(close_idx: int) -> range:
    return range(1, close_idx)


def _top_level_key_line_map(fm_lines: list[str]) -> dict[str, list[int]]:
    """Map top-level frontmatter keys to 0-based indices within ``fm_lines``."""
    out: dict[str, list[int]] = {}
    for idx, line in enumerate(fm_lines):
        if line.startswith((" ", "\t")):
            continue
        match = _TOP_LEVEL_KEY_RE.match(line.rstrip("\n\r"))
        if not match:
            continue
        key = match.group(1)
        out.setdefault(key, []).append(idx)
    return out


def _scalar_value_from_line(line: str) -> object:
    match = _TOP_LEVEL_KEY_RE.match(line.rstrip("\n\r"))
    if not match:
        return None
    raw = match.group(2).strip()
    if raw == "":
        return None
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError:
        return raw


def _file_line_no(fm_line_index: int) -> int:
    """Frontmatter line index to 1-based file line (opening ``---`` is line 1)."""
    return fm_line_index + 2


def _line_sort_key(
    file_line: int,
    blame: dict[int, tuple[str, int]],
) -> tuple[int, int, int] | None:
    fact = blame.get(file_line)
    if fact is None:
        return None
    sha, committer_time = fact
    if sha == _UNCOMMITTED_SHA:
        return (2, committer_time, file_line)
    if committer_time <= 0 and sha != _UNCOMMITTED_SHA:
        return None
    return (1, committer_time, file_line)


def _pick_line_to_keep(
    *,
    key: str,
    fm_indices: list[int],
    fm_lines: list[str],
    blame: dict[int, tuple[str, int]],
    tiebreak_same_commit: SameCommitTiebreak,
) -> tuple[int | None, FrontmatterCollapseRefusal | None]:
    if len(fm_indices) < 2:
        return (fm_indices[0], None)
    file_lines = [_file_line_no(i) for i in fm_indices]
    values = [_scalar_value_from_line(fm_lines[i]) for i in fm_indices]
    sort_keys: list[tuple[int, int, int] | None] = []
    shas: list[str] = []
    for file_line in file_lines:
        fact = blame.get(file_line)
        if fact is None:
            return (
                None,
                FrontmatterCollapseRefusal(
                    spec_path="",
                    key=key,
                    reason="blame missing for a repeated line",
                ),
            )
        shas.append(fact[0])
        sort_keys.append(_line_sort_key(file_line, blame))
    if any(sk is None for sk in sort_keys):
        return (
            None,
            FrontmatterCollapseRefusal(
                spec_path="",
                key=key,
                reason="committer time could not be read for a repeated line",
            ),
        )
    assert sort_keys is not None
    distinct_values = {v for v in values}
    unique_shas = set(shas)
    if len(distinct_values) > 1 and len(unique_shas) == 1:
        if tiebreak_same_commit == "refuse":
            return (
                None,
                FrontmatterCollapseRefusal(
                    spec_path="",
                    key=key,
                    reason="different values with the same newest commit time",
                ),
            )
        return (fm_indices[-1], None)
    best_idx = max(range(len(fm_indices)), key=lambda i: sort_keys[i] or (0, 0, 0))
    return (fm_indices[best_idx], None)


def _validate_collapsed_block(
    *,
    original_fm: list[str],
    new_fm: list[str],
    kept_by_key: dict[str, int],
    repeated_keys: set[str],
) -> bool:
    try:
        loader = _RepeatRecordingLoader("\n".join(new_fm))
        new_data = loader.get_single_data()
    except yaml.YAMLError:
        return False
    repeats = getattr(loader, "repeated_keys", set())
    if repeats:
        return False
    if not isinstance(new_data, dict):
        return False
    try:
        orig_data = yaml.safe_load("\n".join(original_fm))
    except yaml.YAMLError:
        return False
    if not isinstance(orig_data, dict):
        return False
    for key, value in new_data.items():
        if key in repeated_keys:
            kept = kept_by_key.get(key)
            if kept is None:
                return False
            expected = _scalar_value_from_line(original_fm[kept])
            if value != expected:
                return False
        elif orig_data.get(key) != value:
            return False
    return True


def collapse_story_spec_frontmatter_text(
    text: str,
    *,
    blame: dict[int, tuple[str, int]],
    tiebreak_same_commit: SameCommitTiebreak = "refuse",
) -> tuple[str | None, tuple[FrontmatterCollapseRefusal, ...], tuple[str, ...]]:
    """Return collapsed text, refusals, and collapsed key names."""
    split = _split_story_spec(text)
    if split is None:
        return (None, (), ())
    _open_idx, close_idx, body = split
    lines = text.splitlines(keepends=True)
    fm_lines = lines[1:close_idx]
    key_map = _top_level_key_line_map(fm_lines)
    repeated = {k: v for k, v in key_map.items() if len(v) > 1}
    if not repeated:
        return (None, (), ())

    kept_by_key: dict[str, int] = {}
    refusals: list[FrontmatterCollapseRefusal] = []
    remove_indices: set[int] = set()

    for key, indices in sorted(repeated.items()):
        kept, refusal = _pick_line_to_keep(
            key=key,
            fm_indices=indices,
            fm_lines=fm_lines,
            blame=blame,
            tiebreak_same_commit=tiebreak_same_commit,
        )
        if refusal is not None or kept is None:
            refusals.append(
                FrontmatterCollapseRefusal(
                    spec_path="",
                    key=key,
                    reason=refusal.reason if refusal else "ambiguous repeat",
                )
            )
            continue
        kept_by_key[key] = kept
        for idx in indices:
            if idx != kept:
                remove_indices.add(idx)

    if refusals:
        return (None, tuple(refusals), tuple(repeated.keys()))

    new_fm = [line for idx, line in enumerate(fm_lines) if idx not in remove_indices]
    if not _validate_collapsed_block(
        original_fm=fm_lines,
        new_fm=new_fm,
        kept_by_key=kept_by_key,
        repeated_keys=set(repeated.keys()),
    ):
        return (
            None,
            (
                FrontmatterCollapseRefusal(
                    spec_path="",
                    key="*",
                    reason="trial edit failed YAML validation",
                ),
            ),
            tuple(repeated.keys()),
        )

    new_text = lines[0] + "".join(new_fm) + lines[close_idx] + body
    if new_text == text:
        return (None, (), ())
    return (new_text, (), tuple(repeated.keys()))


def findings_for_spec_frontmatter_refusals(
    refusals: tuple[FrontmatterCollapseRefusal, ...],
) -> tuple[Finding, ...]:
    out: list[Finding] = []
    for refusal in refusals:
        out.append(
            Finding(
                code=SPEC_FRONTMATTER_GATE_CODE,
                severity=Severity.ERROR,
                message=(
                    f"story spec {refusal.spec_path!r} repeats frontmatter key {refusal.key!r}: "
                    f"{refusal.reason}"
                ),
            )
        )
    return tuple(out)


def dispatch_spec_frontmatter_should_journal(result: DispatchSpecFrontmatterResult) -> bool:
    return bool(result.collapsed or result.refusals)


def dispatch_spec_frontmatter_journal_payload(
    result: DispatchSpecFrontmatterResult,
) -> dict[str, object]:
    return {
        "collapsed": [{"spec": spec, "key": key} for spec, key in result.collapsed],
        "committed_paths": list(result.committed_paths),
        "refusals": [
            {"spec": r.spec_path, "key": r.key, "reason": r.reason} for r in result.refusals
        ],
        "ok": not result.refusals,
    }


def apply_dispatch_spec_frontmatter_before_verify(
    *,
    worktree: Path,
    repo_root: Path,
    vcs: CommittingVcs,
    blame_vcs: VcsPort,
    tiebreak_same_commit: SameCommitTiebreak = "refuse",
) -> DispatchSpecFrontmatterResult:
    git_repo = dispatch_core.canonical_repo_root(repo_root)
    try:
        scope_changed = vcs.changed_files(git_repo, worktree, base=ORIGIN_MAIN)
    except Exception:
        return DispatchSpecFrontmatterResult((), (), (), False)

    spec_paths = story_spec_paths_in_changed(scope_changed)
    if not spec_paths:
        return DispatchSpecFrontmatterResult((), (), (), False)

    collapsed: list[tuple[str, str]] = []
    refusals: list[FrontmatterCollapseRefusal] = []
    pending_writes: list[tuple[Path, str, tuple[str, ...]]] = []

    for rel in spec_paths:
        abs_path = worktree / rel
        if not abs_path.is_file():
            continue
        text = abs_path.read_text(encoding="utf-8")
        try:
            blame = blame_vcs.line_blame_facts(repo_root=git_repo, path=rel, worktree=worktree)
        except Exception:
            refusals.append(
                FrontmatterCollapseRefusal(
                    spec_path=rel,
                    key="*",
                    reason="git blame failed",
                )
            )
            continue
        new_text, spec_refusals, keys = collapse_story_spec_frontmatter_text(
            text,
            blame=blame,
            tiebreak_same_commit=tiebreak_same_commit,
        )
        for refusal in spec_refusals:
            refusals.append(
                FrontmatterCollapseRefusal(
                    spec_path=rel,
                    key=refusal.key,
                    reason=refusal.reason,
                )
            )
        if spec_refusals:
            continue
        if new_text is None:
            continue
        pending_writes.append((abs_path, new_text, keys))

    committed = False
    paths_to_commit: list[Path] = []
    if pending_writes and not refusals:
        for abs_path, new_text, keys in pending_writes:
            abs_path.write_text(new_text, encoding="utf-8")
            paths_to_commit.append(Path(abs_path.relative_to(worktree)))
            for key in keys:
                collapsed.append((abs_path.relative_to(worktree).as_posix(), key))
        try:
            vcs.commit_paths(
                worktree,
                tuple(paths_to_commit),
                to_redacted_text(_COLLAPSE_COMMIT_SUBJECT_TEXT),
            )
            committed = True
        except Exception:
            committed = False

    return DispatchSpecFrontmatterResult(
        collapsed=tuple(collapsed),
        committed_paths=tuple(p.as_posix() for p in paths_to_commit) if committed else (),
        refusals=tuple(refusals),
        committed=committed,
    )
