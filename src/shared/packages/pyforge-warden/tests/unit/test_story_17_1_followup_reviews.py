"""Story 17.1 — independent follow-up review pins (FRR-* / DW-FU-5-1 / DW-FU-6-3).

Adversarial pass read shipped code against each cited story spec. No material
defects beyond fixes landed in Story 17.1; residual sub-deferrals in
deferred-work-ledger.md for Stories 5.1/6.3 remain open by design.
"""

from __future__ import annotations

from pyforge.warden.hooks import PR_GATE_HOOK_SPECS
from pyforge.warden.scanner_plugins import OPTIONAL_SCANNER_ID_SET, select_scanner_plugins
from pyforge.warden.tea_advisory import TeaRosterMissingError, run_tea_test_review


def test_frr_9_1_hook_book_still_three_warden_owned_specs():
    assert len(PR_GATE_HOOK_SPECS) == 3
    assert all(spec.owner == "warden" for spec in PR_GATE_HOOK_SPECS)


def test_frr_9_2_default_scan_plugins_exclude_unconfigured_optionals():
    plugins = select_scanner_plugins(enabled_optional=())
    ids = {getattr(p, "scanner_id", p.owner) for p in plugins}
    assert "checkmarx" in OPTIONAL_SCANNER_ID_SET
    assert "checkmarx" not in ids


def test_frr_9_3_default_scan_without_checkmarx_is_non_empty_core():
    plugins = select_scanner_plugins(enabled_optional=())
    assert len(plugins) >= 1


def test_dw_fu_11_2_roster_missing_still_refuses(tmp_path):
    try:
        run_tea_test_review(tmp_path)
    except TeaRosterMissingError:
        pass
    else:
        raise AssertionError("expected TeaRosterMissingError")
