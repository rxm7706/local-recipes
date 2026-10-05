"""Unit tests for ``scripts/flag_gate_check.py`` -- the flag gate (doctor Story 34.2,
spec-feature-flag-governance CAP-2; the two-state-test check is Story 34.5, CAP-4's gate clause).

One test per acceptance-criteria row and per I/O-matrix row of each story spec. Every judgement runs
against a fixture repo written under ``tmp_path`` (its own roster, baseline, tree, ``src/`` and
``scripts/``), so no test depends on which flags or stories the live tree holds today; the two live-tree
tests pin only the properties that hold whatever stories the tree carries.

The suite runs from ``pyforge-guild`` (``pixi run -e pyforge-guild python -m pytest
tests/scripts/test_flag_gate_check.py -q``) and from ``pyforge-ci`` (the ``scripts-suite`` lane), where PyYAML
arrives transitively; ``pytest.importorskip("yaml")`` mirrors ``test_flag_rule.py``.
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import detectors  # noqa: E402
import flag_gate_check  # noqa: E402
import flag_rule  # noqa: E402

GATE = _SCRIPTS_DIR / "flag_gate_check.py"
ORPHAN_KEY = "pyforge.test.orphan"

FLAG_BLOCK = """\
flag:
  key: {key}
  provider: openfeature-file
  default: {{production: off, staging: on, dev: on}}
  scope: global
  fallback: "the legacy behaviour"
  cleanup: 90 days after ON in every environment (Q4)
"""

git = shutil.which("git")


def _fixture(
    tmp_path: Path,
    *,
    exemptions=("alpha", "beta"),
    baseline=(),
    tree_keys=(),
    rule_date: str | None = "2026-09-28",
) -> Path:
    """A repo root with its own roster, baseline and tree; no story specs, no `src/`, no `scripts/`."""
    gov = tmp_path / "docs" / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "guild-roster.json").write_text(json.dumps({"flag_exemptions": list(exemptions)}), encoding="utf-8")
    document: dict = {"specs": sorted(baseline)}
    if rule_date is not None:
        document["rule_date"] = rule_date
    (gov / "flag-rule-baseline.json").write_text(json.dumps(document), encoding="utf-8")
    tree = tmp_path / "src" / "platform" / "config" / "flags.json"
    tree.parent.mkdir(parents=True, exist_ok=True)
    flags = {key: _boolean_flag_entry(key) for key in tree_keys}
    tree.write_text(json.dumps({"flags": flags}, indent=2), encoding="utf-8")
    return tmp_path


def _boolean_flag_entry(
    key: str,
    *,
    default_variant: str = "on",
    owner: str = "doctor",
    story: str = "fixture-story",
    on_everywhere: str = "",
) -> dict:
    """One boolean flag with the Story 76.2 metadata shape the gate reads (Story 34.3)."""
    return {
        "state": "ENABLED",
        "variants": {"on": True, "off": False},
        "defaultVariant": default_variant,
        "metadata": {
            "owner": owner,
            "story": story,
            "created": "2026-09-01",
            "on_everywhere": on_everywhere,
            "cleanup_by": "",
        },
    }


def _write_overlays(root: Path, overlays: dict) -> None:
    path = root / "src" / "platform" / "config" / "flag-overlays.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overlays, indent=2), encoding="utf-8")


def _patch_tree_flag(root: Path, key: str, entry: dict) -> None:
    path = root / "src" / "platform" / "config" / "flags.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("flags", {})[key] = entry
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _spec(
    root: Path,
    frontmatter: str = "",
    *,
    name: str = "spec-1-1-a-story.md",
    project: str = "pyforge-doctor",
    type_: str = "feature",
    status: str = "backlog",
    body: str = "body\n",
) -> str:
    """Write one story spec under ``root`` and return its repo-relative posix path."""
    rel = f"_bmad-output/projects/{project}/planning-artifacts/specs/{name}"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: a story\ntype: {type_}\nstatus: {status}\n{frontmatter}---\n\n{body}", encoding="utf-8"
    )
    return rel


def _write(root: Path, rel: str, text: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run(root: Path, *args: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    rc = flag_gate_check.main(["--root", str(root), *args])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _tree_json(root: Path, capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, dict]:
    rc, out, _ = _run(root, "--json", *args, capsys=capsys)
    return rc, json.loads(out)


def _kinds(payload: dict) -> list[str]:
    return [f["kind"] for f in payload["findings"]]


# The two-state test (Story 34.5): what a `done` flagged spec's Verification must name, and what that test holds.

KEY = "pyforge.test.landed"

KIT_TEST = """\
from pyforge.testing_kit.flags import flag_states


@flag_states("{key}")
def test_the_thing(flag_provider):
    assert True
"""
TWO_TREES_TEST = """\
KEY = "{key}"


def test_on(tmp_path):
    _flagd_tree("on")


def test_off(tmp_path):
    _flagd_tree("off")
"""


def _write_test(root: Path, key: str, template: str, *, rel: str = "tests/test_flagged.py") -> str:
    """Write a test file holding ``template`` for ``key``; return its repo-relative path."""
    _write(root, rel, template.format(key=key))
    return rel


def _verification(*names: str) -> str:
    """A story-spec body whose `## Verification` runs each named test file."""
    commands = "".join(f"- `python -m pytest {name} -q` -- expected: pass\n" for name in names)
    return f"## Verification\n\n**Commands:**\n{commands}\n## Review Triage Log\n"


def _landed_root(tmp_path: Path) -> Path:
    """A fixture whose tree holds ``KEY`` and whose ``src/`` reads it: a landed spec has no other finding."""
    root = _fixture(tmp_path, tree_keys=[KEY])
    _write(root, "src/pkg/reader.py", f'flag("{KEY}")\n')
    _write_overlays(
        root,
        {
            "dev": {KEY: "on"},
            "staging": {KEY: "on"},
            "production": {KEY: "off"},
        },
    )
    return root


def _landed_spec(root: Path, body: str, *, name: str = "spec-1-1-landed.md", status: str = "done") -> str:
    return _spec(root, FLAG_BLOCK.format(key=KEY), name=name, status=status, body=body)


# --- new feature, no block ------------------------------------------------------------------


def test_a_post_rule_feature_with_neither_exits_1_with_one_fail_naming_the_spec_and_the_missing_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    rel = _spec(root)

    rc, out, _ = _run(root, capsys=capsys)

    fails = [ln for ln in out.splitlines() if ln.startswith("[flag-gate] fail -- flag-missing")]
    assert rc == 1
    assert len(fails) == 1
    assert rel in fails[0]
    assert "`flag:` block" in fails[0]
    assert "`flag-exempt:`" in fails[0]
    assert out.splitlines()[-1].startswith("[flag-gate] fail --")


def test_a_post_rule_feature_with_a_partial_block_is_flag_missing_and_names_each_missing_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root, "flag:\n  key: pyforge.test.partial\n  provider: openfeature-file\n")

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-missing"]
    message = payload["findings"][0]["message"]
    assert all(f"`{field}`" in message for field in ("default", "scope", "fallback", "cleanup"))


# --- backlog feature, no block: a warning under its station ----------------------------------


def test_the_same_spec_in_the_baseline_exits_0_with_one_warn_naming_it_under_its_station(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    rel = _spec(root, project="pyforge-scribe")
    _fixture(tmp_path, baseline=[rel])

    rc, out, _ = _run(root, capsys=capsys)

    lines = out.splitlines()
    warn_lines = [ln for ln in lines if ln.startswith("[flag-gate] warn --")]
    assert rc == 0
    assert len(warn_lines) == 1
    assert "pyforge-scribe" in warn_lines[0]
    assert f"    {rel}" in lines
    assert not [ln for ln in lines if ln.startswith("[flag-gate] fail")]
    assert lines[-1].startswith("[flag-gate] ok --")


def test_warnings_group_by_station_and_a_default_run_lists_a_few_while_verbose_lists_all(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    rels = [_spec(root, name=f"spec-1-{n}-story.md", project="pyforge-atlas") for n in range(1, 6)]
    rels.append(_spec(root, name="spec-2-1-other.md", project="pyforge-herald"))
    _fixture(tmp_path, baseline=rels)

    rc, out, _ = _run(root, capsys=capsys)
    rc_verbose, out_verbose, _ = _run(root, "-v", capsys=capsys)

    assert rc == rc_verbose == 0
    assert "pyforge-atlas: 5 pre-rule" in out
    assert "pyforge-herald: 1 pre-rule" in out
    assert "... and 2 more (-v lists them all)" in out
    assert all(f"    {rel}" in out_verbose.splitlines() for rel in rels)
    assert "more (-v lists them all)" not in out_verbose


def test_the_json_report_lists_every_pre_rule_warning_with_its_station(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    rels = [_spec(root, name=f"spec-1-{n}-story.md", project="pyforge-mason") for n in range(1, 6)]
    _fixture(tmp_path, baseline=rels)

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["verdict"] == "warn"
    assert payload["rule_date"] == "2026-09-28"
    assert payload["specs_judged"] == 5
    assert [f["station"] for f in payload["findings"]] == ["pyforge-mason"] * 5
    assert {f["path"] for f in payload["findings"]} == set(rels)


# --- fix / chore / docs: nothing (Q1) --------------------------------------------------------


@pytest.mark.parametrize("kind", ["fix", "chore", "docs"])
def test_a_fix_chore_or_docs_spec_needs_no_flag_even_after_the_rule_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
):
    root = _fixture(tmp_path)
    _spec(root, type_=kind)

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []
    assert payload["verdict"] == "pass"


def test_a_pre_rule_fix_spec_is_not_warned_about(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    rel = _spec(root, type_="fix")
    _fixture(tmp_path, baseline=[rel])

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_a_memlog_and_a_folder_spec_file_are_not_story_specs(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    base = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs"
    _write(root, f"{base}/spec-1-1-a-story.memlog.md", "---\ntype: feature\n---\n")
    _write(root, f"{base}/spec-a-folder/SPEC.md", "---\ntype: feature\n---\n")

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["specs_judged"] == 0
    assert payload["findings"] == []


# --- flagged and exempt specs pass ------------------------------------------------------------


def test_a_full_flag_block_and_a_listed_exemption_both_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path, tree_keys=["pyforge.test.flagged"])
    _spec(root, FLAG_BLOCK.format(key="pyforge.test.flagged"), name="spec-1-1-flagged.md")
    _spec(root, "flag-exempt: alpha\n", name="spec-1-2-exempt.md")
    _write(root, "src/pkg/reader.py", 'flag("pyforge.test.flagged")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []
    assert payload["specs_judged"] == 2


# --- unknown exemption ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "kwargs", "baselined"),
    [
        ("post-rule feature", {}, False),
        ("pre-rule feature", {}, True),
        ("post-rule fix", {"type_": "fix"}, False),
        ("post-rule docs", {"type_": "docs"}, False),
    ],
)
def test_an_unknown_exemption_on_any_spec_is_one_fail_naming_the_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str, kwargs: dict, baselined: bool
):
    root = _fixture(tmp_path)
    rel = _spec(root, "flag-exempt: someday\n", **kwargs)
    if baselined:
        _fixture(tmp_path, baseline=[rel])

    rc, payload = _tree_json(root, capsys)

    assert rc == 1, name
    assert _kinds(payload) == ["flag-exempt-unknown"], name
    finding = payload["findings"][0]
    assert finding["path"] == rel
    assert "`flag-exempt: someday`" in finding["message"]
    assert "alpha, beta" in finding["message"]


def test_an_unknown_exemption_is_named_in_the_text_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root, "flag-exempt: someday\n")

    rc, out, _ = _run(root, capsys=capsys)

    assert rc == 1
    assert (
        len([ln for ln in out.splitlines() if ln.startswith("[flag-gate] fail --")]) == 2
    )  # the finding, then the summary
    assert "someday" in out


def test_a_blank_exemption_stays_neither_and_a_doubled_declaration_is_never_an_unknown_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root, "flag-exempt:\n", name="spec-1-1-blank.md")
    _spec(root, FLAG_BLOCK.format(key="pyforge.test.both") + "flag-exempt: someday\n", name="spec-1-2-both.md")

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-missing", "flag-missing"]
    assert any("declares exactly one" in f["message"] for f in payload["findings"])
    assert any("`flag-exempt:` is empty" in f["message"] for f in payload["findings"])


# --- landed, key missing ----------------------------------------------------------------------


def test_a_done_flagged_spec_whose_key_the_tree_lacks_is_one_fail_naming_the_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=["pyforge.test.other"])
    body = _verification(_write_test(root, "pyforge.test.landed", KIT_TEST))
    rel = _spec(root, FLAG_BLOCK.format(key="pyforge.test.landed"), status="done", body=body)
    _write(root, "src/pkg/reader.py", 'flag("pyforge.test.other")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-key-not-in-tree"]
    finding = payload["findings"][0]
    assert finding["path"] == rel
    assert finding["key"] == "pyforge.test.landed"
    assert "`pyforge.test.landed`" in finding["message"]


def test_the_same_spec_at_backlog_has_no_finding_and_a_done_spec_with_its_key_in_the_tree_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=["pyforge.test.landed"])
    _write_overlays(
        root,
        {
            "dev": {"pyforge.test.landed": "on"},
            "staging": {"pyforge.test.landed": "on"},
            "production": {"pyforge.test.landed": "off"},
        },
    )
    _spec(root, FLAG_BLOCK.format(key="pyforge.test.absent"), name="spec-1-1-backlog.md", status="backlog")
    body = _verification(_write_test(root, "pyforge.test.landed", KIT_TEST))
    _spec(root, FLAG_BLOCK.format(key="pyforge.test.landed"), name="spec-1-2-done.md", status="done", body=body)
    _write(root, "src/pkg/reader.py", 'flag("pyforge.test.landed")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_a_done_spec_with_no_usable_key_is_not_a_key_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root, "flag-exempt: alpha\n", status="done")

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


# --- orphan tree key --------------------------------------------------------------------------


def test_a_tree_key_that_no_file_under_src_or_scripts_mentions_is_one_fail_naming_the_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])
    _write(root, "src/pkg/unrelated.py", "x = 1\n")
    _write(root, "scripts/unrelated.py", "y = 2\n")

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-key-orphan"]
    finding = payload["findings"][0]
    assert finding["key"] == ORPHAN_KEY
    assert f"`{ORPHAN_KEY}`" in finding["message"]
    assert finding["path"] == "src/platform/config/flags.json"


@pytest.mark.parametrize("reader", ["src/pkg/reader.py", "scripts/reader.py", "src/pkg/reader.toml"])
def test_the_same_fixture_with_a_src_or_scripts_file_that_reads_the_key_has_no_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], reader: str
):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])
    _write(root, reader, f'flag("{ORPHAN_KEY}")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


@pytest.mark.parametrize(
    "mention",
    [
        "src/pkg/tests/reader.py",
        "src/pkg/test/reader.py",
        "src/pkg/test_reader.py",
        "src/pkg/conftest.py",
        "src/pkg/docs/reader.py",
        "src/pkg/fixtures/reader.py",
        "src/pkg/NOTES.md",
        "scripts/tests/reader.py",
        "tests/reader.py",
        "docs/reader.md",
    ],
)
def test_a_mention_in_a_test_doc_fixture_or_markdown_file_is_not_a_reader(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mention: str
):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])
    _write(root, mention, f'flag("{ORPHAN_KEY}")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-key-orphan"]


def test_the_tree_itself_and_story_specs_never_read_a_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])
    _spec(root, FLAG_BLOCK.format(key=ORPHAN_KEY))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert "flag-key-orphan" in _kinds(payload)


def test_the_overlay_document_names_every_key_and_reads_none(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Story 76.1: `flag-overlays.json` lists a key per environment; it is no more a reader than the tree."""
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])
    _write(root, "src/platform/config/flag-overlays.json", '{"production": {"%s": "off"}}\n' % ORPHAN_KEY)

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-key-orphan"]
    assert payload["findings"][0]["key"] == ORPHAN_KEY
    assert flag_gate_check.OVERLAYS_REL.as_posix() == "src/platform/config/flag-overlays.json"


def test_only_the_unread_key_is_orphaned(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY, "pyforge.test.read"])
    _write(root, "src/pkg/reader.py", 'flag("pyforge.test.read")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert [f["key"] for f in payload["findings"]] == [ORPHAN_KEY]


# --- a landed flagged story's test runs both states (Story 34.5, CAP-4's gate clause) -----------


@pytest.mark.parametrize(
    "import_line",
    [
        "from pyforge.testing_kit.flags import flag_states",
        "from pyforge.testing_kit import flag_states",
        "from pyforge.testing_kit import flags",
        "import pyforge.testing_kit.flags",
    ],
)
def test_a_test_that_uses_the_kits_helper_with_the_specs_key_has_no_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], import_line: str
):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_flagged.py", f'{import_line}\n\n@flag_states("{KEY}")\ndef test_it(): ...\n')
    _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


@pytest.mark.parametrize(
    "writer",
    [
        '_flagd_tree("on")\n_flagd_tree("off")\n',
        "flagd_tree(tmp_path, {KEY: 'on'})\nflagd_tree(tmp_path, {KEY: 'off'}, name='off.json')\n",
        'write(_flagd_tree(str(tmp_path), "on"))\nwrite(_flagd_tree(str(tmp_path), "off"))\n',
    ],
)
def test_a_test_that_writes_two_flagd_trees_for_the_key_has_no_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], writer: str
):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_flagged.py", f'KEY = "{KEY}"\n\ndef test_it(tmp_path):\n    {writer}')
    _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


@pytest.mark.parametrize(
    ("label", "content"),
    [
        (
            "kit helper, another key",
            'from pyforge.testing_kit.flags import flag_states\n@flag_states("pyforge.other.key")\n',
        ),
        ("kit helper, no key at all", "from pyforge.testing_kit.flags import flag_states\n@flag_states(KEY)\n"),
        ("kit helper, a longer key", f'from pyforge.testing_kit.flags import flag_states\n@flag_states("{KEY}_v2")\n'),
        ("kit helper, a sub-key", f'from pyforge.testing_kit.flags import flag_states\n@flag_states("{KEY}.sub")\n'),
        ("key, no helper and no tree", f'KEY = "{KEY}"\ndef test_it():\n    assert True\n'),
        ("key, helper named but never imported", f'KEY = "{KEY}"\n@flag_states(KEY)\ndef test_it(): ...\n'),
        ("two trees, no key", '_flagd_tree("on")\n_flagd_tree("off")\n'),
        ("one tree only", f'KEY = "{KEY}"\n_flagd_tree("on")\n'),
        ("two trees, both on", f'KEY = "{KEY}"\n_flagd_tree("on")\n_flagd_tree("on")\n'),
        ("one call naming both", f'KEY = "{KEY}"\n_flagd_tree("on", "off")\n'),
        ("a definition is not a call", f'KEY = "{KEY}"\ndef _flagd_tree(v="on"): ...\ndef _flagd_tree(v="off"): ...\n'),
        (
            "kit helper imported and key named, never called",
            f'from pyforge.testing_kit.flags import flag_states\nKEY = "{KEY}"\n',
        ),
        (
            "kit helper, a key that ends in the spec's key after a dot",
            f'from pyforge.testing_kit.flags import flag_states\n@flag_states("other.{KEY}")\n',
        ),
        (
            "kit helper, a key that ends in the spec's key after a hyphen",
            f'from pyforge.testing_kit.flags import flag_states\n@flag_states("x-{KEY}")\n',
        ),
        (
            "kit helper, a key that ends in the spec's key after a word character",
            f'from pyforge.testing_kit.flags import flag_states\n@flag_states("my{KEY}")\n',
        ),
        (
            "an unrelated off after two on trees",
            f'KEY = "{KEY}"\n_flagd_tree("on")\n_flagd_tree("on")\n\ndef test_x():\n    assert mode == "off"\n',
        ),
    ],
)
def test_a_test_that_does_not_run_the_specs_key_in_both_states_is_one_fail_naming_the_spec_and_the_test_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], label: str, content: str
):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_flagged.py", content)
    rel = _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1, label
    assert _kinds(payload) == ["flag-test-not-two-state"], label
    finding = payload["findings"][0]
    assert finding["path"] == rel
    assert finding["key"] == KEY
    assert finding["severity"] == "fail"
    assert "tests/test_flagged.py" in finding["message"]
    assert f"`{KEY}`" in finding["message"]


@pytest.mark.parametrize("identifier", ["undef", "typedef"])
def test_a_flagd_tree_call_after_an_identifier_that_ends_in_def_is_still_a_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], identifier: str
):
    root = _landed_root(tmp_path)
    content = f'KEY = "{KEY}"\n{identifier}\n_flagd_tree("on")\n{identifier}\n_flagd_tree("off")\n'
    _write(root, "tests/test_flagged.py", content)
    _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_the_not_two_state_finding_names_every_named_test_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_weak_one.py", "def test_x(): ...\n")
    _write(root, "tests/test_weak_two.py", f'KEY = "{KEY}"\n')
    _landed_spec(root, _verification("tests/test_weak_one.py", "tests/test_weak_two.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-not-two-state"]
    message = payload["findings"][0]["message"]
    assert "tests/test_weak_one.py" in message
    assert "tests/test_weak_two.py" in message


def test_a_verification_that_names_no_test_file_is_one_fail_naming_the_spec(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    body = "## Verification\n\n**Commands:**\n- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- pass\n"
    rel = _landed_spec(root, body)

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-verification-names-no-test"]
    assert payload["findings"][0]["path"] == rel
    assert payload["findings"][0]["key"] == KEY


@pytest.mark.parametrize(
    "body",
    [
        "body\n",  # no Verification section at all
        "## Verification\n\n",  # an empty one
        "## Verification\n\n- `pytest tests/`\n",  # a directory target names no file
        "## Verification\n\n- `pytest --ignore=tests/test_flagged.py tests/`\n",  # an option is not a file run
        "## Verification\n\nRun the tests/test_flagged.py file.\n",  # prose, not a backticked path
        "## Design Notes\n\n`tests/test_flagged.py`\n\n## Verification\n\n- `pytest -q`\n",  # another section
        "## Verification\n\n- `pytest -q`\n\n## Review Triage Log\n\n- `tests/test_flagged.py`\n",  # after it
        "## Verification\n\n- `pytest -q`\n\n## Verification Notes\n\n- `tests/test_flagged.py`\n",  # not the heading
        "## Verification\n\n- `https://example.com/tests/test_flagged.py`\n",  # a URL is not a file the run executes
    ],
)
def test_only_a_test_file_named_in_the_verification_section_counts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], body: str
):
    root = _landed_root(tmp_path)
    _write_test(root, KEY, KIT_TEST)  # a good test exists; the Verification just does not name it
    _landed_spec(root, body)

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-verification-names-no-test"]


@pytest.mark.parametrize(
    "body",
    [
        "## Verification\n\n```bash\npixi run -e pyforge-guild pytest tests/test_flagged.py -q\n```\n",
        "## Verification\n\n- `pytest tests/test_flagged.py::test_the_thing -q`\n",
        "## Verification\n\n- `tests/test_flagged.py`\n",
        "## Verification\n\n- `./tests/test_flagged.py`\n",
        "## Verification\n\n### Manual\n\n- `pytest 'tests/test_flagged.py'`\n",
    ],
)
def test_backticked_paths_and_pytest_targets_in_every_written_form_are_collected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], body: str
):
    root = _landed_root(tmp_path)
    _write_test(root, KEY, KIT_TEST)
    _landed_spec(root, body)

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_a_second_verification_section_after_another_section_is_read_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    _write_test(root, KEY, KIT_TEST)
    body = (
        "## Verification\n\n- `pytest -q`\n\n## Design Notes\n\nprose\n\n"
        "## Verification\n\n- `pytest tests/test_flagged.py`\n"
    )
    _landed_spec(root, body)

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


@pytest.mark.parametrize(
    "name",
    ["tests/test_flagged.py", "tests/flagged_test.py", "web/flagged.test.ts", "e2e/flagged.spec.ts"],
)
def test_a_named_path_counts_as_a_test_file_by_its_name(tmp_path: Path, capsys: pytest.CaptureFixture[str], name: str):
    root = _landed_root(tmp_path)
    _write(root, name, f'@flag_states("{KEY}")\n')
    rel = _landed_spec(root, _verification(name))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-not-two-state"]  # named and found: only its content is short
    assert name in payload["findings"][0]["message"]
    assert payload["findings"][0]["path"] == rel


def test_one_two_state_test_among_several_named_files_is_enough(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_unrelated.py", "def test_x(): ...\n")
    good = _write_test(root, KEY, KIT_TEST, rel="tests/test_two_state.py")
    _landed_spec(root, _verification("tests/test_unrelated.py", good))

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_a_named_test_file_that_does_not_exist_is_one_fail_naming_the_missing_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    rel = _landed_spec(root, _verification("tests/test_absent.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-file-missing"]
    assert payload["findings"][0]["path"] == rel
    assert "tests/test_absent.py" in payload["findings"][0]["message"]


def test_a_missing_path_is_one_fail_never_two_even_beside_a_present_test_that_is_not_two_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_weak.py", "def test_x(): ...\n")
    _landed_spec(root, _verification("tests/test_weak.py", "tests/test_absent.py", "tests/test_gone.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-file-missing"]
    message = payload["findings"][0]["message"]
    assert "tests/test_absent.py" in message
    assert "tests/test_gone.py" in message
    assert "tests/test_weak.py" not in message


@pytest.mark.parametrize("how", ["absolute", "parent-relative"])
def test_a_named_path_outside_the_repo_is_missing_never_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], how: str
):
    root = _landed_root(tmp_path / "repo")
    outside = _write(tmp_path, "outside/test_flagged.py", KIT_TEST.format(key=KEY))  # a real two-state test
    named = str(outside) if how == "absolute" else "../outside/test_flagged.py"
    _landed_spec(root, f"## Verification\n\n- `pytest {named}`\n")

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-file-missing"]
    assert "test_flagged.py" in payload["findings"][0]["message"]


def test_a_named_directory_is_not_a_test_file_even_when_it_is_named_like_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    (root / "tests" / "test_dir.py").mkdir(parents=True)
    _landed_spec(root, _verification("tests/test_dir.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-file-missing"]


def test_a_test_file_is_read_as_text_never_imported_or_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _landed_root(tmp_path)
    _write(
        root,
        "tests/test_flagged.py",
        "import a_module_that_does_not_exist\n"
        "from pyforge.testing_kit.flags import flag_states\n"
        f'raise RuntimeError("the gate must never run this")\n@flag_states("{KEY}")\ndef test_it(): ...\n',
    )
    _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_a_test_file_that_is_not_utf8_is_read_not_crashed_on(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _landed_root(tmp_path)
    (root / "tests").mkdir()
    (root / "tests" / "test_flagged.py").write_bytes(b'\xff\xfe# not utf-8\nKEY = "' + KEY.encode() + b'"\n')
    _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-test-not-two-state"]


@pytest.mark.parametrize(
    ("label", "frontmatter", "status", "body"),
    [
        ("backlog", FLAG_BLOCK.format(key=KEY), "backlog", "body\n"),
        ("in-progress", FLAG_BLOCK.format(key=KEY), "in-progress", "body\n"),
        ("in-review", FLAG_BLOCK.format(key=KEY), "in-review", "## Verification\n\n- `pytest -q`\n"),
        ("exempt and done", "flag-exempt: alpha\n", "done", "body\n"),
        ("exempt and backlog", "flag-exempt: alpha\n", "backlog", "## Verification\n\n- `pytest -q`\n"),
    ],
)
def test_a_spec_not_landed_or_exempt_is_never_judged_on_the_two_state_test(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], label: str, frontmatter: str, status: str, body: str
):
    root = _landed_root(tmp_path)
    _spec(root, frontmatter, status=status, body=body)

    rc, payload = _tree_json(root, capsys)

    assert rc == 0, label
    assert payload["findings"] == []


def test_a_pre_rule_done_flagged_spec_is_not_judged_on_the_two_state_test(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    rel = _landed_spec(root, "body\n")
    _fixture(tmp_path, tree_keys=[KEY], baseline=[rel])

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["findings"] == []


def test_a_done_spec_with_an_incomplete_flag_block_reports_only_the_missing_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    _spec(root, f"flag:\n  key: {KEY}\n  provider: openfeature-file\n", status="done", body="body\n")

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert _kinds(payload) == ["flag-missing"]


def test_spec_mode_on_the_failing_fixture_carries_the_finding_and_verdict_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    _write(root, "tests/test_flagged.py", "def test_x(): ...\n")
    bad = _landed_spec(root, _verification("tests/test_flagged.py"), name="spec-1-1-bad.md")
    good = _landed_spec(
        root, _verification(_write_test(root, KEY, KIT_TEST, rel="tests/test_good.py")), name="spec-1-2-good.md"
    )
    none = _landed_spec(root, "body\n", name="spec-1-3-none.md")

    rc_bad, out_bad, _ = _run(root, "--spec", bad, capsys=capsys)
    rc_good, out_good, _ = _run(root, "--spec", good, capsys=capsys)
    rc_none, out_none, _ = _run(root, "--spec", none, capsys=capsys)

    payload = json.loads(out_bad)
    assert (rc_bad, rc_good, rc_none) == (1, 0, 1)
    assert payload["verdict"] == "red"
    assert [f["kind"] for f in payload["findings"]] == ["flag-test-not-two-state"]
    assert payload["findings"][0]["path"] == bad
    assert "tests/test_flagged.py" in payload["findings"][0]["message"]
    assert json.loads(out_good)["verdict"] == "pass"
    assert [f["kind"] for f in json.loads(out_none)["findings"]] == ["flag-verification-names-no-test"]


def test_the_text_report_names_the_spec_and_the_kind(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _landed_root(tmp_path)
    rel = _landed_spec(root, "body\n")

    rc, out, _ = _run(root, capsys=capsys)

    fails = [ln for ln in out.splitlines() if ln.startswith("[flag-gate] fail -- flag-verification-names-no-test")]
    assert rc == 1
    assert len(fails) == 1
    assert rel in fails[0]


# --- tracked files, not the working tree (a git checkout) -------------------------------------


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_in_a_git_checkout_only_tracked_files_are_judged_and_read(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])
    tracked = _spec(root, "flag-exempt: alpha\n", name="spec-1-1-tracked.md")
    _write(root, "src/pkg/tracked.py", "x = 1\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    # Written after `git add`: untracked, so neither judged as a spec nor counted as a reader.
    _spec(root, name="spec-1-2-untracked.md")
    _write(root, "src/pkg/untracked.py", f'flag("{ORPHAN_KEY}")\n')

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert payload["specs_judged"] == 1
    assert _kinds(payload) == ["flag-key-orphan"]
    assert tracked.endswith("spec-1-1-tracked.md")


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_a_tracked_spec_deleted_from_the_working_tree_is_not_judged(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    rel = _spec(root)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    (root / rel).unlink()

    rc, payload = _tree_json(root, capsys)

    assert rc == 0
    assert payload["specs_judged"] == 0


# --- a spec that cannot be read is never silently out of scope --------------------------------


@pytest.mark.parametrize(
    "text", ["# no fence at all\n", "---\ntype: feature\nnever closed\n", "---\nkey: [unclosed\n---\n"]
)
def test_a_spec_with_unreadable_frontmatter_is_neither_a_post_rule_fail_and_a_pre_rule_warn(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
):
    root = _fixture(tmp_path)
    post = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-1-1-post.md"
    pre = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-1-2-pre.md"
    _write(root, post, text)
    _write(root, pre, text)
    _fixture(tmp_path, baseline=[pre])

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    assert {(f["kind"], f["path"]) for f in payload["findings"]} == {("flag-missing", post), ("flag-pre-rule", pre)}


# --- --spec: one JSON object -------------------------------------------------------------------


def test_spec_mode_prints_one_json_object_per_verdict_and_exits_1_0_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    red = _spec(root, name="spec-1-1-red.md")
    warn = _spec(root, name="spec-1-2-warn.md")
    ok = _spec(root, "flag-exempt: alpha\n", name="spec-1-3-pass.md")
    _fixture(tmp_path, baseline=[warn])

    results = {}
    for label, rel in (("red", red), ("warn", warn), ("pass", ok)):
        rc, out, _ = _run(root, "--spec", rel, capsys=capsys)
        results[label] = (rc, json.loads(out))  # one object: the whole stdout parses as JSON

    assert results["red"][0] == 1
    assert results["warn"][0] == 0
    assert results["pass"][0] == 0
    for label, (_rc, payload) in results.items():
        assert payload["verdict"] == label
        assert payload["rule_date"] == "2026-09-28"
        assert isinstance(payload["findings"], list)
    assert [f["kind"] for f in results["red"][1]["findings"]] == ["flag-missing"]
    assert [f["kind"] for f in results["warn"][1]["findings"]] == ["flag-pre-rule"]
    assert results["pass"][1]["findings"] == []
    assert results["red"][1]["spec"] == red


def test_spec_mode_reds_an_unknown_exemption_and_a_done_key_absent_from_the_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=["pyforge.test.read"])
    _write(root, "src/pkg/reader.py", 'flag("pyforge.test.read")\n')
    unknown = _spec(root, "flag-exempt: someday\n", name="spec-1-1-unknown.md")
    body = _verification(_write_test(root, "pyforge.test.landed", KIT_TEST))
    landed = _spec(
        root, FLAG_BLOCK.format(key="pyforge.test.landed"), name="spec-1-2-landed.md", status="done", body=body
    )
    backlog = _spec(root, FLAG_BLOCK.format(key="pyforge.test.landed"), name="spec-1-3-backlog.md")

    rc_unknown, out_unknown, _ = _run(root, "--spec", unknown, capsys=capsys)
    rc_landed, out_landed, _ = _run(root, "--spec", landed, capsys=capsys)
    rc_backlog, out_backlog, _ = _run(root, "--spec", backlog, capsys=capsys)

    assert (rc_unknown, rc_landed, rc_backlog) == (1, 1, 0)
    assert json.loads(out_unknown)["findings"][0]["kind"] == "flag-exempt-unknown"
    assert json.loads(out_landed)["findings"][0]["kind"] == "flag-key-not-in-tree"
    assert json.loads(out_backlog)["verdict"] == "pass"


def test_spec_mode_judges_only_its_spec_never_the_tree(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path, tree_keys=[ORPHAN_KEY])  # an orphan key the tree-mode run would red
    _spec(root, name="spec-1-1-red.md")  # and a red spec, which --spec on the passing one must not report
    ok = _spec(root, "flag-exempt: alpha\n", name="spec-1-2-pass.md")

    rc, out, _ = _run(root, "--spec", ok, capsys=capsys)

    assert rc == 0
    assert json.loads(out)["findings"] == []


def test_spec_mode_takes_a_cwd_relative_or_an_absolute_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    root = _fixture(tmp_path)
    rel = _spec(root)
    monkeypatch.chdir(root / Path(rel).parent)

    rc_cwd, out_cwd, _ = _run(root, "--spec", Path(rel).name, capsys=capsys)
    rc_abs, out_abs, _ = _run(root, "--spec", str(root / rel), capsys=capsys)
    rc_rel, out_rel, _ = _run(root, "--spec", rel, capsys=capsys)

    assert rc_cwd == rc_abs == rc_rel == 1
    assert json.loads(out_cwd)["spec"] == json.loads(out_abs)["spec"] == json.loads(out_rel)["spec"] == rel


@pytest.mark.parametrize("target", ["not-a-spec.md", "docs/governance/guild-roster.json"])
def test_spec_mode_on_a_path_that_is_not_a_story_spec_is_unknown_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], target: str
):
    root = _fixture(tmp_path)
    _write(root, "not-a-spec.md", "---\ntype: feature\n---\n")

    rc, out, err = _run(root, "--spec", target, capsys=capsys)

    payload = json.loads(out)
    assert rc == 2
    assert payload["verdict"] == "unknown"
    assert "is not a story spec" in payload["error"]
    assert "unknown" in err


def test_spec_mode_on_a_missing_spec_is_unknown_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)

    rc, out, _ = _run(
        root,
        "--spec",
        "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-9-9-absent.md",
        capsys=capsys,
    )

    payload = json.loads(out)
    assert rc == 2
    assert payload["verdict"] == "unknown"
    assert "no such file" in payload["error"]


# --- unreadable input: exit 2, the input named, never green -------------------------------------


def _break(root: Path, which: str, how: str) -> None:
    path = {
        "roster": root / "docs/governance/guild-roster.json",
        "baseline": root / "docs/governance/flag-rule-baseline.json",
        "tree": root / "src/platform/config/flags.json",
    }[which]
    if how == "missing":
        path.unlink()
    elif how == "not-json":
        path.write_text("{ not json", encoding="utf-8")
    elif how == "wrong-shape":
        path.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
    else:  # pragma: no cover
        raise AssertionError(how)


@pytest.mark.parametrize("which", ["roster", "baseline", "tree"])
@pytest.mark.parametrize("how", ["missing", "not-json", "wrong-shape"])
def test_an_unreadable_roster_baseline_or_tree_exits_2_and_names_what_it_could_not_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], which: str, how: str
):
    root = _fixture(tmp_path)
    _spec(root)  # a red spec is present: an unreadable input must not be reported as exit 1
    _break(root, which, how)
    name = {"roster": "guild-roster.json", "baseline": "flag-rule-baseline.json", "tree": "flags.json"}[which]

    rc, out, err = _run(root, capsys=capsys)

    assert rc == 2
    assert name in err
    assert "unknown" in err
    assert "ok --" not in out


@pytest.mark.parametrize("which", ["roster", "baseline", "tree"])
def test_spec_mode_with_an_unreadable_input_is_unknown_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], which: str
):
    root = _fixture(tmp_path)
    rel = _spec(root, "flag-exempt: alpha\n")
    _break(root, which, "missing")

    rc, out, _ = _run(root, "--spec", rel, capsys=capsys)

    payload = json.loads(out)
    assert rc == 2
    assert payload["verdict"] == "unknown"
    assert payload["findings"] == []


def test_the_json_report_of_an_unreadable_input_is_unknown_never_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _break(root, "tree", "missing")

    rc, payload = _tree_json(root, capsys)

    assert rc == 2
    assert payload["verdict"] == "unknown"
    assert "flags.json" in payload["error"]


def test_a_root_that_does_not_exist_is_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    rc, out, err = _run(tmp_path / "absent", capsys=capsys)

    assert rc == 2
    assert "guild-roster.json" in err
    assert "ok --" not in out


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_a_git_checkout_whose_tracked_files_cannot_be_listed_is_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    (root / ".git").write_text("not a git dir\n", encoding="utf-8")  # `.git` exists but is not a repository

    rc, _out, err = _run(root, capsys=capsys)

    assert rc == 2
    assert "git ls-files" in err


def test_a_crash_is_unknown_exit_2_never_a_false_green_or_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    root = _fixture(tmp_path)

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(flag_gate_check, "judge_tree", boom)

    rc, out, err = _run(root, capsys=capsys)

    assert rc == 2
    assert "crashed: RuntimeError: boom" in err
    assert out == ""


# --- the CLI, as the registry and the pixi task run it ------------------------------------------


def test_the_script_runs_as_a_program_and_exits_with_the_verdict(tmp_path: Path):
    root = _fixture(tmp_path)
    _spec(root)

    red = subprocess.run([sys.executable, str(GATE), "--root", str(root)], capture_output=True, text=True, check=False)
    _fixture(tmp_path, baseline=["_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-1-1-a-story.md"])
    warn = subprocess.run([sys.executable, str(GATE), "--root", str(root)], capture_output=True, text=True, check=False)
    (root / "docs/governance/guild-roster.json").unlink()
    unknown = subprocess.run(
        [sys.executable, str(GATE), "--root", str(root)], capture_output=True, text=True, check=False
    )

    assert (red.returncode, warn.returncode, unknown.returncode) == (1, 0, 2)
    assert red.stdout.splitlines()[-1].startswith("[flag-gate] fail --")
    assert warn.stdout.splitlines()[-1].startswith("[flag-gate] ok --")


def test_the_registry_discovers_the_gate_as_a_repo_detector_with_its_pixi_task():
    found, gaps = detectors.discover()

    row = next((d for d in found if d["name"] == "flag_gate_check"), None)
    assert row is not None, "scripts/flag_gate_check.py is invisible to scripts/detectors.py"
    assert row["scope"] == "repo"
    assert row["task"] == "flag-gate-check"
    assert not [g for g in gaps if "flag_gate_check" in g]


# --- metadata, per-environment defaults, the 90-day clock (Story 34.3) -------------------------


def test_a_flag_on_everywhere_91_days_before_the_run_date_is_one_clock_fail_naming_owner_and_story(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=[KEY])
    _write(root, "src/pkg/reader.py", f'flag("{KEY}")\n')
    _patch_tree_flag(
        root,
        KEY,
        _boolean_flag_entry(KEY, owner="steward", story="76-1-overlays", on_everywhere="2026-01-01"),
    )

    rc, payload = _tree_json(root, capsys, "--run-date", "2026-04-02")

    assert rc == 1
    clock = [f for f in payload["findings"] if f["kind"] == "flag-clock-overdue"]
    assert len(clock) == 1
    assert clock[0]["key"] == KEY
    assert "steward" in clock[0]["message"]
    assert "76-1-overlays" in clock[0]["message"]


def test_a_flag_on_everywhere_90_days_before_the_run_date_has_no_clock_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=[KEY])
    _write(root, "src/pkg/reader.py", f'flag("{KEY}")\n')
    _patch_tree_flag(
        root,
        KEY,
        _boolean_flag_entry(KEY, on_everywhere="2026-01-01"),
    )

    rc, payload = _tree_json(root, capsys, "--run-date", "2026-04-01")

    assert rc == 0
    assert "flag-clock-overdue" not in _kinds(payload)


def test_a_flag_off_in_production_never_gets_a_clock_finding_whatever_its_age(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=[KEY])
    _write(root, "src/pkg/reader.py", f'flag("{KEY}")\n')
    _patch_tree_flag(
        root,
        KEY,
        _boolean_flag_entry(KEY, default_variant="on", on_everywhere="2020-01-01"),
    )
    _write_overlays(
        root,
        {
            "dev": {KEY: "on"},
            "staging": {KEY: "on"},
            "production": {KEY: "off"},
        },
    )

    rc, payload = _tree_json(root, capsys, "--run-date", "2026-10-01")

    assert "flag-clock-overdue" not in _kinds(payload)


def test_a_tree_flag_with_no_owner_metadata_is_one_fail_naming_the_flag_and_the_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=[KEY])
    _write(root, "src/pkg/reader.py", f'flag("{KEY}")\n')
    entry = _boolean_flag_entry(KEY)
    entry["metadata"]["owner"] = ""
    _patch_tree_flag(root, KEY, entry)

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    missing = [f for f in payload["findings"] if f["kind"] == "flag-metadata-missing"]
    assert len(missing) == 1
    assert missing[0]["key"] == KEY
    assert "metadata.owner" in missing[0]["message"]


def test_a_done_flagged_spec_whose_production_default_disagrees_with_the_overlay_is_one_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    _write_overlays(root, {"dev": {KEY: "on"}, "staging": {KEY: "on"}, "production": {KEY: "on"}})
    rel = _landed_spec(root, _verification("tests/test_flagged.py"))

    rc, payload = _tree_json(root, capsys)

    assert rc == 1
    env = [f for f in payload["findings"] if f["kind"] == "flag-default-env-mismatch"]
    assert len(env) == 1
    assert env[0]["path"] == rel
    assert env[0]["key"] == KEY
    assert "production" in env[0]["message"]


def test_the_same_spec_at_backlog_has_no_per_environment_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _landed_root(tmp_path)
    _write_overlays(root, {"dev": {KEY: "on"}, "staging": {KEY: "on"}, "production": {KEY: "on"}})
    _landed_spec(root, _verification("tests/test_flagged.py"), status="backlog")

    rc, payload = _tree_json(root, capsys)

    assert "flag-default-env-mismatch" not in _kinds(payload)


def test_spec_mode_json_carries_the_per_environment_finding_and_verdict_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _landed_root(tmp_path)
    _write_overlays(root, {"production": {KEY: "on"}})
    rel = _landed_spec(root, _verification("tests/test_flagged.py"))
    _write_test(root, KEY, KIT_TEST)

    rc, out, _ = _run(root, "--spec", rel, capsys=capsys)
    payload = json.loads(out)

    assert rc == 1
    assert payload["verdict"] == "red"
    assert "flag-default-env-mismatch" in _kinds(payload)


def test_a_malformed_overlay_document_is_exit_2_and_names_the_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _write_overlays(root, {"dev": "not-a-mapping"})

    rc, _out, err = _run(root, capsys=capsys)

    assert rc == 2
    assert "flag-overlays.json" in err


# --- the live tree: what holds whatever stories it carries ---------------------------------------


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_every_key_the_live_tree_holds_is_read_in_src_or_scripts():
    tree = flag_gate_check.load_tree(REPO_ROOT)

    assert flag_gate_check.orphan_keys(REPO_ROOT, tree) == []


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_the_live_tree_has_no_unknown_exemption_no_landed_key_missing_and_no_orphan():
    # Deliberately not "exit 0": a post-rule story that lacks both blocks is a FAIL owned by its Smith,
    # and this suite must not turn red for it a second time; the same holds for a `done` flagged story whose
    # Verification names no two-state test (Story 34.5), which is equally its own Smith's to fix.
    # It pins the honesty of the tree and the roster.
    owned = {
        flag_gate_check.K_MISSING,
        flag_gate_check.K_NO_TEST,
        flag_gate_check.K_TEST_MISSING,
        flag_gate_check.K_NOT_TWO_STATE,
        flag_gate_check.K_DEFAULT_ENV,
    }
    inputs = flag_gate_check.load_inputs(REPO_ROOT)

    _judged, findings = flag_gate_check.judge_tree(REPO_ROOT, inputs)

    assert {f.kind for f in findings} <= {*owned, flag_gate_check.K_PRE_RULE}
    assert [f for f in findings if f.severity == flag_gate_check.FAIL and f.kind not in owned] == []


# --- one declared source, outside every station --------------------------------------------------


def test_the_gate_holds_no_copy_of_the_exemption_list_and_names_no_live_key():
    source = GATE.read_text(encoding="utf-8")

    assert [v for v in flag_rule.load_exemptions() if v in source] == []
    assert [k for k in flag_gate_check.load_tree(REPO_ROOT) if k in source] == []


def test_the_gate_imports_no_station_module_and_never_reads_the_second_tree():
    source = GATE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = [
        alias.name if isinstance(node, ast.Import) else (node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [node])
    ]

    assert not [m for m in imported if m == "pyforge" or m.startswith("pyforge.")]
    assert ".steward/flags.json" not in source  # steward Story 76.3 folds that second tree into the one tree


KIT_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-testing-kit" / "src" / "pyforge" / "testing_kit"


def test_the_gates_kit_helper_is_what_marshal_74_1_landed():
    """A rename in the kit would silently red the first story that uses it; read the kit, never import it."""
    helper = flag_gate_check._KIT_HELPER
    flags = ast.parse((KIT_SRC / "flags.py").read_text(encoding="utf-8"))
    package = ast.parse((KIT_SRC / "__init__.py").read_text(encoding="utf-8"))

    defined = {node.name for node in flags.body if isinstance(node, ast.FunctionDef)}
    reexported = {
        alias.name
        for node in package.body
        if isinstance(node, ast.ImportFrom) and node.module == "pyforge.testing_kit.flags"
        for alias in node.names
    }
    assert helper in defined
    assert helper in reexported
    # and the gate's own import pattern accepts the module the kit defines it in
    assert flag_gate_check._KIT_IMPORT.search(f"from pyforge.testing_kit.flags import {helper}\n")
    assert flag_gate_check._KIT_CALL.search(f'@{helper}("{KEY}")')


def test_the_gate_declares_itself_a_repo_scope_detector():
    tree = ast.parse(GATE.read_text(encoding="utf-8"))
    declared = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DETECTOR" for t in node.targets)
    ]

    assert declared == [{"scope": "repo"}]
