---
name: "2026-11-25-operator-rulings-on-dw-steward-134-2-1-and-dw-ste"
description: "2026-11-25 operator rulings on DW-steward-134-2-1 and DW-steward-136-11-1 (after a deep analysis that probed the hook p…"
metadata:
  type: project
---

2026-11-25 operator rulings on DW-steward-134-2-1 and DW-steward-136-11-1 (after a deep analysis that probed the hook patch against main): (1) Hook patch: apply the push-redirection half only (DW-steward-134-2-1-push-half.patch, 552 tests pass); decline the submit_pr.sh half, which let 'diff <(bash scripts/submit_pr.sh)' run it and 'cat scripts/submit_pr.sh > /tmp/x.sh' copy it past the hook; read that script with the Read tool. (2) The hook's pre-existing gap (it never reads inside $(...) or backticks) is fixed as a tightening Story. (3) Story 59.2's shipped status-set half re-homes on spec-pyforge-steward CAP-132 by amendment, no new CAP. (4) 'Unify for real': the exit-code half of the dropped vocabulary CAP-2 (DW-VOCAB-2026-09-14-8) becomes one machine-readable exit-code declaration in docs/governance/guild-roster.json that doctor, warden, marshal and scripts/detectors.py read; no surface's exit numbers change.
