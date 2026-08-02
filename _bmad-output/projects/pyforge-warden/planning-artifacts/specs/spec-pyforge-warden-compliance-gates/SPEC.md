---
id: SPEC-pyforge-warden-compliance-gates
spec: pyforge-warden-compliance-gates
status: archived
archived-reason: duplicate
owner-dream: docs/dreams/pyforge-warden-compliance-gates.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/pyforge-warden-compliance-gates.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`duplicate`). Charter §5 requires
> every Dream to carry a Spec, archived included: a retirement record is how the next reader
> learns from the decision instead of rediscovering the idea. It states what was contracted,
> why it ended, and what survives — not a plan for work that will not happen.

# pyforge-warden-compliance-gates — retirement record

## Why it was contracted

A "compliance gates" dream for Warden: a pluggable multi-axis Python dependency compliance
gate scanning manifests for security, license, hygiene, and currency issues; aggregating
findings into one never-false-green verdict; fine-grained policy with baseline &
grandfathering; a versioned `ComplianceReport` contract; and an opt-in fix-PR actuator.

## Why it ended

**Retired 2026-08-02, same day it was created.** The dream was generated in a bulk commit
(`dad47c408a`) later found to contain fabricated content elsewhere in the same commit (a
migration note with false claims about the dashboard generator, boilerplate
test-architecture.md files duplicated across stations with only nouns swapped). This dream's
own content did not survive scrutiny as new scope: its six-item "Realization" list maps 1:1
onto capabilities the existing [[pyforge-warden]] Dream already fully governs via
`spec-pyforge-warden` (`status: shipped`, 31/31 stories merged via PR #110) — and Warden's
entire product identity already **is** "a pluggable multi-axis Python dependency compliance
gate," verbatim from that Spec's own opening line:

- **"Multi-axis Scanning — Hygiene, Security (+ CISA-KEV + EPSS), License, Currency"** ↔
  `SPEC-pyforge-warden` CAP-4 ("Every resolved component is assessed on each registered axis
  of trust… Hygiene, security, license, and currency each produce a verdict") plus the
  Constraints section's "Six axes of trust, four live." Shipped as Story 1.3 (deptry), Story
  1.5 (osv-scanner), Story 6.2 (license axis), Story 6.3 (currency axis), Story 6.4 (KEV feed
  + `--fail-on-kev`), Story 6.7 (EPSS feed + `--min-epss`).
- **"Verdict Never False-Greens — Aggregation is pessimistic"** ↔ CAP-1/the Constraints
  section's "Never false-green is *the* acceptance property," the frozen seven-rung lattice
  `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`
  owned solely by `verdict.py`. Shipped as Story 1.1 (C0a projection-safety), Story 1.6
  (severity gate + verdict composition).
- **"Fine-grained Policy — operators define block/warn/accept rules"** ↔ CAP-5 ("A team can
  tune what blocks without editing the tool" — `[tool.pyforge-warden]` config, deterministic
  per-key precedence, CLI-flag override). Shipped as Story 3.1 (configurable `ConfigLoader`).
- **"Baseline & Grandfathering — new violations fixed, old ones waived with expiry"** ↔ CAP-6
  / CAP-9 ("A team can accept a risk in the open and on a clock… a committed baseline
  grandfathers existing findings so the gate blocks new findings only"). Shipped as Story 6.8
  (baseline & grandfathering, FR39).
- **"ComplianceReport Contract — versioned schema, findings, verdict, policy, timestamp,
  approver"** ↔ CAP-7 ("Each run emits a schema-validated, versioned `ComplianceReport`").
  Shipped as Story 1.1 (schema frozen) and Story 6.1 (the one sanctioned versioned
  amendment, FR38).
- **"Fix-PR Actuator — auto-creates PRs for known fixes"** ↔ CAP-12 ("A team can turn
  findings into pull requests without the tool ever writing to their working tree" —
  `--open-fix-prs`). Shipped as Story 6.9 (fix-PR actuator, FR40).

The candidate dream's Success Criteria invent specific numbers absent from the real,
already-validated Spec (e.g. "95%+ match with upstream tools," "operators define 30+
rules," "1000-dep manifest <10 sec") — restating already-shipped capabilities with
fabricated precision rather than describing any capability the real Spec doesn't already
cover. No axis, gate, or contract named in this dream falls outside the real Spec's four
live axes (hygiene/security/license/currency); the two axes the real Spec explicitly leaves
unbuilt — provenance and maintenance — are not mentioned here either, so this dream does not
even gesture at genuinely open scope. There was no new capability to specify; authoring a
second Spec for the same surface would have created a competing, driftable contract for
scope already under governance and already shipped.

## What carries forward

Nothing new — the intent this dream restates already lives in [[pyforge-warden]] and
`spec-pyforge-warden`, which is `status: shipped` (31/31 stories, PR #110). That Spec is the
canonical contract for Warden's compliance-gate capability; this record exists only so a
future reader does not re-derive the "is this new scope?" question from scratch.

## Non-goals

- **Reviving this Dream as written.** Its intent was never separate from
  `spec-pyforge-warden`'s; there is nothing here to revive.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the
  Backlog board by design.
- **Taking this Dream's content as evidence of anything about Warden's real state.** It was
  generated, not authored from firsthand investigation — treat every claim in it the way the
  Marshal retirement record treats its own sibling fabrication: "a premise handed to an agent
  is not evidence." Warden's true state is `spec-pyforge-warden`'s own `Open Questions`
  section (release-vs-story-complete; the legacy Tier-1 spec's fate; provenance/maintenance
  axis promotion) — genuine open work, none of it restated here.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent
went, without re-deriving the duplication or mistaking it for a second contract.
