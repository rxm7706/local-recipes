"""`budget check` CLI dispatch — Story 4.3 (AD-6, FR-18).

`steward budget check` never fabricates a pass/fail — v1 has no metered
spend source wired in anywhere, so `check` always reports "no metered
spend source configured" via the dedicated `EXIT_BUDGET_NOT_CONFIGURED`
exit code, regardless of whether a ceiling was ever declared (Story 4.1).
"""

from __future__ import annotations

import argparse

from pyforge.steward.budget import BudgetDuty
from pyforge.steward.cli import EXIT_BUDGET_NOT_CONFIGURED, EXIT_FAILED, EXIT_OK, main


def test_budget_check_always_reports_not_configured_with_no_ceiling_declared(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)

    rc = main(["budget", "check"])

    assert rc == EXIT_BUDGET_NOT_CONFIGURED
    assert rc != EXIT_OK
    assert rc != EXIT_FAILED


def test_budget_check_always_reports_not_configured_even_with_a_ceiling_declared(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)
    main(["budget", "set", "--cap", "1500usd/month"])

    rc = main(["budget", "check"])

    assert rc == EXIT_BUDGET_NOT_CONFIGURED


def test_budget_check_prints_the_honest_not_configured_message(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.budget.repo_root", lambda: tmp_path)

    main(["budget", "check"])

    out = capsys.readouterr().out
    assert "no metered spend source configured" in out


def test_budget_check_exit_code_is_distinct_from_ok_and_failed():
    assert EXIT_BUDGET_NOT_CONFIGURED not in (EXIT_OK, EXIT_FAILED)


def test_budget_check_primitive_via_duty():
    duty = BudgetDuty()

    result = duty.run(argparse.Namespace(budget_verb="check"))

    assert result.ok is True
    assert "no metered spend source configured" in result.summary
    assert result.details["exit_code"] == EXIT_BUDGET_NOT_CONFIGURED


def test_bare_budget_degrades_and_names_all_three_verbs():
    """Now that `check` (this story) completes the triad, the bare-invocation
    degrade message (AD-7) should name all three verbs Epic 4 defines."""
    duty = BudgetDuty()

    result = duty.run(argparse.Namespace())

    assert result.ok is True
    assert "set" in result.summary
    assert "show" in result.summary
    assert "check" in result.summary
