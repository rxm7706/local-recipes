"""Unit tests for ``pyforge.marshal.seed.fs`` (Story 7.3) -- covers the
spec's I/O & Edge-Case Matrix: a plain no-match write, a direct never-write
hit, a symlink-indirect hit (proving resolution, not the raw path, drives
the match), an interrupted-write propagation proof, ``replace_span``'s
prefix/suffix preservation, ``replace_span``'s guard-before-any-read
ordering, ``NeverWrite``'s immutability (both reassignment and element
mutation), and ``remove`` refusing a never-write target.

Story 11.2 adds ``symlink()`` coverage: the guard trips on a never-write
``link_path`` (guards FIRST, before ``mkdir``), idempotence, an atomically
-proven stale-symlink replacement (no absence window), a named error on a
regular-file/directory collision, ``mkdir(parents=True)`` bootstrapping a
missing parent, and a proof that the guard checks ``link_path``'s own
location rather than a pre-existing symlink's current, resolved target.

Imports the module itself (``fs``), not its individual functions, so the
interrupted-write test can monkeypatch ``fs.atomic_write_bytes`` -- the
exact name ``write``/``replace_span`` reference in their own module
namespace, regardless of how a caller imports them.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.errors import NeverWriteViolation
from pyforge.marshal.seed.fs import NeverWrite

# --- NeverWrite shape / immutability: I/O Matrix row 7 ----------------------


def test_never_write_stores_its_patterns():
    never_write = NeverWrite(("a/*.md", "b/*.md"))
    assert never_write.patterns == ("a/*.md", "b/*.md")


def test_never_write_reassignment_raises_frozen_instance_error():
    never_write = NeverWrite(("a/*.md",))
    with pytest.raises(dataclasses.FrozenInstanceError):
        never_write.patterns = ("b/*.md",)  # type: ignore[misc]


def test_never_write_element_mutation_raises_type_error():
    """``patterns`` is a ``tuple`` -- already immutable on its own, so
    mutating an element raises independently of ``frozen=True``."""
    never_write = NeverWrite(("a/*.md", "b/*.md"))
    with pytest.raises(TypeError):
        never_write.patterns[0] = "c/*.md"  # type: ignore[index]


def test_never_write_constructed_with_a_list_is_coerced_to_a_tuple(tmp_path):
    """Review finding: a type hint alone is not runtime enforcement -- a
    caller passing a ``list`` would defeat element-level immutability
    silently without this coercion. Mirrors ``Manifest.never_write``'s own
    ``__post_init__`` precedent (Story 7.4)."""
    never_write = NeverWrite(["a/*.md", "b/*.md"])  # type: ignore[arg-type]
    assert never_write.patterns == ("a/*.md", "b/*.md")
    assert isinstance(never_write.patterns, tuple)
    with pytest.raises(TypeError):
        never_write.patterns[0] = "c/*.md"  # type: ignore[index]


def test_never_write_rejects_a_blank_pattern():
    with pytest.raises(ValueError):
        NeverWrite(("a/*.md", "   "))


def test_never_write_strips_padded_patterns_on_store():
    """Follow-up review finding: an earlier draft coerced list->tuple but
    forgot to strip, so a padded-but-non-blank pattern (a plausible YAML
    block-scalar typo) would pass validation yet never match any real,
    unpadded path -- silently protecting nothing. Mirrors
    ``Manifest.never_write``'s own strip-on-store behavior exactly."""
    never_write = NeverWrite((" docs/dreams/*.md ", "\tdocs/specs/*.md\n"))
    assert never_write.patterns == ("docs/dreams/*.md", "docs/specs/*.md")
    assert fs._matches(never_write, "docs/dreams/x.md") == "docs/dreams/*.md"


# --- NeverWrite.exempt: construction + validation (Story 10.8) -------------


def test_never_write_defaults_exempt_to_an_empty_frozenset():
    """Every pre-10.8 ``NeverWrite(...)`` construction (no ``exempt`` kwarg)
    must stay valid unchanged -- the spec's own I/O Matrix row."""
    never_write = NeverWrite(("a/*.md",))
    assert never_write.exempt == frozenset()


def test_never_write_stores_its_exempt_set():
    never_write = NeverWrite(patterns=(), exempt=frozenset({"docs/dreams/README.md"}))
    assert never_write.exempt == frozenset({"docs/dreams/README.md"})


def test_never_write_exempt_constructed_with_a_list_is_coerced_to_a_frozenset():
    """Mirrors ``patterns``' own list-coercion precedent -- a type hint alone
    is not runtime enforcement."""
    never_write = NeverWrite(patterns=(), exempt=["a.md", "b.md"])  # type: ignore[arg-type]
    assert never_write.exempt == frozenset({"a.md", "b.md"})
    assert isinstance(never_write.exempt, frozenset)


def test_never_write_exempt_constructed_with_a_set_is_coerced_to_a_frozenset():
    never_write = NeverWrite(patterns=(), exempt={"a.md", "b.md"})
    assert never_write.exempt == frozenset({"a.md", "b.md"})
    assert isinstance(never_write.exempt, frozenset)


def test_never_write_rejects_a_blank_exempt_entry():
    with pytest.raises(ValueError, match="NeverWrite.exempt"):
        NeverWrite(patterns=(), exempt=frozenset({"a.md", "   "}))


def test_never_write_strips_padded_exempt_entries_on_store():
    """Mirrors ``patterns``' own strip-on-store behavior (see
    ``test_never_write_strips_padded_patterns_on_store`` above)."""
    never_write = NeverWrite(patterns=(), exempt=frozenset({" docs/dreams/README.md "}))
    assert never_write.exempt == frozenset({"docs/dreams/README.md"})


# --- _matches: first-hit lookup ---------------------------------------------


def test_matches_returns_the_first_matching_pattern_in_order():
    never_write = NeverWrite(("docs/specs/*.md", "docs/dreams/*.md"))
    assert fs._matches(never_write, "docs/dreams/x.md") == "docs/dreams/*.md"


def test_matches_returns_none_when_nothing_matches():
    never_write = NeverWrite(("docs/specs/*.md",))
    assert fs._matches(never_write, "docs/dreams/x.md") is None


def test_matches_returns_none_for_an_empty_pattern_set():
    assert fs._matches(NeverWrite(()), "anything/at/all.md") is None


def test_matches_a_single_star_pattern_crosses_a_directory_separator():
    """The module's own design rationale: a single ``*`` (like ``**``)
    matches across ``/`` under ``fnmatch`` -- proving the "over-matching is
    the safe direction" claim rather than only asserting it (review
    finding: this was previously undemonstrated)."""
    never_write = NeverWrite(("docs/dreams/*.md",))
    assert fs._matches(never_write, "docs/dreams/sub/x.md") == "docs/dreams/*.md"


def test_matches_returns_none_for_an_exempt_path_that_matches_a_pattern():
    """The Story 10.8 short-circuit: an exempt path bypasses pattern
    matching entirely, even though it would otherwise match."""
    never_write = NeverWrite(("docs/dreams/*.md",), exempt=frozenset({"docs/dreams/README.md"}))
    assert fs._matches(never_write, "docs/dreams/README.md") is None


def test_matches_still_refuses_a_different_path_matching_the_same_pattern_when_not_exempt():
    """The other half of the same guarantee: exempting ONE path must not
    widen protection for every other path the pattern still covers."""
    never_write = NeverWrite(("docs/dreams/*.md",), exempt=frozenset({"docs/dreams/README.md"}))
    assert fs._matches(never_write, "docs/dreams/other.md") == "docs/dreams/*.md"


def test_matches_returns_none_for_an_exempt_path_even_when_named_by_an_exact_literal_pattern():
    """Review finding: the exempt short-circuit is unconditional -- by
    design, per the epics AC's own wording ("excluded from the set -- never
    in the set to begin with") -- so a manifest-declared writable path wins
    even when the colliding ``never_write`` entry is an EXACT literal path
    rather than a broad glob. A manifest author who names the same path in
    both ``never_write`` and as a writable artifact has authored a
    self-contradiction the manifest itself does not detect; this test pins
    the (deliberate) resolution: the writable declaration wins."""
    never_write = NeverWrite(("docs/dreams/README.md",), exempt=frozenset({"docs/dreams/README.md"}))
    assert fs._matches(never_write, "docs/dreams/README.md") is None


def test_matches_is_case_sensitive_regardless_of_platform():
    """Review finding: ``fnmatch.fnmatch`` case-folds via
    ``os.path.normcase`` on Windows and default-case-insensitive macOS
    filesystems, but not on Linux -- a platform-dependent SAFETY guard.
    ``fs._matches`` uses ``fnmatch.fnmatchcase`` specifically so this stays
    case-sensitive on every platform this package targets."""
    never_write = NeverWrite(("docs/dreams/*.md",))
    assert fs._matches(never_write, "Docs/Dreams/x.md") is None


# --- write: plain no-match write, I/O Matrix row 1 --------------------------


def test_write_with_no_match_creates_the_file_with_the_given_bytes(tmp_path):
    target = tmp_path / "README.md"

    fs.write(target, b"hi", repo_root=tmp_path, never_write=NeverWrite(()))

    assert target.read_bytes() == b"hi"


def test_write_with_no_match_overwrites_pre_existing_content_via_the_real_atomic_write(
    tmp_path,
):
    """Review finding: every prior "no-match write" test only exercised
    fresh-file creation. This drives the REAL (non-mocked)
    ``atomic_write_bytes`` against a file that already has different
    content, proving the overwrite -- not just the create path -- works
    end-to-end."""
    target = tmp_path / "README.md"
    target.write_bytes(b"old content")

    fs.write(target, b"new content", repo_root=tmp_path, never_write=NeverWrite(()))

    assert target.read_bytes() == b"new content"


# --- write: direct never-write hit, I/O Matrix row 2 ------------------------


def test_write_direct_never_write_hit_names_the_pattern_and_touches_nothing(tmp_path):
    target = tmp_path / "docs" / "dreams" / "x.md"
    never_write = NeverWrite(("docs/dreams/*.md",))

    with pytest.raises(NeverWriteViolation, match=r"docs/dreams/\*\.md"):
        fs.write(target, b"hi", repo_root=tmp_path, never_write=never_write)

    assert not target.exists()


def test_never_write_violation_message_names_both_the_given_and_resolved_path(tmp_path):
    """Follow-up review finding: the message previously showed only the
    caller-supplied path -- unhelpful for exactly the symlink-indirect
    case (below) where the resolved location, not the literal argument, is
    what actually matched."""
    target_dir = tmp_path / "_bmad-output" / "planning-artifacts"
    target_dir.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(target_dir)
    never_write = NeverWrite(("**/planning-artifacts/**",))

    with pytest.raises(NeverWriteViolation) as exc_info:
        fs.write(alias / "x.md", b"hi", repo_root=tmp_path, never_write=never_write)

    message = str(exc_info.value)
    assert "alias" in message
    assert "planning-artifacts" in message


# --- write: exempt bypasses a matching never-write pattern (Story 10.8) ----


def test_write_to_an_exempt_path_succeeds_despite_a_matching_never_write_pattern(tmp_path):
    """The literal regression this story fixes: a manifest-declared
    writable artifact (``copied-managed``/``copied-seeded``) whose own path
    also matches a broader deny glob must still be writable."""
    target = tmp_path / "docs" / "dreams" / "README.md"
    never_write = NeverWrite(("docs/dreams/*.md",), exempt=frozenset({"docs/dreams/README.md"}))

    fs.write(target, b"hi", repo_root=tmp_path, never_write=never_write)

    assert target.read_bytes() == b"hi"


def test_write_to_a_different_path_matching_the_same_pattern_is_still_refused(tmp_path):
    """The other half: exempting ``docs/dreams/README.md`` must not widen
    protection for every OTHER file ``docs/dreams/*.md`` still covers."""
    target = tmp_path / "docs" / "dreams" / "other.md"
    never_write = NeverWrite(("docs/dreams/*.md",), exempt=frozenset({"docs/dreams/README.md"}))

    with pytest.raises(NeverWriteViolation, match=r"docs/dreams/\*\.md"):
        fs.write(target, b"hi", repo_root=tmp_path, never_write=never_write)

    assert not target.exists()


# --- write: symlink-indirect hit, I/O Matrix row 3 --------------------------


def test_write_symlink_indirect_hit_proves_resolution_not_raw_path_drives_the_match(
    tmp_path,
):
    target_dir = tmp_path / "_bmad-output" / "planning-artifacts"
    target_dir.mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(target_dir)
    never_write = NeverWrite(("**/planning-artifacts/**",))

    raw_path = alias / "x.md"
    assert "planning-artifacts" not in str(raw_path)

    with pytest.raises(NeverWriteViolation):
        fs.write(raw_path, b"hi", repo_root=tmp_path, never_write=never_write)

    assert not (target_dir / "x.md").exists()


# --- write: interrupted write propagates unchanged, I/O Matrix row 4 -------


def test_write_propagates_atomic_write_bytes_failure_unchanged_and_original_survives(tmp_path, monkeypatch):
    """``atomic_write_bytes`` (Story 14.2) already has its own exhaustive
    coverage of temp-file cleanup and ``os.replace`` atomicity in
    ``pyforge-core``'s test suite -- re-deriving that here would duplicate
    it. Instead, this proves ``seed.fs.write``'s OWN contract: a failure
    from the delegate propagates completely unchanged (no wrapping into a
    ``SeedError`` leaf), and a pre-existing file is left exactly as it was
    (trivially true here since the guard already cleared and the mocked
    delegate never touches the filesystem at all)."""
    target = tmp_path / "existing.txt"
    target.write_bytes(b"original")

    def boom(path, data, *, mode=None):
        raise ValueError("mid-write failure")

    monkeypatch.setattr(fs, "atomic_write_bytes", boom)

    with pytest.raises(ValueError, match="mid-write failure"):
        fs.write(target, b"new", repo_root=tmp_path, never_write=NeverWrite(()))

    assert target.read_bytes() == b"original"


# --- replace_span: prefix/suffix preservation, I/O Matrix row 5 ------------


def test_replace_span_preserves_every_byte_outside_the_span(tmp_path):
    target = tmp_path / "region.md"
    target.write_bytes(b"AAAbodyBBB")

    fs.replace_span(target, 3, 7, b"NEW", repo_root=tmp_path, never_write=NeverWrite(()))

    result = target.read_bytes()
    assert result == b"AAANEWBBB"
    assert result[:3] == b"AAA"
    assert result[-3:] == b"BBB"


def test_replace_span_rejects_start_greater_than_end(tmp_path):
    target = tmp_path / "region.md"
    target.write_bytes(b"AAAbodyBBB")
    with pytest.raises(ValueError, match=r"invalid span"):
        fs.replace_span(target, 7, 3, b"NEW", repo_root=tmp_path, never_write=NeverWrite(()))
    assert target.read_bytes() == b"AAAbodyBBB"


def test_replace_span_rejects_a_negative_start(tmp_path):
    target = tmp_path / "region.md"
    target.write_bytes(b"AAAbodyBBB")
    with pytest.raises(ValueError, match=r"invalid span"):
        fs.replace_span(target, -1, 3, b"NEW", repo_root=tmp_path, never_write=NeverWrite(()))
    assert target.read_bytes() == b"AAAbodyBBB"


def test_replace_span_rejects_end_beyond_the_files_length(tmp_path):
    target = tmp_path / "region.md"
    target.write_bytes(b"AAAbodyBBB")
    with pytest.raises(ValueError, match=r"invalid span"):
        fs.replace_span(target, 3, 999, b"NEW", repo_root=tmp_path, never_write=NeverWrite(()))
    assert target.read_bytes() == b"AAAbodyBBB"


def test_replace_span_rejects_a_non_bytes_new_body(tmp_path):
    """Follow-up review finding: passing ``str`` (plausible -- "new region
    content" naturally starts life as text elsewhere) previously fell
    through to a bare, contextless ``TypeError`` from the splice
    expression itself. This now names the argument and its type upfront,
    before any file is even read."""
    target = tmp_path / "region.md"
    target.write_bytes(b"AAAbodyBBB")
    with pytest.raises(TypeError, match="new_body must be bytes"):
        fs.replace_span(
            target,
            3,
            7,
            "NEW",
            repo_root=tmp_path,
            never_write=NeverWrite(()),  # type: ignore[arg-type]
        )
    assert target.read_bytes() == b"AAAbodyBBB"


def test_replace_span_allows_a_zero_length_span_at_a_valid_position(tmp_path):
    """``start == end`` is a legitimate insertion point (e.g. a region whose
    ``begin``/``end`` markers sit on adjacent lines, per S-8.2's own
    zero-length-body case), not an invalid span."""
    target = tmp_path / "region.md"
    target.write_bytes(b"AAABBB")
    fs.replace_span(target, 3, 3, b"NEW", repo_root=tmp_path, never_write=NeverWrite(()))
    assert target.read_bytes() == b"AAANEWBBB"


def test_replace_span_supports_a_replacement_of_different_length(tmp_path):
    """The splice is not constrained to same-length substitution -- the
    reconstruction identity is ``data[:start] + new_body + data[end:]``,
    which naturally handles a shorter or longer replacement."""
    target = tmp_path / "region.md"
    target.write_bytes(b"AAAbodyBBB")

    fs.replace_span(
        target,
        3,
        7,
        b"a-much-longer-body",
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert target.read_bytes() == b"AAAa-much-longer-bodyBBB"


# --- replace_span: guard fires before any read, I/O Matrix row 6 ----------


def test_replace_span_guard_fires_before_any_read(tmp_path):
    """``target`` deliberately does not exist: if ``replace_span`` read
    before guarding, it would raise ``FileNotFoundError`` instead of
    ``NeverWriteViolation`` -- observing the latter proves the guard runs
    first and the file is never even opened."""
    target = tmp_path / "docs" / "dreams" / "x.md"
    never_write = NeverWrite(("docs/dreams/*.md",))

    with pytest.raises(NeverWriteViolation):
        fs.replace_span(target, 0, 0, b"new", repo_root=tmp_path, never_write=never_write)

    assert not target.exists()


# --- remove: never-write refusal, I/O Matrix row 8 --------------------------


def test_remove_on_a_never_write_path_raises_and_leaves_the_file_in_place(tmp_path):
    target = tmp_path / "docs" / "specs" / "x.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"keep me")
    never_write = NeverWrite(("docs/specs/*.md",))

    with pytest.raises(NeverWriteViolation, match=r"docs/specs/\*\.md"):
        fs.remove(target, repo_root=tmp_path, never_write=never_write)

    assert target.read_bytes() == b"keep me"


def test_remove_with_no_match_deletes_the_file(tmp_path):
    target = tmp_path / "scratch.txt"
    target.write_bytes(b"gone soon")

    fs.remove(target, repo_root=tmp_path, never_write=NeverWrite(()))

    assert not target.exists()


def test_remove_guard_fires_before_any_existence_check(tmp_path):
    """Mirrors ``replace_span``'s own guard-before-read proof: ``target``
    deliberately does not exist. If ``remove`` checked existence (or
    attempted the unlink) before guarding, it would raise
    ``FileNotFoundError`` instead of ``NeverWriteViolation`` (review
    finding: this symmetry was missing -- only ``write``/``replace_span``
    had it)."""
    target = tmp_path / "docs" / "dreams" / "x.md"
    never_write = NeverWrite(("docs/dreams/*.md",))

    with pytest.raises(NeverWriteViolation):
        fs.remove(target, repo_root=tmp_path, never_write=never_write)


def test_remove_on_a_missing_non_guarded_path_propagates_file_not_found_error(tmp_path):
    """Review finding: nothing previously proved a plain ``OSError`` from
    ``Path.unlink()`` propagates unchanged, despite the module docstring
    promising exactly that."""
    target = tmp_path / "does-not-exist.txt"
    with pytest.raises(FileNotFoundError):
        fs.remove(target, repo_root=tmp_path, never_write=NeverWrite(()))


# --- guard: repo-external fallback does not crash ---------------------------


def test_guard_falls_back_to_the_absolute_path_outside_repo_root_without_crashing(
    tmp_path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "x.md"

    fs.write(target, b"hi", repo_root=repo_root, never_write=NeverWrite(()))

    assert target.read_bytes() == b"hi"


def test_guard_matches_a_repo_external_target_via_the_absolute_posix_fallback(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "x.md"
    never_write = NeverWrite(("**/outside/*.md",))

    with pytest.raises(NeverWriteViolation):
        fs.write(target, b"hi", repo_root=repo_root, never_write=never_write)

    assert not target.exists()


def test_guard_rejects_a_nonexistent_repo_root(tmp_path):
    """Follow-up review finding: a wrong or misspelled ``repo_root``
    previously degraded every repo-relative pattern (the common case) to
    the absolute-path fallback, which cannot match it -- turning "deny"
    into a silent "allow". Failing loudly here converts a plausible
    misconfiguration into an immediate, diagnosable error."""
    target = tmp_path / "x.md"
    with pytest.raises(ValueError, match="does not resolve to an existing directory"):
        fs.write(
            target,
            b"hi",
            repo_root=tmp_path / "does-not-exist",
            never_write=NeverWrite(()),
        )
    assert not target.exists()


def test_guard_rejects_a_repo_root_that_is_a_file_not_a_directory(tmp_path):
    not_a_dir = tmp_path / "repo_root_file"
    not_a_dir.write_bytes(b"i am a file")
    target = tmp_path / "x.md"
    with pytest.raises(ValueError, match="does not resolve to an existing directory"):
        fs.write(target, b"hi", repo_root=not_a_dir, never_write=NeverWrite(()))


def test_guard_repo_relative_anchored_pattern_cannot_catch_a_repo_external_path(tmp_path):
    """Honest coverage of a known, accepted limitation (review finding):
    a `**`-prefixed pattern survives the repo-external fallback (see the
    test above), but a repo-root-anchored pattern like ``docs/dreams/*.md``
    -- the shape every real pattern in the shipped manifest actually uses
    for its non-`**` entries -- CANNOT match an absolute, repo-external
    path, because the fallback compares against the absolute string, not a
    repo-relative one. This does not fix the gap; it proves it exists
    exactly as documented, rather than only asserting so in prose. If a
    caller ever passes the wrong ``repo_root`` for an anchored pattern, the
    guard degrades silently -- callers MUST pass the correct repo root."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "x.md"
    never_write = NeverWrite(("x.md",))

    # If repo_root were correct (outside == repo_root), this pattern would
    # match "x.md" directly. With the WRONG repo_root, the fallback compares
    # the pattern against the absolute path instead, and the anchored
    # pattern cannot match it -- the write proceeds uncaught.
    fs.write(target, b"hi", repo_root=repo_root, never_write=never_write)
    assert target.read_bytes() == b"hi"


# --- integration: the REAL shipped manifest pattern set ---------------------

# Literally `never_write:` from `seed/templates/manifest.yaml` (Story 7.5,
# already shipped) -- follow-up review finding: every test above hand-built
# small, cosmetic patterns; nothing exercised the module's actual production
# input shape.
_REAL_NEVER_WRITE = NeverWrite(
    (
        "docs/dreams/*.md",
        "**/planning-artifacts/**",
        "**/implementation-artifacts/**",
        "docs/specs/*.md",
        "_bmad/bmm/**",
        "_bmad/core/**",
        "_bmad/skf/**",
    )
)


@pytest.mark.parametrize(
    "relative_target",
    [
        "docs/dreams/my-dream.md",
        "_bmad-output/planning-artifacts/PRD.md",
        "_bmad-output/projects/acme/implementation-artifacts/spec-1-1.md",
        "docs/specs/legacy-intake.md",
        "_bmad/bmm/config.yaml",
        "_bmad/core/agents/dev.md",
        "_bmad/skf/registry.json",
    ],
)
def test_write_refuses_every_category_the_real_shipped_manifest_protects(tmp_path, relative_target):
    target = tmp_path / relative_target
    with pytest.raises(NeverWriteViolation):
        fs.write(target, b"hi", repo_root=tmp_path, never_write=_REAL_NEVER_WRITE)
    assert not target.exists()


def test_write_with_the_real_shipped_manifest_still_allows_an_ordinary_target(tmp_path):
    target = tmp_path / "CLAUDE.md"
    fs.write(target, b"hi", repo_root=tmp_path, never_write=_REAL_NEVER_WRITE)
    assert target.read_bytes() == b"hi"


# --- symlink: guard, idempotence, atomic replace, collision (Story 11.2) ---


def test_symlink_guard_trips_on_a_never_write_link_path(tmp_path):
    """Guards FIRST, like ``write``/``replace_span``/``remove`` -- a
    matching ``link_path`` is refused before ``link_path.parent`` is even
    created."""
    link_path = tmp_path / "docs" / "dreams" / "x"
    never_write = NeverWrite(("docs/dreams/*",))
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    with pytest.raises(NeverWriteViolation):
        fs.symlink(link_path, target_dir, repo_root=tmp_path, never_write=never_write)

    assert not link_path.parent.exists()


def test_symlink_is_idempotent_when_already_pointing_at_the_correct_target(tmp_path, monkeypatch):
    link_path = tmp_path / "alias"
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    link_path.symlink_to(Path("target"))

    def boom(*args, **kwargs):
        raise AssertionError("os.replace must not be called for an idempotent no-op")

    monkeypatch.setattr(fs.os, "replace", boom)

    fs.symlink(link_path, Path("target"), repo_root=tmp_path, never_write=NeverWrite(()))

    assert link_path.readlink() == Path("target")


def test_symlink_idempotent_no_op_tolerates_an_absolute_vs_relative_spelling_difference(tmp_path, monkeypatch):
    """Design Notes' own claim: idempotence compares the RESOLVED target,
    not the raw string -- an existing absolute-spelled symlink already
    pointing at the same real location as a newly-requested RELATIVE
    target must also be recognized as already correct."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    link_path = tmp_path / "alias"
    link_path.symlink_to(target_dir)  # absolute spelling

    def boom(*args, **kwargs):
        raise AssertionError("os.replace must not be called for an idempotent no-op")

    monkeypatch.setattr(fs.os, "replace", boom)

    fs.symlink(link_path, Path("target"), repo_root=tmp_path, never_write=NeverWrite(()))

    assert Path(link_path.readlink()) == target_dir  # unchanged -- still absolute-spelled


def test_symlink_atomically_replaces_a_stale_symlink_with_no_absence_window(tmp_path, monkeypatch):
    """The atomic-replace claim, proven via an instrumented ``os.replace``
    call rather than only the end state (Task list's own wording): the OLD
    symlink must still be PRESENT at ``link_path`` the instant ``os.replace``
    is invoked -- proving no separate ``unlink()`` ran first and left a real
    absence window (the exact hazard CLAUDE.md's own marker/symlink desync
    incident documents)."""
    old_target = tmp_path / "old-target"
    old_target.mkdir()
    new_target = tmp_path / "new-target"
    new_target.mkdir()
    link_path = tmp_path / "alias"
    link_path.symlink_to(old_target)

    real_replace = fs.os.replace
    observed_present_before_replace = []

    def instrumented_replace(src, dst):
        observed_present_before_replace.append(Path(dst).is_symlink())
        real_replace(src, dst)

    monkeypatch.setattr(fs.os, "replace", instrumented_replace)

    fs.symlink(link_path, new_target, repo_root=tmp_path, never_write=NeverWrite(()))

    assert observed_present_before_replace == [True]
    assert Path(link_path.readlink()) == new_target


def test_symlink_raises_a_named_error_when_a_regular_file_occupies_link_path(tmp_path):
    link_path = tmp_path / "alias"
    link_path.write_text("real file, not a symlink", encoding="utf-8")
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    with pytest.raises(fs.SymlinkTargetOccupiedError):
        fs.symlink(link_path, target_dir, repo_root=tmp_path, never_write=NeverWrite(()))

    assert link_path.read_text(encoding="utf-8") == "real file, not a symlink"


def test_symlink_raises_a_named_error_when_a_real_directory_occupies_link_path(tmp_path):
    link_path = tmp_path / "alias"
    link_path.mkdir()
    (link_path / "keep.txt").write_text("real content", encoding="utf-8")
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    with pytest.raises(fs.SymlinkTargetOccupiedError):
        fs.symlink(link_path, target_dir, repo_root=tmp_path, never_write=NeverWrite(()))

    assert (link_path / "keep.txt").read_text(encoding="utf-8") == "real content"


def test_symlink_creates_a_missing_parent_directory(tmp_path):
    """``mkdir(parents=True, exist_ok=True)`` bootstraps a brand-new
    ``_bmad-output/`` that has no parent directory yet."""
    link_path = tmp_path / "_bmad-output" / "planning-artifacts"
    assert not link_path.parent.exists()

    fs.symlink(
        link_path,
        Path("projects/acme/planning-artifacts"),
        repo_root=tmp_path,
        never_write=NeverWrite(()),
    )

    assert link_path.parent.is_dir()
    assert link_path.readlink() == Path("projects/acme/planning-artifacts")


def test_symlink_guard_checks_the_links_own_path_not_a_preexisting_symlinks_current_target(
    tmp_path,
):
    """``resolve_leaf=False`` (see ``_guard``'s own docstring): the guard
    must evaluate ``link_path``'s own location, never dereference it if
    ``link_path`` already happens to be a symlink -- otherwise re-pointing a
    symlink that CURRENTLY points inside the never-write set would be
    refused even though ``link_path``'s own location never matched
    anything. If the guard instead resolved the leaf (following the
    pre-existing symlink to its current, protected target), this call would
    incorrectly raise ``NeverWriteViolation``."""
    protected = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    protected.mkdir(parents=True)
    link_path = tmp_path / "alias"
    link_path.symlink_to(protected / "nested")  # current target sits inside the protected set
    never_write = NeverWrite(("**/planning-artifacts/**",))

    fs.symlink(link_path, tmp_path / "somewhere-else", repo_root=tmp_path, never_write=never_write)

    assert Path(link_path.readlink()) == tmp_path / "somewhere-else"
