---
name: "minting-a-cap-on-a-station-whose-prd-or-architecture-spine-i"
description: "Minting a CAP on a station whose PRD or architecture spine is more than 2 days older than the Spec turns pr-preflight r…"
metadata:
  type: feedback
---

Minting a CAP on a station whose PRD or architecture spine is more than 2 days older than the Spec turns pr-preflight red on chain_currency_sweep_check (the spec->prd feeds edge; the Spec's date is its .memlog.md). Found 2026-09-27 on PR #1637: mason and warden (PRD/spine at 2026-09-20) went red, marshal and steward (touched within 2 days) stayed current. In the same PR, add a dated Currency reconciliation note to the PRD and the spine that says what the CAP changes (and that no FR/AD moves, when none does) and bump their updated: -- a bare stamp is forbidden by CHAIN-CURRENCY-RUNBOOK.md. Check before pushing: python scripts/chain_currency_sweep_check.py --project <slug> --json.
