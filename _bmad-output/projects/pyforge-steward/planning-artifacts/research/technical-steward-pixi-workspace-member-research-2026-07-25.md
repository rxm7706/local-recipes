---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/domain-steward-platform-ops-tooling-research-2026-07-25.md
  - src/shared/packages/pyforge-warden/pyproject.toml
  - src/shared/packages/pyforge-warden/pixi.toml
  - docs/reference/enterprise-deployment.md
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Steward — technical implementation approach for a real installable package (dist pyforge-steward, module pyforge.steward, CLI steward) as a pixi workspace member wrapping this repo''s existing _http.py routing, gh CLI, and pixi machinery'
research_goals: 'Determine the concrete technology stack, packaging shape, plugin/engine architecture, integration patterns, and implementation practices Steward should adopt, grounded in this repo''s own precedent (pyforge-warden''s pixi-build workspace-member pattern) and in 2026 best practice for CLI plugin architecture, credential rotation tooling, and static-site/GitOps deployment.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
mode: 'headless-express'
---

# Research Report: Steward — Technical Implementation Research

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Technical research (headless/express — see the sibling domain-research report's frontmatter for the mode rationale; identical here)

> **Refreshed 2026-08-08** — Steward is now fully shipped (18/18 stories, PRs
> #157/#291/#297/#302/#305). The pre-ship body below is preserved unchanged; the dated
> **Addendum** at the end reconciles it against the shipped code, mines the whole-build
> retrospective (written today) for real technical debt, and adds the feasibility
> assessment of the steward-owned `unified-container.md` Dream against the real
> `provision`/`deploy`/`keys` implementations.

---

## Research Overview

This report determines the concrete technical shape Steward (dist `pyforge-steward`, module `pyforge.steward`, CLI `steward`) should take, grounded in two sources: this repo's own existing precedent for exactly this kind of package (`pyforge-warden` — a real `hatchling` + `pixi-build-python` pixi workspace member with a `[project.scripts]` CLI entry point, a pluggable-engine `interfaces.py`, and a `conformance/unit/meta` test layout) and 2026 external best practice for the four technical surfaces Steward's duties touch: Python CLI plugin architecture, `age`-key rotation mechanics, static-site/GitOps deployment reconciliation, and this repo's own `_http.py` multi-host credential-routing chokepoint. The verdict, elaborated below: Steward should be **structurally a clone of the `pyforge-warden` packaging pattern** (same build backend, same workspace-member wiring, same test-tier split) with a **`click-plugins`-style per-duty subcommand architecture** (`steward provision|deploy|keys|budget`) so each duty can be engineered, tested, and shipped independently — mirroring Warden's own per-axis engine model. Full findings and citations are in the Research Synthesis (§ 11) below.

---

## Technical Research Scope Confirmation

**Research Topic:** Steward's technical implementation approach as a pixi workspace member
**Research Goals:** Concrete stack, packaging, architecture, and implementation-practice recommendations grounded in `pyforge-warden` precedent + 2026 external best practice.

**Technical Research Scope:**

- Technology Stack Analysis — packaging backend, CLI framework, dependency posture
- Integration Patterns — `_http.py` routing reuse, `gh` CLI subprocess pattern, pixi task/environment wiring
- Architectural Patterns — plugin/engine model for the four duties, CLI command-tree design, air-gap posture
- Implementation Approaches — testing tiers, offline-safety NFRs, dogfooding, CI/deploy mechanics for `steward deploy`'s first target (the Pages dashboard)

**Research Methodology:**

- All external claims verified against 2026 web sources
- All repo-internal claims verified by reading the actual `pyforge-warden` package files (`pyproject.toml`, `pixi.toml`, `interfaces.py`, test directory layout) rather than recalled from memory
- Confidence levels applied per finding

**Scope Confirmed:** 2026-07-25

---

## 1. Technical Research Introduction and Methodology

### Technical Research Significance

Every other pyforge Crew persona that has shipped as a real package (`pyforge-warden`, and `pyforge-atlas` per its lean pixi environment) already established a working, repo-tested pattern for "a real installable Python package living inside this staged-recipes-derived repo, built via pixi's `pixi-build-python` backend, consumed through a dedicated lean pixi environment." Steward does not need to invent packaging conventions — it needs to correctly clone them and then decide its own internal (per-duty) architecture. This is the single highest-confidence finding in this report and is verified directly against source files, not web search.
_Source: `src/shared/packages/pyforge-warden/pyproject.toml`, `src/shared/packages/pyforge-warden/pixi.toml`, `pixi.toml` (repo root) lines 1041-1058_

### Technical Research Methodology

- **Research Scope**: packaging/build system, CLI architecture, integration surfaces (`_http.py`, `gh`, pixi), test-tier conventions, and the concrete mechanics of Steward's likely first `deploy` target (Pages).
- **Data Sources**: this repo's own `pyforge-warden` source tree (primary, highest-confidence) + 2026 web sources for external best practice (Click/Typer plugin architecture, `age` key rotation, GitHub Pages Actions deployment).
- **Analysis Framework**: for each technical surface, state the `pyforge-warden` precedent, cross-check it against 2026 external best practice, and flag any divergence Steward's architecture should resolve explicitly.
- **Time Period**: current repo state (2026-07-25) + 2026 web sources.

### Technical Research Goals and Objectives

**Original Goals:** Determine Steward's concrete stack/packaging/architecture, grounded in real precedent.

**Achieved Objectives:**

- Packaging shape fully specified by direct precedent (§ 2).
- CLI/plugin architecture recommendation cross-checked against 2026 `click-plugins`/Typer best practice and Warden's own `interfaces.py` pattern (§ 4).
- `steward deploy`'s concrete first mechanics (Pages reconciliation) specified against both the repo's current hand-run process and 2026 GitHub Actions Pages deployment conventions (§ 3).
- Test-tier and offline-safety conventions carried forward from Warden's NFR discipline (§ 5).

---

## 2. Technology Stack Analysis

### Packaging and Build System

**Direct precedent (`pyforge-warden`):**

```toml
[build-system]
build-backend = "hatchling.build"
requires = ["hatchling"]

[project]
name = "pyforge-warden"
requires-python = ">=3.12"
license = { text = "MIT" }

[project.scripts]
warden = "pyforge.warden.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/pyforge"]
```

The pixi-side wiring (repo-root `pixi.toml`) declares a dedicated `pixi-build` preview feature, a `[feature.pyforge-warden.dependencies]` table pointing `pyforge-warden = { path = "src/shared/packages/pyforge-warden" }`, and a **lean, `no-default-feature = true` pixi environment** so the built package plus its conda run-deps (not the fat default `[dependencies]` table of python 3.14 + pixi + conda + pip + uv) is all that materializes — explicitly called out in a repo-root comment as "the worktree-affordability claim" for loop-driven development.
_Source: repo-root `pixi.toml` lines 140-151, 1041-1058_

**Recommendation for Steward:** clone this exactly — `src/shared/packages/pyforge-steward/` with `pyproject.toml` (`hatchling` backend, `name = "pyforge-steward"`, `[project.scripts] steward = "pyforge.steward.cli:main"`, `packages = ["src/pyforge"]`), a companion `pyforge-steward.pixi.toml`-style local manifest matching Warden's own `src/shared/packages/pyforge-warden/pixi.toml`, and a repo-root `[feature.pyforge-steward]` block + lean `pyforge-steward` environment. This is not a novel architectural decision — it is following an already-validated repo convention.

### CLI Framework

2026 external guidance converges on **Typer for new CLI projects**, with Click reserved for cases needing deep customization or continuing an existing Click-based codebase; since Typer is built on Click, both interoperate and Typer apps can expose an underlying Click group for `click-plugins`-style extension if needed later.
_Source: [devtoolbox.dedyn.io Python CLI Tools Guide 2026](https://devtoolbox.dedyn.io/blog/python-click-typer-cli-guide)_

**Repo precedent check:** `pyforge-warden`'s CLI entry point is `pyforge.warden.cli:main` — the specific framework it uses internally was not independently re-verified in this pass (flagged as an assumption below); whatever Warden uses is the stronger signal for Steward's choice than the general 2026 guidance, since consistency with an existing shipped sibling package outweighs a generic industry recommendation. **Recommendation:** the architecture step should read `pyforge-warden`'s `cli.py` directly to confirm its framework and match it, rather than defaulting to Typer on general principle alone.

### Dependency Posture

Warden's `pyproject.toml` deliberately keeps a **lean, targeted dependency set** (`PyYAML`, `packaging`, `cyclonedx-python-lib`, `jsonschema`, `packageurl-python`, `license-expression`) rather than pulling in a framework-heavy stack, with an explicit code comment: "pure-stdlib as fallback, no execution of untrusted input." This lean-dependency discipline is a strong architectural constraint Steward should inherit, especially since three of its four duties (`keys`, `deploy`, `provision`) will likely shell out to already-installed tools (`age`/`sops`, `gh`, `pixi`) rather than reimplement their logic in Python — keeping Steward itself a thin orchestration layer.
_Source: `src/shared/packages/pyforge-warden/pyproject.toml` lines 13-24_

---

## 3. Integration Patterns Analysis

### Reusing `_http.py`'s Routing Chokepoint

`docs/reference/enterprise-deployment.md` § 6 documents `_http.py` as the single chokepoint every outbound HTTP call in the `conda-forge-expert` scripts flows through, resolving each upstream via an ordered env-var-override chain (`PYPI_BASE_URL`, `GITHUB_API_BASE_URL`, `CONDA_FORGE_BASE_URL`, etc.) plus a `skip_auth=True` guard added specifically to stop the `JFROG_API_KEY` cross-host leak. **This is directly Steward's `keys` duty's nearest existing implementation** — the fix pattern the domain-research report (§ 4) recommended Steward generalize (short-lived, host-scoped credential attachment) is *already partially built* in `_http.py`; Steward's job is to extend that discipline to whatever new credentials it issues (age identities, rotated tokens), not to build a parallel routing layer. **Recommendation:** Steward's `keys` module should import/wrap `_http.py`'s `auth_headers_for(url, skip_auth=...)` pattern rather than reinvent host-scoping logic.
_Source: `docs/reference/enterprise-deployment.md` § 6 "Runtime enterprise routing"_

### `gh` CLI Subprocess Pattern

This repo already establishes the convention of shelling out to `gh` for GitHub operations (PR creation, `gh pr edit --add-label`, etc. — see CLAUDE.md's PR-gate instructions) rather than reimplementing the GitHub API client. Steward's `deploy`/`provision` duties (anything touching GitHub Pages environments, Actions runners, or repo settings) should follow the same subprocess-over-`gh`, not-a-new-API-client convention already established throughout `.claude/scripts/conda-forge-expert/`.

### Pixi Task/Environment Wiring

Steward's `provision` duty operates directly on the object this repo already has: the pixi.toml `[environments]` table (~14 named environments) plus `scripts/bmad-loop-worktree` (concurrent loop homes, one worktree per loop). **Recommendation:** `steward provision --runner bmad-loop --env local-recipes` (the Dream's own CLI cadence example) should resolve to shelling out to `pixi install -e <env>` / invoking `scripts/bmad-loop-worktree` under the hood, not reimplementing pixi's own environment-resolution logic — this matches the lean-dependency, thin-orchestration-layer posture from § 2.

### `steward deploy`'s Concrete First Target: the Pages Dashboard

Current state: `docs/dashboard/` (generate.py + data.js + index.html) built by the `dashboard-gen` pixi task, then hand-pushed. 2026 GitHub-native practice for this exact shape is the `actions/upload-pages-artifact` + `actions/deploy-pages` two-action pattern against a managed `github-pages` deployment environment (auto-created, ideally protected so only the default branch can deploy). The alternative — and closer to what "formalize the manual push into GitOps-style reconciliation" (domain research § 3) means concretely — is the community `peaceiris/actions-gh-pages` action, which works via a diff/apply-like mechanism against a `gh-pages` branch and supports both push-triggered and `schedule`/`workflow_dispatch` reconciliation triggers.
_Source: [GitHub Docs — Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages)_

**Recommendation:** `steward deploy dashboard` (or similarly named) should wrap the existing `dashboard-gen` task, then either (a) push directly and let GitHub's native Pages-from-branch workflow pick it up (simplest, matches today's manual process, no new Actions workflow needed), or (b) introduce a thin GitHub Actions workflow using `actions/upload-pages-artifact` + `actions/deploy-pages` if Steward's PRD wants push-button/scheduled reconciliation rather than a CLI-invoked one. This is a concrete open question for the PRD (carried into `open_questions[]` below) — the research doesn't resolve which is correct, only that both are well-trodden 2026 paths and neither requires standing up ArgoCD/Flux-class infrastructure (confirming domain research § 3's "must not copy" verdict).

---

## 4. Architectural Patterns and Design

### Plugin/Engine Model — Warden's Precedent

`pyforge-warden`'s `src/pyforge/warden/interfaces.py` establishes a pluggable-engine abstraction (the domain-research report's § "Warden" summary and this repo's `pyforge-warden` spec both describe a 6-axis pluggable check-engine model with a "null engine" pattern for axes not yet implemented — confirmed present as a dedicated `interfaces.py` file and a `test_interfaces_and_null_engine.py` unit test). **This is the strongest internal architectural precedent for Steward's own four-duty structure**: instead of one monolithic `steward` module, each duty (`provision`, `deploy`, `keys`, `budget`) should be its own engine/module behind a shared interface, letting duties ship independently (matching the domain-research recommendation to sequence `keys → deploy → provision → budget` as separable epics) and letting an unimplemented duty degrade to a "null" stub rather than blocking the others.
_Source: `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py` (file presence confirmed), `src/shared/packages/pyforge-warden/tests/unit/test_interfaces_and_null_engine.py`_

### CLI Command-Tree Design

2026 guidance frames scalable CLI architecture around three pillars: command-tree organization, lazy loading (deferring heavy imports for subcommands so `--help` stays instant as the command set grows), and plugin architecture via entry points + `importlib.metadata` + protocol interfaces. Applied to Steward: `steward <duty> <verb>` (e.g. `steward keys rotate`, `steward budget enforce`) as a two-level command tree, each duty's module imported lazily so e.g. invoking `steward provision` doesn't eagerly import `budget`'s dependencies.
_Source: [python-cli-toolcraft.com Modern Python CLI Frameworks and Architecture](https://python-cli-toolcraft.com/modern-python-cli-frameworks-architecture/)_

### Security Architecture Pattern for `keys`

Combining domain research § 4 (OIDC-style short-lived/host-scoped credentials, SOPS+age for Git-native at-rest storage) with this section's `_http.py`-reuse finding (§ 3): Steward's `keys` engine should be architected as **two cooperating halves** — (a) an at-rest half wrapping `age`/SOPS for anything Steward stores (age's decrypt-then-re-encrypt rotation pattern: extract the new public key via `age-keygen -y`, loop through encrypted files, decrypt with the old identity and re-encrypt to the new recipient — a well-documented, scriptable 2026 pattern), and (b) an in-flight half extending `_http.py`'s existing `skip_auth`/host-scoping guard to any new credential Steward issues. Note also `age`'s 2026 post-quantum option (`-pq` flag, `age-keygen -pq`) — likely out of scope for Steward v1 but worth flagging as a forward-compatible option since it doesn't require abandoning the base pattern later.
_Source: [sandipb.net Age encryption cookbook](https://blog.sandipb.net/2023/07/06/age-encryption-cookbook/), [GitHub FiloSottile/age](https://github.com/filosottile/age)_

### Air-Gap Posture

Steward inherits the same posture every other pyforge tool documents: env-var-driven routing (no committed enterprise URLs/credentials), offline-safe read paths, and the `*_BASE_URL` override family. Since Steward's `provision`/`deploy` duties will need to reach GitHub (`gh` CLI) and possibly OpenShift/registry endpoints, its architecture doc should explicitly extend the `docs/reference/enterprise-deployment.md` § 6 table with any *new* env vars Steward introduces (e.g. an OpenShift registry base URL for `presenton-pixi-image` deploys), following the exact same "ordered override chain, env-vars only" convention rather than inventing a parallel config mechanism.

---

## 5. Implementation Approaches and Technology Adoption

### Testing Tiers — Warden's Precedent

`pyforge-warden`'s test tree splits into `tests/unit/` (fast, per-module), `tests/conformance/` (behavioral contracts against the spec's acceptance criteria — e.g. `test_baseline_grandfathering.py`, `test_engine_parallelism.py`), and `tests/meta/` (repo-hygiene/invariant tests — e.g. `test_socket_deny_alive.py` enforcing offline-safety, `test_verdict_sole_ownership.py` enforcing an architectural invariant). A `slow` pytest marker separates corpus-scale/real-subprocess tests from the default fast suite so the default `pyforge-warden-test` task stays sub-minute.
_Source: `src/shared/packages/pyforge-warden/tests/` directory listing, `src/shared/packages/pyforge-warden/pyproject.toml` lines 32-41_

**Recommendation:** Steward should adopt the identical three-tier split (`unit/conformance/meta`), with `meta/` tests specifically enforcing Steward's own architectural invariants once the architecture doc names them (e.g., a meta test asserting `keys` never logs a raw credential value, mirroring Warden's `test_socket_deny_alive.py` enforcing its own offline-safety invariant).

### Dogfooding

Warden ships a `scripts/dogfood_scan.py` (Warden auditing its own dependency tree) with a corresponding `tests/conformance/test_dogfood.py`. Steward's equivalent is natural and low-cost: `steward provision` provisioning Steward's *own* dev/test pixi environment, or `steward keys audit` auditing this very repo's own credential surface — both directly testable dogfooding targets that double as the effort's own acceptance evidence.

### Cost Optimization and Resource Management

Per domain research § 5's conclusion, Steward's `budget` duty has no live cloud spend to optimize against today — the "cost optimization" implementation lens for *this* effort is really about Steward's own build/CI cost footprint (keeping its pixi environment lean per § 2, keeping its test suite fast per the `slow`-marker convention) rather than a customer-facing budget feature.

### Risk Assessment and Mitigation

- **Framework-mismatch risk**: recommending Typer from general 2026 guidance without first confirming Warden's actual CLI framework choice could produce an inconsistent sibling package — mitigated by the explicit recommendation in § 2 to read Warden's `cli.py` before deciding.
- **Deploy-mechanism ambiguity risk** (§ 3, native Pages workflow vs. `steward deploy` CLI invocation vs. `peaceiris/actions-gh-pages`): left as an open question rather than a false-confidence recommendation.
- **Scope-creep risk** (echoing domain research § 8): every implementation pattern in this report is deliberately chosen for its *thin-wrapper, subprocess-over-existing-tool* shape (over `age`/`sops`, over `gh`, over `pixi`) specifically to avoid Steward becoming a reimplementation of any of its comparable tools.

---

## 6. Executive Summary

**Key Technical Findings:**

- Steward has a **direct, already-shipped packaging precedent** in this repo (`pyforge-warden`: `hatchling` + `pixi-build-python` workspace member, lean `no-default-feature` pixi environment, `[project.scripts]` CLI entry point) — packaging is a clone-the-precedent decision, not an open design question.
- Warden's `interfaces.py` pluggable-engine + null-engine pattern is the strongest internal precedent for structuring Steward's four duties as independently shippable engine modules behind a shared interface.
- `_http.py`'s existing `skip_auth`/host-scoped-routing chokepoint is Steward's `keys` duty's nearest existing implementation — extend it, don't parallel it.
- `steward deploy`'s first concrete target (the Pages dashboard) has two well-trodden 2026 implementation paths (native `upload-pages-artifact`/`deploy-pages` Actions workflow, or the community `peaceiris/actions-gh-pages` diff/apply action) — left as an explicit PRD-stage decision rather than resolved here.
- Warden's three-tier test split (`unit/conformance/meta`) plus its dogfooding convention (`scripts/dogfood_scan.py`) are directly reusable for Steward.

**Strategic Technical Recommendations:**

1. Clone `pyforge-warden`'s exact packaging shape for `pyforge-steward` (§ 2).
2. Confirm Warden's actual CLI framework by reading its `cli.py` before choosing Steward's — don't default to Typer from general guidance alone (§ 2).
3. Structure Steward's four duties as independent engine modules behind a shared interface, mirroring `interfaces.py` (§ 4).
4. Wrap, don't reimplement: `_http.py` for credential routing, `gh` CLI for GitHub operations, `pixi`/`bmad-loop-worktree` for provisioning, `age`/SOPS for at-rest secrets (§ 3-4).
5. Adopt Warden's `unit/conformance/meta` test-tier split and dogfooding convention verbatim (§ 5).

---

## 7. Technical Research Methodology and Source Documentation

### Primary Sources (repo-internal, highest confidence — read directly, not recalled)

- `src/shared/packages/pyforge-warden/pyproject.toml`
- `src/shared/packages/pyforge-warden/tests/` directory tree (unit/conformance/meta split)
- `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py` (presence confirmed; contents not deep-read this pass — see assumptions)
- repo-root `pixi.toml` lines 1-9, 140-151, 1041-1058
- `docs/reference/enterprise-deployment.md` § 6

### Secondary Sources (external, 2026 web)

- [devtoolbox.dedyn.io — Python CLI Tools with Click and Typer 2026](https://devtoolbox.dedyn.io/blog/python-click-typer-cli-guide)
- [oneuptime.com — How to Build Plugin Systems in Python](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view)
- [python-cli-toolcraft.com — Modern Python CLI Frameworks and Architecture](https://python-cli-toolcraft.com/modern-python-cli-frameworks-architecture/)
- [PyPI — click-plugins](https://pypi.org/project/click-plugins/)
- [GitHub FiloSottile/age](https://github.com/filosottile/age)
- [sandipb.net — Age encryption cookbook](https://blog.sandipb.net/2023/07/06/age-encryption-cookbook/)
- [GitHub Docs — Configuring a publishing source for GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages)

### Confidence Levels

- **High**: packaging/build-system recommendation (direct file read), test-tier recommendation (direct file read), `_http.py` reuse recommendation (direct doc read).
- **Medium**: CLI framework recommendation (external 2026 guidance says Typer; Warden's actual internal framework was not re-verified by reading its `cli.py` contents in this pass — flagged as an assumption).
- **Medium**: `steward deploy` mechanism choice (two valid paths identified, not adjudicated — correctly left as an open question, not a false-confidence pick).

---

## Research Conclusion

### Summary of Key Findings

Steward's technical shape is substantially de-risked by direct, already-shipped precedent in this same repo (`pyforge-warden`): packaging, environment wiring, and test-tier conventions should be cloned rather than redesigned. The genuinely open technical decisions are narrower than they first appear — confirming Warden's CLI framework choice, and picking one of two well-trodden paths for the Pages-deploy mechanism.

### Strategic Impact Assessment

This grounds the architecture skill in concrete, verifiable file paths rather than abstract patterns, and narrows the PRD's open technical questions to two decisions (CLI framework confirmation, deploy mechanism) instead of the much larger design space a from-scratch technical research would have left open.

### Next Steps Recommendations

Feed this alongside the domain-research report into `bmad-product-brief`, then `bmad-prd` → `bmad-architecture` (which should directly read `pyforge-warden`'s `cli.py` and `interfaces.py` contents to close this report's one open framework question) → `bmad-create-epics-and-stories`.

---

**Research Completion Date:** 2026-07-25
**Confidence Level:** High for packaging/testing/integration-reuse findings (direct file verification); medium for the two flagged open items (CLI framework choice, deploy mechanism).

## assumptions[]

- **A1**: Warden's `interfaces.py` and `cli.py` contents were confirmed present by file listing but not deep-read line-by-line in this pass (time-boxed headless research); the architecture step should read them directly before finalizing Steward's engine-interface shape and CLI framework choice.
- **A2**: Ran headless/express, matching the sibling domain-research report's mode.

## open_questions[]

- **OQ1** (carried forward, now technically scoped): should `steward deploy dashboard` push directly and rely on GitHub's native branch-based Pages workflow (matches today's manual process, zero new Actions workflow), or introduce a formal `upload-pages-artifact`/`deploy-pages` (or `peaceiris/actions-gh-pages`) Actions workflow for scheduled/push-button reconciliation? Both are valid 2026 patterns; PRD/architecture should decide based on how much automation v1 actually wants.
- **OQ2**: Does Steward vendor its own `age`/SOPS invocation, or does it require `age`/`sops` as external pixi run-deps (mirroring how Warden treats `deptry`/`osv-scanner` as conda run-deps rather than reimplementing them)? Recommend the latter for consistency with Warden's own dependency posture (§ 2) — architecture should confirm.

---

# Addendum — 2026-08-08 post-ship technical refresh

**Refresh date:** 2026-08-08. **Basis:** direct read of the shipped modules
(`src/shared/packages/pyforge-steward/src/pyforge/steward/{cli,interfaces,keys,deploy,provision,budget}.py`),
`../retros/retro-steward-2026-08-08.md` (written today), `epics.md`, and the steward-owned
Dreams `docs/dreams/unified-container.md` (read in full), `bmad-module-provisioning.md`,
and `enterprise-airgap.md`.

## A1. How the shipped code resolved this report's open items

- **CLI framework** (§ 2's flagged assumption) → **`argparse`**, matching Warden, codified
  as NFR-5/AD-8: one dispatcher (`cli.py::main`) owns every process exit code; no duty
  module ever calls `sys.exit`. Duty-specific exit codes flow through
  `DutyResult.details["exit_code"]` (established for `budget check`'s
  `EXIT_BUDGET_NOT_CONFIGURED`). Not Typer, not Click — this report's "read Warden's cli.py
  before defaulting to Typer" caution was vindicated.
- **OQ1 (deploy mechanism)** → resolved as **(a)-shaped**: `steward deploy dashboard` is a
  CLI-invoked build → diff → commit+push-only-on-real-difference loop on the current branch
  (FR-9), no new Actions workflow, no `deploy-pages` artifact path. NFR-2 pins the
  no-standing-controller property.
- **OQ2 (vendor vs external `age`)** → external run-deps, as recommended: `age`/`age-keygen`
  are subprocess-wrapped with real hardening (rejected `-` stdin sentinel, closed stdin,
  lenient stderr decode) and zero vendored crypto (AD-3).
- **The engine model** shipped leaner than § 4 sketched: a 5-line `Duty` protocol +
  `DutyResult` dataclass in `interfaces.py` (51 lines), one module per duty, lazily resolved
  by `cli.py::resolve_duty` — not a null-engine registry. Right-sized; nothing to fix.

## A2. Real technical debt (mined from the 2026-08-08 retro — every item is a shipped, fixed defect or a live deferral)

The close-out adversarial review found **a real, distinct bug in every one of the four
epics** (retro: "zero 'nothing found' passes"). The debt-relevant residue:

1. **The `--json` error-path bug is a systemic *class*, patched twice, prevented never.**
   Epic 3's close-out found every error inside `ProvisionDuty.run` rendered plain text
   regardless of `--json` (a `json.loads()`-ing caller crashes on any error path); Story
   4.2's self-review found the identical shape in `BudgetDuty` pre-ship, explicitly
   crediting Epic 3's finding. The fix exists per-module
   (`ProvisionDuty._render_error`, `provision.py:397-408`) but the shared primitive does
   not. **Live deferral, by design**: the retro flags "introduce a shared
   `render_error(ns, message)` helper in `interfaces.py` *if a fifth duty module is ever
   added*." Note for planning: **the unified-container and `--module` work are both
   plausible fifth-duty triggers** — whichever lands first inherits this action item.
2. **`_canonical_host` took three review passes to converge** (empty/garbage hosts pass 1;
   IPv6 corrupted by naive `rsplit(":", 1)` — two *different* IPv6 addresses canonicalizing
   to the same wrong string — pass 2; any single-colon suffix treated as a port, so
   `"https:artifactory.example.com"` silently became `"https"` — pass 3). It is now correct
   with regression tests at each step (`keys.py:179-204` documents all three), but the
   retro's lesson stands as a standing constraint: **security-critical string
   normalization gets its own story-sized surface next time**, never one AC inside a larger
   story. This is the highest-stakes code in the package (it implements FR-7).
3. **git-sequencing logic is a distinct risk class**: Epic 2's single review pass found four
   related defects (unscoped commit sweeping pre-staged files; branch resolution after
   commit → detached-HEAD orphan; failed push permanently invisible; `status` reporting an
   unpushed commit as deployed) — all under-specified ordering/partial-failure, not
   isolated bugs. Any future multi-step git reconcile (container-image publish would be
   one) needs an explicit ordering/partial-failure review pass.
4. **Race protection was decided three different ways, each justified** (Epic 1: real
   `fcntl.flock` + atomic replace for the bespoke YAML inventory; Epic 2: deliberate no-lock
   because `.git/index.lock` already serializes; Epic 4: never arose). A future duty adding
   shared state should be pointed at Story 1.4's and 2.2's Design Notes rather than
   re-deriving the tradeoff — and the flock choice has a documented boundary directly
   relevant below: **POSIX `flock` is not effective over NFS** (`keys.py:707-709`), fine for
   a local-only store, a real constraint the moment the inventory lands on a shared volume.

## A3. Feasibility: the `unified-container.md` Dream against the real shipped code

The Dream (dreamt 2026-08-02, steward-owned): one Docker/Podman image containing all eight
stations' installed packages, one entrypoint (likely `marshal`), the whole Guild bootable
from one `podman run`. This section evaluates what that actually takes, given Steward's real
`provision`/`deploy`/`keys` implementations — the provisioning/credential/environment half
(Marshal's parallel research covers the orchestration half).

### A3.1 The controlling constraint: Steward (and the factory) is checkout-anchored, so the image must ship the repo, not just wheels

This is the single most important shipped-code fact for the Dream. Every duty module locates
the repo root by walking up from its own installed location to a marker file:
`scripts/bmad-loop-worktree` (provision.py:62-78, budget.py:68-83),
`docs/dashboard/generate.py` (deploy.py:47-62), and
`.claude/skills/conda-forge-expert/scripts/_http.py` (keys.py:81-97). `keys.py` goes
further: **at import time** it inserts the CFE scripts dir onto `sys.path` and does
`from _http import auth_headers_for` (keys.py:100-104), raising if no checkout encloses it —
`cli.py`'s lazy `resolve_duty` exists partly for this reason. Consequences:

- A "pip-install eight wheels into a distroless image" build **does not boot**. The image
  is *checkout + materialized environments + packages installed editable/path-wise*, i.e.
  exactly "wired the way `marshal init`/genesis already wire a bare-metal install" — the
  Dream's own "What it looks like when real" bullet, confirmed from the code side.
- The upside: the walk-up design is **mount-point agnostic**. Nothing hardcodes
  `/home/...`; the checkout can live at `/pyforge` inside the image and every marker search
  works unchanged. And a short fixed root is not just tolerable but *actively beneficial*:
  the known worktree path-length limit (repo root >~173 bytes panics pixi-build-python —
  auto-memory `project_bmad_loop_worktree_path_length_limit`) is trivially satisfied at
  `/pyforge` where host checkouts routinely flirt with it.

### A3.2 "Distroless" is off the table; "minimal + pinned pixi env" is the real target

Steward's architecture is AD-1 subprocess-wrapping all the way down: `age`, `age-keygen`,
`pixi`, `git`, plus the `gh` convention and Python itself — and the other stations add their
own tool surfaces. A strict distroless image (no shell, no external binaries) contradicts
the factory's load-bearing wrap-never-reimplement doctrine. The realistic shape is a
minimal base + a **lean composed pixi environment** baked via multi-stage build. The repo
already has the exact precedent: the `pyforge-ci` environment
(`no-default-feature = true`, repo `pixi.toml` — created because `local-recipes` at
**1102 packages / ~9.8 GB** was untenable per Pages deploy against a 10 GB cache ceiling).
The same math rules the image: **do not bake `local-recipes`**; compose a
`pyforge-container` env from the lean `pyforge-*` family the same way, and let heavyweight
capabilities (full recipe-build) be an explicit named exception per the Dream's "or an
explicit, named reason it doesn't need one" clause.

### A3.3 Two modes, as the operator framed it

**Mode L — local, no server infrastructure (the v1 target).** Rootless Podman, single
image, entrypoint `marshal` (per [[one-front-door]]). Composition:
- *Baked*: checkout at `/pyforge`, pre-materialized lean env(s) (`pixi install` in a build
  stage — this IS `steward provision --env` run at image-build time; FR-12's code path is
  reusable as the build step's implementation), the eight station packages.
- *Mounted*: the operator's work — either bind-mount a live checkout over `/pyforge`
  (dev mode) or mount only state dirs (`.steward/`, loop homes) over the baked tree.
- *Rootless specifics*: `fcntl.flock` works fine in a single rootless container (local fs);
  git needs `safe.directory` for UID-mapped bind mounts; no daemon, no compose file —
  matching NFR-1/NFR-2's no-standing-service posture at the container layer too.

**Mode I — with infrastructure.** The same image pushed to a registry (JFrog-mirrored per
the air-gap doctrine) and used ARC-style: each bmad-loop runner is a container from the
image + a worktree volume, quotas applied at the container boundary. This is where two
currently-honest stubs get their first real enforcement points: the container boundary is
the first admission point `budget check` has ever had (see the market report § 3), and
per-container CPU/memory/pids limits are the LimitRange analogue. Mode I is explicitly not
v1 — it needs nothing designed now beyond not foreclosing it (the image must not assume it
is the only instance: the flock-over-NFS boundary in A2.4 is the one shipped assumption
that breaks on a shared volume, so Mode I requires either one-writer-per-inventory or a
lock upgrade).

### A3.4 How Steward's credential machinery maps onto container isolation

The mapping is unusually clean because Epic 1 chose files + env vars over a service:

- **`age` identity files → Podman secrets** (`podman secret create` / `--secret`,
  tmpfs-mounted at runtime). The hard rule: **identities are never baked into image
  layers** — a layer-committed identity is exactly the committed-plaintext shape
  `scan_file_for_secrets` exists to catch. Cheap, high-value extension: run `steward keys
  audit --secrets <unpacked-image-rootfs>` as an image-build gate — the shipped scanner
  needs zero changes to scan an unpacked layer tree, giving the container pipeline the same
  fail-loud secret gate the repo has.
- **`_http.py` routing is already 12-factor**: env-var-only (`*_BASE_URL`, truststore,
  `.netrc` chain), nothing committed — it passes through `podman run -e`/`--env-file`
  unchanged. This is `enterprise-airgap.md`'s realized machinery paying off directly: the
  air-gapped container is the *same* container with different env vars, and the image
  itself is the "offline bundle format" that Dream's frontier asks for.
- **Host-scoped resolution is runtime-evaluated**, so an in-container JFrog mirror hostname
  is just another `hosts` entry — no rebuild. (And `_canonical_host` now handles the
  bracketed-IPv6/port forms container networking actually produces — the three-pass
  hardening in A2.2 was accidentally also container-readiness work.)
- **`.steward/` state (`keys-inventory.yaml`, `budget.yaml`)** mounts as a volume so
  rotation/ceiling history survives container replacement; single-writer per A2.4.

### A3.5 What each shipped verb needs for the Dream, concretely

| Verb | Works in-container today? | Delta needed |
|---|---|---|
| `keys` (all 6 verbs) | Yes, given checkout + `age`/`age-keygen` in the env and identity/inventory mounts | None to function; `audit --secrets` as an image gate is pure upside |
| `provision --env/--list/--verify` | Yes — pixi + checkout present | `--env` doubles as the image build step; `--verify` becomes an image smoke gate |
| `provision --runner bmad-loop` | Mechanically yes (script + git present) | Semantics decision: worktree inside container fs (ephemeral) vs on a volume (durable) — this is Mode I's core design question, shared with Marshal's half |
| `deploy dashboard` | Build+diff yes; **push needs write credentials in-container** | Likely stays host-side in Mode L v1, or takes a mounted token — a named exception, not a blocker |
| `budget` | Yes (pure file ops) | Container boundary later becomes its first enforcement point (Mode I) |

### A3.6 Verdict and sizing

**Feasible, and cheaper than the Dream's "nothing built yet" status suggests — because the
expensive prerequisites already happened.** The 2026-08-02 station consolidation (the
Dream's own stated precursor), the lean-env precedent (`pyforge-ci`), the realized air-gap
env-var doctrine, and Steward's mount-point-agnostic checkout anchoring mean Mode L is
approximately: one `Containerfile` (multi-stage: pixi-install a lean composed env → copy
checkout to `/pyforge` → entrypoint `marshal`), one composed `pyforge-container` pixi env,
a secret-hygiene image gate (`keys audit --secrets` over the rootfs), and smoke gates
(`steward provision --verify`, each station's CLI `--help`) — **an epic-sized effort
(roughly 4-6 stories), not a rearchitecture**, with `bmad-spec` on the Dream as the correct
next step. The two genuine design decisions to resolve at Spec time: (1) baked-checkout vs
bind-mount as the primary mode (recommend: baked, bind-mount as dev override), (2) worktree
placement for in-container runners (defer to Mode I; Mode L can run loops against a mounted
host checkout exactly as today). One dependency to sequence: the `bmad-module-provisioning`
Dream's headless-installer constraint ("non-interactive by construction") is *also* an
image-build-time constraint — TTY-only npm installers cannot run in a `RUN` layer either —
so shipping `provision --module` first makes the container build strictly simpler, and both
are steward-owned.

## A4. Refreshed recommendations

1. Treat A3 as the pre-read for running `bmad-spec` on `unified-container.md`; the Spec
   should bind to the checkout-anchoring constraint (A3.1) and the no-baked-secrets rule
   (A3.4) as invariants, and to `pyforge-ci` as the env-composition precedent (A3.2).
2. Sequence `provision --module` (bmad-module-provisioning) ahead of or alongside the
   container Spec — it removes the one hand-driven install step a reproducible image build
   cannot tolerate.
3. Whichever effort adds Steward's fifth duty module first must execute the retro's
   deferred action item: shared `render_error(ns, message)` in `interfaces.py` (A2.1), so
   the `--json`-error-path class cannot recur a third time.
4. Keep the A2 lessons as review-pass checklists for the container work specifically:
   image-publish is git/registry sequencing (A2.3's risk class), and any shared-volume
   deployment must re-decide the locking question with A2.4's flock/NFS boundary on the
   table.
