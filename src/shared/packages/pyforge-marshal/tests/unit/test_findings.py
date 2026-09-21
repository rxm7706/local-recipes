"""Unit tests for ``pyforge.marshal.core.findings`` (Story 1.1, AD-15) --
format + membership checks via ``monkeypatch``-registered synthetic codes.
Most tests below still exercise the mechanism via synthetic codes, never a
fabricated production one -- ``test_registered_codes_contains_the_real_codes``
is the one exception, asserting the registry's REAL, currently-shipped
contents.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.core import findings


def test_registered_codes_contains_the_real_codes():
    """The registry no longer starts empty -- Story 1.2's core/identity.py
    is its first real caller, registering MRS-IDENT-001/002. Story 1.3's
    core/policy.py/cli/config.py add MRS-POLICY-001/002/003/004/005/006.
    Story 1.4's cli/init.py adds MRS-INIT-001/002/003/004. Story 1.5's
    cli/init.py tier3_backlink step adds MRS-INIT-005. Story 1.6's
    cli/init.py::run_homes adds MRS-HOMES-001/002/003. Story 1.7's
    cli/init.py::run_preflight adds MRS-PREFLIGHT-001..010. Story 1.8's
    cli/init.py::run_teardown adds MRS-TEARDOWN-001/002/003. Story 1.9's
    cli/init.py::run_preflight adds MRS-PREFLIGHT-011, graduating the
    harness-version check into two tiers. Story 2.1's cli/gate.py/core/gate.py
    add MRS-GATE-001/002/003/004/005. Story 2.4's
    core/gate.py::classify_doc_only_declaration adds MRS-GATE-006. Story
    3.2's core/journal.py::fold adds MRS-JOURNAL-001/002. Story 3.3's
    cli/spin.py adds MRS-SPIN-001/002/003/004/005/006. Story 3.4's
    cli/spin.py adds a seventh code to the same caller, MRS-SPIN-007. Story
    3.5's supervisor/__main__.py adds a NEW area, MRS-SUPV-001/002/003, and
    cli/spin.py adds an eighth code, MRS-SPIN-008. Story 3.6's
    supervisor/__main__.py adds MRS-SUPV-004/005/006 to the same area, and
    cli/spin.py adds a ninth code, MRS-SPIN-009. Story 3.7's
    supervisor/__main__.py adds MRS-SUPV-007 to the same area, and
    cli/spin.py adds MRS-SPIN-010/011/012. Story 3.8's
    supervisor/__main__.py adds MRS-SUPV-008 to the same area. Story 3.9
    adds MRS-SUPV-009 (a per-story branch retired while its work was NOT
    reachable from the station branch) -- deliberately a new code, since 3.9
    exists because 008 was firing on the success path. Story 2.3's
    cli/gate.py/core/gate.py add MRS-GATE-007/008/009. Story 4.1's
    cli/deploy.py/core/promotion.py add a NEW area, MRS-DEPLOY-001/002/003.
    Story 2.7's cli/gate.py/core/gate.py add MRS-GATE-010/011. Story 4.2's
    cli/init.py/cli/deploy.py add MRS-TEARDOWN-004/MRS-DEPLOY-004. Code
    review (2026-08-06) adds MRS-TEARDOWN-005 (P1) and MRS-DEPLOY-005 (P5).
    Story 4.3's cli/deploy.py::run_land_story adds MRS-DEPLOY-006/007/008/
    009. Story 4.8's cli/land.py adds a NEW area, MRS-LAND-001..007. Story
    4.9's cli/deploy.py::run_promote adds MRS-DEPLOY-023 (the new specs_dir
    advisory lock, AD-42). Story 5.9's cli/deploy.py::run_reconcile_
    completions adds MRS-DEPLOY-024/025/026/027 (the tracked ledger
    unreadable/unlockable, its write path failed, a corroborated
    not-loop-native key absent/unmatched in the ledger, and the post-
    commit Tier-3 feed repair-write failed). Story 3.12's
    cli/spin.py::run_resume adds MRS-SPIN-016 (the retry-escalation
    floor-raise's own policy.toml write failure, AD-26). Story 3.13's
    core/policy.py::compose adds MRS-POLICY-007 (a composed max_parallel
    above 1 -- bmad_loop 0.9.0's own Phase 5 fan-out scheduler is unbuilt
    and clamps every run to 1). Story 22.8's profile-driven session harness
    adds MRS-POLICY-008 (no harness_preference entry has a bmad-loop
    counterpart -- the rendered [adapter].name keeps the template default)
    and MRS-DISP-027/028/029 (a skipped preference candidate; an ignored
    overlay profile file; an omitted model tier). This asserts the
    registry's exact real contents."""
    assert findings.REGISTERED_CODES == frozenset(
        {
            "MRS-IDENT-001",
            "MRS-IDENT-002",
            "MRS-POLICY-001",
            "MRS-POLICY-002",
            "MRS-POLICY-003",
            "MRS-POLICY-004",
            "MRS-POLICY-005",
            "MRS-POLICY-006",
            "MRS-POLICY-007",
            "MRS-POLICY-008",
            "MRS-INIT-001",
            "MRS-INIT-002",
            "MRS-INIT-003",
            "MRS-INIT-004",
            "MRS-INIT-005",
            "MRS-HOMES-001",
            "MRS-HOMES-002",
            "MRS-HOMES-003",
            "MRS-PREFLIGHT-001",
            "MRS-PREFLIGHT-002",
            "MRS-PREFLIGHT-003",
            "MRS-PREFLIGHT-004",
            "MRS-PREFLIGHT-005",
            "MRS-PREFLIGHT-006",
            "MRS-PREFLIGHT-007",
            "MRS-PREFLIGHT-008",
            "MRS-PREFLIGHT-009",
            "MRS-PREFLIGHT-010",
            "MRS-PREFLIGHT-011",
            "MRS-TEARDOWN-001",
            "MRS-TEARDOWN-002",
            "MRS-TEARDOWN-003",
            "MRS-GATE-001",
            "MRS-GATE-002",
            "MRS-GATE-003",
            "MRS-GATE-004",
            "MRS-GATE-005",
            "MRS-GATE-006",
            "MRS-JOURNAL-001",
            "MRS-JOURNAL-002",
            "MRS-SPIN-001",
            "MRS-SPIN-002",
            "MRS-SPIN-003",
            "MRS-SPIN-004",
            "MRS-SPIN-005",
            "MRS-SPIN-006",
            "MRS-SPIN-007",
            "MRS-SPIN-008",
            "MRS-SPIN-009",
            "MRS-SUPV-001",
            "MRS-SUPV-002",
            "MRS-SUPV-003",
            "MRS-SUPV-004",
            "MRS-SUPV-005",
            "MRS-SUPV-006",
            "MRS-SUPV-007",
            "MRS-SPIN-010",
            "MRS-SPIN-011",
            "MRS-SPIN-012",
            "MRS-SUPV-008",
            "MRS-SUPV-009",
            "MRS-SUPV-010",
            "MRS-GATE-007",
            "MRS-GATE-008",
            "MRS-GATE-009",
            "MRS-DEPLOY-001",
            "MRS-DEPLOY-002",
            "MRS-DEPLOY-003",
            "MRS-GATE-010",
            "MRS-GATE-011",
            "MRS-TEARDOWN-004",
            "MRS-DEPLOY-004",
            "MRS-TEARDOWN-005",
            "MRS-DEPLOY-005",
            "MRS-DEPLOY-006",
            "MRS-DEPLOY-007",
            "MRS-DEPLOY-008",
            "MRS-DEPLOY-009",
            "MRS-DEPLOY-010",
            "MRS-DEPLOY-011",
            "MRS-DEPLOY-012",
            "MRS-DEPLOY-013",
            "MRS-DEPLOY-014",
            "MRS-DEPLOY-015",
            "MRS-DEPLOY-016",
            "MRS-DEPLOY-017",
            "MRS-DEPLOY-018",
            "MRS-DEPLOY-019",
            "MRS-DEPLOY-020",
            "MRS-STATUS-001",
            "MRS-DEPLOY-021",
            "MRS-DEPLOY-022",
            "MRS-LAND-001",
            "MRS-LAND-002",
            "MRS-LAND-003",
            "MRS-LAND-004",
            "MRS-LAND-005",
            "MRS-LAND-006",
            "MRS-LAND-007",
            "MRS-LAND-008",
            "MRS-DEPLOY-023",
            "MRS-RETIRE-001",
            "MRS-RETIRE-002",
            "MRS-RETIRE-003",
            "MRS-STATUS-002",
            "MRS-STATUS-003",
            "MRS-STATUS-004",
            "MRS-STATUS-005",
            "MRS-STATUS-006",
            "MRS-STATUS-007",
            "MRS-STATUS-008",
            "MRS-STATUS-009",
            "MRS-CHECK-001",
            "MRS-CHECK-002",
            "MRS-CHECK-003",
            "MRS-CHECK-004",
            "MRS-SPIN-013",
            "MRS-SPIN-014",
            "MRS-SPIN-015",
            "MRS-ADP-001",
            "MRS-ADP-002",
            "MRS-ADP-003",
            "MRS-ADP-004",
            "MRS-ADP-005",
            "MRS-ADP-006",
            "MRS-ADP-007",
            "MRS-ADP-008",
            "MRS-ADP-009",
            "MRS-ADP-010",
            "MRS-ADP-011",
            "MRS-CONFORM-001",
            "MRS-ADP-012",
            "MRS-ADP-013",
            "MRS-ADP-014",
            "MRS-ADP-015",
            "MRS-ADP-016",
            "MRS-SMOKE-001",
            "MRS-SMOKE-002",
            "MRS-SMOKE-003",
            "MRS-SMOKE-004",
            "MRS-SMOKE-005",
            "MRS-SMOKE-006",
            "MRS-SMOKE-007",
            "MRS-MATRIX-001",
            "MRS-MATRIX-002",
            "MRS-ENTRY-001",
            "MRS-UPSTREAM-001",
            "MRS-UPSTREAM-002",
            "MRS-PREFLIGHT-012",
            "MRS-PREFLIGHT-013",
            "MRS-PREFLIGHT-014",
            "MRS-LAND-009",
            "MRS-LAND-010",
            "MRS-LAND-011",
            "MRS-STATUS-010",
            "MRS-STATUS-011",
            "MRS-STATUS-012",
            "MRS-STATUS-013",
            "MRS-DEPLOY-024",
            "MRS-DEPLOY-025",
            "MRS-DEPLOY-026",
            "MRS-DEPLOY-027",
            "MRS-SPIN-016",
            "MRS-REFRESH-001",
            "MRS-REFRESH-002",
            "MRS-REFRESH-003",
            "MRS-REFRESH-004",
            "MRS-REFRESH-005",
            "MRS-REFRESH-006",
            "MRS-REFRESH-007",
            "MRS-REFRESH-008",
            "MRS-CHAIN-001",
            "MRS-CHAIN-002",
            "MRS-CHAIN-003",
            "MRS-CHAIN-004",
            "MRS-CHAIN-005",
            "MRS-DISP-001",
            "MRS-DISP-002",
            "MRS-DISP-003",
            "MRS-DISP-004",
            "MRS-DISP-005",
            "MRS-DISP-006",
            "MRS-DISP-007",
            "MRS-DISP-008",
            "MRS-DISP-009",
            "MRS-DISP-010",
            "MRS-DISP-011",
            "MRS-DISP-012",
            "MRS-DISP-013",
            "MRS-DISP-014",
            "MRS-DISP-015",
            "MRS-DISP-016",
            "MRS-DISP-017",
            "MRS-DISP-018",
            "MRS-DISP-019",
            "MRS-DISP-020",
            "MRS-DISP-021",
            "MRS-DISP-022",
            "MRS-DISP-023",
            "MRS-DISP-024",
            "MRS-DISP-025",
            "MRS-DISP-026",
            # Story 22.7 (fleet-wide drain, FR-193 CAP-7): its own area for
            # campaign-level findings -- 001 missing/unknown mode; 002 repo
            # root; 003 unreadable station ledger; 004 blocked story skipped;
            # 005 station blocked; 006 station busy this cycle; 007 campaign
            # supervisor spawn; 008 unreadable queue overrides; 009 cycle
            # journal write; 010 another cycle holds the fleet-wide campaign
            # lock; 011 one station's dispatch raised (the rest continue);
            # 012 no pyforge stations discovered at all.
            "MRS-DRAIN-001",
            "MRS-DRAIN-002",
            "MRS-DRAIN-003",
            "MRS-DRAIN-004",
            "MRS-DRAIN-005",
            "MRS-DRAIN-006",
            "MRS-DRAIN-007",
            "MRS-DRAIN-008",
            "MRS-DRAIN-009",
            "MRS-DRAIN-010",
            "MRS-DRAIN-011",
            "MRS-DRAIN-012",
            "MRS-DISP-027",
            "MRS-DISP-028",
            "MRS-DISP-029",
            # Story 22.9 (station-scoped dispatch branches): 030 an
            # unattributable legacy `marshal/<key>` branch refuses the
            # dispatch/landing; 031 this run is on an attributable legacy
            # branch and proceeds under an advisory.
            "MRS-DISP-030",
            "MRS-DISP-031",
            # Story 22.11 (station-scoped drain + an explicit story
            # sequence, FR-193 CAP-10): 032 `dispatch`'s sequence-argument
            # validation (neither/both of `story`/`--stories`, or an
            # unknown/already-done key). MRS-DRAIN-013 unknown `--station`;
            # 014 `--stories` without `--station`; 015 the tracked ledger
            # unreadable while validating a fresh `--stories` sequence.
            "MRS-DISP-032",
            # Story 28.16 (parallel dispatch fan-out when deps and surfaces
            # are disjoint): 034 within-station effective-surface intersection
            # refuses the candidate; 035 transitive Deps edge to an in-flight
            # story refuses; MRS-DRAIN-016 wave member refused at scheduling
            # time (WARN, serial fallback for that story).
            "MRS-DISP-034",
            "MRS-DISP-035",
            "MRS-DISP-036",
            "MRS-DISP-037",
            "MRS-DISP-038",
            "MRS-DISP-039",
            "MRS-DISP-040",
            # Story 33.9: verify_scope at factory dispatch boundary.
            "MRS-DISP-041",
            # Story 28.30 (CAP-3, dispatch half of the `output` layer):
            # deploying the caveman skill into a dispatch worktree
            # degraded -- unavailable instrument or a write failure.
            "MRS-DISP-042",
            # 2026-09-12 (dispatch-tier-routing-fails-safe): a tier-mapped
            # model's cost-catalog provider disagreed with the
            # live-verified harness the walk landed on -- override dropped.
            "MRS-DISP-043",
            # Story 51.1 (verification sees the merge result): the
            # merge-tree preview of the branch onto `origin/main` failed
            # `verify_commands`, or the behind-check itself was unevaluable.
            "MRS-DISP-044",
            # Story 51.4 (spec-pyforge-marshal CAP-252): the pre-launch
            # guard's worktree spec is `status: blocked` -- refuse to
            # relaunch bmad-build-auto without an operator decision.
            "MRS-DISP-045",
            # Story 51.11 (CAP-258): worktree spec reads status: blocked but
            # its baseline_revision predates this run -- advisory only.
            "MRS-DISP-046",
            # Story 53.2 (spec-pyforge-marshal CAP-261b): 047 the landing
            # reconciled spec-surface drift found on the branch's own
            # changed files before merging (or could not even evaluate
            # drift, e.g. the doctor source tree unreachable), or
            # `dispatch_land_finalize` ran `deferred_work_intake.py --fix`
            # and it refused a deferral -- always WARN, non-blocking,
            # visible in `marshal watch`/`fleet-picture` ATTENTION rows.
            # 048 the branch's own spec-surface drift named a path this
            # branch did not change (foreign drift) or the reconcile
            # machinery itself failed to safely APPLY a known reconcile
            # (`VcsPort.changed_files`, memlog append, the scoped stamp, or
            # the reconcile commit/push) -- refuses the landing.
            "MRS-DISP-047",
            "MRS-DISP-048",
            "MRS-DRAIN-016",
            "MRS-DRAIN-017",
            "MRS-DRAIN-013",
            "MRS-DRAIN-014",
            "MRS-DRAIN-015",
            # Story 28.2 (wire compression at the harness seam,
            # SPEC-marshal-token-economy CAP-2): MRS-DISP-033 an enabled
            # `[context]` wire layer that factory dispatch could not apply
            # (no `[wrapper]`, an unresolved wrapper binary, an uncreatable
            # CCR store); MRS-SPIN-017 the same layer enabled on the
            # bmad-loop engine, which launches the coding CLI itself and so
            # has no argv for marshal's harness seam to wrap. Both WARN --
            # a layer disables itself with a named finding, never blocks.
            "MRS-DISP-033",
            "MRS-SPIN-017",
            # Story 28.3 (Genesis seeds the token-economy kit,
            # SPEC-marshal-token-economy CAP-3/CAP-4): MRS-PREFLIGHT-015 names
            # a kit item preflight could not put in place -- an unavailable
            # instrument (platform gap), a failed provisioning step, or an
            # unloadable packaged seed manifest. WARN, the same tier and the
            # same reason as the two Story 28.2 codes above.
            "MRS-PREFLIGHT-015",
            "MRS-PREFLIGHT-016",
            # Story 28.15 (scope-violation enforcement mode, policy-declared,
            # default warn, CAP-17): MRS-GATE-012/013 are the warn-mode
            # advisory siblings of MRS-GATE-007/008.
            "MRS-GATE-012",
            "MRS-GATE-013",
            # Story 28.22 (verify blast radius, CAP-5): pre-existing-gate WARN.
            "MRS-GATE-014",
            # Story 22.12 (shared-surface cross-suite gate, CAP-12).
            "MRS-GATE-015",
            # Story 28.8 (derived context recomputes only on source change,
            # SPEC-marshal-token-economy CAP-5): `marshal context refresh`'s
            # own area. 001 UNEVALUABLE (the derived-context declaration
            # itself could not be resolved -- a malformed slug/epic, or no
            # planning-artifacts directory to list); 002 WARN (an ENABLED
            # layer degraded to today's compile-on-hunch behavior with a
            # named reason -- the same never-blocking tier as MRS-DISP-033
            # and MRS-PREFLIGHT-015).
            "MRS-CTX-001",
            "MRS-CTX-002",
            # Story 28.9 (planning-graph retrieval, CAP-6/CAP-13):
            # `marshal context retrieve`'s degradation code -- WARN, never
            # blocking; falls back to Story 28.8's epic-context file.
            "MRS-PLAN-001",
            # Story 28.7 (index freshness is an advisory finding,
            # SPEC-marshal-token-economy CAP-10): `marshal check` gains
            # advisory codegraph/cocoindex staleness findings. Four codes:
            # 001 codegraph index missing in enabled layer, 002 codegraph
            # index stale, 003 cocoindex missing, 004 cocoindex stale.
            # All WARN, never ERROR -- advisory only, per the spec's
            # constraint that a staleness finding alone never blocks.
            "MRS-IDXF-001",
            "MRS-IDXF-002",
            "MRS-IDXF-003",
            "MRS-IDXF-004",
            # Story 28.5 (pinned wrapped-vs-unwrapped benchmark, CAP-9):
            # `marshal benchmark compare`'s own area.
            "MRS-BENCH-001",
            "MRS-BENCH-002",
            "MRS-BENCH-003",
            "MRS-BENCH-004",
            # Story 44.1 (marshal watch).
            "MRS-WATCH-001",
            "MRS-WATCH-002",
            "MRS-WATCH-003",
            "MRS-WATCH-004",
            # Story 47.1 (SPEC-marshal-recall-in-the-loop CAP-1): a
            # pre-launch `scribe recall` attempt that degraded (CLI
            # unresolved/non-zero/timeout, or the artifact write failed).
            "MRS-SPIN-018",
        }
    )


def test_code_pattern_matches_well_formed_code():
    assert findings.CODE_PATTERN.fullmatch("MRS-GATE-001")


@pytest.mark.parametrize(
    "code",
    [
        "not-a-code",
        "mrs-gate-001",
        "MRS-GATE-1",
        "MRS-001",
        "MRS-GATE-0001",
        "",
        "MRS-GATE-001\n",  # the `$`-before-trailing-newline `re` pitfall
        "MRS-GATE-001 ",
        "MRS-GATE-١٢٣",  # Arabic-Indic digits: Python's \d
        # would accept these; [0-9] (matching the schema's ECMA reading)
        # must not.
    ],
)
def test_code_pattern_rejects_malformed_codes(code):
    assert findings.CODE_PATTERN.fullmatch(code) is None


def test_code_pattern_is_matched_with_fullmatch_not_match():
    """Regression: CODE_PATTERN carries no ^/$ anchors and MUST be matched
    with .fullmatch(), never .match() -- .match() only anchors at the start,
    so an unanchored pattern would wrongly accept a code with a trailing
    extra digit or newline as long as its PREFIX is well-formed."""
    assert findings.CODE_PATTERN.match("MRS-GATE-0001") is not None  # prefix matches
    assert findings.CODE_PATTERN.fullmatch("MRS-GATE-0001") is None  # but not fully
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("MRS-GATE-0001")


def test_require_registered_rejects_malformed_code_before_membership_check():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("not-a-code")


def test_require_registered_rejects_wellformed_but_unregistered_code():
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("MRS-ZZZ-999")


def test_require_registered_accepts_monkeypatched_synthetic_code(monkeypatch):
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({"MRS-TST-001"}))
    assert findings.require_registered("MRS-TST-001") == "MRS-TST-001"


def test_require_registered_still_rejects_other_codes_after_monkeypatch(monkeypatch):
    monkeypatch.setattr(findings, "REGISTERED_CODES", frozenset({"MRS-TST-001"}))
    with pytest.raises(findings.UnregisteredFindingCodeError):
        findings.require_registered("MRS-TST-002")


def test_unregistered_finding_code_error_is_a_value_error():
    assert issubclass(findings.UnregisteredFindingCodeError, ValueError)
