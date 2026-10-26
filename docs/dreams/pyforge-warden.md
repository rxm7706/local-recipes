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
- **2026-10-11 — Ruled: the fleet is an operator-designated github.com organisation, read through the operator's
  `gh` login, and never named in a tracked file.** Story 16.1 was minted for a GitHub Enterprise host, with steward
  Story 75.1's credentials. On 2026-10-11 the operator designated the fleet instead: an organisation on github.com,
  its repos, and the items of two of its GitHub Projects (v2). **Rulings** (the Spec memlog records them verbatim,
  with the names redacted):
  1. Inventory the whole organisation plus the items of the two designated projects: the widest scope. The project
     items are a second story.
  2. This repository is public, so no tracked file names the organisation, its repositories or its projects. The
     names live only in a gitignored local config, the exports are gitignored and never committed, and tests use
     fictional fixtures.
  3. The live run reads through the operator's existing `gh` login at run time. No token is copied into
     `steward keys` or any file.

  github.com is now the designated host, not a stand-in. That supersedes the 2026-10-10 "no github.com stand-in"
  condition for this work; its other conditions stand. **What it looks like when real:** the inventory lists every
  repo of the designated organisation, and every item of its designated projects, into gitignored JSON exports. It
  reads only, through REST `GET` and GraphQL `query`, and takes the token from `gh` at run time, holding it in memory
  only. **Constraints:**
  - The client enforces read-only, because the login's `repo` scope is not read-only on its own.
  - Fixtures name `example-org`.
  - A leak-guard test keeps the target's names out of the fleet's tracked paths.
  - Steward 75.1 stays on main as the path for a future GitHub Enterprise target.
  - A live fleet run (16.2) or an approved proposal (16.3) on this organisation needs a credential ruling of its
    own.

  Owner: warden; `spec-pyforge-warden` CAP-26 (FR-43). → Story 16.1 re-scoped (key kept) and Story 16.5 minted,
  specced 2026-10-11.
- **2026-10-11 (leak guard terms) — Ruled: the leak guard forbids the listed repository and project names
  everywhere, and the organisation's name only in warden's own files.** Story 16.1's leak guard (its AC9, in
  `src/platform/tests/test_warden_fleet_inventory.py`: `_leak_guard_terms()` and
  `test_leak_guard_no_operator_terms_in_tracked_tree`) always adds the configured organisation's name to its forbidden
  terms, beside the `leak_guard_terms` listed in the gitignored `.warden/fleet-target.toml`. Story 16.5, landing as
  PR #2146, widens the scan to every file the branch changes. On 2026-10-11 the orchestrator checked, against the
  operator's real configuration kept outside the repository, that the organisation's name appears in 31
  operator-authored tracked files that predate warden: Dreams, research notes, links to public repositories under that
  organisation, and a `gh` inventory note. The organisation is public. What must stay private is that warden
  inventories it, and which of its repositories and projects. With the real configuration present, the guard fails on
  each of those files it scans, so it cannot widen to the whole tree, and any story that edits one of them goes red.
  **Operator ruling 2026-10-11** (AskUserQuestion; the chosen option's label and text, verbatim): "Drop org from terms
  (Recommended)", "The org is already public in your own docs; what must stay private is that warden inventories it,
  and which repos and projects. The guard forbids only the leak_guard_terms you list (repo and project names) plus the
  org name in warden's own files (pyforge-warden, django-warden, warden specs and memlogs). A small warden fix story."
  **What it looks like when fixed:**
  - Each listed term is forbidden in every tracked file and in every file the branch changes.
  - The organisation's name is forbidden in warden's own files, and in any entry of a shared log (team memory, or
    another Spec's memlog) that names warden.
  - The organisation's name anywhere else passes.
  - A configuration with no listed terms is refused unless the operator opts in, so the guard never passes on nothing.

  **Constraints:**
  - A `fix`: no CAP, no flag. The guard's test and the config reader change; the inventory does not.
  - Fixtures stay fictional (`example-org`), and no tracked file, commit message or PR body names the target.
  - The live guard runs only where the operator's configuration is. The orchestrator runs it against the real
    configuration before landing.

  Kinships: Story 16.1 (AC9) and Story 16.5 (the changed-files scan); the guard's file is also on steward's
  `spec-pyforge-unifying-strategy` surface. Owner: warden; a defect against `spec-pyforge-warden` CAP-26 (FR-43).
  → Epic 18 / Story 18.1, specced 2026-10-11.
- **2026-10-25 (the PRD's FR arrows were mapped by subsection, not traced) — Found: four of the warden PRD's FR
  arrows are wrong or missing.** A fleet audit of every station PRD's `FR-n ← CAP-m` arrows, run after marshal Story
  105.1 found marshal's counted rather than traced, read all 41 warden arrows. The 2026-09-17 fold (`548e907247`) gave
  each requirement bullet the capability of its subsection. FR-11 (an offline vulnerability database with its snapshot
  time) and FR-12 (a stale database routes to `indeterminate`) read CAP-4, although CAP-11, air-gapped operation, states
  both almost word for word. FR33 and FR35, the license and currency gate flags, are spelled without the hyphen, so the
  fold skipped them and doctor's `fr-without-cap` cannot see them. **What it looks like when fixed:** FR-11 and FR-12
  read CAP-11, CAP-4; FR33 and FR35 read CAP-5, tunable policy, and keep their spelling. **Constraints:** a chore under
  `spec-one-chain-per-station` CAP-5 (FRs derive from CAPs) and CAP-3 (the station fold procedure); no CAP, no flag, no
  `SPEC.md` change; no detector rule changes; renaming FR33 and FR35 needs its own ruling. Operator ruling, 2026-10-25:
  "Do rows 1-5 in one PR". Owner `spec-pyforge-warden`. → Epic 19 / Story 19.1, specced 2026-10-25. **Amended the same
  day (the independent review; operator ruling "Apply all (Recommended)"):** FR-34 and FR-36 read CAP-4, CAP-11 (their
  cached feeds and snapshot provenance are CAP-11's), and FR35 reads CAP-5, CAP-11 (its freshness precondition).

## Folded Dreams (2026-09-17)

One-chain fold: satellite Dreams archived in place with `Consolidated into [[pyforge-warden]]` banners. The station Spec `spec-pyforge-warden` is `ready` and covers every owner:`warden` Dream.

- **package-inventory-eligibility** — one provenance trail and one eligibility answer (Epic 7 / reminted CAP-13..15).
- **compliance-factory-web-face** — upload a manifest, watch the engines analyze it (Epic 8 / reminted CAP-16..17). Residuals (image import, SBOM stub) stay on the absorbed memlog.
- **golden-path-conda-blind-spot** — promotion must scan the shipped closure (Epic 12 / reminted CAP-18..22).
- **pyforge-warden-compliance-gates** — already archived as a duplicate (2026-08-02); remains a retirement record.

- **2026-10-26 (every requirement derives from a capability) — Found:** the 2026-09-17 fold cut 10 of the Spec's intent and success bullets at their first line and dropped the bullets of CAP-13..CAP-17 (shipped 2026-08-22) entirely; none of the 23 lettered NFR lines cites a capability, and the detector could not read a lettered id at all (five of them, `NFR-R3a`, `NFR-R3b`, `NFR-P-warm`, `NFR-P-cold`, `NFR-P-concurrency`, are spelled outside the grammar and now surface as `fr-id-malformed`). **Ruled** (2026-10-26, operator, fleet-wide: "yes forbid it" — a requirement cites one or more defined capabilities and nothing else; `spec-one-chain-per-station` CAP-5 as amended, CHAIN-STANDARD § 12). **For warden:** the text is restored by script from `548e907247^` with every id stable; the NFR backfill is minted `backlog` as Story 20.2 (ruling (c)) so the detector baseline has an owner for every warden row it carries. Epic 20 / Story 20.1, built in the one-PR effort with the other seven stations; no warden CAP minted, no requirement changes.
