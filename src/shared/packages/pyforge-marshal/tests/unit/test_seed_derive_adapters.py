"""Unit tests for ``pyforge.marshal.seed.derive.adapters`` (Story 11.1) --
covers every row of the spec's I/O & Edge-Case Matrix: rendering
``cursor-rules``/``gemini-md``/``copilot-instructions`` from the shared
region fragments wrapped in tool-specific framing, determinism across
repeated renders, a mutation to a shared fragment propagating into all
three whole-file adapters AND ``AGENTS.md``'s own ``tiers`` region body (the
"single source of truth" claim, cross-checked against ``verbs.adopt``'s
REAL, untouched region-body mechanism -- never re-implemented here), a
fifth adapter added purely via a caller-supplied composition table (no
``adapters.py`` code change), and the two named error rows (an unknown
adapter id, a declared adapter with no wrapper template on disk).

Also exercises the REAL packaged ``seed/templates/files/*.j2`` fragments and
the three REAL wrapper templates this story ships (``template_path=None``),
mirroring ``test_seed_verbs_adopt.py``'s own "Build More Architect Dreams"
real-fragment-content assertion, and closes the loop with one integration
test through the REAL ``run_adopt`` composition: a ``generated-derived``
entry whose id is derive-composed gets its whole file overwritten with
composed content, while a ``hybrid-managed-region`` entry in the SAME run
gains a managed region and keeps its own pre-existing, repo-specific
content untouched -- never a whole-file overwrite for the hybrid case (the
epics AC's own explicit contrast).

Synthetic-template-tree convention mirrors ``test_seed_verbs_adopt.py``'s
own ``tempfile.mkdtemp()``/``write_text`` fixtures: real files on a real
``tmp_path``, never mocked I/O. The one real-git integration test mirrors
that file's ``_manifest``/``_generated_derived``/``_hybrid``/``_git``/
``_init_git_repo``/``clean_repo`` builders (each test file in this package
duplicates its own -- no shared ``conftest.py`` exists, matching every
sibling ``test_seed_verbs_*.py``'s own stated precedent)."""

from __future__ import annotations

import subprocess
from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed.derive.adapters import (
    ADAPTER_COMPOSITION,
    AdapterSpec,
    _read_fragment,
    render_adapter,
)
from pyforge.marshal.seed.errors import InternalError
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
    load_manifest,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.verbs.adopt import _region_body_from_template, run_adopt

_VERSION = ModelVersion.parse("1.0.0")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def template_root(tmp_path: Path) -> Path:
    """A synthetic template tree carrying the three shared region fragments
    and the three real whole-file wrapper templates this story ships,
    each with a distinct, greppable marker string per piece so a test can
    tell exactly which piece of content survived a render."""
    root = tmp_path / "template"
    files_dir = root / "files"
    _write(files_dir / "tiers.md.j2", "TIERS-FRAGMENT-V1\n")
    _write(files_dir / "portability-contract.md.j2", "PORTABILITY-FRAGMENT-V1\n")
    _write(files_dir / "dream-first-workflow.md.j2", "DREAM-FIRST-FRAGMENT-V1\n")
    _write(
        files_dir / "cursor-rules.mdc.j2",
        "---\ndescription: test\nalwaysApply: true\n---\n"
        "CURSOR-WRAPPER-PREAMBLE\n"
        "{{ tiers }}\n{{ portability-contract }}\n{{ dream-first-workflow }}\n",
    )
    _write(
        files_dir / "gemini-md.md.j2",
        "GEMINI-WRAPPER-PREAMBLE\n{{ tiers }}\n{{ portability-contract }}\n{{ dream-first-workflow }}\n",
    )
    _write(
        files_dir / "copilot-instructions.md.j2",
        "COPILOT-WRAPPER-PREAMBLE\n{{ tiers }}\n{{ portability-contract }}\n{{ dream-first-workflow }}\n",
    )
    return root


# --- rendering the three whole-file adapters from shared fragments ---------


@pytest.mark.parametrize(
    ("adapter_id", "preamble_marker"),
    [
        ("cursor-rules", "CURSOR-WRAPPER-PREAMBLE"),
        ("gemini-md", "GEMINI-WRAPPER-PREAMBLE"),
        ("copilot-instructions", "COPILOT-WRAPPER-PREAMBLE"),
    ],
)
def test_render_adapter_embeds_all_three_fragment_bodies_verbatim_in_tool_specific_framing(
    template_root, adapter_id, preamble_marker
):
    content = render_adapter(adapter_id, template_path=template_root)

    assert preamble_marker in content
    assert "TIERS-FRAGMENT-V1" in content
    assert "PORTABILITY-FRAGMENT-V1" in content
    assert "DREAM-FIRST-FRAGMENT-V1" in content


def test_render_adapter_cursor_rules_keeps_its_mdc_frontmatter_intact(template_root):
    content = render_adapter("cursor-rules", template_path=template_root)

    assert content.startswith("---\n")
    assert "alwaysApply: true" in content


def test_render_adapter_is_byte_identical_across_two_calls_with_unchanged_input(template_root):
    first = render_adapter("cursor-rules", template_path=template_root)
    second = render_adapter("cursor-rules", template_path=template_root)

    assert first == second


# --- single source of truth: a fragment mutation reaches every consumer ----


def test_mutating_the_shared_tiers_fragment_changes_all_three_whole_file_adapters_and_the_real_region_body(
    template_root,
):
    """The story's own central claim: one edit to ``tiers.md.j2`` changes
    ``cursor-rules``/``gemini-md``/``copilot-instructions`` AND ``AGENTS.md``'s
    own ``tiers`` region body on the next render -- the LAST of those four
    is exercised through ``verbs.adopt._region_body_from_template`` itself
    (the REAL, untouched production mechanism for ``AGENTS.md``/``CLAUDE.md``),
    not a re-implementation in this module, so this test proves the claim
    end to end rather than merely within ``derive.adapters`` alone.

    The other two fragments (``portability-contract``/``dream-first-
    workflow``) stay unchanged across the mutation -- proving the change is
    surgical, not an incidental full re-render of unrelated content."""
    before = {adapter_id: render_adapter(adapter_id, template_path=template_root) for adapter_id in ADAPTER_COMPOSITION}
    before_region = _region_body_from_template(template_root, "tiers")
    assert before_region == "TIERS-FRAGMENT-V1\n"

    (template_root / "files" / "tiers.md.j2").write_text("TIERS-FRAGMENT-V2\n", encoding="utf-8")

    after = {adapter_id: render_adapter(adapter_id, template_path=template_root) for adapter_id in ADAPTER_COMPOSITION}
    after_region = _region_body_from_template(template_root, "tiers")

    for adapter_id in ADAPTER_COMPOSITION:
        assert before[adapter_id] != after[adapter_id], adapter_id
        assert "TIERS-FRAGMENT-V1" not in after[adapter_id], adapter_id
        assert "TIERS-FRAGMENT-V2" in after[adapter_id], adapter_id
        # The other two fragments' content is untouched by this mutation.
        assert "PORTABILITY-FRAGMENT-V1" in after[adapter_id], adapter_id
        assert "DREAM-FIRST-FRAGMENT-V1" in after[adapter_id], adapter_id
    assert after_region == "TIERS-FRAGMENT-V2\n"
    assert before_region != after_region


# --- extensibility: a fifth adapter needs no adapters.py code change -------


def test_a_fifth_adapter_added_via_a_caller_supplied_composition_table_renders_correctly(
    template_root,
):
    """Adding a fifth adapter is "a manifest entry plus one new wrapper
    template file, no ``adapters.py`` logic change" (the epics AC). This
    test proves the mechanism is genuinely data-driven by supplying a WHOLE
    NEW composition table at the call site -- ``render_adapter`` itself is
    never edited to make this pass, and the module's own ``ADAPTER_
    COMPOSITION`` is asserted untouched afterward."""
    _write(
        template_root / "files" / "extra-adapter.md.j2",
        "EXTRA-WRAPPER-PREAMBLE\n{{ tiers }}\n",
    )
    composition = {
        **ADAPTER_COMPOSITION,
        "extra-adapter": AdapterSpec(fragments=("tiers",), wrapper="extra-adapter.md.j2"),
    }

    content = render_adapter("extra-adapter", template_path=template_root, composition=composition)

    assert "EXTRA-WRAPPER-PREAMBLE" in content
    assert "TIERS-FRAGMENT-V1" in content
    assert "extra-adapter" not in ADAPTER_COMPOSITION


# --- named errors: unknown adapter id, missing wrapper template ------------


def test_render_adapter_raises_a_named_internal_error_for_an_unknown_adapter_id(template_root):
    with pytest.raises(InternalError, match="bogus-adapter"):
        render_adapter("bogus-adapter", template_path=template_root)


def test_render_adapter_raises_a_named_internal_error_when_the_wrapper_template_is_missing(
    tmp_path,
):
    files_dir = tmp_path / "template" / "files"
    _write(files_dir / "tiers.md.j2", "TIERS-FRAGMENT-V1\n")
    _write(files_dir / "portability-contract.md.j2", "PORTABILITY-FRAGMENT-V1\n")
    _write(files_dir / "dream-first-workflow.md.j2", "DREAM-FIRST-FRAGMENT-V1\n")
    # Deliberately no cursor-rules.mdc.j2 written.

    with pytest.raises(InternalError, match="cursor-rules.mdc.j2"):
        render_adapter("cursor-rules", template_path=tmp_path / "template")


def test_render_adapter_raises_when_the_wrapper_template_references_an_unknown_placeholder(
    tmp_path,
):
    files_dir = tmp_path / "template" / "files"
    _write(files_dir / "tiers.md.j2", "TIERS-FRAGMENT-V1\n")
    _write(files_dir / "portability-contract.md.j2", "PORTABILITY-FRAGMENT-V1\n")
    _write(files_dir / "dream-first-workflow.md.j2", "DREAM-FIRST-FRAGMENT-V1\n")
    _write(files_dir / "cursor-rules.mdc.j2", "{{ tiers }}\n{{ not-a-real-fragment }}\n")

    with pytest.raises(InternalError, match="not-a-real-fragment"):
        render_adapter("cursor-rules", template_path=tmp_path / "template")


# --- _read_fragment: ambiguity + Jinja-injection guards ---------------------
# (mirrors verbs.adopt._region_body_from_template's own identical guards)


def test_read_fragment_raises_on_ambiguous_fragment_match(tmp_path):
    files_dir = tmp_path / "files"
    _write(files_dir / "tiers.md.j2", "body a\n")
    _write(files_dir / "tiers.txt.j2", "body b\n")

    with pytest.raises(InternalError, match="tiers"):
        _read_fragment(files_dir, "tiers")


def test_read_fragment_raises_on_jinja_syntax_in_fragment(tmp_path):
    files_dir = tmp_path / "files"
    _write(files_dir / "tiers.md.j2", "hello {{ mode }}\n")

    with pytest.raises(InternalError, match="Jinja"):
        _read_fragment(files_dir, "tiers")


# --- against the REAL packaged templates (template_path=None) --------------


@pytest.mark.parametrize("adapter_id", sorted(ADAPTER_COMPOSITION))
def test_render_adapter_against_the_real_packaged_templates_embeds_the_real_tier_table(
    adapter_id,
):
    """The real fragment content, not a fake body -- mirrors
    ``test_seed_verbs_adopt.py``'s own
    ``test_default_commit_materializes_a_hybrid_region_via_the_real_packaged_fragments``
    assertion verbatim."""
    content = render_adapter(adapter_id)

    assert "Build More Architect Dreams" in content
    assert "not locked to BMAD" in content
    assert "No non-trivial work without a Dream + spec" in content


def test_render_adapter_against_the_real_packaged_templates_is_deterministic():
    first = render_adapter("gemini-md")
    second = render_adapter("gemini-md")

    assert first == second


def test_gemini_md_rendered_tier_table_matches_agents_md_tiers_region_body_semantically():
    """The AC's own comparison: ``GEMINI.md``'s rendered tier table and
    ``AGENTS.md``'s own ``tiers`` region body must match -- same tiers, same
    paths, same git dispositions -- even though the wrapping prose differs.
    Both draw from the identical real ``tiers.md.j2`` fragment, so the
    region body's text is asserted to appear VERBATIM inside GEMINI.md's
    rendered content (a strictly stronger claim than "semantically
    equivalent")."""
    gemini_content = render_adapter("gemini-md")
    tiers_region_body = _region_body_from_template(None, "tiers")

    assert tiers_region_body in gemini_content


@pytest.mark.parametrize("adapter_id", sorted(ADAPTER_COMPOSITION))
def test_every_whole_file_adapter_embeds_the_real_tiers_region_body_verbatim(adapter_id):
    content = render_adapter(adapter_id)
    tiers_region_body = _region_body_from_template(None, "tiers")

    assert tiers_region_body in content


# --- ADAPTER_COMPOSITION stays honest against the real packaged manifest --
# (review finding: nothing previously tied the table's 3 hardcoded keys back
# to manifest.yaml's own entries, so a future rename would silently orphan
# a row here with no test noticing).


def test_every_adapter_composition_key_is_a_real_generated_derived_manifest_entry_with_no_regions():
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        manifest = load_manifest(manifest_path)
    entries_by_id = {entry.id: entry for entry in manifest.entries}

    for adapter_id in ADAPTER_COMPOSITION:
        entry = entries_by_id.get(adapter_id)
        assert entry is not None, f"{adapter_id!r} has no manifest entry"
        assert entry.artifact_class is ArtifactClass.GENERATED_DERIVED, adapter_id
        assert entry.regions == (), adapter_id


# --- real-git integration: run_adopt wires the derive-composed path in ----
# (Story 11.1's own new _default_commit branch, exercised end to end)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


def _unreachable_confirm() -> bool:
    raise AssertionError("confirm() should not have been called")


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=tuple(entries))


def test_run_adopt_writes_a_derive_composed_whole_file_and_a_managed_region_in_the_same_run(tmp_path, template_root):
    """End-to-end proof of the AC's own explicit contrast: a ``generated-
    derived`` entry whose id is derive-composed (``cursor-rules``) gets its
    whole file OVERWRITTEN with composed content, while a
    ``hybrid-managed-region`` entry in the SAME run gains a managed region
    via ``insert_region`` and keeps its OWN pre-existing, repo-specific
    prose byte-for-byte -- never a whole-file overwrite for the hybrid
    case."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "AGENTS.md").write_text("# My project\n\nSome existing repo-specific guidance.\n", encoding="utf-8")
    _commit_all(repo)

    manifest = _manifest(
        ManifestEntry(
            id="cursor-rules",
            artifact_class=ArtifactClass.GENERATED_DERIVED,
            path=".cursor/rules/specs.mdc",
            applies_to=AppliesTo.BOTH,
            rationale="test",
        ),
        ManifestEntry(
            id="agents-md-test",
            artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
            path="AGENTS.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
            format=RegionFormat.HTML,
            regions=(Region(name="tiers", anchor=("# My project",)),),
        ),
    )

    result = run_adopt(
        repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        template_path=template_root,
    )

    assert set(result.applied) == {"cursor-rules", "agents-md-test"}
    cursor_content = (repo / ".cursor" / "rules" / "specs.mdc").read_text(encoding="utf-8")
    assert "CURSOR-WRAPPER-PREAMBLE" in cursor_content
    assert "TIERS-FRAGMENT-V1" in cursor_content

    agents_content = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "Some existing repo-specific guidance." in agents_content
    assert "marshal-seed:begin region=tiers" in agents_content
    assert "TIERS-FRAGMENT-V1" in agents_content
