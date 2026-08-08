---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/research/domain-preflight-health-diagnostics-tooling-research-2026-07-25.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-doctor-2026-08-08.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/
research_type: 'domain'
research_topic: 'Preflight / health-check / diagnostics tooling — post-ship re-validation (refresh of the 2026-07-25 report)'
research_goals: 'Doctor shipped 16/16 stories since the original domain report was written. This refresh checks each 2026-07-25 domain claim against what actually shipped: which conventions held under implementation pressure, which open questions got answered and how, and whether the domain problem the report validated (scattered health signal, no single bedside manner) is actually solved by the shipped shape.'
user_name: Rxm7706
date: '2026-08-08'
web_research_enabled: false
source_verification: true
scope_note: 'REFRESH, not replacement — the 2026-07-25 report remains the source for the external-tool survey and its citations. This document re-validates its claims against the shipped codebase and the whole-build retro, and records the answers to its three Open Questions. Read the 07-25 report first for the survey; read this for what reality did to it.'
---

# Research Report: Domain Refresh — Preflight / Health-Check / Diagnostics Tooling (Post-Ship)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Domain (refresh — validates the 2026-07-25 report against the shipped build)

---

## 1. Verdict summary: every load-bearing domain convention held

The 07-25 report extracted six domain conventions from `brew`/`flutter`/`npm doctor`,
Renovate, and Dependabot. All six survived contact with implementation, most of them
enforced structurally rather than by discipline:

| 07-25 domain claim | Post-ship status | Evidence |
|---|---|---|
| Read-only, non-mutating by default | **HELD, enforced** | NFR-1 read-only guard is an AST meta-test from Story 1.1, extended in its first review pass from `Name`-form `open(...)` to attribute-form `Path(...).open("w")` (retro §harder). No `--fix` shipped anywhere. |
| Modular, individually-nameable checks | **HELD** | `checks/registry.py`; `monitor --watch` axes validated against the public `VALID_WATCH_AXES` set; `--source` filtering on the fleet surface. |
| Tri-state, not binary | **HELD, and it earned its keep** | `DoctorStatus` {OK, WARN, FAIL} in models.py. The shipped normalizers use all three states with real semantics: e.g. cve `delta > 0` → FAIL, other drift → WARN; `feedstock_bad` → FAIL vs. `stuck` → WARN; cadence `silent` → FAIL vs. `decelerating` → WARN. A binary model could not have expressed any of these splits. |
| "Operability, not policy" exit-code split | **HELD wholesale** | Adopted from warden's `--doctor` contract per the technical report; `doctor check`'s exit code answers "is the machine sound," and the diagnose-side Partition enum carries the policy-flavored states instead. |
| Fleet aggregation: atlas already IS the data model Renovate users hand-roll | **CONFIRMED — the report's strongest prediction** | `monitor --fleet` shipped four axes with zero new data pipeline; every axis reads existing atlas tools (staleness_report, cve_watcher, feedstock_health, release_cadence, adoption_stage, version_downloads) over MCP-or-CLI. |
| Prescription ranking: multi-signal, explainable, partition-before-rank | **HELD** | prescribe.py ships partition (ACTIONABLE/BLOCKED/ACCEPTED_RISK) → rank (KEV × EPSS × blast-radius, `rank_factors` per item) → named root cause → single-hop safe-upgrade with always-paired reason. |

One convention the report cross-validated from the Kubernetes ecosystem — the
check/monitor/diagnose split as three distinct contracts with distinct consumers
(readiness/liveness/targeted-diagnosis, `kubectl preflight` vs. `support-bundle`) —
is now empirically supported from inside the build too: the three verbs shipped as
separate epics with separate FRs and never collapsed into one flag-parameterized
command, and the `DoctorReport` envelope enforces the difference structurally
(`prescriptions` is *required* for `diagnose` and *forbidden* — omitted, never null —
for `check`/`monitor`; models.py `__post_init__`).

## 2. The 07-25 Open Questions — all three answered by the build

1. **"Should `check` expose `--list-checks`-style introspection?"** — Answered yes in
   spirit: checks are registry-addressable and watch axes are a public named set
   (`VALID_WATCH_AXES`), matching the `brew doctor --list-checks` convention the report
   predicted would be "likely yes, low cost."
2. **"Persistent Renovate-style surface, or CLI-only for v1?"** — Answered in two stages,
   exactly as the report's framing allowed: v1 shipped CLI/JSON-only; the persistent
   surface then graduated from non-goal to FR-11 in the 2026-08-02 dream-consolidation
   pass and shipped in Epic 4 as `fleet_surface.py` (Story 4.2), including a
   review-hardened subtlety the report could not have anticipated — the surface records
   which axes are *genuinely represented after `--source` filtering*, recomputed via
   `AXIS_SOURCES`, not the requested `--watch` list verbatim (sources/atlas.py).
3. **"Is a hard-coded credential-scope violation always `fail`, or `warn` in some
   enterprise configurations?"** — Resolved by shipping the env-hygiene scanner
   (checks/env_hygiene.py, Story 1.4) with per-finding tri-state semantics rather than a
   category-wide answer. The harder domain lesson landed elsewhere: the *scanner itself*
   was the build's most review-intensive component (guard-polarity blindness found twice
   in the same function by two independent adversarial passes — retro §harder). The
   domain-level takeaway for any future hygiene-shaped check: conditional-suppression
   logic needs polarity-both-directions test design from day one, which no surveyed
   external doctor tool documents because none of them attempts credential-flow analysis.

## 3. Domain re-validation of the MCP-first/CLI-fallback pattern (the shipped novelty)

The 07-25 report treated transport as an implementation detail. Post-ship, Doctor's
MCP-first/CLI-fallback shape (AD-6) deserves domain-level standing, because it is the
one shipped pattern with no direct analogue in the surveyed doctor-tool landscape (all
of `brew`/`flutter`/`npm`/`conda doctor` probe their environment directly):

- **The pattern was designed once and reused three times without divergence**: Story 2.1
  proved it on the staleness axis; 2.2 extended it verbatim to cve + the abandonment
  composite; Story 4.3 (adoption) reused the identical `_fetch_rows`/`_FetchFailed`/
  degrade machinery with zero new exception classes and zero new swallow sites (retro
  §went-well). That is a 3-for-1 return on one reviewed shape — strong evidence the
  domain problem ("one gather contract over N heterogeneous instruments") is real and
  that this is a right-shaped answer to it.
- **Its degrade semantics are the Nagios lesson, arrived at independently**: every
  (sub-)instrument failure becomes exactly one FAIL Finding tagged with its own Source;
  a composite axis's sub-calls degrade independently (partial, never all-or-nothing).
  A diagnostics tool that dies when one instrument is unreachable would fail its own
  domain — Doctor's whole purpose is to survive and report on a broken environment
  (sources/warden.py module docstring states this as doctrine).
- **"MCP available" is operationalized as attempt-and-fall-through, not detection** —
  there is no reliable ambient signal for "an MCP host is present" from a plain library
  call, so every call attempts the stdio session and any failure at any stage falls back
  to CLI transparently. This is a domain finding worth carrying to other stations: any
  sibling wanting MCP-first behavior should copy attempt-first, not invent detection.

## 4. Is the domain problem actually solved?

The original problem statement — "five instruments, reconciled by hand, no single
bedside manner" — is structurally solved: one CLI, three verbs, one schema-versioned
`DoctorReport`, `--json` everywhere, and the operator habit the PRD aimed for
("run `doctor check` first") is now mechanically cheap (5-second budget, NFR-4, with a
review-hardened benchmark that asserts a minimum findings count so "broken-and-therefore-
fast" cannot pass — retro §went-well). What is *not yet* demonstrated is the
adoption half of the domain claim: Marshal running `doctor check` unprompted before every
factory spin-up (PRD §1's success criterion) is wiring that lives outside Doctor's own
16 stories. Until that lands, Doctor is a shipped instrument awaiting its institutional
habit — the domain survey's own warning applies (a pre-flight tool only pays off when it
is invoked by default, as `brew doctor` is by Homebrew's own CI).

## Assumptions

- The 2026-07-25 external-tool survey and its 26 sources are treated as still-valid and
  are not re-fetched; nothing in the shipped build contradicted any of them. New external
  grounding (conda doctor's plugin/fix system, Datadog's CLI verb split) lives in the
  2026-08-08 market report, not duplicated here.
- "Post-ship" = PRs #156, #162, #167, #290, #299, #303 merged; retro of 2026-08-08 is
  the terminal build artifact.

## Open Questions (fresh)

- Who owns wiring `doctor check` into Marshal's pre-spin sequence, and does that story
  belong to Doctor (a v1.x story) or Marshal (a policy/config change)? The domain
  evidence says the value is unrealized until this exists.
- The reactive use case the 07-25 report asked to document ("run `doctor check` after a
  build failure to see if it was environmental") shipped as capability but not as
  documented habit — worth one paragraph in Doctor's README/skill surface rather than a
  code change.
- Should the attempt-first MCP-availability idiom (§3) be written up as a cross-station
  reference (it now exists in Herald-remote and Doctor-local variants), or left as
  per-package docstring doctrine until a third consumer appears?

## Sources

- `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/domain-preflight-health-diagnostics-tooling-research-2026-07-25.md` (the base report this refreshes; external citations live there)
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/retros/retro-doctor-2026-08-08.md`
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` (tri-state, envelope verb-coupling), `sources/atlas.py` (per-axis semantics, degrade contract, `AXIS_SOURCES`), `sources/warden.py` (degrade doctrine), `prescribe.py` (partition→rank→root-cause→safe-upgrade), `fleet_surface.py` (FR-11), `checks/env_hygiene.py` (FR-3)
- `docs/dreams/pyforge-doctor.md` §Realization log; `_bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md` (currency_review 2026-08-02)
