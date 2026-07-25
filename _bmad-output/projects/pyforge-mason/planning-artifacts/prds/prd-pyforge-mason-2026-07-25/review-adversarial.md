---
title: "Adversarial review — PRD: Mason (pyforge-mason)"
target: prd.md
reviewed: 2026-07-25
reviewer: adversarial review pass
verdict: MAJOR REVISION REQUIRED — structurally sound decision record, three critical defects that block story authoring
---

# Adversarial Review — PRD: Mason

**Scope of this review.** `prd.md` (46 FRs / 16 NFRs / 9 D-records), read against the product
brief + addendum, the two research reports, `docs/dreams/ecosystem-crew.md` § 5 (the charter the
PRD declares binding), and the live repository (CFE scripts, `pixi.toml`, `scripts/spec_surface_check.py`).
Claims were verified on disk where verification was possible.

**Verdict.** The central decision (D-1, seam by capability) is well-argued, well-evidenced, and
should stand. The enforcement mechanism (FR-42 – FR-46) is the right instinct. But the PRD contains
**three critical defects** — one self-contradiction that makes closeout impossible, one flagship
user journey that its own D-record puts out of scope, and one command form that the PRD makes
illegal while simultaneously naming it the primary success metric. All three are cheap to fix at
PRD stage and expensive to discover in story 4.

Findings are ordered by severity within each requested category. Severity is **critical** (blocks
story authoring or guarantees a defect at closeout), **high** (a story author will hit it and be
unable to proceed without a PM decision), **medium** (rework or an untestable acceptance criterion).

---

## 1. Internal contradictions

### C-1 · CRITICAL — FR-45 forbids the commit that CLAUDE.md Rule 2 mandates

**FR-45** (Consequences): *"No commit in Mason's history touches `.claude/skills/conda-forge-expert/**`,
`.claude/scripts/conda-forge-expert/**`, or `.claude/tools/conda_forge_server.py`."*
**SM-6** restates it: *"zero commits touching the CFE surface."*

**§9 Constraints**, three paragraphs earlier: *"Rule 2 requires that every conda-forge effort close
with a retrospective that edits the CFE skill — **including this one**."*

CLAUDE.md Rule 2 is explicit about where the retro lands: `SKILL.md`, `reference/*.md`,
`guides/*.md`, and a new `CHANGELOG.md` version entry — all inside
`.claude/skills/conda-forge-expert/`. It is described as "not optional and not deferrable," and
"an effort is not 'done' until the retro lands."

So the PRD requires a commit that FR-45 defines as a requirement violation, and SM-6 counts as a
metric failure. Mason cannot be both Rule-2-compliant and FR-45-green. This is not a wording
problem: a story author closing epic 6 must either violate a numbered FR or violate a project rule
that overrides it.

Compounding it: §9 *"Upstream defects noted, not owned"* routes four real CFE findings to "a CFE
Rule-2 retrospective" — i.e. more commits FR-45 forbids.

**Remedy.** Restate FR-45 as: *"No commit in Mason's **implementation** touches the CFE surface.
The Rule-2 closeout retrospective is the single, explicitly-carved-out exception; it lands after the
final Mason story, in its own commit, and updates `spec-packaging-factory`'s memlog + the surface
baseline."* Mirror the carve-out in SM-6. Add it to §5 Non-Goals ("Mason does not modify the CFE
surface") which currently reads as absolute.

---

### C-2 · CRITICAL — UJ-1, the flagship journey, is out of scope by D-2 and undeliverable through CFE

**UJ-1** describes Dana, maintainer of "a mid-sized analytics library," running
`mason package --target library --ship pypi,conda-forge` and getting a staged-recipes PR back. It
is the first journey listed, the one the vision paragraph sells, and the one FR-17's asymmetric
receipt exists to serve.

**D-2** scopes v1 to *"repositories where a CFE root is discoverable (this repo, or another with
its own `.claude/`)."* Dana's analytics library has no `.claude/scripts/conda-forge-expert/`.
By the PRD's own §2.2, she is a **Non-User** ("Someone in a repository with no discoverable CFE
installation").

It is worse than a scoping mismatch. Verified on disk, `submit_pr.py` does this:

```
118:    recipe_dir = REPO_ROOT / "recipes" / recipe_name
192:    dest = fork_path / "recipes" / recipe_name
200:    _run(["git", "add", f"recipes/{recipe_name}"], cwd=fork_path)
```

The submission path reads the recipe from **this repository's** `recipes/<name>/` and writes into a
clone of **the operator's `staged-recipes` fork**. The research report independently records
`recipes/` hardcoded in 17 canonical scripts. So `--ship conda-forge` executed from an arbitrary
project directory has no source directory CFE will read from and no fork CFE knows about. FR-23
("If a recipe path is given, it is used") does not close this: the gap is not *where the recipe
came from*, it is *the submission mechanics for a project that is not this repo*.

Net effect: **the product's stated differentiator — one command, both ecosystems — is only
executable inside `local-recipes` in v1.** D-1's option table row *"Distribution: Works without CFE
for 2 of 3 verb families"* is therefore true only in the narrow sense that `mason package` *starts*;
its conda half does not.

**Remedy — pick one, explicitly:**
(a) Rewrite UJ-1 so Dana operates from a CFE-co-located repo, and add a sentence to §1 and D-1
stating that the dual-ship motion's conda half is CFE-co-located in v1; or
(b) Scope FR-23 to `channel:<name>` only for v1 and defer `--ship conda-forge` to v2 (this makes
`mason package` genuinely CFE-independent and makes FR-44/SM-3 true as written — see H-1); or
(c) Add an FR for "external-project staged-recipes submission" and accept it as a large net-new
capability (see § 6, scope realism — this is the single biggest hidden item in the PRD).

---

### C-3 · CRITICAL — the ship command has no verb, and FR-30 makes the primary success metric illegal

**FR-30**: *"`mason <noun> <verb>` throughout"*; *"`mason <noun>` with no verb prints that noun's
verbs and exits non-zero."*

Every place the PRD actually invokes the ship motion uses a **noun with no verb**:

- UJ-1: `mason package --target library --ship pypi,conda-forge --dry-run`
- FR-24: `mason package --ship pypi`
- SM-1 (the primary success metric): `mason package --ship pypi`
- The binding charter (`ecosystem-crew.md` § 5, quoted verbatim as binding in §14):
  `mason package --target library --ship pypi,conda-forge`

Under FR-30 every one of these prints a help message and exits non-zero. Meanwhile the only
`mason package` verb the PRD defines is **FR-15 `mason package build`**, whose consequence is
explicitly *"nothing is uploaded."*

**There is no FR defining the command that ships.** FR-16 – FR-23 all describe the behaviour of
`--ship` without ever saying which verb carries it. A story author cannot write "implement the ship
command" because the PRD never names it.

Note this also breaks §14's own assumption: the charter cadence is declared "binding scope, taken
verbatim," and FR-30 contradicts it.

**Remedy.** Either (a) add `mason package ship` (or `publish`) as an FR and update UJ-1 / FR-24 /
SM-1 to use it, accepting the deviation from the charter and recording it as a D-record; or
(b) carve `package` out of FR-30's noun-verb rule (`mason package` with flags is a legal terminal
command) and say so in FR-30 and FR-15. (a) is cleaner; (b) preserves the charter. Do not leave it
implicit.

---

### C-4 · HIGH — FR-23 contradicts FR-44 and SM-3 as literally written

This is the contradiction the review brief asked about, and it is real but narrower than it looks.

**FR-44**: *"A meta-test runs **every** `mason package` and `mason environment` verb with the CFE
root guaranteed unresolvable and asserts **each behaves normally**."*
**SM-3**: *"**Every** `mason package` / `mason environment` verb passes with the CFE root absent."*
**FR-23**: *"This is the one path in `mason package` that requires the CFE root; its absence
produces the FR-5 error **for that target only**."*

FR-23 is the correct, honest requirement. FR-44 and SM-3 are stated unconditionally and are false
in the presence of FR-23. A meta-test written to FR-44's text will fail the day FR-23 lands, and
its author will "fix" it by weakening the assertion — which is precisely the seam-erosion FR-44
exists to prevent. A weakened enforcement test is worse than none, because SM-3 will report green.

**Remedy.** Restate FR-44 as: *"No `mason package` or `mason environment` **verb** fails to run with
the CFE root unresolvable. The `conda-forge` **ship target** is the single enumerated exception: it
returns the FR-5 error for that target while every other target in the same invocation completes
normally — and the meta-test asserts exactly that shape, including that `pypi` still uploads."*
Make the exception an enumerated allowlist of one in the test, so adding a second requires editing
the test deliberately. Mirror in SM-3.

---

### C-5 · HIGH — FR-46 contradicts NFR-13

**FR-46**: *"For a representative recipe operation, Mason's result matches the corresponding
**direct CFE invocation's** result."*
**NFR-13**: *"Every adapter code path has a test using a **fake CFE root**; **no test requires a
real CFE installation**."*

FR-46 cannot be satisfied without a real CFE installation — comparing against a direct invocation
*is* invoking CFE. Either NFR-13 gains a carve-out for the fidelity test (and CI must then provide a
CFE root, which is a CI requirement no FR states), or FR-46 is unimplementable.

Separately, FR-46 is **untestable as written** — see U-1.

**Remedy.** NFR-13 → *"Every adapter code path has a unit test using a fake CFE root. Exactly one
integration test (FR-46) requires a real CFE root; it is marked and skipped when absent, and is
required-not-skipped in the repo's own CI."* Note this is the `PUBLISH_RANGE_REQUIRED` pattern
already used by `pyforge-atlas` in `pixi.toml` — cite it.

---

### C-6 · MEDIUM — NFR-9 contradicts FR-7, FR-25, and (ambiguously) FR-14

**NFR-9**: *"**Every** mutating operation defaults to dry-run."*

- **FR-7 `mason recipe new`** writes a `recipe.yaml` and has no dry-run consequence. Under NFR-9 it
  writes nothing by default — which makes UJ-2 ("`mason recipe new --from-pypi some-lib` produces a
  v1 `recipe.yaml`") fail.
- **FR-25 `mason environment lock`** writes a lockfile, no dry-run consequence. Under NFR-9 the
  product's third verb family does nothing by default.
- **FR-14 `mason recipe update`** says *"`--dry-run` supported"* — supported, not defaulted — while
  FR-13 says *"`--dry-run` **is the default**."* Two adjacent FRs, two different postures, no stated
  reason.

**Remedy.** NFR-9 → *"Every **irreversible or externally-visible** operation (upload, PR creation)
defaults to dry-run. Local file writes do not."* Then state FR-14's default explicitly.

---

### C-7 · MEDIUM — FR-6 credential isolation vs `channel:<name>` in an enterprise, and NFR-6

**FR-6**: *"Mason's own code reads **no** `JFROG_*` variable."*
**FR-16**: `channel:<name>` is a *"synchronous upload to a named conda channel."*
**FR-20** specifies **PyPI credentials only**.
**NFR-6**: *"Mason imposes no direct-internet assumption; proxy/mirror routing is inherited through
the process environment."*

For `--ship pypi` and `mason recipe *`, FR-6 is correct and elegant — the credential lives in the
child process. But `channel:<name>` is a **Mason-native** upload (there is no CFE counterpart), and
UJ-3's Kim ships to a JFrog-hosted conda channel. Mason must then authenticate to that channel
itself. FR-6 forbids the obvious mechanism, FR-20 does not supply an alternative, and NFR-6's
"inherited through the process environment" does not apply to an upload Mason performs in-process.

**Remedy.** Add a consequence to FR-20 covering conda-channel credentials (anaconda.org token /
prefix.dev token / JFrog), and narrow FR-6 to *"Mason reads no CFE credential variable"* — naming
the variables the channel uploader is permitted to read, so the boundary stays testable.

---

### C-8 · MEDIUM — FR-40 pins engines Mason may never invoke, with no precedence rule against CFE's

**Glossary** defines engines as including `rattler-build` and `grayskull`. **FR-40** makes engines
conda run-dependencies of the Mason member package with in-code version constants and a sync
meta-test. But `mason recipe build` (FR-9) and `mason recipe new` (FR-7) delegate to CFE, which
invokes *its own* `rattler-build` / `grayskull` from *its* environment.

So Mason pins engine versions it does not call, and there are now two pins for the same engine with
no stated precedence. Worse, an engine **version policy** for recipe building is arguably recipe
knowledge — the exact thing FR-42 forbids — and FR-42's meta-test would not catch it because it is
a version constant, not a gotcha ID.

**Remedy.** Split the Glossary's engine list into *Mason-invoked* (`build`, `twine`, `conda-lock`,
`pixi`) and *CFE-invoked* (`rattler-build`, `grayskull`), and scope FR-40 to the former only.

---

## 2. Untestable "testable consequences"

Bullets stated under **Consequences (testable)** that a story author cannot turn into an assertion.

### U-1 · HIGH — FR-46 "Mason's result matches the corresponding direct CFE invocation's result"

Undefined comparison. Byte-equal stdout? Mason's entire job (§4.2: *"Mason contributes verb design,
argument ergonomics, output formatting"*) is to **not** produce identical output, so byte-equality
is false by construction and semantic-equality has no stated predicate. As written, whoever
implements it will choose the comparison that passes.
**Fix:** name the predicate — e.g. *"the JSON body Mason emits under `--format json` is a superset
of the CFE script's JSON body for the same arguments, with every CFE key present and unmodified."*
That is checkable and it is what the requirement actually means.

### U-2 · HIGH — FR-24 "produces the same artifacts the repository's existing hand-run build triad produces"

Wheels and sdists are not byte-reproducible by default (timestamps, file ordering,
`SOURCE_DATE_EPOCH` unset). "Same artifacts" therefore fails on the first run for reasons unrelated
to Mason.
**Fix:** *"produces artifacts with the same filenames, the same `METADATA`/`info/index.json`
contents, and the same file manifest as the hand-run triad."*

### U-3 · MEDIUM — FR-45 "No commit in Mason's history touches …"

Unbounded and rebase-fragile. Over what commit range? bmad-loop squashes and rebases; "Mason's
history" is not a defined ref set. And this is not a property a shipped test can hold — it is a CI
check over a diff.
**Fix:** *"`git diff --name-only <base>...HEAD` contains no path under the CFE surface, enforced in
the PR gate"* — plus the Rule-2 carve-out from C-1.

### U-4 · MEDIUM — FR-42 "no conda-forge policy constant, no pin table, no recipe-format field defaults"

The most valuable test in the product (the PRD's words) has no decision procedure. "Gotcha
identifier" is checkable (`G\d+`). "Policy constant" is not: is `python_min` a policy constant? Is
`"recipe.yaml"` a recipe-format field default? Is the CFE import-floor list (FR-3) a CFE constant?
Without an enumerated detection rule this test will be written to whatever the implementation
already contains, i.e. it will be vacuous on day one.
**Fix:** enumerate the detectors: (i) regex `\bG\d{1,3}\b`; (ii) an allowlist-checked scan for
conda-forge vocabulary (`noarch`, `pin_subpackage`, `run_exports`, `python_min`, `stdlib`,
`compiler(`, `staged-recipes` outside the adapter); (iii) no dict literal whose keys are
recipe-schema section names. Then state the allowlist file's path.

### U-5 · MEDIUM — FR-5 "a message naming all four resolution steps and how to satisfy each"

Step 4 of FR-2's chain is *"No match → degradation"* — not a resolution step and not satisfiable.
The error can name three ways to satisfy and one outcome.
**Fix:** *"names the three resolution mechanisms and how to satisfy each."*

### U-6 · MEDIUM — FR-28 "exits non-zero when the lockfile is **stale** relative to its manifests"

"Stale" is undefined. conda-lock has `--check-input-hash`; `pixi lock` has its own check; a
hand-rolled definition (hash the manifests, compare to a recorded hash) is Mason implementing
policy, which FR-25 says it does not. Which is it?
**Fix:** define staleness as *"the engine's own staleness check reports out-of-date"* and record
which engine flag, or accept a Mason-owned hash and say so.

### U-7 · MEDIUM — FR-1 "Every `mason recipe` subcommand's call graph reaches CFE through exactly one adapter function"

"Call graph" implies static analysis Mason does not have as a dependency (FR-41: lean deps, no new
runtime dep — but this is a test dep, which the PRD never discusses). Also *"exactly one adapter
function"* — one per subcommand, or one shared function for all? Both readings are defensible and
they imply different adapter designs.
**Fix:** replace with the FR-43 formulation (import/string scan), and delete FR-1's bullet as
duplicative (see M-7).

### U-8 · MEDIUM — FR-29 "…and in the lockfile's provenance where the format allows"

"Where the format allows" is an escape hatch that makes the bullet unfalsifiable. Also: `conda-lock.yml`
carries content hashes; post-hoc mutation of the file to inject provenance risks invalidating them.
**Fix:** name the two formats and state, per format, whether provenance is written or only reported.

### U-9 · MEDIUM — NFR-3 determinism, applied to CFE-delegating verbs

*"Identical inputs produce identical JSON output"* — but `mason recipe new --from-pypi` hits the
network, `mason recipe update` reads the latest upstream version, and `mason recipe submit` returns
a PR number. The "modulo timestamps and provenance fields" carve-out does not cover any of these.
**Fix:** scope NFR-3 to *"Mason's own transformation is deterministic: given a fixed CFE result,
Mason's rendering is byte-identical."* That is both true and testable with the fake CFE root.

### U-10 · LOW — NFR-12 "Mason's own logic works on linux-64, osx-arm64, win-64"

Unverified for the delegated half: no evidence in the research that CFE's `local_builder.py` or
`submit_pr.py` are exercised on win-64. Stating platform parity for Mason while the verbs are
CFE-shaped invites a story author to claim it untested.
**Fix:** add *"…verified by running the Mason test suite on all three; CFE-delegating verbs are
covered by the fake-CFE tests only."*

---

## 3. Missing FRs — capability gaps a story author will hit

### M-1 · HIGH — No configuration file (asked about explicitly)

Nothing in the PRD covers persistent per-project configuration. FR-35 gives five global flags;
FR-2/FR-3 give two env vars. Everything else must be retyped every invocation: the recipe path
(FR-23), the channel (FR-16), the platform list (FR-27), the manifest set (FR-26), the timeout
(FR-4 says *"a **configurable** timeout"* — configurable by **what**? no flag, no env var, no file
is defined anywhere), the target (FR-21), the artifact output dirs.

This is not a nicety: `mason package --ship` is a release-time command whose arguments are
properties of the project, not of the invocation. Every incumbent the research surveys (hatch,
pixi, maturin) is configured from `pyproject.toml`.

**Remedy.** Add an FR: precedence `flag > env var > project config (`[tool.mason]` in
`pyproject.toml`) > default`, with the config file's keys enumerated and `mason doctor` reporting
which file was loaded. Note this also gives FR-4's "configurable timeout" a home.

### M-2 · HIGH — No logging specification

FR-35 declares `--verbose` / `--quiet` exist. FR-6 asserts *"Mason logs no environment-variable
values **at any verbosity**"* — an assertion about a logging subsystem the PRD never specifies.
Undefined: log destination (stderr, presumably, but NFR-4 only constrains stdout); whether
`--verbose` echoes the CFE subprocess's stderr; what `--quiet` suppresses; whether logs are
structured under `--format json`; whether the CFE argv is logged (it may carry a `--token`).

A story author implementing FR-9 (`mason recipe build` — a multi-minute operation) faces an
unanswered question the PRD does not acknowledge: **is CFE's output streamed live, or captured and
replayed at the end?** FR-4 says the result *carries* stdout, implying capture — which means a
`mason recipe build` of a large package prints nothing for ten minutes. That is a product-quality
decision, not an implementation detail.

**Remedy.** Add an FR covering: streams (all diagnostics to stderr), levels and what each shows,
whether the child's stderr passes through under `--verbose`, and the streaming-vs-capture decision
for long-running delegated commands.

### M-3 · HIGH — No ship-receipt persistence, but NFR-8 and FR-18 require it

**FR-18**: *"Retrying is safe: an already-terminal target is skipped, not re-uploaded."*
**NFR-8**: *"Re-running a completed ship does not duplicate an upload."*

Across separate process invocations — which is what "re-running" means — this requires **persisted
state**. Nothing defines a receipt store: no path, no format, no lifetime, no `--force` override,
no behaviour when the store is absent or stale. For `pypi` the index's own 400-on-duplicate gives
accidental idempotence; for `conda-forge` there is nothing, and a re-run opens a **second
staged-recipes PR** — a visible, embarrassing failure in a human review queue.

**Remedy.** Add an FR for the receipt store (location, JSON schema, `--force`, and the rule that an
absent store degrades to "attempt and let the destination reject", never to silent duplication).
This also gives FR-17's receipt a serialization format, which it currently lacks.

### M-4 · HIGH — No TestPyPI / alternate-index target, which makes SM-1 an untestable one-way door

**FR-16**: *"**Any other value** is rejected with the valid set listed."* The valid set is exactly
`pypi`, `conda-forge`, `channel:<name>`.

Consequence: there is **no way to rehearse `--ship pypi`**. SM-1 — the primary success metric —
requires publishing `pyforge-mason` to the real PyPI, which is irreversible (yank only, name
permanently claimed), and it is the *first* real execution of a code path with no lower-stakes
rehearsal. Standard practice (and twine's own documentation) is `--repository testpypi` first.

`channel:<name>` gives the conda half a safe rehearsal target. The PyPI half has none.

**Remedy.** Either extend FR-16 with `pypi:<repository>` / a `--repository` flag, or add
`testpypi` as a fourth target. Also soften SM-1 to *"a real upload to TestPyPI plus a green
production dry-run"* so the metric is achievable without a one-way door, with the production
publish as a separate, attended, human-gated event.

### M-5 · MEDIUM — No version-source FR

**FR-22** compares "the wheel version and the conda package version." Nothing says how Mason
determines a project's version, what happens when the two build systems read it from different
places (`pyproject.toml` static vs `setuptools-scm` vs a `pixi.toml` `[package] version`), or what
the check does when only one artifact was built (`--ship pypi` alone).

Also missing: FR-22 has **no recipe arm**. For `--ship conda-forge` the version that matters is the
one in `recipe.yaml`, which FR-22 never compares against the wheel — the exact skew most likely to
occur in practice.

### M-6 · MEDIUM — No FR registers Mason with `spec_surface_check`

**FR-45** asserts *"the repository's `spec_surface_check` remains green across the whole effort."*
Verified on disk, that checker enforces **coverage**: *"every tracked file matches ≥1 spec surface
OR an allowlist entry."* Mason will add ~30 tracked files under `src/shared/packages/pyforge-mason/`.
Unless a `spec-pyforge-mason/SPEC.md` with a `surface:` glob exists (or an allowlist entry lands),
the checker goes **red on Mason's first commit** — the opposite of what FR-45 asserts.

It also enforces **drift**: a governed file changing while its spec's `.memlog.md` has not moved is
a finding. So Mason needs an ongoing spec + memlog discipline that no FR describes.

**Remedy.** Add an FR: *"Mason's tracked files are governed by `spec-pyforge-mason`'s `surface:`
globs; the effort maintains the spec memlog and re-stamps the surface baseline."* Reference
`scripts/spec_surface_check.py` and `scripts/spec_surface_allowlist.txt`.

### M-7 · MEDIUM — `mason recipe submit` vs `mason package --ship conda-forge` (asked about explicitly)

**Yes, these are two paths to the same outcome, and yes, the PRD's silence about it is a defect** —
though a fixable one, not necessarily a duplicated implementation.

Evidence they are the same operation: FR-13 *"A user opens a staged-recipes pull request"*; FR-16
`conda-forge` *"asynchronous; opens a staged-recipes pull request."* Both return a ship receipt.
Both wrap CFE's two-phase `prepare_submission_branch` → `submit_pr` flow.

Where they diverge, incoherently:

| | FR-13 `recipe submit` | FR-19/FR-23 `package --ship conda-forge` |
|---|---|---|
| Confirmation | `--dry-run` is the **default** | requires an explicit **confirming flag** |
| Recipe source | a recipe that exists | given path, else offer to generate (FR-23) |
| Receipt | ship receipt | ship receipt, aggregated with other targets |
| CFE required | yes (FR-5) | yes, "for that target only" (FR-23) |

Two different confirmation mechanisms for the same irreversible act is a genuine defect — a user
who learns one is surprised by the other, and a story author will implement them separately.

Second, structural: **FR-13 lives in the `recipe` feature but returns a "ship receipt," a concept
defined by the `package` feature (Glossary + FR-17).** That is a backwards dependency across the
two features the PRD is at pains to keep architecturally independent, and it forces an epic-ordering
constraint the PRD does not state (see § 4).

**Remedy.** State the relationship in one sentence in §4.3: *"`mason package --ship conda-forge`
invokes the same code path as `mason recipe submit`, after resolving a recipe per FR-23. The
confirmation semantics are identical: `--dry-run` is the default for both, and a single named
confirming flag applies to both."* Then delete the divergence.

### M-8 · MEDIUM — Crew-boundary collisions unaddressed

- **`mason doctor` (FR-34)** vs the charter's § 6 Doctor, whose *first* listed responsibility is
  *"Pre-flight Diagnostics: a `doctor` self-check verifies every required engine and toolchain is
  present."* The PRD declares the charter binding (§14) and then puts `doctor` in Mason. Defensible
  (every CLI needs a self-check) but it needs a sentence, or `pyforge-doctor` will collide.
- **`mason recipe scan` (FR-12)** vs `pyforge-warden` — shipped, 31/31, merged, and the crew's
  designated scanner. The addendum names the mechanism (`[project.optional-dependencies]`, atlas's
  AC-8 pattern). The PRD instead routes scanning to CFE's `vulnerability_scanner.py`. That may be
  right, but it produces a second scanning path in the same workspace — the atlas failure mode the
  PRD is organized around. OQ-3 covers autotick ownership only.

**Remedy.** One paragraph in §5 Non-Goals or a new D-record: what Mason owns vs Doctor/Warden.

### M-9 · MEDIUM — No FR for the `--dry-run` plan's fidelity, and no FR for `--ship` preflight ordering

FR-19 says the plan *"names every target, artifact, and destination."* FR-20 says *"a missing
credential is detected **before** any artifact is built or uploaded."* FR-22 says versions are
compared *"before any upload."* These three imply a preflight phase with an ordering
(credentials → build → version check → upload) that no FR states, and which determines whether a
dry-run detects a missing credential (it should) or a version skew (it should). A story author will
guess.

---

## 4. Unstated dependencies that break epic ordering

§6.1 lists MVP scope in an order that reads as an epic sequence: adapter → recipe → package →
environment → CLI shell → distribution → enforcement. That order is wrong in at least five places.

1. **CLI shell (FR-30 – FR-35) must precede every verb.** FR-31's `--format json`, FR-32's exit-code
   module (*"Exit codes originate from one module"*), and FR-33's typed errors are consumed by
   FR-5, FR-8, FR-9, FR-13, FR-17, FR-28. Listed 5th; must be 1st or 2nd.
2. **Distribution (FR-36 – FR-41) must precede FR-24/SM-1.** Self-hosting ships the member package;
   the member package must exist, with its `pyproject.toml`, entry point, and build triad. Listed
   *after* `package`.
3. **FR-13 (`recipe submit`) depends on FR-17 (ship receipt),** which lives in the `package`
   feature. The recipe epic cannot complete before the package epic's receipt model lands — or the
   receipt must be pulled out into the CLI/shared epic. The PRD's own Glossary places "ship receipt"
   as a cross-cutting term; the FR grouping does not reflect it.
4. **FR-23 (`package --ship conda-forge`) depends on FR-7 (`recipe new`) and FR-13 (`recipe submit`).**
   The PRD presents `package` as the CFE-independent family; in ordering terms it is downstream of
   the entire recipe epic. Any plan that runs the package epic first will stall.
5. **FR-40's engine-sync meta-test cannot be authored until OQ-2 and OQ-4 resolve.** FR-40 pins
   "whichever engines it pins"; OQ-2 (does `channel:` upload via `pixi publish`, `anaconda upload`,
   or both?) and OQ-4 (conda-lock vs pixi for FR-25) each add or remove an engine. Two **in-scope
   MVP FRs** have undecided mechanisms in a PRD marked `status: final`.

**Also unstated:** FR-2/FR-3 (resolution + interpreter) must precede every `mason recipe` verb —
this one *is* implied by §6.1's ordering, and is the only dependency the ordering gets right.

**Remedy.** Add a short "build order" note to §6.1: shell + errors + exit codes → adapter →
distribution skeleton → recipe verbs → package (build, then ship) → environment → enforcement
tests (authored alongside, not last). And mark OQ-2/OQ-4 as **blocking** with a resolve-by
milestone, not "revisit at architecture."

---

## 5. Claims not supported by the cited evidence

### E-1 · MEDIUM — "The repository already performs **this exact motion** by hand" (§7, SM-1)

Verified on disk: `pixi.toml` defines `pyforge-warden-build-conda` / `-build-dist` / `-build` and
the identical atlas triad. These **build**. There is **no publish, upload, or twine task for either
sibling** — the only task named `publish` (line 224) is `pyforge-atlas`'s static-Parquet emitter,
unrelated to package distribution. `twine >= 6.2.0` is a root dependency (line 659) but nothing
invokes it.

So the repo dogfoods the **dual-artifact build**, not the **dual-ship**. The brief was careful
("dogfoods the exact dual-artifact motion by hand"); the PRD escalated it to "this exact motion,"
where "this" is `mason package --ship`. The upload half — credentials, index registration,
idempotence, receipts, channel auth — is **entirely unrehearsed in this repository**, and neither
sibling has ever been published anywhere.

This matters because §7 uses the claim to argue SM-1 is *"a near test, not an aspiration."* The
build half is near. The ship half is net-new and unproven. Combined with M-4 (no TestPyPI target),
SM-1's first execution is also its production execution.

**Remedy.** Restate: *"The repository already dogfoods the dual-artifact **build** by hand for two
siblings; the **upload** half is net-new and has never been exercised here."*

### E-2 · MEDIUM — D-1's "Works without CFE for 2 of 3 verb families"

Half-true, and it is the row that carries the decision. `mason package` starts without CFE and can
complete `pypi` and `channel:` — but its headline capability, `--ship conda-forge`, cannot (FR-23,
and C-2 above). The table row invites the reader to conclude the differentiator survives CFE
absence. It does not.

**Remedy.** *"Works without CFE for `environment`, and for `package`'s `pypi` / `channel:` targets;
the `conda-forge` target requires CFE."*

### E-3 · MEDIUM — FR-9's Docker/CI-parity build has no CFE counterpart

FR-9: *"a Docker/CI-parity build is available behind an explicit flag."* Verified: CFE's
`local_builder.py` describes itself, in its module docstring and its argparse description, as a
**"Docker-less local builder"** that *"wraps rattler-build"*. Its only Docker references are a
comment noting behavioural parity with `.scripts/run_docker_build.sh`. No CFE script executes a
containerized build.

So FR-9's second bullet is either undeliverable by delegation, or it is **net-new
container-build orchestration written inside Mason** — which is conda-forge CI knowledge (image
selection, `conda-forge.yml` / `.ci_support` variant handling, mount layout) and sits squarely
against D-1 and FR-42, without FR-42's detectors being able to see it (it is code, not a constant).

**Remedy.** Drop the bullet from v1 (native-only, matching CFE's actual capability) and record it in
§6.2 Out of Scope, or open it as an FR with its own justification.

### E-4 · LOW — "all 60 CFE scripts" use argparse (§4.5)

The research says 60 **of 66**. Minor, but §4.5 uses it as a normative precedent claim.

### E-5 · LOW — FR-7's source flags do check out

Verified: `recipe-generator.py` exposes `pypi`, `template`, `github`, `cran`, `cpan`, `luarocks`,
`npm` subcommands. FR-7's four flags all have real CFE counterparts. **This claim holds** —
recorded because the addendum's "multi-ecosystem" deferral could be misread as contradicting it
(the deferral is about *updaters*, not *generators*; the PRD is correct and could say so in one
clause).

---

## 6. Scope realism — is 46 FRs deliverable?

**The FR count is not the problem; the distribution of mass is.** Roughly:

- **FR-36 – FR-41 (6 FRs, distribution)** — near-zero risk. Two prior instances, copied wholesale.
  Realistically 1–2 stories.
- **FR-30 – FR-35 (6 FRs, CLI shell)** — low risk, ported from `pyforge.warden.cli`. 2 stories.
- **FR-42 – FR-46 (5 FRs, enforcement)** — low-to-medium; U-4 must be fixed first or they are
  vacuous. 1–2 stories.
- **FR-1 – FR-6 (6 FRs, adapter)** — medium. The design is settled by the research; the work is
  real but bounded. 2–3 stories.
- **FR-25 – FR-29 (5 FRs, environment)** — genuinely thin, as the PRD says. 2 stories, *after*
  OQ-4 resolves.
- **FR-7 – FR-14 (8 FRs, recipe)** — **larger than "porcelain" suggests.** See below.
- **FR-15 – FR-24 (10 FRs, package)** — **contains the two enormous items.** See below.

### The three items sized as small that are not

**(a) `--ship conda-forge` for a project that is not this repository — epic-sized, possibly out of reach.**
Covered in C-2. `submit_pr.py` reads from `REPO_ROOT/"recipes"/<name>` and writes into a
`staged-recipes` fork clone. Making that work for an arbitrary project means Mason materializes a
recipe into a staged-recipes checkout, manages the fork, and drives CFE's two-phase flow from
outside its assumed layout — or CFE gains a `--recipe-dir` argument, which FR-45 forbids. **This
single bullet (FR-23) plausibly exceeds the entire `environment` family in cost.** It should either
be scoped to "inside a CFE-co-located repo, using that repo's `recipes/`" or deferred.

**(b) `.conda` production for arbitrary projects — undefined and non-trivial.**
FR-15: *"and a `.conda` via `pixi build`."* `pixi build` requires the target project to carry a
`pixi.toml` with a `[package]` table, a `[package.build.backend]`, and the workspace-level
`preview = ["pixi-build"]`. Mason's siblings have all of that because *this repo* set it up. Dana's
analytics library has a `pyproject.toml` and nothing else. Mason must therefore **synthesize a pixi
package manifest** for arbitrary projects — a capability no FR mentions, no research report sizes,
and which has its own failure surface (backend selection, dependency translation PyPI→conda —
the exact `tree_sitter` vs `tree-sitter` problem the brief opens with).

**(c) Eight bespoke CFE integrations, not one generic adapter.**
Verified per-script: `validate_recipe.py` gates JSON behind a flag; `recipe_optimizer.py`,
`failure_analyzer.py`, `local_builder.py`, `submit_pr.py`, `recipe_updater.py` emit JSON
**unconditionally**; `submit_pr.py` (lines 65, 162, 189) and `recipe_updater.py` (lines 104, 121)
print **non-JSON progress lines to stdout before the JSON body** — confirming FR-4's tolerance shim
is genuinely required, exactly as the PRD says.

The consequence the PRD does not draw: **`--format text` (FR-31's default) requires Mason to render
human output from each script's JSON, which means Mason holds each script's JSON field schema.**
That is eight distinct output contracts, unversioned by §11's own admission (*"CFE coupling is not
versioned"*), each of which breaks silently on a CFE field rename. It also stresses FR-42: field
names *are* domain vocabulary, and the meta-test has no principled way to distinguish
`result["gotchas_applied"]` (fine?) from a gotcha constant (forbidden).

This is also where **SM-4 ("free inheritance": a new CFE gotcha changes Mason's behaviour with no
change to Mason") is weaker than advertised.** It is true for gotchas applied *inside* generation —
the case the PRD names. It is false for: a new CFE dependency (FR-3's hard-coded import floor goes
stale), a new CFE JSON field (Mason's text renderer silently drops it), a new CFE subcommand, or a
renamed field (Mason's renderer breaks). Worth stating honestly.

### Bottom line on realism

**46 FRs is deliverable — after two cuts.** With FR-23 scoped to CFE-co-located repos (or deferred),
and FR-9's Docker bullet dropped, the remainder is a credible 6-epic / ~28–34-story effort of the
same shape as `pyforge-warden` (31 stories), with a materially smaller net-new surface than warden
had. Without those cuts, `mason package` alone is a warden-sized project hiding inside one feature
section, and the PRD's implicit sizing ("the largest net-new build" — but only one sentence of
acknowledgement) will not survive contact with story 3.1.

---

## Summary of required actions before this PRD is implementable

**Must fix (blocks story authoring):**

1. **C-1** — carve the Rule-2 retro out of FR-45 / SM-6, or the effort cannot close.
2. **C-3** — name the ship command (`mason package ship`?) or exempt `package` from FR-30; update
   UJ-1, FR-24, SM-1 to match.
3. **C-2** — decide UJ-1's fate: rewrite the journey, defer `--ship conda-forge`, or fund the
   external-submission capability as its own epic.
4. **C-4** — restate FR-44/SM-3 with the FR-23 exception enumerated.
5. **M-7** — state the `recipe submit` ↔ `package --ship conda-forge` relationship and unify the
   confirmation semantics.

**Should fix (rework if deferred):**

6. **C-5** — NFR-13 carve-out for FR-46; **U-1** — define "matches."
7. **M-1 / M-2 / M-3** — add FRs for configuration file, logging, and receipt persistence.
8. **M-4** — add a rehearsal target and soften SM-1 accordingly.
9. **M-6** — add the `spec_surface_check` registration FR.
10. **U-4** — enumerate FR-42's detectors, or "the single most valuable test in the product" ships
    vacuous.
11. **E-1 / E-2 / E-3** — correct the three overstated claims.
12. **§4 ordering** — add a build-order note; mark OQ-2 / OQ-4 as blocking.

**Nice to have:**

13. **C-6 / C-7 / C-8**, **M-5 / M-8 / M-9**, **U-2 / U-3 / U-5 – U-10**, **E-4**.
14. §6.1 says *"the four enforcement meta-tests (FR-42 – FR-46)"* — that is five.
15. Check the `mason` console-script name for PATH collisions (notably `mason.nvim`'s binary)
    before §11 freezes the public surface.

## What is right and should not be touched

Recorded so a revision does not damage the parts that work:

- **D-1 and its evidence.** The atlas-vs-warden contrast is the strongest argument in the document
  and it is verifiable on disk. The wrap/build boundary drawn *by capability* is correct.
- **FR-17's asymmetric receipt.** Genuinely a correctness insight, not a feature — the PRD is right
  that a uniform "success" would be a bug.
- **FR-4's tolerant JSON parsing.** Verified necessary: `submit_pr.py` and `recipe_updater.py` both
  print progress lines to stdout before their JSON.
- **D-7's interpreter chain.** The lean-env failure mode is real and would have been a silent,
  confusing bug.
- **The counter-metrics (SM-C1 – SM-C3).** Rare, and exactly right for this failure mode.
- **§14's assumptions index and the two `[NOTE FOR PM]` markers.** Unusually honest; keep them.
