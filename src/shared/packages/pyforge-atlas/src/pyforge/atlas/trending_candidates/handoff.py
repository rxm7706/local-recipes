"""``hand_off_candidate`` — CAP-5's whole downstream-handoff contract (Story 13.5, FR-68).

Looks up ONE repo in the already-classified ``trending_candidates_classified`` dataset
(Story 13.2, CAP-2), requires a caller-supplied PASSING health-screen verdict
(abandonment signal + license clarity), and on a tier-1/2 candidate returns ONE
structured, schema-documented record — never a recipe, never a staged-recipes PR
(SPEC.md's CAP-5 success signal). Any ineligible or under-specified input raises
``ValueError`` naming the specific reason; nothing is ever silently passed
(Boundaries & Constraints).

Mirrors ``trending_candidates/query.py``'s read seam EXACTLY
(``_session.bootstrapped_session`` + ``_provenance.load_with_provenance``) and its
"validate first, raise ``ValueError``" contract — no new fetch, no new catalog entry,
no new Kedro node (this is a plain read + CLI, the identical non-pipeline shape CAP-3
already established). Lives OUTSIDE ``mcp/`` for the same reason ``query.py`` does: no
MCP tool is added here (a one-shot gate action has no query/browse use case an MCP
client needs — Boundaries & Constraints), but the module still sits one seam call away
from the AD-7 AST-gated ``mcp/tools.py`` files, free to use pandas.

Why the health-screen verdict is a caller-supplied INPUT, not computed here: this
story builds the structural gate ("the gate exists"), not pyforge-doctor's actual
abandonment/license screen logic — that is explicitly out of scope (SPEC.md's CAP-5
non-goal; see the story spec's Design Notes for the full reasoning). Only the
PRESENCE of both evidence fields is validated, never their truth (Never list) — the
operator/agent is trusted for accuracy, mirroring the org-audit list's
git-review-decides trust model (spec-13-4 Design Notes).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
from kedro.io.core import DatasetError

from pyforge.atlas import provenance as _provenance
from pyforge.atlas.mcp import session as _session
from pyforge.atlas.trending_candidates.query import (
    _INF,
    DATASET_NAME,
    _narrow_integral_floats,
)

# A SEPARATE versioning axis from `_provenance.SCHEMA_VERSION` (the PROVENANCE
# envelope's own version) — deliberately NOT reused. CAP-3's own envelope borrowing
# that unrelated constant is exactly the gap a deferred-work item (spec-13-3) raised:
# "a breaking change to the candidate payload cannot be signalled to a consumer at
# all" because nothing here ever moves when the candidate SHAPE changes. This int
# increments only when `HANDOFF_ENVELOPE_SCHEMA`'s shape changes.
HANDOFF_SCHEMA_VERSION = 1

# A plain Python dict, authored in real JSON-Schema-draft-2020-12 vocabulary
# (`type`/`properties`/`required`/`enum`/`const`) — NOT a `.schema.json` file plus the
# `jsonschema` library (Never list: no new pixi dependency for an XS story; it
# resolves only as an undeclared transitive today). This is genuinely "a documented
# schema" — dumpable via `json.dumps` for an external consumer, and walkable
# structurally (required keys present, primitive types match) without depending on an
# external validator. Only the fields load-bearing enough to be part of CAP-5's own
# contract are marked `required`; the rest of the record (the raw
# `trending_candidates_classified` row's own columns, carried through verbatim) is
# documented here too but left optional, since its exact column set is CAP-2's to
# extend without a breaking change to THIS envelope's own required shape.
HANDOFF_ENVELOPE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "pyforge-atlas trending-handoff envelope (CAP-5, Story 13.5, FR-68)",
    "type": "object",
    "required": [
        "schema_version",
        "dataset",
        "repo_full_name",
        "tier",
        "health_screen",
        "provenance",
        "handed_off_at",
    ],
    "properties": {
        "schema_version": {"type": "integer"},
        "dataset": {"type": "string"},
        "repo_full_name": {"type": "string"},
        "repo_url": {"type": ["string", "null"]},
        "pypi_name": {"type": ["string", "null"]},
        "tier": {"enum": ["1", "2"]},
        "reason": {"type": ["string", "null"]},
        "health_screen": {
            "type": "object",
            "required": ["verdict", "abandonment_signal", "license_clarity"],
            "properties": {
                # A successfully-emitted record's verdict is ALWAYS "pass" — a
                # failing verdict refuses before a record is ever assembled
                # (Boundaries & Constraints: "The health-screen gate runs on EVERY
                # call — no --force/skip flag").
                "verdict": {"const": "pass"},
                "abandonment_signal": {"type": "string", "minLength": 1},
                "license_clarity": {"type": "string", "minLength": 1},
            },
        },
        "provenance": {
            "type": "object",
            "required": ["kind"],
            "properties": {
                "kind": {"type": "string"},
                "build_stamp": {"type": ["string", "null"]},
                "build_stamp_newest": {"type": ["string", "null"]},
                "reason": {"type": ["string", "null"]},
            },
        },
        # Epoch SECONDS (project timestamp convention) — never an ISO string, never
        # milliseconds.
        "handed_off_at": {"type": "integer"},
    },
}

# `_classify_row` (pipelines/upstream_discovery/nodes.py) only ever returns tier
# "1"/"2" TOGETHER with a resolved OSI-license reason string — "already-on-conda-
# forge" and "unclassified-needs-human" are ALWAYS tier "skip". Gating eligibility on
# `tier in _ELIGIBLE_TIERS` therefore excludes BOTH by construction, resolving the
# `unclassified-needs-human`/not-on-cf ambiguity a deferred-work item raised against
# spec-13-3 (see tier-taxonomy.md's As-built note for the full contract) — WITHOUT
# gating on a `not_on_cf` boolean, which never existed as a column on this dataset in
# the first place.
_ELIGIBLE_TIERS = frozenset({"1", "2"})

# The envelope fields `hand_off_candidate` itself always sets, blind-overwriting
# whatever the selected row carries under the same key (review finding): a FUTURE
# CAP-2 column named exactly one of these would otherwise be silently clobbered by
# this envelope's own bookkeeping, corrupting the very data a Mason consumer reads.
# `hand_off_candidate` asserts none of these collide before ever writing to them.
_RESERVED_ENVELOPE_KEYS = frozenset({"schema_version", "dataset", "health_screen", "provenance", "handed_off_at"})


def _select_candidate_row(df: pd.DataFrame, repo_full_name: str) -> pd.DataFrame | None:
    """Casefold-match ``repo_full_name`` against ``df["repo_full_name"]`` (mirrors
    CAP-4's ``load_org_audit_candidates`` dedup precedent — ``alice/LibFoo`` and
    ``alice/libfoo`` are the same candidate), then apply the SAME deterministic sort
    ``query.py`` uses (``stars_total`` desc / ``repo_full_name`` asc / ``period`` asc)
    and take the first row. This resolves a repo appearing up to 3x across trending
    windows (daily/weekly/monthly, CAP-1) to exactly ONE handoff record (I/O &
    Edge-Case Matrix — and closes the deferred-work item CAP-2's own review pass
    raised: "a repo trending in more than one window ... inflating any 'how many
    tier-1 candidates' count").

    Returns a 1-row ``DataFrame`` (never a bare ``Series``) so the caller can run the
    identical whole-frame NaN/±inf-masking pipeline ``query.py``'s own envelope uses.
    ``None`` when nothing matches — an empty ``df``, a missing ``repo_full_name``
    column, or simply no row for this repo — never raises; the caller turns ``None``
    into the single "candidate not found" ``ValueError``."""
    if df.empty or "repo_full_name" not in df.columns:
        return None
    target = str(repo_full_name).strip().casefold()
    # The STORED value is stripped too (review finding), not just the caller's
    # `--repo` argument: a scraped row with incidental leading/trailing whitespace
    # would otherwise silently fail to match an otherwise-correct `--repo` value.
    is_match = df["repo_full_name"].map(lambda v: isinstance(v, str) and v.strip().casefold() == target)
    matches = df[is_match]
    if matches.empty:
        return None
    sort_cols = [c for c in ("stars_total", "repo_full_name", "period") if c in matches.columns]
    if sort_cols:
        # Coerce `stars_total` for the SORT KEY only (review finding: `query.py`
        # already had to add this exact fix for the identical column — a
        # numeric-looking STRING cell survives real scraped data and raises a raw
        # `TypeError` from `sort_values`, "verified live" per its own docstring).
        # A separate frame computes the order; the ORIGINAL (uncoerced) row is what
        # `.loc[order]` actually returns, so the emitted record's own `stars_total`
        # value is untouched by this — only which row wins the tie-break changes.
        sort_frame = matches
        if "stars_total" in sort_frame.columns:
            sort_frame = matches.assign(stars_total=pd.to_numeric(matches["stars_total"], errors="coerce"))
        order = sort_frame.sort_values(by=sort_cols, ascending=[c != "stars_total" for c in sort_cols]).index
        matches = matches.loc[order]
    return matches.iloc[[0]]


def hand_off_candidate(
    *,
    repo_full_name: str,
    verdict: str,
    abandonment_signal: str,
    license_clarity: str,
    project_path: Path | str | None = None,
    env: str | None = None,
) -> dict[str, Any]:
    """Resolve to either a structured record or a refused ``ValueError`` — never a
    partial or ambiguous result (Boundaries & Constraints).

    Validation order mirrors ``query_trending_candidates``'s own fail-fast contract:
    the health-screen gate (verdict + both evidence fields) is checked FIRST, before
    any dataset/session touch, so a bad verdict/evidence call never needs a seeded
    catalog — the gate runs on EVERY call, with no ``--force``/skip path. Only
    PRESENCE is validated here, never the TRUTH of the evidence (Never list).
    """
    if verdict != "pass":
        raise ValueError(f"health screen must PASS to hand off a candidate (verdict={verdict!r})")
    abandonment_signal = "" if abandonment_signal is None else str(abandonment_signal).strip()
    if not abandonment_signal:
        raise ValueError("health screen missing required field: abandonment_signal")
    license_clarity = "" if license_clarity is None else str(license_clarity).strip()
    if not license_clarity:
        raise ValueError("health screen missing required field: license_clarity")

    # Reuse the EXACT read seam query.py uses (Boundaries & Constraints: "no new
    # fetch, no new catalog entry, no new Kedro node"). A `DatasetError` (the
    # realistic "never ingested" state) degrades to an empty frame + an
    # "unavailable" provenance reason, IDENTICAL to query.py — so the row lookup
    # below naturally falls through to the "not found" `ValueError` with the
    # dataset's own unavailability reason folded in, rather than needing a second
    # error path (I/O & Edge-Case Matrix: "Dataset not yet ingested" resolves
    # through the same refusal). A session-BOOTSTRAP failure (e.g. missing
    # conf/local/credentials.yml) is deliberately left UNCAUGHT here — it is not a
    # policy-fail, it is an unexpected error (NFR-6 exit 2); query.py has the
    # identical unguarded shape for the identical reason (a pre-existing, seam-wide
    # gap — see deferred-work.md's spec-13-3 entry on this exact seam).
    with _session.bootstrapped_session(project_path, env=env) as s:
        catalog = _session.loaded_catalog(s)
        try:
            value, info = _provenance.load_with_provenance(catalog, DATASET_NAME)
        except DatasetError as exc:
            value = pd.DataFrame()
            info = _provenance.ProvenanceInfo(
                kind="unavailable",
                build_stamp=None,
                reason=f"{DATASET_NAME} unavailable: {exc}",
            )

    df = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
    matched = _select_candidate_row(df, repo_full_name)
    if matched is None:
        detail = f" ({info.reason})" if info.reason else ""
        raise ValueError(f"candidate not found in {DATASET_NAME!r}: {repo_full_name!r}{detail}")

    # Mask NaN/±inf the SAME way query.py's own envelope does (Code Map) — imported
    # directly from `query.py` rather than duplicated: an independent copy of this
    # JSON-safety fix would silently drift the moment either changed, the same
    # drift risk `REASON_ALREADY_ON_CF` (nodes.py) is deliberately exported to
    # prevent, and this story's Code Map does not touch `query.py` itself (Surgical
    # Changes). Narrowed FIRST (whole-number floats -> `Int64`) so an unrelated null
    # elsewhere in the FULL loaded table — which widens that column to float64 for
    # every row, this one included — does not leak `1200.0` for a genuinely
    # integral count in the ONE row this handoff actually emits.
    narrowed = _narrow_integral_floats(matched)
    json_safe = pd.notna(narrowed) & ~narrowed.isin([_INF, -_INF])
    row = narrowed.astype(object).where(json_safe, None).to_dict(orient="records")[0]

    # Gate on `tier` DIRECTLY, never on a `not_on_cf` boolean (Boundaries &
    # Constraints; module docstring above) — this single check excludes BOTH
    # "already-on-conda-forge" and "unclassified-needs-human" by construction.
    tier = row.get("tier")
    if tier not in _ELIGIBLE_TIERS:
        raise ValueError(f"{repo_full_name!r} is not eligible for handoff: tier={tier!r} reason={row.get('reason')!r}")

    # Guard BEFORE the blind overwrite below (review finding): a future CAP-2 column
    # sharing one of these exact names would otherwise vanish into this envelope's
    # own bookkeeping with no error at all.
    collisions = _RESERVED_ENVELOPE_KEYS.intersection(row)
    if collisions:
        raise ValueError(
            f"classified row for {repo_full_name!r} carries reserved handoff-envelope "
            f"key(s) {sorted(collisions)!r} — CAP-2 must not emit columns named these"
        )

    # The record = the selected row's own columns (repo identity, tier/reason, and
    # whatever else CAP-2 attached) PLUS the handoff envelope's own fields —
    # `schema_version`/`dataset` name THIS envelope (not `_provenance.SCHEMA_VERSION`,
    # which describes something else entirely), `health_screen` records the verdict
    # this call was gated on, `provenance` carries the dataset's own build-freshness
    # signal through unchanged, and `handed_off_at` timestamps the handoff itself.
    record: dict[str, Any] = dict(row)
    record["schema_version"] = HANDOFF_SCHEMA_VERSION
    record["dataset"] = DATASET_NAME
    record["health_screen"] = {
        "verdict": verdict,
        "abandonment_signal": abandonment_signal,
        "license_clarity": license_clarity,
    }
    record["provenance"] = {
        "kind": info.kind,
        "build_stamp": info.build_stamp,
        "build_stamp_newest": info.build_stamp_newest,
        "reason": info.reason,
    }
    # Epoch SECONDS, never an ISO string or milliseconds (project timestamp
    # convention) — `int()` truncates to whole seconds, matching
    # `IncrementalParquetDataset`'s own `int(time.time())` fetched_at stamp.
    record["handed_off_at"] = int(time.time())
    return record
