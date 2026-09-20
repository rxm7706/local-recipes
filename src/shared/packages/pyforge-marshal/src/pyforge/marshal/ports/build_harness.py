"""``BuildHarnessPort`` -- the FR-52 seam for the second engine
(``bmad-build-auto`` / a plain background agent session), sibling to
``HarnessPort``'s bmad-loop coverage (Story 22.1, spec-marshal-single-story-
dispatch CAP-1; Story 22.8 / CAP-8 makes it adapter-plural and
profile-driven).

A Protocol definition only; implemented solely by
``adapters/harness_bmadbuild.py``. Every subprocess invocation of a
session-harness CLI (launch AND authcheck probes) lives there -- never
scattered through ``cli/`` or ``core/`` (AD-4 / FR-52)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..core.harness_profile import HarnessProfile, WireWrap


@dataclass(frozen=True)
class HarnessCandidateSkip:
    """One preference candidate the resolution walked past (Story 22.8):
    the profile name and WHY it was skipped (unknown name, binary not
    found, authcheck failed/timed out). Every skip is reported as a
    structured ``MRS-DISP-027`` finding -- never silent; the 2026-08-27
    cursor-auth failure mode is exactly this record."""

    profile: str
    reason: str


@dataclass(frozen=True)
class HarnessResolution:
    """``BuildHarnessPort.binary_present``'s profile-aware result (Story
    22.8): the chosen profile (name + parsed spec + resolved binary path)
    or ``None``, plus every skipped candidate and any overlay-profile load
    errors. Truthy iff a profile resolved -- preserving the port method's
    original ``if not binary_present()`` meaning while carrying the
    evidence CAP-8 requires.

    Story 28.2 adds ``wrapper_binary_path``: the resolved path of the
    profile's declared wire-compression wrapper, or ``None`` when the
    profile declares none OR its binary did not resolve. Resolved HERE
    because this is the method that already holds ``repo_root`` (the
    fallback-dir anchor) -- never inside ``dispatch``, which does not. A
    wrapper that fails to resolve NEVER skips the candidate: the layer
    degrades, the profile still dispatches."""

    profile: str | None
    binary_path: str | None = None
    spec: HarnessProfile | None = None
    skipped: tuple[HarnessCandidateSkip, ...] = ()
    profile_errors: tuple[str, ...] = ()
    wrapper_binary_path: str | None = None

    def __bool__(self) -> bool:
        return self.profile is not None


@dataclass(frozen=True)
class DispatchLaunchResult:
    """Detached ``BuildHarnessPort.dispatch`` result (Story 22.1): facts the
    caller could not know before launch. Story 22.8 adds the launching
    ``profile`` and, when the policy model tier could not be rendered for
    that profile, the ``model_omitted_reason`` (the caller's
    ``MRS-DISP-029``); ``model`` carries the model string actually rendered
    into the argv (post per-profile translation), or ``None`` when
    omitted.

    Story 28.2 adds ``wire``: the wire-compression decision this launch
    actually made (applied / degraded-with-a-reason / off). ``None`` only
    when the caller passed no ``wire_layer`` at all. The caller reports a
    degraded decision as ``MRS-DISP-033`` and journals the whole payload,
    so "was this session wrapped, and if not, why not" is a recorded fact
    of every dispatch rather than something inferred from an argv."""

    pid: int
    command: tuple[str, ...]
    model: str | None
    budget_env: Mapping[str, str]
    profile: str | None = None
    model_omitted_reason: str | None = None
    wire: WireWrap | None = None


class BuildHarnessPort(Protocol):
    def binary_present(self, preference: Sequence[str] = (), repo_root: Path | None = None) -> HarnessResolution:
        """Resolve the first ``preference`` profile whose binary exists (on
        ``PATH`` or in a profile-declared repo-root-relative fallback dir)
        AND whose declared authcheck passes (Story 22.8) -- binary presence
        alone was necessary-but-insufficient, proven live 2026-08-27.
        Returns a ``HarnessResolution`` (truthy iff dispatchable) carrying
        every skipped candidate; never raises."""
        ...

    def dispatch(
        self,
        worktree: Path,
        *,
        resolution: HarnessResolution,
        project_slug: str,
        story_key: str,
        spec_path: Path,
        model: str | None,
        budget_env: Mapping[str, str],
        log_path: Path,
        wire_layer: Mapping[str, object] | None = None,
    ) -> DispatchLaunchResult:
        """Detach-launch one plain background agent session running
        ``bmad-build-auto`` against ``spec_path`` inside ``worktree``, using
        ``resolution``'s profile (Story 22.8: argv rendered from the
        profile's declarative template; the model tier translated per
        profile, omitted-with-reason rather than guessed).
        ``BMAD_ACTIVE_PROJECT`` is set to ``project_slug`` in the child's
        environment; artifact paths are physical under the worktree (never
        ``scripts/bmad-switch``). Always ``Popen`` with
        ``start_new_session=True`` -- never a CLI's own self-backgrounding
        flag, so the returned ``pid`` is the session process the dispatch
        supervisor tracks. Raises ``BuildHarnessError`` only when the
        process could not be LAUNCHED (including a falsy ``resolution``).

        Story 28.2 (SPEC-marshal-token-economy CAP-2): ``wire_layer`` is
        the resolved ``{"enabled", "aggressiveness"}`` entry for the
        ``wire`` layer of policy's declared ``[context]`` block -- ``None``
        or disabled means the launch is byte-identical to pre-28.2. When
        enabled AND the profile's wrapper resolves, the launch runs through
        it with the CCR store scoped inside ``worktree``; when enabled and
        it does not, the layer disables with a reason on the returned
        ``wire`` and the session launches unwrapped. Never a blocked
        launch."""
        ...
