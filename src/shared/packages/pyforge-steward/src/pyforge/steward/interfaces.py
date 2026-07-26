"""The Duty contract (AD-7) — Steward's null-engine precedent, mirroring warden.

A duty is a unit of platform work (keys, deploy, provision, budget). It is a
``Protocol``, not a base class, so a duty never inherits behaviour it did not
ask for and conformance is checked structurally.

``DutyResult`` carries the outcome. A duty **never** calls ``sys.exit()``: it
returns a result and ``cli.main()`` is the sole owner of the process exit code
(AD-8). That separation is what lets a duty be unit-tested without a subprocess.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class DutyResult:
    """What a duty returns. Frozen: a result is evidence, not a scratchpad."""

    ok: bool
    summary: str
    details: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class Duty(Protocol):
    """Structural contract every duty satisfies."""

    name: str

    def run(self, ns: argparse.Namespace) -> DutyResult:
        """Execute the duty. Must not raise SystemExit and must not exit."""
        ...


class NullDuty:
    """The null engine — satisfies :class:`Duty` and does nothing.

    Exists so the protocol is exercised from Story 1.1 rather than first proven
    when a real duty lands, and so `cli` has something to dispatch to before any
    duty module exists.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, ns: argparse.Namespace) -> DutyResult:   # noqa: ARG002
        return DutyResult(ok=True, summary=f"{self.name}: no verbs yet (Story 1.1)")
