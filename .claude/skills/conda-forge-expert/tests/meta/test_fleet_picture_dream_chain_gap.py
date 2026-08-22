"""Meta-test: `dream_chain_gap_findings()` + `_dream_chain_watch_lines()`
in fleet_picture.py.

Story 12.4 (CAP-4) wires `Source.DREAM_CHAIN`'s `dream-without-spec` FAIL
findings (INV-1 -- Dreams fleet-wide with no Spec) into `fleet_picture.py`'s
ATTENTION block: `dream_chain_gap_findings()` shells out to `sys.executable
-m pyforge.doctor.sources dream-chain --json` and keeps `dream-without-spec`
items plus every unevaluable-equivalent shape (per-cause
`dream-chain-unevaluable` items AND `degrade_on_exception`'s total-degrade
WARN, emitted under `check="dream-chain"` -- the same `check` as the vacuous
OK, separable only by `status`); the pure `_dream_chain_watch_lines()`
helper assembles the `watch` lines `main()` prints.

The ONE deliberate deviation from the sibling consumers' `check=True`
(load-bearing, pinned below): `dream-without-spec` findings are FAIL-status,
so the CLI exits 2 on ANY real gap -- exit codes {0, 2} are BOTH success;
any other exit raises `CalledProcessError` (stderr attached). `main()`'s own
ATTENTION block wraps the call in a `try/except Exception:
watch.append(...)` idiom (same as every other ATTENTION probe in that file);
`dream_chain_gap_findings()` itself does NOT catch failures -- it raises,
and degrading to a "could not check" line is the caller's job (spec
Boundaries).

Same `_load_fleet_picture()` harness as
`test_fleet_picture_verification_staleness.py` (that file isn't a package,
so it's loaded via `importlib.util.spec_from_file_location`).
`subprocess.run` is monkeypatched rather than actually invoking `python -m
pyforge.doctor.sources` -- no real Dream/Spec fleet state is needed to
exercise these functions. `_dream_chain_watch_lines` is pure and tested
directly, no monkeypatching at all.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def _fake_run(findings: list[dict], returncode: int = 0,
              stdout: str | None = None, stderr: str = ""):
    """Build a `subprocess.run` stand-in returning `findings` as the
    `--json` stdout a real `python -m pyforge.doctor.sources dream-chain
    --json` invocation would print. `returncode` is settable -- the exit-code
    contract ({0, 2} accepted, anything else raises) is the load-bearing
    deviation this file exists to pin."""

    def _run(cmd, **kwargs):
        assert cmd[0] == sys.executable
        assert cmd[1:4] == ["-m", "pyforge.doctor.sources", "dream-chain"]
        assert "--json" in cmd
        out = json.dumps(findings) if stdout is None else stdout
        return _FakeCompletedProcess(out, returncode=returncode, stderr=stderr)

    return _run


def _gap_finding(slug: str) -> dict:
    """`chain.py::_gather_dream_chain`'s INV-1 shape (status lowercase, as
    `--json` serializes it)."""
    return {
        "source": "dream-chain",
        "check": "dream-without-spec",
        "status": "fail",
        "message": f"{slug} (owner=doctor) has no Spec — author a Spec",
        "evidence": {"inv": "INV-1", "subject": slug, "owner": "doctor",
                     "status": "ready", "remedy": "author a Spec"},
    }


def _unevaluable_finding(subject: str) -> dict:
    """Per-cause unevaluable shape (`_collect_dreams`/`_collect_specs`'s
    unreadable-input entries)."""
    return {
        "source": "dream-chain",
        "check": "dream-chain-unevaluable",
        "status": "warn",
        "message": f"{subject} could not be read",
        "evidence": {"inv": "INV-0", "subject": subject, "owner": "",
                     "status": "", "remedy": ""},
    }


def _total_degrade_finding() -> dict:
    """`sources/__init__.py::degrade_on_exception`'s shape: the WHOLE gather
    degraded to ONE WARN named after its check argument -- the same `check`
    as the vacuous OK, separable only by `status`."""
    return {
        "source": "dream-chain",
        "check": "dream-chain",
        "status": "warn",
        "message": "dream-chain could not be evaluated here — "
                   "RuntimeError: boom",
        "evidence": {"exception": "RuntimeError"},
    }


def _ok_finding() -> dict:
    """The vacuous clean-chain OK -- same `check` as the total degrade."""
    return {
        "source": "dream-chain",
        "check": "dream-chain",
        "status": "ok",
        "message": "every Spec links a Dream, every Dream has a Spec in its "
                   "owner's project, and every project uses the sharded "
                   "planning tree",
        "evidence": {"dreams": 40, "specs": 40},
    }


def _other_kind(check: str, subject: str) -> dict:
    """A dream-chain kind CAP-4 does NOT count (INV-0/2/3 kinds)."""
    return {
        "source": "dream-chain",
        "check": check,
        "status": "fail",
        "message": f"{subject}: {check}",
        "evidence": {"inv": "INV-0", "subject": subject, "owner": "",
                     "status": "", "remedy": ""},
    }


# --- dream_chain_gap_findings: exit-code contract + filter ------------------


def test_gaps_at_exit_2_are_returned_not_raised(monkeypatch):
    """LOAD-BEARING: FAIL findings make the CLI exit 2 (verified live: 17
    gaps today) -- a verbatim `check=True` sibling mirror would raise on
    exactly this case and degrade every real invocation."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([_gap_finding("alpha"), _gap_finding("beta")], returncode=2),
    )

    result = mod.dream_chain_gap_findings()

    assert len(result) == 2
    assert all(f["check"] == "dream-without-spec" for f in result)
    assert {f["evidence"]["subject"] for f in result} == {"alpha", "beta"}


def test_filter_keeps_both_unevaluable_shapes(monkeypatch):
    """Per-cause `dream-chain-unevaluable` AND the total-degrade WARN
    (`check="dream-chain"`, `status="warn"`) both mean "the count cannot be
    trusted" -- both survive the filter, alongside the gaps."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([
            _gap_finding("alpha"),
            _unevaluable_finding("docs/dreams"),
            _total_degrade_finding(),
        ], returncode=2),
    )

    result = mod.dream_chain_gap_findings()

    assert len(result) == 3
    assert {f["check"] for f in result} == {
        "dream-without-spec", "dream-chain-unevaluable", "dream-chain",
    }


def test_other_kinds_and_the_vacuous_ok_are_filtered_out(monkeypatch):
    """CAP-4 is the Dreams-without-Spec count ONLY: INV-0/2 kinds drop, and
    the vacuous OK -- the same `check` value as the total degrade, separable
    only by `status` -- drops too."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([
            _other_kind("spec-without-dream-link", "spec-x"),
            _other_kind("owner-unassigned", "y"),
            _other_kind("spec-location-mismatch", "spec-z"),
            _ok_finding(),
            _gap_finding("alpha"),
        ], returncode=2),
    )

    result = mod.dream_chain_gap_findings()

    assert len(result) == 1
    assert result[0]["check"] == "dream-without-spec"
    assert result[0]["evidence"]["subject"] == "alpha"


def test_clean_chain_ok_only_filters_to_empty_at_exit_0(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run", _fake_run([_ok_finding()], returncode=0)
    )

    assert mod.dream_chain_gap_findings() == []


def test_unevaluable_only_at_exit_0_is_returned(monkeypatch):
    """WARN-only output exits 0 (WARN never changes the exit code) -- the
    unevaluable-only fixture uses ITS real exit code, not 2."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([_unevaluable_finding("docs/dreams")], returncode=0),
    )

    result = mod.dream_chain_gap_findings()

    assert len(result) == 1
    assert result[0]["check"] == "dream-chain-unevaluable"


def test_total_degrade_only_at_exit_0_is_returned(monkeypatch):
    """The exact masking the spec's review pass 1 caught: a totally-degraded
    detector exits 0 with ONE `check="dream-chain"` WARN -- it must come
    back, never filter to a clean-looking `[]`."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([_total_degrade_finding()], returncode=0),
    )

    result = mod.dream_chain_gap_findings()

    assert len(result) == 1
    assert result[0]["check"] == "dream-chain"
    assert result[0]["status"] == "warn"


@pytest.mark.parametrize("code", [1, 127])
def test_exit_code_outside_0_2_raises_calledprocesserror(monkeypatch, code):
    """Any exit outside {0, 2} raises, with the cmd shape and stderr
    attached (the caller's `try/except` degrades to one "could not check"
    line)."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([], returncode=code, stdout="", stderr="boom"),
    )

    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        mod.dream_chain_gap_findings()

    e = excinfo.value
    assert e.returncode == code
    # cmd shape asserted on the raise path too, not only inside _fake_run
    assert e.cmd[0] == sys.executable
    assert e.cmd[1:4] == ["-m", "pyforge.doctor.sources", "dream-chain"]
    assert "--json" in e.cmd
    assert e.stderr == "boom"


@pytest.mark.parametrize("bad_stdout", ["not json", ""])
def test_malformed_stdout_raises_jsondecodeerror(monkeypatch, bad_stdout):
    """Non-JSON stdout raises -- including EMPTY stdout at exit 2, the
    argparse-usage-error case the exit-code gate alone cannot distinguish
    from a real gap run (the docstring's honest limit: `json.loads` is the
    guard that actually fires there)."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([], returncode=2, stdout=bad_stdout),
    )

    with pytest.raises(json.JSONDecodeError):
        mod.dream_chain_gap_findings()


# --- _dream_chain_watch_lines: pure line assembly ---------------------------


def test_watch_lines_count_line_format():
    mod = _load_fleet_picture()

    lines = mod._dream_chain_watch_lines(
        [_gap_finding("alpha"), _gap_finding("beta")]
    )

    assert lines == [
        (
            "2 Dream(s) with no Spec (e.g. alpha, beta) -- run "
            "`pixi run -e local-recipes dream-chain-check` for the full list"
        )
    ]


def test_watch_lines_caps_examples_at_three_slugs():
    mod = _load_fleet_picture()
    gaps = [_gap_finding(s) for s in ["a1", "b2", "c3", "d4", "e5"]]

    lines = mod._dream_chain_watch_lines(gaps)

    assert len(lines) == 1
    assert lines[0].startswith("5 Dream(s) with no Spec")
    assert "a1" in lines[0] and "b2" in lines[0] and "c3" in lines[0]
    assert "d4" not in lines[0] and "e5" not in lines[0]


def test_watch_lines_sanitizes_each_slug():
    """An externally-sourced slug must never inject an extra bullet line
    (newline) or flood the block (length) -- first line, 40-char cap,
    applied PER SLUG, not to the joined string."""
    mod = _load_fleet_picture()

    lines = mod._dream_chain_watch_lines([
        _gap_finding("evil\ninjected-bullet"),
        _gap_finding("x" * 60),
    ])

    assert len(lines) == 1
    assert "\n" not in lines[0]
    assert "injected-bullet" not in lines[0]
    assert "evil" in lines[0]
    assert "x" * 40 in lines[0]
    assert "x" * 41 not in lines[0]


def test_watch_lines_null_evidence_falls_back_to_placeholder():
    """`evidence` present-but-null (JSON `null`) must not crash the
    assembly -- the `(f.get("evidence") or {})` guard yields the `?`
    placeholder slug."""
    mod = _load_fleet_picture()
    finding = _gap_finding("alpha")
    finding["evidence"] = None

    lines = mod._dream_chain_watch_lines([finding])

    assert len(lines) == 1
    assert lines[0].startswith("1 Dream(s) with no Spec (e.g. ?)")


@pytest.mark.parametrize("subject,rendered", [(None, "?"), (42, "42")])
def test_watch_lines_null_or_nonstring_subject_does_not_crash(
    subject, rendered
):
    """`subject` present-but-null (or non-string) is the symmetric case of
    null `evidence` (review pass 2): one malformed item must degrade to the
    placeholder (or its str() form), never raise `AttributeError` out of the
    pure helper -- which would send a REAL gap count to main()'s "could not
    check dream-chain gaps" line."""
    mod = _load_fleet_picture()
    finding = _gap_finding("alpha")
    finding["evidence"]["subject"] = subject

    lines = mod._dream_chain_watch_lines([finding])

    assert len(lines) == 1
    assert lines[0].startswith(f"1 Dream(s) with no Spec (e.g. {rendered})")


def test_watch_lines_scrubs_control_characters_in_slugs():
    """`\\r`/ESC are legal in POSIX filenames (a subject is a
    docs/dreams/*.md stem) and survive a newline-only split -- printed to a
    terminal they overwrite or spoof the line. Scrubbed to `?` (review
    pass 2); the newline still drops the tail entirely."""
    mod = _load_fleet_picture()

    lines = mod._dream_chain_watch_lines([
        _gap_finding("evil\rspoof"),
        _gap_finding("esc\x1b[31mred"),
    ])

    assert len(lines) == 1
    assert "\r" not in lines[0] and "\x1b" not in lines[0]
    assert "evil?spoof" in lines[0]
    assert "esc?[31mred" in lines[0]


@pytest.mark.parametrize(
    "fixture", [_unevaluable_finding("docs/dreams"), _total_degrade_finding()]
)
def test_watch_lines_neutral_wording_for_either_unevaluable_shape(fixture):
    """Directionally NEUTRAL (spec Change Log precedence note): spec-side
    unevaluable causes INFLATE the count, an unreadable docs/dreams/
    understates it -- the line claims neither direction."""
    mod = _load_fleet_picture()

    lines = mod._dream_chain_watch_lines([fixture])

    assert lines == [
        (
            "dream-chain could not be fully evaluated -- the "
            "Dreams-without-Spec count may be wrong in either direction"
        )
    ]
    assert "understated" not in lines[0]


def test_watch_lines_one_neutral_line_for_multiple_unevaluable():
    """"One line when ANY unevaluable-equivalent item is present" -- both
    shapes at once still produce exactly one trust line, not one each."""
    mod = _load_fleet_picture()

    lines = mod._dream_chain_watch_lines(
        [_unevaluable_finding("docs/dreams"), _total_degrade_finding()]
    )

    assert len(lines) == 1
    assert "either direction" in lines[0]


def test_watch_lines_both_lines_when_gaps_and_unevaluable():
    mod = _load_fleet_picture()

    lines = mod._dream_chain_watch_lines(
        [_gap_finding("alpha"), _total_degrade_finding()]
    )

    assert len(lines) == 2
    assert lines[0].startswith("1 Dream(s) with no Spec (e.g. alpha)")
    assert "either direction" in lines[1]


def test_watch_lines_empty_when_clean():
    mod = _load_fleet_picture()

    assert mod._dream_chain_watch_lines([]) == []
