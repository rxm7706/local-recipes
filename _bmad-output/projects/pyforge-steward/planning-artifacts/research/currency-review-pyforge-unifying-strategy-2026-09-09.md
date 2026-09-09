title: "Currency review — pyforge-unifying-strategy (2026-09-09)"
chain: "pyforge-unifying-strategy"
created: "2026-09-09"
type: research
owner: steward
head: fe4025ea90
---

# Currency review — the Unifying Strategy chain at 2026-09-09

**Scope.** `docs/dreams/pyforge-unifying-strategy.md` (613 lines) and its chain —
`spec-pyforge-unifying-strategy/{SPEC.md, stack.md, convergence.md, resilience-invariants.md,
architecture-diagrams.md, console-parity-inventory.md}`, `spec-python-foundry-cutover/`, steward
`epics.md` / `sprint-status-ledger.yaml` — against live code at `main` `fe4025ea90`.

**Method.** Four independent read-only audits (Dream factual claims; the cutover section; chain
self-consistency and CAP-1..19 status; sibling-Dream impact), each instructed to treat the ledger as
a claim to be tested rather than as evidence. Every headline finding below was then re-verified
directly by the reviewing session. Nothing was edited; `scripts/bmad-switch` was not run.

**Trigger.** Operator request for a deep analysis of impact and changes, after 384 commits and 13
merged PRs (#1079–#1091) since the Dream's last substantive update.

## Verdict

**The code is healthy; the map is stale.** All 28 detectors pass. The eight-station roster, the
five-tier 40/40 claim, the query plane, the infra-kinds lock, the RWX media PVC, the absent
`services/` tree, `pyforge.core.client`'s URL and header contract, and the one-interpreter `3.14.*`
flip all verify exactly as written. No capability is unstarted. What has drifted is the *document
tier*: measured numbers, capability status, namespace discipline, kinship edges, and one live
operational hazard that the Dream's own instructions route the operator into.

---

## 0. URGENT — the Dream instructs a command that re-opens the cutover gate

`docs/dreams/pyforge-unifying-strategy.md:485-487` mandates, before any ledger write:

> `sprint-ledger-sync --project steward --repair-feed` … then `story-status-check`.

Running that today destroys the operator's Epic 44 gate, silently.

| Fact | Evidence |
|---|---|
| Tracked twin holds 14 stories at `blocked` | `sprint-status-ledger.yaml:152-166` |
| Tier-3 feed holds all 15 at `backlog` | `implementation-artifacts/sprint-status.yaml:141-155` (mtime Sep 7 04:49) |
| The syncer guards only `done` | `scripts/promote_sprint_status.py:91` `TERMINAL = frozenset({"done"})`, with `:88-90` stating `blocked` is "deliberately NOT guarded" |
| The generator was fixed; the syncer was not | `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py:77` `STICKY_STATUSES = {"story": frozenset({"blocked"})}` — no counterpart in the syncer |
| Merge keeps the feed's value | `promote_sprint_status.py`: the 14 rows are neither `lost` (not `done`) nor `missing` (present in the feed), so `merged = dict(incoming)` survives and is written to the twin, with `lost` then set to `[]` so the refusal is bypassed |

The three stories un-gated are the outward, irreversible ones: 44.3 creates a GitHub repository,
44.9 opens external conda-forge PRs, 44.10 archives this repo and disables its CI.

**This already happened.** Commit `be0a29b320` (2026-09-06, PR #1077) flipped the same 14 rows via
the generator; the gate stood open two days until `f527e526f0` (2026-09-08) restored it. That fix
landed in the generator only.

**One accident is currently protecting the estate.** A *bare* sync refuses, because Story 47.5 is
`done` in the twin and `blocked` in the feed and `done` is the one guarded status. The
`--repair-feed` variant the Dream mandates takes the other branch and bypasses that refusal.

**Remedy:** add a sticky set to `promote_sprint_status.py` mirroring `sprint_plan.py:77`, amend
`test_promote_sprint_status_regressions.py:55` which pins the current behaviour, reconcile the feed,
and only then leave that instruction in the Dream.

---

## 1. Findings ranked

### 1.1 The Dream breaks its own shipped constraint, unguarded

`SPEC.md:488` — **"Always:** the living Dream is ≤ 400 lines". The Dream is **613 lines**, and its
own Realization log at `:572` claims 43.1 achieved compliance. It regressed the day 43.1 landed and
grew steadily since. **No line-count detector exists**; the cutover Spec then records the overage as
by-design (`spec-python-foundry-cutover/SPEC.md:189`), so two Specs in one chain disagree about the
same rule. A HIGH red-team directive is silently regressed.

### 1.2 `open_questions: []` and "Residual: none" are false

`SPEC.md:35`, `:52`. Actually open:

- **Five red-team directives.** `DW-RT-2026-09-02-2..6` (R-18 sizing, R-19 network baseline, R-20
  secrets, R-21 observability, R-22 live streaming) are `status: open`, all dispositioned
  "Epic 45 candidate" — **a slot now occupied by eval-quality**. They are owner-less in practice.
- **Single-Spec merge.** Parked since 2026-09-01 with no story anywhere. Now urgent: `fnd:AD-18`
  re-derives every rendered Spec in foundry, so an un-merged `extends:` chain is a regeneration input.
- **Story 43.7** (`sidecar-runtime-validation-on-python-3-14`, `backlog`, added 2026-09-08) is
  unknown to the Dream, which states the cutover gate closed with 43.3–43.6 shipped.
- All nine `DW-RT-2026-09-02-*` still carry `agent judgment not applied — a re-read against live
  code is still owed`, now seven days stale.

### 1.3 The CAP namespace has collapsed at roughly 185 sites

The Dream at `:458` says the three CAP spaces are "**never collapsed**". Commit `b8b142db63`
(2026-09-08) normalised 334 cross-spine **AD** citations and never touched the **CAP** axis. Bare
`CAP-n` inside non-canopy satellites: 68 in the foundry spine, 61 in the bmad-suite spine, 9 in
secure-live-dashboards, 34 across epics 45–47. Frequently in the same line as a correctly qualified
`canopy:AD-17` or `suite:FR-2`.

**The Dream violates its own rule five times**, including `:80` "CAP-4 / Epic 35" (that is
`spec-mcp-era-isolation` CAP-4, colliding with Unifying CAP-4) and `:276`, which cited the Vault
ruling with a space-form "Foundry" prefix that resolves to nothing (the Vault ruling is
`canopy:AD-19`; `fnd:AD-19` is the Windows estate).

### 1.4 Six capabilities ship a mechanism whose named success criterion is never exercised

Every Canopy story reads `done`. Graded against each CAP's stated criterion in code:

| CAP | Gap |
|---|---|
| CAP-4 | `start`/`get` exists for 2 of 8 stations; no disconnect test, nothing multi-minute |
| CAP-7 | Board is a 5-row in-process fixture, and the test *asserts the real Vizro dashboard is not mounted* |
| CAP-11 | No eviction test at all; no HPA in the chart |
| CAP-12 | `IDP_USERINFO = None` in `base.py:215` with no production override, so revocation lands next **login**, not next request |
| CAP-14 | "Semantic" recall is a 32-dim embedding over a hardcoded 7-entry synonym map; the promised dual-write selects exactly one plugin |
| CAP-17 | Supervisor carries MCP-`start` runs only; marshal and doctor still read `~/.bmad-loops` |

CAP-10 passes literally, but BS-4 and BS-8 have zero production consumers. Eleven CAPs are shipped
and genuinely verified.

### 1.5 Three chain statements are factually false against live code

| Statement | Reality |
|---|---|
| `SPEC.md:346` and `:624` — "no `GraphStore` class exists in `pyforge-scribe`" | `graph_store.py:59` defines it, with three drivers (`graph_store_pg.py`, `graph_store_plane.py`, `graph_store_plugins.py`) |
| `resilience-invariants.md:104` — "No CloudEvents envelope exists today" | `django_pyforge/events/constants.py` ships it |
| `resilience-invariants.md:103` — "no `read_only=True` appears on any DuckDB file handle" | It appears twice and is AST-enforced |

Each currently reads as a live "not built" instruction to any agent that loads the contract.

### 1.6 The Python floor contradicts itself, and the fix does not cover the worst site

The Dream decided `3.14.*` (43.6 shipped 2026-09-03) and its own measured matrix shows `3.14.*` on
all 31 environments. Surviving `3.12.*`: `SPEC.md:73`, **`SPEC.md:315` (under Constraints, marked
"Always:")**, `stack.md:18`, `stack.md:33`, `convergence.md:32`. Story 44.2's scope names only
`stack.md` and `convergence.md`, so **the two SPEC occurrences are unowned** — and 44.2 is `blocked`.

### 1.7 `stack.md`'s blocking-feedstock table is entirely obsolete and inverted

All six rows shipped in `ed41099205` on 2026-08-25, the day *before* the file's own `updated:` stamp;
its closing prose caught up while the table did not, so the file asserts and denies the same fact.
`pixi.toml:230-246` now reads "Do not author recipes here".

The `cachebox` row's premise is also wrong — conda-forge ships 5.2.3, pinned at `pixi.toml:240` and
`:456`. Consequence: `SPEC.md:29`'s surface glob **`recipes/cachebox/**` points at a directory that
does not exist**.

Other stale rows: `boring-semantic-layer` stated `>=0.3.18` against live pins of `>=0.2.0`
(`pixi.toml:1667`, `:2143`, "conda-forge tops out at 0.2.0"); `duckdb-server` "not in pixi.toml"
though it is at `:2159`; `mcp` 2.0.0 against live `>=2.1.1`; Django `>=5.2.15` against live
`>=5.2.17` (bumped 2026-08-29, closing the risk paragraph above it).

### 1.8 The High-Leverage matrix is half aspirational, and three rows name the wrong station

Of ten numbered bindings: three implemented, two partial, five aspirational.

| Claim | Reality |
|---|---|
| `openlineage-python` → marshal & steward | Zero hits in either tree. The real, dormant integration is in **atlas** |
| `pandera` → warden | Zero in warden. Real usage is **atlas**, validating dataframes, not SBOMs |
| `graphviz2drawio` → herald | Zero in herald. Only use is an atlas *prototype* script |
| `taplo` + `sqlfluff` → warden/doctor | **Zero hits in any `.py` file in the repo.** Doctor's own retro already records it as "bound but not yet built — no story exists" |
| `filelock` → marshal | Not a marshal dependency; marshal uses stdlib `fcntl.flock`, and not on worktrees |

The two BSL metrics the Dream names as shipped — `package_download_velocity` and
`ecosystem_cve_risk_score` — **exist nowhere in the repo but this Dream and `stack.md`**. The nearest
shipped measures are `downloads_total` / `downloads_30d`, a sum rather than a velocity.

### 1.9 Epic 47 hard-gates Phase 0 and the Dream does not know it

`epics.md:2884` — "Story 44.3 is not flipped while any P line is red (AD-8)". Of the P1–P18
readiness lines in `spec-bmad-suite-lifecycle/cutover-readiness.md`: **P2** is this Spec's own
never-re-derive exception, state "exception live"; **P7** is "violated"; **P16** readiness
"undefined". Stories 47.3 and 47.5 additionally write into Epic 44's own surface globs and `Deps:`
lines. The Dream's authoritative Order line at `:483-488` names none of it, and the kinship is
one-way — `bmad-suite-lifecycle.md:188` names this chain; the Dream's Kinships names neither it nor
`bmad-eval-quality`.

### 1.10 The Kinships line is structurally broken

Last substantively edited 2026-08-24, 379 commits ago. Three wikilinks point at documents that do
not exist as Dreams: `[[presentation-deck]]` (a legacy Tier-1 spec), `[[pyforge-operation]]` (a
sibling-repo file, never minted here), `[[pyforge-scorecard]]` (wrong slug for
`build-league-scorecard`). Plus a dangling "§6 above" cross-reference removed by 43.1, a stale
`CAP-1..CAP-13` for marshal-token-economy (now CAP-1..17), and one factually wrong description
(`atlas-query-dashboards` called a "Vizro board" when it proposes Panel/Bokeh and mentions neither
Vizro nor BSL).

**Nine missing edges**, including **`[[python-agent-platform]]` — the parent this Spec `extends`** —
and `[[intelligence-hub]]`, `[[bmad-suite-lifecycle]]`, `[[build-league-scorecard]]`,
`[[chain-currency-sweep]]`. No detector validates Kinship wikilinks.

### 1.11 A live sibling proposes amending this Dream's Constraints, invisibly

`docs/dreams/intelligence-hub.md` (updated 2026-09-09) § *How alignment with the Unifying Strategy
would proceed* proposes a `nebariapp.yaml` template in the Foundry Helm chart, a NIC profile beside
the OCP profile, a **fourth `hub:` CAP prefix on a Spec that would `extends:` this one**, a
`bmad-correct-course`-minted Constraints block, and a Grounding bullet. Every collision is named and
acknowledged; nothing is chosen; realization footprint is zero. But the Unifying Dream mentions
`intelligence-hub` **zero times** while intelligence-hub names it three.

Related, and already executed ahead of the Dream: `recipes/nebari-infrastructure-core` (0.14.0) and
`recipes/nebari-frames` (0.1.7) landed 2026-09-07.

### 1.12 Measured claims have drifted

| Dream claim | Live | Note |
|---|---|---|
| pixi matrix `lock-sha256=9a48b37aad6d1627` | `224e8484adcb9ac9` | 4 lock commits behind; 7 of 31 rows changed (`pyforge-marshal` −18, `platform-ci-test` −12). Python and platforms unchanged. Detector `pixi-env-matrix-stale` is firing |
| "7,855 recipe dirs" | 7,873 | Story 44.8 asserts this as a ceiling; it would fail as written |
| "268 registered worktrees, 85 GB" | 10 worktrees, 8.0K | Swept 2026-09-05; Story 44.10's clause describes an already-satisfied condition |
| `fnd:CAP-1..7` | `fnd:CAP-1..10` | Contradicted in three places including the cutover Spec's own frontmatter versus its body |

### 1.13 Smaller, confirmed

- **DB-GPT is not an ASGI mount and its state does not land in `dbgpt_schema`.** The Dream says both
  at `:18-19`; `config/asgi.py:69-70` says "never an ASGI mount" with a fail-loud guard, and the
  Dream's own table at `:48` says "Pattern B today" — an internal contradiction three lines apart.
- **`compliance_face/` is described as a husk; it is deleted** from git entirely.
- **The `pyforge.*` import rule is stated absolutely and violated on both sides** — the host imports
  `pyforge.steward.{keys,sync}` at 8 sites under `src/platform/ingest/github_projects/`, deliberately
  outside the import-linter's `root_packages`; and `django-atlas`'s portal imports
  `pyforge.steward.dashboard.*` directly under a test allow-list.
- **"Zero domain models on portals" is knowingly wrong** — `django_warden_fabric/models.py:11`
  `ComplianceJob` has 10 fields and its own migrations. The correction is R-25, scheduled into the
  `blocked` Story 44.2.
- **Sixteen of eighteen "living names" bind to nothing** greppable; only `python-agent-platform` is a
  real pixi feature, and `factory/` is not a directory.
- **The regeneration command printed inside the matrix block is broken** — `--update <path>` fails
  argparse; only the Grounding's `--update --dream <path>` form works, and the bad string is
  hardcoded in `scripts/pixi_env_matrix.py::render_markdown`, so every regeneration re-stamps it.
- **Product-noun drift** — the Dream retires "Agent Canopy"/"the Canopy" at `:35`; the Spec still
  uses them as live terms at `SPEC.md:256`, `:397`, `:505`. The `canopy:` id prefix is correct and stays.
- **MinIO named in two atlas artifacts** as deferred/open requirements against `stack.md:76`'s
  "Never: a fourth backing service". Deferred, not active, but unacknowledged.
- **A second Lane-3 runtime ships unnamed** — `pyforge/atlas/views/` is a live Bokeh WebSocket
  runtime beside the Vizro dashboard. "Bokeh" and "Panel" appear zero times in the Dream or Spec.

---

## 2. What is confirmed healthy

Recorded so the correction pass does not disturb it. All verified live:

- The eight-station roster, no ninth, and the five-tier check measured **40/40** with `failures=()`,
  gated in CI.
- The query plane end to end: read-only `ATTACH`, named Kedro pipeline writing the Parquet cache,
  `vss`/HNSW, and an AST-enforced ban on a second writable engine or an agent OLTP DSN.
- Infra kinds exactly PostgreSQL + Redis + Kubernetes across all 28 chart templates; no MinIO in the
  chart; media on an RWX PVC; no `services/` tree; no `:800x` farm.
- `pyforge.core.client`'s prefix, `X-PyForge-API-Version` header and Bearer assertion match the Dream
  character for character, and the in-process station port has a no-loopback test.
- Both red-team CRITICALs are fixed in shipped code: verified IdP bearer before mint, and a durable
  bounded broker whose chart render hard-fails unless `maxmemory` is below the memory limit.
- The one-interpreter `3.14.*` flip holds on all 31 environments.
- 28 of 28 detectors pass.

## 3. Recommended landing

Precedent is the 2026-09-02 red-team review in this directory, which fed `bmad-correct-course` and
minted Epics 40–43.

1. **Fix the syncer first** (§0). It is a live hazard on irreversible operations and is independent
   of every other finding.
2. **Documentation-only corrections now**, since they are factual drift rather than design changes:
   the Python floor at all five sites, the three false statements, the obsolete feedstock table, the
   measured numbers, the Kinships line, the broken regeneration command.
3. **`bmad-correct-course` on `spec-pyforge-unifying-strategy`** for what is genuinely contractual: a
   dated Residual block replacing `open_questions: []`, the CAP-namespace pass on the CAP axis, the
   Epic 47 gate inserted ahead of "operator flips 44.3", and a realized-versus-verified column on the
   capability list.
4. **Re-archive to satisfy the ≤400-line constraint**, or amend the constraint deliberately. Do not
   leave two Specs disagreeing.
5. **Mint the Single-Spec merge story** before the cutover's regeneration drill consumes an un-merged
   `extends:` chain.

Nothing in this review is a decision. It is evidence for the correct-course that follows.
