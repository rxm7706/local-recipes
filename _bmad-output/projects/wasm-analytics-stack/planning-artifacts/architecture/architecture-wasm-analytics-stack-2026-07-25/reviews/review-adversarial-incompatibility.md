---
title: Adversarial Incompatibility Review — ARCHITECTURE-SPINE.md
target: ../ARCHITECTURE-SPINE.md
lens: 'Attack the spine as an adversary: construct two units one level down that each obey every AD to the letter yet still build incompatibly'
created: '2026-07-25'
---

# Adversarial Incompatibility Review — Wasm Analytics Stack Architecture Spine

## Method

For each AD (AD-1..AD-8) and each Deferred item, I tried to construct a
concrete pair of independently-building units — two directories, two roles,
two build steps — that each honor the rule's literal text while producing
artifacts that do not compose, or that silently reintroduce the exact failure
mode the AD claims to prevent. Every finding below names the two units, what
each one would plausibly build, why each is letter-compliant, and exactly how
the pair fails to compose. Each finding closes with a candidate new/tightened
AD.

## Verdict

The spine's ADs are well-aimed at the failure modes they name, but four of
the eight ADs (AD-1, AD-5, AD-6, AD-7) specify a *rule* without specifying the
*shape* the rule's data/mechanism must take, which is exactly the gap two
independently-building units will fill differently; AD-5 x AD-7 also share an
unresolved foundational ambiguity (is dlt→dbt triggering 1:1 per-upload or
N:1 batched?) that undermines both simultaneously, and the Deferred section
contains one direct self-contradiction with SM-2 plus one item (OIDC pattern)
that is misclassified as "not architectural."

---

## 0. Foundational cross-cutting finding (underlies AD-5 and AD-7)

### F0 — Is dlt→dbt triggering 1:1-per-upload or N:1-batched/scheduled? [CRITICAL]

**The ambiguity:** FR-5 says `dbt-duckdb` runs "on a defined schedule/trigger."
AD-7 says "ingestion completion gates transform start via a sequenced
pipeline trigger." Nothing pins down cardinality. Two readings are both
letter-compliant:

- **Reading A (1:1):** every completed `dlt` load immediately and exclusively
  triggers its own `dbt run`, which transforms only that load's new Bronze
  rows. "Ingestion completion gates transform start" reads naturally as
  push-triggered, per-load.
- **Reading B (N:1 batched):** `dbt run` fires on an independent
  schedule/trigger (a cron cadence, or a poll) and each invocation transforms
  *all* Bronze rows accumulated since the last run — potentially from several
  uploads. "A defined schedule/trigger" (FR-5's actual words) reads naturally
  this way, and it's the more operationally realistic pattern (you don't
  normally spin up a full `dbt run` per single Excel upload in a
  regulated-enterprise batch pipeline).

**Two units, two builds:** the `apps/ingest/` owner, reading AD-7 literally,
builds a push-trigger: `dlt`'s pipeline-run success calls a "start transform"
hook per load (Reading A). The `apps/transform/` owner, reading FR-5
literally, builds a cron/schedule-triggered `dbt run` that transforms
whatever is new in Bronze at fire time, with no awareness of individual
upload boundaries (Reading B). Both are AD-7-literal ("ingestion completion
gates transform start" — B's cron only fires after checking no load is
in-progress, which still "gates" it; A's push is also a "sequenced pipeline
trigger"). Composed, you get **both** mechanisms live: a push-triggered
`dbt run` per upload *and* an independently-scheduled `dbt run` on a timer,
which is precisely the "invoke `dbt run` concurrently with an in-progress
`dlt` load" scenario AD-7 exists to prevent, arrived at by two individually
correct implementations.

This ambiguity is also the root cause of the AD-5 findings below: AD-5's
"passed to `dbt` via `--vars '{"trace_id": ...}'`" is a **single, run-scoped
value** — it only make sense under Reading A. Under Reading B it cannot
express per-row lineage at all, because one `dbt run` invocation now spans
many `upload_trace_id`s.

**Candidate AD:** *AD-9 — dlt→dbt triggering is 1:1: every successful `dlt`
load emits exactly one downstream `dbt run` scoped to that load's rows, via
[name the exact mechanism]; no independently-scheduled/cron-triggered `dbt
run` exists in v1.* (Or the converse, batched-N:1 resolution — but then AD-5
must be rewritten to require per-row `upload_trace_id` materialization, not
`--vars`; see F-AD5-2 below.)

---

## 1. AD-1 — Trust-boundary data shape at the WASI validation port

### F-AD1-1 — "primitive/record types" doesn't pin the row shape [HIGH]

**Rule text:** "accepts and returns only primitive/record types built from
strings, numbers, booleans, lists, and records — never a host-shared-memory
or buffer type."

**Two units:** the `apps/api/` owner (writes the Excel-bytes→rows parsing
code that constructs the WIT call arguments) and the `apps/validate-component/`
owner (authors the WIT interface + the componentize-py-generated Python
bindings the component's logic consumes).

- Builder A (api-side, working from the spine's data-shape rule alone) parses
  each Excel row into a **positional, typed** WIT shape:
  ```wit
  variant cell { s(string), n(float64), b(bool), null }
  record row { cells: list<cell> }
  ```
  columns identified by index, with a separately-communicated header/schema.
- Builder B (component-side, also working from the same rule) designs the WIT
  interface as a **named, stringly-typed** shape instead:
  ```wit
  record field { name: string, value: string }
  record row { fields: list<field> }
  ```
  with type coercion (parsing `"42"` → int, `"true"` → bool) done inside the
  sandboxed component logic.

Both are "primitive/record types built from strings, numbers, booleans,
lists, and records — never a host-shared-memory or buffer type," to the
letter. They are structurally incompatible: `componentize-py`-generated
Python bindings for shape A are indexed dataclasses with a `variant` union
type; bindings for shape B are `(name, value)` pairs with everything a
string. Whichever builder finishes second either can't compile against the
WIT the other one authored, or silently produces rows that are typed but
semantically empty (e.g., feeding stringified cells into shape-A's typed
variant slot, or vice versa). Note the Consistency Conventions table *does*
pin dates (ISO 8601 UTC at every stage boundary) but pins nothing else about
the row/cell shape — dates are the one accidentally-safe case, not evidence
the rest is safe.

**Also unpinned:** the **return** shape. AD-1 only constrains "primitive/
record types," and the Consistency Conventions table pins the *failure*
record (`{row_index, column, rule, message}`), but not how a partial-accept
result (UJ-1: "47 valid rows queued separately from 3 rejected ones") is
communicated back — one interleaved `list<row-result>` tagged by a
pass/fail variant, vs. two separate `list<row>` / `list<failure>` returns.
Builder A and Builder B could each pick either shape independently.

**Candidate AD:** *Tighten AD-1 to name the actual WIT record/variant
definitions verbatim (or point to a single `.wit` file as the sole source of
truth authored before either `apps/api/` or `apps/validate-component/` writes
call/binding code), covering: (a) row shape — positional-typed vs.
named-stringly-typed, (b) cell/value representation for each Excel scalar
type, (c) the passing-rows return shape, separate-lists vs. tagged single
list.*

---

## 2. AD-2 — Dependency-denylist enforcement is a build gate

### F-AD2-1 — "resolved dependency closure" is ambiguous between the pixi/conda lock and componentize-py's own bundled-Python manifest [HIGH]

**Rule text:** "runs a static-import-scan step against the validation
component's Python source and its resolved dependency closure."

**Two units:** the top-level `pixi.toml` build-gate owner and the
`apps/validate-component/` owner.

`componentize-py` does not run inside the host's normal pixi/conda
environment — it *bundles* a Python interpreter plus a wasm32-wasi-compatible
subset of the component's dependencies directly into the compiled `.wasm`
artifact, typically resolved from its own requirements/wheel set scoped to
what's WASI-buildable, which is not necessarily the same set of packages
(or even the same package versions) as the general pixi environment used to
run `pixi run build` itself.

- Builder A (pixi.toml owner) implements the scan as `pipdeptree`/`pixi
  list`-style walk of **`pixi.lock`** — "the resolved dependency closure" read
  as "the project's lockfile." This catches a denylisted package only if it's
  declared as a pixi/conda dependency anywhere in the main environment.
- Builder B (validate-component owner) feeds `componentize-py` a **separate,
  component-scoped requirements file** (necessary in practice, since most of
  the main pixi environment's packages are not wasm32-wasi buildable at all)
  — "the resolved dependency closure" read as "whatever componentize-py
  actually bundles into the .wasm."

If Builder A's gate only inspects `pixi.lock`, it never sees Builder B's
component-scoped requirements file at all — a denylisted transitive package
pulled in only through that file (e.g., a dependency of a dependency that
happens to import `pandas` for an optional feature) passes the gate cleanly
while still ending up inside the shipped `.wasm`. This is exactly the
build-gate-vs-real-artifact gap AD-2 exists to close, produced by two
letter-compliant readings of "resolved dependency closure."

**Candidate AD:** *Tighten AD-2 to name the exact scan target: either "the
manifest/lockfile that `componentize-py` itself consumes to bundle the
component" (and require that file to be the single source powering both the
component build and the denylist scan), or explicitly require the scan to
introspect the built `.wasm` artifact's actual bundled module list rather
than any pre-build manifest.*

---

## 3. AD-3 — No WASI sandboxing for `dlt` / `dbt-duckdb` / DuckDB

### F-AD3-1 — "conventional... processes/containers" doesn't pin one-container-per-stage vs. combined [LOW — folds into AD-7/F0]

AD-3 only forbids `wasm32-wasi` targets for these stages; it says nothing
about whether `dlt` and `dbt-duckdb` are packaged as one container/process or
two. This ambiguity by itself doesn't produce an incompatible *pair* under
AD-3 alone — it becomes concrete only combined with AD-7's sequencing
mechanism (see F-AD7-1/F0 above, where a single-combined-process assumption
and a two-separate-Jobs assumption produce genuinely incompatible triggering
designs). No standalone AD needed; folding the resolution into AD-7's
tightening (below) covers this.

---

## 4. AD-4 — The Isolation-Verification Gate must be non-hollow

### F-AD4-1 — the "meta-test" mechanism itself is unspecified: fixture-canary vs. live host-config mutation [MEDIUM]

**Rule text:** "must include a meta-test: deliberately widening the
component's declared WIT capabilities without a matching interface change
must make the gate fail."

**Two units:** whoever builds the gate harness (CI/`apps/validate-component`
test owner) and, separately, whoever maintains the WIT interface as it
evolves over the project's life.

- Mechanism A (**fixture-canary**): hand-author a second, permanently
  checked-in "canary" component — a real WIT file + component source with one
  extra capability (e.g. filesystem write) baked in, compiled once, stored as
  a fixture — and assert the gate flags *that* fixture. This proves the
  gate's assertion logic can detect a widened capability, but never proves it
  against the *actual current* production WIT/component, and the fixture
  silently rots (goes stale, or simply stops resembling the real interface)
  if nobody remembers to regenerate it whenever `apps/validate-component`'s
  real WIT changes.
- Mechanism B (**live host-config mutation**): take the real, current,
  production-compiled component, and at meta-test time instantiate it under
  a deliberately over-permissioned Wasmtime `Linker`/`WasiCtx` (grants a
  capability the WIT doesn't import), asserting the gate's detection logic
  fires. This always tracks the real component, but never proves a
  *recompiled* widened WIT/component would actually be caught — it only
  proves the harness's own assertion function isn't hollow when fed a
  wider grant directly.

Both satisfy "widening the component's declared WIT capabilities without a
matching interface change must make the gate fail" as literally written.
They test different things (the scanner-in-isolation vs. the
harness-against-a-mutated-real-artifact), have different rot properties, and
if two people build both independently (e.g., one as a "just to be safe"
addition on top of the other), the CI pipeline ends up with a
fixture that can silently stop tracking the real interface without either
meta-test noticing the drift.

**Candidate AD:** *Tighten AD-4 to require Mechanism B specifically (mutate
the real, currently-compiled production component's granted capabilities at
test time, not a separately-maintained canary fixture) — this is the only
version of the meta-test that cannot rot independently of the real WIT
interface.*

---

## 5. AD-5 — One trace-ID field, minted once

### F-AD5-1 — wire format of `upload_trace_id` is unspecified: full `traceparent` string vs. bare 32-hex trace-id, and hex vs. UUID-dashed in the OpenLineage facet [CRITICAL]

**Rule text:** "The W3C trace ID is minted at FastAPI ingress... stored as
`upload_trace_id`... passed to `dbt` via `--vars`... carried in every
OpenLineage run event's parent-run facet."

**Two units:** the `apps/api/`+`apps/ingest/` owner (mints/propagates the ID
into `dlt`) and the `apps/transform/` owner (consumes it via `--vars` and
emits it into dbt's OpenLineage facets).

- The W3C spec's `traceparent` header is `version-trace_id-parent_id-flags`;
  the bare "trace id" component is a 32-hex-char lowercase string. AD-5 never
  says which of these `upload_trace_id` *is*. Builder A (api/ingest side)
  could reasonably store the **full `traceparent` header string** (it's the
  literal W3C construct being "propagated"); Builder B (transform side),
  needing something to embed in a lineage-facet run identifier, could
  reasonably expect the **bare 32-hex trace-id**. If A passes the full
  header string into `--vars '{"trace_id": "00-<hex>-<hex>-01"}'` and B's dbt
  macros were written assuming a bare hex string, every downstream use of
  `trace_id` (building a lineage key, embedding it in a facet) embeds a
  different string than what's in the `dlt` load package's metadata —
  breaking the "single-lookup lineage reconstruction" AD-5 exists to
  guarantee, without either side violating the rule's text.
- Separately: OpenLineage's `ParentRunFacet` conventionally expects
  `run.runId` in **UUID format** (many OL backends, including Marquez,
  validate this). A W3C trace id is a 128-bit hex string with no dashes —
  syntactically *not* a UUID. Builder A's `dlt`-side OpenLineage emission
  could reformat the trace id into dashed UUID form to satisfy Marquez's
  schema; Builder B's `dbt`-side OpenLineage integration (e.g. passing the
  `--vars` string straight through, unmodified, into its parent-run facet)
  could emit the raw undashed hex. Marquez then receives two textually
  different parent-run-facet identifiers for "the same" trace from the two
  stages — "a single trace-ID lookup" (PRD SM-3) silently fails to correlate
  them, and nothing in AD-5's text says the string representation must be
  byte-identical across every emission point.

### F-AD5-2 — `--vars` is run-scoped; per-row lineage requires materializing `upload_trace_id` as an actual Bronze/Silver/Gold column, which AD-5 never requires [CRITICAL, inherits F0]

If dbt runs are batched across multiple uploads (Reading B in F0), a single
`--vars '{"trace_id": ...}'` value cannot correctly attribute per-row
lineage — dbt has one CLI-scoped value per invocation but is transforming
Bronze rows from several distinct uploads/trace-ids in that invocation. The
only correct fix is for `upload_trace_id` to be a real, SQL-selectable
**column** carried from Bronze through Silver into Gold (so each dbt model
attaches the correct per-row value to its own OpenLineage column-level
facet), not a single pipeline-run variable. AD-5's text ("passed to `dbt`
via `--vars`") reads as the *only* mechanism, and doesn't require column
materialization. A builder who takes AD-5 at face value (implements
`--vars` only, no Bronze column) produces a `dbt` project structurally
incapable of correct per-row lineage under batched execution, while fully
satisfying AD-5's literal text.

**Candidate AD:** *Tighten AD-5 to: (1) name `upload_trace_id`'s exact byte
representation — e.g. "the bare 32-hex-char W3C trace-id component, lowercase,
no dashes, no `traceparent` version/flags" — required verbatim at every
emission point (dlt load-package metadata, `--vars`, every OpenLineage
facet's runId field, reformatted to UUID-with-dashes only at the Marquez
API boundary if Marquez's schema requires it, and only there); (2) resolve F0
explicitly and, if batched/N:1 triggering is chosen, require `upload_trace_id`
to be materialized as an actual column from Bronze through Gold in addition
to (or instead of) the `--vars` mechanism.*

---

## 6. AD-6 — One securityContext, two consumers

### F-AD6-1 — "a generation step" doesn't require a *shared* generation step; two independently-authored translators satisfy the letter and can silently diverge per-field [HIGH]

**Rule text:** "Both the Helm chart values and the Podman compose file
consume it via a generation step; neither hand-authors its own copy."

**Two units:** the Helm-chart owner (`deploy/helm/`) and the Podman-compose
owner (`deploy/podman-compose/`).

Kubernetes `securityContext` and Podman/Compose's security fields are
*shaped completely differently* — there is no field-for-field analog:
`runAsUser: 1001` / `runAsNonRoot: true` / `readOnlyRootFilesystem: true` /
`allowPrivilegeEscalation: false` (K8s) vs. `user: "1001"` / `read_only:
true` / `security_opt: [no-new-privileges:true]` (Compose). Consuming the
canonical definition therefore *requires* a translation, not a pass-through,
for at least one of the two consumers. AD-6 says each consumer uses "a
generation step" (singular per consumer) but never says it must be the
*same* generation step/tool for both. Two builders can each honestly build
their own one-off translator: the Helm owner's "generation step" might be
nothing more than Helm's native `.Values` loading (since the canonical file,
if authored in K8s-shaped YAML, is directly Helm-consumable with zero
transformation), while the Compose owner's "generation step" is a bespoke
script mapping each K8s field to its Compose equivalent. Nothing ties these
two scripts together or tests that they stay in sync; the Compose owner's
translator can drop or mistranslate a field (e.g., forgetting
`no-new-privileges` entirely, or mapping `runAsNonRoot: true` to nothing
since Compose has no direct analog) while still fully satisfying "consume it
via a generation step" — reintroducing exactly the parity drift AD-6 exists
to prevent, silently, because nothing checks the two derived artifacts
against each other.

### F-AD6-2 — the canonical definition's own file format/toolchain is unpinned, creating first-mover lock-in [MEDIUM, folds into F-AD6-1]

AD-6 doesn't say what format the canonical `deploy/security-context/`
definition takes. If the Helm owner authors it first, the natural choice is
Helm-native YAML (possibly even Go-template-flavored, i.e. a Helm partial
directly usable by `helm template`) — which the Compose owner then cannot
consume without either running it through Helm's templating engine (a heavy,
odd dependency for a plain compose-generation script) or hand-parsing Helm
template syntax. If the Compose owner authors it first as flat data (e.g. a
`.env`-style KV file), the Helm owner now needs custom logic to lift flat KV
pairs into Helm's structured values schema. Whoever gets there first
implicitly privileges their own consumption path.

**Candidate AD:** *Tighten AD-6 to name: (1) the canonical file's exact
format — plain, engine-neutral data (e.g. JSON or plain YAML with no
Go-template syntax), not a Helm partial and not a Compose fragment; (2) a
single shared generation tool (one script/task, e.g. a `pixi run
gen-security-context` target) that emits *both* the Helm values fragment and
the Compose fragment from the one canonical source, with a test asserting
field-for-field equivalence (uid, read-only-root, no-privilege-escalation) —
not two independently-authored per-consumer translators.*

---

## 7. AD-7 — DuckDB single-writer serialization

### F-AD7-1 — "a sequenced pipeline trigger" underspecifies control-flow direction, deployment topology, and failure-handling; at least three incompatible-but-compliant mechanisms are constructible [CRITICAL, inherits F0]

**Rule text:** "Ingestion completion gates transform start via a sequenced
pipeline trigger. No scheduling path may invoke `dbt run` concurrently with
an in-progress `dlt` load against the same DuckDB file."

**Pair 1 — push (in-process, single-pod) vs. pull (cross-pod, Job/CronJob):**
Builder A (`apps/ingest/` owner) implements sequencing as an in-process
synchronous call chain — at the end of the `dlt` pipeline run, directly
invoke `dbt run` as the next line of code in the *same process/pod*. This
literally makes concurrent invocation impossible by construction ("gates" =
Python call order), and is AD-7-compliant. Builder B (`apps/transform/` or
`deploy/` owner, working from the `apps/ingest/` vs `apps/transform/`
structural split and FR-5's "defined schedule/trigger" language) implements
`dlt` and `dbt-duckdb` as *separate* Kubernetes `Job`s, with `dbt`'s Job
triggered by an out-of-process completion signal (a marker file on the
shared PVC, or a Job-succeeded event). Also AD-7-compliant. If both exist —
plausible, since nothing declares there is exactly *one* triggering
mechanism or names which side owns it — you get a push-triggered `dbt run`
*and* an independently-scheduled/event-triggered `dbt run` both live,
which is the concurrent-write scenario AD-7 forbids, assembled from two
individually-compliant pieces.

**Pair 2 — lock-as-safety-net vs. DAG-ordering-only (the prompt's own
example):** Builder C treats DuckDB's own single-writer file lock as the
*real* enforcement mechanism — the "sequenced pipeline trigger" is just an
optimization, and if two writers do race, DuckDB throws an IO/lock-contention
exception that the `dbt`-invocation wrapper catches and retries. Builder D
treats pure orchestrator DAG ordering (Task B `depends_on` Task A in
Argo/Tekton) as sufficient on its own and writes no lock-exception handling
at all, reasoning the DAG makes concurrent invocation structurally
impossible. Both satisfy "no scheduling path may invoke `dbt run`
concurrently... against the same DuckDB file" under their own model of what
"scheduling path" means. Composed: if the DAG is ever bypassed by a path
neither builder anticipated (a manual operator-triggered `dbt run` for a
backfill, a retry of a failed `dlt` load while an unrelated `dbt run` for an
earlier batch is still finishing — plausible if F0 resolves to N:1 batched
triggering), Builder D's dbt wrapper has no retry/backoff for the lock error
it never expected to see, producing spurious pipeline failures under
otherwise-normal timing; if instead Builder C assumed the DAG already
handles it and skipped adding the lock defense they were individually
responsible for, you get the true corruption AD-7 was written to prevent.

**Pair 3 — push-direction ownership:** even granting Pair 1's topology is
resolved, AD-7's "gates" language reads as *ingestion pushes the signal
forward*; FR-5's "defined schedule/trigger" reads as *transform pulls on its
own cadence*. An ingest-side builder implementing a push (e.g. an HTTP call
to a `/trigger-dbt-run` endpoint) and a transform-side builder implementing a
pull (a cron poller reading a watermark/marker file, with no such endpoint
ever built) produce two halves that don't even integrate — the push has
nowhere to land.

**Candidate AD:** *Tighten AD-7 to name the exact mechanism, not just the
outcome: (1) resolve F0 (1:1 push-per-load vs. N:1 scheduled/batched); (2)
name which side owns triggering (ingest pushes vs. transform pulls) and the
literal signal (e.g., "`dlt`'s post-load hook creates a Kubernetes `Job`
named `dbt-run-<load_id>`; no cron-triggered `dbt run` exists"); (3) require
DuckDB's own lock-contention error to be caught and retried by *whichever*
side invokes `dbt run`, as defense-in-depth *in addition to* — not instead
of — orchestrator-level ordering, so a bypass of the DAG (manual invocation,
a retry race) fails safe (retry) rather than either silently corrupting the
file or crashing without recovery.*

---

## 8. AD-8 — Air-gap-routable dependency fetch

### F-AD8-1 — "the configured channel/mirror" is treated as one thing; it is actually (at least) three unrelated configuration surfaces [HIGH]

**Rule text:** "Every build-time fetch (Pixi packages, DuckDB extensions, the
`componentize-py`/Wasmtime toolchain) routes through the configured
channel/mirror."

**Two units:** the top-level `pixi.toml` owner and the
`apps/validate-component/` owner (who needs the `componentize-py`/Wasmtime
toolchain specifically, and whose ingest/transform-adjacent code needs
DuckDB extensions).

These three fetch categories have three genuinely separate configuration
mechanisms with no shared knob: (1) Pixi/conda channel + PyPI index
configuration (`pixi.toml`'s `[pypi-config]`/channel-alias, or `.condarc`);
(2) DuckDB's own extension-repository setting (`SET
custom_extension_repository=...` / an env var, completely separate from
conda/pip config, since DuckDB fetches extensions via its own HTTP client at
`extensions.duckdb.org` by default); (3) `componentize-py`/Wasmtime's own
toolchain-download mechanism, which — being Bytecode Alliance tooling, not a
conda/pip package in the general case — may have no built-in mirror-config
knob at all and shell out directly to a fixed GitHub Releases URL. Builder A
(pixi.toml owner) wires up (1) globally and reasonably assumes "the
configured channel/mirror" is now a single project-wide setting everything
else will honor. Builder B (validate-component owner), actually integrating
DuckDB extensions and the componentize-py/Wasmtime toolchain, discovers
there is no such unified knob and hardcodes environment-specific env vars
for (2) and (3) directly inside `apps/validate-component/`'s own build
script — which is exactly the "build script that works today but breaks the
moment it runs behind an air-gapped mirror" failure AD-8 exists to prevent,
produced by a builder who never violated AD-8's text (they did route their
fetch "through the configured channel/mirror" — their own, locally
hardcoded one).

**Candidate AD:** *Tighten AD-8 to enumerate the three fetch subsystems
explicitly and require each to route through a named, single environment
variable or config file (not "the configured channel/mirror" as an implicit
singular), and require that config to propagate from `pixi.toml` down into
DuckDB's extension-repository setting and componentize-py/Wasmtime's
toolchain fetcher automatically (e.g., a `pixi run build` pre-step that
exports the mirror URL into whatever env vars (2) and (3) each require) —
mirroring `pyforge-atlas` G1's vendored-extension pattern as a mechanism, not
just a citation.*

---

## 9. Deferred section

### F-DEF-1 — CI trigger scope for the Isolation-Verification Gate directly contradicts PRD SM-2 [CRITICAL]

The Deferred section lists "CI trigger scope for the Isolation-Verification
Gate (every build vs. only validation-component-touching changes)" as an
open, un-decided question — "a CI-design question once a CI system is
chosen, not decided here." But the PRD's own primary success metric, **SM-2**,
already states: *"The Isolation-Verification Gate (FR-12) passes **on every
build**..."* This is a direct textual conflict, not a hypothetical one: SM-2
is a testable, primary, already-written commitment that answers exactly the
question the Deferred section claims is unresolved.

**Two units, right now, no CI system needed:** the `apps/validate-component/`
owner, reading SM-2 literally (and reading AD-2's "`pixi run build` runs a
static-import-scan step" as precedent for "verification steps live inside
`pixi run build` itself, unconditionally"), wires the isolation gate into
`pixi run build` so it runs on *every* invocation, repo-wide — matching
FR-14's "a clean checkout, `pixi install && pixi run build`, produces a
runnable digital twin with no manual steps" (which implies the compiled,
*verified* component every time, not conditionally). The CI/deploy owner,
reading the Deferred section literally and treating trigger-scope as an
open optimization question, adds a CI-workflow-level path filter (e.g. a
GitHub Actions `paths:` filter) that skips invoking the gate's `pixi run
build` target entirely on changes outside `apps/validate-component/` —
directly violating SM-2 ("passes on every build") the first time it fires,
while faithfully implementing what the Deferred section describes as still
open. This is not a future risk; the spine as written hands two builders
genuinely contradictory instructions today.

**Candidate AD:** *Promote this out of Deferred into AD-4 (or a new AD-10):
"The Isolation-Verification Gate runs unconditionally inside `pixi run
build`, on every invocation, with no CI-level path-filtering skip — per
SM-2." Remove the Deferred-section framing that implies this is still open,
or explicitly narrow SM-2 if a narrower scope is actually intended.*

### F-DEF-2 — OIDC "provider/library selection" is misclassified; the *authentication pattern* (embedded validation vs. delegated proxy) is architectural and unresolved right now [HIGH]

The Deferred section frames OIDC as purely a provider-name/library choice
("Keycloak / Red Hat SSO / other... Not a two-builders-diverge architectural
call; left to implementation"). That framing is correct for *which* IdP, but
it silently bundles in a second, genuinely architectural question the spine
never separates out: **where does token validation happen?**

**Two units:** the `apps/api/` owner and the `deploy/` (Helm chart / Podman
compose) owner.

- Pattern A (**embedded validation**): FastAPI itself holds an OIDC client
  library (e.g. `authlib`/`python-jose`), validates the `Authorization:
  Bearer <JWT>` header against the IdP's JWKS endpoint in-process, and is the
  literal thing returning HTTP 401.
- Pattern B (**delegated proxy**): an `oauth-proxy`/`oauth2-proxy` sidecar (or
  an OpenShift Route-level OAuth integration — which is exactly what UJ-1's
  entry state literally describes: *"authenticated via the enterprise OIDC
  provider (OpenShift identity)"*) sits in front of FastAPI, handles the OIDC
  flow itself, strips or replaces the `Authorization` header with trusted
  identity headers, and returns 401/redirects *before FastAPI's process is
  ever reached*.

Both satisfy FR-1's testable consequences ("unauthenticated requests receive
HTTP 401 before the upload body is read" — Pattern B satisfies this even
more literally, since the body never reaches the app at all) and the
Consistency Convention ("Auth is OIDC-only at the API ingress... no stage
downstream of the API re-authenticates"). If the `apps/api/` owner builds
Pattern A (writes JWT-validation middleware expecting a raw bearer token)
while the `deploy/` owner builds Pattern B (wires an auth-proxy sidecar into
the Helm chart/Compose file that consumes and discards the raw token,
forwarding only trusted headers), FastAPI's validation middleware never
receives a token to validate — it's either dead code or double-authenticates
against headers it wasn't written to trust. This divergence is fully
independent of which IdP is eventually named, so it should not ride along
with the correctly-deferred provider/library choice.

**Candidate AD:** *Add a new AD pinning the authentication pattern
specifically — e.g. "AD-9 (or renumber): OIDC token validation happens
in-process in `apps/api/`; no auth-delegating sidecar/proxy sits in front of
it" (or the converse, proxy-delegated, if that's the intended reading of
UJ-1's "OpenShift identity" framing) — leaving only the IdP
name/library choice genuinely deferred.*

### F-DEF-3 — `componentize-py`'s dynamic-import restriction's effect on validation-rule config: rule-identifier registry ownership is unresolved now, not just for a hypothetical future dynamic-loading story [MEDIUM]

FR-2 requires concrete, named validation rules *today* (UJ-1: "no negative
headcounts, no duplicate department keys"; FR-3: error reports "name the
specific column/rule that failed"). Given `componentize-py`'s build-time-only
import constraint, two compliant-but-divergent encodings exist: (a)
hardcoded Python conditionals compiled directly into the component (rule
names exist only as scattered string literals, no external registry), vs.
(b) a static, build-time-bundled data file (JSON/YAML) of rule definitions
read by a generic rule-evaluation engine inside the component (rule names
exist as a discoverable manifest). Both are build-time-resolvable, satisfying
the constraint. If `apps/api/` (or the error-surfacing/consistency-convention
owner) assumes rule identifiers are drawn from a shared, externally-readable
manifest — e.g. to validate that a `rule` value in an error response is a
known identifier — while `apps/validate-component/` went with (a), there is
no such manifest to read. The Deferred framing ("deferred to the story that
first hits it") treats this as a future problem, but the encoding choice has
to be made in v1 to satisfy FR-2 at all.

**Candidate AD:** *Tighten (don't defer) this into AD-2's neighborhood: rule
definitions live in a single static, build-time-bundled manifest (not
scattered code conditionals), and the `rule` identifier space in that
manifest is the canonical source `apps/api/`'s error-surfacing code (and any
future admin/introspection surface) must read from.*

### F-DEF-4 — Marquez version drift could break OpenLineage schema compatibility between dlt-side and dbt-side emitters [LOW-MEDIUM]

Stack table already flags Marquez's last tagged release (0.50.0, 2024-10-24)
as stale against actively-pushed `main` (through 2026-07-23) and defers
resolving the actual deployed version. Worth noting explicitly (not just as
a "verify the tag" task): if the `openlineage-python` client code used by
`dlt`/`dbt`'s emitters is developed/tested against the OpenLineage spec
version implied by the stale 0.50.0-era Marquez, while whatever gets
actually deployed is materially newer, facet-schema fields the two sides
assume can drift out of sync (a real but narrower version of F-AD5-1's
formatting risk). No new AD needed beyond executing the existing Deferred
item promptly and pinning the OpenLineage spec version explicitly (not just
the Marquez image tag) once resolved.

### F-DEF-5 — remaining Deferred items are correctly deferred [no risk / informational]

Exact latency/file-size budgets, named regulatory framework, operational
SLA/RTO-RPO, data retention policy, and the `dbt Fusion`/browser-dashboard
watch items do not, on inspection, admit a *right-now* two-builder
incompatibility: each either blocks no code path yet (no retention job is
architected at all, so there's nothing for two builders to diverge on) or is
a pure parameter/tuning value that doesn't change either builder's
structural design once picked. These are appropriately left in Deferred.

---

## Summary table

| Finding | ADs/Deferred item touched | Severity |
| --- | --- | --- |
| F0 — dlt→dbt triggering cardinality (1:1 vs N:1) unresolved | AD-5, AD-7, FR-5 | Critical |
| F-AD5-1 — `upload_trace_id` wire format unspecified (traceparent vs bare hex; hex vs UUID-dashed) | AD-5 | Critical |
| F-AD5-2 — `--vars` is run-scoped; per-row lineage needs a Bronze/Silver/Gold column | AD-5 | Critical |
| F-AD7-1 — "sequenced pipeline trigger" mechanism unpinned (push/pull, topology, lock-vs-DAG) | AD-7 | Critical |
| F-DEF-1 — CI trigger scope for isolation gate contradicts SM-2 | Deferred | Critical |
| F-DEF-2 — OIDC embedded-validation vs. delegated-proxy pattern misclassified as non-architectural | Deferred | High |
| F-AD1-1 — WIT row/cell/return shape unpinned | AD-1 | High |
| F-AD6-1 — two independent hand-rolled securityContext generation scripts | AD-6 | High |
| F-AD2-1 — "resolved dependency closure" ambiguous (pixi.lock vs componentize-py's bundle manifest) | AD-2 | High |
| F-AD8-1 — "the configured channel/mirror" conflates three unrelated fetch subsystems | AD-8 | High |
| F-AD6-2 — canonical securityContext file format/toolchain unpinned (first-mover lock-in) | AD-6 | Medium |
| F-AD4-1 — non-hollow meta-test mechanism unpinned (fixture-canary vs live host-config mutation) | AD-4 | Medium |
| F-DEF-3 — validation-rule identifier registry ownership unresolved now | Deferred | Medium |
| F-DEF-4 — Marquez version drift risks OpenLineage schema mismatch | Deferred | Low-Medium |
| F-AD3-1 — container/process granularity for dlt/dbt (subsumed by F-AD7-1) | AD-3 | Low |
| F-DEF-5 — remaining Deferred items correctly deferred | Deferred | None |
