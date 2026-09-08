"""`parse_cap` + `set_ceiling` + `budget set` CLI dispatch — Story 4.1.

Covers the I/O matrix's happy-path declaration and malformed-cap rows, both
at the primitive level and through the CLI (`main(["budget", "set", ...])`).
"""

from __future__ import annotations

import pytest

from pyforge.steward.budget import (
    BudgetDuty,
    CapParseError,
    load_budget,
    parse_cap,
    set_ceiling,
)
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main


def test_parse_cap_reads_amount_currency_period():
    amount, currency, period = parse_cap("1500usd/month")

    assert amount == 1500.0
    assert currency == "usd"
    assert period == "month"


def test_parse_cap_lowercases_currency_and_period():
    amount, currency, period = parse_cap("42EUR/YEAR")

    assert amount == 42.0
    assert currency == "eur"
    assert period == "year"


def test_parse_cap_accepts_a_decimal_amount():
    amount, _, _ = parse_cap("199.99usd/month")

    assert amount == 199.99


@pytest.mark.parametrize(
    "bad_cap",
    [
        "garbage",             # no digits, no unit, no period
        "1500usd",             # missing "/period"
        "usd/month",           # missing amount
        "1500/month",          # missing currency
        "1500us/month",        # currency not exactly 3 letters
        "1500usdd/month",      # currency not exactly 3 letters
        "-5usd/month",         # not a valid positive-amount shape
        "0usd/month",          # zero amount
        "-5.0usd/month",       # negative decimal
    ],
)
def test_parse_cap_rejects_malformed_values(bad_cap):
    with pytest.raises(CapParseError):
        parse_cap(bad_cap)


def test_set_ceiling_writes_the_declared_schema(tmp_path):
    path = tmp_path / "budget.yaml"

    ceiling = set_ceiling(path, "1500usd/month")

    assert ceiling.amount == 1500.0
    assert ceiling.currency == "usd"
    assert ceiling.period == "month"
    assert ceiling.declared_at

    (loaded,) = load_budget(path)
    assert loaded == ceiling


def test_set_ceiling_replaces_a_prior_declaration(tmp_path):
    path = tmp_path / "budget.yaml"
    set_ceiling(path, "1500usd/month")

    set_ceiling(path, "2000usd/month")

    ceilings = load_budget(path)
    assert len(ceilings) == 1
    assert ceilings[0].amount == 2000.0


def test_set_ceiling_with_a_malformed_cap_never_writes_the_file(tmp_path):
    path = tmp_path / "budget.yaml"

    with pytest.raises(CapParseError):
        set_ceiling(path, "garbage")

    assert not path.exists()


def test_set_ceiling_with_a_malformed_cap_never_corrupts_an_existing_file(tmp_path):
    path = tmp_path / "budget.yaml"
    set_ceiling(path, "1500usd/month")
    before = path.read_text()

    with pytest.raises(CapParseError):
        set_ceiling(path, "garbage")

    assert path.read_text() == before


def test_budget_set_via_cli_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)

    rc = main(["budget", "set", "--cap", "1500usd/month"])

    assert rc == EXIT_OK
    (ceiling,) = load_budget(tmp_path / ".steward" / "budget.yaml")
    assert ceiling.amount == 1500.0


def test_budget_set_via_cli_reports_a_usage_error_for_a_malformed_cap(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)

    rc = main(["budget", "set", "--cap", "garbage"])

    assert rc == EXIT_FAILED
    assert not (tmp_path / ".steward" / "budget.yaml").exists()


def test_budget_set_primitive_via_duty_reports_a_clear_error_not_a_raw_traceback(tmp_path):
    duty = BudgetDuty()
    import argparse

    result = duty.run(argparse.Namespace(budget_verb="set", cap="garbage"))

    assert result.ok is False
    assert "garbage" in result.summary


def test_bare_budget_degrades_and_names_the_set_verb():
    import argparse

    duty = BudgetDuty()

    result = duty.run(argparse.Namespace())

    assert result.ok is True
    assert "set" in result.summary
