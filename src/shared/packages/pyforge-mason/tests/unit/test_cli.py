"""Stories 1.2 + 1.3 + 1.4 — the noun -> verb tree, global flags, the
exit-code / MasonError projection in main(), and doctor's dual-output contract.

Story 1.3 (error taxonomy) was DEFERRED when 1.4 landed, so 1.4 was built
without it and this file carried only 1.2 + 1.4. 1.3 was recovered on
2026-07-31; the two touch main()'s error handling from opposite ends, so the
docstring names all three rather than whichever landed last.

Note the stream split 1.4 established and 1.3 must not undo: `doctor`'s
result flows through `render.write` to STDOUT (AD-8), while a MasonError and a
bare-noun usage error go to STDERR. The doctor tests below assert on stdout.

Story 1.7 extends this file with `CfeUnresolvedError`'s dedicated
EXIT_CFE_UNAVAILABLE branch in main(); the pre-existing
`test_mason_error_raised_in_main_prints_message_and_returns_exit_failed`
already proves the generic MasonError -> EXIT_FAILED path is unchanged, so
no separate regression test was needed for it (review pass, 2026-08-09).

Story 1.8 replaces the four Story-1.4-era doctor tests that asserted on the
placeholder `"not implemented yet"` stub with real-report assertions:
`doctor.build_report` is mocked (`patch("pyforge.mason.cli.doctor.
build_report", ...)`) to return a fixed `DoctorReport` -- `cli.py` calls it
through the `doctor` module object (`doctor.build_report(...)`, not an
imported bare name), so patching the function on its owning module reaches
the call site with no gotcha, unlike `doctor.py`'s own patch targets (see
`test_doctor.py`'s module docstring).

Story 2.4 registers the first real verb, `recipe new`, and extends this
file with its end-to-end dispatch coverage: `recipe.new` is mocked
(`patch("pyforge.mason.cli.recipe.new", ...)`) for the text/JSON happy-path
and error-projection tests, plus the three usage-error cases from the I/O
matrix (no `--from-*`, two `--from-*`, no `--output`) asserting `EXIT_USAGE`
before any CFE resolution is attempted, and a `RecipeGenerationError`-raising
mock asserting `EXIT_FAILED` via `main()`'s generic `MasonError` branch.

Story 2.5 registers the second real verb, `recipe validate`, and its own
test block below mirrors `recipe diagnose`'s established pattern:
`recipe.validate` is mocked (`patch("pyforge.mason.cli.recipe.validate",
...)`) to return a fixed `CfeResult`, text/JSON happy paths, flags/environ/
cwd passthrough, `--cfe-timeout` resolution, and the two dedicated
error-projection tests (`CfeUnresolvedError`/`CfeTimeoutError`). Unlike
every other verb in this file, `validate` also gets a differentiating pair
proving `main()`'s one non-`EXIT_OK`-always dispatch branch: a passing
canned result projects to `EXIT_OK`, a failing one to `EXIT_FAILED`, in
both text and `--format json` modes -- the JSON envelope's own `status`
field stays `"ok"` regardless (spec I/O matrix), only the process exit code
carries the signal.

Story 2.6 registers the next verb, `recipe build`, and extends this file
with its end-to-end dispatch coverage: `recipe.build` is mocked the same
way (`patch("pyforge.mason.cli.recipe.build", ...)`) to return a fixed
`BuildResult`, text/JSON happy paths, the two `--docker`/`--config`
usage-error cases (a manual post-parse cross-check, not argparse-
declarative -- see `main()`'s own comment), and a failed-child-still-
renders-"ok" case mirroring `doctor`'s established "the gap is data"
precedent above.

Story 2.7 adds a second registered verb, `recipe diagnose`, and its own
test block below mirrors the doctor pattern exactly: `recipe.diagnose` is
mocked via `patch("pyforge.mason.cli.recipe.diagnose", ...)` for the
dispatch/rendering/error-projection tests, plus one real, unmocked
end-to-end test against Story 1.9's `fake_cfe_root` fixture (AD-16).

Story 2.8 adds two more registered verbs, `recipe optimize`/`recipe scan`,
mirroring `recipe diagnose`'s own test block exactly, plus one new
error-projection test each: `CfeImportFloorError` -> `EXIT_FAILED` (via
`main()`'s existing generic `MasonError` branch -- no dedicated branch, spec
I/O matrix) -- these two verbs are the first to reach it, since
`recipe.optimize`/`recipe.scan` are the first `recipe.py` use-cases that
probe `cfe.probe_import_floor` and raise `CfeImportFloorError` themselves,
scoped to their own operation-relevant subset. Their real end-to-end
fixture tests therefore also fake the import floor via `cfe.
probe_import_floor` (`monkeypatch.setattr`), not `subprocess.run` wholesale
-- mirrors `test_recipe.py`'s identical Design Notes rationale.

Story 2.9 adds a fourth registered verb, `recipe submit`, mirroring the same
mocked-dispatch + real-fixture-end-to-end pattern, plus coverage the prior
three verbs don't need: `--yes`'s presence/absence inverts whether
`confirm=True`/`confirm=False` reaches `recipe.submit` (and therefore
whether `--dry-run` reaches CFE, per that function's own contract),
`--prepare-only` passes straight through, and the JSON-mode test asserts
the `ShipTargetResult.state` field (a `StrEnum`) serializes as a plain
string (`"pending"`), not `"ShipState.PENDING"` or a `TypeError` -- pinning
`models.py`'s own Design Notes claim about `dataclasses.asdict` +
`json.dumps` interaction.

Story 2.10 adds a fifth registered verb, `recipe update`, mirroring the same
mocked-dispatch + real-fixture-end-to-end pattern as `recipe diagnose`
(returns the raw `CfeResult`, like diagnose/optimize/scan -- not a
`ShipTargetResult`, unlike submit). Coverage the prior four verbs don't
need: `--dry-run`/`--github`/`--repo`/`--pre` all forward straight through
to `recipe.update` unresolved (no inversion, unlike submit's `--yes`), and
one real-fixture test exercises the `--github` dispatch path against the
new `github_updater.py` stub.

Story 3.2 registers the first verb under a DIFFERENT noun, `package build`,
mirroring `recipe build`'s own mocked-dispatch test block shape
(`patch("pyforge.mason.cli.package.build", ...)`, text/JSON happy paths, a
failed-child-still-renders-"ok" case) but with two differences: `--target`'s
`choices=("library",)` gives this verb its own argparse usage-error case
(mirroring `--format`'s existing choices pattern, spec Always boundary), and
there is no CFE-flags-pass-through coverage at all -- `package.build()`
takes no `cfe_root_arg`/`cfe_python_arg`/`cfe_timeout_arg` parameters, so
this verb's dispatch branch reads none of those three flags (spec Always
boundary: zero CFE involvement). `EngineAbsentError`/`PackageVersionMismatchError`
both project through `main()`'s existing generic `MasonError` branch to
`EXIT_FAILED` -- no dedicated branch, same as `CfeImportFloorError` above.

Story 3.9 registers `package`'s SECOND verb, `ship`, plus the one
documented bare-noun exception, `package --ship` (D-12/FR-30) -- both
dispatch through the shared `_dispatch_package_ship` helper
(`patch("pyforge.mason.cli.package.ship", ...)`, mocked to return a fixed
`tuple[ShipTargetResult, ...]`, mirroring every other verb's fixed-result
mocking convention but plural, since `ship()` always returns more than one
result shape's worth of data). New coverage this story's predecessors
don't need: canonical-vs-alias dispatch equivalence, the bare-noun-ship
carve-out coexisting with the unchanged bare-noun-usage-error rule for
every OTHER noun/verb-less shape, `--to`'s native argparse `required=True`
usage error, and the data-dependent aggregate exit code (`EXIT_FAILED` if
any returned result's `state == ShipState.FAILED`, else `EXIT_OK` -- the
ONE dispatch branch in this whole file whose exit code is not uniformly
`EXIT_OK`, spec Design Notes) -- unlike `package build`'s established
never-reads-cfe-flags precedent, `ship` DOES read `--cfe-root`/
`--cfe-python`/`--cfe-timeout` through to `package.ship`, since its own
`conda-forge` target needs them.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason import __version__
from pyforge.mason.cfe import ImportFloorResult
from pyforge.mason.cli import (
    _ENV_CFE_PYTHON,
    _ENV_CFE_ROOT,
    _ENV_CFE_TIMEOUT,
    _ENV_FORMAT,
    _ENV_QUIET,
    _ENV_VERBOSE,
    _configure_logging,
    _resolve_bool,
    _resolve_optional_float,
    _resolve_str,
    build_parser,
    main,
)
from pyforge.mason.doctor import DoctorReport
from pyforge.mason.engines import EngineStatus
from pyforge.mason.errors import (
    CfeImportFloorError,
    CfeTimeoutError,
    CfeUnresolvedError,
    EngineAbsentError,
    EnvironmentCheckTimeoutError,
    EnvironmentLockfileMalformedError,
    EnvironmentLockfileMissingError,
    EnvironmentLockTimeoutError,
    EnvironmentManifestsNotFoundError,
    InvalidShipTargetError,
    MasonError,
    PackageVersionMismatchError,
    RecipeGenerationError,
)
from pyforge.mason.exit_codes import (
    EXIT_CFE_UNAVAILABLE,
    EXIT_FAILED,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_USAGE,
)
from pyforge.mason.models import (
    BuildResult,
    CfeResult,
    CheckResult,
    LockResult,
    PackageBuildResult,
    ShipState,
    ShipTargetResult,
)

_FIXED_REPORT = DoctorReport(
    mason_version="1.2.3+test",
    cfe_root=None,
    cfe_root_step="not-found",
    cfe_interpreter="/fake/python",
    cfe_interpreter_step="running-interpreter",
    cfe_import_floor_satisfied=False,
    cfe_import_floor_missing=("pyyaml", "requests"),
    unavailable_verbs=("recipe",),
    engines=(
        EngineStatus(name="pixi", available=True, version="pixi 0.72.2"),
        EngineStatus(name="twine", available=False, version=None),
    ),
    conda_forge_ship_ready=False,
    conda_forge_ship_blockers=("the CFE root is unresolved",),
)


def test_version_is_reported(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_bare_invocation_prints_help_and_succeeds(capsys):
    """A true bare `mason` invocation is help output, not a diagnostic."""
    assert main([]) == EXIT_OK
    out = capsys.readouterr()
    assert "Mason" in out.out
    assert out.err == ""


def test_help_lists_the_whole_surface(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    for name in ("recipe", "package", "environment", "doctor"):
        assert name in out


@pytest.mark.parametrize("noun", ["recipe", "package", "environment"])
def test_bare_noun_is_a_usage_error(noun, capsys):
    """Amended contract (2026-07-30): a noun with no verb is a usage error —
    stderr, EXIT_USAGE — not the EXIT_OK/stdout stub Story 1.1 used."""
    assert main([noun]) == EXIT_USAGE
    out = capsys.readouterr()
    assert noun in out.err
    assert out.out == ""


def test_unrecognized_verb_is_a_native_argparse_usage_error(capsys):
    """`mason recipe sometypo` — argparse's own invalid-choice handling,
    unaffected by the bare-noun special case above; both land on the same
    stream and exit code."""
    assert main(["recipe", "sometypo"]) == EXIT_USAGE
    err = capsys.readouterr().err
    # The offending token must appear in the diagnostic — `err != ""` alone
    # would pass on any stderr noise without proving invalid-choice fired.
    assert "sometypo" in err


def test_doctor_text_mode_reports_real_report_fields(monkeypatch, capsys):
    """Story 1.8: the stub result is gone -- `doctor`'s output now reflects
    `doctor.build_report`'s actual `DoctorReport`, rendered through
    `render.write` to stdout (AD-8). Also confirms the default format is
    text, not JSON."""
    # An ambient MASON_FORMAT=json would legitimately select JSON here --
    # this test asserts the no-flag/no-env default, so it must be hermetic.
    monkeypatch.delenv("MASON_FORMAT", raising=False)
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    assert "doctor: ok" in out.out
    assert "mason_version: 1.2.3+test" in out.out
    assert "cfe_root_step: not-found" in out.out
    assert "unavailable_verbs: ('recipe',)" in out.out
    assert not out.out.lstrip().startswith("{")
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.out)


def _json_roundtripped(report: DoctorReport) -> dict:
    """`dataclasses.asdict` keeps tuples as tuples; JSON has no tuple type,
    so a round-trip through `json.dumps`/`json.loads` is what an actual
    `data` payload looks like after `render_json` serializes it (tuples ->
    lists) -- the shape this helper produces is what the assertions below
    compare `doc["data"]` against, not the raw `asdict()` result."""
    return json.loads(json.dumps(dataclasses.asdict(report)))


def test_doctor_json_mode_data_matches_dataclasses_asdict_of_the_report(capsys):
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--format", "json"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "doctor"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == _json_roundtripped(_FIXED_REPORT)


def test_doctor_env_var_selects_json_format_without_the_flag(monkeypatch, capsys):
    monkeypatch.setenv("MASON_FORMAT", "json")
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "doctor"
    assert doc["data"] == _json_roundtripped(_FIXED_REPORT)


def test_doctor_status_stays_ok_and_errors_empty_regardless_of_cfe_or_engine_gaps(capsys):
    """`_FIXED_REPORT` already names an unresolved CFE root, a missing
    import floor, and an absent engine -- `doctor` must still report
    `status == "ok"`/`errors == []` and exit 0 (FR-34, AD-6): the gap is
    data in the report, never a failure of the `doctor` command itself."""
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--format", "json"]) == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"]["unavailable_verbs"] == ["recipe"]


def test_doctor_invalid_env_format_falls_back_to_text(monkeypatch, capsys):
    """`--format`'s `choices=("text","json")` validates the flag, but
    `MASON_FORMAT` bypasses argparse entirely -- an out-of-choices value
    must fall back to the text default, not crash."""
    monkeypatch.setenv("MASON_FORMAT", "bogus")
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor"]) == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    assert not out.out.lstrip().startswith("{")
    assert "doctor: ok" in out.out


def test_doctor_calls_build_report_with_flags_environ_and_cwd():
    """`cli.py` must pass the `--cfe-root`/`--cfe-python` flags through
    unresolved (`doctor.build_report` does its own resolution), plus the
    real `os.environ` and `Path.cwd()` -- proven by inspecting the call
    rather than the rendered output.

    Review pass (2026-08-09): both flags are exercised together here (the
    original version of this test only ever passed `--cfe-root`, so
    `--cfe-python`'s own pass-through path was unproven), and `args[2]` is
    now actually asserted against `os.environ` -- this test's own docstring
    already claimed that, but the assertion was missing."""
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT) as mock_build_report:
        assert (
            main(
                [
                    "doctor",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_build_report.assert_called_once()
    args = mock_build_report.call_args.args
    assert args[0] == "/explicit/root"
    assert args[1] == "/explicit/python"
    assert args[2] is os.environ
    assert args[3] == Path.cwd()


def test_doctor_calls_build_report_with_cfe_python_unresolved_when_absent():
    """Symmetric with the flags-given case above: when `--cfe-python` is
    never supplied, `cli.py` must pass `None` through -- `doctor.build_report`
    does its own flag -> environment -> running-interpreter resolution."""
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT) as mock_build_report:
        assert main(["doctor", "--cfe-root", "/explicit/root"]) == EXIT_OK

    args = mock_build_report.call_args.args
    assert args[0] == "/explicit/root"
    assert args[1] is None


def test_doctor_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["doctor", "--help"])
    assert exc.value.code == 0
    assert "doctor" in capsys.readouterr().out


def test_recipe_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "--help"])
    assert exc.value.code == 0
    assert "recipe" in capsys.readouterr().out


# --- Story 2.4: `recipe new` -- verb dispatch (FR-7) ------------------------

_FIXED_RECIPE_RESULT = CfeResult(
    returncode=0,
    stdout="Generated: recipes/requests/recipe.yaml\n",
    stderr="",
    json_body=None,
)


def test_recipe_new_text_mode_happy_path_calls_recipe_new_with_the_resolved_flags(capsys):
    """`recipe.new` is mocked (`patch("pyforge.mason.cli.recipe.new", ...)`,
    the same target-on-the-imported-module pattern `doctor.build_report`
    already established above) -- `cli.py` calls it through the `recipe`
    module object, not an imported bare name."""
    with patch("pyforge.mason.cli.recipe.new", return_value=_FIXED_RECIPE_RESULT) as mock_new:
        assert main(["recipe", "new", "--from-pypi", "requests", "--output", "x"]) == EXIT_OK

    mock_new.assert_called_once()
    args, kwargs = mock_new.call_args
    assert args == ("pypi", "requests", "x")
    assert kwargs["cfe_root_arg"] is None
    assert kwargs["cfe_python_arg"] is None
    assert kwargs["cfe_timeout_arg"] is None
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()

    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe new: ok" in out.out
    assert "returncode: 0" in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_new_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch("pyforge.mason.cli.recipe.new", return_value=_FIXED_RECIPE_RESULT):
        assert (
            main(
                [
                    "recipe",
                    "new",
                    "--from-github",
                    "owner/repo",
                    "--output",
                    "x",
                    "--format",
                    "json",
                ]
            )
            == EXIT_OK
        )

    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe new"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == dataclasses.asdict(_FIXED_RECIPE_RESULT)


@pytest.mark.parametrize(
    "flag,expected_source",
    [
        ("--from-pypi", "pypi"),
        ("--from-github", "github"),
        ("--from-cran", "cran"),
        ("--from-npm", "npm"),
    ],
)
def test_recipe_new_maps_each_from_flag_to_its_own_cfe_subcommand(flag, expected_source):
    """The `--from-*` -> subcommand mapping is `cli.py`'s own job (spec
    Design Notes): `recipe.py::new` merely forwards whatever `source` string
    it is given."""
    with patch("pyforge.mason.cli.recipe.new", return_value=_FIXED_RECIPE_RESULT) as mock_new:
        assert main(["recipe", "new", flag, "pkg", "--output", "x"]) == EXIT_OK

    args = mock_new.call_args.args
    assert args[0] == expected_source
    assert args[1] == "pkg"


def test_recipe_new_with_no_source_flag_is_a_usage_error(capsys):
    assert main(["recipe", "new", "--output", "x"]) == EXIT_USAGE
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err != ""


def test_recipe_new_with_two_source_flags_is_a_usage_error(capsys):
    assert (
        main(
            [
                "recipe",
                "new",
                "--from-pypi",
                "a",
                "--from-github",
                "b",
                "--output",
                "x",
            ]
        )
        == EXIT_USAGE
    )
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err != ""


def test_recipe_new_with_no_output_is_a_usage_error(capsys):
    assert main(["recipe", "new", "--from-pypi", "requests"]) == EXIT_USAGE
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err != ""


def test_recipe_new_generation_failure_projects_to_exit_failed_with_message_on_stderr(capsys):
    """A `RecipeGenerationError` raised out of `recipe.new` is an anticipated
    `MasonError` subclass (AD-7) -- no dedicated branch exists for it, so it
    hits `main()`'s generic `MasonError` handler, same as any other typed
    Mason failure (spec Boundaries & Constraints)."""
    error = RecipeGenerationError(source="pypi", cfe_message="Error: no such package")
    with patch("pyforge.mason.cli.recipe.new", side_effect=error):
        rc = main(["recipe", "new", "--from-pypi", "no-such-package", "--output", "x"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(error)
    assert "Traceback" not in err


# --- Story 2.5: `mason recipe validate <recipe_path>` -----------------------

_FIXED_VALIDATE_PASSING_RESULT = CfeResult(
    returncode=0,
    stdout='{"passed": true, "errors": [], "warnings": [], "info": [], "rattler_lint_ran": true}',
    stderr="",
    json_body={
        "passed": True,
        "errors": [],
        "warnings": [],
        "info": [],
        "rattler_lint_ran": True,
    },
)

_FIXED_VALIDATE_FAILING_RESULT = CfeResult(
    returncode=1,
    stdout='{"passed": false, "errors": ["missing license"], "warnings": [], "info": [], "rattler_lint_ran": true}',
    stderr="",
    json_body={
        "passed": False,
        "errors": ["missing license"],
        "warnings": [],
        "info": [],
        "rattler_lint_ran": True,
    },
)


def test_recipe_validate_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "validate", "--help"])
    assert exc.value.code == 0
    assert "validate" in capsys.readouterr().out


def test_recipe_validate_requires_the_recipe_path_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "validate"])
    assert exc.value.code == 2
    assert "recipe_path" in capsys.readouterr().err


def test_recipe_validate_parses_the_recipe_path_positional():
    ns = build_parser().parse_args(["recipe", "validate", "recipes/foo"])
    assert ns.noun == "recipe"
    assert ns.verb == "validate"
    assert ns.recipe_path == "recipes/foo"


def test_recipe_validate_text_mode_renders_the_cfe_result_fields(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ) as mock_validate:
        assert main(["recipe", "validate", "recipes/foo"]) == EXIT_OK

    mock_validate.assert_called_once()
    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe validate: ok" in out.out
    assert "missing license" not in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_validate_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ):
        assert main(["recipe", "validate", "recipes/foo", "--format", "json"]) == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe validate"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == json.loads(json.dumps(dataclasses.asdict(_FIXED_VALIDATE_PASSING_RESULT)))


def test_recipe_validate_passes_recipe_path_and_resolved_flags_through(monkeypatch):
    """`cli.py` must pass the raw `recipe_path` positional plus the
    unresolved `--cfe-root`/`--cfe-python` flag values, the real
    `os.environ`, and `Path.cwd()` -- `recipe.validate` does its own
    resolution, mirroring `recipe diagnose`'s established contract."""
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ) as mock_validate:
        assert (
            main(
                [
                    "recipe",
                    "validate",
                    "recipes/foo",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_validate.assert_called_once()
    args, kwargs = mock_validate.call_args
    assert args == ("recipes/foo",)
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_validate_resolves_cfe_timeout_flag_via_the_shared_resolver():
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ) as mock_validate:
        assert (
            main(
                [
                    "recipe",
                    "validate",
                    "recipes/foo",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    assert mock_validate.call_args.kwargs["cfe_timeout_arg"] == 30.0


def test_recipe_validate_cfe_timeout_env_var_applies_without_the_flag(monkeypatch):
    monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ) as mock_validate:
        assert main(["recipe", "validate", "recipes/foo"]) == EXIT_OK

    assert mock_validate.call_args.kwargs["cfe_timeout_arg"] == 45.0


def test_recipe_validate_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ) as mock_validate:
        assert main(["recipe", "validate", "recipes/foo"]) == EXIT_OK

    assert mock_validate.call_args.kwargs["cfe_timeout_arg"] is None


def test_recipe_validate_cfe_unresolved_error_returns_exit_cfe_unavailable(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        side_effect=CfeUnresolvedError(),
    ):
        rc = main(["recipe", "validate", "recipes/foo"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err


def test_recipe_validate_cfe_timeout_error_returns_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        side_effect=CfeTimeoutError(script="validate_recipe", timeout=5.0),
    ):
        rc = main(["recipe", "validate", "recipes/foo", "--cfe-timeout", "5"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeTimeoutError(script="validate_recipe", timeout=5.0))
    assert "Traceback" not in err


# --- The exit-code projection itself (spec Intent/FR-8): the one verb whose
# process exit code reflects the wrapped tool's own pass/fail outcome, not
# a blanket EXIT_OK -- proven in both text and --format json modes, and
# that the JSON envelope's own "status" field stays "ok" regardless. -------


def test_recipe_validate_passing_canned_result_returns_exit_ok_text_mode(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ):
        rc = main(["recipe", "validate", "recipes/foo"])

    assert rc == EXIT_OK
    assert "recipe validate: ok" in capsys.readouterr().out


def test_recipe_validate_passing_canned_result_returns_exit_ok_json_mode(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_PASSING_RESULT,
    ):
        rc = main(["recipe", "validate", "recipes/foo", "--format", "json"])

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["passed"] is True


def test_recipe_validate_failing_canned_result_returns_exit_failed_text_mode(capsys):
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_FAILING_RESULT,
    ):
        rc = main(["recipe", "validate", "recipes/foo"])

    assert rc == EXIT_FAILED
    out = capsys.readouterr()
    assert "recipe validate: ok" in out.out
    assert "missing license" in out.out


def test_recipe_validate_failing_canned_result_returns_exit_failed_json_mode(capsys):
    """The JSON envelope's own `status` field stays `"ok"` regardless of the
    recipe's pass/fail outcome (spec I/O matrix) -- only the process exit
    code carries the validation signal."""
    with patch(
        "pyforge.mason.cli.recipe.validate",
        return_value=_FIXED_VALIDATE_FAILING_RESULT,
    ):
        rc = main(["recipe", "validate", "recipes/foo", "--format", "json"])

    assert rc == EXIT_FAILED
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["passed"] is False
    assert doc["data"]["json_body"]["errors"] == ["missing license"]


def test_recipe_validate_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """No mocking: the whole `recipe validate` path runs against Story 1.9's
    fixture CFE root (AD-16) -- the fixture's own canned body is passing, so
    this also proves the real subprocess round trip reaches `EXIT_OK`."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    rc = main(
        [
            "recipe",
            "validate",
            "recipes/example",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe validate"
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["passed"] is True


# --- Story 2.7: `mason recipe diagnose <log_path>` --------------------------

_FIXED_DIAGNOSE_RESULT = CfeResult(
    returncode=0,
    stdout='{"success": true, "error_class": "MODULE_NOT_FOUND_AT_TEST"}',
    stderr="",
    json_body={"success": True, "error_class": "MODULE_NOT_FOUND_AT_TEST"},
)


def test_recipe_diagnose_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "diagnose", "--help"])
    assert exc.value.code == 0
    assert "diagnose" in capsys.readouterr().out


def test_recipe_diagnose_requires_the_log_path_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "diagnose"])
    assert exc.value.code == 2
    assert "log_path" in capsys.readouterr().err


def test_recipe_diagnose_parses_the_log_path_positional():
    ns = build_parser().parse_args(["recipe", "diagnose", "build.log"])
    assert ns.noun == "recipe"
    assert ns.verb == "diagnose"
    assert ns.log_path == "build.log"


def test_recipe_bare_noun_still_a_usage_error_after_diagnose_is_registered(capsys):
    """AC: verb-subparsers restructuring is behavior-preserving for
    `package`/`environment` -- and, symmetrically, `recipe` itself with no
    verb still hits the bare-noun usage-error path, not `diagnose`'s own
    dispatch branch."""
    assert main(["recipe"]) == EXIT_USAGE
    out = capsys.readouterr()
    assert "recipe" in out.err
    assert out.out == ""


def test_recipe_diagnose_text_mode_renders_the_cfe_result_fields(capsys):
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        return_value=_FIXED_DIAGNOSE_RESULT,
    ) as mock_diagnose:
        assert main(["recipe", "diagnose", "build.log"]) == EXIT_OK

    mock_diagnose.assert_called_once()
    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe diagnose: ok" in out.out
    assert "MODULE_NOT_FOUND_AT_TEST" in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_diagnose_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch("pyforge.mason.cli.recipe.diagnose", return_value=_FIXED_DIAGNOSE_RESULT):
        assert main(["recipe", "diagnose", "build.log", "--format", "json"]) == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe diagnose"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == json.loads(json.dumps(dataclasses.asdict(_FIXED_DIAGNOSE_RESULT)))


def test_recipe_diagnose_passes_log_path_and_resolved_flags_through(monkeypatch):
    """`cli.py` must pass the raw `log_path` positional plus the unresolved
    `--cfe-root`/`--cfe-python` flag values, the real `os.environ`, and
    `Path.cwd()` -- `recipe.diagnose` does its own resolution, mirroring
    `doctor`'s established contract (`test_doctor_calls_build_report_with_
    flags_environ_and_cwd` above)."""
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        return_value=_FIXED_DIAGNOSE_RESULT,
    ) as mock_diagnose:
        assert (
            main(
                [
                    "recipe",
                    "diagnose",
                    "build.log",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_diagnose.assert_called_once()
    args, kwargs = mock_diagnose.call_args
    assert args == ("build.log",)
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_diagnose_resolves_cfe_timeout_flag_via_the_shared_resolver():
    """`--cfe-timeout` is resolved via `_resolve_optional_float` (the spec's
    own claim: "first real caller of that helper") and passed through as
    `cfe_timeout_arg`."""
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        return_value=_FIXED_DIAGNOSE_RESULT,
    ) as mock_diagnose:
        assert (
            main(
                [
                    "recipe",
                    "diagnose",
                    "build.log",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    assert mock_diagnose.call_args.kwargs["cfe_timeout_arg"] == 30.0


def test_recipe_diagnose_cfe_timeout_env_var_applies_without_the_flag(monkeypatch):
    monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        return_value=_FIXED_DIAGNOSE_RESULT,
    ) as mock_diagnose:
        assert main(["recipe", "diagnose", "build.log"]) == EXIT_OK

    assert mock_diagnose.call_args.kwargs["cfe_timeout_arg"] == 45.0


def test_recipe_diagnose_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        return_value=_FIXED_DIAGNOSE_RESULT,
    ) as mock_diagnose:
        assert main(["recipe", "diagnose", "build.log"]) == EXIT_OK

    assert mock_diagnose.call_args.kwargs["cfe_timeout_arg"] is None


def test_recipe_diagnose_cfe_unresolved_error_returns_exit_cfe_unavailable(capsys):
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        side_effect=CfeUnresolvedError(),
    ):
        rc = main(["recipe", "diagnose", "build.log"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err


def test_recipe_diagnose_cfe_timeout_error_returns_exit_failed(capsys):
    """Review pass: parity with the existing `CfeUnresolvedError` test above
    -- `CfeTimeoutError` is a `MasonError` subclass, so it must degrade the
    same clean way (message on stderr, no traceback, `EXIT_FAILED`), and
    `--cfe-timeout` is this story's first real wiring of that knob."""
    with patch(
        "pyforge.mason.cli.recipe.diagnose",
        side_effect=CfeTimeoutError(script="diagnose_failure", timeout=5.0),
    ):
        rc = main(["recipe", "diagnose", "build.log", "--cfe-timeout", "5"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeTimeoutError(script="diagnose_failure", timeout=5.0))
    assert "Traceback" not in err


def test_recipe_diagnose_rejects_the_stdin_sentinel_as_a_usage_error(capsys):
    """Review pass: `_invoke_captured` fixes the child's stdin to `DEVNULL`,
    so `-` -- which the real `failure_analyzer.py` documents as its stdin
    sentinel -- would silently read an empty log and report a confident
    "no known error pattern matched" rather than piped content. Rejected as
    a usage error before `recipe.diagnose` (and therefore any subprocess)
    is ever reached."""
    with patch("pyforge.mason.cli.recipe.diagnose") as mock_diagnose:
        rc = main(["recipe", "diagnose", "-"])

    assert rc == EXIT_USAGE
    out = capsys.readouterr()
    assert out.out == ""
    assert "stdin" in out.err
    mock_diagnose.assert_not_called()


def test_recipe_diagnose_verb_metavar_reflects_the_registered_verb(capsys):
    """Review pass: `metavar="{}"` was never updated once a verb was
    actually registered, so `mason recipe <bad-verb>` printed the literal
    token `{}` in its usage/error text instead of
    `{new,validate,build,diagnose,optimize,scan,submit,update}`. Story 2.4
    registered the first verb, `new`; Story 2.5 registers the second,
    `validate`; Story 2.8 widened this to six registered verbs; Story 2.9
    widened it to seven; Story 2.10 widens it again to all eight, in
    registration order."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "bogus-verb"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "{new,validate,build,diagnose,optimize,scan,submit,update}" in err
    assert "argument {}:" not in err


def test_recipe_diagnose_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """No mocking: the whole `recipe diagnose` path runs against Story 1.9's
    fixture CFE root (AD-16)."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    rc = main(
        [
            "recipe",
            "diagnose",
            "build.log",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe diagnose"
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["success"] is True
    assert doc["data"]["json_body"]["error_class"] == "MODULE_NOT_FOUND_AT_TEST"


# --- Story 2.8: `mason recipe optimize <recipe_path>` -----------------------

_FIXED_OPTIMIZE_RESULT = CfeResult(
    returncode=1,
    stdout='{"success": true, "suggestions_found": 1, "suggestions": '
    '[{"code": "ABT-001", "message": "Missing license_file.", '
    '"suggestion": "Add license_file.", "confidence": 0.95}]}',
    stderr="",
    json_body={
        "success": True,
        "suggestions_found": 1,
        "suggestions": [
            {
                "code": "ABT-001",
                "message": "Missing license_file.",
                "suggestion": "Add license_file.",
                "confidence": 0.95,
            }
        ],
    },
)


def test_recipe_optimize_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "optimize", "--help"])
    assert exc.value.code == 0
    assert "optimize" in capsys.readouterr().out


def test_recipe_optimize_requires_the_recipe_path_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "optimize"])
    assert exc.value.code == 2
    assert "recipe_path" in capsys.readouterr().err


def test_recipe_optimize_parses_the_recipe_path_positional():
    ns = build_parser().parse_args(["recipe", "optimize", "recipes/foo"])
    assert ns.noun == "recipe"
    assert ns.verb == "optimize"
    assert ns.recipe_path == "recipes/foo"


def test_recipe_optimize_text_mode_renders_the_cfe_result_fields(capsys):
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        return_value=_FIXED_OPTIMIZE_RESULT,
    ) as mock_optimize:
        assert main(["recipe", "optimize", "recipes/foo"]) == EXIT_OK

    mock_optimize.assert_called_once()
    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe optimize: ok" in out.out
    assert "ABT-001" in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_optimize_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch("pyforge.mason.cli.recipe.optimize", return_value=_FIXED_OPTIMIZE_RESULT):
        assert main(["recipe", "optimize", "recipes/foo", "--format", "json"]) == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe optimize"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == json.loads(json.dumps(dataclasses.asdict(_FIXED_OPTIMIZE_RESULT)))


def test_recipe_optimize_passes_recipe_path_and_resolved_flags_through(monkeypatch):
    """Mirrors `test_recipe_diagnose_passes_log_path_and_resolved_flags_
    through`: `cli.py` passes the raw `recipe_path` positional plus the
    unresolved `--cfe-root`/`--cfe-python` flag values, the real
    `os.environ`, and `Path.cwd()` -- `recipe.optimize` does its own
    resolution."""
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        return_value=_FIXED_OPTIMIZE_RESULT,
    ) as mock_optimize:
        assert (
            main(
                [
                    "recipe",
                    "optimize",
                    "recipes/foo",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_optimize.assert_called_once()
    args, kwargs = mock_optimize.call_args
    assert args == ("recipes/foo",)
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_optimize_resolves_cfe_timeout_flag_via_the_shared_resolver():
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        return_value=_FIXED_OPTIMIZE_RESULT,
    ) as mock_optimize:
        assert (
            main(
                [
                    "recipe",
                    "optimize",
                    "recipes/foo",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    assert mock_optimize.call_args.kwargs["cfe_timeout_arg"] == 30.0


def test_recipe_optimize_cfe_timeout_env_var_applies_without_the_flag(monkeypatch):
    monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        return_value=_FIXED_OPTIMIZE_RESULT,
    ) as mock_optimize:
        assert main(["recipe", "optimize", "recipes/foo"]) == EXIT_OK

    assert mock_optimize.call_args.kwargs["cfe_timeout_arg"] == 45.0


def test_recipe_optimize_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        return_value=_FIXED_OPTIMIZE_RESULT,
    ) as mock_optimize:
        assert main(["recipe", "optimize", "recipes/foo"]) == EXIT_OK

    assert mock_optimize.call_args.kwargs["cfe_timeout_arg"] is None


def test_recipe_optimize_cfe_unresolved_error_returns_exit_cfe_unavailable(capsys):
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        side_effect=CfeUnresolvedError(),
    ):
        rc = main(["recipe", "optimize", "recipes/foo"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err


def test_recipe_optimize_cfe_timeout_error_returns_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        side_effect=CfeTimeoutError(script="optimize_recipe", timeout=5.0),
    ):
        rc = main(["recipe", "optimize", "recipes/foo", "--cfe-timeout", "5"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeTimeoutError(script="optimize_recipe", timeout=5.0))
    assert "Traceback" not in err


def test_recipe_optimize_cfe_import_floor_error_returns_exit_failed(capsys):
    """`recipe optimize` is the first verb whose dispatch can reach
    `CfeImportFloorError` (spec I/O matrix): unlike `CfeUnresolvedError`,
    it has no dedicated exit-code branch -- it is a `MasonError` subclass,
    so it degrades via that generic branch to `EXIT_FAILED` (spec I/O
    matrix row: "Interpreter missing import floor ... EXIT_FAILED")."""
    with patch(
        "pyforge.mason.cli.recipe.optimize",
        side_effect=CfeImportFloorError(missing=["ruamel.yaml"], interpreter="/fake/python"),
    ):
        rc = main(["recipe", "optimize", "recipes/foo"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeImportFloorError(missing=["ruamel.yaml"], interpreter="/fake/python"))
    assert "Traceback" not in err


def test_recipe_optimize_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """No mocking of the subprocess boundary: the whole `recipe optimize`
    path runs against Story 1.9's fixture CFE root (AD-16). The import
    floor is faked via `cfe.probe_import_floor` (spec Design Notes), not
    `subprocess.run` wholesale, which would also intercept the real
    invocation against the fixture stub."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        "pyforge.mason.cfe.probe_import_floor",
        lambda interpreter: ImportFloorResult(interpreter=interpreter, missing=()),
    )

    rc = main(
        [
            "recipe",
            "optimize",
            "recipes/example",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe optimize"
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["success"] is True
    assert doc["data"]["json_body"]["suggestions_found"] == 1


# --- Story 2.8: `mason recipe scan <recipe_path>` ---------------------------

_FIXED_SCAN_RESULT = CfeResult(
    returncode=0,
    stdout='{"success": true, "mode": "osv-api", "total_vulnerabilities": 0, "results": []}',
    stderr="",
    json_body={"success": True, "mode": "osv-api", "total_vulnerabilities": 0, "results": []},
)


def test_recipe_scan_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "scan", "--help"])
    assert exc.value.code == 0
    assert "scan" in capsys.readouterr().out


def test_recipe_scan_requires_the_recipe_path_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "scan"])
    assert exc.value.code == 2
    assert "recipe_path" in capsys.readouterr().err


def test_recipe_scan_parses_the_recipe_path_positional():
    ns = build_parser().parse_args(["recipe", "scan", "recipes/foo"])
    assert ns.noun == "recipe"
    assert ns.verb == "scan"
    assert ns.recipe_path == "recipes/foo"


def test_recipe_scan_text_mode_renders_the_cfe_result_fields(capsys):
    with patch(
        "pyforge.mason.cli.recipe.scan",
        return_value=_FIXED_SCAN_RESULT,
    ) as mock_scan:
        assert main(["recipe", "scan", "recipes/foo"]) == EXIT_OK

    mock_scan.assert_called_once()
    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe scan: ok" in out.out
    assert "osv-api" in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_scan_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch("pyforge.mason.cli.recipe.scan", return_value=_FIXED_SCAN_RESULT):
        assert main(["recipe", "scan", "recipes/foo", "--format", "json"]) == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe scan"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == json.loads(json.dumps(dataclasses.asdict(_FIXED_SCAN_RESULT)))


def test_recipe_scan_passes_recipe_path_and_resolved_flags_through(monkeypatch):
    with patch(
        "pyforge.mason.cli.recipe.scan",
        return_value=_FIXED_SCAN_RESULT,
    ) as mock_scan:
        assert (
            main(
                [
                    "recipe",
                    "scan",
                    "recipes/foo",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_scan.assert_called_once()
    args, kwargs = mock_scan.call_args
    assert args == ("recipes/foo",)
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_scan_resolves_cfe_timeout_flag_via_the_shared_resolver():
    with patch(
        "pyforge.mason.cli.recipe.scan",
        return_value=_FIXED_SCAN_RESULT,
    ) as mock_scan:
        assert (
            main(
                [
                    "recipe",
                    "scan",
                    "recipes/foo",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    assert mock_scan.call_args.kwargs["cfe_timeout_arg"] == 30.0


def test_recipe_scan_cfe_timeout_env_var_applies_without_the_flag(monkeypatch):
    monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
    with patch(
        "pyforge.mason.cli.recipe.scan",
        return_value=_FIXED_SCAN_RESULT,
    ) as mock_scan:
        assert main(["recipe", "scan", "recipes/foo"]) == EXIT_OK

    assert mock_scan.call_args.kwargs["cfe_timeout_arg"] == 45.0


def test_recipe_scan_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.recipe.scan",
        return_value=_FIXED_SCAN_RESULT,
    ) as mock_scan:
        assert main(["recipe", "scan", "recipes/foo"]) == EXIT_OK

    assert mock_scan.call_args.kwargs["cfe_timeout_arg"] is None


def test_recipe_scan_cfe_unresolved_error_returns_exit_cfe_unavailable(capsys):
    with patch(
        "pyforge.mason.cli.recipe.scan",
        side_effect=CfeUnresolvedError(),
    ):
        rc = main(["recipe", "scan", "recipes/foo"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err


def test_recipe_scan_cfe_timeout_error_returns_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.recipe.scan",
        side_effect=CfeTimeoutError(script="scan_for_vulnerabilities", timeout=5.0),
    ):
        rc = main(["recipe", "scan", "recipes/foo", "--cfe-timeout", "5"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeTimeoutError(script="scan_for_vulnerabilities", timeout=5.0))
    assert "Traceback" not in err


def test_recipe_scan_cfe_import_floor_error_returns_exit_failed(capsys):
    """Mirrors `recipe optimize`'s own version of this test -- `scan` is the
    second verb whose dispatch can reach `CfeImportFloorError`, degrading
    via the generic `MasonError` branch to `EXIT_FAILED`."""
    with patch(
        "pyforge.mason.cli.recipe.scan",
        side_effect=CfeImportFloorError(
            missing=["requests", "pyyaml"],
            interpreter="/fake/python",
        ),
    ):
        rc = main(["recipe", "scan", "recipes/foo"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeImportFloorError(missing=["requests", "pyyaml"], interpreter="/fake/python"))
    assert "Traceback" not in err


def test_recipe_scan_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """Mirrors `recipe optimize`'s own real-fixture end-to-end test: no
    mocking of the subprocess boundary, import floor faked via
    `cfe.probe_import_floor`."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        "pyforge.mason.cfe.probe_import_floor",
        lambda interpreter: ImportFloorResult(interpreter=interpreter, missing=()),
    )

    rc = main(
        [
            "recipe",
            "scan",
            "recipes/example",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe scan"
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["success"] is True
    assert doc["data"]["json_body"]["total_vulnerabilities"] == 0


# --- Story 2.9: `mason recipe submit <recipe_path>` -------------------------

_FIXED_SUBMIT_RESULT = ShipTargetResult(
    target="conda-forge",
    state=ShipState.PENDING,
    reference="https://github.com/example/example/pull/1",
    message="PR created: https://github.com/example/example/pull/1",
)


def test_recipe_submit_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "submit", "--help"])
    assert exc.value.code == 0
    assert "submit" in capsys.readouterr().out


def test_recipe_submit_requires_the_recipe_path_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "submit"])
    assert exc.value.code == 2
    assert "recipe_path" in capsys.readouterr().err


def test_recipe_submit_parses_the_recipe_path_positional_and_defaults():
    """`--yes`/`--prepare-only` default to `False` when omitted -- these are
    plain per-verb flags, not part of the `argparse.SUPPRESS`-defaulted
    global set (registration comment in `cli.py`)."""
    ns = build_parser().parse_args(["recipe", "submit", "recipes/foo"])
    assert ns.noun == "recipe"
    assert ns.verb == "submit"
    assert ns.recipe_path == "recipes/foo"
    assert ns.yes is False
    assert ns.prepare_only is False


def test_recipe_submit_parses_yes_and_prepare_only_flags():
    ns = build_parser().parse_args(
        ["recipe", "submit", "recipes/foo", "--yes", "--prepare-only"],
    )
    assert ns.yes is True
    assert ns.prepare_only is True


def test_recipe_submit_text_mode_renders_the_ship_target_result_fields(capsys):
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert main(["recipe", "submit", "recipes/foo", "--yes"]) == EXIT_OK

    mock_submit.assert_called_once()
    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe submit: ok" in out.out
    # The StrEnum field renders as its plain value ("pending"), never
    # "ShipState.PENDING" (models.py's own Design Notes claim) -- render_text
    # formats the ORIGINAL dataclasses.asdict() dict, not a JSON round-trip,
    # so this is the one assertion that actually exercises StrEnum.__str__
    # rather than json.dumps's native str-subclass handling.
    assert "state: pending" in out.out
    assert "ShipState" not in out.out
    assert "pull/1" in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_submit_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch("pyforge.mason.cli.recipe.submit", return_value=_FIXED_SUBMIT_RESULT):
        assert (
            main(
                ["recipe", "submit", "recipes/foo", "--yes", "--format", "json"],
            )
            == EXIT_OK
        )
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe submit"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == json.loads(json.dumps(dataclasses.asdict(_FIXED_SUBMIT_RESULT)))
    # The StrEnum `state` field must serialize as a plain JSON string, not
    # raise (a bare `Enum` would not be JSON-serializable at all -- see
    # models.py's ShipState Design Notes) and not round-trip as the member's
    # repr.
    assert doc["data"]["state"] == "pending"


def test_recipe_submit_passes_recipe_path_and_resolved_flags_through(monkeypatch):
    """Mirrors `test_recipe_scan_passes_recipe_path_and_resolved_flags_
    through`: `cli.py` passes the raw `recipe_path` positional plus the
    unresolved `--cfe-root`/`--cfe-python` flag values, the real
    `os.environ`, and `Path.cwd()` -- `recipe.submit` does its own
    resolution."""
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert (
            main(
                [
                    "recipe",
                    "submit",
                    "recipes/foo",
                    "--yes",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_submit.assert_called_once()
    args, kwargs = mock_submit.call_args
    assert args == ("recipes/foo",)
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_submit_no_yes_flag_passes_confirm_false():
    """Dry run is the default (spec Always boundary, PRD "--dry-run is the
    default"): `confirm=False` reaches `recipe.submit` when `--yes` is
    absent."""
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert main(["recipe", "submit", "recipes/foo"]) == EXIT_OK

    assert mock_submit.call_args.kwargs["confirm"] is False


def test_recipe_submit_yes_flag_passes_confirm_true():
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert main(["recipe", "submit", "recipes/foo", "--yes"]) == EXIT_OK

    assert mock_submit.call_args.kwargs["confirm"] is True


def test_recipe_submit_prepare_only_flag_passes_through():
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert (
            main(
                ["recipe", "submit", "recipes/foo", "--yes", "--prepare-only"],
            )
            == EXIT_OK
        )

    assert mock_submit.call_args.kwargs["prepare_only"] is True


def test_recipe_submit_resolves_cfe_timeout_flag_via_the_shared_resolver():
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert (
            main(
                [
                    "recipe",
                    "submit",
                    "recipes/foo",
                    "--yes",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    assert mock_submit.call_args.kwargs["cfe_timeout_arg"] == 30.0


def test_recipe_submit_cfe_timeout_env_var_applies_without_the_flag(monkeypatch):
    monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert main(["recipe", "submit", "recipes/foo"]) == EXIT_OK

    assert mock_submit.call_args.kwargs["cfe_timeout_arg"] == 45.0


def test_recipe_submit_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.recipe.submit",
        return_value=_FIXED_SUBMIT_RESULT,
    ) as mock_submit:
        assert main(["recipe", "submit", "recipes/foo"]) == EXIT_OK

    assert mock_submit.call_args.kwargs["cfe_timeout_arg"] is None


def test_recipe_submit_cfe_unresolved_error_returns_exit_cfe_unavailable(capsys):
    with patch(
        "pyforge.mason.cli.recipe.submit",
        side_effect=CfeUnresolvedError(),
    ):
        rc = main(["recipe", "submit", "recipes/foo"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err


def test_recipe_submit_cfe_timeout_error_returns_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.recipe.submit",
        side_effect=CfeTimeoutError(script="submit_pr", timeout=5.0),
    ):
        rc = main(["recipe", "submit", "recipes/foo", "--yes", "--cfe-timeout", "5"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeTimeoutError(script="submit_pr", timeout=5.0))
    assert "Traceback" not in err


def test_recipe_submit_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """No mocking: the whole `recipe submit` path runs against Story 1.9's
    fixture CFE root (AD-16). `--yes` (confirm=True, prepare_only=False) is
    the interesting real-fixture case -- the stub's static canned JSON
    already includes `pr_url`, matching the full-flow-success shape exactly
    (spec Code Map), so `state` maps to `PENDING` with the PR URL as
    `reference`."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    rc = main(
        [
            "recipe",
            "submit",
            str(fake_cfe_root / "recipes" / "example"),
            "--yes",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe submit"
    assert doc["status"] == "ok"
    assert doc["data"]["target"] == "conda-forge"
    assert doc["data"]["state"] == "pending"
    assert doc["data"]["reference"] == "https://github.com/example/example/pull/1"


# --- Story 2.10: `mason recipe update <recipe_path>` ------------------------

_FIXED_UPDATE_RESULT = CfeResult(
    returncode=0,
    stdout='{"success": true, "updated": true, "new_version": "9.9.9", "message": "Recipe updated successfully."}',
    stderr="",
    json_body={
        "success": True,
        "updated": True,
        "new_version": "9.9.9",
        "message": "Recipe updated successfully.",
    },
)


def test_recipe_update_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "update", "--help"])
    assert exc.value.code == 0
    assert "update" in capsys.readouterr().out


def test_recipe_update_requires_the_recipe_path_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "update"])
    assert exc.value.code == 2
    assert "recipe_path" in capsys.readouterr().err


def test_recipe_update_parses_the_recipe_path_positional_and_defaults():
    """`--dry-run`/`--github`/`--pre` default to `False`, `--repo` to `None`
    -- these are plain per-verb flags, not part of the `argparse.SUPPRESS`-
    defaulted global set (registration comment in `cli.py`)."""
    ns = build_parser().parse_args(["recipe", "update", "recipes/foo"])
    assert ns.noun == "recipe"
    assert ns.verb == "update"
    assert ns.recipe_path == "recipes/foo"
    assert ns.dry_run is False
    assert ns.github is False
    assert ns.repo is None
    assert ns.pre is False


def test_recipe_update_parses_dry_run_github_repo_and_pre_flags():
    ns = build_parser().parse_args(
        [
            "recipe",
            "update",
            "recipes/foo",
            "--dry-run",
            "--github",
            "--repo",
            "owner/repo",
            "--pre",
        ]
    )
    assert ns.dry_run is True
    assert ns.github is True
    assert ns.repo == "owner/repo"
    assert ns.pre is True


def test_recipe_update_text_mode_renders_the_cfe_result_fields(capsys):
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert main(["recipe", "update", "recipes/foo"]) == EXIT_OK

    mock_update.assert_called_once()
    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe update: ok" in out.out
    assert "Recipe updated successfully." in out.out
    assert not out.out.lstrip().startswith("{")


def test_recipe_update_json_mode_data_matches_dataclasses_asdict_of_the_result(capsys):
    with patch("pyforge.mason.cli.recipe.update", return_value=_FIXED_UPDATE_RESULT):
        assert (
            main(
                ["recipe", "update", "recipes/foo", "--format", "json"],
            )
            == EXIT_OK
        )
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "recipe update"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == json.loads(json.dumps(dataclasses.asdict(_FIXED_UPDATE_RESULT)))


def test_recipe_update_passes_recipe_path_and_resolved_flags_through(monkeypatch):
    """`cli.py` must pass the raw `recipe_path` positional plus the
    unresolved `--cfe-root`/`--cfe-python` flag values, the real
    `os.environ`, and `Path.cwd()` -- `recipe.update` does its own
    resolution, mirroring `diagnose`'s established contract."""
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert (
            main(
                [
                    "recipe",
                    "update",
                    "recipes/foo",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert args == ("recipes/foo",)
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_update_no_dry_run_flag_passes_dry_run_false():
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert main(["recipe", "update", "recipes/foo"]) == EXIT_OK

    assert mock_update.call_args.kwargs["dry_run"] is False


def test_recipe_update_dry_run_flag_passes_dry_run_true():
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert main(["recipe", "update", "recipes/foo", "--dry-run"]) == EXIT_OK

    assert mock_update.call_args.kwargs["dry_run"] is True


def test_recipe_update_github_repo_and_pre_flags_pass_straight_through():
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert (
            main(
                [
                    "recipe",
                    "update",
                    "recipes/foo",
                    "--github",
                    "--repo",
                    "owner/repo",
                    "--pre",
                ]
            )
            == EXIT_OK
        )

    kwargs = mock_update.call_args.kwargs
    assert kwargs["github"] is True
    assert kwargs["github_repo"] == "owner/repo"
    assert kwargs["allow_prerelease"] is True


def test_recipe_update_repo_and_pre_default_to_inert_values_without_github():
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert main(["recipe", "update", "recipes/foo"]) == EXIT_OK

    kwargs = mock_update.call_args.kwargs
    assert kwargs["github"] is False
    assert kwargs["github_repo"] is None
    assert kwargs["allow_prerelease"] is False


def test_recipe_update_warns_on_stderr_when_repo_given_without_github(capsys):
    """Review pass (2026-08-12): `--repo`/`--pre` stay inert without
    `--github` (unchanged contract), but the user now gets a stderr signal
    instead of silent divergence between what they asked for and what ran."""
    with patch("pyforge.mason.cli.recipe.update", return_value=_FIXED_UPDATE_RESULT):
        assert main(["recipe", "update", "recipes/foo", "--repo", "owner/repo"]) == EXIT_OK

    err = capsys.readouterr().err
    assert "--repo/--pre have no effect without --github" in err


def test_recipe_update_warns_on_stderr_when_pre_given_without_github(capsys):
    with patch("pyforge.mason.cli.recipe.update", return_value=_FIXED_UPDATE_RESULT):
        assert main(["recipe", "update", "recipes/foo", "--pre"]) == EXIT_OK

    err = capsys.readouterr().err
    assert "--repo/--pre have no effect without --github" in err


def test_recipe_update_does_not_warn_when_repo_and_pre_given_with_github(capsys):
    with patch("pyforge.mason.cli.recipe.update", return_value=_FIXED_UPDATE_RESULT):
        assert (
            main(
                [
                    "recipe",
                    "update",
                    "recipes/foo",
                    "--github",
                    "--repo",
                    "owner/repo",
                    "--pre",
                ]
            )
            == EXIT_OK
        )

    err = capsys.readouterr().err
    assert "have no effect" not in err


def test_recipe_update_resolves_cfe_timeout_flag_via_the_shared_resolver():
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert (
            main(
                [
                    "recipe",
                    "update",
                    "recipes/foo",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    assert mock_update.call_args.kwargs["cfe_timeout_arg"] == 30.0


def test_recipe_update_cfe_timeout_env_var_applies_without_the_flag(monkeypatch):
    monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert main(["recipe", "update", "recipes/foo"]) == EXIT_OK

    assert mock_update.call_args.kwargs["cfe_timeout_arg"] == 45.0


def test_recipe_update_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.recipe.update",
        return_value=_FIXED_UPDATE_RESULT,
    ) as mock_update:
        assert main(["recipe", "update", "recipes/foo"]) == EXIT_OK

    assert mock_update.call_args.kwargs["cfe_timeout_arg"] is None


def test_recipe_update_cfe_unresolved_error_returns_exit_cfe_unavailable(capsys):
    with patch(
        "pyforge.mason.cli.recipe.update",
        side_effect=CfeUnresolvedError(),
    ):
        rc = main(["recipe", "update", "recipes/foo"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err


def test_recipe_update_cfe_timeout_error_returns_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.recipe.update",
        side_effect=CfeTimeoutError(script="update_recipe", timeout=5.0),
    ):
        rc = main(["recipe", "update", "recipes/foo", "--cfe-timeout", "5"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == str(CfeTimeoutError(script="update_recipe", timeout=5.0))
    assert "Traceback" not in err


def test_recipe_update_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """No mocking: the whole `recipe update` path (default, PyPI) runs
    against Story 1.9's fixture CFE root (AD-16), using Story 2.10's new
    `recipe_updater.py` stub."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    rc = main(
        [
            "recipe",
            "update",
            "recipes/example",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe update"
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["success"] is True
    assert doc["data"]["json_body"]["new_version"] == "9.9.9"


def test_recipe_update_github_against_fake_cfe_root_end_to_end(fake_cfe_root, monkeypatch, capsys):
    """No mocking: the `--github` dispatch path runs against Story 2.10's
    new `github_updater.py` stub."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    rc = main(
        [
            "recipe",
            "update",
            "recipes/example",
            "--github",
            "--repo",
            "owner/repo",
            "--pre",
            "--cfe-root",
            str(fake_cfe_root),
            "--cfe-python",
            sys.executable,
            "--format",
            "json",
        ]
    )

    assert rc == EXIT_OK
    doc = json.loads(capsys.readouterr().out)
    assert doc["command"] == "recipe update"
    assert doc["status"] == "ok"
    assert doc["data"]["json_body"]["success"] is True
    assert doc["data"]["json_body"]["latest_tag"] == "v9.9.9"


@pytest.mark.parametrize(
    "argv",
    [
        ["--format", "json", "recipe"],
        ["recipe", "--format", "json"],
    ],
)
def test_global_flag_parses_before_or_after_the_noun(argv):
    ns = build_parser().parse_args(argv)
    assert ns.format == "json"
    assert ns.noun == "recipe"


@pytest.mark.parametrize(
    "flag,attr",
    [
        ("--cfe-root", "cfe_root"),
        ("--cfe-python", "cfe_python"),
    ],
)
def test_global_string_flags_accepted_at_either_position(flag, attr):
    before = build_parser().parse_args([flag, "/tmp/x", "package"])
    after = build_parser().parse_args(["package", flag, "/tmp/x"])
    assert before.noun == after.noun == "package"
    assert getattr(before, attr) == "/tmp/x"
    assert getattr(after, attr) == "/tmp/x"


@pytest.mark.parametrize(
    "flag,attr",
    [
        ("--verbose", "verbose"),
        ("--quiet", "quiet"),
    ],
)
def test_global_boolean_flags_accepted_at_either_position(flag, attr):
    before = build_parser().parse_args([flag, "environment"])
    after = build_parser().parse_args(["environment", flag])
    assert before.noun == after.noun == "environment"
    assert getattr(before, attr) is True
    assert getattr(after, attr) is True


def test_cfe_timeout_flag_accepted_at_either_position_and_parses_as_float():
    before = build_parser().parse_args(["--cfe-timeout", "30", "package"])
    after = build_parser().parse_args(["package", "--cfe-timeout", "30"])
    assert before.noun == after.noun == "package"
    assert before.cfe_timeout == after.cfe_timeout == 30.0
    assert isinstance(before.cfe_timeout, float)
    assert isinstance(after.cfe_timeout, float)


def test_cfe_timeout_flag_rejects_a_non_numeric_value(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout", "not-a-number"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    # Review pass (2026-08-10): letting float()'s bare ValueError escape
    # made argparse name the private `type=` callable instead of the flag --
    # "invalid _parse_finite_float value: 'not-a-number'". The message a
    # user sees must not leak a helper's identifier.
    assert "_parse_finite_float" not in err
    assert "must be a number of seconds" in err


@pytest.mark.parametrize("bad_value", ["nan", "inf", "Infinity"])
def test_cfe_timeout_flag_rejects_nan_and_infinite_values(bad_value, capsys):
    """Review pass (2026-08-09): `float()` parses `nan`/`inf`/`-inf` as
    well-formed, but neither is a usable subprocess timeout -- `nan` never
    compares as expired, `inf` never expires at all. Must be rejected the
    same way a non-numeric value is.

    `-inf` is deliberately excluded from this parametrize list -- see
    `test_cfe_timeout_flag_rejects_negative_infinity_via_equals_form` below,
    which exercises it correctly."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout", bad_value])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    # Asserted on the validator's own wording, not just exit code 2 + the
    # flag name (review pass, 2026-08-10, second): that weaker pair is
    # exactly what let the `-inf` case pass while argparse -- not
    # `_parse_finite_float` -- was doing the rejecting.
    assert "must be a finite, positive number" in err


def test_cfe_timeout_flag_rejects_negative_infinity_via_equals_form(capsys):
    """`-inf` as a separate argv token looks like another option string to
    argparse's own parser (leading `-`), so `--cfe-timeout -inf` is rejected
    by argparse's own "expected one argument" error *before*
    `_parse_finite_float` ever runs -- both forms exit 2 with `--cfe-timeout`
    in the message, so a naive two-token test for `-inf` passes without
    actually proving the isfinite guard rejects it (edge-case-hunter
    finding, review pass 2026-08-10). The `--cfe-timeout=-inf` single-token
    form bypasses that ambiguity and genuinely reaches the custom
    validator."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout=-inf"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    # The whole point of the equals form: prove `_parse_finite_float` did the
    # rejecting, not argparse's own "expected one argument".
    assert "must be a finite, positive number" in err


@pytest.mark.parametrize("bad_value", ["0", "-1", "-0.5"])
def test_cfe_timeout_flag_rejects_non_positive_values(bad_value, capsys):
    """Review pass (2026-08-10): zero and negative timeouts are equally
    unusable as nan/inf, just via the opposite failure mode -- they expire
    before the delegated operation has any chance to run.

    `-1`/`-0.5` reach the validator rather than being read as option strings
    because argparse treats a leading-`-` token as a negative number when the
    parser has no option that looks like one; the wording assertion below
    pins that, instead of accepting any exit-2 path (review pass,
    2026-08-10, second)."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--cfe-timeout", bad_value])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--cfe-timeout" in err
    assert "must be a finite, positive number" in err


def test_all_six_v1_knobs_have_both_a_flag_and_an_environment_form(monkeypatch):
    """AD-13/FR-48: the v1 knob set is closed and fully enumerated -- each of
    the six has both a flag and an environment-variable form, and each
    resolves flag -> environment -> default. One test, all six (the spec's
    own AC wording).

    The three resolution assertions per knob were added in the 2026-08-10
    (third) review pass. This test previously only checked that six flag
    names and six variable names appear in `format_help()` -- which would
    still pass with `_resolve_optional_float` deleted outright, and asserts
    nothing whatsoever about the precedence the AC actually names. Each
    knob's environment value is chosen so no sub-assertion is vacuous: the
    flag-wins case uses an environment value that would produce a *different*
    answer if the flag were ignored, and the environment case uses one that
    differs from the default.
    """
    knobs = (
        {
            "flag": "--cfe-root",
            "env_var": _ENV_CFE_ROOT,
            "dest": "cfe_root",
            "argv": ["--cfe-root", "/from/flag"],
            "flag_wins": "/from/flag",
            "env_raw": "/from/env",
            "env_wins": "/from/env",
            "default": "auto",
            "resolve": lambda v: _resolve_str(v, _ENV_CFE_ROOT, "auto"),
        },
        {
            "flag": "--cfe-python",
            "env_var": _ENV_CFE_PYTHON,
            "dest": "cfe_python",
            "argv": ["--cfe-python", "/from/flag/python"],
            "flag_wins": "/from/flag/python",
            "env_raw": "/from/env/python",
            "env_wins": "/from/env/python",
            "default": "auto",
            "resolve": lambda v: _resolve_str(v, _ENV_CFE_PYTHON, "auto"),
        },
        {
            "flag": "--cfe-timeout",
            "env_var": _ENV_CFE_TIMEOUT,
            "dest": "cfe_timeout",
            "argv": ["--cfe-timeout", "30"],
            "flag_wins": 30.0,
            "env_raw": "45",
            "env_wins": 45.0,
            "default": None,
            "resolve": lambda v: _resolve_optional_float(v, _ENV_CFE_TIMEOUT),
        },
        {
            # --format's default is one of its own two choices, so the flag
            # form deliberately asks for the default value while the
            # environment asks for the other one: if the flag were ignored,
            # the flag-wins case would come back "json".
            "flag": "--format",
            "env_var": _ENV_FORMAT,
            "dest": "format",
            "argv": ["--format", "text"],
            "flag_wins": "text",
            "env_raw": "json",
            "env_wins": "json",
            "default": "text",
            "resolve": lambda v: _resolve_str(v, _ENV_FORMAT, "text"),
        },
        {
            # Same shape for the two booleans, whose default is also one of
            # only two possible values: the flag-wins case pairs `--verbose`
            # with a falsy environment value, the environment case with a
            # truthy one.
            "flag": "--verbose",
            "env_var": _ENV_VERBOSE,
            "dest": "verbose",
            "argv": ["--verbose"],
            "flag_wins": True,
            "env_raw": "1",
            "env_wins": True,
            "default": False,
            "conflict_env_raw": "0",
            "resolve": lambda v: _resolve_bool(v, _ENV_VERBOSE, False),
        },
        {
            "flag": "--quiet",
            "env_var": _ENV_QUIET,
            "dest": "quiet",
            "argv": ["--quiet"],
            "flag_wins": True,
            "env_raw": "1",
            "env_wins": True,
            "default": False,
            "conflict_env_raw": "0",
            "resolve": lambda v: _resolve_bool(v, _ENV_QUIET, False),
        },
    )
    assert len(knobs) == 6, "AD-13's v1 knob set is closed at six"

    help_text = build_parser().format_help()
    for knob in knobs:
        flag, env_var, dest, resolve = knob["flag"], knob["env_var"], knob["dest"], knob["resolve"]
        assert flag in help_text, f"{flag} missing from --help output"
        assert env_var in help_text, f"{env_var} missing from --help output"

        # 1. Flag beats a conflicting environment value.
        monkeypatch.setenv(env_var, knob.get("conflict_env_raw", knob["env_raw"]))
        ns = build_parser().parse_args(knob["argv"])
        assert resolve(getattr(ns, dest, None)) == knob["flag_wins"], f"{flag}: flag must win"

        # 2. Environment is read when the flag is absent.
        monkeypatch.setenv(env_var, knob["env_raw"])
        ns = build_parser().parse_args([])
        assert resolve(getattr(ns, dest, None)) == knob["env_wins"], f"{env_var}: env must apply"

        # 3. Default when neither is given.
        monkeypatch.delenv(env_var)
        ns = build_parser().parse_args([])
        assert resolve(getattr(ns, dest, None)) == knob["default"], f"{flag}: default must apply"


def test_keyboard_interrupt_projects_to_130(monkeypatch):
    monkeypatch.setattr("pyforge.mason.cli.build_parser", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert main([]) == EXIT_INTERRUPTED


def test_unanticipated_exception_projects_to_exit_failed_with_traceback(monkeypatch, capsys):
    """A crash must project to the documented EXIT_FAILED (AD-7), with the
    full traceback on stderr -- not the interpreter's bare default and not a
    silent failure."""
    monkeypatch.setattr("pyforge.mason.cli.build_parser", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    rc = main([])
    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "Traceback" in err
    assert "RuntimeError" in err
    assert "boom" in err


def test_mason_error_raised_in_main_prints_message_and_returns_exit_failed(monkeypatch, capsys):
    """A MasonError raised inside main()'s try block is an anticipated
    failure (AD-7): its `identifier: message` goes to stderr, no traceback,
    and the process exits EXIT_FAILED -- same monkeypatch pattern as the
    KeyboardInterrupt/RuntimeError cases above. No verb dispatch exists yet
    (later epics), so this proves the handler itself, not a dispatch path.
    The identifier is deliberately synthetic: pinning a real one like
    `cfe:unresolved` -> EXIT_FAILED would pre-break Story 1.7, which maps
    CFE-unavailable to EXIT_CFE_UNAVAILABLE (3)."""
    monkeypatch.setattr(
        "pyforge.mason.cli.build_parser",
        lambda: (_ for _ in ()).throw(MasonError("test:injected-failure", "synthetic anticipated failure")),
    )
    rc = main([])
    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert err.strip() == "test:injected-failure: synthetic anticipated failure"
    assert "Traceback" not in err


# --- Story 1.7: CfeUnresolvedError degrades to EXIT_CFE_UNAVAILABLE --------


def test_cfe_unresolved_error_raised_in_main_returns_exit_cfe_unavailable(monkeypatch, capsys):
    """A `CfeUnresolvedError` raised inside main()'s try block must be caught
    by its own branch -- listed before `except MasonError`, since it is a
    subclass -- and mapped to EXIT_CFE_UNAVAILABLE (3), not the generic
    EXIT_FAILED the MasonError branch below it produces. Same monkeypatch
    pattern as the synthetic-MasonError test above; no `recipe` verb exists
    yet to dispatch through, so this proves the handler itself (spec
    Acceptance Criteria)."""
    monkeypatch.setattr(
        "pyforge.mason.cli.build_parser",
        lambda: (_ for _ in ()).throw(CfeUnresolvedError()),
    )
    rc = main([])
    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())
    assert "Traceback" not in err
    for step_name in ("flag", "environment", "cwd-walk", "not-found"):
        assert step_name in err


# --- AD-13 precedence helpers, tested directly as pure functions -----------
#
# Nothing in main() consumes a resolved value this story (--format feeds
# render.py in Story 1.4, --cfe-root/--cfe-python feed the resolution chain
# in Stories 1.5-1.6, --verbose/--quiet feed logging in Story 1.10), so the
# precedence contract is proven against the helpers directly.


class TestResolveStr:
    def test_flag_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "json")
        assert _resolve_str("text", "MASON_FORMAT", "text") == "text"

    def test_env_wins_over_default(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "json")
        assert _resolve_str(None, "MASON_FORMAT", "text") == "json"

    def test_neither_set_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("MASON_FORMAT", raising=False)
        assert _resolve_str(None, "MASON_FORMAT", "text") == "text"

    def test_whitespace_only_env_value_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_ROOT", "   ")
        assert _resolve_str(None, "MASON_CFE_ROOT", "default-root") == "default-root"

    def test_whitespace_only_flag_value_falls_through_to_env(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "json")
        assert _resolve_str("   ", "MASON_FORMAT", "text") == "json"

    def test_whitespace_only_flag_and_env_fall_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MASON_FORMAT", "   ")
        assert _resolve_str("   ", "MASON_FORMAT", "text") == "text"

    def test_padded_flag_value_is_returned_stripped(self, monkeypatch):
        monkeypatch.delenv("MASON_CFE_ROOT", raising=False)
        assert _resolve_str("  /x  ", "MASON_CFE_ROOT", "d") == "/x"

    def test_padded_env_value_is_returned_stripped(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_ROOT", "  /x  ")
        assert _resolve_str(None, "MASON_CFE_ROOT", "d") == "/x"


class TestResolveBool:
    def test_flag_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("MASON_VERBOSE", "0")
        assert _resolve_bool(True, "MASON_VERBOSE", False) is True

    def test_env_wins_over_default(self, monkeypatch):
        monkeypatch.setenv("MASON_VERBOSE", "1")
        assert _resolve_bool(None, "MASON_VERBOSE", False) is True

    def test_neither_set_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("MASON_QUIET", raising=False)
        assert _resolve_bool(None, "MASON_QUIET", False) is False

    @pytest.mark.parametrize("raw", ["", "0", "false", "FALSE", "no", "No", "  false  "])
    def test_falsy_env_spellings(self, raw, monkeypatch):
        monkeypatch.setenv("MASON_QUIET", raw)
        assert _resolve_bool(None, "MASON_QUIET", True) is False

    @pytest.mark.parametrize("raw", ["1", "true", "yes"])
    def test_truthy_env_spellings(self, raw, monkeypatch):
        monkeypatch.setenv("MASON_VERBOSE", raw)
        assert _resolve_bool(None, "MASON_VERBOSE", False) is True


class TestResolveOptionalFloat:
    """`_resolve_optional_float` has no Mason-wide `default` parameter --
    unlike `_resolve_str`/`_resolve_bool` above, its terminal fallback is
    always `None` (spec Intent: FR-4's "per-operation default" lives at a
    future call site, not in this resolver)."""

    def test_flag_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "99")
        assert _resolve_optional_float(30.0, "MASON_CFE_TIMEOUT") == 30.0

    def test_small_fractional_flag_value_still_wins_over_env(self, monkeypatch):
        """Not a truthiness check -- an unusual but *usable* timeout must
        still win over the environment."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(0.001, "MASON_CFE_TIMEOUT") == 0.001

    @pytest.mark.parametrize(
        "unusable",
        [0.0, -5.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_unusable_flag_value_falls_through_to_env(self, monkeypatch, unusable):
        """Review pass (2026-08-10): this resolver used to validate only its
        environment half, so `nan`/`inf`/`0`/negative passed straight
        through from the flag parameter -- handing a caller exactly the
        value `_parse_finite_float` and `cfe.run_streamed` both reject. A
        flag value that fails the same finite-and-positive test is treated
        as "absent at the step that supplied it" and resolution falls
        through to the environment, mirroring `_resolve_str`'s handling of a
        whitespace-only flag value."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(unusable, "MASON_CFE_TIMEOUT") == 45.0

    @pytest.mark.parametrize(
        "unusable",
        [0.0, -5.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_unusable_flag_value_with_no_env_resolves_to_none(self, monkeypatch, unusable):
        """...and with nothing to fall through to, the resolver returns
        `None` -- never a value its own siblings reject as unusable."""
        monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
        assert _resolve_optional_float(unusable, "MASON_CFE_TIMEOUT") is None

    @pytest.mark.parametrize("unusable", [True, False])
    def test_bool_flag_value_falls_through_to_env(self, monkeypatch, unusable):
        """`bool` is a subclass of `int`, so `True` cleared both the
        `isfinite` and `> 0` checks and was returned verbatim -- and
        `cfe.run_streamed` rejects a bool `timeout` outright, so the resolver
        was still handing out a value its documented consumer refuses
        (review pass, 2026-08-10, second). Treated as unusable, like every
        other value that fails the same standard."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(unusable, "MASON_CFE_TIMEOUT") == 45.0

    @pytest.mark.parametrize("not_a_number", ["30", "", Decimal("30"), object()])
    def test_non_numeric_flag_value_falls_through_instead_of_raising(
        self,
        monkeypatch,
        not_a_number,
    ):
        """A flag value that is not a real number at all reached
        `math.isfinite` and raised its bare "must be real number, not str" --
        naming neither this function nor the parameter (review pass,
        2026-08-10, third). `cfe.run_streamed`'s `timeout` guard was given an
        isinstance check for exactly this message; its sibling resolver was
        left without one. Treated as unusable and fallen through, like every
        other value that fails this resolver's standard -- this function is
        documented as never raising."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(not_a_number, "MASON_CFE_TIMEOUT") == 45.0

    def test_non_numeric_flag_value_with_no_env_resolves_to_none(self, monkeypatch):
        monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
        assert _resolve_optional_float("30", "MASON_CFE_TIMEOUT") is None

    def test_env_wins_over_none_default(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "45")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") == 45.0

    def test_padded_env_value_is_parsed_after_stripping(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "  12.5  ")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") == 12.5

    def test_neither_set_falls_back_to_none(self, monkeypatch):
        monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    def test_malformed_env_value_falls_back_to_none(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "not-a-number")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    def test_whitespace_only_env_value_falls_back_to_none(self, monkeypatch):
        monkeypatch.setenv("MASON_CFE_TIMEOUT", "   ")
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    @pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "Infinity"])
    def test_non_finite_env_value_falls_back_to_none(self, raw, monkeypatch):
        """Review pass (2026-08-09): `float()` parses these as well-formed,
        but a `nan`/`inf` timeout is unusable -- must degrade to `None`
        exactly like a genuinely malformed value, mirroring
        `_parse_finite_float`'s flag-side guard."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", raw)
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None

    @pytest.mark.parametrize("raw", ["0", "-1", "-0.5"])
    def test_non_positive_env_value_falls_back_to_none(self, raw, monkeypatch):
        """Review pass (2026-08-10): zero and negative timeouts are equally
        unusable as nan/inf -- must degrade to `None` the same way,
        mirroring `_parse_finite_float`'s flag-side guard."""
        monkeypatch.setenv("MASON_CFE_TIMEOUT", raw)
        assert _resolve_optional_float(None, "MASON_CFE_TIMEOUT") is None


# --- Story 1.10: `_configure_logging` -- verbosity -> root logger level, ---
# ------------------------------------- always stderr, never stdout --------


class TestConfigureLogging:
    def test_default_level_is_warning_and_info_is_swallowed(self, capsys):
        _configure_logging(verbose=False, quiet=False)
        assert logging.getLogger().getEffectiveLevel() == logging.WARNING
        logger = logging.getLogger("pyforge.mason.test.default")
        logger.info("swallowed-info")
        logger.warning("shown-warning")
        out = capsys.readouterr()
        assert out.out == ""
        assert "swallowed-info" not in out.err
        assert "shown-warning" in out.err

    def test_verbose_sets_level_info(self, capsys):
        _configure_logging(verbose=True, quiet=False)
        assert logging.getLogger().getEffectiveLevel() == logging.INFO
        logger = logging.getLogger("pyforge.mason.test.verbose")
        logger.info("shown-info")
        out = capsys.readouterr()
        assert out.out == ""
        assert "shown-info" in out.err

    def test_quiet_sets_level_error(self, capsys):
        _configure_logging(verbose=False, quiet=True)
        assert logging.getLogger().getEffectiveLevel() == logging.ERROR
        logger = logging.getLogger("pyforge.mason.test.quiet")
        logger.warning("swallowed-warning")
        logger.error("shown-error")
        out = capsys.readouterr()
        assert out.out == ""
        assert "swallowed-warning" not in out.err
        assert "shown-error" in out.err

    def test_quiet_wins_when_both_verbose_and_quiet_are_given(self, capsys):
        """Documented tie-break (spec Boundaries & Constraints): the ACs
        don't specify one, so `--quiet` (the more conservative choice) wins."""
        _configure_logging(verbose=True, quiet=True)
        assert logging.getLogger().getEffectiveLevel() == logging.ERROR


def test_quiet_env_var_beats_an_explicit_verbose_flag(monkeypatch):
    """Review pass (2026-08-10): the tie-break is applied to the two
    *resolved* values, after each knob independently ran AD-13's
    flag -> environment -> default chain -- so a stale `MASON_QUIET=1` in a
    shell profile silently mutes an explicit `--verbose` run. This follows
    from AD-13's per-knob precedence rather than contradicting it, but it is
    surprising, so it is pinned here rather than left to be rediscovered."""
    monkeypatch.setenv("MASON_QUIET", "1")
    monkeypatch.delenv("MASON_VERBOSE", raising=False)
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--verbose"]) == EXIT_OK
    assert logging.getLogger().getEffectiveLevel() == logging.ERROR


def test_env_var_value_never_appears_in_captured_stderr_log_output(monkeypatch, capsys):
    """Regression guard for the spec's env-value-leak row: a distinctive
    marker set via a resolved env var must never appear in stderr (the log
    stream), even at --verbose. `doctor.build_report` is mocked to a fixed
    report (existing doctor-test pattern) -- its own stdout report may
    legitimately echo a resolved value; only the log stream is constrained."""
    marker = "MASON-ENV-LEAK-MARKER-3f9a7c"
    monkeypatch.setenv("MASON_CFE_ROOT", marker)
    with patch("pyforge.mason.cli.doctor.build_report", return_value=_FIXED_REPORT):
        assert main(["doctor", "--verbose"]) == EXIT_OK
    err = capsys.readouterr().err
    assert marker not in err


# --- Story 2.3: credential isolation (AD-14) --------------------------------


@pytest.mark.parametrize(
    "flags",
    [[], ["--quiet"], ["--verbose"], ["--format", "json"], ["--verbose", "--format", "json"]],
    ids=["default", "quiet", "verbose", "json", "verbose-json"],
)
def test_jfrog_credential_sentinel_never_appears_in_doctor_output(monkeypatch, capsys, tmp_path, flags):
    """AD-14: a JFROG_* credential must never surface in `mason doctor`'s
    output at ANY verbosity (review pass, Edge Case Hunter: the original
    version only exercised --verbose despite this exact claim) or in EITHER
    output format (third review pass, Blind Hunter: `--format json` is the
    documented machine-consumed contract surface and `render_json` was never
    exercised with the sentinel set -- latent only because `render_text`
    happens to print the same `data` keys today).

    `doctor.build_report` is deliberately NOT mocked (follow-up review, both
    reviewers, reproduced): it is the only function in the `doctor` path
    that receives `os.environ` at all, so patching it made this test's own
    claim -- that the *report* never echoes the ambient environment --
    structurally unreachable. With the mock in place, a `build_report` that
    folded `environ` into the report printed `JFROG_API_KEY=<sentinel>` to
    stdout while all three parametrized cases still passed.

    Hermeticity follows `test_doctor.py::
    test_build_report_never_raises_against_a_real_unresolved_environment`'s
    established pattern (AD-16): `PATH` points at an empty directory so every
    engine probe reliably reports absent, and the CFE-root walk starts from
    an empty `tmp_path`, while `resolve.py`'s chains and `cfe.py`'s real
    subprocess probe stay genuinely unmocked. The `MASON_*` deletes are that
    hermeticity, not case separation: a stale `MASON_CFE_ROOT`/`MASON_FORMAT`
    in the runner's shell would change what is rendered (fourth review pass,
    Blind Hunter -- the earlier claim that they "keep the three verbosity
    cases from collapsing into one" was false in both directions; see
    below).

    The three verbosity ids exercise ONE render path today, deliberately and
    knowingly (fourth review pass, both reviewers, reproduced): `--quiet`
    and `--verbose` reach only `_configure_logging`, `render.py` has no
    verbosity branch at all, and nothing in the package emits a log record
    yet (`conftest.py`'s own docstring), so all three produce byte-identical
    output. They are kept as forward coverage for the AC's "at ANY
    verbosity" -- the moment a verbosity-conditional render path lands, this
    test covers it without being rewritten -- while the `format` axis is the
    one that genuinely differs today. The pre-existing
    `test_env_var_value_never_appears_in_captured_stderr_log_output` above
    owns the log-stream surface.

    The POSITIVE control is what keeps the sentinel assertions from passing
    vacuously: an absence assertion over empty output proves nothing, so the
    report must first be shown to have actually rendered."""
    for name in ("MASON_QUIET", "MASON_VERBOSE", "MASON_FORMAT", "MASON_CFE_ROOT", "MASON_CFE_PYTHON"):
        monkeypatch.delenv(name, raising=False)
    empty_path_dir = tmp_path / "empty-path"
    empty_path_dir.mkdir()
    monkeypatch.setenv("PATH", str(empty_path_dir))
    monkeypatch.chdir(tmp_path)

    sentinel = "JFROG-SENTINEL-9f3e7a1c"
    monkeypatch.setenv("JFROG_API_KEY", sentinel)

    assert main(["doctor", *flags]) == EXIT_OK

    out = capsys.readouterr()
    # Positive control first: `mason_version` is a `DoctorReport` field that
    # both renderers emit (`render_text` prints one line per `data` key,
    # `render_json` puts the same keys in the envelope's `data`), so this
    # fails the moment the report stops reaching stdout -- without it, the
    # two absence assertions below would pass just as happily against empty
    # output (fourth review pass, both reviewers).
    assert "mason_version" in out.out
    assert sentinel not in out.out
    assert sentinel not in out.err


# --- Story 2.6: `recipe build` verb dispatch --------------------------------

_FIXED_BUILD_RESULT = BuildResult(
    mode="native",
    config="linux64",
    returncode=0,
    stdout="built ok",
    artifact_dir="build_artifacts/linux64",
)


def test_recipe_build_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["recipe", "build", "--help"])
    assert exc.value.code == 0
    assert "build" in capsys.readouterr().out


def test_recipe_build_happy_path_text_mode(capsys):
    with patch(
        "pyforge.mason.cli.recipe.build",
        return_value=_FIXED_BUILD_RESULT,
    ) as mock_build:
        assert main(["recipe", "build", "recipes/foo"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe build: ok" in out.out
    assert "artifact_dir: build_artifacts/linux64" in out.out
    assert "returncode: 0" in out.out

    mock_build.assert_called_once()
    args, kwargs = mock_build.call_args
    assert args[0] == "recipes/foo"
    assert kwargs["docker"] is False
    assert kwargs["config"] is None


def test_recipe_build_happy_path_json_mode(capsys):
    with patch("pyforge.mason.cli.recipe.build", return_value=_FIXED_BUILD_RESULT):
        assert main(["recipe", "build", "recipes/foo", "--format", "json"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "recipe build"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == dataclasses.asdict(_FIXED_BUILD_RESULT)


def test_recipe_build_docker_flag_dispatches_with_config(capsys):
    with patch(
        "pyforge.mason.cli.recipe.build",
        return_value=_FIXED_BUILD_RESULT,
    ) as mock_build:
        assert (
            main(
                ["recipe", "build", "recipes/foo", "--docker", "--config", "linux64"],
            )
            == EXIT_OK
        )

    kwargs = mock_build.call_args.kwargs
    assert kwargs["docker"] is True
    assert kwargs["config"] == "linux64"


def test_recipe_build_docker_without_config_is_a_usage_error(capsys):
    """spec I/O matrix: `--docker` without `--config` is a usage error
    BEFORE any CFE resolution -- `recipe.build` must never even be called."""
    with patch("pyforge.mason.cli.recipe.build") as mock_build:
        rc = main(["recipe", "build", "recipes/foo", "--docker"])

    assert rc == EXIT_USAGE
    out = capsys.readouterr()
    assert out.out == ""
    assert "--docker" in out.err
    assert "--config" in out.err
    mock_build.assert_not_called()


def test_recipe_build_config_without_docker_is_a_usage_error(capsys):
    with patch("pyforge.mason.cli.recipe.build") as mock_build:
        rc = main(["recipe", "build", "recipes/foo", "--config", "linux64"])

    assert rc == EXIT_USAGE
    out = capsys.readouterr()
    assert out.out == ""
    assert "--config" in out.err
    assert "--docker" in out.err
    mock_build.assert_not_called()


def test_recipe_build_docker_with_a_blank_config_is_treated_as_missing(capsys):
    """Review pass: a whitespace-only `--config` must report the same
    "requires --config" usage error as omitting the flag entirely, matching
    `_resolve_str`'s established "whitespace-only counts as not supplied"
    convention -- not silently pass the pairing check and hand `cfe.
    build_docker` a blank value."""
    with patch("pyforge.mason.cli.recipe.build") as mock_build:
        rc = main(["recipe", "build", "recipes/foo", "--docker", "--config", "   "])

    assert rc == EXIT_USAGE
    out = capsys.readouterr()
    assert "--docker" in out.err
    assert "--config" in out.err
    mock_build.assert_not_called()


def test_recipe_build_failed_child_still_renders_ok(capsys):
    """A non-zero delegated build returncode is DATA, never raised (AD-4) --
    `recipe build` itself still reports EXIT_OK, mirroring `doctor`'s
    established "the gap is data" precedent."""
    failed_result = BuildResult(
        mode="native",
        config="linux64",
        returncode=1,
        stdout="build failed",
        artifact_dir="build_artifacts/linux64",
    )
    with patch("pyforge.mason.cli.recipe.build", return_value=failed_result):
        assert main(["recipe", "build", "recipes/foo"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    assert "recipe build: ok" in out.out
    assert "returncode: 1" in out.out


def test_recipe_build_passes_cfe_flags_environ_and_cwd_through():
    with patch(
        "pyforge.mason.cli.recipe.build",
        return_value=_FIXED_BUILD_RESULT,
    ) as mock_build:
        assert (
            main(
                [
                    "recipe",
                    "build",
                    "recipes/foo",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-python",
                    "/explicit/python",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    kwargs = mock_build.call_args.kwargs
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_python_arg"] == "/explicit/python"
    assert kwargs["cfe_timeout_arg"] == 30.0
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()


def test_recipe_build_cfe_timeout_and_flags_absent_pass_none_through():
    with patch(
        "pyforge.mason.cli.recipe.build",
        return_value=_FIXED_BUILD_RESULT,
    ) as mock_build:
        assert main(["recipe", "build", "recipes/foo"]) == EXIT_OK

    kwargs = mock_build.call_args.kwargs
    assert kwargs["cfe_root_arg"] is None
    assert kwargs["cfe_python_arg"] is None
    assert kwargs["cfe_timeout_arg"] is None


def test_recipe_build_cfe_unresolved_error_projects_to_exit_cfe_unavailable(capsys):
    with patch("pyforge.mason.cli.recipe.build", side_effect=CfeUnresolvedError()):
        rc = main(["recipe", "build", "recipes/foo"])

    assert rc == EXIT_CFE_UNAVAILABLE
    err = capsys.readouterr().err
    assert err.strip() == str(CfeUnresolvedError())


def test_recipe_build_global_flag_parses_after_the_verb_and_its_positional():
    """`mason recipe build <path> --format json` -- a global flag given
    AFTER the verb and its positional must still parse, since the `build`
    verb parser also carries `global_flags` as a parent."""
    ns = build_parser().parse_args(["recipe", "build", "recipes/foo", "--format", "json"])
    assert ns.noun == "recipe"
    assert ns.verb == "build"
    assert ns.recipe_path == "recipes/foo"
    assert ns.format == "json"


# --- Story 3.2: `package build` verb dispatch --------------------------------

_FIXED_PACKAGE_BUILD_RESULT = PackageBuildResult(
    target="library",
    project_path="/proj",
    wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
    sdist_path="/proj/dist/pkg-0.1.0.tar.gz",
    conda_path="/proj/dist-conda/pkg-0.1.0-abc123_0.conda",
    wheel_version="0.1.0",
    conda_version="0.1.0",
    pep517_returncode=0,
    pixi_returncode=0,
    pep517_stdout="Successfully built pkg\n",
    pixi_stdout="Building pkg\n",
)


def test_package_build_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["package", "build", "--help"])
    assert exc.value.code == 0
    assert "build" in capsys.readouterr().out


def test_package_build_happy_path_text_mode(capsys):
    with patch(
        "pyforge.mason.cli.package.build",
        return_value=_FIXED_PACKAGE_BUILD_RESULT,
    ) as mock_build:
        assert main(["package", "build", "myproj"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    assert "package build: ok" in out.out
    assert "wheel_version: 0.1.0" in out.out
    assert "conda_version: 0.1.0" in out.out

    mock_build.assert_called_once()
    args, kwargs = mock_build.call_args
    assert args[0] == "myproj"
    assert kwargs["target"] == "library"


def test_package_build_happy_path_json_mode(capsys):
    with patch(
        "pyforge.mason.cli.package.build",
        return_value=_FIXED_PACKAGE_BUILD_RESULT,
    ):
        assert main(["package", "build", "myproj", "--format", "json"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "package build"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == dataclasses.asdict(_FIXED_PACKAGE_BUILD_RESULT)


def test_package_build_invalid_target_is_a_usage_error(capsys):
    """`--target`'s `choices=("library",)` -- an argparse usage error,
    naming `library` as the v1 set (spec I/O matrix), never reaching
    `package.build` at all."""
    with patch("pyforge.mason.cli.package.build") as mock_build:
        rc = main(["package", "build", "myproj", "--target", "application"])

    assert rc == EXIT_USAGE
    err = capsys.readouterr().err
    assert "library" in err
    mock_build.assert_not_called()


def test_package_build_failed_child_still_renders_ok(capsys):
    """A non-zero delegated engine returncode is DATA, never raised (AD-4)
    -- mirrors `recipe build`'s own established "the gap is data"
    precedent."""
    failed_result = PackageBuildResult(
        target="library",
        project_path="/proj",
        wheel_path=None,
        sdist_path=None,
        conda_path=None,
        wheel_version=None,
        conda_version=None,
        pep517_returncode=1,
        pixi_returncode=0,
        pep517_stdout="error: build backend failed\n",
        pixi_stdout="Building pkg\n",
    )
    with patch("pyforge.mason.cli.package.build", return_value=failed_result):
        assert main(["package", "build", "myproj"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    assert "package build: ok" in out.out
    assert "pep517_returncode: 1" in out.out


def test_package_build_version_mismatch_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.package.build",
        side_effect=PackageVersionMismatchError(
            wheel_version="0.1.0",
            conda_version="0.2.0",
            wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
            conda_path="/proj/dist-conda/pkg-0.2.0-abc123_0.conda",
        ),
    ):
        rc = main(["package", "build", "myproj"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "0.1.0" in err
    assert "0.2.0" in err


def test_package_build_engine_absent_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.package.build",
        side_effect=EngineAbsentError("pixi", "pixi"),
    ):
        rc = main(["package", "build", "myproj"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "pixi" in err


def test_package_build_default_target_is_library():
    with patch(
        "pyforge.mason.cli.package.build",
        return_value=_FIXED_PACKAGE_BUILD_RESULT,
    ) as mock_build:
        assert main(["package", "build", "myproj"]) == EXIT_OK

    assert mock_build.call_args.kwargs["target"] == "library"


def test_package_build_never_reads_cfe_flags():
    """spec Always boundary: `package.build()` has no `cfe_root_arg`/
    `cfe_python_arg`/`cfe_timeout_arg` parameters -- passing the shared
    `--cfe-root`/`--cfe-python`/`--cfe-timeout` global flags must still
    parse (they are on `global_flags`, shared by every noun) but never
    reach `package.build`'s call."""
    with patch(
        "pyforge.mason.cli.package.build",
        return_value=_FIXED_PACKAGE_BUILD_RESULT,
    ) as mock_build:
        assert (
            main(
                [
                    "package",
                    "build",
                    "myproj",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    kwargs = mock_build.call_args.kwargs
    assert "cfe_root_arg" not in kwargs
    assert "cfe_python_arg" not in kwargs
    assert "cfe_timeout_arg" not in kwargs


def test_package_build_global_flag_parses_after_the_verb_and_its_positional():
    ns = build_parser().parse_args(["package", "build", "myproj", "--format", "json"])
    assert ns.noun == "package"
    assert ns.verb == "build"
    assert ns.project_path == "myproj"
    assert ns.format == "json"


def test_package_noun_metavar_reflects_the_registered_verbs(capsys):
    """Mirrors `test_recipe_diagnose_verb_metavar_reflects_the_registered_
    verb` above: `package` previously registered no verb at all, so its own
    bad-verb usage error must now name its registered verbs, not the stale
    literal `{}`. Story 3.2 registered the first, `build`; Story 3.9 widens
    this to two, `build` and `ship`, in registration order."""
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["package", "bogus-verb"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "{build,ship}" in err
    assert "argument {}:" not in err


# --- Story 3.9: `package ship --to <targets>` / `package --ship <targets>` --

_FIXED_SHIP_RESULTS = (
    ShipTargetResult(
        target="pypi",
        state=ShipState.TERMINAL,
        reference="https://pypi.org/project/pkg/0.1.0/",
        message="View at:\n...\n",
    ),
    ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/example/example/pull/1",
        message="PR created: https://github.com/example/example/pull/1",
    ),
)


def test_package_ship_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["package", "ship", "--help"])
    assert exc.value.code == 0
    assert "ship" in capsys.readouterr().out


def test_package_ship_requires_the_to_flag(capsys):
    """`--to` is `required=True` on the canonical verb form -- a native
    argparse usage error, no dispatch reached at all."""
    with patch("pyforge.mason.cli.package.ship") as mock_ship:
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["package", "ship"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--to" in err
    mock_ship.assert_not_called()


def test_package_ship_parses_to_and_defaults():
    """`--target`/`--yes`/`--recipe-path` default to `argparse.SUPPRESS`
    (review pass 1) -- when omitted, they are simply ABSENT from the parsed
    namespace, not present holding a plain default value; a direct
    `ns.target`/`ns.yes`/`ns.recipe_path` access would raise
    `AttributeError`. `_dispatch_package_ship` resolves each one via
    `getattr(ns, ..., <default>)` instead (`_add_ship_flags`'s own
    docstring)."""
    ns = build_parser().parse_args(["package", "ship", "--to", "pypi"])
    assert ns.noun == "package"
    assert ns.verb == "ship"
    assert ns.to == "pypi"
    assert not hasattr(ns, "target")
    assert not hasattr(ns, "yes")
    assert not hasattr(ns, "recipe_path")
    assert getattr(ns, "target", "library") == "library"
    assert getattr(ns, "yes", False) is False
    assert getattr(ns, "recipe_path", None) is None


def test_package_ship_canonical_form_dispatches_to_package_ship(capsys):
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "ship", "--to", "pypi,conda-forge", "--yes"]) == EXIT_OK

    mock_ship.assert_called_once()
    args, kwargs = mock_ship.call_args
    assert args == ("pypi,conda-forge",)
    assert kwargs["confirm"] is True
    assert kwargs["target"] == "library"
    assert kwargs["recipe_path"] is None
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()
    out = capsys.readouterr()
    assert out.err == ""
    assert "package ship: ok" in out.out


def test_package_ship_bare_noun_alias_dispatches_identically(capsys):
    """spec I/O matrix: 'Alias happy path... identical dispatch/result to
    the canonical form above.'"""
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "--ship", "pypi,conda-forge", "--yes"]) == EXIT_OK

    mock_ship.assert_called_once()
    args, kwargs = mock_ship.call_args
    assert args == ("pypi,conda-forge",)
    assert kwargs["confirm"] is True
    assert kwargs["target"] == "library"
    assert kwargs["recipe_path"] is None
    assert kwargs["environ"] is os.environ
    assert kwargs["start_directory"] == Path.cwd()
    out = capsys.readouterr()
    assert out.err == ""
    assert "package ship: ok" in out.out


def test_package_ship_canonical_and_alias_forms_call_package_ship_with_equivalent_kwargs():
    """Task list: 'both dispatch to pyforge.mason.cli.package.ship with
    equivalent kwargs.'"""
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "ship", "--to", "pypi", "--yes"]) == EXIT_OK
    canonical_args = mock_ship.call_args.args
    canonical_kwargs = dict(mock_ship.call_args.kwargs)

    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "--ship", "pypi", "--yes"]) == EXIT_OK
    alias_args = mock_ship.call_args.args
    alias_kwargs = dict(mock_ship.call_args.kwargs)

    assert canonical_args == alias_args
    assert canonical_kwargs.keys() == alias_kwargs.keys()
    for key in canonical_kwargs:
        if key == "environ":
            assert canonical_kwargs[key] is alias_kwargs[key] is os.environ
        else:
            assert canonical_kwargs[key] == alias_kwargs[key]


def test_bare_package_with_no_ship_flag_still_a_usage_error(capsys):
    """D-12/FR-30: `--ship` is the ONE documented bare-noun exception --
    bare `mason package` with no `--ship` given must remain the ordinary
    bare-noun `EXIT_USAGE` (mirrors `test_bare_noun_is_a_usage_error`'s own
    parametrized case for `package`, proven again explicitly here since
    this story adds the ONE carve-out from that rule)."""
    assert main(["package"]) == EXIT_USAGE
    out = capsys.readouterr()
    assert "package" in out.err
    assert out.out == ""


def test_recipe_and_environment_bare_nouns_still_usage_errors_after_ship_lands(capsys):
    """`recipe`/`environment` never registered `--ship` at all -- the
    bare-noun-ship dispatch check's own `ns.noun == "package"` guard means
    they cannot reach it, and `getattr(ns, "ship", None)` would be `None`
    for them regardless."""
    assert main(["recipe"]) == EXIT_USAGE
    assert main(["environment"]) == EXIT_USAGE


def test_package_ship_json_mode_data_targets_is_a_list_of_ship_target_result_dicts(capsys):
    with patch("pyforge.mason.cli.package.ship", return_value=_FIXED_SHIP_RESULTS):
        assert (
            main(
                ["package", "ship", "--to", "pypi,conda-forge", "--yes", "--format", "json"],
            )
            == EXIT_OK
        )
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"schema_version", "command", "status", "data", "errors"}
    assert doc["command"] == "package ship"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"]["targets"] == [json.loads(json.dumps(dataclasses.asdict(r))) for r in _FIXED_SHIP_RESULTS]


def test_package_ship_text_mode_never_leaks_the_raw_shipstate_repr(capsys):
    """**New test (review pass 2)**: `--format text` is the DEFAULT format
    (no `--format` flag given at all here) -- `_FIXED_SHIP_RESULTS` above
    includes a `ShipState.TERMINAL` entry (a non-trivial state, not just
    `PENDING`), so this reproduces the exact defect two independent
    reviewers live-found against `render.render_text`: a bare
    `dataclasses.asdict(r)` per target left `state` as a raw `ShipState`
    enum member one level inside the rendered `"targets"` list, which
    `render_text` printed via that list's own `repr()` (`<ShipState.
    TERMINAL: 'terminal'>`), never `str()`. Asserts the literal substring
    `"ShipState."` never appears anywhere in captured stdout -- not merely
    that the plain value `"terminal"` appears, since a partial/incidental
    match would not by itself rule out the `repr()` leaking alongside it."""
    with patch("pyforge.mason.cli.package.ship", return_value=_FIXED_SHIP_RESULTS):
        assert main(["package", "ship", "--to", "pypi,conda-forge", "--yes"]) == EXIT_OK

    out = capsys.readouterr().out
    assert "ShipState." not in out
    assert "terminal" in out
    assert "pending" in out


def test_package_ship_no_yes_flag_passes_confirm_false():
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "ship", "--to", "pypi"]) == EXIT_OK

    assert mock_ship.call_args.kwargs["confirm"] is False


def test_package_ship_yes_flag_passes_confirm_true():
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "ship", "--to", "pypi", "--yes"]) == EXIT_OK

    assert mock_ship.call_args.kwargs["confirm"] is True


def test_package_ship_recipe_path_flag_forwards_through():
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "ship",
                    "--to",
                    "conda-forge",
                    "--yes",
                    "--recipe-path",
                    "/some/recipe",
                ]
            )
            == EXIT_OK
        )

    assert mock_ship.call_args.kwargs["recipe_path"] == "/some/recipe"


def test_package_ship_invalid_target_choice_is_a_usage_error(capsys):
    """`--target`'s `choices=("library",)` -- mirrors `package build`'s own
    usage-error case."""
    with patch("pyforge.mason.cli.package.ship") as mock_ship:
        rc = main(["package", "ship", "--to", "pypi", "--target", "application"])

    assert rc == EXIT_USAGE
    err = capsys.readouterr().err
    assert "library" in err
    mock_ship.assert_not_called()


def test_package_ship_aggregate_exit_code_is_failed_when_any_target_failed():
    mixed_results = (
        ShipTargetResult(target="pypi", state=ShipState.TERMINAL, reference="u", message="ok"),
        ShipTargetResult(
            target="conda-forge",
            state=ShipState.FAILED,
            reference=None,
            message="bad",
        ),
    )
    with patch("pyforge.mason.cli.package.ship", return_value=mixed_results):
        rc = main(["package", "ship", "--to", "pypi,conda-forge", "--yes"])

    assert rc == EXIT_FAILED


def test_package_ship_aggregate_exit_code_is_ok_when_no_target_failed():
    """`NOT_ATTEMPTED` (a dry run, or a rehearsal-gated skip) and
    `TERMINAL` both count as success (AD-9) -- only `FAILED` flips the
    aggregate."""
    all_ok_results = (
        ShipTargetResult(target="pypi", state=ShipState.TERMINAL, reference="u", message="ok"),
        ShipTargetResult(
            target="pypi",
            state=ShipState.NOT_ATTEMPTED,
            reference=None,
            message="gated",
        ),
    )
    with patch("pyforge.mason.cli.package.ship", return_value=all_ok_results):
        rc = main(["package", "ship", "--to", "pypi,pypi-test", "--yes"])

    assert rc == EXIT_OK


def test_package_ship_cfe_root_and_timeout_flags_reach_package_ship():
    """Unlike `package build`'s established never-reads-cfe-flags
    precedent, `ship` DOES need `--cfe-root`/`--cfe-timeout` for its
    `conda-forge` target."""
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "ship",
                    "--to",
                    "conda-forge",
                    "--yes",
                    "--cfe-root",
                    "/explicit/root",
                    "--cfe-timeout",
                    "30",
                ]
            )
            == EXIT_OK
        )

    kwargs = mock_ship.call_args.kwargs
    assert kwargs["cfe_root_arg"] == "/explicit/root"
    assert kwargs["cfe_timeout_arg"] == 30.0


def test_package_ship_cfe_python_flag_reaches_package_ship():
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "ship",
                    "--to",
                    "conda-forge",
                    "--yes",
                    "--cfe-python",
                    "/explicit/python",
                ]
            )
            == EXIT_OK
        )

    assert mock_ship.call_args.kwargs["cfe_python_arg"] == "/explicit/python"


def test_package_ship_cfe_timeout_defaults_to_none_when_unset(monkeypatch):
    monkeypatch.delenv("MASON_CFE_TIMEOUT", raising=False)
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "ship", "--to", "pypi", "--yes"]) == EXIT_OK

    assert mock_ship.call_args.kwargs["cfe_timeout_arg"] is None


def test_package_ship_mason_error_projects_to_exit_failed(capsys):
    """`InvalidShipTargetError` (an invalid TOKEN, propagated un-caught out
    of `package.ship`) degrades via `main()`'s existing generic `MasonError`
    branch to `EXIT_FAILED` -- no dedicated branch, spec I/O matrix:
    'Invalid token... Raises InvalidShipTargetError, EXIT_FAILED.'"""
    with patch(
        "pyforge.mason.cli.package.ship",
        side_effect=InvalidShipTargetError("bogus"),
    ):
        rc = main(["package", "ship", "--to", "pypi", "--yes"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "bogus" in err


def test_package_ship_global_flag_parses_after_the_verb_and_its_positional():
    ns = build_parser().parse_args(
        ["package", "ship", "--to", "pypi", "--format", "json"],
    )
    assert ns.noun == "package"
    assert ns.verb == "ship"
    assert ns.to == "pypi"
    assert ns.format == "json"


# --- Review pass 1: `--yes`/`--recipe-path`/`--target` given BEFORE the
# verb token must parse identically to giving them after -- the confirmed
# silent-clobber bug (Spec Change Log) this pass fixes with
# `argparse.SUPPRESS` on both of `_add_ship_flags`'s registration sites.


def test_package_ship_yes_before_verb_parses_the_same_as_after_via_parse_args():
    """`mason package --yes ship --to pypi` must set `ns.yes = True` --
    before this pass's fix, the `ship` subparser's own `--yes` (a plain
    `False` default) silently clobbered the noun parser's `True` when
    `_SubParsersAction.__call__` copied its fresh sub-namespace onto the
    parent (Spec Change Log: 'mason package --yes ship --to pypi parses to
    ns.yes == False')."""
    before = build_parser().parse_args(["package", "--yes", "ship", "--to", "pypi"])
    after = build_parser().parse_args(["package", "ship", "--to", "pypi", "--yes"])
    assert getattr(before, "yes", False) is True
    assert getattr(after, "yes", False) is True


def test_package_ship_recipe_path_before_verb_parses_the_same_as_after_via_parse_args():
    before = build_parser().parse_args(
        ["package", "--recipe-path", "X", "ship", "--to", "conda-forge"],
    )
    after = build_parser().parse_args(
        ["package", "ship", "--to", "conda-forge", "--recipe-path", "X"],
    )
    assert getattr(before, "recipe_path", None) == "X"
    assert getattr(after, "recipe_path", None) == "X"


def test_package_ship_target_before_verb_parses_the_same_as_after_via_parse_args():
    before = build_parser().parse_args(
        ["package", "--target", "library", "ship", "--to", "pypi"],
    )
    after = build_parser().parse_args(
        ["package", "ship", "--to", "pypi", "--target", "library"],
    )
    assert getattr(before, "target", "library") == "library"
    assert getattr(after, "target", "library") == "library"


def test_package_ship_yes_before_verb_reaches_package_ship_via_main():
    """Same hazard, proven end-to-end through `main()` + `_dispatch_package_
    ship` rather than just `parse_args` -- `package.ship`'s own `confirm`
    kwarg must be `True` regardless of where `--yes` was typed."""
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "--yes", "ship", "--to", "pypi"]) == EXIT_OK
    before_kwargs = dict(mock_ship.call_args.kwargs)

    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert main(["package", "ship", "--to", "pypi", "--yes"]) == EXIT_OK
    after_kwargs = dict(mock_ship.call_args.kwargs)

    assert before_kwargs["confirm"] is True
    assert after_kwargs["confirm"] is True


def test_package_ship_recipe_path_before_verb_reaches_package_ship_via_main():
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "--recipe-path",
                    "X",
                    "ship",
                    "--to",
                    "conda-forge",
                    "--yes",
                ]
            )
            == EXIT_OK
        )
    before_kwargs = dict(mock_ship.call_args.kwargs)

    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "ship",
                    "--to",
                    "conda-forge",
                    "--yes",
                    "--recipe-path",
                    "X",
                ]
            )
            == EXIT_OK
        )
    after_kwargs = dict(mock_ship.call_args.kwargs)

    assert before_kwargs["recipe_path"] == "X"
    assert after_kwargs["recipe_path"] == "X"


def test_package_ship_target_before_verb_reaches_package_ship_via_main():
    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "--target",
                    "library",
                    "ship",
                    "--to",
                    "pypi",
                    "--yes",
                ]
            )
            == EXIT_OK
        )
    before_kwargs = dict(mock_ship.call_args.kwargs)

    with patch(
        "pyforge.mason.cli.package.ship",
        return_value=_FIXED_SHIP_RESULTS,
    ) as mock_ship:
        assert (
            main(
                [
                    "package",
                    "ship",
                    "--to",
                    "pypi",
                    "--yes",
                    "--target",
                    "library",
                ]
            )
            == EXIT_OK
        )
    after_kwargs = dict(mock_ship.call_args.kwargs)

    assert before_kwargs["target"] == "library"
    assert after_kwargs["target"] == "library"


def test_package_ship_empty_string_alias_reaches_package_ship_not_the_bare_noun_usage_error():
    """Review pass 1: `mason package --ship ""` must reach `package.
    ship("")` (and, for real, fail with that call's own
    `InvalidShipTargetError`) -- NOT silently fall through to the generic
    bare-noun `EXIT_USAGE` branch, which is what the prior truthy
    `getattr(ns, "ship", None)` check did for any falsy-but-given `--ship`
    value."""
    with patch("pyforge.mason.cli.package.ship", return_value=()) as mock_ship:
        rc = main(["package", "--ship", ""])

    mock_ship.assert_called_once()
    args, _kwargs = mock_ship.call_args
    assert args == ("",)
    assert rc == EXIT_OK


@pytest.mark.parametrize(
    "argv",
    [
        ["package", "--ship", "pypi", "build", "."],
        ["package", "--ship", "pypi", "ship", "--to", "conda-forge", "--yes"],
    ],
)
def test_package_ship_combined_with_an_explicit_verb_is_a_usage_error(argv, capsys):
    """Review pass 3: `--ship <targets>` is registered on the `package`
    NOUN parser (needed for D-12's bare-noun alias), so it used to parse
    successfully even alongside an explicit verb -- with `ns.ship` then
    silently discarded (neither the `build` nor the `ship` verb branch ever
    read it). Two independent review passes flagged this as a plausible
    real trigger (editing a previous `--ship ...` invocation to add an
    explicit verb, leaving the stale `--ship` in place); rejected as a
    usage error now instead of silently ignored."""
    with patch("pyforge.mason.cli.package.ship") as mock_ship, patch("pyforge.mason.cli.package.build") as mock_build:
        rc = main(argv)

    assert rc == EXIT_USAGE
    err = capsys.readouterr().err
    assert "--ship" in err
    mock_ship.assert_not_called()
    mock_build.assert_not_called()


# --- Story 4.3: `environment lock` verb dispatch -----------------------------

_FIXED_LOCK_RESULT = LockResult(
    manifest_paths=("environment.yml",),
    output_path="lock.yml",
    platforms=(),
    engine_name="conda-lock",
    engine_version="4.0.2",
    returncode=0,
    stdout="",
)

_FIXED_LOCK_RESULT_WITH_PLATFORMS = LockResult(
    manifest_paths=("environment.yml",),
    output_path="lock.yml",
    platforms=("linux-64", "osx-arm64"),
    engine_name="conda-lock",
    engine_version="4.0.2",
    returncode=0,
    stdout="",
)


def test_environment_lock_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["environment", "lock", "--help"])
    assert exc.value.code == 0
    assert "lock" in capsys.readouterr().out


def test_environment_lock_happy_path_text_mode(capsys):
    with patch(
        "pyforge.mason.cli.environment.lock",
        return_value=_FIXED_LOCK_RESULT,
    ) as mock_lock:
        assert main(["environment", "lock", "environment.yml", "-o", "lock.yml"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    assert "environment lock: ok" in out.out
    assert "engine_name: conda-lock" in out.out

    mock_lock.assert_called_once()
    args, kwargs = mock_lock.call_args
    assert args[0] == ["environment.yml"]
    assert args[1] == "lock.yml"
    assert kwargs["platforms"] is None


def test_environment_lock_happy_path_json_mode(capsys):
    with patch("pyforge.mason.cli.environment.lock", return_value=_FIXED_LOCK_RESULT):
        rc = main(
            ["environment", "lock", "environment.yml", "-o", "lock.yml", "--format", "json"],
        )
    assert rc == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "environment lock"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == _json_roundtripped(_FIXED_LOCK_RESULT)


def test_environment_lock_passes_platform_flag_through_unparsed(capsys):
    with patch(
        "pyforge.mason.cli.environment.lock",
        return_value=_FIXED_LOCK_RESULT,
    ) as mock_lock:
        main(
            ["environment", "lock", "environment.yml", "-o", "lock.yml", "--platform", "linux-64,osx-arm64"],
        )

    assert mock_lock.call_args.kwargs["platforms"] == "linux-64,osx-arm64"


# --- Story 4.2: `environment lock` manifest-discovery dispatch --------------


def test_environment_lock_missing_manifest_path_triggers_discovery(capsys):
    """Omitting `manifest_path` (`nargs="*"`) is no longer a usage error --
    it triggers discovery against `Path.cwd()`, and the discovered tuple
    (not an empty one) is what `environment.lock()` receives."""
    with (
        patch(
            "pyforge.mason.cli.environment.discover_manifests",
            return_value=("environment.yml", "pixi.toml"),
        ) as mock_discover,
        patch(
            "pyforge.mason.cli.environment.lock",
            return_value=_FIXED_LOCK_RESULT,
        ) as mock_lock,
    ):
        rc = main(["environment", "lock", "-o", "lock.yml"])

    assert rc == EXIT_OK
    mock_discover.assert_called_once_with(Path.cwd())

    out = capsys.readouterr()
    assert "discovered manifests: environment.yml, pixi.toml" in out.err
    assert "environment lock: ok" in out.out

    mock_lock.assert_called_once()
    args, _kwargs = mock_lock.call_args
    assert args[0] == ("environment.yml", "pixi.toml")


def test_environment_lock_discovery_line_is_not_gated_by_quiet(capsys):
    """The discovery notice is never gated behind `--verbose`/`--quiet`
    (spec Never boundary) -- confirm `--quiet` still shows it."""
    with (
        patch(
            "pyforge.mason.cli.environment.discover_manifests",
            return_value=("environment.yml", "pixi.toml"),
        ),
        patch("pyforge.mason.cli.environment.lock", return_value=_FIXED_LOCK_RESULT),
    ):
        rc = main(["environment", "lock", "-o", "lock.yml", "--quiet"])

    assert rc == EXIT_OK
    assert "discovered manifests: environment.yml, pixi.toml" in capsys.readouterr().err


def test_environment_lock_missing_manifest_path_discovery_raises(capsys):
    """When discovery itself finds nothing, `EnvironmentManifestsNotFoundError`
    propagates to `main()`'s `except MasonError` handler -- `EXIT_FAILED`, the
    message on stderr, no stderr discovery line (it is printed only AFTER a
    successful discovery call), and no traceback."""
    with (
        patch(
            "pyforge.mason.cli.environment.discover_manifests",
            side_effect=EnvironmentManifestsNotFoundError(
                "/proj",
                ("pyproject.toml", "environment.yml", "requirements*.txt", "pixi.toml"),
            ),
        ) as mock_discover,
        patch("pyforge.mason.cli.environment.lock") as mock_lock,
    ):
        rc = main(["environment", "lock", "-o", "lock.yml"])

    assert rc == EXIT_FAILED
    mock_discover.assert_called_once_with(Path.cwd())
    mock_lock.assert_not_called()

    err = capsys.readouterr().err
    assert "no dependency manifests found" in err
    assert "discovered manifests:" not in err


def test_environment_lock_explicit_manifest_path_bypasses_discovery(capsys):
    """An explicit `manifest_path` never triggers discovery and never prints
    the discovery line -- unchanged from pre-4.2 behavior."""
    with (
        patch("pyforge.mason.cli.environment.discover_manifests") as mock_discover,
        patch(
            "pyforge.mason.cli.environment.lock",
            return_value=_FIXED_LOCK_RESULT,
        ) as mock_lock,
    ):
        rc = main(["environment", "lock", "environment.yml", "-o", "lock.yml"])

    assert rc == EXIT_OK
    mock_discover.assert_not_called()
    assert "discovered manifests:" not in capsys.readouterr().err
    mock_lock.assert_called_once()
    args, _kwargs = mock_lock.call_args
    assert args[0] == ["environment.yml"]


def test_environment_lock_renders_populated_platforms(capsys):
    with patch(
        "pyforge.mason.cli.environment.lock",
        return_value=_FIXED_LOCK_RESULT_WITH_PLATFORMS,
    ):
        rc = main(
            ["environment", "lock", "environment.yml", "-o", "lock.yml", "--format", "json"],
        )
    assert rc == EXIT_OK

    doc = json.loads(capsys.readouterr().out)
    assert doc["data"] == _json_roundtripped(_FIXED_LOCK_RESULT_WITH_PLATFORMS)
    assert doc["data"]["platforms"] == ["linux-64", "osx-arm64"]


def test_environment_lock_missing_output_is_a_usage_error(capsys):
    with patch("pyforge.mason.cli.environment.lock") as mock_lock:
        rc = main(["environment", "lock", "environment.yml"])

    assert rc == EXIT_USAGE
    err = capsys.readouterr().err
    assert "--output" in err
    mock_lock.assert_not_called()


def test_environment_lock_failed_child_still_renders_ok(capsys):
    """A non-zero delegated engine returncode is DATA, never raised (AD-4)
    -- mirrors `package build`'s own established "the gap is data"
    precedent."""
    failed_result = LockResult(
        manifest_paths=("environment.yml",),
        output_path="lock.yml",
        platforms=(),
        engine_name="conda-lock",
        engine_version="4.0.2",
        returncode=1,
        stdout="conflict: could not solve\n",
    )
    with patch("pyforge.mason.cli.environment.lock", return_value=failed_result):
        assert main(["environment", "lock", "environment.yml", "-o", "lock.yml"]) == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    assert "environment lock: ok" in out.out
    assert "returncode: 1" in out.out
    assert "conflict: could not solve" in out.out


def test_environment_lock_engine_absent_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.environment.lock",
        side_effect=EngineAbsentError(name="conda-lock", conda_package="conda-lock"),
    ):
        rc = main(["environment", "lock", "environment.yml", "-o", "lock.yml"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "conda-lock" in err


def test_environment_lock_timeout_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.environment.lock",
        side_effect=EnvironmentLockTimeoutError(timeout=600.0),
    ):
        rc = main(["environment", "lock", "environment.yml", "-o", "lock.yml"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "600" in err


# --- Story 4.4: `environment check` verb dispatch -----------------------------

_FIXED_CHECK_RESULT_CURRENT = CheckResult(
    lockfile_path="lock.yml",
    manifest_paths=("environment.yml",),
    platforms=(),
    stale=False,
    engine_name="conda-lock",
    engine_version="4.0.2",
    returncode=0,
    stdout="",
)

_FIXED_CHECK_RESULT_STALE = CheckResult(
    lockfile_path="lock.yml",
    manifest_paths=("environment.yml",),
    platforms=(),
    stale=True,
    engine_name="conda-lock",
    engine_version="4.0.2",
    returncode=0,
    stdout="",
)

_FIXED_CHECK_RESULT_WITH_PLATFORMS = CheckResult(
    lockfile_path="lock.yml",
    manifest_paths=("environment.yml",),
    platforms=("linux-64", "osx-arm64"),
    stale=False,
    engine_name="conda-lock",
    engine_version="4.0.2",
    returncode=0,
    stdout="",
)


def test_environment_check_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["environment", "check", "--help"])
    assert exc.value.code == 0
    assert "check" in capsys.readouterr().out


def test_environment_check_happy_path_current_text_mode_returns_exit_ok(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=_FIXED_CHECK_RESULT_CURRENT,
    ) as mock_check:
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_OK
    out = capsys.readouterr()
    assert out.err == ""
    assert "environment check: ok" in out.out
    assert "stale: False" in out.out

    mock_check.assert_called_once()
    args, kwargs = mock_check.call_args
    assert args[0] == "lock.yml"
    assert args[1] == ["environment.yml"]
    assert kwargs["platforms"] is None


def test_environment_check_happy_path_current_json_mode(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=_FIXED_CHECK_RESULT_CURRENT,
    ):
        rc = main(
            ["environment", "check", "environment.yml", "-l", "lock.yml", "--format", "json"],
        )
    assert rc == EXIT_OK

    out = capsys.readouterr()
    assert out.err == ""
    doc = json.loads(out.out)
    assert doc["command"] == "environment check"
    assert doc["status"] == "ok"
    assert doc["errors"] == []
    assert doc["data"] == _json_roundtripped(_FIXED_CHECK_RESULT_CURRENT)


def test_environment_check_stale_result_returns_exit_failed_text_mode(capsys):
    """A stale verdict is DATA, never raised (AD-4) -- the process exit code
    projects it (spec Intent, mirrors `recipe validate`'s own pass/fail ->
    exit code precedent), but the JSON envelope's own `status` stays "ok"."""
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=_FIXED_CHECK_RESULT_STALE,
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    out = capsys.readouterr()
    assert out.err == ""
    assert "environment check: ok" in out.out
    assert "stale: True" in out.out


def test_environment_check_stale_result_returns_exit_failed_json_mode(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=_FIXED_CHECK_RESULT_STALE,
    ):
        rc = main(
            ["environment", "check", "environment.yml", "-l", "lock.yml", "--format", "json"],
        )

    assert rc == EXIT_FAILED
    doc = json.loads(capsys.readouterr().out)
    assert doc["status"] == "ok"
    assert doc["data"]["stale"] is True


def test_environment_check_passes_platform_flag_through_unparsed(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=_FIXED_CHECK_RESULT_CURRENT,
    ) as mock_check:
        main(
            ["environment", "check", "environment.yml", "-l", "lock.yml", "--platform", "linux-64,osx-arm64"],
        )

    assert mock_check.call_args.kwargs["platforms"] == "linux-64,osx-arm64"


def test_environment_check_renders_populated_platforms(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=_FIXED_CHECK_RESULT_WITH_PLATFORMS,
    ):
        rc = main(
            ["environment", "check", "environment.yml", "-l", "lock.yml", "--format", "json"],
        )
    assert rc == EXIT_OK

    doc = json.loads(capsys.readouterr().out)
    assert doc["data"] == _json_roundtripped(_FIXED_CHECK_RESULT_WITH_PLATFORMS)
    assert doc["data"]["platforms"] == ["linux-64", "osx-arm64"]


# --- Story 4.2: `environment check` manifest-discovery dispatch -------------


def test_environment_check_missing_manifest_path_triggers_discovery(capsys):
    """Omitting `manifest_path` (`nargs="*"`) is no longer a usage error --
    it triggers discovery against `Path.cwd()`, and the discovered tuple
    (not an empty one) is what `environment.check()` receives."""
    with (
        patch(
            "pyforge.mason.cli.environment.discover_manifests",
            return_value=("environment.yml", "pixi.toml"),
        ) as mock_discover,
        patch(
            "pyforge.mason.cli.environment.check",
            return_value=_FIXED_CHECK_RESULT_CURRENT,
        ) as mock_check,
    ):
        rc = main(["environment", "check", "-l", "lock.yml"])

    assert rc == EXIT_OK
    mock_discover.assert_called_once_with(Path.cwd())

    out = capsys.readouterr()
    assert "discovered manifests: environment.yml, pixi.toml" in out.err
    assert "environment check: ok" in out.out

    mock_check.assert_called_once()
    args, _kwargs = mock_check.call_args
    assert args[1] == ("environment.yml", "pixi.toml")


def test_environment_check_missing_manifest_path_discovery_raises(capsys):
    """When discovery itself finds nothing, `EnvironmentManifestsNotFoundError`
    propagates to `main()`'s `except MasonError` handler -- `EXIT_FAILED`, the
    message on stderr, no stderr discovery line, and no traceback."""
    with (
        patch(
            "pyforge.mason.cli.environment.discover_manifests",
            side_effect=EnvironmentManifestsNotFoundError(
                "/proj",
                ("pyproject.toml", "environment.yml", "requirements*.txt", "pixi.toml"),
            ),
        ) as mock_discover,
        patch("pyforge.mason.cli.environment.check") as mock_check,
    ):
        rc = main(["environment", "check", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    mock_discover.assert_called_once_with(Path.cwd())
    mock_check.assert_not_called()

    err = capsys.readouterr().err
    assert "no dependency manifests found" in err
    assert "discovered manifests:" not in err


def test_environment_check_explicit_manifest_path_bypasses_discovery(capsys):
    """An explicit `manifest_path` never triggers discovery and never prints
    the discovery line -- unchanged from pre-4.2 behavior."""
    with (
        patch("pyforge.mason.cli.environment.discover_manifests") as mock_discover,
        patch(
            "pyforge.mason.cli.environment.check",
            return_value=_FIXED_CHECK_RESULT_CURRENT,
        ) as mock_check,
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_OK
    mock_discover.assert_not_called()
    assert "discovered manifests:" not in capsys.readouterr().err
    mock_check.assert_called_once()
    args, _kwargs = mock_check.call_args
    assert args[1] == ["environment.yml"]


def test_environment_check_missing_lockfile_flag_is_a_usage_error(capsys):
    with patch("pyforge.mason.cli.environment.check") as mock_check:
        rc = main(["environment", "check", "environment.yml"])

    assert rc == EXIT_USAGE
    err = capsys.readouterr().err
    assert "--lockfile" in err
    mock_check.assert_not_called()


def test_environment_check_lockfile_missing_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        side_effect=EnvironmentLockfileMissingError("lock.yml"),
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "lock.yml" in err


def test_environment_check_engine_absent_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        side_effect=EngineAbsentError(name="conda-lock", conda_package="conda-lock"),
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "conda-lock" in err


def test_environment_check_timeout_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        side_effect=EnvironmentCheckTimeoutError(timeout=600.0),
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "600" in err


def test_environment_check_lockfile_malformed_error_projects_to_exit_failed(capsys):
    with patch(
        "pyforge.mason.cli.environment.check",
        side_effect=EnvironmentLockfileMalformedError("lock.yml", "'metadata'"),
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "lock.yml" in err


def test_environment_check_nonzero_returncode_projects_to_exit_failed_even_when_not_stale(
    capsys,
):
    """Review pass, 2026-08-15: a genuine `conda-lock` failure (bad
    manifest, solver crash, network error) that leaves the temp copy
    unrewritten reports `stale=False` (the before/after hash comparison
    trivially holds) -- `cli.py`'s dispatch must still fail the process on a
    non-zero `returncode`, or a CI gate would silently green-light on its
    own internal failure."""
    failed_but_not_stale = CheckResult(
        lockfile_path="lock.yml",
        manifest_paths=("environment.yml",),
        platforms=(),
        stale=False,
        engine_name="conda-lock",
        engine_version="4.0.2",
        returncode=1,
        stdout="solver crashed\n",
    )
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=failed_but_not_stale,
    ):
        rc = main(["environment", "check", "environment.yml", "-l", "lock.yml"])

    assert rc == EXIT_FAILED
    out = capsys.readouterr()
    assert out.err == ""
    # The JSON envelope's own status still stays "ok" (spec I/O matrix) --
    # only the process exit code reflects the failure.
    assert "environment check: ok" in out.out
    assert "returncode: 1" in out.out


def test_environment_check_stale_and_nonzero_returncode_together_still_exit_failed(
    capsys,
):
    """Repair pass, 2026-08-15 (S-13.7 verification repair): the two prior
    `returncode`-aware tests each cover one signal in isolation (stale alone,
    or a failed check alone) -- neither exercises them together, e.g. a
    child that partially rewrites the temp copy's hash before crashing.
    `cli.py`'s `not result.stale and result.returncode == 0` dispatch
    condition already handles this by inspection; this pins it."""
    stale_and_failed = CheckResult(
        lockfile_path="lock.yml",
        manifest_paths=("environment.yml",),
        platforms=(),
        stale=True,
        engine_name="conda-lock",
        engine_version="4.0.2",
        returncode=1,
        stdout="solver crashed\n",
    )
    with patch(
        "pyforge.mason.cli.environment.check",
        return_value=stale_and_failed,
    ):
        rc = main(
            ["environment", "check", "environment.yml", "-l", "lock.yml", "--format", "json"],
        )

    assert rc == EXIT_FAILED
    doc = json.loads(capsys.readouterr().out)
    assert doc["data"]["stale"] is True
    assert doc["data"]["returncode"] == 1
