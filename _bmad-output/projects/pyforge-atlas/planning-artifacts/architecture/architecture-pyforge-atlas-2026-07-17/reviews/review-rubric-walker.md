# Reviewer Gate — Rubric Walker Review

- **Artifact**: `_bmad-output/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`
- **Lens**: Rubric Walker (good-spine checklist, item by item)
- **Date**: 2026-07-17
- **Inputs walked**: spec `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (v5.6, full read of §§ 1–15 incl. all 22 FRs, § 5.2, § 3.3/3.4, § 2.5, § 11, § 13); PRD `prd-pyforge-atlas-2026-07-17/prd.md` (§ 8/§ 9.11 spot-verified); brownfield `architecture-cf-atlas.md`; live `pixi.toml` (pin-by-pin spot-check); `intake-groundtruth-2026-07-17.md` (existence verified).

## Verdict

**PASS WITH FINDINGS.** The spine is a strong, unusually well-grounded build substrate: all 22 FRs are mapped and correctly governed, the stack table matches the live `pixi.toml` on every row checked, the open-question adoptions match spec § 11 defaults exactly, the Deferred list is clean (nothing deferred is a must-fix-now divergence point), and the brownfield is ratified rather than contradicted. No critical findings. One high finding (a silent dimension: physical layout of the scaffold and the Parquet data layer), three medium (a missing DAG edge in the structural seed; several AD rules without a deterministic enforcement mechanism; no forward schema-evolution convention), and three low.

---

## Rubric item 1 — Fixes the real divergence points for epic/story builders; misses none

**Mostly PASS; two misses (F-1, F-7) and one seed defect (F-2).**

What it correctly fixes (verified against the spec):

- **Phase → pipeline assignment.** Spec § 5.2/Story B1 leaves the conda-side split between Core and VCS & Health open ("split across the Core and VCS & Health pipelines"). The spine's second diagram fixes it (B, B.5, B.6, F, I, J, M → core; E, E.5, K, L, N → vcs_health), with Phase H correctly in pypi_intelligence per the spec's producer/consumer clarification. This is a genuine divergence point the spine closes — exactly the job of this altitude.
- **Producer-ownership (AD-3)**, credential scoping (AD-2), TTL-as-dataset-concern (AD-5), exit-code convention (AD-12), offline skip-and-mark-stale (AD-13), parity scope for B8/B9/B10 (AD-14), derived-layer freshness (AD-15), the worktree/symlink seam (AD-18, which has already bitten this repo once), migration boundary (AD-19) — each is a real place two story builders would otherwise diverge, and each Rule is stated in enforceable terms.
- **AD-10 wholesale binding of the § 3.3 behavioral contracts** is the right move — it prevents per-story re-litigation of shipped semantics. (Minor: see F-6 on the enumeration reading as exhaustive.)
- The dependency-direction mermaid is declared "a rule, not an illustration" — correct posture.

**Miss (F-1, HIGH)**: the physical-layout dimension — `<scaffold-root>` location, `<pkg>` name, the scaffolded lean env's name, and above all the **Parquet store's on-disk root and partitioning convention** — is neither decided, nor in Deferred, nor an open question. Detailed under rubric item 7.

**Miss (F-7, MEDIUM)**: no forward **dataset schema-evolution convention**. AD-10 freezes the *legacy* shape (post-v25, no resurrecting dropped tables) and the legacy store had an explicit `SCHEMA_VERSION` mechanism (v29 live; v30 claimed by Phase T), but the spine says nothing about how a persisted Parquet dataset's schema changes going forward — add-column in place vs. new dataset version vs. catalog metadata bump, and who migrates existing partitions. Not in Consistency Conventions, not in Deferred, not an open question. Two Wave-B/C stories extending the same dataset family (e.g. the FR-19/20/21 riders on vulnerability/vcs_health datasets) could plausibly diverge here.

**Seed defect (F-2, MEDIUM)**: the domain-pipeline DAG omits the `vulnerability → seed_gaps` edge. Per spec § 3.4's seed-freshness table, `cwe-seed-gap` reads the `cwe_categories` dataset, and per § 13.1 the MITRE CWE catalog fetcher lives in the Vulnerability pipeline. The mermaid diagram feeds SEED only from CORE and PYPI. An epic builder sequencing Wave B from this diagram could schedule B6 (seed-gaps port) without the vuln-fetcher dependency, or a story builder could re-source `cwe_categories` into the wrong pipeline — exactly the drift class AD-3 exists to prevent. One edge (`VULN --> SEED`) fixes it.

## Rubric item 2 — Every AD's Rule is enforceable and prevents its stated divergence

**Mostly PASS; enforcement is uneven (F-3, MEDIUM).**

Well-enforced: AD-2 (`kedro-catalog-check` gate), AD-3 (Kedro's own unique-output validation makes two producers of one dataset a hard error), AD-6 (`dagster-dryrun`), AD-9 (fixture-proven stub-validator swap, Story F2), AD-11 (the gates ARE the mechanism), AD-12 (frozen enum + one-release env-var window), AD-14 (each guard explicitly fixture-enforced), AD-15 (byte-identical-seed pipeline test), AD-16 (`llms-full-check`).

Under-enforced — the Rule is precise but nothing deterministic catches a violation:

- **AD-1**: "No node, contract, or MCP tool may import Dagster or `kedro-mcp` APIs." No named gate. This is trivially grep/import-linter-checkable and is the spine's single most load-bearing lock-in defense — the whole exit-ramp story depends on it.
- **AD-8**: "read surfaces consume BSL, never raw SQL against Parquet/DuckDB." The named gate `bsl-metric-check` proves metric *parity*, not bypass *absence* — a Vizro page or MCP read tool that opens its own DuckDB connection would pass the gate. The 28-CLI-era fragmentation this AD exists to prevent re-enters exactly this way.
- **AD-4**: the `sqlite3` grep gate lands only at F1; Waves A–E have no mechanical guard against a convenience SQLite path creeping into new code (bounded risk while the legacy path legitimately runs in parallel until B4, but worth stating).
- **AD-5**: "No node may implement its own checkpointing" — review-only.

**Recommendation**: add one cheap static gate (import-linter or grep over `pipelines/`, `bsl/`, `mcp/`, `vizro_app/` for `import dagster`, `import kedro_mcp`, and raw `duckdb.connect`/SQL outside `bsl/`) as a Wave-A deliverable beside `kedro-test`/`kedro-catalog-check`. It converts AD-1/AD-8 from policy to invariant at near-zero cost and matches the spine's own "gates are fixtures" doctrine.

## Rubric item 3 — Nothing under Deferred could let two units diverge

**PASS.** Walked every Deferred entry against the wave/story order:

- **A2A transport (→ E1)**: the only producers of A2A alerts (F2 contract hook, F4 policy gate) land in Wave F, after E1 decides. The invariant that IS fixed now (structured payloads, single channel, schemas in `a2a/`) is the part units share. Safe.
- **Q6 (→ before B5)**: B5's AC explicitly requires Q6 recorded before porting; B2's Phase C port is unaffected either way (`g10_spelling` + no-clobber survive per AD-10). Safe.
- **Q7 (→ before B8)**: single-story blast radius. Safe.
- **Sensor sources + daemon (→ G3)**: G3 precedes H4's sensors, so the daemon decision lands before its second consumer (AD-22's Dagster-triggered crews). Safe — and the Q2-vs-§ 5.9 tension is honestly recorded as tension (Decision 7), not silently resolved.
- **Q2/Q3/Q4, F1 threshold, parity granularity beyond the Q1 views, D2 page inventory, F3 embeddings, B.6 full yanked, kedro-viz prototype, H1/H2 detail, BOD-26-04 mode**: each is single-owner, gated at or before its consuming story, with a named revisit condition. None is a cross-unit divergence point.

The things that *should* have been in Deferred but are nowhere: the physical-layout dimension (F-1) and schema evolution (F-7).

## Rubric item 4 — Named tech verified-current against live pixi.toml

**PASS with one wording defect (F-4, LOW).** Spot-checked every stack-table row against `/home/user/local-recipes/pixi.toml`:

| Spine row | pixi.toml | Match |
|---|---|---|
| python 3.14 floor | `python = "3.14.*"` (L542) | ✓ |
| kedro ≥1.5.0 / kedro-datasets ≥9.5.0 / kedro-viz ≥12.4.0 | L674/676/685 | ✓ |
| kedro-dagster ≥0.7.0 | L675 | ✓ |
| kedro-mcp ≥0.1.2 | L870 | ✓ |
| dagster (+pipes, webserver) ≥1.13.13 | L660–662 | ✓ |
| duckdb ≥1.5.4 / ibis-framework ≥12.0.0 (+ibis-duckdb) | L670/673/741 | ✓ |
| boring-semantic-layer ≥0.3.15; structlog >24.2,<26; sqlglot >26.32,<28.7 | L869/548/549 | ✓ |
| vizro ≥0.1.59 / vizro-ai ≥0.4.1 / vizro-mcp ≥0.1.4 | L688–690 | ✓ |
| pandera ≥0.32.1 / deptry ≥0.25.1 / nebi-cli ≥0.13 | L669/584/630 | ✓ |
| openlineage-python ≥1.51.0 / otel sdk+api ≥1.43.0 | L810–812 | ✓ |
| agno ≥2.6.22 / wagtail ≥7.4.2,<8 / django-lasuite ≥0.0.27 / psycopg2 ≥2.9.12 | L759/807/809/816 | ✓ |
| tomlkit <0.13.3 (dagster-dg-core) | L545 | ✓ |
| bmad-method ≥6.10.0,<7 / tmux ≥3.4 | L633/836,841 | ✓ |

**F-4 (LOW)**: the great-expectations row says "1.18.2 **cap**", but pixi.toml L668 is `great-expectations = ">=1.18.2"` — a **floor**. The effective ceiling is environmental (upstream declares `<3.14` from 1.19.0, so the py3.14 solve tops out at the conda-forge 1.18.2 build). The table's own preamble ("Pins are floors from pixi.toml except where capped") makes this row read as a manifest cap that doesn't exist. If conda-forge ever ships a 3.14-compatible ≥1.19 build, the env silently upgrades with no pin stopping it — the behavioral rule in AD-9 ("no story may depend on GX ≥ 1.19 features") still holds, but consider an explicit `<1.19` cap in pixi.toml or rewording the row as "environmental cap, not a manifest pin."

## Rubric item 5 — Ratifies rather than contradicts the brownfield

**PASS.** The brownfield `architecture-cf-atlas.md` carries older literals (SCHEMA_VERSION 28, 22 phases, 4 TTL-gated, 22 CLIs) vs the spec § 3.3 snapshot (v29, 23 cataloged phases incl. Phase I, 6 TTL-gated, 28 CLIs). The spine handles this correctly — Decision 5 explicitly subordinates the brownfield's stale literals to § 3.3 and records a sync note, not a conflict. Substantively, every brownfield mechanism is either ported with its contract intact (AD-10), replaced with the replacement named (AD-4/AD-5/AD-6 vs `phase_state` / `_TTL_GATED` / the 1800 s `cf_atlas_core` cap), or declared a non-product input along the § 3.4 boundary (AD-19). The `_http.py` credential defect is fixed-not-ported per FR-1, matching `docs/enterprise-deployment.md`'s documented workaround. The `bmad-switch pyforge-atlas` supersession of the spec's pre-intake `local-recipes` literal is genuinely carried from PRD § 9.11 (verified at PRD L529–533, L700–704). No contradiction found.

## Rubric item 6 — Spec drove the run; FR-1..FR-22 all mapped, none mis-governed

**PASS.** The Capability → Architecture Map covers all 22 FRs (FR-13/17 and FR-16/18 share rows, correctly — the spec couples them). Governance spot-audit:

- FR-1→AD-2/AD-13; FR-2→AD-3/AD-10; FR-3/4→AD-5 (+AD-19 for `phase_state` retirement); FR-5→AD-4; FR-6→AD-1/AD-6; FR-7→AD-7 (audit scope = `conda_forge_server.py` only, CLI-only trio excluded — matches § 3.3 exactly); FR-8/9→AD-8 (+AD-17; the three FR-9 exceptions match); FR-10→AD-9 (GX ceiling, banned plugins, identical halt semantics — per § 5.8); FR-11/12→AD-20; FR-13/17→AD-10/AD-15 (`cfe:*` + `?channel=` preservation); FR-14→AD-21; FR-15→AD-16; FR-16/18→AD-12 (four-axis report, inverted-enum reconciliation with the one-release `INVENTORY_MATCH_LEGACY_EXIT` window, no osv-scanner re-invocation — all per FR-16/FR-18 verbatim); FR-19/20/21→AD-13/AD-14 (all measured failure-mode guards present: ecosystem-tag match, tri-state `fix_available`, currency-conflation ban, first-availability-not-`latest_conda_upload`, ≤90-day gate, inferred `not-in-tracker` labeling); FR-22→AD-22.
- The two non-FR rows (verify-task inventory, worktree seam) correctly capture the spec's § 2.5 execution-architecture obligations.
- Decision 1's Q-adoptions match spec § 11 defaults verbatim (Q1 exact parity on actionable views; Q2 on-demand + acquisition re-verify at Wave C; Q3 repo routing, no hardcoded endpoint; Q4 Pages/host-agnostic; Q6 consolidate; Q7 build-once). Q5's retirement (Wave H committed) is correctly reflected as FR-22 scope, and the conditional Phase T handling (Decision 8) matches § 3.3's conditional-surface clause.

No FR missing, none mis-governed.

## Rubric item 7 — Every owned dimension decided, deferred, or open; operational envelope

**Mostly PASS — the operational envelope is explicitly present and is one of the spine's strengths**: five deployment planes (operator workstation, loop plane, static publish, air-gapped/enterprise, Wave-H services), the ~3 GB storage budget as a declared resource constraint, the three-way data-domain split, credential handling (conf/local + attended-only credentialed runs + per-host scoping), CI posture (exit codes, fixture gates), observability (AD-20). Infra/provider strategy is decided-or-deferred with named revisit points (Q2 daemon, Q4 host, exit ramps in AD-1).

**F-1 (HIGH) — one dimension is silent: the physical layout of the scaffold and the data layer.**

- `<scaffold-root>` — where in the repo does the nebi-scaffolded Kedro project live? Neither the spine, the spec, nor Story A1 fixes a path.
- `<pkg>` — the Python package name (which also becomes the Dagster repo name, the MCP module path, and the lean pixi env's identity).
- **The Parquet store's root location** — legacy runtime data lives in `.claude/data/conda-forge-expert/` (gitignored); the envelope bullet says runtime data is "`.claude/data/`, gitignored," but the structural seed shows no data directory at all, and whether the new partitioned-Parquet store lives under `.claude/data/`, under `<scaffold-root>/data/`, or elsewhere is undecided.
- **The partitioning convention** — "partitioned Parquet" is load-bearing in AD-4/AD-5 (and Phase P's 30 d monthly partitions are cited), yet no convention row fixes partition keys/layout, so per-dataset partitioning choices get made story-by-story.

Mitigation already in the spine: AD-2 forces all filepaths through the catalog, A2 is a single story, and the seed says "the code owns this once it exists" — so the blast radius is bounded to the A1/A2 story specs needing decisions the spine should have made or explicitly deferred. But the rubric is explicit: a dimension must be decided, deferred, or an open question — this one is none of the three. **Remedy**: one Consistency Conventions row (storage root + partition-key convention) plus either fixing `<scaffold-root>`/`<pkg>` or a Deferred entry "physical layout → A1 story spec (attended)."

**F-5 (LOW)**: AD-11's Rule opens "every wave's first deliverable is its own deterministic gate," but the enumeration covers six gates for Waves A/B/C/D/G only. Waves 0, E, F, H have no entry gate (F1's grep-gate is the F1 story itself; E and H have none anywhere in spec or spine). The wording is inherited from spec § 2.5, so the spine ratifies an existing overstatement rather than inventing one — but a spine rule that reads universal and isn't invites a story builder to either fabricate a gate or ignore the rule. Scope the claim ("every gated wave") or defer E/F/H entry gates with owners (E2 could seed a lineage-fixture gate; H1's scaffold-layout test is nearly one already).

**F-6 (LOW, informational)**: AD-10's contract enumeration reads exhaustive but omits a few § 3.3 fixture-enforced items: the `library-futures` calibration gate ("a weights change that reorders the pinned ranking fails CI … must survive as a pipeline test"), the `recommend-2027` six-property set + the `pypi_intelligence.notes` marker override channel, and the maintainer-universe ~44-feedstock reconciliation (Stories B1/B4). All are technically covered by the leading clause ("the spec § 3.3 contracts port intact"), so binding force is not at issue — but the list is what story builders will actually read: either mark it non-exhaustive ("including:") or add the three.

## Rubric item 8 — Mermaid validity

**PASS.** Both diagrams lint clean as mermaid:

- Diagram 1 (`graph TD`, dependency direction): all node IDs alphanumeric, all labels double-quoted (colons, slashes, parens safely inside quotes), plain `-->` edges. Valid.
- Diagram 2 (`graph LR`, domain DAG): `<br/>` inside quoted labels is supported; the apostrophe in `G'` sits inside a double-quoted string — valid; the en-dash in `O–S` is fine. Valid syntax — but see F-2 for the missing `VULN --> SEED` edge (a content defect, not a syntax one).

---

## Findings Summary

| ID | Severity | Finding | Remedy |
|---|---|---|---|
| F-1 | **HIGH** | Physical-layout dimension silent: `<scaffold-root>` path, `<pkg>` name, Parquet store root, and partition-key convention are neither decided, deferred, nor open — the one whole dimension the rubric flags | Add a storage-layout Consistency Conventions row; fix or explicitly defer scaffold-root/pkg to the A1 story spec |
| F-2 | **MEDIUM** | Domain-pipeline DAG omits `vulnerability → seed_gaps` (`cwe-seed-gap` reads `cwe_categories`, a Vulnerability-pipeline product per spec § 3.4/§ 13.1) | Add `VULN --> SEED` to the second mermaid diagram |
| F-3 | **MEDIUM** | AD-1's import ban and AD-8's no-raw-SQL rule have no deterministic gate (`bsl-metric-check` proves parity, not bypass absence); AD-4's grep gate arrives only at F1; AD-5's no-checkpointing is review-only | Add a Wave-A static import/grep gate beside `kedro-test`; cite it in AD-1/AD-8 |
| F-7 | **MEDIUM** | No forward dataset schema-evolution convention: AD-10 freezes the legacy shape and legacy `SCHEMA_VERSION` disappears, but nothing governs how a persisted Parquet dataset's schema changes (in-place add-column vs. versioned dataset; who migrates partitions) | Add a Consistency Conventions row or a Deferred entry with an owner (natural home: A2/A3 story specs) |
| F-4 | **LOW** | Stack table calls GX "1.18.2 cap" but pixi.toml pins a floor (`>=1.18.2`, L668); the cap is environmental (py3.14 solve), so a future 3.14-compatible ≥1.19 build silently upgrades | Add `<1.19` to pixi.toml or reword the row as an environmental cap |
| F-5 | **LOW** | AD-11's "every wave's first deliverable is its own deterministic gate" vs six named gates for nine waves (0/E/F/H uncovered) — inherited from spec § 2.5 | Scope the claim or defer E/F/H entry gates with owners |
| F-6 | **LOW** | AD-10's contract list reads exhaustive but omits the `library-futures` calibration fixture, the `recommend-2027` property/notes-marker contracts, and the maintainer-universe delta reconciliation | Mark the list "including:" or add the three items |

## What the spine gets right (for the gate record)

- All 22 FRs mapped, correctly governed, none silently re-scoped; the two non-FR map rows capture the spec's execution-architecture obligations.
- Stack verified pin-for-pin against the live `pixi.toml` (14+ rows checked, all match), honoring the FR-15 "in-env build is ground truth" doctrine.
- Open-question adoptions are verbatim spec § 11 defaults with scheduled re-checks; the Deferred list is genuinely safe — every entry is single-owner and lands before its first consumer.
- The brownfield is ratified with its stale literals correctly subordinated to spec § 3.3 (sync note, not conflict); the PRD § 9.11 `bmad-switch` supersession is real and carried.
- The Core/VCS-Health phase assignment closes a divergence point the spec left open — exactly the job of this altitude.
- The operational envelope is explicit and multi-plane — the dimension most spines leave silent is present here (minus F-1's storage-layout corner).
