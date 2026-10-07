---
name: "a-memlog-append-or-a-new-planning-artifacts-research-file-al"
description: "A memlog append or a new planning-artifacts/research/ file alone trips chain-currency-sweep-check's 2-day gate (spec->p…"
metadata:
  type: feedback
---

A memlog append or a new planning-artifacts/research/ file alone trips chain-currency-sweep-check's 2-day gate (spec->prd from the memlog stamp, research->brief from the research file's frontmatter date), with no CAP minted: on 2026-10-07 a docs-only review PR was refused twice by the pre-push preflight. Any commit touching a station's .memlog.md or adding a research/ file re-stamps brief, PRD, spine and epics updated: to that date in the same commit, each with a RE-STAMPED note (no CAP/FR/AD/story moved) and a short Currency reconciliation section (precedents: PRD/spine 2026-10-01, brief 2026-09-25). Read the exact edge from scripts/chain_currency_sweep_check.py --json --project <station> (findings[].evidence.staleBy). ad-citation-check also scans research/ and .memlog.md for bare CAP-n ids the project does not define: never cite an unminted CAP by number there.
