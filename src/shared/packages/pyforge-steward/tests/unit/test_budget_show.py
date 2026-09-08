"""`format_ceilings` + `budget show` CLI dispatch — Story 4.2.

Covers the I/O matrix's declared-ceiling and never-declared rows, in both
text and `--json` form, at the primitive level and through the CLI
(`main(["budget", "show", ...])`).
"""

from __future__ import annotations

import json

from pyforge.steward.budget import format_ceilings, set_ceiling
from pyforge.steward.cli import EXIT_OK, main


def test_format_ceilings_text_shows_a_declared_ceiling(tmp_path):
    path = tmp_path / "budget.yaml"
    ceiling = set_ceiling(path, "1500usd/month")
    from pyforge.steward.budget import load_budget

    text = format_ceilings(load_budget(path), as_json=False)

    assert "1500" in text
    assert "usd" in text
    assert "month" in text
    assert ceiling.declared_at in text


def test_format_ceilings_json_shows_the_same_data_machine_readably(tmp_path):
    path = tmp_path / "budget.yaml"
    set_ceiling(path, "1500usd/month")
    from pyforge.steward.budget import load_budget

    payload = json.loads(format_ceilings(load_budget(path), as_json=True))

    assert payload == [
        {
            "amount": 1500.0,
            "currency": "usd",
            "period": "month",
            "declared_at": payload[0]["declared_at"],
        }
    ]


def test_format_ceilings_text_reports_clearly_when_none_declared():
    text = format_ceilings((), as_json=False)

    assert "no ceiling" in text.lower()
    assert text != "0"


def test_format_ceilings_json_reports_an_empty_array_when_none_declared():
    payload = json.loads(format_ceilings((), as_json=True))

    assert payload == []


def test_budget_show_via_cli_prints_a_declared_ceiling(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)
    main(["budget", "set", "--cap", "1500usd/month"])
    capsys.readouterr()  # discard `set`'s own stdout before asserting on `show`'s

    rc = main(["budget", "show"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "1500" in out
    assert "usd" in out


def test_budget_show_json_via_cli_round_trips(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)
    main(["budget", "set", "--cap", "1500usd/month"])
    capsys.readouterr()  # discard `set`'s own stdout before asserting on `show`'s

    rc = main(["budget", "show", "--json"])

    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["amount"] == 1500.0


def test_budget_show_via_cli_reports_clearly_when_never_declared(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)

    rc = main(["budget", "show"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "no ceiling" in out.lower()
    assert out.strip() != "0"


def test_budget_show_json_via_cli_reports_an_empty_array_when_never_declared(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)

    rc = main(["budget", "show", "--json"])

    assert rc == EXIT_OK
    assert json.loads(capsys.readouterr().out) == []


def test_budget_show_json_via_cli_renders_a_load_error_as_json_not_plain_text(
    tmp_path, monkeypatch, capsys
):
    """Regression test for the `--json`-on-an-error-path bug class Epic 3's
    own closing review found and fixed in `ProvisionDuty` — a corrupt
    `.steward/budget.yaml` must still yield valid JSON on stderr when
    `--json` was passed, never a plain-text summary a caller's
    `json.loads()` would choke on."""
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)
    budget_path = tmp_path / ".steward" / "budget.yaml"
    budget_path.parent.mkdir(parents=True)
    budget_path.write_text("ceilings:\n  - currency: usd\n    period: month\n")  # missing amount

    from pyforge.steward.cli import EXIT_FAILED

    rc = main(["budget", "show", "--json"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    payload = json.loads(err)
    assert "error" in payload


def test_budget_show_json_via_cli_renders_a_non_list_ceilings_error_as_json(
    tmp_path, monkeypatch, capsys
):
    """Review finding: `for raw in document.get("ceilings") or []:` raised a
    bare, uncaught `TypeError` (not `BudgetError`) when "ceilings" was a
    truthy non-list scalar (e.g. `ceilings: 5`) -- that propagated past
    every duty-level exception handler to `cli.main()`'s generic
    `except Exception`, printing a raw Python traceback instead of the
    promised clean, `--json`-aware error."""
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)
    budget_path = tmp_path / ".steward" / "budget.yaml"
    budget_path.parent.mkdir(parents=True)
    budget_path.write_text("ceilings: 5\n")

    from pyforge.steward.cli import EXIT_FAILED

    rc = main(["budget", "show", "--json"])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    payload = json.loads(err)
    assert "error" in payload


def test_budget_show_reports_a_load_error_when_declared_at_is_missing(
    tmp_path, monkeypatch, capsys
):
    """Review finding: `Ceiling.declared_at` is typed `str` (non-optional),
    and this module's own docstring promises a document missing a required
    field raises `BudgetError` -- but the load path used `.get()` for
    `declared_at`, silently defaulting to `None` instead of raising."""
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)
    budget_path = tmp_path / ".steward" / "budget.yaml"
    budget_path.parent.mkdir(parents=True)
    budget_path.write_text(
        "ceilings:\n  - amount: 1500\n    currency: usd\n    period: month\n"
    )  # missing declared_at

    from pyforge.steward.cli import EXIT_FAILED

    rc = main(["budget", "show"])

    assert rc == EXIT_FAILED
