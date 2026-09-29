"""Unit tests for ``pyforge.doctor.__main__``'s ``check`` subcommand (Story
1.5, FR-9/NFR-4) -- covers every row of the story spec's I/O & Edge-Case
Matrix: default combined run, ``--engines``/``--env`` filtering (including
the unknown-name usage error and the degraded-vs-clean asymmetry between
the two categories), ``--list``, ``--json`` (schema-valid via
``jsonschema``, no ``prescriptions`` key), ``--version``/``--help`` parity
with ``pyforge-warden``'s ``scan`` subcommand, and ``path`` positional
forwarding. Mirrors ``test_checks_registry.py``'s
monkeypatch-``run_doctor_checks`` idiom for simulating a healthy/degraded
"engines" category without depending on a real warden self-check.
"""

from __future__ import annotations

import json
import shlex
from importlib import resources
from pathlib import Path

import jsonschema
from pyforge.warden import engines as engines_mod
from pyforge.warden.engines import DoctorCheck

from pyforge.doctor.__main__ import __version__, main
from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.checks.env_hygiene import (
    CHECK_NAME as ENV_CHECK_NAME,
)
from pyforge.doctor.checks.env_hygiene import (
    SCAN_INCOMPLETE_CHECK_NAME,
)
from pyforge.doctor.models import DoctorStatus, Finding, Source

_HEALTHY_ENGINE_CHECKS = (
    ("deptry", True, "within tested range"),
    ("osv-scanner", True, "within tested range"),
    ("osv-db", True, "snapshot fresh"),
    ("kev-feed", True, "operating air-gapped"),
    ("epss-feed", True, "operating air-gapped"),
    ("endoflife-feed", True, "operating air-gapped"),
)


def _schema() -> dict:
    schema_text = resources.files("pyforge.doctor").joinpath("data", "report-schema.json").read_text(encoding="utf-8")
    return json.loads(schema_text)


def _stub_healthy_warden(monkeypatch) -> None:
    checks = tuple(DoctorCheck(name=n, ok=ok, message=m) for n, ok, m in _HEALTHY_ENGINE_CHECKS)
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: checks)


def _stub_degraded_warden(monkeypatch) -> None:
    def _boom(target):
        raise RuntimeError("simulated warden self-check crash")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)


class _ForbiddenGatherError(BaseException):
    """Deliberately a ``BaseException``, NOT ``Exception`` (review finding):
    ``sources.warden.gather``'s own ``except Exception`` degrade-never-crash
    net swallows an ordinary ``AssertionError`` into a FAIL Finding, silently
    defusing this sentinel -- a regression that gathered would have passed
    these tests via their secondary assertions alone. ``gather`` deliberately
    lets ``BaseException`` through, and ``main()``'s handlers catch only
    ``SystemExit``/``KeyboardInterrupt``/``Exception``, so a forbidden gather
    now propagates all the way out and fails the test loudly."""


def _forbid_warden_gather(monkeypatch) -> None:
    def _boom(target):
        raise _ForbiddenGatherError("must never gather/run the 'engines' category here")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)


# --- default combined run (epics AC1) ----------------------------------------


def test_default_combined_run_reports_both_categories_and_projects_exit(monkeypatch, tmp_path: Path, capsys):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "deptry" in captured.out
    assert "warden-doctor" in captured.out
    assert "finding(s)" in captured.out


# --- durability category (Story 5.2, FR-14/AD-11) ----------------------------


def test_durability_findings_reach_both_renders(monkeypatch, tmp_path: Path, capsys):
    """Story 5.1 shipped ``sources/marshal.py`` with NO caller. This is the
    caller, so the source's findings must appear in the human render AND in
    ``--json`` -- FR-9's parity guarantee, which no test could assert while
    nothing rendered the source at all."""
    monkeypatch.setattr(
        "pyforge.doctor.__main__.marshal_source.gather",
        lambda target: (
            Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-regression",
                status=DoctorStatus.OK,
                message="8 tracked ledger(s) hold",
                evidence={"ledgers": 8},
            ),
        ),
    )

    assert main(["check", str(tmp_path), "--durability"]) == 0
    assert "marshal-durability" in capsys.readouterr().out

    assert main(["check", str(tmp_path), "--durability", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [f["source"] for f in doc["findings"]] == ["marshal-durability"]


def test_durability_fail_drives_the_exit_code_lattice(monkeypatch, tmp_path: Path, capsys):
    """A FAIL here is not cosmetic: it must gate exactly like any other
    source's FAIL (epics AC2)."""
    monkeypatch.setattr(
        "pyforge.doctor.__main__.marshal_source.gather",
        lambda target: (
            Finding(
                source=Source.MARSHAL_DURABILITY,
                check="ledger-regression",
                status=DoctorStatus.FAIL,
                message="2 ledger(s) un-finished 55",
                evidence={"total": 55},
            ),
        ),
    )

    assert main(["check", str(tmp_path), "--durability"]) == 2
    assert "fail" in capsys.readouterr().out


def test_default_run_includes_durability_but_a_narrowing_flag_excludes_it(monkeypatch, tmp_path: Path, capsys):
    """No flags -> all three categories. An explicit ``--env`` narrows to env
    alone, so durability must NOT run -- the same "explicit flags narrow"
    semantics ``--engines``/``--env`` already had, extended to a third
    category rather than special-cased."""
    _stub_healthy_warden(monkeypatch)
    calls: list[Path] = []
    monkeypatch.setattr(
        "pyforge.doctor.__main__.marshal_source.gather",
        lambda target: calls.append(target) or (),
    )

    main(["check", str(tmp_path)])
    assert len(calls) == 1, "default run must include the durability category"

    main(["check", str(tmp_path), "--env"])
    assert len(calls) == 1, "--env must narrow to env alone, not also run durability"


# --- bmad-core category (Story 10.3, Epic 10/CAP-3) ---------------------------


def test_bmad_core_findings_reach_both_renders(monkeypatch, tmp_path: Path, capsys):
    """Story 10.1/10.2 shipped ``sources/bmad_method.py`` with no caller.
    This is the caller, so its findings must appear in the human render AND
    in ``--json`` -- FR-9's parity guarantee.

    A lone ``--bmad-core`` narrows to bmad-core ALONE, same "explicit flags
    narrow" semantics ``--engines``/``--env``/``--durability`` already have
    amongst each other -- a forbidden-warden sentinel (instead of a
    healthy-warden stub) proves engines/env/durability never run
    alongside it."""
    _forbid_warden_gather(monkeypatch)
    monkeypatch.setattr(
        "pyforge.doctor.__main__.bmad_method.gather",
        lambda target: (
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-method-version-drift",
                status=DoctorStatus.WARN,
                message="installed bmad-method 6.9.0 is behind pixi.toml's declared floor >=6.11.0",
                evidence={"installed": "6.9.0", "declared_floor": ">=6.11.0"},
            ),
        ),
    )

    assert main(["check", str(tmp_path), "--bmad-core"]) == 0
    assert "bmad-method-version-drift" in capsys.readouterr().out

    assert main(["check", str(tmp_path), "--bmad-core", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [f["source"] for f in doc["findings"]] == ["bmad-method-version-drift"]
    assert doc["findings"][0]["status"] == "warn"


def test_bmad_core_warn_never_drives_the_exit_code(monkeypatch, tmp_path: Path, capsys):
    """This source never emits FAIL (its own module docstring: always OK or
    WARN) -- confirm a WARN finding leaves the exit code at 0, unlike
    durability's FAIL-gates test above. Forbidden-warden sentinel keeps this
    isolated to bmad-core alone (narrows same as the test above)."""
    _forbid_warden_gather(monkeypatch)
    monkeypatch.setattr(
        "pyforge.doctor.__main__.bmad_method.gather",
        lambda target: (
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-method-version-drift",
                status=DoctorStatus.WARN,
                message="drift",
                evidence={},
            ),
        ),
    )

    assert main(["check", str(tmp_path), "--bmad-core"]) == 0
    assert "warn" in capsys.readouterr().out


def test_default_run_never_calls_bmad_core_gather(monkeypatch, tmp_path: Path, capsys):
    """Inverse of ``test_default_run_includes_durability_but_a_narrowing_
    flag_excludes_it``: unlike durability, ``--bmad-core`` must NEVER join
    the zero-flag default run (NFR-4 -- its upstream half makes a real,
    un-mockable npm HTTP call). A forbidden-gather sentinel proves the
    default run never even calls it."""
    _stub_healthy_warden(monkeypatch)

    def _forbid_bmad_core(target):
        raise _ForbiddenGatherError("must never gather the 'bmad-core' category in the default run")

    monkeypatch.setattr("pyforge.doctor.__main__.bmad_method.gather", _forbid_bmad_core)

    exit_code = main(["check", str(tmp_path)])

    assert exit_code == 0
    assert "bmad-method" not in capsys.readouterr().out


def test_explicit_bmad_core_flag_excludes_the_default_trio(monkeypatch, tmp_path: Path, capsys):
    """The other direction of the two tests above, mirroring
    ``test_default_run_includes_durability_but_a_narrowing_flag_excludes_it``
    exactly: an explicit ``--bmad-core`` must narrow away engines/env/
    durability, not merely be excluded FROM them (the earlier bug this
    story's own review pass caught -- ``run_bmad_core`` has to also count
    as an "explicit flag given" for the default-trio trigger condition,
    not just be omitted from what that branch sets)."""
    _forbid_warden_gather(monkeypatch)

    def _forbid_env(target):
        raise _ForbiddenGatherError("must never gather the 'env' category here")

    def _forbid_durability(target):
        raise _ForbiddenGatherError("must never gather the 'durability' category here")

    monkeypatch.setattr(env_hygiene, "gather", _forbid_env)
    monkeypatch.setattr("pyforge.doctor.__main__.marshal_source.gather", _forbid_durability)
    monkeypatch.setattr(
        "pyforge.doctor.__main__.bmad_method.gather",
        lambda target: (
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-method-version-drift",
                status=DoctorStatus.OK,
                message="meets floor",
                evidence={},
            ),
        ),
    )

    exit_code = main(["check", str(tmp_path), "--bmad-core", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert [f["source"] for f in document["findings"]] == ["bmad-method-version-drift"]


def test_explicit_bmad_core_flag_excluded_by_scope_is_a_usage_error(tmp_path: Path, capsys):
    exit_code = main(["check", str(tmp_path), "--bmad-core", "--scope", "runtime"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--bmad-core" in captured.err


def test_bmad_core_flag_matching_scope_repo_runs_fine(monkeypatch, tmp_path: Path, capsys):
    _forbid_warden_gather(monkeypatch)
    monkeypatch.setattr(
        "pyforge.doctor.__main__.bmad_method.gather",
        lambda target: (
            Finding(
                source=Source.BMAD_METHOD_VERSION_DRIFT,
                check="bmad-method-version-drift",
                status=DoctorStatus.OK,
                message="meets floor",
                evidence={},
            ),
        ),
    )

    exit_code = main(["check", str(tmp_path), "--bmad-core", "--scope", "repo", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert [f["source"] for f in document["findings"]] == ["bmad-method-version-drift"]


# --- sibling-dreams category (Story 16.1 / CAP-1) -----------------------------


def test_sibling_dreams_findings_reach_both_renders(monkeypatch, tmp_path: Path, capsys):
    _forbid_warden_gather(monkeypatch)
    monkeypatch.setattr(
        "pyforge.doctor.__main__.sibling_dreams.gather",
        lambda target: (
            Finding(
                source=Source.SIBLING_DREAMS_DRIFT,
                check="sibling-dreams-drift",
                status=DoctorStatus.WARN,
                message="sibling dream 'X' diverges on owner",
                evidence={"title": "X", "axes": ["owner"]},
            ),
        ),
    )

    assert main(["check", str(tmp_path), "--sibling-dreams"]) == 0
    assert "sibling-dreams-drift" in capsys.readouterr().out

    assert main(["check", str(tmp_path), "--sibling-dreams", "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [f["source"] for f in doc["findings"]] == ["sibling-dreams-drift"]


def test_default_run_never_calls_sibling_dreams_gather(monkeypatch, tmp_path: Path, capsys):
    _stub_healthy_warden(monkeypatch)

    def _forbid(target):
        raise _ForbiddenGatherError("must never gather sibling-dreams in the default run")

    monkeypatch.setattr("pyforge.doctor.__main__.sibling_dreams.gather", _forbid)
    assert main(["check", str(tmp_path)]) == 0
    assert "sibling-dreams" not in capsys.readouterr().out


def test_explicit_sibling_dreams_flag_excludes_the_default_trio(monkeypatch, tmp_path: Path, capsys):
    _forbid_warden_gather(monkeypatch)

    def _forbid_env(target):
        raise _ForbiddenGatherError("must never gather env here")

    def _forbid_durability(target):
        raise _ForbiddenGatherError("must never gather durability here")

    monkeypatch.setattr(env_hygiene, "gather", _forbid_env)
    monkeypatch.setattr("pyforge.doctor.__main__.marshal_source.gather", _forbid_durability)
    monkeypatch.setattr(
        "pyforge.doctor.__main__.sibling_dreams.gather",
        lambda target: (
            Finding(
                source=Source.SIBLING_DREAMS_DRIFT,
                check="sibling-dreams-drift",
                status=DoctorStatus.OK,
                message="quiet",
                evidence={},
            ),
        ),
    )

    exit_code = main(["check", str(tmp_path), "--sibling-dreams", "--json"])
    document = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert [f["source"] for f in document["findings"]] == ["sibling-dreams-drift"]


# --- --json parity (epics AC2) -----------------------------------------------


def test_json_emits_one_schema_valid_document_with_no_prescriptions(monkeypatch, tmp_path: Path, capsys):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 0
    assert document["verb"] == "check"
    assert document["schema_version"] == 1
    assert "prescriptions" not in document
    check_names = {finding["check"] for finding in document["findings"]}
    assert "deptry" in check_names


# --- --engines <name> single check (Story 1.3 AC3, reused) -------------------


def test_engines_named_check_matches_full_suite_filtered_to_that_finding(monkeypatch, tmp_path: Path, capsys):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "osv-scanner", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert len(document["findings"]) == 1
    assert document["findings"][0]["check"] == "osv-scanner"
    assert document["findings"][0]["source"] == "warden-doctor"


def test_unknown_engines_check_name_is_usage_error_never_reaches_gather(monkeypatch, tmp_path: Path, capsys):
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "bogus-name"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "bogus-name" in captured.err
    assert captured.out == ""


def test_degraded_engines_category_named_check_renders_one_synthetic_fail(monkeypatch, tmp_path: Path, capsys):
    _stub_degraded_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "osv-scanner", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 2
    assert len(document["findings"]) == 1
    finding = document["findings"][0]
    assert finding["check"] == "osv-scanner"
    assert finding["status"] == "fail"
    assert finding["source"] == "warden-doctor"
    # Never a bare "not found" -- names the degradation and hints a re-run.
    assert "degrad" in finding["message"].lower()
    assert "not found" not in finding["message"].lower()


def test_degraded_whole_engines_category_emits_schema_valid_sentinel_json(monkeypatch, tmp_path: Path, capsys):
    # Review finding: the WHOLE-category degradation shape -- the sentinel
    # `check == "pyforge-warden"` Finding flowing through _emit_json's
    # schema self-validation and exit_code_for -> 2 -- is exactly what an
    # automated --json consumer (Marshal) sees when warden breaks, and it
    # was untested at the CLI layer.
    _stub_degraded_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 2
    assert [f["check"] for f in document["findings"]] == ["pyforge-warden"]
    assert document["findings"][0]["status"] == "fail"


# --- --env <name>: clean vs. a real match (the category asymmetry) ----------


def test_clean_env_named_check_reports_zero_findings_and_exits_zero(tmp_path: Path, capsys):
    (tmp_path / "benign.py").write_text("x = 1\n", encoding="utf-8")

    exit_code = main(["check", str(tmp_path), "--env", ENV_CHECK_NAME, "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert document["findings"] == []


def test_env_named_check_with_a_real_match_forwards_the_path(tmp_path: Path, capsys):
    (tmp_path / "leaky.py").write_text(
        'import os\n\ndef handler():\n    headers["X"] = os.environ.get("SECRET")\n',
        encoding="utf-8",
    )

    exit_code = main(["check", str(tmp_path), "--env", ENV_CHECK_NAME, "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    # env-hygiene findings are WARN-only in v1 -- never gate the exit code.
    assert exit_code == 0
    assert len(document["findings"]) == 1
    finding = document["findings"][0]
    assert finding["check"] == ENV_CHECK_NAME
    assert finding["status"] == "warn"
    assert str(tmp_path) in finding["message"]


def test_env_incomplete_scan_sentinel_flows_through_check_json(monkeypatch, tmp_path: Path, capsys):
    # Review finding: the env category's OTHER degradation shape -- the
    # SCAN_INCOMPLETE sentinel (WARN, exit stays 0: a pre-flight "green"
    # on an incomplete scan) -- was untested at the CLI layer. Trigger
    # idiom mirrors test_checks_env_hygiene.py: shrink the discovery
    # entry cap below the tree size.
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 1)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")

    exit_code = main(["check", str(tmp_path), "--env", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 0
    statuses = {f["check"]: f["status"] for f in document["findings"]}
    assert statuses[SCAN_INCOMPLETE_CHECK_NAME] == "warn"


def test_unknown_env_check_name_is_usage_error(tmp_path: Path, capsys):
    exit_code = main(["check", str(tmp_path), "--env", "bogus-env-check"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "bogus-env-check" in captured.err


def test_unknown_check_name_that_is_also_a_real_path_hints_at_ordering(monkeypatch, tmp_path: Path, capsys):
    # Review finding: --engines/--env's nargs="?" is structurally ambiguous
    # with an adjacent bare positional `path` -- `--engines <real-path>`
    # parses the path as the check NAME. The error must name this specific,
    # discoverable cause rather than a bare "unknown check name".
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--engines", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "looks like a path" in captured.err
    assert "doctor check" in captured.err


def test_empty_check_name_is_usage_error_without_the_path_hint(monkeypatch, capsys):
    # Review finding: `--engines=` yields the empty string, and Path("")
    # normalizes to Path(".") which exists -- without the truthiness guard
    # the error asserted '' "looks like a path" and suggested the nonsense
    # command `doctor check  --engines`.
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--engines="])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "unknown check name" in captured.err
    assert "looks like a path" not in captured.err


def test_path_hint_shell_quotes_a_path_containing_whitespace(monkeypatch, tmp_path: Path, capsys):
    # Review finding: the suggested corrective command interpolated the
    # rejected value raw -- copy-pasting it with an embedded space (or
    # newline) split the arguments. shlex.quote keeps it one shell token.
    _forbid_warden_gather(monkeypatch)
    weird = tmp_path / "my dir"
    weird.mkdir()

    exit_code = main(["check", "--engines", str(weird)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "looks like a path" in captured.err
    assert shlex.quote(str(weird)) in captured.err


# --- --scope (Story 6.3) -----------------------------------------------------


def test_scope_repo_matches_the_default_all_scope_run(monkeypatch, tmp_path: Path, capsys):
    # All 9 registered sources are scope="repo" today (story spec's I/O
    # matrix row 2) -- `--scope repo` must therefore run all three
    # categories exactly like omitting `--scope` entirely.
    _stub_healthy_warden(monkeypatch)
    calls: list[str] = []
    monkeypatch.setattr(env_hygiene, "gather", lambda target: calls.append("env") or ())
    monkeypatch.setattr(
        "pyforge.doctor.__main__.marshal_source.gather",
        lambda target: calls.append("durability") or (),
    )

    exit_code = main(["check", str(tmp_path), "--scope", "repo"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "warden-doctor" in captured.out
    assert calls == ["env", "durability"], (
        "--scope repo must run env and durability too -- both are registered scope='repo', same as engines"
    )


def test_scope_runtime_yields_zero_findings_and_never_gathers_any_category(monkeypatch, tmp_path: Path, capsys):
    # All 9 registered sources are scope="repo" today -- `--scope runtime`
    # must therefore exclude all three `check` categories entirely (story
    # spec's I/O matrix row 3 + acceptance criteria).
    _forbid_warden_gather(monkeypatch)

    def _forbid_env(target):
        raise _ForbiddenGatherError("must never gather the 'env' category here")

    def _forbid_durability(target):
        raise _ForbiddenGatherError("must never gather the 'durability' category here")

    monkeypatch.setattr(env_hygiene, "gather", _forbid_env)
    monkeypatch.setattr("pyforge.doctor.__main__.marshal_source.gather", _forbid_durability)

    exit_code = main(["check", str(tmp_path), "--scope", "runtime", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.validate(document, _schema())
    assert exit_code == 0
    assert document["findings"] == []


def test_scope_runtime_zero_findings_renders_as_text_too(monkeypatch, tmp_path: Path, capsys):
    # Review finding: the --json render of this scenario was covered above,
    # but _emit_text's own zero-finding header path was never exercised for
    # --scope -- FR-9 parity means both renders must agree, and only testing
    # one leaves the other's behavior unverified.
    _forbid_warden_gather(monkeypatch)
    monkeypatch.setattr(
        env_hygiene,
        "gather",
        lambda target: (_ for _ in ()).throw(_ForbiddenGatherError("must never gather the 'env' category here")),
    )
    monkeypatch.setattr(
        "pyforge.doctor.__main__.marshal_source.gather",
        lambda target: (_ for _ in ()).throw(_ForbiddenGatherError("must never gather the 'durability' category here")),
    )

    exit_code = main(["check", str(tmp_path), "--scope", "runtime"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "0 finding(s)" in captured.out


# --- --scope contradicting an explicit category (Story 6.3 review finding) --


def test_explicit_engines_flag_excluded_by_scope_is_a_usage_error(tmp_path: Path, capsys):
    # Review finding: `--engines` (scope="repo") together with `--scope
    # runtime` used to silently narrow to zero findings/exit 0 -- byte-for-
    # byte indistinguishable from "ran clean" for an automated --json
    # consumer. An explicitly-named category now surfaces the contradiction
    # as a usage error instead.
    exit_code = main(["check", str(tmp_path), "--engines", "--scope", "runtime"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--engines" in captured.err
    assert "--scope" in captured.err
    assert captured.out == ""


def test_explicit_durability_flag_excluded_by_scope_is_a_usage_error(tmp_path: Path, capsys):
    exit_code = main(["check", str(tmp_path), "--durability", "--scope", "runtime"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--durability" in captured.err


def test_explicit_flag_matching_scope_is_not_an_error(monkeypatch, tmp_path: Path, capsys):
    _stub_healthy_warden(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--engines", "--scope", "repo", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert document["findings"]


def test_implicit_default_run_with_scope_runtime_is_not_a_usage_error(tmp_path: Path, capsys):
    # The DEFAULT run (no category flag given) is the documented CI-
    # selection path (story spec's I/O matrix row 3) -- --scope narrowing it
    # to zero categories is intentional, never a usage error, unlike an
    # EXPLICIT category flag contradicting --scope above.
    exit_code = main(["check", str(tmp_path), "--scope", "runtime", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert document["findings"] == []


def test_unknown_scope_value_is_a_usage_error(capsys):
    exit_code = main(["check", "--scope", "bogus"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "bogus" in captured.err
    assert captured.out == ""


def test_list_with_scope_runtime_still_prints_the_full_catalog(monkeypatch, capsys):
    # --list wins over --scope too, per its own "ignores ... --scope" help
    # text -- never a narrowed or empty catalog.
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--list", "--scope", "runtime"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "osv-scanner" in captured.out
    assert "deptry" in captured.out
    assert ENV_CHECK_NAME in captured.out


# --- --list --------------------------------------------------------------


def test_list_prints_full_catalog_and_exits_zero_without_gathering(monkeypatch, capsys):
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "osv-scanner" in captured.out
    assert "deptry" in captured.out
    assert ENV_CHECK_NAME in captured.out


def test_list_ignores_engines_and_env_and_json_flags(monkeypatch, capsys):
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", "--list", "--engines", "--env", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    # Plain text catalog, never a JSON document, regardless of --json.
    assert "osv-scanner" in captured.out
    assert not captured.out.lstrip().startswith("{")


def test_list_ignores_an_unknown_engines_check_name_and_a_path(monkeypatch, tmp_path: Path, capsys):
    # Review finding: --list must win even when --engines/--env carries a
    # name that would otherwise be a usage error, and even alongside an
    # explicit path -- its own help text promises "ignores
    # --engines/--env/--json/path" unconditionally.
    _forbid_warden_gather(monkeypatch)

    exit_code = main(["check", str(tmp_path), "--list", "--engines", "bogus-name"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "osv-scanner" in captured.out


# --- --version/--help parity with warden's `scan` subcommand -----------------


def test_top_level_version_returns_zero_and_prints_version(capsys):
    exit_code = main(["--version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert __version__ in captured.out


def test_check_version_is_a_usage_error_matching_warden_scan_version(capsys):
    # Verified live against pyforge.warden.cli.main(["scan", "--version"]):
    # an argparse usage error, exit 2 -- --version stays top-level only.
    exit_code = main(["check", "--version"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err
    assert captured.out == ""


def test_check_help_exits_zero_and_prints_usage(capsys):
    exit_code = main(["check", "--help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage" in captured.out.lower()


# --- bare `doctor` with no subcommand (epics AC list, cross-checked here) ---


def test_bare_doctor_with_no_subcommand_is_a_usage_error(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err


# --- path positional forwarding ----------------------------------------------


def test_path_positional_defaults_to_current_directory(monkeypatch, tmp_path: Path, capsys):
    _stub_healthy_warden(monkeypatch)
    monkeypatch.chdir(tmp_path)

    exit_code = main(["check", "--json"])

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert exit_code == 0
    assert document["findings"]


# --- _write_stdout's sys.stdout is None guard ---------------------------


def test_write_stdout_does_not_crash_when_sys_stdout_is_none(monkeypatch):
    # Review finding: sys.stdout can legitimately be None (e.g. a detached/
    # frozen process) -- _write_stdout must guard this the same way the
    # sibling _stderr already guards sys.stderr.
    from pyforge.doctor import __main__ as main_module

    monkeypatch.setattr(main_module.sys, "stdout", None)
    main_module._write_stdout("doctor: some output\n")


# --- _emit_text's single-line message discipline -------------------------


def test_text_output_neutralizes_embedded_newlines_in_messages(capsys):
    # Review finding: warden's own _run_doctor wraps every message in
    # _single_line so free text (e.g. a scanned file path containing a
    # newline) can never forge extra finding lines under the header and
    # desync its N finding(s) count -- doctor's _emit_text, which claims
    # warden parity, interpolated finding.message raw.
    from pyforge.doctor import __main__ as main_module

    forged = Finding(
        source=Source.WARDEN_DOCTOR,
        check="deptry",
        status=DoctorStatus.OK,
        message="ok\n  [env-hygiene] forged-check: fail -- fabricated line",
        evidence={},
    )
    main_module._emit_text((forged,), verb="check")

    captured = capsys.readouterr()
    body_lines = captured.out.rstrip("\n").split("\n")
    # Exactly the header plus ONE finding line -- the embedded newline is
    # neutralized to a literal \n, never a real line break.
    assert len(body_lines) == 2
    assert "1 finding(s)" in body_lines[0]
    assert "\\n" in body_lines[1]
