"""Story 121.2 (spec-python-foundry-cutover fnd:CAP-8, fnd:CAP-9): ``steward cutover plan`` generates and checks the
capability ledger, its two write modes behind ``pyforge.steward.cutover_ledger_write``; ``flip`` refuses a running
loop and stamps the Realization log (Story 44.12)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml
from pyforge.core.cutover_root import CutoverRootError, read_cutover_root
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward import cli
from pyforge.steward.cutover import (
    LEDGER_WRITE_FLAG,
    REALIZATION_LOG,
    CutoverDuty,
    flip_root,
    loops_running,
)
from pyforge.steward.cutover_ledger import DEFAULT_LEDGER
from pyforge.steward.interfaces import DutyResult

flag_provider = make_flag_provider_fixture()


def test_flip_refused_while_loop_running(tmp_path: Path) -> None:
    flags = tmp_path / "flags.json"
    flags.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {
                            "local-recipes": "local-recipes",
                            "foundry": "foundry",
                        },
                        "defaultVariant": "local-recipes",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    loops = tmp_path / "loops" / "x"
    loops.mkdir(parents=True)
    (loops / "state.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
    realization = tmp_path / "dream.md"
    realization.write_text("## Realization log\n", encoding="utf-8")
    assert loops_running(tmp_path / "loops")
    with pytest.raises(CutoverRootError, match="loop is running"):
        flip_root(flags, "foundry", realization, loop_home=tmp_path / "loops")
    assert read_cutover_root(flags) == "local-recipes"


# --- Story 76.1: a flip is not masked by the per-environment overlay -------------


# Story 76.2: every flag carries its clock. Neither fixture flag is ON in every environment
# (a string flag never is; `pyforge.other` is off in the tree), so both clocks stay empty.
_CLOCKLESS = {
    "owner": "steward",
    "story": "76-2-a-fixture",
    "created": "2026-09-01",
    "on_everywhere": "",
    "cleanup_by": "",
}


def _flag_tree(directory: Path, overlays: object | None = None) -> Path:
    flags = directory / "flags.json"
    flags.write_text(
        json.dumps(
            {
                "flags": {
                    "pyforge.cutover_root": {
                        "state": "ENABLED",
                        "variants": {"local-recipes": "local-recipes", "foundry": "foundry"},
                        "defaultVariant": "local-recipes",
                        "metadata": _CLOCKLESS,
                    },
                    "pyforge.other": {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": "off",
                        "metadata": _CLOCKLESS,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    if overlays is not None:
        (directory / "flag-overlays.json").write_text(json.dumps(overlays), encoding="utf-8")
    return flags


_PINNED = {
    "dev": {"pyforge.cutover_root": "local-recipes", "pyforge.other": "off"},
    "staging": {"pyforge.cutover_root": "local-recipes", "pyforge.other": "on"},
    "production": {"pyforge.cutover_root": "local-recipes"},
}


def test_the_reader_sees_the_overlay_pinned_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flags = _flag_tree(tmp_path, {**_PINNED, "staging": {"pyforge.cutover_root": "foundry"}})
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "staging")
    assert read_cutover_root(flags) == "foundry"
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")
    assert read_cutover_root(flags) == "local-recipes"


@pytest.mark.parametrize("target", ["foundry", "local-recipes"])
def test_flip_then_read_agree_in_every_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    from pyforge.core import flags as core_flags

    flags = _flag_tree(tmp_path, _PINNED)
    other = "foundry" if target == "local-recipes" else "local-recipes"
    flip_root(flags, other, tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    flip_root(flags, target, tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    for environment in core_flags.ENVIRONMENTS:
        monkeypatch.setenv("PYFORGE_ENVIRONMENT", environment)
        assert read_cutover_root(flags) == target, environment
        rendered = json.loads(core_flags.render(environment, flags_path=flags))
        assert rendered["flags"]["pyforge.cutover_root"]["defaultVariant"] == target, environment


def test_flip_touches_only_the_cutover_key_of_the_overlay(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path, _PINNED)
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    overlays = json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))
    assert overlays == {
        "dev": {"pyforge.cutover_root": "foundry", "pyforge.other": "off"},
        "staging": {"pyforge.cutover_root": "foundry", "pyforge.other": "on"},
        "production": {"pyforge.cutover_root": "foundry"},
    }
    assert json.loads(flags.read_text(encoding="utf-8"))["flags"]["pyforge.cutover_root"]["defaultVariant"] == "foundry"


def test_flip_leaves_an_environment_that_does_not_name_the_flag_alone(tmp_path: Path) -> None:
    flags = _flag_tree(
        tmp_path, {"dev": {"pyforge.other": "on"}, "production": {"pyforge.cutover_root": "local-recipes"}}
    )
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    overlays = json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))
    assert overlays == {"dev": {"pyforge.other": "on"}, "production": {"pyforge.cutover_root": "foundry"}}


def test_flip_creates_an_absent_flag_with_a_composable_clock(tmp_path: Path) -> None:
    """A tree without the key gets it, carrying metadata, so a sibling overlay still composes."""
    from pyforge.core import flags as core_flags

    flags = tmp_path / "flags.json"
    flags.write_text(json.dumps({"flags": {}}), encoding="utf-8")
    (tmp_path / "flag-overlays.json").write_text(json.dumps({"production": {}}), encoding="utf-8")
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    created = json.loads(flags.read_text(encoding="utf-8"))["flags"]["pyforge.cutover_root"]
    assert created["defaultVariant"] == "foundry"
    assert created["metadata"]["owner"] == "steward"
    assert created["metadata"]["story"].startswith("44-12-")
    assert created["metadata"]["on_everywhere"] == created["metadata"]["cleanup_by"] == ""
    core_flags.check_metadata({"pyforge.cutover_root": created})
    assert read_cutover_root(flags) == "foundry"


def test_flip_without_a_sibling_overlay_writes_no_overlay(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert not (tmp_path / "flag-overlays.json").exists()
    assert read_cutover_root(flags) == "foundry"


def test_flip_refuses_a_broken_overlay_before_writing_anything(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    (tmp_path / "flag-overlays.json").write_text("{not json", encoding="utf-8")
    before = flags.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="flip refused"):
        flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert flags.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("overlays", "named"),
    [
        ({"dev": {"pyforge.typo": "off"}}, "pyforge.typo"),
        ({"dev": {"pyforge.other": "maybe"}}, "maybe"),
        ({"qa": {"pyforge.other": "on"}}, "qa"),
        ({"dev": {"pyforge.other": {"variants": {}}}}, "pyforge.other"),
    ],
)
def test_flip_refuses_an_invalid_overlay_entry_before_writing_anything(
    tmp_path: Path, overlays: object, named: str
) -> None:
    flags = _flag_tree(tmp_path, overlays)
    overlays_path = tmp_path / "flag-overlays.json"
    tree_before = flags.read_text(encoding="utf-8")
    overlays_before = overlays_path.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="flip refused") as excinfo:
        flip_root(flags, "foundry", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert named in str(excinfo.value)
    assert flags.read_text(encoding="utf-8") == tree_before
    assert overlays_path.read_text(encoding="utf-8") == overlays_before


# --- loop and flip edges ---------------------------------------------------------


def test_loops_running_reads_past_unreadable_and_idle_state(tmp_path: Path) -> None:
    home = tmp_path / "loops"
    for run, text in {"a": "{not json", "b": json.dumps({"status": "done"}), "c": json.dumps({})}.items():
        (home / run).mkdir(parents=True)
        (home / run / "state.json").write_text(text, encoding="utf-8")
    assert loops_running(home) is False
    (home / "d").mkdir()
    (home / "d" / "state.json").write_text(json.dumps({"state": "Active"}), encoding="utf-8")
    assert loops_running(home) is True


def test_loops_running_without_a_loop_home_is_false(tmp_path: Path) -> None:
    assert loops_running(tmp_path / "absent") is False


def test_flip_refuses_an_unknown_variant_before_touching_the_tree(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    before = flags.read_text(encoding="utf-8")
    with pytest.raises(CutoverRootError, match="unknown cutover_root variant 'elsewhere'"):
        flip_root(flags, "elsewhere", tmp_path / "no-dream.md", loop_home=tmp_path / "loops")
    assert flags.read_text(encoding="utf-8") == before


def test_flip_stamps_the_realization_log_when_it_exists(tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    realization = tmp_path / "dream.md"
    realization.write_text("## Realization log\n", encoding="utf-8")
    flip_root(flags, "foundry", realization, loop_home=tmp_path / "loops")
    text = realization.read_text(encoding="utf-8")
    assert text.startswith("## Realization log\n")
    assert text.endswith("`pyforge.cutover_root` → `foundry`\n")


# --- the duty: one live Spec in a checkout as its cwd --------------------------------

# Spelled out for the flag gate's two-state check, which reads the key literally (Story 34.5).
_SWITCH = "pyforge.steward.cutover_ledger_write"
_SPEC = Path("_bmad-output/projects/pyforge-demo/planning-artifacts/specs/spec-pyforge-demo/SPEC.md")
_CAP_ONE = "pyforge-demo:CAP-1"
_CAP_TWO = "pyforge-demo:CAP-2"


def _write_spec(root: Path, *numbers: int) -> None:
    """One live Spec whose capabilities read shipped, so a fresh ledger row draws only the defaulted-row warning."""
    lines = ["---", "title: demo", "status: ready", "---", "", "## Capabilities", ""]
    lines += [f"- **CAP-{n} — Demo capability {n}.** (shipped 2026-11-10)" for n in numbers]
    path = root / _SPEC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def duty_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout holding one live Spec as the duty's cwd, with HOME and every env override pinned inside tmp_path."""
    root = (tmp_path / "repo").resolve()
    (root / ".git").mkdir(parents=True)
    (root / REALIZATION_LOG).parent.mkdir(parents=True)
    _write_spec(root, 1)
    monkeypatch.chdir(root)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for name in ("PYFORGE_FLAGS_PATH", "PYFORGE_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    return root


def _run(**kwargs: object) -> DutyResult:
    return CutoverDuty().run(argparse.Namespace(**kwargs))


def _switch(monkeypatch: pytest.MonkeyPatch, on: bool) -> list[str]:
    """Pin the write switch and return the keys the run reads.

    The reader is patched, never pointed at a one-key flag tree: that would pin the process-wide OpenFeature
    provider for every later test on the worker.
    """
    reads: list[str] = []

    def read_boolean(key: str, default: bool = False, **_kw: object) -> bool:
        reads.append(key)
        return on if key == _SWITCH else default

    monkeypatch.setattr("pyforge.core.flags.read_boolean", read_boolean)
    return reads


def _regenerate(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Write the default ledger with the switch on; return its path."""
    _switch(monkeypatch, True)
    assert _run(cutover_verb="plan", plan_mode="regenerate").ok is True
    return Path.cwd() / DEFAULT_LEDGER


def test_duty_without_a_verb_names_plan_and_flip(duty_repo: Path) -> None:
    for verb in (None, "apply"):
        result = _run(cutover_verb=verb)
        assert result.ok is False
        assert result.summary == "cutover: need plan or flip"


@pytest.mark.parametrize("flags", [None, "missing.json"])
def test_duty_flip_without_a_flag_tree_says_so(duty_repo: Path, tmp_path: Path, flags: str | None) -> None:
    explicit = str(tmp_path / flags) if flags else None
    result = _run(cutover_verb="flip", to="foundry", flags=explicit)
    assert result.ok is False
    assert result.summary == "cutover flip: no flags.json"


def test_duty_flip_sets_the_root_and_stamps_the_realization_log(duty_repo: Path, tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    log = duty_repo / REALIZATION_LOG
    log.write_text("## Realization log\n", encoding="utf-8")
    result = _run(cutover_verb="flip", to="foundry", flags=str(flags))
    assert result.ok is True
    assert result.summary == "cutover flip → foundry"
    assert read_cutover_root(flags) == "foundry"
    assert log.read_text(encoding="utf-8").endswith("`pyforge.cutover_root` → `foundry`\n")


def test_duty_flip_refused_by_a_running_loop_is_a_failed_result(duty_repo: Path, tmp_path: Path) -> None:
    flags = _flag_tree(tmp_path)
    state = tmp_path / "home/.bmad-loops/run-1/state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"status": "running"}), encoding="utf-8")
    before = flags.read_text(encoding="utf-8")
    result = _run(cutover_verb="flip", to="foundry", flags=str(flags))
    assert result.ok is False
    assert result.summary == "cutover: flip refused: a Marshal loop is running"
    assert flags.read_text(encoding="utf-8") == before


# --- plan: the capability ledger's generator, its check and the write switch -------------------


def test_the_parser_offers_plan_and_flip_and_refuses_apply(duty_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert LEDGER_WRITE_FLAG == _SWITCH
    assert "fnd:CAP-8" in cli._HELP["cutover"] and "fnd:CAP-9" in cli._HELP["cutover"]
    parser = cli.build_parser()
    assert parser.parse_args(["cutover", "plan"]).plan_mode == "check"
    for mode in ("regenerate", "append", "check"):
        assert parser.parse_args(["cutover", "plan", f"--{mode}"]).plan_mode == mode
    ns = parser.parse_args(["cutover", "plan", "--ledger", "elsewhere.yaml", "--json"])
    assert (ns.ledger, ns.json) == ("elsewhere.yaml", True)
    for argv in (["cutover", "apply", "--phase", "1a"], ["cutover", "plan", "--regenerate", "--check"]):
        with pytest.raises(SystemExit) as refused:
            parser.parse_args(argv)
        assert refused.value.code == cli.EXIT_USAGE
    capsys.readouterr()
    assert cli.main(["cutover", "apply", "--phase", "1a"]) == cli.EXIT_USAGE
    assert "invalid choice" in capsys.readouterr().err
    assert not (duty_repo / DEFAULT_LEDGER).exists()


def test_duty_regenerates_the_ledger_from_a_subdirectory(duty_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No flag tree in reach: the write switch reads its default, on."""
    monkeypatch.chdir(duty_repo / "docs/dreams")
    ledger = duty_repo / DEFAULT_LEDGER
    first = _run(cutover_verb="plan", plan_mode="regenerate")
    assert first.ok is True
    assert first.summary == (
        f"cutover plan --regenerate: {ledger}: written; 1 added, 0 dropped, 0 remoded\n  defaulted-row {_CAP_ONE}"
    )
    assert first.details == {
        "mode": "regenerate",
        "ledger": str(ledger),
        "changed": True,
        "added": [_CAP_ONE],
        "dropped": [],
        "remoded": [],
    }
    written = ledger.read_bytes()
    again = _run(cutover_verb="plan", plan_mode="regenerate")
    assert again.ok is True
    assert again.summary == f"cutover plan --regenerate: {ledger}: unchanged; 0 added, 0 dropped, 0 remoded"
    assert ledger.read_bytes() == written


def test_duty_appends_only_the_new_row_to_a_ledger_named_from_the_cwd(
    duty_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reads = _switch(monkeypatch, True)
    monkeypatch.chdir(duty_repo / "docs")
    ledger = duty_repo / "docs/ledger.yaml"
    assert _run(cutover_verb="plan", plan_mode="regenerate", ledger="ledger.yaml").ok is True
    before = {row["id"]: row for row in yaml.safe_load(ledger.read_text(encoding="utf-8"))["capabilities"]}
    _write_spec(duty_repo, 1, 2)
    result = _run(cutover_verb="plan", plan_mode="append", ledger="ledger.yaml")
    assert result.ok is True
    assert result.details["ledger"] == str(ledger)
    assert result.details["added"] == [_CAP_TWO]
    after = {row["id"]: row for row in yaml.safe_load(ledger.read_text(encoding="utf-8"))["capabilities"]}
    assert set(after) == {_CAP_ONE, _CAP_TWO}
    assert after[_CAP_ONE] == before[_CAP_ONE]
    assert reads == [_SWITCH, _SWITCH]
    assert not (duty_repo / DEFAULT_LEDGER).exists()


def test_duty_plan_check_ok(duty_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = _regenerate(monkeypatch)
    before = ledger.read_bytes()
    reads = _switch(monkeypatch, True)
    result = _run(cutover_verb="plan")  # a bare `plan` is --check
    assert result.ok is True
    lines = result.summary.splitlines()
    assert lines[0] == f"cutover plan --check: {ledger}: 0 findings, 1 warning"
    assert lines[1].startswith(f"  warning defaulted-row {_CAP_ONE}: ")
    assert result.details["mode"] == "check"
    assert result.details["findings"] == []
    assert [(item["code"], item["id"]) for item in result.details["warnings"]] == [("defaulted-row", _CAP_ONE)]
    assert reads == []  # --check never reads the write switch
    assert cli.main(["cutover", "plan"]) == 0
    assert ledger.read_bytes() == before


def test_duty_plan_check_findings_exit_1(
    duty_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger = _regenerate(monkeypatch)
    _write_spec(duty_repo, 1, 2)  # a live capability the ledger has no row for
    before = ledger.read_bytes()
    result = _run(cutover_verb="plan", plan_mode="check")
    assert result.ok is False
    assert result.summary.splitlines()[0] == f"cutover plan --check: {ledger}: 1 finding, 1 warning"
    assert f"\n  finding unclassified {_CAP_TWO}: " in result.summary
    assert [(item["code"], item["id"]) for item in result.details["findings"]] == [("unclassified", _CAP_TWO)]
    assert "exit_code" not in result.details
    capsys.readouterr()
    assert cli.main(["cutover", "plan", "--check"]) == cli.EXIT_FAILED
    assert f"finding unclassified {_CAP_TWO}" in capsys.readouterr().err
    assert ledger.read_bytes() == before


def test_duty_plan_bad_ledger_is_a_failed_result(
    duty_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _switch(monkeypatch, True)
    absent = _run(cutover_verb="plan", plan_mode="check")
    assert absent.ok is False
    assert absent.summary == f"cutover: {duty_repo / DEFAULT_LEDGER}: no capability ledger to check"
    bad = tmp_path / "bad.yaml"
    bad.write_text("{not yaml", encoding="utf-8")
    for mode in ("check", "regenerate", "append"):
        result = _run(cutover_verb="plan", plan_mode=mode, ledger=str(bad))
        assert result.ok is False, mode
        assert result.summary.startswith(f"cutover: {bad}: not YAML"), mode
        assert bad.read_text(encoding="utf-8") == "{not yaml"


def test_duty_plan_refuses_an_unknown_mode_with_the_usage_code(duty_repo: Path) -> None:
    result = _run(cutover_verb="plan", plan_mode="fold")
    assert result.ok is False
    assert result.summary == "cutover plan: unknown mode 'fold'; pass --regenerate, --append or --check"
    assert result.details == {"exit_code": cli.EXIT_USAGE}
    assert not (duty_repo / DEFAULT_LEDGER).exists()


def test_duty_plan_json_reports_on_stdout_even_when_the_check_fails(
    duty_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _switch(monkeypatch, True)
    ledger = duty_repo / DEFAULT_LEDGER
    assert cli.main(["cutover", "plan", "--regenerate", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "mode": "regenerate",
        "ledger": str(ledger),
        "changed": True,
        "added": [_CAP_ONE],
        "dropped": [],
        "remoded": [],
    }
    _write_spec(duty_repo, 1, 2)
    assert cli.main(["cutover", "plan", "--json"]) == cli.EXIT_FAILED
    checked = json.loads(capsys.readouterr().out)
    assert (checked["mode"], checked["ledger"], checked["ok"]) == ("check", str(ledger), False)
    assert [(item["code"], item["id"]) for item in checked["findings"]] == [("unclassified", _CAP_TWO)]


@pytest.mark.parametrize("mode", ["regenerate", "append"])
def test_write_switch_off_refuses_the_write_mode_and_writes_nothing(
    duty_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], mode: str
) -> None:
    ledger = _regenerate(monkeypatch)
    _write_spec(duty_repo, 1, 2)  # either write mode would now add a row
    before = ledger.read_bytes()
    reads = _switch(monkeypatch, False)
    result = _run(cutover_verb="plan", plan_mode=mode)
    assert result.ok is False
    assert result.summary == (
        f"cutover plan --{mode}: refused, the kill switch {_SWITCH} is off; nothing was written (plan --check still runs)"
    )
    assert result.details == {"exit_code": cli.EXIT_USAGE, "mode": mode, "ledger": str(ledger)}
    assert reads == [_SWITCH]
    capsys.readouterr()
    assert cli.main(["cutover", "plan", f"--{mode}"]) == cli.EXIT_USAGE
    assert "refused, the kill switch" in capsys.readouterr().err
    assert ledger.read_bytes() == before


def test_write_switch_off_leaves_plan_check_running(duty_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = _regenerate(monkeypatch)
    before = ledger.read_bytes()
    reads = _switch(monkeypatch, False)
    result = _run(cutover_verb="plan", plan_mode="check")
    assert result.ok is True
    assert result.summary.startswith(f"cutover plan --check: {ledger}: 0 findings")
    assert cli.main(["cutover", "plan", "--check"]) == 0
    assert _SWITCH not in reads
    assert ledger.read_bytes() == before


@flag_states("pyforge.steward.cutover_ledger_write")
def test_the_ledger_write_flag_gates_the_write_modes_only(
    flag_provider: dict[str, bool], duty_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on = flag_provider[_SWITCH]
    ledger = _regenerate(monkeypatch)
    _write_spec(duty_repo, 1, 2)
    before = ledger.read_bytes()
    _switch(monkeypatch, on)
    wrote = _run(cutover_verb="plan", plan_mode="append")
    assert wrote.ok is on
    assert (ledger.read_bytes() != before) is on
    assert wrote.details.get("exit_code") == (None if on else cli.EXIT_USAGE)
    # --check runs in both states and judges what is on disk: the new capability has a row only when on.
    checked = _run(cutover_verb="plan", plan_mode="check")
    assert checked.summary.startswith(f"cutover plan --check: {ledger}: ")
    assert checked.ok is on
