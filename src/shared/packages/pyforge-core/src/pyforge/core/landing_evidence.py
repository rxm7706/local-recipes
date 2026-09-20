"""pyforge.core.landing_evidence -- ONE shared grammar of landing-evidence
shapes (Story 20.8 / FR-191 CAP-1, spec-landing-evidence-grammar).

Every consumer that asks "did story X land on ``main``?" -- doctor
``story-status``, marshal ``merged_story_keys``, MRS-STATUS-010, ``marshal
retire`` -- currently speaks a partial dialect. This module is the shared
spine (Story 14.2 atomic-write precedent): pure stdlib, imports nothing
from any ``pyforge.<station>`` package, so doctor never imports
``pyforge.marshal``.

Shapes recognized (merge subjects, branch names, recovery convention):

* **Templated merge subject** (AD-24 / FR-187): caller-supplied
  ``merge_subject_template`` with exactly one ``{key}`` placeholder and an
  optional ``{slug}`` placeholder filled with the caller's own
  ``project_slug`` before the ``{key}`` split ever runs -- a subject rendered
  under a foreign slug carries a different literal prefix/suffix and simply
  fails to match (Story 50.4/FR-191 CAP-247).
* **GitHub PR merge subject**: ``Merge pull request #N from <owner>/<branch>``.
* **bmad-loop merge subject**: ``Merge bmad-loop/<run>/<key>-<desc> into
  loop/<project> (bmad-loop)``.
* **Recovery commit subject**: ``recover <station> <epic>-<seq> …`` (the
  documented forward convention for manual recoveries).
* **Story direct commit subject**: ``Story <epic>.<seq>: …`` (pre-convention
  era; requires a station-scoped ``branch`` -- via ``_branch_belongs_to_project``
  -- to corroborate ``project_slug``, since the subject itself carries no
  station token; refuses when ``branch`` is unavailable or foreign, Story
  50.4/FR-191 CAP-247).
* **Branch grammars**: ``land/<station>-<epic>-<seq>…``,
  ``bmad-loop/<run>/<key>-<desc>``, ``<station>/<key>-<desc>`` (GitHub PR
  branch convention), and ``dispatch/<project_slug>/<key>`` (marshal Story
  22.9's station-scoped dispatch branch).
* **Pre-convention recovery allowlist**: three live recovery commits that
  fail every predicate above when judged in isolation -- recognized by SHA
  prefix, never by history rewrite.

Stories 20.9 (doctor adoption) and 20.10 (marshal adoption) wire consumers
to this module; this story ships the grammar + conformance surface only.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

_KEY_PLACEHOLDER = "{key}"

#: The optional second placeholder (Story 50.4, FR-191 CAP-247): a template
#: may carry at most one ``{slug}``, filled/matched against the caller's own
#: ``project_slug`` BEFORE ``{key}`` splitting even looks at the template --
#: a template with no ``{slug}`` at all (every pre-existing per-station
#: override) is unaffected. This mirrors ``pyforge.marshal.core.identity``'s
#: own ``_instantiate_slug`` (the two packages independently own their
#: render/parse pair per this story's Binding, but share the same
#: placeholder-fill semantics).
_SLUG_PLACEHOLDER = "{slug}"

#: The ONE spelling of marshal's station-scoped dispatch branch prefix
#: (Story 22.9). It lives here rather than in ``pyforge.marshal`` because
#: BOTH sides need it and the literal must exist exactly once across the two
#: packages: marshal MINTS ``dispatch/<project_slug>/<key>`` branches, and
#: this grammar has to RECOGNIZE them so a dispatch landing still classifies
#: (``merged_story_keys`` -> ``story_merged_on_main`` -> the supervisor's
#: re-landing guard and the CAP-2 zombie check). ``pyforge.marshal.core.
#: dispatch`` imports this name; nothing here imports marshal.
DISPATCH_BRANCH_PREFIX = "dispatch"

# Leading ``<epic>[.-]<seq><suffix>?`` token -- mirrors marshal
# ``core.identity``'s ``_KEY_RE`` without importing that package.
_KEY_TOKEN_RE = re.compile(r"(?P<epic>[0-9]+)[.\-](?P<seq>[0-9]+)(?P<suffix>[A-Za-z])?(?=$|[.\-])")

_GITHUB_MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+ from \S+?/(?P<branch>\S+)$")

_BMADLOOP_MERGE_SUBJECT_RE = re.compile(r"^Merge bmad-loop/\S+/(?P<key_slug>\S+) into (?P<target>\S+) \(bmad-loop\)$")

_RECOVERY_COMMIT_SUBJECT_RE = re.compile(
    r"^recover\s+(?P<station>\S+)\s+(?P<epic>\d+)[.\-](?P<seq>\d+)",
    re.IGNORECASE,
)

_STORY_DIRECT_COMMIT_SUBJECT_RE = re.compile(
    r"^Story\s+(?P<epic>\d+)\.(?P<seq>\d+)",
    re.IGNORECASE,
)

_LAND_BRANCH_RE = re.compile(
    r"^land/(?P<station>[^/]+)-(?P<epic>\d+)-(?P<seq>\d+)",
    re.IGNORECASE,
)

_BMADLOOP_BRANCH_RE = re.compile(
    r"^bmad-loop/[^/]+/(?P<key_slug>[^/]+)",
    re.IGNORECASE,
)


class LandingEvidenceShape(StrEnum):
    """Which sanctioned landing-evidence shape matched."""

    TEMPLATED_MERGE_SUBJECT = "templated_merge_subject"
    GITHUB_PR_MERGE_SUBJECT = "github_pr_merge_subject"
    BMAD_LOOP_MERGE_SUBJECT = "bmad_loop_merge_subject"
    RECOVERY_COMMIT_SUBJECT = "recovery_commit_subject"
    STORY_DIRECT_COMMIT_SUBJECT = "story_direct_commit_subject"
    LAND_BRANCH_NAME = "land_branch_name"
    BMAD_LOOP_BRANCH_NAME = "bmad_loop_branch_name"
    STATION_BRANCH_NAME = "station_branch_name"
    RECOVERY_COMMIT_ALLOWLIST = "recovery_commit_allowlist"


class BranchDerivedShape(StrEnum):
    """Which project-scoped branch grammar a matched branch satisfied.

    Story 51.7/CAP-255: ``_branch_belongs_to_project`` accepts two shapes
    that carry very different intent guarantees -- marshal Story 22.9's
    ``dispatch/<project_slug>/<key>`` branch, which marshal itself mints
    ONLY when it has actually dispatched ``key``, versus a bare
    ``<station>/…`` branch, which a mint, fallout or fix PR can equally
    well carry (it names the key with no intent to land it -- the
    2026-09-18 ``doctor/27-4-mint`` incident). Exposed on
    ``LandingEvidenceMatch`` so a caller can tell the two apart without
    re-deriving the branch grammar itself.
    """

    DISPATCH_BRANCH = "dispatch_branch"
    STATION_BRANCH = "station_branch"


@dataclass(frozen=True, order=True)
class StoryKeyRef:
    """Portable story key for cross-package grammar (stdlib-only).

    Marshal's ``StoryKey`` and doctor's feed keys both map to this form at
    the grammar boundary. ``suffix`` is ``""`` or a single lowercase letter.
    """

    epic: int
    seq: int
    suffix: str = ""

    def __post_init__(self) -> None:
        if self.epic < 0 or self.seq < 0:
            raise ValueError("epic and seq must be non-negative")
        if self.suffix and (len(self.suffix) != 1 or not ("a" <= self.suffix <= "z")):
            raise ValueError("suffix must be '' or a single lowercase a-z letter")

    def hyphen_form(self) -> str:
        return f"{self.epic}-{self.seq}{self.suffix}"

    def dot_form(self) -> str:
        return f"{self.epic}.{self.seq}{self.suffix}"


# One-time reviewed allowlist for pre-convention recovery landings (open
# question resolution in spec-landing-evidence-grammar): never rewrite history.
PRE_CONVENTION_RECOVERY_COMMITS: frozenset[str] = frozenset(
    {
        "accc097e6a",
        "5290c9bcd2",
        "03d8fc8c86",
    }
)

_RECOVERY_ALLOWLIST_KEYS: dict[str, StoryKeyRef] = {
    "accc097e6a": StoryKeyRef(8, 2),  # marshal 8-2, Story 8.2 direct commit
    "5290c9bcd2": StoryKeyRef(10, 1),  # marshal 10-1 recovery
    "03d8fc8c86": StoryKeyRef(3, 7),  # mason 3-7 recovery
}

RECOVERY_LANDING_CONVENTION = """\
Recovery landing convention (forward-compatible, FR-191 CAP-1):

1. Branch: ``land/<station>-<epic>-<seq>[-<description>]`` off the loop home
   (same shape as PRs #482-#488).
2. Merge commit subject: ``recover <station> <epic>-<seq> (<short title>)``
   when landing by hand without ``marshal land``'s templated subject.
3. Prefer ``marshal land`` / ``deploy land-story`` (FR-187 templated subject)
   for all new landings -- recovery shapes above exist so manual recoveries
   are born recognizable.

Pre-convention era (2026-08-13 stuck-orchestrator recoveries): three commits
are additionally recognized via reviewed SHA allowlist
(``PRE_CONVENTION_RECOVERY_COMMITS``) -- never retroactive subject rewrites.
"""


def _station_from_project_slug(project_slug: str) -> str:
    return project_slug.removeprefix("pyforge-")


def _branch_derived_shape(branch: str | None, project_slug: str) -> BranchDerivedShape | None:
    """Which project-scoped branch grammar (if any) ``branch`` satisfies.

    Two sanctioned shapes, both project-scoped so a cross-station key
    collision can never classify: the legacy/loop ``<station>/…`` prefix,
    and marshal Story 22.9's ``dispatch/<project_slug>/…`` -- the latter
    carrying the FULL slug, which is exactly what makes
    ``dispatch/pyforge-mason/22.9`` unrecognizable to ``pyforge-marshal``.
    ``None`` when ``branch`` matches neither -- the sole source of truth
    ``_branch_belongs_to_project`` and ``classify_merge_subject`` both
    delegate to (Story 51.7/CAP-255).
    """
    if not isinstance(branch, str) or not project_slug:
        return None
    if branch.startswith(f"{DISPATCH_BRANCH_PREFIX}/{project_slug}/"):
        return BranchDerivedShape.DISPATCH_BRANCH
    station = _station_from_project_slug(project_slug)
    if station and branch.startswith(f"{station}/"):
        return BranchDerivedShape.STATION_BRANCH
    return None


def _branch_belongs_to_project(branch: str | None, project_slug: str) -> bool:
    """Does ``branch`` name a branch of ``project_slug``'s station?"""
    return _branch_derived_shape(branch, project_slug) is not None


def _parse_key_token(raw: str) -> StoryKeyRef | None:
    if not isinstance(raw, str):
        return None
    match = _KEY_TOKEN_RE.match(raw.strip())
    if match is None:
        return None
    suffix = (match.group("suffix") or "").lower()
    return StoryKeyRef(
        epic=int(match.group("epic")),
        seq=int(match.group("seq")),
        suffix=suffix,
    )


def _instantiate_slug(template: str, project_slug: str) -> str | None:
    """Fill ``template``'s optional ``{slug}`` with ``project_slug``.

    A ``template`` with no ``{slug}`` passes through unchanged. Returns
    ``None`` (never raises -- this module's parsers are failure-tolerant by
    design) when ``template`` carries more than one ``{slug}``, or when
    ``{slug}`` is present but ``project_slug`` isn't a non-empty ``str``.
    """
    if not isinstance(template, str):
        return None
    if _SLUG_PLACEHOLDER not in template:
        return template
    if template.count(_SLUG_PLACEHOLDER) != 1:
        return None
    if not isinstance(project_slug, str) or project_slug == "":
        return None
    return template.replace(_SLUG_PLACEHOLDER, project_slug)


def _split_template(template: str) -> tuple[str, str] | None:
    if not isinstance(template, str) or template.count(_KEY_PLACEHOLDER) != 1:
        return None
    prefix, suffix = template.split(_KEY_PLACEHOLDER, 1)
    return prefix, suffix


def parse_templated_merge_subject(subject: str, template: str, project_slug: str) -> StoryKeyRef | None:
    """AD-24 templated merge subject: exact prefix/suffix slice around ``{key}``.

    ``template``'s optional ``{slug}`` is filled with ``project_slug`` first
    (Story 50.4) -- a subject rendered under a foreign slug then carries a
    different literal prefix/suffix and fails the ``startswith``/``endswith``
    check below, self-scoping the shape with no separate comparison step.
    """
    instantiated = _instantiate_slug(template, project_slug)
    if instantiated is None:
        return None
    parts = _split_template(instantiated)
    if parts is None or not isinstance(subject, str):
        return None
    prefix, suffix = parts
    if not subject.startswith(prefix) or not subject.endswith(suffix):
        return None
    middle_start = len(prefix)
    middle_end = len(subject) - len(suffix)
    if middle_end < middle_start:
        return None
    return _parse_key_token(subject[middle_start:middle_end])


def parse_github_pr_merge_subject(subject: str, project_slug: str) -> StoryKeyRef | None:
    """GitHub PR merge subject; branch final segment must LEAD with story key.

    Accepts both project-scoped branch shapes (``<station>/…`` and Story
    22.9's ``dispatch/<project_slug>/…``). This is the primary real-world
    detection path: the repo's standing convention is ``gh pr merge
    --merge``, which produces GitHub's default
    ``Merge pull request #N from <owner>/<branch>`` subject.
    """
    match = _GITHUB_MERGE_SUBJECT_RE.match(subject)
    if match is None:
        return None
    branch = match.group("branch")
    if not _branch_belongs_to_project(branch, project_slug):
        return None
    segment = branch.rsplit("/", 1)[-1]
    return _parse_key_token(segment)


def parse_bmadloop_merge_subject(subject: str, project_slug: str) -> StoryKeyRef | None:
    """bmad-loop native merge subject scoped to ``loop/<project_slug>``."""
    match = _BMADLOOP_MERGE_SUBJECT_RE.match(subject)
    if match is None:
        return None
    if match.group("target") != f"loop/{project_slug}":
        return None
    return _parse_key_token(match.group("key_slug"))


def parse_recovery_commit_subject(subject: str, project_slug: str) -> StoryKeyRef | None:
    """``recover <station> <epic>-<seq> …`` manual recovery convention."""
    match = _RECOVERY_COMMIT_SUBJECT_RE.match(subject)
    if match is None:
        return None
    station = _station_from_project_slug(project_slug)
    if not station or match.group("station").lower() != station.lower():
        return None
    suffix = ""
    return StoryKeyRef(
        epic=int(match.group("epic")),
        seq=int(match.group("seq")),
        suffix=suffix,
    )


def parse_story_direct_commit_subject(
    subject: str, project_slug: str, *, branch: str | None = None
) -> StoryKeyRef | None:
    """``Story <epic>.<seq>: …`` direct commit (pre-convention era).

    The subject itself carries no station token, so it can never
    self-disambiguate a cross-station key collision (Story 50.4: steward's
    ``Story 48.2:``/``Story 48.4:`` subjects were poisoning marshal's own
    48.2/48.4). ``branch`` must corroborate ``project_slug`` via
    ``_branch_belongs_to_project`` -- defaulting to ``None`` refuses by
    default when a caller has no branch data (e.g. a subject-only
    ``git log --format=%s`` scan), which is safe for
    ``merged_story_keys``: every real direct-commit landing in this repo's
    history also has an independently-scoped companion merge commit reachable
    in the same history, so the aggregate result is unaffected even though
    the direct commit no longer classifies in isolation.
    """
    match = _STORY_DIRECT_COMMIT_SUBJECT_RE.match(subject)
    if match is None:
        return None
    if not _branch_belongs_to_project(branch, project_slug):
        return None
    return StoryKeyRef(
        epic=int(match.group("epic")),
        seq=int(match.group("seq")),
        suffix="",
    )


def parse_land_branch_name(branch: str, project_slug: str) -> StoryKeyRef | None:
    """``land/<station>-<epic>-<seq>…`` recovery branch grammar."""
    match = _LAND_BRANCH_RE.match(branch)
    if match is None:
        return None
    station = _station_from_project_slug(project_slug)
    if not station or match.group("station").lower() != station.lower():
        return None
    return StoryKeyRef(
        epic=int(match.group("epic")),
        seq=int(match.group("seq")),
        suffix="",
    )


def parse_bmadloop_branch_name(branch: str) -> StoryKeyRef | None:
    """``bmad-loop/<run>/<key>-<desc>`` branch grammar."""
    match = _BMADLOOP_BRANCH_RE.match(branch)
    if match is None:
        return None
    return _parse_key_token(match.group("key_slug"))


def parse_station_branch_name(branch: str, project_slug: str) -> StoryKeyRef | None:
    """``<station>/<key>-<desc>`` GitHub PR branch convention.

    Also accepts Story 22.9's ``dispatch/<project_slug>/<key>``; both are
    project-scoped branch names whose final segment leads with the key, so
    they share one shape rather than minting a second enum member.
    """
    if not _branch_belongs_to_project(branch, project_slug):
        return None
    segment = branch.rsplit("/", 1)[-1]
    return _parse_key_token(segment)


def parse_recovery_commit_sha(commit_sha: str) -> StoryKeyRef | None:
    """Pre-convention allowlist lookup by SHA prefix (full or abbreviated)."""
    normalized = commit_sha.strip().lower()
    for prefix, key in _RECOVERY_ALLOWLIST_KEYS.items():
        if normalized.startswith(prefix.lower()):
            return key
    return None


@dataclass(frozen=True)
class LandingEvidenceMatch:
    """A single classified landing-evidence hit.

    ``branch_shape`` (Story 51.7/CAP-255) names which project-scoped branch
    grammar the match's branch satisfied -- populated only for
    ``GITHUB_PR_MERGE_SUBJECT`` (the one shape whose branch can equally
    well belong to a mint, fallout or fix PR, never a real intent signal by
    itself); ``None`` for every other shape, including when no branch was
    involved at all.
    """

    key: StoryKeyRef
    shape: LandingEvidenceShape
    branch_shape: BranchDerivedShape | None = None


def classify_merge_subject(
    subject: str,
    *,
    template: str,
    project_slug: str,
    branch: str | None = None,
) -> LandingEvidenceMatch | None:
    """Try every merge-subject shape in precedence order.

    ``branch`` (optional, Story 50.4) corroborates the story-direct-commit
    shape only -- every other shape is already self-scoping via
    ``project_slug`` alone.
    """
    parsers: tuple[tuple[Callable[[str], StoryKeyRef | None], LandingEvidenceShape], ...] = (
        (
            lambda s: parse_templated_merge_subject(s, template, project_slug),
            LandingEvidenceShape.TEMPLATED_MERGE_SUBJECT,
        ),
        (lambda s: parse_github_pr_merge_subject(s, project_slug), LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT),
        (lambda s: parse_bmadloop_merge_subject(s, project_slug), LandingEvidenceShape.BMAD_LOOP_MERGE_SUBJECT),
        (lambda s: parse_recovery_commit_subject(s, project_slug), LandingEvidenceShape.RECOVERY_COMMIT_SUBJECT),
        (
            lambda s: parse_story_direct_commit_subject(s, project_slug, branch=branch),
            LandingEvidenceShape.STORY_DIRECT_COMMIT_SUBJECT,
        ),
    )
    for parser, shape in parsers:
        key = parser(subject)
        if key is not None:
            branch_shape: BranchDerivedShape | None = None
            if shape is LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT:
                gh_match = _GITHUB_MERGE_SUBJECT_RE.match(subject)
                if gh_match is not None:
                    branch_shape = _branch_derived_shape(gh_match.group("branch"), project_slug)
            return LandingEvidenceMatch(key=key, shape=shape, branch_shape=branch_shape)
    return None


def classify_branch_name(
    branch: str,
    *,
    project_slug: str,
) -> LandingEvidenceMatch | None:
    """Try every branch-name grammar in precedence order."""
    key = parse_land_branch_name(branch, project_slug)
    if key is not None:
        return LandingEvidenceMatch(key=key, shape=LandingEvidenceShape.LAND_BRANCH_NAME)
    key = parse_bmadloop_branch_name(branch)
    if key is not None:
        return LandingEvidenceMatch(key=key, shape=LandingEvidenceShape.BMAD_LOOP_BRANCH_NAME)
    key = parse_station_branch_name(branch, project_slug)
    if key is not None:
        return LandingEvidenceMatch(key=key, shape=LandingEvidenceShape.STATION_BRANCH_NAME)
    return None


def classify_commit(
    commit_sha: str,
    subject: str,
    *,
    template: str,
    project_slug: str,
    branch: str | None = None,
) -> LandingEvidenceMatch | None:
    """Classify one commit: allowlist first, then merge-subject shapes."""
    key = parse_recovery_commit_sha(commit_sha)
    if key is not None:
        return LandingEvidenceMatch(
            key=key,
            shape=LandingEvidenceShape.RECOVERY_COMMIT_ALLOWLIST,
        )
    return classify_merge_subject(subject, template=template, project_slug=project_slug, branch=branch)


def merged_story_keys(
    subjects: tuple[str, ...],
    *,
    template: str,
    project_slug: str,
) -> frozenset[StoryKeyRef]:
    """Every story key reachable from ``subjects`` via any merge-subject shape.

    Failure-tolerant: non-matching subjects are skipped, never raised.
    """
    keys: set[StoryKeyRef] = set()
    for subject in subjects:
        match = classify_merge_subject(subject, template=template, project_slug=project_slug)
        if match is not None:
            keys.add(match.key)
    return frozenset(keys)


def conformance_fixtures() -> tuple[dict[str, object], ...]:
    """Known-good landing shapes both packages' conformance tests import.

    Each row: ``label``, ``project_slug``, ``template``, optional
    ``subject`` / ``branch`` / ``commit_sha``, ``expected_key``,
    ``expected_shape``.
    """
    template = "Merge {key} into main"
    return (
        {
            "label": "templated_merge_subject",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": "Merge 4-2-teardown into main",
            "expected_key": StoryKeyRef(4, 2),
            "expected_shape": LandingEvidenceShape.TEMPLATED_MERGE_SUBJECT,
        },
        {
            "label": "github_pr_merge_subject",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": "Merge pull request #269 from rxm7706/marshal/2-3-frozen-surface-scope-check",
            "expected_key": StoryKeyRef(2, 3),
            "expected_shape": LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT,
        },
        {
            "label": "bmad_loop_merge_subject",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": (
                "Merge bmad-loop/20260803-023308-65b7/3-7-escalation-deferral-and-resume "
                "into loop/pyforge-marshal (bmad-loop)"
            ),
            "expected_key": StoryKeyRef(3, 7),
            "expected_shape": LandingEvidenceShape.BMAD_LOOP_MERGE_SUBJECT,
        },
        {
            "label": "recovery_commit_marshal_10_1",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": "recover marshal 10-1 (Copier engine wrapper — the single seam)",
            "expected_key": StoryKeyRef(10, 1),
            "expected_shape": LandingEvidenceShape.RECOVERY_COMMIT_SUBJECT,
        },
        {
            "label": "recovery_commit_mason_3_7",
            "project_slug": "pyforge-mason",
            "template": template,
            "subject": (
                "recover mason 3.7 (asymmetric receipts, partial failure and idempotence) "
                "from run 20260813-145934-3eb0's failed/ preserved patch"
            ),
            "expected_key": StoryKeyRef(3, 7),
            "expected_shape": LandingEvidenceShape.RECOVERY_COMMIT_SUBJECT,
        },
        {
            "label": "story_direct_commit_marshal_8_2",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": "Story 8.2: region parser -- span discovery, nesting rejection, fence awareness",
            "branch": "marshal/8-2-region-parser",
            "expected_key": StoryKeyRef(8, 2),
            "expected_shape": LandingEvidenceShape.STORY_DIRECT_COMMIT_SUBJECT,
        },
        {
            # Story 50.4: a going-forward story-direct commit only classifies
            # with a station-scoped `branch` corroborating `project_slug`.
            "label": "story_direct_commit_branch_corroborated",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": "Story 30.2: reversion of an intake-spec pin-loosening rule",
            "branch": "dispatch/pyforge-marshal/30.2",
            "expected_key": StoryKeyRef(30, 2),
            "expected_shape": LandingEvidenceShape.STORY_DIRECT_COMMIT_SUBJECT,
        },
        {
            # Story 50.4/FR-191 CAP-247: the `{slug}`-scoped default template
            # (the new repo-wide default, `policy.DEFAULT_POLICY`) renders and
            # parses like any other templated subject.
            "label": "templated_merge_subject_slug_scoped",
            "project_slug": "pyforge-marshal",
            "template": "Merge {slug}/{key} into main",
            "subject": "Merge pyforge-marshal/48-4 into main",
            "expected_key": StoryKeyRef(48, 4),
            "expected_shape": LandingEvidenceShape.TEMPLATED_MERGE_SUBJECT,
        },
        {
            "label": "land_branch_marshal_10_1",
            "project_slug": "pyforge-marshal",
            "template": template,
            "branch": "land/marshal-10-1-recovery",
            "expected_key": StoryKeyRef(10, 1),
            "expected_shape": LandingEvidenceShape.LAND_BRANCH_NAME,
        },
        {
            "label": "bmad_loop_branch",
            "project_slug": "pyforge-marshal",
            "template": template,
            "branch": "bmad-loop/20260803-023308-65b7/3-7-escalation-deferral-and-resume",
            "expected_key": StoryKeyRef(3, 7),
            "expected_shape": LandingEvidenceShape.BMAD_LOOP_BRANCH_NAME,
        },
        {
            "label": "station_branch",
            "project_slug": "pyforge-marshal",
            "template": template,
            "branch": "marshal/2-3-frozen-surface-scope-check",
            "expected_key": StoryKeyRef(2, 3),
            "expected_shape": LandingEvidenceShape.STATION_BRANCH_NAME,
        },
        {
            # Story 22.9: marshal's station-scoped dispatch branch.
            "label": "dispatch_branch",
            "project_slug": "pyforge-marshal",
            "template": template,
            "branch": "dispatch/pyforge-marshal/22.9",
            "expected_key": StoryKeyRef(22, 9),
            "expected_shape": LandingEvidenceShape.STATION_BRANCH_NAME,
        },
        {
            # The path that actually fires in this repo: `gh pr merge
            # --merge` renders GitHub's default subject around the branch.
            "label": "github_pr_merge_subject_dispatch_branch",
            "project_slug": "pyforge-marshal",
            "template": template,
            "subject": "Merge pull request #900 from rxm7706/dispatch/pyforge-marshal/22.9",
            "expected_key": StoryKeyRef(22, 9),
            "expected_shape": LandingEvidenceShape.GITHUB_PR_MERGE_SUBJECT,
        },
        {
            "label": "allowlist_accc097e6a",
            "project_slug": "pyforge-marshal",
            "template": template,
            "commit_sha": "accc097e6a",
            "subject": "Story 8.2: region parser -- span discovery, nesting rejection, fence awareness",
            "expected_key": StoryKeyRef(8, 2),
            "expected_shape": LandingEvidenceShape.RECOVERY_COMMIT_ALLOWLIST,
        },
        {
            "label": "allowlist_5290c9bcd2",
            "project_slug": "pyforge-marshal",
            "template": template,
            "commit_sha": "5290c9bcd2",
            "subject": "recover marshal 10-1 (Copier engine wrapper — the single seam)",
            "expected_key": StoryKeyRef(10, 1),
            "expected_shape": LandingEvidenceShape.RECOVERY_COMMIT_ALLOWLIST,
        },
        {
            "label": "allowlist_03d8fc8c86",
            "project_slug": "pyforge-mason",
            "template": template,
            "commit_sha": "03d8fc8c86",
            "subject": (
                "recover mason 3.7 (asymmetric receipts, partial failure and idempotence) "
                "from run 20260813-145934-3eb0's failed/ preserved patch"
            ),
            "expected_key": StoryKeyRef(3, 7),
            "expected_shape": LandingEvidenceShape.RECOVERY_COMMIT_ALLOWLIST,
        },
    )
