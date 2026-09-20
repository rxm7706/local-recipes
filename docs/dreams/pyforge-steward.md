---
title: Steward — provision the line, hold the keys
type: dream
owner: steward
status: specified
---

# Steward — the estate the factory stands on

## The Dream

The Provisioner's dream: **nothing the factory needs is missing, and nothing it
no longer needs stays privileged.** Mason ships artifacts and stops at the
registry; Doctor observes and prescribes; the Steward *deploys, provisions, and
operates* — environments and runners, service deployments, credential and
privilege lifecycles, resource budgets, and the incident response when the pager
goes off. Adopted 2026-07-23 when the ownership audit found Deployment &
Operations — the Implementation view's own stage, and the home of Privilege
Drift — orphaned between stations.

## What it owns

- **Provisioning**: bmad-loop runners, CI images, pixi environments — engines
  present before [[pyforge-doctor]]'s pre-flight ever runs.
- **Deployment**: services, not just artifacts — the Pages program console,
  [[presenton-pixi-image]] on OpenShift, [[enterprise-airgap]] bundle installs.
- **Keys**: credential issuance, scoping, rotation, revocation. First case on
  the desk: the `JFROG_API_KEY` unconditional-injection leak (Doctor finds,
  Steward remediates).
- **Budgets**: machine-readable resource ceilings ("locked at $1500/month") and
  their enforcement — the Taxonomy view's resource governance, operationalized.

## What is already Steward-shaped

- The Pages dashboard deploys (today: hand-run `dashboard-gen` + push — a
  Steward duty done manually).
- The pixi environment estate + `environment.yaml` sync discipline.
- The air-gap routing machinery ([[enterprise-airgap]]) awaiting an operator.

## Realization log

- **2026-07-23** — persona adopted into [[pyforge-charter]] (crew 6 → 8);
  naming disambiguated from the [[fleet-stewardship]] practice Dream. CLI and
  chapter deck await their turns.

- **2026-09-16 — The Guild environment: a minimal default for every agent
  and every harness (Dream-append-first; → `spec-pyforge-steward` CAP-5).**
  `local-recipes` was the right default when this repo was a recipe factory and
  nothing else. It is now 222 conda deps, 171 tasks and 10 GB on disk — and
  every agent (Claude, Cursor, Copilot, Gemini, a Cursor Cloud Agent in
  RXM-LOCAL-RECIPES, Marshal itself) is told to run the planning chain through
  it, so a cold cloud environment pays for grayskull, conda-smithy, the CFE
  atlas stack and the vulnerability databases to run `detectors-ci`. Measured
  today: of the 171 tasks, **48 are Guild/planning work** (the detectors, the
  ledger sync, the surface stamps, fleet-picture, the three preflight
  aggregates) and their scripts import exactly `pyforge.*`, `yaml`, `tomli`
  and `pixi_version_registry`; **86 are recipe-factory** (Mason's, they stay).
  The aspiration: **one small environment — `pyforge-guild` — that carries the
  current state of PyForge (core, doctor + its warden/testing-kit seam,
  marshal, steward) and nothing of the factory**, installs in under a minute
  from cold, is what `AGENTS.md`, `CLAUDE.md`, the Cursor rules, the station
  `SKILL.md`s and the cloud environment name as the default, and is the shape
  the foundry inherits (mode `rebuild`: B re-derives it from the same feature
  split). `local-recipes` keeps its name and every task by *including* the new
  feature, so nothing already written breaks; it becomes Mason's environment
  in fact, as it already is in practice. Scribe recall stays `-e pyforge-scribe`
  (cocoindex + graphify are heavy and already per-env). Kinships:
  [[marshal-token-economy]] (a cold 10 GB install is the largest fixed cost a
  cloud session pays before its first token), [[foundry-regenerate-not-fold]],
  [[pyforge-unifying-strategy]].

- **2026-09-16 — Frame draft re-grounding at `d7213c1` / `4596579`
  (Dream-append-first; → `spec-pyforge-steward` CAP-6; Frames remain
  [[intelligence-hub]] CAP-2's subject).** We adopted the frame-spec v0.3
  working draft on 09-14 from the head of openteams-ai/frame-spec#28. Since
  then #28 gained a 09-14 commit — *the draft carries no version number until
  a release assigns one*; its examples now read bare `type: frame` — and #29
  (81 commits, `spec/v0.3-validator`) landed a reference validator with
  composition fixtures, a `--self-check` that proves the draft agrees with its
  own element table, and **conformance profiles**, which §7 now makes a MUST
  for every implementation. Measured today, read-only: upstream's own
  `validate_frame.py` at #29's head passes all nine of our Frames (9/9, one
  INFO per station: `pyforge/company` is a qualified-ref), and `--self-check`
  passes the draft. So the adoption holds; what moves is *how we claim it*:
  (1) our `type: frame [0.3]` stamps a version that does not exist — we go
  bare, and the draft head we conform to is recorded as a **pin** in
  `docs/foundry/frames/README.md`, re-pinned by a memlog line whenever we
  re-ground; (2) PyForge's reader must **publish a conformance profile**
  (`docs/foundry/frames/conformance-profile.yaml`, the #29 YAML shape, checked
  by `--check-profile`) — today it reads Markdown only and resolves no
  composition, and says so; (3) §9 Security Considerations now bind the loader
  we have not built: a Frame is instructions, the source MUST be recorded
  beside the content, an untrusted source MUST NOT be loaded, and
  trust-every-source MUST be declared in the profile — these become
  acceptance criteria on the future Frame-into-agent-context work under
  [[marshal-token-economy]] `[context.wire]`, not an afterthought; (4) #29's
  composition fixtures (dedup keeps first, empty ≠ absent, style-clear) are
  the conformance tests for the day we compose station Frames with the Company
  Frame. Posture unchanged: we operate as if the current heads become v0.3;
  **no commits or comments to openteams-ai** — the validator is fetched to a
  temp dir at the pinned SHA by an opt-in task and never vendored. #28 stands
  at `CHANGES_REQUESTED`, 39 commits, mergeable, no LICENSE on `main` yet; the
  accepted-risk ledger entry stays open with today's date.
- **2026-09-20 (later) — Only `pyforge-guild` exists at runtime; the fleet's whole closure is one
  locked artifact.** Operator rulings 10:10Z–10:30Z, on the day's first fresh-worktree failure
  (steward's adoption-register probe found `eval-quality` only because the primary checkout
  happened to have the 10 GB `local-recipes` env on disk): (1) `local-recipes` is the recipe
  factory, not a runtime — "only pyforge-guild, the bare minimum and default pixi environment,
  will be available at runtime"; station code that shells to `-e local-recipes` or reads
  `.pixi/envs/local-recipes/...` is a bug (audit 2026-09-20: marshal `cli/watch.py`, `core/gate.py`,
  `adapters/scribe_cli.py`; herald `deck_pipeline.py`, `sync_all.py`; steward `provision.py`,
  `upgrade.py`, `suite.py`; the shelled tasks — `bmad-loop`, `deck-export`, `deck-facts`,
  `deck-trio`, `platform-ci-local`, `wasm-build` — and the bmad-builder skill share dir must be
  reachable from `pyforge-guild`); (2) a station's own env carries what its code wields
  (`bmad-eval-quality` now pinned in `pyforge-steward`); (3) a new environment,
  **`pyforge-foundry-full`**, is the union of every PyForge feature — never the runtime, never
  installed by default — so the ecosystem's full, real dependency closure is one solved, locked,
  checkable artifact. The first union solve paid for itself: mason's `python-build <1.6` window
  could not co-resolve with the `>=1.6.0` floors four features pin, and warden's `py-rattler
  >=0.26.0` (a catalog-sync bump) blocked conda's rattler-solver variant — both fixed, and (4)
  "never cap without a reason": mason's engine ranges are floors now (its Spec's one-minor-window
  boundary amended by ruling). A pixi 0.81.0 bump was attempted the same hour and reverted:
  conda-forge's `pixi` package is still 0.80.0 on every platform, and an in-env pixi below
  `requires-pixi` refuses the manifest — retry with `bump-pixi-version -- 0.81.0` once
  `pixi search pixi` shows 0.81.0 (18 registry sites now; `docsite-check.yml` was unregistered).
  → CAP-151 / Story 63.5 (the union env + the steward pin, hand-driven the same day) and CAP-152 /
  Story 63.6 (no station code assumes `local-recipes`: the shelled tasks move into `guild-tasks`
  with their deps in `pyforge-guild`, a meta-test reds the pattern in every station's `src/`;
  marshal 46.12 and herald 25.1 own their shell-outs).
- **2026-09-20 — Proposed: the ledger query answers "what is done, what is running, what is
  next" in one call.** Asked at 08:00Z on the third drain: "the full list of epics and
  stories by station, with what's completed, running and queued next." Today that is three
  commands and a hand-written script: `fleet-picture` (totals), `sprint-ledger-query`
  (every story's status) and `marshal watch --fleet` (what is live, per dispatch clone) —
  and *queued next* (a `backlog` story whose `Deps:` are all `done`) is a column nowhere,
  though 65.1 already ships the logic as `get_runnable_backlog()` for Marshal. The ask: a
  `next` field on every story — `done` / `running` / `ready` / `waits on S-x.y` / `blocked`
  — with `--ready` and `--running` filters, per-station ready/running counts in the
  summary, and the `running` fact taken from marshal's own CLI (`marshal watch --fleet
  --format json`, correct since marshal 51.10–51.13 tonight), never from steward parsing
  marshal's journal; when marshal is unreachable the column reads `?` with one WARN, fail-open.
  Owner: steward (the engine is CAP-146..149's). → CAP-150 / Story 65.2, the next steward slot.
- **2026-09-19 — Proposed and shipped the same day (PR #1507, a parallel session): the
  estate sprint-ledger query engine.** One engine (`pyforge.steward.sprint_ledger_query`)
  over every station's TRACKED `sprint-status-ledger.yaml` + `epics.md` — presets and
  station / epic / status / text filters; registered formatters, sources and hooks; flags
  from `flags.json` / env / CLI gating every optional export; ten output shapes (people,
  `bmad-dashboard` JSON with a shipped schema, Herald's facts-ledger shape, an Atlas
  dataset payload, Jira CSV, GitHub Projects V2 mutations, `get_runnable_backlog()` for
  Marshal); a `WorkPassport` Django model with a minted UUID and tracker keys as aliases;
  three front doors (`steward ledger-query`, two pixi tasks, the `bmad-sprint-ledger-query`
  skill). The session had minted it as a standalone Dream + Spec under
  `fold-exemption: cross-station-seam`; folded here on review (one-chain-per-station — that
  token is for the kernel/testing-kit seams every station imports): this entry is the seed,
  `spec-pyforge-steward` carries CAP-146..149 (the derivation record is a note on its
  memlog), and the passport slice binds to CAP-140 with Story 61.2 still the story of
  record (no `vendor_id`, not the existing join store, 61.1's corridor not landed). The
  standalone `sprint-ledger-query-module.md` + `spec-sprint-ledger-query-module/` pair was
  removed rather than archived in place — `chain-sprawl` reads no status, so a post-ruling
  pair is a finding forever; the detector's own remedy is exactly this entry + the CAPs
  (the sketch survives in git at `c01fdb3f4d`). Story 65.1 (Epic 65; the `63-5` key the
  session used never reached `main`). The review (three layers) found the runnable-backlog
  helper ignoring the repo's Deps grammar, all 237 epics reported in-progress, flags never
  wired, `--sync-postgres` unable to succeed yet reporting ok, unescaped HTML in the HTMX
  view and dossier, a stock admin on the append-only audit trail, a sync pixi task
  registered where no env has django — remediated before merge; the rest is DW-FU-65-1..3.

## 2026-09-17 — One-chain fold (steward, CAP-3)

Steward rebases to one Dream, one Spec, one PRD, one spine, one epic chain. Folded topic Dreams are archived in place with `Consolidated into [[pyforge-steward]]` banners. Exempted chains (Guild unifying-strategy; foundry regenerate / capability-ledger / cutover) keep their folders with `fold-exemption`.

## 2026-09-17 — Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other (folded from asgi-multiplexer-monolith)

# Django, Langflow, and DB-GPT co-locate in one ASGI process without starving each other

## The Dream

The sibling [[langflow-django-plugin]] and [[db-gpt-django-plugin]] Dreams
each describe integrating ONE agentic LLM tool into Django, with
microservice separation as one of their named options. This Dream is the
more aggressive third path: fold ALL THREE — Django (serving a React UI),
Langflow, and DB-GPT — into a SINGLE Python process on a shared ASGI event
loop, trading the network hop and container boundary away entirely for the
lowest possible latency between the web layer and both AI engines. That
trade is only worth taking if the process can actually survive hosting
three frameworks with conflicting dependency trees (FastAPI, SQLAlchemy,
Pydantic across all three) and wildly different execution models (Django's
async-first web serving vs. Langflow/DB-GPT's synchronous LLM inference)
without one starving the others or the whole thing becoming unmaintainable
dependency archaeology.

## What it looks like when real

**Ingress & routing — one ASGI multiplexer, not three servers behind a
proxy.** `config/asgi.py` instantiates all three applications in-process
(`get_asgi_application()`, `create_langflow_app()`, `create_dbgpt_app()`)
and a master async function inspects `scope["path"]` on every incoming
request to hand execution to the right one: `/api/v1/`, `/health`,
`/langflow` → Langflow; `/api/dbgpt/` (prefix stripped) → DB-GPT; anything
else → Django. No Docker-level reverse proxy — routing happens inside the
one process.

**Dependency resolution — a real, solved manifest, not a hope.** Standard
package managers fail outright on three frameworks' conflicting
requirements; realized means an actual environment manifest exists that
strictly pins the lowest common denominator for every shared core library
(e.g., Pydantic — whichever major version both Langflow and DB-GPT can
actually agree to run under), verified to solve, not asserted.

**Statelessness — DB-GPT's filesystem habit is fully disabled, not
partially.** Same rule as the [[db-gpt-django-plugin]] Dream: every local
session-state path DB-GPT would default to must be overridden at runtime,
before the DB-GPT application factory is ever called, forcing all state
into PostgreSQL's `dbgpt_schema`.

**Blocking isolation — the event loop never stalls on an LLM call.**
DB-GPT and Langflow both run synchronous inference that would otherwise
block Django's async event loop and starve ordinary HTTP responses to the
React UI; realized means the ASGI server's thread pool is sized
deliberately (not left at a framework default) so a slow inference never
means a stalled page load.

**Data layer — one PostgreSQL database, three schemas, one owner each.**
`public` (Django), `langflow_schema` (Langflow), `dbgpt_schema` (DB-GPT) —
the same three-schema split the two sibling Dreams each describe on their
own, now co-existing in the same database because all three frameworks
are, for the first time, genuinely in the same process.

## Constraints

- **This is NOT a superset of the sibling Dreams — it is a distinct,
  harder option**, only worth choosing when the latency win from
  same-process execution outweighs the real cost: a much larger blast
  radius (one crashing framework can take the other two down with it,
  where separate containers would not) and a dependency-resolution problem
  that may simply be infeasible for a given trio of versions.
- **Thread-pool sizing is a load-bearing tuning decision, not a constant to
  copy-paste.** An under-sized pool starves the UI; an over-sized one
  invites its own resource-exhaustion failure mode. Whatever value is
  chosen needs to be justified against real measured inference latency,
  not picked once and forgotten.
- **Package sourcing inherits DB-GPT's own constraint** from the
  [[db-gpt-django-plugin]] Dream: its dependency chain is sourced from the
  Conda Enterprise Core repository specifically, for controlled,
  enterprise-compliant pinning — this monolith's dependency-matrix
  resolution has to reconcile against that source, not generic PyPI/
  conda-forge.
- **Statelessness and schema-isolation constraints are inherited
  verbatim** from both sibling Dreams — nothing about running all three in
  one process relaxes either rule; if anything, sharing one process makes
  a state leak between the three harder to detect, not easier.
- Environment surface named: `ANYIO_MAX_THREADS` (or equivalent — prevents
  ASGI event-loop blocking), `LANGFLOW_DATABASE_URL` and
  `DBGPT_DATABASE_URL` (each carrying its own `search_path` schema
  isolation), `DBGPT_SESSION_STORAGE_TYPE=db`.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied
  architecture brief, immediately after the sibling
  [[langflow-django-plugin]] and [[db-gpt-django-plugin]] Dreams — this one
  is their more aggressive "all three, one process" variant rather than a
  fourth independent pattern. Not yet researched against this repo's own
  factory or any specific downstream project — no station claimed, no
  Spec derived, dependency-matrix feasibility unverified. Owner
  deliberately left as `guild` (intake, not a terminal owner) pending a
  decision on which project or station this belongs to, and pending
  confirmation that the underlying dependency conflict is even solvable
  before committing engineering time to it.
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Dependency-solve spike PASSED (conda-native).** Operator-requested feasibility gate run via `micromamba create --dry-run -c conda-forge langflow dbgpt dbgpt-serve "django>=5" python=3.12`: solves cleanly — 373 packages, one environment: langflow 1.11.2 + dbgpt/dbgpt-serve 0.8.1 + django 5.2.15 agreeing on pydantic 2.13.4 / sqlalchemy 2.0.52 / fastapi 0.141.1. Both engines are now conda-forge packages this factory itself shipped (langflow-feedstock pushed 2026-08-13, db-gpt-feedstock 2026-07-22), so the co-install premise is verified-to-solve, not asserted — the monolith is a live option and neither sibling wins by default. The pair choice is now a deliberate decision awaiting the family's last precondition: a named subject project. **Python-3.14 lane (operator constraint, same day: everything must be 3.14-compatible): FAILS today** — `langflow-base` pins `bcrypt ==4.0.1` (langflow-feedstock recipe line 198, upstream's passlib-compat pin) and no py3.14 build of that bcrypt exists, while `dbgpt`+`dbgpt-serve`+`django>=5` alone solve clean on 3.14 (61 pkgs). The family's sole 3.14 blocker is that one exact pin; remedy is upstream langflow dropping the passlib-era pin or a runtime-validated feedstock loosening — tracked as a langflow-feedstock maintenance item. **Infrastructure constraint (operator, same day): core infrastructure is exactly PostgreSQL + Redis + a Kubernetes container platform (Red Hat OCP or Google GCP/GKE, Docker/Podman images) — nothing else.** This fits the family's existing shape (one PostgreSQL with public/langflow_schema/dbgpt_schema; Redis as the Celery broker; hard statelessness now mandatory since pods are ephemeral — pgvector inside the same PostgreSQL if DB-GPT needs a vector store, no separate one), and shifts the deployment mechanism from Compose/Traefik to K8s ingress/OCP routes at Spec time. It tilts the pair choice toward the microservices topology (per-service pods behind one ingress; replicas = capacity; the in-process co-location the monolith trades for is worth less when in-cluster networking is the platform norm) — the monolith stays viable only as a single-container deployment. Final pair choice still deferred to Spec intake with the named subject project.
- **2026-08-14** — **Operator architecture direction (same day, supersedes the open pair framing):** all components build on and integrate into ONE Django service — cookiecutter-django based, WITH FastAPI integration — grounded in [[django-accelerator-framework]]; the engines integrate **preferably as pluggable Django applications** ([[langflow-django-plugin]] / [[db-gpt-django-plugin]] Pattern-A shapes: ASGI mount + schema isolation), deployed on the PostgreSQL + Redis + Kubernetes platform recorded above. Scaling = replicating the whole service (statelessness mandatory); a per-engine sidecar container remains the fallback ONLY where pluggability fails (dependency or lifecycle isolation). Remaining precondition before Spec intake: naming the subject project.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-09-09** — **Fleet readiness pass, realization gate** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C10). The Pattern-A/B integration, schema split and statelessness criteria are exercised in the running estate (`src/platform/config/engine_patterns.py`, `config/settings/base.py:172-175`, `config/estate_dsn.py`). **One named criterion is not:** "the ASGI server's thread pool is sized deliberately (not left at a framework default)" — there is no `ANYIO_MAX_THREADS` or any thread-pool sizing anywhere in `src/platform/`. The residue is recorded (`spec-local-ocp-hybrid-environment/reconciliation-and-corrections.md:41`, `.memlog.md:15`) but had **no story and no ledger key**; it now lands as an acceptance clause on steward **Story 48.2** (R-18 sizing), whose Surface was chart-only. Status stays `realized`.

## 2026-09-17 — bmad-eval-quality — prove the reviewer catches the planted bug (folded from bmad-eval-quality)

# bmad-eval-quality — prove the reviewer catches the planted bug

## The Dream

The factory runs unattended. Every story that lands through a bmad-loop run passes exactly one
safety net: the independent reviewer, because `gate_mode = "none"` switched the human approval
gate off and left the reviewer as the last line. Nothing measures whether that reviewer would
actually catch a real defect. Every other quality surface in the repo is either deterministic (the
~30 `*-check` detectors, pyforge-doctor's sources, the CFE meta tests) or an LLM review whose
strength has never been proven. The repo's own memory records the failure class: detectors that
fail open when GitHub rate-limits them, a false-fact `[reject]` that hides a finding forever, a
fork that ignored review scope.

`eval-quality` ([bmad-code-org/bmad-eval-quality](https://github.com/bmad-code-org/bmad-eval-quality))
is the tool for that gap. It compiles and scores *Behavioral Evaluation Contracts* — versioned JSON
declaring which behaviors to probe, what evidence counts, and the pass/fail oracles — and its one
idea is the **twin-run loop**: run the same contract against a clean system and against one with a
single planted defect; a strong contract passes clean and fails mutated. It executes nothing
itself. Our harness runs the system under test and hands over observations and a sealed run
record; the tool grades the *evaluation*, not the system.

The dream: `bmad-eval-quality` is the fourteenth member of the bmad-suite, installed the suite's
way, and a first contract proves — with a planted `file:line` defect and a catch rate, not a
feeling — that the review layer bmad-loop relies on actually looks.

## Grounding — verified state (2026-09-05 research pass)

Upstream (checked against the tagged and main sources, not memory):

- npm `latest` is 0.1.0 (2026-08-28), the only git tag (`v0.1.0` = `65c6b808`; npm's `gitHead` is
  that same commit). It ships `compile`, `seal`, `preflight` — **no `score`**.
- Scoring (`score`, `runScore`, the `ingest` stage) and nine breaking schema-version bumps sit on
  unreleased main: package.json 0.2.0, HEAD `3172162fbdc7c4bb70ed11c1367dc3e433797535`
  (2026-09-04, the commit wiring the publish action). No runtime version checking — exact pinning
  required.
- `schemas/eval-contract.schema.json`: `permittedInterfaces[].kind` admits api/web/cli/mcp but
  "v0 supports `api`; the other three fail compilation". The shipped `examples/bmad-tea-contract.json`
  (kind cli, 7 of 21 fields) is illustrative and will not compile. Every contract models its SUT as
  an HTTP-shaped operation; the driver is the adapter.
- A contract has 21 required top-level fields; `corpus/dev/contracts/satisfied-declarations.json`
  is the canonical complete example.
- TypeScript with `dist/` gitignored; `prepack` runs `clean && build` (`tsc -p tsconfig-build.json`).
  Node ≥22.20, one prod dep (`zod`), Apache-2.0.
- TEA (`bmad-method-test-architecture-enterprise`) is the reference authoring client; eval-quality
  knows nothing about BMad. TEA is pinned in this repo's pixi but not installed as a module.

In-repo:

- No `evals/` directory and no skill-eval harness exists anywhere; `claude plugin eval` is
  referenced nowhere.
- bmad-loop's review session is `/bmad-build-auto` re-invoked on a `done` spec
  (`bmad_loop/engine.py`), routed to `step-04-review.md`; its findings are prose. The only
  JSON-emitting reviewer surface is the layer prompt
  `.claude/skills/bmad-build-auto/review-prompts/edge-case-hunter.md` ("Return ONLY a valid JSON
  array", `location` = `file:line`), byte-identical to the `bmad-code-review` copy.
- Suite membership is single-sourced at `recipes/bmad-suite/suite-members.yaml` (13 active); it
  feeds the metapackage run deps, pyforge-doctor's watched set (`_SUITE_PREFIX = "bmad-"` and
  `_manifest_suite_members`), and steward's pipeline-truth check. 12 of 13 members source from
  GitHub archives; six are commit-pinned with the `X.Y.Z.dev0 @ <sha>` encoding (G109).
- `tests/packaging/test_bmad_suite_full_feature.py:31-43` freezes the `bmad*` pin set as a
  metapackage-story guard against accidental pins.
- pixi already carries `nodejs >=24.19`; Node is not a blocker.

## Decisions locked (operator, 2026-09-05)

- **Conda name `bmad-eval-quality`.** Suite members carry the `bmad-` prefix after the upstream
  repo name even when the registry name lacks it (`bmad-labs-skills` ↔ `bmad-labs/skills`). The
  bin stays `eval-quality`. The frozen pin baseline gets the new name in the same PR; it is a
  guard, not a naming rule.
- **Source = GitHub main, commit-pinned `0.2.0.dev0 @ 3172162f`.** Rejected: npm 0.1.0 and tag
  v0.1.0 (same commit, no `score`, schema v1 already superseded — every contract authored against
  it would be rewritten at 0.2.0 anyway). The commit pin cannot move; a schema mismatch fails
  `compile` loudly. Flip to tag-mode the day `v0.2.0` lands (`0.1.0 < 0.2.0.dev0 < 0.2.0`).

## What it looks like when real

**Suite membership (CAP-1).** `recipes/bmad-eval-quality/recipe.yaml` in the labs-skills /
manticore encoding (`context.version: "0.2.0.dev0"`, `context.commit`, source = the commit
archive), built through `conda-forge-expert`: `npm ci` → `npm pack` (the tarball is named from
package.json, `eval-quality-0.2.0.tgz`, not from the conda version) → `npm install -g` →
`pnpm-licenses`; per-arch, `nodejs >=22.20.0` floor only. Tests prove the decision held:
`eval-quality --version` prints `0.2.0`, `--help` lists `score`, and `compile` on the shipped
corpus example exits 0. One line in `suite-members.yaml` auto-enrolls it in the metapackage,
doctor's drift watch, and steward's pipeline-truth; the pixi pin
`bmad-eval-quality = ">=0.2.0.dev0"`, the baseline set extended, an install-matrix row with its
hazards, steward's install-class tables and `library-llms-full.md` each gaining a row,
`environment.yaml` regenerated, the `maintenance` label on the PR. Published to SelfExplainML
through the existing channel pipeline.

**The pilot contract (CAP-2).** `evals/review-catches-planted-defect/` holds a tiny fixture
package, `arms/clean.diff` and `arms/mutated.diff` (one boundary flip, e.g. `>=` → `>` at
`pkg/discount.py:17`), the contract with interface `review-api` / operation `review-diff`
(kind `api`), probes, scoring policy, isolation manifest, evaluator configuration, a findings JSON
schema, and a ~150-line `subprocess`-only driver. The driver runs the `edge-case-hunter` layer
headlessly (`claude -p --output-format json --json-schema … --max-budget-usd 2
--no-session-persistence`, model pinned to the station's `[adapter.review].model`), maps exit
code + parsed findings to an observation, and emits the sealed run record. One strong oracle:
`covers-by-key` over `referenceSets.planted-defects` (`["file","line"]`) against the review's
cited locations — "the review ran" never passes on its own. Pixi tasks `eval-quality-smoke`,
`eval-quality-review-twin-run -- --trials N`, `eval-quality-review-replay`; never wired into
`detectors`, because this measures the reviewer and is not a PR gate.

**Success signal.** Smoke exits 0 on the shipped corpus; the pilot contract compiles; a one-trial
twin-run preflights both arms and the mutated arm cites `pkg/discount.py:17` while the clean arm
does not; three trials per arm yield a policy-comparable strength vector with a catch rate the
fleet can read.

## What is real

Nothing in the repo yet. The assessment and plan exist (2026-09-05); this Dream is their seed.
Dream-first applies: `bmad-spec` under `pyforge-steward` produces the contract before any recipe
or driver code.

## Constraints

- Dream-first and the CFE rules: the recipe goes through `conda-forge-expert` (Rule 1) and the
  effort ends with a CFE retro (Rule 2).
- Exact commit pin; bump `version` and `commit` together; never a floating HEAD.
- The pilot is not a gate. Findings stay measurements of the reviewer; Warden remains the sole PR
  verdict.
- Cost is bounded per run (`--max-budget-usd`); report catch-rate across trials, never one
  verdict, and pin model + effort.
- `spec-bmad-suite-channel-product` § Non-goals ("packaging anything new") is deliberately
  overridden for this fourteenth member.

## Non-goals

- Installing TEA as a module (it stays a pinned suite member; TEA is not needed to author
  contracts).
- Evaluating the full `bmad-build-auto` review skill end-to-end (no JSON surface; the layer
  prompt is the measurable unit first).
- Replacing `bmad-review` / `bmad-code-review` — they are the systems under test.
- Any dashboard, hosted service, or automatic prompt repair (upstream's own out-of-scope list).

## Kinships

- [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md) /
  [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md) — the membership machinery this joins.
- [`bmad-module-provisioning.md`](bmad-module-provisioning.md) — install-class wiring precedent.
- [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md) — sibling question about the
  reviewer; this Dream supplies the measurement that one would need.

## Realization log

- **2026-09-05** — Seeded from the assessment of
  [bmad-code-org/bmad-eval-quality](https://github.com/bmad-code-org/bmad-eval-quality). Operator
  locked the conda name (`bmad-eval-quality`) and the source (main, commit-pinned
  `0.2.0.dev0 @ 3172162f`). Next: `bmad-spec` under pyforge-steward.
- **2026-09-05 (later)** — `bmad-spec` derived `spec-bmad-eval-quality` under pyforge-steward
  (SPEC.md + `packaging.md` + `pilot-contract.md`; CAP-1 suite membership, CAP-2 pilot contract;
  status `ready`). Grounding re-verified same day: HEAD still `3172162f`, only `v0.1.0` tagged, npm
  0.1.0. CAP-1 is being built in the same PR as the Spec, in the SelfExplainML packaging pass that
  also retires `bmad-method-wds-expansion` (deprecated in the 6.12.0 core module registry; `bmad-ux`
  absorbs it) — the suite stays at 13 active members.
- **2026-09-05 (packaging)** — CAP-1 landed in PR #1059 (branch `suite/bmad-suite-refresh-2026-09-05`):
  `recipes/bmad-eval-quality/` authored in the bmad-method npm-CLI wrapper class (commit pin
  `3172162f` as `0.2.0.dev0`, `noarch: generic`, clean `npm ci --omit=dev`, license
  `Apache-2.0 AND MIT`, `conda-forge.yml` `noarch_platforms`), built and tested green locally;
  `suite-members.yaml` seats it in place of the retired `bmad-method-wds-expansion`; the
  metapackage regenerated to `2026.9.5`; steward's roster gained `INSTALL_CLASS_CLI`. Story 45.1
  stays `in-progress` until the operator uploads to SelfExplainML and the pixi pin lands (follow-up
  PR). CAP-2 (Story 45.2, the twin-run pilot) is still blocked on a first contract — status stays
  `specified`.
- **2026-09-05 (published + pinned)** — PR #1059 merged (`5cc084dfbe`); the four artifacts uploaded to
  SelfExplainML (`bmad-method` 6.12.0, `bmad-labs-skills` 1.0.0.dev0 build 1, `bmad-eval-quality`
  0.2.0.dev0, `bmad-suite` 2026.9.5); the pin PR adds `bmad-eval-quality >=0.2.0.dev0` to the
  `local-recipes` feature (WDS pin dropped), so `eval-quality` is on PATH in the day-to-day env and
  steward's pipeline-truth reads it `runnable`. **Story 45.1 done.** CAP-2 / Story 45.2 (the
  twin-run pilot) remains blocked on a first contract — status stays `specified`.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C4). CAP-2 is exercised: `evals/review-catches-planted-defect/` (contract, both arms, probes, driver, findings schema) with pixi tasks `eval-quality-smoke` / `eval-quality-review-twin-run` / `eval-quality-review-replay` (`pixi.toml:1044-1055`), and the Spec records the empirical clean-arm false-positive finding from live `--trials 3` runs. Status `specified` → **`realized`**. **Version currency:** § *Decisions locked* and § *What it looks like when real* still name `0.2.0.dev0 @ 3172162f`; upstream has since shipped through **v1.4.1**, the recipe is tag-sourced (`recipes/bmad-eval-quality/recipe.yaml:5,:12,:35`) and the pixi pin is `>=1.4.1` (`pixi.toml:1611`) — the commit-pin decision is historical record, not the live contract.

## 2026-09-17 — BMAD-METHOD's own core stays current, not stuck at whatever version got installed (folded from bmad-method-core-upgrade)

# BMAD-METHOD's own core stays current, not stuck at whatever version got installed

## The Dream

Something in this fleet can safely run `npx bmad-method install`/`@next` against THIS
existing repo — not a fresh clone — reconcile whatever changed in `_bmad/bmm/**`/
`_bmad/core/**` against this repo's own customizations (`_bmad/custom/**`, the
multi-project active-symlink mechanism, any skill this repo has locally overridden or
extended), report what's new/changed/deprecated, and give an operator a real upgrade path
instead of a one-off manual effort redone from scratch every time upstream ships a release.

Today there is no such capability, anywhere in the fleet. The only precedent is
`docs/specs/bmad-loop-adoption.md`'s historical 6.6.0→6.10.0 upgrade — a single, manual,
non-repeatable effort scoped to one specific jump, already closed out. BMAD-METHOD has
released since (v6.11.0, 2026-08-15) with nothing in this repo positioned to even notice,
let alone act on it.

## Whose job this is — resolved 2026-08-15, owner: steward

Investigated directly, not assumed. First pass found this genuinely unowned:

- **Marshal is ruled out on its own documented boundaries.** Marshal's own gap survey
  ([[one-front-door]]) marks `bmad-method` itself as **"route,"** explicitly distinct from
  what it marks **"own."** Marshal's architecture states installed BMAD skills
  (`_bmad/bmm/**`, `_bmad/core/**`) are **"installer-owned... Genesis must never write
  here."** This exclusion stands.
- **`genesis-installer`'s actual FR coverage is unrelated** — confirmed independently on a
  second pass (its own register: bmad-method is "verified, never installed," Genesis
  asserts a version floor and never vendors the package; its `update` verb (CAP-15) upgrades
  Genesis's own *materialized* artifacts, not bmad-method's installed core). Zero execution
  weight either way — all 36 of its stories are still `backlog`.
- **Steward was initially ruled out too**, by [[bmad-module-provisioning]]'s Constraints —
  "Never absorb `bmad-method`'s own governance core... does not reimplement `bmad-method
  install` or take ownership of `_bmad/bmm/**`/`_bmad/core/**`" — read literally, that line
  excludes this exact gap by name.

A second, deeper investigation (operator-requested, 2026-08-15) found that exclusion was
broader than its own reasoning supported. [[bmad-module-provisioning]]'s Constraint was
written to prevent duplicating Marshal's/genesis-installer's turf for **first-installing**
adjacent modules (Skill Forge, BMB) from nothing — a different job from **reconciling an
already-installed** bmad-method core against a new upstream release, which this Dream is
actually about. Steward's own charter is broad by design ("deploys, provisions, and
operates — environments and runners, service deployments, credential and privilege
lifecycles") and its already-shipped `provision --env`/`--runner` duty (Epic 3) is
structurally the same shape this needs: wrap an external tool non-interactively, report a
clear error, never leave partial state unreported.

**Resolution:** [[bmad-module-provisioning]]'s Constraints were amended the same day to
narrow the "never absorb" line to first-install only, and carve out this Dream by name as
the distinct, ALSO-Steward-owned capability for reconciling an already-installed core.
**Detection is a separate, Doctor-owned Dream** — [[bmad-method-version-drift]] — kept
apart because it stands on its own value (an operator should see "you're behind" as an
ambient signal even before anyone runs the upgrade tool) and matches Doctor's own
report-only shape (PRD Non-Goals: "No auto-remediation actuator... Doctor never opens PRs,
patches files, or mutates any state") rather than Steward's mutating one. This Dream may
still perform its OWN pre-flight diff as part of a safe apply (see "What it looks like when
real" below) — that is a mechanical precondition for applying safely, not a duplicate of
[[bmad-method-version-drift]]'s ambient reporting.

**Concrete, live proof this gap is real right now** (found during the second investigation,
not hypothetical): `pixi.toml` already declares `bmad-method = ">=6.11.0"`, but
`_bmad/_config/manifest.yaml` (the actually-installed core) still reports `version:
6.10.0` — the dependency floor was bumped without the installed `_bmad/bmm/**`/
`_bmad/core/**` content ever being reconciled.

## What it looks like when real

- A non-interactive, re-runnable command reports what an upstream BMAD-METHOD release
  would change against this repo's CURRENT installed state before touching anything —
  new/removed modules, skill files this repo has locally modified that upstream also
  touched (a real conflict, not a silent overwrite), and whether `_bmad/custom/**`
  overrides still apply cleanly.
- Applying the upgrade is a deliberate, reviewable step (matches this repo's own
  archive-don't-delete / review-before-mutate convention running through every other
  provisioning-shaped capability in the fleet) — never a silent `npx bmad-method install`
  overwrite in place.
- The multi-project active-symlink/marker mechanism ([[pyforge-marshal]]'s own territory)
  survives an upgrade without needing to be manually re-established afterward.

## What is real

Nothing. Confirmed 2026-08-15: this repo has no mechanism to detect, diff, or apply a
BMAD-METHOD core release, and the only prior upgrade (6.6.0→6.10.0) was a manual,
non-repeatable one-off.

## Constraints

- Must not silently overwrite `_bmad/custom/**` (team + user override layers) — an upgrade
  that clobbers local customization without surfacing the conflict is worse than no
  upgrade path at all.
- Must respect the multi-project symlink/marker mechanism's own fragility (already
  documented as a live footgun in [[pyforge-marshal]]/CLAUDE.md's own "parallel agents"
  warnings) — an upgrade run mid-way through other agent activity must not desync it.

## Non-goals

- Not deciding which currently-unexercised modules to keep or drop (`bmad-manticore`,
  `bmad-labs-skills`, etc.) — that's [[one-front-door]]'s own open question, orthogonal to
  how the CORE gets upgraded.
- Not re-scoping [[bmad-module-provisioning]]'s already-shipped adjacent-module
  provisioning — that Dream's own Constraints were amended 2026-08-15 to carve THIS
  territory out to this Dream by name, not to hand its own realized scope over.
- Not the ambient "you're behind" signal — that is [[bmad-method-version-drift]] (owner:
  doctor), a standing health finding an operator sees without running anything. This Dream
  may do its own pre-flight diff as a precondition for a safe apply, but owning a
  continuously-refreshed fleet-wide staleness report is Doctor's job, not Steward's.

## Kinships

[[bmad-module-provisioning]] (realized; its Constraints were amended 2026-08-15 to carve out
this exact territory by name — first-install there, already-installed reconciliation here) ·
[[bmad-method-version-drift]] (owner: doctor, split off 2026-08-15 — the ambient
detection half of what was originally one unowned Dream) · [[one-front-door]] (the survey
whose own "route" vs "own" line this Dream's investigation relies on) · [[genesis-installer]]
(the boundary this Dream is outside of) · [[pyforge-marshal]] (owns the multi-project symlink
mechanism an upgrade must not break).

## Realization log

- **2026-08-15** — Dream captured. Surfaced when the user asked, after noticing
  BMAD-METHOD v6.11.0 had released, whether any station owns installing/upgrading it in
  this repo. Investigation (mirroring [[bmad-module-provisioning]]'s own ownership
  reasoning) found the gap is real and, unlike that Dream, genuinely unowned — both Marshal
  and Steward have explicit, on-the-record boundaries excluding it. Captured as its own
  Dream with the ownership question left open rather than defaulted, per the same rigor
  [[bmad-module-provisioning]] itself modeled.

- **2026-08-15 (resolved, same day)** — Owner assigned: **steward**. The dashboard's
  ACCOUNTABILITY gate refused to publish over the `unassigned` owner (Charter §7: "the hall
  does not put a row on the wall it cannot attribute"), which prompted the operator to ask
  directly whether Steward could own the install half after all, with Doctor owning
  update/refresh detection. A second investigation (independent of the first, requested
  explicitly to push back rather than rubber-stamp) found [[bmad-module-provisioning]]'s
  exclusion was narrower in its own reasoning than its Constraint's literal wording — written
  against first-install duplication, never evaluated against already-installed reconciliation
  — and found live, present-tense proof the gap matters now: `pixi.toml` already requires
  `bmad-method >=6.11.0` while the installed `_bmad/_config/manifest.yaml` still reports
  `6.10.0`. Resolved by amending [[bmad-module-provisioning]]'s Constraints (narrowed, this
  Dream carved out by name) and splitting the ambient-detection half into a new sibling Dream,
  [[bmad-method-version-drift]] (owner: doctor), rather than co-owning one Dream across two
  stations — no precedent exists for a Dream naming more than one owner, checked against all
  100 Dreams at the time.

- **2026-09-06 — first live steward-driven apply (6.11.0 → 6.12.0, PR #1074).**
  CAP-1..5 ran end to end for the first time; the installer stayed sole writer,
  `_bmad/custom/**` came out byte-identical, CAP-3 restored the multi-project
  `resolve_config.py`. The run also falsified the Spec's first assumption
  ("`--action update -y` is idempotent and safe to re-run"): with a closed stdin
  the installer exits 0 having written nothing; `-y` deletes the cached custom
  module skf; skf's marketplace list and config regeneration drop a skill and
  hand-set answers; seven installer-owned skill files carrying marshal edits were
  regenerated away — and the regenerated user layer made every rendering skill
  HALT on an ambiguous config key. All recovered by hand on the branch. The
  bullet "skill files this repo has locally modified that upstream also touched"
  in *What it looks like when real* was never implemented — CAP-1 narrowed it to
  marker-carrying scripts. Direction: widen the Spec (CAP-6 installer drive,
  CAP-7 custom modules, CAP-8 local-customization scan and re-apply) and
  decompose into Epic 14 stories 14.6–14.8; the customization inventory lives in
  `spec-bmad-method-core-upgrade/customization-inventory.md`.

## 2026-09-17 — BMAD Method modules are provisioned, not hand-installed (folded from bmad-module-provisioning)

# BMAD Method modules are provisioned, not hand-installed

## The Dream

Every BMAD Method module this repo actually uses — `bmad-method` itself, Skill Forge
(`skf-*`), `bmad-builder` (BMB), and whichever of TEA/CIS/the currently-unexercised
`bmad-manticore`/`bmad-labs-skills`/`bmad-utility-skills`/`bmad-method-wds-expansion`/
`bmad-module-template` turn out to be kept — gets provisioned the same disciplined way
`steward provision` already handles pixi environments and `bmad-loop-worktree` runners:
one command, a clear error on failure, no hand-driven installer scripts kept alive only in
someone's session scratchpad.

Today it isn't. Skill Forge is live in `.claude/skills/skf-*` because of a single ad-hoc
`story(0.1)` commit (2026-07-17) that manually drove the `bmad-module-skill-forge` npm
package's TTY-only `Installer` class via a custom, undiscoverable driver script — provisioned
for `pyforge-atlas`'s own needs, not as a repeatable repo-wide capability. `bmad-builder`
is installed as a pixi package but was never taken through its own `bmad-bmb-setup` skill, so
it isn't wired into `.claude/skills/` at all. Neither installation is reproducible, auditable,
or re-runnable against a fresh clone or a brownfield adoption.

## Whose job this is, and why it isn't genesis's

This was investigated directly, not assumed. Two boundaries rule out Marshal:

- Marshal's own gap survey ([[one-front-door]]) marks `bmad-method`, BMB, and Skill Forge as
  **"route"** — explicitly distinct from the things it marks **"own"** (multi-project wiring,
  loop homes, the detector registry) in the same table.
- Marshal's own architecture is explicit that installed BMAD skills (`_bmad/bmm/**`,
  `_bmad/core/**`) are **"installer-owned... Genesis must never write here"** — absorbing
  module installation would make Marshal "the fork-owner of somebody else's governance core"
  (the same reasoning that keeps `bmad-loop` wrapped, never absorbed).
- [[genesis-installer]] (Marshal's Epics 7-12)'s actual FR/AD coverage — read directly from
  its epics document — is a Copier-based *file/region templating* engine (extraction
  manifest, managed-region markers, detect/plan/materialize/migrate). It stamps this repo's
  own conventions (Dreams tier, `AGENTS.md` family, multi-project wiring) into a repo; it has
  no FR anywhere for provisioning a third-party npm-distributed BMAD module.

Steward's own Dream is "the estate the factory stands on — provisioning, deployment,
credential lifecycle, budgets," and its just-shipped Epic 3 (`steward provision --env
<name>`, `--runner bmad-loop --env <name>`) is already the exact shape this needs: wrap an
external installer non-interactively (AD-1/AD-5, "delegate, never reimplement"), report a
clear error instead of the tool's own raw one, never leave partial state unreported.

## What it looks like when real

- `steward provision --module skf` / `--module bmb` (naming TBD at Spec time) runs whatever
  each module's own non-interactive install path actually is — `bmad-bmb-setup`'s config-merge
  scripts for BMB, an equivalent non-interactive driver for Skill Forge — the same way
  `--env`/`--runner` already wrap `pixi install`/`bmad-loop-worktree`.
- `steward provision --list` (already ships, Story 3.3) is extended, or a sibling verb is
  added, so an operator can see which BMAD modules are installed and which are merely
  available, the same at-a-glance discovery Story 3.3 already gives pixi environments.
- A fresh clone or a brownfield `genesis adopt` target can reach "Skill Forge and bmad-builder
  are both live and correctly configured" through one Steward command — no session-scratchpad
  driver script, no manual npm `Installer` class invocation, ever again.
- The existing, already-working Skill Forge installation is left alone (it works); this closes
  the gap for the *next* module or the *next* repo, and gives the current installation a real,
  reproducible provisioning path to fall back on if it ever needs to be redone.

## What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured at the moment the gap was
found while scoping [[conda-forge-expert-rebuild]] (which needs Skill Forge, live today only
because of the one-off 2026-07-17 provisioning). Owner assigned to `steward` per the
investigation above — Marshal was ruled out on its own documented boundaries, not by default.

## Constraints

- **Never absorb `bmad-method`'s own governance core AS A FIRST-INSTALL.** This Dream
  provisions modules from scratch (the Skill Forge/BMB-class case); it does not reimplement
  `bmad-method install` for a repo that has never run it, and does not take blanket ownership
  of `_bmad/bmm/**`/`_bmad/core/**`, which stay installer-owned per Marshal's own architecture.
  **Amended 2026-08-15** (see Realization log): this line originally read as a blanket ban on
  any `bmad-method`-core work by Steward at all, which turned out to be broader than the
  reasoning behind it actually supported. Reconciling an ALREADY-installed bmad-method core
  against a new upstream release — diff, merge, re-apply `_bmad/custom/**` overrides — is a
  distinct capability, carved out to [[bmad-method-core-upgrade]] (owner: steward), never this
  Dream. This Dream's own scope stays exactly what it always was: first-install provisioning
  of adjacent modules (Skill Forge, BMB, future TEA/CIS).
- **Non-interactive by construction.** Every module's own installer tends to assume a TTY
  (Skill Forge's does); the provisioning wrapper must drive it headlessly and reproducibly,
  not rely on a hand-kept driver script the way the 2026-07-17 commit did.

## Non-goals

- Not deciding which of the currently-unexercised modules (`bmad-manticore`,
  `bmad-labs-skills`, `bmad-utility-skills`, `bmad-method-wds-expansion`,
  `bmad-module-template`) to keep or drop — that triage is [[one-front-door]]'s own open
  question, orthogonal to how a kept module gets provisioned.
- Not re-provisioning Skill Forge's already-working installation — this targets the *next*
  module and the *next* repo, not a redo of what already runs.

## Kinships

[[conda-forge-expert-rebuild]] (the effort that surfaced this gap — needs Skill Forge
provisioned reproducibly) · [[pyforge-steward]] (the estate; Epic 3's provisioning duty is
this Dream's direct precedent) · [[one-front-door]] (the survey that first drew the
own/route/triage line this Dream's ownership reasoning relies on) · [[genesis-installer]]
(the boundary this Dream is deliberately outside of) · [[bmad-method-core-upgrade]] (the
distinct, ALSO-Steward-owned capability this Dream's Constraints were narrowed 2026-08-15 to
carve out — first-install here, already-installed reconciliation there).

## Realization log

- **2026-08-07** — Dream captured. Surfaced while scoping [[conda-forge-expert-rebuild]]: that
  effort needs Skill Forge, and investigation showed it was installed via a single 2026-07-17
  ad-hoc commit driving an npm package's TTY-only Installer class by hand, not through any
  repeatable path, and `bmad-builder` was never taken through its own setup skill at all. User
  asked whether provisioning both should have been genesis's job; investigation (Marshal's own
  "route" vs "own" survey, its "installer-owned... Genesis must never write here" architecture
  line, and genesis-installer's actual FR coverage being file/region templating, not module
  provisioning) ruled Marshal out on its own documented boundaries. Assigned to Steward,
  whose Epic 3 provisioning duty (just merged) is structurally the same shape this needs.

- **2026-08-10** — **Realized.** Steward Epic 6, "Module provisioning", is **3/3 done and
  merged**. The Dream's frontmatter had been left at `dreamt` throughout — same rot as
  [[unified-container]], found in the same 2026-08-10 sweep. What the Dream asked for is what
  landed: the hand-installed modules are now provisioned through Steward's own `provision` duty,
  the way it already wraps pixi and the bmad-loop worktree, rather than through a one-off npm
  Installer invocation nobody could reproduce. Evidence: steward's `sprint-status-ledger.yaml`
  Epic 6.

- **2026-08-15 (amendment)** — Constraints narrowed. A new Dream, [[bmad-method-core-upgrade]]
  (captured the same day investigating whether any station owns *upgrading* an already-installed
  bmad-method core — not just first-installing adjacent modules — after the user noticed
  BMAD-METHOD v6.11.0 had released), initially came up genuinely unowned, blocked by this
  Dream's own "never absorb bmad-method's own governance core" line read literally. Deep-dive
  (an independent research pass over this Dream's full text, Steward's own charter, and
  genesis-installer's actual FR coverage) confirmed that line was written to prevent
  duplicating Marshal's/genesis-installer's turf for FIRST-INSTALL, never evaluated against the
  distinct case of reconciling an already-installed core against a new upstream release — this
  Dream drives each module's own installer once, from nothing; reconciling means diffing
  installed state against upstream AND against this repo's own `_bmad/custom/**` overrides,
  which this Dream's existing scope never touches. Concrete live proof the gap is real, found
  during the same investigation: `pixi.toml` already declares `bmad-method = ">=6.11.0"` but
  `_bmad/_config/manifest.yaml` (the actually-installed core) still reports `version: 6.10.0`
  — the dependency floor was bumped without the installed content ever being reconciled.
  Narrowed the Constraint to say so explicitly and handed the upgrade-apply capability to
  [[bmad-method-core-upgrade]] (owner: steward) as its own Dream, keeping this Dream's own
  realized scope (Epic 6, first-install provisioning) unchanged.

## 2026-09-17 — The PrivateChannel bmad-suite is a governed product — always latest, dual-path installable, modules provisioned (folded from bmad-suite-channel-product)

# The PrivateChannel conda install bmad-suite is a governed product

## The Dream

The operator intends to utilize the complete bmad-suite (13 packages). Every
one of them should be installable two ways at all times — **via pixi from the
PrivateChannel channel** and **via its upstream-native method** (npm, npx
module selection, uv-from-git, Claude plugin marketplace, custom-source) —
at the latest available version, with its skills/module actually wired where
the fleet works. Today that is true only because a human hand-drove all seven
pipeline stages during the 2026-08-21/22 refresh: upstream-watch → recipe
bump → build → channel publish → pixi install → module wiring → native-parity
check each exist as an isolated tool, and **no stage is connected to the
next, scheduled, or verified end-to-end**. The proof: the channel served a
stale `bmad-method 6.3.0` for four months and bmad-loop sat two minors behind
(an unattended-run breaker) with no signal until a human looked.

## Grounding — verified state (2026-08-22 research pass)

**Version currency is NOT the gap (today):** all 5 tag-pinned suite recipes
match the newest upstream tag/release; all 6 commit-pinned recipes
(utility-skills, labs-skills, module-template, manticore, dashboard, mybmad)
are pinned at the literal default-branch HEAD. Two exceptions:

1. **Channel `bmad-method` = 6.3.0** vs recipe/conda-forge 6.11.0 — the one
   channel↔recipe divergence (harmless to solves: conda-forge shadows it, and
   conda-forge/bmad-method-feedstock is current at 6.11.0 — the ONLY suite
   package with a feedstock; the other 12 are PrivateChannel-Conda -only).
2. **TEA v1.23.3 tagged-but-unreleased** (git tag exists, package.json 1.23.3;
   npm latest still 1.23.2, no GH release) — a watch/optional bump.

**The native-method taxonomy (7 classes, per upstream docs — the matrix a
dual-path guarantee must encode):**

| Class | Packages | Native command |
|---|---|---|
| npm CLI installer | bmad-method | `npx bmad-method install` |
| Own npx installer | bmad-module-skill-forge | `npx bmad-module-skill-forge install` |
| BMAD module via installer selection | TEA, bmad-builder, CIS (WDS until its 2026-09-05 retirement) | `npx bmad-method install` → select module |
| Custom-source BMAD module | bmad-manticore | `npx bmad-method install --custom-source <repo-url>` |
| Claude Code plugin marketplace | bmad-utility-skills, bmad-labs-skills | `/plugin marketplace add <repo>` (labs also `npx skills add bmad-labs/skills`) |
| uv-from-git (Python, not on PyPI) | bmad-loop | `uv tool install "bmad-loop[tui] @ git+…@v0.11.0"` |
| Template / build-from-source | bmad-module-template (GitHub template); bmad-dashboard + mybmad-dashboard (pnpm build / self-host) | per-repo README |

**npm hazards the pipeline must encode (2026-08-22 count; recounted below):** 7 packages are npm-invisible under
their recipe names (loop, wds, utility-skills, labs-skills, module-template,
manticore, mybmad); 3 more are npm-STALE with GitHub as the channel of record
(builder 1.1.0-on-npm vs 2.2.1, CIS 0.1.9 vs 0.3.1, WDS 0.3.1/0.3.4 vs
0.4.3); and 3 npm name-collisions must never be confused with the suite
(`bmad-dashboard` = caionormando, `bmad-skills` = bacoco, `bmad-method-ui` =
lorenzogm).

**The machinery that exists but composes into nothing (local audit):**

- `autotick-github` / `autotick-npm` pixi tasks — one recipe per manual
  invocation; no batch mode, no registration of covered recipes, no schedule,
  and no HEAD-advance mode for the six commit-pinned dev recipes.
- `steward provision --module` shipped (Epic 6) but `_SUPPORTED_MODULES`
  holds exactly one entry (`bmb`); TEA/CIS/utility-skills/manticore were
  never added. Wired today: core+bmm, skf, labs-skills, loop, dashboards.
  Unwired: TEA, BMB(builder), CIS, utility-skills, manticore.
- `inventory-channel` can audit any channel URL — never pointed at our own.
- Channel publish = the hand-run `anaconda -s … upload` cheatsheet flow; no
  task, no verify-the-listing step, no channel↔recipe drift detection.
- Doctor's suite drift (14.1, shipped 2026-08-22) watches installed-env vs
  npm only — blind to the 7 npm-invisible packages pending the
  GitHub-releases fallback (doctor DW-14-1-1), and nothing watches
  recipe-vs-upstream or channel-vs-recipe at all.
- `bmad-module-skill-forge` has NO pixi.toml pin (consumed only via the BMAD
  installer) — the one pixi-installability gap in the suite itself.

### Roster and version state — re-verified 2026-09-05 (`steward suite pipeline-truth`)

The 2026-08-22 findings above are the seed baseline. This is the live state
after BMAD-METHOD 6.12.0 (released 2026-09-04) and the 2026-09-05 refresh:

- **13 active members, one seat changed.** `bmad-method-wds-expansion` is
  **deprecated** — 6.12.0's `bmad-modules.yaml` marks it `deprecated: true`,
  folded into BMM as the `bmad-ux` skill — so it left the metapackage and
  the matrix (recipe kept in-repo as a catalog row); **`bmad-eval-quality`**
  took the seat (commit-pinned `0.2.0.dev0 @ 3172162f`; npm `latest` 0.1.0
  lacks `score`). Pins: **6 tag-pinned** (method 6.12.0, loop 0.11.1,
  TEA 1.24.0, builder 2.2.2, CIS 0.3.2, skill-forge 2.1.0) and **7
  commit-pinned** (eval-quality, utility-skills, labs-skills, module-template,
  manticore, dashboard, mybmad-dashboard).
- **Every stage agrees for all 13** — recipe = channel = installed. The only
  named drifts are `wired` for the four modules deliberately not provisioned
  in this repo (TEA, builder, utility-skills, manticore) and the npm/GitHub
  divergence for builder (npm 1.1.0) and CIS (npm 0.1.9). The TEA v1.23.3
  watch closed: 1.24.0 released.
- **An eighth native class.** `bmad-eval-quality` is a bare npm CLI with
  nothing to wire into `_bmad/` — steward's roster carries it as
  `INSTALL_CLASS_CLI` (`eval-quality` on PATH). Hazard recount: npm-invisible
  ×6 (loop, utility-skills, labs-skills, module-template, manticore, mybmad),
  npm-stale-with-GitHub-canonical ×3 (builder, CIS, eval-quality),
  name-collisions ×3 (unchanged), plus the G109 renumber hazard (manticore
  GitHub tag 1.0.1 vs recipe 3.1.0.dev0; eval-quality tag 0.1.0 vs
  0.2.0.dev0).
- **One hole in "the whole pipeline's truth".** For the installer-tree class
  (`bmad-method`) the `installed` stage reads the pixi env's conda-meta
  (6.12.0), not the applied `_bmad/_config/manifest.yaml` (6.11.0) — so
  pipeline-truth reads all-green while the core upgrade is still unapplied.
  Doctor's core drift check is the only signal today (it warns 6.11.0 <
  6.12.0). Relayed to steward's deferred-work ledger, not minted as a CAP.

## Whose job this is

**Steward** — the pipeline is operations: publishing to a channel it holds
credentials for, provisioning modules (its realized `bmad-module-provisioning`
capability, deliberately built to grow one `_SUPPORTED_MODULES` entry at a
time), and running scheduled duties. The pieces other stations own are
relayed, not absorbed: **doctor** keeps ambient detection (the
GitHub-releases fallback DW-14-1-1 + new channel↔recipe/recipe↔upstream
checks extend its shipped suite-drift spec); **CFE/the factory** keeps recipe
bumps (autotick extensions land as skill-script work under Rule 1/2);
**mason** keeps recipe validation. Kin, not overlap: steward Epic 14 (core
upgrade apply), `bmad-611-era-alignment` (marshal, era retrofits).

## What it looks like when real

- **One command reports the whole pipeline's truth**: for each of the 13 —
  upstream latest (npm AND GitHub, per its class), recipe version, channel
  version, installed version, wired-or-not — with drift named per stage.
- **One command advances a stale package end-to-end**: autotick (tag-mode or
  HEAD-advance mode per the recipe's pin style) → build → test → publish →
  listing verified — the 2026-08-21 seven-stage hand ritual as governed
  machinery, CFE conventions intact.
- **`steward provision --module` covers every wire-decided module** (TEA,
  bmb, CIS, utility-skills, manticore added; WDS explicitly skip-decided as
  upstream-deprecated; template is a scaffold, labs/loop/skf/dashboards
  already wired) — reproducible against a fresh clone, manifest-recorded,
  collision-checked, guard-green.
- **The dual-path matrix is a tracked contract**: per package, the pixi path
  and the native command, with the npm-invisible/stale/collision hazards
  recorded — and the upgrade verification gate spot-checks one native path
  per class rather than trusting docs.
- **The channel never rots silently again**: channel↔recipe drift is an
  ambient doctor finding (the 6.3.0 relic class), and the stale
  `bmad-method 6.3.0` itself is resolved (refresh-or-drop decided at spec
  time; conda-forge stays canonical for that one package either way).

## What is real

**The governed pipeline (steward Epic 15 + doctor Epics 15/19 + steward
Epics 31/39, all done):** `steward suite pipeline-truth` (CAP-1;
class-correct `wired` since Story 31.2), `steward suite advance` end-to-end
into a reviewable PR with a HEAD-advance mode for commit-pinned recipes
(CAP-2), `steward provision --module` for `{bmb, tea, cis, utility-skills,
manticore}` with WDS a cited skip (CAP-3), the tracked `install-matrix.md`
plus the per-class gate spot-check (CAP-4), doctor's channel↔recipe /
recipe↔upstream findings with the GitHub-releases fallback (CAP-5), and the
`bmad-suite` metapackage + `suite-members.yaml` manifest +
`generate-bmad-suite` (CAP-6; `2026.9.5` on the channel).

**Its first real run — the 2026-09-05 refresh (PRs #1059/#1060):** method
6.12.0, labs-skills HEAD, eval-quality in, WDS out, metapackage regenerated,
four artifacts uploaded, pins landed. Not zero improvisation: the
`bmad-eval-quality` pin had to move into the linux-64/osx-arm64 target tables
because the channel holds only the `__unix` noarch variant (a Windows build
is owed), the CFE-retro slices needed re-mirroring with a CRLF stamp, and
`anaconda upload` stays an operator step by design. Open holes: the
installer-tree `installed` stage (above), the `__win` variant, and doctor's
suite drift mapping 7 of 13 members (commit-pinned members unmapped).

## Constraints

- conda-forge stays canonical for `bmad-method`; the channel copy is
  refresh-or-drop, never a fork.
- Wiring is deliberate per-module triage (one-front-door's posture), never
  wire-everything: WDS is a skip (deprecated upstream, absorbing into
  bmad-ux); each addition to `_SUPPORTED_MODULES` carries its own
  verification (manifest recorded, no skill-name collisions, retired-ID
  guard + integrity meta tests green).
- Native-method commands come from upstream READMEs, recorded with the
  citation — never invented; the collision list travels with the matrix.
- Publishing stays credential-gated through steward's key discipline;
  publish-before-floor-bump ordering holds (the cheatsheet rule).
- Commit-pinned dev recipes keep the `X.Y.Z.dev0 @ <sha>` encoding and the
  version-of-record re-derivation rule (CFE G109).
- A member the upstream module registry marks `deprecated: true` (WDS since
  6.12.0) stays in `suite-members.yaml` as a catalog row and never re-enters
  the metapackage run deps or the matrix; its recipe is kept, not deleted.

## Non-goals

- Packaging anything new (autopilot/bmalph/dashboard-extension stay parked;
  the suite is the operator's 13).
- Submitting more suite packages to conda-forge (PrivateChannel is the home;
  bmad-method's feedstock is the one exception and stays upstream).
- The bmad-method core upgrade itself (steward Epic 14) and the era-retrofit
  chain (marshal Epic 25) — kin efforts this pipeline feeds and consumes.
- Auto-merge of autotick output — bumps land as reviewable PRs, git review
  decides (the factory's standing posture).

## Kinships

[[bmad-module-provisioning]] (realized; `_SUPPORTED_MODULES` is this Dream's
wiring seam) · [[bmad-suite-install-class-wiring]] (companion Dream: how
method/loop/skf/labs/dashboards/template get provisioned by install class —
not through `--module`) · [[bmad-method-version-drift]] (doctor; DW-14-1-1's
GitHub fallback + the new per-stage drift checks extend it) ·
[[bmad-method-core-upgrade]] (steward Epic 14; its CAP-4 pin fan-out and
CAP-5 gate consume this pipeline's output) · [[bmad-611-era-alignment]]
(marshal Epic 25; the era-alignment this pipeline keeps from regressing) ·
CFE skill (autotick machinery; Rule 1/2 govern the recipe-side stories).

## Realization log

- **2026-08-22** — Seeded and specified in one commit (`24c4dce923`): `spec-bmad-suite-channel-product`
  under pyforge-steward (5 CAPs + `install-matrix.md`, status `ready`); decomposed as steward Epic 15
  (4 stories) + doctor Epic 15 (2 stories, the CAP-5 relay); channel `bmad-method` refreshed to
  6.11.0 the same day.
- **2026-09-05** — The channel machinery this Dream specified carried the suite refresh: PR #1059
  regenerated the metapackage to `2026.9.5`, seating `bmad-eval-quality` in place of the retired
  `bmad-method-wds-expansion` (see [`bmad-eval-quality.md`](bmad-eval-quality.md) § Realization log).
- **2026-09-05 (re-check)** — BMAD-METHOD 6.12.0 (released 2026-09-04) re-verified against the live
  `pipeline-truth`: 13/13 recipe = channel = installed; roster = 6 tag-pinned + 7 commit-pinned; the
  eighth class (`cli`) recorded; hazards recounted (6 / 3 / 3). Status → `realized` (owed since
  Epic 15 closed 2026-08-22). Holes relayed rather than minted as CAPs: the installer-tree
  `installed` stage reads the pixi env, not the applied `_bmad/` manifest; the `bmad-eval-quality`
  `__win` variant; doctor suite drift maps 7 of 13. The Spec's memlog and `install-matrix.md`
  were updated the same day.

## 2026-09-17 — Non-module bmad-suite pieces are provisioned by install class — not forced through --module (folded from bmad-suite-install-class-wiring)

# Non-module bmad-suite pieces are provisioned by install class

## The Dream

An operator who wants the **whole** SelfExplainML bmad-suite live on a fresh
clone — not only the five wire-decided BMAD modules — can get there without a
session-scratchpad ritual and without pretending every package is a
`steward provision --module` target.

Today the suite Dream ([[bmad-suite-channel-product]]) correctly grows
`_SUPPORTED_MODULES` for **bmb / tea / cis / utility-skills / manticore**
(CAP-3) and correctly **skips** WDS. It also correctly says steward's product
job is **channel ops + upgrade pipeline**. That left a hole in the operator's
head: *how do method, loop, skill-forge, labs-skills, dashboards, and
module-template get onto PATH and actually wired*, if not through `--module`?

This Dream answers that hole. **Each remaining piece has an install class.**
Steward provisions and keeps them current **through that class** — pixi pin,
existing `--env` / `--runner`, Epic 14 upgrade prove-landed, pixi tasks, or
documented native one-shots — never by stuffing the wrong shape into
`_SUPPORTED_MODULES`.

When this is real, "the suite is installed" means: artifacts on PATH **and**
the class-correct wire has been run (or deliberately N/A), reported in the
same pipeline-truth language CAP-1 already wants (`wired-or-not` per package,
named by class).

## Grounding — the six that are not CAP-3 modules

| Piece | Install class | How it gets on PATH | How it gets wired | Steward surface (intended) |
|---|---|---|---|---|
| **bmad-method** | Core / npm CLI installer | pixi pin (conda-forge canonical; SelfExplainML parity) | `npx bmad-method install` owns `_bmad/core` + BMM — Genesis must never write there | Epic 14 upgrade + prove-landed; **not** `--module` |
| **bmad-loop** | uv-from-git tool / orchestrator | pixi pin (+ optional `uv tool install …@git`) | Loop homes / worktrees | Existing `steward provision --runner bmad-loop --env …`; **not** `--module` |
| **bmad-module-skill-forge** (skf) | Own npx installer (+ module into `_bmad`) | pixi pin (suite pixi gap closed 2026-08-22) | `npx bmad-module-skill-forge install` (or method-driven module install) | Channel pin + native install; **optional** future `--module skf` only if Spec proves it is the same family as bmb — not required to close this Dream |
| **bmad-labs-skills** | Claude plugin / `skills add` marketplace | optional pixi package | `npx skills add bmad-labs/skills` or `/plugin marketplace add …` | Channel pin + CAP-4 matrix spot-check; **not** `--module` |
| **bmad-dashboard** / **mybmad-dashboard** | Build / self-host app | pixi `bmad-ui` feature | `pixi run bmad-dashboard-install` (VS Code); pnpm/setup for web | Publish + pin + install task; **not** `--module` |
| **bmad-module-template** | GitHub template scaffold | channel mirror (optional) | "Use this template" when **creating** a new module repo — never into an existing tree | Channel completeness only; **no provision-into-repo** |

**WDS** stays the explicit skip from the suite Dream (deprecated → `bmad-ux`).
**CAP-3 five** stay on `--module`. This Dream does not reopen those decisions.

## Whose job this is

**Steward** — same estate as [[bmad-module-provisioning]] and
[[bmad-suite-channel-product]]: wrap external installers, never absorb them;
keep pins and channel listings honest; make the operator path discoverable.

Not Marshal/Genesis: those own Copier regions and multi-project wiring;
`_bmad/core/**` and `_bmad/bmm/**` remain installer-owned.

Doctor stays ambient (suite drift, channel↔recipe); CFE/mason stay recipe
build/validate. This Dream does not move those boundaries.

## What it looks like when real

- A **class-keyed playbook** (Dream → Spec companion to the install matrix)
  tells an operator, for each of the six, the pixi path, the native wire, and
  the steward verb/task — one page, no tribal knowledge.
- A **fresh clone** can reach "method core installed, loop runner provisionable,
  skf skills present, labs plugin path documented, dashboard install task
  runnable, template N/A unless scaffolding" without hand-driving npm
  `Installer` classes from a chat transcript.
- CAP-1's `wired-or-not` column tells the truth **per class** (installer tree /
  runner home / plugin enabled / VS Code extension / scaffold N/A) — not a
  boolean that only CAP-3 modules can satisfy.
- Nothing in `_SUPPORTED_MODULES` that is not a BMAD expansion module merging
  into `_bmad/` + `.claude/skills`.
- Optional stretch (Spec may refuse): `steward provision --module skf` as a
  thin wrap of skf's own non-interactive install — sibling to bmb, not a
  precedent for loop/labs/dashboards/template.

## Constraints

- **Never wire-everything through `--module`.** Install class is load-bearing;
  symmetry is not a reason.
- **Never absorb bmad-method first-install** into steward; Epic 14 owns
  reconcile/upgrade of an already-installed core
  ([[bmad-method-core-upgrade]]).
- **Never absorb bmad-loop**; wrap via `--runner` only
  ([[bmad-module-provisioning]]'s same "wrap, don't absorb" line).
- Native commands come from upstream READMEs and the suite install matrix —
  cited, never invented; npm collision denylist travels with the matrix.
- Template is scaffold-only; provisioning it "into" this monorepo is out of
  scope forever.
- Dual-path (pixi + native) remains the suite product contract; this Dream
  only names the **wiring** half for non-module classes.

## Non-goals

- Growing CAP-3's five-module set, or un-skipping WDS.
- Replacing Epic 15's channel pipeline / truth report / advance command.
- Packaging autopilot / bmalph / dashboard-extension (still parked).
- Making labs or dashboards look like BMAD installer modules.
- Auto-enabling Claude plugins without operator consent.

## Kinships

[[bmad-suite-channel-product]] (parent product Dream; CAP-3 modules + CAP-4
matrix — this Dream is the **non-module wiring** companion) ·
[[bmad-module-provisioning]] (realized `--module` seam for installer-class
modules; skf optional extension lives there if Spec says yes) ·
[[bmad-method-core-upgrade]] (method upgrade / prove-landed) ·
[[bmad-method-version-drift]] (doctor ambient) ·
[[one-front-door]] (own / route / triage posture that forbids wire-everything)

## Realization log

- **2026-08-23** — Dreamt. Captured after operator confusion: channel listing
  of all 13 packages ≠ `--module` wiring; CAP-3 five clarified; remaining six
  needed an explicit install-class Dream so steward's "channel + upgrade, not
  --module" line has a positive "how then?" rather than only a refusal.
- **2026-08-24** — Specified. Chain Spec `spec-bmad-suite-install-class-wiring`
  landed `ready` (CAP-1 playbook, CAP-2 class-correct wired-or-not, CAP-3
  fresh-clone path). Companion `install-class-playbook.md` cites parent
  `install-matrix.md`. Decomposed as steward Epic 31 (15 stays done).
  `--module skf` refused as a non-goal.
- **2026-09-06** — Realized. Steward Epic 31 shipped 3/3 (31.1 class-keyed
  playbook, 31.2 class-correct wired-or-not, 31.3 fresh-clone class path) on
  2026-08-24; Spec `spec-bmad-suite-install-class-wiring` re-derived
  `ready → shipped` and this Dream flipped `specified → realized` on 2026-09-06
  (recorded late). The `--module skf` refusal stands (skf stays own-installer,
  custom-module registered). The remaining module wiring is now driven by
  `spec-bmad-suite-lifecycle` (new, 2026-09-06) — its adoption register, not
  this Dream, decides what else gets wired.

## 2026-09-17 — The whole bmad-suite is wielded, kept current, and carried into the foundry (folded from bmad-suite-lifecycle)

# The whole bmad-suite is wielded, kept current, and carried into the foundry

## The Dream

PyForge runs on the BMAD Method, but it wields only part of the suite it packages. Thirteen
SelfExplainML `bmad-suite` members are recipe-built, channel-published, pixi-pinned and
pipeline-truth-current; four of them (TEA, bmad-builder, utility-skills, manticore) have never been
provisioned, two are "documented" or "n/a" by class, one (eval-quality) is pinned with no runner,
and the ones that are wired carry a tail from the 6.12 era shift — twenty-one deprecated shims,
eight rulebooks nothing loads, ten CIS skills one revision behind, seven installer-owned skill files
edited in place, a harness policy that still names a shim.

The dream has three faces and one owner:

1. **Every suite tool has a wielder.** Each of the thirteen members has a recorded verdict — wield
   or skip — and, when wielded, a named station that reaches for it in its daily work: Herald renders
   station videos through manticore and writes release notes through `bmad-os-changelog`; Doctor
   reaches for `bmad-os-root-cause-analysis`; Warden runs `bmad-os-review-pr` and TEA's
   `tea-test-review` as advisory lenses; Scribe keeps docs through `bmad-os-diataxis`; Atlas builds
   MCP faces with `mcp-builder`; Marshal triages with `bmad-os-gh-triage`; Steward provisions all of
   it by install class and authors modules through bmad-builder beside skill-forge.
2. **The estate stays current per release, by a runbook not by heroics.** One cadence — Doctor
   detects the lag, Steward applies the core (`steward upgrade bmad-core`), Marshal runs the era
   round, Mason refreshes the suite recipes, Steward flips the statuses — and the prerelease channel
   is its optional dry-run.
3. **The BMAD estate is cutover-ready.** Before `python-foundry` opens, every prerequisite the
   cutover assumes about `_bmad/`, `.claude/skills/`, `_bmad-output/` and the loop homes is true and
   checked: no shims, no rulebooks, no ungoverned in-place edits, skf by its own installer, memlogs
   that re-render their Specs without loss.

## Grounding — verified state (2026-09-06 research pass)

**The suite, per `steward suite pipeline-truth` (13/13 recipe = channel = installed):**

| Member | Class | Wired today | Verdict (operator, 2026-09-06) |
|---|---|---|---|
| `bmad-method` 6.12.0 | installer-tree | present | Substrate. Only the era tail remains. |
| `bmad-loop` 0.11.1 | runner-home | provisionable | Marshal wraps it (never absorbs). |
| `bmad-module-skill-forge` 2.1.0 | own-installer (custom-module registration kept) | present, 16 skills | Every station; pin `v2.1.0` — npm 2.1.0 tarball `src/` is byte-identical to tag `v2.1.0` (337 files, verified this pass). |
| `bmad-creative-intelligence-suite` 0.3.2 | module | wired, one revision behind | Herald/Scribe. Re-provision (15 `--project-root` lines across 10 `SKILL.md`). |
| `bmad-eval-quality` 0.2.0.dev0 | cli | runnable, no runner | **Pilot unblocked**: the twin-run contract measures the reviewer (Story 45.2). |
| `bmad-method-test-architecture-enterprise` 1.24.0 | module | unwired | **Full adoption**: TEA's nine `bmad-testarch-*` workflows replace the repo generator; `tea-test-review` becomes a Marshal review lens and a Warden advisory. |
| `bmad-builder` 2.2.2 | module | unwired | **Provisioned beside skf** for agent/workflow authoring. Hazard: never `--legacy-dir`, never `cleanup-legacy.py`. |
| `bmad-utility-skills` 2.0.0 | module | unwired | **Adopted**: ten `bmad-os-*` skills routed to Herald, Doctor, Warden, Scribe, Marshal, Steward. |
| `bmad-manticore` 3.1.0.dev0 | module (`--custom-source`) | unwired | **Adopted for Herald** in a dedicated studio folder (its upgrade wipes the studio's `_bmad/` + `_bmad-output/`). |
| `bmad-labs-skills` 1.0.0.dev0 | plugin-path (consent) | documented | **Skill-by-skill**: `mcp-builder` → Atlas, `slides-generator` → Herald, `multi-repo-git-ops` → Marshal, `release-please` → Steward. Never the whole marketplace. |
| `bmad-module-template` 0.1.0 | scaffold | n/a | Catalog row (upstream LICENSE is placeholder text). |
| `bmad-dashboard` 1.2.2.dev0 | vscode-extension | runnable | Marshal's opt-in dev-machine surface; never the console. |
| `mybmad-dashboard` 0.1.0.dev0 | vscode-extension (a Next.js app) | runnable | Opt-in operator view only; never into the platform (its own Postgres and auth rival `/console/`). |

**The 6.12 era tail, verified at HEAD `35ddefbbc5`:** 21 deprecated shim dirs installed (20 in
`v6-shims/` plus `bmad-generate-project-context`, which 6.12 ships as `lifecycle: shim` under `plan/`
— not orphaned); `installShims: true`; marshal `harness_bmadloop.py:328` still names
`bmad-dev-auto` and all eight loop-home policies carry it; steward's apply has no `--no-shims`; the
retired-ID guard lacks `bmad-checkpoint-preview`; eight `project-context.md` rulebooks (976 lines)
survive with four live readers; `architecture-bmad-infra.md` is pinned to 6.11.0; steward's ledger
reads `backlog` for Stories 14.6–14.8 whose code is on main; `spec-bmad-suite-install-class-wiring`
and `spec-bmad-suite-metapackage` are shipped in fact but not in status.

**The open register:** 73 distinct open BMAD-METHOD items across the fleet (marshal Epic 30, the
core-upgrade Spec's five open questions, the steward customization inventory C9/C11/C13, 18 doctor
and 12 steward deferred-work entries on the drift detectors and the suite duty, the marshal
bmad-loop coupling entries, five horizon watches). The Spec's `open-items-register.md` partitions
them: story, deferred-work entry, or watch.

**The cutover's assumptions about this estate** (`spec-python-foundry-cutover`, spine `fnd:AD-5`,
`AD-12`, `AD-20`): the seed is Dreams plus memlogs only; every Spec, spine and epic is re-rendered in
foundry; adapters under `.claude/skills/` are generated, never copied; `_bmad/`, `_bmad-output/projects/`
and `docs/dreams/` move as one unit; the eight loop homes are re-provisioned by the flip with no loop
running. Seventeen prerequisites follow from that text; the live violations today are the shims,
the rulebooks, the seven in-place skill edits (five ungoverned by any spec surface), skf's
dual-installer state, and memlog fidelity (Story 44.13, `backlog`). Eleven gaps nothing tracks:
`_bmad/**` is missing from Epic 44's surface, Epic 44 has no dependency on the era work, the
foundry stack table has no `bmad-*` floor row, `PROJECTS.md` has no cutover layout, loop-home
readiness is undefined, and the `frozen-path-changed` and render-HALT detectors do not exist.

## Decisions locked (operator, 2026-09-06)

- **Shims go now**, not at v7: the era-alignment constraint that kept them (and the harness
  discriminator `bmad-dev-auto`) is retired by memlog; steward gains `--no-shims`; the same-version
  apply that drops them is the first live exercise of the core-upgrade CAP-6/7/8 path.
- **Adopt** utility-skills, manticore (Herald), labs-skills skill-by-skill, and unblock the
  eval-quality pilot. **BMB beside skf.** **TEA fully**, retiring `_bmad/scripts/bmad_tea_playwright.py`
  and its two meta-tests behind an equivalence check.
- **skf stays registered** as a bmad-method custom module (its `bmad-help` routing for fifteen skills
  is worth CAP-7's cost); the release catalog pins `v2.1.0`.
- **Full planning chain** (Spec → PRD → spine → epics) so the adoption epics can be drained by
  Marshal, one per station.
- **mybmad-dashboard** stays out of the platform.

## Whose job this is

Steward owns this Dream: provisioning by install class, the core apply, the suite pipeline and the
cutover chain are all its duties, and the adoption register is a steward companion. Every other
station wields, and the Spec relays one story per wielding station: Marshal (harness flip, TEA
replacing its generator, spec-surface widening, loop-home readiness), Doctor (suite drift 7→13,
the two missing detectors, `root-cause-analysis`), Warden (advisory lenses), Herald (manticore
studio, changelog, slides), Scribe (docs skills), Atlas (`mcp-builder`), Mason (the eval-quality
Windows variant recipe). The Charter's outcome/mechanism rule holds: the owner of the outcome
writes the story; the owner of the mechanism owns the verb it calls.

## What it looks like when real

**Adoption register (CAP-1).** One companion table, thirteen rows: verdict, wielding station,
provisioning path, hazards, status. It supersedes the channel-product Spec's "never wire-everything"
posture and closes the one-front-door row-6 triage. A member's wiring changes only by changing its row.

**Module wave (CAP-2).** `steward provision --module utility-skills`, `--module tea`, `--module bmb`
land their skills in `.claude/skills/` with manifest sections; CIS is re-provisioned; the retired-ID
guard and the integrity meta-tests stay green; nothing is hand-copied.

**Station routing (CAP-3).** Each adopted skill has exactly one wielding station, recorded in that
station's persona skill and the AGENTS.md managed block — never in CLAUDE.md.

**TEA (CAP-4).** Every station's `planning-artifacts/test-architecture.md` is produced by TEA's
workflows; `tea-test-review --base origin/main --min-score N` runs as a Marshal review lens and a
Warden advisory finding; the repo generator, its two meta-tests and its two pixi tasks are retired
only after an equivalence check shows the TEA output covers what the generator did.

**Manticore studio (CAP-5).** Herald's studio lives outside the repo's `_bmad/` root, provisioned
with `--custom-source`, configured in the studio's own `_bmad/custom/config.toml`; the first station
video renders from the deck's speaker notes; the `.mp4` is a gitignored build artifact.

**labs-skills (CAP-6).** Exactly the consented skills, installed by name, each with a register row.

**eval-quality pilot (CAP-7).** `evals/review-catches-planted-defect/` runs under
`eval-quality-smoke`, `eval-quality-review-twin-run` and `eval-quality-review-replay` with a
per-trial budget ceiling; never a PR gate.

**Release cadence (CAP-8).** One runbook: detect → apply → align → refresh → flip, with the
`@next` prerelease as an optional rehearsal (`6.12.1-next.0` is on npm today, unexercised).

**Cutover readiness (CAP-9).** One checklist with an owner per prerequisite; the gaps relayed to
the cutover chain by memlog; the gate is "every line green" before Story 44.3 opens the foundry.

**Shim retirement (CAP-10).** Harness → `bmad-build-auto`, eight homes re-rendered, callers glossed,
guard widened, one `--no-shims` apply, `installShims: false`.

## What is real

Everything above is planning as of 2026-09-06: the Spec, PRD, spine and epics minted in this
session, nothing provisioned, nothing retired. The 6.12 core is applied (PRs #1074, #1076); CAP-6..8
of the core-upgrade Spec are on main, unit-tested; the suite is 13/13 current on the channel.

## Constraints

- Provision by install class only — no hand copies into `.claude/skills/`, never `cleanup-legacy.py`,
  never `bmad-module-skill-forge uninstall` (it would delete every skill directory).
- The manticore studio is a separate root; its upgrade ritual never touches this repo's `_bmad/`.
- TEA and eval-quality verdicts are advisory (Warden) or lenses (Marshal review); Warden's gate stays
  the sole PR verdict.
- Customizations live in `_bmad/custom/**` or are re-applied by the core-upgrade CAP-8 path; every
  in-place edit of an installer-owned file is under a spec `surface:`.
- Retired-name sweeps gloss shipped history (decks, `docs/specs/`, `pixi.toml` comments) rather than
  rewriting it; live docs and code lead with the live names.
- Amended by this Dream (each by a memlog decision on the owning Spec): channel-product
  "never wire-everything" → "wire by adoption register"; era-alignment "shims stay through v7" and
  "TEA adoption is optional" → retired; one-front-door row-6 triage → closed.
- Parallel agents address projects by physical path with `BMAD_ACTIVE_PROJECT` per invocation; the
  ledgers change only through their tools.

## Non-goals

- First-install of bmad-method (Epic 14 upgrades an installed core; a fresh install is the foundry's).
- Refreshing suite conda recipes (the CFE factory flow, Mason).
- Integrating mybmad-dashboard into the platform, provisioning `bmad-module-template`, or installing
  the whole labs-skills marketplace.
- Upstream pull requests (skf `marketplace.json`, the sprint-plan key fix, the skf uninstall bug) —
  each needs an explicit ask.
- The cutover itself (Epic 44) — this Dream makes it possible, it does not perform it.

## Kinships

- [`bmad-method-core-upgrade.md`](bmad-method-core-upgrade.md), [`bmad-method-version-drift.md`](bmad-method-version-drift.md),
  [`bmad-611-era-alignment.md`](bmad-611-era-alignment.md) — the per-release triad this Dream's cadence
  runbook orders; shim retirement and `--no-shims` land as new capabilities on the first and third.
- [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md), [`bmad-suite-install-class-wiring.md`](bmad-suite-install-class-wiring.md),
  [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md), [`bmad-module-provisioning.md`](bmad-module-provisioning.md) —
  the packaging and provisioning machinery this Dream drives to completion.
- [`bmad-eval-quality.md`](bmad-eval-quality.md) — its CAP-2 pilot is unblocked here.
- [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) and the `python-foundry` cutover chain
  (`spec-python-foundry-cutover`, Epic 44) — the estate this Dream makes cutover-ready.
- [`one-front-door.md`](one-front-door.md) — its own/route/triage survey; row 6 closes here.
- [`herald-pitch.md`](herald-pitch.md) — the named manticore consumer.
- [`conda-forge-expert-rebuild.md`](conda-forge-expert-rebuild.md) — the skf-driven rebuild that the
  authoring path decision (BMB beside skf) must not disturb.

## Realization log

- **2026-09-06** — Seeded and specified in one session after a fleet-wide survey (seven listed items
  verified, 73 open items registered, thirteen members catalogued, seventeen cutover prerequisites
  derived). Operator decisions locked (see § Decisions). `bmad-spec` derived
  `spec-bmad-suite-lifecycle` under pyforge-steward (CAP-1..10, companions `adoption-register.md`,
  `release-cadence.md`, `cutover-readiness.md`, `open-items-register.md`; status `ready`), followed
  by the PRD, the epic-altitude spine, and hand-authored epics across eight stations (steward 46/47
  + Story 14.9, marshal 30.5 + Epic 31, doctor 20, warden 11, herald 18, scribe 7, atlas 24, mason 14).
  Implementation begins next session with the era tail (Epic 30, 14.9, 30.5, the `--no-shims` apply).
- **2026-09-07** — Story 47.1 re-ran the live `steward upgrade bmad-core --json`
  pre-flight against this repo's own state and corrected `cutover-readiness.md`'s
  P7/P13 rows: the P7 evidence pool grew from the epic's assumed seven files to a
  live **nine** (eight `local_customizations` + one `locally_modified`, one
  additional skill-file edit having landed 2026-09-06→09-07); P13's "5
  ungoverned" claim was independently re-derived against all nine and held
  exactly, even as the total pool grew — recorded as two separate, dated facts.
  Governing the five ungoverned files remains marshal Story 31.4's job.

## 2026-09-17 — One conda metapackage installs the whole SelfExplainML bmad-suite at latest (folded from bmad-suite-metapackage)

# The bmad-suite metapackage

## The Dream

An operator who wants **every** SelfExplainML channel product — all 13 packages from
`install-matrix.md` — should be able to run one install:

```bash
pixi add bmad-suite   # or: conda install -c SelfExplainML bmad-suite
```

and get a coherent, version-locked bundle whose own version records **when the suite was
refreshed**, with each member pinned to the **latest upstream release** appropriate to that
member's registry class (GitHub tag, npm, PyPI — never a stale npm stub for GitHub-canonical
packages).

Today the channel sells 13 individual recipes; `pixi.toml` carries 11+ separate pins; drift
between members is invisible until a human compares the channel listing to GitHub. The
metapackage is the **product boundary** — the thing that says "this fleet snapshot is
2026.9.1" while member recipes continue to bump independently.

## Grounding

- **Channel catalog (2026-09-01):** 13 packages on SelfExplainML — `bmad-method` plus 12
  suite members including `mybmad-dashboard` (bmad-ui only today).
- **Doctor gap (same session):** ambient drift watches pixi `bmad-*` keys and npm-first;
  misses `mybmad-dashboard` and under-reports GitHub-primary packages (builder, CIS).
- **Existing machinery:** per-member `recipes/<name>/recipe.yaml` with
  `cfe-upstream-registry` + `cfe-upstream-name`; steward `suite pipeline-truth`; CFE autotick
  per recipe — no batch "refresh the whole suite" artifact.

## What it looks like when real

- `recipes/bmad-suite/recipe.yaml` — **noarch metapackage** (`requirements.run` lists every
  member at `>=` the resolved upstream version; no sources of its own).
- `recipes/bmad-suite/suite-members.yaml` — canonical 13-name manifest (single source for
  doctor Story 19.1 watched set and metapackage generation).
- `pixi run -e local-recipes generate-bmad-suite` (or steward duty) — resolves upstream latest
  per member via registry class, writes/updates the metapackage pin block and CalVer
  `context.version`, never hand-edits 13 lines.
- Channel publishes `bmad-suite` alongside members; optional `pixi.toml` feature
  `bmad-suite-full` replaces the long pin block for operators who want the bundle.

## Non-goals

- Replacing individual member recipes (they stay the unit of autotick/build/publish).
- conda-forge submission of the metapackage (SelfExplainML-only, like the other 12).
- Wiring modules (`steward provision --module`) — the metapackage is install-only; provisioning
  stays CAP-3.

## Success signal

`conda install -c SelfExplainML bmad-suite` pulls all 13 members at versions that match
`steward suite pipeline-truth --json` upstream-latest column; doctor's suite drift is quiet
after a metapackage refresh PR merges; the manifest and metapackage version bump in one
reviewable commit.

## Realization log

- **2026-09-01** — Realized in code. Steward Epic 39 shipped the metapackage:
  `recipes/bmad-suite/{recipe.yaml,suite-members.yaml}`, the CFE generator
  (`bmad_suite_metapackage.py` + `build_bmad_suite.py`), pixi tasks
  `generate-bmad-suite` / `build-bmad-suite`, and `bmad-suite 2026.9.1`
  published to the channel (main `e177de648e`; 39.4 CAP-4 pixi feature bundle
  followed).
- **2026-09-05** — First governed refresh: `bmad-suite 2026.9.5` (PRs
  #1059/#1060) — `bmad-eval-quality` seated as a member, `bmad-method
  >=6.12.0`, and `bmad-method-wds-expansion` retired (deprecated upstream,
  absorbed into `bmad-ux`; kept as a catalog row only).
- **2026-09-06** — Status flipped `dreamt → realized` (owed since Epic 39
  closed 4/4 on 2026-09-01); Spec `spec-bmad-suite-metapackage` re-derived
  `in-progress → shipped` the same day.

## 2026-09-17 — Build League and Balanced Product Scorecard (folded from build-league-scorecard)

# Build League and Balanced Product Scorecard

## The Dream

The estate optimizes to **published** measures. Build League and the Balanced Product Scorecard
are operating-model faces (Unifying Strategy Q5, 2026-08-24): we know the rules, and unpublished
metrics do not steer work. Herald (narrative), Atlas (metrics), Marshal (velocity), and Doctor
(SLO burn) consume those rules later. Steward discovery already has owner / `work_class` for the
denominator.

## What it looks like when real

- A published measure set covering **human, agent, and team** dimensions.
- Rules consistent with Q1–Q4: spec coverage, promotion class, Golden Path, Warden-gated
  change, owner on 03.
- A board that is **not** a Canopy CAP — sibling to `pyforge-unifying-strategy`, never CAP-18
  (CAP-18 is hooks in `pyforge-core`).

## What is real

Q5 is **in** the operating model. WFT named the faces and defined no metrics. The operator
scoped 2026-08-24: **scorecard draft is later**; no first-cut measure set in this pass.

## Constraints

- **Never** invent metrics or optimize to unpublished ones.
- **Never** score 01/02 work against 5-tier completeness.
- **Never** treat a Jira key as a quality signal.
- **Never** a scorecard UI capability in the Unifying Strategy chain.

## Open question for the Spec

Answered 2026-09-15. Recorded in § *Operator rulings* below.

1. **operator-measure-set** — which already-counted signals are published, and
   how do we add or retire them without inventing a score?

## Operator rulings (accepted 2026-09-15)

Operator approved the session menu (rows 1–8) and required the catalog to be
**configurable**: each measure can be on, off, or archived; a new source is
an add; a dead source is archived (id kept, never reused). No weights. No
league total. No dashboard in this first epic.

**Human**
1. `warden-verdict` — Warden rung on the PR (Q8 stays the gate).
2. `owner-work-class` — steward discovery `owner` + `work_class` on **03** work.

**Agent**
3. `gate-record-outcomes` — `gate-record.json` command pass/fail per story.
4. `journal-timing` — `journal.json` run/phase timing.
5. `run-cost-usd` — per-run `total_cost_usd`.

**Team**
6. `ledger-throughput` — stories moving to `done`.
7. `detector-pass-fail` — detector / `detectors-ci` pass/fail.
8. `five-tier-completeness` — 8×5 ladder **only** on 03 work. Never 01/02.

States: **on** (may steer), **off** (named, not steering), **archived**
(retired; must not steer; id reserved). First cut: all eight **on**. A new
row starts **off** until the operator flips it. Tables: Spec companion
`measure-catalog.md`.

Do not invent composites. Do not treat a Jira key as quality. Do not flip
Epic 44 `blocked` keys. Hub Outcome Guards **read** this catalog later;
they are not this epic.

## Non-goals

- A dashboard or league table in this first epic.
- Replacing Warden as the PR quality gate (Q8).
- Inventing weights or a single composite score.
- Implementing Hub Outcome Guards here.

## Realization log

- **2026-08-25** — Sibling Dream parked so Q5 is not an unbounded open question on the Canopy
  SPEC. Chain: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/`
  (`status: draft`). Measures remain unpublished until the operator drafts them.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA-B5 / § C13/C14). Still correctly parked; the measure set stays the operator's. Proposed unblocking move that publishes no metric and violates no Never: a **measure inventory** — a read-only enumeration of every signal the estate already counts, with `file:line` per source (five-tier completeness 8×5 at `five_tier.py:17-33`, the ~30 detector pass/fail vector, ledger throughput, `gate-record.json` per-story command outcomes, `journal.json` run/phase timing, Warden verdict rungs, `driver.py:198`'s per-run `total_cost_usd`, steward discovery's `owner`/`work_class`) — so the operator selects rather than invents. Noted: [`intelligence-hub.md`](intelligence-hub.md)'s **Outcome** Guard category is the one category the repo lacks entirely and is blocked on this Dream, which puts a parked Dream on a second Dream's critical path.
- **2026-09-15** — Operator approved the eight already-counted signals as the
  first published set, with on/off/archived config and add/archive of sources.
  Spec `ready`. Steward Epic **62** (62.1–62.3 `backlog`) is the marshal
  dispatch home. Dream `dreamt` → `specified`. Q5 on
  [[pyforge-unifying-strategy]] cites this catalog.

## 2026-09-17 — DB-GPT's agentic, file-hungry model integrates into a stateless Django control plane (folded from db-gpt-django-plugin)

# DB-GPT's agentic, file-hungry model integrates into a stateless Django control plane

## The Dream

DB-GPT is built around agentic personas and data-driven LLM operations —
text-to-SQL, data chat, multi-agent workflows (AWEL) — and it assumes it
owns its own filesystem for vector indices and session state. That
assumption is exactly what a 12-factor, `cookiecutter-django`-shaped
deployment refuses to allow: no local session-state paths, no
per-instance DuckDB files that vanish on redeploy, no state that isn't
recoverable from a shared store. The dream is a small set of named
integration patterns that let a project pull in DB-GPT's real
capabilities — SQL generation, data chat, multi-agent orchestration —
while forcing every piece of DB-GPT's own state through one shared
PostgreSQL control plane instead of the local filesystem it defaults to,
plus a lighter-weight path for projects that don't need the full agent
server at all.

## What it looks like when real

Three named patterns:

**Pattern A — ASGI Reusable App (API mount, tightly coupled).** A Django
data migration provisions an isolated `dbgpt_schema` namespace inside the
SAME PostgreSQL database as the Django project (`public` owned by
Django's ORM, `dbgpt_schema` owned by DB-GPT's own Alembic engine — same
shape as the Langflow ASGI pattern's schema split). DB-GPT is configured,
via environment variables alone, to bypass every local session-state path
it would otherwise default to (`~/.dbgpt/logs`, local DuckDB) and persist
all conversational/agent state into that schema instead. A custom ASGI
dispatcher in a `dbgpt_integration` Django app intercepts `/api/v1/`
traffic and routes it to DB-GPT's own FastAPI app; Django keeps the rest
of the web traffic.

**Pattern B — Asynchronous Multi-Agent Orchestration (Celery +
microservice, loosely coupled).** DB-GPT runs as its own service in
`docker-compose.yml`, managing its own model worker and API server
processes independently of Django. Django captures a complex data
request (e.g. "run a multi-agent SDLC analysis") and hands it to Redis;
a Celery worker issues the REST call that actually drives DB-GPT's AWEL
task graph, then writes the finished analysis back into Django's own
data model.

**Pattern C — Native DB-GPT SDK (library integration, no server at
all).** For lightweight text-to-SQL or a single agent execution that
doesn't warrant a running DB-GPT server, the `db-gpt` Python package is
imported directly into a Django service/view, initialized at runtime with
Django's own database credentials, and run statelessly — no background
daemon, no separate process.

Realized means: a project can pick a pattern, follow a concrete recipe
for it, and DB-GPT's state — regardless of which pattern — never lands on
a local, per-instance filesystem path that a redeploy or a second replica
would silently lose.

## Constraints

- **The storage rule is the load-bearing constraint, not a nice-to-have**:
  every local session-state path DB-GPT would use by default
  (`~/.dbgpt/logs`, local DuckDB instances) must be disabled/bypassed via
  configuration (`DBGPT_SESSION_STORAGE_TYPE=db`), with all metadata
  forced into PostgreSQL's `dbgpt_schema`. A pattern that lets any DB-GPT
  state fall back to local disk defeats the entire reason for this dream.
- **Pattern A** needs the same schema-isolation discipline Langflow's own
  ASGI pattern needs: Django's ORM never reaches into `dbgpt_schema`,
  DB-GPT's Alembic migrations never reach `public`.
- **Pattern B** adds a network hop (Celery worker -> DB-GPT container)
  DB-GPT's own AWEL orchestration doesn't have when run in-process — a new
  failure mode (timeout, partial multi-agent result) Patterns A/C don't
  carry.
- **Pattern C** is single-shot and stateless by design — it is not a
  substitute for A/B when a real multi-turn agent session or AWEL
  workflow is actually needed.
- Package sourcing is a named constraint, not an afterthought: `db-gpt`'s
  target version is sourced from the Conda Enterprise Core repository
  specifically, not the generic conda-forge upstream — a different
  provenance rule than Langflow's plain `langflow==1.11.2` conda-forge
  dependency.
- Environment surface named for Patterns A/B: `DBGPT_WEB_PORT`,
  `DBGPT_DATABASE_URL` (carrying the same `?options=-c%20
  search_path=dbgpt_schema` shape Langflow's `LANGFLOW_DATABASE_URL`
  uses), `DBGPT_SESSION_STORAGE_TYPE=db`.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied
  architecture brief, immediately after the sibling
  [[langflow-django-plugin]] Dream (same shared-PostgreSQL-schema
  pattern family, applied to a second agentic LLM tool). Not yet
  researched against this repo's own factory or any specific downstream
  project — no station claimed, no Spec derived, no pattern chosen.
  Owner deliberately left as `guild` (intake, not a terminal owner)
  pending a decision on which project or station this belongs to. Note:
  `docs/dreams/db-gpt-packaging.md` already exists and is a DIFFERENT,
  unrelated Dream (conda-forge packaging of DB-GPT itself, delivered via
  external PR #33883) — this Dream is about consuming DB-GPT inside a
  Django application, not packaging it.
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Operator integration direction:** this dream's Pattern A (pluggable Django application: ASGI mount + schema isolation) is the PREFERRED shape — the host is a cookiecutter-django Django service with FastAPI integration based on [[django-accelerator-framework]]; infra is PostgreSQL + Redis + Kubernetes only; the same-day conda solve spike proved py3.12 co-install feasibility (py3.14 blocked solely by langflow-base's bcrypt==4.0.1 pin — everything must become 3.14-compatible). Other patterns remain fallbacks where pluggability fails.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-08-21** — **DEVIATION: Pattern A → Pattern B for DB-GPT (AD-14 sidecar-fallback trigger, demonstrated).** Story 11-2 (pyforge-steward, spec-python-agent-platform) hit a real, verified pluggability failure: `dbgpt-app` (needed for DB-GPT's FastAPI mount, including the AgenticData text-to-SQL router) pins `fastapi<0.113.0`; `langflow-base` — already resident in the shared `platform-dev` environment since Story 11.1 — requires `fastapi>=0.135.0`. The ranges are disjoint; no `fastapi` version satisfies both, confirmed live by adding `dbgpt-app` to `pixi.toml` and watching `pixi install -e platform-dev` fail to solve with exactly this conflict. Per AD-14 ("sidecar fallback only on demonstrated pluggability failure, Dream first"), DB-GPT moves from Pattern A to this dream's existing **Pattern B** (Celery + microservice, DB-GPT run via `docker-compose.yml` independently of Django) for Stories 11-2/11-3/11-4 — Pattern B was already specified above, not invented for this deviation. Operator decision (2026-08-21): file the fastapi-ceiling conflict upstream with DB-GPT (`eosphoros-ai/DB-GPT`'s `dbgpt-client` extra) — operator-owned, filed by hand, not automated — while proceeding with Pattern B now rather than blocking indefinitely on an upstream timeline with no guarantee; revisit Pattern A if/when upstream relaxes the pin. This is the first time AD-14's fallback clause has actually fired; the operator intends it as a reusable precedent (demonstrated-conflict → Pattern B, dated here first) for future engine integrations on this platform, not a one-off DB-GPT exception. Langflow is unaffected and stays on Pattern A.
- **2026-08-21** — **Operator direction: pattern selection becomes a per-engine config switch, not a hardcoded fork.** Rather than wiring DB-GPT to Pattern B as a bespoke, one-off code path, Story 11-2 builds the pattern choice (A vs. B, per engine) as a configuration seam every future integration on this platform reuses — so reverting DB-GPT to Pattern A later (once the upstream fastapi conflict resolves) is a config change, not a rewrite, and the next engine that hits a Pattern-A pluggability conflict picks up the same switch instead of re-deriving it. This is a platform-level capability, not an 11-2-local implementation detail — formalized as an architecture-spine addition via `bmad-correct-course` before 11-2's spec is re-scoped (see spec-python-agent-platform's Realization/change log for the resulting AD).
- **2026-08-21 (later)** — **A second, independent DB-GPT limitation found, on Pattern B this time: its own metadata store cannot use PostgreSQL, permanently.** Building the real Pattern-B integration, Story 11-2 live-verified the whole registry-driven design working — schema migration, no ASGI mount, a real Celery text-to-SQL round trip through the sidecar (Gemini-backed, live SQL result returned) — but found `dbgpt-app` 0.8.1 structurally cannot wire its own `service.web.database` metadata store (chat history, knowledge/RAG, flow/plugin configs — real state, not disposable cache) to Postgres: connector-type rejection, a SQLite-only migration path, and MySQL-only `TEXT(length)` SQLAlchemy columns that fail real PostgreSQL DDL. Operator decision: accept SQLite behind a dedicated Kubernetes `PersistentVolumeClaim` as the *permanent* architecture for this one store — not the "interim" label Story 10.5 gave its own volume-backed fix — recorded as a bounded exception to AD-6 (statelessness) in `spec-python-agent-platform`'s architecture spine, narrowly scoped to `dbgpt-app`'s own metadata store, no other engine or component. The PVC still satisfies AD-6's real guarantee (state survives redeploy, never silently lost); the cost is that this one container stays a singleton, not horizontally replicable. Operator files the Postgres-support gap upstream with `eosphoros-ai/DB-GPT` directly (AD-9) — real dialect-portability work, not bankable as a near-term fix, so not gated on. Same shape of decision as the fastapi/Pattern-B deviation above: name the upstream engine's real limitation, record a dated bounded exception, keep moving rather than block the platform on someone else's codebase.

## 2026-09-17 — A new contributor or agent is productive on this repo without tribal knowledge (folded from developer-machine-bootstrap)

# A new contributor or agent is productive on this repo without tribal knowledge

## The Dream

Getting productive on this repo today means reading CLAUDE.md, the skill docs, and enough of
this repo's own conventions (pixi environments, the `local-recipes` vs per-station env split,
the BMAD multi-project marker/symlink dance, which `pixi run -e <env> <task>` invocation does
what) to avoid the documented footguns — none of it wrong, all of it currently living only as
prose a new contributor or a freshly-spun agent has to read and internalize by hand, with no
single command that checks "is this machine/checkout actually set up right" or scaffolds the
parts that are mechanical rather than judgment calls. `steward init`/`setup`/`doctor`-adjacent
tooling would make the mechanical parts of onboarding a command instead of a reading assignment
— shell/PATH setup where relevant, a repo-state self-check, and a scaffold for anything a fresh
clone or a new sibling repo needs before its own tooling works. Framed as a `practice`, not a
`dream`: onboarding never reaches a terminal "done" the way a feature does — it degrades every
time the toolchain changes and has to be re-exercised, the same shape [[packaging-factory]]
already carries in this repo.

## What it looks like when real

- A single command an operator (or a freshly-spun agent session) can run to confirm the checkout
  is in a working state — pixi environments resolvable, the BMAD marker/symlinks agree with the
  current project (composing with [[bmad-switch-scope-enforcement]] once it exists), no dangling
  worktree cruft — rather than discovering a gap mid-task. Emits `--json` for the same reason
  every other check in this repo does (`fleet-picture --json`, every detector's `--json`): a
  self-check that only prints prose can't be composed into a preflight another tool calls.
- Whatever shell/PATH setup this repo's own tooling benefits from (if any is found to be
  needed — see "What is real" below) is a single idempotent, delimiter-bounded write, not a
  hand-edited rc file.
- A scaffolding step for onboarding a NEW sibling repo into this repo's own conventions, if that
  pattern recurs (this repo already has at least one sibling project referenced in prior work,
  `conda-forge-tracker`) — capturing whatever's mechanical about wiring a new repo in.

## What is real

Nothing built yet, and unlike [[bmad-switch-scope-enforcement]] and
[[scratch-worktree-lifecycle]], this Dream has no specific already-bitten incident behind it —
no local getting-started doc exists, and no `init`/`shell-init`/`bootstrap`-shaped tooling exists
in `pyforge-steward` today (checked directly: the package has no module by that name). This is
the most purely aspirational of the three Dreams captured in this batch — a real, plausible gap,
not yet a documented pain point the way DW-1-4-2 or this session's own repeated
`git worktree add` toil are.

A sibling org's `developer-machine-bootstrap` dream (`wf-dev-cli`'s `commands/shell_setup.py`,
`shell_init.py`, `setup.py`, `init_cmd.py`) is considerably larger: managed shell-rc block
injection, a `shell-init` function for env/pixi discovery, a declarative or script-based bootstrap
sequence, and stack-detection scaffolding for Node/Maven/Gradle/Go/Rust/Ruby/.NET repos —
building toward a `pyforge.toml`-equivalent config file that also does not exist in this repo yet.
Most of that surface assumes a multi-language, multi-repo enterprise estate this repo isn't; the
`type: practice` framing and the general "make the mechanical parts of onboarding a command"
shape are what transfer.

## Constraints

- **Never own judgment calls.** A self-check reports what's wrong; it does not silently "fix" a
  developer's deliberate local configuration choice.
- **Idempotent by construction**, matching this repo's own atomic-write conventions (`os.replace`,
  delimiter-bounded rc blocks) rather than append-and-hope.

## Non-goals

- **Not a GUI wizard.** CLI only, matching every other Steward verb.
- **Not stack detection for languages this repo doesn't have.** No Node/Maven/Gradle/Go/Rust/Ruby/.NET
  scaffolding — this repo is Python/pixi, and generalizing beyond that is speculative until a
  second-language need actually appears.
- **Not deciding what belongs in a `pyforge.toml`-equivalent config file** — that decision belongs
  to whichever Dream first needs one ([[scratch-worktree-lifecycle]] does not currently need one,
  scoped to a single mono-repo).

See "Full feature audit" below for the per-feature reasoning behind these and every other
capability the source dream carried that this one doesn't.

## Full feature audit against `developer-machine-bootstrap`

Every capability the sibling org's dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| `steward init` (managed, delimiter-bounded shell rc block) | **Included, hedged** | Kept as a bullet, but not committed to as a concrete verb — no evidence yet that this repo's own tooling actually needs rc-file changes the way a bespoke wrapper might (`pixi run`/`pixi shell` don't require them). A future Spec should confirm the need before building this specific piece. |
| `steward shell-init` (emit a shell function to stdout for `eval`, env/pixi discovery + routing) | **Omitted, not named** (2026-08-14 audit) | A distinct mechanism from `init` — emit-and-eval vs. write-to-rc-file — collapsed into one vague bullet in the first draft. Named here explicitly so a future reader can decide whether it's needed independently of `init`. |
| `steward setup` (declarative/script-based bootstrap sequence, idempotent + resumable) | **Included, hedged** | Kept as "a scaffold for anything a fresh clone... needs," but the sequence-runner design (declarative vs. script mode, resumability) wasn't carried over — only the general shape. |
| `steward initrepo` (stack detection, scaffold `pyforge.toml`) | **Included, narrowed** | Kept as "a scaffolding step for onboarding a new sibling repo," explicitly stripped of multi-language stack detection (see Non-goals). |
| Stack-detection heuristics by marker file | **Omitted, overbroad exclusion** (2026-08-14 audit) | The first draft dismissed the whole marker-file-detection *mechanism* along with the multi-language *scope* it served. A narrower version — "is this a pixi project: does `pixi.toml` exist, does the environment resolve" — is still single-language and plausibly in-scope; it was never called out as a distinct, retained capability. Left as an open question rather than folded in outright, since no concrete need for it has been observed yet (unlike `scratch-worktree-lifecycle`'s `start`/`ls`/`clean`, which map onto directly-observed toil). |
| PowerShell fallback | **Omitted, unverified** | Not mentioned. Defensible on the source's own terms (it treats PowerShell as non-primary too), but this repo has never actually confirmed whether any contributor works on Windows — an assumption, not a checked fact. |
| `argcomplete` tab completion | **Omitted, unverified** | Same repo-wide gap noted in [[scratch-worktree-lifecycle]]'s audit — no PyForge CLI currently registers tab completion; adding it here would set a precedent this one Dream shouldn't decide alone. |

## Kinships

[[pyforge-steward]] (the estate; this Dream's natural home per the same developer-ergonomics
identity as [[scratch-worktree-lifecycle]]) · [[packaging-factory]] (the existing `practice`-type
precedent this Dream's frontmatter follows) · [[scratch-worktree-lifecycle]] (a sibling capability
captured in the same investigation, not directly dependent on this one)

## Realization log

- **2026-08-14** — Dream captured, alongside [[scratch-worktree-lifecycle]] and
  [[bmad-switch-scope-enforcement]], while evaluating a sibling org's dream catalog for PyForge
  fit. Deliberately flagged as the least evidence-backed of the three: no local incident, no
  existing partial tooling, no documented pain point — captured because the gap is plausible and
  the sibling org's shape is a reasonable starting blueprint, not because anything has been bitten
  by its absence yet. Ownership assigned to Steward, matching the source dream's own label and
  steward's established developer-ergonomics identity, with no competing claim found from any
  other station.

- **2026-08-14 (same day)** — Feature-parity audit against the source dream: JSON output added to
  the self-check bullet; `shell-init` and marker-file stack detection named explicitly (they were
  present only implicitly, folded into vaguer bullets, in the first draft). Every source feature
  now carries an explicit disposition in "Full feature audit" rather than living only in a
  conversation transcript.
- **2026-09-09 (fleet readiness pass)** — `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, rows stA-B4 / § 2.3 **C17**. Epic 17 is 2/2 `done` and the four verbs are live (`pyforge/steward/cli.py:51-54`, `:89-101`, `:166`), but the Spec's own success signal — a recorded clean-container run, nothing → `validate-fast`, zero improvised steps — **has never run**, and `spec-17-2` is a 54-line contract husk with no dev log. The owning Spec moves `ready` → `in-progress`. **Decision: the proof runs as a dedicated CI lane against `python-foundry` after Story 44.3 — not podman-in-podman, and not against `local-recipes`, which Story 44.10 archives.** Proving a bootstrap against the repo that is about to stop being the working tree buys nothing, and a dedicated lane avoids the privileged-nesting surface podman-in-podman would add for one job. This places the Dream **`foundry-side`**. Status unchanged in this pass.

## 2026-09-17 — Firewalled Factory (folded from enterprise-airgap)

# Enterprise air-gap — everything works where the internet doesn't

## The Dream

The whole factory — packaging, intelligence, gates, decks — runs inside
regulated, air-gapped enterprises as naturally as it runs here: every outbound
dependency routable through JFrog Artifactory / internal mirrors, every
capability offline-first by design, credentials handled without leakage. Not a
port; a posture: **air-gapped is the default deployment story, not an
afterthought.**

## What is real (the core)

- **`docs/explanation/enterprise-deployment.md`** + `docs/reference/pixi-config-jfrog.example.toml` —
  the deployment doctrine.
- **Runtime-driven routing** in `_http.py`: truststore + JFrog/GitHub/.netrc
  auth chain — env-vars only, never committed config (CFE v6.0/v7.0).
- **Air-gap-by-design decisions** across the stack: atlas's
  `current_repodata.json` choice (explicitly JFrog-reusable), offline-safe read
  CLIs, offline-safe deck bundles, the Pyodide/WASM atlas compilation
  ([[pyforge-atlas]] G1).

## The frontier

- **[[presenton-pixi-image]]** and **[[deckcraft]]** — the two air-gapped
  application expressions, both unbuilt.
- **Warden's registry perimeter** ([[pyforge-warden]] ring 2): block/allow lists
  on Artifactory — quarantine before the firewall.
- **Closed (2026-09-09)** — the `JFROG_API_KEY` cross-resolver leak (the header
  attaching to every outbound request regardless of host) is **fixed**:
  `_http.py:508` gates `X-JFrog-Art-Api` on `is_configured_host`, with regression
  coverage in `tests/unit/test_http_jfrog_host_gate.py`,
  `test_dependency_checker_auth_host_gate.py` (including "never sent to an
  explicitly named public channel") and `test_inventory_channel_auth_host_gate.py`.
  ([[pyforge-doctor]] found it; [[pyforge-steward]] still owns the key lifecycle.)
- **Deployment & install operations** (bundles, OpenShift, mirrors) are the
  **Steward's** station ([[pyforge-steward]], adopted 2026-07-23).
- Offline bundle format for the whole operating model ([[pyforge-genesis]]
  behind a firewall) — kinship with [[sentinel]]'s §40 Airgap Bundle & Install.

## Kinships

- **[[miniforge-installer]]** (mason) — **reciprocal, recorded 2026-09-09.** Its activation
  trigger is *steward-owned and un-watched*: "steward's enterprise-airgap / Story 12.3 work
  surfaces a private-channel-locking need for a Python distributable." The socket already
  exists and is empty by design —
  `src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py:54`,
  `SUPPORTED_DISTRIBUTABLES: dict[str, DistributableBackend] = {}`
  ("Empty by design (Story 9.2). External installers register later."). So whoever runs CAP-3's
  mirror exercise or Story 12.3's air-gap parity check must also decide whether a Python
  distributable needs private-channel locking, and tell mason if it does — nothing on the mason
  side watches for it. *(Fleet readiness 2026-09-09, mason-E1 / Class D D11; the reciprocal half
  is a note on `spec-enterprise-airgap`'s memlog.)*

## Realization log

- **2026 (CFE v6.0→v7.0)** — enterprise routing shipped runtime-driven.
- **2026-07-23** — Dream retro-seeded from the deployment doc + the pattern's
  presence across atlas/warden/presenton/deckcraft.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C2). The host-gate fix verified live (`_http.py:508` plus five regression-test files); § *The frontier*'s "Known health issue" bullet was stale, security-shaped text and is closed. **Still unexercised:** CAP-3's success clause ("pipeline phases run against a JFrog remote-repo mirror unchanged") has no recorded run — realization-gate partial, placed `foundry-side`. Status stays `realized`.

## 2026-09-17 — Django, Langflow, and DB-GPT scale as isolated containers behind one gateway (folded from enterprise-multi-agent-orchestration)

# Django, Langflow, and DB-GPT scale as isolated containers behind one gateway

## The Dream

The sibling [[asgi-multiplexer-monolith]] Dream folds Django, Langflow, and
DB-GPT into one process for latency; this Dream is its structural opposite
— the microservices answer to the same three-framework combination,
chosen specifically BECAUSE the monolithic path may be structurally
unviable (Langflow and DB-GPT's own FastAPI/SQLAlchemy dependency trees
can conflict badly enough that co-locating them in one Python environment
just doesn't solve). Each framework runs in its own container, isolated
by design, with one edge gateway (Traefik) doing path-based routing so a
single public hostname still fronts all three — and Celery/Redis in
between so long-running LLM/agent work never blocks Django's own request
cycle. The point is horizontal scalability and blast-radius containment
(one container crashing doesn't take the other two down) traded against
the network hop the monolith avoids.

## What it looks like when real

**Routing layer — SUPERSEDED 2026-08-14 (see § Realization log).** As
seeded, this Dream specified Traefik prefix-routing over `docker-compose`
to per-engine container ports (`/langflow` → 7860, `/dbgpt` → 8000 with
the prefix stripped, everything else → Django on 5000) with no port
published to the host, declared by `traefik.enable=true` + `PathPrefix` +
`stripprefix` labels on cookiecutter-django's own Traefik-fronted
production compose file. The operator's same-day infrastructure ruling
(PostgreSQL + Redis + Kubernetes only) replaced that mechanism with a
Kubernetes Ingress / OpenShift Route in front of one Service; realized
through [[python-agent-platform]], whose live edge is
`src/platform/deploy/charts/platform/templates/ingress.yaml` and
`src/platform/deploy/overlays/ocp/chart/templates/route.yaml` (pap:AD-11).
The paragraph is retained as the record of the option that was not taken;
it is **not** a description of anything built.

**Orchestration layer — Django dispatches, Celery executes, nothing
blocks.** Django handles UI/user input only; a long-running LLM/agent task
goes to Redis and a Celery worker picks it up, talking to Langflow/DB-GPT
over the internal Docker network (not through the public Traefik edge) —
mirrors the sibling Dreams' own "Pattern B/D" async-orchestration option,
but as the ONLY path here, not one of several.

**Data layer — the same three-schema PostgreSQL split, now owned by
independent containers.** `public` (Django), `langflow_schema`,
`dbgpt_schema` — identical schema-isolation contract to both
[[langflow-django-plugin]] and [[db-gpt-django-plugin]], but each schema's
owning framework now runs in its own container rather than sharing
Django's own process.

**Statelessness — every container is genuinely ephemeral.** No container
in the fleet keeps state that matters on its own local disk — local logs,
DuckDB files, local cache directories are all disabled or treated as
throwaway; conversational memory, agent configuration, and session data
all persist to PostgreSQL, so any container can be killed and replaced
without losing anything.

## Constraints

- **This is a DIFFERENT choice from the monolith Dream, not a fallback
  built the same way twice.** The decision between this and
  [[asgi-multiplexer-monolith]] is real engineering tradeoff (blast-radius
  containment + independent scaling vs. lower latency + one process to
  operate), not a default — whichever is chosen should be chosen on
  purpose, with the dependency-conflict feasibility check from the
  monolith Dream as one deciding input.
- **DB-GPT's own container needs a custom build**, not an off-the-shelf
  image (unlike Langflow, which ships `langflowai/langflow:1.11.2`
  directly) — its dependency chain sources from the Conda Enterprise Core
  repository specifically, the same constraint the sibling Dreams name,
  now expressed as a Dockerfile requirement rather than a pip/conda
  environment requirement.
- **No internal AI-engine port is ever exposed to the host** — the
  isolation intent survived the mechanism change (superseded 2026-08-14);
  today it is carried by one Service behind the chart's Ingress/Route, not
  by Traefik labels.
- **Statelessness is a hard requirement for horizontal scaling to mean
  anything**: if any container silently accumulates local state, adding a
  second replica of that container produces inconsistent behavior instead
  of more capacity — the "all state in PostgreSQL" rule isn't optional
  once more than one replica of anything exists.
- Environment surface named (shared `.env`, extending cookiecutter-django's
  existing `.envs/.production/` convention): `LANGFLOW_DATABASE_URL`,
  `DBGPT_DATABASE_URL` (each with its own `search_path` schema),
  `DBGPT_SESSION_STORAGE_TYPE=db`.
- Infrastructure floor (superseded 2026-08-14): as seeded, Docker Engine +
  Compose v2+, Traefik v2.10+, Redis 6+, PostgreSQL 14+. The governing
  floor is now the infra-kinds lock — PostgreSQL + Redis + Kubernetes only.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied
  architecture brief, immediately after [[asgi-multiplexer-monolith]] —
  the two are a deliberate pair (monolith vs. microservices) for the same
  three-framework combination, and this one arrived with a concrete
  `docker-compose`/`production.yml` extension (Traefik labels, service
  definitions for `langflow`/`dbgpt`/`celeryworker`) rather than prose
  alone. Not yet researched against this repo's own factory or any
  specific downstream project — no station claimed, no Spec derived, no
  decision made between this and the monolith option. Owner deliberately
  left as `guild` (intake, not a terminal owner) pending that decision.
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Dependency-solve spike PASSED (conda-native).** Operator-requested feasibility gate run via `micromamba create --dry-run -c conda-forge langflow dbgpt dbgpt-serve "django>=5" python=3.12`: solves cleanly — 373 packages, one environment: langflow 1.11.2 + dbgpt/dbgpt-serve 0.8.1 + django 5.2.15 agreeing on pydantic 2.13.4 / sqlalchemy 2.0.52 / fastapi 0.141.1. Both engines are now conda-forge packages this factory itself shipped (langflow-feedstock pushed 2026-08-13, db-gpt-feedstock 2026-07-22), so the co-install premise is verified-to-solve, not asserted — the monolith is a live option and neither sibling wins by default. The pair choice is now a deliberate decision awaiting the family's last precondition: a named subject project. **Python-3.14 lane (operator constraint, same day: everything must be 3.14-compatible): FAILS today** — `langflow-base` pins `bcrypt ==4.0.1` (langflow-feedstock recipe line 198, upstream's passlib-compat pin) and no py3.14 build of that bcrypt exists, while `dbgpt`+`dbgpt-serve`+`django>=5` alone solve clean on 3.14 (61 pkgs). The family's sole 3.14 blocker is that one exact pin; remedy is upstream langflow dropping the passlib-era pin or a runtime-validated feedstock loosening — tracked as a langflow-feedstock maintenance item. **Infrastructure constraint (operator, same day): core infrastructure is exactly PostgreSQL + Redis + a Kubernetes container platform (Red Hat OCP or Google GCP/GKE, Docker/Podman images) — nothing else.** This fits the family's existing shape (one PostgreSQL with public/langflow_schema/dbgpt_schema; Redis as the Celery broker; hard statelessness now mandatory since pods are ephemeral — pgvector inside the same PostgreSQL if DB-GPT needs a vector store, no separate one), and shifts the deployment mechanism from Compose/Traefik to K8s ingress/OCP routes at Spec time. It tilts the pair choice toward the microservices topology (per-service pods behind one ingress; replicas = capacity; the in-process co-location the monolith trades for is worth less when in-cluster networking is the platform norm) — the monolith stays viable only as a single-container deployment. Final pair choice still deferred to Spec intake with the named subject project.
- **2026-08-14** — **Operator architecture direction (same day, supersedes the open pair framing):** all components build on and integrate into ONE Django service — cookiecutter-django based, WITH FastAPI integration — grounded in [[django-accelerator-framework]]; the engines integrate **preferably as pluggable Django applications** ([[langflow-django-plugin]] / [[db-gpt-django-plugin]] Pattern-A shapes: ASGI mount + schema isolation), deployed on the PostgreSQL + Redis + Kubernetes platform recorded above. Scaling = replicating the whole service (statelessness mandatory); a per-engine sidecar container remains the fallback ONLY where pluggability fails (dependency or lifecycle isolation). Remaining precondition before Spec intake: naming the subject project.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C1). The § *What it looks like when real* routing paragraph and the two Traefik/Compose constraints were still live prose describing a mechanism this Dream's own 2026-08-14 entry retired; all three are now marked superseded with the decision trail kept. Verified against `src/platform/deploy/**`: zero Traefik references anywhere in `src/`, `scripts/` or `pixi.toml`; the shipped edge is the chart's `ingress.yaml` (one `path: /` rule to the web Service) plus the OCP overlay's `route.yaml`. Status stays `realized`; this was the clearest "realized ≠ in effect" text in the steward half of the pass.

## 2026-09-17 — The Distributed AI Economy — Intelligence Hubs, Frames, Cogs, Ops, and the Accountability Plane (folded from intelligence-hub)

# The Distributed AI Economy — Intelligence Hubs, Frames, Cogs, Ops, and the Accountability Plane

> **Seed Dream.** It carries the OpenTeams whitepaper *The Distributed AI Economy: Intelligence
> Hubs, Frames, Cogs, Ops, and the Accountability Plane* (Travis Oliphant, August 2026, Revision 9)
> into the Dream tier, section by section, so that `bmad-spec` can derive a contract from it. The
> whitepaper stays the source of record; this file is a complete distillation in our own words, with
> a few short attributed quotations — not a copy. Nothing below is an adoption decision.

## Source

- **Document:** https://ownyourintelligence.ai/downloads/Intelligence_Hub_Whitepaper_v9.pdf
  — 46 pages, US letter, produced with LibreOffice 24.2, file dated 2026-08-16; footer
  *OpenTeams | nebari.dev | August 2026 | Revision 9*.
- **Author / publisher:** Travis Oliphant (creator of NumPy and SciPy; CEO, OpenTeams). Companion
  sites: ownyourintelligence.ai, nebari.dev.
- **Integrity:** sha256 `5dabf2bec9cde59e5cc5bfa38eb08d3cd536daf20a6e6d7e815d76cd401dbe41`, captured
  2026-09-05. The PDF is **not** checked in (third-party copyright, 1 MB); re-fetch by URL and
  compare the hash before trusting a later revision against this text.
- **Canonical source repository** (found 2026-09-06 during RB-1):
  https://github.com/openteams-ai/inthub-whitepaper — `whitepaper.md`, `GLOSSARY.md`, `SOURCES.md`,
  `MESSAGING.md`; Revision 9 is tag `v9` (2026-08-17, commit `9c2856923b`), Revision 8 is `v8`
  (2026-08-06); no licence file. Cite later revisions by tag from this repository, not by PDF URL.
- **Field guide** (read 2026-09-09, RB-3): https://ownyourintelligence.ai/ — an Astro site (21 pages
  by sitemap: `/guide/*` in five parts, `/glossary/`, `/sources/`) that *reads* the whitepaper for a
  general audience; not a second source, and its "status audited" block is dated **2026-08-18**, one
  day before the Frame Spec went public, so it still says "no published specification". Its own
  additions: a glossary, a 15-question FAQ, and six **falsifiable indicators** (§ *The decade
  ahead*) against which an outside party can judge the thesis.
- **Implementation estate** (read 2026-09-09, RB-3): https://github.com/nebari-dev — 76 public
  repositories. A first-party Software Pack declares its maturity in its own `pack-metadata.yaml`
  (`level`: experimental / alpha / beta / ga), aggregated by
  `nebari-dev/software-pack-dashboard/tracked-packs.yaml`; the ladder is defined in
  `nebari-dev/software-pack-template/docs/release-readiness-checklist.md`. Derive readiness from
  those files, never from prose.
- **Evidence base:** 34 cited sources — McKinsey (×4), PwC (×2), Deloitte (×3), Stanford HAI
  AI Index 2025 + 2026, Brookings, OSI/OpenLogic State of Open Source 2026, Financial Times,
  Nadella at WEF Davos 2026, Hugging Face, NBER (×2), PEX Network, Dataversity, AlixPartners,
  Gartner (×2), Robert F. Smith (Vista), EU AI Act (Reg. 2024/1689, Arts. 12/14/19), NCSL state
  AI legislation, LinuxInsider, NIST AI RMF 1.0 + GenAI Profile, ISO/IEC 42001:2023, OWASP Top 10
  for LLM Applications, Black Duck OSSRA, Cloudflare OS, Earendil Works, IBM "What is the AI
  stack?". The paper notes that entries it could not re-verify are marked as such, and that one
  attribution (PwC operations survey) was corrected from Deloitte in an earlier revision. Every
  statistic below is the paper's claim, not ours — re-verify at intake before any Spec leans on it.

## The Dream

An organisation owns its intelligence. Its context, its AI workers, its workflows, the checks on
their work and the evidence they leave all live inside a perimeter the organisation governs, built
from shared abstractions that many parties can build to — so that the value of applied AI accrues
to the people who produced the context, and the AI era grows into an open economy rather than a
landlord-and-tenants arrangement.

PyForge is already such a hub in miniature: an owned factory on pixi and conda-forge, with its
context in tracked files, its workers as station skills, its workflows as bmad-loop runs, its
checks as detectors and Warden, and its evidence in ledgers. The Dream is that the Foundry speaks
the whitepaper's vocabulary — Frames, Cogs, Ops, Guards, Gates, Tracks, Organizational Memory —
deliberately rather than by accident, and that the Spec derived from this seed decides *which* of
those shapes PyForge adopts, aligns to, or merely names.

## The whitepaper, distilled

### Preface — why the author wrote it

Three decades of shared abstractions (SciPy, NumPy, Numba, conda, NumFOCUS, now the Applied AI
Society) taught the author one lesson: when a foundational layer is open an ecosystem forms and
value accrues broadly; when it is closed "a landlord forms, and everyone else rents." Enterprise AI
is at that fork. Frontier models are magnificent but rented, and the context, judgment and evidence
that make them valuable inside an organisation are leaking into systems the organisation does not
control. The proposal: organisations organise and adapt their existing IT into self-owned,
self-controlled, governed **Intelligence Hubs**; information technology evolves into **Intelligence
Infrastructure**; accountable intelligence must be intimate with the most important data, and that
intimacy is only safe when both data and intelligence are owned. Six abstractions carry the
argument — Frames, Cogs, Ops, Guards, Gates, Tracks. The paper is explicitly "not a product pitch";
OpenTeams is one contributor among many, and most of the value described is expected to accrue to
organisations the author has never met, as it did with NumPy.

### Executive summary

The next decade of enterprise AI will be defined by who deploys, governs and exchanges AI
capability as owned operational infrastructure — a shift from renting intelligence through
black-box APIs to sovereign, reproducible, auditable deployments. The architecture is three layers
plus one cross-cutting plane:

| Plane / layer | Core units | Does |
|---|---|---|
| Layer 1 — Infrastructure | Intelligence Hub · Nebari · Nebi | Own, deploy and integrate AI as sovereign infrastructure |
| Layer 2 — Execution | Frames · Cogs · Ops | Carry context, perform work, orchestrate outcomes |
| Accountability plane (cross-cutting) | Guards · Gates · Tracks | Verify the work, decide whether it proceeds, record the evidence |
| Layer 3 — Economy | The marketplace | Discover, exchange and monetise artifacts across Hubs |

Every Op declares a **Validation Strategy** so AI-generated work becomes accountable operational
intelligence rather than unverifiable output. The one essential first interface is a **Desktop/Web
Application** through which knowledge workers combine Frames, converse with Frame-oriented Cogs,
run Ops and share context. Market framing: McKinsey sizes sovereign AI at $500–600B by 2030; PwC's
29th CEO Survey (n=4,454) finds 56% of CEOs report zero financial impact from AI and 12% report
both cost and revenue benefit — the investment-to-outcome gap the architecture is meant to close.

### Where this sits in the AI stack

Not a rival stack. The shared abstractions sit inside the familiar layers — Frames at the data
layer, Cogs at the work layer, Ops at the application layer — and the accountability plane is the
paper's concrete answer to what the industry calls observability and governance, made shippable
with the artifacts themselves. Around an owned Hub a second economy of products forms (Hub
experience apps, compute and model management, Track stores, Gate consoles, Op and Cog builders,
Guard libraries, segment-specific Ops).

The paper's own honesty table, as of Revision 9:

| Status | Covers |
|---|---|
| Exists today | Nebari and `nebari-infrastructure-core`; Nebi (packaging and reproducibility, built on pixi, which built on conda); owned Hubs in production; Frames as governed artifacts with storage, identity and connectors; a Desktop/Web Application; owned model serving on open weights |
| In active development | Cogs and Ops as first-class installable objects with declared tools and permissions; the Op manifest with a declared validation strategy; multi-organisation Hubs; the first Guard libraries |
| Thesis | The accountability-plane runtime at scale; a marketplace exchanging artifacts across many independent Hubs; the distributed AI economy itself |

Nebi is singled out as the thesis in miniature: it builds on pixi, which built on conda, rather
than inventing distribution anew — shared abstractions compounding across generations.

### 1. The problem — rented intelligence is fragile, and context leaks away

Organisations know AI is strategic yet depend on vendor-controlled black boxes they cannot inspect,
reproduce, audit or own (the paper names Codex, Claude Code/Cowork, Grok and Gemini), and even when
they can deploy capable AI they cannot capture and propagate the organisational context — rules,
terminology, goals, style, norms — that turns generic AI into specialised work. Eight failure modes,
each with a root cause and a business impact: **vendor lock-in** (third-party APIs → strategic
dependency, cost unpredictability); **security leaks** (data leaves → lost moat and IP, regulatory
exposure in healthcare/finance/government); **execution opacity** (no visibility → cannot audit or
reproduce); **integration fragility** (no standard for how AI plugs into workflows → cost and
breakage); **value leakage** (capabilities cannot be shared or monetised); **context dissipation**
(no portable container for rules, terminology, norms, skills, tools, prompts and processes →
repetitive re-setup, brand and policy drift, the ROI-fuelling context does not stay with its
producer); **governance vacuum** (1 in 5 organisations has mature agent governance — Deloitte 2026;
AI incidents up 56.4% in 2024 — Stanford HAI; 43% have no formal AI governance policy — PEX);
**talent scarcity** (worker skills the #1 barrier — McKinsey; only 20% report high talent
preparedness — Deloitte). The root cause is architectural: no standard model for what an owned
deployment looks like, how capabilities are packaged into executable units, or how organisational
knowledge is encoded, inherited, shared and exchanged. Two market voices frame it: Satya Nadella at
Davos 2026 — sovereignty means embedding the firm's tacit knowledge in weights the firm controls,
otherwise "you're leaking enterprise value to some model somewhere" — and Robert F. Smith of Vista,
who is "shocked" that CEOs on an ARR race have leaked intellectual property.

### 2. The vision — a distributed economy of owned intelligence

Every organisation — enterprise, government, research institution, startup — runs its own Hubs:
sovereign, governed environments integrating its data, legacy applications, AI-native workflows,
policies and models inside its own perimeter, appropriately virtualised across private cloud and
edge. The sovereignty argued for is realistic, not absolutist: Brookings (Feb 2026) finds
full-stack AI sovereignty structurally infeasible for almost any country, so the market for trusted
intermediaries is permanent; Stanford HAI names four sovereign-AI objectives (cultural autonomy,
national security, economic competitiveness, regulatory oversight); McKinsey (Mar 2026) calls
sovereign AI "an ecosystem play" with sovereignty applied deliberately at critical control points.
Control your model choice, data paths, policies and evidence — without fabricating chips or
training a frontier model.

Hubs need not stay isolated: they connect "as a drawbridge connects walled castles", so derived
results flow under the policies of the organisations accountable for the data. Four versioned,
exchangeable artifacts travel those pathways: **Frames** (scoped context, inherited across scopes,
shareable internally and externally), **Cogs** (specialised AI workers oriented by Frames —
reproducible, modular, self-contained cognitive workers), **Ops** (installable, versioned programs
of AI-influenced work, accountable to human oversight) and **Guards** (installable, versioned test
and verification code).

Two framings complete the vision. First, the **Intelligent Ops Factory**: where AI-native software
factories capture requirements, architecture and structured context upstream and feed it to agents
so they produce governed software, an Ops Factory produces and continuously maintains an
organisation's standard operating procedures inside its own Hub — the output is operational
intelligence the organisation owns, not an application; many parties can operate such factories
because the abstractions are shared. Second, **no "Hub to rule them all"**: a distributed fabric of
owned Hubs interoperating through shared open standards, not a shared owner. OpenTeams
participates by contributing Nebari and Nebi, operating a public reference Hub for small
organisations, building products around the Hub and offering maintenance — and argues a
**services / concierge layer** is necessary because the open-source AI ecosystem (model servers,
vector databases, orchestration, observability, identity) is vast, fast-moving and fragmented. The
concierge role is deliberately non-exclusive.

### 3. Layer 1 — Infrastructure

The canonical relationship, held throughout: **Nebari** is OpenTeams' flagship open-source
contribution; **Nebi** is the reproducibility and distribution mechanism; the **Intelligence Hub**
is a customer-specific assembly of open-source and proprietary components that someone integrates,
governs and maintains. No single tool is the infrastructure.

**3.1 Nebari.** Since June 2025 the project has been rearchitected into a modular, composable stack:
`nebari-infrastructure-core` plus more than fifteen software packs at varying maturity, from the
original Jupyter data-science use case to serving open-weight LLMs and GenAI chat. Within its scope
it standardises compute and environment management across cloud and on-premise, model deployment
and versioning, tooling interoperability, and RBAC / audit logging / governance primitives. It is
open-source and additive — usable à la carte on top of existing infrastructure. Stewards named:
Travis Oliphant and Dharhas Pothina. A Hub "is not a Nebari deployment"; Nebari may play a role but
rarely the only one. Market support: OSI's 2026 State of Open Source (n=700+) finds lock-in
avoidance cited by 55% of respondents, up 68% year over year; Black Duck OSSRA on open-source
prevalence; a January 2026 industry quote that open standards let the ecosystem inspect, test and
harden the protocols agents use.

**3.2 Nebi.** The installation foundation: definition, installation and lifecycle management of
complex deployable environments, built and working today on pixi and conda. It defines the common
format by which Frames, Cogs, Ops and Guards are packaged; manages dependencies and environment
snapshots so an Op installed in one Hub behaves identically (within generative-AI limits) in
another; enables versioned rollout and rollback of AI systems, Frames and dependent Cogs; and is the
installation primitive and reproducibility guardrail that makes a marketplace technically possible.
Because it can package anything the open-source community creates, it bridges the ecosystem's
varied standards and the Frame/Cog/Op/Guard ecosystem — without it those artifacts would be
application-layer agreements with no infrastructure-layer enforcement.

**3.3 The Accountable Intelligence Hub.** A particular configuration of open-source components
deployed inside an organisational perimeter, the concrete realisation of the standard and the
centrepiece of the architecture: where Frames are made manifest and connected to Cogs, where Cogs
are installed, configured and run, where Ops orchestrate Cogs, and where the organisation connects
outward to the marketplace as consumer and, over time, publisher. Seven characteristics: operates
inside the organisation's perimeter (cloud, on-prem, hybrid); integrates with ERP/CRM/warehouses/
APIs; enforces governance on model behaviour and data access; stores, versions and manages the
inheritance graph of Frames; provides full auditability of AI actions; stores and governs Tracks;
connects bidirectionally to the marketplace. No two Hubs are identical, by design; nobody is asked
to migrate. Market support: Deloitte sizes the on-prem hybrid market above $50B for 2026 and finds
77% of enterprises weigh a vendor's country of origin, 58% build primarily with local vendors;
McKinsey's "key control points are sovereign by design"; PwC finds 87% of operations leaders
hampered by poor data quality, with McKinsey adding that localisation does not make data usable —
strong sovereign ecosystems build data products and sharing mechanisms.

**3.4 Organizational Memory.** The persistent context substrate that turns a Hub from a server-side
deployment of AI tools into a compound learning system. Frames hold **intentional** context (what
humans chose to make explicit); Cogs and Ops generate **emergent** context (what actually happened);
Guards, Gates and Tracks are part of the same memory. It is a capability on a continuum, not a
product: at the simplest end a version-controlled directory of Frame files; at the richest, full
conversational records of every Cog interaction, semantic retrieval over them, structured records of
every Op execution with its human decisions, knowledge graphs of concepts/decisions/people/outcomes,
existing knowledge bases and ERP data, and time-aware retrieval. The Hub prescribes no technology —
it provides integration points and governance hooks — and the paper offers a menu: versioned Frame
repositories (Git/GitHub/GitLab or object storage), wikis (Confluence, Notion, Obsidian), vector
stores (Chroma, Weaviate, Qdrant, Milvus, pgvector), AI memory frameworks (Mem0, Letta, Zep;
LangChain/LlamaIndex modules), observability platforms (LangSmith, Arize Phoenix, Helicone),
knowledge graphs (Neo4j, ArangoDB), lakes and warehouses (Snowflake, Databricks, Iceberg,
BigQuery, PostgreSQL). A typical configuration combines an object store for Frame versioning, a
vector database for Cog conversations and an observability platform for Op executions. Governance
is essential: access controls, retention policies, anonymisation/redaction, audit trails, and **the
ability to forget**. Memory belongs to the organisation that produced it — "intimacy without
ownership is exposure" — so a Hub cannot be rented or bought whole; vendors and contractors may
maintain parts of it.

### 4. Layer 2 — Execution: Frames, Cogs and Ops

**4.1 From models to work.** The gap is not at the model layer but at execution: turning a capable
model into a reliable, auditable, governable unit of work, while keeping the organisational context
with the organisation instead of dissipating it into one-off prompts and vendor-side logs. Evidence:
72% of enterprises have sovereign AI on the roadmap but 13% are on track (McKinsey); 12% / 56% CEO
figures (PwC); 34% of organisations genuinely reimagining with AI and 1% self-described AI-mature
(Deloitte). The **progression of value**: models predict tokens → Frames orient humans and Cogs to
shared context → Cogs perform specialised work under Frames, skills, tools, memory, permissions and
Guards → Ops orchestrate outcomes with human oversight. A **running example** threads the paper: an
accounts-payable analyst launches a *Vendor Fraud Review* Op; Company Policy, Procurement Rules and
Fraud Detection Methodology Frames orient every step; Invoice Extraction, Vendor Risk and Anomaly
Summary Cogs do the work; Schema, Source, Privacy and Consensus Guards check it; low confidence or
high vendor risk routes the case to a human before any vendor is flagged; the full Track is retained.

**4.2 Where agents fit.** The industry converged on the agent — a model in a loop with tools pursuing
a goal — and the hard problem is no longer building one but **employing** one: who does it work for,
whose context and policies govern it, which tools and data may it touch and under whose identity,
how much autonomy was granted and by whom, who checks the work before it has consequences, what
record remains. "Agent" is a runtime blur across three things the architecture keeps separate: the
**capability** (a Cog — installable, versioned, auditable before it runs), the **engagement** (an Op
— goal, autonomy budget, checkpoints, validation strategy) and the **continuing actor** (identity,
credentials, memory, history — held by the Hub: identity from its directory, credentials brokered
and scoped, memory in Local and Organizational Memory, history in Tracks). An agent, precisely, is a
Cog engaged through an Op, given identity and memory by the Hub; fused into one word, these are how
vendors capture instance state and why governance cannot be tailored. The employment mapping:
Frames are the context and policies; a Cog is the qualified hire; an Op is the assignment; Guards
check the work; Gates are the autonomy budget; Tracks are the personnel record; the Hub is the
workplace. Autonomy is granted per engagement, not per platform (a drafting Op may run nearly
unattended, a payments Op may need approval at every step) — the shape Gartner now insists on,
predicting that by 2027 40% of enterprises will demote or decommission autonomous agents over
governance gaps found only after incidents. Cloudflare OS validates the category (workspace grounded
in organisational context, policy-enforcing "Gatekeepers", persistent app platform) while showing
openness and sovereignty are different properties — Apache-2.0 code designed for one vendor's
network, self-hosting an in-progress escape hatch; Earendil Works documents providers making
sessions deliberately non-portable. Whoever holds an agent's context, memory and history owns the
agent. Agents operating infrastructure (installing, provisioning, patching) are Ops like any other:
Guards pre-check authority, Tracks record actions, Nebi pins artifacts. "Agents are the hands; the
Hub is the employer of record."

**4.3 Frames — shared cultural alignment.** A Frame is a scoped, text-based artifact (a file or folder
of files using an open protocol) carrying the cultural and operational context within which work
happens — the brand voice, terminology, regulatory constraints, conventions and norms that today
live in wikis, Slack history and senior heads. "Context, in this sense, is capital": every prompt
that re-explains the organisation is capital spent as an expense; a Frame is the same context
accreting as a versioned asset. Frames are first-class — authored, discovered, exchanged and
inherited independently of Cogs and Ops. Typical contents: rules, terminology, goals, style, norms,
skills, tool specifications (Nebi or similar spec files), output Guards, prompts, architecture
descriptions, business-process details. Six essential properties: **scoped** (organisation,
department, team, project, role or relationship), **inheritable** (child extends parent; the chain
of authority is auditable), **composable** (company + department + project + ad-hoc for one
session), **shareable** (internally, or selectively externally with reviewed subsets), **discoverable**
(internal libraries, communities of practice, open registries — most Frames spread by community
adoption, not sale) and **owned** (by an accountable human or group — the slice of direct human
accountability in the context). A Frame may declare a Guard that must run on the system's output.
Why a distinct layer rather than "just prompts" or "just skills": a Frame is an organisational
artifact governed by its owner — versioned, audited, inherited, exchanged — the cultural commons made
explicit and portable yet protectable. Illustrative Frames: Brand Voice (marketing), Healthcare
Compliance (legal, pointing to a mandatory Guard), a Q4 Sales Playbook, an External Vendor Frame
with selectively shared sections, a Pharma R&D Compliance Frame published by a consortium. Five use
cases OpenTeams runs itself: internal alignment (a Company Frame every division/team/project/person
inherits), sister companies and ecosystem peers (Product Direction Frames), open-source communities
(Community Frames — Nebari among them), partner engagement (a Partner Frame: "the Frame is the
contract of context") and investor messaging (an Investor Frame against message drift). The **Frame
protocol** — an open specification for the artifact's structure — is the standard that makes the
exchange possible: Nebari standardises infrastructure, Nebi packaging, the Frame protocol cultural
alignment.

**4.4 Cogs — AI workers oriented by Frames.** A Cog is a discrete AI-powered worker, the atomic unit
of AI work — "an AI worker you can hold to account": an assembly of a (possibly specialised) model,
a context including one or more Frames, the skills/tools/APIs it may use, and its governance
parameters (data it may access, actions it may take, what needs human approval), that can be named,
versioned, inspected and replaced. Cogs are the key artifact Nebi distributes and can carry all code,
dependencies and weights. Three types: **model-heavy** (deploys the foundation model), **context-heavy**
(the data and context, pointing at a model by dependency or API endpoint) and **combined** (a complete
isolated worker). Context management is the central discipline: Frames are the durable governed
foundation, around which retrieved documents, slices of Organizational Memory, conversation history,
tool outputs, real-time data and task instructions are assembled at invocation — "a well-constructed
Cog is, in large part, a well-managed context." The **harness explosion** (agent loops, tool-calling
frameworks, graph orchestration, memory scaffolds, skill libraries, evaluation hooks, new ones
monthly) is read as evidence that weights alone are not a worker; a harness is a capability a Cog
builder uses, not a competitor to the Cog, and the Cog abstraction makes the harness choice an
internal detail — a vertical specialist can build a Contract Review Cog on one harness while a
community builds an Invoice Extraction Cog on another and an Op composes both. Cogs are the level at
which AI behaviour becomes auditable like a worker: not "what did the model do?" but "what did this
Cog do, with what inputs, under which Frames, with what outcome?" Productivity evidence: the NBER
"Generative AI at Work" study (5,179 support agents) found a 14% average gain and 34% for novices;
NBER WP 34984 (n=750 executives) finds positive, sector-varying gains expected to strengthen in
2026. Cogs are not usually standalone agents — they can be run directly for debugging, validation,
analysis or simple operations, but normally live inside an Op.

**4.5 Ops — orchestrated AI workflows.** An Op is "the application of the distributed AI economy": the
supervised workflow a human at the keyboard launches, mapping onto how knowledge workers think about
their job — "Close the books", "Onboard this customer", "Qualify this lead", "Draft this campaign",
"Review this vendor for fraud". Composition: one or more Cogs (each with embedded Frames);
workflow-level Frames; a supervising model that sequences, parallelises and handles the unexpected;
human-in-the-loop checkpoints; a declared Validation Strategy (Guards, Gates, Track); integration
logic to enterprise systems; a Nebi-compatible manifest (dependencies, environment, configuration).
Invocation from wherever the user already is: an icon in the Desktop/Web launcher, a CLI or chat
command, a button or link inside a business application, a scheduled or event-triggered job.
Authored once and installed into any compliant Hub, picking up the local Frames — the npm/pip
analogy, for supervised Frame-aware workflows rather than libraries. Market support: Deloitte
anticipates agent marketplaces and argues advantage lies with organisations that redesign
end-to-end processes around agents; 74% of companies plan agentic AI within two years. Seven
characteristics: **versioned** (identifier and changelog), **installable** (via Nebi), **Frame-oriented**
(declares required/applied Frames), **supervised** (coordinating model + human checkpoints),
**triggerable**, **self-contained** (Cogs, logic, integration specs, Frame declarations) and **composable**
(Ops call Ops).

### 5. The accountability plane — Guards, Gates and Tracks

Every AI-assisted workflow must answer two questions: what context should guide this work (Frames),
and how do we know the result can be trusted (Guards, Gates, Tracks). The plane cuts across all
three layers rather than sitting beside them. Without validation AI work stays fragile; with it, it
becomes operational intelligence — and in enterprise, government, healthcare, finance and legal
settings output must be verifiable, governable, auditable and accountable, not merely useful. The
validation gap: rising incident counts with rare standardised evaluations (Stanford HAI); McKinsey's
"gen AI paradox" — ~80% deployed, ~80% no material earnings impact, under 10% of use cases past
pilot — with the prescribed remedy being exactly this layer. Validation runs during Frame
construction, Cog development and Op execution. The paper's own summary line: *"Frames guide the
work. Cogs perform the work. Ops orchestrate the work. Guards verify the work. Gates decide whether
the work proceeds. Tracks make the work accountable."*

**5.1 Guards.** Reusable verification and protection components that check whether a Cog's or Op's
output or action is correct, safe, policy-compliant and ready for use. Broader than tests: some
deterministic, some probabilistic, some comparing independent Cogs, some requiring human review;
running before, during or after work. A Guard can check that the right Frames were applied, that
output matches a schema, that answers are grounded in approved sources, that a proposed action does
not violate policy, that no sensitive data is exposed, that independent Cogs agree, that confidence
is high enough for autonomous action, that a human expert must review, and that behaviour is not
drifting from previously validated behaviour. Named library shapes: Schema, Source, Policy, Privacy,
Consensus, Drift and Expert Guards. The principle: Frames *may* declare Guards; every Op *must*.
Validation is part of Frame and Op design, not a policy-team afterthought.

**5.2 Gates.** Decision points where the results of one or more Guards determine what happens next:
continue, pause, request human approval, escalate to an expert, retry with a different Cog, run more
validation, or stop. "Guards check. Gates decide." Examples: unsupported claims → pause for revision;
low confidence → human review; sensitive data → stop before external transmission; strong Cog
disagreement → expert escalation; all pass → proceed. Gates encode the fact that not all failures
are alike — some need correction, some review, some escalation, some termination — and in the
running example a low extraction confidence or a high vendor-risk score is a routing decision, not a
failure state. Regulation expects formal Gates: the EU AI Act's human-oversight article (Art. 14)
requires that a natural person can interpret, decline, override, reverse or stop the system —
timelines under the AI Omnibus political agreement of December 2027 for standalone high-risk
systems and August 2028 for AI embedded in regulated products.

**5.3 Tracks.** The durable record of an Op or Cog execution: the Op run, Cogs invoked and Frames
applied; input data and source references; model versions and configuration; Guards executed with
results and confidence; Gates passed, failed or escalated; human approvals, edits and overrides;
final outputs or actions; timestamps, user identity, permissions and environment; links to
Organizational Memory. Purposes: auditability (reconstruct why), governance (verify procedure),
learning (corrections become signals for improving Frames, Cogs, Ops and Guards), debugging and
trust. "The Track is not just a log file. It is a structured accountability artifact." Unlike the
other four artifacts, Tracks are usually not exchanged — retained under the producing Hub's
governance, produced only for audits or regulators: "Evidence is not for sale." The EU AI Act
requires automatic event recording and deployer log retention (Arts. 12 and 19); Tracks satisfy
that by construction.

**5.4 Validation across the Op lifecycle.** Four stages, each with its core question and example
controls: **pre-flight** (is this Op allowed and configured? — permission, required-Frame, data
authorisation and model availability checks), **in-flight** (is the work within policy and bounds? —
tool-use, privacy, confidence, policy checks, intermediate review Gates), **post-run** (is the output
correct, useful, safe, actionable? — source grounding, schema validation, expert sampling,
consensus, final approval Gates) and **continuous** (is quality improving, degrading or drifting? —
regression tests, drift detection, benchmark suites, incident reviews, sampled expert audits). A
low-risk drafting Op may need format checks and user review; a high-risk fraud Op may need source
grounding, multiple independent Cogs, expert sampling and a Track retained for years; clinical,
legal, financial and public-sector Ops may need formal Gates before any recommendation becomes an
action. The lifecycle aligns with NIST AI RMF 1.0 (govern, map, measure, manage) and its Generative
AI Profile — declaring Guards, Gates and Tracks per Op is how that framework becomes executable.

**5.5 Seven categories of Guards.** **Algorithmic** (deterministic rules or known results — code
passes tests, SQL executes, totals reconcile, JSON matches schema); **Source-Grounding** (claims
supported by approved evidence; cited passages actually support the conclusion); **Consensus**
(agreement across independent Cogs, prompts, models or paths — two of three must agree; a verifier
Cog reviews another); **Expert** (human judgment on sampled or high-risk outputs — periodic 5%
sampling, mandatory review of high-risk classifications, approval before external communication);
**Policy & Safety** (inside allowed boundaries — no private-data release, no unapproved tools or
sources, no action beyond the user's permissions, brand/legal/ethical constraints); **Regression &
Drift** (golden sets after model updates, rising error rates, a new Frame that degrades performance);
**Outcome** (the intended business result — fewer false positives, shorter onboarding, more contract
risks caught, lower cost without added risk). The strongest are algorithmic; the most
business-meaningful are Outcome Guards; Policy & Safety Guards connect directly to Frames.

**5.6 The Validation Strategy — part of every Op's contract.** Every Op declares which Guards it uses,
where Gates occur, what Tracks are retained and when human review is required, answering: what must
be checked before running and which Frames, Cogs, tools and data are authorised; which outputs need
algorithmic validation and which claims need grounding; when consensus is required; when human or
expert review is required and at what thresholds; what evidence the Track must preserve and for how
long; how failures, corrections and overrides feed back into Organizational Memory. ISO/IEC 42001
(the first AI management-system standard) asks for lifecycle management, independent audit and
continual improvement; a declared strategy makes that concrete and machine-checkable. "An Op is not
complete unless it declares how its work will be verified." The paper sketches the running example
as a validation-aware **Op manifest**: the Op's name; its three Frames; its three Cogs; Guards grouped
by stage (pre-flight: required-Frame, permission, data-source authorisation; in-flight: tool-use
policy, sensitive-data, confidence; post-run: schema, source-grounding, consensus, expert-sampling);
Gates as threshold rules (confidence below 0.80 → human review required; consensus disagreement
above 0.25 → expert review; sensitive data detected → stop and escalate; vendor risk high → human
approval); and a Track block with a seven-year retention and an include list (Frames used, Cogs
invoked, source documents, Guard results, Gate decisions, human approvals, final output).

**5.7 How validation completes the architecture.** Frames define the rules; Guards verify the work
stayed faithful to them (a Healthcare Compliance Frame's rules, a Privacy Guard's check). Cogs
perform; Guards check reliability — and some Guards are themselves Cogs when validation needs
interpretation. Ops orchestrate; Gates decide whether they proceed. Tracks flow into Organizational
Memory, closing an eight-step **Accountability Loop**: Frames orient → Cogs perform → Ops orchestrate
→ Guards validate → Gates control action → Tracks preserve evidence → Organizational Memory learns →
Frames, Cogs, Ops and Guards improve.

**5.8 Validation as an open-source opportunity.** Guard libraries, benchmark suites, prompt-injection
test harnesses (prompt injection tops the OWASP Top 10 for LLM applications), source-grounding
validators, schema and format Guards, domain compliance Guards, red-team datasets, expert-sampling
frameworks, drift monitors, Track schemas, evidence-record viewers, audit and governance dashboards.
Trust cannot be built by one company; it compounds when the ecosystem can inspect, improve and share
the validation tools. "Open Guards can become to accountable AI what open test frameworks became to
software quality."

### 6. Layer 3 — the marketplace

**6.1 Four classes of exchanged artifact,** each with its own publishers, audience and dynamics: **Ops**
(service-as-software under subscription, usage or outcome arrangements), **Cogs** (rented, purchased,
given away or subscribed), **Frames** (the vast majority shared freely within and between organisations;
a few offered commercially as licensed expertise) and **Guards** (many published openly by communities
and experts; commercial libraries encoding regulated-industry expertise — a HIPAA Privacy Guard, a
KYC Source Guard, a Contract Citation Guard, a Prompt Injection Guard). Organising around four
classes rather than one is a deliberate decision: the work, the workers, the context that orients
them and the validation that makes them trustworthy. **Horizontal vs vertical AI:** horizontal Ops
are authored once and installed across many Hubs; vertical specialisation — historically bespoke
consulting that dies with the engagement — becomes portable when the same horizontal Op picks up an
organisation's Frames, is checked by its Guards and leaves Tracks under its governance. **What is
scarce when code is free:** verification, context and accountability. A HIPAA Guard is valuable for
who stands behind it; a Frame is distilled expertise with a named owner; an Op with a thousand
validated Tracks is trustworthy in a way a fresh one is not, and that cannot be faked because Tracks
only accumulate through governed real use — "when generation is free, provenance is the product."
The Frame side of the economy is coordination and shared abstraction more than transaction
(communities of practice, consortia, open-source ecosystems, internal departments). Tracks are not
exchanged, though anonymised or aggregated Track data can inform quality rankings and trust
signals. Pricing trajectory: Gartner (via Deloitte) projects at least 40% of enterprise SaaS spend
shifting to usage-, agent- or outcome-based pricing by 2030; AlixPartners says incumbents must
consider dismantling the pricing models they were built on.

**6.2 The network flywheel — and its brakes.** More Hubs → a larger market for publishers → more
artifacts make each new Hub more valuable → more deployments generate more data on what works →
better artifacts strengthen the marketplace → more Hubs. The paper names four brakes: **cold start**
(the first artifacts are the ones organisations build for themselves anyway; a Hub is valuable
before it exchanges anything), **fragmentation** (three incompatible Frame formats would be worse
than none — standards work is a first-class deliverable), **quality collapse** (Guards nobody trusts,
Ops that pass their own checks and fail in the world — provenance is the defence; lose it and the
marketplace degrades to a code repository) and **incumbent bundling** (a large vendor ships the whole
shape free on rented compute — "the brake most likely to bite"; the only durable answer is that
ownership must be easier than renting). Macro tailwinds: the FT on deglobalisation as a supplier
windfall; Nvidia's $30B sovereign revenue in FY2025; Stanford HAI's $581.7B global corporate AI
investment in 2025 (+130% YoY).

**6.3 Who participates.** Enterprises (deploy Hubs, author Frames, install artifacts); AI developers
(build and publish Ops and Cogs); domain experts (author Frames, configure Cogs, define Op logic);
communities and consortia (open Frames codifying methodologies and vocabularies); consultancies and
agencies (methodology Frames, mostly open); system integrators (deploy and customise Hubs, bespoke
Ops and Frames); open-source contributors (extend Nebari, Nebi, the Frame protocol, Cog and Op
standards); Guard publishers and validation experts (Guards, Gate policies, benchmark suites, Track
audits); regulators and standards bodies (rules, schemas, test profiles, reference Guards).

### 7. Products around the Hub — the Desktop/Web Application as worked example

**7.1** Architecture alone does not create adoption. A second economy forms around an owned Hub —
experience applications, compute and model management, Track stores and viewers, Gate and review
consoles, Op and Cog builders, Guard libraries, segment-specific Ops, integration and operations
services — every one buildable by many parties and integrable into a Hub the organisation owns.
The Desktop/Web Application is worked through as one such product, not the category.

**7.2 Target user:** knowledge workers in sales, marketing, project success, accounting, legal, HR, IT
and shared services — people who operate inside well-defined contexts, apply organisational norms to
every task, need AI that respects those contexts without re-orientation, routinely share context
across boundaries, and are not engineers.

**7.3 Memory in the application.** A personal **Local Memory** absorbs the user's active Frames —
Company on joining, Department layered on, Project composed further, marketplace Frames installed,
personal Frames authored — and becomes the substrate every conversation and Op inherits. Beyond it,
a permissioned window into **Organizational Memory**: the user's own past Cog conversations and Op
runs, their team's where access is granted, and the documents and records their role authorises. The
boundary is policy-controlled (a sales rep sees their accounts, not others'; a clinician their care
team's protocols and summaries, not records outside it) with uniform access controls, retention,
anonymisation and audit. Local Memory is private by default and promotion outward is the user's
call; reach into Organizational Memory is Hub-governed, visible, auditable and reversible by
administrators.

**7.4 Three modes of engagement:** **Applications** (Ops as launcher icons — "the buttons that do the
job", optionally picking up the user's active Frames or pinned to pre-loaded ones), **Conversations**
(chat with Cogs already oriented by the active Frames — brand voice, terminology, goals and tools
without setting the stage) and the **Cog Library** (load a Cog directly as a standalone tool for
analysis, validation, debugging, one-offs, or to explore what exists).

**7.5 Frame management** is the application's most distinctive capability: install Frames from the
marketplace, the internal library or partners; combine them for a session with the application
managing the inheritance graph; author or extend; share internally or externally with field-level
controls; give feedback either as scores on particular concepts on a six-point scale (−10, −1, −0,
+0, +1, +10) or as suggested changes routed to the accountable author; publish back to the
organisation's library, a community board, a user, or the open marketplace. The application is
both a productivity surface and a context exchange.

**7.6 Hub health and governance** for administrators: resource utilisation and model-serving status,
an audit-log browser (AI actions, human interventions, Frame applications, data accesses), policy
management across Frames/Ops/Cogs, and user/role management.

**7.7 Making validation visible** without overwhelming users: Guard status per Op run or Cog output,
Gate prompts in-workflow, a Track view for authorised users, confidence and risk indicators, a
correction workflow that feeds Organizational Memory, and validation badges. Plain language for
users ("This Op passed all required Guards", "This result needs expert review", "A Track has been
saved for audit"); deeper views for compliance (Guard configuration, Gate thresholds, retention,
sampling rates, drift reports, failure trends).

**7.8 Products as market development:** they lower the barrier to Hub deployment, make discovery
app-store-like, create a usage feedback loop for artifact quality, serve the Applied AI Society's
credentialing as a training environment, and demonstrate an owned Hub in the most persuasive way — a
knowledge worker doing their job, with AI, under the right Frames.

**7.9 Technical architecture:** cross-platform native (macOS, Windows, Linux) plus web; local-first
(full function against a local Hub when remote Hub or marketplace is unreachable); Hub-agnostic
(any standards-compliant Hub); Nebi-integrated (artifact install and lifecycle through the Nebi
client); marketplace-connected; local-memory-backed; validation-aware; extensible via a plugin
architecture for Op developers' custom Cog configuration UIs.

### 8. Ecosystem strategy — Nebari, Nebi and the startup ecosystem

**8.1 Open source as the trust foundation.** The marketplace only works if an Op behaves the same in
any Hub, a Frame is interpreted the same by any Cog, and the protocols are stable and open — trust
grounded in open source. Nebari is company-backed to be nurtured with focus but is establishing
community governance, the dynamic that made Python the default language of AI. Adoption is
self-reinforcing, and OpenTeams as primary steward captures some value through enterprise services,
marketplace fees and its own Cogs and Ops.

**8.2 Nebi as the distribution mechanism** — pip to Python, npm to JavaScript: the plumbing that lets
everyone focus on authoring and using artifacts rather than deployment mechanics. Its trust role:
dependencies resolved and pinned, installations logged, every deployment auditable.

**8.3 The startup ecosystem.** As Kubernetes spawned cloud-native startups, Nebari and Nebi can
found a generation of domain-expert AI businesses that publish vertical Ops, Cogs and Guards and —
uniquely — Frames monetising accumulated industry knowledge: a healthcare-informatics expert's HIPAA
Compliance Frame, a consultancy's methodology Frame, a law firm's Contract Review Frame, and the
same pattern across energy, agriculture, legal, financial services and government. No single company
should build every vertical artifact; the economy needs infrastructure and a marketplace that make
it attractive for experts to build them. McKinsey: up to 40% of AI workloads in the public sector and
regulated industries could move to sovereign environments; Hugging Face's Spring 2026 report: open
source remains the foundational layer for building, evaluating and governing AI.

### 9. The landscape

Two axes — how open the standards are, how much the organisation ends up owning — and six rows, each
a legitimate choice: **foundation model providers** (OpenAI, Anthropic, Google — frontier capability
via API, the models most Cogs will call; but context, session state and evidence live in the
provider's system); **cloud AI platforms** (SageMaker, Azure ML — managed scale; the cloud's
standards, limited portability, no shared abstractions for context or work); **agent frameworks**
(LangChain, AutoGen and many harnesses — rapid construction; a harness is a capability, not a
governance model, and a natural layer inside a Cog); **agent OS platforms** (Cloudflare OS — the whole
shape, open source and usable; designed for one vendor's network, self-hosting maturing, standards
governed by one company); **enterprise software vendors** (Salesforce, ServiceNow — AI where the work
happens; context bound to one suite); and **an owned Hub on shared abstractions** (this paper — open
standards and owned deployment together, portable context, accountability shipping with the
artifacts; younger, dependent on an ecosystem forming, and the organisation shoulders ownership
responsibilities others would carry). None is a competitor to defeat; several are components an
owned Hub uses. The durable claim is compounding — open-source trust, portable context, accountable
execution and four-class network effects reinforcing each other — and the room is set by the
readiness gap: 88% of CEOs not achieving meaningful AI returns (PwC), 1% AI-mature (Deloitte), 13%
on track (McKinsey).

### 10. Strategic roadmap

Timing is set by forces beyond any participant: EU AI Act obligations phasing in (governance and
transparency first; many high-risk obligations December 2027 / August 2028 under the AI Omnibus
agreement; fines to €35M or 7% of global turnover); over 1,100 AI bills across 45 US states in 2025;
McKinsey's observation that sovereign cloud and AI migrations take three to four years because of
organisational, not technical, work. Three phases: **Phase 1 (now–6 months)** — Hub deployment
hardened, Nebi packaging standard defined, **Frame protocol published**, first Ops/Cogs/Frames/Guards
built, Desktop/Web Application released; **Phase 2 (6–18 months)** — public marketplace live, 50+ Ops
and 100+ Frames, application GA, first vertical ecosystems (health, energy, legal), initial
open-source Guard libraries; **Phase 3 (18–36 months)** — 1,000+ deployed Hubs, 500+ Ops and 2,000+
Frames, consultancies/communities/experts publishing Frames and Guards, Applied AI Society
credentialing, international Hub networks.

### 11. Conclusion

The Intelligence Economy is the next stage of enterprise computing: IT becomes Intelligence
Infrastructure; AI capability is owned, controlled, deployed, exchanged and governed as core
operational infrastructure, kept intimate with the organisation's most important data because the
organisation owns both; and organisational context is itself a first-class artifact. Nebari
anchors the open infrastructure; Hubs are the organisational loci; Frames the portable context;
Cogs the governed workers; Ops the installable units of work protected by Guards, Gates and Tracks;
Nebi the distribution mechanism; products around the Hub the way everyday knowledge workers reach
it. Accountable AI needs validation as much as context and automation. The abstractions are offered
in the spirit of NumPy, SciPy and Anaconda — shared, so the value accrues broadly. The paper's own
one-sentence framing: a distributed AI economy is "the Linux + App Store for accountable enterprise
AI".

## Where this meets PyForge — observations, not decisions

The paper's vocabulary has a near-neighbour for almost every PyForge surface. The map is for the
Spec to test; each "gap" is a candidate, not a commitment.

| Whitepaper | Nearest thing here today | Gap the paper would name |
|---|---|---|
| Intelligence Hub | The Foundry estate — `src/platform/`, the eight stations, [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md); air-gap by design ([`enterprise-airgap.md`](enterprise-airgap.md)), OCP profile ([`local-ocp-hybrid-environment.md`](local-ocp-hybrid-environment.md)) | Nothing installable *into* the Hub as a Frame/Cog/Op/Guard object; the Hub is code, not a runtime for artifacts |
| Nebi | pixi + conda-forge + this recipe factory + the SelfExplainML channel + the bmad-suite metapackage — the very lineage the paper cites (pixi on conda) | No package format for Frames/Cogs/Ops/Guards; whether Nebi/Nebari are packaged anywhere we can consume is unverified |
| Frames | `CLAUDE.md`, the verified `AGENTS.md` block, `docs/dreams/`, Specs and memlogs, `.claude/memory/` team memory (Scribe), each skill's `SKILL.md`, `docs/governance/` | Inheritance (repo → station → story) is real but informal; no open protocol, no field-level sharing, no feedback channel to an accountable owner beyond git review |
| Cogs | Station skills and personas (`bmad-agent-*`), `conda-forge-expert`, the harness = Claude Code / bmad-loop; the bmad-suite conda packages are the closest "installable unit with declared tools" | Not versioned as a worker with declared permissions and governance parameters; harness choice is not hidden behind a Cog boundary |
| Ops | bmad-loop runs, `marshal factory spin`, the CFE lifecycle loop, pixi tasks, the legacy workflow specs (`feedstock-platform-expansion`, `feedstock-failure-remediation`) | No Op manifest; no *declared* validation strategy per run — the checks exist but are implicit in policy TOML and detectors |
| Guards | ~30 `*-check` detectors, Warden (sole PR verdict), pyforge-doctor sources (advisory), `bmad-review` lenses, [`bmad-eval-quality.md`](bmad-eval-quality.md) (measuring the reviewer) | Categories present: algorithmic, consensus (parallel adversarial review), expert (operator gates), regression/drift (`bmad-drift-check`, spec-surface). Thin or absent: source-grounding of LLM output, outcome Guards |
| Gates | bmad-loop `gate_mode`, `bmad-loop-resolve` escalation, the landing rules of [`pr-lifecycle.md`](pr-lifecycle.md), the operator-confirmation policies in `AGENTS.md` | Autonomy is a repo-wide setting, not granted per engagement — the same observation [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md) makes |
| Tracks | `sprint-status-ledger.yaml`, [`landing-evidence-grammar.md`](landing-evidence-grammar.md), [`durable-runs.md`](durable-runs.md), the deferred-work ledger, run `state.json`, memlogs | No single structured evidence record per run with an explicit retention policy; evidence is spread across several files with different shapes |
| Organizational Memory | Scribe's GraphStore + `.claude/memory/` + per-user auto-memory + `_bmad-output/` | We sit at the paper's simplest tier (a versioned directory); no semantic retrieval over runs, no "ability to forget" policy |
| Desktop/Web Application | The `django-*` station portals, the factory console, the artifact console, Atlas's Vizro board ([`secure-live-dashboards.md`](secure-live-dashboards.md)) | No Frame composition UI, no in-workflow Gate prompts, no Track view for non-admins |
| Marketplace | conda-forge itself, plus the SelfExplainML channel ([`bmad-suite-channel-product.md`](bmad-suite-channel-product.md)) | Exchanges packages, not Frames/Guards with provenance attached |
| Intelligent Ops Factory | The "Dream to Code" pipeline — this repo *is* an ops factory for packaging and station software | The paper's factory produces an organisation's SOPs as installable Ops; ours produces code and recipes |

One honest tension the Spec must carry: the paper lists Claude Code among the rented black boxes,
and this factory runs on it. In the paper's own terms PyForge rents the model and the harness while
owning the context, the workflows, the checks and the evidence — which is exactly the split the
paper says matters most, but it should be stated, not assumed.

## What it might look like when real — candidate shapes for the Spec, none chosen

1. **Vocabulary alignment only.** A mapping from the Charter's Lexicon and the station roster to
   Frames/Cogs/Ops/Guards/Gates/Tracks, recorded once in [`pyforge-charter.md`](pyforge-charter.md)
   or the Unifying Strategy — the cheapest possible realisation; no code.
2. **Frames as first-class.** Once the Frame protocol is published (a Phase 1 milestone in the paper,
   not yet observed when seeded; **published 2026-08-18 as Frame Spec v0.2.0** — RB-1 below),
   publish the repo's own context — the `AGENTS.md` block, station personas,
   the recipe-authoring conventions — as Frame-shaped artifacts with named owners; a Community
   Frame for local-recipes would be the paper's use case 3 applied to ourselves.
   *(RB-3, 2026-09-09: v0.2 conformance is the four frontmatter fields and nothing else — body
   free-form, no section taxonomy, `inherits` resolution recommended not required (frame-spec
   PR #25, merged 2026-09-07). The spec repository ships `tools/frame-reader/SKILL.md` and
   `tools/frame-authoring-assistant/SKILL.md` — PyForge's own skill shape — so this shape is one
   Frame per station inheriting a Company Frame derived from the `AGENTS.md` verified block, a
   reader skill, and git as the store. No registry required.)*
3. **A declared validation strategy per run.** A bmad-loop run or `marshal factory spin` declares its
   Guards by stage, its Gates as threshold rules and its Track contents/retention; the several
   evidence files converge on one structured Track. Landing-evidence grammar and durable-runs are
   the precedents.
4. **Guards as a library.** Expose detectors, Warden axes and review lenses as reusable Guards with a
   declared category (the paper's seven), so a Spec can say which categories it lacks.
   *(RB-3, 2026-09-09: `nebari-dev/provenance-collector-pack` — in-cluster image digest,
   signature, SLSA and SBOM attestation checks, alpha — is a candidate Warden **plugin source**
   under Unifying CAP-18, never a second verdict; it overlaps steward 43.4 "deploy by digest".)*
5. **Package the Nebari/Nebi lineage where missing.** A Mason/CFE lane: verify with `lookup_feedstock`
   and `pypi_intelligence` whether `nebari`, `nebari-infrastructure-core` and `nebi` exist on
   conda-forge or PyPI, and build local recipes if not — a green local build ends the task, no
   external PR without an ask. *(RB-2, 2026-09-06: `nebari` and `nebi` are already on
   conda-forge; only `nebari-infrastructure-core` is missing — the lane narrows to that Go CLI,
   plus the `frames` registry client if wanted.)*
   *(2026-09-09: the local-build half is **already done** — `recipes/nebari-infrastructure-core`
   0.14.0 (`b1f455b029`, with an ARM build fix `60b1bc475f`) and `recipes/nebari-frames` 0.1.7
   (`dd7c4e7eb7`) landed on 2026-09-07, two days before this Dream recorded the lane. What
   remains of shape 5 is only whether either goes to conda-forge, which needs an explicit ask.)*
6. **Foundry Platform as a Nebari Software Pack; NIC as a steward deployment profile.** *(candidate
   added 2026-09-09 from RB-3; not chosen.)* The Foundry Helm chart gains one optional
   `nebariapp.yaml` template — `auth.enforceAtGateway: false`, so `django-allauth` keeps OIDC and
   the nebari-operator only provisions the Keycloak client and its Secret; `routing.publicRoutes`
   for `/ht/` and `/api/health`; a `deviceFlowClient` for the `pyforge` CLI; a Launchpad card — and
   steward gains a NIC profile beside the OCP profile, using NIC's **local kind provider** for an
   attended bring-up of the same class as 12-7 on CRC. PostgreSQL and Redis stay in-chart; NIC's
   Keycloak / Envoy Gateway / cert-manager / ArgoCD play the role the OCP router and OAuth play
   today, so the infra-kinds lock is untouched. Layer 1 *beneath* the Foundry, never the Foundry
   replaced.
7. **Station environments published through Nebi to OCI.** *(candidate added 2026-09-09 from RB-3;
   not chosen.)* `nebi push` of the station pixi workspaces to `quay.io` or the internal registry as
   versioned, rollback-able environment artifacts — the enterprise-mirror / air-gap story on the
   Nebi that exists today (environment management), not a pixi replacement. Nebi's roadmap SBOM and
   compliance checks overlap Warden: watch, do not adopt.

## How alignment with the Unifying Strategy would proceed — candidate, not a decision (2026-09-09)

Recorded after the operator asked what it would take for the evergreen
[`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) to be aligned to this Dream and to
adopt its stack. This is the assessment as given; every line below is a candidate that the Spec
turns into a decision or a non-goal. **Nothing here is chosen.**

**Three readings of "align", which lead to materially different work:**

| Reading | Realises | Cost |
|---|---|---|
| Vocabulary | Shape 1 — the Charter Lexicon speaks Hub / Frame / Cog / Op / Guard / Gate / Track | A recorded Charter amendment; no code |
| Artifact model on the existing stack | Shapes 2, 3, 4 — Frames, a declared validation strategy per run, Guards with categories, one Track per run — on Django + PostgreSQL + Redis + Kubernetes + pixi | Skill, detector and marshal-policy work; Track store foundry-side |
| Layer 1 as a profile as well | Shapes 5, 6, 7 — NIC and `frames` recipes, Foundry as a Software Pack, Nebi push to OCI | A steward deploy profile; attended bring-up; Go recipes |

**What "adopt the stack" can honestly mean today,** by the paper's own honesty table and RB-1..3:
adopt Frame Spec v0.3 as the context format now (the working draft, openteams-ai/frame-spec#28 --
landed by Stories 53.5/53.6; v0.2 was the state when this Dream was written); consume `nebi` and `nebari` from conda-forge as
they are; treat NIC as Layer 1 *beneath* the Foundry, a profile beside OCP; design PyForge's own Op
manifest in the paper's example shape (Frames, Cogs, Guards by stage, Gates as threshold rules,
Track `retain_for` + `include`) so it can be Nebi-packaged once Nebi defines that — no public Op
manifest schema exists. The Foundry *is* the Hub's Layer 2 plus its accountability plane. A sharper
Why than vocabulary: the field guide's six falsifiable indicators — an open Frame spec with
implementations not controlled by OpenTeams; Hubs run by organisations with no OpenTeams
relationship; community Guard libraries with real usage; products around the Hub built by third
parties — are ones PyForge could be independent evidence for.

**Standing rulings the "adopt" reading meets, and the candidate resolution for each:**

| Ruling | Collision | Resolution |
|---|---|---|
| Infra-kinds lock (PostgreSQL + Redis + Kubernetes; DuckDB a library) | `nebari-frames` runs on single-writer SQLite; Collab Hub on fs / S3 / Postgres | Git is the Frame store (the paper's simplest tier, and the guide's own advice); `frames` CLI as validator only; a registry, if ever, is Collab Hub on Postgres. NIC foundation services sit where OCP's router and OAuth sit |
| One PR verdict (Warden) | "Guard" language | Guards are detectors and Warden hook-spec plugins with a declared category; Gates are the verdict plus operator confirmation; nothing mints a second verdict |
| Autonomy is a repo-wide setting (`gate_mode`) | Autonomy granted per engagement | The Op manifest per run is where `gate_mode` becomes per-engagement; converges with [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md) |
| Rented harness (Claude Code on the paper's list) | Cog hides harness choice | The Portability contract in `AGENTS.md` is the Cog boundary; state the split: model and harness rented, context / workflows / checks / evidence owned |
| Air-gap parity | NIC downloads OpenTofu at runtime | Pin conda-forge `opentofu` through `NIC_TOFU_PATH` |
| "No `CAP-20` in the evergreen Spec" (a Never) | New capabilities | They live on `spec-intelligence-hub` with `extends: spec-pyforge-unifying-strategy` under a fourth prefix, `hub:`, beside bare, `pap:` and `fnd:` |
| Living Unifying Dream ≤ 400 lines; historical names stay | Retitling or growing that Dream | Do not retitle; a Grounding bullet and a cross-reference point here; this Dream stays the sibling that carries the whitepaper |

**Candidate sequence,** following the cutover precedent of 2026-09-04 (a Dream section → a derived
Spec that extends the Unifying Strategy → a spine → one steward epic held `blocked` until the
operator iterates):

- **A. Decide and record.** The operator's reading, and the answers to § *Open questions*, land as
  memlog decisions on `spec-intelligence-hub`, then Realization-log entries in both Dreams and a
  Grounding bullet in the Unifying Strategy. Owner stays steward.
- **B. Contract before repo.** `bmad-spec` update → `ready` under the `hub:` prefix;
  `bmad-correct-course` on the Unifying Strategy for a dated Constraints block;
  `bmad-architecture` → a `hub:AD-n` spine; `bmad-create-epics-and-stories` → the next free steward
  epic (45–47 are taken as of 2026-09-09), every story `blocked`; de-register the Spec from doctor's
  `DEFERRED_SPECS`.
- **C. Realise cheapest first, and mind the cutover.** Dreams and memlogs are the only unconditional
  move into `python-foundry`; every rendered artifact is re-derived there. So A and B land now, the
  no-code and doc-only pieces land now, and runtime code waits for the cutover flag so it is built
  once in foundry rather than moved:
  1. Lexicon mapping as a recorded Charter amendment — now.
  2. Eight station Frames inheriting a Company Frame derived from the `AGENTS.md` block, a
     frame-reader skill, an in-repo preflight — now; git as the store, no registry. *(As built:
     six required fields — type, identifier, name, description, visibility, maintainer — and
     NOT a detector; it never joins `detectors`/`detectors-ci`, because Warden stays the sole
     PR verdict. See docs/foundry/frames/README.md.)*
  3. A Guard catalogue as a doctor source deriving the seven categories from a declared attribute on
     each detector, Warden axis and review lens — now; it will show source-grounding and outcome
     Guards missing.
  4. One structured Track per bmad-loop run with stated retention, and a validation block in the
     marshal policy that is the Op manifest — foundry-side.
  5. Mason lane: NIC and the `frames` CLI as Go recipes — **landed 2026-09-07**, ahead of this
     plan; only a conda-forge submission remains, and that needs an ask.
  6. The `nebariapp.yaml` template in the Foundry chart and the NIC kind profile — foundry-side,
     attended like 12-7.
  7. `nebi push` of station workspaces to OCI — foundry-side, after the cutover flag.

**What this would not do:** retitle the Unifying Strategy; mint `CAP-20` on the evergreen Spec;
deploy `nebari-frames` in-cluster as a fourth kind; replace pixi with Nebi; target Nebari classic
(sunsetting); build a marketplace or Desktop/Web Application (Collab Hub is that backend, and stays
a non-goal); vendor the Frame Spec text (no LICENSE); open any external PR.

## What is real

Nothing in the repo yet beyond the whitepaper, this seed and — since 2026-09-05 (evening) — a
`draft` Spec at `spec-intelligence-hub` under pyforge-steward that is the chain link, not the
contract (its five CAPs are the candidate shapes below, none chosen). By the paper's own status table, Cogs
and Ops as installable objects and the Op manifest are "in active development", the Frame protocol
is a milestone not yet published (Revision 9's view; **it shipped 2026-08-18 as Frame Spec
v0.2.0** — RB-1), and the accountability-plane runtime and the marketplace are
"thesis". Dream-first applies: `bmad-spec` under `pyforge-steward` produces the contract, and the
contract chooses among the candidates above before any code.

## Constraints

- **Dream-first.** No code from this file; the Spec decides scope.
- **The whitepaper is the source of record.** This distillation must not drift into claims the paper
  does not make; re-verify any statistic or vendor fact at intake (the paper itself marks entries it
  could not re-verify), and re-fetch by URL + hash before citing a later revision.
- **Copyright.** Distilled in our words with short attributed quotations; the PDF is not tracked and
  is not to be committed.
- **Foundry invariants stand.** `src/platform/` never imports `pyforge.*`; the infra-kinds lock and
  AD-1 (re-affirmed 2026-09-05) are untouched by anything here — the paper's Organizational Memory
  menu is *its* menu, not a licence to add stores to the platform.
- **One PR verdict.** Warden stays the sole gate; doctor findings stay advisory; "Guard" language must
  not mint a second verdict.
- **No implied platform adoption.** Naming Nebari/Nebi here does not adopt them; the Unifying Strategy
  owns the platform shape.
- **No new `docs/specs/` file; no external PRs; no outward dispatch without operator confirmation.**

## Non-goals

- Building a marketplace or a Desktop/Web Application.
- Replacing the Foundry with a Nebari deployment, or `conda-forge-expert` with anything.
- Endorsing or marketing OpenTeams; this is an architecture-and-vocabulary seed.
- Reproducing the whitepaper — this file summarises it; readers who need the text go to the source.

## Open questions for the Spec

- **Owner.** Seeded under `steward` because the Hub is the estate and Steward already owns the
  Unifying Strategy, eval-quality and the channel product. Marshal (Ops, Gates) and Scribe (Frames,
  memory) are the plausible alternatives; owning is becoming at the planning tier, but the planning home is not the package name.
- Is the **Frame protocol** published yet, and where? **Answered 2026-09-06 (RB-1): yes** — Frame
  Spec v0.2.0, released 2026-08-18 at `openteams-ai/frame-spec` (single-file Markdown + YAML
  frontmatter; registries, identity and provenance out of scope; no git tag, no LICENSE file);
  reference registry `nebari-dev/nebari-frames` v0.1.7, beta. The gate on shape 2 is lifted.
- Are **Nebari, `nebari-infrastructure-core`, Nebi** on conda-forge or PyPI, and under what licence?
  **Answered 2026-09-06 (RB-2):** `nebari` yes (2025.10.1, BSD-3-Clause, PyPI-stable parity),
  `nebi` yes and current (0.15, Apache-2.0, four subdirs), `nebari-infrastructure-core` no on
  both (Go, Apache-2.0, GitHub binaries + Homebrew). rxm7706 maintains neither feedstock.
- Which of the **seven Guard categories** does the repo lack entirely, and is source-grounding of LLM
  output the first to add?
- Does a **bmad-loop run** already emit enough to constitute a Track, and what retention would the
  operator want?
- Do we want the repo's **own context published as Frames** (a Community Frame for local-recipes)?
- **Which reading of "align the Unifying Strategy to this Dream"** — vocabulary only, the artifact
  model on the existing stack, or Layer 1 as a NIC profile as well (§ *How alignment … would
  proceed*)? Each is a memlog decision; candidate shapes 6 and 7 exist only under the third.
- Is a **`NebariApp` template** in the Foundry chart wanted while the chart's own ingress and the
  OCP route stay the primary routes — and is the NIC kind profile a steward attended bring-up in
  `local-recipes`, or foundry-side only?
- Is **`nebi push`** of the station workspaces to OCI wanted before the cutover, or only foundry-side?

## Research backlog (pre-Spec)

Two research items queued 2026-09-05 at the operator's request. They are prerequisites for the
Spec, not stories; each closes by appending its finding here (dated, with the evidence) and by
updating the open question it answers. **Both ran on 2026-09-06; findings are recorded inline.** A
third, RB-3, was queued and run on 2026-09-09 when the operator asked what aligning the Unifying
Strategy to this Dream would take.

- **RB-1 — Has the Frame protocol been published?** The paper lists "Frame protocol published" as a
  Phase 1 (now–6 months) milestone and calls the protocol the standard that makes Frame exchange
  possible. Verify: search nebari.dev, the `nebari-dev` GitHub organisation (`gh api
  /orgs/nebari-dev/repos`, `gh search repos --owner nebari-dev frame`), ownyourintelligence.ai and
  OpenTeams' public repositories for a specification, schema or reference implementation. Record the
  URL, version, licence and the file/folder structure it prescribes — or record "not published as of
  <date>". Gates candidate shape 2 (Frames as first-class): nothing Frame-shaped is specified before
  an open specification exists.

  **RB-1 finding — 2026-09-06: published.** Frame Spec **v0.2.0** is public at
  <https://github.com/openteams-ai/frame-spec> (repository created 2026-05-18, made public by
  PR #23 "cleanup/public-release" on 2026-08-19; `CHANGELOG.md` dates the release **2026-08-18**;
  the frozen normative text is `spec/v0.2.md`, 297 lines; `spec/frame-spec.md` is the working
  draft). What it prescribes: a **single Markdown file with YAML frontmatter**; required fields
  `type` (`frame` or `frame [0.2]`), `name`, `description`, `visibility`; recommended `version`,
  `scope`, `maintainer`, `inherits`; the body is ordinary Markdown loaded as system context;
  inheritance is explicit via `inherits`, child over parents, parents read in order, transitive
  resolution optional. Deliberately **not** defined in v0.2: package manifests, canonical
  identity, provenance, review workflows, registries, runtime management; the directory form
  (`frame.md` + assets) is deferred. In-repo tooling: `tools/validate_frames.py` (a v0.2 field
  preflight, also run as a GitHub Action), `tools/frame-builder.html`, two authoring prompts, and
  `examples/` (minimal, complete, meeting-notes inheritance, and a future-facing
  `nebi-frame-package/` with `frame/package.yaml`). Caveats: the README's `releases/tag/v0.2.0`
  link returns 404 — **no git tag or release object exists**, the release is the changelog entry
  plus the frozen file — and the repository has **no LICENSE file** (GitHub reports none), so the
  spec text's reuse terms are unstated. Reference implementation:
  <https://github.com/nebari-dev/nebari-frames> (Go, Apache-2.0, **v0.1.7** on 2026-08-19,
  self-declared *beta*: backend + `frames` CLI + web app + MCP endpoint; Helm chart
  `oci://quay.io/nebari/charts/nebari-frames`; release binaries for linux / darwin / windows on
  amd64 + arm64 and a `frames.rb` formula in `nebari-dev/homebrew-tap`; successor of `skillsctl`).
  It stores Frames in a richer ten-slot YAML schema (terminology, rules, skills, prompts,
  tool_specs, goals, style, norms, architecture, business_process) with `extends` inheritance and
  RBAC, and round-trips a conformant `.frame.md` (`type: frame [0.2]`, one `##` section per slot)
  that passes the spec's validator; `visibility` there is declared intent, not access control.
  Ecosystem status per the spec's own `docs/ecosystem.md`: **no Cog spec exists**; Ops were
  renamed from "Progs"; Collab (openteams.com/collab) is the desktop client, its hub (formerly
  "Nexus") private-invitation only; **Nebi does not define or ship Frame support**
  (`docs/nebi-integration.md` is exploratory). The ownyourintelligence.ai field guide (July 2026,
  Revision 7) that reported "no published specification" predates the release. The whitepaper's
  source repository is <https://github.com/openteams-ai/inthub-whitepaper> (tag `v9` = Revision 9,
  2026-08-17). **Effect:** the gate on candidate shape 2 is lifted; what remains is the operator's
  choice.
- **RB-2 — Are Nebari, `nebari-infrastructure-core` and Nebi on conda-forge (and PyPI)?** Verify each
  name — plus the hyphen/underscore, `-py` and `-python` spellings the PyPI→conda mapping rule
  requires — with `lookup_feedstock`, `get_conda_name` and `pypi_intelligence` from the conda-forge
  MCP server, and cross-check the `nebari-dev` GitHub organisation for the source repositories.
  Record feedstock / PyPI name, latest version, licence, maintainers and whether rxm7706 can modify
  the feedstock. Gates candidate shape 5 (package the lineage where missing); this is a Mason /
  `conda-forge-expert` lane — a green local build ends the task, and no external PR is opened
  without an ask.

  **RB-2 finding — 2026-09-06: two of the three are already on conda-forge.** Checked against live
  `channeldata.json`, `lookup_feedstock` and PyPI's JSON API, four spellings each (bare,
  hyphen↔underscore, `-py`, `-python`) plus the `python-` prefix:
  - **`nebari`** — conda-forge **yes**: `conda-forge/nebari-feedstock` (v0 `meta.yaml`,
    `noarch: python`, `__unix`-only run), **2025.10.1**, BSD-3-Clause, maintainers marcelovilla /
    dcmcand / viniciusdc — **rxm7706 is not a maintainer**; last pushed 2026-04-22, no open PRs.
    PyPI **yes**: latest stable **2025.10.1** (2025-11-04); `2026.3.1rc1` / `rc2` are pre-releases
    and the GitHub release `2026.3.1` (2026-07-17) was **never uploaded to PyPI**, so the feedstock
    sits at PyPI-stable parity, not GitHub parity. nebari.dev now labels this "Nebari classic
    (sunsetting)"; the successor is "Nebari core" (NIC, early access). `nebari-dask` 2025.6.1 is a
    sibling noarch package.
  - **`nebari-infrastructure-core`** (NIC) — conda-forge **no** (all spellings; no feedstock),
    PyPI **no** (404). Go CLI, Apache-2.0, **v0.14.0** (2026-08-25); distributed as GitHub-release
    tarballs for linux / darwin (x86_64 + arm64) and windows (x86_64 + arm64) with a source
    tarball, per-asset SBOMs and sigstore-signed checksums, plus a `nic` Homebrew cask. It downloads
    and manages its own OpenTofu binary at runtime (`NIC_TOFU_PATH` or `tofu` on PATH overrides;
    conda-forge ships `opentofu` 1.12.6). A conda recipe would be a Go source build with
    `go-licenses` — the shape `nebi-feedstock` already uses.
  - **`nebi`** — conda-forge **yes and current**: `conda-forge/nebi-feedstock` (v1 `recipe.yaml`,
    multi-output `nebi-cli` / `nebi-desktop` / `nebi`), **0.15** = upstream v0.15 (2026-08-27),
    Apache-2.0, linux-64 / osx-64 / osx-arm64 / win-64, Go + nodejs build, maintainers viniciusdc /
    Adam-D-Lewis / aktech / pmeier — **rxm7706 is not a maintainer**. PyPI **no** (Go; never
    published there). `nb-nebi-kernels` (a Jupyter KernelSpecManager for nebi workspaces) is not
    packaged anywhere.
  - Also absent from conda-forge: the `frames` registry client (`nebari-frames`) and `skillsctl`.
  Tool notes: `get_conda_name` returned the identity name for all three via the metadata API —
  a fall-through, not evidence of existence; `pypi_intelligence` is a ranked-candidate listing
  with no per-name filter, so it does not apply to a named lookup. **Effect:** candidate shape 5
  narrows to one Go CLI (NIC), plus the `frames` client if the operator wants the registry
  consumable from pixi; no external PR is implied — a green local build ends that lane.
- **RB-3 — What does the field guide add, and what in the Nebari stack is actually ready?** Queued
  and run 2026-09-09 at the operator's request. Sources: every page of ownyourintelligence.ai (by
  sitemap), the whitepaper PDF re-fetched and hash-compared, `openteams-ai/frame-spec` at HEAD, and
  all 76 public `nebari-dev` repositories via the GitHub API, reading each `pack-metadata.yaml`
  where one exists. Gates the candidate approach above and shapes 6–7.

  **RB-3 finding — 2026-09-09.**
  - *The site is a reading, not a source.* Its status audit (2026-08-18) predates the Frame Spec by
    one day and still says "no published specification"; this Dream is ahead of it. It adds a
    glossary, a 15-question FAQ (FAQ 14: a small firm's first step is a Company Frame in "an
    afternoon and a strong opinion about how the company talks"; FAQ 12: MCP is complementary
    Cog-layer plumbing; FAQ 7: "the recursion … terminates in humans at Gates"), the advice to start
    Organizational Memory as versioned Frame files in git, and six falsifiable indicators: (1) the
    Frame protocol as a genuinely open specification with implementations not controlled by
    OpenTeams; (2) Hubs deployed by organisations with no OpenTeams relationship; (3) marketplace
    liquidity from third-party Ops and Frames; (4) community Guard libraries with real usage; (5) one
    vertical where Frame-based context exchange is normal practice; (6) products around the Hub
    built by parties other than the steward. The PDF is byte-identical to the hash under § Source.
  - *The Frame Spec got simpler.* PR #25 "Make the spec's minimalism unmistakable" (merged
    2026-09-07): conformance = the four required frontmatter fields, nothing else; the body is
    free-form with no section taxonomy (a reader had generated ten dutiful sections from
    `docs/overview.md` and concluded the spec was too heavy); resolving `inherits` is recommended,
    not required; new `examples/code-review-norms/` (four fields, no headings, all value in the
    body). The repo ships `tools/frame-reader/SKILL.md`, `tools/frame-authoring-assistant/SKILL.md`,
    `tools/validate_frames.py` (7 tests, 18/18 examples), and `USING-FRAMES.md`. Still no LICENSE
    file and no git tag; `spec/v0.2.md` and the working draft are identical.
  - *What is ready, derived from `pack-metadata.yaml`* (19 packs declare a level; 14 are tracked by
    the dashboard):

    | Level | Packs |
    |---|---|
    | beta | data-science, nebi-pack, lgtm, skillsctl, rayserve, llm-serving, superset, nebari-frames, collab-hub |
    | alpha | chat, mlflow, provenance-collector, langfuse, harbor |
    | experimental | pi-coding-agent, apps, nebari-catalog, dask-gateway, unity-catalog |

    The ladder (`release-readiness-checklist.md`): experimental → alpha ("installs and runs the happy
    path on a current NIC dev cluster") → beta ("customer pilots with engineering support; values may
    change") → GA (`v1.0.0`+, EffVer tags). No pack is GA.
  - *NIC* (`nebari-infrastructure-core` v0.14.0, Go 1.26+, Apache-2.0) is "an opinionated Kubernetes
    distribution": OpenTofu provisions the cluster, ArgoCD installs Keycloak + Envoy Gateway +
    cert-manager + an OpenTelemetry Collector, and the nebari-operator reconciles `NebariApp`
    resources into HTTPRoute + TLS + OIDC. Providers: AWS EKS, GCP GKE, Azure AKS, Hetzner k3s,
    **local kind** (`examples/local-config.yaml`, Docker required) and `existing` (k3d / k3s /
    minikube / managed, no provisioning). Its README: "under heavy development and very unstable …
    not yet suitable for production". Every deployment gets a Launchpad landing page.
  - *`NebariApp` CRD* (`reconcilers.nebari.dev/v1`; the template tracks operator
    `v0.1.0-alpha.19`): `auth.enforceAtGateway: false` makes the operator provision the Keycloak
    client and a `<name>-oidc-client` Secret (`client-id`, `client-secret`, `issuer-url`) while "the
    app handles OAuth natively" — the Foundry's `django-allauth` path; `deviceFlowClient` provisions a
    public client for RFC 8628 CLIs; `routing.publicRoutes` bypass auth (probes); `landingPage` adds
    the Launchpad card; `gateway: public | internal`. A pack may be Helm, Kustomize or plain YAML;
    template example 5 wraps an existing chart.
  - *Nebi* is alpha ("not recommended for production"): server + CLI + desktop; pixi workspaces
    pushed, pulled, diffed and rolled back by tag, published to any OCI registry, under RBAC + OIDC.
    `nebi-pack` (beta) runs it on **PostgreSQL + Keycloak** — not a fourth infra kind.
    `nebari-environments` publishes community pixi environments as OCI artifacts through it. Roadmap
    on nebari.dev: SBoM generation and compliance checking. Still no Frame / Cog / Op / Guard
    packaging.
  - *`nebari-frames`* (beta, v0.1.7): Go backend + `frames` CLI (Homebrew tap) + web app + `/mcp`
    (`create_frame` / `update_frame` tools since 2026-08-21); the chart wants a NIC cluster but the
    binary runs standalone with self-managed OIDC (`OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`,
    `OIDC_DEVICE_CLIENT_ID`); SQLite single-writer, `replicaCount: 1`; one organisation in the MVP;
    Frames consumable by any MCP client "or by Claude Code through file install"; its demo note:
    MCP/Claude needs manual Keycloak realm configuration (dynamic client registration).
  - *`collab-hub-pack`* (beta, v0.1.0, pushed 2026-09-09) is the Desktop/Web Application backend
    ("Collab"): FastAPI; a Frames store (filesystem, S3 or Postgres); Slack / Gmail / Calendar / Drive
    connectors; a Keycloak user directory; scheduled tasks; an MCP server; client "Apollo desktop".
    Confirms the Desktop/Web Application non-goal — it exists upstream.
  - *Guard-shaped and kin:* `provenance-collector-pack` (alpha, BSD-3-Clause) — a CronJob that
    discovers running images and Helm releases, resolves digests, verifies signatures, checks SLSA
    provenance and SBOM attestations, and emits a JSON report with a dashboard and Grafana views.
    `skillsctl` (beta) — a Claude Code skill registry (CLI + backend), predecessor of nebari-frames;
    kin to SKF, not an adoption. `chat-pack` (alpha) — React + a Ravnar AG-UI agent server with
    pydantic-ai tools. `nebari-catalog-pack` (experimental) — "a pack that installs packs" from an OCI
    registry into the GitOps repo: the marketplace in miniature.
  - *Op manifest:* no schema exists anywhere public. The guide's `/guide/guards-gates-tracks/` shows
    only the paper's YAML-style example (`op` → `frames`, `cogs`, `guards` by `preflight` /
    `in_flight` / `post_run`, `gates` as `if … then …` threshold rules, `track` with `retain_for` and
    `include`). PyForge's manifest is ours to define in that shape.
  - Tool notes: `gh api --paginate orgs/nebari-dev/repos`; the pack fields that matter are `level`,
    `nebariapp_integration`, `scope.standalone-supported`, `last_promoted_at`, `demo_notes`.

  **Effect:** shape 1 gains its Why (the indicators); shape 2 is cheaper than seeded (four fields, a
  reader skill, git as the store); shape 4 gains a plugin source; shape 5's local-build half was found already executed
  (both recipes landed 2026-09-07); shapes 6 and 7 are added as candidates; the Desktop/Web Application non-goal is confirmed by Collab Hub.
  Three open questions added under § *Open questions for the Spec*. Nothing chosen.

## Kinships

- [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) — the Foundry as the owned Hub; the
  platform shape this seed must not re-decide.
- [`pyforge-charter.md`](pyforge-charter.md) — the Guild and its Lexicon; Smiths are the nearest
  thing to Cogs, and the Lexicon is where a vocabulary alignment would land.
- [`packaging-factory.md`](packaging-factory.md), [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md),
  [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md) — the conda/pixi lineage the paper cites as
  Nebi's own foundation; the channel as a marketplace in miniature.
- [`bmad-eval-quality.md`](bmad-eval-quality.md), [`risk-tiered-review-depth.md`](risk-tiered-review-depth.md)
  — Guards on the reviewer and risk-proportional validation: the accountability plane already
  arriving piecemeal.
- [`landing-evidence-grammar.md`](landing-evidence-grammar.md), [`durable-runs.md`](durable-runs.md),
  [`deferred-work-visibility.md`](deferred-work-visibility.md), [`pr-lifecycle.md`](pr-lifecycle.md) —
  Tracks and Gates as we practise them today.
- [`team-memory.md`](team-memory.md) (archived into [`pyforge-scribe.md`](pyforge-scribe.md)) —
  Organizational Memory at the paper's simplest tier.
- [`agentic-sdlc-autonomy.md`](agentic-sdlc-autonomy.md) — the four views of autonomy; the paper's
  "autonomy granted per engagement" is the same axis seen from the employer's side.
- [`agent-portability.md`](agent-portability.md) (archived) — harness-agnostic Cogs echo the
  Portability contract in `AGENTS.md`.
- [`enterprise-airgap.md`](enterprise-airgap.md), [`local-ocp-hybrid-environment.md`](local-ocp-hybrid-environment.md)
  — sovereignty as we already build it.
- [`regenerable-factory.md`](regenerable-factory.md) — the Dream → Spec → code chain is our Frame
  inheritance graph and our Track of record at once.

## Realization log

- **2026-09-14 (later)** — **Frame Spec v0.3 adopted in full** (Story 53.6), on the operator ruling
  *"we move forward by adopting frame-spec v0.3 — the PR will merge, and no point starting with an
  outdated version."* 53.5 had stamped `type: frame [0.3]` while the nine Frames still carried a
  v0.2-shaped body, so the estate was conforming to neither version. Read against the normative
  profile fetched from the PR head (`spec/profile/frame-core.csv` + `spec/frame-spec.md`), four
  things changed: `identifier` became a **qualified-ref** (`pyforge/company`, `pyforge/<station>`)
  where §4.2.1 SHOULDs a URI or `publisher "/" frame-name`; `name` became the Charter's prose form
  (`PyForge Steward`), since the element profile marks `title` — which `name` aliases — MUST NOT be
  slug-constrained, and the old slug collided with the Python distribution name; `maintainer` and
  `inherits` became sequences (§6.2.1, *"A writer MUST emit a sequence"*); and the unregistered
  `owner:` collapsed into the registered repeatable `maintainer`. The keys `name`/`inherits` are
  deliberately KEPT — §6.2.1 requires those aliases of a Markdown writer, and `title`/`composition`
  belong to the YAML/JSON encodings only. The preflight was re-keyed from `name` (a label) onto
  `identifier` (the identity), and gained a `scalar-repeatable` finding so the sequence rule cannot
  rot back. Residual exposure recorded, not hidden: #28 is still open, so if its element registry
  moves before merge the nine Frames and `frames.py` are re-run from the same profile CSV.

- **2026-09-05** — Seeded from the whitepaper (Revision 9, August 2026), read in full (46 pages);
  section-complete distillation with the vocabulary map, candidate shapes and open questions above.
  No adoption decided; owner `steward` as the post. Next: `bmad-spec` under `pyforge-steward`
  (dream-chain INV-1 names the expected Spec path) to choose which shape PyForge takes up.
- **2026-09-05 (later)** — Research backlog added at the operator's request: RB-1 (is the Frame
  protocol published?) and RB-2 (are Nebari, `nebari-infrastructure-core` and Nebi on conda-forge /
  PyPI?). Neither has been run; both precede the Spec.
- **2026-09-05 (evening)** — `bmad-spec` (headless/express) seeded `spec-intelligence-hub` under
  pyforge-steward as a **`draft`**: the five candidate shapes are CAP-1..5 (none chosen), the six
  open questions incl. RB-1/RB-2 ride the Spec's `open_questions`, and `vocabulary-map.md` carries
  the table above. Registered in doctor's `DEFERRED_SPECS` so chain-completeness does not demand
  epics for unchosen shapes; dream-chain INV-1 clears. Status stays `dreamt` — README: `specified`
  needs a Spec at `ready` or beyond, and RB-1/RB-2 still precede the contract.
- **2026-09-06** — RB-1 and RB-2 run and closed above. RB-1: the Frame protocol **is** published —
  Frame Spec v0.2.0 (2026-08-18, `openteams-ai/frame-spec`; no tag, no LICENSE file) with
  `nebari-dev/nebari-frames` v0.1.7 as a beta reference registry; the field guide's "not
  published" claim predates it. RB-2: `nebari` (2025.10.1) and `nebi` (0.15, current) are on
  conda-forge; `nebari-infrastructure-core` is absent from conda-forge and PyPI (Go; GitHub
  binaries + Homebrew). The whitepaper's canonical repository (`openteams-ai/inthub-whitepaper`,
  tag `v9`) is recorded under § Source. The Spec's two research questions closed and two derived
  ones took their place (package NIC + `frames`? author the first conformant Frame now?). Status
  stays `dreamt`: the shape decision is still the operator's.
- **2026-09-09** — Operator asked how the evergreen Unifying Strategy would be aligned to this
  Dream and adopt its stack; the assessment was given in-session and now lives here so it stays
  with the seed. RB-3 run and closed (field guide, `openteams-ai/frame-spec` at HEAD, all 76
  `nebari-dev` repositories with maturity derived from `pack-metadata.yaml`, the `NebariApp` CRD).
  Candidate shapes 2 and 4 glossed; shapes 6 (Foundry as a Software Pack, NIC as a steward
  profile) and 7 (Nebi push of station workspaces to OCI) added as candidates; § *How alignment
  with the Unifying Strategy would proceed* records the three readings, the collisions with
  standing rulings and their candidate resolutions, and the A → B → C sequence with its
  now-versus-foundry split. Three open questions added. Still no adoption decided; status stays
  `dreamt`; `spec-intelligence-hub` (`draft`) re-derives from here.
- **2026-09-09 (later)** — Correction from the Unifying Strategy currency review
  (`research/currency-review-pyforge-unifying-strategy-2026-09-09.md`): the recipes shape 5 names
  had already landed on 2026-09-07 (`recipes/nebari-infrastructure-core` 0.14.0,
  `recipes/nebari-frames` 0.1.7), before this Dream recorded the lane. Shape 5, sequence item 5
  and RB-3's Effect line corrected. The same review found the kinship edge to the Unifying Strategy
  was one-way; that Dream now lists this one.
- **2026-09-09 (fleet readiness pass)** — **All nine open questions answered as one operator-approved bundle** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md` § 2.3 **C4**: B6–B11 plus the three questions this Dream gained earlier the same day, plus `guild-E3`). Owner stays **steward**, with `hub:CAP-3` relaying to marshal and CAP-2's Frame-store half to scribe. Verified against live code: the seven Guard categories map to five present surfaces, **Source-Grounding exists at exactly one site** (`scribe/recall.py` AD-8) and **Outcome is absent entirely** — and Outcome Guards are blocked on [`build-league-scorecard.md`](build-league-scorecard.md)'s parked measure set, making the two Dreams a dependency pair. A bmad-loop run emits ~60 % of a Track across five files in a **gitignored** Tier-3 dir, missing model/adapter version, human approvals and any retention statement — so one tracked `track.json` per run is assembled, Tracks kept indefinitely and the raw payload 90 days. Frames: yes, minimally and privately (one Company Frame from the `AGENTS.md` verified block + eight station Frames that `inherits` it, git as the store; no Community Frame, no registry), authored **now**, with CAP-2's success rewritten to an **in-repo four-field preflight** rather than upstream's unlicensed `tools/validate_frames.py`. Shape 5's residue is a conda-forge submission decision only — **not now**. `NebariApp`/NIC-kind profile and `nebi push` are **foundry-side**, and any `hub:` NIC-profile story is gated on the first green `ocp-portability-smoke` run. Escalation resolved: `spec-pyforge-unifying-strategy`'s `realization-gate-home` open question depended on this Spec reaching `ready`; **`spec-intelligence-hub` flips `draft` → `ready`** in this pass, so Epic 49's re-home to `hub:CAP-*` is unblocked and pending that Spec's re-derive. This Dream's own **status stays `dreamt` in this pass and flips to `specified` when the Spec's re-derive lands `ready`** (`docs/dreams/README.md:71` — `specified` requires a Spec at `ready` or better).
- **2026-09-13** — Steward Epic 53 minted (`spec-intelligence-hub hub:CAP-1..4`) and landed all
  five stories the same pass: 53.1 (Charter carries the Hub vocabulary map + reverse cross-walk,
  guild-E3), 53.2 (Company + eight station Frames pass the in-repo four-field preflight, B9/B11),
  53.3 (one tracked `track.json` per run, B8), 53.4 (Guards library, Source-Grounding first per
  B7), 53.5 (adopted the frame-spec v0.3 working draft, Apache-2.0). CAP-5 (package the
  Nebari/Nebi lineage) intentionally stays mason lane — no story minted on this steward epic for
  it. Doctor's `DEFERRED_SPECS` entry for this Spec was removed in the same pass.
- **2026-09-14** — Found live (fleet-picture follow-up audit): the `specified`/`realized` status
  flips this Dream's own 2026-09-05/09-09 entries promised never landed in the frontmatter, and
  `spec-intelligence-hub/SPEC.md` still read `status: ready` despite Epic 53 being 5/5 done.
  Corrected directly — Dream status `dreamt` → `realized`, Spec status `ready` → `shipped` — no
  new work, no re-derive; both flips are bookkeeping only, mirroring the Epic 53 completion
  already on record above.

- **2026-09-16** — Frame draft re-grounding recorded on the station Dream
  ([[pyforge-steward]] § 2026-09-16, `spec-pyforge-steward` CAP-6) per
  Dream-append-first: #28 dropped the version token, #29 added the reference
  validator and made a conformance profile a MUST (§7). Our nine Frames pass
  upstream's validator at `4596579`; we go bare `type: frame` and publish
  PyForge's profile. This Dream stays the Frames' home until the steward fold.

## 2026-09-17 — A ticket moves once, both boards know (folded from jira-github-projects-sync)

# A ticket moves once, both boards know

## The Dream

Two boards, one truth. Whoever moves a card — a developer dragging a GitHub
Projects V2 item to "Done," a PM transitioning a Jira issue from a Cloud
dashboard — the other board reflects it without a human re-typing anything,
without a third-party SaaS bridge (Unito, Exalate) in the loop, and without
the two systems ever chasing their own tail (Jira updates GitHub updates
Jira updates GitHub...). Status, assignee, and the identity link between a
GitHub item and its Jira issue stay synchronized close to real-time, and the
sync engine is boring in exactly the way infrastructure should be: cheap to
run, idempotent, and impossible to accidentally DDoS itself with.

A full technical write-up already exists — PRD, both candidate
architectures (including a concrete normalized PostgreSQL schema for both
systems plus a control-plane bridge layer for Mode B), epics/stories, and an
acceptance checklist — captured and kept current at
`docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md`
(now v1.1, after two follow-up drops of real technical detail were distilled
in place). This Dream distills the aspiration and cites that single document
as the load-bearing source; the deep technical detail (API payloads, SQL
DDL, workflow YAML shapes) lives there for `bmad-spec` (or the fuller
planning chain) to distill when this Dream moves past `dreamt`.

## What it looks like when real

- Moving a GitHub Projects V2 item's status reaches the linked Jira issue,
  and moving a Jira issue's status reaches the linked GitHub item — in each
  direction, without the human doing anything on the other side.
- The two systems never loop: an update one side makes because of a sync
  never triggers a sync back the other way. The intake document now documents
  two candidate mechanisms — Mode A's bot-identity guard clauses, and Mode
  B's time-based check (compare an item's own `updated_at` against the
  sync engine's own `last_sync_timestamp`) — either is a viable starting
  point, not a foregone conclusion.
- Re-processing the same update payload twice produces the same end state
  both times — no duplicate transitions, no double-counted history.
- An item missing its cross-system link fails loud in a log, never
  silently, and never crashes the pipeline for every other item.
- Credentials (GitHub fine-grained PAT, Jira API token) are least-privilege
  and live in secrets storage, never in a repo, never in a log line.
- Status *vocabulary* differences between the two systems ("Done" vs.
  "Closed") are translated explicitly, never assumed to match — a wrong
  exact string sent to either API fails outright.
- Whichever architecture mode ships (real-time serverless via GitHub
  Actions + Jira Automations, or scheduled batch via `dlt` + PostgreSQL, or
  a deliberate combination) is a decision the Spec/architecture phase makes
  explicitly — this Dream does not pre-commit to one over the other.

## What is real

- **The intake material is a single, current document** (v1.1) at
  `docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md`
  — PRD, NFRs, both architecture modes, a concrete normalized PostgreSQL
  schema for both GitHub and Jira, a three-table control-plane bridge layer
  (entity linking, per-field sync-direction config, value translation),
  epics/stories, and an acceptance checklist. Everything from the original
  v1.0 handoff plus two follow-up technical drops, merged in place rather
  than scattered across separate files.
- No code, no GitHub Actions workflow, no Jira Automation rule, no `dlt`
  pipeline exists yet anywhere in this repo. Zero execution weight.
- **Two due-diligence findings already on record, not to re-litigate**:
  **Steampipe** (SQL over both APIs, no dedicated DB needed) was evaluated
  and rejected — its plugins are read-only, ruling it out as Mode B's
  reverse-ETL write path, though it may still be worth a look purely as a
  read-side convenience. **Octosync** (an existing open-source, Dockerized
  GitHub↔Jira sync tool — the closest off-the-shelf match to this Dream's
  own goal) was also evaluated and rejected: unmaintained ~5 years, real
  risk of incompatibility with current API authentication.
- **A known GitHub API limitation is on record**: `updateProjectV2ItemFieldValue`
  (used by both Mode A's Flow A2 and Mode B's reverse-ETL) can update the
  underlying data correctly while leaving the board UI's grouping index
  stale — a moved card can visually appear "stuck" until a manual
  drag-drop. An accepted, documented UX quirk to design around, not a bug
  in this system's own logic (verify against GitHub's issue tracker at
  implementation time whether it's since been fixed).
- **Two competing data-model shapes exist for Mode B, unreconciled on
  purpose**: the original flat single-table sketch (a direct
  `custom_status` column, simpler diff view) versus a fully normalized,
  EAV-style schema plus control plane (more general, handles arbitrary
  custom fields uniformly, needs the bridge tables to make the join
  tractable). Which one Mode B actually ships — and whether the
  control-plane's entity-bridge table *replaces* the original document's
  simpler `custom_jira_key`/`github_item_id` custom-field linking, or the
  two coexist — is an explicit open question for the architecture phase,
  not resolved by either draft existing.
- **Targets an *external* GitHub/Jira project pair** *(settled 2026-08-08; was
  open)*. The intake document is written generically ("PROJ" as a placeholder
  project key) and does not say, which left this open through the Spec draft. It is
  now decided: an external board pair, independent of this repo's own
  `sprint-status-ledger.yaml`, dashboard or story flow — and this engine never reads
  or writes any of them. This is the decision that settles the owner, below.
- **Owner: `steward`** *(settled 2026-08-08; was provisionally `marshal`)*. The
  provisional call reasoned that a sync pipeline "matches marshal's harness-owner
  and cross-system-visibility mandate," with the caveat that this only holds *if
  the sync targets this repo's own tracking*. That caveat turned out to be the
  whole question: under the Marshal/Steward seam — Marshal owns the build line,
  Steward owns the estate the line stands on — an engine syncing this repo's own
  ledger is build-line machinery, and an engine syncing two **external** boards is
  an integration service on the estate. With the scope question answered as
  *external pair*, the ownership follows mechanically rather than by argument. The
  credential-led NFRs landing on Steward's existing `keys` surface is corroboration,
  not the reason.

## Constraints

- No third-party sync SaaS (Unito, Exalate, etc.) — the intake document's own
  stated non-goal, reinforced by due diligence (Octosync, the closest
  existing off-the-shelf tool, was evaluated and rejected as unmaintained,
  not merely dismissed on principle).
- Zero-loop and idempotency are non-negotiable NFRs, not aspirational —
  whatever mode ships must demonstrate both, not just claim them.
- Credentials never committed, never logged, least-privilege scoped.
- The `updateProjectV2ItemFieldValue` grouping-index limitation must be
  designed around as a known, accepted UX quirk — not silently assumed
  away, and not mistaken for a bug in this system's own logic if it
  surfaces during implementation.

## Non-goals

- Not a request to pick Mode A vs. Mode B here — that decision belongs to
  the architecture phase, informed by real usage patterns (real-time need
  vs. audit-trail/reporting need) this Dream does not have yet.
- Not a request to pick the flat vs. normalized Mode B schema shape either
  — same reasoning, same phase.
- Not (necessarily) about this repo's own project tracking — scope
  (external project vs. this repo) is an open question, not a foregone
  conclusion.

## Realization log

- **2026-08-03** — Captured from a complete, externally-authored PRD/
  architecture write-up (v1.0) handed in whole. Preserved at
  `docs/intake/jira-github-projects-sync/`.
- **2026-08-03** — Two follow-up drops (a recap with a known GitHub API bug
  + Steampipe/Octosync evaluation, and two rounds of concrete PostgreSQL
  DDL — GitHub schema, Jira schema, then the control-plane bridge tables
  that reconcile them) were distilled and merged directly into the intake
  document in place (now v1.1), after first drafting them as a separate
  addendum and then consolidating on explicit instruction: one updated
  intake file, one updated Dream, no satellite documents. The intake file
  was also renamed off "-v1-spec.md" — this repo's Lexicon reserves capital-S
  "Spec" for the BMAD Tier-2 five-field contract, and this document is
  Tier-0 grounding material, not that — to
  "-prd-and-architecture.md", matching what the document actually is per
  its own header. Still not specified, not scoped to a target project, not
  acted on.
- **2026-08-08 (scoped and re-owned)** — During the fleet-wide re-triage that
  accompanied the Marshal planning rewrite, this Dream's two standing questions
  turned out to be one. The Spec framed target-scope (Q1) and owner-station (Q5) as
  independent; under the Marshal/Steward seam ratified the same day — Marshal owns
  the build line, Steward owns the estate it stands on — Q1 *determines* Q5, because
  syncing this repo's own ledger would be build-line machinery while syncing two
  external boards is an estate service. Operator answered Q1: **external pair**.
  Owner therefore moved `marshal` → **`steward`**, and the chain relocated from
  `pyforge-marshal` to `pyforge-steward` per INV-2 (the chain follows the owner).
  Five open questions became three. Still greenfield — nothing built, no epic in the
  Marshal rewrite, and no live board named yet.

## 2026-09-17 — Langflow integrates into a cookiecutter-django project without fighting it (folded from langflow-django-plugin)

# Langflow integrates into a cookiecutter-django project without fighting it

## The Dream

`cookiecutter-django` gives a project a robust, opinionated ecosystem —
Docker, Uvicorn, Celery, PostgreSQL — and Langflow (v1.11.2) is a
FastAPI/SQLAlchemy application with its own migration and process model.
Bolting the two together forces a choice between tight coupling (one
process, one deploy) and loose coupling (separate services talking over
HTTP) — and the right choice depends on constraints (deployment topology,
scale, how much of Langflow's own UI is wanted) that vary per project. No
single pattern is universally right, so the dream is a small, named set of
integration architectures a project can pick from deliberately, each with
its own data-ownership story, dependency footprint, and failure mode —
not a single hard-coded "the" way to wire Langflow into Django.

## What it looks like when real

Four named patterns, each usable independently:

**Pattern A — ASGI Reusable App (primary, tightly coupled).** A Django data
migration (`RunSQL`) provisions an isolated PostgreSQL schema
(`langflow_schema`) in the SAME database as the Django project
(`[cookiecutter_project_db]`: `public` owned by Django's ORM via `manage.py
migrate`, `langflow_schema` owned by Langflow's own Alembic migrations at
Uvicorn startup). Langflow's `LANGFLOW_DATABASE_URL` carries a
`search_path` option so its SQLAlchemy/Alembic layer never touches the
`public` schema — no Django ORM collision, one database, one connection
pool. A custom ASGI dispatcher (`langflow_integration/asgi.py`) sits at the
root of the routing stack and forwards `/api/v1/`, `/health`, and
`/langflow/` to the embedded FastAPI app; everything else falls through to
Django. One process, one deploy, one Uvicorn.

**Pattern B — Native Python Execution (no server, loosest coupling).**
Langflow graphs are designed once (locally, via the Langflow UI or however)
and exported as static `.json` flow files committed to the Django repo.
Django views call `langflow.load.run_flow_from_json()` directly — a plain
library call, not an HTTP round-trip — to execute a graph synchronously.
No Langflow server, no extra process, no network hop; the tradeoff is that
flows are static artifacts, not live-editable through a running UI.

**Pattern C — Web Component Integration (frontend-only, microservice).**
Langflow runs as its own container in `docker-compose.yml`, fully separate
from Django — no shared database, no shared process. Django templates load
the `<langflow-chat>` web component from a CDN and point it at the
Langflow container's own API URL, rendering a floating chat widget whose
traffic goes straight from the browser to Langflow, bypassing the Django
backend entirely.

**Pattern D — Asynchronous Celery Execution (scalable backend, decoupled
compute).** Django captures user input and immediately hands it to Celery
via Redis rather than blocking the request on LLM inference latency. A
Celery worker makes an internal HTTP call (`httpx`) to the adjacent
Langflow container, gets the result, and writes it back into Django's own
database — Django and Langflow stay separate services, but the response
still lands in Django's data model instead of only existing inside
Langflow.

Realized means: a project can name which pattern it wants, follow a
concrete recipe for it (schema/migration steps for A, the library-call
shape for B, the compose + CDN snippet for C, the task/worker wiring for
D), and get a working integration without re-deriving the tradeoffs from
scratch each time.

## Constraints

- **Pattern A** needs `search_path` isolation to be real, not aspirational
  — Langflow's migrations must never be able to reach the `public` schema,
  and Django's ORM must never be pointed at `langflow_schema`. This is the
  one pattern where getting the boundary wrong causes silent data corruption
  across two ORMs sharing one database.
- **Pattern D** trades latency for durability: the HTTP call from Celery
  worker to Langflow container is a new failure mode (timeout, connection
  refused, partial response) that pattern A/B never have, since they never
  cross a process boundary for the actual inference call.
- **Pattern C** has zero backend integration by design — anything that
  needs the LLM's output back inside Django's own data model cannot use
  Pattern C alone.
- Dependencies vary by pattern, not a single fixed set: `langflow==1.11.2`
  + `uvicorn` for A/B; `httpx` additionally for D; Celery + Redis
  additionally for D; the Langflow chat-widget CDN script additionally for
  C. A project adopting one pattern should not need to pull in the
  dependency footprint of the other three.
- Environment surface named for Pattern A: `LANGFLOW_FRONTEND_PATH`,
  `LANGFLOW_BACKEND_URL`, and a `LANGFLOW_DATABASE_URL` carrying the
  `?options=-c%20search_path=langflow_schema` suffix.

## Realization log

- **2026-08-13** — Captured as a seed from an operator-supplied architecture
  brief (background/method/architecture/dependencies for all four patterns).
  Not yet researched against this repo's own factory or any specific
  downstream project — no station claimed, no Spec derived, no pattern
  chosen. Owner deliberately left as `guild` (intake, not a terminal owner)
  pending a decision on which project or station this belongs to.
- **2026-08-14** — Owner reassigned `guild` → `steward` by operator decision (2026-08-14 dream-backlog audit): Charter §5 reserves `guild` for pyforge-charter and forbids it as a terminal owner; the whole Django/Langflow/DB-GPT family lands under one deployment-owning station. Status stays `dreamt` — the family's preconditions (monolith-vs-microservices decision, dependency-solve spike, a named subject project) are unchanged.
- **2026-08-14** — **Operator integration direction:** this dream's Pattern A (pluggable Django application: ASGI mount + schema isolation) is the PREFERRED shape — the host is a cookiecutter-django Django service with FastAPI integration based on [[django-accelerator-framework]]; infra is PostgreSQL + Redis + Kubernetes only; the same-day conda solve spike proved py3.12 co-install feasibility (py3.14 blocked solely by langflow-base's bcrypt==4.0.1 pin — everything must become 3.14-compatible). Other patterns remain fallbacks where pluggability fails.
- **2026-08-14** — **Subject project NAMED: [[python-agent-platform]]** (operator). The family's last precondition is met — the subject Dream and its family Spec (spec-python-agent-platform, pyforge-steward) consolidate all four same-day operator decisions plus the spike evidence; this dream's remaining role is the decision trail and its named pattern contracts.

## 2026-09-17 — A local OpenShift hybrid environment runs the agentic SDLC end to end — visual lifecycle, wired BMAD suite, multiplexed apps, synced tracker (folded from local-ocp-hybrid-environment)

# A local OpenShift hybrid environment runs the agentic SDLC end to end

## The Dream

The operator develops against a real, local Red Hat OpenShift cluster
(OpenShift Local under Podman Desktop) with the full agentic SDLC around it:
visual lifecycle management (Podman Desktop) bridged to infrastructure-as-code
(`oc` CLI); the complete BMAD suite wired and orchestrated; a
cookiecutter-django application co-hosted with Langflow (1.11.x) and DB-GPT
behind Traefik/ASGI multiplexing; PostgreSQL and Redis on PVCs with
schema-isolated tenants (`cookiecutter_schema`, `langflow_schema`,
`dbgpt_schema`, `github_metrics`); **Pixi** as the foundational package
manager throughout; **GitHub Projects V2** as the authoritative issue
tracker, synced locally via **dlt** into the cluster's PostgreSQL; and TEA
validating deployments. The full operator-authored technical specification
(six phases, architecture diagram, wiring plan) is filed verbatim at
`docs/intake/local-ocp-hybrid-environment/technical-spec.md` — it is this
Dream's source input and the spec pass's primary source.

## What the fleet already has (convergence map — read before scoping)

The spec's phases land on a fleet that has already built much of this; the
spec pass must reconcile "scaffold fresh" against "deploy what exists":

- **The application layer largely EXISTS as steward's platform**
  (`src/platform/`, Epics 10–13): a cookiecutter-django-derived host with
  Langflow AND DB-GPT integrated as pluggable apps (Pattern-A/B, AD-17),
  schema/PVC isolation decisions already made (AD-6 + the dated SQLite
  exception), Celery + Redis wiring, compose profiles, and — decisive for
  this Dream — **Story 12.1's vanilla Helm chart + thin OCP Route overlay,
  restricted-v2 hardcoded**, whose Tier-3 (live Route admission/SCC) was
  honestly left unverified because *no cluster existed*. This Dream's
  cluster IS the missing verification environment for 12.1 — and 12.2 (GKE
  profile) / 12.3 (air-gap parity) are its siblings in the same epic.
- **ASGI multiplexing has a prior Dream**: [[asgi-multiplexer-monolith]]
  — RESOLVED at spec time (2026-08-22): ABSORBED into python-agent-platform
  per its own 2026-08-14 Realization log; pointer spec authored; the
  intake's Traefik multiplexer is struck (the shipped in-process dispatcher
  + Route is the topology).
- **BMAD wiring is already chartered**: the spec's "BMAD Suite Wiring Plan"
  table is `spec-bmad-suite-channel-product` CAP-3's target state verbatim
  (steward Epic 15.3 wires TEA/BMB/CIS/utility-skills/manticore; WDS skip).
  This Dream CONSUMES that chain; it does not re-own it. One spec command,
  `bmad-marshal-detectors-init`, does not exist anywhere — flag for the
  spec pass (the nearest real machinery is marshal's detector registry +
  one-front-door's mc-* triage).
- **Tracker sync has a prior spec**: steward's `spec-jira-github-projects-sync`
  (planning-artifacts/specs). The dlt→`github_metrics` bridge is kin —
  reconcile at spec time.
- **Versions** *(corrected 2026-08-22 at spec time)*: the langflow suite
  MERGED and graduated to `conda-forge/langflow-feedstock`, now v1.11.4
  (8 outputs) — the platform pins `langflow >=1.11.4`, so the intake's
  1.11.2 was BEHIND the estate, not ahead; no bump decision exists. DB-GPT
  stays consume-not-submit (G58, external PR #33883).
- **Pixi-as-foundation and dlt** are native here: dlt ships in the pixi
  estate (`library-llms-full.md`), and the workspace conventions
  (environments, lock discipline, the 16-site pixi version registry) apply
  to the new workspace the spec scaffolds.

## What it looks like when real

- One documented bring-up takes a fresh workstation to: cluster Running in
  Podman Desktop, `oc` authenticated, BMAD suite fully wired (via the
  channel-product chain), the platform deployed from the 12.1 chart with
  Routes admitted under restricted-v2 (12.1's Tier-3 finally verified
  live), PVC-backed Postgres/Redis with the four isolated schemas, and
  Langflow + DB-GPT served behind the multiplexed ingress.
- GitHub Projects V2 is the tracker of record, and its items/fields/status
  land in `github_metrics` via a dlt pipeline run from the Pixi workspace —
  no third-party SaaS middleware.
- TEA validates the deployment as part of the flow (its wiring arrives via
  Epic 15.3; `tea-test-review` gates exist today).
- The whole thing is IaC-reproducible: manifests/values tracked, secrets
  never committed (the `.dlt/secrets.toml` and pull-secret handling follow
  steward's key discipline).

## What is real

The intake spec (verbatim, filed); steward's platform + chart (Epics 10–12.1
shipped); the channel-product chain (Epic 15, backlog) that will wire the
suite; dlt installed; the prior asgi-multiplexer and jira-github-projects
Dreams/specs; no cluster, no Podman Desktop integration, no dlt pipeline, no
GitHub Projects V2 board, nothing deployed to OCP.

## Constraints

- Reuse-first: the spec pass must justify any fresh scaffold over deploying
  `src/platform/` + the 12.1 chart (the spec's cookiecutter-django scaffold
  and the platform are the same lineage — divergence is debt).
- Secrets (GitHub PAT, pull secret, DB credentials) follow steward's key
  discipline — never committed, never host-unscoped; the spec's inline
  `debug_password` is a local-dev placeholder, not a pattern.
- BMAD wiring flows through `provision --module` (Epic 15.3), never ad-hoc
  installer runs that leave no manifest record.
- The multiplexer decision (in-process ASGI vs Traefik-routed pods) is made
  once, reconciling [[asgi-multiplexer-monolith]] — not implemented both
  ways.

## Non-goals

- Owning suite wiring or channel currency ([[bmad-suite-channel-product]]).
- The core upgrade ([[bmad-method-core-upgrade]]) and era alignment
  ([[bmad-611-era-alignment]]).
- Production/cloud OCP — this is OpenShift LOCAL; GKE/air-gap stay stories
  12.2/12.3 in the platform epic.
- Replacing the fleet's sprint-ledger machinery with GitHub Projects V2 —
  the board tracks THIS effort's work; any deeper tracker integration is
  `spec-jira-github-projects-sync`'s question.

## Kinships

steward Epics 10–13 (`spec-python-agent-platform` — the app layer + 12.1
chart this deploys and finally live-verifies) · [[asgi-multiplexer-monolith]]
(absorb-vs-kin at spec time) · [[bmad-suite-channel-product]] (CAP-3 wiring
consumed) · `spec-jira-github-projects-sync` (tracker kin) ·
`docs/specs/langflow-conda-forge.md` (1.10.1 suite; the 1.11.x bump
question) · DB-GPT G58 consume-not-submit lineage.

## Realization log

- **2026-08-22** — Seeded (`24c4dce923`) and specified the same day: `spec-local-ocp-hybrid-environment`
  under pyforge-steward (5 CAPs, 2 companions, status `ready`), decomposed as the steward Epic 12
  extension S-12.4..12.8, operator-locked (`6bcedf41ab`).
- **2026-09-09 (fleet readiness pass)** — Log resumed; it had stopped at 2026-08-22 while the epic finished (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB). All five CAPs are closed as Stories 12.4–12.8, all `done`: 12.4 bring-up + registry posture, 12.5 the DB-GPT sidecar in the chart, 12.6 Redis hardened, 12.7 Tier-3 **attended** verification on a real CRC cluster (`https://platform.apps-crc.testing/ht/` → 200, record `spec-12-1-…-verification-2026-08-25.md`), 12.8 the dlt Projects-V2 bridge (`src/platform/ingest/github_projects/`, pixi task `github-metrics-dlt` at `pixi.toml:166`). CAP-4's criterion was exercised on a real cluster, not merely merged. **Status unchanged in this pass** (the batch approved the log entry, not a flip); the evidence for `realized` is on the record here if the operator wants it.

## 2026-09-17 — Isolate MCP eras without one lockfile (folded from mcp-era-isolation)

# Isolate MCP eras without one lockfile

## The Dream

Station MCP faces speak official MCP 2.x (dual-era Streamable HTTP) on the live
host **without** forcing Langflow and FastMCP 3 to share that interpreter. A
modern Cursor/Codex client can still talk to factory FastMCP 3 stdio tools
through a **later** translator — not by rewriting JSON inside gunicorn.

Three problems stay named, never merged:

1. **Pin** — `python-agent-platform` cannot import `mcp.server.mcpserver`
   (mcp 2.x) while Langflow + conda FastMCP 3 declare `mcp>=1.24,<2`.
2. **Dual-era wire** — already coded in `django_pyforge.mcp_http` (revisions
   `2025-03-26`–`2026-07-28`). It lights up when (1) is isolated.
3. **Factory stdio** — modern clients vs FastMCP 3 / mcp 1.x local tools.
   That is a downgrade/upgrade proxy, not the CRC ImportError.

## What it looks like when real

- CRC `/ht/` stays 200. Langflow still imports in the **web** image.
- `POST /stations/atlas/mcp` initialize with `2025-06-18` echoes that revision.
- `MCP-Protocol-Version: 2026-07-28` is accepted on the same POST path.
- Unsupported revision → JSON-RPC `-32022` with `data.supported`.
- GET `/stations/<name>/mcp` → 405, `Allow: POST`.
- `[feature.python-agent-platform]` is **not** lifted to mcp 2.x.
- Sidecar env solve has **no** FastMCP 3.

## What is real

Story 21.2 / 21.4 mounted official-SDK faces; CRC 12.7 skipped them on
`ImportError` so gunicorn could boot. `spec-platform-image-one-pixi-env`
explicitly did not invent mcp 2.0 + Langflow in one lock. FastMCP 4 is beta
and not on conda-forge. SEP-2663 Tasks is not in mcp 2.0.0.

## Sequence

1. **Slice 1 (this Dream's build)** — Pattern B sidecar (`mcp-host`): mcp 2.x,
   no Langflow, no FastMCP 3. Host `dispatch_station_mcp` proxies
   `POST /stations/<name>/mcp` to that process. Identity and path pattern stay
   on the host.
2. **Slice 2 (later)** — factory stdio translator (BMAD-SPEC-2026-MCP as
   input). Own spec. Does not claim to fix CRC.
3. **Slice 3 (later)** — retire the ImportError skip when FastMCP 4 is on
   conda-forge **or** Langflow drops `mcp<2`. Until then the skip is a safety
   net only when the sidecar URL is **unset**. CAP-4 does not retire it.
4. **CAP-4 (cluster required, 2026-08-26)** — Helm + production check fail-loud
   if mcp-host / `MCP_HOST_SIDECAR_BASE_URL` is omitted **on the cluster**.
   Steward Epic 35 / `spec-35-1-cluster-requires-mcp-host.md`. Not Epic 34.

Invert (sidecar Langflow, lift mcp 2.x on the web image) only if the hop
fails CAP-1 identity or latency.

## Constraints

- Do not remint unifying-strategy architecture. `lane1-serves-dw-h3` stays no.
- Do not fold `mcp-types` / `httpx2` into `python-agent-platform`.
- Do not lift FastMCP 4 from PyPI. Do not wait on Tasks.
- Do not implement the pasted translator in-process (cannot load both SDKs).
- Write planning under `_bmad-output/projects/pyforge-steward/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-steward`. No `bmad-switch` from parallel agents.

## Non-goals

- 12-7 Route/SCC re-prove.
- Libro.
- One lockfile for mcp 2.0 and Langflow.
- Q5 scorecard.

## Realization log

- **2026-08-26** — Dream captured from the MCP era program plan. Spec:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/`.
- **2026-08-26** — Slice 1 landed: pixi env `mcp-host`, sidecar Containerfile,
  host proxy via `MCP_HOST_SIDECAR_BASE_URL`, CRC proofs in spec memlog.
  Slice 2 implementation started 2026-08-26 (`scripts/mcp_factory_stdio_translator.py`).
  Slice 3 criteria in `retire-skip.md` (ImportError skip kept).
- **2026-08-26** — CAP-4 planned: cluster overlay cannot omit mcp-host
  (`cluster-required.md`). Epic 35.1 ready-for-dev. Dispatch after 34.1.

## 2026-09-17 — The sidecar that only says its own name (folded from mcp-host-real-station-tools)

# The sidecar that only says its own name

## The Dream

An agent that reaches a deployed platform's `/stations/<name>/mcp` should get that
station's real tools — the ones the same code exposes in-process on a laptop or in
`platform-ci-local`. Today it gets one tool, for every station, no matter which
station's URL it called: `station_face()`, which returns the station's own name
string and nothing else. The mcp-host sidecar that `spec-mcp-era-isolation` shipped
to work around the web image's `mcp 1.x` pin is real infrastructure — a second
process, a second image, a live proxy hop — built to eventually carry real traffic.
It has never carried any.

> A bridge that only echoes the name of the far bank has not yet been walked across.

## Why now — found chasing a different proof

The 2026-09-12 CAP-3 attended CRC exercise set out to drive one real bmad-loop-style
run through a deployed platform and watch it appear on `/runs/`. Every layer beneath
that goal turned out sound once four small, genuine bugs were fixed (Containerfile
missing a `COPY`, two independent DNS-egress NetworkPolicy defects, a JWKS scheme
check, and — found in this same pass — an unwired assertion-signing keypair). A real
Authorization Code + PKCE login worked. A real IdP bearer verified. A real host
assertion minted. Then the actual publish call — `POST /stations/marshal/mcp`,
`publish_loop_run` — came back `Unknown tool: publish_loop_run`, from the real `mcp`
library's own tool manager, meaning a real `MCPServer` answered the call and simply
never had that tool registered.

Tracing it down: `platform.djangoEnv` (the chart's shared env helper, used by every
platform-image pod unconditionally) always sets `MCP_HOST_SIDECAR_BASE_URL`, and
`dispatch_station_mcp` in `django_pyforge/mcp_http.py` proxies **every** station's
MCP call to that URL whenever it is set — no per-station carve-out. The sidecar
(`src/platform/mcp_host/app.py`) builds its per-station apps with
`asgi_for_station(name)`, from `django_pyforge/mcp_dual_era.py` — a function whose
entire body is a `server.tool()` decorator around a closure that returns `name`. It
was written to prove the **dual-era handshake wire** works across the mcp 1.x/2.x
pin boundary (`spec-mcp-era-isolation` CAP-1..3, shipped and still true today —
re-verified live this same exercise), not to carry any station's real tool surface.

Checked directly against the web pod's own interpreter: `from mcp.server.mcpserver
import MCPServer` still raises `ModuleNotFoundError` there (the pin `mcp-era-isolation`
exists to work around is still live), so there is no way to reach `django_marshal_portal`,
`django_herald_portal`, or any other station's real MCP tools **in-process** either.
The sidecar is the only place any of them could run. None of them do.

`spec-mcp-era-isolation`'s own three-slice sequence (`docs/dreams/mcp-era-isolation.md`)
never names this as future work: slice 2 is a stdio wire-format translator for a
different problem (modern MCP clients vs FastMCP 3 stdio, unrelated to this HTTP
dispatch path — confirmed by reading `spec-mcp-factory-stdio-translator`), and slice 3
is retiring the in-process `ImportError` skip once FastMCP 4 or an unpinned Langflow
ships upstream. Nothing currently specced closes the gap between "the sidecar exists
and proxies correctly" and "the sidecar actually hosts a station's tools."

## What it looks like when real

- `POST /stations/marshal/mcp` with `publish_loop_run` reaches the SAME
  `publish_held_loop_bounded` code path a laptop or `platform-ci-local` run reaches
  — through the sidecar, not despite it.
- Every station wired with a real in-process MCP app today (`django_marshal_portal`,
  and whichever siblings define one) is reachable the same way once the sidecar is
  the only process that can load `mcp.server.mcpserver`.
- The generic `station_face()` stub stops being the answer for a station that has a
  real implementation; it may remain the fallback for one that does not.
- CAP-3's own live-run proof — a real bmad-loop run appearing on `/runs/`, its timing
  queryable after the workstation that ran it is gone — becomes achievable on a real
  deployed cluster, closing the one item its own verification record
  (`spec-run-state-one-publisher/verification-2026-09-12.md`) left "NOT PROVEN."

## Constraints / Non-goals

- **Not a rewrite of slice 1.** The dual-era handshake, the proxy dispatch, the
  `MCP_HOST_SIDECAR_BASE_URL` wiring, the CAP-4 cluster-required fail-loud — all stay
  exactly as shipped. This Dream is additive: what the sidecar hosts, not how it is
  reached.
- **Not the stdio translator.** `spec-mcp-factory-stdio-translator` (slice 2) solves a
  different, already-specced problem (modern-client wire format against FastMCP 3
  stdio tools). This Dream does not touch it.
- **Not retiring the ImportError skip.** Slice 3 stays gated on an upstream FastMCP
  4 / Langflow pin change, tracked in `retire-skip.md`. This Dream does not change
  when that skip goes away.
- **Django-in-the-sidecar is a real design question, not a given.** The real
  per-station apps (e.g. `django_marshal_portal.mcp_asgi`) call into
  `django_pyforge.supervisor`, which needs Django's ORM. The sidecar image
  deliberately runs no Django today ("No Langflow. No FastMCP. Imports
  `django_pyforge.mcp_dual_era` only."). Whether the derived Spec adds a minimal
  Django settings module + ORM connectivity to the sidecar, or finds another shape
  entirely, is an open question for that Spec to answer — not pre-decided here.
- **Cross-station by construction.** A station's own portal package
  (`django_<name>_portal`) stays that station's surface; this Dream's Spec only
  owns how the sidecar discovers and mounts what already exists.

## Kinships

[[mcp-era-isolation]] (the ancestor — slice 1 shipped the proxy and the handshake;
this Dream is the un-specced gap between "proxies correctly" and "hosts anything
real") · [[run-state-one-publisher]] (CAP-3's own live-run criterion is blocked on
this, discovered running its attended CRC exercise 2026-09-12) · [[pyforge-unifying-strategy]]
(CAP-17 — the criterion this ultimately unblocks) · [[pyforge-steward]] (the station;
`mcp_http.py`, `mcp_dual_era.py`, `mcp_host/app.py`, the chart's sidecar wiring are
all its surface) · [[pyforge-marshal]] (the first station whose real tools this
would actually carry, and the one that found the gap).

## Realization log

- **2026-09-12** — Seeded (operator ruling: gap-closure enters through the Dream-to-Code
  chain like any other effort). Found running the CAP-3 attended CRC exercise
  (`spec-run-state-one-publisher/verification-2026-09-12.md`) while chasing why a
  real, correctly-signed host assertion still could not publish a run: the mint
  path worked end-to-end once its own bug (unwired signing keypair, landed
  separately) was fixed, but the publish call hit the mcp-host sidecar's
  identity-only stub instead of marshal's real held-loop tools. Confirmed by
  reading `mcp_host/app.py`, `mcp_dual_era.py::asgi_for_station`, and
  `django_pyforge/mcp_http.py::dispatch_station_mcp`, and by re-checking live on
  the CRC cluster that the web pod's own interpreter still cannot import
  `mcp.server.mcpserver` — the sidecar remains the only place a real per-station
  MCP app could run, and none run there today. Cross-checked against
  `spec-mcp-era-isolation`'s own three-slice sequence and `spec-mcp-factory-stdio-translator`:
  neither names this gap. Next act: `bmad-spec` derives the Spec under `pyforge-steward`.
- **2026-09-12** — Realized, same day as seeding. Rather than leaving the two open
  questions for a future pass, they were resolved by implementing CAP-1..3 directly and
  proving them live: a minimal Django settings module (`django_pyforge` +
  `django_marshal_portal` only, no Langflow, no Redis client — the sidecar's calls never
  touch cache or the event broker) answered the ORM-access question; marshal's own lean
  `PortalConfig.ready()` (no `pyforge.marshal` import, unlike mason's eager
  `pyforge.mason.boot`) answered the scope question. `mcp_host/app.py` now discovers real
  per-station apps through the same `iter_station_mcp_apps()` seam the web pod uses
  in-process, falling back to the identity stub for every other station. A second,
  previously-unreachable bug surfaced the moment the tool became callable at all: the
  real MCP SDK turns a `**payload: Any` parameter into a REQUIRED, separately-named
  `payload` field, not "any extra keys allowed" — `HostPublisher`'s client call sent flat
  kwargs and failed schema validation; fixed on both the server (`django_marshal_portal`)
  and client (`publisher_host.py`) sides. Landed PR #1285. A real `HostPublisher` process,
  run from a workstation against the deployed CRC cluster, published a run, heartbeat'd it,
  completed it, exited — and a separate `curl` call to `/runs/` afterward showed the run
  under "Completed timing" with its real duration. CAP-17's own `verified:` line updated
  on `spec-pyforge-unifying-strategy` in the same pass.

## 2026-09-17 — One workspace opens every repo a story touches (folded from multi-repo-workspaces)

# One workspace opens every repo a story touches

## The Dream

Fleet work routinely spans local-recipes + conda-forge-tracker + feedstock
clones, but workspace tooling is single-repo: steward Epic 13
(spec-scratch-worktree-lifecycle, stories 13.1/13.2 backlog) manages
worktrees of THIS repo only. The dream: `steward workspace start <feature>`
cuts one worktree per registered repo on a shared feature branch, generates
a `.code-workspace`, answers dirty/unpushed status across the set in one
command, and refuses destructive removal while any member is dirty — the
repo set modeled declaratively (the org's `pyforge.toml [projects.<slug>]`
shape).

## Grounding

Imported from the sibling PyForge instantiation's ONLY substantive
capability gap vs this fleet: OpenTeams mgmt-wf's
`developer-workspace-management` dream (2026-08-22 analysis; unlicensed —
pattern adopted, prose not copied). Local kinship is live: Epic 13 is
backlog, so the spec pass DECIDES extend-Epic-13 vs new chain rather than
building two worktree systems.

## Constraints / Non-goals

Single-repo verbs stay 13.1/13.2's contract; this layers coordination above
them. Not a monorepo migration; not bmad-switch scope (kin:
`bmad-switch-scope-enforcement`).

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-multi-repo-workspaces` derived under pyforge-steward and decomposed into the station backlog
  the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09 (fleet readiness pass)** — Log resumed; it had stopped at 2026-08-22 while the epic finished (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C7**). CAP-1/CAP-2 are built and `done` (Stories 13.3, 13.4): `start_repo_set` / `status_repo_set` / `clean_repo_set` and `.code-workspace` generation at `workspace.py:277`, `:394`, `:413`, `:239`, registry path `.steward/repo-sets.yaml` at `:38`. **Never adopted** — no `.steward/repo-sets.yaml` exists; `git ls-files .steward/` returns only `keys-inventory.yaml` and the two `.example.yaml` files. **Decision: park with a named trigger — "when a second repo joins the estate", i.e. `python-foundry`, Story 44.3.** Adopting now would mean writing a repo-set naming a repo that does not exist. Status held at `specified`.

## 2026-09-17 — OpenShift runs as a CI portability profile — the OCP overlay proven on a real cluster (folded from ocp-as-a-portability-profile)

# OpenShift runs as a CI portability profile — the OCP overlay proven on a real cluster

## The Dream

The platform's **first deployment target is Red Hat OpenShift** — not merely
as a chart template, but as something Platform CI can prove automatically.
Story 12.1 shipped a vanilla Kubernetes core chart and a thin OCP Route overlay;
Story 12.2 proved the vanilla Ingress path on a GKE-shaped `kind` profile;
Story 12.3 proved air-gap parity. The OCP half of AD-11's portability clause
remains honestly open: `deploy/README.md` still names "No OCP live-cluster
verification in this repo."

This Dream closes that gap the same way 12.2 closed the GKE gap: an optional
Platform CI job spins up a **real OpenShift API** (OpenShift Local / CRC — not
`kind`, which cannot admit Routes or enforce `restricted-v2` SCC), pushes the
shared platform image through the internal-registry pattern, installs the core
chart with `overlays/ocp/core-overrides.yaml` plus the Route overlay, and
curls the app through the cluster router — never a `port-forward` or a direct
Service curl. OCP is a **profile**, not a second implementation: the overlay
Story 12.1 already owns stays the only OCP-specific surface.

## What it looks like when real

- `ocp-portability-smoke` exists in `.github/workflows/platform-ci.yml`, default
  **off** on PRs (same opt-in pattern as `gke-portability-smoke` and
  `air-gap-parity`): repo variable `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true` or
  a `workflow_dispatch` toggle.
- The job reuses `build-platform-image`'s artifact (P1 fan-in), installs helm/kubectl
  from `platform-dev` (AD-16), and treats CRC/OpenShift Local as a named
  system-level exception alongside `kind`.
- Smoke assertions prove: Route admission, edge-terminated HTTPS to `/ht/` and
  `/admin/login/`, migrate hook completion, and that postgres/redis pods run
  without fixed `runAsUser` under SCC-assigned UIDs.
- A dated verification note in the 12.1 orbit records whatever contingency the
  run needed (official postgres/redis images vs. RH/bitnami fallbacks) — kin to
  Story 12.7's attended checklist, but automated and repeatable.

## What is real

- Story 12.1 overlay (`src/platform/deploy/overlays/ocp/`) and invariant tests
  (`test_chart_invariants.py`) — template/lint only, no live cluster.
- Story 12.2 `gke-portability-smoke` — the sibling CI pattern to mirror
  (optional job, shared image artifact, no `--wait` helm install, migrate wait
  before ORM assertion).
- Story 12.3 `air-gap-parity` — orthogonal; does not substitute for OCP Route/SCC proof.
- `spec-local-ocp-hybrid-environment` + Story 12.4 bring-up facts — the internal-registry
  push commands and CRC 2.63.0 / OpenShift 4.22.7 baseline this job copies;
  the full hybrid SDLC (BMAD wiring, dlt, DB-GPT sidecar) stays out of scope.
- No automated OCP job in Platform CI today.

## Constraints

- AD-11: core chart unchanged; OCP specifics only via the existing overlay
  (`core-overrides.yaml` + `platform-ocp` Route chart) — never OCP kinds in the core.
- AD-16: helm/kubectl from pixi; CRC/`oc` as explicit named system exceptions.
- AD-15: paths-filtered Platform CI; non-`recipes/` PRs carry the `maintenance` label.
- Default off on PR push — CRC is slow (~30–90 min job budget), disk-heavy (~35 GiB
  bundle), and needs a Red Hat pull secret (`CRC_PULL_SECRET`).
- **Runner honesty:** OpenShift Local's documented OS support excludes Ubuntu/Debian
  for the Podman Desktop path; GitHub-hosted `ubuntu-latest` may or may not run CRC
  via `crc-org/crc-github-action`. The spec's first implementation must prove the
  chosen runner class or fall back to a labeled self-hosted RHEL/Fedora runner —
  never claim OCP verification on a cluster that never started.

## Non-goals

- Replacing Story 12.7's full attended Tier-3 record (PVC edge cases, sidecar
  inventory after 12.5, Redis hardening after 12.6) — this job proves the
  portability profile, not every hybrid-environment CAP.
- Production/cluster-specific networking, external DNS, or corporate mirror posture.
- Duplicating `container`'s docker+podman matrix — one engine (Docker) for CRC, same
  rationale as 12.2.
- Nightly-only scheduling is acceptable as a follow-up if PR-default remains off;
  making every PR pay CRC cost is explicitly rejected.

## Kinships

- [[python-agent-platform]] — AD-11 (OCP-first, GKE as CI profile); CAP-6 portability.
- `spec-12-2-gke-as-a-portability-profile` — structural sibling; copy job shape,
  diverge at cluster + overlay + assertion path.
- [[local-ocp-hybrid-environment]] — consumes CAP-1 registry/bring-up facts (Story 12.4);
  does not re-own the full hybrid SDLC.
- Story 12.7 — overlapping Tier-3 items; 12.9 automates the subset CI can own;
  12.7 remains the attended closeout after chart extensions 12.5–12.6 land.

## Realization log

- **2026-08-23** — Dreamt and prematurely marked `specified` against
  `spec-12-9-ocp-as-a-portability-profile` (a story-spec name). That folder
  never existed; INV-1 matches the Dream slug, so the chain was still
  `dream-without-spec`.
- **2026-08-24** — Chain Spec `spec-ocp-as-a-portability-profile` landed
  `ready` (CAP-1..3). Bound to existing Story 12.9; ledger flipped
  done→backlog because Platform CI still has no `ocp-portability-smoke`
  job. Runner class remains an open question at story time.
- **2026-09-09 (fleet readiness pass)** — Log resumed; the last entry asserted a job that now exists (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C14**). Story 12.9 landed: `ocp-portability-smoke` at `.github/workflows/platform-ci.yml:1243`, `runs-on: ubuntu-latest`, 90-minute budget, CRC internal-registry push, double-gated on `PLATFORM_CI_OCP_PORTABILITY_SMOKE` / `workflow_dispatch` plus a fail-fast `CRC_PULL_SECRET` check at `:1265-1272` — so the earlier "Platform CI still has no `ocp-portability-smoke` job" line is **superseded**, and the runner-class open question is answered *by construction* (`ubuntu-latest` + the CRC action). CAP-1 met. **CAP-2 and CAP-3 are not:** `gh variable list` returns only `ACTIONS_ENABLED=false`, `gh secret list` has no `CRC_PULL_SECRET`, and `spec-12-9-…md:54` records "first green ocp-portability-smoke deferred to operator". **Operator decision this pass (batch C14): fund one green run — set `CRC_PULL_SECRET` + `PLATFORM_CI_OCP_PORTABILITY_SMOKE` and dispatch once, before Story 44.10 disables this repo's CI.** Status stays `specified` until that run exists — this Dream's own Constraint says never claim OCP verification on a cluster that never started. It is also the gate on any Intelligence-Hub NIC-profile story.

## 2026-09-17 — Postgres and Redis become consumed, not self-hosted, matching the IdP and object-storage pattern (folded from platform-datastores-consumed-not-self-hosted)

# Postgres and Redis become consumed, not self-hosted, matching the IdP and object-storage pattern

## The Dream

`spec-pyforge-unifying-strategy`'s AD-1 names the platform's infrastructure as
"exactly PostgreSQL + Redis + Kubernetes," and until 2026-09-10 treated any
fourth backing service as a failed design review. The object-storage
exception (`docs/dreams/platform-object-storage-kind.md`,
`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`)
authorized a narrower, specific move for a *new* kind of service: **consumed,
never self-hosted** — pyforge holds an endpoint URL and credentials only; the
operations team runs the real thing (NetApp StorageGRID). That mirrors a
pattern already trusted once before, for the identity provider
(`canopy:AD-19`: *"pod specs carry secret references only; no Vault HTTP
from the platform image. Cluster ESO/Vault stays outside the image."*).

**The question this Dream asks, seeded from a live conversation
(2026-09-11):** if "consumed, not self-hosted" is the right shape for the
IdP and now object storage, why do Postgres and Redis — the other two of
AD-1's three *always* infrastructure kinds — not get the same treatment?

**Confirmed evidence, this session, each independently verified by direct
file reads:**

1. **Postgres and Redis are self-hosted by pyforge's own Helm chart today,
   in every deployment profile that exists, including the "enterprise" one.**
   `src/platform/deploy/charts/platform/templates/` ships
   `postgres-statefulset.yaml`, `postgres-backup-cronjob.yaml`,
   `postgres-backup-pvc.yaml`, `postgres-service.yaml`,
   `redis-deployment.yaml`, `redis-service.yaml`, `redis-broker-pvc.yaml` —
   pyforge's own chart deploys, patches, backs up, and is operationally
   responsible for both. Compare `pap:CAP-6`'s own admission language:
   *"third-party images (`postgres:17`, `redis:7`) under the internal-registry
   rule"* — the *image* is upstream, but pyforge is still the *operator*.
2. **The one existing "enterprise" overlay (OCP) does not change this.**
   `src/platform/deploy/overlays/ocp/core-overrides.yaml` (Story 12.1) only
   nulls `runAsUser`/`fsGroup` so the *same* self-hosted `postgres`/`redis`
   StatefulSet/Deployment pass OpenShift's `restricted-v2` admission policy.
   It does not switch to an externally-provided Enterprise Postgres/Redis.
   Kubernetes-as-substrate is enterprise-provided (OCP); the two stateful
   services running on top of it are not.
3. **The application already consumes both exactly the way it would consume
   an external service.** `src/platform/config/settings/base.py` reads
   `DATABASE_URL` and `REDIS_URL`/`REDIS_BROKER_URL`/`REDIS_CACHE_URL` via
   `env()` (django-environ) — an endpoint-and-credential seam, identical in
   shape to `canopy:AD-19`'s IdP pattern and the new object-storage S3
   client seam (`src/platform/config/object_storage.py`). Nothing at the
   application layer distinguishes "pyforge's own StatefulSet" from "an
   Enterprise-managed instance" — both are just a URL.

**Confirmed, operator-stated (2026-09-11): the real deployment target is all
four, Enterprise-managed.** *"When I deploy pyforge, I will have an
Enterprise Managed OCP Cluster, an Enterprise Managed PostgreSQL DB, an
Enterprise Managed Redis Instance, and an Enterprise Managed NetApp [object
storage] solution."* This is not a hypothetical symmetry argument — it is
the actual deployment shape. OCP (OpenShift Container Platform, Red Hat's
enterprise Kubernetes distribution) is self-managed by the enterprise's own
platform/ops org on infrastructure they control — on-prem, virtualized, or
cloud — not a third-party SaaS vendor; the operative distinction for this
Dream isn't "external company" but "a different org than pyforge's own
application/deployment team owns and operates it." All four backing pieces
(OCP, PostgreSQL, Redis, object storage) are provided and operated that way
in the real target environment; pyforge's job is to consume all four via
configuration, not to stand up any of them itself. (The object-storage
target is NetApp StorageGRID — internally also referred to as "HPOS" by the
operator; same target, informal name, no correction owed to the
already-merged Dream/Spec text that names it StorageGRID.)

**Refined, operator-stated (2026-09-11): the deployment topology, precisely.**
All four — Enterprise Managed PostgreSQL, Enterprise Managed Redis, the
Enterprise Managed OCP cluster, and Enterprise Managed StorageGRID — are
co-located at the same data center. Pyforge itself ships as a container
image (podman/docker) deployed into a **namespace within** that
enterprise-managed OCP cluster — pyforge is a tenant workload inside a
cluster it neither owns nor operates, not a cluster pyforge stands up
itself. From that namespace it reaches Postgres, Redis, and StorageGRID as
co-located network peers, the same shape `canopy:AD-19` already assumes for
the IdP (a namespace-scoped workload holding endpoint + credentials, never
cluster-admin-level access to anything it doesn't own).

**What this Dream asks for:** move Postgres and Redis to the same
*consumed, not self-hosted* model already proven for the IdP and object
storage — an Enterprise-managed PostgreSQL and Redis the operations team
runs, pyforge holding only connection config, the same way
`DATABASE_URL`/`REDIS_URL` already work today, minus the bundled
StatefulSet/Deployment as the *only* supported path.

## Non-goals

- **Not removing local-dev self-hosting.** Local development keeps a
  self-hosted Postgres/Redis path (matching how Silo/Garage stay locally
  self-hostable even though production consumes StorageGRID externally) —
  this Dream is about the *deployed platform's* operational model, not
  local dev ergonomics, exactly like the object-storage exception was scoped.
- **Not a unilateral removal of the bundled chart templates.** If this
  Dream is realized, the shape is additive/pluggable first (a BYO-endpoint
  overlay alongside the existing self-hosted default, mirroring the
  default-plus-alternative pattern already used for scribe's nightly-trigger
  backend and Silo/Garage) — not a breaking cutover that strands anyone
  currently relying on the bundled StatefulSet/Deployment.
- **Not reopening Kubernetes's own treatment.** Kubernetes is the substrate
  the chart deploys onto, not a backing service pyforge's chart stands up —
  a different kind of thing than Postgres/Redis/object storage, out of
  scope here.
- **Not resolving AD-1's own wording.** Whether this requires a dated
  exception (mirroring the object-storage precedent) or a rewrite of AD-1's
  "always" list itself (since Postgres/Redis are named directly, unlike
  object storage which was a genuinely new kind) is a real open question
  for whatever Spec follows this Dream, not decided here.
- **Not touching backup/DR responsibility without naming the handoff.** The
  chart's own `postgres-backup-cronjob.yaml` exists today; moving to a
  consumed model shifts backup/PITR responsibility to the ops-provided
  Enterprise instance entirely. That handoff needs to be explicit in
  whatever Spec follows, not silently assumed.

## Realization log

- **2026-09-11 (seeded from a live conversation)** — The operator, reviewing
  the object-storage exception, asked why Postgres and Redis don't get the
  same "consumed, not self-hosted" treatment already given to the IdP and
  object storage. Verified live: pyforge's own chart self-hosts both today,
  including under the one existing "enterprise" (OCP) overlay, which only
  adjusts security context rather than switching to external instances; the
  application's own `DATABASE_URL`/`REDIS_URL` consumption is already
  endpoint-and-credential shaped, identical to the IdP/object-storage
  pattern. Dream seeded rather than treated as a settled conclusion — the
  concrete "is there a real Enterprise Postgres/Redis target" confirmation
  the object-storage precedent had was still missing at this point.
- **2026-09-11 (same day, operator confirmation)** — The operator confirmed
  this is not hypothetical: the real deployment target is an Enterprise
  Managed OCP cluster, Enterprise Managed PostgreSQL, Enterprise Managed
  Redis, and Enterprise Managed NetApp object storage, all four ops-provided
  and externally operated. This resolves the Dream's own first open
  question (a confirmed real target, matching the bar the object-storage
  precedent already met) — the "not yet confirmed" caveat is retired.
  Separately clarified: "NetApp HPOS" is the operator's informal name for
  the same StorageGRID target already named in the merged object-storage
  Dream/Spec — no correction owed there.
- **2026-09-11 (processed via `bmad-correct-course`)** —
  `sprint-change-proposal-2026-09-11-ad-1-datastores-exception.md`. AD-1
  gained a second dated exception (PostgreSQL + Redis, consumed not
  self-hosted, mirroring the object-storage precedent); decomposed into
  steward Epic 51 (Stories 51.1-51.3): a BYO-external-PostgreSQL overlay, a
  BYO-external-Redis overlay, and the backup/PITR responsibility handoff.
  Existing self-hosted default preserved as a Non-goal, not removed. Status:
  dreamt → specified.
- **2026-09-11 (topology refinement, pre-approval)** — The operator refined
  the deployment topology while reviewing the proposal for approval: all
  four Enterprise-managed pieces (PostgreSQL, Redis, OCP, StorageGRID) are
  co-located at the same data center; pyforge itself ships as a
  podman/docker container into a namespace within the enterprise-managed
  OCP cluster — a tenant workload, not the cluster's owner/operator.
  Non-structural (no capability or story changes) — folded into the Dream's
  own topology paragraph and the Spec's Why section for accuracy.
- **2026-09-11 (later, same session)** — Epic 51 drained 3/3. Story 51.1: the
  `external-postgres` Helm overlay + chart guards + invariant tests, default
  render proven byte-identical (`local-recipes#1259`). Story 51.2: the
  `external-redis` overlay, same pattern (`local-recipes#1260`). Story 51.3:
  the backup CronJob guarded on Story 51.1's toggle, enterprise database team
  named as backup/PITR owner in `deploy/README.md` (`local-recipes#1261`).
  All four capabilities in `spec-platform-datastores-consumed-not-self-hosted/
  SPEC.md` carry `verified:` lines; the Spec and this Dream both close as
  `shipped`/`realized`. Status: `specified` → `realized`.

## 2026-09-17 — platform-dev boots the local canopy without a second env (folded from platform-dev-boots-local)

# platform-dev boots the local canopy without a second env

## The Dream

`pixi install -e platform-dev` is the no-Docker, no-CRC local baseline
(pap:AD-16). An operator should mint a persona and run `manage.py` from
**that** env. Today `config.settings.local` always loads
`debug_toolbar`, and that package lives only on `platform-ci-test`.
`platform-dev` dies on import. The workaround is a second env. The
Dream is one env: servers and the local Django leaf resolve together.

> A baseline that cannot load its own settings is not a baseline.

## Why now

Found 2026-09-13 while launching the canopy without Docker or CRC.
`platform-dev` python has Django, Wagtail, gunicorn, `django_extensions`,
and PyJWT. It does not have `django-debug-toolbar`.
`COMPONENT_RUNTIME=local python -m config.local_dev.mint staff` and
`manage.py runserver` both fail. The image feature
(`python-agent-platform`) must stay clean of the toolbar.

## What it looks like when real

- `platform-dev` python imports `config.settings.local`.
- `manage.py check` and mint run from that env against pixi Postgres.
- A policy test refuses a `platform-dev` solve that omits the toolbar
  or an image feature that gains it.
- CRC and Docker are unused for this proof.

## Constraints / Non-goals

- Pin `django-debug-toolbar` on `[feature.platform-dev]` only.
- Do not add it to `python-agent-platform` (the image).
- Do not start a `:800x` services farm; do not require compose or CRC.
- Do not flip Epic 44 `blocked` keys.

## Kinships

[[python-agent-platform]] (pap:AD-16, Story 11.1 — the env this Dream
repairs) · [[pyforge-steward]] (the host and the local leaf).

## Realization log

- **2026-09-13** — Seeded after a live `ModuleNotFoundError: debug_toolbar`
  on `platform-dev`. Operator asked the gap to be minted and implemented
  as a steward story, not a silent pin.
- **2026-09-13** — Spec `ready` (`pdl:CAP-1`), Epic 56 / Story 56.1. Live:
  `platform-dev` imports `debug_toolbar` 8.0.0, `django.setup()` under
  `config.settings.local`, `manage.py check`, and mint `staff`. Policy
  suite 6 passed. Image feature still omits the toolbar.

## 2026-09-17 — The platform host earns its 15 factors — OIDC-delegated auth, telemetry, startup refusals, policy-as-tests, pixi-sourced deps (folded from platform-fifteen-factors)

# The platform host earns its 15 factors

## The Dream

`src/platform` is ahead on deployment (chart + OCP overlay + restricted-v2)
and engine integration, but behind on platform hygiene: no telemetry
(structlog/OTel), local-password auth (allauth signup + createsuperuser)
instead of OIDC-delegated identity, pip requirements files inside a
conda-forge factory, no startup refusal contract, no policy-as-tests. The
dream: the host earns the 15-factor bar — identity keyed on `idp_subject`
with roles derived per-authentication from IdP group claims; request_id/
trace_id on every log line with OTLP export when configured; two-stage
fail-fast misconfiguration refusals; dependency/credential/typing policy as
tests; pixi.toml as the sole dependency authority.

## Grounding

Reference implementation: millsks/django-15-factor-base (MIT — patterns and
code borrowable with notice), same cookiecutter-django lineage, verified
2026-08-22 (intake report). Local backing-services substrate: millsks/
devinfra (MIT) folds in — Keycloak realm-as-code (aud+roles claims,
reimport round-trip), the LGTM observability stack, smoke-test.sh, the
documented Redis `noeviction` rationale (LRU silently drops Celery tasks).

## Constraints / Non-goals

Convergence-checked: `spec-django-accelerator-framework` (mason) is the
TEMPLATE pipeline — different scope; this hardens the live host. Not a
re-platforming: AD-4/AD-17 topology untouched; OIDC lands beside the OCP
chain (Keycloak locally via devinfra patterns, real IdP later). Kin:
`local-ocp-hybrid-environment` (12.4's workstation substrate),
`developer-machine-bootstrap`.

## Realization log

- **2026-08-22** — Seeded from the seven-repo external analysis (`f0c695758c`);
  `spec-platform-fifteen-factors` derived under pyforge-steward and decomposed into the station
  backlog the same day (`a20192dd84`). Spec status `ready`.
- **2026-09-09 (fleet readiness pass)** — Log resumed; it had stopped at 2026-08-22 while Epic 16 finished 5/5 `done` (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C7**). Keycloak realm-as-code is real (`src/platform/compose/keycloak/realms/platform-realm.json`), but **CAP-1's production half is empty**: `production.py` carries zero OIDC/IDP overrides, `base.py:214-215` has `IDP_CLAIMS_SNAPSHOT = None` / `IDP_USERINFO = None`, and `COMPONENT_OIDC_ISSUER` / `_CLIENT_ID` / `_JWKS_URL` / `_AUDIENCE` all default to `""` at `base.py:564-580`. **The Spec's open question is answered this pass: Keycloak in-cluster, deployed by the Foundry chart, as the default profile, with the `COMPONENT_OIDC_*` seam kept as the BYO-IdP escape hatch — minted as steward Story 48.9 and co-decided with Story 49.6.** Infra-kinds check: no breach — Keycloak is a chart `Deployment` storing state in the existing PostgreSQL. Correction to § *Grounding*: the devinfra "13-service" figure is unfounded — `src/platform/compose/compose.yml` runs **7** services (postgres, redis, platform, keycloak, worker, dbgpt, mcp-host) and there is no LGTM stack anywhere; the chart's 28 templates carry no observability backing service, which is why the flagged infra-kinds collision is LOW and not live. Status unchanged.

## 2026-09-17 — One pixi env for the platform image (folded from platform-image-one-pixi-env)

# One pixi env for the platform image

## The Dream

The platform image is one locked environment. A `pixi install --frozen -e python-agent-platform`
already contains Langflow, DB-GPT, and the Django-host extras that today arrive as a second
`pip install --no-deps` layer. Overlaps with conda fail at **lock** time, not as a build-time
uninstall that silently replaces `mcp`.

## What it looks like when real

- `src/platform/Containerfile` has no `python3 -m pip install --no-deps` RUN.
- `[feature.platform-image-pip]` is gone (or is not an installer); pins live on the env the
  image actually materializes.
- Rebuilding the image after a lock change does not uninstall conda `mcp` / `sse-starlette` /
  `python-multipart`.
- Pixitainer is **re-evaluated** as a Docker/Podman backend against the Story 10.3 contract
  (UBI9-minimal, no pixi in the runtime, GID 0, gunicorn CMD). If it still fails, the
  hand-rolled Containerfile stays and only the pip RUN dies.

## What is real

Story 16.1 made `[feature.platform-image-pip]` the sole *authority* for that pip layer; the
Containerfile still *installs* it with pip. CRC 2026-08-25 showed pip `--no-deps` uninstalling
conda `mcp` 1.28.1. Steward 12-7 is **done** (`/ht/` 200); this Dream is the queued follow-up
in `.cursor/pyforge-fleet-drain/NEXT-AFTER-12-7.md`.

Story 10.3 already rejected conda-forge `pixitainer` 0.8.3 (`pixi-containerize` → Apptainer
SIF). Mason presenton still uses pixitainer for other images. This Dream re-evals
`pixitainer-docker` only; it does not reopen a shared pixi *base* image
(`docs/dreams/pixi-container-image.md`).

## Constraints

- `platform-ci-test` stays a separate conda solve (psycopg3 vs image psycopg2).
- Runtime stage still copies the materialized env — **no pixi binary** in the final image.
- `python-agent-platform` may keep `mcp <2` for Langflow/FastMCP; host MCP 2.0 faces are not
  solved by folding the pip layer alone.
- Do not mix `meta.yaml` / `recipe.yaml`. Invoke `conda-forge-expert` if this effort touches
  recipes.

## Non-goals

- Re-proving steward 12-7 (Route / SCC / PVC / UID).
- Merging `platform-ci-test` into `python-agent-platform`.
- A repo-owned pixi base image (`pixi-container-image`).
- Eight stations in one image (`unified-container`).

## Realization log

- **2026-08-25** — Dream captured after 12-7 close. Intent from `NEXT-AFTER-12-7.md`. Spec:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-image-one-pixi-env/`.
- **2026-08-25** — Host extras on `[feature.python-agent-platform.dependencies]` (conda-forge;
  whitenoise `>=6.11`). Containerfile pip `--no-deps` removed; `platform_image_pip_layer.py`
  tombstone (exit 2). CAP-3: keep hand-rolled Containerfile (`pixitainer-eval.md` dated fail table).
- **2026-08-25** — SPEC shipped. `podman build` → `localhost/platform:one-pixi-env` (`8cbee8e8f879`).
  Image imports `django_structlog` + `rjsmin` (py312). Next cluster: Liquibase `:17`/`:18`, not 12-7.

## 2026-09-17 — The estate gets an S3-compatible object store, without becoming its operator (folded from platform-object-storage-kind)

# The estate gets an S3-compatible object store, without becoming its operator

## The Dream

The air-gap deployment target will have **NetApp StorageGRID** — S3-compatible
object storage — as infrastructure the operations team already runs, the same
way it already runs the Kubernetes cluster and the identity provider. Nothing in
the estate can point at it today, because `spec-pyforge-unifying-strategy`'s own
Constraint reads: *"infrastructure is exactly PostgreSQL + Redis + Kubernetes. A
component demanding a fourth backing service has failed its design review."*
`stack.md` names the obvious wrong answer explicitly: *"Never: a fourth backing
service (Vault-in-pod, MinIO, extra bus)."*

That line was written, and re-affirmed once already
(`sprint-change-proposal-2026-09-05-ad-1-reopen.md`, for Lane 1 media
specifically — a Kubernetes RWX PVC covered that case, no exception needed), to
stop the estate from becoming the **operator** of a fourth kind of
infrastructure it would have to run, patch, and reason about itself. Both
examples it names — Vault-in-pod, self-hosted MinIO — are things pyforge would
deploy and manage inside its own Helm chart.

StorageGRID isn't that. It's **ops-provided and externally operated** — pyforge
would only ever hold an S3 endpoint URL and credentials, the same shape the
estate already trusts for the identity provider (`canopy:AD-19`: *"pod specs
carry secret references only; no Vault HTTP from the platform image. Cluster
ESO/Vault stays outside the image"*). Consuming an externally-operated service
via a client library was never what the "fourth kind" rule was written to
forbid — self-hosting one was.

**What this Dream asks for:** a bounded, dated exception under AD-1 — object
storage specifically, consumed via an S3 client only, credentials and endpoint
taken as configuration never hard-coded, never a service pyforge deploys inside
its own platform image or Helm chart. Not a reopening of Lane 1 media's own
settled RWX-PVC answer, and not a licence for any other new backing service —
this is scoped to exactly the one kind, exactly the one consumption pattern.

**The local-dev half.** Nobody develops or tests against production
StorageGRID. This session verified, live, two real pixi-installable
candidates for a local equivalent:

- **Silo** (`pgsty/silo`) — a maintained fork of the actual MinIO codebase
  (same S3/IAM API surface, same on-disk format, same `MINIO_*` env vars),
  born because upstream MinIO gutted its own community edition in 2026.
  Real release binaries for Linux, macOS, **and Windows** (confirmed against
  live GitHub release assets: `darwin_amd64`/`darwin_arm64`,
  `linux_amd64`/`linux_arm64`, `windows_amd64`/`windows_arm64`). No
  conda-forge feedstock exists for it yet — this repo, being a conda-forge
  recipe factory, is positioned to author one.
- **Garage** — a real, from-scratch S3-compatible object store, already on
  conda-forge today (confirmed via live feedstock lookup), but Linux/macOS
  only (no Windows build, upstream or packaged) and a deliberately narrower
  S3 API surface than Silo/MinIO's.

Silo is the better long-term fit — full three-OS coverage, closer API fidelity
to what real StorageGRID behavior looks like — at the cost of needing a recipe
authored first. Garage works today with zero extra packaging work, at the cost
of no Windows story and a narrower feature set. The Dream asks for **both**,
pluggable, Silo as default once its recipe exists — the same default-plus-
alternatives shape this session already built for scribe's nightly-trigger
installer (`PYFORGE_SCRIBE_TRIGGER_BACKEND`), reused here rather than invented
fresh.

## Non-goals

- Not migrating Lane 1 media, or any other feature, onto object storage in
  this pass. That stays on its own settled RWX-PVC answer unless a separate,
  later Dream/story reopens that specific question with its own justification.
- Not self-hosting MinIO, Silo, or Garage inside the deployed platform image
  or Helm chart, in production. Production consumes StorageGRID as an
  external endpoint only.
- Not a general-purpose "add any infra we feel like" precedent. This Dream is
  scoped to object storage specifically, with its own stated justification
  (ops-provided, externally operated, consumed via client) — it does not
  loosen AD-1 for anything else.

## Realization log

- **2026-09-10** — Dream seeded from a live conversation investigating where
  media and CycloneDX SBOMs are stored under the current infra-kinds lock.
  Both turned out to already have working, non-object-storage answers (Lane 1
  media: RWX PVC, re-affirmed 2026-09-05; CycloneDX SBOMs: warden emits them
  as a plain `--sbom-output` file artifact, never touching the platform's own
  storage boundary) — but the real driver surfaced during that same
  conversation: NetApp StorageGRID will exist as ops-provided air-gap
  infrastructure, and nothing in the estate can consume it yet. Garage and
  Silo were both verified live (conda-forge feedstock lookup for Garage; real
  GitHub release assets for Silo) as the two pixi-installable local-dev
  candidates, with Silo chosen as the intended default given its fuller
  three-OS coverage and closer MinIO/StorageGRID API fidelity, Garage kept as
  the pluggable alternative. Next: `bmad-correct-course` against this Dream to
  process the AD-1 exception formally, matching the 2026-09-05 precedent's own
  procedure exactly, then decompose the implementation (Silo conda-forge
  recipe, local pixi tooling, a minimal S3-client seam) into stories.
- **2026-09-10 (later, same session)** — processed via `bmad-correct-course`
  (`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`). AD-1
  gained the dated consumed-not-self-hosted exception in
  `spec-pyforge-unifying-strategy/SPEC.md` (and `stack.md`'s own "Never" line
  qualified to match); decomposed into steward **Epic 50** (Stories 50.1-50.3):
  the Silo conda-forge recipe, local-dev pixi tooling (Silo default / Garage
  alternative), and a minimal S3-client seam. Status: `pitched` → `specified`.
- **2026-09-10 (later still, same session)** — Epic 50 drained 3/3. Story 50.1:
  `recipes/silo/recipe.yaml` authored, all four CFE gates green locally,
  published to `https://anaconda.org/SelfExplainML/silo` (`local-recipes#1183`).
  Story 50.2: the standalone `platform-object-storage` pixi feature +
  `scripts/platform_object_storage.py`, both backends' up/down/status verified
  live (idempotent, real S3 traffic, Garage's clean Windows refusal exercised)
  (`local-recipes#1184`). Story 50.3: `src/platform/config/object_storage.py` +
  a real round-trip test against an ephemeral local Silo, `platform-ci-local
  -- --test` full green (`local-recipes#1185`). All four capabilities in
  `spec-platform-object-storage-kind/SPEC.md` carry `verified:` lines; the
  Spec and this Dream both close as `shipped`/`realized`. Status: `specified`
  → `realized`.

## 2026-09-17 — One Django service hosts the agentic engines as pluggable applications, anywhere — including air-gapped (folded from python-agent-platform)

# One Django service hosts the agentic engines as pluggable applications, anywhere — including air-gapped

## The Dream

A single Django service — cookiecutter-django based, FastAPI-integrated — is the control plane
for the agentic engines this factory itself packaged: Langflow and DB-GPT join it as pluggable
Django applications, not as a constellation of bespoke deployments. The whole platform needs
exactly three pieces of infrastructure — PostgreSQL, Redis, and a Kubernetes container platform
(Red Hat OCP or Google GCP/GKE, Docker/Podman images) — and it deploys identically on the open
internet and inside an air-gapped enterprise network. Scaling is replicating the service;
statelessness is mandatory, not aspirational.

## What it looks like when real

- The host service renders from the [[django-accelerator-framework]] shape: cookiecutter-django
  with FastAPI integration, `env()`-split settings, health endpoints wired to K8s probes,
  mirror endpoints parameterized at render time.
- Langflow and DB-GPT integrate per their plugin dreams' **Pattern A** ([[langflow-django-plugin]],
  [[db-gpt-django-plugin]]): ASGI mount + schema isolation — one PostgreSQL carrying
  `public` / `langflow_schema` / `dbgpt_schema` (pgvector in the same instance if DB-GPT needs a
  vector store); Redis as the Celery broker for anything that must not block Django. A
  per-engine sidecar container is the fallback ONLY where pluggability fails.
- Every dependency resolves in conda space from packages this factory shipped
  (langflow-feedstock, db-gpt-feedstock) — the co-install is *verified to solve, not asserted*
  (2026-08-14 spike: py3.12 clean, 373 pkgs).
- Python 3.14 compatibility holds end-to-end (operator constraint); today's sole blocker is
  langflow-base's `bcrypt ==4.0.1` pin — a named prerequisite, not a surprise.
- Air-gapped deployment is first-class: internal-registry images, mirrored conda/pypi indexes
  only, zero-CDN static assets, env/secret-mount credentials through the existing config seams,
  internal-CA trust — the posture [[enterprise-airgap]] established and the five enriched
  source-catalog dreams detail.

## What is real

- Both engines are live conda-forge packages this factory delivered (langflow-feedstock pushed
  2026-08-13; db-gpt-feedstock 2026-07-22).
- The feasibility spike passed (py3.12), the py3.14 blocker is isolated to one pin, and the
  topology/infra/architecture decisions are recorded with dates in the five family dreams.
- ~~Nothing of the platform itself exists yet — no `src/platform/` tree, no rendered host, no
  pluggable app.~~ *(Written 2026-08-14; **superseded 2026-09-09**, fleet readiness pass.
  `src/platform/` is a live cookiecutter-django host: Langflow on Pattern A with real
  `search_path` isolation (`config/settings/base.py:613-633`), DB-GPT on Pattern B
  (`config/asgi.py:67-85`), a Helm chart with an OCP overlay, and Epics 10–12 / 16 / 43 shipped.
  The original line is kept struck through as the record of where the Dream started — see
  § Realization log.)*

## Constraints

- **Infrastructure is exactly** PostgreSQL + Redis + Kubernetes. A component that demands a
  fourth piece of infrastructure has failed its design review.
- Statelessness is mandatory — every container ephemeral, all state in PostgreSQL/Redis.
- Air-gap parity: any capability that only works with internet egress is incomplete.
- The strict engine-isolation rules from the plugin dreams stand: schema isolation is real
  (`search_path`), local-disk state paths are forced off, dependency footprints stay per-pattern.
- This repo's factory remains the package source; the platform consumes, it does not fork.

## Non-goals

- **Not** a re-litigation of the monolith-vs-microservices pair — the operator direction
  (2026-08-14) is pluggable-apps-in-one-service with sidecars only on pluggability failure;
  the sibling topology dreams record the full decision trail.
- **Not** a new packaging effort — the engines are already on conda-forge.
- **Not** a fork of the factory's engines — the platform consumes the factory's published conda
  packages only; **`src/platform/` must not import `pyforge.*` station code** as the default
  boundary rule, with the two recorded brownfield carve-outs until their owning stories land:
  `src/platform/ingest/github_projects/*` (eight `pyforge.steward.*` imports) and
  `django-atlas` portal tests (allow-listed `pyforge.steward.dashboard` imports). *(Corrected
  2026-08-14: originally "not owned by this repo's codebase"; the operator's monorepo decision
  places the platform IN this repo at `src/platform/` — the boundary survives as this import
  rule, not a repo wall. Qualified 2026-09-10, Story 48.8 — the absolute ban was knowingly
  false against live code.)*

## Kinships

- [[django-accelerator-framework]] — the host's basis; its activation trigger is this platform.
- [[langflow-django-plugin]] / [[db-gpt-django-plugin]] — the pluggable-app contracts.
- [[enterprise-multi-agent-orchestration]] / [[asgi-multiplexer-monolith]] — the decided
  topology pair; their Realization logs carry the spike evidence and constraints.
- [[enterprise-airgap]] — the air-gap posture this platform inherits.

## Realization log

- **2026-08-14** — Captured and spec'd the same day (spec-python-agent-platform, pyforge-steward)
  as the named subject project the Django/Langflow/DB-GPT family was waiting for. Consolidates
  the operator's four same-day decisions: (1) core infra = PostgreSQL + Redis + K8s only;
  (2) one cookiecutter-django host with FastAPI integration based on
  [[django-accelerator-framework]]; (3) engines as pluggable Django applications, sidecars only
  on pluggability failure; (4) air-gap parity per the enriched source-catalog dreams. Feasibility:
  conda-native co-install solves on py3.12 (373 pkgs); py3.14 blocked solely by langflow-base's
  `bcrypt ==4.0.1` (langflow-feedstock maintenance item). Name chosen by the operator:
  **python-agent-platform**.
- **2026-08-14** — **All three Spec open questions resolved (operator), recorded in spec-python-agent-platform:** (1) first deployment target = Red Hat OCP (strictest-superset image discipline, air-gap exercised where it is real), GKE as the CI portability profile; (2) the platform lives IN this repo at `src/platform/` per the monorepo goal — cookiecutter-django roots there, one new env-scoped pixi feature pins py3.12 until the bcrypt prerequisite clears, and the factory/platform boundary becomes an import rule (published conda packages only, never `pyforge.*`); (3) first render ships on py3.12 with the bcrypt fix running in parallel (upstream passlib-drop ask + runtime-validated langflow-feedstock loosening — upstream main re-verified today still pinning bcrypt==4.0.1) and py3.14 as a release gate. Knock-ons: reusable-cicd-workflows stays parked; pixi-container-image activates when the platform containerizes. The Spec is now decomposition-ready.
- **2026-08-21** — **DB-GPT deviates to Pattern B (sidecar), per AD-14 — and pattern selection becomes a config switch, not a fork.** Story 11-2 hit a real fastapi-pin conflict between `dbgpt-app` and `langflow-base` in the shared environment — no version satisfies both, confirmed live. Full deviation record: [[db-gpt-django-plugin]] Realization log. The "sidecars only on pluggability failure" default (line 29 above) held as designed; Langflow remains on Pattern A. Operator direction: rather than a one-off DB-GPT code path, the platform host gains a per-engine, per-pattern configuration seam (A vs. B) that any future integration reuses and that lets DB-GPT revert to Pattern A later as a config change once upstream resolves the conflict — formalized as an architecture-spine addition via `bmad-correct-course` ahead of Story 11-2's re-scoping.
- **2026-09-09 (fleet readiness pass)** — Body corrected, history kept (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, Class B row stB / § 2.3 **C7**). § *What is real* still asserted "Nothing of the platform itself exists yet — no `src/platform/` tree" in a Dream whose Spec's `surface:` **is** `src/platform/**`; the line is now struck through and dated rather than deleted. Two further staleness findings recorded here rather than edited, because they are contract-shaped and belong to the merge, not to a doc sweep: (1) § *Constraints* still narrates the py3.12 / `bcrypt ==4.0.1` gate that Story 43.6 closed — `[feature.python-agent-platform.dependencies]` pins `python = "3.14.*"` (`pixi.toml:47`); (2) § *Non-goals* states the `pyforge.*` import ban **absolutely** while live code knowingly violates it at two carve-outs — `src/platform/ingest/github_projects/` imports `pyforge.steward.{keys,sync}` at 8 sites and sits outside the import-linter's `root_packages` (`src/platform/pyproject.toml:288-289`), and `django-atlas`'s portal imports `pyforge.steward.dashboard.*` under a test allow-list (`src/platform/tests/test_station_portal_shells.py:113`). Either narrow the rule to the request path or name the two carve-outs; do not leave an absolute that live code contradicts. **Sequencing:** Story 48.8 supersedes `spec-python-agent-platform` into `spec-pyforge-unifying-strategy`, and 48.8 precedes the regeneration drill — a merge that copies text forward would carry these lines into the surviving contract, so 48.8 must be sequenced after, or explicitly include, this correction. Four sibling Specs point `absorbed-into: spec-python-agent-platform` (`spec-asgi-multiplexer-monolith`, `spec-langflow-django-plugin`, `spec-enterprise-multi-agent-orchestration`, `spec-db-gpt-django-plugin`, each at `SPEC.md:5`) and must be retargeted in the same story; `pap:` stays a live id prefix (280 citations across 60 files and four other stations, incl. `scripts/ad_citation_check.py:123-124`) — the merge moves the TEXT, never the namespace. Status unchanged.

## 2026-09-17 — A scratch worktree for one story's work is one command, not five (folded from scratch-worktree-lifecycle)

# A scratch worktree for one story's work is one command, not five

## The Dream

Landing a single story — or drafting a Dream, or any point-in-time task scoped to one story's
worth of work — currently means a human or agent hand-typing the same five-step ritual every
time: `git worktree add <scratch-path> -b <branch> origin/<source-branch>`, do the work, `git
worktree remove <scratch-path>`, and (if the story touched a gitignored Tier-3 feed) manually
`rsync`-mirroring it in and back out because `implementation-artifacts/` never exists in a fresh
worktree. Nothing wraps this. The pattern is right there in this repo's own recent history — a
dozen-plus scratch worktrees created and destroyed by hand in a single session's worth of landing
passes, each one the identical five commands, each one a chance to typo the branch name or forget
the cleanup. `steward workspace start/ls/clean` (or an equivalent verb set) makes this one command
each: open a scratch worktree for a named story, see what's currently open, and prune what's
already merged — the same shape `bmad-loop clean` already gives loop-run worktrees, but for
human/agent-driven point-in-time work instead.

## What it looks like when real

- `steward workspace start <story-or-task-slug> [--from <branch>]` creates a worktree at a
  conventional scratch path, checks out a new branch off the given source (defaulting to
  `origin/main`), and reports the path — replacing the current copy-pasted `git worktree add`
  invocation with one command that can't typo the branch-name/source pairing.
- `steward workspace ls` lists every currently-open scratch worktree this tool created and its
  branch — answering "what did I leave open" without a raw `git worktree list | grep`.
- `steward workspace status [<slug>]` reports, per worktree, what `ls` deliberately does not:
  dirty/clean, ahead/behind its source, and whether its branch has already merged — the health
  check `ls` only gestures at. Kept as its own verb rather than folded into `ls`'s output because
  `ls` should stay a cheap enumeration (no git-status subprocess per worktree) while `status` is
  the one that pays that cost, mirroring `developer-workspace-management`'s own split between
  `ls` and `status` in its source form.
- `steward workspace clean [--merged-only]` removes worktrees whose branch has already merged
  (or, unfiltered, prompts per-worktree) — the same shape as `bmad-loop clean`'s archive-not-delete
  discipline for loop-run worktrees, applied to this tool's own scratch worktrees instead.
- Every verb accepts `--json` for machine-readable output, matching this repo's own established
  convention (`fleet-picture --json`, every detector's `--json`) — `ls`/`status` in particular are
  exactly the kind of output another tool (or a future automated landing pass) would want to
  consume programmatically rather than scrape from text.
- Nothing here reimplements git — every verb is a thin, named wrapper around `git worktree`
  itself, matching Steward's own "hexagonal wrap-never-reimplement" identity.

## What is real

Nothing built yet — this is a fresh `dreamt`-stage capture, motivated by directly observed
repetition rather than speculation. The five-step manual pattern this replaces is the literal
sequence used throughout the current session's own landing passes (create scratch worktree off
`origin/loop/pyforge-<slug>`, merge `origin/main`, do the work, mirror the gitignored Tier-3 feed
in via `rsync` when needed, remove the worktree) — evidence that this gap is live, not
hypothetical, though no incident (unlike [[bmad-switch-scope-enforcement]]'s DW-1-4-2) has yet
resulted from it; it is pure toil, not yet a documented bug.

A sibling org's `developer-workspace-management` dream (`wf-dev-cli`'s `commands/workspace.py`,
1,187 LOC) does a related, much larger thing: MULTI-repo worktree coordination (a "workspace" is
several repos' worktrees, one per registered project, opened together via a generated
`.code-workspace` file and editor launch). That shape doesn't map onto this repo, which is a
single mono-repo — there is no second repo to coordinate, no `.code-workspace` file needed since
the editor already opens the one root. This Dream keeps only the piece that transfers: the
open/list/clean lifecycle for a scratch worktree, scoped to one repo, one branch, one story.

## Whose job this is, and why it isn't Marshal's

Investigated directly, not assumed, because Marshal already owns `marshal init`/`bmad-loop-worktree`
— the closest-looking existing machinery:

- Marshal's own `spec-pyforge-marshal/SPEC.md` CAP-1 contract is scoped, in its own words, to
  "an isolated... place for a **loop** to run" — every success criterion (marker/symlink
  agreement, Tier-3 backlink, teardown refusing on uncommitted work) is phrased around loop-run
  isolation specifically, never a general story-scoped developer worktree.
  `marshal init <slug>` creates exactly ONE worktree per station slug, at a fixed path
  (`<loop-home-root>/<slug>`), on a fixed branch (`loop/<slug>`) — there is no notion of "one
  more, for this specific story, then discard it."
- `cli/init.py`'s own module docstring explicitly declines to generalize: "no legacy sibling-repo
  layout (the spec's own Boundaries & Constraints — do not reinvent the sibling-repo layout)."
  Marshal has already, deliberately, drawn this line.
- Steward's own `provision.py` disclaims worktree creation ("`marshal init`... it never
  provisions") — but that disclaim is scoped to NOT duplicating Marshal's LOOP-home machinery,
  not a blanket refusal of worktree creation for a different purpose. Steward's own Dream is "the
  estate the factory stands on" — developer/operator ergonomics broadly — and this is squarely
  that: a human or agent's own point-in-time workspace, not a loop's.

## Constraints

- **Never touch a loop-run worktree.** This tool's scratch worktrees and Marshal's loop homes
  are different lifecycles at different paths; this Dream must not read, list, or clean anything
  under Marshal's `<loop-home-root>/<slug>` paths.
- **Wrap, never reimplement.** Every verb is a named `git worktree` invocation plus bookkeeping —
  no custom git-plumbing logic that could drift from git's own semantics.
- **A scratch worktree that touches a BMAD project should verify its context**, not assume it —
  see Kinships below.

## Non-goals

- **Not multi-repo coordination.** No `.code-workspace` file, no `clone-repos`, no notion of a
  "project" spanning several git repositories — this repo is a mono-repo and stays one.
- **Not automatic editor launch.** `workspace start` reports a path; opening it in an editor is
  the caller's own next step, same as any `git worktree add` today.
- **Not a replacement for `bmad-loop clean`** — that tool's archive-not-delete discipline for
  loop-run worktrees is untouched and out of scope here.

See "Full feature audit" below for the per-feature reasoning behind these and every other
capability the source dream carried that this one doesn't.

## Full feature audit against `developer-workspace-management`

Every verb the sibling org's dream names, and this Dream's disposition on each — so a future
reader can decide whether to include or enhance any of the omitted ones without reconstructing
this audit by hand:

| Source feature | Disposition | Why |
|---|---|---|
| `workspace start {feature}` (multi-repo) | **Included, narrowed** | Kept, scoped to one repo — no second repo exists here to coordinate. |
| `.code-workspace` file generation | **Omitted** | No second repo to open together; the editor already opens this repo's one root. |
| Auto-open editor | **Omitted** | Keeps the verb scriptable/composable rather than assuming an interactive editor session — same reasoning as `workspace open` below. |
| `workspace add` (add a repo to an existing workspace) | **Omitted** | No multi-repo "workspace" concept exists here to add a repo *to*. |
| `workspace rm` (remove a repo from a workspace) | **Omitted** | Same reasoning as `add`. |
| `workspace clean` | **Included** | `workspace clean [--merged-only]`. |
| `workspace ls` | **Included** | `workspace ls`. |
| `workspace status` (parallel git-health checks) | **Included** (2026-08-14 audit) | Was folded into `ls`'s description in the first draft, undersold as a result; now its own verb — see "What it looks like when real." |
| `workspace open` (reopen editor) | **Omitted** | Same reasoning as auto-open — this tool reports paths, not opens editors. |
| `workspace update` (sync/update across repos) | **Omitted, not ruled out** | No PyForge equivalent identified yet. In single-repo form this would mean "fast-forward the scratch branch from its source" — plausible and useful, but unlike `start`/`ls`/`clean`/`status` it doesn't map onto anything directly observed this session, so it's left as a genuine open question rather than silently dropped. |
| `workspace clone-repos` | **Omitted** | Mono-repo — nothing to clone. |
| JSON output | **Included** (2026-08-14 audit) | Missing from the first draft despite matching this repo's own strong `--json`-everywhere convention; now every verb. |
| `pyforge.toml [projects]` registry | **Omitted** | No config file of this shape exists or is needed for a single mono-repo; see [[developer-machine-bootstrap]]'s own audit for the adjacent question of whether *any* `pyforge.toml`-equivalent belongs in this repo. |
| `argcomplete` tab completion | **Omitted, unverified** | No PyForge CLI (checked: `fleet-picture`, the detectors, `bmad-switch`) currently registers tab completion — adding it here would set a repo-wide precedent this one Dream shouldn't decide unilaterally. |

## Kinships

[[bmad-switch-scope-enforcement]] (a scratch worktree opened against a specific BMAD project is
exactly the caller [[bmad-switch-scope-enforcement]]'s `verify_scope` primitive was designed for —
cross-station kinship, Marshal's mechanism called from a Steward-owned verb, not a merge) ·
[[pyforge-steward]] (the estate; this Dream's natural home per steward's own developer-ergonomics
identity) · [[bmad-module-provisioning]] (the investigative-rigor precedent this Dream's
"whose job" section follows — ruling a nearby station out on its own documented boundaries rather
than by default)

## Realization log

- **2026-08-14** — Dream captured, alongside [[developer-machine-bootstrap]] and
  [[bmad-switch-scope-enforcement]], while evaluating a sibling org's dream catalog for PyForge
  fit. Scoped down hard from the source dream's multi-repo `.code-workspace` shape to a
  single-repo scratch-worktree lifecycle, grounded in this session's own directly-observed
  repetition (a dozen-plus hand-run `git worktree add`/`remove` cycles across landing passes, no
  tool wrapping any of it). Ownership investigated rather than assumed: Marshal's `marshal init`
  is explicitly loop-home-scoped (its CAP-1 contract's own words) and its own docstring declines
  to generalize ("do not reinvent the sibling-repo layout"); assigned to Steward as the
  developer-ergonomics station whose disclaim of loop-worktree creation was scoped to avoiding
  duplication of Marshal's machinery, not a refusal of worktree tooling generally.

- **2026-08-14 (same day)** — Feature-parity audit against the source dream, requested after the
  initial capture, found `workspace status` and JSON output silently undersold rather than
  deliberately excluded; both folded in above. Every other source feature now carries an explicit
  disposition in "Full feature audit" rather than living only in a conversation transcript.

- **2026-08-14** — Spec authored (spec-scratch-worktree-lifecycle, pyforge-steward) by the
  2026-08-14 dream-backlog audit: workspace start/ls/status/clean over git worktree,
  own-worktrees-only bookkeeping, archive-not-delete clean.

## 2026-09-17 — A dashboard can be handed to the company without being rebuilt (folded from secure-live-dashboards)

# A dashboard can be handed to the company without being rebuilt

## The Dream

Someone builds a Vizro board that answers a real question. Then it has to leave the laptop —
and today that is where it stops, because everything that makes it safe to hand to a company
is missing and none of it is dashboard work: who is looking at it, which rows they may see,
what they did, how it runs behind the corporate proxy, and what happens when someone
bypasses the UI and calls the download endpoint directly.

The dream is that this second half already exists as a **pattern any dashboard in the estate
adopts**, not as a thing each dashboard reinvents. Atlas's board is the first adopter and the
proof; it is not the subject. A second dashboard should reach production by declaring which
column carries access and which header carries identity — not by rewriting an audit schema, a
container stack, and a CI security suite.

## What it looks like when real

- A dashboard gains row-level isolation by naming its access column and its proxy headers.
  No dashboard writes its own filtering pipeline.
- The master dataset is cached once, server-side, and shared across concurrent users; the
  role-filtered slice is computed **per request and never written back to the shared cache**.
  Two users at once produce one upstream fetch, not two, and never each other's rows.
- A viewer cannot see an admin page in the DOM at all — the navigation tree is built from
  the caller's role, not hidden with CSS.
- Every load, filter, navigation and export lands in an audit trail with the row count, not
  merely the fact that something happened.
- Someone who bypasses the UI and posts directly to a restricted download endpoint is
  refused **server-side**, logged as critical, and announced to a SIEM/Slack/Teams webhook —
  the front-end absence of a button is never the control.
- The same stack runs against SQLite on a laptop and PostgreSQL in production by changing one
  connection string, so the security boundaries are exercised in development rather than
  first met in production.
- Exports can be delivered encrypted, and the toggle is configuration rather than a fork.
- The security boundaries are asserted by tests that mock different corporate identities and
  prove isolation holds — and those tests run on every push, against an in-memory database,
  before a merge is allowed.
- **The same Vizro board can also be published as a free static site on GitHub Pages** — its
  Plotly components exported to HTML, assembled into a responsive grid, rebuilt by CI — for the
  case where the audience is everyone and there is nothing to isolate. One dashboard
  definition, two delivery modes, and **choosing a mode is choosing a security posture, not a
  hosting preference**: the static mode ships its data to the browser, so a board that has
  declared role isolation cannot be delivered that way.

## What is real

- **Both delivery modes exist as intake material.** The hosted one is the full blueprint
  below; the static one is a Vizro→GitHub Pages workaround
  (`docs/intake/secure-live-dashboards/vizro-static-github-pages-workaround.md`) — export
  `vm.Graph(figure=...)` components via `fig.to_html(full_html=False, include_plotlyjs='cdn')`,
  inject into a responsive grid template, and have GitHub Actions publish to `gh-pages`, with
  optional client-side filtering through `Plotly.react()`.
- **The full blueprint exists** as intake material: system integration and token lifecycle,
  the two-step RLS pipeline (global cache → per-request slice), the audit schema
  (`id`, `timestamp`, `username`, `role`, `action_description`, `row_count`), webhook alerting,
  role-gated and optionally Fernet-encrypted CSV export, the four-service Compose stack
  (app / Postgres / Redis / backup) behind an Nginx edge, the corporate palette, the pytest
  security suite, and GitHub Actions + GitLab CI pipelines.
- **Vizro is already in this repo and already load-bearing.** `pyforge-atlas` ships a
  BSL-driven Vizro dashboard (`pyforge/atlas/dashboard/app.py`) with a `dashboard-dryrun`
  gate and a `query_vizro_ai` MCP tool. This Dream does not introduce Vizro; it makes what is
  already here shippable to other people.
- **Steward already owns the neighbouring surfaces.** `spec-unified-container` (the one-image
  Guild build), `spec-enterprise-airgap`, and the `keys` credential surface are the same
  estate this pattern deploys into — including a live secrets-scan gate
  (`scripts/container-gates`) that already refuses to bake credentials into an image.

## Why Steward, and why a pattern

The blueprint is roughly five parts security and infrastructure to one part dashboard: token
lifecycle, identity from proxy headers, row isolation, audit persistence, webhook alerting,
export gating and encryption, WSGI topology, container orchestration, TLS and subnet policy,
and a CI security suite. Steward is the station that *"provisions the engines the factory runs
on, deploys the services it ships, holds the keys that guard it"* — Vizro is the thing being
secured here, not the work being done.

And a pattern rather than an application, because the second dashboard is where the value
lands. A one-off hardening of one board leaves the next one facing the same wall.

## Open questions

- **Where does the pattern live?** A `steward` subcommand that scaffolds and verifies, a
  library the dashboard imports, or a template repository. Each implies a different upgrade
  story when the pattern improves — and an adopter that has diverged is the case that matters.
- **How much does the pattern own versus assert?** It could *provide* the RLS pipeline and
  audit writer, or it could *verify* that a dashboard has an acceptable one. The first is
  reusable and rigid; the second tolerates dashboards that already made their own choices.
- **Does the identity model bind to one proxy convention?** The blueprint reads `ROLE_HEADER`
  and `USER_ID_HEADER` from the environment, which is configurable but still assumes headers
  from a trusted reverse proxy. What happens where that assumption does not hold is not
  answered.
- **Is trusting proxy headers acceptable here?** Anything that can reach the app directly can
  forge them, so the pattern's guarantee is only as strong as the network path. Whether that
  needs a defence, or an explicit recorded assumption, is a genuine security decision.
- **Does the audit trail have a retention and access story?** It accumulates every user's
  activity, which makes it both a compliance asset and a privacy liability.
- **Is Redis a requirement or one cache backend?** The blueprint names it for cross-worker
  shared state; whether the pattern mandates it or treats it as pluggable changes the floor
  for a small adopter.

## Non-goals

- Not a replacement for Atlas's dashboard, and not a second Vizro application. Atlas's board
  is the first adopter and the proof.
- Not an authentication system. The pattern consumes an identity that a corporate proxy has
  already established; it never authenticates a user itself.
- Not a general BI platform. It secures dashboards this estate builds, not arbitrary
  third-party analytics.
- Not a decision, here, about how the pattern is packaged or how much it owns — those are the
  open questions above and belong to the Spec and architecture phases.

## Realization log

- **2026-08-09** — Seeded from a complete, externally-authored blueprint (role-based live
  dashboard architecture: RLS, audit, webhooks, encrypted export, Compose/Nginx stack,
  security CI). Operator chose `owner: steward` over `atlas` on the reasoning above, and
  scoped it as a **reusable pattern** other dashboards adopt rather than a hardening of the
  existing board or a standalone system.
- **2026-08-09** — Spec produced (`bmad-spec`), then architecture (`bmad-architecture`):
  the pattern is a **library in the request path plus a subcommand around it**, split on the
  process boundary; the library provides, the subcommand verifies; verification is Steward's,
  with a carve-out to Doctor for verdicts on Steward's own implementation.
- **2026-08-09** — Second adopter named, and it changed the pattern: Herald's
  `spec-herald-moments-2-4-live-backend` **adopts this rather than building its own backend**,
  which answered its "where does a persistent Herald backend run, and under whose operational
  ownership" question with *Steward's perimeter*. Because Herald commits to no framework,
  the pattern was un-bound from Vizro (binds at the WSGI/request layer instead); because
  Herald needs a CI webhook receiver, machine callers gained an HMAC-proof path that never
  grants a human role. Marshal's fleet board is a **candidate** — the fit is the estate's
  strongest, since `docs/dashboard/data.js` is already keyed by station — but it needs its
  own Dream, since `spec-factory-console` owns that board and is already realized.
- **2026-08-09** — Second delivery mode added: the static Vizro→GitHub Pages path. It is
  **not** a cheaper way to ship the same board — its client-side filtering embeds every
  role's rows in the page, so the two modes are a per-dashboard choice of security posture.
  This is why Marshal wants an *alternate* live board rather than a secured static one.
- **2026-09-09 (fleet readiness pass)** — **Built, not adopted** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, rows stB-B6 / stB-E3 / § 2.3 **C15**). Epic 9 is 7/7 `done`, and of the nine modules under `pyforge/steward/dashboard/` only `cache`, `filtering` and `declarations` have any consumer outside the package — all in `django-atlas/src/django_atlas_portal/board.py:17-20`, over a **5-row in-process fixture** (`board.py:28-36`). `middleware`, `audit`, `views`, `navigation`, `models`, `export` have **zero** consumers. `pyforge.steward.dashboard` is in no `INSTALLED_APPS` (`src/platform/config/settings/base.py` has zero `dashboard` matches), so `AuditEntry` (`models.py:43`, `migrations/0001_initial.py`) has no table in any running deployment and Story 9.3's promise — "every load, filter, navigation and export lands in an audit trail" — is unexercised. **Vessel: Story 49.4, as one decision** — if 49.4 mounts Atlas's real Vizro board on the host it installs `pyforge.steward.dashboard` and routes the board's loads through `audit` + `export`; if 49.4 instead rewrites CAP-7's criterion to name the fixture, this Dream's Django half is rewritten as deferred in the same act. Accuracy note: `convergence.md:38,:129`'s "never adopted" is corrected to "adopted at fixture grade (`django-atlas/board.py:17-20`); the real Vizro board (`pyforge/atlas/dashboard/app.py`) imports zero steward modules" — the old wording understated what exists and would send an implementer to build a seam that is already there. Status unchanged in this pass.

## 2026-09-17 — The estate hosts its own BMAD catalog, not Claude's public marketplace (folded from self-hosted-bmad-marketplace)

# The estate hosts its own BMAD catalog, not Claude's public marketplace

> **Seed Dream.** Operator asked 2026-09-14 to capture "what you would still invent"
> after the suite on A is fully wielded: a self-hosted App Store. Live org
> inventory the same day (bmad-code-org, openteams-ai, nebari-dev,
> ownyourintelligence.ai) is recorded below so later research and `bmad-spec`
> do not re-discover it from chat. Scribe recall that morning:
> `scribe recall "self-hosted BMAD marketplace Hub Layer 3 labs" --mode planning`
> → **no grounded answer** — no prior team decision or Dream exists.

## The Dream

The estate points installers and agent harnesses at **our** module and skill
catalog — air-gapped if need be — and reviews what we publish. Claude's public
plugin marketplace and github.com are optional upstreams, not the only index.

A self-hosted App Store, in the shape that already exists: fork or mirror
`bmad-plugins-marketplace`, put `registry/` on internal git or object storage,
point the installer and Claude/Codex `extraKnownMarketplaces` at that clone,
use Builder / module-template (and SKF) as the publish path, add trust review
of our own.

What the org still does not ship — and this Dream names as the product — is a
hosted browse/buy UI, an air-gap index, billing, and Hub Layer 3. Those are
**three different SKUs**. Mixing them is how Hub LC-3 got bundled with
"Desktop/Web Application." Keep them distinct.

## Why now

Full BMAD-suite integration on A is done (steward Epics 46 and 47 `done`,
adoption register 13/13 `wield`). `spec-bmad-suite-lifecycle` still records
**"The whole labs marketplace"** as a non-goal of *that* chain — skill-by-skill
labs, never the store. Hub Launch (CAP-1..4) still parks **Skills / Agent
Marketplace** as later-cap **LC-3**. Air-gap cannot depend on github.com plus
Claude's public marketplace. This Dream is the later product those two
contracts deferred, not a reopen of either.

## Three SKUs (conclusion — do not collapse)

| SKU | Artifact | Reuse | Still invent |
|---|---|---|---|
| **A — BMAD module/skill catalog** | YAML registry + `npx bmad-method install` + Claude/Codex `extraKnownMarketplaces` | Fork/mirror [bmad-plugins-marketplace](https://github.com/bmad-code-org/bmad-plugins-marketplace); Builder + [bmad-module-template](https://github.com/bmad-code-org/bmad-module-template) + SKF as publish; [bmad-plugins](https://github.com/bmad-code-org/bmad-plugins) as the public Claude/Codex shape | Trust review of our own; air-gap **YAML** index; browse UI if we want more than a git tree |
| **B — Claude skill registry** (optional second face) | Claude Code skill dirs | Consume [nebari-dev/skillsctl](https://github.com/nebari-dev/skillsctl) (`explore` / `install` / `publish`, ConnectRPC + SQLite + OIDC). Kin to SKF, not an adoption | Point it at an internal clone; steward/object-storage wiring. Do not mint a second registry |
| **C — Hub Layer 3** | Ops / Cogs / Frames / Guards across independent Hubs; Tracks stay home | Vocabulary from the whitepaper / field guide; Frame Spec v0.2; nebari-frames as a *pattern*; [nebari-catalog-pack](https://github.com/nebari-dev/nebari-catalog-pack) + Harbor + nebi for **OCI packs** | The four-class marketplace, billing, inter-Hub exchange. Still **thesis** upstream (field guide 2026-08-18) |

**v1 default candidate (not chosen):** SKU A only. B is a later face. C stays
on Hub `later-caps.md` LC-3 until someone hoists it.

## What is real (measured 2026-09-14, not remembered)

### On A

- No hosted App Store. The suite **consumes and authors** catalogs.
- `spec-bmad-suite-lifecycle` non-goal: "The whole labs marketplace."
- `spec-intelligence-hub` Launch non-goal: marketplace / Desktop-Web App;
  LC-3 is adopt-anytime, not forbidden, not Launch.
- Scribe: no plugin packaging until a second consumer repo.
- Object storage is a **consumed** kind (`docs/dreams/platform-object-storage-kind.md`
  realized; steward Epic 50). A YAML or tarball index may live there. We do
  not become the operator of a fourth infra kind.
- `bmad-builder` is already wielded (`steward provision --module bmb`).
- `bmad-module-template` is authoring-only (steward 52.1 / [[suite-scaffold-and-mybmad-sidecar]]).
- MyBMAD is a **sprint GPS sidecar**, never a store (`spec-bmad-suite-lifecycle`
  and 52.1). [bmad-method-ui](https://github.com/bmad-code-org/bmad-method-ui)
  is the same class.

### bmad-code-org (live `gh repo list` 2026-09-14)

| Repo | Role |
|---|---|
| [bmad-plugins-marketplace](https://github.com/bmad-code-org/bmad-plugins-marketplace) | Official YAML registry, schema, trust tiers, PR submit, Claude `extraKnownMarketplaces`. Index at check time: **3 modules** |
| [bmad-plugins](https://github.com/bmad-code-org/bmad-plugins) | Claude + Codex plugin marketplace (`bmad-method` + `bmad-toolbox`) |
| [bmad-builder](https://github.com/bmad-code-org/bmad-builder) | Author / validate / distribute |
| [bmad-module-template](https://github.com/bmad-code-org/bmad-module-template) | Scaffold + `marketplace.json` |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | `npx bmad-method install` / `--custom-content` |
| [bmad-method-ui](https://github.com/bmad-code-org/bmad-method-ui) | VS Code + MyBMAD `web/` — not a store |

Outside the org, still relevant: SKF (`armelhbobdad/bmad-module-skill-forge`);
labs (`bmad-labs/skills`). `bmad-automator` is archived.

### ownyourintelligence.ai (field guide, fetched 2026-09-14)

A field guide, not a product. Distils the OpenTeams whitepaper *The Distributed
AI Economy* (Oliphant, Rev 9; canonical git
[openteams-ai/inthub-whitepaper](https://github.com/openteams-ai/inthub-whitepaper)
tag `v9` — cite that, never a PDF URL alone). Four traded classes: Ops, Cogs,
Frames, Guards. Tracks stay home.

Its own maturity ledger (site audit date **2026-08-18**, still the live copy
today) puts **“public marketplace” under thesis**. Nearest live analogue named
there: nebari.dev “Community hub (coming soon).” Collab Desktop is listed as
**exists** on `openteams.com` — that is the Desktop/Web Application
`spec-intelligence-hub` already refused to rebuild.

Leverage: vocabulary and “Tracks stay home.” Not a registry, installer, or
billing system. Do not endorse or market OpenTeams.

### openteams-ai (live `gh repo list` 2026-09-14)

No store. Protocols and distribution only.

| Repo | What it is | For this product |
|---|---|---|
| [frame-spec](https://github.com/openteams-ai/frame-spec) | Frame markdown + YAML (v0.2). No registry. RB-1: no LICENSE file and no git tag as of 2026-09-09 | Already used as git Frames (Hub CAP-2). Wrong artifact for BMAD modules. In-repo four-field preflight only — do not bind ACs to `tools/validate_frames.py` |
| [inthub-whitepaper](https://github.com/openteams-ai/inthub-whitepaper) | Rev 9 source of record | Cite by tag; do not reproduce |
| [apollo-capabilities](https://github.com/openteams-ai/apollo-capabilities) | Community Apollo bits as **OCI via nebi** | Same shape as conda/OCI publish, not `extraKnownMarketplaces` |
| checkmaite / datamaite / modelmaite | MAITE wrappers | Unrelated |
| POST Python / `pp*` | SciPy rebuild | Unrelated |

### nebari-dev (live `gh repo list` 2026-09-14)

This is the leverage, and it is **three different products**. Hub Dream RB-3
(2026-09-09) already mapped most of this; today's check confirms it still holds.

**Closest to a skill App Store — [skillsctl](https://github.com/nebari-dev/skillsctl)**
(Apache-2.0, last push 2026-08-26). CLI + ConnectRPC registry + SQLite BLOB
store + OIDC + `explore` / `install` / `publish` for **Claude Code skills**.
Docs: https://packs.nebari.dev/skillsctl/. Local backend: `DEV_MODE=true go run
./backend/cmd/server` on `:8080`. Hub research: “kin to SKF, not an adoption.”
README still says it **ships as the Claude Code skill registry**.

**Successor investment — [nebari-frames](https://github.com/nebari-dev/nebari-frames)**
(beta, Apache-2.0, Helm `oci://quay.io/nebari/charts/nebari-frames`). Hosted UI
+ CLI + MCP for **Frames** (context slots, inheritance, RBAC). README:
borrowed registry foundations from skillsctl; **new work goes here**.
SQLite single-writer, `replicaCount: 1` — a fourth infra kind, already parked
(Hub LC-2 / B9; git is our Frame store). Wrong artifact for BMAD modules.

**Marketplace-in-miniature for packs, not agents**

- [nebari-catalog-pack](https://github.com/nebari-dev/nebari-catalog-pack) —
  browses an **OCI** pack registry and installs packs into GitOps as ArgoCD
  Apps. Hub Dream: “the marketplace in miniature.”
- [software-pack-dashboard](https://github.com/nebari-dev/software-pack-dashboard)
  — running list of Nebari software packs.
- [nebi](https://github.com/nebari-dev/nebi) — OCI / pixi publish. Live scope
  is environment management; the paper’s larger “package Frames/Cogs/Ops/Guards
  across Hubs” role remains roadmap.
- [harbor-pack](https://github.com/nebari-dev/harbor-pack) — Harbor; air-gap
  **container** registry, not a BMAD YAML index.

**Do not reuse as the BMAD store**

- [collab-hub-pack](https://github.com/nebari-dev/collab-hub-pack) — Collab API
  (Frames store on fs / S3 / Postgres). Confirms the Desktop/Web Application
  non-goal — it exists upstream.
- [nebari-landing](https://github.com/nebari-dev/nebari-landing) /
  [apps-pack](https://github.com/nebari-dev/apps-pack) — can *host* a UI on the
  cluster; they are not a catalog.

## What we reuse vs invent

**Reuse (SKU A)**

1. Fork or mirror `bmad-plugins-marketplace` (schema, trust tiers, PR submit).
2. Host `registry/` on internal git **or** the consumed object-storage kind.
3. Point `bmad-method install` / `--custom-content` and Claude/Codex
   `extraKnownMarketplaces` at that clone.
4. Publish via Builder + module-template + SKF (already wielded / authoring-only).
5. Trust review of **our** listings — the public marketplace's tiers are a
   starting vocabulary, not a delegation of review.

**Invent (the product gap)**

1. Hosted browse / install UI — if v1 is more than a git tree. Not MyBMAD,
   not Collab, not nebari-frames.
2. Air-gap **YAML** index (object storage or git bundle). Harbor/catalog-pack
   cover OCI packs, not this schema.
3. Billing — candidate **non-goal for v1** (open question).
4. Hub Layer 3 (SKU C) — still thesis; not this Dream's v1 unless hoisted.

## Constraints

- Owner **steward** (suite install, object storage, Hub later-caps).
- AD-1: PostgreSQL + Redis + Kubernetes. Object storage is consumed, not
  self-hosted in Helm. **Do not** stand up skillsctl or nebari-frames SQLite
  as a fourth kind we operate.
- Do not replace Foundry with Nebari. Do not replace `conda-forge-expert`.
- Do not endorse or market OpenTeams. Distil; do not reproduce the whitepaper
  or commit its PDF.
- Do not rebuild Collab / Desktop-Web Application. MyBMAD stays a sidecar.
- Do not flip Epic 44 `blocked` keys or unpark 44.4 / 44.5 / 44.6.
- Foundry-product Dreams after 54.5 are authored on B. This is **A-only**
  (factory / suite / Hub).
- Suite-lifecycle's "whole labs marketplace" non-goal still holds **for that
  Spec**. This Dream is the later product, not a silent drop of that line.
- No station story and no ledger row until open questions close and
  `bmad-spec` (or a hand stub that then re-derives) settles the contract.

## Non-goals

- Reminting Hub CAP-1..4 or Launch.
- Dumping the whole labs marketplace into `.claude/skills/` (CAP-6 consent
  list stays).
- Becoming operator of a fifth infra kind.
- Folding `src/shared/packages/` (44.4 parked).
- First-install on B / P18.
- Replacing conda-forge-expert.
- Endorsing the OpenTeams store or calling Layer 3 "the OpenTeams marketplace"
  (the field guide de-branded it).
- Binding acceptance criteria to `frame-spec`'s unlicensed validator.
- Shipping billing, four-class exchange, or Collab in v1 unless an open
  question is answered that way.

## Open questions for the Spec

Answered 2026-09-15. Recorded in § *Operator rulings* below. They bind the
Spec re-derive. The Dream is `specified` only after that Spec is `ready`.

1. **v1 SKU** — A only, or A plus a consumed skillsctl face (B) in the same
   contract?
2. **Browse UI in v1** — git + `extraKnownMarketplaces` is enough, or do we
   invent a hosted browse/install surface (and where does it run)?
3. **Registry home** — internal git, object storage, conda channel, or a
   switchable set?
4. **Fork vs mirror** of `bmad-plugins-marketplace` — and do we carry their
   public index or start empty?
5. **Trust review** — who reviews our listings, and do we reuse their trust
   tiers or write our own?
6. **Billing** — non-goal for v1, or a named later-cap on *this* Spec?
7. **Layer 3 / Frames** — hoist the whitepaper marketplace, or only estate
   Frame list/share/add on the same rails?

## Operator rulings (accepted 2026-09-15)

Operator approved the session plan. Short names from the seed stay; each is
defined in prose here.

**SKU A** = our BMAD module catalog (YAML the installer already understands).
**SKU B** = a Claude Code skill store (`skillsctl`). **SKU C / Layer 3** =
buying and selling Frames, Cogs, Ops, Guards across independent Hubs, plus
billing. **LC-2** = Hub's parked "Frame registry." **LC-3** = Hub's parked
"skills / agent marketplace" ticket (this Dream owns the BMAD-catalog half).

1. **v1 is our BMAD catalog plus estate Frames on the same rails.** Not the
   Claude-skill store. That store gets an empty *source slot* so it can plug
   in later without a rewrite.

2. **A thin browse list in v1.** Operators can read the catalog (modules and
   Frames, trust tier, link or install hint). Not a click-to-install App
   Store. Not MyBMAD, Collab Desktop, or Nebari's Frames website. Install
   still uses `bmad-method install` / pixi.

3. **Git is where listings are edited. Shipping is a config switch.**
   Default ship path: a small pixi/conda package on the channel we already
   use (SelfExplainML locally; Artifactory when air-gapped). Object storage
   and a git bundle / tarball are extra backends you can turn on. Adding a
   backend later is a plugin, not a new product.

4. **Our repo, their file format. Not an automatic mirror.** Start with no
   community modules. We may point at official modules we already wield.
   Their public catalog is an optional *source plugin*, default off. The
   2026-09-14 "three modules" count is stale — do not bake in a number.

5. **Steward reviews our list.** Reuse their tier *names*: Unverified
   (validator passed), Community Reviewed (steward approved our PR), BMad
   Certified (operator endorsed, or already in the wielded suite). Their
   team does not review us. Every listing names which *source* produced it.

6. **No billing on this Spec.**

7. **No Layer 3.** Frame list / share / add-as-a-reviewed-git-listing is in
   (Hub LC-2 is done here). Frame files stay under `docs/foundry/frames/`.
   Do not stand up Nebari Frames or trade with other Hubs.

Creating a new GitHub repo for the catalog still needs operator confirm at
that story. Do not flip Epic 44 `blocked` keys.

## Kinships

[[intelligence-hub]] (Layer 3 / LC-3; Desktop/Web Application stays a
non-goal; Frames stay git) · [[bmad-suite-lifecycle]] ("whole labs
marketplace" non-goal of *that* chain) · [[bmad-suite-channel-product]]
(private channel as a marketplace in miniature) ·
[[suite-scaffold-and-mybmad-sidecar]] (template is publish path; MyBMAD is
not the store) · [[platform-object-storage-kind]] (air-gap index blob, if
chosen) · [[pyforge-steward]] (owner) · [[pyforge-unifying-strategy]]
(estate; do not re-decide the platform shape)

## Realization log

- **2026-09-14** — Seeded after the operator asked to capture "what you would
  still invent" and then to inventory openteams-ai, nebari-dev, and
  ownyourintelligence.ai before research/`bmad-spec`. Live `gh repo list` on
  both orgs + field-guide fetch the same day. Conclusion: none of those three
  surfaces ships a self-hosted BMAD App Store; skillsctl / catalog-pack /
  Harbor / nebi are optional later faces; Layer 3 remains thesis; Collab
  exists and stays a non-goal. Scribe planning recall: no grounded prior
  answer. Next act: `bmad-spec` under steward once the open questions close;
  until then the stub Spec is the chain link only (`status: draft`, Dream
  stays `dreamt`).
- **2026-09-15** — Operator approved Q1–7 (thin browse; git to edit; conda /
  Artifactory default ship backend; object storage and bundles as plugins;
  Frames list/share on the same rails; no Layer 3; no billing). Spec `ready`.
  Steward Epic **60** (60.1–60.4 `backlog`) is the marshal dispatch home.
  Dream `dreamt` → `specified`.

## 2026-09-17 — Module-template stays an authoring tool; mybmad joins as a sidecar, never the console (folded from suite-scaffold-and-mybmad-sidecar)

# Module-template stays an authoring tool; mybmad joins as a sidecar, never the console

## The Dream

The 2026-09-06 suite register left two members at `skip`: `bmad-module-template`
(catalog only) and `mybmad-dashboard` (launcher present, out of the platform).
The campaign now wants both **wielded** — but not the way a module or a
console is wielded.

1. **module-template is an authoring tool.** Steward already authors modules
   through `bmad-builder` beside skill-forge. The template is the scaffold that
   path consumes. It is never `steward provision --module`'d into
   `.claude/skills/`. A placeholder LICENSE is not a reason to copy it into
   the live skill tree.
2. **mybmad is an opt-in sidecar on the estate plane.** Same PostgreSQL as
   the host, **own schema** (`mybmad`). Same Keycloak/OIDC as `/console/`.
   It does not replace `/console/`. `src/platform/` must not grow a second
   login — mybmad is a client of the existing IdP, not a new password store.

## Why mybmad is not the console — estate contract (2026-09-13)

`/console/` is the django-pyforge host. mybmad is a Next.js sidecar, not that
host. Operator ruling: **use our Postgres and our auth; give mybmad its own
schema.**

- **Postgres:** the platform (or BYO) cluster. Prisma `DATABASE_URL` sets
  `schema=mybmad` (or equivalent `search_path`). Liquibase/Django stay on
  their schema. Never a second cluster as the wielded path; never Prisma
  tables in `public` next to Django.
- **Auth:** the same Keycloak/OIDC plane (`COMPONENT_OIDC_*`). No Better Auth
  email/password as the estate login. No second IdP and no new login views
  under `src/platform/`. A Keycloak client for the sidecar is configuration,
  not a second plane.
- **Not `/console/`:** no mount, no replacing Wagtail. `retired-console-check`
  stays green.

The conda launcher's local `pg_ctl` + Better Auth remains a **dev fallback**
when the estate cluster is absent — not the wielded register path.

## Kinships

- `docs/dreams/bmad-suite-lifecycle.md` / `spec-bmad-suite-lifecycle` CAP-1
  (register rows 11 and 13; 2026-09-06 skip verdict)
- `spec-bmad-suite-channel-product` (catalog, not wire-everything)
- `bmad-dashboard` row 12 (opt-in, never `/console/`)
- pap host ADs: one identity plane, `retired-console-check`

## What it looks like when real

The adoption register records row 11 as **wield (authoring tool only)** and
row 13 as **wield (sidecar on estate Postgres + OIDC, schema `mybmad`)**.
`mybmad` is not `/console/` and not a PR gate. The host **shows** it in
django-pyforge chrome (switcher / embed) after the same OIDC session, as a
surface — not station nine. Stations keep talking through `station_port`;
they do not import mybmad. `bmad-spec` re-derives the lifecycle Spec so
Non-goals name this consume contract, not a skip.

## Realization log

- **2026-09-13** — Minted Story 52.1. Operator locked the bridge: same
  PostgreSQL, schema `mybmad`; same Keycloak/OIDC; no second login in
  `src/platform/`; not `/console/`.

## 2026-09-17 — One container, eight stations (folded from unified-container)

# One container, eight stations

## The Dream

All of PyForge — the eight stations, not just their planning artifacts — eventually lives in
a single Docker/Podman container. One image, one boot, the whole Guild available: Marshal
orchestrating, Atlas surfacing intelligence, Warden gating, Mason packaging, Doctor
diagnosing, Herald proclaiming, Scribe remembering, Steward provisioning. Shipping the
factory itself as a containerized solution, not just running it from a checked-out repo.

Unifying eight stations into one deployable boundary is also a forcing function: it only
works cleanly if the stations share a coherent architecture to begin with. Today (2026-08-02)
Atlas, Herald, Mason, and Marshal were each consolidated from multiple independent
brief/PRD/architecture/Spec chains — some with genuinely different tech-stack paradigms per
satellite — down to one chain per station. That consolidation is a precursor to this Dream,
not a coincidence: a single container boundary is a much saner thing to design against eight
coherent per-station architectures than against a scattered set of independently-paradigmed
satellite chains.

## What it looks like when real

- One `docker build` / `podman build` produces an image containing all 8 stations' installed
  packages (`src/shared/packages/pyforge-*`), wired the way `marshal init`/`genesis` already
  wire a bare-metal install today.
- A single entrypoint (likely `marshal`, since it's already "one composed surface" per
  [[one-front-door]]) can reach every station's CLI surface from inside the container.
- Whatever currently assumes a full git checkout + pixi environment (loop homes, the
  detector suite, the dashboard) has a containerized equivalent — or an explicit, named
  reason it doesn't need one.

## What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured explicitly to hold the idea
until the 2026-08-02 station-consolidation work (and its Dream-coverage follow-up) is on
stable ground. Owner assigned to `steward` on the reasoning that containerized deployment is
squarely its stated domain ("the estate the factory stands on — provisioning, deployment,
credential lifecycle") — reconsider if a different station turns out to be the better fit
once this gets pressure-tested via `bmad-spec`.

## Realization log

- **2026-08-02** — Dream captured. User's framing: unifying all 8 stations into one
  container is itself a reason to unify architecture first — directly motivated by the same
  session's PRD/brief/architecture/Spec consolidation across Atlas/Herald/Mason/Marshal.

- **2026-08-10** — **Realized.** Steward Epic 7, "The one-container Guild", is **5/5 done and
  merged**, and `spec-unified-container/SPEC.md` already read `status: shipped`. The Dream's own
  frontmatter had been left at `dreamt` throughout — nobody advanced it as the chain moved,
  which is the exact rot the "no `building` state" rule exists to prevent and which had already
  bitten `pyforge-warden` and `deckcraft` on 2026-07-25. The architecture that shipped resolved
  Q1 as **one lean image**, with `pyforge-factory-full` deferred behind a named trigger ("when
  recipe builds need to run inside the container"); the ASGI stack ships as the
  `pyforge-steward[dashboard]` extra rather than a base dependency, so the container never
  carries it. Evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` (AD-1
  through AD-6) and steward's `sprint-status-ledger.yaml` Epic 7.
- **2026-09-09 (fleet readiness pass)** — **Built, not in effect** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, rows stB-B3/B4/B5/B7 / § 2.3 **C7**). Epic 7 remains 5/5 `done` and the artifacts are real (root `Containerfile`, `.dockerignore`, `scripts/container-gates`, the `pyforge-container` pixi env) — but **the image is built by nothing**: `grep -rn Containerfile .github/workflows/*.yml` matches only `src/platform/Containerfile` and the two sidecar files, `pixi.toml` contains no `docker build` / `podman build`, and the two gate tasks (`pixi.toml:556`, `:569`) appear in **no** workflow. CAP-5 is titled "the image proves itself at build time"; there is no build time. **Vessel: new steward Story 48.10** — a job or pixi task invoked by `pyforge-station-tests.yml` that builds the root `Containerfile` and runs `scripts/container-gates secrets-scan` + `container-volumes` on the result, mirroring `platform-ci.yml:305-375`, landed **before** Story 44.10 closes this repo's CI window. Two of the Spec's four open questions retire as already-decided (`uc:AD-2` one image, `ARCHITECTURE-SPINE.md:1318-1334`; baked checkout at `/pyforge` ratified, `:1291`); Q3/Q4 stay open with the named blocker that **neither Mode question is decidable until something builds the image**. Status unchanged in this pass (the batch approved the finding and the vessel, not a demotion).

## 2026-09-17 — One name, one job — reconciling three vocabularies (folded from vocabulary-one-name-one-job)

# One name, one job — reconciling three vocabularies

> **Seed Dream.** PyForge now speaks three vocabularies at once — BMAD-METHOD's upstream terms,
> our own Lexicon and the artifact statuses derived from it, and the Intelligence Hub / Frame
> vocabulary adopted 2026-09-13. They have never been compared in one pass. This Dream carries
> that comparison into the Dream tier so `bmad-spec` can derive a contract from it. Nothing below
> is an adoption decision.
>
> **Two halves.** *Which vocabulary does this word belong to* (§ What is real) and *what shape do
> we write it in* (§ The shapes). The second half was added 2026-09-14; it is the same rule
> applied to identifiers rather than to words, and it is kept here rather than split into a
> sibling Dream because a status word that is perfectly reconciled is still unreachable if the id
> carrying it cannot be parsed.

## Source

`_bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-vocabulary-three-source-reconciliation-2026-09-14.md`
— the measured three-source pass at `main` `445976e5be` (2026-09-14).

`…/research/technical-identifier-shapes-inventory-2026-09-14.md`
— the identifier-shape sweep, same head, same day; the source for § The shapes.

Every count and quotation in this Dream comes from one of those two; re-verify against them
rather than against this file's prose. **Both measured a dirty working tree** (36 modified or
untracked paths at `445976e5be`) — see the shapes research § 8 for the one place that changes a
result.

## The Dream

The Lexicon already states the rule this Dream wants to make true everywhere:

> **Every noun does exactly one job; every job has exactly one noun.**

Today that rule holds inside the Lexicon's seven nouns and nowhere else. Around them sit four
status vocabularies, of which one is declared; a word that means three different things
(`in-progress`); one job with four names (`done` / `shipped` / `realized` / `review`); and a
value that is our most-used Spec status but is upstream's canonical *illegal* value (`shipped`,
67 live Specs, reset to `backlog` by upstream's own test suite).

The Dream is that a reader — human or agent — can look at any status on any artifact in this
estate and know, without reading code, which vocabulary it belongs to, what act it asserts, and
what it obliges downstream. And that the detectors enforcing it read that vocabulary from one
declared place rather than five hard-coded sets scattered across `board.py`, `chain.py`, and
`status_body_consistency.py`.

The same rule has a second edge. *Every noun does exactly one job* is about meaning; **every
thing is written down exactly one way** is about shape, and the estate satisfies it in one place
and almost nowhere else. A story is named three times in three files and no two spellings are
derivable from each other. A deferred-work id has eleven grammars. The Dream's second half is
that an agent can find the thing it was told about — that a name, once chosen, survives the trip
between `epics.md`, the ledger, the spec folder, a branch, and a sentence of prose.

## What is real

Measured 2026-09-14, not remembered:

- **The Dream ladder is already principled and declared** (`docs/dreams/README.md:63-104`):
  *"each state names the act that completed, never the artifact that proves it"*, with the
  rejected alternatives recorded (`seeded`/`in-deck`/`in-spec`, renamed 2026-07-25) and a
  deliberate refusal of a `building` state. **This is the asset to extend, not replace.**
- **The Spec ladder has no declaration at all** — 8 values across 163 files, of which only
  `extension-point` is defined, and that in the *Dream* README.
- **Our ledger is largely upstream-conformant**, which the sprawl framing had obscured:
  `done`/`backlog`/`in-progress` are BMAD's story lattice and `optional` is BMAD's *retrospective*
  lattice applied exactly where it belongs. Only `blocked` is net-new local.
- **BMAD provides no extension point for status vocabulary**, and silently resets unrecognized
  values — the fail-open behaviour our local `STICKY_STATUSES` patch exists to defeat.
- **The Hub has six shared abstractions, not seven.** Our Charter (Tier 0, line 606), the
  Intelligence Hub Spec (lines 48, 68) and `vocabulary-map.md` all name seven by folding in
  Organizational Memory, which upstream tiers as Layer-1 infrastructure. The Charter's
  *substantive* rulings are unaffected; the enumeration is not.
- **Our nine Frames are authored against an unmerged, unlicensed draft** — `type: frame [0.3]`,
  `identifier:`, `license:` are v0.3-only fields, and `frame-spec` PR #28 (which would add both
  v0.3 and Apache-2.0) is still open.
- **The failure this prevents has already happened three times.** Two Dreams are recorded in
  `docs/dreams/README.md:90-98` as reading `dreamt` while their epics were 3/3 and 5/5 done;
  `intelligence-hub` was found the same way on 2026-09-14.
- **There is a fourth vocabulary tier nobody mapped: Design.** The 45-slide deck teaches a whole
  practice vocabulary — **four phases**, **three tracks**, parallel track, party mode, execution
  matrix, method-vs-machinery, project-context-as-constitution — and **none of it** appears in
  `vocabulary-map.md`, the Charter cross-walk, or any repo glossary. The Lexicon slide itself is
  current; everything around it was recorded in Design and never entered practice.
- **`Track` collides and nobody named it.** Hub `Track` is the durable evidence record
  (`hub:CAP-3`, Story 53.3's `track.json`); the deck's `Track` is a BMAD planning lane (Quick
  Flow / BMad Method / Enterprise). The Charter named the Cogs/Smith collision and stopped.
  `Guard`/`Gate` were never examined at all, and already carry three senses across Hub, our
  detectors/`gate_mode`, and BMAD's `PASS`/`CONCERNS`/`FAIL`.
- **The deck teaches four names BMAD retired** (`bmad-quick-dev`, `bmad-dev-auto`,
  `bmad-create-story`, `bmad-dev-story`) plus **Paige**, the Tech Writer persona retired in 6.11.
  `CLAUDE.md` records the renames correctly; the public-facing deck does not.
- **The Design→repo pull is stale again.** Local copies date to 2026-08-01 and
  `Agentic SDLC.dc.html` is **13.5 KB behind** Design. The Charter's own log (line 826) records
  the 2026-08-01 pull as the *first* one ever, made to fix exactly this drift class. It recurred.

## The shapes

The same question asked of identifiers rather than words. Measured 2026-09-14, not remembered;
every count is in `technical-identifier-shapes-inventory-2026-09-14.md`.

- **The estate proves the shape is achievable.** `^### Story \d+\.\d+: .+$` holds **952/952**
  across all eight stations — zero exceptions, one separator, no drift. The doctor finding codes
  are second: **124 distinct codes, 124 conforming to `^[a-z0-9]+(-[a-z0-9]+)*$`**. Neither is
  declared anywhere; both are simply obeyed. **These are the assets to extend, exactly as the
  Dream ladder was on the word side.**
- **One story is spelled three ways, 2760 times.** `### Story 33.9:` (dotted, Title Case) ⟷
  ledger `33-9-verify_scope-guards-marshal-factory-dispatch:` ⟷
  `spec-33-9-verify_scope-…md`. No two are mechanically derivable, **and the slugify that
  connects them is not deterministic**: of 842 stories present in both the ledger and a spec file,
  **53 carry different slugs for the same number** (atlas 19, herald 19, marshal 7). A fourth
  spelling lives in branch names, a fifth in prose.
- **The slugify is not closed over its own alphabet.** 14 of 952 ledger keys fail the shape they
  are documented to have — underscores (`33-9-verify_scope-…`), non-ASCII
  (`22-4-a-diátaxis-adapted-…`), a typographic apostrophe collapsed to `-s-`. A regex over the
  documented shape silently drops all 14.
- **`Story N.N` (11941) and `S-N.N` (2615) are both live prose**, in the same files, neither
  declared. marshal alone writes `S-` 1303 times.
- **Deferred-work ids have eleven grammars over 1338 ids** — `DW-FU-<E>-<S>-<n>` 665,
  `DW-<E>-<S>-<n>` 347, `DW-FU-<E>-<n>` 185, then eight more including bare `DW-1`…`DW-10`
  (which collide across projects by construction) and six malformed (`DW-FU`, `DW-B4-`,
  `DW-B2-1..5` — a range in an id slot). **This Dream's own sibling pass demonstrates the
  failure**: `DW-VOCAB-2026-09-14-1..7` is one sequence split across two ledger files, steward
  holding 1,2,3,4,5,7 and marshal holding 6, with nothing in the shape able to say so.
- **Long vs short station form has no rule.** LONG in project dirs (8), packages (10), pixi envs
  (13), pixi tasks (64), `dispatch/`+`loop/` branches (44); SHORT in Dream `owner:` (165/165),
  `bmad-agent-*` skills (8), all 35 `Source` enum values, 22 branch namespaces, 9 pixi tasks.
  `pyforge-scribe` is the env and package but `scribe-pg-up` is its task. **And the four short
  rosters in code disagree with each other** — three member orders, and `DREAM_STATIONS`
  (`marshal/mcp/coverage.py:30`) holds only 6 of 8, omitting doctor and scribe.
- **Frontmatter key casing is inverted between the two spec tiers, inside the same files.**
  Numbered story specs run 27 snake_case keys to 1 kebab; named `SPEC.md` runs 7 kebab to 4
  snake. Every `SPEC.md` carries `owner-dream:` and `open_questions:` side by side.
- **Commit subjects split 72/50 and punctuate in opposite directions.** Conventional-commit
  `type(scope):` never ends in a period (0 of 72); the Capitalized-sentence family almost always
  does (46 of 50). Five commits use a *station name* as the conventional-commit type.
- **Dream `title:` matches its own filename in 0 of 165 cases** — kebab slug against prose title,
  69 of them `Noun phrase — subtitle` and 96 full sentences. And **19 of 165 `status:` values
  carry a trailing `# …` comment on the same line**, so a naive parse reports 40+ statuses where
  the ladder declares 5. That is a shape defect sitting directly on top of the word-side ladder
  this Dream is otherwise trying to preserve.
- **Finding codes are clean until they carry data.** 124/124 literal codes are kebab, but six
  call sites in `sources/atlas.py` pass a feedstock or package name into `check=`, so the field
  that elsewhere carries `spec-surface` can carry a package name or the literal
  `"<unknown feedstock>"` (`atlas.py:172`).
- **The estate can already close a shape defect cleanly — but the record of it is uncommitted.**
  `DW-VOCAB-2026-09-14-5` (steward `epic-18`) and `-6` (marshal `epic-29`) report ledger rows with
  no epic heading. Both are raised, fixed and `status: closed`; a full cross-check of all eight
  projects found **214 epic keys against 214 headings, zero mismatches**, with no story orphaned.
  That is the whole loop working. **None of it is committed** — the DW entries, the two headings
  and the closures were all minted 2026-09-14 and `git show HEAD:…` returns 0 for every one of
  them, inside a 46-file changeset staged on `main`. The shape defect is solved; its durability
  is not.

## Constraints

- **The Charter is Tier 0.** Its six-vs-seven correction is an *amendment with a Realization-log
  entry*, never an edit. Its standing CAP-4 ruling — an external vocabulary is cross-walked and
  **never joins** the seven Lexicon nouns — binds this Dream too.
- **Do not rename a Lexicon noun.** The seven are constitutional.
- **Upstream BMAD terms are not ours to redefine.** Where we differ from `sprint_plan.py`'s
  lattices we either conform or record why, in the open — never silently.
- **Status is not a proxy for work remaining** (`docs/dreams/README.md:90-98`). Any proposal that
  re-introduces activity-tracking into a hand-declared status is already answered: the ledger and
  `fleet-picture` own that question.
- **No migration that rewrites history.** Memlogs are append-only; Realization logs are the
  amendment record.
- **A vocabulary change lands with its detector.** Any renamed or retired value updates the code
  that reads it in the same change, or it is not done.
- **A shape change is a mass rename, and mass renames break readers.** 1338 `DW-` ids and 952
  ledger keys are each read by detectors, ledgers, branch names and prose. Nothing here may
  propose a rename whose reader-update cost has not been measured first.
- **`### Story N.N:` and the 124 kebab finding codes are not up for redesign.** They already hold
  at 952/952 and 124/124. Any shape ruling extends them or leaves them alone.
- **Historical prose keeps its original names.** Memlogs, Realization logs and retros record what
  was written at the time; only live pointers get repointed.

## Non-goals

- Adopting Cogs / Ops as PyForge nouns — the Charter already ruled cross-walk, never join.
- Building a Frame registry, or chasing `frame-spec` v0.3 before PR #28 merges.
- Renaming `sprint-status-ledger.yaml` to upstream's `sprint-status.yaml` as an end in itself.
- Re-litigating the Dream ladder, which is declared, principled, and working.
- A vocabulary UI, linter-as-product, or anything shipped outside this estate.
- **Retro-renaming the 1338 existing `DW-` ids**, or the 53 divergent story slugs. A grammar for
  what is minted *next* is a different and much smaller question than a migration of what exists.
- **Unifying branch names.** Five of the twelve branch shapes are machine-generated by
  `bmad-loop`, `dispatch`, `attempt-preserve` and the worktree tooling; they are internal and
  short-lived. Only the human-authored namespaces are in scope at all, and possibly none of them.
- Fixing `DW-VOCAB-2026-09-14-5`/`-6` here — they have working-tree fixes already and belong to
  whoever owns that uncommitted change, not to this Dream.

## Open questions for the Spec

1. **Does the Spec ladder get declared as-is, or reduced?** Eight values exist; `absorbed`,
   `superseded` and `archived` arguably name one act (ended, by three different routes).
2. **Does `in-progress` survive on Specs?** It is the "what is happening" shape the Dream side
   deliberately rejected, and it collides with two other vocabularies.
3. **Where does the Spec ladder live?** A Spec-side README mirroring `docs/dreams/README.md`, a
   section of the Charter, or a machine-readable declaration both prose and detectors read.
4. **Do we follow Frame v0.3's `recommended, not required` + `must preserve unregistered`
   pattern?** Upstream adopted it for exactly our reason — a required enum would invalidate their
   own examples.
5. **Does a BMAD↔Lexicon cross-walk belong in the Charter** beside the Hub one, given BMAD
   supplies the terms in heaviest daily use (Epic, Story, Sprint, PRD, Retrospective)?
6. **`pitched`** — declared in `guild-roster.json`, used by nothing. Retire it or use it?
7. **Is one declared vocabulary source feasible** that `board.py`, `chain.py` and
   `status_body_consistency.py` all read, replacing five hard-coded sets?
8. **Does the Design tier's practice vocabulary join the map, or stay teaching-only?** Four
   phases, three tracks, party mode and method-vs-machinery are taught publicly and carried
   nowhere in the repo. Either they are estate vocabulary and belong in the map, or they are
   presentation scaffolding and should say so.
9. **How is the `Track` collision resolved** — rename our planning-lane sense, qualify both
   (`planning track` vs `evidence Track`), or accept the overload with a named ruling as the
   Charter did for Cogs/Smith? Same question for `Guard`/`Gate` across three senses.
10. **What keeps Design and repo from drifting a third time?** The 2026-08-01 pull was itself the
    fix for a year of drift, and the deck is 13.5 KB behind again. Is this a detector, a pull
    step in a Herald story, or an accepted manual cadence?
11. **Who owns retiring stale teaching?** The deck teaches four retired BMAD skill names and a
    retired persona. Correcting it is Herald's surface, but the vocabulary ruling is steward's.

### On shapes (added 2026-09-14)

12. **Which of the three story spellings is canonical, and do the other two derive from it?**
    The heading is the human one, the ledger key is the machine one, the spec filename is neither
    consistently. A declared slugify — applied once, at mint time, by one function — would make
    the other two derivable; 53 existing divergences say no such function is in use today.
13. **Does `DW-` get one grammar for newly minted ids?** Eleven shapes exist. The two that carry
    real information are `DW-[FU-]<E>-<S>-<n>` (story-scoped, 1197 ids) and
    `DW-<SLUG>-<date>-<n>` (sweep-scoped, ~30). The rest are neither. Note that
    `deferred_work_promote.py` is already recorded as keeping generic Tier-3 ids verbatim, so a
    grammar without a mint-time guard will not hold.
14. **Is a project qualifier part of a `DW-` id?** Bare `DW-1`…`DW-10` collide across ledgers,
    and this Dream's own `DW-VOCAB` sequence is split across two of them.
15. **Kebab or snake for frontmatter keys?** The two spec tiers answer oppositely, in the same
    files. Whichever wins, `open_questions` or `owner-dream` has to move — and both are read by
    detectors.
16. **Does `S-N.N` retire, or get declared as a legitimate short form?** 2615 uses; retiring it is
    a prose migration across every planning artifact, declaring it is one sentence.
17. **Do commit subjects get one style?** 72 conventional-commit against 50 Capitalized-sentence
    in the last 200, punctuating in opposite directions. This is the cheapest ruling available and
    the only one enforceable at the gate rather than by sweep.
18. **Does the long/short station form get a per-context rule** — long for paths and packages,
    short for code and prose, say — or is one form canonical everywhere? And separately: do the
    four `STATIONS` rosters collapse into one declared list? `DREAM_STATIONS` silently omitting
    doctor and scribe is the kind of defect a single source would have prevented.
19. **Should `docs/dreams/README.md`'s ladder forbid the trailing `# …` comment on `status:`?**
    19 of 165 Dreams carry one, which is why the ladder parses as 40+ values instead of 5. The
    word-side ladder is this Dream's protected asset; this is a shape defect sitting on top of it.
20. **Is a `check=` that carries runtime data still a finding code?** Six call sites in
    `atlas.py` say the field has two jobs. Either it has one and the data moves to `evidence`, or
    the code vocabulary is declared open and nothing downstream may enumerate it.

Answers for 1–20 were accepted 2026-09-15 and are recorded in § *Operator rulings* below.
They bind a later `bmad-spec` re-derive. They do **not** make this Dream `specified` — the
Spec is still `draft` until that re-derive lands the same answers in the contract.

## Operator rulings (accepted 2026-09-15)

Operator accepted the full recommended batch in session. Recorded here so the Dream carries
the *why*, not only a key. The test that judged every answer is the one this Dream already
had: **each state names the act that completed, never what is happening; remaining work is
the ledger.** No mass rename, no history rewrite, no Lexicon-noun change.

### Word side

1. **Declare all eight Spec values. Do not collapse `absorbed` / `superseded` / `archived`.**
   They look like one “ended” act and are not. `board.py` already treats them as different
   obligations: `shipped` still owes a story trail; `absorbed` is credited on the absorbing
   chain; `archived` / `superseded` were abandoned, not delivered; `extension-point` is a
   seam. Collapsing them would make INV-A lie. Keep `shipped` as *our* Spec-terminal. That
   it is illegal on an upstream *story* is a cross-walk footnote, not a rename of the
   ~67 live `shipped` Specs.

2. **Stop putting `in-progress` on Specs.** It is the `building` state the Dream ladder
   refused, and it collides with BMAD’s story lattice and our ledger. Live Specs already
   use it as leftover-CAP accounting (`deferred-work-visibility`; `developer-machine-bootstrap`
   still `in-progress` after Epic 17 is 2/2 `done`). A contract that exists is `ready` until
   every CAP is delivered (`shipped`) or the chain is ended. **Grandfather** today’s files —
   no mass rewrite. Detectors may keep treating the old value as open until each file is
   next edited.

3. **One machine-readable declaration detectors import; the Charter states the rule in a
   short paragraph.** The Dream README stays the Dream ladder only. The coupling
   (`specified` requires Spec `ready`; `extension-point` keeps the Dream `dreamt`) must not
   live only in `docs/dreams/README.md` while `board.py` / `chain.py` /
   `status_body_consistency.py` each keep a private set.

4. **Yes — recommended, not required, and a reader must preserve an unregistered value.**
   Frame v0.3 chose that so its own examples stayed valid. A closed enum would red ~163
   `SPEC.md` files on day one. Unknown values: preserve, warn, do not reset (the fail-open
   BMAD already does is why `STICKY_STATUSES` exists).

5. **Yes — a BMAD↔Lexicon cross-walk belongs in the Charter, same shape as the Hub walk:
   map, never join.** Epic / Story / Sprint / PRD / Retrospective are the daily nouns and
   have no walk. Record the divergences in the open: Spec `shipped` ≠ story `done` ≠ Dream
   `realized`; ledger `blocked` is ours; `optional` is BMAD’s retrospective lattice used
   where it belongs.

6. **Keep `pitched`. Do not require it. Do not backfill.** Use it when Herald has actually
   made the case (a deck exists) and the Spec is still `draft`. `guild-roster.json` already
   declares it; zero live Dreams use it. Forcing the rung would invent ceremony the
   factory does not run.

7. **Yes — one declared source for status sets.** Exit-code lattices sit in the **same
   file, a different key** — do not mash “what a Spec may say” with “what a process may
   return.” That leftover design half is `DW-VOCAB-2026-09-14-8` (docs half already in
   `CLAUDE.md`).

8. **Design practice vocabulary is teaching-only, and the deck must say so.** Do not
   import four-phases / three-tracks / party mode / execution matrix into
   `vocabulary-map.md`. Upstream 6.12 already says those phases are independent tools, not
   stages, and “three tracks” collides with *evidence Track*. **Exception:**
   method-vs-machinery and project-context-as-constitution already describe this estate —
   they belong next to the Charter, not as new Lexicon nouns.

9. **Already ruled 2026-09-14; restated.** Write **evidence Track** vs **planning track**.
   Gate has three senses; `verdict` is the narrow word. Charter amendments, not edits.

10. **Herald owns the Design→repo pull; a detector owns recurrence (etag/size).** Manual
    cadence failed twice (2026-08-01 pull; 2026-09-14 deck 13.5 KB behind). Do not accept
    “we’ll remember.” This is CAP-5 / `DW-VOCAB-2026-09-14-3`.

11. **Steward writes the vocabulary ruling; Herald changes the deck.** Same split already
    on `DW-VOCAB-2026-09-14-3`.

### Shape side

12. **Heading is human-canonical (`### Story N.N:`). Ledger key is machine-canonical.
    Spec filename is `spec-` plus that ledger key. One slugify, at mint time only.**
    Headings already hold 952/952. 53 of 842 number-pairs have divergent slugs — no
    retro-rename.

13. **New `DW-` ids only: two families.** Story-scoped and sweep-scoped (the two that
    already carry information). Ban the other nine shapes for anything minted after this
    ruling. A grammar without a mint-time guard will not hold —
    `deferred_work_promote.py` copies generic Tier-3 ids verbatim.

14. **Yes — every new `DW-` id includes the short station token.** Bare `DW-1`…`DW-10`
    collide across ledgers; this Dream’s own `DW-VOCAB` sequence split across steward and
    marshal. No retro-rename of the 1338 existing ids.

15. **Both casings stay, as context rules.** Named `SPEC.md` is kebab-led (`owner-dream`)
    with `open_questions` beside it; numbered story specs are snake-led. Do not move
    either key — detectors read both. A single “winner” is a detector break.

16. **Declare `S-N.N` as a legal short form in prose only.** The heading stays
    `### Story N.N:`. Retiring 2615 uses is a planning-prose migration with no reader
    benefit.

17. **Capitalized sentence, no trailing period, no `Co-Authored-By`.** Conventional
    `type(scope):` is allowed only under `recipes/` and the CFE changelog. This is the
    one shape a commit hook can enforce; the last-200 mix punctuates in opposite
    directions.

18. **Per-context, plus one declared roster of eight.** LONG for paths, packages, pixi
    envs; SHORT for Dream `owner:`, `Source`, and prose. Collapse the four disagreeing
    `STATIONS` lists. `DREAM_STATIONS` omitting doctor and scribe is the defect a single
    list prevents. Do not pick one form for every surface.

19. **Forbid a trailing `# …` on the same line as Dream `status:`.** Put the comment on
    the next line. 19 of 165 Dreams make a five-value ladder parse as 40+. Fix-on-touch
    or one hygiene PR; add a detector. This protects the Dream ladder this file exists
    to extend.

20. **`check=` is a finding code only. Runtime data goes in `evidence`.** Six `atlas.py`
    call sites put a feedstock or package name (or `"<unknown feedstock>"`) in the field
    that elsewhere carries `spec-surface`. That is a small code fix once the Spec is
    `ready`, not a second vocabulary.

### Deliberately not in this batch

- Renaming Spec `shipped` to `done` (fights the story lattice and ~67 files).
- Unifying branch names (most are machine-generated and short-lived).
- Retro-fixing the 53 divergent slugs or the 1338 `DW-` ids.
- Re-opening Frame v0.3 (adopted on steward Story 53.6).

## Kinships

- [[intelligence-hub]] — the Hub half of the vocabulary; its CAP-1 landed the Charter cross-walk
  this Dream corrects the enumeration of.
- [[pyforge-charter]] — Tier 0; holds the Lexicon and the cross-walk ruling.
- [[pyforge-unifying-strategy]] — the estate-wide chain these statuses report into.
- [[build-league-scorecard]] — parked on the operator's measure set; shares the "what do our
  words assert" question from the measurement side.

## Realization log

- **2026-09-14** — Seeded. Three parallel read-only passes (this repo's live vocabulary; BMAD
  v6.12.0 pristine; OpenTeams whitepaper `v9` + `frame-spec` + the guide) recorded in
  `research/technical-vocabulary-three-source-reconciliation-2026-09-14.md`. Three corrections to
  our own records came out of it: the Hub has **six** shared abstractions and our Charter names
  seven; the Guard categories are right but **Source-Grounding ranks second, not sixth**; and
  `extension-point` is **not** a category error but a documented parked-Spec state. No adoption
  decided, no Charter amendment made — `status: dreamt` until a Spec reaches `ready`.
- **2026-09-14 (later)** — Operator direction: the Design tier belongs in this research too. A
  fourth pass over Design project `f58c0f17` (`Agentic SDLC` deck + the two Lexicon posters) found
  three further things, recorded as § 5b of the research: the deck teaches a practice vocabulary
  (four phases, three tracks, parallel track, party mode, execution matrix, method-vs-machinery,
  project-context-as-constitution) that **never entered `vocabulary-map.md` or the Charter
  cross-walk**; it still names four BMAD skills retired in 6.11 plus the retired Paige persona;
  and the local pull is stale again — `Agentic SDLC.dc.html` is 13.5 KB behind Design, the same
  drift class the Charter's line-826 amendment fixed on 2026-08-01. The `Track` collision (Hub
  evidence record vs BMAD planning lane) and the unexamined `Guard`/`Gate` overload were added to
  the disagreement list; the Lexicon slide itself verified current against the Charter's seven.
- **2026-09-14 (third)** — Operator direction: keep the identifier-shape question in this Dream
  rather than minting a sibling. A fifth read-only pass over the same head measured nine naming
  surfaces (station names, epic/story addressing, spec names, Dream names, deferred-work ids,
  detector codes, pixi tasks, branches/commits, planning-artifact filenames), recorded as
  `research/technical-identifier-shapes-inventory-2026-09-14.md` and summarized in § The shapes.
  It found two things worth stating at Dream level: the estate **already holds one shape
  perfectly** (`### Story N.N:`, 952/952, and 124/124 kebab finding codes) so the goal is
  demonstrably reachable; and **one story is spelled three non-derivable ways 2760 times**, with
  53 of 842 slugs actually divergent between ledger and spec file. Open questions 12–20 added; no
  shape chosen, no rename proposed. The Spec stays `draft` and this Dream stays `dreamt` — the
  shape questions are operator decisions of exactly the kind already blocking the word side.
- **2026-09-14 (third, corrected same session)** — The entry above first recorded that
  `DW-VOCAB-2026-09-14-5`/`-6` were "fixed but still open in the ledger". **That was wrong**: both
  read `status: closed`, and the claim came from a truncated `grep` that never reached the
  `status:` line rather than from a measurement. Corrected in place here and in the research § 8.
  The accurate finding is narrower and more useful: those two are a **complete, correct loop**
  (raised → fixed → closed, 214 epic keys against 214 headings fleet-wide, no story orphaned),
  and the exposure is durability, not correctness — the whole chain, this Dream included, sits in
  a 46-file changeset **staged on `main` and uncommitted**, none of it reachable from `HEAD`.
- **2026-09-15** — Operator accepted the full recommended ruling batch (word-side Q1–11,
  shape-side Q12–20) and directed that the answers and their reasons be appended to **this
  Dream** before any Spec re-derive. Recorded in § *Operator rulings (accepted 2026-09-15)*.
  Status stays `dreamt`: a `draft` Spec still has unanswered `open_questions:` in its
  frontmatter until `bmad-spec` re-derives the contract from this file. No epic. No
  `SPEC.md` hand-edit.
- **2026-09-15 (later)** — Operator: decompose all the way to stories ready for
  marshal dispatch. `bmad-spec` re-derived `spec-vocabulary-one-name-one-job` to
  `ready` (CAP-1..8; CAP-4 already met; `open_questions: []`). This Dream flips
  `dreamt` → `specified`. Steward Epic **59** (59.1–59.7 `backlog`) is the
  dispatch home. `DEFERRED_SPECS` drops this slug.

## 2026-09-17 — They mail a dated list; we mail a dated list (folded from work-passports-dated-extracts)

# They mail a dated list; we mail a dated list

> **Seed Dream.** Operator 2026-09-14: BMAD stories, GitHub Projects, Jira, and
> Postgres as one working system — **sibling** to [[jira-github-projects-sync]],
> not a reopen of steward Epic 8. Converged in
> `_bmad-output/brainstorming/brainstorm-bmad-story-board-unity-2026-09-14/`
> (`bmad-brainstorming`, then intent). Scribe recall that day
> (`scribe recall "work passport extract corridor Jira GitHub Postgres dream"
> --mode planning`) → **no grounded answer**.

## The Dream

The internal agile team **sees every piece of work they are allowed to see**
without anyone logging into a board they are forbidden to open.

Work already lives in more than one room: **internal enterprise Jira** (Kanban
and quarterly planning), **Internal GitHub Projects** (our issues; later, BMAD
epics and stories as fridge magnets), **External GitHub Projects** (the vendor
book we are allowed to share a surface for). The vendor cannot sit in our Jira
or our GitHub. We cannot sit in their private GitHub. They **can** extract and
send a file. We **can** send a filtered extract they load into their GitHub.

The product is that **corridor** — two dated lists, a **work passport** (a UUID
we mint; Jira keys and GitHub numbers are nicknames), and the **Postgres app we
already have** as the join store. It is not a fifth Kanban. It is not a live
sync into their org.

> How might the internal agile team see every piece of work that already lives
> on internal Jira, the internal GitHub Project, and the external vendor GitHub
> Project, without anyone needing access to a board they are forbidden to open?

## What it looks like when real

- Standup cites a **waybill** ("as of drop N"), not "any updates from the vendor?"
- Testers pull a **shipped** shelf from the last inbound extract, not from a
  hunt in a private repo.
- Findings leave in a **signed outbound slice** the vendor can load — not a
  dump of our Jira, not factory BMAD work unless marked vendor-shared.
- Vendor status on the glass is **as-of** (their clock and our received clock).
  An empty on-time file is a failed drop. A late drop leaves yesterday visible
  and stale, not a blank book. Before the first waybill, the vendor pane is
  **unborn**, not empty.
- Unlinked inbound rows sit in **quarantine**. Humans link; the system does not
  guess by title.
- Security can show **no PAT** that opens their org or writes ours on their
  behalf.
- BMAD ledger stays the factory source. Internal GH cards, when they exist,
  say **projected**.

## What is real

- Mandated surfaces: internal Jira, Internal GitHub Projects for our issues,
  External GitHub Projects for vendor-facing issues, the existing Postgres
  application.
- Extract both ways is operator-confirmed (2026-09-14). The air-gap is **no
  live login**, not no data.
- [[jira-github-projects-sync]] / steward Epic 8 is **specified** and `done` on
  the ledger — bidirectional sync for an **external pair we can both see**.
  `steward sync reconcile` and the 12.8 `github_metrics` dlt load stay
  **adapters**, never this product, and must not be aimed at the vendor private
  project.
- Brainstorm memlog + intent:
  `_bmad-output/brainstorming/brainstorm-bmad-story-board-unity-2026-09-14/`.

## Constraints

- Postgres is a constraint, not a design choice for v1 storage.
- No third-party sync SaaS (Unito, Exalate).
- No live GitHub credential into the vendor private project; they load our
  extract.
- No fourth tracker in the app.
- Do not treat a daily extract as live.
- Do not fabricate vendor rows to hide holes.
- Do not flip Epic 44 `blocked` keys. A-only.

## Non-goals

- Reopening Epic 8 as "BMAD + Jira + GitHub + Postgres."
- Inventory/analytics UI in the egg (history can feed them later).
- Replacing Jira or GitHub as where people **act**.
- Foundry-product Dream on B.

## Egg, then larva

**Egg:** inbound + outbound loaders, frozen tiny schema, passport UUID,
waybill + as-of, two views on the existing app (`standup`, `shipped`),
quarantine, signed outbound slice.

**Larva (later):** live collectors for Jira and Internal GH we already own;
Internal GH as fridge; BMAD projection; Herald book; inventory on extract
history. Epic 8 only on an **allowed-pair** list **inside our walls**.

## Open questions for the Spec

Answered 2026-09-15. Recorded in § *Operator rulings* below. They bind the
Spec re-derive. The Dream is `specified` only after that Spec is `ready`.

1. **Transport** — email, share folder, or app upload?
2. **Larva trigger** — after N Drop Nights, or a date / explicit start?
3. **Missing passport after week two** — keep minting, or reject?
4. **Second vendor in v1** — operate two, or schema-ready only?
5. **Outbound signer** — named role, or implicit operator?
6. **Standup glass if the app is refused** — mailed query, or Herald slide?

## Operator rulings (accepted 2026-09-15)

Operator approved the session plan. **Egg** is this first cut. **Larva** is
later. **Waybill** = which drop and which clocks. **Passport** = the UUID we
mint. Do not treat steward Epic 8 as this product.

1. **Default transport is upload into the existing app.** Email and a shared
   folder are extra transports that drop the same file into the same loader.
   v1 does not require a mailbox parser. Tables: Spec companion
   `transports-and-vendors.md`.

2. **Larva does not start automatically.** Not after N Drop Nights. CAP-6
   and CAP-7 stay later empty slots. Live collectors start when the operator
   flips a date or an explicit "start larva" story.

3. **First two weeks (config; default 14 days): mint a passport and
   quarantine until a human links nicknames.** After that, do not mint. The
   row stays in quarantine as "no passport" until a human overrides. Never
   match by title.

4. **Schema has `vendor_id` from day one. v1 runs one vendor.** A second
   vendor is config, not a rewrite. No second standup pane until turned on.

5. **Named role: outbound signer.** A person or GitHub team on the existing
   app, recorded on the waybill. Default: the steward operator running Drop
   Night. Unsigned or over-broad files do not leave.

6. **App views `standup` and `shipped` are the product.** A mailed/export
   of the same table (CSV or markdown of the last waybill) is a plugin so
   standup can run from a file. A Herald slide is a later empty slot, not
   required for egg.

Do not flip Epic 44 `blocked` keys. Do not aim Epic 8 or `steward sync` at
the vendor private project.

## Realization log

- **2026-09-14** — Captured from operator topology + `bmad-brainstorming`
  (facilitator → ideate-for-me → converge MoSCoW). Owner **steward** (estate
  join, existing app, kinship to Epic 8). Chain Spec seeded `draft` the same
  day so dream-chain INV-1 holds; Dream stays `dreamt` until that Spec is
  `ready`.
- **2026-09-15** — Operator approved Q1–6 (upload default; email/share
  plugins; larva not auto; mint-then-reject after two weeks; one vendor
  operated, `vendor_id` ready; named outbound signer; mailed query plugin;
  Herald later). Spec `ready`. Steward Epic **61** (61.1–61.5 `backlog`)
  is the marshal dispatch home. Dream `dreamt` → `specified`.
