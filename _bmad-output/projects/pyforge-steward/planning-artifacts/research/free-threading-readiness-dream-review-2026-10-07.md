---
chain: pyforge-steward
created: 2026-10-07
updated: 2026-10-07
status: final
type: dream-review
title: "Free-threading readiness per platform: independent Dream review"
companion: "docs/dreams/pyforge-steward.md (2026-10-06 entries: free-threading readiness; BLAS per target)"
ruling: "2026-10-07 operator rulings, taken during this review and recorded on the Dream entry: on-demand decision read; Level 1 computed, not tracked; Level 2 operator-run and PR-landed; pin python-gil estate-wide now"
---

# Independent review: free-threading readiness per platform (steward Dream, 2026-10-06)

- **Reviewer:** an independent session (AGENTS.md guideline 8). The prior review, `32ba071e73`, was
  written by the session that authored the entry and folded into it; this one was not.
- **Reviewed:** `docs/dreams/pyforge-steward.md` lines 560-792 at `a96e07c280` (the free-threading
  entry and the BLAS entry).
- **Read against:** AGENTS.md; `spec-pyforge-steward` (SPEC.md, PRD, spine, epics); `pixi.toml` and
  `pixi.lock`; the steward `provision` duty; the detectors aggregator and `detectors.yml`;
  `.github/actions-policy.toml`; the atlas and conda-forge-expert channel readers; marshal's
  cross-surface gate; the library catalog and its checker; the Python 3.14 release notes and
  free-threading howto; PEP 779 and PEP 803; conda-forge's `python314t` migrator and its status feed.
- **Method:** three parallel read-only sweeps of the estate, two lock-parsing scripts (reproduced
  below), five web reads, and four operator questions answered in session.

## Verdict

The aspiration is right and steward-owned. The 2026-10-06 baseline measurement is sound. The
mechanism around it is over-built for the estate as it stands. Five facts the entry does not know
change its shape:

1. A free-threaded interpreter is already in the tracked lock.
2. No estate reader can feed the Level 1 metadata match.
3. Scheduled CI is switched off repo-wide.
4. `detectors-ci` cannot red anything without a dedicated blocking step, and the closest WARN analog
   is stale today.
5. abi3 packages can never run on 3.14t.

With the operator's four answers, v1 collapses to one on-demand read built on `pixi lock`, a
`python-gil` pin fix, and an operator-run native probe. Three cross-station twins (marshal rule,
atlas reader, catalog field) disappear.

## Operator answers (2026-10-07)

| Question | Answer |
|---|---|
| First CAP outcome | On-demand decision read: readiness is a read, no environment moves |
| Level 1 shape | Compute on demand: no tracked file, no staleness detector (ruling 1 dissolves) |
| Level 2 transport | Operator-run, PR-landed; scheduled CI is a later story blocked on `.github/actions-policy.toml` (ruling 2) |
| Accidental `cp314t` | Pin `python-gil` estate-wide now, as a fix story |

Ruling 3 (probe subset) is recommended below as derived, not declared.

## A. Facts the entry gets wrong or does not know

### A1. The lock already carries a free-threaded interpreter

`pyforge-testing-kit` on `osx-arm64-min` resolves to `python-3.14.7-h6f66cd8_6_cp314t`,
`libpython-3.14.7-he655c36_6_cp314t` and `python_abi-3.14-9_cp314t` (`pixi.lock:19643-19665`),
with `cffi-2.1.1-py314hd9eca70_3` and `cryptography-50.0.1-py314h4bc2b79_1` resolved as `*_cp314t`
builds (`pixi.lock:49481`, `:49756`). The same environment's linux-64 and win-64 blocks use the
GIL build.

Cause: `[feature.pyforge-testing-kit.dependencies]` (`pixi.toml:3086-3095`) declares no `python`
spec, the environment is `no-default-feature`, and nothing in `pixi.toml` pins `python-gil` (zero
hits). The solver was free to pick the free-threaded variant and did. It has been in the lock since
at least `9de381a01e` (2026-08-14).

The entry says "No `python-freethreading` environment exists in `pixi.toml`" (true of the manifest,
false of the lock) and lists `pyforge-testing-kit` among the environments with "no blocker" without
noticing that the solver already proved that on one platform. The baseline's "pure name-level"
caveat does not cover this; the generator must never assume a locked interpreter is a GIL build.

Prior art the entry should cite: red-team finding D-5 (2026-09-02,
`research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md:191`) already called
the estate's free-threading claims overstated; the DW-RT row is `promoted` and Story 44.2 carries
the doc fix.

### A2. abi3 is a missing status

`_python_abi3_support-1.0-hd8ed1ab_3` depends on `cpython` and `python-gil`
(`pixi.lock:32653-32658`), so every abi3-built package is unsolvable under `python-freethreading`
by construction. Independently, the stable ABI is unsupported on free-threaded builds until 3.15's
`abi3t` (PEP 803). In the lock today there are 35 abi3 package names: `cryptography`, `hf-xet`,
`watchfiles`, `wcwidth`, `pynacl`, `pyzmq`, `py-rattler`, `py-rattler-build`, `polars-runtime-32`,
`cocoindex`, `nh3`, `uuid-utils`, `vl-convert-python`, `skia-pathops`, `ast-serialize` and twenty
`tree-sitter-*` grammars. `pyforge-guild` carries 6 on every platform (`ast-serialize`,
`cryptography`, `hf-xet`, `python-abi3`, `watchfiles`, `wcwidth`), `local-recipes` 35, `platform-dev` 8.

The ladder's `not-installable` would lump these with "no `cp314t` build yet" and send Mason after
feedstocks that cannot ship one on 3.14. The read needs an `abi3` status: blocked by the
interpreter version, remediable only by a `cp314t`-specific variant of the feedstock or by 3.15.

### A3. Blocker remediation is an allowlist, not a build

conda-forge's `python314t.yaml` migrator (conda-forge-pinning-feedstock,
`recipe/migrations/python314t.yaml`) is `longterm`, opt-in through an allowlist, limited to 20 open
PRs, and depends on the `python314` migrator. The status feed
(`regro/cf-graph-countyfair`, `status/migration_json/python314t.json`) shows `pyyaml`, `markupsafe`,
`pyarrow`, `protobuf`, `tokenizers`, `numpy`, `pandas`, `psycopg2` and `pydantic-core` not in the
migration at all, and `onnxruntime` dirty (its PR #210, 2026-09-18).

So "Mason prepares the feedstock change that publishes a `cp314t` build" is mostly wrong. The fix
path has three classes: a pinning-feedstock allowlist entry; the migrator bot's own PR on an
allowlisted feedstock; and, in-tree, `recipes/orjson/recipe.yaml:17` carries `skip: is_freethreading`
while `conda_build_config.yaml:1005` sets `is_freethreading: [false]`, so the estate's own factory
never builds a `t` variant. The report should name the class with the package and platform. The
operator's rule stands: no feedstock, staged-recipes, pinning or upstream PR without an explicit ask.

### A4. Counts, re-derived from the lock

- `[environments]` has 35 names; `default` is an alias of `pyforge-guild`. The entry says 36.
- Compiled package names per platform (any record with a `python_abi` dependency, interpreter
  packages removed): linux-64 153, osx-arm64 136, win-64 119. The entry's 154 / 120 / 137 sit within
  its stated "python itself removed by hand" caveat; the generator's own figures become the reference.
- `pyforge-guild`: 31 on every platform (matches). `pyforge-core`: 0 on every platform.
- Pure noarch-python records: 945 (the entry's 843 used a different method; neither is load-bearing).
- `sqlite_vec` 0.1.9 is the only platform-specific PyPI wheel (confirmed; three wheels).

### A5. The proposed probe subset probes nothing useful

`mcp-host` is linux-64 only (`pixi.toml:377`), so it cannot be probed on three platforms.
`pyforge-core` has zero compiled packages, so probing it proves nothing. `pyforge-guild` cannot
solve free-threaded today (8 to 9 blockers). The hand list therefore names the least informative
environments plus one that cannot run. Ruling 3 should be derived: every environment whose Level 1
solve succeeded on that platform, filtered by `--env`.

### A6. The `environment.yaml` claim is wrong

Only `-e build` is exported (`.github/workflows/scripts/linter.py:64-80`). A new free-threaded
environment that leaves `[dependencies]`, `feature.python` and `feature.build` alone leaves Check #3
green. The lock-growth objection to tracked probe environments stands; the `environment.yaml` one
does not.

### A7. Release facts worth one line each

PEP 779: free-threaded builds are officially supported in 3.14 (released 2025-10-07). The 3.14
release notes put the single-threaded penalty at 5-10 % depending on platform and compiler; the
free-threading howto gives 1 % (macOS aarch64) to 8 % (x86-64 Linux) on pyperformance. The note's
"2-10 %" is close enough; cite the docs, not the note.

## B. Engine and precedent mismatches

### B1. No existing reader can feed the Level 1 metadata match

- Atlas flattens repodata to `conda_name, version, timestamp, subdir`, dropping `build` and
  `depends` (`pyforge-atlas/.../datasets/core_sources.py:95-116`), reads only
  `current_repodata.json` (`:351`), and its Python-version filter `^\d+\.\d+$`
  (`pipelines/core/nodes.py:24`) rejects `3.14t`.
- Legacy cf_atlas aggregates to one row per package (`conda_forge_atlas.py:1267`);
  `detail_cf_atlas.py:164` keeps builds but reduces to the latest per subdir; `cf_atlas.db` has no
  build column (73 columns, only `conda_subdirs` and `python_min` are related).
- rattler is used once, host-only (`inventory_match.py:730-750`); atlas deliberately avoided the
  sharded protocol.

"Engines are consumed, not authored" cannot be met by the readers the entry names.

**Recommendation (bold): drop the metadata-match check; the solve probe subsumes it.** A throwaway
manifest (the environment's declared set plus `python-freethreading`) run through `pixi lock`
solves all three platforms from one host, reads full sharded repodata itself (no
`current_repodata.json` newest-only gap), and the resulting lock is the per-package evidence:
`*_cp314t` build strings, which packages moved version, and, on failure, the solver's conflict
message naming the package with no `python_abi *_cp314t` build. One engine, already present in
every environment.

### B2. `steward provision --verify` already has a meaning

`--verify` compares `pixi project export conda-environment -e build` with `environment.yaml`
(`provision.py:315-368`); its help text calls it "the PR CI sync gate" (`cli.py:918-920`). Hanging
native Level 2 probes on it overloads a single-host check. Also, `--env NAME` alone installs the
environment (`provision.py:1588-1600`), so a new `--free-threading` flag must sit above `--env` in
`ProvisionDuty.run`'s precedence chain (`:1668-1692`), or `--free-threading --env X` installs X.
The flag list is pinned by `_PROVISION_HELP` and `tests/unit/test_provision_plugin.py:299`; the duty
count (25) is untouched by a flag.

### B3. `detectors-ci` is advisory

The GitHub sweep always exits 0 (`.github/workflows/detectors.yml:27-40, 179-206`); only two
dedicated steps block (`cfe_rebuild_guard_check` at `:216`, doctor `ledger-regression` at `:237`).
"Red in `detectors-ci`" means red in the local `pr-preflight` only. The closest analog, the WARN
`pixi-env-matrix-stale` source (`sources/factory.py:1624-1644`, generator
`scripts/pixi_env_matrix.py`, `lock-sha256=` fingerprint embedded in
`docs/dreams/pyforge-unifying-strategy.md:468`), is stale right now: embedded `5f35632597cd8ebf`,
lock `41d5177298cf4a4b`. That is live proof that a WARN lock-fingerprint check does not keep data
current. Moot under "compute on demand"; if a tracked file ever returns, block through a dedicated
step, never a bare registration.

### B4. Scheduled CI is off, and no runner has pixi on macOS or Windows

`.github/actions-policy.toml:18` sets `enabled = false`; only `staged-recipes-linter` and
`detectors` are allowed back. Every cron is inert (`substrate-nightly`, `herald-live-demo`;
`sync-pypi-mappings` lost its cron after 32 straight failures). `test-macos.yml` and
`test-windows.yml` are miniconda recipe builds, dispatch-only, with no pixi. Three precedents exist
for getting results into the tree: a bot PR (`sync-pypi-mappings.yml:84`, failed), a direct push
(`steward deploy dashboard`, `deploy.py:170-236`), and a release asset with a sha256 manifest
(`substrate-nightly.yml:104-114`). Herald's scheduler is a local crontab by design
(`docs/cli-runbooks.md:296-334`). An operator-run native probe landed by an ordinary PR is the only
path that works today; the scheduled matrix is a `backlog` story blocked on the policy flip.

### B5. Marshal's 22.14 rule table is not "one more row"

`CrossSurfaceRule` lives at `pyforge-marshal/.../core/gate.py:621-707`; path matching is an
`if rule.rule_id ==` chain (`:658-667`); the count is pinned in `tests/unit/test_gate.py:543-546`;
its spec forbids new tasks and new finding codes. It is a marshal story with a twin CAP. Moot under
"compute on demand".

### B6. The library catalog cannot carry structured readiness

`scripts/llms_full_check.py` parses `ENTRY_RE` (`:50`) and skips prose on purpose (`:24-25`);
per-platform notes are free bold text (10 hits). The catalog is already stale on the interpreter:
`library-llms-full.md:57-61, 103-106` say `>=3.14.6` and `3.12.*` environments, while
`pixi.toml:36, 190, 359, 411` say `>=3.14.7` and `3.14.*`. Writing readiness into it adds a second
decay surface. Drop it; one header line can point at the CLI read. The stale pins are a
pre-existing finding to fix now.

### B7. Steward-owned tracked data lives in `.steward/`

The Spec surface lists `.steward/budget.yaml` and `.steward/keys-inventory.yaml`; `docs/reference/`
holds no generated YAML or JSON. Level 2 evidence belongs at `.steward/free-threading-evidence.yaml`
(dated, keyed by platform and build string).

## C. Chain and process traps before `bmad-spec`

- **Chain currency.** Spec, PRD, spine and epics are all `updated: 2026-10-04`. Stamping the next CAP
  on a later date opens a gap over `_FEEDS_GRACE_DAYS = 2` (`scripts/fleet_scan.py:2117, 2134`) and
  `chain-currency-sweep-check` reds `pr-preflight`. Re-stamp PRD, spine and epics in the same commit.
- **Capability ledger.** A new CAP in an existing Spec fails `capability-ledger-check`
  ("unclassified CAP-N", `capability_ledger.py:310-337`) without a `pyforge-steward:CAP-<n>` row in
  `docs/foundry/capability-ledger.yaml` (pattern at `:4374-4379`). Mode `rebuild`, unless the
  operator wants `A-only` with an expiry.
- **Feature flag.** Rule date 2026-09-28: `--free-threading` is a feature and needs a flag block;
  the `python-gil` pin is a fix and needs none.
- **Cross-station twins.** Under v1: doctor keeps one (ageing of Level 2 evidence, warn-only like
  `DUE_FOR_VERIFICATION_STALENESS_DAYS`); marshal, atlas and the catalog twins vanish; mason's
  hand-off (a `mason recipe` read of the readiness JSON) is a later story. Each must be named on its
  own station's Dream or scoped out explicitly.
- **No documented Dream-review step exists** (CHAIN-STANDARD section 3 goes append, memlog,
  `bmad-spec`). This file follows the marshal precedent
  (`research/preserved-work-refs-2026-10-04-review.md`): a dated review under `research/`, cited
  from the Dream.
- **Entry size.** 210 lines; the next-largest dated station entry is 72. "A Dream trim waits for
  its Spec" is cited as convention but stated nowhere. The v1/v2 split below moves most of the
  mechanism into the Spec at `bmad-spec` time.

## D. Recommended shape (what `bmad-spec` should see)

- **The readiness-read CAP (v1; the next free number on `spec-pyforge-steward` is 166).** `steward provision --free-threading [--env NAME]
  [--platform P] [--json] [--write]`, behind a flag. Engine: `pixi lock` on a throwaway manifest per
  environment, all three platforms. Statuses: `not-installable`, `abi3`, `installable` (with the
  version moves the solve needed), `pure-python`, `unassessed` (a PyPI sdist or a non-conda-forge
  package). The report names each blocker with its direct dependents and its remediation class
  (allowlist, migrator PR, in-tree `is_freethreading` skip). JSON schema shipped frozen under
  `src/pyforge/steward/data/` (the doctor and warden shape). Gates nothing; never feeds warden.
  Acceptance seeds: the 2026-10-06 baseline counts (name-level, from the lock and the repodata the
  read records), the `pyforge-testing-kit` on osx-arm64 case, an abi3 case (`cryptography` on
  linux-64), and `mcp-host` reporting linux-64 only.
- **The native-evidence CAP (v2; the number after it).** `--probe` builds the throwaway environment on the host,
  walks installed `*.cpython-314t-*.so` and `*.cp314t-win_amd64.pyd` files, imports each in a fresh
  interpreter with warnings captured (never `PYTHON_GIL=0`), records `gil-free`, `re-enables-gil` or
  `import-error` per build, and writes `.steward/free-threading-evidence.yaml`. Evidence is
  build-keyed and demotes to `installable` on a lock bump; doctor ages it (doctor twin CAP,
  warn-only). The scheduled matrix is a `backlog` story blocked on the actions-policy flip and on
  pixi reaching the macOS and Windows runners.
- **Fix story under the existing provision CAP (no flag).** Add `python-gil` beside the python pin
  (`[feature.python.dependencies]` `pixi.toml:36` and `[dependencies]` `:2443`; check the
  env-scoped pins at `:190, 359, 380, 411`), relock, regenerate `environment.yaml` if `build`
  changes, and prove it with a lock meta-test: no tracked environment resolves
  `python_abi * *_cp314t` on any platform. Fix the stale catalog pins in the same story.
- **BLAS entry: its own CAP, after the readiness read.** It is a `pixi.toml` policy (one BLAS per target, a
  thread-count default per BLAS); its only readiness tie is that the probe environment inherits the
  thread defaults.
- **Retired from the entry:** the metadata-match reader, the tracked data file, the staleness
  detector, the marshal rule, the catalog readiness notes, the bot-PR / data-store question, the
  hand-edited probe subset.

## Reproduction

Both scripts read `pixi.lock` at repo root and print the figures cited above.

```python
# cp314t and python-gil per environment and platform
import re
env = plat = None
for i, l in enumerate(open("pixi.lock"), 1):
    if i > 45000: break
    m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", l);  env = m.group(1) if m else env
    m = re.match(r"^      ([a-z0-9-]+):\s*$", l); plat = m.group(1) if m else plat
    if "_cp314t" in l: print(i, env, plat, l.strip()[:100])
```

```python
# abi3 packages per environment and platform
import re, collections
lines = open("pixi.lock").read().splitlines(); pk = lines.index("packages:")
recs, cur = {}, None
for l in lines[pk:]:
    if l.startswith(("- conda: ", "- pypi: ")): cur = l.split(": ", 1)[1].strip(); recs[cur] = []
    elif cur and l.startswith("  - "): recs[cur].append(l.strip()[2:])
abi3 = {u for u, d in recs.items() if any(x.startswith("_python_abi3_support") for x in d)}
name = lambda u: u.rsplit("/", 1)[1].rsplit("-", 2)[0]
env = plat = None; per = collections.defaultdict(set)
for l in lines[:pk]:
    m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", l);  env = m.group(1) if m else env
    m = re.match(r"^      ([a-z0-9-]+):\s*$", l); plat = m.group(1) if m else plat
    m = re.match(r"^      - conda: (\S+)", l)
    if m and m.group(1) in abi3: per[(env, plat)].add(name(m.group(1)))
print(sorted({name(u) for u in abi3})); print({k: len(v) for k, v in per.items()})
```

## Sources

- Python 3.14 release notes (PEP 779, "Free-threaded Python is officially supported"; 5-10 %).
- Python 3.14 free-threading howto (`sys._is_gil_enabled()`, `PYTHON_GIL` / `-X gil`, 1-8 %).
- PEP 803, "abi3t": stable ABI for free-threaded builds, from 3.15.
- conda-forge-pinning-feedstock `recipe/migrations/python314t.yaml` (long-term, allowlist, 20 PRs).
- regro/cf-graph-countyfair `status/migration_json/python314t.json` (bucket per feedstock).
- `pixi.lock` and `pixi.toml` at `a96e07c280`; paths cited inline.
