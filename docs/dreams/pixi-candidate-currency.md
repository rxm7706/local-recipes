---
title: Every pixi.toml dependency — in or out, floor or latest — carries a live reason, not a silent guess
type: dream
owner: doctor
status: dreamt
---

# Every pixi.toml dependency — in or out, floor or latest — carries a live reason, not a silent guess

## The Dream

`pixi.toml`'s `[feature.local-recipes.dependencies]` block (and its `pypi-dependencies` /
`target.*` siblings) has accumulated **44 commented-out candidate packages** across 64 lines —
some with a one-line reason trailing the entry, most with none at all. Today the only way to
know whether any one of them is genuinely blocked, safely addable, dead upstream, or just never
revisited is to re-derive it from scratch — which is exactly what happened this session for
`caveman`, `headroom-ai`, `codegraph`, `ppt-master`, `ocrmypdf`, and (transitively, via the
click conflict it shares with `headroom-ai`) the `dbt-*` trio. Each of those took real
investigation — conda-forge repodata queries, actual `pixi install` solves, upstream release
notes — to answer a question that, once answered, should never need re-answering unless the
world underneath it changes.

The deeper discovery this session made: **most of these 44 already have a local recipe**, many
already built successfully (`cfe-local-build-status: success`), several already confirmed live
on conda-forge or SelfExplainML. The packaging half of the work is frequently *done* — what's
missing is a tracked answer to "why isn't this in the environment, then," which today lives
nowhere but a git blame and a half-line trailing comment.

This is one half of a single problem; the other half is the mirror image. `pixi.toml` already
carries a canonical bulk-upgrade command (top of file, 19 excludes, each with an inline reason)
for *active* dependencies the maintainer already knows are deliberately held back below latest.
What's missing is the same accounting for everything else already IN the environment: is a given
active package at its true latest, and if not, is that a *choice* or a *conflict*, and if a
conflict, *whose*? The literal trigger: "what is blocking the latest networkx, what's blocking
latest click" — both answerable, and both illustrate the two shapes this half takes. `networkx`
is already on the canonical exclude list (`2.4.*`, "pinned for conda-build compat" — a choice,
documented, done). `click` is not excluded at all, isn't even directly declared, and is stuck at
`8.2.1` while conda-forge ships `8.4.2` — because `conda-recipe-manager 0.10.5` hard-pins
`click==8.2.1` exactly (a feedstock bug — its own `pyproject.toml` declares click unpinned),
which is the *exact same* root cause already named above as the reason `headroom-ai` and the
whole `dbt-*` trio can't be added. One root cause, symptoms on both sides of the comment
boundary — which is why this stays one Dream, not two.

## What it looks like when real

- Every commented-out `pixi.toml` entry carries a **disposition** answering one of five
  questions definitively: *blocked* (a real, currently-verified conflict, with a re-check
  trigger named — new upstream release, ecosystem migration landing), *archived* (upstream is
  dead; no action possible, ever), *stale* (a dead duplicate or superseded entry; delete it),
  *ready* (verified clean, just needs the line uncommented), or *unexamined* (nobody has
  checked yet — the honest default, not a guess dressed as one).
- Re-checking a `blocked` disposition is cheap because the trigger condition is named, not
  because someone remembers to look — the same "re-derive, don't decay" discipline
  [[chain-currency-sweep]] applies to planning-spine artifacts, applied here to a dependency
  ledger instead.
- A `blocked` disposition that shares a root cause across multiple packages (the
  `conda-recipe-manager` `click==8.2.1` pin blocks `headroom-ai` *and* the entire `dbt-*`
  trio identically) is recorded once, not rediscovered three times.
- The same discipline applies to ACTIVE dependencies stuck below their true latest: a
  `blocked` disposition names the **exact** upstream package + spec doing the blocking, found
  by scanning what our *actually-resolved* builds declare in `depends`/`constrains` — not
  inferred, read directly off conda-forge's repodata for the builds genuinely in our lock.
  `platform-gap` (the newest release genuinely hasn't shipped a build for one of our three
  platforms/python 3.14 yet) is a distinct disposition from `blocked` (a real, fixable-elsewhere
  version conflict) — the fix path differs (wait vs. an upstream feedstock PR).
- The canonical upgrade command's exclude list and this Dream's `deliberate` bucket are the same
  list, checked against each other — an exclude with no reason, or a real block missing from the
  excludes, is the kind of drift [[chain-currency-sweep]] exists to catch elsewhere.

## What is real

Verified this session, each via an actual `pixi install` solve or a real local build — not
inferred from comments:

- **Added**: `ppt-master` (base deps, SelfExplainML noarch build) and `codegraph` (linux-64
  target, SelfExplainML linux-64-only build) — both solve clean, zero downgrades.
- **Blocked, root-caused**: `headroom-ai` and the `dbt-core`/`dbt-duckdb`/`dbt-postgres` trio
  all hit the *same* wall — `conda-recipe-manager`'s feedstock pins `click==8.2.1` exactly,
  which conflicts with anything needing `click>=8.3`. This is a documented upstream feedstock
  bug (`pixi.toml`'s own dbt comment already names it), not something fixable in this repo.
  `caveman` is blocked separately — it hard-requires `nodejs>=26.5.0`, which conflicts with
  `marp-cli`'s `nodejs` 22/24 pin; this environment hasn't adopted nodejs 26 yet (a separate,
  already-documented `a2a-sdk`/`libabseil` conflict).
- **Reconfirmed still valid**: `ocrmypdf`'s linux-64-only placement (its hard dep `pngquant` is
  still absent from conda-forge's `osx-arm64`/`win-64` repodata, verified live).
- **Fixed at the source, not here**: `pngquant`'s own osx_64 cross-compile bug (a
  `PKG_CONFIG_ALLOW_CROSS` gap in `libpng-sys`'s build.rs) was root-caused and patched in the
  upstream feedstock PR (conda-forge/pngquant-feedstock#16) — once that merges and pngquant
  ships win-64/osx-arm64, `ocrmypdf`'s own gate can be revisited.

**Addendum 2026-08-30 — the click wall fell, and caveman got a patched build (all
solver-verified, landed):**

- **`headroom-ai` ACTIVE (0.37.0, all platforms) + `dbt-core`/`dbt-duckdb`/`dbt-postgres`
  ACTIVE**: the shared `conda-recipe-manager` `click==8.2.1` wall was removed rather than
  waited out — nothing in this repo invokes `crm`/`conda_recipe_manager`/`feedrattler`
  (verified: zero task/script/source hits), so `conda-recipe-manager` + `feedrattler` (which
  transitively requires it) moved out of `feature.grayskull`/`feature.local-recipes` into a
  new grayskull-env-only `[feature.crm.dependencies]`. Migration tooling still runs via
  `pixi run -e grayskull …`; the upstream fix (conda-forge/conda-recipe-manager-feedstock#44)
  remains the long-term path back if local-recipes ever grows a real crm call. Note the
  false-dawn on the way: headroom-ai 0.37.0's `pixi search` listing appeared click-free, but
  anaconda.org repodata shows every 0.37.0 build carries `click >=8.3.3` — the wall was real
  until crm left the env.
- **`caveman` ACTIVE (2.4.0 build 2, linux-64 target)** via a patched SelfExplainML rebuild:
  the blocker was SHARPENED first — not (only) marp-cli's nodejs, but `codegraph` 1.6.0's own
  `nodejs >=24.19,<25` run-export makes caveman (build 1: `nodejs >=26.6,<27` run-export from
  a host that resolved 26.6.0) mutually exclusive with an active Layer-2 instrument. Upstream's
  true floor is `engines >=18`, so build 2 holds host nodejs at `24.*` and its run-export lands
  inside codegraph's window (`recipes/caveman` documents the hold + lift trigger: the env
  moving to nodejs 26 once the marp-cli/a2a-sdk libabseil gap closes).

**Active-dependency version currency** (the other half of this Dream): a full audit pass, same
session, grounded entirely in live solver output and repodata — not guessed. Parsed `pixi.lock`'s
`local-recipes` environment (1147 packages on linux-64), diffed against fresh conda-forge
repodata to find everything below latest (149), then used `pixi update --dry-run` (re-solves
*within existing manifest constraints*, no manifest edits) as the oracle for "genuinely stuck" vs
"just a stale lock nobody refreshed": 38 of 149 were stale-lock only; **111 stay capped even
after a full re-solve**. Of those:

- **Root causes found and solver-verified for 8 packages**, collapsing to 6 distinct upstream
  culprits: `conda-recipe-manager==8.2.1` (blocks `click`, and per the candidate ledger above,
  `headroom-ai`/`dbt-*`); `instructor`'s `constrains: anthropic==0.76.0` (a soft constraint,
  G67-class, binding because `anthropic` is separately active — blocks `anthropic` and
  transitively `langchain-anthropic`) plus its hard `depends: rich>=13.7.0,<15.0.0` (blocks
  `rich`); `conda-smithy`'s `depends: py-rattler>=0.22,<0.23` (blocks `py-rattler` and
  transitively `pixi-to-conda-lock`); `pytorch`'s + `vsts-python-api`'s `setuptools<82` caps
  (block `setuptools`); `panel-core`'s `bokeh>=3.7.0,<3.10.0` cap; `conda`'s own
  `ruamel.yaml>=0.11.14,<0.19` cap.
- **One platform-support gap solver-verified directly**: temporarily bumped `pyarrow`/
  `pyarrow-all`'s floor to `25.0.0` and re-ran `pixi update --dry-run` for real (edit reverted
  after) — `pyarrow-core 25.0.0`'s osx-arm64 build needs *either* `python>=3.13,<3.14.0a0`
  (conflicts with this workspace's python 3.14 floor) *or* an unreachable `libabseil` window — a
  genuine upstream platform gap, not a local conflict, plausibly explaining the ~20-package
  Arrow/AWS-C transitive cluster too.
- **One hard, unfixable-locally ceiling**: `speechrecognition 3.17.0`'s own build declares
  `python>=3.10,<3.13` — no py3.14 build exists yet.
- **Two checked but left genuinely undiagnosed** (`diffusers`, `conda` itself — small deltas,
  no offending cap found in this pass).
- **All 93 remaining packages evidence-verified, not left as hypotheses**: for each, either a
  currently-locked package's own `depends`/`constrains` excludes the latest version, or the
  target's own newest build introduces a new requirement conflicting with something already
  locked. Every finding was traced through its full chain to a terminal package, and every
  terminal package was independently confirmed to already be at ITS OWN conda-forge latest —
  these are real upstream compatibility caps, not stale locks. 59 trace to 34 distinct terminal
  packages (`aws-sdk-cpp` alone blocks 13 — the single highest-leverage check), 28 are
  same-recipe-family siblings needing a coordinated bump rather than an upstream fix, 4
  (`grpcio`/`grpcio-status`/`libgrpc`/`libabseil`) are a genuine multi-producer ecosystem
  version-diamond (G97-class — no single feedstock fix, needs convergence across release
  trains), and 2 are deliberate tradeoffs (bumping would force downgrading something kept newer
  on purpose) — see the version currency ledger below.

## The full candidate ledger

Grouped by disposition. "Local recipe" = a `recipes/<name>/` directory exists in this repo
(most already do); "cfe build" is that recipe's own `cfe-local-build-status` field where one is
recorded.

### ✅ Resolved this session

| Package | Location | Outcome |
|---|---|---|
| `ppt-master` | base deps | Added — bumped 4.2.0→5.1.0, built, published to SelfExplainML |
| `codegraph` | linux-64 target | Added — SelfExplainML linux-64-only build |

### 🔴 Blocked — real, verified conflict (re-check trigger named)

| Package | Local recipe / build | Conflict | Re-check when |
|---|---|---|---|
| `headroom-ai` | ✅ success | `conda-recipe-manager` pins `click==8.2.1`; headroom-ai needs `click>=8.3.3` | `conda-recipe-manager-feedstock` relaxes the pin (upstream `pyproject.toml` already declares unpinned `click` — it's a feedstock bug, not an upstream constraint) |
| `dbt-core` | build status unrecorded | same `click==8.2.1` conflict (dbt-core needs `click>=8.3.0,<9.0`) | same fix as above |
| `dbt-duckdb` | build status unrecorded | transitively blocked by `dbt-core` | same fix as above |
| `dbt-postgres` | ❌ failed (cf: confirmed-on-conda-forge) | same `click` conflict | same fix as above |
| `caveman` | ✅ success (SelfExplainML, this session) | needs `nodejs>=26.5.0`; conflicts with `marp-cli`'s `nodejs` 22/24 pin | this env adopts nodejs 26 (blocked on a separate `a2a-sdk`/`libabseil` conflict) OR marp-cli 4.5.0 is adopted |

### ⚫ Archived / no action possible — upstream is dead

| Package | Why |
|---|---|
| `agntcy-acp` | upstream project archived |
| `python-a2a` | upstream stalled, no updates |
| `imaginairy` | flagged outdated/unmaintained on conda-forge |

### ⚪ Stale — dead duplicates or superseded entries, safe to delete without investigation

| Package | Line | Why |
|---|---|---|
| `ocrmypdf` | 1596 (base deps) | already active in the linux-64 target block — this is a dead second copy |
| `pyarrow` | 1515 | superseded by the already-active `pyarrow-all` in the same block |
| `pydantic` | 1410 (`>=2.11.9,<2.13`) | superseded by the second, newer-pinned entry at 1635 |
| `networkx` | 1420 (`2.4.*`) | exact duplicate of the identical entry at line 57 |
| `ixi-build-go` | 1468 | **typo** — missing leading `p`, should read `pixi-build-go` (currently can't even be found under this name) |

### 🟡 High confidence — packaging already done, worth trying first

Local recipe exists, `cfe-local-build-status: success`, and upstream availability is already
confirmed (conda-forge or SelfExplainML):

| Package | On | Note |
|---|---|---|
| `networkx` | conda-forge | recipe flags a `missing-license-file` blocker — check before adding |
| `tomli-w` | conda-forge | clean |
| `mybmad-dashboard` | staged-recipes PR #33513 (pending) | linux/osx only per its own recipe note |
| `bmalph` | staged-recipes PR #33557 (pending) | we verified this exact PR **green** earlier this session (as a side effect of the caveman-installer PR fix) — likely close to merge, worth checking PR state before re-investigating |
| `bmad-autopilot` | pending-submission | unix-only |
| `claude-mem` | pending-submission | — |
| `litellm` | conda-forge, confirmed | pixi.toml's own comment says "NOT ADDED — Tier-3 LLM router" — investigate why it was deliberately held back before assuming it's just unexamined |
| `ibis-framework` | conda-forge, confirmed | `missing-license-file` blocker flagged, same as networkx |
| `agent-framework` | pending-submission | recipe exists, never built locally (`not-attempted`) |

### 🟠 Known local build failures — investigate the recorded failure before retrying

| Package | Recorded status |
|---|---|
| `appthreat-vulnerability-db` | failed — `missing-license-file` blocker ×3 (likely multi-output) |
| `pydantic` (active entry, line 1635) | failed |
| `streamlit` | failed — `missing-license-file` blocker |
| `pygwalker` | failed (separately, also has its own upstream `python-quickjs`-on-osx-arm64 gap noted inline) |
| `chainlit` | build-clean-test-blocked (artifact built; test env solve blocked) |

### ⚪ Special case — likely stale, needs re-verification against this session's own work

| Package | Recorded blocker | Why it's suspect |
|---|---|---|
| `langflow` | `blocked-pending-prerequisites`: langflow-base, lfx, opendsstar | This session's own ancestor work (the `langflow-suite` bundle: langflow-base + langflow + lfx + langflow-sdk) built, tested, and submitted to staged-recipes successfully. This local recipe's blocker list almost certainly predates that and needs a fresh check, not a repeat of the original investigation. |

### 🔵 Recipe exists locally, no CFE build record — genuinely unexamined, but packaging groundwork may already exist

`regex`, `portalocker`, `dlt`, `perspective`, `django-pygwalker`, `crawl4ai`,
`azure-identity-broker`, `microsoft-agents-m365copilot`, `kedro-dagster`, `generator-code`,
`crewai`. Several of these (`regex`, `portalocker`, `dlt`, `django-pygwalker`) carry a
`meta.yaml` alongside `recipe.yaml` — this repo's convention for mirroring a feedstock that's
**already deployed on v0 conda-forge**, meaning these are plausibly already on conda-forge and
simply never re-tried in this environment.

`microsoft-agents-m365copilot` is worth flagging specifically: the pixi.toml entry names only
the bare package, but a full 14-recipe local closure already exists
(`microsoft-agents-activity`, `-copilotstudio-client`, `-hosting-aiohttp`, `-hosting-core`,
`-m365copilot`, `-m365copilot-beta`, `-m365copilot-core`, plus the eight `microsoft-kiota-*`
recipes it depends on) — investigating this one means investigating the closure, not one
package.

### ⬜ No local recipe at all — genuinely never investigated

`oras-py`, `conda-tree`, `pixi-build-nodejs`, `pixi-devenv`, `pixi-browse`, `nebi-desktop`
(already carries a real blocker note — `webkit2gtk4.1` needs `__glibc>=2.34`, unsatisfiable —
so this one is closer to *blocked* than *unexamined*), `aichat`, `vscodepy`, `daft`,
`pyarrow-all` (only inside the fully-commented scratch template at the bottom of the file, not
the active `pyarrow-all` already in use elsewhere), `m2-bash`, `posix` (this exact package name
is independently flagged in a skill gotcha as deprecated in favor of `m2-base` on Windows).

## The version currency ledger

The mirror image of the candidate ledger above: ACTIVE dependencies stuck below their true
conda-forge latest even after a full `pixi update --dry-run` re-solve within existing manifest
constraints (111 of 149 found below-latest; 38 were stale-lock only and excluded here as
non-findings).

### Already deliberate — on the canonical exclude list, each with a stated reason (no action)

`conda-libmamba-solver`, `conda-build`, `conda-index`, `conda-forge-ci-setup`,
`conda-forge-pinning`, `frozendict`, `networkx` (`2.4.*` — conda-build compat),
`rattler-build-conda-compat`, `grayskull`, `conda-recipe-manager` (excluded from the *upgrade*
command, but its own pin is exactly what blocks `click` below — exclusion from upgrade attempts
doesn't mean its effects are excluded), `conda-smithy` (`<4` — CalVer needs `conda`, absent
here), `shellcheck`, `nodejs` (`<27.0,!=25.*` — LTS-track policy), `python`, `django` (`<6.0`,
paired with `wagtail<8.0`), `channels`, `daphne`, `wagtail` (`<8.0`), `coderedcms`.

### 🔴 Blocked — root cause solver/repodata-verified, exact culprit named

| Package | Locked → Latest | Blocked by |
|---|---|---|
| `click` | 8.2.1 → 8.4.2 | `conda-recipe-manager==8.2.1` (exact pin, feedstock bug) |
| `anthropic` | 0.76.0 → 1.2.0 | `instructor`'s `constrains: anthropic==0.76.0` (binds because anthropic is separately active) |
| `rich` | 14.3.4 → 15.0.0 | `instructor`'s hard `depends: rich>=13.7.0,<15.0.0` |
| `langchain-anthropic` | 1.3.1 → 1.7.0 | transitively via `anthropic` above (1.7.0 needs `anthropic>=0.120.0`) |
| `py-rattler` | 0.22.0 → 0.25.0 | `conda-smithy`'s `depends: py-rattler>=0.22,<0.23` |
| `pixi-to-conda-lock` | 0.4.3 → 0.4.5 | transitively via `py-rattler` above (0.4.5 needs `py-rattler>=0.24,<0.25`) |
| `setuptools` | 81.0.0 → 84.0.0 | `pytorch`'s `depends: setuptools<82` + `vsts-python-api`'s `depends: setuptools<82.0a0` |
| `bokeh` | 3.9.2 → 3.10.0 | `panel-core`'s `depends: bokeh>=3.7.0,<3.10.0` |
| `ruamel.yaml` | 0.18.17 → 0.19.1 | `conda`'s own `depends: ruamel.yaml>=0.11.14,<0.19` |

### 🟠 Platform/upstream-support gap — verified, no local fix, just wait

| Package | Locked → Latest | Gap |
|---|---|---|
| `pyarrow` / `pyarrow-all` | 24.0.0 → 25.0.0 | `pyarrow-core 25.0.0`'s osx-arm64 build needs `python<3.14` or an unreachable `libabseil` window (solver-verified) |
| `speechrecognition` | 3.10.4 → 3.17.0 | 3.17.0's own build declares `python>=3.10,<3.13` — no py3.14 build yet |

### ⚪ Undiagnosed — checked, real blocker not found in this pass

| Package | Locked → Latest | Note |
|---|---|---|
| `diffusers` | 0.39.0 → 0.40.0 | own deps look satisfiable; blocker not identified |
| `conda` | 26.5.0 → 26.7.1 | py3.14 build exists, no offending cap found; small delta, low priority |

### 🔵 Transitive-only — solver/repodata-verified, 93 packages, every row a real finding

Verified this session (continued from the request to make the book of work accurate): for every one of the 93, either (a) a package *currently in our lock* declares a `depends`/`constrains` spec that excludes the latest version (`BLOCKED-BY-EXISTING-PIN`), or (b) the target's own newest build introduces a *new* requirement that conflicts with something already locked (`NEW-BUILD-CONFLICTS-WITH-LOCKED`). Every finding was then **traced through its full chain** to a terminal package, and every terminal package was independently checked — **all of them are already at their own conda-forge latest**, confirming these are genuine upstream compatibility caps (the fix is that package's own next release), not stale locks or local misconfiguration.

### Sprint priority — fix one upstream package, unblock N

Sorted by blast radius. This is the actual actionable list: checking (or filing against) **one** terminal package's feedstock clears every row underneath it.

| Terminal package (check/file upstream) | Unblocks | Packages |
|---|---|---|
| `aws-sdk-cpp` | 13 | `aws-c-auth`, `aws-c-cal`, `aws-c-common`, `aws-c-compression`, `aws-c-event-stream`, `aws-c-http`, `aws-c-io`, `aws-c-mqtt`, `aws-c-s3`, `aws-c-sdkutils`, `aws-checksums`, `aws-crt-cpp`, `s2n` |
| `conda-lock` | 3 | `dulwich`, `hatch`, `virtualenv` |
| `getdaft` | 3 | `fsspec`, `pins`, `tqdm` |
| `leptonica` | 3 | `giflib`, `libdeflate`, `libgdal-core` |
| `omegaconf` | 2 | `antlr-python-runtime`, `python_abi` |
| `libavif16` | 2 | `aom`, `dav1d` |
| `dagster` | 2 | `coloredlogs`, `grpcio-health-checking` |
| `coderedcms` | 2 | `django-bootstrap5`, `icalendar` |
| `wagtail` | 2 | `django-treebeard`, `draftjs_exporter` |
| `instructor` | 2 | `jiter`, `openai` |
| `graphifyy` | 2 | `tree-sitter-julia`, `tree_sitter` |
| `at-spi2-atk` | 1 | `at-spi2-core` |
| `azure-identity-cpp` | 1 | `azure-core-cpp` |
| `libmamba` | 1 | `fmt` |
| `click` | 1 | `huggingface_hub` |
| `opentelemetry-api` | 1 | `importlib-metadata` |
| `lumen` | 1 | `intake` |
| `kedro-viz` | 1 | `ipython` |
| `pngquant` | 1 | `libimagequant` |
| `markitdown` | 1 | `magika` |
| `great-expectations` | 1 | `marshmallow` |
| `liblief` | 1 | `mbedtls` |
| `mupdf` | 1 | `mesalib` |
| `vsts-python-api` | 1 | `msrest` |
| `apptainer` | 1 | `openssl` |
| `a2a-sdk` | 1 | `protobuf` |
| `conda-oci-mirror` | 1 | `oras-py` |
| `pixi-build-cmake` | 1 | `pixi-build-api-version` |
| `libmambapy` | 1 | `pybind11-abi` |
| `playwright-python` | 1 | `pyee` |
| `graphviz2drawio` | 1 | `svg.path` |
| `bleach` | 1 | `tinycss2` |
| `matplotlib-base` | 1 | `tk` |
| `google-genai` | 1 | `websockets` |

Full per-package detail (locked → latest, terminal blocker):

| Package | Locked | Latest | Blocked by (terminal, already at ITS OWN latest) |
|---|---|---|---|
| `aws-c-auth` | 0.10.4 | 0.10.5 | `aws-sdk-cpp` |
| `aws-c-cal` | 0.9.14 | 0.9.15 | `aws-sdk-cpp` |
| `aws-c-common` | 0.14.2 | 0.14.5 | `aws-sdk-cpp` |
| `aws-c-compression` | 0.3.2 | 0.3.3 | `aws-sdk-cpp` |
| `aws-c-event-stream` | 0.7.1 | 0.7.2 | `aws-sdk-cpp` |
| `aws-c-http` | 0.11.0 | 0.11.1 | `aws-sdk-cpp` |
| `aws-c-io` | 0.27.3 | 0.27.7 | `aws-sdk-cpp` |
| `aws-c-mqtt` | 0.16.0 | 0.16.2 | `aws-sdk-cpp` |
| `aws-c-s3` | 0.12.8 | 0.13.1 | `aws-sdk-cpp` |
| `aws-c-sdkutils` | 0.2.7 | 0.2.10 | `aws-sdk-cpp` |
| `aws-checksums` | 0.2.10 | 0.2.11 | `aws-sdk-cpp` |
| `aws-crt-cpp` | 0.40.1 | 0.43.5 | `aws-sdk-cpp` |
| `s2n` | 1.7.5 | 1.7.8 | `aws-sdk-cpp` |
| `dulwich` | 0.24.10 | 1.2.10 | `conda-lock` |
| `hatch` | 1.16.3 | 1.17.1 | `conda-lock` |
| `virtualenv` | 20.39.0 | 21.7.7 | `conda-lock` |
| `fsspec` | 2026.4.0 | 2026.7.0 | `getdaft` |
| `pins` | 0.9.0 | 0.9.1 | `getdaft` |
| `tqdm` | 4.67.3 | 4.70.0 | `getdaft` |
| `giflib` | 5.2.2 | 6.1.3 | `leptonica` |
| `libdeflate` | 1.25 | 1.26 | `leptonica` |
| `libgdal-core` | 3.13.2 | 3.13.3 | `leptonica` |
| `antlr-python-runtime` | 4.9.3 | 4.13.2 | `omegaconf` |
| `python_abi` | 3.14 | 3.15 | `omegaconf` |
| `aom` | 3.14.1 | 3.15.0 | `libavif16` |
| `dav1d` | 1.2.1 | 1.5.4 | `libavif16` |
| `coloredlogs` | 14.0 | 15.0.1 | `dagster` |
| `grpcio-health-checking` | 1.78.1 | 1.83.0 | `dagster` |
| `django-bootstrap5` | 25.2 | 26.3 | `coderedcms` |
| `icalendar` | 6.3.2 | 7.3.0 | `coderedcms` |
| `django-treebeard` | 5.3.0 | 7.0.1 | `wagtail` |
| `draftjs_exporter` | 5.2.0 | 7.1.0 | `wagtail` |
| `jiter` | 0.11.1 | 0.16.0 | `instructor` |
| `openai` | 2.53.0 | 3.6.0 | `instructor` |
| `tree-sitter-julia` | 0.23.1 | 0.25.0 | `graphifyy` |
| `tree_sitter` | 0.25.2 | 0.26.0 | `graphifyy` |
| `at-spi2-core` | 2.40.3 | 2.58.3 | `at-spi2-atk` |
| `azure-core-cpp` | 1.16.3 | 1.16.4 | `azure-identity-cpp` |
| `fmt` | 12.1.0 | 12.2.0 | `libmamba` |
| `huggingface_hub` | 1.16.1 | 1.29.0 | `click -> conda-recipe-manager==8.2.1` |
| `importlib-metadata` | 8.7.1 | 9.0.1 | `opentelemetry-api` |
| `intake` | 0.7.0 | 2.0.9 | `lumen` |
| `ipython` | 8.37.0 | 9.17.0 | `kedro-viz` |
| `libimagequant` | 2.17.0 | 4.4.1 | `pngquant` |
| `magika` | 0.6.2 | 1.0.3 | `markitdown` |
| `marshmallow` | 3.26.2 | 4.3.1 | `great-expectations` |
| `mbedtls` | 3.6.3.1 | 4.2.0 | `liblief` |
| `mesalib` | 26.1.6 | 26.2.1 | `mupdf` |
| `msrest` | 0.6.21 | 0.7.1 | `vsts-python-api` |
| `openssl` | 3.6.4 | 4.0.1 | `apptainer` |
| `protobuf` | 6.33.5 | 7.35.1 | `a2a-sdk` (also independently capped `<7` by `dagster`) |
| `oras-py` | 0.1.14 | 0.2.43 | `conda-oci-mirror` |
| `pixi-build-api-version` | 7 | 12 | `pixi-build-cmake` |
| `pybind11-abi` | 11 | 12 | `libmambapy` |
| `pyee` | 13.0.1 | 14.0.0 | `playwright-python` |
| `svg.path` | 6.3 | 7.1 | `graphviz2drawio` |
| `tinycss2` | 1.4.0 | 1.5.1 | `bleach` |
| `tk` | 8.6.13 | 9.0.4 | `matplotlib-base` |
| `websockets` | 16.1.1 | 17.1 | `google-genai` |

### Same-recipe-family — needs a coordinated version bump, not an upstream fix (28 packages)

These aren't blocked by a single named upstream bug — they're siblings from the same
multi-output recipe or a deliberately lockstep-versioned pair, and just need bumping together
once the real blocker clears.

| Package | Locked | Latest | Real blocker |
|---|---|---|---|
| `google-cloud-bigquery-storage` | 2.38.0 | 2.41.0 | google-cloud-bigquery-storage-core sibling pair |
| `google-cloud-bigquery-storage-core` | 2.38.0 | 2.41.0 | google-cloud-bigquery-storage sibling pair |
| `httpcore2` | 2.5.0 | 2.12.0 | httpx2 lockstep pair (a real conda-forge fork/rename pair this repo consumes — both builds already exist at 2.12.0, nothing external blocks either; just needs a coordinated bump) |
| `httpx2` | 2.5.0 | 2.12.0 | httpcore2 lockstep pair (same note) |
| `libarrow` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-acero` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-compute` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-dataset` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-flight` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-flight-sql` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-gandiva` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libarrow-substrait` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libgoogle-cloud` | 3.6.0 | 3.8.0 | pyarrow platform-gap |
| `libgoogle-cloud-storage` | 3.6.0 | 3.8.0 | pyarrow platform-gap |
| `libparquet` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `libprotobuf` | 6.33.5 | 7.36.0 | pyarrow platform-gap (pulled in transitively by `libarrow`'s own exact pin) |
| `libtorch` | 2.12.0 | 2.13.0 | pytorch sibling pair |
| `pytorch` | 2.12.0 | 2.13.0 | libtorch sibling pair |
| `mesa-lavapipe` | 26.1.6 | 26.2.1 | mesalib sibling |
| `mesa-llvmpipe` | 26.1.6 | 26.2.1 | mesalib sibling |
| `microsoft-kiota-abstractions` | 1.10.1 | 1.12.0 | microsoft-kiota closure siblings |
| `microsoft-kiota-authentication-azure` | 1.10.1 | 1.12.0 | microsoft-kiota closure siblings |
| `microsoft-kiota-http` | 1.10.1 | 1.12.0 | microsoft-kiota closure siblings |
| `msgraph-core` | 1.4.0 | 1.5.1 | microsoft-kiota closure siblings |
| `orc` | 2.3.0 | 2.3.1 | pyarrow platform-gap |
| `pyarrow-core` | 24.0.0 | 25.0.0 | pyarrow platform-gap |
| `pybind11` | 3.0.4 | 3.1.0 | pybind11-global sibling pair |
| `pybind11-global` | 3.0.4 | 3.1.0 | pybind11 sibling pair |

**`grpcio` / `grpcio-status` / `libgrpc` / `libabseil` (4 packages) — a genuine ecosystem
version-diamond, not a single-package fix.** These don't collapse to one terminal package the
way the rest of this table does. `grpcio 1.83.0`'s own build requires `libabseil
>=20260526.0,<20260527.0a0`; separately, `protobuf 6.33.5` (itself capped `<7` by both
`a2a-sdk` and `dagster` — see the sprint-priority table above) requires `libabseil
>=20260107.1,<20260108.0a0` — two different consumers wanting two different, non-overlapping
`libabseil` windows at once. Even resolving the `protobuf<7` cap wouldn't automatically clear
this: `grpcio`/`protobuf`'s release trains would also need to land on a *shared* `libabseil`
window simultaneously. This is the same shape as the `G97`-class "ERA DIAMOND between ecosystem
pin epochs" already documented in the conda-forge-expert skill (`SKILL.md`) — the fix is
upstream convergence across multiple release trains, not a single feedstock PR.

| Package | Locked | Latest |
|---|---|---|
| `grpcio` | 1.78.1 | 1.83.0 |
| `grpcio-status` | 1.78.1 | 1.83.0 |
| `libgrpc` | 1.78.1 | 1.83.0 |
| `libabseil` | 20260107.1 | 20260817.0 |

### Tradeoff — not a bug, a deliberate non-upgrade (2 packages)

Bumping these would force *downgrading* something we're deliberately keeping newer. No feedstock fix applies; the call is whether the tradeoff is worth revisiting.

| Package | Locked | Latest | What it would cost |
|---|---|---|---|
| `azure-core` | 1.38.2 | 1.41.0 | flask (azure-core wants flask 2.2.5, we run 3.1.3) |
| `db-dtypes` | 1.4.3 | 1.7.1 | numpy (db-dtypes wants numpy<=2.2.6, we run 2.5.2) |

## The channel-sourcing debt ledger

A third shape of the same problem: every active dependency that does NOT come from
conda-forge is a standing bet that a non-default channel or a bare PyPI wheel keeps
working — currency debt exactly like the two ledgers above, just on the *source* axis
instead of the *version* axis. Verified against `pixi.lock`'s own resolved URLs (ground
truth — not `pixi.toml`'s comments, which describe availability/history and can lag what
actually got locked), not inferred from intent.

### SelfExplainML-channel packages (30, all locally authored)

Every one of the 30 packages `pixi.lock` actually resolves from the `SelfExplainML`
channel has a `recipes/<name>/` in this repo — none is a third-party channel dependency
we don't control, but every one is a conda-forge submission still in flight (or, for a
few, permanently out of reach of conda-forge by construction). Grouped by area, with each
recipe's own `cfe-on-conda-forge-status`:

| Area | Packages | Status |
|---|---|---|
| BMAD suite tooling | `bmad-builder`, `bmad-creative-intelligence-suite`, `bmad-dashboard`, `bmad-method-test-architecture-enterprise`, `bmad-method-wds-expansion`, `bmad-module-skill-forge`, `bmad-module-template`, `bmad-utility-skills`, `mybmad-dashboard` | `pending-approval-on-conda-forge` |
| BMAD suite tooling | `bmad-labs-skills`, `bmad-loop`, `bmad-manticore` | `pending-submission-to-conda-forge` |
| Token-economy instruments (§ see "What is real" above / [[marshal-token-economy]]) | `caveman` | `pending-submission-to-conda-forge` |
| Token-economy instruments | `codegraph` | `pending-approval-on-conda-forge` |
| MCP tooling | `fastmcp` | `confirmed-on-conda-forge` — **check needed**: still resolving from SelfExplainML despite the metadata; per `pixi.toml`'s own comment, conda-forge tops out at `3.4.7` (hard-requires `mcp<2.0`) while this env pins `>=4.0.0b5` — the recipe metadata likely describes the OLD `<=3.4.7` package, not the `>=4.0` build actually locked |
| MCP tooling | `fastmcp-slim` | no status field recorded |
| Kedro tooling | `kedro-mcp` | `pypi-only` — describes the *upstream* package (no conda-forge feedstock exists for it at all); this repo's own recipe packages a locally source-patched fork (swaps the `fastmcp` import for the official `mcp` SDK) that has no upstream conda-forge counterpart to converge toward |
| Kedro tooling | `kedro-skills` | no status field recorded |
| Enterprise/deploy | `liquibase`, `liquibase-postgresql` | no status field recorded (vendored JDBC per `pixi.toml`'s own comment) |
| Enterprise/deploy (OpenFeature) | `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`, `openfeature-sdk` | `pending-submission-to-conda-forge` — OpenFeature is absent from conda-forge AND anaconda.org entirely (Grounding 2026-08-24 ruling in [[pyforge-unifying-strategy]]); this is the closest any of these four will get until conda-forge itself gains the feedstocks |
| Presentation/deck tooling | `ppt-master`, `pptxgenjs`, `pptxgenjs-plus`, `vizro-e2e-flow` | `pending-submission-to-conda-forge` |
| Misc | `panzi-json-logic` | `pending-submission-to-conda-forge` |
| Misc | `slowapi` | `confirmed-on-conda-forge` — **same check needed as `fastmcp`**: still locked from SelfExplainML despite the metadata; `pixi.toml`'s own comment names a specific `0.1.10` SelfExplainML build as expected in the lock, so this is very likely a version/channel-priority nuance (SelfExplainML's build satisfies a constraint conda-forge's doesn't) rather than a stale field — worth a real re-check, not a guess |

**What this actually means:** 25 of 30 are genuinely "our own packaging work, not yet
merged upstream" — the fix path is finishing the staged-recipes submission each already
has in flight, same lifecycle every other recipe in this repo follows. The 4 OpenFeature
packages and the whole BMAD-suite family are the closest thing to *permanent* SelfExplainML
residents in this list — OpenFeature by a documented upstream absence, BMAD-suite tooling
because it's a thin npm/npx wrapper ecosystem unlikely to ever grow conda-forge feedstocks
of its own. `kedro-mcp` is permanent for a different reason: the package itself is a
local fork with no upstream to converge toward. The 2 `confirmed-on-conda-forge` outliers
(`fastmcp`, `slowapi`) are the one genuinely open question in this table — each needs a
real repodata check (which exact version conda-forge ships today vs. what this env's
`pixi.toml` constraint actually requires), not an assumption that the field is simply
stale.

### Bare-PyPI dependency (1)

`[feature.vuln-db.pypi-dependencies]` carries exactly one active entry:
**`appthreat-vulnerability-db`** (multi-source CVE DB — NVD/GHSA/OSV/npm/Snyk), pulled
directly from PyPI with no conda-forge equivalent at all. This is the CVE-scanning engine
behind `vdb-refresh`/`cve-watcher`, not a candidate for conda packaging in this pass — its
own dependency tree (multiple scanner backends) makes it a poor fit for a single conda
recipe, and nothing else in this repo needs the exact same debt this dependency creates.
The commented-out `crewai` line in the same table is not live debt — it's a dormant
placeholder for a package already tracked in the candidate ledger's own "unexamined"
bucket above.

## The external-tracking gap ledger

A fourth shape of currency debt, on the *visibility* axis rather than source/version:
which of this environment's active dependencies have no corresponding tracking item on
OpenTeams-WFT-CDO's own conda-forge-packaging project board
(`github.com/orgs/OpenTeams-WFT-CDO/projects/1`, "OSS Enhancements (Conda Forge, Pixi,
ect)" milestone — that org's own `[Conda-Forge Packaging] <name>` / `Add <name> to
conda-forge` / `Build <name> vX on conda-forge` title conventions). Verified 2026-08-31:
extracted 1309 distinct tracked names from that milestone's ~1332 items, parsed all 335
active `pixi.toml` dependency keys via `tomllib`, cross-referenced. **197 of 335 are not
tracked there.** After excluding base conda/pixi ecosystem infra (52 — `conda`, `pixi`,
`python`, `conda-build`, `rattler-build`, the `pixi-*` plugin family, system tools like
`gh`/`tmux`/`nodejs`/`postgresql`) and this repo's own `pyforge-*` packages (10, not
third-party OSS), **135 remain as genuine candidates**:

- **108 with a local `recipes/<name>/`** — real packaging debt this repo already did the
  work for, invisible to that tracker: `bmad-labs-skills`, `bmad-loop`, `bmad-manticore`,
  `bmad-module-skill-forge`, `bokeh-django`, `boring-semantic-layer`, `caveman`,
  `channels`, `cocoindex`, `codegraph`, `coderedcms`, `cookiecutter`, `copier`,
  `cyclonedx-bom`, `cyclonedx-python-lib`, `dagster`, `dagster-webserver`, `daphne`,
  `dask-core`, `dbt-duckdb`, `deptry`, `diffusers`, `django-anymail`, `django-appconf`,
  `django-compressor`, `django-ipware`, `django-lasuite`, `django-mcp-server`,
  `django-model-utils`, `djlint`, `dlt`, `duckdb-server`, `elevenlabs`, `fido2`,
  `frozendict`, `github-copilot-sdk`, `graphifyy`, `great-expectations`, `headroom-ai`,
  `httpx2`, `ibis-framework`, `import-linter`, `ipdb`, `jinja2-ospath`, `kedro`,
  `kedro-dagster`, `kedro-datasets`, `kedro-mcp`, `kedro-skills`, `kedro-viz`,
  `langchain-chroma`, `langflow`, `liquibase`, `liquibase-postgresql`, `mammoth`,
  `markitdown`, `marp-cli`, `mermaid-py`, `mlx`, `mlx-lm`, `moto`, `msgraph-sdk`,
  `mybmad-dashboard`, `nbqa`, `ocrmypdf`, `odfpy`, `office2pdf`, `ollama-python`,
  `openfeature-flagd-api`, `openfeature-flagd-core`, `openfeature-provider-flagd`,
  `openfeature-sdk`, `openlineage-python`, `opentelemetry-instrumentation-psycopg`,
  `osv-scanner`, `pandera`, `pandoc`, `panel`, `panel-graphic-walker`, `pdf2image`,
  `pip-audit`, `playwright-python`, `pptxgenjs`, `pptxgenjs-plus`, `psycopg2`, `pyrefly`,
  `pyright`, `python-build`, `python-graphviz`, `qrcode`, `rank-bm25`, `rcssmin`,
  `redis-py`, `rjsmin`, `ruamel.yaml`, `sentencepiece`, `spec-kit`, `speechrecognition`,
  `sphinx-autobuild`, `tablib`, `truststore`, `twine`, `uvicorn-worker`, `vizro`,
  `vizro-ai`, `vizro-e2e-flow`, `vizro-mcp`, `wagtail`.
- **27 with no local recipe** — genuinely unverified, several plausibly already fine on
  conda-forge with no packaging needed at all (`pgvector`, `llama.cpp`, the `ibis-*`
  backend family) rather than real debt: `age`, `cachebox`, `channels-redis`,
  `claude-agent-acp`, `cruft`, `d2`, `dagster-pipes`, `dbgpt`, `dbgpt-app`, `dbgpt-serve`,
  `fasta2a`, `go-sops`, `graphviz2drawio`, `ibis-duckdb`, `ibis-mssql`, `ibis-oracle`,
  `ibis-polars`, `ibis-postgres`, `ibis-sqlite`, `llama.cpp`, `lumen-ai-anthropic`,
  `mcp-types`, `nebi-cli`, `pdfminer.six`, `pgvector`, `pyarrow-all`, `pydantic-ai`.

**This is a visibility gap, not a packaging verdict.** A package missing from OpenTeams'
board is not necessarily un-packaged or blocked — the 108-with-recipe bucket already has
its own disposition in the ledgers above (most `pending-*` on conda-forge already); this
ledger only says that disposition isn't mirrored onto that external tracker. Whether it
should be is an operator call, not something this Dream decides unilaterally per package.

## Constraints

- **A `blocked` disposition must name what would unblock it**, not just that it's blocked —
  the difference between this ledger and the status quo is exactly that a re-check has a
  trigger instead of requiring someone to remember to look.
- **Don't re-derive a shared root cause per package.** `headroom-ai` and the `dbt-*` trio are
  one investigation, not four.
- **Trust local `cfe-*` metadata as a hint, not ground truth** — the `langflow` entry above is
  the live proof it can drift stale within a single session's own timeframe.
- **A `blocked`-vs-`platform-gap` disposition for an active dependency must name the exact
  upstream package + spec**, read off the actually-resolved build's own `depends`/`constrains` —
  never "something conflicts." `platform-gap` findings need solver verification (an actual
  bumped-floor solve, as done for `pyarrow`), not just "conda-forge has a newer version" — a
  package can be behind latest for reasons that have nothing to do with platform support.

## Non-goals

- **Not a commitment to add any specific package**, and not a commitment to unblock any specific
  active dependency — this Dream separates "safe to try" from "blocked" from "dead" on the
  candidate side, and "deliberate" from "blocked" from "platform-gap" from "undiagnosed" on the
  currency side; several blockers are pinned deliberately elsewhere for good reasons
  (`conda-smithy<4`) and unblocking their symptoms may not be worth the tradeoff — that stays a
  separate call per finding.
- **Not re-litigating conda-forge submission strategy** for the recipes already
  `pending-approval`/`pending-submission` — that's the recipes' own `cfe-on-conda-forge-status`
  lifecycle, tracked per-recipe already.
- **Not a commitment to actually fix any of the 33 terminal-package findings** — each is
  evidence-verified (a real `depends`/`constrains` spec, a real conflicting requirement, a real
  confirmed-at-latest terminal), which is different from deciding it's worth an upstream issue
  or a local workaround. That triage stays a separate call per finding, same as the candidate
  ledger's own non-goal above.
- **A verified finding that later turns out wrong belongs in this same ledger as a correction**,
  not a silent re-derivation — the whole point of naming the exact evidence (which package,
  which spec, which build) is that it can be checked and, if wrong, fixed in place.

## Kinships

[[chain-currency-sweep]] (the same "re-derive, don't decay" discipline, applied to a dependency
ledger instead of a planning-spine chain) · [[pyforge-doctor-dependency-health]] (archived, but
the closest prior framing of "every dependency gets a tracked health disposition" — this Dream
is narrower and repo-local rather than factory-wide)

## Realization log

- **2026-08-30** — Dream captured directly from a live audit: all 64 commented-out lines in
  `pixi.toml` enumerated, cross-referenced against `recipes/` (37 of 44 packages already have a
  local recipe — more than expected going in), and each existing recipe's own `cfe-*` metadata
  pulled where present. Six packages got a *fully verified* disposition this session
  (`ppt-master`, `codegraph` added; `headroom-ai`, `caveman`, `dbt-core`/`dbt-duckdb`/
  `dbt-postgres` root-caused as blocked; `ocrmypdf` reconfirmed; `pngquant`'s own separate
  cross-compile bug fixed upstream). The rest are triaged by disposition but not individually
  re-verified in this pass — that re-verification is the Dream's own future work, not assumed
  done. **Owner picked as `doctor`** (dependency/environment-health framing, advisory not
  gating) as the best fit among the eight-station enum; this is a repo-local housekeeping
  concern rather than a PyForge Guild product, so the fit is imperfect — correct trivially if
  another owner reads better.
- **2026-08-30 (same session, continued)** — folded in the mirror-image half: a full
  version-currency audit of ACTIVE `local-recipes` dependencies (originally drafted as a
  separate sibling Dream, then merged in here on request — "this is all related to currency").
  Parsed `pixi.lock` (1147 packages), diffed against fresh conda-forge repodata (149 behind
  latest), used `pixi update --dry-run` as the oracle to separate stale-lock (38) from
  genuinely-capped (111), then built a reverse-dependency index from actually-resolved builds'
  own `depends`/`constrains` to name real culprits instead of guessing. 8 packages got a fully
  verified root cause (collapsing to 6 upstream culprits, one of which — `conda-recipe-manager
  ==8.2.1` — turned out to be the SAME root cause already blocking `headroom-ai`/`dbt-*` on the
  candidate side, confirming this really is one Dream). One platform-gap hypothesis
  (`pyarrow-core` on osx-arm64) was confirmed with a real solver test (temporary floor bump,
  reverted after — nothing left in the manifest).
- **2026-08-30 (same session, continued again)** — the remaining 93 were left as unconfirmed
  cluster hypotheses; asked to verify them so the book of work is accurate before treating any
  of it as sprint-ready. Built a verifier reusing the already-downloaded repodata (no new network
  calls): for each of the 93, checked whether a currently-locked package's own
  `depends`/`constrains` excludes the latest version, and where none did, checked whether the
  target's own newest build introduces a new requirement conflicting with something already
  locked — 79 hit the first check, 14 the second, **zero came back with no explanation**. Every
  finding was then traced through its full blocking chain to a terminal package (recursively —
  e.g. `s2n → aws-c-io → aws-c-auth → aws-c-s3 → aws-crt-cpp → aws-sdk-cpp`), and every one of
  those terminals was independently confirmed to already be at ITS OWN conda-forge latest —
  ruling out "just needs `pixi update`" as an explanation for any of them. Result: 59 packages
  trace to 34 distinct terminal packages (sorted by blast radius — `aws-sdk-cpp` alone explains
  13 of the 59), 28 turned out to be same-recipe-family siblings (needing a coordinated version
  bump, not an upstream fix — folded into the `pyarrow`/kiota/etc. findings already on record)
  rather than independent findings, and 2 are deliberate tradeoffs (upgrading would force
  downgrading `flask`/`numpy`, which we don't want). One sub-finding required a second pass: the
  first draft mis-collapsed `grpcio`/`grpcio-status`/`libgrpc`/`libabseil` into the same-family
  bucket under a dangling "(see below)" that never resolved — re-checked their real evidence and
  reclassified as a genuine 4-package multi-producer ecosystem version-diamond (`grpcio 1.83.0`
  and `protobuf 6.33.5` want non-overlapping `libabseil` windows simultaneously; `protobuf`
  itself traces to `a2a-sdk`, now correctly counted among the 34 terminals) — a real, distinct
  finding, not a single-package fix, called out explicitly rather than hidden inside a table
  note. The hypothesis-only language was removed from every section that referenced it.
- **2026-08-31** — Added the third ledger, channel-sourcing debt: operator direction that
  packages depending on SelfExplainML or bare PyPI "are also currency / workarounds and
  debt." Queried `pixi.lock`'s own resolved URLs (ground truth, not `pixi.toml` comments)
  for every package actually served from SelfExplainML — 30 found, cross-checked against
  `recipes/` (all 30 have a local recipe — none is a third-party channel risk, all are our
  own in-flight conda-forge submissions) and each recipe's own `cfe-on-conda-forge-status`.
  25 are `pending-*`, 4 (OpenFeature) and the BMAD-suite family are effectively permanent
  SelfExplainML residents (documented upstream absence / thin npm-wrapper ecosystem), 1
  (`kedro-mcp`) is permanent for a different reason (a local fork with no upstream to
  converge toward), and 2 (`fastmcp`, `slowapi`) are flagged `confirmed-on-conda-forge` yet
  still lock from SelfExplainML — a real open question (likely a version/constraint
  mismatch between the recipe metadata and what's actually locked), not resolved in this
  pass. Also found the one active bare-PyPI dependency (`appthreat-vulnerability-db`, no
  conda-forge equivalent) and confirmed the commented-out `crewai` pypi-dependencies line
  is dormant, not live debt (already tracked in the candidate ledger's own "unexamined"
  bucket).
- **2026-08-31 (same session, continued)** — added the fourth ledger, external-tracking
  gap: cross-referenced all 335 active `pixi.toml` packages against OpenTeams-WFT-CDO's
  own conda-forge-packaging project board (1309 tracked names extracted from its "OSS
  Enhancements" milestone). 197 untracked; after excluding base conda/pixi infra and this
  repo's own `pyforge-*` packages, 135 genuine candidates remain — 108 with a local
  recipe already (real packaging debt invisible to that tracker) and 27 without one
  (unverified; several plausibly already fine on conda-forge with no debt at all). Framed
  explicitly as a visibility gap, not a packaging verdict — this Dream doesn't decide
  per-package whether external tracking is warranted.
