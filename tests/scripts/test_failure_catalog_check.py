"""Unit tests for scripts/failure_catalog_check.py (Story 7.2,
spec-7-2-the-pointers-lint-and-the-drift-gates) -- covers every row of the
spec's I/O & Edge-Case Matrix.

Mirrors tests/scripts/test_mason_cfe_surface_check.py's fixture style
(tmp-dir based, reaching the module the same way, since scripts/ has no
__init__.py) but never touches the real committed catalog/SKILL.md except
in the one deliberate "real committed catalog" smoke test the spec asks
for.

The pointer-resolution lint (check_pointers) and the drift delegation
(check_drift) are proven RED-FIRST in isolation from each other, on
purpose: by construction, any catalog produced by the real generator with
an unresolvable enforced_by pointer is ALSO out of sync with a fresh
regen (the generator only ever emits a pointer once it has confirmed the
code is live in the registry) -- so "each independently produce a
finding" is demonstrated at the function level (check_pointers /
check_drift each exercised on their own), not by contriving a single
fixture that is simultaneously drift-clean and pointer-broken.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import failure_catalog_check as fcc  # noqa: E402  (sys.path must be set up first)

# The real generator's pure functions (build_catalog/render_catalog) are
# imported here ONLY to construct a byte-exact, drift-clean fixture catalog
# for the "clean fixture" scenario -- never to re-implement or fake Story
# 7.1's generator logic itself.
_CFE_SCRIPTS_DIR = REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "scripts"
if str(_CFE_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_CFE_SCRIPTS_DIR))

import failure_catalog_generator as fcg  # noqa: E402


# --- fixture helpers ---------------------------------------------------

CATALOG_REL_PARTS = (".claude", "skills", "conda-forge-expert", "config",
                     "failure-catalog.yaml")
SKILL_MD_REL_PARTS = (".claude", "skills", "conda-forge-expert", "SKILL.md")
OPTIMIZER_REL_PARTS = (".claude", "skills", "conda-forge-expert", "scripts",
                       "recipe_optimizer.py")
GENERATOR_REL_PARTS = (".claude", "skills", "conda-forge-expert", "scripts",
                       "failure_catalog_generator.py")
PATHS_HELPER_REL_PARTS = (".claude", "skills", "conda-forge-expert", "scripts",
                          "_paths.py")

OPTIMIZER_TARGET_REL = "/".join(OPTIMIZER_REL_PARTS)

# A minimal, self-contained fixture gotcha corpus: G1 has no enforced check
# (-> enforced_by: null); G2 is enforced by a fixture check code that lives
# in the fixture recipe_optimizer.py below.
FIXTURE_SKILL_MD = """# Fixture Skill

## Some Other Section

not part of the gotcha corpus.

## Recipe Authoring Gotchas

### G1. First gotcha with no enforced check

**Symptom**: something goes wrong with `foo.bar` and "a quoted error string".

**Why**: reasons, not a check.

### G2. Second gotcha enforced by the optimizer

**Symptom**: something else goes wrong with `baz.qux`.

**Why**: The optimizer's **FOO-001** check catches this.

## Next Top-Level Section

more stuff, not part of the gotcha corpus.
"""

FIXTURE_OPTIMIZER = '''"""Fixture stand-in for recipe_optimizer.py -- only the
code="..." lines matter to failure_catalog_generator.py's registry regex."""

FINDING = dict(
    code="FOO-001",
)
'''


def _write(root: Path, rel_parts: tuple[str, ...], content: str) -> Path:
    path = root.joinpath(*rel_parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _install_generator(root: Path) -> None:
    """Copy the REAL failure_catalog_generator.py + its _paths.py sibling
    into `root`'s fixture .claude/skills/conda-forge-expert/scripts/ tree,
    so check_drift()'s subprocess call has something real to invoke.
    _paths.py's get_repo_root() is a pure parent-count walk (parents[4]
    from its own file), so copied four levels under `root` it resolves
    `root` itself as the repo root -- no other fixture markers needed."""
    for rel_parts in (GENERATOR_REL_PARTS, PATHS_HELPER_REL_PARTS):
        src = REPO_ROOT.joinpath(*rel_parts)
        dst = root.joinpath(*rel_parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _write_synced_catalog(root: Path, skill_md_text: str, optimizer_text: str) -> None:
    """Write a catalog.yaml that byte-exactly matches a fresh regen of
    (skill_md_text, optimizer_text) via the REAL generator -- drift-clean
    by construction."""
    catalog = fcg.build_catalog(skill_md_text, optimizer_text)
    rendered = fcg.render_catalog(catalog)
    _write(root, CATALOG_REL_PARTS, rendered)


# --- check_pointers() -- isolated red-first proof for `unresolved-pointer` -


def test_check_pointers_clean_all_resolve(tmp_path: Path) -> None:
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    rows = [
        {"id": "G1", "enforced_by": None},
        {"id": "G2", "enforced_by": f"{OPTIMIZER_TARGET_REL}:FOO-001"},
    ]
    findings, null_rows = fcc.check_pointers(tmp_path, rows)
    assert findings == []
    assert null_rows == 1


def test_check_pointers_bogus_code_absent_from_target(tmp_path: Path) -> None:
    """RED-FIRST: a code that isn't in the pointed-at file's live source."""
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    rows = [{"id": "G99", "enforced_by": f"{OPTIMIZER_TARGET_REL}:BOGUS-999"}]

    findings, null_rows = fcc.check_pointers(tmp_path, rows)

    assert null_rows == 0
    assert len(findings) == 1
    assert findings[0]["kind"] == "unresolved-pointer"
    assert findings[0]["id"] == "G99"
    assert "BOGUS-999" in findings[0]["detail"]


def test_check_pointers_missing_target_file(tmp_path: Path) -> None:
    """RED-FIRST: the enforced_by path itself doesn't exist."""
    rows = [{"id": "G100", "enforced_by":
             ".claude/skills/conda-forge-expert/scripts/does_not_exist.py:FOO-001"}]

    findings, null_rows = fcc.check_pointers(tmp_path, rows)

    assert null_rows == 0
    assert len(findings) == 1
    assert findings[0]["kind"] == "unresolved-pointer"
    assert findings[0]["id"] == "G100"
    assert "does not exist" in findings[0]["detail"]


def test_check_pointers_malformed_pointer_no_colon(tmp_path: Path) -> None:
    rows = [{"id": "G101", "enforced_by": "not-a-valid-pointer"}]

    findings, null_rows = fcc.check_pointers(tmp_path, rows)

    assert null_rows == 0
    assert len(findings) == 1
    assert findings[0]["kind"] == "unresolved-pointer"


def test_check_pointers_null_rows_counted_not_flagged(tmp_path: Path) -> None:
    rows = [{"id": f"G{i}", "enforced_by": None} for i in range(5)]

    findings, null_rows = fcc.check_pointers(tmp_path, rows)

    assert findings == []
    assert null_rows == 5


# --- check_drift() -- isolated red-first proof for `catalog-drift` --------


def test_check_drift_clean_when_catalog_matches_fresh_regen(tmp_path: Path) -> None:
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, FIXTURE_SKILL_MD)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    assert fcc.check_drift(tmp_path) == []


def test_check_drift_detects_drifted_catalog(tmp_path: Path) -> None:
    """RED-FIRST: the catalog was generated for the original SKILL.md, but
    SKILL.md then changed (a gotcha title edited) without regenerating."""
    _install_generator(tmp_path)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    drifted_skill_md = FIXTURE_SKILL_MD.replace(
        "### G1. First gotcha with no enforced check",
        "### G1. First gotcha, title edited without regenerating",
    )
    _write(tmp_path, SKILL_MD_REL_PARTS, drifted_skill_md)

    findings = fcc.check_drift(tmp_path)

    assert len(findings) == 1
    assert findings[0]["kind"] == "catalog-drift"
    assert findings[0]["id"] is None


def test_check_drift_generator_cannot_run_raises_could_not_run(tmp_path: Path) -> None:
    """SKILL.md missing the gotcha heading entirely -- the generator's own
    CatalogError path, not an ordinary drift report."""
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, "# Fixture Skill\n\nno gotcha section here.\n")
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write(tmp_path, CATALOG_REL_PARTS, "source_sha256: \"x\"\nrows: []\n")

    with pytest.raises(fcc.CouldNotRunError):
        fcc.check_drift(tmp_path)


def test_check_drift_missing_generator_script_raises_could_not_run(tmp_path: Path) -> None:
    with pytest.raises(fcc.CouldNotRunError):
        fcc.check_drift(tmp_path)


# --- _load_catalog() -- malformed-catalog validation ------------------------


def test_load_catalog_invalid_yaml_raises_could_not_run(tmp_path: Path) -> None:
    """RED-FIRST: syntactically invalid YAML must be a could-not-run, not an
    uncaught exception or a silent empty-rows read."""
    catalog_path = _write(tmp_path, CATALOG_REL_PARTS,
                          "rows:\n  - id: G1\n  enforced_by: [unterminated\n")

    with pytest.raises(fcc.CouldNotRunError):
        fcc._load_catalog(catalog_path)


def test_load_catalog_missing_rows_key_raises_could_not_run(tmp_path: Path) -> None:
    """RED-FIRST: valid YAML that simply lacks the top-level 'rows' key
    entirely must not be misread as an empty, clean catalog."""
    catalog_path = _write(tmp_path, CATALOG_REL_PARTS,
                          'source_sha256: "x"\nnot_rows: []\n')

    with pytest.raises(fcc.CouldNotRunError):
        fcc._load_catalog(catalog_path)


# --- run() / main() -- combined I/O-matrix rows ----------------------------


def test_run_clean_fixture_zero_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, FIXTURE_SKILL_MD)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    findings, stats = fcc.run()

    assert findings == []
    assert stats["total_rows"] == 2
    assert stats["null_rows"] == 1
    assert stats["coverage"] == pytest.approx(0.5)


def test_run_bogus_pointer_and_drift_both_surface_as_findings(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When a pointer is tampered with on a self-consistent fixture, the
    catalog is (by construction, see module docstring) ALSO out of sync
    with a fresh regen -- run() must still report exit 1 with the
    unresolved-pointer finding present, proving the two checks compose
    rather than silently swallowing one another."""
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, FIXTURE_SKILL_MD)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    catalog_path = tmp_path.joinpath(*CATALOG_REL_PARTS)
    tampered = catalog_path.read_text(encoding="utf-8").replace("FOO-001", "BOGUS-001")
    catalog_path.write_text(tampered, encoding="utf-8")

    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    findings, _stats = fcc.run()

    kinds = {f["kind"] for f in findings}
    assert "unresolved-pointer" in kinds


def test_main_exit_0_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                            capsys: pytest.CaptureFixture[str]) -> None:
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, FIXTURE_SKILL_MD)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py"])
    rc = fcc.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "clean" in out
    assert "null_rows=1" in out


def test_main_exit_1_findings_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, FIXTURE_SKILL_MD)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    catalog_path = tmp_path.joinpath(*CATALOG_REL_PARTS)
    tampered = catalog_path.read_text(encoding="utf-8").replace("FOO-001", "BOGUS-001")
    catalog_path.write_text(tampered, encoding="utf-8")

    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py", "--json"])
    rc = fcc.main()
    out = capsys.readouterr().out

    assert rc == 1
    payload = json.loads(out)
    kinds = {f["kind"] for f in payload["findings"]}
    assert "unresolved-pointer" in kinds
    assert payload["stats"]["total_rows"] == 2


def test_main_exit_1_findings_plain_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                          capsys: pytest.CaptureFixture[str]) -> None:
    """The non-`--json` findings-report branch -- the exact path
    scripts/detectors.py's run_one() invokes (no --json flag) and what
    `pixi run -e local-recipes failure-catalog-check` shows by default.
    Was previously exercised only via the --json variant above."""
    _install_generator(tmp_path)
    _write(tmp_path, SKILL_MD_REL_PARTS, FIXTURE_SKILL_MD)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write_synced_catalog(tmp_path, FIXTURE_SKILL_MD, FIXTURE_OPTIMIZER)

    catalog_path = tmp_path.joinpath(*CATALOG_REL_PARTS)
    tampered = catalog_path.read_text(encoding="utf-8").replace("FOO-001", "BOGUS-001")
    catalog_path.write_text(tampered, encoding="utf-8")

    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py"])
    rc = fcc.main()
    out = capsys.readouterr().out

    assert rc == 1
    assert "unresolved-pointer" in out
    assert "G2" in out
    assert "FAIL: " in out


def test_main_exit_2_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    # No .claude tree at all under tmp_path -- the catalog itself is missing.
    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py"])
    rc = fcc.main()
    captured = capsys.readouterr()

    assert rc == 2
    assert "failure-catalog-check:" in captured.err


def test_main_exit_2_json_still_emits_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py", "--json"])
    rc = fcc.main()
    out = capsys.readouterr().out

    assert rc == 2
    payload = json.loads(out)
    assert payload["findings"] == []
    assert "error" in payload


# --- double-failure: check_drift() CouldNotRunError must not swallow -------
# --- pointer_findings already discovered by check_pointers() ---------------


def _write_broken_drift_fixture_with_a_real_pointer_finding(tmp_path: Path) -> None:
    """A catalog with one genuinely unresolved enforced_by pointer (G99 ->
    BOGUS-999, absent from the fixture optimizer), paired with a SKILL.md
    that's missing the gotcha heading entirely -- the generator's own
    CatalogError path, so check_drift() raises CouldNotRunError rather than
    reporting an ordinary drift finding. The two failures are independent:
    check_pointers() only reads the catalog's rows; check_drift() only
    re-derives from SKILL.md/optimizer via the generator subprocess."""
    _install_generator(tmp_path)
    _write(tmp_path, OPTIMIZER_REL_PARTS, FIXTURE_OPTIMIZER)
    _write(tmp_path, SKILL_MD_REL_PARTS, "# Fixture Skill\n\nno gotcha section here.\n")
    _write(tmp_path, CATALOG_REL_PARTS,
           'source_sha256: "x"\n'
           "rows:\n"
           "  - id: G99\n"
           f'    enforced_by: "{OPTIMIZER_TARGET_REL}:BOGUS-999"\n')


def test_run_could_not_run_still_carries_prior_pointer_findings(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RED-FIRST (Patch 1): when check_drift() raises CouldNotRunError, the
    unresolved-pointer finding check_pointers() already found must not
    vanish -- it must be reachable off the raised exception."""
    _write_broken_drift_fixture_with_a_real_pointer_finding(tmp_path)
    monkeypatch.setattr(fcc, "ROOT", tmp_path)

    with pytest.raises(fcc.CouldNotRunError) as excinfo:
        fcc.run()

    pointer_findings = getattr(excinfo.value, "pointer_findings", None)
    assert pointer_findings is not None
    assert len(pointer_findings) == 1
    assert pointer_findings[0]["kind"] == "unresolved-pointer"
    assert pointer_findings[0]["id"] == "G99"


def test_main_exit_2_still_surfaces_prior_pointer_findings_json(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Same double-failure, through main() --json: exit code stays 2 (the
    could-not-run contract is unchanged), but the pointer finding already
    found is visible in the JSON payload rather than silently discarded."""
    _write_broken_drift_fixture_with_a_real_pointer_finding(tmp_path)
    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py", "--json"])

    rc = fcc.main()
    out = capsys.readouterr().out

    assert rc == 2
    payload = json.loads(out)
    assert "error" in payload
    assert len(payload["findings"]) == 1
    assert payload["findings"][0]["kind"] == "unresolved-pointer"
    assert payload["findings"][0]["id"] == "G99"


def test_main_exit_2_still_surfaces_prior_pointer_findings_plain_text(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Same double-failure, through main()'s plain-text path: both the
    pointer finding and the could-not-run message must appear."""
    _write_broken_drift_fixture_with_a_real_pointer_finding(tmp_path)
    monkeypatch.setattr(fcc, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["failure_catalog_check.py"])

    rc = fcc.main()
    captured = capsys.readouterr()

    assert rc == 2
    assert "unresolved-pointer" in captured.out
    assert "G99" in captured.out
    assert "failure-catalog-check:" in captured.err


# --- real committed catalog (smoke) ----------------------------------------


def test_real_committed_catalog_is_clean_and_reports_null_rows() -> None:
    """Given the REAL committed failure-catalog.yaml (per the spec's
    Verification section) -- exit 0, zero findings, and the null-rows count
    computed here independently from the same on-disk file, so this stays
    correct as the gotcha corpus grows rather than hardcoding a count."""
    catalog_path = REPO_ROOT.joinpath(*CATALOG_REL_PARTS)
    catalog = fcc._load_catalog(catalog_path)
    rows = catalog["rows"]
    expected_null_rows = sum(1 for r in rows if r.get("enforced_by") is None)

    findings, stats = fcc.run()

    assert findings == []
    assert stats["total_rows"] == len(rows)
    assert stats["null_rows"] == expected_null_rows


def test_cli_against_live_repo_exits_zero() -> None:
    """`python scripts/failure_catalog_check.py` -- exact command from the
    spec's Verification section."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "failure_catalog_check.py")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "clean" in proc.stdout
