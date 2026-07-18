"""The SINGLE Agent-to-Agent payload schema family (Story E1, FR-11, AD-20).

AD-20 makes the ``a2a/`` module the **sole** structured inter-agent channel between
the ``cf_atlas`` analytical agent and the ``conda-forge-expert`` authoring agent, and
the **single schema source** for BOTH alerts and insights. The architecture review
warned explicitly against *two competing alert dialects*; the answer is exactly ONE
payload family declared here, discriminated by ``kind``:

- :class:`AtlasInsight` (``kind="insight"``) — a BSL-derived finding (staleness,
  adoption-stage, feedstock-health, actionable scope, downloads, …). It **references a
  BSL metric by its stable identifier** (``metric_id`` ∈ ``semantic.METRIC_PROVENANCE``)
  and carries the ALREADY-COMPUTED value; it NEVER re-implements the metric arithmetic
  (AD-8 — metric logic stays in ``semantic/``, validated here against the registry).
- :class:`AtlasAlert` (``kind="alert"``) — a contract violation / policy breach
  (the FR-10/FR-18 alert family): a severity + subject + violated rule + evidence.

Every payload carries an **injected** ``build_stamp`` (AD-17): payloads feeding
authoring decisions travel with their pipeline build timestamp. The stamp is a required
constructor argument, never ``datetime.now()`` at construction, so the offline gate is
deterministic — mirroring ``dashboard/factory_status.py`` and the B-wave datasets.

Schemas are ``frozen`` + ``extra="forbid"`` so a payload is immutable and a stray/unknown
field is rejected rather than silently carried — the round-trip preserves the payload
EXACTLY (:mod:`pyforge.atlas.a2a.transport`).
"""

from __future__ import annotations

import json
import math
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pyforge.atlas.semantic import METRIC_PROVENANCE

# Bumped only on a breaking schema change; travels on the wire so a receiver can reject
# an incompatible producer instead of mis-parsing it.
SCHEMA_VERSION = "1"


class A2ADecodeError(ValueError):
    """Raised when a wire payload cannot be decoded (unknown/absent ``kind``,
    malformed JSON, or a schema-validation failure) — a controlled failure, never
    an uncaught crash (Reviewer-B unknown-kind contract)."""


def _ensure_json_native(obj: Any, path: str) -> Any:
    """Reject any non-JSON-native value (set, object, tuple, …) with a controlled error.

    A2A payloads must be JSON-native so the canonical-JSON round-trip preserves them
    EXACTLY — pydantic would otherwise silently coerce e.g. a ``set`` into a list (a silent
    round-trip MUTATION). Validated recursively at construction, so a bad value fails fast.
    ``bool``/``int``/``float``/``str``/``None`` are scalars; ``dict`` keys must be strings.
    """
    if isinstance(obj, float) and not math.isfinite(obj):
        # JSON has no NaN/Infinity; pydantic's default serializes them to null (a SILENT
        # nan/inf -> None mutation across the round-trip), so reject them up front.
        raise ValueError(f"{path}: non-finite float {obj!r} is not JSON-native")
    if obj is None or isinstance(obj, (str, int, float)):  # bool is a subclass of int
        return obj
    if isinstance(obj, dict):
        for key, val in obj.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: JSON object keys must be strings, got {type(key).__name__}")
            _ensure_json_native(val, f"{path}.{key}")
        return obj
    if isinstance(obj, list):
        for i, val in enumerate(obj):
            _ensure_json_native(val, f"{path}[{i}]")
        return obj
    raise ValueError(
        f"{path}: non-JSON-native value of type {type(obj).__name__} — a2a payloads must be "
        f"JSON-native so the round-trip preserves them exactly"
    )


class Severity(str, Enum):
    """Alert severity ladder (ascending). ``str`` mix-in → JSON-native round-trip."""

    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class _BasePayload(BaseModel):
    """Fields common to every inter-agent payload (the single family root)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = SCHEMA_VERSION
    # AD-17: the pipeline build timestamp travels IN the payload. Required + injected —
    # never defaulted from datetime.now(), so authoring never consumes an unstamped payload.
    build_stamp: str
    # What the payload is about: a package / feedstock / maintainer identifier.
    subject: str

    @field_validator("build_stamp")
    @classmethod
    def _stamp_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("build_stamp is required (AD-17) — an empty stamp is no stamp")
        return v

    @field_validator("subject")
    @classmethod
    def _subject_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("subject is required — the payload must name what it is about")
        return v


class AtlasInsight(_BasePayload):
    """A BSL-derived insight referencing a metric by its stable identifier (AD-8)."""

    kind: Literal["insight"] = "insight"
    # A stable BSL metric identifier — MUST be a key of semantic.METRIC_PROVENANCE. The
    # payload references the metric; the arithmetic lives in semantic/ (AD-8), never here.
    metric_id: str
    # The already-computed metric value (str/num/bool/None or a JSON-native structure).
    value: Any = None
    # Optional structured context (dimensions the value was computed over, etc.).
    detail: dict[str, Any] = Field(default_factory=dict)

    @field_validator("value")
    @classmethod
    def _value_json_native(cls, v: Any) -> Any:
        return _ensure_json_native(v, "value")

    @field_validator("detail")
    @classmethod
    def _detail_json_native(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _ensure_json_native(v, "detail")

    @field_validator("metric_id")
    @classmethod
    def _known_metric(cls, v: str) -> str:
        if v not in METRIC_PROVENANCE:
            raise ValueError(
                f"unknown BSL metric id {v!r}; insight payloads must reference a metric "
                f"declared in semantic.METRIC_PROVENANCE (AD-8), one of "
                f"{sorted(METRIC_PROVENANCE)}"
            )
        return v


class AtlasAlert(_BasePayload):
    """A contract violation / policy breach (FR-10/FR-18 alert family)."""

    kind: Literal["alert"] = "alert"
    severity: Severity
    # The violated rule / contract / policy identifier.
    rule: str
    # Structured evidence for the breach (may be empty when none was supplied).
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence")
    @classmethod
    def _evidence_json_native(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _ensure_json_native(v, "evidence")

    @field_validator("rule")
    @classmethod
    def _rule_present(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("rule is required — an alert must name the violated rule")
        return v


# The discriminated payload family. Every inter-agent structured payload is one of these
# two variants — there is no third dialect (AD-20).
AtlasPayload = Union[AtlasInsight, AtlasAlert]

# The wire ``kind`` -> model dispatch table (also the exhaustive set of known kinds).
_KIND_TO_MODEL: dict[str, type[_BasePayload]] = {
    "insight": AtlasInsight,
    "alert": AtlasAlert,
}


def decode_payload(payload_json: str) -> AtlasPayload:
    """Reconstruct the exact payload from its canonical JSON, dispatching on ``kind``.

    An unknown/absent ``kind``, malformed JSON, or a schema-validation failure raises
    :class:`A2ADecodeError` — a controlled error, never an uncaught crash.
    """
    try:
        obj = json.loads(payload_json)
    except (ValueError, TypeError) as exc:
        raise A2ADecodeError(f"payload is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise A2ADecodeError(f"payload must be a JSON object, got {type(obj).__name__}")
    kind = obj.get("kind")
    model = _KIND_TO_MODEL.get(kind) if isinstance(kind, str) else None
    if model is None:
        raise A2ADecodeError(
            f"unknown payload kind {kind!r}; known kinds: {sorted(_KIND_TO_MODEL)}"
        )
    try:
        return model.model_validate(obj)
    except ValueError as exc:  # pydantic ValidationError is a ValueError
        raise A2ADecodeError(f"payload failed {kind} schema validation: {exc}") from exc
