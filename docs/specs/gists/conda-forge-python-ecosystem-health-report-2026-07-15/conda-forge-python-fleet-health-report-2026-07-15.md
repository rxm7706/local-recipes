Conda-Forge Python Ecosystem Health Report (2026-07-15)

# Conda-Forge Python Ecosystem Health Report

**Analysis date:** 2026-07-15
**Data sources:** `cf_atlas` (local conda-forge intelligence database, refreshed 2026-07-15), live PyPI JSON API sample, live `conda-forge/conda-forge-bot-data` migration feed
**Scope:** Python packages distributed via conda-forge (PyPI-matched conda packages)
**Prepared by:** Claude Code / local `conda-forge-expert` atlas tooling

---

## Executive Summary

Conda-forge's Python footprint is large (21,163 packages, 64.6% of the channel), predominantly current with upstream (81.7%), and — when a maintainer or bot does act on a new release — fast (median 8.9 hours to publish a matching build, confirmed across the **full 19,765-feedstock population**, not a downloads-biased sample). The **Python 3.14 readiness gap is narrow**: 96.9% of Python feedstocks are already ready or require no action, leaving a confirmed, addressable population of 621 feedstocks, four of which (`tensorflow`, `sktime`, `faiss-split`, `ray-packages`) account for roughly a third of the download volume still exposed.

The headline risk is not volume — it's **concentration and tail latency**. A small number of high-traffic, compiled feedstocks carry a disproportionate share of both the version-currency risk and the migration-readiness risk, and they are stuck on identifiable, fixable blockers (merge conflicts, failing CI), not unknown causes.

---

## Key Findings

1. **Python is the majority of the channel.** 21,163 of 32,765 live conda-forge packages (64.6%) are Python-ecosystem, spanning 19,765 of 27,827 feedstocks (71.0%).

2. **Four in five Python packages are current with upstream.** 81.7% match or exceed their PyPI/source release; only 3.6% are a full major version behind. Coverage of this comparison is near-complete (99.95% of packages have a resolvable upstream match).

3. **The Python 3.14 migration is materially further along than a naive read suggests.** 82.3% of Python feedstocks are `noarch` and require no rebuild at all. Of the 17.7% that do need a rebuild, 9.2% (of the whole population) are already done. The confirmed, unresolved gap is **3.1% of all Python feedstocks (621 of 19,765)**.

4. **Migration-readiness risk is concentrated, not diffuse.** The top four unmigrated feedstocks by download volume (`tensorflow`, `sktime`, `faiss-split`, `ray-packages`) represent roughly a third of all download volume still in the gap. Each has a named, actionable blocker — a merge-conflicted bot PR (`dirty`) or a failing CI leg (`unstable`) — not an unknown cause.

5. **Release pickup is fast, but the fleet-wide "how fast" question and the "how much is behind" question are different populations — conflating them produces a materially wrong number.** A naive release-to-availability lag calculation over the full 19,765-feedstock population shows 47.0% of computed results with a lag exceeding 10 days. Root-cause analysis found this to be dominated by a measurement artifact (detailed in Finding 6), not a real backlog.

6. **A significant methodological artifact was identified and corrected in this analysis — and confirmed at full-population scale.** Conda-forge periodically rebuilds long-stable package versions for unrelated reasons (Python-version-matrix expansion, ABI/compiler migrations, dependency bumps). The rebuild timestamp is real, but it does not represent "time to catch up" — it represents "time since this old version was last touched for an unrelated reason." Of the raw ">10 day" bucket across all 18,083 computed feedstock results, **83.7% had a PyPI release itself over one year old** — the artifact, confirmed at scale, not a small-sample fluke (an earlier 5,000-package downloads-biased sample had found 76.5% on the same check). The corrected analysis, restricted to releases young enough that this artifact cannot apply (n = 4,078, the full feedstock population), shows: **72.4% of packages published within 24 hours, 83.7% within 72 hours, median lag 8.9 hours** — closely matching the original smaller sample (72.5% / 83.1% / 8.2h), which cross-validates that the smaller sample was not meaningfully biased despite being downloads-weighted.

7. **A real, non-artifactual slow-catch-up tail exists and is identifiable.** Ten feedstocks with genuinely recent releases (all under 90 days old) show real, uncorrected lag of 70–86 days — dominated by heavy, compiled scientific packages (`biaplotter`, `photutils`, `itk`, `eigency`, `ydata-profiling`). These are legitimate targets for packaging attention, distinct from the migration-readiness gap in Finding 3.

---

## Section 1 — Ecosystem Composition

| Metric | Count | Share |
|---|--:|--:|
| Total live conda-forge packages (all ecosystems) | 32,765 | — |
| Total live conda-forge feedstocks (all ecosystems) | 27,827 | — |
| **Python packages** (PyPI-matched) | **21,163** | 64.6% of packages |
| **Python feedstocks** (≥1 output PyPI-matched) | **19,765** | 71.0% of feedstocks |

The package/feedstock gap reflects multi-output recipes — one feedstock producing several conda packages.

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

Pattern: heavy, compiled scientific-computing packages dominate this tail (consistent with the earlier sample's finding — `photutils`, `itk`, `eigency` reappear). This is consistent with build complexity — not maintainer neglect — as the likely driver, though this analysis does not confirm root cause per package.

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

Not meaningfully. The two corrected distributions are within 1 percentage point of each other on every bucket, and medians differ by 0.3 hours (8.9h vs. 9.2h). **This is the expected result, not a null finding**: `scope`'s 1,202 packages beyond the feedstock population are too small a fraction (5.9% of Section 5's matched population) to move the aggregate, and there is no evidence in this data that the specific packages this organization references behave differently — in terms of conda-forge's release-pickup speed — than the fleet at large. If a future refresh of `scope` (e.g., after removing the dominant `conda-forge-pypi` bulk-add, to isolate just the organization-specific requests) shows a materially different distribution, that would be the more interesting signal; this snapshot does not.

---

## Recommendations

1. **Treat the four highest-download unmigrated feedstocks as a priority queue, not a backlog item.** `tensorflow` and `faiss-split` need a manual PR rebase (merge conflicts); `sktime`, `ray-packages`, and `pystan` need CI debugging on the py3.14 build itself. These are the highest-leverage single actions available in the current dataset.

2. **Do not use raw `latest_conda_upload` deltas as a freshness KPI without the release-age correction applied.** Any future automation of this metric must exclude or separately bucket packages whose upstream release predates a reasonable "genuine catch-up" window (this analysis used 90 days); otherwise migration-driven rebuilds of stable packages will manufacture false alarms. This is now confirmed at three independent sample scales/populations (5,000-download-biased, 19,726-feedstock, 20,920-scope) — treat it as a structural property of conda-forge's rebuild cadence, not a sampling quirk.

3. **Track the ten-feedstock slow-catch-up tail (Section 4) as a distinct category from migration readiness (Section 3).** They represent different failure modes — packaging complexity for actively-releasing software, versus a one-time version-matrix rebuild — and likely warrant different remediation (build-system investment vs. bot-PR triage).

4. **Revisit the 1,053 "not in tracker" feedstocks before treating the 96.9% readiness figure as final.** This analysis assumed they require no action; that assumption was not individually verified and is the single largest source of uncertainty in the Section 3 headline number.

5. **If `scope`-specific freshness behavior is genuinely of interest, isolate it from the bulk `conda-forge-pypi` addition.** Section 5 as currently constructed is dominated by the full ecosystem population it absorbed; a `scope` variant containing only the organization-specific sources (enterprise manifests, the GitHub Projects board, the maintainer's feedstock list, `pixi.toml`) would be a sharper test of whether this organization's actual dependency footprint tracks upstream any differently than the fleet at large.

---

## Methodology & Data Sources

- **Ecosystem composition and version currency:** local `cf_atlas.db` (conda-forge intelligence database), refreshed same-day via its standard incremental phase pipeline (channel scan, PyPI current-version cache, dependency graph, feedstock health). Version comparisons use `packaging.version` (PEP 440-aware), not string equality.
- **Python 3.14 migration status:** live JSON pulled from `raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/status/migration_json/python314.json` at analysis time — the same data source that powers conda-forge's public migration status dashboard.
- **Release-to-availability sample (Section 4):** live query against `pypi.org`'s JSON API for one representative package per Python feedstock — the full 19,726-feedstock population with resolvable data (not a downloads-weighted sample), at concurrency 3 with retry/backoff, consistent with the atlas's existing PyPI-crawl conventions.
- **Release-to-availability sample (Section 5):** the same live-fetch pipeline and PyPI JSON API, applied to the `scope` population (20,920 matched packages). Section 4 and Section 5's live fetches were deduplicated into a single ~20,928-package union pass (the two populations overlap by 94%), so no package was fetched from PyPI twice.

## Limitations

- **Section 4 is now the full feedstock population, not a sample** — this removes the earlier downloads-bias limitation entirely. The remaining constraint is coverage: only 91.7% of feedstocks matched to a resolvable PyPI release, and the corrected bucket table further restricts to the 22.6% with a release ≤90 days old (n=4,078) — this is a real subset, not the full 19,726, because most feedstocks did not have a qualifying recent release to measure at all (this is a coverage constraint of the methodology, not a chosen sample).
- **Section 5's `scope` population is heavily dominated by the `conda-forge-pypi` bulk addition** (21,163 of 21,952 entries, 96.4%), so its results are not independent confirmation from a meaningfully different population — see Recommendation 5 for how to sharpen this in a future pass.
- 1,800 of the 20,928 union-fetched packages (8.6%) could not be matched to a specific PyPI release at all (version-string normalization differences or conda-only version strings); excluded from all Section 4/5 figures.
- Negative-lag results (conda build timestamp before PyPI's recorded upload time) were excluded from the corrected tables without individual root-cause investigation, consistent with the original analysis.
- The 1,053 Python feedstocks absent from the py3.14 migration tracker were **not individually verified**; Section 3's 96.9% readiness figure assumes their absence means no action is required, which is a plausible but unconfirmed assumption.
- All figures are a point-in-time snapshot (2026-07-15) and will drift as conda-forge's own migration and release activity, and this organization's `scope` tab, continue to change.
