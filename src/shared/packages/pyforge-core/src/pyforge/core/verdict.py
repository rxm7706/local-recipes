"""pyforge.core.verdict -- the ONE verdict-lattice rank/exit-domain
bookkeeping primitive, plus a generic exception-to-exit-code dispatch helper
(Story 14.3, SPEC-pyforge-core CAP-3).

Before this story, warden, marshal, and doctor each hand-rolled their own
``{member: rank for rank, member in enumerate(order)}`` dict-comprehension
and their own hand-typed/hand-computed exit-code domain literal, and herald
hand-rolled a most-specific-first ``isinstance`` exit-code dispatch loop.
``Lattice`` and ``dispatch_exit_code`` are the two shared MECHANISMS every
station's own domain data (its enum members, its own exit values, its own
station-specific projection logic) now builds on -- none of that domain
data moves here; only the bookkeeping does.

``Lattice`` is generic over any hashable member type -- no ``enum`` import
needed, so it works against any station's own ``StrEnum`` without
pyforge-core ever naming it.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence


class Lattice:
    """Rank + exit-domain bookkeeping for one station's verdict lattice.

    ``order`` is the rung sequence, strongest-first (or any fixed order a
    station chooses -- ``Lattice`` does not interpret the order, it only
    indexes it). ``exit_by_member`` maps each member to the process exit
    code it projects to; members absent from ``order`` may still appear in
    ``exit_by_member`` (``.rank`` is only ever called for members a station
    actually ranks), but every member's exit value contributes to
    ``.exit_codes``.
    """

    def __init__(self, order: Sequence[Hashable], exit_by_member: Mapping[Hashable, int]) -> None:
        self.order: tuple[Hashable, ...] = tuple(order)
        if len(set(self.order)) != len(self.order):
            raise ValueError(
                f"Lattice order contains a duplicate member: {self.order!r} -- "
                "a duplicate would silently let the last occurrence's rank win, "
                "producing an ambiguous rank with no error (review-pass patch, "
                "fail-loud per this codebase's convention)"
            )
        self.exit_by_member: dict[Hashable, int] = dict(exit_by_member)
        self._rank_by_member: dict[Hashable, int] = {member: rank for rank, member in enumerate(self.order)}

    def rank(self, member: Hashable) -> int:
        """The 0-indexed position of ``member`` in ``order`` -- replaces
        every station's own ``{m: i for i, m in enumerate(order)}``
        dict-comprehension."""
        return self._rank_by_member[member]

    @property
    def exit_codes(self) -> frozenset[int]:
        """The frozen exit-code domain -- replaces every station's own
        hand-typed/hand-computed domain literal."""
        return frozenset(self.exit_by_member.values())

    def narrows(self, other: Lattice) -> bool:
        """True when this lattice's exit-code domain is a subset of
        ``other``'s -- the concrete mechanism that turns a "subset of"
        docstring claim into a computed fact."""
        return self.exit_codes <= other.exit_codes


def dispatch_exit_code(
    exc: BaseException,
    table: Sequence[tuple[type[BaseException], int]],
    default: int,
) -> int:
    """Project ``exc`` to an exit code via a most-specific-first
    ``isinstance`` scan of ``table`` -- generalizes herald's
    ``exit_code_for`` algorithm so any station can reuse it against its own
    ``(exception_type, exit_code)`` table.

    ``table`` is checked in order: the first entry whose type ``exc`` is an
    instance of wins. An exception matching no entry falls through to
    ``default``.
    """
    for exc_type, code in table:
        if isinstance(exc, exc_type):
            return code
    return default
