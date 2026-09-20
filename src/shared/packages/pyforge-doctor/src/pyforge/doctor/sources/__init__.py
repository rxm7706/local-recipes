"""Doctor's own source registry — scope + subject + owner per ``Source`` (Story 6.2).

``pyforge.doctor.sources`` was empty: nothing declared which station's artifact
each ``models.Source`` member judges (``subject_station``) or which station
implements the gather that judges it (``owning_station``). Two consumers need
that declaration and had no place to read it from:

1. The fleet's detector-ownership audit (Charter §6 / INV-4 — "the station
   that owns an artifact must not be the final word on judging it") has
   nowhere to check subject-vs-owner other than reading source code by hand.
2. ``scripts/detectors.py``'s registry is built by AST-scanning
   ``scripts/*_check.py`` files on disk — a source that already lives inside
   Doctor's own package (e.g. ``marshal-durability``) is invisible to it,
   because there is no file for it to scan.

This module is that registry: a validated, exhaustive ``REGISTRY`` tuple, one
``SourceRegistration`` per current ``Source`` member. ``SourceRegistration``
mirrors ``checks.registry.CheckSpec``'s thin frozen-dataclass-plus-``list_*``
shape, but adds a ``__post_init__`` that FAILS LOUD rather than accepting a
default: a registration with no declared subject or owner, or a scope outside
the closed ``{"repo", "runtime"}`` pair, is a bug in this file, not a value
worth storing.

``tests/unit/test_sources_registry.py`` enforces the other half — that
``REGISTRY`` and ``Source`` stay in exact set-equality, in both directions —
mirroring ``checks/registry.py``'s own
``test_every_cataloged_category_is_dispatchable_by_gather_one`` tripwire.
Registering a *new* ``Source`` member is each of Stories 6.4-6.9's own job
(their own ``gather()`` lands alongside their own registration); this module
built the mechanism, and Story 6.4 was the first to land registrations of its
own on top of it (``LEDGER_REGRESSION``, ``STORY_STATUS``). The count itself
is deliberately NOT written down in prose here: ``REGISTRY`` is the count, and
``test_sources_registry.py`` pins it to ``Source`` in both directions, so a
number in this docstring could only ever be a second source of truth that goes
stale the next time a story appends a row (it already did once, at 9).

``scripts/detectors.py``'s consumption of this module (its ``_doctor_sources``
helper) degrades to ``(False, [])`` when ``pyforge.doctor`` isn't importable
in the active environment. That is DELIBERATELY not the same discipline as
``discover()``'s own "unknown, never green" handling of a detector it cannot
run — a Doctor-owned source's absence from the active environment is a normal,
expected outcome (Doctor is a dedicated lean package, not installed in every
env that runs this script), not a detector failing to execute. The caller
still needs to tell "the package is here and reports zero" apart from "the
package isn't here," which is what the leading ``bool`` is for, not a
registry finding.

Story 6.3 adds two consumers of this same ``REGISTRY``: ``scope_for`` is the
one canonical per-source scope lookup — the CLI's ``doctor check --scope
{repo,runtime,all}`` filter reads every category's scope through it, rather
than a second hand-rolled scope list that would drift the moment a
``SourceRegistration``'s ``scope`` changes. ``degrade_on_exception`` is a
reusable "cannot evaluate here" wrapper for a future ``scope="runtime"``
source's own gather (e.g. Story 6.5's ``dashboard_drift``, which reads tmux/
``~/.bmad-loops`` state absent in CI) — see Story 6.3's OWN spec Design Notes
(review finding: this used to point at Story 6.5, which is the source named
in the example, not the story that wrote this rationale) for why it is
deliberately NOT wired into today's three existing (``scope="repo"``)
dispatch calls, whose own gather functions already promise never to raise.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models import DoctorStatus, Finding, Source

__all__ = (
    "REGISTRY",
    "SourceRegistration",
    "degrade_on_exception",
    "list_sources",
    "scope_for",
)

_VALID_SCOPES = frozenset({"repo", "runtime"})


@dataclass(frozen=True)
class SourceRegistration:
    """One ``Source`` member's scope, judged subject, and implementing owner.

    ``scope`` is ``"repo"`` (reads only tracked files/git history, runs
    anywhere) or ``"runtime"`` (reads host state, cannot run in CI) — the same
    two values ``scripts/detectors.py``'s own ``DETECTOR = {"scope": ...}``
    declares. Every source registered here today is ``"repo"``; Story 6.3
    builds the scope-selection mechanism (``scope_for``,
    ``degrade_on_exception``) without registering one — Story 6.5's
    ``dashboard_drift`` is what introduces the first ``"runtime"`` member.

    ``subject_station`` is the station whose artifact this source judges;
    ``owning_station`` is the station whose ``gather()`` implements the
    judgement (always ``"doctor"`` today — Doctor holds every verdict).

    Fails loud at construction rather than accepting a default: a
    registration with no declared subject or owner, or a scope outside the
    closed pair above, is a defect in THIS FILE, not a value worth storing.
    """

    source: Source
    scope: str
    subject_station: str
    owning_station: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, Source):
            raise ValueError(
                f"source must be a models.Source member, got {self.source!r}"
            )
        if not self.subject_station or not self.subject_station.strip():
            raise ValueError(
                f"{self.source!r}: subject_station must be a non-empty "
                f"station name, got {self.subject_station!r}"
            )
        if not self.owning_station or not self.owning_station.strip():
            raise ValueError(
                f"{self.source!r}: owning_station must be a non-empty "
                f"station name, got {self.owning_station!r}"
            )
        if self.scope not in _VALID_SCOPES:
            raise ValueError(
                f"{self.source!r}: scope must be one of "
                f"{sorted(_VALID_SCOPES)}, got {self.scope!r}"
            )

    def to_json_dict(self) -> dict[str, str]:
        """Serialize to the plain-dict shape ``scripts/detectors.py`` and any
        future consumer (the detector-ownership audit) both need — mirrors
        ``models.Finding.to_json_dict()``'s own convention rather than making
        each consumer hand-rebuild this dataclass's four fields."""
        return {
            "source": self.source.value,
            "scope": self.scope,
            "subject_station": self.subject_station,
            "owning_station": self.owning_station,
        }


# Subject/owner assignment, one row per Source member (each story's own Design
# Notes carries the full rationale per row). Every entry is
# owning_station="doctor" (Doctor holds every verdict) and scope="repo" --
# Story 6.3 builds the scope-selection mechanism without registering a
# "runtime" entry; Story 6.5's dashboard_drift is the first one. "repo" means
# "declares itself CI-safe," not "never reads host state": Story 6.4's
# STORY_STATUS is scope="repo" (matching its own script's DETECTOR
# declaration) despite reading `~/.bmad-loops` -- see its own row's comment
# below for why that classification is preserved rather than corrected here.
REGISTRY: tuple[SourceRegistration, ...] = (
    SourceRegistration(
        source=Source.WARDEN_DOCTOR,
        scope="repo",
        subject_station="warden",
        owning_station="doctor",
    ),  # relays warden's own self-report -- AD-11's existing exception
    SourceRegistration(
        source=Source.STALENESS_REPORT,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.CVE_WATCHER,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.BEHIND_UPSTREAM,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.FEEDSTOCK_HEALTH,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.RELEASE_CADENCE,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.ENV_HYGIENE,
        scope="repo",
        subject_station="doctor",
        owning_station="doctor",
    ),  # Doctor's own repo-wide scan -- no other station's artifact judged
    SourceRegistration(
        source=Source.MARSHAL_DURABILITY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.ADOPTION,
        scope="repo",
        subject_station="atlas",
        owning_station="doctor",
    ),
    SourceRegistration(
        source=Source.LEDGER_REGRESSION,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.4 -- ported from scripts/ledger_regression_check.py
    SourceRegistration(
        source=Source.LEDGER_DIRECTION,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 15.2 (marshal) -- ledger-vs-git drift with direction
    SourceRegistration(
        source=Source.STORY_STATUS,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.4 -- ported from scripts/story_status_check.py; scope stays
    # "repo" per the original script's own DETECTOR declaration even though
    # gather_story_status reads the published plane FIRST (marshal Story 33.12
    # re-pointed sources/marshal.py _harness_tasks/gather_story_status) and
    # falls back to ~/.bmad-loops only when the plane is unreachable -- the
    # CAP-17 retirement is landed, not merely scheduled.
    SourceRegistration(
        source=Source.CHAIN_COMPLETENESS,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.5 -- ported from scripts/chain_completeness_check.py
    SourceRegistration(
        source=Source.DASHBOARD_DRIFT,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.5 originally runtime (Tier-3 feeds). Steward 30.2 / FR-7:
    # reintroduction gate over tracked files only — scope is repo so CI sees it.
    SourceRegistration(
        source=Source.CHECK_LAYOUT,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.5 -- ported from docs/dashboard/check_layout.py; scope stays
    # "repo" per that script's own declaration -- preserve, don't redesign --
    # even though gather_check_layout binds a loopback socket and launches
    # chromium, which is not what this field's "runs anywhere" gloss implies.
    # Nothing dispatches it yet; the choice has to be revisited when Story 6.9
    # wires it, because `doctor check` reads scope_for() live and holds a 5s
    # NFR-4 budget a browser sweep cannot meet (recorded in deferred-work.md).
    SourceRegistration(
        source=Source.DREAM_CHAIN,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.6 -- ported from scripts/dream_chain_check.py
    SourceRegistration(
        source=Source.SPEC_SURFACE,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.6 -- ported from scripts/spec_surface_check.py
    SourceRegistration(
        source=Source.DEFERRED_WORK,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.6 -- ported from scripts/deferred_work_check.py; scope stays
    # "repo" per that script's own DETECTOR declaration even though it reads
    # each project's gitignored Tier-3 implementation-artifacts/deferred-work.md
    # -- preserve, don't redesign (mirrors Story 6.4's STORY_STATUS row above).
    SourceRegistration(
        source=Source.FORWARD_DEPENDENCY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.7 -- ported from scripts/forward_dependency_check.py; scope
    # stays "repo" per that script's own DETECTOR declaration. Unlike every
    # sibling row, this port CHANGED the module's dependencies rather than
    # merely relocating it: the script imported
    # bmad_loop.sprintstatus.ACTIONABLE_STATUSES, which sources/deps.py
    # restates instead (AD-13). That is what makes this row's
    # subject_station="marshal" honest -- the source now judges Marshal's
    # artifacts while depending on nothing Marshal ships, which is the
    # property S-6.10's meta-test will assert for every source.
    SourceRegistration(
        source=Source.BMAD_DRIFT,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 6.8 -- ported from scripts/bmad_drift_check.py, the tenth and
    # last of Epic 6's Charter §6 sweep; scope stays "repo" per that script's
    # own DETECTOR declaration.
    SourceRegistration(
        source=Source.BMAD_OUTPUT_HYGIENE,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 9.2 (CAP-8) -- sources/hygiene.py. subject_station="fleet",
    # not a single station: this sweep's real subject is every station's own
    # planning artifacts at once (doctor included, self-judging alongside the
    # rest), so naming any one station would misrepresent what it judges.
    # CHAIN_COMPLETENESS's subject_station="marshal" precedent (it too walks
    # all 8 projects) does NOT apply here -- what THAT source judges (the
    # Guildhall board's truthfulness) really is Marshal-owned, but no single
    # station owns "every station's own hygiene." Each Finding's own
    # evidence["station"] still carries the real station a given instance was
    # found in -- no per-finding traceability is lost.
    SourceRegistration(
        source=Source.DUE_FOR_VERIFICATION,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 11.1 (Epic 11/CAP-1) -- batches tracked deferred-work-ledger
    # entries due for re-verification, per project; judges a Marshal-produced
    # artifact (the tracked ledger), same subject_station rationale as
    # DEFERRED_WORK above. Unlike every prior row, this source has no
    # retiring `scripts/*_check.py` origin -- the first genuinely NEW
    # (non-ported) REGISTRY member.
    SourceRegistration(
        source=Source.BMAD_METHOD_VERSION_DRIFT,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 10.1 (Epic 10/CAP-1) -- compares the installed BMAD-METHOD
    # framework version against pixi.toml's own declared floor; mirrors
    # BMAD_DRIFT/DREAM_CHAIN/SPEC_SURFACE/FORWARD_DEPENDENCY's own "factory
    # apparatus" precedent -- Marshal owns the repo's tooling-installation
    # surface even though applying a fix is steward's territory. Story 10.2
    # (Epic 10/CAP-2) extends the same bmad_method.py gather() to also
    # compare that installed version against the latest release actually
    # published upstream (npm), still this one Source -- CAP-2 issues one
    # live, unauthenticated npm-registry GET (fails open, never raises),
    # which is not what this field's "runs anywhere" gloss implies either,
    # same tension CHECK_LAYOUT's own comment above already names for its
    # loopback-socket/chromium case. Story 10.3 dispatches this Source two
    # ways: `doctor check --bmad-core` (an opt-in-only category in
    # `__main__.py`, deliberately excluded from the default run because of
    # the NFR-4 5s budget tension named above) and
    # `scripts/fleet_picture.py`'s ATTENTION block (a subprocess probe
    # naming any `warn` finding under `watch`) -- never `doctor monitor`
    # (see that story's own Boundaries for why). Story 14.1 (Epic 14/CAP-4)
    # extends the same gather() once more with an entirely-fail-open suite
    # pass -- every pixi.toml `bmad-*` pin (derived, core excluded)
    # compared against its latest npm release
    # (check="bmad-suite-upstream-drift"), installed versions read from
    # gitignored `.pixi/envs/*/conda-meta/` filenames (runtime state,
    # legitimately absent on a fresh clone/CI, hence fail-open rather than
    # CAP-1/2's raise-then-degrade) -- still this one Source, still
    # WARN-or-OK only, riding the same two Story 10.3 dispatch surfaces
    # with zero wiring changes. Story 15.1 (Epic 15/DW-14-1-1) extends the
    # same gather() once more: when the npm fetch misses for a suite
    # package, a GitHub releases/tags fallback (keyed by that package's
    # own `recipes/<name>/recipe.yaml` github mapping, never a hardcoded
    # name->repo table) is tried before giving up on it -- still this one
    # Source, still WARN-or-OK only, zero wiring changes here either.
    # Story 15.2 (Epic 15/spec-15-2) extends the same gather() once more
    # with two ambient checks against the SelfExplainML anaconda.org
    # channel and each package's own tracked recipe.yaml version:
    # `bmad-channel-drift` (channel behind the recipe's declared version)
    # and `bmad-recipe-upstream-drift` (recipe behind the already-resolved
    # upstream latest) -- still this one Source, still warn-only, zero
    # wiring changes here either. Story 19.1 (Epic 19) extends the same
    # gather() once more: manifest-driven watched set (union with pixi
    # pins) and registry-aware ``_resolve_upstream_latest`` per member --
    # still this one Source, still warn-only, zero wiring changes here.
    SourceRegistration(
        source=Source.BACKLOG_INTAKE,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 13.1 (Epic 13/CAP-1) -- sources/backlog_intake.py. Judges a
    # Marshal-produced artifact (every station's tracked deferred-work-
    # ledger.md), same subject_station rationale as DEFERRED_WORK/
    # DUE_FOR_VERIFICATION above. Wired as its own `doctor backlog-intake
    # <identifier>` CLI verb, not a scope="repo" whole-sweep dispatch entry
    # -- it takes a caller-supplied identifier, which is why it stays out
    # of sources/__main__.py's DISPATCH (every member there is
    # Callable[[Path], tuple[Finding, ...]], with no room for one).
    SourceRegistration(
        source=Source.SIBLING_DREAMS_DRIFT,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 16.1 (Epic 16 / CAP-1) -- sources/sibling_dreams.py. Diffs
    # shared Dream titles vs the named sibling tree; warn-only; fleet
    # subject (both local docs/dreams and the sibling). Opt-in via
    # `doctor check --sibling-dreams` + fleet-picture ATTENTION probe.
    SourceRegistration(
        source=Source.DREAMS_HYGIENE,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 17.2 (Epic 17 / FR-147) -- chain.gather_dreams_hygiene.
    # Dream-tier hygiene (frontmatter vocab/owner/title, README table sync,
    # realization-log presence), distinct from DREAM_CHAIN INV-0..3. Not a
    # DISPATCH name: invoked as `dream-chain --dreams` (CLI spelling chosen
    # over folding into `--inv`).
    SourceRegistration(
        source=Source.CHAIN_LAYERS_AUDIT,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    ),  # Story 17.3 (Epic 17 / FR-150 residual, FR-152) + Story 21.1 (CAP-3) --
    # board.gather_chain_layers_audit. CAP-3 pass/fail per checkpoint for one
    # named project, seeded from pyforge.doctor.sources.fleet_scan + dream-chain.
    # Not a DISPATCH name: invoked as `chain-completeness --layers --project <slug>`.
    SourceRegistration(
        source=Source.PLATFORM_POLICY_SUITE,
        scope="repo",
        subject_station="steward",
        owning_station="doctor",
    ),  # Retro action item 3 (retro-pyforge-steward-2026-09-04.md, 2026-09-05)
    # -- sources/platform_policy.py. Judges src/platform's manifest-only
    # tests/policy subset (spec-python-agent-platform's surface, steward-
    # owned); shells out to the platform-ci-test env's own interpreter
    # (AD-5, cli_bridge.run_pytest), WARN when that env is not installed,
    # FAIL only on an actual policy-suite failure. A DISPATCH member
    # (Callable[[Path], tuple[Finding, ...]]), unlike BACKLOG_INTAKE/
    # DREAMS_HYGIENE/CHAIN_LAYERS_AUDIT above.
    SourceRegistration(
        source=Source.BMAD_RENDER_CONFIG_AMBIGUITY,
        scope="repo",
        subject_station="steward",
        owning_station="doctor",
    ),  # Story 20.2 -- sources/bmad_config.py. subject_station="steward":
    # `_bmad/custom/config*.toml` customizations are steward's territory
    # (spec-bmad-method-core-upgrade's own customization-inventory.md C2
    # row, "steward | Sanctioned custom layer"). A DISPATCH member
    # (Callable[[Path], tuple[Finding, ...]]), same shape as
    # PLATFORM_POLICY_SUITE above.
    SourceRegistration(
        source=Source.FROZEN_PATH_CHANGED,
        scope="repo",
        subject_station="steward",
        owning_station="doctor",
    ),  # Story 20.3 -- sources/frozen_path.py. subject_station="steward":
    # steward owns the cutover plan / capability ledger (AD-22's own
    # "steward cutover plan --append" ownership). A DISPATCH member
    # (Callable[[Path], tuple[Finding, ...]]), same shape as
    # BMAD_RENDER_CONFIG_AMBIGUITY/PLATFORM_POLICY_SUITE above -- unlike
    # both of those, this one CAN report FAIL (see models.Source's own
    # comment for why).
    SourceRegistration(
        source=Source.CAPABILITY_EFFECT,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 21.10 -- sources/capability_effect.py. Reads every station's
    # SPEC.md CAP ``verified:`` lines (CAP-2); caller reach (CAP-1) lands in
    # Story 21.9; ``detectors`` / ``__main__`` dispatch wiring in 21.11.
    SourceRegistration(
        source=Source.STATUS_BODY_CONSISTENCY,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 21.12 -- sources/status_body_consistency.py. CAP-1
    # progress-phrase pass; CAP-2..4 land in 21.13–21.15; ``detectors`` /
    # ``__main__`` dispatch wiring in 21.16.
    SourceRegistration(
        source=Source.PIXI_CURRENCY_LEDGER,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 21.7 -- sources/pixi_currency.py. CAP-4 advisory ledger
    # staleness vs ``pixi.toml`` commit history; WARN-only; fleet subject
    # (repo-wide ``pixi.toml`` surface, same rationale as SIBLING_DREAMS_DRIFT).
    SourceRegistration(
        source=Source.GENERAL_DOCS_CONSISTENCY,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 22.3 -- sources/general_docs_consistency.py. Human-facing
    # documentation identity (README vs skill-brief, AGENTS.md vs Dream);
    # WARN-only; fleet subject (general docs layer, not one station).
    SourceRegistration(
        source=Source.CAPABILITY_LEDGER,
        scope="repo",
        subject_station="steward",
        owning_station="doctor",
    ),  # Story 55.2 -- sources/capability_ledger.py. subject_station=
    # "steward": A authors the tracked capability ledger; doctor judges it.
    # A DISPATCH member; CAN FAIL (unclassified / undated A-only).
    SourceRegistration(
        source=Source.DOCS_SHELF_OCCUPANCY,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 23.7 -- sources/docs_shelf.py. Leftover-shelf path occupancy
    # vs the docs/MAP.md allow-list (`_bmad-output/` root, air-gap cluster);
    # fleet subject (the general docs layer, same rationale as
    # GENERAL_DOCS_CONSISTENCY/PIXI_CURRENCY_LEDGER above), never FAIL.
    SourceRegistration(
        source=Source.CHAIN_SPRAWL,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 25.1 -- sources/one_chain.py. Dream-append-first enforced:
    # new Dream file / Spec folder vs docs/governance/chain-sprawl-baseline.json
    # (dated snapshot, only ever pruned); exemption list read from
    # guild-roster.json `fold_exemptions`. Fleet subject: it grades every
    # station's planning tree. CAN FAIL.
    SourceRegistration(
        source=Source.FR_WITHOUT_CAP,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 25.2 -- sources/one_chain.py. A PRD FR minted after the rule
    # date cites a CAP that an open Spec under its station declares;
    # docs/governance/fr-baseline.json is the pre-rule population. CAN FAIL.
    SourceRegistration(
        source=Source.DOCS_MAP_HYGIENE,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 30.1 (spec-pyforge-doctor CAP-83) -- sources/docs_map_hygiene.py.
    # docs/MAP.md vs the four Diátaxis quadrants (docs/tutorials, how-to,
    # reference, explanation) only. A MAP link to a missing page under docs/
    # is FAIL; an unmapped quadrant page is WARN (warn-first). CAN FAIL.
    SourceRegistration(
        source=Source.LIVE_PROOF_SURFACE,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 26.1 (spec-pyforge-doctor CAP-77) -- sources/live_proof_surfaces.py.
    # A touched surface catalogued in live-proof-surfaces.md (herald, scribe,
    # atlas, warden, guild-cross-station) gets an advisory finding naming it;
    # fleet subject (the catalog spans multiple stations, same rationale as
    # GENERAL_DOCS_CONSISTENCY/DOCS_SHELF_OCCUPANCY above). Never FAIL.
    SourceRegistration(
        source=Source.DOCS_CURRENCY,
        scope="repo",
        subject_station="fleet",
        owning_station="doctor",
    ),  # Story 30.2 (spec-pyforge-doctor CAP-84) -- sources/docs_currency.py.
    # map-render / authored-page-stale / skill-dir-hygiene, beside
    # DOCS_MAP_HYGIENE above; fleet subject (the general docs layer, same
    # rationale as GENERAL_DOCS_CONSISTENCY/DOCS_SHELF_OCCUPANCY). Never FAIL.
)


def list_sources() -> tuple[SourceRegistration, ...]:
    """Return the full registered ``REGISTRY``.

    The one place both the detector-ownership audit and
    ``scripts/detectors.py``'s ``_doctor_sources()`` read from.
    """
    return REGISTRY


def scope_for(source: Source) -> str:
    """Return ``source``'s registered scope (``"repo"`` or ``"runtime"``).

    The one canonical per-source scope lookup — Story 6.3's ``doctor check
    --scope`` filter reads through THIS function rather than a second
    hand-rolled loop over ``REGISTRY``, so a future ``SourceRegistration``'s
    scope change (e.g. a source moving from ``"repo"`` to ``"runtime"``)
    cannot silently desync a duplicated call site.

    Raises ``ValueError`` if ``source`` has no ``REGISTRY`` entry — this
    module's own exhaustiveness test
    (``test_every_source_member_has_exactly_one_registry_entry``) already
    guarantees every current ``Source`` member resolves; a ``source`` that
    reaches this branch is a bug in ``REGISTRY``, not a value worth
    defaulting past.
    """
    for registration in REGISTRY:
        if registration.source is source:
            return registration.scope
    raise ValueError(f"{source!r} has no REGISTRY entry")


def degrade_on_exception(
    source: Source,
    check: str,
    gather: Callable[[], tuple[Finding, ...]],
) -> tuple[Finding, ...]:
    """Run ``gather()``; convert any raised ``Exception`` into exactly one
    WARN ``Finding`` naming it, rather than letting it propagate.

    This is the reusable "cannot evaluate here" path a ``scope="runtime"``
    source needs (Story 6.5+'s ``dashboard_drift`` and whatever follows it):
    unlike ``sources/warden.py``, ``sources/marshal.py``, and
    ``checks/env_hygiene.py`` — whose own ``gather`` functions already
    document and enforce their own "degrades, never crashes" contract (see
    ``sources/marshal.py``'s module docstring) — a source whose inputs are
    host state (tmux, ``~/.bmad-loops``) that is simply ABSENT outside an
    operator's own machine has no such contract to lean on yet. This helper
    is that contract, generalized, for a caller that wraps its own raw
    host-state read with it.

    Deliberately NOT wired into today's three existing (repo-scope)
    dispatch calls in ``__main__.py`` — an exception escaping one of THOSE
    today would be a real bug in a module that already promises never to
    raise, and must keep propagating to ``main()``'s own top-level
    exception net (exit 2), never get silently reclassified as WARN (see
    the story spec's Design Notes).

    Catches ``Exception``, never ``BaseException`` — a ``KeyboardInterrupt``
    or ``SystemExit`` raised inside ``gather`` must still propagate
    untouched, mirroring ``main()``'s own three-tier handler ordering.
    """
    try:
        return gather()
    except Exception as exc:  # noqa: BLE001 -- this IS the degrade
        # boundary this function exists to provide, not a suppressed bug.
        return (
            Finding(
                source=source,
                check=check,
                status=DoctorStatus.WARN,
                message=(
                    f"{check} could not be evaluated here — "
                    f"{exc.__class__.__name__}: {exc}"
                ),
                evidence={"exception": exc.__class__.__name__},
            ),
        )
