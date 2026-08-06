"""Story-spec promotion classification (Story 4.1, architecture spine
AD-4/AD-12/AD-13/AD-24/AD-29/AD-33) -- the pure core ``cli/deploy.py``'s
``marshal deploy promote`` delegates to for both halves of its job: which
stories are durable (``merged_story_keys``) and which Tier-3 spec
candidates should be promoted, skipped, or reported as a paper-trail gap
(``classify_promotion_candidates``).

Pure data only (AD-4): no I/O, no subprocess, no ``pathlib`` I/O methods,
no clock, no ``..adapters`` import. The impure edges -- reading Tier-3 spec
files and the tracked archive off disk, and calling
``VcsPort.commit_subjects``/``commit_paths`` -- live entirely in
``cli/deploy.py``.

Placement (per the story's own Code Map, which offers this as the
alternative to growing ``core/journal.py`` further): a new, small,
self-contained module rather than an addition to ``journal.py`` -- that
module is already 1000+ lines covering the run journal's write protocol,
fold, and frozen-surface accumulation, none of which this story's
promotion concern touches.

``merged_story_keys`` (AD-24, AD-33): the reachability predicate -- tries
THREE merge-subject shapes per subject, in order:

1. ``core.identity.parse_merge_subject(subject, template)`` -- the AD-24
   templated form (``"Merge {key} into main"``), for a future
   ``marshal land``-driven landing path. No landing path in THIS repo
   writes this form today.
2. ``extract_story_key_from_github_merge_subject`` (below) -- GitHub's own
   PR-merge subject, ``"Merge pull request #N from <owner>/<branch>"``,
   the shape every manually-branched story landing in this repo carries.
3. ``extract_story_key_from_bmadloop_merge_subject`` (below) -- bmad-loop's
   own native merge-commit shape, ``"Merge bmad-loop/<run-id>/<key>-<desc>
   into <branch> (bmad-loop)"``. Added as a post-merge finding while
   closing out Epic 2: five of its seven stories landed this way, via the
   shared ``loop/pyforge-marshal`` branch, and matched neither pattern 1
   nor 2 -- this repo (and every project in this factory) uses BOTH
   landing paths, not just one.

A subject that conforms to NEITHER pattern is skipped, never a hard
failure for the whole scan -- most commit subjects in any real repository
are not story merges (e.g. ``"fastmcp-v4"``, ``"pixi update requires-pixi
= \">=0.75.0\""``).

``SpecCandidate``/``PromotionPlan``/``classify_promotion_candidates``
(AD-12, AD-13, AD-29): partitions every discovered Tier-3 spec candidate
into ``to_promote`` (durable, not yet promoted, valid content) and
``gaps`` (a registered ``Finding`` per problem case -- missing spec for a
merged story, or an invalid/truncated spec). A not-yet-merged story's spec
is neither promoted nor a gap -- it is correctly not yet a candidate at all
(per the story's own I/O matrix: "Skipped -- not a promotion candidate
yet"), so it produces nothing in either bucket.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .identity import (
    MalformedStoryKeyError,
    MergeSubjectConformanceError,
    StoryKey,
    normalize,
    parse_merge_subject,
    render_filename_slug,
)
from .model import Finding, Severity

_MISSING_SPEC_CODE = "MRS-DEPLOY-001"
_INVALID_SPEC_CODE = "MRS-DEPLOY-002"

# GitHub's own PR-merge commit-subject shape -- "Merge pull request #N from
# <owner>/<branch>" -- the shape every real merge commit in THIS repo's
# history actually carries (verified live via `git log --merges` at the
# spec-amendment that added this function). `\S+` (not `[^/]+`) for the
# owner/branch prefix before the captured `branch` group: it is greedy, so
# it backtracks to the LAST `/` in the string, meaning `branch` already
# lands on the final path segment (e.g. "marshal/2-3-title" contributes
# just "2-3-title") without this regex needing to know how many slashes a
# real branch name carries.
_GITHUB_MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+ from \S+/(?P<branch>\S+)$")

# bmad-loop's own native merge-commit shape -- "Merge bmad-loop/<run-id>/
# <key>-<description> into <branch> (bmad-loop)" -- the shape every
# bmad-loop-driven story landing in this repo's history actually carries
# (verified live, post-merge finding while closing out Epic 2: 2.1/2.2/
# 2.4/2.5/2.6 all landed this way, via the shared `loop/pyforge-marshal`
# branch, and matched NEITHER of the two patterns above -- this repo uses
# both landing paths, manual `marshal/<key>-<desc>` branches AND bmad-loop
# runs, not just one). This is bmad-loop's own convention across every
# project in this factory (warden, herald, scribe, atlas all carry the
# identical shape in their own history), not something local to marshal.
_BMADLOOP_MERGE_SUBJECT_RE = re.compile(
    r"^Merge bmad-loop/\S+/(?P<key_slug>\S+) into (?P<target>\S+) \(bmad-loop\)$"
)


def extract_story_key_from_bmadloop_merge_subject(
    subject: str, project_slug: str
) -> StoryKey | None:
    """The third merge-subject pattern ``merged_story_keys`` tries: matches
    bmad-loop's own native merge-commit shape and parses the story key from
    the middle ``<key>-<description>`` segment (between the run-id and
    ``into``).

    ``project_slug`` is REQUIRED, not optional (live cross-project
    collision, found running this for real against local-recipes: this one
    repo hosts every BMAD project's loop-driven history in ONE shared `git
    log`, and pyforge-warden's own Story 6.8 -- "Merge bmad-loop/.../6-8-
    baseline-grandfathering into loop/pyforge-warden (bmad-loop)" -- was
    silently misread as pyforge-MARSHAL's own Story 6.8, reporting a false
    "merged but no spec" gap for a story that has nothing to do with this
    project at all). The merge target must equal ``loop/<project_slug>``
    -- this repo's own loop-home branch convention (confirmed live:
    `loop/pyforge-marshal`, `loop/pyforge-warden`, `loop/pyforge-herald`,
    `loop/pyforge-scribe` all follow it) -- or the subject is treated as
    NOT belonging to this project, same as any other non-matching subject.

    Same failure-tolerant shape as
    ``extract_story_key_from_github_merge_subject``: returns ``None``,
    never raises, for a non-matching subject, a wrong-project target, or a
    key segment whose leading token isn't a parseable story key."""
    match = _BMADLOOP_MERGE_SUBJECT_RE.match(subject)
    if match is None:
        return None
    if match.group("target") != f"loop/{project_slug}":
        return None
    try:
        return normalize(match.group("key_slug"))
    except MalformedStoryKeyError:
        return None


def extract_story_key_from_github_merge_subject(subject: str) -> StoryKey | None:
    """The second merge-subject pattern ``merged_story_keys`` tries (Story
    4.1's spec amendment, "TWO merge shapes, not one"): matches GitHub's own
    PR-merge subject shape and attempts to parse a story key out of the
    branch's final ``/``-separated path segment (this repo's own observed
    convention, ``marshal/<epic>-<seq>-<description>``).

    Returns ``None`` -- never raises -- for either failure mode: the
    subject doesn't match the GitHub shape at all, or the extracted
    segment's leading token isn't a parseable story key
    (``core.identity.normalize``'s ``MalformedStoryKeyError``, e.g. a
    branch like ``"marshal/refresh-dashboard-3-7"`` whose digits appear but
    not as the segment's LEADING token -- ``normalize()`` matches only at
    position 0, so this correctly does not extract ``3.7``). No new
    key-parsing logic: the extracted segment is handed straight to
    ``core.identity.normalize``, which already tolerates trailing
    descriptive text after the ``<epic>-<seq>`` token."""
    match = _GITHUB_MERGE_SUBJECT_RE.match(subject)
    if match is None:
        return None
    segment = match.group("branch").rsplit("/", 1)[-1]
    try:
        return normalize(segment)
    except MalformedStoryKeyError:
        return None


def _classify_merge_subject(subject: str, template: str, project_slug: str) -> StoryKey | None:
    """Try all three merge-subject patterns ``merged_story_keys`` recognizes,
    in order, returning the first match or ``None`` if none conform.
    Factored out so ``merged_story_keys`` (deduplicated by key) and
    ``count_conforming_subjects`` (a raw per-subject diagnostic count) share
    one classification, never copies that could silently diverge.
    ``project_slug`` scopes the bmad-loop pattern only (see
    ``extract_story_key_from_bmadloop_merge_subject``'s own docstring for
    why that scoping is required, not optional, in this shared-history
    repo)."""
    try:
        return parse_merge_subject(subject, template)
    except MergeSubjectConformanceError:
        pass
    key = extract_story_key_from_github_merge_subject(subject)
    if key is not None:
        return key
    return extract_story_key_from_bmadloop_merge_subject(subject, project_slug)


def merged_story_keys(
    subjects: tuple[str, ...], template: str, project_slug: str
) -> frozenset[StoryKey]:
    """Every ``StoryKey`` whose merge subject appears in ``subjects``
    (AD-24, AD-33): each subject is classified via
    ``_classify_merge_subject`` -- first the AD-24 templated form
    (``core.identity.parse_merge_subject``), then, if that doesn't conform,
    the GitHub PR-merge form, then bmad-loop's own native form (scoped to
    ``project_slug`` -- see that extractor's own docstring for the live
    cross-project collision this scoping prevents). A subject matching
    NONE of the three is silently skipped, never raised -- most of any
    real repository's commit history is not a story merge for THIS
    project. Pure: no I/O, no ``VcsPort`` -- ``subjects`` is the caller's
    already-gathered ``VcsPort.commit_subjects`` result."""
    keys: set[StoryKey] = set()
    for subject in subjects:
        key = _classify_merge_subject(subject, template, project_slug)
        if key is not None:
            keys.add(key)
    return frozenset(keys)


def count_conforming_subjects(subjects: tuple[str, ...], template: str, project_slug: str) -> int:
    """Diagnostic-only (Story 4.1 review fix): how many of ``subjects``
    conform to ANY merge-subject pattern ``merged_story_keys`` tries --
    a raw per-subject count, deliberately NOT deduplicated by key the way
    ``merged_story_keys``'s own ``frozenset`` result is. Exists so
    ``cli/deploy.py`` can report ``data.subjects_examined``/
    ``data.subjects_matched`` and an operator can tell "genuinely nothing
    has merged yet" apart from "the detection mechanism examined N commits
    and none of them conformed to any recognized pattern" -- a silent
    zero-vs-zero ambiguity a prior version of this run reported no way to
    distinguish."""
    return sum(
        1
        for subject in subjects
        if _classify_merge_subject(subject, template, project_slug) is not None
    )


@dataclass(frozen=True)
class SpecCandidate:
    """One Tier-3 spec-promotion candidate (Story 4.1): ``story_key``
    (parsed from its Tier-3 filename by the CLI boundary), ``path`` (the
    Tier-3 file's path, a plain ``str`` for reporting only -- this module
    holds no ``pathlib`` I/O, per AD-4), and ``text`` (the file's
    already-read content, or ``None`` when it could not be read at all --
    distinct from a present-but-invalid body, which reaches this dataclass
    as a non-``None`` string that ``classify_promotion_candidates`` then
    judges via ``is_valid_spec_text``)."""

    story_key: StoryKey
    path: str
    text: str | None


@dataclass(frozen=True)
class PromotionPlan:
    """The result of ``classify_promotion_candidates`` (Story 4.1):
    ``to_promote`` -- every ``SpecCandidate`` that is durable, not yet
    promoted, and carries valid content -- plus ``gaps``, one registered
    ``Finding`` per problem (a merged story with no Tier-3 spec at all, or
    one whose Tier-3 spec fails the minimal parse).

    ``missing_spec_keys`` (Story 4.2): the subset of ``gaps`` that are
    specifically "durable, no Tier-3 spec at all" (``MRS-DEPLOY-001``), as a
    structured ``frozenset[StoryKey]`` rather than something a caller would
    need to regex out of a ``Finding``'s human ``message``. Added for
    ``cli/deploy.py::unreachable_promotions_for_slug`` (Story 4.2's own
    "exactly one implementation of is this slug's story durable" reuse
    requirement, AD-24/AD-33): teardown's reachability check needs this
    same durable-with-no-spec-at-all set as a first-class value, not text to
    parse back out of a paper-trail message meant for humans.

    ``invalid_spec_keys`` (code review, 2026-08-06, P3): the subset of
    ``gaps`` that are specifically "durable, Tier-3 spec present but
    zero-byte/truncated" (``MRS-DEPLOY-002``). A corrupt or truncated
    paper trail is at least as concerning as a missing one -- a missing
    spec is unambiguous, a truncated one might carry partial, misleading
    content -- so ``unreachable_promotions_for_slug`` folds this set into
    the unreachable set alongside ``missing_spec_keys`` too (this
    DELIBERATELY widens Story 4.2's original Always bullet, which named
    only the missing-spec case; see this story's own Spec Change Log for
    the review finding that corrected it)."""

    to_promote: tuple[SpecCandidate, ...]
    gaps: tuple[Finding, ...]
    missing_spec_keys: frozenset[StoryKey] = frozenset()
    invalid_spec_keys: frozenset[StoryKey] = frozenset()


# A `status:` key at the LINE START of the frontmatter block, after
# stripping leading whitespace -- not a bare substring search anywhere in
# the block (review finding: the prior `"status:" in frontmatter` check
# matched a line like `substatus: draft` or the literal text `status:`
# inside a comment, neither of which is a real frontmatter key).
_STATUS_KEY_RE = re.compile(r"^status:\s")


def is_valid_spec_text(text: str | None) -> bool:
    """The minimal parse validation-before-promotion requires (AD-13):
    non-empty, and its frontmatter block (the leading ``---`` ... ``---``
    fence) carries a ``status:`` key -- matched as an actual frontmatter KEY
    (a line whose stripped text starts with ``status:``), never a bare
    substring anywhere in the block. Deliberately shallow -- this is a
    paper-trail smoke test proving the file is a real, non-truncated spec,
    not a schema validator. Reused by ``cli/deploy.py`` to judge a TRACKED
    archive copy's own validity too (a candidate is "already promoted" only
    when the tracked copy passes this same check -- a broken tracked copy
    never blocks re-promoting a good Tier-3 one, per AD-13's own "never
    promoted over a GOOD copy" wording, which implies a bad existing copy is
    not one)."""
    if text is None or not text.strip():
        return False
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    frontmatter = text[3:end]
    return any(_STATUS_KEY_RE.match(line.strip()) for line in frontmatter.splitlines())


def classify_promotion_candidates(
    candidates: tuple[SpecCandidate, ...],
    merged_keys: frozenset[StoryKey],
    already_promoted: frozenset[StoryKey],
) -> PromotionPlan:
    """Partition ``candidates`` against ``merged_keys`` (AD-33's git-truthful
    reachability answer) and ``already_promoted`` (the CLI boundary's own
    read of the tracked archive, per ``is_valid_spec_text`` above) into a
    ``PromotionPlan`` (AD-13, AD-29). Iterates over ``sorted(merged_keys)``
    -- deterministic output order for a deterministic input, never
    dict/set-iteration order -- and for each durable, not-yet-promoted key:

    - no matching Tier-3 candidate at all -> a ``MRS-DEPLOY-001`` gap
      (never silently passed over, per the story's own Always bullet);
    - a matching candidate whose content fails ``is_valid_spec_text`` -> a
      ``MRS-DEPLOY-002`` gap, and it is NEVER added to ``to_promote``
      (AD-13: a zero-byte/truncated source is reported, never promoted over
      a good copy);
    - otherwise -> added to ``to_promote``.

    A key present in ``candidates`` but absent from ``merged_keys``
    contributes nothing to either bucket -- it is correctly not yet a
    promotion candidate (the story's own I/O matrix: "not-yet-merged story,
    spec exists in Tier-3" -> "Skipped -- not a promotion candidate yet").
    """
    candidate_by_key: dict[StoryKey, SpecCandidate] = {
        candidate.story_key: candidate for candidate in candidates
    }

    to_promote: list[SpecCandidate] = []
    gaps: list[Finding] = []
    missing_spec_keys: set[StoryKey] = set()
    invalid_spec_keys: set[StoryKey] = set()
    for key in sorted(merged_keys):
        if key in already_promoted:
            continue
        candidate = candidate_by_key.get(key)
        if candidate is None:
            gaps.append(
                Finding(
                    code=_MISSING_SPEC_CODE,
                    severity=Severity.WARN,
                    message=(
                        f"story {key} is merged but no Tier-3 spec "
                        f"(spec-{render_filename_slug(key)}*.md) was found to promote"
                    ),
                    path=None,
                )
            )
            missing_spec_keys.add(key)
            continue
        if not is_valid_spec_text(candidate.text):
            gaps.append(
                Finding(
                    code=_INVALID_SPEC_CODE,
                    severity=Severity.WARN,
                    message=(
                        f"story {key}'s Tier-3 spec at {candidate.path!r} is "
                        "zero-byte or fails a minimal parse (missing "
                        "frontmatter or a status: key) -- not promoted"
                    ),
                    path=candidate.path,
                )
            )
            invalid_spec_keys.add(key)
            continue
        to_promote.append(candidate)

    return PromotionPlan(
        to_promote=tuple(to_promote),
        gaps=tuple(gaps),
        missing_spec_keys=frozenset(missing_spec_keys),
        invalid_spec_keys=frozenset(invalid_spec_keys),
    )
