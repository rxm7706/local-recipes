---
title: 'Story 6.4: KEV feed provisioning, enrichment & the `--fail-on-kev` gate'
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

### Story 6.4: KEV feed provisioning, enrichment & the `--fail-on-kev` gate

As a **security engineer**,
I want the gate to block known-exploited vulnerabilities with honest feed semantics,
So that a KEV listing can never be silently missed (FR36).

**Acceptance Criteria:**

**Given** a provisioned KEV feed (cache layout, lifecycle, and max-age policy documented — the OSV-DB provisioning decision record `osv-db-offline-provisioning-decision.md` is the template), **When** a security finding matches a KEV-listed advisory on a pinned version, **Then** the finding carries `kev: true` (+ `kev_date` post-6.1) and the verdict blocks (`--fail-on-kev` is in the FR18 default) — exit 1. **And** this story delivers the **`feeds.py` skeleton** (ONE cache layout + ONE provenance shape + staleness/max-age defaults living in `feeds.py`, overridable only via the FR30 ConfigLoader) that 6.3 and 6.7 consume — axes never compute staleness. **And** KEV/EPSS enrichment mutates findings at exactly one pipeline position: inside the vuln producer, before policy dedup. **And** this story ships a **hermetic fixture KEV feed** (the 1.4 fixture-DB precedent) wired into the test harness, so the default-on `--fail-on-kev` policy never flips shipped E1/E2 fixtures to `indeterminate`. **And** the KEV tier's opt-out is named and testable: the FR30 config key `policy.fail_on_kev = false` (config/table-driven — the coarse `--no-fail-on-*` flag family stays retired), which makes the no-KEV-policy branch reachable.

**Given** an absent or stale KEV snapshot **while a KEV-blocking policy is in effect**, **When** the scan runs, **Then** the verdict is **`indeterminate` with a KEV-provenance driver** — the gate never silently no-ops (the review-T1 fix). **And** with **no** KEV policy in effect, null slots gate on CVSS as before. **And** the report's per-feed KEV provenance (`{source, snapshot_at, max_age_ok}`) makes `kev: null` (feed absent) distinguishable from "assessed, not KEV-listed". **And** feed fetch is offline-default / opt-in-online / never silent (NFR-S2).

### Story 6.5: Two-mode policy integration (unconfigured visibility + flag-activated gating)

As the **owner of the never-false-green invariant**,
I want unconfigured-axis verdicts visible without blocking AND configured axes gating in the same release,
So that `gating: false` is honesty, not invisibility, and a configured policy actually blocks (FR37 + FR33/FR35 — D12).

**Acceptance Criteria:**

**Given** an axis with `gating: false` (unconfigured license/currency), **When** a component's verdict is `unknown`, `denied`, or `eol`, **Then** the policy feeds a **`warn` rung** whose driver names the axis + finding — status `warn` (not `clean`), exit 0 — and a clean run on gating axes with any non-gating unknowns can never render status `clean`. **And** `--warn-as-error` escalates these to non-zero for strict shops. **And** this story **solely owns the escalation mapping** for axes 3/4 (producers are meta-tested to never feed above `warn`; both modes proven by running the identical fixture set and diffing only rungs/exit). **And** the tighten-only rule is applied as redefined by the architecture (2026-07-16): the shipped 1.2 `indeterminate` backstop is a **placeholder, not a floor** — the axis's defined mapping (warn unconfigured / gate configured) supersedes it for that axis; the C0 bound (never toward `clean`) is the invariant; verdict.py sole-ownership guard passes.

**Given** an axis whose policy flags are configured (FR33/FR35 — v1, D12), **When** `gating` flips true for that axis, **Then** the same outcomes escalate (`denied`/`eol` → `policy-violation`, `unknown` → `indeterminate`) **with no producer changes** — the escalation is a policy-table change only, proven by running the identical fixture set in both modes and diffing only the rungs/exit.

### Story 6.6: Engine version-range pinning (the distribution gate)

As the **release owner**,
I want the engine run-deps constrained to tested version ranges,
So that publishing can't ship the fleet-wide false-error the ranges exist to prevent (NFR-C1).

**Acceptance Criteria:**

**Given** `src/shared/packages/pyforge-warden/pixi.toml` (run-deps `deptry = "*"`, `osv-scanner = "*"` today), **When** this story lands, **Then** both engines carry a **tested version range** (per NFR-C1: a range, not an exact pin — the engines come from feedstocks), the range choice is recorded with its compatibility evidence (deptry output schema; osv `--format json` shape + exit-code contract), and an out-of-range engine at runtime fails loud via FR21's typed `engine-unavailable`/incompatible error. **And** internal JFrog v1 publish and public v1.x publish are both blocked until this story is DONE (the D6 gate) — encoded mechanically as a release-gate row in `sprint-status.yaml` and a checkbox in the spec DoD (its mechanical homes, not process prose). **And** the story is the recorded owner of `pixi.toml:32-33` — closing the review-T-a finding that no story owned the mitigation. **And** the standing cross-cutting gates hold (C0 fixtures unaffected by the range change; twice-run determinism NFR-R3b).

### Story 6.7: EPSS feed + the `--min-epss` gate

As a **security engineer prioritizing by exploit likelihood**,
I want EPSS scores on findings and a probability-threshold gate with honest feed semantics,
So that exploit-likely vulnerabilities block and a missing feed can never fake a pass (FR36 — D12).

**Acceptance Criteria:**

**Given** a provisioned FIRST EPSS feed (cache layout, lifecycle, max-age policy — story 6.4's KEV feed work is the direct template, one shared `feeds.py` layer; this story builds no private cache and computes no staleness itself), **When** a security finding matches, **Then** it carries `epss {score, percentile}` (post-6.1 schema) with per-feed provenance `{source, snapshot_at, max_age_ok}`, and `--min-epss <0..1>` blocks at/above the threshold (`policy-violation`).

**Given** an absent or stale EPSS snapshot **while `--min-epss` is set**, **When** the scan runs, **Then** the verdict is **`indeterminate`** with an EPSS-provenance driver — the mirrored FR-K1 absence rule: an active policy never silently no-ops. **And** with no `--min-epss` set, null `epss` slots change nothing (CVSS/KEV gate as before). **And** feed fetch is offline-default / opt-in-online / never silent (NFR-S2).

### Story 6.8: Baseline & grandfathering (gate new findings only)

As a **maintainer adopting the gate over existing debt**,
I want to accept today's findings in a committed, expiring baseline and block only new ones,
So that day-one debt doesn't force disabling the gate — and nothing is silently suppressed (FR39 — D12).

**Acceptance Criteria:**

**Given** `--baseline .warden-baseline.yaml` (committed, schema-validated — malformed → typed `config-validation` error, never a guess), **When** the scan runs, **Then** findings whose **stable finding IDs** (the full finding-ID grammar — 1.1's three families **plus 6.1's license/currency families**; the same key waiver matching uses) appear in the baseline do not block; **NEW findings gate normally**; every applied baseline entry is **echoed in the report** carrying the 6.1 **suppression rung-discriminator** marking it `baseline` (vs `waiver`) — loud, `bypassed`-style; C0 holds: a baselined run can never render `clean`, and the baseline can never mask an `error`.

**Given** a baseline entry past its `expires_at` (waiver-identical semantics), **When** the scan runs, **Then** the finding **re-blocks** until fixed or re-accepted. **And** the tool only ever **reads** the baseline (NFR-R3a/S4); `--baseline-emit` prints a candidate stanza for the human to commit — the tool never writes the repo. **And** baseline entries are a **second input to 3.2's suppression engine** — one engine, no parallel suppression path; baseline + waiver interaction is deterministic (waiver wins where both match — one suppression, echoed once, discriminated per 6.1).

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
- **Status:** done + merged to `main` — feeds.py substrate + KEV enrichment + fail-on-kev gate; 1334 tests green (canonical --frozen, re-verified on branch); merge 3de107081e; dev×2 (dev-1 left spec status=in-review → benign rollback+retry)
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
