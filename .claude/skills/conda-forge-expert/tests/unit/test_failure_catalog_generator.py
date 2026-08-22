"""Fixture tests for failure_catalog_generator.py (Story 7.1).

Pattern: importlib load of the canonical script (see test_cwe_seed_gap.py),
exercised against a small inline SKILL.md-shaped fixture string — NOT the
real 4200-line SKILL.md. Fully offline, no network.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"

# A small SKILL.md-shaped fixture covering every extraction case the spec
# calls out: a real enforced code, no code mention at all, a stale/
# nonexistent code, two DIFFERENT codes in one body (ambiguity -> null),
# and a Question/Answer-shaped entry with no **Symptom**: label at all
# (the fallback-to-whole-body-scan path).
FIXTURE_SKILL_MD = '''# A Fixture Skill

Some unrelated front matter.

## Recipe Authoring Gotchas

Patterns that look right but fail silently.

### G1. First gotcha with a real enforced code

**Symptom**: something fails with "boom error" and `some code`.

**Why**: reasons.

**Fix**: use X. The optimizer's **REAL-001** check flags this.

### G2. Second gotcha with no code mention at all

**Symptom**: something else fails with `another code`.

**Why**: reasons.

**Fix**: do Y.

### G3. Third gotcha mentioning a stale/nonexistent code

**Symptom**: fails with "stale error".

**Why**: reasons.

**Fix**: do Z. The optimizer's **FAKE-999** check flags this.

### G4. Fourth gotcha with the phrase pointing at two different codes

**Symptom**: fails with "ambiguous error".

**Why**: reasons.

**Fix**: The optimizer's **REAL-001** check flags this. The optimizer's **REAL-002** check also flags a related issue.

### G5. Fifth gotcha with no Symptom label at all

**Question**: what happens with `weird thing` and "quoted fallback text"?

**Answer**: it breaks.

## Skill Automation

Unrelated trailing section content that must NOT be included in the
extracted section text or scanned for signatures/codes.
'''

# A synthetic recipe_optimizer.py: two live codes (REAL-001, REAL-002) as
# real `code="..."` assignments, plus a docstring mention of REAL-003 that
# must NOT count (only live code="..." assignments are the registry).
FIXTURE_OPTIMIZER_SOURCE = '''"""
Some docstring mentioning REAL-003 in prose - not a code="..." assignment,
so it must never appear in the derived registry.
"""

def check_one():
    return OptimizationSuggestion(
        code="REAL-001",
        message="...",
    )


def check_two():
    return OptimizationSuggestion(
        code="REAL-002",
        message="...",
    )
'''

OPTIMIZER_REL = ".claude/skills/conda-forge-expert/scripts/recipe_optimizer.py"


def _load_module():
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "failure_catalog_generator", _SCRIPTS_DIR / "failure_catalog_generator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


# --- section extraction --------------------------------------------------


def test_extract_gotcha_section_bounded_by_next_top_heading(mod):
    section = mod.extract_gotcha_section(FIXTURE_SKILL_MD)
    assert section.startswith("## Recipe Authoring Gotchas")
    assert "### G5." in section
    assert "## Skill Automation" not in section
    assert "Unrelated trailing section content" not in section


def test_extract_gotcha_section_missing_heading_raises(mod):
    with pytest.raises(mod.CatalogError):
        mod.extract_gotcha_section("# No gotcha section here\n")


def test_split_gotcha_entries_zero_entries_raises(mod):
    section = "## Recipe Authoring Gotchas\n\nNo entries at all.\n"
    with pytest.raises(mod.CatalogError):
        mod.split_gotcha_entries(section)


def test_split_gotcha_entries_order_and_titles(mod):
    section = mod.extract_gotcha_section(FIXTURE_SKILL_MD)
    entries = mod.split_gotcha_entries(section)
    assert [n for n, _, _ in entries] == [1, 2, 3, 4, 5]
    assert entries[0][1] == "First gotcha with a real enforced code"
    assert entries[4][1] == "Fifth gotcha with no Symptom label at all"


# --- optimizer registry ---------------------------------------------------


def test_extract_optimizer_registry_only_live_code_assignments(mod):
    registry = mod.extract_optimizer_registry(FIXTURE_OPTIMIZER_SOURCE)
    assert registry == {"REAL-001", "REAL-002"}
    assert "REAL-003" not in registry  # docstring prose, not a code="..." assignment


# --- enforced_by ------------------------------------------------------


@pytest.fixture(scope="module")
def entries(mod):
    section = mod.extract_gotcha_section(FIXTURE_SKILL_MD)
    return {n: (title, body) for n, title, body in mod.split_gotcha_entries(section)}


@pytest.fixture(scope="module")
def registry(mod):
    return mod.extract_optimizer_registry(FIXTURE_OPTIMIZER_SOURCE)


def test_enforced_by_real_code_resolves(mod, entries, registry):
    _, body = entries[1]
    assert mod.extract_enforced_by(body, registry) == f"{OPTIMIZER_REL}:REAL-001"


def test_enforced_by_no_code_mention_is_null(mod, entries, registry):
    _, body = entries[2]
    assert mod.extract_enforced_by(body, registry) is None


def test_enforced_by_stale_code_is_null(mod, entries, registry):
    """FAKE-999 is mentioned via the exact phrase but is not a live
    recipe_optimizer.py code -- must resolve to null, never a bogus pointer."""
    _, body = entries[3]
    assert mod.extract_enforced_by(body, registry) is None


def test_enforced_by_two_different_codes_is_null(mod, entries, registry):
    """The ambiguity rule: the phrase pointing at TWO different codes in one
    body resolves to null, even though both codes are individually live."""
    _, body = entries[4]
    assert mod.extract_enforced_by(body, registry) is None


# --- symptom_signature -----------------------------------------------


def test_symptom_signature_quotes_then_backticks_in_order(mod, entries):
    _, body = entries[1]
    assert mod.extract_symptom_signature(body) == ["boom error", "some code"]


def test_symptom_signature_backtick_only(mod, entries):
    _, body = entries[2]
    assert mod.extract_symptom_signature(body) == ["another code"]


def test_symptom_signature_falls_back_to_whole_body_when_no_label(mod, entries):
    """G5 has no **Symptom**: label at all (Question/Answer shape) -- the
    generator must still produce a non-empty signature by scanning the
    whole body."""
    _, body = entries[5]
    tokens = mod.extract_symptom_signature(body)
    assert tokens  # never empty
    assert "weird thing" in tokens
    assert "quoted fallback text" in tokens


def test_symptom_signature_dedupes_and_caps(mod):
    body = "**Symptom**: " + " ".join(f'"tok{i}"' for i in range(20)) + "\n\n**Why**: x\n"
    tokens = mod.extract_symptom_signature(body)
    assert len(tokens) <= mod.MAX_SIGNATURE_TOKENS


# --- full catalog assembly + determinism ------------------------------


def test_build_catalog_shape(mod):
    catalog = mod.build_catalog(FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER_SOURCE)
    assert [r["id"] for r in catalog["rows"]] == [f"G{i}" for i in range(1, 6)]
    enforced = {r["id"]: r["enforced_by"] for r in catalog["rows"]}
    assert enforced["G1"] == f"{OPTIMIZER_REL}:REAL-001"
    assert enforced["G2"] is None
    assert enforced["G3"] is None
    assert enforced["G4"] is None
    assert enforced["G5"] is None
    assert all(r["symptom_signature"] for r in catalog["rows"])


def test_build_catalog_missing_section_raises(mod):
    with pytest.raises(mod.CatalogError):
        mod.build_catalog("# nothing here\n", FIXTURE_OPTIMIZER_SOURCE)


def test_render_catalog_is_idempotent(mod):
    catalog = mod.build_catalog(FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER_SOURCE)
    first = mod.render_catalog(catalog)
    second = mod.render_catalog(mod.build_catalog(FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER_SOURCE))
    assert first == second


def test_render_catalog_matches_schema_shape(mod):
    catalog = mod.build_catalog(FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER_SOURCE)
    rendered = mod.render_catalog(catalog)
    assert rendered.startswith("# GENERATED FILE — DO NOT HAND-EDIT.\n")
    assert 'source_sha256: "' in rendered
    assert "enforced_by: null" in rendered
    assert f'enforced_by: "{OPTIMIZER_REL}:REAL-001"' in rendered
    assert "generated_at" not in rendered  # no wall-clock field, ever


# --- CLI (main()) — in a tmp_path fixture "repo" ----------------------


def _write_fixture_repo(tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "conda-forge-expert"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(FIXTURE_SKILL_MD, encoding="utf-8")
    (skill_dir / "scripts" / "recipe_optimizer.py").write_text(
        FIXTURE_OPTIMIZER_SOURCE, encoding="utf-8")


def test_main_write_mode_creates_catalog(mod, tmp_path, monkeypatch):
    _write_fixture_repo(tmp_path)
    monkeypatch.setattr(mod, "get_repo_root", lambda: tmp_path)
    rc = mod.main([])
    assert rc == 0
    out = tmp_path / mod.OUTPUT_REL
    assert out.exists()
    assert "enforced_by: null" in out.read_text()


def test_main_check_mode_in_sync_then_drift(mod, tmp_path, monkeypatch):
    _write_fixture_repo(tmp_path)
    monkeypatch.setattr(mod, "get_repo_root", lambda: tmp_path)
    assert mod.main([]) == 0
    assert mod.main(["--check"]) == 0

    out = tmp_path / mod.OUTPUT_REL
    out.write_text(out.read_text().replace("boom error", "HAND EDITED"))
    assert mod.main(["--check"]) != 0


def test_main_check_mode_missing_file_is_nonzero(mod, tmp_path, monkeypatch):
    _write_fixture_repo(tmp_path)
    monkeypatch.setattr(mod, "get_repo_root", lambda: tmp_path)
    assert mod.main(["--check"]) != 0
    assert not (tmp_path / mod.OUTPUT_REL).exists()


def test_main_unparseable_skill_md_is_nonzero_and_writes_nothing(mod, tmp_path, monkeypatch):
    skill_dir = tmp_path / ".claude" / "skills" / "conda-forge-expert"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# no gotcha section\n", encoding="utf-8")
    (skill_dir / "scripts" / "recipe_optimizer.py").write_text(
        FIXTURE_OPTIMIZER_SOURCE, encoding="utf-8")
    monkeypatch.setattr(mod, "get_repo_root", lambda: tmp_path)
    rc = mod.main([])
    assert rc != 0
    assert not (tmp_path / mod.OUTPUT_REL).exists()
