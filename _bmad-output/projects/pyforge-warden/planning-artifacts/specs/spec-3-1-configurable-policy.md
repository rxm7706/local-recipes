---
title: 'Story 3.1: Configurable policy (the ConfigLoader)'
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

### Story 3.1: Configurable policy (the ConfigLoader)

As a **team lead**,
I want to tune the gate per-repo without editing the tool,
So that the gate fits our risk posture.

**Acceptance Criteria:**

**Given** a `[tool.pyforge-warden]` table in `pyproject.toml` and/or `pixi.toml`, **When** loaded, **Then** config resolves with **per-key precedence** (pyproject wins; conflicts surfaced to stderr, never fail the build) and CLI flags override (FR30).

**Given** config values, **When** applied, **Then** `--fail-on`, the CVSS thresholds, the DEP001-block confidence threshold, and the coverage-floor (`--fail-under-coverage`, default off) all move the verdict (FR18/FR19 — incl. FR19's repurposed roles: the under-`--warn-only` coverage guardrail and the ceiling on waived-away `indeterminate` surface); a config-key type error → typed `config-validation` error. **And** the hygiene→status + CVSS-threshold tables live in the `ConfigLoader`.

### Story 3.2: Auditable expiring waivers

As a **developer under deadline**,
I want to file an auditable, time-boxed exception for a finding,
So that I can ship without lying about the risk.

**Acceptance Criteria:**

**Given** `--bypass --reason "<text>"`, **When** run, **Then** a `.warden-waivers.yaml` stanza (reason + authorizer + expiry — FR24) is emitted via `safe_dump` for the human to commit — the tool **never writes the repo** (NFR-S4); the reason round-trips safely (no YAML injection). **And** a valid waiver → status `bypassed`, exit 0, `review_required: true`.

**Given** a malformed or wildcard-over-broad waiver, **When** read, **Then** it is schema-validated and rejected (FR26); waivers are least-privilege (specific id+package+ecosystem) and every applied waiver is echoed in output (NFR-S3). **And** the waiver file carries an in-file **`version:`** key; an unknown/future version is rejected with a typed error, never guessed (added 2026-07-12 per PRD CLI § contract stability).

### Story 3.3: Waiver expiry + warn-only adoption on-ramp

As a **conda/pixi maintainer adopting the gate**,
I want expired waivers to re-block and a warn-only first-run mode,
So that suppression can't rot silently and I can adopt without a day-one red wall.

**Acceptance Criteria:**

**Given** a waiver past its `expires_at`, **When** the next scan runs, **Then** the finding **re-blocks** (exit 1) and applied/expired waivers are flagged for review (FR25). *(Waiver expiry changes the input rung; `verdict.py` still owns the projection.)*

**Given** `--warn-only`, **When** run on a repo with pre-existing findings, **Then** findings surface as `warn`, exit **0**, and the report nudges how to graduate to an enforcing gate (FR23); this defends the `gate-disabled = 0` anti-metric.

## Realized in

- **Package:** `src/shared/packages/pyforge-warden/` (import `pyforge.warden`).
- **Status:** done + merged to `main`.
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
