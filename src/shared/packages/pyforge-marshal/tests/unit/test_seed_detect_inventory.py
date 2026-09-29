"""Unit tests for ``pyforge.marshal.seed.detect.inventory`` (Stories 9.2 +
9.4 + 9.5) -- covers the spec's I/O & Edge-Case Matrix: absent/present
whole-file, referenced, every hybrid-managed-region outcome (region
found/missing, multi-region partial, malformed markers, path-is-a-directory,
non-UTF-8), the excluded-dir explicit-target carve-out, tree exclusion of
``.git``/``node_modules``/``.pixi``, gitignore negation and
nested-gitignore non-consultation, the ``0o555`` purity proof, (S-9.4) the
legacy short-circuit, ``Inventory.legacy``, ``effective_never_write``, and
``legacy_findings`` -- plus the "walked once" contract and the hand-rolled
matcher's leading-``/`` anchoring and ``**`` grammar -- and (S-9.5)
``coverage_findings``/``coverage_counts``'s two failure rules (an
unrecognized ``artifact_class`` force-set past ``ManifestEntry.__post_init__``,
and an ``unclassified-deferred`` entry with a blank ``rationale``) -- and
(S-10.8) ``writable_exemptions``'s own exempt-set computation: it includes
``copied-managed``/``copied-seeded`` entries, excludes every other class,
and subtracts a path that is also ``present-legacy`` (AD-59 still wins).
"""

from __future__ import annotations

import dataclasses
import os
import tempfile
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.findings import FindingType, Severity
from pyforge.marshal.seed.detect.inventory import (
    ArtifactState,
    Classification,
    Inventory,
    LegacyRecord,
    classify,
    coverage_counts,
    coverage_findings,
    effective_never_write,
    legacy_findings,
    writable_exemptions,
)
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)

_VERSION = ModelVersion.parse("1.0.0")


def _manifest(*entries: ManifestEntry, never_write: tuple[str, ...] = ()) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=never_write, entries=tuple(entries))


def _referenced(entry_id: str, path: str = "unused", *, legacy_of: str | None = None) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.REFERENCED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        pin=">=1.0",
        legacy_of=legacy_of,
    )


def _whole_file(
    entry_id: str, path: str, artifact_class: ArtifactClass, *, legacy_of: str | None = None
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=artifact_class,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        legacy_of=legacy_of,
    )


def _hybrid(
    entry_id: str,
    path: str,
    *region_names: str,
    fmt: RegionFormat = RegionFormat.HTML,
    legacy_of: str | None = None,
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=fmt,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
        legacy_of=legacy_of,
    )


def _doc(*lines: str) -> str:
    return "".join(f"{line}\n" for line in lines)


def _hybrid_text(name: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    body = "line1\n"
    sha = region_sha(body)
    return _doc("intro", render_begin(fmt, name, _VERSION, sha), "line1", render_end(fmt, name), "outro")


def _one(inventory: Inventory) -> Classification:
    (classification,) = inventory.classifications
    return classification


# --- ArtifactState shape -----------------------------------------------


def test_artifact_state_is_exactly_the_four_epics_ac_members():
    assert {member.value for member in ArtifactState} == {
        "absent",
        "present-conformant",
        "present-divergent",
        "present-legacy",
    }


# --- absent / present whole-file, referenced ----------------------------


def test_absent_whole_file_entry_is_absent(tmp_path):
    manifest = _manifest(_whole_file("a", "missing.txt", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.ABSENT)


def test_present_whole_file_entry_is_present_conformant(tmp_path):
    (tmp_path / "seeded.txt").write_text("hello\n")
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.PRESENT_CONFORMANT)


def test_referenced_entry_is_always_present_conformant_even_when_path_is_absent(tmp_path):
    manifest = _manifest(_referenced("dep", "does-not-exist"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="dep", state=ArtifactState.PRESENT_CONFORMANT)


@pytest.mark.parametrize(
    "artifact_class",
    [
        ArtifactClass.COPIED_MANAGED,
        ArtifactClass.COPIED_SEEDED,
        ArtifactClass.GENERATED_DERIVED,
        ArtifactClass.UNCLASSIFIED_DEFERRED,
    ],
)
def test_every_other_present_class_is_present_conformant_no_hash_check(tmp_path, artifact_class):
    (tmp_path / "target.txt").write_text("anything at all\n")
    manifest = _manifest(_whole_file("a", "target.txt", artifact_class))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.PRESENT_CONFORMANT)


def test_whole_file_entry_whose_path_is_a_directory_is_present_conformant(tmp_path):
    """The module docstring states a present directory is simply present
    for a whole-file class -- no recursive content comparison. Proven here
    directly, distinct from the hybrid-managed-region directory case
    (which is `present-divergent`, since a directory is never a readable
    region-bearing file)."""
    (tmp_path / "target_dir").mkdir()
    manifest = _manifest(_whole_file("a", "target_dir", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.PRESENT_CONFORMANT)


# --- hybrid-managed-region ------------------------------------------------


def test_hybrid_entry_with_absent_file_is_absent(tmp_path):
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.ABSENT)


def test_hybrid_entry_with_declared_region_found_is_present_conformant(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(_hybrid_text("tiers"))
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_CONFORMANT)


def test_hybrid_entry_with_declared_region_missing_is_present_divergent(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("no markers in this file at all\n")
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


def test_hybrid_entry_with_only_one_of_two_declared_regions_found_is_present_divergent(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(_hybrid_text("tiers"))
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers", "model-badge"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


def test_hybrid_entry_with_malformed_markers_is_present_divergent_not_raised(tmp_path):
    """``parse_regions`` raises ``RegionParseError`` for a stray end marker
    -- caught internally here, never propagated (the Always bullet's
    explicit list)."""
    (tmp_path / "CLAUDE.md").write_text(_doc("intro", render_end(RegionFormat.HTML, "tiers"), "outro"))
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


def test_hybrid_entry_whose_path_is_a_directory_is_present_divergent(tmp_path):
    (tmp_path / "CLAUDE.md").mkdir()
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


def test_hybrid_entry_with_non_utf8_content_is_present_divergent_not_raised(tmp_path):
    (tmp_path / "CLAUDE.md").write_bytes(b"\xff\xfe not valid utf-8 \x80")
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


def test_hybrid_entry_with_reserved_slashstar_format_is_present_divergent_not_raised(tmp_path):
    """``RegionFormat.SLASHSTAR`` is a real, ``ManifestEntry``-legal value
    that ``markers.parse_marker_line`` rejects with a bare
    ``NotImplementedError`` -- confirmed by review to otherwise crash
    ``classify()`` for the whole manifest instead of degrading like every
    sibling error path."""
    (tmp_path / "app.c").write_text("/* some C file */\n")
    manifest = _manifest(_hybrid("h", "app.c", "tiers", fmt=RegionFormat.SLASHSTAR))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


def test_hybrid_entry_with_invalid_marker_field_is_present_divergent_via_marker_error(tmp_path):
    """A line matching the marker delimiter shape and the ``marshal-seed:``
    tag but failing deeper grammar (an invalid sha) raises ``MarkerError``,
    not ``RegionParseError`` -- proving the other half of
    ``_classify_hybrid``'s except clause, previously untested."""
    (tmp_path / "CLAUDE.md").write_text(
        _doc(
            "intro",
            "<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=zzzzzzzz -->",
            "outro",
        )
    )
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_hybrid_entry_unreadable_file_is_present_divergent_not_raised(tmp_path):
    """A present-but-unreadable file raises ``OSError``/``PermissionError``
    from ``read_text`` -- confirmed by review to previously crash
    ``classify()`` instead of degrading, inconsistent with the sibling
    ``_load_gitignore_rules`` read's own ``OSError`` handling."""
    target = tmp_path / "CLAUDE.md"
    target.write_text(_hybrid_text("tiers"))
    target.chmod(0o000)
    try:
        manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
        inventory = classify(manifest, tmp_path)
    finally:
        target.chmod(0o644)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_DIVERGENT)


# --- path containment (never escape repo_root) ------------------------------


def test_entry_with_absolute_path_is_absent_never_reads_outside_repo(tmp_path):
    """``Path.__truediv__`` discards ``repo_root`` entirely when the right
    operand is absolute (documented ``pathlib`` behavior) -- confirmed by
    review to otherwise read an arbitrary host path. A real file OUTSIDE
    ``tmp_path`` proves the difference: without the guard this would read
    it and report ``present-conformant``."""
    with tempfile.TemporaryDirectory() as outside_dir:
        secret = Path(outside_dir) / "secret.txt"
        secret.write_text("outside the repo\n")
        manifest = _manifest(_whole_file("a", str(secret), ArtifactClass.COPIED_MANAGED))
        inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.ABSENT)


def test_entry_with_traversal_path_escaping_repo_root_is_absent(tmp_path):
    """A ``../``-relative path that resolves outside ``repo_root`` is the
    same escape as an absolute path, just spelled differently -- also
    guarded by ``_resolve_within_repo``."""
    with tempfile.TemporaryDirectory() as outside_dir:
        secret = Path(outside_dir) / "secret.txt"
        secret.write_text("outside the repo\n")
        relative_escape = os.path.relpath(secret, tmp_path)
        manifest = _manifest(_whole_file("a", relative_escape, ArtifactClass.COPIED_MANAGED))
        inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.ABSENT)


def test_entry_path_through_a_symlink_escaping_repo_root_is_absent(tmp_path):
    """A plain relative ``entry.path`` that resolves through an on-disk
    symlink pointing outside ``repo_root`` is a more realistic escape
    vector than a hand-crafted absolute/``../`` manifest string (a stray
    symlink checked into a repo) -- ``Path.resolve()`` follows it, so
    ``_resolve_within_repo``'s containment check already covers this, but
    it was previously unproven by a test."""
    with tempfile.TemporaryDirectory() as outside_dir:
        secret = Path(outside_dir) / "secret.txt"
        secret.write_text("outside the repo\n")
        link = tmp_path / "link.txt"
        link.symlink_to(secret)
        manifest = _manifest(_whole_file("a", "link.txt", ArtifactClass.COPIED_MANAGED))
        inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.ABSENT)


# --- excluded-dir carve-out / tree exclusion ------------------------------


def test_entry_path_inside_a_gitignored_directory_is_still_classified_by_real_presence(tmp_path):
    (tmp_path / ".gitignore").write_text("build/\n")
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "artifact.txt").write_text("hi\n")
    manifest = _manifest(_whole_file("a", "build/artifact.txt", ArtifactClass.GENERATED_DERIVED))

    inventory = classify(manifest, tmp_path)

    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.PRESENT_CONFORMANT)
    # The carve-out is per-ENTRY, not a re-inclusion -- the walked tree
    # itself still excludes the gitignored directory's contents.
    assert "build/artifact.txt" not in inventory.tree


@pytest.mark.parametrize("excluded_dir", [".git", "node_modules", ".pixi"])
def test_files_under_excluded_dir_names_are_absent_from_tree(tmp_path, excluded_dir):
    nested = tmp_path / excluded_dir / "sub"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("x\n")
    (tmp_path / "kept.txt").write_text("y\n")

    inventory = classify(_manifest(), tmp_path)

    assert not any(path.startswith(f"{excluded_dir}/") for path in inventory.tree)
    assert "kept.txt" in inventory.tree


@pytest.mark.parametrize("excluded_dir", [".git", "node_modules", ".pixi"])
def test_excluded_dir_names_are_pruned_at_any_depth_not_only_the_top(tmp_path, excluded_dir):
    nested = tmp_path / "a" / "b" / excluded_dir / "c"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("x\n")
    (tmp_path / "a" / "b" / "kept.txt").write_text("y\n")

    inventory = classify(_manifest(), tmp_path)

    assert not any(f"{excluded_dir}/" in path for path in inventory.tree)
    assert "a/b/kept.txt" in inventory.tree


# --- gitignore grammar -----------------------------------------------------


def test_gitignore_negation_is_last_match_wins(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n!keep.log\n")
    (tmp_path / "keep.log").write_text("keep\n")
    (tmp_path / "other.log").write_text("drop\n")

    inventory = classify(_manifest(), tmp_path)

    assert "keep.log" in inventory.tree
    assert "other.log" not in inventory.tree


def test_a_subdirectorys_own_gitignore_is_not_consulted(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / ".gitignore").write_text("x\n")
    (sub / "x").write_text("still tracked from the root's point of view\n")

    inventory = classify(_manifest(), tmp_path)

    assert "sub/x" in inventory.tree


def test_leading_slash_anchors_the_pattern_to_repo_root(tmp_path):
    (tmp_path / ".gitignore").write_text("/only-root.txt\n")
    (tmp_path / "only-root.txt").write_text("x\n")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "only-root.txt").write_text("y\n")

    inventory = classify(_manifest(), tmp_path)

    assert "only-root.txt" not in inventory.tree
    assert "sub/only-root.txt" in inventory.tree


def test_embedded_slash_anchors_the_pattern_even_without_a_leading_slash(tmp_path):
    """Real gitignore anchors a pattern to the ``.gitignore``'s own
    directory whenever it carries a ``/`` anywhere before the end -- not
    only a LEADING one. Confirmed by review: this repo's own root
    ``.gitignore`` pattern ``.idea/**/workspace.xml`` previously matched at
    ANY depth (e.g. ``sub/.idea/workspace.xml``), which real git would
    never exclude from a root ``.gitignore``."""
    (tmp_path / ".gitignore").write_text(".idea/**/workspace.xml\n")
    nested_idea = tmp_path / "sub" / ".idea"
    nested_idea.mkdir(parents=True)
    (nested_idea / "workspace.xml").write_text("z\n")

    inventory = classify(_manifest(), tmp_path)

    assert "sub/.idea/workspace.xml" in inventory.tree


def test_double_star_matches_across_slash_boundaries(tmp_path):
    """This repo's own root ``.gitignore`` uses exactly this shape
    (``.idea/**/workspace.xml``) -- proves both the zero-intermediate-dir
    case and a genuinely nested one."""
    (tmp_path / ".gitignore").write_text(".idea/**/workspace.xml\n")
    idea = tmp_path / ".idea"
    idea.mkdir()
    (idea / "workspace.xml").write_text("x\n")
    nested = idea / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "workspace.xml").write_text("y\n")
    (idea / "kept.xml").write_text("z\n")

    inventory = classify(_manifest(), tmp_path)

    assert ".idea/workspace.xml" not in inventory.tree
    assert ".idea/a/b/workspace.xml" not in inventory.tree
    assert ".idea/kept.xml" in inventory.tree


def test_trailing_double_star_matches_everything_inside_the_prefix(tmp_path):
    """A pattern shaped like ``build/**`` (a trailing ``**`` segment) is a
    very common real-world gitignore idiom -- confirmed by review to
    previously match NOTHING at all: the generated regex required the
    matched string to end in a literal ``/``, which no walked file path
    (or the bare directory itself) ever carries."""
    (tmp_path / ".gitignore").write_text("build/**\n")
    build_dir = tmp_path / "build"
    nested = build_dir / "sub"
    nested.mkdir(parents=True)
    (build_dir / "a.txt").write_text("x\n")
    (nested / "b.txt").write_text("y\n")

    inventory = classify(_manifest(), tmp_path)

    assert "build/a.txt" not in inventory.tree
    assert "build/sub/b.txt" not in inventory.tree


def test_bracket_character_class_excludes_matching_files(tmp_path):
    """This repo's own root ``.gitignore`` uses bracket expressions
    extensively (``*.py[cod]``, ``[Dd]ebug/``, dozens more) -- confirmed by
    review to previously match NOTHING: a blanket ``re.escape`` turned
    ``[cod]`` into a literal 5-character string no walked path ever
    carries, so every one of those exclusions silently excluded nothing at
    all."""
    (tmp_path / ".gitignore").write_text("*.py[cod]\n")
    (tmp_path / "mod.pyc").write_text("x\n")
    (tmp_path / "mod.pyo").write_text("y\n")
    (tmp_path / "mod.pyx").write_text("z\n")

    inventory = classify(_manifest(), tmp_path)

    assert "mod.pyc" not in inventory.tree
    assert "mod.pyo" not in inventory.tree
    assert "mod.pyx" in inventory.tree


def test_negated_bracket_character_class_excludes_non_matching_files(tmp_path):
    (tmp_path / ".gitignore").write_text("*.[!ch]\n")
    (tmp_path / "a.o").write_text("x\n")
    (tmp_path / "a.c").write_text("y\n")
    (tmp_path / "a.h").write_text("z\n")

    inventory = classify(_manifest(), tmp_path)

    assert "a.o" not in inventory.tree
    assert "a.c" in inventory.tree
    assert "a.h" in inventory.tree


def test_gitignore_with_only_comments_and_blank_lines_excludes_nothing(tmp_path):
    """A present ``.gitignore`` that yields zero rules after filtering
    comments/blank lines exercises a different branch than a missing
    ``.gitignore`` (the file read succeeds, but every line is skipped) --
    both must degrade to "nothing excluded"."""
    (tmp_path / ".gitignore").write_text("# just a comment\n\n   \n")
    (tmp_path / "kept.txt").write_text("x\n")

    inventory = classify(_manifest(), tmp_path)

    assert "kept.txt" in inventory.tree


# --- tree shape --------------------------------------------------------


def test_tree_contains_posix_relative_paths_of_every_walked_file(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b.txt").write_text("x\n")
    (tmp_path / "top.txt").write_text("y\n")

    inventory = classify(_manifest(), tmp_path)

    assert inventory.tree == frozenset({"a/b.txt", "top.txt"})


def test_classify_walks_the_tree_exactly_once(tmp_path, monkeypatch):
    import pyforge.marshal.seed.detect.inventory as inventory_module

    (tmp_path / "x.txt").write_text("x\n")
    calls: list[int] = []
    original_walk = os.walk

    def _counting_walk(*args, **kwargs):
        calls.append(1)
        yield from original_walk(*args, **kwargs)

    monkeypatch.setattr(inventory_module.os, "walk", _counting_walk)

    classify(_manifest(_whole_file("a", "x.txt", ArtifactClass.COPIED_SEEDED)), tmp_path)

    assert len(calls) == 1


# --- acceptance criteria ---------------------------------------------------


def test_empty_manifest_returns_empty_classifications_and_no_error(tmp_path):
    inventory = classify(_manifest(), tmp_path)
    assert inventory.classifications == ()
    assert isinstance(inventory, Inventory)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_classify_is_read_only_against_a_permission_locked_tree(tmp_path):
    """``classify()`` performs reads only (Always bullet): run it against a
    tree with write permission removed and confirm it completes without
    raising -- if it had attempted any write, the missing write permission
    on ``tmp_path`` would have raised ``PermissionError`` instead."""
    (tmp_path / ".gitignore").write_text("*.log\n")
    (tmp_path / "seeded.txt").write_text("hello\n")
    (tmp_path / "CLAUDE.md").write_text(_hybrid_text("tiers"))
    manifest = _manifest(
        _whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED),
        _hybrid("h", "CLAUDE.md", "tiers"),
        _referenced("dep"),
    )

    tmp_path.chmod(0o555)
    try:
        inventory = classify(manifest, tmp_path)
    finally:
        tmp_path.chmod(0o755)

    assert isinstance(inventory, Inventory)
    assert set(inventory.classifications) == {
        Classification(entry_id="a", state=ArtifactState.PRESENT_CONFORMANT),
        Classification(entry_id="h", state=ArtifactState.PRESENT_CONFORMANT),
        Classification(entry_id="dep", state=ArtifactState.PRESENT_CONFORMANT),
    }


# --- legacy convention detection (S-9.4) ------------------------------------


def test_present_legacy_whole_file_entry_is_present_legacy_with_one_legacy_record(tmp_path):
    (tmp_path / "old.txt").write_text("hand-authored\n")
    manifest = _manifest(_whole_file("a", "old.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.PRESENT_LEGACY)
    assert inventory.legacy == (LegacyRecord(entry_id="a", path="old.txt", legacy_of="succ"),)


def test_absent_legacy_of_entry_stays_absent_with_no_legacy_record(tmp_path):
    manifest = _manifest(_whole_file("a", "missing.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="a", state=ArtifactState.ABSENT)
    assert inventory.legacy == ()


def test_legacy_hybrid_entry_with_missing_region_is_present_legacy_not_divergent(tmp_path):
    """A ``hybrid-managed-region`` entry with a missing declared region would
    ordinarily be ``present-divergent`` (see the sibling
    ``test_hybrid_entry_with_declared_region_missing_is_present_divergent``)
    -- ``legacy_of`` short-circuits that structural check entirely, per
    AD-59's "never written to, never inspected" rule."""
    (tmp_path / "CLAUDE.md").write_text("no markers in this file at all\n")
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers", legacy_of="succ"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="h", state=ArtifactState.PRESENT_LEGACY)
    assert inventory.legacy == (LegacyRecord(entry_id="h", path="CLAUDE.md", legacy_of="succ"),)


def test_referenced_entry_with_legacy_of_set_is_still_present_conformant(tmp_path):
    """``referenced`` is never materialized -- ``legacy_of`` is never
    consulted for this class, regardless of whether it is set."""
    manifest = _manifest(_referenced("dep", "does-not-exist", legacy_of="succ"))
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="dep", state=ArtifactState.PRESENT_CONFORMANT)
    assert inventory.legacy == ()


def test_canonical_specs_dir_legacy_worked_example(tmp_path):
    """The AD-59 / epics AC canonical worked example, proven via a
    self-contained fixture using the real manifest's own id AND class for
    ``specs-dir-legacy`` (``templates/manifest.yaml``'s ``generated-derived``,
    not an arbitrary stand-in) -- never by editing the shipped manifest
    itself (see the spec's Design Notes)."""
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    manifest = _manifest(
        _whole_file(
            "specs-dir-legacy",
            "docs/specs/",
            ArtifactClass.GENERATED_DERIVED,
            legacy_of="planning-artifacts-symlink",
        )
    )
    inventory = classify(manifest, tmp_path)
    assert _one(inventory) == Classification(entry_id="specs-dir-legacy", state=ArtifactState.PRESENT_LEGACY)
    (finding,) = legacy_findings(inventory)
    assert finding.severity == Severity.INFO
    assert finding.type == FindingType.LEGACY_PRESENT
    assert finding.path == "docs/specs/"
    assert finding.message == ("docs/specs/: superseded by 'planning-artifacts-symlink'; preserved, never modified")


def test_manifest_with_no_legacy_entries_yields_empty_legacy_and_empty_findings(tmp_path):
    (tmp_path / "seeded.txt").write_text("hello\n")
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    assert inventory.legacy == ()
    assert legacy_findings(inventory) == ()


def test_effective_never_write_unions_manifest_patterns_with_legacy_paths(tmp_path):
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    manifest = _manifest(
        _whole_file("specs-dir-legacy", "docs/specs/", ArtifactClass.COPIED_MANAGED, legacy_of="succ"),
        never_write=("a/*",),
    )
    inventory = classify(manifest, tmp_path)
    assert effective_never_write(manifest, inventory) == frozenset({"a/*", "docs/specs/"})


def test_effective_never_write_dedupes_when_legacy_path_already_in_never_write(tmp_path):
    """The union is a real set union, not a naive concatenation -- a legacy
    path already named in the manifest's own ``never_write`` must not appear
    twice or otherwise change the result's membership."""
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    manifest = _manifest(
        _whole_file("specs-dir-legacy", "docs/specs/", ArtifactClass.COPIED_MANAGED, legacy_of="succ"),
        never_write=("docs/specs/", "b/*"),
    )
    inventory = classify(manifest, tmp_path)
    assert effective_never_write(manifest, inventory) == frozenset({"docs/specs/", "b/*"})


def test_writable_exemptions_includes_copied_managed_and_copied_seeded_entries(tmp_path):
    """The epics AC's own two named classes -- both draw straight from
    ``manifest.entries``, regardless of whether the path exists on disk (see
    ``writable_exemptions``'s own docstring: the ordinary "create it for the
    first time" case is exactly the shape this exists to unblock)."""
    manifest = _manifest(
        _whole_file("dreams-readme", "docs/dreams/README.md", ArtifactClass.COPIED_MANAGED),
        _whole_file("specs-readme", "specs/README.md", ArtifactClass.COPIED_SEEDED),
    )
    inventory = classify(manifest, tmp_path)
    assert writable_exemptions(manifest, inventory) == frozenset({"docs/dreams/README.md", "specs/README.md"})


def test_writable_exemptions_excludes_every_other_artifact_class(tmp_path):
    """``referenced``/``generated-derived``/``hybrid-managed-region``/
    ``unclassified-deferred`` are never exempted this way -- only the two
    named classes above are."""
    manifest = _manifest(
        _referenced("ref"),
        _whole_file("derived", "derived.txt", ArtifactClass.GENERATED_DERIVED),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
        _whole_file("deferred", "deferred.txt", ArtifactClass.UNCLASSIFIED_DEFERRED),
    )
    inventory = classify(manifest, tmp_path)
    assert writable_exemptions(manifest, inventory) == frozenset()


def test_writable_exemptions_subtracts_a_path_that_is_also_present_legacy(tmp_path):
    """AD-59 still wins: a path recognized as ``present-legacy`` is never
    exempted, even though its own entry is a ``copied-managed`` class that
    would otherwise qualify -- the spec's own I/O Matrix row."""
    (tmp_path / "docs" / "dreams").mkdir(parents=True)
    (tmp_path / "docs" / "dreams" / "README.md").write_text("x\n", encoding="utf-8")
    manifest = _manifest(
        _whole_file(
            "dreams-readme",
            "docs/dreams/README.md",
            ArtifactClass.COPIED_MANAGED,
            legacy_of="succ",
        )
    )
    inventory = classify(manifest, tmp_path)
    assert inventory.legacy == (LegacyRecord(entry_id="dreams-readme", path="docs/dreams/README.md", legacy_of="succ"),)
    assert writable_exemptions(manifest, inventory) == frozenset()


def test_multiple_legacy_entries_yield_records_and_findings_in_manifest_order(tmp_path):
    (tmp_path / "first.txt").write_text("x\n")
    (tmp_path / "second.txt").write_text("y\n")
    manifest = _manifest(
        _whole_file("a", "first.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ-a"),
        _whole_file("b", "second.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ-b"),
    )
    inventory = classify(manifest, tmp_path)
    assert inventory.legacy == (
        LegacyRecord(entry_id="a", path="first.txt", legacy_of="succ-a"),
        LegacyRecord(entry_id="b", path="second.txt", legacy_of="succ-b"),
    )
    findings = legacy_findings(inventory)
    assert len(findings) == 2
    assert all(finding.severity == Severity.INFO for finding in findings)
    assert all(finding.type == FindingType.LEGACY_PRESENT for finding in findings)
    assert [finding.path for finding in findings] == ["first.txt", "second.txt"]


def test_legacy_records_ordered_correctly_when_interleaved_with_non_legacy_entries(tmp_path):
    """`Inventory.legacy` must reflect manifest entry order among LEGACY
    entries specifically, even when non-legacy entries are interleaved
    between them -- proving `classify()` filters by state rather than
    coincidentally preserving order because every entry in the manifest
    happened to be legacy (see the sibling all-legacy ordering test)."""
    (tmp_path / "first.txt").write_text("x\n")
    (tmp_path / "middle.txt").write_text("m\n")
    (tmp_path / "second.txt").write_text("y\n")
    manifest = _manifest(
        _whole_file("a", "first.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ-a"),
        _whole_file("mid", "middle.txt", ArtifactClass.COPIED_SEEDED),
        _whole_file("b", "second.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ-b"),
    )
    inventory = classify(manifest, tmp_path)
    assert inventory.legacy == (
        LegacyRecord(entry_id="a", path="first.txt", legacy_of="succ-a"),
        LegacyRecord(entry_id="b", path="second.txt", legacy_of="succ-b"),
    )
    assert inventory.classifications == (
        Classification(entry_id="a", state=ArtifactState.PRESENT_LEGACY),
        Classification(entry_id="mid", state=ArtifactState.PRESENT_CONFORMANT),
        Classification(entry_id="b", state=ArtifactState.PRESENT_LEGACY),
    )


# --- frozen dataclass conventions ------------------------------------------


def test_classification_is_frozen_and_hashable():
    classification = Classification(entry_id="a", state=ArtifactState.ABSENT)
    with pytest.raises(dataclasses.FrozenInstanceError):
        classification.state = ArtifactState.PRESENT_CONFORMANT  # type: ignore[misc]
    assert isinstance(hash(classification), int)


def test_legacy_record_is_frozen_and_hashable():
    record = LegacyRecord(entry_id="a", path="old.txt", legacy_of="succ")
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.path = "new.txt"  # type: ignore[misc]
    assert isinstance(hash(record), int)


def test_inventory_is_frozen(tmp_path):
    inventory = classify(_manifest(), tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        inventory.tree = frozenset()  # type: ignore[misc]


def test_inventory_is_hashable(tmp_path):
    inventory = classify(_manifest(), tmp_path)
    assert isinstance(hash(inventory), int)


# --- manifest coverage (S-9.5) ----------------------------------------------
#
# `coverage_findings`/`coverage_counts` are pure over `Manifest` alone -- no
# `repo_root`/`classify()` involved, so none of these tests need `tmp_path`
# (the module docstring's own boundary: coverage is intrinsic to the
# manifest, not a property of the target repo).


def test_coverage_findings_returns_empty_tuple_when_every_entry_is_validly_classed():
    """Mix of all 6 real classes; the ``unclassified-deferred`` entry carries
    a real rationale (`_whole_file`'s own default, ``"test"``)."""
    manifest = _manifest(
        _referenced("dep"),
        _whole_file("a", "a.txt", ArtifactClass.COPIED_MANAGED),
        _whole_file("b", "b.txt", ArtifactClass.COPIED_SEEDED),
        _whole_file("c", "c.txt", ArtifactClass.GENERATED_DERIVED),
        _hybrid("h", "h.txt", "region-one"),
        _whole_file("d", "d.txt", ArtifactClass.UNCLASSIFIED_DEFERRED),
    )
    assert coverage_findings(manifest) == ()
    assert coverage_counts(manifest) == {
        "referenced": 1,
        "copied-managed": 1,
        "copied-seeded": 1,
        "generated-derived": 1,
        "hybrid-managed-region": 1,
        "unclassified-deferred": 1,
    }
    assert sum(coverage_counts(manifest).values()) == len(manifest.entries)


def test_coverage_findings_flags_an_entry_forced_to_an_invalid_artifact_class():
    """``artifact_class`` force-set (``object.__setattr__``) past
    ``ManifestEntry.__post_init__`` to a raw string outside ``ArtifactClass``
    -- the otherwise-unreachable branch this story's defensive re-check
    exists to catch (`test_seed_model_version.py`'s identical idiom)."""
    entry = _whole_file("a", "a.txt", ArtifactClass.COPIED_MANAGED)
    object.__setattr__(entry, "artifact_class", "not-a-real-class")
    manifest = _manifest(entry)

    (finding,) = coverage_findings(manifest)
    assert finding.severity == Severity.HARD
    assert finding.type == FindingType.UNCOVERED
    assert finding.path == "a.txt"
    assert finding.message == "a: artifact_class 'not-a-real-class' is not a valid ArtifactClass member"
    assert coverage_counts(manifest) == {"uncovered": 1}


def test_coverage_findings_flags_a_deferred_entry_with_a_forced_blank_rationale():
    entry = _whole_file("a", "a.txt", ArtifactClass.UNCLASSIFIED_DEFERRED)
    object.__setattr__(entry, "rationale", "   ")
    manifest = _manifest(entry)

    (finding,) = coverage_findings(manifest)
    assert finding.severity == Severity.HARD
    assert finding.type == FindingType.UNCOVERED
    assert finding.path == "a.txt"
    assert finding.message == "a: unclassified-deferred entry has a blank rationale"
    assert coverage_counts(manifest) == {"uncovered": 1}


def test_coverage_findings_flags_a_deferred_entry_with_a_forced_non_str_rationale():
    """``rationale`` force-set to ``None`` -- `_uncovered_reason` guards this
    field with the same ``isinstance`` discipline as ``artifact_class``, so a
    non-``str`` value is reported as ``uncovered`` rather than raising
    ``AttributeError`` out of a bare ``.strip()`` call."""
    entry = _whole_file("a", "a.txt", ArtifactClass.UNCLASSIFIED_DEFERRED)
    object.__setattr__(entry, "rationale", None)
    manifest = _manifest(entry)

    (finding,) = coverage_findings(manifest)
    assert finding.severity == Severity.HARD
    assert finding.type == FindingType.UNCOVERED
    assert finding.path == "a.txt"
    assert finding.message == "a: unclassified-deferred entry has a blank rationale"
    assert coverage_counts(manifest) == {"uncovered": 1}


def test_coverage_findings_passes_a_deferred_entry_with_a_real_rationale():
    manifest = _manifest(_whole_file("a", "a.txt", ArtifactClass.UNCLASSIFIED_DEFERRED))
    assert coverage_findings(manifest) == ()
    assert coverage_counts(manifest) == {"unclassified-deferred": 1}


def test_coverage_findings_reports_two_uncovered_entries_in_manifest_order():
    """Two entries fail coverage for DIFFERENT reasons -- proves the
    ordering is manifest entry order, not e.g. failure-reason grouping, and
    that a passing entry between them is simply excluded (never a
    placeholder)."""
    invalid_class_entry = _whole_file("a", "a.txt", ArtifactClass.COPIED_MANAGED)
    object.__setattr__(invalid_class_entry, "artifact_class", "bogus")
    ok_entry = _whole_file("mid", "mid.txt", ArtifactClass.COPIED_SEEDED)
    blank_rationale_entry = _whole_file("b", "b.txt", ArtifactClass.UNCLASSIFIED_DEFERRED)
    object.__setattr__(blank_rationale_entry, "rationale", "")
    manifest = _manifest(invalid_class_entry, ok_entry, blank_rationale_entry)

    findings = coverage_findings(manifest)
    assert [finding.path for finding in findings] == ["a.txt", "b.txt"]
    assert all(finding.severity == Severity.HARD for finding in findings)
    assert all(finding.type == FindingType.UNCOVERED for finding in findings)
    assert coverage_counts(manifest) == {"uncovered": 2, "copied-seeded": 1}
    assert sum(coverage_counts(manifest).values()) == len(manifest.entries)


def test_coverage_findings_and_counts_on_an_empty_manifest():
    manifest = _manifest()
    assert coverage_findings(manifest) == ()
    assert coverage_counts(manifest) == {}
