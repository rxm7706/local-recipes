"""Canonical enums + report/finding types — the frozen contract (Story 1.1).

Doctor's own closed taxonomy (architecture spine AD-3): structurally mirrors
``pyforge.warden``'s ``StrEnum`` + frozen-dataclass ``__post_init__``
coercion idiom, but THIS MODULE never imports from ``pyforge.warden`` — its
``Finding``/``Source``/``DoctorStatus`` taxonomy is deliberately independent.
Importing warden's ``ErrorKind`` would silently stretch a vocabulary scoped
to *scan-engine operational failure* over Doctor's broader domain
(engine-missing / feedstock-stale / credential-hygiene), making it a shared,
driftable vocabulary neither package fully owns. The rule is scoped, not an
absolute package-wide ban: ``doctor.sources.warden`` (Story 1.2, AD-1) is
the one sanctioned exception, importing only
``pyforge.warden.engines.run_doctor_checks`` as a library call and
normalizing its output into this module's own ``Finding`` shape — it never
imports ``ErrorKind`` or any other warden vocabulary into this taxonomy.

``DoctorReport`` is the one JSON envelope per invocation (Consistency
Conventions): ``{schema_version, verb, generated_at, findings,
prescriptions}`` — ``prescriptions`` present (a list, possibly empty) only
when ``verb == "diagnose"``; for ``check``/``monitor`` it stays ``None`` in
the Python model AND is omitted (never ``null``) from the serialized JSON.

This module is pure data: no I/O, no subprocess, no network, no clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# The verbs the CLI dispatches. Originally the three Epic 1-3 verbs this
# story froze the envelope's verb/prescriptions coherence rule for; Story
# 13.1 (Epic 13/CAP-1) added "backlog-intake" -- a fourth verb that, like
# "check"/"monitor", never carries prescriptions (only "diagnose" does).
_VALID_VERBS = frozenset({"check", "monitor", "diagnose", "backlog-intake"})


class DoctorStatus(StrEnum):
    """Per-Finding health tri-state (closed)."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


class Source(StrEnum):
    """The wrapped instruments (closed) — one member per gather filter the
    architecture spine names (AD-1 warden-doctor; AD-6 the five atlas Watch
    axes; AD-3/FR-3 env-hygiene; AD-9/FR-12 adoption, Story 4.3 — the closed
    taxonomy EXTENDED, never opened).

    Each member's scope, subject station, and owning station are declared in
    ``doctor.sources.REGISTRY`` (Story 6.2)."""

    WARDEN_DOCTOR = "warden-doctor"
    STALENESS_REPORT = "staleness-report"
    CVE_WATCHER = "cve-watcher"
    BEHIND_UPSTREAM = "behind-upstream"
    FEEDSTOCK_HEALTH = "feedstock-health"
    RELEASE_CADENCE = "release-cadence"
    ENV_HYGIENE = "env-hygiene"
    # Charter §6 (2026-07-28): the Doctor holds the verdict on the Marshal's own
    # conformance -- "the one station that would otherwise grade itself". Added
    # 2026-08-08 after a sync destroyed 96 `done` markers across four stations and
    # all three guards written in response lived in Marshal's own surface.
    MARSHAL_DURABILITY = "marshal-durability"
    ADOPTION = "adoption"
    # Story 6.4 (FR-15): the closed taxonomy EXTENDED again -- Doctor's
    # verdict on the tracked sprint ledger's own regression-freedom (ported
    # from scripts/ledger_regression_check.py) and on the Tier-3 sprint-status
    # feed's false-green stories (ported from scripts/story_status_check.py).
    # Both judge a Marshal-produced artifact; see sources/ledger.py and
    # sources/marshal.py's gather_story_status for the independence rationale.
    LEDGER_REGRESSION = "ledger-regression"
    STORY_STATUS = "story-status"
    # Story 15.2 (marshal FR-137/FR-138): standalone ledger-vs-git drift with
    # DIRECTION — landed-but-unpromoted (merged in git, not done in the
    # tracked twin) and the converse. Reads merge history + tracked ledgers
    # only; never the Tier-3 feed. See sources/ledger.py::gather_direction.
    LEDGER_DIRECTION = "ledger-direction"
    # Story 6.5 (FR-15): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on the fleet-status board's own truthfulness: every open Spec a
    # station owns is decomposed and its epics/ledger/board agree (ported from
    # scripts/chain_completeness_check.py), the committed data.js and tracked
    # ledger twins have not drifted from their feeds (ported from
    # scripts/dashboard_drift_check.py), and the console bar's status chips
    # actually render without overlapping or clipping (ported from
    # docs/dashboard/check_layout.py). All three judge a Marshal-produced
    # artifact (the Guildhall console + its data feeds); see sources/board.py
    # for the independence rationale.
    CHAIN_COMPLETENESS = "chain-completeness"
    DASHBOARD_DRIFT = "dashboard-drift"
    CHECK_LAYOUT = "check-layout"
    # Story 6.6 (FR-15): the closed taxonomy EXTENDED a further time -- Doctor's
    # verdict on the Dream-to-Code chain itself: every Spec links a Dream and
    # every Dream has a Spec in its owner's project, using the 6.10 sharded
    # planning tree (ported from scripts/dream_chain_check.py); every tracked
    # file is governed by a spec surface or an allowlist entry, and a governed
    # file's content has not drifted out from under its spec's contract
    # (ported from scripts/spec_surface_check.py); no deferred-work entry lives
    # only in gitignored Tier-3 scratch (ported from
    # scripts/deferred_work_check.py). All three judge Marshal-governed factory
    # apparatus; see sources/chain.py for the independence rationale.
    DREAM_CHAIN = "dream-chain"
    SPEC_SURFACE = "spec-surface"
    DEFERRED_WORK = "deferred-work"
    # Story 6.7 (FR-15): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on the one defect bmad-loop's own picker is blind to: a story
    # whose documented **Deps:** names a story in a LATER epic, which the
    # engine's strict within-epic file-order scan cannot see (ported from
    # scripts/forward_dependency_check.py). Judges a Marshal-produced artifact
    # (each station's epics doc + tracked ledger); see sources/deps.py for the
    # independence rationale and AD-13 for why it restates the harness's
    # ACTIONABLE_STATUSES rather than importing it.
    FORWARD_DEPENDENCY = "forward-dependency"
    # Story 6.8 (FR-15): the closed taxonomy EXTENDED a final time -- Doctor's
    # verdict on the pyforge-marshal project docs' own currency: a tracked
    # doc's missing/behind source_pin, misfiled archive artifacts and stray
    # files, stale spec status, a stale deferred-work reconciliation stamp,
    # stale counts/atlas-phase lists, stale rule content, sync-baseline
    # drift, project coverage completeness, Tier-1/Tier-3 filing alignment,
    # unindexed intake specs, and Dream vocabulary/ownership drift (ported
    # from scripts/bmad_drift_check.py, the tenth and last of Epic 6's
    # Charter §6 sweep). Judges a Marshal-produced artifact; see
    # sources/factory.py for the independence rationale.
    BMAD_DRIFT = "bmad-drift"
    # Story 9.2 (CAP-8): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on the fleet's OWN planning-artifact hygiene: Story 9.1's five
    # pure predicates (dead test scaffolding, a hollow Tier-3 sprint-status,
    # an orphan planning-artifact, a README still carrying its unfilled
    # template stub, a Dream's status lagging its station's own completed
    # work) given production evidence by sources/hygiene.py, which walks all
    # 8 stations' own conventional planning-artifact locations in one sweep
    # (not every file a station may hold) -- see that module and
    # sources/__init__.py's own row for why subject_station="fleet" (a new
    # value, not a single station) is correct here.
    BMAD_OUTPUT_HYGIENE = "bmad-output-hygiene"
    # Story 11.1 (Epic 11/CAP-1): the closed taxonomy EXTENDED once more --
    # Doctor's per-project batch of tracked deferred-work-ledger entries due
    # for re-verification: an entry with no `verified:` line at all, or one
    # whose `verified:` date is older than a staleness threshold
    # (sources/chain.py's DUE_FOR_VERIFICATION_STALENESS_DAYS). Unlike every
    # member above, this one never gates (always WARN, never FAIL) -- it
    # informs which of the ~400+ fleet-wide entries have never been
    # re-checked, or were re-checked too long ago. Judges a Marshal-produced
    # artifact (the tracked ledger); see sources/chain.py for the
    # independence rationale.
    DUE_FOR_VERIFICATION = "due-for-verification"
    # Story 10.1 (Epic 10/CAP-1): the closed taxonomy EXTENDED once more --
    # Doctor's verdict on whether the INSTALLED BMAD-METHOD framework version
    # (`_bmad/_config/manifest.yaml`'s `installation.version`) meets
    # `pixi.toml`'s own declared `bmad-method` floor. Distinct from the
    # existing BMAD_DRIFT above: that member judges `pyforge-marshal`'s own
    # project-doc currency (skill version, schema version, MCP tool counts,
    # ...), a wholly different artifact class -- this one judges the
    # installed framework tool itself. Like DUE_FOR_VERIFICATION, this
    # informs rather than gates (always WARN or OK, never FAIL). Judges a
    # Marshal-produced artifact (the factory's own tooling-installation
    # surface); see sources/bmad_method.py for the independence rationale.
    # Story 10.2 (Epic 10/CAP-2) extends the SAME member's gather() with a
    # second, independent comparison -- installed vs. the latest release
    # actually published upstream on npm, not just against the declared
    # floor -- rather than adding a new member (review finding, Story 10.2:
    # keep this comment in sync whenever gather()'s own scope grows). Story
    # 10.3 (Epic 10/CAP-3) wires this Source into `doctor check --bmad-core`
    # (opt-in only, never the default run) and `scripts/fleet_picture.py`'s
    # ATTENTION block, closing the "undetected until an operator happened to
    # ask" gap the standalone pixi task left open. Story 14.1 (Epic 14/CAP-4)
    # extends the SAME member's gather() once more with a suite pass: every
    # `bmad-*` dependency key pixi.toml pins (DERIVED at gather time, never
    # a hardcoded list; the core itself excluded -- that is CAP-1/CAP-2's
    # own territory) is compared against its latest npm release
    # (check="bmad-suite-upstream-drift"), reading installed versions from
    # gitignored `.pixi/envs/*/conda-meta/` filenames -- entirely fail-open
    # (that state is legitimately absent on a fresh clone/CI), still
    # warn-only, still this one Source, riding Story 10.3's existing
    # surfaces unchanged. Story 15.1 (Epic 15/DW-14-1-1) extends the suite
    # pass once more: when the npm fetch misses for a suite package, a
    # GitHub releases/tags fallback (keyed by that package's own
    # `recipes/<name>/recipe.yaml` github mapping) is tried before giving
    # up on it -- still this one Source, still warn-only, riding the same
    # surfaces. Story 15.2 (Epic 15, spec-15-2) extends the SAME member's
    # gather() once more with two ambient checks against the SelfExplainML
    # anaconda.org channel and each package's own tracked recipe.yaml
    # version: `bmad-channel-drift` (channel behind the recipe's declared
    # version) and `bmad-recipe-upstream-drift` (recipe behind the
    # already-resolved upstream latest) -- still this one Source, still
    # WARN-only, riding the same surfaces. Story 19.1 (Epic 19) extends the
    # suite pass once more: the watched set UNIONS steward's tracked
    # ``recipes/bmad-suite/suite-members.yaml`` with pixi ``bmad-*`` pins
    # (``mybmad-dashboard`` included), and upstream resolution follows each
    # member's ``cfe-upstream-registry`` via ``_resolve_upstream_latest`` --
    # still this one Source, still warn-only, riding the same surfaces.
    BMAD_METHOD_VERSION_DRIFT = "bmad-method-version-drift"
    # Story 13.1 (Epic 13/CAP-1): the closed taxonomy EXTENDED once more --
    # Doctor's verdict on which tracked deferred-work-ledger entries, fleet
    # wide, precisely name a given epic or story -- surfaced at
    # story-drafting time so a human does not have to grep the ledger by
    # hand (the motivating incident: DW-CHAIN-COMPLETENESS-1, a bare
    # substring test over concatenated prose that reported false-clean
    # while missing most of what it claimed to check). Unlike every member
    # above, this one takes a caller-supplied identifier rather than
    # judging a fixed artifact wholesale -- it is a query, not a sweep --
    # so it is wired as its own `doctor backlog-intake <id>` CLI verb,
    # never a `sources/__main__.py` DISPATCH entry (whose members are all
    # `Callable[[Path], tuple[Finding, ...]]`, with no room for the
    # identifier). Always WARN (a match) or OK (no match), never FAIL --
    # informs, never gates, mirroring DUE_FOR_VERIFICATION's own
    # discipline. Judges a Marshal-produced artifact (the tracked ledger);
    # see sources/backlog_intake.py for the independence rationale.
    BACKLOG_INTAKE = "backlog-intake"
    # Story 16.1 (Epic 16 / spec-sibling-dreams-drift CAP-1): warn-only
    # ambient check that shared Dream titles diverge between this tree and
    # the named sibling (OpenTeams mgmt-wf) on status/owner/content-hash.
    # Fleet subject; never FAIL; fail-open without token / when unreachable.
    SIBLING_DREAMS_DRIFT = "sibling-dreams-drift"
    # Story 17.2 (Epic 17 / FR-147): Dream-tier hygiene mode on the
    # dream-chain surface — frontmatter validity (status vocab, owner in
    # station/`guild`, title present), README table sync, realization-log
    # presence. Distinct from DREAM_CHAIN's INV-0..3. Invoked as
    # `python -m pyforge.doctor.sources dream-chain --dreams` (CLI spelling
    # chosen over folding into `--inv`). Warn-only; never mutates Dreams.
    DREAMS_HYGIENE = "dreams-hygiene"
    # Story 17.3 (Epic 17 / FR-150 residual + FR-152): read-only chain-layer
    # presence report for ONE named project, seeded from
    # pyforge.doctor.sources.fleet_scan's FLEET_STAGES/_stage_globs/_resolve.
    # Distinct from CHAIN_COMPLETENESS INV-A..D and from DREAMS_HYGIENE.
    # Invoked as `chain-completeness --layers --project <slug>`. Warn-only.
    CHAIN_LAYERS_AUDIT = "chain-layers-audit"
    # Retro action item 3 (retro-pyforge-steward-2026-09-04.md, 2026-09-05):
    # a `pixi.toml` IDE-metadata commit (098f0f0672) silently dropped the
    # `cachebox <6` / `openfeature-provider-flagd <0.5.1` ceilings
    # `src/platform/tests/policy` guards, unnoticed because Platform CI --
    # the only workflow that ran that suite -- was disabled at the time.
    # Judges `src/platform`'s manifest-only policy suite (the
    # `not django_db`-marked subset; no live database needed) so this class
    # of regression is caught even when Platform CI itself is disabled or
    # never triggered. Subject is steward (spec-python-agent-platform owns
    # `src/platform`); WARN when the `platform-ci-test` pixi env this needs
    # is not installed here (never a silent skip, never a confident FAIL
    # for an absence that is not the repo's fault), FAIL only on an actual
    # policy-suite failure. See sources/platform_policy.py.
    PLATFORM_POLICY_SUITE = "platform-policy-suite"
    # Story 20.2 (Epic 20): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on whether `_bmad/scripts/render_skill.py`'s own central-config
    # merge (`load_central_config()`'s four `_bmad/config*.toml` /
    # `_bmad/custom/config*.toml` layers) contains an AMBIGUOUS bare key --
    # the same key name occurring at two different dotted paths, which HALTs
    # every rendering skill (bmad-build, bmad-build-auto, ...) with
    # `RenderError: ambiguous config value` the moment a `{{.key}}` short
    # token tries to resolve it (live 2026-09-06: `[core] user_skill_level`
    # colliding with a regenerated `[modules.bmm] user_skill_level`, fixed by
    # commit `99e595cc6a`). This source independently REPRODUCES the
    # renderer's own merge and scan logic (never imports
    # `_bmad/scripts/config_utils.py`/`render_skill.py` -- Boundaries), one
    # WARN per ambiguous key naming it and every colliding path, one OK
    # naming the checked-key count when none collide. Never gates (`ok`/
    # `warn` only, mirroring BMAD_METHOD_VERSION_DRIFT's own always-informs
    # discipline). subject_station="steward" (sources/__init__.py's own
    # REGISTRY entry): the scanned config spans an installer-managed base
    # layer (`_bmad/config*.toml`, regenerated wholesale on every install,
    # never hand-edited) and a steward-owned custom layer
    # (`_bmad/custom/config*.toml`) -- a human can only ever resolve a
    # collision by moving the CUSTOM-layer pin, since the base layer isn't a
    # hand-edit surface at all. Mirrors spec-bmad-method-core-upgrade's own
    # `customization-inventory.md` C2 row ("steward | Sanctioned custom
    # layer") and its remediation record for the live 2026-09-06 incident
    # this source detects, which fixed the collision by moving
    # `_bmad/custom/config.toml`'s own pins (commit `99e595cc6a`), not the
    # installer-managed base file. See sources/bmad_config.py for the
    # independence rationale.
    BMAD_RENDER_CONFIG_AMBIGUITY = "bmad-render-config-ambiguity"
    # Story 20.3 (Epic 20): the closed taxonomy EXTENDED once more -- Doctor's
    # verdict on whether a capability currently `rebuilding`/`moving` in the
    # tracked capability ledger (`docs/foundry/manifest.{yaml,yml,json}`, an
    # `[ASSUMPTION: schema]` synthesis -- no ledger exists at all until the
    # real python-foundry cutover begins) had one of its own frozen source
    # paths touched by `origin/main..HEAD` anyway (AD-22's own freeze rule;
    # `cutover-readiness.md` G11: "never built" before this story). Unlike
    # BMAD_RENDER_CONFIG_AMBIGUITY/BMAD_METHOD_VERSION_DRIFT above, this
    # member CAN FAIL -- the story's own AC is explicit ("a change under a
    # frozen path is a fail naming the capability and the path"), a
    # deliberate departure from Epic 20's general "warn at most" framing,
    # governed by this specific AC (mirrors LEDGER_REGRESSION/SPEC_SURFACE/
    # PLATFORM_POLICY_SUITE's own FAIL-capable precedent). subject_station=
    # "steward" (sources/__init__.py's own REGISTRY entry): steward owns the
    # cutover plan / capability ledger (AD-22's own "steward cutover plan
    # --append" ownership). See sources/frozen_path.py for the independence
    # rationale.
    FROZEN_PATH_CHANGED = "frozen-path-changed"
    # Story 21.10 (Epic 21 / spec-capability-effect-check CAP-2): read-only
    # realized-versus-verified column from each CAP's optional ``verified:``
    # line in ``SPEC.md``; WARN when a ``shipped``/``realized`` Spec's CAP
    # carries none. Story 21.9 (CAP-1 caller reach) and Story 21.11
    # (detectors / fleet-picture wiring) extend the same module and member.
    CAPABILITY_EFFECT = "capability-effect"
    # Story 21.12 (Epic 21 / spec-status-body-consistency CAP-1): read-only
    # verdict on whether a Dream or Spec's prose still agrees with its own
    # terminal ``status:`` — starting with incomplete progress phrases
    # (``N of M stories/capabilities`` with ``N < M``). Stories 21.13–21.16
    # extend the same module; Story 21.16 wires dispatch + detectors.
    STATUS_BODY_CONSISTENCY = "status-body-consistency"
    # Story 21.7 (Epic 21 / spec-pixi-candidate-currency CAP-4): advisory
    # ledger-staleness check for the Dream's four dependency ledgers vs
    # ``pixi.toml`` commit history. WARN-only; never gates.
    PIXI_CURRENCY_LEDGER = "pixi-currency-ledger"
    # Story 22.3 (Epic 22 / spec-general-docs-consistency CAP-3): cross-
    # references human-facing docs (station README vs skill-brief, AGENTS.md
    # vs station Dream) for quotable identity contradictions. WARN-only,
    # fail-open — never a second PR gate.
    GENERAL_DOCS_CONSISTENCY = "general-docs-consistency"
    # Story 23.7 (Epic 23 / spec-pyforge-doctor CAP-54): compares live
    # directory occupancy at two leftover-shelf-prone locations (the
    # `_bmad-output/` root, the air-gap documentation cluster) against the
    # allow-list that docs/MAP.md's own "Outside this map" table and Story
    # 23.2's fold established. Distinct from GENERAL_DOCS_CONSISTENCY above
    # (identity contradictions, not occupancy). WARN-only, fail-open — never
    # a second PR gate. See sources/docs_shelf.py.
    DOCS_SHELF_OCCUPANCY = "docs-shelf-occupancy"
    # Story 55.2 (steward Epic 55 / spec-foundry-capability-ledger fcl:CAP-2):
    # CAP heading + intent/success extract vs docs/foundry/capability-ledger.yaml.
    # HARD on unclassified live CAP-N and A-only without expiry; post-PIN
    # unclassified paths are --append. Extract-only inventory.
    CAPABILITY_LEDGER = "capability-ledger"
    # Doctor Epic 25 (spec-one-chain-per-station, guild outcome / doctor
    # mechanism): Story 25.1 -- a Dream file or Spec folder minted after the
    # ruling SHA without a declared `fold-exemption:` is a FAIL; Story 25.2 --
    # a PRD FR minted after the rule date must cite a resolving `CAP-m`.
    CHAIN_SPRAWL = "chain-sprawl"
    FR_WITHOUT_CAP = "fr-without-cap"
    # Story 30.1 (spec-pyforge-doctor CAP-83): the closed taxonomy EXTENDED
    # once more -- docs/MAP.md vs the four Diátaxis quadrant directories
    # (docs/tutorials, docs/how-to, docs/reference, docs/explanation) it
    # governs. A MAP link to a missing page under docs/ is FAIL; a quadrant
    # page absent from MAP.md is WARN (warn-first, CAP-62 posture). Quadrant
    # README.md index pages are exempt; MAP.md § "Outside this map" layers
    # are never scanned.
    DOCS_MAP_HYGIENE = "docs-map-hygiene"
    # Story 26.1 (spec-pyforge-doctor CAP-77): the closed taxonomy EXTENDED
    # once more -- a touched surface catalogued in live-proof-surfaces.md
    # (a fleet-wide inventory of surfaces a dev/review pass structurally
    # cannot verify from inside the repo alone) gets an advisory finding
    # naming it, quoting the catalog's own "how to prove it live" cell
    # verbatim. Matches ONLY the catalog's hand-authored `Surface globs`
    # column (added 2026-09-20 after the first attempt's keyword fallback
    # produced false positives against real tracked files) -- never a
    # keyword pulled from prose. Always WARN, never FAIL (AD-2). See
    # sources/live_proof_surfaces.py for the independence rationale.
    LIVE_PROOF_SURFACE = "live-proof-surface"
    # Story 30.2 (spec-pyforge-doctor CAP-84): the closed taxonomy EXTENDED
    # once more -- three read-only checks over docs/map.yaml (the new
    # machine registry) and docs/MAP.md (its render): (a) map-render --
    # MAP.md's generated "## Page registry" section byte-matches a fresh
    # render of map.yaml; (b) authored-page-stale -- a kind: authored page's
    # own sources:/verified: frontmatter has fallen behind a named source's
    # git last-touch, or the page body cites a backticked skill/script/path
    # token that no longer resolves; (c) skill-dir-hygiene -- a stray
    # non-layout file inside a bmad-*/pyforge-*/skf-* skill directory. All
    # three WARN-only, fail-open (never FAIL; a missing/invalid docs/map.yaml
    # degrades to one WARN via degrade_on_exception). See
    # sources/docs_currency.py for the independence rationale.
    DOCS_CURRENCY = "docs-currency"


class Partition(StrEnum):
    """Where a ``Prescription`` lands (closed; Epic 3's ``diagnose``
    partition + rank pass populates this)."""

    ACTIONABLE = "actionable"
    BLOCKED = "blocked"
    ACCEPTED_RISK = "accepted-risk"


@dataclass(frozen=True)
class Finding:
    """One gathered signal, tagged with its origin ``Source``.

    ``evidence`` is a Source-specific object, opaque to this envelope (the
    architecture spine's own wording) — never validated here.
    """

    source: Source
    check: str
    status: DoctorStatus
    message: str
    evidence: dict

    def __post_init__(self) -> None:
        # Coerce so a raw string source/status either resolves to a member
        # or fails loud HERE (StrEnum equality would otherwise admit it,
        # crashing later at .value during serialization).
        object.__setattr__(self, "source", Source(self.source))
        object.__setattr__(self, "status", DoctorStatus(self.status))
        # Fail loud on a non-dict evidence (schema requires type:object) and
        # shallow-copy it -- frozen=True only blocks attribute reassignment,
        # not mutation of a referenced mutable object, so a caller holding
        # the original dict must not be able to mutate this Finding after
        # construction.
        if not isinstance(self.evidence, dict):
            raise ValueError(f"evidence must be a dict, got {self.evidence!r}")
        object.__setattr__(self, "evidence", dict(self.evidence))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "source": self.source.value,
            "check": self.check,
            "status": self.status.value,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class Prescription:
    """One ranked remediation for a ``Finding`` (``diagnose`` only, Epic 3).

    ``rank``/``rank_factors`` stay ``None``-able at scaffold stage — a later
    epic's ranking pass populates them; nothing produces a ``Prescription``
    yet in this story.

    ``safe_upgrade_target``/``safe_upgrade_reason`` (Story 4.4, FR-13, AD-10)
    are a later epic's single-hop upgrade-path recommendation: a specific
    next-safe-version string when confidently known, else ``None`` with
    ``safe_upgrade_reason`` always stating why (never a bare ``None`` with
    no explanation, mirroring ``rank``/``rank_factors``'s own always-paired
    value+explanation convention). Default to ``None`` so every existing
    construction site (Epic 3, unaware of this pair) keeps working
    unchanged.
    """

    finding_ref: str
    partition: Partition
    rank: int | None
    rank_factors: dict | None
    action: str
    root_cause: str
    safe_upgrade_target: str | None = None
    safe_upgrade_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "partition", Partition(self.partition))
        # Same defensive-copy rationale as Finding.evidence -- frozen=True
        # doesn't stop a caller from mutating a referenced mutable dict.
        if self.rank_factors is not None:
            object.__setattr__(self, "rank_factors", dict(self.rank_factors))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "finding_ref": self.finding_ref,
            "partition": self.partition.value,
            "rank": self.rank,
            "rank_factors": self.rank_factors,
            "action": self.action,
            "root_cause": self.root_cause,
            "safe_upgrade_target": self.safe_upgrade_target,
            "safe_upgrade_reason": self.safe_upgrade_reason,
        }


@dataclass(frozen=True)
class DoctorReport:
    """The frozen external report envelope (see ``data/report-schema.json``).

    ``prescriptions`` is present (a list, possibly empty) only when
    ``verb == "diagnose"``; for ``check``/``monitor`` it must stay ``None``
    in the Python model AND be omitted (never ``null``) from the serialized
    JSON — ``to_json_dict`` only adds the key when it is not ``None``.

    ``grade``/``axis_scores`` (Story 4.1, FR-10) are a later epic's optional
    composite-health-grade projection — deliberately stored here as ALREADY-
    SERIALIZED plain data (a ``str`` value and a tuple of plain dicts), not
    as ``doctor.score``'s own ``Grade``/``AxisScore`` types, so this module
    never needs to import ``doctor.score`` (that would be a reverse
    dependency onto a module that itself depends on ``models`` — AD-3 keeps
    this taxonomy module's own import surface minimal). Present only when
    the CLI layer actually computed a grade for this report (today: the
    ``diagnose`` verb only); omitted, never ``null``, otherwise — same
    presence discipline as ``prescriptions`` above, but WITHOUT that field's
    hard verb-coupling validation, since a future verb may want to carry a
    grade too without this module needing another edit.
    """

    schema_version: int
    verb: str
    generated_at: str
    findings: tuple[Finding, ...]
    prescriptions: tuple[Prescription, ...] | None = None
    grade: str | None = None
    axis_scores: tuple[dict, ...] | None = None

    def __post_init__(self) -> None:
        # report-schema.json declares schema_version's minimum as 1 -- fail
        # loud at construction rather than only at schema-validation time.
        if isinstance(self.schema_version, bool) or self.schema_version < 1:
            raise ValueError(f"schema_version must be an int >= 1, got {self.schema_version!r}")
        if self.verb not in _VALID_VERBS:
            raise ValueError(f"verb must be one of {sorted(_VALID_VERBS)}, got {self.verb!r}")
        object.__setattr__(self, "findings", tuple(self.findings))
        if self.verb == "diagnose":
            if self.prescriptions is None:
                raise ValueError("verb 'diagnose' requires prescriptions (a list, possibly empty) — got None")
            object.__setattr__(self, "prescriptions", tuple(self.prescriptions))
        elif self.prescriptions is not None:
            raise ValueError(
                f"verb {self.verb!r} must not carry prescriptions (only "
                "'diagnose' reports do) — the key must be omitted, never null"
            )
        if self.axis_scores is not None:
            object.__setattr__(self, "axis_scores", tuple(dict(axis) for axis in self.axis_scores))

    def to_json_dict(self) -> dict[str, object]:
        document: dict[str, object] = {
            "schema_version": self.schema_version,
            "verb": self.verb,
            "generated_at": self.generated_at,
            "findings": [finding.to_json_dict() for finding in self.findings],
        }
        if self.prescriptions is not None:
            document["prescriptions"] = [prescription.to_json_dict() for prescription in self.prescriptions]
        if self.grade is not None:
            document["grade"] = self.grade
        if self.axis_scores is not None:
            document["axis_scores"] = [dict(axis) for axis in self.axis_scores]
        return document
