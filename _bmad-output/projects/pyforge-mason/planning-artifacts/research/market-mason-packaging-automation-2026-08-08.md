---
stepsCompleted:
  - step-01-init
  - step-02-scope
  - step-03-competitive-landscape
  - step-04-gap-revalidation
  - step-05-unified-packaging-vision
  - step-06-cross-station
  - step-07-synthesis
inputDocuments:
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/research/domain-packaging-automation-tooling-research-2026-07-25.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/research/technical-mason-cli-seam-research-2026-07-25.md"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md (38 stories, revision 2)"
  - "docs/dreams/pyforge-mason.md (status: specified)"
  - "src/shared/packages/pyforge-mason/ (shipped Epic 1 slice, 495 LOC)"
  - ".claude/skills/conda-forge-expert/SKILL.md (v8.81.0)"
workflowType: 'research'
lastStep: 7
research_type: 'market'
research_topic: 'Competitive/analogue landscape for Mason — the one-CLI pip+conda+ship packaging surface — refreshed against live 2026 web evidence'
research_goals: 'Fill the missing market-research tier for pyforge-mason; re-validate the D1 dual-ship gap with fresh sources; ground the unified pip/conda packaging + container vision; inform Epics 2-5 (34 remaining stories)'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: true
source_verification: true
project: pyforge-mason
---

# Market Research: Mason Packaging-Automation Landscape (2026-08-08)

**Date:** 2026-08-08
**Research Type:** Market / competitive landscape
**Consumer:** Epics 2–5 of `pyforge-mason` (34 backlog stories); the domain report of 2026-07-25
had `research_type: domain` and explicitly deferred an open discovery sweep (its OQ-1). This
report is that sweep, plus a re-validation of every market-shaped open question the planning
chain left dangling — with **live 2026 web evidence** this time (the 2026-07-25 pass ran with an
exhausted search budget and known primary URLs only).

**Timing note.** Only 4/38 stories are shipped (Epic 1 S-1.1–S-1.4: scaffold, CLI shell, error
taxonomy, output contract — 495 LOC in `src/shared/packages/pyforge-mason/src/pyforge/mason/`).
Every competitive finding below therefore still has room to shape implementation, not just
describe it. Findings are keyed to the story IDs in
`_bmad-output/projects/pyforge-mason/planning-artifacts/epics.md` they should inform.

---

## 1. Executive summary — what changed since 2026-07-25

Five market facts moved, three of them directly answering the July report's open questions:

1. **Grayskull now emits v1 `recipe.yaml`** (`grayskull pypi --use-v1-format
   --strict-conda-forge`), and it is the conda-forge docs' recommended path for new PyPI
   recipes. The July domain report's assumption A-7 ("grayskull is v0-only") is **triggered** —
   its component-level argument weakens exactly as that assumption predicted, and none of
   D1–D4 fall. rattler-build has also grown its own `generate-recipe` subcommand. Recipe
   *generation* is now commoditized at the v1 format level; Mason's `recipe new` (S-2.4)
   remains a thin delegation and gains nothing by knowing this — but CFE's generator is now
   one of three generators in the market, and delegation-fidelity (S-5.3) is what keeps Mason
   indifferent to which one CFE uses internally.
2. **`pixi publish` shipped as a real command — and it is still conda-only.** Targets:
   channel URLs, `cloudsmith://`, S3 (with automatic channel init + reindex), local dirs. No
   PyPI target exists in the CLI reference. The July report's OQ-2 ("does pixi publish
   secretly do PyPI?") is **answered: no**. **D1 — the dual-ship gap — holds** and now has a
   dated second confirmation.
3. **The lockfile war ended by absorption, mostly in pixi's favor.** conda-lock is still
   maintained (PyPI release 2026-07-01) but its lead maintainer publicly calls pixi "the
   future of lockfiles in the Conda ecosystem" (conda-lock issue #615), ships a
   `render-lock-spec` pixi-migration subcommand, and — bigger — the **May 2026 conda releases
   made `conda create/install/export` natively understand both `conda-lock.yml` and
   `pixi.lock`**, multi-platform, solver-skipping. The July report's OQ-3 is **answered**:
   Mason's Epic 4 engine question (OQ-E3) should now default to **pixi-first with a conda-lock
   adapter as the compatibility path**, not the other way around. See § 4.
4. **Publishing grew a security dimension the PRD barely prices in.** PyPI trusted publishing
   (OIDC, short-lived tokens, no stored secrets) is now the documented golden path for
   `uv publish` and CI generally; prefix.dev supports OIDC trusted publishing for conda
   channels; rattler-build can attach **Sigstore attestations** (`--generate-attestation`) on
   upload to prefix.dev. Mason's credential stories (S-3.4 "read at point of use, never
   logged") are necessary but no longer sufficient market posture — see § 5.
5. **pixi-build is *still* preview** (opt-in `workspace.preview = ["pixi-build"]`,
   documented limitations, backends now released stable on conda-forge, `pixi-build-python`
   pinned `0.*` exactly as Mason's S-1.1 AC already requires) — but adoption crossed a
   threshold: **CPython itself, SciPy, Xarray, and Dask now build with it**. The
   preview-software risk the July technical report flagged (A-T4) is smaller than it was, and
   the repo's bet on it looks market-aligned rather than eccentric.

**Bottom line for the 34 remaining stories:** the differentiator survived a full year of the
fastest-moving corner of the ecosystem (prefix.dev shipped publish, attestations, OIDC,
generate-recipe — and still no PyPI path). Nobody has built "one CLI, both ecosystems, one
receipt." The two nearest analogues (whl2conda, hatch-conda-build) are dual-*build*, not
dual-*ship*, and neither touches conda-forge submission. Mason's moat is unchanged; what moved
is the *engine choices underneath it* — and three of the five epic-level open questions
(OQ-E2, OQ-E3, and the S-3.4 uploader choice) now have market-informed answers.

---

## 2. Competitive / analogue landscape (refreshed)

### 2a. PyPI-side incumbents: `build` + hatchling + twine/uv

- **`python -m build` + hatchling** remains the boring, correct PEP-517 substrate. Mason's
  S-3.2 already specifies it. No change; no competitor claim — these are engines, and every
  competitor in this table uses them too.
- **`uv publish`** is the material mover: it is now the community-documented golden path for
  PyPI publishing, with native OIDC trusted-publishing exchange (auto-detects GitHub Actions,
  `--trusted-publishing always`), retries, and multi-index awareness. **Implication for
  S-3.4:** the AC says "via the `twine` engine adapter." Behind the S-3.1 engine protocol
  that's swappable, but the *decision* deserves revisiting before S-3.4 is built: `uv` is a
  single static binary already adjacent to the pixi ecosystem, handles TestPyPI (S-3.9's
  `pypi-test` target) via index configuration, and does OIDC natively — twine does trusted
  publishing too, but uv is where the market's attention and fixes are going. Recommendation:
  keep the engine protocol, implement the **uploader adapter behind a name that is not
  `twine`** (e.g. `engines/pypi_upload.py`) so the engine can be twine or uv without renaming
  the seam. Low cost now; annoying rename later.
- **Hatch (the project manager)** is still structurally conda-unaware. Unchanged from July.

### 2b. PyPI→conda bridging: grayskull, whl2conda, hatch-conda-build, CFE itself

| Tool | What it does | Ship to PyPI? | Ship to conda-forge? | Read for Mason |
|---|---|---|---|---|
| **grayskull** | PyPI/CRAN/GitHub metadata → recipe; **now v1-capable** (`--use-v1-format`) | ❌ | ❌ (draft only) | Component. CFE already shells to it. Its v1 support removes a format-translation excuse for anyone forking recipe knowledge — good for the D-1 seam. |
| **whl2conda** | Pure-python wheel → `.conda` directly, no conda-build, PyPI→conda dependency renaming, `[tool.whl2conda]` in pyproject, `whl2conda build --build-wheel` does a one-command dual **build** | ❌ | ❌ | **The closest living analogue to `mason package build`.** Validates the demand for one-command dual-artifact production. Stops at build: no upload, no submission, no receipt. Also only pure-python wheels. |
| **hatch-conda-build** | Hatch plugin: conda target from pyproject.toml, grayskull-translated deps, output is a local indexed channel | ❌ | ❌ | Analogue at the build-backend layer; requires conda-build on PATH (the slow engine). Confirms the "one manifest, two artifacts" instinct — this repo's pixi-build-python triad is the same idea with a better engine. |
| **conda-forge-expert (this repo)** | Full lifecycle: generate → validate → build → diagnose → submit → maintain; v8.81.0, 67 canonical scripts, 46 MCP tools | ❌ (no wheel path — verified in July, still true) | ✅ | Mason's wrapped engine, not a competitor. Nothing else in this table submits to conda-forge at all. |

**The competitive read:** dual-*build* has three independent implementations in the market
(whl2conda, hatch-conda-build, this repo's pixi triad). Dual-*ship* — build **and** upload
**and** open the staged-recipes PR **and** report the asymmetric truth of it — has **zero**.
Epic 3's differentiator claim survives; S-3.7's asymmetric receipt is precisely the part no
analogue has even attempted.

### 2c. Conda-side engines: rattler-build, pixi build/publish, conda-build

- **rattler-build** is now conda-forge's default builder for v1 recipes, and since the May 2026
  conda releases, v1 builds route through the **py-rattler-build Python API** rather than
  shelling the CLI. Mason never calls rattler-build directly (CFE does, behind the seam), so
  this is free inheritance — but it is a **watch item for S-2.6**: if CFE's local builder
  migrates from CLI shelling to py-rattler-build, stdout shapes may change under Mason's
  tolerant parser (S-2.1's leading-progress-line handling). The fake-CFE fixture (S-1.9)
  should include a stub whose output mimics both shapes.
- **`rattler-build publish` / `upload`** now covers prefix.dev, anaconda.org, Quetz, JFrog
  Artifactory, and S3 — with channel auto-init + reindex for filesystem/S3 targets, shared
  credential store with pixi, prefix.dev OIDC trusted publishing, and Sigstore attestations.
  **This answers OQ-E2 (S-3.5's engine choice)**: the July question was "`pixi publish` or
  `anaconda upload`"; the 2026 answer is that the pixi/rattler credential-sharing family
  covers every channel target an enterprise user plausibly names, including the JFrog case
  this repo's own enterprise posture cares about. Recommendation: S-3.5's engine adapter
  wraps `pixi publish` (or `rattler-build upload` — same auth store), and `anaconda upload`
  is not needed in v1.
- **conda-build** persists for v0 recipes; irrelevant to Mason (CFE owns the choice).

### 2d. Hermetic multi-ecosystem builders: Nix, Bazel

Refreshed because "one CLI for pip+conda+ship" invites the question "isn't that Nix?"

- **Nix**: the Python story consolidated on **uv2nix** (uv.lock → Nix derivations, built on
  pyproject.nix); poetry2nix is maintainer-seeking and its own author points users to uv2nix.
  Nix solves *reproducible builds of one closed world*; it does not publish to PyPI or
  conda-forge and treats conda as just another foreign format. Not a competitor for Mason's
  ship motion; a competitor only for the *environment* verb family, and only for users
  already inside Nix.
- **Bazel `rules_python`**: hermetic toolchains via python-build-standalone; monorepo-scale
  build correctness. Same read: no publish path, no conda path, enormous adoption cost.
  A practitioner line from the search is worth keeping: offering Nix to people already
  wrestling with Bazel is "just cruel" — the hermetic tools price themselves out of Mason's
  operator (an individual maintainer with a pixi env).

**Read:** the hermetic systems compete on *reproducibility*, which Mason gets from
pixi.lock/conda-lock via Epic 4 at ~1% of the adoption cost, and they concede *distribution*
entirely. No repositioning needed; keep them named as non-goals if a stakeholder asks.

### 2e. The delivery/deployment adjacency: pixi-pack, containers

- **pixi-pack / pixi-unpack** (Quantco): pack a `pixi.lock`-resolved environment into a single
  self-contained archive, unpack anywhere, cross-platform packing (build a win-64 pack on
  linux-64). The conda-pack successor, air-gap friendly.
- **The pixi container pattern** is now officially documented: multi-stage Docker from
  `ghcr.io/prefix-dev/pixi`, `pixi install --locked -e prod`, `pixi shell-hook -e prod >
  /shell-hook.sh`, copy `/app/.pixi` into a bare `ubuntu:24.04` final stage — no pixi binary
  in production, ~37MB saved, lockfile-exact runtime.

These matter for § 3 (the unified-packaging vision) and for a possible post-v1 verb — they
are the market's answer to "how does a pip+conda environment become a shippable artifact."

---

## 3. The unified pip+conda packaging vision — Mason's half of the container question

The operator asked: what would it take for `mason package build` / `mason ship` to genuinely
unify PyPI wheel/sdist builds AND conda builds under one CLI — and is this repo's own
pixi-build-python pattern the actual target, or does Mason need something else for arbitrary
third-party projects? (Marshal's parallel research owns the fleet-wide single-container
vision; this section is the packaging-specific substrate.)

### 3a. What the repo's own pattern proves — and what it assumes

The `pyforge-mason-build` triad in the root `pixi.toml` (lines ~124–150) is a working
one-manifest dual-build: one `pyproject.toml`, hatchling wheel via `python -m build`,
`.conda` via `pixi build` with `pixi-build-python` wrapping *the same hatchling backend*.
S-3.2's ACs codify exactly this. It is real, dogfooded across three sibling packages
(warden, atlas/doctor, mason), and S-3.8 ("Mason ships Mason") closes the loop.

But the pattern carries **three assumptions that fail on arbitrary third-party projects**:

1. **A `[package]` table in a member `pixi.toml`.** Arbitrary projects have `pyproject.toml`
   only. `pixi build` has nothing to build without the pixi package manifest.
2. **pixi-build preview opt-in** at the workspace root. A third-party repo won't have
   `preview = ["pixi-build"]`.
3. **PyPI→conda dependency-name mapping** done implicitly by pixi-build-python's opt-in
   mapping. For non-trivial dependency sets the mapping is exactly the unreliable four-spelling
   problem this repo's own memory documents (`feedback_pypi_conda_mapping_unreliable.md`).

### 3b. The v1 answer the epics already give — keep it

FR-21/S-3.2 restrict `--target` to `library` and the ACs are written against a project that
looks like this repo's members. **That scoping is correct and should be defended in review**:
v1 Mason unifies pip+conda for *pixi-native projects*, which is the population actually
growing (CPython, SciPy, Xarray, Dask now build with pixi-build). The S-3.2 AC "any other
value is rejected with a message naming `library` as the v1 set" is the right fence.

### 3c. The post-v1 ladder (recommend recording as roadmap, not v1 scope)

For arbitrary third-party projects, the market offers three escalating strategies, each with
a living analogue Mason can wrap rather than invent:

| Rung | Strategy | Engine analogue | Cost |
|---|---|---|---|
| 1 | Wheel → conda conversion for pure-python projects (`--target library` grows a `no-pixi` path) | **whl2conda** (fast, no conda-build, does dependency renaming) | Small — one engine adapter under S-3.1's protocol. Pure-python only. |
| 2 | Generate a scaffold `pixi.toml [package]` for the project, then run the existing pixi path | none (novel, but mechanical) | Medium — and it edges toward recipe knowledge; must stay a mechanical transform or it violates the seam guard's spirit |
| 3 | Full recipe generation + build via CFE (`mason recipe new --from-pypi` → `recipe build`) | already exists — Epic 2 | Zero new code; this IS the path for compiled/complex projects |

Rung 3 is the important observation: **for arbitrary complex projects, Mason's unified answer
is not `package build` growing conda powers — it is the `recipe` and `package` families
composing.** The one-CLI unification is the noun surface, not one mega-verb. A future
`mason package build --via recipe` that chains S-2.4→S-2.6 would give arbitrary-project
coverage with zero new packaging knowledge in Mason. Worth a D-record when Epic 3 starts.

### 3d. The container piece Mason actually owns

The fleet-container Dream (Marshal's research) needs, from Mason's side, exactly two
packaging capabilities — both already in or adjacent to Epic 4:

- **The lock is the container's input contract.** The documented pixi container pattern is
  `pixi install --locked` inside a build stage. `mason environment lock` (S-4.3) +
  `mason environment check` (S-4.4, the CI staleness gate) are the verbs that make a
  PyForge-wide image reproducible. No new scope needed — but S-4.3's output-format choice
  should prefer `pixi.lock`-compatible output *because the container pattern consumes it
  natively* (one more weight on the § 4 engine decision).
- **A pack/export motion** (`pixi-pack`-shaped: lockfile → self-contained archive, air-gap
  friendly, cross-platform packing) is the missing verb if the fleet container must be built
  where the network isn't. This is **not in the 38 stories** and should not be smuggled in;
  recommend recording `mason environment pack` as a named post-v1 candidate (an S-3.1-style
  engine adapter over pixi-pack) in the deferred-work ledger when Epic 4 lands. It is the
  single cheapest bridge between Mason's charter and the one-container vision.

**What Mason should *not* own:** Dockerfile authoring, image builds, registry pushes, OCI
targets for `--ship`. That is Marshal/fleet territory; the S-3.3 target vocabulary
(`pypi`, `conda-forge`, `channel:<name>`) should stay closed in v1 precisely so this
boundary stays legible.

---

## 4. Epic 4's engine question (OQ-E3), answered by the market

July's framing: "conda-lock or pixi? May need both adapters." The 2026 evidence reorders it:

- conda-lock's own maintainer endorses pixi as the future and ships a migration subcommand.
- conda itself now consumes **both** `conda-lock.yml` and `pixi.lock` natively (May 2026),
  so the *consumer-side* lock-in that justified conda-lock's renderers is dissolving.
- The container/deployment patterns (§ 2e, § 3d) consume `pixi.lock`.
- This repo's own tooling is pixi-native end to end.

**Recommendation for S-4.1:** first adapter is **pixi** (`pixi lock` /
`pixi install --locked` for verification in S-4.4); conda-lock becomes the *second* adapter,
justified by exactly one real constraint — projects whose manifests are
`environment.yml`/`requirements.txt` with no pixi.toml (S-4.2 discovers all four manifest
types, and pixi does not solve a bare environment.yml). That maps each engine to a manifest
population instead of "maybe both," and gives S-4.1's provenance reporting (engine name +
version in the lockfile) a concrete two-engine test case. The AD-12 protocol already makes
this cheap.

---

## 5. The security/provenance current the PRD under-prices

Three converging 2026 facts: PyPI trusted publishing as the default posture; prefix.dev OIDC
trusted publishing for conda channels; rattler-build Sigstore attestations on upload. The
market is moving from "keep the token secret" (Mason's S-3.4/AD-14 posture — credential
blindness, read-at-point-of-use) to "**there is no token**" (workload identity) and
"**the artifact proves its origin**" (attestation/provenance).

Mason's v1 stories are not wrong — an interactive CLI on a maintainer's machine legitimately
uses tokens, and AD-14 is the right hygiene. But two cheap alignments are available while
Epic 3 is still unbuilt:

1. **S-3.4 should not architecturally assume a token exists.** If the uploader engine is uv
   (§ 2a), OIDC comes free in CI; the "missing credentials detected before build" AC should
   phrase its check as "no viable auth path" (token OR ambient OIDC) rather than "no token."
   One sentence in the story spec now; a redesign later.
2. **The ShipReceipt (AD-9, S-3.7) is the natural carrier for provenance.** When attestation
   arrives (post-v1), it lands as a field on `ShipTargetResult`, not a new subsystem. Worth a
   one-line note in S-3.7's spec so the model isn't closed against it (`schema_version` in the
   FR-31 envelope already anticipates evolution).

No new stories recommended; both are spec-level nudges.

---

## 6. Cross-station boundaries (Warden, CFE) — is the delegation clean?

- **Mason ↔ CFE:** the boundary is clean *and freshly stress-tested*: the
  `pyforge-mason-recipe-validator` sibling Dream (2026-08-02) proposed a native ~50-rule lint
  engine inside Mason and was retired same-day because D-1 + S-2.5/S-2.8 already cover it.
  That incident is the best available evidence the seam decision holds under real pressure —
  and it is exactly the erosion S-2.2's deny-list exists to catch mechanically. Since S-2.2 is
  unbuilt, the *only* thing currently preventing a repeat is Dream-level governance; **the
  critical-path designation on S-2.2 is validated and it should be the first story of Epic 2**,
  as the epics doc already orders it.
- **Mason ↔ Warden (the operator's duplication question):** no duplication found, by
  construction on both sides. `mason recipe scan` (S-2.8) renders **CFE's scanner findings on
  a recipe artifact, applying "no severity policy, threshold, or filtering of its own"**
  (verbatim AC). Warden's axes (hygiene/security/license/currency) judge a **project's
  dependency manifests** and *own* the policy gates (flag-activated, baselines,
  grandfathering). Mason ships and reports; Warden decides whether shipping was allowed — the
  Dream's own line ("the hand that builds must not be the gate that judges") is implemented
  faithfully in the ACs. One seam to keep an eye on: if a future story ever wants Mason to
  *block* a ship on scan findings, that is Warden's jurisdiction and should arrive as the
  established optional-sibling-dependency pattern (atlas's
  `[project.optional-dependencies] gate = ["pyforge-warden"]`), not as thresholds in
  `package.py`. Recommend one deny-list entry in S-2.2 (or a companion meta-test) for
  severity-threshold constants, which would make this mechanical too.

---

## 7. Recommendations keyed to remaining stories

| Story | Recommendation | Source section |
|---|---|---|
| S-2.1 / S-1.9 | Fixture stubs should mimic both CLI-shelled and py-rattler-build-era output shapes; CFE's builder may migrate under the seam | § 2c |
| S-2.2 | Add a severity/threshold-constant pattern to the deny-list (Warden-jurisdiction guard); build S-2.2 first in Epic 2 — the validator-Dream near-miss proves the erosion pressure is real | § 6 |
| S-3.1 | Name the PyPI uploader adapter neutrally (`pypi_upload`), engine = uv or twine behind it | § 2a |
| S-3.4 | Phrase credential preflight as "no viable auth path" (token or OIDC), not "no token" | § 5 |
| S-3.5 | OQ-E2 answer: pixi/rattler upload family (shared auth, covers prefix.dev/anaconda/Quetz/JFrog/S3); drop `anaconda upload` from consideration | § 2c |
| S-3.7 | Keep `ShipTargetResult` open to a future provenance/attestation field | § 5 |
| S-3.2 | Defend the `library`-only fence in review; record the rung-1/rung-3 arbitrary-project ladder as a D-record or deferred-work entry, not scope | § 3b–3c |
| S-4.1 | OQ-E3 answer: pixi engine first; conda-lock as second adapter mapped to non-pixi manifest populations | § 4 |
| S-4.3 | Prefer pixi.lock-compatible output — it is what the container deployment pattern consumes | § 3d |
| Epic 4 closeout | Record `mason environment pack` (pixi-pack wrap) as the named post-v1 bridge to the fleet-container vision | § 3d |

## assumptions[]

1. **A-M1** — Search-result syntheses (WebSearch, 2026-08-08) are treated as current-state
   evidence; none were independently benchmarked. Specific version numbers (pixi 0.70.x images,
   conda-lock 2026-07-01 release) are directional.
2. **A-M2** — "pixi publish has no PyPI target" is read from the current CLI reference's
   silence plus explicit search confirmation; as in July (A-5), absence-of-docs is treated as
   absence-of-feature. Re-check when Epic 3 starts (see OQ-M1).
3. **A-M3** — Marshal's concurrent research owns the fleet-container conclusions; § 3d
   deliberately stops at the packaging substrate and may need reconciling with Marshal's file
   when both land.

## open_questions[]

1. **OQ-M1** — prefix.dev's velocity is the standing threat to D1: they shipped publish,
   OIDC, attestations, and generate-recipe within ~a year. If pixi ever grows `pixi publish
   --to pypi` (it wraps uv internally for installs already), the dual-ship gap narrows to the
   conda-forge-submission + receipt layer. Re-run this check at Epic 3 kickoff and again at
   S-3.8 (self-ship).
2. **OQ-M2** — whl2conda's dependency-renaming table vs. this repo's four-spelling mapping
   lore: if rung 1 of § 3c is ever built, evaluate whether whl2conda's mapping is good enough
   or whether the mapping question routes through CFE (which would make rung 1
   seam-relevant, not seam-free as assumed).
3. **OQ-M3** — Does `mason environment check` (S-4.4) define "stale" the way `pixi lock
   --check` / conda-lock `--check-input-hash` do (input-hash comparison), or by re-solving?
   The engines disagree subtly; the AC ("names which manifests drifted") implies input-hash.
   Settle in the story spec.

## Sources

Web (2026-08-08 WebSearch passes):
- pixi build preview status + backends: https://pixi.prefix.dev/latest/build/getting_started/ · https://prefix-dev.github.io/pixi-build-backends/backends/pixi-build-python/ · https://github.com/prefix-dev/pixi-build-backends · https://prefix.dev/blog/pixi-build
- uv publish + trusted publishing: https://docs.pypi.org/trusted-publishers/ · https://pydevtools.com/handbook/how-to/how-to-publish-to-pypi-with-trusted-publishing/ · https://pydevtools.com/handbook/how-to/how-to-publish-to-testpypi-with-uv/
- grayskull v1 + conda-forge v1 default: https://conda-forge.org/docs/maintainer/adding_pkgs/ · https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/ · https://conda.org/blog/2026-05-20-may-releases/ · https://conda.org/blog/2026-08-03-july-releases/
- pixi publish / rattler-build upload / attestations: https://pixi.prefix.dev/latest/reference/cli/pixi/publish/ · https://rattler-build.prefix.dev/dev/publish/ · https://rattler-build.prefix.dev/latest/authentication_and_upload/
- conda-lock vs pixi.lock: https://github.com/conda/conda-lock/issues/615 · https://conda.github.io/conda-lock/pixi-migration/ · https://conda.org/blog/conda-roadmap-q1-2026/ · https://github.com/Quantco/pixi-pack
- container pattern: https://pixi.prefix.dev/latest/deployment/container/ · https://github.com/prefix-dev/pixi-docker · https://tech.quantco.com/blog/pixi-production/
- dual-build analogues: https://github.com/zuzukin/whl2conda · https://github.com/conda-incubator/hatch-conda-build
- hermetic builders: https://discourse.nixos.org/t/uv2nix-build-develop-python-projects-using-uv-with-nix/58563 · https://github.com/nix-community/poetry2nix · https://github.com/bazel-contrib/rules_python

Local: `epics.md` (r2), `docs/dreams/pyforge-mason.md`, `src/shared/packages/pyforge-mason/`
(495 LOC shipped), root `pixi.toml` mason wiring, `.claude/skills/conda-forge-expert/SKILL.md`
v8.81.0, ground-truth counts 2026-08-08: 67 canonical scripts / 60 public wrappers / 46 MCP
tools (drifted from the July report's 66/57/46 — see the domain refresh addendum).
