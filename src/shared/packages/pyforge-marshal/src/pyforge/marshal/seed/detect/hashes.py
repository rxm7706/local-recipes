"""Content hashing for managed files and regions (Story 9.3, architecture
FR-106/FR-86/P-07).

Epic 9's detect stage can already classify an artifact STRUCTURALLY
(S-9.2: present, absent, region-present-by-name) but has no signal for the
one thing FR-86's refusal actually needs: whether a tool-owned file or
region was hand-edited since the model last recorded its content. This
module is that signal -- one normalizing content-hash function shared by
both whole-file and region-body hashing, plus two comparison functions that
turn a mismatch (or an unrecorded-but-present artifact) into a HARD
``Finding``.

**Why this does not call ``regions.markers.region_sha`` directly.**
``region_sha(body)`` hashes its argument raw
(``sha256(body.encode("utf-8")).hexdigest()[:8]``), with no line-ending
normalization -- correct for S-8.1's own scope (a parser reporting a
*declared* sha as-is), but wrong for this story's CRLF requirement
(FR-106): a caller on a CRLF checkout would compute a different hash for
byte-identical logical content, exactly the false positive the epics AC
forbids. ``hash_content`` therefore normalizes line endings first (CRLF and
a lone CR both collapse to LF, matching ``regions.parse``'s own
``str.splitlines()``-based universal-newline handling), then applies the
identical sha256-truncated-to-8-hex shape -- matching ``region_sha``'s
output format (so a state file's ``body_sha`` field, AD-58, is one
convention either way) without depending on a function whose contract
excludes normalization.

**Why ``recorded_sha=None`` is always a mismatch, never a pass-through.**
The naive shape ("no recorded value means nothing to compare, so accept")
is exactly what FR-86's "not silently accepted" line forbids: an artifact
adopted outside Genesis (copied in by hand, or the state entry lost) is
structurally indistinguishable from a legitimately-managed one once it
exists on disk, and treating it as conformant would let hand-authored
content pass permanently under the tool's own attestation.

This module performs NO I/O of any kind: every function takes already-read
text (``str``) and an already-parsed ``RegionSpan``/``recorded_sha`` --
reading the file and resolving the target path stay the caller's job
(mirrors S-9.1/S-9.2's own purity, P-03). It reads no
``.marshal/seed-state.yml`` -- ``state/store.py`` does not exist yet (a
later epic); ``recorded_sha`` is always a caller-supplied parameter. It
constructs no ``ArtifactState``/``Classification`` and does not import
``inventory.py`` -- hashing is orthogonal to S-9.2's structural
classification; this story only adds the hash-comparison primitive a later
story (S-9.6) wires in. It checks no ``generated-derived`` staleness --
that is ``derived-stale``, a different mechanism (recomputation, not a
recorded-hash comparison), out of this story's scope. And per P-07, no
hash comparison belongs in ``seed/apply/`` at all -- apply trusts the plan;
asserted by this package's own
``tests/meta/test_p07_no_hash_comparison_in_apply.py``.
"""

from __future__ import annotations

import hashlib

from ..regions.parse import RegionSpan
from .findings import Finding, FindingType, Severity


def normalize_line_endings(text: str) -> str:
    """Collapse CRLF and a lone CR to LF, so identical logical content
    checked out with different line endings normalizes to the same string
    before hashing. Order matters: CRLF pairs are collapsed FIRST, so the
    lone-CR pass afterward only ever touches a CR that was never part of a
    CRLF pair (never double-collapsing one CRLF terminator into two LFs)."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def hash_content(text: str) -> str:
    """The one hash algorithm both whole-file and region-body hashing
    share: sha256 over line-ending-normalized UTF-8 bytes, truncated to 8
    lowercase hex characters -- matching ``regions.markers.region_sha``'s
    own output shape (see the module docstring for why this is a separate,
    normalizing implementation rather than a delegating call)."""
    normalized = normalize_line_endings(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]


def region_body_text(text: str, span: RegionSpan) -> str:
    """Extract exactly ``span.body_span`` from ``text`` -- the identical
    UTF-8 byte-slice operation S-8.3's substitution performs (and
    ``test_seed_regions_parse.py``'s own ``_slice`` helper proves): never
    the marker lines, never the rest of the file."""
    start, end = span.body_span
    return text.encode("utf-8")[start:end].decode("utf-8")


def _hash_mismatch_detail(current_sha: str, recorded_sha: str | None) -> str:
    """The shared "why this is a mismatch" clause both check functions
    report -- kept in one place so the ``recorded_sha is None`` wording and
    the ordinary-mismatch wording cannot drift apart between the two call
    sites."""
    if recorded_sha is None:
        return f"no recorded hash in state (adopted out-of-band); current hash {current_sha}"
    return f"content hash {current_sha} does not match recorded hash {recorded_sha}"


def check_managed_file(path: str, current_text: str, recorded_sha: str | None) -> Finding | None:
    """Compare a managed file's current content hash against its recorded
    state. Returns ``None`` only when ``recorded_sha`` is not ``None`` and
    equals ``hash_content(current_text)``; otherwise returns a HARD
    ``managed-file-modified`` ``Finding`` naming ``path`` -- including the
    ``recorded_sha is None`` case (present on disk but never recorded in
    state, FR-86's "adopted out-of-band" case -- see the module docstring
    for why this is never a silent pass-through)."""
    current_sha = hash_content(current_text)
    if recorded_sha is not None and current_sha == recorded_sha:
        return None
    return Finding.new(
        Severity.HARD,
        FindingType.MANAGED_FILE_MODIFIED,
        path,
        f"{path}: {_hash_mismatch_detail(current_sha, recorded_sha)}",
    )


def check_managed_region(path: str, text: str, span: RegionSpan, recorded_sha: str | None) -> Finding | None:
    """Compare one managed region's current body-content hash against its
    recorded state -- always ``recorded_sha`` (the out-of-band value from
    state), never ``span.sha`` (the hash the region's OWN begin marker
    declares). ``span.sha`` is attacker/editor-controlled: a hand-edit that
    changes the body can trivially hand-edit the adjacent marker's ``sha=``
    field to match, so comparing against it would defeat the very
    modification check this function exists to perform (S-8.2's own
    ``RegionSpan.sha`` docstring: it is "reported as-is and never recomputed
    against body_span's actual content"; comparing against an independent,
    out-of-band source is what makes this a real guard, not self-referential
    -- P-07). Hashes ``region_body_text(text, span)`` only -- content outside
    the region never affects the result. Returns ``None`` only when
    ``recorded_sha`` is not ``None`` and equals the body's computed hash;
    otherwise returns a HARD ``managed-region-modified`` ``Finding`` naming
    ``path`` and ``span.name`` -- including the ``recorded_sha is None``
    case, for the same reason as ``check_managed_file`` above."""
    current_sha = hash_content(region_body_text(text, span))
    if recorded_sha is not None and current_sha == recorded_sha:
        return None
    return Finding.new(
        Severity.HARD,
        FindingType.MANAGED_REGION_MODIFIED,
        path,
        f"{path}#{span.name}: {_hash_mismatch_detail(current_sha, recorded_sha)}",
    )
