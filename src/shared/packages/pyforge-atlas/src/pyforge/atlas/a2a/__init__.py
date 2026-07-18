"""The Agent-to-Agent (A2A) surface between cf_atlas and conda-forge-expert (Story E1, FR-11).

This module is the **sole structured inter-agent channel** and the **single schema source**
for BOTH alerts and insights (AD-20). Every structured payload the ``cf_atlas`` analytical
agent hands the ``conda-forge-expert`` authoring agent — a BSL-derived insight or an
FR-10/FR-18 alert — is one variant of the ONE payload family declared in :mod:`.schema`;
no competing dialect is defined anywhere else in the package (the architecture review's
"two competing alert dialects" hazard). Structural guards:
``tests/catalog/test_no_inline_io.py::test_a2a_sdk_only_in_a2a_layer`` (only ``a2a/`` imports
the a2a-sdk) + ``tests/a2a_surface/test_a2a_payloads.py`` (no other module defines a payload
schema — the dir avoids the ``a2a`` name so pytest's prepended path can't shadow the SDK).

Invariants:

- **AD-20** — one channel, one schema source (this package).
- **AD-17** — every payload carries an INJECTED ``build_stamp``; a payload cannot be built
  without one, and it is never read from ``datetime.now()`` at construction.
- **AD-8** — an insight references a BSL metric by its ``semantic.METRIC_PROVENANCE``
  identifier and carries the already-computed value; it never re-implements the arithmetic.

**Transport decision (resolved in Story E1; live wire DEFERRED — DW-E1-1).** The hand-off is
**direct in-process message-passing** (:func:`hand_off` → :class:`AuthoringInbox`) over a
genuine ``a2a.types.Message`` envelope, offline + deterministic. The live cross-process wire
(a running ``fasta2a`` server / A2A broker) is deferred — see :mod:`.transport` for the full
rationale.
"""

from __future__ import annotations

from pyforge.atlas.a2a.builders import build_alert_payload, build_insight_payload
from pyforge.atlas.a2a.schema import (
    SCHEMA_VERSION,
    A2ADecodeError,
    AtlasAlert,
    AtlasInsight,
    AtlasPayload,
    Severity,
    decode_payload,
)
from pyforge.atlas.a2a.transport import (
    A2ATransportError,
    AuthoringInbox,
    from_message,
    hand_off,
    to_message,
)

__all__ = [
    "SCHEMA_VERSION",
    "A2ADecodeError",
    "A2ATransportError",
    "AtlasAlert",
    "AtlasInsight",
    "AtlasPayload",
    "AuthoringInbox",
    "Severity",
    "build_alert_payload",
    "build_insight_payload",
    "decode_payload",
    "from_message",
    "hand_off",
    "to_message",
]
