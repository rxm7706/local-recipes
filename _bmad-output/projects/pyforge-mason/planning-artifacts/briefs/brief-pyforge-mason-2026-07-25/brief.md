---
title: "Product Brief: Mason (pyforge-mason)"
status: draft
created: 2026-07-25
updated: 2026-07-25
project: pyforge-mason
dream: docs/dreams/packaging-factory.md
adopted_kernel: _bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory/SPEC.md
inputs:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/domain-packaging-automation-tooling-research-2026-07-25.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/technical-mason-cli-seam-research-2026-07-25.md
  - docs/dreams/ecosystem-crew.md (§ 5 Mason)
---

# Product Brief: Mason

**dist** `pyforge-mason` · **module** `pyforge.mason` · **CLI** `mason`

## Executive Summary

Mason turns this repository's packaging capability into a product. Today that capability is real,
proven, and trapped: the `conda-forge-expert` skill runs a 9-step recipe lifecycle across
769 maintained feedstocks, carries 106 accumulated gotchas and 10 hard constraints, exposes
46 MCP tools, and is backed by 1,186 tests — but it only exists inside a Claude Code session in
one repository. You cannot `pip install` it. You cannot run it in CI. A colleague cannot use it.

Mason is the installable face of that capability plus the half it never had. Three verb families:
`mason recipe` (the full generate → validate → build → diagnose → submit loop), `mason package`
(build and ship a library to PyPI **and** conda-forge in one motion), `mason environment` (resolve
mixed conda+pip dependency sets into one lockfile).

The middle verb is the one nobody else offers. The domain research is unambiguous: Hatch and
maturin are structurally conda-unaware; `pixi publish` targets conda channels and its documentation
is silent on PyPI; conda-smithy and the conda-forge autotick-bot are, by their own documentation,
non-redeployable outside conda-forge's infrastructure. Every serious Python library needs both
ecosystems, and **no single tool spans them**. That gap is not a missing feature in one product —
it is an unowned seam between two toolchains with different governance, and no incumbent's roadmap
claims it.

## The Problem

**For the maintainer shipping a library.** You finish a release. Now you do it twice. You build a
wheel, upload it, and you are done in 90 seconds — that half is solved. Then you switch toolchains
entirely: a different metadata format, a different dependency namespace (`ruamel.yaml` on PyPI is
`ruamel.yaml` on conda but `tree_sitter` is `tree-sitter`), a different build system, a platform
matrix, and a review queue staffed by volunteers. The knowledge that makes the second half fast is
tribal, and the tools that encode it do not talk to the tools that did the first half.

**For the maintainer at scale.** conda-forge's autotick-bot does version bumps and migrations
beautifully — for conda-forge. Its own documentation states it "cannot be deployed elsewhere." If
you run a private channel, an air-gapped mirror, a JFrog Artifactory proxy, or a fork, that entire
class of automation is unavailable to you. There is no maintainer-operable equivalent.

**For this repository specifically.** The packaging capability that solves both problems already
exists here and cannot leave. It is a Claude-Code-resident skill: 41,410 lines of canonical Python
reachable only through pixi tasks defined in one `pixi.toml`, with `recipes/` hardcoded in
17 scripts. The asset is real; the distribution is zero.

**How people cope today.** They hand-write recipes and wait through review cycles; they use
grayskull for a first draft and manual labor for everything after; or they simply do not ship to
conda at all, and their users go without.

## The Solution

A single installable CLI, distributed the same way as its siblings — as both a conda package and a
wheel, from one `pyproject.toml`.

```bash
mason recipe build ./recipes/recipe.yaml       # the lifecycle loop, as a command
mason package --target library --ship pypi,conda-forge   # the dual-ship motion
mason environment lock --output conda-lock.txt           # one lockfile across both
```

The architectural core is a decision, not a feature: **Mason holds no recipe knowledge of its
own.** Every recipe operation delegates to the existing `conda-forge-expert` machinery through one
adapter module. Mason owns the product surface — verbs, ergonomics, packaging, error messages,
orchestration. The skill owns recipe semantics, and continues to, because a mandatory retro loop
(CLAUDE.md Rule 2) updates it after every packaging effort. Wrapping means Mason gets those
updates for free. Forking would mean re-earning 106 gotchas and then drifting behind them forever.

Where nothing exists to wrap — PyPI publishing, lock orchestration — Mason builds natively,
orchestrating established engines (`build`, `twine`/`uv`, `pixi build`, conda-lock) rather than
re-solving or re-building anything.

## What Makes This Different

**One command, both ecosystems.** The only genuinely unowned capability in the survey. Structural,
not incremental — the incumbents are not converging on it.

**Automation the maintainer operates.** Autotick-class behaviour as an artifact you run, against
your channel, behind your proxy, in your CI. The enterprise-routing groundwork already exists
(truststore + JFrog/GitHub/.netrc auth chain, used by 27 of the 66 canonical scripts).

**Accumulated packaging judgement.** 106 numbered gotchas and 10 constraints — that a PyPI
`source.url` must use the `pypi.org/packages/...` pattern to survive an air-gapped proxy; that a
`build.bat` must `call` every `.cmd` shim or silently terminate. No incumbent knows any of this.
It is the real moat, and Mason's design exists to keep it in one place rather than copy it.

**Agent-native.** Every incumbent is a human CLI. This capability is already reachable by agents
through 46 MCP tools. Mason keeps a machine-callable surface first-class, which is what makes
"steering intent, not syntax" reachable.

**Where we are honest about not differentiating:** `mason environment lock` competes with
conda-lock, which already spans conda and pip via a vendored Poetry solver and is actively
maintained. Mason wraps it. The value there is policy and orchestration, and the scope is small.

## Who This Serves

**Primary — the dual-ecosystem library maintainer.** Ships Python libraries that need both a wheel
and a conda package. Competent with packaging, tired of doing it twice, currently losing hours per
release to the conda half. Success: one command, both ecosystems, no format archaeology.

**Primary — the fleet maintainer.** Maintains many feedstocks (here: 769) and wants autotick-class
automation they control. Success: the maintenance loop runs against their targets, not only
conda-forge's.

**Secondary — the enterprise/air-gapped operator.** Cannot reach public infrastructure; needs the
same lifecycle against internal mirrors. Success: it works behind the proxy without a fork.

**Secondary — the agent.** Calls Mason to package something on a human's behalf. Success: verbs
that are legible to a model, errors that are actionable without a human reading a traceback.

## Success Criteria

**Primary (the master switch).** Mason ships its own release — wheel to PyPI, conda package to a
channel — using `mason package --ship`. Until Mason can ship Mason, the dual-ship claim is
unproven. The repository already dogfoods the exact dual-artifact motion by hand for two sibling
packages, so this is a real and near test, not an aspiration.

**Supporting.**
- Every `mason recipe` operation routes through the CFE adapter — **enforced by a test**, not by
  intent. Zero recipe-domain constants in `pyforge.mason`.
- `mason package` and `mason environment` run with the CFE machinery entirely absent.
- Distribution parity with the sibling packages: `.conda` + wheel + sdist from one `pyproject.toml`.
- A CFE skill update (new gotcha) reaches Mason's behaviour with **no change to Mason**.
- Zero recipe knowledge duplicated. The counter-example is in this repo: `pyforge-atlas` rebuilt its
  capability as ~29,000 lines and the 8,902-line original is still what runs in production. Mason
  must not produce a second implementation of anything.

## Scope

**In (v1).**
- `mason recipe` — the lifecycle loop, delegated to CFE via one adapter module
- `mason package` — build wheel + conda artifact; ship to PyPI; initiate the conda-forge path
- `mason environment lock` — wrap conda-lock / `pixi.lock`, thin
- Packaging as a pixi workspace member, mirroring `pyforge-warden` / `pyforge-atlas` exactly:
  hatchling + `pixi-build-python`, PEP-420 `src/pyforge/mason/`, argparse CLI, lean dependencies,
  engines as conda run-dependencies, the three-task build triad
- A CFE-discovery resolution chain (`--cfe-root` → `MASON_CFE_ROOT` → walk up for `.claude/` →
  structured degradation)

**Out (v1).**
- Any reimplementation of recipe semantics, gotchas, pins, or conda-forge policy — permanently out
- A second MCP server duplicating the existing 46 tools (deferred; Mason-only verbs later)
- Re-solving dependencies; Mason orchestrates solvers, never replaces them
- Multi-ecosystem autotick (CRAN/npm/cargo) — the dream's frontier, not v1
- Replacing the existing pixi task surface (coexistence in v1; see open questions)
- Running with no `.claude/` present at all — undecided and scope-critical

**The known asymmetry, stated up front:** shipping to PyPI is a synchronous upload measured in
seconds. Shipping to conda-forge is a pull request into `staged-recipes` with a human review queue
measured in days. `--ship pypi,conda-forge` cannot be one transaction, and a verb that reports
success when half the work is merely queued would be a correctness bug. The PRD must specify the
reporting contract.

## Vision

Mason is one member of the Ecosystem Crew — the station that binds ingredients into shipped
structures, beside Atlas (mapping), Warden (clearing), Doctor (health). If it succeeds, the
packaging factory stops being a place and becomes a tool: the lifecycle that runs here runs
anywhere, for anyone, against any channel.

The frontier the origin dream already names: multi-ecosystem autotick so the factory is no longer
Python-first; a smart test extractor that re-runs recipe tests against an existing artifact without
rebuilding; a static dependency-version checker that validates ranges rather than existence. Each is
a Mason verb once the station is a product.

The deeper aim is smaller and more stubborn: packaging a library should be a sentence, not an
afternoon of YAML archaeology. Mason is what makes that sentence executable outside the room it was
invented in.

---

## assumptions[]

1. **A-1** — The crew-charter verbs (`recipe build`, `package --ship`, `environment lock`) are
   binding product scope, taken verbatim from `docs/dreams/ecosystem-crew.md` § 5.
2. **A-2** — "Dual-ecosystem" means conda-forge + PyPI. npm/CRAN/CPAN/LuaRocks are *source*
   ecosystems for recipe generation, not `--ship` targets.
3. **A-3** — The target operator is the individual maintainer or small team already using pixi, not
   conda-forge core infrastructure. If it were the latter, the autotick-bot is the incumbent and
   Mason is redundant.
4. **A-4** — Mason may not modify the CFE surface (governed by `spec-packaging-factory` +
   CLAUDE.md Rule 1). This is the constraint that makes the wrap decision structural.
5. **A-5** — The workspace conventions demonstrated by `pyforge-warden` and `pyforge-atlas`
   (argparse, hatchling + `pixi-build-python`, lean deps, build triad) are normative for new
   members. Inferred from two instances and their comments, not from a written standard.
6. **A-6** — Local measurements (41,410 LOC, 106 gotchas, 46 MCP tools, 1,186 tests) are
   point-in-time at CFE v8.79.1 and will drift. They are used for shape arguments, not commitments.

## open_questions[]

1. **OQ-1** *(scope-critical)* — Must `mason` run in a repository with **no** `.claude/` present
   (arbitrary CI, another org)? If yes, wrapping is materially weakened and vendoring must be
   re-evaluated. This is the highest-leverage unanswered question in the brief.
2. **OQ-2** — Does `--ship conda-forge` mean "open a staged-recipes PR" (asynchronous, human-gated)
   or "upload to a conda channel" (synchronous)? Plausibly both, as distinct targets.
3. **OQ-3** — Does Mason eventually **replace** the ~105 CFE pixi tasks, or coexist indefinitely?
   `pyforge-atlas` never answered this and now runs two implementations.
4. **OQ-4** — Credential model for `--ship pypi`: API token, OIDC trusted publishing, or
   artifact-only (build but do not upload)?
5. **OQ-5** — Python floor: 3.12 (warden) or 3.14 (atlas)?
6. **OQ-6** — Does Mason own multi-ecosystem autotick, or is that Marshal/Steward territory? The
   dream places it in the packaging factory; the crew charter omits it from Mason's cadence.
7. **OQ-7** — Coverage risk: the competitive survey ran without a web-search budget and was built
   from known primary sources. A discovery sweep for unknown entrants has **not** been run.
