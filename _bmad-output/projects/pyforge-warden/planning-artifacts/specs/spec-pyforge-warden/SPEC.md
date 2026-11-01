---
id: SPEC-pyforge-warden
spec: pyforge-warden
status: ready
updated: "2026-11-01"   # AMENDED 2026-11-01 (EGM fleet audit, marshal Story 113.7): CAP-23 (an enabled TEA run that skipped reaches the report as one advisory skip record; Story 13.2), CAP-24 (the estate allowlist and its per-call fleet authorization, the bounded solver sharing the fix's own edit, every failure path in actuation; Story 14.4), CAP-25 (the shipped estate rules, the telemetry-off argv and env pinned by test; Story 15.2) and CAP-26 (an operator-started fleet run over an operator-designated github.com organisation read through the gh login, the export pinned with head_sha, job and proposal statuses never a verdict, time bounds, approve-time expiry, re-scan and re-solve, no non-PyPI/conda proposal, per-ecosystem offline DBs, unknown-then-warn license and currency; title drops 'on GitHub Enterprise'; Stories 16.6-16.10) amended, each success naming its command and exit code (CHAIN-STANDARD section 2); the No-silent-egress Constraint re-scoped by process, the Runtime-shape pixi floor (0.80.0, the workspace requires-pixi) and scope sentence and the fleet-verdict Non-goal re-worded; glossary.md added to companions; the legacy source cited at its archive path and spec-one-chain-per-station:CAP-3 qualified twice; markers stay (ready <date>) until the fix stories land on main; findings WAR-M-Z1..Z6, WAR-M-D1..D6, WAR-M-C1..C6, WAR-D-C1, WAR-D-C2, WAR-D-C5, WAR-D-C6, WAR-D-R1, WAR-D-R3, WAR-D-R4. Prior "2026-09-28"
owner-dream: docs/dreams/pyforge-warden.md
covers-dreams:
  - docs/dreams/pyforge-warden.md
  - archive/docs/dreams/package-inventory-eligibility.md
  - archive/docs/dreams/compliance-factory-web-face.md
  - archive/docs/dreams/golden-path-conda-blind-spot.md
  - archive/docs/dreams/pyforge-warden-compliance-gates.md
surface:
  - src/shared/packages/pyforge-warden/**
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - src/shared/packages/pyforge-warden/src/pyforge/warden/extract/__init__.py   # also governed by pyforge-marshal/spec-pyforge-core
  - src/shared/packages/pyforge-warden/src/pyforge/warden/extract/lockfiles.py   # also governed by pyforge-marshal/spec-pyforge-core
companions:
  - verdict-contract.md
  - axes.md
  - extraction-contract.md
  - glossary.md
sources:
  - ../../../../../../docs/dreams/pyforge-warden.md
  - ../../../../../../archive/docs/specs/pyforge-warden.md   # LEGACY Tier-1 intake spec — superseded by this Tier-2 Spec; absorbed, not adopted; at docs/specs/ until doctor Story 23.3 (2026-09-18)
  - ../../prds/prd-pyforge-warden-2026-07-14/prd.md
  - ../../architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md
  - ../../epics.md
open_questions: []   # all three answered 2026-09-14 by operator ruling — see § Open Questions.
---

> **Canonical contract.** Derived from `.memlog.md` and the folded Specs on 2026-09-17 (spec-one-chain-per-station:CAP-3 / warden fold). Companions stay record. Do not hand-edit — append the memlog and re-derive.

# Warden — the compliance gate that never false-greens

## Why


A pain, already paid daily, and a promise stated in the negative. Dependency **hygiene**
and dependency **security** are two disjointed tools and two disjointed pipelines, stitched
in CI by brittle glue that decides whether to fail the build. And conda/pixi projects are
second-class in both: neither `deptry` nor `osv-scanner` parses `environment.yml`,
`meta.yaml`, `recipe.yaml`, or `pixi.toml`, so a feedstock maintainer's only option is to
hand-translate a recipe into a fictional `requirements.txt` — lossy, stale the instant the
recipe changes, quietly wrong. Every incumbent scanner requires an *installed* environment;
nobody serves **pre-build source-manifest** scanning, and nobody brings dependency hygiene
to conda at all.

Both jobs, though, begin at the same manifest parse. Warden builds one conda/pixi-native
front door feeding independent per-axis assessment paths, and emits one schema-validated
report behind **one exit code**. The soul of it is the negative promise: **Warden refuses
to fake a pass.** In a domain where failure costs are asymmetric — a missed CVE is
catastrophic, a blocked build is merely expensive — an honest "not verified" beats a false
"all clear," at fleet scale, without ever mutating the host or the source. That is not one
feature among many; it is the acceptance property every other decision in this contract
serves.


## Capabilities
- **CAP-1 — one command, one exit** ← spec-pyforge-warden CAP-1 (shipped 2026-09-11)
  - **intent:** A pipeline — or a developer at a terminal — can run the whole multi-axis check as one non-interactive command and gate on a single exit code.
  - **success:** `warden scan <path>` reduces N per-finding outcomes to one status and one exit code from the frozen enum; the gate decides on report **content + severity**, never on a subprocess return code; there are zero prompts in any mode, including local workstation mode, where `--bypass` still takes its reason inline.
- **CAP-2 — source-manifest extraction** ← spec-pyforge-warden CAP-2 (shipped 2026-09-11)
  - **intent:** A project's declared dependency set can be resolved from its **source** manifests — pre-build, with no resolved or installed environment — whether those dependencies come from PyPI or conda-forge.
  - **success:** Six formats plus lockfiles are supported; PyPI inputs delegate to the engines' native parsers rather than re-implementing that parsing; corpus conformance over ~1,950 real conda recipes yields **0 uncaught exceptions** with a ratcheted unparseable rate CI holds monotonic; and a differential oracle asserts the extracted dependency set is a superset of the authoritative renderer's, modulo name-only-marked.
- **CAP-3 — assessed versus present** ← spec-pyforge-warden CAP-3 (shipped 2026-09-11)
  - **intent:** A consumer can tell what was actually **assessed** from what was merely **present**.
  - **success:** The resolved scan set is the denominator — every discovered manifest is scanned and reported per manifest (**union coverage**, not a precedence winner); coverage is reported per axis, each with its own denominators and a stated `resolution_depth` (`direct-only` vs `locked-closure`); a manifest may be 100% hygiene-covered and 0% vulnerability-covered, and the two are asserted as distinct fields on the fixture set; every withheld component states its reason and stays visible, never silently dropped.
- **CAP-4 — per-axis verdict** ← spec-pyforge-warden CAP-4 (shipped 2026-09-11)
  - **intent:** Every resolved component is assessed on each registered axis of trust, and the verdict says which axis spoke.
  - **success:** Hygiene, security, license, and currency each produce a verdict for 100% of resolved components, with per-axis coverage and provenance; each non-`clean` status carries a driver naming its axis and finding; a coverage claim for an unregistered axis is a hard error. Catalog: `axes.md`.
- **CAP-5 — tunable policy** ← spec-pyforge-warden CAP-5 (shipped 2026-09-11)
  - **intent:** A team can tune what blocks without editing the tool.
  - **success:** Per-repo configuration lives in a `[tool.pyforge-warden]` table in `pyproject.toml` and/or `pixi.toml` with deterministic per-key precedence, CLI flags overriding, and conflicts surfaced by name-and-value to stderr while never changing the exit code; a project's existing `[tool.deptry]` ignore configuration is honored; hygiene and security gate by default; license and currency gate when their policy flags are configured and, unconfigured, feed a visible `warn` — never a silent clean; and a minimum-coverage floor gate exists but **defaults off**, so first contact is never gated on coverage.
- **CAP-6 — waivers and baselines** ← spec-pyforge-warden CAP-6 (shipped 2026-09-11)
  - **intent:** A team can accept a risk in the open and on a clock, rather than muting it.
  - **success:** Waivers and baselines are committed files the tool **reads and never writes**; suppression keys on the stable finding-ID grammar; every applied entry is echoed in the report; an expired entry re-blocks; wildcards are rejected as over-broad; and a bypassed run still carries `bypassed` + `review_required` in the audit record even though its residual exit is 0.
- **CAP-7 — report and SBOM as data** ← spec-pyforge-warden CAP-7 (shipped 2026-09-11)
  - **intent:** A pipeline or a downstream estate can consume the run as data, not prose.
  - **success:** Each run emits a schema-validated, versioned `ComplianceReport` on stdout as a **single valid document or empty** — never partial, never diagnostics-contaminated — and a CycloneDX 1.6 SBOM with source-registry-correct purls and self-declared partiality when coverage is incomplete, whose component count equals the resolved-inventory count post-merge with the root project excluded.
- **CAP-8 — typed failure routing** ← spec-pyforge-warden CAP-8 (shipped 2026-09-11)
  - **intent:** A fleet operator can route every failure to its owner without reading a log.
  - **success:** Each failure carries a typed error kind — unparsable-manifest → developer; engine-unavailable → platform; engine output unrecognized, unparseable, crashed, or timed out, plus config-parse, config-validation, and internal-error → the tool's maintainers — and a missing, incompatible, crashed, timed-out, or output-drifted engine is exit 2 and never a silent pass. The same detection is re-exposed as a `--doctor` self-check on the one verb, which exits 0 when healthy or 2 with a typed kind, and **never 1**: it reports operability, not policy.
- **CAP-9 — adoption on-ramp** ← spec-pyforge-warden CAP-9 (shipped 2026-09-11)
  - **intent:** A repository carrying accumulated debt can turn the gate on without a day-one red wall that gets it ripped out.
  - **success:** `--warn-only` reports everything at exit 0; a committed baseline grandfathers existing findings so the gate blocks **new findings only**, with expiring entries that re-block; and every non-zero exit names the offending package, the finding (advisory ID + severity + fixed version, or the hygiene rule), the source manifest and location, and a remediation path.
- **CAP-10 — determinism and no residue** ← spec-pyforge-warden CAP-10 (shipped 2026-09-11)
  - **intent:** A run can be trusted to reproduce, and to leave nothing behind.
  - **success:** Decision-determinism by default (identical inputs plus an identical database snapshot yield an identical exit code and findings set) and **byte-identical** output under `--deterministic` over a documented volatile-field set; a scan never mutates the scanned tree or host state and cleans up on success *and* failure; per-invocation cost is O(project), independent of fleet size, with the live axes running in parallel and no shared mutable state; the tool's *own* overhead on top of the engines is bounded at p95 over a pinned reference corpus with the engines stubbed (engine scan time scales with dependency count and is not ours to promise), and first-run database provisioning is a one-time, cacheable cost so later runs are warm.
- **CAP-11 — air-gapped operation** ← spec-pyforge-warden CAP-11 (shipped 2026-09-11)
  - **intent:** An air-gapped or firewalled fleet can run the gate with no network at all, and know how fresh its data was.
  - **success:** The orchestrator's own process opens no socket, asserted by a socket-guard test, with all network confined to named engine subprocesses; the vulnerability database and the KEV, EPSS, and end-of-life feeds are provisioned or cached, offline by default and opt-in online but never silent; every verdict records its data source and snapshot timestamp; and stale, empty, swapped, or unverifiable data routes to `indeterminate` rather than a confident clean.
- **CAP-12 — fix-PR actuator** ← spec-pyforge-warden CAP-12 (shipped 2026-09-11)
  - **intent:** A team can turn findings into pull requests without the tool ever writing to their working tree.
  - **success:** `--open-fix-prs` runs strictly post-verdict with environment-supplied credentials, opening upgrade and removal pull requests through the forge API only; a failed PR-open never alters the verdict or exit code — it lands in the report's `actuation` section, outside status and exit composition; and `--fix-prs-dry-run` shares the real code path up to the egress seam while opening no sockets.
- **CAP-13 — SourceContract + identity API** ← spec-package-inventory-eligibility CAP-1 (shipped 2026-08-22)
  - **intent:** SourceContract adapters (fetch/parse/validate/ingest; feeds.py's proven shape generalized) + the identity API (inventory.py's Component identity exposed adapter-facing); CAP-2 eligibility-union with ProvenanceEntry trails and the NEW vocabulary (eligible-union/observed-in-use/flagged-for-review — distinct from Status verdicts); CAP-3 CycloneDX output via sbom.py + FABRIC's 13x6 manifest corpus adopted as fixtures (Apache-2.0, notices kept). Sibling org's same-name dream = pattern reference only (unlicensed)
  - **success:** two heterogeneous sources ingest without touching the union core; `scikit_learn`/`sklearn` collapse to one identity.
- **CAP-14 — eligibility-union + provenance** ← spec-package-inventory-eligibility CAP-2 (shipped 2026-08-22)
  - **intent:** Union over required-authority sources; every result carries ProvenanceEntry trails (source + timestamp); the new vocabulary (`eligible-union`/`observed-in-use`/`flagged-for-review`) stays distinct from `models.py`'s Status rungs.
  - **success:** an answer is reproducible from its own provenance alone.
- **CAP-15 — CycloneDX out + the corpus in** ← spec-package-inventory-eligibility CAP-3 (shipped 2026-08-22)
  - **intent:** Output through `sbom.py`'s renderer + purl discipline; FABRIC's 13-archetype × 6-format manifest corpus adopted as fixtures (Apache-2.0, notices kept).
  - **success:** deterministic CycloneDX; the corpus exercises every adapter.
- **CAP-16 — the service skeleton** ← spec-compliance-factory-web-face CAP-1 (shipped 2026-08-22)
  - **intent:** manifest upload (safe-loader validation), async Celery execution calling the EXISTING warden/atlas engines, keys-not-blobs; CAP-2 results: SBOM + vuln/license/currency reports rendered from engine output, derived progress (FABRIC _phase_guard pattern — no phase chooses its own number). FABRIC is the Apache-2.0 shape reference; engines never reimplemented
  - **success:** an uploaded pixi.lock returns a job id and completes against the real engines.
- **CAP-17 — results + derived progress** ← spec-compliance-factory-web-face CAP-2 (shipped 2026-08-22)
  - **intent:** SBOM + vulnerability/license/currency reports rendered from engine output; progress derived from phase position (`_phase_guard` pattern — no phase chooses its own number).
  - **success:** progress is monotonic by construction; reports match the CLI engines byte-for-byte on the same input.
- **CAP-18 — environment-scoped lockfile extraction** ← spec-golden-path-conda-blind-spot CAP-1 (shipped 2026-09-09)
  - **intent:** Warden extracts exactly the packages one named pixi environment resolves for one platform from a multi-environment `pixi.lock`, instead of the union of everything the file ever resolved.
  - **success:** scanning this repo's root `pixi.lock` scoped to `python-agent-platform` / `linux-64` yields the same set as that environment's `packages.linux-64` list in the lock (count, names, versions), with no other environment's exclusive packages; the unscoped call (`environment=None`, `platform=None`) keeps today's union behaviour and emits a structured WARNING naming the environment count.
- **CAP-19 — the promotion scans the shipped closure** ← spec-golden-path-conda-blind-spot CAP-2 (shipped 2026-09-09)
  - **intent:** `golden-path-promotion` scans the resolved `python-agent-platform` environment out of the root `pixi.lock` — the thing built into the image — not a bare `pixi.toml` in a scratch dir.
  - **success:** the promotion record's components equal the CAP-1 set, every component carries a locked version (no `NO_VERSION` from an unresolved manifest), and the scratch-dir staging is gone.
- **CAP-20 — the offline OSV database is provisioned in CI** ← spec-golden-path-conda-blind-spot CAP-3 (shipped 2026-09-09)
  - **intent:** the promotion job runs with a real, provenance-bearing offline OSV database, provisioned by the mechanism the Story 1.4 decision record already accepted, so the vulnerability axis assesses every identity-resolved component.
  - **success:** `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` points at a populated `<cache>/osv-scanner/PyPI/all.zip` with a recorded `snapshot_at`, provisioned by osv-native `--download-offline-databases` on the connected runner and held in an `actions/cache` keyed by the snapshot date; the record's vulnerability axis reports assessed > 0; a DB older than `db-max-age` (7 days, strict) or without provenance routes the verdict to `indeterminate`, never `clean`.
- **CAP-21 — the verdict is honest and specific** ← spec-golden-path-conda-blind-spot CAP-4 (shipped 2026-09-09)
  - **intent:** `warden_status` is `clean` only when the shipped closure's conda+pypi identity is scanned end to end; anything short of that is `indeterminate` / `warn` with a nameable gap, never a permanent architectural `indeterminate`.
  - **success:** on a not-clean verdict the record names the unassessed components and the reason (`UNMAPPED_ECOSYSTEM`, stale DB, missing DB); a deliberately pinned vulnerable version in the environment flips the record to a failing rung that names the finding. Coverage is not a separate gate: no `--fail-under-coverage` floor is added, because an unassessed component cannot reach `clean` under this Spec's first Constraint.
- **CAP-22 — deploy gates on the verdict (already true on main — preserve)** ← spec-golden-path-conda-blind-spot CAP-5 (shipped 2026-09-09)
  - **intent:** `platform-deploy` promotes a digest only when its recorded verdict is `clean` (shipped in `1016f4e763`; this spec keeps it).
  - **success:** the verifier refuses `indeterminate` / `warn` / `fail` and a missing record, accepts `clean`, names the driver finding id, and a test fails if the `!= 'clean'` refusal is removed. `clean` is the only promotable rung — a `warn` is never promotable, waiver or not.
- **CAP-23 — the TEA advisory reviews the diff from the remote-tracking ref** ← spec-pyforge-warden CAP-23 (ready 2026-09-27)
  - **intent:** `tea_advisory` passes `--base refs/remotes/origin/main` to TEA's `tea-test-review`, whose CLI diffs
    `<base>...HEAD`; a local branch or tag named `origin/main` at HEAD no longer empties the changed-test set. An
    enabled TEA run that started but returned no trusted verdict — a missing `refs/remotes/origin/main`, as in a shallow
    checkout, makes TEA exit 2, its ENV_ERROR — reaches the report's `advisory` section as one skip record carrying its
    reason, so a skipped review never reads like a scan with TEA off. Advisory only: never a finding, a rung or the exit
    code.
  - **success:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` exits 0, and its
    `tests/unit/test_tea_advisory.py` turns it red when any clause is absent: the argv the default runner builds carries
    `--base refs/remotes/origin/main` (`test_the_default_runner_passes_the_remote_tracking_ref_as_the_base`); an enabled
    run whose TEA exits 2 adds exactly one `tea-test-review` advisory record marked skipped, carrying its reason and no
    score or recommendation, while the status, the exit code and every other report key equal the run with TEA disabled
    (`test_full_scan_with_a_missing_base_ref_reports_the_skip_and_keeps_the_verdict`); TEA not enabled, or its binary
    absent from `PATH`, adds no record (`test_full_scan_with_tea_not_enabled_carries_no_tea_record`,
    `test_full_scan_with_the_binary_absent_writes_no_record`); a roster without `tea` still refuses loudly, never a
    silent pass (`test_full_scan_with_roster_missing_refuses_not_a_silent_pass`).
- **CAP-24 — the fix-PR actuator finishes the fix on the estate's repos** ← spec-pyforge-warden CAP-24 (ready 2026-09-28)
  - **intent:** For a `vuln:` finding, the fix-PR actuator (CAP-12) resolves a target version and delivers the fix, not
    a pointer to it. The target is the lowest release the finding's OSV advisory names as fixed — every
    `ECOSYSTEM`/`SEMVER` `fixed` event of the matching `affected[]` entry at or above the current version, ascending —
    that the estate's own solver accepts: pixi re-solves the repo's lock with that floor in a throwaway copy, and the
    first candidate that solves wins. The solver probes each candidate through the same manifest edit the fix makes, so
    every declaration form the edit handles is probed, and its search is bounded by a candidate cap and a total solve
    budget per finding. The actuator then edits the manifest that declares the dependency (`pixi.toml`, `pyproject.toml`
    or a recipe) in that copy, re-solves the lock there when the repo has one, and opens the result as a **draft** pull
    request through the forge API's Git Data endpoints, on the estate's own repos only: the estate allowlist, the
    `fix-pr-estate-repos` configuration key, whose default is `rxm7706/local-recipes` and `rxm7706/python-foundry`. The
    one exception widens nothing: CAP-26's operator approval passes a per-call authorization that admits the one
    approved finding's repo for that one call. The scanned tree is never written: the copy is a `mkdtemp` (`0700`)
    directory, removed on success and on failure. `--fix-prs-dry-run` opens no socket and reports the lowest OSV-fixed
    candidate with the solver marked not-run; pixi runs only on the real `--open-fix-prs` path, through the single
    subprocess helper, under a tested version range. A failed resolve, edit, solve or PR-open, a cap or budget stop
    included, is captured in the report's `actuation` section with its reason and never changes a rung, the status or
    the exit code. (Operator rulings 2026-09-28 and 2026-11-01.)
  - **success:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` exits 0 and turns red when any clause below
    is absent. A fixture advisory with `fixed` events 1.2.3 and 1.3.0, where the fixture solver refuses 1.2.3, yields
    target 1.3.0; the dry-run payload names 1.2.3 with the solver not-run and the socket-guard stays green
    (`tests/unit/test_fix_target_resolution.py`). The default solver probes a bare-key and a quoted-key `pixi.toml`
    entry, a `pyproject.toml` dependency and a recipe requirement line through the fix's own edit, in a copy that holds
    no `.pixi/` or `.git`, refuses a package declared in two manifests, tries at most 5 candidates within an 1800 s
    solve budget per finding, and bounds each `pixi lock`, pinned to the copy by `--manifest-path`, by the smaller of
    its configurable 600 s timeout and the budget left (`tests/unit/test_fix_solver_seam.py`); the edit keeps the
    value's quotes, a trailing comment and the file's line endings, and the result parses as TOML
    (`tests/unit/test_manifest_edit.py`). After a real-path run against a fixture forge the scanned tree is
    byte-identical and the throwaway copy is gone, after a success and after a forced failure
    (`tests/unit/test_manifest_fixup.py`); the edited manifest and the re-solved lock arrive as one commit on a
    `warden/fix/` branch behind a draft PR (`tests/unit/test_actuator_draft_pr_estate.py`). Each failure is a `failed`
    outcome in `actuation` naming its reason, with the status and exit code unchanged: no `fixed` candidate, the solver
    refusing every candidate, the cap or the budget reached, an out-of-range pixi (one whole-run outcome), a dependency
    no manifest declares, a failed manifest edit, a failed PR-open (`tests/unit/test_fix_target_resolution.py`,
    `tests/unit/test_actuator_require_manifest_fix.py`, `tests/unit/test_manifest_fixup.py`,
    `tests/integration/test_fix_pr_actuator.py`). A repo outside the estate allowlist gets no manifest-edit PR, absent a
    per-call CAP-26 authorization naming that repo for its one approved finding, which opens that draft without widening
    the allowlist (`test_non_estate_repo_is_skipped_when_draft_flag_on`,
    `test_authorized_fleet_repo_opens_draft_without_widening_allowlist`). The tested pixi range, `>=0.80.0,<0.82`, keeps
    its floor at `pixi.toml`'s `requires-pixi` (`tests/meta/test_engine_version_range_sync.py`), and `pixi run --frozen
    -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/integration/test_fix_solver_real_pixi.py -m slow`
    exits 0, running the real `pixi lock` on a hermetic local-channel fixture.
- **CAP-25 — SAST joins as an optional plugin: opengrep with estate-owned rules** ← spec-pyforge-warden CAP-25 (ready 2026-09-28)
  - **intent:** Opengrep (LGPL-2.1) takes the SAST slot on the PR-gate hook book as an optional scanner beside the
    `ghas` stub in `scanner_plugins.py`, enabled like the others through `WARDEN_OPTIONAL_SCANNERS`. It runs the
    estate's own rules — written for this estate from the Spec's Constraints, shipped in the package's data and never
    fetched from a registry — offline, through the single subprocess helper, under a tested version range, with its
    metrics and version check switched off in its argv and environment, because the socket guard cannot see a
    subprocess's egress. A test-only marker rule lives with the tests, never among the shipped rules. Each result
    becomes a non-`Finding` advisory note (tool, rule id, path, line, severity) in the report's `advisory` section — the
    TEA advisory's shape (suite:AD-4) — so SAST informs the reader but never adds a finding family, a rung, a status or
    an exit code, and never publishes a verdict: `warden scan` stays the sole PR verdict and the `ComplianceReport`
    stays at 1.1.0. An absent binary is omit-not-error (Story 9.3). CodeQL is rejected on its licence. Opengrep arrives
    as a conda package (mason Story 21.4). (Operator rulings 2026-09-28 and 2026-11-01.)
  - **success:** In the `pyforge-warden` environment on linux-64, where opengrep is a run-dependency, `pixi run --frozen
    -e pyforge-warden pyforge-warden-test` exits 0, and its `tests/unit/test_sast_opengrep.py` turns it red when any
    clause is absent: the package's `data/sast-rules/` ships the estate rules `subprocess-shell-true`,
    `yaml-unsafe-load` and `eval-exec` and no planted marker
    (`test_bundled_rules_dir_ships_the_estate_rules_and_no_planted_marker`); with `opengrep` enabled, each estate rule
    trips its fixture repo through `warden scan`, and the report's `advisory` names the bare rule id, the path and every
    tripping line while the status, the exit code and every other report key equal the same run with the scanner
    disabled (`test_each_estate_rule_trips_its_fixture_through_warden_scan`); the engine call carries
    `--disable-version-check` and the environment `SEMGREP_SEND_METRICS=off` and `OPENGREP_ENABLE_VERSION_CHECK=0`, and
    names only the local rules path, no registry (`test_opengrep_engine_argv_capture`,
    `test_build_opengrep_scan_argv_uses_local_rules_only`); an absent opengrep binary omits the scanner, and a default
    run's status and exit code stay unchanged (`test_run_opengrep_advisory_absent_binary_is_silent`,
    `tests/unit/test_default_warden_without_checkmarx.py`).
- **CAP-26 — Warden scans the enterprise fleet, one verdict per repo** ← spec-pyforge-warden CAP-26 (ready 2026-09-28)
  - **intent:** A fleet run inventories the repos of an operator-designated github.com organisation and scans each one
    with `warden scan` — one verdict per repo, exactly as today, and no fleet-level pass/fail. A run starts only from an
    operator action, the `warden_fleet_run` management command or its portal action, never a webhook. The organisation
    is never named in a tracked file: it lives in a gitignored local config, tests use a fictional organisation, and the
    leak guard forbids its name in tracked files. The inventory, and the items of the operator-designated GitHub
    Projects, are read through the operator's `gh` login at run time, with the token held in memory for that run only,
    and are read-only by construction: the REST client sends GET only and the GraphQL client query operations only, each
    refusing anything else before a socket opens. Both are published as gitignored JSON exports that other stations read
    as data (Atlas's dependency history, `spec-pyforge-atlas:CAP-61`), never through an import; each inventory row
    carries its default branch's tip (`head_sha`). Steward's GitHub Enterprise identities
    (`spec-pyforge-steward:CAP-164`) stay the path for a future GitHub Enterprise target. Which credential a live fleet
    scan and an approved proposal's draft PR use is not yet ruled: it is the operator's call, and the suite proves both
    paths against fakes. The run lives in `django-warden`'s operator-started Celery worker on the `ComplianceJob`
    pattern: keys-not-blobs (the Celery message carries ids only), and run and per-repo rows whose status is a job
    status (pending, running, succeeded, failed) that is never a verdict — no CLEAN or VULNERABLE second verdict; each
    per-repo row stores that repo's own `warden scan` report and exit code. Each repo is cloned into a throwaway
    directory, removed on success and on failure. Every repo scan, approve and clone is time-bounded: a timeout fails
    only that repo's row and names the bound, and the run stays succeeded as a job while it records its failed and
    skipped repo counts, never a verdict. On a fleet repo the actuator only plans: each `vuln:` fix on a PyPI or conda
    component is queued as a proposal holding the dry-run target, its candidates kept in the stored report and never a
    diff; a finding in an npm, Go or Cargo lockfile, whose ecosystem the report's `actuation` names, stays in the report
    and queues nothing, since CAP-24 edits no such manifest. A proposal's lifecycle (queued, approved, opened, failed,
    dismissed) is never a verdict either. A proposal opens — through the CAP-24 path, as a draft PR — only after the
    operator approves it, one proposal at a time, through a portal approve action or its management command (one code
    path); nothing ever auto-opens on a fleet repo. The approve refuses an expired approval before any clone, re-clones,
    re-scans the fresh clone and refuses a finding it no longer lists, then re-solves there from the stored candidates
    and the clone's own manifest locations; its per-call authorization admits only that proposal's repo for that call
    and never widens the estate allowlist. An approve that yields no manifest edit records `failed` with the reason and
    makes no forge write: nothing opens with an empty tree. Repos in ecosystems osv-scanner parses natively (npm, Go,
    Cargo, …) get the security axis through osv-scanner's own lockfile parsers, offline, against a per-ecosystem offline
    database provisioned on a connected runner; an ecosystem with no database reads `indeterminate`, never `clean`.
    Their license and currency axes resolve nothing for such a component, so each draws a `license:unknown` and a
    `currency:unknown` finding — `warn` while the axis is ungated, `indeterminate` once it is gated, never `clean` — and
    those axes' coverage rows count the components; hygiene stays `not-applicable`. Lifts two Non-goals, "Fleet
    aggregation" and "Non-Python osv-scanner ecosystems" (operator rulings 2026-09-28, 2026-10-11 and 2026-11-01).
  - **success:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` and the platform suite, `pixi run -e
    pyforge-guild platform-ci-local -- --test`, each exit 0 with no real network and turn red when any clause below is
    absent. Inventory: a fictional fixture organisation (`example-org`) of three repos yields three inventory rows and a
    JSON export whose every `repos[]` row carries `full_name`, `default_branch`, `clone_url`, `archived` and a non-empty
    `head_sha`, read with one GET per repo; a repo with no readable tip is listed under `skipped` with its reason, never
    as a row without `head_sha`; any other failure writes no export; and the export meets atlas's
    `parse_fleet_inventory` row rule, read as data (`src/platform/tests/test_warden_fleet_inventory.py`,
    `tests/unit/test_fleet_github_rest.py`); two fixture projects yield the project-items export
    (`src/platform/tests/test_warden_fleet_project_items.py`); a non-GET REST request and a non-query GraphQL operation
    are refused before a socket opens (`tests/unit/test_fleet_github_rest.py`,
    `tests/unit/test_fleet_github_graphql.py`). Run: a fleet run over three repos persists one run row and three
    per-repo rows, each carrying that repo's own `warden scan` report and exit code, and no run or per-repo status
    outside the job vocabulary; the throwaway clones are gone after a success and after a forced failure; each repo scan
    and each approve run under a 240 s soft and a 300 s hard limit and every `git` call of a clone under a 120 s
    timeout, so a clone that never returns ends its repo `failed` naming the timeout while the other repos and the run
    succeed, and the run row counts its failed and skipped repos (`src/platform/tests/test_warden_fleet_run.py`).
    Proposals: a planned `vuln:` fix lands as a queued proposal whose target is the resolved version, and no forge call
    is made until an approve action, after which exactly that proposal opens, against a fake forge, as a draft PR on its
    repo whose one commit carries the manifest edit to the re-resolved floor; an approve with no manifest fix, of a
    finding the fresh scan no longer lists, or of a proposal older than the approval expiry (default seven days, 604800
    s) records `failed` with zero forge writes; an npm `vuln:` finding queues no proposal
    (`src/platform/tests/test_warden_fleet_proposals.py`). Non-Python: a fixture npm `package-lock.json` pinning a
    known-vulnerable version, scanned offline against its fixture database, yields a `vuln:` finding with `hygiene`
    `not-applicable`, and with no npm database reads `indeterminate`; a clean-lock and a vulnerable-lock npm fixture
    compose ungated to `warn`, the vulnerable one also carrying its `vuln:` finding, and, gated on license or currency,
    to `indeterminate` driven by that axis, with the license and currency rows counting their components
    (`tests/unit/test_non_python_lockfiles.py`); `scripts/platform-provision-osv-offline-db.sh` provisions the PyPI,
    npm, Go and crates.io databases, skipping each one already provisioned, and the fleet worker scans against the cache
    its `WARDEN_OSV_DB_CACHE_DIRECTORY` setting names (`src/platform/tests/test_golden_path_promotion_osv_db.py`,
    `src/platform/tests/test_warden_fleet_run.py`).

## Constraints

- **The exit-code enum `{0, 1, 2, 130}` is frozen and closed** — 0 for `clean`/`warn`/`not-applicable`/`bypassed`, 1 for `policy-violation` or `indeterminate`, 2 for operational error, 130 for interrupt. Adding a code is a **MAJOR** change, because a new value silently breaks every `elif rc == 2:` consumer in the fleet — the deliberate opposite of the additive rule governing flags and report fields. Exit 2 stays **reserved** for operational error so fleet routing (`rc == 2` → infra owner) holds. No abnormal exit returns 0: any signal, interrupt, or uncaught internal error is non-zero and never a passing report.
- **The verdict lattice is frozen at seven rungs, in this order:** `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`. Status severity and exit code are deliberately *different* orderings — `bypassed` sits above `clean` because a suppression is an audit-relevant event. **`verdict.py` is the sole owner** of both the lattice and the exit projection; no other module maps a status to an exit code, enforced by a sole-ownership guard test. Every non-`clean` status carries a `driver` (axis + finding ID): an exit that cannot distinguish "critical CVE" from "blocking DEP001" is an incoherent contract. Full projection: `verdict-contract.md`.
- **Never false-green is *the* acceptance property, and `indeterminate` is its mechanism.** `not-applicable` means **nothing existed** to scan; `indeterminate` means **something existed** we could not or would not scan. `indeterminate` sits *above* `warn` precisely so a clean sibling axis can never mask it, and it projects to exit 1 — never a silent 0. Any run that did not meaningfully scan (empty extraction, expected-but-missing manifest, crashed engine, skipped coverage) is never `clean` in the **status** channel; only the sanctioned downgrades (`--allow-empty`, `--warn-only`) may lower the **exit** — the status stays honest. **Absence of an expected field is an error, not a zero.** Coverage improves **only** by resolving (reading the lock) or by name-level flagging — **never** by assuming a version. Enum variant-sets may grow **additively**, which is safe only because the projection treats any unknown value as `indeterminate`, never `clean`.
- **The `ComplianceReport` schema is versioned and its producer is closed at 1.1.0.** Exactly one amendment was sanctioned and paid; no other story may widen the schema. A coverage claim for an axis absent from the report's registered-axis tuple is a **hard error**, never a silent drop. The report and the SBOM version **independently** — the SBOM is CycloneDX spec 1.6 plus its own profile version, emitted `experimental` until a consumer ingests it.
- **Six axes of trust, four live.** Hygiene, security, license, and currency are registered producers that report and gate. **Provenance** (Sigstore/SLSA, PEP 740 trusted publishing, in-toto/GUAC) and **maintenance** (OpenSSF Scorecard, `criticality_score`, sustainability) are named direction and remain **unbuilt** — the six-axis identity is the destination, not the shipped surface. A new axis registers behind the existing engine seam with an axis string; there is no separate axis protocol.
- **One spine: a single `Component` and `ResolvedInventory`.** Discovery, routing, and extraction *produce* it; axis producers *annotate* it; report, SBOM, and verdict *read* it. No stage reaches around it or redefines a parallel shape. Identity is `(ecosystem, name, concrete_version)`; the purl is derived and its non-identity qualifiers stripped before any comparison. A `(name, None)` entry merges into `(name, version)` **only** when exactly one concrete version exists. Never guess-attribute a version.
- **No *execution* of untrusted input** — the constraint was never "stdlib-only". The extraction zone imports no execution primitive (`eval`/`exec`/`compile`/`__import__`/`os.system`/`subprocess`) and renders no templates (no `jinja2` import), using `yaml.safe_load` only, enforced by an AST-denylist meta-test. Safe parsers are permitted because they do not execute input. One module alone spawns subprocesses, always through a single normalization helper: machine output forced to a system-temp file, `NO_COLOR=1`, `stdin=DEVNULL`, explicit UTF-8 decode with undecodable output mapping to a typed error.
- **The tool never writes the scanned repository.** Waiver stanzas and baseline candidates are emitted to stdout for a human to commit; temp artifacts go to the system temp directory via `mkstemp`/`mkdtemp` at `0600`/`0700` (`mkstemp` *is* the symlink/TOCTOU defense); the actuator writes pull requests through the forge API, never the tree. Cleanup runs on success and on failure.
- **No silent egress.** The orchestrator's own process — `warden scan`'s — opens no socket (socket-guard test); all network is confined to named engine subprocesses; air-gapped mode passes explicit offline/local-DB flags **because osv-scanner defaults online** — an assertion, not a hope. KEV, EPSS, and end-of-life are cached feeds under the same posture. The fix-PR actuator is the sole carve-out inside that process, scoped to that one module under the real flag — never a global loosening; an operator-approved fleet proposal's draft PR leaves through the same actuator. The fleet's own egress — its read-only GitHub clients (`pyforge/warden/fleet_github_rest.py`, `pyforge/warden/fleet_github_graphql.py`) and its `git` clones — is explicit and operator-started, and runs only in `django-warden`'s Celery worker, outside `warden scan`'s process (CAP-26).
- **Engines are consumed, not authored.** `deptry` and `osv-scanner` are conda run-dependencies provisioned from existing conda-forge feedstocks — never curl-fetched at runtime — pinned to a **tested version range** rather than an exact pin, failing loud when out of range. That range is the guard against silent upstream output-schema drift, and it is also the distribution gate. Where the local mirror recipes for the engines are touched, this repo's CFE Rule 1 (invoke the skill) and Rule 2 (closeout retro) apply.
- **Engine exit codes are read as content, never as the gate.** osv's `1` means vulnerabilities found and is *expected*; `127` is multiplexed, so a database-absent/empty/corrupt `127` is a coverage gap routing to `indeterminate` while any other `127` is an error; anything outside `{0,1,127,128}` is an error. Decisively: a present-but-**empty** database makes osv exit **0 with an empty body**, which neither the exit code nor a namelist count catches — so a **content pre-flight** (parse and validate the advisory shape, require a non-zero advisory count at osv's case-sensitive `PyPI` segment) gates any trusted clean, and a provenance-less database routes to `indeterminate`.
- **osv has no conda ecosystem**, so a conda dependency is parsed as PyPI and a differently-named pinned package (`pytorch` → `torch`, a native `openssl`) would match the *wrong* identity and false-green silently. Therefore `vuln_matchable = (pypi_identity is not None) AND (version resolved to ==X.Y.Z)`, with `pypi_identity` resolved **only** from trustworthy provenance — lockfile PyPI entries, explicit PyPI sections, or the bundled static conda→pypi map. Unmapped yields `None`; conda `=1.2` is a *prefix*, not an exact match, and is withheld as `range-only`.
- **Extraction is non-rendering and two-pass**, which is the security posture expressed as a parsing strategy: v1 recipes are valid YAML and load directly; v0 recipes are neutralized first — selectors captured as marks, statement lines stripped, simple filtered interpolations substituted through **our own safe-filter allowlist**, never a Jinja engine. `run_constrained`/`run_constraints` entries are **constraints, not dependencies**, excluded from vulnerability matching and SBOM counts. Degrading never raises. Per-construct handling and the regression gate: `extraction-contract.md`.
- **Cross-ecosystem names are never silently merged or deduped** — per-ecosystem attribution is preserved and uncertainty is marked. A component's purl reflects the **source registry of the manifest it came from**, and an unresolved registry-of-truth is marked, not guessed into a purl.
- **Stream discipline:** the report goes to stdout, all diagnostics, progress, and warnings to stderr; in machine mode stdout is a single valid document or empty, never partial. Human text output and stderr are **explicitly unstable** and may change any release — declaring non-contract is itself a stability statement.
- **Contract stability is taxonomized, not one rule.** *Output* (report, SBOM) evolves by adding fields and bumping a version. *Input* (config keys, the waiver and baseline file schemas) evolves by accepting the old form forever, then deprecate → warn → remove, because those keys live across a 20k-repo fleet; an unknown or future waiver-file version is **rejected with a typed error, never guessed**. The exit enum is frozen. v1 ships the behavior, not the paperwork — no deprecation lifecycle machinery.
- **Determinism discipline:** never iterate a set for output — sort before every emit, serialize with sorted keys and fixed separators, take no unguarded wall-clock reading. `--deterministic` pins the documented volatile-field set: report and SBOM timestamps, the CycloneDX `serialNumber` and `bom-ref` derived from a content hash, iteration order, absolute paths rewritten repo-relative, the database version, and the `actuation` section.
- **Single-writer rules bind independently-built work.** The config loader alone computes the per-axis `gating` bool; producers and the report only read it. Axis producers never feed a rung above `warn`, and escalation is owned in exactly one place. Suppression matching-by-finding-ID plus expiry is implemented **once**, for both the waiver and baseline formats, with the waiver winning where both match and the suppression echoed once. KEV and EPSS enrich findings at exactly one position — inside the vulnerability producer, **before** policy dedup, never after.
- **The waiver file, the baseline file, and the offline database are untrusted-or-verified inputs:** schema-validated, expiry enforced against wall-clock, never executed. Authorship and integrity are **explicitly delegated** to code review and CODEOWNERS — the tool cannot verify a forge control at runtime and says so rather than pretending otherwise. The database's trust anchor is conda package integrity plus build-date staleness.
- **Bundled data carries its own age.** The LTS registry and the conda→pypi map carry a build-time `snapshot_at`, and every verdict derived from them carries `max_age_ok` against a configurable maximum age: a stale bundled registry can never silently report `supported`, and stale-under-an-active-gate routes to `indeterminate`. Absent or stale KEV/EPSS feeds under an active policy do the same — the gate never silently no-ops, and a null enrichment slot (feed absent) stays distinguishable from "assessed, not listed."
- **Resource bounds are enforced mechanisms, not hopes:** extraction is line-bounded with a per-line byte cap and a total manifest-size cap; no compiled pattern contains nested unbounded quantifiers (static assertion); database extraction is decompression-bounded and zip-slip confined; every engine invocation carries a bounded, configurable timeout whose expiry maps to a typed error and the frozen exit code — never an indefinite hang, never scored as a pass.
- **Engine-input purity and output neutralization:** the synthesized requirements projection is a **pure data projection** — any line beginning with `-`, or carrying a URL, VCS ref, path, or environment marker we did not author, is rejected or neutralized; manifest-derived values are never passed as CLI flags; `shell=True` is banned. Every input-derived string is emitted only through a schema-aware encoder, never string concatenation; purls are canonically percent-encoded; control and escape characters are stripped — so a malicious component string cannot make the tool a confused-deputy injection vector against a downstream SBOM or dashboard consumer.
- **Scope is the consumption edge — the first of three rings.** Ring 1 (edge) scans what applications actually pull, precisely per project, seeing only what is scanned; ring 2 (registry perimeter) and ring 3 (public upstream) are roadmap and direction. Within the edge there are **two modes, one identity**: *edge mode* — no data estate at runtime, bundled tiers carrying build-time age provenance — is the shipped differentiator; *fleet mode*, estate-backed, is roadmap. Both compose to the same lattice and the same exit codes.
- **Naming is a contract, and the mismatch is intentional.** *Warden* is the product/brand (display only), `pyforge-warden` the distribution name and project slug, `pyforge.warden` the import package, `warden` the CLI entry point. Product name ≠ distribution name because the bare names are taken upstream and this ships internal-first.
- **Runtime shape:** Python ≥ 3.12; `argparse`, not Click or Typer; stdlib-lean with a small set of targeted, conda-provisioned, safe-API-only runtime dependencies — "lightweight" means runtime footprint, not total cost, and the fixture-maintenance tax on conda selectors and Jinja grammars is real. pixi ≥ 0.80.0, the workspace's `requires-pixi`, is a **build/dev-environment floor**: the tool never invokes pixi at runtime, except the fix-PR actuator's real `--open-fix-prs` path (CAP-24), which runs the estate's solver as a named engine subprocess, under a tested range whose floor is that same `requires-pixi`, in a throwaway copy of the repo, never the scanned tree. Scope is **Python only** — PyPI plus conda-forge — except the lockfile ecosystems osv-scanner parses natively (npm, Go, Cargo, …), opened by CAP-26 on 2026-09-28: the security axis assesses them, and license and currency, which resolve nothing for them, report them unknown, never clean.

## Non-goals

- **Auto-fixing or removing dependencies in the scanned tree** — the actuator opens pull requests; nothing edits the working tree, ever.
- **Resolving or pinning transitive version trees** — the engines do that; Warden reads what resolves and states its resolution depth when it cannot.
- **Source-code license scanning** — license comes from declared metadata (conda `about:` plus installed-distribution metadata) only.
- **A fleet-level verdict** — a fleet run (CAP-26) is N `warden scan` verdicts, one per repo; no fleet-wide pass/fail, score or roll-up verdict is ever composed. *(The former Non-goal "Fleet aggregation" — a fleet run is N invocations with cross-repo aggregation delegated to the CI system — was lifted by operator ruling 2026-09-28: Warden now runs the fleet over an operator-designated organisation.)*
- **Retention and retrieval of evidence** — the tool emits self-describing artifacts; storage, indexing, and query-over-time belong to the CI system, precisely because the tool never writes the repository.
- **Telemetry** — the gate-disabled anti-metric is not measurable in-tool; it is defended by proxies (false-green = 0, a warn-only on-ramp, an auditable expiring bypass).
- **Verifying waiver authorship** — delegated to code review and CODEOWNERS; a runtime forge-control check is outside the process boundary.
- **Interactivity** — no prompts, ever, in any mode. Local workstation mode softens nothing.
- **Replacing this repository's existing project-scanning intelligence layer.**
- **osv-scanner's container and artifact scanning.** *(Its non-Python lockfile ecosystems — npm, Go, Rust, … — were a Non-goal until operator ruling 2026-09-28 lifted it for the security axis: CAP-26.)*
- **SPDX SBOM output** — CycloneDX only, locked.
- **SARIF output** — v1.x; the `--format` value space is reserved so it lands additively rather than as a breaking widening.
- **Full conda↔PyPI name reconciliation** and **per-section (dev/test) severity policy** — deferred; the contract marks uncertainty and tags each dependency with its source environment under one uniform policy instead.
- **Registry perimeter** (block/allow lists + quarantine), **engine swappability** (`--engine`), the **client provisioner**, **estate promotion**, and **public PyPI/conda-forge publish** — v1.x, in that order.
- **Axes 5–6, malicious-package and typosquat detection, the public-upstream ring, reachability analysis, alternate-library suggestions, OpenVEX/CSAF exchange, TUI/IDE surfaces, and the fleet control plane / OSPO / leader scorecards** — vision, unbuilt.

## Success signal

On any Python repository — PyPI-sourced or conda/pixi-sourced — one `warden scan` returns
a verdict a fleet operator acts on **without reading a log**: the exit code routes the
failure to its owner, the report names what was and was not assessed, and the SBOM says so
too.

The promise is proven mechanically rather than asserted. An enumerated adversarial-fixture
corpus — stale, empty, swapped, or unverifiable database; engine crash, timeout, absence,
or version drift; a manifest that parses but silently yields nothing; an injection attempt;
an over-broad waiver — produces **zero exit-0 outcomes**. The extractor raises **0 uncaught
exceptions** across ~1,950 real conda recipes under a ratcheted unparseable rate CI holds
monotonic. The report validates against its committed schema and the SBOM against
CycloneDX 1.6 with component count equal to the resolved inventory. A `--deterministic`
run is byte-identical twice over. And every one of those verdicts is readable from exit
codes and produced files alone.

## Fold provenance (2026-09-17)

One-chain fold (spec-one-chain-per-station:CAP-3 / CHAIN-STANDARD §7). This heading is the INV-A citation window: `spec-pyforge-warden` CAP-1..22. Absorbed folders keep pointer + memlog + companions. Satellite Dreams archived in place into [[pyforge-warden]].

## Assumptions

- The story set is **complete**, and has grown past v1: v1 was 31 stories across 6 epics, merged 2026-07-25; the station now carries **43 story keys, all `done`, across eleven epics** — epics 7–11 post-date the v1 scope (the eligibility union, the web face, the PR-gate hook book + scanner plugins, the skill/persona/portal slice, and the two advisory lenses) — plus a twelfth epic minted 2026-09-09 for `spec-golden-path-conda-blind-spot`. This contract is therefore written in the present tense as a standing description, not a plan. The legacy Tier-1 spec's `status: in-progress` predates that completion, and the Dream's former "23/31 in-build" line was corrected to 43/43 in the same 2026-09-09 pass.
- The competitive wedge — pre-build source-manifest scanning plus conda dependency hygiene, where every incumbent requires an installed environment — is **time-bound**, grounded by a dated spike to be re-run before any external release. If parity arrives, the hygiene-plus-security unification and the honest-coverage contract survive it, and conda dependency hygiene still has zero incumbents.
- The engines' output formats are a contract Warden is hostage to. The tested version range plus engine-output shape validation are the mitigations, so a working-but-drifted engine surfaces as a typed error rather than a false-green.

## Open Questions

**All three answered by operator ruling 2026-09-14.** None remain. They had blocked
`chain_currency_sweep_check`'s coherence checkpoint for warden, whose `overtaken` remedy is
explicitly *"resolve with the operator"* — so they could not be closed by inference.

- **Is v1 released, or story-complete?** → **Story-complete, not released.** All 31 stories are
  merged; the release-level Definition-of-Done items are genuinely unticked — the CFE Rule-2
  closeout retro (the engine mirror recipes lack CHANGELOG entries) and the internal JFrog
  PyPI+conda publish behind the engine version-range gate. The build is finished; the release is
  not. Recorded this way deliberately rather than ticking the residue: retroactively redefining
  "done" to match what shipped is the exact move `docs/dreams/README.md:90-98` warns against, and
  it would hide two real pieces of work.
- **What becomes of the legacy Tier-1 spec?** → **Re-stamped shipped and marked superseded**,
  matching what `claude-team-memory`, `copilot-bridge-vscode-extension` and
  `bmad-copilot-adapter-upstream` already did in the same phasing-out tier. *The question's premise
  was stale:* `docs/specs/pyforge-warden.md` (now `archive/docs/specs/pyforge-warden.md`, doctor Story 23.3) was corrected to `status: shipped` on 2026-09-03, so
  only the `superseded_by:` pointer was ever missing. Its Goals prose is kept as written — its own
  § *Release buckets* already records D12's move of the former v1.1 content into v1, making the
  text dated rather than wrong, and historical prose keeps its original wording.
- **What promotes provenance and maintenance out of vision?** → **The product stays six-axis, with
  the two annotated unbuilt.** The Charter's six-axis Warden identity is constitutional and is not
  narrowed to match today's build; provenance and maintenance are described as unbuilt wherever the
  six are enumerated, so the gap is visible rather than erased. *(The alternative — describing the
  product as four-axis until they land — was declined: it would have made the docs and the Charter
  disagree about what Warden is.)* What promotes them out of vision remains unset, and is a
  scoping question for whoever picks them up, not a blocker on this Spec.
