"""``marshal seed check``'s verb logic: a pure, read-only composition of
Epic 9's already-landed detect/plan primitives into one conformance report
(Story 10.5, FR-88/FR-89/FR-90/FR-91/FR-92/FR-93/NFR-P1).

Until this module, `cli/seed.py::run_check` was Story 7.1's stub -- it
printed "not yet implemented" and returned `EXIT_OK` unconditionally, so
nothing in this package could ever detect that an adopted repo had drifted
from the seed model it installed. `run_check` is that detector: it reads
state (never writes it), classifies the manifest against the target repo
(`detect.inventory.classify`), builds the SAME plan `adopt`/`update` would
act on (`plan.build.build_plan`, **never** `write_plan`) -- the epic-10
context note is explicit that `check` "is defined as detect + plan, writes
unreachable," not a second, independently-drifting implementation of either
-- and turns the result into a `CheckReport` of `Finding`s plus a
model-version status. No `seed.fs` import exists anywhere in this module,
and none is needed: every primitive this module calls is itself read-only,
so "never write" is a property of this module's import surface, not merely
of the runtime path it happens to exercise (`tests/unit/
test_seed_verbs_check.py`'s write-blocking fixture pins this).

**Why `build_plan` matters here, concretely, not just by convention.**
`build_plan`'s own docstring (Story 8.5) documents a real, easy-to-miss
correctness trap this module would otherwise fall into: a
`hybrid-managed-region` entry that is `ArtifactState.ABSENT` (the whole
file is gone) but every one of its declared regions is already recorded in
`state.opted_out` is `_is_fully_opted_out` -- `build_plan` produces NO
`Action` for it, because FR-112 says the tool will never re-insert an
opted-out region and there is therefore nothing left for `seed update` to
do. A naive "`ARTIFACT_MISSING` for every `ABSENT` classification" (the
Approach paragraph's own shorthand, read literally) would report a HARD,
exit-blocking finding for an artifact the operator has explicitly and
permanently opted out of, with a remedy ("run `marshal seed adopt`") that
is simply false -- adopting again would materialize nothing, because
everything about it is opted out. `run_check` below emits `ARTIFACT_MISSING`
only for an `ABSENT` classification whose artifact id still appears in
`plan.actions` -- i.e. only when there is a real pending remediation --
which is exactly what `build_plan` already computed and this module must
not re-derive by hand (P-03: no module in this package re-implements a
sibling's classification rule). Every other `ArtifactClass` never reaches
`_is_fully_opted_out` at all (`build_plan`'s own `_pendency` returns `None`
for a non-hybrid entry, so `_is_fully_opted_out` is `False` unconditionally)
-- so this gate changes behavior for exactly the one case it exists for and
is a no-op everywhere else, including every row of this story's own I/O
matrix that predates opt-outs.

**Why `PRESENT_LEGACY` short-circuits before any hash/region check.**
AD-59 frames a recognized legacy artifact as "never written to" -- Genesis
stops inspecting its internal structure the moment `legacy_of` is
classified. Running `check_managed_file`/`classify_regions` against it
anyway would report drift for content nobody expects to still match a
model the manifest itself says this artifact has been superseded by; the
one finding a legacy artifact ever produces is `legacy_findings`'s own INFO
``legacy-present``, unconditionally, via `detect.inventory.legacy_findings`
composed with everything else below.

**Why `ArtifactClass.REFERENCED` short-circuits too.** `classify()` itself
never inspects a referenced entry's filesystem state -- `model/artifact.py`'s
``CLASS_BEHAVIOR`` calls the class "not materialized" -- so it always
classifies `PRESENT_CONFORMANT` before even checking presence. Reading its
declared `path` here would be pointless I/O against a path that, by the
class's own definition, may not name a real file at all.

**Why the whole-file and region-body hash checks are keyed off
`state.managed[]`, never off `ArtifactClass` alone.** The schema
(`state/schema.json::managedArtifact`) lets a claim exist for ANY class, not
only `copied-managed`/`copied-seeded`/`hybrid-managed-region` -- and
`ManagedArtifact.inserted_region_span` is the IFF signal for which
`detect.hashes` function applies (non-`None` -> `check_managed_region`
against the freshly re-parsed span of that name; `None` -> `check_managed_file`
against the whole file), not the manifest entry's own declared class. This
matters concretely, not just by convention: a manifest entry's declared
class can be reclassified across model versions (Epic 11's own migration
machinery exists for exactly that), while `state.managed[]`'s record still
describes what was actually recorded at adopt/last-update time -- so the
primitive selection below reads `record.inserted_region_span`, never
`entry.artifact_class`, even though the surrounding region-status loop
(`classify_regions`/`region_findings`) legitimately does key off
`entry.artifact_class` (it reports on the CURRENT manifest's declared
regions, not history). A present entry with no `state.managed[]` record at
all (never adopted, or a manifest addition state has not caught up to yet)
has nothing recorded to compare against, so no hash check runs for it --
silence, not a finding; rung 6's "hand-edit reported" contract belongs to
`verbs.preconditions`, a MUTATING-verb gate this module does not call and
does not duplicate (see this story's own Never bullets).

**Why `ARTIFACT_MISSING` is also gated on `applies_to` vs. `state.mode`
(Story 10.7 fix).** `run_check`'s `ARTIFACT_MISSING` gate above only asked
`build_plan`'s own "is there a real pending remediation" question -- it had
no `applies_to` awareness at all, a narrowly-scoped, confirmed-necessary
latent defect in this ALREADY-SHIPPED module. Direct reading of `templates/
manifest.yaml` confirms the concrete failure it produces: `specs-dir-legacy`
(`applies_to: adopt`)'s own rationale reads "a fresh init never creates
it" -- yet nothing before this fix ever consulted that field, so this gate
WOULD flag `specs-dir-legacy` as a HARD finding on every freshly `init`'d
repo, and symmetrically WOULD flag `starter-dream`/`specs-readme`
(`applies_to: init`) as HARD findings on every `adopt`'d repo. Story 10.5's
own AC never exercised `applies_to` at all (it predates both `init` and
`adopt` having any real implementation), so this was never caught until
Story 10.7's own "`marshal seed check` on the fresh repo is green" AC could
not hold without it. The fix is one additive condition on the existing
branch: skip the finding when `state is not None and entry.applies_to is
not AppliesTo.BOTH and entry.applies_to.value != state.mode` -- i.e. only
when there IS a recorded mode (a never-adopted repo, `state is None`, keeps
its UNCHANGED pre-fix behavior: every non-``referenced`` entry, `init`-only
or `adopt`-only alike, is still reported missing, matching 10.5's own
existing AC/tests for that case byte-for-byte) and the entry's own
`applies_to` neither is `BOTH` (which participates in every mode, so it is
never exempted) nor matches the CURRENT repo's recorded `state.mode`. This
is the ONLY change this story makes to this module -- no other finding
type, no other branch, no refactor.

**Why the record lookup also compares `record.path`, not just `record.id`.**
`detect.optout._claims_region` already documents (and was fixed for) the
identical trap: AD-55 makes `id`, not `path`, the stable address, so a
manifest entry's `path` can move while its `id` does not, and a stale
`state.managed[]` record still names the OLD path. Comparing hashes against
a record whose `path` no longer matches the entry's current `path` would
compare today's file content against a claim describing a location that no
longer carries it -- a near-guaranteed spurious finding, or a missed real
one, depending on what happens to live at the old path. `managed_by_id`
below is intentionally id-only for the LOOKUP (finding the right record
among several by its stable id); the path is checked as a second, separate
gate immediately after, matching `_claims_region`'s own "all three halves
required" rule and its documented "a moved path falls through to no-check,
never a guess" conservative direction -- a genuine path-move is `seed
update`'s migration to reconcile, not `check`'s hash comparison.

**Why `STATE_INVALID` degrades to a single Finding and nothing else
changes.** `state.read_state` already documents this exactly:
``StateInvalid`` is the read path's ONLY escaping exception (FR-104), and a
never-adopted repo (`None`) is a normal case rather than an error. This
module's own contract narrows that further -- a caught ``StateInvalid``
must not abort the run: the rest of the check proceeds with `state=None`,
which is exactly the never-adopted view (`classify_regions`/`is_opted_out`
already accept `state=None` and degrade the same way `read_state` itself
would for an absent file). One HARD ``state-invalid`` `Finding` names the
corruption; everything downstream simply cannot see anything this repo may
have previously recorded.

**Why `model_version` comparison lives here rather than in `detect.inventory`
or `state.store`.** Neither module owns both halves of the comparison:
`Manifest.model_version` is the BUNDLED clock (`model/manifest.py`,
A-05), `SeedState.model_version` is the REPO's own recorded clock, and
`ModelVersion`'s ordering (`model/version.py`) is the only piece either side
needs. `run_check` is the first real call site that reads both at once, per
FR-92's own three-way vocabulary (`model-behind` / `current` / `ahead`) --
a never-adopted repo (`state is None`) is unconditionally `model-behind`
("nothing installed yet" is this story's own Boundaries wording), never an
error and never `ahead`/`current` (there is no recorded value to be either
of those).

**Story 28.3's token-economy kit (SPEC-marshal-token-economy CAP-3/CAP-4).**
`run_check` gains ONE optional keyword, `context_layers`, and delegates the
whole question to `detect.kit` -- three per-item checks in, findings out. No
kit logic lives here: this module neither knows what a caveman skill is nor
what makes a codegraph index fresh, matching its own standing rule that it
composes sibling primitives rather than re-deriving them. Two properties of
that delegation are load-bearing and stated so a later edit cannot lose them
by accident: (1) `context_layers=None` produces an EMPTY `report.kit` and
zero findings, which is what keeps every pre-28.3 caller byte-identical, and
(2) no kit finding is ever HARD, so a token-economy gap can never turn a
conformant repo's `marshal seed check` red -- the spec's "never blocks a
run" constraint, enforced in `detect/kit.py`'s own severity table.

**Import surface.** `detect.findings`/`detect.hashes`/`detect.inventory`/
`detect.kit`/`detect.optout` (the finding vocabulary and every detect
primitive this module composes), `plan.build.build_plan` (never `write_plan`, and never
`plan.build.write_plan`'s sibling `default_plan_path`/`load_plan` -- this
module persists nothing and reads no `plan.json`), `model.manifest`
(`AppliesTo` -- Story 10.7's own addition, for the `applies_to`-vs-`state.
mode` gate above -- `ArtifactClass`, `Manifest`), `regions.parse`/`regions.markers` (parsing a
present hybrid file's spans for the region-hash check, the identical
exception triple every sibling degrade-rather-than-guess call site in this
package already catches), `state` (`read_state`, `SeedState`, `state_path`)
and `errors.StateInvalid` (caught, never re-raised). No `seed.fs`, no
`seed.verbs.preconditions`, no `seed.verbs.skips`, no `seed.apply`, no
`seed.engine`, no `seed.cli` -- this module is a leaf `verbs/` module with
no write capability reachable from its own imports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pyforge.core.process import PosixProcess

from ..detect.findings import Finding, FindingType, Severity
from ..detect.hashes import check_managed_file, check_managed_region
from ..detect.inventory import ArtifactState, classify, legacy_findings
from ..detect.kit import KitCheck, kit_checks, kit_findings
from ..detect.optout import classify_regions, region_findings
from ..detect.referenced_deps import referenced_dep_findings
from ..errors import StateInvalid
from ..model.manifest import AppliesTo, ArtifactClass, Manifest
from ..plan.build import build_plan
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions
from ..state import SeedState, read_state, state_path


class ModelVersionStatus(StrEnum):
    """FR-92's own three-way vocabulary, kebab-case matching this package's
    established `StrEnum` wire-value convention (`ArtifactState`,
    `FindingType`, `RegionDisposition`). `BEHIND` is the only member a
    never-adopted repo (`state is None`) can ever report -- there is no
    recorded `state.model_version` to be `CURRENT`/`AHEAD` of anything."""

    BEHIND = "model-behind"
    CURRENT = "current"
    AHEAD = "ahead"


@dataclass(frozen=True)
class CheckReport:
    """`run_check`'s whole return value: a plain, JSON-serializable data
    shape (this story's own Boundaries bullet), never an exception -- the
    six-leaf `SeedError` taxonomy belongs to `cli/seed.py`, which decides
    exit codes from this report rather than catching a raise from here (this
    module raises nothing of its own; see the module docstring's
    `StateInvalid` paragraph for the one exception it DOES catch).

    `strict` is carried on the report, not merely consumed and discarded, so
    `failing` -- the one field a caller actually needs to pick an exit code
    -- is computed once, here, from the exact rule the epics AC states
    ("exits non-zero on any HARD finding; `--strict` additionally fails on
    DRIFT") rather than re-derived at each of `cli/seed.py`'s two render
    branches (text and `--json`) with two chances to disagree."""

    findings: tuple[Finding, ...]
    strict: bool
    manifest_model_version: str
    state_model_version: str | None
    model_version_status: ModelVersionStatus
    #: Story 28.3: the token-economy kit's three per-item checks, in
    #: ``KIT_ITEMS`` order. Empty when the caller supplied no
    #: ``context_layers`` at all (nothing was asked, so nothing is claimed);
    #: otherwise ALWAYS three entries, including the passing and the
    #: declared-off ones -- AC 1 asks for three distinct checks, and a
    #: report that only ever showed failures could not distinguish
    #: "verified, fine" from "never looked". Defaulted so every existing
    #: construction site (and every test that predates this story) keeps
    #: working unchanged.
    kit: tuple[KitCheck, ...] = field(default=())

    def by_severity(self, severity: Severity) -> tuple[Finding, ...]:
        """Every finding of exactly `severity`, in report order -- the one
        query both `failing` and `cli/seed.py`'s severity-grouped text
        renderer need, kept in one place so the two can never disagree about
        what "a HARD finding" means."""
        return tuple(finding for finding in self.findings if finding.severity is severity)

    @property
    def failing(self) -> bool:
        """Whether this run should exit non-zero: any HARD finding, always;
        any DRIFT finding, only under `--strict`. INFO findings never affect
        this -- `legacy-present`/`opted-out` are AD-59/FR-112's own
        "informational only, no action required" cases, never a reason to
        block CI."""
        if self.by_severity(Severity.HARD):
            return True
        return self.strict and bool(self.by_severity(Severity.DRIFT))

    def to_json_dict(self) -> dict[str, Any]:
        """FR-91's CI-annotatable shape: fixed field order, every `Finding`
        via its own `to_json_dict()` (never a hand-rolled re-serialization),
        `failing` computed rather than left for a consumer to re-derive from
        severities it would otherwise have to know this package's own
        HARD/DRIFT/`--strict` rule to reconstruct correctly."""
        return {
            "strict": self.strict,
            "findings": [finding.to_json_dict() for finding in self.findings],
            "model_version": {
                "manifest": self.manifest_model_version,
                "state": self.state_model_version,
                "status": self.model_version_status.value,
            },
            "kit": [check.to_json_dict() for check in self.kit],
            "failing": self.failing,
        }


def _read_text_or_blank(target: Path) -> str:
    """The UTF-8 text at `target`, or `""` for anything that is not a
    readable regular file -- absent, a directory, unreadable, or invalid
    encoding. Mirrors `plan.build._read_text_or_blank_verbose`'s identical
    degrade rule (that function is private to a sibling module this story
    may not reach into -- `verbs/skips.py`'s module docstring states this
    package's established stance on that trade: a small, deliberate
    duplication of a PRIVATE helper beats an import across a module
    boundary). Unlike that function, this module never needs the
    "was this actually read" second value `_current_text_verbose` carries
    for `build_plan`'s own opt-out consent argument -- `run_check` never
    infers consent from readability, it only reads a file to hash or parse
    it, and `""` is a safe, already-documented input to every consumer
    below (`classify_regions` handles it explicitly; `hash_content`/
    `parse_regions` have nothing better to do with it either)."""
    if not target.is_file():
        return ""
    try:
        return target.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def _model_version_status(manifest: Manifest, state: SeedState | None) -> tuple[ModelVersionStatus, str | None]:
    """`(status, state_model_version_str)` for the report -- `state is None`
    is unconditionally `BEHIND` with no recorded version to report (the
    module docstring's own "nothing installed yet" framing); otherwise the
    three-way comparison is `ModelVersion`'s own ordering, never re-derived
    by hand from the two `str` forms."""
    if state is None:
        return ModelVersionStatus.BEHIND, None
    state_version = str(state.model_version)
    if state.model_version < manifest.model_version:
        return ModelVersionStatus.BEHIND, state_version
    if state.model_version == manifest.model_version:
        return ModelVersionStatus.CURRENT, state_version
    return ModelVersionStatus.AHEAD, state_version


def run_check(
    repo_root: Path,
    manifest: Manifest,
    *,
    strict: bool = False,
    context_layers: Mapping[str, Mapping[str, Any]] | None = None,
    process: PosixProcess | None = None,
) -> CheckReport:
    """Compose Epic 9's detect/plan primitives into one `CheckReport`
    against `repo_root`, writing nothing (no `.marshal/` creation, no
    `plan.json`, no state write) and raising nothing of its own (a caught
    `StateInvalid` becomes one `Finding`; see the module docstring).

    Explicit inputs only, no hidden I/O beyond what `read_state`/`classify`/
    `build_plan` already perform (this story's own Boundaries bullet,
    matching `verbs.preconditions`/`verbs.skips`'s pure-function verb-module
    convention): `manifest` is the caller's already-loaded bundled model
    (`cli/seed.py` loads it; this module never reads `templates/manifest.yaml`
    itself), and `repo_root` names the target repo to check.

    Order of operations, and why it is this order: `read_state` first (its
    own `StateInvalid` must be absorbed into `state=None` before anything
    downstream -- `classify`/`classify_regions`/`build_plan` all accept a
    `None` state and degrade to the never-adopted view for it, so there is
    exactly one place this module ever branches on "did state fail to
    read"); `classify` next (one walk of `repo_root`, reused for both the
    per-entry finding loop below and as `build_plan`'s own required input);
    `build_plan` last, before the loop, so the loop can consult
    `plan.actions`'s artifact-id set for the one gate that needs it
    (`ARTIFACT_MISSING` suppression on a fully-opted-out hybrid entry -- see
    the module docstring).

    `context_layers` (Story 28.3) is Story 28.1's already-RESOLVED
    `[context]` declaration -- `core.policy.resolve_context_layers`'s
    mapping, read from a policy file by `cli/seed.py` at the CLI boundary
    exactly the way `manifest` is. `None` (the default) means the caller
    asked no token-economy question at all: `report.kit` is empty and not
    one kit finding is produced, so every pre-28.3 call site keeps its
    byte-identical behavior. A mapping with every layer off produces three
    `KitCheck`s and still zero findings -- AC 4's "declared-off, not
    missing". `process` is the same injectable `PosixProcess` the kit's own
    freshness probe takes, threaded rather than left to default so a caller
    that has one (a test, or `run_kit`) is not silently forced back onto a
    real `git log` subprocess."""
    findings: list[Finding] = []

    state: SeedState | None
    try:
        state = read_state(repo_root)
    except StateInvalid as exc:
        relative_state_path = state_path(repo_root).relative_to(repo_root).as_posix()
        findings.append(Finding.new(Severity.HARD, FindingType.STATE_INVALID, relative_state_path, exc.message))
        state = None

    inventory = classify(manifest, repo_root)
    opted_out = frozenset(state.opted_out) if state is not None else frozenset()
    plan = build_plan(manifest, inventory, opted_out=opted_out)
    actioned_ids = frozenset(action.artifact_id for action in plan.actions)

    entries_by_id = {entry.id: entry for entry in manifest.entries}
    managed_by_id = {record.id: record for record in state.managed} if state is not None else {}

    for classification in inventory.classifications:
        entry = entries_by_id[classification.entry_id]

        if classification.state is ArtifactState.ABSENT:
            # Gated by `plan.actions`, never by the classification alone --
            # see the module docstring's `build_plan` paragraph for the real
            # correctness gap ("fully opted out") this closes -- AND by
            # `applies_to` vs. the current repo's recorded `state.mode`
            # (Story 10.7 fix, see the module docstring's own paragraph):
            # an entry that does not apply to THIS repo's mode is never
            # "missing", it was simply never owed here in the first place.
            applies_to_other_mode = (
                state is not None and entry.applies_to is not AppliesTo.BOTH and entry.applies_to.value != state.mode
            )
            if classification.entry_id in actioned_ids and not applies_to_other_mode:
                findings.append(
                    Finding.new(
                        Severity.HARD,
                        FindingType.ARTIFACT_MISSING,
                        entry.path,
                        f"{entry.path}: {entry.id!r} is declared by the manifest but absent from the repo",
                    )
                )
            continue

        if classification.state is ArtifactState.PRESENT_LEGACY:
            # AD-59: never written to, never inspected again -- its one
            # finding (INFO legacy-present) comes from `legacy_findings`
            # below, built from `inventory.legacy` in the SAME pass
            # `classify()` already did.
            continue

        if entry.artifact_class is ArtifactClass.REFERENCED:
            # Not materialized -- `classify()` itself never inspected the
            # filesystem to reach PRESENT_CONFORMANT here, and neither does
            # this module (module docstring).
            continue

        # PRESENT_CONFORMANT or PRESENT_DIVERGENT, a real materialized
        # artifact this module may inspect. `PRESENT_DIVERGENT` is only
        # ever reached by a hybrid-managed-region entry (`detect.inventory`'s
        # own documented invariant), so branching on `entry.artifact_class`
        # rather than on `classification.state` covers both states
        # correctly with one condition.
        text = _read_text_or_blank(repo_root / entry.path)
        record = managed_by_id.get(entry.id)
        if record is not None and record.path != entry.path:
            # A moved path falls through to "no record" -- never a guess --
            # matching `_claims_region`'s identical, already-fixed trap (see
            # the module docstring). A genuine path move is `seed update`'s
            # migration to reconcile, not `check`'s hash comparison.
            record = None

        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            statuses = classify_regions(entry, text, state)
            findings.extend(region_findings(statuses))

        # The whole-file vs. region-body hash-check primitive is selected by
        # `record.inserted_region_span`, never by `entry.artifact_class`
        # alone (module docstring) -- the manifest's CURRENT class can have
        # drifted from what `state.managed[]` actually recorded.
        if record is not None and record.inserted_region_span is not None:
            if entry.format is None:
                # The record was written while this entry was still
                # hybrid-managed-region; the manifest has since reclassified
                # it to a class with no declared region format, so there is
                # no format left to re-parse the recorded span's name out
                # of. A later `seed update` migration reconciles the stale
                # record shape -- `check` detects, it never repairs (this
                # story's own Never bullets).
                pass
            else:
                try:
                    spans = parse_regions(text, entry.format)
                except RegionParseError, MarkerError, NotImplementedError:
                    spans = ()
                span = next(
                    (candidate for candidate in spans if candidate.name == record.inserted_region_span.name),
                    None,
                )
                # `span is None` means the recorded region is not (or no
                # longer) parseable from the file -- `region_findings`
                # above has already reported that as `managed-region-missing`
                # (or, if unparseable, produced no per-region finding at all,
                # matching `classify_regions`'s own degrade-rather-than-guess
                # rule); there is nothing left here to hash a mismatch
                # against.
                if span is not None:
                    finding = check_managed_region(entry.path, text, span, record.body_sha)
                    if finding is not None:
                        findings.append(finding)
        elif record is not None:
            finding = check_managed_file(entry.path, text, record.body_sha)
            if finding is not None:
                findings.append(finding)

    findings.extend(legacy_findings(inventory))
    findings.extend(referenced_dep_findings(manifest, repo_root))

    # Story 28.3's three token-economy-kit checks. Computed even when every
    # layer is off (so the report can SHOW three checks), but contributing
    # findings only for a layer the operator actually declared on.
    kit = kit_checks(repo_root, context_layers, process=process) if context_layers is not None else ()
    findings.extend(kit_findings(kit))

    model_version_status, state_model_version = _model_version_status(manifest, state)
    if model_version_status is ModelVersionStatus.BEHIND:
        state_version_text = (
            "no recorded model_version (never adopted)" if state is None else (f"model_version {state_model_version}")
        )
        findings.append(
            Finding.new(
                Severity.DRIFT,
                FindingType.MODEL_BEHIND,
                state_path(repo_root).relative_to(repo_root).as_posix(),
                f"repo is at {state_version_text}; the bundled seed manifest is at"
                f" model_version {manifest.model_version}",
            )
        )

    return CheckReport(
        findings=tuple(findings),
        strict=strict,
        manifest_model_version=str(manifest.model_version),
        state_model_version=state_model_version,
        model_version_status=model_version_status,
        kit=kit,
    )
