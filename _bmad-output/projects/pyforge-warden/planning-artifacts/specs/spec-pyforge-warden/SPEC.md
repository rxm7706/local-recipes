---
id: SPEC-pyforge-warden
spec: pyforge-warden
status: shipped
owner-dream: docs/dreams/pyforge-warden.md
surface:
  - src/shared/packages/pyforge-warden/**
companions:
  - verdict-contract.md
  - axes.md
  - extraction-contract.md
sources:
  - ../../../../../../docs/dreams/pyforge-warden.md
  - ../../../../../../docs/specs/pyforge-warden.md   # LEGACY Tier-1 intake spec (status: in-progress, FR1–FR40, D1–D12, release map, vision catalog) — superseded by this Tier-2 Spec; absorbed, not adopted
  - ../../prd.md
  - ../../architecture.md
  - ../../epics.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

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

- **CAP-1**
  - **intent:** A pipeline — or a developer at a terminal — can run the whole multi-axis check as one non-interactive command and gate on a single exit code.
  - **success:** `warden scan <path>` reduces N per-finding outcomes to one status and one exit code from the frozen enum; the gate decides on report **content + severity**, never on a subprocess return code; there are zero prompts in any mode, including local workstation mode, where `--bypass` still takes its reason inline.
- **CAP-2**
  - **intent:** A project's declared dependency set can be resolved from its **source** manifests — pre-build, with no resolved or installed environment — whether those dependencies come from PyPI or conda-forge.
  - **success:** Six formats plus lockfiles are supported; PyPI inputs delegate to the engines' native parsers rather than re-implementing that parsing; corpus conformance over ~1,950 real conda recipes yields **0 uncaught exceptions** with a ratcheted unparseable rate CI holds monotonic; and a differential oracle asserts the extracted dependency set is a superset of the authoritative renderer's, modulo name-only-marked.
- **CAP-3**
  - **intent:** A consumer can tell what was actually **assessed** from what was merely **present**.
  - **success:** Coverage is reported per axis, each with its own denominators and a stated `resolution_depth` (`direct-only` vs `locked-closure`); a manifest may be 100% hygiene-covered and 0% vulnerability-covered, and the two are asserted as distinct fields on the fixture set; every withheld component states its reason and stays visible, never silently dropped.
- **CAP-4**
  - **intent:** Every resolved component is assessed on each registered axis of trust, and the verdict says which axis spoke.
  - **success:** Hygiene, security, license, and currency each produce a verdict for 100% of resolved components, with per-axis coverage and provenance; each non-`clean` status carries a driver naming its axis and finding; a coverage claim for an unregistered axis is a hard error. Catalog: `axes.md`.
- **CAP-5**
  - **intent:** A team can tune what blocks without editing the tool.
  - **success:** Per-repo configuration lives in a `[tool.pyforge-warden]` table in `pyproject.toml` and/or `pixi.toml` with deterministic per-key precedence, CLI flags overriding, and conflicts surfaced by name-and-value to stderr while never changing the exit code; hygiene and security gate by default; license and currency gate when their policy flags are configured and, unconfigured, feed a visible `warn` — never a silent clean.
- **CAP-6**
  - **intent:** A team can accept a risk in the open and on a clock, rather than muting it.
  - **success:** Waivers and baselines are committed files the tool **reads and never writes**; suppression keys on the stable finding-ID grammar; every applied entry is echoed in the report; an expired entry re-blocks; wildcards are rejected as over-broad; and a bypassed run still carries `bypassed` + `review_required` in the audit record even though its residual exit is 0.
- **CAP-7**
  - **intent:** A pipeline or a downstream estate can consume the run as data, not prose.
  - **success:** Each run emits a schema-validated, versioned `ComplianceReport` on stdout as a **single valid document or empty** — never partial, never diagnostics-contaminated — and a CycloneDX 1.6 SBOM with source-registry-correct purls and self-declared partiality when coverage is incomplete, whose component count equals the resolved-inventory count post-merge with the root project excluded.
- **CAP-8**
  - **intent:** A fleet operator can route every failure to its owner without reading a log.
  - **success:** Each failure carries a typed error kind — unparsable-manifest → developer; engine-unavailable → platform; engine output unrecognized, unparseable, crashed, or timed out, plus config-parse, config-validation, and internal-error → the tool's maintainers — and a missing, incompatible, crashed, timed-out, or output-drifted engine is exit 2 and never a silent pass.
- **CAP-9**
  - **intent:** A repository carrying accumulated debt can turn the gate on without a day-one red wall that gets it ripped out.
  - **success:** `--warn-only` reports everything at exit 0; a committed baseline grandfathers existing findings so the gate blocks **new findings only**, with expiring entries that re-block; and every non-zero exit names the offending package, the finding (advisory ID + severity + fixed version, or the hygiene rule), the source manifest and location, and a remediation path.
- **CAP-10**
  - **intent:** A run can be trusted to reproduce, and to leave nothing behind.
  - **success:** Decision-determinism by default (identical inputs plus an identical database snapshot yield an identical exit code and findings set) and **byte-identical** output under `--deterministic` over a documented volatile-field set; a scan never mutates the scanned tree or host state and cleans up on success *and* failure; per-invocation cost is O(project), independent of fleet size, with the live axes running in parallel and no shared mutable state.
- **CAP-11**
  - **intent:** An air-gapped or firewalled fleet can run the gate with no network at all, and know how fresh its data was.
  - **success:** The orchestrator's own process opens no socket, asserted by a socket-guard test, with all network confined to named engine subprocesses; the vulnerability database and the KEV, EPSS, and end-of-life feeds are provisioned or cached, offline by default and opt-in online but never silent; every verdict records its data source and snapshot timestamp; and stale, empty, swapped, or unverifiable data routes to `indeterminate` rather than a confident clean.
- **CAP-12**
  - **intent:** A team can turn findings into pull requests without the tool ever writing to their working tree.
  - **success:** `--open-fix-prs` runs strictly post-verdict with environment-supplied credentials, opening upgrade and removal pull requests through the forge API only; a failed PR-open never alters the verdict or exit code — it lands in the report's `actuation` section, outside status and exit composition; and `--fix-prs-dry-run` shares the real code path up to the egress seam while opening no sockets.

## Constraints

- **The exit-code enum `{0, 1, 2, 130}` is frozen and closed** — 0 for `clean`/`warn`/`not-applicable`/`bypassed`, 1 for `policy-violation` or `indeterminate`, 2 for operational error, 130 for interrupt. Adding a code is a **MAJOR** change, because a new value silently breaks every `elif rc == 2:` consumer in the fleet — the deliberate opposite of the additive rule governing flags and report fields. Exit 2 stays **reserved** for operational error so fleet routing (`rc == 2` → infra owner) holds. No abnormal exit returns 0: any signal, interrupt, or uncaught internal error is non-zero and never a passing report.
- **The verdict lattice is frozen at seven rungs, in this order:** `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`. Status severity and exit code are deliberately *different* orderings — `bypassed` sits above `clean` because a suppression is an audit-relevant event. **`verdict.py` is the sole owner** of both the lattice and the exit projection; no other module maps a status to an exit code, enforced by a sole-ownership guard test. Every non-`clean` status carries a `driver` (axis + finding ID): an exit that cannot distinguish "critical CVE" from "blocking DEP001" is an incoherent contract. Full projection: `verdict-contract.md`.
- **Never false-green is *the* acceptance property, and `indeterminate` is its mechanism.** `not-applicable` means **nothing existed** to scan; `indeterminate` means **something existed** we could not or would not scan. `indeterminate` sits *above* `warn` precisely so a clean sibling axis can never mask it, and it projects to exit 1 — never a silent 0. Any run that did not meaningfully scan (empty extraction, expected-but-missing manifest, crashed engine, skipped coverage) is never `clean` in the **status** channel; only the sanctioned downgrades (`--allow-empty`, `--warn-only`) may lower the **exit** — the status stays honest. **Absence of an expected field is an error, not a zero.** Coverage improves **only** by resolving (reading the lock) or by name-level flagging — **never** by assuming a version.
- **The `ComplianceReport` schema is versioned and its producer is closed at 1.1.0.** Exactly one amendment was sanctioned and paid; no other story may widen the schema. A coverage claim for an axis absent from the report's registered-axis tuple is a **hard error**, never a silent drop. The report and the SBOM version **independently** — the SBOM is CycloneDX spec 1.6 plus its own profile version, emitted `experimental` until a consumer ingests it.
- **Six axes of trust, four live.** Hygiene, security, license, and currency are registered producers that report and gate. **Provenance** (Sigstore/SLSA, PEP 740 trusted publishing, in-toto/GUAC) and **maintenance** (OpenSSF Scorecard, `criticality_score`, sustainability) are named direction and remain **unbuilt** — the six-axis identity is the destination, not the shipped surface. A new axis registers behind the existing engine seam with an axis string; there is no separate axis protocol.
- **One spine: a single `Component` and `ResolvedInventory`.** Discovery, routing, and extraction *produce* it; axis producers *annotate* it; report, SBOM, and verdict *read* it. No stage reaches around it or redefines a parallel shape. Identity is `(ecosystem, name, concrete_version)`; the purl is derived and its non-identity qualifiers stripped before any comparison. A `(name, None)` entry merges into `(name, version)` **only** when exactly one concrete version exists. Never guess-attribute a version.
- **No *execution* of untrusted input** — the constraint was never "stdlib-only". The extraction zone imports no execution primitive (`eval`/`exec`/`compile`/`__import__`/`os.system`/`subprocess`) and renders no templates (no `jinja2` import), using `yaml.safe_load` only, enforced by an AST-denylist meta-test. Safe parsers are permitted because they do not execute input. One module alone spawns subprocesses, always through a single normalization helper: machine output forced to a system-temp file, `NO_COLOR=1`, `stdin=DEVNULL`, explicit UTF-8 decode with undecodable output mapping to a typed error.
- **The tool never writes the scanned repository.** Waiver stanzas and baseline candidates are emitted to stdout for a human to commit; temp artifacts go to the system temp directory via `mkstemp`/`mkdtemp` at `0600`/`0700` (`mkstemp` *is* the symlink/TOCTOU defense); the actuator writes pull requests through the forge API, never the tree. Cleanup runs on success and on failure.
- **No silent egress.** The orchestrator's own process opens no socket (socket-guard test); all network is confined to named engine subprocesses; air-gapped mode passes explicit offline/local-DB flags **because osv-scanner defaults online** — an assertion, not a hope. KEV, EPSS, and end-of-life are cached feeds under the same posture. The fix-PR actuator is the sole carve-out, scoped to that one module under the real flag — never a global loosening.
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
- **Runtime shape:** Python ≥ 3.12; `argparse`, not Click or Typer; stdlib-lean with a small set of targeted, conda-provisioned, safe-API-only runtime dependencies — "lightweight" means runtime footprint, not total cost, and the fixture-maintenance tax on conda selectors and Jinja grammars is real. pixi ≥ 0.72.2 is a **build/dev-environment floor**: the tool never invokes pixi at runtime. Scope is **Python only** — PyPI plus conda-forge.

## Non-goals

- **Auto-fixing or removing dependencies in the scanned tree** — the actuator opens pull requests; nothing edits the working tree, ever.
- **Resolving or pinning transitive version trees** — the engines do that; Warden reads what resolves and states its resolution depth when it cannot.
- **Source-code license scanning** — license comes from declared metadata (conda `about:` plus installed-distribution metadata) only.
- **Fleet aggregation** — a fleet run is N invocations, with cross-repo aggregation delegated to the CI system. This is a by-design non-capability, not a missing feature.
- **Retention and retrieval of evidence** — the tool emits self-describing artifacts; storage, indexing, and query-over-time belong to the CI system, precisely because the tool never writes the repository.
- **Telemetry** — the gate-disabled anti-metric is not measurable in-tool; it is defended by proxies (false-green = 0, a warn-only on-ramp, an auditable expiring bypass).
- **Verifying waiver authorship** — delegated to code review and CODEOWNERS; a runtime forge-control check is outside the process boundary.
- **Interactivity** — no prompts, ever, in any mode. Local workstation mode softens nothing.
- **Replacing this repository's existing project-scanning intelligence layer.**
- **Non-Python osv-scanner ecosystems** (npm, Go, Rust, …) and its container/artifact scanning.
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

## Assumptions

- The story set is **complete** — 31 stories across 6 epics, merged 2026-07-25 — so this contract is written in the present tense as a standing description, not a plan. The Dream's "23/31 in-build" line and the legacy Tier-1 spec's `status: in-progress` both predate that completion.
- The competitive wedge — pre-build source-manifest scanning plus conda dependency hygiene, where every incumbent requires an installed environment — is **time-bound**, grounded by a dated spike to be re-run before any external release. If parity arrives, the hygiene-plus-security unification and the honest-coverage contract survive it, and conda dependency hygiene still has zero incumbents.
- The engines' output formats are a contract Warden is hostage to. The tested version range plus engine-output shape validation are the mitigations, so a working-but-drifted engine surfaces as a typed error rather than a false-green.

## Open Questions

- **Is v1 released, or story-complete?** All 31 stories merged, but the legacy spec's v1 Definition of Done still carries unchecked release-level items: the CFE Rule-2 closeout retro (the engine mirror recipes lack CHANGELOG entries) and the internal JFrog publish behind the engine version-range gate.
- **What becomes of the legacy Tier-1 spec?** `docs/specs/pyforge-warden.md` still reads `status: in-progress`, and its Goals block still describes the pre-D12 tiering in which the license and currency gates were v1.x. Does it get re-stamped and marked superseded by this Spec, or frozen as a historical record?
- **What promotes provenance and maintenance out of vision?** Two of the Charter's six axes are unbuilt with no owner and no trigger — and until they have one, does the product describe itself as four-axis or six-axis?
