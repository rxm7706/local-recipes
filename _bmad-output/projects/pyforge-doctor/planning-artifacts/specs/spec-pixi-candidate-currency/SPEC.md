---
id: SPEC-pixi-candidate-currency
status: ready   # added 2026-09-09 (doctor-B6): the key was absent, which is the only reason
                # chain-completeness reported ok — all five CAPs are uncovered by any doctor
                # epic or FR, so an open status fires spec-not-decomposed. CAP-1/2/3/5 are
                # satisfied by the Dream's ledgers; CAP-4 is the one code capability, and it
                # is decomposed into exactly one doctor story.
owner-dream: docs/dreams/pixi-candidate-currency.md
companions:
  - ../../../../../../docs/dreams/pixi-candidate-currency.md
surface:
  - pixi.toml
  - pixi.lock
  - .claude/data/conda-forge-expert/
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/**
---

> **Canonical contract.** This SPEC and the companion `docs/dreams/pixi-candidate-currency.md`
> (adopted — the live ledgers themselves, owned and updated by whoever runs the audit, not
> by this Spec) are the complete, preservation-validated contract for what to build,
> validate, and keep current.

# Every pixi.toml dependency carries a live, re-checkable reason — never a silent guess

## Why

A pain to solve. `pixi.toml`'s commented-out candidates and `pixi.lock`'s below-latest
active dependencies had accumulated with no tracked answer to "is this blocked, dead, or
just never checked" — the same question got re-derived from scratch every time it came
up (this repo's own session history: `caveman`, `headroom-ai`, `codegraph`, `click`, and
the `dbt-*` trio each cost real investigation to answer once). A first full audit (2026-08-30)
answered it for 44 candidates and 149 below-latest actives with real solver/repodata
evidence, then grew two more axes the same day and the next: which active dependencies
come from a non-conda-forge channel or bare PyPI (30 + 1), and which have no external
tracking item on OpenTeams-WFT-CDO's own conda-forge-packaging board (135 genuine gaps of
197 checked). The risk this Spec closes is not the audit itself — it's the audit decaying
into another one-time snapshot, the exact failure mode `[[chain-currency-sweep]]` already
exists to prevent for planning-spine artifacts, applied here to a dependency ledger instead.

## Capabilities

- **CAP-1 — SATISFIED by the Dream's ledgers, not by code**
  - **intent:** Every commented-out `pixi.toml` candidate carries exactly one of five
    dispositions — blocked (names a re-check trigger), archived (upstream dead), stale
    (dead duplicate/superseded), ready (verified clean), unexamined (the honest default).
  - **success:** Every one of the Dream's 44 candidates already carries one; a newly
    commented-out candidate with no disposition is the detectable gap this contract names.
- **CAP-2 — SATISFIED by the Dream's ledgers, not by code**
  - **intent:** Every active dependency below its conda-forge latest, after a
    `pixi update --dry-run` re-solve rules out a merely stale lock, carries blocked /
    platform-gap / deliberate-tradeoff / undiagnosed, naming the exact upstream package and
    `depends`/`constrains` spec read off an actually-resolved build — never "something
    conflicts."
  - **success:** A shared root cause blocking several packages at once (e.g. one feedstock
    pin) is recorded once and every dependent package cites it, not re-derived per package.
- **CAP-3 — SATISFIED by the Dream's ledgers, not by code**
  - **intent:** Every active dependency not resolved from conda-forge (SelfExplainML or
    bare PyPI) carries permanent-by-necessity / pending-conda-forge-submission /
    needs-recheck, cross-referenced against the owning `recipes/<name>/`'s own
    `cfe-on-conda-forge-status` where one exists.
  - **success:** A recipe flagged `confirmed-on-conda-forge` whose package still locks from
    SelfExplainML (found live 2026-08-31: `fastmcp`, `slowapi`) is flagged `needs-recheck`,
    never silently accepted as consistent.
- **CAP-4 — the one code capability; decomposed as a single doctor story**
  - **intent:** A `pyforge-doctor`-owned advisory check reads each ledger's own recorded
    verification date and flags when it exceeds a declared staleness threshold — the same
    `gather`/finding pattern `chain_currency_sweep_check` already uses, advisory only, never
    a second PR gate (Warden doctrine, fleet-wide).
  - **success:** A ledger last verified beyond the threshold produces a named finding;
    re-running the audit and updating the recorded date clears it; the threshold is a
    declared policy value, never a hardcoded magic number.
- **CAP-5 — SATISFIED by the Dream's ledgers, not by code**
  - **intent:** Every active dependency lacking a corresponding `[Conda-Forge Packaging]
    <name>`-shaped tracking item on OpenTeams-WFT-CDO's own project board carries
    visibility-gap-with-recipe (real packaging debt, invisible externally) or
    visibility-gap-unverified (no local recipe, plausibly already fine upstream) — a
    distinct axis from CAP-1..3's packaging/currency dispositions.
  - **success:** Base conda/pixi ecosystem infra and this repo's own `pyforge-*` packages
    are excluded by construction, never miscounted as candidates; an external-tracking gap
    is never treated as a packaging verdict on its own.

## Constraints

- **A `blocked` disposition must name what would unblock it** — the difference between this
  ledger and the status quo is a re-check with a named trigger, not requiring someone to
  remember to look.
- **Don't re-derive a shared root cause per package.** One investigation, not N.
- **Trust local `cfe-*` metadata as a hint, never ground truth** — evidenced live (the
  `langflow` entry drifted stale within a single session). CAP-1..3 dispositions are always
  verified against `pixi.lock`/repodata/a real solve, never against the metadata field alone.
- **CAP-4's staleness check is advisory only, never a second PR gate** — the fleet-wide
  Warden doctrine every other doctor-owned check already follows.
- **CAP-4's threshold is a declared policy value**, never a magic number inside the check
  module; `verdict.exit_code_for` stays the sole verdict owner.

## Non-goals

- **Not a commitment to add any specific candidate, or unblock any specific active
  dependency.** Disposition is separate from remediation — a separate call per finding.
- **Not re-litigating conda-forge submission strategy** for recipes already
  `pending-approval`/`pending-submission` — that stays the recipe's own
  `cfe-on-conda-forge-status` lifecycle.
- **Not a commitment to fix any of the 33 version-currency terminal-package findings**, or
  to file any of the CAP-5 external-tracking gaps upstream — each stays a separate call.
- **Not a merge of this environment-dependency ledger with per-recipe
  `cfe-on-conda-forge-status` metadata.** They cross-reference (CAP-3) but stay two
  separate concerns: the environment graph vs. submission status.

## Success signal

An operator (or agent) asking "why isn't `X` in the environment" or "why is `Y` stuck below
latest" gets a cited answer from the ledger in seconds, not a re-derived investigation — and
that answer is demonstrably still current, not a decayed snapshot, because CAP-4's staleness
check would have flagged it otherwise.

## Assumptions

- CAP-1/CAP-2/CAP-3/CAP-5 are contracts over the Dream's four ledgers — they are met by
  those ledgers carrying the dispositions, not by any module, and are therefore not
  decomposed into stories. CAP-4 is the only capability that becomes code.
- The ledger is already drifting, which is what CAP-4 exists to catch: the Dream audited 44
  candidates over 64 commented dependency lines; `pixi.toml` now carries roughly 62 (a
  looser regex over the same file returns 66 — the exact figure is the implementing story's
  to settle), with 45 commits to `pixi.toml` since the last currency pass. Without CAP-4 the
  Success signal above is false.
- CAP-4's exact mechanism (a new `pyforge.doctor.sources` check module vs. extending an
  existing one) is left to implementation — the Dream and this kernel constrain its
  *behavior* (advisory, named threshold, per-ledger verification date) not its file layout.
- The staleness threshold's actual value is not set here — a reasonable default (e.g. 30
  days, matching this fleet's existing per-station verification-freshness convention) is an
  implementation decision, not a kernel-level commitment.

## Open questions

- Whether CAP-4's check should also age-check individual *findings* within each ledger
  (per-package) or only the ledger's own top-level "last audited" date — the Dream's three
  (now four) audit passes were each whole-ledger sweeps, not per-finding re-verifications,
  so a per-finding cadence is unproven at this scale.
