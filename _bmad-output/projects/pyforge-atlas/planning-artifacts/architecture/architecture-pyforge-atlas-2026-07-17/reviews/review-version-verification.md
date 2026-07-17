# Reviewer Lens — Version & Reality-Check Verification

- **Target:** `ARCHITECTURE-SPINE.md` (cf_atlas Kedro/Dagster/DuckDB Migration, 2026-07-17)
- **Lens:** every committed decision web-researched or reality-checked rather than asserted from training data; Stack table cross-checked row-by-row against the live `pixi.toml` (+ `pixi.lock`); GX-cap and kedro-dagster-pin claims checked against spec § FR-15 / § 13.2 / § 5.8; existence spot-checks for the obscure named technologies via web.
- **Reviewer date:** 2026-07-17
- **Evidence base:** `/home/user/local-recipes/pixi.toml`, `/home/user/local-recipes/pixi.lock` (resolved versions — the strongest in-repo ground truth per FR-15 doctrine), `/home/user/local-recipes/docs/specs/cfe-atlas-datapipeline-kedro-migration.md`, `/home/user/local-recipes/_bmad-output/projects/pyforge-atlas/planning-artifacts/intake-groundtruth-2026-07-17.md`, plus live web searches (proxy worked; kedro-dagster, boring-semantic-layer, kedro-mcp, nebi spot-checked).

## Verdict

**PASS with findings.** The spine's central verification claim holds: every Stack-table row traces to a real pin in the live `pixi.toml`, and `pixi.lock` proves the whole stack actually resolves in-env on Python 3.14.6 (kedro 1.5.0, kedro-dagster 0.7.0, dagster 1.13.13, duckdb 1.5.4, great-expectations 1.18.2, pandera 0.32.1, agno 2.6.22, nebi-cli 0.13, kedro-mcp 0.1.2, boring-semantic-layer 0.3.15 all present as resolved artifacts). The GX-cap and kedro-dagster claims match the spec exactly. No named technology is fabricated or dead. However, the verification-against-pixi.toml sweep missed four things the manifest itself would have told a careful reader — most notably that two Stack rows are PyPI-sourced in a spine that ratifies a "conda-forge-only" invariant, and that the `minio` pin is the Python SDK, not the storage server the Wave-H text implies.

## Row-by-row Stack table cross-check (vs live `pixi.toml` + `pixi.lock`)

| Spine row | pixi.toml evidence | Lock-resolved | Verdict |
|---|---|---|---|
| Python 3.14 floor | line 33 `python = ">=3.14.6,3.14.*"` (+ `3.14.*` at 493/542/875) | 3.14.6 | ✔ (nuance: exact-minor pin, not just a floor — see F-5) |
| kedro ≥1.5.0 | line 674 | 1.5.0 | ✔ |
| kedro-datasets ≥9.5.0 | line 676 | — | ✔ |
| kedro-viz ≥12.4.0 | line 685 | — | ✔ |
| kedro-dagster ≥0.7.0 | line 675 — **carries `# TODO PY314 conda-forge compat check`** | 0.7.0 (noarch) | ✔ pin / ⚠ see F-2 |
| kedro-mcp ≥0.1.2 | line 870 — **`[feature.local-recipes.pypi-dependencies]`** | 0.1.2 (PyPI) | ⚠ see F-1 |
| dagster / -pipes / -webserver ≥1.13.13 | lines 660–662 | 1.13.13 | ✔ |
| duckdb ≥1.5.4 (+ vss) | line 670 | 1.5.4 | ✔ pin / ⚠ vss see F-6 |
| ibis-framework / ibis-duckdb ≥12.0.0 | lines 673, 741 | — | ✔ |
| boring-semantic-layer ≥0.3.15 | line 869 — **`[feature.local-recipes.pypi-dependencies]`** | 0.3.15 (PyPI) | ⚠ see F-1 |
| structlog >24.2,<26 · sqlglot >26.32,<28.7 | lines 548–549 (exact match, incl. the xorq rationale comment) | — | ✔ |
| vizro ≥0.1.59 / vizro-ai ≥0.4.1 / vizro-mcp ≥0.1.4 | lines 688–690 | — | ✔ |
| pandera ≥0.32.1 | line 669 | 0.32.1 | ✔ |
| great-expectations 1.18.2 cap | line 668 is `">=1.18.2"` — a **floor** in the manifest | **exactly 1.18.2** | ✔ vs spec / ⚠ wording see F-4 |
| deptry ≥0.25.1 | line 584 | 0.25.1 | ✔ |
| nebi-cli ≥0.13 | line 630 | 0.13 (3 platforms) | ✔ |
| openlineage-python ≥1.51.0 | line 810 | 1.51.0 | ✔ |
| opentelemetry-sdk/api ≥1.43.0 | lines 811–812 | — | ✔ |
| duckdb-wasm / Pyodide "no pixi pin" | confirmed absent from pixi.toml | — | ✔ (accurate as stated) |
| agno ≥2.6.22 | line 759 | 2.6.22 | ✔ |
| wagtail ≥7.4.2,<8 (LTS) | line 807 | 7.4.2 | ✔ |
| django-lasuite ≥0.0.27 | line 809 | — | ✔ |
| PostgreSQL / MinIO / psycopg2 | postgresql resolved 18.4; `minio = ">=7.2.20"` line 815; psycopg2 ≥2.9.12 line 816 | 18.4 / 7.2.20 / 2.9.12 | ✔ psql+psycopg2 / ⚠ minio see F-3 |
| tomlkit <0.13.3 (dagster-dg-core) | line 545, rationale comment matches | — | ✔ |
| bmad-method ≥6.10.0,<7 | line 633 | — | ✔ |
| bmad-loop "v0.8.1 tag" | line 639 is `bmad-loop = ">=0.8.1"` — a **conda floor pin**, not a git tag | — | ⚠ see F-5 |
| tmux ≥3.4 | lines 836/841 — linux-64/osx-arm64 target tables only, matching the spine's "linux-64/osx-arm64 only" loop-plane claim | 3.7b | ✔ |
| litellm excluded (AD-16) | line 778: commented out, "NOT ADDED"; py3.14 rationale recorded in spec Q3 (line 1085) | absent | ✔ |

## Spec cross-checks (the two claims the lens singled out)

- **great-expectations 1.18.2 cap** — spine matches spec verbatim in substance. Spec § 5.8 (line 534): conda-forge 1.18.2 "installs and imports cleanly on Python 3.14 (live-verified 2026-07-16), but *upstream* declares `requires_python <3.14` as of 1.19.0 — so the env is capped at 1.18.2 … no story may depend on GX ≥1.19 features". Same in § 13.2 (line 1217), FR-10 (line 624), and the v5.2 changelog entry (line 1351) that encodes the "verify against the conda-forge build, not PyPI" lesson. The lock resolving *exactly* 1.18.2 on py3.14 independently confirms the cap is solver-real, not just doctrinal. ✔
- **kedro-dagster `dagster <2.0` pin** — spine matches spec. § 4.4 risk posture (line 425) and § 13.2 (line 1210) both record "bus-factor ≈ 1 … `dagster <2.0` pin; replaceable glue; exit ramps: Dagster Components / Prefect deployer". The spine's AD-1 parenthetical reproduces this faithfully, including the Prefect-acquisition context (announced 2026-07-13 per spec — a post-cutoff fact the spec web-researched, not asserted). ✔ (but see F-2 for the py3.14 residue.)

## Web spot-checks (non-blocking; proxy worked)

- **kedro-dagster** — exists; PyPI + GitHub (gtauzin → stateful-y org, consistent with the spec's "sole maintainer at a small consultancy"); alpha status; published classifiers list **Python 3.11–3.13 only** — corroborates F-2. No breaking event after 2026-07-16 surfaced.
- **boring-semantic-layer** — exists; 0.3.15 is the current release (2026-06-30, boringdata × xorq-labs); matches the pin exactly.
- **kedro-mcp** — exists on PyPI, 0.1.x era, "MCP server with Kedro prompts and tools" — consistent with the spine's "guidance-scoped 0.1.x plugin, never load-bearing" posture (AD-7).
- **nebi** — exists (nebari-dev/nebi, "Server and CLI for managing multi-user Pixi environments"; nebi.nebari.dev). See F-7 on fit.
- **duckdb-wasm / Pyodide / agno** — established projects, agno pinned+resolved in-env; existence not in doubt; no further check needed.

Sources: [kedro-dagster PyPI](https://pypi.org/project/kedro-dagster/), [stateful-y/kedro-dagster](https://github.com/stateful-y/kedro-dagster), [boring-semantic-layer PyPI](https://pypi.org/project/boring-semantic-layer/), [BSL site](https://boringdata.github.io/boring-semantic-layer/), [kedro-mcp (piwheels mirror)](https://www.piwheels.org/project/kedro-mcp/), [nebari-dev/nebi](https://github.com/nebari-dev/nebi), [Nebi docs](https://nebi.nebari.dev/).

## Findings

### F-1 (MEDIUM) — Two Stack rows are PyPI-sourced, contradicting the "conda-forge-only" invariant the spine ratifies
`boring-semantic-layer` and `kedro-mcp` live in `[feature.local-recipes.pypi-dependencies]` (pixi.toml lines 868–870), and the lock resolves them as PyPI wheels — yet AD-16's rule says "every component is conda-forge-sourced" and FR-15 is titled "conda-forge only". The Stack table lists both without an exception marker. This is exactly the class of fact a pixi.toml verification sweep should have caught. Not a blocker (both are declared replaceable/non-load-bearing glue per AD-1/AD-7), but the spine should either (a) footnote the two PyPI exceptions in the Stack table and AD-16, or (b) record migrating them to conda-forge as a rider. Note the air-gap consequence is already half-handled: AD-16's `[pypi-config]` routing clause exists *because* PyPI deps exist — the spine just never says which ones they are.

### F-2 (MEDIUM) — kedro-dagster's Python-3.14 compatibility is asserted-by-solve, not verified; the live manifest itself flags it
pixi.toml line 675 carries `# TODO PY314 conda-forge compat check` on the exact package, and upstream's published classifiers stop at Python 3.13 (web-verified). The lock resolves kedro-dagster 0.7.0 as **noarch** — and noarch packages don't let the solver enforce a Python ceiling, so "resolves in-env" is weaker evidence here than for any other row (contrast GX, where the solve *did* enforce the cap). The spine's "the stack is already resolved in-env (FR-15: adoption is wiring, not dependency addition)" over-reads solver success for this one dependency. Recommended: an import-and-compile smoke of kedro-dagster on py3.14 as part of Story A1/C1 acceptance (the `dagster-dryrun` gate would catch it, but that's Wave C — a Wave-A check is cheap insurance), and clear the manifest TODO when done.

### F-3 (MEDIUM-LOW) — "MinIO conda-forge-provisioned" rests on the Python client SDK, not a server
The pinned `minio = ">=7.2.20"` (resolved: `minio-7.2.20-pyhd8ed1ab_0.conda`, **noarch python**) is the MinIO *Python SDK* — MinIO server releases use date-based versions, and the noarch/pyh build string confirms this is the client library. The pixi.toml comment (line 815, "Amazon S3-compatible object storage system") mislabels it, and the spine's AD-22/deployment bullet ("PostgreSQL + MinIO, conda-forge-provisioned") inherits the mislabel. PostgreSQL is genuinely provisioned (server 18.4 in the lock); the MinIO *service* is not yet. Wave-H concern only — but it's an unverified assertion about what the live env provides. Recommended: verify a conda-forge MinIO server package exists (or pick an alternative S3-compatible store) before H1, and fix the manifest comment.

### F-4 (LOW) — GX "cap" wording implies a manifest upper bound that isn't there
The Stack preamble says "Pins are floors from pixi.toml except where capped", and the GX row reads "1.18.2 **cap**" — but the manifest pin is `>=1.18.2` (a floor). The cap is real (doctrine per spec § 5.8 + solver-imposed by the py3.14 env, lock-confirmed at exactly 1.18.2), just not expressed in pixi.toml. A reader auditing the manifest for `<1.19` will find nothing. One-line fix: "cap is env/doctrine-enforced (spec § 5.8), not a manifest upper bound". Optionally add `,<1.19` to the pin to make the manifest self-documenting.

### F-5 (LOW) — Two rows echo the spec/CLAUDE.md rather than the live manifest
- **bmad-loop "v0.8.1 tag"**: spec § 2 (line 96) describes a "pixi git dependency pinned to tag v0.8.1 (`tui` extra)"; the live pixi.toml (line 639) has a conda-style `bmad-loop = ">=0.8.1"` floor pin. Provisioning form drifted; the spine copied the spec's description instead of the manifest it claims to have verified against.
- **Python "3.14 floor (repo-wide)"**: the live pins are `>=3.14.6,3.14.*` / `3.14.*` — an exact-minor pin (floor *and* ceiling). Immaterial today, but "floor" suggests 3.15 would be accepted; the manifest says it wouldn't.

### F-6 (LOW) — DuckDB `vss` extension availability is unverified, and it matters for the offline invariant
`vss` appears only as a parenthetical capability; no `duckdb-extension-vss`-style package is pinned and DuckDB extensions default to network `INSTALL vss` at runtime. That collides with AD-13 (offline consumer profile) and the air-gap posture unless the extension is bundled or mirrored. Deferred item "F3 embedding model/strategy" is the natural home — add "offline vss provisioning" to that deferral's scope so it isn't discovered at F3 runtime.

### F-7 (INFO) — nebi's live positioning is environment management, not project scaffolding
nebi exists and 0.13 matches the lock on all three platforms, but its own docs position it as "git for environments" (tracking/sharing pixi workspaces), not a Kedro-project scaffolder — `kedro new` owns that role. The spec (§ 4.9) partially anticipates this ("if custom scaffolding logic is required … contributed back to nebi-client"), and Story A1's AC only requires "a Kedro project skeleton … scaffolded by nebi". Not a version issue; just note that A1 may resolve to "kedro new + nebi-managed env" in practice, which satisfies AD-16's intent.

### F-8 (INFO) — Everything else in the verification story checks out
- The intake-groundtruth file exists (`intake-groundtruth-2026-07-17.md`) and the spine correctly routes volatile counts through it + spec § 3.3 rather than free-standing literals (Decision 5).
- The "spec live-verifications date 2026-07-16" claim (Decision 4) matches the spec changelog (v5.1/v5.2/v5.4 entries all dated 2026-07-16), and the intake is one day later — the freshness window is honest.
- The Prefect/Dagster acquisition (2026-07-13), the GX PyPI-vs-conda-forge lesson, and the kedro py3.14 `PYTHONWARNINGS` suppression (pixi.toml line 151) are all post-training-cutoff facts correctly sourced from the spec's recorded research, not asserted from model memory.
- No named technology failed the existence check; no breaking event after 2026-07-16 surfaced for any of the six spot-checked projects (a ~1-day window — low information value, recorded for completeness).

## Disposition summary

| # | Severity | One-line | Suggested owner |
|---|---|---|---|
| F-1 | MEDIUM | BSL + kedro-mcp are PyPI deps; Stack table/AD-16 hide the conda-forge-only exception | Spine edit (Stack footnote + AD-16 clause) |
| F-2 | MEDIUM | kedro-dagster py3.14 unverified (manifest TODO + upstream ≤3.13 classifiers; noarch solve proves nothing) | A1/C1 AC: import smoke; clear TODO |
| F-3 | MEDIUM-LOW | "MinIO provisioned" = Python SDK only; no server in-env | Pre-H1 check; fix pixi.toml comment |
| F-4 | LOW | GX "cap" reads as a manifest bound; pin is a floor | Wording fix (or add `,<1.19`) |
| F-5 | LOW | bmad-loop tag-vs-floor + Python floor-vs-exact-minor echo docs, not the manifest | Two wording fixes |
| F-6 | LOW | `vss` offline provisioning unverified vs AD-13 | Fold into the F3 deferral |
| F-7 | INFO | nebi = env manager; scaffolding is `kedro new`'s job | None (A1 latitude exists) |
| F-8 | INFO | All other rows + freshness claims verified clean | None |

None of the findings undermine an architectural decision; they are verification-hygiene gaps in an otherwise genuinely reality-checked spine. The strongest evidence in the spine's favor is that `pixi.lock` — not just the manifest — carries every claimed component at (or above) its claimed pin, resolved on Python 3.14.6.
