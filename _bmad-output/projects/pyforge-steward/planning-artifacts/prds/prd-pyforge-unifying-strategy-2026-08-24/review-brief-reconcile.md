# Brief reconcile — Canopy PRD vs 2026-08-24 brief Update

Ad-hoc reviewer for Validate. Compares `briefs/brief-pyforge-unifying-strategy-2026-08-24/brief.md` + `addendum.md` to `prd.md` + PRD `addendum.md`. Does not re-score the seven rubric dimensions.

## Verdict

**FRs and glossary agree with the brief.** The disagreement is leftover PRD tail copy written when architecture and epics were still ahead, and when packaging still looked like in-chain CFE stories.

## Agreements (do not “fix”)

- Five-tier is 03-only (brief; PRD glossary + FR-37/38/39 + SM-5).
- Registration carries owner / `work_class` / promotion date; SLA not an AppConfig field (FR-1).
- No 01/02 station tiles (FR-2).
- Hooks/plugins glossary + AD-21 pointer (PRD §3).
- Path B ≠ Tachyon; Lane 2 HTMX implied by stack/SPEC; Q4 identity on FR-17 area.
- No CAP-18; scorecard unpublished.
- Remaining product question: Lane 1 vs atlas DW-H3 (brief; PRD still-open #2).
- MCP Tasks: `start`/`get` (both).

## Gaps

- **high** OQ-4 zombie — Brief: URL scheme closed (FR-9a). PRD §11 answers it; PRD §10 and §14 still speak as if it is open.
- **high** Recipe authorship — Brief addendum sequencing 1: operator gates. PRD §10: every packaging item is a CFE session in this chain.
- **medium** Seventeen vs sixteen — Brief and §12 use 17; §2 still says 16.
- **medium** “Where next” — Brief: S-18.1, do not regenerate sprint feed. PRD §14: architecture then epics from 18.
- **low** Agent-as-user hedge — Brief: PRD confirmed. PRD Assumptions Index still calls it unverified derivation.

## Compact summary

input: brief-pyforge-unifying-strategy-2026-08-24; gaps: OQ-4 zombie in §10/§14, CFE-vs-operator packaging, sixteen vs seventeen, stale §14 next-step; file: review-brief-reconcile.md
