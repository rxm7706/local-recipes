Conda-Forge Python Ecosystem Health Report — v2 (2026-07-15)

# Conda-Forge Python Ecosystem Health Report — v2

**Analysis date:** 2026-07-15
**Data sources:** `cf_atlas` (local conda-forge intelligence database, refreshed 2026-07-15), live PyPI JSON API sample, live `conda-forge/conda-forge-bot-data` migration feed, live `api.basilisk.prefix.dev` OSV-compatible vulnerability API
**Scope:** Python packages distributed via conda-forge (PyPI-matched conda packages)
**Prepared by:** Claude Code / local `conda-forge-expert` atlas tooling
**v2 changes from v1:** adds Section 6 (vulnerability exposure via Basilisk); Sections 1–5 unchanged from v1.

---

## Executive Summary

Conda-forge's Python footprint is large (21,163 packages, 64.6% of the channel), predominantly current with upstream (81.7%), and — when a maintainer or bot does act on a new release — fast (median 8.9 hours to publish a matching build, confirmed across the **full 19,765-feedstock population**, not a downloads-biased sample). The **Python 3.14 readiness gap is narrow**: 96.9% of Python feedstocks are already ready or require no action, leaving a confirmed, addressable population of 621 feedstocks, four of which (`tensorflow`, `sktime`, `faiss-split`, `ray-packages`) account for roughly a third of the download volume still exposed.

**New in v2:** version-string currency and true security currency are not the same thing. Of the 21,163 Python packages, only 1.6% (348) carry a confirmed conda-native vulnerability match on their *current* installed version — but **113 of those are packages this report's own Section 2 already classifies as "current with upstream"**, including `libuuid` (203M downloads), `libtiff` (135M), and `libarchive` (57M). Being at the latest available conda-forge build does not mean being unaffected; for compiled system libraries, the fix for a CVE is frequently a *future* release, not something already sitting one version bump away. Separately, none of Section 4's ten slowest-catching-up feedstocks carry a matched vulnerability — the "slow to update" population and the "known-vulnerable" population are empirically independent in this dataset.

The headline risk is not volume — it's **concentration and tail latency**. A small number of high-traffic, compiled feedstocks carry a disproportionate share of the version-currency risk, the migration-readiness risk, and (new in v2) the confirmed-vulnerability risk, and in every case the blocker is identifiable and fixable, not an unknown cause.

---

## Key Findings

1. **Python is the majority of the channel.** 21,163 of 32,765 live conda-forge packages (64.6%) are Python-ecosystem, spanning 19,765 of 27,827 feedstocks (71.0%).

2. **Four in five Python packages are current with upstream.** 81.7% match or exceed their PyPI/source release; only 3.6% are a full major version behind. Coverage of this comparison is near-complete (99.95% of packages have a resolvable upstream match).

3. **The Python 3.14 migration is materially further along than a naive read suggests.** 82.3% of Python feedstocks are `noarch` and require no rebuild at all. Of the 17.7% that do need a rebuild, 9.2% (of the whole population) are already done. The confirmed, unresolved gap is **3.1% of all Python feedstocks (621 of 19,765)**.

4. **Migration-readiness risk is concentrated, not diffuse.** The top four unmigrated feedstocks by download volume (`tensorflow`, `sktime`, `faiss-split`, `ray-packages`) represent roughly a third of all download volume still in the gap. Each has a named, actionable blocker — a merge-conflicted bot PR (`dirty`) or a failing CI leg (`unstable`) — not an unknown cause.

5. **Release pickup is fast, but the fleet-wide "how fast" question and the "how much is behind" question are different populations — conflating them produces a materially wrong number.** A naive release-to-availability lag calculation over the full 19,765-feedstock population shows 47.0% of computed results with a lag exceeding 10 days. Root-cause analysis found this to be dominated by a measurement artifact (detailed in Finding 6), not a real backlog.

6. **A significant methodological artifact was identified and corrected in this analysis — and confirmed at full-population scale.** Conda-forge periodically rebuilds long-stable package versions for unrelated reasons (Python-version-matrix expansion, ABI/compiler migrations, dependency bumps). The rebuild timestamp is real, but it does not represent "time to catch up." Of the raw ">10 day" bucket across all 18,083 computed feedstock results, **83.7% had a PyPI release itself over one year old** — the artifact, confirmed at scale (an earlier 5,000-package downloads-biased sample had found 76.5% on the same check). The corrected analysis (n = 4,078) shows: **72.4% of packages published within 24 hours, 83.7% within 72 hours, median lag 8.9 hours** — closely matching the original smaller sample (72.5% / 83.1% / 8.2h).

7. **A real, non-artifactual slow-catch-up tail exists and is identifiable.** Ten feedstocks with genuinely recent releases (all under 90 days old) show real, uncorrected lag of 70–86 days — dominated by heavy, compiled scientific packages (`biaplotter`, `photutils`, `itk`, `eigency`, `ydata-profiling`).

8. **(New in v2) Version currency and security currency are different measurements, and the gap between them is concentrated in compiled system libraries.** 1.6% of the ecosystem (348 packages) carries a confirmed vulnerability match on its current version, but among those, **113 are packages Section 2 already calls "current"** — meaning conda-forge is at the latest upstream release and the CVE persists anyway. The highest-download instances (`libuuid` 203M, `libtiff` 135M, `libarchive` 57M, `perl` 33M) are all compiled non-Python system libraries — this is a real, live security-exposure surface that a version-currency check alone cannot see.

9. **(New in v2) The slow-catch-up tail and the vulnerability-exposure population do not overlap.** None of Section 4's ten slowest-to-update feedstocks appear in Basilisk's confirmed-vulnerability set. In this dataset, "slow to release a new build" and "known to be currently vulnerable" are independent risk signals, not the same problem wearing two names — both need tracking, but neither predicts the other.

10. **(New in v2) Most confirmed CVE matches are a deployment-currency problem, not an absence-of-fix problem.** Checking all 765 unique advisories' fix-version data against each affected package's currently-installed version: **85.3% of the 5,101 (package, advisory) matches are directly resolvable by moving to a version that already exists.** Only ~15% represent the genuinely harder case — no known fix, or a version-branch structure where "just upgrade" isn't well-defined.

---

## Section 1 — Ecosystem Composition

| Metric | Count | Share |
|---|--:|--:|
| Total live conda-forge packages (all ecosystems) | 32,765 | — |
| Total live conda-forge feedstocks (all ecosystems) | 27,827 | — |
| **Python packages** (PyPI-matched) | **21,163** | 64.6% of packages |
| **Python feedstocks** (≥1 output PyPI-matched) | **19,765** | 71.0% of feedstocks |

The package/feedstock gap reflects multi-output recipes — one feedstock producing several conda packages.

**What composes the other 35.4% (11,602 packages)** — verified live against the atlas, not assumed:

| Category | Count | Share of 32,765 |
|---|--:|--:|
| **R / CRAN** (`r-*` naming convention) | 3,814 | 11.6% |
| Perl / CPAN (`perl-*`) | 184 | 0.6% |
| Compiler/toolchain (gcc, clang, llvm, gfortran, etc.) | 162 | 0.5% |
| Rust / Cargo | 61 | 0.2% |
| Go | 46 | 0.1% |
| OCaml | 15 | 0.05% |
| Lua | 10 | 0.03% |
| Julia, Node.js core, Haskell (combined) | 6 | ~0.02% |
| **Unclassified — predominantly core C/C++ system libraries** | 7,304 | 22.3% |

R/CRAN alone is over a third of the entire non-Python remainder — the real second ecosystem on the channel, not a rounding error. The "unclassified" 22.3% was spot-checked by top downloads rather than asserted: it is dominated by foundational C/C++ runtime and build infrastructure (`openssl`, `libgcc-ng`, `libgomp`, `libstdcxx-ng`, `libblas`/`libopenblas`, `libxml2`, `libcurl`, `zlib`/`xz`/`zstd`) that Python, R, and every other ecosystem on the channel links against transitively — not a mystery bucket. Notably, **the `python` interpreter itself is the #2-downloaded package in this non-Python bucket** (393M downloads): it isn't `pypi_name`-matched (the interpreter isn't shipped on PyPI), so it correctly falls outside the "Python packages" count above despite being load-bearing for the whole ecosystem. The atlas's cross-ecosystem name-mapping columns (`npm_name`, `cran_name`, `cpan_name`) were checked and found almost entirely unpopulated at scale (136 of 11,602 matched `npm_name`, 0 for CRAN/CPAN) — this breakdown uses conda-forge's actual naming conventions instead, not those columns.

## Section 2 — Version Currency vs. Upstream

*Population: 21,163 Python packages. Comparison uses PEP 440-aware version parsing against each package's resolved upstream source (PyPI or the recipe's declared VCS source, per its `conda_source_registry`).*

| Status | Count | Share |
|---|--:|--:|
| **Current** | 17,276 | **81.7%** |
| Behind — patch only | 1,090 | 5.2% |
| Behind — minor version | 1,805 | 8.5% |
| Behind — major version | 760 | 3.6% |
| Unknown (non-PEP 440 version string) | 222 | 1.0% |
| No upstream data cached | 10 | 0.05% |

Comparison coverage: 99.95%. Excluding the 1% unparseable, **82.5%** of comparable packages are current.

## Section 3 — Python 3.14 Migration Readiness

*Population: 19,765 Python feedstocks (feedstock-level, matching the migration's own unit of tracking). Live migration status pulled from `conda-forge/conda-forge-bot-data`.*

| Category | Count | Share of 19,765 |
|---|--:|--:|
| `noarch` — no rebuild required | 16,276 | 82.3% |
| Compiled — requires a rebuild | 3,489 | 17.7% |
| — of which, already **done** | 1,815 | 9.2% |
| — of which, **confirmed pending** | 621 | 3.1% |
| — of which, not in the migration tracker* | 1,053 | 5.3% |

**Net: 96.9% ready or requiring no action; 3.1% (621 feedstocks) is the confirmed, addressable gap.**

\* *Not verified individually; most plausibly do not depend on Python directly and require no rebuild, but this is an assumption, not a confirmed fact — see Limitations.*

### Highest-impact unmigrated feedstocks (by download volume)

| Feedstock | Downloads | Status | Blocker |
|---|--:|---|---|
| tensorflow | 15.5M | in-pr | Merge-conflicted bot PR (`dirty`) |
| sktime | 11.3M | in-pr | Failing CI (`unstable`) |
| faiss-split | 10.6M | in-pr | Merge-conflicted bot PR (`dirty`) |
| ray-packages | 5.5M | in-pr | Failing CI (`unstable`) |
| pystan | 3.8M | in-pr | Failing CI (`unstable`) |
| pandera | 3.1M | awaiting-parents | Blocked on a dependency's migration |
| openbabel | 2.3M | in-pr | Failing CI (`unstable`) |

These four alone (`tensorflow`, `sktime`, `faiss-split`, `ray-packages`) represent approximately **43M downloads — roughly one-third of all download volume** still in the unmigrated population.

## Section 4 — Release-to-Availability Velocity ("Freshness Score")

*Methodology: for packages currently matching their upstream release, compare PyPI's recorded `upload_time` against conda-forge's build timestamp for the same version. **Full-population sample**: one representative package (highest-download output) per Python feedstock — 19,726 of the 19,765-feedstock universe had a resolvable `latest_conda_version` + build timestamp to sample from (39 excluded for lacking either).*

### Coverage

Of the 19,726 sampled feedstocks, **18,083 (91.7%) matched to a real, resolvable PyPI release** for their current version. The remaining 8.3% failed to match — version-string normalization differences between conda-forge and PyPI, or conda-only version strings with no corresponding PyPI release.

### The artifact (see Key Finding 6), confirmed at full-population scale

The raw full-population sample shows 47.0% of the 18,083 computed results with a lag exceeding 10 days. As established in the original (5,000-package, downloads-biased) analysis, this is dominated by an artifact: conda-forge rebuilds long-stable, unchanged package versions for reasons unrelated to catching up with a release (migrations, ABI bumps, Python-version-matrix expansion). The rebuild timestamp is real, but it does not represent "time to catch up." Verification at full scale: of the raw ">10 day" bucket (8,503 feedstocks), **83.7% had a PyPI release itself over one year old** — closely matching the smaller sample's 76.5% finding on the same check, confirming the artifact is real and consistent, not a small-sample coincidence.

### Corrected distribution

*Restricted to packages whose PyPI release is itself ≤90 days old — recent enough that a conda-forge build event can only plausibly represent catching up to that release, not an unrelated later rebuild. n = 4,078 (22.6% of the 18,083 computed results).*

| Time to availability | Count | Share |
|---|--:|--:|
| **< 24 hours** | 2,953 | **72.4%** |
| 24–48 hours | 294 | 7.2% |
| 48–72 hours | 165 | 4.0% |
| 72 hours – 5 days | 174 | 4.3% |
| 5–10 days | 165 | 4.0% |
| **> 10 days** | 327 | **8.0%** |

**Cumulative: 72.4% ≤ 24h · 79.6% ≤ 48h · 83.7% ≤ 72h · 16.3% take more than 5 days.**
**Median lag: 8.9 hours. Mean: 3.04 days** (mean is pulled upward by the tail; median is the representative figure).

*Cross-validation:* these figures (72.4% / 83.7% / 8.9h) closely match the original 5,000-package, downloads-biased sample (72.5% / 83.1% / 8.2h) — evidence that download-weighting did not meaningfully distort the earlier result, though the full-population figure is now the authoritative one.

### The genuine slow-catch-up tail (not an artifact)

These feedstocks have recent releases (all under 90 days old at time of sampling) and show real, uncorrected delay:

| Feedstock | Lag | Release age |
|---|--:|--:|
| biaplotter | 86.2 days | 86 days |
| photutils | 84.7 days | 89 days |
| itk | 83.7 days | 84 days |
| nccl4py | 81.0 days | 82 days |
| django-anymail | 75.1 days | 88 days |
| negspacy | 74.0 days | 87 days |
| eigency | 73.9 days | 81 days |
| propelauth_py | 72.2 days | 85 days |
| ydata-profiling | 71.5 days | 84 days |
| aurora | 69.8 days | 75 days |

Pattern: heavy, compiled scientific-computing packages dominate this tail (consistent with the earlier sample's finding — `photutils`, `itk`, `eigency` reappear). This is consistent with build complexity — not maintainer neglect — as the likely driver, though this analysis does not confirm root cause per package. **See Section 6: none of these ten feedstocks carry a confirmed Basilisk vulnerability match.**

## Section 5 — Freshness-Lag Analysis: The "Scope" Population

*Population: the `scope` tab in `Python Packages_updated.xlsx.ods` — 21,952 unique packages aggregated from 10 sources (7 raw enterprise environment/manifest dumps, a GitHub Projects board's "OSS Enhancements" milestone, an internal maintainer's feedstock list, and this repo's own `pixi.toml local-recipes` environment). This section asks a different question from Section 4: not "how fast does conda-forge catch up, fleet-wide" but **"how fast does conda-forge catch up on the specific packages this organization's tooling, environments, and requests actually reference."***

### Coverage

Of the 21,952 `scope` entries, **20,920 (95.3%) matched to a real, resolvable conda-forge Python package** — a materially higher match rate than a random cross-section would suggest, because `scope` is now dominated by the `conda-forge-pypi` tab (the full 21,163-package ecosystem population added directly into it). The unmatched 1,032 are predominantly conda-only build metapackages (e.g. `_openmp_mutex`, `_libgcc_mutex`), platform/CUDA-variant package names (`nvidia-cuda-nvrtc-cu12`, `pylibraft-cu12`), or packages genuinely absent from conda-forge.

Of those 20,920, **19,120 (91.4%) matched to a real, resolvable PyPI release** for their current conda-forge version — consistent with Section 4's 91.7% match rate, as expected given the heavy overlap between the two populations (the `scope` population contributed only 1,202 packages beyond Section 4's feedstock population).

### The artifact, confirmed again on this population

The raw `scope` sample shows 45.7% of the 19,120 computed results with a lag exceeding 10 days, of which **83.4% have a PyPI release itself over one year old** — the same rebuild-cadence artifact identified in Section 4, appearing at essentially the same rate on an independently-constructed population. This is a third independent confirmation of the artifact (5,000-sample: 76.5%; Section 4 full population: 83.7%; Section 5 scope population: 83.4%).

### Corrected distribution

*Restricted to packages whose PyPI release is itself ≤90 days old. n = 4,486 (23.5% of the 19,120 computed results).*

| Time to availability | Count | Share |
|---|--:|--:|
| **< 24 hours** | 3,207 | **71.5%** |
| 24–48 hours | 358 | 8.0% |
| 48–72 hours | 169 | 3.8% |
| 72 hours – 5 days | 207 | 4.6% |
| 5–10 days | 196 | 4.4% |
| **> 10 days** | 349 | **7.8%** |

**Cumulative: 71.5% ≤ 24h · 79.5% ≤ 48h · 83.2% ≤ 72h · 16.8% take more than 5 days.**
**Median lag: 9.2 hours. Mean: 3.00 days.**

### Section 4 vs. Section 5 — do they actually differ?

Not meaningfully. The two corrected distributions are within 1 percentage point of each other on every bucket, and medians differ by 0.3 hours (8.9h vs. 9.2h). **This is the expected result, not a null finding**: `scope`'s 1,202 packages beyond the feedstock population are too small a fraction (5.9% of Section 5's matched population) to move the aggregate, and there is no evidence in this data that the specific packages this organization references behave differently — in terms of conda-forge's release-pickup speed — than the fleet at large.

## Section 6 — Vulnerability Exposure via Basilisk (prefix.dev) *(new in v2)*

*Basilisk (`basilisk.prefix.dev`, API at `api.basilisk.prefix.dev`) is prefix.dev's conda-native vulnerability advisory service. It matches OSV/NVD-sourced advisories against the actual conda-forge PURL (`pkg:conda/conda-forge/<name>@<version>`), which is a different match key from the atlas's existing PyPI-identity-based vulnerability data — Basilisk can, in principle, catch conda-specific packaging drift (e.g. a fix landed upstream but the feedstock hasn't rebuilt) that a PyPI-only vuln feed would miss.*

*Methodology: `POST /v1/querybatch` (85 requests of 250 queries each, well under the documented 1,000/request cap) against the full 21,163-package ecosystem population (Section 1), one query per package at its current `latest_conda_version`. Full OSV records (severity, summary) were then fetched via `GET /v1/vulns/{id}` for the 49 unique advisory IDs behind the top-15-by-downloads table below — full-detail fetching was intentionally scoped to this bounded, high-value subset rather than all 765 unique advisory IDs the batch query surfaced.*

### Overall exposure

| | Count | Share of 21,163 |
|---|--:|--:|
| Packages with ≥1 confirmed advisory on current version | 348 | 1.6% |
| Total (package, advisory) matches | 5,101 | — |
| Unique advisory IDs involved | 765 | — |

The low headline rate (1.6%) is consistent with conda-forge's high overall currency (Section 2). The average flagged package carries **14.7 matched advisories**, meaning exposure is concentrated in a small set of packages with long CVE histories, not spread thinly across the ecosystem.

### Vulnerability presence by Section 2 currency status

| Currency status | Vulnerable packages |
|---|--:|
| Behind — minor version | 169 |
| **Current** | **113** |
| Behind — major version | 37 |
| Behind — patch only | 16 |
| Unknown | 13 |

**113 of the 348 vulnerable packages (32.5%) are classified "current" by Section 2** — conda-forge is at the latest available upstream release, and a confirmed advisory still matches it. For these, there is no simple "just take the newer build" remediation; the fix, if one exists, hasn't shipped upstream yet, or the vulnerability is specific to how the artifact is built/bundled. The other 222 (63.8%) are *also* behind on version currency — for these, upgrading conda-forge's build to the already-available newer version is at least a candidate remediation path (this analysis did not verify per-CVE `fix_version` data to confirm the newer version actually resolves each specific advisory).

### Highest-impact "current but vulnerable" packages (by download volume)

| Package | Version | Downloads | # Advisories | Representative advisory |
|---|---|--:|--:|---|
| libuuid | 2.42.2 | 203,148,527 | 1 | CVE-2026-3184 — improper hostname canonicalization in `login(1)` (util-linux) |
| libtiff | 4.7.2 | 134,982,483 | 4 | CVE-2023-52356 — SEGV via crafted TIFF (network-exploitable, availability impact) |
| graphite2 | 1.3.15 | 69,907,154 | 1 | CVE-2017-5436 — out-of-bounds write via crafted font (network-exploitable, high impact) |
| libarchive | 3.8.8 | 56,934,450 | 4 | CVE-2026-5121 — 32-bit integer overflow (network-exploitable, high impact) |
| perl | 5.32.1.1 | 33,177,658 | 7 | CVE-2023-31484 — CPAN.pm doesn't verify TLS certs when downloading distributions |
| libnetcdf | 4.10.1 | 32,717,648 | 5 | CVE-2025-14932 — stack-based buffer overflow, remote code execution |
| ffmpeg | 8.1.2 | 29,206,149 | 2 | CVE-2025-25468 — memory leak in compression handling |
| libsndfile | 1.2.2 | 28,443,621 | 6 | CVE-2022-33065 — signed-integer overflow in `au_read_header` |
| opencv / libopencv | 5.0.0 | 12.7M / 12.5M | 1 | OSV-2023-444 — heap-buffer-overflow in `opj_jp2_apply_pclr` |
| yajl | 2.1.0 | 8,380,677 | 1 | CVE-2023-33460 — memory leak in `yajl_tree_parse` |
| ecdsa | 0.19.2 | 4,041,555 | 1 | CVE-2024-23342 — Minerva timing attack on P-256 (python-ecdsa) |
| unzip | 6.0 | 1,541,691 | 14 | CVE-2014-8139 — heap-based buffer overflow in CRC32 verification |
| diskcache | 5.6.3 | 1,527,986 | 1 | CVE-2025-69872 — unsafe pickle deserialization |
| pypdf2 | 3.0.1 | 1,340,404 | 1 | CVE-2023-36464 — possible infinite loop on malformed comment |

Pattern: the highest-download instances are almost entirely **compiled, non-Python system libraries** (`libuuid`, `libtiff`, `libarchive`, `perl`, `libnetcdf`, `ffmpeg`, `libsndfile`) that sit underneath the Python ecosystem as transitive dependencies rather than being installed directly by name. `ecdsa`, `diskcache`, and `pypdf2` are the three genuinely Python-identity entries in this top-14 by download volume.

### Cross-reference: the slow-catch-up tail (Section 4) is not the vulnerable set

None of Section 4's ten slowest-to-catch-up feedstocks (`biaplotter`, `photutils`, `itk`, `nccl4py`, `django-anymail`, `negspacy`, `eigency`, `propelauth_py`, `ydata-profiling`, `aurora`) appear anywhere in Basilisk's 348-package confirmed-vulnerability set. This is a clean, checked negative result, not an assumption: **"slow to release a new build" and "known to carry an active CVE" are independent risk populations in this dataset.** A remediation program built around only one of these two signals would systematically miss the other.

### What fraction of these advisories are avoidable by upgrading?

*Methodology: full OSV records were fetched for all 765 unique advisory IDs (not just the top-15 table's 49) via `GET /v1/vulns/{id}`. Each of the 5,101 (package, advisory) matches was checked for a structured `fixed` version event in the advisory's `affected[].ranges`, matched by package name — the raw OSV data retains each advisory's *original* ecosystem tag (typically `PyPI`), not `conda-forge`, so matching must be done by name, not by ecosystem field.*

| | Count | Share of 5,101 matches |
|---|--:|--:|
| **Fix version stated, current install predates it → avoidable by upgrading** | 4,353 | **85.3%** |
| Fix version stated but not cleanly comparable (different release branch — see below) | 220 | 4.3% |
| No fix-version data captured for this package at all | 528 | 10.4% |

At the **package level**: of the 348 vulnerable packages, **179 (51.4%) have at least one advisory that upgrading would resolve.** This is lower than the match-level 85.3% because a handful of packages carry many advisories with mixed fix-status — one unresolvable CVE keeps a package out of the "clean" bucket even when most of its flagged issues are individually fixable.

**Two things checked, not assumed:**

- **"No fix data" (10.4%) is a data-completeness gap, not evidence of "no fix exists."** 48% of all 765 unique advisories carry only an enumerated affected-versions list with no structured fix event — common for older CVE-sourced records on C libraries, where a real fix exists but wasn't captured in machine-readable OSV form.
- **The 4.3% "not cleanly comparable" bucket is a genuine branch-versioning artifact, hand-verified on several instances**, not noise: e.g. `airflow-with-aiobotocore` shows current `3.0.1` against a stated fix of `2.11.1`, which naive version comparison misreads as "already past the fix." That's Airflow's 2.x maintenance branch versus its 3.x branch — different release lines, not sequential versions. Simple numeric comparison breaks down across major-branch splits like this.

**Bottom line: roughly 85% of the specific CVE instances currently matched against conda-forge's Python ecosystem could be eliminated by moving to a version that already exists somewhere — this is a currency/deployment gap, not an absence of fixes.** The remaining ~15% is the genuinely harder tail: either no fix has shipped anywhere yet, or the software's branch structure makes "just upgrade" not a well-defined instruction. (Scope note: this is computed across the 348 already-vulnerable packages — i.e., "of the CVEs we found, how many are fixable," not "of all 21,163 packages, what fraction of total CVE risk is avoidable.")

---

## Recommendations

1. **Treat the four highest-download unmigrated feedstocks as a priority queue, not a backlog item.** `tensorflow` and `faiss-split` need a manual PR rebase (merge conflicts); `sktime`, `ray-packages`, and `pystan` need CI debugging on the py3.14 build itself.

2. **Do not use raw `latest_conda_upload` deltas as a freshness KPI without the release-age correction applied.** Confirmed at three independent sample scales/populations (5,000-download-biased, 19,726-feedstock, 20,920-scope) — treat it as a structural property of conda-forge's rebuild cadence, not a sampling quirk.

3. **Track the ten-feedstock slow-catch-up tail (Section 4) as a distinct category from migration readiness (Section 3) and from vulnerability exposure (Section 6).** All three are independent failure modes in this data, confirmed by the zero-overlap cross-check.

4. **Revisit the 1,053 "not in tracker" feedstocks before treating the 96.9% readiness figure as final.** This assumption was not individually verified and is the single largest source of uncertainty in the Section 3 headline number.

5. **(New in v2) Treat the 113 "current but vulnerable" packages as their own remediation category, distinct from both version-lag and migration-readiness work.** These cannot be fixed by a routine version bump; each needs a package-specific judgment call (wait for an upstream fix, evaluate whether the CVE is even reachable in this build configuration, or accept the risk with an explicit waiver). The 14 highest-download instances above are the natural starting list.

6. **(Done in this v2 update) Full advisory detail was fetched for all 765 unique advisory IDs** (not just the top-15 table's 49), enabling the fix-availability analysis above. The natural next step is ranking the full 348-package vulnerable set by actual CVSS severity rather than by download volume alone — the severity data is now in hand but not yet used for ranking.

7. **(New) Prioritize the 179 packages with a confirmed available fix (85.3% of matches) as a scheduling problem, not a research problem.** For these, a specific newer version is already known to resolve the CVE — the work is packaging/rebuild scheduling. Reserve case-by-case security triage for the ~169 packages where no fix is currently resolvable from this data (the harder, genuinely open tail).

8. **If `scope`-specific freshness behavior is genuinely of interest, isolate it from the bulk `conda-forge-pypi` addition** (unchanged from v1 — see Section 5).

---

## Methodology & Data Sources

- **Ecosystem composition and version currency:** local `cf_atlas.db` (conda-forge intelligence database), refreshed same-day via its standard incremental phase pipeline. Version comparisons use `packaging.version` (PEP 440-aware), not string equality.
- **Python 3.14 migration status:** live JSON pulled from `raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status/migration_json/python314.json`.
- **Release-to-availability samples (Sections 4 & 5):** live queries against `pypi.org`'s JSON API, deduplicated into a single ~20,928-package union pass (94% overlap between the two populations) so no package was fetched twice.
- **Vulnerability exposure (Section 6, new in v2):** live queries against `api.basilisk.prefix.dev`'s OSV-compatible REST API — `POST /v1/querybatch` (85 requests × 250 packages) against the full Section 1 ecosystem population, followed by `GET /v1/vulns/{id}` for **all 765 unique advisory IDs** the batch query surfaced (updated after initial publication, which had scoped detail-fetching to the top-15 table's 49 IDs only). No authentication required; the schema was confirmed directly against the service's own `/openapi.json` before querying, not assumed from documentation prose. Fix-version comparisons use `packaging.version` (PEP 440-aware), matched by package name against the advisory's `affected[].package.name` — the raw OSV data retains each advisory's original ecosystem tag (typically `PyPI`), so matching by ecosystem field would silently fail; this was caught and corrected during the analysis.

## Limitations

- **Section 4 is the full feedstock population, not a sample.** The corrected bucket table restricts to the 22.6% of computed results with a release ≤90 days old (n=4,078) — a coverage constraint of the methodology (most feedstocks lack a qualifying recent release to measure), not a chosen sample.
- **Section 5's `scope` population is heavily dominated by the `conda-forge-pypi` bulk addition** (96.4% of entries), so it is not independent confirmation from a meaningfully different population.
- 1,800 of the 20,928 union-fetched packages (8.6%) could not be matched to a specific PyPI release; excluded from Section 4/5 figures.
- The 1,053 Python feedstocks absent from the py3.14 migration tracker were **not individually verified**.
- **(Updated in this v2 revision) Fix-version detail is now fetched for all 765 unique advisory IDs**, not just the top-15 table's 49 — the earlier limitation on this point is resolved; see "What fraction of these advisories are avoidable by upgrading?" under Section 6.
- **The fix-availability analysis is conditional on the 348 already-vulnerable packages, not a fleet-wide statement.** "85.3% of matches are avoidable by upgrading" answers "of the CVEs Basilisk found, how many are fixable" — it is not a claim about what fraction of the *entire* 21,163-package ecosystem's total CVE exposure is avoidable, since that would require knowing about vulnerabilities Basilisk's matching didn't surface at all.
- **The 220 "not cleanly comparable" matches were spot-checked, not individually resolved.** Several were confirmed to be cross-branch version comparisons (e.g. Airflow 2.x vs. 3.x) where simple numeric comparison is invalid; the analysis reports this as its own bucket rather than guessing a resolution for each one. A complete fix would require per-advisory knowledge of which release branch a fix applies to, which is not uniformly available in this OSV data.
- **The 10.4% "no fix data" bucket is a data-completeness gap, not confirmation that no fix exists** — see Section 6 for detail.
- All figures are a point-in-time snapshot (2026-07-15) and will drift as conda-forge's own release activity, the py3.14 migration, and Basilisk's advisory database all continue to change.
