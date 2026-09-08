# PRD Quality Review — the Canopy mounts the eight stations

## Overall verdict

The FRs, glossary, and SM-5 already carry the 2026-08-24 operating-model bind (03-only five-tier, `work_class`, hooks/plugins, Q4 envelope). That is enough to implement from. What is at risk is the **tail**: §2 still says sixteen capabilities, §10 still treats OQ-4 and recipe authorship as live, and §14 still reads as if architecture and epics have not run. A later pass that extracts those sections would undo FR-9a and canopy:AD-16.

## Decision-readiness — adequate

Trade-offs are named where they count: CodeRed dropped, RFC-5 unimplementable as written, Tasks replaced by `start`/`get`, packaging operator-owned in the OM but **not** in §10. Open Questions §11 still-open list is real (FastMCP vs `mcp` outage, Liquibase tracking schema). `lane1-serves-dw-h3` **answered no 2026-08-25**. Answered items include OQ-4. The failure is leftover prose that re-opens answered decisions.

### Findings
- **high** Tail sections re-open answered decisions (§10, §14) — Integration still says the compliance portal “may need to move if OQ-4 chooses a uniform prefix”; §14 says architecture must fix “its URL scheme (OQ-4)” and that epics begin after. §11 already answers OQ-4; Epics 18–30 exist. *Fix:* PRD Update: rewrite §10 bullet and §14 to past tense / closed; point at FR-9a and Epic 18.

## Substance over theater — strong

Four users including the agent; UJs are sessions not personas-as-furniture. NFRs have numbers (30s, 8×5, RS256). Vision is brownfield-specific (`src/platform/` one of eight). No finding.

## Strategic coherence — strong

Thesis: finish the shipped Canopy, do not rewrite the host. Feature grouping by delivery seam matches epics. SM-5 and SM-C3 still attack shallow skill-count. MVP honestly defers flags and governed DDL behind packaging. No finding.

## Done-ness clarity — strong

FRs 1–42 carry testable consequences. FR-37/38/39 are 03-scoped. FR-12 names `start`/`get`. Vague “gracefully” language is not the pattern here.

### Findings
- **low** UJs do not mention `work_class` or Golden Path (§2.3) — Journeys still describe the 03 estate only, which is correct enough; OM rules live in glossary + FR-2. *Fix:* optional one clause on UJ-1 that 01/02 work is not a switcher tile.

## Scope honesty — adequate

Non-goals are explicit (no ninth station, no atlas Wagtail spec, no CAP-18 in glossary). `[NOTE FOR PM]` callouts are real tensions. Open-item density is appropriate for a chain-top PRD **if** the answered OQs stay answered in §10.

### Findings
- **high** Packaging authorship disagrees with the brief and canopy:AD-16 (§10) — “Each is a `conda-forge-expert` session under repo Rule 1.” Brief addendum and canopy:AD-16: S-26.3 / S-27.1 do not author recipes. *Fix:* PRD Update: those six builds are operator-owned gates; Rule 1 applies if recipes are authored outside this chain.

## Downstream usability — thin

This PRD is chain-top. Glossary terms (`work_class`, hooks/plugins, Tachyon) are consistent in §3 and FRs. The extract hazard is the stale tail plus “sixteen capabilities” in §2.

### Findings
- **high** Capability count drift (§2) — “five of the sixteen capabilities” after CAP-17 exists. Brief says seventeen. Traceability §12 lists CAP-1..17. *Fix:* change sixteen → seventeen.
- **medium** §14 claims architecture and epic passes are still ahead — Spine is `final`; Epics 18–30 written; first dispatch S-18.1. *Fix:* “What comes next” = implement S-18.1; packaging tails wait. `lane1-serves-dw-h3` **answered no 2026-08-25** (historical finding).

## Shape fit — strong

Internal/brownfield capability spec with a few UJs is the right shape. Not over-formalized. Chain-top downstream usability is the dimension that is thin, not shape.

## Mechanical notes

- Glossary: `work_class`, Path B/Tachyon, hooks/plugins present and used in FR-1/2/17/37–39.
- FR IDs include FR-9a/9b/21a; contiguous enough; no duplicate FR numbers spotted.
- Assumptions Index still flags agent-as-first-class as derived; brief Update says PRD confirmed it — index can drop the hedge on Update.
- OQ numbering in §11 (still-open 1–3 vs answered -2, -1, 0, 5, 6, 7) is historical and ugly; not a broken cross-ref.
- `addendum.md` OM section agrees with the brief addendum; PRD body tail does not.
