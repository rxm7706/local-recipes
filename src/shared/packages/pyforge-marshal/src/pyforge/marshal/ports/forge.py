"""``ForgePort`` -- Marshal's first and only outbound-network egress port
(Story 4.4, NFR-2, AD-34): a Protocol definition only (Structural Seed:
``ports/`` declares shapes, never implementations); implemented solely by
``adapters/forge_gh.py::GhForge`` (AD-4), a thin wrapper around the ``gh``
CLI -- never a raw HTTP/REST client, matching this repo's own entire
session-long practice of shelling out to ``gh``.

Mirrors ``ports/notify.py``'s own established egress-port shape: every
method on an egress-classified port is scanned by
``tests/meta/test_ad34_egress_registry_completeness.py``, which flags ANY
bare-``str``-typed parameter, "regardless of which parameter is
semantically 'the payload'" (``NotifyPort.notify_desktop``'s own docstring,
quoting that guard). ``title``/``body`` are the real payload and are typed
``Redacted``, exactly like every other egress port. The spec's own literal
Boundaries wording types ``repo``/``head_branch``/``base``/``head``/``ref``/
``check_name`` as bare ``str`` -- verified live against the guard, that
shape fails it on every one of those six parameters (none carries secret or
session-derived content; they are ``gh``-CLI routing identifiers Marshal
itself constructs, but the guard is intentionally undiscriminating about
role, only about type). ``ForgeRef`` wraps them in one small value type,
mirroring ``NotifyPort.notify_desktop``'s own precedent of restructuring a
signature around this exact guard rather than defeating it -- see this
story's own Spec Change Log for the full record.

- ``find_open_pr`` -- the existing-PR detection ``marshal deploy batch-pr``
  uses to decide ``create_pr`` vs. ``update_pr`` (idempotent, re-entrant: a
  re-run after new stories land on the same wave updates rather than
  duplicates).
- ``create_pr``/``update_pr`` -- open or update a PR's title/body. Both
  accept ONLY ``Redacted`` text, assembled and redacted by the caller
  BEFORE this port's boundary (AD-34's "redact at capture" idiom,
  ``NotifyPort``'s own convention) -- never a bare string passed through.
- ``add_labels`` -- a fired ``label`` landing rule's own action, applied
  once the PR exists; never blocking (the hygiene-preflight design: only a
  fired ``required_check`` rule can block).
- ``check_run_status`` -- the generic satisfaction answer for a fired
  ``required_check`` landing rule: "is there a green CI check by this
  declared name" -- the one mechanism that works for ANY future
  project-declared rule without Marshal ever knowing what the check
  actually verifies (see the story's own Design Notes).
- ``merge_pr`` (Story 4.8, FR-60/AD-40) -- merges a PR and, in the SAME
  forge-side write, optionally retires its head branch: ``marshal land``'s
  one merge+retire primitive, never a separate ``delete_branch``-only call
  (see this story's own Design Notes for why).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..core.egress import Redacted


@dataclass(frozen=True)
class ForgeRef:
    """One non-secret forge identifier -- a repo slug (``"<owner>/<name>"``),
    a branch/ref/commit-ish name, or a check-run name (Story 4.4). Wrapped
    in a value type rather than passed as a bare ``str`` PURELY to satisfy
    AD-34's egress-registry-completeness meta-test (see this module's own
    docstring) -- none of these values is secret-shaped or session-derived
    free text, so no redaction ever applies to a ``ForgeRef``; only
    ``title``/``body`` (the real payload) go through ``Redacted``."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError(f"value must be a non-empty str, got {self.value!r}")


@dataclass(frozen=True)
class PrInfo:
    """One pull request's identity (Story 4.4): ``number`` (the PR number),
    ``url`` (its web URL), ``state`` (the forge's own lowercase state
    string, e.g. ``"open"``/``"closed"``/``"merged"``), and ``base`` (the PR's
    own target base branch name, e.g. ``"main"`` -- added by code review,
    2026-08-06, P8: ``find_open_pr``'s result must be checkable against the
    policy-declared ``landing_base_branch`` before ``update_pr`` is ever
    called against it, so an open PR that targets a DIFFERENT base than
    policy declares is never silently updated)."""

    number: int
    url: str
    state: str
    base: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.number, int)
            or isinstance(self.number, bool)
            or self.number <= 0
        ):
            raise ValueError(f"number must be a positive int, got {self.number!r}")
        if not isinstance(self.url, str) or not self.url:
            raise ValueError(f"url must be a non-empty str, got {self.url!r}")
        if not isinstance(self.state, str) or not self.state:
            raise ValueError(f"state must be a non-empty str, got {self.state!r}")
        if not isinstance(self.base, str) or not self.base:
            raise ValueError(f"base must be a non-empty str, got {self.base!r}")


class ForgeCommandError(Exception):
    """Raised when a ``gh`` invocation fails: a non-zero exit (not
    authenticated, a rejected request, an unknown repo/PR), a missing ``gh``
    executable, a hung process exceeding its timeout, or a response that
    could not be parsed as the JSON this port's own callers expect. Mirrors
    ``adapters/vcs_git.py::VcsCommandError``'s identical shape -- never lets
    a raw ``subprocess`` exception or a JSON-decode error escape this port's
    adapter."""


class ForgePort(Protocol):
    def find_open_pr(self, repo: ForgeRef, head_branch: ForgeRef) -> PrInfo | None:
        """The already-open PR (if any) whose head is ``head_branch`` on
        ``repo``. ``None`` if none is open -- never raises for "not found",
        only for a real ``gh`` failure. Raises ``ForgeCommandError`` on any
        ``gh`` failure."""
        ...

    def create_pr(
        self, repo: ForgeRef, base: ForgeRef, head: ForgeRef, title: Redacted, body: Redacted
    ) -> PrInfo:
        """Opens a new PR on ``repo`` from ``head`` into ``base``.
        ``title``/``body`` accept ONLY ``Redacted`` -- never a bare ``str``
        -- assembled and redacted before this port's boundary (AD-34).
        Raises ``ForgeCommandError`` on any ``gh`` failure."""
        ...

    def update_pr(
        self, repo: ForgeRef, number: int, title: Redacted, body: Redacted
    ) -> PrInfo:
        """Updates an existing PR's title/body. Same ``Redacted``-only
        contract as ``create_pr``. Raises ``ForgeCommandError`` on any
        ``gh`` failure."""
        ...

    def add_labels(self, repo: ForgeRef, number: int, labels: tuple[str, ...]) -> None:
        """Applies ``labels`` to an existing PR -- a fired ``label``
        landing rule's own ACTION, never a blocking gate (Story 4.4's own
        hygiene-preflight design: only a fired ``required_check`` rule can
        block). Raises ``ForgeCommandError`` on any ``gh`` failure."""
        ...

    def check_run_status(
        self, repo: ForgeRef, ref: ForgeRef, check_name: ForgeRef
    ) -> str | None:
        """The named check run's own conclusion for ``ref`` (a commit sha
        or branch) on ``repo`` -- e.g. ``"success"``/``"failure"`` -- or
        ``None`` if no such check has run at all against ``ref``. Raises
        ``ForgeCommandError`` on any ``gh`` failure."""
        ...

    def merge_pr(
        self,
        repo: ForgeRef,
        number: int,
        strategy: ForgeRef,
        *,
        expected_head_sha: ForgeRef,
        delete_branch: bool,
    ) -> None:
        """Merges PR ``number`` on ``repo`` using ``strategy`` (one of
        ``"merge"``/``"squash"``/``"rebase"`` -- the closed vocabulary
        ``landing_merge_strategy`` already validates; this method trusts its
        caller and does not re-validate), optionally deleting the PR's own
        head branch as PART OF THE SAME forge-side write when
        ``delete_branch`` is ``True`` (Story 4.8, AD-40's landing primitive:
        merge and branch retirement are ONE atomic call, never two racing
        round-trips). ``strategy``/``expected_head_sha`` are wrapped in
        ``ForgeRef`` -- not typed bare ``str`` -- for the SAME reason
        ``repo``/``head_branch``/etc. already are (see this module's own
        docstring): AD-34's egress-registry-completeness guard flags any
        bare-``str`` parameter on an egress-classified port regardless of
        role, and neither is any more secret-shaped than those.

        ``expected_head_sha`` is REQUIRED (code review, 2026-08-06, both
        reviewers independently, the single most severe finding against
        this story): every OTHER write in this package's landing family
        (``land-story``'s ``merge_branch``, ``batch-pr``'s PR write) pins a
        captured sha and re-verifies it has not moved immediately before
        the write -- this method's FIRST version merged by PR NUMBER ALONE,
        with no equivalent guard, so a commit landing on the branch between
        this run's required-check poll and the merge call would be merged
        UNVETTED. Passed through to ``gh pr merge --match-head-commit``,
        which GitHub itself refuses atomically (a real, native primitive
        for exactly this TOCTOU, not a caller-side re-check racing the same
        window it is trying to close) if the PR's current head no longer
        matches. Raises ``ForgeCommandError`` on any ``gh`` failure,
        INCLUDING a head-commit mismatch -- a caller treats that as a hard
        stop, never a retried or silently-corrected merge."""
        ...
