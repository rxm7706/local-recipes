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

``merged_story_keys`` (AD-24, AD-33; Story 20.10 / FR-191 CAP-3): the
reachability predicate -- classifies every subject via
``pyforge.core.landing_evidence``'s shared grammar (templated merge subject,
GitHub PR merge, bmad-loop merge, recovery commit, story-direct commit, and
``land/<station>-<epic>-<seq>`` branch names embedded in GitHub PR merge
subjects). A subject that matches none of those shapes is skipped, never a
hard failure for the whole scan -- most commit subjects in any real
repository are not story merges (e.g. ``"fastmcp-v4"``, ``"pixi update
requires-pixi = \">=0.75.0\""``).

``marshal_native_merged_keys`` (Story 5.9, AD-5/AD-24/AD-33): the SAME
reachability predicate narrowed to only the two Marshal-DRIVEN patterns
above (1 and 3) -- reused verbatim, never a fourth pattern-matcher. A key
``merged_story_keys`` finds but this function does not is labeled
``"not-loop-native"`` by ``cli/deploy.py::run_reconcile_completions`` --
NOT ``"bmad-quick-dev"`` (Spec Change Log, 2026-08-12): ``marshal land``
is ALSO Marshal-driven but its default merge strategy writes a
plain-PR-shaped subject byte-identical to a human's, so this predicate
cannot tell the two apart from git alone, and the reported label narrows
to what git alone actually proves. See that function's own docstring for
the full "why the templated form is Marshal-driven" rationale.

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

from pyforge.core.landing_evidence import (
    LandingEvidenceShape,
    StoryKeyRef,
    classify_branch_name,
    classify_commit,
    classify_merge_subject,
    parse_bmadloop_merge_subject,
    parse_github_pr_merge_subject,
)

from .identity import (
    MalformedStoryKeyError,
    StoryKey,
    normalize,
    render_filename_slug,
)
from .model import Finding, Severity

_MISSING_SPEC_CODE = "MRS-DEPLOY-001"
_INVALID_SPEC_CODE = "MRS-DEPLOY-002"

# GitHub PR-merge subject shape retained only to extract the ``branch``
# token for ``land/<station>-<epic>-<seq>`` recovery landings whose merge
# commit subject does not carry a station-prefixed branch segment --
# ``pyforge.core.landing_evidence.parse_github_pr_merge_subject`` handles
# the ordinary ``<station>/<key>-<desc>`` case inside the shared grammar.
_GITHUB_MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+ from \S+?/(?P<branch>\S+)$")

_MARSHAL_NATIVE_SHAPES = frozenset(
    {
        LandingEvidenceShape.TEMPLATED_MERGE_SUBJECT,
        LandingEvidenceShape.BMAD_LOOP_MERGE_SUBJECT,
    }
)


def _story_key_from_ref(ref: StoryKeyRef) -> StoryKey | None:
    try:
        return normalize(ref.dot_form())
    except MalformedStoryKeyError:
        return None


def extract_story_key_from_bmadloop_merge_subject(
    subject: str, project_slug: str
) -> StoryKey | None:
    """Delegate to ``pyforge.core.landing_evidence`` (Story 20.10).

    Preserved as a public surface for callers and tests that already import
    this name; returns ``None`` for any non-match, never raises."""
    ref = parse_bmadloop_merge_subject(subject, project_slug)
    if ref is None:
        return None
    return _story_key_from_ref(ref)


def extract_story_key_from_github_merge_subject(
    subject: str, project_slug: str
) -> StoryKey | None:
    """Delegate to ``pyforge.core.landing_evidence`` (Story 20.10).

    Preserved as a public surface for callers and tests that already import
    this name; returns ``None`` for any non-match, never raises."""
    ref = parse_github_pr_merge_subject(subject, project_slug)
    if ref is None:
        return None
    return _story_key_from_ref(ref)


def _classify_merge_subject(subject: str, template: str, project_slug: str) -> StoryKey | None:
    """Classify one commit subject via the shared landing-evidence grammar.

    After the grammar's own merge-subject shapes, also tries branch-name
    grammars on the branch token embedded in a GitHub PR merge subject --
    recovery landings via ``land/<station>-<epic>-<seq>`` branches carry
    that shape in the merge commit even though
    ``parse_github_pr_merge_subject`` scopes on ``<station>/`` prefixes."""
    match = classify_merge_subject(subject, template=template, project_slug=project_slug)
    if match is not None:
        return _story_key_from_ref(match.key)
    gh_match = _GITHUB_MERGE_SUBJECT_RE.match(subject)
    if gh_match is not None:
        branch_match = classify_branch_name(
            gh_match.group("branch"), project_slug=project_slug
        )
        if branch_match is not None:
            return _story_key_from_ref(branch_match.key)
    return None


def _classify_commit(sha: str, subject: str, template: str, project_slug: str) -> StoryKey | None:
    """``classify_commit`` at the Marshal ``StoryKey`` boundary."""
    match = classify_commit(sha, subject, template=template, project_slug=project_slug)
    if match is None:
        return None
    return _story_key_from_ref(match.key)


def merged_story_keys(
    subjects: tuple[str, ...],
    template: str,
    project_slug: str,
    *,
    commits: tuple[tuple[str, str], ...] = (),
) -> frozenset[StoryKey]:
    """Every ``StoryKey`` whose landing evidence appears in ``subjects`` or
    ``commits`` (Story 20.10 / FR-191 CAP-3).

    Each subject is classified via ``_classify_merge_subject``; each
    ``(sha, subject)`` pair in ``commits`` is additionally classified via
    ``pyforge.core.landing_evidence.classify_commit`` (the pre-convention
    recovery SHA allowlist lives there). A non-matching entry is silently
    skipped, never raised. Pure: no I/O, no ``VcsPort``."""
    keys: set[StoryKey] = set()
    for subject in subjects:
        key = _classify_merge_subject(subject, template, project_slug)
        if key is not None:
            keys.add(key)
    for sha, subject in commits:
        key = _classify_commit(sha, subject, template, project_slug)
        if key is not None:
            keys.add(key)
    return frozenset(keys)


def branch_story_merge_confirmed_by_grammar(
    branch: str,
    story_key: StoryKey,
    subjects: tuple[str, ...],
    template: str,
    project_slug: str,
    *,
    commits: tuple[tuple[str, str], ...] = (),
) -> bool:
    """Patch-id matching supplemented by the shared grammar (Story 20.10).

    ``True`` when ``story_key`` is durably merged on ``main`` per
    ``merged_story_keys`` AND ``branch`` names the same story via a
    recognized branch grammar (``land/…``, ``bmad-loop/…``, or
    ``<station>/…``). Used by ``marshal retire`` when
    ``VcsPort.is_branch_merged`` alone cannot confirm a recovered branch
    whose content-equivalence check fails but whose story demonstrably
    landed via the recovery convention."""
    merged = merged_story_keys(
        subjects, template, project_slug, commits=commits
    )
    if story_key not in merged:
        return False
    branch_match = classify_branch_name(branch, project_slug=project_slug)
    if branch_match is not None:
        key = _story_key_from_ref(branch_match.key)
        return key == story_key
    return False


def marshal_native_merged_keys(
    subjects: tuple[str, ...], template: str, project_slug: str
) -> frozenset[StoryKey]:
    """Story 5.9 ("a story finished by hand is not invisible to the
    ledger", AD-5/AD-24/AD-33): every ``StoryKey`` whose merge subject in
    ``subjects`` conforms to one of the TWO Marshal-DRIVEN merge-subject
    patterns -- the AD-24 templated form
    (``core.identity.parse_merge_subject``, ``deploy land-story``'s own
    rendered signature: that command resolves ``merge_subject_template``
    from policy and calls ``identity.render_merge_subject`` itself, so a
    merge landing this way was orchestrated BY Marshal) and bmad-loop's own
    native merge-commit form
    (``extract_story_key_from_bmadloop_merge_subject``, scoped to
    ``project_slug`` for the identical live cross-project-collision reason
    that function's own docstring documents in full) -- DELIBERATELY
    SKIPPING the third, GitHub-PR-merge pattern
    (``extract_story_key_from_github_merge_subject``) this module's own
    ``merged_story_keys`` also tries.

    Reuses BOTH helper functions VERBATIM (this story's own Boundaries: "no
    new regexes") -- this is not a fourth pattern-matcher, only a
    DIFFERENT, narrower subset of the same two functions ``merged_story_
    keys``/``_classify_merge_subject`` already call, tried in the SAME
    order (templated first, then bmad-loop-native): a subject conforming to
    the templated form is classified by it even though it happens to ALSO
    look github-shaped, mirroring ``_classify_merge_subject``'s own
    precedence.

    **Why the templated form counts as "Marshal-driven," not "not-loop-
    native"** (this story's own Design Notes, in full): the Dream's own
    framing is binary (bmad-loop vs. everything else), written before
    ``deploy land-story`` existed. ``land-story`` re-runs Marshal's own
    gate and renders the merge subject from policy -- Marshal orchestrated
    that merge, so grouping it with bmad-loop (both "Marshal already
    knows") against every other route is the accurate two-actor split, not
    a deviation from the AC's binary vocabulary.

    A key present in ``core.promotion.merged_story_keys``'s own (all-three-
    pattern) result but ABSENT from this function's result landed via a
    route Marshal itself did not drive -- reported as ``"not-loop-native"``
    (Spec Change Log, 2026-08-12), NOT ``"bmad-quick-dev"``: ``marshal
    land``'s own default merge strategy ALSO writes a plain-PR-shaped
    subject, byte-identical to a human's, so this function cannot tell a
    genuine ``bmad-quick-dev`` landing apart from a ``marshal land`` one
    from git alone, and the reported label narrows to what git alone
    actually proves rather than over-claiming which route it was -- which
    is exactly the set ``cli/deploy.py::run_reconcile_completions``
    computes (``merged_story_keys(...) - marshal_native_merged_keys(...)``,
    corroborated further by a valid Tier-3/tracked spec before ever
    triggering a write; see that function's own docstring).

    A subject matching NEITHER pattern is silently skipped, never raised --
    the identical failure-tolerant contract ``merged_story_keys`` already
    documents. Pure: no I/O, no ``VcsPort`` -- ``subjects`` is the caller's
    already-gathered ``VcsPort.commit_subjects`` result (the SAME tuple
    ``merged_story_keys``/``_scan_promotions`` already gathered -- never a
    second git read)."""
    keys: set[StoryKey] = set()
    for subject in subjects:
        match = classify_merge_subject(subject, template=template, project_slug=project_slug)
        if match is None or match.shape not in _MARSHAL_NATIVE_SHAPES:
            continue
        key = _story_key_from_ref(match.key)
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
