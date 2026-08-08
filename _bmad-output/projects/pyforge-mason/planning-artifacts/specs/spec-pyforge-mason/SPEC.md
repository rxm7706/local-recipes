---
id: SPEC-pyforge-mason
owner-dream: docs/dreams/pyforge-mason.md
covers-dreams:
  - docs/dreams/presenton-pixi-image.md   # folded in 2026-08-02 as CAP-8..CAP-13 (see § Satellite below); satisfies INV-1 for this Dream
surface:
  - src/shared/packages/pyforge-mason/**    # the CLI this Spec builds (not yet created)
companions:
  - glossary.md                                                                      # spec-authored: the vocabulary the chain requires verbatim
  - ../../prds/prd-pyforge-mason-2026-07-25/prd.md                                   # adopted (chain): FR-1..FR-50 / NFR-1..NFR-16 / D-1..D-13
  - ../../architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md   # adopted (chain): the 16 ADs, structural seed, stack, diagrams
  - ../../epics.md                                                                   # adopted (chain): 5 epics / 38 stories
  - ../spec-packaging-factory/SPEC.md # adopted: the Spec governing the CFE surface Mason wraps — authoritative over Mason (Rule 1)
sources:
  - ../../../../../../docs/dreams/packaging-factory.md
  - ../../briefs/brief-pyforge-mason-2026-07-25/brief.md
  - ../../briefs/brief-pyforge-mason-2026-07-25/addendum.md
  - ../../prds/prd-pyforge-mason-2026-07-25/review-adversarial.md   # absorbed: findings applied in PRD revision 2 (FR-47..FR-50, D-10..D-13)
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# mason CLI — the packaging factory, made portable

## Why

A pain to solve, and an asset to free. The repository's packaging capability is real, proven, and **trapped**: a nine-step recipe lifecycle across 769 maintained feedstocks, carrying 106 accumulated gotchas and 10 hard constraints, exposed through 46 MCP tools and backed by 1,186 tests — reachable only inside a Claude Code session, in one repository, through pixi tasks defined in one manifest, with `recipes/` hardcoded in seventeen scripts. You cannot install it. You cannot run it in CI. A colleague cannot use it. The asset is real; the distribution is zero. And the half it never had is the half nobody else has either: for the maintainer shipping a library, the wheel takes ninety seconds and then the conda half means switching toolchains entirely — a different metadata format, a different dependency namespace, a different build system, a platform matrix, and a volunteer review queue. The domain survey is unambiguous that **no single tool spans both ecosystems**: Hatch and maturin are structurally conda-unaware, `pixi publish` targets conda channels with documentation silent on PyPI, and conda-smithy and the autotick-bot state in their own documentation that they cannot be deployed outside conda-forge's infrastructure. That is not a missing feature in one product — it is an unowned seam between two toolchains with different governance. `mason` is the installable face of the trapped capability plus that missing half: three verb families, where the middle one is the differentiator and the outer two make the product usable by people who never touch a recipe. The deeper aim is smaller and more stubborn: **packaging a library should be a sentence, not an afternoon of YAML archaeology** — executable outside the room it was invented in.

## Capabilities

- **CAP-1 — the CFE seam**
  - **intent:** A single module is the entire boundary between Mason and the packaging machinery it wraps, so the wrap decision is enforceable rather than aspirational.
  - **success:** A static check finds no wrapped-script path or filename anywhere outside the adapter, and every recipe subcommand's call graph reaches the machinery through exactly one adapter function; the root-resolution chain (explicit flag → environment variable → upward walk → structured degradation) and the interpreter chain (flag → environment → the running interpreter, with the wrapped machinery's import floor probed before first use) are each independently unit-testable against a synthetic filesystem and always record which step matched; every invocation carries a mandatory timeout whose expiry produces a distinct typed error and leaves no orphaned process; output parsing tolerates a leading non-JSON progress line before the JSON body; and Mason's own code reads no credential variable at all.

- **CAP-2 — `mason recipe`: the lifecycle, as a product face**
  - **intent:** A user carries a package through the whole conda-forge recipe lifecycle — generate, validate, build, diagnose, optimize, scan, submit, update — through Mason's verbs, with every piece of packaging judgement supplied by the machinery Mason delegates to and none of it living in Mason.
  - **success:** Generation from each supported upstream source produces a v1 recipe at a user-specified path with Mason asserting no field defaults of its own; validation exits non-zero on any reported failure with the machinery's finding identifiers and check codes preserved **verbatim** — never renumbered or reworded; native build is the default with any CI-parity build behind an explicit flag that is never implicit, streaming child output as it is produced rather than leaving a silent terminal for a multi-minute build; diagnosis names cause and fix, and says so plainly when the machinery returns none rather than inventing one; update shows the change before writing it; submission defaults to dry-run, requires an explicit confirming flag, preserves the two-phase prepare-then-open flow as separately addressable, and returns a ship receipt carrying the pull-request reference.

- **CAP-3 — `mason package`: the dual-ship motion**
  - **intent:** A user builds a library's artifacts and ships them to PyPI, a conda channel, and conda-forge in one motion — with a receipt that tells the truth about which targets are done and which are merely queued.
  - **success:** A build produces wheel, sdist and conda artifact from one project manifest, reports their paths, uploads nothing, and runs with the wrapped machinery absent; ship accepts exactly the four defined targets and rejects anything else while listing the valid set, honours multiple targets independently, and builds first if artifacts are absent by reusing the build implementation rather than duplicating it; a version disagreement between the wheel and the conda package aborts before any upload with both values shown; a missing credential is detected **before** any artifact is built or uploaded; one target's failure never prevents the others being attempted; a repeat ship to conda-forge for an already-open pull request reports `pending` with the existing reference and opens **no** second pull request; and Mason ships Mason — a rehearsal publish to the test index must pass before the irreversible one runs.

- **CAP-4 — `mason environment`: dependency binding**
  - **intent:** A user resolves a project's mixed conda and pip dependency sets into a single lockfile, and can ask in CI whether that lockfile has gone stale.
  - **success:** Solving is delegated entirely to an engine with Mason implementing no resolution logic; discovered manifests are listed before solving and explicit paths override discovery; platform targeting is repeatable and the engine's default is reported when none is given; the check verb exits non-zero on a stale lockfile and emits machine-readable output suitable for CI; the producing engine's name and version appear in output and in the lockfile's provenance where the format allows; and the whole capability runs with the wrapped machinery absent.

- **CAP-5 — the CLI shell and output contract**
  - **intent:** Mason presents one coherent public surface — a noun-verb command tree with both human and machine output, a stable exit-code contract, structured errors, and the ability to diagnose its own installation truthfully, including what it cannot do.
  - **success:** Three nouns plus top-level self-diagnosis and version; a bare noun prints that noun's verbs and exits non-zero, with exactly one documented alias exception that a test asserts is the only one; under machine output stdout carries exactly one JSON document or nothing while every diagnostic goes to stderr; exit codes originate from one module and no command computes its own; every anticipated failure produces a typed error with a stable identifier and an actionable message, and none surfaces as a raw traceback; self-diagnosis reports Mason's version, the resolved root and which step found it, the selected interpreter and whether the import floor is satisfied, and each engine's presence and version — **exiting 0 when Mason is usable for the non-wrapping verbs even with the machinery missing**, reporting the gap rather than failing; and no global flag is required for any command to run.

- **CAP-6 — distribution**
  - **intent:** Mason ships the way its siblings ship, so the capability finally leaves the repository it was invented in.
  - **success:** One project manifest drives both a conda artifact and a wheel plus sdist, all building green through the three-task build triad; the console entry point resolves and reports the installed distribution version; the root workspace carries a path dependency and a lean environment for the member; engines are conda run-dependencies with declared version ranges mirrored by in-code constants and kept in sync by a meta-test, and nothing is fetched at runtime; and the wheel's dependencies contain only what the module imports, with any dependency on a sibling package an optional extra rather than a hard requirement.

- **CAP-7 — proving the seam holds, and closing the loop**
  - **intent:** The product's central guarantee — that Mason wraps the packaging capability and never forks it — is verified by tests rather than asserted by documentation, and the effort closes by improving the very skill it wraps.
  - **success:** The knowledge deny-list is declared in one reviewable module where every entry cites the artifact it derives from, **and ships positive fixtures planting a violation of each category so that a deny-list matching nothing is a failing test, not a passing one**; weakening or removing an entry requires a rationale a companion test asserts is present; the sole-caller test finds no reference to the wrapped machinery outside the adapter; the independence test runs every `package` and `environment` verb with the root guaranteed unresolvable behind a **named one-entry allow-list**, asserting positively that the excepted target fails for the *right* reason; the governance check stays green with zero implementation commits touching the governed surface and exactly one sanctioned retrospective commit that does; the fidelity test proves Mason transforms presentation rather than semantics, is slow-marked, excluded from the default task, and **skips cleanly** when no root resolves; and the effort is not done until the retrospective lands skill edits plus a dated changelog entry with a semver bump.

## Constraints

- **The central decision — wrap by capability, not by product.** Mason **wraps** the packaging machinery by subprocess for all recipe operations and **builds** natively for `package` and `environment`. The boundary is drawn by *capability*. Pure porcelain was rejected because two of the three charter verb families have **nothing to wrap** — no wheel build, no upload path and no lock orchestration exists anywhere in the wrapped machinery's 41,410 lines, so a pure wrapper is not a smaller Mason but a Mason missing its reason to exist. Extraction/reimplementation was rejected on three independently sufficient grounds: **governance makes a fork structurally adversarial** (Rule 1 makes the skill authoritative over any conflicting story, and Rule 2 mandates that every conda-forge effort *edits the skill* — so a fork is continuously invalidated by the loop that governs the domain); **the in-repo precedent failed** (a sibling project rebuilt ~29,000 lines across 32 merged stories and the 8,902-line original is still the live runtime — nothing routes to the rebuild); and **it forks the moat**, converting 106 gotchas and 10 constraints from an appreciating asset into a depreciating one. The accepted cost, paid deliberately: **Mason is not standalone** — `mason recipe` requires a discoverable installation and is inert without one.
- **Knowledge-free core.** No module in Mason may contain a conda-forge gotcha identifier, policy constant, pin table, recipe-format field default, or selector/platform rule. Recipe semantics enter Mason only as opaque data through the port. Enforced by a meta-test with an explicit deny-list — because this repository has already proven that intent alone does not prevent the failure.
- **The port is the sole caller.** One module may name a wrapped script, hold its path, or spawn its process; every script used is declared once in a module-level table there, and a use-case calls a named adapter function rather than passing a script name.
- **Subprocess only — never import, importlib, or exec.** Five of the wrapped modules are physically unimportable (hyphenated filenames, including the 2,653-line recipe generator, in a tree governed by a changelog sentinel so renaming is unavailable); import would inherit `__file__`-relative data resolution that is meaningless from an installed location, a repo-root anchor that varies across scripts, 55+ credential environment reads, and a documented hang history with no in-import timeout. Every invocation is a timed subprocess returning a typed result in which a non-zero return code is **data, not an exception**.
- **Capability tiers are structural, not conventional.** CFE-dependent: the recipe use-cases and **only** the `conda-forge` ship target. CFE-independent: everything else. The port resolves **per target, not per command** — a PyPI ship must succeed with the machinery absent. The exception is a named one-entry allow-list; a blanket "except where CFE is needed" formulation is explicitly forbidden, because that phrasing is the erosion the rule exists to stop.
- **The wrapped surface is read-only, forever.** No *implementation* commit writes to the governed tree. Behaviour Mason needs and the machinery lacks is an open question routed to that machinery's own retrospective — never a local patch, never a vendored copy. Exactly one sanctioned exception: the closing retrospective, identified by a `retro:` subject plus a changelog entry in the same commit, with the check asserting it is used **once** so it cannot be borrowed to sneak an implementation change through.
- **Degradation is designed behaviour, never a crash.** An unresolvable root makes recipe commands exit non-zero naming all four resolution steps and how to satisfy each, while the other two verb families run unaffected. No command emits a Python traceback for this condition.
- **Resolution is a pure decision over inputs.** The resolution chains are pure functions over (explicit argument, environment mapping, start directory) performing filesystem *reads* only — never writes, network, or process spawns — and the outcome always records which step matched, so self-diagnosis reports without re-resolving.
- **Dependencies point inward only, and no use-case imports `subprocess`.** That single rule is what stops recipe logic leaking inward one helper at a time.
- **Mason never solves and never builds from scratch.** Every external tool is an adapter behind one protocol, discovered on `PATH`, provisioned as a conda run-dependency, and **never downloaded at runtime**; a missing engine is a typed error naming the engine and how to provision it.
- **One shared shape for all shipping, and `pending` is never collapsed into success.** Every target yields a state of `not_attempted`, `failed`, `pending`, or `terminal` plus a reference; the aggregate exit code is failure only if a target failed to *initiate*. PyPI completes in seconds and conda-forge completes in days behind a human review queue — reporting a uniform success for a queued pull request is a correctness bug, not a presentation choice. Adding a target means adding an adapter that produces this shape, never a new shape.
- **Idempotence by interrogating the target, never by local state.** Mason persists no state directory, no receipt cache, no lock file of its own — a local cache is a second source of truth that goes stale and silently skips a real upload. An uninterrogable target yields `pending` with the reason stated, never an assumption in either direction.
- **One owner per operation.** Staged-recipes submission has exactly one implementation, reached through the port; the `conda-forge` ship target *calls* it and wraps the result, and `mason recipe submit` is the same call rendered directly. Neither may reimplement the other.
- **One error taxonomy, one exit-code owner.** All anticipated failures are typed errors carrying a stable identifier that **is API** — changing one is a major version bump. A single module is the sole producer of every exit code; no other module computes or hardcodes one.
- **Core returns data; only the driving adapter formats.** Use-cases return frozen dataclasses; one renderer turns them into text or JSON. Under machine output, stdout carries exactly one JSON document or nothing and every diagnostic, progress line and log record goes to stderr. No use-case writes to stdout.
- **Credential blindness.** Mason reads no enterprise credential variable and makes no authenticated request on the wrapped machinery's behalf — credentials reach it only through the inherited process environment, confining that machinery's known-unconditional credential-header injection to its own process. Upload credentials are read at the point of use, never stored on a rendered or logged object, and validated **before** any artifact is built. No code path logs an environment-variable *value* at any verbosity.
- **No configuration file in v1.** Configuration is flags and environment variables only, precedence uniformly flag → environment → default, with the knob set enumerated. Two configuration systems with undefined precedence is the classic source of "it works on my machine."
- **Safety by default.** Every mutating verb accepts a dry-run flag and defaults to it where the operation is irreversible. A PyPI upload is recognized as irreversible and the dry-run plan says so explicitly.
- **Every test runs against a fake root.** The suite ships a fixture root of stub scripts with canned output; no test requires a real installation, network, or recipe directory — otherwise Mason's own CI would depend on the very co-location the design admits is a constraint. Exactly one declared exception, and it skips cleanly rather than failing.
- **Workspace conventions are adopted wholesale, not reconsidered.** Member layout under the shared packages tree, a member manifest with no workspace table, a namespace package with no package initializer, one build manifest driving both artifacts, `argparse` (no CLI framework dependency for ergonomics alone), lean dependencies, Python floor `>= 3.12`.
- **Offline-safe and enterprise-neutral.** Every command not inherently requiring the network runs offline and network use is never implicit; Mason imposes no direct-internet assumption, inheriting proxy and mirror routing through the process environment; Mason's own logic works on linux-64, osx-arm64 and win-64 with platform limits belonging to the engines and reported as such; and Mason never renders templates or executes recipe content itself.

## Non-goals

- **Mason will never hold recipe knowledge.** Not a v1 deferral — a permanent property.
- **Mason is not a fork.** No extracted, vendored, or re-implemented copy of the canonical scripts, in any version.
- **Mason does not modify the wrapped surface** — it is governed by its own Spec and authoritative over Mason.
- **Mason does not solve dependencies.** It orchestrates solvers.
- **Mason does not replace the existing pixi task surface in v1.** Additive; nothing is removed or deprecated. The sibling project's failure was not the rebuild alone — it was a rebuild with no migration. Mason earns the surface first; migration is its own effort.
- **Mason does not ship a second MCP server** duplicating the existing 46 tools — that is the sibling's failure mode in miniature.
- **Mason is not a build system**, and **not a general-purpose release manager**: changelogs, tags, releases and version bumping are out.
- **No operation in a repository with no discoverable installation** — it would require changing a surface Mason may not edit, which is reimplementation by the back door.
- **No shipping to conda-forge from a project with no co-located recipe source directory.** The submission flow reads from that path and writes into a fork clone, and Mason may not change either. This is the honest v1 boundary, stated up front and reported by self-diagnosis before a release is attempted — **not** a hidden failure. The PyPI half has no such limit.
- **No trusted-publishing credential flow in v1** — token-based only.
- **No multi-ecosystem autotick** (CRAN/npm/cargo updaters), **no smart test extractor**, **no static dependency-version checker** — the origin Dream's frontier, not v1.
- **No application or binary project shapes** — v1 is `library` only.
- **No persistent state and no concurrency** — every operation is sequential in v1, and the per-target result shape already permits parallelism later without a redesign.

## Success signal

**Mason ships Mason.** The master switch: `mason package` publishes `pyforge-mason` itself — rehearsal to the test index first, then the real one — and its build produces the same conda artifact the repository's hand-run build triad produces today. Until Mason can ship Mason, the dual-ship claim is unproven, and the honest caveat is that what the repository dogfoods today is the dual-artifact **build**, not the ship: neither sibling package has a publish task, so the ship half is a genuine first, which is exactly why the rehearsal gates the irreversible upload.

Supported by five secondary signals, each demonstrable rather than asserted: the deny-list test is green at every commit **and its own planted-violation fixtures prove it is not vacuous**; the independence allow-list has exactly one entry; a gotcha added to the wrapped skill *after* Mason ships changes Mason's behaviour with **no change to Mason**; the conda artifact, wheel and sdist all build green from one manifest; and the governance check is green with exactly one sanctioned retrospective commit carrying a dated changelog entry and a semver bump.

Deliberately **not** optimized, and tracked as counter-metrics: Mason's own line count (approaching the wrapped machinery's scale means the wrap decision has quietly inverted), the recipe verb count (wrapping all 46 tools would be surface bloat, not product — coverage is not a goal), and adapter surface area (a growing adapter API means recipe logic is migrating into Mason one helper at a time).

## Assumptions

- The Charter's verb cadence (`recipe build`, `package --ship`, `environment lock`) is binding product scope, taken verbatim and never confirmed with a stakeholder.
- "Dual-ecosystem" means conda-forge + PyPI. npm, CRAN, CPAN and LuaRocks are *source* ecosystems for recipe generation, not ship targets.
- The target operator is the individual maintainer or small team already using pixi — not conda-forge core infrastructure, where the autotick-bot is the incumbent and Mason would be redundant.
- The conventions demonstrated by the two sibling packages are normative for a new workspace member. Inferred from two instances and their in-file comments; no written standard exists.
- The wrapped machinery's stdout is stable enough to parse — a **de-facto** contract evidenced by 46 MCP tools over an extended period with one known tolerance shim, not a formal one. Mason inherits the risk and bounds it with tolerant parsing plus the fidelity test.
- Local measurements (41,410 lines, 106 gotchas, 10 constraints, 46 MCP tools, 1,186 tests, 769 feedstocks, 17 scripts hardcoding the recipe directory) are point-in-time and **will drift** — used for shape arguments, never as commitments.
- PyPI and the forge can be interrogated cheaply enough to make interrogation-based idempotence practical. If not, the revisit must reopen the no-persistent-state rule explicitly rather than adding a cache quietly.
- `packaging` is the only non-stdlib runtime import Mason needs; any addition must be justified at the story that introduces it.
- The conda build backend's preview member-package semantics remain stable for the duration — both existing members already carry this exposure.
- Mason's own package is representative enough to prove shipping. It is **pure Python**; a compiled package would exercise paths this self-hosting test does not.
- `pixi publish`'s documented silence on PyPI reflects an absent feature — not verified against its source.

## Open Questions

The chain's adversarial review returned *major revision required* and **was resolved**: revision 2 of the PRD added four requirements and four decision records, fixing the closeout contradiction, the missing ship verb, the flagship-journey scope conflict, and two requirement-level contradictions. Nothing below is a blocker; these are the decisions the chain deliberately left to architecture, implementation, or a later scoping round.

1. **Which wrapped script backs each recipe verb?** The adapter's declaration table must name one per verb — mechanical, no invariant depends on it, but it must exist before the first recipe-verb story starts.
2. **Which recipe verbs beyond the eight in scope earn a place?** Deferred to usage; the verb-count counter-metric warns against reflexive coverage.
3. **What exactly is the knowledge deny-list's content?** The rule is fixed; the concrete pattern set is an implementation artifact that must be reviewable and hard to weaken silently, and needs a review gate of its own — a vacuous deny-list passes forever while the seam sits unguarded.
4. **Does the channel target upload via `pixi publish`, `anaconda upload`, or both?** An engine choice with no product consequence; both satisfy the protocol.
5. **Should the lock capability prefer `conda-lock` or `pixi.lock` when both are viable**, and is the relationship between them one of succession? Unresolved by available sources; may need both adapters.
6. **Is the CI-parity container build reachable through the adapter at all?** That path is a task rather than a canonical script, and the local builder is explicitly container-less. If no adapter-reachable entry point exists, the CI-parity build drops from scope — it is the one part of the build requirement with no confirmed wrappable target.
7. **Can the governance check inspect the effort's commit range automatically** in this repository's branching model, or must it be a documented manual gate?
8. **Does Mason own multi-ecosystem autotick, or is that another station's territory?** The origin Dream places it in the packaging factory; the Charter omits it from Mason's cadence. This is the most load-bearing deferral — the Dream's headline frontier item.
9. **Does Mason declare a minimum version of the wrapped machinery** once coupling fragility is observed? v1 declares none: delegation is by argv and the machinery's own semver governs its behaviour, so a break is fixed in the adapter.
10. **Is there a real user for application or binary project shapes**, or is `library` the whole product?
11. **Competitive coverage risk** — the survey was assembled from known primary sources **without a web-search budget**, and a discovery sweep for unknown dual-publish entrants has not been run. An existing entrant would invalidate the central decision's differentiation premise.
12. **Does the conda-forge shipping boundary change the product's positioning claim**, or is "the PyPI half works everywhere, the conda half works where your recipes live" an acceptable public story?
13. **Should self-diagnosis be a fourth noun or a top-level verb?** Currently top-level; cosmetic, no invariant affected.

---

## Satellite: Presenton (air-gapped conda-native repackaging)

**Status: BLOCKED.** This satellite Spec was finalized 2026-07-25 and governs a genuinely different
product from `mason` itself: an air-gapped, conda-forge-native repackaging of the third-party
Presenton AI deck-generation app for Red Hat OpenShift. Its owning Dream
(`docs/dreams/presenton-pixi-image.md`) carries `status: archived`, `archived-reason: blocked`,
`blocked-on: Phase-0 decision gate (Epic 1)` — no story has entered implementation, and the six
Phase-0 exit criteria named in the Open Questions below (most load-bearingly, exit 6a: whether
Microsoft's disconnected on-prem stack already ships a Copilot-for-PowerPoint-equivalent) remain
unresolved.

**Contradiction flagged — the most direct one in this whole consolidation.** On 2026-08-02, *before*
this consolidation, this satellite's own `SPEC.md` was rewritten from a live five-field kernel into an
archived retirement record. That retirement record names, as an explicit **non-goal**: *"Folding this
Dream's intent into `pyforge-mason`'s own narrative"* — reasoning that *"the two are genuinely
different subject matter... archiving this separately (rather than absorbing it) reflects that
difference honestly."* What follows in this section does exactly what that non-goal forbade. It is
done at the user's explicit direction, after being shown that separation language, overriding the
2026-08-02 retirement decision for the **planning-chain tier only** — the Dream-level narrative and
the epics/blocked-status stay separate (per `docs/dreams/pyforge-mason.md` § *Related but out of
scope*). This is recorded here rather than silently resolved. See
`archive/_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-presenton-pixi-image/` for
both the retirement record and (in git history within that archived copy) the live five-field kernel
this section reconstitutes.

**No other contradiction found** between the two kernels' Constraints/Non-goals: Presenton's own
AD-19 ("recipe.yaml content itself is out of this Spec's scope, governed by conda-forge-expert per
CLAUDE.md Rules 1 and 2") is consistent with — not contradicting — Mason's own stance that CFE is
authoritative over recipe semantics.

**Own scope, continued numbering.** Presenton's capabilities are folded in below as **CAP-8..CAP-13**
(continuing after this Spec's own `CAP-7`), and its Constraints' `AD-n` references are renumbered to
**AD-17..AD-24** to match the renumbering already applied in the merged
`ARCHITECTURE-SPINE.md`:

| Original ID | Renumbered ID |
|---|---|
| CAP-1 Air-gapped browser rendering | **CAP-8** |
| CAP-2 Clean-room deck export pipeline | **CAP-9** |
| CAP-3 LLM provider abstraction and tiering | **CAP-10** |
| CAP-4 Signed air-gapped image assembly | **CAP-11** |
| CAP-5 OCP deployment and operations | **CAP-12** |
| CAP-6 Upstream drift defense | **CAP-13** |
| AD-1 (build routing) | **AD-17** |
| AD-2 (one true port) | **AD-18** |
| AD-3 (recipe/image boundary) | **AD-19** |
| AD-5 (single provenance pass) | **AD-21** |
| AD-6 (phase-boundary enforcement) | **AD-22** |
| AD-8 (SCC target) | **AD-24** |

*(AD-4 and AD-7 are cited only inside capability success text below, renumbered to AD-20 and AD-23
respectively, consistent with the architecture spine — Presenton's own Constraints section never
headed those two directly.)*

### Presenton Capabilities

- **CAP-8**
  - **intent:** The image renders decks using a bundled, air-gap-buildable Chromium, with zero reachable public CDN at build or runtime.
  - **success:** `playwright-with-chromium` builds, validates, is scanned, and is optimized; AD-17's zero-external-CDN build routing holds; AD-20's Chromium sandbox defaults to a documented `--no-sandbox` posture compatible with OpenShift `restricted-v2`/`restricted-v3`.
- **CAP-9**
  - **intent:** The image renders AI-generated slide content into an editable `.pptx` (image-overlay + extracted-text-shapes fidelity — Decisions Log Q1) carrying a real `docProps/thumbnail.jpeg`, replacing the opaque upstream export bundle and `convert-linux-x64` binary with clean-room, source-available components wired in via Presenton patches.
  - **success:** `presenton-export-node`, `pptx-assembler`, and `pptx-thumbnail-inject` each build+validate+scan+optimize and pass Fixture Set 1 — `AC-FX-AUTHOR-01` (byte/structural equivalence) and `AC-FX-AUTHOR-02` (image SSIM ≥ 0.99).
- **CAP-10**
  - **intent:** The deployed app selects among three OpenAI-compatible LLM tiers (Tier 1 external corporate proxy, Tier 2 in-cluster `llama.cpp` sidecar, Tier 3 init-container GGUF fetch) purely via one env-var contract, with the `copilot-bridge` VSIX covering the VS Code developer inner loop.
  - **success:** `llmai` lands on conda-forge; Helm `values.llmProvider.tier` selects a sub-block with no per-tier code fork (AD-18); per-refinement latency ≤10s P95 on Tier-1 (measurable outcomes table).
- **CAP-11**
  - **intent:** The five confirmed recipes assemble into one pixi-locked, reproducibly-buildable OCI image, carrying a pre-wired, default-off memory-subsystem feature flag, with SBOM generation and signed attestation as the final build stage.
  - **success:** image builds reproducibly with zero external CDN access; CycloneDX (primary) + SPDX (secondary) SBOM plus a cosign attestation ship with every build (AD-21); the `presenton-memory` pixi feature + `values.memory.enabled` (default `false`) are wired end to end (AD-23).
- **CAP-12**
  - **intent:** The image deploys via a standard Helm chart on OpenShift with Restricted-SCC-compatible defaults, ships a versioned `/metrics` schema artifact, and gives day-0/day-2 operators preflight, smoke, credential-rotation, and mark-broken-response fixtures.
  - **success:** AD-24's `restricted-v2` defaults hold (capabilities dropped, `seccompProfile: runtime/default`, no privilege escalation, non-root arbitrary UID, no hardcoded UID/GID); `AC-FX-INSTALL-*` and `AC-FX-DAY2-01..03` pass; the `/metrics` schema is versioned and shipped with the chart.
- **CAP-13**
  - **intent:** Recipe-maintainers get a weekly, non-build-blocking drift-detection harness comparing current upstream Presenton against the captured Fixture Set 1 baseline, filing an auto-issue on breaking drift, in a CI workflow whose network egress is strictly separated from the air-gapped build pipeline.
  - **success:** `AC-FX-MAINT-01..03` and `AC-FX-DRIFT-01..04` all pass; the online-capture workflow never shares a runner or environment with the air-gapped build workflow, enforced at the network-policy level (AD-22), not by convention.

### Presenton Constraints

- **AD-17 build routing:** every channel/package resolution in the build pipeline routes through the `*_BASE_URL` env-var family; no recipe, build step, or CI job hardcodes a public URL; `pixitainer` only consumes the pixi-locked environment, never fetches externally itself.
- **AD-18 one true port:** the LLM provider is the *only* swappable seam. Presenton and the Helm chart set only `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` (plus optional `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL` passthrough) to select a tier; no tier-specific code path may creep into the app.
- **AD-19 recipe/image boundary:** the image-assembly layer consumes published, versioned conda artifacts by name and pin only — it never vendors or patches recipe internals. `recipe.yaml` content itself is out of this Spec's scope, governed by `conda-forge-expert` per CLAUDE.md Rules 1 and 2.
- **AD-21 single provenance pass:** exactly one `syft`+`cosign` step per image build (post-`pixitainer`, pre-registry-push), producing CycloneDX (primary) + SPDX (secondary) in one deterministic pass — never two disagreeing SBOMs for the same image tag.
- **AD-22 phase-boundary enforcement:** the online-capture/drift CI workflow and the air-gapped build workflow never share a runner or environment; the air-gapped pipeline has zero network egress, enforced at the CI-runner/network-policy level, not by convention.
- **AD-24 SCC target:** Helm SecurityContext defaults to `restricted-v2` compatibility on every target cluster — all capabilities dropped, `seccompProfile: runtime/default`, `allowPrivilegeEscalation: false`, non-root arbitrary UID via the GID-0/`chmod g=u` convention, no hardcoded UID/GID anywhere; `restricted-v3` (`hostUsers: false`) is asserted but not separately branch-tested until the AD-20 Chromium-sandbox spike runs.
- **Hard, no-regression constraints:** zero LibreOffice in the runtime, zero non-conda-forge packages in the runtime, zero non-pixi build steps, zero external CDN access at build or runtime.
- **Phase 0 gates v1 build kickoff (6 exit criteria):** exit 1 (build-complete-hold: GGUF model+quant chosen, bench methodology, source-pathway with alt-source clause) is the critical-path long-pole gating exits 2–3; exits 4/5/6 are independent. Exit 6 (Microsoft disconnected-stack check + memory-subsystem scope decision) is the highest-urgency independent exit because it bears on whether the core differentiator still holds and changes the confirmed recipe count (5 vs 7) — **unresolved, see Open Questions.**

### Presenton Non-goals

- `template-style-extractor` — dropped entirely; upstream Presenton already ships LibreOffice-free template import (stdlib `zipfile`+`ElementTree`, native ODF, `pdfplumber` MIT for PDF) with the identical legacy-format rejection this project had independently proposed (Decisions Log Q2, superseded).
- The end web UI of upstream Presenton — out of scope; upstream owns the React/Next.js UI entirely.
- A full JetBrains plugin — v1 ships a docs-only one-pager (REST + OpenAPI + Postman collection); the full plugin is a Growth-tier item.
- Upstreaming `chromium` directly to conda-forge — still stalled at staged-recipes#21431 with no 2026 movement; v1 vendors `chrome-headless-shell` via `playwright-with-chromium` instead; direct upstreaming is Vision-tier.
- An SVG→DrawingML fidelity tier — net-new conda-forge work with no existing library; Vision-tier, not v1/Growth.
- Knowledge-base integration beyond prompt + uploaded files — explicitly held against customer pressure as a v1 boundary (Landing Condition 4); decks whose source material doesn't fit in prompt+files stay out of scope until Vision tier.

### Presenton Success signal

A two-gate JTBD that must both hold, because either collapsing kills the product on its own axis. **Buyer-gate** (binary, procurement-visible): all confirmed recipes upstream-merged on conda-forge → landed on the customer's JFrog Artifactory mirror → OCI image on the customer's registry, with SBOM (CycloneDX+SPDX) + a signed-image (cosign) attestation + a versioned `/metrics` schema shipped with every build. **User-gate** (behavioral, renewal-driving): one pilot customer clears a three-signatory acceptance checklist (CISO/platform-owner + named end-user lead + backup-signatory continuity clause) within 12 weeks of go-live (18 with the one-time extension) — requiring `AC-PILOT-001` (≥60% of piloted decks show "edit-not-rewrite" behavior), ≤30 min P95 prompt-to-first-slide-renderable, and ≤10s P95 per-refinement latency on Tier-1. Missing either gate within its window returns the program to Phase 0 scoping rather than limping forward.

### Presenton Assumptions

- Q1 (editable-PPTX fidelity bar) is locked at image-overlay + extracted-text-shapes, matching upstream `convert-linux-x64` behavior — not native chart objects or theme/master editability.
- Q3 (LLM provider strategy) is locked: `llmai`'s existing `CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` contract covers all three production tiers plus the `copilot-bridge` dev path without any Presenton source patch.
- Q4 (air-gap definition) is locked at full air-gap: build CI runs inside the perimeter against an internal JFrog Artifactory mirror; every dependency must be allowlisted on the mirror or the build fails.
- The reference LLM class for cost/latency targets, the Tier-2 default GGUF model+quantization, and the exact repo landing path for the build/Helm artifacts are all deferred to Phase 0 / architecture-spike resolution and do not change this Spec's shape.

### Presenton Open Questions

- **Phase-0 exit 6(a), Redmond-contingency check:** does Microsoft's disconnected stack (Azure Local disconnected operations + Microsoft 365 Local + Foundry Local, GA worldwide 2026-02-24) already include, or roadmap, a Copilot-for-PowerPoint-equivalent deck-generation capability? Unconfirmed — directly determines whether Risk R3 (existential, JTBD-collapsing) is materialized, partially materialized, or infrastructure-only. Must resolve before further v1 build investment.
- **Phase-0 exit 6(b), memory-subsystem scope:** does `mem0ai` + `fastembed-vectorstore` (unconditional Presenton dependencies, neither on conda-forge) become two additional v1 recipes (5→7 total), or is the memory/chat-history subsystem documented as dropped for v1? Architecture (AD-23) pre-wires both branches, but the no-op-without-a-Presenton-source-patch path is not yet verified — if a patch is required, the maintenance-burden model changes.
- **`psycopg` license flag (Risk R7 replacement):** LGPL-3.0-only, a different obligation class than the Apache/MIT-dominated rest of the stack — flagged for buyer legal/compliance review alongside the JFrog allowlist gap analysis (Phase 0 exit 4); likely-but-not-confirmed acceptable.
