---
title: Warden — the gate that never lies
type: dream
owner: warden
status: specified
---

# Warden — the compliance gate that never false-greens

## The Dream

The Guardian's dream: **one gate for both Python worlds** — PyPI applications
and the conda/conda-forge data stacks — interrogating every dependency across
six axes of trust (hygiene · security · license · currency · provenance ·
maintenance) and returning one honest verdict. The soul of the dream is a
negative promise: **Warden refuses to fake a pass.** An honest "not verified"
beats a false "all clear," at fleet scale (20k+ repos), without ever mutating
the host or the source.

## What it looks like when real

- One CLI, pluggable engines (deptry, osv-scanner + KEV/EPSS, license-expression,
  EOL ladders), one schema-validated ComplianceReport + CycloneDX SBOM, a frozen
  exit-code contract `{0,1,2,130}` and the verdict lattice.
- Waivers as code (expiring, committed); baselines that gate only *new* debt;
  an opt-in fix-PR actuator; the three-ring vision (consumption edge → registry
  perimeter → public upstream).

## What is real

- **43/43 stories merged** across epics 1–11
  (`_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml`),
  FR1–FR40 frozen, schema 1.1.0, honest dashboard live. Built loop-driven by
  [[pyforge-marshal]]. Epics 7–11 post-date the original v1 scope: the eligibility
  union (7), the web face (8), the PR-gate hook book + scanner plugins (9), the
  skill/persona/portal slice (10), and the two advisory lenses (11). Epic 12 was
  minted 2026-09-09 for [[golden-path-conda-blind-spot]].
- **In effect, not merely merged:** `warden scan` is the estate's sole PR verdict, and
  `scripts/platform-deploy-verify-promotion.py:31` refuses any digest whose recorded
  verdict is not `clean`.
- Spec: `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/`
  (Tier 2, `ready` — living station contract after the 2026-09-17 one-chain fold);
  `docs/specs/pyforge-warden.md` is the absorbed legacy Tier-1
  intake. Package at `src/shared/packages/pyforge-warden/`.

## Realization log

- **2026-07-15/16** — spec-first; v1 re-baselined (D12).
- **2026-07 (through 07-18)** — bmad-loop implementation to 23/31; PAUSED,
  resume at 6.3.
- **2026-07-23** — Dream retro-seeded; chapter deck `presentations/pyforge-warden/`
  (the deck-family exemplar). Registry-perimeter ring links to [[enterprise-airgap]].
- **2026-07-23 (gist audit)** — grounding: the Phase-0 deep review (47 KB), the Python Dependency Policy sketch, and the Enterprise Python Manifest (Assured-OSS lists → the vetted-base row) all pre-figure v1 (`docs/intake/gists/`).
- **2026-09-09** — Fleet readiness pass (operator-approved decision batch,
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`).
  § What is real re-grounded against the live ledger (23/31 → 43/43; epics 7–11 named).
  Realization re-confirmed under the *exercised-in-the-estate* gate rather than the merge
  gate: warden is the sole PR verdict and `platform-deploy` reads it. Two ledger-vs-in-effect
  gaps found on OTHER warden Dreams — the web face's engine import and the eligibility CLI
  — recorded on their own Dreams and Specs, not here.
- **2026-09-27 (night) — Proposed: the TEA advisory reviews the diff from the remote-tracking ref.**
  `tea_advisory` runs TEA's `tea-test-review --base origin/main`, and the CLI diffs `<base>...HEAD`
  (`cli/lib/changed-tests.js`, `cli/lib/diff-evidence.js`), so a local branch or tag named
  `origin/main` at HEAD empties the changed-test set and the advisory reviews nothing — found by
  doctor Story 31.1's review (`DW-warden-tea-advisory-short-base-2026-09-27`). **What it looks like
  when real:** warden passes `--base refs/remotes/origin/main`; a stray ref changes nothing TEA
  reviews. **Constraints:** advisory only — never a finding, a rung or the exit code; TEA's own
  default (`origin/main`) is upstream's and not changed here. Kinships: `spec-pyforge-steward`
  CAP-158 (steward's `tea-test-review` task passes the same base). Owner: warden.
- **2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin,
  and Warden scans the enterprise fleet.** Source: the intake
  `archive/docs/intake/system_architecture_specification.md` ("Automated Security Scanning & PR
  Generation Engine"), triaged 2026-09-28 under operator rulings. The intake designs a new engine:
  git objects stored inside PostgreSQL by the `gitgres` extension, `git-pkgs` Go binaries for
  manifests and PRs, CodeQL, a FastAPI/Celery orchestrator with SQLAlchemy, and a push webhook.
  **Most of it already exists here:**
  - `warden scan` covers four of six axes.
  - The CycloneDX SBOM (CAP-7) and the offline OSV database (CAP-20).
  - The scanner-plugin slots in `scanner_plugins.py`, where `ghas` is a stub.
  - The fix-PR actuator (CAP-12).
  - django-warden's Celery-driven `ComplianceJob`.
  - CFE's `scan_project.py`, which clones a repo and parses many manifest kinds.

  The real gap is the intake's Phase 4. The actuator "does NOT compute a target version" and says
  "precise target resolution + manifest editing are deferred" (`actuator.py:21-23`).
  **Operator rulings 2026-09-28** (the scope is all three):
  1. Finish Phase 4 on the estate's own repos, `local-recipes` and `python-foundry`, as draft PRs.
  2. Scan the enterprise fleet on GitHub Enterprise. This lifts two Non-goals, "Fleet
     aggregation" and "Non-Python osv-scanner ecosystems". Every fleet fix is **queued as a
     proposal**, and it opens as a PR only after the operator approves it.
  3. Mason packages the tools ([[pyforge-mason]], same day).

  **Rejected, with reasons:**
  - CodeQL: its CLI licence covers private code only with a GitHub Code Security licence. Opengrep
    (LGPL-2.1) takes the SAST slot instead, with rules the estate owns.
  - `gitgres` as the engine's git store: it has no releases and its author calls it "a neat hack
    right now". It has no delta compression, and a C extension needs a DBA grant on the
    enterprise-managed PostgreSQL. Ephemeral clones stand in. Mason packages gitgres, but the
    engine does not adopt it.
  - A second verdict: a `scan_jobs.status` of CLEAN or VULNERABLE would compete with
    `warden scan`'s exit code.
  - Webhooks: Atlas rejected them as the default trigger (`orchestration/event_source.py:17-18`).
  - A standalone FastAPI/SQLAlchemy service: the platform is one ASGI process, the Django ORM and
    Liquibase (canopy:AD-10's process topology).

  **What it looks like when real:**
  - For a `vuln:` finding, the actuator picks the lowest OSV-fixed release the estate's solver
    accepts. It edits the manifest (`pixi.toml`, `pyproject.toml` or a recipe), re-solves the
    lock, and opens a draft PR on an estate repo.
  - An opengrep plugin reports SAST findings that inform the verdict but never publish one.
  - A fleet run inventories the GHE organisation's repos and scans each one, one verdict per repo
    as today. It persists the run in a `ComplianceJob`-shaped row and queues each fix as a
    proposal, which the operator opens one at a time.

  **Constraints:**
  - No silent egress: the actuator stays the sole carve-out, and a fleet PR opens only through
    it.
  - Engines are consumed, not authored: git-pkgs, forge and opengrep arrive as conda packages with
    tested version ranges.
  - `warden scan` stays the sole PR verdict.
  - Credentials come from Steward ([[pyforge-steward]], same day).
  - Every new capability carries a flag block ([[feature-flag-governance]], same day).

  **Kinships:** [[pyforge-atlas]] (dependency history, same day), [[pyforge-mason]] (packaging,
  same day), [[pyforge-steward]] (GHE credentials, same day), CAP-7, CAP-12 and CAP-20.
  Owner: warden. → `spec-pyforge-warden` CAP-24 / Epic 14 / Stories 14.1–14.3 (FR-41), CAP-25 /
  Epic 15 / Story 15.1 (FR-42; `blocked` on mason Story 21.4), CAP-26 / Epic 16 / Stories 16.1–16.4
  (FR-43; 16.1 `blocked` on steward Story 75.1), specced 2026-09-28; the Spec's Non-goals are
  re-rendered for the two lifted by ruling 2.
  **Amended 2026-09-28 (spec pass):** finishing the fix needs the estate's solver at runtime, so the
  Spec's "never invokes pixi at runtime" now reads "except the actuator's real `--open-fix-prs` path",
  in a throwaway copy (dry-run still opens no socket); and the lifted non-Python Non-goal became its
  own story (16.4), because it is core-scan work rather than `django-warden` work.
- **2026-10-03 (Phase 4+5) — Ruled: warden's open medium and low deferrals close in one fix story.** The
  operator ruled on 2026-10-03 that the deferral burn-down's Phase 4 (open medium rows) and Phase 5 (open
  low rows) run together on the idle station lanes, then, the same day, that each station takes exactly
  one story. Warden carries 3 open medium and 8 open low rows (measured with a parser over its
  `deferred-work-ledger.md`). **What it looks like when fixed:** each eligibility result records the
  effective required authority set, so the answer is reproducible from the result alone (CAP-2); one
  package identity yields one result whose provenance keeps every observation; an unsupported CycloneDX
  `specVersion` is refused; the TEA roster refusal that landed on 2026-09-07 is pinned and its row closed;
  seven recommended follow-up reviews have run and their findings are fixed. **Constraints:** a `fix`
  story, no CAP, no flag; a row closes only with a `resolution:` and a cited `verified:` line; `warden
  scan` stays the sole PR verdict and the report schema changes additively only.
  Owner `spec-pyforge-warden`. → Epic 17 / Story 17.1, specced 2026-10-03.
- **2026-10-07 (subprocess seam) — Found: the TEA advisory spawns its own subprocess, outside `engines.py`.**
  The spine's security boundary names `engines.py` the only module that spawns subprocesses, always through
  `_engine_env()` (§ Boundary contracts; the ownership decision at `engines.py:3-12`). Since Story 11.2
  (2026-09-07, `9f2bfd9057`), `tea_advisory.py` imports `subprocess` (`:62`) and its `_default_runner` calls
  `subprocess.run` itself (`:150-:174`), so the one process warden starts for TEA skips the seam's normalized
  environment (`NO_COLOR=1`, `stdin=DEVNULL`, the typed `ErrorRecord` for a missing binary, a timeout or an OS
  failure). Measured on `8ef4a6aa79`: across `src/pyforge/warden/` only `engines.py` (`:91`) and `tea_advisory.py`
  import `subprocess`, and no module calls `os.system`, `os.popen` or `asyncio.create_subprocess_*`. The argv is a
  list and there is no shell, so it is not an injection risk. It is a breach of the rule that no test catches:
  `tests/meta/test_extract_no_execution.py` scans `extract/` only, and nothing scans the rest of the package for a
  second spawn site. The chain-currency cascade of 2026-10-07 recorded it in the spine and left it (§ Currency
  reconciliation — 2026-10-07, "One older divergence, recorded and not repaired"). **What it looks like when
  fixed:** the TEA runner spawns through an `engines.py` entry point over `_engine_env()`, as `run_pixi_lock` does
  for pixi; `tea_advisory.py` imports no `subprocess`; a meta test reds any `pyforge.warden` module other than
  `engines.py` that imports `subprocess` or calls `os.system`, `os.popen` or `asyncio.create_subprocess_*`.
  **Constraints:** a `fix` story, no new CAP, no flag. The advisory behaves as today: a note, never a finding, a
  rung or the exit code (suite:AD-4); fail-open on an environmental problem and fail-closed when the roster lacks
  `tea` (suite:AD-10); the base `refs/remotes/origin/main` (CAP-23); the injected-runner seam stays. No TEA version
  range is added (`pixi.toml` pins TEA `>=1.27.2`, open-ended, so there is no tested range to mirror). Owner:
  warden; the shipped behaviour is Story 11.2's (`spec-bmad-suite-lifecycle` CAP-4, folded on 2026-09-17 into
  `pyforge-steward:CAP-33`). → Epic 11 / Story 11.3, specced 2026-10-07; Epic 11 reopens.

## Folded Dreams (2026-09-17)

One-chain fold: satellite Dreams archived in place with `Consolidated into [[pyforge-warden]]` banners. The station Spec `spec-pyforge-warden` is `ready` and covers every owner:`warden` Dream.

- **package-inventory-eligibility** — one provenance trail and one eligibility answer (Epic 7 / reminted CAP-13..15).
- **compliance-factory-web-face** — upload a manifest, watch the engines analyze it (Epic 8 / reminted CAP-16..17). Residuals (image import, SBOM stub) stay on the absorbed memlog.
- **golden-path-conda-blind-spot** — promotion must scan the shipped closure (Epic 12 / reminted CAP-18..22).
- **pyforge-warden-compliance-gates** — already archived as a duplicate (2026-08-02); remains a retirement record.

