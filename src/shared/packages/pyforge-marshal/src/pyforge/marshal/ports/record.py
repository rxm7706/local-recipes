"""``RecordPort`` -- the sole port classified ``egress: true`` (Story 2.6,
architecture spine AD-34). A Protocol definition only (Structural Seed:
``ports/`` declares shapes, never implementations); implemented solely by
``adapters/fs_local.py::LocalFs.write_redacted_atomic`` (AD-4), which
delegates entirely to the existing ``write_text_atomic`` write mechanics --
no new I/O primitive, only a type boundary.

One method, ``write_redacted_atomic``: takes a ``core.egress.Redacted``
payload, never a bare ``str`` -- the structural half of AD-34's "an egress
port accepts only a Redacted payload" guarantee, enforced by
``tests/meta/test_ad34_egress_registry_completeness.py``. A caller obtains a
``Redacted`` only via ``core.egress.to_redacted()``, the one redacting
serializer, so a call site can never route unredacted content through this
port.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..core.egress import Redacted


class RecordPort(Protocol):
    def write_redacted_atomic(self, path: Path, payload: Redacted) -> None:
        """Write ``payload.text`` to ``path`` via the same
        temp-file-then-``os.replace`` atomic sequence ``FsPort.
        write_text_atomic`` already uses, creating parent directories as
        needed. Raises ``FsError`` on failure -- this port adds no new
        failure mode, only a narrower accepted payload type."""
        ...
