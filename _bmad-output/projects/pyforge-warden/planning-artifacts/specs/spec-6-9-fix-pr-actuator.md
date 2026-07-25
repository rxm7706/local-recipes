---
title: 'Story 6.9: Fix-PR actuator (opt-in remediation PRs)'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap; dev-notes / review-triage-log not recovered'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec file was
> lost when its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed on
> worktree teardown. This file **recovers the load-bearing contract** — the Intent and
> Acceptance Criteria below are lifted **verbatim** from the tracked, authoritative
> `planning-artifacts/epics.md` (the source the original spec was derived from), and the
> Realized-in section maps it to the shipped implementation on `main`. What is **not**
> recovered: the original implementation dev-notes and the review-triage log (those lived
> only in the lost file). Behaviour is verified by the current green suite; the story is
> done and merged.

## Contract (from epics.md — verbatim, authoritative)

### Story 6.9: Fix-PR actuator (opt-in remediation PRs)

As a **platform engineer running the gate at fleet scale**,
I want findings to open remediation PRs automatically when I opt in,
So that the gate drives fixes, not just red builds (FR40 — D12).

**Acceptance Criteria:**

**Given** `--open-fix-prs` with forge credentials provided via environment (never flags), **When** the verdict has been composed (exit code fixed), **Then** `cli.py` — the sole invoker — runs the actuator, **then** assembles + emits the final report including the `actuation` section (6.1's slot; content in the NFR-R3b volatile-field set): order = compose verdict → actuate → assemble → emit. PRs open via the forge API — security findings → upgrade-to-fixed-version PRs; hygiene unused-dependency findings → removal PRs — with the finding ID + report excerpt in the PR body. **And** the scanned working tree is **never written** (NFR-R3a asserted by the harness); the actuator is the **only** component permitted forge egress, and the C0c socket-deny carve-out applies **only to the real path under the flag** (landed in this story, never a global loosening), inert without the flag.

**Given** `--fix-prs-dry-run`, **When** the actuator runs, **Then** it shares the real code path up to the egress seam, writes its intent into the same `actuation` report section (stdout stays ONE pure document, NFR-I3), and **opens no sockets** (the carve-out does not apply to dry-run). **And** a failed PR-open is recorded in the `actuation` section + stderr — **never an FR20 rung**; verdict, status, and exit code unchanged. **And** duplicate protection: an existing open PR for the same finding ID is detected and skipped, never re-opened.

### Story 6.10: Amendment design spike — finding-ID families, verdict encoding, rung-discriminator & fold semantics (decision record)

As the **owner of the one sanctioned schema amendment**,
I want the amendment's unspecified shapes pinned in a decision record before 6.1 freezes them,
So that the HARD-gate story is a mechanical schema bump, not design work on the critical path (the story-1.4 spike precedent).

**Acceptance Criteria:**

**Given** the 6.1 scope list, **When** the spike completes, **Then** a committed decision record (planning-artifacts) pins: the **license/currency finding-ID family grammars** (single-line, colon-delimited, injective — same rules as the three shipped families) and the **typed verdict encoding** (schema-validated fields policy/waivers/baselines key on); the **suppression rung-discriminator** shape (a closed `baseline | waiver` marker on echoed suppressions); and the **Gap-B merge/fold table** for every new `Component` field (conservative C0 semantics per field, `_merge_group`/`_fold_bare` positions named).

**Given** the decision record, **When** 6.1 executes, **Then** 6.1 implements it without new design decisions — 6.1 remains the sole schema writer and the HARD gate (one amendment, one bump; this spike changes no code and no schema).

## Realized in

- **Package:** `src/shared/packages/pyforge-warden/` (import `pyforge.warden`).
- **Status:** done + merged to `main` — recovered from stalled run + adversarial review; merged 1f62e8b432 (1840 green)
- **Verification:** the shipped behaviour for this story is covered by the current
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` suite (green on `main`).
  For the precise file-level Code Map, read the implementation on `main` — this
  regenerated spec deliberately does not guess a per-file map it cannot verify from the
  lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Root cause: story specs lived in Tier-3
gitignored `implementation-artifacts/`; they are now tracked here in
`planning-artifacts/specs/` so they survive worktree teardown and are in every clone.
