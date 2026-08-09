"""The `MasonError` taxonomy root (AD-7, FR-33).

Every anticipated failure Mason raises is a `MasonError` (or, in later
stories, one of its subclasses) carrying a stable, colon-delimited
identifier -- part of the public surface (Consistency Conventions: "Error
identifiers... Identifiers are API -- changing one is a MAJOR bump"), shaped
like `cfe:unresolved` / `ship:credential-missing` / `engine:absent`.

No concrete subclass or raise site is added by this story (see the spec's
Never boundary) -- those belong to the epics that implement CFE resolution,
credentials, and engines. This module pins the taxonomy machinery only.

Per AD-1 (shared shapes, no behaviour), this module holds the exception type
and its validation only -- no formatting beyond `__str__`, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

# Two lowercase, hyphen-delimited segments joined by a single colon, e.g.
# "cfe:unresolved" or "ship:credential-missing". Neither segment may be
# empty, start/end with a hyphen, or contain a double hyphen. `\Z` (not `$`)
# anchors strictly to the end of the string -- `$` alone would also accept a
# single trailing newline, letting a malformed identifier through.
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*:[a-z0-9]+(-[a-z0-9]+)*\Z")


class MasonError(Exception):
    """Base class for every anticipated Mason failure.

    `identifier` must be a string matching `_IDENTIFIER_PATTERN`, and
    `message` must be a string with non-whitespace content that states what
    failed and what to do next (NFR-14); construction raises `ValueError`
    for either violation, since
    an unvalidated identifier or a message with nothing to say is exactly
    the drift AD-7 and NFR-14 exist to prevent.
    """

    def __init__(self, identifier: str, message: str) -> None:
        if not isinstance(identifier, str) or not _IDENTIFIER_PATTERN.match(identifier):
            raise ValueError(
                f"invalid MasonError identifier {identifier!r}: must be a string "
                f"matching {_IDENTIFIER_PATTERN.pattern!r} (e.g. 'cfe:unresolved')"
            )
        if not isinstance(message, str) or not message.strip():
            raise ValueError(
                "MasonError message must be a non-empty string: it must state "
                "what failed and what to do next (NFR-14)"
            )
        self.identifier = identifier
        self.message = message
        super().__init__(identifier, message)

    def __str__(self) -> str:
        return f"{self.identifier}: {self.message}"


class CfeImportFloorError(MasonError):
    """The selected CFE interpreter is missing part of CFE's import floor
    (FR-3, NFR-14).

    Raised by `cfe.py::ensure_import_floor` when `probe_import_floor`
    reports any gap -- construction raises `ValueError` for an empty
    `missing`, since an import-floor error naming nothing missing is
    exactly the incoherent state this class exists to rule out. `missing`
    holds pip/conda *distribution* names (e.g. `pyyaml`), not import names
    (`yaml`), in `cfe.CFE_IMPORT_FLOOR`'s declared order, so the message
    names exactly what a user would `pip install`/`conda install`; it is
    stored as a `tuple`, not whatever `Sequence` was passed, matching the
    immutable-shape convention every other dataclass in this story follows.
    """

    def __init__(self, missing: Sequence[str], interpreter: str) -> None:
        missing = tuple(missing)
        if not missing:
            raise ValueError(
                "CfeImportFloorError requires a non-empty `missing`: an "
                "import-floor error naming nothing missing is incoherent"
            )
        self.missing = missing
        self.interpreter = interpreter
        message = (
            f"interpreter {interpreter!r} is missing CFE's import floor: "
            f"{', '.join(missing)}"
        )
        super().__init__("cfe:import-floor-missing", message)
