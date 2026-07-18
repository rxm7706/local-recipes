"""Unit tests — the ``--bypass``/``--reason`` CLI surface + committed
``.warden-waivers.yaml`` integration (Story 3.2, FR24-FR26).

A new sibling to ``test_discovery_extract_cli.py`` (already large) per the
story spec's Code Map. Mirrors that file's own conventions: real
``tmp_path`` fixtures, ``main()`` invoked end-to-end, JSON output
schema-validated via ``jsonschema``.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from importlib import resources
from pathlib import Path

import jsonschema
import yaml

from pyforge.warden.cli import main
from pyforge.warden.report import TOOL_NAME

_FAR_FUTURE = "2099-01-01T00:00:00+00:00"
_LONG_AGO = "2000-01-01T00:00:00+00:00"
_RECENTLY_EXPIRED = "2000-06-01T00:00:00+00:00"


def write_pyproject(directory: Path, deps: list[str], *, extra: str = "") -> None:
    body = (
        "[project]\n"
        'name = "demo"\n'
        'version = "0.0.1"\n'
        f"dependencies = {json.dumps(deps)}\n"
        f"{extra}"
    )
    (directory / "pyproject.toml").write_text(body, encoding="utf-8")


def write_waiver_file(
    directory: Path,
    *,
    entry_id: str = "hygiene:DEP002:requests",
    accepted_at: str = _LONG_AGO,
    expires_at: str = _FAR_FUTURE,
    reason: str = "tracked in JIRA-1",
    authorized_by: str = "alice",
) -> None:
    body = (
        "version: 1\n"
        "waivers:\n"
        f"  - id: {entry_id!r}\n"
        f"    reason: {reason!r}\n"
        f"    authorized_by: {authorized_by!r}\n"
        f"    accepted_at: {accepted_at!r}\n"
        f"    expires_at: {expires_at!r}\n"
    )
    (directory / ".warden-waivers.yaml").write_text(body, encoding="utf-8")


def load_schema() -> dict:
    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def scan_json(capsys, target, extra_args: list[str] | None = None) -> tuple[int, dict, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json", *(extra_args or [])])
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return rc, document, captured.err


def _blocking_fixture(tmp_path: Path) -> None:
    """A hygiene DEP002 (unused-dependency) warn finding: the fixture
    every test in this file uses as its one "blocking" finding."""
    write_pyproject(tmp_path, ["requests==2.31.0"])
    (tmp_path / "main.py").write_text("", encoding="utf-8")


def _critical_vuln_fixture(tmp_path: Path) -> None:
    """A real CRITICAL vuln finding (Story 3.3): pdos-vuln-fixture==1.0.0
    matches the seeded PDOS-FIXTURE-0001 OSV advisory via the ambient
    offline DB every test session gets (tests/conftest.py's autouse
    _osv_ambient_db_env fixture) -- mirrors
    tests/conformance/test_scan_harness.py's own technique
    (test_critical_vuln_fixture_composes_policy_violation) so
    --warn-only/expiry tests exercise a genuine severity-gated
    policy-violation end to end, not a hand-built rung. The empty adjacent
    main.py (same technique as _blocking_fixture) keeps hygiene applicable
    so deptry also flags the fictitious dependency DEP002 (unused) -- a
    harmless, already-WARN native hygiene finding alongside the critical
    vuln:."""
    write_pyproject(tmp_path, ["pdos-vuln-fixture==1.0.0"])
    (tmp_path / "main.py").write_text("", encoding="utf-8")


def _high_vuln_fixture(tmp_path: Path) -> None:
    """A real HIGH (non-critical) vuln finding (Story 3.3): mirrors
    tests/fixtures/projects/vuln_high -- pdos-vuln-fixture-high==1.0.0
    matches PDOS-FIXTURE-0002, composing 'warn' by default (FR18: block on
    critical only) and 'policy-violation' under --fail-on high. No
    adjacent .py source, so hygiene is not applicable (no DEP002 noise) --
    this fixture exists solely to prove the nudge's downgraded-count
    varies with --fail-on while the final status/exit code do not."""
    write_pyproject(tmp_path, ["pdos-vuln-fixture-high==1.0.0"])


# --- --bypass requires --reason (usage error, exit 2, never 0) ----------


def test_bypass_without_reason_is_a_usage_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc = main(["scan", str(tmp_path), "--bypass"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "usage" in captured.err
    assert "--reason" in captured.err


def test_reason_without_bypass_is_not_an_error(capsys, tmp_path):
    """--reason has no effect on its own (never a usage error) -- only
    --bypass without --reason is guarded."""
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--reason", "unused"])
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "warn"


def test_bypass_with_empty_string_reason_is_not_a_usage_error(capsys, tmp_path):
    """The flag being PRESENT (even with an empty value) satisfies
    --bypass's requirement -- only its ABSENCE (argparse default None) is a
    usage error."""
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--bypass", "--reason", ""])
    assert rc == 0
    assert document["status"]["value"] == "bypassed"


# --- --bypass --reason "<text>" with blocking findings -------------------


def test_bypass_with_blocking_findings_prints_stanza_and_exits_bypassed(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    rc = main(["scan", str(tmp_path), "--bypass", "--reason", "ci override"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "version: 1" in captured.out
    assert "hygiene:DEP002:requests" in captured.out
    assert "ci override" in captured.out
    assert "status=bypassed" in captured.out
    assert "exit_code=0" in captured.out
    # The tool never writes the stanza into the scanned tree.
    assert not (tmp_path / ".warden-waivers.yaml").exists()


def test_bypass_stanza_is_yaml_safe_load_parseable_with_one_entry(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    # The stanza is the FIRST document-shaped content on stdout, before the
    # text-format human summary -- yaml.safe_load stops at the first
    # complete mapping it can parse from the leading lines.
    stanza_lines = []
    for line in captured.out.splitlines():
        if line.startswith(f"{TOOL_NAME}:"):
            break
        stanza_lines.append(line)
    document = yaml.safe_load("\n".join(stanza_lines))
    assert document["version"] == 1
    assert len(document["waivers"]) == 1
    assert document["waivers"][0]["id"] == "hygiene:DEP002:requests"
    assert document["waivers"][0]["reason"] == "x"


def test_bypass_json_format_still_exits_bypassed(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--bypass", "--reason", "x"])
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "bypassed"


def test_bypass_json_format_writes_the_stanza_to_stderr_not_stdout(capsys, tmp_path):
    """Review finding: --format json must keep stdout as EXACTLY one
    schema-valid document (NFR-I3) -- the stanza would otherwise be lost
    entirely for a json/CI consumer, so it goes to stderr instead."""
    _blocking_fixture(tmp_path)
    rc, document, err = scan_json(capsys, tmp_path, ["--bypass", "--reason", "ci override"])
    assert rc == 0
    assert document["status"]["value"] == "bypassed"
    assert "version: 1" in err
    assert "hygiene:DEP002:requests" in err
    assert "ci override" in err


def test_authorized_by_falls_back_to_unknown_when_getpass_raises(
    capsys, tmp_path, monkeypatch
):
    import pyforge.warden.cli as cli_module

    def _raise() -> str:
        raise OSError("no such user")

    monkeypatch.setattr(cli_module.getpass, "getuser", _raise)
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    assert "authorized_by: unknown" in captured.out


def test_bypass_respects_configured_waiver_default_expiry_days(capsys, tmp_path):
    write_pyproject(
        tmp_path,
        ["requests==2.31.0"],
        extra="\n[tool.pyforge-warden]\nwaiver-default-expiry-days = 30\n",
    )
    (tmp_path / "main.py").write_text("", encoding="utf-8")
    capsys.readouterr()
    main(["scan", str(tmp_path), "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    stanza_lines = []
    for line in captured.out.splitlines():
        if line.startswith(f"{TOOL_NAME}:"):
            break
        stanza_lines.append(line)
    document = yaml.safe_load("\n".join(stanza_lines))
    entry = document["waivers"][0]
    accepted = datetime.fromisoformat(entry["accepted_at"])
    expires = datetime.fromisoformat(entry["expires_at"])
    assert expires - accepted == timedelta(days=30)


# --- a committed valid non-expired waiver file (no --bypass) -------------


def test_committed_valid_waiver_bypasses_the_matching_finding(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "bypassed"


def test_committed_waiver_is_echoed_in_text_format(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(tmp_path, reason="tracked in JIRA-1", authorized_by="alice")
    rc = main(["scan", str(tmp_path)])  # text is the default format
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=bypassed" in captured.out
    assert "[waiver] hygiene:DEP002:requests" in captured.out
    assert "reason=tracked in JIRA-1" in captured.out
    assert "authorized_by=alice" in captured.out
    assert _FAR_FUTURE in captured.out


def test_expired_waiver_leaves_the_original_finding_status(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    write_waiver_file(
        tmp_path, accepted_at=_LONG_AGO, expires_at=_RECENTLY_EXPIRED
    )
    rc, document, _ = scan_json(capsys, tmp_path)
    assert document["status"]["value"] == "warn"  # never bypassed
    assert rc == document["exit_code"] == 0


def test_expired_waiver_shows_a_waiver_expired_notice_not_a_waiver_notice(
    capsys, tmp_path
):
    """Story 3.3: an expired match is no longer silently indistinguishable
    from "no waiver ever existed" -- it gets its own [waiver-expired] line
    (never the [waiver] applied-notice line), and that line must not
    unconditionally claim the finding is currently re-blocked (the actual
    outcome is stated by the status=/exit_code= line above it)."""
    _blocking_fixture(tmp_path)
    write_waiver_file(
        tmp_path,
        reason="tracked in JIRA-1",
        authorized_by="alice",
        accepted_at=_LONG_AGO,
        expires_at=_RECENTLY_EXPIRED,
    )
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[waiver]" not in captured.out
    assert "[waiver-expired] hygiene:DEP002:requests" in captured.out
    assert "reason=tracked in JIRA-1" in captured.out
    assert "authorized_by=alice" in captured.out
    assert _RECENTLY_EXPIRED in captured.out
    assert "re-blocked" not in captured.out


# --- expired waiver on a real policy-violation (Story 3.3) --------------


def test_expired_waiver_on_a_real_critical_vuln_still_composes_policy_violation(
    capsys, tmp_path
):
    """I/O matrix row: a real critical-vuln finding, expired waiver on the
    same id -- status/exit_code are unchanged from today (the re-block
    mechanism itself is untouched), in both text and json format."""
    _critical_vuln_fixture(tmp_path)
    write_waiver_file(
        tmp_path,
        entry_id="vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0",
        accepted_at=_LONG_AGO,
        expires_at=_RECENTLY_EXPIRED,
    )
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 1
    assert document["exit_code"] == 1
    assert document["status"]["value"] == "policy-violation"

    capsys.readouterr()
    rc_text = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc_text == 1
    assert "status=policy-violation" in captured.out
    assert "exit_code=1" in captured.out
    assert (
        "[waiver-expired] vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
        in captured.out
    )
    assert "[waiver]" not in captured.out
    assert "re-blocked" not in captured.out


# --- embedded-newline line forgery (Story 3.3 review finding) ------------


def test_embedded_newline_in_authorized_by_never_forges_a_line_active_waiver(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    write_waiver_file(
        tmp_path, authorized_by="alice\n  [forged] fake extra line"
    )
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert not any(
        line.strip() == "[forged] fake extra line"
        for line in captured.out.splitlines()
    )
    assert "authorized_by=alice\\n  [forged] fake extra line" in captured.out


def test_embedded_newline_in_authorized_by_never_forges_a_line_expired_waiver(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    write_waiver_file(
        tmp_path,
        accepted_at=_LONG_AGO,
        expires_at=_RECENTLY_EXPIRED,
        authorized_by="bob\n  [forged] fake extra line",
    )
    rc = main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert not any(
        line.strip() == "[forged] fake extra line"
        for line in captured.out.splitlines()
    )
    assert "authorized_by=bob\\n  [forged] fake extra line" in captured.out


# --- malformed / wildcard-id / unknown-version waiver file (FR26) --------


def test_malformed_waiver_yaml_is_a_config_parse_error(capsys, tmp_path):
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 1\nwaivers:\n  - id: [unterminated\n", encoding="utf-8"
    )
    rc, document, err = scan_json(capsys, tmp_path)
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-parse" in by_kind
    assert by_kind["config-parse"]["owner"] == "waiver"
    assert err != ""


def test_unknown_version_waiver_file_is_a_config_validation_error(capsys, tmp_path):
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 2\nwaivers: []\n", encoding="utf-8"
    )
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "waiver"


def test_wildcard_id_waiver_file_rejects_the_whole_file(capsys, tmp_path):
    write_waiver_file(tmp_path, entry_id="vuln:*:*")
    rc, document, _ = scan_json(capsys, tmp_path)
    assert rc == 2
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-validation" in by_kind
    assert by_kind["config-validation"]["owner"] == "waiver"


def test_malformed_waiver_file_still_fails_closed_even_with_bypass(capsys, tmp_path):
    """Review finding (traced but previously untested): a malformed
    committed waiver file's error rung must survive --bypass -- an
    ``error:...``-driven rung never matches any of the three finding-id
    families, so bypass_blocking cannot touch it, and the scan still fails
    closed at exit 2 regardless of --bypass."""
    _blocking_fixture(tmp_path)
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 1\nwaivers:\n  - id: [unterminated\n", encoding="utf-8"
    )
    rc, document, err = scan_json(
        capsys, tmp_path, ["--bypass", "--reason", "ci override"]
    )
    assert rc == 2
    assert rc == document["exit_code"]
    assert document["status"]["value"] == "error"
    by_kind = {e["kind"]: e for e in document["errors"]}
    assert "config-parse" in by_kind
    assert by_kind["config-parse"]["owner"] == "waiver"
    assert err != ""


def test_missing_waiver_file_is_not_an_error(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    rc, document, err = scan_json(capsys, tmp_path)
    assert document["status"]["value"] == "warn"
    assert document["errors"] == []
    assert "waiver" not in err


# --- --warn-only (Story 3.3, FR23/FR25) -----------------------------------


def test_warn_only_help_text_scopes_the_fail_on_no_effect_claim():
    """The help text's "no effect" claim must be scoped precisely to the
    composed status/exit code (genuinely --fail-on-invariant while
    --warn-only is set) -- NOT to the nudge's printed downgraded-finding
    count, which DOES vary with --fail-on (review-pass-2 finding)."""
    from pyforge.warden.cli import _build_parser

    _, scan_parser = _build_parser()
    help_text = scan_parser._option_string_actions["--warn-only"].help
    assert "status" in help_text
    assert "exit code" in help_text
    assert "--fail-on" in help_text
    assert "count" in help_text


def test_warn_only_downgrades_a_real_policy_violation_to_warn_with_a_nudge(
    capsys, tmp_path
):
    _critical_vuln_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--warn-only"])
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "warn"

    capsys.readouterr()
    rc_text = main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert rc_text == 0
    assert "status=warn" in captured.out
    assert "exit_code=0" in captured.out
    assert (
        "[warn-only] 1 finding not enforced while --warn-only is set -- "
        "drop --warn-only to re-enable enforcement" in captured.out
    )


def test_warn_only_nudge_counts_only_downgraded_findings_not_the_total(
    capsys, tmp_path
):
    """Mixed-finding-count row: one native-warn hygiene DEP002 finding and
    one native-warn license:unknown finding (Story 6.2: pdos-vuln-fixture is
    not an installed package) -- neither touched by warn_blocking, since
    neither was ever policy-violation/indeterminate -- alongside the one
    real downgraded critical vuln -- the nudge must name 1, never the
    report's total finding count of 3."""
    _critical_vuln_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--warn-only"])
    assert rc == 0
    assert len(document["findings"]) == 3

    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert "findings=3" in captured.out  # the verdict line's own total
    assert "[warn-only] 1 finding not enforced" in captured.out


def test_warn_only_nudge_pluralizes_for_multiple_downgraded_findings(
    capsys, tmp_path
):
    write_pyproject(tmp_path, ["pdos-vuln-fixture==1.0.0", "leftpad"])
    rc, document, _ = scan_json(capsys, tmp_path, ["--warn-only"])
    assert rc == 0
    assert document["status"]["value"] == "warn"

    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert (
        "[warn-only] 2 findings not enforced while --warn-only is set -- "
        "drop --warn-only to re-enable enforcement" in captured.out
    )


def test_warn_only_does_not_downgrade_a_tool_error_and_prints_no_nudge(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    (tmp_path / ".warden-waivers.yaml").write_text(
        "version: 1\nwaivers:\n  - id: [unterminated\n", encoding="utf-8"
    )
    rc, document, _ = scan_json(capsys, tmp_path, ["--warn-only"])
    assert rc == 2
    assert document["exit_code"] == 2
    assert document["status"]["value"] == "error"

    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert "status=error" in captured.out
    assert "[warn-only]" not in captured.out


def test_warn_only_on_an_already_clean_scan_prints_no_nudge(capsys, tmp_path):
    write_pyproject(tmp_path, ["requests==2.31.0"])
    (tmp_path / "main.py").write_text("import requests\n", encoding="utf-8")
    rc, document, _ = scan_json(capsys, tmp_path, ["--warn-only"])
    assert rc == 0
    assert document["status"]["value"] == "clean"

    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert "status=clean" in captured.out
    assert "[warn-only]" not in captured.out


def test_warn_only_combined_with_bypass_is_bypassed_with_no_nudge(capsys, tmp_path):
    _blocking_fixture(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only", "--bypass", "--reason", "x"])
    captured = capsys.readouterr()
    assert "status=bypassed" in captured.out
    assert "exit_code=0" in captured.out
    assert "[warn-only]" not in captured.out


def test_warn_only_combined_with_an_active_waiver_is_bypassed_with_no_nudge(
    capsys, tmp_path
):
    _blocking_fixture(tmp_path)
    write_waiver_file(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert "status=bypassed" in captured.out
    assert "[warn-only]" not in captured.out


def test_warn_only_combined_with_an_expired_waiver_downgrades_with_a_nudge(
    capsys, tmp_path
):
    """--warn-only + an expired waiver on the SAME finding: apply_waivers
    leaves the rung untouched (still policy-violation), then warn_blocking
    downgrades that same rung to warn -- status=warn, nudge present, and
    the expired-notice wording must not overclaim re-blocking (since
    warn-only just proved it is not, in fact, currently re-blocked)."""
    _critical_vuln_fixture(tmp_path)
    write_waiver_file(
        tmp_path,
        entry_id="vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0",
        accepted_at=_LONG_AGO,
        expires_at=_RECENTLY_EXPIRED,
    )
    capsys.readouterr()
    rc = main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "status=warn" in captured.out
    assert (
        "[waiver-expired] vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
        in captured.out
    )
    assert "re-blocked" not in captured.out
    assert "[warn-only] 1 finding not enforced" in captured.out


def test_warn_only_with_fail_under_coverage_breach_stays_indeterminate_no_nudge(
    capsys, tmp_path
):
    """FR19 guardrail: the indeterminate:coverage-floor:<axis> rung is
    computed inside report.assemble_report, strictly AFTER cli.py calls
    warn_blocking -- it structurally survives --warn-only untouched, so the
    composed status/exit code stay indeterminate/1 and no nudge (which
    would contradict that exit code) ever renders."""
    write_pyproject(tmp_path, ["leftpad", "requests>=2.0"])
    capsys.readouterr()
    rc = main(
        [
            "scan",
            str(tmp_path),
            "--warn-only",
            "--fail-under-coverage",
            "50",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "status=indeterminate" in captured.out
    assert "exit_code=1" in captured.out
    assert "[warn-only]" not in captured.out


def test_warn_only_no_nudge_when_composed_warn_is_unrelated_to_warn_only(
    capsys, tmp_path
):
    """The residual gate-hole review-pass-2 caught: status == "warn" alone
    is not sufficient -- a lone native hygiene warn-tier finding (never
    policy-violation/indeterminate) must not trigger a nonsensical nudge
    claiming 0 findings would be re-enabled by dropping a flag that
    touched nothing."""
    _blocking_fixture(tmp_path)
    rc, document, _ = scan_json(capsys, tmp_path, ["--warn-only"])
    assert rc == 0
    assert document["status"]["value"] == "warn"

    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured = capsys.readouterr()
    assert "status=warn" in captured.out
    assert "[warn-only]" not in captured.out


def test_fail_on_low_plus_warn_only_still_yields_warn_and_exit_zero(capsys, tmp_path):
    """Design-notes verification: --fail-on low (the strictest severity
    floor) combined with --warn-only still yields status=warn/exit 0 --
    warn_blocking downgrades unconditionally regardless of --fail-on, so
    only dropping --warn-only (never raising --fail-on) re-enables
    enforcement."""
    _critical_vuln_fixture(tmp_path)
    rc, document, _ = scan_json(
        capsys, tmp_path, ["--warn-only", "--fail-on", "low"]
    )
    assert rc == 0
    assert document["exit_code"] == 0
    assert document["status"]["value"] == "warn"


def test_fail_on_changes_the_nudge_count_but_never_the_final_status_or_exit(
    capsys, tmp_path
):
    """Review-pass-2 finding: the composed status/exit code ARE --fail-on
    -invariant while --warn-only is set, but the nudge's printed
    downgraded-finding COUNT is NOT -- a stricter --fail-on floor makes
    more findings compose policy-violation before warn_blocking runs,
    hence more get counted as downgraded, even though status/exit_code
    stay identical (live-verified on the HIGH-severity fixture: 0
    downgraded at the default fail_on=critical, 1 downgraded under
    --fail-on high)."""
    _high_vuln_fixture(tmp_path)
    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only"])
    captured_default = capsys.readouterr()
    capsys.readouterr()
    main(["scan", str(tmp_path), "--warn-only", "--fail-on", "high"])
    captured_high = capsys.readouterr()

    assert "status=warn" in captured_default.out
    assert "exit_code=0" in captured_default.out
    assert "[warn-only]" not in captured_default.out  # 0 downgraded

    assert "status=warn" in captured_high.out
    assert "exit_code=0" in captured_high.out
    assert "[warn-only] 1 finding not enforced" in captured_high.out
