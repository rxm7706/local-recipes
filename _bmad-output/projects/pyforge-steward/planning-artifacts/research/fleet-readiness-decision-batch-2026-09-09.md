---
title: "Fleet readiness — consolidated decision batch (2026-09-09)"
chain: "pyforge-unifying-strategy"
created: "2026-09-09"
type: research
owner: steward
head: fe4025ea90
status: approved   # operator 2026-09-09, all eight questions answered as recommended
---

# Fleet readiness — the Dream-to-Code chain across all 96 live Dreams, at 2026-09-09

**Scope.** Every live Dream (`status != archived`) in `docs/dreams/`, its Spec (`owner-dream:` /
`covers-dreams:` join), its epics and ledger keys, graded against live code at `main` `fe4025ea90`
under the **realization gate** (Unifying Dream § *Where next*): a capability is `realized` when its
named success criterion is exercised in the running estate, not when its story merges.

**Operator rulings that framed the pass (AskUserQuestion, 2026-09-09).** Scope = everything live.
Greenfield spine = the python-foundry cutover (`fnd:`, steward Epic 44) plus the Intelligence Hub
alignment (`hub:`, `spec-intelligence-hub`); every Dream states its placement (`now` /
`foundry-side` / `hub:` / `unaffected`). Shape questions: Claude proposes, the operator approves.
Cadence: parallel read-only analysis → **this one decision batch** → apply per station, sequentially.

**Method.** Eight read-only agents on one shared rubric, split atlas+warden / doctor /
herald+scribe+guild / marshal A (15 Dreams) / marshal B (14) / mason / steward A (14) / steward B (13).
Each produced Table A (per Dream), Table B (operator decisions), Section C (old→new edits, not
applied), D (ranked findings), E (cross-station hits). Nothing was edited by any agent; no agent ran
`bmad-switch` or any `sprint-ledger-sync`. The reviewing session then re-verified every headline
claim carried into § 2 directly against code (list in § 6). The per-station reports are
session-scoped scratch; **this file is the record.**

**Inventory (frontmatter join, comment-stripped).** 131 Dream files, 35 archived, **96 live**
(37 `realized`, 52 `specified`, 6 `dreamt`, 1 `pitched`). Fleet ledgers: 775 stories, 737 `done`,
38 open, 16 `blocked`. Hard gaps at start: 12 (6 `draft` Specs, 1 `pitched`, 5 status-less).
Soft gaps: 30 (Spec `ready`/`in-progress` with `open_questions > 0`).

**Corrections to the rubric the pass surfaced (all verified).**
- Specs with **no `status:` line** number **8**, not 6: doctor ×4 (`spec-backlog-intake-check`,
  `spec-deferred-work-resolution-sweep`, `spec-fleet-hygiene-verification-exemplar-program`,
  `spec-pixi-candidate-currency`), marshal ×3 (`spec-marshal-land-cross-project-story-key-collision`,
  `spec-marshal-status-harness-run-id-poisoning`, `spec-pyforge-marshal`), mason ×1 (`spec-pyforge-mason`).
  `spec-pyforge-steward` / `spec-pyforge-charter` / `spec-pyforge-scribe` carry both `id:` and `status:`.
- doctor's `DEFERRED_SPECS` (`board.py:87-135`) holds **7** entries, not 6; **3 are inert** (named
  Spec not in `OPEN_SPEC_STATUSES`): `spec-agentic-sdlc-autonomy` (`pitched`),
  `spec-artifact-chain-reconciliation` (`shipped`), and `spec-chain-currency-sweep` (live only because
  its own status is stale). The `spec-intelligence-hub` entry is live but its rationale is factually
  wrong (says NIC is absent; `recipes/nebari-infrastructure-core` landed 2026-09-07).
- The inventory's per-Spec `oq` counts under-counted wherever questions live in the body or in a
  memlog rather than frontmatter (steward-A: 14 claimed vs 22 real; scribe 1 vs 4; charter 0 vs 1).

## 0. Operator rulings (AskUserQuestion, 2026-09-09 — the approval of record)

| Question | Ruling |
|---|---|
| Class A + Class B blocks | **Approve both blocks** |
| C1 retire `pyforge/atlas/views/` · C2 close the CFE rebuild at slices 1–2, delete-on-cutover · C3 absorb + archive `django-accelerator-framework` | **All three as recommended** |
| C4 Intelligence Hub bundle (nine answers) | **Approve bundle; flip `spec-intelligence-hub` `draft → ready`** |
| C6 widen Epic 49 to the twelve station satellites | **Yes — effect stories on each owning station's epics; steward Epic 49 keeps an index row per station** |
| C7 Epic 48 additions (48.1/48.2/48.8 amended; new 48.9 OIDC, 48.10 root Containerfile CI, 48.11 warden path dep) | **Mint all as listed** |
| C5 CAP-17 seam | **`spec-marshal-token-economy` CAP-18 via the Epic 33 correct-course, one publisher with CAP-7; risk-tiered wiring story in Epic 33** |
| C8 doctor rulings incl. the 49.2 relay | **Approve all, including the relay to a new doctor Dream + Spec** |
| C9–C17 station bundles | **Approve all** (incl. C14: fund one green `ocp-portability-smoke` run before 44.10) |

Every row in § 2 is therefore approved as written; § 4 is the apply order.

## 1. Verdict

**The fleet is built; it is not switched on.** Doctor and scribe are the healthiest stations
(92/93 and 19/19 `done`, code real). Across the other six, the pass found **eighteen** capabilities
of the marshal-token-economy shape — a `done` epic whose named success criterion has never been
exercised in the running estate — and only six of them (the Unifying CAPs) had a vessel before
today (Epic 49). Nine open questions across five `shipped`/`realized` steward Specs were answered
in code and never retired. Four Dream bodies and two Specs contradict their own `status:`. The
document tier drifts faster than any detector polices.

The largest single decisions are three retire/stop calls (§ 2.3 C1–C3), the Intelligence Hub bundle
(§ 2.3 C4), and whether Epic 49's realization gate widens from the Unifying CAPs to the station
satellites (§ 2.3 C6).

## 2. The decision batch

Row ids are `<report>-B<n>` so a decision can be traced to its evidence. Every row carries the
recommendation, the evidence pointer, and the alternative the recommending agent rejected.

### 2.1 Class A — close as decided or stale (approve as one block)

These are declared `open_questions` that live code or a later artifact has already answered.
Each closes by memlog → `bmad-spec` update on the owning Spec (steward-A rows also delete the
question and leave a dated `# Answered` comment).

| id | Spec | Decision | Evidence |
|---|---|---|---|
| stA-B2 | `spec-bmad-suite-channel-product` | CAP-2 scheduling stays **manual-on-signal**; close. | doctor 20.1 `done`; watched set roster-derived (`bmad_method.py:411-449`); two governed refreshes ran on the manual path. |
| stA-B3 | `spec-bmad-suite-lifecycle` | `tea-test-review --min-score 80` **stands**; residue becomes "record the next ten PRs' scores", not a decision. | `pixi.toml:884` ships 80; 46.3 `done`; task "never joins detectors". |
| stA-B1 | `spec-bmad-eval-quality` (+ dup on `spec-bmad-suite-lifecycle`) | CAP-2 trial cost → **local ledger under `evals/`** now; fold into 44.15 metering only if it ships. **De-duplicate**: delete the lifecycle copy. | `driver.py:198` already reads `total_cost_usd`; 44.15 is `blocked`. |
| stA-C6 | `spec-bmad-module-provisioning` | Retire all 3 questions as answered in code. | `_SUPPORTED_MODULES` = 5; `provision.py:71` derive-don't-declare; `--module skf` refused. |
| stA-C7 | `spec-bmad-suite-metapackage` | Retire both questions (CalVer; bmad-method conda-forge-canonical). Add assumption: lock still resolves `2026.9.5` vs recipe `2026.9.9`. | `recipes/bmad-suite/recipe.yaml:14`; `pixi.lock:17510`. |
| stA-C9 | `spec-bmad-method-core-upgrade` | Retire both questions (ambient drift → doctor 20.1 shipped; `[modules.skf]` answers → neither, installer regenerates; CAP-7 snapshot/restore is what preserves them). | `failure-modes.md:26` trap 14; `_bmad/config.toml:24`. |
| stA-B10 | `spec-intelligence-hub` OQ5 | **Stale as written** — both recipes landed 2026-09-07. Rewrite as "when do NIC/nebari-frames go to conda-forge?" → **not now** (NIC self-describes "very unstable"; nothing consumes either; external PR needs an explicit ask). | `recipes/nebari-infrastructure-core/recipe.yaml:5`, `recipes/nebari-frames/recipe.yaml:5`. |
| atlas-B3 | `spec-artifactory-download-intelligence` | Excel governance rendering → **decline permanently**, record as Non-goal. | atlas 23.8/23.9 `done`; `test_quartet_no_xlsx_surface.py` asserts zero workbook surface. |
| atlas-B2 | `spec-atlas-query-dashboards` | Session-bridging question dies with C1 (retire) or gains the trigger "first `views/` route mounted behind an authenticated host". | `test_host_board_row_isolation.py:26` already forbids mounting analytics on the identity host. |
| mars-A-B3 | `spec-artifact-chain-reconciliation` OQ-1 | Sampling failure on a shipped station → **coverage-debt row, never a ledger reopen**. | reopen re-arms the dispatch picker (`feedback_merged_story_with_backlog_ledger_row_respawns_forever`). |
| mars-A-E4 | `spec-artifact-chain-reconciliation` OQ-2 | Standing practice → **answered by `chain-currency-sweep`**; mark STALE, point there. | one-shot outgrown ~2× (61→131 Dreams). |
| mars-A-B10 | `spec-dashboard-velocity-captures-hand-driven-work` OQ-4 | HALT duration stamp → **NO, moot**: `marshal factory dispatch` journals per-session timing at source. | four live `journal.jsonl` runs read. |
| mars-B-OQ1/2/5 | `spec-marshal-single-story-dispatch` | OQ-1 verb = `factory dispatch` (branch grammar is a shared-spine constant); OQ-2 profile-driven, shipped — **add a Constraint naming the fork prohibition**; OQ-5 shipped as a sibling supervisor (two writers → why CAP-17 needs one publisher). | `landing_evidence.py:50`; `core/harness_profile.py`; `dispatch_supervisor/__main__.py`. |
| mars-B-B12 | `spec-marshal-single-story-dispatch` OQ-4 | Disjointness = **declared surfaces only** (shipped); record that within-station fan-out is impossible until story specs declare `surface:`. | `cli/dispatch.py:868`; `dispatch_fleet.py:770-790`; CAP-16 auto-derivation `gate.py:348-423`. |
| mars-B-B5/B6 | `spec-marshal-parallel-dispatch-fanout` oq1/oq2 | Keep **fixed integer** cap; keep **live intersection** (declaration, not cost, is the bottleneck). | no measured baseline exists (token economy § Gates bypassed). |
| mars-B-B8 | `spec-marshal-verify-fail-terminalization` oq2 | Keep v1: patch left at `failed/<story>/changes.patch`, **never auto-applied**. | fleet escalation policy (preserve-then-restore). |
| mars-B-B14 | `spec-landing-evidence-grammar` | Accept the green; record "708 of 898 unchecked" in the success signal; no coverage story. | hedge is by design (Dream Constraints). |
| mason-B2 | `spec-conda-forge-expert-rebuild` OQ2 | **NO** — Skill Forge compiles the knowledge layer; code is mirrored byte-for-byte (sha256-identical both slices). Record as resolution. | `campaign-state.yaml:524-527`, `:638-642`. |
| mason-B4 | `spec-conda-forge-expert-rebuild` OQ5 | Rule-2 retros edit the **legacy skill only**; slices re-ported byte-for-byte + `brief_mirrored_through` advanced in the same PR. **Move to Constraints.** | v8.88.1 CHANGELOG; `9b92661d4d` → `4b04cce30e`. |
| stB-B3/B4 | `spec-unified-container` | Q1 one image (`uc:AD-2`) and Q2 baked checkout — **both decided by the spine**; retire from `open_questions`. | `ARCHITECTURE-SPINE.md:1291`, `:1318-1334`. |
| stB-B2(a) | `spec-ocp-as-a-portability-profile` | Runner class **already chosen**: `ubuntu-latest` + CRC action (`platform-ci.yml:1251`). The half that remains is § 2.3 C14. | — |
| scribe-B1 | `spec-pyforge-scribe` body Q3 | Keep Scribe's own `--type` vocabulary; **no ADR numbering** (breaks AD-3 byte-parity, CAP-1's criterion); reading target-repo `docs/adr/` → deferred-work entry. | `capture.py` type enum; Charter Lexicon §2. |
| guild-B1 | `spec-pyforge-charter` memlog `(open)` 2026-07-31 | **Keep `owner: guild`**; close and record the reason in §5 (`guild` names the absence of a station, a job no other value does). Surface the question into frontmatter first, then close it. | four hardcoded sites incl. `chain.py:96`. |
| herald-OQs | herald Specs (3 of 4 OQs) | Answerable from shipped code per the herald report § D (F-8/F-9); close as recorded there. | — |

### 2.2 Class B — status corrections (approve as one block)

Dream statuses follow `docs/dreams/README.md:71` (`specified` requires a Spec at `ready`+;
`realized` now means the criterion is exercised). Spec statuses follow the realization gate.

| id | Artifact | current → proposed | Why |
|---|---|---|---|
| stA | `bmad-eval-quality` Dream / Spec | `specified` → **`realized`**; Spec `shipped` retexted for tag `1.4.1` (D4: the Spec still contracts `--version` = `0.2.0` and a commit pin; the shipped recipe fails its own Spec read literally). | `recipes/bmad-eval-quality/recipe.yaml:5,12,35`; `pixi.toml:1611`. |
| stA | `spec-bmad-suite-lifecycle` | `ready` → **`in-progress`** (Epic 46 9/10, Epic 47 5/5, all eight relays `done`). | ledger. |
| stA | `spec-developer-machine-bootstrap` | `ready` → **`in-progress`**: Epic 17 `done`, verbs live, but the Spec's own success signal (a recorded clean-container run) never ran; story spec is a 54-line husk. | `steward/cli.py:51-54`. |
| stA | `spec-bmad-method-core-upgrade` | keep `in-progress`, **restate the reason** — the 6.12 apply *did* happen (`4fa185be56`) but minted traps 12–15; flip on the next release's zero-recovery apply. | `failure-modes.md:26`. |
| stA | `enterprise-multi-agent-orchestration` Dream | keep `realized`; mark the Traefik/Compose § *What it looks like when real* + two constraints **SUPERSEDED 2026-08-14** (zero Traefik anywhere; edge = chart `ingress.yaml` + OCP `route.yaml`). | `src/platform/deploy/**`. |
| stA | `enterprise-airgap` Dream | close the "Known health issue" — the `JFROG_API_KEY` leak is fixed and regression-tested; CAP-3's mirror run remains unexercised (`foundry-side`). | `_http.py:508` host-gated + 5 test files. |
| stA | `asgi-multiplexer-monolith` Dream | keep `realized`; log the one unexercised criterion (thread-pool sizing; no `ANYIO_MAX_THREADS` anywhere in `src/platform/`) → clause on 48.2 (§ 2.3 C7). | — |
| atlas-B4 | `enterprise-data-models-and-apis` Dream | `specified` → **`dreamt`**; Spec stays `extension-point`, and README names `extension-point` as a parked state that does **not** satisfy `specified`. | Spec § What is real = "Nothing". |
| atlas-B5 | `atlas-kedro-catalog-expansion` | Spec `ready` → **`shipped`** now; Dream stays `specified` until one recorded run materializes `identity_complete_export` + `enterprise_jfrog_consumption` (declared datasets are contracts, not data). | `catalog.yml:987-989`, `:1301-1303`. |
| mars-A | five marshal Specs sitting `ready`/`draft` on 100 %-done epics | flip per the marshal-A report Table A (stale-low). | ledger + code. |
| mars-B | nine marshal Specs stale-low | flip per the marshal-B report Table A; **`risk-tiered-review-depth` moves DOWN** (`shipped`→`in-progress`, Dream `realized`→`specified`): zero callers outside `tests/unit/test_gate.py`. | `core/gate.py:724,768`. |
| mars-B-B13 | `spec-pyforge-marshal` | add **`status: shipped`** + a dated disposition pass over the `BLOCKED-ON` F-1..F-6 / Q-11..Q-16 block, hoisted into a real `open_questions:` key. | body says the block is "unresolved"; detectors see zero questions. |
| mars-A-B2 | `spec-agentic-sdlc-autonomy` | `pitched` → **`ready`**, keep the `DEFERRED_SPECS` entry (makes the exemption live; `pitched` is Dream vocabulary and is invisible to `board.py:716`). Fleet ruling: `pitched` is not a Spec status. | `board.py:77`. |
| doctor-B2 | `spec-chain-currency-sweep` | `ready` → **`shipped`**; delete its `DEFERRED_SPECS` entry in the same change. CAP-6 narrowed per doctor-B3 (one-line Worked-Example entry per run, enforced in the runbook's Land step). | four sweeps recorded in `prd.md:6`. |
| doctor-B4 | `spec-sibling-dreams-drift` / Dream | Spec `ready` → **`in-progress`**; Dream stays `specified` (16.1 `done` but the detector cannot fire: keyed on title, sibling shares 8 filenames and 0 titles). | `sibling_dreams.py:118,155`. |
| doctor-B7 | `spec-deferred-work-resolution-sweep` | add **`status: in-progress`** + CAP-9 "intake refuses/flags an entry citing no resolvable `location:`" (144 of 183 never-verified entries have none). | `sweep-tooling-effectiveness-2026-09-08.md`. |
| doctor-B6 | `spec-pixi-candidate-currency` | add **`status: ready`**; one doctor story for CAP-4 (the staleness check — 5/5 CAPs uncovered today); CAP-1/2/3/5 reworded as satisfied by the Dream's ledgers. | `pixi.toml` 62 commented dep lines vs 64 audited. |
| doctor | `spec-backlog-intake-check`, `spec-fleet-hygiene-verification-exemplar-program` | add the `status:` their decomposition implies (`shipped`). | 0 uncovered CAPs each. |
| mason | `spec-pyforge-mason` | add **`status: shipped`** (7/7 CAPs uncovered only because chain-completeness never saw it). | — |
| mason-B5 | `pyforge-mason` Dream | keep `realized` **with a dated caveat** naming two gaps: `mason doctor` reports `unavailable_verbs: ('recipe',)` because `[feature.pyforge-mason.dependencies]` lacks `truststore` + `conda-forge-metadata` (`cfe.py:180-186` floor), and nothing in the estate invokes `mason recipe|package|environment`. | `pixi.toml:281-283`. |
| mason-B6 | `django-accelerator-framework` | see § 2.3 C3 (absorb + archive resolves mason's only status-vocabulary violation). | — |
| herald | `herald-moments-2-4-live-backend` Spec | `ready` → **`in-progress`**; LB-2/LB-3 `foundry-side` (§ 2.3 C12). | — |
| herald/scribe | four Dream/Spec bodies contradicting their own `status:` (herald Dream+Spec, scribe Dream+Spec "3 of 9 stories" under `realized`/`shipped`) | re-ground the bodies; status unchanged. | § 2.4 D1 for the missing detector. |
| stB | four steward Dreams whose Realization logs stopped while their epics completed (`local-ocp-hybrid-environment`, `ocp-as-a-portability-profile`, `multi-repo-workspaces`, `platform-fifteen-factors`) + `python-agent-platform` ("no `src/platform/` tree") | append dated entries; status unchanged. | `platform-ci.yml:1243` etc. |
| stA | `cutover-readiness.md` P1/P2/P3/P7/P13 + § G rows G4/G7/G11 | re-derive per the steward-A report § C5 (P3 **NOT satisfied — 8 of 9 spines have a memlog**, warden's does not; P7 pool 11; P13 4 of 11 ungoverned). | verified this session. |
| stA-D8 | steward ledger `epic-44..49: backlog` while their stories are `done` | epic rollup defect (also atlas `epic-24`, warden `epic-11`) → folded into 48.1 (§ 2.3 C7). | `sprint-status-ledger.yaml:305-360`. |

### 2.3 Class C — structural decisions (each needs its own yes)

**C1 — atlas: retire `pyforge/atlas/views/` (atlas-B1).** Epic 14 shipped a second Lane-3 runtime
(CAP-1..4, 4/4 `done`) that nothing reaches: no CLI verb, pixi task, ASGI mount or portal imports it
(verified: only `tests/unit/views/*`). It reads the legacy SQLite store through a dynamic-import
bridge whose own docstring says the DuckDB-singularity gate "stays green even though the loaded
script itself imports `sqlite3`" (`cli_bridge.py:11-17`) — a declared evasion of CAP-19 ("no private
DuckDB") and of `spec-pyforge-atlas`'s own Non-goal. The live Vizro board renders 31 pages over BSL.
**Recommend RETIRE**: delete the package + tests, record the supersession on the Spec, keep the
widget-registry idea only if a Vizro page wants it. *Alternative:* mount it (`pyforge atlas views
serve`) with a declared, recorded exemption — institutionalises a second engine against a Never.
**Consequence for steward:** the Unifying Dream's Kinships line (`:669`) currently asserts this as
"a second, shipped Lane-3 runtime" — false under the gate; replace with the retirement.

**C2 — mason: stop the CFE rebuild at slices 1–2 (mason-B1) + delete-on-cutover (mason-B3).**
OQ3 asked whether full scope survives the first slice's measured cost. The cost is recurring: every
CFE release is a byte-re-port into two mirrors (23 qualifying retro commits in range; both re-scope
gates returned `adjust`, never `go`); zero callers have flipped (`campaign.callers` empty, both
slices `compiled`); slice 3 is 12.3× slice 1 and atlas-owned; and OQ2's answer (Class A) removes the
upside — Forge compiles briefs, the code is copied. **Recommend: declare the endgame over slices
1–2, cut callers over or retire the mirrors, close the campaign.** Long tail: **delete-on-cutover,
no stubs** (Mason reaches CFE by filesystem path, not import — a stub cannot serve a path resolver;
44.10 archives the repo anyway). *Alternative:* brief slice 4 as one more datapoint. **[Rule 1]:**
executing either edits `.claude/skills/conda-forge-expert/**` → `conda-forge-expert` skill invoked.
**Sequencing hit (mason-E2):** S-44.6 moves the CFE cell to `skills/domain/`; the campaign's
surface and slice map are written against `.claude/skills/…` — closing the campaign first makes
44.6 tractable.

**C3 — mason→steward: absorb `django-accelerator-framework` into `spec-python-agent-platform`,
then archive (mason-B6).** The CAP-2 trigger ("a third/fourth Django surface repeats the copy by
hand") was falsified: the estate reached nine Django faces and factored `PortalConfig` instead
(`django-pyforge`; eight portals with ~10 declarative fields; one `manage.py`). The Dream names
itself "genuinely unclaimed"; mason has no epic for it; its `surface:` dual-governs
`src/platform/deploy/DR.md` with a steward Spec (live `drift-presumed` under both); CAP-1's evidence
is already stale in the mason copy (`urls.py:26` vs live `:98`); and `specified` + `draft` is mason's
only README:71 violation. **Recommend absorb + archive (`archived-reason: absorbed`).**
*Alternative:* answer "repo-wide", promote to `ready`, re-home `owner:` to steward.
Note: 48.8 supersedes `spec-python-agent-platform` itself — absorb into the Unifying Spec's
Lane-2 section rather than into a Spec about to be superseded, or sequence after 48.8.

**C4 — the Intelligence Hub bundle (stA-B6..B11 + the three Dream questions + guild-E3).**
Nine answers, one approval; the Spec flips `draft → ready` and leaves `DEFERRED_SPECS` in the same
change, which is the precondition the Unifying Spec's own `realization-gate-home` question names.

| # | Question | Recommended answer |
|---|---|---|
| B6 | Owner | **Steward** stays owner; `hub:CAP-3` (Track) relays to marshal; the Frame-store half of CAP-2 relays to scribe. Same one-owner-plus-relays shape as `bmad-suite-lifecycle` (8 stations). |
| B7 | Which Guard categories are missing | Exactly two: **Source-Grounding** (exists at one site only — `scribe/recall.py` AD-8 — nowhere on dev/review output) and **Outcome** (absent entirely; blocked on C16's measure set). **Source-grounding first.** |
| B8 | Does a bmad-loop run constitute a Track; retention | Content ~60 % there (journal, gate record, state, logs) but **gitignored Tier-3** and missing model/adapter version, human approvals, any retention statement. **Assemble one tracked `track.json` per run**; keep Tracks indefinitely, raw payload 90 days. Marshal supplies the field enumeration (mars-B-E2). |
| B9 | Publish the repo's context as Frames | **Yes, minimally and privately**: one Company Frame from the `AGENTS.md` verified block + eight station Frames that `inherits` it, git as the store. **No Community Frame, no registry** (frame-spec has no LICENSE/tag; nebari-frames is single-writer SQLite, a fourth infra kind). Prerequisite: refresh the `AGENTS.md` block (stamped at `99e595cc6a`, main is `fe4025ea90`) via `bmad-project-context`. |
| B10 | Package NIC / frames client | Stale — done 2026-09-07 (Class A). Residue = conda-forge submission → **not now**. |
| B11 | Author the first `.frame.md` now or after the shape decision | **Now** — same work as B9, the one move the cutover does not penalise. **Contract fix:** CAP-2's success must not bind to upstream's unlicensed `tools/validate_frames.py`; rewrite to an in-repo four-field preflight, upstream validator optional. |
| D-1 | Which reading of "align" | **Reading 2** (artifact model on the existing stack) with reading 1 (vocabulary cross-walk) folded in; reading 3 (NIC substrate) deferred behind the cutover flag. |
| D-2 | `NebariApp` template + NIC kind profile | **Not now, `foundry-side`**; chart Ingress/Route stays primary (pap:AD-11). **Gate any `hub:` NIC-profile story on the first green `ocp-portability-smoke` run** (stB-F3: two unproven profiles side by side double the claim with zero evidence). |
| D-3 | `nebi push` before the cutover | **`foundry-side`, after the flag.** |
| guild-E3 | Charter amendment shape for CAP-1 | Close the "or the Unifying Strategy" branch **in the Charter's favour**; add the reverse cross-walk block (three Lexicon nouns with no Hub counterpart; the Cogs collision); carry an **explicit CAP-4 ruling** that an external vocabulary is cross-walked and never enters the seven. |

**C5 — marshal: the CAP-17 publishing seam lands as `spec-marshal-token-economy` CAP-18
(mars-B-B1).** Minted by the already-scheduled `bmad-correct-course` → Epic 33, as **one publisher
story shared with CAP-7 savings telemetry** (which today is five stub getters returning `None` —
the Layer-0 caveman getter plus four, `harness_bmadloop.py:1875-1898`). Three artifacts already name Epic 33; steward 49.8 is `blocked`
on it; the Spec is `ready` so correct-course takes it. *Alternative:* `spec-pyforge-marshal` CAP-5
(station front-door contract, purer) — requires Class B's `status:` + `BLOCKED-ON` disposition
first. **Also in Epic 33 (mars-B-B3):** the `risk-tiered-review-depth` wiring story, same "turn on
what is built" shape.

**C6 — widen Epic 49's realization gate from the Unifying CAPs to the station satellites.** The
pass found twelve more `done`-but-not-in-effect capabilities with no vessel:

| Capability | Owner | Evidence |
|---|---|---|
| `adaptive-model-tiering` (fed on 2 of 8 stations; floor-raise only on spin) | marshal | Unifying table row, corrected 2026-09-09 |
| `risk-tiered-review-depth` (zero callers) | marshal | `core/gate.py:724,768` |
| `marshal-parallel-dispatch-fanout` (`max_parallel = 1` everywhere; no live wave) | marshal | `cli/dispatch.py:902` |
| two Epic-20 watchdogs + Story 3.12 floor-raise observe `~/.bmad-loops`, dormant since 2026-08-22 | marshal | marshal-A headline |
| `atlas-query-dashboards` (C1) | atlas | — |
| `secure-live-dashboards` Django half (`pyforge.steward.dashboard` in no `INSTALLED_APPS`; `AuditEntry` has no table; 6 of 9 modules 0 consumers) | steward | `base.py` grep empty |
| `unified-container` (root `Containerfile` built by no workflow or pixi task; the container gates invoked by nothing) | steward | `platform-ci.yml:280,289` build other files |
| `ocp-as-a-portability-profile` / air-gap CI proofs (12.2/12.3/12.9 gated on repo variables that are not set) | steward | `gh variable list` = `ACTIONS_ENABLED=false` only |
| `developer-machine-bootstrap` (no clean-container run) | steward | Class B |
| herald live backend (100/100 failed runs, workflow disabled), deck-QA gate (called by nothing), pptx pipeline (never rendered a station deck) | herald | herald headline |
| `pyforge-mason` recipe verb family (`unavailable_verbs: ('recipe',)`) | mason | mason-B5 |
| scribe compile on a schedule (store last written 2026-08-27; "nightly" is a hand-installed crontab line) | scribe | scribe headline |

**Recommend:** effect stories on the **owning station's** epics (marshal Epic 33; atlas, herald,
mason, scribe each a small epic), with steward Epic 49 carrying only an index row per station so
one board shows the gate. Story 49.2's effect check gains marshal-B's cheapest test: **"has a caller
outside its own test file."** *Alternative:* all under steward Epic 49 (one board, foreign
surfaces everywhere — the exact `spec-surface-check` hazard doctor-B8 names).

**C7 — steward Epic 48 additions.**
- **48.1 widened**: station-agnostic by construction (`STICKY_STATUSES` has no syncer counterpart for
  *any* project, stB-E4) + the **epic-rollup defect** (Class B, stA-D8) + the `AGENTS.md:49`
  `--repair-feed` instruction still live (stA-D3) + the one-line `scratch-worktree-lifecycle` landing
  ritual (stB-B8). Marshal's `test_promote_sprint_status_regressions.py:55` pins the bug (mars-A-E3).
- **48.2 gains a clause**: ASGI thread-pool sized deliberately (`ANYIO_MAX_THREADS` or equivalent)
  against the same measured Langflow RSS (stA-B14).
- **48.8 Surface widened** (stA-B13, stB-B9): the four `absorbed-into: spec-python-agent-platform`
  pointers (asgi, db-gpt, enterprise-multi-agent, langflow-django-plugin), steward's own spine
  `ARCHITECTURE-SPINE.md:281,617` (parent pointer + `pap:AD-n` form), mason's
  `spec-django-accelerator-framework/SPEC.md:11,95` (relay). **`pap:` stays a live prefix** (280
  sites / 60 files / 4 stations; `ad_citation_check.py:123-124` special-cases it).
- **New 48.9 — OIDC default profile** (stB-B1): Keycloak in-cluster deployed by the Foundry chart
  (state in the existing PostgreSQL → not a lock breach), `COMPONENT_OIDC_*` seam stays the BYO
  escape hatch; decided together with 49.6 (`IDP_CLAIMS_SNAPSHOT` `None` at `base.py:214-215`).
- **New 48.10 — build the root `Containerfile` in CI** (stB-B7): a job or pixi task invoked by
  `pyforge-station-tests.yml`, running `container-gates secrets-scan` + `container-volumes` on the
  result; before 44.10 closes the CI window.
- **New 48.11 — `pyforge-warden` path dep in the platform env** (warden-B7, warden-E4): `tasks.py:97-102`
  lazy-imports `pyforge.warden.cli`; the image installs only `python-agent-platform`, whose sole path
  dep is `pyforge-steward`; every job lands `FAILED`. Same fix shape as `pixi.toml:181`. Requires
  `environment.yaml` regeneration (ungated).
- **`multi-repo-workspaces`** parked with the trigger "when a second repo joins the estate" (= 44.3).

**C8 — doctor rulings (doctor-B1/B5/B8/B9, guild-E1, herald-E3, mason-E8).**
- `DEFERRED_SPECS`: delete the two inert entries; add the invariant comment ("an entry names a Spec
  whose `status:` is in `OPEN_SPEC_STATUSES`"); fix the `spec-intelligence-hub` rationale; add a
  pruning rule for the exit "Spec left the open set" (mars-A-E2). `spec-pyforge-charter` (8 CAPs,
  zero stories, `in-progress`) is registered nowhere — **register with reason** (guild-E2).
- `chain-completeness`: emit **`spec-status-missing`** for a Spec with no `status:` key (never guess
  an implied status); the Dream side already has this check (`chain.py:993`).
- `sibling-dreams-drift`: **re-key on filename**, keep title as a reported axis; emit
  `sibling-dreams-unreachable` instead of `return ()` when the token is absent (fail-open today).
- `chain.py:96` `CONSTITUTIVE` hardcode → derive from `guild-roster.json` `guild_dreams` (guild-E1).
- `dreams-hygiene` reconciles only Dreams with a README row (`chain.py:891`) — 61 of 131 invisible;
  nothing enforces README:71. See § 2.4 D2.
- Deferred-work verifier bug (herald-E3, HIGH): project-relative `source_spec` resolved from repo root
  → resolvable specs stamped "absent" and re-marked open without reading. Fix in doctor's sweep.
- **Story 49.2's home**: keep the *criterion* on the Unifying Spec; **relay the implementation to a
  new doctor Dream + Spec** (every other doctor Source came through doctor's chain; `bmad_method.py:9-20`
  is doctor's own precedent for a dedicated module); record the incoming surface claim in
  `spec-pyforge-doctor`'s memlog **before** any code lands — otherwise `spec-surface-check` reds
  49.2 and 49.8 at merge. 49.8: doctor's only action is that memlog line + a comment at
  `sources/__init__.py:223`.

**C9 — warden `golden-path-conda-blind-spot` (warden-B1..B6).** Selector = both flags, explicit in
CI, host default only interactively. Provisioning = osv-native `--download-offline-databases` on the
connected runner, `actions/cache` keyed by snapshot date. **No coverage floor** (`clean` alone; the
first Constraint already forbids dropping components). **`clean` only — never promote on `warn`**,
waiver or not (`platform-deploy-verify-promotion.py:31` is the only fail-closed gate). Unscoped
union stays the default with a structured WARNING. **Mint now, ahead of CAP-1..4:** a regression test
that fails if the `!= 'clean'` refusal is removed — nothing tests the verifier today (only two
workflows reference it). `package-inventory-eligibility`: accept the deferral, record a named
residual; config story only together with the missing CLI front door (warden-B8).
`DEFERRED_SPECS`'s warden entry lists three wrong open questions (warden-E1) — fix in C8.

**C10 — marshal cursor routing + budgets + retries (mars-A-B1/B4/B5/B6..B9, mars-B-B4/B7/B11).**
`agent-tool-surface`: **federate** — HTTP station face (`mcp_http.py:137`) is the governed front
door, stdio servers are local adapters; 46 CFE tools + atlas tools have no CLI⇄tool parity gate
(mars-A-E6 → mason/atlas). Liveness `unknown` at resume: **warn-and-proceed**, printed reason
(refusing would block routine resumes daily — `project_steward_unknown_landing_journal`).
`bmad-switch-scope-enforcement`: wire `verify_scope` at `marshal factory dispatch`, defer
skill-injection to foundry 44.5. Cursor: **run the probe, plan for NO**; fallback **CAP-3b** (allowlist,
not a shelled-out "subagent" — the estate was burned at that seam twice); `.mdc` generation as a
**maintained pixi task + drift detector**; assume **no inline-import analog**, verify in the same
probe session. Fan-out: **mint `dispatch.max_parallel`** (one knob currently governs two engines and
fires a false-context clamp warn). Retry cap **3 per story per campaign**, policy-declared. Budget
signal: **wall-clock + idle-strand enforced by the dispatch supervisor; token ceilings advisory**
until Epic 33's benchmark exists. `fleet-consistency-standard`: INV-2/3 mechanisation → **doctor**;
coverage over the django tier → **testing-charter CAP-4**, not here.

**C11 — herald (herald-B1, E-1, E-4).** "Is there real pull?" → **No, and the evidence is in**:
`herald-live-demo.yml` `disabled_manually`, 100/100 failures, last run 2026-08-24; the store is
`runner.temp`; `webhook.py`/`scheduler.py` "never run as a real, listening process"; steward's
`deploy perimeter` cannot target an arbitrary ASGI callable (`deploy.py:484`). Re-open as a
*hosting* decision when the Foundry gives Herald a perimeter. Meanwhile: re-point
`webhook.ON_SHIP_PATH` / `ON_PR_CLOSE_PATH` onto `/stations/herald/api/v1/…` (only warden v1 is
registered on the seam, `station_api.py:146`); `stack.md:68` still binds `graphviz2drawio` to herald
(zero in herald — atlas prototype only). Herald's ledger: 59 `open` / 0 `resolved`; `DW-FU-15-1` is
resolved (`pyforge-station-tests.yml:160-182`) and still reads open.

**C12 — guild (guild-B1, E-4).** Keep `guild` (Class A). **The Guildhall referent needs a Charter
amendment**: `factory-console` is `superseded`, the Pages console retired-and-guarded; live surfaces
are Atlas's Vizro board, the Wagtail CMS and eight `django-*` portals; herald's Spec still cites
"the Guildhall is Marshal's ([[factory-console]])". §7 is a Lexicon noun, so the ruling is
constitutional, not a station decision — and CAP-7's refusal-to-publish gate has no home until it
lands. Charter CAP-3 names two reader files that no longer exist. **Recommend: mint the amendment as
a Charter open question now; decide the surface with C4's Track/Frame answers** (a Track is exactly
what a Guildhall displays).

**C13 — build-league-scorecard (stA-B5).** Do **not** fill the measure set. **Commission a measure
inventory**: a read-only enumeration of every signal the estate already counts, with `file:line`
(five-tier 8×5 completeness, ~30 detector pass/fail, ledger throughput, `gate-record.json` command
outcomes, `journal.json` timing, warden verdict rungs, `driver.py:198` per-run cost, steward
discovery `owner`/`work_class`) — a menu the operator selects from. Publishes no metric; violates no
Never; **unblocks the Hub's Outcome Guards** (C4-B7).

**C14 — steward, fund one green `ocp-portability-smoke` run before 44.10 (stB-B2(b)).** Set
`CRC_PULL_SECRET` + dispatch once. 44.10 disables this repo's CI; without a green run CAP-2/CAP-3 are
never provable in either repo and `deploy/README.md:134` stays permanently conditional. This is
also C4-D2's gate. *Alternative:* rewrite CAP-2/3 as template-only (the "criterion says fixture"
shape).

**C15 — steward, `secure-live-dashboards` adopter via 49.4 (stB-B6, stB-E3).** If 49.4 mounts
Atlas's real Vizro board on the host, it installs `pyforge.steward.dashboard` and routes loads through
`audit` + `export`; if 49.4 rewrites CAP-7 to name the fixture, the Spec's Django half is rewritten as
deferred in the same act. One decision. Correct 49.4's and `convergence.md:38,:129`'s "never
adopted" to "adopted at fixture grade (`django-atlas/board.py:17-20`, 5-row fixture); the real board
imports zero steward modules."

**C16 — atlas MinIO reconcile (atlas-B6).** Re-point DW-H1's object-storage half at the infra-kinds
answer (RWX volume / RWX-capable storage class); edit `spec-wagtail-corporate-brain/SPEC.md:24,135,137`
and `spec-pyforge-atlas/SPEC.md:571`. Do not re-open the Never (re-affirmed 2026-09-05).

**C17 — steward-A residue: `developer-machine-bootstrap` proof → a dedicated CI lane against
`python-foundry` after 44.3 (stA-B4)**, not podman-in-podman against a repo 44.10 archives.

### 2.4 Class D — new detector / Dream candidates raised by the pass (no vessel today)

| # | Gap | Raised by | Proposed vessel |
|---|---|---|---|
| D1 | **"Body contradicts its own status"** — six documents in one pass (herald ×2, scribe ×2, charter, unified-container) carry a `status:` their prose contradicts; `bmad-drift-check` polices vocabulary and counts, never narrative. | guild-E5, scribe-E3 | new doctor Dream (ambient, warn-only, fail-open — the `sibling-dreams-drift` shape); name the join and prove it on live data before the story closes (doctor-B4's lesson) |
| D2 | **README coverage** — `docs/dreams/README.md` maps 70 of 132 files; `dreams-hygiene` sees only rowed Dreams; nothing enforces README:71. | mars-B-E5, mason-E8, atlas-E2, warden-E2 | doctor: extend `dreams-hygiene` (`chain.py:891`) to every Dream file + a README:71 check; steward: regenerate the per-station progress figures the index carries (atlas "waves 0–H", warden "25/31" vs live 43/43) — or drop them |
| D3 | **Kinship wikilink validator** — the currency review found broken links; no detector validates `[[…]]` resolution. | stB-F2 | fold into `dreams-hygiene-check` |
| D4 | **Effect check: "has a caller outside its own test file"** | mars-B-E6 | 49.2 (C6) |
| D5 | **Deferred-work verifier path bug** (HIGH) | herald-E3 | doctor sweep fix (C8) |
| D6 | `bmad-drift` 17 live warns on marshal artifacts (`pin-behind` v8.86.1 < v8.90.1; CFE shipped five releases 2026-09-09 alone) — propose a **derived pin** (read `SKILL.md:10`) instead of a stamped literal. | doctor-E, mason-E5 | marshal SYNC-RUNBOOK row 84 |
| D7 | `stack.md` "Absent — feedstock work" table lists six feedstocks that shipped in `ed41099205` (incl. `cachebox`, on conda-forge at 5.2.3); High-Leverage matrix still carries five aspirational rows + three wrong-station bindings; broken regeneration command in `pixi_env_matrix.py::render_markdown`; the `pyforge.*` import-rule violation on both sides; "16 of 18 living names bind to nothing" — the currency review's five unvesselled findings. | stB-F2, stB-E5 | one 48.x "document-tier residue" story, or fold into 48.7's CAP-axis pass |
| D8 | Warden's architecture spine has **no `.memlog.md`** (P3) — blocks 44.13 as widened by 47.5. | stA-D1 | warden: mint the memlog (topic = architecture) |
| D9 | Marshal Story 31.4: the in-place-edited installer-owned pool is 11, 4 ungoverned, three never named anywhere (`sprint_status.py`, its test, `sprint-status-template.yaml` — the file carrying the Epic-44 `blocked` restore). | stA-D2 | marshal 31.4 (`backlog`) |
| D10 | Two `bmad_loop` dist-infos in one env (`0.11.1` + `0.8.1`). | mars-A-E7 | steward env hygiene |
| D11 | `miniforge-installer`'s trigger is steward-owned and un-watched; `reusable-cicd-workflows`' trigger fires at 44.7; `fleet-stewardship`'s `recipes/**` surface is mostly archived after 44.8; `fnd:CAP-3`/`CAP-6` (44.6, 44.9) carry Mason Rule 1/2 ACs with no mason counterpart. | mason-E1/E3/E4/E7 | reciprocal Kinship/trigger lines (steward ↔ mason) |

## 3. Cross-station routing table

| Finding | From → to | Vessel |
|---|---|---|
| Unifying Kinships asserts `atlas-query-dashboards` as a shipped Lane-3 runtime | atlas → steward | C1 (Dream edit, steward-owned) |
| 49.2 mints a doctor Source from a steward story | doctor → steward | C8 relay |
| 49.7/49.8 citations (`hub:CAP-3`; Unifying CAP-17 ≠ token-economy CAP-17) | marshal-B → steward | **applied 2026-09-09** (epics.md:3018, proposal:222; 49.7 re-grounded per scribe-E1) |
| CAP-17 seam → token-economy CAP-18 | marshal-B → marshal correct-course | C5 |
| warden spine memlog missing (P3) | steward-A → warden | D8 |
| `pyforge-warden` path dep + `environment.yaml` | warden → steward | 48.11 |
| MinIO in two atlas Specs ← DW-H1 wording | atlas → steward | C16 |
| `stack.md:68` graphviz2drawio herald binding | herald → steward | D7 |
| `DEFERRED_SPECS` warden entry text; intelligence-hub rationale | warden/steward → doctor | C8 |
| CFE cell move (44.6) vs rebuild campaign surface | mason → steward | C2 sequencing |
| `DW-FU-15-1` resolved but open; verifier bug | herald → doctor | C8 / D5 |
| 46 CFE + atlas MCP tools ungated for CLI⇄tool parity | marshal → mason/atlas | C10 |
| Guildhall referent | guild → herald/marshal | C12 |

## 4. Apply order (after approval — sequential, one station at a time)

Every BMAD write-skill resolves through the per-tree `_bmad-output/planning-artifacts` symlink, so
the apply is **never parallel**: `scripts/bmad-switch <slug>` between stations, memlog append →
`bmad-spec` update for every Spec except `spec-pyforge-unifying-strategy` (the standing hand-edit
exception). No `sprint-ledger-sync` on steward until 48.1 lands; new steward keys are minted with
`sprint_plan.py generate --set`.

1. **steward** (currently switched): Class A/B steward rows; Epic 48 additions (C7); Epic 49 index
   rows + 49.4/49.2 text (C6, C15); Unifying Dream Kinships (C1 consequence); `cutover-readiness.md`
   P-rows; Intelligence Hub Spec + Dream (C4) → `draft → ready`; build-league log (C13);
   `docs/dreams/README.md` rows; steward brief reconciliation for this file.
2. **doctor**: C8 (board.py edits are code → stories, not Spec edits: `DEFERRED_SPECS` prune,
   `spec-status-missing`, sibling re-key, CONSTITUTIVE, verifier bug); Class B doctor statuses;
   new Dream for 49.2's implementation + D1.
3. **marshal**: Class B flips (incl. `spec-pyforge-marshal` status + disposition); C10 closures;
   correct-course → Epic 33 with CAP-18 + risk-tiered wiring (C5) + the effect stories (C6).
4. **atlas**: C1 retirement record; atlas-B4/B5 statuses; C16 MinIO edits.
5. **warden**: C9 answers; verify-promotion regression story; D8 spine memlog.
6. **mason**: C2 campaign close (invokes `conda-forge-expert`); C3 absorb/archive; Class B status;
   Kinship lines (D11).
7. **herald / scribe / guild**: C11, C12, Class A/B rows.
8. Re-stamp baselines (`spec-surface-check --write-baseline --spec …` scoped; `bmad-drift-check`
   `--write-baseline`), run all 28 detectors + `chain_currency_sweep_check.py`, land as docs/planning
   PR(s) with the `maintenance` label (48.11 also regenerates `environment.yaml`).

## 5. What was applied before this batch (already on the working tree, uncommitted)

- Unifying Dream, Intelligence Hub Dream, token-economy Dream: the 2026-09-09 sections recorded in
  the currency review and its sprint-change proposal (approved), plus this session's corrections
  (adaptive-tiering row; `hub:CAP-3` vs token-economy CAP-3; CAP-7's four stub getters).
- Steward `epics.md`: Epics 48/49 minted; 49.7 re-grounded (scribe-E1); 49.8 citations fixed.
- `sprint-change-proposal-2026-09-09-currency-review.md:222` citation fixed.
- `resilience-invariants.md` BS-5/BS-6 rows marked SUPERSEDED (the Residual's false claim closed).

## 7. Apply record (2026-09-09, same day)

**Phase 1 — parallel by physical path (seven agents, no switch, no BMAD write-skill, no ledger
sync, no code).** Every station applied and verified; no existing ledger row changed status or was
dropped anywhere (checked key-by-key against `main`).

| Station | What landed | New ledger keys |
|---|---|---|
| steward | Epic 48: 48.1/48.2/48.7/48.8 amended, **48.9 OIDC / 48.10 root Containerfile CI / 48.11 warden path dep** minted; Epic 49: 49.2 widened + relayed, 49.4/49.6 text, **index rows 49.9–49.13** (`blocked`); Unifying SPEC.md hand-edit (companions, Residual, `## Absorbed (daf:CAP-*)` receiving the framework Spec's CAP-1 with the corrected `urls.py:98` citation); `cutover-readiness.md` P1/P2/P3/P7/P13 + G4/G7/G11 re-derived (**P3 NOT satisfied, 8 of 9**); 15 steward Dream edits; README status column synced, `extension-point` named, count line re-derived, rows for doctor's two new Dreams; reciprocal notes on 44.6/44.7/44.8/49.8; `enterprise-airgap` Kinships ↔ `miniforge-installer` | +28 (incl. the 20 from the morning's Epics 48/49) |
| doctor | **Epic 21 "Realization-gate hygiene"** (16 stories: DEFERRED_SPECS prune + invariant + charter registration; `spec-status-missing`; sibling re-key + `-unreachable`; CONSTITUTIVE from roster; verifier path bug; dreams-hygiene coverage + README:71 + Kinship validator; pixi-candidate CAP-4; intake CAP-9; effect-check CAP-1..3; status-body CAP-1..5); **NEW Dreams + Specs `capability-effect-check` (49.2's implementation) and `status-body-consistency` (D1)**; runbook § Land gains CAP-6's one-line rule | +18 |
| marshal | **Epic 33 "Token economy in effect"** (10 stories; CAP-18 one publisher; risk-tiered wiring; tiering fed on 8 stations + floor-raise on dispatch; watchdogs re-pointed; first live wave; `verify_scope` at dispatch; derived CFE pin) via a hand-authored correct-course product (proposal in `change-history/`, readiness report READY); 31.4 widened to the 11-file pool; 24 memlogs (77 entries); 22 Dream edits incl. **`risk-tiered-review-depth` down to `specified`** | +12 |
| atlas | **Epic 25** (25.1 retire `views/` + the page-count literal fix; 25.2 materialize CAP-8's Parquets, `blocked` on the attended Artifactory path; 25.3 MCP parity gate); DW-H1 re-pointed to RWX; `atlas-query-dashboards` Dream archived/retired, `enterprise-data-models-and-apis` → `dreamt`; two Dream bodies re-grounded | +5 |
| warden | **Epic 12** (12.1 verify-promotion regression test first; 12.2–12.6 = golden-path CAP-1..5 with the five answers baked in); `golden-path-conda-blind-spot` Spec → ready, Dream `specified`; **architecture spine `.memlog.md` initialised** (P3); `pyforge-warden` Dream 43/43 | +8 |
| mason | Rule 1 honoured (`conda-forge-expert` invoked); **campaign `endgame_declared: true`**; **Epic 15** (15.1 close the campaign, `blocked` = operator-dispatched; 15.2 the unwritten Rule-2 retro for 13.2) + **Epic 16** (16.1 CFE import floor; 16.2 first `mason recipe` caller; 16.3 CFE MCP parity gate; 16.4 Containerfile guard by glob); `django-accelerator-framework` Dream **archived / absorbed**, Spec → `absorbed-into: spec-pyforge-unifying-strategy`; `pyforge-mason` `realized` + dated caveat; three Dreams' currency (v8.90.1 / 117 gotchas / 46 tools) | +10 |
| herald / scribe / guild | herald **Epic 19 "Herald in effect"** (19.1 webhook routes on the station seam; 19.2 one real ship, `blocked` foundry-side; 19.3 deck-QA gets a caller; 19.4 one real pptx deck); `DW-FU-15-1` + `DW-14-2-1` resolved; scribe **Epic 8** (8.1 the compile gets an estate-owned trigger — not a GitHub workflow, per `docs/cli-runbooks.md`); Charter memlog: `guild` question surfaced + closed, **Guildhall-referent question minted**, CAP-4 cross-walk ruling; `pyforge-charter` Dream `pitched → specified`; `scribe-mines-raw-session-transcripts` → `realized` | herald +6, scribe +3 |

Ledger shape: the generator had rewritten six twins into its grouped form with six metadata keys
(none existed at `main`); the lead re-rendered all eight through `promote_sprint_status.render`
(canonical header + sorted keys) — parity vs `main`: **+90 keys, 0 removed, 0 changed**;
`ledger-regression` and `story-status` green. Marshal's proposal moved to `change-history/` and
its readiness report renamed to the date-only form the drift-check classifies. Spec-surface: scoped
baselines stamped for doctor's `spec-sibling-dreams-drift` (surface gained its test file) and the
two new doctor Specs, and for mason's `spec-machine-checked-recipe-knowledge` (its Spec now governs
`scripts/failure_catalog_check.py`, so the allowlist line for that path — matching nothing —
was removed by the lead; Story 15.1's clause reads as verified) and `spec-django-accelerator-framework`
(three dashboard paths left its surface on absorption). Four `drift-presumed` warns predate today
(`spec-packaging-factory` ×2 = the v8.88.1 `pr_artifacts.py` re-port; `spec-pyforge-unifying-strategy`
← `test_dashboard_e2e.py`; `spec-python-agent-platform` ← `deploy/DR.md`) and are left for their
owners to reconcile by memlog + scoped stamp.

**Phase 2 — sequential re-derive through `bmad-spec` (one switch user at a time).** 78 Spec
folders: doctor 9 (2 new SPEC.md) → warden 4 → herald 5 → scribe 2 → Charter 1 → mason 9 →
atlas 8 → steward 16 (Unifying SPEC skipped: hand-edit exception) → marshal 24 (+ herald and atlas
station Specs re-rendered once more). Zero reverts; every CAP id preserved; `spec-intelligence-hub`
reads **`ready`**; `spec-django-accelerator-framework` reads **`absorbed`** with its full prior
contract kept in-file until the Unifying Lane-2 section carries it. `dream-chain-check` and
`dreams-hygiene-check` green fleet-wide.

**Final gate (2026-09-09, after the marshal answers).** `pixi run -e local-recipes detectors`:
28 of 28 pass; `detectors-ci` exit 0; `chain_currency_sweep_check.py`: all eight station spines
current; `bmad-drift-check` warnings only (the CFE pin drift marshal 33.10 owns); `spec-surface-check`
ok with the four pre-existing warnings named above. Nothing committed at the time of writing; the
landing shape is the operator's call.

**Corrections to this file learned in the apply.** Stub savings getters are **five**
(`harness_bmadloop.py:1875-1898`, Layer-0 caveman + four). Atlas holds **93 story keys**, not 137
(a row count). `cutover-readiness.md` is `spec-bmad-suite-lifecycle`'s CAP-9 companion. DW-H1 is
atlas's row. `bmad-eval-quality`'s open questions close to zero, not one. The chain-currency
sweep's `overtaken` flag is structural (`fleet_scan.py:2118`: any open question on a chain Spec that
has a PRD and an architecture) and is not in `detectors`/CI; its runbook remedy is "resolve with the
operator, then empty the list" — see § 8.

## 8. Residual after the apply — resolved and remaining

**Resolved the same day (operator, chain-currency runbook § overtaken).** The six questions the
approved hoist put on `spec-pyforge-marshal` — plus body item 15 — were answered and rendered back
to `open_questions: []`:

| Item | Ruling |
|---|---|
| F-4 trust model | **B is the contract, A the v1 state**: attribution is advisory today (call-surface only, `journal.py:159`); it becomes unforgeable before the Track serves a second principal. Vessel **Story 33.11**, `blocked` on its trigger (cutover flag / shared Hub / external adopter) so it never outranks throughput work. |
| F-5 (narrowed) | No unattended mid-run freeze writer under `none`/`per-epic`; per-story approval; the policy seed is the only unattended source. |
| Q-11 | Cross-run fleet budget **out of scope for v1** (first shared mutable state across loop homes); per-run/per-story ceilings + `dispatch.max_parallel` + wall-clock/idle-strand are the controls; revisit after 33.1's baseline. |
| Q-12 | `gen_ai.*` OpenTelemetry deferred until the semconv is stable; the Track (33.4) is v1's seam. |
| Q-13 | Trigger one (bmad-loop `copilot --acp`) recorded as fired; alone it does not start the ACP migration. |
| Q-14 | Closed as a read: one wave of per-session timing from the dispatch journals, an AC on Story 33.1; 25 min stands until then. |
| body item 15 | Difficulty lives in the story spec's `difficulty:` frontmatter (57 specs; read by `model_tier_map`). |

**Epic 33 dispatch sequence (operator 2026-09-09, written into marshal's readiness report):**
33.1 → 33.5 → 33.4 → 33.2/33.3 → 33.6/33.7/33.9/33.10 → 33.8 last; 33.11 outside the queue on its
trigger. A hypothesis until 33.1 reports a measured baseline.

**Remaining asks.**
1. **Guildhall referent** — one open question on the Charter Spec (C12); herald's Non-goal `:137`
   re-words when the amendment lands.
2. **Fund one green `ocp-portability-smoke` run** (C14): set `CRC_PULL_SECRET`, dispatch once,
   before Story 44.10.
3. **Dispatch order across stations**: steward 48.1 first (unlocks every ledger sync); marshal 33.1
   first and alone; warden 12.1; doctor 21.1/21.2; mason 15.1 only on explicit confirmation.
4. Not applied by design: steward-B's unapproved status demotion of `unified-container`; the
   `ready -> shipped` recommendation on `spec-artifactory-download-intelligence` (scope-guarded);
   mars-A C11's stale `upstream-register.json` bmad-loop 0.9.0 citations; herald's 53 untouched
   open ledger entries (several duplicates); marshal PRD's dated paragraph (§ 4.6 of its proposal).
5. Seen in the fleet picture, not this pass's scope: bmad-eval-quality 1.4.2 and TEA 1.26.0 are
   released upstream — a bmad-suite refresh for a later session.

## 6. Claims re-verified by the reviewing session (beyond the agents' own evidence)

`harness_bmadloop.py:1875-1898` five stub getters (marshal agent counted the Layer-0 caveman one) · `herald-live-demo` last runs all `failure` ·
`webhook.py:183-184` path literals · `chain.py:96` CONSTITUTIVE hardcode · warden spine memlog absent
(9 spines, 8 memlogs) · steward ledger `epic-44..49: backlog` · `AGENTS.md:49` `--repair-feed` ·
`pixi.lock:17510` `bmad-suite-2026.9.5` · `_http.py:508` host-gated header · eval-quality Spec `:47-51,:68-69`
still `0.2.0` · `views/` imported only by its own tests (retired Story 25.1) · `[feature.pyforge-mason.dependencies]`
two lines, no floor deps · root `Containerfile` unreferenced (platform-ci builds `src/platform/Containerfile`
+ dbgpt sidecar) · `pyforge.steward.dashboard` absent from `base.py` · `gh variable list` =
`ACTIONS_ENABLED=false`; secrets = `ANACONDA_API_TOKEN`, `HERALD_WEBHOOK_SECRET` · verify-promotion
referenced only by two workflows · platform env path deps = `pyforge-steward` only ·
`sibling_dreams.py:118,155` keyed on title · `classify_review_tier`/`resolve_review_cycles` no
callers outside `gate.py` + tests · marshal `epics.md` tops at Epic 32 · `driver.py:198` `total_cost_usd`.
Not independently re-run: steward-A's P7/P13 customization-pool numbers (derived read-only after the
sandbox blocked the `steward upgrade bmad-core --json` pre-flight; method stated in that report).
