# The verdict contract — lattice, exit projection, and the never-false-green guards

Companion to `SPEC.md`. The kernel's Constraints declare the frozen enum, the lattice, the
sole-owner rule, and the indeterminate doctrine as normative. This file holds the tables
those constraints compress: the full projection, how an engine's own exit codes are read,
and the enumerated adversarial corpus that proves the promise mechanically.

`verdict.py` is the sole owner of everything in this file. No other module maps a status
to an exit code.

---

## The 7-rung lattice

Ordered most severe first. Status severity and exit code are **deliberately different
orderings**.

| Rung | Means |
|---|---|
| `error` | the run itself is untrustworthy — you cannot assert "no violation" over something you failed to scan |
| `policy-violation` | a finding tripped an active gate |
| `indeterminate` | **something existed we could not or would not scan** |
| `warn` | a finding surfaced that does not gate (incl. every unconfigured-axis verdict) |
| `bypassed` | a covered finding was suppressed by a valid waiver — above `clean` because a suppression is an audit-relevant event |
| `clean` | assessed, nothing found |
| `not-applicable` | **nothing existed to scan** |

`indeterminate` sits **above** `warn` for one reason: a clean sibling axis must never be
able to mask "we couldn't scan what existed." That single placement is what makes partial
coverage non-silent.

Every non-`clean` status carries `status.driver` (axis + finding id). An exit that cannot
distinguish "critical CVE" from "blocking DEP001" is an incoherent contract.

## The 7 → 4 exit projection

| Status | Exit |
|---|---|
| `clean` · `not-applicable` · `bypassed` | **0** |
| `warn` | **0** (configurable; `--warn-as-error` escalates) |
| `policy-violation` (un-waived) | **1** |
| `indeterminate` | **1** — a trustworthy run honestly reporting unproven cleanliness is a policy-family outcome, never a silent 0 |
| `error` | **2** — reserved for *operational* failure, preserving fleet routing (`rc == 2` → infra owner) |
| SIGINT / interrupt | **130** |

Derivation order: any `error` → 2; else any un-waived `policy-violation` → 1; else any
`indeterminate` → 1; else 0. `error` dominates the *exit* because the verdict is
untrustworthy; the *report* still records the violations that were detected. The exit
collapses to one number; the report does not.

**The enum is closed.** Adding a code is a MAJOR change — a new value silently breaks
every `elif rc == 2:` consumer in the fleet. This is the deliberate opposite of the
additive rule that governs flags and report fields.

## Reading the engines' exit codes as content

The gate decides on report **content + severity**, never on a subprocess return code.
osv-scanner's own codes are read as data:

| osv exit | Read as |
|---|---|
| `0` | no vulns — *but only trustworthy after the DB content pre-flight below* |
| `1` | vulns found — **expected**, not an error |
| `127` | **multiplexed**: DB-absent / empty / corrupt → coverage gap → `indeterminate`; any *other* 127 (osv crashing with a valid DB) → `error` |
| `128` | no packages found → coverage skipped → `indeterminate` |
| anything outside `{0,1,127,128}` | `error` |

**The DB content pre-flight (the sharpest false-green).** A present-but-empty or
content-corrupt database makes osv exit **0 with an empty body** — which neither the exit
code nor a namelist count catches. The loader parses and validates the advisory shape,
requires an advisory count ≥ 1 at osv's case-sensitive `PyPI` directory segment, and only
then trusts a clean. A provenance-less DB (`snapshot_at = None`) routes to
`indeterminate` regardless.

deptry emits **no severity** — its five rules are uniform violations. Severity is *our*
policy artifact, which is why the hygiene→status table lives in the config loader
alongside the CVSS thresholds (see `axes.md`).

## The C0 guard corpus — proving the promise, not asserting it

**C0: the gate never emits a false-green.** It is not one reliability item among many; it
is *the* acceptance property that the reliability, security, and exit-code constraints all
serve. The metric is mechanical: an enumerated adversarial-fixture corpus in which
**zero fixtures emit exit 0**.

| Guard | The fixture it defends against |
|---|---|
| DB integrity | stale · empty · swapped · unverifiable vulnerability database |
| Engine health | crash · timeout · missing binary · version-incompatible · output-schema drift |
| Extraction honesty | a manifest that parses but yields zero deps while its dependency section is non-empty (`deps_section_present && raw_token_count > 0 && extracted_count == 0` ⇒ `extraction-anomaly`, degrade to name-only+marked — never `clean` at 100%) |
| Discovery honesty | Python signals present but nothing parseable ⇒ fail-closed exit 2 (`--allow-empty` downgrades deliberately, for monorepo sweeps) |
| Coverage honesty | offline with no local DB ⇒ `coverage: skipped`, never "0 vulns" |
| Input safety | injection attempt in a manifest, a waiver reason, or a component name |
| Suppression discipline | a wildcard / over-broad waiver |

The governing invariant behind all of them: **absence of an expected field is an error,
not a zero**, and coverage improves **only** by resolving (reading the lock) or by
name-level flagging — never by assuming a version.

## Suppression, in the same lattice

| Waiver state | Effect |
|---|---|
| valid + matches | suppress the finding; status carries `bypassed` + `review_required`; residual exit 0 |
| valid + matches nothing | `stale-waiver` warn; no verdict change |
| expired + matches | finding **un-waived** — counts toward exit 1 — plus a `waiver-expired` warn |
| expired + matches nothing | `stale-waiver` warn |

A baseline entry suppresses the same way, by the same stable finding-ID grammar and the
same expiry semantics, but grandfathers existing debt wholesale rather than accepting one
risk. Where both a waiver and a baseline entry match, the waiver wins, and the report
echoes the suppression once with a rung discriminator naming which applied.
