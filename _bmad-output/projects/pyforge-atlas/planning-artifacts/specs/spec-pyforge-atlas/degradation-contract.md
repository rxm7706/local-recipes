# The degradation contract — three markers, one exit projection

Companion to `SPEC.md`. The kernel's Constraints declare the three degradation markers, the
frozen exit-code convention, offline skip-and-mark-stale, and the single-report-producer rule
as normative. This file holds the tables those constraints compress: what each marker means,
what produces it, exactly how it projects to an exit code, and where the boundary with Warden
sits.

The markers are the mechanism by which Atlas refuses to report a confident number it did not
earn. Three markers that look interchangeable in prose are not interchangeable in the
projection — conflating them is how a pipeline silently reports `clean` for data it never read.

---

## The three markers

Never interchanged. Each answers a different question, and the difference is load-bearing.

| Marker | Means | Produced when | Data state |
|---|---|---|---|
| `not-applicable` | **Nothing existed** to assess | The subject genuinely has no instance of the thing being measured | No data is correct |
| `unresolved` | **A resolver could not run** | A resolution step was attempted and could not complete — offline resolver, missing mapping, unmatched identity | Data is missing and its absence is meaningful |
| `stale` | **Data exists but is past its freshness bound** | A dataset load succeeded against a last-good copy older than its consumer contract | Data is present but untrustworthy |

The distinction that matters most: `not-applicable` means *there was nothing to see*, while
`unresolved` and `stale` mean *there was something and we could not see it properly*. The first
is an honest zero. The other two are honest admissions of ignorance, and an honest admission of
ignorance must never project to a pass.

## The fixed policy mapping

| Marker | Policy outcome | Exit |
|---|---|---|
| `not-applicable` | reports `not-applicable` | 0 |
| `unresolved` | routes to `indeterminate` | 1 |
| `stale` beyond its contract | routes to `indeterminate` | 1 |
| `stale` within its contract | reports normally, marker surfaced | 0 |

`indeterminate` projecting to **1, never 0**, is the whole point. A degraded read is not a
passing read.

## The frozen exit convention

Exit 0 pass · 1 policy-fail · 2 error, over the closed enum `{0, 1, 2, 130}`, everywhere a CLI
or gate exits. This is Warden's convention, adopted unmodified — the two tools share one exit
grammar so fleet routing (`rc == 2` → infra owner) holds across both.

| Code | Meaning |
|---|---|
| `0` | Pass — including `not-applicable` and within-contract `stale` |
| `1` | Policy failure — including every `indeterminate` |
| `2` | Operational error |
| `130` | Interrupt |

Adding a code is a **MAJOR** change: a new value silently breaks every `elif rc == 2:` consumer
in the fleet.

## Offline degradation — skip and mark, never raise

When its endpoint is unreachable, an external-source node:

1. **Skips gracefully** — no exception, no aborted run.
2. **Keeps the last-good dataset intact** — it never writes an empty dataset over real data.
   This is the rule that prevents an outage from destroying history.
3. **Stamps a machine-readable staleness marker** in dataset metadata.

Consumers then surface the marker and apply the freshness contract. Data stale beyond its bound
degrades the affected read or policy axis to `indeterminate` — never a silent pass.

The **consumer profile is fully offline by design**. Offline is a supported mode, not a
failure mode.

New external sources bind the standard rate-limit discipline: a concurrency cap, `Retry-After`
plus jittered backoff, and remaining quota surfaced to the schedule.

## Staleness never launders

A staleness marker propagates forward. The factory layer reads pipeline outputs and carries
their source datasets' staleness markers into compiled wiki output, so republication cannot
launder freshness — a stale fact stays visibly stale no matter how many derived surfaces it
passes through.

Bundled and derived artifacts carry their own age for the same reason: a consumer must never be
able to read an old artifact and believe it is current.

## One report producer

**Exactly one terminal node** assembles the compliance report. Upstream pipelines produce
inputs and never assemble. That single producer is what makes the exit code mean one thing.

The report schema is **Warden's four-axis `ComplianceReport`, unmodified and consumed by
import** through an optional extra — never a vendored copy, so drift is impossible by
construction. Absent the extra, the gate node fails with an explicit install hint while every
other pipeline continues to run.

## The Warden boundary

| | Atlas | Warden |
|---|---|---|
| Role | Measures | Judges |
| Owns | Signals, datasets, freshness | Axes, verdicts, the lattice |
| Code edge | May depend on `pyforge-warden` **only** through the optional gate extra | **Never** imports Atlas |
| Data edge | Produces data Warden may consume | Consumption is data-level and optional-if-present |

Exactly one cross-package code edge, and it points one way. Both tools install and run
independently.

Atlas may expose a maintenance-class feed; it may not render a verdict on it. When Atlas needs
to express "this is bad," the honest expression is a marker and a number — the judgment belongs
to the gate.

## Pipeline snapshots are advisory

Before acting, the recipe-authoring loop **re-verifies live**. No Atlas surface may position
its datasets as a substitute for that check, and every payload feeding an authoring decision
carries its build timestamp. A snapshot is evidence of what was true at a moment, never a
license to skip looking.
