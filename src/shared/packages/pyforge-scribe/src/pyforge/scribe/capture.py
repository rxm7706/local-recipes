"""pyforge.scribe.capture — the direct-capture write path (AD-1 / AD-2 / FR-7).

`capture()` is the ONLY write path this module exposes, and it writes ONLY
under `<memory_root>/<type>/` plus one appended index line in
`<memory_root>/MEMORY.md` — no other path. It is append-only / no-clobber:
a slug collision appends a numeric suffix rather than overwriting an
existing file (AD-1). `memory_root` is always an injected `Path`, never a
hardcoded repo-relative constant, so this module has no notion of "the
repo" at all.

The whole record-file-write + index-update is one locked critical section
(`_locked()`): `MEMORY.md`'s read-modify-write is not otherwise atomic, so
concurrent invocations (a realistic scenario -- multiple agent worktrees
capturing at once) would otherwise race and corrupt or drop entries.
`memory_root` itself must already exist (Story 1.1 scaffolds it as a
checked-in tree) -- `capture()` fails loudly rather than silently
materializing a disconnected `.claude/memory/` tree if invoked from the
wrong working directory.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from pyforge.scribe.models import CAPTURE_TYPES, CaptureRecord, CaptureType

_SECTION_HEADINGS: dict[CaptureType, str] = {
    "feedback": "## Feedback",
    "project": "## Project",
    "reference": "## Reference",
}

_SLUG_MAX_LEN = 60
_DESCRIPTION_MAX_LEN = 120
_LOCK_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class CaptureResult:
    """What `capture()` did, for the CLI layer to report back."""

    record: CaptureRecord
    path: Path
    memory_index_line: str


def capture(
    memory_root: Path,
    capture_type: CaptureType,
    text: str,
    *,
    slug: str | None = None,
    description: str | None = None,
) -> CaptureResult:
    """Append one new record under ``memory_root/<capture_type>/`` (AD-1/AD-2/FR-7).

    By default ``name``/``description`` are derived from ``text`` — passing
    ``slug``/``description`` explicitly (Story 1.3's ``promote.py``) overrides
    that derivation so a promoted entry can keep its own rewritten
    description and a filename-derived slug instead of one re-derived from
    the (already rewritten) body text; leaving both ``None`` preserves the
    original direct-capture behavior byte-for-byte. Either way the slug is
    sanitized and collision-checked exactly the same way, and a collision
    appends a numeric suffix — the original file is never touched. Raises
    ``ValueError`` for an invalid ``capture_type``, blank ``text``, or a
    missing/malformed ``memory_root`` -- always before any filesystem write.
    """
    if capture_type not in CAPTURE_TYPES:
        raise ValueError(f"invalid capture type {capture_type!r}; must be one of {CAPTURE_TYPES}")
    if not text.strip():
        raise ValueError("capture text must not be blank")
    if not memory_root.is_dir():
        raise ValueError(
            f"{memory_root} does not exist -- run `scribe capture` from the repo root "
            "(the checked-in .claude/memory/ tree must already exist)"
        )

    with _locked(memory_root):
        memory_md_path = memory_root / "MEMORY.md"
        heading = _SECTION_HEADINGS[capture_type]
        _require_section(memory_md_path, heading)

        type_dir = memory_root / capture_type
        type_dir.mkdir(parents=True, exist_ok=True)

        base_slug = _slugify(slug) if slug is not None else _slugify(text)
        final_slug = _unique_slug(type_dir, base_slug)
        final_description = _truncate(
            description if description is not None else text, _DESCRIPTION_MAX_LEN
        )
        record = CaptureRecord(
            type=capture_type, name=final_slug, description=final_description, text=text
        )

        path = type_dir / f"{final_slug}.md"
        path.write_text(record.to_frontmatter() + "\n" + text.strip() + "\n", encoding="utf-8")

        index_line = f"- [{final_slug}]({capture_type}/{final_slug}.md) — {final_description}"
        _append_index_line(memory_md_path, capture_type, index_line)

    return CaptureResult(record=record, path=path, memory_index_line=index_line)


@contextlib.contextmanager
def _locked(memory_root: Path):
    """Serialize concurrent `capture()` calls against the same `memory_root`.

    A cross-platform advisory lock on a fixed lock file -- stdlib only
    (``fcntl`` on POSIX, ``msvcrt`` on Windows), no new dependency. This is
    the fix for the reproduced concurrent-capture data loss: without it,
    two processes race `MEMORY.md`'s read-modify-write and silently drop
    each other's index lines (or corrupt a section heading entirely).

    The lock file itself lives in the OS temp dir, keyed by `memory_root`'s
    resolved path, never inside `memory_root` -- `capture()` writes ONLY
    under `<memory_root>/<type>/` plus `MEMORY.md` (AD-2/FR-7), and the
    legacy spec's Story 1 AC is explicit that `.claude/memory/`'s
    `.gitignore` stays untouched (everything there is intentionally
    tracked), so a stray runtime artifact must not land in that tree.
    """
    root_key = hashlib.sha256(str(memory_root.resolve()).encode("utf-8")).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"pyforge-scribe-{root_key}.lock"
    lock_file = open(lock_path, "a+")
    deadline = time.monotonic() + _LOCK_TIMEOUT_S
    try:
        if sys.platform == "win32":
            import msvcrt

            while True:
                try:
                    lock_file.seek(0)  # lock a consistent byte-0 region across processes
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"timed out waiting for capture lock: {lock_path}") from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"timed out waiting for capture lock: {lock_path}") from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


def _require_section(memory_md_path: Path, heading: str) -> None:
    """Fail before writing anything if `MEMORY.md` or its section is missing."""
    if not memory_md_path.is_file():
        raise ValueError(f"{memory_md_path} does not exist -- was .claude/memory/ scaffolded?")
    if heading not in memory_md_path.read_text(encoding="utf-8").splitlines():
        raise ValueError(f"{memory_md_path} is missing the {heading!r} section")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:_SLUG_MAX_LEN].strip("-")
    return slug or "capture"


def _unique_slug(type_dir: Path, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while (type_dir / f"{slug}.md").exists():
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


def _truncate(text: str, limit: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _append_index_line(memory_md_path: Path, capture_type: CaptureType, index_line: str) -> None:
    """Add exactly one new line under the matching H2 section of MEMORY.md."""
    heading = _SECTION_HEADINGS[capture_type]
    lines = memory_md_path.read_text(encoding="utf-8").splitlines()

    try:
        heading_idx = lines.index(heading)
    except ValueError as exc:
        raise ValueError(f"{memory_md_path} is missing the {heading!r} section") from exc

    body_end = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            body_end = i
            break

    body = [line for line in lines[heading_idx + 1 : body_end] if line.strip()]
    body.append(index_line)

    new_lines = lines[: heading_idx + 1] + [""] + body + [""] + lines[body_end:]
    memory_md_path.write_text("\n".join(new_lines).rstrip("\n") + "\n", encoding="utf-8")
