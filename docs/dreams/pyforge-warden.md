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
- **2026-10-26 (planning artifacts outside the one-chain shape) — Found:** the `status: archived` Spec folder `spec-pyforge-warden-compliance-gates` (retired 2026-08-02 as a duplicate; a retirement record) still sat under the station `specs/` directory, the one warden path the 2026-10-26 re-audit of the one-chain rule on main `97c8211773` listed. **What it looks like when fixed:** the folder sits at `archive/_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden-compliance-gates/` with its memlog (`spec-one-chain-per-station` CAP-11; CHAIN-STANDARD § 11), moved by `git mv`, nothing deleted; the chain-sprawl baseline shrinks by one; the station `specs/` directory holds the station Spec, the absorbed folders and `spec-<E>-<S>-<slug>.md` story specs only. **Constraints:** a chore under `spec-one-chain-per-station` CAP-11; no CAP, no FR, no AD, no `SPEC.md` change; the moved files' text is untouched; the Dream `docs/dreams/pyforge-warden-compliance-gates.md` stays where it is (the archived-Dreams move is its own task). Owner `spec-pyforge-warden`. → Epic 21 / Story 21.1, specced 2026-10-26; built in the same PR with steward 113.1 and marshal 109.1.

## 2026-10-26 — A web face for the compliance factory — upload a manifest, watch warden and atlas analyze it (folded from compliance-factory-web-face)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 23.1). The body below is `docs/dreams/compliance-factory-web-face.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/compliance-factory-web-face.md`.*

## A web face for the compliance factory

### The Dream

The fleet's compliance engines are CLI-only: warden's six-axis gate, the
CycloneDX universe machinery, atlas intelligence. The dream: a service face
— upload any supported manifest (requirements/pyproject/pixi/conda), get
SBOMs + vulnerability/license/currency reports rendered from the SAME
engines, async via Celery, blobs kept out of brokers (keys-not-blobs).

### Grounding

FABRIC (millsks/django-python-generate-sbom, Apache-2.0, 2026-08-22
analysis) proves the shape in production: 8-phase Celery pipeline, derived
progress (`_phase_guard` — "no phase chooses its own number"), multi-tenant
orgs + API keys, 13-archetype × 6-format manifest corpus (folding into
warden fixtures regardless of this dream). Lower priority by design: the
engines exist; only the face is missing.

### Constraints / Non-goals

The engines stay canonical — the face calls warden/atlas, never reimplements
them (FABRIC's analyzers are NOT imported). Herald adjacency for UI. Not
multi-tenant SaaS on day one. Kin: `spec-pyforge-warden-compliance-gates`,
`package-inventory-eligibility`, cyclonedx-universe-inventory (shipped).

### Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-compliance-factory-web-face` derived under pyforge-warden and decomposed into the station
  backlog the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09** — Fleet readiness pass (operator-approved batch, `fleet-readiness-decision-batch-2026-09-09.md`
  row warden-B7). Stories 8.1/8.2 read `done` and the app IS mounted —
  `django_warden_fabric` is registered through `_STATION_PORTAL_PACKAGES`
  (`src/platform/config/settings/base.py:28`), having relocated from
  `src/platform/compliance_face/` to `src/shared/packages/django-warden/` in `2394d850db`,
  with `/compliance/` a permanent redirect to `/stations/warden/`. **The host question this
  Dream left open was answered by delivery: a platform-mounted Django app, as predicted.**
  Two realization gaps found against live code, both recorded on the Spec as a residual:
  the platform env carries no `pyforge-warden` path dep (`pixi.toml`
  `[feature.python-agent-platform.dependencies]` has only `pyforge-steward`) while
  `tasks.py:97-102` lazy-imports `pyforge.warden.cli`, so the deployed image cannot reach
  the engines the face calls and every job lands `FAILED`; and `sbom_json` is hardcoded
  `"{}"` (`tasks.py:111`), half-stubbing CAP-2. The dependency fix is **steward Story 48.11**
  (steward's surface, warden's capability; it also regenerates `environment.yaml`). Spec
  moved `ready` → `in-progress`; this Dream stays `specified` — the contract exists and is
  sound, the estate has not caught up to it.

## 2026-10-26 — A promotion gate that has never seen what it ships (folded from golden-path-conda-blind-spot)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 23.1). The body below is `docs/dreams/golden-path-conda-blind-spot.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/golden-path-conda-blind-spot.md`.*

## A promotion gate that has never seen what it ships

### The Dream

`golden-path-promotion` (Story 43.4) ran for the first time on 2026-09-04. It
recorded a Warden verdict of **`indeterminate`** over 329 components, zero of
them assessed for vulnerabilities. That is not a fluke result waiting on a
rerun — the verdict is structurally incapable of ever saying `clean`, because
of what it is actually scanning.

Read `scripts/platform-golden-path-promotion.sh`'s own comment: *"Warden has
no per-environment selector and its lock reader does not accept this
workspace's pixi.lock yet, so the honest target is the workspace manifest
alone, staged in a scratch dir."* The gate does not scan the resolved,
pinned closure that ships inside the platform image. It scans a bare
`pixi.toml` — no locked versions, no per-environment scoping — because
Warden's `PixiLockExtractor` was built (Story 2.2) to flatten *every*
environment and platform the lockfile ever resolved into one undifferentiated
set. That is a reasonable default for a manifest with one environment; it is
the wrong answer for this repo's `pixi.lock`, which resolves dozens of
environments — recipe tooling, docs, dev, five station test envs, and the one
that actually matters here, `python-agent-platform` — and unioning them all
would misrepresent what the deployed image contains far worse than scanning
nothing does.

Even where Warden *can* name a conda package's PyPI identity — Epic 2's
`spec-2-1-conda-pypi-map` already shipped a verified-confidence conda→pypi
map — a bare `pixi.toml` carries no locked version for anything but an exact
pin, so `classify_conda_specifier` degrades most of the inventory to
`NO_VERSION` before OSV ever gets a chance to match it. And even a perfectly
identified, perfectly versioned inventory would still come back
`indeterminate`: no CI job anywhere in this repo provisions the offline OSV
database. `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` is unset everywhere, and
Story 1.4's own decision record says a missing DB must route to
`indeterminate` rather than a false `clean` — which is correct, and exactly
what's happening, just for a reason nobody has gone back to fix.

One more piece completes the picture, and it isn't Warden's: `platform-deploy`
gates on the promotion *record existing*, not on `warden_status == "clean"`.
So today, a genuinely compromised image would promote exactly as freely as a
clean one, provided the script ran and wrote something. The record was meant
to be read, and nothing reads it yet.

Three structural gaps, one gate that has never been able to tell anyone
anything: it has never seen the image it's promoting, never had a database to
check against, and its one consumer never asked what it said.

### What it looks like when real

- `golden-path-promotion` scans the *actual* resolved `python-agent-platform`
  environment out of the root `pixi.lock` — real pinned versions, the thing
  that is actually built into the image — not a bare, unresolved `pixi.toml`.
- Warden's lockfile reader can be told which environment (and platform) to
  extract, instead of flattening every environment in the file into one set.
  A deploy gate needs to answer "what is IN this image", not "what exists
  anywhere in this monorepo's dev tooling."
- CI provisions the offline OSV database through the mechanism Story 1.4
  already designed and accepted — a conda-packaged DB, an explicit
  `--download-offline-databases` run on a connected machine, or a mirror — so
  `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` points at something real instead of
  nothing.
- `platform-deploy`'s verifier refuses any digest whose recorded verdict is
  not `clean` — not merely one whose record is missing.
- The verdict finally says something true: `clean` when the shipped
  environment's conda+pypi closure is actually scanned end to end,
  `indeterminate`/`warn` only for a real, specific, nameable gap — never a
  permanent architectural `indeterminate` that no amount of correct behavior
  could ever clear.

### What is real (measured 2026-09-04, `retro-pyforge-steward-2026-09-04.md`)

- `golden-path-promotion`'s first-ever run: `warden_status: indeterminate`,
  329 components, vulnerability axis 0 assessed.
- `scripts/platform-golden-path-promotion.sh` stages a bare `pixi.toml` (no
  lock) in a scratch dir as its scan target, by explicit, commented design —
  not an oversight, a documented workaround for the two gaps above.
- `pyforge-warden/extract/lockfiles.py::PixiLockExtractor`'s own docstring:
  "every package the file ever resolved, across all environments/platforms —
  no per-environment/per-platform selection" (Story 2.2-era decision).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-2-1-conda-pypi-map-the-ecosystem-identity-predicate.md`
  — verified-confidence conda→pypi identity mapping, already shipped (Epic 2).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/osv-db-offline-provisioning-decision.md`
  — Story 1.4 spike, **accepted** 2026-07-14: the offline-DB mechanism,
  staleness rule, cold-start disposition, and trust model are all already
  specified in detail. Nobody has wired the CI-side provisioning step it
  describes.
- `scripts/platform-deploy-verify-promotion.py` refuses a digest only when the
  promotion record is absent; it does not inspect `warden_status`.

### Constraints

- **Never promote to `clean` by loosening what counts as scanned.** An
  environment selector that still can't resolve a component's identity must
  keep withholding it (`UNMAPPED_ECOSYSTEM`), never quietly drop it from the
  denominator to make the percentage look better.
- **Reuse the two already-accepted designs.** `spec-2-1`'s conda→pypi map and
  the Story 1.4 OSV-DB decision record are correct and already gate other
  stories (1.5, 2.4) — this Dream wires them into the golden-path, it does not
  re-derive matching or staleness semantics from scratch.
- **Stay offline-first (NFR-S2).** Provisioning the database is an explicit,
  non-default CI step; the scan itself never egresses silently.
- **The two halves of the gate land together.** Warden producing a real
  verdict and `platform-deploy` actually reading it (steward's flip, record-
  exists → status-is-clean) are one effort, not two — a real verdict nobody
  gates on is exactly as useless as no verdict at all.

### Non-goals

- **Not** a general-purpose multi-environment/multi-platform selector for
  every future Warden caller. Build only what the golden-path use case needs
  — one named environment, the current platform — and widen it later if a
  second caller actually needs more.
- **Not** a new conda-native vulnerability data source. OSV via the verified
  conda→pypi identity is the v1 answer the accepted decision record already
  chose; revisit only if that proves insufficient in practice.
- **Not** touching the CFE atlas's own separate `pixi.lock` parser
  (`scan_project`) — a different, already-working subsystem. This Dream is
  scoped to `pyforge-warden/extract/lockfiles.py` and the golden-path script.

### Realization log

- **2026-09-04** — Captured, from `retro-pyforge-steward-2026-09-04.md` action
  item 8. Root cause traced to two comments already sitting in the code
  rather than assumed: `scripts/platform-golden-path-promotion.sh`'s own note
  on why it scans a bare `pixi.toml`, and `PixiLockExtractor`'s docstring
  naming the flattening as a deliberate Story-2.2 scope decision that has
  since become the actual blocker. The two designs this Dream leans on
  (`spec-2-1-conda-pypi-map`, the Story 1.4 OSV-DB decision record) were both
  already accepted before this Dream existed — verified by reading them, not
  assumed from their titles.
- **2026-09-05** — Spec distilled (`bmad-spec`, express mode) at
  `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-golden-path-conda-blind-spot/`
  — five capabilities, four constraints, five open questions for the operator;
  status `draft`. **Correction to § What is real:**
  `scripts/platform-deploy-verify-promotion.py` has refused any verdict that is
  not `clean` since `1016f4e763` (2026-09-04, after this Dream's measurement),
  so the third gap is closed and the gate is fail-closed today — nothing
  promotes until the verdict is real. Preserved in the Spec as CAP-5.
- **2026-09-09** — Fleet readiness pass, re-verified against live code rather than the
  Spec's own summary; all five open questions then answered by the operator
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
  § 2.3 C9), so the Spec moved `draft` → `ready` and this Dream's `specified` became
  earned. **Still open, re-confirmed unbuilt:** CAP-1 — `PixiLockExtractor` reads the flat
  top-level `packages:` list with no selection at all (`extract/lockfiles.py:180-206`);
  CAP-2 — the script still stages a bare `pixi.toml` in a scratch dir; CAP-3 —
  `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` appears in warden package code and tests only, with
  zero hits in any workflow. **CAP-5's behaviour re-confirmed true** (`scripts/platform-deploy-verify-promotion.py:31`)
  **but its guard is absent:** no test anywhere references that script — only the two
  workflows and `scripts/platform-ci-local.sh` — so the estate's only fail-closed deploy
  gate is three unprotected lines. That guard is minted first, as warden Story 12.1, ahead
  of the four CAPs it protects; CAP-1..5 follow as Stories 12.2–12.6.
  The answers, one line each: both `--pixi-environment` / `--pixi-platform` flags, explicit
  in CI, host default only interactively · osv-native `--download-offline-databases` on the
  connected runner, `actions/cache` keyed by the snapshot date · no coverage floor, `clean`
  alone gates · `clean` only, never promote on `warn`, waiver or not · the unscoped union
  stays the default with a structured WARNING, never an error.

## 2026-10-26 — Every package has one provenance trail and one eligibility answer, from any source (folded from package-inventory-eligibility)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 23.1). The body below is `docs/dreams/package-inventory-eligibility.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/package-inventory-eligibility.md`.*

## Every package has one provenance trail and one eligibility answer, from any source

### The Dream

"Can I use this package" has no single, auditable answer today when the evidence for it is
scattered across several disconnected sources — a curated allow-list, an existing SBOM, a
manifest, download telemetry — each with its own identity format for the same package. Warden
already computes an authoritative answer to a NARROWER, related question — "does the package set
in THIS project pass THIS project's compliance gate" — via its own hygiene/security/license/currency
axes. This Dream is the wider question: given several INDEPENDENT evidence sources, not just one
project's own manifest, is a given package eligible for use at all, with full provenance back to
whichever source(s) said so — expressed as one CycloneDX artifact, the same output shape Warden
already produces for its narrower question.

### What it looks like when real

- A pluggable `SourceContract` (`fetch`/`parse`/`validate`/`ingest`) that new evidence sources
  implement without touching the union-computation core — mirroring `feeds.py`'s already-proven
  fetch/cache/provenance shape (KEV, endoflife.date, EPSS), generalized from "one feed, one
  reader" to "N heterogeneous sources, one adapter interface each."
- A normalization layer resolving `scikit-learn`/`scikit_learn`/`sklearn` to one canonical
  identity — largely already exists as `inventory.py`'s `Component` identity
  (`(ecosystem, canonical_name, concrete_version)`, PEP-503-canonical, purl-derived); the gap is
  exposing it as a standalone, adapter-facing API rather than something baked into
  `ResolvedInventory`'s own internals.
- Eligibility computed as the union of required-authority sources, each result carrying
  `ProvenanceEntry`s back to every source and timestamp that contributed — a genuinely new
  vocabulary (`eligible-union`/`observed-in-use`/`flagged-for-review`), distinct from `models.py`'s
  existing `Status` verdict rungs (`error`/`policy-violation`/`indeterminate`/`warn`/`bypassed`/
  `clean`/`not-applicable`), which answer "did this project's OWN scan pass," not "is this
  package allowed to exist in the estate at all."
- Output through `sbom.py`'s existing CycloneDX renderer and purl discipline (`packageurl.PackageURL`,
  never PEP-503 dot-collapsing) — this Dream needs a new INPUT pipeline, not a new output format.

### What is real

Substantial infrastructure already exists in `pyforge-warden` and this Dream extends it rather
than starting fresh:

- **`sbom.py`** already renders CycloneDX (1.6) with correct purl discipline and self-validation
  — but as a projection over one project's own `ResolvedInventory`, not a multi-source union.
- **`feeds.py`** already has the generic cache-dir/staleness/provenance substrate three feeds
  share (KEV, endoflife.date, EPSS) — structurally the closest existing analog to the Dream's
  `SourceContract`, but built for one feed shape at a time, not a registry of heterogeneous
  adapters.
- **`inventory.py`**'s `Component` identity is already close to the Dream's `PackageIdentity` —
  canonical, purl-derived, ecosystem-aware — though scoped internally rather than exposed as a
  standalone normalization API.
- **`mapping.py`** already ships a static, packaged conda↔PyPI identity map (sourced from atlas's
  `export-purls`) — narrower than the Dream's alias-resolution engine (no `[-_.]+` collapsing, no
  general name-alias table) but the same "bundled asset, no network" discipline.
- **`discovery.py`** scans a LOCAL filesystem target for manifests — nothing like the Dream's
  external adapters (gist, existing-SBOM, Artifactory), which is the genuinely new surface here.

The `SourceContract` ABC + adapter registry + union-eligibility computation
(`sources.py`'s ~1100 LOC of prior art) and the standalone normalization engine remain the real
gap — new modules, not a port of existing code, though every one of them has a structurally
similar sibling already proven inside `pyforge-warden`.

### Full feature audit against `package-inventory-eligibility`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| `SourceContract` ABC (`fetch`/`parse`/`validate`/`ingest`) | **Included, new** | The genuine gap — `feeds.py` is the closest existing shape but is single-feed, not a registry. |
| `GistSourceAdapter` (canonical gist, free/premium/default tiers) | **Omitted, WF-specific** | The "canonical gist" concept is a WF-org artifact (Google Assured OSS package lists); no PyForge equivalent source identified. The adapter *interface* is included; this specific adapter is not. |
| `CycloneDXSourceAdapter` (existing SBOM documents) | **Included** | Directly reusable — Warden already reads/writes CycloneDX elsewhere (`sbom.py`); parsing an EXTERNAL CycloneDX doc as one evidence source is a natural adapter. |
| `ManifestSourceAdapter` (requirements.txt, environment.yaml) | **Included** | Directly reusable — `discovery.py` already parses `environment.yaml`/`pyproject.toml`/lockfiles for the narrower per-project scan; the parsing logic is adjacent, adapting it as one evidence SOURCE among several is new wiring, not new parsing. |
| `ArtifactorySourceAdapter` (JSON package evidence) | **Omitted, no target confirmed** | No Artifactory instance is currently wired into this repo's `_http.py` enterprise-routing layer for this purpose; the adapter interface supports adding one later without presupposing it exists now. |
| Normalization / `PackageIdentity` / alias resolution | **Included, partially exists** | `inventory.py`'s `Component` identity already does most of this; the alias-resolution table (`scikit-learn`/`sklearn`) is the incremental piece. |
| Eligibility computation (union-based, 3 statuses) | **Included, new** | Genuinely new vocabulary, deliberately kept separate from `models.py`'s `Status` enum — see Constraints. |
| Conflict flag detection (10 string markers) | **Included** | Small, self-contained, ports directly — no PyForge-specific blocker. |
| `ProvenanceEntry` (source, locator, timestamp, metadata) | **Included, new** | No direct analog in Warden today; every existing axis reports a verdict, not a source-attributed provenance chain. |
| CycloneDX output | **Included, reused** | Via `sbom.py`'s existing renderer — see Constraints. Source targets 1.5; Warden's existing renderer already targets 1.6, so this Dream inherits 1.6 rather than regressing to match the source exactly. |
| Multi-environment SBOM generation (EDL/SAS/GCP/ODP parsers) | **Omitted, WF-specific** | Four named enterprise data-environment formats with no PyForge analog — this repo has no equivalent set of deployment environments to enumerate. |
| Cross-environment summary reports (markdown, discrepancy detection) | **Omitted** | Depends entirely on the multi-environment mode above; nothing to summarize without it. |
| Pre-generation count validation | **Included** | General-purpose sanity check (does an adapter's own result meet an expected minimum), ports independent of any WF-specific source. |

### Constraints

- **Reuse `sbom.py`'s CycloneDX renderer and purl discipline** — no second, divergent CycloneDX
  serializer.
- **Reuse `feeds.py`'s cache/staleness/provenance substrate** where an adapter's own fetch
  behavior fits that shape (a gist or Artifactory-JSON adapter plausibly does; an ad-hoc manifest
  parse does not need caching at all).
- **This eligibility vocabulary and `models.py`'s `Status` enum stay separate.** They answer
  different questions (estate-wide "may this exist" vs. project-scoped "did the scan pass") and
  must not be collapsed into one enum just because both live in Warden.

### Non-goals

- **Not real-time approval** — batch inventory, not a gating API (source dream's own framing,
  carried over unchanged).
- **Not vulnerability/CVE correlation** — Warden's existing `vuln.py`/CISA-KEV axis is the
  separate, already-shipped mechanism for that; this Dream's eligibility question is orthogonal.
- **Not license compliance analysis** — Warden's existing `license.py` axis already owns this for
  the narrower per-project question; this Dream's CycloneDX output can carry license fields if a
  source provides them, but computing compliance from them is out of scope here.
- **Not deciding which specific evidence sources this deployment needs** (a WF-equivalent gist,
  an internal SBOM registry, Artifactory telemetry) — that's a Spec-time question once a real
  target environment is named, not something this Dream should presuppose.

### Kinships

[[pyforge-warden]] (the estate this extends — `sbom.py`/`feeds.py`/`mapping.py`/`inventory.py` are
all direct prior art) · [[pyforge-doctor]] (per the source dream's own Kinships, Doctor would
validate this pipeline's output health, mirroring its existing role validating other stations'
verdict artifacts)

### Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Grounded directly against `pyforge-warden`'s existing modules (`sbom.py`, `feeds.py`,
  `mapping.py`, `inventory.py`, `discovery.py`) rather than assumed from the source dream's own
  framing — found closer structural overlap than expected (`inventory.py`'s `Component` identity
  is nearly the Dream's `PackageIdentity` already) but confirmed the union-eligibility computation
  and external-source adapter registry are genuinely new. No specific already-bitten incident
  motivates this one (unlike [[bmad-switch-scope-enforcement]]); captured because the gap is real
  and the existing infrastructure fit is unusually clean, not because of a documented pain point.
- **2026-09-09** — Fleet readiness pass (operator-approved batch, `fleet-readiness-decision-batch-2026-09-09.md`
  row warden-B8). Stories 7.1–7.3 `done`; the three genuinely-new pieces this Dream named
  all exist as real modules — `SourceContract` + registry (`sources.py`), the union with
  `ProvenanceEntry` trails and the separate `eligible-union`/`observed-in-use`/
  `flagged-for-review` vocabulary (`eligibility.py`), and CycloneDX output through the
  existing renderer (`eligibility_sbom.py`). **The Constraint that this vocabulary stay
  separate from `models.py`'s `Status` rungs HELD** — verified by reading, not assumed.
  Gap: no CLI verb reaches any of it (`cli.py` contains no `eligib*` string), so the Spec's
  Success signal — "one CLI question, one CycloneDX answer" — cannot be exercised; Spec
  moved `ready` → `in-progress`. The Spec's one open question (required-authority policy)
  is **answered in code** — `eligibility.py:113-121` defaults to unanimous consensus over
  every source present in the evidence — with the config surface deliberately deferred
  (`eligibility.py:128-131`); the deferral is accepted and recorded as a named residual,
  and the config story is minted only together with the missing CLI front door, since a
  settable policy no CLI can set is unreachable. This Dream stays `specified`.

## 2026-10-26 — Dream — PyForge Warden: Compliance Gates (folded from pyforge-warden-compliance-gates)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 23.1). The body below is `docs/dreams/pyforge-warden-compliance-gates.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pyforge-warden-compliance-gates.md`.*

> **Superseded.** This Dream's six-item "Realization" list maps 1:1 onto capabilities
> [`docs/dreams/pyforge-warden.md`](pyforge-warden.md) (status: realized) already fully
> governs via `spec-pyforge-warden` (`status: shipped`, 31/31 stories merged via PR #110) —
> and Warden's entire shipped product already **is** "a pluggable multi-axis Python
> dependency compliance gate," verbatim from that Spec's own opening line. Multi-axis
> scanning (hygiene/security/license/currency), the never-false-green verdict lattice,
> fine-grained policy, baseline & grandfathering, the versioned `ComplianceReport` contract,
> and the fix-PR actuator are all shipped capabilities (CAP-1, CAP-4, CAP-5, CAP-6/9, CAP-7,
> CAP-12) with named stories (1.1, 1.3, 1.5, 3.1, 6.1, 6.2, 6.3, 6.4, 6.7, 6.8, 6.9). Created
> 2026-08-02 in a bulk commit later found to contain fabricated content elsewhere in the
> same commit; retired same day rather than spec'd as new work. See
> `spec-pyforge-warden-compliance-gates` for the retirement record.

## PyForge Warden — Compliance Gates

### Vision

**Warden** is a pluggable multi-axis Python dependency compliance gate — scanning manifests for security, license compliance, hygiene, and currency issues; aggregating findings; and enforcing policy with fine-grained controls (baseline, grandfathering, flag-activated gates).

**The ask**: Build a compliance engine that makes every decision verifiable, auditable, and configurable — giving operators both security confidence and operational flexibility.

### Problem

- **Compliance is multi-axis.** Security CVEs, license violations, hygiene issues (unmaintained deps, duplicates), currency (outdated versions). One tool only catches security; the operator misses license risks.
- **Violations are discovered late.** Package lands in the factory; downstream discovers the license violation. Rollback required; time lost.
- **Scanning tools conflict.** osv-scanner says "safe"; deptry flags hygiene issues; license checker complains about GPL. Operator doesn't know which to trust.
- **Policy is rigid.** Either blocks all CVEs or allows all. No nuance: "block critical; warn on medium; accept old-but-known".
- **Enforcement is scattered.** One team manually reviews security; another checks licenses. No unified gate.

### Realization

**Warden** delivers:

1. **Multi-axis Scanning** — Hygiene (deptry), Security (osv-scanner + CISA-KEV + EPSS), License, Currency (version age). One verdict aggregates all axes.

2. **Verdict Never False-Greens** — If any axis fails, verdict fails. Aggregation is pessimistic: FAIL + PASS + WARN = FAIL. No hiding behind "mostly safe."

3. **Fine-grained Policy** — Operators define: "block all CRITICAL", "warn on HIGH published ≤30 days ago", "accept numpy<=2.0 (v0 compat)". No binary on/off.

4. **Baseline & Grandfathering** — First scan establishes baseline (current state). New violations must be fixed. Old violations can be waived with expiry date.

5. **ComplianceReport Contract** — Versioned schema with all findings, verdict, policy applied, timestamp, approver. Machines can parse; humans can audit.

6. **Fix-PR Actuator** — For violations with known fixes (bump version, add license, remove duplicate), Warden auto-creates a PR. Operator reviews; bot merges if tests pass.

### Success Criteria

- ✅ **Completeness**: 4+ axes (security, license, hygiene, currency) with no false-greens
- ✅ **Accuracy**: 95%+ match with upstream tools (osv-scanner, deptry); auditable divergences documented
- ✅ **Policy**: Operators define 30+ rules; policy changes apply to in-flight scans
- ✅ **Auditability**: Every verdict includes: findings, policy applied, baseline comparison, approver
- ✅ **Speed**: Scan 1000-dep manifest <10 sec; 100-manifest fleet <5 min
- ✅ **Safety**: Zero false-greens over 1000+ audits; finding codes stable and registered

### Acceptance

Warden is done when:
1. All 4 axes (security, license, hygiene, currency) implemented and passing tests
2. Verdict never false-greens: 100+ test cases verifying aggregation logic
3. Policy system deployed: operators define 30+ rules; policy changes auto-apply
4. Baseline & grandfathering proven: baseline-set tests that old violations are waived, new ones flagged
5. Fix-PR actuator tested: auto-PRs created for 80%+ of fixable violations; 90%+ merge cleanly
6. Audit trail complete: every verdict loggable, queryable, and auditable by security team
