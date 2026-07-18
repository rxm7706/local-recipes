"""A2A wire transport: payload ↔ ``a2a.types.Message`` serde + the in-process hand-off.

**Transport decision (Story E1 — resolved here; live wire DEFERRED).** The AC lets the
transport resolve in this story and lets the *live cross-process* wire be deferred. We
resolve it as **direct in-process message-passing** (:func:`hand_off` → :class:`AuthoringInbox`):
the ``cf_atlas`` analytical agent serializes a payload to a genuine ``a2a.types.Message`` and
delivers it directly to the ``conda-forge-expert`` authoring agent's inbox, which deserializes
it back to the exact payload. This is a real (in-process) A2A hand-off proving the
analytical→authoring direction with ZERO network — the offline/deterministic gate contract.

The genuine cross-process wire (a running ``fasta2a`` server / an A2A broker between two OS
processes) is **DEFERRED** to a follow-up (ledger entry **DW-E1-1**): standing up a live
server needs a bound socket + a second process, neither of which comes up offline in-container,
and faking a broker would be dishonest. The message ENVELOPE is already the real a2a-sdk
``Message`` here, so the follow-up is a delivery-substrate swap, not a schema change.

**Why the payload rides as canonical JSON inside a ``DataPart``.** The a2a-sdk types are
protobuf-backed; a protobuf ``Struct``/``Value`` coerces every number to ``double``, so an
``int`` severity or an ``int`` inside untyped ``evidence`` would come back as a ``float`` and
break "preserves the payload EXACTLY". So the wire carries the payload's canonical
``model_dump_json`` string in a single ``DataPart`` field, and the receiver reconstructs the
pydantic model from that JSON — exact for typed fields, untyped ``evidence``/``value``,
nesting, and unicode alike.
"""

from __future__ import annotations

import hashlib

import a2a.types as a2a_types
from google.protobuf import json_format, struct_pb2
from pydantic_core import PydanticSerializationError

from pyforge.atlas.a2a.schema import A2ADecodeError, AtlasPayload, _BasePayload, decode_payload

# The single DataPart field carrying the canonical payload JSON, and the metadata keys
# that mirror the discriminator + stamp for envelope-level inspection (never the source of
# truth — the payload JSON is).
_PAYLOAD_KEY = "atlas_payload"
_KIND_KEY = "atlas_kind"


class A2ATransportError(RuntimeError):
    """Raised when a payload cannot be serialized to / located within an A2A message."""


def _deterministic_message_id(payload_json: str) -> str:
    """A content-addressed, deterministic message id (no uuid, no now() — offline gate)."""
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:16]
    return f"atlas-a2a-{digest}"


def to_message(payload: AtlasPayload, *, message_id: str | None = None) -> a2a_types.Message:
    """Serialize a payload into a genuine ``a2a.types.Message`` (role = AGENT).

    The payload's canonical JSON rides in one ``DataPart``; ``kind``/``schema_version``/
    ``build_stamp`` are mirrored into the message metadata for cheap envelope inspection.
    ``message_id`` defaults to a deterministic content hash so the gate is reproducible.
    """
    if not isinstance(payload, _BasePayload):
        raise A2ATransportError(
            f"not an a2a payload: {type(payload).__name__} — construct one via the "
            f"a2a builders (AD-20: the a2a/ module is the single schema source)"
        )
    try:
        payload_json = payload.model_dump_json()
    except (PydanticSerializationError, ValueError, TypeError) as exc:
        raise A2ATransportError(
            f"payload is not JSON-serializable (a field carries a non-JSON value): {exc}"
        ) from exc

    # Serialization-boundary self-check: re-decode the canonical JSON and require it to
    # reproduce the payload EXACTLY. This closes the `model_construct` bypass (pydantic's
    # validator-skipping escape hatch) — a payload built that way can carry a set/int-key
    # that model_dump_json() silently coerces to a list/str; the round-trip would then
    # mutate it with no error. Any construction path that isn't round-trip-safe fails HERE
    # instead of shipping a corrupted payload (E1 review, Reviewer-B finding 1).
    try:
        if decode_payload(payload_json) != payload:
            raise A2ATransportError(
                "payload failed the serialization self-check — it is not round-trip-safe "
                "(likely built via model_construct, bypassing field validation)"
            )
    except A2ADecodeError as exc:
        raise A2ATransportError(f"payload failed the serialization self-check: {exc}") from exc

    data_value = struct_pb2.Value()
    json_format.ParseDict({_PAYLOAD_KEY: payload_json}, data_value)
    metadata = struct_pb2.Struct()
    metadata.update(
        {
            _KIND_KEY: payload.kind,
            "schema_version": payload.schema_version,
            "build_stamp": payload.build_stamp,
        }
    )
    return a2a_types.Message(
        message_id=message_id or _deterministic_message_id(payload_json),
        role=a2a_types.Role.ROLE_AGENT,
        parts=[a2a_types.Part(data=data_value)],
        metadata=metadata,
    )


def _extract_payload_json(message: a2a_types.Message) -> str:
    """Pull the canonical payload JSON out of the message's DataPart."""
    for part in message.parts:
        # A DataPart is a Part whose `data` (a protobuf Value) holds a struct with our key.
        if part.HasField("data") and part.data.HasField("struct_value"):
            mapping = json_format.MessageToDict(part.data.struct_value)
            candidate = mapping.get(_PAYLOAD_KEY)
            if isinstance(candidate, str):
                return candidate
    raise A2ATransportError(
        f"no atlas payload DataPart found on the message (expected a {_PAYLOAD_KEY!r} field)"
    )


def from_message(message: a2a_types.Message) -> AtlasPayload:
    """Deserialize an ``a2a.types.Message`` back into the exact payload.

    Raises :class:`A2ATransportError` if the envelope carries no atlas payload, and
    :class:`A2ADecodeError` if the payload JSON is malformed / of an unknown kind — both
    controlled failures, never an uncaught crash.
    """
    return decode_payload(_extract_payload_json(message))


class AuthoringInbox:
    """The ``conda-forge-expert`` authoring-agent side of the hand-off.

    Receives serialized A2A messages, decodes each to its exact payload, and records the
    ordered stream. This is the direct-message receiver — no broker, no socket.
    """

    def __init__(self) -> None:
        self._received: list[AtlasPayload] = []

    def receive(self, message: a2a_types.Message) -> AtlasPayload:
        payload = from_message(message)
        self._received.append(payload)
        return payload

    @property
    def payloads(self) -> tuple[AtlasPayload, ...]:
        """The ordered payloads received so far."""
        return tuple(self._received)


def hand_off(
    payload: AtlasPayload,
    inbox: AuthoringInbox,
    *,
    message_id: str | None = None,
) -> AtlasPayload:
    """The ``cf_atlas`` analytical agent hands a structured payload to the authoring inbox.

    Serializes to a genuine a2a ``Message`` and delivers it directly (in-process). Returns
    the payload the authoring side decoded — equal to ``payload``, proving the
    analytical→authoring direction preserves the payload exactly.
    """
    return inbox.receive(to_message(payload, message_id=message_id))
